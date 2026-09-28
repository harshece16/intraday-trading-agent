"""Research look L40 — does a zero-shot Kronos forecast rank the next intraday move?

Pre-registered: docs/research/prereg-kronos-feature-ic.md (commit 0657a0e, amendment 1
in 61e4832), both before this file was written. Background:
research/kronos-research-2026-09-28.md.

Order enforced here, as the prereg fixes it:
  stage 0 (six halts, no feature-target relationship read):
    1. the Kronos repo's own regression test passes on the pinned revisions
    2. Hugging Face revisions pinned to commits dated before REVISION_CUTOFF
    3. lookahead proof: forecast bit-identical with and without later bars present
    4. timing on 200 forecasts -> sample_count by the prereg's 36-hour rule
    5. Kite adjustment runs (#108): stock-sessions whose lookback straddles a
       span fetched on a different date are dropped and listed
    6. coverage: >= 30 sessions in each half
  then ONE IC pass: per-session rank IC, partial IC given the last hour's return,
  quintile spread in bp, t across sessions, BH q=0.10 over the family of three.

Measurement only. No strategy, no backtest, no trial (count stays at 125). Nothing
in the live path imports this (tests/test_research_splits.py). torch and the vendored
Kronos repo are imported lazily, inside the forecaster, so the pure functions below
are testable without either.

Run on the Mac, against the Kite 5-minute cache, from backend/:
    research/.kvenv/bin/python -m research.kronos_feature_ic --stage0-only
    research/.kvenv/bin/python -m research.kronos_feature_ic
"""
import argparse
import csv
import json
import math
import os
import random
import statistics as st
import subprocess
import sys
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/

from research import splits  # noqa: E402

# ---- the pre-registration's constants, named once ------------------------------

SELECTION_START = "2025-09-01"
SELECTION_END = "2025-12-31"
DECISION_TIMES = ["09:45", "10:30", "11:15", "12:00", "12:45", "13:30"]
LOOKBACK = 512
PRED_LEN = 12
HORIZONS = OrderedDict([("f15", 3), ("f30", 6), ("f60", 12)])
M60_BARS = 12
SAMPLE_COUNT_DEFAULT = 3
TIMING_BUDGET_HOURS = 36.0
SEED = 123
TEMPERATURE, TOP_P, TOP_K = 1.0, 0.9, 0
MODEL_REPO = "NeoQuasar/Kronos-small"
TOKENIZER_REPO = "NeoQuasar/Kronos-Tokenizer-base"
REVISION_CUTOFF = "2025-09-01"
MIN_SESSIONS_IF_MOVED = 60
ROUND_TRIP_BP = 16.63
TWO_LEG_BP = 33.26
MIN_STOCKS = 20
MIN_SESSIONS_PER_HALF = 30
MIN_SESSIONS_GATE = 60
BH_Q = 0.10
UPSTREAM_MSE = [0.008979, 0.003741]     # tests/test_kronos_regression.py in the Kronos repo
LOOKBACK_SESSIONS = 8                   # 512 bars / 75 per session, rounded up
BAR_MINUTES = 5

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.environ.get("KRONOS_VENDOR", os.path.join(HERE, "kronos_vendor"))
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "docs", "research", "data")
OUT = os.path.join(OUT_DIR, "kronos_l40_result.json")
ROWS = os.path.join(HERE, "kronos_rows_l40.jsonl")
MEMBERSHIP_CSV = os.path.join(HERE, "data", "nifty100_membership.csv")


# ---- statistics, copied verbatim from step2_feature_ic.py so this module does not
# ---- import the scanner ---------------------------------------------------------

def tstat(vals):
    if len(vals) < 2:
        return None, None, None
    m, sd = st.mean(vals), st.stdev(vals)
    se = sd / math.sqrt(len(vals))
    return m, (m / se if se else None), se


def two_sided_p(t, df):
    """Normal approximation; df is large here (dozens of sessions)."""
    if t is None:
        return None
    return 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))


