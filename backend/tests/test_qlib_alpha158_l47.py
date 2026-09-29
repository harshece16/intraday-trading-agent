"""Research look L47 (docs/research/prereg-qlib-lgbm-alpha158.md): the parts that decide
something, on small synthetic data only. No candle cache is read; D2b keeps L47's real
computation off the Mac."""
import importlib.machinery
import json
import math
import os
import random
import sqlite3
import subprocess
import sys
from collections import deque
from datetime import datetime, timedelta

import pytest

from research import kronos_feature_ic as k
from research import qlib_alpha158_l47 as q

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")


# ---- synthetic bars ------------------------------------------------------------------------

def _bars(n, seed=7, base=3000.0, start="2025-01-01T09:15:00"):
    """A tick-rounded random walk with flat stretches, ties and zero-volume bars."""
    rng = random.Random(seed)
    t0 = datetime.fromisoformat(start)
    out, p = [], base
    for i in range(n):
        o = p
        p = max(1.0, round((p + rng.choice([-1, 0, 0, 0, 1]) * 0.05 * rng.randint(0, 30)) / 0.05) * 0.05)
        hi = max(o, p) + 0.05 * rng.randint(0, 6)
        lo = min(o, p) - 0.05 * rng.randint(0, 6)
        vol = rng.choice([0, 0, 3, 150, 2000, 40000, 90000])
        out.append({"time": (t0 + timedelta(minutes=5 * i)).isoformat(), "open": o, "high": hi, "low": lo,
                    "close": p, "volume": vol})
    return out


# ---- the feature list ------------------------------------------------------------------------

def _qlib_default_fields():
    """Alpha158DL.get_feature_config()'s default fields and names, transcribed from
    qlib/contrib/data/loader.py at be725493 (the loop structure kept)."""
    fields = ["($close-$open)/$open", "($high-$low)/$open", "($close-$open)/($high-$low+1e-12)",
              "($high-Greater($open, $close))/$open", "($high-Greater($open, $close))/($high-$low+1e-12)",
              "(Less($open, $close)-$low)/$open", "(Less($open, $close)-$low)/($high-$low+1e-12)",
              "(2*$close-$high-$low)/$open", "(2*$close-$high-$low)/($high-$low+1e-12)"]
    names = ["KMID", "KLEN", "KMID2", "KUP", "KUP2", "KLOW", "KLOW2", "KSFT", "KSFT2"]
    for field in ["OPEN", "HIGH", "LOW", "VWAP"]:
        fields += ["$%s/$close" % field.lower()]
        names += [field + "0"]
    w = [5, 10, 20, 30, 60]
    specs = [
        ("ROC", lambda d: "Ref($close, %d)/$close" % d), ("MA", lambda d: "Mean($close, %d)/$close" % d),
        ("STD", lambda d: "Std($close, %d)/$close" % d), ("BETA", lambda d: "Slope($close, %d)/$close" % d),
        ("RSQR", lambda d: "Rsquare($close, %d)" % d), ("RESI", lambda d: "Resi($close, %d)/$close" % d),
        ("MAX", lambda d: "Max($high, %d)/$close" % d), ("MIN", lambda d: "Min($low, %d)/$close" % d),
        ("QTLU", lambda d: "Quantile($close, %d, 0.8)/$close" % d), ("QTLD", lambda d: "Quantile($close, %d, 0.2)/$close" % d),
        ("RANK", lambda d: "Rank($close, %d)" % d),
        ("RSV", lambda d: "($close-Min($low, %d))/(Max($high, %d)-Min($low, %d)+1e-12)" % (d, d, d)),
        ("IMAX", lambda d: "IdxMax($high, %d)/%d" % (d, d)), ("IMIN", lambda d: "IdxMin($low, %d)/%d" % (d, d)),
        ("IMXD", lambda d: "(IdxMax($high, %d)-IdxMin($low, %d))/%d" % (d, d, d)),
        ("CORR", lambda d: "Corr($close, Log($volume+1), %d)" % d),
        ("CORD", lambda d: "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), %d)" % d),
        ("CNTP", lambda d: "Mean($close>Ref($close, 1), %d)" % d), ("CNTN", lambda d: "Mean($close<Ref($close, 1), %d)" % d),
        ("CNTD", lambda d: "Mean($close>Ref($close, 1), %d)-Mean($close<Ref($close, 1), %d)" % (d, d)),
        ("SUMP", lambda d: "Sum(Greater($close-Ref($close, 1), 0), %d)/(Sum(Abs($close-Ref($close, 1)), %d)+1e-12)" % (d, d)),
        ("SUMN", lambda d: "Sum(Greater(Ref($close, 1)-$close, 0), %d)/(Sum(Abs($close-Ref($close, 1)), %d)+1e-12)" % (d, d)),
        ("SUMD", lambda d: "(Sum(Greater($close-Ref($close, 1), 0), %d)-Sum(Greater(Ref($close, 1)-$close, 0), %d))"
                           "/(Sum(Abs($close-Ref($close, 1)), %d)+1e-12)" % (d, d, d)),
        ("VMA", lambda d: "Mean($volume, %d)/($volume+1e-12)" % d), ("VSTD", lambda d: "Std($volume, %d)/($volume+1e-12)" % d),
        ("WVMA", lambda d: "Std(Abs($close/Ref($close, 1)-1)*$volume, %d)/(Mean(Abs($close/Ref($close, 1)-1)*$volume, %d)+1e-12)"
                           % (d, d)),
        ("VSUMP", lambda d: "Sum(Greater($volume-Ref($volume, 1), 0), %d)/(Sum(Abs($volume-Ref($volume, 1)), %d)+1e-12)" % (d, d)),
        ("VSUMN", lambda d: "Sum(Greater(Ref($volume, 1)-$volume, 0), %d)/(Sum(Abs($volume-Ref($volume, 1)), %d)+1e-12)" % (d, d)),
        ("VSUMD", lambda d: "(Sum(Greater($volume-Ref($volume, 1), 0), %d)-Sum(Greater(Ref($volume, 1)-$volume, 0), %d))"
                            "/(Sum(Abs($volume-Ref($volume, 1)), %d)+1e-12)" % (d, d, d)),
    ]
    for op, fn in specs:
        fields += [fn(d) for d in w]
        names += ["%s%d" % (op, d) for d in w]
    return fields, names


