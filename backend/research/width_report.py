"""
What the panel differences and the demerger residuals touched in each book
of the universe-width test (prereg-universe-width.md, amendment 4 section
8). Reads the saved outputs, the panel-difference list and the stage-0 jump
list. It re-runs nothing and computes no new return.

Usage (from backend/):
    .venv/bin/python research/width_report.py

Writes docs/research/data/momentum_width_report.json.
"""

import bisect
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

import momentum_3i as m3  # noqa: E402
import nse_prices  # noqa: E402

N_HOLD = m3.N_HOLD
AFTER = 10              # sessions after the ex-date
BOUGHT_WITHIN = 12      # months after a residual jump
PARTS = ("A", "B", "W")


def load(name):
    with open(os.path.join(m3.OUT_DIR, name)) as fh:
        return json.load(fh)


def held_on(holdings, fills, sessions, first, last):
    """The months whose holdings were in the book on any session from first to last.
    holdings[i] is the book after the fill of fills[i]; it stands until fills[i + 1]."""
    out = []
    for i, h in enumerate(holdings):
        start = fills[i]
        end = fills[i + 1] - 1 if i + 1 < len(fills) else len(sessions) - 1
        if start <= last and end >= first:
            out.append(h)
    return out


def main():
    sessions = nse_prices.load(wide=True)[0]
    diff = load("momentum_width_panel_differences.json")["rows"]
    jumps = load("momentum_width_stage0_run2.json")["jumps"]
    residuals = [j for j in jumps if any("rrangement" in p or "emerger" in p for _, p in j["actions_in_nse_file"])]
    me = dict(m3.month_ends(sessions))
    report = {}
    for part in PARTS:
        out = load("momentum_width_%s.json" % part)
        if not out.get("testable"):
            report[part] = {"testable": False}
            continue
        holdings = out["base"]["holdings"]
        fills = [me[h["month"]] + 1 for h in holdings]
        touched = []
        for r in diff:
            first = bisect.bisect_left(sessions, r["ex_date"])
            months = [h["month"] for h in held_on(holdings, fills, sessions, first, first + AFTER)
                      if r["chain"] in h["holdings"]]
            if months:
                credit = r.get("repaired_credits_the_holder_with")
                touched.append({"chain": r["chain"], "ex_date": r["ex_date"], "kind": r["kind"], "cause": r["cause"],
                                "held_after_the_rebalance_of": months,
                                "difference_on_the_name": credit,
                                "points_on_the_book": None if credit is None else 100 * credit / N_HOLD,
                                "default": r["default"], "repaired": r["repaired"]})
        resid = []
        for j in residuals:
            day = sessions.index(j["date"])
            held = [h["month"] for h in held_on(holdings, fills, sessions, day, day) if j["symbol"] in h["holdings"]]
            month = j["date"][:7]
            year, mon = int(month[:4]), int(month[5:])
            limit = "%04d-%02d" % (year + (mon + BOUGHT_WITHIN - 1) // 12, (mon + BOUGHT_WITHIN - 1) % 12 + 1)
            later = [h["month"] for h in holdings if month <= h["month"] <= limit and j["symbol"] in h["holdings"]]
            resid.append({"symbol": j["symbol"], "date": j["date"], "adjusted_return": j["adjusted_return"],
                          "held_on_the_day": bool(held), "in_the_book_within_12_months_after": later})
        report[part] = {"ledger": out.get("ledger"), "actions_on_a_held_name": touched,
                        "actions_on_a_held_name_beyond_a_tenth_of_a_point":
                            [t for t in touched if t["points_on_the_book"] is None
                             or abs(t["points_on_the_book"]) >= 0.1],
                        "demerger_residuals": resid,
                        "consolidations_on_a_held_name": [c for c in out.get("consolidations_applied", [])
                                                          if c["held_by_this_book"]]}
    with open(os.path.join(m3.OUT_DIR, "momentum_width_report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    for part, r in report.items():
        if not r.get("actions_on_a_held_name"):
            print(part, r)
            continue
        print(part, r["ledger"], "actions on a held name:", len(r["actions_on_a_held_name"]))
        for t in r["actions_on_a_held_name_beyond_a_tenth_of_a_point"]:
            print("  ", t["chain"], t["ex_date"], t["kind"], t["difference_on_the_name"], t["points_on_the_book"])
        print("   residuals held or bought:", [(x["symbol"], x["date"], x["held_on_the_day"],
                                                 x["in_the_book_within_12_months_after"]) for x in
                                                r["demerger_residuals"]
                                                if x["held_on_the_day"] or x["in_the_book_within_12_months_after"]])


if __name__ == "__main__":
    main()
