"""
Risk management for the F&O side — options-BUYING only (long calls, long
puts). Writing/selling options and trading futures are deliberately out of
scope, not an oversight:

  - NISM Series VIII is explicit that a long option's maximum loss is the
    premium paid, full stop — a known, capped number before the trade is
    even placed. A short (written) option's maximum loss, by the same
    textbook's own account, "has to be unlimited" for a short call, and is
    very large (strike x lot size, minus premium received) for a short
    put. That is a fundamentally different risk shape from everything else
    this codebase does, which is sized to a known, bounded loss per trade
    (RISK["max_risk_per_trade_pct"] for cash equity; this module's
    "max_premium_risk_pct" here).
  - Futures carry margin-based leverage and mark-to-margin calls that can
    exceed the capital put up, which the same bounded-risk discipline
    doesn't cover either.

So: every F&O position this module sizes is a bought option, whose entire
possible loss is decided at entry (the premium paid for the lots bought),
never discovered later via a margin call.
"""

import math


def lots_to_buy(capital: float, max_premium_risk_pct: float, premium: float, lot_size: int) -> int:
    """How many lots of this option to buy: cap the total premium spent
    (= the trade's entire max loss) at max_premium_risk_pct of the F&O
    capital allocation, same "decide the max loss before you place the
    trade" discipline as the cash-equity Percent Risk Model."""
    if premium <= 0 or lot_size <= 0:
        return 0
    budget = capital * max_premium_risk_pct / 100
    lots = math.floor(budget / (premium * lot_size))
    return max(lots, 0)


def stop_and_target_premium(entry_premium: float, stop_pct: float, target_pct: float) -> dict:
    """Premium-based exits (NISM's own framing for an option buyer: profit
    or loss is realized in premium terms, not the underlying's price) —
    exit if the premium held falls `stop_pct`% or rises `target_pct`%."""
    return {
        "stop_premium": round(entry_premium * (1 - stop_pct / 100), 2),
        "target_premium": round(entry_premium * (1 + target_pct / 100), 2),
    }


def max_loss(premium: float, lots: int, lot_size: int) -> float:
    """The one number that matters before placing the order: the entire
    amount this trade can lose, no matter what the underlying does."""
    return round(premium * lots * lot_size, 2)


def mwpl_block_reason(underlying: str, ban, today_iso: str, index_underlyings=()):
    """Why a new option BUY on `underlying` must not be placed under NSE's
    Market Wide Position Limit ban, or None if it may.

    `ban` is nse_feed.fno_ban_list()'s value: {"trade_date", "symbols"} or
    None. The check FAILS CLOSED: an unfetchable list, or one published for
    a different trade date, blocks stock options, because the penalty for
    increasing a position in a banned stock is real money and "we could not
    check" is not evidence that it is clear. Index options are exempt; the
    ban applies to single-stock derivatives only."""
    if underlying in set(index_underlyings):
        return None
    if ban is None:
        return "F&O ban list (MWPL) could not be fetched — ban status unknown"
    if ban.get("trade_date") != today_iso:
        return f"F&O ban list is for {ban.get('trade_date')}, not today ({today_iso}) — ban status unknown"
    if underlying.upper() in ban.get("symbols", set()):
        return "in NSE's F&O ban period (market-wide OI above 95% of MWPL) — new positions are penalised"
    return None
