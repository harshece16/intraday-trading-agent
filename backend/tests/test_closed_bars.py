"""The live checklist reads only finished candles, while stops and fills use the live price (issue #18)."""
import functools
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd

import config
import data_provider
import database
import scanner
import trader_brain
import trading_engine
from state import AppState, _new_position

IST = data_provider.IST


def _bars(last_start, n=100, close=100.0, volume=1000, delayed=False):
    """n consecutive 5-minute bars ending with the bar that starts at last_start."""
    out = []
    for i in range(n):
        t = last_start - timedelta(minutes=5 * (n - 1 - i))
        bar = {"time": t.isoformat(), "open": close, "high": close + 1, "low": close - 1,
               "close": close, "volume": volume}
        if delayed:
            bar["delayed"] = True
        out.append(bar)
    return out


def _at(h, m, s=0, day=16):
    return datetime(2026, 9, day, h, m, s, tzinfo=IST)


# ---- data_provider.closed_bars --------------------------------------------

def test_realtime_forming_bar_is_dropped():
    candles = _bars(_at(11, 20))
    assert data_provider.closed_bars(candles, "5m", now=_at(11, 22, 18)) == candles[:-1]


def test_realtime_bar_is_kept_once_it_has_ended():
    candles = _bars(_at(11, 20))
    assert data_provider.closed_bars(candles, "5m", now=_at(11, 25)) == candles


def test_delayed_feed_newest_row_is_never_trusted_during_the_session():
    # 20 minutes after the bar "ended" by the wall clock, but a delayed feed's
    # newest row can still be filling.
    candles = _bars(_at(10, 50), delayed=True)
    assert data_provider.closed_bars(candles, "5m", now=_at(11, 10)) == candles[:-1]


def test_delayed_feed_newest_row_is_kept_once_the_session_has_settled():
    candles = _bars(_at(15, 25), delayed=True)
    assert data_provider.closed_bars(candles, "5m", now=_at(15, 45)) == candles[:-1]
    assert data_provider.closed_bars(candles, "5m", now=_at(16, 0)) == candles


def test_delayed_feed_previous_session_is_kept():
    candles = _bars(_at(15, 25, day=15), delayed=True)
    assert data_provider.closed_bars(candles, "5m", now=_at(9, 20)) == candles


def test_explicit_delayed_flag_covers_untagged_candles():
    candles = _bars(_at(10, 50))
    assert data_provider.closed_bars(candles, "5m", now=_at(11, 10)) == candles
    assert data_provider.closed_bars(candles, "5m", now=_at(11, 10), delayed=True) == candles[:-1]


