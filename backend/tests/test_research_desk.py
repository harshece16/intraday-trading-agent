"""Sahab's Research Desk: research-only briefs, grounded outputs, budgets and both LLM backends — no network."""
import inspect
import json
import subprocess
import threading
import time

import pytest

import config
import database
import research_desk as rd

SYMBOL = "TESTCO"
DEFAULT_ENABLED = config.RESEARCH_DESK["enabled"]  # read before any fixture switches the desk on

ANALYSIS = {
    "bull_score": 7.0, "bear_score": 2.0, "entry_threshold": 6.0, "bias": "long", "setup": "Bullish Engulfing",
    "regime": "trending", "structure": "uptrend", "htf_trend": "up", "always_in": "long",
    "rsi": 61.5, "adx": 28.0, "atr": 4.2, "ema20": 1000.0, "ema50": 990.0, "vwap": 1002.0,
    "volume_ratio": 1.4, "support": 995.0, "resistance": 1030.0, "long_ok": True, "short_ok": False,
    "entry_mode": "checklist", "bar_time": "2026-09-17T11:20:00+05:30", "ltp": 1005.0,
    "patterns": [{"name": "Bullish Engulfing", "bias": "bullish"}],
    "reasons": [{"points": 2.0, "text": "Price > EMA20 > EMA50"}], "bear_reasons": [],
    "confirmations": ["trend", "momentum", "pattern"], "bear_confirmations": [], "blockers": [],
    "checklist": {"long": {"passed": True, "pattern": "Bullish Engulfing", "entry": 1005.0, "stop": 995.0,
                           "target": 1030.0, "rrr": 2.3, "size_factor": 1.0, "items": []}},
}
ROW = {"symbol": SYMBOL, "name": "Test Co", "industry": "IT", "side": "LONG", "status": "ACTIVE",
       "score": 55.0, "final_score": 60.0, "ltp": 1005.0, "chg_pct": 1.2,
       "reasons": [{"points": 20.0, "text": "Daily uptrend"}], "catalyst": None, "event": None,
       "swing_patterns": [], "large_deals": None}
MARKET = {"bias": "neutral", "nifty": {"chg_pct": 0.45}, "vix": 13.2, "vix_high": False}


class FakeState:
    def __init__(self):
        self.lock = threading.Lock()
        self.indicators = {SYMBOL: dict(ANALYSIS)}
        self.scanner = {"rows": [dict(ROW)], "sectors": [{"industry": "IT", "chg_pct": 0.8}],
                        "session_date": "2026-09-17", "market": MARKET}
        self.market = MARKET
        self.positions = {}


def point(text, *citations):
    return {"text": text, "citations": list(citations)}


GOOD = {
    rd.AnalystReport: {"stance": "bullish", "summary": "The checklist passed with RSI at 61.5.",
                       "points": [point("RSI is 61.5, inside the momentum zone.", "technical.rsi")]},
    rd.ResearcherCase: {"thesis": "Trend and pattern agree.", "rebuttal": "",
                        "points": [point("Bull score 7.0 beats bear score 2.0.", "technical.bull_score")]},
    rd.InvestmentPlan: {"rating": 1, "summary": "The evidence leans positive.",
                        "evidence": [point("The checklist passed.", "technical.checklist.passed")],
                        "key_risks": [point("The edge is unproven.", "risk.scorecard")],
                        "what_would_change_view": [point("A failed checklist.", "technical.checklist")]},
    rd.TraderProposal: {"proposal": "long", "entry": 1005.0, "stop": 995.0, "target": 1030.0,
                        "rationale": "The checklist passed.",
                        "points": [point("The stop is 995.0.", "technical.checklist.stop")]},
    rd.RiskView: {"stance": "support", "summary": "Costs are small next to the stop.",
                  "points": [point("The stop clears the cost floor.", "risk.plan.stop_to_cost_ratio")]},
    rd.FinalDecision: {"rating": 1, "proposal_verdict": "approve", "executive_summary": "Positive lean.",
                       "investment_thesis": "Trend, pattern and checklist agree.",
                       "evidence": [point("RSI is 61.5.", "technical.rsi")],
                       "key_risks": [point("The edge is unproven.", "risk.scorecard")]},
}


