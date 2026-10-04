"""
Issue #156: a live position was left unwatched when the backend restarted
while it was open. The restart came back in Paper, rehydration restored
paper legs only, and reconciliation ran only in live mode, so nothing
checked the stop or the target and the 15:08 square-off skipped it.

A position now carries whether it is real money, and its closing order
goes where that says, whatever mode the engine is in.
"""
import time

import pytest

import config
import data_provider
import database
import trading_engine
from kite_broker import KiteExecutor
from state import AppState, _new_position

NOTE = "Varsity checklist passed on the 11:20 candle: stop 98.00, target 104.00, reward-to-risk 1.57 at the entry price"


class FakeKite:
    def __init__(self, positions=None, fill_price=97.5, down=False):
        # positions=None: Kite's day book agrees with the engine (every live
        # close reads it first since #250).
        self.day = None if positions is None else list(positions)
        self.fill_price, self.down, self.placed, self.eng = fill_price, down, [], None

    def positions(self):
        if self.down:
            raise ConnectionError("Kite is unreachable")
        if self.day is None:
            return {"day": [] if self.eng is None else [
                {"tradingsymbol": s, "quantity": p["quantity"], "product": "MIS"}
                for s, p in self.eng.state.positions.items() if p["quantity"]], "net": []}
        return {"day": self.day, "net": []}

    def place_order(self, **kw):
        if self.down:
            raise ConnectionError("Kite is unreachable")
        self.placed.append(kw)
        return f"ord{len(self.placed)}"

    def order_history(self, order_id):
        qty = self.placed[-1]["quantity"]
        return [{"status": "COMPLETE", "filled_quantity": qty, "average_price": self.fill_price}]


def held(symbol, qty):
    return {"tradingsymbol": symbol, "quantity": qty, "product": "MIS"}


def journal_leg(symbol="AAA", side="BUY", qty=10, price=100.0, mode="live", pid="L1"):
    database.record_trade({"id": f"{pid}-{side}", "position_id": pid, "ts": time.time() - 60, "symbol": symbol,
                           "side": side, "quantity": qty, "price": price, "mode": mode, "reason": "test",
                           "note": NOTE, "realized": 0.0, "charges": 10.0})


def restarted(fake, paper_mode=True, monkeypatch=None):
    eng = trading_engine.TradingEngine(AppState(watchlist=["AAA"], paper_mode=paper_mode))
    ex = KiteExecutor.__new__(KiteExecutor)
    ex.kite = fake
    eng.kite_executor = ex
    fake.eng = eng
    return eng


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(config, "KITE_FILL_DEADLINE_S", 0.05)
    monkeypatch.setattr(config, "KITE_FILL_POLL_S", 0.01)
    monkeypatch.setattr(data_provider, "get_ltp", lambda symbol: 97.0)


def test_a_restart_in_paper_restores_the_live_position_and_says_so_loudly():
    journal_leg()
    eng = restarted(FakeKite([held("AAA", 10)]))
    pos = eng.state.positions["AAA"]
    assert eng.state.paper_mode is True
    assert (pos["quantity"], pos["live"], pos["stop_price"], pos["target_price"]) == (10, True, 98.0, 104.0)
    assert eng.risk.open_positions_count == 1
    assert any(a["level"] == "error" and "LIVE position is open" in a["message"] for a in eng.state.activity)


def test_its_stop_closes_it_with_a_real_order_while_the_engine_is_in_paper():
    journal_leg()
    fake = FakeKite([held("AAA", 10)])
    eng = restarted(fake)
    assert eng.check_stop_from_tick("AAA", 97.0) is True
    assert [(o["transaction_type"], o["quantity"]) for o in fake.placed] == [("SELL", 10)]
    exit_leg = database.trades_between(0)[-1]
    assert (exit_leg["mode"], exit_leg["price"], exit_leg["position_id"]) == ("live", 97.5, "L1")
    assert eng.state.positions["AAA"]["quantity"] == 0


def test_the_square_off_closes_it_too():
    journal_leg(side="SELL")
    fake = FakeKite([held("AAA", -10)])
    eng = restarted(fake)
    assert eng._square_off_all() == ["AAA"]
    assert [(o["transaction_type"], o["quantity"]) for o in fake.placed] == [("BUY", 10)]


