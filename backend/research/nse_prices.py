"""
NSE daily prices with official corporate-action adjustments and dividends —
the data fix behind 3i (#130, prereg-3i-momentum-corrected-data.md).

3h adjusted splits by guessing from the price and traded quantity, and missed
splits whose volume regime changed, demergers, rights and dividends. This
loader applies NSE's own corporate-actions file instead:

    split "From Rs a To Rs b"      prices before the ex-date / (a/b)
    bonus a:b                       prices before / ((a+b)/b)
    rights a:b @ premium p          prices before x TERP/P
    demerger / arrangement          prices before x OPEN(ex)/CLOSE(ex-1)
    dividend D per share            prices before x (1 - D/CLOSE(ex-1))

so `close` is a total-return price series (dividends reinvested) and `raw`
is the price as printed that day. Fund units (ISIN INF..., NSE's ETF list,
BEES/ETF names) are excluded. Sessions on or after the held-out start are
never loaded unless asked. Data only: nothing here reads a forward return.
"""

import csv
import datetime
import glob
import io
import os
import pickle
import re
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from splits import HELD_OUT_START as HELD_OUT_FIRST_SESSION  # noqa: E402

BHAV_DIR = os.path.join(BACKEND, "data", "bhav_daily")
HELD_OUT_DIR = os.path.join(BACKEND, "data", "bhav_daily_2026_heldout")
CA_DIR = os.path.join(BACKEND, "data", "corp_actions")
CACHE = os.path.join(BHAV_DIR, "nse_prices.pkl")

ETF_NAME = re.compile(r"(BEES|ETF|IETF|CASE)$")


# --- bhavcopy -------------------------------------------------------------------

def parse_bhavcopy(path):
    """EQ-series rows: (symbol, iso date, open, close, prev_close, isin, traded value ₹)."""
    out = []
    with zipfile.ZipFile(path) as z, z.open(z.namelist()[0]) as fh:
        for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="ignore")):
            r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
            if "TckrSymb" in r:
                if r.get("SctySrs") != "EQ":
                    continue
                out.append((r["TckrSymb"], r["TradDt"], float(r.get("OpnPric") or 0), float(r["ClsPric"] or 0),
                            float(r["PrvsClsgPric"] or 0), r.get("ISIN", ""), float(r.get("TtlTrfVal") or 0)))
            elif "SYMBOL" in r:
                if r.get("SERIES") != "EQ":
                    continue
                ts = r["TIMESTAMP"]
                try:
                    d = datetime.datetime.strptime(ts, "%d-%b-%Y").date().isoformat()
                except ValueError:
                    d = datetime.datetime.strptime(ts, "%d-%b-%y").date().isoformat()
                out.append((r["SYMBOL"], d, float(r.get("OPEN") or 0), float(r["CLOSE"] or 0),
                            float(r["PREVCLOSE"] or 0), r.get("ISIN", ""), float(r.get("TOTTRDVAL") or 0)))
    return out


def symbol_chains(symbolchange_csv):
    """old symbol -> new symbol, from NSE's symbolchange.csv."""
    nxt = {}
    for line in open(symbolchange_csv, errors="ignore"):
        p = [x.strip() for x in line.rsplit(",", 3)]
        if len(p) == 4 and p[1] and p[2] and p[1] != p[2] and p[1].upper() != "SM_KEY_SYMBOL":
            nxt[p[1]] = p[2]
    return nxt


def canonical(sym, nxt, cache):
    if sym in cache:
        return cache[sym]
    seen, cur = [sym], sym
    while cur in nxt and nxt[cur] not in seen:
        cur = nxt[cur]
        seen.append(cur)
    for s in seen:
        cache[s] = cur
    return cur


# --- corporate actions ------------------------------------------------------------

_NUM = r"(\d+(?:\.\d+)?)"
RX_SPLIT_KW = re.compile(r"\bs(?:plit|plt|pl|pt)\b|sub-?\s*division", re.I)
RX_BONUS = re.compile(r"\bbon(?:us)?\b\s*[-:]?\s*(?:issue\s*)?" + _NUM + r"\s*:\s*" + _NUM, re.I)
RX_BONUS_KW = re.compile(r"\bbon(?:us)?\b", re.I)
RX_RIGHTS = re.compile(r"\bri?ghts?\b\s*[-:]?\s*" + _NUM + r"\s*:\s*" + _NUM +
                       r"\s*@\s*(prem(?:ium)?\.?)?\s*(?:of\s*)?(?:rs\.?|re\.?)?\s*" + _NUM, re.I)
RX_DEMERGER = re.compile(r"demerger|scheme\s+of\s+arrangement|arrangement", re.I)
RX_RS = re.compile(r"(?:rs|re)\.?\s*-?\s*" + _NUM, re.I)
RX_PCT = re.compile(_NUM + r"\s*%")
RX_DIV_BARE = re.compile(r"\bdiv(?!ision)\w*\.?\s*[-:]?\s*" + _NUM, re.I)
RX_NUM = re.compile(_NUM)


