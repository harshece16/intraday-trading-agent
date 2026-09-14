"""
Day Plan — turns the risk model's own formulas into concrete numbers for a
capital amount you're actually planning to trade with, and separately shows
what literally happened today measured against those same rules.

This deliberately does NOT predict a return, an end-of-day P&L, or whether
today will be a "good day" — there's no honest, backtested edge to base that
on yet (see the Dimaag Scorecard: the live Information Coefficient is
currently negative, expectancy hasn't cleared the bar). Predicting a rupee
outcome would be fabricating a number this system has no right to state.

What IS real and computable, so that's what this shows instead:
  - the risk model's own boundaries at a given capital — max ₹ risk per
    trade, max ₹ daily loss, and the actual share/lot size each current
    watchlist pick would get — plain arithmetic (risk_manager.py), not a
    forecast;
  - what really happened today — actual fills from the journal, actual
    realized P&L, whether the day stayed inside those same boundaries —
    historical fact, checked against a rule, never a target "achieved" or
    "missed" against an invented number.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import config
import database
from risk_manager import RiskManager

IST = ZoneInfo("Asia/Kolkata")


def pick_rows(scanner_result, premarket_result):
    """Real, currently-ranked candidates to size the plan against — the live
    intraday scanner's active picks if it's run today, else the pre-market
    shortlist (which is all that can exist before the market opens)."""
    today = datetime.now(IST).date().isoformat()
    if scanner_result and scanner_result.get("session_date") == today:
        return [r for r in scanner_result["rows"] if r.get("status") == "ACTIVE"], "today's live intraday scan"
    if premarket_result:
        return [r for r in premarket_result["rows"] if r.get("status") == "WATCHLIST"], "pre-market ranking (live scan hasn't run yet today)"
    return [], None


def plan(capital: float, rows: list) -> dict:
    cfg = {**config.RISK, "total_capital": capital}
    risk = RiskManager(cfg)
    max_risk_per_trade = capital * cfg["max_risk_per_trade_pct"] / 100
    max_daily_loss = capital * cfg["max_daily_loss_pct"] / 100

    candidates = []
    for r in rows:
        ltp = r.get("ltp") or r.get("close")
        atr_pct, side = r.get("atr_pct"), r.get("side")
        if not ltp or not atr_pct or side not in ("LONG", "SHORT"):
            continue
        atr = ltp * atr_pct / 100
        bside = "BUY" if side == "LONG" else "SELL"
        qty = risk.position_size(ltp, atr=atr)
        stop = risk.stop_loss_price(ltp, bside, atr=atr)
        target = risk.take_profit_price(ltp, bside, atr=atr)
        stop_distance = abs(ltp - stop)
        target_distance = abs(target - ltp)
        candidates.append({
            "symbol": r["symbol"], "side": side, "ltp": round(ltp, 2), "atr_pct": atr_pct,
            "qty": qty, "tradable": qty > 0,
            "stop_price": round(stop, 2), "target_price": round(target, 2),
            "risk_rupees": round(qty * stop_distance, 2), "reward_rupees": round(qty * target_distance, 2),
            "rrr": round(target_distance / stop_distance, 2) if stop_distance else None,
            "notional": round(qty * ltp, 2),
        })

    total_risk = sum(c["risk_rupees"] for c in candidates if c["tradable"])
    tradable_count = sum(1 for c in candidates if c["tradable"])
    return {
        "capital": capital,
        "max_risk_per_trade_pct": cfg["max_risk_per_trade_pct"],
        "max_risk_per_trade_rupees": round(max_risk_per_trade, 2),
        "max_daily_loss_pct": cfg["max_daily_loss_pct"],
        "max_daily_loss_rupees": round(max_daily_loss, 2),
        "max_open_positions": cfg["max_open_positions"],
        "candidates": candidates,
        "tradable_count": tradable_count,
        "total_risk_if_all_filled_rupees": round(total_risk, 2),
        "exceeds_daily_loss_cap": total_risk > max_daily_loss,
    }


def outcome(capital_used_today: float) -> dict:
    now = datetime.now(IST)
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=IST).timestamp()
    trades = database.trades_between(start_of_day)
    realized = sum(t["realized"] for t in trades if t.get("realized") is not None)
    closed = [t for t in trades if t.get("r_multiple") is not None]
    wins = [t for t in closed if t["r_multiple"] > 0]
    max_daily_loss = abs(capital_used_today) * config.RISK["max_daily_loss_pct"] / 100
    return {
        "date": now.date().isoformat(),
        "capital_used_today": capital_used_today,
        "trades": trades,
        "trade_count": len(trades),
        "closed_count": len(closed),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 1) if closed else None,
        "realized_pnl": round(realized, 2),
        "max_daily_loss_rupees": round(max_daily_loss, 2),
        "hit_daily_loss_limit": realized <= -max_daily_loss if max_daily_loss else False,
    }
