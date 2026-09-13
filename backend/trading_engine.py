"""
The trading engine — a background loop that, every POLL_INTERVAL_SECONDS:
  1. Checks the market phase (open / square-off window / closed).
  2. Kicks off a market scan in a background thread when one is due — the
     scanner picks WHAT to trade and publishes market context (it also runs
     while the market is closed, so the dashboard always shows a plan).
  3. For each active-watchlist symbol: refreshes candles, enforces
     stop-loss / take-profit, runs the strategy to decide WHEN.
  4. Applies market filters and risk sizing, executes paper or live.
  5. Writes analysis, trades, and a plain-English activity log into AppState.
"""

import asyncio
import logging
import threading
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import config
import data_provider
import news_sentiment
from paper_broker import execute_paper_order
from risk_manager import RiskManager
from scanner import Scanner
from state import AppState
from strategy_engine import STRATEGY_FUNCTIONS, atr as compute_atr

logger = logging.getLogger("trading_bot")
IST = ZoneInfo("Asia/Kolkata")


def _parse_hhmm(s: str) -> dtime:
    h, m = map(int, s.split(":"))
    return dtime(h, m)


MARKET_OPEN_T = _parse_hhmm(config.MARKET_OPEN)
MARKET_CLOSE_T = _parse_hhmm(config.MARKET_CLOSE)
SQUARE_OFF_T = _parse_hhmm(config.SQUARE_OFF_TIME)


def market_phase(now=None) -> str:
    now = now or datetime.now(IST)
    if now.weekday() >= 5:
        return "closed"
    t = now.time()
    if t < MARKET_OPEN_T or t >= MARKET_CLOSE_T:
        return "closed"
    if t >= SQUARE_OFF_T:
        return "square_off_window"
    return "open"


