"""
3h — slow momentum held in delivery, measured from NSE's daily bhavcopies.

Pre-registration: docs/research/prereg-3h-slow-momentum-delivery.md. Read it
first; every rule below is a transcription of it, and the results file
cites this file's commit hash after the prereg's.

Stage 0 (no look): coverage of the downloaded bhavcopies and universe size
at every month-end. Stage 1 (trial 119; run 1 = trial 118 was VOID, see the
prereg's amendment 2): the strategy against its equal-weighted universe
benchmark, net of Zerodha's delivery charges.

Usage (from backend/):
    .venv/bin/python research/slow_momentum.py stage0
    .venv/bin/python research/slow_momentum.py stage1 [--held-out]

Reads backend/data/bhav_daily/*.zip (gitignored) plus symbolchange.csv and
EQUITY_L.csv in the same folder. Writes docs/research/data/slow_momentum_*.json.
Nothing here is imported by the live path.
"""

import argparse
import bisect
import collections
import datetime
import json
import math
import os
import pickle
import statistics as st
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

import evaluation  # noqa: E402

DATA_DIR = os.path.join(BACKEND, "data", "bhav_daily")
OUT_DIR = os.path.join(BACKEND, "..", "docs", "research", "data")
CACHE = os.path.join(DATA_DIR, "parsed.pkl")

# --- pre-registered constants ---------------------------------------------
SELECTION_START = "2010-01"      # first month-end with a signal
SELECTION_END = "2025-12"
HALF_SPLIT = "2018-01"           # second half starts here
HELD_OUT_START = "2026-01"
N_HOLD = 15
RANK_KEEP = 30
UNIVERSE_N = 200
MIN_HISTORY = 250
MIN_PRICE = 20.0
LIQ_WINDOW = 126
VOL_WINDOW = 252
N_TRIALS = 119                   # run 1 (void, data defect) counted; this is run 2
CAPITAL = 100000.0
CAPITAL_COLUMNS = (100000.0, 5500.0, 300000.0)

# per-leg costs, as fractions of the leg value (Zerodha CNC, 2026 tariff)
STT = 0.0010
STAMP_BUY = 0.00015
NSE_TXN = 0.0000307
SEBI = 0.000001
GST = 0.18
SLIPPAGE = 0.0005
DP_PER_SELL = 15.34 * 1.18      # ₹ per scrip per sell-day, GST included

# Corporate actions (amendment 2). NSE's PREVCLOSE is never adjusted for a
# split or bonus, so the only tell is the price itself: a one-day drop of
# 25% or more whose ratio snaps (within 10%) to a standard split/bonus factor
# AND whose traded quantity scales by about the same factor (share-count
# conservation; median implied quantity over 20 sessions either side within
# [0.5f, 2f]). Factors below 4/3 (1:4, 1:5 bonuses) are deliberately left
# out: a −17% or −20% day is too often a real crash.
CA_MIN_DROP = -0.25
CA_FACTORS = (4 / 3, 1.5, 5 / 3, 2, 2.5, 3, 4, 5, 6, 8, 10, 20, 25, 50, 100)
CA_SNAP_TOL = 0.10
CA_QTY_WINDOW = 20
CA_QTY_BAND = (0.5, 2.0)
PREVCLOSE_MISMATCH = 0.02       # PREVCLOSE ≠ prior close: a MISSING SESSION, reported in stage 0


def buy_cost(value):
    pct = STT + STAMP_BUY + NSE_TXN + SEBI + GST * (NSE_TXN + SEBI) + SLIPPAGE
    return value * pct


def sell_cost(value, dp=True):
    pct = STT + NSE_TXN + SEBI + GST * (NSE_TXN + SEBI) + SLIPPAGE
    return value * pct + (DP_PER_SELL if dp else 0.0)


# --- loading ----------------------------------------------------------------

def _load_symbol_chains(symbolchange_csv):
    """old symbol -> new symbol, from NSE's symbolchange.csv."""
    nxt = {}
    for line in open(symbolchange_csv, errors="ignore"):
        p = [x.strip() for x in line.rsplit(",", 3)]
        if len(p) == 4 and p[1] and p[2] and p[1] != p[2] and p[1].upper() != "SM_KEY_SYMBOL":
            nxt[p[1]] = p[2]
    return nxt


