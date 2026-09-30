"""The scanner sets no side, and every scan is journaled for the shadow log
(README section 115; docs/research/scanner-audit-2026-09-28.md, rules 3.8 and
5.3 and section 6).

- The old score's stronger side is kept as score_side, for information. The
  row's own side is empty, the day's list is still the most-traded stocks,
  and an entry is no longer refused for disagreeing with the old score.
- What stays is tradability: a long-only stock is never shorted, and shorts
  can still be switched off.
- Every stock of every scan is written with the inputs of the audit's passes
  1 to 3; the 15:08 price is written once a session from Kite; the view
  scan_candidates joins them into a return per scan and stock.
- The Jev book keeps the old score's side in its snapshot and as its
  baseline, as registered (prereg-jev-book.md, clarification 9).
"""
import os
import sqlite3
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import data_provider  # noqa: E402
import database  # noqa: E402
import day_plan  # noqa: E402
import jev_book  # noqa: E402
import research_desk  # noqa: E402
import scanner  # noqa: E402
import trading_engine  # noqa: E402
from state import AppState, _new_position  # noqa: E402
from tests.test_scanner_live_feed import CFG, SESSION, UNIVERSE, _live, _quote, feeds  # noqa: E402,F401

IST = trading_engine.IST


# --- the scan ------------------------------------------------------------------------------------------

def test_the_scan_sets_no_side_and_keeps_the_old_scores_lean_for_information(feeds, monkeypatch):
    _live(feeds, monkeypatch)
    res = scanner.Scanner(CFG).run()
    assert "active_sides" not in res
    for r in res["rows"]:
        assert r["side"] is None
        want = "LONG" if r["long_score"] >= r["short_score"] else "SHORT"
        assert r["score_side"] == want
    # the day's list is still the most-traded eligible stocks, whatever the score says
    assert res["active"] == scanner.select_liquid([r for r in res["rows"] if not r["excluded"]], CFG)


def test_a_long_only_stock_has_no_short_score(feeds, monkeypatch):
    _live(feeds, monkeypatch)
    monkeypatch.setattr(scanner, "load_guards", lambda cfg: {"ban": None, "bands": {
        "AAA": {"series": "EQ", "band": 20.0, "remarks": ""}}})
    rows = {r["symbol"]: r for r in scanner.Scanner({**CFG, "guards": True}).run()["rows"]}
    assert rows["AAA"]["long_only"] and rows["AAA"]["score_side"] == "LONG" and rows["AAA"]["short_score"] is None
    assert not rows["BBB"]["long_only"] and rows["BBB"]["short_score"] is not None


def _quotes(feeds, moves, nifty_ltp):
    """moves: {symbol: (change, vwap)} as fractions of the previous close."""
    out = {}
    for s, c in feeds["last"].items():
        chg, vwap = moves.get(s, (0.02, 0.015))
        out[s] = _quote(ltp=c * (1 + chg), open_=c * 1.01, prev=c, volume=20000, vwap=c * (1 + vwap), hhmm="10:00:00")
    out["NIFTY 50"] = {**_quote(ltp=nifty_ltp, open_=22050.0, prev=22000.0, volume=0, vwap=0.0, hhmm="10:00:00"),
                       "last_trade": None}
    return out