def benjamini_hochberg(pvals, q=0.10):
    """Returns the set of indices that survive BH at level q."""
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    survivors, kmax = set(), -1
    for rank_, i in enumerate(idx, start=1):
        if pvals[i] <= q * rank_ / m:
            kmax = rank_
    if kmax > 0:
        survivors = set(idx[:kmax])
    return survivors


def rank(v):
    n = len(v)
    order = sorted(range(n), key=lambda i: v[i])
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def _pearson(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return num / den if den else None


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    return _pearson(rank(xs), rank(ys))


def partial_spearman(xs, ys, zs):
    """Rank correlation of x and y after removing the (linear, in ranks) part each
    shares with z. The prereg's control: the forecast against the next move, given
    the last hour's return."""
    if len(xs) < 4:
        return None
    rx, ry, rz = rank(xs), rank(ys), rank(zs)

    def residual(a, z):
        mz, ma = st.mean(z), st.mean(a)
        vz = sum((c - mz) ** 2 for c in z)
        beta = sum((c - mz) * (d - ma) for c, d in zip(z, a)) / vz if vz else 0.0
        return [d - ma - beta * (c - mz) for c, d in zip(z, a)]

    return _pearson(residual(rx, rz), residual(ry, rz))


def quintile_spread(feats, targs):
    """Top-quintile mean target minus bottom-quintile mean, in the target's units,
    with each quintile's own mean so a one-sided reading stays visible."""
    n = len(feats)
    q = n // 5
    if q < 1:
        return None
    order = sorted(range(n), key=lambda i: feats[i])
    bottom = [targs[i] for i in order[:q]]
    top = [targs[i] for i in order[-q:]]
    return {"spread": st.mean(top) - st.mean(bottom), "top": st.mean(top), "bottom": st.mean(bottom), "q": q}


# ---- data shaping (pure) --------------------------------------------------------

def membership_asof(rows, date):
    """NIFTY 100 members on `date` from research/data/nifty100_membership.csv rows
    (symbol, from, to; blank from = since the file starts, blank to = still in)."""
    out = set()
    for r in rows:
        frm, to = (r.get("from") or ""), (r.get("to") or "")
        if (not frm or frm <= date) and (not to or date <= to):
            out.add(r["symbol"])
    return out


def load_membership_rows(path=MEMBERSHIP_CSV):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def by_session(candles):
    """{date: [bars in time order]} for one symbol's cached candles."""
    days = OrderedDict()
    for c in candles:
        days.setdefault(c["time"][:10], []).append(c)
    for d in days:
        days[d].sort(key=lambda c: c["time"])
    return days


def decision_bar_index(session_bars, hhmm):
    """Index of the bar that CLOSES at hhmm: its start is hhmm minus one bar. None if
    that bar is missing, so a stock-time is skipped rather than shifted."""
    t = datetime.strptime(hhmm, "%H:%M") - timedelta(minutes=BAR_MINUTES)
    start = t.strftime("%H:%M")
    for i, c in enumerate(session_bars):
        if c["time"][11:16] == start:
            return i
    return None


def target_bp(session_bars, i, k):
    """Signed return, in bp, from the open of the bar after the decision bar `i` to the
    close of the bar `k` bars later (k=3 -> +15 min). None if the session is too short."""
    if i + k >= len(session_bars) or i + 1 >= len(session_bars):
        return None
    entry = session_bars[i + 1]["open"]
    exit_ = session_bars[i + k]["close"]
    if not entry:
        return None
    return (exit_ - entry) / entry * 1e4


def lookback_window(flat, idx, n=LOOKBACK):
    """The `n` closed bars ending at flat index `idx` (inclusive), or None."""
    if idx - (n - 1) < 0:
        return None
    return flat[idx - (n - 1): idx + 1]


def m60_bp(flat, idx, bars=M60_BARS):
    """The last `bars` bars' close-to-close return in bp, ending at the decision bar.
    At 09:45 this spans the overnight gap; that is what 'the last twelve bars' means."""
    if idx - bars < 0:
        return None
    c0, cm = flat[idx]["close"], flat[idx - bars]["close"]
    return (c0 - cm) / cm * 1e4 if cm else None


def forecast_features(pred_closes, c0):
    """f15/f30/f60 in bp from the forecast closes (index k-1 is k bars ahead)."""
    out = {}
    for name, k in HORIZONS.items():
        if len(pred_closes) < k or not c0:
            out[name] = None
        else:
            out[name] = (pred_closes[k - 1] - c0) / c0 * 1e4
    return out


def pick_revision(commits, cutoff=REVISION_CUTOFF):
    """Latest (sha, date) with date < cutoff, else None. Dates are ISO strings."""
    before = [c for c in commits if c[1][:10] < cutoff]
    if not before:
        return None
    return max(before, key=lambda c: c[1])


def moved_window(commits, sessions, cutoff=REVISION_CUTOFF):
    """The prereg's §2 rule when no revision predates the cutoff: the window starts
    after the earliest revision's date; void if fewer than MIN_SESSIONS_IF_MOVED
    sessions remain before the held-out boundary."""
    earliest = min(commits, key=lambda c: c[1])
    start = earliest[1][:10]
    kept = [s for s in sessions if s > start]
    return {"start": start, "sessions": len(kept), "void": len(kept) < MIN_SESSIONS_IF_MOVED}


def selection_sessions(all_sessions):
    """Sessions in the selection window, minus the phase-2 embargo before the held-out
    boundary. The 2026 window is never returned."""
    window = [s for s in sorted(all_sessions) if SELECTION_START <= s <= SELECTION_END]
    selection, _ = splits.selection_holdout(window, boundary=splits.HELD_OUT_START,
                                            embargo=splits.EMBARGO_SESSIONS)
    return selection


def adjustment_boundaries(fetched_rows):
    """Per symbol, the from_dates of spans whose fetch date differs from the previous
    span's: where Kite's as-of-fetch dividend adjustment (#108) can step."""
    by_sym = defaultdict(list)
    for r in fetched_rows:
        if r.get("fetched_at") is None:
            continue
        day = datetime.fromtimestamp(r["fetched_at"]).strftime("%Y-%m-%d")
        by_sym[r["symbol"]].append((r["from_date"], day))
    out = {}
    for sym, spans in by_sym.items():
        spans.sort()
        bounds = [frm for (frm, day), (_, prev_day) in zip(spans[1:], spans[:-1]) if day != prev_day]
        if bounds:
            out[sym] = bounds
    return out


def straddles(bounds, sessions, date, span=LOOKBACK_SESSIONS):
    """True if a boundary falls inside the `span` sessions ending at `date`."""
    i = sessions.index(date)
    window = sessions[max(0, i - span + 1): i + 1]
    return any(window[0] <= b <= window[-1] for b in bounds)


# ---- statistics over sessions (pure) ---------------------------------------------

def session_stats(rows):
    """rows: [(feature, target, m60)] for one session and one feature."""
    f = [r[0] for r in rows]
    y = [r[1] for r in rows]
    m = [r[2] for r in rows]
    qs = quintile_spread(f, y)
    return {"n": len(rows), "ic": spearman(f, y), "pic": partial_spearman(f, y, m),
            "spread": qs["spread"] if qs else None,
            "top": qs["top"] if qs else None, "bottom": qs["bottom"] if qs else None}


def _series_summary(vals):
    vals = [v for v in vals if v is not None]
    m, t, se = tstat(vals)
    return {"n": len(vals), "mean": m, "t": t, "se": se,
            "p": two_sided_p(t, len(vals) - 1) if t is not None else None,
            "pct_pos": (sum(v > 0 for v in vals) / len(vals) if vals else None),
            "detectable_at_t2": (2 * se if se else None)}


def summarise(per_session):
    """per_session: {date: session_stats}. Mean/t across sessions, both halves."""
    dates = sorted(per_session)
    first, second = splits.halves(dates)
    out = {"sessions": len(dates)}
    for key in ("ic", "pic", "spread", "top", "bottom"):
        out[key] = _series_summary([per_session[d][key] for d in dates])
        out[key]["halves"] = [_series_summary([per_session[d][key] for d in first]),
                              _series_summary([per_session[d][key] for d in second])]
    return out


def gate(summary_by_feature):
    """The prereg's §8 gate, evaluated on the summaries. BH runs over the family of
    three spread tests; the partial-IC condition is a validity check outside it
    (amendment 1)."""
    names = list(summary_by_feature)
    ps = [summary_by_feature[n]["spread"]["p"] if summary_by_feature[n]["spread"]["p"] is not None else 1.0
          for n in names]
    survivors = benjamini_hochberg(ps, q=BH_Q)
    verdicts = {}
    for i, n in enumerate(names):
        s = summary_by_feature[n]
        sp, pic = s["spread"], s["pic"]
        checks = {
            "spread_gt_two_leg": sp["mean"] is not None and sp["mean"] > TWO_LEG_BP,
            "spread_t_gt_2": sp["t"] is not None and sp["t"] > 2,
            "sessions_ge_min": s["sessions"] >= MIN_SESSIONS_GATE,
            "both_halves_positive": all(h["mean"] is not None and h["mean"] > 0 for h in sp["halves"]),
            "bh_survives": i in survivors,
            "partial_ic_t_gt_2": pic["mean"] is not None and pic["mean"] > 0 and pic["t"] is not None and pic["t"] > 2,
        }
        one_side = {side: (s[side]["mean"] is not None and abs(s[side]["mean"]) > ROUND_TRIP_BP
                           and s[side]["t"] is not None and abs(s[side]["t"]) > 2)
                    for side in ("top", "bottom")}
        verdicts[n] = {"passes": all(checks.values()), "checks": checks, "single_side_note": one_side}
    return verdicts


# ---- the forecaster (torch and the vendored repo, imported lazily) ---------------

def set_seeds(seed=SEED):
    import numpy as np
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class KronosForecaster:
    def __init__(self, model_rev, tokenizer_rev, sample_count, device=None):
        import torch  # noqa: F401
        if VENDOR not in sys.path:
            sys.path.insert(0, VENDOR)
        from model import Kronos, KronosPredictor, KronosTokenizer
        self.tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_REPO, revision=tokenizer_rev)
        self.model = Kronos.from_pretrained(MODEL_REPO, revision=model_rev)
        self.predictor = KronosPredictor(self.model, self.tokenizer, device=device, max_context=LOOKBACK)
        self.sample_count = sample_count

    @staticmethod
    def _frame(window):
        import pandas as pd
        df = pd.DataFrame([{k: float(b[k]) for k in ("open", "high", "low", "close", "volume")} for b in window])
        ts = pd.Series(pd.to_datetime([b["time"] for b in window]))
        return df, ts

    @staticmethod
    def _future_stamps(last_time):
        import pandas as pd
        t0 = datetime.fromisoformat(last_time) + timedelta(minutes=BAR_MINUTES)
        return pd.Series(pd.to_datetime([t0 + timedelta(minutes=BAR_MINUTES * i) for i in range(PRED_LEN)]))

    def forecast_batch(self, windows):
        """windows: list of 512-bar lists. Returns a list of PRED_LEN forecast closes each."""
        set_seeds()
        dfs, xts, yts = [], [], []
        for w in windows:
            df, ts = self._frame(w)
            dfs.append(df)
            xts.append(ts)
            yts.append(self._future_stamps(w[-1]["time"]))
        preds = self.predictor.predict_batch(dfs, xts, yts, pred_len=PRED_LEN, T=TEMPERATURE, top_k=TOP_K,
                                             top_p=TOP_P, sample_count=self.sample_count, verbose=False)
        return [p["close"].tolist() for p in preds]


