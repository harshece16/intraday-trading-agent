"""
Candlestick pattern recognition (Steve Nison / Japanese candlestick canon).

A pattern only means something in context: a hammer is a reversal signal
*after a decline*; the same shape after a rally is a hanging man. So every
detector here is conditioned on the trend leading into the pattern, and bars
whose range is tiny relative to ATR are ignored as noise.

Returns [{"name", "bias": "bullish"|"bearish"|"neutral", "strength": 1-3}].
"""


def _body(c):
    return abs(c["close"] - c["open"])


def _range(c):
    return c["high"] - c["low"]


def _upper(c):
    return c["high"] - max(c["open"], c["close"])


def _lower(c):
    return min(c["open"], c["close"]) - c["low"]


def _bull(c):
    return c["close"] > c["open"]


def _bear(c):
    return c["close"] < c["open"]


def _mid_body(c):
    return (c["open"] + c["close"]) / 2


def prior_trend(candles, atr_val, bars=8):
    """Direction of the move leading *into* the last 3 bars."""
    if len(candles) < bars + 4:
        return "flat"
    move = candles[-4]["close"] - candles[-4 - bars]["close"]
    if move < -atr_val:
        return "down"
    if move > atr_val:
        return "up"
    return "flat"


def detect_patterns(candles, atr_val):
    if len(candles) < 15 or not atr_val:
        return []
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    r3 = _range(c3)
    if r3 < 0.3 * atr_val:
        return []

    trend = prior_trend(candles, atr_val)
    found = []

    def add(name, bias, strength):
        found.append({"name": name, "bias": bias, "strength": strength})

    b1, b2, b3 = _body(c1), _body(c2), _body(c3)

    # --- single-bar ---
    if b3 <= 0.1 * r3:
        add("Doji", "neutral", 1)
    elif _lower(c3) >= 2 * b3 and _upper(c3) <= max(0.5 * b3, 0.1 * r3):
        if trend == "down":
            add("Hammer", "bullish", 2)
        elif trend == "up":
            add("Hanging Man", "bearish", 1)
    elif _upper(c3) >= 2 * b3 and _lower(c3) <= max(0.5 * b3, 0.1 * r3):
        if trend == "up":
            add("Shooting Star", "bearish", 2)
        elif trend == "down":
            add("Inverted Hammer", "bullish", 1)

    if b3 >= 0.9 * r3 and r3 >= atr_val:
        add("Bullish Marubozu" if _bull(c3) else "Bearish Marubozu", "bullish" if _bull(c3) else "bearish", 2)

    # --- two-bar ---
    r2 = _range(c2)
    if _bear(c2) and _bull(c3) and c3["close"] >= c2["open"] and c3["open"] <= c2["close"] and b3 > b2:
        add("Bullish Engulfing", "bullish", 3 if trend == "down" else 1)
    if _bull(c2) and _bear(c3) and c3["close"] <= c2["open"] and c3["open"] >= c2["close"] and b3 > b2:
        add("Bearish Engulfing", "bearish", 3 if trend == "up" else 1)

    if trend == "down" and _bear(c2) and r2 and b2 >= 0.6 * r2 and _bull(c3) \
            and c3["open"] <= c2["close"] and _mid_body(c2) < c3["close"] < c2["open"]:
        add("Piercing Line", "bullish", 2)
    if trend == "up" and _bull(c2) and r2 and b2 >= 0.6 * r2 and _bear(c3) \
            and c3["open"] >= c2["close"] and c2["open"] < c3["close"] < _mid_body(c2):
        add("Dark Cloud Cover", "bearish", 2)

    if r2 and b2 >= 0.6 * r2 and b3 < 0.5 * b2 \
            and max(c3["open"], c3["close"]) < max(c2["open"], c2["close"]) \
            and min(c3["open"], c3["close"]) > min(c2["open"], c2["close"]):
        if trend == "down" and _bear(c2):
            add("Bullish Harami", "bullish", 1)
        elif trend == "up" and _bull(c2):
            add("Bearish Harami", "bearish", 1)

    tol = 0.05 * atr_val
    if trend == "down" and _bear(c2) and _bull(c3) and abs(c2["low"] - c3["low"]) <= tol:
        add("Tweezer Bottom", "bullish", 1)
    if trend == "up" and _bull(c2) and _bear(c3) and abs(c2["high"] - c3["high"]) <= tol:
        add("Tweezer Top", "bearish", 1)

    if c3["high"] <= c2["high"] and c3["low"] >= c2["low"]:
        add("Inside Bar", "neutral", 1)

    # --- three-bar ---
    r1 = _range(c1)
    if trend == "down" and _bear(c1) and r1 and b1 >= 0.6 * r1 and b2 <= 0.3 * b1 \
            and _bull(c3) and c3["close"] > _mid_body(c1):
        add("Morning Star", "bullish", 3)
    if trend == "up" and _bull(c1) and r1 and b1 >= 0.6 * r1 and b2 <= 0.3 * b1 \
            and _bear(c3) and c3["close"] < _mid_body(c1):
        add("Evening Star", "bearish", 3)

    trio = (c1, c2, c3)
    if all(_bull(c) and _range(c) and _body(c) >= 0.5 * _range(c) for c in trio) \
            and c1["close"] < c2["close"] < c3["close"] \
            and c1["open"] <= c2["open"] <= c1["close"] and c2["open"] <= c3["open"] <= c2["close"]:
        add("Three White Soldiers", "bullish", 2)
    if all(_bear(c) and _range(c) and _body(c) >= 0.5 * _range(c) for c in trio) \
            and c1["close"] > c2["close"] > c3["close"] \
            and c1["close"] <= c2["open"] <= c1["open"] and c2["close"] <= c3["open"] <= c2["open"]:
        add("Three Black Crows", "bearish", 2)

    return found
