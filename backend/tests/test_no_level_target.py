"""#40: with no support/resistance beyond the entry there is no target, so
the R:R item fails, instead of a gross 2R target judged net of costs. The old
behaviour stays reachable as an explicit number, for the before/after run."""
import pytest

import trader_brain
from tests.test_stop_width import _plan


def _rrr(out):
    return next(i for i in out["items"] if i["key"] == "rrr")


def test_the_default_is_no_formulaic_target():
    assert trader_brain.DEFAULTS["rrr_without_level"] is None


def test_no_level_beyond_means_no_target_and_a_failed_rrr_item():
    out = _plan("long", 99.0, 100.5, 100.0, {})        # _plan passes no levels at all
    item = _rrr(out)
    assert out["target"] is None and out["rrr"] is None
    assert item["ok"] is False and "beyond the entry to aim a target at" in item["detail"]
    assert out["passed"] is False


def test_the_same_holds_for_a_short():
    out = _plan("short", 99.5, 101.0, 100.0, {})
    assert out["target"] is None and _rrr(out)["ok"] is False


def test_an_explicit_number_restores_the_old_gross_target():
    out = _plan("long", 99.0, 100.5, 100.0, {"rrr_without_level": 2.0})
    risk = out["entry"] - out["stop"]
    assert out["target"] == pytest.approx(out["entry"] + 2.0 * risk)
    assert "2R gross, no level beyond" in _rrr(out)["detail"]
    # ...and it is judged net of costs, so 2.0 gross nets under 2.0
    assert out["rrr"] < 2.0
