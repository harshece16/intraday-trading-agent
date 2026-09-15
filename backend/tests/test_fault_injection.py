"""
Fault-injection tests for the trading engine's real external dependencies —
Kite, NSE's data feed, and the batched candle fetch. This is a live-money
system; a network blip, an expired session, or a malformed API response
must degrade gracefully (skip that one thing, log it, keep ticking) rather
than crash the engine's background thread or corrupt state. Each test here
deliberately breaks one real dependency and asserts the specific graceful
behavior the surrounding code already claims to have, so a future change
can't silently regress it.

Distinct from test_entries_today_rollback.py, which covers risk/entry
*logic* bugs found auditing the live log — these cover *infrastructure*
failure modes: the bot's own strategy code is never wrong here, its
plumbing is.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from kiteconnect.exceptions import TokenException

import config
import data_provider
import nse_feed
import trading_engine
from state import AppState


def make_engine(watchlist=None):
    state = AppState(watchlist=watchlist or [], paper_mode=True)
    engine = trading_engine.TradingEngine(state)
    engine.scanner = None  # keep tick() focused on the per-symbol loop under test
    return engine, state


# ---- data_provider.get_candles_batch ---------------------------------------

def test_candles_batch_kite_and_yfinance_both_down_returns_empty_not_raise(monkeypatch):
    """Kite down AND yfinance down for every symbol — the real "internet is
    just broken this minute" case. get_candles_batch() must return an empty
    map, not propagate, so the tick loop can fall back per-symbol instead of
    losing the whole cycle.

    Writing this test first caught a real gap: the per-symbol Kite fetch
    was defended (each future's exception caught individually) but the
    batched yfinance *fallback* call wasn't — it raised straight out of
    get_candles_batch(), silently relying on _tick_impl()'s own try/except
    to mask it rather than the function honoring its own documented
    contract. Fixed in data_provider.py (_safe_yfinance_batch)."""
    monkeypatch.setattr(config, "USE_KITE_DATA", True)
    monkeypatch.setattr(config, "KITE_API_KEY", "dummy")
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "dummy")

    def boom_kite(symbol, interval, period):
        raise RuntimeError("Kite historical API unreachable")
    monkeypatch.setattr(data_provider, "_get_intraday_candles_kite", boom_kite)

    def boom_yf(symbols, interval, period):
        raise RuntimeError("yfinance unreachable")
    monkeypatch.setattr(data_provider, "_get_intraday_candles_yfinance_batch", boom_yf)

    out = data_provider.get_candles_batch(["RELIANCE", "TCS"], interval="5m", period="5d")

    assert out == {}


def test_candles_batch_kite_down_falls_back_to_yfinance_cleanly(monkeypatch):
    """The realistic partial-outage case: Kite's historical endpoint is down
    (or rate-limited) but yfinance still works. Every symbol should still
    come back with data, routed through the batched yfinance fallback."""
    monkeypatch.setattr(config, "USE_KITE_DATA", True)
    monkeypatch.setattr(config, "KITE_API_KEY", "dummy")
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "dummy")

    def boom_kite(symbol, interval, period):
        raise RuntimeError("Too many requests")
    monkeypatch.setattr(data_provider, "_get_intraday_candles_kite", boom_kite)

    calls = []
    def fake_yf_batch(symbols, interval, period):
        calls.append(list(symbols))
        return {s: [{"time": "2026-09-15T10:00:00", "open": 1, "high": 1, "low": 1,
                     "close": 1, "volume": 100}] for s in symbols}
    monkeypatch.setattr(data_provider, "_get_intraday_candles_yfinance_batch", fake_yf_batch)

    out = data_provider.get_candles_batch(["RELIANCE", "TCS", "INFY"], interval="5m", period="5d")

    assert set(out.keys()) == {"RELIANCE", "TCS", "INFY"}
    assert calls and set(calls[0]) == {"RELIANCE", "TCS", "INFY"}


# ---- tick()'s open-market loop ---------------------------------------------

def test_tick_survives_batch_fetch_exception_and_falls_back_per_symbol(monkeypatch):
    """get_candles_batch() itself raising (not just returning {}) must not
    kill the tick — _tick_impl() wraps that call specifically so each
    symbol still gets a chance via _process_symbol()'s own single-fetch
    fallback (candles=None)."""
    engine, state = make_engine(watchlist=["AAA", "BBB"])
    monkeypatch.setattr(trading_engine, "market_phase", lambda now: "open")

    def boom_batch(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(data_provider, "get_candles_batch", boom_batch)

    seen = []
    def fake_process_symbol(self, symbol, candles=None):
        seen.append((symbol, candles))
    monkeypatch.setattr(trading_engine.TradingEngine, "_process_symbol", fake_process_symbol)

    engine._tick_impl()  # must not raise

    assert seen == [("AAA", None), ("BBB", None)]


def test_tick_isolates_one_bad_symbol_from_the_rest(monkeypatch):
    """A single symbol's processing blowing up (bad data, a strategy bug,
    anything) must not stop the other 24 symbols on a real 25-wide
    watchlist from being processed the same cycle."""
    engine, state = make_engine(watchlist=["GOOD1", "BAD", "GOOD2"])
    monkeypatch.setattr(trading_engine, "market_phase", lambda now: "open")
    monkeypatch.setattr(data_provider, "get_candles_batch", lambda *a, **k: {})

    processed = []
    def fake_process_symbol(self, symbol, candles=None):
        if symbol == "BAD":
            raise RuntimeError("boom")
        processed.append(symbol)
    monkeypatch.setattr(trading_engine.TradingEngine, "_process_symbol", fake_process_symbol)

    engine._tick_impl()  # must not raise

    assert processed == ["GOOD1", "GOOD2"]
    assert state.last_error is not None and "BAD" in state.last_error


# ---- _sync_capital / Kite session health -----------------------------------

def test_sync_capital_survives_expired_kite_session(monkeypatch):
    """The daily-expiry case: Kite's access token has lapsed. Must log a
    clear alert and return quietly — not crash the tick, not corrupt
    state.real_capital or config.RISK['total_capital']."""
    engine, state = make_engine()
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "dummy")
    config.RISK["sync_capital_with_kite"] = True
    config.RISK["total_capital"] = 12345.0

    class FakeKite:
        def get_margins(self):
            raise TokenException("session expired")
    engine.kite_executor = FakeKite()

    engine._sync_capital()  # must not raise

    assert config.RISK["total_capital"] == 12345.0  # untouched, not corrupted
    assert any(e["level"] == "error" and "expired" in e["message"] for e in state.activity)


def test_sync_capital_survives_generic_kite_network_failure(monkeypatch):
    """A transient network/HTTP failure (not a token expiry) hitting
    margins() must be swallowed the same way — logged, not raised."""
    engine, state = make_engine()
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "dummy")
    config.RISK["sync_capital_with_kite"] = True
    config.RISK["total_capital"] = 999.0

    class FakeKite:
        def get_margins(self):
            raise requests.exceptions.ConnectionError("connection reset")
    engine.kite_executor = FakeKite()

    engine._sync_capital()  # must not raise

    assert config.RISK["total_capital"] == 999.0


def test_position_reconciliation_survives_kite_positions_failure(monkeypatch):
    """Kite's positions() call failing mid-check must leave
    _untracked_kite_positions exactly as it was, not wipe it (which would
    silently re-open the double-entry risk §19/§24 exist to close)."""
    engine, state = make_engine()
    engine._untracked_kite_positions = {"RELIANCE"}

    class FakeKite:
        def get_positions(self):
            raise RuntimeError("Kite API 500")
    engine.kite_executor = FakeKite()

    engine._check_position_reconciliation()  # must not raise

    assert engine._untracked_kite_positions == {"RELIANCE"}


# ---- nse_feed graceful degradation -----------------------------------------

def test_fii_dii_flows_survives_nse_timeout(monkeypatch):
    nse_feed._cache.clear()

    def boom(*a, **k):
        raise requests.exceptions.Timeout("NSE took too long")
    monkeypatch.setattr(nse_feed._session["s"] or requests, "get", boom, raising=False)
    monkeypatch.setattr(requests.Session, "get", boom)

    result = nse_feed.fii_dii_flows()  # must not raise

    assert result is None


def test_large_deals_today_survives_nse_timeout(monkeypatch):
    nse_feed._cache.clear()

    def boom(*a, **k):
        raise requests.exceptions.Timeout("NSE took too long")
    monkeypatch.setattr(requests.Session, "get", boom)

    result = nse_feed.large_deals_today()  # must not raise

    assert result == {}