def _canonical(sym, nxt, cache):
    if sym in cache:
        return cache[sym]
    seen = [sym]
    cur = sym
    while cur in nxt and nxt[cur] not in seen:
        cur = nxt[cur]
        seen.append(cur)
    for s in seen:
        cache[s] = cur
    return cur


def load_all(data_dir=DATA_DIR, refresh=False):
    """Returns (sessions, chains). sessions: sorted list of ISO dates.
    chains: canonical -> dict(idx=[...], close=[...], val=[...], prev=[...])
    with idx the position in `sessions`. Corporate actions already applied."""
    if os.path.exists(CACHE) and not refresh:
        with open(CACHE, "rb") as fh:
            return pickle.load(fh)
    nxt = _load_symbol_chains(os.path.join(data_dir, "symbolchange.csv"))
    cache = {}
    files = sorted(f for f in os.listdir(data_dir) if f.endswith(".zip"))
    by_date = {}
    t0 = time.time()
    for i, f in enumerate(files):
        try:
            rows = _parse(os.path.join(data_dir, f))
        except Exception as exc:  # a saved 404 page under a .zip name, say
            print(f"skip {f}: {exc}")
            continue
        for sym, d, close, prev, isin, val in rows:
            if close <= 0:
                continue
            by_date.setdefault(d, []).append((sym, close, prev, isin, val))
        if i % 500 == 0:
            print(f"parsed {i}/{len(files)} {time.time() - t0:.0f}s", flush=True)
    sessions = sorted(by_date)
    chains = {}
    isin_owner = {}
    isin_merges = 0
    for idx, d in enumerate(sessions):
        for sym, close, prev, isin, val in by_date[d]:
            canon = _canonical(sym, nxt, cache)
            if isin:
                prior = isin_owner.get(isin)
                if prior is None:
                    isin_owner[isin] = canon
                elif prior != canon:
                    # the same security under a symbol symbolchange.csv missed
                    cache[canon] = prior
                    cache[sym] = prior
                    canon = prior
                    isin_merges += 1
            c = chains.setdefault(canon, {"idx": [], "close": [], "prev": [], "val": []})
            if c["idx"] and c["idx"][-1] == idx:
                continue  # duplicate row for the day
            c["idx"].append(idx)
            c["close"].append(close)
            c["prev"].append(prev)
            c["val"].append(val)
    ca = _apply_corporate_actions(chains)
    meta = {"files": len(files), "sessions": len(sessions), "chains": len(chains),
            "isin_merges": isin_merges, **ca}
    out = (sessions, chains, meta)
    with open(CACHE, "wb") as fh:
        pickle.dump(out, fh)
    print(json.dumps(meta))
    return out


def _parse(path):
    """EQ rows (symbol, iso date, close, prev_close, isin, traded value ₹) from either NSE format."""
    import csv
    import io
    import zipfile
    z = zipfile.ZipFile(path)
    out = []
    with z.open(z.namelist()[0]) as fh:
        for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="ignore")):
            r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
            if "TckrSymb" in r:  # July 2024 onward
                if r.get("SctySrs") != "EQ":
                    continue
                out.append((r["TckrSymb"], r["TradDt"], float(r["ClsPric"] or 0), float(r["PrvsClsgPric"] or 0),
                            r.get("ISIN", ""), float(r.get("TtlTrfVal") or 0)))
            elif "SYMBOL" in r:
                if r.get("SERIES") != "EQ":
                    continue
                ts = r["TIMESTAMP"]
                try:
                    d = datetime.datetime.strptime(ts, "%d-%b-%Y").date().isoformat()
                except ValueError:
                    d = datetime.datetime.strptime(ts, "%d-%b-%y").date().isoformat()
                out.append((r["SYMBOL"], d, float(r["CLOSE"] or 0), float(r["PREVCLOSE"] or 0),
                            r.get("ISIN", ""), float(r.get("TOTTRDVAL") or 0)))
    return out


def _snap_factor(ratio):
    """Nearest standard factor within CA_SNAP_TOL of the one-day ratio, else None."""
    f = min(CA_FACTORS, key=lambda x: abs(x - ratio))
    return f if abs(f / ratio - 1) <= CA_SNAP_TOL else None


