"""Cohort 4 of the rule lab (rule_lab_patterns.py, prereg amendment 7): the registry, each
series against an independent reading, hand-built fixtures that fire each rule, causality by
truncation for every one, the flags' R3 exit, and the cohort's own screen window."""
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import candlestick_patterns  # noqa: E402
import indicators  # noqa: E402
import rule_lab  # noqa: E402
import rule_lab_patterns as rlp  # noqa: E402
from test_rule_lab import DAY, PREV, PREV2, _lab_rows, _long_walk, bars, fires, flat, history, where  # noqa: E402

COHORT4 = [r for r in rule_lab.RULE_IDS if rule_lab.REGISTRY[r]["cohort"] == 4]


def _causal(c, positions=None, day=DAY):
    """The rules firing on each of today's bars must not change when later bars are deleted."""
    full = fires(c, day)
    first = next(i for i, b in enumerate(c) if b["time"].startswith(day))
    for pos in (positions if positions is not None else range(len(full))):
        cut = c[:first + pos + 1]
        got = set(rule_lab.signals_at(rule_lab.session_context(cut, day), pos))
        assert got == full[pos], (pos, got ^ full[pos])
    return full


# ---- the registry -------------------------------------------------------------------

def test_cohort_four_is_fifty_rules_at_its_own_alpha():
    assert len(COHORT4) == 50 and len(rule_lab.RULE_IDS) == 157
    sides = [rule_lab.RULE_SIDE[r] for r in COHORT4]
    assert sides.count("LONG") == 25 and sides.count("SHORT") == 25
    assert [r for r in COHORT4 if rule_lab.REGISTRY[r]["exit"] == "r"] == ["C02L", "C02S"]
    assert rule_lab.R_RULES == ["R19", "R20", "C02L", "C02S"]
    assert rule_lab.cohort_alpha(4) == pytest.approx(0.003125)
    assert all(rule_lab.REGISTRY[r]["label"] == "2b" and rule_lab.REGISTRY[r]["sources"] for r in COHORT4)
    # every name of the engine's detector is now a rule of the lab, through the detector itself
    traded = {n for rid, n, _ in rlp.DIRECTIONAL} | rlp.COHORT1_PATTERNS | {"Doji", "Inside Bar"}
    assert traded == set(candlestick_patterns.PATTERN_NAMES)
    # L55's family stays the 107 of cohorts 1 and 2
    assert len(rule_lab.l55_conditions()) == 107 and not set(rule_lab.l55_conditions()) & set(COHORT4)


# ---- series against an independent reading -----------------------------------------------

def test_adx_series_equals_the_engines_adx_on_every_prefix():
    c = _long_walk(31)
    a, p, m = rlp.adx_series(c, 14)
    for k in range(20, len(c), 7):
        ref = indicators.adx(c[:k + 1], 14)
        if ref is None:
            assert a[k] is None
        else:
            assert a[k] == pytest.approx(ref["adx"]) and p[k] == pytest.approx(ref["plus_di"])
            assert m[k] == pytest.approx(ref["minus_di"])
    assert a[27] is None and a[28] is not None


def test_keltner_atr_equals_the_engines_atr_on_every_prefix():
    c = _long_walk(32)
    s = rlp._atr_mean_series(c, 10)
    for k in range(5, len(c), 9):
        assert s[k] == (None if indicators.atr(c[:k + 1], 10) is None else pytest.approx(indicators.atr(c[:k + 1], 10)))


def test_obv_divergence_rule_equals_the_engines_reading():
    c = _long_walk(33)
    first = len(c) - 75
    full = fires(c)
    hits = 0
    for pos in range(75):
        ref = indicators.obv_divergence(c[:first + pos + 1], 20)
        assert ("I11L" in full[pos]) == (ref == "bullish") and ("I11S" in full[pos]) == (ref == "bearish"), pos
        hits += ref is not None
    assert hits > 0


def _naive_ichimoku(c, k):
    def hl(n, j):
        w = c[j - n + 1:j + 1]
        return (max(b["high"] for b in w) + min(b["low"] for b in w)) / 2
    tk, kj = hl(9, k), hl(26, k)
    j = k - 26
    return tk, kj, (hl(9, j) + hl(26, j)) / 2, hl(52, j)


