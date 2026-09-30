"""
Sahab Ranker — our own next-month cross-sectional return engine (trials 121
and 122). Pre-registration: docs/research/prereg-ranker-engine.md; every rule
here is a transcription of it, and its commit precedes this file's.

    .venv/bin/python research/ranker.py        # one run: both configurations, all three gates

Inputs are 14 literature signals computed from research/nse_prices.py at each
month-end; C1 weights them by their past rank correlation with next-month
returns, C2 is a ridge regression with a fixed penalty; both are refitted
every month on data whose target is complete. The book is 3i's (15 names,
keep while ranked <= 30, next-session close fills, delivery costs), and the
baseline is 3i's momentum rule over the same months.
"""

import bisect
import collections
import datetime
import json
import math
import os
import statistics as st
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

import evaluation  # noqa: E402
import momentum_3i as m3  # noqa: E402
import nse_prices as npx  # noqa: E402
from splits import HELD_OUT_START as HELD_OUT_FIRST_SESSION  # noqa: E402

OUT = os.path.join(BACKEND, "..", "docs", "research", "data", "ranker_result.json")
FEATURES = ["mom_12_1", "mom_6_1", "mom_3_1", "rev_1", "mom_voladj", "vol_252", "vol_63", "hi52",
            "log_liq", "amihud", "beta", "idio_vol", "div_yield", "log_price"]
MIN_TRAIN_MONTHS = 36
RIDGE_LAMBDA_PER_ROW = 0.1
N_FAMILY = 2
T_GATE1 = 2.24            # two-sided Bonferroni 5% across 2
T_GATE2 = 1.65
T_GATE3 = 1.65
CAPITAL = 1_000_000.0
HALF_SPLIT = None         # the median month of the evaluation window (set at run time)
LAST3_START = "2023-01"


# --- inputs ------------------------------------------------------------------------

def rank_norm(values):
    """dict name -> value (None allowed) -> dict name -> rank in [-0.5, 0.5]; missing -> 0."""
    have = [(v, n) for n, v in values.items() if v is not None and not (isinstance(v, float) and math.isnan(v))]
    out = {n: 0.0 for n in values}
    if len(have) < 2:
        return out
    have.sort()
    i = 0
    while i < len(have):
        j = i
        while j + 1 < len(have) and have[j + 1][0] == have[i][0]:
            j += 1
        r = (i + j) / 2.0
        for k in range(i, j + 1):
            out[have[k][1]] = r / (len(have) - 1) - 0.5
        i = j + 1
    return out


def market_series(sessions, chains, universes, months_idx):
    """Daily equal-weighted return of the point-in-time top-400 (previous month-end's list)."""
    mes = [(m, i) for m, i in months_idx]
    out = {}
    for pos in range(1, len(mes)):
        m_prev, i_prev = mes[pos - 1]
        _, i_cur = mes[pos]
        uni = universes.get(m_prev, [])[:400]
        for i in range(i_prev + 1, i_cur + 1):
            rs = []
            for n in uni:
                c = chains[n]
                k = bisect.bisect_left(c["idx"], i)
                if k < len(c["idx"]) and c["idx"][k] == i and k > 0 and c["idx"][k - 1] == i - 1:
                    rs.append(c["close"][k] / c["close"][k - 1] - 1)
            if rs:
                out[i] = sum(rs) / len(rs)
    return out


def dividend_yield_index(events):
    """chain -> sorted [(row position, D/P)] from the loader's dividend factors."""
    out = collections.defaultdict(list)
    for canon, k, kind, f, ex, purpose in events:
        if kind == "dividend":
            out[canon].append((k, 1.0 - f))
    for v in out.values():
        v.sort()
    return out


