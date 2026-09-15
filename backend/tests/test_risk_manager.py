"""
Regression coverage for the money-moving math a multi-expert review flagged
as having zero automated tests: position sizing, stop/target pricing, and
the daily-loss circuit breaker. These are pure functions of a plain config
dict, so no mocking is needed — a future edit that silently breaks real-money
sizing now has something to catch it before it reaches a live order.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from risk_manager import RiskManager


def make_cfg(**overrides):
    cfg = {
        "max_risk_per_trade_pct": 1.0,
        "stop_loss_pct": 0.8,
        "take_profit_pct": 1.6,
        "max_open_positions": 3,
        "max_position_notional_pct": 33.0,
        "max_daily_loss_pct": 2.0,
        "total_capital": 100000.0,
        "use_atr_risk": True,
        "atr_sl_multiplier": 1.5,
        "atr_tp_multiplier": 3.0,
    }
    cfg.update(overrides)
    return cfg


def test_position_size_van_tharp_formula():
    # risk_amount = 100000 * 1% = 1000; stop_distance = ATR(20) * 1.5 = 30 -> qty = 33
    risk = RiskManager(make_cfg())
    qty = risk.position_size(entry_price=500, atr=20)
    assert qty == 33


def test_position_size_respects_notional_cap():
    # A huge account with a tiny stop would otherwise size to far more than
    # the account is worth — max_position_notional_pct must cap it.
    risk = RiskManager(make_cfg(total_capital=100000.0, max_position_notional_pct=33.0))
    qty = risk.position_size(entry_price=100, atr=0.5)  # tiny stop -> huge naive qty
    notional = qty * 100
    assert notional <= 100000.0 * 0.33 + 1e-6  # +eps for float rounding


def test_position_size_zero_when_no_stop_distance():
    risk = RiskManager(make_cfg(use_atr_risk=False, stop_loss_pct=0.0))
    assert risk.position_size(entry_price=500, atr=None) == 0


def test_position_size_uses_structural_stop_when_given():
    risk = RiskManager(make_cfg())
    # explicit stop_price overrides the ATR-derived stop distance
    qty_atr = risk.position_size(entry_price=500, atr=20)
    qty_structural = risk.position_size(entry_price=500, atr=20, stop_price=490)
    assert qty_structural != qty_atr
    # risk_amount(1000) / |500-490| = 100, but the 33% notional cap at this
    # price/capital (100000*0.33/500 = 66) binds first — both real Van Tharp
    # math AND the notional-cap safeguard have to agree for this to hold.
    assert qty_structural == 66


def test_stop_and_target_price_direction():
    risk = RiskManager(make_cfg())
    long_stop = risk.stop_loss_price(entry_price=500, side="BUY", atr=20)
    long_target = risk.take_profit_price(entry_price=500, side="BUY", atr=20)
    short_stop = risk.stop_loss_price(entry_price=500, side="SELL", atr=20)
    short_target = risk.take_profit_price(entry_price=500, side="SELL", atr=20)
    assert long_stop < 500 < long_target
    assert short_target < 500 < short_stop


def test_daily_loss_limit_hit():
    risk = RiskManager(make_cfg(total_capital=100000.0, max_daily_loss_pct=2.0))
    assert not risk.daily_loss_limit_hit()
    risk.record_realized_pnl(-1500)
    assert not risk.daily_loss_limit_hit()  # -1500 > -2000 limit
    risk.record_realized_pnl(-600)
    assert risk.daily_loss_limit_hit()  # -2100 <= -2000 limit


def test_can_open_new_position_respects_both_gates():
    risk = RiskManager(make_cfg(max_open_positions=2))
    assert risk.can_open_new_position()
    risk.open_positions_count = 2
    assert not risk.can_open_new_position()
    risk.open_positions_count = 0
    risk.record_realized_pnl(-100000)  # blow well past the daily loss limit
    assert not risk.can_open_new_position()