def _split_ratio(text):
    """'From Rs a To Rs b' in any of NSE's spellings, including the abbreviated
    ones ('Fv Splt Frm Rs 10 To Re 1', 'Fv Spl-Rs10tore1', 'Fv Spl Rs.5tors.2')."""
    for clause in re.split(r"/(?!-)|;", text):   # "/-" is the rupee suffix, not a separator
        m = RX_SPLIT_KW.search(clause)
        if not m:
            continue
        nums = [float(x) for x in RX_NUM.findall(clause[m.end():])]
        if len(nums) >= 2 and nums[0] > nums[1] > 0:
            return nums[0] / nums[1]
        return None
    return None


def parse_purpose(purpose, face_value):
    """Actions in one corporate-action row: a list of (kind, value) with kind in
    split/bonus/rights/demerger/dividend. Unparsed split/bonus/rights text is
    returned as ('unparsed', text) so stage 0 can count it."""
    text = purpose.replace("–", "-")
    acts = []
    if RX_SPLIT_KW.search(text):
        r = _split_ratio(text)
        acts.append(("split", r) if r else ("unparsed", text))
    m = RX_BONUS.search(text)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        acts.append(("bonus", (a + b) / b) if a > 0 and b > 0 else ("unparsed", text))
    elif RX_BONUS_KW.search(text):
        acts.append(("unparsed", text))
    m = RX_RIGHTS.search(text)
    if m:
        a, b, prem, px = float(m.group(1)), float(m.group(2)), m.group(3), float(m.group(4))
        price = (face_value or 0) + px if prem else px
        acts.append(("rights", (a, b, price)))
    elif re.search(r"\bri?ghts?\b", text, re.I):
        acts.append(("unparsed_rights", text))
    if RX_DEMERGER.search(text):
        acts.append(("demerger", None))
    if re.search(r"\bdiv(?!ision)", text, re.I):
        total = 0.0
        for clause in re.split(r"/(?!-)|;|\band\b|&|\+", text, flags=re.I):
            if not re.search(r"\bdiv(?!ision)", clause, re.I):
                continue
            pct = RX_PCT.findall(clause)
            rs = RX_RS.findall(clause)
            if pct and not rs:
                if face_value:
                    total += sum(float(x) for x in pct) / 100.0 * face_value
            elif rs:
                total += sum(float(x) for x in rs)
            else:
                bare = RX_DIV_BARE.search(clause)
                if bare:
                    total += float(bare.group(1))
        if total > 0:
            acts.append(("dividend", total))
    return acts


def load_corporate_actions(ca_dir=CA_DIR, first_year=2008, last_year=2025):
    """[(symbol, ex_date iso, [(kind, value)...], purpose)] from NSE's yearly CSVs."""
    rows = []
    for path in sorted(glob.glob(os.path.join(ca_dir, "ca_*.csv"))):
        year = int(os.path.basename(path)[3:7])
        if year < first_year or year > last_year:
            continue
        with open(path, encoding="utf-8-sig", errors="ignore") as fh:
            for r in csv.DictReader(fh):
                r = {k.strip().strip('"'): (v or "").strip() for k, v in r.items() if k}
                try:
                    ex = datetime.datetime.strptime(r["EX-DATE"], "%d-%b-%Y").date().isoformat()
                except (KeyError, ValueError):
                    continue
                try:
                    fv = float(r.get("FACE VALUE") or 0)
                except ValueError:
                    fv = 0.0
                acts = parse_purpose(r.get("PURPOSE", ""), fv)
                if acts:
                    rows.append((r["SYMBOL"], ex, acts, r.get("PURPOSE", "")))
    return rows


def etf_symbols(ca_dir=CA_DIR):
    path = os.path.join(ca_dir, "eq_etfseclist.csv")
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8-sig", errors="ignore") as fh:
        return {(r.get("Symbol") or "").strip() for r in csv.DictReader(fh)} - {""}


# --- the panel --------------------------------------------------------------------