def test_the_port_has_157_features_in_qlibs_order_with_only_vwap0_dropped():
    fields, names = _qlib_default_fields()
    assert len(names) == 158
    keep = [(f, n) for f, n in zip(fields, names) if n != "VWAP0"]
    assert q.FEATURE_NAMES == [n for _, n in keep]
    assert list(q.qlib_expressions().values()) == [f for f, _ in keep]
    assert len(q.FEATURE_NAMES) == q.N_FEATURES == 157 and len(set(q.FEATURE_NAMES)) == 157
    assert q.QLIB_COMMIT == "be725493eb1a6bbb42bf11b37aa7669f59610ff1"
    fam = [op for group in q.FAMILIES for op in group]
    assert set(fam) >= set(q.ROLLING)


# ---- each operator against a direct computation -------------------------------------------------

def test_every_feature_matches_the_hand_calculation_to_1e9_including_partial_windows():
    bars = _bars(700)
    F = q.alpha158_from_bars(bars)
    checked = 0
    for t in list(range(0, 66)) + list(range(66, 700, 23)):
        hand = q.hand_features(bars, t)
        for j, name in enumerate(q.FEATURE_NAMES):
            assert q.close_enough(F[t, j], hand[name]), (t, name, F[t, j], hand[name])
            checked += 1
    assert checked > 157 * 90


def test_the_dataframe_entry_point_returns_the_same_matrix():
    bars = _bars(150)
    df = pd.DataFrame(bars)
    out = q.alpha158_features(df)
    assert list(out.columns) == q.FEATURE_NAMES and len(out) == 150
    assert q.canonical_bytes(out.to_numpy()) == q.canonical_bytes(q.alpha158_from_bars(bars))
    with pytest.raises(ValueError):
        q.alpha158_features(df.iloc[::-1])


def test_kbar_and_price_features_by_hand():
    bars = [{"time": "a", "open": 100.0, "high": 104.0, "low": 98.0, "close": 103.0, "volume": 10}]
    F = q.alpha158_from_bars(bars)[0]
    f = dict(zip(q.FEATURE_NAMES, F))
    assert f["KMID"] == pytest.approx(0.03) and f["KLEN"] == pytest.approx(0.06)
    assert f["KMID2"] == pytest.approx(3 / 6) and f["KUP"] == pytest.approx(0.01) and f["KUP2"] == pytest.approx(1 / 6)
    assert f["KLOW"] == pytest.approx(0.02) and f["KLOW2"] == pytest.approx(2 / 6)
    assert f["KSFT"] == pytest.approx((206 - 104 - 98) / 100) and f["KSFT2"] == pytest.approx(4 / 6)
    assert f["OPEN0"] == pytest.approx(100 / 103) and f["HIGH0"] == pytest.approx(104 / 103)
    assert f["LOW0"] == pytest.approx(98 / 103)
    # one bar: no window has two values, Ref is missing
    assert math.isnan(f["ROC5"]) and math.isnan(f["STD5"]) and math.isnan(f["BETA5"]) and math.isnan(f["CORR5"])
    assert f["MA5"] == pytest.approx(1.0) and f["RANK5"] == 1.0 and f["IMAX5"] == pytest.approx(1 / 5)
    assert f["CNTP5"] == 0.0 and math.isnan(f["SUMP5"])          # Ref NaN: `>` is False, Greater is NaN


def _series(n=160, seed=3, nan_at=(40, 41, 97)):
    rng = random.Random(seed)
    x = np.array([1.0 + 0.1 * math.sin(i / 5.0) + 0.05 * rng.random() for i in range(n)])
    y = np.array([2.0 + 0.3 * rng.random() for _ in range(n)])
    x[list(nan_at)] = np.nan
    y[[10, 97, 120]] = np.nan
    return x, y


@pytest.mark.parametrize("n", q.WINDOWS)
def test_mean_sum_std_corr_match_the_pandas_calls_qlib_makes(n):
    x, y = _series()
    sx, sy = pd.Series(x), pd.Series(y)
    assert np.allclose(q.rolling_mean(x, n), sx.rolling(n, min_periods=1).mean(), rtol=0, atol=1e-12, equal_nan=True)
    assert np.allclose(q.rolling_sum(x, n)[0], sx.rolling(n, min_periods=1).sum(), rtol=0, atol=1e-12, equal_nan=True)
    assert np.allclose(q.rolling_std(x, n), sx.rolling(n, min_periods=1).std(), rtol=0, atol=1e-12, equal_nan=True)
    # ops.py Corr: pandas' rolling corr, then NaN where either rolling std is ~0
    ref = sx.rolling(n, min_periods=1).corr(sy)
    ref[np.isclose(sx.rolling(n, min_periods=1).std(), 0, atol=2e-05)
        | np.isclose(sy.rolling(n, min_periods=1).std(), 0, atol=2e-05)] = np.nan
    assert np.allclose(q.rolling_corr(x, y, n), ref, rtol=0, atol=1e-10, equal_nan=True)


def test_corr_and_rsquare_are_masked_where_an_input_is_flat():
    c = np.array([100.0] * 30 + [100.0 + 0.5 * i for i in range(30)])
    v = np.linspace(1, 3, 60)
    r = q.rolling_corr(c, v, 5)
    assert np.isnan(r[4:30]).all() and np.isfinite(r[40:]).all()
    _, rsq, _ = q.rolling_regression(c, 5)
    assert np.isnan(rsq[4:30]).all() and np.allclose(rsq[40:], 1.0)


