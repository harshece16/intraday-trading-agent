"""
The trading engine — a background loop that, every POLL_INTERVAL_SECONDS:
  1. Checks whether the market is open (and whether it's time to auto
     square-off open positions before close).
  2. Refreshes intraday candles per watchlist symbol.
  3. Runs the configured strategy to get a signal.
  4. Applies risk sizing / limits.
  5. Executes via paper_broker (default) or KiteExecutor (live mode).
  6. Writes results into AppState for the API/WebSocket layer to serve.
"""

import asyncio
import logging
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import config
import data_provider
import news_sentiment
from strategy_engine import STRATEGY_FUNCTIONS, atr as compute_atr
from risk_manager import RiskManager
from paper_broker import execute_paper_order
from state import AppState

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
    if now.weekday() >= 5:  # Sat/Sun
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

    def _ensure_kite(self):
        if self.kite_executor is None:
            from kite_broker import KiteExecutor
            self.kite_executor = KiteExecutor(config.KITE_API_KEY, config.KITE_ACCESS_TOKEN)
        return self.kite_executor

    def reset_kite_executor(self):
        """Drop the cached executor so the next order rebuilds it with
        whatever access token config now holds — needed after the
        dashboard's in-app 'Connect Kite' flow updates the token without a
        process restart."""
        self.kite_executor = None

    def _square_off_all(self):
        for symbol in self.state.watchlist:
            pos = self.state.positions[symbol]
            if pos["quantity"] == 0:
                continue
            side = "SELL" if pos["quantity"] > 0 else "BUY"
            qty = abs(pos["quantity"])
            try:
                price = data_provider.get_ltp(symbol)
            except Exception:
                price = pos["avg_price"]
            self._execute(symbol, side, qty, price, reason="auto_square_off")
        self.risk.open_positions_count = 0

    def _execute(self, symbol, side, qty, price, reason=""):
        if self.state.paper_mode:
            realized = execute_paper_order(self.state, symbol, side, qty, price)
        else:
            executor = self._ensure_kite()
            executor.place_order(symbol, side, qty)
            # Mirror the fill into local state — this is what the dashboard,
            # the stop-loss/take-profit check, and the daily loss limit read
            # from, so live mode needs it updated exactly like paper mode.
            realized = self.state.apply_fill(symbol, side, qty, price)
            self.state.record_trade(symbol, side, qty, price, mode="live")
        if realized:
            self.risk.record_realized_pnl(realized)
        suffix = f" realized_pnl={realized:.2f}" if realized else ""
        logger.info(f"{reason or 'signal'}: {side} {qty} {symbol} @ {price:.2f}{suffix}")

    def _check_stop_take(self, symbol, ltp) -> bool:
        """Exit a position immediately if the latest price has crossed its
        stop-loss or take-profit level. Returns True if an exit fired."""
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
        self._execute(symbol, exit_side, abs(qty), ltp, reason="stop_loss" if hit_stop else "take_profit")
        self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)
        return True

    def tick(self):
        now = datetime.now(IST)
        if self._last_day != now.date():
            self.risk.reset_day()
            self.state.realized_pnl_today = 0.0
            self._last_day = now.date()

        phase = market_phase(now)
        self.state.market_status = "open" if phase in ("open", "square_off_window") else "closed"

        if phase == "closed":
            return

        if phase == "square_off_window":
            self._square_off_all()
            return

        for symbol in self.state.watchlist:
            try:
                candles = data_provider.get_intraday_candles(symbol, interval=config.CANDLE_INTERVAL, period="5d")
                if not candles:
                    continue

                with self.state.lock:
                    self.state.candles[symbol] = candles[-200:]  # keep a bounded window

                ltp = candles[-1]["close"]

                # Stop-loss / take-profit takes priority over new signals —
                # an open position must not wait for the next opposite
                # signal to exit a losing trade.
                if self._check_stop_take(symbol, ltp):
                    with self.state.lock:
                        self.state.indicators[symbol] = {
                            **(self.state.strategy_state[symbol] or {}), "ltp": ltp
                        }
                    continue

                params = dict(self.strategy_params)
                if getattr(self.strategy_fn, "uses_news", False) and params.get("use_news", True):
                    params["news"] = news_sentiment.get_sentiment(symbol)
                signal, new_state = self.strategy_fn(
                    candles, prev_state=self.state.strategy_state[symbol], **params
                )
                with self.state.lock:
                    self.state.strategy_state[symbol] = new_state
                    self.state.indicators[symbol] = {**(new_state or {}), "ltp": ltp}

                if signal:
                    self.state.record_signal(symbol, signal, new_state)

                if signal is None:
                    continue

                entry_price = ltp

                if signal == "BUY":
                    if self.state.positions[symbol]["quantity"] != 0:
                        continue
                    if not self.risk.can_open_new_position():
                        continue
                    atr_val = compute_atr(candles, config.RISK.get("atr_period", 14)) \
                        if config.RISK.get("use_atr_risk") else None
                    qty = self.risk.position_size(entry_price, atr=atr_val)
                    if qty <= 0:
                        continue
                    self._execute(symbol, "BUY", qty, entry_price)
                    with self.state.lock:
                        self.state.positions[symbol]["entry_atr"] = atr_val
                    self.risk.open_positions_count += 1

                elif signal == "SELL":
                    pos = self.state.positions[symbol]
                    if pos["quantity"] <= 0:
                        continue  # nothing to close
                    self._execute(symbol, "SELL", pos["quantity"], entry_price)
                    self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)

            except Exception as exc:
                logger.exception(f"Error processing {symbol}: {exc}")
                with self.state.lock:
                    self.state.last_error = f"{symbol}: {exc}"

        with self.state.lock:
            self.state.last_update_ts = now.timestamp()

    async def run_forever(self):
        self.state.running = True
        while self.state.running:
            await asyncio.get_event_loop().run_in_executor(None, self.tick)
            await asyncio.sleep(config.POLL_INTERVAL_SECONDS)
