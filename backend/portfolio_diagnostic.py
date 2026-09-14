"""
A read-only technical snapshot of your actual Kite holdings, using the exact
same indicators the scanner runs on the NIFTY 100 (indicators.py,
market_structure.py, swing_patterns.py) — not a separate or lighter-weight
analysis. This is deliberately NOT a buy/sell recommendation or a return
forecast: it reports what today's technical picture actually is for each
holding (trend, momentum, distance from key levels, any confirmed daily
pattern), and leaves the decision to you. Providing personalized advice
about real financial holdings is out of scope for this app; a diagnostic
reading is not.
"""

import indicators as ind
import market_structure as ms
import swing_patterns
from scanner import download_batch, yf_ticker

MIN_BARS = 60


def _posture(trend, rsi_v, pct_from_high, pct_from_low, reversal):
    """A plain-English label combining the real signals above — never a
    score, never a probability, just naming the pattern that's present."""
    tags = []
    if reversal and reversal["kind"] == "top":
        tags.append("Possible top reversal today (Murphy ch 4)")
    if reversal and reversal["kind"] == "bottom":
        tags.append("Possible bottom reversal today (Murphy ch 4)")
    if trend == "up" and rsi_v is not None and rsi_v > 70:
        tags.append("Uptrend, RSI overbought")
    elif trend == "up":
        tags.append("Uptrend")
    elif trend == "down" and rsi_v is not None and rsi_v < 30:
        tags.append("Downtrend, RSI oversold")
    elif trend == "down":
        tags.append("Downtrend")
    else:
        tags.append("Range / no clear trend")
    if pct_from_high is not None and pct_from_high <= 3:
        tags.append("Within 3% of its 52-week high")
    if pct_from_low is not None and pct_from_low <= 3:
        tags.append("Within 3% of its 52-week low")
    return tags


def run(holdings):
    """holdings: Kite holdings() list. Returns one diagnostic row per symbol
    that has enough daily history on NSE — silently skipping (and reporting)
    ones it can't read, never guessing in their place."""
    symbols = [h["tradingsymbol"] for h in holdings]
    tickers = [yf_ticker(s) for s in symbols]
    daily = download_batch(tickers, period="1y", interval="1d")

    rows, unreadable = [], []
    for h in holdings:
        sym = h["tradingsymbol"]
        bars = daily.get(yf_ticker(sym))
        if not bars or len(bars) < MIN_BARS:
            unreadable.append(sym)
            continue
        closes = [b["close"] for b in bars]
        close = closes[-1]
        atr_v = ind.atr(bars, 14)
        e20, e50 = ind.ema(closes, 20), ind.ema(closes, 50)
        trend = "up" if close > e20 > e50 else "down" if close < e20 < e50 else "sideways"
        rsi_v = ind.rsi(closes[-100:], 14)
        year = bars[-250:]
        high52, low52 = max(b["high"] for b in year), min(b["low"] for b in year)
        pct_from_high = (high52 - close) / high52 * 100 if high52 else None
        pct_from_low = (close - low52) / low52 * 100 if low52 else None
        highs, lows = ms.swing_points(bars, left=2, right=2)
        levels = ms.key_levels(bars, highs, lows, atr_v) if atr_v else []
        support, resistance = ms.nearest_levels(close, levels)
        patterns = swing_patterns.scan_daily_patterns(bars, atr_v) if atr_v else []
        reversal = swing_patterns.detect_reversal_day(bars, atr_v) if atr_v else None

        rows.append({
            "symbol": sym, "exchange": h.get("exchange"), "quantity": h.get("quantity"),
            "average_price": h.get("average_price"), "last_price": h.get("last_price"),
            "pnl": h.get("pnl"),
            "close": round(close, 2), "trend": trend, "rsi": round(rsi_v, 1) if rsi_v is not None else None,
            "atr_pct": round(atr_v / close * 100, 2) if atr_v else None,
            "pct_from_52w_high": round(pct_from_high, 1) if pct_from_high is not None else None,
            "pct_from_52w_low": round(pct_from_low, 1) if pct_from_low is not None else None,
            "support": round(support["price"], 2) if support else None,
            "resistance": round(resistance["price"], 2) if resistance else None,
            "confirmed_patterns": [p["name"] for p in patterns],
            "reversal_day": reversal["kind"] if reversal else None,
            "posture": _posture(trend, rsi_v, pct_from_high, pct_from_low, reversal),
        })
    return {"rows": rows, "unreadable": unreadable, "asof_note": "Today's technical read only — not a forecast, not advice."}
