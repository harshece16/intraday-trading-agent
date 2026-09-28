"""
Chaywanaprash — Sahab's own research analyst (chyawanprash, the Ayurvedic
general-strengthening tonic; same naming spirit as Trader Sahab / Sahab's
Dimaag / the Varsity Grand Checklist). Where Sahab's Dimaag scores one
trade, Chaywanaprash looks at the platform itself: it pulls real,
structured stats out of the same journal database every other part of
this system already writes to (checklist_evals, activity, trades — see
database.checklist_blocker_stats() and recent_activity_issues()) and, when
an LLM is available, asks Claude to read those real numbers and propose
concrete, evidence-backed improvements. The LLM is the Anthropic API when
ANTHROPIC_API_KEY is set, otherwise the Claude Code CLI (`claude -p`, billed
to your Claude plan) — the same two backends as research_desk.py.

Same discipline as everywhere else in this codebase: never fabricate.
With no LLM available, or the daily call budget spent, it still
returns the raw computed stats — clearly labeled as ungenerated — rather
than inventing a narrative. And it is deliberately read-only: it never
edits config.py, trader_brain.py, or anything else. It produces a report
a human reads and decides on, the same loop this project has followed for
every other change this session — find something real, report it,
implement only once asked.
"""

import json
import logging
import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone

import config
import database
import research_desk

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


def backends():
    """The backends a run would try right now, in order. In "auto" the CLI is
    also the fallback when the API call fails (a bad or out-of-credit key)."""
    mode = config.CHAYWANAPRASH.get("llm_backend", "auto")
    found = []
    if mode in ("auto", "anthropic_api") and config.NEWS.get("anthropic_api_key"):
        found.append("anthropic_api")
    if mode in ("auto", "claude_cli") and research_desk._cli_binary():
        found.append("claude_cli")
    return found


def _allowed():
    if not config.CHAYWANAPRASH.get("enabled") or not backends():
        return False
    with _lock:
        _reset_budget_if_new_day()
        if _budget["used"] >= config.CHAYWANAPRASH.get("daily_limit", 12):
            return False
        _budget["used"] += 1
        return True


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Rules about the code's hygiene rather than how it trades; left out of the review.
_NOT_TRADING_AREAS = ("security", "ui", "workflow")

REVIEW_TASK = """This is the fortnightly review of Sahab's Dimaag. `recent_changes` lists \
every change merged in the window and the platform's rules as they stand now. \
1. For the changes that touch how stocks are picked, entered, sized or exited, say whether \
the journal data above shows each one working as intended, or that there is too little data \
to tell. \
2. Name rules the data shows never firing, firing on everything, or contradicting each other. \
3. Propose at most five improvements to the decision rules, each naming the file or rule id it \
touches and the test that must pass before it ships: net of costs, on both halves of the \
sample, counted as a new trial. Say plainly when the right move is to change nothing."""


def _recent_changes(days):
    """What changed in the brain over the window: the merged commits, and the
    rules as they stand (docs/architecture/rules.json)."""
    out = {"window_days": days}
    try:
        proc = subprocess.run(["git", "log", f"--since={days} days ago", "--format=%ad %s", "--date=short"],
                              cwd=REPO, capture_output=True, text=True, timeout=30)
        out["merged_changes"] = proc.stdout.splitlines()
    except Exception as exc:
        out["merged_changes"] = f"git log unavailable: {exc}"
    # ponytail: the whole rulebook, since rules.json only began on 2026-09-28;
    # diff it against the window's start once it has two weeks of history.
    try:
        with open(os.path.join(REPO, "docs", "architecture", "rules.json")) as f:
            out["rules"] = [{k: r.get(k) for k in ("id", "area", "status", "rule")}
                            for r in json.load(f)["rules"] if r.get("area") not in _NOT_TRADING_AREAS]
    except Exception as exc:
        out["rules"] = f"rules.json unavailable: {exc}"
    return out


def _gather_findings(hours, changes=False):
    findings = {
        "checklist_blockers": database.checklist_blocker_stats(hours),
        "journal_summary": database.journal_summary(),
        "dimag_ki_batti": database.dimag_ki_batti(),
        "recent_warn_error_activity": database.recent_activity_issues(hours),
    }
    if changes:
        findings["recent_changes"] = _recent_changes(round(hours / 24))
    return findings