@pytest.mark.parametrize("n", q.WINDOWS)
def test_idxmax_idxmin_match_qlibs_rolling_apply_one_based(n):
    rng = random.Random(n)
    x = np.array([float(rng.randint(0, 6)) for _ in range(140)])      # many ties
    x[[3, 77]] = np.nan
    s = pd.Series(x)
    for which, fn in (("max", lambda w: w.argmax() + 1), ("min", lambda w: w.argmin() + 1)):
        ref = s.rolling(n, min_periods=1).apply(fn, raw=True).to_numpy()
        assert q.canonical_bytes(q.rolling_argext(x, n, which)) == q.canonical_bytes(ref)


def _percentileofscore_rank(a, score):
    """scipy.stats.percentileofscore(a, score, kind='rank') / 100 (Qlib's Rank fallback)."""
    a = np.asarray(a)
    left, right = np.count_nonzero(a < score), np.count_nonzero(a <= score)
    return (left + right + (1 if right > left else 0)) * (50.0 / len(a)) / 100


@pytest.mark.parametrize("n", q.WINDOWS)
def test_rank_is_the_percentile_of_the_last_value_average_ties(n):
    rng = random.Random(100 + n)
    x = np.array([float(rng.randint(0, 8)) for _ in range(120)])
    got = q.rolling_rank(x, n)
    for t in range(len(x)):
        w = x[max(0, t - n + 1): t + 1]
        assert got[t] == pytest.approx(_percentileofscore_rank(w, w[-1]), abs=1e-15)


@pytest.mark.parametrize("n", q.WINDOWS)
def test_quantile_interpolates_linearly(n):
    x, _ = _series(nan_at=())
    for qq in (0.8, 0.2):
        got = q.rolling_quantile(x, n, qq)
        for t in range(len(x)):
            w = x[max(0, t - n + 1): t + 1]
            assert got[t] == pytest.approx(np.quantile(w, qq, method="linear"), abs=1e-14)


class _CySlopeFamily(object):
    """A line-by-line Python port of qlib/data/_libs/rolling.pyx's Slope, Resi and Rsquare
    (one object computes all three from the same running sums)."""

    def __init__(self, window):
        self.window, self.na_count = window, window
        self.barv = deque([np.nan] * window)
        self.i_sum = self.x_sum = self.x2_sum = self.y_sum = self.y2_sum = self.xy_sum = np.float64(0)

    def update(self, val):
        val = np.float64(val)
        self.barv.append(val)
        self.xy_sum = self.xy_sum - self.y_sum
        self.x2_sum = self.x2_sum + self.i_sum - 2 * self.x_sum
        self.x_sum = self.x_sum - self.i_sum
        front = self.barv[0]
        if not np.isnan(front):
            self.i_sum -= 1
            self.y_sum -= front
            self.y2_sum -= front * front
        else:
            self.na_count -= 1
        self.barv.popleft()
        if np.isnan(val):
            self.na_count += 1
        else:
            self.i_sum += 1
            self.x_sum += self.window
            self.x2_sum += self.window * self.window
            self.y_sum += val
            self.y2_sum += val * val
            self.xy_sum += self.window * val
        N = np.float64(self.window - self.na_count)
        with np.errstate(all="ignore"):
            slope = (N * self.xy_sum - self.x_sum * self.y_sum) / (N * self.x2_sum - self.x_sum * self.x_sum)
            interp = self.y_sum / N - slope * (self.x_sum / N)
            resi = val - (slope * self.window + interp)
            r = (N * self.xy_sum - self.x_sum * self.y_sum) / np.sqrt(
                (N * self.x2_sum - self.x_sum * self.x_sum) * (N * self.y2_sum - self.y_sum * self.y_sum))
        return slope, r * r, resi


@pytest.mark.parametrize("n", q.WINDOWS)
def test_slope_rsquare_resi_match_a_port_of_qlibs_cython(n):
    x, _ = _series()
    cy = _CySlopeFamily(n)
    ref = np.array([cy.update(v) for v in x])
    ref_rsq = ref[:, 1].copy()
    ref_rsq[np.isclose(pd.Series(x).rolling(n, min_periods=1).std(), 0, atol=2e-05)] = np.nan   # ops.py Rsquare
    slope, rsq, resi = q.rolling_regression(x, n)
    for got, want in ((slope, ref[:, 0]), (rsq, ref_rsq), (resi, ref[:, 2])):
        assert np.allclose(got, want, rtol=1e-9, atol=1e-9, equal_nan=True)


def test_the_lookahead_property_bit_for_bit():
    bars = _bars(900, seed=11)
    full = q.alpha158_from_bars(bars)
    for t in [0, 1, 4, 5, 59, 60, 61, 333, 899]:
        cut = q.alpha158_from_bars(bars[: t + 1])[-1]
        assert q.canonical_bytes(full[t]) == q.canonical_bytes(cut), t
    # and the check can fail: a feature that peeks one bar ahead is caught
    leaky = np.concatenate([full[1:, 0], [np.nan]])
    assert q.canonical_bytes(leaky[:5]) != q.canonical_bytes(full[:5, 0])


def test_feature_fingerprint_is_stable_within_a_process():
    assert q.feature_fingerprint() == q.feature_fingerprint()


# ---- rows, labels, split ------------------------------------------------------------------------

def _session(date, n=75, base=100.0, seed=0):
    rng = random.Random(int(date.replace("-", "")) * 100 + seed)
    t = datetime.strptime(date + " 09:15", "%Y-%m-%d %H:%M")
    out, p = [], base
    for i in range(n):
        o = p
        p = p * (1 + rng.gauss(0, 0.004))
        out.append({"time": (t + timedelta(minutes=5 * i)).isoformat(), "open": o, "high": max(o, p) * 1.001,
                    "low": min(o, p) * 0.999, "close": p, "volume": 1000 + rng.randint(0, 5000)})
    return out


