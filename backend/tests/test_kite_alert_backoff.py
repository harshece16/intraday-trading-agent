"""
The expired-Kite alert was throttled on a flat 15-minute interval, so a token
that died at 06:00 produced ~40 identical rows a day — 4 an hour overnight,
and ~95% of the entire error channel. Nobody can click Reconnect at 03:00, so
every copy after the first carried no information. Issue #71.

These pin the three things that matter: the FIRST alert is still immediate,
repeats stretch instead of repeating flat, and a reconnect makes a later
expiry loud again rather than inheriting a 4-hour interval.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from kiteconnect.exceptions import TokenException

import config
import data_provider
import trading_engine
from state import AppState


def _engine(monkeypatch):
    engine = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    monkeypatch.setattr(engine, "_ensure_kite", _raise_token_exception)
    monkeypatch.setattr(data_provider, "mark_kite_token_rejected", lambda: None)
    monkeypatch.setattr(config, "RISK", {**config.RISK, "sync_capital_with_kite": True})
    # _sync_capital() returns immediately on a falsy KITE_ACCESS_TOKEN. A dev
    # machine has a .kite_session.json so this is set and the tests pass; CI
    # has no session file, so without this the engine never reaches the
    # TokenException path and all four tests saw 0 alerts. Pin it here rather
    # than inherit whatever the machine happens to have.
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "test-token-not-a-real-one")
    return engine


def _raise_token_exception():
    raise TokenException("token expired")


def _alerts(state):
    return [a for a in state.activity
            if a["kind"] == "error" and "Kite session has expired" in a["message"]]


class _Clock:
    """A fake clock that only ever moves forward. _sync_capital() has its own
    300s throttle keyed on time.time(), so a helper that restarts the clock
    per call silently stops the engine reaching the Kite call at all — which
    is exactly what made the first version of the reconnect test look like a
    product bug."""

    def __init__(self, monkeypatch, start=1_000_000.0):
        self.t = start
        monkeypatch.setattr(trading_engine.time, "time", lambda: self.t)

    def run(self, engine, seconds, step=30):
        end = self.t + seconds
        while self.t < end:
            engine._sync_capital()
            self.t += step


def _run(engine, monkeypatch, seconds, step=30):
    _Clock(monkeypatch).run(engine, seconds, step)


def test_first_alert_is_immediate(monkeypatch):
    engine = _engine(monkeypatch)
    _run(engine, monkeypatch, seconds=60)

    assert len(_alerts(engine.state)) == 1


def test_repeats_stretch_instead_of_firing_every_15_minutes(monkeypatch):
    """06:00 expiry to a 09:15 reconnect is 3h15m: 14 alerts on the old flat
    throttle, 3 with the backoff."""
    engine = _engine(monkeypatch)
    _run(engine, monkeypatch, seconds=int(3.25 * 3600))

    n = len(_alerts(engine.state))
    assert n == 3, n
    assert int(3.25 * 3600) // trading_engine.TOKEN_ALERT_MIN_INTERVAL + 1 == 14   # the old behaviour


def test_interval_doubles_and_then_caps(monkeypatch):
    engine = _engine(monkeypatch)
    assert engine._token_alert_interval == trading_engine.TOKEN_ALERT_MIN_INTERVAL

    _run(engine, monkeypatch, seconds=24 * 3600)

    assert engine._token_alert_interval == trading_engine.TOKEN_ALERT_MAX_INTERVAL


def test_reconnect_makes_a_later_expiry_loud_again(monkeypatch):
    """Without the reset, a token that dies tomorrow inherits today's
    stretched interval and stays quiet for four hours."""
    engine = _engine(monkeypatch)
    clock = _Clock(monkeypatch)
    clock.run(engine, seconds=24 * 3600)
    assert engine._token_alert_interval == trading_engine.TOKEN_ALERT_MAX_INTERVAL
    before = len(_alerts(engine.state))

    engine.reset_kite_executor()                      # what the Kite callback calls

    assert engine._token_alert_interval == trading_engine.TOKEN_ALERT_MIN_INTERVAL
    clock.run(engine, seconds=600)                    # same clock, moving forward
    assert len(_alerts(engine.state)) == before + 1   # immediately loud again
