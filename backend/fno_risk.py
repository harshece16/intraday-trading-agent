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


def mwpl_block_reason(underlying: str, ban, today_iso: str, index_underlyings=(), unknown_why: str = ""):
    """Why a new option BUY on `underlying` must not be placed under NSE's
    Market Wide Position Limit ban, or None if it may.

    `ban` is nse_feed.fno_ban_list()'s value, the same list the scanner's
    ban guard reads: {"trade_date": "YYYY-MM-DD", "symbols": set} or None.
    `unknown_why`, when the list is None, is why it could not be read
    (nse_feed.failure_text), so the reason says when the last try failed.

    None means the ban status is UNKNOWN, as it does for the scanner, and so
    does a list published for another trade date. The scanner lets an unknown
    list exclude nothing, because trading a stock's shares in its ban period is
    not penalised. Increasing a position in its derivatives is (NISM Series
    VIII: ₹5,000 to ₹1,00,000), so here an unknown status blocks stock
    options, and the reason says the status is unknown rather than that the
    stock is banned. Index options are exempt: the ban covers single-stock
    derivatives only, and index derivatives are never on the list."""
    if underlying.upper() in {u.upper() for u in index_underlyings}:
        return None
    if ban is None:
        why = f" ({unknown_why})" if unknown_why else ""
        return f"NSE's F&O ban list could not be read{why}, so the ban status is unknown; no stock option is bought"
    if ban.get("trade_date") != today_iso:
        return (f"NSE's F&O ban list is for {ban.get('trade_date')}, not today ({today_iso}), "
                "so the ban status is unknown; no stock option is bought")
    if underlying.upper() in ban.get("symbols", set()):
        return (f"In NSE's F&O ban for {today_iso}: market-wide positions are above 95% of the limit, "
                "and a new position is penalised")
    return None