def _apply_corporate_actions(chains):
    """Amendment 2: detect splits/bonuses from the price and the traded
    quantity, never from PREVCLOSE. PREVCLOSE mismatches on contiguous rows
    are counted as missing sessions and returned for the stage-0 report."""
    n_ca, n_nosnap, n_qty_reject, n_mismatch = 0, 0, 0, 0
    mismatches = []
    for name, c in chains.items():
        close, prev, idx, val = c["close"], c["prev"], c["idx"], c["val"]
        n = len(close)
        factors = [1.0] * n
        for i in range(1, n):
            if idx[i] - idx[i - 1] == 1 and prev[i] > 0 and abs(prev[i] / close[i - 1] - 1) > PREVCLOSE_MISMATCH:
                n_mismatch += 1
                if len(mismatches) < 400:
                    mismatches.append((name, i))
            if close[i - 1] <= 0:
                continue
            r = close[i] / close[i - 1] - 1
            if r > CA_MIN_DROP:
                continue
            f = _snap_factor(close[i - 1] / close[i])
            if f is None:
                n_nosnap += 1
                continue
            lo, hi = max(0, i - CA_QTY_WINDOW), min(n, i + CA_QTY_WINDOW)
            qb = [v / p for v, p in zip(val[lo:i], close[lo:i]) if p > 0 and v > 0]
            qa = [v / p for v, p in zip(val[i:hi], close[i:hi]) if p > 0 and v > 0]
            if not qb or not qa:
                n_qty_reject += 1
                continue
            q = st.median(qa) / st.median(qb)
            if not (CA_QTY_BAND[0] * f <= q <= CA_QTY_BAND[1] * f):
                n_qty_reject += 1
                continue
            n_ca += 1
            for j in range(i):
                factors[j] /= f
        c["close"] = [cl * fa for cl, fa in zip(close, factors)]
        del c["prev"]
    return {"ca_detected": n_ca, "ca_nosnap": n_nosnap, "ca_qty_reject": n_qty_reject,
            "prevclose_mismatches_contiguous": n_mismatch}


# --- calendar helpers -------------------------------------------------------

def month_ends(sessions):
    """Last session of each calendar month -> list of (yyyy-mm, idx)."""
    out = []
    for i, d in enumerate(sessions):
        if i + 1 == len(sessions) or sessions[i + 1][:7] != d[:7]:
            out.append((d[:7], i))
    return out


def close_on_or_before(chain, idx):
    """Chain's last close at or before session idx, or None."""
    k = bisect.bisect_right(chain["idx"], idx) - 1
    return chain["close"][k] if k >= 0 else None


def rows_before(chain, idx):
    return bisect.bisect_right(chain["idx"], idx)


# --- the universe and the signal ---------------------------------------------

def universe_at(chains, idx):
    """Top-200 by median traded value over the trailing 126 sessions (absent
    days count as zero), with >= 250 sessions of history and close >= 20."""
    cands = []
    for name, c in chains.items():
        k = rows_before(c, idx)
        if k < MIN_HISTORY or c["idx"][k - 1] != idx:
            continue  # must have traded on the month-end itself
        if c["close"][k - 1] < MIN_PRICE:
            continue
        lo = bisect.bisect_left(c["idx"], idx - LIQ_WINDOW + 1)
        vals = c["val"][lo:k] + [0.0] * (LIQ_WINDOW - (k - lo))
        cands.append((st.median(vals), name))
    cands.sort(reverse=True)
    return [n for _, n in cands[:UNIVERSE_N]]


def scores_at(chains, names, me_idx_by_month, month, idx):
    """score = mean(r6/sigma, r12/sigma), returns measured to month-end t-1."""
    months = sorted(me_idx_by_month)
    pos = months.index(month)
    if pos < 13:
        return {}
    i1, i7, i13 = (me_idx_by_month[months[pos - k]] for k in (1, 7, 13))
    out = {}
    for n in names:
        c = chains[n]
        c1, c7, c13 = close_on_or_before(c, i1), close_on_or_before(c, i7), close_on_or_before(c, i13)
        if not (c1 and c7 and c13):
            continue
        k = rows_before(c, idx)
        lo = max(0, k - VOL_WINDOW - 1)
        cl = c["close"][lo:k]
        rets = [cl[j] / cl[j - 1] - 1 for j in range(1, len(cl)) if cl[j - 1] > 0]
        if len(rets) < 60:
            continue
        sigma = st.pstdev(rets)
        if sigma <= 0:
            continue
        out[n] = ((c1 / c7 - 1) / sigma + (c1 / c13 - 1) / sigma) / 2
    return out