def test_the_shadow_direction_needs_all_three_legs_to_agree(feeds, monkeypatch):
    """AAA and BBB are the two IT stocks: AAA +3% above its VWAP, BBB +2% below
    its VWAP. The banks and autos all move alike, so their industry leg is level."""
    _live(feeds, monkeypatch)
    moves = {"AAA": (0.03, 0.015), "BBB": (0.02, 0.025)}
    monkeypatch.setattr(data_provider, "kite_quotes", lambda symbols, indices=(): _quotes(feeds, moves, 22100.0))
    up = {r["symbol"]: r for r in scanner.Scanner(CFG).run()["rows"]}
    monkeypatch.setattr(data_provider, "kite_quotes", lambda symbols, indices=(): _quotes(feeds, moves, 21950.0))
    down = {r["symbol"]: r for r in scanner.Scanner(CFG).run()["rows"]}
    # the industry is the other stocks in it, not the stock itself
    assert up["AAA"]["sector_chg_pct"] == pytest.approx(2.0) and up["BBB"]["sector_chg_pct"] == pytest.approx(3.0)
    assert (up["AAA"]["shadow_side"], up["BBB"]["shadow_side"]) == ("LONG", None)        # NIFTY above its open
    assert (down["AAA"]["shadow_side"], down["BBB"]["shadow_side"]) == (None, "SHORT")    # NIFTY below its open
    assert up["CCC"]["shadow_side"] is None                                               # level with its industry
    for r in up.values():
        assert r["side"] is None and r["feed"] == "live" and r["price_at"] == f"{SESSION}T10:00:00+05:30"


def test_the_shadow_direction_is_none_when_an_input_is_missing():
    assert scanner.shadow_side(101, 100, 1.0, 0.5, 22100, 22000) == "LONG"
    assert scanner.shadow_side(99, 100, 0.5, 1.0, 21900, 22000) == "SHORT"
    assert scanner.shadow_side(101, 100, 1.0, 0.5, 21900, 22000) is None
    assert scanner.shadow_side(101, None, 1.0, 0.5, 22100, 22000) is None
    assert scanner.shadow_side(101, 100, 1.0, None, 22100, 22000) is None
    assert scanner.shadow_side(100, 100, 1.0, 0.5, 22100, 22000) is None          # level with its VWAP


def test_the_premarket_read_names_the_list_without_a_side():
    picks = [{"symbol": s, "side": None, "score_side": "SHORT", "reasons": []} for s in ("A", "B")]
    text = " ".join(scanner._premarket_narrative("risk-off", ["NIFTY fell"], 13.0, False, picks, {}, {}))
    assert "Today's list: A, B." in text and "checklist picks long or short" in text
    assert "short side" not in text and "long side" not in text


# --- the entry gate ------------------------------------------------------------------------------------

@pytest.fixture
def engine(monkeypatch):
    state = AppState(watchlist=[], paper_mode=True)
    eng = trading_engine.TradingEngine(state)
    state.positions["TESTCO"] = _new_position()
    state.market = {"bias": "neutral", "reasons": []}
    return eng


def _row(**kw):
    return {"symbol": "TESTCO", "industry": "IT", "excluded": None, "long_only": False, "side": None,
            "score_side": "SHORT", **kw}


def test_an_entry_is_not_refused_for_disagreeing_with_the_old_score(engine):
    engine.state.scanner = {"rows": [_row(score_side="SHORT")]}
    assert engine._entry_block_reason("TESTCO", "LONG") is None
    assert engine._entry_block_reason("TESTCO", "SHORT") is None
    engine.state.scanner = {"rows": [_row(score_side="LONG")]}
    assert engine._entry_block_reason("TESTCO", "SHORT") is None


def test_a_real_scan_leaves_both_sides_open_on_every_listed_stock(engine, feeds, monkeypatch):
    """Until README section 115 the scan's side refused the other one: 'scanner favours SHORT for this stock today'."""
    _live(feeds, monkeypatch)
    engine.state.scanner = scanner.Scanner(CFG).run()
    for sym in engine.state.scanner["active"]:
        engine.state.positions[sym] = _new_position()
        assert engine._entry_block_reason(sym, "LONG") is None
        assert engine._entry_block_reason(sym, "SHORT") is None


def test_a_long_only_stock_is_never_shorted(engine):
    engine.state.scanner = {"rows": [_row(long_only=True, score_side="LONG")]}
    assert "long-only" in engine._entry_block_reason("TESTCO", "SHORT")
    assert engine._entry_block_reason("TESTCO", "LONG") is None


