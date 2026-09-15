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

import chaywanaprash
import config
import database


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
