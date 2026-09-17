"""
Issue #21 — every P&L the app reported used to be gross.

state.apply_fill() computed (fill - average price) x quantity. Slippage was
inside the fill price, but brokerage, STT, exchange fees, GST and stamp duty
were filed beside the trade in `charges` and never subtracted anywhere: not
from the header's "Realized today", not from the trade journal, not from the
2% daily loss limit, and not from the Scorecard's R-multiples — which made
live expectancy incomparable with the backtester's, which has always been net.

These tests pin the round trip down: both legs' charges come off the closing
fill exactly once, gross stays available beside it, and the journal's own
history gets restated rather than left half gross and half net.
"""
import sqlite3

import pytest

import config
import database
import state as state_mod
from state import AppState


ENTRY_CHARGES = 12.47   # the real BEL figures from the journal
EXIT_CHARGES = 8.20


@pytest.fixture
def st():
    return AppState(watchlist=["TESTCO"], paper_mode=True)


def _round_trip(st, entry=100.0, exit_=110.0, qty=10, side="BUY"):
    """Open then close a position, returning the closing fill's numbers."""
    close_side = "SELL" if side == "BUY" else "BUY"
    st.apply_fill("TESTCO", side, qty, entry, charges=ENTRY_CHARGES)
    return st.apply_fill("TESTCO", close_side, qty, exit_, charges=EXIT_CHARGES)


def test_both_legs_charges_come_off_the_closing_fill(st):
    fill = _round_trip(st)
    assert fill["gross"] == pytest.approx(100.0)                      # (110 - 100) x 10
    assert fill["charges_deducted"] == pytest.approx(ENTRY_CHARGES + EXIT_CHARGES)
    assert fill["net"] == pytest.approx(100.0 - ENTRY_CHARGES - EXIT_CHARGES)


def test_opening_fill_reports_no_pnl_but_banks_its_charges(st):
    fill = st.apply_fill("TESTCO", "BUY", 10, 100.0, charges=ENTRY_CHARGES)
    assert (fill["gross"], fill["charges_deducted"], fill["net"]) == (0.0, 0.0, 0.0)
    assert st.positions["TESTCO"]["charges"] == pytest.approx(ENTRY_CHARGES)
    assert st.realized_pnl_today == 0.0


def test_a_short_round_trip_is_also_net(st):
    fill = _round_trip(st, entry=110.0, exit_=100.0, side="SELL")
    assert fill["gross"] == pytest.approx(100.0)
    assert fill["net"] == pytest.approx(100.0 - ENTRY_CHARGES - EXIT_CHARGES)


def test_charges_bigger_than_the_move_turn_a_gross_win_into_a_net_loss(st):
    """The case that matters: a trade that looks profitable and isn't."""
    fill = _round_trip(st, entry=100.0, exit_=101.0, qty=10)   # +10 gross
    assert fill["gross"] > 0
    assert fill["net"] < 0
    assert st.realized_pnl_today == pytest.approx(fill["net"])


def test_running_realized_total_is_net(st):
    _round_trip(st)
    _round_trip(st, entry=100.0, exit_=90.0)
    expected = (100.0 - ENTRY_CHARGES - EXIT_CHARGES) + (-100.0 - ENTRY_CHARGES - EXIT_CHARGES)
    assert st.realized_pnl_today == pytest.approx(expected)


def test_a_partial_exit_is_not_charged_for_the_whole_position(st):
    """Half the position closing releases half the opening charges, and the
    rest stays on the position for the second exit — never double-counted."""
    st.apply_fill("TESTCO", "BUY", 10, 100.0, charges=ENTRY_CHARGES)
    first = st.apply_fill("TESTCO", "SELL", 4, 110.0, charges=EXIT_CHARGES)
    assert first["charges_deducted"] == pytest.approx(ENTRY_CHARGES * 0.4 + EXIT_CHARGES)
    assert st.positions["TESTCO"]["charges"] == pytest.approx(ENTRY_CHARGES * 0.6)

    second = st.apply_fill("TESTCO", "SELL", 6, 110.0, charges=EXIT_CHARGES)
    assert second["charges_deducted"] == pytest.approx(ENTRY_CHARGES * 0.6 + EXIT_CHARGES)
    total_deducted = first["charges_deducted"] + second["charges_deducted"]
    assert total_deducted == pytest.approx(ENTRY_CHARGES + 2 * EXIT_CHARGES)


