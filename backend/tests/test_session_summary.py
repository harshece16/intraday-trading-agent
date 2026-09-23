"""
The end-of-session summary answers the one question the rolling blocker
counts can't: on a day that produced no trades, which single gate came
closest to letting one through, and on which stock.

The ranking is the part worth protecting. Only `rrr` is a continuous
quantity, so it is the only required item where "how close" is a real
measurement; every other required item is boolean, and these tests pin
down that the summary says so rather than inventing a distance for it.
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

import database

IST = ZoneInfo("Asia/Kolkata")


def _today():
    return datetime.now(IST).date().isoformat()


def _ts_today(hhmm="10:30"):
    h, m = (int(x) for x in hhmm.split(":"))
    day = datetime.now(IST).date()
    return datetime(day.year, day.month, day.day, h, m, tzinfo=IST).timestamp()


def _item(key, ok, detail="", required=True):
    return {"key": key, "required": required, "ok": ok,
            "label": key.upper(), "detail": detail}


def _eval(symbol, side="long", failing=(), rrr=None, hhmm="10:30", passing=("pattern", "sr", "volume", "dow", "rrr")):
    """Insert one checklist_evals row with a controlled timestamp.
    record_checklist_eval() stamps time.time() itself, so these tests write
    the row directly to place it inside a known IST day."""
    items = [_item(k, k not in failing) for k in passing]
    side_block = {"items": items}
    if rrr is not None:
        side_block["rrr"] = rrr
    payload = {side: side_block}
    with database._conn() as c:
        c.execute(
            "INSERT INTO checklist_evals (ts, symbol, ltp, bull_score, checklist_json) VALUES (?,?,?,?,?)",
            (_ts_today(hhmm), symbol, 100.0, 5.0, json.dumps(payload)),
        )


def _trade(position_id, ts, symbol="TESTCO"):
    database.record_trade({
        "id": f"{position_id}-{ts}", "position_id": position_id, "ts": ts, "symbol": symbol,
        "side": "BUY", "quantity": 1, "price": 100.0, "mode": "paper",
    })


def test_rrr_near_miss_ranks_by_distance_to_the_bar():
    _eval("FARCO", failing=("rrr",), rrr=0.30, hhmm="10:00")
    _eval("CLOSECO", failing=("rrr",), rrr=1.42, hhmm="11:00")

    s = database.session_summary(session_date=_today())

    assert s["near_misses_by_lone_blocker"] == {"rrr": 2}
    assert [n["symbol"] for n in s["near_misses"]] == ["CLOSECO", "FARCO"]
    assert s["near_misses"][0]["shortfall"] == 0.08
    assert s["near_misses"][0]["ranked_by"] == "rrr"


def test_repeated_ticks_on_one_setup_collapse_to_a_single_near_miss():
    """The engine re-reads the checklist every tick, so a setup sitting just
    under the bar for half an hour produced ~60 near-identical rows and the
    unfiltered top-5 was the same stock five times (seen on a real session)."""
    for hhmm, rrr in (("12:31", 1.20), ("12:32", 1.26), ("12:33", 1.22)):
        _eval("DRREDDY", failing=("rrr",), rrr=rrr, hhmm=hhmm)
    _eval("OTHERCO", failing=("rrr",), rrr=1.10, hhmm="13:00")

    s = database.session_summary(session_date=_today())

    assert [n["symbol"] for n in s["near_misses"]] == ["DRREDDY", "OTHERCO"]
    assert s["distinct_near_misses"] == 2
    best = s["near_misses"][0]
    assert best["rrr"] == 1.26           # the closest look, not the latest
    assert best["occurrences"] == 3      # ...but all three are accounted for
    assert s["near_misses_by_lone_blocker"] == {"rrr": 4}   # raw tally unchanged


def test_summary_line_counts_distinct_setups_not_ticks():
    for hhmm in ("12:31", "12:32", "12:33"):
        _eval("DRREDDY", failing=("rrr",), rrr=1.26, hhmm=hhmm)

    line = database.session_summary_line(database.session_summary(session_date=_today()))

    assert "1 setup(s) came within one item" in line
    assert "held for 3 evaluations" in line


def test_boolean_gate_near_miss_reports_no_distance_and_sorts_last():
    _eval("BOOLCO", failing=("pattern",), rrr=None, hhmm="14:00")
    _eval("RRRCO", failing=("rrr",), rrr=0.10, hhmm="09:30")

    s = database.session_summary(session_date=_today())

    assert [n["symbol"] for n in s["near_misses"]] == ["RRRCO", "BOOLCO"]
    boolean = s["near_misses"][1]
    assert boolean["rrr"] is None
    assert boolean["shortfall"] is None
    assert boolean["ranked_by"] == database._NEAR_MISS_UNRANKED


def test_full_pass_is_counted_and_is_not_a_near_miss():
    _eval("PASSCO", failing=(), rrr=2.0)

    s = database.session_summary(session_date=_today())

    assert s["full_passes"] == 1
    assert s["near_misses"] == []
    assert s["evaluations"] == 1


def test_two_failing_items_is_not_a_near_miss():
    _eval("TWOCO", failing=("rrr", "volume"), rrr=0.5)

    s = database.session_summary(session_date=_today())

    assert s["near_misses"] == []
    assert s["required_item_fail_counts"] == {"rrr": 1, "volume": 1}


def test_entries_count_positions_opened_today_not_legs_or_carried_exits():
    yesterday = _ts_today("10:00") - 86400
    _trade("pos-old", yesterday)            # opened yesterday
    _trade("pos-old", _ts_today("15:10"))   # ...exited today: not an entry today
    _trade("pos-new", _ts_today("10:15"))   # opened today
    _trade("pos-new", _ts_today("14:00"))   # two legs, one position

    s = database.session_summary(session_date=_today())

    assert s["entries_taken"] == 1


def test_summary_line_names_the_closest_gate_and_the_shortfall():
    _eval("CLOSECO", failing=("rrr",), rrr=1.42, hhmm="11:00")

    line = database.session_summary_line(database.session_summary(session_date=_today()))

    assert line.startswith(database.SESSION_SUMMARY_PREFIX)
    assert "no trades" in line
    assert "CLOSECO" in line
    assert "1.42" in line
    assert "0.08" in line


def test_summary_line_when_nothing_was_evaluated():
    line = database.session_summary_line(database.session_summary(session_date=_today()))

    assert "no checklist evaluations ran" in line


def test_summary_line_reports_entries_when_the_day_traded():
    _eval("PASSCO", failing=(), rrr=2.0)
    _trade("pos-new", _ts_today("10:15"))

    line = database.session_summary_line(database.session_summary(session_date=_today()))

    assert "1 position(s) opened" in line


def test_logged_on_guard_is_false_until_the_summary_is_recorded():
    today = _today()
    assert database.session_summary_logged_on(today) is False

    database.record_activity(database.SESSION_SUMMARY_KIND,
                             f"{database.SESSION_SUMMARY_PREFIX}{today}: no trades.")

    assert database.session_summary_logged_on(today) is True


def test_summary_ignores_evaluations_from_other_days():
    _eval("TODAYCO", failing=("rrr",), rrr=1.0)
    with database._conn() as c:
        c.execute(
            "INSERT INTO checklist_evals (ts, symbol, ltp, bull_score, checklist_json) VALUES (?,?,?,?,?)",
            (_ts_today("10:00") - 86400, "YESTERCO", 100.0, 5.0,
             json.dumps({"long": {"items": [_item("rrr", False)], "rrr": 1.49}})),
        )

    s = database.session_summary(session_date=_today())

    assert s["evaluations"] == 1
    assert [n["symbol"] for n in s["near_misses"]] == ["TODAYCO"]


# ---- engine hook -----------------------------------------------------------
#
# The summary is only useful if it actually fires, exactly once, on the first
# tick after a real session's close. These drive the real _tick_impl() with a
# frozen clock rather than calling the hook directly, so the phase/holiday/
# weekday conditions guarding it are the ones under test.

import config                      # noqa: E402
import trading_engine              # noqa: E402
from state import AppState         # noqa: E402


class _FrozenDatetime(datetime):
    """datetime subclass whose now() returns a fixed IST moment."""
    frozen = None

    @classmethod
    def now(cls, tz=None):
        return cls.frozen if tz is None else cls.frozen.astimezone(tz)


def _tick_at(monkeypatch, hhmm, day_offset=0):
    engine = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    engine.scanner = None
    h, m = (int(x) for x in hhmm.split(":"))
    today = datetime.now(IST).date()
    frozen = datetime(today.year, today.month, today.day, h, m, tzinfo=IST)
    _FrozenDatetime.frozen = frozen
    monkeypatch.setattr(trading_engine, "datetime", _FrozenDatetime)
    monkeypatch.setattr(trading_engine.holidays, "is_holiday", lambda *a, **k: False)
    monkeypatch.setattr(trading_engine.holidays, "holiday_name", lambda *a, **k: None)
    return engine, frozen


def _summary_lines(state):
    return [a for a in state.activity if a["kind"] == database.SESSION_SUMMARY_KIND]


def test_engine_logs_the_summary_once_after_the_close(monkeypatch):
    if datetime.now(IST).weekday() >= 5:
        import pytest
        pytest.skip("the hook is weekday-only; the frozen clock keeps today's weekday")
    _eval("CLOSECO", failing=("rrr",), rrr=1.42, hhmm="11:00")
    engine, _ = _tick_at(monkeypatch, "15:45")

    engine._tick_impl()
    engine._tick_impl()          # a second tick the same evening

    lines = _summary_lines(engine.state)
    assert len(lines) == 1
    assert "CLOSECO" in lines[0]["message"]


def test_engine_does_not_log_the_summary_before_the_close(monkeypatch):
    if datetime.now(IST).weekday() >= 5:
        import pytest
        pytest.skip("weekday-only hook")
    _eval("CLOSECO", failing=("rrr",), rrr=1.42, hhmm="11:00")
    engine, _ = _tick_at(monkeypatch, "12:00")

    engine._tick_impl()

    assert _summary_lines(engine.state) == []


def test_engine_skips_a_summary_already_in_the_activity_log(monkeypatch):
    """An evening restart clears the in-memory guard; the activity table is
    what stops the same summary being logged twice."""
    if datetime.now(IST).weekday() >= 5:
        import pytest
        pytest.skip("weekday-only hook")
    _eval("CLOSECO", failing=("rrr",), rrr=1.42, hhmm="11:00")
    database.record_activity(database.SESSION_SUMMARY_KIND,
                             f"{database.SESSION_SUMMARY_PREFIX}{_today()}: already logged.")
    engine, _ = _tick_at(monkeypatch, "15:45")

    engine._tick_impl()

    assert _summary_lines(engine.state) == []


def _pass(symbol, side, hhmm, bar_time=None):
    """A read where every required item passed, at a controlled time."""
    items = [_item(k, True) for k in ("pattern", "sr", "volume", "dow", "rrr")]
    with database._conn() as c:
        c.execute(
            "INSERT INTO checklist_evals (ts, symbol, ltp, bull_score, checklist_json, bar_time) VALUES (?,?,?,?,?,?)",
            (_ts_today(hhmm), symbol, 100.0, 5.0, json.dumps({side: {"items": items}}), bar_time),
        )


def test_re_reads_and_after_cutoff_passes_are_not_counted_as_setups_in_the_entry_path():
    # #82: 8 re-reads of one in-window setup + 8 re-reads of a setup after
    # the 14:30 cutoff. The old count said 16; it is 1 setup that could be
    # tried, and 1 more that never could.
    for m in range(8):
        _pass("INDHOTEL", "long", f"11:{35 + m:02d}")
        _pass("SOLARINDS", "short", f"15:{5 + m:02d}")
    s = database.session_summary(_today())
    assert s["full_passes"] == 1
    assert s["full_passes_outside_window"] == 1
    assert s["full_pass_reads"] == 16
    line = database.session_summary_line(s)
    assert "produced 1 setup(s) passing every required item inside the 09:30–14:30 entry window" in line
    assert "plus 1 outside it, never tried" in line


def test_the_recorded_bar_time_decides_the_window_not_the_read_time():
    # Read at 14:40 (delayed data) of the 14:20 bar: inside the window.
    _pass("TESTCO", "long", "14:40", bar_time=f"{_today()}T14:20:00+05:30")
    s = database.session_summary(_today())
    assert s["full_passes"] == 1 and s["full_passes_outside_window"] == 0


def test_without_a_bar_time_the_last_finished_bar_is_assumed():
    # 14:33 read, no bar_time: the last finished bar started 14:25, inside.
    # 14:36 read: the last finished bar started 14:30, outside.
    _pass("AAA", "long", "14:33")
    _pass("BBB", "long", "14:36")
    s = database.session_summary(_today())
    assert s["full_passes"] == 1 and s["full_passes_outside_window"] == 1


def test_record_checklist_eval_stores_the_bar_time():
    database.record_checklist_eval("TESTCO", 100.0, {"bull_score": 1.0, "bar_time": "2026-09-23T11:35:00+05:30",
                                                     "checklist": {"long": {"items": []}}})
    with database._conn() as c:
        assert c.execute("SELECT bar_time FROM checklist_evals").fetchone()[0] == "2026-09-23T11:35:00+05:30"


def _reads(start, end, every_s=38):
    """Plain reads (one failing item, so no near-miss noise) every `every_s`
    seconds between two HH:MM times today."""
    t, stop = _ts_today(start), _ts_today(end)
    stamps = []
    while t < stop:
        stamps.append(t)
        t += every_s
    stamps.append(stop)            # always read at the end time itself
    with database._conn() as c:
        for t in stamps:
            c.execute("INSERT INTO checklist_evals (ts, symbol, ltp, bull_score, checklist_json) VALUES (?,?,?,?,?)",
                      (t, "TESTCO", 100.0, 1.0, json.dumps({"long": {"items": [_item("pattern", False),
                                                                                _item("rrr", False)]}})))


def test_full_session_coverage_adds_nothing_to_the_line():
    _reads("09:15", "15:14")
    s = database.session_summary(_today())
    assert s["coverage"]["uncovered_min"] == 0 and s["coverage"]["gaps"] == []
    assert "Coverage" not in database.session_summary_line(s)


def test_a_late_start_is_reported_before_the_counts():
    # 23 Sep: the laptop slept until 10:38.
    _reads("10:38", "15:14")
    s = database.session_summary(_today())
    assert s["coverage"]["uncovered_min"] == 83 and s["coverage"]["gaps"] == [["09:15", "10:38"]]
    line = database.session_summary_line(s)
    assert "no trades. Coverage: engine evaluated 10:38–15:14; 83 min of the 09:15–15:15 session not covered (09:15–10:38)." in line
    assert line.index("Coverage") < line.index("checklist evaluations")


def test_a_midday_gap_over_five_minutes_is_reported_and_a_short_one_is_not():
    _reads("09:15", "11:00")
    _reads("11:04", "12:00")      # 4-minute hole: normal jitter, not reported
    _reads("12:30", "15:14")      # 30-minute hole: reported
    cov = database.session_summary(_today())["coverage"]
    assert cov["gaps"] == [["12:00", "12:30"]] and 29 <= cov["uncovered_min"] <= 31


def test_an_early_stop_is_reported():
    _reads("09:15", "13:00")
    cov = database.session_summary(_today())["coverage"]
    assert cov["gaps"] == [["13:00", "15:15"]] and cov["last"] == "13:00"


def test_coverage_is_reported_on_a_day_that_traded_too():
    _reads("10:00", "15:14")
    _trade("P1", _ts_today("10:30"))
    line = database.session_summary_line(database.session_summary(_today()))
    assert "1 position(s) opened" in line and "45 min of the 09:15–15:15 session not covered" in line
