"""Research look L51 (docs/research/prereg-index-timing.md): the parts that decide
something, on small synthetic data only. No cache, panel or index database is read."""
import ast
import json
import math
import os
import sqlite3
from datetime import date, datetime, timedelta

import pytest

from research import index_timing_l51 as L

np = pytest.importorskip("numpy")
pytest.importorskip("pandas")

HERE = os.path.dirname(os.path.abspath(__file__))


# ---- constants the prereg fixes --------------------------------------------------------------

def test_cost_is_computed_with_costs_py_and_matches_the_prereg():
    assert round(L.COST_BP, 2) == 6.95
    charges = L.round_trip_bp(dict(L.FUTURES_COSTS, slippage_pct=0.0))
    assert round(charges, 2) == 5.95
    assert round(L.round_trip_bp(dict(L.FUTURES_COSTS_2025, slippage_pct=0.0)), 2) == 2.92
    assert round(L.COST_BP_2025, 2) == 3.92


def test_grid_and_training_bars():
    assert [L.bar_close_hhmm(i) for i in L.GRID["h30"]] == [
        "09:45", "10:15", "10:45", "11:15", "11:45", "12:15", "12:45", "13:15", "13:45", "14:15", "14:45"]
    assert [L.bar_close_hhmm(i) for i in L.GRID["h60"]] == ["09:45", "10:45", "11:45", "12:45", "13:45"]
    assert L.bar_close_hhmm(L.GRID["h30"][-1] + 6) == "15:15"
    assert L.bar_close_hhmm(L.GRID["h60"][-1] + 12) == "14:45"
    for h, kb in L.HORIZONS.items():
        tb = L.train_bars(kb)
        assert L.bar_close_hhmm(tb[0]) == "09:45"
        assert L.bar_close_hhmm(tb[-1] + kb) == "15:15"
        assert set(L.GRID[h]) <= set(tb)
    assert len(L.train_bars(6)) == 61 and len(L.train_bars(12)) == 55
    assert len(L.FACTORS) == 23 and len(L.PREDICTORS) == 92
    assert len(L.ALPHAS) == 15 and L.ALPHAS[0] == pytest.approx(1e-3) and L.ALPHAS[-1] == pytest.approx(1e4)


def test_need_is_eighty_percent_rounded_up():
    assert [L.need(w) for w in (5, 21, 60, 250, 252)] == [4, 17, 48, 200, 202]


# ---- loaders, on throwaway databases ----------------------------------------------------------

def _epoch(day, hhmm):
    return int(datetime.fromisoformat("%sT%s" % (day, hhmm)).replace(tzinfo=L.IST).timestamp())


def test_load_stock_bars_places_bars_and_excludes_the_held_out_window(tmp_path):
    db = str(tmp_path / "k.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts INTEGER, open REAL, high REAL, low REAL, "
                "close REAL, volume INTEGER)")
    rows = [("AAA", "5m", _epoch("2025-12-31", "09:15"), 10, 0, 0, 11, 1),
            ("AAA", "5m", _epoch("2025-12-31", "15:25"), 12, 0, 0, 13, 1),
            ("BBB", "5m", _epoch("2025-12-31", "09:20"), 20, 0, 0, 21, 1),
            ("AAA", "5m", _epoch("2026-01-01", "09:15"), 98, 0, 0, 98, 1),
            ("AAA", "5m", _epoch("2026-01-02", "09:15"), 99, 0, 0, 99, 1)]
    con.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    before = os.path.getmtime(db)
    dates, syms, O, C, info = L.load_stock_bars(db, start="2025-12-01")      # default end: 2026-01-01 (N5)
    assert dates == ["2025-12-31"] and syms == ["AAA", "BBB"] and L.DATA_END == "2026-01-01"
    assert O[0, 0, 0] == 10 and C[0, 0, 0] == 11 and C[0, 74, 0] == 13 and O[0, 1, 1] == 20
    assert np.isnan(O[0, 1, 0]) and info["rows"] == 3 and info["max_ts_ist"] < "2026-01-01"
    assert os.path.getmtime(db) == before


