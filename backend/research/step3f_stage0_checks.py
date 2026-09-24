"""
3f stage 0 — the two data gates, coded as halts. RESEARCH ONLY; reads no forward return.

  0b coverage  — of the member-months from the start month through 2025-12, how many
                 have an adjusted close on the signal date (the last session of the
                 month)? Gate: >= 95%.
  0c vendor    — over 2024-09-20..2025-12-31, the correlation of daily close-to-close
                 returns between yfinance and a second source, per stock. Gate as
                 pre-registered: >= 0.98 for >= 95% of stocks, the second source being
                 the Kite 5-minute cache's last bar. A third comparison against the NSE
                 bhavcopy's official close (the primary source) is reported alongside,
                 because the last bar of the day is a last trade, not the official close.

Inputs are sqlite files built outside the repo (none is committed):
  --yf     daily(symbol, date, open, high, low, close, adj_close, volume)  from yfinance,
           auto_adjust=False, one ticker per symbol as <SYMBOL>.NS
  --kite   kite_close(symbol, date, close, bar_time)  the last 5m bar per session from
           backend/data/kite_history.db, read-only
  --bhav   bhav(symbol, date, close, last, prev_close, ...)  EQ rows of NSE's daily
           BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip
  --bhav-monthend  the same for every month-end session 2009-01..2025-12 plus a
           fetched(month, date, rows, http) table — amendment 3's level test
  --membership  research/data/nifty100_membership_monthly.csv

Usage:
  python research/step3f_stage0_checks.py --yf yf_daily.db --kite kite_close.db [--bhav bhav.db]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
START, END = "2010-01", "2025-12"
VENDOR_FROM, VENDOR_TO = "2024-09-20", "2025-12-31"


def corr(a, b):
    n = len(a)
    if n < 20:
        return float("nan")
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return sum((x - ma) * (z - mb) for x, z in zip(a, b)) / (sa * sb) if sa and sb else float("nan")


def median(xs):
    xs = sorted(x for x in xs if x == x)
    return xs[len(xs) // 2] if xs else float("nan")


def coverage(yf_db, membership_csv, start=START, end=END):
    mem = collections.defaultdict(list)
    for r in csv.DictReader(open(membership_csv)):
        if start <= r["month"] <= end:
            mem[r["month"]].append(r["symbol"])
    have = collections.defaultdict(set)
    for s, d in yf_db.execute("select symbol, date from daily where adj_close > 0"):
        have[s].add(d)
    cal = sorted({d for s in have for d in have[s]})
    by_month_end = {}
    for d in cal:
        by_month_end[d[:7]] = d  # last session of each month
    total = ok = 0
    by_year = collections.defaultdict(lambda: [0, 0])
    missing = collections.defaultdict(list)
    for mo, syms in sorted(mem.items()):
        sig = by_month_end[mo]
        for s in syms:
            total += 1
            by_year[mo[:4]][1] += 1
            if sig in have[s]:
                ok += 1
                by_year[mo[:4]][0] += 1
            else:
                missing[s].append(mo)
    return {
        "member_months": total, "covered": ok, "pct": round(100 * ok / total, 2), "gate": ok / total >= 0.95,
        "by_year": {y: f"{a}/{b} ({100 * a / b:.1f}%)" for y, (a, b) in sorted(by_year.items())},
        "by_half": {
            "2010-2017": _half(by_year, lambda y: y <= "2017"),
            "2018-2025": _half(by_year, lambda y: y >= "2018"),
        },
        "symbols_missing": {s: {"months": len(ms), "first": ms[0], "last": ms[-1]}
                            for s, ms in sorted(missing.items(), key=lambda kv: -len(kv[1]))},
    }


def _half(by_year, pred):
    a = sum(v[0] for y, v in by_year.items() if pred(y))
    b = sum(v[1] for y, v in by_year.items() if pred(y))
    return f"{a}/{b} ({100 * a / b:.1f}%)"


def _series(db, sql):
    out = collections.defaultdict(dict)
    for s, d, c in db.execute(sql):
        if c:
            out[s][d] = c
    return out


def vendor(yf_db, other, label, price_col="close", threshold=0.98, other_returns=None):
    """Per-stock correlation of close-to-close returns, yfinance `price_col` vs `other`.
    `other_returns[symbol][date]` overrides the second source's daily return (the
    bhavcopy is unadjusted, but NSE's own PrvsClsgPric is adjusted on ex-dates, so
    ClsPric/PrvsClsgPric is the exchange's adjusted return for the day)."""
    yf = _series(yf_db, f"select symbol, date, {price_col} from daily where date between '{VENDOR_FROM}' and '{VENDOR_TO}'")
    rows = []
    for s in sorted(other):
        if s not in yf:
            rows.append({"symbol": s, "n": 0, "corr": None, "note": "no yfinance data"})
            continue
        ds = sorted(set(yf[s]) & set(other[s]))
        ra = [yf[s][d1] / yf[s][d0] - 1 for d0, d1 in zip(ds, ds[1:])]
        if other_returns:
            rb = [other_returns[s].get(d1, other[s][d1] / other[s][d0] - 1) for d0, d1 in zip(ds, ds[1:])]
        else:
            rb = [other[s][d1] / other[s][d0] - 1 for d0, d1 in zip(ds, ds[1:])]
        level = [abs(yf[s][d] / other[s][d] - 1) for d in ds]
        # a split or bonus is adjusted by one source and not the other: one day with a >20% return gap.
        ca = [d1 for d0, d1, x, z in zip(ds, ds[1:], ra, rb) if abs(x - z) > 0.2]
        ra_x = [x for x, z in zip(ra, rb) if abs(x - z) <= 0.2]
        rb_x = [z for x, z in zip(ra, rb) if abs(x - z) <= 0.2]
        rows.append({"symbol": s, "n": len(ds), "corr": round(corr(ra, rb), 4),
                     "corr_ex_corporate_action_days": round(corr(ra_x, rb_x), 4), "corporate_action_days": ca,
                     "median_level_gap": round(median(level), 5), "max_level_gap": round(max(level), 4) if level else None})
    good = [r for r in rows if r["corr"] is not None and r["corr"] >= threshold]
    good_x = [r for r in rows if r["corr"] is not None and r["corr_ex_corporate_action_days"] >= threshold]
    return {
        "comparison": label, "stocks": len(rows), f"corr_ge_{threshold}": len(good),
        "pct": round(100 * len(good) / len(rows), 1), "gate": len(good) / len(rows) >= 0.95,
        "median_corr": round(median([r["corr"] for r in rows if r["corr"] is not None]), 4),
        f"ex_corporate_action_days_corr_ge_{threshold}": len(good_x),
        "ex_corporate_action_days_pct": round(100 * len(good_x) / len(rows), 1),
        "corporate_action_days_total": sum(len(r.get("corporate_action_days", [])) for r in rows),
        "worst": sorted([r for r in rows if r["corr"] is not None], key=lambda r: r["corr"])[:12],
        "below_threshold_ex_corporate_action_days": sorted(
            [r for r in rows if r["corr"] is None or r["corr_ex_corporate_action_days"] < threshold],
            key=lambda r: r.get("corr_ex_corporate_action_days") or -1),
    }


