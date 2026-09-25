"""The Scorecard's backtest-evidence row: the live confidence gate now sees
what two years of backtests measured about the live rule set, not only the
handful of paper trades. Test A measured the live checklist losing
significantly, so the gate's system multiplier falls to 0.25x and no
setup can reach the 60 bar on its own."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import confidence
import database
import evaluation

LIVE = {**config.STRATEGY_PARAMS[config.STRATEGY], "interval": config.CANDLE_INTERVAL}


def _ev(net_r, t, halves, applies=None):
    return {"applies_to": applies or {"strategy": "sahab_dimaag", "entry_mode": "checklist", "interval": "5m"},
            "primary": {"label": "x", "trades": 201, "sessions": 495, "net_r": net_r, "t": t,
                        "net_r_halves": halves, "source": "test"}}


def test_the_committed_evidence_fails_the_live_rule_set():
    row = evaluation.backtest_evidence_row(evaluation.load_backtest_evidence(), config.STRATEGY, LIVE)
    assert row["status"] == "fail"
    assert "-0.356R" in row["detail"] and "t = -3.59" in row["detail"]


def test_pass_needs_significant_profit_in_both_halves():
    row = lambda *a: evaluation.backtest_evidence_row(_ev(*a), "sahab_dimaag", {"entry_mode": "checklist", "interval": "5m"})
    assert row(0.2, 2.5, [0.1, 0.3])["status"] == "pass"
    assert row(0.2, 2.5, [0.1, -0.1])["status"] == "not_enough_data"     # one half negative
    assert row(0.05, 0.8, [0.1, 0.0])["status"] == "not_enough_data"     # not significant
    assert row(-0.1, -1.5, [-0.1, -0.1])["status"] == "not_enough_data"  # a loss, but not significant
    assert row(-0.3, -3.0, [-0.3, -0.3])["status"] == "fail"


def test_evidence_for_a_different_configuration_does_not_grade_the_live_one():
    ev = _ev(-0.3, -3.0, [-0.3, -0.3])
    for live in ({"entry_mode": "confluence", "interval": "5m"}, {"entry_mode": "checklist", "interval": "15m"}):
        r = evaluation.backtest_evidence_row(ev, "sahab_dimaag", live)
        assert r["status"] == "not_enough_data" and "Backtest the live configuration" in r["detail"]
    assert evaluation.backtest_evidence_row(ev, "sma_crossover", {"entry_mode": "checklist", "interval": "5m"})["status"] \
        == "not_enough_data"


def test_the_live_scorecard_carries_the_row_and_the_backtest_scorecard_does_not():
    live = database.journal_summary()["scorecard"]
    bt = database.journal_summary(include_backtest_evidence=False)["scorecard"]
    assert any(r["criterion"] == "Backtest evidence for the live rule set" for r in live)
    assert not any(r["criterion"] == "Backtest evidence for the live rule set" for r in bt)


def test_with_the_evidence_no_setup_reaches_the_60_bar():
    scorecard = database.journal_summary()["scorecard"]
    assert confidence._system_multiplier(scorecard)["multiplier"] == 0.25
    perfect = {"bull_score": 30.0, "bear_score": 0.0, "confirmations": ["a", "b", "c", "d", "e"], "adx": 60}
    s = confidence.score_trade(perfect, "LONG", scorecard)
    assert s["score"] <= 25 < config.RISK["min_confidence_to_trade"]
