"""
3i — slow momentum in delivery on corrected NSE data (trial 120) and an
unseen-stock confirmation (L38). Pre-registration:
docs/research/prereg-3i-momentum-corrected-data.md — every rule here is a
transcription of it, and its commit precedes this file's.

Usage (from backend/):
    .venv/bin/python research/momentum_3i.py stage0          # data gate, no returns
    .venv/bin/python research/momentum_3i.py partA           # trial 120
    .venv/bin/python research/momentum_3i.py partB           # L38 confirmation
    .venv/bin/python research/momentum_3i.py heldout         # only after A passes and B confirms

Prices come from research/nse_prices.py (official corporate actions,
dividends, fund units excluded). Writes docs/research/data/momentum_3i_*.json.
Nothing on the live path imports this.
"""

import argparse
import bisect
import collections
import datetime
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

import evaluation  # noqa: E402
import nse_prices  # noqa: E402
from splits import HELD_OUT_START as HELD_OUT_FIRST_SESSION  # noqa: E402

OUT_DIR = os.path.join(BACKEND, "..", "docs", "research", "data")

# --- pre-registered constants (3h's rules, not re-tuned) --------------------------
N_HOLD = 15
RANK_KEEP = 30
MIN_HISTORY = 250
MIN_PRICE = 20.0
LIQ_WINDOW = 126
VOL_WINDOW = 252
SELECTION_START = "2010-01"
HALF_SPLIT = "2018-01"
LAST3_START = "2023-01"
PARTS = {"A": {"ranks": (1, 200), "slippage": 0.0005}, "B": {"ranks": (201, 400), "slippage": 0.0010}}
N_FAMILY = 3
T_GATE_A = 2.394          # two-sided Bonferroni at 5% across 3
T_CONFIRM_B = 1.65        # one-sided 5%
CAPITAL = 1_000_000.0
CAPITAL_COLUMNS = (100_000.0, 1_000_000.0, 2_500_000.0)

STT = 0.0010
STAMP_BUY = 0.00015
NSE_TXN = 0.0000307
SEBI = 0.000001
GST = 0.18
DP_PER_SELL = 15.34        # GST included (Zerodha)

LIQUID_VALUE = 5e7         # ₹5 crore traded that day
STAGE0_CONSISTENT_MIN = 0.97
STAGE0_UNEXPLAINED_MAX = 10


# --- calendar and universe ----------------------------------------------------------

def month_ends(sessions):
    out = []
    for i, d in enumerate(sessions):
        if i + 1 == len(sessions) or sessions[i + 1][:7] != d[:7]:
            out.append((d[:7], i))
    return out


def rows_before(c, idx):
    return bisect.bisect_right(c["idx"], idx)


def close_on_or_before(c, idx):
    k = rows_before(c, idx) - 1
    return c["close"][k] if k >= 0 else None


def ranked_universe(chains, idx):
    """All eligible chains at session idx, ranked by median traded value over
    the trailing 126 sessions (absent days count as zero)."""
    cands = []
    for name, c in chains.items():
        k = rows_before(c, idx)
        if k < MIN_HISTORY or c["idx"][k - 1] != idx or c["raw"][k - 1] < MIN_PRICE:
            continue
        lo = bisect.bisect_left(c["idx"], idx - LIQ_WINDOW + 1)
        vals = c["val"][lo:k] + [0.0] * (LIQ_WINDOW - (k - lo))
        cands.append((st.median(vals), name))
    cands.sort(reverse=True)
    return [n for _, n in cands]


def scores(chains, names, me_idx, months, month, idx):
    pos = months.index(month)
    if pos < 13:
        return {}
    i1, i7, i13 = (me_idx[months[pos - k]] for k in (1, 7, 13))
    out = {}
    for n in names:
        c = chains[n]
        c1, c7, c13 = close_on_or_before(c, i1), close_on_or_before(c, i7), close_on_or_before(c, i13)
        if not (c1 and c7 and c13):
            continue
        k = rows_before(c, idx)
        cl = c["close"][max(0, k - VOL_WINDOW - 1):k]
        rets = [cl[j] / cl[j - 1] - 1 for j in range(1, len(cl)) if cl[j - 1] > 0]
        if len(rets) < 60:
            continue
        sigma = st.pstdev(rets)
        if sigma > 0:
            out[n] = ((c1 / c7 - 1) / sigma + (c1 / c13 - 1) / sigma) / 2
    return out


