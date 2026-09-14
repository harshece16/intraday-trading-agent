"""
Assembles the dashboard's Technical Analysis reference page from the actual
constants the engine trades on — not a hand-written description that could
drift out of sync with the code. Every citation string, pattern name, and
statistic here is imported from the module that uses it live.
"""

import brooks
import bulkowski
import candlestick_patterns
import config
import evaluation
import fno_risk  # noqa: F401 — imported so this module errors loudly if that one breaks
import llm_sentiment
import market_structure
import news_sentiment
import options_pricing  # noqa: F401 — same
import risk_manager  # noqa: F401 — same
import swing_patterns  # noqa: F401 — same
import trader_brain


def get_methods():
    p = trader_brain.DEFAULTS
    return {
        "checklist": {
            "title": "The Varsity Grand Checklist — decides WHEN to trade",
            "intro": f"A trade needs every required point. Threshold to enter: "
                     f"{p['entry_threshold']} points, at least {p['min_confirmations']} agreeing categories, "
                     f"a {p['min_edge']}-point edge over the opposite case, and a reward-to-risk of at least "
                     f"{p['min_rrr']}. Indicators and the news catalyst only resize the trade "
                     f"({p['indicator_miss_size']:.0%} on a miss), they don't block it.",
            "rules": [
                {"key": k, "source": v} for k, v in trader_brain.CHECKLIST_SOURCES.items()
            ],
        },
        "candlestick_patterns": {
            "title": "Candlestick patterns",
            "source": "Nison, Japanese Candlestick Charting Techniques; conditioned on the prior trend per Varsity Technical Analysis ch 4-10",
            "note": "A pattern only counts in context — the same shape after a decline is a hammer, "
                    "after a rally it's a hanging man. Noise bars (range under 0.3x ATR) are ignored.",
            "count": len(candlestick_patterns.PATTERN_NAMES),
            "names": candlestick_patterns.PATTERN_NAMES,
        },
        "daily_patterns": {
            "title": "Daily-chart reversal patterns (scanner only, not the intraday checklist)",
            "source": bulkowski.SOURCE,
            "note": "Measured on US stocks, daily charts — used here as a directional weight on the "
                    "scanner's daily setup score, never assumed to transfer to this market or timeframe.",
            "patterns": [
                {
                    "name": name, "bias": stats["bias"], "rank": stats["rank"],
                    "bull_failure_rate_pct": stats["bull"]["failure_rate_pct"],
                    "bull_avg_move_pct": stats["bull"]["avg_move_pct"],
                    "bear_failure_rate_pct": stats["bear"]["failure_rate_pct"],
                    "bear_avg_move_pct": stats["bear"]["avg_move_pct"],
                }
                for name, stats in bulkowski.PATTERN_STATS.items()
            ],
        },
        "reversal_days": {
            "title": "Reversal days (scanner only)",
            "source": "Murphy, Technical Analysis of the Financial Markets, ch 4",
            "note": "A new high (low) for the move followed by a lower (higher) close than the prior day. "
                    "Heavier volume (a 'selling climax' at a bottom) and an outside day both add weight. "
                    "A warning sign folded into the scanner's daily score, never a trigger by itself.",
        },
        "volume_confirmation": {
            "title": "On Balance Volume divergence (intraday checklist, volume category)",
            "source": "Granville (1963), per Murphy, Technical Analysis of the Financial Markets, ch 7",
            "note": "The OBV line — cumulative volume signed by each bar's close direction — should move "
                    "the same way as price. When it doesn't over a look-back window, that's an early warning "
                    "the move lacks real participation, ahead of what one bar's volume ratio alone can show.",
        },
        "gaps": {
            "title": "Gap classification (scanner only)",
            "source": bulkowski.GAP_SOURCE,
            "note": "% of gaps of each type that close (price returns and spans the gap) within a week — "
                    "low means persistent (a real signal), high means it usually just fills.",
            "close_within_week_pct": bulkowski.GAP_CLOSE_WITHIN_WEEK_PCT,
        },
        "trend": {
            "title": "Trend and structure",
            "rules": [
                {"name": "Dow Theory — higher highs & higher lows", "source": "Varsity Technical Analysis ch 17-18"},
                {"name": "Always-in direction — price vs 20-EMA and trend-bar majority",
                 "source": "Brooks, Trading Price Action Trends (glossary: trend bar, always-in)"},
                {"name": "Higher-timeframe filter — 5-minute bars resampled to 15-minute",
                 "source": "Multi-timeframe analysis, general TA practice"},
            ],
        },
        "levels": {
            "title": "Support, resistance and other reference levels",
            "rules": [
                {"name": "Swing highs/lows clustered within 0.5 ATR", "source": "Price action / Varsity Technical Analysis ch 11"},
                {"name": "Previous day's high, low and close", "source": "Varsity Technical Analysis ch 11"},
                {"name": "Opening range (first 15 minutes)", "source": "Intraday trading practice"},
                {"name": f"Fibonacci retracement — {', '.join(f'{r * 100:g}%' for r in market_structure.FIB_RATIOS)}",
                 "source": "Varsity Technical Analysis ch 16"},
                {"name": "Central Pivot Range — pivot, top (TC), bottom (BC)", "source": "Varsity Technical Analysis ch 22"},
            ],
        },
        "momentum": {
            "title": "Momentum and volatility indicators",
            "source": "Varsity Technical Analysis ch 13-16",
            "names": ["EMA (20/50)", "RSI (14)", "MACD (12/26/9)", "Bollinger Bands (20, 2 SD)",
                      "ADX / +DI / -DI (Wilder, 14)", "Stochastic (14, 3)", "ATR (14)"],
        },
        "news": {
            "title": "News and catalysts",
            "note": "Headlines must actually name the company. Scored by an LLM reading the actual "
                    "article text (Claude Haiku) when that's configured and its daily budget allows, "
                    "an India-tuned finance lexicon otherwise, or the source's own sentiment when it "
                    "supplies one — weighted by source trust and recency. The LLM path is never assumed "
                    "to help just because it exists: database.factor_ic() measures whether the resulting "
                    "score actually predicts anything, the same honesty check applied everywhere else.",
            "llm_sentiment": llm_sentiment.stats(),
            "sources": [{"name": k, "weight": v} for k, v in news_sentiment.SOURCE_WEIGHT.items()],
        },
        "risk": {
            "title": "Position sizing and evaluation",
            "rules": [
                {"name": "Percent Risk Model — risk % of capital / stop distance",
                 "source": "Van Tharp, Trade Your Way to Financial Freedom, ch 9 (Model 3)"},
                {"name": "Percent Volatility Model — ATR-based stop distance",
                 "source": "Van Tharp, Trade Your Way to Financial Freedom, ch 9 (Model 4)"},
                {"name": "R-multiples, expectancy, Kelly fraction",
                 "source": "Van Tharp, Trade Your Way to Financial Freedom, ch 6, 11-14"},
                {"name": "Deflated Sharpe Ratio — corrects for how many backtests have been tried",
                 "source": "Bailey & López de Prado (2014), cited in Jansen, Machine Learning for Trading, ch 1"},
                {"name": "Information Coefficient — does a score rank stocks by what they do next?",
                 "source": "Grinold's fundamental law of active management, cited in Jansen, Machine Learning for Trading, ch 1"},
            ],
        },
        "fno": {
            "title": f"F&O (options-buying only) — {'ON' if config.FNO['enabled'] else 'OFF'}",
            "source": "NISM Series VIII, Equity Derivatives workbook",
            "note": f"Buys calls on a LONG signal, puts on a SHORT signal — same checklist, capped-risk "
                    f"instrument. Writing/selling and futures are deliberately excluded: NISM's own text says "
                    f"a long option's maximum loss is the premium paid, full stop, while a short call's "
                    f"maximum loss 'has to be unlimited' — a fundamentally different risk shape from everything "
                    f"else this codebase sizes to a known, bounded loss. Greeks (Delta, Gamma, Theta, Vega) use "
                    f"NISM's own definitions, computed via Black-Scholes-Merton with volatility solved from the "
                    f"contract's live premium (Kite gives OHLC + OI for F&O, not IV directly). "
                    f"Ring-fenced to ₹{config.FNO['capital']:,.0f} of capital, max "
                    f"{config.FNO['max_premium_risk_pct']:.0f}% of that per trade (the entire premium risked), "
                    f"gated by a per-trade confidence score that's capped low whenever the Dimaag Scorecard "
                    f"hasn't proven a real system-wide edge yet — see the Journal page.",
            "rules": [
                {"name": "Delta — premium change per unit move in the underlying", "source": "NISM Series VIII"},
                {"name": "Gamma — change in delta per unit move (delta's own speed)", "source": "NISM Series VIII"},
                {"name": "Theta — premium change per day closer to expiry (time decay)", "source": "NISM Series VIII"},
                {"name": "Vega — premium change per 1-point change in volatility", "source": "NISM Series VIII"},
                {"name": "Black-Scholes-Merton pricing + implied-volatility solve",
                 "source": "Black & Scholes (1973); Merton (1973) — standard industry model, not NSE-specific"},
                {"name": "Expiry >= 5 days out only (avoids the sharpest theta decay window)",
                 "source": "NISM Series VIII + Murphy on time decay"},
            ],
        },
        "not_yet_used": {
            "title": "Read, but not (yet) built in",
            "items": [
                {"name": "Murphy, Technical Analysis of the Financial Markets — Elliott Wave, Point & Figure, "
                         "time cycles, intermarket analysis (bonds/dollar/commodities), and market-breadth "
                         "indicators (advance-decline line, McClellan Oscillator, TRIN)",
                 "reason": "Read in full (OCR'd — the PDF is a scanned book with no text layer; tesseract and "
                           "poppler were installed this session to read it). Reversal days and On Balance "
                           "Volume divergence (ch 4 and ch 7) are concrete, verifiable rules and are now wired "
                           "into the scanner and checklist above. The rest is either too subjective to encode "
                           "reliably (Elliott Wave's wave-counting requires judgment calls Murphy himself says "
                           "trained analysts disagree on), redundant with what's already implemented (Point & "
                           "Figure vs. the candlestick/bar-chart patterns already in place), needs data this "
                           "system doesn't fetch (market-breadth needs every NSE constituent, not just the "
                           "watchlist), or doesn't apply to a single-stock intraday cash strategy (intermarket "
                           "analysis is built for cross-asset macro trading)."},
                {"name": "NISM Series VIII (Equity Derivatives) workbook — the parts not yet used",
                 "reason": "Read in full. Its Greeks and long-option payoff definitions now power the F&O "
                           "section above. Still not built in: SPAN margining (this engine never writes/sells "
                           "options, so it never posts margin), and the Market Wide Position Limit ban — NSE "
                           "penalises INCREASING a position once market-wide F&O open interest in a stock "
                           "crosses its limit (1% of value, ₹5,000-₹1,00,000 penalty), which could in principle "
                           "block a new option-buy too. There's no live MWPL-status check in code yet — a real "
                           "gap if F&O volume grows, not something to assume away."},
                {"name": "Gradient boosting, deep time series, autoencoders, GANs, reinforcement learning, "
                         "RAG/knowledge graphs (Jansen, Machine Learning for Trading, ch 9-24)",
                 "reason": "Need thousands of examples or months of history; a week of paper trading isn't "
                           "in range. See research/ml4t_integration_plan.md for the full reasoning."},
            ],
        },
    }
