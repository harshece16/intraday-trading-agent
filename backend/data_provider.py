"""
Market data. Uses real-time Kite Connect data when credentials are
configured (config.USE_KITE_DATA + KITE_API_KEY/KITE_ACCESS_TOKEN — see
generate_access_token.py), falling back to free but ~15-min-delayed
yfinance data otherwise. Both paths return the same shape, so nothing
downstream (strategy_engine, trading_engine, backtester) needs to know
which one is active.

NSE symbols need a ".NS" suffix for Yahoo Finance (e.g. "RELIANCE.NS");
Kite uses the bare tradingsymbol with an "NSE:" exchange prefix instead.
"""

import concurrent.futures
import logging
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from kiteconnect.exceptions import TokenException

import config

logger = logging.getLogger("trading_bot")

# yfinance.download() keeps results in module-global state that every call resets and then waits on,
# so overlapping calls from different threads get each other's tickers or wait for entries that never come.
_YF_DOWNLOAD_LOCK = threading.Lock()
_YF_LOCK_TIMEOUT_SECONDS = 120

# The access token Kite last rejected; data calls skip Kite until config holds a different one.
_kite_rejected_token = None

IST = ZoneInfo("Asia/Kolkata")

# Bar length for the intraday intervals that map one-to-one onto Kite's.
_INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "60m": 3600}

# yfinance's NSE intraday feed runs ~15 min behind, so its newest row can still be filling after the bar ends.
_DELAYED_FEED_SETTLE = timedelta(minutes=30)

# yfinance-style interval strings -> Kite's own interval names.
_KITE_INTERVAL_MAP = {
    "1m": "minute", "2m": "minute", "5m": "5minute",
    "15m": "15minute", "30m": "30minute", "60m": "60minute", "1d": "day",
}

# Kite Connect's historical-data endpoint is rate-limited to roughly
# 3 req/sec; more concurrent workers just trades faster individual calls
# for more 429s that a symbol would then fall back to yfinance for anyway.
_KITE_HISTORICAL_MAX_WORKERS = 3

_kite_client = None
_instrument_token_cache = {}  # tradingsymbol -> instrument_token, fetched once per process


def kite_data_active() -> bool:
    return bool(config.USE_KITE_DATA and config.KITE_API_KEY and config.KITE_ACCESS_TOKEN
                and config.KITE_ACCESS_TOKEN != _kite_rejected_token)


def mark_kite_token_rejected():
    global _kite_rejected_token
    _kite_rejected_token = config.KITE_ACCESS_TOKEN


def _note_kite_failure(exc):
    if isinstance(exc, TokenException):
        mark_kite_token_rejected()


def yf_download(**kwargs):
    """yfinance.download(), one call at a time across the process (see _YF_DOWNLOAD_LOCK)."""
    import yfinance as yf
    if not _YF_DOWNLOAD_LOCK.acquire(timeout=_YF_LOCK_TIMEOUT_SECONDS):
        raise TimeoutError(f"another yfinance download has been running for over {_YF_LOCK_TIMEOUT_SECONDS}s")
    try:
        return yf.download(**kwargs)
    finally:
        _YF_DOWNLOAD_LOCK.release()


def _get_kite():
    global _kite_client
    if _kite_client is None:
        from kiteconnect import KiteConnect
        _kite_client = KiteConnect(api_key=config.KITE_API_KEY)
        _kite_client.set_access_token(config.KITE_ACCESS_TOKEN)
    return _kite_client


def reset_kite_client():
    """Drop the cached Kite client so the next call rebuilds it with
    whatever access token config now holds — needed after the dashboard's
    in-app 'Connect Kite' flow updates the token without a process restart."""
    global _kite_client
    _kite_client = None


def _instrument_token(symbol: str) -> int:
    if symbol not in _instrument_token_cache:
        kite = _get_kite()
        for row in kite.instruments("NSE"):
            if row.get("segment") == "NSE" and row.get("instrument_type") == "EQ":
                _instrument_token_cache[row["tradingsymbol"]] = row["instrument_token"]
    if symbol not in _instrument_token_cache:
        raise RuntimeError(f"No NSE instrument token found for {symbol!r}")
    return _instrument_token_cache[symbol]


