"""
Paper trading execution — updates positions/trade log in AppState without
sending any real order. This is the default execution path.
"""

from state import AppState


def execute_paper_order(state: AppState, symbol: str, side: str, quantity: int, price: float,
                        reason=None, note=None, charges=None) -> float:
    realized = state.apply_fill(symbol, side, quantity, price)
    state.record_trade(symbol, side, quantity, price, mode="paper", reason=reason, note=note,
                       realized=realized, charges=charges)
    return realized
