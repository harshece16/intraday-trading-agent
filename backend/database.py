"""
Sahab's Journal — a local SQLite audit trail of everything the agent sees and
does, meant to become a knowledge base once enough of it accumulates.

Design principle (ML4Trading, ch 1: "data should reflect only information
available and known at the given time"): every row is a point-in-time
snapshot written when the decision was made, never edited afterwards. A
scan, a checklist read, and a trade each freeze exactly what Sahab's Dimaag
saw at that moment — including checks that failed — so a later analysis
never accidentally uses hindsight.

Tables:
  scans             one row per market scan
  scan_rows         one row per (scan, symbol) — the full ranked list, not just picks
  checklist_evals   one row per live checklist read on an active-watchlist stock
  trades            one row per fill, with the checklist snapshot that justified an
                    entry, and the realized R-multiple once an exit closes the loop
  signals           the raw signal log
  activity          the plain-English activity log
  research_briefs   one row per Research Desk brief (research_desk.py): the grounded
                    snapshot, every agent's validated output, the rating, tokens, cost
  day_lists         one row per session: the day's list, written once when it is
                    fixed, so a restart keeps it (#198)
  session_closes    one row per (session, stock): Kite's last traded price at the
                    15:08 square-off, the outcome of the shadow log (README §115)
  scan_candidates   a view, not a table: the shadow log of the scanner audit's
                    passes 1 to 3. Every stock of every scan with its inputs (from
                    scan_rows and scans) and its return to 15:08 (session_closes)

Single-writer (the trading engine's background thread) so no connection
pooling is needed; SQLite's own locking covers the occasional API-thread read.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import config
import evaluation

# The journal is the evidence base for everything in docs/research/, so it
# must be possible to point a throwaway instance somewhere else. Hardcoding
# this meant "test on another port" isolated the port but not the database,
# and a second engine wrote 119 rows into the live journal on 2026-09-22.
# Issue #70.
_DEFAULT_DB_PATH = Path(__file__).parent / "data" / "sahab_journal.db"
DB_PATH = Path(os.environ.get("SAHAB_DB_PATH") or _DEFAULT_DB_PATH)
_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, session_date TEXT, bias TEXT,
    nifty_ltp REAL, nifty_chg_pct REAL, vix REAL, adv INTEGER, dec INTEGER,
    scanned INTEGER, excluded_count INTEGER, active_json TEXT, reasons_json TEXT,
    feed TEXT, quotes_at TEXT, nifty_open REAL, nifty_trend TEXT, fii_net_cr REAL
);
CREATE TABLE IF NOT EXISTS scan_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL, session_date TEXT, symbol TEXT NOT NULL, side TEXT,
    score REAL, final_score REAL, excluded TEXT, status TEXT,
    ltp REAL, chg_pct REAL, daily_trend TEXT, rs10 REAL, rvol REAL, gap_pct REAL,
    catalyst_score REAL, swing_pattern TEXT, reasons_json TEXT,
    score_side TEXT, long_score REAL, short_score REAL, long_only INTEGER, feed TEXT, price_at TEXT,
    vwap REAL, or_high REAL, or_low REAL, sector_chg_pct REAL, sector_trend TEXT,
    turnover_cr REAL, atr_pct REAL, shadow_side TEXT
);
CREATE TABLE IF NOT EXISTS session_closes (
    session_date TEXT NOT NULL, symbol TEXT NOT NULL, price REAL NOT NULL, ts REAL NOT NULL,
    last_trade TEXT, source TEXT,
    PRIMARY KEY (session_date, symbol)
);
CREATE INDEX IF NOT EXISTS idx_scan_rows_symbol_date ON scan_rows(symbol, session_date);
CREATE TABLE IF NOT EXISTS checklist_evals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, symbol TEXT NOT NULL, ltp REAL,
    bull_score REAL, bear_score REAL, entry_threshold REAL,
    long_ok INTEGER, short_ok INTEGER, setup TEXT, regime TEXT, always_in TEXT, news_score REAL,
    checklist_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_checklist_symbol_ts ON checklist_evals(symbol, ts);
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY, position_id TEXT, ts REAL NOT NULL, symbol TEXT NOT NULL,
    side TEXT, quantity INTEGER, price REAL, mode TEXT, reason TEXT, note TEXT,
    realized REAL, charges REAL, initial_risk REAL, r_multiple REAL, checklist_json TEXT,
    realized_gross REAL, signal_price REAL, order_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_trades_position ON trades(position_id);
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, symbol TEXT, signal TEXT, detail_json TEXT
);
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, kind TEXT, symbol TEXT, message TEXT, level TEXT
);
CREATE TABLE IF NOT EXISTS fno_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, underlying TEXT NOT NULL, side TEXT,
    confidence_score INTEGER, confidence_label TEXT,
    local_setup_score INTEGER, edge_margin_pts REAL, categories TEXT, regime_clarity_pct INTEGER,
    system_multiplier REAL, system_reason TEXT,
    executed INTEGER NOT NULL, block_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_fno_eval_underlying_ts ON fno_evaluations(underlying, ts);
CREATE TABLE IF NOT EXISTS fno_trades (
    position_id TEXT PRIMARY KEY, underlying TEXT NOT NULL, tradingsymbol TEXT NOT NULL,
    is_call INTEGER, strike REAL, expiry TEXT, lot_size INTEGER, lots INTEGER,
    entry_ts REAL, entry_premium REAL, entry_iv_pct REAL, entry_delta REAL, entry_theta REAL, entry_vega REAL,
    confidence_score INTEGER, confidence_label TEXT,
    exit_ts REAL, exit_premium REAL, exit_reason TEXT, realized REAL, r_multiple REAL
);
CREATE TABLE IF NOT EXISTS chaywanaprash_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, lookback_hours REAL, llm_used INTEGER,
    narrative TEXT, findings_json TEXT, input_tokens INTEGER, output_tokens INTEGER
);
CREATE TABLE IF NOT EXISTS depth_samples (
    ts REAL NOT NULL, symbol TEXT NOT NULL, ltp REAL, bid REAL, ask REAL, spread_bp REAL,
    bid_qty1 INTEGER, ask_qty1 INTEGER, bid_qty5 INTEGER, ask_qty5 INTEGER, imbalance5 REAL,
    volume INTEGER, total_buy_qty INTEGER, total_sell_qty INTEGER
);
CREATE INDEX IF NOT EXISTS idx_depth_symbol_ts ON depth_samples(symbol, ts);
CREATE TABLE IF NOT EXISTS liquidity_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, symbol TEXT NOT NULL, side TEXT, qty INTEGER, ltp REAL, mode TEXT,
    status TEXT, ok INTEGER, reason TEXT,
    spread_bp REAL, impact_bp REAL, entry_depth INTEGER, exit_depth INTEGER
);
CREATE INDEX IF NOT EXISTS idx_liquidity_symbol_ts ON liquidity_checks(symbol, ts);
CREATE TABLE IF NOT EXISTS market_breadth_daily (
    session_date TEXT PRIMARY KEY, ts REAL NOT NULL,
    advances INTEGER, declines INTEGER, unchanged INTEGER, total INTEGER,
    trin REAL
);
CREATE TABLE IF NOT EXISTS research_briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, symbol TEXT NOT NULL,
    snapshot_json TEXT, reports_json TEXT, rating INTEGER,
    model_ids TEXT, tokens INTEGER, cost_usd REAL
);
CREATE INDEX IF NOT EXISTS idx_research_briefs_symbol_ts ON research_briefs(symbol, ts);
CREATE TABLE IF NOT EXISTS manual_reviews (
    id TEXT PRIMARY KEY, created_ts REAL NOT NULL, session_date TEXT NOT NULL,
    symbol TEXT NOT NULL, side TEXT NOT NULL, blocker TEXT, mode TEXT,
    status TEXT NOT NULL, decided_ts REAL, position_id TEXT,
    outcome_json TEXT, card_json TEXT, shadow_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_manual_reviews_date ON manual_reviews(session_date);
CREATE TABLE IF NOT EXISTS control (
    key TEXT PRIMARY KEY, value TEXT, ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS day_lists (
    session_date TEXT PRIMARY KEY, symbols_json TEXT NOT NULL, fixed_ts REAL NOT NULL,
    fixed_when TEXT, mode TEXT
);
"""


