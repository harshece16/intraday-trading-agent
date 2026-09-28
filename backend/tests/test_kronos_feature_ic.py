"""Research look L40 (docs/research/prereg-kronos-feature-ic.md): the pure parts.

Everything here runs without torch, the vendored Kronos repo or the candle cache,
which is also the point of the first test: the module must not pull either in at
import time, or CI and the live path would grow a dependency the prereg forbids.
"""
import sys
from datetime import datetime, timedelta

import pytest

from research import kronos_feature_ic as k


def _session(date, start="09:15", n=75, base=100.0):
    t = datetime.strptime("%s %s" % (date, start), "%Y-%m-%d %H:%M")
    bars = []
    for i in range(n):
        p = base + i * 0.1
        bars.append({"time": (t + timedelta(minutes=5 * i)).isoformat(), "open": p, "high": p + 0.05,
                     "low": p - 0.05, "close": p + 0.02, "volume": 1000 + i})
    return bars


def test_module_imports_neither_torch_nor_the_vendor():
    assert "torch" not in {name.split(".")[0] for name in dir(k)}
    assert not any(m == "model" for m in sys.modules if m == "model")


def test_membership_asof_reads_open_ended_intervals():
    rows = [{"symbol": "A", "from": "", "to": "2010-09-30"},
            {"symbol": "B", "from": "2016-04-01", "to": "2019-09-26"},
            {"symbol": "C", "from": "2020-01-01", "to": ""}]
    assert k.membership_asof(rows, "2010-01-15") == {"A"}
    assert k.membership_asof(rows, "2017-06-01") == {"B"}
    assert k.membership_asof(rows, "2025-11-03") == {"C"}


def test_decision_bar_is_the_bar_that_closes_at_the_decision_time():
    bars = _session("2025-11-03")
    i = k.decision_bar_index(bars, "09:45")
    assert bars[i]["time"][11:16] == "09:40"       # starts 09:40, closes 09:45
    assert k.decision_bar_index(bars, "09:15") is None  # no bar closes at the open


def test_target_enters_next_bar_open_and_exits_k_bars_later_close():
    bars = _session("2025-11-03")
    i = k.decision_bar_index(bars, "09:45")
    entry, exit_ = bars[i + 1]["open"], bars[i + 3]["close"]
    assert bars[i + 1]["time"][11:16] == "09:45"
    assert bars[i + 3]["time"][11:16] == "09:55"   # closes 10:00 = t + 15 min
    assert k.target_bp(bars, i, 3) == pytest.approx((exit_ - entry) / entry * 1e4)
    assert k.target_bp(bars, len(bars) - 2, 3) is None


def test_feature_window_sees_nothing_after_t_and_target_sees_nothing_before():
    bars = _session("2025-11-03")
    flat = bars
    i = k.decision_bar_index(bars, "13:30")
    window = k.lookback_window(flat, i, n=10)
    assert window[-1] is bars[i] and len(window) == 10
    # Mutate bars after t: the window is untouched.
    later = [dict(b, close=999.0) for b in bars[i + 1:]]
    assert k.lookback_window(bars[: i + 1] + later, i, n=10) == window
    # Mutate bars at and before t: the target is untouched.
    earlier = [dict(b, close=-1.0, open=-1.0) for b in bars[: i + 1]]
    assert k.target_bp(earlier + bars[i + 1:], i, 6) == k.target_bp(bars, i, 6)
    assert k.lookback_window(flat, 5, n=10) is None


def test_m60_is_the_last_twelve_bars_close_to_close():
    bars = _session("2025-11-03")
    i = 30
    expect = (bars[30]["close"] - bars[18]["close"]) / bars[18]["close"] * 1e4
    assert k.m60_bp(bars, i) == pytest.approx(expect)
    assert k.m60_bp(bars, 5) is None


def test_forecast_features_read_matched_horizons_in_bp():
    pred = [100 + i for i in range(1, 13)]
    f = k.forecast_features(pred, 100.0)
    assert f["f15"] == pytest.approx(300.0) and f["f30"] == pytest.approx(600.0) and f["f60"] == pytest.approx(1200.0)
    assert k.forecast_features(pred[:5], 100.0)["f60"] is None


def test_pick_revision_takes_latest_before_cutoff_and_moved_window_rule():
    commits = [("a", "2025-07-01T00:00:00"), ("b", "2025-08-20T00:00:00"), ("c", "2026-04-13T00:00:00")]
    assert k.pick_revision(commits, "2025-09-01") == ("b", "2025-08-20T00:00:00")
    assert k.pick_revision([commits[2]], "2025-09-01") is None
    sessions = ["2026-05-%02d" % d for d in range(1, 31)]
    moved = k.moved_window([commits[2]], sessions)
    assert moved["start"] == "2026-04-13" and moved["void"] is True


