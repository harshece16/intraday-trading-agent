"""
Shared in-memory state for the dashboard. A single process holds this;
the background trading loop and scanner write to it, the API/WebSocket layer
reads it. Not persisted across restarts.
"""

import threading
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import config
import database

ACTIVITY_LIMIT = 300
IST = ZoneInfo("Asia/Kolkata")


def _new_position():
    return {"quantity": 0, "avg_price": 0.0, "entry_atr": None,
            "stop_price": None, "target_price": None, "initial_risk": None, "position_id": None}


class AppState:
    def __init__(self, watchlist, paper_mode: bool):
        self.lock = threading.RLock()
        self.paper_mode = paper_mode
        self.running = False
        self.market_status = "unknown"  # "open" | "closed" | "unknown"
        self.holiday = None  # {"name": str, "next_trading_day": "YYYY-MM-DD"} on an NSE holiday, else None
        self.next_open = None  # ISO datetime (IST) of the next session open, for the dashboard countdown

        self.watchlist = []
        self.candles = {}          # symbol -> recent candle window
        self.strategy_state = {}   # symbol -> last strategy state, for edge-triggered signals
        self.indicators = {}       # symbol -> latest analysis snapshot, for display
        # symbol -> {"quantity": int, "avg_price": float, "entry_atr": float|None}
        self.positions = {}
        # underlying NSE symbol -> one open long-option position (see fno_risk.py:
        # options-buying only, so "quantity" here is always > 0 — there is no short side).
        # {"tradingsymbol", "underlying", "is_call", "lots", "lot_size", "entry_premium",
        #  "stop_premium", "target_premium", "ltp", "unrealized_pnl", "confidence", "position_id"}
        self.fno_positions = {}
        self.set_watchlist(watchlist)

        self.market = None         # market context from the latest scan
        self.scanner = None        # full latest scan result
        self.activity = []         # agent activity log, newest first

        self.trades = []           # trade blotter, newest first
        self.signals_log = []      # recent raw signals, newest first
        self.realized_pnl_today = 0.0
        self.last_update_ts = None
        self.last_error = None
        # Set by trading_engine._sync_capital() whenever RISK['total_capital'] is
        # refreshed from the real Kite account — lets the dashboard show that the
        # risk model's capital figure is real money, not a stale config guess.
        self.capital_sync = None  # {"amount": float, "synced_at": epoch, "source": ..., "real_kite_balance": float} | None
        # Always the real Kite equity balance, regardless of mode — separate
        # from capital_sync["amount"]/risk_total_capital, which is whatever
        # RiskManager is actually sizing against right now (paper_capital in
        # paper mode, this same real number in live mode). Lets the dashboard
        # show "what going live would actually use" even mid-paper-session.
        self.real_capital = None
        # scanner.run_premarket()'s cached result — see trading_engine's
        # request_premarket_scan()/_run_premarket_scan(). Owned here (not a
        # module-level dict in app.py) so the engine itself can read it to seed
        # the day's watchlist before the live intraday scanner has run.
        self.premarket = {"result": None, "error": None, "running": False}
        self._rehydrate_today()

    def _rehydrate_today(self):
        """A restart during market hours used to silently drop today's real
        trades from the dashboard — self.trades/realized_pnl_today are
        in-memory-only fields, reset to empty on every __init__, even
        though database.record_trade() already logged them permanently.
        Found live: restarting to deploy a fix made an already-closed real
        trade (BEL, -30) vanish from the Trade Journal page, looking like
        it had never happened. Reload today's real fills from the journal
        so a restart doesn't erase the record of what actually happened."""
        start_of_day = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        try:
            todays_trades = database.trades_between(start_of_day)
        except Exception:
            return
        self.trades = list(reversed(todays_trades))  # newest first, matching record_trade()'s insert(0, ...)
        self.realized_pnl_today = sum(t["realized"] for t in self.trades if t.get("realized"))

    def set_watchlist(self, symbols):
        with self.lock:
            self.watchlist = list(symbols)
            for s in self.watchlist:
                self.candles.setdefault(s, [])
                self.strategy_state.setdefault(s, None)
                self.indicators.setdefault(s, {})
                self.positions.setdefault(s, _new_position())

    def log(self, kind, message, symbol=None, level="info"):
        ts = time.time()
        with self.lock:
            self.activity.insert(0, {"ts": ts, "kind": kind, "symbol": symbol, "message": message, "level": level})
            del self.activity[ACTIVITY_LIMIT:]
        database.record_activity(kind, message, symbol=symbol, level=level, ts=ts)

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
                "holiday": self.holiday,
                "next_open": self.next_open,
                "market_open": config.MARKET_OPEN,
                "market_close": config.MARKET_CLOSE,
                "server_ts": time.time(),
                "watchlist": self.watchlist,
                "indicators": self.indicators,
                "positions": positions_out,
                "fno_positions": self.fno_positions,
                "market": self.market,
                "scanner": self.scanner,
                "activity": self.activity[:80],
                "trades": self.trades[:50],
                "tax": self._tax_summary(),
                "signals_log": self.signals_log[:30],
                "realized_pnl_today": self.realized_pnl_today,
                "unrealized_pnl": unrealized,
                "last_update_ts": self.last_update_ts,
                "last_error": self.last_error,
                "risk_total_capital": config.RISK["total_capital"],
                "real_capital": self.real_capital,
                "capital_sync": self.capital_sync,
                "kite_connected": bool(config.KITE_ACCESS_TOKEN),
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
            pos = self.positions.setdefault(symbol, _new_position())
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
                    pos.update(_new_position())

            pos["quantity"] = new_qty
            return realized

    def record_trade(self, symbol, side, quantity, price, mode, reason=None, note=None, realized=None,
                     charges=None, position_id=None, initial_risk=None, r_multiple=None, checklist_snapshot=None):
        trade = {
            "id": str(uuid.uuid4())[:8], "position_id": position_id,
            "symbol": symbol, "side": side, "quantity": quantity,
            "price": price, "mode": mode, "ts": time.time(),
            "reason": reason, "note": note, "realized": realized, "charges": charges,
            "initial_risk": initial_risk, "r_multiple": r_multiple,
        }
        with self.lock:
            self.trades.insert(0, trade)
        database.record_trade(trade, checklist_snapshot=checklist_snapshot)

    def _tax_summary(self):
        """Intraday equity is speculative business income (Varsity Markets & Taxation ch 3-6).
        Trade-wise turnover is the sum of the absolute profit or loss of each closed trade."""
        closed = [t for t in self.trades if t.get("realized")]
        return {
            "turnover": sum(abs(t["realized"]) for t in closed),
            "net_pnl": sum(t["realized"] for t in closed),
            "charges": sum(t.get("charges") or 0 for t in self.trades),
            "closed_trades": len(closed),
        }

    def record_signal(self, symbol, signal, detail=None):
        ts = time.time()
        with self.lock:
            self.signals_log.insert(0, {"symbol": symbol, "signal": signal, "detail": detail, "ts": ts})
            del self.signals_log[100:]
        database.record_signal(symbol, signal, detail=detail, ts=ts)
