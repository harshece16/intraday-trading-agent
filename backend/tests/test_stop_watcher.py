"""
Tick-driven stops (stop_watcher.py), and the exit claim that makes them safe.

Stops used to be checked only inside the 30-second poll, so a breached stop
could sit unnoticed for up to 30 seconds — worth about Rs 12 on a Rs 33,000
position against the measured 5-minute ATR, on every losing trade.

Adding a second thread that can close positions introduced a real hazard:
_check_stop_take() and _close() both read the quantity and *then* placed the
closing order, with no lock across the two steps. Two threads seeing one
breached stop would each send a full closing order, flipping the position
instead of going flat. engine._claim_exit() is what prevents that, and the
first tests here are about the race rather than the socket.
"""
import threading
import time

import pytest

import config
import stop_watcher
import trading_engine
from state import AppState, _new_position


@pytest.fixture
def engine():
    st = AppState(watchlist=["TESTCO"], paper_mode=True)
    eng = trading_engine.TradingEngine(st)
    st.positions["TESTCO"] = {**_new_position(), "quantity": 100, "avg_price": 100.0,
                              "stop_price": 99.0, "target_price": 103.0,
                              "initial_risk": 1.0, "position_id": "p1"}
    eng.risk.open_positions_count = 1
    return eng


def _fills(engine):
    return [t for t in engine.state.trades if t["symbol"] == "TESTCO"]


# ---- the exit claim -----------------------------------------------------


def test_a_breached_stop_closes_the_position(engine):
    assert engine.check_stop_from_tick("TESTCO", 98.5) is True
    assert engine.state.positions["TESTCO"]["quantity"] == 0
    assert _fills(engine)[0]["reason"] == "stop_loss"


def test_a_breached_target_closes_the_position(engine):
    assert engine.check_stop_from_tick("TESTCO", 103.5) is True
    assert engine.state.positions["TESTCO"]["quantity"] == 0
    assert _fills(engine)[0]["reason"] == "take_profit"


def test_a_price_inside_the_bracket_does_nothing(engine):
    assert engine.check_stop_from_tick("TESTCO", 101.0) is False
    assert engine.state.positions["TESTCO"]["quantity"] == 100
    assert _fills(engine) == []


def _race(engine, price=98.0, others=1):
    """Force the exact interleaving the claim exists to stop, instead of
    hoping threads collide.

    Timing-based versions of this test pass even with the claim removed:
    Python's GIL switch interval (5 ms) lets the first caller finish the whole
    close before the second one resumes, so the window never opens. Here the
    first caller is held *inside* _execute — position still showing its full
    quantity, order not yet filled — while the others run. That is precisely
    the state a second thread would have found mid-flight.

    Returns (held_caller_result, other_results, execute_calls).
    """
    inside = threading.Event()
    release = threading.Event()
    calls = []
    real_execute = engine._execute

    def held_execute(*args, **kwargs):
        calls.append(args)
        inside.set()
        release.wait(5)
        return real_execute(*args, **kwargs)

    engine._execute = held_execute
    first = []
    t = threading.Thread(target=lambda: first.append(engine.check_stop_from_tick("TESTCO", price)))
    t.start()
    assert inside.wait(5), "the first caller never reached _execute"
    # Every one of these runs while the position is still open on paper.
    other_results = [engine.check_stop_from_tick("TESTCO", price) for _ in range(others)]
    release.set()
    t.join(5)
    assert not t.is_alive()
    engine._execute = real_execute
    return first[0], other_results, calls


def test_a_second_thread_mid_close_sends_no_order(engine):
    """The hazard the whole design is built around: the poll loop and the tick
    stream see the same breach, and the second arrives while the first is
    still inside the broker call."""
    first, others, calls = _race(engine)
    assert first is True
    assert others == [False], "the second caller must find the exit already claimed"
    assert len(calls) == 1, "a second closing order would flip the position short"
    assert len(_fills(engine)) == 1
    assert engine.state.positions["TESTCO"]["quantity"] == 0


