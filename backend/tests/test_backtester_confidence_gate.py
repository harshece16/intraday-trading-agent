"""
Regression tests for a real gap found while building a grid-search tool to
responsibly tune RISK["min_confidence_to_trade"]: backtester.run_backtest()
never applied confidence.score_trade() at all, so varying
min_confidence_to_trade had zero effect on backtest results — the
backtester and live trading_engine._try_enter() were silently testing two
different things. Fixed by applying the same gate live trading uses,
defaulting to the real current journal scorecard.

Uses a fake strategy registered directly in STRATEGY_FUNCTIONS (not the
real sahab_dimaag checklist) so the test doesn't need to engineer
realistic price action that clears a real candlestick pattern — it only
needs to prove the gate itself is wired in and respects
risk_cfg["min_confidence_to_trade"].
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from costs import ZERO_COSTS
from strategy_engine import STRATEGY_FUNCTIONS

import backtester

IST = ZoneInfo("Asia/Kolkata")


def _synthetic_candles():
    candles = []
    for day in range(3):
        start = datetime(2026, 1, 5 + day, 9, 15, tzinfo=IST)
        for i in range(60):  # 09:15 to 14:10, 5-min bars
            t = start + timedelta(minutes=5 * i)
            candles.append({
                "time": t.isoformat(), "open": 100.0, "high": 101.0, "low": 99.0,
                "close": 100.0, "volume": 1000,
            })
    return candles


def _register_fake_strategy(name, signal, state):
    def fake_signal_fn(candles, prev_state=None, **params):
        return (signal, state) if prev_state is None else (None, state)
    STRATEGY_FUNCTIONS[name] = fake_signal_fn
    return name


def _run(monkeypatch, score, min_conf):
    name = _register_fake_strategy(
        "_test_confidence_gate_strategy", "BUY",
        {"bull_score": 10, "bear_score": 0, "confirmations": [], "adx": 30},
    )
    try:
        monkeypatch.setattr(backtester.confidence, "score_trade",
                            lambda analysis, side, scorecard: {"score": score, "label": "test"})
        risk_cfg = {**config.RISK, "min_confidence_to_trade": min_conf, "total_capital": 100000}
        trades, _ = backtester.run_backtest(
            ["TEST"], name, {}, risk_cfg, "5m", 5,
            costs_cfg=ZERO_COSTS, preloaded={"TEST": _synthetic_candles()}, scorecard=[],
        )
        return trades
    finally:
        del STRATEGY_FUNCTIONS[name]


def test_low_confidence_score_blocks_every_entry(monkeypatch):
    trades = _run(monkeypatch, score=30, min_conf=60)
    assert trades == []


def test_high_confidence_score_allows_entry(monkeypatch):
    trades = _run(monkeypatch, score=90, min_conf=60)
    assert len(trades) >= 1


def test_min_confidence_none_skips_the_gate_entirely(monkeypatch):
    """risk_cfg with no min_confidence_to_trade key at all -> the gate is
    skipped (min_conf is None), not treated as 0 — matches
    trading_engine._try_enter()'s config.RISK.get(..., 60) default only
    applying when the key is genuinely absent."""
    name = _register_fake_strategy(
        "_test_confidence_gate_strategy2", "BUY",
        {"bull_score": 10, "bear_score": 0, "confirmations": [], "adx": 30},
    )
    try:
        monkeypatch.setattr(backtester.confidence, "score_trade",
                            lambda analysis, side, scorecard: (_ for _ in ()).throw(
                                AssertionError("score_trade should not be called when min_conf is None")))
        risk_cfg = {k: v for k, v in config.RISK.items() if k != "min_confidence_to_trade"}
        risk_cfg["total_capital"] = 100000
        trades, _ = backtester.run_backtest(
            ["TEST"], name, {}, risk_cfg, "5m", 5,
            costs_cfg=ZERO_COSTS, preloaded={"TEST": _synthetic_candles()}, scorecard=[],
        )
        assert len(trades) >= 1
    finally:
        del STRATEGY_FUNCTIONS[name]


def test_defaults_to_the_real_journal_scorecard_when_not_passed(monkeypatch):
    import database
    called_with = {}

    def fake_journal_summary():
        called_with["called"] = True
        return {"scorecard": [{"criterion": "x", "status": "pass", "detail": ""}]}
    monkeypatch.setattr(database, "journal_summary", fake_journal_summary)

    name = _register_fake_strategy(
        "_test_confidence_gate_strategy3", "BUY",
        {"bull_score": 10, "bear_score": 0, "confirmations": [], "adx": 30},
    )
    try:
        risk_cfg = {**config.RISK, "min_confidence_to_trade": 60, "total_capital": 100000}
        backtester.run_backtest(
            ["TEST"], name, {}, risk_cfg, "5m", 5,
            costs_cfg=ZERO_COSTS, preloaded={"TEST": _synthetic_candles()},
            # no `scorecard=` kwarg -> must fetch the real one
        )
        assert called_with.get("called") is True
    finally:
        del STRATEGY_FUNCTIONS[name]
