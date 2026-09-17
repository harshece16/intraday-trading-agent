"""
Sahab's Research Desk: a research-only, multi-agent brief per stock, following
the team layout of Tauric Research's TradingAgents (README §41, §44).

One brief:
  1. A timestamped snapshot built only from data the platform already has: the
     engine's checklist read (or the scanner's deep read), the scanner row,
     fundamentals.py, news_sentiment.py, market context and a sizing/cost preview.
  2. Analyst team: market, sentiment, news and fundamentals analysts.
  3. Research team: bull and bear researchers debate; the research manager rates
     how the evidence leans and writes the investment plan.
  4. Trader: turns the plan into a proposal that can only reuse the checklist's
     own entry, stop and target.
  5. Risk team: aggressive, conservative and neutral analysts review the
     proposal, next to risk flags computed in code.
  6. Portfolio manager: the final rating (Sell to Buy), approves or rejects the
     proposal, and writes the executive summary and investment thesis.

Hard boundaries:
- Research only. Nothing here places an order, and nothing it writes feeds
  confidence.py, trader_brain.py, sizing or any entry gate. The final rating is
  logged and scored by database.research_rating_ic() with the same per-session
  IC method and t >= 2 bar as every other signal (README §38); it earns no
  weight anywhere until that passes. "Approve" only means the portfolio manager
  agrees with the trader's proposal on paper.
- Grounded. Every agent returns JSON checked against a schema. A point that
  cites a field missing from the snapshot, or writes a number the snapshot
  doesn't contain, is dropped and recorded. A rating left with no grounded
  evidence is discarded.
- Off by default, with daily brief and cost caps. Runs happen on demand in a
  background thread, never inside the engine's 30 s tick.
"""

import bisect
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, ValidationError

import config
import confidence
import costs
import database
import fundamentals
import news_sentiment
import trader_brain
from risk_manager import RiskManager

logger = logging.getLogger("trading_bot")
IST = ZoneInfo("Asia/Kolkata")

# USD per million tokens (input, output) for the Anthropic API backend. Checked
# on 2026-09-17 against the list-price costs the Claude CLI reports per call.
# The CLI backend uses the cost the CLI itself reports instead.
PRICES_PER_M_USD = {
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
MAX_TOKENS = 8000
STOP_TO_COST_MIN = 3.0
TIME_HORIZON = "next session"
RATING_LABELS = {-2: "Sell", -1: "Underweight", 0: "Hold", 1: "Overweight", 2: "Buy"}

SYSTEM_PROMPT = """You are one member of Sahab's Research Desk, the research team for Trader Sahab, an \
intraday trading agent for NSE (India) cash equities. The desk mirrors a trading firm: analysts, a bull and a \
bear researcher, a research manager, a trader, a risk team and a portfolio manager. You write research. You \
never place orders, and nothing you write feeds a trading gate or a position size.

Each request gives you a timestamped JSON snapshot built from the platform's own data, then your role and task.

Code checks every point you write and drops the ones that break these rules:
- Use only the snapshot and any reports quoted in your task. Don't add outside knowledge about the company, \
its sector or the market.
- Every number you write must appear in the snapshot. You may round a number or show a ratio as a percentage, \
but don't compute new figures, estimate price levels or targets, or state probabilities.
- Every point needs at least one citation: a snapshot field path such as technical.rsi, \
scanner.reasons[0].text, news.headlines[2].title or market.nifty.chg_pct.
- Don't write dates or clock times unless they appear in the snapshot.
- If the snapshot doesn't support a view, say so plainly instead of filling the gap.
- Don't forecast prices. Describe what the evidence shows, how strong it is, and what would change it.
- Keep each point to one or two sentences."""

ANALYSTS = (
    ("market", "Market analyst",
     "the `technical` and `scanner` sections (use `rules` for what the thresholds mean)",
     "what the checklist read and the scanner ranking show about this stock's setup and trend"),
    ("sentiment", "Sentiment analyst",
     "`news.score`, the `score` of each item in `news.headlines`, the mood fields in `market` "
     "(bias, breadth, vix, fii_dii, real_market_breadth) and `scanner.sector`",
     "how sentiment toward this stock and the market's mood read today"),
    ("news", "News analyst",
     "`news.headlines`, `scanner.catalyst`, `scanner.event` and `scanner.large_deals`",
     "what recent headlines, filings and events say, and whether they support or contradict the scanner's side"),
    ("fundamentals", "Fundamentals analyst",
     "the `fundamentals` section, and `scanner.event` for any results or corporate event",
     "the company's quality and any red flags in its financial ratios"),
)
RISK_ANALYSTS = (
    ("aggressive", "Aggressive risk analyst",
     "Argue for taking the trader's proposal, or a firmer version of it, wherever the evidence supports it, "
     "and say what has to hold for that to be right."),
    ("conservative", "Conservative risk analyst",
     "Argue for protecting capital: costs against the stop, sizing, the gates that would block the trade, and "
     "the system's unproven edge."),
    ("neutral", "Neutral risk analyst",
     "Weigh the aggressive and conservative views and say where the evidence actually lands."),
)


# ---- output schemas ------------------------------------------------------

class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Point(_Strict):
    text: str
    citations: List[str]


class AnalystReport(_Strict):
    stance: Literal["bullish", "bearish", "neutral", "insufficient_data"]
    summary: str
    points: List[Point]


class ResearcherCase(_Strict):
    thesis: str
    points: List[Point]
    rebuttal: str


class InvestmentPlan(_Strict):
    rating: Literal[-2, -1, 0, 1, 2]
    summary: str
    evidence: List[Point]
    key_risks: List[Point]
    what_would_change_view: List[Point]


class TraderProposal(_Strict):
    proposal: Literal["long", "short", "stand_aside"]
    entry: Optional[float]
    stop: Optional[float]
    target: Optional[float]
    rationale: str
    points: List[Point]


class RiskView(_Strict):
    stance: Literal["support", "modify", "reject"]
    summary: str
    points: List[Point]


class FinalDecision(_Strict):
    rating: Literal[-2, -1, 0, 1, 2]
    proposal_verdict: Literal["approve", "reject"]
    executive_summary: str
    investment_thesis: str
    evidence: List[Point]
    key_risks: List[Point]


def api_schema(model_cls):
    """The model's JSON schema with $refs inlined and titles dropped. Every
    object keeps additionalProperties: false and every field stays required."""
    schema = model_cls.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(defs[node["$ref"].rsplit("/", 1)[-1]])
            return {k: resolve(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


class AgentError(Exception):
    pass


# ---- LLM backends --------------------------------------------------------

def _cli_binary():
    found = shutil.which("claude")
    if found:
        return found
    fallback = os.path.expanduser("~/.local/bin/claude")
    return fallback if os.path.exists(fallback) else None


class AnthropicApiBackend:
    name = "anthropic_api"
    label = "Anthropic API"

    def __init__(self, client=None):
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=config.NEWS["anthropic_api_key"])
        self.client = client

    def ask(self, model, effort, system, snapshot_text, task, schema_cls):
        """Returns (json_text, usage) or raises AgentError. `effort` only applies to the CLI backend."""
        resp = self.client.messages.create(
            model=model, max_tokens=MAX_TOKENS, system=system,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "Snapshot (JSON):\n" + snapshot_text, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": task},
            ]}],
            output_config={"format": {"type": "json_schema", "schema": api_schema(schema_cls)}},
        )
        if resp.stop_reason == "refusal":
            raise AgentError("declined by the model")
        if resp.stop_reason == "max_tokens":
            raise AgentError("ran out of output tokens before finishing")
        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), None)
        if text is None:
            raise AgentError("no text in the response")
        u = resp.usage
        price = PRICES_PER_M_USD[model]
        in_tok, out_tok = u.input_tokens or 0, u.output_tokens or 0
        cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
        cost = (in_tok * price[0] + cache_write * price[0] * 1.25 + cache_read * price[0] * 0.1
                + out_tok * price[1]) / 1e6
        return text, {"models": [getattr(resp, "model", None) or model], "input_tokens": in_tok + cache_read + cache_write,
                      "output_tokens": out_tok, "cost_usd": round(cost, 6), "turns": 1}