def _ask_api(user_content):
    resp = _get_client().messages.create(
        model=MODEL, max_tokens=1500, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = resp.content[0].text.strip()
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def _ask_cli(user_content, run=None):
    """`claude -p` with every tool, hook and MCP server switched off, as in
    research_desk.ClaudeCliBackend — text in, text out."""
    cmd = [research_desk._cli_binary(), "-p", "--output-format", "json", "--model", MODEL,
           "--effort", config.CHAYWANAPRASH.get("cli_effort", "medium"),
           "--tools", "", "--no-session-persistence", "--strict-mcp-config",
           "--disable-slash-commands", "--setting-sources", "", "--system-prompt", SYSTEM_PROMPT]
    # Without the key in its environment the CLI signs in with your Claude
    # plan; with it, a bad key would fail here exactly as it did on the API.
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    # The findings go in on stdin: they are too long to be safe as an argument.
    proc = (run or subprocess.run)(cmd, input=user_content, capture_output=True, text=True, env=env,
                                   timeout=config.CHAYWANAPRASH.get("cli_timeout_s", 240),
                                   cwd=tempfile.gettempdir())
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        raise RuntimeError(f"the Claude CLI returned no JSON (exit {proc.returncode}): {proc.stderr[-300:]}")
    if data.get("is_error") or not data.get("result"):
        raise RuntimeError(f"the Claude CLI reported an error: {str(data.get('result'))[:300]}")
    usage = data.get("usage") or {}
    in_tok = sum(usage.get(k) or 0 for k in
                 ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return data["result"].strip(), in_tok, usage.get("output_tokens") or 0


def _ask_llm(findings):
    user_content = (
        "Here is the platform's real data for this window:\n\n"
        + json.dumps(findings, indent=2, default=str)
        + "\n\nAnalyze it and give your prioritized recommendations."
        + ("\n\n" + REVIEW_TASK if "recent_changes" in findings else "")
    )
    names = backends()
    for i, name in enumerate(names):
        try:
            return (_ask_api if name == "anthropic_api" else _ask_cli)(user_content)
        except Exception as exc:
            if i == len(names) - 1:
                raise
            logger.warning(f"Chaywanaprash: {name} failed ({exc}) — trying {names[i + 1]}")


def analyze(hours=None, persist=True, changes=False):
    """Runs one research pass: real stats always; an LLM-written analysis
    of them too, if an LLM is available and today's budget allows.
    Returns {"llm_used": bool, "narrative": str|None, "findings": {...},
    "note": str|None}. Never raises for a missing key or a spent budget —
    only for something actually going wrong while it should have run."""
    hours = hours or config.CHAYWANAPRASH.get("lookback_hours", 24)
    findings = _gather_findings(hours, changes)

    if not _allowed():
        reason = (
            "Chaywanaprash is disabled (config.CHAYWANAPRASH['enabled'])" if not config.CHAYWANAPRASH.get("enabled")
            else "No ANTHROPIC_API_KEY configured and no Claude Code CLI found" if not backends()
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
        "configured": bool(backends()), "backends": backends(),
        "used_today": used, "daily_limit": config.CHAYWANAPRASH.get("daily_limit", 12),
    }


# ---- the fortnightly review, started from the engine tick --------------------

_review = {"date": None}


def review_due(now, holiday):
    """After the close on a trading day, when no two-week review with a
    narrative is under a week old. One look a day: the answer holds until
    tomorrow, so the tick doesn't re-read the reports every few seconds and a
    failed run retries the next trading day."""
    conf = config.CHAYWANAPRASH
    if not conf.get("review_every_days") or holiday or now.weekday() >= 5:
        return False
    if now.strftime("%H:%M") < conf.get("review_after", "15:40") or _review["date"] == now.date():
        return False
    _review["date"] = now.date()
    hours = conf.get("review_lookback_days", 14) * 24
    cutoff = time.time() - (conf["review_every_days"] - 0.5) * 86400
    return not any(r["llm_used"] and (r["lookback_hours"] or 0) >= hours and r["ts"] >= cutoff
                   for r in database.recent_chaywanaprash_reports(limit=50))


def maybe_start_review(now, holiday, log):
    """Called from the engine tick. Starts the review in its own thread (the
    CLI takes about 30 s and the tick must not wait) and reports the outcome
    through `log`, the engine's activity log. Never raises."""
    try:
        if not review_due(now, holiday):
            return False
        days = config.CHAYWANAPRASH.get("review_lookback_days", 14)

        def work():
            try:
                result = analyze(hours=days * 24, changes=True)
            except Exception as exc:
                logger.exception("Chaywanaprash: the fortnightly review failed")
                log("system", f"Chaywanaprash: the fortnightly review failed ({exc})", level="warn")
                return
            if result["llm_used"]:
                log("system", f"Chaywanaprash: the review of the last {days} days is saved. "
                              "Read it at GET /api/chaywanaprash/reports; it changes nothing by itself")
            else:
                log("system", f"Chaywanaprash: the review saved stats only. {result['note']}", level="warn")

        threading.Thread(target=work, name="chaywanaprash-review", daemon=True).start()
        return True
    except Exception:
        logger.exception("Chaywanaprash: could not start the fortnightly review")
        return False
