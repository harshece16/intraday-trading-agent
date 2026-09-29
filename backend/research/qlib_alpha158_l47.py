"""Research look L47 — does a LightGBM model on Qlib's Alpha158 factors, trained on the
project's own five-minute bars, rank the next intraday move?

Pre-registered: docs/research/prereg-qlib-lgbm-alpha158.md (commit dbdf872), approved as
decision D2b (docs/research/decisions/log-2026-09-30.md), both before this file was
written. This module implements that text and nothing else.

Three commands, run on the PC only (D2b: the Mac does not compute L47), from backend/:

    python -m research.qlib_alpha158_l47 stage0   # prereg §6: seven checks, each a halt
    python -m research.qlib_alpha158_l47 train    # §3-§4 and §7: once; models + normaliser hashed
    python -m research.qlib_alpha158_l47 score    # §5: once, on L40's 43,362 stock-times

KRONOS_CANDLE_DB overrides the candle cache path, as in L46.

The feature port. Qlib's Alpha158 (qlib/contrib/data/loader.py, Alpha158DL's default
config, Qlib commit QLIB_COMMIT) is ported expression by expression, with Qlib's operator
semantics from qlib/data/ops.py and qlib/data/_libs/rolling.pyx at the same commit:

  * every rolling operator uses min_periods=1: at the start of a series the window holds
    only the bars that exist, and NaN values inside a window are skipped;
  * Std has ddof=1 (pandas' default); Rank is pandas' rolling rank(pct=True), average
    ties; Quantile interpolates linearly; IdxMax/IdxMin are numpy's argmax/argmin + 1 on
    the window (1 = the oldest bar), first occurrence;
  * Slope/Rsquare/Resi regress the window's values on its slot positions 1..N (NaN
    slots skipped, positions kept), Resi being the last value's residual; Rsquare and
    Corr are set to NaN where the rolling std of an input is within 2e-5 of 0.

Where Qlib calls pandas' online rolling algorithms (Mean, Sum, Std, Corr) or its Cython
incremental sums (Slope, Rsquare, Resi), this port computes each window directly, in a
fixed order, from that window's values. The quantity is the same; the floating-point
error is not: the online algorithms carry drift from the start of the series (a direct
recomputation differs from pandas' rolling corr by up to 1e-5 on close-price windows),
which the prereg's 1e-9 hand-calculation check (§6.3) could not pass. Rolling Max, Min,
Quantile and Rank are exact order statistics and use pandas' own calls.

Nothing in the live path imports this (tests/test_research_splits.py). numpy, pandas and
lightgbm are imported inside functions only.
"""
import argparse
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
import traceback
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPO = os.path.dirname(BACKEND)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from research import kronos_feature_ic as k  # noqa: E402
from research import splits  # noqa: E402

# ---- the pre-registration's constants, named once -----------------------------------

PREREG = "docs/research/prereg-qlib-lgbm-alpha158.md"
QLIB_COMMIT = "be725493eb1a6bbb42bf11b37aa7669f59610ff1"
IST = timezone(timedelta(hours=5, minutes=30))

TRAIN_START = "2024-09-20"            # §3: sessions 2024-09-20 .. 2025-08-14
VAL_END = "2025-08-14"
VAL_SESSIONS = 40                     # §3: validation = the last 40 sessions to VAL_END
PURGE_SESSIONS = 5                    # §3: a 5-session purge between training and validation
MIN_GAP_TO_L40 = 5                    # §6.4: last label end >= 5 sessions before L40's first
FIRST_CLOSE, LAST_CLOSE = "09:45", "13:30"   # §3: every closed bar whose close is 09:45-13:30
READ_BEFORE = splits.HELD_OUT_START   # §3: the 2026 window is not read
READ_BEFORE_TS = int(datetime(2026, 1, 2, tzinfo=IST).timestamp())
# train reads nothing after the validation window: bars before 2025-08-15 00:00 IST
TRAIN_READ_BEFORE_TS = int(datetime(2025, 8, 15, tzinfo=IST).timestamp())

HORIZONS = k.HORIZONS                 # f15/f30/f60 -> k = 3/6/12 bars
N_FEATURES = 157                      # Alpha158's 158 minus VWAP0
EPS = 1e-12                           # qlib/constant.py
MAD_SCALE = 1.4826                    # RobustZScoreNorm
CLIP = 3.0
CS_RANK_SCALE = 3.46                  # CSRankNorm
CORR_STD_ATOL = 2e-05                 # ops.py: Rsquare and Corr masks

L40_SESSIONS_WITH_DATA = 78           # §5, §6.6
L40_STOCK_TIMES = 43362
LOOKAHEAD_PER_SEGMENT = 80            # §6.2: >= 200 across training, validation and test
HAND_TOL = 1e-9                       # §6.3
N_TESTS_NIGHT = 24                    # §5: L40 3 + L46 18 + L47 3
SEED = 123
CUTOFF = datetime(2026, 9, 30, 7, 30, tzinfo=IST)   # §7

# §4, verbatim from examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml and
# qlib/contrib/model/gbdt.py (objective from `loss`, verbosity -1), except num_threads,
# which the prereg fixes at 16, and the three it adds: CPU, deterministic, seed 123.
LGB_PARAMS = OrderedDict([
    ("objective", "mse"), ("verbosity", -1),
    ("colsample_bytree", 0.8879), ("learning_rate", 0.2), ("subsample", 0.8789),
    ("lambda_l1", 205.6999), ("lambda_l2", 580.9768), ("max_depth", 8), ("num_leaves", 210),
    ("num_threads", 16), ("device_type", "cpu"), ("deterministic", True), ("seed", SEED),
])
NUM_BOOST_ROUND = 1000
EARLY_STOPPING_ROUNDS = 50

OUT_DIR = os.path.join(REPO, "docs", "research", "data")
STAGE0 = os.path.join(OUT_DIR, "l47_stage0.json")
FROZEN = os.path.join(OUT_DIR, "l47_frozen.json")
RESULT = os.path.join(OUT_DIR, "l47_result.json")
L40_RESULT = os.path.join(OUT_DIR, "kronos_l40_result.json")
MODELS_DIR = os.path.join(HERE, "l47_models")
ROWS = os.path.join(HERE, "l47_rows.jsonl")
NORMALISER_FILE = "normaliser.json"


def model_file(name):
    return "lgbm_%s.txt" % name


# ---- Alpha158's feature list (loader.py, default config, VWAP0 dropped) --------------

WINDOWS = (5, 10, 20, 30, 60)
KBAR = OrderedDict([
    ("KMID", "($close-$open)/$open"),
    ("KLEN", "($high-$low)/$open"),
    ("KMID2", "($close-$open)/($high-$low+1e-12)"),
    ("KUP", "($high-Greater($open, $close))/$open"),
    ("KUP2", "($high-Greater($open, $close))/($high-$low+1e-12)"),
    ("KLOW", "(Less($open, $close)-$low)/$open"),
    ("KLOW2", "(Less($open, $close)-$low)/($high-$low+1e-12)"),
    ("KSFT", "(2*$close-$high-$low)/$open"),
    ("KSFT2", "(2*$close-$high-$low)/($high-$low+1e-12)"),
])
PRICE = OrderedDict([("OPEN0", "$open/$close"), ("HIGH0", "$high/$close"), ("LOW0", "$low/$close")])
DROPPED = OrderedDict([("VWAP0", "$vwap/$close")])   # Kite's five-minute bars carry no VWAP
ROLLING = OrderedDict([
    ("ROC", "Ref($close, {d})/$close"),
    ("MA", "Mean($close, {d})/$close"),
    ("STD", "Std($close, {d})/$close"),
    ("BETA", "Slope($close, {d})/$close"),
    ("RSQR", "Rsquare($close, {d})"),
    ("RESI", "Resi($close, {d})/$close"),
    ("MAX", "Max($high, {d})/$close"),
    ("MIN", "Min($low, {d})/$close"),
    ("QTLU", "Quantile($close, {d}, 0.8)/$close"),
    ("QTLD", "Quantile($close, {d}, 0.2)/$close"),
    ("RANK", "Rank($close, {d})"),
    ("RSV", "($close-Min($low, {d}))/(Max($high, {d})-Min($low, {d})+1e-12)"),
    ("IMAX", "IdxMax($high, {d})/{d}"),
    ("IMIN", "IdxMin($low, {d})/{d}"),
    ("IMXD", "(IdxMax($high, {d})-IdxMin($low, {d}))/{d}"),
    ("CORR", "Corr($close, Log($volume+1), {d})"),
    ("CORD", "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), {d})"),
    ("CNTP", "Mean($close>Ref($close, 1), {d})"),
    ("CNTN", "Mean($close<Ref($close, 1), {d})"),
    ("CNTD", "Mean($close>Ref($close, 1), {d})-Mean($close<Ref($close, 1), {d})"),
    ("SUMP", "Sum(Greater($close-Ref($close, 1), 0), {d})/(Sum(Abs($close-Ref($close, 1)), {d})+1e-12)"),
    ("SUMN", "Sum(Greater(Ref($close, 1)-$close, 0), {d})/(Sum(Abs($close-Ref($close, 1)), {d})+1e-12)"),
    ("SUMD", "(Sum(Greater($close-Ref($close, 1), 0), {d})-Sum(Greater(Ref($close, 1)-$close, 0), {d}))"
             "/(Sum(Abs($close-Ref($close, 1)), {d})+1e-12)"),
    ("VMA", "Mean($volume, {d})/($volume+1e-12)"),
    ("VSTD", "Std($volume, {d})/($volume+1e-12)"),
    ("WVMA", "Std(Abs($close/Ref($close, 1)-1)*$volume, {d})/(Mean(Abs($close/Ref($close, 1)-1)*$volume, {d})+1e-12)"),
    ("VSUMP", "Sum(Greater($volume-Ref($volume, 1), 0), {d})/(Sum(Abs($volume-Ref($volume, 1)), {d})+1e-12)"),
    ("VSUMN", "Sum(Greater(Ref($volume, 1)-$volume, 0), {d})/(Sum(Abs($volume-Ref($volume, 1)), {d})+1e-12)"),
    ("VSUMD", "(Sum(Greater($volume-Ref($volume, 1), 0), {d})-Sum(Greater(Ref($volume, 1)-$volume, 0), {d}))"
              "/(Sum(Abs($volume-Ref($volume, 1)), {d})+1e-12)"),
])
# §6.3's operator families, as the prereg groups them
FAMILIES = [["KMID", "KLEN", "KMID2", "KUP", "KUP2", "KLOW", "KLOW2", "KSFT", "KSFT2"], ["OPEN", "HIGH", "LOW"],
            ["ROC"], ["MA"], ["STD"], ["BETA", "RSQR", "RESI"], ["MAX", "MIN", "QTLU", "QTLD"], ["RANK", "RSV"],
            ["IMAX", "IMIN", "IMXD"], ["CORR", "CORD"], ["CNTP", "CNTN", "CNTD"], ["SUMP", "SUMN", "SUMD"],
            ["VMA", "VSTD", "WVMA"], ["VSUMP", "VSUMN", "VSUMD"]]