def test_a_position_closed_in_kite_while_the_engine_was_down_sends_no_order():
    # the closing order would otherwise open a new short
    journal_leg()
    fake = FakeKite([])
    eng = restarted(fake)
    eng.check_stop_from_tick("AAA", 97.0)
    assert fake.placed == []
    assert eng.state.positions["AAA"]["quantity"] == 0 and eng.risk.open_positions_count == 0
    assert any("closed outside the engine" in a["message"] for a in eng.state.activity)


def test_a_position_cut_in_kite_is_closed_at_kites_quantity():
    journal_leg()
    fake = FakeKite([held("AAA", 4)])
    eng = restarted(fake)
    eng.check_stop_from_tick("AAA", 97.0)
    assert [o["quantity"] for o in fake.placed] == [4]
    assert eng.state.positions["AAA"]["quantity"] == 0


def test_kite_holding_the_other_side_is_reported_and_left_alone():
    journal_leg()
    eng = restarted(FakeKite([held("AAA", -10)]))
    eng._verify_live_position("AAA")
    assert eng.state.positions["AAA"]["quantity"] == 10
    assert any("Kite holds -10 in AAA" in a["message"] and a["level"] == "error" for a in eng.state.activity)


def test_no_order_is_sent_while_kite_cannot_confirm_the_position():
    journal_leg()
    fake = FakeKite([held("AAA", 10)], down=True)
    eng = restarted(fake)
    assert eng.check_stop_from_tick("AAA", 97.0) is False  # swallowed; the tick stream survives
    assert fake.placed == [] and eng.state.positions["AAA"]["quantity"] == 10
    fake.down = False
    assert eng.check_stop_from_tick("AAA", 97.0) is True   # and it closes once Kite is back
    assert len(fake.placed) == 1


def test_reconciliation_verifies_restored_positions_even_in_paper(monkeypatch):
    journal_leg()
    eng = restarted(FakeKite([held("AAA", 10)]))
    assert eng._holds_live() is True
    eng._check_position_reconciliation()
    assert eng._unverified_live == set()
    assert eng._untracked_kite_positions == set()


def test_going_live_is_refused_while_kite_holds_a_position_the_engine_does_not(monkeypatch):
    eng = restarted(FakeKite([held("ZZZ", 5)]))
    monkeypatch.setattr(data_provider, "kite_session_status", lambda probe=False: {"connected": True})
    readiness = eng.live_readiness(probe=True)
    assert readiness["ready"] is False and "ZZZ" in " ".join(readiness["blockers"])


# ---- the mode is switched while a position is open ---------------------------

def test_a_paper_position_never_sends_a_real_order_after_a_switch_to_live():
    fake = FakeKite()
    eng = restarted(fake)
    eng.state.positions["AAA"] = _new_position()
    eng._execute("AAA", "BUY", 10, 100.0, position_id="p1")
    assert eng.state.positions["AAA"]["live"] is False
    eng.state.positions["AAA"].update(stop_price=98.0, target_price=104.0)
    eng.state.paper_mode = False
    assert eng.check_stop_from_tick("AAA", 97.0) is True
    assert fake.placed == []
    assert database.trades_between(0)[-1]["mode"] == "paper"


def test_a_live_position_is_closed_with_a_real_order_after_a_switch_to_paper():
    fake = FakeKite(fill_price=100.2)
    eng = restarted(fake, paper_mode=False)
    eng.state.positions["AAA"] = _new_position()
    eng._execute("AAA", "BUY", 10, 100.0, position_id="p1")
    assert eng.state.positions["AAA"]["live"] is True
    eng.state.positions["AAA"].update(stop_price=98.0, target_price=104.0)
    eng.state.paper_mode = True
    fake.fill_price = 97.5
    assert eng.check_stop_from_tick("AAA", 97.0) is True
    assert [o["transaction_type"] for o in fake.placed] == ["BUY", "SELL"]
    assert database.trades_between(0)[-1]["mode"] == "live"
