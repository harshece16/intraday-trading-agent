"""Forecast x candlestick combination search — trials 128 to 202.

Pre-registered: docs/research/prereg-combo-search.md (commit 6921f08), before L40's
result was read and before any L46 model ran. This file implements it and nothing
else: 75 combinations, each a directional single-leg trade rule on the L40 sample's
stock-times, net of 16.63 bp a trade, judged by a Bonferroni t over 75, both halves,
and a deflated Sharpe ratio at 75 trials.

Inputs: the rows files of the L40 run of record and of every L46 model (stock-time,
forecast features, realised targets), and the candle cache for the patterns.

    python -m research.combo_search --kronos-rows PATH --l46-rows-dir DIR --out PATH

Pure standard library: runs in any environment.
"""
import argparse
import json
import os
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import candlestick_patterns as cp  # noqa: E402
import evaluation  # noqa: E402
import indicators  # noqa: E402
from research import kronos_feature_ic as k  # noqa: E402
from research import splits  # noqa: E402

COST_BP = 16.63
N_TRIALS = 75
T_BAR = 3.40
MIN_TRADES, MIN_SESSIONS, DSR_BAR = 100, 40, 0.95
SOURCES = ["kronos", "chronos_bolt", "timesfm_2p5", "moirai_2", "flowstate", "tirex", "sundial", "ensemble"]
HORIZONS = ["f15", "f30", "f60"]
RULES = ["R1", "R2", "R3"]
PATTERN_WINDOW = 40


# ---- pure parts ------------------------------------------------------------------

def pattern_direction(patterns):
    """+1 / -1 for a directional pattern of strength >= 2, 0 for none or a conflict."""
    dirs = {+1 if p["bias"] == "bullish" else -1 for p in patterns
            if p["bias"] in ("bullish", "bearish") and p["strength"] >= 2}
    return dirs.pop() if len(dirs) == 1 else 0


def quintile_flags(values):
    """For one decision time: {index: +1 top quintile, -1 bottom quintile}, as the
    harness's quintile_spread cuts them (n // 5 at each end)."""
    n = len(values)
    q = n // 5
    if q < 1:
        return {}
    order = sorted(range(n), key=lambda i: values[i])
    out = {i: -1 for i in order[:q]}
    out.update({i: +1 for i in order[-q:]})
    return out


def rule_direction(rule, forecast, quint, pattern):
    """Trade direction for one stock-time under a rule, 0 for no trade."""
    if rule == "R1":
        if quint == +1 and forecast > COST_BP:
            return +1
        if quint == -1 and forecast < -COST_BP:
            return -1
        return 0
    if rule == "R2":
        return pattern if pattern and forecast * pattern > 0 else 0
    if rule == "R3":
        return pattern if pattern and quint == pattern else 0
    if rule == "R4":
        return pattern
    raise ValueError(rule)


def judge(trades, sessions):
    """trades: [(date, net_bp)]; sessions: the source's session list, for halves."""
    by_day = defaultdict(list)
    for d, net in trades:
        by_day[d].append(net)
    days = sorted(by_day)
    series = [st.mean(by_day[d]) for d in days]
    m, t, se = k.tstat(series)
    first, second = splits.halves(sorted(sessions))
    f_set, s_set = set(first), set(second)
    h1 = [st.mean(by_day[d]) for d in days if d in f_set]
    h2 = [st.mean(by_day[d]) for d in days if d in s_set]
    dsr = evaluation.deflated_sharpe_ratio(series, N_TRIALS) if len(series) >= 10 else {"dsr": None}
    out = {"trades": len(trades), "sessions_with_trades": len(days),
           "mean_net_bp_per_trade": st.mean([x for _, x in trades]) if trades else None,
           "per_session_mean_bp": m, "t": t, "se": se,
           "half1_bp": st.mean(h1) if h1 else None, "half2_bp": st.mean(h2) if h2 else None,
           "dsr": dsr.get("dsr"), "sharpe_per_session": dsr.get("sharpe")}
    checks = {
        "enough_trades": len(trades) >= MIN_TRADES and len(days) >= MIN_SESSIONS,
        "positive_net": (out["mean_net_bp_per_trade"] or 0) > 0,
        "t_over_bonferroni": (t or 0) > T_BAR,
        "both_halves_positive": (out["half1_bp"] or 0) > 0 and (out["half2_bp"] or 0) > 0,
        "dsr_over_bar": (out["dsr"] or 0) >= DSR_BAR,
    }
    out["checks"] = checks
    out["passes"] = all(checks.values())
    return out


