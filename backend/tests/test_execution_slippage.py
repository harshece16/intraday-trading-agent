"""
Regression test for a real gap found while reviewing the system against
standard algo-trading practice: costs.apply_slippage() was used by
backtester.py for every fill but never called from trading_engine._execute()
— the one path every live and paper trade actually goes through. That broke
backtester.py's own "same code, same costs" property: live/paper P&L was
held to a laxer cost standard than backtested performance, a well-documented
way a strategy looks better on paper than it performs with real capital.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import trading_engine
from state import AppState, _new_position


def make_engine():
    state = AppState(watchlist=[], paper_mode=True)
    engine = trading_engine.TradingEngine(state)
    return engine, state


def test_buy_fill_is_slipped_up_from_the_signal_price():
    engine, state = make_engine()
    symbol = "SLIPTEST"
    state.positions[symbol] = _new_position()

    engine._execute(symbol, "BUY", 10, 100.0, reason="test")

    fill_price = state.positions[symbol]["avg_price"]
    expected = 100.0 * (1 + config.COSTS["slippage_pct"] / 100)
    assert fill_price == expected
    assert fill_price > 100.0  # a market buy fills a little higher, never at the exact signal price


def test_sell_fill_is_slipped_down_from_the_signal_price():
    engine, state = make_engine()
    symbol = "SLIPTEST2"
    state.positions[symbol] = _new_position()

    engine._execute(symbol, "SELL", 10, 100.0, reason="test")

    fill_price = state.positions[symbol]["avg_price"]
    expected = 100.0 * (1 - config.COSTS["slippage_pct"] / 100)
    assert fill_price == expected
    assert fill_price < 100.0  # a market sell fills a little lower, never at the exact signal price


def test_slippage_matches_backtester_direction_convention():
    """Same helper, same sign convention as backtester.py already used for
    every historical fill — this just closes the gap where the live path
    didn't call it."""
    import costs
    assert costs.apply_slippage("BUY", 100.0, config.COSTS) > 100.0
    assert costs.apply_slippage("SELL", 100.0, config.COSTS) < 100.0