# ---- stage 0 ---------------------------------------------------------------------

def halt(stage0, step, why):
    stage0["halted_at"] = {"step": step, "why": why}
    _write({"stage0": stage0, "status": "HALTED"})
    print("HALT at stage 0 step %s: %s" % (step, why))
    sys.exit(2)


def _write(obj):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(obj, f, indent=1, default=str)


def stage0_regression(stage0, skip_reason=None):
    if skip_reason:
        stage0["regression"] = {"result": "SKIPPED", "why": skip_reason}
        return
    test = os.path.join(VENDOR, "tests", "test_kronos_regression.py")
    if not os.path.exists(test):
        halt(stage0, 1, "vendored repo has no tests/test_kronos_regression.py at %s" % VENDOR)
    started = time.time()
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", test], cwd=VENDOR, capture_output=True, text=True)
    stage0["regression"] = {"result": "PASS" if r.returncode == 0 else "FAIL", "seconds": round(time.time() - started),
                            "tail": r.stdout[-1500:], "expected_mse": UPSTREAM_MSE}
    if r.returncode != 0:
        halt(stage0, 1, "upstream regression test failed; our inference path is not the authors'")


def stage0_revisions(stage0, sessions):
    from huggingface_hub import HfApi
    api = HfApi()
    picks = {}
    for repo in (MODEL_REPO, TOKENIZER_REPO):
        commits = [(c.commit_id, c.created_at.isoformat()) for c in api.list_repo_commits(repo)]
        pick = pick_revision(commits)
        picks[repo] = {"commits": commits, "picked": pick}
    stage0["revisions"] = picks
    if all(v["picked"] for v in picks.values()):
        return sessions, {r: v["picked"][0] for r, v in picks.items()}
    all_commits = [c for v in picks.values() for c in v["commits"]]
    moved = moved_window(all_commits, sessions)
    stage0["revisions"]["moved_window"] = moved
    if moved["void"]:
        halt(stage0, 2, "no revision predates %s and only %d sessions remain after the earliest one; the look is VOID"
             % (REVISION_CUTOFF, moved["sessions"]))
    kept = [s for s in sessions if s > moved["start"]]
    latest = {r: max(v["commits"], key=lambda c: c[1])[0] for r, v in picks.items()}
    return kept, latest


