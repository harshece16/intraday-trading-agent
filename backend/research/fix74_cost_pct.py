"""Issue #74 — before/after backtest for the checklist's cost_pct correction.

A declared bug-fix pair (CLAUDE.md: judge strategy changes by net-of-cost
backtests on both halves). The fix itself is justified by measurement, not by
this backtest: the gate priced a round trip at 12 bp, phase 2 measured
16.60 bp, and costs.round_trip_pct() reproduces 16.60 bp from config.COSTS.
This run only checks the correction does no harm.

Fixed in advance, committed before the first run:

- Arms: baseline cost_pct = 0.12 vs fixed cost_pct = trader_brain.DEFAULTS
  (derived, 0.166). Nothing else differs.
- Harness: Test A's — run_backtest(), NIFTY 100, scanner top 5/day,
  min_confidence_to_trade = 0, scorecard = [], config.COSTS, 5m Kite bars.
- Window: SELECTION ONLY — sessions before splits.HELD_OUT_START
  (2026-01-02). The held-out window is not loaded into any run.
- Split: splits.halves() of the selection sessions, each half run separately.
- Metric: net R per trade (pnl / (risk_per_share * qty)), with n, t and 95% CI.
- Pass rule: the fix SHIPS unless its net expectancy is below the baseline's
  in BOTH halves. It is expected to take fewer trades; fewer trades is not
  a failure.
- One run. A re-run only for a crash before any statistic was printed.
- Counted as trials 36 and 37 in trials.md (conservative: an overstated
  count makes the Deflated Sharpe stricter).
"""
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backtester
import config
import kite_history
import scanner
import trader_brain
import universe
from research import splits

OUT = Path(__file__).resolve().parents[2] / "docs/research/fix74_result.json"
DAYS = 730
ARMS = {"baseline_0.12": 0.12, f"fixed_{trader_brain.DEFAULTS['cost_pct']}": trader_brain.DEFAULTS["cost_pct"]}


def summarise(trades):
    rs = [t["pnl"] / (t["risk_per_share"] * t["qty"]) for t in trades if t.get("risk_per_share") and t.get("qty")]
    if len(rs) < 2:
        return {"n": len(rs), "net_r": rs[0] if rs else None}
    m, sd = st.mean(rs), st.stdev(rs)
    se = sd / math.sqrt(len(rs))
    return {"n": len(rs), "net_r": m, "sd": sd, "t": m / se if se else None,
            "ci": [m - 1.96 * se, m + 1.96 * se],
            "win_pct": 100 * sum(r > 0 for r in rs) / len(rs),
            "net_rs": sum(t["pnl"] for t in trades)}


def main():
    rows = universe.load()
    symbols = [r["symbol"] for r in rows]
    preloaded = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=DAYS)
    selection, held_out = splits.selection_holdout(splits.sessions_in(preloaded))
    # Drop held-out candles before anything else sees them.
    preloaded, _ = splits.slice_data(preloaded, {}, selection)
    first, second = splits.halves(selection)
    print(splits.describe_split("selection", selection))
    print(splits.describe_split("first half", first))
    print(splits.describe_split("second half", second))
    print(f"held-out: {len(held_out)} sessions — NOT loaded into any run\n", flush=True)

    daily = scanner.download_batch([scanner.yf_ticker(s) for s in symbols] + [scanner.NIFTY], "2y", "1d")
    picks = scanner.premarket_picks(daily, rows, selection, 5, config.SCANNER, allow_shorts=True)
    risk_cfg = {**config.RISK, "min_confidence_to_trade": 0}

    out = {"selection": [selection[0], selection[-1], len(selection)],
           "halves": [[first[0], first[-1], len(first)], [second[0], second[-1], len(second)]],
           "arms": {}}
    for half_name, half in (("first", first), ("second", second)):
        candles, allowed = splits.slice_data(preloaded, picks, half)
        for arm, cost_pct in ARMS.items():
            params = {**config.STRATEGY_PARAMS["sahab_dimaag"], "cost_pct": cost_pct}
            trades, _ = backtester.run_backtest(sorted(candles), "sahab_dimaag", params, risk_cfg,
                                                config.CANDLE_INTERVAL, DAYS, costs_cfg=config.COSTS,
                                                preloaded=candles, allowed_by_day=allowed, scorecard=[])
            s = summarise(trades)
            out["arms"].setdefault(arm, {})[half_name] = s
            print(f"{half_name:<7} {arm:<16} {json.dumps(s, default=lambda x: round(x, 4))}", flush=True)
        del candles, allowed

    base, fix = out["arms"].values()
    worse = [h for h in ("first", "second")
             if fix[h].get("net_r") is not None and base[h].get("net_r") is not None
             and fix[h]["net_r"] < base[h]["net_r"]]
    out["verdict"] = "FAIL — worse in both halves" if len(worse) == 2 else "PASS — ships"
    out["worse_halves"] = worse
    print(f"\nVerdict: {out['verdict']} (fix below baseline in: {worse or 'neither'})")
    OUT.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