def test_naive_timestamps_are_read_as_ist():
    candles = [{"time": "2026-09-16T11:20:00", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
    assert data_provider.closed_bars(candles, "5m", now=_at(11, 22)) == []
    assert data_provider.closed_bars(candles, "5m", now=_at(11, 25)) == candles


def test_empty_and_non_intraday_input_is_returned_unchanged():
    assert data_provider.closed_bars([], "5m", now=_at(11, 22)) == []
    daily = _bars(_at(11, 20))
    assert data_provider.closed_bars(daily, "1d", now=_at(11, 22)) == daily


def _yf_frame(ticker=None):
    idx = pd.DatetimeIndex([pd.Timestamp("2026-09-16 05:40", tz="UTC"),
                            pd.Timestamp("2026-09-16 05:45", tz="UTC")])
    df = pd.DataFrame({"Open": [1.0, 1.0], "High": [1.0, 1.0], "Low": [1.0, 1.0],
                       "Close": [1.0, 1.0], "Volume": [10, 10]}, index=idx)
    return pd.concat({ticker: df}, axis=1) if ticker else df


def test_yfinance_candles_are_tagged_delayed():
    with patch("yfinance.download", return_value=_yf_frame()):
        single = data_provider._get_intraday_candles_yfinance("TCS", "5m", "5d")
    with patch("yfinance.download", return_value=_yf_frame("TCS.NS")):
        batch = data_provider._get_intraday_candles_yfinance_batch(["TCS"], "5m", "5d")
    assert single and all(c["delayed"] for c in single)
    assert batch["TCS"] and all(c["delayed"] for c in batch["TCS"])


# ---- the engine ------------------------------------------------------------

def _engine():
    state = AppState(watchlist=[], paper_mode=True)
    engine = trading_engine.TradingEngine(state)
    engine.scanner = None
    return engine, state


def test_engine_checklist_reads_finished_bars_while_stops_use_the_live_price(monkeypatch):
    engine, state = _engine()
    state.positions["TESTCO"] = _new_position()
    candles = _bars(_at(11, 20))
    candles[-1] = {**candles[-1], "close": 105.0}  # the forming bar's latest price

    seen_bars, seen_ltp = [], []
    engine.strategy_fn = lambda bars, prev_state=None, **kw: (seen_bars.append(bars), (None, {}))[1]
    monkeypatch.setattr(engine, "_check_stop_take", lambda sym, ltp: (seen_ltp.append(ltp), False)[1])

    engine._process_symbol("TESTCO", candles=candles, now=_at(11, 22, 18))
    engine._process_symbol("TESTCO", candles=candles, now=_at(11, 25))

    assert seen_bars[0] == candles[:-1]
    assert seen_bars[1] == candles
    assert seen_ltp == [105.0, 105.0]
    assert state.candles["TESTCO"][-1]["close"] == 105.0  # the chart still shows the forming bar


def _checklist_short_analysis(stop=101.0, target=98.0):
    plan = {"side": "short", "stop": stop, "target": target, "entry": 100.0, "rrr": 1.68,
            "size_factor": 1.0, "passed": True, "items": [], "pattern": "Bearish Engulfing"}
    return {"setup": "Bearish Engulfing", "entry_mode": "checklist", "bull_score": 0.0, "bear_score": 20.0,
            "bear_confirmations": ["trend", "momentum", "levels", "volume"], "confirmations": [],
            "adx": 40, "checklist": {"short": plan}, "bar_time": "2026-09-16T11:20:00+05:30"}


def _allow_entries(monkeypatch):
    monkeypatch.setattr(database, "journal_summary", lambda: {"scorecard": [
        {"criterion": c, "status": "pass", "detail": ""} for c in ("x", "y", "z")]})
    monkeypatch.setattr(database, "new_position_id", lambda: "pos-1")
    monkeypatch.setattr(database, "record_trade", lambda *a, **k: None)
    monkeypatch.setitem(config.RISK, "total_capital", 100000)


def test_entry_is_blocked_when_the_live_price_has_passed_the_stop(monkeypatch):
    _allow_entries(monkeypatch)
    engine, state = _engine()
    state.positions["TESTCO"] = _new_position()

    entered = engine._try_enter("TESTCO", "SHORT", 101.5, _bars(_at(11, 20), n=20), _checklist_short_analysis())

    assert entered is False
    assert state.positions["TESTCO"]["quantity"] == 0
    assert any("already passed the plan's stop" in e["message"] for e in state.activity)


def test_entry_goes_in_and_records_the_candle_and_live_reward_to_risk(monkeypatch):
    _allow_entries(monkeypatch)
    engine, state = _engine()
    state.positions["TESTCO"] = _new_position()

    entered = engine._try_enter("TESTCO", "SHORT", 100.0, _bars(_at(11, 20), n=20), _checklist_short_analysis())

    assert entered is True
    assert state.positions["TESTCO"]["quantity"] < 0
    note = state.trades[0]["note"]
    assert "on the 11:20 candle" in note and "1.68 at the entry price" in note


# ---- trader_brain.recheck_plan ---------------------------------------------

def test_recheck_plan_uses_the_checklists_own_reward_to_risk():
    plan = {"stop": 99.0, "target": 103.0}
    got = trader_brain.recheck_plan(plan, "long", 100.0, {"cost_pct": 0.12, "min_rrr": 1.5})
    cost = 100.0 * 0.12 / 100
    assert got["ok"] is True
    assert abs(got["rrr"] - (3.0 - cost) / (1.0 + cost)) < 1e-9


def test_recheck_plan_rejects_a_long_below_its_stop_or_past_its_target():
    plan = {"stop": 99.0, "target": 103.0}
    assert trader_brain.recheck_plan(plan, "long", 98.9)["ok"] is False
    assert trader_brain.recheck_plan(plan, "long", 103.0)["ok"] is False


def test_recheck_plan_rejects_a_fill_that_leaves_too_little_reward():
    # Price has drifted most of the way to the target since the bar closed.
    got = trader_brain.recheck_plan({"stop": 99.0, "target": 103.0}, "long", 102.0, {"min_rrr": 1.5})
    assert got["ok"] is False and got["rrr"] < 1.5
    assert "below 1.5" in got["reason"]


# ---- scanner relative volume -----------------------------------------------

def test_scanner_relative_volume_ignores_the_unfinished_newest_row(monkeypatch):
    monkeypatch.setattr(data_provider, "closed_bars",
                        functools.partial(data_provider.closed_bars, now=_at(9, 32)))
    prior = [{"time": (_at(9, 15, day=15) + timedelta(minutes=5 * i)).isoformat(),
              "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000} for i in range(5)]
    today = [{"time": (_at(9, 15) + timedelta(minutes=5 * i)).isoformat(),
              "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000} for i in range(3)]
    today[-1]["volume"] = 100  # the 09:25 bar has only just started filling

    m = scanner.intraday_metrics(prior + today, {"close": 100.0})

    assert m["rvol"] == 1.0  # 2 finished bars vs the same 2 bars yesterday, not 2,100 vs 3,000
    assert m["bars_today"] == 3
