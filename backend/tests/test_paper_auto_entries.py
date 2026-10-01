"""
Automatic entries in Paper (README section 118).

The cash confidence gate's bar depends on the mode at the moment of the entry:
RISK["paper_min_confidence_to_trade"] (0) in Paper, RISK["min_confidence_to_trade"]
(60) in Live. What must hold:
- in Paper, a checklist pass the live bar would block is entered, and its
  trade row records the score, the bar applied, and that the live bar would
  have blocked it;
- in Live, the same setup is blocked exactly as before, and offered as a card;
- a switch to Live restores the live bar for the very next entry, and a paper
  position opened before the switch stays a paper position;
- a switch to Live between the gate and the order can't send a real order
  that only the paper bar let through;
- in Paper a confidence-only near-miss is entered, not carded; cards for a
  checklist item still are;
- every other rule still blocks in Paper.
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import config
import database
import liquidity
import methods
import review_queue
import trading_engine
from state import AppState, _new_position

IST = review_queue.IST
KEYS = ["pattern", "sr", "cost", "volume", "dow", "rrr"]
BARS = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}] * 30
FAILING_SCORECARD = {"scorecard": [{"criterion": "x", "status": "fail", "detail": ""}]}
PASSING_SCORECARD = {"scorecard": [{"criterion": c, "status": "pass", "detail": ""} for c in "xyz"]}


def plan(failing=(), stop=98.0, target=106.0):
    items = [{"key": k, "label": f"{k} label", "ok": k not in failing, "detail": f"{k} detail", "required": True}
             for k in KEYS]
    return {"side": "long", "items": items, "passed": not failing, "pattern": "Hammer", "entry": 100.0,
            "stop": stop, "target": target, "rrr": 1.0, "size_factor": 1.0}


def analysis(p=None, bar_time="2026-10-01T10:15:00+05:30"):
    return {"entry_mode": "checklist", "setup": "Hammer", "bar_time": bar_time,
            "checklist": {"long": p or plan(), "short": None},
            "bull_score": 8.0, "bear_score": 2.0, "confirmations": ["trend", "levels", "volume"], "adx": 30}


class NoKite:
    """Any attempt to reach Kite fails the test: nothing here may place a real order."""
    def __getattr__(self, name):
        pytest.fail(f"a real Kite call was made ({name})")


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setitem(config.REVIEW_QUEUE, "enabled", True)
    monkeypatch.setattr(review_queue, "now_ist", lambda: datetime(2026, 10, 1, 10, 20, tzinfo=IST))
    monkeypatch.setattr(liquidity, "check", lambda *a, **k: (True, None, {}))
    monkeypatch.setattr(database, "journal_summary", lambda: FAILING_SCORECARD)
    state = AppState(watchlist=[], paper_mode=True)
    eng = trading_engine.TradingEngine(state)
    monkeypatch.setattr(eng, "_ensure_kite", lambda: NoKite())
    for sym in ("AAA", "BBB"):
        state.positions[sym] = _new_position()
    state.market = {"bias": "neutral", "reasons": []}
    state.market_status = "open"
    return eng


def entry_rows():
    return [t for t in database.recent_trades() if t["side"] == "BUY"]


# ---- the bar ------------------------------------------------------------------

def test_the_bar_is_zero_in_paper_and_sixty_in_live():
    assert config.RISK["paper_min_confidence_to_trade"] == 0
    assert config.cash_confidence_bar(True) == 0
    assert config.cash_confidence_bar(False) == config.RISK["min_confidence_to_trade"] == 60
    # The F&O gate is separate and unchanged.
    assert config.FNO["min_confidence_to_trade"] == 60


# ---- paper ----------------------------------------------------------------------

def test_paper_enters_below_the_live_bar_and_journals_the_score(engine):
    assert engine._try_enter("AAA", "LONG", 100.0, BARS, analysis()) is True
    pos = engine.state.positions["AAA"]
    assert pos["quantity"] > 0 and pos["live"] is False
    [row] = entry_rows()
    assert row["mode"] == "paper"
    conf = row["confidence"]
    assert conf["score"] < 60
    assert conf["mode"] == "paper" and conf["bar_applied"] == 0 and conf["live_bar"] == 60
    assert conf["paper_bar_let_through"] is True and conf["live_bar_would_block"] is True
    assert conf["multiplier"] == 0.25 and conf["local_setup"] is not None
    assert "below the live bar of 60: taken under the paper bar of 0" in row["note"]
    # The in-memory trade the dashboard reads carries the same record.
    assert engine.state.trades[0]["confidence"] == conf


def test_paper_entry_the_live_bar_would_also_take_is_marked_so(engine, monkeypatch):
    monkeypatch.setattr(database, "journal_summary", lambda: PASSING_SCORECARD)
    analysis_strong = {**analysis(), "bull_score": 20.0, "bear_score": 0.0,
                       "confirmations": ["trend", "momentum", "levels", "volume"], "adx": 40}
    assert engine._try_enter("AAA", "LONG", 100.0, BARS, analysis_strong) is True
    conf = entry_rows()[0]["confidence"]
    assert conf["score"] >= 60
    assert conf["paper_bar_let_through"] is False and conf["live_bar_would_block"] is False


def test_a_confidence_only_near_miss_is_entered_in_paper_not_carded(engine):
    assert engine._try_enter("AAA", "LONG", 100.0, BARS, analysis()) is True
    assert engine.review_queue.snapshot()["cards"] == []


def test_a_checklist_near_miss_is_still_carded_in_paper_with_the_bar_in_force(engine):
    engine._offer_near_misses("AAA", 100.0, BARS, analysis(plan(failing=("rrr",))))
    [card] = engine.review_queue.snapshot()["cards"]
    assert card["blocker"]["key"] == "rrr" and card["mode"] == "paper"
    assert card["confidence"]["bar"] == 0


@pytest.mark.parametrize("rule", ["paused", "risk_off", "max_positions", "daily_loss", "size_zero", "liquidity",
                                  "stop_passed"])
def test_every_other_rule_still_blocks_in_paper(engine, monkeypatch, rule):
    a = analysis()
    if rule == "paused":
        engine.state.entries_paused = True
    elif rule == "risk_off":
        engine.state.market = {"bias": "risk-off", "reasons": ["weak"]}
    elif rule == "max_positions":
        engine.risk.open_positions_count = config.RISK["max_open_positions"]
    elif rule == "daily_loss":
        monkeypatch.setattr(engine.risk, "daily_loss_limit_hit", lambda: True)
    elif rule == "size_zero":
        monkeypatch.setattr(engine.risk, "position_size", lambda *a, **k: 0)
    elif rule == "liquidity":
        monkeypatch.setattr(liquidity, "check", lambda *a, **k: (False, "spread too wide", {}))
    elif rule == "stop_passed":
        a = analysis(plan(stop=100.5))
    assert engine._try_enter("AAA", "LONG", 100.0, BARS, a) is False
    assert engine.state.positions["AAA"]["quantity"] == 0 and entry_rows() == []


# ---- live -----------------------------------------------------------------------

def test_live_blocks_below_the_bar_exactly_as_before_and_offers_a_card(engine, monkeypatch):
    engine.state.paper_mode = False
    monkeypatch.setattr(engine, "_execute", lambda *a, **k: pytest.fail("no order below the live bar"))
    assert engine._try_enter("AAA", "LONG", 100.0, BARS, analysis()) is False
    [blocked] = database.recent_blocked_signals()
    assert blocked["reason_type"] == "confidence_gate" and blocked["min_confidence_bar"] == 60
    assert blocked["final_score"] < 60
    [card] = engine.review_queue.snapshot()["cards"]
    assert card["blocker"]["key"] == "confidence" and card["blocker"]["need"] == 60
    assert card["mode"] == "live" and card["confidence"]["bar"] == 60


def test_a_switch_to_live_restores_the_bar_for_the_next_entry(engine):
    assert engine._try_enter("AAA", "LONG", 100.0, BARS, analysis()) is True
    engine.state.paper_mode = False
    assert engine._try_enter("BBB", "LONG", 100.0, BARS, analysis()) is False
    assert engine.state.positions["BBB"]["quantity"] == 0
    # The paper position opened before the switch is still a paper position.
    assert engine.state.positions["AAA"]["live"] is False
    assert [r["symbol"] for r in entry_rows()] == ["AAA"]


def test_a_switch_to_live_during_the_entry_cannot_send_a_real_order(engine, monkeypatch):
    def flip_to_live(*a, **k):
        engine.state.paper_mode = False         # the owner clicks Go live mid-entry
        return True, None, {}
    monkeypatch.setattr(liquidity, "check", flip_to_live)
    assert engine._try_enter("AAA", "LONG", 100.0, BARS, analysis()) is False
    assert engine.state.positions["AAA"]["quantity"] == 0 and entry_rows() == []
    [blocked] = database.recent_blocked_signals()
    assert blocked["reason_type"] == "confidence_gate" and blocked["min_confidence_bar"] == 60


# ---- what reports the bar ----------------------------------------------------------

def test_the_snapshot_and_methods_report_the_bar_in_force():
    paper = AppState(watchlist=[], paper_mode=True).snapshot()
    assert (paper["confidence_bar"], paper["live_confidence_bar"]) == (0, 60)
    live = AppState(watchlist=[], paper_mode=False).snapshot()
    assert (live["confidence_bar"], live["live_confidence_bar"]) == (60, 60)
    assert "Paper now, where the bar is 0" in methods.get_methods(paper_mode=True)["risk"]["note"]
    live_note = methods.get_methods(paper_mode=False)["risk"]["note"]
    assert "The engine is in Live" in live_note and "60/100" in live_note


# ---- the journal column ------------------------------------------------------------

def test_an_old_journal_gains_the_confidence_column_and_keeps_its_rows(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE trades (id TEXT PRIMARY KEY, position_id TEXT, ts REAL NOT NULL, symbol TEXT NOT NULL, "
                "side TEXT, quantity INTEGER, price REAL, mode TEXT, reason TEXT, note TEXT, realized REAL, "
                "charges REAL, initial_risk REAL, r_multiple REAL, checklist_json TEXT, realized_gross REAL, "
                "signal_price REAL, order_id TEXT)")
    old.execute("INSERT INTO trades (id, ts, symbol, side, quantity, price, mode) "
                "VALUES ('t1', 1.0, 'AAA', 'BUY', 1, 10.0, 'paper')")
    old.commit()
    old.close()
    monkeypatch.setattr(database, "DB_PATH", path)
    database._local.conn = None
    [row] = database.recent_trades()
    assert row["id"] == "t1" and row["confidence"] is None