# --- the simulation ------------------------------------------------------------

class Book:
    def __init__(self, capital, dp=True):
        self.cash = capital
        self.pos = {}           # name -> shares
        self.dp = dp
        self.buys = self.sells = 0
        self.cost_paid = 0.0
        self.turnover_value = 0.0
        self.unbuyable = 0
        self.forced_exits = 0

    def value(self, chains, idx):
        v = self.cash
        for n, sh in self.pos.items():
            px = close_on_or_before(chains[n], idx)
            v += sh * (px or 0.0)
        return v

    def sell(self, name, px):
        sh = self.pos.pop(name)
        val = sh * px
        c = sell_cost(val, self.dp)
        self.cash += val - c
        self.cost_paid += c
        self.turnover_value += val
        self.sells += 1

    def buy(self, name, px, amount):
        if amount <= 0 or px <= 0:
            return
        c = buy_cost(amount)
        sh = (amount - c) / px
        if px > amount:
            self.unbuyable += 1
        self.pos[name] = self.pos.get(name, 0.0) + sh
        self.cash -= amount
        self.cost_paid += c
        self.turnover_value += amount
        self.buys += 1


def fill_idx(sessions, me_idx):
    """The session after the month-end: where every trade fills."""
    return me_idx + 1 if me_idx + 1 < len(sessions) else None


def fill_price(chains, name, idx):
    c = chains[name]
    k = bisect.bisect_left(c["idx"], idx)
    if k < len(c["idx"]) and c["idx"][k] == idx:
        return c["close"][k]
    return close_on_or_before(c, idx)   # no trade that day: last close


def simulate(sessions, chains, start_month, end_month, capital, dp=True):
    mes = month_ends(sessions)
    me_idx = {m: i for m, i in mes}
    strat, bench, bh = Book(capital, dp), Book(capital, dp=False), Book(capital, dp=False)
    series = []   # (month, fill_date, strat_value, bench_value, bh_value)
    prev_universe = None
    ranks_log = []
    for month, idx in mes:
        if month < start_month or month > end_month:
            continue
        f = fill_idx(sessions, idx)
        if f is None:
            break
        uni = universe_at(chains, idx)
        sc = scores_at(chains, uni, me_idx, month, idx)
        if not sc:
            continue  # amendment 2: the series starts at the first month-end with a signal
        ranked = sorted(sc, key=sc.get, reverse=True)
        rank = {n: i + 1 for i, n in enumerate(ranked)}
        uset = set(uni)
        # --- strategy
        for n in list(strat.pos):
            ended = chains[n]["idx"][-1] < idx   # no trade since before this month-end: delisted
            if ended:
                strat.forced_exits += 1
            if ended or n not in uset or rank.get(n, 10 ** 6) > RANK_KEEP:
                strat.sell(n, fill_price(chains, n, f) or 0.0)
        vac = N_HOLD - len(strat.pos)
        if vac > 0:
            per = strat.cash / vac
            for n in ranked:
                if vac == 0:
                    break
                if n in strat.pos:
                    continue
                strat.buy(n, fill_price(chains, n, f) or 0.0, per)
                vac -= 1
        # --- benchmark: EW universe at entry, churn only
        if prev_universe is None:
            per = bench.cash / len(uni)
            for n in uni:
                bench.buy(n, fill_price(chains, n, f) or 0.0, per)
            per = bh.cash / len(uni)
            for n in uni:
                bh.buy(n, fill_price(chains, n, f) or 0.0, per)
        else:
            for n in list(bench.pos):
                ended = chains[n]["idx"][-1] < idx
                if ended or n not in uset:
                    bench.sell(n, fill_price(chains, n, f) or 0.0)
            entrants = [n for n in uni if n not in bench.pos]
            if entrants:
                per = bench.cash / len(entrants)
                for n in entrants:
                    bench.buy(n, fill_price(chains, n, f) or 0.0, per)
            for n in list(bh.pos):
                if chains[n]["idx"][-1] < idx:
                    bh.sell(n, fill_price(chains, n, f) or 0.0)
        prev_universe = uni
        series.append((month, sessions[f], strat.value(chains, f), bench.value(chains, f), bh.value(chains, f)))
        ranks_log.append({"month": month, "universe": len(uni), "scored": len(sc)})
    return series, strat, bench, bh, ranks_log