def features_at(chains, names, me_idx, months, month, idx, mkt, divs):
    pos = months.index(month)
    if pos < 13:
        return {}
    i_1, i_3, i_6, i_7, i_12, i_13 = (me_idx[months[pos - k]] for k in (1, 3, 6, 7, 12, 13))
    raw = {f: {} for f in FEATURES}
    for n in names:
        c = chains[n]
        k = m3.rows_before(c, idx)
        if k < 60:
            continue
        cl = c["close"]
        ct = cl[k - 1]
        g = lambda i: m3.close_on_or_before(c, i)
        c1, c3, c6, c7, c12, c13 = g(i_1), g(i_3), g(i_6), g(i_7), g(i_12), g(i_13)
        win = cl[max(0, k - 253):k]
        rets = [win[j] / win[j - 1] - 1 for j in range(1, len(win)) if win[j - 1] > 0]
        sig = st.pstdev(rets) if len(rets) > 20 else None
        raw["mom_12_1"][n] = c1 / c12 - 1 if c1 and c12 else None
        raw["mom_6_1"][n] = c1 / c6 - 1 if c1 and c6 else None
        raw["mom_3_1"][n] = c1 / c3 - 1 if c1 and c3 else None
        raw["rev_1"][n] = ct / c1 - 1 if c1 else None
        raw["mom_voladj"][n] = (((c1 / c7 - 1) + (c1 / c13 - 1)) / 2 / sig) if (c1 and c7 and c13 and sig) else None
        raw["vol_252"][n] = sig
        r63 = rets[-63:]
        raw["vol_63"][n] = st.pstdev(r63) if len(r63) > 20 else None
        raw["hi52"][n] = ct / max(win) if win else None
        lo = bisect.bisect_left(c["idx"], idx - m3.LIQ_WINDOW + 1)
        vals = c["val"][lo:k] + [0.0] * (m3.LIQ_WINDOW - (k - lo))
        med = st.median(vals)
        raw["log_liq"][n] = math.log(med) if med > 0 else None
        am = []
        for j in range(max(1, k - 63), k):
            if c["idx"][j] - c["idx"][j - 1] == 1 and c["val"][j] > 0 and cl[j - 1] > 0:
                am.append(abs(cl[j] / cl[j - 1] - 1) / c["val"][j])
        raw["amihud"][n] = st.median(am) if am else None
        xs, ys = [], []
        for j in range(max(1, k - 252), k):
            ii = c["idx"][j]
            if ii in mkt and c["idx"][j - 1] == ii - 1 and cl[j - 1] > 0:
                xs.append(mkt[ii])
                ys.append(cl[j] / cl[j - 1] - 1)
        if len(xs) > 60:
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            vx = sum((x - mx) ** 2 for x in xs)
            beta = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / vx if vx > 0 else None
            if beta is not None:
                res = [y - my - beta * (x - mx) for x, y in zip(xs, ys)]
                raw["beta"][n], raw["idio_vol"][n] = beta, st.pstdev(res)
            else:
                raw["beta"][n] = raw["idio_vol"][n] = None
        else:
            raw["beta"][n] = raw["idio_vol"][n] = None
        dv = divs.get(n, [])
        lo_k = bisect.bisect_left(dv, (k - 252, -1.0))
        hi_k = bisect.bisect_left(dv, (k, -1.0))
        raw["div_yield"][n] = sum(y for _, y in dv[lo_k:hi_k])
        raw["log_price"][n] = math.log(c["raw"][k - 1]) if c["raw"][k - 1] > 0 else None
    ranked = {f: rank_norm(raw[f]) for f in FEATURES}
    return {n: [ranked[f][n] for f in FEATURES] for n in names if n in ranked["mom_12_1"]}


def target_at(chains, names, sessions, idx, idx_next):
    """Rank of total return from the session after idx to the session after idx_next, minus the mean."""
    f0, f1 = idx + 1, idx_next + 1
    if f1 >= len(sessions):
        return {}
    r = {}
    for n in names:
        p0, p1 = m3.close_on_or_before(chains[n], f0), m3.close_on_or_before(chains[n], f1)
        r[n] = p1 / p0 - 1 if p0 and p1 else None
    return rank_norm(r)


# --- models -------------------------------------------------------------------------

def fit_ic(train):
    """train: list of (X rows, y) per month -> weights = mean monthly Pearson(rank X_f, rank y)."""
    w = np.zeros(len(FEATURES))
    count = 0
    for X, y in train:
        if len(y) < 10:
            continue
        X, y = np.asarray(X), np.asarray(y)
        yc = y - y.mean()
        for f in range(X.shape[1]):
            xc = X[:, f] - X[:, f].mean()
            den = math.sqrt(float((xc ** 2).sum() * (yc ** 2).sum()))
            w[f] += float((xc * yc).sum()) / den if den > 0 else 0.0
        count += 1
    return w / count if count else w


def fit_ridge(train):
    X = np.vstack([np.asarray(X) for X, y in train if len(y)])
    y = np.concatenate([np.asarray(y) for X, y in train if len(y)])
    lam = RIDGE_LAMBDA_PER_ROW * len(y)
    return np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ y)


# --- book ----------------------------------------------------------------------------

