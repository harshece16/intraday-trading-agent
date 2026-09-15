"""
swing_backtester.run_swing_backtest() — multi-day long-only holds on daily
bars (README §37). Synthetic bars, no network: checks entry/exit timing,
cost-model selection by actual holding, the optional stop, no double
entry while already holding, and that the ATR risk unit never peeks at
the entry day's own bar.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from costs import DELIVERY_COSTS, ZERO_COSTS, leg_cost
from swing_backtester import ic_summary, run_swing_backtest

DATES = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(40)]


def _bars(close_fn=lambda i: 100.0 + i):
    return [{"time": f"{d}T00:00:00+05:30", "open": close_fn(i) - 0.5, "high": close_fn(i) + 1.0,
             "low": close_fn(i) - 1.5, "close": close_fn(i), "volume": 1000} for i, d in enumerate(DATES)]


def _run(daily, picks, hold, **kw):
    return run_swing_backtest(daily, picks, DATES, hold, notional_per_trade=10_000,
                              intraday_costs=kw.pop("intraday", ZERO_COSTS),
                              delivery_costs=kw.pop("delivery", ZERO_COSTS), **kw)


def test_enters_at_open_and_exits_at_close_after_hold_sessions():
    bars = _bars()
    trades = _run({"AAA": bars}, {DATES[20]: {"AAA": "LONG"}}, hold=2)
    assert len(trades) == 1
    t = trades[0]
    assert t["entry_date"] == DATES[20] and t["exit_date"] == DATES[21]
    assert t["entry_price"] == bars[20]["open"] and t["exit_price"] == bars[21]["close"]
    assert t["sessions_held"] == 2 and t["reason"] == "time"


def test_hold_one_is_same_day_and_uses_intraday_costs():
    trades = _run({"AAA": _bars()}, {DATES[20]: {"AAA": "LONG"}}, hold=1,
                  intraday=config.COSTS, delivery=DELIVERY_COSTS)
    assert trades[0]["exit_date"] == DATES[20] and trades[0]["cost_model"] == "intraday"


def test_overnight_hold_uses_delivery_costs():
    trades = _run({"AAA": _bars()}, {DATES[20]: {"AAA": "LONG"}}, hold=3,
                  intraday=config.COSTS, delivery=DELIVERY_COSTS)
    assert trades[0]["cost_model"] == "delivery"


def test_short_picks_are_never_traded():
    assert _run({"AAA": _bars()}, {DATES[20]: {"AAA": "SHORT"}}, hold=2) == []


def test_no_second_entry_while_already_holding():
    picks = {DATES[20]: {"AAA": "LONG"}, DATES[21]: {"AAA": "LONG"}, DATES[22]: {"AAA": "LONG"}}
    trades = _run({"AAA": _bars()}, picks, hold=3)
    assert len(trades) == 1 and trades[0]["exit_date"] == DATES[22]


def test_stop_exits_at_stop_or_gapped_open():
    bars = _bars(lambda i: 100.0)
    bars[21] = {**bars[21], "open": 99.0, "low": 50.0}  # crashes through the stop intraday
    trades = _run({"AAA": bars}, {DATES[20]: {"AAA": "LONG"}}, hold=5, stop_atr=1.0)
    t = trades[0]
    assert t["reason"] == "stop" and t["exit_date"] == DATES[21]
    # open (99.0) was still above the stop, so the fill is the stop itself: entry - 1 ATR
    assert abs(t["exit_price"] - (t["entry_price"] - t["risk_per_share"])) < 1e-9

    gapped = _bars(lambda i: 100.0)
    gapped[21] = {**gapped[21], "open": 60.0, "low": 50.0}  # opens far below the stop
    g = _run({"AAA": gapped}, {DATES[20]: {"AAA": "LONG"}}, hold=5, stop_atr=1.0)[0]
    assert g["reason"] == "stop" and g["exit_price"] == 60.0  # filled at the gapped open, not the stop


def test_risk_unit_never_uses_the_entry_days_own_bar():
    calm, spiky = _bars(lambda i: 100.0), _bars(lambda i: 100.0)
    spiky[20] = {**spiky[20], "high": 500.0, "low": 1.0}  # huge range ON the entry day
    a = _run({"AAA": calm}, {DATES[20]: {"AAA": "LONG"}}, hold=1)[0]
    b = _run({"AAA": spiky}, {DATES[20]: {"AAA": "LONG"}}, hold=1)[0]
    assert a["risk_per_share"] == b["risk_per_share"]


def test_intraday_leg_cost_unchanged_by_delivery_keys():
    # config.COSTS has no stt_pct_buy / dp_charge_per_sell -> same formula as before.
    c = config.COSTS
    turnover = 1000 * 10
    brokerage = min(c["brokerage_per_order"], turnover * c["brokerage_pct"] / 100)
    exch = turnover * c["exchange_txn_pct"] / 100
    expected_buy = brokerage + exch + turnover * c["sebi_charges_pct"] / 100 \
        + turnover * c["stamp_duty_pct_buy"] / 100 + (brokerage + exch) * c["gst_pct"] / 100
    assert abs(leg_cost("BUY", 1000, 10, c) - expected_buy) < 1e-9


def test_delivery_costs_charge_stt_on_the_buy_and_dp_on_the_sell():
    assert leg_cost("BUY", 1000, 10, DELIVERY_COSTS) > leg_cost("BUY", 1000, 10, config.COSTS)
    sell = leg_cost("SELL", 1000, 10, DELIVERY_COSTS)
    assert sell >= 10_000 * 0.1 / 100 + DELIVERY_COSTS["dp_charge_per_sell"]


def test_ic_summary_mean_tstat_and_positive_share():
    flat = ic_summary([0.1, -0.1, 0.1, -0.1])
    assert flat["days"] == 4 and abs(flat["mean_ic"]) < 1e-12 and flat["pct_positive"] == 50
    up = ic_summary([0.05, 0.06, 0.04])
    assert up["mean_ic"] > 0 and up["t_stat"] > 0
    assert ic_summary([0.1])["mean_ic"] is None  # one day is not a time series