def stage0_lookahead(stage0, fc, flat_by_sym, samples, n=20):
    import numpy as np
    rng = random.Random(SEED)
    checks = []
    for sym, idx in rng.sample(samples, min(n, len(samples))):
        flat = flat_by_sym[sym]
        full = lookback_window(flat, idx)
        truncated = lookback_window(flat[: idx + 1], idx)
        a = fc.forecast_batch([full])[0]
        b = fc.forecast_batch([truncated])[0]
        checks.append({"symbol": sym, "idx": idx, "identical": bool(np.array_equal(a, b))})
    stage0["lookahead"] = checks
    if not all(c["identical"] for c in checks):
        halt(stage0, 3, "a forecast changed when later bars were present in the source table")


def stage0_timing(stage0, fc, flat_by_sym, samples, total_forecasts, n=200):
    rng = random.Random(SEED + 1)
    picks = rng.sample(samples, min(n, len(samples)))
    windows = [lookback_window(flat_by_sym[s], i) for s, i in picks]
    started = time.time()
    for i in range(0, len(windows), 25):
        fc.forecast_batch(windows[i:i + 25])
    per = (time.time() - started) / max(len(windows), 1)
    hours_at_3 = per * total_forecasts / 3600 * (3 / fc.sample_count)
    chosen = SAMPLE_COUNT_DEFAULT if hours_at_3 <= TIMING_BUDGET_HOURS else 1
    stage0["timing"] = {"forecasts": len(windows), "seconds_per_forecast_at_sample_count": fc.sample_count,
                        "seconds_per": per, "total_forecasts": total_forecasts,
                        "est_hours_at_sample_count_3": hours_at_3, "sample_count_chosen": chosen}
    return chosen