def test_aggregate_index_minutes_is_start_labelled():
    rows = []
    for m in range(0, 375):
        t = datetime(2025, 3, 3, 9, 15) + timedelta(minutes=m)
        rows.append((t.strftime("%Y-%m-%d %H:%M"), 1000 + m, 1000.5 + m))
    out = L.aggregate_index_minutes(rows)
    opens, closes, minutes = out["2025-03-03"]
    assert minutes == 375
    assert opens[0] == 1000 and closes[0] == 1004.5          # 09:15 open, 09:19 close
    assert opens[1] == 1005 and closes[74] == 1000.5 + 374    # 09:20 open, 15:29 close
    missing = [r for r in rows if r[0][11:16] != "09:19"]
    opens2, closes2, minutes2 = L.aggregate_index_minutes(missing)["2025-03-03"]
    assert closes2[0] is None and minutes2 == 374


def test_load_index_bars_reads_only_the_index_and_before_the_cut(tmp_path):
    db = str(tmp_path / "o.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE bars (symbol TEXT, ts TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER)")
    con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?)", [
        ("NIFTY 50", "2025-12-31 09:15", 1, 0, 0, 2, 0), ("NIFTYBEES", "2025-12-31 09:15", 5, 0, 0, 6, 0),
        ("NIFTY 50", "2026-01-02 09:15", 9, 0, 0, 9, 0)])
    con.commit()
    con.close()
    bars, info = L.load_index_bars(db, start="2025-12-01", end="2026-01-02")
    assert list(bars) == ["2025-12-31"] and bars["2025-12-31"][0][0] == 1 and info["rows"] == 1


def test_fetch_spans_whole_days():
    ok = [{"symbol": "A", "from_date": "2025-01-01T00:00:00", "to_date": "2025-03-01T00:00:00", "fetched_at": 1}]
    bad = ok + [{"symbol": "B", "from_date": "2025-01-01T11:00:00", "to_date": "2025-03-01T00:00:00", "fetched_at": 1}]
    assert L.spans_are_whole_days(ok)["count_not_whole_days"] == 0
    assert L.spans_are_whole_days(bad)["count_not_whole_days"] == 1


# ---- factor construction -----------------------------------------------------------------------

def test_bar_returns_exclude_the_overnight_gap():
    O = np.array([100.0, 101.0, 102.0])
    C = np.array([101.0, 102.0, 100.0])
    r = L.bar_returns(O, C)
    assert r[0] == pytest.approx(0.01) and r[1] == pytest.approx(102 / 101 - 1) and r[2] == pytest.approx(100 / 102 - 1)


def test_tercile_groups_ties_and_minimum():
    vals = np.array([1.0, 1.0, 1.0] + list(range(3, 33)) + [np.nan])
    elig = np.ones(len(vals), dtype=bool)
    bottom, top = L.tercile_groups(vals, elig)
    assert len(bottom) == len(top) == 11
    assert list(bottom[:3]) == [0, 1, 2]                       # ties broken by column (symbol order)
    assert 33 not in top and 33 not in bottom                  # NaN is not ranked
    elig[:5] = False
    assert L.tercile_groups(vals, elig) is None                # 28 eligible < 30


def _synthetic_session(N=45, seed=3):
    rng = np.random.default_rng(seed)
    O = 100 + rng.standard_normal((L.BARS, N)).cumsum(0)
    C = O + rng.standard_normal((L.BARS, N)) * 0.1
    O[:, -1] = np.nan
    C[:, -1] = np.nan                                          # a stock with no bars
    C[10, 0] = np.nan                                          # one missing bar
    IO = 20000 + rng.standard_normal(L.BARS).cumsum()
    IC = IO + rng.standard_normal(L.BARS)
    chars = {name: rng.standard_normal(N) for name in L.CHARS}
    chars["MOM"][:20] = np.nan                                 # too few ranked -> missing factor
    members = np.ones(N, dtype=bool)
    members[5] = False
    sector_of = np.array(["Financial Services"] * 10 + ["Power"] * 6 + ["Other"] * (N - 16), dtype=object)
    return O, C, IO, IC, chars, members, sector_of