# --- statistics -----------------------------------------------------------------

def monthly_returns(values):
    return [values[i] / values[i - 1] - 1 for i in range(1, len(values))]


def describe(values, months):
    r = monthly_returns(values)
    n_years = (len(r)) / 12
    cagr = (values[-1] / values[0]) ** (1 / n_years) - 1 if n_years > 0 else None
    vol = st.pstdev(r) * math.sqrt(12) if len(r) > 1 else None
    peak, mdd = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return {"cagr": cagr, "ann_vol": vol, "sharpe_rf0": (cagr / vol) if (cagr is not None and vol) else None,
            "max_drawdown": mdd, "worst_month": min(r), "best_month": max(r),
            "months_positive": sum(1 for x in r if x > 0), "n_months": len(r),
            "start": months[0], "end": months[-1]}


def t_stat(xs):
    if len(xs) < 2:
        return None
    sd = st.stdev(xs)
    return (st.mean(xs) / sd * math.sqrt(len(xs))) if sd > 0 else None


def excess_block(strat_vals, bench_vals, months):
    rs, rb = monthly_returns(strat_vals), monthly_returns(bench_vals)
    ex = [a - b for a, b in zip(rs, rb)]
    m = months[1:]
    h1 = [e for e, mo in zip(ex, m) if mo < HALF_SPLIT]
    h2 = [e for e, mo in zip(ex, m) if mo >= HALF_SPLIT]
    return {"mean_monthly": st.mean(ex), "sd_monthly": st.stdev(ex), "t": t_stat(ex), "n": len(ex),
            "half1": {"mean": st.mean(h1) if h1 else None, "t": t_stat(h1), "n": len(h1)},
            "half2": {"mean": st.mean(h2) if h2 else None, "t": t_stat(h2), "n": len(h2)},
            "series": ex}


# --- stages ----------------------------------------------------------------------

def stage0(sessions, chains, meta):
    per_year = collections.Counter(d[:4] for d in sessions)
    mes = month_ends(sessions)
    # a file within 3 sessions of every calendar month-end: the month-end
    # session must fall in the month's last 5 calendar days
    late = []
    for m, i in mes:
        d = datetime.date.fromisoformat(sessions[i])
        nxt = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        if (nxt - d).days > 5:
            late.append((m, sessions[i]))
    uni_counts = {}
    for m, i in mes:
        if m >= SELECTION_START:
            uni_counts[m] = len(universe_at(chains, i))
    short = {m: n for m, n in uni_counts.items() if n < UNIVERSE_N}
    gate1 = all(per_year.get(str(y), 0) >= 240 for y in range(2009, 2026)) and not late
    gate2 = not short
    out = {"meta": meta, "files_per_year": dict(sorted(per_year.items())), "month_ends_late": late,
           "universe_size_by_month": uni_counts, "months_short_of_200": short,
           "gate1_coverage": gate1, "gate2_universe": gate2, "pass": gate1 and gate2}
    _write("slow_momentum_stage0.json", out)
    print(json.dumps({k: v for k, v in out.items() if k not in ("universe_size_by_month",)}, indent=1))
    return out


