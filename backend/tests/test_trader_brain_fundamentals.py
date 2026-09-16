"""
trader_brain.py's new fundamentals criterion (real ROE/margin/PEG/debt-equity
via fundamentals.py, added as a tilt-only checklist item — see trader_brain's
step 8 and fundamentals.py's module docstring for why it's a tilt, not a
veto: a weak balance sheet shouldn't block an otherwise-good intraday trade).
"""
import trader_brain

_WINDOW = [{"open": 100, "high": 101, "low": 99, "close": 100, "time": "2026-01-01T10:00:00"}] * 5


def _checklist_item(side, fundamentals_score, macd_hist=0.1, rsi=55.0, always_in="long"):
    macd_v = {"hist": macd_hist, "prev_hist": 0.0}
    result = trader_brain._checklist(
        side, _WINDOW, [], [], 1.0, 1.2, "up", "uptrend", macd_v, rsi, always_in,
        None, fundamentals_score, trader_brain.DEFAULTS,
    )
    return next(i for i in result["items"] if i["key"] == "fundamentals"), result


def test_no_fundamentals_data_is_ok_and_full_size():
    item, result = _checklist_item("long", None)
    assert item["ok"] is True
    assert "no fundamentals data" in item["detail"]


def test_weak_fundamentals_trims_size_on_a_long():
    item, result = _checklist_item("long", -3.0)
    assert item["ok"] is False
    assert "trade at" in item["detail"]
    assert result["size_factor"] == trader_brain.DEFAULTS["indicator_miss_size"]


def test_weak_fundamentals_does_not_block_a_short():
    # Weak fundamentals support a SHORT — the same -3.0 score should NOT
    # trim size on the short side, since it agrees with that direction.
    item, _ = _checklist_item("short", -3.0, macd_hist=-0.1, rsi=45.0, always_in="short")
    assert item["ok"] is True


def test_mildly_negative_fundamentals_dont_trim_size():
    # -0.5 is below zero but above the -1.0 tilt threshold — shouldn't cut size.
    item, _ = _checklist_item("long", -0.5)
    assert item["ok"] is True


def test_trader_brain_signal_declares_uses_fundamentals():
    assert trader_brain.trader_brain_signal.uses_fundamentals is True
