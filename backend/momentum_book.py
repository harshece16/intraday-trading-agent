"""
The paper momentum book — the positional strategy that passed 3i (README
section 83; docs/research/results-3i-momentum-corrected-data.md).

Rules, unchanged from the pre-registration: at each month-end, rank the 200
most-traded NSE stocks (median traded value over 126 sessions, as-printed
close >= Rs 20, >= 250 sessions of history, fund units excluded) by
mean(r6/sigma, r12/sigma) with the skip-month; hold 15, keep a holding while
it ranks in the top 30, replace from the top; trade at the next session's
close; pay Zerodha's delivery charges. The benchmark is the same universe
equal-weighted.

Orders fill as they did in trial 126 (README section 99): a buy waits when
the stock closes locked at its upper band, a sell waits at the lower band,
and nothing fills on a day the stock did not trade. A buy that has waited
five sessions is cancelled. Orders still open at the next month-end are
dropped and decided again. Prices come from NSE's daily bhavcopies, adjusted with NSE's
own corporate-actions file (splits, bonuses, consolidations, rights,
demergers, dividends).

The price panel is the repaired one of README section 97: it reads the
trade-for-trade series (BE, BZ) as well as EQ, so a holding that leaves EQ is
still priced and sold at what it traded for (#175). The universe is still
chosen from EQ rows only, as the rule was tested.

It runs as an evening job in its own process (`python momentum_book.py
daily`), started by the engine after the close, so building the price panel
(~70 s, a few hundred MB) never touches the trading process. State lives in
data/momentum_book_state.json. Paper only: nothing here places an order.

The job never trades past data it doesn't have (#159). A day whose bhavcopy
failed to download is fetched again on later runs, and the book stops before
it until it is in, however long that takes (#220). A month turn whose ranking
comes out empty stops the book the same way. A corporate-actions or
symbol-change refresh that fails is logged, and the state keeps how old the
file is. A download goes to a .part file and is kept only as a valid zip; a
file the panel can't read is fetched again, and the book waits for it (#262).
A holding or order follows its stock through an NSE symbol change; one whose
price history is missing stops the job rather than be valued at its cost
(#261). Only one evening job runs at a time, across engine restarts too.

The book switches itself off if, from six months on, the cumulative net
excess over the benchmark falls below n x 0.71% - 2 x 3.89% x sqrt(n)
(n months). The two figures are trial 126's, the configuration this book
runs (the owner's decision of 2026-09-29).

This module deliberately repeats the loader and ranking code of
research/nse_prices.py (its repaired panel, `load(wide=True)`),
research/momentum_3i.py and the fill rules of research/momentum_width.py
instead of importing them: live code may not import research
(test_research_splits). Parity tests hold the copies to the same answers.
"""

import argparse
import bisect
import csv
import datetime
import fcntl
import glob
import io
import json
import logging
import math
import os
import re
import statistics as st
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)

logger = logging.getLogger("trading_bot")

BHAV_DIRS = [os.path.join(DATA, d) for d in ("bhav_daily", "bhav_daily_2026_heldout", "bhav_live")]
LIVE_DIR = os.path.join(DATA, "bhav_live")
CA_DIR = os.path.join(DATA, "corp_actions")
STATE_PATH = os.path.join(DATA, "momentum_book_state.json")
LOG_PATH = os.path.join(DATA, "momentum_book.log")

DEFAULTS = {
    "enabled": True,
    "capital": 1_000_000.0,
    "universe": 200,
    "hold": 15,
    "rank_keep": 30,
    "slippage": 0.0005,
    "expected_monthly_excess": 0.0071,
    "monthly_excess_sd": 0.0389,
    "band_from_month": 6,
    "job_after": "19:30",
    "job_until": "23:30",
    "retry_minutes": 30,
}

MIN_HISTORY = 250
MIN_PRICE = 20.0
LIQ_WINDOW = 126
VOL_WINDOW = 252
STT = 0.0010
STAMP_BUY = 0.00015
NSE_TXN = 0.0000307
SEBI = 0.000001
GST = 0.18
DP_PER_SELL = 15.34
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
ETF_NAME = re.compile(r"(BEES|ETF|IETF|CASE)$")
# Series read, in order of preference when a symbol has more than one on a
# day. BE and BZ are trade-for-trade. SME series are never read.
SERIES = ("EQ", "BE", "BZ")
EQ = 0
DIVIDEND_MAX_SHARE = 1.0      # of the previous close
DEMERGER_MIN_RATIO = 0.01
# Fills (a copy of research/momentum_width.py's rules H2 to H4)
BANDS = (0.02, 0.05, 0.10, 0.20)
BAND_INSIDE, BAND_OUTSIDE = 0.0030, 0.0010
LOW_PRICE, TICK = 20.0, 0.05  # below Rs 20 a band is also matched to within one tick
BUY_CARRY = 5                 # sessions after the fill day a buy may wait


def cfg():
    try:
        import config
        return {**DEFAULTS, **getattr(config, "MOMENTUM_BOOK", {})}
    except Exception:
        return dict(DEFAULTS)


# --- data: download ---------------------------------------------------------------

def bhav_url(d):
    if d >= datetime.date(2024, 7, 8):
        tag = d.strftime("%Y%m%d")
        return tag, f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{tag}_F_0000.csv.zip"
    tag = d.strftime("%d%b%Y").upper()
    return tag, (f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{d.year}/"
                 f"{d.strftime('%b').upper()}/cm{tag}bhav.csv.zip")


def _curl(url, out, extra=None):
    cmd = ["curl", "-s", "-A", UA, "-w", "%{http_code}", "-o", out, "--max-time", "60"] + (extra or []) + [url]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=90).stdout.strip()
    except Exception:
        return "000"


def fetch_bhavcopy(d, out_dir=LIVE_DIR):
    """Download one session's bhavcopy; returns the path, or None (holiday, not yet published, failed)."""
    return download_bhavcopy(d, out_dir)[0]


def download_bhavcopy(d, out_dir=LIVE_DIR):
    """(path or None, outcome) for one day's bhavcopy. The outcome is "cached",
    "fetched", "no_file" (NSE answered 404: a weekend, a holiday, or a file
    not published yet) or "failed" (any other answer, no answer, or a file
    that is not a zip): a day that may have been a session but isn't here.

    Only a valid zip counts as cached. The download goes to `<file>.part` and
    is moved into place only once it is a valid zip, so a download cut off
    part-way (the job killed, the connection dropped) never leaves a file
    that looks cached (#262)."""
    os.makedirs(out_dir, exist_ok=True)
    tag, url = bhav_url(d)
    path = os.path.join(out_dir, f"{tag}.zip")
    if os.path.exists(path):
        if zipfile.is_zipfile(path):
            return path, "cached"
        os.remove(path)                       # a broken file from before #262: fetch it again
    part = path + ".part"
    code = _curl(url, part)
    if code != "200" or not (os.path.exists(part) and zipfile.is_zipfile(part)):
        if os.path.exists(part):
            os.remove(part)
        return None, "no_file" if code == "404" else "failed"
    os.replace(part, path)
    return path, "fetched"


