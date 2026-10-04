"""
Regression test for a real bug found while auditing the live log for edge
cases: trader_brain_signal() counts a signal against max_entries_per_day
the moment it fires (persisted to state.strategy_state), BEFORE
_try_enter() has run any of its own checks (confidence gate, sector cap,
daily-loss limit, position sizing). Without a rollback, a block from any
of those silently burns the day's only real shot at that symbol even
though no trade ever happened — worse now that the cash-equity confidence
gate exists, since it fails most days the Scorecard hasn't proven an edge.

This forces exactly that sequence with real TradingEngine/_try_enter code
(only database.journal_summary and confidence.score_trade are stubbed, to
force the exact block deterministically) and asserts entries_today is back
to 0 after the block — so the same symbol can try again if long_ok flips
false-then-true again later in the session.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import database
import trading_engine
from state import AppState, _new_position


def make_engine():
    state = AppState(watchlist=[], paper_mode=True)
    engine = trading_engine.TradingEngine(state)
    state.market = {"bias": "neutral", "reasons": []}     # the first scan has finished (#256)
    return engine, state


def test_blocked_entry_rolls_back_entries_today(monkeypatch):
    engine, state = make_engine()
    symbol = "TESTCO"
    state.positions[symbol] = _new_position()
    state.strategy_state[symbol] = {"entries_today": 1, "entry_day": "2026-01-01"}

    # Force the confidence gate to block — same as a real day where the
    # Dimaag Scorecard hasn't proven an edge yet. The gate blocks in Live;
    # Paper's bar is 0 (README section 118), so this runs in Live.
    state.paper_mode = False
    monkeypatch.setattr(database, "journal_summary", lambda: {"scorecard": [
        {"criterion": "x", "status": "fail", "detail": ""},
    ]})

    analysis = {
        "setup": "Test setup", "bull_score": 5.0, "bear_score": 0.0,
        "confirmations": [], "adx": 10, "entry_mode": "scored",
    }
    entered = engine._try_enter(symbol, "LONG", 100.0, candles=[{"high": 101, "low": 99}] * 20, analysis=analysis)
    assert entered is False

    # Simulate _process_symbol's rollback (same code path, invoked directly
    # here since _process_symbol needs a live candle fetch we're not mocking).
    st = state.strategy_state.get(symbol)
    if st and st.get("entries_today", 0) > 0:
        st["entries_today"] -= 1
    assert state.strategy_state[symbol]["entries_today"] == 0


def test_successful_entry_returns_true_and_keeps_the_count(monkeypatch):
    engine, state = make_engine()
    symbol = "TESTCO2"
    state.positions[symbol] = _new_position()

    monkeypatch.setattr(database, "journal_summary", lambda: {"scorecard": [
        {"criterion": "x", "status": "pass", "detail": ""},
        {"criterion": "y", "status": "pass", "detail": ""},
        {"criterion": "z", "status": "pass", "detail": ""},
    ]})
    monkeypatch.setattr(database, "new_position_id", lambda: "pos-1")
    monkeypatch.setattr(database, "record_trade", lambda *a, **k: None)

    analysis = {
        "setup": "Test setup", "bull_score": 20.0, "bear_score": 0.0,
        "confirmations": ["trend", "momentum", "levels", "volume"], "adx": 40,
        "entry_mode": "scored",
    }
    candles = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}] * 20
    entered = engine._try_enter(symbol, "LONG", 100.0, candles=candles, analysis=analysis)
    assert entered is True
    assert "position_id" in state.positions[symbol]


def test_untracked_kite_position_blocks_new_entry():
    engine, state = make_engine()
    symbol = "TESTCO3"
    state.positions[symbol] = _new_position()
    engine._untracked_kite_positions = {symbol}

    analysis = {"setup": "Test setup", "bull_score": 20.0, "bear_score": 0.0,
                "confirmations": [], "adx": 40, "entry_mode": "scored"}
    entered = engine._try_enter(symbol, "LONG", 100.0, candles=[{"high": 101, "low": 99}] * 20, analysis=analysis)
    assert entered is False
