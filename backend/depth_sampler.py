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

Each row also keeps the book itself, level by level (#188): every non-empty
level of each side, best first, as [price, quantity, orders] in
bid_levels_json and ask_levels_json. Until then only the touch and the
five-level quantity sums were kept, so the cost of an order bigger than
level 1 could only be modelled (#66). The summary columns are computed
exactly as before from the same levels, because the pre-registered
order-book test (docs/research/prereg-orderbook.md) reads them.
"""

import json
import logging

import config
import database

logger = logging.getLogger("trading_bot")


def levels_json(levels):
    """One side of the book as stored: [[price, quantity, orders], ...] best
    first, compact JSON. `orders` is None if Kite leaves it out."""
    return json.dumps([[lv["price"], lv["quantity"], lv.get("orders")] for lv in levels], separators=(",", ":"))


def snapshot(symbol, quote, ts):
    """One depth_samples row from a Kite quote dict, or None if the book is empty.
    A level counts only if it has a price and a quantity (Kite pads a thin
    book with zeros); the summary columns and the stored levels use the same
    levels, so level 1 is (bid, bid_qty1) and the quantities add up to bid_qty5."""
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
        "bid_levels_json": levels_json(bids), "ask_levels_json": levels_json(asks),
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


def _in_windows(hhmm, windows):
    return any(start <= hhmm < end for start, end in windows)


def index_row(name, quote, ts):
    """A depth_samples row for an index: level only, no book."""
    ltp = (quote or {}).get("last_price")
    return {"ts": ts, "symbol": name, "ltp": ltp} if ltp else None


def sample_windows(now, now_ts, fetch=None):
    """Order books of the overnight-hold ETFs, plus the index level, inside the
    entry and exit windows only (README section 81). The overnight test needs
    the spread a trader would actually cross at 15:20-15:29 to buy and at
    09:16-09:20 to sell; NIFTYBEES is not in the pre-open auction, so the exit
    is the continuous market, and its opening prints are noisy. One quote
    call per tick inside a window, none outside. Never raises."""
    cfg = getattr(config, "DEPTH_SAMPLER", {})
    symbols = cfg.get("window_symbols") or []
    indices = cfg.get("window_indices") or []
    if not cfg.get("enabled", True) or not (symbols or indices):
        return 0
    if not _in_windows(now.strftime("%H:%M"), cfg.get("windows") or []):
        return 0
    instruments = [f"NSE:{s}" for s in symbols] + [f"NSE:{i}" for i in indices]
    try:
        if fetch is None:
            import data_provider
            if not data_provider.kite_data_active():
                return 0
            quotes = data_provider._get_kite().quote(instruments)
        else:
            quotes = fetch(instruments)
    except Exception as exc:
        logger.warning(f"Window depth sample skipped: {exc}")
        return 0
    rows = [snapshot(s, quotes.get(f"NSE:{s}") or {}, now_ts) for s in symbols]
    rows += [index_row(i, quotes.get(f"NSE:{i}"), now_ts) for i in indices]
    rows = [r for r in rows if r]
    if rows:
        try:
            database.record_depth_samples(rows)
        except Exception as exc:
            logger.warning(f"Window depth samples not written: {exc}")
            return 0
    return len(rows)

