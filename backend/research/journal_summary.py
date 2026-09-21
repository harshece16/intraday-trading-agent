"""Entry 5 §A — read-only journal summary.

Opens the journal with SQLite's read-only URI so this cannot write, migrate or
vacuum anything, and never touches the running backend.
"""
import json
import sqlite3
import sys
from pathlib import Path
import time
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
DB = "file:" + str(Path(__file__).resolve().parents[1] / "data/sahab_journal.db") + "?mode=ro"


def day(ts):
    return datetime.fromtimestamp(ts, IST).strftime("%Y-%m-%d")


con = sqlite3.connect(DB, uri=True)
con.row_factory = sqlite3.Row

# ---- 1. mode ----------------------------------------------------------
modes = Counter(r["mode"] for r in con.execute("SELECT mode FROM trades"))
print(f"MODE per leg: {dict(modes)}")

# ---- 2. closed round trips -------------------------------------------
legs = list(con.execute(
    "SELECT ts, symbol, side, quantity, price, mode, reason, realized, realized_gross,"
    " charges, r_multiple, position_id FROM trades ORDER BY ts"))
closed = [l for l in legs if l["r_multiple"] is not None]
print(f"\nlegs={len(legs)}  closed round trips={len(closed)}")

net = sum(l["realized"] for l in closed)
gross = sum(l["realized_gross"] for l in closed)
chg = sum((l["charges"] or 0) for l in legs)
rs = [l["r_multiple"] for l in closed]
wins = [r for r in rs if r > 0]
print(f"net Rs {net:+.2f}   gross Rs {gross:+.2f}   charges(all legs) Rs {chg:.2f}")
print(f"mean R {sum(rs)/len(rs):+.4f}   win rate {100*len(wins)/len(rs):.1f}% ({len(wins)}/{len(rs)})")
print(f"exits: {dict(Counter(l['reason'] for l in closed))}")

print("\nby day:")
byday = defaultdict(list)
for l in closed:
    byday[day(l["ts"])].append(l)
for d in sorted(byday):
    ls = byday[d]
    print(f"  {d}  n={len(ls)}  net Rs {sum(x['realized'] for x in ls):+8.2f}  "
          f"gross Rs {sum(x['realized_gross'] for x in ls):+8.2f}  "
          f"meanR {sum(x['r_multiple'] for x in ls)/len(ls):+.3f}  "
          f"{', '.join(x['symbol'] for x in ls)}")

# ---- 3. the funnel ----------------------------------------------------
REQUIRED_ORDER = ["pattern", "sr", "volume", "dow", "cost", "rrr"]

sessions = defaultdict(lambda: {
    "sides": 0, "checklist_pass": 0, "gate_pass": 0,
    "fail": Counter(), "near": Counter(), "passed_item": Counter(),
    "rrr": [],
})

n_rows = 0
for r in con.execute("SELECT ts, symbol, bull_score, bear_score, entry_threshold, checklist_json"
                     " FROM checklist_evals ORDER BY ts"):
    n_rows += 1
    d = day(r["ts"])
    S = sessions[d]
    try:
        cl = json.loads(r["checklist_json"])
    except (TypeError, json.JSONDecodeError):
        continue
    for side in ("long", "short"):
        s = cl.get(side)
        if not s:
            continue
        S["sides"] += 1
        items = s.get("items") or []
        req = [i for i in items if i.get("required")]
        failing = [i["key"] for i in req if not i.get("ok")]
        for k in failing:
            S["fail"][k] += 1
        for i in req:
            if i.get("ok"):
                S["passed_item"][i["key"]] += 1
        if len(failing) == 1:
            S["near"][failing[0]] += 1
        if not failing:
            S["checklist_pass"] += 1
            score = r["bull_score"] if side == "long" else r["bear_score"]
            thr = r["entry_threshold"]
            if score is not None and thr is not None and score >= thr:
                S["gate_pass"] += 1
        if s.get("rrr") is not None:
            S["rrr"].append(s["rrr"])

print(f"\nchecklist_evals rows read: {n_rows:,}")

tot = {"sides": 0, "checklist_pass": 0, "gate_pass": 0,
       "fail": Counter(), "near": Counter(), "passed_item": Counter(), "rrr": []}
for S in sessions.values():
    tot["sides"] += S["sides"]
    tot["checklist_pass"] += S["checklist_pass"]
    tot["gate_pass"] += S["gate_pass"]
    tot["fail"] += S["fail"]
    tot["near"] += S["near"]
    tot["passed_item"] += S["passed_item"]
    tot["rrr"] += S["rrr"]

sig = list(con.execute("SELECT ts, signal FROM signals ORDER BY ts"))
entries = [l for l in legs if l["r_multiple"] is None]

print("\n=== FUNNEL, ALL TIME ===")
print(f"  side-evaluations            {tot['sides']:>8,}")
for k in REQUIRED_ORDER:
    p = tot["passed_item"].get(k, 0)
    print(f"    passed {k:<10}        {p:>8,}  ({100*p/tot['sides'] if tot['sides'] else 0:5.2f}%)"
          f"   sole blocker in {tot['near'].get(k,0):,} near-misses")
print(f"  all required items passed   {tot['checklist_pass']:>8,}  "
      f"({100*tot['checklist_pass']/tot['sides'] if tot['sides'] else 0:.4f}%)")
print(f"  ...and cleared confidence   {tot['gate_pass']:>8,}")
print(f"  signals recorded            {len(sig):>8,}")
print(f"  orders placed (entries)     {len(entries):>8,}")
print(f"\n  top fail reasons: {tot['fail'].most_common()}")
if tot["rrr"]:
    v = sorted(tot["rrr"])
    print(f"  rrr: n={len(v):,} median={v[len(v)//2]:.3f} "
          f"p90={v[int(len(v)*0.9)]:.3f} max={v[-1]:.3f}")

print("\n=== FUNNEL, LAST 5 SESSIONS ===")
for d in sorted(sessions)[-5:]:
    S = sessions[d]
    print(f"  {d}: sides={S['sides']:,}  checklist_pass={S['checklist_pass']}  "
          f"gate_pass={S['gate_pass']}  top fails={S['fail'].most_common(3)}")

print(f"\nsessions in journal: {len(sessions)} ({min(sessions)} -> {max(sessions)})")
con.close()
