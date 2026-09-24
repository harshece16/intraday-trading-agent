"""auth.py: the dashboard key goes in a header or a WebSocket message, never
a URL, and any key= that reaches a uvicorn log line is redacted (#87)."""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import auth
import config

KEY = "test-key_AbC123-xyz"


def _use_key(monkeypatch):
    monkeypatch.setattr(config, "DASHBOARD_API_KEY", KEY)


def test_key_ok_accepts_only_the_exact_key(monkeypatch):
    _use_key(monkeypatch)
    assert auth.key_ok(KEY) is True
    for bad in (None, "", KEY + "x", KEY[:-1], KEY.upper()):
        assert auth.key_ok(bad) is False


def test_key_ok_refuses_everything_when_no_key_is_configured(monkeypatch):
    monkeypatch.setattr(config, "DASHBOARD_API_KEY", "")
    assert auth.key_ok("") is False and auth.key_ok("anything") is False


class FakeSocket:
    def __init__(self, messages=None, hang=False):
        self.messages, self.hang, self.closed_with = list(messages or []), hang, None

    async def receive_text(self):
        if self.hang:
            await asyncio.sleep(3600)
        return self.messages.pop(0)

    async def close(self, code=1000):
        self.closed_with = code


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_websocket_first_message_with_the_key_is_accepted(monkeypatch):
    _use_key(monkeypatch)
    ws = FakeSocket([json.dumps({"type": "auth", "key": KEY})])
    assert _run(auth.authenticate_websocket(ws)) is True and ws.closed_with is None


def test_websocket_wrong_key_or_wrong_shape_is_closed_4401(monkeypatch):
    _use_key(monkeypatch)
    for first in (json.dumps({"type": "auth", "key": "nope"}), json.dumps({"key": KEY}),
                  json.dumps(["auth", KEY]), "not json"):
        ws = FakeSocket([first])
        assert _run(auth.authenticate_websocket(ws)) is False and ws.closed_with == 4401


def test_websocket_that_never_authenticates_is_closed(monkeypatch):
    _use_key(monkeypatch)
    monkeypatch.setattr(auth, "AUTH_TIMEOUT_S", 0.05)
    ws = FakeSocket(hang=True)
    assert _run(auth.authenticate_websocket(ws)) is False and ws.closed_with == 4401


def test_redact_removes_the_key_from_query_strings():
    assert auth.redact(f'"WebSocket /ws?key={KEY}" [accepted]') == '"WebSocket /ws?key=<redacted>" [accepted]'
    assert auth.redact(f"GET /api/state?x=1&key={KEY}&y=2") == "GET /api/state?x=1&key=<redacted>&y=2"
    assert auth.redact("GET /api/state?monkey=1") == "GET /api/state?monkey=1"   # not a key= param
    assert (auth.redact('"GET /kite/callback?action=login&status=success&request_token=AbC123xyz HTTP/1.1" 200')
            == '"GET /kite/callback?action=login&status=success&request_token=<redacted> HTTP/1.1" 200')


def test_filter_redacts_uvicorn_style_records_whose_path_is_an_argument(capsys):
    # uvicorn.access logs '%s - "%s %s HTTP/%s" %d' with the path in args, so a
    # filter that only looked at record.msg would miss it.
    logger = logging.getLogger("test.redaction")
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(auth.RedactKeyFilter())
    logger.addHandler(handler)
    logger.propagate = False
    try:
        logger.warning('%s - "%s %s HTTP/%s" %d', "127.0.0.1:1", "GET", f"/api/state?key={KEY}", "1.1", 200)
    finally:
        logger.removeHandler(handler)
    out = capsys.readouterr().out
    assert KEY not in out and "key=<redacted>" in out


def test_install_attaches_the_filter_once():
    auth.install_log_redaction()
    auth.install_log_redaction()
    n = sum(isinstance(f, auth.RedactKeyFilter) for f in logging.getLogger("uvicorn.access").filters)
    assert n == 1
