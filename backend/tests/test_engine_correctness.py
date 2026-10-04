"""
Regression tests for the correctness bugs found by the 2026-10-05 logic
review (README section 122):

- #256 the first ticks after a restart traded before the first scan
- #257 the Scorecard counted a partially filled exit as several trades
- #258 the tax box's charges included open entry legs
- #259 the engine scanned all day on holidays and weekends and churned the
       tracked list

Every test drives the real code against a throwaway journal; no Kite call.
"""
import threading
import time
from datetime import date, datetime

import pytest

import config
import data_provider
import database
import liquidity
import trading_engine
from state import AppState, _new_position
from tests.test_engine_money_paths import BARS, FAILING, analysis, quiet_tick

IST = trading_engine.IST


@pytest.fixture(autouse=True)
def no_kite(monkeypatch):
    monkeypatch.setattr(config, "KITE_API_KEY", "")
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "")


# ---------------------------------------------------------------------------
# #256 no entries or cards before the first scan
# ---------------------------------------------------------------------------

def _fake_strategy(signal, a):
    def fn(bars, prev_state=None, **params):
        return signal, {**a, "entries_today": 1, "entry_day": "2026-10-01", "long_ok": signal == "BUY",
                        "short_ok": signal == "SHORT"}
    return fn


def test_the_first_tick_after_a_restart_does_not_enter_before_the_first_scan(monkeypatch):
    monkeypatch.setattr(liquidity, "check", lambda *a, **k: (True, None, {}))
    monkeypatch.setattr(database, "journal_summary", lambda: FAILING)
    state = AppState(watchlist=[], paper_mode=True)
    eng = trading_engine.TradingEngine(state)           # what a deploy restart builds
    assert eng.scanner is not None and state.market is None
    released = threading.Event()

    def slow_scan():                                    # 2026-10-01 12:19: the first scan took 39 s
        released.wait(10)
        raise RuntimeError("test: the scan is not needed")

    monkeypatch.setattr(eng.scanner, "run", slow_scan)
    quiet_tick(monkeypatch, eng, "open")
    monkeypatch.setattr(eng, "request_scan", trading_engine.TradingEngine.request_scan.__get__(eng))
    candles = [{"time": f"2026-10-01T10:{m:02d}:00+05:30", "open": 100, "high": 101, "low": 99, "close": 100,
                "volume": 1000} for m in range(0, 60, 5)]
    monkeypatch.setattr(data_provider, "get_candles_batch", lambda syms, **k: {s: candles for s in syms})
    eng.strategy_fn = _fake_strategy("BUY", analysis())
    state.set_watchlist(["HDFCBANK"])
    try:
        eng._tick_impl()
        assert eng._scan_thread is not None and eng._scan_thread.is_alive()   # the scan is still running
        assert state.positions["HDFCBANK"]["quantity"] == 0
        assert any("waiting for the first market scan" in a["message"] for a in state.activity)
    finally:
        released.set()
        eng._scan_thread.join(5)


def test_no_review_card_before_the_first_scan(monkeypatch):
    monkeypatch.setitem(config.REVIEW_QUEUE, "enabled", True)
    eng = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    eng.state.positions["AAA"] = _new_position()
    eng._offer_near_misses("AAA", 100.0, BARS, analysis(
        {**analysis()["checklist"]["long"], "items": [
            {**i, "ok": i["key"] != "volume"} for i in analysis()["checklist"]["long"]["items"]], "passed": False}))
    assert eng.review_queue.snapshot()["cards"] == []
    assert "first market scan" in eng._entry_block_reason("AAA", "LONG")
    eng.state.market = {"bias": "neutral", "reasons": []}           # the first scan has finished
    assert eng._entry_block_reason("AAA", "LONG") is None


# ---------------------------------------------------------------------------
# #257 the Scorecard counts a position once
# ---------------------------------------------------------------------------

def _leg(i, pid, side, qty, price, realized=0.0, r=None, risk=None, mode="live"):
    database.record_trade({"id": f"{pid}-{i}", "position_id": pid, "ts": time.time() - 100 + i, "symbol": pid or "LEGACY",
                           "side": side, "quantity": qty, "price": price, "mode": mode, "reason": "t",
                           "note": None, "realized": realized, "charges": 0.0, "initial_risk": risk,
                           "r_multiple": r})


