"""
PEAD Stage A — build the event table (data only; no forward return is read).
Pre-registration: docs/research/prereg-pead-stage-a.md (+ clarification 1).

    .venv/bin/python research/pead_events.py fetch     # NSE results + integrated-filing indexes, XBRL values
    .venv/bin/python research/pead_events.py build     # events + data gate -> docs/research/data/pead_events.json

The fetch step is slow (thousands of XBRL files, throttled) and resumable:
everything is cached under docs/research/data/pead_*.json.
"""

import csv
import datetime
import json
import os
import re
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

DOCS_DATA = os.path.join(BACKEND, "..", "docs", "research", "data")
IDX_PATH = os.path.join(DOCS_DATA, "pead_results_index.json")
INT_PATH = os.path.join(DOCS_DATA, "pead_integrated_index.json")
XBRL_PATH = os.path.join(DOCS_DATA, "pead_xbrl_values.json")
EVENTS_PATH = os.path.join(DOCS_DATA, "pead_events.json")
MEMBERSHIP = os.path.join(HERE, "data", "nifty100_membership_monthly.csv")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
FIRST_Q_END = datetime.date(2017, 6, 30)     # q-4 for the first XBRL-era quarters
SELECTION_LAST = datetime.date(2025, 12, 31)


# --- inputs ---------------------------------------------------------------------------

def membership():
    """{month 'YYYY-MM': set(symbols)} and the set of symbols seen since 2018."""
    by_month = {}
    with open(MEMBERSHIP) as fh:
        for r in csv.DictReader(fh):
            by_month.setdefault(r["month"], set()).add(r["symbol"])
    syms = set().union(*(v for m, v in by_month.items() if m >= "2018-01"))
    return by_month, syms


def _load(path, default):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def _save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(obj, fh)
    os.replace(tmp, path)


def fetch_indexes(symbols):
    import nse_feed  # live module used read-only for its NSE cookie session (research may import live code)
    idx, integ = _load(IDX_PATH, {}), _load(INT_PATH, {})
    for i, s in enumerate(sorted(symbols)):
        if s not in idx:
            d = nse_feed._fetch(f"/api/corporates-financial-results?index=equities&symbol={s}&period=Quarterly",
                                "/companies-listing/corporate-filings-financial-results", 5)
            keep = ("broadCastDate", "exchdisstime", "filingDate", "toDate", "fromDate", "consolidated", "xbrl", "format", "relatingTo")
            idx[s] = [{k: r.get(k) for k in keep} for r in d] if isinstance(d, list) else None
            _save(IDX_PATH, idx)
            time.sleep(0.8)
        if s not in integ:
            rows, page = [], 1
            while True:
                d = nse_feed._fetch(f"/api/integrated-filing-results?index=equities&symbol={s}&period_ended=all"
                                    f"&type=Integrated%20Filing-%20Financials&page={page}",
                                    "/companies-listing/corporate-integrated-filing", 5)
                if not isinstance(d, dict) or not d.get("data"):
                    break
                keep = ("broadcast_Date", "qe_Date", "consolidated", "xbrl", "type_Sub", "revised_Date")
                rows += [{k: r.get(k) for k in keep} for r in d["data"]]
                total = int(d.get("totalCount") or 0)
                if len(rows) >= total or page >= 20:
                    break
                page += 1
                time.sleep(0.8)
            integ[s] = rows
            _save(INT_PATH, integ)
            time.sleep(0.8)
        if (i + 1) % 20 == 0:
            print(f"indexes: {i + 1}/{len(symbols)}", flush=True)
    return idx, integ


# --- filings --------------------------------------------------------------------------

def _dt(s, fmts=("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y", "%d-%B-%Y")):
    for f in fmts:
        try:
            return datetime.datetime.strptime((s or "").strip(), f)
        except ValueError:
            continue
    return None


RX_FNAME_DATE = re.compile(r"_(\d{2})(\d{2})(\d{4})\d{6}(?:_WEB)?\.xml$")


def filename_date(url):
    m = RX_FNAME_DATE.search(url or "")
    if not m:
        return None
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def filings_for(symbol, idx, integ):
    """[{q_end, basis 'C'/'S', broadcast datetime, xbrl, source}] — XBRL era only."""
    out = []
    for r in idx.get(symbol) or []:
        url, b, q = r.get("xbrl") or "", _dt(r.get("broadCastDate")), _dt(r.get("toDate"))
        if not url.endswith(".xml") or b is None or q is None:
            continue
        basis = "C" if (r.get("consolidated") or "").startswith("Consolidated") else "S"
        out.append({"q_end": q.date().isoformat(), "basis": basis, "broadcast": b.isoformat(), "xbrl": url, "source": "results"})
    for r in integ.get(symbol) or []:
        url, b, q = r.get("xbrl") or "", _dt(r.get("broadcast_Date")), _dt((r.get("qe_Date") or "").title())
        if not url.endswith(".xml") or b is None or q is None:
            continue
        basis = "C" if (r.get("consolidated") or "").startswith("Consolidated") else "S"
        out.append({"q_end": q.date().isoformat(), "basis": basis, "broadcast": b.isoformat(), "xbrl": url, "source": "integrated"})
    return out


