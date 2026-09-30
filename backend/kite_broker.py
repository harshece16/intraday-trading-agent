"""
Live order execution via Zerodha Kite Connect. Only invoked when
state.paper_mode is False. Order placement is on Kite's free API tier —
market data for signals still comes from yfinance (data_provider.py), this
module is only used to actually send BUY/SELL orders and read positions.

Setup: run generate_access_token.py (see that file) to obtain today's
access token before going live — Kite sessions expire daily. You must also
whitelist a static IP on your Kite Connect developer dashboard before any
live order will be accepted — see the README's "Going live" section.
"""

import logging
import time

import config

logger = logging.getLogger("trading_bot")

# Kite's order statuses that will never change again. Anything else (OPEN,
# TRIGGER PENDING, the VALIDATION/PUT ORDER REQ steps) is still in flight.
ORDER_FINAL = ("COMPLETE", "REJECTED", "CANCELLED")
ORDER_UNKNOWN = "UNKNOWN"


class OrderNotFilled(Exception):
    """Kite confirmed that the order bought or sold nothing."""


class OrderUnconfirmed(Exception):
    """The order was sent, but Kite never told us how it ended."""

# Kite's own quote symbols for index spot prices — not a tradingsymbol,
# the exchange's literal quote key for the index itself.
INDEX_QUOTE_SYMBOLS = {"NIFTY": "NSE:NIFTY 50", "BANKNIFTY": "NSE:NIFTY BANK"}


class KiteExecutor:
    def __init__(self, api_key: str, access_token: str):
        from kiteconnect import KiteConnect
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)

    def place_order(self, symbol: str, side: str, quantity: int):
        from kiteconnect import KiteConnect
        order_id = self.kite.place_order(
            variety=KiteConnect.VARIETY_REGULAR,
            exchange=KiteConnect.EXCHANGE_NSE,
            tradingsymbol=symbol,
            transaction_type=side,
            quantity=quantity,
            product=KiteConnect.PRODUCT_MIS,  # intraday margin product
            order_type=KiteConnect.ORDER_TYPE_MARKET,
            # Required since SEBI's 2026-04-01 retail algo rules — a MARKET
            # order placed with market_protection unset (or 0) is rejected.
            # This caps how far from the last price the order can fill.
            market_protection=config.KITE_MARKET_PROTECTION_PCT,
        )
        logger.info(f"[LIVE] {side} {quantity} {symbol} -> order {order_id}")
        return order_id

    def order_state(self, order_id):
        """The order's latest state from Kite: {"status", "filled_quantity",
        "average_price", "message"}. Raises whatever Kite raises."""
        history = self.kite.order_history(order_id)
        if not history:
            return {"status": ORDER_UNKNOWN, "filled_quantity": 0, "average_price": 0.0, "message": "no order history"}
        last = history[-1]
        return {"status": last.get("status") or ORDER_UNKNOWN,
                "filled_quantity": int(last.get("filled_quantity") or 0),
                "average_price": float(last.get("average_price") or 0.0),
                "message": last.get("status_message") or ""}

    def wait_for_fill(self, order_id, deadline_s=None, poll_s=None, sleep=time.sleep):
        """Poll the order until Kite says it is finished, and return its state
        (see order_state). A MARKET order normally completes at once, but it
        carries a market-protection limit, so in a fast market it can sit
        partly filled. Past the deadline the rest is cancelled, so that what
        comes back is final and nothing can fill later behind the engine's
        back. Status UNKNOWN means Kite could not be read or the order would
        not cancel: the caller must not assume either a fill or no fill.
        Never raises."""
        deadline_s = config.KITE_FILL_DEADLINE_S if deadline_s is None else deadline_s
        poll_s = config.KITE_FILL_POLL_S if poll_s is None else poll_s
        unknown = {"status": ORDER_UNKNOWN, "filled_quantity": 0, "average_price": 0.0, "message": ""}

        def read_until(end):
            state = dict(unknown)
            while True:
                try:
                    state = self.order_state(order_id)
                except Exception as exc:
                    logger.warning(f"[LIVE] couldn't read order {order_id}: {exc}")
                    state = {**unknown, "message": str(exc)}
                if state["status"] in ORDER_FINAL or time.monotonic() >= end:
                    return state
                sleep(poll_s)

        state = read_until(time.monotonic() + deadline_s)
        if state["status"] in ORDER_FINAL:
            return state
        try:
            from kiteconnect import KiteConnect
            self.kite.cancel_order(variety=KiteConnect.VARIETY_REGULAR, order_id=order_id)
            logger.warning(f"[LIVE] order {order_id} was still {state['status']} after {deadline_s}s — cancelled the rest")
        except Exception as exc:
            # It may have completed in the meantime, which is fine: the read
            # below will say so.
            logger.warning(f"[LIVE] couldn't cancel order {order_id}: {exc}")
        state = read_until(time.monotonic() + deadline_s)
        return state if state["status"] in ORDER_FINAL else {**state, "status": ORDER_UNKNOWN}

    def get_positions(self):
        """Today's intraday (MIS) positions specifically — Kite's "day" book,
        not "net" (which also includes carried-forward CNC holdings, already
        shown separately via get_holdings()). Used to reconcile against
        state.positions after a restart, since this engine only ever trades
        intraday and squares off at config.SQUARE_OFF_TIME."""
        return self.kite.positions()["day"]

    def place_fno_order(self, tradingsymbol: str, side: str, lots: int, lot_size: int):
        """BUY-only (see fno_risk.py) NFO order — MIS product, same
        same-day-square-off discipline as the rest of this engine. `side`
        here is always "BUY" to open (long call/put) or "SELL" to close;
        there is no short-side entry."""
        from kiteconnect import KiteConnect
        order_id = self.kite.place_order(
            variety=KiteConnect.VARIETY_REGULAR,
            exchange=KiteConnect.EXCHANGE_NFO,
            tradingsymbol=tradingsymbol,
            transaction_type=side,
            quantity=lots * lot_size,
            product=KiteConnect.PRODUCT_MIS,
            order_type=KiteConnect.ORDER_TYPE_MARKET,
            market_protection=config.KITE_MARKET_PROTECTION_PCT,
        )
        logger.info(f"[LIVE F&O] {side} {lots} lot(s) {tradingsymbol} -> order {order_id}")
        return order_id

    def get_fno_ltp(self, tradingsymbol: str) -> float:
        quote = self.kite.ltp(f"NFO:{tradingsymbol}")
        return quote[f"NFO:{tradingsymbol}"]["last_price"]

    def get_quotes(self, tradingsymbols: list) -> dict:
        """Bulk real quote (price + open interest) for a list of NFO
        tradingsymbols — used for index_pcr()'s real OI reads."""
        return self.kite.quote([f"NFO:{t}" for t in tradingsymbols])

    def get_index_spot(self, underlying: str) -> float:
        sym = INDEX_QUOTE_SYMBOLS.get(underlying)
        if not sym:
            raise ValueError(f"No known index quote symbol for {underlying}")
        return self.kite.quote([sym])[sym]["last_price"]

    def get_holdings(self):
        """Long-term equity holdings (T+1 settled, not today's intraday MIS
        positions) — Kite Connect's holdings() endpoint, free of charge."""
        return self.kite.holdings()

    def get_margins(self):
        """Available cash/margin by segment — Kite Connect's margins() endpoint."""
        return self.kite.margins()
