"""3g's detector, checked before stage 0 runs (prereg-3g-smc-mtf.md,
Accounting): each rule on hand-built bars, the bull/bear mirror, and a
lookahead proof — events on a truncated series equal the full series' events
up to the cut, at every cut."""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research import smc_mtf as smc


def _day(date, closes, first_open, overrides=None):
    """75 start-labelled 5m bars, 09:15..15:25, open = previous close,
    high/low = the body unless overridden."""
    assert len(closes) == 75
    out, o, t = [], first_open, datetime.fromisoformat(f"{date}T09:15:00")
    for i, c in enumerate(closes):
        b = {"time": t.isoformat(), "open": o, "high": max(o, c), "low": min(o, c), "close": c, "volume": 1000}
        b.update((overrides or {}).get(i, {}))
        out.append(b)
        o, t = c, t + timedelta(minutes=5)
    return out


def _lin(a, b, n):
    return [a + (b - a) * (i + 1) / n for i in range(n)]


def _bearish_scenario():
    d1 = _day("2025-03-03", [105.0] * 75, 105.0, {0: {"high": 110.0, "low": 100.0}})
    d2 = _day("2025-03-04", _lin(105, 99, 48) + [98.8] * 26 + [98.5], 105.0)
    a = (_lin(98.5, 100.5, 12)                                   # H1 09:15 — the bull OB candle
         + [100.5 + 0.5 * (i + 1) / 3 for i in range(3)] + _lin(101, 99.8, 9)   # H2 — peak 101
         + _lin(99.8, 97.5, 12)                                  # H3 — closes below OB open: confirmation
         + _lin(97.5, 98.6, 12))                                 # H4 — A closes 98.6 < 99.0
    b = [99.6, 99.4, 99.0] + [98.8, 98.5, 98.3] + [98.3] * 21     # 15m sweep candle, then the cemented one
    d3 = _day("2025-03-05", a + b, 98.5)
    return d1 + d2 + d3


def test_aggregate_4h_slots_and_completeness():
    bars = _bearish_scenario()
    h4 = smc.aggregate(bars, smc._4H)
    assert [(x["date"], x["start"], x["end"]) for x in h4[:3]] == [
        ("2025-03-03", "09:15", "13:15"), ("2025-03-03", "13:15", "15:30"), ("2025-03-04", "09:15", "13:15")]
    assert h4[0]["high"] == 110.0 and h4[0]["low"] == 100.0
    assert all(x["complete"] for x in h4)
    part = smc.aggregate(bars[:-3], smc._4H)                     # cut before 15:30 on the last day
    assert part[-1]["complete"] is False and part[-2]["complete"] is True


def test_bias_rule():
    dd = {"a": {"high": 110, "low": 100, "close": 105}, "up": {"close": 111}, "dn": {"close": 99}, "in": {"close": 104}}
    assert smc.bias(dd, "up", "a") == "bull"
    assert smc.bias(dd, "dn", "a") == "bear"
    assert smc.bias(dd, "in", "a") is None


def test_hand_built_bearish_setup_fires_once_with_known_prices():
    evs = smc.detect(_bearish_scenario())
    assert len(evs) == 1
    e = evs[0]
    assert (e["day"], e["end"], e["side"], e["sweep"]) == ("2025-03-05", "2025-03-05T13:45", "SHORT", "A-of-D")
    assert abs(e["entry"] - 98.3) < 1e-9 and abs(e["stop"] - 99.6) < 1e-9
    assert abs(e["target"] - (98.3 - 2 * 1.3)) < 1e-9


def test_entry_waits_for_the_4h_sweep_bar_to_close():
    """The 1H confirmation lands at 12:15, inside the A bar. The 15m entry
    must still wait for 13:15, when the sweep is first known."""
    bars = _bearish_scenario()
    assert all(e["end"][11:16] > "13:15" for e in smc.detect(bars))


def test_a_trade_through_hstar_cancels_the_setup():
    bars = _bearish_scenario()
    i = next(k for k, b in enumerate(bars) if b["time"] == "2025-03-05T13:20:00")
    bars[i] = {**bars[i], "high": 101.5}                        # above H* = 101 before the entry
    assert smc.detect(bars) == []


def test_mirror_gives_the_same_setup_on_the_other_side():
    bars = _bearish_scenario()
    [bear] = smc.detect(bars)
    [bull] = smc.detect(smc.mirror(bars))
    assert bull["side"] == "BUY" and bull["end"] == bear["end"] and bull["sweep"] == bear["sweep"]
    assert abs(bull["entry"] + bear["entry"]) < 1e-9 and abs(bull["stop"] + bear["stop"]) < 1e-9
    assert abs(bull["target"] + bear["target"]) < 1e-9


def _walk(seed, days=30):
    rnd, out, px = random.Random(seed), [], 500.0
    d = datetime(2025, 1, 6)
    for _ in range(days):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        t = d.replace(hour=9, minute=15)
        for _ in range(75):
            o = px
            px = max(10.0, px * (1 + rnd.gauss(0, 0.004)))
            hi, lo = max(o, px) * (1 + abs(rnd.gauss(0, 0.002))), min(o, px) * (1 - abs(rnd.gauss(0, 0.002)))
            out.append({"time": t.isoformat(), "open": o, "high": hi, "low": lo, "close": px, "volume": 1000})
            t += timedelta(minutes=5)
        d += timedelta(days=1)
    return out


def _end_of(bar):
    return f"{bar['time'][:10]}T{smc._plus5(bar['time'][11:16])}"


def test_no_lookahead_truncated_series_reproduce_full_events():
    """Cut at every bar from the previous session's 13:15 to the end of each
    event's session, plus coarse cuts elsewhere. Any read of a later bar makes
    a truncated series disagree with the full one."""
    total = 0
    for seed in range(20):
        full = _walk(seed, days=60)
        evs = smc.detect(full)
        total += len(evs)
        cuts = set(range(160, len(full), 97))
        for e in evs:
            first = next(i for i, b in enumerate(full) if b["time"][:10] == e["day"])
            cuts.update(range(max(1, first - 27), min(len(full), first + 75) + 1))
        for cut in sorted(cuts):
            upto = _end_of(full[cut - 1])
            assert smc.detect(full[:cut]) == [e for e in evs if e["end"] <= upto], (seed, cut)
    assert total >= 10, "the random walks must produce enough events for this test to mean anything"


def test_no_lookahead_at_every_bar_of_the_hand_built_day():
    full = _bearish_scenario()
    [e] = smc.detect(full)
    for cut in range(150, len(full) + 1):
        got = smc.detect(full[:cut])
        assert got == ([e] if e["end"] <= _end_of(full[cut - 1]) else []), cut


def test_strategy_fn_fires_on_the_5m_bar_that_ends_the_15m_entry_bar():
    bars = _bearish_scenario()
    [e] = smc.detect(bars)
    fn = smc.strategy_fn_for({id(bars[0]): {e["end"]: e}})
    fired = [(b["time"], fn(bars[: i + 1])[0]) for i, b in enumerate(bars) if fn(bars[: i + 1])[0]]
    assert fired == [("2025-03-05T13:40:00", "SHORT")]
    sig, st = fn(bars[: [b["time"] for b in bars].index("2025-03-05T13:40:00") + 1])
    assert st["entry_mode"] == "checklist" and st["checklist"]["short"]["stop"] == e["stop"]
