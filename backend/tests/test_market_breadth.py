"""
Tests for real, whole-exchange market breadth (Murphy, Technical Analysis
of the Financial Markets ch 10) — nse_feed.market_breadth() (a live TRIN
reading from NSE's own advance/decline feed, verified live against
~3,700 real NSE stocks — not this scanner's narrower NIFTY 100 universe)
and database.mcclellan_oscillator() (needs real day-over-day history, so
it must report "not enough data" honestly rather than compute a number
from too little history to mean anything).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import database


def _day(i):
    return f"2026-01-{i + 1:02d}"


def test_mcclellan_reports_not_enough_data_below_min_days():
    for i in range(10):
        database.record_market_breadth(_day(i), {"advances": 60, "declines": 40, "unchanged": 0, "total": 100})

    result = database.mcclellan_oscillator(min_days=39)

    assert result["oscillator"] is None
    assert result["days"] == 10
    assert "not enough" in result["note"] or "need at least" in result["note"]


def test_mcclellan_computes_once_enough_days_exist():
    # 40 days of consistently positive net advances -> a positive, real
    # oscillator value once both EMAs have enough history.
    for i in range(40):
        database.record_market_breadth(_day(i), {"advances": 70, "declines": 30, "unchanged": 0, "total": 100})

    result = database.mcclellan_oscillator(min_days=39)

    assert result["oscillator"] is not None
    assert result["days"] == 40


def test_mcclellan_ignores_rows_with_missing_counts():
    for i in range(39):
        database.record_market_breadth(_day(i), {"advances": 60, "declines": 40, "unchanged": 0, "total": 100})
    database.record_market_breadth(_day(39), {"advances": None, "declines": None, "unchanged": None, "total": None})

    result = database.mcclellan_oscillator(min_days=39)

    assert result["days"] == 39  # the null row is excluded, not counted toward min_days


def test_record_market_breadth_is_idempotent_per_day():
    database.record_market_breadth("2026-02-01", {"advances": 50, "declines": 50, "unchanged": 0, "total": 100})
    database.record_market_breadth("2026-02-01", {"advances": 80, "declines": 20, "unchanged": 0, "total": 100})

    with database._conn() as c:
        rows = c.execute(
            "SELECT advances FROM market_breadth_daily WHERE session_date = ?", ("2026-02-01",)
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["advances"] == 80  # the later write wins, not a duplicate row
