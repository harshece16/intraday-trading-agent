"""#35: F&O P&L is net of real charges, on the same convention as equity:
each leg carries its own charges, and the exit's `realized` (which feeds the
daily loss limit, the journal and the F&O confidence IC) is net of both."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import costs
import database
import trading_engine
from state import AppState


def test_option_tariff_is_a_flat_rs20_and_premium_based():
    c = costs.FNO_OPTION_COSTS
    assert c["brokerage_flat"] == 20.0
    # a tiny premium still pays the full Rs 20 brokerage per order
    small = costs.leg_cost("BUY", 1.0, 10, c)
    assert small > 20.0
    # a Rs 5,460 premium round trip: 110.16 bp, as phase-3 scoping computed
    rt = costs.leg_cost("BUY", 84, 65, c) + costs.leg_cost("SELL", 84, 65, c)
    assert abs(rt / 5460 * 1e4 - 110.16) < 0.01


def test_equity_brokerage_is_unchanged_by_the_flat_option():
    import config
    assert "brokerage_flat" not in config.COSTS
    turnover = 10_000
    assert costs.leg_cost("BUY", 1000, 10, config.COSTS) > turnover * 0.03 / 100   # 0.03%, not Rs 20


def _engine_with_position(monkeypatch, entry=100.0, exit_=130.0, lots=1, lot_size=65):
    e = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    e.scanner = None
    qty = lots * lot_size
    entry_charges = costs.leg_cost("BUY", entry, qty, costs.FNO_OPTION_COSTS)
    e.state.fno_positions["NIFTY"] = {
        "tradingsymbol": "NIFTY26SEP23350CE", "underlying": "NIFTY", "lots": lots, "lot_size": lot_size,
        "entry_premium": entry, "position_id": "P-FNO-1", "ltp": exit_, "entry_charges": entry_charges,
    }
    monkeypatch.setattr(e, "_fno_ltp", lambda sym: exit_)
    exits = []
    monkeypatch.setattr(database, "record_fno_exit", lambda pid, ltp, reason, realized, r: exits.append((realized, r)))
    return e, qty, entry_charges, exits


def test_an_fno_exit_is_net_of_both_legs_charges(monkeypatch):
    e, qty, entry_charges, exits = _engine_with_position(monkeypatch)
    before = e.risk.daily_realized_pnl
    e._close_fno("NIFTY", "target")
    t = e.state.trades[0]
    gross = (130.0 - 100.0) * qty
    exit_charges = costs.leg_cost("SELL", 130.0, qty, costs.FNO_OPTION_COSTS)
    assert abs(t["realized_gross"] - gross) < 1e-9
    assert abs(t["charges"] - exit_charges) < 1e-9
    assert abs(t["realized"] - (gross - entry_charges - exit_charges)) < 1e-9
    # the daily loss limit and the F&O journal see NET, not gross
    assert abs((e.risk.daily_realized_pnl - before) - t["realized"]) < 1e-9
    assert abs(exits[0][0] - t["realized"]) < 1e-9
    assert t["r_multiple"] < gross / (100.0 * qty)       # r is net too


def test_a_missing_entry_charge_is_recomputed_not_treated_as_zero(monkeypatch):
    e, qty, entry_charges, _ = _engine_with_position(monkeypatch)
    e.state.fno_positions["NIFTY"].pop("entry_charges")
    e._close_fno("NIFTY", "stop")
    t = e.state.trades[0]
    assert abs((t["realized_gross"] - t["realized"]) - (entry_charges + t["charges"])) < 1e-9
