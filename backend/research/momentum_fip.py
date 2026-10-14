"""
Frog-in-the-pan tie-break: does filling the momentum book's vacancies with
"continuous-information" winners beat filling them by rank? Stage 0 (look
L56), the trial on the top 200 (trial 204) and its confirmation on ranks
201-400 (look L57).

Pre-registration: docs/research/prereg-fip-tiebreak.md. Every rule here is a
transcription of it, and its commit precedes this file.

Usage (from backend/):
    .venv/bin/python research/momentum_fip.py stage0    # holdings and counts, no return
    .venv/bin/python research/momentum_fip.py trial     # needs a stage 0 that says proceed

The book, the fills, the costs and the statistics are momentum_width.py's,
not copied; only the order vacancies are filled in differs. Writes
docs/research/data/momentum_fip_*.json. Nothing on the live path imports this.
"""

import argparse
import contextlib
import datetime
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

import evaluation  # noqa: E402
import momentum_3i as m3  # noqa: E402
import momentum_width as mw  # noqa: E402

PREREG = "prereg-fip-tiebreak.md"
MIN_RETURNS = 200            # daily returns in the 12-month window, or the name has no ID
SAMPLES = {"S1": "A", "S2": "B"}   # momentum_width's parts: top 200, ranks 201-400
LEDGER = {"stage0": "look L56", "S1": "trial 204", "S2": "look L57"}
N_FAMILY = 11                # trials 118-120, L38, A', B', T3, T4, T5, W and this one
T_FAMILY = 2.838             # two-sided 5%, Bonferroni across eleven
N_PROJECT = 204
COVERAGE_MIN = 0.97
DIFFER_MIN = 2.0             # of 15 holdings, mean over S1's months
STAGE0_FILE = "momentum_fip_stage0.json"


# --- the rule ------------------------------------------------------------------------

def information_discreteness(c, i13, i1):
    """Da, Gurun and Warachka's ID over the score's own 12 months: sign of the
    12-month return times (share of down days - share of up days). Lower means
    the return came in many small steps. None if it cannot be computed."""
    lo, hi = m3.rows_before(c, i13) - 1, m3.rows_before(c, i1)
    if lo < 0:
        return None
    cl = c["close"][lo:hi]
    rets = [cl[j] / cl[j - 1] - 1 for j in range(1, len(cl)) if cl[j - 1] > 0]
    if len(rets) < MIN_RETURNS or cl[-1] == cl[0]:
        return None
    up, down = sum(r > 0 for r in rets), sum(r < 0 for r in rets)
    return (1 if cl[-1] > cl[0] else -1) * (down - up) / len(rets)


class FipOrder:
    """The order vacancies are filled in: names ranked 30 or better by lowest
    ID (ties to the better rank), then those with no ID by rank, then the
    base order below rank 30. Keeps each month's IDs for stage 0."""

    def __init__(self):
        self.ids = {}

    def __call__(self, order, chains, me_idx, months, month):
        pos = months.index(month)
        i13, i1 = me_idx[months[pos - 13]], me_idx[months[pos - 1]]
        top = order[:m3.RANK_KEEP]
        ids = {n: information_discreteness(chains[n], i13, i1) for n in top}
        self.ids[month] = ids
        have = sorted((n for n in top if ids[n] is not None), key=ids.get)   # stable sort keeps rank on ties
        return have + [n for n in top if ids[n] is None] + order[m3.RANK_KEEP:]


# --- the two arms --------------------------------------------------------------------

def arms(part, panel, unis):
    """(base, this rule, IDs by month) for one of momentum_width's parts."""
    sessions, chains, _, _ = panel
    cfg, start = mw.PARTS[part], m3.SELECTION_START
    base = mw.summarise(*mw.simulate(sessions, chains, unis, cfg, m3.CAPITAL, start))
    order = FipOrder()
    fip = mw.summarise(*mw.simulate(sessions, chains, unis, cfg, m3.CAPITAL, start, fill_order=order))
    return base, fip, order.ids