def test_training_rows_are_the_46_bars_closing_0945_to_1330_for_members_only():
    starts = q.train_bar_starts()
    assert len(starts) == 46 and list(starts)[0] == "09:40" and list(starts.values())[-1] == "13:30"
    days = ["2025-01-01", "2025-01-02"]
    flat = {"AAA": _session(days[0]) + _session(days[1]), "BBB": _session(days[0]) + _session(days[1], n=60)}
    by_day = {s: k.by_session(c) for s, c in flat.items()}
    members = {days[0]: {"AAA", "BBB"}, days[1]: {"AAA"}}
    rows = q.training_stock_times(flat, by_day, days, members, {"AAA": [days[0]]})
    assert [r[1] for r in rows].count(days[0]) == 46 and all(r[0] == "BBB" for r in rows if r[1] == days[0])
    assert [r[1] for r in rows].count(days[1]) == 46 and all(r[0] == "AAA" for r in rows if r[1] == days[1])
    assert rows == sorted(rows, key=lambda r: (r[1], r[2], r[0]))
    first = rows[0]
    assert first[2] == "09:45" and flat[first[0]][first[3]]["time"].endswith("09:40:00")
    # a short session: targets that would leave it are None (dropped per horizon)
    short = {"CCC": _session(days[0], n=50)}
    r2 = q.training_stock_times(short, {"CCC": k.by_session(short["CCC"])}, [days[0]], {days[0]: {"CCC"}}, {})
    ys, ends = q.labels(r2, {"CCC": k.by_session(short["CCC"])})
    assert ys["f15"][-1] is None and ys["f15"][0] is not None and ends["f15"][0][:10] == days[0]
    i = r2[0][4]
    bars = short["CCC"]
    assert ys["f30"][0] == pytest.approx((bars[i + 6]["close"] - bars[i + 1]["open"]) / bars[i + 1]["open"] * 1e4)


def test_labels_are_ranked_across_stocks_at_each_timestamp_like_csranknorm():
    vals = [5.0, 1.0, 1.0, 3.0, 10.0, -2.0, 7.0]
    keys = ["t1", "t1", "t1", "t1", "t2", "t2", "t2"]
    got = q.cs_rank_labels(vals, keys)
    want_pct = [4 / 4, 1.5 / 4, 1.5 / 4, 3 / 4, 3 / 3, 1 / 3, 2 / 3]
    assert np.allclose(got, [(p - 0.5) * 3.46 for p in want_pct])


def _calendar(start="2024-09-20", end="2025-12-31"):
    d, out = datetime.strptime(start, "%Y-%m-%d"), []
    while d <= datetime.strptime(end, "%Y-%m-%d"):
        if d.weekday() < 5:
            out.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return out


def test_split_is_training_then_a_five_session_purge_then_the_last_40_sessions():
    cal = _calendar()
    sp = q.split_sessions(cal)
    assert sp["window"][0] == "2024-09-20" and sp["window"][-1] == "2025-08-14"
    assert len(sp["validation"]) == 40 and sp["validation"][-1] == "2025-08-14"
    assert len(sp["purge"]) == 5 and sp["train"] + sp["purge"] + sp["validation"] == sp["window"]
    assert len(q.sessions_between(cal, sp["train"][-1], sp["validation"][0])) == 5
    # L40 starts 2025-09-01: 11 weekday sessions sit between the last validation label and it
    assert len(q.sessions_between(cal, "2025-08-14", "2025-09-01")) >= q.MIN_GAP_TO_L40
    with pytest.raises(ValueError):
        q.split_sessions(cal[:30])


# ---- normaliser --------------------------------------------------------------------------------

def test_the_normaliser_is_qlibs_robust_zscore_fitted_on_training_rows_only():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 3))
    X[5, 1] = np.nan
    X[7, 2] = np.inf
    dates = ["2025-01-%02d" % (1 + i % 20) for i in range(200)]
    train = sorted(set(dates))
    stats = q.fit_normaliser(X, dates, train)
    med = np.nanmedian(X, axis=0)
    assert np.allclose(stats["median"], med)
    assert np.allclose(stats["std"], (np.nanmedian(np.abs(X - med), axis=0) + 1e-12) * 1.4826)
    with pytest.raises(AssertionError):
        q.fit_normaliser(X, dates, train[:-1])          # a row from outside training is refused
    Y = X.copy()
    q.apply_normaliser(Y, stats)
    assert Y[5, 1] == 0.0 and Y[7, 2] == 3.0 and np.abs(Y).max() <= 3.0
    z = (X[0] - np.array(stats["median"])) / np.array(stats["std"])
    assert np.allclose(Y[0], np.clip(z, -3, 3))
    assert q.same_stats(stats, json.loads(json.dumps(stats)))


# ---- freezing and the gate ----------------------------------------------------------------------

