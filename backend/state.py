"""
Shared in-memory state for the dashboard. A single process holds this;
the background trading loop writes to it, the API/WebSocket layer reads it.
Not persisted across restarts — add a database if you need history to
survive a restart.
"""

import threading
import time
import uuid


class AppState:
    def __init__(self, watchlist, paper_mode: bool):
        self.lock = threading.Lock()
        self.watchlist = watchlist
        self.paper_mode = paper_mode
        self.running = False
        self.market_status = "unknown"  # "open" | "closed" | "unknown"

        # symbol -> list of candle dicts (most recent window kept in memory)
        self.candles = {s: [] for s in watchlist}
        # symbol -> last strategy state (e.g. moving averages) for signal detection
        self.strategy_state = {s: None for s in watchlist}
        # symbol -> latest computed indicator snapshot, for display
        self.indicators = {s: {} for s in watchlist}

        # symbol -> {"quantity": int, "avg_price": float, "entry_atr": float|None}
        self.positions = {s: {"quantity": 0, "avg_price": 0.0, "entry_atr": None} for s in watchlist}

        self.trades = []          # trade blotter, newest first
        self.signals_log = []     # recent raw signals, newest first
        self.realized_pnl_today = 0.0
        self.last_update_ts = None
        self.last_error = None

    def snapshot(self):
        """Return a plain-dict snapshot safe to JSON-serialize for the API/WebSocket."""
        with self.lock:
            unrealized = 0.0
            positions_out = {}
            for sym, pos in self.positions.items():
                ltp = self.indicators.get(sym, {}).get("ltp")
                pnl = None
                if pos["quantity"] != 0 and ltp is not None:
                    pnl = (ltp - pos["avg_price"]) * pos["quantity"]
                    unrealized += pnl
                positions_out[sym] = {**pos, "ltp": ltp, "unrealized_pnl": pnl}

            return {
                "paper_mode": self.paper_mode,
                "running": self.running,
                "market_status": self.market_status,
                "watchlist": self.watchlist,
                "indicators": self.indicators,
                "positions": positions_out,
                "trades": self.trades[:50],
                "signals_log": self.signals_log[:30],
                "realized_pnl_today": self.realized_pnl_today,
                "unrealized_pnl": unrealized,
                "last_update_ts": self.last_update_ts,
                "last_error": self.last_error,
            }

    def apply_fill(self, symbol, side, quantity, price) -> float:
        """
        Update positions + realized P&L for an order fill. Used by both the
        paper broker and the live (Kite) path, so position/P&L bookkeeping
        stays correct regardless of mode — this is also what stop-loss /
        take-profit checks and the daily loss limit read from.
        Returns realized P&L for this fill (0.0 if just opening/adding).
        """
        with self.lock:
            pos = self.positions[symbol]
            signed_qty = quantity if side == "BUY" else -quantity
            new_qty = pos["quantity"] + signed_qty
            realized = 0.0

            if pos["quantity"] == 0 or (pos["quantity"] > 0) == (signed_qty > 0):
                # adding to (or opening) a position — blend the average price
                total_cost = pos["avg_price"] * pos["quantity"] + price * signed_qty
                pos["avg_price"] = total_cost / new_qty if new_qty != 0 else 0.0
            else:
                # reducing or flipping a position — realize P&L on the closed portion
                closed_qty = min(abs(signed_qty), abs(pos["quantity"]))
                realized = (price - pos["avg_price"]) * closed_qty * (1 if pos["quantity"] > 0 else -1)
                self.realized_pnl_today += realized
                if new_qty == 0:
                    pos["avg_price"] = 0.0
                    pos["entry_atr"] = None

            pos["quantity"] = new_qty
            return realized

    def record_trade(self, symbol, side, quantity, price, mode):
        with self.lock:
            self.trades.insert(0, {
                "id": str(uuid.uuid4())[:8],
                "symbol": symbol, "side": side, "quantity": quantity,
                "price": price, "mode": mode, "ts": time.time(),
            })

    def record_signal(self, symbol, signal, detail=None):
        with self.lock:
            self.signals_log.insert(0, {
                "symbol": symbol, "signal": signal, "detail": detail, "ts": time.time(),
            })
