"""
Daily-chart reversal patterns from Bulkowski's *Encyclopedia of Chart
Patterns*: Double Top/Bottom and Head-and-Shoulders Top/Bottom. Detected
geometrically from swing highs/lows (`market_structure.swing_points`) on
DAILY bars — the timeframe his statistics (`bulkowski.PATTERN_STATS`) were
actually measured on. Not intended for 5-minute candles.
"""

import market_structure as ms


def _pct_close(a, b, atr_v, tol=0.15):
    return abs(a - b) <= tol * atr_v


def detect_double_bottom(daily, atr_v, lookback=90):
    """Two comparable swing lows with a peak between them; confirmed once
    price closes back above that peak (Bulkowski's "confirmation line")."""
    bars = daily[-lookback:]
    highs, lows = ms.swing_points(bars, left=2, right=2)
    if len(lows) < 2:
        return None
    (i1, l1), (i2, l2) = lows[-2], lows[-1]
    if i2 - i1 < 5 or not _pct_close(l1, l2, atr_v, tol=0.5):
        return None
    between_highs = [h for j, h in highs if i1 < j < i2]
    if not between_highs:
        return None
    confirm = max(between_highs)
    close = bars[-1]["close"]
    if close <= confirm:
        return {"confirmed": False, "confirm_line": confirm, "neckline": None}
    return {"confirmed": True, "confirm_line": confirm, "stop": min(l1, l2)}


def detect_double_top(daily, atr_v, lookback=90):
    bars = daily[-lookback:]
    highs, lows = ms.swing_points(bars, left=2, right=2)
    if len(highs) < 2:
        return None
    (i1, h1), (i2, h2) = highs[-2], highs[-1]
    if i2 - i1 < 5 or not _pct_close(h1, h2, atr_v, tol=0.5):
        return None
    between_lows = [l for j, l in lows if i1 < j < i2]
    if not between_lows:
        return None
    confirm = min(between_lows)
    close = bars[-1]["close"]
    if close >= confirm:
        return {"confirmed": False, "confirm_line": confirm}
    return {"confirmed": True, "confirm_line": confirm, "stop": max(h1, h2)}


def detect_head_and_shoulders(daily, atr_v, lookback=110, top=True):
    """Three peaks/troughs with the middle one most extreme; confirmed on a
    neckline break (the line joining the two shoulders' opposite swings)."""
    bars = daily[-lookback:]
    highs, lows = ms.swing_points(bars, left=2, right=2)
    pivots = highs if top else lows
    if len(pivots) < 3:
        return None
    (i1, p1), (i2, p2), (i3, p3) = pivots[-3], pivots[-2], pivots[-1]
    if not (i2 - i1 >= 4 and i3 - i2 >= 4):
        return None
    head_is_extreme = (p2 > p1 and p2 > p3) if top else (p2 < p1 and p2 < p3)
    shoulders_similar = _pct_close(p1, p3, atr_v, tol=0.6)
    if not (head_is_extreme and shoulders_similar):
        return None
    opp = lows if top else highs
    between = [v for j, v in opp if i1 < j < i3]
    if len(between) < 2:
        return None
    neckline = (between[0] + between[-1]) / 2  # simple two-point neckline, not sloped
    close = bars[-1]["close"]
    confirmed = close < neckline if top else close > neckline
    return {
        "confirmed": confirmed, "neckline": neckline,
        "stop": p2,  # beyond the head
    }


def scan_daily_patterns(daily, atr_v):
    """All confirmed patterns on this daily series, as
    [{"name", "side", "stop", "level"}], most recent context only."""
    out = []
    db = detect_double_bottom(daily, atr_v)
    if db and db["confirmed"]:
        out.append({"name": "Double Bottom", "side": "long", "stop": db["stop"], "level": db["confirm_line"]})
    dt = detect_double_top(daily, atr_v)
    if dt and dt["confirmed"]:
        out.append({"name": "Double Top", "side": "short", "stop": dt["stop"], "level": dt["confirm_line"]})
    hsb = detect_head_and_shoulders(daily, atr_v, top=False)
    if hsb and hsb["confirmed"]:
        out.append({"name": "Head and Shoulders Bottom", "side": "long", "stop": hsb["stop"], "level": hsb["neckline"]})
    hst = detect_head_and_shoulders(daily, atr_v, top=True)
    if hst and hst["confirmed"]:
        out.append({"name": "Head and Shoulders Top", "side": "short", "stop": hst["stop"], "level": hst["neckline"]})
    return out
