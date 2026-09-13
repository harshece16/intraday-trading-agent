"""
Realistic per-order transaction cost + slippage modeling for intraday
equity (MIS) trades, based on config.COSTS. See that dict for the specific
rates and their source/caveats.
"""


def apply_slippage(side: str, price: float, costs_cfg: dict) -> float:
    """Return the price you'd realistically fill at, not the price the
    signal fired at. A market BUY fills a little higher, a market SELL a
    little lower."""
    slip = costs_cfg.get("slippage_pct", 0.0) / 100
    return price * (1 + slip) if side == "BUY" else price * (1 - slip)


def leg_cost(side: str, price: float, qty: int, costs_cfg: dict) -> float:
    """Total brokerage + statutory charges for one executed order (one leg
    of a trade — the entry or the exit)."""
    turnover = price * qty
    brokerage = min(costs_cfg["brokerage_per_order"], turnover * costs_cfg["brokerage_pct"] / 100)
    stt = turnover * costs_cfg["stt_pct_sell"] / 100 if side == "SELL" else 0.0
    exchange_txn = turnover * costs_cfg["exchange_txn_pct"] / 100
    sebi = turnover * costs_cfg["sebi_charges_pct"] / 100
    stamp_duty = turnover * costs_cfg["stamp_duty_pct_buy"] / 100 if side == "BUY" else 0.0
    gst = (brokerage + exchange_txn) * costs_cfg["gst_pct"] / 100
    return brokerage + stt + exchange_txn + sebi + stamp_duty + gst


ZERO_COSTS = {
    "brokerage_per_order": 0.0, "brokerage_pct": 0.0, "stt_pct_sell": 0.0,
    "exchange_txn_pct": 0.0, "sebi_charges_pct": 0.0, "stamp_duty_pct_buy": 0.0,
    "gst_pct": 0.0, "slippage_pct": 0.0,
}
