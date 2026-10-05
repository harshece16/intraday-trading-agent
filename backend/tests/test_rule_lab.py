"""The single-rule paper lab (rule_lab.py, README section 124, prereg-rule-lab.md):
each rule's signal on hand-built bars, the virtual book's entry, exit and cost
arithmetic, isolation from the engine, the leaderboard's statistics, the
journal migration, and the historical search's parity with the forward lab."""
import json
import math
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "research"))

import candlestick_patterns  # noqa: E402
import config  # noqa: E402
import data_provider  # noqa: E402
import database  # noqa: E402
import indicators  # noqa: E402
import rule_lab  # noqa: E402
import trading_engine  # noqa: E402
from state import AppState  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
DAY = "2026-10-05"
PREV = "2026-10-01"
PREV2 = "2026-09-30"


def bars(day, specs, start="09:15"):
    """[(open, high, low, close, volume), ...] as 5-minute bars from `start` on `day`."""
    t0 = datetime.fromisoformat(f"{day}T{start}:00+05:30")
    return [{"time": (t0 + timedelta(minutes=5 * i)).isoformat(), "open": o, "high": h, "low": low,
             "close": c, "volume": v} for i, (o, h, low, c, v) in enumerate(specs)]


def flat(day, n=75, price=100.0, vol=1000, start="09:15"):
    return bars(day, [(price, price + 0.2, price - 0.2, price, vol)] * n, start=start)


def history():
    return flat(PREV2) + flat(PREV)


def fires(candles, day=DAY):
    ctx = rule_lab.session_context(candles, day)
    return {pos: set(rule_lab.signals_at(ctx, pos)) for pos in range(len(ctx["today"]))}


def where(candles, rid, day=DAY):
    return [p for p, s in fires(candles, day).items() if rid in s]


# ---- the registry -------------------------------------------------------------

COHORT1 = [f"R{i:02d}" for i in range(1, 21)]


def test_twenty_rules_registered_once_with_fixed_sides():
    assert rule_lab.RULE_IDS[:20] == COHORT1
    longs = [r for r in COHORT1 if rule_lab.RULE_SIDE[r] == "LONG"]
    assert len(longs) == 10
    assert rule_lab.R_RULES[:2] == ["R19", "R20"]
    assert all(rule_lab.REGISTRY[r]["cohort"] == 1 for r in COHORT1)


def test_cohort_two_is_the_catalogs_conditions():
    two = [r for r in rule_lab.RULE_IDS if rule_lab.REGISTRY[r]["cohort"] == 2]
    assert len(two) == 87 and len(rule_lab.RULE_IDS) == 157 and len(rule_lab.l55_conditions()) == 107
    assert all(rule_lab.REGISTRY[r].get("sources") for r in two)
    assert all(rule_lab.REGISTRY[r]["exit"] == "fixed" for r in two)
    with pytest.raises(ValueError):
        rule_lab.register("R01", "dup", "LONG", "x", lambda c, p, k: False)


def test_cohort_alpha_spends_five_percent_over_every_cohort():
    assert rule_lab.cohort_alpha(1) == pytest.approx(0.025)
    assert rule_lab.cohort_alpha(2) == pytest.approx(0.0125)
    assert sum(rule_lab.cohort_alpha(k) for k in range(1, 60)) <= 0.05 + 1e-12


# ---- each rule's signal ---------------------------------------------------------

def test_inside_bar_breakout_and_breakdown():
    up = history() + bars(DAY, [(100, 105, 95, 101, 1000), (101, 104, 96, 102, 1000), (102, 104.6, 101, 104.5, 1000)])
    assert where(up, "R07") == [2] and where(up, "R08") == []
    down = history() + bars(DAY, [(100, 105, 95, 101, 1000), (101, 104, 96, 100, 1000), (100, 100.5, 95, 95.5, 1000)])
    assert where(down, "R08") == [2] and where(down, "R07") == []
    not_inside = history() + bars(DAY, [(100, 105, 95, 101, 1000), (101, 106, 96, 102, 1000), (102, 107, 101, 106.5, 1000)])
    assert where(not_inside, "R07") == []


def test_volume_spike_needs_twice_the_time_of_day_average_over_two_sessions():
    today = bars(DAY, [(100, 101, 99.5, 100.8, 2100), (100.8, 101, 100, 100.2, 2500), (100, 100.3, 99, 99.2, 1900)])
    c = history() + today
    assert where(c, "R09") == [0]          # up bar, 2.1x
    assert where(c, "R10") == [1]          # down bar, 2.5x; bar 2 is 1.9x
    one_session = flat(PREV) + today       # fewer than 2 earlier sessions: undefined, silent
    assert where(one_session, "R09") == [] and where(one_session, "R10") == []


def test_opening_range_breakout_fires_on_the_first_close_beyond_only():
    today = bars(DAY, [(100, 101, 99, 100, 1000), (100, 100.8, 99.5, 100.2, 1000), (100.2, 100.9, 99.8, 100.5, 1000),
                       (100.5, 100.9, 100.1, 100.6, 1000), (100.6, 101.6, 100.5, 101.5, 1000),
                       (101.5, 102.2, 101.2, 102, 1000), (102, 102, 98.5, 98.8, 1000)])
    c = history() + today
    assert where(c, "R13") == [4]
    assert where(c, "R14") == [6]


@pytest.mark.parametrize("open_, close, expect", [
    (101, 101.5, {"R15"}), (101, 100.5, {"R17"}), (99, 98.5, {"R16"}), (99, 99.5, {"R18"}),
    (100.3, 100.8, set()),            # gap 0.3%, under 0.5%
    (112, 113, set()),                # gap 12%, treated as a data or corporate-action event
])
def test_gap_rules(open_, close, expect):
    c = history() + bars(DAY, [(open_, max(open_, close) + 0.1, min(open_, close) - 0.1, close, 1000),
                               (close, close, close, close, 1000)])
    gap_rules = {"R15", "R16", "R17", "R18"}
    assert fires(c)[0] & gap_rules == expect
    assert not (fires(c)[1] & gap_rules)


def _u(c_list, k, vwap, ema, up=True):
    c = c_list[k]["close"]
    if up:
        return c > vwap and c > ema[k] and ema[k] > ema[k - 3]
    return c < vwap and c < ema[k] and ema[k] < ema[k - 3]


@pytest.mark.parametrize("up", [True, False])
def test_trend_turn_matches_an_independent_reading(up):
    rnd = random.Random(7)
    p = 100.0
    spec = []
    for i in range(75):
        drift = (0.15 if up else -0.15) if i > 20 else (-0.1 if up else 0.1)
        o = p
        p = p + drift + rnd.uniform(-0.1, 0.1)
        spec.append((o, max(o, p) + 0.05, min(o, p) - 0.05, p, 1000 + rnd.randint(0, 300)))
    c = history() + bars(DAY, spec)
    rid = "R11" if up else "R12"
    closes = [b["close"] for b in c]
    ema = indicators.ema_series(closes, 20)
    first = len(history())
    expected = []
    for pos in range(1, 75):
        k = first + pos
        v_now = indicators.session_vwap(c[first:k + 1])
        v_before = indicators.session_vwap(c[first:k])
        if _u(c, k, v_now, ema, up) and not _u(c, k - 1, v_before, ema, up):
            expected.append(pos)
    assert expected, "the series should turn at least once"
    assert where(c, rid) == expected


