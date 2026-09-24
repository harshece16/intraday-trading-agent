"""
Dashboard API key handling — in a header or a WebSocket message, never a URL.

The key gates every route, including the Live toggle. It used to be accepted
as a `?key=` query parameter, and the dashboard sent it that way on every
WebSocket connect, the Kite login popup and the trades CSV. uvicorn writes
each request line to backend.log, so the key sat there in plain text on
hundreds of lines (issue #87). A URL is the wrong place for a credential:
logs, browser history and proxies all keep it.

So:
- REST: only the `X-Api-Key` header counts (`key_ok`).
- WebSocket: browsers can't set a header on the handshake, so the socket is
  accepted and its FIRST message must be {"type": "auth", "key": ...}, within
  AUTH_TIMEOUT_S, or it is closed with 4401 (`authenticate_websocket`).
- Logging: `RedactKeyFilter` rewrites any `key=...` left in a uvicorn log
  line, so a stale bookmark or an old script still can't write the key to disk.
"""

import asyncio
import hmac
import json
import logging
import re

import config

AUTH_TIMEOUT_S = 5.0
# The dashboard key, and Kite's one-time request_token, which Kite puts in the
# /kite/callback URL: single-use and short-lived, but still a credential.
_KEY_IN_URL = re.compile(r"([?&](?:key|request_token)=)[^&\s\"']+")


def key_ok(candidate) -> bool:
    """Constant-time comparison, so a wrong key's timing says nothing about
    how close it was."""
    expected = config.DASHBOARD_API_KEY
    if not candidate or not expected:
        return False
    return hmac.compare_digest(str(candidate).encode(), expected.encode())


async def authenticate_websocket(websocket) -> bool:
    """Call after websocket.accept(). Returns True once the first message
    carries the right key; otherwise closes the socket with 4401."""
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_S)
        msg = json.loads(raw)
        ok = isinstance(msg, dict) and msg.get("type") == "auth" and key_ok(msg.get("key"))
    except Exception:
        ok = False
    if not ok:
        await websocket.close(code=4401)
    return ok


def redact(text: str) -> str:
    return _KEY_IN_URL.sub(r"\1<redacted>", text)


class RedactKeyFilter(logging.Filter):
    """Strips `key=...` from a record's formatted message. Formats it first,
    because uvicorn passes the request path as a %-argument, not in msg."""

    def filter(self, record):
        try:
            message = record.getMessage()
        except Exception:
            return True
        cleaned = redact(message)
        if cleaned != message:
            record.msg, record.args = cleaned, ()
        return True


def install_log_redaction():
    """Attach the filter to every logger uvicorn writes request lines with,
    and to their handlers, so it applies however the loggers are configured."""
    f = RedactKeyFilter()
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(name)
        if not any(isinstance(x, RedactKeyFilter) for x in lg.filters):
            lg.addFilter(f)
        for h in lg.handlers:
            if not any(isinstance(x, RedactKeyFilter) for x in h.filters):
                h.addFilter(f)
