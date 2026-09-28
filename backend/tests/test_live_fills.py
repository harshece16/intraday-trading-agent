"""
Issue #155: a live order was booked as filled in full at the modelled price
(the last price moved 3 bp against us), and Kite's answer was never read. A
rejected order became a position the account didn't hold, and real slippage
never reached the journal. These drive the engine's real order path against
a stand-in for Kite.
"""
import pytest

import config
import data_provider
import database
import kite_broker
import trading_engine
from kite_broker import KiteExecutor, OrderNotFilled, OrderUnconfirmed
from state import AppState, _new_position


class FakeKite:
    """Stands in for kiteconnect.KiteConnect: a script of order states."""

    def __init__(self, states, cancel_to=None, fail_reads=0):
        self.states, self.cancel_to, self.fail_reads = list(states), cancel_to, fail_reads
        self.placed, self.cancelled = [], []

    def place_order(self, **kw):
        self.placed.append(kw)
        return f"ord{len(self.placed)}"

    def order_history(self, order_id):
        if self.fail_reads:
            self.fail_reads -= 1
            raise ConnectionError("Kite is unreachable")
        state = self.states[0] if len(self.states) == 1 else self.states.pop(0)
        return [{"status": "PUT ORDER REQ RECEIVED"}, state]

    def cancel_order(self, variety, order_id):
        self.cancelled.append(order_id)
        if self.cancel_to:
            self.states = [self.cancel_to]


def order(status, filled=0, avg=0.0, message=None):
    return {"status": status, "filled_quantity": filled, "average_price": avg, "status_message": message}


def executor(fake):
    ex = KiteExecutor.__new__(KiteExecutor)  # skip __init__: no real KiteConnect
    ex.kite = fake
    return ex


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setattr(config, "KITE_FILL_DEADLINE_S", 0.05)
    monkeypatch.setattr(config, "KITE_FILL_POLL_S", 0.01)
    monkeypatch.setattr(data_provider, "get_ltp", lambda symbol: 100.0)
    eng = trading_engine.TradingEngine(AppState(watchlist=["AAA"], paper_mode=False))
    eng.state.positions["AAA"] = _new_position()
    return eng


def use(eng, fake):
    eng.kite_executor = executor(fake)
    return fake


def hold(eng, qty, price=100.0, stop=98.0, target=103.0):
    eng.state.positions["AAA"] = {**_new_position(), "quantity": qty, "avg_price": price, "stop_price": stop,
                                  "target_price": target, "initial_risk": abs(price - stop), "position_id": "p1"}
    eng.risk.open_positions_count = 1


# ---- the broker's read of an order ------------------------------------------

def test_wait_for_fill_returns_kites_price_and_quantity():
    state = executor(FakeKite([order("OPEN"), order("COMPLETE", 10, 100.4)])).wait_for_fill("o", 1, 0.001)
    assert state == {"status": "COMPLETE", "filled_quantity": 10, "average_price": 100.4, "message": ""}


def test_an_order_still_open_at_the_deadline_is_cancelled_and_its_part_fill_returned():
    fake = FakeKite([order("OPEN", 4, 100.2)], cancel_to=order("CANCELLED", 4, 100.2))
    state = executor(fake).wait_for_fill("o", 0.02, 0.005)
    assert fake.cancelled == ["o"]
    assert (state["status"], state["filled_quantity"]) == ("CANCELLED", 4)


def test_an_order_kite_cannot_be_asked_about_is_unknown_not_unfilled():
    state = executor(FakeKite([order("COMPLETE", 10, 100.0)], fail_reads=10 ** 6)).wait_for_fill("o", 0.02, 0.005)
    assert state["status"] == kite_broker.ORDER_UNKNOWN


def test_one_failed_read_does_not_lose_the_fill():
    state = executor(FakeKite([order("COMPLETE", 10, 100.0)], fail_reads=1)).wait_for_fill("o", 1, 0.001)
    assert state["status"] == "COMPLETE"


# ---- the engine books what Kite did -----------------------------------------

def test_a_live_entry_is_booked_at_kites_price_not_the_modelled_one(engine):
    use(engine, FakeKite([order("COMPLETE", 10, 100.40)]))
    engine._execute("AAA", "BUY", 10, 100.0, reason="ORB", position_id="p1")
    assert engine.state.positions["AAA"]["avg_price"] == 100.40
    assert costs_modelled(100.0) != 100.40
    row = database.trades_between(0)[0]
    assert (row["price"], row["mode"], row["quantity"]) == (100.40, "live", 10)
    assert (row["signal_price"], row["order_id"]) == (100.0, "ord1")
    assert "+40.0 bp against the signal price" in row["note"]


