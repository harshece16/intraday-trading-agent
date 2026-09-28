"""
Universe width: does the 3i momentum rule hold in less-traded stocks, and is
a wider book better than the one running? Stage 0 (look L41), replications
A' and B' of trial 120 and L38 on the repaired price panel (#175), tier
confirmations T3/T4/T5 (look L42) and the wide book W (trial 126).

Pre-registration: docs/research/prereg-universe-width.md. Every rule here is
a transcription of it, and its commit precedes this file's.

Usage (from backend/):
    .venv/bin/python research/momentum_width.py stage0     # data gate, no strategy return
    .venv/bin/python research/momentum_width.py A          # A', then B
    .venv/bin/python research/momentum_width.py T3         # then T4, T5
    .venv/bin/python research/momentum_width.py W          # needs the tier outputs

The signal, the portfolio rule, the costs and the statistics are imported
from momentum_3i.py, not copied. Writes docs/research/data/momentum_width_*.json.
Nothing on the live path imports this.
"""

import argparse
import bisect
import collections
import csv
import datetime
import glob
import json
import math
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

import evaluation  # noqa: E402
import momentum_3i as m3  # noqa: E402
import nse_prices  # noqa: E402
from splits import HELD_OUT_START as HELD_OUT_FIRST_SESSION  # noqa: E402

OUT_DIR = m3.OUT_DIR
PREREG = "prereg-universe-width.md"

# --- pre-registered constants --------------------------------------------------
EQ = 0                       # position of "EQ" in nse_prices.WIDE_SERIES
S1_WINDOW = 60               # no BE or BZ row in the last 60 sessions
S2_MIN_DAYS = 120            # traded on at least 120 of the last 126 sessions
S3_MIN_MEDIAN = 7_000_000.0  # median daily traded value of at least Rs 70 lakh
BANDS = (0.02, 0.05, 0.10, 0.20)
BAND_INSIDE, BAND_OUTSIDE = 0.0030, 0.0010
BUY_CARRY = 5                # sessions after the fill day a buy may be carried
ENDED_LOOKBACK = 20          # rows checked for BE/BZ when a chain has ended
# E-3i rank at the month-end -> slippage per side (base, stress)
SLIPPAGE = ((200, 0.0005, 0.0010), (400, 0.0015, 0.0030), (600, 0.0025, 0.0050), (1000, 0.0040, 0.0080))
SLIPPAGE_BEYOND = (0.0075, 0.0150)
MIN_MONTHS = 120
TIER_STEP = 200

PARTS = {
    "A": {"list": "e3i", "ranks": (1, 200), "flat": 0.0005, "label": "A' (trial 120 re-run)"},
    "B": {"list": "e3i", "ranks": (201, 400), "flat": 0.0010, "label": "B' (L38 re-run)"},
    "T3": {"list": "ewide", "ranks": (401, 600), "label": "T3, ranks 401-600"},
    "T4": {"list": "ewide", "ranks": (601, 800), "label": "T4, ranks 601-800"},
    "T5": {"list": "ewide", "ranks": (801, 1000), "label": "T5, ranks 801-1,000"},
}
TIERS = ("T3", "T4", "T5")
T_TIER = 2.128               # one-sided 5%, Bonferroni across three tiers
N_FAMILY = 4
T_FAMILY = 2.498             # two-sided 5%, Bonferroni across four
T_PAIRED = 1.645             # one-sided 5%
Z_POWER_80 = 0.8416

STAGE0_UNIVERSE_PARITY_MIN = 0.995
STAGE0_CONSISTENT_MIN = 0.97
STAGE0_TOP = 1000
JUMP = 0.30
JUMP_MIN_VALUE = 1e7         # Rs 1 crore traded that day
JUMP_WINDOW = 5              # sessions either side of the jump
PARITY_TOLERANCE = 1e-9
RX_PRICE_ACTION = re.compile(
    r"spl|sub-?\s*division|\bbon|\bri?ghts?\b|demerger|arrangement|consolidat|reduction|amalgamat|merger", re.I)


# --- eligibility and ranking -------------------------------------------------------

def eq_view(chains):
    """EQ rows only: the fields 3i's eligibility and ranking read. A panel
    with no series column (3i's own) is all EQ."""
    out = {}
    for name, c in chains.items():
        if "ser" not in c:
            out[name] = c
            continue
        keep = [j for j, s in enumerate(c["ser"]) if s == EQ]
        if keep:
            out[name] = {k: [c[k][j] for j in keep] for k in ("idx", "raw", "val")}
    return out


def ranked(eq, idx):
    """3i's ranked_universe, keeping each name's median: [(median, name)], best first."""
    cands = []
    for name, c in eq.items():
        k = m3.rows_before(c, idx)
        if k < m3.MIN_HISTORY or c["idx"][k - 1] != idx or c["raw"][k - 1] < m3.MIN_PRICE:
            continue
        lo = bisect.bisect_left(c["idx"], idx - m3.LIQ_WINDOW + 1)
        vals = c["val"][lo:k] + [0.0] * (m3.LIQ_WINDOW - (k - lo))
        cands.append((st.median(vals), name))
    cands.sort(reverse=True)
    return cands


