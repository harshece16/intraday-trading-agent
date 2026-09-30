"""Research look L51 — do lagged intraday returns of factor portfolios predict the
NIFTY's next 30 or 60 minutes past a futures round trip?

Pre-registered: docs/research/prereg-index-timing.md (commit 769c21c), before this
file was written; its amendments are dated there. After Aleti, Bollerslev and
Siggaard (Management Science 71(9), 2025). Background: predictive-tools sweep, part B,
candidate 2.

What it does, as the prereg fixes it:
  23 factor series on five-minute bars (12 characteristic sorts of the NIFTY 100,
  9 sectors, the NIFTY 50 itself, equal-weight minus the index) -> 92 lagged
  predictors -> a numpy Ridge per horizon (30 and 60 minutes), its penalty chosen
  once by time-series cross-validation in the first training window, refitted
  monthly on an expanding window with a 5-session purge -> trade NIFTY futures
  when the forecast exceeds the round trip -> gate on the L40 selection sample.

Two modes:
  --stage0   the seven halts of prereg §9. Reads no target dated on or after
             2025-09-01 and pairs no forecast with any realised return except in
             the planted controls, which use 2025-03..2025-08 only.
  --score    the one scoring pass (prereg §10). Refuses without the main session's
             go-ahead (--go), a committed stage 0 with no halt, and an absent
             result file.

Measurement only: no strategy, no trial (the count stays at 202). Nothing in the
live path imports this. Never imports app, reads no key, calls no broker. The two
databases are opened read-only.

Run from backend/ with the main checkout's data (a worktree has none):
    SAHAB_RESEARCH_DATA=/path/to/main/backend/data \\
        nice -n 15 .venv/bin/python -m research.index_timing_l51 --stage0
"""
import argparse
import csv
import hashlib
import json
import math
import os
import platform
import sqlite3
import statistics as st
import subprocess
import sys
import time
from collections import OrderedDict, defaultdict
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPO = os.path.dirname(BACKEND)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import costs  # noqa: E402
import evaluation  # noqa: E402
from research import kronos_feature_ic as k  # noqa: E402
from research import splits  # noqa: E402

# ---- the pre-registration's constants, named once ------------------------------------------

PREREG = "docs/research/prereg-index-timing.md"
PREREG_COMMIT = "769c21c"
HELD_OUT_START = splits.HELD_OUT_START          # "2026-01-02": nothing on or after it is read
SCORING_START = k.SELECTION_START               # "2025-09-01"
FIRST_MONTH, LAST_MONTH = "2025-03", "2025-12"
PSEUDO_OOS_END = "2025-08-31"
FIRST_SESSION = "2024-09-20"

BARS = 75                                       # 09:15 .. 15:25 bar starts
BAR_MINUTES = 5
FIRST_DECISION_BAR = 5                          # closes 09:45
LAST_EXIT_BAR = 71                              # closes 15:15
HORIZONS = OrderedDict([("h30", 6), ("h60", 12)])
GRID = {"h30": list(range(5, 66, 6)), "h60": list(range(5, 54, 12))}
INDEX_SYMBOL = "NIFTY 50"
INDEX_MINUTES = 375
MIN_FULL_MEMBERS = 60                           # members with all 75 bars, for a session to be used
MIN_RANKED = 30                                 # members with a valid characteristic, per factor-session

CHARS = ["LIQ", "TURN", "ILLIQ", "MOM", "REV21", "REV5", "REV1", "VOL", "IVOL", "BETA", "HIGH52", "RANGE"]
SECTORS = OrderedDict([
    ("FIN", "Financial Services"), ("CAPG", "Capital Goods"), ("AUTO", "Automobile and Auto Components"),
    ("HLTH", "Healthcare"), ("FMCG", "Fast Moving Consumer Goods"), ("METAL", "Metals & Mining"),
    ("POWER", "Power"), ("OILGAS", "Oil Gas & Consumable Fuels"), ("IT", "Information Technology"),
])
FACTORS = CHARS + list(SECTORS) + ["MKT", "EWX"]
LAGS = ["last5", "last30", "sofar", "prev"]
PREDICTORS = ["%s_%s" % (f, lag) for f in FACTORS for lag in LAGS]
VALID_SHARE = 0.8
MIN_MARKET_MEMBERS = 50

ALPHAS = [10 ** (e / 2) for e in range(-6, 9)]  # 1e-3 .. 1e4, 15 values
CV_BLOCKS = 5
PURGE = 5
WINSOR = (0.005, 0.995)
CLIP = 5.0

FUTURES_COSTS = {  # zerodha.com/charges, equity futures, read 2026-09-30
    "brokerage_per_order": 20.0, "brokerage_pct": 0.03, "stt_pct_sell": 0.05, "exchange_txn_pct": 0.00183,
    "sebi_charges_pct": 0.0001, "ipft_pct": 0.0000001, "stamp_duty_pct_buy": 0.002, "gst_pct": 18.0,
    "slippage_pct": 0.005,
}
FUTURES_COSTS_2025 = dict(FUTURES_COSTS, stt_pct_sell=0.02, exchange_txn_pct=0.00173)
NOTIONAL = 65 * 25000.0
MIN_TRADES, MIN_TRADE_SESSIONS, T_BAR, DSR_BAR, N_CONFIGS = 100, 40, 2.0, 0.95, 2

CONTROL_SEED = 51
PLANTED_NOISE_MULT = math.sqrt(3.0)             # amendment 1: correlation 0.5 (was 3.18, 0.3)
LOOKAHEAD_CHECKS = 240
HAND_CHECKS = 5

DATA = os.environ.get("SAHAB_RESEARCH_DATA") or os.path.join(BACKEND, "data")
KITE_DB = os.path.join(DATA, "kite_history.db")
INDEX_DB = os.path.join(DATA, "overnight_1m.db")
SECTOR_CSV = os.path.join(BACKEND, "data", "nifty100.csv")
OUT_DIR = os.path.join(REPO, "docs", "research", "data")
STAGE0_OUT = os.path.join(OUT_DIR, "l51_stage0.json")
RESULT_OUT = os.path.join(OUT_DIR, "l51_result.json")

IST = timezone(timedelta(hours=5, minutes=30))
EPOCH_ORDINAL = date(1970, 1, 1).toordinal()


def round_trip_bp(cfg=FUTURES_COSTS, notional=NOTIONAL):
    """The futures round trip in bp, from costs.py's own formula."""
    return costs.round_trip_pct(notional, cfg) * 100


COST_BP = round_trip_bp()
COST_BP_2025 = round_trip_bp(FUTURES_COSTS_2025)


def _np():
    import numpy as np
    return np


# ---- small pure helpers ----------------------------------------------------------------------

