"""
Thomas Bulkowski, *Encyclopedia of Chart Patterns* (2nd ed.) — measured
statistics for classical daily-chart reversal patterns, from his own
"Results Snapshot" tables (thousands of patterns, US stocks, mostly
1991-recent, before this edition's 2005 printing). These numbers describe
multi-week patterns on DAILY bars, not 5-minute candles — a fair swing-
trading signal at the timeframe the scanner already looks at (daily trend,
relative strength), not evidence for intraday pattern trading. Used here to
add a cited, evidence-weighted swing signal to the scanner, never assumed to
transfer to a different market or timeframe.

Also includes his Gaps chapter stats: how often each gap type closes
(price returns and spans it) within a week — the closest thing in the book
to an intraday-relevant, quantified rule.
"""

# {pattern: {bull: {failure_rate_pct, avg_move_pct, pullback_or_throwback_pct}, bear: {...}}}
# avg_move_pct is the average rise (bullish patterns) or decline (bearish patterns).
PATTERN_STATS = {
    "Double Bottom": {
        "bias": "bullish", "rank": "10 of 23 (bull), 10 of 19 (bear)",
        "bull": {"failure_rate_pct": 5, "avg_move_pct": 35, "retrace_pct": 64},
        "bear": {"failure_rate_pct": 7, "avg_move_pct": 24, "retrace_pct": 61},
    },
    "Double Top": {
        "bias": "bearish", "rank": "4 of 21 (bull), 17 of 21 (bear)",
        "bull": {"failure_rate_pct": 8, "avg_move_pct": 19, "retrace_pct": 61},
        "bear": {"failure_rate_pct": 11, "avg_move_pct": 19, "retrace_pct": 48},
    },
    "Head and Shoulders Bottom": {
        "bias": "bullish", "rank": "7 of 23 (bull), 6 of 19 (bear)",
        "bull": {"failure_rate_pct": 3, "avg_move_pct": 38, "retrace_pct": 45},
        "bear": {"failure_rate_pct": 4, "avg_move_pct": 30, "retrace_pct": 51},
    },
    "Head and Shoulders Top": {
        "bias": "bearish", "rank": "1 of 21 (bull), 6 of 21 (bear)",
        "bull": {"failure_rate_pct": 4, "avg_move_pct": 22, "retrace_pct": 50},
        "bear": {"failure_rate_pct": 1, "avg_move_pct": 29, "retrace_pct": 64},
    },
}

SOURCE = "Bulkowski, Encyclopedia of Chart Patterns — Results Snapshot (US stocks, daily charts)"

# Gaps chapter: % of gaps that close (price returns and spans the gap) within a week.
# Low = persistent (a real signal); high = fills fast (usually just noise or exhaustion).
GAP_CLOSE_WITHIN_WEEK_PCT = {
    "area": 91, "breakaway": 5, "continuation": 12, "exhaustion": 70,
}
GAP_SOURCE = "Bulkowski, Encyclopedia of Chart Patterns, ch 23 'Gaps'"


def classify_gap(gap_pct, daily_trend, pct_from_high, pct_from_low, atr_pct):
    """A rough classification along Bulkowski's four gap types, using only
    daily context already computed by the scanner (no formal trendline
    fit): breakaway (starts a new trend, near a 52-week extreme, larger than
    typical daily range), exhaustion (gaps further in an already-extended
    trend — likely to fail and fill), continuation (mid-trend, unremarkable),
    area (small, inside a range). Returns (kind, close_within_week_pct)."""
    if abs(gap_pct) < 0.5:
        return "area", GAP_CLOSE_WITHIN_WEEK_PCT["area"]
    trend_agrees = (gap_pct > 0 and daily_trend == "up") or (gap_pct < 0 and daily_trend == "down")
    near_extreme = pct_from_high <= 5 if gap_pct > 0 else pct_from_low <= 5
    large = abs(gap_pct) >= 1.5 * max(atr_pct, 0.1)
    if trend_agrees and near_extreme and large:
        return "breakaway", GAP_CLOSE_WITHIN_WEEK_PCT["breakaway"]
    if trend_agrees and (pct_from_high > 15 and pct_from_low > 15):
        return "exhaustion", GAP_CLOSE_WITHIN_WEEK_PCT["exhaustion"]
    return "continuation", GAP_CLOSE_WITHIN_WEEK_PCT["continuation"]


def pattern_target(name, price, stop, side, regime="bull"):
    """A target and confidence note from Bulkowski's measured average move for
    this exact pattern, when we have it — otherwise None (caller falls back
    to its own target rule)."""
    stats = PATTERN_STATS.get(name)
    if not stats:
        return None
    s = stats.get(regime, stats["bull"])
    move_pct = s["avg_move_pct"] / 100
    target = price * (1 + move_pct) if side == "long" else price * (1 - move_pct)
    return {
        "target": target, "failure_rate_pct": s["failure_rate_pct"], "avg_move_pct": s["avg_move_pct"],
        "retrace_pct": s["retrace_pct"], "rank": stats["rank"], "source": SOURCE,
    }