@pytest.mark.parametrize("seed", [41, 42, 43])
def test_indicator_rules_match_independent_readings_on_a_walk(seed):
    c = _long_walk(seed)
    first = len(c) - 75
    full = _causal(c, range(0, 75, 3))
    closes = [b["close"] for b in c]
    e20 = indicators.ema_series(closes, 20)
    seen = set()
    for pos in range(1, 75):
        k = first + pos
        f = full[pos]
        # Keltner: EMA20 +/- 2 x ATR10
        ku = [e20[j] + 2 * indicators.atr(c[:j + 1], 10) for j in (k - 1, k)]
        kl = [e20[j] - 2 * indicators.atr(c[:j + 1], 10) for j in (k - 1, k)]
        assert ("I04L" in f) == (closes[k] > ku[1] and closes[k - 1] <= ku[0]), pos
        assert ("I04S" in f) == (closes[k] < kl[1] and closes[k - 1] >= kl[0]), pos
        assert ("I05L" in f) == (closes[k - 1] < kl[0] and closes[k] >= kl[1]), pos
        assert ("I05S" in f) == (closes[k - 1] > ku[0] and closes[k] <= ku[1]), pos
        # Donchian 20
        hh = max(b["high"] for b in c[k - 20:k])
        ll = min(b["low"] for b in c[k - 20:k])
        assert ("I07L" in f) == (closes[k] > hh) and ("I07S" in f) == (closes[k] < ll), pos
        # Ichimoku
        tk, kj, sa, sb = _naive_ichimoku(c, k)
        tkp, kjp, _, _ = _naive_ichimoku(c, k - 1)
        assert ("I03L" in f) == (tk > kj and tkp <= kjp and closes[k] > max(sa, sb)), pos
        assert ("I03S" in f) == (tk < kj and tkp >= kjp and closes[k] < min(sa, sb)), pos
        # ADX 25 with a DI cross, from the engine's adx on prefixes
        a, ap = indicators.adx(c[:k + 1], 14), indicators.adx(c[:k], 14)
        up = a["adx"] > 25 and a["plus_di"] > a["minus_di"] and ap["plus_di"] <= ap["minus_di"]
        dn = a["adx"] > 25 and a["minus_di"] > a["plus_di"] and ap["minus_di"] <= ap["plus_di"]
        assert ("I01L" in f) == up and ("I01S" in f) == dn, pos
        # VWAP, its sigma bands and the cross
        day = c[first:k + 1]
        v = indicators.session_vwap(day)
        vp = indicators.session_vwap(c[first:k])
        vol = sum(b["volume"] for b in day)
        sd = (sum(b["volume"] * (((b["high"] + b["low"] + b["close"]) / 3 - v) ** 2) for b in day) / vol) ** 0.5
        b = c[k]
        assert ("I10L" in f) == (b["close"] > v and closes[k - 1] <= vp), pos
        assert ("I10S" in f) == (b["close"] < v and closes[k - 1] >= vp), pos
        if pos >= 6:
            assert ("I08L" in f) == (b["low"] <= v - sd < b["close"] and b["close"] > b["open"]), pos
            assert ("I08S" in f) == (b["high"] >= v + sd > b["close"] and b["close"] < b["open"]), pos
            assert ("I09L" in f) == (b["close"] < v - 2 * sd) and ("I09S" in f) == (b["close"] > v + 2 * sd), pos
        else:
            assert not f & {"I08L", "I08S", "I09L", "I09S"}
        # the filters
        assert ("F10L" in f) == ("F10S" in f) == (pos < 6) and ("F11L" in f) == ("F11S" in f) == (pos >= 51), pos
        seen |= f & set(COHORT4)
    assert {"I04L", "I04S", "I07L", "I07S", "I10L", "I10S"} <= seen