def bar_hhmm(j):
    """Start time of bar j (0 -> 09:15)."""
    m = 9 * 60 + 15 + BAR_MINUTES * j
    return "%02d:%02d" % (m // 60, m % 60)


def bar_close_hhmm(j):
    return bar_hhmm(j + 1)


def train_bars(kbars):
    """Decision bars whose close is 09:45 or later and whose exit bar closes by 15:15."""
    return list(range(FIRST_DECISION_BAR, LAST_EXIT_BAR - kbars + 1))


def need(window):
    """Valid observations a window of `window` rows needs: at least 80%."""
    return int(math.ceil(VALID_SHARE * window - 1e-9))


def derangement(n, rng):
    """A permutation of range(n) with no fixed point."""
    np = _np()
    while True:
        p = rng.permutation(n)
        if n < 2 or not (p == np.arange(n)).any():
            return p


# ---- data: the two databases, read-only ------------------------------------------------------

def _ro(path):
    if not os.path.exists(path):
        raise FileNotFoundError("%s not found; set SAHAB_RESEARCH_DATA to the main checkout's backend/data" % path)
    return sqlite3.connect("file:%s?mode=ro" % path, uri=True)


def _cut_epoch(day=HELD_OUT_START):
    return int(datetime.fromisoformat(day).replace(tzinfo=IST).timestamp())


def load_stock_bars(path=KITE_DB, start=FIRST_SESSION, end=HELD_OUT_START):
    """(dates, symbols, O, C, info): open and close of every five-minute bar, arrays of
    shape (sessions, 75, symbols), NaN where the cache has no bar. Rows on or after
    `end` are excluded in the SQL and the latest timestamp read is asserted."""
    np = _np()
    lo, hi = _cut_epoch(start), _cut_epoch(end)
    con = _ro(path)
    rows = con.execute("SELECT symbol, ts, open, close FROM candles WHERE interval='5m' AND ts >= ? AND ts < ?",
                       (lo, hi)).fetchall()
    con.close()
    if not rows:
        raise RuntimeError("no stock bars read")
    syms = sorted({r[0] for r in rows})
    col = {s: n for n, s in enumerate(syms)}
    ts = np.array([r[1] for r in rows], dtype=np.int64)
    max_ts = int(ts.max())
    assert max_ts < hi, "a stock bar on or after %s was read" % end
    local = ts + 19800
    day = local // 86400
    minute = (local % 86400) // 60 - (9 * 60 + 15)
    ok = (minute >= 0) & (minute % BAR_MINUTES == 0) & (minute // BAR_MINUTES < BARS)
    days = sorted(set(day.tolist()))
    drow = {d: i for i, d in enumerate(days)}
    dates = [date.fromordinal(EPOCH_ORDINAL + d).isoformat() for d in days]
    O = np.full((len(days), BARS, len(syms)), np.nan)
    C = np.full((len(days), BARS, len(syms)), np.nan)
    di = np.array([drow[d] for d in day.tolist()])
    ji = minute // BAR_MINUTES
    ci = np.array([col[r[0]] for r in rows])
    op = np.array([r[2] for r in rows], dtype=float)
    cl = np.array([r[3] for r in rows], dtype=float)
    O[di[ok], ji[ok], ci[ok]] = op[ok]
    C[di[ok], ji[ok], ci[ok]] = cl[ok]
    info = {"rows": len(rows), "off_grid_rows": int((~ok).sum()), "symbols": len(syms),
            "first": dates[0], "last": dates[-1],
            "max_ts_ist": datetime.fromtimestamp(max_ts, IST).isoformat()}
    return dates, syms, O, C, info


def aggregate_index_minutes(minute_rows):
    """minute_rows: [(ts 'YYYY-MM-DD HH:MM', open, close)]. Returns {date: (opens[75],
    closes[75], minutes)}: a bar starting at hh:mm takes the open of the hh:mm minute
    and the close of the hh:mm+4 minute (start-time labelling, like the stock cache);
    None where that minute is missing."""
    out = {}
    for ts, op, cl in minute_rows:
        d, hm = ts[:10], ts[11:16]
        m = int(hm[:2]) * 60 + int(hm[3:5]) - (9 * 60 + 15)
        if m < 0 or m >= BARS * BAR_MINUTES:
            continue
        rec = out.setdefault(d, [[None] * BARS, [None] * BARS, 0])
        j, pos = divmod(m, BAR_MINUTES)
        rec[2] += 1
        if pos == 0:
            rec[0][j] = op
        if pos == BAR_MINUTES - 1:
            rec[1][j] = cl
    return {d: (v[0], v[1], v[2]) for d, v in out.items()}


def load_index_bars(path=INDEX_DB, start=FIRST_SESSION, end=HELD_OUT_START):
    """{date: (opens, closes, minutes)} for the NIFTY 50, from Kite one-minute bars."""
    con = _ro(path)
    rows = con.execute("SELECT ts, open, close FROM bars WHERE symbol=? AND ts >= ? AND ts < ? ORDER BY ts",
                       (INDEX_SYMBOL, start, end)).fetchall()
    con.close()
    if not rows:
        raise RuntimeError("no index bars read")
    assert max(r[0] for r in rows) < end, "an index bar on or after %s was read" % end
    any_minute = sorted({r[0][:10] for r in rows})
    return aggregate_index_minutes(rows), {"rows": len(rows), "first": rows[0][0], "last": rows[-1][0],
                                           "dates_any_minute": any_minute}


def load_fetch_spans(path=KITE_DB):
    con = _ro(path)
    rows = con.execute("SELECT symbol, from_date, to_date, fetched_at FROM fetched WHERE interval='5m'").fetchall()
    con.close()
    return [{"symbol": r[0], "from_date": r[1], "to_date": r[2], "fetched_at": r[3]} for r in rows]


def spans_are_whole_days(spans):
    """Kite's as-of-fetch adjustment (#108) can only step where one fetched span ends and
    the next begins. If every boundary is at midnight, a session's bars all come from one
    fetch, so returns inside a session are never affected."""
    bad = [s for s in spans if not (str(s["from_date"]).endswith("T00:00:00") and str(s["to_date"]).endswith("T00:00:00"))]
    return {"spans": len(spans), "not_whole_days": bad[:20], "count_not_whole_days": len(bad)}


def load_sectors(path=SECTOR_CSV):
    with open(path, newline="") as f:
        return {r["Symbol"].strip(): r["Industry"].strip() for r in csv.DictReader(f)}


def load_panel(symbols):
    """The repaired bhavcopy panel (nse_prices.load(wide=True)) as dense arrays over
    `symbols`: (panel dates, C adjusted close, V traded value, H, L), rows oldest first,
    NaN where a symbol has no row. The panel excludes 2026 unless asked; asserted."""
    np = _np()
    from research import nse_prices
    pdates, chains, meta, _events = nse_prices.load(wide=True)
    assert pdates[-1] < HELD_OUT_START, "the panel holds a held-out session"
    T, N = len(pdates), len(symbols)
    arr = {key: np.full((T, N), np.nan) for key in ("close", "val", "high", "low")}
    missing = []
    for n, s in enumerate(symbols):
        ch = chains.get(s)
        if ch is None:
            missing.append(s)
            continue
        idx = np.array(ch["idx"], dtype=np.int64)
        for key in arr:
            arr[key][idx, n] = np.array(ch[key], dtype=float)
    info = {"sessions": T, "first": pdates[0], "last": pdates[-1], "symbols": N, "missing_symbols": missing,
            "fund_units_excluded": meta.get("fund_units_excluded") if isinstance(meta, dict) else None}
    return list(pdates), arr["close"], arr["val"], arr["high"], arr["low"], info, chains


# ---- characteristics (daily, from panel rows dated before the session) -----------------------

def daily_returns(C):
    np = _np()
    R = np.full(C.shape, np.nan)
    R[1:] = C[1:] / C[:-1] - 1.0
    return R


def market_returns(R, member_mask):
    """Equal-weighted mean daily return of the point-in-time members, row by row; NaN when
    fewer than MIN_MARKET_MEMBERS have a return."""
    np = _np()
    out = np.full(R.shape[0], np.nan)
    for p in range(R.shape[0]):
        v = R[p, member_mask[p]]
        v = v[~np.isnan(v)]
        if len(v) >= MIN_MARKET_MEMBERS:
            out[p] = v.mean()
    return out


def _window_mean(X, w):
    np = _np()
    win = X[-w:]
    cnt = (~np.isnan(win)).sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.nansum(win, 0) / cnt
    m[cnt < need(w)] = np.nan
    return m


def _window_std(X, w):
    np = _np()
    win = X[-w:]
    cnt = (~np.isnan(win)).sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = np.nansum(win, 0) / cnt
        ss = np.nansum((win - mu) ** 2, 0)
        sd = np.sqrt(ss / (cnt - 1))
    sd[cnt < need(w)] = np.nan
    return sd


def _window_ols(y, x, w):
    """Per column: OLS of y on x (with intercept) over the last w rows, pairwise-valid.
    Returns (slope, residual sd with n-2 degrees of freedom)."""
    np = _np()
    Y = y[-w:]
    X = np.broadcast_to(x[-w:, None], Y.shape)
    ok = ~np.isnan(Y) & ~np.isnan(X)
    n = ok.sum(0).astype(float)
    Xm = np.where(ok, X, 0.0)
    Ym = np.where(ok, Y, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mx = Xm.sum(0) / n
        my = Ym.sum(0) / n
        dx = np.where(ok, X - mx, 0.0)
        dy = np.where(ok, Y - my, 0.0)
        sxx = (dx * dx).sum(0)
        sxy = (dx * dy).sum(0)
        beta = sxy / sxx
        resid = np.where(ok, dy - beta * dx, 0.0)
        rsd = np.sqrt((resid * resid).sum(0) / (n - 2))
    bad = n < need(w)
    beta[bad] = np.nan
    rsd[bad] = np.nan
    return beta, rsd


def characteristics(C, V, H, L, M):
    """The 12 characteristics at the last row of the inputs, which must hold only panel
    rows dated before the session. C, V, H, L: (T, N); M: (T,). {name: (N,) array}."""
    np = _np()
    T = C.shape[0]
    R = daily_returns(C)
    t = T - 1
    out = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        Vp = np.where(V > 0, V, np.nan)
        out["LIQ"] = np.log(_window_mean(Vp, 60))
        out["TURN"] = _window_mean(Vp, 5) / _window_mean(Vp, 60)
        out["ILLIQ"] = _window_mean(np.abs(R) / Vp, 60)

        def ratio(a, b):
            if t - b < 0:
                return np.full(C.shape[1], np.nan)
            return C[t - a] / C[t - b] - 1.0

        out["MOM"] = ratio(21, 252)
        out["REV21"] = ratio(0, 21)
        out["REV5"] = ratio(0, 5)
        out["REV1"] = ratio(0, 1)
        out["VOL"] = _window_std(R, 60)
        _b60, rsd60 = _window_ols(R, M, 60)
        out["IVOL"] = rsd60
        b250, _r = _window_ols(R, M, 250)
        out["BETA"] = b250
        win = C[-252:]
        cnt = (~np.isnan(win)).sum(0)
        hi52 = C[t] / np.nanmax(np.where(np.isnan(win), -np.inf, win), 0)
        hi52[(cnt < need(252)) | np.isnan(C[t])] = np.nan
        out["HIGH52"] = hi52
        rng = np.log(np.where((H > 0) & (L > 0), H / L, np.nan))
        out["RANGE"] = _window_mean(rng, 21)
    for key in out:
        out[key] = np.where(np.isfinite(out[key]), out[key], np.nan)
    return out


# ---- factor portfolios (five-minute bars of one session) -------------------------------------

def bar_returns(O, C):
    """(75, N) or (75,) bar returns: bar 0 close/open - 1, later bars close/previous close - 1."""
    np = _np()
    r = np.full(C.shape, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r[0] = C[0] / O[0] - 1.0
        r[1:] = C[1:] / C[:-1] - 1.0
    return r


def _rowmean(A):
    """Mean of each row over its finite entries; NaN for a row with none."""
    np = _np()
    ok = ~np.isnan(A)
    cnt = ok.sum(1)
    s = np.where(ok, A, 0.0).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = s / cnt
    m[cnt == 0] = np.nan
    return m


def tercile_groups(values, eligible):
    """(bottom, top) column indices: the eligible columns with a finite value, sorted by
    value then column (symbols are in alphabetical order), n // 3 each end. None when
    fewer than MIN_RANKED are eligible."""
    np = _np()
    cols = np.where(eligible & np.isfinite(values))[0]
    if len(cols) < MIN_RANKED:
        return None
    order = cols[np.lexsort((cols, values[cols]))]
    q = len(cols) // 3
    return order[:q], order[-q:]


def session_factors(O, C, IO, IC, chars, members, sector_of):
    """The 23 factor series on one session: (75, 23) array, NaN where undefined.
    O, C: (75, N) stock bars; IO, IC: (75,) index bars; chars: {name: (N,)} from panel rows
    before the session; members: (N,) bool, point-in-time members; sector_of: (N,) labels.
    Also returns the number of ranked members per characteristic."""
    np = _np()
    r = bar_returns(O, C)
    ri = bar_returns(IO, IC)
    F = np.full((BARS, len(FACTORS)), np.nan)
    ranked = {}
    for f, name in enumerate(CHARS):
        g = tercile_groups(chars[name], members)
        ranked[name] = 0 if g is None else int((members & np.isfinite(chars[name])).sum())
        if g is None:
            continue
        bottom, top = g
        F[:, f] = _rowmean(r[:, top]) - _rowmean(r[:, bottom])
    ew = _rowmean(r[:, members])
    for s, (code, label) in enumerate(SECTORS.items()):
        cols = np.where(members & (sector_of == label))[0]
        if len(cols):
            F[:, len(CHARS) + s] = _rowmean(r[:, cols]) - ew
    F[:, FACTORS.index("MKT")] = ri
    F[:, FACTORS.index("EWX")] = ew - ri
    return F, ranked


def predictors_at(F_s, F_prev, i):
    """The 92 predictors at the close of bar i: per factor, the last bar, the last six bars,
    the session so far, and the previous session. Missing factor bars count as 0."""
    np = _np()
    Fz = np.nan_to_num(F_s[: i + 1], nan=0.0)
    Pz = np.nan_to_num(F_prev, nan=0.0)
    last5 = Fz[i]
    last30 = Fz[max(0, i - 5): i + 1].sum(0)
    sofar = Fz.sum(0)
    prev = Pz.sum(0)
    return np.stack([last5, last30, sofar, prev], axis=1).reshape(-1)


def target_bp_index(IO, IC, i, kbars):
    """The index's return in bp from the open of bar i+1 to the close of bar i+k."""
    if i + kbars >= BARS:
        return float("nan")
    entry, exit_ = IO[i + 1], IC[i + kbars]
    return (exit_ / entry - 1.0) * 1e4


# ---- the dataset: everything the model sees ---------------------------------------------------

class Dataset:
    """Loaded sources and the derived arrays. `sessions` are the used sessions (prereg §2);
    X[s, i] holds the 92 predictors at the close of bar i of used session s (s >= 1)."""

    def __init__(self):
        self.info = {}

    # -- loading --
    def load(self, kite_db=KITE_DB, index_db=INDEX_DB):
        np = _np()
        t0 = time.time()
        dates, syms, O, C, sinfo = load_stock_bars(kite_db)
        index_bars, iinfo = load_index_bars(index_db)
        self.info["stock_cache"] = sinfo
        self.info["index_db"] = iinfo
        self.syms = syms
        self.membership_rows = k.load_membership_rows()
        sectors = load_sectors()
        self.sector_of = np.array([sectors.get(s, "") for s in syms], dtype=object)
        self.info["symbols_without_sector"] = [s for s in syms if s not in sectors]
        self.all_dates, self.O_all, self.C_all = dates, O, C
        self.index_bars = index_bars
        # panel: every symbol that is ever a member, so the market return has no survivorship
        member_syms = sorted({r["symbol"] for r in self.membership_rows} | set(syms))
        pdates, PC, PV, PH, PL, pinfo, chains = load_panel(member_syms)
        self.chains = chains
        self.info["panel"] = pinfo
        self.pdates = pdates
        self.member_syms = member_syms
        pcol = {s: n for n, s in enumerate(member_syms)}
        self.cache_cols = np.array([pcol[s] for s in syms])
        start = max(0, _bisect(pdates, dates[0]) - 320)
        self.p0 = start
        self.PC, self.PV, self.PH, self.PL = PC[start:], PV[start:], PH[start:], PL[start:]
        self.pdates_w = pdates[start:]
        mem = np.zeros((len(self.pdates_w), len(member_syms)), dtype=bool)
        for p, d in enumerate(self.pdates_w):
            m = k.membership_asof(self.membership_rows, d)
            for s in m:
                if s in pcol:
                    mem[p, pcol[s]] = True
        self.panel_members = mem
        self.PR = daily_returns(self.PC)
        self.M = market_returns(self.PR, mem)
        self.info["load_seconds"] = round(time.time() - t0, 1)
        return self

    # -- sessions --
    def members_on(self, d):
        """(N,) bool: point-in-time NIFTY 100 members on d among the cache symbols."""
        np = _np()
        cache = self.__dict__.setdefault("_members", {})
        if d not in cache:
            m = k.membership_asof(self.membership_rows, d)
            cache[d] = np.array([s in m for s in self.syms])
        return cache[d]

    def choose_sessions(self):
        """Used sessions: in both sources, the index complete (375 minutes), and at least
        MIN_FULL_MEMBERS members with all 75 bars."""
        np = _np()
        drow = {d: i for i, d in enumerate(self.all_dates)}
        used, dropped = [], []
        for d in self.all_dates:
            ib = self.index_bars.get(d)
            if ib is None:
                dropped.append((d, "no index bars"))
                continue
            if ib[2] != INDEX_MINUTES or any(v is None for v in ib[0]) or any(v is None for v in ib[1]):
                dropped.append((d, "index has %d minutes" % ib[2]))
                continue
            s = drow[d]
            full = (~np.isnan(self.O_all[s]).any(0)) & (~np.isnan(self.C_all[s]).any(0))
            n_full = int((full & self.members_on(d)).sum())
            if n_full < MIN_FULL_MEMBERS:
                dropped.append((d, "%d members with all bars" % n_full))
                continue
            used.append(d)
        only_index = sorted(set(self.index_bars) - set(self.all_dates))
        self.sessions = used
        self.srow = [drow[d] for d in used]
        self.info["sessions"] = {"cached": len(self.all_dates), "index": len(self.index_bars), "used": len(used),
                                 "dropped": dropped, "index_only_dates": only_index,
                                 "first": used[0], "last": used[-1]}
        return used

    # -- characteristics per session --
    def panel_upto(self, d):
        """Number of panel rows (in the loaded window) dated before d."""
        return _bisect(self.pdates_w, d)

    def chars_for(self, d, PC=None, PV=None, PH=None, PL=None, M=None):
        """Characteristics of the cache symbols for session d, from panel rows before d.
        The arrays can be passed truncated (the look-ahead proof); by default the loaded
        panel is sliced to the rows before d."""
        n = self.panel_upto(d)
        cc = self.cache_cols
        PC = self.PC[:n] if PC is None else PC
        PV = self.PV[:n] if PV is None else PV
        PH = self.PH[:n] if PH is None else PH
        PL = self.PL[:n] if PL is None else PL
        M = self.M[:n] if M is None else M
        return characteristics(PC[:, cc], PV[:, cc], PH[:, cc], PL[:, cc], M)

    def index_arrays(self, d):
        np = _np()
        ib = self.index_bars[d]
        return np.array(ib[0], dtype=float), np.array(ib[1], dtype=float)

    def build_factors(self):
        np = _np()
        S = len(self.sessions)
        self.F = np.full((S, BARS, len(FACTORS)), np.nan)
        self.ranked = {}
        self.chars = {}
        for s, d in enumerate(self.sessions):
            ch = self.chars_for(d)
            self.chars[d] = ch
            IO, IC = self.index_arrays(d)
            F, ranked = session_factors(self.O_all[self.srow[s]], self.C_all[self.srow[s]], IO, IC, ch,
                                        self.members_on(d), self.sector_of)
            self.F[s] = F
            self.ranked[d] = ranked
        return self.F

    def build_predictors(self):
        np = _np()
        S = len(self.sessions)
        self.X = np.full((S, BARS, len(PREDICTORS)), np.nan)
        for s in range(1, S):
            for i in range(FIRST_DECISION_BAR, BARS):
                self.X[s, i] = predictors_at(self.F[s], self.F[s - 1], i)
        return self.X

    def build_targets(self, before=None):
        """{horizon: (S, 75) array of target bp}; NaN for sessions on or after `before`,
        so stage 0 never computes a scoring-sample target."""
        np = _np()
        S = len(self.sessions)
        out = {}
        for h, kb in HORIZONS.items():
            Y = np.full((S, BARS), np.nan)
            for s, d in enumerate(self.sessions):
                if before is not None and d >= before:
                    continue
                IO, IC = self.index_arrays(d)
                for i in range(FIRST_DECISION_BAR, BARS - kb):
                    Y[s, i] = target_bp_index(IO, IC, i, kb)
            out[h] = Y
        self.Y = out
        return out


def _bisect(sorted_list, x):
    """Number of items < x."""
    lo, hi = 0, len(sorted_list)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_list[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


# ---- Ridge, cross-validation, refits -----------------------------------------------------------

def fit_ridge(X, y, alpha):
    """numpy Ridge: standardise X with these rows' mean and sd (ddof 0), clip at ±CLIP,
    NaN -> 0, constant columns -> 0; winsorise y at these rows' WINSOR quantiles; intercept
    = mean of the winsorised y, unpenalised; lambda = alpha * n."""
    np = _np()
    assert np.isfinite(X).all() and np.isfinite(y).all(), "a training row has a missing value"
    mu = X.mean(0)
    sd = X.std(0)
    lo, hi = np.quantile(y, WINSOR)
    yw = np.clip(y, lo, hi)
    Z = standardise(X, mu, sd)
    ybar = yw.mean()
    n, p = Z.shape
    A = Z.T @ Z + alpha * n * np.eye(p)
    b = np.linalg.solve(A, Z.T @ (yw - ybar))
    return {"mu": mu, "sd": sd, "ybar": float(ybar), "b": b, "alpha": alpha, "n": int(n),
            "winsor": (float(lo), float(hi))}


def standardise(X, mu, sd):
    np = _np()
    safe = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / safe
    Z[:, sd <= 0] = 0.0
    Z = np.clip(Z, -CLIP, CLIP)
    return np.nan_to_num(Z, nan=0.0)


def predict(model, X):
    return model["ybar"] + standardise(X, model["mu"], model["sd"]) @ model["b"]


def rows(ds, sessions_idx, bars, Y, X=None):
    """Stacked (X, y, session index, bar) over the given sessions and bars where the
    target is defined (for fitting) — y may be NaN when only forecasting."""
    np = _np()
    X = ds.X if X is None else X
    ss, ii = [], []
    for s in sessions_idx:
        for i in bars:
            ss.append(s)
            ii.append(i)
    ss = np.array(ss, dtype=int)
    ii = np.array(ii, dtype=int)
    if len(ss) == 0:
        return np.zeros((0, X.shape[2])), np.zeros(0), ss, ii
    return X[ss, ii], (Y[ss, ii] if Y is not None else np.full(len(ss), np.nan)), ss, ii


def training_rows(ds, train_idx, h, Y, X=None):
    np = _np()
    Xr, yr, ss, ii = rows(ds, train_idx, train_bars(HORIZONS[h]), Y, X)
    keep = np.isfinite(yr)
    return Xr[keep], yr[keep], ss[keep], ii[keep]


def first_window(sessions):
    """Indices of the first training window: the second used session to six sessions before
    the first session of FIRST_MONTH."""
    j = next(n for n, d in enumerate(sessions) if d[:7] >= FIRST_MONTH)
    return list(range(1, j - PURGE)), j


def cv_folds(window_idx):
    """[(train indices, validation indices)] for blocks 2..5, purging the 5 sessions before
    each validation block."""
    np = _np()
    blocks = [list(b) for b in np.array_split(np.array(window_idx), CV_BLOCKS)]
    folds = []
    for v in range(1, CV_BLOCKS):
        train = [s for b in blocks[:v] for s in b]
        train = train[:-PURGE] if len(train) > PURGE else []
        folds.append((train, blocks[v]))
    return folds


def choose_alpha(ds, h, Y, X=None):
    """The α with the lowest pooled validation MSE on the winsorised target (thresholds
    from each fold's training rows); a tie goes to the larger α."""
    np = _np()
    window, _j = first_window(ds.sessions)
    folds = cv_folds(window)
    curve = []
    for a in ALPHAS:
        sse, cnt = 0.0, 0
        for tr, va in folds:
            Xt, yt, _s, _i = training_rows(ds, tr, h, Y, X)
            Xv, yv, _s2, _i2 = training_rows(ds, va, h, Y, X)
            m = fit_ridge(Xt, yt, a)
            yvw = np.clip(yv, *m["winsor"])
            e = predict(m, Xv) - yvw
            sse += float((e * e).sum())
            cnt += len(e)
        curve.append((a, sse / cnt))
    best = min(curve, key=lambda c: (c[1], -c[0]))
    fold_info = [{"train": [ds.sessions[tr[0]], ds.sessions[tr[-1]]], "validate": [ds.sessions[va[0]], ds.sessions[va[-1]]],
                  "gap_sessions": va[0] - tr[-1] - 1} for tr, va in folds]
    return best[0], curve, fold_info


def month_sessions(sessions, month):
    return [n for n, d in enumerate(sessions) if d[:7] == month]


def months_between(first, last):
    out, y, m = [], int(first[:4]), int(first[5:7])
    while "%04d-%02d" % (y, m) <= last:
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def refit_plan(sessions, first=FIRST_MONTH, last=LAST_MONTH):
    """[(month, training session indices, forecast session indices)]: expanding window from
    the second used session to six sessions before the month's first session."""
    plan = []
    for mo in months_between(first, last):
        fc = month_sessions(sessions, mo)
        if not fc:
            continue
        plan.append((mo, list(range(1, fc[0] - PURGE)), fc))
    return plan


def walk_forward(ds, h, alpha, Y, first=FIRST_MONTH, last=LAST_MONTH, X=None, keep_models=False):
    """Refit monthly and forecast the scoring grid. Returns decisions [(session idx, bar,
    forecast)] and per-month training facts."""
    decisions, facts, models = [], [], {}
    for mo, train, fc in refit_plan(ds.sessions, first, last):
        Xt, yt, _s, _i = training_rows(ds, train, h, Y, X)
        m = fit_ridge(Xt, yt, alpha)
        Xf, _yf, ss, ii = rows(ds, fc, GRID[h], None, X)
        f = predict(m, Xf)
        decisions += [(int(s), int(i), float(v)) for s, i, v in zip(ss, ii, f)]
        facts.append({"month": mo, "train_first": ds.sessions[train[0]], "train_last": ds.sessions[train[-1]],
                      "first_forecast": ds.sessions[fc[0]], "gap_sessions": fc[0] - train[-1] - 1,
                      "train_rows": m["n"]})
        if keep_models:
            models[mo] = m
    return decisions, facts, models


# ---- trade rule and statistics --------------------------------------------------------------

def trades_from(decisions, targets, cost=COST_BP):
    """decisions: [(date, bar, forecast)]; targets: {(date, bar): bp}. A trade when
    |forecast| > cost, direction its sign; net = direction x target - cost."""
    out = []
    for d, i, f in decisions:
        if abs(f) > cost:
            r = targets[(d, i)]
            out.append({"date": d, "bar": i, "side": 1 if f > 0 else -1, "forecast": f, "gross": (1 if f > 0 else -1) * r,
                        "net": (1 if f > 0 else -1) * r - cost})
    return out


def judge(trades, sample_sessions, n_trials=N_CONFIGS):
    """The prereg §8 gate over one horizon's trades on a sample of sessions."""
    by_day = defaultdict(list)
    for t in trades:
        by_day[t["date"]].append(t["net"])
    days = sorted(by_day)
    series = [st.mean(by_day[d]) for d in days]
    m, t_, se = k.tstat(series)
    first, second = splits.halves(sorted(sample_sessions))
    f_set, s_set = set(first), set(second)
    h1 = [st.mean(by_day[d]) for d in days if d in f_set]
    h2 = [st.mean(by_day[d]) for d in days if d in s_set]
    dsr = evaluation.deflated_sharpe_ratio(series, n_trials) if len(series) >= 10 else {"dsr": None}
    out = {"trades": len(trades), "sessions": len(sample_sessions), "sessions_with_trades": len(days),
           "mean_net_bp_per_trade": st.mean([x["net"] for x in trades]) if trades else None,
           "mean_gross_bp_per_trade": st.mean([x["gross"] for x in trades]) if trades else None,
           "per_session_mean_bp": m, "t": t_, "se": se,
           "half1_bp": st.mean(h1) if h1 else None, "half2_bp": st.mean(h2) if h2 else None,
           "half_sessions": [len(first), len(second)],
           "dsr": dsr.get("dsr"), "sharpe_per_session": dsr.get("sharpe"), "dsr_n_trials": n_trials}
    checks = {
        "enough_trades": len(trades) >= MIN_TRADES and len(days) >= MIN_TRADE_SESSIONS,
        "positive_net": (out["mean_net_bp_per_trade"] or 0) > 0,
        "t_over_2": (t_ or 0) > T_BAR,
        "both_halves_positive": (out["half1_bp"] or 0) > 0 and (out["half2_bp"] or 0) > 0,
        "dsr_over_bar": (out["dsr"] or 0) >= DSR_BAR,
    }
    out["checks"] = checks
    out["passes"] = all(checks.values())
    return out


def _avg_rank(v):
    np = _np()
    import pandas as pd
    return pd.Series(v).rank(method="average").to_numpy(dtype=float)


def forecast_stats(f, r):
    """Information, not a gate: IC (Pearson, Spearman) with the naive t, the paper's
    uncentred out-of-sample R^2, the sign's hit rate and the gross Sign rule."""
    np = _np()
    f, r = np.asarray(f, dtype=float), np.asarray(r, dtype=float)
    n = len(f)
    if n < 3 or f.std() == 0 or r.std() == 0:
        return {"n": n, "note": "too few or constant values"}
    ic = float(np.corrcoef(f, r)[0, 1])
    ric = float(np.corrcoef(_avg_rank(f), _avg_rank(r))[0, 1])

    def tt(c):
        return c * math.sqrt((n - 2) / max(1e-12, 1 - c * c))

    sign = np.sign(f)
    return {"n": n, "ic": ic, "ic_t": tt(ic), "rank_ic": ric, "rank_ic_t": tt(ric),
            "r2_oos_uncentred": float(1 - ((r - f) ** 2).sum() / (r ** 2).sum()),
            "hit_rate": float((sign * r > 0).mean()), "sign_rule_gross_bp": float((sign * r).mean()),
            "forecast_abs_pct": {q: float(np.percentile(np.abs(f), q)) for q in (50, 90, 99, 100)},
            "share_above_cost": float((np.abs(f) > COST_BP).mean())}


# ---- stage 0 checks ----------------------------------------------------------------------------

class Halt(Exception):
    pass


EXPECTED_DROPPED = {  # amendment 4
    "2024-11-01": "no index bars",       # Muhurat, 18:00-19:00 IST: no regular-hours bar in either database
    "2025-10-21": "index has 60 minutes",  # Muhurat, 13:45-14:45 IST
    "2026-01-01": "no index bars",       # in the stock cache (before HELD_OUT_START); the index database ends 2025-12-31
}


def check_coverage(ds, st0):
    np = _np()
    ses = st0["data"]["sessions"]
    dropped = {d: why for d, why in ses["dropped"]}
    index_dates = set(ds.info["index_db"]["dates_any_minute"])
    stock_dates = {d for d in ds.all_dates if d <= "2025-12-31"}
    selection = k.selection_sessions(ds.all_dates)
    scoring = [d for d in selection if d in set(ds.sessions)]
    first, second = splits.halves(scoring)
    members_full = []
    for d, s in zip(ds.sessions, ds.srow):
        full = (~np.isnan(ds.O_all[s]).any(0)) & (~np.isnan(ds.C_all[s]).any(0))
        members_full.append(int((full & ds.members_on(d)).sum()))
    cov = {"dropped": dropped, "expected_dropped": EXPECTED_DROPPED,
           "cache_equals_index_dates_to_2025_12_31": stock_dates == index_dates,
           "dates_only_in_cache": sorted(stock_dates - index_dates),
           "dates_only_in_index": sorted(index_dates - stock_dates),
           "selection_sessions": len(selection), "scoring_sessions": len(scoring),
           "scoring_first_last": [scoring[0], scoring[-1]] if scoring else None,
           "scoring_halves": [len(first), len(second)],
           "members_with_all_bars": {"min": min(members_full), "median": float(np.median(members_full)),
                                     "max": max(members_full)},
           "held_out_read": {"stock_max_ts_ist": ds.info["stock_cache"]["max_ts_ist"],
                             "index_last": ds.info["index_db"]["last"], "panel_last": ds.info["panel"]["last"]}}
    st0["coverage"] = cov
    ok = (dropped == EXPECTED_DROPPED and cov["cache_equals_index_dates_to_2025_12_31"] and len(scoring) == 78
          and min(len(first), len(second)) >= 30
          and ds.info["stock_cache"]["max_ts_ist"] < HELD_OUT_START
          and ds.info["index_db"]["last"] < HELD_OUT_START and ds.info["panel"]["last"] < HELD_OUT_START)
    if not ok:
        raise Halt("coverage: %s" % json.dumps({k_: cov[k_] for k_ in ("dropped", "cache_equals_index_dates_to_2025_12_31",
                                                                       "dates_only_in_cache", "dates_only_in_index",
                                                                       "scoring_sessions", "scoring_halves")}))
    return scoring


def check_alignment(ds, st0, before=SCORING_START):
    """Correlation of the index's bar return with the equal-weighted member bar return at
    lags -2..+2 (index lagged), within sessions, sessions before the scoring sample."""
    np = _np()
    xs = {lag: ([], []) for lag in range(-2, 3)}
    for s, d in enumerate(ds.sessions):
        if d >= before:
            break
        ew = ds.F[s, :, FACTORS.index("EWX")] + ds.F[s, :, FACTORS.index("MKT")]
        ri = ds.F[s, :, FACTORS.index("MKT")]
        for lag in range(-2, 3):
            for j in range(2, BARS - 2):
                a, b = ew[j], ri[j + lag]
                if np.isfinite(a) and np.isfinite(b):
                    xs[lag][0].append(a)
                    xs[lag][1].append(b)
    corr = {lag: float(np.corrcoef(v[0], v[1])[0, 1]) for lag, v in xs.items()}
    spans = spans_are_whole_days(load_fetch_spans())
    st0["alignment"] = {"corr_by_index_lag": corr, "pairs": len(xs[0][0]), "fetch_spans": spans}
    best = max(corr, key=lambda lag: corr[lag])
    if best != 0 or corr[0] < 0.7 or spans["count_not_whole_days"]:
        raise Halt("alignment: best lag %s, corr0 %.3f, spans not whole days %d"
                   % (best, corr[0], spans["count_not_whole_days"]))


def hand_characteristic(ds, sym, d, name):
    """One characteristic by plain Python from the panel chain lists, independently of the
    dense arrays: rows are panel sessions before d."""
    pos = {x: n for n, x in enumerate(ds.pdates)}
    t = _bisect(ds.pdates, d) - 1

    def series(s, key):
        ch = ds.chains[s]
        return {i: v for i, v in zip(ch["idx"], ch[key])}

    C = series(sym, "close")

    def c(i):
        return C.get(i)

    def ret(s_close, i):
        a, b = s_close.get(i), s_close.get(i - 1)
        return None if a is None or b is None else a / b - 1.0

    def market(i):
        dd = ds.pdates[i]
        vals = []
        for s in k.membership_asof(ds.membership_rows, dd):
            if s in ds.chains:
                cs = _chain_cache(ds, s)
                r = ret(cs, i)
                if r is not None:
                    vals.append(r)
        return sum(vals) / len(vals) if len(vals) >= MIN_MARKET_MEMBERS else None

    def window(w):
        return list(range(t - w + 1, t + 1))

    if name in ("LIQ", "TURN"):
        V = series(sym, "val")

        def mv(w):
            vals = [V[i] for i in window(w) if V.get(i) is not None and V[i] > 0]
            return sum(vals) / len(vals) if len(vals) >= need(w) else None

        if name == "LIQ":
            m = mv(60)
            return None if m is None else math.log(m)
        a, b = mv(5), mv(60)
        return None if a is None or b is None else a / b
    if name == "ILLIQ":
        V = series(sym, "val")
        vals = []
        for i in window(60):
            r = ret(C, i)
            if r is not None and V.get(i) is not None and V[i] > 0:
                vals.append(abs(r) / V[i])
        return sum(vals) / len(vals) if len(vals) >= need(60) else None
    if name in ("MOM", "REV21", "REV5", "REV1"):
        a, b = {"MOM": (21, 252), "REV21": (0, 21), "REV5": (0, 5), "REV1": (0, 1)}[name]
        x, y = c(t - a), c(t - b)
        return None if x is None or y is None else x / y - 1.0
    if name == "VOL":
        vals = [ret(C, i) for i in window(60)]
        vals = [v for v in vals if v is not None]
        if len(vals) < need(60):
            return None
        mu = sum(vals) / len(vals)
        return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))
    if name in ("IVOL", "BETA"):
        w = 60 if name == "IVOL" else 250
        pairs = []
        for i in window(w):
            r = ret(C, i)
            mk = market(i)
            if r is not None and mk is not None:
                pairs.append((mk, r))
        if len(pairs) < need(w):
            return None
        mx = sum(p[0] for p in pairs) / len(pairs)
        my = sum(p[1] for p in pairs) / len(pairs)
        sxx = sum((p[0] - mx) ** 2 for p in pairs)
        sxy = sum((p[0] - mx) * (p[1] - my) for p in pairs)
        beta = sxy / sxx
        if name == "BETA":
            return beta
        ss = sum((p[1] - my - beta * (p[0] - mx)) ** 2 for p in pairs)
        return math.sqrt(ss / (len(pairs) - 2))
    if name == "HIGH52":
        vals = [C[i] for i in window(252) if C.get(i) is not None]
        if len(vals) < need(252) or c(t) is None:
            return None
        return c(t) / max(vals)
    if name == "RANGE":
        H, L = series(sym, "high"), series(sym, "low")
        vals = [math.log(H[i] / L[i]) for i in window(21)
                if H.get(i) is not None and L.get(i) is not None and H[i] > 0 and L[i] > 0]
        return sum(vals) / len(vals) if len(vals) >= need(21) else None
    raise ValueError(name)


def _chain_cache(ds, s):
    cache = ds.__dict__.setdefault("_close_maps", {})
    if s not in cache:
        ch = ds.chains[s]
        cache[s] = {i: v for i, v in zip(ch["idx"], ch["close"])}
    return cache[s]


def _close(a, b, rel=1e-12, abs_tol=0.0):
    """Both missing, or equal to a relative `rel` (characteristics, §9.3) or an absolute
    `abs_tol` (factor returns, §9.4: 1e-12 in return units)."""
    if a is None or b is None or (isinstance(b, float) and math.isnan(b)) or (isinstance(a, float) and math.isnan(a)):
        a_nan = a is None or (isinstance(a, float) and math.isnan(a))
        b_nan = b is None or (isinstance(b, float) and math.isnan(b))
        return a_nan and b_nan
    if abs_tol:
        return abs(a - b) <= abs_tol
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-300)


def check_characteristics(ds, st0, rng):
    np = _np()
    picks = []
    pool = [(d, n) for d in ds.sessions for n in range(len(ds.syms)) if ds.members_on(d)[n]]
    for j in rng.choice(len(pool), HAND_CHECKS, replace=False):
        picks.append(pool[int(j)])
    results, bad = [], []
    for d, n in picks:
        sym = ds.syms[n]
        row = {"symbol": sym, "session": d}
        for name in CHARS:
            vec = float(ds.chars[d][name][n])
            hand = hand_characteristic(ds, sym, d, name)
            ok = _close(vec, hand)
            row[name] = {"vectorised": vec, "hand": hand, "match": ok}
            if not ok:
                bad.append((sym, d, name, vec, hand))
        results.append(row)
    # a later corporate action multiplies every earlier adjusted close by one constant
    inv = []
    for d, n in picks:
        npos = ds.panel_upto(d)
        PCs = ds.PC[:npos] * 1.2345
        scaled = ds.chars_for(d, PC=PCs)
        for name in CHARS:
            a, b = float(scaled[name][n]), float(ds.chars[d][name][n])
            if not _close(a, b):
                inv.append((ds.syms[n], d, name, a, b))
    cover = {}
    for name in CHARS:
        counts = [ds.ranked[d][name] for d in ds.sessions]
        cover[name] = {"min": int(min(counts)), "median": float(np.median(counts))}
    st0["characteristics"] = {"hand_checks": results, "mismatches": bad, "scale_invariance_failures": inv,
                              "ranked_members_per_session": cover}
    if bad or inv or min(v["min"] for v in cover.values()) < MIN_RANKED:
        raise Halt("characteristics: %d hand mismatches, %d scale failures, min ranked %s"
                   % (len(bad), len(inv), min(v["min"] for v in cover.values())))


def hand_factors(ds, s, j, kite_db=KITE_DB):
    """All 23 series at bar j of used session s, by plain Python, re-reading the two bars
    from the cache (not the dense arrays)."""
    d = ds.sessions[s]
    con = _ro(kite_db)
    t_j = int(datetime.fromisoformat("%sT%s" % (d, bar_hhmm(j))).replace(tzinfo=IST).timestamp())
    t_p = t_j - BAR_MINUTES * 60
    got = defaultdict(dict)
    for sym, ts, op, cl in con.execute("SELECT symbol, ts, open, close FROM candles WHERE interval='5m' AND ts IN (?, ?)",
                                       (t_j, t_p)):
        got[sym][ts] = (op, cl)
    con.close()

    def r_stock(sym):
        b = got.get(sym, {})
        if j == 0:
            x = b.get(t_j)
            return None if x is None else x[1] / x[0] - 1.0
        a, p = b.get(t_j), b.get(t_p)
        return None if a is None or p is None else a[1] / p[1] - 1.0

    members = [sym for sym in ds.syms if sym in k.membership_asof(ds.membership_rows, d)]
    rets = {sym: r_stock(sym) for sym in members}

    def mean(syms):
        v = [rets[x] for x in syms if rets[x] is not None]
        return sum(v) / len(v) if v else None

    ib = ds.index_bars[d]
    ri = ib[1][0] / ib[0][0] - 1.0 if j == 0 else ib[1][j] / ib[1][j - 1] - 1.0
    out = {}
    col = {x: n for n, x in enumerate(ds.syms)}
    for name in CHARS:
        vals = [(float(ds.chars[d][name][col[x]]), x) for x in members if math.isfinite(float(ds.chars[d][name][col[x]]))]
        if len(vals) < MIN_RANKED:
            out[name] = None
            continue
        vals.sort()
        q = len(vals) // 3
        top, bottom = mean([x for _, x in vals[-q:]]), mean([x for _, x in vals[:q]])
        out[name] = None if top is None or bottom is None else top - bottom
    ew = mean(members)
    for code, label in SECTORS.items():
        sec = [x for x in members if ds.sector_of[col[x]] == label]
        m = mean(sec)
        out[code] = None if m is None or ew is None else m - ew
    out["MKT"] = ri
    out["EWX"] = None if ew is None else ew - ri
    return out


def check_factors(ds, st0, rng):
    np = _np()
    results, bad = [], []
    for _ in range(HAND_CHECKS):
        s = int(rng.integers(1, len(ds.sessions)))
        j = int(rng.integers(0, BARS))
        hand = hand_factors(ds, s, j)
        row = {"session": ds.sessions[s], "bar": bar_hhmm(j)}
        for f, name in enumerate(FACTORS):
            vec = float(ds.F[s, j, f])
            ok = _close(vec, hand[name], abs_tol=1e-12)
            row[name] = ok
            if not ok:
                bad.append((ds.sessions[s], bar_hhmm(j), name, vec, hand[name]))
        results.append(row)
    flat = ds.F[1:].reshape(-1, len(FACTORS))
    keep = np.isfinite(flat).all(1)
    corr = np.corrcoef(flat[keep].T)
    missing = {name: int((~np.isfinite(ds.F[:, :, f])).sum()) for f, name in enumerate(FACTORS)}
    st0["factors"] = {"hand_checks": results, "mismatches": bad,
                      "bar_sd_bp": {name: float(np.nanstd(ds.F[:, :, f]) * 1e4) for f, name in enumerate(FACTORS)},
                      "missing_factor_bars": missing,
                      "largest_abs_correlations": _top_corr(corr),
                      "sessions_used_for_moments": "all used sessions (factor returns only, no target)"}
    if bad:
        raise Halt("factors: %d hand mismatches" % len(bad))


def _top_corr(corr, n=10):
    pairs = []
    for a in range(len(FACTORS)):
        for b in range(a + 1, len(FACTORS)):
            pairs.append((abs(float(corr[a, b])), FACTORS[a], FACTORS[b], float(corr[a, b])))
    pairs.sort(reverse=True)
    return [{"pair": [p[1], p[2]], "corr": p[3]} for p in pairs[:n]]


def truncated_predictors(ds, s, i):
    """The 92 predictors at (used session s, bar i), rebuilt from sources with every bar
    after the decision bar's close and every panel row dated on or after the session
    removed. The session list itself is a sample definition and is kept."""
    np = _np()
    d, dp = ds.sessions[s], ds.sessions[s - 1]
    npos = ds.panel_upto(d)
    PC, PV, PH, PL = ds.PC[:npos].copy(), ds.PV[:npos].copy(), ds.PH[:npos].copy(), ds.PL[:npos].copy()
    mem = ds.panel_members[:npos]
    M = market_returns(daily_returns(PC), mem)
    O_s = ds.O_all[ds.srow[s]].copy()
    C_s = ds.C_all[ds.srow[s]].copy()
    O_s[i + 1:] = np.nan
    C_s[i + 1:] = np.nan
    IO, IC = ds.index_arrays(d)
    IO, IC = IO.copy(), IC.copy()
    IO[i + 1:] = np.nan
    IC[i + 1:] = np.nan
    ch = characteristics(PC[:, ds.cache_cols], PV[:, ds.cache_cols], PH[:, ds.cache_cols], PL[:, ds.cache_cols], M)
    F_s, _r = session_factors(O_s, C_s, IO, IC, ch, ds.members_on(d), ds.sector_of)
    npp = ds.panel_upto(dp)
    Mp = market_returns(daily_returns(ds.PC[:npp]), ds.panel_members[:npp])
    chp = characteristics(ds.PC[:npp][:, ds.cache_cols], ds.PV[:npp][:, ds.cache_cols], ds.PH[:npp][:, ds.cache_cols],
                          ds.PL[:npp][:, ds.cache_cols], Mp)
    IOp, ICp = ds.index_arrays(dp)
    F_p, _r = session_factors(ds.O_all[ds.srow[s - 1]], ds.C_all[ds.srow[s - 1]], IOp, ICp, chp,
                              ds.members_on(dp), ds.sector_of)
    return predictors_at(F_s, F_p, i)


def check_lookahead(ds, st0, rng, scoring):
    np = _np()
    window, j_mar = first_window(ds.sessions)
    pseudo = [n for n, d in enumerate(ds.sessions) if FIRST_MONTH <= d[:7] and d <= PSEUDO_OOS_END]
    score = [n for n, d in enumerate(ds.sessions) if d in set(scoring)]
    per = LOOKAHEAD_CHECKS // 3
    picks = []
    for pool in (window, pseudo, score):
        for _ in range(per):
            picks.append((int(pool[int(rng.integers(0, len(pool)))]), int(rng.integers(FIRST_DECISION_BAR, LAST_EXIT_BAR))))
    bad = []
    for s, i in picks:
        full = ds.X[s, i]
        trunc = truncated_predictors(ds, s, i)
        if not np.array_equal(full, trunc):
            bad.append({"session": ds.sessions[s], "bar": bar_hhmm(i),
                        "max_abs_diff": float(np.nanmax(np.abs(full - trunc)))})
    st0["lookahead"] = {"checks": len(picks), "by_window": {"first_training_window": per, "pseudo_oos": per,
                                                            "scoring_sample": per},
                        "failures": bad, "bit_identical": not bad}
    if bad:
        raise Halt("look-ahead: %d of %d predictor vectors changed" % (len(bad), len(picks)))


def check_purge(ds, st0):
    window, j_mar = first_window(ds.sessions)
    plan = refit_plan(ds.sessions)
    gaps = [(mo, fc[0] - train[-1] - 1) for mo, train, fc in plan]
    folds = cv_folds(window)
    fold_gaps = [va[0] - tr[-1] - 1 for tr, va in folds]
    stage0_fit_last = max(ds.sessions[train[-1]] for mo, train, fc in plan if mo <= PSEUDO_OOS_END[:7])
    cv_last = ds.sessions[window[-1]]
    violations = []
    for mo, train, fc in plan:
        for s in fc:
            if max(train) > s - PURGE - 1:
                violations.append((mo, ds.sessions[s]))
    st0["purge"] = {"refit_gaps_sessions": gaps, "cv_fold_gaps_sessions": fold_gaps,
                    "first_window": [ds.sessions[window[0]], ds.sessions[window[-1]], len(window)],
                    "latest_training_session_of_any_stage0_fit": max(stage0_fit_last, cv_last),
                    "forecast_rows_with_training_inside_purge": violations}
    if (min(g for _, g in gaps) < PURGE or min(fold_gaps) < PURGE or violations
            or max(stage0_fit_last, cv_last) >= SCORING_START):
        raise Halt("purge: gaps %s, fold gaps %s, violations %d" % (gaps, fold_gaps, len(violations)))


def pseudo_sessions(ds):
    return [d for d in ds.sessions if FIRST_MONTH <= d[:7] and d <= PSEUDO_OOS_END]


def run_pipeline(ds, h, Y, X, first=FIRST_MONTH, last=PSEUDO_OOS_END[:7]):
    """CV -> monthly refits -> decisions, for the given predictor array."""
    alpha, curve, _f = choose_alpha(ds, h, Y, X)
    dec, facts, _m = walk_forward(ds, h, alpha, Y, first, last, X)
    return alpha, curve, dec, facts


def score_decisions(ds, dec, Y, sample):
    targets = {(ds.sessions[s], i): float(Y[s, i]) for s, i, _f in dec}
    decisions = [(ds.sessions[s], i, f) for s, i, f in dec if ds.sessions[s] in set(sample)]
    trades = trades_from(decisions, targets)
    return trades, decisions, targets


def check_controls(ds, st0, Y):
    """Positive control (planted target + noise) must pass both horizons; negative control
    (session-deranged predictors) must pass neither. Months 2025-03..2025-08 only."""
    np = _np()
    sample = pseudo_sessions(ds)
    window, _j = first_window(ds.sessions)
    out = {"sample": [sample[0], sample[-1], len(sample)], "positive": {}, "negative": {}}
    rng = np.random.default_rng(CONTROL_SEED)
    for h, kb in HORIZONS.items():
        Yh = Y[h]
        tr = [(s, i) for s in window for i in train_bars(kb)]
        sd = float(np.nanstd(np.array([Yh[s, i] for s, i in tr])))
        noise = rng.standard_normal(Yh.shape) * PLANTED_NOISE_MULT * sd
        planted = np.nan_to_num(Yh + noise, nan=0.0)
        Xp = np.concatenate([ds.X, planted[:, :, None]], axis=2)
        alpha, curve, dec, facts = run_pipeline(ds, h, Yh, Xp)
        trades, decisions, targets = score_decisions(ds, dec, Yh, sample)
        res = judge(trades, sample)
        f = [x[2] for x in decisions]
        r = [targets[(x[0], x[1])] for x in decisions]
        res["alpha"] = alpha
        res["corr_planted_target_first_window"] = float(np.corrcoef([planted[s, i] for s, i in tr],
                                                                    [Yh[s, i] for s, i in tr])[0, 1])
        res["forecast_stats"] = forecast_stats(f, r)
        out["positive"][h] = res
    last_idx = max(n for n, d in enumerate(ds.sessions) if d <= PSEUDO_OOS_END)
    pool = list(range(1, last_idx + 1))     # the first session has no previous session, so no predictors
    rng2 = np.random.default_rng(CONTROL_SEED)
    perm = derangement(len(pool), rng2)
    Xn = ds.X.copy()
    for a, b in zip(pool, perm):
        Xn[a] = ds.X[pool[int(b)]]
    out["negative"]["deranged_sessions"] = len(pool)
    for h in HORIZONS:
        alpha, curve, dec, facts = run_pipeline(ds, h, Y[h], Xn)
        trades, decisions, targets = score_decisions(ds, dec, Y[h], sample)
        res = judge(trades, sample)
        res["alpha"] = alpha
        res["forecast_stats"] = forecast_stats([x[2] for x in decisions], [targets[(x[0], x[1])] for x in decisions])
        out["negative"][h] = res
    st0["controls"] = out
    pos_ok = all(out["positive"][h]["passes"] for h in HORIZONS)
    neg_ok = not any(out["negative"][h]["passes"] for h in HORIZONS)
    if not (pos_ok and neg_ok):
        raise Halt("controls: positive passes %s, negative passes %s"
                   % ({h: out["positive"][h]["passes"] for h in HORIZONS},
                      {h: out["negative"][h]["passes"] for h in HORIZONS}))


def feasibility(ds, st0, Y, alphas):
    """Information: the real forecast's size on the scoring grid over 2025-03..2025-08, from
    models trained before each month. No realised return is compared with it."""
    np = _np()
    out = {}
    for h in HORIZONS:
        dec, facts, _m = walk_forward(ds, h, alphas[h], Y[h], FIRST_MONTH, PSEUDO_OOS_END[:7])
        f = np.array([x[2] for x in dec])
        share = float((np.abs(f) > COST_BP).mean())
        out[h] = {"decisions": len(f), "abs_forecast_bp_pct": {q: float(np.percentile(np.abs(f), q))
                                                              for q in (50, 90, 99, 100)},
                  "forecast_sd_bp": float(f.std()), "forecast_mean_bp": float(f.mean()),
                  "share_above_cost": share,
                  "expected_trades_in_78_sessions": share * 78 * len(GRID[h]),
                  "refits": facts}
    st0["feasibility_information"] = out


# ---- run records ---------------------------------------------------------------------------------

def _git(*args):
    try:
        return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


def environment():
    np = _np()
    import pandas as pd
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "machine": platform.platform(), "git_head": _git("rev-parse", "HEAD"),
            "data_dir": DATA, "kite_db": KITE_DB, "index_db": INDEX_DB}


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=_json_default)
    os.replace(tmp, path)


