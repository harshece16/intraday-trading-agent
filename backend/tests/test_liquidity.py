"""liquidity.py — the entry-time order-book check. Pure assess() on built
depth dicts, plus check()'s paper/live behaviour when no depth is readable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import database
import liquidity


def _book(bid, ask, qty=1000, levels=5, step=0.05):
    return {"buy": [{"price": round(bid - i * step, 2), "quantity": qty, "orders": 3} for i in range(levels)],
            "sell": [{"price": round(ask + i * step, 2), "quantity": qty, "orders": 3} for i in range(levels)]}


def test_spread_cap_is_derived_from_the_cost_model():
    assert liquidity.max_spread_bp() == 2 * config.COSTS["slippage_pct"] * 100 == 6.0


def test_a_tight_deep_book_passes():
    r = liquidity.assess(_book(1000.00, 1000.20), "LONG", 50)
    assert r["ok"] is True, r["reason"]
    assert r["spread_bp"] == 2.0
    assert r["entry_depth"] == r["exit_depth"] == 5000


def test_a_wide_spread_is_refused():
    r = liquidity.assess(_book(1000.00, 1001.00), "LONG", 50)   # 10 bp
    assert r["ok"] is False and "spread is 10.0 bp" in r["reason"]


def test_an_order_bigger_than_five_levels_is_refused():
    r = liquidity.assess(_book(1000.00, 1000.10, qty=10), "LONG", 60)
    assert r["ok"] is False and "hold only 50" in r["reason"]


def test_walking_the_book_past_the_slippage_is_refused():
    # Tight top of book but a thin best level: filling 400 reaches far down the asks.
    book = _book(1000.00, 1000.10, qty=100, step=0.40)
    r = liquidity.assess(book, "LONG", 400)
    assert r["ok"] is False and "walks the book" in r["reason"]


def test_a_thin_exit_side_is_refused_even_when_entry_is_deep():
    book = _book(1000.00, 1000.10, qty=1000)
    for lv in book["buy"]:
        lv["quantity"] = 20          # a long exits into the bids: 100 total
    r = liquidity.assess(book, "LONG", 50)
    assert r["ok"] is False and "exit side holds 100" in r["reason"]


def test_a_short_enters_into_the_bids():
    book = _book(1000.00, 1000.10, qty=1000)
    for lv in book["sell"]:
        lv["quantity"] = 20
    r = liquidity.assess(book, "SHORT", 50)        # a short exits into the asks
    assert r["entry_depth"] == 5000 and r["exit_depth"] == 100 and r["ok"] is False


def test_an_empty_side_is_refused():
    assert liquidity.assess({"buy": [], "sell": _book(1, 1.01)["sell"]}, "LONG", 1)["ok"] is False


def test_no_depth_lets_paper_through_but_never_live(monkeypatch):
    recorded = []
    monkeypatch.setattr(database, "record_liquidity_check", lambda *a: recorded.append(a))
    ok_paper, _, res = liquidity.check("TESTCO", "LONG", 10, 100.0, paper_mode=True, fetch=lambda s: None)
    ok_live, reason, _ = liquidity.check("TESTCO", "LONG", 10, 100.0, paper_mode=False, fetch=lambda s: None)
    assert ok_paper is True and res["status"] == "unchecked"
    assert ok_live is False and "live order needs a checked book" in reason
    assert len(recorded) == 2           # both readings are journaled


def test_a_depth_read_error_is_treated_as_unchecked(monkeypatch):
    monkeypatch.setattr(database, "record_liquidity_check", lambda *a: None)
    def boom(symbol):
        raise RuntimeError("Kite down")
    assert liquidity.check("TESTCO", "LONG", 10, 100.0, paper_mode=False, fetch=boom)[0] is False


def test_readings_round_trip_through_the_journal():
    r = {**liquidity.assess(_book(1000.00, 1000.20), "LONG", 50), "status": "checked"}
    database.record_liquidity_check("TESTCO", "LONG", 50, 1000.1, "paper", r)
    row = database.recent_liquidity_checks(limit=1)[0]
    assert row["symbol"] == "TESTCO" and row["ok"] == 1 and row["spread_bp"] == 2.0 and row["exit_depth"] == 5000