def first_filed(filings):
    """{(q_end, basis): the earliest-broadcast filing}."""
    best = {}
    for f in filings:
        k = (f["q_end"], f["basis"])
        if k not in best or f["broadcast"] < best[k]["broadcast"]:
            best[k] = f
    return best


def year_before(q_end):
    d = datetime.date.fromisoformat(q_end)
    try:
        return d.replace(year=d.year - 1).isoformat()
    except ValueError:            # 29-Feb
        return d.replace(year=d.year - 1, day=28).isoformat()


# --- XBRL values ------------------------------------------------------------------------

TAGS = {
    "pat": ("ProfitLossForPeriod", "ProfitLossForThePeriod"),
    "paidup": ("PaidUpValueOfEquityShareCapital",),
    "fv": ("FaceValueOfEquityShareCapital",),
    "eps": ("BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
            "BasicEarningsPerShareAfterExtraordinaryItems", "BasicEarningsLossPerShareFromContinuingOperations"),
    "start": ("DateOfStartOfReportingPeriod",),
    "end": ("DateOfEndOfReportingPeriod",),
}


def parse_xbrl(text):
    out = {}
    for key, names in TAGS.items():
        for name in names:
            m = re.search(r"<[\w-]+:" + name + r'\s+contextRef="OneD"[^>]*>\s*([^<]+?)\s*<', text)
            if m:
                out[key] = m.group(1)
                break
    vals = {}
    for k in ("pat", "paidup", "fv", "eps"):
        try:
            vals[k] = float(out[k]) if k in out else None
        except ValueError:
            vals[k] = None
    vals["start"], vals["end"] = out.get("start"), out.get("end")
    return vals


def fetch_xbrl_values(urls):
    cache = _load(XBRL_PATH, {})
    todo = [u for u in urls if u not in cache]
    s = requests.Session()
    s.headers.update(UA)
    for i, u in enumerate(todo):
        try:
            r = s.get(u, timeout=30)
            cache[u] = parse_xbrl(r.text) if r.status_code == 200 else {"error": r.status_code}
        except Exception as exc:
            cache[u] = {"error": str(exc)[:80]}
        if (i + 1) % 50 == 0:
            _save(XBRL_PATH, cache)
            print(f"xbrl: {i + 1}/{len(todo)}", flush=True)
        time.sleep(0.4)
    _save(XBRL_PATH, cache)
    return cache


def needed_filings(idx, integ, symbols):
    """The (q, q-4) filings the basis rule would use, per symbol."""
    need = {}
    for s in symbols:
        best = first_filed(filings_for(s, idx, integ))
        for (q, basis), f in best.items():
            if datetime.date.fromisoformat(q) < datetime.date(2018, 3, 31):
                continue
            q4 = year_before(q)
            b = "C" if (q, "C") in best and (q4, "C") in best else ("S" if (q, "S") in best and (q4, "S") in best else None)
            if b and basis == b:
                need[(s, q)] = (best[(q, b)], best[(q4, b)], b)
    return need


# --- build ------------------------------------------------------------------------------