def passes_screens(c, idx, median):
    """Screens S1, S2 and S3 on the repaired panel's chain."""
    k = m3.rows_before(c, idx)
    if any(s != EQ for s in c["ser"][bisect.bisect_left(c["idx"], idx - S1_WINDOW + 1):k]):
        return False
    if k - bisect.bisect_left(c["idx"], idx - m3.LIQ_WINDOW + 1) < S2_MIN_DAYS:
        return False
    return median >= S3_MIN_MEDIAN


def universes(sessions, chains, screens=True):
    """month -> the E-3i list, the E-wide list, and each name's E-3i rank and
    median traded value at that month-end."""
    eq = eq_view(chains)
    out = {}
    for month, idx in m3.month_ends(sessions):
        if month < m3.SELECTION_START:
            continue
        full = ranked(eq, idx)
        out[month] = {
            "e3i": [n for _, n in full],
            "ewide": [n for v, n in full if passes_screens(chains[n], idx, v)] if screens else [],
            "rank3i": {n: i + 1 for i, (_, n) in enumerate(full)},
            "median": {n: v for v, n in full},
        }
    return out


def start_month(unis, which, deepest):
    """The first month from which the list holds `deepest` names at every
    later month-end (stage-0 gate 7). None if it never does."""
    first = None
    for month in sorted(unis):
        if len(unis[month][which]) >= deepest:
            first = first or month
        else:
            first = None
    return first


def monthly_returns_available(sessions, unis, start):
    """How many monthly returns a part that starts at `start` will have,
    counted from the calendar alone (no return is read)."""
    if not start:
        return 0
    mes = m3.month_ends(sessions)
    n = 0
    for pos, (month, idx) in enumerate(mes):
        f = idx + 1
        if month < start or month not in unis or pos < 13:
            continue
        if f >= len(sessions) or sessions[f] >= HELD_OUT_FIRST_SESSION:
            break
        n += 1
    return max(0, n - 1)


def slippage(name, uni, cfg, stress):
    if "flat" in cfg:
        return cfg["flat"]
    rank = uni["rank3i"].get(name)
    col = 2 if stress else 1
    if rank is not None:
        for row in SLIPPAGE:
            if rank <= row[0]:
                return row[col]
    return SLIPPAGE_BEYOND[col - 1]


# --- fills ---------------------------------------------------------------------------

def lock(c, j):
    """+1 if row j closed locked at its upper band, -1 at its lower band (rule H3)."""
    close, prev = c["raw"][j], c["prev"][j]
    if prev <= 0 or close <= 0:
        return 0
    ret = close / prev - 1
    for b in BANDS:
        if close >= c["high"][j] - 1e-9 and b - BAND_INSIDE <= ret <= b + BAND_OUTSIDE:
            return 1
        if close <= c["low"][j] + 1e-9 and -b - BAND_OUTSIDE <= ret <= -b + BAND_INSIDE:
            return -1
    return 0


def ended_in_t2t(c):
    return any(s != EQ for s in c.get("ser", [])[-ENDED_LOOKBACK:])