# --- the book -------------------------------------------------------------------------

class Book:
    def __init__(self, capital, slippage, dp=True):
        self.cash, self.pos = capital, {}
        self.slippage, self.dp = slippage, dp
        self.buys = self.sells = self.forced = 0
        self.cost = self.turnover = 0.0

    def buy_cost(self, v):
        return v * (STT + STAMP_BUY + NSE_TXN + SEBI + GST * (NSE_TXN + SEBI) + self.slippage)

    def sell_cost(self, v):
        return v * (STT + NSE_TXN + SEBI + GST * (NSE_TXN + SEBI) + self.slippage) + (DP_PER_SELL if self.dp else 0.0)

    def value(self, chains, idx):
        return self.cash + sum(sh * (close_on_or_before(chains[n], idx) or 0.0) for n, sh in self.pos.items())

    def sell(self, name, px):
        v = self.pos.pop(name) * px
        c = self.sell_cost(v)
        self.cash += v - c
        self.cost += c
        self.turnover += v
        self.sells += 1

    def buy(self, name, px, amount):
        if amount <= 0 or px <= 0:
            return
        c = self.buy_cost(amount)
        self.pos[name] = self.pos.get(name, 0.0) + (amount - c) / px
        self.cash -= amount
        self.cost += c
        self.turnover += amount
        self.buys += 1


def fill_price(chains, name, idx):
    return close_on_or_before(chains[name], idx) or 0.0


def simulate(sessions, chains, universes, part, capital, start_month, held_out=False):
    lo, hi = PARTS[part]["ranks"]
    slip = PARTS[part]["slippage"]
    mes = month_ends(sessions)
    me_idx = {m: i for m, i in mes}
    months = [m for m, _ in mes]
    strat, bench = Book(capital, slip, dp=True), Book(capital, slip, dp=False)
    series, holdings = [], []
    started = False
    for month, idx in mes:
        if month < start_month:
            continue
        f = idx + 1
        if f >= len(sessions):
            break
        if not held_out and sessions[f] >= HELD_OUT_FIRST_SESSION:
            break
        uni = universes[month][lo - 1:hi]
        sc = scores(chains, uni, me_idx, months, month, idx)
        if not sc:
            continue
        ranked = sorted(sc, key=sc.get, reverse=True)
        rank = {n: i + 1 for i, n in enumerate(ranked)}
        uset = set(uni)
        for n in list(strat.pos):
            ended = chains[n]["idx"][-1] < idx
            strat.forced += ended
            if ended or n not in uset or rank.get(n, 10 ** 9) > RANK_KEEP:
                strat.sell(n, fill_price(chains, n, f))
        vac = N_HOLD - len(strat.pos)
        per = strat.cash / vac if vac > 0 else 0
        for n in ranked:
            if vac <= 0:
                break
            if n not in strat.pos:
                strat.buy(n, fill_price(chains, n, f), per)
                vac -= 1
        if not started:
            per_b = bench.cash / len(uni)
            for n in uni:
                bench.buy(n, fill_price(chains, n, f), per_b)
            started = True
        else:
            for n in list(bench.pos):
                if chains[n]["idx"][-1] < idx or n not in uset:
                    bench.sell(n, fill_price(chains, n, f))
            entrants = [n for n in uni if n not in bench.pos]
            if entrants:
                per_b = bench.cash / len(entrants)
                for n in entrants:
                    bench.buy(n, fill_price(chains, n, f), per_b)
        series.append((month, sessions[f], strat.value(chains, f), bench.value(chains, f)))
        holdings.append({"month": month, "holdings": sorted(strat.pos)})
    return series, strat, bench, holdings


# --- statistics -------------------------------------------------------------------------

def mrets(vals):
    return [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]


def t_of(xs):
    if len(xs) < 2:
        return None
    sd = st.stdev(xs)
    return st.mean(xs) / sd * math.sqrt(len(xs)) if sd > 0 else None


def describe(vals):
    r = mrets(vals)
    years = len(r) / 12
    cagr = (vals[-1] / vals[0]) ** (1 / years) - 1 if years > 0 else None
    vol = st.pstdev(r) * math.sqrt(12) if len(r) > 1 else None
    peak, mdd = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return {"cagr": cagr, "ann_vol": vol, "sharpe_rf0": cagr / vol if cagr is not None and vol else None,
            "max_drawdown": mdd, "worst_month": min(r), "best_month": max(r),
            "months_positive": sum(x > 0 for x in r), "n_months": len(r)}