@contextlib.contextmanager
def zero_costs():
    saved = (m3.STT, m3.STAMP_BUY, m3.NSE_TXN, m3.SEBI, m3.DP_PER_SELL)
    m3.STT = m3.STAMP_BUY = m3.NSE_TXN = m3.SEBI = m3.DP_PER_SELL = 0.0
    try:
        yield
    finally:
        m3.STT, m3.STAMP_BUY, m3.NSE_TXN, m3.SEBI, m3.DP_PER_SELL = saved


def gross_difference(part, panel, unis):
    """This rule's monthly return minus the base's with every cost at zero."""
    sessions, chains, _, _ = panel
    free, start = dict(mw.PARTS[part], flat=0.0), m3.SELECTION_START
    with zero_costs():
        b = mw.simulate(sessions, chains, unis, free, m3.CAPITAL, start)[0]
        f = mw.simulate(sessions, chains, unis, free, m3.CAPITAL, start, fill_order=FipOrder())[0]
    return mw.block([x - y for x, y in zip(m3.mrets([s[2] for s in f]), m3.mrets([s[2] for s in b]))])


def spearman(xs, ys):
    """Rank correlation, ordinal ranks."""
    def ranks(v):
        r = [0] * len(v)
        for k, i in enumerate(sorted(range(len(v)), key=v.__getitem__)):
            r[i] = k
        return r
    a, b = ranks(xs), ranks(ys)
    ma, mb = st.mean(a), st.mean(b)
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / den if den else None


def mean_id(summary, ids):
    """Mean ID of the names an arm held, over the name-months that have one."""
    xs = [ids[h["month"]][n] for h in summary["holdings"] for n in h["holdings"]
          if ids.get(h["month"], {}).get(n) is not None]
    return st.mean(xs) if xs else None


def stored(part):
    with open(os.path.join(mw.OUT_DIR, "momentum_width_%s.json" % part)) as fh:
        return json.load(fh)["base"]


# --- stage 0: holdings and counts, no return ------------------------------------------------

def differ(fip, base):
    held = {h["month"]: set(h["holdings"]) for h in base["holdings"]}
    return [len(set(h["holdings"]) - held[h["month"]]) for h in fip["holdings"]]


def stage0_sample(part, panel, unis):
    base, fip, ids = arms(part, panel, unis)
    years = (len(base["months"]) - 1) / 12
    cover = [(sum(v is not None for v in m.values()), len(m)) for m in ids.values()]
    rho, spread = [], []
    for m in ids.values():
        have = [(rank, v) for rank, v in enumerate(m.values()) if v is not None]   # dicts keep rank order
        if len(have) > 2:
            rho.append(spearman([r for r, _ in have], [v for _, v in have]))
            spread.append(st.pstdev([v for _, v in have]))
    d = differ(fip, base)
    return {"part": part, "months": len(base["months"]),
            "parity_with_recorded_holdings": base["holdings"] == stored(part)["holdings"],
            "id_coverage": sum(a for a, _ in cover) / sum(b for _, b in cover),
            "holdings_that_differ": {"mean": st.mean(d), "median": st.median(d), "max": max(d),
                                     "months_identical": sum(x == 0 for x in d)},
            "buys_per_year": {"base": base["strategy_book"]["buys"] / years,
                              "this_rule": fip["strategy_book"]["buys"] / years},
            "rank_correlation_id_with_score_rank_mean": st.mean([r for r in rho if r is not None]),
            "id_sd_across_top_30_mean": st.mean(spread)}


