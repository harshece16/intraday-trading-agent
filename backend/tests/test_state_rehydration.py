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


# ---- issue #22: the per-stock entry count survives a restart -------------


def _fill(trade_id, position_id, ts, symbol, side, realized=None):
    database.record_trade({
        "id": trade_id, "position_id": position_id, "ts": ts, "symbol": symbol, "side": side,
        "quantity": 10, "price": 100.0, "mode": "paper", "reason": "test", "note": None,
        "realized": realized, "charges": 1.0, "initial_risk": 1.0, "r_multiple": None,
    })


def test_a_stock_traded_today_is_still_counted_after_a_restart():
    """MAZDOCK, 17 Sep: shorted, stopped out, and a restart would have let the
    engine short it again the same day."""
    _fill("m1", "posM", _today_ts(0.2), "MAZDOCK", "SELL")
    _fill("m2", "posM", _today_ts(0.3), "MAZDOCK", "BUY", realized=-120.0)

    state = AppState(watchlist=["MAZDOCK", "TCS"], paper_mode=True)

    today = datetime.now(IST).date().isoformat()
    assert state.strategy_state["MAZDOCK"] == {"entries_today": 1, "entry_day": today}
    assert not state.strategy_state.get("TCS")


def test_two_positions_in_one_stock_count_twice():
    _fill("a1", "posA", _today_ts(0.1), "BEL", "BUY")
    _fill("a2", "posA", _today_ts(0.2), "BEL", "SELL", realized=10.0)
    _fill("b1", "posB", _today_ts(0.3), "BEL", "BUY")
    assert AppState(watchlist=[], paper_mode=True).strategy_state["BEL"]["entries_today"] == 2


def test_yesterdays_entries_dont_count():
    start = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    _fill("y1", "posY", start - 3600 * 5, "INFY", "BUY")
    assert not AppState(watchlist=["INFY"], paper_mode=True).strategy_state.get("INFY")


def test_the_brain_carries_the_restored_count_forward():
    """End to end through trader_brain_signal(): given the restored state and
    a session of today's bars, the count it returns is still 1, not reset to
    0, so max_entries_per_day keeps refusing a second entry."""
    import math
    from datetime import timedelta
    import trader_brain
    _fill("r1", "posR", _today_ts(0.2), "RELIANCE", "BUY")
    state = AppState(watchlist=["RELIANCE"], paper_mode=True)

    today = datetime.now(IST).replace(hour=9, minute=15, second=0, microsecond=0)
    start = today - timedelta(days=1)
    bars = []
    for i in range(150):
        t = start + timedelta(minutes=5 * (i % 75)) + timedelta(days=i // 75)
        c = 100 + 3 * math.sin(i / 9) + i * 0.02
        bars.append({"time": t.isoformat(), "open": c - 0.2, "high": c + 0.6, "low": c - 0.6, "close": c,
                     "volume": 1000 + (i % 7) * 150})
    assert bars[-1]["time"][:10] == today.date().isoformat()

    signal, st = trader_brain.trader_brain_signal(bars, prev_state=state.strategy_state["RELIANCE"])
    assert st["entries_today"] == 1
    assert signal not in ("BUY", "SHORT")


# ---- issue #247: the blotter is rolled to today at the day change -------------


def test_day_change_drops_earlier_days_legs_from_the_blotter_and_tax(monkeypatch):
    """state.trades was rebuilt from the journal only at start-up, so a
    backend that ran across midnight kept earlier days' legs, and the tax
    summary counted them as today's (/api/state at 2026-10-04 23:57 still
    held the 2026-10-01 APOLLOHOSP legs, tax net -203.58)."""
    state = AppState(watchlist=[], paper_mode=True)
    days_ago = time.time() - 86400 * 3
    state.trades = [
        {"id": "old-exit", "ts": days_ago + 60, "symbol": "APOLLOHOSP", "side": "BUY", "quantity": 4,
         "price": 8078.92, "realized": -203.58, "realized_gross": -169.34, "charges": 13.62},
        {"id": "old-entry", "ts": days_ago, "symbol": "APOLLOHOSP", "side": "SELL", "quantity": 4,
         "price": 8036.59, "realized": 0.0, "realized_gross": 0.0, "charges": 20.62},
    ]
    state.realized_pnl_today = -203.58
    engine = trading_engine.TradingEngine(state)
    engine.scanner = None
    engine._last_day = datetime.now(IST).date().replace(year=2000)  # force a day change
    monkeypatch.setattr(trading_engine, "market_phase", lambda now: "closed")

    engine._tick_impl()

    assert state.trades == []
    assert state.realized_pnl_today == 0.0
    assert engine.risk.daily_realized_pnl == 0.0
    tax = state._tax_summary()
    assert tax["net_pnl"] == 0 and tax["charges"] == 0 and tax["closed_trades"] == 0


def test_day_change_keeps_todays_journal_legs():
    _insert_trade("t1", _today_ts(0.2), "BEL", "SELL", 389.65)
    _insert_trade("t2", _today_ts(0.4), "BEL", "BUY", 390.25, realized=-30.0)
    state = AppState(watchlist=[], paper_mode=True)
    state.trades.append({"id": "stale", "ts": time.time() - 86400 * 2, "realized": 50.0})

    state.roll_trades_to_today()

    assert {t["id"] for t in state.trades} == {"t1", "t2"}
    assert state.trades[0]["id"] == "t2"  # newest first
    assert state.realized_pnl_today == -30.0


def test_day_change_survives_a_journal_failure(monkeypatch):
    state = AppState(watchlist=[], paper_mode=True)
    state.trades = [{"id": "stale", "ts": time.time() - 86400 * 2, "realized": 50.0},
                    {"id": "fresh", "ts": _today_ts(0.5), "realized": -10.0}]
    monkeypatch.setattr(database, "trades_between", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))

    state.roll_trades_to_today()

    assert [t["id"] for t in state.trades] == ["fresh"]
    assert state.realized_pnl_today == -10.0
