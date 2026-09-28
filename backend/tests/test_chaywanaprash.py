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
from datetime import datetime, timedelta, timezone
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


IST = timezone(timedelta(hours=5, minutes=30))
MONDAY_AFTER_CLOSE = datetime(2026, 9, 28, 15, 45, tzinfo=IST)


@pytest.fixture
def review_on(monkeypatch):
    monkeypatch.setattr(config, "CHAYWANAPRASH", {**config.CHAYWANAPRASH, "enabled": True, "review_every_days": 7,
                                                  "review_lookback_days": 14, "review_after": "15:40"})
    monkeypatch.setattr(chaywanaprash, "_review", {"date": None})


def test_review_is_due_after_the_close_on_a_trading_day_only(review_on):
    assert chaywanaprash.review_due(MONDAY_AFTER_CLOSE, holiday=False)
    assert not chaywanaprash.review_due(MONDAY_AFTER_CLOSE.replace(hour=15, minute=30), holiday=False)
    assert not chaywanaprash.review_due(MONDAY_AFTER_CLOSE, holiday=True)
    assert not chaywanaprash.review_due(MONDAY_AFTER_CLOSE + timedelta(days=5), holiday=False)  # Saturday


def test_review_waits_a_week_after_a_two_week_report_with_a_narrative(review_on):
    database.record_chaywanaprash_report(14 * 24, True, "narrative", {})
    assert not chaywanaprash.review_due(MONDAY_AFTER_CLOSE, holiday=False)


def test_review_looks_at_the_reports_once_a_day(review_on, monkeypatch):
    reads = []
    monkeypatch.setattr(database, "recent_chaywanaprash_reports",
                        lambda limit: reads.append(1) or [{"llm_used": True, "lookback_hours": 336, "ts": 1e12}])
    for minute in (41, 42, 43):
        assert not chaywanaprash.review_due(MONDAY_AFTER_CLOSE.replace(minute=minute), holiday=False)
    assert len(reads) == 1


def test_a_stats_only_or_one_day_report_does_not_count_as_the_review(review_on):
    database.record_chaywanaprash_report(14 * 24, False, None, {})  # the LLM failed
    database.record_chaywanaprash_report(24, True, "narrative", {})  # a manual one-day run
    assert chaywanaprash.review_due(MONDAY_AFTER_CLOSE, holiday=False)


def test_review_runs_off_the_tick_thread_and_logs_the_outcome(review_on, monkeypatch):
    runs, logged = [], []
    monkeypatch.setattr(chaywanaprash, "analyze",
                        lambda **kw: runs.append(kw) or {"llm_used": True, "narrative": "x", "note": None})

    class InlineThread:
        def __init__(self, target, **kw):
            self.target = target

        def start(self):
            self.target()
    monkeypatch.setattr(chaywanaprash.threading, "Thread", InlineThread)
    log = lambda kind, message, **kw: logged.append(message)

    assert chaywanaprash.maybe_start_review(MONDAY_AFTER_CLOSE, False, log) is True
    assert runs == [{"hours": 14 * 24, "changes": True}]
    assert "review of the last 14 days is saved" in logged[0]
    # One attempt a day, even though no report was saved.
    assert chaywanaprash.maybe_start_review(MONDAY_AFTER_CLOSE, False, log) is False


def test_the_review_reads_merged_changes_and_the_rules_and_asks_for_the_review(monkeypatch):
    changes = chaywanaprash._recent_changes(14)
    assert changes["window_days"] == 14
    assert isinstance(changes["merged_changes"], list)
    assert changes["rules"] and all(r["area"] not in ("security", "ui", "workflow") for r in changes["rules"])

    monkeypatch.setattr(chaywanaprash, "backends", lambda: ["claude_cli"])
    sent = []
    monkeypatch.setattr(chaywanaprash, "_ask_cli", lambda content: sent.append(content) or ("r", 1, 1))
    chaywanaprash._ask_llm({"recent_changes": changes})
    assert "fortnightly review of Sahab's Dimaag" in sent[0]
    chaywanaprash._ask_llm({"checklist_blockers": {}})
    assert "fortnightly review" not in sent[1]


def test_recent_changes_survives_git_being_unavailable(monkeypatch):
    def no_git(*a, **kw):
        raise FileNotFoundError("git")
    monkeypatch.setattr(chaywanaprash.subprocess, "run", no_git)
    assert "git log unavailable" in chaywanaprash._recent_changes(14)["merged_changes"]