def _migrate(conn):
    """Add columns the schema gained after a journal was already in use.
    `CREATE TABLE IF NOT EXISTS` leaves an existing table alone, so a new
    column has to be ALTERed in. Idempotent: each block returns early once
    its column exists."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(trades)")}
    if "realized_gross" not in cols:
        conn.execute("ALTER TABLE trades ADD COLUMN realized_gross REAL")
        _restate_realized_net_of_charges(conn)
    # The price the engine asked for, beside the price it got, and Kite's
    # order id on a live leg (#155). The gap between the two is the slippage
    # #66 needs measured. Rows from before this have neither.
    for col, kind in (("signal_price", "REAL"), ("order_id", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE trades ADD COLUMN {col} {kind}")
    # The bar a checklist read was judged on (#82): the entry window is a rule
    # about the bar's time, and the row's ts is when the read ran, which can be
    # minutes later (closed bars, or delayed yfinance data).
    cols = {r[1] for r in conn.execute("PRAGMA table_info(checklist_evals)")}
    if "bar_time" not in cols:
        conn.execute("ALTER TABLE checklist_evals ADD COLUMN bar_time TEXT")
    # What a review card would have done had it been approved (review_queue.shadow_outcome).
    cols = {r[1] for r in conn.execute("PRAGMA table_info(manual_reviews)")}
    if "shadow_json" not in cols:
        conn.execute("ALTER TABLE manual_reviews ADD COLUMN shadow_json TEXT")
    # The shadow log of the scanner audit's passes 1 to 3 (README §115): the
    # inputs a later pre-registered test reads, on the rows already written
    # for every stock of every scan. Rows from before this have NULL here.
    for table, new in (("scans", _SCANS_SHADOW_COLS), ("scan_rows", _SCAN_ROWS_SHADOW_COLS)):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for col, kind in new:
            if col not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {kind}")
    # Created here, after the columns it reads exist; replaced when its definition changes.
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'view' AND name = 'scan_candidates'").fetchone()
    if not row or row[0] != SCAN_CANDIDATES_VIEW:
        conn.execute("DROP VIEW IF EXISTS scan_candidates")
        conn.execute(SCAN_CANDIDATES_VIEW)


_SCANS_SHADOW_COLS = (("feed", "TEXT"), ("quotes_at", "TEXT"), ("nifty_open", "REAL"), ("nifty_trend", "TEXT"),
                      ("fii_net_cr", "REAL"))
_SCAN_ROWS_SHADOW_COLS = (
    ("score_side", "TEXT"), ("long_score", "REAL"), ("short_score", "REAL"), ("long_only", "INTEGER"),
    ("feed", "TEXT"), ("price_at", "TEXT"), ("vwap", "REAL"), ("or_high", "REAL"), ("or_low", "REAL"),
    ("sector_chg_pct", "REAL"), ("sector_trend", "TEXT"), ("turnover_cr", "REAL"), ("atr_pct", "REAL"),
    ("shadow_side", "TEXT"))

# Every stock of every scan, with the inputs of the audit's passes 1 to 3 and
# the return from the scan's price to the 15:08 price (NULL for a scan after
# 15:08, or a session with no close recorded). score_side reads `side` on rows
# from before README §115, when the old score's lean was written there.
SCAN_CANDIDATES_VIEW = (
    "CREATE VIEW scan_candidates AS SELECT "
    "r.id AS row_id, r.scan_id, s.ts AS scan_ts, r.session_date, r.symbol, r.status, r.excluded, r.long_only, "
    "r.feed, r.price_at, r.ltp, r.chg_pct, r.gap_pct, r.rvol, r.vwap, "
    "CASE WHEN r.vwap > 0 AND r.ltp > 0 THEN (r.ltp / r.vwap - 1) * 10000 END AS vwap_dist_bp, "
    "r.or_high, r.or_low, r.sector_chg_pct, r.sector_trend, r.turnover_cr, r.atr_pct, r.daily_trend, r.rs10, "
    "r.catalyst_score, r.score, r.final_score, r.long_score, r.short_score, "
    "COALESCE(r.score_side, r.side) AS score_side, r.shadow_side, "
    "s.feed AS scan_feed, s.quotes_at, s.bias, s.nifty_ltp, s.nifty_open, s.nifty_chg_pct, s.nifty_trend, "
    "s.vix, s.fii_net_cr, c.price AS close_price, c.ts AS close_ts, "
    "CASE WHEN c.price > 0 AND r.ltp > 0 AND s.ts < c.ts THEN (c.price / r.ltp - 1) * 10000 END AS ret_to_close_bp "
    "FROM scan_rows r JOIN scans s ON s.id = r.scan_id "
    "LEFT JOIN session_closes c ON c.session_date = r.session_date AND c.symbol = r.symbol")


def _restate_realized_net_of_charges(conn):
    """Issue #21: every `realized` written before this restated the P&L
    *before* brokerage, STT, exchange fees, GST and stamp duty — those were
    filed in `charges` and never subtracted. Keep the original figure in
    realized_gross, and rewrite realized (and the R-multiple derived from it)
    net of the whole round trip's charges, so the Scorecard's live expectancy
    is finally comparable with the backtester's, which has always been net.

    A position's legs are paired by position_id. Its total charges are split
    across whichever legs carry a realized figure, in proportion to the
    quantity each one closed."""
    rows = conn.execute("SELECT id, position_id, quantity, realized, COALESCE(charges, 0) AS charges, "
                        "initial_risk FROM trades").fetchall()
    by_position = {}
    for r in rows:
        by_position.setdefault(r["position_id"], []).append(r)

    updates = []
    for legs in by_position.values():
        total_charges = sum(leg["charges"] for leg in legs)
        closing = [leg for leg in legs if leg["realized"]]
        closed_qty = sum(abs(leg["quantity"] or 0) for leg in closing)
        for leg in legs:
            gross = leg["realized"]
            if gross is None:
                continue
            if leg in closing and closed_qty:
                share = total_charges * abs(leg["quantity"] or 0) / closed_qty
            elif leg in closing:            # a closing leg of unknown size
                share = total_charges / len(closing)
            else:                           # an opening leg: realized is 0.0
                share = 0.0
            net = gross - share
            r_multiple = (net / (leg["initial_risk"] * leg["quantity"])) \
                if leg["initial_risk"] and leg["quantity"] else None
            updates.append((gross, net, r_multiple, leg["id"]))
    conn.executemany("UPDATE trades SET realized_gross=?, realized=?, r_multiple=? WHERE id=?", updates)


def _conn():
    """One connection per thread (the engine's background thread does almost
    all the writing; API-handler threads read)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()
        _local.conn = conn
    return conn


def _j(obj):
    return json.dumps(obj, default=str) if obj is not None else None


# ---- writes ---------------------------------------------------------------

def record_scan(result):
    """One `scans` row and one `scan_rows` row per stock. Together with
    session_closes they are the shadow log of README §115 (the view
    scan_candidates reads them)."""
    m = result.get("market") or {}
    feed = result.get("feed") or {}
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO scans (ts, session_date, bias, nifty_ltp, nifty_chg_pct, vix, adv, dec, "
            "scanned, excluded_count, active_json, reasons_json, feed, quotes_at, nifty_open, nifty_trend, "
            "fii_net_cr) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (result.get("ts", time.time()), result.get("session_date"), m.get("bias"),
             (m.get("nifty") or {}).get("ltp"), (m.get("nifty") or {}).get("chg_pct"), m.get("vix"),
             (m.get("breadth") or {}).get("adv"), (m.get("breadth") or {}).get("dec"),
             result.get("scanned"), result.get("excluded_count"),
             _j(result.get("active")), _j(m.get("reasons")),
             feed.get("prices"), feed.get("quotes_at"), m.get("nifty_open"), (m.get("nifty") or {}).get("trend"),
             (m.get("fii_dii") or {}).get("fii_net_cr")),
        )
        scan_id = cur.lastrowid
        session_date = result.get("session_date")
        rows = [
            (scan_id, session_date, r["symbol"], r.get("side"), r.get("score"), r.get("final_score"),
             r.get("excluded"), r.get("status"), r.get("ltp"), r.get("chg_pct"), r.get("daily_trend"),
             r.get("rs10"), r.get("rvol"), r.get("gap_pct"),
             (r.get("catalyst") or {}).get("score") if r.get("catalyst") else None,
             _j(r.get("swing_patterns")), _j(r.get("reasons")),
             r.get("score_side"), r.get("long_score"), r.get("short_score"),
             None if r.get("long_only") is None else int(bool(r["long_only"])), r.get("feed"), r.get("price_at"),
             r.get("vwap"), r.get("or_high"), r.get("or_low"), r.get("sector_chg_pct"), r.get("sector_trend"),
             r.get("turnover_cr"), r.get("atr_pct"), r.get("shadow_side"))
            for r in result.get("rows", [])
        ]
        c.executemany(
            "INSERT INTO scan_rows (scan_id, session_date, symbol, side, score, final_score, excluded, "
            "status, ltp, chg_pct, daily_trend, rs10, rvol, gap_pct, catalyst_score, swing_pattern, "
            "reasons_json, score_side, long_score, short_score, long_only, feed, price_at, vwap, or_high, "
            "or_low, sector_chg_pct, sector_trend, turnover_cr, atr_pct, shadow_side) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )


def record_session_closes(session_date, quotes, ts=None, source="kite"):
    """Each stock's last traded price at the 15:08 square-off (README §115):
    the outcome every scan of the session is scored against in
    scan_candidates. `quotes` is {name: {"ltp", "last_trade", "at"}} as
    data_provider.kite_quotes returns it. A name whose price is not from this
    session is left out. The first write for a session and name stands.
    Returns the number of rows written."""
    ts = ts or time.time()
    rows = [(session_date, name, float(q["ltp"]), ts, q.get("last_trade") or q.get("at"), source)
            for name, q in (quotes or {}).items()
            if (q.get("ltp") or 0) > 0 and (q.get("last_trade") or q.get("at") or "")[:10] == session_date]
    with _conn() as c:
        before = c.total_changes
        c.executemany("INSERT OR IGNORE INTO session_closes (session_date, symbol, price, ts, last_trade, source) "
                      "VALUES (?,?,?,?,?,?)", rows)
        return c.total_changes - before


def session_closes_recorded(session_date):
    return bool(_conn().execute("SELECT 1 FROM session_closes WHERE session_date = ? LIMIT 1",
                                (session_date,)).fetchone())


def scan_candidates(session_date):
    """The shadow log for one session, in scan order: every stock of every
    scan, its inputs and its return to 15:08 (the scan_candidates view)."""
    return [dict(r) for r in _conn().execute(
        "SELECT * FROM scan_candidates WHERE session_date = ? ORDER BY scan_id, symbol", (session_date,))]


def record_checklist_eval(symbol, ltp, analysis):
    if not analysis or "bull_score" not in analysis:
        return
    with _conn() as c:
        c.execute(
            "INSERT INTO checklist_evals (ts, symbol, ltp, bull_score, bear_score, entry_threshold, "
            "long_ok, short_ok, setup, regime, always_in, news_score, checklist_json, bar_time) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), symbol, ltp, analysis.get("bull_score"), analysis.get("bear_score"),
             analysis.get("entry_threshold"), int(bool(analysis.get("long_ok"))),
             int(bool(analysis.get("short_ok"))), analysis.get("setup"), analysis.get("regime"),
             analysis.get("always_in"), analysis.get("news_score"), _j(analysis.get("checklist")),
             analysis.get("bar_time")),
        )