def test_shorts_switched_off_are_refused(engine, monkeypatch):
    monkeypatch.setitem(config.SCANNER, "allow_shorts", False)
    engine.state.scanner = {"rows": [_row()]}
    assert "switched off" in engine._entry_block_reason("TESTCO", "SHORT")
    assert engine._entry_block_reason("TESTCO", "LONG") is None


def test_an_excluded_stock_and_the_market_bias_still_block(engine):
    engine.state.scanner = {"rows": [_row(excluded="Results today")]}
    assert engine._entry_block_reason("TESTCO", "LONG") == "Results today"
    engine.state.scanner = {"rows": [_row()]}
    engine.state.market = {"bias": "risk-off", "reasons": ["NIFTY fell"]}
    assert "no new longs" in engine._entry_block_reason("TESTCO", "LONG")


# --- the journal ---------------------------------------------------------------------------------------

def test_every_stock_of_every_scan_is_journaled_with_its_inputs_and_scored_at_1508(feeds, monkeypatch):
    _live(feeds, monkeypatch)
    res = scanner.Scanner(CFG).run()
    database.record_scan(res)
    got = database.scan_candidates(SESSION)
    assert len(got) == 6
    by = {r["symbol"]: r for r in res["rows"]}
    for g in got:
        r = by[g["symbol"]]
        assert g["score_side"] == r["score_side"] and g["long_score"] == r["long_score"]
        assert g["shadow_side"] == r["shadow_side"] and g["feed"] == "live" and g["price_at"] == r["price_at"]
        assert (g["ltp"], g["vwap"], g["gap_pct"], g["rvol"]) == (r["ltp"], r["vwap"], r["gap_pct"], r["rvol"])
        assert (g["or_high"], g["or_low"]) == (r["or_high"], r["or_low"])
        assert g["sector_chg_pct"] == r["sector_chg_pct"] and g["turnover_cr"] == r["turnover_cr"]
        assert g["status"] == ("ACTIVE" if g["symbol"] in res["active"] else "WATCH")
        assert g["long_only"] == 0 and g["vwap_dist_bp"] == pytest.approx((r["ltp"] / r["vwap"] - 1) * 1e4)
        assert g["scan_feed"] == "live" and g["nifty_open"] == pytest.approx(22050.0)
        assert g["close_price"] is None and g["ret_to_close_bp"] is None               # 15:08 not reached
    assert all(g["or_high"] is not None for g in got if g["symbol"] in res["active"])  # live bars for the list
    # 15:08: Kite's prices; a stock whose last trade is from an earlier day is left out
    closes = {s: {"ltp": by[s]["ltp"] * 1.01, "last_trade": f"{SESSION}T15:08:05+05:30"} for s in by}
    closes["AAA"]["last_trade"] = "2026-09-26T15:29:59+05:30"
    assert database.record_session_closes(SESSION, closes, ts=res["ts"] + 60) == 5
    assert database.record_session_closes(SESSION, {"BBB": {"ltp": 1.0, "last_trade": SESSION}}) == 0  # first stands
    got = {g["symbol"]: g for g in database.scan_candidates(SESSION)}
    assert got["AAA"]["ret_to_close_bp"] is None
    for s in ("BBB", "CCC", "DDD", "EEE", "FFF"):
        assert got[s]["ret_to_close_bp"] == pytest.approx(100.0, abs=0.05)             # +1% (ltp rounded to paise)
    # a scan after 15:08 has no forward return
    database.record_scan({**res, "ts": res["ts"] + 120})
    late = [g for g in database.scan_candidates(SESSION) if g["scan_ts"] > res["ts"] + 60]
    assert len(late) == 6 and all(g["ret_to_close_bp"] is None for g in late)


