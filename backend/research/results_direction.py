"""Research look L36 — does the year-on-year direction of the FILED profit
number predict the tradable results-day move? Pre-registered in
docs/research/prereg-results-direction.md; committed before the run.
Selection sample only. Raw index/XBRL numbers cached under docs/research/data.
"""
import json
import math
import re
import statistics as st
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import kite_history
import nse_feed
import universe
from research import splits
from research.event_study import build_index, returns_for, tstat, bh_pass, p_from_t

DATA = Path(__file__).resolve().parents[2] / "docs/research/data"
IDX = DATA / "results_index.json"
XB = DATA / "results_xbrl_pat.json"
OUT = Path(__file__).resolve().parents[2] / "docs/research/results_direction_result.json"
HURDLE_BP = 16.63
WINDOWS = ("30m", "60m", "close")
_UA = {"User-Agent": "Mozilla/5.0"}


def fetch_index(symbols):
    idx = json.loads(IDX.read_text()) if IDX.exists() else {}
    for s in symbols:
        if s in idx:
            continue
        d = nse_feed._fetch(f"/api/corporates-financial-results?index=equities&symbol={s}&period=Quarterly",
                            "/companies-listing/corporate-filings-financial-results", 5)
        idx[s] = [{k: r.get(k) for k in ("broadCastDate", "toDate", "consolidated", "xbrl", "audited")}
                  for r in d] if isinstance(d, list) else None
        IDX.write_text(json.dumps(idx))
        time.sleep(0.8)
    return idx


def pat_from_xbrl(url, cache):
    if url in cache:
        return cache[url]
    try:
        t = requests.get(url, headers=_UA, timeout=20).text
        m = re.search(r'<(?:[\w-]+:)?ProfitLossForPeriod contextRef="OneD"[^>]*>([-\d.]+)<', t)
        cache[url] = float(m.group(1)) if m else None
    except Exception:
        cache[url] = None
    XB.write_text(json.dumps(cache))
    time.sleep(0.5)
    return cache[url]


def _d(s, fmt):
    try:
        return datetime.strptime(s, fmt)
    except (TypeError, ValueError):
        return None


def pick_filings(rows):
    """One filing per quarter-end: consolidated if present, else standalone."""
    by_q = {}
    for r in rows or []:
        if not r.get("xbrl") or not r.get("toDate"):
            continue
        q = r["toDate"]
        cur = by_q.get(q)
        if cur is None or (r.get("consolidated") == "Consolidated" and cur.get("consolidated") != "Consolidated"):
            by_q[q] = r
    return by_q


def main():
    symbols = [r["symbol"] for r in universe.load()]
    pre = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=730)
    selection, _ = splits.selection_holdout(splits.sessions_in(pre))
    pre, _ = splits.slice_data(pre, {}, selection)
    sessions = [datetime.fromisoformat(d).date() for d in selection]
    lo, hi = sessions[0], sessions[-1]
    print(splits.describe_split("selection", selection), flush=True)

    idx = fetch_index(symbols)
    cache = json.loads(XB.read_text()) if XB.exists() else {}
    per = {w: {"aligned": [], "gap": [], "kinds": {}} for w in WINDOWS}
    n_events = n_dir = 0
    for s in symbols:
        by_q = pick_filings(idx.get(s))
        candles = pre.get(s)
        if not by_q or not candles:
            continue
        times, by_day = build_index(candles)
        for q, r in by_q.items():
            bdt = _d(r["broadCastDate"], "%d-%b-%Y %H:%M:%S")
            if not bdt or not (lo <= bdt.date() <= hi):
                continue
            n_events += 1
            qend = _d(q, "%d-%b-%Y")
            prev_key = next((k for k in by_q if (pk := _d(k, "%d-%b-%Y")) and qend and
                             abs((qend - pk).days - 365) <= 3), None)
            if prev_key is None:
                continue
            pat_now, pat_prev = pat_from_xbrl(r["xbrl"], cache), pat_from_xbrl(by_q[prev_key]["xbrl"], cache)
            if pat_now is None or pat_prev is None or pat_now == pat_prev:
                continue
            sign = 1 if pat_now > pat_prev else -1
            res = returns_for(bdt, candles, times, by_day, sessions)
            if not res:
                continue
            kind, entry_time, rets, gap = res
            n_dir += 1
            for w in WINDOWS:
                if rets.get(w) is not None:
                    per[w]["aligned"].append(rets[w] * sign)
                    per[w]["kinds"][kind] = per[w]["kinds"].get(kind, 0) + 1
            if gap is not None:
                per["close"]["gap"].append(gap * sign)

    results, pvals = {}, []
    for w in WINDOWS:
        a = per[w]["aligned"]
        t = tstat(a)
        results[w] = {"n": len(a), "aligned_mean_bp": round(st.mean(a), 2) if a else None,
                      "t": round(t, 2) if t else None, "kinds": per[w]["kinds"],
                      "share_positive": round(100 * sum(x > 0 for x in a) / len(a), 1) if a else None}
        if len(a) >= 50 and results[w]["aligned_mean_bp"] > HURDLE_BP and (t or 0) > 2:
            pvals.append((w, p_from_t(t, len(a))))
    g = per["close"]["gap"]
    results["gap_aligned_bp_not_tradable"] = {"n": len(g), "mean": round(st.mean(g), 2) if g else None,
                                              "t": round(tstat(g), 2) if tstat(g) else None}
    survivors = sorted(bh_pass(pvals)) if pvals else []
    out = {"selection": [selection[0], selection[-1], len(selection)], "results_events_in_window": n_events,
           "with_direction": n_dir, "hurdle_bp": HURDLE_BP, "results": results, "step2_earned": survivors}
    OUT.write_text(json.dumps(out, indent=1))
    print(f"\nresults events in window {n_events}, with a YoY direction {n_dir}")
    for w in WINDOWS:
        r = results[w]; print(f"{w:<6} n={r['n']:>4} aligned {r['aligned_mean_bp']} bp  t={r['t']}  positive {r['share_positive']}%  {r['kinds']}")
    print("gap (not tradable):", results["gap_aligned_bp_not_tradable"])
    print("step-2 earned:", survivors or "NONE")


if __name__ == "__main__":
    main()
