"""#157: an option buy checked only the pause, the daily loss limit, the
open-position cap and the confidence gate. It now also passes the cash
entry rules that make sense for an option on the underlying: one entry per
stock per day (shared with cash), the market bias (a call is a LONG, a put
a SHORT), the scanner's exclusion and side, the sector cap (cash and
options counted together), an untracked Kite position in the stock or in
any contract on it, and a spread-and-depth check on the contract's own book.
It acts on the edge-triggered signal, not on long_ok/short_ok every tick."""
from datetime import datetime

import pytest

import config
import database
import fno_risk
import liquidity
import trading_engine
from state import _new_position
from tests.fno_kit import analysis, book, engine, evaluations


def _enter(e, underlying="ACME", side="LONG"):
    return e._try_enter_fno(underlying, side, analysis())


def _blocked_reasons(e):
    return [a["message"] for a in e.state.activity if a["kind"] == "blocked"]


def test_a_clean_signal_buys_the_option_and_spends_the_days_entry(monkeypatch):
    e = engine(monkeypatch)
    assert _enter(e) is True
    pos = e.state.fno_positions["ACME"]
    assert pos["tradingsymbol"] == "ACME26OCT1000CE" and pos["live"] is False and pos["lots"] >= 1
    assert e.state.strategy_state["ACME"]["entries_today"] == 1
    assert e.risk.open_positions_count == 1
    assert evaluations()[-1]["executed"] == 1
    [check] = database.recent_liquidity_checks(limit=5)
    assert (check["symbol"], check["status"], check["ok"]) == ("ACME26OCT1000CE", "checked", 1)


def test_one_entry_per_stock_per_day_counts_an_earlier_option_trade(monkeypatch):
    e = engine(monkeypatch)
    assert _enter(e) is True
    e._close_fno("ACME", "fno_take_profit")
    assert "ACME" not in e.state.fno_positions
    assert _enter(e) is False
    assert "already traded today" in _blocked_reasons(e)[0]
    assert "already traded today" in evaluations()[-1]["block_reason"]


def test_one_entry_per_stock_per_day_counts_a_cash_entry_too(monkeypatch):
    e = engine(monkeypatch)
    today = datetime.now(trading_engine.IST).date().isoformat()
    e.state.strategy_state["ACME"] = {"entries_today": 1, "entry_day": today}
    assert _enter(e) is False and "ACME" not in e.state.fno_positions


def test_a_count_from_an_earlier_day_does_not_block(monkeypatch):
    e = engine(monkeypatch)
    e.state.strategy_state["ACME"] = {"entries_today": 1, "entry_day": "2020-01-01"}
    assert _enter(e) is True


@pytest.mark.parametrize("bias,side,blocked", [
    ("risk-off", "LONG", True), ("risk-off", "SHORT", False),
    ("risk-on", "SHORT", True), ("risk-on", "LONG", False),
])
def test_market_bias_blocks_calls_in_risk_off_and_puts_in_risk_on(monkeypatch, bias, side, blocked):
    e = engine(monkeypatch)
    e.state.market = {"bias": bias, "reasons": ["test"]}
    assert _enter(e, side=side) is (not blocked)
    if blocked:
        assert "market is " + bias in _blocked_reasons(e)[0]


def test_the_scanners_exclusion_and_side_apply_to_the_underlying(monkeypatch):
    e = engine(monkeypatch)
    e.state.scanner = {"rows": [{"symbol": "ACME", "excluded": "turnover below ₹50 cr"},
                                {"symbol": "BETA", "side": "SHORT"}], "active": []}
    assert _enter(e) is False and "turnover below" in _blocked_reasons(e)[0]
    assert _enter(e, "BETA", "LONG") is False and "scanner favours SHORT" in _blocked_reasons(e)[0]
    assert _enter(e, "BETA", "SHORT") is True


def _sector_scan(e):
    e.state.scanner = {"rows": [{"symbol": "ACME", "industry": "Widgets"},
                                {"symbol": "BETA", "industry": "Widgets"}], "active": []}


def test_the_sector_cap_counts_an_open_cash_position(monkeypatch):
    e = engine(monkeypatch)
    _sector_scan(e)
    e.state.positions["BETA"] = {**_new_position(), "quantity": 10, "avg_price": 100.0}
    assert _enter(e) is False and "in Widgets" in _blocked_reasons(e)[0]


def test_an_open_option_counts_against_the_sector_cap_for_cash_too(monkeypatch):
    e = engine(monkeypatch)
    _sector_scan(e)
    assert _enter(e) is True
    assert "in Widgets" in e._entry_block_reason("BETA", "LONG")
    assert _enter(e, "BETA") is False


def test_the_pause_blocks_an_option_buy(monkeypatch):
    e = engine(monkeypatch)
    e.state.entries_paused = True
    assert _enter(e) is False and "paused" in _blocked_reasons(e)[0]


def test_an_untracked_kite_position_in_the_stock_blocks(monkeypatch):
    e = engine(monkeypatch)
    e._untracked_kite_positions = {"ACME"}
    assert _enter(e) is False and "untracked" in _blocked_reasons(e)[0]