def test_a_burst_of_ticks_mid_close_still_sends_one_order(engine):
    """A real tick burst is more than one extra caller."""
    first, others, calls = _race(engine, price=97.0, others=7)
    assert first is True
    assert others == [False] * 7
    assert len(calls) == 1
    assert engine.state.positions["TESTCO"]["quantity"] == 0


def test_the_open_position_count_is_decremented_once(engine):
    """Double-decrementing would leave the engine believing it holds fewer
    positions than it does, and let it open past max_open_positions.

    Starts at 3 rather than 1 on purpose: the counter is clamped with
    max(0, ...), so from 1 a double decrement still lands on 0 and the bug
    hides. From 3, one decrement gives 2 and two give 1."""
    engine.risk.open_positions_count = 3
    _race(engine, others=3)
    assert engine.risk.open_positions_count == 2


def test_a_claim_is_released_even_when_the_order_raises(engine, monkeypatch):
    """A broker error must not leave the symbol permanently unclosable."""
    def boom(*a, **k):
        raise RuntimeError("broker rejected the order")
    monkeypatch.setattr(engine, "_execute", boom)
    with pytest.raises(RuntimeError):
        engine._exit_position("TESTCO", 98.0, "stop_loss")
    assert "TESTCO" not in engine._exiting, "the claim must be released on failure"
    # and a later attempt can still close it
    monkeypatch.undo()
    assert engine._exit_position("TESTCO", 98.0, "stop_loss") is True


def test_a_flat_position_cannot_be_claimed(engine):
    engine.state.positions["TESTCO"]["quantity"] = 0
    assert engine._claim_exit("TESTCO") is False
    assert engine.check_stop_from_tick("TESTCO", 50.0) is False


def test_the_tick_path_never_opens_a_position(engine):
    """The blast radius: this path can only ever close something already held."""
    engine.state.positions["TESTCO"]["quantity"] = 0
    for price in (1.0, 50.0, 100.0, 500.0, 10_000.0):
        assert engine.check_stop_from_tick("TESTCO", price) is False
    assert _fills(engine) == []
    assert engine.state.positions["TESTCO"]["quantity"] == 0


def test_an_unknown_symbol_is_ignored_rather_than_raising(engine):
    assert engine.check_stop_from_tick("NOSUCHCO", 100.0) is False


def test_shorts_are_bracketed_the_right_way_round(engine):
    engine.state.positions["TESTCO"] = {**_new_position(), "quantity": -100, "avg_price": 100.0,
                                        "stop_price": 101.0, "target_price": 97.0,
                                        "initial_risk": 1.0, "position_id": "s1"}
    assert engine.check_stop_from_tick("TESTCO", 100.5) is False   # inside the bracket
    assert engine.check_stop_from_tick("TESTCO", 101.5) is True    # stop is ABOVE for a short
    assert _fills(engine)[0]["reason"] == "stop_loss"
    assert _fills(engine)[0]["side"] == "BUY", "covering a short buys"


# ---- the watcher ---------------------------------------------------------


class FakeTicker:
    """Stands in for KiteTicker: records subscriptions, lets a test push ticks."""
    MODE_LTP = "ltp"

    def __init__(self, api_key, access_token):
        self.subscribed, self.unsubscribed, self.modes = [], [], []
        self.connected = self.closed = False
        self.on_ticks = self.on_connect = self.on_close = self.on_error = None

    def connect(self, threaded=False, disable_ssl_verification=False):
        self.connected = True
        if self.on_connect:
            self.on_connect(self, {})

    def subscribe(self, tokens): self.subscribed.extend(tokens)
    def unsubscribe(self, tokens): self.unsubscribed.extend(tokens)
    def set_mode(self, mode, tokens): self.modes.append((mode, list(tokens)))
    def close(self): self.closed = True

    def push(self, token, price):
        self.on_ticks(self, [{"instrument_token": token, "last_price": price}])


