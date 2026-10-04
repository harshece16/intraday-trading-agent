"""The momentum book at the centre (README section 116): the monthly report
against the benchmark, the next rebalance, and the alerts after the evening
job, on its success, failure and restart paths.

The job is never run here. A fake process stands in for it with the exit
code under test, and the state file it would have saved is written by hand.
conftest points the state file and the alert record at a temporary folder
and blanks the Telegram credentials; the `sent` fixture captures what would
be posted."""
import datetime
import json
import os
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BACKEND, "research"))

import momentum_alerts as ma  # noqa: E402
import momentum_book as mb  # noqa: E402
import telegram_alerts as tg  # noqa: E402
import trading_engine  # noqa: E402
from state import AppState  # noqa: E402
from test_momentum_book import _panel, _run  # noqa: E402

IST = trading_engine.IST
BUYS = ["ADANIPOWER", "BEL", "BSE", "CDSL", "COFORGE", "DIXON", "HAL", "INDHOTEL", "KAYNES", "MAZDOCK",
        "PERSISTENT", "POLYCAB", "SOLARINDS", "TRENT", "VEDL"]


class FakeJob:
    """What maybe_start_evening_job keeps in _last_attempt["proc"]: a process
    whose poll() gives its exit code once it has ended, None while it runs."""

    def __init__(self, rc):
        self.rc = rc

    def poll(self):
        return self.rc


@pytest.fixture
def sent(monkeypatch):
    monkeypatch.setattr(tg, "_token", "123:TEST")
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


@pytest.fixture
def job(monkeypatch):
    attempt = {"date": None, "ts": 0.0, "proc": None}
    monkeypatch.setattr(mb, "_last_attempt", attempt)
    return attempt


def _at(day, hhmm):
    y, m, d = (int(x) for x in day.split("-"))
    h, mi = (int(x) for x in hhmm.split(":"))
    return datetime.datetime(y, m, d, h, mi, tzinfo=IST)


def _lines(st):
    return [a for a in st.activity if a["kind"] == ma.KIND]


def _first_rebalance_state():
    """The book as the job would save it after the 1 Oct 2026 rebalance."""
    s = mb.new_state(1_000_000.0, "2026-09-26")
    per = 1_000_000.0 / 15
    for sym in BUYS:
        cost = round(mb.buy_cost(per, 0.0005), 2)
        s["trades"].append({"date": "2026-10-01", "side": "BUY", "symbol": sym, "value": round(per, 2), "cost": cost})
        s["book"]["positions"][sym] = {"symbol": sym, "fill_date": "2026-10-01", "amount": per - cost,
                                       "fill_price": 100.0}
    s["book"]["cash"] = 0.0
    book = 1_000_000.0 - sum(t["cost"] for t in s["trades"])
    s.update(status="active", rebalances=1, last_processed="2026-10-01", latest_session="2026-10-01",
             updated_at="2026-10-01T19:32:10", excess_months=0, cumulative_excess=0.0,
             data={"problem": None, "failed_downloads": []})
    s["month_points"] = [{"date": "2026-10-01", "book": book, "bench": 999_300.0}]
    s["nav"] = [{"date": "2026-10-01", "book": round(book, 2), "bench": 999_300.0}]
    return s


def _second_rebalance(s):
    """Add the 2 Nov 2026 rebalance: two sold, two bought, a month of excess."""
    s = json.loads(json.dumps(s))
    for sym in ("VEDL", "BSE"):
        s["book"]["positions"].pop(sym)
        s["trades"].append({"date": "2026-11-02", "side": "SELL", "symbol": sym, "value": 70_000.0, "cost": 120.0})
    for sym in ("MCX", "NETWEB"):
        s["trades"].append({"date": "2026-11-02", "side": "BUY", "symbol": sym, "value": 70_000.0, "cost": 90.0})
        s["book"]["positions"][sym] = {"symbol": sym, "fill_date": "2026-11-02", "amount": 69_910.0}
    b0, m0 = s["month_points"][0]["book"], s["month_points"][0]["bench"]
    s["month_points"].append({"date": "2026-11-02", "book": b0 * 1.031, "bench": m0 * 1.012})
    s.update(rebalances=2, last_processed="2026-11-02", latest_session="2026-11-02",
             updated_at="2026-11-02T19:33:00", excess_months=1, cumulative_excess=0.031 - 0.012)
    return s


def _save(s, bump=0):
    mb.save_state(s, mb.STATE_PATH)
    if bump:                                   # a later write, even within the same clock tick
        t = os.path.getmtime(mb.STATE_PATH) + bump
        os.utime(mb.STATE_PATH, (t, t))


# --- the report --------------------------------------------------------------------------

