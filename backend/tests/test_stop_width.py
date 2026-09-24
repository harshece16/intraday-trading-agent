"""
The reward-to-risk problem was a stop-distance problem.

Measured over 8,674 real checklist evaluations: the round trip cost a median
0.85R and exceeded the entire risk budget in 41% of setups, because a
5-minute pattern's own extreme sits ~0.14% from the entry against a 0.12%
round trip. That forced the target 3.62R away just to clear 1.5R after costs,
which intraday moves rarely manage — so only 3.7% of evaluations passed the
R:R rule, and the median R:R was negative.

`stop_buffer_atr` parks the stop beyond the pattern's extreme and
`min_stop_atr` stops it ever sitting too close to the entry. Both widen the
stop rather than rejecting the trade, which is what `min_stop_to_cost` does.
Position sizing keeps the rupee risk where it was.
"""
import math

import pytest

import trader_brain


ATR = 1.0


def _window(n=60, base=100.0):
    """A flat-ish window; the pattern's own bars are appended by the caller."""
    return [{"time": f"2026-09-18T09:{15 + i // 4:02d}:00+05:30", "open": base, "high": base + 0.2,
             "low": base - 0.2, "close": base, "volume": 10_000} for i in range(n)]


def _plan(side, low, high, close, params):
    """Run the real checklist over a window whose last bar is the pattern."""
    w = _window()
    w[-1] = {"time": "2026-09-18T09:45:00+05:30", "open": close, "high": high,
             "low": low, "close": close, "volume": 20_000}
    patterns = [{"name": "Hammer" if side == "long" else "Hanging Man",
                 "bias": "bullish" if side == "long" else "bearish", "strength": 3}]
    p = {**trader_brain.DEFAULTS, **params}
    return trader_brain._checklist(side, w, patterns, [], atr_v=ATR, vol10=1.5,
                                   htf_trend="up" if side == "long" else "down",
                                   structure="uptrend" if side == "long" else "downtrend",
                                   macd_v={"hist": 1.0 if side == "long" else -1.0},
                                   rsi_v=55.0 if side == "long" else 45.0,
                                   always_in=side, news_score=None, fundamentals_score=None, p=p)


def test_no_buffer_keeps_the_stop_on_the_pattern_low():
    """With both levers off the stop is the pattern's own extreme, unchanged."""
    out = _plan("long", 99.0, 100.5, 100.0, {"stop_buffer_atr": 0.0, "min_stop_atr": 0.0})
    assert out["stop"] == pytest.approx(99.0)


def test_the_shipped_defaults_are_the_ones_the_backtest_chose():
    """A 1 ATR floor and no buffer. The buffer is off on purpose: it widens
    every stop, including healthy ones, which pushes good setups past
    max_target_atr and buys its better headline numbers by shrinking the
    sample (buffer 0.50 posted the best first half off five trades). The floor
    only repairs the pathologically tight stops — it improved both halves
    while keeping 21 of the baseline's 30 trades. See README section 48."""
    assert trader_brain.DEFAULTS["min_stop_atr"] == 1.0
    assert trader_brain.DEFAULTS["stop_buffer_atr"] == 0.0
    # and the target cap stays where it is: letting targets out to 4 ATR added
    # 35 trades averaging -1.17R each
    assert trader_brain.DEFAULTS["max_target_atr"] == 3.0


def test_the_buffer_parks_the_stop_beyond_the_pattern_low_on_a_long():
    out = _plan("long", 99.0, 100.5, 100.0, {"stop_buffer_atr": 0.25})
    assert out["stop"] == pytest.approx(99.0 - 0.25 * ATR)


def test_the_buffer_parks_the_stop_above_the_pattern_high_on_a_short():
    """A short's stop has to move the other way, or the buffer would tighten it."""
    out = _plan("short", 99.5, 101.0, 100.0, {"stop_buffer_atr": 0.25})
    assert out["stop"] == pytest.approx(101.0 + 0.25 * ATR)
    assert out["stop"] > 100.0, "a short's stop must stay above the entry"


def test_the_floor_widens_a_stop_that_is_too_close_to_the_entry():
    """A tiny pattern right at the close would otherwise risk almost nothing
    and be swamped by costs."""
    out = _plan("long", 99.95, 100.1, 100.0, {"min_stop_atr": 0.5})
    assert out["stop"] == pytest.approx(100.0 - 0.5 * ATR)


def test_the_floor_leaves_an_already_wide_stop_alone():
    out = _plan("long", 97.0, 100.5, 100.0, {"min_stop_atr": 0.5})
    assert out["stop"] == pytest.approx(97.0), "a 3 ATR stop must not be pulled in to 0.5"


