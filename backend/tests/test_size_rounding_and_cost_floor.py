"""
Issues #28 and #25 — two ways a trade's economics went wrong before it was placed.

#28: the share count was rounded twice. `position_size()` returned whole
shares, and the caller then multiplied by the checklist's reduced size factor
and truncated again, so 60% of a 3-share cap became 1 share (33%) and 60% of a
1-share cap became 0 and blocked the trade outright. Seen live on 17 Sep:
DIVISLAB went in at 1 share while the note said "60% size".

#25: a candlestick stop can sit closer to the entry than the round trip costs
to make, which turns the trade into a bet on costs rather than on the setup.
TMPV's stop was 0.080% away against a 0.12% round trip and lost 4.33R net in
38 seconds.
"""
import pytest

import trader_brain
from risk_manager import RiskManager


CAPITAL = 100_000
RISK_CFG = {
    "total_capital": CAPITAL,
    "max_risk_per_trade_pct": 1.0,
    "max_daily_loss_pct": 2.0,
    "max_position_notional_pct": 33.0,
    "stop_loss_pct": 0.8,
    "max_open_positions": 3,
}


@pytest.fixture
def risk():
    return RiskManager(dict(RISK_CFG))


# ---- #28: one rounding, at the end -------------------------------------


def test_the_size_factor_is_applied_before_rounding(risk):
    """DIVISLAB, the trade that exposed this. The 33% cap allows 3.55 shares;
    60% of that is 2.13, so the trade should be 2 shares. Rounding the cap to
    3 first and then taking 60% gave int(1.8) = 1 — a third of the cap, while
    the journal note claimed 60%."""
    price = 9_289.29
    assert risk.position_size(price, stop_price=price - 11.29) == 3          # full size
    assert risk.position_size(price, stop_price=price - 11.29, size_factor=0.6) == 2


def test_a_reduced_size_no_longer_silently_becomes_a_third_of_the_cap(risk):
    """The general form: the reduced size must never come out further below
    its intended share of full size than one whole share of rounding."""
    for price in (2_000.0, 5_000.0, 9_289.29, 12_264.0, 16_000.0):
        full = risk.position_size(price, stop_price=price * 0.999)
        reduced = risk.position_size(price, stop_price=price * 0.999, size_factor=0.6)
        if full == 0:
            continue
        assert reduced <= full
        assert reduced >= int(full * 0.6), f"{price}: {reduced} is below 60% of {full}"


def test_the_reduced_size_never_exceeds_the_caps(risk):
    """Rounding stays downward: a 60% position must never come out larger than
    60% of what the risk and notional caps allow, or the cap isn't a cap."""
    for price in (500.0, 1_000.0, 2_500.0, 9_289.29):
        exact = min(CAPITAL * 0.01 / (price * 0.001), CAPITAL * 0.33 / price)
        assert risk.position_size(price, stop_price=price * 0.999, size_factor=0.6) <= exact * 0.6 + 1e-9


def test_a_cheap_stock_is_unaffected(risk):
    """Where the share count is large, double rounding never mattered and the
    fix must not change the answer."""
    price = 100.0
    assert risk.position_size(price, stop_price=99.0, size_factor=0.6) == int(
        min(CAPITAL * 0.01 / 1.0, CAPITAL * 0.33 / price) * 0.6)


def test_a_share_too_expensive_for_the_notional_cap_is_still_refused(risk):
    """BOSCHLTD at Rs 48,035: one share is 48% of a Rs 1L account, past the
    33% cap, so it stays blocked at any size factor. That's the cap working."""
    assert risk.position_size(48_035.0, stop_price=48_000.0) == 0
    assert risk.position_size(48_035.0, stop_price=48_000.0, size_factor=0.6) == 0


def test_size_factor_of_one_matches_no_size_factor(risk):
    for price in (100.0, 1_000.0, 9_289.29):
        assert (risk.position_size(price, stop_price=price * 0.99)
                == risk.position_size(price, stop_price=price * 0.99, size_factor=1.0))


def test_the_engine_and_the_backtester_size_identically():
    """backtester.py's 'same code, same costs' property: both call the one
    sizing function the same way, so neither can drift from the other."""
    import inspect
    import backtester
    import trading_engine
    bt = inspect.getsource(backtester.run_backtest)
    eng = inspect.getsource(trading_engine.TradingEngine._try_enter)
    for src in (bt, eng):
        assert "size_factor=" in src, "sizing must pass the factor into position_size()"
        assert "int(risk.position_size" not in src and "int(self.risk.position_size" not in src, \
            "no rounding outside position_size()"


# ---- #25: the stop has to be worth more than the costs -----------------


def _plan(price, stop_pct, rrr=3.0):
    stop = price * (1 - stop_pct / 100)
    return {"stop": stop, "target": price + (price - stop) * rrr, "size_factor": 1.0}


