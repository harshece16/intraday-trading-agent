"""
Risk manager — enforces position sizing and loss limits before any order
(paper or live) is allowed through.

Stop/target distance is ATR-based when `use_atr_risk` is set and an ATR
value is supplied (adapts to each symbol's actual volatility); otherwise it
falls back to the fixed `stop_loss_pct` / `take_profit_pct`.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("trading_bot")


class RiskManager:
    def __init__(self, risk_config: dict):
        self.cfg = risk_config
        self.daily_realized_pnl = 0.0
        self.open_positions_count = 0

    def reset_day(self):
        self.daily_realized_pnl = 0.0
        self.open_positions_count = 0

    def record_realized_pnl(self, pnl: float):
        self.daily_realized_pnl += pnl

    def daily_loss_limit_hit(self) -> bool:
        limit = -abs(self.cfg["total_capital"] * self.cfg["max_daily_loss_pct"] / 100)
        return self.daily_realized_pnl <= limit

    def _stop_distance(self, entry_price: float, atr: float | None) -> float:
        if self.cfg.get("use_atr_risk") and atr:
            return atr * self.cfg.get("atr_sl_multiplier", 1.5)
        return entry_price * self.cfg["stop_loss_pct"] / 100

    def _target_distance(self, entry_price: float, atr: float | None) -> float:
        if self.cfg.get("use_atr_risk") and atr:
            return atr * self.cfg.get("atr_tp_multiplier", 3.0)
        return entry_price * self.cfg["take_profit_pct"] / 100

    def position_size(self, entry_price: float, atr: float | None = None) -> int:
        risk_amount = self.cfg["total_capital"] * self.cfg["max_risk_per_trade_pct"] / 100
        stop_distance = self._stop_distance(entry_price, atr)
        if stop_distance <= 0:
            return 0
        qty = int(risk_amount / stop_distance)
        # Tight intraday ATR stops otherwise imply several times the account in notional.
        cap_pct = self.cfg.get("max_position_notional_pct")
        if cap_pct and entry_price > 0:
            qty = min(qty, int(self.cfg["total_capital"] * cap_pct / 100 / entry_price))
        return max(qty, 0)

    def stop_loss_price(self, entry_price: float, side: str, atr: float | None = None) -> float:
        d = self._stop_distance(entry_price, atr)
        return entry_price - d if side == "BUY" else entry_price + d

    def take_profit_price(self, entry_price: float, side: str, atr: float | None = None) -> float:
        d = self._target_distance(entry_price, atr)
        return entry_price + d if side == "BUY" else entry_price - d

    def can_open_new_position(self) -> bool:
        if self.daily_loss_limit_hit():
            return False
        if self.open_positions_count >= self.cfg["max_open_positions"]:
            return False
        return True
