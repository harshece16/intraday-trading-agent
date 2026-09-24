"""The confluence engine on the deep Kite cache — pre-registered in
docs/research/prereg-confluence-deep.md, committed with this script before
the run. One arm (confluence); the checklist comparator is trial 39. Pass:
net R > 0 with t > 2 over the selection sample AND positive in both halves.
Selection sample only; the held-out window is never loaded. Trial 40.
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

OUT = Path(__file__).resolve().parents[2] / "docs/research/confluence_deep_result.json"
DAYS = 730
ARMS = {"confluence": "confluence"}


def summarise(trades):
    ok = [t for t in trades if t.get("risk_per_share") and t.get("qty")]
    rs = [t["pnl"] / (t["risk_per_share"] * t["qty"]) for t in ok]
    extra = {"gross_r": st.mean([t["gross_pnl"] / (t["risk_per_share"] * t["qty"]) for t in ok]) if ok else None,
             "stop_bp_median": st.median([t["risk_per_share"] / t["entry_price"] * 1e4 for t in ok]) if ok else None}
    if len(rs) < 2:
        return {"n": len(rs), "net_r": rs[0] if rs else None}
    m, sd = st.mean(rs), st.stdev(rs)
    se = sd / math.sqrt(len(rs))
    return {**extra, "n": len(rs), "net_r": m, "sd": sd, "t": m / se if se else None,
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
    all_trades = []
    for half_name, half in (("first", first), ("second", second)):
        candles, allowed = splits.slice_data(preloaded, picks, half)
        for arm, mode in ARMS.items():
            params = {**config.STRATEGY_PARAMS["sahab_dimaag"], "entry_mode": mode}
            trades, _ = backtester.run_backtest(sorted(candles), "sahab_dimaag", params, risk_cfg,
                                                config.CANDLE_INTERVAL, DAYS, costs_cfg=config.COSTS,
                                                preloaded=candles, allowed_by_day=allowed, scorecard=[])
            all_trades += trades
            s = summarise(trades)
            out["arms"].setdefault(arm, {})[half_name] = s
            print(f"{half_name:<7} {arm:<16} {json.dumps(s, default=lambda x: round(x, 4))}", flush=True)
        del candles, allowed

    # Pooled over the whole selection sample: rerun on all of it would load the
    # data twice, so pool the per-half trade lists instead.
    arm = out["arms"]["confluence"]
    pooled = summarise(all_trades)
    out["pooled"] = pooled
    ok = (pooled.get("net_r") is not None and pooled["net_r"] > 0 and (pooled.get("t") or 0) > 2
          and all((arm[h].get("net_r") or -1) > 0 for h in ("first", "second")))
    out["verdict"] = "PASS" if ok else "FAIL — live engine stays on the checklist"
    print(f"\npooled: {json.dumps(pooled, default=lambda x: round(x, 4))}")
    print(f"Verdict: {out['verdict']}")
    OUT.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
