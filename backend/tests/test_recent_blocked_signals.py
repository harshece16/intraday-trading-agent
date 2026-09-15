"""
database.recent_blocked_signals() parses the confidence-gate breakdown back
out of the plain-English activity message trading_engine._blocked() writes
(built from confidence.score_trade()'s own f-strings). This is a regex
against generated prose, not a structured column, so it needs its own
coverage — including the case that actually broke a naive "match to the
final ')'" pattern in review: a Scorecard criterion name containing its own
parentheses inside the system-multiplier reason.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import database


def test_confidence_gate_message_parses():
    database.record_activity(
        "blocked",
        "Hanging Man (short) signal skipped — confidence 53/100 below the 60 bar "
        "(Local setup scored 89/100, scaled by a 0.60x system-evidence factor "
        "(Scorecard has no failures yet, but not enough data to confirm a real "
        "edge either — confidence is capped until it does.))",
        symbol="MUTHOOTFIN",
        level="warn",
    )
    [row] = database.recent_blocked_signals()
    assert row["symbol"] == "MUTHOOTFIN"
    assert row["setup"] == "Hanging Man (short)"
    assert row["reason_type"] == "confidence_gate"
    assert row["final_score"] == 53
    assert row["min_confidence_bar"] == 60
    assert row["local_setup_score"] == 89
    assert row["system_multiplier"] == 0.60
    assert "not enough data" in row["system_multiplier_reason"]


def test_confidence_gate_message_with_parens_in_reason_still_parses():
    # The system-multiplier reason itself can contain parens (a Scorecard
    # criterion name like "Predictive skill (Information Coefficient)") —
    # this is the case that would break a non-greedy or naive regex.
    database.record_activity(
        "blocked",
        "Three Black Crows (short) signal skipped — confidence 25/100 below the 60 bar "
        "(Local setup scored 100/100, scaled by a 0.25x system-evidence factor "
        "(Scorecard currently FAILS on: Predictive skill (Information Coefficient) — "
        "a strong local setup can't outweigh proven-absent system edge.))",
        symbol="MAZDOCK",
        level="warn",
    )
    [row] = database.recent_blocked_signals()
    assert row["reason_type"] == "confidence_gate"
    assert row["local_setup_score"] == 100
    assert row["system_multiplier"] == 0.25
    assert row["system_multiplier_reason"].endswith("proven-absent system edge.")


def test_confidence_gate_parses_a_fractional_bar():
    # min_confidence_to_trade is an int today, but nothing in config.py enforces that —
    # a future tuning pass (see backend/tune_entry_params.py) could land a fractional
    # threshold. The bar group must not silently stop matching if that happens.
    database.record_activity(
        "blocked",
        "Bullish Marubozu (long) signal skipped — confidence 40/100 below the 45.5 bar "
        "(Local setup scored 67/100, scaled by a 0.60x system-evidence factor "
        "(Scorecard has no failures yet, but not enough data to confirm a real edge "
        "either — confidence is capped until it does.))",
        symbol="TCS",
        level="warn",
    )
    [row] = database.recent_blocked_signals()
    assert row["reason_type"] == "confidence_gate"
    assert row["min_confidence_bar"] == 45.5


def test_non_confidence_block_falls_back_to_raw_reason():
    database.record_activity(
        "blocked",
        "Bullish Marubozu (long) signal skipped — already at the max of 3 open positions",
        symbol="SBIN",
        level="warn",
    )
    [row] = database.recent_blocked_signals()
    assert row["reason_type"] == "other"
    assert row["reason"] == "already at the max of 3 open positions"
    assert "final_score" not in row


def test_window_and_limit_respected():
    import time

    old_ts = time.time() - 999999
    database.record_activity("blocked", "Old (long) signal skipped — stale", symbol="OLD", level="warn", ts=old_ts)
    database.record_activity("blocked", "New (long) signal skipped — fresh", symbol="NEW", level="warn")
    rows = database.recent_blocked_signals(hours=24)
    assert [r["symbol"] for r in rows] == ["NEW"]
