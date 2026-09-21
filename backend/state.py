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
import data_provider
import database

ACTIVITY_LIMIT = 300
IST = ZoneInfo("Asia/Kolkata")


def _gross_of(trade):
    """A trade's P&L before charges. Falls back to the net figure for any row
    written before issue #21 added the column and never backfilled."""
    gross = trade.get("realized_gross")
    return gross if gross is not None else (trade.get("realized") or 0.0)


def _new_position():
    # "charges" holds the brokerage + statutory charges already paid to open
    # this position. They're released against the realized figure when it
    # closes, so a round trip's P&L is net of both legs (issue #21).
    return {"quantity": 0, "avg_price": 0.0, "entry_atr": None,
            "stop_price": None, "target_price": None, "initial_risk": None, "position_id": None,
            "charges": 0.0}


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
        # Read outside self.lock: it touches only config and module state, and
        # the snapshot lock guards this object's own fields.
        kite = data_provider.kite_session_status()
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
                "kite_connected": kite["connected"],
                # Carried in the snapshot (which the WebSocket pushes every 3s)
                # so any page can say *why* Kite isn't usable without polling
                # /api/kite/status of its own.
                "kite_state": kite["state"],
                "kite_reason": kite["reason"],
                "kite_expires_at": kite["expires_at"],
                # Which URL Zerodha redirects back to. Only actionable when
                # something is wrong, but the page that shows it is the page
                # you land on when it is.
                "kite_redirect_url": kite["redirect_url"],
                "kite_login_stalled": kite["login_stalled"],
            }

    def apply_fill(self, symbol, side, quantity, price, charges=0.0) -> dict:
        """
        Update positions + realized P&L for an order fill. Used by both the
        paper broker and the live (Kite) path, so position/P&L bookkeeping
        stays correct regardless of mode — this is also what stop-loss /
        take-profit checks and the daily loss limit read from.

        `charges` is this leg's brokerage + statutory charges (costs.leg_cost).
        Slippage is already inside `price`, but until issue #21 these charges
        were only filed beside the trade and never taken off the P&L, so every
        realized figure the app reported — the header, the trade journal, the
        2% daily loss limit, the Scorecard's R-multiples — was gross. The
        opening leg's charges now ride on the position and are released when
        it closes, so the closing fill reports what the account actually
        gained or lost.

        Returns {"gross", "charges_deducted", "net"} for this fill — all 0.0
        when the fill only opens or adds to a position.
        """
        with self.lock:
            pos = self.positions.setdefault(symbol, _new_position())
            signed_qty = quantity if side == "BUY" else -quantity
            new_qty = pos["quantity"] + signed_qty
            gross = 0.0
            deducted = 0.0

            if pos["quantity"] == 0 or (pos["quantity"] > 0) == (signed_qty > 0):
                total_cost = pos["avg_price"] * pos["quantity"] + price * signed_qty
                pos["avg_price"] = total_cost / new_qty if new_qty != 0 else 0.0
                pos["charges"] = pos.get("charges", 0.0) + (charges or 0.0)
            else:
                open_qty = abs(pos["quantity"])
                closed_qty = min(abs(signed_qty), open_qty)
                gross = (price - pos["avg_price"]) * closed_qty * (1 if pos["quantity"] > 0 else -1)
                # only the share of the opening charges that belongs to the
                # quantity being closed, so a partial exit isn't charged twice.
                entry_share = pos.get("charges", 0.0) * closed_qty / open_qty if open_qty else 0.0
                pos["charges"] = pos.get("charges", 0.0) - entry_share
                deducted = entry_share + (charges or 0.0)
                self.realized_pnl_today += gross - deducted
                if new_qty == 0:
                    pos.update(_new_position())

            pos["quantity"] = new_qty
            return {"gross": gross, "charges_deducted": deducted, "net": gross - deducted}

    def record_trade(self, symbol, side, quantity, price, mode, reason=None, note=None, realized=None,
                     charges=None, position_id=None, initial_risk=None, r_multiple=None, checklist_snapshot=None,
                     realized_gross=None):
        """`realized` is net of both legs' charges; `realized_gross` is the same
        figure before them, and `charges` stays this one leg's own charges, so
        summing the column over every row still gives the day's total (#21)."""
        trade = {
            "id": str(uuid.uuid4())[:8], "position_id": position_id,
            "symbol": symbol, "side": side, "quantity": quantity,
            "price": price, "mode": mode, "ts": time.time(),
            "reason": reason, "note": note, "realized": realized,
            "realized_gross": realized_gross, "charges": charges,
            "initial_risk": initial_risk, "r_multiple": r_multiple,
        }
        with self.lock:
            self.trades.insert(0, trade)
        database.record_trade(trade, checklist_snapshot=checklist_snapshot)

    def _tax_summary(self):
        """Intraday equity is speculative business income (Varsity Markets & Taxation ch 3-6).
        Trade-wise turnover is the sum of the absolute profit or loss of each closed
        trade, taken *before* expenses — brokerage and statutory charges are a
        business expense claimed separately, not netted off turnover. So turnover
        reads gross while net_pnl reads net (issue #21)."""
        closed = [t for t in self.trades if t.get("realized")]
        return {
            "turnover": sum(abs(_gross_of(t)) for t in closed),
            "net_pnl": sum(t["realized"] for t in closed),
            "gross_pnl": sum(_gross_of(t) for t in closed),
            "charges": sum(t.get("charges") or 0 for t in self.trades),
            "closed_trades": len(closed),
        }

    def record_signal(self, symbol, signal, detail=None):
        ts = time.time()
        with self.lock:
            self.signals_log.insert(0, {"symbol": symbol, "signal": signal, "detail": detail, "ts": ts})
            del self.signals_log[100:]
        database.record_signal(symbol, signal, detail=detail, ts=ts)
