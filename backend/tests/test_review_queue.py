"""
The manual review queue (review_queue.py, TradingEngine.approve_review).

What must hold, because an approval can place a real order:
- a card is offered only for a setup that failed exactly ONE required
  checklist item (or passed and was stopped only by the confidence gate),
  inside the entry window, with a stop and target the price hasn't passed;
- approving overrides only that gate — every risk limit is re-checked;
- live mode never places an order without explicit confirmation;
- an expired or already-decided card can't be approved;
- every card and decision is journaled.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import config
import data_provider
import database
import liquidity
import review_queue
import trading_engine
from state import AppState, _new_position

IST = review_queue.IST
SYMBOL = "TESTCO"
KEYS = ["pattern", "sr", "cost", "volume", "dow", "rrr"]
BARS = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}] * 30


def plan(failing=("rrr",), stop=98.0, target=106.0, side="long"):
    items = [{"key": k, "label": f"{k} label", "ok": k not in failing, "detail": f"{k} detail", "required": True}
             for k in KEYS]
    return {"side": side, "items": items, "passed": not failing, "pattern": "Hammer", "entry": 100.0,
            "stop": stop, "target": target, "rrr": 1.0, "size_factor": 1.0}


def analysis(long_plan, bar_time="2026-09-24T10:15:00+05:30"):
    return {"entry_mode": "checklist", "setup": "Hammer", "bar_time": bar_time,
            "checklist": {"long": long_plan, "short": None},
            "bull_score": 8.0, "bear_score": 2.0, "confirmations": ["trend", "levels", "volume"], "adx": 30}


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setitem(config.REVIEW_QUEUE, "enabled", True)
    monkeypatch.setattr(review_queue, "now_ist", lambda: datetime(2026, 9, 24, 10, 20, tzinfo=IST))
    monkeypatch.setattr(liquidity, "check", lambda *a, **k: (True, None, {}))
    state = AppState(watchlist=[], paper_mode=True)
    eng = trading_engine.TradingEngine(state)
    state.positions[SYMBOL] = _new_position()
    state.market = {"bias": "neutral", "reasons": []}
    state.market_status = "open"
    return eng


def offer(eng, p=None, bar_time="2026-09-24T10:15:00+05:30"):
    eng._offer_near_misses(SYMBOL, 100.0, BARS, analysis(p or plan(), bar_time))
    return eng.review_queue.snapshot()["cards"]


# ---- the card ---------------------------------------------------------------

def test_single_blocker_only_when_exactly_one_required_item_fails():
    assert review_queue.single_blocker(plan(failing=())) is None
    assert review_queue.single_blocker(plan(failing=("rrr",)))["key"] == "rrr"
    assert review_queue.single_blocker(plan(failing=("rrr", "volume"))) is None


def test_card_math_matches_the_checklists_net_rrr():
    card = review_queue.build_card(SYMBOL, "LONG", plan(), {"key": "rrr", "label": "l", "detail": "d"},
                                   100.0, 0.166, 10, now=datetime(2026, 9, 24, 10, 20, tzinfo=IST))
    rrr = (6 - 0.166) / (2 + 0.166)
    assert card["net_rrr"] == round(rrr, 2)
    assert card["breakeven_win_rate"] == round(1 / (1 + rrr), 3)
    assert card["expected_r"] == round(0.32 * rrr - 0.68, 2)
    assert card["risk_rs"] == 20.0 and card["reward_rs"] == 60.0


def test_a_target_that_does_not_cover_costs_has_no_breakeven():
    card = review_queue.build_card(SYMBOL, "LONG", plan(target=100.1), {"key": "rrr", "label": "l", "detail": "d"},
                                   100.0, 0.166, 10)
    assert card["net_rrr"] < 0 and card["breakeven_win_rate"] is None
    assert "doesn't cover" in card["verdict"]


# ---- offering ---------------------------------------------------------------

def test_one_card_per_stock_side_and_day_and_it_is_journaled(engine):
    cards = offer(engine)
    assert len(cards) == 1 and cards[0]["blocker"]["key"] == "rrr" and cards[0]["status"] == "pending"
    assert len(offer(engine)) == 1                      # the same setup again: not re-asked
    assert [c["status"] for c in database.reviews_on("2026-09-24")] == ["pending"]


@pytest.mark.parametrize("case", ["disabled", "two_failures", "after_cutoff", "no_target", "past_stop"])
def test_no_card_when_it_could_not_be_taken(engine, monkeypatch, case):
    p, bar_time = plan(), "2026-09-24T10:15:00+05:30"
    if case == "disabled":
        monkeypatch.setitem(config.REVIEW_QUEUE, "enabled", False)
    elif case == "two_failures":
        p = plan(failing=("rrr", "volume"))
    elif case == "after_cutoff":
        bar_time = "2026-09-24T14:45:00+05:30"
    elif case == "no_target":
        p = plan(target=None)
    elif case == "past_stop":
        p = plan(stop=101.0)
    assert offer(engine, p, bar_time) == []


def test_no_card_when_another_rule_would_stop_it_anyway(engine):
    engine.state.market = {"bias": "risk-off", "reasons": ["weak"]}
    assert offer(engine) == []


def test_confidence_gate_block_is_offered_as_a_card(engine, monkeypatch):
    monkeypatch.setattr(database, "journal_summary",
                        lambda: {"scorecard": [{"criterion": "x", "status": "fail", "detail": ""}]})
    entered = engine._try_enter(SYMBOL, "LONG", 100.0, BARS, analysis(plan(failing=())))
    assert entered is False
    [card] = engine.review_queue.snapshot()["cards"]
    assert card["blocker"]["key"] == "confidence"


# ---- deciding ---------------------------------------------------------------

def approve_ready(engine, monkeypatch, ltp=100.5):
    monkeypatch.setattr(data_provider, "get_ltp", lambda s: ltp)
    monkeypatch.setattr(database, "new_position_id", lambda: "pos-manual")
    [card] = offer(engine)
    return card


def test_approval_places_the_entry_with_the_cards_stop_and_target(engine, monkeypatch):
    card = approve_ready(engine, monkeypatch)
    result = engine.approve_review(card["id"])
    assert result["ok"] and result["status"] == "approved" and result["qty"] > 0
    pos = engine.state.positions[SYMBOL]
    assert pos["quantity"] == result["qty"] and pos["stop_price"] == 98.0 and pos["target_price"] == 106.0
    assert pos["position_id"] == "pos-manual"
    assert engine.state.strategy_state[SYMBOL]["entries_today"] == 1
    assert engine.risk.open_positions_count == 1
    [row] = database.reviews_on("2026-09-24")
    assert row["status"] == "approved" and row["position_id"] == "pos-manual"
    assert engine.approve_review(card["id"])["status"] == "approved"   # a second click does nothing
    assert engine.state.positions[SYMBOL]["quantity"] == result["qty"]


def test_live_mode_never_orders_without_explicit_confirmation(engine, monkeypatch):
    card = approve_ready(engine, monkeypatch)
    engine.state.paper_mode = False
    monkeypatch.setattr(engine, "_execute", lambda *a, **k: pytest.fail("no order without confirm_live"))
    result = engine.approve_review(card["id"])
    assert not result["ok"] and result["status"] == "pending"
    assert engine.review_queue.get(card["id"])["status"] == "pending"


@pytest.mark.parametrize("why", ["price_past_stop", "max_positions", "daily_loss", "already_traded", "market_closed"])
def test_approval_still_obeys_every_risk_limit(engine, monkeypatch, why):
    card = approve_ready(engine, monkeypatch, ltp=97.5 if why == "price_past_stop" else 100.5)
    if why == "max_positions":
        engine.risk.open_positions_count = config.RISK["max_open_positions"]
    elif why == "daily_loss":
        monkeypatch.setattr(engine.risk, "daily_loss_limit_hit", lambda: True)
    elif why == "already_traded":
        engine.state.strategy_state[SYMBOL] = {"entries_today": 1, "entry_day": "2026-09-24"}
    elif why == "market_closed":
        engine.state.market_status = "closed"
    result = engine.approve_review(card["id"])
    assert not result["ok"] and result["status"] == "refused"
    assert engine.state.positions[SYMBOL]["quantity"] == 0


def test_expired_card_cannot_be_approved(engine, monkeypatch):
    card = approve_ready(engine, monkeypatch)
    engine.review_queue.cards[card["id"]]["expires_ts"] = 0
    result = engine.approve_review(card["id"])
    assert result["status"] == "expired" and engine.state.positions[SYMBOL]["quantity"] == 0


def test_reject_closes_the_card(engine, monkeypatch):
    card = approve_ready(engine, monkeypatch)
    assert engine.reject_review(card["id"])["status"] == "rejected"
    assert engine.approve_review(card["id"])["status"] == "rejected"
    assert engine.state.positions[SYMBOL]["quantity"] == 0


def test_unknown_card():
    state = AppState(watchlist=[], paper_mode=True)
    eng = trading_engine.TradingEngine(state)
    assert eng.approve_review("nope")["status"] is None


# ---- the shared entry-window rule ------------------------------------------

def test_entry_window_open_matches_the_signals_rule():
    import trader_brain
    p = {"no_entry_before": "09:30", "last_entry_time": "14:30", "no_entry_windows": [["12:00", "13:00"]]}
    assert not trader_brain.entry_window_open("09:25", p)
    assert trader_brain.entry_window_open("09:30", p)
    assert not trader_brain.entry_window_open("12:15", p)
    assert trader_brain.entry_window_open("13:00", p)
    assert not trader_brain.entry_window_open("14:30", p)


def test_trader_brain_signal_runs_end_to_end_on_a_session_of_bars():
    """Regression: extracting entry_window_open() once dropped a variable the
    signal still used further down (`blocked_window`), and every stock's
    evaluation raised NameError. No unit test ran the full signal, so the
    suite stayed green; the running engine is what caught it."""
    import math
    from datetime import timedelta
    import trader_brain
    start = datetime(2026, 9, 23, 9, 15, tzinfo=IST)
    bars = []
    for i in range(150):
        t = start + timedelta(minutes=5 * (i % 75)) + timedelta(days=i // 75)
        c = 100 + 3 * math.sin(i / 9) + i * 0.02
        bars.append({"time": t.isoformat(), "open": c - 0.2, "high": c + 0.6, "low": c - 0.6, "close": c,
                     "volume": 1000 + (i % 7) * 150})
    for windows in ([], [["10:00", "11:00"]]):
        signal, st = trader_brain.trader_brain_signal(bars, no_entry_windows=windows)
        assert st and "checklist" in st


# ---- hypothetical outcome ("what if it had been approved") -----------------

from datetime import timedelta  # noqa: E402

OFFER = datetime(2026, 9, 24, 13, 45, 10, tzinfo=IST)


def shadow_card(side="LONG", entry=100.0, stop=98.0, target=106.0, qty=10):
    return {"side": side, "entry": entry, "stop": stop, "target": target, "qty": qty,
            "created_ts": OFFER.timestamp()}


def bar(hhmm, o, h, low, c):
    h_, m_ = map(int, hhmm.split(":"))
    t = datetime(2026, 9, 24, h_, m_, tzinfo=IST)
    return {"time": t.isoformat(), "open": o, "high": h, "low": low, "close": c}


def later(hhmm):
    h_, m_ = map(int, hhmm.split(":"))
    return datetime(2026, 9, 24, h_, m_, 30, tzinfo=IST)


import costs  # noqa: E402
ZERO = costs.ZERO_COSTS   # nothing charged: every figure below is exact


def test_long_hits_target_and_books_the_gain():
    bars = [bar("13:50", 100, 101, 99.5, 100.5), bar("13:55", 100.5, 106.5, 100.4, 106)]
    out = review_queue.shadow_outcome(shadow_card(), bars, ltp=106, now=later("14:00"), costs_cfg=ZERO)
    assert out["status"] == "target" and out["exit_price"] == 106.0
    assert out["net_rs"] == 60.0 and out["r"] == 3.0


def test_short_is_stopped_and_a_gap_fills_at_the_open():
    card = shadow_card(side="SHORT", entry=100.0, stop=102.0, target=94.0)
    bars = [bar("13:50", 100, 101, 99, 100.8), bar("13:55", 103, 104, 102.5, 103.5)]
    out = review_queue.shadow_outcome(card, bars, ltp=103.5, now=later("14:00"), costs_cfg=ZERO)
    assert out["status"] == "stopped" and out["exit_price"] == 103   # gapped over 102
    assert out["net_rs"] == -30.0 and out["r"] == -1.5


def test_stop_is_assumed_first_when_one_bar_touches_both():
    bars = [bar("13:50", 100, 107, 97, 101)]
    out = review_queue.shadow_outcome(shadow_card(), bars, ltp=101, now=later("13:55"), costs_cfg=ZERO)
    assert out["status"] == "stopped" and out["exit_price"] == 98.0


def test_bars_that_started_before_the_offer_are_ignored():
    # The 13:45 bar was already running at 13:45:10; its low of 97 is from before the offer.
    bars = [bar("13:45", 100, 100.2, 97, 100), bar("13:50", 100, 101, 99.5, 100.6)]
    out = review_queue.shadow_outcome(shadow_card(), bars, ltp=100.6, now=later("13:52"), costs_cfg=ZERO)
    assert out["status"] == "open" and out["mark_price"] == 100.6
    assert out["net_rs"] == 6.0


def test_squared_off_at_the_square_off_bars_open():
    bars = [bar("13:50", 100, 101, 99.5, 100.5), bar("15:10", 101, 102, 100.5, 101.5), bar("15:15", 101.8, 102, 101, 101.2)]
    out = review_queue.shadow_outcome(shadow_card(), bars, ltp=101.2, now=later("15:20"),
                                      costs_cfg=ZERO, square_off="15:15")
    assert out["status"] == "squared_off" and out["exit_price"] == 101.8


def test_real_costs_make_a_flat_trade_negative():
    bars = [bar("13:50", 100, 100.5, 99.5, 100.0)]
    out = review_queue.shadow_outcome(shadow_card(), bars, ltp=100.0, now=later("13:55"))
    assert out["status"] == "open" and out["gross_rs"] < 0 and out["net_rs"] < out["gross_rs"]


def test_engine_saves_the_outcome_for_unapproved_cards_only(engine, monkeypatch):
    monkeypatch.setattr(data_provider, "get_ltp", lambda s: 100.5)
    monkeypatch.setattr(database, "new_position_id", lambda: "pos-manual")
    [card] = offer(engine)
    engine.state.candles[SYMBOL] = [bar("10:25", 100, 106.5, 99.9, 106)]
    engine._update_review_shadows(later("10:30"), min_interval=0)
    [row] = database.reviews_on("2026-09-24")
    assert row["shadow"]["status"] == "target"                      # saved to the journal
    assert engine.review_queue.snapshot()["shadow_summary"]["trades"] == 1

    # An approved card is a real position, not a hypothetical one.
    engine.review_queue.cards.clear(); engine.review_queue._seen.clear()
    engine.state.strategy_state.clear()
    [card2] = offer(engine)
    assert engine.approve_review(card2["id"])["status"] == "approved"
    assert all(c["id"] != card2["id"] for c in engine.review_queue.shadow_candidates())


# ---- #102: an exit seen only in the last price or a forming bar is provisional ----

def test_delayed_ltp_exit_is_provisional_and_a_later_bar_overrides_it():
    """The SBIN case: on delayed data the last price was past the target before
    the bar that settled the trade existed. That exit must not be final."""
    card = shadow_card(side="SHORT", entry=978.8, stop=980.4, target=978.5, qty=20)
    early = review_queue.shadow_outcome(card, [], ltp=978.0, now=later("13:58"), costs_cfg=ZERO)
    assert early["status"] == "target" and early["final"] is False

    settled = review_queue.shadow_outcome(card, [bar("13:50", 978.9, 980.7, 978.4, 978.6)], ltp=979.5,
                                          now=later("13:58"), costs_cfg=ZERO)
    assert settled["status"] == "stopped" and settled["final"] is True and settled["exit_price"] == 980.4


def test_an_exit_in_a_bar_still_forming_is_provisional_until_the_bar_completes():
    forming = [bar("13:50", 100, 106.5, 99.5, 106)]
    assert review_queue.shadow_outcome(shadow_card(), forming, ltp=106, now=later("13:52"),
                                       costs_cfg=ZERO)["final"] is False
    assert review_queue.shadow_outcome(shadow_card(), forming, ltp=106, now=later("13:55"),
                                       costs_cfg=ZERO)["final"] is True


def test_provisional_and_legacy_outcomes_stay_candidates_final_ones_do_not(engine):
    [card] = offer(engine)
    q = engine.review_queue
    q.set_shadow(card["id"], {"status": "target", "final": False, "net_rs": -1.0, "r": -0.1})
    assert [c["id"] for c in q.shadow_candidates()] == [card["id"]]
    q.set_shadow(card["id"], {"status": "target", "net_rs": -1.0, "r": -0.1})          # saved before #102
    assert [c["id"] for c in q.shadow_candidates()] == [card["id"]]
    q.set_shadow(card["id"], {"status": "stopped", "final": True, "net_rs": -2.0, "r": -1.0})
    assert q.shadow_candidates() == []
    assert q.snapshot()["shadow_summary"]["provisional"] == 0