def test_pattern_rules_are_the_engines_detector():
    rnd = random.Random(11)
    p = 100.0
    spec = []
    for i in range(150):
        o = p + rnd.uniform(-0.3, 0.3)
        p = o + rnd.uniform(-1.2, 1.2)
        hi = max(o, p) + abs(rnd.gauss(0, 0.5))
        lo = min(o, p) - abs(rnd.gauss(0, 0.5))
        spec.append((o, hi, lo, p, 1000))
    c = flat(PREV2) + bars(PREV, spec[:75]) + bars(DAY, spec[75:])
    names = {"R01": "Bullish Engulfing", "R02": "Bearish Engulfing", "R03": "Hammer", "R04": "Shooting Star",
             "R05": "Bullish Marubozu", "R06": "Bearish Marubozu"}
    first = 150
    seen = set()
    for pos, fired in fires(c).items():
        k = first + pos
        window = c[max(0, k - 29):k + 1]
        found = {x["name"] for x in candlestick_patterns.detect_patterns(window, indicators.atr(window, 14))}
        for rid, name in names.items():
            assert (rid in fired) == (name in found), (rid, pos)
            if name in found:
                seen.add(rid)
    assert {"R01", "R02"} <= seen


def test_bullish_engulfing_by_hand():
    pre = bars(DAY, [(100, 100.3, 99.7, 100, 1000)] * 14)
    spec = [(100.5, 100.6, 99.4, 99.5, 1000), (99.4, 101.2, 99.3, 101.0, 1500)]
    c = history() + pre + bars(DAY, spec, start="10:25")
    assert 15 in where(c, "R01")


def _rising(n=75, start=100.0, step=0.1):
    return [(start + step * i, start + step * i + 0.08, start + step * i - 0.02, start + step * (i + 1) - 0.02, 1000)
            for i in range(n)]


def test_pullback_to_a_rising_ema20():
    prev = bars(PREV, _rising(75, 95.0, 0.05))
    today = bars(DAY, _rising(10, prev[-1]["close"], 0.05))
    c = flat(PREV2, price=95) + prev + today
    closes = [b["close"] for b in c]
    ema = indicators.ema_series(closes + [closes[-1]], 20)
    e_next = ema[-1]
    # the next bar dips to the average and closes back above it
    o = c[-1]["close"]
    c.append({"time": (datetime.fromisoformat(c[-1]["time"]) + timedelta(minutes=5)).isoformat(),
              "open": o, "high": o + 0.05, "low": e_next - 0.3, "close": o, "volume": 1000})
    # recompute the EMA with this bar's real close (= o) and confirm the touch
    k = len(c) - 1
    ema2 = indicators.ema_series([b["close"] for b in c], 20)
    assert c[k]["low"] <= ema2[k] < c[k]["close"]
    assert 10 in where(c, "R19")
    assert 10 not in where(c, "R20")


def test_spec_signal_matches_a_coded_rule():
    spec = {"all": [["rvol", ">=", 2], ["close", ">", "open"]]}
    sig = rule_lab.spec_signal(spec)
    today = bars(DAY, [(100, 101, 99.5, 100.8, 2100), (100.8, 101, 100, 100.2, 2500), (100, 100.9, 99, 100.7, 900)])
    c = history() + today
    ctx = rule_lab.session_context(c, DAY)
    assert [p for p in range(3) if sig(ctx, p, {})] == where(c, "R09") == [0]
    with pytest.raises(ValueError):
        rule_lab.spec_signal({"all": [["close", "!!", "open"]]})


# ---- the virtual book ------------------------------------------------------------

def _hand_net(side, e, x, qty):
    """Zerodha MIS by hand, independent of costs.py: config.COSTS's rates."""
    slip = 0.0003
    buy_px, sell_px = (e * (1 + slip), x * (1 - slip)) if side == "LONG" else (x * (1 + slip), e * (1 - slip))

    def leg(px, is_buy):
        t = px * qty
        brok = min(20.0, t * 0.0003)
        stt = 0 if is_buy else t * 0.00025
        exch = t * 0.0000307
        sebi = t * 0.000001
        ipft = t * 0.000000001
        stamp = t * 0.00003 if is_buy else 0
        gst = (brok + exch + sebi + ipft) * 0.18
        return brok + stt + exch + sebi + ipft + stamp + gst
    return (sell_px - buy_px) * qty - leg(buy_px, True) - leg(sell_px, False)