def bhav_file_date(path):
    """The session date a cached bhavcopy's file name stands for, or None."""
    name = os.path.basename(path)
    if not name.endswith(".zip"):
        return None
    for fmt in ("%Y%m%d", "%d%b%Y"):
        try:
            return datetime.datetime.strptime(name[:-4], fmt).date()
        except ValueError:
            continue
    return None


def cached_dates():
    """Days with a bhavcopy that is a valid zip. A broken file is not counted,
    so the day is fetched again (#262)."""
    dates = set()
    for d in BHAV_DIRS:
        for f in glob.glob(os.path.join(d, "*.zip")):
            day = bhav_file_date(f)
            if day is not None and zipfile.is_zipfile(f):
                dates.add(day)
    return dates


REFETCH_DAYS = 31      # a day whose download failed is tried again on every run for this long


def update_bhavcopies(today, lookback_days=REFETCH_DAYS):
    """Fetch every calendar day without a bhavcopy from `lookback_days` before
    today, or from the last cached session if that is older, to today
    (weekends included: NSE holds occasional special sessions). Returns
    (files fetched, days whose download failed), the failed days sorted.

    It used to start at the day after the newest cached file, so a day whose
    download failed while a later one succeeded fell behind the start and was
    never fetched again (#159). Days NSE has no file for (404) cost one quick
    request each per run."""
    have = cached_dates()
    if not have:
        return 0, []
    d = min(max(have) + datetime.timedelta(days=1), today - datetime.timedelta(days=lookback_days))
    got, failed = 0, []
    while d <= today:
        if d not in have:
            path, outcome = download_bhavcopy(d)
            if path:
                got += 1
            elif outcome == "failed":
                failed.append(d)
            time.sleep(0.3)
        d += datetime.timedelta(days=1)
    return got, failed


def update_corporate_actions(year, ca_dir=CA_DIR):
    """Refresh NSE's corporate-actions CSV for one year (cookie-gated API)."""
    os.makedirs(ca_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        jar, out = os.path.join(tmp, "cj.txt"), os.path.join(tmp, "ca.csv")
        _curl("https://www.nseindia.com/companies-listing/corporate-filings-actions", os.devnull,
              ["-c", jar, "-b", jar])
        time.sleep(1.5)
        today = datetime.date.today()
        end = min(datetime.date(year, 12, 31), today + datetime.timedelta(days=90))
        url = (f"https://www.nseindia.com/api/corporates-corporateActions?index=equities"
               f"&from_date=01-01-{year}&to_date={end.strftime('%d-%m-%Y')}&csv=true")
        code = _curl(url, out, ["-b", jar, "-c", jar, "-H",
                                "Referer: https://www.nseindia.com/companies-listing/corporate-filings-actions"])
        if code == "200" and os.path.getsize(out) > 1000 and b"SYMBOL" in open(out, "rb").read(200):
            os.replace(out, os.path.join(ca_dir, f"ca_{year}.csv"))
            return True
    return False


def symbolchange_path():
    return os.path.join(DATA, "bhav_daily", "symbolchange.csv")


def refresh_reference_files(max_age_days=7):
    """Refresh NSE's symbol-change file once a week. Returns True when it was
    refreshed, False when the refresh failed (the older file stays in use),
    None when it was not due (#220)."""
    path = symbolchange_path()
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < max_age_days * 86400:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    code = _curl("https://nsearchives.nseindia.com/content/equities/symbolchange.csv", tmp)
    if code == "200" and os.path.exists(tmp) and os.path.getsize(tmp) > 1000:
        os.replace(tmp, path)
        return True
    if os.path.exists(tmp):
        os.remove(tmp)
    return False


# --- data: parse (a copy of research/nse_prices.py; parity-tested) -------------------

def parse_bhavcopy(path):
    """Rows of the EQ, BE and BZ series: (symbol, iso date, open, close,
    previous close, isin, traded value, position of the series in SERIES,
    high, low)."""
    out = []
    code = {name: i for i, name in enumerate(SERIES)}
    with zipfile.ZipFile(path) as z, z.open(z.namelist()[0]) as fh:
        for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="ignore")):
            r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
            if "TckrSymb" in r:
                if r.get("SctySrs") not in code:
                    continue
                out.append((r["TckrSymb"], r["TradDt"], float(r.get("OpnPric") or 0), float(r["ClsPric"] or 0),
                            float(r["PrvsClsgPric"] or 0), r.get("ISIN", ""), float(r.get("TtlTrfVal") or 0),
                            code[r["SctySrs"]], float(r.get("HghPric") or 0), float(r.get("LwPric") or 0)))
            elif "SYMBOL" in r:
                if r.get("SERIES") not in code:
                    continue
                ts = r["TIMESTAMP"]
                try:
                    d = datetime.datetime.strptime(ts, "%d-%b-%Y").date().isoformat()
                except ValueError:
                    d = datetime.datetime.strptime(ts, "%d-%b-%y").date().isoformat()
                out.append((r["SYMBOL"], d, float(r.get("OPEN") or 0), float(r["CLOSE"] or 0),
                            float(r["PREVCLOSE"] or 0), r.get("ISIN", ""), float(r.get("TOTTRDVAL") or 0),
                            code[r["SERIES"]], float(r.get("HIGH") or 0), float(r.get("LOW") or 0)))
    return out


def symbol_chains(symbolchange_csv):
    nxt = {}
    if not os.path.exists(symbolchange_csv):
        return nxt
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
RX_CONSOLIDATION = re.compile(r"consolidat", re.I)
RX_RS_WORD = re.compile(r"\b(?:rs|re)\.?\s*-?\s*" + _NUM, re.I)       # not the "re 9" inside "Share 9purpose"
RX_FACE_VALUE = re.compile(r"(?:\bof\s+)?\b(?:rs|re)\.?\s*-?\s*" + _NUM + r"\s*(?:/-)?\s*each\b", re.I)
RX_REMARK = re.compile(r"\([^)]*\)?")                                # a bracketed remark, closed or not
RX_DIVIDEND = re.compile(r"\bdiv(?!ision)", re.I)


def _consolidation_ratio(text):
    """'Consolidation ... From Re a To Rs b' with b > a: b/a (#177)."""
    for clause in re.split(r"/(?!-)|;", text):
        m = RX_CONSOLIDATION.search(clause)
        if not m:
            continue
        nums = [float(x) for x in RX_NUM.findall(clause[m.end():])]
        if len(nums) >= 2 and 0 < nums[0] < nums[1]:
            return nums[1] / nums[0]
        return None
    return None