class Book:
    """3i's book, with orders that may be carried from one session to the next."""

    def __init__(self, capital, dp, honest=True, stress=False):
        self.cash, self.pos, self.orders = capital, {}, []
        self.dp, self.honest, self.stress = dp, honest, stress
        self.buys = self.sells = self.forced = 0
        self.cost = self.turnover = 0.0
        self.count = collections.Counter()
        self.participation = {}     # year -> largest buy as a share of median daily value

    def value(self, chains, idx):
        return self.cash + sum(sh * (m3.close_on_or_before(chains[n], idx) or 0.0) for n, sh in self.pos.items())

    def _sold(self, name, px, slip):
        v = self.pos.pop(name) * px
        c = v * (m3.STT + m3.NSE_TXN + m3.SEBI + m3.GST * (m3.NSE_TXN + m3.SEBI) + slip) + (m3.DP_PER_SELL if self.dp else 0.0)
        self.cash += v - c
        self.cost += c
        self.turnover += v
        self.sells += 1

    def _bought(self, name, px, amount, slip):
        if amount <= 0 or px <= 0:
            return
        c = amount * (m3.STT + m3.STAMP_BUY + m3.NSE_TXN + m3.SEBI + m3.GST * (m3.NSE_TXN + m3.SEBI) + slip)
        self.pos[name] = self.pos.get(name, 0.0) + (amount - c) / px
        self.cash -= amount
        self.cost += c
        self.turnover += amount
        self.buys += 1

    def sell_ended(self, name, c, slip):
        """Rule H5: a holding whose chain has ended is sold at its last close;
        in the stress case a chain that ended in trade-for-trade pays nothing."""
        self.forced += 1
        self.count["ended"] += 1
        if ended_in_t2t(c):
            self.count["ended_in_t2t"] += 1
            if self.stress:
                self.pos.pop(name)
                self.sells += 1
                return
        self._sold(name, c["close"][-1], slip)

    def order(self, side, name, slip, placed, amount=0.0, median=None):
        self.orders.append({"side": side, "name": name, "slip": slip, "placed": placed,
                            "amount": amount, "median": median, "carried": None})

    def work(self, chains, s, sessions, side=None):
        """Try every open order at session s (rules H1 to H4)."""
        still = []
        for o in self.orders:
            if side and o["side"] != side:
                still.append(o)
                continue
            if o["side"] == "buy" and s > o["placed"] + BUY_CARRY:
                self.count["buys_cancelled"] += 1
                continue
            c = chains[o["name"]]
            k = m3.rows_before(c, s)
            if not self.honest:
                px = c["close"][k - 1] if k else 0.0        # 3i: the close on or before
            elif not k or c["idx"][k - 1] != s:
                px = None
                why = "no_trade"
            elif lock(c, k - 1) == (1 if o["side"] == "buy" else -1):
                px = None
                why = "locked"
            else:
                px = c["close"][k - 1]
            if px is None:
                if o["carried"] is None:
                    o["carried"] = why
                    self.count["carried_" + o["side"] + "_" + why] += 1
                still.append(o)
                continue
            if o["side"] == "sell":
                if self.honest and c["ser"][k - 1] != EQ:
                    self.count["sells_priced_in_t2t"] += 1
                self._sold(o["name"], px, o["slip"])
            else:
                self._bought(o["name"], px, o["amount"], o["slip"])
                if o["median"]:
                    year = sessions[s][:4]
                    self.participation[year] = max(self.participation.get(year, 0.0), o["amount"] / o["median"])
        self.orders = still

    def drop_orders(self):
        self.count["orders_dropped_at_month_end"] += len(self.orders)
        self.orders = []


def simulate(sessions, chains, unis, cfg, capital, start, honest=True, stress=False):
    """One part: the strategy and its benchmark, month by month. Returns
    (series, strategy book, benchmark book, holdings)."""
    lo, hi = cfg["ranks"]
    mes = m3.month_ends(sessions)
    me_idx = {m: i for m, i in mes}
    months = [m for m, _ in mes]
    strat = Book(capital, dp=True, honest=honest, stress=stress)
    bench = Book(capital, dp=False, honest=honest, stress=stress)
    series, holdings = [], []
    started, last_fill = False, None
    for month, idx in mes:
        if month < start:
            continue
        f = idx + 1
        if f >= len(sessions) or sessions[f] >= HELD_OUT_FIRST_SESSION:
            break
        if last_fill is not None:
            for s in range(last_fill + 1, idx + 1):
                strat.work(chains, s, sessions)
                bench.work(chains, s, sessions)
            strat.drop_orders()
            bench.drop_orders()
        uni = unis[month]
        names = uni[cfg["list"]][lo - 1:hi]
        sc = m3.scores(chains, names, me_idx, months, month, idx)
        if not sc:
            continue
        order = sorted(sc, key=sc.get, reverse=True)
        rank = {n: i + 1 for i, n in enumerate(order)}
        uset = set(names)

        for n in list(strat.pos):
            if chains[n]["idx"][-1] < idx:
                strat.sell_ended(n, chains[n], slippage(n, uni, cfg, stress))
            elif n not in uset or rank.get(n, 10 ** 9) > m3.RANK_KEEP:
                strat.order("sell", n, slippage(n, uni, cfg, stress), f)
        strat.work(chains, f, sessions, "sell")
        vac = m3.N_HOLD - len(strat.pos)
        per = strat.cash / vac if vac > 0 else 0
        for n in order:
            if vac <= 0:
                break
            if n not in strat.pos:
                strat.order("buy", n, slippage(n, uni, cfg, stress), f, per, uni["median"].get(n))
                vac -= 1
        strat.work(chains, f, sessions, "buy")

        if not started:
            per_b = bench.cash / len(names)
            for n in names:
                bench.order("buy", n, slippage(n, uni, cfg, stress), f, per_b)
            started = True
        else:
            for n in list(bench.pos):
                if chains[n]["idx"][-1] < idx:
                    bench.sell_ended(n, chains[n], slippage(n, uni, cfg, stress))
                elif n not in uset:
                    bench.order("sell", n, slippage(n, uni, cfg, stress), f)
            bench.work(chains, f, sessions, "sell")
            entrants = [n for n in names if n not in bench.pos]
            if entrants:
                per_b = bench.cash / len(entrants)
                for n in entrants:
                    bench.order("buy", n, slippage(n, uni, cfg, stress), f, per_b)
        bench.work(chains, f, sessions, "buy")

        last_fill = f
        series.append((month, sessions[f], strat.value(chains, f), bench.value(chains, f)))
        holdings.append({"month": month, "holdings": sorted(strat.pos)})
    return series, strat, bench, holdings


