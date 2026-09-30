"""Research look L49 — do the scanner audit's four intraday features, or the overnight-gap
reversal, rank the next intraday move past cost?

Pre-registered: docs/research/prereg-scanner-features.md (commit dc06a10), before this
file was written; amendment 1 (6baae5a) before it was committed. The harness is L40's (kronos_feature_ic), unchanged and called, not
copied: its sample (build_samples), targets (target_bp), control (m60_bp), per-session
statistics (session_stats), summaries (summarise), gate and Benjamini-Hochberg. What
this file adds is five features and their stage 0.

    F1 gap           (09:15 open / previous official close - 1), continuation-signed
    F2 rvol          volume to t / mean volume to t on the 20 prior regular sessions
    F3 vwap_dist     (close at t / session VWAP to t - 1)
    F4 sector        leave-one-out mean of the industry's moves since their previous close
    F5 gap_reversal  -(close at 09:45 / previous official close - 1), 09:45 only

Order, as the prereg fixes it: stage 0 (nine checks, no feature compared with any
return) -> committed and pushed -> independent review -> ONE measurement pass.

Data, all read-only: the Kite 5-minute cache (SQLite mode=ro, rows before 2026-01-02
only), NSE's 2025 bhavcopies, NSE's 2025 corporate-actions file, NSE's symbol-change
file and research/data/l49_industries.csv. kite_history is not imported: it imports
config, which touches credential files. No Kite call is made.

From backend/, pointing at the main checkout's cache and NSE files:
    KRONOS_CANDLE_DB=<...>/backend/data/kite_history.db SAHAB_RESEARCH_DATA=<...>/backend/data \\
        nice -n 15 .venv/bin/python -m research.scanner_features_l49 --stage0
    ... --measure --review-note "<who approved stage 0, when>"      # once, after the review

Measurement only: no strategy, no backtest, no trial (the count stays at 202). Nothing
in the live path imports this (tests/test_research_splits.py).
"""
import argparse
import bisect
import csv
import hashlib
import io
import json
import math
import os
import platform
import random
import re
import sqlite3
import subprocess
import sys
import time
import zipfile
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import indicators  # noqa: E402  the scanner's own VWAP formula
from research import kronos_feature_ic as k  # noqa: E402
from research import nse_prices  # noqa: E402
from research import splits  # noqa: E402

# ---- the pre-registration's constants, named once -----------------------------------

PREREG = "docs/research/prereg-scanner-features.md"
PREREG_COMMIT = "dc06a10"
FEATURES = ("gap", "rvol", "vwap_dist", "sector", "gap_reversal")
AUDIT_FEATURES = ("gap", "rvol", "vwap_dist", "sector")
GAP_REVERSAL_TIME = "09:45"
TESTS = OrderedDict([("%s_%s" % (f, h), (f, h)) for f in AUDIT_FEATURES for h in k.HORIZONS])
TESTS["gap_reversal_f60"] = ("gap_reversal", "f60")
N_TESTS = 13
RVOL_SESSIONS = 20
REGULAR_OPEN = "09:15"
CUTOFF = splits.HELD_OUT_START                      # nothing on or after 2026-01-02 is read
BHAV_START = "2025-08-01"                           # the earliest bhavcopy a check needs
CONTROL_START, CONTROL_END = "2025-05-01", "2025-08-29"
ALIGN_TOL_BP = 5.0
ALIGN_MIN_SHARE = 0.95
MISSING_MAX_SHARE = 0.01
LOOKAHEAD_N = 200
HAND_N = 5
HAND_TOL_BP = 1e-9
CONTROL_NOISE_BP = 5.0                              # amendment 1: the positive control's noise
SEED = 123
L40_EXPECTED = {"sessions": 79, "sessions_with_data": 78, "stock_times": 43362, "halves": [39, 40]}
PREREGISTERED_REASONS = ("ca_exdate", "ca_volume_unit", "singleton_industry", "rvol_short_baseline",
                         "ca_exdate_peers")
IST = timezone(timedelta(hours=5, minutes=30))

CANDLE_DB = os.environ.get("KRONOS_CANDLE_DB") or os.path.join(BACKEND, "data", "kite_history.db")
DATA = os.environ.get("SAHAB_RESEARCH_DATA") or os.path.join(BACKEND, "data")
BHAV_DIR = os.path.join(DATA, "bhav_daily")
CA_FILE = os.path.join(DATA, "corp_actions", "ca_2025.csv")
SYMBOLCHANGE = os.path.join(BHAV_DIR, "symbolchange.csv")
INDUSTRIES = os.path.join(HERE, "data", "l49_industries.csv")
REPO = os.path.dirname(BACKEND)
OUT_DIR = os.path.join(REPO, "docs", "research", "data")
STAGE0_OUT = os.path.join(OUT_DIR, "l49_stage0.json")
RESULT_OUT = os.path.join(OUT_DIR, "l49_result.json")
L40_RECORD = os.path.join(OUT_DIR, "kronos_l40_result.json")

assert len(FEATURES) == 5 and len(TESTS) == N_TESTS


# ---- data, read-only ----------------------------------------------------------------

def connect_ro(path):
    """The candle cache, opened so that nothing can be written to it."""
    if not os.path.exists(path):
        raise SystemExit("no candle cache at %s" % path)
    return sqlite3.connect("file:%s?mode=ro" % path, uri=True)


def day_start_ts(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST).timestamp())


def bar_time(ts):
    """The string kite_history.load gives a bar on a machine set to IST."""
    return datetime.fromtimestamp(ts, IST).replace(tzinfo=None).isoformat()


def load_candles(conn, symbols, before=CUTOFF):
    """{symbol: [bars, oldest first]} in kite_history.load's shape, for `symbols` in
    sorted order (as L40's load_batch gave them), rows before `before` only."""
    wanted = set(symbols)
    out = OrderedDict((s, []) for s in sorted(wanted))
    sql = ("SELECT symbol, ts, open, high, low, close, volume FROM candles "
           "WHERE interval='5m' AND ts < ? ORDER BY symbol, ts")
    for sym, ts, o, h, lo, c, v in conn.execute(sql, (day_start_ts(before),)):
        if sym in wanted:
            out[sym].append({"time": bar_time(ts), "open": o, "high": h, "low": lo, "close": c, "volume": v})
    out = OrderedDict((s, b) for s, b in out.items() if b)
    latest = max(b[-1]["time"] for b in out.values()) if out else None
    if latest and latest[:10] >= before:
        raise RuntimeError("read a bar dated %s, on or after %s" % (latest, before))
    return out, latest