def stage0_adjustment(stage0, kite_history, symbols, sessions):
    runs = kite_history.fetch_runs("5m")
    rows = kite_history._conn().execute(
        "SELECT symbol, from_date, to_date, fetched_at FROM fetched WHERE interval='5m'").fetchall()
    bounds = adjustment_boundaries([dict(r) for r in rows])
    dropped = {}
    for sym in symbols:
        if sym in bounds:
            bad = [d for d in sessions if straddles(bounds[sym], sessions, d)]
            if bad:
                dropped[sym] = bad
    stage0["adjustment"] = {"fetch_runs": runs, "boundaries": bounds, "dropped_stock_sessions": dropped,
                            "dropped_count": sum(len(v) for v in dropped.values())}
    return dropped


def stage0_coverage(stage0, sessions, stock_times_per_session):
    first, second = splits.halves(sessions)
    cov = {"sessions": len(sessions), "first_half": len(first), "second_half": len(second),
           "stock_times": sum(stock_times_per_session.values()),
           "sessions_below_min_stocks": [d for d, n in stock_times_per_session.items() if n < MIN_STOCKS * len(DECISION_TIMES)]}
    stage0["coverage"] = cov
    if min(len(first), len(second)) < MIN_SESSIONS_PER_HALF:
        halt(stage0, 6, "a half has fewer than %d sessions" % MIN_SESSIONS_PER_HALF)