def test_entry_next_open_exit_after_30_minutes_and_costs():
    # gap and go at 09:15 -> enter at the 09:20 open, exit at the 09:50 open
    spec = [(101, 101.6, 100.9, 101.5, 1000)] + [(101.5 + 0.1 * i, 101.7 + 0.1 * i, 101.4 + 0.1 * i, 101.6 + 0.1 * i, 1000)
                                                for i in range(1, 12)]
    c = history() + bars(DAY, spec)
    trades = [t for t in rule_lab.simulate_session(c, DAY) if t["rule"] == "R15"]
    assert len(trades) == 1
    t = trades[0]
    assert t["entry_time"].endswith("09:20:00+05:30") and t["entry_price"] == pytest.approx(101.6)
    assert t["exit_time"].endswith("09:50:00+05:30") and t["exit_price"] == pytest.approx(102.2)
    assert t["qty"] == int(50000 // 101.6)
    net = _hand_net("LONG", 101.6, 102.2, t["qty"])
    assert t["net_rs"] == pytest.approx(net, rel=1e-9)
    assert t["net_bp"] == pytest.approx(net / (101.6 * t["qty"]) * 1e4)
    assert t["gross_bp"] == pytest.approx((102.2 / 101.6 - 1) * 1e4)
    # the round trip at this size is the project's 16.6 bp hurdle
    assert t["gross_bp"] - t["net_bp"] == pytest.approx(16.6, abs=0.3)


def test_short_arithmetic():
    spec = [(99, 99.1, 98.4, 98.5, 1000)] + [(98.5 - 0.1 * i, 98.6 - 0.1 * i, 98.3 - 0.1 * i, 98.4 - 0.1 * i, 1000)
                                            for i in range(1, 12)]
    c = history() + bars(DAY, spec)
    t = [t for t in rule_lab.simulate_session(c, DAY) if t["rule"] == "R16"][0]
    assert t["side"] == "SHORT" and t["entry_price"] == pytest.approx(98.4)
    assert t["exit_price"] == pytest.approx(97.8)
    assert t["net_rs"] == pytest.approx(_hand_net("SHORT", 98.4, 97.8, t["qty"]), rel=1e-9)


def _session_with_signal_at(hhmm, n=75, rule_bar=None):
    """A flat session with an inside-bar breakout ending at `hhmm`."""
    c = history() + flat(DAY, n)
    t0 = datetime.fromisoformat(f"{DAY}T09:15:00+05:30")
    k = len(history()) + int((datetime.fromisoformat(f"{DAY}T{hhmm}:00+05:30") - t0).total_seconds() // 300)
    c[k - 2].update(open=100, high=101, low=99, close=100)
    c[k - 1].update(open=100, high=100.5, low=99.5, close=100.2)
    c[k].update(open=100.2, high=100.9, low=100.1, close=100.8)
    return c


def test_last_entry_at_14_30():
    t = [t for t in rule_lab.simulate_session(_session_with_signal_at("14:25"), DAY) if t["rule"] == "R07"]
    assert len(t) == 1 and t[0]["entry_time"].endswith("14:30:00+05:30")
    # the last entry's 30 minutes end at 15:00, before the 15:05 square-off bar
    assert t[0]["exit_time"].endswith("15:00:00+05:30") and t[0]["exit_reason"] == "horizon"
    late = [t for t in rule_lab.simulate_session(_session_with_signal_at("14:30"), DAY) if t["rule"] == "R07"]
    assert late == []                      # its entry bar would start at 14:35


def test_one_open_trade_per_rule_per_stock():
    c = history() + bars(DAY, [(100, 101, 99, 100, 1000)] * 75)
    for k in range(len(history()), len(c)):
        c[k].update(volume=3000, close=100.5, high=101)       # an up bar on 3x volume, every bar
    t = [t for t in rule_lab.simulate_session(c, DAY) if t["rule"] == "R09"]
    entries = [x["entry_time"][11:16] for x in t]
    assert entries[:3] == ["09:20", "09:50", "10:20"]       # re-entry at the open where the last one exits
    for a, b in zip(t, t[1:]):
        assert b["entry_time"] >= a["exit_time"]


def test_tradability_guards_skip_shorts():
    spec = [(99, 99.1, 98.4, 98.5, 1000)] + [(98.5, 98.6, 98.3, 98.4, 1000)] * 11
    c = history() + bars(DAY, spec)
    assert any(t["rule"] == "R16" for t in rule_lab.simulate_session(c, DAY))
    assert not any(rule_lab.RULE_SIDE[t["rule"]] == "SHORT" for t in rule_lab.simulate_session(c, DAY, long_only=True))
    assert not any(rule_lab.RULE_SIDE[t["rule"]] == "SHORT" for t in rule_lab.simulate_session(c, DAY, allow_shorts=False))


def test_open_until_the_exit_bar_arrives_then_closed():
    spec = [(101, 101.6, 100.9, 101.5, 1000)] + [(101.6, 101.7, 101.5, 101.6, 1000)] * 4
    c = history() + bars(DAY, spec)
    t = [t for t in rule_lab.simulate_session(c, DAY) if t["rule"] == "R15"][0]
    assert t["status"] == "open" and "exit_price" not in t
    c2 = history() + bars(DAY, spec + [(101.6, 101.7, 101.5, 101.6, 1000)] * 4)
    t2 = [t for t in rule_lab.simulate_session(c2, DAY) if t["rule"] == "R15"][0]
    assert t2["status"] == "closed"


def test_forming_bar_gives_only_its_open():
    spec = [(101, 101.6, 100.9, 101.5, 1000)] + [(101.6, 101.7, 101.5, 101.6, 1000)] * 6
    c = history() + bars(DAY, spec)
    # the newest bar (09:45) is still forming: decisions ignore it, the 09:50 exit hasn't started
    n_closed = len(c) - 1
    t = [t for t in rule_lab.simulate_session(c, DAY, n_closed=n_closed) if t["rule"] == "R15"][0]
    assert t["status"] == "open"
    c.append({**c[-1], "time": f"{DAY}T09:50:00+05:30", "open": 102.0})
    t = [t for t in rule_lab.simulate_session(c, DAY, n_closed=len(c) - 1) if t["rule"] == "R15"][0]
    assert t["status"] == "closed" and t["exit_price"] == 102.0


def _pullback_session(after):
    """R19 fires on today's bar 10; `after` are the bars after it as (o, h, l, c)."""
    prev = bars(PREV, _rising(75, 95.0, 0.05))
    today = bars(DAY, _rising(10, prev[-1]["close"], 0.05))
    c = flat(PREV2, price=95) + prev + today
    closes = [b["close"] for b in c]
    o = c[-1]["close"]
    ema_guess = indicators.ema_series(closes + [o], 20)[-1]
    sig = {"time": (datetime.fromisoformat(c[-1]["time"]) + timedelta(minutes=5)).isoformat(),
           "open": o, "high": o + 0.05, "low": ema_guess - 0.3, "close": o, "volume": 1000}
    c.append(sig)
    t = datetime.fromisoformat(sig["time"])
    for i, (oo, h, lo, cc) in enumerate(after):
        c.append({"time": (t + timedelta(minutes=5 * (i + 1))).isoformat(), "open": oo, "high": h, "low": lo,
                  "close": cc, "volume": 1000})
    return c, sig


def _r19(c):
    return [t for t in rule_lab.simulate_session(c, DAY) if t["rule"] == "R19"]


def test_r3_exit_target_stop_and_both_in_one_bar():
    c, sig = _pullback_session([])
    e = sig["close"] + 0.01
    stop = sig["low"]
    r = e - stop
    target = e + 3 * r
    c, sig = _pullback_session([(e, e + 0.1, e - 0.05, e + 0.05), (e + 0.05, target + 0.2, e, target)])
    t = _r19(c)[0]
    assert t["exit_reason"] == "target" and t["exit_price"] == pytest.approx(target)
    assert t["net_r"] == pytest.approx(t["net_rs"] / (r * t["qty"]))
    assert 2.0 < t["net_r"] < 3.0           # 3R before costs, less after
    c, sig = _pullback_session([(e, e + 0.1, stop - 0.01, e)])
    t = _r19(c)[0]
    assert t["exit_reason"] == "stop" and t["exit_price"] == pytest.approx(stop) and t["net_r"] < -1
    c, sig = _pullback_session([(e, target + 1, stop - 1, e)])
    assert _r19(c)[0]["exit_reason"] == "stop"            # one bar reaches both: the stop is taken
    c, sig = _pullback_session([(e, e + 0.1, e - 0.1, e), (stop - 0.5, stop, stop - 0.8, stop - 0.6)])
    t = _r19(c)[0]
    assert t["exit_reason"] == "stop" and t["exit_price"] == pytest.approx(stop - 0.5)   # gapped past: the open


def test_r3_square_off_at_the_1505_open():
    c, sig = _pullback_session([])
    e = sig["close"] + 0.01
    start = datetime.fromisoformat(sig["time"])
    n = int((datetime.fromisoformat(f"{DAY}T15:25:00+05:30") - start).total_seconds() // 300)
    c, sig = _pullback_session([(e, e + 0.02, e - 0.02, e)] * n)
    t = _r19(c)[0]
    assert t["exit_reason"] == "square_off" and t["exit_time"].endswith("15:05:00+05:30")


def test_r3_skips_a_stop_inside_the_cost():
    c, sig = _pullback_session([])
    # make the signal bar's low sit 5 bp under the entry: below the 16.6 bp floor
    e = sig["close"]
    c[-1]["low"] = min(c[-1]["low"], e * (1 - 0.0005))
    c.append({**c[-1], "time": (datetime.fromisoformat(c[-1]["time"]) + timedelta(minutes=5)).isoformat(),
              "open": e, "high": e, "low": e, "close": e})
    for t in _r19(c):
        assert (t["entry_price"] - t["stop_price"]) / t["entry_price"] * 100 >= 0.166


# ---- the journal -----------------------------------------------------------------

def test_record_inserts_once_closes_once_and_never_rewrites_a_closed_row():
    spec = [(101, 101.6, 100.9, 101.5, 1000)] + [(101.6, 101.7, 101.5, 101.6, 1000)] * 4
    t_open = [t for t in rule_lab.simulate_session(history() + bars(DAY, spec), DAY) if t["rule"] == "R15"]
    assert rule_lab.record("AAA", t_open, "kite") == (1, 0)
    assert rule_lab.record("AAA", t_open, "kite") == (0, 0)
    c2 = history() + bars(DAY, spec + [(102.0, 102.1, 101.9, 102.0, 1000)] * 4)
    t_closed = [t for t in rule_lab.simulate_session(c2, DAY) if t["rule"] == "R15"]
    assert rule_lab.record("AAA", t_closed, "kite") == (0, 1)
    tampered = [{**t_closed[0], "exit_price": 999.0, "net_bp": 999.0}]
    assert rule_lab.record("AAA", tampered, "kite") == (0, 0)
    row = database._conn().execute("SELECT * FROM rule_lab_trades").fetchone()
    assert row["status"] == "closed" and row["exit_price"] == pytest.approx(102.0)


def test_migration_adds_the_tables_to_an_old_journal(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    old_schema = database.SCHEMA[:database.SCHEMA.index("CREATE TABLE IF NOT EXISTS rule_lab_trades")]
    assert "rule_lab" not in old_schema
    conn = sqlite3.connect(path)
    conn.executescript(old_schema)
    conn.execute("INSERT INTO activity (ts, kind, message) VALUES (1, 'system', 'before')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(database, "DB_PATH", path)
    database._local.conn = None
    c = database._conn()
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"rule_lab_trades", "rule_lab_sessions"} <= names
    assert c.execute("SELECT COUNT(*) FROM activity").fetchone()[0] == 1
    database._local.conn = None
    assert database._conn().execute("SELECT COUNT(*) FROM rule_lab_trades").fetchone()[0] == 0   # idempotent


# ---- isolation ---------------------------------------------------------------------

def _live_like_candles(symbol_seed=1):
    rnd = random.Random(symbol_seed)
    p = 100.0
    out = []
    for day in (PREV2, PREV, DAY):
        spec = []
        for i in range(75):
            o = p
            p = p + rnd.uniform(-0.4, 0.4)
            spec.append((o, max(o, p) + 0.2, min(o, p) - 0.2, p, rnd.randint(500, 4000)))
        out += bars(day, spec)
    return out


def test_lab_writes_only_its_own_tables():
    lab = rule_lab.RuleLab()
    now = datetime.fromisoformat(f"{DAY}T15:20:00+05:30")
    cm = {f"S{i}": _live_like_candles(i) for i in range(12)}
    info = lab.run(now, cm, list(cm), scan_row=lambda s: {"long_only": s == "S0"})
    assert "error" not in info and info["inserted"] > 0
    conn = database._conn()
    assert conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM activity").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM rule_lab_trades WHERE symbol='S0' AND side='SHORT'").fetchone()[0] == 0
    assert conn.execute("SELECT symbols FROM rule_lab_sessions").fetchone()[0] == 12
    # a second pass with the same bars reads nothing again
    assert lab.run(now, cm, list(cm))["symbols"] == 0


def test_lab_exception_is_swallowed_and_logged(monkeypatch):
    lab = rule_lab.RuleLab()
    monkeypatch.setattr(rule_lab, "simulate_session", lambda *a, **k: 1 / 0)
    info = lab.run(datetime.fromisoformat(f"{DAY}T10:00:00+05:30"), {"A": _live_like_candles()}, ["A"])
    assert "ZeroDivisionError" in info["error"]


def test_time_budget_defers_the_rest_to_the_next_tick():
    lab = rule_lab.RuleLab(budget_s=0.0)
    now = datetime.fromisoformat(f"{DAY}T15:20:00+05:30")
    cm = {f"S{i}": _live_like_candles(i) for i in range(3)}
    info = lab.run(now, cm, list(cm))
    assert info["deferred"] == 3 and info["symbols"] == 0


def test_a_failing_lab_cannot_touch_the_tick_or_the_book(monkeypatch):
    state = AppState(watchlist=["AAA"], paper_mode=True)
    engine = trading_engine.TradingEngine(state)
    engine.scanner = None
    monkeypatch.setattr(trading_engine, "market_phase", lambda now: "open")
    monkeypatch.setattr(data_provider, "get_candles_batch", lambda *a, **k: {"AAA": _live_like_candles()})
    processed = []
    monkeypatch.setattr(trading_engine.TradingEngine, "_process_symbol",
                        lambda self, s, candles=None, now=None: processed.append(s))

    def boom(*a, **k):
        raise RuntimeError("lab bug")
    monkeypatch.setattr(engine.rule_lab, "run", boom)
    before = (dict(state.positions), state.capital if hasattr(state, "capital") else None,
              engine.risk.daily_realized_pnl, engine.risk.open_positions_count)
    engine._tick_impl()                      # must not raise
    assert processed == ["AAA"]
    assert state.last_update_ts is not None
    after = (dict(state.positions), state.capital if hasattr(state, "capital") else None,
             engine.risk.daily_realized_pnl, engine.risk.open_positions_count)
    assert before == after


def test_the_engine_runs_the_lab_after_the_symbol_loop(monkeypatch):
    state = AppState(watchlist=["AAA"], paper_mode=True)
    engine = trading_engine.TradingEngine(state)
    engine.scanner = None
    order = []
    monkeypatch.setattr(trading_engine, "market_phase", lambda now: "open")
    monkeypatch.setattr(data_provider, "get_candles_batch", lambda *a, **k: {"AAA": _live_like_candles()})
    monkeypatch.setattr(trading_engine.TradingEngine, "_process_symbol",
                        lambda self, s, candles=None, now=None: order.append("symbol"))
    monkeypatch.setattr(engine.rule_lab, "run", lambda *a, **k: order.append("lab"))
    engine._tick_impl()
    assert order == ["symbol", "lab"]
    monkeypatch.setattr(config, "RULE_LAB", {"enabled": False})
    order.clear()
    engine._tick_impl()
    assert order == ["symbol"]


def test_the_lab_never_names_the_order_path():
    src = Path(rule_lab.__file__).read_text()
    for name in ("execute_paper_order", "kite_broker", "_execute(", "place_order", "review_queue",
                 "risk_manager", "record_trade", "state.positions", "Scorecard("):
        assert name not in src, name


# ---- the leaderboard's statistics ---------------------------------------------------

def test_clustered_t_by_hand():
    data = {"a": [10, 20], "b": [-5], "c": [30, 0, 15]}
    st = rule_lab.clustered(data)
    xs = [10, 20, -5, 30, 0, 15]
    m = sum(xs) / 6
    ss = (30 - 2 * m) ** 2 + (-5 - m) ** 2 + (45 - 3 * m) ** 2
    se = math.sqrt(3 / 2 * ss) / 6
    assert st["mean"] == pytest.approx(m) and st["se"] == pytest.approx(se) and st["t"] == pytest.approx(m / se)
    assert st["ci"] == pytest.approx([m - 1.96 * se, m + 1.96 * se])
    assert rule_lab.clustered({"a": [1.0]})["t"] is None


def test_describe_win_rate_break_even_and_losing_streak():
    trades = [{"session": "2026-10-0%d" % (i // 3 + 1), "entry_time": str(i), "net_bp": x, "gross_bp": x + 16.6}
              for i, x in enumerate([10, -5, -5, -5, 20, -10])]
    d = rule_lab.describe(trades)
    assert d["win_rate"] == pytest.approx(2 / 6)
    assert d["payoff"] == pytest.approx(15 / 6.25)
    assert d["break_even_win_rate"] == pytest.approx(1 / (1 + 15 / 6.25))
    assert d["max_consecutive_losses"] == 3
    assert d["expectancy_r"] is None


def _synthetic(rules_mu, sessions, per=8, seed=3, sd=40.0):
    rnd = random.Random(seed)
    return {r: {s: [rnd.gauss(mu, sd) for _ in range(per)] for s in sessions} for r, mu in rules_mu.items()}


def test_romano_wolf_finds_a_real_edge_and_not_noise():
    sessions = [f"S{i:03d}" for i in range(60)]
    data = _synthetic({"good": 25.0, **{f"n{i}": 0.0 for i in range(10)}}, sessions)
    out = rule_lab.romano_wolf(data, sessions, block=3, b=2000)
    assert out["good"]["rejected"]
    assert not any(out[f"n{i}"]["rejected"] for i in range(10))
    noise = _synthetic({f"n{i}": 0.0 for i in range(10)}, sessions, seed=5)
    assert not any(v["rejected"] for v in rule_lab.romano_wolf(noise, sessions, block=3, b=2000).values())


def test_romano_wolf_bar_is_above_a_single_tests():
    sessions = [f"S{i:03d}" for i in range(60)]
    noise = _synthetic({f"n{i}": 0.0 for i in range(20)}, sessions, seed=9)
    out = rule_lab.romano_wolf(noise, sessions, block=3, b=2000, alpha=0.05)
    crit = next(v["critical"] for v in out.values() if v.get("critical") is not None)
    assert crit > 1.645


def _lab_rows(n_sessions, edge_rule=None, edge=40.0, per=6, seed=1):
    rnd = random.Random(seed)
    sessions = [(datetime(2026, 10, 5) + timedelta(days=i)).date().isoformat() for i in range(n_sessions)]
    trades = []
    for s in sessions:
        for r in rule_lab.RULE_IDS:
            for j in range(per):
                mu = edge if r == edge_rule else -2.0
                trades.append({"rule": r, "session_date": s, "net_bp": rnd.gauss(mu, 30.0)})
    return trades, sessions


def test_status_is_collecting_before_the_40th_session():
    trades, sessions = _lab_rows(39)
    st = rule_lab.evaluate(trades, sessions, open_left=set())
    assert all(v["status"] == "collecting" for v in st.values())


def test_screen_look_at_40_sessions_and_confirmation_on_the_next_40(monkeypatch):
    monkeypatch.setattr(rule_lab, "BOOTSTRAP_B", 2000)
    trades, sessions = _lab_rows(45, edge_rule="R09")
    st = rule_lab.evaluate(trades, sessions, open_left=set())
    assert st["R09"]["status"] == "candidate" and st["R09"]["confirm_from"] == sessions[40]
    assert sum(v["status"] == "screen_failed" for v in st.values()) == len(rule_lab.RULE_IDS) - 1
    # a session of the screen with an open trade holds the look
    assert rule_lab.evaluate(trades, sessions, open_left={sessions[3]})["R09"]["status"] == "collecting"
    trades, sessions = _lab_rows(80, edge_rule="R09")
    st = rule_lab.evaluate(trades, sessions, open_left=set())
    assert st["R09"]["status"] == "confirmed"


def test_page_reads_the_journal(monkeypatch):
    rule_lab._page_cache.update(at=0.0, data=None)
    lab = rule_lab.RuleLab()
    now = datetime.fromisoformat(f"{DAY}T15:20:00+05:30")
    cm = {f"S{i}": _live_like_candles(i) for i in range(12)}
    lab.run(now, cm, list(cm))
    page = rule_lab.page(max_age_s=0)
    assert len(page["rules"]) == len(rule_lab.RULE_IDS) and page["sessions"] == 1
    assert page["round_trip_bp"] == pytest.approx(16.6, abs=0.1)
    assert all(r["status"] == "collecting" for r in page["rules"])
    json.dumps(page)


# ---- the historical search (research/rule_lab_screen.py) ---------------------------------

def _synthetic_cache(path, days, symbols=("AAA", "BBB", "CCC"), seed=2):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, ts INTEGER NOT NULL, open REAL,"
                 " high REAL, low REAL, close REAL, volume INTEGER, PRIMARY KEY (symbol, interval, ts))")
    rnd = random.Random(seed)
    for sym in symbols:
        p = 100.0
        for day in days:
            t0 = datetime.fromisoformat(f"{day}T09:15:00+05:30")
            p *= 1 + rnd.uniform(-0.01, 0.01)
            for i in range(75):
                o = p
                p = max(1.0, p + rnd.uniform(-0.3, 0.3))
                ts = int((t0 + timedelta(minutes=5 * i)).timestamp())
                conn.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)",
                             (sym, "5m", ts, o, max(o, p) + 0.1, min(o, p) - 0.1, p, rnd.randint(200, 5000)))
    conn.commit()
    conn.close()


def _weekdays(first, n):
    d = datetime.fromisoformat(first)
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.date().isoformat())
        d += timedelta(days=1)
    return out


@pytest.fixture
def screen(tmp_path):
    import rule_lab_screen
    db = tmp_path / "cache.db"
    days = _weekdays("2025-11-03", 40) + _weekdays("2026-01-01", 6)
    _synthetic_cache(db, days)
    return rule_lab_screen, str(db), days


def test_screen_never_loads_a_2026_bar_in_discovery(screen):
    rls, db, days = screen
    conn = rls.connect(db)
    bars_ = rls.load_bars(conn, "AAA", 0, rls.DISCOVERY_END_TS)
    assert bars_ and max(b["time"] for b in bars_) < "2026-01-01"
    assert rls.count_2026_rows(conn)["AAA"] == 6 * 75
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO candles VALUES ('X','5m',1,1,1,1,1,1)")


def test_stage0_counts_without_returns(screen, tmp_path):
    rls, db, days = screen
    out = tmp_path / "s0.json"
    rec = rls.stage0(db, str(out), rule_lab.l55_conditions(), workers=1, log=lambda *a: None)
    assert rec["family"]["conditions_by_cohort"] == {"1": 20, "2": 87}
    assert rec["newest_bar_read"] < "2026-01-01"
    enum, greedy = rls.max_family_size(rule_lab.l55_conditions())
    assert rec["family"]["enumerated"] == enum and rec["family"]["greedy_max"] == greedy
    text = out.read_text()
    for word in ("net_bp", "mean", "gross", "exit_price"):
        assert word not in text


def test_search_singles_equal_the_forward_lab(screen):
    rls, db, days = screen
    conds = COHORT1 + ["Y01L", "Y05S", "Y13L", "O03S", "F02L"]
    results = rls.build(db, conds, outcomes=True, workers=1, syms=["AAA"])
    panel = rls.Panel(results, conds, outcomes=True)
    conn = rls.connect(db)
    allbars = rls.load_bars(conn, "AAA", 0, rls.DISCOVERY_END_TS)
    by_day = rls.sessions_of(allbars)
    order = sorted(by_day)
    for rid in conds:
        kind = "R3" if rid in rule_lab.R_RULES else "H30"
        side = rule_lab.RULE_SIDE[rid]
        taken = panel.trades((rid,), side, kind)
        S, N, valid = panel.session_sums(taken, side, kind)
        got = sorted(round(float(x), 6) for x in panel.net[(kind, side)][valid])
        want = []
        for di, d in enumerate(order):
            if di < rls.HISTORY_SESSIONS:
                continue
            candles = [c for dd in order[max(0, di - 4):di] for c in by_day[dd]] + by_day[d]
            want += [round(t["net_bp"], 6) for t in rule_lab.simulate_session(candles, d, rules=[rid])
                     if t["status"] == "closed"]
        assert got == sorted(want), rid


def test_discover_and_confirm_end_to_end_on_synthetic_bars(screen, tmp_path, monkeypatch):
    rls, db, days = screen
    monkeypatch.setattr(rule_lab, "BOOTSTRAP_B", 300)
    monkeypatch.setattr(rls, "MIN_TRADES", 5)
    monkeypatch.setattr(rls, "MIN_SESSIONS", 3)
    monkeypatch.setattr(rls, "GREEDY_MIN_TRADES", 5)
    monkeypatch.setattr(rls, "git_state", lambda repo_dir=None: ("abc123", False))
    s0 = tmp_path / "s0.json"
    rls.stage0(db, str(s0), COHORT1, workers=1, log=lambda *a: None)
    out = tmp_path / "d.json"
    rec = rls.discover(db, str(out), COHORT1, workers=1, log=lambda *a: None, stage0_path=str(s0))
    assert rec["sessions"][1] < "2026-01-01"
    assert 700 <= rec["family_size"] <= 1260
    assert rec["pbo"] is None or 0 <= rec["pbo"] <= 1
    assert len(rec["survivors"]) <= 5
    assert set(rec["rules"]) <= set(rule_lab.RULE_IDS)
    assert rec["provenance"]["commit"] == "abc123" and rec["provenance"]["dirty"] is False
    assert rec["provenance"]["family_hash"] == rls.family_hash(COHORT1)
    assert {r["origin"] for r in rec["top"]} <= {"enumerated", "greedy"}
    assert all(r["origin"] == "enumerated" for r in rec["top"] if len(r["conditions"]) <= 3)
    assert all("origin" in s for s in rec["survivors"])
    rec["survivors"] = [{"side": "LONG", "exit": "H30", "conditions": ["R09"], "t": 1.0, "mean": 1.0, "n": 1,
                         "origin": "enumerated"}]
    out.write_text(json.dumps(rec))
    c = rls.confirm_2026(db, str(out), str(tmp_path / "c.json"), COHORT1, workers=1,
                         log=lambda *a: None)
    assert c["window"][0] == "2026-01-01" and len(c["survivors"]) == 1
    assert c["metadata_2026_read_before_bars"] == "MAX(ts) of candles only"
    assert c["provenance"]["family_hash"] == rec["provenance"]["family_hash"]


def test_discover_and_confirm_refuse_an_existing_record_a_dirty_tree_and_a_changed_family(screen, tmp_path,
                                                                                            monkeypatch):
    rls, db, days = screen
    monkeypatch.setattr(rls, "git_state", lambda repo_dir=None: ("abc123", False))
    s0 = tmp_path / "s0.json"
    rls.stage0(db, str(s0), COHORT1, workers=1, log=lambda *a: None)
    out = tmp_path / "d.json"
    out.write_text("{}")
    with pytest.raises(rls.RefusedRun, match="exists"):
        rls.discover(db, str(out), COHORT1, workers=1, log=lambda *a: None, stage0_path=str(s0))
    out.unlink()
    monkeypatch.setattr(rls, "git_state", lambda repo_dir=None: ("abc123", True))
    with pytest.raises(rls.RefusedRun, match="uncommitted"):
        rls.discover(db, str(out), COHORT1, workers=1, log=lambda *a: None, stage0_path=str(s0))
    monkeypatch.setattr(rls, "git_state", lambda repo_dir=None: ("abc123", False))
    with pytest.raises(rls.RefusedRun, match="condition list"):
        rls.discover(db, str(out), COHORT1[:-1], workers=1, log=lambda *a: None, stage0_path=str(s0))
    # the same condition list but a stage 0 record whose family figures differ: refused on the hash
    tampered = json.loads(s0.read_text())
    tampered["family"]["greedy_max"] += 1
    tampered.pop("family_hash", None)
    s0b = tmp_path / "s0b.json"
    s0b.write_text(json.dumps(tampered))
    with pytest.raises(rls.RefusedRun, match="family hash"):
        rls.discover(db, str(out), COHORT1, workers=1, log=lambda *a: None, stage0_path=str(s0b))
    assert not out.exists(), "a refused run writes nothing"
    disc = tmp_path / "disc.json"
    disc.write_text(json.dumps({"survivors": [{"side": "LONG", "exit": "H30", "conditions": ["R09"]}],
                                "provenance": {"family_hash": "not-the-one"}}))
    with pytest.raises(rls.RefusedRun, match="family hash"):
        rls.confirm_2026(db, str(disc), str(tmp_path / "c.json"), COHORT1, workers=1, log=lambda *a: None)


def test_committed_stage0_record_hashes_to_the_current_family():
    import rule_lab_screen as rls
    rec = json.load(open(rls.default_stage0()))
    assert rls.stage0_family_hash(rec) == rls.family_hash(rule_lab.l55_conditions())   # L55 is closed at 107


def test_catalog_rules_register_once_with_every_source(tmp_path, monkeypatch):
    import rule_lab_screen as rls
    monkeypatch.setattr(rule_lab, "REGISTRY", dict(rule_lab.REGISTRY))
    monkeypatch.setattr(rule_lab, "RULES", list(rule_lab.RULES))
    monkeypatch.setattr(rule_lab, "RULE_IDS", list(rule_lab.RULE_IDS))
    monkeypatch.setattr(rule_lab, "RULE_SIDE", dict(rule_lab.RULE_SIDE))
    monkeypatch.setattr(rule_lab, "RULE_NAME", dict(rule_lab.RULE_NAME))
    a = [{"id": "Y1", "name": "vwap reclaim", "side": "long", "sources": ["yt:1"],
          "spec": {"all": [["close", ">", "vwap"], ["prev_close", "<", "prev_vwap"]]}},
         {"id": "Y2", "name": "no spec", "side": "LONG"}]
    b = {"rules": [{"id": "O1", "side": "LONG", "sources": ["ssrn:2"],
                    "spec": {"all": [["prev_close", "<", "prev_vwap"], ["close", ">", "vwap"]]}}]}
    pa, pb = tmp_path / "a.json", tmp_path / "b.json"
    pa.write_text(json.dumps(a))
    pb.write_text(json.dumps(b))
    reg, skipped = rls.load_catalog_rules([str(pa), str(pb)])
    assert reg == ["Y1"] and [s["id"] for s in skipped] == ["Y2"]
    assert rule_lab.REGISTRY["Y1"]["cohort"] == 2
    assert rule_lab.REGISTRY["Y1"]["sources"] == ["yt:1", "ssrn:2"]


def _long_walk(seed=21, days=(PREV2, PREV, DAY)):
    rnd = random.Random(seed)
    p, out = 100.0, []
    for d in days:
        spec = []
        p *= 1 + rnd.uniform(-0.012, 0.012)
        for i in range(75):
            o = p
            p = max(1.0, p * (1 + rnd.gauss(0, 0.0025)))
            spec.append((o, max(o, p) * (1 + abs(rnd.gauss(0, 0.001))), min(o, p) * (1 - abs(rnd.gauss(0, 0.001))), p,
                         rnd.randint(300, 6000)))
        out += bars(d, spec)
    return out


@pytest.mark.parametrize("seed", [21, 22])
def test_every_condition_is_causal(seed):
    """A signal on bar pos must not change when the bars after it are removed (no look-ahead),
    for every registered rule, including the 15- and 60-minute ones."""
    c = _long_walk(seed)
    first = len(c) - 75
    full = fires(c)
    for pos in range(0, 75, 2):
        cut = c[:first + pos + 1]
        ctx = rule_lab.session_context(cut, DAY)
        got = set(rule_lab.signals_at(ctx, pos))
        assert got == full[pos], (pos, got ^ full[pos])
    fired = set().union(*full.values())
    assert len(fired) >= 40, "the walk should exercise most conditions"


def test_signal_cache_reuses_a_finished_bar():
    c = _long_walk(5)
    cache = {}
    ctx = rule_lab.session_context(c, DAY)
    a = rule_lab.signals_at(ctx, 10, cache)
    assert rule_lab.signals_at(rule_lab.session_context(c[:-30], DAY), 10, cache) is a


def test_shadow_lab_ignores_the_engines_shorts_switch(monkeypatch):
    monkeypatch.setattr(config, "SCANNER", {**config.SCANNER, "allow_shorts": False})
    lab = rule_lab.RuleLab()
    now = datetime.fromisoformat(f"{DAY}T15:20:00+05:30")
    cm = {f"S{i}": _live_like_candles(i) for i in range(12)}
    lab.run(now, cm, list(cm))
    n = database._conn().execute("SELECT COUNT(*) FROM rule_lab_trades WHERE side='SHORT'").fetchone()[0]
    assert n > 0


def _up_days(n, start_day_idx=0):
    """n rising sessions before DAY, each a flat-ish day closing above the one before."""
    days = ["2026-09-23", "2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30"][-n:]
    out = []
    for i, d in enumerate(days):
        base = 94.0 + i
        spec = [(base + 0.2, base + 0.3, base - 0.3, base + 0.2 + (0.0 if j % 2 else 0.1), 1000) for j in range(74)]
        spec.append((base + 0.9, base + 1.0, base + 0.8, base + 0.9, 1000))  # closes well up
        out += bars(d, spec)
    return out


def _gap_up_short_fixture():
    """Three up days; yesterday opened in the bottom 20% of its range and closed in the top 20%
    (range 98-102); today gaps up past PDH + 0.3 x range, the first bar is green, the second red,
    the third closes below the red bar's low and back below PDH: Y11S, O02S, O04S and O07S."""
    hist = _up_days(3)
    prev = bars(PREV, [(98.2, 98.6, 98.0, 98.4, 1000)] + [(98.4 + 0.05 * j, 98.6 + 0.05 * j, 98.2 + 0.05 * j,
                                                           98.5 + 0.05 * j, 1000) for j in range(72)]
                + [(101.6, 102.0, 101.4, 101.8, 1000), (101.8, 101.9, 101.6, 101.8, 1000)])
    today = bars(DAY, [(103.5, 103.8, 103.4, 103.7, 1500), (103.7, 103.8, 103.1, 103.2, 1500),
                       (103.2, 103.3, 101.4, 101.5, 1500)] + [(101.5, 101.7, 101.3, 101.5, 1000)] * 60)
    return hist + prev + today


def _gap_down_long_fixture():
    """Yesterday opened in the top 20% and closed in the bottom quarter (range 98-102); today opens
    below PDL - 0.3 x range, the first bar is red, the second closes back above PDL with a green body:
    O02L, O04L and O07L."""
    hist = _up_days(2)
    prev = bars(PREV, [(101.8, 102.0, 101.5, 101.7, 1000)] + [(101.7 - 0.05 * j, 101.9 - 0.05 * j,
                                                              101.5 - 0.05 * j, 101.6 - 0.05 * j, 1000) for j in range(72)]
                + [(98.4, 98.6, 98.0, 98.2, 1000), (98.2, 98.4, 98.1, 98.2, 1000)])
    today = bars(DAY, [(96.5, 96.6, 96.2, 96.3, 1500), (96.3, 98.6, 96.2, 98.5, 1500)]
                 + [(98.5, 98.7, 98.3, 98.5, 1000)] * 60)
    return hist + prev + today


@pytest.mark.parametrize("fixture, expect", [
    (_gap_up_short_fixture, {"Y11S", "O02S", "O04S", "O07S"}),
    (_gap_down_long_fixture, {"O02L", "O04L", "O07L"}),
])
def test_rare_gap_conditions_fire_on_hand_built_bars_and_are_causal(fixture, expect):
    c = fixture()
    full = fires(c)
    fired = set().union(*full.values())
    assert expect <= fired, expect - fired
    first = next(i for i, b in enumerate(c) if b["time"].startswith(DAY))
    for pos in range(0, 6):
        cut = c[:first + pos + 1]
        assert set(rule_lab.signals_at(rule_lab.session_context(cut, DAY), pos)) == full[pos], pos


def test_y15_fires_once_dema200_has_history_and_is_causal():
    """Y15 needs about 400 bars; six sessions of a random walk give 450, and a Supertrend flip beyond
    DEMA200 occurs for at least one seed."""
    days = ("2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", PREV, DAY)
    hit = None
    for seed in range(30, 60):
        c = _long_walk(seed, days=days)
        full = fires(c)
        if any(r in s for s in full.values() for r in ("Y15L", "Y15S")):
            hit = (c, full)
            break
    assert hit is not None, "no seed produced a Y15 signal"
    c, full = hit
    first = len(c) - 75
    for pos in range(0, 75, 3):
        cut = c[:first + pos + 1]
        got = set(rule_lab.signals_at(rule_lab.session_context(cut, DAY), pos))
        assert got == full[pos], (pos, got ^ full[pos])


# ---- amendment 6: the filtered maximum and the cluster guard --------------------

def test_a_two_trade_rule_no_longer_sets_the_bar():
    """A rule with two trades and a near-zero standard error used to dominate every replicate's
    maximum (look 1's critical value was 7.17e7). With the floor it is void: the critical value with it
    present equals the one without, and it cannot be rejected."""
    sessions = [f"S{i:03d}" for i in range(60)]
    noise = _synthetic({f"n{i}": 0.0 for i in range(10)}, sessions, seed=3)
    without = rule_lab.romano_wolf(noise, sessions, block=3, b=2000)
    crit_without = next(v["critical"] for v in without.values() if v.get("critical") is not None)
    tiny = dict(noise)
    tiny["two"] = {"S000": [50.0001], "S001": [50.0]}
    floor = [r for r in tiny if r != "two"]
    with_floor = rule_lab.romano_wolf(tiny, sessions, block=3, b=2000, in_max=floor)
    crit_with = next(v["critical"] for v in with_floor.values() if v.get("critical") is not None)
    assert with_floor["two"]["in_max"] is False and not with_floor["two"]["rejected"]
    assert abs(crit_with - crit_without) < 1e-9
    # (that the unfiltered maximum was the problem is look 1's record: critical value 7.17e7)


def test_cluster_guard_drops_replicates_with_too_few_effective_sessions():
    """The guard removes a rule from a replicate's maximum when its effective session clusters
    (the replicate's weights over the sessions it traded in) are below the floor. Dropping entries
    never raises a maximum; a floor no replicate can meet empties every maximum."""
    import numpy as np
    sessions = [f"S{i:03d}" for i in range(60)]
    noise = _synthetic({f"n{i}": 0.0 for i in range(6)}, sessions, seed=4)
    S = np.array([[sum(noise[r].get(s) or []) for s in sessions] for r in sorted(noise)])
    N = np.array([[len(noise[r].get(s) or []) for s in sessions] for r in sorted(noise)])
    # a rule that trades in only three sessions: its effective clusters are usually below five
    S2 = np.vstack([S, np.array([[30.0, 31.0, 29.0] + [0.0] * 57])])
    N2 = np.vstack([N, np.array([[1, 1, 1] + [0] * 57], dtype=float)])
    _, _, _, c_off = rule_lab.romano_wolf_matrix(S2, N2, 3, b=1000, min_clusters=0)
    _, _, _, c5 = rule_lab.romano_wolf_matrix(S2, N2, 3, b=1000, min_clusters=5)
    _, _, _, c_all = rule_lab.romano_wolf_matrix(S2, N2, 3, b=1000, min_clusters=1000)
    assert c5[0] <= c_off[0] + 1e-12
    assert c_all[0] == np.inf
    # the thin rule's own replicate statistics are what the guard removes: without it, the two agree
    _, _, _, c5_without = rule_lab.romano_wolf_matrix(S, N, 3, b=1000, min_clusters=5)
    _, _, _, c_off_without = rule_lab.romano_wolf_matrix(S, N, 3, b=1000, min_clusters=0)
    assert abs(c5_without[0] - c_off_without[0]) < 1e-9


def test_forward_screen_voids_rules_below_the_floor_and_reports_the_family(monkeypatch):
    monkeypatch.setattr(rule_lab, "BOOTSTRAP_B", 1000)
    trades, sessions = _lab_rows(41, edge_rule="R09")
    thin = [t for t in trades if not (t["rule"] == "R16" and t["session_date"] > sessions[2])]
    st = rule_lab.evaluate(thin, sessions, open_left=set())
    assert st["R16"]["status"] == "screen_failed" and st["R16"]["screen"]["void"] is True
    assert st["R09"]["status"] == "candidate" and st["R09"]["screen"]["void"] is False
    sc = st["R09"]["screen"]
    assert sc["family"] == len(rule_lab.RULE_IDS) and sc["family_in_max"] == len(rule_lab.RULE_IDS) - 1
    assert sc["critical"] is not None and sc["critical"] < 10


def test_look2_family_hash_differs_and_record_carries_the_amended_fields(screen, tmp_path, monkeypatch):
    rls, db, days = screen
    monkeypatch.setattr(rule_lab, "BOOTSTRAP_B", 300)
    monkeypatch.setattr(rls, "MIN_TRADES", 5)
    monkeypatch.setattr(rls, "MIN_SESSIONS", 3)
    monkeypatch.setattr(rls, "GREEDY_MIN_TRADES", 5)
    monkeypatch.setattr(rls, "git_state", lambda repo_dir=None: ("abc123", False))
    assert rls.family_hash(COHORT1, look=2) != rls.family_hash(COHORT1, look=1)
    s0 = tmp_path / "s0.json"
    rls.stage0(db, str(s0), COHORT1, workers=1, log=lambda *a: None)
    out1 = tmp_path / "d.json"
    out1.write_text("{}")  # look 1's record exists; look 2 writes elsewhere and is not refused by it
    out2 = tmp_path / "d_look2.json"
    rec = rls.discover(db, str(out2), COHORT1, workers=1, log=lambda *a: None, stage0_path=str(s0), look=2)
    assert rec["look_number"] == 2 and rec["mode"] == "discover-look2"
    assert rec["max_filter"] == {"min_trades": 5, "min_sessions": 3, "min_clusters": rule_lab.MIN_CLUSTERS_IN_MAX}
    assert rec["newest_bar_read"] < "2026-01-01"
    assert rec["provenance"]["family_hash"] == rls.family_hash(COHORT1, look=2)
    assert 0 < rec["family_in_max"] <= rec["family_size"]
    assert all(r["n"] >= 5 and r["sessions"] >= 3 for r in rec["powered_rows"]) and all(r["n"] >= 5 for r in rec["top"])
    assert rec["best"] is None or rec["best"]["n"] >= 5
    assert all(len(r["halves"]) == 2 for r in rec["powered_rows"])
    assert out1.read_text() == "{}"
    # the same family under look 1's hash is refused for look 2 (the filter is part of the hash)
    with pytest.raises(rls.RefusedRun, match="family hash"):
        rls.refuse_unless_allowed(str(tmp_path / "x_look2.json"), COHORT1, rls.family_hash(COHORT1, 1), "x", look=2)


def test_halves_are_null_when_a_half_has_no_trades():
    import numpy as np
    import rule_lab_screen as rls
    ev = {("LONG", "H30", ("R01",)): {"S": np.array([0.0] * 20 + [5.0] * 20, dtype="float32"),
                                     "N": np.array([0] * 20 + [1] * 20, dtype="float32"),
                                     "mean": 5.0, "t": 2.0, "n": 20, "sessions": 20}}
    rls.judge(ev, [f"d{i}" for i in range(40)], b=200, log=lambda *a: None, look=2)
    assert ev[("LONG", "H30", ("R01",))]["halves"][0] is None


def test_look2_refuses_a_stage0_record_whose_conditions_differ(screen, tmp_path, monkeypatch):
    """The expected hash comes from the stage 0 record, never from the run's own condition list."""
    rls, db, days = screen
    monkeypatch.setattr(rls, "git_state", lambda repo_dir=None: ("abc123", False))
    s0 = tmp_path / "s0.json"
    rls.stage0(db, str(s0), COHORT1[:-1], workers=1, log=lambda *a: None)
    rec = json.loads(s0.read_text())
    assert rls.stage0_family_hash(rec, look=2) == rls.family_hash(COHORT1[:-1], look=2)
    assert rls.stage0_family_hash(rec, look=2) != rls.stage0_family_hash(rec, look=1)
    for look in (1, 2):
        with pytest.raises(rls.RefusedRun, match="condition list"):
            rls.discover(db, str(tmp_path / f"d_look{look}.json"), COHORT1, workers=1, log=lambda *a: None,
                         stage0_path=str(s0), look=look)
    assert not (tmp_path / "d_look2.json").exists()