def fetch_runs(conn):
    rows = conn.execute("SELECT date(fetched_at, 'unixepoch', '+330 minutes') d, COUNT(*) FROM fetched "
                        "WHERE interval='5m' AND fetched_at IS NOT NULL GROUP BY d ORDER BY d").fetchall()
    return [{"date": d, "spans": n} for d, n in rows]


def fetched_rows(conn):
    rows = conn.execute("SELECT symbol, from_date, to_date, fetched_at FROM fetched WHERE interval='5m'").fetchall()
    return [{"symbol": s, "from_date": f, "to_date": t, "fetched_at": a} for s, f, t, a in rows]


def adjustment_drops(rows, symbols, sessions):
    """L40's stage 0 step 5 (kronos_feature_ic.stage0_adjustment) without kite_history."""
    bounds = k.adjustment_boundaries(rows)
    dropped = {}
    for sym in symbols:
        if sym in bounds:
            bad = [d for d in sessions if k.straddles(bounds[sym], sessions, d)]
            if bad:
                dropped[sym] = bad
    return dropped


BHAV_NAME = re.compile(r"(\d{4})(\d{2})(\d{2})\.zip$")


def bhav_files(bhav_dir, start, end=CUTOFF):
    """[(iso date, path)] of the daily files dated start <= day < end, never 2026."""
    out = []
    for name in sorted(os.listdir(bhav_dir)):
        m = BHAV_NAME.match(name)
        if not m:
            continue
        day = "%s-%s-%s" % m.groups()
        if start <= day < end and day < CUTOFF:
            out.append((day, os.path.join(bhav_dir, name)))
    return out


def parse_bhav(path):
    """EQ rows of one daily bhavcopy: (symbol, iso date, open, high, low, close, last)."""
    out = []
    with zipfile.ZipFile(path) as z, z.open(z.namelist()[0]) as fh:
        for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="ignore")):
            r = {key.strip(): (v or "").strip() for key, v in r.items() if key}
            if "TckrSymb" in r:
                if r.get("SctySrs") != "EQ":
                    continue
                out.append((r["TckrSymb"], r["TradDt"], float(r.get("OpnPric") or 0), float(r.get("HghPric") or 0),
                            float(r.get("LwPric") or 0), float(r.get("ClsPric") or 0), float(r.get("LastPric") or 0)))
            elif "SYMBOL" in r:
                if r.get("SERIES") != "EQ":
                    continue
                ts = r["TIMESTAMP"]
                try:
                    d = datetime.strptime(ts, "%d-%b-%Y").date().isoformat()
                except ValueError:
                    d = datetime.strptime(ts, "%d-%b-%y").date().isoformat()
                out.append((r["SYMBOL"], d, float(r.get("OPEN") or 0), float(r.get("HIGH") or 0),
                            float(r.get("LOW") or 0), float(r.get("CLOSE") or 0), float(r.get("LAST") or 0)))
    return out


def load_bhav(files, symbols, nxt):
    """{(cache symbol, iso date): {open, high, low, close, last}} for `symbols`, with
    NSE's old symbols mapped to the cache's through the symbol-change chains."""
    wanted, cache, out, mismatched = set(symbols), {}, {}, []
    for day, path in files:
        for sym, d, o, h, lo, c, last in parse_bhav(path):
            canon = nse_prices.canonical(sym, nxt, cache)
            if canon not in wanted:
                continue
            if d != day:
                mismatched.append((os.path.basename(path), d))
            out.setdefault((canon, d), {"open": o, "high": h, "low": lo, "close": c, "last": last})
    return out, sorted(set(mismatched))


def is_unit_change(purpose):
    """A split, bonus or consolidation: the unit volume is counted in changes."""
    return bool(nse_prices.RX_SPLIT_KW.search(purpose) or nse_prices.RX_BONUS_KW.search(purpose)
                or nse_prices.RX_CONSOLIDATION.search(purpose))


def load_corporate_actions(path, nxt):
    """({symbol: {ex-dates}}, {symbol: {ex-dates of unit changes}}) from one yearly file."""
    if os.path.basename(path) >= "ca_2026":
        raise RuntimeError("the 2026 corporate-actions file is not read")
    dates, unit, cache = defaultdict(set), defaultdict(set), {}
    with open(path, encoding="utf-8-sig", errors="ignore") as fh:
        for r in csv.DictReader(fh):
            r = {key.strip().strip('"'): (v or "").strip() for key, v in r.items() if key}
            try:
                ex = datetime.strptime(r["EX-DATE"], "%d-%b-%Y").date().isoformat()
            except (KeyError, ValueError):
                continue
            sym = nse_prices.canonical(r.get("SYMBOL", ""), nxt, cache)
            dates[sym].add(ex)
            if is_unit_change(r.get("PURPOSE", "")):
                unit[sym].add(ex)
    return dict(dates), dict(unit)


def load_industries(path=None):
    with open(path or INDUSTRIES, newline="") as f:
        return {r["symbol"]: r["industry"] for r in csv.DictReader(f)}


# ---- the features (pure: read only what a Ctx holds) ---------------------------------

class Ctx:
    """Everything a feature may read. Built once from the data, or from the data cut at a
    decision time for the look-ahead proof."""

    def __init__(self, sessions_by_sym, calendar, bhav, ca_dates, ca_unit_dates, industry, members_by_date,
                 dropped):
        self.sessions_by_sym = sessions_by_sym
        self.calendar = calendar
        self.bhav = bhav
        self.ca_dates = ca_dates
        self.ca_unit_dates = ca_unit_dates
        self.industry = industry
        self.members_by_date = members_by_date
        self.dropped = dropped
        self.days_by_sym = {s: sorted(v) for s, v in sessions_by_sym.items()}
        self._pc, self._vol, self._chg = {}, {}, {}

    def bars(self, sym, day):
        return self.sessions_by_sym.get(sym, {}).get(day)


def prev_session(ctx, d):
    i = bisect.bisect_left(ctx.calendar, d)
    return ctx.calendar[i - 1] if i > 0 else None


def prev_close(ctx, s, d):
    """(pc, reason): NSE's official close of the previous session on the cache's price
    basis, K_last x CLOSE / LAST, all three from the previous session (prereg §3)."""
    key = (s, d)
    if key not in ctx._pc:
        ctx._pc[key] = _prev_close(ctx, s, d)
    return ctx._pc[key]


