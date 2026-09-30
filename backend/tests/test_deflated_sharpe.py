"""DSR regression tests (#132): the luck baseline must not scale with the
candidate's own Sharpe, so a real edge with enough data can pass, and a
no-edge series can't."""
import math
import random

import evaluation


def _series(mean, sd, n, seed):
    rnd = random.Random(seed)
    return [rnd.gauss(mean, sd) for _ in range(n)]


def test_strong_edge_with_enough_data_passes_at_project_trial_count():
    # per-observation Sharpe ~0.5 over 20,000 observations: t ~ 70
    out = evaluation.deflated_sharpe_ratio(_series(0.05, 0.1, 20000, 1), 119)
    assert out["dsr"] >= 0.99
    assert out["luck_baseline_sharpe"] < out["sharpe"]


def test_baseline_does_not_scale_with_the_candidates_sharpe():
    a = evaluation.deflated_sharpe_ratio(_series(0.01, 0.1, 2000, 2), 119)
    b = evaluation.deflated_sharpe_ratio(_series(0.05, 0.1, 2000, 2), 119)
    # same n, same N: same baseline whatever the candidate's Sharpe
    assert a["luck_baseline_sharpe"] == b["luck_baseline_sharpe"]
    expected = evaluation.expected_max_sharpe(119, 1 / math.sqrt(2000 - 1))
    assert abs(a["luck_baseline_sharpe"] - round(expected, 3)) < 1e-9


def test_no_edge_series_does_not_pass():
    passes = sum(evaluation.deflated_sharpe_ratio(_series(0.0, 0.1, 500, s), 119)["dsr"] >= 0.95
                 for s in range(200))
    assert passes <= 2   # the best of 119 lucky tries is what the baseline prices in


def test_needs_about_t_4_3_at_119_trials():
    # normal returns: DSR crosses 0.95 near t = E[max of 119] + 1.645 ~ 4.3
    n = 1000
    def dsr_at_t(t):
        mean = t / math.sqrt(n)            # sd 1 -> per-obs Sharpe = t/sqrt(n)
        xs = _series(0.0, 1.0, n, 7)
        m = sum(xs) / n
        sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
        xs = [(x - m) / sd + mean for x in xs]   # exact mean and sd
        return evaluation.deflated_sharpe_ratio(xs, 119)["dsr"]
    assert dsr_at_t(3.5) < 0.95
    assert dsr_at_t(5.0) > 0.95


def test_single_trial_reduces_to_ordinary_one_sided_test():
    n = 400
    xs = _series(0.0, 1.0, n, 11)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    xs = [(x - m) / sd + 2.0 / math.sqrt(n) for x in xs]   # t = 2.0 exactly
    out = evaluation.deflated_sharpe_ratio(xs, 1)
    assert abs(out["dsr"] - 0.977) < 0.01


def test_explicit_sharpe_std_still_respected():
    xs = _series(0.02, 0.1, 1000, 3)
    out = evaluation.deflated_sharpe_ratio(xs, 50, sharpe_std=0.2)
    assert abs(out["luck_baseline_sharpe"] - round(evaluation.expected_max_sharpe(50, 0.2), 3)) < 1e-9
