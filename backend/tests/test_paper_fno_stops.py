"""#154: a paper F&O position is repriced each tick (Black-Scholes at the entry
IV on the live underlying spot), so its stop, target and square-off price move
with the underlying instead of staying at the entry premium."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import config
import costs
import data_provider
import fno_risk
import options_pricing
import trading_engine
from state import AppState

STRIKE, LOT, DAYS, VOL = 1000.0, 50, 20, 0.20
R = config.FNO["risk_free_rate_pct"] / 100


def _model(spot, is_call=True):
    return round(options_pricing.price(spot, STRIKE, DAYS / 365, VOL, R, is_call), 2)


def _engine(monkeypatch, spot, paper=True, is_call=True):
    e = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=paper))
    entry = _model(1000.0, is_call)
    exits = fno_risk.stop_and_target_premium(entry, config.FNO["stop_loss_pct_of_premium"],
                                             config.FNO["target_pct_of_premium"])
    expiry = (datetime.now(trading_engine.IST).date() + timedelta(days=DAYS)).isoformat()
    e.state.fno_positions["ACME"] = {
        "tradingsymbol": "ACME26OCT1000CE", "underlying": "ACME", "is_call": is_call,
        "strike": STRIKE, "expiry": expiry, "entry_iv": VOL, "lots": 1, "lot_size": LOT,
        "entry_premium": entry, "ltp": entry, "position_id": "P-FNO-1",
        "entry_charges": costs.leg_cost("BUY", entry, LOT, costs.FNO_OPTION_COSTS), **exits,
    }
    e.risk.open_positions_count = 1
    box = {"spot": spot}

    def get_ltp(symbol):
        if box["spot"] is None:
            raise RuntimeError("no price")
        return box["spot"]

    monkeypatch.setattr(data_provider, "get_ltp", get_ltp)
    return e, entry, box


def _exit_trade(e):
    assert "ACME" not in e.state.fno_positions
    return e.state.trades[0]


def test_unchanged_spot_reprices_to_the_entry_premium_and_fires_nothing(monkeypatch):
    e, entry, _ = _engine(monkeypatch, 1000.0)
    assert e._check_fno_stop_take("ACME") is False
    assert e.state.fno_positions["ACME"]["ltp"] == entry


def test_paper_stop_fires_when_the_underlying_moves_against(monkeypatch):
    e, entry, _ = _engine(monkeypatch, 960.0)
    assert _model(960.0) <= e.state.fno_positions["ACME"]["stop_premium"]
    assert e._check_fno_stop_take("ACME") is True
    t = _exit_trade(e)
    assert t["reason"] == "fno_stop_loss"
    assert t["price"] == _model(960.0)
    assert t["realized"] < 0


def test_paper_put_stop_fires_when_the_underlying_rises(monkeypatch):
    e, entry, _ = _engine(monkeypatch, 1040.0, is_call=False)
    assert e._check_fno_stop_take("ACME") is True
    assert _exit_trade(e)["reason"] == "fno_stop_loss"


def test_paper_target_fires_when_the_underlying_moves_in_favour(monkeypatch):
    e, entry, _ = _engine(monkeypatch, 1040.0)
    assert _model(1040.0) >= e.state.fno_positions["ACME"]["target_premium"]
    assert e._check_fno_stop_take("ACME") is True
    t = _exit_trade(e)
    assert t["reason"] == "fno_take_profit"
    assert t["price"] == _model(1040.0)
    assert t["realized"] > 0


def test_square_off_books_at_the_repriced_premium_net_of_charges(monkeypatch):
    e, entry, _ = _engine(monkeypatch, 1010.0)
    pos = dict(e.state.fno_positions["ACME"])
    e._close_fno("ACME", "fno_auto_square_off")
    t = _exit_trade(e)
    px = _model(1010.0)
    assert px != entry and t["price"] == px
    gross = (px - entry) * LOT
    assert t["realized_gross"] == pytest.approx(gross)
    assert t["realized"] == pytest.approx(
        gross - pos["entry_charges"] - costs.leg_cost("SELL", px, LOT, costs.FNO_OPTION_COSTS))
    assert not t["note"]


def test_unreadable_spot_fires_nothing_and_logs_once(monkeypatch):
    e, entry, box = _engine(monkeypatch, None)
    assert e._check_fno_stop_take("ACME") is False
    assert e._check_fno_stop_take("ACME") is False
    assert e.state.fno_positions["ACME"]["ltp"] == entry
    assert not e.state.trades
    assert len([a for a in e.state.activity if "can't reprice" in a["message"]]) == 1


def test_square_off_without_a_spot_uses_the_last_repriced_premium(monkeypatch):
    e, entry, box = _engine(monkeypatch, 1010.0)
    assert e._check_fno_stop_take("ACME") is False
    box["spot"] = None
    e._close_fno("ACME", "fno_auto_square_off")
    t = _exit_trade(e)
    assert t["price"] == _model(1010.0) != entry
    assert "last repriced premium" in t["note"]


def test_live_mode_still_uses_kites_premium(monkeypatch):
    e, entry, box = _engine(monkeypatch, 960.0, paper=False)   # the model would say "stop"

    class Kite:
        orders = []

        def get_fno_ltp(self, sym):
            return entry * 2

        def place_fno_order(self, *a):
            self.orders.append(a)
            return "ord1"

        def wait_for_fill(self, order_id):
            return {"status": "COMPLETE", "filled_quantity": LOT, "average_price": entry * 2 - 0.5, "message": ""}

        def get_positions(self):       # a live close reads the day book first (#250)
            return [{"tradingsymbol": p["tradingsymbol"], "quantity": p["lots"] * p["lot_size"]}
                    for p in e.state.fno_positions.values()]

    monkeypatch.setattr(e, "_ensure_kite", lambda: Kite())
    assert e._check_fno_stop_take("ACME") is True
    t = _exit_trade(e)
    # Kite's quote fires the target; the exit is booked at Kite's executed premium (#186)
    assert t["reason"] == "fno_take_profit" and t["price"] == entry * 2 - 0.5
    assert (t["signal_price"], t["order_id"], t["mode"]) == (entry * 2, "ord1", "live")
    assert Kite.orders and Kite.orders[0][1] == "SELL"