def _freeze(tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    files = {}
    for name in q.expected_frozen_files():
        (models / name).write_text("content of %s" % name)
        files[name] = q.sha256_file(str(models / name))
    frozen = tmp_path / "l47_frozen.json"
    frozen.write_text(json.dumps({"files": files, "feature_fingerprint": "x"}))
    return str(frozen), str(models)


def test_the_hash_check_passes_on_the_frozen_files_and_refuses_a_changed_one(tmp_path):
    frozen, models = _freeze(tmp_path)
    assert q.verify_frozen(frozen, models)["files"]
    with open(os.path.join(models, q.model_file("f30")), "a") as f:
        f.write(" ")
    with pytest.raises(RuntimeError, match="hash mismatch"):
        q.verify_frozen(frozen, models)


def test_the_hash_check_refuses_a_missing_record_or_file(tmp_path):
    with pytest.raises(RuntimeError):
        q.verify_frozen(str(tmp_path / "absent.json"), str(tmp_path))
    frozen, models = _freeze(tmp_path)
    os.remove(os.path.join(models, q.NORMALISER_FILE))
    with pytest.raises(RuntimeError, match="missing"):
        q.verify_frozen(frozen, models)


def _summary(p, mean=40.0, t=5.0):
    return {"sessions": 78, "spread": {"mean": mean, "t": t, "p": p, "halves": [{"mean": 30.0}, {"mean": 50.0}]},
            "pic": {"mean": 0.05, "t": 3.0}, "ic": {"mean": 0.05, "t": 3.0},
            "top": {"mean": 20.0, "t": 3.0}, "bottom": {"mean": -20.0, "t": -3.0}}


def test_the_night_gate_runs_bh_across_24_with_voids_at_p_one():
    l40 = {"status": "DONE", "result": {"summaries": {h: _summary(0.5, 1.0, 0.5) for h in k.HORIZONS}}}
    l46 = {"chronos_bolt": {"status": "DONE", "result": {"summaries": {h: _summary(0.3, -2.0, -1.0) for h in k.HORIZONS}}},
           "sundial": {"status": "VOID"}}
    strong = {h: _summary(1e-6) for h in k.HORIZONS}
    night = q.night_gate(l40, l46, strong)
    assert len(night["p"]) == 24 and night["p"]["L46:sundial:f60"] == 1.0 and night["p"]["L46:tirex:f15"] == 1.0
    assert night["status"]["L46:tirex"] == "NOT RUN"
    assert all(night["bh_survives"]["L47:%s" % h] for h in k.HORIZONS)
    v = q.verdict(strong, night)
    assert all(v[h]["passes"] for h in k.HORIZONS)
    # three tests at p = 0.02 survive BH within L47's three (0.02 <= 0.10) but not across the
    # night's 24 (rank 3 needs p <= 0.10 * 3 / 24 = 0.0125): the verdict needs both
    weak = {h: _summary(0.02) for h in k.HORIZONS}
    nw = q.night_gate(l40, l46, weak)
    vw = q.verdict(weak, nw)
    assert all(vw[h]["l40_section8_and_bh_within_3"]["checks"]["bh_survives"] for h in k.HORIZONS)
    assert not any(vw[h]["passes"] for h in k.HORIZONS)


def test_score_refuses_after_the_cutoff_unless_the_owner_approved():
    class A(object):
        owner_approved_after_cutoff = False
    before = datetime(2026, 9, 30, 7, 29, tzinfo=q.IST)
    after = datetime(2026, 9, 30, 7, 30, tzinfo=q.IST)
    assert q.guard_cutoff(A(), before)["after_cutoff_owner_approved"] is False
    with pytest.raises(SystemExit):
        q.guard_cutoff(A(), after)
    A.owner_approved_after_cutoff = True
    assert q.guard_cutoff(A(), after)["after_cutoff_owner_approved"] is True


# ---- the loader ----------------------------------------------------------------------------------

class _FakeKiteHistory(object):
    def __init__(self, path):
        self.path = path

    def _conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c


def test_the_loader_reads_nothing_on_or_after_2026_01_02(tmp_path):
    db = str(tmp_path / "c.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts INTEGER, open REAL, high REAL, low REAL, "
                "close REAL, volume INTEGER)")
    cut = q.READ_BEFORE_TS
    for ts in (cut - 600, cut - 300, cut, cut + 300):
        con.execute("INSERT INTO candles VALUES ('AAA','5m',?,1,1,1,1,1)", (ts,))
    con.commit()
    bars, max_ts = q.load_bars(_FakeKiteHistory(db), ["AAA", "ZZZ"])
    assert list(bars) == ["AAA"] and len(bars["AAA"]) == 2 and max_ts == cut - 300
    assert bars["AAA"][-1]["time"] == "2026-01-01T23:55:00"          # IST, whatever the machine's zone
    assert q.READ_BEFORE == "2026-01-02"


def test_the_loader_halts_if_a_later_bar_comes_back():
    class Conn(object):
        def execute(self, *a):
            class R(object):
                def fetchall(self_inner):
                    return [(q.READ_BEFORE_TS + 300, 1, 1, 1, 1, 1)]
            return R()

    class KH(object):
        def _conn(self):
            return Conn()
    with pytest.raises(q.CutoffViolation):
        q.load_bars(KH(), ["AAA"])


# ---- the positive control on synthetic validation data --------------------------------------------

def test_the_positive_control_clears_the_bar_and_m60_matches_the_harness():
    days = _calendar("2025-06-02", "2025-06-30")[:12]
    flat, by_day = {}, {}
    for j in range(22):
        bars = []
        for d in days:
            bars += _session(d, seed=j, base=100.0 + j)
        flat["S%02d" % j] = bars
        by_day["S%02d" % j] = k.by_session(bars)
    members = {d: set(flat) for d in days}
    samples = k.build_samples(flat, by_day, days[-4:], members, {})
    assert samples
    pc = q.positive_control(samples, flat, by_day)
    assert pc["passes"], pc
    assert pc["m60_worst_abs_diff_bp"] < 1e-9 and not pc["m60_mismatches"]


# ---- LightGBM (skipped where it is not installed; the Mac's venv has none) -------------------------

def test_lightgbm_trains_with_the_prereg_parameters_and_stops_on_validation():
    lgb = pytest.importorskip("lightgbm", reason="lightgbm is not installed in this environment (the PC has it)")
    rng = np.random.default_rng(1)
    X = rng.normal(size=(3000, 6))
    y = X[:, 0] * 0.5 + rng.normal(size=3000)
    b1, ev = q.train_one(X[:2000], y[:2000], X[2000:], y[2000:])
    b2, _ = q.train_one(X[:2000], y[:2000], X[2000:], y[2000:])
    assert 1 <= b1.best_iteration <= q.NUM_BOOST_ROUND and "l2" in ev["valid"]
    assert b1.model_to_string() == b2.model_to_string()                 # deterministic
    assert b1.params["num_leaves"] == 210 and b1.params["seed"] == 123
    assert lgb.__version__


# ---- isolation ------------------------------------------------------------------------------------

def test_the_module_imports_no_heavy_package_at_import_time():
    code = ("import sys; import research.qlib_alpha158_l47; "
            "print(','.join(m for m in ('numpy', 'pandas', 'lightgbm', 'scipy', 'torch') if m in sys.modules))")
    backend = os.path.dirname(os.path.dirname(os.path.abspath(q.__file__)))
    out = subprocess.run([sys.executable, "-c", code], cwd=backend, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == ""


def test_commands_refuse_to_run_on_the_mac(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("L47_ALLOW_MAC", raising=False)
    with pytest.raises(SystemExit, match="PC only"):
        q.guard_platform()


# ---- amendment 1 (review finding B2): +-inf is missing, as it is to pandas' rolling functions ------

def _with_infs(n=160, seed=5):
    x, y = _series(n=n, seed=seed)
    y[[20, 21, 60, 130]] = np.inf
    y[[90]] = -np.inf
    x[[45]] = np.inf
    return x, y


@pytest.mark.parametrize("n", q.WINDOWS)
def test_corr_skips_an_infinite_pair_like_pandas_plus_qlibs_mask(n):
    x, y = _with_infs()
    sx, sy = pd.Series(x), pd.Series(y)
    ref = sx.rolling(n, min_periods=1).corr(sy)
    ref[np.isclose(sx.rolling(n, min_periods=1).std(), 0, atol=2e-05)
        | np.isclose(sy.rolling(n, min_periods=1).std(), 0, atol=2e-05)] = np.nan
    got = q.rolling_corr(x, y, n)
    assert np.allclose(got, ref, rtol=0, atol=1e-10, equal_nan=True)
    assert np.isfinite(got[25:30]).all() or n > 5       # a window holding an inf is not NaN as a whole


@pytest.mark.parametrize("n", q.WINDOWS)
def test_mean_sum_std_skip_infinite_values_like_pandas(n):
    _, y = _with_infs()
    sy = pd.Series(y)
    assert np.allclose(q.rolling_mean(y, n), sy.rolling(n, min_periods=1).mean(), rtol=0, atol=1e-12, equal_nan=True)
    assert np.allclose(q.rolling_sum(y, n)[0], sy.rolling(n, min_periods=1).sum(), rtol=0, atol=1e-12, equal_nan=True)
    assert np.allclose(q.rolling_std(y, n), sy.rolling(n, min_periods=1).std(), rtol=0, atol=1e-12, equal_nan=True)


def test_cord_after_a_zero_volume_bar_differs_from_qlibs_pandas_only_by_pandas_float_error():
    """B2: after a zero-volume bar CORD skips the infinite pair instead of going NaN. Against
    Qlib's own pandas computation the port then differs in two ways only: pandas' float error
    where both are finite, and windows whose paired values of an input are constant (an
    undefined correlation: the port gives NaN, pandas a version-dependent value). Exactness
    is the hand check's job."""
    bars = _bars(3000, seed=21)
    F = q.alpha158_from_bars(bars)
    c = np.array([b["close"] for b in bars], dtype="float64")
    v = np.array([b["volume"] for b in bars], dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        left, right = c / q._shift(c, 1), np.log(v / q._shift(v, 1) + 1)
    assert np.isinf(right).sum() > 100                    # zero-volume bars followed by trading
    for n in q.WINDOWS:
        got = F[:, q.FEATURE_NAMES.index("CORD%d" % n)]
        assert q.canonical_bytes(got) == q.canonical_bytes(q.rolling_corr(left, right, n))
        diff = q.corr_differences(left, right, n)
        assert diff["other"] == 0 and diff["both_finite"] > 1000, (n, diff)
        assert diff["max_abs_diff_both_finite"] < 1e-3, (n, diff)
        theirs = q.qlib_pandas_corr(left, right, n)
        for t in np.where(np.isnan(got) & ~np.isnan(theirs))[0]:     # pandas' version-dependent value
            w = slice(max(0, t - n + 1), t + 1)
            ok = np.isfinite(left[w]) & np.isfinite(right[w])
            assert np.ptp(left[w][ok]) == 0 or np.ptp(right[w][ok]) == 0
        holds_inf = pd.Series(np.isinf(right).astype(float)).rolling(n, min_periods=1).max().to_numpy() > 0
        assert np.isfinite(got[holds_inf]).sum() > 50, n  # before amendment 1 every one of these was NaN


def test_corr_vs_pandas_is_recorded_by_kind_for_every_window():
    bars = {"AAA": _bars(400, seed=2), "BBB": _bars(300, seed=4)}
    out = q.corr_vs_pandas(bars)
    assert out["zero_volume_bars"] == sum(1 for b in bars["AAA"] + bars["BBB"] if b["volume"] == 0)
    assert all(out["%s%d" % (op, d)]["other"] == 0 for op in ("CORR", "CORD") for d in q.WINDOWS)


def test_the_hand_calculation_treats_non_finite_values_as_missing():
    assert q._std([1.0, float("inf"), 3.0]) == pytest.approx(math.sqrt(2.0))
    assert q._sum([1.0, float("-inf"), 2.0]) == 3.0
    assert q._pearson([1.0, 2.0, 3.0, 4.0], [2.0, float("inf"), 6.0, 8.0]) == pytest.approx(1.0)
    assert math.isnan(q._pearson([1.1, 1.1, 1.1, 2.0], [0.3, 0.3, 0.3, float("inf")]))   # constant once paired


def test_corr_is_nan_where_the_paired_values_of_an_input_are_constant():
    # the unpaired x varies (std > 2e-5, no mask) but the pairs left after the inf all share x
    x = np.array([1.1, 1.1, 1.1, 1.1, 2.0])
    y = np.array([0.1, 0.2, 0.7, 0.5, np.inf])
    assert math.isnan(q.rolling_corr(x, y, 5)[-1])
    third = np.array([1.0 / 3] * 4 + [5.0])              # a non-dyadic constant: the mean may round off it
    assert math.isnan(q.rolling_corr(third, y, 5)[-1])


# ---- amendment 1 (review finding B1): the one-run rule, train side --------------------------------

class _Args(object):
    def __init__(self, **kw):
        self.refit_reason = None
        self.owner_approved_after_cutoff = True      # tests do not depend on the wall clock
        self.owner_approved_rescore = None
        self.l40_result = None
        self.l46_dir = None
        self.l40_rows = None
        self.__dict__.update(kw)


@pytest.fixture
def paths(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    for name, value in (("STAGE0", data / "l47_stage0.json"), ("FROZEN", data / "l47_frozen.json"),
                        ("RESULT", data / "l47_result.json"), ("TRAIN_STARTED", data / "l47_train_started.json"),
                        ("MODELS_DIR", tmp_path / "models"), ("ROWS", tmp_path / "l47_rows.jsonl")):
        monkeypatch.setattr(q, name, str(value))
    monkeypatch.setattr(q, "guard_platform", lambda: None)
    monkeypatch.setattr(q, "in_head", lambda p: False)
    monkeypatch.setattr(q, "committed_at_head", lambda p: True)
    (data / "l47_stage0.json").write_text(json.dumps({"status": "STAGE0_DONE", "stage0": {}}))
    return tmp_path


def test_train_refuses_without_a_done_stage0(paths):
    os.remove(q.STAGE0)
    with pytest.raises(SystemExit, match="STAGE0_DONE"):
        q.train_guards(_Args(refit_reason="x"))


def test_train_refuses_even_with_a_reason_once_the_frozen_record_is_committed(paths, monkeypatch):
    monkeypatch.setattr(q, "in_head", lambda p: p == q.FROZEN)
    with pytest.raises(SystemExit, match="frozen"):
        q.train_guards(_Args(refit_reason="a declared bug"))


@pytest.mark.parametrize("which", ["RESULT", "ROWS", "ROWS_TMP"])
def test_train_refuses_even_with_a_reason_once_scoring_has_started(paths, which):
    path = q.ROWS + ".tmp" if which == "ROWS_TMP" else getattr(q, which)
    with open(path, "w") as f:
        f.write("{}")
    with pytest.raises(SystemExit, match="scoring pass has started"):
        q.train_guards(_Args(refit_reason="a declared bug"))


@pytest.mark.parametrize("left", ["train_started", "model_file", "frozen_uncommitted"])
def test_an_earlier_training_attempt_needs_a_recorded_reason(paths, left):
    if left == "train_started":
        with open(q.TRAIN_STARTED, "w") as f:
            json.dump({"status": "TRAIN_STARTED", "started": "t"}, f)
    elif left == "model_file":
        os.makedirs(q.MODELS_DIR)
        open(os.path.join(q.MODELS_DIR, q.model_file("f15")), "w").close()
    else:
        with open(q.FROZEN, "w") as f:
            json.dump({"files": {}}, f)
    with pytest.raises(SystemExit, match="refit-reason"):
        q.train_guards(_Args())
    previous = q.train_guards(_Args(refit_reason="crash before freezing"))
    assert previous and len(previous) == 1


def test_a_first_training_needs_no_reason(paths):
    assert q.train_guards(_Args()) is None


def test_train_writes_its_started_marker_before_the_first_lgb_train(paths, monkeypatch):
    rows_tr = [("AAA", "2025-01-0%d" % d, "09:45", d, 5) for d in range(1, 6)]
    rows_va = [("AAA", "2025-02-01", "09:45", 9, 5)]

    def fake_features(flat, req):
        return np.array([[float((r * 7 + j) % 11) for j in range(q.N_FEATURES)] for r, _ in enumerate(req)])

    class FakeData(object):
        def __init__(self, kh, before_ts):
            self.rows_tr, self.rows_va, self.flat_by_sym = rows_tr, rows_va, {}
            self.split = {"train": sorted({r[1] for r in rows_tr})}
            self.y_tr = {h: [1.0] * len(rows_tr) for h in q.HORIZONS}
            self.y_va = {h: [1.0] for h in q.HORIZONS}

        def describe(self):
            return {"sessions": {"train": 1, "validation": 1}, "rows": {"train": 5}}

    norm = q.fit_normaliser(fake_features(None, rows_tr), [r[1] for r in rows_tr], [r[1] for r in rows_tr])
    with open(q.STAGE0, "w") as f:
        json.dump({"status": "STAGE0_DONE", "stage0": {"data": FakeData(None, None).describe(),
                                                       "4_purge": {"normaliser": norm}}}, f)
    monkeypatch.setattr(q, "Data", FakeData)
    monkeypatch.setattr(q, "feature_rows", fake_features)
    monkeypatch.setattr(q, "_kite_history", lambda: object())
    monkeypatch.setitem(sys.modules, "lightgbm", type(sys)("lightgbm"))

    def first_lgb_train(*a, **kw):
        assert os.path.exists(q.TRAIN_STARTED)
        raise RuntimeError("crash inside the first lgb.train")
    monkeypatch.setattr(q, "train_one", first_lgb_train)
    with pytest.raises(RuntimeError, match="first lgb.train"):
        q.run_train(_Args())
    marker = json.load(open(q.TRAIN_STARTED))
    assert marker["status"] == "TRAIN_STARTED" and marker["started"] and marker["environment"]
    assert not os.path.exists(q.FROZEN)
    with pytest.raises(SystemExit, match="refit-reason"):
        q.train_guards(_Args())


# ---- amendment 1 (review findings B1, N5-N7): the one-run rule, score side --------------------------

@pytest.fixture
def score_env(paths, monkeypatch):
    os.makedirs(q.MODELS_DIR)
    files = {}
    for name in q.expected_frozen_files():
        with open(os.path.join(q.MODELS_DIR, name), "w") as f:
            f.write("model %s" % name)
        files[name] = q.sha256_file(os.path.join(q.MODELS_DIR, name))
    with open(q.FROZEN, "w") as f:
        json.dump({"files": files, "stage0_sha256": q.sha256_file(q.STAGE0),
                   "feature_fingerprint": q.feature_fingerprint(),
                   "horizons": {h: {"best_iteration": 7} for h in q.HORIZONS}}, f)
    l40 = paths / "kronos_l40_result.json"
    l40.write_text(json.dumps({"status": "DONE", "stage0": {"adjustment": {"dropped_stock_sessions": {}}}}))
    l46 = paths / "l46"
    l46.mkdir()
    from research.tsfm_family_ic import MODELS
    for j, m in enumerate(MODELS):
        (l46 / ("l46_%s_result.json" % m)).write_text(json.dumps({"status": "VOID" if j == 5 else "DONE"}))
    fake = type(sys)("lightgbm")
    fake.__spec__ = importlib.machinery.ModuleSpec("lightgbm", None)
    monkeypatch.setitem(sys.modules, "lightgbm", fake)
    return _Args(l40_result=str(l40), l46_dir=str(l46))


def test_score_guards_pass_on_a_frozen_committed_complete_record(score_env):
    frozen, l40, l46, record = q.score_guards(score_env)
    assert frozen["files"] and l40["status"] == "DONE" and len(l46) == 6 and "rescore" not in record


@pytest.mark.parametrize("status", ["STARTED", "HALTED", "DONE", "anything"])
def test_score_refuses_if_a_result_exists_with_any_status(score_env, status):
    with open(q.RESULT, "w") as f:
        json.dump({"status": status}, f)
    with pytest.raises(SystemExit, match="runs once"):
        q.score_guards(score_env)
    score_env.owner_approved_rescore = "owner: the PC lost power mid-pass"
    _, _, _, record = q.score_guards(score_env)
    assert record["rescore"]["reason"] == "owner: the PC lost power mid-pass"
    assert record["rescore"]["previous"]["status"] == status


def test_score_refuses_an_unreadable_result_too(score_env):
    with open(q.RESULT, "w") as f:
        f.write("{half a json")
    with pytest.raises(SystemExit, match="runs once"):
        q.score_guards(score_env)


def test_score_refuses_a_frozen_record_that_is_not_committed(score_env, monkeypatch):
    monkeypatch.setattr(q, "committed_at_head", lambda p: p != q.FROZEN)
    with pytest.raises(SystemExit, match="not committed"):
        q.score_guards(score_env)


def test_score_refuses_a_stage0_record_that_is_not_committed(score_env, monkeypatch):
    monkeypatch.setattr(q, "committed_at_head", lambda p: p != q.STAGE0)
    with pytest.raises(SystemExit, match="l47_stage0.json is not committed"):
        q.score_guards(score_env)


def test_score_refuses_a_stage0_record_other_than_the_one_training_followed(score_env):
    with open(q.STAGE0, "a") as f:
        f.write(" ")
    with pytest.raises(SystemExit, match="stage0_sha256"):
        q.score_guards(score_env)


def test_score_refuses_changed_feature_code(score_env, monkeypatch):
    monkeypatch.setattr(q, "feature_fingerprint", lambda: "different")
    with pytest.raises(SystemExit, match="feature code"):
        q.score_guards(score_env)


def test_score_refuses_while_l46_has_not_finished(score_env):
    from research.tsfm_family_ic import MODELS
    path = os.path.join(score_env.l46_dir, "l46_%s_result.json" % list(MODELS)[2])
    with open(path, "w") as f:
        json.dump({"status": "STARTED"}, f)
    with pytest.raises(SystemExit, match="L46 has not finished"):
        q.score_guards(score_env)
    os.remove(path)
    with pytest.raises(SystemExit, match="L46 has not finished"):
        q.score_guards(score_env)


def test_score_refuses_without_l40s_result_or_a_named_l40_rows_file(score_env):
    score_env.l40_rows = score_env.l40_result + ".absent"
    with pytest.raises(SystemExit, match="l40-rows"):
        q.score_guards(score_env)
    os.remove(score_env.l40_result)
    with pytest.raises(SystemExit, match="L40's result"):
        q.score_guards(score_env)


def test_score_writes_started_before_any_bar_is_read(score_env, monkeypatch):
    class NoBars(object):
        def _conn(self):
            raise RuntimeError("a bar was about to be read")
    monkeypatch.setattr(q, "_kite_history", lambda: NoBars())
    with pytest.raises(RuntimeError, match="about to be read"):
        q.run_score(score_env)
    doc = json.load(open(q.RESULT))
    assert doc["status"] == "STARTED" and doc["score"]["started"] and doc["score"]["frozen_files_verified"]
    with pytest.raises(SystemExit, match="runs once"):
        q.score_guards(score_env)


def test_adjustment_drops_and_l40_rows_counts_are_compared_as_l40_recorded(tmp_path):
    assert q._dropped_as_sets({"A": ["2025-09-02", "2025-09-01"], "B": []}) == q._dropped_as_sets({"A": ["2025-09-01", "2025-09-02"]})
    assert q._dropped_as_sets({}) != q._dropped_as_sets({"A": ["2025-09-01"]})
    rows = tmp_path / "rows.jsonl"
    rows.write_text("\n".join(json.dumps({"date": d}) for d in ["2025-09-01"] * 3 + ["2025-09-02"] * 2) + "\n")
    assert q.l40_rows_per_session(str(rows)) == {"2025-09-01": 3, "2025-09-02": 2}


def test_prediction_ties_counts_distinct_values_and_ties_across_the_quintile_cuts(tmp_path):
    rows = []
    for j in range(25):                                  # 25 stocks: quintiles of 5
        v = 0.0 if j < 8 else float(j)                   # 8 tied at the bottom, across the 5/6 cut
        rows.append({"date": "2025-09-01", "m60": 1.0, "targets": {h: 1.0 for h in q.HORIZONS},
                     "features": {h: v for h in q.HORIZONS}})
    for j in range(25):
        rows.append({"date": "2025-09-02", "m60": 1.0, "targets": {h: 1.0 for h in q.HORIZONS},
                     "features": {h: float(j) for h in q.HORIZONS}})
    for j in range(5):                                   # below MIN_STOCKS: ignored, as evaluate_rows does
        rows.append({"date": "2025-09-03", "m60": 1.0, "targets": {h: 1.0 for h in q.HORIZONS},
                     "features": {h: 0.0 for h in q.HORIZONS}})
    path = tmp_path / "rows.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    t = q.prediction_ties(str(path))["f15"]
    assert t["sessions"] == 2 and t["distinct_predictions_per_session"] == {"median": 21.5, "min": 18}
    assert t["share_tied_at_bottom_cut"] == pytest.approx(8 / 50) and t["share_tied_at_top_cut"] == 0
    assert t["sessions_with_a_tie_across_the_bottom_cut"] == 1


def test_lightgbm_runs_column_wise_for_determinism():
    assert q.LGB_PARAMS["force_col_wise"] is True and q.LGB_PARAMS["deterministic"] is True