def _json_default(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def cost_record():
    return {"round_trip_bp": COST_BP, "charges_bp": round_trip_bp(dict(FUTURES_COSTS, slippage_pct=0.0)),
            "slippage_bp_per_leg": FUTURES_COSTS["slippage_pct"] * 100, "notional": NOTIONAL,
            "tariff": FUTURES_COSTS, "source": "zerodha.com/charges, equity futures, read 2026-09-30",
            "round_trip_bp_2025_tariff": COST_BP_2025, "tariff_2025": FUTURES_COSTS_2025}


def load_all():
    ds = Dataset().load()
    ds.choose_sessions()
    ds.build_factors()
    ds.build_predictors()
    return ds


def stage0(args):
    np = _np()
    st0 = {"look": "L51", "prereg": PREREG, "prereg_commit": PREREG_COMMIT, "mode": "stage0",
           "started": datetime.now().isoformat(), "argv": sys.argv[1:], "environment": environment(),
           "cost": cost_record(), "factors": None, "status": "RUNNING"}
    rng = np.random.default_rng(CONTROL_SEED)
    try:
        ds = load_all()
        st0["data"] = dict(ds.info)
        st0["predictors"] = {"count": len(PREDICTORS), "factors": FACTORS, "lags": LAGS}
        st0["grid"] = {h: [bar_close_hhmm(i) for i in GRID[h]] for h in HORIZONS}
        st0["training_bars"] = {h: [bar_close_hhmm(train_bars(kb)[0]), bar_close_hhmm(train_bars(kb)[-1]),
                                    len(train_bars(kb))] for h, kb in HORIZONS.items()}
        scoring = check_coverage(ds, st0)
        check_alignment(ds, st0)
        check_characteristics(ds, st0, rng)
        check_factors(ds, st0, rng)
        check_lookahead(ds, st0, rng, scoring)
        Y = ds.build_targets(before=SCORING_START)
        alphas, cv = {}, {}
        for h in HORIZONS:
            a, curve, folds = choose_alpha(ds, h, Y[h])
            alphas[h] = a
            cv[h] = {"alpha": a, "curve": [{"alpha": x, "mse": m} for x, m in curve], "folds": folds}
        st0["alpha"] = cv
        check_purge(ds, st0)
        check_controls(ds, st0, Y)
        feasibility(ds, st0, Y, alphas)
        st0["targets_computed_through"] = max(d for s, d in enumerate(ds.sessions)
                                              if np.isfinite(Y["h30"][s]).any())
        st0["status"] = "STAGE0_DONE"
    except Halt as e:
        st0["status"] = "HALTED"
        st0["halted_at"] = str(e)
    st0["finished"] = datetime.now().isoformat()
    _write(STAGE0_OUT, st0)
    print("stage 0:", st0["status"], st0.get("halted_at", ""))
    return st0


# ---- the one scoring pass -------------------------------------------------------------------------

def scoring_refusals(go, rescore_reason=None, stage0_path=STAGE0_OUT, result_path=RESULT_OUT):
    """Reasons the scoring pass must not start (prereg §10); empty when it may."""
    why = []
    if not go:
        why.append("no --go: the main session's go-ahead is required")
    if not os.path.exists(stage0_path):
        why.append("no stage 0 record")
    else:
        with open(stage0_path) as f:
            s0 = json.load(f)
        if s0.get("status") != "STAGE0_DONE" or s0.get("halted_at"):
            why.append("stage 0 status is %s" % s0.get("status"))
        rel = os.path.relpath(stage0_path, REPO)
        tracked = _git("ls-files", "--error-unmatch", rel)
        dirty = _git("status", "--porcelain", "--", rel)
        if not tracked or dirty:
            why.append("stage 0 record is not committed as is")
    if os.path.exists(result_path) and not rescore_reason:
        why.append("%s exists: the scoring pass runs once" % os.path.basename(result_path))
    return why


def score(args):
    np = _np()
    why = scoring_refusals(args.go, args.owner_approved_rescore)
    if why:
        print("REFUSED:", "; ".join(why))
        sys.exit(3)
    with open(STAGE0_OUT) as f:
        s0 = json.load(f)
    s0_hash = hashlib.sha256(open(STAGE0_OUT, "rb").read()).hexdigest()
    rec = {"look": "L51", "prereg": PREREG, "mode": "score", "status": "STARTED", "go": args.go,
           "owner_approved_rescore": args.owner_approved_rescore, "started": datetime.now().isoformat(),
           "environment": environment(), "stage0_sha256": s0_hash, "cost": cost_record()}
    _write(RESULT_OUT, rec)
    ds = load_all()
    scoring = [d for d in k.selection_sessions(ds.all_dates) if d in set(ds.sessions)]
    assert len(scoring) == s0["coverage"]["scoring_sessions"]
    Y = ds.build_targets(before=None)
    result = {"scoring_sample": [scoring[0], scoring[-1], len(scoring)]}
    for h in HORIZONS:
        a, _curve, _folds = choose_alpha(ds, h, Y[h])
        assert a == s0["alpha"][h]["alpha"], "the α differs from stage 0's"
        dec, facts, models = walk_forward(ds, h, a, Y[h], keep_models=True)
        trades, decisions, targets = score_decisions(ds, dec, Y[h], scoring)
        res = judge(trades, scoring)
        f = [x[2] for x in decisions]
        r = [targets[(x[0], x[1])] for x in decisions]
        res["forecast_stats"] = forecast_stats(f, r)
        by_time = defaultdict(lambda: {"trades": 0, "net_sum": 0.0})
        by_side = defaultdict(lambda: {"trades": 0, "net_sum": 0.0})
        for t in trades:
            by_time[bar_close_hhmm(t["bar"])]["trades"] += 1
            by_time[bar_close_hhmm(t["bar"])]["net_sum"] += t["net"]
            by_side["long" if t["side"] > 0 else "short"]["trades"] += 1
            by_side["long" if t["side"] > 0 else "short"]["net_sum"] += t["net"]
        res["by_decision_time"] = dict(by_time)
        res["by_side"] = dict(by_side)
        res["net_at_2025_tariff_bp_per_trade"] = (st.mean([t["gross"] - COST_BP_2025 for t in trades])
                                                  if trades else None)
        pseudo = pseudo_sessions(ds)
        tr_p, dec_p, tg_p = score_decisions(ds, dec, Y[h], pseudo)
        res["pseudo_oos_information"] = {"judge": judge(tr_p, pseudo),
                                         "forecast_stats": forecast_stats([x[2] for x in dec_p],
                                                                          [tg_p[(x[0], x[1])] for x in dec_p])}
        dm = models.get(LAST_MONTH)
        if dm is not None:
            order = np.argsort(-np.abs(dm["b"]))[:10]
            res["december_top_coefficients"] = [{"predictor": PREDICTORS[j], "coef_bp_per_sd": float(dm["b"][j])}
                                                for j in order]
        res["alpha"] = a
        res["refits"] = facts
        result[h] = res
    result["l51_clears"] = any(result[h]["passes"] for h in HORIZONS)
    rec.update({"status": "DONE", "finished": datetime.now().isoformat(), "result": result})
    _write(RESULT_OUT, rec)
    for h in HORIZONS:
        r_ = result[h]
        print("%s: trades %d, net %s bp/trade, t %s, halves %s / %s, DSR %s, IC %s -> passes %s"
              % (h, r_["trades"], r_["mean_net_bp_per_trade"], r_["t"], r_["half1_bp"], r_["half2_bp"], r_["dsr"],
                 r_["forecast_stats"].get("ic"), r_["passes"]))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--stage0", action="store_true")
    g.add_argument("--score", action="store_true")
    ap.add_argument("--go", default=None, help="who gave the go-ahead for the scoring pass, and when")
    ap.add_argument("--owner-approved-rescore", default=None)
    args = ap.parse_args(argv)
    if args.stage0:
        stage0(args)
    else:
        score(args)


if __name__ == "__main__":
    main()
