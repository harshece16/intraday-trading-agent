"""
The Kronos space: a database and readers for the forecasts of research look L40.

Kronos is an open-source price-forecasting model (a transformer over
candlestick bars). The project tests it as research look L40
(docs/research/prereg-kronos-feature-ic.md, README section 93). Research
processes that live outside the live path write their output as JSON files:

- ``backend/data/kronos_shadow_<date>.json`` and ``..._summary.json``, written
  by ``backend/research/kronos_shadow.py`` during a session: one forecast per
  stock per quarter hour on the scanner's list, and the target that later
  happened;
- ``docs/research/data/kronos_l40_stage0.json``, ``..._stage0_pc.json`` and
  ``kronos_l40_result.json``, written by the L40 pass itself.

This module reads those files into its own sqlite database,
``backend/data/kronos.db``, and reads that database back for the dashboard's
Kronos page. That is all it does. It is written only by research processes
(through the files it ingests) and read only by two display routes in
``app.py``; no decision in the engine reads it, and the engine never writes to
it (README section 102, rule RES-32).

Live path: reads data files and a sqlite database only. Never imports torch,
the vendored Kronos code or anything under ``backend/research/``
(``tests/test_research_splits.py::test_no_live_module_imports_research``).

Python 3.9 compatible.
"""
import json
import logging
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("trading_bot")

BACKEND_DIR = Path(__file__).parent
DATA_DIR = BACKEND_DIR / "data"
DOCS_DATA_DIR = BACKEND_DIR.parent / "docs" / "research" / "data"
DB_PATH = Path(os.environ.get("SAHAB_KRONOS_DB_PATH") or DATA_DIR / "kronos.db")

