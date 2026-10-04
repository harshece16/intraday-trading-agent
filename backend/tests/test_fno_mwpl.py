"""NSE's F&O ban (Market Wide Position Limit) on the F&O entry path (README
section 108, rule FNO-08): a stock-option buy is refused for an underlying
on the day's ban list, an unknown list refuses stock options and says the
status is unknown, index options are exempt, and the engine checks before
any contract lookup, quote or order.

The list and its parser are nse_feed.fno_ban_list() / parse_fno_ban(), the
same ones the scanner's ban guard uses; their own tests are in
test_scanner_guards.py."""
import ast
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import confidence
import config
import database
import fno_instruments
import fno_risk
import nse_feed
import trading_engine
from state import AppState

INDEXES = ["NIFTY", "BANKNIFTY"]
TODAY = "2026-09-29"
BAN = nse_feed.parse_fno_ban("Securities in Ban For Trade Date 29-SEP-2026:\n1,LICHSGFIN\n2,SAIL\n")
CLEAR = nse_feed.parse_fno_ban("Securities in Ban For Trade Date 29-SEP-2026:\n")
FNO_BAN_LIST = nse_feed.fno_ban_list      # the real one, before any test replaces it


def test_a_banned_stock_is_refused_and_a_clear_one_is_not():
    assert "F&O ban for 2026-09-29" in fno_risk.mwpl_block_reason("SAIL", BAN, TODAY, INDEXES)
    assert fno_risk.mwpl_block_reason("sail", BAN, TODAY, INDEXES)          # symbols compare in upper case
    assert fno_risk.mwpl_block_reason("RELIANCE", BAN, TODAY, INDEXES) is None
    assert fno_risk.mwpl_block_reason("SAIL", CLEAR, TODAY, INDEXES) is None   # a clear day is known, not unknown


@pytest.mark.parametrize("ban", [None, BAN], ids=["unreadable", "another trade date"])
def test_an_unknown_list_refuses_stock_options_and_says_unknown(ban):
    reason = fno_risk.mwpl_block_reason("RELIANCE", ban, "2026-09-30", INDEXES)
    assert "unknown" in reason and "F&O ban for" not in reason


def test_index_options_are_exempt_even_when_the_status_is_unknown():
    assert fno_risk.mwpl_block_reason("NIFTY", None, TODAY, INDEXES) is None
    assert fno_risk.mwpl_block_reason("BANKNIFTY", BAN, "2026-09-30", INDEXES) is None


# --- the engine ----------------------------------------------------------------------------

def _engine(monkeypatch, ban):
    e = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    e.state.market = {"bias": "neutral", "reasons": []}     # the first scan has finished (#256)
    monkeypatch.setattr(database, "journal_summary", lambda *a, **k: {"scorecard": []})
    monkeypatch.setattr(confidence, "score_trade",
                        lambda *a, **k: {"score": 90, "label": "high", "explanation": "test"})
    monkeypatch.setattr(nse_feed, "fno_ban_list", lambda *a, **k: ban)
    monkeypatch.setattr(fno_instruments, "nearest_expiry", lambda *a, **k: None)   # stop right after the ban check
    monkeypatch.setattr(fno_instruments, "find_contract",
                        lambda *a, **k: pytest.fail("a contract was looked up for a blocked underlying"))
    today = datetime.now(trading_engine.IST).date().isoformat()
    return e, today


def _evaluations():
    with database._conn() as c:
        return c.execute("SELECT underlying, executed, block_reason FROM fno_evaluations").fetchall()


def _dated(ban, day):
    return {"trade_date": day, "symbols": set(ban["symbols"])}


def test_the_engine_refuses_a_banned_underlying_and_journals_why(monkeypatch):
    e, today = _engine(monkeypatch, None)
    monkeypatch.setattr(nse_feed, "fno_ban_list", lambda *a, **k: _dated(BAN, today))
    e._try_enter_fno("SAIL", "LONG", {"ltp": 100.0})
    [(underlying, executed, reason)] = _evaluations()
    assert (underlying, executed) == ("SAIL", 0) and f"F&O ban for {today}" in reason
    assert any(a.get("kind") == "blocked" and "F&O ban" in a.get("message", "") for a in e.state.activity)
    assert "SAIL" not in e.state.fno_positions


def test_the_engine_refuses_stock_options_when_the_list_is_unknown(monkeypatch):
    e, _ = _engine(monkeypatch, None)
    e._try_enter_fno("RELIANCE", "LONG", {"ltp": 100.0})
    [(_, executed, reason)] = _evaluations()
    assert executed == 0 and "unknown" in reason


def test_nse_down_costs_one_timeout_not_one_per_candidate_and_the_reason_says_when(monkeypatch):
    """#212: while NSE's archive does not answer, the first candidate waits
    out the timeout and the rest are refused at once until the retry time."""
    e, _ = _engine(monkeypatch, None)
    monkeypatch.setattr(nse_feed, "fno_ban_list", FNO_BAN_LIST)
    monkeypatch.setattr(nse_feed, "_ban_cache", {"at": 0.0, "value": None, "failed": None})
    calls = []

    def down(url, **kw):
        calls.append(url)
        raise nse_feed.requests.Timeout("read timed out")
    monkeypatch.setattr(nse_feed.requests, "get", down)
    for underlying in ("RELIANCE", "SAIL", "TCS"):
        e._try_enter_fno(underlying, "LONG", {"ltp": 100.0})
    assert calls == [nse_feed.FNO_BAN_URL]
    reasons = [r for _, _, r in _evaluations()]
    assert len(reasons) == 3 and len(set(reasons)) == 1
    assert "could not be read (the last try, at " in reasons[0] and "failed (no answer within 15 s)" in reasons[0]
    assert "ban status is unknown" in reasons[0]


def test_the_engine_lets_an_index_and_a_clear_stock_past_the_ban_check(monkeypatch):
    e, today = _engine(monkeypatch, None)
    e._try_enter_fno(config.FNO["index_underlyings"][0], "LONG", {"ltp": 100.0})
    monkeypatch.setattr(nse_feed, "fno_ban_list", lambda *a, **k: _dated(BAN, today))
    e._try_enter_fno("RELIANCE", "LONG", {"ltp": 100.0})
    reasons = [r for _, _, r in _evaluations()]
    assert reasons == ["no listed expiry in range", "no listed expiry in range"]   # stopped at the NEXT step


def test_the_ban_check_comes_before_any_contract_lookup_or_order():
    src = (Path(__file__).parent.parent / "trading_engine.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "_try_enter_fno")
    body = ast.get_source_segment(src, fn)
    assert "fno_risk.mwpl_block_reason(" in body and "nse_feed.fno_ban_list()" in body
    at = body.index("mwpl_block_reason(")
    # the live order goes out through _live_fno_fill(), which reads Kite's fill (#186)
    assert at < body.index("nearest_expiry(") < body.index("find_contract(") < body.index("_live_fno_fill(")