def test_a_partially_filled_exit_counts_as_one_trade():
    # a winner closed in one fill: +2R
    _leg(0, "W", "BUY", 100, 1000.0)
    _leg(1, "W", "SELL", 100, 1020.0, realized=2000.0, r=2.0, risk=10.0)
    # a same-size loser closed in two Kite fills (1 + 99): -1R in all
    _leg(2, "X", "BUY", 100, 1000.0)
    _leg(3, "X", "SELL", 1, 990.0, realized=-10.0, r=-1.0, risk=10.0)
    _leg(4, "X", "SELL", 99, 990.0, realized=-990.0, r=-1.0, risk=10.0)
    assert database.closed_trade_rs() == pytest.approx([2.0, -1.0])
    ts = database.trade_stats()
    assert ts["closed_trades"] == 2 and ts["win_rate_pct"] == 50.0 and ts["expectancy_r"] == pytest.approx(0.5)


def test_a_row_without_a_position_id_still_counts_on_its_own():
    _leg(0, None, "SELL", 10, 100.0, realized=-5.0, r=-0.5, risk=1.0)
    assert database.closed_trade_rs() == [-0.5]


# ---------------------------------------------------------------------------
# #258 the tax box's charges match its gross and net
# ---------------------------------------------------------------------------

def test_the_tax_box_adds_up_with_a_position_open(monkeypatch):
    st = AppState(["AAA", "BBB"], paper_mode=True)
    eng = trading_engine.TradingEngine(st)
    eng._execute("AAA", "BUY", 10, 100.0, position_id="a", live=False)
    eng._execute("AAA", "SELL", 10, 102.0, position_id="a", initial_risk=1.0, live=False)
    eng._execute("BBB", "SELL", 4, 8039.0, position_id="b", live=False)      # still open
    t = st.snapshot()["tax"]
    assert t["gross_pnl"] - t["charges"] == pytest.approx(t["net_pnl"])
    paid = sum(x["charges"] for x in st.trades)
    bbb_entry = next(x for x in st.trades if x["symbol"] == "BBB")["charges"]
    assert t["open_charges"] == pytest.approx(bbb_entry)
    assert t["charges"] + t["open_charges"] == pytest.approx(paid)


# ---------------------------------------------------------------------------
# #259 off days: one scan, and the tracked list is left alone
# ---------------------------------------------------------------------------

class FakeScanner:
    def __init__(self):
        self.runs = 0
        self.cfg = {"interval_minutes_open": 5, "interval_minutes_closed": 30}

    def due(self, market_open):
        return True

    def list_fixed_for(self, day):
        return False

    def run(self):
        self.runs += 1
        return {"active": ["NEWPICK"], "market": {"bias": "neutral", "reasons": ["flat"]}, "rows": [],
                "scanned": 100, "duration_s": 1.0, "excluded_count": 0, "session_date": "2026-10-02"}


def _off_day_engine(monkeypatch, day):
    eng = trading_engine.TradingEngine(AppState(watchlist=["OLDPICK"], paper_mode=True))
    eng.scanner = FakeScanner()
    quiet_tick(monkeypatch, eng, "closed")
    monkeypatch.setattr(eng, "request_scan", trading_engine.TradingEngine.request_scan.__get__(eng))
    monkeypatch.setattr(trading_engine.holidays, "holiday_name", lambda now: "Gandhi Jayanti" if day == 2 else None)
    def is_holiday(d):
        d = d.date() if isinstance(d, datetime) else d
        return d == date(2026, 10, 2)

    monkeypatch.setattr(trading_engine.holidays, "is_holiday", is_holiday)
    when = datetime(2026, 10, day, 11, 0, tzinfo=IST)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return when

    monkeypatch.setattr(trading_engine, "datetime", Clock)
    return eng


@pytest.mark.parametrize("day", [2, 3])        # Friday 2026-10-02 (a holiday), Saturday 2026-10-03
def test_an_off_day_scans_once_and_does_not_change_tracking(monkeypatch, day):
    eng = _off_day_engine(monkeypatch, day)
    for _ in range(4):
        eng._tick_impl()
        if eng._scan_thread:
            eng._scan_thread.join(5)
    assert eng.scanner.runs == 1
    assert eng.state.watchlist == ["OLDPICK"]
    assert eng.state.market == {"bias": "neutral", "reasons": ["flat"]}      # the plan is still shown
    assert not any(a["message"].startswith(("Now tracking", "Stopped tracking")) for a in eng.state.activity)


def test_a_trading_day_still_scans_on_its_cadence_and_tracks_the_picks(monkeypatch):
    eng = _off_day_engine(monkeypatch, 5)                                  # Monday 2026-10-05
    for _ in range(2):
        eng._tick_impl()
        if eng._scan_thread:
            eng._scan_thread.join(5)
    assert eng.scanner.runs == 2
    assert "NEWPICK" in eng.state.watchlist