# ---- data ---------------------------------------------------------------------------

def load_rows(path):
    rows = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            rows[(r["sym"], r["date"], r["hhmm"])] = r
    return rows


def pattern_map(keys, flat_by_sym, sessions_by_sym):
    """{(sym, date, hhmm): direction} from the closed bars up to the decision bar."""
    pos = {}
    for sym, flat in flat_by_sym.items():
        pos[sym] = {(c["time"][:10], c["time"][11:16]): i for i, c in enumerate(flat)}
    out = {}
    for sym, d, hhmm in keys:
        bars = sessions_by_sym.get(sym, {}).get(d)
        if not bars:
            continue
        i = k.decision_bar_index(bars, hhmm)
        if i is None:
            continue
        idx = pos[sym].get((d, bars[i]["time"][11:16]))
        if idx is None:
            continue
        window = flat_by_sym[sym][max(0, idx - PATTERN_WINDOW + 1): idx + 1]
        atr = indicators.atr(window, 14)
        out[(sym, d, hhmm)] = pattern_direction(cp.detect_patterns(window, atr)) if atr else 0
    return out


def ensemble_rows(sources):
    """Stock-times present in every source: mean percentile rank per horizon, and the
    median forecast in bp as the magnitude for R1."""
    common = set.intersection(*(set(r) for r in sources.values()))
    by_time = defaultdict(list)
    for key in common:
        by_time[(key[1], key[2])].append(key)
    out = {}
    for _, keys in by_time.items():
        for h in HORIZONS:
            pct = defaultdict(list)
            for rows in sources.values():
                vals = [rows[key]["features"][h] for key in keys]
                order = sorted(range(len(keys)), key=lambda i: vals[i])
                for rank, i in enumerate(order):
                    pct[keys[i]].append(rank / max(len(keys) - 1, 1))
            for key in keys:
                row = out.setdefault(key, {"sym": key[0], "date": key[1], "hhmm": key[2], "features": {}, "magnitude": {},
                                           "targets": next(iter(sources.values()))[key]["targets"]})
                row["features"][h] = st.mean(pct[key])
                row["magnitude"][h] = st.median([rows[key]["features"][h] for rows in sources.values()])
    return out


