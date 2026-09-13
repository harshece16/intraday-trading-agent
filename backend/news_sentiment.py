"""
News sentiment from free Yahoo Finance headlines, scored with a
finance-specific lexicon (earnings beats/misses, rating changes, order wins,
regulatory probes, promoter pledges, ...).

Recent headlines count more (12h half-life), headlines that actually name the
company count more than loosely related ones, and results are cached per
symbol so the 30s engine loop doesn't hammer Yahoo. Any failure returns a
neutral score — news is supporting evidence, never a reason to crash.

Lexicon scoring is crude next to a real NLP model: it can't read sarcasm,
context, or "priced in". Treat it as a tilt, not a signal on its own.
"""

import logging
import math
import re
import time
from datetime import datetime, timezone

logger = logging.getLogger("trading_bot")

CACHE_TTL_SECONDS = 900
HALF_LIFE_HOURS = 12
MAX_AGE_HOURS = 72

# Yahoo headlines usually use the company name, not the NSE ticker.
ALIASES = {
    "RELIANCE": ["reliance"],
    "TCS": ["tcs", "tata consultancy"],
    "INFY": ["infosys"],
    "HDFCBANK": ["hdfc bank"],
    "ICICIBANK": ["icici bank"],
    "SBIN": ["sbi", "state bank of india"],
    "BHARTIARTL": ["airtel", "bharti"],
    "ITC": ["itc"],
    "LT": ["larsen", "l&t"],
    "HINDUNILVR": ["hindustan unilever", "hul"],
}

POSITIVE = {
    "beats estimates": 2.0, "beat estimates": 2.0, "tops estimates": 2.0, "beats": 1.0,
    "record profit": 2.0, "record revenue": 1.5, "profit rises": 1.5, "profit jumps": 1.5,
    "profit surges": 1.8, "revenue growth": 1.0, "margin expansion": 1.2,
    "upgrade": 1.5, "upgraded": 1.5, "upgrades": 1.5, "outperform": 1.0, "overweight": 0.8,
    "buy rating": 1.2, "target raised": 1.2, "raises target": 1.2,
    "raises guidance": 1.8, "raises outlook": 1.8,
    "order win": 1.5, "wins order": 1.5, "bags order": 1.5, "secures order": 1.5, "contract win": 1.3,
    "buyback": 1.3, "bonus issue": 1.0, "dividend": 0.6, "stake increase": 0.8,
    "acquisition": 0.6, "acquires": 0.6, "partnership": 0.5, "expansion": 0.6, "approval": 0.8,
    "strong demand": 1.0, "debt free": 1.0, "deleveraging": 0.8,
    "surge": 1.0, "surges": 1.0, "soars": 1.0, "rallies": 0.8, "jumps": 0.8, "gains": 0.5,
    "record high": 0.8, "all-time high": 0.8, "bullish": 0.8,
}

NEGATIVE = {
    "misses estimates": 2.0, "miss estimates": 2.0, "misses": 1.0,
    "profit falls": 1.5, "profit drops": 1.5, "profit declines": 1.5, "net loss": 1.5, "loss widens": 1.8,
    "margin pressure": 1.0, "weak demand": 1.0, "headwinds": 0.8,
    "downgrade": 1.5, "downgraded": 1.5, "downgrades": 1.5, "underperform": 1.0, "underweight": 0.8,
    "sell rating": 1.2, "target cut": 1.2, "cuts target": 1.2,
    "cuts guidance": 1.8, "lowers guidance": 1.8, "cuts outlook": 1.8,
    "probe": 1.3, "investigation": 1.2, "raid": 1.5, "fraud": 2.0, "scam": 2.0,
    "penalty": 1.2, "sebi order": 1.0, "ban": 1.0, "lawsuit": 1.0, "default": 1.5,
    "resigns": 1.0, "resignation": 1.0, "pledge": 0.8, "stake sale": 0.8,
    "layoffs": 0.8, "strike": 0.8, "recall": 1.0, "outage": 0.8, "warning": 0.8,
    "plunge": 1.2, "plunges": 1.2, "slumps": 1.0, "tumbles": 1.0, "crash": 1.5, "falls": 0.5,
    "bearish": 0.8,
}

_NEGATORS = r"(?:not|no|fails to|failed to|didn't|did not)\s+"
_cache = {}


def _score_text(text):
    text = text.lower()
    raw = 0.0
    for lexicon, sign in ((POSITIVE, 1), (NEGATIVE, -1)):
        for phrase in sorted(lexicon, key=len, reverse=True):
            pattern = r"\b" + re.escape(phrase) + r"\b"
            negated = len(re.findall(_NEGATORS + pattern, text))
            total = len(re.findall(pattern, text))
            if total:
                raw += sign * lexicon[phrase] * (total - 2 * negated)
                text = re.sub(pattern, " ", text)
    return math.tanh(raw / 2)


def _parse_item(item):
    content = item.get("content", item)
    title = content.get("title") or ""
    summary = content.get("summary") or content.get("description") or ""
    published = None
    if content.get("pubDate"):
        try:
            published = datetime.fromisoformat(content["pubDate"].replace("Z", "+00:00"))
        except ValueError:
            pass
    elif item.get("providerPublishTime"):
        published = datetime.fromtimestamp(item["providerPublishTime"], tz=timezone.utc)
    return title, summary, published


def _fetch(symbol):
    import yfinance as yf
    ticker = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
    return yf.Ticker(ticker).news or []


def get_sentiment(symbol):
    cached = _cache.get(symbol)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    result = {"score": 0.0, "count": 0, "headlines": []}
    try:
        items = _fetch(symbol)
        names = [symbol.lower()] + ALIASES.get(symbol.upper(), [])
        now = datetime.now(timezone.utc)
        weighted = weight_sum = 0.0
        scored = []
        for item in items:
            title, summary, published = _parse_item(item)
            if not title:
                continue
            age_h = (now - published).total_seconds() / 3600 if published else 24.0
            if age_h > MAX_AGE_HOURS:
                continue
            text = f"{title}. {summary}"
            relevance = 1.0 if any(re.search(r"\b" + re.escape(n) + r"\b", text.lower()) for n in names) else 0.4
            s = _score_text(text)
            w = relevance * 0.5 ** (age_h / HALF_LIFE_HOURS)
            weighted += w * s
            weight_sum += w
            scored.append({"title": title, "score": round(s, 2), "age_h": round(age_h, 1)})

        if weight_sum > 0:
            # Scale by evidence mass so one stale, loosely related headline can't dominate.
            result["score"] = round(max(-1.0, min(1.0, weighted / weight_sum * min(1.0, weight_sum / 1.5))), 3)
        result["count"] = len(scored)
        result["headlines"] = sorted(scored, key=lambda h: h["age_h"])[:5]
    except Exception as exc:
        logger.warning(f"News sentiment unavailable for {symbol}: {exc}")
        result["error"] = str(exc)

    _cache[symbol] = (time.time(), result)
    return result