def qlib_expressions():
    """name -> Qlib expression, in Qlib's column order (the order LightGBM sees)."""
    out = OrderedDict(KBAR)
    out.update(PRICE)
    for op, tpl in ROLLING.items():
        for d in WINDOWS:
            out["%s%d" % (op, d)] = tpl.format(d=d)
    return out


FEATURE_NAMES = list(qlib_expressions())


# ---- rolling primitives (numpy/pandas, imported lazily) --------------------------------

def _np():
    import numpy as np
    return np


def _shift(x, d):
    """Qlib's Ref(x, d), d > 0: the value d bars earlier, NaN before the series starts."""
    np = _np()
    out = np.full(len(x), np.nan)
    if d < len(x):
        out[d:] = x[: len(x) - d]
    return out


def _columns(x, n):
    """The window's n columns, oldest first: column j holds x[t-n+1+j] at row t, NaN where
    that bar precedes the series. Row t depends on x[t-n+1..t] only."""
    np = _np()
    p = np.concatenate([np.full(n - 1, np.nan), np.asarray(x, dtype="float64")])
    T = len(x)
    return [p[j: j + T] for j in range(n)]


def rolling_sum(x, n):
    """Sum over the window's non-NaN values (NaN if there are none); and their count."""
    np = _np()
    cols = _columns(x, n)
    s = np.zeros(len(x))
    cnt = np.zeros(len(x))
    for c in cols:
        ok = ~np.isnan(c)
        s += np.where(ok, c, 0.0)
        cnt += ok
    s[cnt == 0] = np.nan
    return s, cnt


def rolling_mean(x, n):
    s, cnt = rolling_sum(x, n)
    with _np().errstate(invalid="ignore", divide="ignore"):
        return s / cnt


def rolling_std(x, n):
    """Sample standard deviation (ddof=1) of the window's non-NaN values; NaN below two."""
    np = _np()
    m = rolling_mean(x, n)
    cols = _columns(x, n)
    ss = np.zeros(len(x))
    cnt = np.zeros(len(x))
    with np.errstate(invalid="ignore", over="ignore"):
        for c in cols:
            ok = ~np.isnan(c)
            ss += np.where(ok, (c - m) ** 2, 0.0)
            cnt += ok
        var = ss / (cnt - 1)
    var[cnt < 2] = np.nan
    return np.sqrt(var)


def rolling_corr(x, y, n):
    """Qlib's Corr: Pearson over the window's pairs where both are present (pandas'
    prep_binary), NaN below two pairs, and NaN where either input's rolling std is within
    2e-5 of 0 (ops.py Corr._load_internal)."""
    np = _np()
    cx, cy = _columns(x, n), _columns(y, n)
    oks = [~np.isnan(a) & ~np.isnan(b) for a, b in zip(cx, cy)]
    T = len(x)
    cnt, sx, sy = np.zeros(T), np.zeros(T), np.zeros(T)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        for a, b, ok in zip(cx, cy, oks):
            cnt += ok
            sx += np.where(ok, a, 0.0)
            sy += np.where(ok, b, 0.0)
        mx, my = sx / cnt, sy / cnt
        sxy, sxx, syy = np.zeros(T), np.zeros(T), np.zeros(T)
        for a, b, ok in zip(cx, cy, oks):
            da, db = a - mx, b - my
            sxy += np.where(ok, da * db, 0.0)
            sxx += np.where(ok, da * da, 0.0)
            syy += np.where(ok, db * db, 0.0)
        r = sxy / np.sqrt(sxx * syy)
    r[cnt < 2] = np.nan
    mask = np.isclose(rolling_std(x, n), 0, atol=CORR_STD_ATOL) | np.isclose(rolling_std(y, n), 0, atol=CORR_STD_ATOL)
    r[mask] = np.nan
    return r


def rolling_regression(y, n):
    """Qlib's Slope, Rsquare and Resi (rolling.pyx): least squares of the window's values on
    their slot positions 1..n, NaN slots skipped. Resi is the last value's residual, NaN
    if it is missing. Rsquare is NaN where the rolling std is within 2e-5 of 0."""
    np = _np()
    cols = _columns(y, n)
    T = len(y)
    oks = [~np.isnan(c) for c in cols]
    cnt, sx, sy = np.zeros(T), np.zeros(T), np.zeros(T)
    for j, (c, ok) in enumerate(zip(cols, oks)):
        cnt += ok
        sx += np.where(ok, float(j + 1), 0.0)
        sy += np.where(ok, c, 0.0)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        mx, my = sx / cnt, sy / cnt
        sxy, sxx, syy = np.zeros(T), np.zeros(T), np.zeros(T)
        for j, (c, ok) in enumerate(zip(cols, oks)):
            dx, dy = (j + 1) - mx, c - my
            sxy += np.where(ok, dx * dy, 0.0)
            sxx += np.where(ok, dx * dx, 0.0)
            syy += np.where(ok, dy * dy, 0.0)
        slope = sxy / sxx
        rsq = (sxy * sxy) / (sxx * syy)
        interp = my - slope * mx
        resi = cols[-1] - (slope * n + interp)
    rsq[np.isclose(rolling_std(y, n), 0, atol=CORR_STD_ATOL)] = np.nan
    return slope, rsq, resi


def rolling_argext(x, n, which):
    """Qlib's IdxMax/IdxMin: rolling(n, min_periods=1).apply(lambda w: w.argmax() + 1, raw=True).
    1 is the oldest bar of the window; a window shorter than n starts at the first bar."""
    np = _np()
    from numpy.lib.stride_tricks import sliding_window_view
    x = np.asarray(x, dtype="float64")
    f = np.argmax if which == "max" else np.argmin
    T = len(x)
    out = np.full(T, np.nan)
    for t in range(min(n - 1, T)):
        w = x[: t + 1]
        if not np.isnan(w).all():
            out[t] = f(w) + 1
    if T >= n:
        W = sliding_window_view(x, n)
        r = f(W, axis=1) + 1.0
        r[np.isnan(W).all(axis=1)] = np.nan
        out[n - 1:] = r
    return out


def _pd_rolling(x, n):
    import pandas as pd
    return pd.Series(x, dtype="float64").rolling(n, min_periods=1)


def rolling_max(x, n):
    return _pd_rolling(x, n).max().to_numpy()


def rolling_min(x, n):
    return _pd_rolling(x, n).min().to_numpy()


def rolling_quantile(x, n, q):
    return _pd_rolling(x, n).quantile(q, interpolation="linear").to_numpy()


def rolling_rank(x, n):
    return _pd_rolling(x, n).rank(method="average", ascending=True, pct=True).to_numpy()


# ---- the 157 features --------------------------------------------------------------------