def excess(sv, bv, months):
    ex = [a - b for a, b in zip(mrets(sv), mrets(bv))]
    m = months[1:]
    part = lambda cond: [e for e, mo in zip(ex, m) if cond(mo)]
    h1, h2, l3 = part(lambda mo: mo < HALF_SPLIT), part(lambda mo: mo >= HALF_SPLIT), part(lambda mo: mo >= LAST3_START)
    blk = lambda xs: {"mean": st.mean(xs) if xs else None, "t": t_of(xs), "n": len(xs)}
    return {"mean_monthly": st.mean(ex), "sd_monthly": st.stdev(ex), "t": t_of(ex), "n": len(ex),
            "half1": blk(h1), "half2": blk(h2), "last3": blk(l3), "series": ex}


def run_part(part, held_out=False):
    sessions, chains, meta, _ = nse_prices.load(include_held_out=held_out)
    universes = {m: ranked_universe(chains, i) for m, i in month_ends(sessions) if m >= SELECTION_START}
    start = "2025-12" if held_out else SELECTION_START   # held-out: the 2025-12 rebalance fills on the first 2026 session
    runs = {cap: simulate(sessions, chains, universes, part, cap, start, held_out) for cap in CAPITAL_COLUMNS}
    series, strat, bench, holdings = runs[CAPITAL]
    months = [s[0] for s in series]
    sv, bv = [s[2] for s in series], [s[3] for s in series]
    ex = excess(sv, bv, months)
    ds, db = describe(sv), describe(bv)
    gap = (ds["cagr"] - db["cagr"]) * 100
    dsr = evaluation.deflated_sharpe_ratio(ex["series"], N_FAMILY)
    years = max(1e-9, len(ex["series"]) / 12)
    out = {"prereg": "prereg-3i-momentum-corrected-data.md", "part": part, "held_out": held_out,
           "run_at": datetime.datetime.now().isoformat(timespec="seconds"), "meta": meta,
           "first_month": months[0], "last_month": months[-1],
           "strategy": ds, "benchmark": db, "cagr_gap_pp": gap,
           "excess_net": {k: v for k, v in ex.items() if k != "series"}, "excess_net_series": ex["series"],
           "dsr_family": dsr,
           "dsr_project_wide_information": evaluation.deflated_sharpe_ratio(ex["series"], evaluation.trials_of_record() + 1),
           "turnover": {"buys": strat.buys, "sells": strat.sells, "forced_exits": strat.forced,
                        "one_sided_pct_of_avg_book_per_year": strat.turnover / 2 / st.mean(sv) / years * 100,
                        "cost_pct_of_avg_book_per_year": strat.cost / st.mean(sv) / years * 100},
           "capital_columns": {str(int(c)): {"cagr": describe([s[2] for s in r[0]])["cagr"],
                                             "excess_mean": st.mean(excess([s[2] for s in r[0]], [s[3] for s in r[0]], months)["series"]),
                                             "excess_t": excess([s[2] for s in r[0]], [s[3] for s in r[0]], months)["t"]}
                               for c, r in runs.items()},
           "holdings": holdings, "values": {"strategy": sv, "benchmark": bv}, "months": months}
    yearly = collections.defaultdict(float)
    for mo, e in zip(months[1:], ex["series"]):
        yearly[mo[:4]] += e
    out["yearly_excess_sum"] = dict(yearly)
    if held_out:
        out["confirms"] = ex["mean_monthly"] > 0
    elif part == "A":
        rule = {"t_ge_2_394": (ex["t"] or 0) >= T_GATE_A and ex["mean_monthly"] > 0,
                "dsr_family_ge_0_95": (dsr.get("dsr") or 0) >= 0.95,
                "both_halves_positive": (ex["half1"]["mean"] or 0) > 0 and (ex["half2"]["mean"] or 0) > 0,
                "last3_positive": (ex["last3"]["mean"] or 0) > 0,
                "cagr_gap_ge_2pp": gap >= 2.0,
                "round_trips_ge_100": strat.sells >= 100}
        out.update({"pass_rule": rule, "PASS": all(rule.values())})
    else:
        rule = {"t_ge_1_65": (ex["t"] or 0) >= T_CONFIRM_B and ex["mean_monthly"] > 0,
                "both_halves_positive": (ex["half1"]["mean"] or 0) > 0 and (ex["half2"]["mean"] or 0) > 0}
        out.update({"confirm_rule": rule, "CONFIRMS": all(rule.values())})
    name = f"momentum_3i_part{part}{'_heldout' if held_out else ''}.json"
    _write(name, out)
    keys = ("first_month", "last_month", "strategy", "benchmark", "cagr_gap_pp", "excess_net", "dsr_family",
            "turnover", "pass_rule", "PASS", "confirm_rule", "CONFIRMS", "confirms")
    print(json.dumps({k: out[k] for k in keys if k in out}, indent=1, default=str))
    return out