@pytest.fixture
def watcher(engine, monkeypatch):
    monkeypatch.setattr(config, "KITE_API_KEY", "k")
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "t")
    monkeypatch.setattr(stop_watcher.data_provider, "kite_data_active", lambda: True)
    monkeypatch.setattr(stop_watcher.data_provider, "_instrument_token", lambda s: 12345)
    w = stop_watcher.StopWatcher(engine, ticker_factory=FakeTicker)
    engine.stop_watcher = w
    return w


def test_the_watcher_stands_down_without_a_kite_session(engine, monkeypatch):
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "")
    w = stop_watcher.StopWatcher(engine, ticker_factory=FakeTicker)
    assert w.available() is False
    w.start()
    assert w._started is False
    w.sync()                     # must not raise
    assert w.stats()["connected"] is False
    assert "30-second poll" in w.stats()["note"]


def test_it_subscribes_to_exactly_what_is_held(watcher):
    watcher.sync()
    assert watcher._ticker.subscribed == [12345]
    assert watcher._ticker.modes == [("ltp", [12345])]
    assert watcher.stats()["watching"] == ["TESTCO"]


def test_a_tick_through_the_stop_closes_the_position(watcher, engine):
    watcher.sync()
    watcher._ticker.push(12345, 98.0)
    assert engine.state.positions["TESTCO"]["quantity"] == 0
    assert _fills(engine)[0]["reason"] == "stop_loss"
    assert watcher.stats()["exits_fired"] == 1


def test_a_tick_inside_the_bracket_leaves_the_position_alone(watcher, engine):
    watcher.sync()
    watcher._ticker.push(12345, 100.5)
    assert engine.state.positions["TESTCO"]["quantity"] == 100
    assert watcher.stats()["exits_fired"] == 0
    assert watcher.stats()["ticks_seen"] == 1


def test_it_unsubscribes_once_the_position_is_closed(watcher):
    watcher.sync()
    watcher._ticker.push(12345, 98.0)
    assert 12345 in watcher._ticker.unsubscribed
    assert watcher.stats()["watching"] == []


def test_sync_drops_a_symbol_that_is_no_longer_held(watcher, engine):
    watcher.sync()
    engine.state.positions["TESTCO"]["quantity"] = 0
    watcher.sync()
    assert 12345 in watcher._ticker.unsubscribed
    assert watcher.stats()["watching"] == []


def test_a_bad_tick_does_not_kill_the_stream(watcher, engine):
    """An exception escaping on_ticks would take the whole fast path down."""
    watcher.sync()
    watcher._ticker.on_ticks(watcher._ticker, [{"instrument_token": None, "last_price": None}])
    watcher._ticker.on_ticks(watcher._ticker, [{}])
    watcher._ticker.on_ticks(watcher._ticker, None)
    assert engine.state.positions["TESTCO"]["quantity"] == 100
    watcher._ticker.push(12345, 98.0)      # still working afterwards
    assert engine.state.positions["TESTCO"]["quantity"] == 0


def test_an_engine_error_is_counted_not_raised(watcher, engine, monkeypatch):
    watcher.sync()
    monkeypatch.setattr(engine, "_check_stop_take",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    watcher._ticker.push(12345, 98.0)      # must not raise
    assert engine.state.positions["TESTCO"]["quantity"] == 100


def test_a_symbol_without_an_instrument_token_is_skipped(watcher, monkeypatch):
    monkeypatch.setattr(stop_watcher.data_provider, "_instrument_token",
                        lambda s: (_ for _ in ()).throw(KeyError(s)))
    watcher.sync()                          # must not raise
    assert watcher.stats()["watching"] == []


def test_stop_closes_the_stream(watcher):
    watcher.sync()
    ticker = watcher._ticker
    watcher.stop()
    assert ticker.closed is True
    assert watcher.stats()["started"] is False


def test_stats_report_staleness_only_while_something_is_watched(watcher):
    watcher.sync()
    watcher._last_tick_at = time.time() - (stop_watcher.TICK_SILENCE_WARN_SECONDS + 10)
    assert watcher.stats()["stale"] is True
    watcher._tokens = {}
    assert watcher.stats()["stale"] is False, "silence with nothing held is normal"