def simulate(sessions, chains, universes, lo, hi, scores_by_month, slippage, capital, months_eval):
    book, bench = m3.Book(capital, slippage, dp=True), m3.Book(capital, slippage, dp=False)
    mes = dict(m3.month_ends(sessions))
    series, started = [], False
    for month in months_eval:
        idx = mes[month]
        f = idx + 1
        if f >= len(sessions) or sessions[f] >= HELD_OUT_FIRST_SESSION:
            break
        uni = universes[month][lo - 1:hi]
        sc = scores_by_month.get(month) or {}
        if not sc:
            continue
        ranked = sorted(sc, key=sc.get, reverse=True)
        rank = {n: i + 1 for i, n in enumerate(ranked)}
        uset = set(uni)
        for n in list(book.pos):
            ended = chains[n]["idx"][-1] < idx
            book.forced += ended
            if ended or n not in uset or rank.get(n, 10 ** 9) > m3.RANK_KEEP:
                book.sell(n, m3.fill_price(chains, n, f))
        vac = m3.N_HOLD - len(book.pos)
        per = book.cash / vac if vac > 0 else 0
        for n in ranked:
            if vac <= 0:
                break
            if n not in book.pos:
                book.buy(n, m3.fill_price(chains, n, f), per)
                vac -= 1
        if not started:
            per_b = bench.cash / len(uni)
            for n in uni:
                bench.buy(n, m3.fill_price(chains, n, f), per_b)
            started = True
        else:
            for n in list(bench.pos):
                if chains[n]["idx"][-1] < idx or n not in uset:
                    bench.sell(n, m3.fill_price(chains, n, f))
            entrants = [n for n in uni if n not in bench.pos]
            if entrants:
                per_b = bench.cash / len(entrants)
                for n in entrants:
                    bench.buy(n, m3.fill_price(chains, n, f), per_b)
        series.append((month, book.value(chains, f), bench.value(chains, f)))
    return series, book


def stats(series, book, half_split):
    months = [s[0] for s in series]
    sv, bv = [s[1] for s in series], [s[2] for s in series]
    ex = [(sv[i] / sv[i - 1] - 1) - (bv[i] / bv[i - 1] - 1) for i in range(1, len(sv))]
    m = months[1:]
    part = lambda cond: [e for e, mo in zip(ex, m) if cond(mo)]
    h1, h2, l3 = part(lambda mo: mo < half_split), part(lambda mo: mo >= half_split), part(lambda mo: mo >= LAST3_START)
    ds, db = m3.describe(sv), m3.describe(bv)
    return {"months": m, "excess": ex, "mean": st.mean(ex), "t": m3.t_of(ex),
            "half1": st.mean(h1) if h1 else None, "half2": st.mean(h2) if h2 else None,
            "last3": st.mean(l3) if l3 else None, "cagr": ds["cagr"], "bench_cagr": db["cagr"],
            "cagr_gap_pp": (ds["cagr"] - db["cagr"]) * 100, "max_drawdown": ds["max_drawdown"],
            "round_trips": book.sells, "dsr_family": evaluation.deflated_sharpe_ratio(ex, N_FAMILY)}


def paired(a, b, half_split):
    common = [mo for mo in a["months"] if mo in set(b["months"])]
    ea, eb = dict(zip(a["months"], a["excess"])), dict(zip(b["months"], b["excess"]))
    d = [ea[mo] - eb[mo] for mo in common]
    h1 = [ea[mo] - eb[mo] for mo in common if mo < half_split]
    h2 = [ea[mo] - eb[mo] for mo in common if mo >= half_split]
    return {"n": len(d), "mean": st.mean(d), "t": m3.t_of(d), "half1": st.mean(h1) if h1 else None,
            "half2": st.mean(h2) if h2 else None}


# --- run ------------------------------------------------------------------------------