def test_every_cohort_four_rule_fires_somewhere_on_the_walks():
    seen = set()
    for seed in range(41, 56):
        for pos, f in fires(_long_walk(seed)).items():
            seen |= f & set(COHORT4)
    rare = {"C01L", "C01S", "C02L", "C02S", "I02L", "I02S", "I03L", "I03S", "I01L", "I01S", "I06L", "I06S",
            "P13", "P14", "P15", "P16", "P11", "P12", "P09", "P10", "P07", "P08", "P03", "P04", "P17L", "P17S",
            "P18L", "P18S", "P01", "P02", "P05", "P06", "I09L", "I09S"}
    missing = set(COHORT4) - seen - rare
    assert not missing, missing


# ---- the candlestick rules are the engine's detector -------------------------------------------

def _pattern_walk(seed):
    rnd = random.Random(seed)
    p = 100.0
    spec = []
    for i in range(225):
        o = p + rnd.uniform(-0.3, 0.3)
        p = o + rnd.uniform(-1.2, 1.2)
        spec.append((o, max(o, p) + abs(rnd.gauss(0, 0.5)), min(o, p) - abs(rnd.gauss(0, 0.5)), p, 1000))
    return bars(PREV2, spec[:75]) + bars(PREV, spec[75:150]) + bars(DAY, spec[150:])


@pytest.mark.parametrize("seed", [13, 14, 15, 16])
def test_sixteen_pattern_rules_are_the_engines_detector_bar_by_bar(seed):
    c = _pattern_walk(seed)
    names = {rid: n for rid, n, _ in rlp.DIRECTIONAL}
    first = 150
    seen = set()
    for pos, fired in fires(c).items():
        k = first + pos
        window = c[max(0, k - 29):k + 1]
        found = {x["name"] for x in candlestick_patterns.detect_patterns(window, indicators.atr(window, 14))}
        for rid, name in names.items():
            assert (rid in fired) == (name in found), (rid, pos)
            seen |= {rid} if name in found else set()
        if pos >= 1:
            wp = c[max(0, k - 30):k]
            prev = {x["name"] for x in candlestick_patterns.detect_patterns(wp, indicators.atr(wp, 14))}
            b, q = c[k], c[k - 1]
            assert ("P17L" in fired) == ("Doji" in prev and b["close"] > q["high"]), pos
            assert ("P17S" in fired) == ("Doji" in prev and b["close"] < q["low"]), pos
            assert ("P18L" in fired) == ("Inside Bar" in prev and b["close"] > q["high"]), pos
            assert ("P18S" in fired) == ("Inside Bar" in prev and b["close"] < q["low"]), pos
    assert seen, "the walk should show at least one of the sixteen patterns"


def test_morning_star_and_doji_breakout_by_hand():
    pre = [(100 - 0.3 * i, 100.1 - 0.3 * i, 99.6 - 0.3 * i, 99.7 - 0.3 * i, 1000) for i in range(14)]
    low = pre[-1][3]
    star = [(low, low + 0.05, low - 1.2, low - 1.0, 1000),               # a tall red bar
            (low - 1.1, low - 1.0, low - 1.3, low - 1.12, 1000),          # a small body
            (low - 1.05, low - 0.2, low - 1.1, low - 0.3, 1000)]          # a bullish close past the red bar's midpoint
    c = history() + bars(DAY, pre + star)
    assert 16 in where(c, "P09")
    doji = [(100, 100.6, 99.4, 100.01, 1000), (100.05, 100.9, 100.0, 100.8, 1000)]
    c = history() + bars(DAY, [(100, 100.3, 99.7, 100, 1000)] * 14 + doji)
    assert where(c, "P17L") == [15] and where(c, "P17S") == []
    _causal(c, [14, 15])


# ---- hand-built fixtures for the rules the walks rarely reach -------------------------------------