# --- statistics ------------------------------------------------------------------------

def block(xs):
    return {"mean": st.mean(xs) if xs else None, "t": m3.t_of(xs), "n": len(xs)}


def halves(xs):
    """The first and second half of a run's own months. The second half takes
    the extra month, which is 3i's split for a run over the full sample."""
    h = len(xs) // 2
    return xs[:h], xs[h:]


def series_stats(xs, months):
    """xs[i] is the return to months[i + 1]."""
    h1, h2 = halves(xs)
    last3 = [x for x, mo in zip(xs, months[1:]) if mo >= m3.LAST3_START]
    return {"mean_monthly": st.mean(xs), "sd_monthly": st.stdev(xs), "t": m3.t_of(xs), "n": len(xs),
            "half1": block(h1), "half2": block(h2), "last3": block(last3),
            "second_half_from": months[1 + len(h1)]}


def under_water(vals):
    """Longest run of months below an earlier peak."""
    peak, run, worst = vals[0], 0, 0
    for v in vals:
        if v >= peak:
            peak, run = v, 0
        else:
            run += 1
            worst = max(worst, run)
    return worst


def book_report(book):
    return {"buys": book.buys, "sells": book.sells, "forced_exits": book.forced, "fills": dict(book.count),
            "largest_buy_share_of_median_day": {y: round(v, 5) for y, v in sorted(book.participation.items())}}


def summarise(series, strat, bench, holdings):
    months = [s[0] for s in series]
    sv, bv = [s[2] for s in series], [s[3] for s in series]
    ex = [a - b for a, b in zip(m3.mrets(sv), m3.mrets(bv))]
    ds, db = m3.describe(sv), m3.describe(bv)
    years = max(1e-9, len(ex) / 12)
    yearly = collections.defaultdict(float)
    for mo, e in zip(months[1:], ex):
        yearly[mo[:4]] += e
    ds["months_under_water"], db["months_under_water"] = under_water(sv), under_water(bv)
    return {"first_month": months[0], "last_month": months[-1], "strategy": ds, "benchmark": db,
            "cagr_gap_pp": (ds["cagr"] - db["cagr"]) * 100,
            "excess_net": series_stats(ex, months), "excess_net_series": ex,
            "turnover": {"one_sided_pct_of_avg_book_per_year": strat.turnover / 2 / st.mean(sv) / years * 100,
                         "cost_pct_of_avg_book_per_year": strat.cost / st.mean(sv) / years * 100},
            "strategy_book": book_report(strat), "benchmark_book": book_report(bench),
            "yearly_excess_sum": dict(yearly), "holdings": holdings,
            "values": {"strategy": sv, "benchmark": bv}, "months": months}


def gross_excess(sessions, chains, unis, cfg, start):
    """The same run with every cost at zero (information only)."""
    saved = (m3.STT, m3.STAMP_BUY, m3.NSE_TXN, m3.SEBI, m3.DP_PER_SELL)
    m3.STT = m3.STAMP_BUY = m3.NSE_TXN = m3.SEBI = m3.DP_PER_SELL = 0.0
    try:
        free = dict(cfg, flat=0.0)
        series, _, _, _ = simulate(sessions, chains, unis, free, m3.CAPITAL, start)
    finally:
        m3.STT, m3.STAMP_BUY, m3.NSE_TXN, m3.SEBI, m3.DP_PER_SELL = saved
    ex = [a - b for a, b in zip(m3.mrets([s[2] for s in series]), m3.mrets([s[3] for s in series]))]
    return block(ex)


def capital_columns(sessions, chains, unis, cfg, start, stress=False):
    out = {}
    for cap in m3.CAPITAL_COLUMNS:
        series, _, _, _ = simulate(sessions, chains, unis, cfg, cap, start, stress=stress)
        sv, bv = [s[2] for s in series], [s[3] for s in series]
        ex = [a - b for a, b in zip(m3.mrets(sv), m3.mrets(bv))]
        out[str(int(cap))] = {"cagr": m3.describe(sv)["cagr"], "excess_mean": st.mean(ex), "excess_t": m3.t_of(ex)}
    return out


# --- the parts ---------------------------------------------------------------------------

def load_panel():
    sessions, chains, meta, _ = nse_prices.load(wide=True)
    return sessions, chains, meta


