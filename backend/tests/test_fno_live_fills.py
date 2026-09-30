"""#186: a live option order was booked at the premium quoted just before it,
and Kite's answer was never read, so a rejected order became a position the
account didn't hold. The F&O path now reads Kite's fill the way #155/#182
made the cash path do: executed premium and quantity, rejection, part
fills, and an order Kite never confirmed. Driven through the real
KiteExecutor against a stand-in for kiteconnect."""
import pytest

import database
from kite_broker import OrderUnconfirmed
from tests.fno_kit import LOT, FakeKite, analysis, engine, evaluations, fno_row, order


def _enter(e, underlying="ACME"):
    return e._try_enter_fno(underlying, "LONG", analysis())


def _legs():
    return database.trades_between(0)


def test_a_live_buy_is_booked_at_kites_premium_and_quantity(monkeypatch):
    fake = FakeKite([order("COMPLETE", 4 * LOT, 20.60)], quote=20.0)   # 20% of 10,000 / (20 x 25) = 4 lots
    e = engine(monkeypatch, paper=False, kite=fake)
    assert _enter(e) is True
    assert fake.placed[0]["exchange"] == "NFO" and fake.placed[0]["quantity"] == 4 * LOT
    pos = e.state.fno_positions["ACME"]
    assert (pos["entry_premium"], pos["lots"], pos["live"]) == (20.60, 4, True)
    # the premium stop and target are percentages of the premium actually paid
    assert (pos["stop_premium"], pos["target_premium"]) == (round(20.60 * 0.6, 2), round(20.60 * 1.8, 2))
    [leg] = _legs()
    assert (leg["price"], leg["quantity"], leg["mode"]) == (20.60, 100, "live")
    assert (leg["signal_price"], leg["order_id"]) == (20.0, "ord1")
    assert "+300.0 bp against the quoted premium 20.00" in leg["note"]
    assert fno_row(pos["position_id"])["entry_premium"] == 20.60


def test_a_rejected_buy_books_nothing_and_does_not_spend_the_day(monkeypatch):
    fake = FakeKite([order("REJECTED", message="RMS: margin exceeds")])
    e = engine(monkeypatch, paper=False, kite=fake)
    assert _enter(e) is False
    assert e.state.fno_positions == {} and _legs() == [] and e.risk.open_positions_count == 0
    assert (e.state.strategy_state.get("ACME") or {}).get("entries_today", 0) == 0
    ev = evaluations()[-1]
    assert ev["executed"] == 0 and "margin exceeds" in ev["block_reason"]
    assert any(a["level"] == "error" and "did not fill" in a["message"] for a in e.state.activity)


def test_a_part_filled_buy_books_only_what_filled(monkeypatch):
    fake = FakeKite([order("OPEN", LOT, 20.1)], cancel_to=order("CANCELLED", LOT, 20.1))
    e = engine(monkeypatch, paper=False, kite=fake)
    assert _enter(e) is True
    assert fake.cancelled == ["ord1"]
    assert e.state.fno_positions["ACME"]["lots"] == 1 and _legs()[0]["quantity"] == LOT


def _held(monkeypatch, fake, lots=4, premium=20.0):
    fake.states = [order("COMPLETE", lots * LOT, premium)]
    e = engine(monkeypatch, paper=False, kite=fake)
    assert _enter(e) is True
    return e


def test_a_live_exit_is_booked_at_kites_premium(monkeypatch):
    fake = FakeKite(quote=20.0)
    e = _held(monkeypatch, fake)
    fake.quote, fake.states = 11.5, [order("COMPLETE", 4 * LOT, 11.20)]
    assert e._check_fno_stop_take("ACME") is True                     # 11.5 <= stop 12.0
    assert fake.placed[-1]["transaction_type"] == "SELL"
    exit_leg = _legs()[-1]
    assert (exit_leg["price"], exit_leg["signal_price"], exit_leg["order_id"]) == (11.20, 11.5, "ord2")
    assert exit_leg["realized_gross"] == pytest.approx((11.20 - 20.0) * 100)
    assert e.state.fno_positions == {} and e.risk.open_positions_count == 0
    row = fno_row(exit_leg["position_id"])
    assert row["exit_premium"] == 11.20 and row["realized"] == pytest.approx(exit_leg["realized"])