def test_the_floor_applies_to_shorts_on_the_correct_side():
    out = _plan("short", 99.9, 100.05, 100.0, {"min_stop_atr": 0.5})
    assert out["stop"] == pytest.approx(100.0 + 0.5 * ATR)


def test_buffer_and_floor_together_take_whichever_is_wider():
    # buffer alone would give 99.9 - 0.25 = 99.65 (0.35 from entry); the floor wins
    out = _plan("long", 99.9, 100.1, 100.0, {"stop_buffer_atr": 0.25, "min_stop_atr": 0.5})
    assert out["stop"] == pytest.approx(99.5)
    # here the buffered stop is already past the floor, so it stands
    out = _plan("long", 98.0, 100.2, 100.0, {"stop_buffer_atr": 0.25, "min_stop_atr": 0.5})
    assert out["stop"] == pytest.approx(97.75)


def test_a_wider_stop_lowers_the_target_distance_needed_to_clear_min_rrr():
    """The whole point. With cost c per unit of risk, a net 1.5 R:R needs a
    target 1.5 + 2.5c away, so shrinking c shrinks the bar."""
    price = 100.0
    def needed(stop):
        risk = abs(price - stop)
        c = price * 0.12 / 100 / risk
        return 1.5 + 2.5 * c
    tight, wide = needed(99.86), needed(99.50)     # 0.14% vs 0.50% stops
    assert tight > 3.5, "a pattern-low stop needs an implausible target"
    assert wide < 2.2
    assert wide < tight


def test_the_support_check_measures_the_pattern_not_the_buffer():
    """The structure is the pattern's low; the buffer is only how far beyond it
    the stop is parked. Measuring the buffered price would spend half the
    tolerance on the buffer and fail setups sitting exactly where we want."""
    w = _window()
    w[-1] = {"time": "2026-09-18T09:45:00+05:30", "open": 100.0, "high": 100.5,
             "low": 99.0, "close": 100.0, "volume": 20_000}
    patterns = [{"name": "Hammer", "bias": "bullish", "strength": 3}]
    levels = [{"price": 99.0, "kind": "swing", "touches": 3}]      # exactly at the pattern low
    p = {**trader_brain.DEFAULTS, "stop_buffer_atr": 0.4, "sr_tolerance_atr": 0.5}
    out = trader_brain._checklist("long", w, patterns, levels, atr_v=ATR, vol10=1.5,
                                  htf_trend="up", structure="uptrend", macd_v={"hist": 1.0},
                                  rsi_v=55.0, always_in="long", news_score=None,
                                  fundamentals_score=None, p=p)
    sr = next(i for i in out["items"] if i["key"] == "sr")
    assert sr["ok"], sr["detail"]
    assert out["stop"] == pytest.approx(98.6)


def test_the_cost_rule_and_the_buffer_attack_the_same_problem_from_two_sides():
    """min_stop_to_cost rejects a too-tight stop; the buffer prevents one.
    A pattern that would have been rejected can now clear the floor."""
    tiny = {"stop_buffer_atr": 0.0, "min_stop_atr": 0.0}
    widened = {"stop_buffer_atr": 0.0, "min_stop_atr": 0.5}
    a = _plan("long", 99.97, 100.05, 100.0, tiny)
    b = _plan("long", 99.97, 100.05, 100.0, widened)
    cost_item = lambda out: next(i for i in out["items"] if i["key"] == "cost")
    assert not cost_item(a)["ok"], "a 0.03% stop is inside the round trip's cost"
    assert cost_item(b)["ok"], "widened to 0.5 ATR it clears the floor"


def test_the_plan_still_reports_a_finite_stop_and_target():
    out = _plan("long", 99.0, 100.5, 100.0, {"stop_buffer_atr": 0.25, "min_stop_atr": 0.5})
    assert out["stop"] is not None and math.isfinite(out["stop"])
    assert out["entry"] == pytest.approx(100.0)


def test_min_stop_cost_widen_is_off_by_default_43():
    assert trader_brain.DEFAULTS["min_stop_cost_widen"] is None


def test_the_cost_floor_widens_a_stop_that_one_atr_leaves_under_the_cost_43():
    # ATR is 1.0 on a 100 stock, so 1 ATR = 1%; a 0.2 ATR here (quiet stock) would be 0.2%.
    quiet = {"stop_buffer_atr": 0.0, "min_stop_atr": 0.001}          # ATR floor effectively off
    base = _plan("long", 99.97, 100.05, 100.0, quiet)
    wide = _plan("long", 99.97, 100.05, 100.0, {**quiet, "min_stop_cost_widen": 3})
    cost = 100.0 * trader_brain.DEFAULTS["cost_pct"] / 100
    assert base["entry"] - base["stop"] < 3 * cost
    assert wide["entry"] - wide["stop"] == pytest.approx(3 * cost, abs=0.01)   # 3 round trips (plan rounds to 2 dp)