def record_fno_evaluation(underlying, side, conf, executed: bool, block_reason=None):
    """Every time the engine looks at an underlying for an F&O trade — not
    just the ones that fire — so the knowledge base grows from every
    confidence read, the same reason checklist_evals logs every read instead
    of only executed cash-equity trades. This is what will eventually let a
    later analysis ask 'does the confidence score actually rank F&O outcomes
    better than chance?' once enough of these pair up with closed trades."""
    local = conf.get("local_setup", {})
    sysm = conf.get("system_evidence", {})
    with _conn() as c:
        c.execute(
            "INSERT INTO fno_evaluations (ts, underlying, side, confidence_score, confidence_label, "
            "local_setup_score, edge_margin_pts, categories, regime_clarity_pct, system_multiplier, "
            "system_reason, executed, block_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), underlying, side, conf.get("score"), conf.get("label"),
             local.get("score"), local.get("edge_margin_pts"), local.get("categories"),
             local.get("regime_clarity_pct"), sysm.get("multiplier"), sysm.get("reason"),
             int(executed), block_reason),
        )


def record_fno_entry(position_id, pos: dict):
    """pos is the dict shape trading_engine.py stores in state.fno_positions
    at entry — a point-in-time snapshot of the Greeks/IV/confidence that
    justified the trade, frozen before anyone knows how it turns out."""
    conf = pos.get("confidence") or {}
    greeks = pos.get("entry_greeks") or {}
    with _conn() as c:
        c.execute(
            "INSERT INTO fno_trades (position_id, underlying, tradingsymbol, is_call, strike, expiry, "
            "lot_size, lots, entry_ts, entry_premium, entry_iv_pct, entry_delta, entry_theta, entry_vega, "
            "confidence_score, confidence_label) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (position_id, pos["underlying"], pos["tradingsymbol"], int(pos["is_call"]), pos["strike"],
             pos["expiry"], pos["lot_size"], pos["lots"], time.time(), pos["entry_premium"],
             greeks.get("iv_pct"), greeks.get("delta"), greeks.get("theta"), greeks.get("vega"),
             conf.get("score"), conf.get("label")),
        )


def record_fno_exit(position_id, exit_premium, exit_reason, realized, r_multiple):
    with _conn() as c:
        c.execute(
            "UPDATE fno_trades SET exit_ts=?, exit_premium=?, exit_reason=?, realized=?, r_multiple=? "
            "WHERE position_id=?",
            (time.time(), exit_premium, exit_reason, realized, r_multiple, position_id),
        )


def fno_journal_summary(min_pairs=10):
    """The F&O-equivalent of journal_summary(): how much evidence exists,
    and — once there's enough of it — whether the confidence score has
    actually ranked trades by outcome any better than chance would. Below
    `min_pairs` closed trades this honestly says so instead of guessing."""
    with _conn() as c:
        n_eval = c.execute("SELECT COUNT(*) FROM fno_evaluations").fetchone()[0]
        n_executed = c.execute("SELECT COUNT(*) FROM fno_evaluations WHERE executed=1").fetchone()[0]
        rows = c.execute(
            "SELECT confidence_score, r_multiple FROM fno_trades WHERE r_multiple IS NOT NULL"
        ).fetchall()
        closed = c.execute(
            "SELECT r_multiple FROM fno_trades WHERE r_multiple IS NOT NULL"
        ).fetchall()
    out = {"evaluations_logged": n_eval, "trades_opened": n_executed, "closed_trades": len(closed)}
    if closed:
        rs = [r[0] for r in closed]
        wins = [x for x in rs if x > 0]
        out["win_rate_pct"] = round(len(wins) / len(rs) * 100, 1)
        out["expectancy_r"] = round(sum(rs) / len(rs), 3)
    conf_scores = [r["confidence_score"] for r in rows if r["confidence_score"] is not None]
    r_mults = [r["r_multiple"] for r in rows if r["confidence_score"] is not None]
    if len(conf_scores) < min_pairs:
        out["confidence_ic"] = None
        out["confidence_ic_note"] = (f"Only {len(conf_scores)} closed F&O trades with a recorded confidence "
                                     f"score — need at least {min_pairs} before asking whether confidence "
                                     f"actually predicts outcome means anything.")
    else:
        out["confidence_ic"] = round(_spearman(conf_scores, r_mults), 3)
        out["confidence_ic_note"] = ("Rank correlation between entry confidence and the trade's R-multiple — "
                                     "0 means the confidence score has no relationship to outcome, ±1 is perfect.")
    return out


def record_trade(trade, checklist_snapshot=None):
    with _conn() as c:
        c.execute(
            "INSERT INTO trades (id, position_id, ts, symbol, side, quantity, price, mode, reason, note, "
            "realized, charges, initial_risk, r_multiple, checklist_json, realized_gross, signal_price, order_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (trade["id"], trade.get("position_id"), trade["ts"], trade["symbol"], trade["side"],
             trade["quantity"], trade["price"], trade["mode"], trade.get("reason"), trade.get("note"),
             trade.get("realized"), trade.get("charges"), trade.get("initial_risk"), trade.get("r_multiple"),
             _j(checklist_snapshot), trade.get("realized_gross"), trade.get("signal_price"), trade.get("order_id")),
        )


def record_signal(symbol, signal, detail=None, ts=None):
    with _conn() as c:
        c.execute("INSERT INTO signals (ts, symbol, signal, detail_json) VALUES (?,?,?,?)",
                  (ts or time.time(), symbol, signal, _j(detail)))


def record_activity(kind, message, symbol=None, level="info", ts=None):
    with _conn() as c:
        c.execute("INSERT INTO activity (ts, kind, symbol, message, level) VALUES (?,?,?,?,?)",
                  (ts or time.time(), kind, symbol, message, level))


def new_position_id():
    return str(uuid.uuid4())[:12]


def record_market_breadth(session_date, breadth):
    """One row per real trading day (INSERT OR REPLACE, so re-recording the
    same day just refreshes it — the day's read can only get more complete
    as the session progresses, not less). This history is what
    mcclellan_oscillator() needs; TRIN itself is computed fresh from a
    single live reading (nse_feed.market_breadth()) and doesn't need it."""
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO market_breadth_daily "
            "(session_date, ts, advances, declines, unchanged, total, trin) VALUES (?,?,?,?,?,?,?)",
            (session_date, time.time(), breadth.get("advances"), breadth.get("declines"),
             breadth.get("unchanged"), breadth.get("total"), breadth.get("trin")),
        )


def _ema_series(values, period):
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    ema = sum(values[:period]) / period  # seed with a simple average, standard convention
    out = [ema]
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
        out.append(ema)
    return out