def alpha158_matrix(o, h, l, c, v):
    """(T, 157) float64, columns in FEATURE_NAMES order; row t uses bars <= t only."""
    np = _np()
    o, h, l, c, v = (np.asarray(a, dtype="float64") for a in (o, h, l, c, v))
    f = OrderedDict()
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        hl = h - l + 1e-12
        f["KMID"] = (c - o) / o
        f["KLEN"] = (h - l) / o
        f["KMID2"] = (c - o) / hl
        f["KUP"] = (h - np.maximum(o, c)) / o
        f["KUP2"] = (h - np.maximum(o, c)) / hl
        f["KLOW"] = (np.minimum(o, c) - l) / o
        f["KLOW2"] = (np.minimum(o, c) - l) / hl
        f["KSFT"] = (2 * c - h - l) / o
        f["KSFT2"] = (2 * c - h - l) / hl
        f["OPEN0"] = o / c
        f["HIGH0"] = h / c
        f["LOW0"] = l / c

        c1, v1 = _shift(c, 1), _shift(v, 1)
        gain, loss, move = np.maximum(c - c1, 0), np.maximum(c1 - c, 0), np.abs(c - c1)
        vgain, vloss, vmove = np.maximum(v - v1, 0), np.maximum(v1 - v, 0), np.abs(v - v1)
        up = np.greater(c, c1).astype("float64")        # False where Ref is NaN, as numpy does
        down = np.less(c, c1).astype("float64")
        logv = np.log(v + 1)
        ret = c / c1
        logvr = np.log(v / v1 + 1)
        wv = np.abs(c / c1 - 1) * v
        vden = v + 1e-12

        per = defaultdict(OrderedDict)
        for d in WINDOWS:
            mx, mn = rolling_max(h, d), rolling_min(l, d)
            slope, rsq, resi = rolling_regression(c, d)
            imax, imin = rolling_argext(h, d, "max"), rolling_argext(l, d, "min")
            cntp, cntn = rolling_mean(up, d), rolling_mean(down, d)
            sg, sl, sm = rolling_sum(gain, d)[0], rolling_sum(loss, d)[0], rolling_sum(move, d)[0]
            vg, vl, vm = rolling_sum(vgain, d)[0], rolling_sum(vloss, d)[0], rolling_sum(vmove, d)[0]
            per["ROC"][d] = _shift(c, d) / c
            per["MA"][d] = rolling_mean(c, d) / c
            per["STD"][d] = rolling_std(c, d) / c
            per["BETA"][d] = slope / c
            per["RSQR"][d] = rsq
            per["RESI"][d] = resi / c
            per["MAX"][d] = mx / c
            per["MIN"][d] = mn / c
            per["QTLU"][d] = rolling_quantile(c, d, 0.8) / c
            per["QTLD"][d] = rolling_quantile(c, d, 0.2) / c
            per["RANK"][d] = rolling_rank(c, d)
            per["RSV"][d] = (c - mn) / (mx - mn + 1e-12)
            per["IMAX"][d] = imax / d
            per["IMIN"][d] = imin / d
            per["IMXD"][d] = (imax - imin) / d
            per["CORR"][d] = rolling_corr(c, logv, d)
            per["CORD"][d] = rolling_corr(ret, logvr, d)
            per["CNTP"][d] = cntp
            per["CNTN"][d] = cntn
            per["CNTD"][d] = cntp - cntn
            per["SUMP"][d] = sg / (sm + 1e-12)
            per["SUMN"][d] = sl / (sm + 1e-12)
            per["SUMD"][d] = (sg - sl) / (sm + 1e-12)
            per["VMA"][d] = rolling_mean(v, d) / vden
            per["VSTD"][d] = rolling_std(v, d) / vden
            per["WVMA"][d] = rolling_std(wv, d) / (rolling_mean(wv, d) + 1e-12)
            per["VSUMP"][d] = vg / (vm + 1e-12)
            per["VSUMN"][d] = vl / (vm + 1e-12)
            per["VSUMD"][d] = (vg - vl) / (vm + 1e-12)
        for op in ROLLING:
            for d in WINDOWS:
                f["%s%d" % (op, d)] = per[op][d]
    assert list(f) == FEATURE_NAMES
    return np.column_stack([f[n] for n in FEATURE_NAMES]) if len(c) else np.empty((0, N_FEATURES))


def alpha158_from_bars(bars):
    """The feature matrix for one symbol's bars (dicts in time order, as the cache loads them)."""
    np = _np()
    arr = np.array([[b["open"], b["high"], b["low"], b["close"], b["volume"]] for b in bars], dtype="float64")
    if not len(arr):
        return np.empty((0, N_FEATURES))
    return alpha158_matrix(arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3], arr[:, 4])


def alpha158_features(bars_df):
    """The 157 features at every closed bar of one symbol's continuous five-minute series.
    bars_df: columns open, high, low, close, volume, time, in time order. The row for bar t
    uses bars <= t only."""
    import pandas as pd
    times = list(bars_df["time"])
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("bars must be in strictly increasing time order")
    m = alpha158_matrix(bars_df["open"], bars_df["high"], bars_df["low"], bars_df["close"], bars_df["volume"])
    return pd.DataFrame(m, index=bars_df.index, columns=FEATURE_NAMES)


def canonical_bytes(a):
    """Bytes of a float64 array with every NaN in one canonical form (for bit comparisons)."""
    np = _np()
    a = np.asarray(a, dtype="float64")
    return np.where(np.isnan(a), np.nan, a).tobytes()


def feature_fingerprint():
    """SHA-256 of the features of a fixed synthetic series: train records it, score checks it,
    so the scoring pass cannot compute its features with different code."""
    rng = random.Random(SEED)
    bars, p = [], 1000.0
    for i in range(400):
        o = p
        p = max(1.0, p + rng.choice([-1, 0, 0, 1]) * 0.05 * rng.randint(0, 40))
        hi, lo = max(o, p) + 0.05 * rng.randint(0, 5), min(o, p) - 0.05 * rng.randint(0, 5)
        bars.append({"open": o, "high": hi, "low": lo, "close": p, "volume": float(rng.choice([0, 0, 1, 500, 12000, 80000]))})
    return hashlib.sha256(canonical_bytes(alpha158_from_bars(bars))).hexdigest()


# ---- the hand calculation (§6.3): pure Python, from the bars, no numpy or pandas -------

NAN = float("nan")


def _isnan(x):
    return x != x


def _div(a, b):
    """numpy's float division: x/0 is +-inf, 0/0 is NaN, NaN propagates."""
    if _isnan(a) or _isnan(b):
        return NAN
    if b == 0:
        if a == 0:
            return NAN
        return math.copysign(math.inf, a) * math.copysign(1.0, b)
    return a / b


def _log(x):
    if _isnan(x) or x < 0:
        return NAN
    if x == 0:
        return -math.inf
    if math.isinf(x):
        return math.inf
    return math.log(x)


def _greater0(x):
    return NAN if _isnan(x) else max(x, 0.0)


def _present(vals):
    return [x for x in vals if not _isnan(x)]


def _sum(vals):
    v = _present(vals)
    if not v:
        return NAN
    return math.fsum(v) if all(math.isfinite(x) for x in v) else sum(v)


def _mean(vals):
    v = _present(vals)
    return _sum(v) / len(v) if v else NAN


def _std(vals):
    v = _present(vals)
    if len(v) < 2:
        return NAN
    if not all(math.isfinite(x) for x in v):
        return NAN
    m = math.fsum(v) / len(v)
    return math.sqrt(math.fsum((x - m) ** 2 for x in v) / (len(v) - 1))


def _masked(sd):
    return (not _isnan(sd)) and abs(sd) <= CORR_STD_ATOL


def _pearson(xs, ys):
    pairs = [(a, b) for a, b in zip(xs, ys) if not _isnan(a) and not _isnan(b)]
    if _masked(_std(xs)) or _masked(_std(ys)) or len(pairs) < 2:
        return NAN
    if not all(math.isfinite(a) and math.isfinite(b) for a, b in pairs):
        return NAN
    ma = math.fsum(a for a, _ in pairs) / len(pairs)
    mb = math.fsum(b for _, b in pairs) / len(pairs)
    sab = math.fsum((a - ma) * (b - mb) for a, b in pairs)
    saa = math.fsum((a - ma) ** 2 for a, _ in pairs)
    sbb = math.fsum((b - mb) ** 2 for _, b in pairs)
    return _div(sab, math.sqrt(saa * sbb))


def _regression(vals, n):
    """(slope, r^2, residual of the last value) on slot positions; vals is the window,
    oldest first, len(vals) <= n, the last value in slot n."""
    pts = [(n - len(vals) + 1 + j, y) for j, y in enumerate(vals) if not _isnan(y)]
    if len(pts) < 2:
        return NAN, NAN, NAN
    mx = math.fsum(p for p, _ in pts) / len(pts)
    my = math.fsum(y for _, y in pts) / len(pts)
    sxy = math.fsum((p - mx) * (y - my) for p, y in pts)
    sxx = math.fsum((p - mx) ** 2 for p, _ in pts)
    syy = math.fsum((y - my) ** 2 for _, y in pts)
    slope = sxy / sxx
    rsq = NAN if _masked(_std(vals)) else _div(sxy * sxy, sxx * syy)
    last = vals[-1]
    resi = NAN if _isnan(last) else last - (slope * n + (my - slope * mx))
    return slope, rsq, resi


def _quantile(vals, q):
    s = sorted(_present(vals))
    if not s:
        return NAN
    pos = q * (len(s) - 1)
    lo = int(math.floor(pos))
    if pos == lo:
        return s[lo]
    return s[lo] + (s[lo + 1] - s[lo]) * (pos - lo)


def _pct_rank(vals):
    v = _present(vals)
    x = vals[-1]
    if not v or _isnan(x):
        return NAN
    less = sum(1 for y in v if y < x)
    eq = sum(1 for y in v if y == x)
    return (less + (eq + 1) / 2.0) / len(v)


def _first_arg(vals, best):
    if all(_isnan(x) for x in vals):
        return NAN
    for j, x in enumerate(vals):
        if _isnan(x):
            return float(j + 1)          # numpy's argmax/argmin stop at the first NaN
    target = best(vals)
    return float(vals.index(target) + 1)