def test_session_factors_by_hand():
    O, C, IO, IC, chars, members, sector_of = _synthetic_session()
    F, ranked = L.session_factors(O, C, IO, IC, chars, members, sector_of)
    r = L.bar_returns(O, C)
    ri = L.bar_returns(IO, IC)
    j = 11
    vol = chars["VOL"]
    ok = [n for n in range(len(vol)) if members[n]]
    order = sorted(ok, key=lambda n: (vol[n], n))
    q = len(order) // 3

    def m(cols):
        v = [r[j, c] for c in cols if not math.isnan(r[j, c])]
        return sum(v) / len(v)

    assert F[j, L.FACTORS.index("VOL")] == pytest.approx(m(order[-q:]) - m(order[:q]), abs=1e-15)
    assert np.isnan(F[:, L.FACTORS.index("MOM")]).all() and ranked["MOM"] == 0
    ew = m(ok)
    fin = [n for n in ok if sector_of[n] == "Financial Services"]
    assert F[j, L.FACTORS.index("FIN")] == pytest.approx(m(fin) - ew, abs=1e-15)
    assert np.isnan(F[j, L.FACTORS.index("IT")])               # no member in that sector
    assert F[j, L.FACTORS.index("MKT")] == ri[j]
    assert F[j, L.FACTORS.index("EWX")] == pytest.approx(ew - ri[j], abs=1e-15)


def test_factors_and_predictors_ignore_later_bars():
    O, C, IO, IC, chars, members, sector_of = _synthetic_session()
    F, _ = L.session_factors(O, C, IO, IC, chars, members, sector_of)
    Fp, _ = L.session_factors(O[::-1].copy(), C[::-1].copy(), IO[::-1].copy(), IC[::-1].copy(), chars, members,
                              sector_of)
    for i in (5, 23, 60):
        O2, C2, IO2, IC2 = O.copy(), C.copy(), IO.copy(), IC.copy()
        O2[i + 1:] = np.nan
        C2[i + 1:] = 1e9
        IO2[i + 1:] = np.nan
        IC2[i + 1:] = -5
        F2, _ = L.session_factors(O2, C2, IO2, IC2, chars, members, sector_of)
        assert np.array_equal(np.nan_to_num(F[: i + 1]), np.nan_to_num(F2[: i + 1]))
        assert np.array_equal(L.predictors_at(F, Fp, i), L.predictors_at(F2, Fp, i))


def test_predictors_at_lags():
    F = np.arange(L.BARS * 23, dtype=float).reshape(L.BARS, 23)
    Fp = np.ones((L.BARS, 23))
    Fp[3, 2] = np.nan
    p = L.predictors_at(F, Fp, 9).reshape(23, 4)
    assert (p[:, 0] == F[9]).all()
    assert (p[:, 1] == F[4:10].sum(0)).all()
    assert (p[:, 2] == F[:10].sum(0)).all()
    assert p[2, 3] == 74 and p[0, 3] == 75                     # a missing previous bar counts as 0
    assert L.PREDICTORS[:4] == ["LIQ_last5", "LIQ_last30", "LIQ_sofar", "LIQ_prev"]


# ---- characteristics -----------------------------------------------------------------------------

def _panel(T=300, N=6, seed=5):
    rng = np.random.default_rng(seed)
    M = rng.standard_normal(T) * 0.01
    beta = np.linspace(0.5, 1.5, N)
    R = beta * M[:, None] + rng.standard_normal((T, N)) * 0.01
    C = 100 * np.cumprod(1 + R, axis=0)
    V = rng.uniform(1e8, 1e9, (T, N))
    H = C * (1 + rng.uniform(0, 0.02, (T, N)))
    Lo = C * (1 - rng.uniform(0, 0.02, (T, N)))
    C[T - 50, 1] = np.nan                                       # a missing day
    V[-3:, 2] = np.nan
    return C, V, H, Lo, M