class FakeBackend:
    name = "fake"
    label = "Fake"

    def __init__(self, outputs=None, cost=0.01, delay=0.0):
        self.outputs = {**GOOD, **(outputs or {})}
        self.cost = cost
        self.delay = delay
        self.calls = []
        self.active = 0
        self.peak = 0
        self._lock = threading.Lock()

    def ask(self, model, effort, system, snapshot_text, task, schema_cls):
        with self._lock:
            self.calls.append((schema_cls.__name__, model, effort, task.splitlines()[0]))
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(self.delay)
        with self._lock:
            self.active -= 1
        return json.dumps(self.outputs[schema_cls]), {
            "models": [model], "input_tokens": 100, "output_tokens": 50, "cost_usd": self.cost, "turns": 1}


@pytest.fixture(autouse=True)
def desk(monkeypatch):
    monkeypatch.setitem(config.RESEARCH_DESK, "enabled", True)
    monkeypatch.setitem(config.RESEARCH_DESK, "llm_backend", "claude_cli")
    monkeypatch.setitem(config.RISK, "total_capital", 100000)  # other tests leave this changed
    monkeypatch.setattr(rd, "_cli_binary", lambda: "/usr/local/bin/claude")
    monkeypatch.setattr(rd, "_usage", {"date": None, "briefs": 0, "calls": 0, "input_tokens": 0,
                                       "output_tokens": 0, "cost_usd": 0.0})
    monkeypatch.setattr(rd, "_run", {"running": False, "symbols": [], "done": [], "current": None, "stages": [],
                                     "started_at": None, "finished_at": None, "stopped_reason": None})
    monkeypatch.setattr(rd.fundamentals, "get_fundamentals",
                        lambda s: {"score": 2.0, "label": "Strong", "metrics": [
                            {"label": "Return on equity", "value": 0.2, "points": 1.0, "text": "Return on equity 20.0%"}]})
    monkeypatch.setattr(rd.news_sentiment, "get_sentiment",
                        lambda s, n=None: {"score": 0.2, "count": 1, "sources": {"Google News": 1},
                                           "headlines": [{"title": "Test Co wins order", "publisher": "P",
                                                          "age_h": 3.0, "score": 0.4}]})


# ---- switched off / unavailable -------------------------------------------

def test_desk_is_off_by_default():
    assert DEFAULT_ENABLED is False


def test_refuses_to_run_when_switched_off(monkeypatch):
    monkeypatch.setitem(config.RESEARCH_DESK, "enabled", False)
    started, message, _ = rd.request_run(FakeState(), [SYMBOL], backend=FakeBackend())
    assert started is False and "switched off" in message
    assert rd.run_brief(FakeState(), SYMBOL, backend=FakeBackend())["ran"] is False


def test_backend_selection(monkeypatch):
    monkeypatch.setitem(config.RESEARCH_DESK, "llm_backend", "auto")
    monkeypatch.setitem(config.NEWS, "anthropic_api_key", "sk-test")
    assert rd.backend_name() == "anthropic_api"
    monkeypatch.setitem(config.NEWS, "anthropic_api_key", "")
    assert rd.backend_name() == "claude_cli"
    monkeypatch.setattr(rd, "_cli_binary", lambda: None)
    assert rd.backend_name() is None
    assert "No LLM is available" in rd._blocked_reason()


# ---- a full brief ------------------------------------------------------------

def test_full_brief_runs_every_role_in_order_and_logs_the_rating():
    backend = FakeBackend()
    result = rd.run_brief(FakeState(), SYMBOL, backend=backend)
    assert result["ran"] and result["status"] == "complete" and result["rating"] == 1

    names = [c[0] for c in backend.calls]
    assert sorted(names[:4]) == ["AnalystReport"] * 4
    assert names[4:] == ["ResearcherCase", "ResearcherCase", "InvestmentPlan", "TraderProposal",
                         "RiskView", "RiskView", "RiskView", "FinalDecision"]
    assert {c[1] for c in backend.calls[:4]} == {config.RESEARCH_DESK["analyst_model"]}
    assert {c[1] for c in backend.calls[4:]} == {config.RESEARCH_DESK["team_model"]}
    assert [c[3] for c in backend.calls[8:11]] == [
        "Your role: Aggressive risk analyst on the risk management team.",
        "Your role: Conservative risk analyst on the risk management team.",
        "Your role: Neutral risk analyst on the risk management team."]

    brief = database.recent_research_briefs(SYMBOL, limit=1)[0]
    assert brief["rating"] == 1
    rep = brief["reports"]
    assert rep["research_only"] is True and rep["decision"]["rating_label"] == "Overweight"
    assert rep["trader"]["stop"] == 995.0 and not rep["rejected"]
    assert brief["snapshot"]["technical"]["checklist"]["stop"] == 995.0
    assert all(s["status"] == "done" for s in rd._run["stages"])


