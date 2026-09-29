"""The scanner and a tick's bar fetch at the same moment in one process, as
they will run in the engine: does the shared spacing hold against Kite?"""
import json
import logging
import sys
import threading
import time
from datetime import datetime

import config
import data_provider
import database
import scanner

assert "preview_live.db" in str(database.DB_PATH), database.DB_PATH
lines, starts = [], []


class H(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            lines.append(record.getMessage()[:160])


logging.getLogger("trading_bot").addHandler(H())
inner = data_provider._wait_for_kite_historical


def counted(*a, **k):
    inner(*a, **k)                    # returns when the request may go
    starts.append(time.monotonic())


data_provider._wait_for_kite_historical = counted
sc = scanner.Scanner(config.SCANNER)
first = sc.run()                      # fills the caches; its list is the watchlist
watch = list(first["active"])
starts.clear()
out = {}


def tick():
    t = time.time()
    got = data_provider.get_candles_batch(watch, interval="5m", period="5d")
    out["tick"] = {"seconds": round(time.time() - t, 1), "symbols": len(got),
                   "from_kite": sum(1 for c in got.values() if c and not c[-1].get("delayed"))}


def scan():
    t = time.time()
    res = sc.run()
    listed = [s for s in res["active"] if s in sc.intraday]
    out["scan"] = {"seconds": round(time.time() - t, 1), "feed": res["feed"]["prices"], "rows_live": res["feed"]["rows_live"],
                   "listed_bars_from_kite": sum(1 for s in listed if not sc.intraday[s][-1].get("delayed"))}


alone = time.time()
tick()
out["tick_alone"] = dict(out.pop("tick"))
n_alone = len(starts)
starts.clear()
a, b = threading.Thread(target=scan), threading.Thread(target=tick)
a.start()
time.sleep(4.5)                        # the scan's downloads take about 5 s before its bar requests
b.start()
a.join()
b.join()
gaps = sorted(y - x for x, y in zip(sorted(starts), sorted(starts)[1:]))
out.update({"at": datetime.now().strftime("%H:%M:%S"), "requests_alone": n_alone, "requests_together": len(starts),
            "gap_between_request_starts_s": {"smallest": round(gaps[0], 3), "median": round(gaps[len(gaps) // 2], 3), "largest": round(gaps[-1], 2)},
            "most_in_any_one_second": max(sum(1 for y in starts if 0 <= y - x < 1.0) for x in starts),
            "warnings": lines})
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps(out, indent=1))
