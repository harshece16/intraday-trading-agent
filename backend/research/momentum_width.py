"""
Universe width: does the 3i momentum rule hold in less-traded stocks, and is
a wider book better than the one running? Stage 0 (look L41), A' and B'
(trial 126, look L42: trial 120 and L38 on the repaired price panel of #175
with honest fills), the tiers T3/T4/T5 (looks L43 to L45) and the wide book
W (trial 127).

Pre-registration: docs/research/prereg-universe-width.md with amendments 1
to 3. Every rule here is a transcription of them, and their commits precede
this version of the file.

Usage (from backend/):
    .venv/bin/python research/momentum_width.py stage0     # data gate, no strategy return
    .venv/bin/python research/momentum_width.py A          # A', then B
    .venv/bin/python research/momentum_width.py T3         # then T4, T5
    .venv/bin/python research/momentum_width.py W          # needs A' and the tier outputs

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
LOW_PRICE, TICK = 20.0, 0.05  # below Rs 20 a band is also matched to within one tick
BUY_CARRY = 5                # sessions after the fill day a buy may be carried
ENDED_LOOKBACK = 20          # rows checked for BE/BZ when a chain has ended
# E-3i rank at the month-end -> slippage per side (base, stress)
SLIPPAGE = ((200, 0.0005, 0.0010), (400, 0.0015, 0.0030), (600, 0.0025, 0.0050), (1000, 0.0040, 0.0080))
SLIPPAGE_BEYOND = (0.0075, 0.0150)
MIN_MONTHS = 120
K_CHOICES = (800, 600, 400)  # K is 800; a smaller one only if 800 has too few months

PARTS = {
    "A": {"list": "e3i", "ranks": (1, 200), "flat": 0.0005, "label": "A' (trial 120 re-run)"},
    "B": {"list": "e3i", "ranks": (201, 400), "flat": 0.0010, "label": "B' (L38 re-run)"},
    "T3": {"list": "ewide", "ranks": (401, 600), "label": "T3, ranks 401-600"},
    "T4": {"list": "ewide", "ranks": (601, 800), "label": "T4, ranks 601-800"},
    "T5": {"list": "ewide", "ranks": (801, 1000), "label": "T5, ranks 801-1,000"},
}
TIERS = ("T3", "T4", "T5")
LEDGER = {"A": "trial 126", "B": "look L42", "T3": "look L43", "T4": "look L44", "T5": "look L45",
          "W": "trial 127"}
T_TIER = 2.13                # one-sided 5%, Bonferroni across three tiers
N_FAMILY = 10                # trials 118-120, L38, A', B', T3, T4, T5, W
T_FAMILY = 2.807             # two-sided 5%, Bonferroni across ten
T_PAIRED = 1.65              # one-sided 5%
Z_POWER_80 = 0.8416

STAGE0_UNIVERSE_PARITY_MIN = 0.995
STAGE0_CONSISTENT_MIN = 0.97
STAGE0_TOP = 1000
JUMP = 0.30
JUMP_WINDOW = 5              # sessions either side of the jump
STAGE0_MAX_ROUNDS = 2        # fix-and-re-run rounds allowed
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


def screens_failed(c, idx, median):
    """Which of the screens S1, S2 and S3 the repaired panel's chain fails.
    A row with no traded value is not a traded day."""
    k = m3.rows_before(c, idx)
    out = []
    if any(s != EQ for s in c["ser"][bisect.bisect_left(c["idx"], idx - S1_WINDOW + 1):k]):
        out.append("S1")
    lo = bisect.bisect_left(c["idx"], idx - m3.LIQ_WINDOW + 1)
    if sum(1 for v in c["val"][lo:k] if v > 0) < S2_MIN_DAYS:
        out.append("S2")
    if median < S3_MIN_MEDIAN:
        out.append("S3")
    return out


def passes_screens(c, idx, median):
    return not screens_failed(c, idx, median)


def universes(sessions, chains, screens=True):
    """month -> the E-3i list, the E-wide list, and each name's E-3i rank and
    median traded value at that month-end."""
    eq = eq_view(chains)
    out = {}
    for month, idx in m3.month_ends(sessions):
        if month < m3.SELECTION_START:
            continue
        full = ranked(eq, idx)
        failed = {}
        if screens:
            for v, n in full:
                why = screens_failed(chains[n], idx, v)
                if why:
                    failed[n] = why
        out[month] = {
            "e3i": [n for _, n in full],
            "ewide": [n for _, n in full if n not in failed] if screens else [],
            "failed": failed,
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
    at_high, at_low = close >= c["high"][j] - 1e-9, close <= c["low"][j] + 1e-9
    for b in BANDS:
        up = b - BAND_INSIDE <= ret <= b + BAND_OUTSIDE
        down = -b - BAND_OUTSIDE <= ret <= -b + BAND_INSIDE
        if prev < LOW_PRICE:
            up = up or abs(close - prev * (1 + b)) <= TICK + 1e-9
            down = down or abs(close - prev * (1 - b)) <= TICK + 1e-9
        if at_high and up:
            return 1
        if at_low and down:
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
        self.cost = self.turnover = self.turnover_last_row = 0.0
        self.count = collections.Counter()
        self.participation = {}     # year -> largest buy as a share of median daily value
        self.ended = []             # every held chain that ended (rule H5)

    def value(self, chains, idx):
        return self.cash + sum(sh * (m3.close_on_or_before(chains[n], idx) or 0.0) for n, sh in self.pos.items())

    def _sold(self, name, px, slip):
        v = self.pos.pop(name) * px
        c = v * (m3.STT + m3.NSE_TXN + m3.SEBI + m3.GST * (m3.NSE_TXN + m3.SEBI) + slip) + (m3.DP_PER_SELL if self.dp else 0.0)
        self.cash += v - c
        self.cost += c
        self.turnover += v
        self.sells += 1
        self._last_row(v, slip)
        return v - c

    def _last_row(self, value, slip):
        if slip in SLIPPAGE_BEYOND:
            self.count["fills_at_last_slippage_row"] += 1
            self.turnover_last_row += value

    def _bought(self, name, px, amount, slip):
        if amount <= 0 or px <= 0:
            return
        c = amount * (m3.STT + m3.STAMP_BUY + m3.NSE_TXN + m3.SEBI + m3.GST * (m3.NSE_TXN + m3.SEBI) + slip)
        self.pos[name] = self.pos.get(name, 0.0) + (amount - c) / px
        self.cash -= amount
        self.cost += c
        self.turnover += amount
        self.buys += 1
        self._last_row(amount, slip)

    def sell_ended(self, name, c, slip, month):
        """Rule H5: a holding whose chain has ended is sold at its last close;
        in the stress case a chain that ended in trade-for-trade pays nothing."""
        self.forced += 1
        self.count["ended"] += 1
        t2t = ended_in_t2t(c)
        record = {"symbol": name, "month": month, "last_close": c["raw"][-1], "ended_in_t2t": t2t,
                  "last_series": nse_prices.WIDE_SERIES[c["ser"][-1]] if "ser" in c else "EQ",
                  "value_at_last_close": self.pos[name] * c["close"][-1]}
        self.ended.append(record)
        if t2t:
            self.count["ended_in_t2t"] += 1
            if self.stress:
                self.pos.pop(name)
                self.sells += 1
                record["proceeds"] = 0.0
                return
        record["proceeds"] = self._sold(name, c["close"][-1], slip)

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
            elif not k or c["idx"][k - 1] != s or c["val"][k - 1] <= 0:
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
                strat.sell_ended(n, chains[n], slippage(n, uni, cfg, stress), month)
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
                    bench.sell_ended(n, chains[n], slippage(n, uni, cfg, stress), month)
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
            "share_of_turnover_at_last_slippage_row": book.turnover_last_row / book.turnover if book.turnover else 0.0,
            "ended_chains_held": book.ended,
            "largest_buy_share_of_median_day": {y: round(v, 5) for y, v in sorted(book.participation.items())}}


def break_even_slippage(ex_mean, strat, bench, sv, bv):
    """The addition to every fill's slippage, per side, that would take the
    mean monthly net excess to zero. First order: it holds the trades fixed."""
    n = len(sv) - 1
    edge = strat.turnover / (st.mean(sv) * n) - bench.turnover / (st.mean(bv) * n)
    return ex_mean / edge if edge > 0 else None


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
            "added_slippage_per_side_that_zeroes_the_excess": break_even_slippage(st.mean(ex), strat, bench, sv, bv),
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
    return nse_prices.load(wide=True)


def consolidations(events, unis, held=()):
    """Every consolidation the repaired panel applied: its ratio, whether the
    chain was inside E-3i ranks 1-400 at the month-end before, and whether a
    book held it."""
    months = sorted(unis)
    out = []
    for canon, _, kind, factor, ex_date, purpose in events:
        if kind != "consolidation":
            continue
        pos = bisect.bisect_left(months, ex_date[:7]) - 1
        out.append({"symbol": canon, "ex_date": ex_date, "ratio": factor, "purpose": purpose,
                    "inside_ranks_1_to_400": pos >= 0 and canon in unis[months[pos]]["e3i"][:400],
                    "held_by_this_book": canon in held})
    return out


def run(part, cfg=None, panel=None, unis=None):
    cfg = cfg or PARTS[part]
    sessions, chains, meta, events = panel or load_panel()
    meta = {k: v for k, v in meta.items() if k != "aliases"}
    unis = unis or universes(sessions, chains)
    replication = "flat" in cfg
    start = m3.SELECTION_START if replication else start_month(unis, cfg["list"], cfg["ranks"][1])
    out = {"prereg": PREREG, "part": part, "ledger": LEDGER[part], "label": cfg["label"], "ranks": list(cfg["ranks"]),
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
        out["consolidations_applied"] = consolidations(
            events, unis, {n for h in base["holdings"] for n in h["holdings"]})
        if part == "A":
            dsr = evaluation.deflated_sharpe_ratio(base["excess_net_series"], m3.N_FAMILY)
            rule = {"t_ge_2_394": (ex["t"] or 0) >= m3.T_GATE_A and ex["mean_monthly"] > 0,
                    "dsr_family_ge_0_95": (dsr.get("dsr") or 0) >= 0.95,
                    "both_halves_positive": both,
                    "last3_positive": (ex["last3"]["mean"] or 0) > 0,
                    "cagr_gap_ge_2pp": base["cagr_gap_pp"] >= 2.0,
                    "round_trips_ge_100": base["strategy_book"]["sells"] >= 100}
            dsr10 = evaluation.deflated_sharpe_ratio(base["excess_net_series"], N_FAMILY)
            out.update({"dsr_family_n3": dsr, "rule_of_trial_120": rule, "SURVIVES": all(rule.values()),
                        "against_the_bar_at_n_10_information": {
                            "t_bound": T_FAMILY, "t_clears": (ex["t"] or 0) >= T_FAMILY, "dsr": dsr10,
                            "would_clear": (ex["t"] or 0) >= T_FAMILY and (dsr10.get("dsr") or 0) >= 0.95}})
        else:
            rule = {"t_ge_1_65": (ex["t"] or 0) >= m3.T_CONFIRM_B and ex["mean_monthly"] > 0,
                    "both_halves_positive": both}
            out.update({"rule_of_L38": rule, "SURVIVES": all(rule.values())})
    else:
        stress = summarise(*simulate(sessions, chains, unis, cfg, m3.CAPITAL, start, stress=True))
        out["stress"] = stress
        if part in TIERS:
            rule = {"base_t_ge_2_13": (ex["t"] or 0) >= T_TIER and ex["mean_monthly"] > 0,
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


def fixed_k(sessions, unis):
    """K for the wide book: 800, or the next smaller choice if the list is
    too short for 120 monthly returns. Decided from list sizes only."""
    for k in K_CHOICES:
        if monthly_returns_available(sessions, unis, start_month(unis, "ewide", k)) >= MIN_MONTHS:
            return k
    return None


def tiers_inside(k):
    return [t for t in TIERS if PARTS[t]["ranks"][1] <= (k or 0)]


def run_wide():
    tiers = {}
    for tier in TIERS:
        with open(os.path.join(OUT_DIR, "momentum_width_%s.json" % tier)) as fh:
            tiers[tier] = json.load(fh)
    with open(os.path.join(OUT_DIR, "momentum_width_A.json")) as fh:
        narrow = json.load(fh)
    panel = load_panel()
    unis = universes(panel[0], panel[1])
    k = fixed_k(panel[0], unis)
    if k is None:
        out = {"prereg": PREREG, "part": "W", "ledger": LEDGER["W"], "testable": False, "k": None}
        _finish("W", out)
        return out
    cfg = {"list": "ewide", "ranks": (1, k), "label": "W, ranks 1-%d" % k}
    out = run("W", cfg, panel, unis)
    inside = tiers_inside(k)
    out["k"] = k
    out["tiers"] = {t: bool(r.get("CONFIRMS")) for t, r in tiers.items()}
    base, ex = out["base"], out["base"]["excess_net"]
    dsr = evaluation.deflated_sharpe_ratio(base["excess_net_series"], N_FAMILY)
    paired = paired_test(base, narrow["base"])
    rule = {"1_t_ge_2_807": (ex["t"] or 0) >= T_FAMILY and ex["mean_monthly"] > 0,
            "2_dsr_family_ge_0_95": (dsr.get("dsr") or 0) >= 0.95,
            "3_both_halves_and_last3_positive": (ex["half1"]["mean"] or 0) > 0 and (ex["half2"]["mean"] or 0) > 0
            and (ex["last3"]["mean"] or 0) > 0,
            "4_cagr_gap_and_round_trips": base["cagr_gap_pp"] >= 2.0 and base["strategy_book"]["sells"] >= 100,
            "5_stress_mean_positive": out["stress"]["excess_net"]["mean_monthly"] > 0,
            "6_better_than_running_book": paired["mean"] > 0 and (paired["t"] or 0) >= T_PAIRED
            and (paired["half1"]["mean"] or 0) > 0 and (paired["half2"]["mean"] or 0) > 0,
            "7_sharpe_not_lower": paired["sharpe_wide"] >= paired["sharpe_running"],
            "8_tiers_inside_k_confirm": all(out["tiers"][t] for t in inside)}
    out.update({"tiers_inside_k": inside, "dsr_family": dsr, "paired_against_running_book": paired,
                "pass_rule": rule, "PASS": all(rule.values()),
                "criterion_6_note": "the wider universe returned more in this sample; the rule did not add more there"
                if rule["6_better_than_running_book"] and paired["difference_in_excess"]["mean"] <= 0 else None,
                "a_prime_survives": bool(narrow.get("SURVIVES")),
                "dsr_project_wide_information": evaluation.deflated_sharpe_ratio(
                    base["excess_net_series"], evaluation.trials_of_record() + 1)})
    _finish("W", out)
    return out


def paired_test(wide, running):
    """W's net monthly return minus A's, over the months both have."""
    rw = dict(zip(wide["months"][1:], m3.mrets(wide["values"]["strategy"])))
    rr = dict(zip(running["months"][1:], m3.mrets(running["values"]["strategy"])))
    bw = dict(zip(wide["months"][1:], m3.mrets(wide["values"]["benchmark"])))
    br = dict(zip(running["months"][1:], m3.mrets(running["values"]["benchmark"])))
    common = sorted(set(rw) & set(rr))
    w, r = [rw[m] for m in common], [rr[m] for m in common]
    diff = [a - b for a, b in zip(w, r)]
    in_benchmarks = [bw[m] - br[m] for m in common]
    in_excess = [d - b for d, b in zip(diff, in_benchmarks)]
    h1, h2 = halves(diff)
    sd = st.stdev(diff)
    held = {h["month"]: set(h["holdings"]) for h in running["holdings"]}
    shared = [len(set(h["holdings"]) & held[h["month"]]) for h in wide["holdings"] if h["month"] in held]
    return {"n": len(diff), "mean": st.mean(diff), "sd": sd, "t": m3.t_of(diff),
            "half1": block(h1), "half2": block(h2),
            "difference_in_excess": block(in_excess), "difference_in_benchmarks": block(in_benchmarks),
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
    kinds = {k for k, _ in nse_prices.parse_purpose(purpose, face_value, repaired=True)}
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
                t["no_trade"] += (nxt - idx) - sum(1 for j in range(a, b) if c["val"][j] > 0)
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


def stage0(round_no=1):
    if not 1 <= round_no <= 1 + STAGE0_MAX_ROUNDS:
        raise SystemExit("stage 0 may be re-run at most %d times" % STAGE0_MAX_ROUNDS)
    old = nse_prices.load()
    rebuilt = nse_prices.build()
    loader_diff = same_panel(old, rebuilt)
    del rebuilt
    parity = engine_parity(old)
    sessions, chains, meta, events = nse_prices.load(refresh=True, wide=True)
    unis = universes(sessions, chains)
    months = sorted(unis)

    per_year = collections.Counter(d[:4] for d in sessions)
    mes = m3.month_ends(sessions)
    late = []
    for m, i in mes:
        d = datetime.date.fromisoformat(sessions[i])
        nxt = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        if (nxt - d).days > 5:
            late.append((m, sessions[i]))
    gate1 = all(per_year.get(str(y), 0) >= 240 for y in range(2009, 2026)) and not late

    # gate 3: the E-3i lists on the repaired panel against 3i's own panel, the
    # two universes that were read (ranks 1-200 and 201-400) taken separately
    bands = {"1-200": (0, 200), "201-400": (200, 400)}
    same, total = collections.Counter(), collections.Counter()
    differences, read_by_3i = [], {}
    for m, i in mes:
        if m not in unis:
            continue
        recorded = m3.ranked_universe(old[1], i)
        read_by_3i[m] = set(recorded[:400])
        for label, (lo, hi) in bands.items():
            a, b = set(recorded[lo:hi]), set(unis[m]["e3i"][lo:hi])
            total[label] += len(a)
            same[label] += len(a & b)
            if a != b:
                differences.append({"month": m, "ranks": label, "only_in_3i": sorted(a - b),
                                    "only_in_repaired": sorted(b - a)})
    universe_parity = {label: same[label] / total[label] if total[label] else 0.0 for label in bands}
    del old

    # gates 5 and 6 cover every chain inside the first 1,000 of either list
    covered = {m: set(unis[m]["e3i"][:STAGE0_TOP]) | set(unis[m]["ewide"][:STAGE0_TOP]) for m in months}

    def member_before(name, date):
        pos = bisect.bisect_left(months, date[:7]) - 1
        return pos >= 0 and name in covered[months[pos]]

    checked, bad = 0, []
    applied = collections.defaultdict(set)
    for canon, k, kind, f, ex_date, purpose in events:
        applied[(canon, ex_date)].add(kind)
        if kind not in ("split", "bonus", "consolidation") or ex_date < "2010-01-01" \
                or not member_before(canon, ex_date):
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
            r = c["close"][j] / c["close"][j - 1] - 1
            if abs(r) <= JUMP:
                continue
            d = sessions[c["idx"][j]]
            if d < "2010-01-01" or not member_before(name, d):
                continue
            lo = sessions[max(0, c["idx"][j - 1] - JUMP_WINDOW)]
            hi = sessions[min(len(sessions) - 1, c["idx"][j] + JUMP_WINDOW)]
            near = [(ex, p, fv) for sym in meta["aliases"].get(name, [name]) for ex, p, fv in actions.get(sym, [])
                    if lo <= ex <= hi and (RX_PRICE_ACTION.search(p) or nse_prices.parse_purpose(p, fv, True))]
            jumps.append({"symbol": name, "date": d, "sessions_since_last_row": c["idx"][j] - c["idx"][j - 1],
                          "adjusted_return": round(r, 4),
                          "raw_return": round(c["raw"][j] / c["raw"][j - 1] - 1, 4),
                          "traded_value": c["val"][j],
                          "actions_in_nse_file": sorted({(ex, p) for ex, p, _ in near}),
                          "not_applied": sorted({(ex, p) for ex, p, fv in near
                                                 if not_applied(p, fv, applied[(name, ex)])})})
    jumps.sort(key=lambda x: x["date"])
    unapplied = [x for x in jumps if x["not_applied"]]

    # what the tiers hold that trial 120 or L38 could have read
    ever_400 = set()
    for m in months:
        ever_400 |= set(unis[m]["e3i"][:400])
    tiers = {}
    for part in TIERS:
        lo, hi = PARTS[part]["ranks"]
        n = seen = ever = 0
        for m in months:
            names = unis[m]["ewide"][lo - 1:hi]
            n += len(names)
            seen += len(set(names) & read_by_3i[m])
            ever += len(set(names) & ever_400)
        tiers[part] = {"member_months": n, "inside_a_universe_3i_read_that_month": seen,
                       "share_from_chains_ever_ranked_1_to_400": ever / n if n else None}
    screened = {}
    for label, (lo, hi) in bands.items():
        t = collections.Counter()
        for m in months:
            for name in unis[m]["e3i"][lo:hi]:
                t["member_months"] += 1
                why = unis[m]["failed"].get(name)
                if why:
                    t["fail_any"] += 1
                    for w in why:
                        t["fail_" + w] += 1
        screened[label] = dict(t)

    sizes = {m: len(unis[m]["ewide"]) for m in months}
    starts = {p: start_month(unis, PARTS[p]["list"], PARTS[p]["ranks"][1]) for p in TIERS}
    for k in K_CHOICES:
        starts["W_%d" % k] = start_month(unis, "ewide", k)
    returns = {p: monthly_returns_available(sessions, unis, v) for p, v in starts.items()}
    boundary = {}
    for m in months:
        if m.endswith("-12") or m == months[-1]:
            ewide, med = unis[m]["ewide"], unis[m]["median"]
            boundary[m] = {str(r): med[ewide[r - 1]] for r in (200, 400, 600, 800, 1000) if len(ewide) >= r}

    gates = {"1_coverage": gate1,
             "2_loader_parity": not loader_diff,
             "3_universe_parity": all(v >= STAGE0_UNIVERSE_PARITY_MIN for v in universe_parity.values()),
             "4_engine_parity": all(p["ok"] for p in parity.values()),
             "5_adjustment_consistency": consistent >= STAGE0_CONSISTENT_MIN,
             "6_no_unapplied_action_behind_a_jump": not unapplied}
    out = {"prereg": PREREG, "ledger": "look L41", "round": round_no,
           "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "meta": {k: v for k, v in meta.items() if k != "aliases"},
           "files_per_year": dict(sorted(per_year.items())), "month_ends_late": late,
           "loader_differences": loader_diff[:50], "engine_parity": parity,
           "universe_parity_share": universe_parity, "universe_differences": differences[:200],
           "universe_differences_total": len(differences),
           "splits_bonuses_consolidations_checked": checked, "inconsistent": bad, "consistent_share": consistent,
           "consolidations_applied": consolidations(events, unis),
           "jumps": jumps, "jumps_total": len(jumps), "jumps_with_an_unapplied_action": len(unapplied),
           "jumps_by_kind": {"on_consecutive_sessions": sum(1 for x in jumps if x["sessions_since_last_row"] == 1),
                             "across_a_gap": sum(1 for x in jumps if x["sessions_since_last_row"] > 1),
                             "up": sum(1 for x in jumps if x["adjusted_return"] > 0),
                             "down": sum(1 for x in jumps if x["adjusted_return"] < 0)},
           "ewide_size_by_month": sizes, "e3i_size_by_month": {m: len(unis[m]["e3i"]) for m in months},
           "start_month": starts, "monthly_returns_available": returns, "k": fixed_k(sessions, unis),
           "tiers_against_what_3i_read": tiers, "screens_inside_ranks_1_to_400": screened,
           "median_traded_value_at_rank": boundary,
           "tradability": tradability_map(sessions, chains, unis),
           "gates": gates, "PASS": all(gates.values())}
    _write("momentum_width_stage0_run%d.json" % round_no, out)
    _write("momentum_width_stage0.json", out)
    keep = ("round", "meta", "engine_parity", "universe_parity_share", "universe_differences_total",
            "loader_differences", "splits_bonuses_consolidations_checked", "consistent_share",
            "consolidations_applied", "jumps_total",
            "jumps_by_kind", "jumps_with_an_unapplied_action", "start_month", "monthly_returns_available", "k",
            "tiers_against_what_3i_read", "screens_inside_ranks_1_to_400", "gates", "PASS")
    print(json.dumps({k: out[k] for k in keep}, indent=1, default=str))
    return out


# --- output ----------------------------------------------------------------------------------

def _write(name, obj):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, name), "w") as fh:
        json.dump(obj, fh, indent=1, default=str)


def _finish(part, out):
    _write("momentum_width_%s.json" % part, out)
    show = {k: out[k] for k in ("part", "ledger", "label", "start_month", "testable", "k", "tiers", "tiers_inside_k",
                                "recorded", "against_the_bar_at_n_10_information", "consolidations_applied",
                                "criterion_6_note", "a_prime_survives",
                                "rule_of_trial_120", "rule_of_L38", "SURVIVES", "confirm_rule", "CONFIRMS",
                                "pass_rule", "PASS", "dsr_family", "gross_excess", "capital_columns") if k in out}
    if "recorded" in show:
        show["recorded"] = {k: v for k, v in show["recorded"].items() if k != "difference_series"}
    for case in ("base", "stress"):
        if case in out:
            show[case] = {k: out[case][k] for k in ("first_month", "last_month", "strategy", "benchmark",
                                                    "cagr_gap_pp", "excess_net", "turnover", "strategy_book",
                                                    "added_slippage_per_side_that_zeroes_the_excess")}
    if "paired_against_running_book" in out:
        show["paired"] = {k: v for k, v in out["paired_against_running_book"].items() if k != "series"}
    print(json.dumps(show, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=["stage0", "A", "B", "T3", "T4", "T5", "W"])
    ap.add_argument("--round", type=int, default=1, help="stage 0 only: 1 for the first run, 2 or 3 for a re-run")
    a = ap.parse_args()
    if a.part == "stage0":
        stage0(a.round)
    elif a.part == "W":
        run_wide()
    else:
        run(a.part)


if __name__ == "__main__":
    main()