def test_analysts_run_in_parallel():
    backend = FakeBackend(delay=0.2)
    rd.run_brief(FakeState(), SYMBOL, backend=backend)
    assert backend.peak == len(rd.ANALYSTS)


def test_rating_ic_waits_for_enough_sessions():
    rd.run_brief(FakeState(), SYMBOL, backend=FakeBackend())
    ic = database.research_rating_ic()
    assert ic["ic"] is None and ic["passes"] is False and "Not enough data" in ic["note"]


# ---- grounding ------------------------------------------------------------

def test_invented_numbers_and_missing_fields_are_dropped():
    backend = FakeBackend(outputs={rd.AnalystReport: {
        "stance": "bullish", "summary": "RSI is 61.5.",
        "points": [point("RSI is 61.5.", "technical.rsi"),
                   point("RSI is 99.9, very strong.", "technical.rsi"),
                   point("The moon phase is favourable.", "technical.moon")]}})
    rd.run_brief(FakeState(), SYMBOL, backend=backend)
    rep = database.recent_research_briefs(SYMBOL, limit=1)[0]["reports"]
    report = rep["analysts"]["market"]["report"]
    assert [p["text"] for p in report["points"]] == ["RSI is 61.5."]
    reasons = {r["reason"] for r in rep["rejected"] if r["agent"] == "market"}
    assert any("99.9" in r for r in reasons) and any("technical.moon" in r for r in reasons)


def test_trader_cannot_invent_levels():
    backend = FakeBackend(outputs={rd.TraderProposal: {**GOOD[rd.TraderProposal], "stop": 990.0}})
    rd.run_brief(FakeState(), SYMBOL, backend=backend)
    rep = database.recent_research_briefs(SYMBOL, limit=1)[0]["reports"]
    assert rep["trader"]["stop"] is None and rep["trader"]["proposal"] == "stand_aside"
    assert any(r["agent"] == "trader" and r["field"] == "stop" for r in rep["rejected"])


def test_a_rating_without_grounded_evidence_is_withheld():
    backend = FakeBackend(outputs={rd.FinalDecision: {
        **GOOD[rd.FinalDecision], "evidence": [point("RSI is 77.7.", "technical.rsi")]}})
    result = rd.run_brief(FakeState(), SYMBOL, backend=backend)
    assert result["status"] == "ungrounded" and result["rating"] is None
    assert database.recent_research_briefs(SYMBOL, limit=1)[0]["rating"] is None


def test_malformed_output_is_recorded_not_raised():
    class Broken(FakeBackend):
        def ask(self, model, effort, system, snapshot_text, task, schema_cls):
            if schema_cls is rd.InvestmentPlan:
                return '{"rating": 7}', {"models": [model], "input_tokens": 1, "output_tokens": 1,
                                         "cost_usd": 0.0, "turns": 1}
            return super().ask(model, effort, system, snapshot_text, task, schema_cls)
    result = rd.run_brief(FakeState(), SYMBOL, backend=Broken())
    assert result["status"] == "partial" and result["rating"] is None
    rep = database.recent_research_briefs(SYMBOL, limit=1)[0]["reports"]
    assert any(e["agent"] == "research_manager" for e in rep["errors"])
    assert rep["trader"] is None and rep["decision"] is None


# ---- budgets --------------------------------------------------------------

def test_daily_brief_limit(monkeypatch):
    monkeypatch.setitem(config.RESEARCH_DESK, "daily_brief_limit", 1)
    assert rd.run_brief(FakeState(), SYMBOL, backend=FakeBackend())["ran"] is True
    second = rd.run_brief(FakeState(), SYMBOL, backend=FakeBackend())
    assert second["ran"] is False and "brief limit" in second["reason"]


def test_cost_limit_stops_a_brief_midway(monkeypatch):
    monkeypatch.setitem(config.RESEARCH_DESK, "daily_cost_limit_usd", 1.0)
    backend = FakeBackend(cost=0.3)
    result = rd.run_brief(FakeState(), SYMBOL, backend=backend)
    assert result["status"] == "partial" and result["budget_stop"] is True
    assert len(backend.calls) < 12


