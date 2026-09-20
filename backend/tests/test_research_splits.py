"""
Research split helpers, and the boundary that keeps them out of the live path.

The isolation test is the important one. `backend/research/` exists so phase-2
work is reproducible, but research code changes fast, is written to answer one
question, and is not held to the standards the trading engine is. If the live
engine ever imports from it, that distinction quietly stops being true.
"""
import ast
from pathlib import Path

import pytest

from research import splits


BACKEND = Path(__file__).parent.parent


# ---- the boundary -------------------------------------------------------


def _live_path_modules():
    """Every backend module the running system could reach — everything except
    the research package itself and the tests."""
    for path in BACKEND.glob("*.py"):
        yield path
    for path in (BACKEND / "strategies").rglob("*.py"):
        yield path


def _imported_names(path):
    """Top-level module names imported by a file, via either import form."""
    try:
        tree = ast.parse(path.read_text())
    except (SyntaxError, UnicodeDecodeError):
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_no_live_module_imports_research():
    """The one rule that keeps research code from becoming load-bearing.

    Checked by parsing every live module's imports rather than by grepping, so
    a name inside a string or a comment can't produce a false alarm and an
    aliased import can't hide."""
    offenders = []
    for path in _live_path_modules():
        if "research" in _imported_names(path):
            offenders.append(path.relative_to(BACKEND).as_posix())
    assert offenders == [], (
        "these live-path modules import from backend/research, which is "
        f"research-only code: {offenders}")


def test_the_isolation_test_can_actually_fail(tmp_path):
    """A guard that passes vacuously is worse than no guard. Prove the import
    scanner detects the thing it exists to detect."""
    offender = tmp_path / "pretend_live_module.py"
    offender.write_text("import research\nfrom research import splits\n")
    assert "research" in _imported_names(offender)

    innocent = tmp_path / "innocent.py"
    innocent.write_text('# research is mentioned here\nX = "research"\nimport json\n')
    assert "research" not in _imported_names(innocent)


def test_research_package_is_importable_on_its_own():
    assert splits.HELD_OUT_START == "2026-01-02"
    assert splits.EMBARGO_SESSIONS == 5


# ---- splits -------------------------------------------------------------


def _sessions(n=20, start=1):
    """n consecutive session labels in 2025-12 / 2026-01, spanning the boundary."""
    out = []
    d = start
    while len(out) < n:
        out.append(f"2025-12-{d:02d}" if d <= 31 else f"2026-01-{d-31:02d}")
        d += 1
    return out


def test_selection_and_heldout_split_at_the_named_boundary():
    sel, held = splits.selection_holdout(_sessions(20, 25))
    assert all(s < "2026-01-02" for s in sel)
    assert all(s >= "2026-01-02" for s in held)
    assert len(sel) + len(held) == 20


def test_the_split_is_chronological_not_random():
    sel, held = splits.selection_holdout(_sessions(20, 25))
    assert max(sel) < min(held), "every selection session must precede every held-out one"


def test_input_order_does_not_matter():
    shuffled = list(reversed(_sessions(20, 25)))
    sel, held = splits.selection_holdout(shuffled)
    assert sel == sorted(sel) and held == sorted(held)


def test_embargo_is_taken_out_of_selection_not_heldout():
    """Held-out is the scarcer sample, so the gap comes out of selection."""
    sel_no, held_no = splits.selection_holdout(_sessions(20, 25), embargo=0)
    sel_yes, held_yes = splits.selection_holdout(_sessions(20, 25), embargo=3)
    assert held_yes == held_no, "held-out must be untouched by the embargo"
    assert len(sel_yes) == len(sel_no) - 3
    assert max(sel_yes) < min(held_yes)


def test_an_embargo_longer_than_selection_empties_it_rather_than_wrapping():
    sel, held = splits.selection_holdout(_sessions(20, 25), embargo=99)
    assert sel == []
    assert held


