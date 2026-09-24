"""
Phone alerts over Telegram, sent by the backend itself.

The browser notifications (frontend/src/notifications.js) only fire while a
dashboard tab is open, which is exactly when the owner doesn't need them. An
unattended engine needs a channel that reaches a phone with the laptop shut.

What is sent: the activity lines the engine already writes that someone
away from the screen would act on — fills, errors, risk events (loss limit,
square-off, kill switch, pause), review-queue cards waiting for a decision,
warn-level system events (mode switches) and the end-of-session summary.
Scans, watchlist churn and blocked signals stay on the dashboard.

Setup: create a bot with @BotFather, message it once, then put
{"bot_token": "...", "chat_id": "..."} in backend/.telegram.json (gitignored),
or set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID, and restart. Unconfigured, every
call here is a no-op.

Sending never blocks the engine: messages go on a queue and one daemon thread
posts them. The bot token is part of Telegram's URL, so it is never logged —
a failure logs the status code only.
"""

import json
import logging
import os
import queue
import threading
import time
from pathlib import Path

import requests

logger = logging.getLogger("trading_bot")

_FILE = Path(__file__).parent / ".telegram.json"
API = "https://api.telegram.org/bot{token}/sendMessage"

ALWAYS = {"trade", "error", "risk", "summary"}
WARN_ONLY = {"system", "review"}
DEDUPE_SECONDS = 30 * 60    # the same line again within 30 min is dropped
MAX_PER_MINUTE = 20         # Telegram allows ~30/s; this is about not spamming a phone
TIMEOUT = 10


def _load():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (token and chat) and _FILE.exists():
        try:
            d = json.loads(_FILE.read_text())
            token, chat = token or d.get("bot_token", ""), chat or str(d.get("chat_id", ""))
        except (OSError, json.JSONDecodeError):
            logger.warning("backend/.telegram.json is unreadable — Telegram alerts are off")
    return token, chat


_token, _chat_id = _load()
enabled = True              # the dashboard's on/off; configured() is the other half
_queue = queue.Queue(maxsize=200)
_recent = {}                # text -> last sent ts, for dedupe
_sent_ts = []               # send times in the last minute, for the rate cap
_lock = threading.Lock()
_worker = None
last_error = None


def configured() -> bool:
    return bool(_token and _chat_id)


def status():
    return {"configured": configured(), "enabled": enabled, "last_error": last_error}


def wants(kind, level) -> bool:
    return kind in ALWAYS or level in ("trade", "error") or (kind in WARN_ONLY and level == "warn")


def format_line(kind, message, symbol=None, paper_mode=True):
    mode = "PAPER" if paper_mode else "LIVE"
    head = f"[{mode}] {kind.upper()}" + (f" · {symbol}" if symbol else "")
    return f"{head}\n{message}"


def notify(kind, message, symbol=None, level="info", paper_mode=True):
    """Queue an activity line for Telegram if it's one worth a phone alert."""
    if not (configured() and enabled and wants(kind, level)):
        return False
    return enqueue(format_line(kind, message, symbol, paper_mode))


def enqueue(text) -> bool:
    now = time.time()
    with _lock:
        if now - _recent.get(text, 0) < DEDUPE_SECONDS:
            return False
        _recent[text] = now
        for k in [k for k, ts in _recent.items() if now - ts > DEDUPE_SECONDS]:
            del _recent[k]
    try:
        _queue.put_nowait(text)
    except queue.Full:
        return False
    _ensure_worker()
    return True


def send_now(text) -> dict:
    """Send synchronously and report the outcome — the dashboard's test button."""
    if not configured():
        return {"ok": False, "error": "Telegram isn't set up (backend/.telegram.json)."}
    return _post(text)


def _post(text):
    global last_error
    try:
        r = requests.post(API.format(token=_token), json={"chat_id": _chat_id, "text": text[:4000],
                                                          "disable_web_page_preview": True}, timeout=TIMEOUT)
    except requests.RequestException as exc:
        # The exception text can contain the URL, and the URL contains the token.
        last_error = f"network error ({type(exc).__name__})"
        logger.warning(f"Telegram alert not sent: {last_error}")
        return {"ok": False, "error": last_error}
    if r.status_code != 200:
        try:
            desc = r.json().get("description", "")
        except ValueError:
            desc = ""
        last_error = f"HTTP {r.status_code} {desc}".strip()
        logger.warning(f"Telegram alert not sent: {last_error}")
        return {"ok": False, "error": last_error}
    last_error = None
    return {"ok": True}


def _run():
    while True:
        text = _queue.get()
        with _lock:
            now = time.time()
            _sent_ts[:] = [t for t in _sent_ts if now - t < 60]
            wait = 60 - (now - _sent_ts[0]) if len(_sent_ts) >= MAX_PER_MINUTE else 0
        if wait > 0:
            time.sleep(wait)
        with _lock:
            _sent_ts.append(time.time())
        _post(text)


def _ensure_worker():
    global _worker
    with _lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run, name="telegram-alerts", daemon=True)
            _worker.start()