def hand_features(bars, t):
    """All 157 features at bar t, computed directly from the bar dicts by each expression's
    definition. Independent of the vectorised port above."""
    O = [float(b["open"]) for b in bars[: t + 1]]
    H = [float(b["high"]) for b in bars[: t + 1]]
    L = [float(b["low"]) for b in bars[: t + 1]]
    C = [float(b["close"]) for b in bars[: t + 1]]
    V = [float(b["volume"]) for b in bars[: t + 1]]
    o, h, l, c, v = O[t], H[t], L[t], C[t], V[t]

    def ref(series, j, d):
        return series[j - d] if j - d >= 0 else NAN

    def win(series, n):
        return [series[j] for j in range(max(0, t - n + 1), t + 1)]

    def derived(fn, n):
        return [fn(j) for j in range(max(0, t - n + 1), t + 1)]

    out = OrderedDict()
    hl = h - l + 1e-12
    out["KMID"] = (c - o) / o
    out["KLEN"] = (h - l) / o
    out["KMID2"] = (c - o) / hl
    out["KUP"] = (h - max(o, c)) / o
    out["KUP2"] = (h - max(o, c)) / hl
    out["KLOW"] = (min(o, c) - l) / o
    out["KLOW2"] = (min(o, c) - l) / hl
    out["KSFT"] = (2 * c - h - l) / o
    out["KSFT2"] = (2 * c - h - l) / hl
    out["OPEN0"], out["HIGH0"], out["LOW0"] = o / c, h / c, l / c

    gain = lambda j: _greater0(C[j] - ref(C, j, 1))           # noqa: E731
    loss = lambda j: _greater0(ref(C, j, 1) - C[j])           # noqa: E731
    move = lambda j: abs(C[j] - ref(C, j, 1))                 # noqa: E731
    vgain = lambda j: _greater0(V[j] - ref(V, j, 1))          # noqa: E731
    vloss = lambda j: _greater0(ref(V, j, 1) - V[j])          # noqa: E731
    vmove = lambda j: abs(V[j] - ref(V, j, 1))                # noqa: E731
    up = lambda j: 1.0 if (not _isnan(ref(C, j, 1)) and C[j] > ref(C, j, 1)) else 0.0    # noqa: E731
    down = lambda j: 1.0 if (not _isnan(ref(C, j, 1)) and C[j] < ref(C, j, 1)) else 0.0  # noqa: E731
    wv = lambda j: abs(_div(C[j], ref(C, j, 1)) - 1) * V[j]   # noqa: E731

    per = defaultdict(OrderedDict)
    for d in WINDOWS:
        cw, hw, lw = win(C, d), win(H, d), win(L, d)
        mx, mn = max(hw), min(lw)
        slope, rsq, resi = _regression(cw, d)
        imax, imin = _first_arg(hw, max), _first_arg(lw, min)
        cntp, cntn = _mean(derived(up, d)), _mean(derived(down, d))
        sg, sl, sm = _sum(derived(gain, d)), _sum(derived(loss, d)), _sum(derived(move, d))
        vg, vl, vm = _sum(derived(vgain, d)), _sum(derived(vloss, d)), _sum(derived(vmove, d))
        per["ROC"][d] = _div(ref(C, t, d), c)
        per["MA"][d] = _mean(cw) / c
        per["STD"][d] = _std(cw) / c
        per["BETA"][d] = slope / c
        per["RSQR"][d] = rsq
        per["RESI"][d] = resi / c
        per["MAX"][d] = mx / c
        per["MIN"][d] = mn / c
        per["QTLU"][d] = _quantile(cw, 0.8) / c
        per["QTLD"][d] = _quantile(cw, 0.2) / c
        per["RANK"][d] = _pct_rank(cw)
        per["RSV"][d] = _div(c - mn, mx - mn + 1e-12)
        per["IMAX"][d] = imax / d
        per["IMIN"][d] = imin / d
        per["IMXD"][d] = (imax - imin) / d
        per["CORR"][d] = _pearson(cw, [_log(x + 1) for x in win(V, d)])
        per["CORD"][d] = _pearson(derived(lambda j: _div(C[j], ref(C, j, 1)), d),
                                  derived(lambda j: _log(_div(V[j], ref(V, j, 1)) + 1), d))
        per["CNTP"][d] = cntp
        per["CNTN"][d] = cntn
        per["CNTD"][d] = cntp - cntn
        per["SUMP"][d] = _div(sg, sm + 1e-12)
        per["SUMN"][d] = _div(sl, sm + 1e-12)
        per["SUMD"][d] = _div(sg - sl, sm + 1e-12)
        per["VMA"][d] = _div(_mean(win(V, d)), v + 1e-12)
        per["VSTD"][d] = _div(_std(win(V, d)), v + 1e-12)
        wvs = derived(wv, d)
        per["WVMA"][d] = _div(_std(wvs), _mean(wvs) + 1e-12)
        per["VSUMP"][d] = _div(vg, vm + 1e-12)
        per["VSUMN"][d] = _div(vl, vm + 1e-12)
        per["VSUMD"][d] = _div(vg - vl, vm + 1e-12)
    for op in ROLLING:
        for d in WINDOWS:
            out["%s%d" % (op, d)] = per[op][d]
    return out


def close_enough(a, b, tol=HAND_TOL):
    """|a - b| <= tol, relative once |b| > 1; NaN matches NaN, inf matches the same inf."""
    a, b = float(a), float(b)
    if _isnan(a) or _isnan(b):
        return _isnan(a) and _isnan(b)
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= tol * max(1.0, abs(b))


# ---- data: the loader, sessions, the split, the rows (§3) -------------------------------

def _ist_iso(ts):
    return datetime.fromtimestamp(ts, IST).replace(tzinfo=None).isoformat()


class CutoffViolation(AssertionError):
    """The loader returned a bar at or after its cut-off."""


def load_bars(kite_history, symbols, before_ts=READ_BEFORE_TS):
    """{symbol: [bars oldest first]} with every bar's timestamp < before_ts, and the latest
    timestamp read. The filter is in the query, so nothing later is ever read."""
    conn = kite_history._conn()
    out, max_ts = {}, None
    for s in symbols:
        rows = conn.execute("SELECT ts, open, high, low, close, volume FROM candles "
                            "WHERE symbol=? AND interval='5m' AND ts < ? ORDER BY ts ASC", (s, before_ts)).fetchall()
        if not rows:
            continue
        out[s] = [{"time": _ist_iso(r[0]), "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
                  for r in rows]
        last = rows[-1][0]
        max_ts = last if max_ts is None else max(max_ts, last)
    if max_ts is not None and max_ts >= before_ts:
        raise CutoffViolation("read a bar at or after the cut-off: %s" % _ist_iso(max_ts))
    return out, max_ts


def split_sessions(cache_sessions, start=TRAIN_START, end=VAL_END, n_val=VAL_SESSIONS, purge=PURGE_SESSIONS):
    """§3: training | purge | validation over the cache's sessions in [start, end]."""
    window = [s for s in sorted(set(cache_sessions)) if start <= s <= end]
    if len(window) < n_val + purge + 1:
        raise ValueError("only %d sessions in %s..%s" % (len(window), start, end))
    return {"window": window, "train": window[: -(n_val + purge)],
            "purge": window[-(n_val + purge): -n_val], "validation": window[-n_val:]}


def sessions_between(sessions, a, b):
    """Sessions strictly after a and strictly before b."""
    return [s for s in sessions if a < s < b]


def train_bar_starts(first=FIRST_CLOSE, last=LAST_CLOSE):
    """{bar start hh:mm: its close hh:mm} for every bar whose close is in [first, last]."""
    out = OrderedDict()
    t = datetime.strptime(first, "%H:%M")
    end = datetime.strptime(last, "%H:%M")
    while t <= end:
        out[(t - timedelta(minutes=k.BAR_MINUTES)).strftime("%H:%M")] = t.strftime("%H:%M")
        t += timedelta(minutes=k.BAR_MINUTES)
    return out


def training_stock_times(flat_by_sym, sessions_by_sym, dates, members_by_date, dropped):
    """§3's rows: [(sym, date, close hh:mm, flat index, index in the session)] for every
    point-in-time member and every closed bar whose close is 09:45-13:30 on `dates`,
    ordered by (date, time, symbol) as Qlib orders its index."""
    starts = train_bar_starts()
    keep = set(dates)
    out = []
    for sym, flat in flat_by_sym.items():
        pos = None
        for d in dates:
            if sym not in members_by_date[d] or d in dropped.get(sym, []):
                continue
            bars = sessions_by_sym[sym].get(d)
            if not bars:
                continue
            if pos is None:
                pos = {c["time"]: i for i, c in enumerate(flat)}
            for i, b in enumerate(bars):
                hh = starts.get(b["time"][11:16])
                if hh is not None:
                    out.append((sym, d, hh, pos[b["time"]], i))
    assert all(r[1] in keep for r in out)
    out.sort(key=lambda r: (r[1], r[2], r[0]))
    return out


def labels(rows, sessions_by_sym):
    """{horizon: [target_bp or None]} and {horizon: [label end time or None]} for each row.
    None: the target would leave the session (the row is dropped for that horizon)."""
    ys = {name: [] for name in HORIZONS}
    ends = {name: [] for name in HORIZONS}
    for sym, d, _, _, i in rows:
        bars = sessions_by_sym[sym][d]
        for name, kk in HORIZONS.items():
            y = k.target_bp(bars, i, kk)
            ys[name].append(y)
            ends[name].append(bars[i + kk]["time"] if y is not None else None)
    return ys, ends


def feature_rows(flat_by_sym, requests):
    """Features for [(sym, flat index)], each symbol's series computed once, whole."""
    np = _np()
    X = np.empty((len(requests), N_FEATURES))
    by_sym = defaultdict(list)
    for r, (sym, idx) in enumerate(requests):
        by_sym[sym].append((r, idx))
    for sym in sorted(by_sym):
        F = alpha158_from_bars(flat_by_sym[sym])
        rs = [r for r, _ in by_sym[sym]]
        ids = [i for _, i in by_sym[sym]]
        X[rs] = F[ids]
    return X


# ---- normalisation and labels (§3) ---------------------------------------------------------

def fit_normaliser(X, dates, train_sessions):
    """Qlib's RobustZScoreNorm.fit, on training rows only: median, and MAD * 1.4826 (+EPS)."""
    np = _np()
    allowed = set(train_sessions)
    outside = sorted({d for d in dates if d not in allowed})
    if outside:
        raise AssertionError("normaliser fit offered rows outside training: %s" % outside[:5])
    if len(dates) != len(X):
        raise AssertionError("one date per row")
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        median = np.nanmedian(X, axis=0)
        std = np.nanmedian(np.abs(X - median), axis=0)
    std = std + EPS
    std = std * MAD_SCALE
    return {"median": [float(x) for x in median], "std": [float(x) for x in std],
            "fit_rows": int(len(X)), "fit_first": min(dates) if dates else None, "fit_last": max(dates) if dates else None}


def apply_normaliser(X, stats):
    """RobustZScoreNorm.__call__ (clip +-3) then Fillna(0), in place."""
    np = _np()
    X -= np.asarray(stats["median"], dtype="float64")
    X /= np.asarray(stats["std"], dtype="float64")
    np.clip(X, -CLIP, CLIP, out=X)
    X[np.isnan(X)] = 0.0
    return X


def same_stats(a, b):
    """Normaliser statistics equal, NaN matching NaN."""
    for key in ("median", "std"):
        if len(a[key]) != len(b[key]):
            return False
        for x, y in zip(a[key], b[key]):
            if not (x == y or (_isnan(x) and _isnan(y))):
                return False
    return True


def cs_rank_labels(values, keys):
    """Qlib's CSRankNorm: rank(pct=True) within each timestamp, minus 0.5, times 3.46."""
    import pandas as pd
    s = pd.Series(values, dtype="float64")
    r = s.groupby(pd.Series(list(keys))).rank(pct=True)
    r -= 0.5
    r *= CS_RANK_SCALE
    return r.to_numpy()


# ---- the model (§4) --------------------------------------------------------------------------

def train_one(X_tr, y_tr, X_va, y_va, feature_names=None, params=None):
    """Qlib's LGBModel.fit: lgb.train on train with [train, valid] as validation sets; early
    stopping skips the training set, so it watches validation l2."""
    import lightgbm as lgb
    p = dict(LGB_PARAMS if params is None else params)
    names = feature_names if feature_names is not None else "auto"
    dtr = lgb.Dataset(X_tr, label=y_tr, free_raw_data=False, feature_name=names)
    dva = lgb.Dataset(X_va, label=y_va, free_raw_data=False, feature_name=names)
    evals = {}
    booster = lgb.train(p, dtr, num_boost_round=NUM_BOOST_ROUND, valid_sets=[dtr, dva], valid_names=["train", "valid"],
                        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS), lgb.log_evaluation(period=20),
                                   lgb.record_evaluation(evals)])
    return booster, evals