def test_closing_resets_the_positions_charge_bucket(st):
    _round_trip(st)
    assert st.positions["TESTCO"]["charges"] == pytest.approx(0.0)


def test_the_daily_loss_limit_sees_the_net_figure(st):
    """The 2% limit used to be measured on gross P&L, so charges could push a
    day past the limit without the engine ever noticing."""
    import risk_manager
    risk = risk_manager.RiskManager({"total_capital": 100_000, "max_daily_loss_pct": 2.0})
    limit = -2000.0
    # -1990 gross sits just inside the 2% limit; the 20.67 of charges on the
    # round trip is what actually takes the day past it
    fill = _round_trip(st, entry=1000.0, exit_=801.0, qty=10)
    assert fill["gross"] == pytest.approx(-1990.0)

    assert fill["gross"] > limit, "gross alone would not have tripped the limit"
    assert fill["net"] < limit
    risk.record_realized_pnl(fill["net"])
    assert risk.daily_loss_limit_hit(), "net of charges, the day is past the limit"


def test_the_journal_stores_gross_and_net_side_by_side(st):
    st.apply_fill("TESTCO", "BUY", 10, 100.0, charges=ENTRY_CHARGES)
    fill = st.apply_fill("TESTCO", "SELL", 10, 110.0, charges=EXIT_CHARGES)
    st.record_trade("TESTCO", "SELL", 10, 110.0, mode="paper", realized=fill["net"],
                    realized_gross=fill["gross"], charges=EXIT_CHARGES, initial_risk=2.0,
                    position_id="p1")
    row = database.recent_trades(limit=1)[0]
    assert row["realized"] == pytest.approx(100.0 - ENTRY_CHARGES - EXIT_CHARGES)
    assert row["realized_gross"] == pytest.approx(100.0)
    # the charges column stays this leg's own charges, so summing it over every
    # row still gives the day's total rather than counting the entry twice
    assert row["charges"] == pytest.approx(EXIT_CHARGES)


def test_tax_summary_keeps_turnover_gross_and_pnl_net(st):
    """Trade-wise turnover is defined before expenses — charges are claimed
    separately as a business expense (Varsity, Markets and Taxation)."""
    st.record_trade("TESTCO", "BUY", 10, 100.0, mode="paper", realized=0.0,
                    realized_gross=0.0, charges=ENTRY_CHARGES, position_id="p1")
    st.record_trade("TESTCO", "SELL", 10, 110.0, mode="paper",
                    realized=100.0 - ENTRY_CHARGES - EXIT_CHARGES, realized_gross=100.0,
                    charges=EXIT_CHARGES, position_id="p1")
    tax = st.snapshot()["tax"]
    assert tax["turnover"] == pytest.approx(100.0)
    assert tax["gross_pnl"] == pytest.approx(100.0)
    assert tax["net_pnl"] == pytest.approx(100.0 - ENTRY_CHARGES - EXIT_CHARGES)
    assert tax["charges"] == pytest.approx(ENTRY_CHARGES + EXIT_CHARGES)
    assert tax["closed_trades"] == 1


def test_gross_of_falls_back_to_net_for_a_row_written_before_the_column(st):
    assert state_mod._gross_of({"realized": -30.0}) == pytest.approx(-30.0)
    assert state_mod._gross_of({"realized": -50.0, "realized_gross": -30.0}) == pytest.approx(-30.0)
    assert state_mod._gross_of({}) == pytest.approx(0.0)


# ---- the journal restatement -------------------------------------------


