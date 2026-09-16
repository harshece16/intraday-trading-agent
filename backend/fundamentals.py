"""
Company-quality fundamentals — real financial ratios (ROE, operating margin,
PEG, debt/equity) fetched live via Yahoo Finance, same yfinance dependency
and "<SYMBOL>.NS" ticker convention already used by news_sentiment.py's
_yahoo(). Field scales verified against live data (TCS: returnOnEquity and
operatingMargins are plain 0-1 ratios; debtToEquity is Yahoo's own
percent-scaled convention, so it's divided by 100 here to get an actual
ratio — confirmed sane against TCS's real near-zero debt profile).

This is the genuine "fundamental side of the checklist" that
trader_brain.py's "catalyst" criterion has always claimed to cover but, in
practice, only ever carried news sentiment for (see
CHECKLIST_SOURCES["catalyst"] there).

Scored against the conventional Peter Lynch / Graham-style value & quality
screening thresholds also covered qualitatively in Zerodha Varsity's
Fundamental Analysis module — a documented heuristic weight, not something
this app has itself IC/DSR-validated (same status as news_weight; see the
README's "validate before trusting a new signal" process, issue #12).

A stock missing a given metric on Yahoo just skips that one criterion —
never guessed. All-missing returns score=None ("not enough data"), the same
convention used everywhere else in this app (e.g. the Dimaag Scorecard).

get_fundamentals(symbol) is cached 24h: these ratios move on quarterly
results, not intraday, so a long TTL avoids hammering Yahoo on every scan.
"""

import logging
import threading
import time

logger = logging.getLogger("trading_bot")

CACHE_TTL_SECONDS = 86400  # 24h — quarterly fundamentals, not intraday data

THRESHOLDS = {
    "roe": {"good": 0.15, "poor": 0.08, "label": "Return on equity", "pct": True},
    "operating_margin": {"good": 0.15, "poor": 0.05, "label": "Operating margin", "pct": True},
    "debt_to_equity": {"good": 1.0, "poor": 2.0, "label": "Debt/equity", "lower_is_better": True},
    "peg_ratio": {"good": 1.5, "poor": 3.0, "label": "PEG ratio", "lower_is_better": True, "positive_only": True},
}

_cache = {}
_lock = threading.Lock()


def _score_metric(key, value):
    t = THRESHOLDS[key]
    if value is None:
        return None
    if t.get("positive_only") and value <= 0:
        return None
    lower_is_better = t.get("lower_is_better", False)
    good = value <= t["good"] if lower_is_better else value >= t["good"]
    poor = value >= t["poor"] if lower_is_better else value <= t["poor"]
    points, ok = (1.0, True) if good else (-1.0, False) if poor else (0.0, True)
    shown = f"{value * 100:.1f}%" if t.get("pct") else f"{value:.2f}"
    return {"key": key, "label": t["label"], "value": value, "points": points, "ok": ok,
            "text": f"{t['label']} {shown}"}


def _fetch_ratios(symbol):
    import yfinance as yf
    info = yf.Ticker(f"{symbol}.NS").get_info()
    dte = info.get("debtToEquity")
    return {
        "roe": info.get("returnOnEquity"),
        "operating_margin": info.get("operatingMargins"),
        "debt_to_equity": dte / 100 if dte is not None else None,
        "peg_ratio": info.get("trailingPegRatio") or info.get("pegRatio"),
    }


def get_fundamentals(symbol):
    """Real ROE/margin/PEG/debt-equity for `symbol`, scored -4..+4, cached 24h.
    Returns {"score": None, "label": "Not enough data", ...} when Yahoo has
    none of these fields for the stock, rather than guessing a value."""
    key = symbol.upper()
    with _lock:
        cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    try:
        raw = _fetch_ratios(key)
    except Exception as exc:
        logger.warning(f"Fundamentals failed for {key}: {exc}")
        raw = {}

    metrics = [m for m in (_score_metric(k, raw.get(k)) for k in THRESHOLDS) if m is not None]
    if not metrics:
        result = {"score": None, "label": "Not enough data", "metrics": [], "raw": raw}
    else:
        score = sum(m["points"] for m in metrics)
        label = "Strong" if score >= 1.5 else "Weak" if score <= -1.5 else "Mixed"
        result = {"score": score, "label": label, "metrics": metrics, "raw": raw}

    with _lock:
        _cache[key] = (time.time(), result)
    return result
