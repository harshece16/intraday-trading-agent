"""
Trader Brain — a confluence strategy that encodes the checklist a
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
  8. Discipline: no entries in the opening 15 min or late in the session,
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
    "adx_trend": 25,
    "adx_range": 20,
    "htf_factor": 3,
    "use_news": True,
    "news_weight": 2.0,
    "news_veto": -0.5,
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


def trader_brain_signal(candles, prev_state=None, news=None, **params):
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

    # Higher timeframe
    if htf_trend == "up":
        bull.add("htf", 1.5, "15-min trend is up")
        bear.add("htf", -1.0, "Bearish case fights the 15-min uptrend")
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

    # 6. Volume
    if vol_ratio is not None:
        if vol_ratio >= 1.5 and up_bar:
            bull.add("volume", 1.0, f"Volume {vol_ratio:.1f}x average on an up bar")
        elif vol_ratio >= 1.5 and down_bar:
            bear.add("volume", 1.0, f"Volume {vol_ratio:.1f}x average on a down bar")
        elif vol_ratio < 0.6:
            bull.add("volume", -0.5, "Thin volume — weak conviction")

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

    # 5. Candlestick triggers, weighted by location
    at_value = near_support or abs(last["low"] - e20) <= 0.5 * atr_v or (vwap and abs(last["low"] - vwap) <= 0.5 * atr_v)
    at_top = near_resistance or (vwap and abs(last["high"] - vwap) <= 0.5 * atr_v)
    for pat in patterns:
        if pat["bias"] == "bullish":
            pts = pat["strength"] * (1.0 if at_value else 0.5)
            bull.add("pattern", pts, f"{pat['name']}" + (" at a value area" if at_value else " (no level context)"))
        elif pat["bias"] == "bearish":
            pts = pat["strength"] * (1.0 if at_top else 0.5)
            bear.add("pattern", pts, f"{pat['name']}" + (" at resistance" if at_top else " (no level context)"))

    # 7. News
    news_score = None
    veto = False
    if news and p["use_news"]:
        news_score = news.get("score", 0.0)
        if news_score > 0.15:
            bull.add("news", news_score * p["news_weight"], f"Positive news sentiment ({news_score:+.2f})")
        elif news_score < -0.15:
            bear.add("news", -news_score * p["news_weight"], f"Negative news sentiment ({news_score:+.2f})")
        if news_score <= p["news_veto"]:
            veto = True

    # 8. Decision with discipline rules
    hhmm = last["time"][11:16]
    in_entry_window = p["no_entry_before"] <= hhmm < p["last_entry_time"]
    exit_long = bear.total >= p["exit_threshold"] or (price < e50 and structure == "downtrend") or veto
    long_ok = (
        in_entry_window and not veto and not exit_long
        and bull.total >= p["entry_threshold"]
        and len(bull.categories) >= p["min_confirmations"]
        and bull.total - bear.total >= p["min_edge"]
    )

    signal = None
    if long_ok and not prev_state.get("long_ok"):
        signal = "BUY"
    elif exit_long and not prev_state.get("exit_long"):
        signal = "SELL"

    if brk_up:
        setup = "Breakout"
    elif regime == "ranging" and (rsi_v <= 40 or near_support):
        setup = "Range reversal"
    elif price > e20 > e50 and abs(last["low"] - e20) <= 0.5 * atr_v:
        setup = "Trend pullback"
    elif bull.total >= bear.total:
        setup = "Bullish confluence"
    else:
        setup = "Bearish pressure"

    blockers = []
    if not in_entry_window:
        blockers.append(f"Outside entry window ({p['no_entry_before']}–{p['last_entry_time']})")
    if veto:
        blockers.append("Strongly negative news — standing aside")
    if bull.total < p["entry_threshold"]:
        blockers.append(f"Bull score {bull.total:.1f} below {p['entry_threshold']}")
    if len(bull.categories) < p["min_confirmations"]:
        blockers.append(f"Only {len(bull.categories)} confirming categories (need {p['min_confirmations']})")

    new_state = {
        "long_ok": long_ok,
        "exit_long": exit_long,
        "setup": setup,
        "regime": regime,
        "structure": structure,
        "htf_trend": htf_trend,
        "bull_score": _r(bull.total),
        "bear_score": _r(bear.total),
        "entry_threshold": p["entry_threshold"],
        "exit_threshold": p["exit_threshold"],
        "confirmations": bull.categories,
        "reasons": bull.reasons(6),
        "bear_reasons": bear.reasons(4),
        "blockers": [] if long_ok else blockers,
        "patterns": [{"name": x["name"], "bias": x["bias"]} for x in patterns],
        "rsi": _r(rsi_v, 1), "adx": _r(adx, 1), "atr": _r(atr_v),
        "ema20": _r(e20), "ema50": _r(e50), "vwap": _r(vwap) if vwap else None,
        "volume_ratio": _r(vol_ratio) if vol_ratio is not None else None,
        "support": _r(support["price"]) if support else None,
        "resistance": _r(resistance["price"]) if resistance else None,
        "news_score": news_score,
        "news_headlines": (news or {}).get("headlines", [])[:3],
        "bar_time": last["time"],
    }
    return signal, new_state


trader_brain_signal.uses_news = True