def _legacy_journal(path):
    """A journal written the old way: realized is gross, charges sit unused."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE trades (id TEXT PRIMARY KEY, position_id TEXT, ts REAL NOT NULL, "
                 "symbol TEXT NOT NULL, side TEXT, quantity INTEGER, price REAL, mode TEXT, "
                 "reason TEXT, note TEXT, realized REAL, charges REAL, initial_risk REAL, "
                 "r_multiple REAL, checklist_json TEXT)")
    rows = [
        # the real BEL round trip: -30 gross, 12.47 + 8.20 of charges
        ("entry", "pos1", 1.0, "BEL", "SELL", 50, 389.65, "paper", None, None, 0.0, 12.47, None, None, None),
        ("exit", "pos1", 2.0, "BEL", "BUY", 50, 390.25, "paper", "stop_loss", None, -30.0, 8.20, 0.55, -1.09, None),
        # a position still open: one leg, no realized figure
        ("open", "pos2", 3.0, "INDHOTEL", "BUY", 45, 720.67, "paper", None, None, 0.0, 13.62, None, None, None),
    ]
    conn.executemany("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


def test_an_existing_journal_is_restated_net_and_keeps_the_gross_figure(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    _legacy_journal(path)
    monkeypatch.setattr(database, "DB_PATH", path)
    database._local.conn = None

    rows = {r["id"]: r for r in database.recent_trades(limit=10)}
    assert rows["exit"]["realized_gross"] == pytest.approx(-30.0)
    assert rows["exit"]["realized"] == pytest.approx(-30.0 - 12.47 - 8.20)
    # the R-multiple follows the net figure, so live R matches backtested R
    assert rows["exit"]["r_multiple"] == pytest.approx((-30.0 - 12.47 - 8.20) / (0.55 * 50))
    # an opening leg has no P&L to restate, and its charges are not lost:
    # they were deducted on the closing leg above
    assert rows["entry"]["realized"] == pytest.approx(0.0)
    assert rows["entry"]["charges"] == pytest.approx(12.47)
    # the still-open position is left completely alone
    assert rows["open"]["realized"] == pytest.approx(0.0)


def test_the_restatement_conserves_every_rupee_of_charges(tmp_path, monkeypatch):
    """Sum(gross) - Sum(net) must equal the charges column exactly: nothing
    double-counted, nothing dropped."""
    path = tmp_path / "legacy.db"
    _legacy_journal(path)
    monkeypatch.setattr(database, "DB_PATH", path)
    database._local.conn = None

    conn = database._conn()
    gross, net = conn.execute("SELECT SUM(realized_gross), SUM(realized) FROM trades").fetchone()
    # only closed positions can have their charges released; pos2 is still open
    closed_charges = conn.execute(
        "SELECT SUM(COALESCE(charges, 0)) FROM trades WHERE position_id = 'pos1'").fetchone()[0]
    assert gross - net == pytest.approx(closed_charges)


def test_the_restatement_runs_once_and_is_safe_to_reopen(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    _legacy_journal(path)
    monkeypatch.setattr(database, "DB_PATH", path)

    database._local.conn = None
    first = database._conn().execute("SELECT SUM(realized), SUM(realized_gross) FROM trades").fetchone()
    database._local.conn = None            # a second process opening the same journal
    second = database._conn().execute("SELECT SUM(realized), SUM(realized_gross) FROM trades").fetchone()
    assert tuple(first) == pytest.approx(tuple(second))


def test_a_fresh_journal_needs_no_restatement(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "fresh.db")
    database._local.conn = None
    cols = {r[1] for r in database._conn().execute("PRAGMA table_info(trades)")}
    assert "realized_gross" in cols


# ---- the whole path, through the engine --------------------------------


def test_a_real_round_trip_through_the_engine_is_journalled_net():
    """The wiring, not just apply_fill: engine._execute -> paper broker ->
    record_trade -> the journal row the dashboard and Scorecard read."""
    import trading_engine
    st = AppState(watchlist=[], paper_mode=True)
    engine = trading_engine.TradingEngine(st)
    engine._execute("NETTEST", "BUY", 10, 100.0, reason="test", position_id="rt1")
    engine._execute("NETTEST", "SELL", 10, 110.0, reason="take_profit",
                    position_id="rt1", initial_risk=2.0)

    rows = {r["side"]: r for r in database.recent_trades(limit=10)}
    entry, exit_ = rows["BUY"], rows["SELL"]
    charges = (entry["charges"] or 0) + (exit_["charges"] or 0)
    assert charges > 0, "the fixture would prove nothing with charges switched off"
    assert exit_["realized"] == pytest.approx(exit_["realized_gross"] - charges)
    assert exit_["realized"] < exit_["realized_gross"]
    assert exit_["r_multiple"] == pytest.approx(exit_["realized"] / (2.0 * 10))
    # what the header and the daily loss limit read
    assert st.realized_pnl_today == pytest.approx(exit_["realized"])
    assert engine.risk.daily_realized_pnl == pytest.approx(exit_["realized"])
