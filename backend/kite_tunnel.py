"""
The Kite login tunnel: started when the login starts, stopped when it ends.

Kite Connect only accepts an HTTPS Redirect URL, so the one registered for
this app is an ngrok static domain. The in-app "Connect Kite" flow therefore
only worked if someone had remembered to run `ngrok http 8000` first. Every
morning it didn't, Kite redirected to "ERR_NGROK_3200 ... is offline" and the
login was lost.

So the backend owns the tunnel. `/api/kite/login-url` calls `ensure_up()`,
which starts ngrok on the registered domain and waits until its local API
reports the tunnel; `/kite/callback` calls `stop_soon()`, which shuts it a
few seconds later, once the "connected" page has gone back out through it. A
timer stops it after `max_seconds` regardless, so an abandoned login doesn't
leave the backend on the internet. While it is up, every route except
/kite/callback still needs the dashboard key (ApiKeyMiddleware).

An ngrok already serving the domain (one started by hand, say) is reused,
and left running, since this module didn't start it.
"""

import json
import logging
import shutil
import subprocess
import threading
import time
import urllib.request

import config

logger = logging.getLogger("trading_bot")

_lock = threading.Lock()
_proc = None            # the ngrok process this module started, if any
_stop_timer = None


def _cfg():
    return getattr(config, "KITE_TUNNEL", {})


def enabled() -> bool:
    return bool(_cfg().get("enabled") and _cfg().get("domain"))


def public_url() -> str:
    return f"https://{_cfg()['domain']}"


def _tunnel_is_up(timeout=1.5) -> bool:
    """True if an ngrok agent on this machine reports a tunnel for our
    domain. Reads ngrok's local API rather than calling the public URL, which
    would hit /kite/callback's side effects."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{_cfg().get('api_port', 4040)}/api/tunnels",
                                    timeout=timeout) as r:
            tunnels = json.load(r).get("tunnels", [])
    except Exception:
        return False
    return any(t.get("public_url", "").rstrip("/") == public_url() for t in tunnels)


def _spawn():
    exe = shutil.which("ngrok")
    if not exe:
        raise RuntimeError("ngrok is not installed (brew install ngrok)")
    port = _cfg().get("backend_port", 8000)
    return subprocess.Popen([exe, "http", str(port), "--url", public_url(), "--log", "false"],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _schedule_stop(delay):
    global _stop_timer
    if _stop_timer:
        _stop_timer.cancel()
    _stop_timer = threading.Timer(delay, stop)
    _stop_timer.daemon = True
    _stop_timer.start()


def ensure_up(wait_s=None) -> dict:
    """Start the tunnel if it isn't up, and wait until ngrok reports it.
    Returns {"ok": bool, "started": bool, "error": str|None}."""
    global _proc
    wait_s = wait_s if wait_s is not None else _cfg().get("start_timeout_s", 15)
    with _lock:
        if _tunnel_is_up():
            if _proc is not None:
                _schedule_stop(_cfg().get("max_seconds", 600))
            return {"ok": True, "started": False, "error": None}
        try:
            _proc = _spawn()
        except Exception as exc:
            return {"ok": False, "started": False, "error": str(exc)}
        deadline = time.time() + wait_s
        while time.time() < deadline:
            if _proc.poll() is not None:
                err = (_proc.stderr.read() or b"").decode(errors="replace").strip()[-300:]
                _proc = None
                return {"ok": False, "started": False, "error": f"ngrok exited: {err or 'no output'}"}
            if _tunnel_is_up():
                _schedule_stop(_cfg().get("max_seconds", 600))
                logger.info(f"Kite login tunnel up at {public_url()} (stops after the login, or in "
                            f"{_cfg().get('max_seconds', 600) // 60} min)")
                return {"ok": True, "started": True, "error": None}
            time.sleep(0.3)
        _stop_locked()
        return {"ok": False, "started": False, "error": f"ngrok did not report the tunnel within {wait_s:g}s"}


def _stop_locked():
    global _proc
    if _proc is not None and _proc.poll() is None:
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _proc.kill()
        logger.info("Kite login tunnel stopped")
    _proc = None


def stop():
    """Stop the tunnel if this module started it. One started by hand is left alone."""
    global _stop_timer
    with _lock:
        if _stop_timer:
            _stop_timer.cancel()
            _stop_timer = None
        _stop_locked()


def stop_soon(delay_s=5.0):
    """Called from /kite/callback: its response still has to travel back
    through the tunnel, so it can't be torn down mid-request."""
    if _proc is not None:
        _schedule_stop(delay_s)


def running() -> bool:
    return _proc is not None and _proc.poll() is None