def test_characteristics_against_direct_formulas():
    C, V, H, Lo, M = _panel()
    ch = L.characteristics(C, V, H, Lo, M)
    t = C.shape[0] - 1
    n = 0
    R = C[1:, n] / C[:-1, n] - 1
    assert ch["MOM"][n] == pytest.approx(C[t - 21, n] / C[t - 252, n] - 1, rel=1e-12)
    assert ch["REV1"][n] == pytest.approx(C[t, n] / C[t - 1, n] - 1, rel=1e-12)
    assert ch["VOL"][n] == pytest.approx(np.std(R[-60:], ddof=1), rel=1e-12)
    x, y = M[-250:], np.concatenate([[np.nan], R])[-250:]
    slope = np.polyfit(x, y, 1)[0]
    assert ch["BETA"][n] == pytest.approx(slope, rel=1e-9)
    x6, y6 = M[-60:], R[-60:]
    b6, a6 = np.polyfit(x6, y6, 1)
    resid = y6 - a6 - b6 * x6
    assert ch["IVOL"][n] == pytest.approx(math.sqrt((resid ** 2).sum() / 58), rel=1e-9)
    assert ch["HIGH52"][n] == pytest.approx(C[t, n] / C[-252:, n].max(), rel=1e-12)
    assert ch["RANGE"][n] == pytest.approx(np.log(H[-21:, n] / Lo[-21:, n]).mean(), rel=1e-12)
    assert ch["LIQ"][n] == pytest.approx(math.log(V[-60:, n].mean()), rel=1e-12)
    assert ch["TURN"][n] == pytest.approx(V[-5:, n].mean() / V[-60:, n].mean(), rel=1e-12)
    assert ch["ILLIQ"][n] == pytest.approx((np.abs(R[-60:]) / V[-60:, n]).mean(), rel=1e-12)
    # stock 2 lost 3 of its last 5 traded values: TURN missing, LIQ still valid (57 of 60)
    assert np.isnan(ch["TURN"][2]) and np.isfinite(ch["LIQ"][2])


def test_characteristics_are_invariant_to_a_later_corporate_action():
    C, V, H, Lo, M = _panel()
    a = L.characteristics(C, V, H, Lo, M)
    b = L.characteristics(C * 0.4321, V, H, Lo, M)
    for name in L.CHARS:
        assert np.allclose(a[name], b[name], rtol=1e-12, atol=0, equal_nan=True), name


def test_characteristics_need_enough_history():
    C, V, H, Lo, M = _panel(T=200)
    ch = L.characteristics(C, V, H, Lo, M)
    assert np.isnan(ch["MOM"]).all() and np.isnan(ch["BETA"]).all() and np.isnan(ch["HIGH52"]).all()
    assert np.isfinite(ch["VOL"][0])


def test_bisect_counts_rows_strictly_before():
    days = ["2025-01-01", "2025-01-02", "2025-01-03"]
    assert L._bisect(days, "2025-01-02") == 1 and L._bisect(days, "2025-01-04") == 3 and L._bisect(days, "2024") == 0


def test_market_returns_needs_enough_members():
    R = np.full((2, 60), 0.01)
    R[1, 15:] = np.nan
    mask = np.ones((2, 60), dtype=bool)
    m = L.market_returns(R, mask)
    assert m[0] == pytest.approx(0.01) and np.isnan(m[1])


# ---- Ridge, folds, refits --------------------------------------------------------------------------

def test_fit_ridge_standardises_on_training_rows_and_shrinks():
    rng = np.random.default_rng(1)
    X = rng.standard_normal((4000, 5)) * [1, 2, 3, 4, 5] + 10
    X[:, 4] = 7.0                                               # constant column
    y = 3.0 * (X[:, 0] - 10) + rng.standard_normal(4000)
    m = L.fit_ridge(X, y, 1e-6)
    lo, hi = np.quantile(y, L.WINSOR)
    assert m["winsor"] == (pytest.approx(lo), pytest.approx(hi))
    Z = (X[:, :4] - X[:, :4].mean(0)) / X[:, :4].std(0)
    yw = np.clip(y, lo, hi)
    ols = np.linalg.lstsq(Z, yw - yw.mean(), rcond=None)[0]
    assert m["b"][:4] == pytest.approx(ols, rel=1e-5, abs=1e-5) and m["b"][4] == 0
    assert m["b"][0] == pytest.approx(3.0, rel=0.06)            # winsorising the regressand attenuates a little
    big = L.fit_ridge(X, y, 1e6)
    assert np.abs(L.predict(big, X) - big["ybar"]).max() < 1e-3
    Xo = X[:5].copy()
    Xo[0, :4] = X[:, :4].mean(0)
    Xo[0, 0] = 1e9                                              # clipped at +5 sd
    assert L.predict(m, Xo)[0] == pytest.approx(m["ybar"] + 5 * m["b"][0])
    with pytest.raises(AssertionError):
        L.fit_ridge(np.array([[np.nan], [1.0]]), np.array([1.0, 2.0]), 1.0)