def test_selection_sessions_stay_in_window_and_drop_the_embargo():
    sessions = ["2025-08-29", "2025-09-01"] + ["2025-12-%02d" % d for d in range(1, 32)] + ["2026-01-02", "2026-02-02"]
    sel = k.selection_sessions(sessions)
    assert sel[0] == "2025-09-01"
    assert all(s <= "2025-12-31" for s in sel)
    assert sel[-1] == "2025-12-26"           # last five December sessions embargoed
    assert not any(s >= "2026-01-01" for s in sel)


def test_partial_spearman_removes_a_momentum_echo():
    rng = __import__("random").Random(1)
    m = [rng.gauss(0, 1) for _ in range(200)]
    y = [mi + rng.gauss(0, 0.3) for mi in m]
    echo = [mi * 2 + 1 for mi in m]                 # a "feature" that is exactly momentum
    assert k.spearman(echo, y) > 0.8
    assert k.partial_spearman(echo, y, m) is None   # nothing left once momentum is removed
    noisy_echo = [mi + rng.gauss(0, 0.01) for mi in m]
    assert abs(k.partial_spearman(noisy_echo, y, m)) < 0.15
    own = [yi + rng.gauss(0, 0.5) for yi in y]      # a feature with information of its own
    assert k.partial_spearman(own, y, m) > 0.3


def test_quintile_spread_and_gate():
    feats = list(range(10))
    targs = [float(i * 10) for i in range(10)]
    qs = k.quintile_spread(feats, targs)
    assert qs["q"] == 2 and qs["spread"] == pytest.approx(80.0)
    assert k.quintile_spread([1, 2, 3], [1, 2, 3]) is None

    def summary(spread_mean, spread_t, pic_mean, pic_t, halves=(1.0, 1.0), sessions=80, p=0.001):
        series = lambda m, t: {"mean": m, "t": t, "p": p, "halves": [{"mean": halves[0]}, {"mean": halves[1]}]}
        return {"sessions": sessions, "spread": series(spread_mean, spread_t), "pic": series(pic_mean, pic_t),
                "ic": series(0.01, 1.0), "top": series(20.0, 2.5), "bottom": series(-20.0, -2.5)}
    ok = summary(40.0, 3.0, 0.02, 2.5)
    fail_cost = summary(30.0, 3.0, 0.02, 2.5)
    fail_echo = summary(40.0, 3.0, 0.00, 0.5)
    v = k.gate({"f15": ok, "f30": fail_cost, "f60": fail_echo})
    assert v["f15"]["passes"] is True
    assert v["f30"]["passes"] is False and v["f30"]["checks"]["spread_gt_two_leg"] is False
    assert v["f60"]["passes"] is False and v["f60"]["checks"]["partial_ic_t_gt_2"] is False
    assert v["f15"]["single_side_note"] == {"top": True, "bottom": True}


def test_adjustment_boundaries_and_straddle():
    day1 = datetime(2026, 9, 1, 10).timestamp()
    day2 = datetime(2026, 9, 25, 10).timestamp()
    rows = [{"symbol": "X", "from_date": "2025-07-01", "to_date": "2025-08-29", "fetched_at": day1},
            {"symbol": "X", "from_date": "2025-08-30", "to_date": "2025-10-28", "fetched_at": day1},
            {"symbol": "X", "from_date": "2025-10-29", "to_date": "2025-12-27", "fetched_at": day2},
            {"symbol": "Y", "from_date": "2025-07-01", "to_date": "2025-12-27", "fetched_at": day1}]
    b = k.adjustment_boundaries(rows)
    assert b == {"X": ["2025-10-29"]}
    sessions = ["2025-10-%02d" % d for d in range(20, 32)] + ["2025-11-%02d" % d for d in range(1, 15)]
    assert k.straddles(b["X"], sessions, "2025-10-30") is True      # boundary inside the 8-session lookback
    assert k.straddles(b["X"], sessions, "2025-11-14") is False     # more than 8 sessions later
    assert k.straddles(b["X"], sessions, "2025-10-28") is False     # before the boundary


def test_session_stats_and_summary_are_per_session_then_across():
    per = {}
    rng = __import__("random").Random(2)
    for d in range(1, 61):
        rows = [(rng.gauss(0, 1), rng.gauss(0, 30), rng.gauss(0, 1)) for _ in range(25)]
        per["2025-10-%02d" % (d % 28 + 1) + ("" if d <= 28 else "b%d" % d)] = k.session_stats(rows)
    s = k.summarise(per)
    assert s["sessions"] == 60 and s["ic"]["n"] == 60
    assert abs(s["ic"]["mean"]) < 0.1 and s["ic"]["detectable_at_t2"] > 0
    assert len(s["spread"]["halves"]) == 2 and s["spread"]["halves"][0]["n"] == 30
