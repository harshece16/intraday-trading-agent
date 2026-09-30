"""Name the rows whose live price sits away from Kite's quotes read just
before and just after the scan."""
import json
import logging
import sys
import time
from datetime import datetime

import config
import data_provider
import database
import scanner

assert "preview_live.db" in str(database.DB_PATH), database.DB_PATH
lines = []


class H(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            lines.append(record.getMessage()[:160])


logging.getLogger("trading_bot").addHandler(H())
symbols = [u["symbol"] for u in scanner.universe.load()]
before = data_provider.kite_quotes(symbols, indices=("NIFTY 50",))
t0 = time.time()
sc = scanner.Scanner(config.SCANNER)
res = sc.run()
took = round(time.time() - t0, 1)
after = data_provider.kite_quotes(symbols, indices=("NIFTY 50",))
rows = {r["symbol"]: r for r in res["rows"]}
out = []
for s, r in rows.items():
    b, a = before[s], after[s]
    lo, hi = min(b["ltp"], a["ltp"], b["low"], a["low"]), max(b["ltp"], a["ltp"])
    d_b, d_a = (r["ltp"] / b["ltp"] - 1) * 1e4, (r["ltp"] / a["ltp"] - 1) * 1e4
    out.append({"symbol": s, "row": r["ltp"], "before": b["ltp"], "after": a["ltp"], "bp_from_before": round(d_b, 1), "bp_from_after": round(d_a, 1),
                "between": min(b["ltp"], a["ltp"]) <= r["ltp"] <= max(b["ltp"], a["ltp"]), "on_list": s in res["active"], "feed": r.get("feed"),
                "last_trade_before": (b.get("last_trade") or "")[11:19], "last_trade_after": (a.get("last_trade") or "")[11:19]})
out.sort(key=lambda x: -min(abs(x["bp_from_before"]), abs(x["bp_from_after"])))
rep = {"at": datetime.now().strftime("%H:%M:%S"), "seconds": took, "feed": res["feed"], "between_the_two_quotes": sum(1 for x in out if x["between"]),
       "within_3bp_of_either": sum(1 for x in out if min(abs(x["bp_from_before"]), abs(x["bp_from_after"])) <= 3),
       "furthest": out[:8], "listed_bars_from_kite": sum(1 for s in res["active"] if s in sc.intraday and not sc.intraday[s][-1].get("delayed")),
       "warnings": lines}
json.dump(rep, open(sys.argv[1], "w"), indent=1)
print(json.dumps(rep, indent=1))
