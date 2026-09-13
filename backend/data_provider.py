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

import logging
from datetime import datetime, timedelta

import pandas as pd

import config

logger = logging.getLogger("trading_bot")

# yfinance-style interval strings -> Kite's own interval names.
_KITE_INTERVAL_MAP = {
    "1m": "minute", "2m": "minute", "5m": "5minute",
    "15m": "15minute", "30m": "30minute", "60m": "60minute", "1d": "day",
}

_kite_client = None
_instrument_token_cache = {}  # tradingsymbol -> instrument_token, fetched once per process


def kite_data_active() -> bool:
    return bool(config.USE_KITE_DATA and config.KITE_API_KEY and config.KITE_ACCESS_TOKEN)


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
    import yfinance as yf

    ticker = _yf_symbol(symbol)
    df = yf.download(
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
        })
    return candles


def get_intraday_candles(symbol: str, interval: str = "5m", period: str = "5d"):
    """
    Returns a list of dicts: [{"time": iso str, "close": float, "open": float,
    "high": float, "low": float, "volume": int}, ...] oldest first.
    """
    if kite_data_active():
        try:
            return _get_intraday_candles_kite(symbol, interval, period)
        except Exception as exc:
            logger.warning(f"Kite historical data failed for {symbol} ({exc}); falling back to yfinance")
    return _get_intraday_candles_yfinance(symbol, interval, period)


def get_ltp(symbol: str) -> float:
    """Last traded / most recent price."""
    if kite_data_active():
        try:
            kite = _get_kite()
            key = f"NSE:{symbol}"
            return float(kite.ltp([key])[key]["last_price"])
        except Exception as exc:
            logger.warning(f"Kite LTP failed for {symbol} ({exc}); falling back to yfinance")

    candles = _get_intraday_candles_yfinance(symbol, interval="1m", period="1d")
    if not candles:
        # fall back to a coarser interval if 1m data isn't available
        candles = _get_intraday_candles_yfinance(symbol, interval="5m", period="5d")
    if not candles:
        raise RuntimeError(f"Could not fetch price for {symbol}")
    return candles[-1]["close"]