def _prev_close(ctx, s, d):
    if d in ctx.ca_dates.get(s, ()):
        return None, "ca_exdate"
    dm = prev_session(ctx, d)
    if dm is None:
        return None, "missing:no_previous_session"
    bars = ctx.bars(s, dm)
    if not bars:
        return None, "missing:no_bars_previous_session"
    row = ctx.bhav.get((s, dm))
    if row is None:
        return None, "missing:no_bhavcopy_row"
    if not (row["close"] > 0 and row["last"] > 0 and bars[-1]["close"] > 0):
        return None, "missing:nonpositive_price"
    return bars[-1]["close"] * row["close"] / row["last"], None


def _decision(ctx, s, d, hhmm):
    bars = ctx.bars(s, d)
    if not bars:
        return None, None
    return bars, k.decision_bar_index(bars, hhmm)


def gap(ctx, s, d, hhmm):
    """F1: the day's opening gap against the previous official close, in bp."""
    pc, why = prev_close(ctx, s, d)
    if pc is None:
        return None, why
    bars = ctx.bars(s, d)
    if not bars or bars[0]["time"][11:16] != REGULAR_OPEN:
        return None, "missing:no_0915_bar"
    return (bars[0]["open"] / pc - 1) * 1e4, None


def _volume_to(ctx, s, e, cut):
    key = (s, e, cut)
    if key not in ctx._vol:
        ctx._vol[key] = sum(b["volume"] for b in ctx.sessions_by_sym[s][e] if b["time"][11:16] <= cut)
    return ctx._vol[key]


def rvol(ctx, s, d, hhmm):
    """F2: volume from the open through the decision bar, over the mean of the same on
    the stock's 20 most recent earlier regular sessions (first bar at 09:15)."""
    bars, i = _decision(ctx, s, d, hhmm)
    if bars is None or i is None:
        return None, "missing:no_decision_bar"
    cut = bars[i]["time"][11:16]
    days = ctx.days_by_sym[s]
    base = []
    for e in reversed(days[:bisect.bisect_left(days, d)]):
        if ctx.sessions_by_sym[s][e][0]["time"][11:16] != REGULAR_OPEN:
            continue
        base.append(e)
        if len(base) == RVOL_SESSIONS:
            break
    if len(base) < RVOL_SESSIONS:
        return None, "rvol_short_baseline"
    if any(base[-1] <= x <= d for x in ctx.ca_unit_dates.get(s, ())):
        return None, "ca_volume_unit"
    mean = math.fsum(_volume_to(ctx, s, e, cut) for e in base) / RVOL_SESSIONS
    if mean <= 0:
        return None, "missing:zero_baseline_volume"
    return math.fsum(b["volume"] for b in bars[:i + 1]) / mean, None


def vwap_dist(ctx, s, d, hhmm):
    """F3: the decision bar's close against the session VWAP through that bar, in bp,
    with the scanner's formula (indicators.session_vwap) on closed bars."""
    bars, i = _decision(ctx, s, d, hhmm)
    if bars is None or i is None:
        return None, "missing:no_decision_bar"
    vw = indicators.session_vwap(bars[:i + 1])
    if not vw:
        return None, "missing:zero_volume"
    return (bars[i]["close"] / vw - 1) * 1e4, None


def day_change(ctx, s, d, hhmm):
    """A stock's move from its previous official close to the close of its bar ending at
    hhmm, in bp. Reads nothing later than hhmm."""
    key = (s, d, hhmm)
    if key not in ctx._chg:
        pc, why = prev_close(ctx, s, d)
        if pc is None:
            ctx._chg[key] = (None, why)
        else:
            bars, i = _decision(ctx, s, d, hhmm)
            ctx._chg[key] = (None, "missing:no_decision_bar") if bars is None or i is None else \
                ((bars[i]["close"] / pc - 1) * 1e4, None)
    return ctx._chg[key]


def peers(ctx, s, d):
    ind = ctx.industry.get(s)
    return sorted(p for p in ctx.members_by_date.get(d, ()) if p != s and ind is not None
                  and ctx.industry.get(p) == ind and p in ctx.sessions_by_sym and d not in ctx.dropped.get(p, ()))


def sector(ctx, s, d, hhmm):
    """F4: the mean move since the previous official close of the stock's point-in-time
    NIFTY 100 industry peers, the stock itself left out."""
    if ctx.industry.get(s) is None:
        return None, "missing:no_industry"
    ps = peers(ctx, s, d)
    if not ps:
        return None, "singleton_industry"
    moves = [day_change(ctx, p, d, hhmm) for p in ps]
    vals = [v for v, _ in moves if v is not None]
    if not vals:
        return None, "ca_exdate_peers" if all(w == "ca_exdate" for _, w in moves) else "missing:no_peer_move"
    return math.fsum(vals) / len(vals), None


def gap_reversal(ctx, s, d, hhmm):
    """F5: minus the move from the previous official close to the close of the bar ending
    at hhmm (tested at 09:45 only), in bp."""
    v, why = day_change(ctx, s, d, hhmm)
    return (None, why) if v is None else (-v, None)


FEATURE_FUNCS = OrderedDict([("gap", gap), ("rvol", rvol), ("vwap_dist", vwap_dist), ("sector", sector),
                             ("gap_reversal", gap_reversal)])
assert tuple(FEATURE_FUNCS) == FEATURES


def compute_features(ctx, sym, d, hhmm):
    return OrderedDict((name, fn(ctx, sym, d, hhmm)) for name, fn in FEATURE_FUNCS.items())


def feature_applies(name, hhmm):
    return name != "gap_reversal" or hhmm == GAP_REVERSAL_TIME


def is_missing(reason):
    return reason is not None and reason.startswith("missing:")


# ---- the look-ahead proof ---------------------------------------------------------------

