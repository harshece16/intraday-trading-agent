"""
Deep history from Kite, cached for backtests (issue #46).

yfinance stops at ~60 days of 5-minute candles, which caps a NIFTY 100
backtest at 21-42 trades. At the measured 2.51R spread of trade outcomes,
detecting a +0.5R edge needs 101 trades and +0.2R needs 631 — so every
strategy question so far has been decided on a sample too small to decide it.

The Kite session has been expired since 16 Sep, so these run against a fake
Kite whose behaviour is pinned to the documented API: historical_data(token,
from, to, interval) returning rows with a `date` datetime. What is covered is
pagination, resume, rate limiting, storage and the backtester's source
selection. What is NOT covered is Kite's real responses.
"""
import sqlite3
import threading
import time
from datetime import datetime, timedelta

import pytest

import kite_history


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(kite_history, "DB_PATH", tmp_path / "hist.db")
    # The real 0.4s pacing would add minutes to this file. Pacing is covered
    # on its own below, against dedicated RateLimiter instances.
    monkeypatch.setattr(kite_history._limiter, "min_interval", 0.0)
    kite_history._reset_connection()
    yield tmp_path / "hist.db"
    kite_history._reset_connection()


class FakeKite:
    """Returns one candle per trading-ish day in the window, and records every
    call so pagination and pacing can be asserted."""

    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on or set()

    def historical_data(self, token, frm, to, interval):
        self.calls.append((token, frm, to, interval))
        if len(self.calls) in self.fail_on:
            raise RuntimeError("Kite said no")
        rows, day = [], frm
        while day < to:
            if day.weekday() < 5:
                rows.append({"date": day.replace(hour=9, minute=15), "open": 100.0, "high": 101.0,
                             "low": 99.0, "close": 100.5, "volume": 1000})
            day += timedelta(days=1)
        return rows


def _download(kite, symbol="TESTCO", days=180, interval="5m"):
    return kite_history.download_symbol(symbol, interval=interval, days=days,
                                        kite=kite, token_for=lambda s: 12345)


# ---- pagination ---------------------------------------------------------


def test_a_long_span_is_split_into_windows_kite_will_accept():
    """The whole point: one request can't ask for two years."""
    kite = FakeKite()
    _download(kite, days=730)
    assert len(kite.calls) == 13, "730 days in 60-day windows"
    for _, frm, to, _ in kite.calls:
        assert (to - frm).days <= kite_history.CHUNK_DAYS


def test_windows_are_contiguous_and_cover_the_whole_span():
    kite = FakeKite()
    _download(kite, days=365)
    spans = [(frm, to) for _, frm, to, _ in kite.calls]
    for (_, end_a), (start_b, _) in zip(spans, spans[1:]):
        assert end_a == start_b, "a gap between windows would lose candles silently"
    assert (spans[-1][1] - spans[0][0]).days == 365


def test_windows_are_requested_oldest_first():
    kite = FakeKite()
    _download(kite, days=365)
    starts = [frm for _, frm, _, _ in kite.calls]
    assert starts == sorted(starts)


def test_the_interval_is_translated_to_kites_vocabulary():
    kite = FakeKite()
    _download(kite, days=60, interval="5m")
    assert kite.calls[0][3] == "5minute"
    _download(kite, days=60, interval="15m")
    assert kite.calls[-1][3] == "15minute"


# ---- resume -------------------------------------------------------------


def test_a_second_run_fetches_nothing_new():
    kite = FakeKite()
    first = _download(kite, days=365)
    calls_after_first = len(kite.calls)
    second = _download(kite, days=365)
    assert len(kite.calls) == calls_after_first, "a cached window must not be re-requested"
    assert second["windows"] == 0
    assert second["skipped"] == first["windows"]


def test_an_interrupted_pull_resumes_where_it_stopped():
    """A two-year pull that dies halfway must not start over."""
    kite = FakeKite(fail_on={3, 4})
    first = _download(kite, days=365)
    assert first["errors"] == 2
    retry = FakeKite()
    second = _download(retry, days=365)
    assert len(retry.calls) == 2, "only the two failed windows should be retried"
    assert second["errors"] == 0


def test_an_empty_window_is_remembered_rather_than_retried_forever():
    """A holiday stretch or a pre-listing period legitimately has no candles.
    Recording it stops every later run asking again."""
    class Empty(FakeKite):
        def historical_data(self, *a):
            super().historical_data(*a)
            return []
    kite = Empty()
    _download(kite, days=120)
    n = len(kite.calls)
    _download(kite, days=120)
    assert len(kite.calls) == n


def test_one_failed_window_does_not_abandon_the_symbol():
    kite = FakeKite(fail_on={2})
    counts = _download(kite, days=365)
    assert counts["errors"] == 1
    assert counts["windows"] == 6, "the other windows still stored"
    assert counts["rows"] > 0


def test_a_symbol_with_no_instrument_token_is_reported_not_raised():
    counts = kite_history.download_symbol(
        "NOSUCH", days=60, kite=FakeKite(),
        token_for=lambda s: (_ for _ in ()).throw(RuntimeError("no token")))
    assert counts["errors"] == 1 and counts["rows"] == 0


# ---- storage ------------------------------------------------------------