def run(part, cfg=None, panel=None, unis=None):
    cfg = cfg or PARTS[part]
    sessions, chains, meta = panel or load_panel()
    unis = unis or universes(sessions, chains)
    replication = "flat" in cfg
    start = m3.SELECTION_START if replication else start_month(unis, cfg["list"], cfg["ranks"][1])
    out = {"prereg": PREREG, "part": part, "label": cfg["label"], "ranks": list(cfg["ranks"]),
           "list": cfg["list"], "run_at": datetime.datetime.now().isoformat(timespec="seconds"), "meta": meta,
           "start_month": start}
    n_months = monthly_returns_available(sessions, unis, start)
    if n_months < MIN_MONTHS:
        out.update({"testable": False, "months_available": n_months})
        _finish(part, out)
        return out
    base = summarise(*simulate(sessions, chains, unis, cfg, m3.CAPITAL, start))
    out.update({"testable": True, "base": base, "gross_excess": gross_excess(sessions, chains, unis, cfg, start),
                "capital_columns": capital_columns(sessions, chains, unis, cfg, start)})
    ex = base["excess_net"]
    both = (ex["half1"]["mean"] or 0) > 0 and (ex["half2"]["mean"] or 0) > 0
    if replication:
        out["recorded"] = compare_with_recorded(part, base)
        if part == "A":
            dsr = evaluation.deflated_sharpe_ratio(base["excess_net_series"], m3.N_FAMILY)
            rule = {"t_ge_2_394": (ex["t"] or 0) >= m3.T_GATE_A and ex["mean_monthly"] > 0,
                    "dsr_family_ge_0_95": (dsr.get("dsr") or 0) >= 0.95,
                    "both_halves_positive": both,
                    "last3_positive": (ex["last3"]["mean"] or 0) > 0,
                    "cagr_gap_ge_2pp": base["cagr_gap_pp"] >= 2.0,
                    "round_trips_ge_100": base["strategy_book"]["sells"] >= 100}
            out.update({"dsr_family_n3": dsr, "rule_of_trial_120": rule, "SURVIVES": all(rule.values())})
        else:
            rule = {"t_ge_1_65": (ex["t"] or 0) >= m3.T_CONFIRM_B and ex["mean_monthly"] > 0,
                    "both_halves_positive": both}
            out.update({"rule_of_L38": rule, "SURVIVES": all(rule.values())})
    else:
        stress = summarise(*simulate(sessions, chains, unis, cfg, m3.CAPITAL, start, stress=True))
        out["stress"] = stress
        if part in TIERS:
            rule = {"base_t_ge_2_128": (ex["t"] or 0) >= T_TIER and ex["mean_monthly"] > 0,
                    "base_both_halves_positive": both,
                    "stress_mean_positive": stress["excess_net"]["mean_monthly"] > 0}
            out.update({"confirm_rule": rule, "CONFIRMS": all(rule.values())})
    _finish(part, out)
    return out


def compare_with_recorded(part, base):
    """A' and B' beside the results already recorded, month by month."""
    with open(os.path.join(OUT_DIR, "momentum_3i_part%s.json" % part)) as fh:
        old = json.load(fh)
    diff = [a - b for a, b in zip(base["excess_net_series"], old["excess_net_series"])]
    changed = sum(1 for a, b in zip(base["holdings"], old["holdings"]) if a["holdings"] != b["holdings"])
    return {"recorded_mean": old["excess_net"]["mean_monthly"], "recorded_t": old["excess_net"]["t"],
            "recorded_cagr": old["strategy"]["cagr"], "difference_mean": st.mean(diff),
            "largest_monthly_difference": max(diff, key=abs), "months_with_other_holdings": changed,
            "difference_series": diff}


def wide_k(results):
    """K for the wide book: 400, plus 200 for every tier that confirms,
    counted outward from T3 and stopping at the first that does not."""
    k = 400
    for tier in TIERS:
        if not results[tier].get("CONFIRMS"):
            break
        k += TIER_STEP
    return k


def run_wide():
    tiers = {}
    for tier in TIERS:
        with open(os.path.join(OUT_DIR, "momentum_width_%s.json" % tier)) as fh:
            tiers[tier] = json.load(fh)
    with open(os.path.join(OUT_DIR, "momentum_width_A.json")) as fh:
        narrow = json.load(fh)
    k = wide_k(tiers)
    cfg = {"list": "ewide", "ranks": (1, k), "label": "W, ranks 1-%d" % k}
    panel = load_panel()
    out = run("W", cfg, panel)
    out["k"] = k
    out["tiers"] = {t: bool(r.get("CONFIRMS")) for t, r in tiers.items()}
    if not out["testable"]:
        _finish("W", out)
        return out
    base, ex = out["base"], out["base"]["excess_net"]
    dsr = evaluation.deflated_sharpe_ratio(base["excess_net_series"], N_FAMILY)
    paired = paired_test(base, narrow["base"])
    rule = {"1_t_ge_2_498": (ex["t"] or 0) >= T_FAMILY and ex["mean_monthly"] > 0,
            "2_dsr_family_ge_0_95": (dsr.get("dsr") or 0) >= 0.95,
            "3_both_halves_and_last3_positive": (ex["half1"]["mean"] or 0) > 0 and (ex["half2"]["mean"] or 0) > 0
            and (ex["last3"]["mean"] or 0) > 0,
            "4_cagr_gap_and_round_trips": base["cagr_gap_pp"] >= 2.0 and base["strategy_book"]["sells"] >= 100,
            "5_stress_mean_positive": out["stress"]["excess_net"]["mean_monthly"] > 0,
            "6_better_than_running_book": paired["mean"] > 0 and (paired["t"] or 0) >= T_PAIRED
            and (paired["half1"]["mean"] or 0) > 0 and (paired["half2"]["mean"] or 0) > 0,
            "7_sharpe_not_lower": paired["sharpe_wide"] >= paired["sharpe_running"]}
    out.update({"dsr_family": dsr, "paired_against_running_book": paired, "pass_rule": rule,
                "PASS": all(rule.values()),
                "dsr_project_wide_information": evaluation.deflated_sharpe_ratio(
                    base["excess_net_series"], evaluation.trials_of_record() + 1)})
    _finish("W", out)
    return out