def mcclellan_oscillator(min_days=39):
    """McClellan Oscillator (Murphy, Technical Analysis of the Financial
    Markets ch 10): EMA19(net advances) - EMA39(net advances), where net
    advances = advances - declines each real trading day. A genuine
    day-over-day breadth momentum read, not derivable from one live
    snapshot — needs min_days of real history first, same "not enough
    data yet" discipline as factor_ic()/deflated_sharpe_ratio() elsewhere
    in this journal, not a number nobody should trust with 5 days behind
    it."""
    with _conn() as c:
        rows = c.execute(
            "SELECT session_date, advances, declines FROM market_breadth_daily "
            "WHERE advances IS NOT NULL AND declines IS NOT NULL ORDER BY session_date"
        ).fetchall()
    if len(rows) < min_days:
        return {"oscillator": None, "days": len(rows),
               "note": f"Only {len(rows)} real trading day(s) of breadth history so far — need at least "
                       f"{min_days} before the McClellan Oscillator's 39-day EMA means anything."}
    net = [r["advances"] - r["declines"] for r in rows]
    ema19 = _ema_series(net, 19)
    ema39 = _ema_series(net, 39)
    oscillator = ema19[-1] - ema39[-1]
    return {"oscillator": round(oscillator, 1), "days": len(rows),
           "as_of": rows[-1]["session_date"]}


def record_chaywanaprash_report(lookback_hours, llm_used, narrative, findings, input_tokens=0, output_tokens=0):
    with _conn() as c:
        c.execute(
            "INSERT INTO chaywanaprash_reports "
            "(ts, lookback_hours, llm_used, narrative, findings_json, input_tokens, output_tokens) "
            "VALUES (?,?,?,?,?,?,?)",
            (time.time(), lookback_hours, int(llm_used), narrative, _j(findings), input_tokens, output_tokens),
        )


def record_review(card):
    """A manual-review card, written the moment it is offered — so the table
    holds every setup put in front of the user, not only the approved ones.
    That is what lets a later analysis ask whether the user's approvals beat
    the gates they overrode."""
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO manual_reviews "
            "(id, created_ts, session_date, symbol, side, blocker, mode, status, decided_ts, position_id, "
            " outcome_json, card_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (card["id"], card["created_ts"], card["session_date"], card["symbol"], card["side"],
             (card.get("blocker") or {}).get("key"), card.get("mode"), card["status"], card.get("decided_ts"),
             card.get("position_id"), _j(card.get("outcome")), _j(card)),
        )


def update_review(review_id, status, decided_ts, position_id=None, outcome=None, card=None):
    with _conn() as c:
        c.execute(
            "UPDATE manual_reviews SET status=?, decided_ts=?, position_id=?, outcome_json=?, "
            "card_json=COALESCE(?, card_json) WHERE id=?",
            (status, decided_ts, position_id, _j(outcome), _j(card), review_id),
        )


def update_review_shadow(review_id, shadow):
    with _conn() as c:
        c.execute("UPDATE manual_reviews SET shadow_json=? WHERE id=?", (_j(shadow), review_id))


def reviews_on(session_date):
    """Every card offered on one IST session date, oldest first, as the card
    dicts they were written as (status and outcome current)."""
    with _conn() as c:
        rows = c.execute(
            "SELECT card_json, status, decided_ts, position_id, outcome_json, shadow_json FROM manual_reviews "
            "WHERE session_date = ? ORDER BY created_ts", (session_date,),
        ).fetchall()
    out = []
    for r in rows:
        card = json.loads(r["card_json"]) if r["card_json"] else {}
        card.update({"status": r["status"], "decided_ts": r["decided_ts"], "position_id": r["position_id"],
                     "outcome": json.loads(r["outcome_json"]) if r["outcome_json"] else None,
                     "shadow": json.loads(r["shadow_json"]) if r["shadow_json"] else None})
        out.append(card)
    return out


def record_depth_samples(rows):
    """One tick's order-book snapshots for the watchlist (depth_sampler.py)."""
    cols = ("ts", "symbol", "ltp", "bid", "ask", "spread_bp", "bid_qty1", "ask_qty1", "bid_qty5", "ask_qty5",
            "imbalance5", "volume", "total_buy_qty", "total_sell_qty")
    with _conn() as c:
        c.executemany(f"INSERT INTO depth_samples ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                      [tuple(r.get(k) for k in cols) for r in rows])


def depth_sample_stats():
    with _conn() as c:
        row = c.execute("SELECT COUNT(*) n, COUNT(DISTINCT symbol) s, COUNT(DISTINCT date(ts,'unixepoch','+330 minutes')) d, "
                        "MIN(ts) lo, MAX(ts) hi FROM depth_samples").fetchone()
    return {"rows": row["n"], "symbols": row["s"], "sessions": row["d"], "first_ts": row["lo"], "last_ts": row["hi"]}


def record_liquidity_check(symbol, side, qty, ltp, mode, result):
    """One liquidity.check() reading. Written whether it passed, failed or
    could not be taken, so the table is a sample of real spreads, not only
    of the entries that went through."""
    with _conn() as c:
        c.execute(
            "INSERT INTO liquidity_checks "
            "(ts, symbol, side, qty, ltp, mode, status, ok, reason, spread_bp, impact_bp, entry_depth, exit_depth) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), symbol, side, qty, ltp, mode, result.get("status"), int(bool(result.get("ok"))),
             result.get("reason"), result.get("spread_bp"), result.get("impact_bp"),
             result.get("entry_depth"), result.get("exit_depth")),
        )


def recent_liquidity_checks(limit=100):
    with _conn() as c:
        rows = c.execute("SELECT * FROM liquidity_checks ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def record_research_brief(ts, symbol, snapshot, reports, rating, model_ids, tokens, cost_usd):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO research_briefs "
            "(ts, symbol, snapshot_json, reports_json, rating, model_ids, tokens, cost_usd) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ts, symbol, _j(snapshot), _j(reports), rating, ",".join(model_ids), tokens, cost_usd),
        )
        return cur.lastrowid


def recent_research_briefs(symbol, limit=5):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM research_briefs WHERE symbol = ? ORDER BY ts DESC LIMIT ?", (symbol, limit)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["snapshot"] = json.loads(d.pop("snapshot_json")) if d.get("snapshot_json") else None
        d["reports"] = json.loads(d.pop("reports_json")) if d.get("reports_json") else None
        d["model_ids"] = [m for m in (d.get("model_ids") or "").split(",") if m]
        out.append(d)
    return out


def recent_chaywanaprash_reports(limit=20):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM chaywanaprash_reports ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["findings"] = json.loads(d.pop("findings_json")) if d.get("findings_json") else None
        d["llm_used"] = bool(d["llm_used"])
        out.append(d)
    return out


# ---- reads / knowledge base -------------------------------------------------

