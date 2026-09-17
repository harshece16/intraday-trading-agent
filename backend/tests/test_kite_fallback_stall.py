"""Engine stalls while Kite is down (issue #23): serialized yfinance downloads, no retries on a rejected token, a tick watchdog."""
import threading
import time
from unittest.mock import patch

import pandas as pd
from kiteconnect.exceptions import TokenException

import config
import data_provider
import scanner
import trading_engine
from state import AppState


def _engine():
    engine = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    engine.scanner = None
    return engine


# ---- yfinance downloads never overlap --------------------------------------

def test_yfinance_downloads_never_overlap():
    active, peak, lock = [0], [0], threading.Lock()

    def slow_download(**kwargs):
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        time.sleep(0.05)
        with lock:
            active[0] -= 1
        return pd.DataFrame()

    with patch("yfinance.download", side_effect=slow_download):
        threads = [threading.Thread(target=data_provider.yf_download, kwargs={"tickers": "X"}) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert peak[0] == 1


def test_every_download_path_goes_through_the_lock(monkeypatch):
    calls = []
    monkeypatch.setattr(data_provider, "yf_download", lambda **kw: calls.append(kw["tickers"]) or pd.DataFrame())
    with patch("yfinance.download", side_effect=AssertionError("called yfinance.download directly")):
        data_provider._get_intraday_candles_yfinance("TCS", "5m", "5d")
        data_provider._get_intraday_candles_yfinance_batch(["TCS", "INFY"], "5m", "5d")
        scanner.download_batch(["TCS.NS"], "5d", "5m")
    assert calls == ["TCS.NS", ["TCS.NS", "INFY.NS"], ["TCS.NS"]]


def test_a_stuck_download_times_out_instead_of_blocking_forever(monkeypatch):
    monkeypatch.setattr(data_provider, "_YF_LOCK_TIMEOUT_SECONDS", 0.05)
    assert data_provider._YF_DOWNLOAD_LOCK.acquire(timeout=1)
    try:
        try:
            data_provider.yf_download(tickers="X")
            raise AssertionError("expected a timeout")
        except TimeoutError:
            pass
    finally:
        data_provider._YF_DOWNLOAD_LOCK.release()


# ---- a rejected Kite token isn't retried ------------------------------------

def _kite_configured(monkeypatch, token="old-token"):
    monkeypatch.setattr(config, "USE_KITE_DATA", True)
    monkeypatch.setattr(config, "KITE_API_KEY", "key")
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", token)


def test_rejected_kite_token_is_skipped_until_it_changes(monkeypatch):
    _kite_configured(monkeypatch)
    kite_calls = []

    def rejected(symbol, interval, period):
        kite_calls.append(symbol)
        raise TokenException("Incorrect `api_key` or `access_token`.")
    monkeypatch.setattr(data_provider, "_get_intraday_candles_kite", rejected)
    monkeypatch.setattr(data_provider, "_get_intraday_candles_yfinance_batch",
                        lambda symbols, interval, period: {s: [] for s in symbols})

    data_provider.get_candles_batch(["A", "B"])
    assert sorted(kite_calls) == ["A", "B"]
    assert data_provider.kite_data_active() is False

    data_provider.get_candles_batch(["A", "B"])
    assert sorted(kite_calls) == ["A", "B"]  # not retried

    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "new-token")  # user reconnected
    assert data_provider.kite_data_active() is True


def test_other_kite_errors_keep_kite_in_use(monkeypatch):
    _kite_configured(monkeypatch)

    def rate_limited(symbol, interval, period):
        raise RuntimeError("Too many requests")
    monkeypatch.setattr(data_provider, "_get_intraday_candles_kite", rate_limited)
    monkeypatch.setattr(data_provider, "_get_intraday_candles_yfinance_batch", lambda symbols, i, p: {})
    data_provider.get_candles_batch(["A"])
    assert data_provider.kite_data_active() is True


def test_capital_sync_marks_the_token_rejected(monkeypatch):
    _kite_configured(monkeypatch)
    monkeypatch.setitem(config.RISK, "sync_capital_with_kite", True)
    engine = _engine()

    class RejectingKite:
        def get_margins(self):
            raise TokenException("Incorrect `api_key` or `access_token`.")
    engine.kite_executor = RejectingKite()

    engine._sync_capital()
    assert data_provider.kite_data_active() is False


# ---- tick watchdog ------------------------------------------------------------

def test_watchdog_logs_stacks_once_for_a_stuck_tick(caplog):
    engine = _engine()
    engine._tick_started_at = time.time() - 300
    with caplog.at_level("ERROR", logger="trading_bot"):
        engine._check_tick_stall()
        engine._check_tick_stall()
    reports = [r for r in caplog.records if "Engine tick has been running" in r.getMessage()]
    assert len(reports) == 1
    assert "--- thread MainThread ---" in reports[0].getMessage()
    alerts = [e for e in engine.state.activity if e["level"] == "error" and "stuck on one cycle" in e["message"]]
    assert len(alerts) == 1


def test_watchdog_is_quiet_for_a_normal_tick(caplog):
    engine = _engine()
    engine._tick_started_at = time.time() - 10
    with caplog.at_level("ERROR", logger="trading_bot"):
        engine._check_tick_stall()
    assert not engine.state.activity
    assert not [r for r in caplog.records if "Engine tick has been running" in r.getMessage()]


def test_tick_records_its_start_and_clears_it(monkeypatch):
    engine = _engine()
    seen = []
    monkeypatch.setattr(engine, "_tick_impl", lambda: seen.append(engine._tick_started_at))
    engine.tick()
    assert seen[0] is not None
    assert engine._tick_started_at is None
