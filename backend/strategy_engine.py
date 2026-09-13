"""
Strategy functions, operating on intraday candles. Each returns
(signal, new_state) where signal is "BUY", "SELL", or None.

Both strategies below add a trend filter (only enter in the direction of a
longer-term SMA) and, for the crossover strategy, a volume filter (only
enter on above-average volume). These don't turn a strategy into a
guaranteed edge — they just filter out some of the lowest-conviction,
counter-trend entries that a raw crossover/RSI signal would otherwise take.
Exit signals are never filtered — safety (getting out) always goes through.
"""


def _sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


from indicators import atr  # noqa: E402,F401 — re-exported for trading_engine/backtester
from trader_brain import trader_brain_signal


def sma_crossover_signal(
    candles, fast=9, slow=21, trend_period=50, volume_filter=True, prev_state=None
):
    closes = [c["close"] for c in candles]
    volumes = [c["volume"] for c in candles]
    fast_sma = _sma(closes, fast)
    slow_sma = _sma(closes, slow)
    if fast_sma is None or slow_sma is None:
        return None, prev_state

    was_above = prev_state.get("fast_above_slow") if prev_state else None
    is_above = fast_sma > slow_sma

    signal = None
    if was_above is not None and was_above != is_above:
        if is_above:
            # Crossing up — only take it as a BUY if the broader trend
            # agrees and (optionally) volume confirms conviction.
            trend_sma = _sma(closes, trend_period)
            trend_ok = trend_sma is None or closes[-1] > trend_sma
            vol_ok = True
            if volume_filter and len(volumes) >= 20:
                avg_vol = sum(volumes[-20:]) / 20
                vol_ok = avg_vol == 0 or volumes[-1] > avg_vol
            if trend_ok and vol_ok:
                signal = "BUY"
        else:
            # Crossing down — always signal the exit, unfiltered.
            signal = "SELL"

    return signal, {"fast_above_slow": is_above, "fast_sma": fast_sma, "slow_sma": slow_sma}


def _rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        change = closes[-i] - closes[-i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def rsi_reversion_signal(
    candles, period=14, oversold=30, overbought=70, trend_period=50, prev_state=None
):
    closes = [c["close"] for c in candles]
    rsi = _rsi(closes, period)
    if rsi is None:
        return None, prev_state

    signal = None
    if rsi < oversold:
        # Buying oversold into a strong downtrend is "catching a falling
        # knife" — require price not be far below its longer-term trend.
        trend_sma = _sma(closes, trend_period)
        if trend_sma is None or closes[-1] > trend_sma * 0.98:
            signal = "BUY"
    elif rsi > overbought:
        signal = "SELL"

    return signal, {"last_rsi": rsi}


STRATEGY_FUNCTIONS = {
    "sma_crossover": sma_crossover_signal,
    "rsi_reversion": rsi_reversion_signal,
    "sahab_dimaag": trader_brain_signal,  # displayed as "Sahab's Dimaag" — implemented in trader_brain.py
}