def paired_test(wide, running):
    """W's net monthly return minus A's, over the months both have."""
    rw = dict(zip(wide["months"][1:], m3.mrets(wide["values"]["strategy"])))
    rr = dict(zip(running["months"][1:], m3.mrets(running["values"]["strategy"])))
    common = sorted(set(rw) & set(rr))
    w, r = [rw[m] for m in common], [rr[m] for m in common]
    diff = [a - b for a, b in zip(w, r)]
    h1, h2 = halves(diff)
    sd = st.stdev(diff)
    held = {h["month"]: set(h["holdings"]) for h in running["holdings"]}
    shared = [len(set(h["holdings"]) & held[h["month"]]) for h in wide["holdings"] if h["month"] in held]
    return {"n": len(diff), "mean": st.mean(diff), "sd": sd, "t": m3.t_of(diff),
            "half1": block(h1), "half2": block(h2),
            "smallest_difference_detectable_at_80pct_power": (T_PAIRED + Z_POWER_80) * sd / math.sqrt(len(diff)),
            "sharpe_wide": st.mean(w) / st.stdev(w), "sharpe_running": st.mean(r) / st.stdev(r),
            "names_held_in_common_mean": st.mean(shared) if shared else None, "series": diff}


# --- stage 0 --------------------------------------------------------------------------------

def same_panel(a, b):
    """Differences between two panels, value for value."""
    out = []
    if a[0] != b[0]:
        out.append("sessions differ")
    if set(a[1]) != set(b[1]):
        out.append("chains differ: %d only in the first, %d only in the second"
                   % (len(set(a[1]) - set(b[1])), len(set(b[1]) - set(a[1]))))
    for name in set(a[1]) & set(b[1]):
        for k in ("idx", "close", "raw", "open", "val", "isins"):
            if a[1][name][k] != b[1][name][k]:
                out.append("%s.%s differs" % (name, k))
                break
    if a[2]["actions_applied"] != b[2]["actions_applied"]:
        out.append("actions applied differ")
    if [tuple(e) for e in a[3]] != [tuple(e) for e in b[3]]:
        out.append("events differ")
    return out


def engine_parity(old):
    """The new simulator with honest fills off, on 3i's panel, against the
    recorded series of trial 120 and L38."""
    sessions, chains = old[0], old[1]
    unis = universes(sessions, chains, screens=False)
    out = {}
    for part in ("A", "B"):
        series, _, _, holdings = simulate(sessions, chains, unis, PARTS[part], m3.CAPITAL,
                                          m3.SELECTION_START, honest=False)
        ex = [a - b for a, b in zip(m3.mrets([s[2] for s in series]), m3.mrets([s[3] for s in series]))]
        with open(os.path.join(OUT_DIR, "momentum_3i_part%s.json" % part)) as fh:
            rec = json.load(fh)
        gap = max(abs(a - b) for a, b in zip(ex, rec["excess_net_series"])) if len(ex) == len(rec["excess_net_series"]) else None
        out[part] = {"months": len(ex), "recorded_months": len(rec["excess_net_series"]),
                     "largest_difference": gap, "holdings_identical": holdings == rec["holdings"],
                     "ok": gap is not None and gap <= PARITY_TOLERANCE and holdings == rec["holdings"]}
    return out


def raw_actions(ca_dir):
    """symbol -> [(ex-date, purpose)] for every row of NSE's corporate-actions files to 2025."""
    out = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(ca_dir, "ca_*.csv"))):
        if int(os.path.basename(path)[3:7]) > 2025:
            continue
        with open(path, encoding="utf-8-sig", errors="ignore") as fh:
            for r in csv.DictReader(fh):
                r = {k.strip().strip('"'): (v or "").strip() for k, v in r.items() if k}
                try:
                    ex = datetime.datetime.strptime(r["EX-DATE"], "%d-%b-%Y").date().isoformat()
                except (KeyError, ValueError):
                    continue
                try:
                    fv = float(r.get("FACE VALUE") or 0)
                except ValueError:
                    fv = 0.0
                out[r.get("SYMBOL", "")].append((ex, r.get("PURPOSE", ""), fv))
    return out


