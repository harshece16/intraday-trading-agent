"""
Paper trading execution — updates positions/trade log in AppState without
sending any real order. This is the default execution path.
"""

from state import AppState


def execute_paper_order(state: AppState, symbol: str, side: str, quantity: int, price: float,
                        reason=None, note=None, charges=None, checklist_snapshot=None,
                        position_id=None, initial_risk=None, signal_price=None, confidence=None,
                        on_fill=None) -> dict:
    """Returns apply_fill()'s {"gross", "charges_deducted", "net"} for this fill.
    `on_fill(fill)` runs right after the position is updated and before the
    journal write, so the caller's bookkeeping can't be skipped by a journal
    error (#253)."""
    fill = state.apply_fill(symbol, side, quantity, price, charges=charges or 0.0, mode="paper")
    if on_fill is not None:
        on_fill(fill)
    r_multiple = (fill["net"] / (initial_risk * quantity)) if initial_risk and quantity else None
    state.record_trade(symbol, side, quantity, price, mode="paper", reason=reason, note=note,
                       realized=fill["net"], realized_gross=fill["gross"], charges=charges,
                       position_id=position_id, initial_risk=initial_risk, r_multiple=r_multiple,
                       checklist_snapshot=checklist_snapshot, signal_price=signal_price,
                       confidence=confidence)
    return fill