def test_the_monthly_report_is_the_bands_own_arithmetic():
    sessions, chains = _panel()
    conf = {**mb.DEFAULTS, "universe": 20}
    state = _run(sessions, chains, conf, created_idx=300)
    rep = mb.monthly_report(state)
    months = rep["months"]
    assert len(months) == state["excess_months"] >= 5
    assert months[-1]["cumulative_excess"] == state["cumulative_excess"]         # the same sum, exactly
    pts = state["month_points"]
    for k, row in enumerate(months, start=1):
        assert row["start"] == pts[k - 1]["date"] and row["end"] == pts[k]["date"]
        assert row["book_return"] == pts[k]["book"] / pts[k - 1]["book"] - 1
        assert row["excess"] == row["book_return"] - row["bench_return"]
        assert row["turnover"] is not None and row["turnover"] >= 0
    # every book trade's cost lands in exactly one month, or the opening rebalance
    traded = [t for t in state["trades"] if t["side"] in ("BUY", "SELL") and t["date"] <= pts[-1]["date"]]
    assert round(sum(r["costs"] for r in months) + rep["opening"]["costs"], 2) == \
        pytest.approx(sum(t["cost"] for t in traded), abs=0.05)
    assert rep["opening"]["bought"] == 15


def test_before_month_one_the_report_has_no_month(tmp_path):
    path = str(tmp_path / "s.json")
    mb.save_state(_first_rebalance_state(), path)
    out = mb.summary(state_path=path)
    assert out["months"] == []                                   # no zeros standing in for results
    assert out["opening_rebalance"]["bought"] == 15
    assert out["first_rebalance"] == "2026-10-01"
    assert out["next_rebalance"] == "2026-11-02" and out["next_rebalance_calendar_ok"]
    assert out["band"]["state"] == "not_active" and out["band"]["floor"] is None
    assert out["band"]["floor_at_start"] == pytest.approx(6 * 0.0071 - 2 * 0.0389 * 6 ** 0.5)

    assert out["month_to_date"] is None                          # nothing marked past the rebalance yet

    missing = mb.summary(state_path=str(tmp_path / "missing.json"))
    assert missing["status"] == "not_started" and missing["months"] == [] and missing["next_rebalance"]


def test_the_month_under_way_is_shown_apart_and_not_counted(tmp_path):
    sessions, chains = _panel()
    conf = {**mb.DEFAULTS, "universe": 20}
    state = _run(sessions, chains, conf, created_idx=300)
    path = str(tmp_path / "s.json")
    mb.save_state(state, path)
    out = mb.summary(state_path=path)
    last, pt = state["nav"][-1], state["month_points"][-1]
    assert last["date"] > pt["date"]
    assert out["month_to_date"] == {"start": pt["date"], "to": last["date"], "book": last["book"] / pt["book"] - 1,
                                    "bench": last["bench"] / pt["bench"] - 1}
    assert out["months"][-1]["end"] == pt["date"]               # the report stops at the last completed month


def test_the_band_status_follows_the_pre_registered_floor():
    conf = mb.cfg()
    s = {"status": "active", "excess_months": 6, "cumulative_excess": -0.10}
    b = mb.band_status(s, conf)
    assert b["active"] and b["state"] == "inside"
    assert b["floor"] == mb.band_threshold(6, 0.0071, 0.0389)
    assert b["expected_cumulative"] == pytest.approx(6 * 0.0071)
    assert mb.band_status({**s, "cumulative_excess": -0.20}, conf)["state"] == "below"
    assert mb.band_status({**s, "excess_months": 5}, conf)["state"] == "not_active"
    assert mb.band_status({**s, "status": "switched_off"}, conf)["state"] == "switched_off"


def test_the_next_rebalance_is_the_first_session_of_the_next_month():
    assert mb.next_rebalance("2026-09-30") == ("2026-10-01", True)
    assert mb.next_rebalance("2026-10-01") == ("2026-11-02", True)      # 1 Nov is a Sunday
    assert mb.next_rebalance("2026-12-31T19:30:00") == ("2027-01-01", False)   # no 2027 holiday list yet


# --- alerts: success --------------------------------------------------------------------

def test_telegram_always_sends_the_momentum_kind():
    assert tg.wants("momentum", "info")