def level_test(yf_db, bhav_me_db, membership_csv, tolerance=0.0006, start=START, end=END):
    """Amendment 3: every member's yfinance Close on every signal date vs NSE's official
    close; a miss or a gap > tolerance is 'missing'; the 95% coverage gate re-applied."""
    mem = collections.defaultdict(list)
    for r in csv.DictReader(open(membership_csv)):
        if start <= r["month"] <= end:
            mem[r["month"]].append(r["symbol"])
    yf = _series(yf_db, "select symbol, date, close from daily where date >= '2009-01-01'")
    off = _series(bhav_me_db, "select symbol, date, close from bhav")
    fetched = {m: d for m, d in bhav_me_db.execute("select month, date from fetched where http = '200'")}
    yf_month_end = {}
    for s in yf:
        for d in yf[s]:
            if d[:7] >= "2009-01":
                yf_month_end[d[:7]] = max(yf_month_end.get(d[:7], ""), d)
    calendar_mismatch = {m: (yf_month_end[m], fetched[m]) for m in fetched if m in yf_month_end and yf_month_end[m] != fetched[m]}
    total = exist = match = 0
    by_year = collections.defaultdict(lambda: [0, 0, 0])
    mismatches = []
    for mo, syms in sorted(mem.items()):
        d = fetched.get(mo)
        if not d:
            continue
        for s in syms:
            total += 1
            by_year[mo[:4]][2] += 1
            y = yf[s].get(d)
            if y is None and mo in calendar_mismatch:
                y = yf[s].get(calendar_mismatch[mo][0])  # yfinance's row sits on its own (non-session) date
            if y is None or s not in off or d not in off[s]:
                mismatches.append({"month": mo, "symbol": s, "yf": y, "nse": off.get(s, {}).get(d), "reason": "absent"})
                continue
            exist += 1
            by_year[mo[:4]][1] += 1
            gap = abs(y / off[s][d] - 1)
            if gap <= tolerance:
                match += 1
                by_year[mo[:4]][0] += 1
            else:
                mismatches.append({"month": mo, "symbol": s, "yf": round(y, 2), "nse": off[s][d], "gap_bp": round(gap * 1e4, 1), "reason": "gap"})
    gaps = [m for m in mismatches if m["reason"] == "gap"]
    return {
        "tolerance_bp": tolerance * 1e4, "months_with_bhavcopy": len(fetched), "member_months": total,
        "close_exists": exist, "exists_and_matches": match, "pct_match": round(100 * match / total, 2),
        "gate_95pct": match / total >= 0.95,
        "by_year": {y: f"match {a}/{c} ({100 * a / c:.1f}%), exists {b}/{c}" for y, (a, b, c) in sorted(by_year.items())},
        "gap_mismatches": len(gaps), "absent": len(mismatches) - len(gaps),
        "gap_by_symbol": dict(collections.Counter(m["symbol"] for m in gaps).most_common(20)),
        "gap_bp_distribution": {"median": median([m["gap_bp"] for m in gaps]) if gaps else None,
                                 "over_50bp": sum(1 for m in gaps if m["gap_bp"] > 50)},
        "yfinance_month_end_not_an_nse_session": calendar_mismatch,
        "mismatches": mismatches,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--yf", required=True)
    ap.add_argument("--kite", required=True)
    ap.add_argument("--bhav")
    ap.add_argument("--bhav-monthend", help="bhav(symbol, date, close, ...) + fetched(month, date, rows, http) for every signal date, amendment 3")
    ap.add_argument("--membership", default=os.path.join(HERE, "data", "nifty100_membership_monthly.csv"))
    ap.add_argument("--out", default=None, help="write the full JSON here")
    a = ap.parse_args()
    yf_db = sqlite3.connect(a.yf)
    result = {"coverage_0b": coverage(yf_db, a.membership)}
    kite = _series(sqlite3.connect(a.kite),
                   f"select symbol, date, close from kite_close where date between '{VENDOR_FROM}' and '{VENDOR_TO}'")
    result["vendor_0c_preregistered"] = vendor(yf_db, kite, "yfinance Close vs Kite cache last 5m bar (as pre-registered)")
    result["vendor_0c_kite_vs_adj_close"] = vendor(yf_db, kite, "yfinance Adj Close vs Kite cache last 5m bar", price_col="adj_close")
    if a.bhav:
        bdb = sqlite3.connect(a.bhav)
        bhav = _series(bdb, f"select symbol, date, close from bhav where date between '{VENDOR_FROM}' and '{VENDOR_TO}'")
        result["vendor_0c_bhavcopy_raw"] = vendor(yf_db, bhav, "yfinance Close vs NSE bhavcopy official close, raw (unadjusted on ex-dates)")
        nse_ret = collections.defaultdict(dict)
        for s_, d_, c_, pc_ in bdb.execute(f"select symbol, date, close, prev_close from bhav where date between '{VENDOR_FROM}' and '{VENDOR_TO}'"):
            if c_ and pc_:
                nse_ret[s_][d_] = c_ / pc_ - 1
        result["vendor_0c_bhavcopy"] = vendor(yf_db, bhav, "yfinance Close vs NSE bhavcopy official close, NSE's own ClsPric/PrvsClsgPric return (primary source)", other_returns=nse_ret)
        last = _series(bdb, f"select symbol, date, last from bhav where date between '{VENDOR_FROM}' and '{VENDOR_TO}'")
        # is the cache's last bar the last trade of the day? compare Kite vs bhavcopy LastPric, dividend offsets aside
        kd = sqlite3.connect(":memory:")
        kd.execute("create table daily(symbol, date, close)")
        kd.executemany("insert into daily values (?,?,?)", [(s, d, c) for s in kite for d, c in kite[s].items()])
        result["kite_vs_bhavcopy_close"] = vendor(kd, bhav, "Kite cache last 5m bar vs NSE bhavcopy official close (NSE adjusted return)", other_returns=nse_ret)
    if a.bhav_monthend:
        result["level_test_amendment3"] = level_test(yf_db, sqlite3.connect(a.bhav_monthend), a.membership)
    if a.out:
        json.dump(result, open(a.out, "w"), indent=1)
    for k, v in result.items():
        print(f"== {k}")
        print(json.dumps({kk: vv for kk, vv in v.items() if kk not in ("symbols_missing", "worst", "below_threshold_ex_corporate_action_days", "mismatches")}, indent=1))
        if "worst" in v:
            print(" worst:", [(r["symbol"], r["corr"], r["corr_ex_corporate_action_days"], r.get("median_level_gap")) for r in v["worst"]])
        if "below_threshold_ex_corporate_action_days" in v:
            print(" below threshold ex-CA:", [(r["symbol"], r.get("corr_ex_corporate_action_days"), r["n"], r.get("median_level_gap")) for r in v["below_threshold_ex_corporate_action_days"]])
        if "symbols_missing" in v:
            print(" missing:", {s: m["months"] for s, m in v["symbols_missing"].items()})


if __name__ == "__main__":
    main()
