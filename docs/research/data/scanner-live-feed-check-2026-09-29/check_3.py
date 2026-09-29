"""How far prices move in the seconds a scan takes, and how old Yahoo's newest
price is against Kite's. Four quote requests and one Yahoo download."""
import json
import statistics as st
import sys
import time
from datetime import datetime

import data_provider
import database
import scanner

assert "preview_live.db" in str(database.DB_PATH), database.DB_PATH
symbols = [u["symbol"] for u in scanner.universe.load()]
tickers = [u["ticker"] if "ticker" in u else u["symbol"] + ".NS" for u in scanner.universe.load()]


def q(xs, p):
    xs = sorted(xs)
    return xs[int(p * (len(xs) - 1))]


def spread(xs):
    return {"median": round(st.median(xs), 1), "p90": round(q(xs, .9), 1), "max": round(max(xs), 1), "n": len(xs)}


def off(a, b):
    return [abs(a[s] / b[s]["ltp"] - 1) * 1e4 for s in a if s in b and b[s]["ltp"] > 0]


t0 = time.time()
snaps = [(0.0, datetime.now().strftime("%H:%M:%S"), data_provider.kite_quotes(symbols, indices=("NIFTY 50",)))]
ta = time.time()
intraday = scanner.download_batch(tickers, "5d", "5m")
tb = time.time()
snaps.append((round(time.time() - t0, 1), datetime.now().strftime("%H:%M:%S"), data_provider.kite_quotes(symbols, indices=("NIFTY 50",))))
for target in (10, 15, 20):
    time.sleep(max(0, target - (time.time() - t0)))
    snaps.append((round(time.time() - t0, 1), datetime.now().strftime("%H:%M:%S"), data_provider.kite_quotes(symbols, indices=("NIFTY 50",))))

yahoo, last_bar = {}, {}
for sym, tk in zip(symbols, tickers):
    c = intraday.get(tk) or intraday.get(sym)
    if c:
        yahoo[sym] = c[-1]["close"]
        last_bar[sym] = c[-1]["time"][11:16]
base = {s: v["ltp"] for s, v in snaps[0][2].items() if s in symbols and v["ltp"] > 0}
out = {"snapshots_at_seconds": [(a, b) for a, b, _ in snaps],
       "yahoo_download": {"from_s": round(ta - t0, 1), "to_s": round(tb - t0, 1), "stocks": len(yahoo),
                          "last_bar": {k: sum(1 for v in last_bar.values() if v == k) for k in sorted(set(last_bar.values()))}},
       "kite_moved_from_the_first_snapshot_bp": {str(a): spread(off(base, snap)) for a, _, snap in snaps[1:]},
       "yahoo_against_kite_bp": {str(a): spread(off(yahoo, snap)) for a, _, snap in snaps},
       "age_of_kite_last_trade_s": None}
ages = []
for s, v in snaps[1][2].items():
    if s in symbols and v.get("last_trade") and v.get("at"):
        try:
            ages.append((datetime.fromisoformat(v["at"]) - datetime.fromisoformat(v["last_trade"])).total_seconds())
        except Exception:
            pass
if ages:
    out["age_of_kite_last_trade_s"] = {"median": st.median(ages), "p90": q(ages, .9), "max": max(ages), "n": len(ages)}
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps(out, indent=1))