def costs_modelled(price):
    import costs
    return costs.apply_slippage("BUY", price, config.COSTS)


def test_a_rejected_order_books_nothing(engine):
    fake = use(engine, FakeKite([order("REJECTED", message="Insufficient funds")]))
    with pytest.raises(OrderNotFilled, match="Insufficient funds"):
        engine._execute("AAA", "BUY", 10, 100.0, position_id="p1")
    assert len(fake.placed) == 1
    assert engine.state.positions["AAA"]["quantity"] == 0
    assert database.trades_between(0) == []
    assert any("did not fill" in a["message"] and a["level"] == "error" for a in engine.state.activity)


def test_a_part_fill_books_only_what_filled(engine):
    use(engine, FakeKite([order("OPEN", 4, 100.2)], cancel_to=order("CANCELLED", 4, 100.2)))
    engine._execute("AAA", "BUY", 10, 100.0, position_id="p1")
    assert engine.state.positions["AAA"]["quantity"] == 4
    assert database.trades_between(0)[0]["quantity"] == 4


def test_a_part_filled_exit_leaves_the_rest_open_and_counted(engine):
    hold(engine, 10)
    use(engine, FakeKite([order("OPEN", 6, 97.9)], cancel_to=order("CANCELLED", 6, 97.9)))
    assert engine.check_stop_from_tick("AAA", 97.0) is True
    assert engine.state.positions["AAA"]["quantity"] == 4
    assert engine.risk.open_positions_count == 1


def test_a_live_exit_realizes_pnl_from_kites_price(engine):
    hold(engine, 10)
    use(engine, FakeKite([order("COMPLETE", 10, 97.5)]))
    engine.check_stop_from_tick("AAA", 97.9)
    row = database.trades_between(0)[0]
    assert row["realized_gross"] == pytest.approx(-25.0)
    assert engine.state.positions["AAA"]["quantity"] == 0 and engine.risk.open_positions_count == 0


def test_risk_per_share_is_measured_from_the_fill(engine, monkeypatch):
    use(engine, FakeKite([order("COMPLETE", 10, 100.5)]))
    monkeypatch.setattr(engine, "_entry_block_reason", lambda *a: None)
    monkeypatch.setattr(trading_engine.confidence, "score_trade",
                        lambda *a: {"score": 99, "label": "high", "explanation": ""})
    monkeypatch.setattr(trading_engine.liquidity, "check", lambda *a: (True, None, None))
    monkeypatch.setattr(engine.risk, "position_size", lambda *a, **kw: 10)
    monkeypatch.setattr(trading_engine.trader_brain, "recheck_plan", lambda *a: {"ok": True, "rrr": 2.0})
    plan = {"stop": 98.0, "target": 104.0, "size_factor": 1.0}
    assert engine._try_enter("AAA", "LONG", 100.0, [], {"setup": "ORB", "entry_mode": "checklist",
                                                        "checklist": {"long": plan}}) is True
    pos = engine.state.positions["AAA"]
    assert (pos["stop_price"], pos["target_price"]) == (98.0, 104.0)  # chart levels don't move
    assert pos["initial_risk"] == pytest.approx(2.5)


def test_a_rejected_entry_is_a_blocked_entry_not_a_crash(engine, monkeypatch):
    use(engine, FakeKite([order("REJECTED", message="RMS: margin exceeds")]))
    monkeypatch.setattr(engine, "_entry_block_reason", lambda *a: None)
    monkeypatch.setattr(trading_engine.confidence, "score_trade",
                        lambda *a: {"score": 99, "label": "high", "explanation": ""})
    monkeypatch.setattr(trading_engine.liquidity, "check", lambda *a: (True, None, None))
    monkeypatch.setattr(engine.risk, "position_size", lambda *a, **kw: 10)
    assert engine._try_enter("AAA", "LONG", 100.0, [], {"setup": "ORB"}) is False
    assert engine.risk.open_positions_count == 0


# ---- an order Kite never confirmed ------------------------------------------