def _dividend_text(text):
    """The text a dividend is read from: a face value ("Of Rs. 10/- Each") is
    not a dividend, and a bracketed remark repeats or breaks down an amount
    already given (#178)."""
    text = RX_FACE_VALUE.sub(" ", text)
    bare = RX_REMARK.sub(" ", text)
    for clause in re.split(r"/(?!-)|;|\band\b|&|\+", bare, flags=re.I):
        if RX_DIVIDEND.search(clause) and (RX_RS_WORD.search(clause) or RX_PCT.search(clause)
                                           or RX_DIV_BARE.search(clause)):
            return bare
    return text


def _split_ratio(text):
    for clause in re.split(r"/(?!-)|;", text):
        m = RX_SPLIT_KW.search(clause)
        if not m:
            continue
        nums = [float(x) for x in RX_NUM.findall(clause[m.end():])]
        if len(nums) >= 2 and nums[0] > nums[1] > 0:
            return nums[0] / nums[1]
        return None
    return None


def parse_purpose(purpose, face_value):
    text = purpose.replace("–", "-")
    acts = []
    if RX_CONSOLIDATION.search(text):
        r = _consolidation_ratio(text)
        acts.append(("consolidation", r) if r else ("unparsed", text))
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
        acts.append(("rights", (a, b, (face_value or 0) + px if prem else px)))
    elif re.search(r"\bri?ghts?\b", text, re.I):
        acts.append(("unparsed_rights", text))
    if RX_DEMERGER.search(text):
        acts.append(("demerger", None))
    if re.search(r"\bdiv(?!ision)", text, re.I):
        total = 0.0
        for clause in re.split(r"/(?!-)|;|\band\b|&|\+", _dividend_text(text), flags=re.I):
            if not re.search(r"\bdiv(?!ision)", clause, re.I):
                continue
            pct, rs = RX_PCT.findall(clause), RX_RS_WORD.findall(clause)
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


def load_corporate_actions(ca_dir=CA_DIR, first_year=2008, last_year=None):
    last_year = last_year or datetime.date.today().year
    rows = []
    for path in sorted(glob.glob(os.path.join(ca_dir, "ca_*.csv"))):
        try:
            year = int(os.path.basename(path)[3:7])
        except ValueError:
            continue
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
                    rows.append((r["SYMBOL"], ex, acts))
    return rows


def etf_symbols(ca_dir=CA_DIR):
    path = os.path.join(ca_dir, "eq_etfseclist.csv")
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8-sig", errors="ignore") as fh:
        return {(r.get("Symbol") or "").strip() for r in csv.DictReader(fh)} - {""}


def build_panel(bhav_dirs=None, ca_dir=CA_DIR, symbolchange=None, report=None):
    """(sessions, chains): chains[name] = dict(idx, close (total-return
    adjusted), raw, val, ser, high, low, prev, eq). ser is each row's series
    as a position in SERIES. high, low and prev (the previous close) are as
    printed; the band-lock rule reads them. eq holds the EQ rows alone, which
    is what the universe is chosen from; prices and sales use every row.

    A chain is named by the symbol's latest name in NSE's symbol-change file,
    and rows with one ISIN stay in one chain. Given a dict as `report`, it
    fills report["aliases"] (every symbol read -> the chain it is in, for the
    evening job to follow a holding whose symbol changed, #261) and
    report["unreadable"] (files that could not be read: a session the panel
    lacks, #262)."""
    bhav_dirs = bhav_dirs or BHAV_DIRS
    nxt = symbol_chains(symbolchange or symbolchange_path())
    cache, by_date, unreadable = {}, {}, []
    for d in bhav_dirs:
        for p in glob.glob(os.path.join(d, "*.zip")):
            try:
                rows = parse_bhavcopy(p)
            except Exception:
                unreadable.append(p)
                continue
            for sym, day, op, close, prev, isin, val, series, high, low in rows:
                if close > 0:
                    by_date.setdefault(day, []).append((sym, op, close, isin, val, prev, high, low, series))
    sessions = sorted(by_date)
    chains, owner = {}, {}
    for idx, day in enumerate(sessions):
        # EQ rows first, in file order, so the row kept for a chain on a day
        # is its EQ row when it has one (the sort is stable)
        for sym, op, close, isin, val, prev, high, low, series in sorted(by_date[day], key=lambda r: r[-1]):
            canon = canonical(sym, nxt, cache)
            if isin:
                prior = owner.setdefault(isin, canon)
                if prior != canon:
                    cache[canon] = cache[sym] = prior
                    canon = prior
            c = chains.setdefault(canon, {"idx": [], "close": [], "raw": [], "open": [], "val": [], "ser": [],
                                          "high": [], "low": [], "prev": [], "isins": set()})
            if c["idx"] and c["idx"][-1] == idx:
                continue
            c["idx"].append(idx)
            c["raw"].append(close)
            c["close"].append(close)
            c["open"].append(op)
            c["val"].append(val)
            c["ser"].append(series)
            c["high"].append(high)
            c["low"].append(low)
            c["prev"].append(prev)
            if isin:
                c["isins"].add(isin)
    etfs, aliases = etf_symbols(ca_dir), {}
    for s, canon in cache.items():
        aliases.setdefault(canon, set()).add(s)
    for name in list(chains):
        names = aliases.get(name, set()) | {name}
        if any(i.startswith("INF") for i in chains[name]["isins"]) or names & etfs or any(ETF_NAME.search(n) for n in names):
            del chains[name]
    factors = {}
    for sym, ex, acts in load_corporate_actions(ca_dir):
        canon = canonical(sym, nxt, cache)
        c = chains.get(canon)
        if c is None:
            continue
        target = bisect.bisect_left(sessions, ex)
        k = bisect.bisect_left(c["idx"], target) if target < len(sessions) else len(c["idx"])
        if k == 0 or k >= len(c["idx"]):
            continue
        prev = c["raw"][k - 1]
        for kind, value in acts:
            f = None
            if kind in ("split", "bonus"):
                f = 1.0 / value
            elif kind == "consolidation":
                f = value
            elif kind == "rights":
                a, b, price = value
                terp = (b * prev + a * price) / (a + b) if prev > 0 else 0
                f = terp / prev if 0 < terp < prev else None
            elif kind == "demerger":
                op, cl = c["open"][k], c["raw"][k]
                ratio = op / prev if op > 0 and prev > 0 else 0
                if not DEMERGER_MIN_RATIO < ratio < 0.98 and prev > 0:
                    ratio = cl / prev
                f = ratio if DEMERGER_MIN_RATIO < ratio < 0.98 else None
            elif kind == "dividend":
                f = 1.0 - value / prev if 0 < value < prev * DIVIDEND_MAX_SHARE else None
            if f is not None:
                per = factors.setdefault(canon, {})
                per[k] = per.get(k, 1.0) * f
    for canon, per in factors.items():
        cl, running = chains[canon]["close"], 1.0
        for j in range(len(cl) - 1, -1, -1):
            if j + 1 in per:
                running *= per[j + 1]
            cl[j] *= running
    for c in chains.values():
        keep = [j for j, series in enumerate(c["ser"]) if series == EQ]
        c["eq"] = {k: [c[k][j] for j in keep] for k in ("idx", "raw", "val")}
    if report is not None:
        report["unreadable"] = sorted(unreadable)
        report["aliases"] = {s: _resolve(s, cache, chains) for s in cache}
    return sessions, chains


