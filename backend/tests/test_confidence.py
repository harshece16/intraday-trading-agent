"""
Regression coverage for confidence.py's system-evidence gate — the
mechanism that's supposed to cap confidence low whenever the Dimaag
Scorecard hasn't proven a real edge, now applied to cash equity as well as
F&O (see trading_engine._try_enter). This is the exact logic a multi-expert
review found was silently NOT gating cash equity before this fix; a
regression here would silently reopen that gap.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import confidence

ALL_PASS = [
    {"criterion": "Trading edge (expectancy)", "status": "pass", "detail": ""},
    {"criterion": "Statistical significance (Deflated Sharpe Ratio)", "status": "pass", "detail": ""},
    {"criterion": "Predictive skill (Information Coefficient)", "status": "pass", "detail": ""},
]
ONE_FAIL = [
    {"criterion": "Trading edge (expectancy)", "status": "pass", "detail": ""},
    {"criterion": "Statistical significance (Deflated Sharpe Ratio)", "status": "pass", "detail": ""},
    {"criterion": "Predictive skill (Information Coefficient)", "status": "fail", "detail": ""},
]
PENDING = [
    {"criterion": "Trading edge (expectancy)", "status": "not_enough_data", "detail": ""},
    {"criterion": "Statistical significance (Deflated Sharpe Ratio)", "status": "not_enough_data", "detail": ""},
    {"criterion": "Predictive skill (Information Coefficient)", "status": "not_enough_data", "detail": ""},
]

PERFECT_ANALYSIS = {
    "bull_score": 20.0, "bear_score": 0.0,
    "confirmations": ["trend", "momentum", "levels", "volume"],
    "adx": 40,
}
WEAK_ANALYSIS = {"bull_score": 6.0, "bear_score": 5.0, "confirmations": [], "adx": 5}


def test_system_multiplier_all_pass():
    assert confidence._system_multiplier(ALL_PASS)["multiplier"] == 1.0


def test_system_multiplier_any_fail_caps_low():
    assert confidence._system_multiplier(ONE_FAIL)["multiplier"] == 0.25


def test_system_multiplier_pending_is_between():
    assert confidence._system_multiplier(PENDING)["multiplier"] == 0.5


def test_system_multiplier_empty_scorecard_is_unproven():
    assert confidence._system_multiplier([])["multiplier"] == 0.25


def test_perfect_setup_still_blocked_when_scorecard_fails():
    # This is the exact scenario the cash-equity gate fix depends on: a
    # locally flawless checklist read must NOT be enough to trade when the
    # system hasn't proven a real edge yet.
    conf = confidence.score_trade(PERFECT_ANALYSIS, "LONG", ONE_FAIL)
    assert conf["local_setup"]["score"] == 100
    assert conf["score"] == 25
    assert conf["score"] < 60  # below config.RISK/FNO's default min_confidence_to_trade


def test_perfect_setup_passes_when_scorecard_all_pass():
    conf = confidence.score_trade(PERFECT_ANALYSIS, "LONG", ALL_PASS)
    assert conf["score"] == 100
    assert conf["score"] >= 60


def test_weak_setup_blocked_even_with_proven_edge():
    conf = confidence.score_trade(WEAK_ANALYSIS, "LONG", ALL_PASS)
    assert conf["score"] < 60


def test_missing_analysis_scores_zero_not_crash():
    conf = confidence.score_trade({}, "LONG", ALL_PASS)
    assert conf["score"] == 0
    assert conf["local_setup"]["score"] == 0