def load(refresh=False, include_held_out=False, bhav_dir=BHAV_DIR, ca_dir=CA_DIR):
    """(sessions, chains, meta). chains: canonical -> dict(idx, close (total-return
    adjusted), raw, open, val, isins). Fund units excluded."""
    cache_path = CACHE.replace(".pkl", "_with_heldout.pkl") if include_held_out else CACHE
    if os.path.exists(cache_path) and not refresh:
        with open(cache_path, "rb") as fh:
            return pickle.load(fh)
    t0 = time.time()
    nxt = symbol_chains(os.path.join(bhav_dir, "symbolchange.csv"))
    cache = {}
    paths = [os.path.join(bhav_dir, f) for f in os.listdir(bhav_dir) if f.endswith(".zip")]
    if include_held_out and os.path.isdir(HELD_OUT_DIR):
        paths += [os.path.join(HELD_OUT_DIR, f) for f in os.listdir(HELD_OUT_DIR) if f.endswith(".zip")]
    by_date, bad_files = {}, 0
    for p in paths:
        try:
            rows = parse_bhavcopy(p)
        except Exception:
            bad_files += 1
            continue
        for sym, d, op, close, prev, isin, val in rows:
            if close <= 0 or (d >= HELD_OUT_FIRST_SESSION and not include_held_out):
                continue
            by_date.setdefault(d, []).append((sym, op, close, isin, val))
    sessions = sorted(by_date)
    chains, isin_owner = {}, {}
    for idx, d in enumerate(sessions):
        for sym, op, close, isin, val in by_date[d]:
            canon = canonical(sym, nxt, cache)
            if isin:
                prior = isin_owner.setdefault(isin, canon)
                if prior != canon:
                    cache[canon] = cache[sym] = prior
                    canon = prior
            c = chains.setdefault(canon, {"idx": [], "close": [], "raw": [], "open": [], "val": [], "isins": set()})
            if c["idx"] and c["idx"][-1] == idx:
                continue
            c["idx"].append(idx)
            c["raw"].append(close)
            c["close"].append(close)
            c["open"].append(op)
            c["val"].append(val)
            if isin:
                c["isins"].add(isin)

    # fund units out
    etfs = etf_symbols(ca_dir)
    aliases = {}
    for s, canon in cache.items():
        aliases.setdefault(canon, set()).add(s)
    excluded = []
    for name in list(chains):
        names = aliases.get(name, set()) | {name}
        if any(i.startswith("INF") for i in chains[name]["isins"]) or names & etfs or any(ETF_NAME.search(n) for n in names):
            excluded.append(name)
            del chains[name]

    # corporate actions, applied backward from each ex-date: collect each
    # chain's factors by row position, then one backward cumulative pass
    import bisect
    counts = {"split": 0, "bonus": 0, "rights": 0, "demerger": 0, "dividend": 0,
              "unparsed": 0, "unparsed_rights": 0, "rejected": 0, "no_chain": 0, "no_session": 0}
    events = []   # (chain, row position, kind, factor, ex_date, purpose) for stage-0 checks
    factors = {}  # chain -> {row position: product of factors}
    for sym, ex, acts, purpose in load_corporate_actions(ca_dir):
        canon = canonical(sym, nxt, cache)
        c = chains.get(canon)
        if c is None:
            counts["no_chain"] += 1
            continue
        target = bisect.bisect_left(sessions, ex)          # first session on or after the ex-date
        k = bisect.bisect_left(c["idx"], target) if target < len(sessions) else len(c["idx"])
        if k == 0 or k >= len(c["idx"]):
            counts["no_session"] += 1
            continue
        prev_close = c["raw"][k - 1]
        for kind, value in acts:
            if kind in ("unparsed", "unparsed_rights"):
                counts[kind] += 1
                continue
            f = None
            if kind in ("split", "bonus"):
                f = 1.0 / value
            elif kind == "rights":
                a, b, price = value
                terp = (b * prev_close + a * price) / (a + b) if prev_close > 0 else 0
                f = terp / prev_close if 0 < terp < prev_close else None
            elif kind == "demerger":
                # prereg: OPEN(ex)/CLOSE(ex-1), the special pre-open's ex-value.
                # Amendment 1: where the open is not a discovered ex-value (no
                # drop at the open), use CLOSE(ex)/CLOSE(ex-1) instead.
                op, cl_ex = c["open"][k], c["raw"][k]
                ratio = op / prev_close if op > 0 and prev_close > 0 else 0
                if not 0.05 < ratio < 0.98 and prev_close > 0:
                    ratio = cl_ex / prev_close
                f = ratio if 0.05 < ratio < 0.98 else None
            elif kind == "dividend":
                f = 1.0 - value / prev_close if 0 < value < prev_close * 0.9 else None
            if f is None:
                counts["rejected"] += 1
                continue
            counts[kind] += 1
            events.append((canon, k, kind, f, ex, purpose[:80]))
            per = factors.setdefault(canon, {})
            per[k] = per.get(k, 1.0) * f
    for canon, per in factors.items():
        cl = chains[canon]["close"]
        running = 1.0
        for j in range(len(cl) - 1, -1, -1):
            if j + 1 in per:
                running *= per[j + 1]
            cl[j] *= running
    meta = {"files": len(paths), "bad_files": bad_files, "sessions": len(sessions), "chains": len(chains),
            "fund_units_excluded": len(excluded), "actions_applied": counts,
            "built_seconds": round(time.time() - t0, 1)}
    out = (sessions, chains, meta, events)
    with open(cache_path, "wb") as fh:
        pickle.dump(out, fh)
    return out