def _resolve(sym, cache, chains):
    """The chain a symbol's rows went into. An ISIN merge re-points a chain's
    name after other names were already pointed at it, so follow the links."""
    cur, seen = sym, set()
    while cur not in chains and cur in cache and cache[cur] != cur and cur not in seen:
        seen.add(cur)
        cur = cache[cur]
    return cur


# --- ranking (a copy of research/momentum_3i.py; parity-tested) -----------------------

def rows_before(c, idx):
    return bisect.bisect_right(c["idx"], idx)


def close_on_or_before(c, idx):
    k = rows_before(c, idx) - 1
    return c["close"][k] if k >= 0 else None


def ranked_universe(chains, idx):
    """Eligible chains at session idx, most-traded first. Chosen from EQ rows
    only: a stock in trade-for-trade on the day is not eligible, and its
    trade-for-trade days count as days without a trade."""
    cands = []
    for name, c in chains.items():
        c = c.get("eq", c)
        k = rows_before(c, idx)
        if k < MIN_HISTORY or c["idx"][k - 1] != idx or c["raw"][k - 1] < MIN_PRICE:
            continue
        lo = bisect.bisect_left(c["idx"], idx - LIQ_WINDOW + 1)
        vals = c["val"][lo:k] + [0.0] * (LIQ_WINDOW - (k - lo))
        cands.append((st.median(vals), name))
    cands.sort(reverse=True)
    return [n for _, n in cands]


def month_end_indices(sessions):
    return [i for i, d in enumerate(sessions) if i + 1 == len(sessions) or sessions[i + 1][:7] != d[:7]]


def scores(chains, names, sessions, idx):
    """mean(r6/sigma, r12/sigma), returns measured to the month-end before idx."""
    ends = [i for i in month_end_indices(sessions) if i <= idx]
    if not ends or ends[-1] != idx or len(ends) < 14:
        return {}
    i1, i7, i13 = ends[-2], ends[-8], ends[-14]
    out = {}
    for n in names:
        c = chains[n]
        c1, c7, c13 = close_on_or_before(c, i1), close_on_or_before(c, i7), close_on_or_before(c, i13)
        if not (c1 and c7 and c13):
            continue
        k = rows_before(c, idx)
        cl = c["close"][max(0, k - VOL_WINDOW - 1):k]
        rets = [cl[j] / cl[j - 1] - 1 for j in range(1, len(cl)) if cl[j - 1] > 0]
        if len(rets) < 60:
            continue
        sigma = st.pstdev(rets)
        if sigma > 0:
            out[n] = ((c1 / c7 - 1) / sigma + (c1 / c13 - 1) / sigma) / 2
    return out


def target_book(chains, sessions, month_end_idx, current, universe_n, hold, keep):
    """(keep, sell, buy, universe): the pre-registered rebalance at a month-end,
    as it would be if every order filled. The book itself decides with
    ranking() and lets an order wait (process_session)."""
    uni, ranked, rank = ranking(chains, sessions, month_end_idx, universe_n)
    uset = set(uni)
    sell = [n for n in current if ended(chains, n, month_end_idx) or n not in uset or rank.get(n, 10 ** 9) > keep]
    kept = [n for n in current if n not in sell]
    buy = [n for n in ranked if n not in kept][:max(0, hold - len(kept))]
    return kept, sell, buy, uni


def ranking(chains, sessions, month_end_idx, universe_n):
    """(universe, names by score best first, rank of each name)."""
    uni = ranked_universe(chains, month_end_idx)[:universe_n]
    sc = scores(chains, uni, sessions, month_end_idx)
    ranked = sorted(sc, key=sc.get, reverse=True)
    return uni, ranked, {n: i + 1 for i, n in enumerate(ranked)}


def ended(chains, name, month_end_idx):
    """The listing has no row on or after the month-end."""
    return chains.get(name) is None or chains[name]["idx"][-1] < month_end_idx


# --- fills (a copy of research/momentum_width.py; parity-tested) -----------------------

def lock(c, j):
    """+1 if row j closed locked at its upper band, -1 at its lower band."""
    close, prev = c["raw"][j], c["prev"][j]
    if prev <= 0 or close <= 0:
        return 0
    ret = close / prev - 1
    at_high, at_low = close >= c["high"][j] - 1e-9, close <= c["low"][j] + 1e-9
    for b in BANDS:
        up = b - BAND_INSIDE <= ret <= b + BAND_OUTSIDE
        down = -b - BAND_OUTSIDE <= ret <= -b + BAND_INSIDE
        if prev < LOW_PRICE:
            up = up or abs(close - prev * (1 + b)) <= TICK + 1e-9
            down = down or abs(close - prev * (1 - b)) <= TICK + 1e-9
        if at_high and up:
            return 1
        if at_low and down:
            return -1
    return 0


def why_not(c, idx, side):
    """None if an order on this side can fill at session idx, else the reason
    it waits: the stock did not trade, or it closed locked against the order."""
    k = rows_before(c, idx)
    if not k or c["idx"][k - 1] != idx or c["val"][k - 1] <= 0:
        return "no_trade"
    if "high" in c and lock(c, k - 1) == (1 if side == "BUY" else -1):
        return "locked"
    return None


# --- the book -------------------------------------------------------------------------

def buy_cost(v, slip):
    return v * (STT + STAMP_BUY + NSE_TXN + SEBI + GST * (NSE_TXN + SEBI) + slip)


def sell_cost(v, slip, dp=True):
    return v * (STT + NSE_TXN + SEBI + GST * (NSE_TXN + SEBI) + slip) + (DP_PER_SELL if dp else 0.0)


def new_state(capital, today):
    return {"version": 2, "created": today, "status": "waiting_for_month_end", "status_reason": None,
            "capital": capital, "last_processed": None,
            "book": {"cash": capital, "positions": {}, "orders": []},
            "bench": {"cash": capital, "positions": {}, "orders": []},
            "nav": [], "month_points": [], "trades": [], "rebalances": 0, "fills": {}}


def load_state(path=STATE_PATH):
    if os.path.exists(path):
        with open(path) as fh:
            return upgrade_state(json.load(fh))
    return None


def upgrade_state(state):
    """A state written before orders could wait has none open."""
    for side in ("book", "bench"):
        state[side].setdefault("orders", [])
    state.setdefault("fills", {})
    state["version"] = 2
    return state


def save_state(state, path=STATE_PATH):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, path)


