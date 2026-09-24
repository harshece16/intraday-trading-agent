"""
The owner's controls over an unattended engine: pause new entries, the kill
switch (close everything, back to Paper), and the checks before going live.

Before these, the only way to stop the engine mid-session was to switch to
Paper, which leaves open positions alone, or to kill the process, which
leaves them with no stops at all. And /api/mode went live on a dead Kite
session or after the daily loss limit had already been hit.
"""
import pytest

import data_provider
import trading_engine
from state import AppState, _new_position


def _open(eng, symbol, qty, price=100.0):
    eng.state.positions[symbol] = {**_new_position(), "quantity": qty, "avg_price": price,
                                   "stop_price": price * 0.98, "target_price": price * 1.03,
                                   "initial_risk": price * 0.02, "position_id": f"p-{symbol}"}
    eng.risk.open_positions_count += 1


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setattr(data_provider, "get_ltp", lambda symbol: 101.0)
    st = AppState(watchlist=["AAA", "BBB"], paper_mode=True)
    return trading_engine.TradingEngine(st)


def _fills(eng):
    return list(reversed(eng.state.trades))


# ---- pause -------------------------------------------------------------


def test_a_paused_engine_blocks_new_entries(engine):
    engine.state.positions["AAA"] = _new_position()
    engine.set_entries_paused(True)
    assert engine._try_enter("AAA", "LONG", 100.0, None, {"setup": "ORB"}) is False
    assert any("paused" in a["message"] for a in engine.state.activity if a["kind"] == "blocked")


def test_the_pause_survives_a_restart(engine):
    engine.set_entries_paused(True)
    restarted = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    assert restarted.state.entries_paused is True
    restarted.set_entries_paused(False)
    assert trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True)).state.entries_paused is False


def test_pause_leaves_open_positions_and_their_stops_alone(engine):
    _open(engine, "AAA", 10)
    engine.set_entries_paused(True)
    assert engine.state.positions["AAA"]["quantity"] == 10
    assert engine.check_stop_from_tick("AAA", 97.0) is True  # stop still fires
    assert engine.state.positions["AAA"]["quantity"] == 0


# ---- kill switch -------------------------------------------------------


def test_kill_switch_closes_everything_pauses_and_returns_to_paper(engine):
    _open(engine, "AAA", 10)
    _open(engine, "BBB", -5)
    engine.state.paper_mode = False
    # A live close would reach Kite; stand in for the broker call only.
    engine._execute = _paper_execute(engine)
    out = engine.stop_and_flatten()
    assert sorted(out["closed"]) == ["AAA", "BBB"]
    assert out["failed"] == []
    assert engine.state.positions["AAA"]["quantity"] == 0
    assert engine.state.positions["BBB"]["quantity"] == 0
    assert engine.state.entries_paused is True
    assert engine.state.paper_mode is True
    assert {f["reason"] for f in _fills(engine)} == {"kill_switch"}


def test_kill_switch_stays_live_when_a_close_fails(engine):
    _open(engine, "AAA", 10)
    engine.state.paper_mode = False

    def failing_execute(*a, **k):
        raise RuntimeError("Kite rejected the order")

    engine._execute = failing_execute
    out = engine.stop_and_flatten()
    assert out["failed"][0]["symbol"] == "AAA"
    assert engine.state.paper_mode is False
    assert engine.state.entries_paused is True


def _paper_execute(eng):
    real = eng._execute

    def run(*args, **kwargs):
        was = eng.state.paper_mode
        eng.state.paper_mode = True
        try:
            return real(*args, **kwargs)
        finally:
            eng.state.paper_mode = was
    return run


# ---- square-off goes through the exit claim ----------------------------


def test_square_off_skips_a_position_another_thread_is_already_closing(engine):
    """The 15:15 square-off used to call _execute directly. A stop firing on
    the tick thread at the same moment would send a second closing order and
    flip the position instead of flattening it."""
    _open(engine, "AAA", 10)
    engine._exiting.add("AAA")  # the tick thread holds the claim
    assert engine._square_off_all() == []
    assert _fills(engine) == []
    engine._exiting.discard("AAA")
    assert engine._square_off_all() == ["AAA"]
    assert len(_fills(engine)) == 1


# ---- live readiness ----------------------------------------------------


def _kite(monkeypatch, connected):
    monkeypatch.setattr(data_provider, "kite_session_status",
                        lambda probe=False: {"connected": connected, "state": "expired" if not connected else "connected",
                                             "reason": "session expired" if not connected else "ok"})


def test_live_is_refused_without_a_usable_kite_session(engine, monkeypatch):
    _kite(monkeypatch, False)
    r = engine.live_readiness()
    assert r["ready"] is False
    assert "Kite" in r["blockers"][0]


def test_live_is_refused_after_the_daily_loss_limit(engine, monkeypatch):
    _kite(monkeypatch, True)
    engine.risk.daily_realized_pnl = -1e9
    r = engine.live_readiness()
    assert r["ready"] is False
    assert "loss limit" in r["blockers"][0]


def test_live_is_allowed_when_nothing_blocks(engine, monkeypatch):
    _kite(monkeypatch, True)
    assert engine.live_readiness() == {"ready": True, "blockers": [], "entries_paused": False}