def recent_trades(limit=200):
    with _conn() as c:
        rows = c.execute("SELECT * FROM trades ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["checklist"] = json.loads(d.pop("checklist_json")) if d.get("checklist_json") else None
        out.append(d)
    return out


def trades_between(start_ts: float, end_ts: float | None = None):
    """Real fills in a time window, oldest first — used for "today's actual
    trades" (day_plan.py) rather than recent_trades()'s all-time newest-first
    view, which isn't day-scoped."""
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM trades WHERE ts >= ? AND ts <= ? ORDER BY ts ASC",
            (start_ts, end_ts if end_ts is not None else time.time()),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["checklist"] = json.loads(d.pop("checklist_json")) if d.get("checklist_json") else None
        out.append(d)
    return out


def trade_stats():
    """Win rate and expectancy over every closed leg with a known R-multiple —
    the same metrics the backtester reports, now measured on live/paper fills."""
    with _conn() as c:
        rs = [r[0] for r in c.execute("SELECT r_multiple FROM trades WHERE r_multiple IS NOT NULL").fetchall()]
    if not rs:
        return {"closed_trades": 0, "win_rate_pct": None, "expectancy_r": None, "kelly_pct": None}
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    avg_w = sum(wins) / len(wins) if wins else 0.0
    avg_l = sum(losses) / len(losses) if losses else 0.0
    w = len(wins) / len(rs)
    kelly = (w - (1 - w) / (avg_w / abs(avg_l))) if avg_w > 0 and avg_l < 0 else None
    return {
        "closed_trades": len(rs), "win_rate_pct": round(w * 100, 1),
        "expectancy_r": round(sum(rs) / len(rs), 3), "avg_win_r": round(avg_w, 2),
        "avg_loss_r": round(avg_l, 2), "kelly_pct": round(kelly * 100, 1) if kelly is not None else None,
    }


def checklist_blocker_stats(hours=24):
    """What's actually gating entries right now, across every live checklist
    read in the window — not just the ones that became trades (0 trades
    means checklist_item_breakdown() above has nothing to say; this table
    has one). For each required item (pattern, sr, volume, dow, rrr): how
    often it's the thing that fails. Near-misses: evaluations where exactly
    one required item failed — the closest calls to a real trade, and which
    single gate is blocking each. R:R distribution: the real numbers behind
    the rrr item's pass rate, since "99% fail" alone doesn't say whether
    that's close (median 1.3) or nowhere near (median 0.1)."""
    since = time.time() - hours * 3600
    with _conn() as c:
        rows = c.execute(
            "SELECT symbol, ts, checklist_json FROM checklist_evals WHERE ts > ?", (since,)
        ).fetchall()
    fail_counts, pass_counts = {}, {}
    near_misses = {}
    rrr_vals, vol_vals = [], []
    total_sides = 0
    for r in rows:
        cl = json.loads(r["checklist_json"])
        for side in ("long", "short"):
            s = cl.get(side)
            if not s:
                continue
            total_sides += 1
            items = s["items"]
            req = [i for i in items if i["required"]]
            failing = [i["key"] for i in req if not i["ok"]]
            for k in failing:
                fail_counts[k] = fail_counts.get(k, 0) + 1
            for i in req:
                if i["ok"]:
                    pass_counts[i["key"]] = pass_counts.get(i["key"], 0) + 1
            if len(failing) == 1:
                near_misses[failing[0]] = near_misses.get(failing[0], 0) + 1
            if s.get("rrr") is not None:
                rrr_vals.append(s["rrr"])
            vol_item = next((i for i in items if i["key"] == "volume"), None)
            if vol_item:
                m = re.search(r"([\d.]+)×", vol_item["detail"])
                if m:
                    vol_vals.append(float(m.group(1)))

    def _summary(vals):
        if not vals:
            return None
        vals = sorted(vals)
        n = len(vals)
        return {
            "n": n, "min": round(vals[0], 2), "max": round(vals[-1], 2),
            "median": round(vals[n // 2], 2), "mean": round(sum(vals) / n, 2),
            "pct_at_or_above_1_5": round(sum(1 for v in vals if v >= 1.5) / n * 100, 1),
        }

    return {
        "window_hours": hours,
        "total_evaluations": total_sides,
        "required_item_fail_counts": fail_counts,
        "required_item_pass_counts": pass_counts,
        "near_misses_by_lone_blocker": near_misses,
        "rrr_distribution": _summary(rrr_vals),
        "volume_ratio_distribution": _summary(vol_vals),
    }


# Ordering near-misses needs care. Only `rrr` is a continuous quantity, so it
# is the one required item where "how close did it come" is a real measurement
# (1.42 against a 1.5 bar is nearly there; 0.1 is not). Every other required
# item is a boolean — a pattern either formed or it didn't — and inventing a
# distance for those would be asserting a closeness that was never measured.
# So rrr-blocked near-misses sort first, by rrr descending; the rest follow,
# most recent first, and are reported as "no distance to report".
SESSION_SUMMARY_KIND = "summary"
SESSION_SUMMARY_PREFIX = "Session summary for "
_NEAR_MISS_UNRANKED = "boolean gate — no distance to the bar to report"


def _min_rrr():
    """The live reward-to-risk bar, read the same way trading_engine does
    (config.STRATEGY_PARAMS[config.STRATEGY]) so a strategy switch moves the
    summary's bar with it. Importing trader_brain here just for DEFAULTS
    would pull brooks/indicators/market_structure into database.py."""
    return config.STRATEGY_PARAMS.get(config.STRATEGY, {}).get("min_rrr", 1.5)


def _entry_window():
    """(no_entry_before, last_entry_time, no_entry_windows) as the live
    strategy reads them, so the summary applies the same window trader_brain
    does: a pass is only tried if no_entry_before <= bar < last_entry_time."""
    p = config.STRATEGY_PARAMS.get(config.STRATEGY, {})
    return p.get("no_entry_before", "09:30"), p.get("last_entry_time", "14:30"), p.get("no_entry_windows", [])


def _bar_hhmm(bar_time, ts, ist):
    """HH:MM of the bar a read was judged on. Rows written before #82 carry no
    bar_time; for those, the last finished 5-minute bar at the time of the
    read (its start, floored to 5 minutes, minus one bar) is the best
    available estimate. When data was delayed (yfinance) the real bar is
    earlier than this, so near 14:30 an old read can be placed just outside
    the window when it was really inside. New rows record the bar itself."""
    if bar_time and len(str(bar_time)) >= 16:
        return str(bar_time)[11:16]
    t = datetime.fromtimestamp(ts, ist)
    start = t.replace(minute=t.minute - t.minute % 5, second=0, microsecond=0) - timedelta(minutes=5)
    return start.strftime("%H:%M")


COVERAGE_GAP_MIN = 5


def _session_coverage(read_ts, day, ist):
    """Which part of the session the engine actually evaluated, from the
    checklist reads themselves (not the OS: a sleeping laptop writes nothing,
    and that absence is the evidence).

    The session runs from MARKET_OPEN to SQUARE_OFF_TIME, since the engine
    stops reading at square-off. A gap of more than COVERAGE_GAP_MIN minutes
    between consecutive reads (or before the first / after the last) is
    counted as uncovered, so a sleeping machine is never mistaken for a quiet
    market."""
    def at(hhmm):
        h, m = (int(x) for x in hhmm.split(":"))
        return datetime.combine(day, datetime.min.time(), tzinfo=ist).replace(hour=h, minute=m).timestamp()
    open_ts, close_ts = at(config.MARKET_OPEN), at(config.SQUARE_OFF_TIME)
    ts = sorted(t for t in read_ts if open_ts <= t <= close_ts)
    session_min = round((close_ts - open_ts) / 60)
    hm = lambda t: datetime.fromtimestamp(t, ist).strftime("%H:%M")
    if not ts:
        return {"first": None, "last": None, "session_min": session_min, "uncovered_min": session_min,
                "gaps": [[config.MARKET_OPEN, config.SQUARE_OFF_TIME]]}
    edges = [open_ts] + ts + [close_ts]
    gaps, uncovered = [], 0.0
    for a, b in zip(edges, edges[1:]):
        if b - a > COVERAGE_GAP_MIN * 60:
            gaps.append([hm(a), hm(b)])
            uncovered += b - a
    return {"first": hm(ts[0]), "last": hm(ts[-1]), "session_min": session_min,
            "uncovered_min": round(uncovered / 60), "gaps": gaps}


def session_summary(session_date=None, near_miss_limit=5):
    """Why a session ended with the trade count it did.

    Answers the question the blocker counts can't: on a day with no trades,
    which single gate came closest to letting one through, and on which
    stock. `checklist_blocker_stats()` aggregates a rolling window across
    every gate at once; this is one IST calendar day, and it names the
    individual evaluations that were one item short.

    A near-miss is an evaluation where exactly one *required* checklist item
    failed. `full_passes` counts distinct (symbol, side) setups where none
    did AND the bar sat inside the entry window: those are the ones that
    reach the entry path, where the confidence gate and the risk caps in
    trading_engine._try_enter() then apply, so full_passes > 0 with
    entries == 0 points downstream of the checklist, not at it. Passes
    outside the window are never tried and are counted separately
    (`full_passes_outside_window`); `full_pass_reads` keeps the raw count of
    evaluations, since the engine re-reads a setup every ~38 s (#82).
    """
    ist = ZoneInfo("Asia/Kolkata")
    day = datetime.now(ist).date() if session_date is None \
        else datetime.fromisoformat(session_date).date()
    start = datetime.combine(day, datetime.min.time(), tzinfo=ist).timestamp()
    end = start + 86400

    with _conn() as c:
        rows = c.execute(
            "SELECT symbol, ts, checklist_json, bar_time FROM checklist_evals WHERE ts >= ? AND ts < ? ORDER BY ts",
            (start, end),
        ).fetchall()
        # Distinct position_id whose *first* leg landed in the window: an exit
        # of a position opened on an earlier day is not an entry taken today,
        # and counting legs would double-count every round trip.
        opened = c.execute(
            "SELECT COUNT(*) FROM (SELECT position_id FROM trades WHERE position_id IS NOT NULL "
            "GROUP BY position_id HAVING MIN(ts) >= ? AND MIN(ts) < ?)",
            (start, end),
        ).fetchone()[0]

    fail_counts = {}
    near_misses = {}
    candidates = []
    symbols = set()
    pass_reads = 0
    passes_in, passes_out = set(), set()
    win_from, win_to, win_blocked = _entry_window()
    total_sides = 0
    for r in rows:
        try:
            cl = json.loads(r["checklist_json"])
        except (TypeError, ValueError):
            continue
        for side in ("long", "short"):
            s = cl.get(side)
            if not s:
                continue
            total_sides += 1
            symbols.add(r["symbol"])
            req = [i for i in s.get("items", []) if i.get("required")]
            failing = [i for i in req if not i.get("ok")]
            for i in failing:
                fail_counts[i["key"]] = fail_counts.get(i["key"], 0) + 1
            if not failing:
                pass_reads += 1
                hhmm = _bar_hhmm(r["bar_time"], r["ts"], ist)
                in_window = win_from <= hhmm < win_to and not any(a <= hhmm < b for a, b in win_blocked)
                (passes_in if in_window else passes_out).add((r["symbol"], side))
            elif len(failing) == 1:
                blocker = failing[0]
                near_misses[blocker["key"]] = near_misses.get(blocker["key"], 0) + 1
                rrr = s.get("rrr") if blocker["key"] == "rrr" else None
                candidates.append({
                    "symbol": r["symbol"], "side": side, "ts": r["ts"],
                    "time_ist": datetime.fromtimestamp(r["ts"], ist).strftime("%H:%M"),
                    "blocker": blocker["key"],
                    "blocker_label": blocker.get("label"),
                    "detail": blocker.get("detail"),
                    "rrr": rrr,
                    "shortfall": None if rrr is None else round(_min_rrr() - rrr, 2),
                    "ranked_by": "rrr" if rrr is not None else _NEAR_MISS_UNRANKED,
                })

    # Collapse to one row per (symbol, side, blocker) before ranking. The
    # engine re-reads the checklist every tick, so a setup that sits just
    # under the bar for half an hour produces ~60 near-identical rows —
    # verified against a real session, where the unfiltered top 5 was the
    # same DRREDDY long five times over. Keep that symbol-side's best look
    # (highest rrr; for a boolean gate, its latest) and carry how many
    # evaluations it held for, which is the genuinely new information: a
    # setup that hovered at 1.26 for 40 minutes is a different fact from
    # one that touched it on a single tick.
    best = {}
    for n in candidates:
        key = (n["symbol"], n["side"], n["blocker"])
        prev = best.get(key)
        if prev is None:
            n["occurrences"] = 1
            best[key] = n
            continue
        prev["occurrences"] += 1
        better = (n["rrr"] > prev["rrr"]) if (n["rrr"] is not None and prev["rrr"] is not None) \
            else (n["ts"] > prev["ts"])
        if better:
            n["occurrences"] = prev["occurrences"]
            best[key] = n
    candidates = list(best.values())

    # rrr-blocked first (highest rrr = closest to the bar), then the boolean
    # gates most-recent-first. -ts as the tiebreaker keeps the sort total.
    candidates.sort(key=lambda n: (0 if n["rrr"] is not None else 1,
                                   -(n["rrr"] if n["rrr"] is not None else 0),
                                   -n["ts"]))

    return {
        "session_date": day.isoformat(),
        "evaluations": total_sides,
        "symbols_evaluated": len(symbols),
        "full_passes": len(passes_in),
        "full_passes_outside_window": len(passes_out - passes_in),
        "full_pass_reads": pass_reads,
        "entry_window": [win_from, win_to],
        "coverage": _session_coverage([r["ts"] for r in rows], day, ist),
        "entries_taken": opened,
        "required_item_fail_counts": fail_counts,
        "near_misses_by_lone_blocker": near_misses,
        "near_misses": candidates[:near_miss_limit],
        "distinct_near_misses": len(candidates),
        "min_rrr": _min_rrr(),
    }


PREOPEN_KITE_KIND = "kite_preopen"


def activity_kind_logged_on(kind, session_date):
    """True if an activity of `kind` was recorded on this IST date, so a
    once-a-day alert survives a restart (the engine's own guard is in memory)."""
    ist = ZoneInfo("Asia/Kolkata")
    day = datetime.fromisoformat(session_date).date()
    start = datetime.combine(day, datetime.min.time(), tzinfo=ist).timestamp()
    with _conn() as c:
        row = c.execute("SELECT 1 FROM activity WHERE kind = ? AND ts >= ? AND ts < ? LIMIT 1",
                        (kind, start, start + 86400)).fetchone()
    return row is not None


def get_control(key, default=None):
    """A dashboard control that must survive a restart (the entry pause).
    Kept in the journal because it is the one store every engine instance
    already points at, and tests already isolate it."""
    with _conn() as c:
        row = c.execute("SELECT value FROM control WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_control(key, value):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO control (key, value, ts) VALUES (?, ?, ?)",
                  (key, json.dumps(value), time.time()))


def record_day_list(session_date, symbols, fixed_ts, fixed_when, mode="liquidity"):
    """The day's list, written when it is fixed (#198). The first list written
    for a session stands: a later write for the same session is ignored, so
    the list read back after a restart is the one the session started with,
    with the time it was first fixed. Returns the list the journal holds."""
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO day_lists (session_date, symbols_json, fixed_ts, fixed_when, mode) "
                  "VALUES (?, ?, ?, ?, ?)", (session_date, json.dumps(list(symbols)), fixed_ts, fixed_when, mode))
    return get_day_list(session_date)


def _day_list_row(row):
    if row is None:
        return None
    return {"session": row["session_date"], "symbols": json.loads(row["symbols_json"]),
            "fixed_ts": row["fixed_ts"], "when": row["fixed_when"], "mode": row["mode"]}


def get_day_list(session_date):
    """The list fixed for this session, or None."""
    with _conn() as c:
        row = c.execute("SELECT * FROM day_lists WHERE session_date = ?", (session_date,)).fetchone()
    return _day_list_row(row)


def latest_day_list(mode="liquidity"):
    """The most recent list fixed in this mode: the one a scanner that had
    been running all along would hold. Whether it is still the current
    session's is the scanner's decision (Scanner.day_list_for)."""
    with _conn() as c:
        row = c.execute("SELECT * FROM day_lists WHERE mode = ? ORDER BY session_date DESC LIMIT 1",
                        (mode,)).fetchone()
    return _day_list_row(row)


def session_summary_logged_on(session_date):
    """True if the end-of-session summary for this IST date is already in the
    activity log. The engine's once-a-day guard is in-memory, so without this
    an evening restart would re-log the same summary; the activity table is
    the only thing that survives the restart."""
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM activity WHERE kind = ? AND message LIKE ? LIMIT 1",
            (SESSION_SUMMARY_KIND, f"{SESSION_SUMMARY_PREFIX}{session_date}:%"),
        ).fetchone()
    return row is not None


def session_summary_line(summary):
    """The one-line rendering trading_engine logs to the activity stream when
    a session closes. Kept next to session_summary() so the wording and the
    numbers can't drift apart."""
    date = summary["session_date"]
    evals, entries = summary["evaluations"], summary["entries_taken"]
    # Said first, before any count: a day the engine only half-saw is not
    # evidence about the market. On 23 Sep the laptop slept 09:14-10:38 and the
    # summary read like a quiet day. Silent when the whole session was covered.
    cov = summary.get("coverage") or {}
    coverage = ""
    if evals and cov.get("uncovered_min", 0) > 0:
        spans = ", ".join(f"{a}–{b}" for a, b in cov["gaps"])
        coverage = (f" Coverage: engine evaluated {cov['first']}–{cov['last']}; {cov['uncovered_min']} min of the "
                    f"{config.MARKET_OPEN}–{config.SQUARE_OFF_TIME} session not covered ({spans}).")
    if not evals:
        return f"{SESSION_SUMMARY_PREFIX}{date}: no checklist evaluations ran — the engine saw no active watchlist."
    if entries:
        return (f"{SESSION_SUMMARY_PREFIX}{date}: {entries} position(s) opened from {evals:,} checklist "
                f"evaluations across {summary['symbols_evaluated']} stocks.{coverage}")

    # Distinct setups inside the entry window, not raw reads (#82): the engine
    # re-reads a setup every ~38 s, and a pass after the cutoff is never tried.
    out_of_window = summary.get("full_passes_outside_window", 0)
    win = summary.get("entry_window") or ["09:30", "14:30"]
    head = (f"{SESSION_SUMMARY_PREFIX}{date}: no trades.{coverage} {evals:,} checklist evaluations across "
            f"{summary['symbols_evaluated']} stocks produced {summary['full_passes']} setup(s) passing every "
            f"required item inside the {win[0]}–{win[1]} entry window"
            + (f" (plus {out_of_window} outside it, never tried)" if out_of_window else ""))
    near = summary["near_misses"]
    if not near:
        counts = summary["required_item_fail_counts"]
        worst = max(counts, key=counts.get) if counts else None
        tail = f"; nothing came within one item of passing (most-failed gate: {worst})." if worst \
            else "; nothing came within one item of passing."
        return head + tail
    n = near[0]
    if n["rrr"] is not None:
        held = f", held for {n['occurrences']} evaluations" if n.get("occurrences", 1) > 1 else ""
        closest = (f"{n['symbol']} {n['side']} at {n['time_ist']}, reward-to-risk {n['rrr']:.2f} "
                   f"against the {summary['min_rrr']:g} bar — short by {n['shortfall']:.2f}{held}")
    else:
        closest = (f"{n['symbol']} {n['side']} at {n['time_ist']}, blocked on "
                   f"{n['blocker']} ({_NEAR_MISS_UNRANKED})")
    # Count distinct symbol-sides, not raw evaluations: the raw tally counts
    # the same setup once per 30s tick (595 on a day that was really 30-odd
    # situations), which reads as far more near-activity than there was.
    distinct = summary["distinct_near_misses"]
    return (head + f". {distinct} setup(s) came within one item of passing; "
                   f"closest was {closest}.")

_BLOCKED_MSG_RE = re.compile(r"^(?P<setup>.+?) signal skipped — (?P<why>.+)$", re.DOTALL)
# Mirrors the exact f-strings trading_engine._try_enter() / confidence.score_trade()
# build the message from — greedy .* is deliberate: system_multiplier_reason can itself
# contain parentheses (a Scorecard criterion name like "Predictive skill (Information
# Coefficient)"), and greedy backtracking still finds the real trailing "))" at the end
# of the string regardless. bar uses [\d.]+, not \d+: min_confidence_to_trade is an int
# today but nothing in config.py guarantees that stays true (e.g. a tuning pass landing
# a fractional threshold) — parsed as float either way. DOTALL for the same reason
# _BLOCKED_MSG_RE has it: mult_reason shouldn't break the match if it ever spans lines.
_CONF_BLOCK_RE = re.compile(
    r"^confidence (?P<score>\d+)/100 below the (?P<bar>[\d.]+) bar \("
    r"Local setup scored (?P<local>\d+)/100, scaled by a (?P<mult>[\d.]+)x system-evidence factor \("
    r"(?P<mult_reason>.*)\)\)$",
    re.DOTALL,
)


def recent_blocked_signals(hours=24, limit=100):
    """Every signal that reached trading_engine._try_enter() and got logged
    as 'blocked' in the window — checklist-passing setups that still didn't
    trade. Parses the confidence-gate breakdown (local setup score, system
    multiplier, exact reason) back out of the activity message when that's
    why, so the dashboard can show it structured instead of as a log line.
    Falls back to the raw message for every other block reason (position
    sizing to 0, max open positions, sector cap, risk-off bias, etc.) —
    this never fails to return a row just because the message didn't match
    the confidence-gate shape."""
    since = time.time() - hours * 3600
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, symbol, message FROM activity WHERE kind = 'blocked' AND ts > ? "
            "ORDER BY ts DESC LIMIT ?", (since, limit),
        ).fetchall()
    out = []
    for r in rows:
        m = _BLOCKED_MSG_RE.match(r["message"])
        setup, why = (m.group("setup"), m.group("why")) if m else (None, r["message"])
        entry = {"ts": r["ts"], "symbol": r["symbol"], "setup": setup, "reason": why, "reason_type": "other"}
        cm = _CONF_BLOCK_RE.match(why)
        if cm:
            entry.update({
                "reason_type": "confidence_gate",
                "final_score": int(cm.group("score")),
                "min_confidence_bar": float(cm.group("bar")),
                "local_setup_score": int(cm.group("local")),
                "system_multiplier": float(cm.group("mult")),
                "system_multiplier_reason": cm.group("mult_reason"),
            })
        out.append(entry)
    return out


