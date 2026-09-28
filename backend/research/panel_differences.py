"""
Every corporate action whose adjustment factor differs between the default
price panel (EQ rows only, what trial 120 and L38 read) and the repaired
panel of #175 (EQ, BE and BZ rows). Asked for by reviewer entry 22 (F2) of
docs/research/prereg-universe-width.md, before part A' runs.

Usage (from backend/):
    .venv/bin/python research/panel_differences.py

Reads the two cached panels and the recorded holdings of trial 120 and L38.
It computes no strategy return. Writes
docs/research/data/momentum_width_panel_differences.json.
"""

import bisect
import collections
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

import momentum_3i as m3  # noqa: E402
import momentum_width as mw  # noqa: E402
import nse_prices  # noqa: E402

OUT = os.path.join(m3.OUT_DIR, "momentum_width_panel_differences.json")
# the ten rows that come from the repaired panel's own reading and bounds
# (amendments 1 and 3): one consolidation, two actions outside the old
# bounds, seven dividend amounts
EXPECTED = (("VERTOZ", "2025-06-25", "consolidation"), ("AURUM", "2020-12-23", "dividend"),
            ("KESORAMIND", "2025-03-10", "demerger"), ("GSKCONS", "2011-03-11", "dividend"),
            ("TULSYAN", "2012-09-20", "dividend"), ("VTMLTD", "2013-02-26", "dividend"),
            ("RAJPALAYAM", "2013-02-27", "dividend"), ("JEYPORE", "2013-02-28", "dividend"),
            ("ITC", "2016-05-30", "dividend"), ("HINDZINC", "2018-03-23", "dividend"))
CAUSES = {
    "reading": "the repaired panel's reading or bounds (amendments 1 and 3)",
    "default_none": "not applied in the default panel: no EQ row on or after the ex-date, or refused on a stale price",
    "repaired_none": "not applied in the repaired panel: refused on the price of the ex-date itself",
    "late": "applied on the ex-date, not at the next EQ row: the stock was in trade-for-trade",
    "previous": "the previous close is a trade-for-trade row's",
    "other": "other",
}
W_FROM, W_TO, W_K = "2014-05", "2025-11", 400


def index(events, chains, sessions, rename):
    out = collections.defaultdict(list)
    for canon, k, kind, f, ex, purpose in events:
        c = chains[canon]
        wide = "ser" in c
        out[(rename(canon), ex, kind)].append({
            "factor": f, "purpose": purpose, "previous_close": c["raw"][k - 1],
            "previous_row_series": nse_prices.WIDE_SERIES[c["ser"][k - 1]] if wide else "EQ",
            "row_series": nse_prices.WIDE_SERIES[c["ser"][k]] if wide else "EQ",
            "applied_on": sessions[c["idx"][k]]})
    return out


def cause_of(key, x, y, expected):
    if key in expected:
        return CAUSES["reading"]
    if not x:
        return CAUSES["default_none"]
    if not y:
        return CAUSES["repaired_none"]
    if x[0]["applied_on"] != y[0]["applied_on"]:
        return CAUSES["late"]
    if abs(x[0]["previous_close"] - y[0]["previous_close"]) > 1e-9:
        return CAUSES["previous"]
    return CAUSES["other"]


def held_near(holdings, chain, ex_date):
    """Did a recorded book hold the chain in the ex-date's month or the month before or after?"""
    months = [h["month"] for h in holdings]
    pos = bisect.bisect_left(months, ex_date[:7])
    return any(chain in holdings[i]["holdings"] for i in (pos - 1, pos, pos + 1) if 0 <= i < len(holdings))