def value_of(position, chains, sess_idx, day_idx):
    """Value today of an amount invested at a past close, from total-return prices:
    invariant to corporate actions applied after the purchase."""
    c = chains.get(position["symbol"])
    if c is None:
        return position["amount"]
    p0 = close_on_or_before(c, sess_idx[position["fill_date"]])
    p1 = close_on_or_before(c, day_idx)
    return position["amount"] * p1 / p0 if p0 and p1 else position["amount"]


def band_threshold(n, mean, sd):
    return n * mean - 2 * sd * math.sqrt(n)


def _sell_now(state, side, name, chains, sess_idx, i, day, slip, order=None):
    book = state[side]
    pos = book["positions"].pop(name)
    v = value_of(pos, chains, sess_idx, i)
    c = sell_cost(v, slip, dp=side == "book")
    book["cash"] += v - c
    if side == "book":
        trade = {"date": day, "side": "SELL", "symbol": name, "value": round(v, 2), "cost": round(c, 2)}
        if order and order["placed"] != day:
            trade["ordered"] = order["placed"]
        row = chains.get(name)
        if row is not None and "ser" in row:
            k = rows_before(row, i)
            if k and row["idx"][k - 1] == i and row["ser"][k - 1] != EQ:
                trade["series"] = SERIES[row["ser"][k - 1]]
                _count(state, "sells_priced_in_trade_for_trade")
        state["trades"].append(trade)


def _count(state, what):
    state["fills"][what] = state["fills"].get(what, 0) + 1


def work_orders(state, side, chains, sess_idx, i, day, slip, only=None):
    """Try every open order of one book at session i. An order that cannot
    fill waits; a buy that has waited BUY_CARRY sessions is cancelled."""
    book, still = state[side], []
    for o in book["orders"]:
        if only and o["side"] != only:
            still.append(o)
            continue
        if o["side"] == "BUY" and i > sess_idx[o["placed"]] + BUY_CARRY:
            if side == "book":
                _count(state, "buys_cancelled")
                state["trades"].append({"date": day, "side": "CANCELLED BUY", "symbol": o["symbol"],
                                        "value": round(o["amount"], 2), "cost": 0.0, "ordered": o["placed"],
                                        "reason": o.get("waiting")})
            continue
        c = chains.get(o["symbol"])
        why = "no_trade" if c is None else why_not(c, i, o["side"])
        if why:
            if not o.get("waiting"):
                o["waiting"] = why
                if side == "book":
                    _count(state, "waited_%s_%s" % (o["side"].lower(), why))
            still.append(o)
            continue
        if o["side"] == "SELL":
            _sell_now(state, side, o["symbol"], chains, sess_idx, i, day, slip, o)
            continue
        amount = o["amount"]
        if amount <= 0:
            continue
        cost = buy_cost(amount, slip)
        pos = {"symbol": o["symbol"], "fill_date": day, "amount": amount - cost}
        if side == "book":
            pos["fill_price"] = c["raw"][rows_before(c, i) - 1]
            trade = {"date": day, "side": "BUY", "symbol": o["symbol"], "value": round(amount, 2),
                     "cost": round(cost, 2)}
            if o["placed"] != day:
                trade["ordered"] = o["placed"]
            state["trades"].append(trade)
        book["positions"][o["symbol"]] = pos
        book["cash"] -= amount
    book["orders"] = still


def _order(book, side, name, day, amount=0.0):
    book["orders"].append({"side": side, "symbol": name, "placed": day, "amount": amount, "waiting": None})


def rebalance(state, chains, sessions, sess_idx, i, day, conf):
    """The month-turn rebalance, decided at the previous session's close.
    Sells that can fill are filled first; a holding whose sell waits still
    counts as held; each buy's amount is fixed today as cash over vacancies.
    Returns False when there is nothing to rank yet."""
    me, slip = i - 1, conf["slippage"]
    uni, ranked, rank = ranking(chains, sessions, me, conf["universe"])
    if not uni or not ranked:
        return False
    uset, book, bench = set(uni), state["book"], state["bench"]
    book["orders"], bench["orders"] = [], []

    for n in list(book["positions"]):
        if ended(chains, n, me):
            _count(state, "ended")
            _sell_now(state, "book", n, chains, sess_idx, i, day, slip)
        elif n not in uset or rank.get(n, 10 ** 9) > conf["rank_keep"]:
            _order(book, "SELL", n, day)
    work_orders(state, "book", chains, sess_idx, i, day, slip, "SELL")
    vacancies = conf["hold"] - len(book["positions"])
    per = book["cash"] / vacancies if vacancies > 0 else 0
    for n in ranked:
        if vacancies <= 0:
            break
        if n not in book["positions"]:
            _order(book, "BUY", n, day, per)
            vacancies -= 1
    work_orders(state, "book", chains, sess_idx, i, day, slip, "BUY")

    if state["rebalances"] == 0:
        per_b = bench["cash"] / len(uni)
        for n in uni:
            _order(bench, "BUY", n, day, per_b)
    else:
        for n in list(bench["positions"]):
            if ended(chains, n, me):
                _sell_now(state, "bench", n, chains, sess_idx, i, day, slip)
            elif n not in uset:
                _order(bench, "SELL", n, day)
        work_orders(state, "bench", chains, sess_idx, i, day, slip, "SELL")
        entrants = [n for n in uni if n not in bench["positions"]]
        if entrants:
            per_b = bench["cash"] / len(entrants)
            for n in entrants:
                _order(bench, "BUY", n, day, per_b)
    work_orders(state, "bench", chains, sess_idx, i, day, slip, "BUY")
    state["rebalances"] += 1
    state["status"] = "active"
    return True


class IncompleteData(Exception):
    """The panel can't carry out the rule on this session. The evening job
    stops before it and leaves it for the next run (#159)."""


def missing_chains(state, chains):
    """(side, symbol) of every holding or open order with no chain in the panel."""
    out = []
    for side in ("book", "bench"):
        names = list(state[side]["positions"]) + [o["symbol"] for o in state[side].get("orders", [])]
        out += [(side, n) for n in dict.fromkeys(names) if n not in chains]
    return out


def follow_symbol_changes(state, chains, aliases, today):
    """Re-key every holding and open order whose symbol is no longer a chain
    to the chain its rows are now in. NSE renames a stock (ZOMATO to ETERNAL),
    the weekly symbol-change file learns it, and build_panel names the chain
    by the new symbol; the position still carries the old one. Left alone it
    would be valued at its cost and sold at its cost at the next month turn
    (#261). Returns the changes made, also kept in state["symbol_changes"]."""
    done = []
    for side in ("book", "bench"):
        book = state[side]
        for old in list(book["positions"]):
            new = aliases.get(old)
            if old in chains or new is None or new == old or new not in chains or new in book["positions"]:
                continue
            pos = book["positions"][old]
            pos["symbol"] = new
            pos.setdefault("bought_as", old)
            # in place, so the holdings keep their order (and the book's sum its rounding)
            book["positions"] = {(new if k == old else k): v for k, v in book["positions"].items()}
            done.append({"date": today, "side": side, "from": old, "to": new, "what": "holding"})
        for o in book.get("orders", []):
            new = aliases.get(o["symbol"])
            if o["symbol"] in chains or new is None or new == o["symbol"] or new not in chains:
                continue
            done.append({"date": today, "side": side, "from": o["symbol"], "to": new, "what": o["side"] + " order"})
            o["symbol"] = new
    if done:
        state.setdefault("symbol_changes", []).extend(done)
        for ch in done:
            logger.info(f"Momentum book: {ch['side']} {ch['what']} {ch['from']} follows NSE's symbol change "
                        f"to {ch['to']} (#261)")
    return done


