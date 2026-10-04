"""
Risk manager — enforces position sizing and loss limits before any order
(paper or live) is allowed through.

Position sizing is Van Tharp's **Percent Risk Model** (*Trade Your Way to
Financial Freedom*, ch 9, Model 3): risk a fixed % of capital per trade,
divided by the stop distance. The stop distance itself follows his **Percent
Volatility Model** (ch 9, Model 4) when ATR is available — sized off each
symbol's own volatility instead of a flat percentage — or a structural stop
(the pattern's own low/high) when the caller supplies one.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("trading_bot")


MODES = ("paper", "live")


class RiskManager:
    """The daily loss limit counts paper and live money separately (#252).
    One pooled counter let a morning's paper profit cancel out an afternoon's
    real-money loss, and paper losses refuse a switch to Live for a limit real
    money never reached. `mode_fn` returns "paper" or "live": the mode a call
    without an explicit `mode` is about. The engine sets it to follow its own
    Paper/Live switch; without one (the backtester) everything is "paper"."""

    def __init__(self, risk_config: dict, mode_fn=None):
        self.cfg = risk_config
        self.daily_realized = {m: 0.0 for m in MODES}
        self.open_positions_count = 0
        self.mode_fn = mode_fn

    def _mode(self, mode=None) -> str:
        mode = mode or (self.mode_fn() if self.mode_fn else "paper")
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}")
        return mode

    @property
    def daily_realized_pnl(self) -> float:
        """Today's realized P&L, net of charges, in the current mode."""
        return self.daily_realized[self._mode()]

    @daily_realized_pnl.setter
    def daily_realized_pnl(self, value: float):
        self.daily_realized[self._mode()] = value

    def reset_day(self):
        self.daily_realized = {m: 0.0 for m in MODES}
        self.open_positions_count = 0

    def record_realized_pnl(self, pnl: float, mode=None):
        self.daily_realized[self._mode(mode)] += pnl

    def daily_loss_limit_hit(self, mode=None) -> bool:
        limit = -abs(self.cfg["total_capital"] * self.cfg["max_daily_loss_pct"] / 100)
        return self.daily_realized[self._mode(mode)] <= limit

    def _stop_distance(self, entry_price: float, atr: float | None) -> float:
        if self.cfg.get("use_atr_risk") and atr:
            return atr * self.cfg.get("atr_sl_multiplier", 1.5)
        return entry_price * self.cfg["stop_loss_pct"] / 100

    def _target_distance(self, entry_price: float, atr: float | None) -> float:
        if self.cfg.get("use_atr_risk") and atr:
            return atr * self.cfg.get("atr_tp_multiplier", 3.0)
        return entry_price * self.cfg["take_profit_pct"] / 100

    def position_size(self, entry_price: float, atr: float | None = None, stop_price: float | None = None,
                      size_factor: float = 1.0) -> int:
        """Percentage-risk sizing (Varsity Risk Management ch 14): risk amount / stop distance.
        A structural stop (e.g. the candlestick pattern's low) is used when given.

        `size_factor` covers every reduction applied to a full position — the
        checklist's reduced size for a missing indicator, and the high-VIX
        multiplier. It belongs here rather than at the call site because the
        share count must be rounded exactly once (issue #28): callers used to
        round the full size to whole shares and then multiply, so 60% of a
        3-share cap became int(1.8) = 1 share, a third of the cap rather than
        the intended 60%, and a 1-share cap became 0 and blocked the trade.

        Rounding is still downward at the end. Rounding to the nearest share
        would let a reduced position come out *larger* than the risk and
        notional caps allow, which is the wrong direction for a rule whose
        whole job is to be a ceiling.
        """
        risk_amount = self.cfg["total_capital"] * self.cfg["max_risk_per_trade_pct"] / 100
        stop_distance = abs(entry_price - stop_price) if stop_price else self._stop_distance(entry_price, atr)
        if stop_distance <= 0:
            return 0
        qty = risk_amount / stop_distance
        # Tight intraday ATR stops otherwise imply several times the account in notional.
        cap_pct = self.cfg.get("max_position_notional_pct")
        if cap_pct and entry_price > 0:
            qty = min(qty, self.cfg["total_capital"] * cap_pct / 100 / entry_price)
        return max(int(qty * size_factor), 0)

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
