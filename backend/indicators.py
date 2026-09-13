"""
Technical indicators, pure Python over candle dicts (oldest first). Each
function returns None when there isn't enough history yet.
"""

from typing import List, Optional


def atr(candles, period=14) -> Optional[float]:
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, period + 1):
        high = candles[-i]["high"]
        low = candles[-i]["low"]
        prev_close = candles[-i - 1]["close"]
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return sum(trs) / period


def ema_series(values, period) -> List[Optional[float]]:
    out = [None] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    out[period - 1] = e
    for i in range(period, len(values)):
        e = values[i] * k + e * (1 - k)
        out[i] = e
    return out


def ema(values, period) -> Optional[float]:
    return ema_series(values, period)[-1] if values else None


def rsi(closes, period=14) -> Optional[float]:
    """Wilder-smoothed RSI, as used on every charting platform."""
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(1, period + 1):
        ch = closes[i] - closes[i - 1]
        gains += max(ch, 0.0)
        losses += max(-ch, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    for i in range(period + 1, len(closes)):
        ch = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(ch, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-ch, 0.0)) / period
    if avg_loss == 0:
        return 100.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def macd(closes, fast=12, slow=26, signal=9) -> Optional[dict]:
    if len(closes) < slow + signal + 1:
        return None
    ef, es = ema_series(closes, fast), ema_series(closes, slow)
    line = [f - s for f, s in zip(ef, es) if f is not None and s is not None]
    sig = ema_series(line, signal)
    hist = [l - s for l, s in zip(line, sig) if s is not None]
    return {"macd": line[-1], "signal": sig[-1], "hist": hist[-1], "prev_hist": hist[-2]}


def bollinger(closes, period=20, mult=2.0) -> Optional[dict]:
    if len(closes) < period:
        return None
    w = closes[-period:]
    mid = sum(w) / period
    sd = (sum((x - mid) ** 2 for x in w) / period) ** 0.5
    upper, lower = mid + mult * sd, mid - mult * sd
    return {"mid": mid, "upper": upper, "lower": lower, "width_pct": (upper - lower) / mid * 100 if mid else 0.0}


def session_vwap(candles) -> Optional[float]:
    """VWAP anchored to the current trading day (the intraday institutional benchmark)."""
    day = candles[-1]["time"][:10]
    pv = vol = 0.0
    for c in reversed(candles):
        if c["time"][:10] != day:
            break
        pv += (c["high"] + c["low"] + c["close"]) / 3 * c["volume"]
        vol += c["volume"]
    return pv / vol if vol > 0 else None


def adx(candles, period=14) -> Optional[dict]:
    """Wilder's ADX with +DI/-DI. ADX measures trend strength, not direction."""
    n = len(candles)
    if n < period * 2 + 1:
        return None
    trs, pdm, mdm = [], [], []
    for i in range(1, n):
        h, l = candles[i]["high"], candles[i]["low"]
        ph, pl, pc = candles[i - 1]["high"], candles[i - 1]["low"], candles[i - 1]["close"]
        up, down = h - ph, pl - l
        pdm.append(up if up > down and up > 0 else 0.0)
        mdm.append(down if down > up and down > 0 else 0.0)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))

    tr_s, p_s, m_s = sum(trs[:period]), sum(pdm[:period]), sum(mdm[:period])
    dxs = []
    pdi = mdi = 0.0
    for i in range(period - 1, len(trs)):
        if i >= period:
            tr_s = tr_s - tr_s / period + trs[i]
            p_s = p_s - p_s / period + pdm[i]
            m_s = m_s - m_s / period + mdm[i]
        pdi = 100 * p_s / tr_s if tr_s else 0.0
        mdi = 100 * m_s / tr_s if tr_s else 0.0
        dxs.append(100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0.0)

    adx_v = sum(dxs[:period]) / period
    for dx in dxs[period:]:
        adx_v = (adx_v * (period - 1) + dx) / period
    return {"adx": adx_v, "plus_di": pdi, "minus_di": mdi}


def stochastic(candles, k_period=14, d_period=3) -> Optional[dict]:
    if len(candles) < k_period + d_period + 1:
        return None
    ks = []
    for j in range(d_period + 1):
        end = len(candles) - d_period + j
        w = candles[end - k_period:end]
        hh = max(c["high"] for c in w)
        ll = min(c["low"] for c in w)
        ks.append(100 * (w[-1]["close"] - ll) / (hh - ll) if hh > ll else 50.0)
    return {
        "k": ks[-1], "prev_k": ks[-2],
        "d": sum(ks[-d_period:]) / d_period,
        "prev_d": sum(ks[-d_period - 1:-1]) / d_period,
    }


def volume_ratio(candles, period=20) -> Optional[float]:
    """Last bar's volume relative to the average of the preceding `period` bars."""
    if len(candles) < period + 1:
        return None
    avg = sum(c["volume"] for c in candles[-period - 1:-1]) / period
    return candles[-1]["volume"] / avg if avg > 0 else None


def obv_series(candles):
    """On Balance Volume (Granville, 1963; per Murphy, Technical Analysis of
    the Financial Markets, ch 7): cumulative volume signed by each bar's
    close direction. It's the TREND of this line that matters, not its
    absolute level."""
    out = []
    total = 0.0
    prev_close = None
    for c in candles:
        if prev_close is not None:
            if c["close"] > prev_close:
                total += c["volume"]
            elif c["close"] < prev_close:
                total -= c["volume"]
        out.append(total)
        prev_close = c["close"]
    return out


def obv_divergence(candles, lookback=20):
    """Murphy ch 7: 'the on balance volume line should follow in the same
    direction as the price trend ... it's when the volume line fails to move
    in the same direction that a divergence exists and warns of a possible
    trend reversal.' Compares price's change over `lookback` bars against
    OBV's change over the same window; returns "bullish"/"bearish" when they
    disagree, else None."""
    if len(candles) < lookback + 1:
        return None
    closes = [c["close"] for c in candles]
    obv = obv_series(candles)
    price_chg = closes[-1] - closes[-lookback]
    obv_chg = obv[-1] - obv[-lookback]
    if price_chg > 0 and obv_chg < 0:
        return "bearish"
    if price_chg < 0 and obv_chg > 0:
        return "bullish"
    return None


def resample(candles, factor):
    """Merge every `factor` bars within the same session into one higher-timeframe bar
    (e.g. 5m x 3 = 15m), for multi-timeframe confirmation without another data fetch."""
    out, bucket, day = [], [], None
    for c in candles:
        d = c["time"][:10]
        if bucket and (d != day or len(bucket) == factor):
            out.append(_merge(bucket))
            bucket = []
        day = d
        bucket.append(c)
    if bucket:
        out.append(_merge(bucket))
    return out


def _merge(bars):
    return {
        "time": bars[0]["time"],
        "open": bars[0]["open"],
        "high": max(b["high"] for b in bars),
        "low": min(b["low"] for b in bars),
        "close": bars[-1]["close"],
        "volume": sum(b["volume"] for b in bars),
    }