def truncated_ctx(ctx, d, hhmm):
    """The data as it stood when the bar closing at hhmm on d had closed: every bar of
    every stock that starts later removed, every bhavcopy dated d or later removed.
    Corporate-action dates, industries and membership are schedules known in advance."""
    start = (datetime.strptime(hhmm, "%H:%M") - timedelta(minutes=k.BAR_MINUTES)).strftime("%H:%M")
    cutoff = "%sT%s:00" % (d, start)
    sbs = {}
    for sym, days in ctx.sessions_by_sym.items():
        keep = {e: bars for e, bars in days.items() if e < d}
        part = [b for b in days.get(d, ()) if b["time"] <= cutoff]
        if part:
            keep[d] = part
        sbs[sym] = keep
    calendar = sorted({e for days in sbs.values() for e in days})
    bhav = {key: row for key, row in ctx.bhav.items() if key[1] < d}
    return Ctx(sbs, calendar, bhav, ctx.ca_dates, ctx.ca_unit_dates, ctx.industry, ctx.members_by_date, ctx.dropped)


def lookahead_proof(ctx, picks):
    """[(sym, d, hhmm)] -> list of checks; every feature must be bit-identical."""
    checks = []
    for sym, d, hhmm in picks:
        full = compute_features(ctx, sym, d, hhmm)
        cut = compute_features(truncated_ctx(ctx, d, hhmm), sym, d, hhmm)
        same = {n: (full[n][0] == cut[n][0]) and ((full[n][0] is None) == (cut[n][0] is None)) for n in FEATURES}
        checks.append({"symbol": sym, "date": d, "hhmm": hhmm, "identical": all(same.values()),
                       "differs": [n for n, ok in same.items() if not ok],
                       "defined": [n for n in FEATURES if full[n][0] is not None]})
    return checks


# ---- the hand calculation: a separate path, straight from the files ------------------

class Hand:
    """Each feature from SQLite rows, the bhavcopy CSV inside its zip and the corporate-
    action CSV, read directly. Shares only the definitions with the module."""

    def __init__(self, conn, bhav_dir, ca_file, symbolchange, industries_path, membership_rows, symbols):
        self.conn, self.bhav_dir, self.ca_file = conn, bhav_dir, ca_file
        self.symbols = sorted(symbols)
        self.rows = membership_rows
        with open(industries_path, newline="") as f:
            self.industry = {r["symbol"]: r["industry"] for r in csv.DictReader(f)}
        nxt = {}
        for line in open(symbolchange, errors="ignore"):
            p = [x.strip() for x in line.rsplit(",", 3)]
            if len(p) == 4 and p[1] and p[2] and p[1] != p[2]:
                nxt[p[1]] = p[2]
        self.nxt = nxt
        self._ca_cache, self._zip_cache = {}, {}

    def _newest(self, sym):
        seen = [sym]
        while sym in self.nxt and self.nxt[sym] not in seen:
            sym = self.nxt[sym]
            seen.append(sym)
        return sym

    def _bars(self, sym, day):
        lo = day_start_ts(day)
        rows = self.conn.execute("SELECT ts, open, high, low, close, volume FROM candles WHERE interval='5m' "
                                 "AND symbol=? AND ts>=? AND ts<? ORDER BY ts", (sym, lo, lo + 86400)).fetchall()
        return [{"hhmm": datetime.fromtimestamp(r[0], IST).strftime("%H:%M"), "open": r[1], "high": r[2],
                 "low": r[3], "close": r[4], "volume": r[5]} for r in rows]

    def _prev_day(self, d):
        marks = ",".join("?" * len(self.symbols))
        row = self.conn.execute("SELECT MAX(ts) FROM candles WHERE interval='5m' AND symbol IN (%s) AND ts<?" % marks,
                                self.symbols + [day_start_ts(d)]).fetchone()
        return datetime.fromtimestamp(row[0], IST).date().isoformat() if row[0] else None

    def _stock_days_before(self, sym, d):
        rows = self.conn.execute("SELECT DISTINCT date(ts, 'unixepoch', '+330 minutes') FROM candles "
                                 "WHERE interval='5m' AND symbol=? AND ts<? ORDER BY 1 DESC",
                                 (sym, day_start_ts(d))).fetchall()
        return [r[0] for r in rows]

    def _bhav_row(self, sym, day):
        if day not in self._zip_cache:
            path = os.path.join(self.bhav_dir, day.replace("-", "") + ".zip")
            rows = []
            if os.path.exists(path):
                with zipfile.ZipFile(path) as z, z.open(z.namelist()[0]) as fh:
                    for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="ignore")):
                        rows.append({key.strip(): (v or "").strip() for key, v in r.items() if key})
            self._zip_cache[day] = rows
        for r in self._zip_cache[day]:
            if r.get("SctySrs") == "EQ" and self._newest(r.get("TckrSymb", "")) == sym:
                return {"close": float(r["ClsPric"]), "last": float(r["LastPric"])}
        return None

    def _ca(self, sym):
        if sym not in self._ca_cache:
            self._ca_cache[sym] = self._read_ca(sym)
        return self._ca_cache[sym]

    def _read_ca(self, sym):
        dates, unit = set(), set()
        with open(self.ca_file, encoding="utf-8-sig", errors="ignore") as fh:
            for r in csv.DictReader(fh):
                r = {key.strip().strip('"'): (v or "").strip() for key, v in r.items() if key}
                if self._newest(r.get("SYMBOL", "")) != sym:
                    continue
                try:
                    ex = datetime.strptime(r["EX-DATE"], "%d-%b-%Y").date().isoformat()
                except (KeyError, ValueError):
                    continue
                dates.add(ex)
                if is_unit_change(r.get("PURPOSE", "")):
                    unit.add(ex)
        return dates, unit

    @staticmethod
    def _start(hhmm):
        return (datetime.strptime(hhmm, "%H:%M") - timedelta(minutes=5)).strftime("%H:%M")

    def pc(self, sym, d):
        if d in self._ca(sym)[0]:
            return None
        dm = self._prev_day(d)
        bars = self._bars(sym, dm) if dm else []
        row = self._bhav_row(sym, dm) if dm else None
        if not bars or not row or row["last"] <= 0 or row["close"] <= 0:
            return None
        return bars[-1]["close"] * row["close"] / row["last"]

    def close_at(self, sym, d, hhmm):
        start = self._start(hhmm)
        for b in self._bars(sym, d):
            if b["hhmm"] == start:
                return b["close"]
        return None

    def features(self, sym, d, hhmm):
        start = self._start(hhmm)
        out = {}
        bars = self._bars(sym, d)
        today = [b for b in bars if b["hhmm"] <= start]
        pc = self.pc(sym, d)
        c0 = self.close_at(sym, d, hhmm)
        out["gap"] = None if pc is None or not bars or bars[0]["hhmm"] != "09:15" else (bars[0]["open"] / pc - 1) * 1e4
        base, first = [], None
        for e in self._stock_days_before(sym, d):
            eb = self._bars(sym, e)
            if eb and eb[0]["hhmm"] == "09:15":
                base.append(sum(b["volume"] for b in eb if b["hhmm"] <= start))
                first = e
            if len(base) == 20:
                break
        unit = self._ca(sym)[1]
        if len(base) < 20 or any(first <= x <= d for x in unit) or sum(base) <= 0:
            out["rvol"] = None
        else:
            out["rvol"] = sum(b["volume"] for b in today) / (sum(base) / 20.0)
        vol = sum(b["volume"] for b in today)
        pv = sum((b["high"] + b["low"] + b["close"]) / 3 * b["volume"] for b in today)
        out["vwap_dist"] = None if vol <= 0 else (c0 / (pv / vol) - 1) * 1e4
        members = k.membership_asof(self.rows, d)
        ind = self.industry.get(sym)
        moves = []
        for p in sorted(members):
            if p == sym or p not in self.symbols or self.industry.get(p) != ind:
                continue
            ppc, pc0 = self.pc(p, d), self.close_at(p, d, hhmm)
            if ppc is not None and pc0 is not None:
                moves.append((pc0 / ppc - 1) * 1e4)
        out["sector"] = sum(moves) / len(moves) if moves else None
        out["gap_reversal"] = None if pc is None or c0 is None else -(c0 / pc - 1) * 1e4
        return out


