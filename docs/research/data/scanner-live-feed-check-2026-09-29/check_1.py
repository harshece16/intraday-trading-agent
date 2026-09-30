"""Shadow check of the scanner's live feed during a session. Runs the branch's
scanner in its own process on a throwaway journal, next to a delayed scan from
the same code, and compares both with Kite's quotes taken just before and
after. Places no order and changes nothing in the running engine."""
import json
import logging
import os
import statistics as st
import sys
import time
import urllib.request
from datetime import datetime

import config
import data_provider
import database
import scanner

assert "preview_live.db" in str(database.DB_PATH), database.DB_PATH
OUT = sys.argv[1]


class Count(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage()[:160])


warn = Count()
logging.getLogger("trading_bot").addHandler(warn)

uni = scanner.universe.load()
symbols = [u["symbol"] for u in uni]
now = datetime.now().strftime("%H:%M:%S")
report = {"at": now, "kite_active": data_provider.kite_data_active()}
if not report["kite_active"]:
    json.dump(report, open(OUT, "w"), indent=1)
    print(json.dumps(report))
    raise SystemExit(0)

before = data_provider.kite_quotes(symbols, indices=("NIFTY 50",))
t0 = time.time()
live_scanner = scanner.Scanner(config.SCANNER)
live = live_scanner.run()
live_s = time.time() - t0
after = data_provider.kite_quotes(symbols, indices=("NIFTY 50",))
t0 = time.time()
delayed_scanner = scanner.Scanner({**config.SCANNER, "live_feed": False})
delayed = delayed_scanner.run()
delayed_s = time.time() - t0

A = {r["symbol"]: r for r in live["rows"]}
B = {r["symbol"]: r for r in delayed["rows"]}
both = [s for s in A if s in B]


def bp(a, b):
    return (a / b - 1) * 1e4


def q(xs, p):
    xs = sorted(xs)
    return xs[int(p * (len(xs) - 1))] if xs else None


# 1. the live scan's price against Kite's quotes taken just before and after it
inside = sum(1 for s in A if s in before and s in after
             and min(before[s]["ltp"], after[s]["ltp"]) * 0.999 <= A[s]["ltp"] <= max(before[s]["ltp"], after[s]["ltp"]) * 1.001)
# 2. how stale the delayed feed is, in price and in time
stale_bp = [abs(bp(B[s]["ltp"], after[s]["ltp"])) for s in both if s in after and after[s]["ltp"] > 0]
last_live = {s: live_scanner.intraday[s][-1]["time"] for s in live["active"] if s in live_scanner.intraday}
last_delayed = {s: delayed_scanner.intraday[s][-1]["time"] for s in delayed["active"] if s in delayed_scanner.intraday}
# 3. the gap against NSE's open
gap_truth = {s: (after[s]["open"] / after[s]["prev_close"] - 1) * 100 for s in after if s in A and after[s]["prev_close"] > 0}
gap_live_err = [abs(A[s]["gap_pct"] - gap_truth[s]) for s in gap_truth]
gap_delayed_err = [abs(B[s]["gap_pct"] - gap_truth[s]) for s in gap_truth if s in B]
# 4. relative volume and VWAP
rv_live = [A[s]["rvol"] for s in both if A[s]["rvol"] is not None]
rv_del = [B[s]["rvol"] for s in both if B[s]["rvol"] is not None]
rv_diff = [A[s]["rvol"] - B[s]["rvol"] for s in both if A[s]["rvol"] is not None and B[s]["rvol"] is not None]
vwap_bp = [abs(bp(A[s]["vwap"], B[s]["vwap"])) for s in both if A[s]["vwap"] and B[s]["vwap"]]
# 5. what changes for the engine: sides, scores, exclusions
sides = [(s, B[s]["side"], A[s]["side"]) for s in both if A[s]["side"] != B[s]["side"]]
listed_sides = [x for x in sides if x[0] in live["active"]]
score_diff = [abs(A[s]["score"] - B[s]["score"]) for s in both]
excl = [(s, B[s]["excluded"], A[s]["excluded"]) for s in both if bool(A[s]["excluded"]) != bool(B[s]["excluded"])]
opening = {"live": sum(1 for s in live["active"] if any("opening range" in x["text"] for x in A[s]["reasons"])),
           "delayed": sum(1 for s in delayed["active"] if any("opening range" in x["text"] for x in B[s]["reasons"]))}

report.update({
    "live_scan": {"seconds": round(live_s, 1), "session": live["session_date"], "feed": live["feed"],
                  "scanned": live["scanned"], "active": len(live["active"]), "selection": {k: v for k, v in live["selection"].items() if k != "rule"},
                  "nifty": live["market"]["nifty"], "bias": live["market"]["bias"]},
    "delayed_scan": {"seconds": round(delayed_s, 1), "session": delayed["session_date"], "feed": delayed["feed"],
                     "scanned": delayed["scanned"], "nifty": delayed["market"]["nifty"], "bias": delayed["market"]["bias"]},
    "kite_nifty_after": {k: after["NIFTY 50"][k] for k in ("ltp", "open", "prev_close", "at")},
    "price_inside_the_quotes_before_and_after": [inside, len(A)],
    "delayed_price_off_by_bp": {"median": round(st.median(stale_bp), 1), "p90": round(q(stale_bp, .9), 1), "max": round(max(stale_bp), 1)},
    "last_bar_of_the_list": {"live": sorted(set(v[11:16] for v in last_live.values())), "delayed": sorted(set(v[11:16] for v in last_delayed.values())),
                             "live_bars_fetched_for": len(last_live)},
    "gap_error_against_nse_points": {"live_max": round(max(gap_live_err), 3), "delayed_median": round(st.median(gap_delayed_err), 3),
                                     "delayed_max": round(max(gap_delayed_err), 3),
                                     "delayed_off_by_0_3_or_more": sum(1 for x in gap_delayed_err if x >= 0.3)},
    "relative_volume": {"live_median": round(st.median(rv_live), 2), "delayed_median": round(st.median(rv_del), 2),
                        "live_blank": sum(1 for s in both if A[s]["rvol"] is None),
                        "difference_median": round(st.median(rv_diff), 3), "difference_p10_p90": [round(q(rv_diff, .1), 2), round(q(rv_diff, .9), 2)]},
    "vwap_differs_by_bp": {"median": round(st.median(vwap_bp), 1), "max": round(max(vwap_bp), 1)},
    "sides_that_differ": {"all": len(sides), "on_the_list": listed_sides, "others": [x for x in sides if x not in listed_sides][:10]},
    "score_differs_by": {"median": round(st.median(score_diff), 1), "max": round(max(score_diff), 1)},
    "exclusions_that_differ": excl,
    "list_equal": live["active"] == delayed["active"],
    "opening_range_in_the_reasons_of_listed_stocks": opening,
    "warnings": warn.lines,
    "examples": {s: {"kite_ltp": after[s]["ltp"], "live": {k: A[s][k] for k in ("ltp", "chg_pct", "gap_pct", "rvol", "vwap", "side", "score")},
                     "delayed": {k: B[s][k] for k in ("ltp", "chg_pct", "gap_pct", "rvol", "vwap", "side", "score")}}
                 for s in ("RELIANCE", "HDFCBANK", "TCS", "INFY") if s in A and s in B},
})
json.dump(report, open(OUT, "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in report.items() if k != "examples"}, indent=1, default=str))
print(json.dumps(report["examples"], indent=1))
