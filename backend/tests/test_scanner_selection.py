"""How the scanner chooses the day's active list (README section 91).

"liquidity" mode: the most-traded eligible stocks, chosen once per session and
kept all day. "score" mode: the old ranked list, re-chosen every scan.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scanner  # noqa: E402


def _row(sym, turnover, score=50.0, side="SHORT", trend="down"):
    """`side` is the old score's stronger side, which a scan row carries as
    score_side; the row's own side is empty (README section 115)."""
    return {"symbol": sym, "turnover_cr": turnover, "score": score, "final_score": score,
            "side": None, "score_side": side, "daily_trend": trend, "excluded": None}


CFG = {"active_count": 3, "selection": "liquidity", "freeze_min_coverage": 0.9,
       "min_score": 20, "counter_trend_active_count": 2}


def test_the_most_traded_eligible_stocks_are_chosen_whatever_their_score_or_side():
    eligible = [_row("A", 100, score=90), _row("B", 900, score=5, side="LONG", trend="down"),
                _row("C", 500, score=30), _row("D", 700, score=0), _row("E", 50, score=99)]
    assert scanner.select_liquid(eligible, CFG) == ["B", "D", "C"]


def test_ties_are_broken_by_symbol_so_the_list_is_reproducible():
    eligible = [_row("ZED", 100), _row("ABC", 100), _row("MID", 100), _row("LOW", 10)]
    assert scanner.select_liquid(eligible, CFG) == ["ABC", "MID", "ZED"]
    assert scanner.select_liquid(list(reversed(eligible)), CFG) == ["ABC", "MID", "ZED"]


def test_a_missing_turnover_ranks_last_rather_than_failing():
    eligible = [_row("A", None), _row("B", 10), _row("C", 20), _row("D", 30)]
    assert scanner.select_liquid(eligible, CFG) == ["D", "C", "B"]


def test_the_list_is_fixed_for_the_session_and_does_not_rotate():
    sc = scanner.Scanner(CFG)
    first = [_row("A", 900), _row("B", 800), _row("C", 700), _row("D", 600)]
    active, fixed = sc.day_list_for("2026-09-29", first, n_rows=100, n_universe=100, now=1.0)
    assert active == ["A", "B", "C"] and fixed
    # later in the day D trades far more; the list does not change
    later = [_row("A", 900), _row("B", 800), _row("C", 700), _row("D", 5000)]
    active, fixed = sc.day_list_for("2026-09-29", later, n_rows=100, n_universe=100, now=2.0)
    assert active == ["A", "B", "C"] and fixed and sc.day_list["fixed_ts"] == 1.0


def test_a_stock_that_stops_being_eligible_is_dropped_not_replaced():
    sc = scanner.Scanner(CFG)
    sc.day_list_for("2026-09-29", [_row("A", 900), _row("B", 800), _row("C", 700), _row("D", 600)], 100, 100)
    # B is excluded later (say, a results announcement): the list shrinks, D does not step in
    active, _ = sc.day_list_for("2026-09-29", [_row("A", 900), _row("C", 700), _row("D", 600)], 100, 100)
    assert active == ["A", "C"]


def test_a_new_session_chooses_a_new_list():
    sc = scanner.Scanner(CFG)
    sc.day_list_for("2026-09-29", [_row("A", 900), _row("B", 800), _row("C", 700), _row("D", 600)], 100, 100)
    active, fixed = sc.day_list_for("2026-09-30", [_row("A", 1), _row("B", 2), _row("C", 3), _row("D", 4)], 100, 100)
    assert active == ["D", "C", "B"] and fixed and sc.day_list["session"] == "2026-09-30"


def test_the_list_is_not_fixed_while_too_much_of_the_universe_is_missing():
    sc = scanner.Scanner(CFG)
    thin = [_row("A", 900), _row("C", 700), _row("D", 600)]            # B's download failed
    active, fixed = sc.day_list_for("2026-09-29", thin, n_rows=80, n_universe=100)
    assert active == ["A", "C", "D"] and not fixed and sc.day_list is None
    full = [_row("A", 900), _row("B", 800), _row("C", 700), _row("D", 600)]
    active, fixed = sc.day_list_for("2026-09-29", full, n_rows=100, n_universe=100)
    assert active == ["A", "B", "C"] and fixed


def test_liquidity_is_the_default_and_score_mode_is_still_available():
    import config
    assert scanner.selection_mode(config.SCANNER) == "liquidity"
    assert scanner.selection_mode({"selection": "score"}) == "score"
    assert scanner.selection_mode({}) == "liquidity"
    # the old ranked selection is unchanged
    eligible = [_row("A", 1, score=90, side="SHORT", trend="down"), _row("B", 1, score=80, side="LONG", trend="up"),
                _row("C", 1, score=70, side="SHORT", trend="up"), _row("D", 1, score=10)]
    assert scanner.select_active(eligible, "risk-off", CFG) == ["A", "B"]


def test_the_rule_the_dashboard_shows_names_the_count():
    assert "25 most-traded" in scanner.LIQUIDITY_RULE.format(n=25)
    assert "kept all day" in scanner.LIQUIDITY_RULE.format(n=25)