def test_an_unconfirmed_exit_books_nothing_and_blocks_a_second_closing_order(engine):
    hold(engine, 10)
    fake = use(engine, FakeKite([order("COMPLETE", 10, 97.5)], fail_reads=10 ** 6))
    assert engine.check_stop_from_tick("AAA", 97.0) is False  # swallowed, as the tick stream needs
    assert engine.state.positions["AAA"]["quantity"] == 10
    assert "AAA" in engine._unconfirmed_orders
    engine.check_stop_from_tick("AAA", 96.0)
    assert len(fake.placed) == 1  # no second closing order on top of the first
    with pytest.raises(OrderUnconfirmed):
        engine._execute("AAA", "SELL", 10, 96.0)


def test_an_unconfirmed_exit_is_booked_once_kite_answers(engine):
    hold(engine, 10)
    fake = use(engine, FakeKite([order("COMPLETE", 10, 97.5)], fail_reads=10 ** 6))
    engine.check_stop_from_tick("AAA", 97.0)
    fake.fail_reads = 0
    engine._resolve_unconfirmed_orders()
    assert engine._unconfirmed_orders == {}
    assert engine.state.positions["AAA"]["quantity"] == 0 and engine.risk.open_positions_count == 0
    row = database.trades_between(0)[0]
    assert (row["price"], row["order_id"], row["position_id"]) == (97.5, "ord1", "p1")
    assert len(fake.placed) == 1


def test_an_unconfirmed_entry_that_filled_is_restored_with_its_stop(engine):
    fake = use(engine, FakeKite([order("COMPLETE", 10, 100.3)], fail_reads=10 ** 6))
    with pytest.raises(OrderUnconfirmed):
        engine._execute("AAA", "BUY", 10, 100.0, reason="ORB", position_id="p9",
                        note="Varsity checklist passed: stop 98.00, target 104.00")
    fake.fail_reads = 0
    engine._resolve_unconfirmed_orders()
    pos = engine.state.positions["AAA"]
    assert (pos["quantity"], pos["avg_price"], pos["position_id"]) == (10, 100.3, "p9")
    assert (pos["stop_price"], pos["target_price"]) == (98.0, 104.0)
    assert pos["initial_risk"] == pytest.approx(2.3)
    assert engine.risk.open_positions_count == 1


def test_an_unconfirmed_order_that_never_filled_frees_the_symbol(engine):
    fake = use(engine, FakeKite([order("REJECTED", message="circuit limit")], fail_reads=10 ** 6))
    with pytest.raises(OrderUnconfirmed):
        engine._execute("AAA", "BUY", 10, 100.0)
    fake.fail_reads = 0
    engine._resolve_unconfirmed_orders()
    assert engine._unconfirmed_orders == {} and database.trades_between(0) == []
    fake.states = [order("COMPLETE", 10, 100.1)]
    engine._execute("AAA", "BUY", 10, 100.0)  # a new order goes through again
    assert engine.state.positions["AAA"]["quantity"] == 10


def test_a_kite_failure_while_resolving_does_not_raise(engine):
    hold(engine, 10)
    use(engine, FakeKite([order("COMPLETE", 10, 97.5)], fail_reads=10 ** 6))
    engine.check_stop_from_tick("AAA", 97.0)
    engine._resolve_unconfirmed_orders()  # Kite still unreachable
    assert "AAA" in engine._unconfirmed_orders


# ---- paper is unchanged ------------------------------------------------------

def test_paper_fills_still_use_the_modelled_price_and_record_the_signal_price(engine):
    engine.state.paper_mode = True
    engine._execute("AAA", "BUY", 10, 100.0, position_id="p1")
    row = database.trades_between(0)[0]
    assert row["mode"] == "paper" and row["price"] == pytest.approx(costs_modelled(100.0))
    assert row["signal_price"] == 100.0 and row["order_id"] is None


def test_an_old_journal_gains_the_new_columns(tmp_path, monkeypatch):
    import sqlite3
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE trades (id TEXT PRIMARY KEY, position_id TEXT, ts REAL NOT NULL, symbol TEXT NOT NULL, "
                 "side TEXT, quantity INTEGER, price REAL, mode TEXT, reason TEXT, note TEXT, realized REAL, "
                 "charges REAL, initial_risk REAL, r_multiple REAL, checklist_json TEXT, realized_gross REAL)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(database, "DB_PATH", path)
    database._local.conn = None
    AppState(watchlist=[], paper_mode=True).record_trade("AAA", "BUY", 1, 10.0, mode="paper", signal_price=9.9)
    assert database.trades_between(0)[0]["signal_price"] == 9.9