def _business_days(first="2024-09-20", last="2025-12-31"):
    d, out = date.fromisoformat(first), []
    while d.isoformat() <= last:
        if d.weekday() < 5 and d.isoformat() != "2025-12-25":
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def test_first_window_folds_and_refits_are_purged():
    ses = _business_days()
    window, j = L.first_window(ses)
    assert ses[j] == "2025-03-03" and window[0] == 1 and j - window[-1] - 1 == L.PURGE
    folds = L.cv_folds(window)
    assert len(folds) == 4
    for tr, va in folds:
        assert va[0] - tr[-1] - 1 == L.PURGE and va == list(range(va[0], va[-1] + 1))
    plan = L.refit_plan(ses)
    assert [p[0] for p in plan] == L.months_between("2025-03", "2025-12")
    for mo, train, fc in plan:
        assert train[0] == 1 and fc[0] - train[-1] - 1 == L.PURGE and all(ses[s][:7] == mo for s in fc)


class _FakeDS:
    def __init__(self, strength, seed=11, P=4):
        rng = np.random.default_rng(seed)
        self.sessions = _business_days()
        S = len(self.sessions)
        self.X = rng.standard_normal((S, L.BARS, P))
        self.X[0] = np.nan
        self.X[:, :L.FIRST_DECISION_BAR] = np.nan
        noise = rng.standard_normal((S, L.BARS)) * 20
        self.Y = {h: strength * np.nan_to_num(self.X[:, :, 0]) + noise for h in L.HORIZONS}


def test_choose_alpha_and_walk_forward_on_a_planted_signal():
    ds = _FakeDS(strength=15.0)
    a, curve, folds = L.choose_alpha(ds, "h30", ds.Y["h30"])
    assert a <= 1.0 and len(curve) == 15 and all(f["gap_sessions"] == L.PURGE for f in folds)
    dec, facts, _m = L.walk_forward(ds, "h30", a, ds.Y["h30"])
    assert {f["month"] for f in facts} == set(L.months_between("2025-03", "2025-12"))
    assert all(f["gap_sessions"] == L.PURGE for f in facts)
    sample = [d for d in ds.sessions if "2025-09-01" <= d <= "2025-12-23"]
    trades, decisions, targets = L.score_decisions(ds, dec, ds.Y["h30"], sample)
    res = L.judge(trades, sample)
    assert res["passes"], res["checks"]


def test_choose_alpha_prefers_heavy_shrinkage_without_signal():
    ds = _FakeDS(strength=0.0)
    a, curve, _f = L.choose_alpha(ds, "h60", ds.Y["h60"])
    assert a >= 1.0
    dec, _facts, _m = L.walk_forward(ds, "h60", a, ds.Y["h60"])
    sample = [d for d in ds.sessions if "2025-09-01" <= d <= "2025-12-23"]
    trades, _d, _t = L.score_decisions(ds, dec, ds.Y["h60"], sample)
    assert not L.judge(trades, sample)["passes"]


def test_choose_alpha_tie_goes_to_the_larger_alpha(monkeypatch):
    ds = _FakeDS(strength=0.0)
    monkeypatch.setattr(L, "predict", lambda m, X: np.zeros(len(X)))
    a, curve, _f = L.choose_alpha(ds, "h30", ds.Y["h30"])
    assert a == L.ALPHAS[-1]


# ---- trade rule and gate ----------------------------------------------------------------------------

def test_trades_from_threshold_and_net():
    targets = {("d1", 5): 20.0, ("d1", 11): -3.0, ("d2", 5): -10.0}
    dec = [("d1", 5, 7.0), ("d1", 11, 6.9), ("d2", 5, -8.0)]
    tr = L.trades_from(dec, targets, cost=6.95)
    assert [(t["date"], t["side"]) for t in tr] == [("d1", 1), ("d2", -1)]
    assert tr[0]["net"] == pytest.approx(20 - 6.95) and tr[1]["net"] == pytest.approx(10 - 6.95)


