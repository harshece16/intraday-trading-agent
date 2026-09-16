"""
Sahab's Dimaag ("Sahab's brain" — Trader Sahab's decision engine, module
name trader_brain.py kept for history) — a confluence strategy that encodes
the checklist a
professionally trained technical trader (CMT / NISM curriculum, Dow theory,
Nison candlesticks, Wyckoff volume principles) runs before taking a trade:

  1. Context first: what regime is this (trending vs ranging, via ADX)?
     What does the higher timeframe say? Never fight the 15-min trend.
  2. Trend & structure: EMA alignment, VWAP side, higher highs/higher lows.
  3. Momentum: MACD, RSI read *according to the regime* (50-70 is strength
     in a trend; <35 is opportunity only in a range), stochastic turns.
  4. Location: where is price relative to support/resistance, previous-day
     levels and the opening range? Is there room to the next obstacle?
  5. Trigger: a candlestick pattern — weighted higher when it forms *at* a
     level, because a pattern in the middle of nowhere means little.
  6. Confirmation: volume participation on the trigger bar.
  7. Catalyst: news sentiment as a tilt, and a veto on strongly negative news.
  8. Fundamentals: real ROE/margin/PEG/debt-equity (fundamentals.py) as a
     tilt only — a weak balance sheet doesn't veto an otherwise-good
     intraday technical trade, it just trims size, same treatment as
     indicators/catalyst.
  9. Discipline: no entries in the opening 15 min or late in the session,
     require several *independent* categories to agree, never chase an
     overextended move.

Each rule adds or subtracts points to a bullish or bearish evidence ledger.
A BUY needs a high total, enough distinct confirming categories, and a clear
margin over the bearish case. The long is exited when the bearish case
builds up, or when trend structure breaks.

This is a disciplined decision process, not a guarantee. Backtest it
(python backtester.py --strategy trader_brain) and judge it on net-of-cost
results over as much data as you can get.
"""

import brooks
import indicators as ind
import market_structure as ms
from candlestick_patterns import detect_patterns

DEFAULTS = {
    "lookback": 250,
    "entry_threshold": 6.0,
    "min_confirmations": 3,
    "min_edge": 2.0,
    "exit_threshold": 5.0,
    "no_entry_before": "09:30",
    "last_entry_time": "14:30",
    "max_entries_per_day": 1,
    "no_entry_windows": [],          # e.g. [["12:00", "13:30"]] to skip the midday chop
    "allow_shorts": True,
    "entry_mode": "checklist",
    "min_rrr": 1.5,
    "sr_tolerance_atr": 0.5,
    "volume_lookback": 10,
    "indicator_miss_size": 0.6,
    "min_pattern_atr": 0.3,
    "max_pattern_atr": 3.0,
    "cost_pct": 0.12,
    "rrr_without_level": 2.0,
    "max_target_atr": 3.0,           # how far out to look for a level that actually clears min_rrr
    "adx_trend": 25,
    "adx_range": 20,
    "htf_factor": 3,
    "use_news": True,
    "news_weight": 2.0,
    "news_veto": -0.5,
    "use_fundamentals": True,
    "fundamentals_weight": 1.5,
}


class _Ledger:
    def __init__(self):
        self.items = []

    def add(self, category, points, reason):
        self.items.append((category, points, reason))

    @property
    def total(self):
        return sum(p for _, p, _ in self.items)

    @property
    def categories(self):
        net = {}
        for c, p, _ in self.items:
            net[c] = net.get(c, 0.0) + p
        return sorted(c for c, v in net.items() if v > 0)

    def reasons(self, limit):
        ranked = sorted(self.items, key=lambda it: -abs(it[1]))[:limit]
        return [{"category": c, "points": round(p, 2), "text": r} for c, p, r in ranked]


def _r(x, nd=2):
    return round(x, nd) if isinstance(x, float) else x