def run():
    sessions, chains, meta, events = npx.load()
    mes = [(m, i) for m, i in m3.month_ends(sessions) if m >= m3.SELECTION_START]
    months = [m for m, _ in m3.month_ends(sessions)]
    me_idx = dict(m3.month_ends(sessions))
    universes = {m: m3.ranked_universe(chains, i) for m, i in mes}
    mkt = market_series(sessions, chains, universes, mes)
    divs = dividend_yield_index(events)
    feat = {"A": {}, "B": {}}
    targ = {"A": {}, "B": {}}
    for pos, (m, i) in enumerate(mes):
        for part, (lo, hi) in (("A", (1, 200)), ("B", (201, 400))):
            names = universes[m][lo - 1:hi]
            feat[part][m] = features_at(chains, names, me_idx, months, m, i, mkt, divs)
            if pos + 1 < len(mes):
                targ[part][m] = target_at(chains, names, sessions, i, mes[pos + 1][1])
    feat_months = [m for m, _ in mes if feat["A"].get(m)]
    # walk-forward scores
    scores = {"C1": {"A": {}, "B": {}}, "C2": {"A": {}, "B": {}}}
    weights_log = {"C1": {}, "C2": {}}
    for pos, m in enumerate(feat_months):
        train_months = feat_months[:max(0, pos - 1)]        # s <= t-2
        train = []
        for s in train_months:
            fx, ty = feat["A"][s], targ["A"].get(s) or {}
            rows = [(fx[n], ty[n]) for n in fx if n in ty]
            if rows:
                train.append(([r[0] for r in rows], [r[1] for r in rows]))
        if len(train) < MIN_TRAIN_MONTHS:
            continue
        w1, w2 = fit_ic(train), fit_ridge(train)
        weights_log["C1"][m], weights_log["C2"][m] = w1.tolist(), w2.tolist()
        for part in ("A", "B"):
            fx = feat[part].get(m) or {}
            for cfg, w in (("C1", w1), ("C2", w2)):
                scores[cfg][part][m] = {n: float(np.dot(w, x)) for n, x in fx.items()}
    eval_months = sorted(scores["C1"]["A"])
    half_split = eval_months[len(eval_months) // 2]
    # the baseline: 3i's momentum score, same months
    base_scores = {"A": {}, "B": {}}
    for m in eval_months:
        for part, (lo, hi) in (("A", (1, 200)), ("B", (201, 400))):
            base_scores[part][m] = m3.scores(chains, universes[m][lo - 1:hi], me_idx, months, m, me_idx[m])
    res = {}
    for part, (lo, hi, slip) in (("A", (1, 200, 0.0005)), ("B", (201, 400, 0.0010))):
        s_base, b_base = simulate(sessions, chains, universes, lo, hi, base_scores[part], slip, CAPITAL, eval_months)
        res[f"baseline_{part}"] = stats(s_base, b_base, half_split)
        for cfg in ("C1", "C2"):
            s_, b_ = simulate(sessions, chains, universes, lo, hi, scores[cfg][part], slip, CAPITAL, eval_months)
            res[f"{cfg}_{part}"] = stats(s_, b_, half_split)
    verdict = {}
    for cfg in ("C1", "C2"):
        a, b = res[f"{cfg}_A"], res[f"{cfg}_B"]
        pa, pb = paired(a, res["baseline_A"], half_split), paired(b, res["baseline_B"], half_split)
        g1 = {"t_ge_2_24": (a["t"] or 0) >= T_GATE1 and a["mean"] > 0,
              "dsr_family_ge_0_95": (a["dsr_family"].get("dsr") or 0) >= 0.95,
              "both_halves_positive": (a["half1"] or 0) > 0 and (a["half2"] or 0) > 0,
              "last3_positive": (a["last3"] or 0) > 0, "cagr_gap_ge_2pp": a["cagr_gap_pp"] >= 2.0,
              "round_trips_ge_100": a["round_trips"] >= 100}
        g2 = {"paired_t_ge_1_65": (pa["t"] or 0) >= T_GATE2 and pa["mean"] > 0,
              "paired_both_halves_positive": (pa["half1"] or 0) > 0 and (pa["half2"] or 0) > 0}
        g3 = {"unseen_t_ge_1_65": (b["t"] or 0) >= T_GATE3 and b["mean"] > 0,
              "unseen_both_halves_positive": (b["half1"] or 0) > 0 and (b["half2"] or 0) > 0,
              "unseen_beats_momentum": pb["mean"] > 0}
        verdict[cfg] = {"gate1": g1, "gate1_pass": all(g1.values()), "paired_vs_momentum_A": pa,
                        "gate2": g2, "gate2_pass": all(g2.values()), "paired_vs_momentum_B": pb,
                        "gate3": g3, "gate3_pass": all(g3.values())}
        verdict[cfg]["ADOPT"] = verdict[cfg]["gate1_pass"] and verdict[cfg]["gate2_pass"] and verdict[cfg]["gate3_pass"]
    adopted = [c for c in ("C1", "C2") if verdict[c]["ADOPT"]]
    choice = max(adopted, key=lambda c: verdict[c]["paired_vs_momentum_A"]["t"] or 0) if adopted else None
    final_w = {cfg: dict(zip(FEATURES, weights_log[cfg][eval_months[-1]])) for cfg in ("C1", "C2")}
    out = {"prereg": "prereg-ranker-engine.md", "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "eval_first": eval_months[0], "eval_last": res["C1_A"]["months"][-1] if res["C1_A"]["months"] else None,
           "half_split": half_split, "results": {k: {kk: vv for kk, vv in v.items() if kk not in ("excess", "months")}
                                                  for k, v in res.items()},
           "verdict": verdict, "adopted": choice, "final_weights": final_w,
           "series": {k: {"months": v["months"], "excess": v["excess"]} for k, v in res.items()}}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    brief = {k: {"mean": round(v["mean"] * 100, 3), "t": round(v["t"] or 0, 2), "half1": v["half1"], "half2": v["half2"],
                 "last3": v["last3"], "cagr": v["cagr"], "bench": v["bench_cagr"], "dsr": v["dsr_family"].get("dsr")}
             for k, v in res.items()}
    print(json.dumps({"eval": [eval_months[0], out["eval_last"]], "results": brief, "verdict": verdict,
                      "adopted": choice, "final_weights": final_w}, indent=1, default=str))
    return out


if __name__ == "__main__":
    run()