def test_judge_needs_trades_sessions_halves_and_dsr():
    sessions = ["2025-09-%02d" % d for d in range(1, 29)] + ["2025-10-%02d" % d for d in range(1, 29)]
    trades = [{"date": d, "net": 5.0 + (i % 3), "gross": 12.0} for i, d in enumerate(sessions) for _ in range(2)]
    res = L.judge(trades, sessions)
    assert res["trades"] == 112 and res["sessions_with_trades"] == 56 and res["passes"]
    few = L.judge(trades[:60], sessions)
    assert not few["checks"]["enough_trades"] and not few["passes"]
    neg_half = [dict(t, net=-t["net"]) if t["date"] < "2025-10" else t for t in trades]
    assert not L.judge(neg_half, sessions)["checks"]["both_halves_positive"]
    assert res["dsr_n_trials"] == 2


def test_forecast_stats():
    f = np.array([1.0, -2.0, 3.0, -1.0, 0.5])
    r = np.array([2.0, -1.0, 5.0, 1.0, -0.5])
    s = L.forecast_stats(f, r)
    assert s["ic"] == pytest.approx(np.corrcoef(f, r)[0, 1])
    assert s["hit_rate"] == pytest.approx(0.6)
    assert s["r2_oos_uncentred"] == pytest.approx(1 - ((r - f) ** 2).sum() / (r ** 2).sum())


def test_derangement_has_no_fixed_point():
    rng = np.random.default_rng(51)
    for n in (2, 5, 100):
        p = L.derangement(n, rng)
        assert sorted(p) == list(range(n)) and not (p == np.arange(n)).any()


# ---- one-run guard and isolation ------------------------------------------------------------------

def _paths(tmp_path):
    return {"stage0": str(tmp_path / "s0.json"), "result": str(tmp_path / "res.json"),
            "decisions": str(tmp_path / "dec.csv"), "models": str(tmp_path / "models.json"),
            "module": L.MODULE_PATH, "prereg": L.PREREG_PATH}


def test_scoring_refuses_without_go_stage0_or_with_a_result(tmp_path):
    paths = _paths(tmp_path)
    why = L.scoring_refusals(None, paths=paths, clean=lambda p: True)
    assert any("--go" in w for w in why) and any("no stage 0" in w for w in why)
    with open(paths["stage0"], "w") as f:
        json.dump({"status": "HALTED", "halted_at": "x", "module_sha256": "not this module"}, f)
    with open(paths["result"], "w") as f:
        f.write("{}")
    why = L.scoring_refusals("main session, 2026-10-01", paths=paths, clean=lambda p: False)
    assert any("HALTED" in w for w in why) and any("runs once" in w for w in why)
    assert any("module differs" in w for w in why) and any("no pseudo-out-of-sample" in w for w in why)
    assert sum("not committed" in w for w in why) == 3          # stage 0 record, module, prereg


# ---- the scoring pass, end to end, on a synthetic dataset (amendment 6, B1) ------------------------

def _fake_dataset(strength, seed=5, P=3):
    rng = np.random.default_rng(seed)
    ds = L.Dataset()
    ds.sessions = ds.all_dates = _business_days()
    ds.index_bars = {}
    for d in ds.sessions:
        closes = 20000 + np.cumsum(rng.standard_normal(L.BARS) * 10)
        opens = np.concatenate([[20000.0], closes[:-1]]) + rng.standard_normal(L.BARS)
        ds.index_bars[d] = (list(opens), list(closes), L.INDEX_MINUTES)
    ds.info = {"stock_cache": {"rows": 1234}, "index_db": {"rows": 5678}}
    true = ds.build_targets(before=None)
    S = len(ds.sessions)
    X = rng.standard_normal((S, L.BARS, P))
    if strength:
        X[:, :, 0] = np.nan_to_num(true["h30"]) + rng.standard_normal((S, L.BARS)) * 2
        X[:, :, 1] = np.nan_to_num(true["h60"]) + rng.standard_normal((S, L.BARS)) * 3
    X[0] = np.nan
    X[:, :L.FIRST_DECISION_BAR] = np.nan
    ds.X = X
    return ds