def main():
    old = nse_prices.load()
    new = nse_prices.load(wide=True)
    sessions = new[0]
    unis = mw.universes(sessions, new[1])
    months = sorted(unis)
    top = {m: set(unis[m]["e3i"][:400]) for m in months}
    alias = {s: c for c, names in new[2]["aliases"].items() for s in names}

    def inside(name, date):
        pos = bisect.bisect_left(months, date[:7]) - 1
        return pos >= 0 and name in top[months[pos]]

    recorded = {}
    for part, label in (("A", "trial 120"), ("B", "L38")):
        with open(os.path.join(m3.OUT_DIR, "momentum_3i_part%s.json" % part)) as fh:
            recorded[label] = json.load(fh)["holdings"]

    a = index(old[3], old[1], sessions, lambda x: alias.get(x, x))
    b = index(new[3], new[1], sessions, lambda x: x)
    expected = {(alias.get(s, s), d, k) for s, d, k in EXPECTED}
    rows = []
    for key in sorted(set(a) | set(b)):
        x, y = a.get(key, []), b.get(key, [])
        if sorted(round(e["factor"], 12) for e in x) == sorted(round(e["factor"], 12) for e in y):
            continue
        row = {"chain": key[0], "ex_date": key[1], "kind": key[2], "cause": cause_of(key, x, y, expected),
               "inside_e3i_ranks_1_to_400": inside(key[0], key[1]),
               "held_by_a_recorded_book_that_month_or_next_to_it":
                   [label for label, h in recorded.items() if held_near(h, key[0], key[1])],
               "purpose": (y or x)[0]["purpose"],
               "default": [{k: e[k] for k in ("factor", "previous_close", "applied_on")} for e in x],
               "repaired": [{k: e[k] for k in ("factor", "previous_close", "previous_row_series", "row_series",
                                               "applied_on")} for e in y]}
        if x and y:
            # what a holder is credited with in the repaired panel over and above the default one
            row["repaired_credits_the_holder_with"] = x[0]["factor"] / y[0]["factor"] - 1
        rows.append(row)

    by = collections.defaultdict(collections.Counter)
    for r in rows:
        by[r["cause"]]["all"] += 1
        by[r["cause"]][r["kind"]] += 1
        by[r["cause"]]["inside_e3i_ranks_1_to_400"] += r["inside_e3i_ranks_1_to_400"]

    def spread(xs):
        return {"n": len(xs), "mean": st.mean(xs), "median": st.median(xs), "lowest": min(xs), "highest": max(xs),
                "beyond_10_pct": sum(1 for x in xs if abs(x) > 0.10), "positive": sum(1 for x in xs if x > 0)} if xs else {}

    late = [r for r in rows if r["cause"] == CAUSES["late"] and r["kind"] == "demerger"]
    gaps = [sessions.index(r["default"][0]["applied_on"]) - sessions.index(r["repaired"][0]["applied_on"])
            for r in late if r["inside_e3i_ranks_1_to_400"]]
    renamed = {s: alias[s] for s in old[1] if alias.get(s, s) != s}
    in_w = {new_name: sum(1 for m in months if W_FROM <= m <= W_TO and new_name in unis[m]["ewide"][:W_K])
            for new_name in renamed.values()}
    w_all = w_deep = deepest = 0
    for m in months:
        if W_FROM <= m <= W_TO:
            for name in unis[m]["ewide"][:W_K]:
                w_all += 1
                if unis[m]["rank3i"][name] > 400:
                    w_deep += 1
                    deepest = max(deepest, unis[m]["rank3i"][name])
    late_by = [(sessions.index(r["repaired"][0]["applied_on"]) - bisect.bisect_left(sessions, r["ex_date"]), r)
               for r in rows if r["repaired"]]
    summary = {
        "rows": len(rows), "inside_e3i_ranks_1_to_400": sum(r["inside_e3i_ranks_1_to_400"] for r in rows),
        "by_cause": {k: dict(v) for k, v in by.items()},
        "demergers_applied_late_in_the_default_panel": {
            "inside_ranks_1_to_400": spread([r["repaired_credits_the_holder_with"] for r in late
                                             if r["inside_e3i_ranks_1_to_400"]]),
            "outside": spread([r["repaired_credits_the_holder_with"] for r in late
                               if not r["inside_e3i_ranks_1_to_400"]]),
            "sessions_late_inside_ranks_1_to_400": {"median": st.median(gaps), "max": max(gaps)} if gaps else {}},
        "rows_on_a_name_a_recorded_book_held": [
            {k: r[k] for k in ("chain", "ex_date", "kind", "cause",
                               "held_by_a_recorded_book_that_month_or_next_to_it")}
            | {"repaired_credits_the_holder_with": r.get("repaired_credits_the_holder_with")}
            for r in rows if r["held_by_a_recorded_book_that_month_or_next_to_it"]],
        "applied_more_than_7_sessions_after_the_ex_date_in_the_repaired_panel": sorted(
            [{"chain": r["chain"], "ex_date": r["ex_date"], "kind": r["kind"], "sessions_late": d,
              "inside_e3i_ranks_1_to_400": r["inside_e3i_ranks_1_to_400"]} for d, r in late_by if d > 7],
            key=lambda x: -x["sessions_late"]),
        "chains": {"default": len(old[1]), "repaired": len(new[1]), "renamed_in_the_repaired_panel": renamed,
                   "months_a_renamed_chain_is_inside_w": in_w},
        "w_universe": {"member_months": w_all, "with_an_e3i_rank_above_400": w_deep, "deepest_e3i_rank": deepest,
                       "from": W_FROM, "to": W_TO, "k": W_K},
        "actions_applied": {"default": old[2]["actions_applied"], "repaired": new[2]["actions_applied"]}}
    with open(OUT, "w") as fh:
        json.dump({"what": "Every corporate action whose factor differs between the default panel (what trial 120 "
                           "and L38 read) and the repaired panel. Built from the two cached panels and the "
                           "recorded holdings. No return is read.",
                   "summary": summary, "rows": rows}, fh, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