def timestamp_rank_ic(pred, target, keys):
    """Mean over timestamps of the Spearman rank IC between prediction and raw target."""
    groups = defaultdict(lambda: ([], []))
    for p, y, key in zip(pred, target, keys):
        if y is None or _isnan(y):
            continue
        groups[key][0].append(float(p))
        groups[key][1].append(float(y))
    ics = [k.spearman(ps, ys) for ps, ys in (groups[g] for g in sorted(groups)) if len(ps) >= 3]
    ics = [x for x in ics if x is not None]
    m, t, se = k.tstat(ics)
    return {"timestamps": len(ics), "mean": m, "t": t, "se": se}


# ---- hashing, git, the environment ---------------------------------------------------------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_frozen_files():
    return [model_file(n) for n in HORIZONS] + [NORMALISER_FILE]


def verify_frozen(frozen_path=FROZEN, models_dir=MODELS_DIR):
    """The score pass's precondition: l47_frozen.json exists and every frozen file's SHA-256
    matches it. Returns the frozen record; raises RuntimeError otherwise."""
    if not os.path.exists(frozen_path):
        raise RuntimeError("no %s: train (and commit its record) before scoring" % frozen_path)
    with open(frozen_path) as f:
        frozen = json.load(f)
    files = frozen.get("files") or {}
    if sorted(files) != sorted(expected_frozen_files()):
        raise RuntimeError("the frozen record lists %s, expected %s" % (sorted(files), sorted(expected_frozen_files())))
    for name, want in files.items():
        path = os.path.join(models_dir, name)
        if not os.path.exists(path):
            raise RuntimeError("frozen file missing: %s" % path)
        got = sha256_file(path)
        if got != want:
            raise RuntimeError("hash mismatch for %s: file %s, frozen record %s" % (name, got, want))
    return frozen


def _git(*args):
    r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def committed_at_head(path):
    """True if `path` is tracked and identical to HEAD (the frozen hashes are committed)."""
    rel = os.path.relpath(path, REPO).replace(os.sep, "/")
    tracked, _ = _git("ls-files", "--error-unmatch", "--", rel)
    if tracked != 0:
        return False
    clean, _ = _git("diff", "--quiet", "HEAD", "--", rel)
    return clean == 0


def environment():
    out = {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
           "cpu_count": os.cpu_count()}
    for name in ("numpy", "pandas", "lightgbm", "scipy"):
        try:
            out[name] = __import__(name).__version__
        except Exception:
            out[name] = None
    rc, head = _git("rev-parse", "HEAD")
    out["git_head"] = head if rc == 0 else None
    rc, dirty = _git("status", "--porcelain", "--", os.path.relpath(__file__, REPO).replace(os.sep, "/"))
    out["module_dirty"] = bool(dirty) if rc == 0 else None
    out["module_sha256"] = sha256_file(__file__)
    return out


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=str)
    os.replace(tmp, path)


def _read(path):
    with open(path) as f:
        return json.load(f)


def guard_platform():
    """D2b: the Mac does not compute L47."""
    if sys.platform == "darwin" and os.environ.get("L47_ALLOW_MAC") != "1":
        raise SystemExit("L47 computes on the PC only (decision D2b). Refusing to run on this Mac.")


def _kite_history():
    import kite_history
    db = os.environ.get("KRONOS_CANDLE_DB")
    if db:
        from pathlib import Path
        kite_history.DB_PATH = Path(db)
    return kite_history


class Data(object):
    """What stage0 and train share: bars, sessions, the split, membership, drops, rows."""

    def __init__(self, kite_history, before_ts):
        self.membership_rows = k.load_membership_rows()
        symbols = sorted({r["symbol"] for r in self.membership_rows})
        pre, self.max_ts = load_bars(kite_history, symbols, before_ts)
        self.cache_sessions = splits.sessions_in(pre)
        self.split = split_sessions(self.cache_sessions)
        self.flat_by_sym = {s: sorted(c, key=lambda x: x["time"]) for s, c in pre.items()}
        self.sessions_by_sym = {s: k.by_session(c) for s, c in self.flat_by_sym.items()}
        upto = [s for s in self.cache_sessions if s <= VAL_END]
        dates = self.split["train"] + self.split["validation"]
        self.members_by_date = {d: k.membership_asof(self.membership_rows, d) for d in dates}
        adj = {}
        dropped = k.stage0_adjustment(adj, kite_history, list(self.flat_by_sym), upto)
        window = set(self.split["window"])
        self.dropped = {s: [d for d in v if d in window] for s, v in dropped.items()}
        self.dropped = {s: v for s, v in self.dropped.items() if v}
        self.adjustment = adj["adjustment"]
        self.adjustment["dropped_stock_sessions"] = self.dropped
        self.adjustment["dropped_count"] = sum(len(v) for v in self.dropped.values())
        self.rows_tr = training_stock_times(self.flat_by_sym, self.sessions_by_sym, self.split["train"],
                                            self.members_by_date, self.dropped)
        self.rows_va = training_stock_times(self.flat_by_sym, self.sessions_by_sym, self.split["validation"],
                                            self.members_by_date, self.dropped)
        self.y_tr, self.end_tr = labels(self.rows_tr, self.sessions_by_sym)
        self.y_va, self.end_va = labels(self.rows_va, self.sessions_by_sym)

    def describe(self):
        return {"max_ts_read": self.max_ts, "max_time_read_ist": _ist_iso(self.max_ts) if self.max_ts else None,
                "symbols_with_bars": len(self.flat_by_sym),
                "sessions": {"window": [self.split["window"][0], self.split["window"][-1], len(self.split["window"])],
                             "train": [self.split["train"][0], self.split["train"][-1], len(self.split["train"])],
                             "purge": self.split["purge"], "validation": [self.split["validation"][0],
                                                                          self.split["validation"][-1], len(self.split["validation"])]},
                "rows": {"train": len(self.rows_tr), "validation": len(self.rows_va),
                         "train_by_horizon": {n: sum(y is not None for y in self.y_tr[n]) for n in HORIZONS},
                         "validation_by_horizon": {n: sum(y is not None for y in self.y_va[n]) for n in HORIZONS}},
                "members_per_date": [min(len(v) for v in self.members_by_date.values()),
                                     max(len(v) for v in self.members_by_date.values())]}


