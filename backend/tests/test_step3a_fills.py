"""3a fill rules on synthetic bars (prereg-3a amendments 1 b/c/d/e, 3.1, 3.2).
No real data is read, so nothing here can leak a result."""
import pytest

from research import step3a_opening_range as s3


def bar(o, h, l, c, v=100):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def day(extra):
    d = {"09:15": bar(100, 101, 99, 100), "09:20": bar(100, 101, 99, 100),
         "09:25": bar(100, 101, 99, 100)}
    d.update(extra)
    return d


def test_entry_is_next_bar_open_never_signal_close():
    d = day({"09:30": bar(100, 102, 100, 101.5), "09:35": bar(103, 104, 102.5, 103.5),
             "15:10": bar(105, 105, 105, 105)})
    sig = s3.find_signal(d)
    assert (sig["signal_t"], sig["entry_t"], sig["side"]) == ("09:30", "09:35", "BUY")
    assert sig["entry"] == 103 and sig["stop"] == 99


def test_touch_is_not_a_signal_only_a_close_is():
    d = day({"09:30": bar(100, 103, 100, 100.5), "09:35": bar(100, 100, 100, 100),
             "15:10": bar(100, 100, 100, 100)})
    assert s3.find_signal(d) is None


def test_no_signal_bar_after_1430():
    d = day({"14:35": bar(100, 103, 100, 102), "14:40": bar(102, 102, 102, 102),
             "15:10": bar(102, 102, 102, 102)})
    assert s3.find_signal(d) is None


def test_short_side_and_stop_is_range_high():
    d = day({"09:30": bar(100, 100, 98, 98.5), "09:35": bar(98, 98, 97, 97.5),
             "15:10": bar(96, 96, 96, 96)})
    sig = s3.find_signal(d)
    assert sig["side"] == "SELL" and sig["stop"] == 101
    tr = s3.simulate(d, sig)
    assert tr["reason"] == "timeout" and tr["gross_bp"] == pytest.approx((98 - 96) / 98 * 1e4)


def test_intrabar_touch_fills_at_stop_and_gap_fills_at_open():
    base = {"09:30": bar(100, 102, 100, 101.5), "09:35": bar(103, 104, 102.5, 103.5)}
    touch = day({**base, "09:40": bar(103, 103, 98.5, 99.5), "15:10": bar(110, 110, 110, 110)})
    tr = s3.simulate(touch, s3.find_signal(touch))
    assert tr["reason"] == "stop" and tr["exit"] == 99
    gap = day({**base, "09:40": bar(97, 98, 96, 97.5), "15:10": bar(110, 110, 110, 110)})
    tr = s3.simulate(gap, s3.find_signal(gap))
    assert tr["reason"] == "stop_gap" and tr["exit"] == 97


def test_entry_bar_itself_can_stop_the_trade():
    d = day({"09:30": bar(100, 102, 100, 101.5), "09:35": bar(103, 103, 98, 102),
             "15:10": bar(110, 110, 110, 110)})
    tr = s3.simulate(d, s3.find_signal(d))
    assert tr["reason"] == "stop" and tr["exit_t"] == "09:35"


def test_round_trip_cost_is_the_preregistered_16_60bp():
    d = day({"09:30": bar(100, 102, 100, 101.5), "09:35": bar(103, 104, 102.5, 103.5),
             "15:10": bar(103, 103, 103, 103)})
    tr = s3.simulate(d, s3.find_signal(d))
    assert tr["gross_bp"] == pytest.approx(0)
    assert -tr["net_bp"] == pytest.approx(16.60, abs=0.15)


def test_rel_vol_needs_14_prior_sessions_and_uses_only_the_past():
    days = {"2025-01-%02d" % i: day({}) for i in range(1, 16)}
    days["2025-01-15"] = {k: bar(100, 101, 99, 100, v=300) for k in s3.OR_BARS}
    rel = s3.rel_vol_table({"AAA": days})
    assert list(rel) == ["2025-01-15"]
    assert rel["2025-01-15"]["AAA"] == pytest.approx(3.0)


def test_top20_tie_is_alphabetical():
    rel = {"S%02d" % i: 1.0 for i in range(25)}
    assert s3.top_names(rel) == {"S%02d" % i for i in range(20)}


def test_friction_rule_threshold():
    assert s3.MIN_STOP_BP == pytest.approx(110.67, abs=0.01)


def test_cap_is_five_chronological_then_alphabetical():
    d = day({"09:30": bar(100, 103, 100, 102), "09:35": bar(102, 103, 102, 103),
             "15:10": bar(103, 103, 103, 103)})
    by = {s: {"2025-01-01": d} for s in "GFEDCBA"}
    sigs = sorted(({**s3.find_signal(d), "sym": s, "date": "2025-01-01"} for s in by),
                  key=lambda x: (x["signal_t"], x["sym"]))
    assert [t["sym"] for t in s3.capped(by, sigs)] == list("ABCDE")
