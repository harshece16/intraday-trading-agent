"""Second shadow check: time each part of the scan, measure staleness of the
running engine's prices and of the live scan's prices at the same offset from
a Kite quote, and look for Kite's request limit. Read-only against the engine."""
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
OUT, MAIN = sys.argv[1], sys.argv[2]
_k = json.load(open(MAIN + "/.dashboard_key.json"))
_k = _k.get("key") or _k.get("api_key") or list(_k.values())[0]


def engine(path):
    req = urllib.request.Request("http://127.0.0.1:8000" + path, headers={"X-Api-Key": _k})
    return json.load(urllib.request.urlopen(req, timeout=20))


class Count(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.lines = []

    def emit(self, record):
        self.lines.append(datetime.now().strftime("%H:%M:%S ") + record.getMessage()[:160])


warn = Count()
logging.getLogger("trading_bot").addHandler(warn)
spent = {}


def timed(mod, name):
    fn = getattr(mod, name)

    def wrap(*a, **k):
        t = time.time()
        try:
            return fn(*a, **k)
        finally:
            spent[name] = round(spent.get(name, 0) + time.time() - t, 2)
    setattr(mod, name, wrap)


for mod, name in ((data_provider, "kite_quotes"), (data_provider, "get_candles_batch"), (scanner, "download_batch"),
                  (scanner, "load_guards"), (scanner, "complete_daily"), (scanner.news_sentiment, "get_sentiment"),
                  (scanner.fundamentals, "get_fundamentals")):
    try:
        timed(mod, name)
    except AttributeError as exc:
        print("not timed:", name, exc)

symbols = [u["symbol"] for u in scanner.universe.load()]


def hhmmss():
    return datetime.now().strftime("%H:%M:%S")


def bp(a, b):
    return (a / b - 1) * 1e4


def q(xs, p):
    xs = sorted(xs)
    return xs[int(p * (len(xs) - 1))] if xs else None


def spread(xs):
    return {"median": round(st.median(xs), 1), "p90": round(q(xs, .9), 1), "max": round(max(xs), 1), "n": len(xs)}


def run(cfg):
    spent.clear()
    t = time.time()
    sc = scanner.Scanner(cfg)
    res = sc.run()
    return sc, res, round(time.time() - t, 1), dict(spent)


report = {"kite_active": data_provider.kite_data_active(), "started": hhmmss()}
assert report["kite_active"]

# A. a live scan in a new process (nothing cached), then a delayed one, then
#    the live one again with everything cached.
s1, live1, d1, parts1 = run(config.SCANNER)
_, delayed1, d2, parts2 = run({**config.SCANNER, "live_feed": False})
report["durations"] = {"live_first_scan_of_a_process": {"seconds": d1, "parts": parts1},
                       "delayed_after_it": {"seconds": d2, "parts": parts2},
                       "engine_running_now": None}

# B. wait for the engine's next scan, read Kite at that moment, then scan live.
first = engine("/api/scanner")
report["durations"]["engine_running_now"] = first.get("duration_s")
seen, waited = first["ts"], 0
while waited < 330:
    time.sleep(2)
    waited += 2
    now = engine("/api/scanner")
    if now["ts"] != seen:
        break
else:
    now = first
q_engine = data_provider.kite_quotes(symbols, indices=("NIFTY 50",))
t_engine = hhmmss()
s3, live3, d3, parts3 = run(config.SCANNER)
q_live = data_provider.kite_quotes(symbols, indices=("NIFTY 50",))
t_live = hhmmss()
report["durations"]["live_with_everything_cached"] = {"seconds": d3, "parts": parts3}

E = {r["symbol"]: r for r in now["rows"]}
L = {r["symbol"]: r for r in live3["rows"]}
report["engine_scan"] = {"finished": datetime.fromtimestamp(now["ts"]).strftime("%H:%M:%S"), "quotes_read": t_engine,
                         "waited_s": waited, "session": now["session_date"], "rows": len(E), "list": len(now["active"])}
report["live_scan"] = {"feed": live3["feed"], "quotes_read_after": t_live, "session": live3["session_date"], "rows": len(L),
                       "nifty": live3["market"]["nifty"], "engine_nifty": now["market"]["nifty"]}

# staleness: each scan's price against a Kite quote read right after it
report["engine_price_off_by_bp"] = spread([abs(bp(E[s]["ltp"], q_engine[s]["ltp"])) for s in E if s in q_engine and q_engine[s]["ltp"] > 0])
report["live_price_off_by_bp"] = spread([abs(bp(L[s]["ltp"], q_live[s]["ltp"])) for s in L if s in q_live and q_live[s]["ltp"] > 0])
truth = {s: (q_live[s]["open"] / q_live[s]["prev_close"] - 1) * 100 for s in q_live if s in symbols and q_live[s]["prev_close"] > 0 and q_live[s]["open"] > 0}
ge = {s: abs(E[s]["gap_pct"] - truth[s]) for s in truth if s in E and E[s].get("gap_pct") is not None}
gl = {s: abs(L[s]["gap_pct"] - truth[s]) for s in truth if s in L and L[s].get("gap_pct") is not None}
worst = sorted(ge, key=lambda s: -ge[s])[:6]
report["gap_error_points"] = {
    "engine": {"median": round(st.median(ge.values()), 3), "max": round(max(ge.values()), 3), "off_by_0_3_or_more": sum(1 for v in ge.values() if v >= 0.3),
               "off_by_0_3_or_more_on_its_list": sum(1 for s, v in ge.items() if v >= 0.3 and s in now["active"]), "n": len(ge)},
    "live": {"median": round(st.median(gl.values()), 3), "max": round(max(gl.values()), 3), "off_by_0_3_or_more": sum(1 for v in gl.values() if v >= 0.3), "n": len(gl)},
    "worst_engine_rows": [{"symbol": s, "nse_gap": round(truth[s], 2), "engine_gap": E[s]["gap_pct"], "live_gap": L.get(s, {}).get("gap_pct"),
                           "on_list": s in now["active"]} for s in worst]}
vw = {s: abs(bp(L[s]["vwap"], q_live[s]["vwap"])) for s in L if s in q_live and L[s].get("vwap") and q_live[s].get("vwap")}
ve = {s: abs(bp(E[s]["vwap"], q_engine[s]["vwap"])) for s in E if s in q_engine and E[s].get("vwap") and q_engine[s].get("vwap")}
report["vwap_off_nse_by_bp"] = {"engine": spread(list(ve.values())), "live": spread(list(vw.values()))}
both = [s for s in L if s in E]
rv = [L[s]["rvol"] - E[s]["rvol"] for s in both if L[s].get("rvol") is not None and E[s].get("rvol") is not None]
report["relative_volume"] = {"live_median": round(st.median([L[s]["rvol"] for s in both if L[s].get("rvol") is not None]), 2),
                             "engine_median": round(st.median([E[s]["rvol"] for s in both if E[s].get("rvol") is not None]), 2),
                             "difference_p10_median_p90": [round(q(rv, .1), 2), round(st.median(rv), 2), round(q(rv, .9), 2)],
                             "live_blank": sum(1 for s in L if L[s].get("rvol") is None)}
sides = [(s, E[s]["side"], L[s]["side"], s in now["active"]) for s in both if E[s]["side"] != L[s]["side"]]
report["sides_that_differ_engine_to_live"] = sides
sd = [abs(L[s]["score"] - E[s]["score"]) for s in both]
report["score_differs_by"] = {"median": round(st.median(sd), 1), "p90": round(q(sd, .9), 1), "max": round(max(sd), 1)}
report["exclusions_that_differ"] = [(s, E[s].get("excluded"), L[s].get("excluded")) for s in both if bool(E[s].get("excluded")) != bool(L[s].get("excluded"))]
report["list"] = {"engine_only": sorted(set(now["active"]) - set(live3["active"])), "shadow_only": sorted(set(live3["active"]) - set(now["active"])),
                  "note": "The shadow fixed its list at its own first scan this afternoon, the engine at 09:15."}
report["guards"] = live3.get("guards")
report["selection"] = {k: v for k, v in live3["selection"].items() if k != "rule"}
listed = [s for s in live3["active"] if s in s3.intraday]
report["bars_of_the_list"] = {"listed": len(live3["active"]), "with_bars": len(listed),
                              "from_kite": sum(1 for s in listed if not s3.intraday[s][-1].get("delayed")),
                              "fell_back_to_delayed": [s for s in listed if s3.intraday[s][-1].get("delayed")],
                              "last_bar": sorted(set(s3.intraday[s][-1]["time"][11:16] for s in listed)),
                              "opening_range_known": sum(1 for s in live3["active"] if any("pening range" in x["text"] for x in L[s]["reasons"]))}
report["rows_by_feed"] = {f: sum(1 for r in live3["rows"] if r.get("feed") == f) for f in ("live", "delayed")}
report["warnings"] = warn.lines
act = engine("/api/activity?limit=200")
act = act if isinstance(act, list) else act.get("activity", act.get("items", []))
hits = [a for a in act if any(w in json.dumps(a) for w in ("Too many requests", "falling back", "429"))]
report["engine_activity_mentions_of_the_request_limit"] = len(hits)
report["finished"] = hhmmss()
json.dump(report, open(OUT, "w"), indent=1, default=str)
print(json.dumps(report, indent=1, default=str))
