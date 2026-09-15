"""
Two backtester additions made to diagnose why the checklist loses
(README §36):

1. Every trade now records entry_time, stop, target and risk_per_share, so
   diagnostics (max favorable excursion, bars held, "did price reach the
   target after the stop?") use the real entry bar instead of guessing it
   from a matching close price — the first attempt at that analysis had to
   guess, and was too fragile to act on.
2. A strategy can return "ENTER", meaning "enter on whichever side the
   scanner picked this symbol for today" — needed for a no-timing baseline
   that tests the scanner's ranking on its own.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from costs import ZERO_COSTS
from strategy_engine import STRATEGY_FUNCTIONS

import backtester

IST = ZoneInfo("Asia/Kolkata")
DAYS = ["2026-01-05", "2026-01-06", "2026-01-07"]


def _candles():
    out = []
    for d in DAYS:
        start = datetime.fromisoformat(f"{d}T09:15:00").replace(tzinfo=IST)
        for i in range(60):
            t = start + timedelta(minutes=5 * i)
            out.append({"time": t.isoformat(), "open": 100.0, "high": 101.0, "low": 99.0,
                        "close": 100.0, "volume": 1000})
    return out


def _run(signal, picks):
    name = "_test_trade_fields_strategy"

    def fn(candles, prev_state=None, **params):
        return (signal, {"fired": True}) if not prev_state else (None, prev_state)
    STRATEGY_FUNCTIONS[name] = fn
    try:
        risk_cfg = {k: v for k, v in config.RISK.items() if k != "min_confidence_to_trade"}
        risk_cfg["total_capital"] = 100000
        trades, _ = backtester.run_backtest(
            ["TEST"], name, {}, risk_cfg, "5m", 5, costs_cfg=ZERO_COSTS,
            preloaded={"TEST": _candles()}, allowed_by_day=picks, scorecard=[],
        )
        return trades
    finally:
        del STRATEGY_FUNCTIONS[name]


def test_trades_record_entry_time_stop_target_and_risk():
    trades = _run("BUY", None)
    assert trades, "expected the fake BUY to open a position"
    t = trades[0]
    assert t["entry_time"] is not None
    assert datetime.fromisoformat(t["entry_time"]) < datetime.fromisoformat(t["exit_time"])
    assert t["stop"] is not None and t["target"] is not None
    assert t["risk_per_share"] and t["risk_per_share"] > 0
    assert t["stop"] < t["entry_price"] < t["target"]  # long: stop below, target above


def test_enter_signal_takes_the_scanners_picked_side():
    picks = {d: {"TEST": "SHORT"} for d in DAYS}
    trades = _run("ENTER", picks)
    assert trades and trades[0]["side"] == "SHORT"

    picks = {d: {"TEST": "LONG"} for d in DAYS}
    trades = _run("ENTER", picks)
    assert trades and trades[0]["side"] == "LONG"


def test_enter_signal_without_a_pick_never_trades():
    picks = {d: {"OTHER": "LONG"} for d in DAYS}
    assert _run("ENTER", picks) == []