# --- stage 0 ----------------------------------------------------------------------------

def stage0():
    sessions, chains, meta, events = nse_prices.load(refresh=True)
    per_year = collections.Counter(d[:4] for d in sessions)
    mes = month_ends(sessions)
    late = []
    for m, i in mes:
        d = datetime.date.fromisoformat(sessions[i])
        nxt = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        if (nxt - d).days > 5:
            late.append((m, sessions[i]))
    universes = {m: ranked_universe(chains, i) for m, i in mes if m >= SELECTION_START}
    short = {m: len(u) for m, u in universes.items() if len(u) < 400}
    top400_by_month = {m: set(u[:400]) for m, u in universes.items()}
    months = sorted(top400_by_month)

    def member_before(name, date):
        pos = bisect.bisect_left(months, date[:7]) - 1
        return pos >= 0 and name in top400_by_month[months[pos]]

    checked, bad = 0, []
    for canon, k, kind, f, ex_date, purpose in events:
        if kind not in ("split", "bonus") or ex_date < "2010-01-01":
            continue
        if not member_before(canon, ex_date):
            continue
        c = chains[canon]
        r = c["close"][k] / c["close"][k - 1] - 1
        checked += 1
        if abs(r) > 0.20:
            bad.append({"symbol": canon, "ex_date": ex_date, "kind": kind, "factor": f,
                        "adjusted_return": round(r, 4), "purpose": purpose})
    phantoms = []
    for name, c in chains.items():
        for j in range(1, len(c["idx"])):
            if c["idx"][j] - c["idx"][j - 1] != 1 or c["val"][j] < LIQUID_VALUE:
                continue
            r = c["close"][j] / c["close"][j - 1] - 1
            d = sessions[c["idx"][j]]
            if r < -0.30 and d >= "2010-01-01" and member_before(name, d):
                phantoms.append({"symbol": name, "date": d, "adjusted_return": round(r, 4),
                                 "raw_return": round(c["raw"][j] / c["raw"][j - 1] - 1, 4)})
    consistent = 1 - len(bad) / checked if checked else 0.0
    gate1 = all(per_year.get(str(y), 0) >= 240 for y in range(2009, 2026)) and not late and not short
    gate2 = consistent >= STAGE0_CONSISTENT_MIN
    out = {"meta": meta, "files_per_year": dict(sorted(per_year.items())), "month_ends_late": late,
           "months_short_of_400": short, "splits_bonuses_checked": checked, "inconsistent": bad,
           "consistent_share": consistent, "residual_phantoms": sorted(phantoms, key=lambda x: x["date"]),
           "gate1_coverage": gate1, "gate2_consistency": gate2,
           "gate3_note": f"{len(phantoms)} residual one-day drops below -30% on liquid days among top-400 names; "
                         f"each must be explained in the results file; gate: <= {STAGE0_UNEXPLAINED_MAX} unexplained"}
    _write("momentum_3i_stage0.json", out)
    print(json.dumps({k: v for k, v in out.items() if k not in ("files_per_year",)}, indent=1, default=str)[:6000])
    return out


def _write(name, obj):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, name), "w") as fh:
        json.dump(obj, fh, indent=1, default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["stage0", "partA", "partB", "heldout"])
    a = ap.parse_args()
    if a.stage == "stage0":
        stage0()
    elif a.stage == "heldout":
        run_part("A", held_out=True)
    else:
        run_part(a.stage[-1])


if __name__ == "__main__":
    main()