def _days_from_period(period: str) -> int:
    return int(period[:-1]) if period.endswith("d") else 5


def _get_intraday_candles_kite(symbol: str, interval: str, period: str):
    kite = _get_kite()
    token = _instrument_token(symbol)
    kite_interval = _KITE_INTERVAL_MAP.get(interval, "5minute")
    to_date = datetime.now()
    from_date = to_date - timedelta(days=_days_from_period(period))

    rows = kite.historical_data(token, from_date, to_date, kite_interval)
    return [
        {
            "time": r["date"].isoformat(),
            "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]),
            "volume": int(r["volume"]),
        }
        for r in rows
    ]


def _yf_symbol(symbol: str) -> str:
    return symbol if symbol.endswith(".NS") else f"{symbol}.NS"


def _get_intraday_candles_yfinance(symbol: str, interval: str, period: str):
    ticker = _yf_symbol(symbol)
    df = yf_download(
        tickers=ticker, interval=interval, period=period,
        progress=False, auto_adjust=False,
    )
    if df is None or df.empty:
        logger.warning(f"No data returned for {ticker}")
        return []

    # yfinance sometimes returns a MultiIndex column set for single tickers
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # yfinance returns UTC; strategies read session dates and HH:MM from the ISO string as IST.
    if df.index.tz is not None:
        df.index = df.index.tz_convert("Asia/Kolkata")

    candles = []
    for ts, row in df.iterrows():
        candles.append({
            "time": ts.isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
            "delayed": True,
        })
    return candles


def get_intraday_candles(symbol: str, interval: str = "5m", period: str = "5d"):
    """
    Returns a list of dicts: [{"time": iso str, "close": float, "open": float,
    "high": float, "low": float, "volume": int}, ...] oldest first. "time" is
    the bar's start. Candles from the delayed yfinance feed also carry
    "delayed": True (see closed_bars()).
    """
    if kite_data_active():
        try:
            return _get_intraday_candles_kite(symbol, interval, period)
        except Exception as exc:
            _note_kite_failure(exc)
            logger.warning(f"Kite historical data failed for {symbol} ({exc}); falling back to yfinance")
    return _get_intraday_candles_yfinance(symbol, interval, period)


def closed_bars(candles, interval: str = "5m", now=None, delayed=None):
    """Drop the newest bar unless it has finished; `now` should be taken before the fetch."""
    seconds = _INTERVAL_SECONDS.get(interval)
    if not candles or seconds is None:
        return candles
    last = candles[-1]
    start = datetime.fromisoformat(last["time"])
    if start.tzinfo is None:
        start = start.replace(tzinfo=IST)
    now = now or datetime.now(IST)
    if delayed is None:
        delayed = bool(last.get("delayed"))
    if delayed:
        # How far behind the delayed feed runs isn't known exactly, so trust its newest row only after the session.
        close_t = datetime.strptime(config.MARKET_CLOSE, "%H:%M").time()
        session_close = datetime.combine(start.astimezone(IST).date(), close_t, tzinfo=IST)
        finished = now >= session_close + _DELAYED_FEED_SETTLE
    else:
        finished = now >= start + timedelta(seconds=seconds)
    return candles if finished else candles[:-1]