OLD_SCHEMA = """
CREATE TABLE scans (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, session_date TEXT, bias TEXT,
    nifty_ltp REAL, nifty_chg_pct REAL, vix REAL, adv INTEGER, dec INTEGER, scanned INTEGER, excluded_count INTEGER,
    active_json TEXT, reasons_json TEXT);
CREATE TABLE scan_rows (id INTEGER PRIMARY KEY AUTOINCREMENT, scan_id INTEGER NOT NULL, session_date TEXT,
    symbol TEXT NOT NULL, side TEXT, score REAL, final_score REAL, excluded TEXT, status TEXT, ltp REAL, chg_pct REAL,
    daily_trend TEXT, rs10 REAL, rvol REAL, gap_pct REAL, catalyst_score REAL, swing_pattern TEXT, reasons_json TEXT);
INSERT INTO scans (id, ts, session_date, bias) VALUES (1, 1000.0, '2026-09-29', 'neutral');
INSERT INTO scan_rows (scan_id, session_date, symbol, side, score, ltp) VALUES (1, '2026-09-29', 'OLDCO', 'LONG', 12.0, 100.0);
"""


def test_a_journal_from_before_gains_the_columns_and_its_rows_read_the_old_side(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as c:
        c.executescript(OLD_SCHEMA)
    monkeypatch.setattr(database, "DB_PATH", path)
    database._local.conn = None
    [row] = database.scan_candidates("2026-09-29")
    assert row["symbol"] == "OLDCO" and row["score_side"] == "LONG" and row["shadow_side"] is None
    cols = {r[1] for r in database._conn().execute("PRAGMA table_info(scan_rows)")}
    assert {"score_side", "shadow_side", "vwap", "sector_chg_pct", "price_at"} <= cols
    stored = database._conn().execute("SELECT sql FROM sqlite_master WHERE name = 'scan_candidates'").fetchone()[0]
    assert stored == database.SCAN_CANDIDATES_VIEW          # so a later connection leaves it alone


# --- the 15:08 price -----------------------------------------------------------------------------------

def test_the_1508_prices_are_read_from_kite_once_a_session(engine, monkeypatch):
    now = datetime(2026, 9, 29, 15, 8, 20, tzinfo=IST)
    calls = []

    def quotes(symbols, indices=()):
        calls.append((list(symbols), indices))
        return {"AAA": {"ltp": 101.0, "last_trade": "2026-09-29T15:08:10+05:30", "at": "2026-09-29T15:08:19+05:30"},
                "NIFTY 50": {"ltp": 22000.0, "last_trade": None, "at": "2026-09-29T15:08:19+05:30"}}
    monkeypatch.setattr(trading_engine.universe, "load", lambda: UNIVERSE)
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: True)
    monkeypatch.setattr(data_provider, "kite_quotes", quotes)
    engine._record_session_closes(now)
    engine._record_session_closes(now.replace(second=50))
    assert len(calls) == 1 and calls[0] == ([u["symbol"] for u in UNIVERSE], ("NIFTY 50",))
    rows = database._conn().execute("SELECT symbol, price FROM session_closes ORDER BY symbol").fetchall()
    assert [tuple(r) for r in rows] == [("AAA", 101.0), ("NIFTY 50", 22000.0)]
    assert any("Shadow log: recorded" in a["message"] for a in engine.state.activity)
    # after a restart the session is not asked for again
    fresh = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    fresh._record_session_closes(now.replace(minute=9))
    assert len(calls) == 1


def test_without_kite_there_is_no_1508_price_and_it_is_said_once(engine, monkeypatch):
    now = datetime(2026, 9, 29, 15, 8, 20, tzinfo=IST)
    monkeypatch.setattr(trading_engine.universe, "load", lambda: UNIVERSE)
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: False)
    monkeypatch.setattr(data_provider, "kite_quotes", lambda *a, **k: pytest.fail("Kite is not asked when it is off"))
    engine._record_session_closes(now)
    engine._record_session_closes(now.replace(minute=9))
    assert not database.session_closes_recorded("2026-09-29")
    assert sum("no live Kite price" in a["message"] for a in engine.state.activity) == 1


