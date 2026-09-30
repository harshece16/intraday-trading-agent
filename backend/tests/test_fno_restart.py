"""#187: state.fno_positions lived only in memory, so a restart dropped an
open option position's premium stop, target and 15:08 square-off. Worse, its
entry leg in `trades` (under the option's tradingsymbol, with "stop X,
target Y" in the note) was restored as a CASH position in that symbol.

A restart now rebuilds today's open option positions from fno_trades and
their legs, keeps them out of the cash restore, counts them against their
underlying's one entry a day, watches them whether or not F&O is switched
on, and treats a live one as #156/#183 treat a live cash position: its
closing order is real, and Kite must confirm it is still open first."""
import pytest

import data_provider
import database
import trading_engine
from state import AppState
from tests.fno_kit import LOT, FakeKite, analysis, engine, fno_row, order, use


def _open(monkeypatch, paper=True, kite=None, underlying="ACME"):
    e = engine(monkeypatch, paper=paper, kite=kite)
    assert e._try_enter_fno(underlying, "LONG", analysis()) is True
    return e, dict(e.state.fno_positions[underlying])


def _restart(paper=True):
    return trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=paper))


def test_an_open_paper_option_is_restored_as_an_option_not_as_cash(monkeypatch):
    _, before = _open(monkeypatch)
    e = _restart()
    pos = e.state.fno_positions["ACME"]
    for key in ("tradingsymbol", "is_call", "strike", "expiry", "lots", "lot_size", "entry_premium",
                "stop_premium", "target_premium", "position_id", "live"):
        assert pos[key] == before[key], key
    assert pos["entry_charges"] == pytest.approx(before["entry_charges"])
    assert pos["entry_iv"] == pytest.approx(before["entry_iv"])
    assert before["tradingsymbol"] not in e.state.positions               # the old bug
    assert e.state.restored_positions == [] and e.state.restored_fno_positions == ["ACME"]
    assert e.risk.open_positions_count == 1
    assert e.state.strategy_state["ACME"]["entries_today"] == 1          # counted on the underlying
    assert before["tradingsymbol"] not in e.state.strategy_state
    assert any("Restored 1 open F&O position" in a["message"] for a in e.state.activity)


def test_the_restored_option_is_watched_with_fno_switched_off(monkeypatch):
    _, before = _open(monkeypatch)
    e = _restart()
    assert e._fno_active() is False                                       # the switch is in memory only
    monkeypatch.setattr(data_provider, "get_ltp", lambda symbol: 900.0)   # the call's premium collapses
    e._process_fno()
    assert e.state.fno_positions == {} and e.risk.open_positions_count == 0
    row = fno_row(before["position_id"])
    assert row["exit_reason"] == "fno_stop_loss" and row["realized"] < 0


def test_the_restored_option_is_squared_off(monkeypatch):
    _, before = _open(monkeypatch)
    e = _restart()
    monkeypatch.setattr(data_provider, "get_ltp", lambda symbol: 1000.0)
    assert e._close_fno("ACME", "fno_auto_square_off") is True
    assert fno_row(before["position_id"])["exit_reason"] == "fno_auto_square_off"


def test_a_closed_option_is_not_restored_but_still_counts_for_the_day(monkeypatch):
    e, before = _open(monkeypatch)
    monkeypatch.setattr(data_provider, "get_ltp", lambda symbol: 1000.0)
    e._close_fno("ACME", "fno_take_profit")
    again = _restart()
    assert again.state.fno_positions == {} and again.risk.open_positions_count == 0
    assert again.state.strategy_state["ACME"]["entries_today"] == 1
    assert again._fno_entry_block_reason("ACME", "LONG").startswith("ACME was already traded today")


def test_a_paper_option_is_not_restored_in_live_mode(monkeypatch):
    _open(monkeypatch)
    assert _restart(paper=False).state.fno_positions == {}


def test_a_part_filled_exit_restores_only_the_rest(monkeypatch):
    fake = FakeKite([order("COMPLETE", 4 * LOT, 20.0)], quote=20.0)
    e, before = _open(monkeypatch, paper=False, kite=fake)
    fake.states, fake.cancel_to = [order("OPEN", 3 * LOT, 11.3)], order("CANCELLED", 3 * LOT, 11.3)
    e._close_fno("ACME", "fno_stop_loss")
    pos = _restart(paper=False).state.fno_positions["ACME"]
    assert pos["lots"] == 1 and pos["entry_lots"] == 4
    assert pos["entry_charges"] == pytest.approx(before["entry_charges"] / 4)
    assert pos["realized_so_far"] == pytest.approx(database.trades_between(0)[-1]["realized"])


# ---- a live option across a restart (#156's rules) ------------------------------

def _live_then_restart_in_paper(monkeypatch, kite_holds):
    fake = FakeKite([order("COMPLETE", 4 * LOT, 20.0)], quote=20.0)
    _, before = _open(monkeypatch, paper=False, kite=fake)
    e = _restart(paper=True)
    after = FakeKite([order("COMPLETE", 4 * LOT, 18.0)], quote=18.5,
                     positions=[{"tradingsymbol": before["tradingsymbol"], "quantity": kite_holds, "product": "MIS"}]
                     if kite_holds else [])
    use(e, after)
    return e, before, after


def test_a_live_option_is_restored_in_paper_and_said_loudly(monkeypatch):
    e, before, _ = _live_then_restart_in_paper(monkeypatch, 100)
    assert e.state.paper_mode is True and e.state.fno_positions["ACME"]["live"] is True
    assert e._unverified_live_fno == {"ACME"} and e._holds_live() is True
    assert any(a["level"] == "error" and "LIVE option position is open" in a["message"] for a in e.state.activity)


def test_its_close_is_a_real_order_once_kite_confirms_it(monkeypatch):
    e, before, kite = _live_then_restart_in_paper(monkeypatch, 100)
    assert e._close_fno("ACME", "fno_auto_square_off") is True
    assert kite.placed[-1]["exchange"] == "NFO" and kite.placed[-1]["transaction_type"] == "SELL"
    leg = database.trades_between(0)[-1]
    assert (leg["mode"], leg["price"], leg["order_id"]) == ("live", 18.0, "ord1")


def test_kite_flat_drops_it_and_sends_nothing(monkeypatch):
    e, before, kite = _live_then_restart_in_paper(monkeypatch, 0)
    assert e._close_fno("ACME", "fno_auto_square_off") is True
    assert kite.placed == [] and e.state.fno_positions == {} and e.risk.open_positions_count == 0
    assert any("closed outside the engine" in a["message"] for a in e.state.activity)


def test_kite_unreadable_sends_no_order(monkeypatch):
    e, before, kite = _live_then_restart_in_paper(monkeypatch, 100)
    kite.down = True
    with pytest.raises(trading_engine.OrderUnconfirmed):
        e._close_fno("ACME", "fno_auto_square_off")
    assert kite.placed == [] and "ACME" in e.state.fno_positions


def test_reconciliation_verifies_it_and_does_not_call_it_untracked(monkeypatch):
    e, before, kite = _live_then_restart_in_paper(monkeypatch, 100)
    kite.day.append({"tradingsymbol": "OTHER26OCT100CE", "quantity": 50, "product": "MIS"})
    e._check_position_reconciliation()
    assert e._unverified_live_fno == set()
    assert e._untracked_kite_positions == {"OTHER26OCT100CE"}             # ours is tracked
    assert any("Kite confirms the restored live option position" in a["message"] for a in e.state.activity)