def test_candles_come_back_in_the_shape_the_backtester_expects():
    _download(FakeKite(), days=120)
    candles = kite_history.load("TESTCO", "5m")
    assert candles, "nothing stored"
    c = candles[0]
    assert set(c) == {"time", "open", "high", "low", "close", "volume"}
    assert isinstance(c["time"], str) and "T" in c["time"]
    assert c["high"] >= c["low"]


def test_candles_are_returned_oldest_first():
    _download(FakeKite(), days=180)
    times = [c["time"] for c in kite_history.load("TESTCO", "5m")]
    assert times == sorted(times)


def test_re_fetching_the_same_candle_does_not_duplicate_it():
    """Windows are inclusive at their edges, so the same bar can arrive twice."""
    _download(FakeKite(), days=120)
    n = len(kite_history.load("TESTCO", "5m"))
    conn = sqlite3.connect(kite_history.DB_PATH)
    conn.execute("DELETE FROM fetched")     # force a full re-fetch
    conn.commit(); conn.close()
    kite_history._reset_connection()
    _download(FakeKite(), days=120)
    assert len(kite_history.load("TESTCO", "5m")) == n


def test_intervals_are_stored_separately():
    _download(FakeKite(), days=120, interval="5m")
    _download(FakeKite(), days=120, interval="15m")
    assert kite_history.load("TESTCO", "5m")
    assert kite_history.load("TESTCO", "15m")
    assert kite_history.available("5m") and kite_history.available("15m")
    assert not kite_history.available("1m")


def test_days_filter_trims_the_window_read_back():
    _download(FakeKite(), days=365)
    everything = kite_history.load("TESTCO", "5m")
    recent = kite_history.load("TESTCO", "5m", days=30)
    assert 0 < len(recent) < len(everything)


def test_load_batch_skips_symbols_that_are_not_cached():
    _download(FakeKite(), days=60)
    out = kite_history.load_batch(["TESTCO", "ABSENT"], "5m")
    assert set(out) == {"TESTCO"}


def test_available_is_false_before_anything_is_cached():
    assert kite_history.available("5m") is False
    assert kite_history.status("5m")["cached"] is False


def test_status_describes_what_is_cached():
    _download(FakeKite(), days=365)
    st = kite_history.status("5m")
    assert st["cached"] is True
    assert st["symbols"] == 1 and st["candles"] > 0 and st["sessions"] > 0
    assert st["from"] < st["to"]


# ---- rate limiting ------------------------------------------------------


def test_requests_are_paced():
    """Kite documents 3 requests/second on this endpoint; being throttled
    mid-pull costs far more than going slightly slower."""
    limiter = kite_history.RateLimiter(min_interval=0.05)
    started = time.time()
    for _ in range(4):
        limiter.wait()
    assert time.time() - started >= 0.15


def test_the_limiter_is_shared_across_threads():
    """Two callers must not between them exceed what one caller would."""
    limiter = kite_history.RateLimiter(min_interval=0.05)
    stamps = []
    lock = threading.Lock()

    def go():
        for _ in range(3):
            limiter.wait()
            with lock:
                stamps.append(time.time())

    threads = [threading.Thread(target=go) for _ in range(2)]
    for t in threads: t.start()
    for t in threads: t.join()
    stamps.sort()
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    assert all(g >= 0.04 for g in gaps), f"requests came too close together: {gaps}"


# ---- the backtester's source selection ----------------------------------


class Args:
    def __init__(self, source, interval="5m", days=55):
        self.source, self.interval, self.days = source, interval, days


def test_source_kite_refuses_to_run_on_an_empty_cache():
    """The failure that matters: a run meant to use two years must not
    silently answer a different question using 60 days of yfinance."""
    import backtester
    with pytest.raises(SystemExit) as exc:
        backtester._intraday_source(Args("kite"), ["TESTCO"])
    assert "cache is empty" in str(exc.value)
    assert "kite_history.py" in str(exc.value), "the error should say how to fix it"


def test_source_kite_uses_the_cache_when_it_is_there():
    import backtester
    _download(FakeKite(), days=365)
    out = backtester._intraday_source(Args("kite"), ["TESTCO"])
    assert set(out) == {"TESTCO"} and out["TESTCO"]


def test_auto_prefers_the_cache_over_yfinance(monkeypatch):
    import backtester
    import scanner
    _download(FakeKite(), days=365)
    monkeypatch.setattr(scanner, "download_batch",
                        lambda *a, **k: pytest.fail("yfinance must not be touched when the cache has data"))
    out = backtester._intraday_source(Args("auto"), ["TESTCO"])
    assert set(out) == {"TESTCO"}


def test_auto_falls_back_to_yfinance_on_an_empty_cache(monkeypatch):
    import backtester
    import scanner
    monkeypatch.setattr(scanner, "download_batch",
                        lambda tickers, period, interval: {"TESTCO.NS": [{"time": "2026-09-01T09:15:00"}]})
    out = backtester._intraday_source(Args("auto"), ["TESTCO"])
    assert set(out) == {"TESTCO"}


def test_source_yfinance_ignores_the_cache_even_when_filled(monkeypatch):
    import backtester
    import scanner
    _download(FakeKite(), days=365)
    called = []
    monkeypatch.setattr(scanner, "download_batch",
                        lambda tickers, period, interval: called.append(1) or {"TESTCO.NS": [{"time": "x"}]})
    backtester._intraday_source(Args("yfinance"), ["TESTCO"])
    assert called, "--source yfinance must not quietly read the Kite cache"
