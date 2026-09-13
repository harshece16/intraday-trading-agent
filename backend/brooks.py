"""
Al Brooks, *Trading Price Action Trends* (glossary, and Introduction ch on
the 20-EMA). Two codeable concepts not already covered by Varsity's Dow
Theory: a precise definition of a "trend bar", and the "always-in" direction
— the side you'd take if forced to have a position at every moment.

"trend bar: A bar with a body, which means that the close was above or below
the open, indicating that there is at least a minor price movement." A doji
is the opposite: a bar with (essentially) no body. Brooks also notes a strong
breakout bar has "a large bull trend body and small tails or no tails."

Brooks trades off "a single chart ... with no indicators except a 20-bar
exponential moving average (EMA)" and reads the always-in direction from how
price and trend bars behave around it.
"""


def is_trend_bar(bar, min_body_atr=0.1):
    body = abs(bar["close"] - bar["open"])
    rng = bar["high"] - bar["low"]
    return body > 0 and body >= min_body_atr * max(rng, 1e-9) and rng > 0


def trend_bar_strength(bar):
    """1.0 = a clean trend bar closing at its extreme with almost no tail
    (Brooks: "large body and small tails or no tails"); 0 = a doji."""
    rng = bar["high"] - bar["low"]
    if rng <= 0:
        return 0.0
    body = abs(bar["close"] - bar["open"])
    close_at_extreme = (bar["close"] - bar["low"]) / rng if bar["close"] >= bar["open"] \
        else (bar["high"] - bar["close"]) / rng
    return round(min(1.0, body / rng) * close_at_extreme, 3)


def always_in_direction(candles, ema_period=20):
    """"If you have to be in the market at all times ... this is whatever
    your current position is." Approximated as: price on one side of the
    20-EMA, with most of the recent trend bars closing that same side —
    the mode flips only when a strong, confirmed opposite move breaks it.
    Returns "long", "short", or "range" (no confident always-in state)."""
    from indicators import ema, ema_series
    closes = [c["close"] for c in candles]
    if len(closes) < ema_period + 10:
        return "range"
    ema_now = ema(closes, ema_period)
    series = ema_series(closes, ema_period)
    window = candles[-10:]
    ema_window = series[-10:]
    sides = [1 if c["close"] > e else -1 for c, e in zip(window, ema_window) if e is not None]
    if not sides:
        return "range"
    trend_bars = [c for c in window if is_trend_bar(c)]
    bar_sides = [1 if c["close"] > c["open"] else -1 for c in trend_bars]
    price = closes[-1]
    above = price > ema_now
    side_agreement = sum(1 for s in sides if s == (1 if above else -1)) / len(sides)
    bar_agreement = sum(1 for s in bar_sides if s == (1 if above else -1)) / len(bar_sides) if bar_sides else 0.5
    if side_agreement >= 0.7 and bar_agreement >= 0.5:
        return "long" if above else "short"
    return "range"
