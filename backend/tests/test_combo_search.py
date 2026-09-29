"""The combination search's pre-registered rules (prereg-combo-search.md), on synthetic data."""
from research import combo_search as c


def test_a_pattern_counts_only_with_strength_two_and_no_conflict():
    assert c.pattern_direction([{"bias": "bullish", "strength": 2}]) == 1
    assert c.pattern_direction([{"bias": "bearish", "strength": 3}, {"bias": "neutral", "strength": 3}]) == -1
    assert c.pattern_direction([{"bias": "bullish", "strength": 1}]) == 0
    assert c.pattern_direction([{"bias": "bullish", "strength": 2}, {"bias": "bearish", "strength": 2}]) == 0
    assert c.pattern_direction([]) == 0


def test_quintiles_cut_like_the_harness():
    flags = c.quintile_flags(list(range(10)))          # n // 5 = 2 at each end
    assert flags == {0: -1, 1: -1, 8: 1, 9: 1}
    assert c.quintile_flags([1.0, 2.0, 3.0]) == {}


def test_the_four_rules():
    assert c.rule_direction("R1", 20.0, 1, 0) == 1 and c.rule_direction("R1", 10.0, 1, 0) == 0
    assert c.rule_direction("R1", -20.0, -1, 0) == -1 and c.rule_direction("R1", -20.0, 0, 0) == 0
    assert c.rule_direction("R2", 5.0, 0, 1) == 1 and c.rule_direction("R2", -5.0, 0, 1) == 0
    assert c.rule_direction("R3", 0.0, -1, -1) == -1 and c.rule_direction("R3", 0.0, 1, -1) == 0
    assert c.rule_direction("R4", 0.0, 0, -1) == -1


def test_the_bar_is_the_prereg_bar():
    assert (c.N_TRIALS, c.T_BAR, c.DSR_BAR, c.MIN_TRADES, c.MIN_SESSIONS, c.COST_BP) == (75, 3.40, 0.95, 100, 40, 16.63)
    assert len(c.SOURCES) * len(c.HORIZONS) * len(c.RULES) + len(c.HORIZONS) == 75


def test_noise_does_not_pass_and_a_steady_edge_does():
    import random
    rng = random.Random(1)
    days = ["2025-%02d-%02d" % (m, d) for m in (9, 10, 11, 12) for d in range(1, 21)]
    noise = [(d, rng.gauss(-2.0, 30.0)) for d in days for _ in range(3)]
    assert not c.judge(noise, days)["passes"]
    edge = [(d, rng.gauss(25.0, 10.0)) for d in days for _ in range(3)]
    j = c.judge(edge, days)
    assert j["passes"] and j["checks"]["t_over_bonferroni"] and j["dsr"] >= 0.95
