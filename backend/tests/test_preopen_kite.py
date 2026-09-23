"""The pre-open Kite check: one error-level alert (which the dashboard
pushes) on a trading day whose Kite session isn't live, from 08:45 until the
close, and never twice a day, even across a restart."""
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import data_provider
import database
import trading_engine
from state import AppState

IST = ZoneInfo("Asia/Kolkata")
WEDNESDAY = (2026, 9, 23)


def _engine(monkeypatch, live=False, configured=True):
    monkeypatch.setattr(config, "KITE_API_KEY", "k" if configured else "")
    monkeypatch.setattr(config, "KITE_API_SECRET", "s" if configured else "")
    probes = []
    def status(probe=False):
        probes.append(probe)
        return {"connected": live}
    monkeypatch.setattr(data_provider, "kite_session_status", status)
    e = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    e.scanner = None
    return e, probes


def _at(hhmm, day=WEDNESDAY):
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(*day, h, m, tzinfo=IST)


def _alerts(engine):
    return [a for a in engine.state.activity if a["kind"] == database.PREOPEN_KITE_KIND]


def test_no_live_session_at_0845_raises_one_error_alert(monkeypatch):
    e, probes = _engine(monkeypatch, live=False)
    e._check_preopen_kite(_at("08:45"), holiday=None)
    a = _alerts(e)
    assert len(a) == 1 and a[0]["level"] == "error"
    assert "market opens at 09:15" in a[0]["message"] and "Reconnect" in a[0]["message"]
    assert probes == [True]                       # one live probe, not just the clock


def test_it_fires_once_a_day(monkeypatch):
    e, probes = _engine(monkeypatch, live=False)
    for t in ("08:45", "08:46", "09:30", "14:00"):
        e._check_preopen_kite(_at(t), holiday=None)
    assert len(_alerts(e)) == 1 and len(probes) == 1


def test_a_restart_does_not_repeat_it(monkeypatch):
    e, _ = _engine(monkeypatch, live=False)
    e._check_preopen_kite(_at("08:45"), holiday=None)
    restarted, probes = _engine(monkeypatch, live=False)
    # the activity table is the only guard that survives a restart; the test
    # clock is a fixed date, so point the lookup at it
    monkeypatch.setattr(database, "activity_kind_logged_on", lambda kind, d: kind == database.PREOPEN_KITE_KIND)
    restarted._check_preopen_kite(_at("09:00"), holiday=None)
    assert _alerts(restarted) == [] and probes == []


def test_a_live_session_is_silent(monkeypatch):
    e, _ = _engine(monkeypatch, live=True)
    e._check_preopen_kite(_at("08:45"), holiday=None)
    assert _alerts(e) == []


def test_waking_mid_session_still_alerts_and_says_the_market_is_open(monkeypatch):
    # 23 Sep: the Mac slept until 10:38 with the token dead.
    e, _ = _engine(monkeypatch, live=False)
    e._check_preopen_kite(_at("10:38"), holiday=None)
    assert "market is already open" in _alerts(e)[0]["message"]


def test_before_0845_after_the_close_weekends_holidays_and_no_kite_setup_are_silent(monkeypatch):
    e, probes = _engine(monkeypatch, live=False)
    e._check_preopen_kite(_at("08:30"), holiday=None)
    e._check_preopen_kite(_at("15:45"), holiday=None)
    e._check_preopen_kite(_at("09:00", day=(2026, 9, 26)), holiday=None)       # Saturday
    e._check_preopen_kite(_at("09:00", day=(2026, 10, 2)), holiday="Gandhi Jayanti")
    unconfigured, p2 = _engine(monkeypatch, live=False, configured=False)
    unconfigured._check_preopen_kite(_at("09:00"), holiday=None)
    assert _alerts(e) == [] and _alerts(unconfigured) == [] and probes == [] and p2 == []


def test_a_failed_probe_falls_back_to_the_clock(monkeypatch):
    e, _ = _engine(monkeypatch)
    def boom(probe=False):
        raise RuntimeError("network down")
    monkeypatch.setattr(data_provider, "kite_session_status", boom)
    monkeypatch.setattr(data_provider, "kite_session_live", lambda: False)
    e._check_preopen_kite(_at("08:45"), holiday=None)
    assert len(_alerts(e)) == 1


def test_the_tick_loop_calls_it(monkeypatch):
    e, _ = _engine(monkeypatch)
    calls = []
    monkeypatch.setattr(e, "_check_preopen_kite", lambda now, holiday: calls.append((now, holiday)))
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "")     # keep _sync_capital off the network
    monkeypatch.setattr(trading_engine.holidays, "holiday_name", lambda *a, **k: None)
    e._tick_impl()
    assert len(calls) == 1