def hand_check(ctx, hand, picks):
    rows = []
    for sym, d, hhmm in picks:
        mod = compute_features(ctx, sym, d, hhmm)
        byhand = hand.features(sym, d, hhmm)
        diffs = {}
        for n in FEATURES:
            a, b = mod[n][0], byhand[n]
            if (a is None) != (b is None):
                diffs[n] = "defined in one path only (module %r, hand %r)" % (a, b)
            elif a is not None and abs(a - b) > HAND_TOL_BP:
                diffs[n] = abs(a - b)
        rows.append({"symbol": sym, "date": d, "hhmm": hhmm, "module": {n: mod[n][0] for n in FEATURES},
                     "hand": byhand, "max_abs_diff_bp": max([abs(mod[n][0] - byhand[n]) for n in FEATURES
                                                             if mod[n][0] is not None and byhand[n] is not None] or [0]),
                     "mismatches": diffs})
    return rows


# ---- alignment of Kite's last bar with NSE's last price (stage 0 check 4) -------------

def alignment(ctx, stock_days):
    """For stock-days (s, e) whose last bar enters a previous close: r(e) = K_last / LAST,
    and its move from the stock's previous session, on pairs with no ex-date on e."""
    moves, open_gaps, skipped = [], [], Counter()
    for s, e in sorted(stock_days):
        pe = prev_session(ctx, e)
        be, bp = ctx.bars(s, e), ctx.bars(s, pe) if pe else None
        re_, rp = ctx.bhav.get((s, e)), ctx.bhav.get((s, pe)) if pe else None
        if not be or not bp or not re_ or not rp or re_["last"] <= 0 or rp["last"] <= 0:
            skipped["missing"] += 1
            continue
        r_e, r_p = be[-1]["close"] / re_["last"], bp[-1]["close"] / rp["last"]
        if be[0]["time"][11:16] == REGULAR_OPEN and re_["open"] > 0:
            open_gaps.append(abs((be[0]["open"] / re_["open"]) / r_e - 1) * 1e4)
        if e in ctx.ca_dates.get(s, ()):
            skipped["ex_date"] += 1
            continue
        moves.append((abs(r_e / r_p - 1) * 1e4, s, pe, e))
    vals = sorted(m[0] for m in moves)
    share = sum(v <= ALIGN_TOL_BP for v in vals) / len(vals) if vals else 0.0
    og = sorted(open_gaps)
    return {"pairs": len(vals), "share_within_tol": share, "tol_bp": ALIGN_TOL_BP, "min_share": ALIGN_MIN_SHARE,
            "median_bp": _q(vals, 0.5), "p95_bp": _q(vals, 0.95), "max_bp": vals[-1] if vals else None,
            "worst": [{"symbol": s, "from": p, "to": e, "move_bp": m} for m, s, p, e in sorted(moves, reverse=True)[:15]],
            "skipped": dict(skipped),
            "open_vs_last_information": {"n": len(og), "median_bp": _q(og, 0.5), "p95_bp": _q(og, 0.95),
                                         "share_within_tol": (sum(v <= ALIGN_TOL_BP for v in og) / len(og)) if og else None},
            "passes": share >= ALIGN_MIN_SHARE}


def _q(vals, p):
    if not vals:
        return None
    return vals[min(len(vals) - 1, int(p * (len(vals) - 1) + 0.5))]


# ---- statistics: the harness's, per test ---------------------------------------------------

def rows_for_test(samples, feats, targets, m60s, test):
    """{date: [(feature, target, m60)]} for one of the 13 tests."""
    feat, horizon = TESTS[test]
    by_d = defaultdict(list)
    for j, s in enumerate(samples):
        if not feature_applies(feat, s[2]):
            continue
        fv, tv, mv = feats[j][feat][0], targets[j][horizon], m60s[j]
        if fv is None or tv is None or mv is None:
            continue
        by_d[s[1]].append((fv, tv, mv))
    return by_d


def summarise_rows(by_d):
    """kronos_feature_ic.evaluate_rows's aggregation for one feature and horizon."""
    per_session = {d: k.session_stats(r) for d, r in by_d.items() if len(r) >= k.MIN_STOCKS}
    return k.summarise(per_session), per_session


def evaluate(samples, feats, targets, m60s):
    summaries, per_session = OrderedDict(), OrderedDict()
    for test in TESTS:
        summaries[test], per_session[test] = summarise_rows(rows_for_test(samples, feats, targets, m60s, test))
    return summaries, per_session, k.gate(summaries)


