"""#108: the Kite cache is dividend-adjusted, so its price LEVELS sit below
what traded by a constant factor within a fetch run. This pins why that
doesn't move an intraday backtest: stops and ATR scale with price, so R is
unchanged, and notional-capped sizing makes rupee notional, charges and
P&L unchanged too, up to whole-share rounding. Fake steps where spans from
different runs meet are a separate risk, caught by kite_history.fetch_runs().
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from strategy_engine import STRATEGY_FUNCTIONS

import backtester

IST = ZoneInfo("Asia/Kolkata")


def _candles(scale):
    out, start = [], datetime(2026, 1, 5, 9, 15, tzinfo=IST)
    for i in range(70):
        c = (500.0 + 3.0 * ((i * 7) % 11) - i * 0.4) * scale        # a jagged drift, so stops and targets get hit
        out.append({"time": (start + timedelta(minutes=5 * i)).isoformat(), "open": c, "high": c * 1.004,
                    "low": c * 0.996, "close": c, "volume": 1000})
    return out


def _run(scale):
    name = "_test_scale_invariance"

    def fn(window, prev_state=None, **params):
        if len(window) - 1 == 30 and not (prev_state or {}).get("fired"):
            return "BUY", {"fired": True}
        return None, prev_state or {}
    STRATEGY_FUNCTIONS[name] = fn
    try:
        risk_cfg = {k: v for k, v in config.RISK.items() if k != "min_confidence_to_trade"}
        risk_cfg["total_capital"] = 100000
        trades, _ = backtester.run_backtest(["TEST"], name, {}, risk_cfg, "5m", 5, costs_cfg=config.COSTS,
                                            preloaded={"TEST": _candles(scale)}, scorecard=[])
    finally:
        del STRATEGY_FUNCTIONS[name]
    return trades[0]


def test_a_dividend_scaled_series_gives_the_same_r_notional_charges_and_pnl():
    real, adjusted = _run(1.0), _run(0.94)          # ~6%: COALINDIA's adjustment in Sep 2024
    assert real["reason"] == adjusted["reason"]
    assert abs(real["r"] - adjusted["r"]) < 0.01
    # Whole-share rounding is the only difference, and it is bounded by one
    # share: sizing floors risk / stop to whole shares on each series.
    notional = lambda t: t["qty"] * t["entry_price"]
    one_share = max(real["entry_price"], adjusted["entry_price"])
    assert abs(real["qty"] / 0.94 - adjusted["qty"]) <= 1           # shares scale by 1/factor, to the share
    assert abs(notional(real) - notional(adjusted)) <= one_share
    per_share_move = abs(real["exit_price"] - real["entry_price"])
    assert abs(real["pnl"] - adjusted["pnl"]) <= per_share_move + abs(real["cost"] - adjusted["cost"]) + 1e-6
    assert abs(real["cost"] - adjusted["cost"]) <= one_share * 0.002          # charges ~0.1% of one share's value
