"""
Chaywanaprash is the platform's own research analyst (see
chaywanaprash.py's docstring for the full picture) — it reads real stats
out of the journal database and, when an LLM key is configured, asks
Claude to turn them into recommendations. These tests cover the part that
must never break regardless of whether a key is configured: it always
returns the real computed stats, and it never fabricates a narrative
when it can't actually call an LLM.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from types import SimpleNamespace

import pytest

import chaywanaprash
import config
import database
import research_desk


@pytest.fixture(autouse=True)
def no_cli(monkeypatch):
    """No test may reach the real `claude` binary on the machine running it."""
    monkeypatch.setattr(research_desk, "_cli_binary", lambda: None)


def test_analyze_without_api_key_returns_real_stats_no_fake_narrative(monkeypatch):
    monkeypatch.setattr(config, "CHAYWANAPRASH", {**config.CHAYWANAPRASH, "enabled": True})
    monkeypatch.setattr(config, "NEWS", {**config.NEWS, "anthropic_api_key": ""})

    result = chaywanaprash.analyze(hours=24, persist=False)

    assert result["llm_used"] is False
    assert result["narrative"] is None
    assert "No ANTHROPIC_API_KEY" in result["note"]
    assert "checklist_blockers" in result["findings"]
    assert "journal_summary" in result["findings"]


def test_analyze_disabled_still_returns_real_stats(monkeypatch):
    monkeypatch.setattr(config, "CHAYWANAPRASH", {**config.CHAYWANAPRASH, "enabled": False})
    monkeypatch.setattr(config, "NEWS", {**config.NEWS, "anthropic_api_key": "dummy-key"})

    result = chaywanaprash.analyze(hours=24, persist=False)

    assert result["llm_used"] is False
    assert "disabled" in result["note"]
    assert result["findings"]["checklist_blockers"]["window_hours"] == 24


def test_analyze_survives_llm_call_failure(monkeypatch):
    monkeypatch.setattr(config, "CHAYWANAPRASH", {**config.CHAYWANAPRASH, "enabled": True, "daily_limit": 12})
    monkeypatch.setattr(config, "NEWS", {**config.NEWS, "anthropic_api_key": "dummy-key"})

    def boom(findings):
        raise RuntimeError("Anthropic API unreachable")
    monkeypatch.setattr(chaywanaprash, "_ask_llm", boom)

    result = chaywanaprash.analyze(hours=24, persist=False)  # must not raise

    assert result["llm_used"] is False
    assert "LLM call failed" in result["note"]
    assert result["findings"] is not None


def test_analyze_respects_daily_budget(monkeypatch):
    monkeypatch.setattr(config, "CHAYWANAPRASH", {**config.CHAYWANAPRASH, "enabled": True, "daily_limit": 1})
    monkeypatch.setattr(config, "NEWS", {**config.NEWS, "anthropic_api_key": "dummy-key"})
    monkeypatch.setattr(chaywanaprash, "_budget", {"date": None, "used": 0})

    calls = []
    def fake_ask(findings):
        calls.append(1)
        return "narrative", 10, 20
    monkeypatch.setattr(chaywanaprash, "_ask_llm", fake_ask)

    first = chaywanaprash.analyze(hours=24, persist=False)
    second = chaywanaprash.analyze(hours=24, persist=False)

    assert first["llm_used"] is True
    assert second["llm_used"] is False
    assert "used up" in second["note"]
    assert len(calls) == 1


def test_checklist_blocker_stats_shape_with_no_data():
    stats = database.checklist_blocker_stats(hours=1)
    assert stats["window_hours"] == 1
    assert stats["total_evaluations"] == 0
    assert stats["rrr_distribution"] is None


def test_record_and_read_chaywanaprash_report():
    database.record_chaywanaprash_report(24, True, "test narrative", {"a": 1}, 10, 20)
    reports = database.recent_chaywanaprash_reports(limit=5)
    assert len(reports) == 1
    assert reports[0]["narrative"] == "test narrative"
    assert reports[0]["findings"] == {"a": 1}
    assert reports[0]["llm_used"] is True


def _cli_reply(**over):
    body = {"is_error": False, "result": "1. Fix the thing.", "usage": {"input_tokens": 7, "output_tokens": 3}}
    body.update(over)
    return SimpleNamespace(stdout=json.dumps(body), stderr="", returncode=0)


def test_cli_is_used_when_there_is_no_api_key(monkeypatch):
    monkeypatch.setattr(config, "CHAYWANAPRASH", {**config.CHAYWANAPRASH, "enabled": True, "llm_backend": "auto"})
    monkeypatch.setattr(config, "NEWS", {**config.NEWS, "anthropic_api_key": ""})
    monkeypatch.setattr(research_desk, "_cli_binary", lambda: "/fake/claude")
    monkeypatch.setattr(chaywanaprash, "_budget", {"date": None, "used": 0})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return _cli_reply()
    monkeypatch.setattr(chaywanaprash.subprocess, "run", fake_run)

    result = chaywanaprash.analyze(hours=24, persist=False)

    assert result["llm_used"] is True
    assert result["narrative"] == "1. Fix the thing."
    assert seen["cmd"][0] == "/fake/claude"
    assert "checklist_blockers" in seen["input"]  # the real findings went in
    assert "ANTHROPIC_API_KEY" not in seen["env"]  # so the CLI uses the plan login


def test_auto_falls_back_to_cli_when_the_api_call_fails(monkeypatch):
    monkeypatch.setattr(config, "CHAYWANAPRASH", {**config.CHAYWANAPRASH, "llm_backend": "auto"})
    monkeypatch.setattr(config, "NEWS", {**config.NEWS, "anthropic_api_key": "bad-key"})
    monkeypatch.setattr(research_desk, "_cli_binary", lambda: "/fake/claude")

    def bad_api(content):
        raise RuntimeError("401 invalid x-api-key")
    monkeypatch.setattr(chaywanaprash, "_ask_api", bad_api)
    monkeypatch.setattr(chaywanaprash, "_ask_cli", lambda content: ("from the cli", 1, 2))

    assert chaywanaprash.backends() == ["anthropic_api", "claude_cli"]
    assert chaywanaprash._ask_llm({"x": 1}) == ("from the cli", 1, 2)


def test_cli_error_is_not_turned_into_a_narrative(monkeypatch):
    monkeypatch.setattr(research_desk, "_cli_binary", lambda: "/fake/claude")
    with pytest.raises(RuntimeError):
        chaywanaprash._ask_cli("x", run=lambda cmd, **kw: _cli_reply(is_error=True, result="Not logged in"))
