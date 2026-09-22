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
    # Intraday STT is sell-side only; delivery STT applies to both legs, so
    # stt_pct_buy / dp_charge_per_sell default to 0 and leave intraday
    # configs (config.COSTS) computing exactly what they always did.
    stt_pct = costs_cfg["stt_pct_sell"] if side == "SELL" else costs_cfg.get("stt_pct_buy", 0.0)
    stt = turnover * stt_pct / 100
    exchange_txn = turnover * costs_cfg["exchange_txn_pct"] / 100
    sebi = turnover * costs_cfg["sebi_charges_pct"] / 100
    stamp_duty = turnover * costs_cfg["stamp_duty_pct_buy"] / 100 if side == "BUY" else 0.0
    gst = (brokerage + exchange_txn) * costs_cfg["gst_pct"] / 100
    dp_charge = costs_cfg.get("dp_charge_per_sell", 0.0) if side == "SELL" else 0.0
    return brokerage + stt + exchange_txn + sebi + stamp_duty + gst + dp_charge



def round_trip_pct(notional: float, costs_cfg: dict) -> float:
    """A full round trip (entry + exit charges, plus slippage on both legs)
    as a % of `notional`, priced as one share at that value. This is the
    number the checklist's reward-to-risk gate deducts (trader_brain's
    cost_pct). Deriving it here keeps the gate and the P&L on the same cost
    model; a hardcoded 0.12 drifted 28% under the measured 16.60 bp (#74).

    With Zerodha's intraday tariff it is flat at every notional below the
    Rs 20 brokerage cap (~Rs 66,667), and only falls above it."""
    if notional <= 0:
        return 0.0
    charges = leg_cost("BUY", notional, 1, costs_cfg) + leg_cost("SELL", notional, 1, costs_cfg)
    slippage = 2 * notional * costs_cfg.get("slippage_pct", 0.0) / 100
    return (charges + slippage) / notional * 100

# Equity delivery (CNC) — for trades held past the day they were bought.
# Zerodha's published tariff as best known at time of writing: ₹0 brokerage,
# STT 0.1% on BOTH buy and sell (vs 0.025% sell-only intraday), stamp duty
# 0.015% on buy (vs 0.003% intraday), and a flat depository charge per scrip
# per sell day (₹13.5 + 18% GST). Verify against zerodha.com/charges before
# trusting results that depend on these — same caveat as config.COSTS.
DELIVERY_COSTS = {
    "brokerage_per_order": 0.0, "brokerage_pct": 0.0,
    "stt_pct_sell": 0.1, "stt_pct_buy": 0.1,
    "exchange_txn_pct": 0.00297, "sebi_charges_pct": 0.0001,
    "stamp_duty_pct_buy": 0.015, "gst_pct": 18.0,
    "slippage_pct": 0.03, "dp_charge_per_sell": 15.93,
}


ZERO_COSTS = {
    "brokerage_per_order": 0.0, "brokerage_pct": 0.0, "stt_pct_sell": 0.0,
    "exchange_txn_pct": 0.0, "sebi_charges_pct": 0.0, "stamp_duty_pct_buy": 0.0,
    "gst_pct": 0.0, "slippage_pct": 0.0,
}
