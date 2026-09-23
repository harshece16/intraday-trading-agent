"""Issue #40 — before/after backtest for removing the formulaic no-level target.

A declared bug-fix pair, run the same way as #74 (fix74_cost_pct.py). When
no support/resistance lies beyond the entry, the checklist used to aim at a
GROSS 2.0R target and judge it NET of costs. The fix gives such a setup no
target, so it fails the R:R item; it can only remove trades, never add them.
The branch is reachable: across the whole journal, 920 evaluation-sides took
it, 186 cleared R:R and 9 passed the full checklist.

Fixed in advance, committed before the first run:

- Arms: baseline rrr_without_level = 2.0 (the old behaviour) vs fixed
  rrr_without_level = None. cost_pct is the derived 0.166 in both. Nothing
  else differs.
- Harness, window, split: identical to fix74 — run_backtest(), NIFTY 100,
  scanner top 5/day, min_confidence_to_trade = 0, scorecard = [],
  config.COSTS, 5m Kite bars, SELECTION ONLY (before 2026-01-02, held-out
  never loaded), splits.halves().
- Metric: net R per trade, with n, t and 95% CI.
- Pass rule: the fix SHIPS unless its net expectancy is below the
  baseline's in BOTH halves. Fewer trades is expected and is not a failure.
- One run. A re-run only for a crash before any statistic was printed.
- Counted as trials 38 and 39 in trials.md, the count of record. 3e
  (prereg "expected trial 38") and 3f have not run; both say their numbers
  are assigned at run time, so theirs move down by two.
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

OUT = Path(__file__).resolve().parents[2] / "docs/research/fix40_result.json"
DAYS = 730
ARMS = {"baseline_2R_gross": 2.0, "fixed_no_target": None}


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
        for arm, no_level in ARMS.items():
            params = {**config.STRATEGY_PARAMS["sahab_dimaag"], "rrr_without_level": no_level}
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