def test_fibonacci_retracement_bounce_and_rejection():
    up = [(100 + 0.2 * i, 100.25 + 0.2 * i, 99.95 + 0.2 * i, 100.2 + 0.2 * i, 1000) for i in range(10)]  # 100 -> 102
    # range 100.0-102.25 after bar 9 (its high); 38.2% = 101.39, 61.8% = 100.86
    pull = [(102, 102.05, 101.6, 101.7, 1000), (101.7, 101.75, 101.45, 101.5, 1000),
            (101.5, 101.6, 101.0, 101.55, 1000)]                           # low in the zone, closes above 38.2%
    c = history() + bars(DAY, up + pull)
    dh, dl = max(b["high"] for b in bars(DAY, up + pull[:2])), 99.95
    f38, f62 = dh - 0.382 * (dh - dl), dh - 0.618 * (dh - dl)
    assert f62 <= 101.0 <= f38 < 101.55
    assert where(c, "I02L") == [12] and where(c, "I02S") == []
    down = [(o, h, lo, cl, v) for (o, h, lo, cl, v) in [(200 - x, 200 - x + 0.05, 200 - x - 0.3, 200 - x - 0.25, 1000)
                                                        for x in [0.25 * i for i in range(10)]]]
    rally = [(197.75, 198.1, 197.7, 198.0, 1000), (198.0, 198.4, 197.95, 198.3, 1000),
             (198.3, 198.95, 198.2, 198.25, 1000)]
    c = history() + bars(DAY, down + rally)
    assert where(c, "I02S") == [12]
    _causal(c, [11, 12])


def test_parabolic_sar_flips_on_a_reversal_bar():
    rising = [(100 + 0.2 * i, 100.3 + 0.2 * i, 99.9 + 0.2 * i, 100.2 + 0.2 * i, 1000) for i in range(75)]
    hist = flat(PREV2) + bars(PREV, rising)
    top = rising[-1][3]
    down = [(top - 0.3 * i, top - 0.3 * i + 0.1, top - 0.3 * i - 0.4, top - 0.3 * (i + 1), 1000) for i in range(20)]
    jump = [(down[-1][3], down[-1][3] + 3.0, down[-1][3] - 0.1, down[-1][3] + 2.8, 1000)]
    c = hist + bars(DAY, down + jump)
    assert where(c, "I06L") == [20]
    assert where(c, "I06S") and max(where(c, "I06S")) < 3
    _causal(c, [0, 1, 2, 19, 20])


def test_double_top_and_double_bottom_on_the_neckline_break():
    def leg(a, b, n, w=0.1):
        step = (b - a) / n
        return [(a + step * i, max(a + step * i, a + step * (i + 1)) + w, min(a + step * i, a + step * (i + 1)) - w,
                 a + step * (i + 1), 1000) for i in range(n)]
    tops = leg(100, 102, 5) + leg(102, 100.5, 5) + leg(100.5, 102.05, 5)       # two tops: 102.1 and 102.15
    tops += leg(102.05, 101.2, 3) + [(101.2, 101.3, 100.1, 100.2, 1000)]      # the first close below 100.4
    c = history() + bars(DAY, tops)
    highs, lows = rlp.swings(rule_lab.session_context(c, DAY), 18)
    assert [j for j, _ in highs] == [4, 14]
    assert where(c, "C01S") == [18] and where(c, "C01L") == []
    bottoms = [(2 * 101 - o, 2 * 101 - lo, 2 * 101 - h, 2 * 101 - cl, v) for (o, h, lo, cl, v) in tops]
    c2 = history() + bars(DAY, bottoms)
    assert where(c2, "C01L") == [18] and where(c2, "C01S") == []
    _causal(c, [16, 17, 18])
    _causal(c2, [18])
    # tops 0.5% apart are not a double top
    wide = list(tops)
    wide[14] = (wide[14][0], 102.7, wide[14][2], wide[14][3], 1000)
    assert where(history() + bars(DAY, wide), "C01S") == []


def _flag_session(long=True):
    pole = [(100 + 0.3 * i, 100.35 + 0.3 * i, 99.95 + 0.3 * i, 100.3 + 0.3 * i, 1000) for i in range(6)]  # to 101.85
    top = pole[-1][1]
    flag = [(101.8, 101.82, 101.55, 101.6, 900), (101.6, 101.7, 101.5, 101.65, 800),
            (101.65, 101.75, 101.52, 101.7, 800), (101.7, 101.8, 101.6, 101.75, 800)]
    brk = [(101.75, 102.2, 101.7, 102.1, 2000)]
    after = [(102.1 + 0.05 * i, 102.2 + 0.05 * i, 102.0 + 0.05 * i, 102.15 + 0.05 * i, 1000) for i in range(30)]
    spec = pole + flag + brk + after
    if not long:
        spec = [(2 * 101 - o, 2 * 101 - lo, 2 * 101 - h, 2 * 101 - cl, v) for (o, h, lo, cl, v) in spec]
    assert all(b[2] >= top - 0.4 * (top - 99.95) for b in flag) or not long
    return history() + bars(DAY, spec)


