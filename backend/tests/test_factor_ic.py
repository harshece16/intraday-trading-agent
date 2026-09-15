"""
Regression tests for a real statistical bug found while running Chaywanaprash
(§29) over the live journal: database.factor_ic() paired every raw
scan_rows row as an independent (session, symbol) observation, but a
symbol is scanned repeatedly through a session (every 5-60 min) — all
sharing one session_date. Verified live: RELIANCE had 59 rows for a single
Friday (market-closed preview scans), every one identical
(final_score=58.1, chg_pct=-1.3). The old code counted those 59 duplicate
rows as 59 independent data points feeding a rank correlation — a
pseudo-replication bug that inflated a real session's worth of evidence
(~1 genuine transition per symbol so far) into an apparent 8,091 "pairs",
and made the Scorecard's Information Coefficient check (which gates real
trading via confidence.py's system-evidence multiplier) falsely confident.

dimag_ki_batti() is new: which of the platform's real, already-tagged
swing patterns currently shows the strongest genuine result, using the
same corrected, deduplicated methodology — see its docstring for why it
deliberately never invents a winner.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import database


def _insert_scan_row(scan_id, session_date, symbol, final_score, chg_pct, swing_pattern=None):
    with database._conn() as c:
        c.execute(
            "INSERT INTO scan_rows (scan_id, session_date, symbol, final_score, chg_pct, swing_pattern) "
            "VALUES (?,?,?,?,?,?)",
            (scan_id, session_date, symbol, final_score, chg_pct, swing_pattern),
        )


def test_factor_ic_dedupes_repeated_intraday_scans_of_one_session():
    # RELIANCE-shaped scenario: 10 identical rows for session A (repeated
    # market-closed preview scans), then rows for session B. Without dedup
    # this alone would produce 9 (session-A-A) pairs; with dedup it must
    # collapse to at most 1 (A -> B) pair for this symbol.
    for i in range(10):
        _insert_scan_row(i, "2026-01-02", "DEDUPTEST", final_score=50.0, chg_pct=-1.0)
    _insert_scan_row(10, "2026-01-06", "DEDUPTEST", final_score=50.0, chg_pct=2.0)

    with database._conn() as c:
        rows = c.execute(
            "SELECT id, session_date, symbol, final_score AS f, chg_pct FROM scan_rows "
            "WHERE symbol='DEDUPTEST' ORDER BY symbol, session_date, id"
        ).fetchall()
    by_symbol = database._last_reading_per_symbol_session(rows)

    assert by_symbol["DEDUPTEST"] == [("2026-01-02", 50.0, -1.0), ("2026-01-06", 50.0, 2.0)]


def test_factor_ic_uses_latest_row_not_first_within_a_session():
    # If a symbol's score genuinely changes across scans within the same
    # session_date (a real intraday update, not a closed-market repeat),
    # the LAST read of that session is what should represent it — not the
    # first, and not an average that would blur a real update away.
    _insert_scan_row(20, "2026-01-02", "LATESTTEST", final_score=10.0, chg_pct=-5.0)
    _insert_scan_row(21, "2026-01-02", "LATESTTEST", final_score=90.0, chg_pct=-5.0)
    _insert_scan_row(22, "2026-01-06", "LATESTTEST", final_score=50.0, chg_pct=3.0)

    with database._conn() as c:
        rows = c.execute(
            "SELECT id, session_date, symbol, final_score AS f, chg_pct FROM scan_rows "
            "WHERE symbol='LATESTTEST' ORDER BY symbol, session_date, id"
        ).fetchall()
    by_symbol = database._last_reading_per_symbol_session(rows)

    assert by_symbol["LATESTTEST"][0] == ("2026-01-02", 90.0, -5.0)


def test_dimag_ki_batti_never_invents_a_winner_with_too_little_data():
    result = database.dimag_ki_batti(min_pairs=1000)  # impossible bar given test data
    assert result["winner"] is None
    assert "too early" in result["note"]


def test_dimag_ki_batti_parses_multi_pattern_rows_and_credits_each_name():
    pattern_json = json.dumps([
        {"name": "Double Top", "side": "short", "stop": 100.0, "level": 90.0},
        {"name": "Head and Shoulders Top", "side": "short", "stop": 100.0, "level": 88.0},
    ])
    for i, (session, score, chg) in enumerate([
        ("2026-02-01", 10, -3.0), ("2026-02-02", 20, -2.0), ("2026-02-03", 30, -1.0),
        ("2026-02-04", 40, 1.0), ("2026-02-05", 50, 2.0), ("2026-02-06", 60, 3.0),
    ]):
        _insert_scan_row(100 + i, session, "MULTIPAT", final_score=score, chg_pct=chg,
                         swing_pattern=pattern_json)

    result = database.dimag_ki_batti(min_pairs=3)

    assert "Double Top" in result["by_pattern"]
    assert "Head and Shoulders Top" in result["by_pattern"]
    # Both patterns fired on every one of these rows -> identical IC.
    assert result["by_pattern"]["Double Top"]["ic"] == result["by_pattern"]["Head and Shoulders Top"]["ic"]


def test_dimag_ki_batti_picks_the_highest_ic_among_qualifying_patterns():
    # Pattern A: score and next-day change move together (perfect positive rank correlation).
    for i, (session, score, chg) in enumerate([
        ("2026-03-01", 10, -3.0), ("2026-03-02", 20, -2.0), ("2026-03-03", 30, -1.0),
        ("2026-03-04", 40, 1.0), ("2026-03-05", 50, 2.0), ("2026-03-06", 60, 3.0),
    ]):
        _insert_scan_row(200 + i, session, "PATA", final_score=score, chg_pct=chg,
                         swing_pattern=json.dumps([{"name": "PatternA", "side": "long"}]))
    # Pattern B: score and next-day change actively disagree (perfect
    # negative rank correlation) — a real relationship, just the wrong sign,
    # so it must lose to Pattern A's clean positive one.
    for i, (session, score, chg) in enumerate([
        ("2026-03-01", 60, -3.0), ("2026-03-02", 50, -2.0), ("2026-03-03", 40, -1.0),
        ("2026-03-04", 30, 1.0), ("2026-03-05", 20, 2.0), ("2026-03-06", 10, 3.0),
    ]):
        _insert_scan_row(300 + i, session, "PATB", final_score=score, chg_pct=chg,
                         swing_pattern=json.dumps([{"name": "PatternB", "side": "long"}]))

    result = database.dimag_ki_batti(min_pairs=3)

    assert result["winner"]["pattern"] == "PatternA"
    assert result["winner"]["ic"] == 1.0
