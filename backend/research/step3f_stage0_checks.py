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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--yf", required=True)
    ap.add_argument("--kite", required=True)
    ap.add_argument("--bhav")
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
    if a.out:
        json.dump(result, open(a.out, "w"), indent=1)
    for k, v in result.items():
        print(f"== {k}")
        print(json.dumps({kk: vv for kk, vv in v.items() if kk not in ("symbols_missing", "worst")}, indent=1))
        if "worst" in v:
            print(" worst:", [(r["symbol"], r["corr"], r["corr_ex_corporate_action_days"], r.get("median_level_gap")) for r in v["worst"]])
        if "below_threshold_ex_corporate_action_days" in v:
            print(" below threshold ex-CA:", [(r["symbol"], r.get("corr_ex_corporate_action_days"), r["n"], r.get("median_level_gap")) for r in v["below_threshold_ex_corporate_action_days"]])
        if "symbols_missing" in v:
            print(" missing:", {s: m["months"] for s, m in v["symbols_missing"].items()})


if __name__ == "__main__":
    main()