def run_source(rows, patterns, source):
    """All three rules and horizons for one source's rows."""
    by_time = defaultdict(list)
    for key in rows:
        by_time[(key[1], key[2])].append(key)
    trades = {(h, r): [] for h in HORIZONS for r in RULES}
    for _, keys in by_time.items():
        for h in HORIZONS:
            vals = [rows[key]["features"][h] for key in keys]
            flags = quintile_flags(vals)
            for i, key in enumerate(keys):
                target = (rows[key].get("targets") or {}).get(h)
                if target is None or vals[i] is None:
                    continue
                magnitude = rows[key].get("magnitude", {}).get(h, vals[i]) if source == "ensemble" else vals[i]
                for rule in RULES:
                    d = rule_direction(rule, magnitude, flags.get(i, 0), patterns.get(key, 0))
                    if d:
                        trades[(h, rule)].append((key[1], d * target - COST_BP))
    return trades


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kronos-rows", required=True)
    ap.add_argument("--l46-rows-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    import kite_history
    db = os.environ.get("KRONOS_CANDLE_DB")
    if db:
        from pathlib import Path
        kite_history.DB_PATH = Path(db)

    sources, missing = {}, []
    if os.path.exists(args.kronos_rows):
        sources["kronos"] = load_rows(args.kronos_rows)
    else:
        missing.append("kronos")
    for name in SOURCES[1:-1]:
        p = os.path.join(args.l46_rows_dir, "l46_rows_%s.jsonl" % name)
        if os.path.exists(p):
            sources[name] = load_rows(p)
        else:
            missing.append(name)
    if len(sources) >= 2:
        sources["ensemble"] = ensemble_rows({n: r for n, r in sources.items()})
    else:
        missing.append("ensemble")

    all_keys = set().union(*(set(r) for r in sources.values()))
    symbols = sorted({key[0] for key in all_keys})
    pre = kite_history.load_batch(symbols, interval="5m")
    flat_by_sym = {s: sorted(c, key=lambda x: x["time"]) for s, c in pre.items()}
    sessions_by_sym = {s: k.by_session(c) for s, c in flat_by_sym.items()}
    patterns = pattern_map(all_keys, flat_by_sym, sessions_by_sym)

    results, n_run = [], 0
    for name in SOURCES:
        if name not in sources:
            for h in HORIZONS:
                for rule in RULES:
                    results.append({"source": name, "horizon": h, "rule": rule, "status": "NOT RUN: source void", "passes": False})
            continue
        rows = sources[name]
        sessions = sorted({key[1] for key in rows})
        trades = run_source(rows, patterns, name)
        for (h, rule), tr in trades.items():
            res = judge(tr, sessions)
            res.update({"source": name, "horizon": h, "rule": rule, "status": "RUN"})
            results.append(res)
            n_run += 1
    # R4: pattern alone, on the L40 sample's stock-times
    base = sources.get("kronos") or next(iter(sources.values()))
    base_sessions = sorted({key[1] for key in base})
    for h in HORIZONS:
        tr = []
        for key, row in base.items():
            d = patterns.get(key, 0)
            target = (row.get("targets") or {}).get(h)
            if d and target is not None:
                tr.append((key[1], d * target - COST_BP))
        res = judge(tr, base_sessions)
        res.update({"source": "none (pattern alone)", "horizon": h, "rule": "R4", "status": "RUN"})
        results.append(res)
        n_run += 1

    n_patterns = sum(1 for v in patterns.values() if v)
    out = {"prereg": "docs/research/prereg-combo-search.md", "finished": datetime.now().isoformat(),
           "trials": "128-202", "n_trials_for_correction": N_TRIALS, "combinations_run": n_run,
           "sources_void": missing, "stock_times_with_a_pattern": n_patterns, "stock_times": len(patterns),
           "bar": {"t": T_BAR, "dsr": DSR_BAR, "min_trades": MIN_TRADES, "min_sessions": MIN_SESSIONS, "cost_bp": COST_BP},
           "passing": [r for r in results if r.get("passes")], "results": results}
    tmp = args.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1, default=str)
    os.replace(tmp, args.out)
    ranked = sorted((r for r in results if r["status"] == "RUN"), key=lambda r: -(r.get("t") or -99))
    print("combinations run: %d of %d; void sources: %s; stock-times with a pattern: %d of %d"
          % (n_run, N_TRIALS, missing or "none", n_patterns, len(patterns)))
    for r in ranked[:10]:
        print("  %-22s %s %s  trades %5d  net %6.1f bp/trade  t %5.2f  halves %6.1f / %6.1f  DSR %s  %s"
              % (r["source"], r["horizon"], r["rule"], r["trades"], r["mean_net_bp_per_trade"] or 0, r["t"] or 0,
                 r["half1_bp"] or 0, r["half2_bp"] or 0, r["dsr"], "PASS" if r["passes"] else "fail"))
    print("passing:", len(out["passing"]))


if __name__ == "__main__":
    main()
