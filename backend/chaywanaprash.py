"""
Chaywanaprash — Sahab's own research analyst (chyawanprash, the Ayurvedic
general-strengthening tonic; same naming spirit as Trader Sahab / Sahab's
Dimaag / the Varsity Grand Checklist). Where Sahab's Dimaag scores one
trade, Chaywanaprash looks at the platform itself: it pulls real,
structured stats out of the same journal database every other part of
this system already writes to (checklist_evals, activity, trades — see
database.checklist_blocker_stats() and recent_activity_issues()) and, when
an Anthropic API key is configured, asks Claude to read those real numbers
and propose concrete, evidence-backed improvements.

Same discipline as everywhere else in this codebase: never fabricate.
With no API key configured, or the daily call budget spent, it still
returns the raw computed stats — clearly labeled as ungenerated — rather
than inventing a narrative. And it is deliberately read-only: it never
edits config.py, trader_brain.py, or anything else. It produces a report
a human reads and decides on, the same loop this project has followed for
every other change this session — find something real, report it,
implement only once asked.
"""

import logging
import threading
from datetime import datetime, timezone

import config
import database

logger = logging.getLogger("trading_bot")

MODEL = "claude-sonnet-5"
# A rarer, heavier, on-demand call than llm_sentiment.py's per-headline
# scoring — worth the flagship model. Verified against anthropic.com/claude
# pricing on 2026-09-15; re-check if it's been a while.
PRICE_PER_M_INPUT_USD = 3.0
PRICE_PER_M_OUTPUT_USD = 15.0

SYSTEM_PROMPT = """You are Chaywanaprash, the research analyst for Trader Sahab, an intraday \
NSE equity/options trading platform. You are given REAL, computed statistics pulled directly \
from the platform's own SQLite trade journal — never invented, never estimated. Your job is to \
read them and propose concrete, prioritized, safe improvements to the PLATFORM (its code, its \
checklist logic, its risk rules, its data pipeline) — not trading advice about any stock.

Rules:
- Cite only numbers actually present in the data you were given. Never invent a statistic, a \
percentage, or a claim about market conditions you weren't given evidence for.
- If the data doesn't support a conclusion (too few samples, nothing anomalous), say so plainly \
rather than manufacturing a finding.
- Distinguish clearly between: (a) a likely code/logic bug (something producing a result that \
can't be intentional), (b) a genuine market-condition observation (the data reflects real \
conditions, not a flaw), and (c) a design tradeoff worth reconsidering (intentional, but maybe \
miscalibrated).
- Never recommend loosening a risk or entry-quality bar just to force more trades. Recommend \
fixing what's actually broken instead.
- Be concrete: name the file/function where you can infer one from the data's structure, and say \
exactly what would change. No vague "consider optimizing X" filler.
- Keep it tight: a short prioritized list, not an essay. Every change you actually ship still \
goes through a human — you are producing a report, not applying a patch.
"""

_client = None
_lock = threading.Lock()
_budget = {"date": None, "used": 0}


def _reset_budget_if_new_day():
    today = datetime.now(timezone.utc).date()
    if _budget["date"] != today:
        _budget.update(date=today, used=0)


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=config.NEWS["anthropic_api_key"])
    return _client


def _allowed():
    if not config.CHAYWANAPRASH.get("enabled") or not config.NEWS.get("anthropic_api_key"):
        return False
    with _lock:
        _reset_budget_if_new_day()
        if _budget["used"] >= config.CHAYWANAPRASH.get("daily_limit", 12):
            return False
        _budget["used"] += 1
        return True


def _gather_findings(hours):
    return {
        "checklist_blockers": database.checklist_blocker_stats(hours),
        "journal_summary": database.journal_summary(),
        "recent_warn_error_activity": database.recent_activity_issues(hours),
    }


def _ask_llm(findings):
    import json as _json
    user_content = (
        "Here is the platform's real data for this window:\n\n"
        + _json.dumps(findings, indent=2, default=str)
        + "\n\nAnalyze it and give your prioritized recommendations."
    )
    resp = _get_client().messages.create(
        model=MODEL, max_tokens=1500, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = resp.content[0].text.strip()
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def analyze(hours=None, persist=True):
    """Runs one research pass: real stats always; an LLM-written analysis
    of them too, if a key is configured and today's budget allows.
    Returns {"llm_used": bool, "narrative": str|None, "findings": {...},
    "note": str|None}. Never raises for a missing key or a spent budget —
    only for something actually going wrong while it should have run."""
    hours = hours or config.CHAYWANAPRASH.get("lookback_hours", 24)
    findings = _gather_findings(hours)

    if not _allowed():
        reason = (
            "No ANTHROPIC_API_KEY configured" if not config.NEWS.get("anthropic_api_key")
            else "Chaywanaprash is disabled (config.CHAYWANAPRASH['enabled'])" if not config.CHAYWANAPRASH.get("enabled")
            else f"Today's daily_limit ({config.CHAYWANAPRASH.get('daily_limit', 12)}) is used up"
        )
        result = {"llm_used": False, "narrative": None, "findings": findings,
                  "note": f"{reason} — showing the real computed stats only, no LLM narrative."}
        if persist:
            database.record_chaywanaprash_report(hours, False, None, findings)
        return result

    try:
        narrative, in_tok, out_tok = _ask_llm(findings)
    except Exception as exc:
        logger.warning(f"Chaywanaprash LLM analysis failed: {exc}")
        result = {"llm_used": False, "narrative": None, "findings": findings,
                  "note": f"LLM call failed ({exc}) — showing the real computed stats only."}
        if persist:
            database.record_chaywanaprash_report(hours, False, None, findings)
        return result

    result = {"llm_used": True, "narrative": narrative, "findings": findings, "note": None}
    if persist:
        database.record_chaywanaprash_report(hours, True, narrative, findings, in_tok, out_tok)
    return result


def stats():
    """For a dashboard usage check, same shape as llm_sentiment.stats()."""
    with _lock:
        _reset_budget_if_new_day()
        used = _budget["used"]
    return {
        "enabled": bool(config.CHAYWANAPRASH.get("enabled")),
        "configured": bool(config.NEWS.get("anthropic_api_key")),
        "used_today": used, "daily_limit": config.CHAYWANAPRASH.get("daily_limit", 12),
    }
