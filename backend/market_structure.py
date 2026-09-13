"""
Price-action / market-structure analysis: swing points, Dow-theory trend
(higher highs + higher lows), support/resistance zones built from where price
actually turned, previous-day and opening-range reference levels, and
breakout/breakdown detection.
"""


def swing_points(candles, left=3, right=3):
    """A swing high is a bar whose high exceeds the `left` bars before and the
    `right` bars after it. Only bars with `right` bars of hindsight qualify,
    so there's no look-ahead."""
    highs, lows = [], []
    for i in range(left, len(candles) - right):
        h, l = candles[i]["high"], candles[i]["low"]
        if all(h > candles[j]["high"] for j in range(i - left, i)) and \
                all(h >= candles[j]["high"] for j in range(i + 1, i + right + 1)):
            highs.append((i, h))
        if all(l < candles[j]["low"] for j in range(i - left, i)) and \
                all(l <= candles[j]["low"] for j in range(i + 1, i + right + 1)):
            lows.append((i, l))
    return highs, lows


def structure_trend(highs, lows):
    if len(highs) < 2 or len(lows) < 2:
        return "range"
    hh, hl = highs[-1][1] > highs[-2][1], lows[-1][1] > lows[-2][1]
    lh, ll = highs[-1][1] < highs[-2][1], lows[-1][1] < lows[-2][1]
    if hh and hl:
        return "uptrend"
    if lh and ll:
        return "downtrend"
    return "range"


def key_levels(candles, highs, lows, atr_val):
    """Cluster swing prices within half an ATR into zones; more touches = stronger level."""
    points = sorted(p for _, p in highs + lows)
    zones, cluster = [], []
    for p in points:
        if cluster and p - cluster[0] > 0.5 * atr_val:
            zones.append({"price": sum(cluster) / len(cluster), "kind": "swing", "touches": len(cluster)})
            cluster = []
        cluster.append(p)
    if cluster:
        zones.append({"price": sum(cluster) / len(cluster), "kind": "swing", "touches": len(cluster)})

    days = []
    for c in candles:
        d = c["time"][:10]
        if not days or days[-1][0] != d:
            days.append((d, []))
        days[-1][1].append(c)

    if len(days) >= 2:
        prev = days[-2][1]
        zones.append({"price": max(c["high"] for c in prev), "kind": "prev_day_high", "touches": 2})
        zones.append({"price": min(c["low"] for c in prev), "kind": "prev_day_low", "touches": 2})
        zones.append({"price": prev[-1]["close"], "kind": "prev_day_close", "touches": 1})

    today = days[-1][1]
    if len(today) > 3:
        opening = today[:3]
        zones.append({"price": max(c["high"] for c in opening), "kind": "opening_range_high", "touches": 2})
        zones.append({"price": min(c["low"] for c in opening), "kind": "opening_range_low", "touches": 2})

    return zones


def nearest_levels(price, levels):
    below = [lv for lv in levels if lv["price"] < price]
    above = [lv for lv in levels if lv["price"] > price]
    support = max(below, key=lambda lv: lv["price"]) if below else None
    resistance = min(above, key=lambda lv: lv["price"]) if above else None
    return support, resistance


def breakout_above(candles, levels, atr_val):
    """Close crossed above a meaningful level this bar, and isn't already overextended past it."""
    if len(candles) < 2:
        return None
    prev_close, close = candles[-2]["close"], candles[-1]["close"]
    hits = [lv for lv in levels
            if lv["touches"] >= 2 and prev_close <= lv["price"] < close and close - lv["price"] <= atr_val]
    return max(hits, key=lambda lv: lv["price"]) if hits else None


def breakdown_below(candles, levels, atr_val):
    if len(candles) < 2:
        return None
    prev_close, close = candles[-2]["close"], candles[-1]["close"]
    hits = [lv for lv in levels
            if lv["touches"] >= 2 and prev_close >= lv["price"] > close and lv["price"] - close <= atr_val]
    return min(hits, key=lambda lv: lv["price"]) if hits else None