PATTERN_BARS = {
    "Bullish Engulfing": 2, "Bearish Engulfing": 2, "Piercing Line": 2, "Dark Cloud Cover": 2,
    "Bullish Harami": 2, "Bearish Harami": 2, "Tweezer Bottom": 2, "Tweezer Top": 2,
    "Morning Star": 3, "Evening Star": 3, "Three White Soldiers": 3, "Three Black Crows": 3,
    "Abandoned Baby Bottom": 3, "Abandoned Baby Top": 3,
    "Rising Three Methods": 5, "Falling Three Methods": 5,
}
_LEVEL_NAMES = {
    "swing": "a tested swing level", "prev_day_high": "yesterday's high", "prev_day_low": "yesterday's low",
    "prev_day_close": "yesterday's close", "opening_range_high": "the opening-range high",
    "opening_range_low": "the opening-range low", "cpr_top": "the CPR top", "cpr_bottom": "the CPR bottom",
    "pivot": "the pivot",
}


def _level_name(lv):
    if lv["kind"].startswith("fib_"):
        return f"the {lv['kind'][4:]}% Fibonacci retracement"
    return _LEVEL_NAMES.get(lv["kind"], lv["kind"].replace("_", " "))


CHECKLIST_SOURCES = {
    "pattern": "Varsity Technical Analysis ch 4-10, and Nison, Japanese Candlestick Charting Techniques",
    "sr": "Varsity Technical Analysis, ch 11 (support & resistance)",
    "volume": "Varsity Technical Analysis, ch 12 (volume); On Balance Volume divergence per "
              "Murphy, Technical Analysis of the Financial Markets, ch 7",
    "dow": "Varsity Technical Analysis ch 17-18 (Dow Theory), and Brooks, Trading Price Action Trends (always-in direction)",
    "indicators": "Varsity Technical Analysis, ch 13-16 (moving averages, RSI, MACD)",
    "catalyst": "NSE filings + news sentiment (news_sentiment.py) — the news side of the checklist",
    "rrr": "Varsity Technical Analysis ch 18.5 (Reward-to-Risk), targets from Bulkowski's measured pattern moves when available",
    "fundamentals": "Real ROE/margin/PEG/debt-equity via Yahoo Finance (fundamentals.py) — Peter Lynch / Graham-style "
                    "screening thresholds, also covered in Zerodha Varsity's Fundamental Analysis module",
}