def _keys(rows):
    return ["%s %s" % (r[1], r[2]) for r in rows]


# ---- stage 0 (§6) ------------------------------------------------------------------------------

def positive_control(samples, flat_by_sym, sessions_by_sym):
    """§6.7 on validation stock-times: the target as its own feature, through the harness's
    statistics; and m60 recomputed from the closes against the harness's m60_bp."""
    np = _np()
    closes = {s: np.array([b["close"] for b in flat], dtype="float64") for s, flat in flat_by_sym.items()}
    per = {name: defaultdict(list) for name in HORIZONS}
    m60_bad, worst = [], 0.0
    for sym, d, hhmm, idx, i in samples:
        m60 = k.m60_bp(flat_by_sym[sym], idx)
        again = float((closes[sym][idx] / closes[sym][idx - k.M60_BARS] - 1.0) * 1e4)
        worst = max(worst, abs(m60 - again))
        if abs(m60 - again) > HAND_TOL:
            m60_bad.append([sym, d, hhmm, m60, again])
        bars = sessions_by_sym[sym][d]
        for name, kk in HORIZONS.items():
            y = k.target_bp(bars, i, kk)
            per[name][d].append((y, y, m60))
    out = {"stock_times": len(samples), "m60_mismatches": m60_bad[:20], "m60_worst_abs_diff_bp": worst, "horizons": {}}
    ok = not m60_bad
    for name in HORIZONS:
        s = k.summarise({d: k.session_stats(r) for d, r in per[name].items() if len(r) >= k.MIN_STOCKS})
        sp, ic = s["spread"], s["ic"]
        passed = (sp["mean"] is not None and sp["mean"] > k.TWO_LEG_BP and sp["t"] is not None and sp["t"] > 2
                  and all(hh["mean"] is not None and hh["mean"] > 0 for hh in sp["halves"])
                  and ic["mean"] is not None and ic["mean"] >= 0.99)
        out["horizons"][name] = {"sessions": s["sessions"], "spread_mean_bp": sp["mean"], "spread_t": sp["t"],
                                 "spread_over_bar": (sp["mean"] / k.TWO_LEG_BP) if sp["mean"] is not None else None,
                                 "halves_mean_bp": [hh["mean"] for hh in sp["halves"]], "ic_mean": ic["mean"],
                                 "passes": passed}
        ok = ok and passed
    out["passes"] = ok
    return out


def lookahead_check(flat_by_sym, picks, full_rows):
    """§6.2: features at t from the whole series against features from the series with every
    bar after t removed, bit for bit (NaN payloads made canonical)."""
    out = []
    for (seg, sym, idx), a in zip(picks, full_rows):
        b = alpha158_from_bars(flat_by_sym[sym][: idx + 1])[-1]
        same = canonical_bytes(a) == canonical_bytes(b)
        out.append({"segment": seg, "symbol": sym, "time": flat_by_sym[sym][idx]["time"], "identical": bool(same)})
    return out


def hand_check(flat_by_sym, picks, full_rows):
    """§6.3: every feature (every family) at each pick against hand_features, to 1e-9."""
    out = []
    for (seg, sym, idx), row in zip(picks, full_rows):
        hand = hand_features(flat_by_sym[sym], idx)
        bad = [[name, float(row[j]), hand[name]] for j, name in enumerate(FEATURE_NAMES)
               if not close_enough(row[j], hand[name])]
        out.append({"segment": seg, "symbol": sym, "time": flat_by_sym[sym][idx]["time"],
                    "features_checked": len(FEATURE_NAMES), "mismatches": bad})
    return out


def run_stage0(args):
    guard_platform()
    kh = _kite_history()
    stage0 = OrderedDict([("look", "L47"), ("prereg", PREREG), ("qlib_commit", QLIB_COMMIT),
                          ("started", datetime.now(IST).isoformat()), ("argv", sys.argv[1:]),
                          ("candle_db", str(kh.DB_PATH)), ("environment", environment())])

    def halt(step, why):
        stage0["halted_at"] = {"step": step, "why": why}
        stage0["finished"] = datetime.now(IST).isoformat()
        _write(STAGE0, {"stage0": stage0, "status": "VOID"})
        print("VOID at stage 0 step %s: %s" % (step, why), flush=True)
        sys.exit(2)

    try:
        _stage0_body(stage0, kh, halt)
    except SystemExit:
        raise
    except Exception:
        stage0["crash"] = traceback.format_exc()
        _write(STAGE0, {"stage0": stage0, "status": "CRASHED"})
        raise


def _stage0_body(stage0, kh, halt):
    np = _np()
    started = time.time()
    # 1. the feature count and the Qlib commit
    names = FEATURE_NAMES
    stage0["1_features"] = {"count": len(names), "unique": len(set(names)) == len(names), "qlib_commit": QLIB_COMMIT,
                            "dropped": list(DROPPED), "names": names}
    if len(names) != N_FEATURES or len(set(names)) != N_FEATURES:
        halt(1, "the port has %d features (%d unique), not %d" % (len(names), len(set(names)), N_FEATURES))

    print("stage 0: loading bars before %s (IST) ..." % READ_BEFORE, flush=True)
    try:
        data = Data(kh, READ_BEFORE_TS)
    except CutoffViolation as exc:
        halt(4, "the loader read a timestamp on or after %s: %s" % (READ_BEFORE, exc))
    stage0["data"] = data.describe()
    selection = k.selection_sessions(data.cache_sessions)
    sel_adj = {}
    dropped_sel = k.stage0_adjustment(sel_adj, kh, list(data.flat_by_sym), selection)
    members_sel = {d: k.membership_asof(data.membership_rows, d) for d in selection}
    samples = k.build_samples(data.flat_by_sym, data.sessions_by_sym, selection, members_sel, dropped_sel)
    members_va = {d: data.members_by_date[d] for d in data.split["validation"]}
    samples_va = k.build_samples(data.flat_by_sym, data.sessions_by_sym, data.split["validation"], members_va, data.dropped)
    print("stage 0: %d training rows, %d validation rows, %d test stock-times" % (len(data.rows_tr), len(data.rows_va),
                                                                                 len(samples)), flush=True)

    rng = random.Random(SEED)
    look = ([("train", r[0], r[3]) for r in rng.sample(data.rows_tr, min(LOOKAHEAD_PER_SEGMENT, len(data.rows_tr)))]
            + [("validation", r[0], r[3]) for r in rng.sample(data.rows_va, min(LOOKAHEAD_PER_SEGMENT, len(data.rows_va)))]
            + [("test", s[0], s[3]) for s in rng.sample(samples, min(LOOKAHEAD_PER_SEGMENT, len(samples)))])
    hand = ([("train", r[0], r[3]) for r in rng.sample(data.rows_tr, 2)]
            + [("validation", r[0], r[3]) for r in rng.sample(data.rows_va, 2)]
            + [("test", s[0], s[3]) for s in rng.sample(samples, 1)])
    print("stage 0: computing the features ...", flush=True)
    req = ([(r[0], r[3]) for r in data.rows_tr] + [(p[1], p[2]) for p in look] + [(p[1], p[2]) for p in hand])
    X = feature_rows(data.flat_by_sym, req)
    n_tr = len(data.rows_tr)
    X_tr, X_look, X_hand = X[:n_tr], X[n_tr: n_tr + len(look)], X[n_tr + len(look):]

    # 2. look-ahead
    print("stage 0: look-ahead proof on %d stock-times ..." % len(look), flush=True)
    la = lookahead_check(data.flat_by_sym, look, X_look)
    segs = {seg: sum(1 for c in la if c["segment"] == seg) for seg in ("train", "validation", "test")}
    stage0["2_lookahead"] = {"stock_times": len(la), "by_segment": segs, "all_identical": all(c["identical"] for c in la),
                             "checks": la}
    if len(la) < 200 or min(segs.values()) == 0:
        halt(2, "only %d look-ahead stock-times (%s)" % (len(la), segs))
    if not all(c["identical"] for c in la):
        halt(2, "a feature changed when the bars after t were removed")

    # 3. hand calculation
    hc = hand_check(data.flat_by_sym, hand, X_hand)
    stage0["3_hand_calculation"] = {"stock_times": len(hc), "tolerance": HAND_TOL, "families": FAMILIES, "checks": hc}
    if len(hc) < 5 or any(c["mismatches"] for c in hc):
        halt(3, "a feature differs from its direct computation by more than %g" % HAND_TOL)

    # 4. purge assertions
    first_l40 = selection[0]
    ends = [e for n in HORIZONS for e in data.end_tr[n] + data.end_va[n] if e is not None]
    last_label = max(ends)[:10]
    train_ends = [e for n in HORIZONS for e in data.end_tr[n] if e is not None]
    last_train_label = max(train_ends)[:10]
    gap_l40 = sessions_between(data.cache_sessions, last_label, first_l40)
    gap_tv = sessions_between(data.cache_sessions, data.split["train"][-1], data.split["validation"][0])
    gap_label_tv = sessions_between(data.cache_sessions, last_train_label, data.split["validation"][0])
    try:
        norm = fit_normaliser(X_tr, [r[1] for r in data.rows_tr], data.split["train"])
        norm_ok = True
    except AssertionError as exc:
        norm, norm_ok = {"error": str(exc)}, False
    stage0["4_purge"] = {"last_label_end": last_label, "first_l40_session": first_l40, "sessions_between": len(gap_l40),
                         "train_last": data.split["train"][-1], "validation_first": data.split["validation"][0],
                         "purge_sessions": data.split["purge"], "train_validation_gap": len(gap_tv),
                         "train_label_gap_to_validation": len(gap_label_tv),
                         "normaliser_fit_on_training_only": norm_ok, "normaliser": norm,
                         "max_time_read_ist": _ist_iso(data.max_ts), "read_before": READ_BEFORE}
    if len(gap_l40) < MIN_GAP_TO_L40:
        halt(4, "the last label ends %s, only %d sessions before L40's first (%s)" % (last_label, len(gap_l40), first_l40))
    if len(gap_tv) < PURGE_SESSIONS or len(gap_label_tv) < PURGE_SESSIONS:
        halt(4, "training and validation are %d sessions apart (labels %d)" % (len(gap_tv), len(gap_label_tv)))
    if not norm_ok:
        halt(4, "the normaliser was offered rows outside training")
    if data.max_ts >= READ_BEFORE_TS:
        halt(4, "a timestamp on or after %s was read" % READ_BEFORE)
    nan_frac = np.isnan(X_tr).mean(axis=0)
    stage0["4_purge"]["training_nan_fraction"] = {n: float(x) for n, x in zip(FEATURE_NAMES, nan_frac) if x > 0}
    stage0["4_purge"]["training_inf_count"] = {n: int(x) for n, x in zip(FEATURE_NAMES, np.isinf(X_tr).sum(axis=0)) if x}
    del X, X_tr

    # 5. adjustment
    stage0["5_adjustment"] = {"training_window": data.adjustment, "test_window": sel_adj["adjustment"]}
    if not data.adjustment.get("fetch_runs"):
        halt(5, "the cache records no fetch runs; the adjustment check cannot be made")

    # 6. L40's sample
    with_data = sorted({s[1] for s in samples})
    stage0["6_l40_sample"] = {"selection": splits.describe_split("selection", selection), "sessions_with_data": len(with_data),
                              "stock_times": len(samples), "expected": [L40_SESSIONS_WITH_DATA, L40_STOCK_TIMES]}
    if len(with_data) != L40_SESSIONS_WITH_DATA or len(samples) != L40_STOCK_TIMES:
        halt(6, "L40's sample is %d sessions / %d stock-times, not %d / %d"
             % (len(with_data), len(samples), L40_SESSIONS_WITH_DATA, L40_STOCK_TIMES))

    # 7. positive control, validation only
    pc = positive_control(samples_va, data.flat_by_sym, data.sessions_by_sym)
    stage0["7_positive_control"] = pc
    if not pc["passes"]:
        halt(7, "the target as its own feature did not clear the bar, or m60 differs from the harness's")

    stage0["seconds"] = round(time.time() - started)
    stage0["finished"] = datetime.now(IST).isoformat()
    _write(STAGE0, {"stage0": stage0, "status": "STAGE0_DONE"})
    print("stage 0 complete: all seven checks pass; wrote %s" % STAGE0, flush=True)