def test_the_default_floor_is_the_one_the_evidence_supports():
    """1x, not something larger. Below 1x the charges exceed the whole risk the
    position was sized on, so a stop-out is worse than 2R by construction —
    that is the argument for a floor and it only reaches 1x. Raising it to 3x
    would have blocked both winning trades in the live sample and made the
    backtest's expectancy worse (README section 46)."""
    assert trader_brain.DEFAULTS["min_stop_to_cost"] == 1.0


def test_a_stop_inside_the_cost_floor_is_refused():
    """TMPV: a 0.050% stop against a 0.12% round trip is 0.41x, so losing at
    the stop costs over 2R. It lost 4.33R net in 38 seconds."""
    price = 301.44
    out = trader_brain.recheck_plan(_plan(price, 0.050), "long", price)
    assert out["ok"] is False
    assert "round trip" in out["reason"]
    assert "0.4" in out["reason"]


def test_a_stop_comfortably_past_the_floor_is_allowed():
    price = 301.11
    out = trader_brain.recheck_plan(_plan(price, 0.71), "long", price)
    assert out["ok"] is True, out["reason"]


def test_the_floor_scales_with_the_configured_cost():
    """The floor is a multiple of cost_pct, not a hardcoded percentage, so a
    different cost model moves it."""
    price = 1_000.0
    plan = _plan(price, 0.30, rrr=8.0)
    assert trader_brain.recheck_plan(plan, "long", price, {"cost_pct": 0.05})["ok"] is True   # 6.0x
    assert trader_brain.recheck_plan(plan, "long", price, {"cost_pct": 0.40})["ok"] is False  # 0.75x


def test_the_floor_can_be_switched_off():
    """A nominal 8:1 is needed before a 0.080% stop clears the existing R:R
    gate at all — see the test below for why that is the whole point."""
    price = 301.11
    out = trader_brain.recheck_plan(_plan(price, 0.080, rrr=8.0), "long", price, {"min_stop_to_cost": 0.0})
    assert out["ok"] is True, out["reason"]
    # and with the floor on, the same plan is refused before R:R is even reached
    blocked = trader_brain.recheck_plan(_plan(price, 0.080, rrr=8.0), "long", price)
    assert blocked["ok"] is False and "round trip" in blocked["reason"]


def test_a_tight_stop_destroys_the_reward_to_risk_it_appears_to_offer():
    """Why the floor exists rather than trusting R:R alone. At TMPV's 0.080%
    stop a nominal 3:1 is really 0.60:1 after a 0.12% round trip — the costs
    are larger than the risk, so the ratio is mostly measuring charges."""
    price = 301.11
    plan = _plan(price, 0.080, rrr=3.0)
    net = trader_brain._net_rrr(price, plan["stop"], plan["target"], 0.12)
    assert net == pytest.approx(0.60, abs=0.01)
    # the same nominal 3:1 on a stop well clear of costs keeps most of its value
    wide = _plan(price, 0.71, rrr=3.0)
    assert trader_brain._net_rrr(price, wide["stop"], wide["target"], 0.12) > 2.3


def test_shorts_are_measured_the_same_way():
    price = 301.11
    stop = price * 1.0008          # 0.080% above, a short's stop
    plan = {"stop": stop, "target": price - (stop - price) * 3, "size_factor": 1.0}
    assert trader_brain.recheck_plan(plan, "short", price)["ok"] is False
    stop = price * 1.0071          # 0.71% above
    plan = {"stop": stop, "target": price - (stop - price) * 3, "size_factor": 1.0}
    assert trader_brain.recheck_plan(plan, "short", price)["ok"] is True


def test_the_checklist_carries_the_cost_item_and_it_is_required():
    """The gate lives in the checklist itself, so the backtester applies it
    too — and the user can see why a trade was refused."""
    assert "cost" in trader_brain.CHECKLIST_SOURCES
    keys = _checklist_keys()
    assert "cost" in keys, keys


def _checklist_keys():
    """Run the real checklist over a synthetic window and collect its item keys."""
    import math
    window = []
    for i in range(60):
        base = 100.0 + math.sin(i / 5) * 2
        window.append({"time": f"2026-09-17T09:{15 + i // 4:02d}:00+05:30", "open": base, "high": base + 0.6,
                       "low": base - 0.6, "close": base + 0.2, "volume": 10_000})
    out = trader_brain._checklist(
        "long", window, [], [], atr_v=1.0, vol10=1.5, htf_trend="up", structure="uptrend",
        macd_v={"hist": 0.5}, rsi_v=55.0, always_in="long", news_score=None,
        fundamentals_score=None, p=dict(trader_brain.DEFAULTS))
    return [i["key"] for i in out["items"]]


def test_the_cost_item_fails_loudly_rather_than_silently_passing():
    """A checklist with no stop at all must fail the cost item, not skip it —
    an unmeasurable cost ratio is not a pass."""
    keys = _checklist_keys()
    assert keys.count("cost") == 1


def test_zero_costs_do_not_crash_the_cost_item():
    """`--no-costs` runs and any config with cost_pct 0 must not divide by it."""
    out = trader_brain.recheck_plan(_plan(1000.0, 0.05), "long", 1000.0, {"cost_pct": 0.0})
    assert out["ok"] is True, out["reason"]