# ---- the one IC pass ----------------------------------------------------------------

def build_samples(flat_by_sym, sessions_by_sym, sessions, members_by_date, dropped):
    """Every (symbol, session, decision time) with a full lookback and all three
    targets. Returns [(sym, date, hhmm, flat_idx, session_idx)]."""
    out = []
    for sym, flat in flat_by_sym.items():
        pos = {(c["time"][:10], c["time"][11:16]): i for i, c in enumerate(flat)}
        for d in sessions:
            if sym not in members_by_date[d] or d in dropped.get(sym, []):
                continue
            bars = sessions_by_sym[sym].get(d)
            if not bars:
                continue
            for hhmm in DECISION_TIMES:
                i = decision_bar_index(bars, hhmm)
                if i is None:
                    continue
                idx = pos.get((d, bars[i]["time"][11:16]))
                if idx is None or lookback_window(flat, idx) is None or m60_bp(flat, idx) is None:
                    continue
                if any(target_bp(bars, i, k) is None for k in HORIZONS.values()):
                    continue
                out.append((sym, d, hhmm, idx, i))
    return out


def run_ic_pass(fc, samples, flat_by_sym, sessions_by_sym, progress=None):
    """Forecast every sample, batched by (session, time); append rows to ROWS so a
    crash before any statistic can resume without recomputing."""
    done = set()
    if os.path.exists(ROWS):
        with open(ROWS) as f:
            for line in f:
                r = json.loads(line)
                done.add((r["sym"], r["date"], r["hhmm"]))
    groups = defaultdict(list)
    for s in samples:
        if (s[0], s[1], s[2]) not in done:
            groups[(s[1], s[2])].append(s)
    keys = sorted(groups)
    started = time.time()
    with open(ROWS, "a") as out:
        for n, key in enumerate(keys, 1):
            batch = groups[key]
            for j in range(0, len(batch), 25):
                part = batch[j:j + 25]
                preds = fc.forecast_batch([lookback_window(flat_by_sym[s[0]], s[3]) for s in part])
                for s, pc in zip(part, preds):
                    sym, d, hhmm, idx, i = s
                    flat, bars = flat_by_sym[sym], sessions_by_sym[sym][d]
                    row = {"sym": sym, "date": d, "hhmm": hhmm, "c0": flat[idx]["close"], "pred_close": pc,
                           "m60": m60_bp(flat, idx),
                           "targets": {name: target_bp(bars, i, k) for name, k in HORIZONS.items()}}
                    row["features"] = forecast_features(pc, row["c0"])
                    out.write(json.dumps(row) + "\n")
                out.flush()
            if progress and (n % 20 == 0 or n == len(keys)):
                progress(n, len(keys), started)


def evaluate_rows(path=ROWS):
    per = {name: defaultdict(list) for name in HORIZONS}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            for name in HORIZONS:
                fv, tv = r["features"].get(name), r["targets"].get(name)
                if fv is None or tv is None or r["m60"] is None:
                    continue
                per[name][r["date"]].append((fv, tv, r["m60"]))
    summaries = {}
    for name in HORIZONS:
        per_session = {d: session_stats(rows) for d, rows in per[name].items() if len(rows) >= MIN_STOCKS}
        summaries[name] = summarise(per_session)
    return {"summaries": summaries, "gate": gate(summaries)}