def build():
    import nse_prices as npx
    by_month, syms = membership()
    idx, integ = _load(IDX_PATH, {}), _load(INT_PATH, {})
    xv = _load(XBRL_PATH, {})
    need = needed_filings(idx, integ, syms)
    sessions, chains, _, _ = npx.load()          # selection sessions only; raw closes for t-6
    nxt = npx.symbol_chains(os.path.join(npx.BHAV_DIR, "symbolchange.csv"))
    cache = {}
    import bisect
    counts = {"candidates": len(need), "no_xbrl_values": 0, "not_quarterly": 0, "dating_defect": 0, "no_shares": 0,
              "no_price": 0, "not_member": 0, "exit_after_selection": 0, "kept": 0}
    shares_fallback = {"paidup": 0, "eps": 0, "previous": 0}
    events, last_shares, shares_check = [], {}, []
    for (s, q), (fq, f4, basis) in sorted(need.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        vq, v4 = xv.get(fq["xbrl"]) or {}, xv.get(f4["xbrl"]) or {}
        if vq.get("pat") is None or v4.get("pat") is None:
            counts["no_xbrl_values"] += 1
            continue
        if vq.get("start") and vq.get("end"):
            try:
                span = (datetime.date.fromisoformat(vq["end"]) - datetime.date.fromisoformat(vq["start"])).days
            except ValueError:
                span = 90
            if span > 100:
                counts["not_quarterly"] += 1
                continue
        b_dt = datetime.datetime.fromisoformat(fq["broadcast"])
        fd = filename_date(fq["xbrl"])
        if fd is not None and (b_dt.date() - fd).days >= 2:
            counts["dating_defect"] += 1
            continue
        shares, method = None, None
        if vq.get("paidup") and vq.get("fv") and vq["fv"] > 0:
            shares, method = vq["paidup"] / vq["fv"], "paidup"
        elif vq.get("eps") and abs(vq["eps"]) >= 1:
            shares, method = vq["pat"] / vq["eps"], "eps"
        elif (s, basis) in last_shares:
            shares, method = last_shares[(s, basis)], "previous"
        if not shares or shares <= 0:
            counts["no_shares"] += 1
            continue
        shares_fallback[method] += 1
        last_shares[(s, basis)] = shares
        if v4.get("paidup") and v4.get("fv") and v4["fv"] > 0:
            shares_check.append(abs(shares / (v4["paidup"] / v4["fv"]) - 1) <= 0.05)
        canon = npx.canonical(s, nxt, cache)
        c = chains.get(canon) or chains.get(s)
        pos = bisect.bisect_left(sessions, b_dt.date().isoformat())          # first session on/after the broadcast date
        if c is None or pos >= len(sessions):
            counts["no_price"] += 1
            continue
        k_before = bisect.bisect_left(c["idx"], pos)                          # chain rows strictly before that
        if k_before < 6:
            counts["no_price"] += 1
            continue
        price_t6 = c["raw"][k_before - 6]
        entry_pos = bisect.bisect_right(sessions, b_dt.date().isoformat())   # first session AFTER the broadcast date
        if entry_pos >= len(sessions):
            counts["exit_after_selection"] += 1
            continue
        entry = sessions[entry_pos]
        if s not in by_month.get(entry[:7], set()):
            counts["not_member"] += 1
            continue
        if entry_pos + 60 >= len(sessions) or sessions[entry_pos + 60] > SELECTION_LAST.isoformat():
            counts["exit_after_selection"] += 1
            continue
        sue = (vq["pat"] - v4["pat"]) / (shares * price_t6)
        events.append({"symbol": s, "chain": canon if canon in chains else s, "q_end": q, "basis": basis,
                       "broadcast": fq["broadcast"], "filename_date": fd.isoformat() if fd else None,
                       "pat_q": vq["pat"], "pat_q4": v4["pat"], "shares": shares, "shares_method": method,
                       "price_t6": price_t6, "sue_m": sue, "entry": entry, "exit": sessions[entry_pos + 60],
                       "source": fq["source"]})
        counts["kept"] += 1
    # data gate 1: coverage of point-in-time member-quarters 2019-Q2 .. 2025-Q2
    have = {(e["symbol"], e["q_end"]) for e in events}
    q_ends = [datetime.date(y, m, d) for y in range(2019, 2026) for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))
              if datetime.date(2019, 6, 30) <= datetime.date(y, m, d) <= datetime.date(2025, 6, 30)]
    denom = num = 0
    for qe in q_ends:
        for s in by_month.get(qe.isoformat()[:7], set()):
            denom += 1
            num += (s, qe.isoformat()) in have
    coverage = num / denom if denom else 0.0
    gate = {"coverage": coverage, "member_quarters": denom, "with_event": num, "gate1_pass": coverage >= 0.60,
            "shares_consistent_share": (sum(shares_check) / len(shares_check)) if shares_check else None}
    out = {"prereg": "prereg-pead-stage-a.md", "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "counts": counts, "shares_method": shares_fallback, "gate": gate, "events": events}
    _save(EVENTS_PATH, out)
    print(json.dumps({"counts": counts, "shares_method": shares_fallback, "gate": gate}, indent=1))
    return out


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    by_month, syms = membership()
    if cmd == "fetch":
        idx, integ = fetch_indexes(syms)
        need = needed_filings(idx, integ, syms)
        urls = sorted({f["xbrl"] for fq, f4, b in need.values() for f in (fq, f4)})
        print(f"{len(need)} candidate events need {len(urls)} XBRL files", flush=True)
        fetch_xbrl_values(urls)
        print("fetch done", flush=True)
    else:
        build()


if __name__ == "__main__":
    main()
