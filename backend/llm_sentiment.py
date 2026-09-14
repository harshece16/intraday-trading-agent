"""
LLM-read news sentiment — the one LLM integration in this codebase, and
deliberately narrow: it reads a headline's actual text (catching negation,
sarcasm, and which company a multi-company article is really about, which
the keyword lexicon in sentiment_lexicon.py can miss) and returns a
sentiment score in the same [-1, 1] range that lexicon already returns.

This is NOT a price predictor. It does not see a chart, a candle, or a
number that hasn't already happened. It reads one piece of text and scores
its tone toward the company, the same narrow task a human analyst skimming
headlines does — nothing here claims to know what the stock will do next.

Whether reading news this way actually helps is not assumed — it goes
through the same honesty check as everything else: Information Coefficient
(database.factor_ic()) is computed on the scanner's live score regardless of
which sentiment source fed it, so if LLM-read sentiment doesn't improve on
what the lexicon already gave, that will show up there, not just here.

Falls back to the lexicon (never blocks scoring) on any error, missing key,
parse failure, or once the daily call budget is used up.
"""

import hashlib
import json
import logging
import re
import threading
import time
from datetime import datetime, timezone

import config

logger = logging.getLogger("trading_bot")

MODEL = "claude-haiku-4-5-20251001"
# Verified against anthropic.com/claude/haiku on 2026-09-14 — re-check if it's
# been a while, Anthropic can change pricing. Applied to the real input/output
# token counts each API response reports, not an estimate.
PRICE_PER_M_INPUT_USD = 1.0
PRICE_PER_M_OUTPUT_USD = 5.0
SYSTEM_PROMPT = (
    "You score financial news headlines for how they read for a specific listed company's share "
    "price — nothing else. Reply with ONLY a JSON object: {\"score\": <number from -1 to 1>}. "
    "-1 is severely negative (fraud, insolvency, a large earnings miss), 0 is neutral or not really "
    "about this company, 1 is severely positive (a large order win, a big earnings beat). Account for "
    "negation (\"fails to win order\" is negative) and read past hedging language for the real tone. "
    "Output nothing but the JSON object, no explanation."
)

_client = None
_cache = {}  # headline hash -> score; headlines don't change once published, so no TTL needed
_budget = {"date": None, "used": 0, "input_tokens": 0, "output_tokens": 0}
_lock = threading.Lock()


def _reset_budget_if_new_day():
    today = datetime.now(timezone.utc).date()
    if _budget["date"] != today:
        _budget.update(date=today, used=0, input_tokens=0, output_tokens=0)


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=config.NEWS["anthropic_api_key"])
    return _client


def _allowed():
    if not config.NEWS.get("anthropic_api_key") or not config.NEWS.get("use_llm_sentiment"):
        return False
    with _lock:
        _reset_budget_if_new_day()
        if _budget["used"] >= config.NEWS.get("llm_daily_limit", 500):
            return False
        _budget["used"] += 1
        return True


def _cache_key(title, summary):
    return hashlib.sha256(f"{title}|{summary or ''}".encode()).hexdigest()


def score_headline(title, summary=None):
    """Returns a float in [-1, 1], or None if the LLM path is unavailable
    right now (disabled, no key, budget spent, or the call failed) — callers
    fall back to sentiment_lexicon.score_text() in that case, exactly as
    they already fall back when a source has no built-in score."""
    if not title:
        return None
    key = _cache_key(title, summary)
    if key in _cache:
        return _cache[key]
    if not _allowed():
        return None
    try:
        resp = _get_client().messages.create(
            model=MODEL, max_tokens=30, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Headline: {title}\nSummary: {summary or '(none)'}"}],
        )
        with _lock:
            _reset_budget_if_new_day()
            _budget["input_tokens"] += resp.usage.input_tokens
            _budget["output_tokens"] += resp.usage.output_tokens
        text = resp.content[0].text.strip()
        match = re.search(r"-?\d*\.?\d+", text)
        if not match:
            raise ValueError(f"no number in response: {text!r}")
        score = max(-1.0, min(1.0, float(match.group())))
    except Exception as exc:
        logger.warning(f"LLM sentiment failed for {title[:60]!r}: {exc}")
        return None
    _cache[key] = score
    return score


def stats():
    """For the dashboard's live usage check — real token counts the API
    itself reported today, and the cost those actually imply at Haiku 4.5's
    published rate (not an estimate from call count x an assumed size)."""
    with _lock:
        _reset_budget_if_new_day()
        used, in_tok, out_tok = _budget["used"], _budget["input_tokens"], _budget["output_tokens"]
    cost = in_tok / 1e6 * PRICE_PER_M_INPUT_USD + out_tok / 1e6 * PRICE_PER_M_OUTPUT_USD
    return {
        "enabled": bool(config.NEWS.get("use_llm_sentiment")), "configured": bool(config.NEWS.get("anthropic_api_key")),
        "used_today": used, "daily_limit": config.NEWS.get("llm_daily_limit", 500),
        "cached_headlines": len(_cache),
        "input_tokens_today": in_tok, "output_tokens_today": out_tok,
        "estimated_cost_usd_today": round(cost, 4),
        "estimated_cost_usd_at_daily_limit": round(
            config.NEWS.get("llm_daily_limit", 500) * (in_tok / used * PRICE_PER_M_INPUT_USD
            + out_tok / used * PRICE_PER_M_OUTPUT_USD) / 1e6, 2) if used else None,
    }


def set_enabled(enabled: bool):
    """Runtime on/off toggle — separate from whether a key is even configured,
    same pattern as config.FNO['enabled'] (app.py's POST /api/fno/enable)."""
    config.NEWS["use_llm_sentiment"] = bool(enabled)
    return config.NEWS["use_llm_sentiment"]
