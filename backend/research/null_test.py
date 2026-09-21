"""Step 1 — random-entry null test. Pre-registered in prereg-null-test.md.

Drives the REAL harness (backtester.run_backtest) with a strategy whose
signal is drawn from an RNG and ignores every bar it is shown. Everything
else — bar walking, exit precedence, fill convention, sizing, the 15:15
timeout — is the same code the verdict used, which is the point: a
re-implementation would test the re-implementation.

Pass rule (zero costs): seed-mean gross expectancy within +/-0.05R of zero.
"""
import json
import math
import random
import statistics as st
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backtester
import config
import costs as costs_mod
import kite_history
import scanner
import strategy_engine
import universe

TRADES_JSON = str(Path(__file__).resolve().parents[2] / "docs/research/data/testA_trades.json")
OUT = str(Path(__file__).resolve().parents[2] / "docs/research/data/null_result.json")
SEEDS = 200
NULL_NAME = "_null_random_entry"
DAYS = 730


def load_real():
    with open(TRADES_JSON) as f:
        blob = json.load(f)
    trades = blob["trades"]
    triples, hours = [], []
    for t in trades:
        price, rps = t["entry_price"], t["risk_per_share"]
        stop_bp = rps / price * 10000
        rr = abs(t["target"] - price) / rps if t.get("target") else None
        if rr is None:
            continue
        # implied size factor: actual qty against what full size would have been
        base = backtester.RiskManager({**config.RISK}).position_size(
            price, stop_price=price - rps, size_factor=1.0)
        sf = min(1.0, t["qty"] / base) if base else 1.0
        triples.append((stop_bp, rr, sf))
        if t.get("entry_time"):
            hours.append(t["entry_time"][11:13])
    return blob, trades, triples, Counter(hours)


def make_null(rng, triples, hour_weights, long_frac, fire_p):
    """A strategy function with no information in it."""
    hours = list(hour_weights)
    weights = [hour_weights[h] for h in hours]
    total = sum(weights)
    hour_p = {h: w / total for h, w in zip(hours, weights)}
    peak = max(hour_p.values())

    def null_signal(window, prev_state=None, **params):
        bar = window[-1]
        hour = bar["time"][11:13]
        # fire with a probability shaped like the real hour profile
        p = fire_p * (hour_p.get(hour, 0.0) / peak)
        if p <= 0 or rng.random() >= p:
            return None, {"entry_mode": "checklist", "checklist": {}}
        side = "BUY" if rng.random() < long_frac else "SHORT"
        stop_bp, rr, sf = triples[rng.randrange(len(triples))]
        price = bar["close"]
        dist = price * stop_bp / 10000
        if dist <= 0:
            return None, {"entry_mode": "checklist", "checklist": {}}
        stop = price - dist if side == "BUY" else price + dist
        target = price + dist * rr if side == "BUY" else price - dist * rr
        key = "long" if side == "BUY" else "short"
        return side, {"entry_mode": "checklist",
                      "checklist": {key: {"stop": stop, "target": target, "size_factor": sf}}}

    null_signal.uses_news = False
    null_signal.uses_fundamentals = False
    return null_signal


def summarise(trades):
    keep = [t for t in trades if t.get("r") is not None and t.get("risk_per_share")]
    if not keep:
        return None
    net = [t["r"] for t in keep]
    gross = [t["gross_pnl"] / (t["risk_per_share"] * t["qty"]) for t in keep]
    resolved = [t for t in keep if t["reason"] in ("stop_loss", "take_profit")]
    tp = sum(1 for t in resolved if t["reason"] == "take_profit")
    return {
        "n": len(keep),
        "gross": st.mean(gross),
        "net": st.mean(net),
        "target_rate": (tp / len(resolved) * 100) if resolved else None,
        "r_rupees": st.median([t["risk_per_share"] * t["qty"] for t in keep]),
        "stop_bp": st.median([t["risk_per_share"] / t["entry_price"] * 10000 for t in keep]),
    }


def pct_rank(value, dist):
    """Percentile of `value` within `dist`."""
    below = sum(1 for d in dist if d < value)
    return 100.0 * below / len(dist)


def describe(name, vals):
    vals = sorted(vals)
    n = len(vals)
    return (f"{name:<22} mean {st.mean(vals):+.4f}  sd {st.stdev(vals):.4f}  "
            f"min {vals[0]:+.4f}  p2.5 {vals[int(.025*n)]:+.4f}  "
            f"p97.5 {vals[int(.975*n)]:+.4f}  max {vals[-1]:+.4f}")


