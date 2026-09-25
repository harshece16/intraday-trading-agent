"""
Order-book sampling — the first data here that no backtest has ever used.

The 76-configuration search (README section 69) showed every price-and-volume
entry rule sitting at zero before costs: candle shapes and indicators carry
no information at this cost. A new brain needs new information, and the one
source this project can collect for itself is Kite's five-level order book.
The liquidity check (section 58) reads it, but only at entry, a few times a
day. This samples it for every watched stock on every engine tick, so that in
a few weeks there is a dataset to ask: does spread, depth imbalance or a
depth shift precede the move?

One Kite `quote` call per tick for the whole watchlist; rows go to
depth_samples. Pure data collection: nothing here reads the result, and no
trading decision changes. `snapshot()` is a pure function of a quote dict so
it can be tested without Kite.
"""

import logging

import config
import database

logger = logging.getLogger("trading_bot")


def snapshot(symbol, quote, ts):
    """One depth_samples row from a Kite quote dict, or None if the book is empty."""
    depth = quote.get("depth") or {}
    bids = [lv for lv in depth.get("buy", []) if lv.get("price") and lv.get("quantity")]
    asks = [lv for lv in depth.get("sell", []) if lv.get("price") and lv.get("quantity")]
    if not bids or not asks:
        return None
    bid, ask = bids[0]["price"], asks[0]["price"]
    mid = (bid + ask) / 2
    bid_qty, ask_qty = sum(lv["quantity"] for lv in bids), sum(lv["quantity"] for lv in asks)
    return {
        "ts": ts, "symbol": symbol, "ltp": quote.get("last_price"),
        "bid": bid, "ask": ask, "spread_bp": round((ask - bid) / mid * 1e4, 3),
        "bid_qty1": bids[0]["quantity"], "ask_qty1": asks[0]["quantity"],
        "bid_qty5": bid_qty, "ask_qty5": ask_qty,
        # +1 = all bids, -1 = all asks: the book's lean, independent of size
        "imbalance5": round((bid_qty - ask_qty) / (bid_qty + ask_qty), 4) if bid_qty + ask_qty else None,
        "volume": quote.get("volume"), "total_buy_qty": quote.get("buy_quantity"),
        "total_sell_qty": quote.get("sell_quantity"),
    }


def sample(symbols, now_ts, fetch=None):
    """Sample every symbol once. Never raises: a failed sample is a gap in
    the dataset, not a stalled engine tick."""
    if not getattr(config, "DEPTH_SAMPLER", {}).get("enabled", True) or not symbols:
        return 0
    try:
        if fetch is None:
            import data_provider
            if not data_provider.kite_data_active():
                return 0
            quotes = data_provider._get_kite().quote([f"NSE:{s}" for s in symbols])
        else:
            quotes = fetch(symbols)
    except Exception as exc:
        logger.warning(f"Depth sample skipped: {exc}")
        return 0
    rows = [r for r in (snapshot(s, quotes.get(f"NSE:{s}") or {}, now_ts) for s in symbols) if r]
    if rows:
        try:
            database.record_depth_samples(rows)
        except Exception as exc:
            logger.warning(f"Depth samples not written: {exc}")
            return 0
    return len(rows)