def not_applied(purpose, face_value, applied_kinds):
    """True if this row of NSE's file should have moved the price series and
    the loader applied nothing, or less than the row says."""
    kinds = {k for k, _ in nse_prices.parse_purpose(purpose, face_value)}
    if not kinds:
        return bool(RX_PRICE_ACTION.search(purpose))
    return bool(kinds - set(applied_kinds))


def tradability_map(sessions, chains, unis):
    """By tier and year: stock-days with no trade, band locks, trade-for-trade
    rows. Membership is fixed at each month-end for the month that follows."""
    tiers = (("1-200", 0, 200), ("201-400", 200, 400), ("401-600", 400, 600),
             ("601-800", 600, 800), ("801-1000", 800, 1000))
    tally = collections.defaultdict(collections.Counter)
    mes = [(m, i) for m, i in m3.month_ends(sessions) if m in unis]
    for (month, idx), (_, nxt) in zip(mes, mes[1:]):
        for label, lo, hi in tiers:
            t = tally[(label, sessions[nxt][:4])]
            for n in unis[month]["ewide"][lo:hi]:
                c = chains[n]
                a, b = bisect.bisect_right(c["idx"], idx), bisect.bisect_right(c["idx"], nxt)
                t["stock_days"] += nxt - idx
                t["no_trade"] += (nxt - idx) - (b - a)
                for j in range(a, b):
                    k = lock(c, j)
                    t["locked_up"] += k > 0
                    t["locked_down"] += k < 0
                    t["t2t_rows"] += c["ser"][j] != EQ
    out = {}
    for (label, year), t in sorted(tally.items()):
        d = t["stock_days"] or 1
        out.setdefault(label, {})[year] = {"stock_days": t["stock_days"],
                                           "pct_no_trade": 100 * t["no_trade"] / d,
                                           "pct_locked_up": 100 * t["locked_up"] / d,
                                           "pct_locked_down": 100 * t["locked_down"] / d,
                                           "pct_t2t_rows": 100 * t["t2t_rows"] / d}
    return out