def main():
    blob, real_trades, triples, hour_weights = load_real()
    n_sessions = blob["sessions"]
    real = summarise(real_trades)
    long_frac = sum(1 for t in real_trades if t["side"] == "LONG") / len(real_trades)
    print(f"real: n={real['n']}  gross {real['gross']:+.4f}R  net {real['net']:+.4f}R  "
          f"target(resolved) {real['target_rate']:.2f}%  R Rs{real['r_rupees']:.1f}  "
          f"stop {real['stop_bp']:.1f}bp")
    print(f"matching: {len(triples)} bootstrap triples, long_frac {long_frac:.3f}, "
          f"hours {dict(sorted(hour_weights.items()))}\n", flush=True)

    rows = universe.load()
    symbols = [r["symbol"] for r in rows]
    preloaded = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=DAYS)
    sessions = sorted({c["time"][:10] for cs in preloaded.values() for c in cs})
    daily = scanner.download_batch([scanner.yf_ticker(s) for s in symbols] + [scanner.NIFTY], "2y", "1d")
    picks = scanner.premarket_picks(daily, rows, sessions, 5, config.SCANNER, allow_shorts=True)
    print(f"loaded {len(preloaded)} symbols, {len(sessions)} sessions\n", flush=True)

    # calibrate the firing probability to land near the real trade count
    fire_p = 0.0073   # calibrated: 0.02 -> 554 trades, target 201
    risk_cfg = {**config.RISK, "min_confidence_to_trade": 0}
    params = {"entry_mode": "checklist", "max_entries_per_day": 1}

    results = {"zero_cost": [], "with_cost": []}
    for mode, cost_cfg in (("zero_cost", costs_mod.ZERO_COSTS), ("with_cost", config.COSTS)):
        print(f"=== {mode} — {SEEDS} seeds ===", flush=True)
        for seed in range(SEEDS):
            rng = random.Random(10_000 + seed)
            strategy_engine.STRATEGY_FUNCTIONS[NULL_NAME] = make_null(
                rng, triples, hour_weights, long_frac, fire_p)
            try:
                trades, _ = backtester.run_backtest(
                    sorted(preloaded), NULL_NAME, params, risk_cfg,
                    config.CANDLE_INTERVAL, DAYS, costs_cfg=cost_cfg,
                    preloaded=preloaded, allowed_by_day=picks, scorecard=[])
            except Exception as exc:
                print(f"  seed {seed}: FAILED {type(exc).__name__}: {exc}", flush=True)
                continue
            s = summarise(trades)
            if s:
                results[mode].append(s)
            if (seed + 1) % 25 == 0:
                done = results[mode]
                print(f"  {seed+1}/{SEEDS}  running mean gross "
                      f"{st.mean([x['gross'] for x in done]):+.4f}R  "
                      f"mean n {st.mean([x['n'] for x in done]):.0f}", flush=True)
        strategy_engine.STRATEGY_FUNCTIONS.pop(NULL_NAME, None)

    print("\n" + "=" * 70)
    for mode in ("zero_cost", "with_cost"):
        rs = results[mode]
        if not rs:
            print(f"{mode}: no seeds produced trades")
            continue
        print(f"\n--- {mode} ({len(rs)} seeds) ---")
        print(describe("gross expectancy R", [x["gross"] for x in rs]))
        print(describe("net expectancy R", [x["net"] for x in rs]))
        tr = [x["target_rate"] for x in rs if x["target_rate"] is not None]
        print(describe("resolved target %", tr))
        print(f"trades/seed  mean {st.mean([x['n'] for x in rs]):.0f}   "
              f"R Rs median {st.median([x['r_rupees'] for x in rs]):.1f}   "
              f"stop bp median {st.median([x['stop_bp'] for x in rs]):.1f}")

    # ---- pass rule ----
    zc = [x["gross"] for x in results["zero_cost"]]
    if zc:
        m = st.mean(zc)
        verdict = "PASS" if abs(m) <= 0.05 else "FAIL"
        print("\n" + "=" * 70)
        print(f"PASS RULE (zero cost): seed-mean gross expectancy {m:+.4f}R "
              f"vs +/-0.05R  ->  {verdict}")
        if m > 0.05:
            print("  NOTE: positive beyond the band is the alarming direction — "
                  "the harness would be manufacturing edge from nothing.")

    # ---- findings ----
    print("\n--- findings about the strategy (not pass conditions) ---")
    if zc:
        print(f"real gross {real['gross']:+.4f}R sits at the "
              f"{pct_rank(real['gross'], zc):.1f}th percentile of the zero-cost null")
    tr0 = [x["target_rate"] for x in results["zero_cost"] if x["target_rate"] is not None]
    if tr0:
        print(f"real resolved-target {real['target_rate']:.2f}% sits at the "
              f"{pct_rank(real['target_rate'], tr0):.1f}th percentile of the null "
              f"(null mean {st.mean(tr0):.2f}%)")
        print(f"reference line 1/(1+RR) averaged over real trades: 31.26%  "
              f"-> null mean is {st.mean(tr0) - 31.26:+.2f}pp from it "
              f"(timeout asymmetry)")

    with open(OUT, "w") as f:
        json.dump({"real": real, "results": results}, f, default=str)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
