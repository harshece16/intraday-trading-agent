"""#162: holidays are held per year. A date in a year with no list is loud:
an error at start-up and on every pre-market read, and
`holiday_calendar_missing` in the engine state. Weekends stay closed. The
results calendar's next session skips holidays as well as weekends."""
import asyncio
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import holidays
import nse_feed
import trading_engine
from state import AppState

IST = ZoneInfo("Asia/Kolkata")


def _engine():
    e = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    e.scanner = None
    return e


def _errors(engine):
    return [a for a in engine.state.activity if a["level"] == "error" and "holiday list" in a["message"]]


# --- holidays.py ---------------------------------------------------------------------------------

def test_2026_has_a_list_and_2027_does_not():
    assert holidays.calendar_missing(date(2026, 10, 2)) is None
    assert holidays.calendar_missing(datetime(2027, 1, 26, 10, 0, tzinfo=IST)) == 2027
    assert holidays.holiday_name(date(2026, 10, 2)) == "Mahatma Gandhi Jayanti"
    assert holidays.NSE_HOLIDAYS[2026] is holidays.NSE_HOLIDAYS_2026


def test_without_a_list_weekdays_trade_and_weekends_stay_closed():
    wednesday = datetime(2027, 1, 6, 10, 0, tzinfo=IST)
    saturday = datetime(2027, 1, 9, 10, 0, tzinfo=IST)
    assert holidays.holiday_name(wednesday) is None
    assert trading_engine.market_phase(wednesday) == "open"
    assert trading_engine.market_phase(saturday) == "closed"
    assert holidays.next_trading_day(date(2027, 1, 8)) == date(2027, 1, 11)     # Friday -> Monday


def test_a_listed_holiday_is_still_closed():
    assert trading_engine.market_phase(datetime(2026, 10, 2, 10, 0, tzinfo=IST)) == "closed"
    assert holidays.next_trading_day(date(2026, 10, 1)) == date(2026, 10, 5)


def test_the_message_names_the_year_and_the_fix():
    msg = holidays.missing_calendar_message(2027)
    assert "2027" in msg and "backend/holidays.py" in msg and "holiday-master" in msg


# --- the engine ----------------------------------------------------------------------------------

def test_a_year_without_a_list_logs_one_error_and_sets_the_state():
    e = _engine()
    assert e._warn_if_no_holiday_calendar("at start-up", now=datetime(2027, 1, 4, 8, 0, tzinfo=IST)) == 2027
    missing = e.state.snapshot()["holiday_calendar_missing"]
    assert missing["year"] == 2027 and "2027" in missing["message"]
    assert len(_errors(e)) == 1


def test_a_year_with_a_list_is_quiet():
    e = _engine()
    assert e._warn_if_no_holiday_calendar("at start-up", now=datetime(2026, 10, 1, 8, 0, tzinfo=IST)) is None
    assert e.state.snapshot()["holiday_calendar_missing"] is None
    assert _errors(e) == []


def test_every_tick_keeps_the_state_current():
    e = _engine()
    e._holiday_calendar_state(datetime(2027, 1, 4, 8, 0, tzinfo=IST))
    assert e.state.holiday_calendar_missing["year"] == 2027
    e._holiday_calendar_state(datetime(2026, 12, 31, 8, 0, tzinfo=IST))
    assert e.state.holiday_calendar_missing is None
    assert _errors(e) == []                        # the tick sets the state; it does not log


def test_the_pre_market_read_warns(monkeypatch):
    # This year has no list: the case the engine would meet on 2027-01-01.
    monkeypatch.setattr(holidays, "NSE_HOLIDAYS", {})
    e = _engine()
    monkeypatch.setattr(trading_engine, "run_premarket",
                        lambda cfg: {"watchlist": [], "market": {"bias": "neutral"}})
    e._run_premarket_scan()
    assert len(_errors(e)) == 1
    assert e.state.holiday_calendar_missing["year"] == datetime.now(IST).year


def test_the_pre_market_read_warns_even_when_the_read_fails(monkeypatch):
    monkeypatch.setattr(holidays, "NSE_HOLIDAYS", {})
    e = _engine()

    def boom(cfg):
        raise RuntimeError("feed down")

    monkeypatch.setattr(trading_engine, "run_premarket", boom)
    e._run_premarket_scan()
    assert len(_errors(e)) == 1


def test_start_up_warns(monkeypatch):
    monkeypatch.setattr(holidays, "NSE_HOLIDAYS", {})
    monkeypatch.setattr(config, "RISK", {**config.RISK, "tick_stops": False})
    monkeypatch.setattr(config, "POLL_INTERVAL_SECONDS", 0)
    e = _engine()
    monkeypatch.setattr(e, "tick", lambda: setattr(e.state, "running", False))
    asyncio.run(e.run_forever())
    assert len(_errors(e)) == 1
    assert e.state.holiday_calendar_missing is not None


# --- nse_feed.results_calendar -------------------------------------------------------------------

class _Thursday(datetime):
    """2026-10-01, the day before Gandhi Jayanti (Friday 2026-10-02)."""
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 1, 9, 0, tzinfo=tz)


def test_results_after_a_holiday_are_excluded_on_the_day_before_it(monkeypatch):
    events = [
        {"symbol": "AAA", "date": "05-Oct-2026", "purpose": "Financial Results"},   # next session
        {"symbol": "BBB", "date": "06-Oct-2026", "purpose": "Financial Results"},   # the one after
        {"symbol": "CCC", "date": "01-Oct-2026", "purpose": "Financial Results"},   # today
    ]
    monkeypatch.setattr(nse_feed, "_fetch", lambda *a, **k: events)
    monkeypatch.setattr(nse_feed, "datetime", _Thursday)
    assert set(nse_feed.results_calendar()) == {"AAA", "CCC"}