def positive_control(samples, flat_by_sym, sessions_by_sym):
    """Stage 0 check 8, on a segment before the sample, through the harness's gate: the
    target plus 5 bp of seeded noise (amendment 1: the bare target's partial IC is 1 in
    every session, so its t does not exist), its negation, and a seeded random number."""
    rng = random.Random(SEED)
    by = {"%s_%s" % (kind, h): defaultdict(list) for kind in ("pos", "neg", "null") for h in k.HORIZONS}
    for sym, d, hhmm, idx, i in samples:
        bars = sessions_by_sym[sym][d]
        m = k.m60_bp(flat_by_sym[sym], idx)
        for h, kbars in k.HORIZONS.items():
            y = k.target_bp(bars, i, kbars)
            f = y + rng.gauss(0.0, CONTROL_NOISE_BP)
            by["pos_" + h][d].append((f, y, m))
            by["neg_" + h][d].append((-f, y, m))
            by["null_" + h][d].append((rng.random(), y, m))
    summaries = OrderedDict((n, summarise_rows(r)[0]) for n, r in by.items())
    verdicts = k.gate(summaries)
    pattern_ok = (all(verdicts["pos_" + h]["passes"] for h in k.HORIZONS)
                  and all(not verdicts["neg_" + h]["passes"] and summaries["neg_" + h]["spread"]["mean"] < 0
                          for h in k.HORIZONS)
                  and all(not verdicts["null_" + h]["passes"] for h in k.HORIZONS))
    brief = {n: {"sessions": s["sessions"], "spread_mean_bp": s["spread"]["mean"], "spread_t": s["spread"]["t"],
                 "spread_over_bar": (s["spread"]["mean"] / k.TWO_LEG_BP) if s["spread"]["mean"] is not None else None,
                 "halves_mean_bp": [hh["mean"] for hh in s["spread"]["halves"]],
                 "pic_mean": s["pic"]["mean"], "pic_t": s["pic"]["t"], "passes": verdicts[n]["passes"]}
             for n, s in summaries.items()}
    return {"stock_times": len(samples), "noise_bp": CONTROL_NOISE_BP, "tests": brief, "passes": pattern_ok}


def distribution(vals):
    v = sorted(vals)
    if not v:
        return {"n": 0}
    mean = math.fsum(v) / len(v)
    sd = math.sqrt(math.fsum((x - mean) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else None
    return {"n": len(v), "mean": mean, "sd": sd, "min": v[0], "max": v[-1],
            "quantiles": {str(p): _q(v, p) for p in (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)}}


# ---- assembling the data --------------------------------------------------------------------

def assemble(conn):
    """Everything both stage 0 and the pass need, from the read-only sources."""
    info = {}
    rows = k.load_membership_rows()
    members = sorted({r["symbol"] for r in rows})
    candles, latest = load_candles(conn, members)
    info["latest_bar_read"] = latest
    info["symbols_loaded"] = len(candles)
    flat_by_sym = OrderedDict((s, sorted(c, key=lambda x: x["time"])) for s, c in candles.items())
    sessions_by_sym = OrderedDict((s, k.by_session(c)) for s, c in flat_by_sym.items())
    calendar = splits.sessions_in(flat_by_sym)
    sessions = k.selection_sessions(calendar)
    control = [c for c in calendar if CONTROL_START <= c <= CONTROL_END]
    members_by_date = {d: k.membership_asof(rows, d) for d in sessions + control}
    fetched = fetched_rows(conn)
    dropped = adjustment_drops(fetched, list(flat_by_sym), sessions)
    dropped_control = adjustment_drops(fetched, list(flat_by_sym), control)
    nxt = nse_prices.symbol_chains(SYMBOLCHANGE)
    files = bhav_files(BHAV_DIR, BHAV_START)
    bhav, mismatched = load_bhav(files, list(flat_by_sym), nxt)
    info["bhav_files"] = {"count": len(files), "first": files[0][0] if files else None,
                          "last": files[-1][0] if files else None, "date_mismatches": mismatched}
    ca_dates, ca_unit = load_corporate_actions(CA_FILE, nxt)
    industry = load_industries()
    ctx = Ctx(sessions_by_sym, calendar, bhav, ca_dates, ca_unit, industry, members_by_date, dropped)
    samples = k.build_samples(flat_by_sym, sessions_by_sym, sessions, members_by_date, dropped)
    return {"info": info, "rows": rows, "members": members, "flat_by_sym": flat_by_sym,
            "sessions_by_sym": sessions_by_sym, "calendar": calendar, "sessions": sessions, "control": control,
            "members_by_date": members_by_date, "dropped": dropped, "dropped_control": dropped_control,
            "fetched": fetched, "ctx": ctx, "samples": samples}


def all_features(ctx, samples):
    return [compute_features(ctx, s[0], s[1], s[2]) for s in samples]


def coverage(samples, feats, sessions):
    out, halt_reasons = OrderedDict(), []
    for n in FEATURES:
        idx = [j for j, s in enumerate(samples) if feature_applies(n, s[2])]
        reasons = Counter(feats[j][n][1] for j in idx if feats[j][n][0] is None)
        by_stock = Counter(samples[j][0] for j in idx if feats[j][n][0] is None)
        missing = sum(c for r, c in reasons.items() if is_missing(r))
        out[n] = {"stock_times": len(idx), "defined": len(idx) - sum(reasons.values()),
                  "undefined_by_reason": dict(reasons), "undefined_by_stock": dict(by_stock.most_common()),
                  "missing_share": missing / len(idx) if idx else None,
                  "unregistered_reasons": sorted(r for r in reasons if not is_missing(r)
                                                 and r not in PREREGISTERED_REASONS)}
        if not idx or missing / len(idx) > MISSING_MAX_SHARE:
            halt_reasons.append("%s: missing data removes %s of %d stock-times" % (n, missing, len(idx)))
        if out[n]["unregistered_reasons"]:
            halt_reasons.append("%s: undefined for a reason the prereg does not name: %s"
                                % (n, out[n]["unregistered_reasons"]))
    per_test = OrderedDict()
    for test, (feat, _h) in TESTS.items():
        counts = Counter(s[1] for j, s in enumerate(samples)
                         if feature_applies(feat, s[2]) and feats[j][feat][0] is not None)
        usable = sorted(d for d, c in counts.items() if c >= k.MIN_STOCKS)
        first, second = splits.halves(usable)
        per_test[test] = {"sessions": len(usable), "halves": [len(first), len(second)]}
        if min(len(first), len(second)) < k.MIN_SESSIONS_PER_HALF:
            halt_reasons.append("%s: a half has fewer than %d sessions" % (test, k.MIN_SESSIONS_PER_HALF))
    return {"features": out, "tests": per_test}, halt_reasons


# ---- stage 0 ----------------------------------------------------------------------------

def _git(*args):
    try:
        return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True).stdout.strip()
    except Exception as exc:  # recorded, not fatal
        return "unavailable: %s" % exc


def environment():
    return {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
            "niceness": os.nice(0) if hasattr(os, "nice") else None, "head": _git("rev-parse", "HEAD"),
            "module_dirty": bool(_git("status", "--porcelain", "backend/research/scanner_features_l49.py")),
            "candle_db": CANDLE_DB, "data_dir": DATA}


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=str)
        f.write("\n")