def _stage0_for(ds, path):
    """What stage 0 would record for this dataset: no target from 2025-09-01 on."""
    Y0 = ds.build_targets(before=L.SCORING_START)
    alphas = {h: L.choose_alpha(ds, h, Y0[h])[0] for h in L.HORIZONS}
    po = L.pseudo_oos_forecasts(ds, Y0, alphas)
    scoring = [d for d in L.k.selection_sessions(ds.all_dates) if d in set(ds.sessions)]
    s0 = {"status": "STAGE0_DONE", "module_sha256": L.sha256_file(L.MODULE_PATH),
          "coverage": {"scoring_sessions": len(scoring)}, "alpha": {h: {"alpha": alphas[h]} for h in L.HORIZONS},
          "data": {"stock_cache": {"rows": 1234}, "index_db": {"rows": 5678}},
          "pseudo_oos_forecasts": {h: [[ds.sessions[x[0]], x[1], x[2]] for x in po[h][0]] for h in L.HORIZONS}}
    with open(path, "w") as f:
        json.dump(s0, f)
    return s0, scoring


class _Args:
    go = "synthetic test"
    owner_approved_rescore = None


def _run_score(ds, tmp_path):
    paths = _paths(tmp_path)
    s0, scoring = _stage0_for(ds, paths["stage0"])
    commits = []

    def commit(files, message):
        commits.append((message, [json.load(open(x)).get("status") if x.endswith(".json") and "res" in x else None
                                  for x in files]))
        return "fake%d" % len(commits)

    rec = L.score(_Args(), load=lambda: ds, paths=paths, commit=commit,
                  refusals=lambda go, rr, p: L.scoring_refusals(go, rr, p, clean=lambda x: True))
    return rec, paths, commits, scoring


