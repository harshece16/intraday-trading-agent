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

Single-writer (the trading engine's background thread) so no connection
pooling is needed; SQLite's own locking covers the occasional API-thread read.
"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
import uuid
from pathlib import Path

import evaluation

DB_PATH = Path(__file__).parent / "data" / "sahab_journal.db"
_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL, session_date TEXT, bias TEXT,
    nifty_ltp REAL, nifty_chg_pct REAL, vix REAL, adv INTEGER, dec INTEGER,
    scanned INTEGER, excluded_count INTEGER, active_json TEXT, reasons_json TEXT
);
CREATE TABLE IF NOT EXISTS scan_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL, session_date TEXT, symbol TEXT NOT NULL, side TEXT,
    score REAL, final_score REAL, excluded TEXT, status TEXT,
    ltp REAL, chg_pct REAL, daily_trend TEXT, rs10 REAL, rvol REAL, gap_pct REAL,
    catalyst_score REAL, swing_pattern TEXT, reasons_json TEXT
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
    realized REAL, charges REAL, initial_risk REAL, r_multiple REAL, checklist_json TEXT
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
"""


def _conn():
    """One connection per thread (the engine's background thread does almost
    all the writing; API-handler threads read)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        conn.commit()
        _local.conn = conn
    return conn


def _j(obj):
    return json.dumps(obj, default=str) if obj is not None else None


# ---- writes ---------------------------------------------------------------

def record_scan(result):
    m = result.get("market") or {}
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO scans (ts, session_date, bias, nifty_ltp, nifty_chg_pct, vix, adv, dec, "
            "scanned, excluded_count, active_json, reasons_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (result.get("ts", time.time()), result.get("session_date"), m.get("bias"),
             (m.get("nifty") or {}).get("ltp"), (m.get("nifty") or {}).get("chg_pct"), m.get("vix"),
             (m.get("breadth") or {}).get("adv"), (m.get("breadth") or {}).get("dec"),
             result.get("scanned"), result.get("excluded_count"),
             _j(result.get("active")), _j(m.get("reasons"))),
        )
        scan_id = cur.lastrowid
        session_date = result.get("session_date")
        rows = [
            (scan_id, session_date, r["symbol"], r.get("side"), r.get("score"), r.get("final_score"),
             r.get("excluded"), r.get("status"), r.get("ltp"), r.get("chg_pct"), r.get("daily_trend"),
             r.get("rs10"), r.get("rvol"), r.get("gap_pct"),
             (r.get("catalyst") or {}).get("score") if r.get("catalyst") else None,
             _j(r.get("swing_patterns")), _j(r.get("reasons")))
            for r in result.get("rows", [])
        ]
        c.executemany(
            "INSERT INTO scan_rows (scan_id, session_date, symbol, side, score, final_score, excluded, "
            "status, ltp, chg_pct, daily_trend, rs10, rvol, gap_pct, catalyst_score, swing_pattern, "
            "reasons_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )


def record_checklist_eval(symbol, ltp, analysis):
    if not analysis or "bull_score" not in analysis:
        return
    with _conn() as c:
        c.execute(
            "INSERT INTO checklist_evals (ts, symbol, ltp, bull_score, bear_score, entry_threshold, "
            "long_ok, short_ok, setup, regime, always_in, news_score, checklist_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), symbol, ltp, analysis.get("bull_score"), analysis.get("bear_score"),
             analysis.get("entry_threshold"), int(bool(analysis.get("long_ok"))),
             int(bool(analysis.get("short_ok"))), analysis.get("setup"), analysis.get("regime"),
             analysis.get("always_in"), analysis.get("news_score"), _j(analysis.get("checklist"))),
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
            "realized, charges, initial_risk, r_multiple, checklist_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (trade["id"], trade.get("position_id"), trade["ts"], trade["symbol"], trade["side"],
             trade["quantity"], trade["price"], trade["mode"], trade.get("reason"), trade.get("note"),
             trade.get("realized"), trade.get("charges"), trade.get("initial_risk"), trade.get("r_multiple"),
             _j(checklist_snapshot)),
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


def factor_ic(field="final_score", min_pairs=20):
    """Information Coefficient (ML4Trading ch 1 / Grinold): the rank correlation
    between a factor's value on one session and the SAME stock's move on the
    NEXT session it was scanned — i.e. did today's score actually predict
    tomorrow's return? Needs at least `min_pairs` independent (session, symbol)
    observations to mean anything (the book's "breadth" of the bet); returns
    None with a reason below that, rather than a number nobody should trust."""
    with _conn() as c:
        rows = c.execute(
            f"SELECT session_date, symbol, {field} AS f, chg_pct FROM scan_rows "
            f"WHERE {field} IS NOT NULL AND chg_pct IS NOT NULL ORDER BY symbol, session_date"
        ).fetchall()
    by_symbol = {}
    for r in rows:
        by_symbol.setdefault(r["symbol"], []).append((r["session_date"], r["f"], r["chg_pct"]))
    xs, ys = [], []
    for series in by_symbol.values():
        series.sort(key=lambda t: t[0])
        for i in range(len(series) - 1):
            xs.append(series[i][1])
            ys.append(series[i + 1][2])
    if len(xs) < min_pairs:
        return {"field": field, "ic": None, "pairs": len(xs),
               "note": f"Only {len(xs)} (session, symbol) pairs so far — need at least {min_pairs} "
                       f"before an Information Coefficient means anything (ML4Trading ch 1: breadth)."}
    return {"field": field, "ic": round(_spearman(xs, ys), 3), "pairs": len(xs)}


def journal_summary():
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
        "scorecard": evaluation.scorecard(ts, dsr, ic),
    }
