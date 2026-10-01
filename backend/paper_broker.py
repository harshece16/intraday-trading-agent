"""
Paper trading execution — updates positions/trade log in AppState without
sending any real order. This is the default execution path.
"""

from state import AppState


def execute_paper_order(state: AppState, symbol: str, side: str, quantity: int, price: float,
                        reason=None, note=None, charges=None, checklist_snapshot=None,
                        position_id=None, initial_risk=None, signal_price=None, confidence=None) -> dict:
    """Returns apply_fill()'s {"gross", "charges_deducted", "net"} for this fill."""
    fill = state.apply_fill(symbol, side, quantity, price, charges=charges or 0.0)
    r_multiple = (fill["net"] / (initial_risk * quantity)) if initial_risk and quantity else None
    state.record_trade(symbol, side, quantity, price, mode="paper", reason=reason, note=note,
                       realized=fill["net"], realized_gross=fill["gross"], charges=charges,
                       position_id=position_id, initial_risk=initial_risk, r_multiple=r_multiple,
                       checklist_snapshot=checklist_snapshot, signal_price=signal_price,
                       confidence=confidence)
    return fill