def test_a_rejected_exit_leaves_the_position_open_and_watched(monkeypatch):
    fake = FakeKite(quote=20.0)
    e = _held(monkeypatch, fake)
    fake.quote, fake.states = 11.5, [order("REJECTED", message="circuit limit")]
    assert e._check_fno_stop_take("ACME") is False
    assert e.state.fno_positions["ACME"]["lots"] == 4 and len(_legs()) == 1
    assert any("couldn't close" in a["message"] and a["level"] == "error" for a in e.state.activity)
    fake.states = [order("COMPLETE", 4 * LOT, 11.4)]
    assert e._check_fno_stop_take("ACME") is True                     # the next tick tries again
    assert e.state.fno_positions == {}


def test_a_part_filled_exit_leaves_the_rest_open_and_journals_the_whole_on_close(monkeypatch):
    fake = FakeKite(quote=20.0)
    e = _held(monkeypatch, fake)
    fake.quote = 11.5
    fake.states, fake.cancel_to = [order("OPEN", 3 * LOT, 11.3)], order("CANCELLED", 3 * LOT, 11.3)
    assert e._check_fno_stop_take("ACME") is True
    pos = e.state.fno_positions["ACME"]
    assert pos["lots"] == 1 and e.risk.open_positions_count == 1
    assert fno_row(pos["position_id"])["exit_ts"] is None
    fake.states, fake.cancel_to = [order("COMPLETE", LOT, 11.0)], None
    assert e._close_fno("ACME", "fno_auto_square_off") is True
    first, second = _legs()[1], _legs()[2]
    assert (first["quantity"], second["quantity"]) == (3 * LOT, LOT)
    row = fno_row(pos["position_id"])
    assert row["realized"] == pytest.approx(first["realized"] + second["realized"])
    assert row["r_multiple"] == pytest.approx(row["realized"] / (20.0 * 4 * LOT))
    # the two exit legs release the entry charges exactly once between them
    charges = sum(leg["charges"] for leg in _legs())
    assert sum(leg["realized_gross"] for leg in _legs()[1:]) - charges == pytest.approx(row["realized"])


def test_an_unconfirmed_buy_books_nothing_blocks_a_second_and_is_booked_when_kite_answers(monkeypatch):
    fake = FakeKite([order("COMPLETE", 4 * LOT, 20.3)], fail_reads=10 ** 6)
    e = engine(monkeypatch, paper=False, kite=fake)
    assert _enter(e) is True                                          # an order went out
    assert e.state.fno_positions == {} and _legs() == []
    assert e.state.strategy_state["ACME"]["entries_today"] == 1
    assert _enter(e) is False and len(fake.placed) == 1               # no second order on top
    fake.fail_reads = 0
    e._resolve_unconfirmed_orders()
    assert e._unconfirmed_orders == {}
    pos = e.state.fno_positions["ACME"]
    assert (pos["entry_premium"], pos["lots"]) == (20.3, 4) and e.risk.open_positions_count == 1
    assert _legs()[0]["order_id"] == "ord1" and evaluations()[-1]["executed"] == 1
    assert e.state.strategy_state["ACME"]["entries_today"] == 1       # spent once, not twice


def test_an_unconfirmed_sell_blocks_a_second_closing_order(monkeypatch):
    fake = FakeKite(quote=20.0)
    e = _held(monkeypatch, fake)
    fake.quote, fake.states, fake.fail_reads = 11.5, [order("COMPLETE", 4 * LOT, 11.4)], 10 ** 6
    assert e._check_fno_stop_take("ACME") is False
    assert e._check_fno_stop_take("ACME") is False
    assert len(fake.placed) == 2                                      # the entry and one sale
    with pytest.raises(OrderUnconfirmed):
        e._close_fno("ACME", "kill_switch")
    fake.fail_reads = 0
    e._resolve_unconfirmed_orders()
    assert e.state.fno_positions == {} and _legs()[-1]["price"] == 11.4


def test_the_kill_switch_reports_a_rejected_option_sale_and_stays_live(monkeypatch):
    fake = FakeKite(quote=20.0)
    e = _held(monkeypatch, fake)
    fake.states = [order("REJECTED", message="exchange closed")]
    out = e.stop_and_flatten()
    assert out["failed"] and out["failed"][0]["symbol"] == "ACME" and out["paper_mode"] is False
    assert "ACME" in e.state.fno_positions


def test_paper_still_books_the_model_premium_and_sends_nothing(monkeypatch):
    e = engine(monkeypatch)
    monkeypatch.setattr(e, "_ensure_kite", lambda: pytest.fail("a paper option reached Kite"))
    assert _enter(e) is True
    leg = _legs()[0]
    assert leg["mode"] == "paper" and leg["order_id"] is None and leg["signal_price"] is None