def process_session(state, chains, sessions, day, conf, sess_idx=None, strict=False):
    """Advance the book through one session: rebalance on the first session of
    a month (ranking at the previous session's close), otherwise try the
    orders that are waiting, then mark to market.

    A month turn with nothing to rank is skipped, as the research simulator
    skips the months before its panel has the history to rank. The evening
    job passes strict=True: the live book's panel has years of history, so an
    empty ranking there means broken data, and skipping would lose the month's
    rebalance and mark and leave the next session no longer a month turn. It
    raises IncompleteData instead, before the state is changed (#159)."""
    sess_idx = sess_idx or {d: i for i, d in enumerate(sessions)}
    i = sess_idx[day]
    if state["status"] == "switched_off":
        return
    upgrade_state(state)
    if strict:
        # A holding with no chain would be valued at its cost and sold at its
        # cost. The job re-keys a renamed one first; anything still missing is
        # broken data, so the book stops before the session (#261).
        gone = missing_chains(state, chains)
        if gone:
            raise IncompleteData(
                "no price history in the panel for " + ", ".join(f"{n} ({side})" for side, n in gone)
                + f": the book stops before {day} rather than value or sell it at its cost; a symbol change "
                "NSE's symbol-change file does not list yet, or a delisting the panel lost, needs a look")
    prev = sessions[i - 1] if i > 0 else None
    month_turn = prev is not None and prev[:7] != day[:7] and (state["last_processed"] or "") >= prev
    if month_turn:
        if not rebalance(state, chains, sessions, sess_idx, i, day, conf):
            if strict:
                uni = ranked_universe(chains, i - 1)[:conf["universe"]]
                raise IncompleteData(
                    f"the ranking at the {prev} close is empty ({len(uni)} stocks in the universe), so the "
                    f"rebalance for {day} cannot be made; the book stops before {day} and the next run tries again")
            return
    else:
        for side in ("book", "bench"):
            work_orders(state, side, chains, sess_idx, i, day, conf["slippage"])
    book_v = state["book"]["cash"] + sum(value_of(p, chains, sess_idx, i) for p in state["book"]["positions"].values())
    bench_v = state["bench"]["cash"] + sum(value_of(p, chains, sess_idx, i) for p in state["bench"]["positions"].values())
    if state["status"] == "active":
        if state["nav"] and state["nav"][-1]["date"] == day:
            state["nav"].pop()
        state["nav"].append({"date": day, "book": round(book_v, 2), "bench": round(bench_v, 2)})
    if month_turn:
        state["month_points"].append({"date": day, "book": book_v, "bench": bench_v})
        pts = state["month_points"]
        excess = [(pts[k]["book"] / pts[k - 1]["book"] - 1) - (pts[k]["bench"] / pts[k - 1]["bench"] - 1)
                  for k in range(1, len(pts))]
        n = len(excess)
        state["excess_months"] = n
        state["cumulative_excess"] = sum(excess)
        if n >= conf["band_from_month"]:
            floor = band_threshold(n, conf["expected_monthly_excess"], conf["monthly_excess_sd"])
            state["band_floor"] = floor
            if sum(excess) < floor:
                state["status"] = "switched_off"
                state["status_reason"] = (f"Cumulative excess {sum(excess):+.2%} after {n} months is below the "
                                          f"pre-registered floor {floor:+.2%}")
    state["last_processed"] = day


def _file_time(path):
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
    except OSError:
        return None


BUSY = 5      # daily()'s exit code when another evening job holds the lock


def _take_lock(state_path):
    """An exclusive lock beside the state file, holding the job's pid, or None
    when another job holds it. The OS drops it when the job ends, killed or
    not, so a stale lock never blocks a later run."""
    fh = open(state_path + ".lock", "a+")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    fh.seek(0)
    fh.truncate()
    fh.write(str(os.getpid()))
    fh.flush()
    return fh


def job_running(state_path=None):
    """True when an evening job holds the lock: one started before an engine
    restart is still running, and a second must not start beside it."""
    path = (state_path or STATE_PATH) + ".lock"
    if not os.path.exists(path):
        return False
    try:
        with open(path, "a+") as fh:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                return True
            fcntl.flock(fh, fcntl.LOCK_UN)
    except OSError:
        return False
    return False


def daily(today=None, state_path=STATE_PATH, fetch=True):
    """The evening job: fetch data, then advance the book through every
    session it hasn't processed yet. Exit code 0 = processed today's session,
    3 = today's bhavcopy isn't published yet (the engine retries), 4 = the
    data is incomplete: a past day's download failed, a bhavcopy can't be
    read, a holding has no price history, or a month-end ranking came out
    empty. The book then stops before that day, keeps what it processed up to
    it, and the next run tries again (#159). 5 = another evening job is
    running (it holds the lock beside the state file); nothing is done."""
    lock = _take_lock(state_path)
    if lock is None:
        logger.warning("Momentum book: another evening job is still running; this one does nothing")
        return BUSY
    try:
        return _daily(today, state_path, fetch)
    finally:
        lock.close()