def _halt(rec, step, why):
    rec["halted_at"] = {"step": step, "why": why}
    rec["finished"] = datetime.now(IST).isoformat()
    _write(STAGE0_OUT, {"stage0": rec, "status": "HALTED"})
    print("HALT at stage 0 check %s: %s" % (step, why), flush=True)
    sys.exit(2)


def stage0():
    t0 = time.time()
    rec = OrderedDict([("look", "L49"), ("prereg", PREREG), ("prereg_commit", PREREG_COMMIT),
                       ("started", datetime.now(IST).isoformat()), ("argv", sys.argv[1:]),
                       ("environment", environment())])
    # 1. feature count
    rec["1_features"] = {"features": list(FEATURES), "tests": {t: list(v) for t, v in TESTS.items()},
                         "n_tests": len(TESTS), "passes": len(FEATURES) == 5 and len(TESTS) == N_TESTS}
    if not rec["1_features"]["passes"]:
        _halt(rec, 1, "the feature or test count is not the prereg's")

    conn = connect_ro(CANDLE_DB)
    runs = fetch_runs(conn)
    data = assemble(conn)
    info = data["info"]
    # 2. data and the 2026 guard
    rec["2_data"] = {"fetch_runs": runs, "latest_bar_read": info["latest_bar_read"],
                     "symbols_loaded": info["symbols_loaded"], "bhav_files": info["bhav_files"],
                     "corporate_actions_file": os.path.basename(CA_FILE), "industries_file": INDUSTRIES,
                     "passes": (len(runs) == 1 and info["latest_bar_read"][:10] < CUTOFF
                                and (info["bhav_files"]["last"] or "") < CUTOFF
                                and os.path.basename(CA_FILE) == "ca_2025.csv")}
    if len(runs) != 1:
        _halt(rec, 2, "the cache holds %d fetch runs; the prereg halts on more than one" % len(runs))
    if not rec["2_data"]["passes"]:
        _halt(rec, 2, "a 2026 source was read")
    print("stage 0: data loaded, %d symbols, latest bar %s, %.0f s" % (info["symbols_loaded"],
                                                                         info["latest_bar_read"], time.time() - t0), flush=True)

    # 3. L40's sample reproduced
    samples, sessions = data["samples"], data["sessions"]
    with_data = sorted({s[1] for s in samples})
    first, second = splits.halves(sessions)
    l40 = {}
    if os.path.exists(L40_RECORD):
        with open(L40_RECORD) as f:
            l40s = json.load(f)["stage0"]
        l40 = {"coverage": l40s.get("coverage"), "dropped": l40s.get("adjustment", {}).get("dropped_stock_sessions"),
               "selection": l40s.get("selection")}
    got = {"sessions": len(sessions), "sessions_with_data": len(with_data), "stock_times": len(samples),
           "halves": [len(first), len(second)]}
    ok3 = (got == L40_EXPECTED and data["dropped"] == {} and l40.get("dropped") == {}
           and (l40.get("coverage") or {}).get("stock_times") == len(samples)
           and l40.get("selection") == splits.describe_split("selection", sessions))
    rec["3_l40_sample"] = {"got": got, "expected": L40_EXPECTED, "selection": splits.describe_split("selection", sessions),
                           "l40_record": l40, "dropped": data["dropped"], "passes": ok3}
    if not ok3:
        _halt(rec, 3, "L40's sample is not reproduced: %s" % got)

    ctx = data["ctx"]
    # 4. Kite's last bar and NSE's last price are the same trade
    used = set()
    for d in sessions:
        dm = prev_session(ctx, d)
        for s in data["members_by_date"][d]:
            if s in ctx.sessions_by_sym and dm:
                used.add((s, dm))
    rec["4_alignment"] = alignment(ctx, used)
    if not rec["4_alignment"]["passes"]:
        _halt(rec, 4, "only %.2f%% of consecutive stock-days keep K_last / LAST within %.0f bp"
              % (100 * rec["4_alignment"]["share_within_tol"], ALIGN_TOL_BP))
    print("stage 0: alignment %.4f within %.0f bp over %d pairs" % (rec["4_alignment"]["share_within_tol"],
                                                                    ALIGN_TOL_BP, rec["4_alignment"]["pairs"]), flush=True)

    # 5. coverage (features only; no target is read)
    feats = all_features(ctx, samples)
    cov, why5 = coverage(samples, feats, sessions)
    rec["5_coverage"] = dict(cov, passes=not why5)
    if why5:
        _halt(rec, 5, "; ".join(why5))
    print("stage 0: features computed for %d stock-times, %.0f s" % (len(samples), time.time() - t0), flush=True)

    # 6. hand calculation
    rng = random.Random(SEED)
    at_0945 = [s for s in samples if s[2] == GAP_REVERSAL_TIME]
    picks = [(s[0], s[1], s[2]) for s in rng.sample(samples, HAND_N) + rng.sample(at_0945, HAND_N)]
    hand = Hand(conn, BHAV_DIR, CA_FILE, SYMBOLCHANGE, INDUSTRIES, data["rows"], list(data["flat_by_sym"]))
    hc = hand_check(ctx, hand, picks)
    defined = Counter(n for r in hc for n in FEATURES if r["module"][n] is not None)
    ok6 = all(not r["mismatches"] for r in hc)
    rec["6_hand_calculation"] = {"stock_times": hc, "defined_per_feature": dict(defined), "tol_bp": HAND_TOL_BP,
                                 "passes": ok6}
    if not ok6:
        _halt(rec, 6, "a feature differs from its hand calculation")

    # 7. look-ahead proof
    rng = random.Random(SEED + 7)
    picks = [(s[0], s[1], s[2]) for s in rng.sample(samples, LOOKAHEAD_N)]
    la = lookahead_proof(ctx, picks)
    ok7 = all(c["identical"] for c in la)
    rec["7_lookahead"] = {"stock_times": len(la), "identical": sum(c["identical"] for c in la),
                          "defined_per_feature": dict(Counter(n for c in la for n in c["defined"])),
                          "at_0945": sum(c["hhmm"] == GAP_REVERSAL_TIME for c in la),
                          "failures": [c for c in la if not c["identical"]], "passes": ok7}
    if not ok7:
        _halt(rec, 7, "a feature changed when later bars or bhavcopies were present")
    print("stage 0: look-ahead proof %d of %d identical, %.0f s" % (rec["7_lookahead"]["identical"], len(la),
                                                                    time.time() - t0), flush=True)

    # 8. positive control before the sample (targets read on that segment only)
    ctl = k.build_samples(data["flat_by_sym"], data["sessions_by_sym"], data["control"], data["members_by_date"],
                          data["dropped_control"])
    pc8 = positive_control(ctl, data["flat_by_sym"], data["sessions_by_sym"])
    rec["8_positive_control"] = dict(pc8, segment=[CONTROL_START, CONTROL_END],
                                     sessions_listed=len(data["control"]), dropped=data["dropped_control"])
    if not pc8["passes"]:
        _halt(rec, 8, "the positive, negative and null controls did not give the expected pattern")

    # 9. information: feature distributions on the selection sample (no target read)
    rec["9_distributions"] = OrderedDict(
        (n, distribution([feats[j][n][0] for j, s in enumerate(samples)
                          if feature_applies(n, s[2]) and feats[j][n][0] is not None])) for n in FEATURES)
    rec["seconds"] = round(time.time() - t0)
    rec["finished"] = datetime.now(IST).isoformat()
    _write(STAGE0_OUT, {"stage0": rec, "status": "STAGE0_DONE"})
    print("stage 0 complete: all nine checks written to %s" % STAGE0_OUT, flush=True)
    return rec


