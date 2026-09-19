"""
Watch Kite's tick stream and act on a breached stop the moment it happens.

Without this, stops are only checked inside the 30-second poll
(trading_engine._check_stop_take, called from _process_symbol), so a stop can
be through and unnoticed for up to 30 seconds. Measured against the real
5-minute ATR that is worth about Rs 12 on a Rs 33,000 position at the worst
case — a third of what the whole round trip costs in charges — and it lands on
every losing trade, which is where this strategy's expectancy currently lives.

Three things keep this safe to run beside a live engine:

* It only ever CLOSES a position. There is no path from here to an entry, a
  size change or an order for a symbol not already held.
* The 30-second poll keeps checking stops exactly as before. This is an
  accelerator, not a replacement — if the socket dies, drops, or was never
  connected, behaviour falls back to what it was.
* Closing goes through engine._exit_position(), which claims the symbol first,
  so the poll and this thread can never both send a closing order.

It needs a live Kite session for the market data, but not live trading: a
paper-mode run with a valid Kite token gets real-time stops too.
"""
import logging
import threading
import time

import config
import data_provider

logger = logging.getLogger("trading_bot")

# Kite drops the connection if nothing is subscribed, and reconnects on its
# own; this is only about how long we tolerate silence before saying so.
TICK_SILENCE_WARN_SECONDS = 120


class StopWatcher:
    def __init__(self, engine, ticker_factory=None):
        self.engine = engine
        self.state = engine.state
        # Injectable so the decision path can be tested without a socket.
        self._ticker_factory = ticker_factory or _kite_ticker
        self._ticker = None
        self._lock = threading.Lock()
        self._tokens = {}            # instrument_token -> symbol
        self._subscribed = set()     # instrument_tokens currently subscribed
        self._connected = False
        self._started = False
        self._last_tick_at = None
        self._counts = {"ticks": 0, "exits": 0, "errors": 0}

    # ---- lifecycle ------------------------------------------------------

    def available(self) -> bool:
        """A live Kite session is needed for the feed, whatever the trading mode."""
        return bool(config.KITE_API_KEY and config.KITE_ACCESS_TOKEN) and data_provider.kite_data_active()

    def start(self):
        """Idempotent. Does nothing, quietly, when Kite isn't connected — the
        poll is still checking stops, so there is nothing to warn about."""
        if self._started or not self.available():
            return
        try:
            self._ticker = self._ticker_factory(config.KITE_API_KEY, config.KITE_ACCESS_TOKEN)
        except Exception:
            logger.exception("Stop watcher: could not build the Kite ticker")
            return
        self._ticker.on_ticks = self._on_ticks
        self._ticker.on_connect = self._on_connect
        self._ticker.on_close = self._on_close
        self._ticker.on_error = self._on_error
        try:
            self._ticker.connect(threaded=True, disable_ssl_verification=False)
        except Exception:
            logger.exception("Stop watcher: could not open the tick stream")
            self._ticker = None
            return
        self._started = True
        self.state.log("system", "Stop watcher connected to the Kite tick stream — "
                                 "stops are now checked on every tick, not every 30 s")

    def stop(self):
        self._started = False
        self._connected = False
        ticker, self._ticker = self._ticker, None
        if ticker is not None:
            try:
                ticker.close()
            except Exception:
                logger.exception("Stop watcher: error closing the tick stream")

    # ---- subscriptions --------------------------------------------------

    def sync(self):
        """Match the subscription list to the symbols actually held. Called
        once per engine tick, so a position opened this cycle is being watched
        within a second of the order going in."""
        if not self._started:
            self.start()
            if not self._started:
                return
        with self.state.lock:
            held = [s for s, p in self.state.positions.items() if p.get("quantity")]
        wanted = {}
        for symbol in held:
            try:
                wanted[data_provider._instrument_token(symbol)] = symbol
            except Exception:
                # A symbol with no Kite instrument row simply keeps the
                # 30-second poll as its only stop check.
                logger.debug("Stop watcher: no instrument token for %s", symbol)
        with self._lock:
            self._tokens = wanted
            add = set(wanted) - self._subscribed
            drop = self._subscribed - set(wanted)
            self._subscribed = set(wanted)
        if not self._connected:
            return          # on_connect subscribes to whatever is current
        self._apply(add, drop)

    def _apply(self, add, drop):
        ticker = self._ticker
        if ticker is None:
            return
        try:
            if drop:
                ticker.unsubscribe(list(drop))
            if add:
                ticker.subscribe(list(add))
                # LTP mode: the last traded price is all a stop needs, and it
                # is the smallest packet Kite sends.
                ticker.set_mode(ticker.MODE_LTP, list(add))
        except Exception:
            logger.exception("Stop watcher: subscription update failed")

    # ---- callbacks ------------------------------------------------------

    def _on_connect(self, ws, response):
        self._connected = True
        with self._lock:
            tokens = list(self._subscribed)
        if tokens:
            self._apply(set(tokens), set())

    def _on_close(self, ws, code, reason):
        self._connected = False
        logger.warning("Stop watcher: tick stream closed (%s %s) — the 30 s poll still covers stops", code, reason)

    def _on_error(self, ws, code, reason):
        self._counts["errors"] += 1
        logger.warning("Stop watcher: tick stream error (%s %s)", code, reason)

    def _on_ticks(self, ws, ticks):
        """Runs on the ticker's own thread. Must never raise: an exception here
        kills the stream and silently takes the fast stop path with it."""
        self._last_tick_at = time.time()
        for tick in ticks or []:
            try:
                symbol = self._tokens.get(tick.get("instrument_token"))
                price = tick.get("last_price")
                if not symbol or not price:
                    continue
                self._counts["ticks"] += 1
                if self.engine.check_stop_from_tick(symbol, float(price)):
                    self._counts["exits"] += 1
                    with self._lock:
                        token = tick.get("instrument_token")
                        self._subscribed.discard(token)
                        self._tokens.pop(token, None)
                    self._apply(set(), {tick.get("instrument_token")})
            except Exception:
                self._counts["errors"] += 1
                logger.exception("Stop watcher: failed handling a tick")

    # ---- status ---------------------------------------------------------

    def stats(self) -> dict:
        silent_for = (time.time() - self._last_tick_at) if self._last_tick_at else None
        return {
            "available": self.available(),
            "started": self._started,
            "connected": self._connected,
            "watching": sorted(self._tokens.values()),
            "ticks_seen": self._counts["ticks"],
            "exits_fired": self._counts["exits"],
            "errors": self._counts["errors"],
            "last_tick_ts": self._last_tick_at,
            "stale": bool(silent_for and silent_for > TICK_SILENCE_WARN_SECONDS and self._tokens),
            "note": ("Stops are checked on every tick." if self._connected else
                     "Not connected — stops fall back to the 30-second poll, exactly as before."),
        }


def _kite_ticker(api_key, access_token):
    from kiteconnect import KiteTicker
    return KiteTicker(api_key, access_token)