class TradingEngine:
    def __init__(self, state: AppState):
        self.state = state
        self.risk = RiskManager(config.RISK)
        self.strategy_fn = STRATEGY_FUNCTIONS[config.STRATEGY]
        self.strategy_params = config.STRATEGY_PARAMS[config.STRATEGY]
        self.kite_executor = None
        self._last_day = None
        self.scanner = Scanner(config.SCANNER) if config.SCANNER.get("enabled") else None
        self._scan_thread = None
        self.size_multiplier = 1.0
        self._last_errors = {}

    def _ensure_kite(self):
        if self.kite_executor is None:
            from kite_broker import KiteExecutor
            self.kite_executor = KiteExecutor(config.KITE_API_KEY, config.KITE_ACCESS_TOKEN)
        return self.kite_executor

    def reset_kite_executor(self):
        """Drop the cached executor so the next order rebuilds it with
        whatever access token config now holds."""
        self.kite_executor = None

    # ---- scanning -------------------------------------------------------

    def request_scan(self) -> bool:
        if not self.scanner or (self._scan_thread and self._scan_thread.is_alive()):
            return False
        self._scan_thread = threading.Thread(target=self._run_scan, name="scanner", daemon=True)
        self._scan_thread.start()
        return True

    def _run_scan(self):
        self.state.log("scan", "Scanning the NIFTY 100 universe…")
        try:
            result = self.scanner.run()
        except Exception as exc:
            logger.exception("Scan failed")
            self.state.log("error", f"Scan failed: {exc}", level="error")
            return

        held = [s for s, p in self.state.positions.items() if p["quantity"] != 0]
        new_watch = list(dict.fromkeys(list(config.SCANNER.get("pinned", [])) + result["active"] + held))
        old_watch = list(self.state.watchlist)
        mkt = result["market"]
        with self.state.lock:
            self.state.market = mkt
            self.state.scanner = result
        self.state.set_watchlist(new_watch)
        self.size_multiplier = config.MARKET_FILTER["vix_high_size_multiplier"] if mkt.get("vix_high") else 1.0

        picks = ", ".join(result["active"]) or "nothing qualifies"
        self.state.log(
            "scan",
            f"Scanned {result['scanned']} stocks in {result['duration_s']:.0f}s · market {mkt['bias']} "
            f"({'; '.join(mkt['reasons'][:2])}) · {result['excluded_count']} filtered out · active: {picks}",
        )
        rows = {r["symbol"]: r for r in result["rows"]}
        for sym in new_watch:
            if sym in old_watch:
                continue
            row = rows.get(sym)
            if row:
                why = "; ".join(x["text"] for x in row["reasons"][:2])
                self.state.log("watchlist", f"Now tracking (score {row['final_score']:.0f}): {why}", symbol=sym)
            else:
                self.state.log("watchlist", "Now tracking (pinned or held position)", symbol=sym)
        dropped = [s for s in old_watch if s not in new_watch]
        if dropped:
            self.state.log("watchlist", f"Stopped tracking {', '.join(dropped)} — no longer among the top picks")
        if mkt.get("vix_high"):
            self.state.log("risk", f"India VIX {mkt['vix']:.1f} is elevated — new position sizes reduced", level="warn")

    def _scan_row(self, symbol):
        result = self.state.scanner
        if not result:
            return None
        return next((r for r in result["rows"] if r["symbol"] == symbol), None)

    # ---- execution ------------------------------------------------------

    def _execute(self, symbol, side, qty, price, reason="signal", note=None):
        if self.state.paper_mode:
            realized = execute_paper_order(self.state, symbol, side, qty, price, reason=reason, note=note)
        else:
            executor = self._ensure_kite()
            executor.place_order(symbol, side, qty)
            realized = self.state.apply_fill(symbol, side, qty, price)
            self.state.record_trade(symbol, side, qty, price, mode="live", reason=reason, note=note)
        if realized:
            self.risk.record_realized_pnl(realized)
        pnl = f" · P&L ₹{realized:,.0f}" if realized else ""
        logger.info(f"{reason}: {side} {qty} {symbol} @ {price:.2f}{pnl}")
        self.state.log("trade", f"{side} {qty} @ {price:.2f} ({reason}){pnl}" + (f" — {note}" if note else ""),
                       symbol=symbol, level="trade")
        return realized

    def _square_off_all(self):
        for symbol, pos in list(self.state.positions.items()):
            if pos["quantity"] == 0:
                continue
            side = "SELL" if pos["quantity"] > 0 else "BUY"
            try:
                price = data_provider.get_ltp(symbol)
            except Exception:
                price = pos["avg_price"]
            self._execute(symbol, side, abs(pos["quantity"]), price, reason="auto_square_off")
        self.risk.open_positions_count = 0

    def _check_stop_take(self, symbol, ltp) -> bool:
        pos = self.state.positions[symbol]
        qty = pos["quantity"]
        if qty == 0:
            return False
        side = "BUY" if qty > 0 else "SELL"
        atr_val = pos.get("entry_atr")
        stop = self.risk.stop_loss_price(pos["avg_price"], side, atr=atr_val)
        target = self.risk.take_profit_price(pos["avg_price"], side, atr=atr_val)
        hit_stop = (qty > 0 and ltp <= stop) or (qty < 0 and ltp >= stop)
        hit_target = (qty > 0 and ltp >= target) or (qty < 0 and ltp <= target)
        if not (hit_stop or hit_target):
            return False
        exit_side = "SELL" if qty > 0 else "BUY"
        self._execute(symbol, exit_side, abs(qty), ltp, reason="stop_loss" if hit_stop else "take_profit",
                      note=f"stop {stop:.2f} / target {target:.2f}")
        self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)
        return True

    def _blocked(self, symbol, setup, why):
        self.state.log("blocked", f"{setup} signal skipped — {why}", symbol=symbol, level="warn")

    def _close(self, symbol, ltp, reason, note=None):
        qty = self.state.positions[symbol]["quantity"]
        if qty == 0:
            return
        self._execute(symbol, "SELL" if qty > 0 else "BUY", abs(qty), ltp, reason=reason, note=note)
        self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)

    def _try_enter(self, symbol, side, ltp, candles, analysis):
        """side is "LONG" (buy) or "SHORT" (intraday MIS sell, squared off by 15:15)."""
        if self.state.positions[symbol]["quantity"] != 0:
            return
        setup = f"{analysis.get('setup', 'Entry')} ({side.lower()})"
        row = self._scan_row(symbol)
        mkt = self.state.market or {}
        reasons_txt = "; ".join(mkt.get("reasons", [])[:2])
        if row and row.get("excluded"):
            return self._blocked(symbol, setup, row["excluded"])
        if row and row.get("side") and row["side"] != side:
            return self._blocked(symbol, setup, f"scanner favours {row['side']} for this stock today")
        if side == "LONG" and mkt.get("bias") == "risk-off" and config.MARKET_FILTER["block_new_longs_when_risk_off"]:
            return self._blocked(symbol, setup, f"no new longs — market is risk-off ({reasons_txt})")
        if side == "SHORT" and mkt.get("bias") == "risk-on" and config.MARKET_FILTER.get("block_new_shorts_when_risk_on", True):
            return self._blocked(symbol, setup, f"no new shorts — market is risk-on ({reasons_txt})")
        if self.risk.daily_loss_limit_hit():
            return self._blocked(symbol, setup, "daily loss limit reached")
        if self.risk.open_positions_count >= config.RISK["max_open_positions"]:
            return self._blocked(symbol, setup, f"already at the max of {config.RISK['max_open_positions']} open positions")

        atr_val = compute_atr(candles, config.RISK.get("atr_period", 14)) if config.RISK.get("use_atr_risk") else None
        qty = int(self.risk.position_size(ltp, atr=atr_val) * self.size_multiplier)
        if qty <= 0:
            return self._blocked(symbol, setup, "position size rounds to 0 shares")

        key = "reasons" if side == "LONG" else "bear_reasons"
        why = "; ".join(r["text"] for r in analysis.get(key, [])[:3])
        note = f"bull {analysis['bull_score']:.1f} vs bear {analysis['bear_score']:.1f} — {why}" \
            if "bull_score" in analysis else None
        self._execute(symbol, "BUY" if side == "LONG" else "SELL", qty, ltp, reason=setup, note=note)
        with self.state.lock:
            self.state.positions[symbol]["entry_atr"] = atr_val
        self.risk.open_positions_count += 1

    def _note_forming_setup(self, symbol, prev, analysis):
        if not analysis or "bull_score" not in analysis or analysis.get("long_ok") or analysis.get("short_ok"):
            return
        near = analysis["entry_threshold"] - 1.5
        waiting = analysis["blockers"][0] if analysis.get("blockers") else "confirmation"
        for key, side in (("bull_score", "long"), ("bear_score", "short")):
            if side == "short" and not analysis.get("shorts_enabled", True):
                continue
            old = (prev or {}).get(key)
            if analysis[key] >= near and (old is None or old < near):
                self.state.log(
                    "setup",
                    f"{analysis['setup']} forming ({side}) — {key.split('_')[0]} {analysis[key]:.1f}/"
                    f"{analysis['entry_threshold']:g}; waiting on: {waiting}",
                    symbol=symbol,
                )

    def _process_symbol(self, symbol):
        candles = data_provider.get_intraday_candles(symbol, interval=config.CANDLE_INTERVAL, period="5d")
        if not candles:
            return
        with self.state.lock:
            self.state.candles[symbol] = candles[-200:]
        ltp = candles[-1]["close"]

        if self._check_stop_take(symbol, ltp):
            with self.state.lock:
                self.state.indicators[symbol] = {**(self.state.strategy_state.get(symbol) or {}), "ltp": ltp}
            return

        params = dict(self.strategy_params)
        if getattr(self.strategy_fn, "uses_news", False) and params.get("use_news", True):
            params["news"] = news_sentiment.get_sentiment(symbol)
        prev = self.state.strategy_state.get(symbol)
        signal, analysis = self.strategy_fn(candles, prev_state=prev, **params)
        with self.state.lock:
            self.state.strategy_state[symbol] = analysis
            self.state.indicators[symbol] = {**(analysis or {}), "ltp": ltp}

        self._note_forming_setup(symbol, prev, analysis)
        if signal:
            self.state.record_signal(symbol, signal, analysis)

        a = analysis or {}
        qty = self.state.positions[symbol]["quantity"]
        # Exits check the brain's exit condition every tick, not only its edge, so an
        # exit can't be missed when an entry signal for the other side fires on the same bar.
        if qty > 0 and (signal in ("SELL", "SHORT") or a.get("exit_long")):
            why = "; ".join(r["text"] for r in a.get("bear_reasons", [])[:2])
            self._close(symbol, ltp, "brain_exit", why or None)
        elif qty < 0 and (signal in ("BUY", "COVER") or a.get("exit_short")):
            why = "; ".join(r["text"] for r in a.get("reasons", [])[:2])
            self._close(symbol, ltp, "brain_cover", why or None)
        elif qty == 0 and signal in ("BUY", "SHORT"):
            self._try_enter(symbol, "LONG" if signal == "BUY" else "SHORT", ltp, candles, a)

    # ---- loop -----------------------------------------------------------

    def tick(self):
        now = datetime.now(IST)
        if self._last_day != now.date():
            self.risk.reset_day()
            self.state.realized_pnl_today = 0.0
            self._last_day = now.date()

        phase = market_phase(now)
        self.state.market_status = "open" if phase in ("open", "square_off_window") else "closed"

        if self.scanner and self.scanner.due(phase != "closed"):
            self.request_scan()

        if phase == "square_off_window":
            if any(p["quantity"] for p in self.state.positions.values()):
                self.state.log("risk", "Square-off time — closing all open positions", level="warn")
                self._square_off_all()
        elif phase == "open":
            for symbol in list(self.state.watchlist):
                try:
                    self._process_symbol(symbol)
                    self._last_errors.pop(symbol, None)
                except Exception as exc:
                    logger.exception(f"Error processing {symbol}: {exc}")
                    msg = str(exc)
                    with self.state.lock:
                        self.state.last_error = f"{symbol}: {msg}"
                    if self._last_errors.get(symbol) != msg:
                        self._last_errors[symbol] = msg
                        self.state.log("error", msg, symbol=symbol, level="error")

        with self.state.lock:
            self.state.last_update_ts = now.timestamp()

    async def run_forever(self):
        self.state.running = True
        self.state.log("system", f"Engine started in {'PAPER' if self.state.paper_mode else 'LIVE'} mode "
                                 f"· strategy {config.STRATEGY}")
        while self.state.running:
            await asyncio.get_event_loop().run_in_executor(None, self.tick)
            await asyncio.sleep(config.POLL_INTERVAL_SECONDS)