def test_an_untracked_kite_position_in_any_contract_on_the_stock_blocks(monkeypatch):
    e = engine(monkeypatch)
    e._untracked_kite_positions = {"ACME26NOV1100PE", "ACMEX26OCT500CE"}
    assert _enter(e) is False
    assert "ACME26NOV1100PE" in _blocked_reasons(e)[0] and "ACMEX" not in _blocked_reasons(e)[0]
    e._untracked_kite_positions = {"ACMEX26OCT500CE"}           # another stock's contract
    assert _enter(e) is True


def test_contract_on_needs_the_name_then_the_year():
    assert fno_risk.contract_on("NIFTY26OCT24500CE", "NIFTY")
    assert fno_risk.contract_on("NIFTY2610624500PE", "NIFTY")          # a weekly
    assert not fno_risk.contract_on("NIFTYNXT5026OCT70000CE", "NIFTY")
    assert not fno_risk.contract_on("BANKNIFTY26OCT51000CE", "NIFTY")
    assert fno_risk.contract_on("M&M26OCT3000CE", "M&M")
    assert not fno_risk.contract_on("M&MFIN26OCT300CE", "M&M")
    assert not fno_risk.contract_on("ACME", "ACME")                    # the stock itself


# ---- liquidity on the contract's book ----------------------------------------

def test_a_wide_option_spread_is_refused(monkeypatch):
    e = engine(monkeypatch, depth=book(19.0, 20.0))                   # 5.1% of the mid
    assert _enter(e) is False
    assert "liquidity: the option's spread is 5.13% of the premium" in _blocked_reasons(e)[0]
    assert "ACME" not in e.state.fno_positions
    assert e.state.strategy_state.get("ACME") is None                  # nothing was sent: not spent


def test_a_thin_option_book_is_refused(monkeypatch):
    e = engine(monkeypatch, depth=book(19.9, 20.1, qty=40))
    assert _enter(e) is False and "liquidity:" in _blocked_reasons(e)[0]


def test_paper_goes_ahead_without_a_book_and_live_does_not(monkeypatch):
    e = engine(monkeypatch, depth="none")
    assert _enter(e) is True
    from tests.fno_kit import FakeKite
    live = engine(monkeypatch, paper=False, kite=FakeKite(), depth="none")
    assert _enter(live, "BETA") is False
    assert "no market depth available" in _blocked_reasons(live)[0]


def test_assess_option_rules():
    cap, mult = config.FNO["max_spread_pct_of_premium"], 3.0
    ok = liquidity.assess_option(book(19.9, 20.1), 100, cap, mult)
    assert ok["ok"] is True and ok["spread_bp"] == 100.0
    assert "over the 2% cap" in liquidity.assess_option(book(19.0, 20.0), 100, cap, mult)["reason"]
    assert "hold only 50" in liquidity.assess_option(book(19.9, 20.1, qty=10), 100, cap, mult)["reason"]
    walk = liquidity.assess_option(book(19.95, 20.05, qty=30, step=0.5), 100, cap, mult)
    assert "walks the option's book" in walk["reason"]
    thin_exit = book(19.9, 20.1)
    for lv in thin_exit["buy"]:
        lv["quantity"] = 40                                           # 200 in the bids
    assert "exit side holds 200" in liquidity.assess_option(thin_exit, 100, cap, mult)["reason"]
    assert "empty" in liquidity.assess_option({"buy": [], "sell": []}, 100, cap, mult)["reason"]


# ---- edge-triggered -------------------------------------------------------------

def _active(e, monkeypatch, underlyings=("ACME",)):
    monkeypatch.setattr(e, "_fno_active", lambda: True)
    monkeypatch.setattr(e, "_fno_underlyings", lambda: list(underlyings))
    e.state.strategy_state["ACME"] = {**analysis(), "long_ok": True, "short_ok": False}


def test_a_standing_long_ok_without_a_signal_buys_nothing(monkeypatch):
    e = engine(monkeypatch)
    _active(e, monkeypatch)
    e._process_fno()
    assert e.state.fno_positions == {}


def test_the_signal_is_taken_once(monkeypatch):
    e = engine(monkeypatch)
    _active(e, monkeypatch)
    tries = []
    real = e._try_enter_fno
    monkeypatch.setattr(e, "_try_enter_fno", lambda *a: tries.append(a) or real(*a))
    e._fno_signals = {"ACME": "LONG"}
    e._process_fno()
    e._process_fno()                                                   # long_ok still True, no new edge
    assert len(tries) == 1 and "ACME" in e.state.fno_positions


def test_a_signal_on_a_stock_outside_the_fno_list_is_dropped(monkeypatch):
    e = engine(monkeypatch)
    _active(e, monkeypatch, underlyings=("BETA",))
    e._fno_signals = {"ACME": "LONG"}
    e._process_fno()
    assert e.state.fno_positions == {} and e._fno_signals == {}


def test_process_symbol_leaves_the_edge_for_the_option_path(monkeypatch):
    e = engine(monkeypatch)
    bars = [{"time": f"2026-09-30T10:{m:02d}:00+05:30", "open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.0, "volume": 1000} for m in (0, 5, 10)]
    e.state.set_watchlist(["ACME"])
    monkeypatch.setattr(e, "strategy_fn", lambda bars, prev_state=None, **k: ("BUY", {"bull_score": 1, "long_ok": True}))
    monkeypatch.setattr(e, "_try_enter", lambda *a, **k: False)
    e._process_symbol("ACME", candles=bars, now=datetime(2026, 9, 30, 11, 0, tzinfo=trading_engine.IST))
    assert e._fno_signals == {"ACME": "LONG"}
