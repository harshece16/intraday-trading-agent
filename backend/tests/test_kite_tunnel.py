"""kite_tunnel.py: the backend owns the ngrok tunnel Kite redirects through.
Started (and waited on) when a login starts, stopped after the callback or a
timeout, never left running by a restart, and a hand-started ngrok is reused
and not killed."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import kite_tunnel


class FakeProc:
    def __init__(self):
        self.terminated = False
        self.stderr = None

    def poll(self):
        return 0 if self.terminated else None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.terminated = True


def _setup(monkeypatch, up_after=1, already_up=False):
    monkeypatch.setattr(config, "KITE_TUNNEL", {"enabled": True, "domain": "example.ngrok-free.dev",
                                                "start_timeout_s": 2, "max_seconds": 600})
    monkeypatch.setattr(kite_tunnel, "_proc", None)
    monkeypatch.setattr(kite_tunnel, "_stop_timer", None)
    spawned = []
    def spawn():
        p = FakeProc()
        spawned.append(p)
        return p
    monkeypatch.setattr(kite_tunnel, "_spawn", spawn)
    checks = {"n": 0}
    def is_up(timeout=1.5):
        checks["n"] += 1
        if already_up:
            return True
        return bool(spawned) and not spawned[-1].terminated and checks["n"] > up_after
    monkeypatch.setattr(kite_tunnel, "_tunnel_is_up", is_up)
    return spawned


def test_redirect_url_is_the_registered_https_tunnel_not_localhost():
    assert config.KITE_REDIRECT_URL == "https://ambiguity-patchy-untold.ngrok-free.dev/kite/callback"


def test_ensure_up_starts_ngrok_and_waits_until_it_reports_the_tunnel(monkeypatch):
    spawned = _setup(monkeypatch, up_after=2)
    r = kite_tunnel.ensure_up()
    assert r == {"ok": True, "started": True, "error": None}
    assert len(spawned) == 1 and kite_tunnel.running()
    kite_tunnel.stop()


def test_a_second_login_reuses_the_running_tunnel(monkeypatch):
    spawned = _setup(monkeypatch)
    kite_tunnel.ensure_up()
    r = kite_tunnel.ensure_up()
    assert r["ok"] and r["started"] is False and len(spawned) == 1
    kite_tunnel.stop()


def test_stop_soon_after_the_callback_takes_it_down(monkeypatch):
    spawned = _setup(monkeypatch)
    kite_tunnel.ensure_up()
    kite_tunnel.stop_soon(delay_s=0.05)
    time.sleep(0.3)
    assert spawned[0].terminated and not kite_tunnel.running()


def test_the_backstop_timer_stops_an_abandoned_login(monkeypatch):
    spawned = _setup(monkeypatch)
    config.KITE_TUNNEL["max_seconds"] = 0.05
    kite_tunnel.ensure_up()
    time.sleep(0.3)
    assert spawned[0].terminated


def test_a_hand_started_ngrok_is_reused_and_never_killed(monkeypatch):
    spawned = _setup(monkeypatch, already_up=True)
    r = kite_tunnel.ensure_up()
    kite_tunnel.stop_soon(delay_s=0.01)
    kite_tunnel.stop()
    assert r == {"ok": True, "started": False, "error": None} and spawned == []


def test_a_tunnel_that_never_comes_up_is_reported_and_cleaned_up(monkeypatch):
    spawned = _setup(monkeypatch, up_after=10**9)
    config.KITE_TUNNEL["start_timeout_s"] = 0.3
    r = kite_tunnel.ensure_up()
    assert r["ok"] is False and "did not report the tunnel" in r["error"]
    assert spawned[0].terminated and not kite_tunnel.running()


def test_missing_ngrok_is_a_clear_error(monkeypatch):
    _setup(monkeypatch)
    def no_ngrok():
        raise RuntimeError("ngrok is not installed (brew install ngrok)")
    monkeypatch.setattr(kite_tunnel, "_spawn", no_ngrok)
    r = kite_tunnel.ensure_up()
    assert r["ok"] is False and "not installed" in r["error"]