class ClaudeCliBackend:
    """`claude -p` with every tool, plugin, hook and MCP server switched off: text in, JSON out."""
    name = "claude_cli"
    label = "Claude Code CLI (your Claude plan)"

    def __init__(self, binary=None, run=subprocess.run):
        self.binary = binary or _cli_binary()
        self.run = run

    def command(self, model, effort, system, prompt, schema_cls):
        return [self.binary, "-p", prompt, "--output-format", "json", "--model", model, "--effort", effort,
                "--tools", "", "--no-session-persistence", "--strict-mcp-config",
                "--disable-slash-commands", "--setting-sources", "",
                "--system-prompt", system, "--json-schema", json.dumps(api_schema(schema_cls))]

    def ask(self, model, effort, system, snapshot_text, task, schema_cls):
        prompt = "Snapshot (JSON):\n" + snapshot_text + "\n\n" + task
        try:
            proc = self.run(self.command(model, effort, system, prompt, schema_cls), capture_output=True, text=True,
                            timeout=config.RESEARCH_DESK.get("cli_timeout_s", 240), cwd=tempfile.gettempdir())
        except subprocess.TimeoutExpired:
            raise AgentError("the Claude CLI timed out")
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            raise AgentError(f"the Claude CLI returned no JSON (exit {proc.returncode}): {proc.stderr[-300:]}")
        if data.get("is_error"):
            raise AgentError(f"the Claude CLI reported an error: {str(data.get('result'))[:300]}")
        structured = data.get("structured_output")
        text = json.dumps(structured) if structured is not None else data.get("result")
        if not text:
            raise AgentError("no output from the Claude CLI")
        usage = data.get("usage") or {}
        return text, {
            "models": list((data.get("modelUsage") or {}).keys()) or [model],
            "input_tokens": sum(usage.get(k) or 0 for k in
                                ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
            "output_tokens": usage.get("output_tokens") or 0,
            "cost_usd": round(float(data.get("total_cost_usd") or 0.0), 6),
            "turns": data.get("num_turns"),
        }


def backend_name():
    """Which backend a run would use right now, or None if neither is available."""
    mode = config.RESEARCH_DESK.get("llm_backend", "auto")
    has_key = bool(config.NEWS.get("anthropic_api_key"))
    if mode == "anthropic_api" or (mode == "auto" and has_key):
        return "anthropic_api" if has_key else None
    if mode in ("claude_cli", "auto"):
        return "claude_cli" if _cli_binary() else None
    return None


def make_backend():
    name = backend_name()
    if name == "anthropic_api":
        return AnthropicApiBackend()
    if name == "claude_cli":
        return ClaudeCliBackend()
    raise AgentError("No LLM backend is available.")


# ---- budget, usage and run progress --------------------------------------

_lock = threading.RLock()
_usage = {"date": None, "briefs": 0, "calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
_run = {"running": False, "symbols": [], "done": [], "current": None, "stages": [],
        "started_at": None, "finished_at": None, "stopped_reason": None}


def _reset_if_new_day():
    today = datetime.now(IST).date()
    if _usage["date"] != today:
        _usage.update(date=today, briefs=0, calls=0, input_tokens=0, output_tokens=0, cost_usd=0.0)


def _blocked_reason():
    """Why a new brief can't start right now, or None."""
    cfg = config.RESEARCH_DESK
    name = backend_name()
    if name is None:
        if cfg.get("llm_backend") == "anthropic_api":
            return "No ANTHROPIC_API_KEY is configured."
        return "No LLM is available: set ANTHROPIC_API_KEY, or install the Claude Code CLI."
    if not cfg.get("enabled"):
        return "The Research Desk is switched off."
    if name == "anthropic_api":
        for key in ("analyst_model", "team_model"):
            if cfg[key] not in PRICES_PER_M_USD:
                return f"No price on file for {cfg[key]}, so the daily cost cap can't be enforced."
    with _lock:
        _reset_if_new_day()
        if _usage["briefs"] >= cfg["daily_brief_limit"]:
            return f"Today's brief limit ({cfg['daily_brief_limit']}) is used up."
        if _usage["cost_usd"] >= cfg["daily_cost_limit_usd"]:
            return f"Today's cost limit (${cfg['daily_cost_limit_usd']:.2f}) is used up."
    return None


def _reserve_brief():
    with _lock:
        reason = _blocked_reason()
        if reason is None:
            _usage["briefs"] += 1
        return reason


def _cost_limit_reached():
    with _lock:
        _reset_if_new_day()
        return _usage["cost_usd"] >= config.RESEARCH_DESK["daily_cost_limit_usd"]


def _record_usage(info):
    with _lock:
        _reset_if_new_day()
        _usage["calls"] += 1
        for key in ("input_tokens", "output_tokens", "cost_usd"):
            _usage[key] += info[key]


def _set_stage(agent, status):
    with _lock:
        for stage in _run["stages"]:
            if stage["agent"] == agent:
                stage["status"] = status


def stats():
    cfg = config.RESEARCH_DESK
    name = backend_name()
    with _lock:
        _reset_if_new_day()
        usage = dict(_usage)
        run = {**_run, "symbols": list(_run["symbols"]), "done": list(_run["done"]),
               "stages": [dict(s) for s in _run["stages"]]}
    return {
        "research_only": True,
        "enabled": bool(cfg.get("enabled")),
        "backend": name,
        "backend_label": {"anthropic_api": AnthropicApiBackend.label, "claude_cli": ClaudeCliBackend.label}.get(name),
        "blocked_reason": _blocked_reason(),
        "models": {"analysts": cfg["analyst_model"], "team": cfg["team_model"]},
        "debate_rounds": cfg["debate_rounds"],
        "calls_per_brief": len(ANALYSTS) + 2 * max(1, int(cfg["debate_rounds"])) + 3 + len(RISK_ANALYSTS),
        "briefs_today": usage["briefs"], "daily_brief_limit": cfg["daily_brief_limit"],
        "calls_today": usage["calls"],
        "input_tokens_today": usage["input_tokens"], "output_tokens_today": usage["output_tokens"],
        "cost_usd_today": round(usage["cost_usd"], 4), "daily_cost_limit_usd": cfg["daily_cost_limit_usd"],
        "run": run,
        "rating_ic": database.research_rating_ic(),
    }


def set_enabled(enabled: bool):
    config.RESEARCH_DESK["enabled"] = bool(enabled)
    return config.RESEARCH_DESK["enabled"]


# ---- snapshot ------------------------------------------------------------

_TECH_KEYS = ("bias", "setup", "regime", "structure", "htf_trend", "always_in", "bull_score", "bear_score",
              "entry_threshold", "rsi", "adx", "atr", "ema20", "ema50", "vwap", "volume_ratio",
              "support", "resistance", "long_ok", "short_ok", "entry_mode", "bar_time",
              "news_score", "fundamentals_score", "fundamentals_label")
_SCAN_KEYS = ("name", "industry", "side", "status", "rank", "score", "final_score", "long_score", "short_score",
              "ltp", "chg_pct", "gap_pct", "rvol", "rs_today", "atr_pct", "daily_trend", "rs10",
              "pct_from_high", "pct_from_low", "turnover_cr", "beta", "excluded")


def _plain(obj):
    return json.loads(json.dumps(obj, default=str))


def _rules():
    p = {**trader_brain.DEFAULTS, **config.STRATEGY_PARAMS.get(config.STRATEGY, {})}
    bar_minutes = int(config.CANDLE_INTERVAL.rstrip("m")) if config.CANDLE_INTERVAL.endswith("m") else None
    return {
        "bar_minutes": bar_minutes,
        "higher_timeframe_minutes": bar_minutes * p["htf_factor"] if bar_minutes else None,
        "entry_threshold": p["entry_threshold"], "min_confirmations": p["min_confirmations"],
        "min_rrr": p["min_rrr"], "volume_lookback_bars": p["volume_lookback"],
        "sr_tolerance_atr": p["sr_tolerance_atr"], "indicator_miss_size": p["indicator_miss_size"],
        "entry_window": f"{p['no_entry_before']}-{p['last_entry_time']}",
        "indicator_periods": {"ema_fast": 20, "ema_slow": 50, "rsi": 14, "atr": 14, "adx": 14,
                              "macd": [12, 26, 9], "bollinger": [20, 2], "stochastic": [14, 3]},
        "adx_trending_at": p["adx_trend"], "adx_ranging_below": p["adx_range"],
        "relative_strength_days": 10, "high_low_lookback_weeks": 52,
        "max_risk_per_trade_pct": config.RISK["max_risk_per_trade_pct"],
        "max_open_positions": config.RISK["max_open_positions"],
        "max_positions_per_sector": config.RISK.get("max_positions_per_sector"),
        "max_position_notional_pct": config.RISK.get("max_position_notional_pct"),
        "min_confidence_to_trade": config.RISK.get("min_confidence_to_trade"),
        "stop_to_cost_min": STOP_TO_COST_MIN,
    }


def _technical(analysis, source, row):
    if not analysis:
        return {"available": False,
                "note": "No live checklist read or scanner deep read exists for this stock yet."}
    tech = {k: analysis.get(k) for k in _TECH_KEYS}
    tech.update(available=True, source=source)
    tech["ltp"] = analysis.get("ltp") if analysis.get("ltp") is not None else (row or {}).get("ltp")
    tech["bar_hhmm"] = (analysis.get("bar_time") or "")[11:16] or None
    tech["patterns"] = [p.get("name") for p in analysis.get("patterns") or []]
    tech["bull_evidence"] = [{"points": x.get("points"), "text": x.get("text")} for x in analysis.get("reasons") or []]
    tech["bear_evidence"] = [{"points": x.get("points"), "text": x.get("text")}
                             for x in analysis.get("bear_reasons") or []]
    tech["bull_categories"] = list(analysis.get("confirmations") or [])
    tech["bear_categories"] = list(analysis.get("bear_confirmations") or [])
    tech["blockers"] = list(analysis.get("blockers") or [])
    side = ((row or {}).get("side") or ("SHORT" if analysis.get("bias") == "short" else "LONG")).lower()
    cl = (analysis.get("checklist") or {}).get(side)
    if cl:
        tech["checklist"] = {
            "side": side, "passed": cl.get("passed"), "pattern": cl.get("pattern"),
            "entry": cl.get("entry"), "stop": cl.get("stop"), "target": cl.get("target"),
            "rrr": cl.get("rrr"), "size_factor": cl.get("size_factor"),
            "items": [{"label": i.get("label"), "ok": i.get("ok"), "required": i.get("required"),
                       "detail": i.get("detail")} for i in cl.get("items") or []],
        }
    return tech


def _scanner(row, scan):
    if not row:
        return {"available": False, "note": "This stock isn't in the latest scan."}
    out = {k: row.get(k) for k in _SCAN_KEYS}
    out["available"] = True
    out["reasons"] = [{"points": x.get("points"), "text": x.get("text")} for x in row.get("reasons") or []]
    cat = row.get("catalyst")
    out["catalyst"] = {"score": cat.get("score"), "top": cat.get("top")} if isinstance(cat, dict) else None
    out["event"] = row.get("event")
    out["swing_patterns"] = [{"name": s.get("name"), "side": s.get("side"), "level": s.get("level"),
                              "stop": s.get("stop")} for s in row.get("swing_patterns") or []]
    out["large_deals"] = row.get("large_deals")
    sectors = scan.get("sectors") or []
    rank = next((i for i, s in enumerate(sectors, 1) if s.get("industry") == row.get("industry")), None)
    out["sector"] = ({"industry": row.get("industry"), "chg_pct": sectors[rank - 1].get("chg_pct"),
                      "rank": rank, "of": len(sectors)} if rank else None)
    out["session_date"] = scan.get("session_date")
    return out


def _fundamentals(symbol):
    try:
        f = fundamentals.get_fundamentals(symbol)
    except Exception as exc:
        return {"available": False, "note": f"Fundamentals unavailable: {exc}"}
    return {"available": f.get("score") is not None, "score": f.get("score"), "label": f.get("label"),
            "metrics": [{"label": m.get("label"), "value": m.get("value"), "points": m.get("points"),
                         "text": m.get("text")} for m in f.get("metrics") or []]}


def _news(symbol, name):
    try:
        n = news_sentiment.get_sentiment(symbol, name)
    except Exception as exc:
        return {"available": False, "note": f"News unavailable: {exc}"}
    return {"available": True, "score": n.get("score"), "count": n.get("count"), "sources": n.get("sources"),
            "headlines": [{"title": h.get("title"), "publisher": h.get("publisher") or h.get("source"),
                           "age_h": h.get("age_h"), "score": h.get("score")}
                          for h in (n.get("headlines") or [])[:8]]}


def _risk(analysis, tech, scan_section, market, rows, positions):
    open_positions = {s: p for s, p in positions.items() if p.get("quantity")}
    industries = {r.get("symbol"): r.get("industry") for r in rows}
    industry = scan_section.get("industry")
    same_sector = sum(1 for s in open_positions if industry and industries.get(s) == industry)
    scorecard = database.journal_summary().get("scorecard", [])
    out = {
        "open_positions": len(open_positions),
        "same_sector_open_positions": same_sector,
        "scorecard": [{"criterion": r.get("criterion"), "status": r.get("status")} for r in scorecard],
        "vix_size_multiplier": config.MARKET_FILTER["vix_high_size_multiplier"] if market.get("vix_high") else 1.0,
    }
    side = (scan_section.get("side") or "").upper() or ("SHORT" if tech.get("bias") == "short" else "LONG")
    if analysis:
        conf = confidence.score_trade(analysis, side, scorecard)
        out["confidence_gate"] = {"side": side, "score": conf["score"], "label": conf["label"],
                                  "bar": config.RISK.get("min_confidence_to_trade", 60),
                                  "explanation": conf["explanation"]}
    cl = tech.get("checklist") or {}
    entry, stop = cl.get("entry"), cl.get("stop")
    if entry and stop and entry != stop:
        shares = int(RiskManager(config.RISK).position_size(entry, stop_price=stop) * out["vix_size_multiplier"]
                     * (cl.get("size_factor") or 1.0))
        plan = {"stop_distance_pct": round(abs(entry - stop) / entry * 100, 3), "shares": shares}
        if shares > 0:
            notional = entry * shares
            cost = (costs.leg_cost("BUY", entry, shares, config.COSTS) + costs.leg_cost("SELL", entry, shares, config.COSTS)
                    + 2 * notional * config.COSTS.get("slippage_pct", 0.0) / 100)
            cost_pct = cost / notional * 100
            plan.update(notional=round(notional, 2), risk_rupees=round(abs(entry - stop) * shares, 2),
                        modeled_round_trip_cost_rupees=round(cost, 2),
                        modeled_round_trip_cost_pct=round(cost_pct, 3),
                        stop_to_cost_ratio=round(plan["stop_distance_pct"] / cost_pct, 2),
                        cost_in_r=round(cost / (abs(entry - stop) * shares), 2))
        out["plan"] = plan
    return out


def build_snapshot(state, symbol, now=None):
    """A point-in-time record of everything the agents may use. Reads state and
    existing data functions only; writes nothing and never trades."""
    sym = symbol.upper()
    now = now or datetime.now(IST)
    with state.lock:
        live = dict(state.indicators.get(sym) or {})
        scan = dict(state.scanner or {})
        market = dict(state.market or scan.get("market") or {})
        positions = {s: dict(p) for s, p in state.positions.items()}
    rows = list(scan.get("rows") or [])
    row = next((r for r in rows if r.get("symbol") == sym), None)
    if live.get("bull_score") is not None:
        analysis, source = live, "live checklist read"
    elif row and row.get("brain"):
        analysis, source = row["brain"], "scanner deep read"
    else:
        analysis, source = None, None

    tech = _technical(analysis, source, row)
    scan_section = _scanner(row, scan)
    market_section = {k: market.get(k) for k in ("bias", "score", "reasons", "session_date", "nifty", "vix",
                                                  "vix_high", "breadth", "fii_dii", "real_market_breadth")}
    risk = _risk(analysis, tech, scan_section, market_section, rows, positions)
    position = positions.get(sym) or {}
    if position.get("quantity"):
        risk["this_position"] = {k: position.get(k) for k in ("quantity", "avg_price", "stop_price", "target_price")}
    return _plain({
        "meta": {"symbol": sym, "as_of": now.isoformat(timespec="seconds"), "as_of_hhmm": now.strftime("%H:%M"),
                 "session_date": scan.get("session_date") or market.get("session_date"),
                 "technical_source": source, "time_horizon": TIME_HORIZON},
        "rules": _rules(),
        "technical": tech,
        "scanner": scan_section,
        "fundamentals": _fundamentals(sym),
        "news": _news(sym, (row or {}).get("name")),
        "market": market_section,
        "risk": risk,
    })


def deterministic_flags(snapshot):
    """Risk flags computed in code from the snapshot, so they never depend on a
    model. Informational only: they don't block or size anything."""
    flags = []
    tech, scan, risk, market = snapshot["technical"], snapshot["scanner"], snapshot["risk"], snapshot["market"]
    plan = risk.get("plan")

    def add(severity, text, *citations):
        flags.append({"severity": severity, "text": text, "citations": list(citations)})

    if not tech.get("available"):
        add("medium", "No checklist read exists for this stock, so the desk has no technical evidence.",
            "technical.available")
    elif not plan:
        add("low", "The checklist has no stop yet, so the trade can't be sized or costed.", "technical.checklist")
    elif plan.get("stop_to_cost_ratio") is not None and plan["stop_to_cost_ratio"] < STOP_TO_COST_MIN:
        add("high" if plan["stop_to_cost_ratio"] < 1.5 else "medium",
            f"The stop is only {plan['stop_to_cost_ratio']}x the modeled round-trip cost "
            f"({plan['stop_distance_pct']}% vs {plan['modeled_round_trip_cost_pct']}%), under the "
            f"{STOP_TO_COST_MIN:g}x floor, so costs alone would take {plan['cost_in_r']}R.",
            "risk.plan.stop_to_cost_ratio", "risk.plan.cost_in_r")
    elif plan.get("shares") == 0:
        add("medium", "Position size rounds to 0 shares at the current risk settings.", "risk.plan.shares")
    if scan.get("excluded"):
        add("high", f"The scanner excludes this stock today: {scan['excluded']}", "scanner.excluded")
    if scan.get("event"):
        add("high", "A results date or corporate event is flagged for this stock.", "scanner.event")
    if tech.get("available") and scan.get("side") and tech.get("bias") and tech["bias"] != scan["side"].lower():
        add("medium", f"The checklist leans {tech['bias']} but the scanner ranks this stock "
                      f"{scan['side'].lower()}, and the engine refuses trades against the scanner's side.",
            "technical.bias", "scanner.side")
    side = (scan.get("side") or "").upper()
    if (side == "LONG" and market.get("bias") == "risk-off") or (side == "SHORT" and market.get("bias") == "risk-on"):
        add("medium", f"The market is {market['bias']}, which blocks new {side.lower()}s.",
            "market.bias", "scanner.side")
    if market.get("vix_high"):
        add("low", f"India VIX is high, so new positions are sized at {risk['vix_size_multiplier']}x.",
            "market.vix", "risk.vix_size_multiplier")
    if risk.get("same_sector_open_positions", 0) >= (snapshot["rules"].get("max_positions_per_sector") or 99):
        add("medium", "The sector already holds the maximum number of open positions.",
            "risk.same_sector_open_positions", "rules.max_positions_per_sector")
    unproven = [r["criterion"] for r in risk.get("scorecard", []) if r.get("status") != "pass"]
    if unproven:
        add("medium", f"The Dimaag Scorecard hasn't shown a proven edge yet ({len(unproven)} of "
                      f"{len(risk['scorecard'])} rows not passing).", "risk.scorecard")
    gate = risk.get("confidence_gate")
    if gate and gate["score"] < gate["bar"]:
        add("low", f"The confidence gate would block this {gate['side'].lower()} right now "
                   f"({gate['score']} vs a bar of {gate['bar']}).",
            "risk.confidence_gate.score", "risk.confidence_gate.bar")
    return flags


# ---- grounding -----------------------------------------------------------

_NUM_RE = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?")


def _numbers_in(text):
    out = []
    for m in _NUM_RE.finditer(text or ""):
        raw = m.group().rstrip(",")
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        decimals = len(raw.split(".", 1)[1]) if "." in raw else 0
        out.append((raw, value, decimals))
    return out


def _flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, (dict, list)) and not obj and prefix:
        out[prefix] = obj  # keep empty containers citable
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


class Grounding:
    """What the snapshot actually contains: its field paths, and every number in
    it, both stored values and numbers inside its text."""

    def __init__(self, snapshot):
        self.flat = _flatten(snapshot)
        values = set()
        for v in self.flat.values():
            if isinstance(v, bool):
                continue
            nums = [float(v)] if isinstance(v, (int, float)) else [n for _, n, _ in _numbers_in(v)] \
                if isinstance(v, str) else []
            for n in nums:
                values.update((abs(n), abs(n) * 100, abs(n) / 100))  # a ratio may be written as a percentage
        self.values = sorted(values)

    @staticmethod
    def _normalize(path):
        path = path.strip().strip("`").strip()
        return re.sub(r"\.(\d+)(?=\.|\[|$)", r"[\1]", path)

    def path_ok(self, path):
        path = self._normalize(path)
        if not path:
            return False
        return path in self.flat or any(k.startswith(path + ".") or k.startswith(path + "[") for k in self.flat)

    def number_ok(self, value, decimals=2):
        tol = 0.5 * 10 ** (-decimals) + 1e-9
        target = abs(value)
        i = bisect.bisect_left(self.values, target - tol)
        return i < len(self.values) and self.values[i] <= target + tol

    def problem(self, text, citations=None, need_citation=False):
        """Why this text isn't grounded, or None if it is."""
        if need_citation and not citations:
            return "no snapshot field cited"
        bad_paths = [c for c in citations or [] if not self.path_ok(c)]
        if bad_paths:
            return f"cites {', '.join(bad_paths)}, which isn't in the snapshot"
        bad = [raw for raw, value, decimals in _numbers_in(text) if not self.number_ok(value, decimals)]
        if bad:
            return f"writes {', '.join(bad)}, which isn't in the snapshot"
        return None


def _ground_points(points, agent, field, grounding, rejected):
    kept = []
    for i, p in enumerate(points):
        why = grounding.problem(p["text"], p.get("citations"), need_citation=True)
        if why:
            rejected.append({"agent": agent, "field": f"{field}[{i}]", "text": p["text"], "reason": why})
        else:
            kept.append(p)
    return kept


def _ground_text(data, key, agent, grounding, rejected):
    why = grounding.problem(data[key])
    if why:
        rejected.append({"agent": agent, "field": key, "text": data[key], "reason": why})
        data[key] = ""


def _ground(agent, schema_cls, data, grounding, rejected, snapshot):
    """Drops every ungrounded piece of a validated agent output (a plain dict)."""
    if schema_cls is AnalystReport:
        _ground_text(data, "summary", agent, grounding, rejected)
        data["points"] = _ground_points(data["points"], agent, "points", grounding, rejected)
        if data["stance"] != "insufficient_data" and not data["points"]:
            rejected.append({"agent": agent, "field": "stance", "text": data["stance"],
                             "reason": "no grounded points left to support it"})
            data["stance"] = "insufficient_data"
    elif schema_cls is ResearcherCase:
        for key in ("thesis", "rebuttal"):
            _ground_text(data, key, agent, grounding, rejected)
        data["points"] = _ground_points(data["points"], agent, "points", grounding, rejected)
    elif schema_cls in (InvestmentPlan, FinalDecision):
        for key in ("summary", "executive_summary", "investment_thesis"):
            if key in data:
                _ground_text(data, key, agent, grounding, rejected)
        for key in ("evidence", "key_risks", "what_would_change_view"):
            if key in data:
                data[key] = _ground_points(data[key], agent, key, grounding, rejected)
    elif schema_cls is TraderProposal:
        _ground_text(data, "rationale", agent, grounding, rejected)
        data["points"] = _ground_points(data["points"], agent, "points", grounding, rejected)
        plan = snapshot["technical"].get("checklist") or {}
        for key in ("entry", "stop", "target"):
            value = data[key]
            if value is not None and (plan.get(key) is None or abs(value - plan[key]) > 0.005):
                rejected.append({"agent": agent, "field": key, "text": str(value),
                                 "reason": "only the checklist's own entry, stop and target may be used"})
                data[key] = None
        if data["proposal"] != "stand_aside" and data["stop"] is None:
            rejected.append({"agent": agent, "field": "proposal", "text": data["proposal"],
                             "reason": "a proposal needs the checklist's stop"})
            data["proposal"] = "stand_aside"
    elif schema_cls is RiskView:
        _ground_text(data, "summary", agent, grounding, rejected)
        data["points"] = _ground_points(data["points"], agent, "points", grounding, rejected)
    return data


# ---- agent tasks ---------------------------------------------------------

def _dump(obj):
    return json.dumps(obj, sort_keys=True)


def _analyst_task(title, focus, question):
    return (f"Your role: {title}, on the analyst team.\nFocus on {focus}. Assess {question}.\n"
            "Return a stance (bullish, bearish, neutral or insufficient_data), a two- or three-sentence "
            "summary, and 2 to 5 cited points.")


def _researcher_task(side, symbol, round_no, rounds, reports, opponent):
    direction = "better" if side == "bull" else "worse"
    other = "bear" if side == "bull" else "bull"
    lines = [
        f"Your role: {side.capitalize()} researcher on the research team, debate round {round_no} of {rounds}.",
        f"Make the strongest evidence-based case that {symbol} does {direction} than other NIFTY 100 stocks "
        f"in the {TIME_HORIZON}, using the analyst reports below and the snapshot. Name the weakest part of "
        "your own case in one of your points.",
        (f"The {other} researcher's previous case is below. Use `rebuttal` to answer its strongest point."
         if opponent else "Set `rebuttal` to an empty string."),
        "", "Analyst reports (JSON):", _dump(reports),
    ]
    if opponent:
        lines += ["", f"The {other} researcher's previous case (JSON):", _dump(opponent)]
    return "\n".join(lines)


def _research_manager_task(symbol, reports, debate):
    return "\n".join([
        "Your role: Research manager.",
        f"Weigh the analyst reports and the bull/bear debate below, then write the investment plan: rate how "
        f"the evidence leans for {symbol} in the {TIME_HORIZON} relative to other NIFTY 100 stocks, from -2 "
        "(clearly worse) through 0 (balanced, or not enough evidence) to 2 (clearly better).",
        "Return the rating; a two- or three-sentence summary; evidence (the cited points that decided it); "
        "key_risks; and what_would_change_view (the snapshot fields whose change would flip it).",
        "", "Analyst reports (JSON):", _dump(reports), "", "Debate (JSON):", _dump(debate),
    ])


def _trader_task(symbol, plan):
    return "\n".join([
        "Your role: Trader.",
        f"Turn the research manager's investment plan below into a proposal for {symbol}: long, short or "
        "stand_aside. This is a written proposal for review; nothing executes it.",
        "You may only use the checklist's own levels: copy `technical.checklist.entry`, `.stop` and `.target` "
        "exactly, or set them to null. Choose stand_aside when the checklist hasn't passed, its side "
        "disagrees with the plan's rating, or `risk.plan` shows the trade can't be sized.",
        "Return the proposal, entry, stop, target, a one- or two-sentence rationale, and 1 to 4 cited points.",
        "", "Investment plan (JSON):", _dump(plan),
    ])


def _risk_task(title, brief, proposal, flags, earlier_views):
    lines = [
        f"Your role: {title} on the risk management team.",
        brief,
        "Review the trader's proposal below against the snapshot's `risk`, `market` and `scanner` sections and "
        "the risk flags already computed in code. Stance: support, modify or reject. Your view is advice for "
        "the portfolio manager; it never blocks or sizes a trade.",
        "Return the stance, a one- or two-sentence summary, and 1 to 4 cited points.",
        "", "Trader's proposal (JSON):", _dump(proposal),
        "", "Risk flags computed in code (JSON):", _dump(flags),
    ]
    if earlier_views:
        lines += ["", "Views already given by the rest of the risk team (JSON):", _dump(earlier_views)]
    return "\n".join(lines)


def _portfolio_manager_task(symbol, plan, proposal, risk_views, flags):
    return "\n".join([
        "Your role: Portfolio manager. You make the desk's final call.",
        f"Read the investment plan, the trader's proposal and the risk team's views below. Give {symbol} a final "
        f"rating for the {TIME_HORIZON} relative to other NIFTY 100 stocks: -2 Sell, -1 Underweight, 0 Hold, "
        "1 Overweight, 2 Buy. Approve or reject the trader's proposal on paper; nothing executes it.",
        "The rating is logged and later scored against what actually happened; it isn't a trade instruction.",
        "Return the rating, the proposal verdict, a two- or three-sentence executive summary, a short investment "
        "thesis, the cited evidence that decided it, and the key risks.",
        "", "Investment plan (JSON):", _dump(plan),
        "", "Trader's proposal (JSON):", _dump(proposal),
        "", "Risk team views (JSON):", _dump(risk_views),
        "", "Risk flags computed in code (JSON):", _dump(flags),
    ])


def _stages(rounds):
    stages = [("Analyst team", key, title) for key, title, _, _ in ANALYSTS]
    for r in range(1, rounds + 1):
        stages += [("Research team", f"bull_r{r}", f"Bull researcher (round {r})"),
                   ("Research team", f"bear_r{r}", f"Bear researcher (round {r})")]
    stages.append(("Research team", "research_manager", "Research manager"))
    stages.append(("Trading team", "trader", "Trader"))
    stages += [("Risk management", key, title) for key, title, _ in RISK_ANALYSTS]
    stages.append(("Portfolio management", "portfolio_manager", "Portfolio manager"))
    return [{"team": team, "agent": agent, "title": title, "status": "pending"} for team, agent, title in stages]


# ---- one brief -----------------------------------------------------------

class _Brief:
    def __init__(self, backend, symbol, snapshot, grounding):
        self.backend = backend
        self.symbol = symbol
        self.snapshot = snapshot
        self.snapshot_text = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        self.grounding = grounding
        self.calls, self.rejected, self.errors = [], [], []
        self.models = set()
        self.stopped = None
        self._lock = threading.Lock()  # the analysts run in parallel

    def ask(self, agent, model, effort, task, schema_cls):
        """One agent call: validated against the schema, then grounded. Returns a
        plain dict, or None with the reason recorded in self.errors."""
        with self._lock:
            if self.stopped or _cost_limit_reached():
                self.stopped = self.stopped or "Today's research cost limit was reached mid-brief."
                _set_stage(agent, "skipped")
                return None
        _set_stage(agent, "running")
        started = time.time()
        try:
            text, info = self.backend.ask(model, effort, SYSTEM_PROMPT, self.snapshot_text, task, schema_cls)
        except Exception as exc:
            logger.warning(f"Research Desk {agent} call failed for {self.symbol}: {exc}")
            with self._lock:
                self.errors.append({"agent": agent, "error": f"call failed: {exc}"})
            _set_stage(agent, "error")
            return None
        _record_usage(info)
        with self._lock:
            self.calls.append({"agent": agent, "seconds": round(time.time() - started, 1), **info})
            self.models.update(info["models"])
        try:
            data = schema_cls.model_validate_json(text).model_dump()
        except ValidationError as exc:
            with self._lock:
                self.errors.append({"agent": agent, "error": f"output rejected: {exc}"})
            _set_stage(agent, "error")
            return None
        with self._lock:
            grounded = _ground(agent, schema_cls, data, self.grounding, self.rejected, self.snapshot)
        _set_stage(agent, "done")
        return grounded


def run_brief(state, symbol, backend=None):
    """Research one stock and persist the brief. Returns {"ran": False, "reason": ...}
    when the desk is off, unavailable or over budget; otherwise a summary of the stored brief."""
    sym = symbol.upper()
    reason = _reserve_brief()
    if reason:
        return {"ran": False, "symbol": sym, "reason": reason, "budget_stop": True}

    cfg = config.RESEARCH_DESK
    rounds = max(1, int(cfg["debate_rounds"]))
    with _lock:
        _run["stages"] = _stages(rounds)
    started = time.time()
    backend = backend or make_backend()
    snapshot = build_snapshot(state, sym)
    grounding = Grounding(snapshot)
    flags = deterministic_flags(snapshot)
    brief = _Brief(backend, sym, snapshot, grounding)
    a_model, a_effort = cfg["analyst_model"], cfg.get("analyst_effort", "low")
    t_model, t_effort = cfg["team_model"], cfg.get("team_effort", "medium")

    with ThreadPoolExecutor(max_workers=len(ANALYSTS)) as pool:
        futures = {key: (title, pool.submit(brief.ask, key, a_model, a_effort,
                                            _analyst_task(title, focus, question), AnalystReport))
                   for key, title, focus, question in ANALYSTS}
        analysts = {key: {"title": title, "report": fut.result()} for key, (title, fut) in futures.items()}
    reports = {k: v["report"] for k, v in analysts.items() if v["report"]}

    debate, bull, bear = [], None, None
    for r in range(1, rounds + 1):
        prev_bull, prev_bear = bull, bear
        bull = brief.ask(f"bull_r{r}", t_model, t_effort, _researcher_task("bull", sym, r, rounds, reports, prev_bear),
                         ResearcherCase)
        bear = brief.ask(f"bear_r{r}", t_model, t_effort, _researcher_task("bear", sym, r, rounds, reports, prev_bull),
                         ResearcherCase)
        debate.append({"round": r, "bull": bull, "bear": bear})

    plan = brief.ask("research_manager", t_model, t_effort, _research_manager_task(sym, reports, debate),
                     InvestmentPlan)
    proposal = brief.ask("trader", t_model, t_effort, _trader_task(sym, plan), TraderProposal) if plan else None

    risk_views = {}
    if proposal:
        for key, title, stance_brief in RISK_ANALYSTS:
            earlier = {k: v["view"] for k, v in risk_views.items() if v["view"]}
            risk_views[key] = {"title": title,
                               "view": brief.ask(key, t_model, t_effort,
                                                 _risk_task(title, stance_brief, proposal, flags, earlier), RiskView)}
    decision = None
    if proposal:
        decision = brief.ask("portfolio_manager", t_model, t_effort,
                             _portfolio_manager_task(sym, plan, proposal,
                                                     {k: v["view"] for k, v in risk_views.items()}, flags),
                             FinalDecision)
    with _lock:
        for stage in _run["stages"]:
            if stage["status"] == "pending":
                stage["status"] = "skipped"

    rating = None
    if decision is not None:
        if decision["evidence"]:
            rating = decision["rating"]
            decision["rating_label"] = RATING_LABELS[rating]
        else:
            brief.rejected.append({"agent": "portfolio_manager", "field": "rating", "text": str(decision["rating"]),
                                   "reason": "no grounded evidence left to support it"})
            decision["rating"] = None
    if plan is not None and plan.get("evidence"):
        plan["rating_label"] = RATING_LABELS[plan["rating"]]

    if decision is not None and rating is None:
        status = "ungrounded"
    elif brief.stopped or decision is None or brief.errors:
        status = "partial"
    else:
        status = "complete"
    reports_out = {
        "status": status, "research_only": True, "backend": backend.name, "time_horizon": TIME_HORIZON,
        "analysts": analysts, "debate": debate, "investment_plan": plan, "trader": proposal,
        "risk": {"deterministic": flags, "team": risk_views}, "decision": decision,
        "rejected": brief.rejected, "errors": brief.errors, "calls": brief.calls,
        "stopped": brief.stopped, "duration_s": round(time.time() - started, 1),
    }
    tokens = sum(c["input_tokens"] + c["output_tokens"] for c in brief.calls)
    cost = round(sum(c["cost_usd"] for c in brief.calls), 6)
    brief_id = database.record_research_brief(started, sym, snapshot, reports_out, rating,
                                              sorted(brief.models), tokens, cost)
    return {"ran": True, "symbol": sym, "id": brief_id, "status": status, "rating": rating,
            "cost_usd": cost, "budget_stop": bool(brief.stopped)}


# ---- background runs -----------------------------------------------------

def _run_worker(state, symbols, backend=None):
    try:
        for sym in symbols:
            with _lock:
                _run["current"] = sym
            try:
                result = run_brief(state, sym, backend=backend)
            except Exception as exc:
                logger.exception(f"Research Desk brief failed for {sym}")
                result = {"ran": False, "symbol": sym, "reason": f"failed: {exc}"}
            with _lock:
                _run["done"].append({k: result.get(k) for k in ("symbol", "ran", "status", "rating", "reason")})
            if result.get("budget_stop"):
                with _lock:
                    _run["stopped_reason"] = result.get("reason") or "Today's research cost limit was reached."
                break
    finally:
        with _lock:
            _run.update(running=False, current=None, finished_at=time.time())


def request_run(state, symbols, backend=None):
    """Starts researching `symbols` in a background thread. Returns (started, message, thread)."""
    symbols = list(dict.fromkeys(s.upper() for s in symbols if s))[: config.RESEARCH_DESK["max_symbols_per_run"]]
    if not symbols:
        return False, "No symbols to research.", None
    reason = _blocked_reason()
    if reason:
        return False, reason, None
    with _lock:
        if _run["running"]:
            return False, "A research run is already in progress.", None
        _run.update(running=True, symbols=symbols, done=[], current=None, stages=[],
                    started_at=time.time(), finished_at=None, stopped_reason=None)
    thread = threading.Thread(target=_run_worker, args=(state, symbols, backend), name="research-desk", daemon=True)
    thread.start()
    return True, f"Researching {len(symbols)} stock(s) in the background.", thread


def latest_briefs(symbol, limit=3):
    return database.recent_research_briefs(symbol.upper(), limit=limit)