def _read_rows(path):
    import csv
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def test_score_end_to_end_zero_trades(tmp_path):
    ds = _fake_dataset(strength=0)
    rec, paths, commits, scoring = _run_score(ds, tmp_path)
    assert [c[0] for c in commits] == ["research: L51 scoring pass STARTED", "research: L51 scoring pass DONE"]
    assert commits[0][1] == ["STARTED"] and rec["started_commit"] == "fake1"
    res = rec["result"]
    assert rec["status"] == "DONE" and res["h30"]["trades"] == 0 and res["h60"]["trades"] == 0
    assert not res["l51_clears"] and res["scoring_sample"][2] == len(scoring)
    v = " ".join(res["verdict"])
    assert "L51 does not clear at 30 minutes: the forecast exceeded the 6.95 bp round trip on 0 of %d decisions" \
        % (len(scoring) * 11) in v
    assert L.POWER_30 in v and L.POWER_CAVEAT in v and "Direction from the predictors at 60 minutes" in v
    rows_ = _read_rows(paths["decisions"])
    pseudo = L.pseudo_sessions(ds)
    assert len(rows_) == rec["decisions_rows"] == (len(pseudo) + len(scoring)) * 16
    assert rec["decisions_sha256"] == L.sha256_file(paths["decisions"])
    assert rec["models_sha256"] == L.sha256_file(paths["models"])
    assert {r["session"] for r in rows_} <= set(pseudo) | set(scoring)
    assert max(r["session"] for r in rows_) == L.LAST_SCORING_SESSION
    assert all(r["side"] == "0" and float(r["net_bp"]) == 0.0 for r in rows_)
    # every forecast is recomputable from the models file and the predictors
    models = json.load(open(paths["models"]))["models"]
    assert sorted(models["h30"]) == L.months_between("2025-03", "2025-12")
    srow = {d: n for n, d in enumerate(ds.sessions)}
    for r in rows_[:: max(1, len(rows_) // 40)]:
        m = models[r["horizon"]][r["refit_month"]]
        mm = {"ybar": m["ybar"], "mu": np.array(m["mu"]), "sd": np.array(m["sd"]), "b": np.array(m["b"])}
        f = L.predict(mm, ds.X[srow[r["session"]], int(r["bar"])][None, :])[0]
        assert f == pytest.approx(float(r["forecast_bp"]), abs=1e-9)
        assert float(r["xb_bp"]) == pytest.approx(float(r["forecast_bp"]) - m["ybar"], abs=1e-12)
        kb = L.HORIZONS[r["horizon"]]
        assert float(r["target_bp"]) == pytest.approx(
            (float(r["index_exit"]) / float(r["index_entry"]) - 1) * 1e4, rel=1e-12)
        assert r["decision_close"] == L.bar_close_hhmm(int(r["bar"])) and kb in (6, 12)
    # the one-run rule: a second pass refuses
    with pytest.raises(SystemExit):
        L.score(_Args(), load=lambda: ds, paths=paths, commit=lambda *a: None,
                refusals=lambda go, rr, p: L.scoring_refusals(go, rr, p, clean=lambda x: True))


def test_score_end_to_end_with_trades(tmp_path):
    ds = _fake_dataset(strength=1)
    rec, paths, commits, scoring = _run_score(ds, tmp_path)
    res = rec["result"]
    rows_ = _read_rows(paths["decisions"])
    for h in L.HORIZONS:
        sc = [r for r in rows_ if r["horizon"] == h and r["sample"] == "scoring"]
        traded = [r for r in sc if r["side"] != "0"]
        assert res[h]["trades"] == len(traded) > 0
        assert res[h]["mean_net_bp_per_trade"] == pytest.approx(np.mean([float(r["net_bp"]) for r in traded]))
        assert all(float(r["net_bp_2025"]) == pytest.approx(float(r["gross_bp"]) - L.COST_BP_2025) for r in traded)
        assert res[h]["xb_headline"]["reading"] == "direction present"
        assert {r["half"] for r in sc} == {"1", "2"}


def test_scoring_stops_if_stage0_forecasts_do_not_reproduce(tmp_path):
    ds = _fake_dataset(strength=0)
    paths = _paths(tmp_path)
    s0, _scoring = _stage0_for(ds, paths["stage0"])
    s0["pseudo_oos_forecasts"]["h30"][3][2] += 1e-6
    with open(paths["stage0"], "w") as f:
        json.dump(s0, f)
    with pytest.raises(AssertionError, match="differ from stage 0"):
        L.score(_Args(), load=lambda: ds, paths=paths, commit=lambda *a: "x",
                refusals=lambda go, rr, p: [])


def test_walk_forward_until_stops_forecasting():
    ds = _fake_dataset(strength=0)
    Y = ds.build_targets(before=None)
    dec, facts, _m = L.walk_forward(ds, "h60", 10.0, Y["h60"], until=L.LAST_SCORING_SESSION)
    assert max(ds.sessions[x[0]] for x in dec) == L.LAST_SCORING_SESSION


# ---- the predictor part of the forecast (amendment 6, B2) ------------------------------------------

def test_clustered_ic_is_the_pearson_ic_and_widens_with_clustering():
    rng = np.random.default_rng(3)
    x = rng.standard_normal(600)
    r = 0.2 * x + rng.standard_normal(600)
    single = L.clustered_ic(x, r, list(range(600)))
    assert single["ic"] == pytest.approx(np.corrcoef(x, r)[0, 1])
    # the same data duplicated inside clusters: same IC, the clustered t does not grow
    x2, r2 = np.repeat(x, 5), np.repeat(r, 5)
    dup = L.clustered_ic(x2, r2, list(np.repeat(np.arange(600), 5)))
    assert dup["ic"] == pytest.approx(single["ic"]) and dup["t_clustered"] == pytest.approx(single["t_clustered"],
                                                                                                rel=0.01)
    assert L.clustered_ic([1, 1, 1], [1, 2, 3], [0, 1, 2])["ic"] is None


def test_xb_reading_rule():
    rng = np.random.default_rng(4)
    ses = ["2025-09-%02d" % d for d in range(1, 29)] + ["2025-10-%02d" % d for d in range(1, 29)]
    rows_ = []
    for d in ses:
        for _ in range(11):
            a = rng.standard_normal()
            rows_.append((d, a, 0.5 * a + rng.standard_normal()))
    assert L.xb_stats(rows_, ses)["reading"] == "direction present"
    flipped = [(d, -a, b) for d, a, b in rows_]
    assert L.xb_stats(flipped, ses)["reading"] == "anti-predictive"
    half_only = [(d, a, b if d < "2025-10" else -b) for d, a, b in rows_]
    assert L.xb_stats(half_only, ses)["reading"] == "no direction"


def test_module_imports_nothing_live():
    tree = ast.parse(open(L.__file__).read())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    live = {"app", "kite_broker", "kite_history", "data_provider", "trading_engine", "paper_broker", "scanner",
            "trader_brain", "risk_manager", "config", "database"}
    assert not (names & live), names & live