def _checklist(side, window, patterns, levels, atr_v, vol10, htf_trend, structure, macd_v, rsi_v,
               always_in, news_score, fundamentals_score, p):
    """Zerodha Varsity's Grand Checklist (Technical Analysis module, ch 11-18) for one side,
    plus two connections Varsity doesn't make explicit: Al Brooks' "always-in" direction
    alongside Dow Theory, and today's news catalyst alongside the chart. Required: pattern,
    stop at S&R, volume, trend, RRR. Indicators and the catalyst only change the size."""
    s = 1 if side == "long" else -1
    bias = "bullish" if s > 0 else "bearish"
    level_word = "support" if s > 0 else "resistance"
    price = window[-1]["close"]
    items = []

    def item(key, label, ok, detail, required=True):
        items.append({"key": key, "label": label, "ok": bool(ok), "detail": detail, "required": required,
                     "source": CHECKLIST_SOURCES[key]})

    candidates = sorted((x for x in patterns if x["bias"] == bias), key=lambda x: -x["strength"])
    pattern = candidates[0] if candidates else None
    stop = target = rrr = None
    if pattern:
        bars = window[-PATTERN_BARS.get(pattern["name"], 1):]
        stop = min(b["low"] for b in bars) if s > 0 else max(b["high"] for b in bars)
        span = max(b["high"] for b in bars) - min(b["low"] for b in bars)
        sane = p["min_pattern_atr"] * atr_v <= span <= p["max_pattern_atr"] * atr_v
        item("pattern", "Recognisable candlestick pattern", sane,
             pattern["name"] if sane else
             f"{pattern['name']}, but its range is {span / atr_v:.1f}× ATR; Varsity says not to trade abnormal candles")
    else:
        item("pattern", "Recognisable candlestick pattern", False, f"No {bias} pattern after a prior trend")

    risk = abs(price - stop) if stop is not None else 0.0
    if risk > 0:
        tol = p["sr_tolerance_atr"] * atr_v
        near = [lv for lv in levels
                if (lv["price"] <= price if s > 0 else lv["price"] >= price)
                and abs(lv["price"] - stop) <= tol and (lv["touches"] >= 2 or lv["kind"] != "swing")]
        best = min(near, key=lambda lv: abs(lv["price"] - stop)) if near else None
        item("sr", f"Stop-loss sits at {level_word}", best is not None,
             f"Stop {stop:.2f} is at {_level_name(best)} ({best['price']:.2f})" if best else
             f"No {level_word} within {p['sr_tolerance_atr']:g} ATR of the stop {stop:.2f}")
    else:
        item("sr", f"Stop-loss sits at {level_word}", False, "Needs a pattern to place the stop")

    item("volume", "Above-average volume", vol10 is not None and vol10 > 1.0,
         f"Volume is {vol10:.1f}× its {p['volume_lookback']}-candle average" if vol10 is not None else "No volume data")

    always_in_side = "long" if s > 0 else "short"
    brooks_ok = always_in == always_in_side
    dow_ok = htf_trend == ("up" if s > 0 else "down") or (
        htf_trend == "flat" and structure != ("downtrend" if s > 0 else "uptrend"))
    item("dow", "Trend agrees (Dow Theory or Brooks always-in)", dow_ok or brooks_ok,
         f"15-min trend {htf_trend}, structure {structure}, Brooks always-in {always_in}")

    hist = macd_v["hist"]
    ind_ok = hist * s > 0 and (rsi_v < 75 if s > 0 else rsi_v > 25)
    item("indicators", "Indicators confirm (MACD and RSI)", ind_ok,
         f"MACD histogram {'above' if hist > 0 else 'below'} zero, RSI {rsi_v:.0f}"
         + ("" if ind_ok else f"; trade at {p['indicator_miss_size']:.0%} size"), required=False)

    cat_ok = news_score is None or news_score * s >= -0.15
    news_word = "no notable news" if news_score is None or abs(news_score) < 0.05 \
        else f"news sentiment {news_score:+.2f}"
    item("catalyst", "News catalyst doesn't contradict the trade", cat_ok,
         f"{news_word}" + ("" if cat_ok else f"; trade at {p['indicator_miss_size']:.0%} size"), required=False)

    fund_ok = fundamentals_score is None or fundamentals_score * s >= -1.0
    fund_word = "no fundamentals data" if fundamentals_score is None else f"fundamentals score {fundamentals_score:+.1f}"
    item("fundamentals", "Company fundamentals don't contradict the trade", fund_ok,
         f"{fund_word}" + ("" if fund_ok else f"; trade at {p['indicator_miss_size']:.0%} size"), required=False)

    if risk > 0:
        cost = price * p["cost_pct"] / 100
        level_word2 = "resistance" if s > 0 else "support"
        beyond = sorted(
            (lv["price"] for lv in levels
             if (lv["price"] > price + 0.1 * atr_v if s > 0 else lv["price"] < price - 0.1 * atr_v)),
            key=lambda lv_price: abs(lv_price - price),
        )
        # "Next level" means the nearest one that actually gives room to run,
        # not just whichever is structurally closest — key_levels()/fib/CPR
        # produce many closely-spaced candidates (swing zones, 7 fib ratios,
        # CPR sub-levels), so the single nearest one is very often under
        # 0.5 ATR away and auto-fails R:R regardless of how good the setup
        # otherwise is (empirically: median R:R was ~0, taking the nearest
        # level, across a real session's worth of evaluations). Walk
        # outward — capped at max_target_atr so the target stays realistic
        # for an intraday move — for the first level that clears min_rrr;
        # only fall back to the formulaic no-level target if none do.
        qualifying = next(
            (lv_price for lv_price in beyond
             if abs(lv_price - price) <= p["max_target_atr"] * atr_v
             and (abs(lv_price - price) - cost) / (risk + cost) >= p["min_rrr"]),
            None,
        )
        if qualifying is not None:
            target = qualifying
            source = f"next {level_word2} that clears {p['min_rrr']:g}R"
        elif beyond:
            target = beyond[0]
            source = f"next {level_word2}"
        else:
            target = price + s * p["rrr_without_level"] * risk
            source = f"{p['rrr_without_level']:g}R, no level beyond"
        rrr = (abs(target - price) - cost) / (risk + cost)
        item("rrr", f"Reward-to-risk at least {p['min_rrr']:g}", rrr >= p["min_rrr"],
             f"Target {target:.2f} ({source}), stop {stop:.2f}: {rrr:.2f} after costs")
    else:
        item("rrr", f"Reward-to-risk at least {p['min_rrr']:g}", False, "Needs a stop to measure risk")

    return {
        "side": side,
        "items": items,
        "passed": all(i["ok"] for i in items if i["required"]),
        "pattern": pattern["name"] if pattern else None,
        "entry": _r(price), "stop": _r(stop), "target": _r(target), "rrr": _r(rrr),
        "size_factor": p["indicator_miss_size"] if not (ind_ok and cat_ok and fund_ok) else 1.0,
    }