# ---- train (§3, §4, §7) ------------------------------------------------------------------------

def run_train(args):
    guard_platform()
    np = _np()
    import lightgbm as lgb
    if not os.path.exists(STAGE0) or _read(STAGE0).get("status") != "STAGE0_DONE":
        raise SystemExit("refusing to train: %s is missing or not STAGE0_DONE" % STAGE0)
    previous = None
    partial = [f for f in expected_frozen_files() if os.path.exists(os.path.join(MODELS_DIR, f))]
    if os.path.exists(FROZEN) or partial:
        if not args.refit_reason:
            raise SystemExit("refusing to train: %s (training runs once; a refit after a crash or a declared bug needs "
                             "--refit-reason, which is recorded)" % ("%s exists" % FROZEN if os.path.exists(FROZEN)
                                                                    else "an earlier attempt left %s" % partial))
        previous = _read(FROZEN) if os.path.exists(FROZEN) else {"partial_files_from_an_unfrozen_attempt": partial}
    s0 = _read(STAGE0)["stage0"]
    kh = _kite_history()
    started = time.time()
    print("train: loading bars before 2025-08-15 (IST) ...", flush=True)
    data = Data(kh, TRAIN_READ_BEFORE_TS)
    desc = data.describe()
    for key in ("train", "validation"):
        if desc["sessions"][key] != s0["data"]["sessions"][key]:
            raise SystemExit("refusing to train: the %s sessions differ from stage 0's" % key)
    if desc["rows"] != s0["data"]["rows"]:
        raise SystemExit("refusing to train: the rows differ from stage 0's: %s vs %s" % (desc["rows"], s0["data"]["rows"]))
    print("train: %d training rows, %d validation rows; computing the features ..." % (len(data.rows_tr), len(data.rows_va)),
          flush=True)
    X_tr = feature_rows(data.flat_by_sym, [(r[0], r[3]) for r in data.rows_tr])
    X_va = feature_rows(data.flat_by_sym, [(r[0], r[3]) for r in data.rows_va])
    norm = fit_normaliser(X_tr, [r[1] for r in data.rows_tr], data.split["train"])
    if not same_stats(norm, s0["4_purge"]["normaliser"]):
        raise SystemExit("refusing to train: the normaliser differs from the one stage 0 fitted on the same rows")
    apply_normaliser(X_tr, norm)
    apply_normaliser(X_va, norm)
    k_tr, k_va = _keys(data.rows_tr), _keys(data.rows_va)

    os.makedirs(MODELS_DIR, exist_ok=True)
    out = OrderedDict()
    for name in HORIZONS:
        y_tr = np.array([np.nan if y is None else y for y in data.y_tr[name]], dtype="float64")
        y_va = np.array([np.nan if y is None else y for y in data.y_va[name]], dtype="float64")
        m_tr, m_va = ~np.isnan(y_tr), ~np.isnan(y_va)
        lab_tr = cs_rank_labels(y_tr[m_tr], [kk for kk, m in zip(k_tr, m_tr) if m])
        lab_va = cs_rank_labels(y_va[m_va], [kk for kk, m in zip(k_va, m_va) if m])
        Xt = X_tr if m_tr.all() else X_tr[m_tr]
        Xv = X_va if m_va.all() else X_va[m_va]
        print("train %s: %d training rows, %d validation rows" % (name, len(lab_tr), len(lab_va)), flush=True)
        t0 = time.time()
        booster, evals = train_one(Xt, lab_tr, Xv, lab_va, feature_names=FEATURE_NAMES)
        path = os.path.join(MODELS_DIR, model_file(name))
        booster.save_model(path, num_iteration=booster.best_iteration)
        reloaded = lgb.Booster(model_file=path)
        pred = reloaded.predict(Xv)
        keys_va = [kk for kk, m in zip(k_va, m_va) if m]
        yv = [float(y) for y in y_va[m_va]]
        six = set(k.DECISION_TIMES)
        sel = [j for j, kk in enumerate(keys_va) if kk[-5:] in six]
        out[name] = {"best_iteration": booster.best_iteration, "rounds_run": len(evals["valid"]["l2"]),
                     "best_valid_l2": evals["valid"]["l2"][booster.best_iteration - 1] if booster.best_iteration else None,
                     "train_rows": int(len(lab_tr)), "validation_rows": int(len(lab_va)),
                     "validation_rank_ic_all_times": timestamp_rank_ic(pred, yv, keys_va),
                     "validation_rank_ic_l40_times": timestamp_rank_ic([pred[j] for j in sel], [yv[j] for j in sel],
                                                                       [keys_va[j] for j in sel]),
                     "seconds": round(time.time() - t0)}
        print("train %s: best iteration %s, validation rank IC %.4f (information only)"
              % (name, booster.best_iteration, out[name]["validation_rank_ic_all_times"]["mean"] or 0), flush=True)
    npath = os.path.join(MODELS_DIR, NORMALISER_FILE)
    with open(npath, "w") as f:
        json.dump({"features": FEATURE_NAMES, "median": norm["median"], "std": norm["std"], "eps": EPS,
                   "mad_scale": MAD_SCALE, "clip": CLIP, "fill": 0.0, "fit_rows": norm["fit_rows"],
                   "fit_first": norm["fit_first"], "fit_last": norm["fit_last"]}, f)
    files = OrderedDict((n, sha256_file(os.path.join(MODELS_DIR, n))) for n in expected_frozen_files())
    record = OrderedDict([
        ("look", "L47"), ("prereg", PREREG), ("qlib_commit", QLIB_COMMIT), ("trained", datetime.now(IST).isoformat()),
        ("files", files), ("models_dir", os.path.relpath(MODELS_DIR, REPO).replace(os.sep, "/")),
        ("feature_fingerprint", feature_fingerprint()), ("lgb_params", LGB_PARAMS),
        ("num_boost_round", NUM_BOOST_ROUND), ("early_stopping_rounds", EARLY_STOPPING_ROUNDS),
        ("horizons", out), ("data", desc), ("stage0_sha256", sha256_file(STAGE0)),
        ("environment", environment()), ("seconds", round(time.time() - started)),
        ("note", "validation IC is information only; it is not a gate and cannot change the design (prereg §7)"),
    ])
    if previous is not None:
        record["refit"] = {"reason": args.refit_reason, "previous": previous}
    _write(FROZEN, record)
    print("train complete; wrote %s. Commit and push it before the scoring pass." % FROZEN, flush=True)


