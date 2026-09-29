"""The run harness of research look L40 (prereg amendment 3): the parts that decide
something. Runs without torch, the vendored repo or the candle cache."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from research import kronos_l40_launch as h

IST = timezone(timedelta(hours=5, minutes=30))


def _at(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=IST)


def _no_holiday(day):
    return False


def test_the_module_does_not_import_torch_at_import_time():
    source = open(h.__file__).read()
    top = source.split("def paused_at")[0]
    assert "import torch" not in top and "kronos_feature_ic" not in top.split('"""')[-1]
    assert "torch" not in {name.split(".")[0] for name in dir(h)}


def test_the_run_is_paused_through_the_session_and_not_outside_it():
    # 2026-09-30 is a Wednesday
    assert not h.paused_at(_at("2026-09-30 08:29"), _no_holiday)
    assert h.paused_at(_at("2026-09-30 08:30"), _no_holiday)       # before the 08:45 list fix
    assert h.paused_at(_at("2026-09-30 09:15"), _no_holiday)
    assert h.paused_at(_at("2026-09-30 15:44"), _no_holiday)
    assert not h.paused_at(_at("2026-09-30 15:45"), _no_holiday)
    assert not h.paused_at(_at("2026-09-30 23:10"), _no_holiday)


def test_weekends_and_holidays_are_not_paused():
    assert not h.paused_at(_at("2026-10-03 11:00"), _no_holiday)   # a Saturday
    assert not h.paused_at(_at("2026-10-04 11:00"), _no_holiday)   # a Sunday
    assert not h.paused_at(_at("2026-10-02 11:00"), lambda day: True)


def test_the_window_is_read_in_indian_time_whatever_zone_the_clock_is_in():
    utc = datetime(2026, 9, 30, 4, 0, tzinfo=timezone.utc)         # 09:30 IST
    assert h.paused_at(utc, _no_holiday)
    assert not h.paused_at(datetime(2026, 9, 30, 11, 0, tzinfo=timezone.utc), _no_holiday)   # 16:30 IST


def test_the_sample_count_of_record_comes_from_a_finished_stage_0_only(tmp_path):
    path = tmp_path / "stage0.json"
    assert h.sample_count_of_record(str(path)) is None
    path.write_text(json.dumps({"status": "HALTED", "stage0": {"timing": {"sample_count_chosen": 3}}}))
    assert h.sample_count_of_record(str(path)) is None
    path.write_text(json.dumps({"status": "STAGE0_DONE", "stage0": {"timing": {"sample_count_chosen": 1}}}))
    assert h.sample_count_of_record(str(path)) == 1


def test_a_run_whose_timing_chooses_differently_halts_before_the_pass():
    halted = []

    def halt(stage0, step, why):
        halted.append((step, why))
        raise SystemExit(2)

    def timing_says_one(stage0, *a, **kw):
        stage0["timing"] = {"sample_count_chosen": 1}
        return 1

    stage0 = {}
    with pytest.raises(SystemExit):
        h.checked_timing(timing_says_one, 3, halt)(stage0)
    assert halted and halted[0][0] == 4
    assert stage0["timing"]["sample_count_of_record"] == 3


def test_a_run_whose_timing_agrees_goes_on():
    def halt(stage0, step, why):
        raise AssertionError("should not halt")

    def timing_says_three(stage0, *a, **kw):
        stage0["timing"] = {"sample_count_chosen": 3}
        return 3

    stage0 = {}
    assert h.checked_timing(timing_says_three, 3, halt)(stage0) == 3
    assert stage0["timing"]["sample_count_of_record"] == 3


def test_the_device_and_threads_are_fixed():
    assert (h.DEVICE, h.THREADS) == ("cpu", 4)
    assert (h.PAUSE_FROM, h.PAUSE_TO) == ("08:30", "15:45")