HORIZONS = ("f15", "f30", "f60")
SHADOW_DAY_RE = re.compile(r"^kronos_shadow_(\d{4}-\d{2}-\d{2})\.json$")
SHADOW_SUMMARY_RE = re.compile(r"^kronos_shadow_(\d{4}-\d{2}-\d{2})_summary\.json$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# The research records the store keeps, by file name, with the kind shown on the page.
RUN_FILES = (
    ("l40_stage0", "stage0", "kronos_l40_stage0.json"),
    ("l40_stage0_pc", "stage0", "kronos_l40_stage0_pc.json"),
    ("l40_result", "result", "kronos_l40_result.json"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS shadow_forecasts (
    date TEXT NOT NULL, hhmm TEXT NOT NULL, symbol TEXT NOT NULL,
    computed_at TEXT, c0 REAL, f15 REAL, f30 REAL, f60 REAL, m60 REAL,
    bars_delayed INTEGER, kite_active INTEGER,
    scanner_side TEXT, scanner_score REAL, scanner_final_score REAL, scanner_ltp REAL,
    scanner_gap_pct REAL, scanner_rvol REAL, scanner_feed TEXT,
    target_f15 REAL, target_f30 REAL, target_f60 REAL, pred_close_json TEXT,
    PRIMARY KEY (date, hhmm, symbol)
);
CREATE TABLE IF NOT EXISTS shadow_days (
    date TEXT PRIMARY KEY, sample_count INTEGER, device TEXT, rows INTEGER, stocks INTEGER, times INTEGER,
    bars_live INTEGER, bars_delayed INTEGER, running_json TEXT, summary_json TEXT, updated TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    name TEXT PRIMARY KEY, kind TEXT, recorded_at TEXT, source_path TEXT, payload_json TEXT
);
"""


# ---- the database --------------------------------------------------------------


def _connect(db_path=None):
    """A short-lived connection. This database is not the engine's journal: nothing
    holds a connection open, and a busy timeout covers a research process ingesting
    at the same moment as a page request."""
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _read_json(path):
    """The file, or None when it is missing or half-written. The shadow rewrites its
    day file every quarter hour; a reader that lands mid-write skips it this time."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        logger.info("kronos store: skipping %s this time (%s)", os.path.basename(str(path)), exc)
        return None


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _flag(x):
    return None if x is None else int(bool(x))


# ---- ingest ----------------------------------------------------------------------


def _forecast_row(date, r):
    """The row's date is the file's: a day file holds one session."""
    feats = r.get("features") or {}
    sc = r.get("scanner") or {}
    tg = r.get("targets") or {}
    return (
        date, r.get("hhmm"), r.get("symbol"), r.get("computed_at"), _num(r.get("c0")),
        _num(feats.get("f15")), _num(feats.get("f30")), _num(feats.get("f60")), _num(r.get("m60")),
        _flag(r.get("bars_delayed")), _flag(r.get("kite_active")),
        sc.get("side"), _num(sc.get("score")), _num(sc.get("final_score")), _num(sc.get("ltp")),
        _num(sc.get("gap_pct")), _num(sc.get("rvol")), sc.get("feed"),
        _num(tg.get("f15")), _num(tg.get("f30")), _num(tg.get("f60")),
        json.dumps(r.get("pred_close")) if r.get("pred_close") is not None else None,
    )


_UPSERT_FORECAST = """
INSERT INTO shadow_forecasts (date, hhmm, symbol, computed_at, c0, f15, f30, f60, m60, bars_delayed, kite_active,
    scanner_side, scanner_score, scanner_final_score, scanner_ltp, scanner_gap_pct, scanner_rvol, scanner_feed,
    target_f15, target_f30, target_f60, pred_close_json)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(date, hhmm, symbol) DO UPDATE SET
    computed_at=excluded.computed_at, c0=excluded.c0, f15=excluded.f15, f30=excluded.f30, f60=excluded.f60,
    m60=excluded.m60, bars_delayed=excluded.bars_delayed, kite_active=excluded.kite_active,
    scanner_side=excluded.scanner_side, scanner_score=excluded.scanner_score,
    scanner_final_score=excluded.scanner_final_score, scanner_ltp=excluded.scanner_ltp,
    scanner_gap_pct=excluded.scanner_gap_pct, scanner_rvol=excluded.scanner_rvol, scanner_feed=excluded.scanner_feed,
    target_f15=excluded.target_f15, target_f30=excluded.target_f30, target_f60=excluded.target_f60,
    pred_close_json=excluded.pred_close_json
"""

# The day file and the summary file each carry part of a day's row. Each upsert
# keeps what the other file wrote (COALESCE), so ingesting one never blanks the other.
_UPSERT_DAY_FROM_DAY_FILE = """
INSERT INTO shadow_days (date, sample_count, device, rows, stocks, times, bars_live, bars_delayed, running_json, updated)
VALUES (?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(date) DO UPDATE SET
    sample_count=COALESCE(excluded.sample_count, shadow_days.sample_count),
    device=COALESCE(excluded.device, shadow_days.device),
    rows=excluded.rows, stocks=excluded.stocks, times=excluded.times,
    bars_live=excluded.bars_live, bars_delayed=excluded.bars_delayed,
    running_json=excluded.running_json, updated=COALESCE(excluded.updated, shadow_days.updated)
"""

_UPSERT_DAY_FROM_SUMMARY = """
INSERT INTO shadow_days (date, sample_count, device, rows, stocks, times, bars_live, bars_delayed, summary_json, updated)
VALUES (?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(date) DO UPDATE SET
    sample_count=COALESCE(excluded.sample_count, shadow_days.sample_count),
    device=COALESCE(excluded.device, shadow_days.device),
    rows=COALESCE(excluded.rows, shadow_days.rows), stocks=COALESCE(excluded.stocks, shadow_days.stocks),
    times=COALESCE(excluded.times, shadow_days.times),
    bars_live=COALESCE(excluded.bars_live, shadow_days.bars_live),
    bars_delayed=COALESCE(excluded.bars_delayed, shadow_days.bars_delayed),
    summary_json=excluded.summary_json, updated=COALESCE(shadow_days.updated, excluded.updated)
"""


def _ingest_day_file(conn, date, doc):
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict) and r.get("symbol") and r.get("hhmm")]
    conn.executemany(_UPSERT_FORECAST, [_forecast_row(date, r) for r in rows])
    delayed = sum(1 for r in rows if r.get("bars_delayed"))
    conn.execute(_UPSERT_DAY_FROM_DAY_FILE, (
        date, doc.get("sample_count"), doc.get("device"), len(rows),
        len({r["symbol"] for r in rows}), len({r["hhmm"] for r in rows}),
        len(rows) - delayed, delayed,
        json.dumps(doc.get("running") or {}), doc.get("updated"),
    ))
    return len(rows)


def _ingest_summary_file(conn, date, doc):
    bars = doc.get("bars") or {}
    conn.execute(_UPSERT_DAY_FROM_SUMMARY, (
        date, doc.get("sample_count"), doc.get("device"), doc.get("rows"), doc.get("stocks"), doc.get("times"),
        bars.get("live"), bars.get("delayed"), json.dumps(doc), doc.get("updated"),
    ))


def ingest_shadow_files(data_dir=None, db_path=None):
    """Read every kronos_shadow_<date>.json and kronos_shadow_<date>_summary.json in
    ``data_dir`` into the store. Upserts, so a day file rewritten with targets filled
    in overwrites the NULLs of the earlier read. A file that cannot be parsed (being
    rewritten at that moment) is skipped this time and named in the result."""
    data_dir = Path(data_dir or DATA_DIR)
    found = {"days": 0, "rows": 0, "summaries": 0, "skipped": []}
    if not data_dir.is_dir():
        return found
    names = sorted(os.listdir(str(data_dir)))
    with closing(_connect(db_path)) as conn:
        for name in names:
            m = SHADOW_DAY_RE.match(name)
            if not m:
                continue
            doc = _read_json(data_dir / name)
            if not isinstance(doc, dict):
                found["skipped"].append(name)
                continue
            found["days"] += 1
            found["rows"] += _ingest_day_file(conn, m.group(1), doc)
        for name in names:
            m = SHADOW_SUMMARY_RE.match(name)
            if not m:
                continue
            doc = _read_json(data_dir / name)
            if not isinstance(doc, dict):
                found["skipped"].append(name)
                continue
            found["summaries"] += 1
            _ingest_summary_file(conn, m.group(1), doc)
        conn.commit()
    return found


def _recorded_at(doc, path):
    for key in ("finished", "started", "updated"):
        if isinstance(doc.get(key), str):
            return doc[key]
    stage0 = doc.get("stage0") if isinstance(doc.get("stage0"), dict) else {}
    if isinstance(stage0.get("started"), str):
        return stage0["started"]
    try:
        return datetime.fromtimestamp(os.path.getmtime(str(path))).isoformat(timespec="seconds")
    except OSError:
        return None


def ingest_run_files(docs_data_dir=None, db_path=None):
    """Read the L40 records (stage 0 on the Mac, stage 0 on the PC, the result) that
    exist in ``docs_data_dir`` into the ``runs`` table, whole, as payload_json."""
    docs_data_dir = Path(docs_data_dir or DOCS_DATA_DIR)
    found = {"runs": [], "skipped": []}
    with closing(_connect(db_path)) as conn:
        for name, kind, filename in RUN_FILES:
            path = docs_data_dir / filename
            if not path.is_file():
                continue
            doc = _read_json(path)
            if not isinstance(doc, dict):
                found["skipped"].append(filename)
                continue
            conn.execute(
                "INSERT INTO runs (name, kind, recorded_at, source_path, payload_json) VALUES (?,?,?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET kind=excluded.kind, recorded_at=excluded.recorded_at, "
                "source_path=excluded.source_path, payload_json=excluded.payload_json",
                (name, kind, _recorded_at(doc, path), "docs/research/data/" + filename, json.dumps(doc)),
            )
            found["runs"].append(name)
        conn.commit()
    return found


# ---- readers ---------------------------------------------------------------------


def _loads(text, default):
    if not text:
        return default
    try:
        return json.loads(text)
    except ValueError:
        return default


def _display_row(r):
    """One forecast as the page shows it: features, scanner fields and targets grouped."""
    targets = {h: r["target_" + h] for h in HORIZONS}
    return {
        "date": r["date"], "hhmm": r["hhmm"], "symbol": r["symbol"], "computed_at": r["computed_at"],
        "c0": r["c0"], "f15": r["f15"], "f30": r["f30"], "f60": r["f60"], "m60": r["m60"],
        "bars_delayed": bool(r["bars_delayed"]) if r["bars_delayed"] is not None else None,
        "kite_active": bool(r["kite_active"]) if r["kite_active"] is not None else None,
        "scanner": {"side": r["scanner_side"], "score": r["scanner_score"], "final_score": r["scanner_final_score"],
                    "ltp": r["scanner_ltp"], "gap_pct": r["scanner_gap_pct"], "rvol": r["scanner_rvol"],
                    "feed": r["scanner_feed"]},
        "targets": targets if any(v is not None for v in targets.values()) else None,
        "pred_close": _loads(r["pred_close_json"], None),
    }


def _day_record(row):
    running = _loads(row["running_json"], {})
    summary = _loads(row["summary_json"], None)
    return {
        "date": row["date"], "sample_count": row["sample_count"], "device": row["device"],
        "rows": row["rows"], "stocks": row["stocks"], "times": row["times"],
        "bars_live": row["bars_live"], "bars_delayed": row["bars_delayed"], "updated": row["updated"],
        "running": running if isinstance(running, dict) else {},
        "summary": summary if isinstance(summary, dict) else None,
    }


def shadow_day(date=None, db_path=None):
    """The full shadow day: its rows, running statistics and summary. ``date`` None
    means the latest day. None when there is no such day."""
    with closing(_connect(db_path)) as conn:
        if date is None:
            row = conn.execute("SELECT * FROM shadow_days ORDER BY date DESC LIMIT 1").fetchone()
        else:
            row = conn.execute("SELECT * FROM shadow_days WHERE date = ?", (date,)).fetchone()
        if row is None:
            return None
        day = _day_record(row)
        rows = conn.execute("SELECT * FROM shadow_forecasts WHERE date = ? ORDER BY hhmm, symbol",
                            (day["date"],)).fetchall()
    day["forecasts"] = [_display_row(r) for r in rows]
    times = sorted({r["hhmm"] for r in day["forecasts"]})
    day["hhmm_list"] = times
    day["latest_hhmm"] = times[-1] if times else None
    day["realised"] = sum(1 for r in day["forecasts"] if r["targets"])
    return day


def _ic_line(stats):
    """Per horizon: the mean rank IC, its t and the number of times behind it."""
    out = {}
    for h in HORIZONS:
        s = stats.get(h) if isinstance(stats, dict) else None
        ic = (s or {}).get("ic") or {}
        out[h] = {"mean": ic.get("mean"), "t": ic.get("t"), "times": (s or {}).get("times", (s or {}).get("sessions"))}
    return out


def shadow_days(db_path=None):
    """One record per shadow day, newest first, with the day's IC per horizon."""
    with closing(_connect(db_path)) as conn:
        rows = conn.execute("SELECT * FROM shadow_days ORDER BY date DESC").fetchall()
    out = []
    for row in rows:
        d = _day_record(row)
        stats = (d["summary"] or {}).get("stats") or d["running"]
        d["ic"] = _ic_line(stats)
        d["agreement"] = (d["summary"] or {}).get("share_of_forecasts_on_the_scanners_side")
        d.pop("running")
        d.pop("summary")
        out.append(d)
    return out


def runs(db_path=None):
    """The research records, as stored."""
    with closing(_connect(db_path)) as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY name").fetchall()
    return [{"name": r["name"], "kind": r["kind"], "recorded_at": r["recorded_at"],
             "source_path": r["source_path"], "payload": _loads(r["payload_json"], {})} for r in rows]


# ---- the look, summarised for display ------------------------------------------------


def _stage0_summary(rec):
    """The fields the page shows from a stage 0 record. Every field is optional:
    the record's shape is the research script's, and the page must not break
    when a field is missing."""
    doc = rec.get("payload") or {}
    s0 = doc.get("stage0") if isinstance(doc.get("stage0"), dict) else {}
    harness = doc.get("harness") if isinstance(doc.get("harness"), dict) else {}
    regression = s0.get("regression") if isinstance(s0.get("regression"), dict) else {}
    timing = s0.get("timing") if isinstance(s0.get("timing"), dict) else {}
    coverage = s0.get("coverage") if isinstance(s0.get("coverage"), dict) else {}
    adjustment = s0.get("adjustment") if isinstance(s0.get("adjustment"), dict) else {}
    lookahead = s0.get("lookahead") if isinstance(s0.get("lookahead"), list) else []
    revisions = []
    for repo, info in (s0.get("revisions") or {}).items():
        picked = (info or {}).get("picked") if isinstance(info, dict) else None
        if isinstance(picked, (list, tuple)) and len(picked) >= 2:
            revisions.append({"repo": repo, "commit": str(picked[0])[:8], "date": str(picked[1])[:10]})
    return {
        "name": rec.get("name"), "source_path": rec.get("source_path"), "status": doc.get("status"),
        "started": s0.get("started"), "selection": s0.get("selection"),
        "machine": harness.get("machine"), "device": harness.get("device"), "threads": harness.get("threads"),
        "torch": harness.get("torch"), "python": harness.get("python"),
        "regression": regression.get("result"), "regression_seconds": regression.get("seconds"),
        "revisions": revisions,
        "lookahead_identical": sum(1 for x in lookahead if isinstance(x, dict) and x.get("identical")),
        "lookahead_n": len(lookahead),
        "seconds_per_forecast": timing.get("seconds_per"),
        "est_hours_at_sample_count_3": timing.get("est_hours_at_sample_count_3"),
        "sample_count_chosen": timing.get("sample_count_chosen"),
        "sessions": coverage.get("sessions"), "first_half": coverage.get("first_half"),
        "second_half": coverage.get("second_half"), "stock_times": coverage.get("stock_times"),
        "dropped_count": adjustment.get("dropped_count"),
    }


def _stat(block):
    block = block if isinstance(block, dict) else {}
    halves = block.get("halves") if isinstance(block.get("halves"), list) else []
    return {"mean": block.get("mean"), "t": block.get("t"), "p": block.get("p"), "n": block.get("n"),
            "pct_pos": block.get("pct_pos"),
            "halves": [(h or {}).get("mean") if isinstance(h, dict) else None for h in halves[:2]]}


def _result_summary(rec):
    doc = rec.get("payload") or {}
    result = doc.get("result") if isinstance(doc.get("result"), dict) else {}
    summaries = result.get("summaries") if isinstance(result.get("summaries"), dict) else {}
    gate = result.get("gate") if isinstance(result.get("gate"), dict) else {}
    horizons = {}
    for h in HORIZONS:
        s = summaries.get(h) if isinstance(summaries.get(h), dict) else None
        if s is None:
            continue
        g = gate.get(h) if isinstance(gate.get(h), dict) else {}
        horizons[h] = {
            "sessions": s.get("sessions"),
            "ic": _stat(s.get("ic")), "pic": _stat(s.get("pic")), "spread": _stat(s.get("spread")),
            "top": _stat(s.get("top")), "bottom": _stat(s.get("bottom")),
            "passes": g.get("passes"), "checks": g.get("checks") if isinstance(g.get("checks"), dict) else {},
            "single_side_note": g.get("single_side_note") if isinstance(g.get("single_side_note"), dict) else {},
        }
    return {
        "name": rec.get("name"), "source_path": rec.get("source_path"), "status": doc.get("status"),
        "finished": doc.get("finished"), "constants": doc.get("constants") if isinstance(doc.get("constants"), dict) else {},
        "horizons": horizons,
    }


def look_summary(records):
    """What the page's "The test" card shows: each stage 0 record and the result."""
    stage0 = [_stage0_summary(r) for r in records if r.get("kind") == "stage0"]
    results = [_result_summary(r) for r in records if r.get("kind") == "result"]
    return {"stage0": stage0, "result": results[0] if results else None}


# ---- what the routes return ---------------------------------------------------------


def page(today=None, data_dir=None, docs_data_dir=None, db_path=None):
    """GET /api/kronos. Ingests first (a few small files), so the page is current
    without a restart of anything."""
    ingest_shadow_files(data_dir, db_path)
    ingest_run_files(docs_data_dir, db_path)
    day = shadow_day(today, db_path) if today else None
    if day is None:
        day = shadow_day(None, db_path)
    return {
        "look": look_summary(runs(db_path)),
        "today": day,
        "date_today": today,
        "days": shadow_days(db_path),
        "prereg": "docs/research/prereg-kronos-feature-ic.md",
    }


def day_page(date, data_dir=None, db_path=None):
    """GET /api/kronos/day/{date}. None for a date the store has no day for."""
    if not DATE_RE.match(date or ""):
        return None
    ingest_shadow_files(data_dir, db_path)
    return shadow_day(date, db_path)