def test_background_run_reports_progress_and_finishes():
    started, _, thread = rd.request_run(FakeState(), [SYMBOL], backend=FakeBackend())
    assert started
    thread.join(timeout=10)
    st = rd.stats()
    assert st["run"]["running"] is False
    assert st["run"]["done"][0]["symbol"] == SYMBOL and st["run"]["done"][0]["status"] == "complete"
    assert st["briefs_today"] == 1 and st["calls_today"] == 12 and st["research_only"] is True


# ---- research only ----------------------------------------------------------

def test_desk_has_no_path_to_orders_or_gates():
    source = inspect.getsource(rd)
    for forbidden in ("place_order", "_execute", "execute_paper_order", "kite_executor",
                      "import trading_engine", "paper_broker", "kite_broker", "strategy_state"):
        assert forbidden not in source, forbidden


# ---- CLI backend ------------------------------------------------------------

class Proc:
    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


def test_cli_backend_runs_claude_with_everything_switched_off():
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"], seen["kwargs"] = cmd, kwargs
        return Proc(json.dumps({"is_error": False, "num_turns": 2, "total_cost_usd": 0.0123,
                                "structured_output": GOOD[rd.RiskView],
                                "usage": {"input_tokens": 10, "cache_read_input_tokens": 5,
                                          "cache_creation_input_tokens": 20, "output_tokens": 7},
                                "modelUsage": {"claude-sonnet-5": {}}}))

    backend = rd.ClaudeCliBackend(binary="/usr/local/bin/claude", run=fake_run)
    text, info = backend.ask("claude-sonnet-5", "medium", "SYSTEM", "{}", "TASK", rd.RiskView)
    cmd = seen["cmd"]
    assert cmd[:2] == ["/usr/local/bin/claude", "-p"]
    for flag, value in (("--tools", ""), ("--setting-sources", ""), ("--model", "claude-sonnet-5"),
                        ("--effort", "medium"), ("--system-prompt", "SYSTEM"), ("--output-format", "json")):
        assert cmd[cmd.index(flag) + 1] == value
    assert "--strict-mcp-config" in cmd and "--no-session-persistence" in cmd and "--disable-slash-commands" in cmd
    assert json.loads(cmd[cmd.index("--json-schema") + 1]) == rd.api_schema(rd.RiskView)
    assert json.loads(text) == GOOD[rd.RiskView]
    assert info == {"models": ["claude-sonnet-5"], "input_tokens": 35, "output_tokens": 7,
                    "cost_usd": 0.0123, "turns": 2}


@pytest.mark.parametrize("proc, message", [
    (Proc(json.dumps({"is_error": True, "result": "Usage limit reached"})), "reported an error"),
    (Proc("not json", returncode=1, stderr="boom"), "returned no JSON"),
])
def test_cli_backend_errors_become_agent_errors(proc, message):
    backend = rd.ClaudeCliBackend(binary="/usr/local/bin/claude", run=lambda cmd, **kw: proc)
    with pytest.raises(rd.AgentError, match=message):
        backend.ask("m", "low", "S", "{}", "T", rd.RiskView)


def test_cli_backend_timeout_becomes_an_agent_error():
    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)
    with pytest.raises(rd.AgentError, match="timed out"):
        rd.ClaudeCliBackend(binary="/usr/local/bin/claude", run=slow).ask("m", "low", "S", "{}", "T", rd.RiskView)


# ---- API backend --------------------------------------------------------------

def test_api_backend_prices_the_reported_tokens():
    class Usage:
        input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens = 1000, 500, 2000, 400

    class Block:
        type, text = "text", json.dumps(GOOD[rd.RiskView])

    class Resp:
        stop_reason, content, usage, model = "end_turn", [Block()], Usage(), "claude-sonnet-5"

    class Client:
        class messages:
            @staticmethod
            def create(**kwargs):
                assert kwargs["output_config"]["format"]["schema"] == rd.api_schema(rd.RiskView)
                return Resp()

    text, info = rd.AnthropicApiBackend(client=Client()).ask("claude-sonnet-5", "medium", "S", "{}", "T", rd.RiskView)
    assert json.loads(text) == GOOD[rd.RiskView]
    expected = (1000 * 2.0 + 400 * 2.0 * 1.25 + 2000 * 2.0 * 0.1 + 500 * 10.0) / 1e6
    assert info["cost_usd"] == pytest.approx(expected) and info["input_tokens"] == 3400
