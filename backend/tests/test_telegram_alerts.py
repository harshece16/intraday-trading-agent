"""
Telegram phone alerts (telegram_alerts.py). The network is never touched:
requests.post is replaced, and conftest blanks the credentials by default.
"""
import logging

import pytest
import requests

import telegram_alerts as tg
from state import AppState


@pytest.fixture
def sent(monkeypatch):
    """Configure a fake bot and capture what would be posted, synchronously."""
    monkeypatch.setattr(tg, "_token", "123:SECRET")
    monkeypatch.setattr(tg, "_chat_id", "42")
    monkeypatch.setattr(tg, "enabled", True)
    monkeypatch.setattr(tg, "_recent", {})
    out = []

    class Capture:
        def put_nowait(self, text):
            out.append(text)

    monkeypatch.setattr(tg, "_queue", Capture())
    monkeypatch.setattr(tg, "_ensure_worker", lambda: None)
    return out


def test_only_actionable_lines_are_sent():
    assert tg.wants("trade", "trade")
    assert tg.wants("error", "error")
    assert tg.wants("risk", "info")
    assert tg.wants("summary", "info")
    assert tg.wants("system", "warn")        # mode switches
    assert tg.wants("review", "warn")        # a card waiting for a decision
    assert not tg.wants("review", "info")    # "You rejected ..." — you know
    assert not tg.wants("system", "info")
    assert not tg.wants("scan", "info")
    assert not tg.wants("watchlist", "info")
    assert not tg.wants("blocked", "warn")   # dozens a day; the summary covers them


def test_nothing_is_sent_when_not_configured():
    assert tg.configured() is False          # conftest blanks the credentials
    assert tg.notify("trade", "BUY 1 @ 100", level="trade") is False
    assert tg.send_now("hi")["ok"] is False


def test_nothing_is_sent_when_switched_off(sent, monkeypatch):
    monkeypatch.setattr(tg, "enabled", False)
    assert tg.notify("trade", "BUY 1 @ 100", level="trade") is False
    assert sent == []


def test_a_fill_logged_by_the_engine_reaches_the_phone_with_its_mode(sent):
    st = AppState(watchlist=[], paper_mode=False)
    st.log("trade", "BUY 12 @ 2915.40 (signal)", symbol="RELIANCE", level="trade")
    st.log("scan", "Scanned 100 stocks")
    assert sent == ["[LIVE] TRADE · RELIANCE\nBUY 12 @ 2915.40 (signal)"]


def test_the_same_line_twice_is_sent_once(sent):
    tg.notify("error", "quote timeout", level="error")
    tg.notify("error", "quote timeout", level="error")
    assert len(sent) == 1


def test_a_failure_never_logs_the_bot_token(monkeypatch, caplog):
    monkeypatch.setattr(tg, "_token", "123:SECRET")
    monkeypatch.setattr(tg, "_chat_id", "42")

    def boom(url, **kw):
        raise requests.ConnectionError(f"Max retries exceeded with url: {url}")

    monkeypatch.setattr(tg.requests, "post", boom)
    with caplog.at_level(logging.WARNING, logger="trading_bot"):
        out = tg.send_now("hi")
    assert out["ok"] is False
    assert "SECRET" not in caplog.text and "SECRET" not in out["error"]


def test_a_rejected_send_reports_telegrams_reason(monkeypatch):
    monkeypatch.setattr(tg, "_token", "123:SECRET")
    monkeypatch.setattr(tg, "_chat_id", "42")

    class R:
        status_code = 400

        def json(self):
            return {"description": "Bad Request: chat not found"}

    monkeypatch.setattr(tg.requests, "post", lambda url, **kw: R())
    assert tg.send_now("hi") == {"ok": False, "error": "HTTP 400 Bad Request: chat not found"}
