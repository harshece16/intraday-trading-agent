"""
Regression test for a real bug found live: AppState.trades and
realized_pnl_today are in-memory-only fields, reset to empty on every
process start, even though database.record_trade() already logs every
fill permanently. A restart during market hours (to deploy a fix, say)
made an already-closed real trade vanish from the Trade Journal page —
looking like it had never happened, when the database still had it.
AppState now reloads today's real fills from the journal on construction.
"""
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

import database
import trading_engine
from state import AppState

IST = ZoneInfo("Asia/Kolkata")


def _today_ts(fraction):
    # Guaranteed to be today (IST) and already past, whenever the suite runs —
    # a fixed `now - 3600` silently became yesterday in the hour after midnight.
    now = time.time()
    start = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    return start + (now - start) * fraction


def _insert_trade(trade_id, ts, symbol, side, price, realized=None):
    database.record_trade({
        "id": trade_id, "position_id": "pos1", "ts": ts, "symbol": symbol, "side": side,
        "quantity": 50, "price": price, "mode": "paper", "reason": "test", "note": None,
        "realized": realized, "charges": 5.0, "initial_risk": 0.5, "r_multiple": None,
    })


def test_todays_trades_are_loaded_on_construction():
    _insert_trade("t1", _today_ts(0.2), "BEL", "SELL", 389.65)
    _insert_trade("t2", _today_ts(0.4), "BEL", "BUY", 390.25, realized=-30.0)

    state = AppState(watchlist=[], paper_mode=True)

    ids = {t["id"] for t in state.trades}
    assert {"t1", "t2"} <= ids
    assert state.realized_pnl_today == -30.0


def test_trades_are_newest_first():
    _insert_trade("older", _today_ts(0.2), "BEL", "SELL", 389.65)
    _insert_trade("newer", _today_ts(0.8), "BEL", "BUY", 390.25, realized=-30.0)

    state = AppState(watchlist=[], paper_mode=True)

    assert state.trades[0]["id"] == "newer"


def test_yesterdays_trades_are_not_loaded():
    yesterday = time.time() - 86400 * 2
    _insert_trade("stale", yesterday, "OLDSTOCK", "SELL", 100.0, realized=50.0)

    state = AppState(watchlist=[], paper_mode=True)

    ids = {t["id"] for t in state.trades}
    assert "stale" not in ids
    assert state.realized_pnl_today == 0.0


def test_rehydration_survives_a_database_failure(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db unavailable")
    monkeypatch.setattr(database, "trades_between", boom)

    state = AppState(watchlist=[], paper_mode=True)  # must not raise

    assert state.trades == []


def test_engine_seeds_daily_loss_counter_from_rehydrated_trades():
    """A second, related bug: even once state.realized_pnl_today was
    correctly rehydrated, TradingEngine.__init__ left _last_day as None,
    so _tick_impl()'s very first tick after any restart saw "a new day
    started" and zeroed both state.realized_pnl_today and
    risk.daily_realized_pnl right back out — silently erasing today's real
    losses from the max_daily_loss_pct safety check on every restart."""
    _insert_trade("loss1", _today_ts(0.2), "BEL", "SELL", 389.65)
    _insert_trade("loss2", _today_ts(0.4), "BEL", "BUY", 390.25, realized=-30.0)

    state = AppState(watchlist=[], paper_mode=True)
    engine = trading_engine.TradingEngine(state)

    assert engine.risk.daily_realized_pnl == -30.0
    assert engine._last_day == datetime.now(IST).date()


def test_first_tick_after_restart_does_not_re_zero_the_loss_counter(monkeypatch):
    _insert_trade("loss1", _today_ts(0.2), "BEL", "SELL", 389.65)
    _insert_trade("loss2", _today_ts(0.4), "BEL", "BUY", 390.25, realized=-30.0)

    state = AppState(watchlist=[], paper_mode=True)
    engine = trading_engine.TradingEngine(state)
    engine.scanner = None
    monkeypatch.setattr(trading_engine, "market_phase", lambda now: "closed")

    engine._tick_impl()  # the first real tick after construction

    assert engine.risk.daily_realized_pnl == -30.0
    assert state.realized_pnl_today == -30.0
