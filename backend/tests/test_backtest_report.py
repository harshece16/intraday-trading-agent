"""#53, #48, #13: the backtester reports friction whole (slippage AND
charges), describes the sample it actually ran on, and fills entries at the
signal bar's own close (the convention every R-multiple rests on)."""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from costs import apply_slippage
from strategy_engine import STRATEGY_FUNCTIONS

import backtester

IST = ZoneInfo("Asia/Kolkata")
SLIP = {**config.COSTS, "slippage_pct": 0.05}


def _trade(**kw):
    t = {"symbol": "T", "exit_time": "2026-01-05T11:00:00+05:30", "entry_time": "2026-01-05T10:00:00+05:30",
         "side": "LONG", "qty": 10, "entry_price": 100.05, "exit_price": 101.95, "gross_pnl": 19.0,
         "cost": 3.0, "pnl": 16.0, "reason": "take_profit", "r": 1.0, "stop": 99.0, "target": 102.0,
         "risk_per_share": 1.05, "pre_slippage_pnl": 20.0, "slippage": 1.0}
    t.update(kw)
    return t


def test_close_position_records_pre_slippage_pnl_and_slippage():
    pos = backtester.Position() if hasattr(backtester, "Position") else None
    if pos is None:
        pos = backtester._Position()
    risk = backtester.RiskManager({**config.RISK, "total_capital": 100000})
    backtester._open_position(pos, "BUY", 100.0, 10, None, SLIP, risk, stop=99.0, target=102.0)
    trades = []
    backtester._close_position(pos, 102.0, risk, trades, "T", datetime(2026, 1, 5, 11, tzinfo=IST), "tp", SLIP)
    t = trades[0]
    entry, exit_ = apply_slippage("BUY", 100.0, SLIP), apply_slippage("SELL", 102.0, SLIP)
    assert abs(t["pre_slippage_pnl"] - 20.0) < 1e-9
    assert abs(t["gross_pnl"] - (exit_ - entry) * 10) < 1e-9
    assert abs(t["slippage"] - (20.0 - t["gross_pnl"])) < 1e-9 and t["slippage"] > 0
    assert pos.raw_entry is None                      # reset with the rest of the position


def test_report_shows_slippage_and_charges_separately(capsys):
    backtester.report([_trade(), _trade(exit_time="2026-01-06T11:00:00+05:30", entry_time="2026-01-06T10:00:00+05:30")],
                      [0, 16, 32], 100000, costs_enabled=True)
    out = capsys.readouterr().out
    assert "Pre-friction P&L:  40.00" in out
    assert "Slippage:          2.00" in out and "Charges:           6.00" in out
    assert "Total friction:    8.00" in out
    assert "after slippage, before charges" in out
    assert "before costs/slippage" not in out            # the old, wrong label


def test_small_sample_disclaimer_names_its_size_and_source(capsys):
    backtester.report([_trade()], [0, 16], 100000, costs_enabled=True, data_source="yfinance (delayed, ~60 days)")
    out = capsys.readouterr().out
    assert "1 trading session(s) from yfinance" in out and "small sample" in out


def test_large_kite_sample_is_not_called_a_small_yfinance_sample(capsys):
    # #48: 495 sessions of Kite cache used to print "a small, recent,
    # delayed-data sample from yfinance".
    trades = []
    d = datetime(2024, 9, 20, tzinfo=IST)
    for i in range(70):
        day = (d + timedelta(days=i)).date().isoformat()
        trades.append(_trade(entry_time=f"{day}T10:00:00+05:30", exit_time=f"{day}T11:00:00+05:30"))
    backtester.report(trades, [0] * 71, 100000, costs_enabled=True, data_source="the Kite 5-minute cache")
    out = capsys.readouterr().out
    assert "yfinance" not in out and "small" not in out
    assert "trades on 70 sessions from the Kite 5-minute cache" in out


def _candles(close_at_signal=100.0):
    out = []
    start = datetime(2026, 1, 5, 9, 15, tzinfo=IST)
    for i in range(70):
        t = start + timedelta(minutes=5 * i)
        c = close_at_signal + i * 0.1
        out.append({"time": t.isoformat(), "open": c - 0.05, "high": c + 0.5, "low": c - 0.5, "close": c,
                    "volume": 1000})
    return out


def test_entry_fills_at_the_signal_bars_own_close_13():
    """#13: run_backtest() fills an entry at the close of the bar the signal
    was computed on (window = candles[:i+1]), plus slippage, not at the next
    bar's open. Intentional, and every reported R-multiple depends on it, so
    it is pinned here rather than left implicit."""
    candles = _candles()
    fire_on = 40
    seen = {}
    name = "_test_same_bar_close"

    def fn(window, prev_state=None, **params):
        if len(window) - 1 == fire_on and not (prev_state or {}).get("fired"):
            seen["bar"] = window[-1]
            return "BUY", {"fired": True}
        return None, prev_state or {}
    STRATEGY_FUNCTIONS[name] = fn
    try:
        risk_cfg = {k: v for k, v in config.RISK.items() if k != "min_confidence_to_trade"}
        risk_cfg["total_capital"] = 100000
        trades, _ = backtester.run_backtest(["TEST"], name, {}, risk_cfg, "5m", 5, costs_cfg=SLIP,
                                            preloaded={"TEST": candles}, allowed_by_day=None, scorecard=[])
    finally:
        del STRATEGY_FUNCTIONS[name]
    assert trades, "the synthetic signal should produce a trade"
    assert seen["bar"] is candles[fire_on] or seen["bar"]["time"] == candles[fire_on]["time"]
    assert abs(trades[0]["entry_price"] - apply_slippage("BUY", candles[fire_on]["close"], SLIP)) < 1e-9
    assert trades[0]["entry_time"].startswith(candles[fire_on]["time"][:16])