def _get_intraday_candles_yfinance_batch(symbols: list, interval: str, period: str) -> dict:
    """One yfinance request for many tickers instead of N separate ones —
    same batching trick scanner.py's download_batch() uses, adapted to key
    by our bare NSE symbol and return get_intraday_candles()'s candle shape."""
    tickers = [_yf_symbol(s) for s in symbols]
    df = yf_download(tickers=tickers, interval=interval, period=period, group_by="ticker",
                     progress=False, threads=True, auto_adjust=False)
    out = {}
    if df is None or df.empty:
        return out
    if df.index.tz is not None:
        df.index = df.index.tz_convert("Asia/Kolkata")
    multi = isinstance(df.columns, pd.MultiIndex)
    level0 = set(df.columns.get_level_values(0)) if multi else set()
    for symbol, ticker in zip(symbols, tickers):
        if multi and ticker not in level0:
            continue
        sub = (df[ticker] if multi else df).dropna(subset=["Close"])
        if sub.empty:
            continue
        out[symbol] = [
            {
                "time": ts.isoformat(), "open": float(o), "high": float(h), "low": float(l),
                "close": float(c), "volume": int(v) if not pd.isna(v) else 0, "delayed": True,
            }
            for ts, o, h, l, c, v in zip(sub.index, sub["Open"], sub["High"], sub["Low"], sub["Close"], sub["Volume"])
        ]
    return out


def get_candles_batch(symbols: list, interval: str = "5m", period: str = "5d") -> dict:
    """Fetch candles for many symbols concurrently instead of one blocking
    HTTP round-trip at a time (used by the live tick loop, now watching up
    to config.SCANNER['active_count'] symbols instead of the original 6).
    Returns {symbol: candles}; a symbol whose fetch fails on every path is
    simply absent from the result so the caller can fall back per-symbol.
    """
    symbols = list(dict.fromkeys(symbols))  # de-dupe, keep order
    if not symbols:
        return {}

    def _safe_yfinance_batch(syms):
        # The per-symbol Kite fetch above is defended (each future's
        # exception is caught individually); this batched yfinance call
        # wasn't — a fault-injection test caught it raising straight out of
        # get_candles_batch() when yfinance itself is unreachable, breaking
        # this function's own contract ("a symbol that fails on every path
        # is simply absent"), even though _tick_impl()'s own try/except
        # happened to mask it in practice. One bad batch call should drop
        # those symbols from the result, not the whole tick's candle fetch.
        try:
            return _get_intraday_candles_yfinance_batch(syms, interval, period)
        except Exception as exc:
            logger.warning(f"Batched yfinance fetch failed for {len(syms)} symbol(s) ({exc})")
            return {}

    if not kite_data_active():
        return _safe_yfinance_batch(symbols)

    out = {}
    fallback = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=_KITE_HISTORICAL_MAX_WORKERS) as pool:
        futures = {}
        for i, s in enumerate(symbols):
            # Stagger submissions to roughly match Kite's ~3 req/sec cap —
            # 3 idle workers otherwise fire near-simultaneously the moment
            # they're created, bursting well past the limit before any of
            # them has finished a request to naturally pace the next one.
            if i >= _KITE_HISTORICAL_MAX_WORKERS:
                time.sleep(1.0 / _KITE_HISTORICAL_MAX_WORKERS)
            futures[pool.submit(_get_intraday_candles_kite, s, interval, period)] = s
        for fut in concurrent.futures.as_completed(futures):
            symbol = futures[fut]
            try:
                out[symbol] = fut.result()
            except Exception as exc:
                _note_kite_failure(exc)
                logger.warning(f"Kite historical data failed for {symbol} ({exc}); falling back to yfinance")
                fallback.append(symbol)
    if fallback:
        out.update(_safe_yfinance_batch(fallback))
    return out


def get_ltp(symbol: str) -> float:
    """Last traded / most recent price."""
    if kite_data_active():
        try:
            kite = _get_kite()
            key = f"NSE:{symbol}"
            return float(kite.ltp([key])[key]["last_price"])
        except Exception as exc:
            _note_kite_failure(exc)
            logger.warning(f"Kite LTP failed for {symbol} ({exc}); falling back to yfinance")

    candles = _get_intraday_candles_yfinance(symbol, interval="1m", period="1d")
    if not candles:
        # fall back to a coarser interval if 1m data isn't available
        candles = _get_intraday_candles_yfinance(symbol, interval="5m", period="5d")
    if not candles:
        raise RuntimeError(f"Could not fetch price for {symbol}")
    return candles[-1]["close"]