# ---- score (§5) --------------------------------------------------------------------------------

def _void_summary():
    from research.l46_family_gate import VOID_SUMMARY
    return VOID_SUMMARY


def night_gate(l40_doc, l46_docs, l47_summaries):
    """BH at q=0.10 across the night's 24 forecast tests (L40 3, L46 18, L47 3), a void or
    missing test entering at p = 1 (it carries no p)."""
    from research.tsfm_family_ic import MODELS
    combined, status = OrderedDict(), OrderedDict()
    status["L40"] = l40_doc.get("status") if l40_doc else "NOT RUN"
    for h in HORIZONS:
        ok = bool(l40_doc and l40_doc.get("status") == "DONE")
        combined["L40:%s" % h] = l40_doc["result"]["summaries"][h] if ok else _void_summary()
    for m in MODELS:
        doc = l46_docs.get(m)
        status["L46:%s" % m] = doc.get("status") if doc else "NOT RUN"
        for h in HORIZONS:
            ok = bool(doc and doc.get("status") == "DONE")
            combined["L46:%s:%s" % (m, h)] = doc["result"]["summaries"][h] if ok else _void_summary()
    status["L47"] = "DONE"
    for h in HORIZONS:
        combined["L47:%s" % h] = l47_summaries[h]
    assert len(combined) == N_TESTS_NIGHT
    verdicts = k.gate(combined)
    ps = OrderedDict((key, s["spread"]["p"] if s["spread"]["p"] is not None else 1.0) for key, s in combined.items())
    return {"status": status, "p": ps, "bh_survives": OrderedDict((key, v["checks"]["bh_survives"]) for key, v in verdicts.items())}


def verdict(l47_summaries, night):
    within = k.gate(l47_summaries)
    out = OrderedDict()
    for h in HORIZONS:
        out[h] = {"passes": within[h]["passes"] and night["bh_survives"]["L47:%s" % h],
                  "l40_section8_and_bh_within_3": within[h], "bh_across_24": night["bh_survives"]["L47:%s" % h]}
    return out


def guard_cutoff(args, now=None):
    now = now or datetime.now(IST)
    if now >= CUTOFF and not args.owner_approved_after_cutoff:
        raise SystemExit("refusing to score: it is %s, after the 07:30 IST cut-off (prereg §7); the scoring pass waits "
                         "for the owner (--owner-approved-after-cutoff)" % now.strftime("%Y-%m-%d %H:%M IST"))
    return {"now": now.isoformat(), "cutoff": CUTOFF.isoformat(), "after_cutoff_owner_approved": bool(now >= CUTOFF)}


def load_night_inputs(l40_path, l46_dir):
    if not os.path.exists(l40_path):
        raise SystemExit("refusing to score: L40's result %s is missing (pass --l40-result)" % l40_path)
    l40 = _read(l40_path)
    if l40.get("status") != "DONE":
        raise SystemExit("refusing to score: L40's result is %s, not DONE" % l40.get("status"))
    from research.tsfm_family_ic import MODELS
    l46 = {}
    for m in MODELS:
        p = os.path.join(l46_dir, "l46_%s_result.json" % m)
        l46[m] = _read(p) if os.path.exists(p) else None
    return l40, l46


def run_score(args):
    guard_platform()
    cut = guard_cutoff(args)
    if os.path.exists(RESULT) and _read(RESULT).get("status") == "DONE":
        raise SystemExit("refusing to score: %s is DONE; the scoring pass runs once" % RESULT)
    try:
        frozen = verify_frozen(FROZEN, MODELS_DIR)
    except RuntimeError as exc:
        raise SystemExit("refusing to score: %s" % exc)
    if not committed_at_head(FROZEN):
        raise SystemExit("refusing to score: %s is not committed at HEAD (its hashes must be committed and pushed "
                         "before the scoring pass reads any target)" % FROZEN)
    if feature_fingerprint() != frozen["feature_fingerprint"]:
        raise SystemExit("refusing to score: the feature code differs from the code the models were trained with")
    l40, l46 = load_night_inputs(args.l40_result, args.l46_dir)
    import lightgbm as lgb

    kh = _kite_history()
    started = time.time()
    record = OrderedDict([("look", "L47"), ("prereg", PREREG), ("started", datetime.now(IST).isoformat()),
                          ("cutoff", cut), ("frozen_files_verified", frozen["files"]),
                          ("frozen_sha256", sha256_file(FROZEN)), ("environment", environment())])
    membership = k.load_membership_rows()
    pre, max_ts = load_bars(kh, sorted({r["symbol"] for r in membership}), READ_BEFORE_TS)
    record["max_time_read_ist"] = _ist_iso(max_ts)
    flat_by_sym = {s: sorted(c, key=lambda x: x["time"]) for s, c in pre.items()}
    sessions_by_sym = {s: k.by_session(c) for s, c in flat_by_sym.items()}
    selection = k.selection_sessions(splits.sessions_in(pre))
    members = {d: k.membership_asof(membership, d) for d in selection}
    adj = {}
    dropped = k.stage0_adjustment(adj, kh, list(flat_by_sym), selection)
    samples = k.build_samples(flat_by_sym, sessions_by_sym, selection, members, dropped)
    with_data = sorted({s[1] for s in samples})
    record["sample"] = {"selection": splits.describe_split("selection", selection), "sessions_with_data": len(with_data),
                        "stock_times": len(samples), "adjustment_dropped": adj["adjustment"]["dropped_count"]}
    if len(with_data) != L40_SESSIONS_WITH_DATA or len(samples) != L40_STOCK_TIMES:
        record["status_reason"] = "L40's sample not reproduced; no target was scored"
        _write(RESULT, {"score": record, "status": "HALTED"})
        raise SystemExit("HALT: L40's sample is %d / %d, not %d / %d" % (len(with_data), len(samples),
                                                                      L40_SESSIONS_WITH_DATA, L40_STOCK_TIMES))
    print("score: %d stock-times over %d sessions; computing the features ..." % (len(samples), len(with_data)), flush=True)
    X = feature_rows(flat_by_sym, [(s[0], s[3]) for s in samples])
    norm = _read(os.path.join(MODELS_DIR, NORMALISER_FILE))
    if norm["features"] != FEATURE_NAMES:
        raise SystemExit("refusing to score: the normaliser's feature list differs")
    apply_normaliser(X, norm)
    preds = {h: lgb.Booster(model_file=os.path.join(MODELS_DIR, model_file(h))).predict(X) for h in HORIZONS}

    tmp = ROWS + ".tmp"
    record["previous_partial_rows_found"] = os.path.exists(ROWS) or os.path.exists(tmp)
    with open(tmp, "w") as out:
        for j, (sym, d, hhmm, idx, i) in enumerate(samples):
            flat, bars = flat_by_sym[sym], sessions_by_sym[sym][d]
            row = {"sym": sym, "date": d, "hhmm": hhmm, "c0": flat[idx]["close"], "m60": k.m60_bp(flat, idx),
                   "targets": {name: k.target_bp(bars, i, kk) for name, kk in HORIZONS.items()},
                   "features": {name: float(preds[name][j]) for name in HORIZONS}}
            out.write(json.dumps(row) + "\n")
    os.replace(tmp, ROWS)
    result = k.evaluate_rows(ROWS)
    night = night_gate(l40, l46, result["summaries"])
    record["finished"] = datetime.now(IST).isoformat()
    record["seconds"] = round(time.time() - started)
    _write(RESULT, OrderedDict([("score", record), ("status", "DONE"), ("result", result), ("night_gate", night),
                                ("verdict", verdict(result["summaries"], night)),
                                ("constants", {"two_leg_bp": k.TWO_LEG_BP, "round_trip_bp": k.ROUND_TRIP_BP,
                                               "bh_q": k.BH_Q, "night_tests": N_TESTS_NIGHT, "horizons": dict(HORIZONS)})]))
    v = verdict(result["summaries"], night)
    for name, s in result["summaries"].items():
        sp, ic, pic = s["spread"], s["ic"], s["pic"]
        print("L47 %s: sessions %d | IC %.4f (t %.2f) | partial IC %.4f (t %.2f) | spread %.1f bp (t %.2f) | passes: %s"
              % (name, s["sessions"], ic["mean"] or 0, ic["t"] or 0, pic["mean"] or 0, pic["t"] or 0,
                 sp["mean"] or 0, sp["t"] or 0, v[name]["passes"]), flush=True)
    print("wrote", RESULT, flush=True)


# ---- main --------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["stage0", "train", "score"])
    ap.add_argument("--refit-reason", default=None, help="train only: a crash or declared bug before freezing (§7)")
    ap.add_argument("--l40-result", default=L40_RESULT, help="score only: L40's result JSON")
    ap.add_argument("--l46-dir", default=OUT_DIR, help="score only: the folder holding l46_<model>_result.json")
    ap.add_argument("--owner-approved-after-cutoff", action="store_true",
                    help="score only: the owner's decision to run the one scoring pass after 07:30 IST")
    args = ap.parse_args(argv)
    {"stage0": run_stage0, "train": run_train, "score": run_score}[args.command](args)


if __name__ == "__main__":
    main()