def stage1(sessions, chains, meta, held_out=False):
    global STT, STAMP_BUY, NSE_TXN, SEBI, SLIPPAGE, DP_PER_SELL
    start, end = (HELD_OUT_START, "2099-12") if held_out else (SELECTION_START, SELECTION_END)
    result = {"prereg": "prereg-3h-slow-momentum-delivery.md", "held_out": held_out,
              "n_trials": N_TRIALS, "meta": meta, "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
              "costs": {"buy_pct": buy_cost(1.0), "sell_pct_ex_dp": sell_cost(1.0, dp=False),
                        "dp_per_sell_inr": DP_PER_SELL}}
    # gross-of-cost run: zero every cost
    saved = (STT, STAMP_BUY, NSE_TXN, SEBI, SLIPPAGE, DP_PER_SELL)
    runs = {}
    for cap in CAPITAL_COLUMNS:
        series, strat, bench, bh, log = simulate(sessions, chains, start, end, cap)
        runs[cap] = (series, strat, bench, bh, log)
    STT = STAMP_BUY = NSE_TXN = SEBI = SLIPPAGE = 0.0
    DP_PER_SELL = 0.0
    g_series, g_strat, g_bench, g_bh, _ = simulate(sessions, chains, start, end, CAPITAL)
    STT, STAMP_BUY, NSE_TXN, SEBI, SLIPPAGE, DP_PER_SELL = saved

    series, strat, bench, bh, log = runs[CAPITAL]
    months = [s[0] for s in series]
    sv, bv, hv = [s[2] for s in series], [s[3] for s in series], [s[4] for s in series]
    gsv, gbv = [s[2] for s in g_series], [s[3] for s in g_series]
    n_years = max(1e-9, (len(series) - 1) / 12)
    ex = excess_block(sv, bv, months)
    gex = excess_block(gsv, gbv, months)
    dsr = evaluation.deflated_sharpe_ratio(ex["series"], N_TRIALS)
    d_s, d_b, d_h = describe(sv, months), describe(bv, months), describe(hv, months)
    cagr_gap_pp = (d_s["cagr"] - d_b["cagr"]) * 100 if d_s["cagr"] is not None else None
    round_trips = strat.sells
    passes = {
        "t_gt_2": (ex["t"] or 0) > 2.0 and ex["mean_monthly"] > 0,
        "both_halves_positive": (ex["half1"]["mean"] or 0) > 0 and (ex["half2"]["mean"] or 0) > 0,
        "cagr_gap_ge_2pp": (cagr_gap_pp or 0) >= 2.0,
        "dsr_ge_0_95": (dsr.get("dsr") or 0) >= 0.95,
        "round_trips_ge_100": round_trips >= 100,
    }
    result.update({
        "months": months, "fill_dates": [s[1] for s in series],
        "strategy": d_s, "benchmark_ew_universe": d_b, "buy_and_hold_universe_2010": d_h,
        "strategy_gross": describe(gsv, months), "benchmark_gross": describe(gbv, months),
        "excess_net": {k: v for k, v in ex.items() if k != "series"},
        "excess_gross": {k: v for k, v in gex.items() if k != "series"},
        "excess_net_series": ex["series"],
        "dsr": dsr, "cagr_gap_pp": cagr_gap_pp,
        "turnover": {"one_sided_pct_of_avg_book_per_year": strat.turnover_value / 2 / st.mean(sv) / n_years * 100,
                     "buys": strat.buys, "sells": strat.sells, "forced_exits": strat.forced_exits,
                     "unbuyable_picks": strat.unbuyable,
                     "cost_paid_inr": strat.cost_paid,
                     "cost_pct_of_avg_book_per_year": strat.cost_paid / st.mean(sv) / n_years * 100},
        "benchmark_turnover": {"buys": bench.buys, "sells": bench.sells, "cost_paid_inr": bench.cost_paid},
        "capital_columns": {str(int(cap)): {"strategy": describe([s[2] for s in r[0]], months),
                                            "cost_paid_inr": r[1].cost_paid,
                                            "excess_net": {k: v for k, v in excess_block([s[2] for s in r[0]], [s[3] for s in r[0]], months).items() if k != "series"}}
                            for cap, r in runs.items()},
        "universe_log": log,
        "pass_rule": passes, "PASS": all(passes.values()),
        "values": {"strategy": sv, "benchmark": bv, "buy_and_hold": hv},
    })
    name = "slow_momentum_stage1_heldout.json" if held_out else "slow_momentum_stage1.json"
    _write(name, result)
    summary = {k: result[k] for k in ("strategy", "benchmark_ew_universe", "excess_net", "excess_gross",
                                       "dsr", "cagr_gap_pp", "turnover", "pass_rule", "PASS")}
    print(json.dumps(summary, indent=1, default=str))
    return result


def _write(name, obj):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, name), "w") as fh:
        json.dump(obj, fh, indent=1, default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["stage0", "stage1"])
    ap.add_argument("--held-out", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="re-parse the zips instead of using parsed.pkl")
    a = ap.parse_args()
    sessions, chains, meta = load_all(refresh=a.refresh)
    if a.stage == "stage0":
        stage0(sessions, chains, meta)
    else:
        stage1(sessions, chains, meta, held_out=a.held_out)


if __name__ == "__main__":
    main()