# --- readers of the side -------------------------------------------------------------------------------

def test_the_jev_book_keeps_the_old_scores_side_in_its_snapshot_and_baseline(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    rows = [{"symbol": "S0", "ltp": 100.0, "side": None, "score_side": "SHORT", "reasons": [], "brain": {}},
            {"symbol": "S1", "ltp": 100.0, "side": "LONG", "reasons": [], "brain": {}}]          # a row from before
    sc = {"session_date": "2026-09-28", "active": ["S0", "S1"], "rows": rows, "market": {"bias": "neutral"}}
    sent = []

    def post(url, json=None, headers=None, timeout=None):
        sent.append(json["state"]["stock"]["side"])
        body = {"answers": {"action": {"choice": "skip"}, "p_up": {"noul": 0.5}, "size": {"score": 0}}}
        return type("R", (), {"status_code": 200, "json": lambda self: body, "text": "", "headers": {}})()
    path = str(tmp_path / "s.json")
    jev_book.decide_round(sc, datetime(2026, 9, 28, 9, 46), lambda s: 100.0, post=post, state_path=path,
                          sleep=lambda s: None)
    assert sent == ["SHORT", "LONG"]
    assert [d["scanner_side"] for d in jev_book.load_state(path)["days"]["2026-09-28"]["decisions"]] == ["SHORT", "LONG"]


def test_jevs_snapshot_is_the_same_as_before_the_change():
    """The same stock-time as the scanner wrote it before README section 115 and after it."""
    before = {"symbol": "S0", "ltp": 100.0, "side": "SHORT", "score": -3.0, "final_score": -5.0,
              "reasons": [{"text": "x"}], "brain": {"setup": "y"}}
    after = {**before, "side": None, "score_side": "SHORT", "long_score": -9.0, "short_score": -3.0,
             "shadow_side": "LONG", "sector_chg_pct": 0.4, "price_at": "2026-09-28T09:45:00+05:30", "or_high": 101.0}
    market = {"bias": "neutral", "reasons": ["r"], "nifty": {"ltp": 1.0, "chg_pct": 0.1}, "vix": 13.0}
    now = datetime(2026, 9, 28, 9, 46)
    assert jev_book.build_state(after, {**market, "nifty_open": 0.9}, now) == jev_book.build_state(before, market, now)


def _snapshot(bias, long_only=False, market_bias="neutral"):
    return {"technical": {"available": True, "bias": bias}, "scanner": {"side": None, "long_only": long_only},
            "risk": {"plan": None, "scorecard": []}, "market": {"bias": market_bias}, "rules": {}}


def test_the_research_desk_reads_the_checklists_side():
    flags = research_desk.deterministic_flags(_snapshot("short", long_only=True))
    assert any(f["severity"] == "high" and "long-only" in f["text"] for f in flags)
    assert not any("scanner's side" in f["text"] for f in flags)
    flags = research_desk.deterministic_flags(_snapshot("long", market_bias="risk-off"))
    assert any("blocks new longs" in f["text"] for f in flags)
    assert not any("long-only" in f["text"] for f in research_desk.deterministic_flags(_snapshot("long", True)))


def test_the_day_plan_sizes_the_checklists_side_and_says_when_it_has_none():
    assert day_plan.plan_side({"brain": {"short_ok": True}}) == ("SHORT", "checklist")
    assert day_plan.plan_side({"brain": {"short_ok": True, "bias": "short"}, "long_only": True}) == ("LONG", "checklist")
    assert day_plan.plan_side({"brain": {"bias": "short"}}) == ("SHORT", "checklist")
    assert day_plan.plan_side({"side": None}) == ("LONG", "long case")
    got = day_plan.plan(100000.0, [{"symbol": "A", "ltp": 100.0, "atr_pct": 2.0, "side": None}])
    assert [(c["symbol"], c["side"], c["side_basis"]) for c in got["candidates"]] == [("A", "LONG", "long case")]
