"""The search harness's own correctness, checked before it runs: the series
indicators equal indicators.py's per-window values, nothing reads a later
bar, aggregated bars are end-labelled and end at 15:10, and a 15-minute
backtest never carries a position overnight."""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import indicators
from research import strategy_search as ss


def _bars5(days=("2025-03-03", "2025-03-04", "2025-03-05"), seed=7):
    rnd, out, px = random.Random(seed), [], 500.0
    for d in days:
        t = datetime.fromisoformat(f"{d}T09:15:00")
        while t.strftime("%H:%M") <= "15:25":
            o = px
            px = max(10.0, px * (1 + rnd.gauss(0, 0.002)))
            hi, lo = max(o, px) * (1 + abs(rnd.gauss(0, 0.001))), min(o, px) * (1 - abs(rnd.gauss(0, 0.001)))
            out.append({"time": t.isoformat(), "open": o, "high": hi, "low": lo, "close": px,
                        "volume": rnd.randint(500, 5000)})
            t += timedelta(minutes=5)
    return out


def test_series_match_indicators_py_at_every_checked_bar():
    c = _bars5()
    closes = [b["close"] for b in c]
    rsi, adx, vwap, atr = ss.rsi_series(closes), ss.adx_series(c), ss.vwap_series(c), ss.atr_series(c)
    for i in range(30, len(c), 7):
        w = c[: i + 1]
        assert abs(rsi[i] - indicators.rsi(closes[: i + 1])) < 1e-9
        assert abs(adx[i] - indicators.adx(w)["adx"]) < 1e-9
        assert abs(vwap[i] - indicators.session_vwap(w)) < 1e-9
        assert abs(atr[i] - indicators.atr(w)) < 1e-9


def test_features_have_no_lookahead():
    c = _bars5()
    full = ss.features(c)
    k = 120
    part = ss.features(c[:k])
    for name in full:
        for i in range(k):
            a, b = full[name][i], part[name][i]
            assert (a is None and b is None) or abs(a - b) < 1e-9, (name, i)


def test_aggregated_bars_are_end_labelled_and_each_session_ends_at_1510():
    c = ss.aggregate(_bars5(), 15)
    by_day = {}
    for b in c:
        by_day.setdefault(b["time"][:10], []).append(b["time"][11:16])
    for times in by_day.values():
        assert times[0] == "09:30" and times[-1] == "15:10"
        assert "15:15" not in times and "15:25" not in times
    h = ss.aggregate(_bars5(), 60)
    assert [b["time"][11:16] for b in h if b["time"].startswith("2025-03-03")] == \
        ["10:15", "11:15", "12:15", "13:15", "14:15", "15:10"]


def test_aggregation_preserves_ohlcv():
    b5 = [b for b in _bars5() if b["time"].startswith("2025-03-03") and "09:15" <= b["time"][11:16] < "09:30"]
    first = ss.aggregate(_bars5(), 15)[0]
    assert first["open"] == b5[0]["open"] and first["close"] == b5[-1]["close"]
    assert first["high"] == max(b["high"] for b in b5) and first["low"] == min(b["low"] for b in b5)
    assert first["volume"] == sum(b["volume"] for b in b5)


def test_a_15_minute_backtest_never_holds_overnight():
    """The bug the end labels exist to prevent: every position opened on a
    day is closed the same day, by 15:10."""
    candles = {"TEST": ss.aggregate(_bars5(days=tuple(f"2025-03-{d:02d}" for d in (3, 4, 5, 6, 7, 10))), 15)}
    by_tf = {15: candles}
    feats = {15: {id(c[0]): ss.features(c) for c in candles.values()}}
    cfg = {"id": "t", "kind": "family", "family": "PB", "tf": 15, "stop": 3.0, "exit": "hold", "side": "both"}
    trades = ss.run_config(cfg, by_tf, feats)
    for t in trades:
        assert t["entry_time"][:10] == t["exit_time"][:10], t
        assert t["exit_time"][11:16] <= "15:10"


def test_the_grid_has_76_configurations_with_unique_ids():
    g = ss.grid()
    assert len(g) == 76 and len({c["id"] for c in g}) == 76


def test_selection_pass_rule_needs_all_four_clauses():
    good = {"net_r": 0.2, "t": 3.0, "n": 150}
    half = {"net_r": 0.1}
    assert ss.passes(half, half, good, {"dsr": 0.97})
    assert not ss.passes(half, half, good, {"dsr": 0.94})                      # DSR
    assert not ss.passes(half, {"net_r": -0.01}, good, {"dsr": 0.97})          # a half
    assert not ss.passes(half, half, {**good, "t": 1.9}, {"dsr": 0.97})        # t
    assert not ss.passes(half, half, {**good, "n": 99}, {"dsr": 0.97})         # count


def test_diagnostic_excursions_in_r_use_only_the_bars_the_trade_was_open():
    from research import search_diagnostics as sd
    t = {"side": "LONG", "entry_price": 100.0, "risk_per_share": 1.0,
         "entry_time": "2025-03-03T10:00:00+05:30", "exit_time": "2025-03-03T10:15:00+05:30"}
    bars = [{"time": "2025-03-03T10:00:00", "high": 150.0, "low": 50.0},      # entry bar: excluded
            {"time": "2025-03-03T10:05:00", "high": 102.5, "low": 99.5},
            {"time": "2025-03-03T10:10:00", "high": 101.0, "low": 98.8},
            {"time": "2025-03-03T10:20:00", "high": 130.0, "low": 90.0}]      # after exit: excluded
    mfe, mae = sd.excursions(t, bars)
    assert mfe == 2.5 and abs(mae - (-1.2)) < 1e-9
    short = {**t, "side": "SHORT"}
    mfe, mae = sd.excursions(short, bars)
    assert abs(mfe - 1.2) < 1e-9 and mae == -2.5
