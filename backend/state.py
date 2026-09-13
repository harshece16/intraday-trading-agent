"""
Shared in-memory state for the dashboard. A single process holds this;
the background trading loop and scanner write to it, the API/WebSocket layer
reads it. Not persisted across restarts.
"""

import threading
import time
import uuid

ACTIVITY_LIMIT = 300


class AppState:
    def __init__(self, watchlist, paper_mode: bool):
        self.lock = threading.RLock()
        self.paper_mode = paper_mode
        self.running = False
        self.market_status = "unknown"  # "open" | "closed" | "unknown"

        self.watchlist = []
        self.candles = {}          # symbol -> recent candle window
        self.strategy_state = {}   # symbol -> last strategy state, for edge-triggered signals
        self.indicators = {}       # symbol -> latest analysis snapshot, for display
        # symbol -> {"quantity": int, "avg_price": float, "entry_atr": float|None}
        self.positions = {}
        self.set_watchlist(watchlist)

        self.market = None         # market context from the latest scan
        self.scanner = None        # full latest scan result
        self.activity = []         # agent activity log, newest first

        self.trades = []           # trade blotter, newest first
        self.signals_log = []      # recent raw signals, newest first
        self.realized_pnl_today = 0.0
        self.last_update_ts = None
        self.last_error = None

    def set_watchlist(self, symbols):
        with self.lock:
            self.watchlist = list(symbols)
            for s in self.watchlist:
                self.candles.setdefault(s, [])
                self.strategy_state.setdefault(s, None)
                self.indicators.setdefault(s, {})
                self.positions.setdefault(s, {"quantity": 0, "avg_price": 0.0, "entry_atr": None})

    def log(self, kind, message, symbol=None, level="info"):
        with self.lock:
            self.activity.insert(0, {
                "ts": time.time(), "kind": kind, "symbol": symbol, "message": message, "level": level,
            })
            del self.activity[ACTIVITY_LIMIT:]

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
                "market": self.market,
                "scanner": self.scanner,
                "activity": self.activity[:80],
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
            pos = self.positions.setdefault(symbol, {"quantity": 0, "avg_price": 0.0, "entry_atr": None})
            signed_qty = quantity if side == "BUY" else -quantity
            new_qty = pos["quantity"] + signed_qty
            realized = 0.0

            if pos["quantity"] == 0 or (pos["quantity"] > 0) == (signed_qty > 0):
                total_cost = pos["avg_price"] * pos["quantity"] + price * signed_qty
                pos["avg_price"] = total_cost / new_qty if new_qty != 0 else 0.0
            else:
                closed_qty = min(abs(signed_qty), abs(pos["quantity"]))
                realized = (price - pos["avg_price"]) * closed_qty * (1 if pos["quantity"] > 0 else -1)
                self.realized_pnl_today += realized
                if new_qty == 0:
                    pos["avg_price"] = 0.0
                    pos["entry_atr"] = None

            pos["quantity"] = new_qty
            return realized

    def record_trade(self, symbol, side, quantity, price, mode, reason=None, note=None):
        with self.lock:
            self.trades.insert(0, {
                "id": str(uuid.uuid4())[:8],
                "symbol": symbol, "side": side, "quantity": quantity,
                "price": price, "mode": mode, "ts": time.time(),
                "reason": reason, "note": note,
            })

    def record_signal(self, symbol, signal, detail=None):
        with self.lock:
            self.signals_log.insert(0, {
                "symbol": symbol, "signal": signal, "detail": detail, "ts": time.time(),
            })
            del self.signals_log[100:]