def test_a_completed_rebalance_logs_one_line_and_sends_one_message(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    _save(_first_rebalance_state())
    job["proc"] = FakeJob(0)
    before = open(mb.STATE_PATH).read()

    ma.check(_at("2026-10-01", "19:34"), None, st.log)
    ma.check(_at("2026-10-01", "19:35"), None, st.log)        # the next tick: nothing new

    lines = _lines(st)
    assert len(lines) == 1 and len(sent) == 1
    msg = lines[0]["message"]
    assert "rebalanced at the 1 Oct 2026 close for October 2026" in msg
    assert "Bought 15: " + ", ".join(sorted(BUYS)) in msg and "Sold 0: none" in msg
    assert "No month is complete yet" in msg
    assert "Next rebalance: the 2 Nov 2026 close." in msg
    assert "floor then -14.80%" in msg
    assert sent[0].startswith("[PAPER] MOMENTUM\n")
    assert open(mb.STATE_PATH).read() == before                 # the book's state is never written
    assert json.load(open(ma.ALERTS_PATH))["rebalance"] == "2026-10-01"


def test_a_later_rebalance_reports_the_month_against_the_benchmark(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    _save(_first_rebalance_state())
    ma.check(_at("2026-10-01", "19:34"), None, st.log)
    _save(_second_rebalance(_first_rebalance_state()), bump=5)
    job["proc"] = FakeJob(0)

    ma.check(_at("2026-11-02", "19:34"), None, st.log)

    lines = _lines(st)
    assert len(lines) == 2 and len(sent) == 2
    msg = lines[0]["message"]                                   # newest first
    assert "Bought 2: MCX, NETWEB." in msg and "Sold 2: BSE, VEDL." in msg
    assert "October 2026: book +3.10%, benchmark +1.20%, excess +1.90%." in msg
    assert "cumulative excess +1.90% over 1 month." in msg
    assert "Next rebalance: the 1 Dec 2026 close." in msg


# --- alerts: restart -------------------------------------------------------------------

def test_a_restart_does_not_repeat_a_rebalance_alert(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    _save(_first_rebalance_state())
    job["proc"] = FakeJob(0)
    ma.check(_at("2026-10-01", "19:34"), None, st.log)

    ma.reset()                                   # the backend restarts: memory gone, record on disk
    job["proc"] = None                           # and the job's handle with it
    ma.check(_at("2026-10-01", "19:40"), None, st.log)

    assert len(_lines(st)) == 1 and len(sent) == 1


def test_a_rebalance_made_while_the_engine_was_down_is_alerted_once_after_the_restart(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    _save(_first_rebalance_state())
    ma.check(_at("2026-10-01", "19:34"), None, st.log)

    ma.reset()
    _save(_second_rebalance(_first_rebalance_state()), bump=5)   # the job ran; nobody watched it
    ma.check(_at("2026-11-02", "21:00"), None, st.log)
    ma.check(_at("2026-11-02", "21:01"), None, st.log)

    lines = _lines(st)
    assert len(lines) == 2 and "2 Nov 2026 close" in lines[0]["message"]


def test_with_no_record_only_the_latest_rebalance_is_alerted(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    _save(_second_rebalance(_first_rebalance_state()))
    ma.check(_at("2026-11-02", "21:00"), None, st.log)
    lines = _lines(st)
    assert len(lines) == 1 and "2 Nov 2026 close" in lines[0]["message"]


def test_nothing_is_alerted_before_the_first_rebalance(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    s = mb.new_state(1_000_000.0, "2026-09-26")
    s.update(last_processed="2026-09-30", latest_session="2026-09-30", updated_at="2026-09-30T19:31:49")
    _save(s)
    job["proc"] = FakeJob(0)
    ma.check(_at("2026-09-30", "19:34"), None, st.log)
    assert _lines(st) == [] and sent == []


# --- alerts: failure ------------------------------------------------------------------

def test_a_failed_run_is_alerted_once_with_its_reason(sent, job, tmp_path, monkeypatch):
    st = AppState(watchlist=[], paper_mode=True)
    s = mb.new_state(1_000_000.0, "2026-09-26")
    s.update(last_processed="2026-09-30", latest_session="2026-09-30", updated_at="2026-09-30T19:31:49")
    _save(s)
    log = tmp_path / "momentum_book.log"
    log.write_text("Traceback (most recent call last):\n  File \"momentum_book.py\"\nMemoryError\n")
    monkeypatch.setattr(mb, "LOG_PATH", str(log))

    job["proc"] = FakeJob(1)
    ma.check(_at("2026-10-01", "19:32"), None, st.log)
    job["proc"] = FakeJob(1)                     # the retry half an hour later fails the same way
    ma.check(_at("2026-10-01", "20:02"), None, st.log)

    lines = _lines(st)
    assert len(lines) == 1 and len(sent) == 1
    assert lines[0]["level"] == "error"
    msg = lines[0]["message"]
    assert "failed with exit code 1" in msg and "MemoryError" in msg and "unchanged since 2026-09-30" in msg


def test_a_job_killed_by_a_signal_is_alerted(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    job["proc"] = FakeJob(-9)
    ma.check(_at("2026-10-01", "19:40"), None, st.log)
    assert "was stopped by signal 9" in _lines(st)[0]["message"]


def test_a_run_that_found_another_job_running_is_not_alerted(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    assert ma.BUSY == mb.BUSY
    job["proc"] = FakeJob(mb.BUSY)               # a job from before an engine restart held the lock
    ma.check(_at("2026-10-01", "19:40"), None, st.log)
    assert _lines(st) == [] and sent == []


def test_a_run_that_stopped_early_is_alerted_once_even_across_a_restart(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    s = mb.new_state(1_000_000.0, "2026-09-26")
    problem = ("NSE's bhavcopy for 2026-09-30 could not be downloaded; the book stops before it and the next "
               "run tries again")
    s.update(last_processed="2026-09-29", latest_session="2026-10-01", updated_at="2026-10-01T19:33:00",
             data={"problem": problem})
    _save(s)
    job["proc"] = FakeJob(4)
    ma.check(_at("2026-10-01", "19:34"), None, st.log)
    ma.reset()
    _save(s, bump=5)                              # the retry stops at the same day
    ma.check(_at("2026-10-01", "20:05"), None, st.log)

    lines = _lines(st)
    assert len(lines) == 1 and len(sent) == 1
    assert lines[0]["level"] == "warn" and problem in lines[0]["message"]


def test_a_day_not_processed_when_the_window_closes_is_alerted_once(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    s = mb.new_state(1_000_000.0, "2026-09-26")
    s.update(last_processed="2026-09-30", latest_session="2026-09-30", updated_at="2026-10-01T23:01:00")
    _save(s)
    job["proc"] = FakeJob(3)                      # not published: the engine retries, nothing to say yet
    ma.check(_at("2026-10-01", "23:02"), None, st.log)
    assert _lines(st) == []

    ma.check(_at("2026-10-01", "23:30"), None, st.log)
    ma.check(_at("2026-10-01", "23:31"), None, st.log)
    lines = _lines(st)
    assert len(lines) == 1 and len(sent) == 1
    assert "not processed by 23:30" in lines[0]["message"]
    assert "makes this month's rebalance at today's close" in lines[0]["message"]


def test_the_window_close_says_nothing_on_a_holiday_or_once_the_day_is_in(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    s = _first_rebalance_state()
    _save(s)
    ma.check(_at("2026-10-01", "23:40"), None, st.log)          # processed: only the rebalance line
    assert [a for a in _lines(st) if "not processed" in a["message"]] == []
    ma.reset()
    s2 = dict(s, last_processed="2026-10-01", updated_at="2026-10-02T21:00:00")
    _save(s2, bump=5)
    ma.check(_at("2026-10-02", "23:40"), "Mahatma Gandhi Jayanti", st.log)
    assert [a for a in _lines(st) if "not processed" in a["message"]] == []


# --- nothing here can stop the job -------------------------------------------------------

def test_the_check_never_raises(job, monkeypatch, caplog):
    def boom(*a, **k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(ma, "_check", boom)
    ma.check(_at("2026-10-01", "19:34"), None, lambda *a, **k: None)     # no exception
    assert "alert check failed" in caplog.text


def test_an_unreadable_state_or_record_is_survived(sent, job):
    st = AppState(watchlist=[], paper_mode=True)
    with open(mb.STATE_PATH, "w") as fh:
        fh.write("{not json")
    with open(ma.ALERTS_PATH, "w") as fh:
        fh.write("[]")
    ma.check(_at("2026-10-01", "19:34"), None, st.log)
    assert _lines(st) == []


class _FrozenDatetime(datetime.datetime):
    frozen = None

    @classmethod
    def now(cls, tz=None):
        return cls.frozen if tz is None else cls.frozen.astimezone(tz)


def test_the_engine_starts_the_job_before_the_check_and_a_failing_check_does_not_stop_it(monkeypatch):
    """Drive the real tick at 20:00 on a trading day: the job hook runs, then
    the check; a check that blows up is contained and the tick goes on."""
    calls = []
    monkeypatch.setattr(trading_engine.momentum_book, "maybe_start_evening_job",
                        lambda now, holiday: calls.append("start") or True)

    def failing_check(now, holiday, log):
        calls.append("check")
        raise RuntimeError("alert code broken")

    monkeypatch.setattr(ma, "_check", failing_check)
    engine = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    engine.scanner = None
    _FrozenDatetime.frozen = datetime.datetime(2026, 10, 1, 20, 0, tzinfo=IST)
    monkeypatch.setattr(trading_engine, "datetime", _FrozenDatetime)
    monkeypatch.setattr(trading_engine.holidays, "is_holiday", lambda *a, **k: False)
    monkeypatch.setattr(trading_engine.holidays, "holiday_name", lambda *a, **k: None)

    engine._tick_impl()

    assert calls == ["start", "check"]
    assert any("evening job started" in a["message"] for a in engine.state.activity)