def recent_activity_issues(hours=24, limit=50):
    """Warn/error-level activity rows in the window — the same table the
    Live Log UI reads, filtered to what's actually worth a human or
    Chaywanaprash's attention."""
    since = time.time() - hours * 3600
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, kind, symbol, message, level FROM activity "
            "WHERE ts > ? AND level IN ('warn', 'error') ORDER BY ts DESC LIMIT ?",
            (since, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def checklist_item_breakdown():
    """For each checklist item (pattern, sr, volume, dow, indicators, catalyst, rrr),
    the win rate and average R of closed trades where that item passed vs failed at
    entry — the plain-English version of asking "which rule actually matters"."""
    with _conn() as c:
        rows = c.execute(
            "SELECT checklist_json, r_multiple FROM trades "
            "WHERE r_multiple IS NOT NULL AND checklist_json IS NOT NULL"
        ).fetchall()
    by_item = {}
    for row in rows:
        cl = json.loads(row["checklist_json"]) or {}
        for it in cl.get("items", []):
            bucket = by_item.setdefault(it["key"], {"pass": [], "fail": []})
            bucket["pass" if it["ok"] else "fail"].append(row["r_multiple"])
    out = {}
    for key, buckets in by_item.items():
        out[key] = {
            side: {"n": len(vals), "avg_r": round(sum(vals) / len(vals), 2) if vals else None,
                  "win_rate_pct": round(sum(1 for v in vals if v > 0) / len(vals) * 100, 1) if vals else None}
            for side, vals in buckets.items()
        }
    return out


def _rank(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def _spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    rx, ry = _rank(xs), _rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def _last_reading_per_symbol_session(rows):
    """rows: sqlite3.Row objects with id, session_date, symbol, f, chg_pct,
    ordered by symbol, session_date, id. Collapses repeated intraday
    re-scans of the same (symbol, session_date) down to one reading — the
    latest — per group.

    Real bug this fixes: scan_rows gets one row per scan, and a symbol is
    scanned repeatedly through a session (every 5-60 min) — all sharing the
    same session_date and, while the market's closed, an identical frozen
    score/chg_pct (verified live: RELIANCE had 59 rows for one Friday
    session, every single one f=58.1, chg_pct=-1.3, from repeated
    market-closed preview scans). Treating every raw row as an independent
    (session, symbol) observation — the original factor_ic() did — counts
    those 59 near-duplicate rows as 59 independent data points feeding a
    rank correlation, when they're really one. That inflated a real
    session's worth of evidence (~1 genuine transition per symbol so far)
    into an apparent 8,091 "pairs" and a falsely narrow confidence interval
    around the Information Coefficient this gates real trading decisions
    on (confidence.py's system-evidence multiplier)."""
    latest = {}
    for r in rows:
        latest[(r["symbol"], r["session_date"])] = (r["f"], r["chg_pct"])
    by_symbol = {}
    for (symbol, session_date), (f, chg) in latest.items():
        by_symbol.setdefault(symbol, []).append((session_date, f, chg))
    return by_symbol


def _ic_from_by_symbol(by_symbol, field, min_pairs):
    xs, ys = [], []
    for series in by_symbol.values():
        series.sort(key=lambda t: t[0])
        for i in range(len(series) - 1):
            xs.append(series[i][1])
            ys.append(series[i + 1][2])
    if len(xs) < min_pairs:
        return {"field": field, "ic": None, "pairs": len(xs),
               "note": f"Only {len(xs)} independent (session, symbol) pairs so far — need at least "
                       f"{min_pairs} before an Information Coefficient means anything (ML4Trading ch 1: breadth)."}
    ic = _spearman(xs, ys)
    if ic is None:
        # Every value on one side is tied (e.g. a pattern whose score or
        # chg_pct happened to be identical across all its pairs so far) —
        # _spearman() correctly refuses a divide-by-zero rather than
        # returning a fake number; surface that honestly instead of
        # crashing on round(None, ...).
        return {"field": field, "ic": None, "pairs": len(xs),
               "note": "No variance in the data yet (every pair tied on one side) — "
                       "a rank correlation isn't defined until that changes."}
    return {"field": field, "ic": round(ic, 3), "pairs": len(xs)}


def factor_ic(field="final_score", min_sessions=20, min_stocks_per_session=20):
    """Information Coefficient (ML4Trading ch 1 / Grinold): did a stock's
    score on one session rank how it moved on the NEXT session it was
    scanned? Computed the standard way for a ranking signal — one
    cross-sectional rank correlation PER session transition, averaged
    across sessions, with a t-stat.

    Why per session, not pooled (README §38): this used to pool every
    (stock, next-session) pair into one correlation and ask for only 20
    pairs. That graded "pass" on a single day — 100 stocks, Sep 11 -> Sep 15,
    a day the whole market fell — because one day's stocks all move with the
    same market; they're nowhere near 100 independent observations. Across
    434 replayed sessions the scanner's daily IC is 0.000 (§37). Breadth, in
    Grinold's sense, is independent bets over time.

    Reports nothing until `min_sessions` separate transitions exist, each
    with at least `min_stocks_per_session` stocks. One reading per
    (symbol, session_date) — see _last_reading_per_symbol_session."""
    with _conn() as c:
        rows = c.execute(
            f"SELECT id, session_date, symbol, {field} AS f, chg_pct FROM scan_rows "
            f"WHERE {field} IS NOT NULL AND chg_pct IS NOT NULL ORDER BY symbol, session_date, id"
        ).fetchall()
    by_symbol = _last_reading_per_symbol_session(rows)
    by_transition = {}
    for series in by_symbol.values():
        series.sort(key=lambda t: t[0])
        for (d0, score, _), (d1, _, next_chg) in zip(series, series[1:]):
            xs, ys = by_transition.setdefault((d0, d1), ([], []))
            xs.append(score)
            ys.append(next_chg)

    daily = _daily_ics(by_transition, min_stocks_per_session)
    base = {"field": field, "pairs": sum(len(xs) for xs, _ in by_transition.values()),
            "sessions": len(daily), "min_sessions": min_sessions}
    if len(daily) < min_sessions:
        return {**base, "ic": None, "t_stat": None,
               "note": f"Only {len(daily)} separate session transition(s) with {min_stocks_per_session}+ stocks so "
                       f"far — need at least {min_sessions}. One day's stocks all move with the same market, so a "
                       f"single day's cross-section isn't evidence of ranking skill (README §37-38)."}
    stats = _mean_ic_with_t(daily)
    if stats is None:
        return {**base, "ic": None, "t_stat": None,
               "note": "Identical IC on every session — no day-to-day variance to judge significance against."}
    return {**base, **stats}


def _daily_ics(groups, min_stocks_per_session):
    """One Spearman rank IC per cross-section ({session_key: (xs, ys)}) that
    has enough stocks, in session order — the per-session method of §38."""
    daily = []
    for key in sorted(groups):
        xs, ys = groups[key]
        if len(xs) >= min_stocks_per_session:
            ic = _spearman(xs, ys)
            if ic is not None:
                daily.append(ic)
    return daily


def _mean_ic_with_t(daily):
    """Mean daily IC, its t-stat and the share of positive sessions — or None
    when every session's IC is identical (no variance to test against)."""
    mean = sum(daily) / len(daily)
    sd = math.sqrt(sum((x - mean) ** 2 for x in daily) / (len(daily) - 1))
    if sd == 0:
        return None
    return {"ic": round(mean, 3), "t_stat": round(mean / sd * math.sqrt(len(daily)), 2),
            "pct_sessions_positive": round(sum(x > 0 for x in daily) / len(daily) * 100)}


def research_rating_ic(min_sessions=20, min_stocks_per_session=20):
    """Does the Research Desk's rating (-2..+2) rank how stocks actually
    moved in the session it was predicting? Same method as factor_ic():
    one rank correlation per session, averaged, with a t-stat, and nothing
    reported until there are `min_sessions` sessions with
    `min_stocks_per_session`+ rated stocks each.

    The predicted session is the first scanned session that starts after the
    brief was written: a brief from before the open (config.MARKET_OPEN)
    predicts that day, anything later predicts the next session. Its return is
    that session's chg_pct from scan_rows (latest reading, as in factor_ic).
    Only the latest brief per (symbol, predicted session) counts."""
    with _conn() as c:
        briefs = c.execute(
            "SELECT ts, symbol, rating FROM research_briefs WHERE rating IS NOT NULL ORDER BY ts, id"
        ).fetchall()
        rows = c.execute(
            "SELECT symbol, session_date, chg_pct FROM scan_rows "
            "WHERE chg_pct IS NOT NULL ORDER BY symbol, session_date, id"
        ).fetchall()
    session_return = {}
    for r in rows:
        session_return[(r["symbol"], r["session_date"])] = r["chg_pct"]
    sessions_by_symbol = {}
    for symbol, session_date in session_return:
        sessions_by_symbol.setdefault(symbol, []).append(session_date)

    ist = ZoneInfo("Asia/Kolkata")
    latest = {}
    for b in briefs:
        written = datetime.fromtimestamp(b["ts"], ist)
        day = written.date().isoformat()
        before_open = written.strftime("%H:%M") < config.MARKET_OPEN
        target = next((d for d in sorted(sessions_by_symbol.get(b["symbol"], []))
                       if (d >= day if before_open else d > day)), None)
        if target is not None:
            latest[(b["symbol"], target)] = b["rating"]

    by_session = {}
    for (symbol, session_date), rating in latest.items():
        xs, ys = by_session.setdefault(session_date, ([], []))
        xs.append(rating)
        ys.append(session_return[(symbol, session_date)])

    daily = _daily_ics(by_session, min_stocks_per_session)
    base = {"field": "research_rating", "rated_pairs": len(latest), "sessions": len(daily),
            "min_sessions": min_sessions, "min_stocks_per_session": min_stocks_per_session,
            "min_t_stat": evaluation.IC_MIN_T_STAT}
    if len(daily) < min_sessions:
        return {**base, "ic": None, "t_stat": None, "passes": False,
                "note": f"Not enough data: {len(daily)} of {min_sessions} sessions have "
                        f"{min_stocks_per_session}+ rated stocks with a known next-session return. "
                        f"The rating gets no weight anywhere until this clears t >= {evaluation.IC_MIN_T_STAT:g}."}
    stats = _mean_ic_with_t(daily)
    if stats is None:
        return {**base, "ic": None, "t_stat": None, "passes": False,
                "note": "Identical IC on every session — no day-to-day variance to judge significance against."}
    passes = stats["ic"] > 0 and stats["t_stat"] >= evaluation.IC_MIN_T_STAT
    return {**base, **stats, "passes": passes,
            "note": "Positive and consistent enough to consider as an input (after a benchmark backtest)."
            if passes else "No consistent predictive skill yet — the rating stays research-only."}


def _swing_pattern_names(raw_json):
    """scan_rows.swing_pattern holds a JSON array of dicts (name/side/stop/
    level — see database.record_scan()), not a bare string. A row can carry
    more than one real pattern at once (e.g. a Double Top AND a Head and
    Shoulders Top on the same read) — yield each name separately so both
    get credit, rather than treating the whole raw JSON string as one
    compound category (which would silently fragment "Double Top" alone
    from "Double Top + Head and Shoulders Top" into two unrelated buckets)."""
    try:
        parsed = json.loads(raw_json) if raw_json else []
    except (ValueError, TypeError):
        return []
    return [p["name"] for p in parsed if isinstance(p, dict) and p.get("name")]


def dimag_ki_batti(field="final_score", min_pairs=20):
    """"Dimag ki batti" (the lightbulb moment) — of the platform's real,
    already-tagged setup patterns (scan_rows.swing_pattern — Bulkowski daily
    patterns and Murphy reversal days, see swing_patterns.py), which one
    currently shows the strongest genuine result, using the same honest,
    deduplicated-to-one-reading-per-(symbol,session_date) IC as factor_ic().
    Deliberately does NOT invent a new pattern or force a winner: with
    fewer than min_pairs observations for every real pattern (the honest
    state this early in live logging), it says that plainly rather than
    picking one anyway — the whole point is a real lightbulb, not a
    manufactured one."""
    with _conn() as c:
        rows = c.execute(
            f"SELECT id, session_date, symbol, swing_pattern, {field} AS f, chg_pct FROM scan_rows "
            f"WHERE {field} IS NOT NULL AND chg_pct IS NOT NULL "
            f"AND swing_pattern IS NOT NULL AND swing_pattern NOT IN ('', '[]') "
            f"ORDER BY symbol, session_date, id"
        ).fetchall()

    # One reading per (symbol, session_date, pattern_name) — same dedup
    # reasoning as factor_ic(), applied per pattern since a symbol's set of
    # detected patterns can itself change scan to scan.
    latest = {}
    for r in rows:
        for name in _swing_pattern_names(r["swing_pattern"]):
            latest[(r["symbol"], r["session_date"], name)] = (r["f"], r["chg_pct"])

    by_pattern_symbol = {}
    for (symbol, session_date, name), (f, chg) in latest.items():
        by_pattern_symbol.setdefault(name, {}).setdefault(symbol, []).append((session_date, f, chg))

    by_pattern = {name: _ic_from_by_symbol(by_symbol, field, min_pairs)
                 for name, by_symbol in by_pattern_symbol.items()}
    qualifying = {k: v for k, v in by_pattern.items() if v["ic"] is not None}
    if not qualifying:
        return {"winner": None, "by_pattern": by_pattern,
                "note": f"No real pattern has {min_pairs}+ independent (session, symbol) observations "
                        f"yet — too early to say which one actually works, not evidence that none do."}
    best = max(qualifying.items(), key=lambda kv: kv[1]["ic"])
    return {"winner": {"pattern": best[0], **best[1]}, "by_pattern": by_pattern, "note": None}


def journal_summary(include_backtest_evidence=True):
    """The dashboard's journal numbers and the Scorecard the confidence gate
    reads. The Scorecard includes the backtest-evidence row by default, so
    the live gate knows what two years of backtests measured. backtester.py
    passes include_backtest_evidence=False: a backtest judging a NEW rule set
    must not be blocked by the old rule set's verdict."""
    with _conn() as c:
        n_scans = c.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        n_evals = c.execute("SELECT COUNT(*) FROM checklist_evals").fetchone()[0]
        n_trades = c.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        first_ts = c.execute("SELECT MIN(ts) FROM scans").fetchone()[0]
        rs = [r[0] for r in c.execute("SELECT r_multiple FROM trades WHERE r_multiple IS NOT NULL").fetchall()]
    ts, ic = trade_stats(), factor_ic("final_score")
    n_trials = evaluation.trial_count()
    dsr = evaluation.deflated_sharpe_ratio(rs, n_trials) if n_trials else \
        {"dsr": None, "note": "No backtest trials logged yet (run backtester.py) — nothing to compare against."}
    return {
        "scans_logged": n_scans, "checklist_evals_logged": n_evals, "trades_logged": n_trades,
        "logging_since": first_ts,
        "trade_stats": ts,
        "checklist_item_breakdown": checklist_item_breakdown(),
        "factor_ic": ic,
        "scorecard": evaluation.scorecard(ts, dsr, ic, backtest_row=evaluation.backtest_evidence_row(
            evaluation.load_backtest_evidence(), config.STRATEGY,
            {**config.STRATEGY_PARAMS.get(config.STRATEGY, {}), "interval": config.CANDLE_INTERVAL})
            if include_backtest_evidence else None),
    }
