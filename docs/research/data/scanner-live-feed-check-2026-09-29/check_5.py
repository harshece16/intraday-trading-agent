"""After the fix for #196: the same comparison, with the hole filled."""
import json
import logging
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
MAIN = sys.argv[2]
_k = json.load(open(MAIN + "/.dashboard_key.json"))
_k = _k.get("key") or _k.get("api_key") or list(_k.values())[0]


def engine(path):
    req = urllib.request.Request("http://127.0.0.1:8000" + path, headers={"X-Api-Key": _k})
    return json.load(urllib.request.urlopen(req, timeout=20))


lines = []


class H(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            lines.append(record.getMessage()[:160])


logging.getLogger("trading_bot").addHandler(H())
HOLE = ["ABB", "APOLLOHOSP", "BAJAJHLDNG", "BOSCHLTD", "CIPLA", "HCLTECH", "INDIGO", "JINDALSTEL", "NESTLEIND", "SBILIFE",
        "SIEMENS", "TVSMOTOR", "TORNTPHARM", "ULTRACEMCO", "UNITDSPR", "VBL"]
symbols = [u["symbol"] for u in scanner.universe.load()]
t = time.time()
delayed = scanner.Scanner({**config.SCANNER, "live_feed": False}).run()
d_delayed = round(time.time() - t, 1)
t = time.time()
live = scanner.Scanner(config.SCANNER).run()
d_live = round(time.time() - t, 1)
q = data_provider.kite_quotes(symbols, indices=("NIFTY 50",))
eng = engine("/api/scanner")
E = {r["symbol"]: r for r in eng["rows"]}
D = {r["symbol"]: r for r in delayed["rows"]}
L = {r["symbol"]: r for r in live["rows"]}
truth = {s: (q[s]["open"] / q[s]["prev_close"] - 1) * 100 for s in symbols if s in q and q[s]["prev_close"] > 0 and q[s]["open"] > 0}
chg = {s: (q[s]["ltp"] / q[s]["prev_close"] - 1) * 100 for s in truth}


def errs(rows, key, ref):
    e = {s: abs(rows[s][key] - ref[s]) for s in ref if s in rows and rows[s].get(key) is not None}
    return {"median": round(st.median(e.values()), 3), "max": round(max(e.values()), 3),
            "off_by_0_3_or_more": sum(1 for v in e.values() if v >= 0.3),
            "of_them_in_the_16": sum(1 for s, v in e.items() if v >= 0.3 and s in HOLE), "n": len(e)}


rep = {"at": datetime.now().strftime("%H:%M:%S"), "seconds": {"delayed": d_delayed, "live": d_live},
       "daily_completed_from_nse": {"delayed": delayed.get("daily_completed_from_nse"), "live": live.get("daily_completed_from_nse")},
       "feed": live["feed"],
       "gap_error_points": {"engine_now": errs(E, "gap_pct", truth), "delayed_with_fix": errs(D, "gap_pct", truth), "live_with_fix": errs(L, "gap_pct", truth)},
       "day_change_error_points": {"engine_now": errs(E, "chg_pct", chg), "delayed_with_fix": errs(D, "chg_pct", chg), "live_with_fix": errs(L, "chg_pct", chg)},
       "the_16": [{"symbol": s, "nse_gap": round(truth[s], 2), "engine_gap": E[s]["gap_pct"], "delayed_gap": D[s]["gap_pct"], "live_gap": L[s]["gap_pct"],
                   "engine_side": E[s]["side"], "live_side": L[s]["side"], "engine_score": E[s]["score"], "live_score": L[s]["score"],
                   "rs10": [E[s].get("rs10"), L[s].get("rs10")], "atr_pct": [E[s].get("atr_pct"), L[s].get("atr_pct")],
                   "trend": [E[s].get("daily_trend"), L[s].get("daily_trend")], "on_list": s in eng["active"]} for s in HOLE if s in E and s in L and s in D],
       "sides_engine_to_live": [(s, E[s]["side"], L[s]["side"], s in eng["active"]) for s in L if s in E and E[s]["side"] != L[s]["side"]],
       "sides_delayed_to_live": [(s, D[s]["side"], L[s]["side"], s in live["active"]) for s in L if s in D and D[s]["side"] != L[s]["side"]],
       "exclusions_engine_to_live": [(s, E[s].get("excluded"), L[s].get("excluded")) for s in L if s in E and bool(E[s].get("excluded")) != bool(L[s].get("excluded"))],
       "sectors": {"engine": eng.get("sectors"), "live": live.get("sectors")} if False else None,
       "warnings": lines}
json.dump(rep, open(sys.argv[1], "w"), indent=1, default=str)
print(json.dumps(rep, indent=1, default=str))