def stage0():
    old = nse_prices.load()
    rebuilt = nse_prices.build()
    loader_diff = same_panel(old, rebuilt)
    del rebuilt
    parity = engine_parity(old)
    sessions, chains, meta, events = nse_prices.load(refresh=True, wide=True)
    unis = universes(sessions, chains)

    per_year = collections.Counter(d[:4] for d in sessions)
    mes = m3.month_ends(sessions)
    late = []
    for m, i in mes:
        d = datetime.date.fromisoformat(sessions[i])
        nxt = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        if (nxt - d).days > 5:
            late.append((m, sessions[i]))
    gate1 = all(per_year.get(str(y), 0) >= 240 for y in range(2009, 2026)) and not late

    # gate 3: the E-3i top 400 on the repaired panel against 3i's own panel
    same = total = 0
    differences = []
    for m, i in mes:
        if m not in unis:
            continue
        a, b = set(m3.ranked_universe(old[1], i)[:400]), set(unis[m]["e3i"][:400])
        total += len(a)
        same += len(a & b)
        if a != b:
            differences.append({"month": m, "only_in_3i": sorted(a - b), "only_in_repaired": sorted(b - a)})
    universe_parity = same / total if total else 0.0
    del old

    months = sorted(unis)
    top = {m: set(unis[m]["e3i"][:STAGE0_TOP]) for m in months}

    def member_before(name, date):
        pos = bisect.bisect_left(months, date[:7]) - 1
        return pos >= 0 and name in top[months[pos]]

    checked, bad = 0, []
    applied = collections.defaultdict(set)
    for canon, k, kind, f, ex_date, purpose in events:
        applied[(canon, ex_date)].add(kind)
        if kind not in ("split", "bonus") or ex_date < "2010-01-01" or not member_before(canon, ex_date):
            continue
        c = chains[canon]
        r = c["close"][k] / c["close"][k - 1] - 1
        checked += 1
        if abs(r) > 0.20:
            bad.append({"symbol": canon, "ex_date": ex_date, "kind": kind, "factor": f,
                        "adjusted_return": round(r, 4), "purpose": purpose})
    consistent = 1 - len(bad) / checked if checked else 0.0

    actions = raw_actions(nse_prices.CA_DIR)
    jumps = []
    for name, c in chains.items():
        for j in range(1, len(c["idx"])):
            if c["idx"][j] - c["idx"][j - 1] != 1 or c["val"][j] < JUMP_MIN_VALUE:
                continue
            r = c["close"][j] / c["close"][j - 1] - 1
            d = sessions[c["idx"][j]]
            if abs(r) <= JUMP or d < "2010-01-01" or not member_before(name, d):
                continue
            lo = sessions[max(0, c["idx"][j] - JUMP_WINDOW)]
            hi = sessions[min(len(sessions) - 1, c["idx"][j] + JUMP_WINDOW)]
            near = [(ex, p, fv) for sym in meta["aliases"].get(name, [name]) for ex, p, fv in actions.get(sym, [])
                    if lo <= ex <= hi and (RX_PRICE_ACTION.search(p) or nse_prices.parse_purpose(p, fv))]
            jumps.append({"symbol": name, "date": d, "adjusted_return": round(r, 4),
                          "raw_return": round(c["raw"][j] / c["raw"][j - 1] - 1, 4),
                          "actions_in_nse_file": sorted({(ex, p) for ex, p, _ in near}),
                          "not_applied": sorted({(ex, p) for ex, p, fv in near
                                                 if not_applied(p, fv, applied[(name, ex)])})})
    jumps.sort(key=lambda x: x["date"])
    unapplied = [x for x in jumps if x["not_applied"]]

    sizes = {m: len(unis[m]["ewide"]) for m in months}
    starts = {p: start_month(unis, PARTS[p]["list"], PARTS[p]["ranks"][1]) for p in TIERS}
    for k in (400, 600, 800, 1000):
        starts["W_%d" % k] = start_month(unis, "ewide", k)
    boundary = {}
    for m in months:
        if m.endswith("-12") or m == months[-1]:
            ewide, med = unis[m]["ewide"], unis[m]["median"]
            boundary[m] = {str(r): med[ewide[r - 1]] for r in (200, 400, 600, 800, 1000) if len(ewide) >= r}

    gates = {"1_coverage": gate1,
             "2_loader_parity": not loader_diff,
             "3_universe_parity": universe_parity >= STAGE0_UNIVERSE_PARITY_MIN,
             "4_engine_parity": all(p["ok"] for p in parity.values()),
             "5_adjustment_consistency": consistent >= STAGE0_CONSISTENT_MIN,
             "6_no_unapplied_action_behind_a_jump": not unapplied}
    out = {"prereg": PREREG, "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "meta": {k: v for k, v in meta.items() if k != "aliases"},
           "files_per_year": dict(sorted(per_year.items())), "month_ends_late": late,
           "loader_differences": loader_diff[:50], "engine_parity": parity,
           "universe_parity_share": universe_parity, "universe_differences": differences[:200],
           "universe_months_that_differ": len(differences),
           "splits_bonuses_checked": checked, "inconsistent": bad, "consistent_share": consistent,
           "jumps": jumps, "jumps_total": len(jumps), "jumps_with_an_unapplied_action": len(unapplied),
           "ewide_size_by_month": sizes, "e3i_size_by_month": {m: len(unis[m]["e3i"]) for m in months},
           "start_month": starts, "median_traded_value_at_rank": boundary,
           "tradability": tradability_map(sessions, chains, unis),
           "gates": gates, "PASS": all(gates.values())}
    _write("momentum_width_stage0.json", out)
    keep = ("meta", "engine_parity", "universe_parity_share", "universe_months_that_differ", "loader_differences",
            "splits_bonuses_checked", "consistent_share", "jumps_total", "jumps_with_an_unapplied_action",
            "start_month", "gates", "PASS")
    print(json.dumps({k: out[k] for k in keep}, indent=1, default=str))
    return out


# --- output ----------------------------------------------------------------------------------

def _write(name, obj):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, name), "w") as fh:
        json.dump(obj, fh, indent=1, default=str)


def _finish(part, out):
    _write("momentum_width_%s.json" % part, out)
    show = {k: out[k] for k in ("part", "label", "start_month", "testable", "k", "tiers", "recorded",
                                "rule_of_trial_120", "rule_of_L38", "SURVIVES", "confirm_rule", "CONFIRMS",
                                "pass_rule", "PASS", "dsr_family", "gross_excess", "capital_columns") if k in out}
    if "recorded" in show:
        show["recorded"] = {k: v for k, v in show["recorded"].items() if k != "difference_series"}
    for case in ("base", "stress"):
        if case in out:
            show[case] = {k: out[case][k] for k in ("first_month", "last_month", "strategy", "benchmark",
                                                    "cagr_gap_pp", "excess_net", "turnover", "strategy_book")}
    if "paired_against_running_book" in out:
        show["paired"] = {k: v for k, v in out["paired_against_running_book"].items() if k != "series"}
    print(json.dumps(show, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=["stage0", "A", "B", "T3", "T4", "T5", "W"])
    a = ap.parse_args()
    if a.part == "stage0":
        stage0()
    elif a.part == "W":
        run_wide()
    else:
        run(a.part)


if __name__ == "__main__":
    main()
