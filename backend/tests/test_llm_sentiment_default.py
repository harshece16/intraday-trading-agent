"""#160: LLM headline scoring is off by default, even with ANTHROPIC_API_KEY
set. Only the dashboard switch (or config, by hand) turns it on, and the
switch's position is kept in the journal across a restart."""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import database
import llm_sentiment
import trading_engine
from state import AppState

CONFIG_PY = Path(__file__).parent.parent / "config.py"


def _fresh_config(monkeypatch, api_key):
    """config.py executed again as a separate module, under a given
    environment, without touching the imported `config` other tests use."""
    monkeypatch.setenv("DASHBOARD_API_KEY", "test-dashboard-key")   # no key file is created
    if api_key is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)
    spec = importlib.util.spec_from_file_location("config_fresh_for_test", CONFIG_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_key_alone_does_not_turn_headline_scoring_on(monkeypatch):
    with_key = _fresh_config(monkeypatch, "sk-ant-test-not-a-real-key")
    assert with_key.NEWS["anthropic_api_key"] == "sk-ant-test-not-a-real-key"
    assert with_key.NEWS["use_llm_sentiment"] is False
    without_key = _fresh_config(monkeypatch, None)
    assert without_key.NEWS["use_llm_sentiment"] is False


def test_chaywanaprash_does_not_follow_the_key(monkeypatch):
    """Chaywanaprash is on by default on purpose (README sections 92 and 95:
    it runs when asked and once a week, on the API or the Claude Code CLI).
    Whether a key is set chooses its backend, not whether it runs."""
    with_key = _fresh_config(monkeypatch, "sk-ant-test-not-a-real-key")
    without_key = _fresh_config(monkeypatch, None)
    assert with_key.CHAYWANAPRASH["enabled"] is True
    assert without_key.CHAYWANAPRASH["enabled"] is True


def test_off_means_no_api_call_even_with_a_key(monkeypatch):
    monkeypatch.setattr(config, "NEWS", {**config.NEWS, "anthropic_api_key": "sk-ant-test",
                                         "use_llm_sentiment": False})
    monkeypatch.setattr(llm_sentiment, "_cache", {})

    def no_client():
        raise AssertionError("the API must not be called while the switch is off")

    monkeypatch.setattr(llm_sentiment, "_get_client", no_client)
    assert llm_sentiment.score_headline("Company wins a large order") is None
    assert llm_sentiment.stats()["enabled"] is False


def _engine():
    e = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    e.scanner = None
    return e


def test_the_switch_is_saved_and_a_restart_keeps_it(monkeypatch):
    monkeypatch.setattr(config, "NEWS", {**config.NEWS, "anthropic_api_key": "sk-ant-test",
                                         "use_llm_sentiment": False})
    assert llm_sentiment.set_enabled(True) is True
    assert database.get_control(llm_sentiment.CONTROL_KEY) is True

    config.NEWS["use_llm_sentiment"] = False        # what a restart starts from
    _engine()
    assert config.NEWS["use_llm_sentiment"] is True

    llm_sentiment.set_enabled(False)
    config.NEWS["use_llm_sentiment"] = True         # e.g. set by hand before the switch was used
    _engine()
    assert config.NEWS["use_llm_sentiment"] is False


def test_a_switch_never_used_leaves_the_default(monkeypatch):
    monkeypatch.setattr(config, "NEWS", {**config.NEWS, "use_llm_sentiment": False})
    assert database.get_control(llm_sentiment.CONTROL_KEY) is None
    _engine()
    assert config.NEWS["use_llm_sentiment"] is False