# ---- main ---------------------------------------------------------------------------

def _progress(done, total, started):
    el = time.time() - started
    eta = time.strftime("%Y-%m-%d %H:%M", time.localtime(started + el / max(done, 1) * total))
    print("  %d/%d session-times, %.0f min elapsed, est. finish %s" % (done, total, el / 60, eta), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage0-only", action="store_true")
    ap.add_argument("--skip-regression", default=None, help="record a reason instead of running the upstream test")
    ap.add_argument("--device", default=None)
    ap.add_argument("--limit-symbols", type=int, default=0, help="smoke runs only; recorded in the output")
    args = ap.parse_args(argv)

    import kite_history
    stage0 = {"started": datetime.now().isoformat(), "argv": sys.argv[1:], "prereg": "docs/research/prereg-kronos-feature-ic.md"}
    if args.limit_symbols:
        stage0["SMOKE_RUN_NOT_THE_LOOK"] = args.limit_symbols

    rows = load_membership_rows()
    all_members = sorted({r["symbol"] for r in rows})
    if args.limit_symbols:
        all_members = all_members[: args.limit_symbols]
    pre = kite_history.load_batch(all_members, interval="5m")
    sessions = selection_sessions(splits.sessions_in(pre))
    if not sessions:
        halt(stage0, 0, "no cached sessions in the selection window %s..%s" % (SELECTION_START, SELECTION_END))
    stage0["selection"] = splits.describe_split("selection", sessions)

    stage0_regression(stage0, args.skip_regression)
    sessions, revs = stage0_revisions(stage0, sessions)

    members_by_date = {d: membership_asof(rows, d) for d in sessions}
    flat_by_sym = {s: sorted(c, key=lambda x: x["time"]) for s, c in pre.items()}
    sessions_by_sym = {s: by_session(c) for s, c in flat_by_sym.items()}

    fc = KronosForecaster(revs[MODEL_REPO], revs[TOKENIZER_REPO], SAMPLE_COUNT_DEFAULT, device=args.device)
    dropped = stage0_adjustment(stage0, kite_history, list(flat_by_sym), sessions)
    samples = build_samples(flat_by_sym, sessions_by_sym, sessions, members_by_date, dropped)
    lookahead_pool = [(s[0], s[3]) for s in samples]
    stage0_lookahead(stage0, fc, flat_by_sym, lookahead_pool)
    fc.sample_count = stage0_timing(stage0, fc, flat_by_sym, lookahead_pool, len(samples))
    per_session_count = defaultdict(int)
    for s in samples:
        per_session_count[s[1]] += 1
    stage0_coverage(stage0, sessions, per_session_count)
    _write({"stage0": stage0, "status": "STAGE0_DONE"})
    print("stage 0 complete: %d samples over %d sessions, sample_count=%d" % (len(samples), len(sessions), fc.sample_count))
    if args.stage0_only:
        return

    run_ic_pass(fc, samples, flat_by_sym, sessions_by_sym, progress=_progress)
    result = evaluate_rows()
    _write({"stage0": stage0, "status": "DONE", "finished": datetime.now().isoformat(), "result": result,
            "constants": {"two_leg_bp": TWO_LEG_BP, "round_trip_bp": ROUND_TRIP_BP, "bh_q": BH_Q, "horizons": dict(HORIZONS)}})
    for name, s in result["summaries"].items():
        sp, ic, pic = s["spread"], s["ic"], s["pic"]
        print("%s: sessions %d | IC %.4f (t %.2f) | partial IC %.4f (t %.2f) | spread %.1f bp (t %.2f) | passes: %s"
              % (name, s["sessions"], ic["mean"] or 0, ic["t"] or 0, pic["mean"] or 0, pic["t"] or 0,
                 sp["mean"] or 0, sp["t"] or 0, result["gate"][name]["passes"]))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