def stage0():
    panel = mw.load_panel()
    unis = mw.universes(panel[0], panel[1], screens=False)
    out = {"prereg": PREREG, "ledger": LEDGER["stage0"],
           "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "samples": {s: stage0_sample(p, panel, unis) for s, p in SAMPLES.items()}}
    s = out["samples"]
    out["gates"] = {"parity": all(v["parity_with_recorded_holdings"] for v in s.values()),
                    "coverage_ge_0_97": all(v["id_coverage"] >= COVERAGE_MIN for v in s.values()),
                    "s1_holdings_differ_ge_2": s["S1"]["holdings_that_differ"]["mean"] >= DIFFER_MIN}
    out["proceed"] = all(out["gates"].values())
    mw._write(STAGE0_FILE, out)
    print(json.dumps(out, indent=1))
    return out


# --- the trial ------------------------------------------------------------------------

def family_bar(fip):
    ex = fip["excess_net"]
    dsr = evaluation.deflated_sharpe_ratio(fip["excess_net_series"], N_FAMILY)
    rule = {"t_ge_2_838": (ex["t"] or 0) >= T_FAMILY and ex["mean_monthly"] > 0,
            "dsr_ge_0_95_at_n_11": (dsr.get("dsr") or 0) >= 0.95,
            "both_halves_positive": (ex["half1"]["mean"] or 0) > 0 and (ex["half2"]["mean"] or 0) > 0,
            "last3_positive": (ex["last3"]["mean"] or 0) > 0,
            "cagr_gap_ge_2pp": fip["cagr_gap_pp"] >= 2.0,
            "round_trips_ge_100": fip["strategy_book"]["sells"] >= 100}
    return rule, dsr


def trial():
    with open(os.path.join(mw.OUT_DIR, STAGE0_FILE)) as fh:
        if not json.load(fh)["proceed"]:
            sys.exit("stage 0 did not say proceed: the trial is withdrawn and is not run")
    panel = mw.load_panel()
    unis = mw.universes(panel[0], panel[1], screens=False)
    out = {"prereg": PREREG, "run_at": datetime.datetime.now().isoformat(timespec="seconds"), "samples": {}}
    for s, part in SAMPLES.items():
        base, fip, ids = arms(part, panel, unis)
        paired = mw.paired_test(fip, base)
        out["samples"][s] = {
            "ledger": LEDGER[s], "part": part, "base": base, "this_rule": fip, "paired_this_rule_minus_base": paired,
            "paired_passes": (paired["t"] or 0) >= mw.T_PAIRED and paired["mean"] > 0,
            "gross_difference": gross_difference(part, panel, unis),
            "mean_id_of_holdings": {"base": mean_id(base, ids), "this_rule": mean_id(fip, ids)}}
    s1 = out["samples"]["S1"]
    rule, dsr = family_bar(s1["this_rule"])
    out.update({"family_bar_s1": rule, "dsr_family_n11": dsr,
                "dsr_project_n204_information": evaluation.deflated_sharpe_ratio(
                    s1["this_rule"]["excess_net_series"], N_PROJECT),
                "pass_rule": {"paired_s1": s1["paired_passes"], "paired_s2": out["samples"]["S2"]["paired_passes"],
                              "family_bar_s1": all(rule.values())}})
    out["PASS"] = all(out["pass_rule"].values())
    mw._write("momentum_fip_trial.json", out)
    keep = ("first_month", "last_month", "strategy", "cagr_gap_pp", "excess_net", "turnover", "strategy_book")
    show = {k: out[k] for k in ("pass_rule", "PASS", "family_bar_s1", "dsr_family_n11", "dsr_project_n204_information")}
    for s, v in out["samples"].items():
        show[s] = {"paired": {k: x for k, x in v["paired_this_rule_minus_base"].items() if k != "series"},
                   "gross_difference": v["gross_difference"], "mean_id_of_holdings": v["mean_id_of_holdings"],
                   "base": {k: v["base"][k] for k in keep}, "this_rule": {k: v["this_rule"][k] for k in keep}}
    print(json.dumps(show, indent=1, default=str))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["stage0", "trial"])
    {"stage0": stage0, "trial": trial}[ap.parse_args().step]()


if __name__ == "__main__":
    main()