def test_bull_and_bear_flag_fire_on_the_break_and_exit_by_r3():
    c = _flag_session(True)
    assert where(c, "C02L") == [10] and where(c, "C02S") == []
    _causal(c, [8, 9, 10, 11])
    t = [t for t in rule_lab.simulate_session(c, DAY) if t["rule"] == "C02L"]
    assert len(t) == 1 and t[0]["stop_price"] == pytest.approx(101.7) and t[0]["entry_time"].endswith("10:10:00+05:30")
    assert t[0]["target_price"] == pytest.approx(t[0]["entry_price"] + 3 * (t[0]["entry_price"] - 101.7))
    assert t[0]["status"] == "closed" and t[0]["exit_reason"] in ("target", "square_off") and "net_r" in t[0]
    c = _flag_session(False)
    assert where(c, "C02S") == [10] and where(c, "C02L") == []
    # a flag that retraces more than 40% of the pole is not a flag
    deep = _flag_session(True)
    k = len(history()) + 7
    deep[k] = {**deep[k], "low": 100.5}
    assert where(deep, "C02L") == []


def test_adx_di_cross_on_a_v_reversal():
    fall = [(110 - 0.4 * i, 110.05 - 0.4 * i, 109.5 - 0.4 * i, 109.6 - 0.4 * i, 1000) for i in range(30)]
    bottom = fall[-1][3]
    rise = [(bottom + 0.7 * i, bottom + 0.8 + 0.7 * i, bottom - 0.05 + 0.7 * i, bottom + 0.7 * (i + 1), 1000)
            for i in range(20)]
    c = history() + bars(DAY, fall + rise)
    hits = where(c, "I01L")
    assert len(hits) == 1 and 30 <= hits[0] <= 40
    k = len(history()) + hits[0]
    a, ap = indicators.adx(c[:k + 1], 14), indicators.adx(c[:k], 14)
    assert a["adx"] > 25 and a["plus_di"] > a["minus_di"] and ap["plus_di"] <= ap["minus_di"]
    _causal(c, [hits[0] - 1, hits[0], hits[0] + 1])


# ---- the trade and the look -----------------------------------------------------------------

def test_cohort_four_screen_runs_on_its_own_first_forty_sessions(monkeypatch):
    monkeypatch.setattr(rule_lab, "BOOTSTRAP_B", 500)
    trades, sessions = _lab_rows(43, edge_rule="I07L")
    # the cohort was added after the lab started: its rules have no trade in the first three sessions
    late = [t for t in trades if not (rule_lab.REGISTRY[t["rule"]]["cohort"] == 4 and t["session_date"] < sessions[3])]
    assert rule_lab.cohort_start(4, late) == sessions[3] and rule_lab.cohort_start(1, late) is None
    assert rule_lab.cohort_start(4, []) is False
    st = rule_lab.evaluate(late, sessions[:42], open_left=set())
    assert st["R01"]["status"] == "screen_failed"                        # cohort 1's screen: sessions 1-40
    assert st["I07L"]["status"] == "collecting"                          # cohort 4's window ends at session 43
    st = rule_lab.evaluate(late, sessions, open_left=set())
    assert st["I07L"]["status"] == "candidate" and st["I07L"]["confirm_from"] is None
    assert st["I07L"]["screen"]["family"] == 157 and st["I07S"]["status"] == "screen_failed"


def test_page_carries_the_cohort_label_and_start(monkeypatch):
    rule_lab._page_cache.update(at=0.0, data=None)
    page = rule_lab.page(max_age_s=0)
    assert page["family"] == 157 and page["cohort_alpha"]["4"] == pytest.approx(0.003125)
    assert page["cohort_start"] == {"1": None, "2": None, "4": None}
    row = next(r for r in page["rules"] if r["rule"] == "P09")
    assert row["cohort"] == 4 and row["cohort_label"] == "2b" and "trials 128-202" in row["prior"]