def _daily(today, state_path, fetch):
    conf = cfg()
    today = today or datetime.date.today()
    state = load_state(state_path) or new_state(conf["capital"], today.isoformat())
    checks = state.setdefault("data", {})
    # Days whose download failed and have not come in since, kept across runs:
    # a day that keeps failing is not dropped once it leaves the 31-day
    # window that update_bhavcopies asks NSE about (#220).
    pending = {datetime.date.fromisoformat(d) for d in checks.get("failed_days_pending") or []}
    failed, ca_refreshed, sc_refreshed = [], None, None
    if fetch:
        sc_refreshed = refresh_reference_files()
        if sc_refreshed is False:
            logger.warning(
                "Momentum book: NSE's symbol-change file could not be refreshed. The copy from "
                f"{_file_time(symbolchange_path()) or 'no date'} stays in use; a holding renamed since keeps "
                "its old symbol until a refresh works (#220)")
        ca_refreshed = bool(update_corporate_actions(today.year))
        if not ca_refreshed:
            logger.warning(
                f"Momentum book: NSE's corporate-actions file for {today.year} could not be refreshed. Prices are "
                f"adjusted with the copy from {_file_time(os.path.join(CA_DIR, f'ca_{today.year}.csv')) or 'no date'}; "
                "a split or bonus announced since would show as a price drop (#159)")
        failed = list(update_bhavcopies(today)[1])
        window = today - datetime.timedelta(days=REFETCH_DAYS)
        for d in sorted(pending - set(failed)):
            # update_bhavcopies asked again for every day of the window; an
            # older one is asked for here
            if d < window and download_bhavcopy(d)[1] == "failed":
                failed.append(d)
        if failed:
            logger.warning(f"Momentum book: NSE's bhavcopy could not be downloaded for "
                           f"{', '.join(d.isoformat() for d in sorted(failed))}; the next run tries again (#159)")
        pending = set(failed)
    report = {}
    sessions, chains = build_panel(report=report)
    bad = report.get("unreadable") or []
    if bad and fetch:
        # a file cut off part-way before #262, or damaged since: fetch it again
        for path in bad:
            day = bhav_file_date(path)
            if day is None:
                continue                      # not named as a bhavcopy: left for the owner, and the book stops
            logger.warning(f"Momentum book: {path} cannot be read; it is deleted and fetched again (#262)")
            os.remove(path)
            if download_bhavcopy(day)[1] not in ("fetched", "cached"):
                pending.add(day)              # the file existed, so the day was a session: wait for it
        report = {}
        sessions, chains = build_panel(report=report)
        bad = report.get("unreadable") or []
    start = state["last_processed"] or state["created"]
    todo = [d for d in sessions if d > start and d <= today.isoformat()]
    if state["last_processed"] is None:
        # first run: remember the last session before the book existed, so the
        # next month turn after it triggers the first rebalance
        before = [d for d in sessions if d <= state["created"]]
        state["last_processed"] = before[-1] if before else None
        todo = [d for d in sessions if d > (state["last_processed"] or "") and d <= today.isoformat()]
    problem = None
    if bad:
        # the panel lacks those sessions; any of them may be in the book's past
        # or ahead of it, so nothing is processed (#262)
        todo = []
        problem = (f"{len(bad)} bhavcopy file(s) cannot be read ({', '.join(os.path.basename(p) for p in bad[:5])}"
                   f"{', ...' if len(bad) > 5 else ''}); the book stops until they are fetched again")
    # A past day whose download failed may have been a session. Processing the
    # sessions after it would fill orders a day late, or rank a month turn at
    # the wrong close, so the book waits for it (#159).
    gap = next((d.isoformat() for d in sorted(pending)
                if d < today and d.isoformat() > (state["last_processed"] or "")), None)
    if gap and not problem:
        todo = [d for d in todo if d < gap]
        problem = (f"NSE's bhavcopy for {gap} could not be downloaded; the book stops before it and the next "
                   "run tries again")
    follow_symbol_changes(state, chains, report.get("aliases") or {}, today.isoformat())
    sess_idx = {d: i for i, d in enumerate(sessions)}
    for d in todo:
        try:
            process_session(state, chains, sessions, d, conf, sess_idx, strict=True)
        except IncompleteData as exc:
            problem = str(exc)
            break
    state["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    state["latest_session"] = sessions[-1] if sessions else None
    if fetch:
        checks["corporate_actions_refreshed"] = ca_refreshed
        checks["failed_downloads"] = [d.isoformat() for d in sorted(failed)]
        if sc_refreshed is not None:
            checks["symbol_changes_refreshed"] = sc_refreshed
    # a failed day the book has already passed can't hold it back any more
    checks["failed_days_pending"] = sorted(d.isoformat() for d in pending
                                           if d.isoformat() > (state["last_processed"] or ""))
    checks["corporate_actions_as_of"] = _file_time(os.path.join(CA_DIR, f"ca_{today.year}.csv"))
    checks["symbol_changes_as_of"] = _file_time(symbolchange_path())
    checks["unreadable_files"] = [os.path.basename(p) for p in bad]
    checks["problem"] = problem
    save_state(state, state_path)
    if problem:
        logger.error(f"Momentum book: {problem} (#159)")
        return 4
    return 0 if sessions and sessions[-1] == today.isoformat() else 3


def clear_failed_day(day, state_path=STATE_PATH):
    """The owner's way past a day that keeps failing but was not a session
    (NSE answering something other than 404 for it): drop it from the list
    the book waits on. Run it only while no evening job is running."""
    lock = _take_lock(state_path)
    if lock is None:
        raise RuntimeError("an evening job is running; try again when it has finished")
    try:
        state = load_state(state_path)
        checks = (state or {}).get("data") or {}
        days = checks.get("failed_days_pending") or []
        if day not in days:
            return False
        checks["failed_days_pending"] = [d for d in days if d != day]
        save_state(state, state_path)
        return True
    finally:
        lock.close()


# --- read side (the API) ------------------------------------------------------------

def next_rebalance(after_day):
    """(ISO date, whether NSE's holiday list covers it) of the first session of
    the month after `after_day`'s month: the next month turn, whose close the
    rebalance trades at. A day processed in a month is past that month's turn,
    so this is the next rebalance for any book whose last session is
    `after_day`. In a year with no holiday list every weekday counts (#162),
    so the date may fall on a holiday; the flag says so."""
    import holidays
    d = datetime.date.fromisoformat(after_day[:10])
    first = (d.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    while first.weekday() >= 5 or holidays.is_holiday(first):
        first += datetime.timedelta(days=1)
    return first.isoformat(), holidays.calendar_missing(first) is None


def monthly_report(state):
    """The book against its benchmark, one row per completed month (README
    section 116). Read-only: it recomputes from the month points and trades
    the job already saved, and changes nothing.

    A month runs from one rebalance close to the next. Its return is the
    month points' ratio, so it is net of the charges of every trade inside
    it, including the rebalance that closes it; turnover and costs count the
    same trades. Excess and cumulative excess are the band's own figures:
    the monthly excess summed, as process_session sums it. The opening
    rebalance's trades come before the first point and belong to no month."""
    pts = state.get("month_points") or []
    trades = [t for t in state.get("trades") or [] if t.get("side") in ("BUY", "SELL")]
    months, cum = [], 0.0
    for k in range(1, len(pts)):
        a, b = pts[k - 1], pts[k]
        book_r = b["book"] / a["book"] - 1
        bench_r = b["bench"] / a["bench"] - 1
        cum += book_r - bench_r
        inside = [t for t in trades if a["date"] < t["date"] <= b["date"]]
        traded = sum(t["value"] for t in inside)
        months.append({"month": a["date"][:7], "start": a["date"], "end": b["date"], "n": k,
                       "book_return": book_r, "bench_return": bench_r, "excess": book_r - bench_r,
                       "cumulative_excess": cum, "turnover": traded / 2 / a["book"] if a["book"] else None,
                       "costs": round(sum(t["cost"] for t in inside), 2),
                       "bought": sum(1 for t in inside if t["side"] == "BUY"),
                       "sold": sum(1 for t in inside if t["side"] == "SELL")})
    opening = None
    if pts:
        first = [t for t in trades if t["date"] <= pts[0]["date"]]
        opening = {"date": pts[0]["date"], "costs": round(sum(t["cost"] for t in first), 2),
                   "bought": sum(1 for t in first if t["side"] == "BUY"),
                   "invested": round(sum(t["value"] for t in first if t["side"] == "BUY"), 2)}
    return {"months": months, "opening": opening}


def band_status(state, conf=None):
    """Where the book stands against its switch-off band: expected cumulative
    excess n x mean, and the floor n x mean - 2 x sd x sqrt(n), which applies
    from month `band_from_month` (prereg-3i, notes on the forward paper book)."""
    conf = conf or cfg()
    mean, sd, start = conf["expected_monthly_excess"], conf["monthly_excess_sd"], conf["band_from_month"]
    n = state.get("excess_months", 0) if state else 0
    cum = state.get("cumulative_excess") if n else None
    active = n >= start
    floor = band_threshold(n, mean, sd) if active else None
    if state and state.get("status") == "switched_off":
        where = "switched_off"
    elif not active:
        where = "not_active"
    else:
        where = "inside" if cum >= floor else "below"
    return {"from_month": start, "expected_monthly_excess": mean, "monthly_excess_sd": sd, "months": n,
            "cumulative_excess": cum, "expected_cumulative": n * mean, "floor": floor,
            "floor_at_start": band_threshold(start, mean, sd), "active": active, "state": where}


def summary(state_path=STATE_PATH):
    """What the dashboard shows. Cheap: reads the state file only."""
    conf = cfg()
    s = load_state(state_path)
    if not s:
        nxt, cal_ok = next_rebalance(datetime.date.today().isoformat())
        return {"enabled": conf["enabled"], "status": "not_started",
                "note": "The first evening job hasn't run yet. The book trades after the first month-end close.",
                "months": [], "opening_rebalance": None, "band": band_status(None, conf),
                "next_rebalance": nxt, "next_rebalance_calendar_ok": cal_ok}
    last = s["nav"][-1] if s["nav"] else None
    out = {"enabled": conf["enabled"], "status": s["status"], "status_reason": s.get("status_reason"),
           "capital": s["capital"], "created": s["created"], "last_processed": s["last_processed"],
           "latest_session": s.get("latest_session"), "updated_at": s.get("updated_at"),
           "rebalances": s["rebalances"], "nav": s["nav"][-400:],
           "book_value": last["book"] if last else s["capital"], "bench_value": last["bench"] if last else s["capital"],
           "excess_months": s.get("excess_months", 0), "cumulative_excess": s.get("cumulative_excess"),
           "band_floor": s.get("band_floor"), "band_from_month": conf["band_from_month"],
           "expected_monthly_excess": conf["expected_monthly_excess"],
           "holdings": sorted(({"symbol": p["symbol"], "since": p["fill_date"], "invested": round(p["amount"], 2),
                                "fill_price": p.get("fill_price")} for p in s["book"]["positions"].values()),
                              key=lambda r: r["symbol"]),
           "waiting_orders": [{"side": o["side"], "symbol": o["symbol"], "ordered": o["placed"],
                               "reason": o.get("waiting")} for o in s["book"].get("orders", [])],
           "fills": s.get("fills", {}), "data": s.get("data", {}),
           "cash": round(s["book"]["cash"], 2), "recent_trades": s["trades"][-40:]}
    rep = monthly_report(s)
    nxt, cal_ok = next_rebalance(s["last_processed"] or s["created"])
    pts = s["month_points"]
    mtd = None
    if pts and last and last["date"] > pts[-1]["date"]:
        # the month under way: shown apart, never counted before it completes
        mtd = {"start": pts[-1]["date"], "to": last["date"], "book": last["book"] / pts[-1]["book"] - 1,
               "bench": last["bench"] / pts[-1]["bench"] - 1}
    out.update(months=rep["months"], opening_rebalance=rep["opening"], band=band_status(s, conf), month_to_date=mtd,
               next_rebalance=nxt, next_rebalance_calendar_ok=cal_ok,
               first_rebalance=s["month_points"][0]["date"] if s["month_points"] else None,
               since_start={"book": out["book_value"] / s["capital"] - 1, "bench": out["bench_value"] / s["capital"] - 1})
    return out


# --- engine hook ------------------------------------------------------------------------

_last_attempt = {"date": None, "ts": 0.0, "proc": None}


def maybe_start_evening_job(now, holiday):
    """Called from the engine tick. Starts the evening job in its own process
    after the close on a weekday, retrying every half hour until the day's
    bhavcopy is in. Never raises."""
    try:
        conf = cfg()
        if not conf["enabled"] or holiday or now.weekday() >= 5:
            return False
        hhmm = now.strftime("%H:%M")
        if not conf["job_after"] <= hhmm < conf["job_until"]:
            return False
        today = now.date().isoformat()
        state = load_state()
        if state and state.get("latest_session") == today and state.get("last_processed") == today:
            return False
        if state and state.get("status") == "switched_off":
            return False                      # MOM-10: nothing left to process (#227)
        if _last_attempt["date"] == today and time.time() - _last_attempt["ts"] < conf["retry_minutes"] * 60:
            return False
        prev = _last_attempt.get("proc")
        if prev is not None and prev.poll() is None:
            return False                      # the last job is still running
        if job_running():
            return False                      # a job from before an engine restart is still running
        _last_attempt.update(date=today, ts=time.time())
        log = open(LOG_PATH, "ab")
        _last_attempt["proc"] = subprocess.Popen([sys.executable, os.path.abspath(__file__), "daily"], cwd=HERE,
                                                 stdout=log, stderr=log, stdin=subprocess.DEVNULL)
        logger.info("Momentum book: evening job started")
        return True
    except Exception:
        logger.exception("Momentum book: could not start the evening job")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["daily", "summary", "clear-failed-day"])
    ap.add_argument("--date", help="process up to this date (YYYY-MM-DD); default today. For clear-failed-day: "
                                   "the day to stop waiting for")
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()
    if a.cmd == "summary":
        print(json.dumps(summary(), indent=1))
        return 0
    if a.cmd == "clear-failed-day":
        if not a.date:
            ap.error("clear-failed-day needs --date")
        print("cleared" if clear_failed_day(a.date) else f"{a.date} is not in the list of failed days")
        return 0
    d = datetime.date.fromisoformat(a.date) if a.date else None
    # The job's output goes to momentum_book.log; give its warnings a time.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    t0 = time.time()
    code = daily(d, fetch=not a.no_fetch)
    print(f"{datetime.datetime.now().isoformat(timespec='seconds')} daily done code={code} in {time.time() - t0:.0f}s", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