def test_halves_splits_evenly_and_is_a_different_question_from_heldout():
    first, second = splits.halves(_sessions(20, 25))
    assert len(first) == 10 and len(second) == 10
    assert max(first) < min(second)
    # the halves boundary is NOT the held-out boundary
    sel, _ = splits.selection_holdout(_sessions(20, 25))
    assert len(first) != len(sel) or max(first) != max(sel)


def test_halves_handles_an_odd_count_without_losing_a_session():
    first, second = splits.halves(_sessions(21, 25))
    assert len(first) + len(second) == 21


def test_boundary_date_reports_the_realised_session_not_the_constant():
    sessions = ["2025-12-30", "2025-12-31", "2026-01-05", "2026-01-06"]
    assert splits.boundary_date(sessions) == "2026-01-05"
    assert splits.boundary_date(["2025-12-30"]) is None


def test_slice_data_keeps_only_the_requested_sessions():
    preloaded = {
        "AAA": [{"time": "2025-12-30T09:15:00", "close": 1},
                {"time": "2026-01-05T09:15:00", "close": 2}],
        "BBB": [{"time": "2026-01-05T09:15:00", "close": 3}],
    }
    picks = {"2025-12-30": {"AAA": "LONG"}, "2026-01-05": {"BBB": "LONG"}}
    candles, allowed = splits.slice_data(preloaded, picks, ["2025-12-30"])
    assert set(candles) == {"AAA"}, "a symbol with no bars in the window is dropped"
    assert len(candles["AAA"]) == 1
    assert set(allowed) == {"2025-12-30"}


def test_slice_data_does_not_mutate_the_source():
    preloaded = {"AAA": [{"time": "2025-12-30T09:15:00", "close": 1},
                         {"time": "2026-01-05T09:15:00", "close": 2}]}
    before = len(preloaded["AAA"])
    splits.slice_data(preloaded, {}, ["2025-12-30"])
    assert len(preloaded["AAA"]) == before, "slicing must not consume the cache"


def test_sessions_in_collects_every_date_once():
    preloaded = {"AAA": [{"time": "2026-01-05T09:15:00"}, {"time": "2026-01-05T09:20:00"}],
                 "BBB": [{"time": "2026-01-06T09:15:00"}]}
    assert splits.sessions_in(preloaded) == ["2026-01-05", "2026-01-06"]


def test_describe_split_flags_a_window_earlier_work_has_seen():
    seen = splits.describe_split("held-out", ["2026-01-05", "2026-02-05"])
    assert "already seen by earlier work" in seen
    clean = splits.describe_split("selection", ["2025-11-01", "2025-12-01"])
    assert "already seen" not in clean


# ---- power --------------------------------------------------------------


def test_required_trades_matches_the_reviewers_arithmetic():
    """Amendment 1: 80% power, two-sided 5%. At the old 1.41R spread a +0.25R
    edge needs ~250 trades."""
    assert splits.required_trades(1.41, 0.25) == pytest.approx(250, abs=5)


def test_required_trades_scales_with_the_square_of_the_spread():
    a = splits.required_trades(1.0, 0.25)
    b = splits.required_trades(2.0, 0.25)
    assert b == pytest.approx(4 * a, rel=0.01)


def test_a_smaller_edge_needs_disproportionately_more_trades():
    assert splits.required_trades(1.41, 0.10) > 5 * splits.required_trades(1.41, 0.25)


def test_the_testability_bar_reproduces_085_trades_per_session():
    """~297 selection sessions, +0.25R, 1.41R spread -> the reviewer's 0.85."""
    bar = splits.trades_per_session_bar(1.41, 0.25, 297)
    assert bar == pytest.approx(0.85, abs=0.03)


def test_required_trades_is_undefined_for_a_zero_edge():
    assert splits.required_trades(1.41, 0) is None
    assert splits.trades_per_session_bar(1.41, 0, 297) is None