def trader_brain_signal(candles, prev_state=None, news=None, fundamentals=None, **params):
    p = {**DEFAULTS, **params}
    prev_state = prev_state or {}
    window = candles[-p["lookback"]:]
    if len(window) < 80:
        return None, prev_state

    closes = [c["close"] for c in window]
    last = window[-1]
    price = last["close"]

    atr_v = ind.atr(window, 14)
    e20, e50 = ind.ema(closes, 20), ind.ema(closes, 50)
    rsi_v = ind.rsi(closes, 14)
    macd_v = ind.macd(closes)
    bb = ind.bollinger(closes)
    vwap = ind.session_vwap(window)
    adx_v = ind.adx(window, 14)
    stoch = ind.stochastic(window)
    vol_ratio = ind.volume_ratio(window, 20)
    if not atr_v or None in (e20, e50, rsi_v, macd_v, bb, adx_v, stoch):
        return None, prev_state

    htf = ind.resample(window, p["htf_factor"])
    htf_closes = [c["close"] for c in htf]
    h20, h50 = ind.ema(htf_closes, 20), ind.ema(htf_closes, 50)
    htf_trend = "flat"
    if h20 is not None and h50 is not None:
        if h20 > h50 and htf_closes[-1] > h20:
            htf_trend = "up"
        elif h20 < h50 and htf_closes[-1] < h20:
            htf_trend = "down"

    highs, lows = ms.swing_points(window)
    structure = ms.structure_trend(highs, lows)
    levels = ms.key_levels(window, highs, lows, atr_v)
    cpr = ms.central_pivot_range(window)
    levels = levels + ms.fibonacci_levels(highs, lows) + ms.cpr_levels(cpr)
    support, resistance = ms.nearest_levels(price, levels)
    brk_up = ms.breakout_above(window, levels, atr_v)
    brk_dn = ms.breakdown_below(window, levels, atr_v)
    patterns = detect_patterns(window, atr_v)

    adx = adx_v["adx"]
    regime = "trending" if adx >= p["adx_trend"] else "ranging" if adx < p["adx_range"] else "transition"
    up_bar, down_bar = last["close"] > last["open"], last["close"] < last["open"]

    bull, bear = _Ledger(), _Ledger()

    # 1-2. Trend, VWAP, structure
    if price > e20 > e50:
        bull.add("trend", 2.0, "Price > EMA20 > EMA50 — trend aligned up")
    elif price < e20 < e50:
        bear.add("trend", 2.0, "Price < EMA20 < EMA50 — trend aligned down")
    if vwap:
        if price > vwap:
            bull.add("trend", 1.0, f"Above session VWAP {vwap:.2f} — buyers in control")
        else:
            bear.add("trend", 1.0, f"Below session VWAP {vwap:.2f} — sellers in control")
    if structure == "uptrend":
        bull.add("structure", 1.0, "Higher highs & higher lows (Dow theory uptrend)")
    elif structure == "downtrend":
        bear.add("structure", 1.0, "Lower highs & lower lows (Dow theory downtrend)")

    if cpr:
        if price > cpr["top"]:
            bull.add("levels", 1.0, f"Above the CPR top {cpr['top']:.2f}")
        elif price < cpr["bottom"]:
            bear.add("levels", 1.0, f"Below the CPR bottom {cpr['bottom']:.2f}")

    # Higher timeframe
    if htf_trend == "up":
        bull.add("htf", 1.5, "15-min trend is up")
        bear.add("htf", -2.0, "Short would fight the 15-min uptrend")
    elif htf_trend == "down":
        bear.add("htf", 1.5, "15-min trend is down")
        bull.add("htf", -2.0, "Long would fight the 15-min downtrend")

    # 3. Momentum, read per regime
    hist, prev_hist = macd_v["hist"], macd_v["prev_hist"]
    if prev_hist <= 0 < hist:
        bull.add("momentum", 1.5, "MACD bullish crossover")
    elif hist > 0 and hist > prev_hist:
        bull.add("momentum", 1.0, "MACD histogram positive and rising")
    if prev_hist >= 0 > hist:
        bear.add("momentum", 1.5, "MACD bearish crossover")
    elif hist < 0 and hist < prev_hist:
        bear.add("momentum", 1.0, "MACD histogram negative and falling")

    if regime == "ranging":
        if rsi_v <= 35:
            bull.add("momentum", 1.5, f"RSI {rsi_v:.0f} oversold inside a range")
        elif rsi_v >= 65:
            bear.add("momentum", 1.5, f"RSI {rsi_v:.0f} overbought inside a range")
        if stoch["prev_k"] < stoch["prev_d"] and stoch["k"] > stoch["d"] and stoch["prev_k"] < 25:
            bull.add("momentum", 1.0, "Stochastic turning up from oversold")
        if stoch["prev_k"] > stoch["prev_d"] and stoch["k"] < stoch["d"] and stoch["prev_k"] > 75:
            bear.add("momentum", 1.0, "Stochastic turning down from overbought")
        if price <= bb["lower"]:
            bull.add("levels", 1.0, "At lower Bollinger band in a range (mean reversion)")
        elif price >= bb["upper"]:
            bear.add("levels", 1.0, "At upper Bollinger band in a range (mean reversion)")
    else:
        if 50 <= rsi_v <= 70:
            bull.add("momentum", 1.0, f"RSI {rsi_v:.0f} in bullish momentum zone")
        elif 30 <= rsi_v < 50:
            bear.add("momentum", 1.0, f"RSI {rsi_v:.0f} in bearish momentum zone")
    if rsi_v >= 78:
        bull.add("momentum", -1.5, f"RSI {rsi_v:.0f} overextended — don't chase")
    elif rsi_v <= 22:
        bear.add("momentum", -1.5, f"RSI {rsi_v:.0f} washed out — late to sell")

    # 6. Volume read with price (Varsity volume trend table, 10-period average)
    vol10 = ind.volume_ratio(window, p["volume_lookback"])
    if vol10 is not None:
        if up_bar:
            if vol10 > 1:
                bull.add("volume", 1.0, f"Price up on {vol10:.1f}× average volume, smart money buying")
            else:
                bull.add("volume", -0.5, f"Price up on thin volume ({vol10:.1f}×), weak hands buying")
        elif down_bar:
            if vol10 > 1:
                bear.add("volume", 1.0, f"Price down on {vol10:.1f}× average volume, smart money selling")
            else:
                bear.add("volume", -0.5, f"Price down on thin volume ({vol10:.1f}×), weak hands selling")

    # On Balance Volume divergence (Murphy ch 7): the volume trend disagreeing
    # with the price trend over a longer window is an early warning, ahead of
    # what a single bar's volume ratio can show.
    obv_div = ind.obv_divergence(window, p["volume_lookback"] * 2)
    if obv_div == "bullish":
        bull.add("volume", 1.0, "OBV rising while price fell — Murphy volume/price divergence")
    elif obv_div == "bearish":
        bear.add("volume", 1.0, "OBV falling while price rose — Murphy volume/price divergence")

    # 4. Location
    if brk_up:
        strong = vol_ratio is not None and vol_ratio >= 1.2
        bull.add("levels", 2.0 if strong else 1.0,
                 f"Breakout above {brk_up['kind'].replace('_', ' ')} {brk_up['price']:.2f}"
                 + ("" if strong else " (weak volume)"))
    if brk_dn:
        strong = vol_ratio is not None and vol_ratio >= 1.2
        bear.add("levels", 2.0 if strong else 1.0,
                 f"Breakdown below {brk_dn['kind'].replace('_', ' ')} {brk_dn['price']:.2f}"
                 + ("" if strong else " (weak volume)"))
    near_support = support is not None and price - support["price"] <= 0.75 * atr_v
    near_resistance = resistance is not None and resistance["price"] - price <= 0.75 * atr_v
    if near_support and up_bar and not brk_dn:
        bull.add("levels", 1.0, f"Bouncing off support {support['price']:.2f}")
    if near_resistance and down_bar and not brk_up:
        bear.add("levels", 1.0, f"Rejected at resistance {resistance['price']:.2f}")
    if resistance is not None and resistance["price"] - price < atr_v and not brk_up:
        bull.add("levels", -1.5, f"Resistance {resistance['price']:.2f} within 1 ATR — poor reward:risk")
    if support is not None and price - support["price"] < atr_v and not brk_dn:
        bear.add("levels", -1.5, f"Support {support['price']:.2f} within 1 ATR — poor reward:risk for a short")

    # 5. Candlestick triggers, weighted by location
    at_value = near_support or abs(last["low"] - e20) <= 0.5 * atr_v or (vwap and abs(last["low"] - vwap) <= 0.5 * atr_v)
    at_top = near_resistance or abs(last["high"] - e20) <= 0.5 * atr_v or (vwap and abs(last["high"] - vwap) <= 0.5 * atr_v)
    for pat in patterns:
        if pat["bias"] == "bullish":
            pts = pat["strength"] * (1.0 if at_value else 0.5)
            bull.add("pattern", pts, f"{pat['name']}" + (" at a value area" if at_value else " (no level context)"))
        elif pat["bias"] == "bearish":
            pts = pat["strength"] * (1.0 if at_top else 0.5)
            bear.add("pattern", pts, f"{pat['name']}" + (" at resistance" if at_top else " (no level context)"))

    # 7. News
    news_score = None
    long_veto = short_veto = False
    if news and p["use_news"]:
        news_score = news.get("score", 0.0)
        if news_score > 0.15:
            bull.add("news", news_score * p["news_weight"], f"Positive news sentiment ({news_score:+.2f})")
        elif news_score < -0.15:
            bear.add("news", -news_score * p["news_weight"], f"Negative news sentiment ({news_score:+.2f})")
        long_veto = news_score <= p["news_veto"]
        short_veto = news_score >= -p["news_veto"]

    # 8. Fundamentals — a tilt only, never a veto (a weak balance sheet
    # doesn't invalidate a good intraday technical trade, unlike news).
    fundamentals_score = None
    if fundamentals and p["use_fundamentals"]:
        fundamentals_score = fundamentals.get("score")
        if fundamentals_score is not None:
            if fundamentals_score >= 1.0:
                bull.add("fundamentals", fundamentals_score * p["fundamentals_weight"] / 4,
                         f"Strong fundamentals (score {fundamentals_score:+.1f})")
            elif fundamentals_score <= -1.0:
                bear.add("fundamentals", -fundamentals_score * p["fundamentals_weight"] / 4,
                         f"Weak fundamentals (score {fundamentals_score:+.1f})")

    # 9. Decision with discipline rules — longs and shorts are exact mirrors
    hhmm = last["time"][11:16]
    blocked_window = next(((a, b) for a, b in p["no_entry_windows"] if a <= hhmm < b), None)
    in_entry_window = p["no_entry_before"] <= hhmm < p["last_entry_time"] and blocked_window is None
    exit_long = bear.total >= p["exit_threshold"] or (price < e50 and structure == "downtrend") or long_veto
    exit_short = bull.total >= p["exit_threshold"] or (price > e50 and structure == "uptrend") or short_veto
    long_ok = (
        in_entry_window and not long_veto and not exit_long
        and bull.total >= p["entry_threshold"]
        and len(bull.categories) >= p["min_confirmations"]
        and bull.total - bear.total >= p["min_edge"]
    )
    short_ok = (
        p["allow_shorts"] and in_entry_window and not short_veto and not exit_short
        and bear.total >= p["entry_threshold"]
        and len(bear.categories) >= p["min_confirmations"]
        and bear.total - bull.total >= p["min_edge"]
    )

    always_in = brooks.always_in_direction(window)
    cl_long = _checklist("long", window, patterns, levels, atr_v, vol10, htf_trend, structure, macd_v, rsi_v,
                        always_in, news_score, fundamentals_score, p)
    cl_short = _checklist("short", window, patterns, levels, atr_v, vol10, htf_trend, structure, macd_v, rsi_v,
                          always_in, news_score, fundamentals_score, p) \
        if p["allow_shorts"] else None
    if p["entry_mode"] == "checklist":
        # Varsity exits are the pattern stop, the S&R target and the square-off, not score swings.
        exit_long, exit_short = long_veto, short_veto
        long_ok = in_entry_window and not long_veto and cl_long["passed"]
        short_ok = bool(cl_short) and in_entry_window and not short_veto and cl_short["passed"]
        if long_ok and short_ok:
            long_ok = short_ok = False

    day = last["time"][:10]
    entries_today = prev_state.get("entries_today", 0) if prev_state.get("entry_day") == day else 0
    can_enter = entries_today < p["max_entries_per_day"]
    signal = None
    if long_ok and not prev_state.get("long_ok") and can_enter:
        signal = "BUY"
        entries_today += 1
    elif short_ok and not prev_state.get("short_ok") and can_enter:
        signal = "SHORT"
        entries_today += 1
    elif exit_long and not prev_state.get("exit_long"):
        signal = "SELL"
    elif exit_short and not prev_state.get("exit_short"):
        signal = "COVER"

    bullish_side = bull.total >= bear.total
    if brk_up:
        setup = "Breakout"
    elif brk_dn:
        setup = "Breakdown"
    elif regime == "ranging" and bullish_side and (rsi_v <= 40 or near_support):
        setup = "Range reversal"
    elif regime == "ranging" and not bullish_side and (rsi_v >= 60 or near_resistance):
        setup = "Range rejection"
    elif price > e20 > e50 and abs(last["low"] - e20) <= 0.5 * atr_v:
        setup = "Trend pullback"
    elif price < e20 < e50 and abs(last["high"] - e20) <= 0.5 * atr_v:
        setup = "Pullback short"
    else:
        setup = "Bullish confluence" if bullish_side else "Bearish confluence"
    if p["entry_mode"] == "checklist":
        if long_ok and cl_long["pattern"]:
            setup = cl_long["pattern"]
        elif short_ok and cl_short["pattern"]:
            setup = cl_short["pattern"]

    ledger, other = (bull, bear) if bullish_side else (bear, bull)
    label = "Bull" if bullish_side else "Bear"
    blockers = []
    if not bullish_side and not p["allow_shorts"]:
        blockers.append("Short selling is disabled")
    if blocked_window:
        blockers.append(f"Midday no-entry window ({blocked_window[0]}–{blocked_window[1]})")
    elif not in_entry_window:
        blockers.append(f"Outside entry window ({p['no_entry_before']}–{p['last_entry_time']})")
    if bullish_side and long_veto:
        blockers.append("Strongly negative news — no longs")
    if not bullish_side and short_veto:
        blockers.append("Strongly positive news — no shorts")
    if ledger.total < p["entry_threshold"]:
        blockers.append(f"{label} score {ledger.total:.1f} below {p['entry_threshold']}")
    if len(ledger.categories) < p["min_confirmations"]:
        blockers.append(f"Only {len(ledger.categories)} confirming categories (need {p['min_confirmations']})")
    if ledger.total - other.total < p["min_edge"]:
        blockers.append(f"Edge over the opposite case only {ledger.total - other.total:.1f} (need {p['min_edge']})")
    if not can_enter and signal not in ("BUY", "SHORT"):
        blockers.append(f"Already took {entries_today} entry today in this stock — no revenge trades")
    if p["entry_mode"] == "checklist":
        cl = cl_long if bullish_side or not cl_short else cl_short
        blockers = [b for b in blockers if b.startswith(("Outside", "Midday", "Strongly", "Already", "Short selling"))]
        blockers += [f"{i['label']}: {i['detail']}" for i in cl["items"] if i["required"] and not i["ok"]]

    new_state = {
        "long_ok": long_ok,
        "short_ok": short_ok,
        "exit_long": exit_long,
        "exit_short": exit_short,
        "bias": "long" if bullish_side else "short",
        "shorts_enabled": p["allow_shorts"],
        "setup": setup,
        "regime": regime,
        "structure": structure,
        "htf_trend": htf_trend,
        "always_in": always_in,
        "bull_score": _r(bull.total),
        "bear_score": _r(bear.total),
        "entry_threshold": p["entry_threshold"],
        "exit_threshold": p["exit_threshold"],
        "confirmations": bull.categories,
        "bear_confirmations": bear.categories,
        "reasons": bull.reasons(6),
        "bear_reasons": bear.reasons(6),
        "blockers": [] if (long_ok or short_ok) else blockers,
        "patterns": [{"name": x["name"], "bias": x["bias"]} for x in patterns],
        "rsi": _r(rsi_v, 1), "adx": _r(adx, 1), "atr": _r(atr_v),
        "ema20": _r(e20), "ema50": _r(e50), "vwap": _r(vwap) if vwap else None,
        "volume_ratio": _r(vol_ratio) if vol_ratio is not None else None,
        "support": _r(support["price"]) if support else None,
        "resistance": _r(resistance["price"]) if resistance else None,
        "news_score": news_score,
        "news_headlines": (news or {}).get("headlines", [])[:3],
        "fundamentals_score": fundamentals_score,
        "fundamentals_label": (fundamentals or {}).get("label"),
        "bar_time": last["time"],
        "entry_day": day,
        "entries_today": entries_today,
        "entry_mode": p["entry_mode"],
        "checklist": {"long": cl_long, "short": cl_short},
        "cpr": {k: _r(v) for k, v in cpr.items()} if cpr else None,
    }
    return signal, new_state


trader_brain_signal.uses_news = True
trader_brain_signal.uses_fundamentals = True