# ---- the one measurement pass ----------------------------------------------------------

def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def refusals(rerun_reason=None):
    """Why the measurement pass may not start, or []."""
    why = []
    if not os.path.exists(STAGE0_OUT):
        why.append("no stage 0 record at %s" % STAGE0_OUT)
    else:
        with open(STAGE0_OUT) as f:
            if json.load(f).get("status") != "STAGE0_DONE":
                why.append("stage 0 did not finish with every check passing")
        for rel in ("docs/research/data/l49_stage0.json", "backend/research/scanner_features_l49.py"):
            if subprocess.run(["git", "-C", REPO, "ls-files", "--error-unmatch", rel], capture_output=True).returncode:
                why.append("%s is not committed" % rel)
            elif _git("status", "--porcelain", rel):
                why.append("%s differs from its commit" % rel)
    if os.path.exists(RESULT_OUT) and not rerun_reason:
        why.append("%s exists: one run only (prereg §10)" % RESULT_OUT)
    return why


def measure(review_note, rerun_reason=None):
    why = refusals(rerun_reason)
    if why:
        raise SystemExit("refused: " + "; ".join(why))
    with open(STAGE0_OUT) as f:
        st0 = json.load(f)["stage0"]
    started = {"look": "L49", "status": "STARTED", "started": datetime.now(IST).isoformat(),
               "review_note": review_note, "rerun_reason": rerun_reason, "stage0_sha256": _sha256(STAGE0_OUT),
               "environment": environment()}
    _write(RESULT_OUT, started)                      # before any target is read
    conn = connect_ro(CANDLE_DB)
    data = assemble(conn)
    samples, ctx = data["samples"], data["ctx"]
    if len(samples) != L40_EXPECTED["stock_times"]:
        raise SystemExit("the sample is %d stock-times, not L40's %d" % (len(samples), L40_EXPECTED["stock_times"]))
    feats = all_features(ctx, samples)
    cov, _ = coverage(samples, feats, data["sessions"])
    if cov != {key: st0["5_coverage"][key] for key in ("features", "tests")}:
        raise SystemExit("the features' coverage differs from stage 0's record")
    flat, sbs = data["flat_by_sym"], data["sessions_by_sym"]
    targets = [OrderedDict((h, k.target_bp(sbs[s[0]][s[1]], s[4], kb)) for h, kb in k.HORIZONS.items())
               for s in samples]
    m60s = [k.m60_bp(flat[s[0]], s[3]) for s in samples]
    summaries, per_session, verdicts = evaluate(samples, feats, targets, m60s)
    ps = [summaries[t]["spread"]["p"] if summaries[t]["spread"]["p"] is not None else 1.0 for t in TESTS]
    survivors = sorted(list(TESTS)[i] for i in k.benjamini_hochberg(ps, q=k.BH_Q))
    result = dict(started, status="DONE", finished=datetime.now(IST).isoformat(),
                  result={"summaries": summaries, "gate": verdicts, "bh_survivors": survivors,
                          "per_session": per_session},
                  constants={"two_leg_bp": k.TWO_LEG_BP, "round_trip_bp": k.ROUND_TRIP_BP, "bh_q": k.BH_Q,
                             "n_tests": N_TESTS, "min_stocks": k.MIN_STOCKS, "min_sessions_gate": k.MIN_SESSIONS_GATE})
    _write(RESULT_OUT, result)
    for t in TESTS:
        s = summaries[t]
        sp, ic, pic = s["spread"], s["ic"], s["pic"]
        print("%-20s sessions %d | IC %.4f (t %.2f) | partial IC %.4f (t %.2f) | spread %.2f bp (t %.2f) | passes: %s"
              % (t, s["sessions"], ic["mean"] or 0, ic["t"] or 0, pic["mean"] or 0, pic["t"] or 0,
                 sp["mean"] or 0, sp["t"] or 0, verdicts[t]["passes"]), flush=True)
    print("BH survivors at q=%.2f across %d: %s" % (k.BH_Q, N_TESTS, survivors or "none"), flush=True)
    print("wrote", RESULT_OUT, flush=True)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stage0", action="store_true", help="the nine checks; reads no feature against any return")
    mode.add_argument("--measure", action="store_true", help="the ONE measurement pass, after the review of stage 0")
    ap.add_argument("--review-note", default=None, help="who approved stage 0, and when (required with --measure)")
    ap.add_argument("--owner-approved-rerun", default=None, help="a recorded reason; only for prereg §10's cases")
    args = ap.parse_args(argv)
    if args.stage0:
        stage0()
    else:
        if not args.review_note:
            raise SystemExit("--measure needs --review-note: the pass runs only after the independent review")
        measure(args.review_note, args.owner_approved_rerun)


if __name__ == "__main__":
    main()
