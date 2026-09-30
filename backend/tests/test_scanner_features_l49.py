"""Research look L49 (docs/research/prereg-scanner-features.md): the five features, the
look-ahead proof, the hand path, the loaders' 2026 guards and the pass's refusals.
Everything here runs on synthetic data; no test reads the candle cache or NSE files."""
import ast
import csv
import io
import json
import os
import random
import sqlite3
import zipfile
from collections import OrderedDict
from datetime import datetime, timedelta

import pytest

from research import kronos_feature_ic as k
from research import scanner_features_l49 as m

MODULE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research",
                      "scanner_features_l49.py")


def _weekdays(start, n):
    d, out = datetime.strptime(start, "%Y-%m-%d"), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return out


def _session(date, start="09:15", n=75, base=100.0, step=0.1, vol=1000):
    t = datetime.strptime("%s %s" % (date, start), "%Y-%m-%d %H:%M")
    out = []
    for i in range(n):
        p = base + i * step
        out.append({"time": (t + timedelta(minutes=5 * i)).isoformat(), "open": p, "high": p + 0.05,
                    "low": p - 0.05, "close": p + 0.02, "volume": vol + i})
    return out


def _ctx(days, symbols=("A", "B", "C", "T"), industry=None, bhav=None, ca=None, unit=None, special=None):
    """A Ctx over `days` with simple deterministic bars; bhav rows on every day unless
    given. `special` maps (sym, day) to a replacement bar list."""
    industry = industry or {"A": "Banks", "B": "Banks", "C": "Banks", "T": "Telecom"}
    sbs = OrderedDict()
    for j, s in enumerate(symbols):
        sbs[s] = OrderedDict()
        for n, d in enumerate(days):
            bars = (special or {}).get((s, d)) or _session(d, base=100.0 + 10 * j + n, vol=1000 * (j + 1))
            sbs[s][d] = bars
    if bhav is None:
        bhav = {}
        for s in symbols:
            for d in days:
                last = sbs[s][d][-1]["close"]
                bhav[(s, d)] = {"open": sbs[s][d][0]["open"], "high": 0, "low": 0, "close": last * 1.001, "last": last}
    members = {d: set(symbols) for d in days}
    return m.Ctx(sbs, sorted(days), bhav, ca or {}, unit or {}, industry, members, {})


# ---- the pre-registration's shape -------------------------------------------------------

def test_family_is_thirteen_tests_with_the_gap_reversal_at_60_minutes_only():
    assert len(m.TESTS) == 13 == m.N_TESTS
    assert m.FEATURES == ("gap", "rvol", "vwap_dist", "sector", "gap_reversal")
    assert [t for t, (f, _h) in m.TESTS.items() if f == "gap_reversal"] == ["gap_reversal_f60"]
    for f in m.AUDIT_FEATURES:
        assert [h for (ff, h) in m.TESTS.values() if ff == f] == list(k.HORIZONS)
    assert m.feature_applies("gap_reversal", "09:45") and not m.feature_applies("gap_reversal", "10:30")
    assert m.feature_applies("sector", "13:30")


def test_module_imports_neither_kite_history_config_nor_app():
    tree = ast.parse(open(MODULE).read())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
            names |= {a.name for a in node.names}
    assert not names & {"kite_history", "config", "app", "trading_engine", "scanner"}


def test_bar_time_is_kite_history_s_shape_in_ist():
    ts = int(datetime(2025, 9, 1, 9, 15).replace(tzinfo=m.IST).timestamp())
    assert m.bar_time(ts) == "2025-09-01T09:15:00"
    assert m.day_start_ts("2026-01-02") == int(datetime(2026, 1, 2).replace(tzinfo=m.IST).timestamp())


# ---- the features --------------------------------------------------------------------------

def test_previous_close_is_the_official_close_on_kite_s_basis():
    days = _weekdays("2025-10-01", 3)
    ctx = _ctx(days)
    d, dm = days[2], days[1]
    k_last = ctx.sessions_by_sym["A"][dm][-1]["close"]
    ctx.bhav[("A", dm)] = {"open": 0, "high": 0, "low": 0, "close": 99.0, "last": 110.0}
    pc, why = m.prev_close(ctx, "A", d)
    assert why is None and pc == pytest.approx(k_last * 99.0 / 110.0, rel=1e-15)


def test_previous_close_is_undefined_on_an_ex_date_or_without_nse_s_row():
    days = _weekdays("2025-10-01", 3)
    ctx = _ctx(days, ca={"A": {days[2]}})
    assert m.prev_close(ctx, "A", days[2]) == (None, "ca_exdate")
    del ctx.bhav[("B", days[1])]
    assert m.prev_close(ctx, "B", days[2]) == (None, "missing:no_bhavcopy_row")
    ctx.bhav[("C", days[1])]["last"] = 0
    assert m.prev_close(ctx, "C", days[2]) == (None, "missing:nonpositive_price")
    assert m.prev_close(ctx, "A", days[0]) == (None, "missing:no_previous_session")


def test_previous_session_is_the_market_s_even_when_it_is_a_special_session():
    days = _weekdays("2025-10-20", 3)
    muhurat = _session(days[1], start="13:45", n=12, base=150.0)
    ctx = _ctx(days, special={("A", days[1]): muhurat})
    pc, _ = m.prev_close(ctx, "A", days[2])
    row = ctx.bhav[("A", days[1])]
    assert pc == pytest.approx(muhurat[-1]["close"] * row["close"] / row["last"])


def test_gap_is_the_0915_open_against_the_previous_close():
    days = _weekdays("2025-10-01", 3)
    ctx = _ctx(days)
    pc, _ = m.prev_close(ctx, "A", days[2])
    v, why = m.gap(ctx, "A", days[2], "10:30")
    assert why is None and v == pytest.approx((ctx.sessions_by_sym["A"][days[2]][0]["open"] / pc - 1) * 1e4)
    assert m.gap(ctx, "A", days[2], "09:45")[0] == v          # the same at every time of the day


def test_rvol_uses_twenty_regular_sessions_and_skips_a_special_one():
    days = _weekdays("2025-10-01", 23)
    special = {("A", days[10]): _session(days[10], start="13:45", n=12, vol=5)}
    ctx = _ctx(days, special=special)
    d, hhmm = days[22], "09:45"
    v, why = m.rvol(ctx, "A", d, hhmm)
    assert why is None
    base = [e for e in days[:22] if e != days[10]][-20:]
    cut = "09:40"
    num = sum(b["volume"] for b in ctx.sessions_by_sym["A"][d] if b["time"][11:16] <= cut)
    den = sum(sum(b["volume"] for b in ctx.sessions_by_sym["A"][e] if b["time"][11:16] <= cut) for e in base) / 20
    assert v == pytest.approx(num / den)


def test_rvol_is_undefined_with_a_short_baseline_or_a_split_inside_it():
    days = _weekdays("2025-10-01", 21)
    assert m.rvol(_ctx(days), "A", days[19], "09:45") == (None, "rvol_short_baseline")
    ctx = _ctx(days, unit={"A": {days[5]}})
    assert m.rvol(ctx, "A", days[20], "09:45") == (None, "ca_volume_unit")
    assert m.rvol(ctx, "B", days[20], "09:45")[1] is None
    ctx = _ctx(days, unit={"A": {days[0]}})                   # the baseline's first day is inside it
    assert m.rvol(ctx, "A", days[20], "09:45") == (None, "ca_volume_unit")
    days = _weekdays("2025-10-01", 22)
    ctx = _ctx(days, unit={"A": {days[0]}})                   # the day before the baseline starts
    assert m.rvol(ctx, "A", days[21], "09:45")[1] is None


def test_vwap_distance_uses_the_scanner_s_formula_on_closed_bars():
    days = _weekdays("2025-10-01", 2)
    ctx = _ctx(days)
    bars = ctx.sessions_by_sym["B"][days[1]]
    i = k.decision_bar_index(bars, "11:15")
    upto = bars[:i + 1]
    vw = sum((b["high"] + b["low"] + b["close"]) / 3 * b["volume"] for b in upto) / sum(b["volume"] for b in upto)
    v, why = m.vwap_dist(ctx, "B", days[1], "11:15")
    assert why is None and v == pytest.approx((bars[i]["close"] / vw - 1) * 1e4, rel=1e-12)


def test_sector_is_the_rest_of_the_industry_and_singletons_have_none():
    days = _weekdays("2025-10-01", 3)
    ctx = _ctx(days)
    d, hhmm = days[2], "12:00"
    moves = [m.day_change(ctx, p, d, hhmm)[0] for p in ("B", "C")]
    v, why = m.sector(ctx, "A", d, hhmm)
    assert why is None and v == pytest.approx(sum(moves) / 2)
    assert m.sector(ctx, "T", d, hhmm) == (None, "singleton_industry")
    ctx = _ctx(days, ca={"B": {d}, "C": {d}})
    assert m.sector(ctx, "A", d, hhmm) == (None, "ca_exdate_peers")


def test_sector_peers_do_not_need_bars_after_the_decision_time():
    days = _weekdays("2025-10-01", 3)
    short = _session(days[2], n=13)                           # B stops trading at 10:15
    ctx = _ctx(days, special={("B", days[2]): short})
    v, _ = m.sector(ctx, "A", days[2], "10:15")
    assert v == pytest.approx((m.day_change(ctx, "B", days[2], "10:15")[0]
                               + m.day_change(ctx, "C", days[2], "10:15")[0]) / 2)


def test_gap_reversal_is_minus_the_move_since_the_previous_close():
    days = _weekdays("2025-10-01", 3)
    ctx = _ctx(days)
    move, _ = m.day_change(ctx, "C", days[2], "09:45")
    assert m.gap_reversal(ctx, "C", days[2], "09:45") == (-move, None)


# ---- the look-ahead proof -------------------------------------------------------------------

def test_lookahead_proof_holds_for_every_feature():
    days = _weekdays("2025-10-01", 23)
    ctx = _ctx(days)
    picks = [(s, days[22], t) for s in ("A", "B", "T") for t in k.DECISION_TIMES]
    checks = m.lookahead_proof(ctx, picks)
    assert all(c["identical"] for c in checks)
    assert {"gap", "rvol", "vwap_dist", "sector", "gap_reversal"} <= set(checks[0]["defined"])


def test_truncation_removes_later_bars_and_same_day_bhavcopies():
    days = _weekdays("2025-10-01", 3)
    ctx = _ctx(days)
    cut = m.truncated_ctx(ctx, days[1], "10:30")
    assert cut.sessions_by_sym["A"][days[1]][-1]["time"].endswith("10:25:00")
    assert days[2] not in cut.sessions_by_sym["A"] and days[2] not in cut.calendar
    assert ("A", days[1]) not in cut.bhav and ("A", days[0]) in cut.bhav


def test_lookahead_proof_catches_a_leaky_feature(monkeypatch):
    days = _weekdays("2025-10-01", 3)
    ctx = _ctx(days)

    def leaky(c, s, d, hhmm):                               # the session's LAST bar, not the decision bar
        return c.bars(s, d)[-1]["close"], None
    monkeypatch.setitem(m.FEATURE_FUNCS, "vwap_dist", leaky)
    checks = m.lookahead_proof(ctx, [("A", days[2], "10:30")])
    assert not checks[0]["identical"] and checks[0]["differs"] == ["vwap_dist"]


# ---- statistics: the harness's, per test ------------------------------------------------------

def test_per_test_aggregation_equals_the_harness_s_evaluate_rows(tmp_path):
    rng = random.Random(5)
    days = _weekdays("2025-10-01", 64)
    samples, feats, targets, m60s = [], [], [], []
    rows_path = tmp_path / "rows.jsonl"
    with open(rows_path, "w") as out:
        for d in days:
            for s in range(25):
                for t in ("09:45", "10:30"):
                    v, y = rng.gauss(0, 1), {h: rng.gauss(0, 30) for h in k.HORIZONS}
                    mv = rng.gauss(0, 20)
                    samples.append(("S%d" % s, d, t, 0, 0))
                    feats.append({n: (v, None) for n in m.FEATURES})
                    targets.append(y)
                    m60s.append(mv)
                    out.write(json.dumps({"date": d, "m60": mv, "features": {h: v for h in k.HORIZONS},
                                          "targets": y}) + "\n")
    harness = k.evaluate_rows(str(rows_path))["summaries"]
    for h in k.HORIZONS:
        mine, _ = m.summarise_rows(m.rows_for_test(samples, feats, targets, m60s, "rvol_" + h))
        assert json.dumps(mine, sort_keys=True) == json.dumps(harness[h], sort_keys=True)
    rev, _ = m.summarise_rows(m.rows_for_test(samples, feats, targets, m60s, "gap_reversal_f60"))
    at_0945 = [j for j, s in enumerate(samples) if s[2] == "09:45"]
    assert rev["sessions"] == 64 and len(at_0945) == 64 * 25


def test_evaluate_runs_the_harness_gate_once_across_the_thirteen():
    rng = random.Random(9)
    days = _weekdays("2025-10-01", 62)
    samples, feats, targets, m60s = [], [], [], []
    for d in days:
        for s in range(25):
            for t in ("09:45", "12:00"):
                y = {h: rng.gauss(0, 40) for h in k.HORIZONS}
                samples.append(("S%d" % s, d, t, 0, 0))
                feats.append({n: (y["f60"] + rng.gauss(0, 5) if n == "sector" else rng.random(), None)
                              for n in m.FEATURES})
                targets.append(y)
                m60s.append(rng.gauss(0, 20))
    summaries, _, verdicts = m.evaluate(samples, feats, targets, m60s)
    assert list(verdicts) == list(m.TESTS)
    assert verdicts["sector_f60"]["passes"]                  # a planted near-perfect forecast
    assert not any(v["passes"] for t, v in verdicts.items() if t != "sector_f60")


def test_positive_control_gives_the_expected_pattern():
    rng = random.Random(11)
    days = _weekdays("2025-05-01", 70)
    flat_by_sym, sessions_by_sym, members = OrderedDict(), OrderedDict(), {}
    for s in range(22):
        p, bars = 100.0, []
        for d in days:
            t = datetime.strptime(d + " 09:15", "%Y-%m-%d %H:%M")
            for i in range(75):
                o = p
                p = p * (1 + rng.gauss(0, 0.002))
                bars.append({"time": (t + timedelta(minutes=5 * i)).isoformat(), "open": o, "high": max(o, p),
                             "low": min(o, p), "close": p, "volume": 1000})
        flat_by_sym["S%02d" % s] = bars
        sessions_by_sym["S%02d" % s] = k.by_session(bars)
    members = {d: set(flat_by_sym) for d in days}
    samples = k.build_samples(flat_by_sym, sessions_by_sym, days, members, {})
    out = m.positive_control(samples, flat_by_sym, sessions_by_sym)
    assert out["passes"], out["tests"]
    assert all(out["tests"]["pos_" + h]["spread_over_bar"] > 1 for h in k.HORIZONS)


def test_a_constant_partial_ic_has_no_t_which_is_why_the_control_has_noise():
    # The bare target's partial IC is 1 in every session up to rounding: the harness's t
    # is then undefined (zero spread) or rounding error, so the gate's verdict on it is luck.
    mean, t, se = k.tstat([1.0] * 62)
    assert mean == 1.0 and t is None and se == 0.0


# ---- coverage and alignment ------------------------------------------------------------------

def test_coverage_halts_on_missing_data_but_not_on_registered_reasons():
    days = _weekdays("2025-10-01", 62)
    samples = [("S%d" % s, d, "09:45", 0, 0) for d in days for s in range(25)]
    ok = [{n: (1.0, None) for n in m.FEATURES} for _ in samples]
    for j in range(0, len(samples), 20):
        ok[j]["sector"] = (None, "singleton_industry")
    cov, why = m.coverage(samples, ok, days)
    assert not why and cov["features"]["sector"]["undefined_by_reason"] == {"singleton_industry": 78}
    bad = [dict(f) for f in ok]
    for j in range(0, len(samples), 50):
        bad[j]["gap"] = (None, "missing:no_bhavcopy_row")
    _, why = m.coverage(samples, bad, days)
    assert any(w.startswith("gap:") for w in why)
    odd = [dict(f) for f in ok]
    odd[0]["rvol"] = (None, "something_else")
    _, why = m.coverage(samples, odd, days)
    assert any("does not name" in w for w in why)


def test_alignment_passes_when_kite_s_last_bar_is_nse_s_last_price():
    days = _weekdays("2025-10-01", 6)
    ctx = _ctx(days)
    used = {(s, d) for s in ("A", "B") for d in days[1:]}
    out = m.alignment(ctx, used)
    assert out["passes"] and out["share_within_tol"] == 1.0 and out["pairs"] == len(used)
    ctx.bhav[("A", days[3])]["last"] *= 1.01                  # a 100 bp disagreement on one day
    out = m.alignment(ctx, used)
    assert out["worst"][0]["symbol"] == "A" and out["worst"][0]["move_bp"] > 90


# ---- loaders: read-only, and never 2026 ----------------------------------------------------------

def _cache_db(path, series):
    conn = sqlite3.connect(str(path))
    conn.executescript("CREATE TABLE candles (symbol TEXT, interval TEXT, ts INTEGER, open REAL, high REAL, "
                       "low REAL, close REAL, volume INTEGER, PRIMARY KEY (symbol, interval, ts));"
                       "CREATE TABLE fetched (symbol TEXT, interval TEXT, from_date TEXT, to_date TEXT, rows INTEGER, "
                       "fetched_at REAL, PRIMARY KEY (symbol, interval, from_date, to_date));")
    for sym, bars in series.items():
        for b in bars:
            ts = int(datetime.fromisoformat(b["time"]).replace(tzinfo=m.IST).timestamp())
            conn.execute("INSERT INTO candles VALUES (?, '5m', ?, ?, ?, ?, ?, ?)",
                         (sym, ts, b["open"], b["high"], b["low"], b["close"], b["volume"]))
        conn.execute("INSERT INTO fetched VALUES (?, '5m', '2024-09-20', '2026-09-18', 1, ?)",
                     (sym, datetime(2026, 9, 20, 12).timestamp()))
    conn.commit()
    conn.close()


def test_load_candles_stops_before_2026_and_cannot_write(tmp_path):
    db = tmp_path / "cache.db"
    _cache_db(db, {"A": _session("2025-12-31") + _session("2026-01-02"), "B": _session("2025-12-31")})
    conn = m.connect_ro(str(db))
    out, latest = m.load_candles(conn, ["A", "B", "Z"])
    assert list(out) == ["A", "B"] and latest.startswith("2025-12-31")
    assert all(b["time"] < "2026" for bars in out.values() for b in bars)
    assert m.fetch_runs(conn) == [{"date": "2026-09-20", "spans": 2}]
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM candles")


def _udiff_zip(path, day, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["TradDt", "TckrSymb", "SctySrs", "OpnPric", "HghPric", "LwPric", "ClsPric", "LastPric"])
    for sym, series, o, c, last in rows:
        w.writerow([day, sym, series, o, max(o, c), min(o, c), c, last])
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("BhavCopy.csv", buf.getvalue())


def test_bhavcopies_map_old_symbols_and_never_list_2026(tmp_path):
    _udiff_zip(tmp_path / "20251013.zip", "2025-10-13", [("TATAMOTORS", "EQ", 1, 2, 2.1), ("X", "BE", 1, 1, 1)])
    _udiff_zip(tmp_path / "20251027.zip", "2025-10-27", [("TMPV", "EQ", 3, 4, 4.1)])
    _udiff_zip(tmp_path / "20260102.zip", "2026-01-02", [("TMPV", "EQ", 5, 6, 6.1)])
    files = m.bhav_files(str(tmp_path), "2025-01-01", end="2027-01-01")
    assert [d for d, _ in files] == ["2025-10-13", "2025-10-27"]
    bhav, mism = m.load_bhav(files, ["TMPV"], {"TATAMOTORS": "TMPV"})
    assert bhav[("TMPV", "2025-10-13")]["last"] == 2.1 and bhav[("TMPV", "2025-10-27")]["close"] == 4.0
    assert not mism and len(bhav) == 2


def test_corporate_actions_file_of_2026_is_refused_and_unit_changes_are_found(tmp_path):
    path = tmp_path / "ca_2025.csv"
    path.write_text('"SYMBOL","COMPANY NAME","SERIES","PURPOSE","FACE VALUE","EX-DATE"\n'
                    '"TATAMOTORS","x","EQ","Demerger","2","14-Oct-2025"\n'
                    '"B","x","EQ","Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share","10","03-Nov-2025"\n'
                    '"C","x","EQ","Bonus 1:1","1","26-Aug-2025"\n'
                    '"D","x","EQ","Dividend - Rs 5 Per Share","1","01-Sep-2025"\n', encoding="utf-8")
    dates, unit = m.load_corporate_actions(str(path), {"TATAMOTORS": "TMPV"})
    assert dates["TMPV"] == {"2025-10-14"} and "TMPV" not in unit
    assert unit == {"B": {"2025-11-03"}, "C": {"2025-08-26"}}
    with pytest.raises(RuntimeError):
        m.load_corporate_actions(str(tmp_path / "ca_2026.csv"), {})


# ---- the hand path against the module, end to end on synthetic files ---------------------------

def test_hand_path_agrees_with_the_module_through_the_loaders(tmp_path, monkeypatch):
    rng = random.Random(3)
    days = _weekdays("2025-10-01", 32)
    series = {}
    for j, sym in enumerate(("AAA", "BBB", "CCC", "TTT")):
        bars, p = [], 100.0 + 50 * j
        for d in days:
            t = datetime.strptime(d + " 09:15", "%Y-%m-%d %H:%M")
            for i in range(75):
                o = p
                p = round(p * (1 + rng.gauss(0, 0.002)), 2)
                bars.append({"time": (t + timedelta(minutes=5 * i)).isoformat(), "open": o, "high": max(o, p) + 0.05,
                             "low": min(o, p) - 0.05, "close": p, "volume": rng.randint(100, 5000)})
        series[sym] = bars
    db = tmp_path / "cache.db"
    _cache_db(db, series)
    data = tmp_path / "data"
    (data / "bhav_daily").mkdir(parents=True)
    (data / "corp_actions").mkdir()
    for d in days:
        rows = []
        for sym, bars in series.items():
            day = [b for b in bars if b["time"][:10] == d]
            name = "OLDB" if sym == "BBB" and d < days[15] else sym
            rows.append((name, "EQ", day[0]["open"], round(day[-1]["close"] * (1 + rng.gauss(0, 0.001)), 2),
                         day[-1]["close"]))
        _udiff_zip(data / "bhav_daily" / (d.replace("-", "") + ".zip"), d, rows)
    (data / "bhav_daily" / "symbolchange.csv").write_text("SM_NAME,SM_KEY_SYMBOL,SM_NEW_SYMBOL,SM_APPLICABLE_FROM\n"
                                                          "B Ltd,OLDB,BBB,%s\n" % days[15])
    (data / "corp_actions" / "ca_2025.csv").write_text(
        '"SYMBOL","COMPANY NAME","SERIES","PURPOSE","FACE VALUE","EX-DATE"\n'
        '"CCC","x","EQ","Dividend - Rs 2 Per Share","1","%s"\n' % datetime.strptime(days[30], "%Y-%m-%d").strftime("%d-%b-%Y"),
        encoding="utf-8")
    ind = tmp_path / "industries.csv"
    ind.write_text("symbol,industry\nAAA,Banks\nBBB,Banks\nCCC,Banks\nTTT,Telecom\n")
    rows = [{"symbol": s, "from": "", "to": ""} for s in series]
    monkeypatch.setattr(m, "BHAV_DIR", str(data / "bhav_daily"))
    monkeypatch.setattr(m, "CA_FILE", str(data / "corp_actions" / "ca_2025.csv"))
    monkeypatch.setattr(m, "SYMBOLCHANGE", str(data / "bhav_daily" / "symbolchange.csv"))
    monkeypatch.setattr(m, "INDUSTRIES", str(ind))
    monkeypatch.setattr(m, "BHAV_START", "2025-09-01")
    monkeypatch.setattr(k, "load_membership_rows", lambda path=None: rows)
    conn = m.connect_ro(str(db))
    got = m.assemble(conn)
    ctx = got["ctx"]
    assert got["sessions"] == days[:-5]                       # L40's embargo before 2026
    picks = [(s, d, t) for s in ("AAA", "BBB", "CCC", "TTT") for d in (days[21], days[26])
             for t in ("09:45", "12:00", "13:30")]
    hand = m.Hand(conn, m.BHAV_DIR, m.CA_FILE, m.SYMBOLCHANGE, str(ind), rows, list(series))
    checks = m.hand_check(ctx, hand, picks)
    assert all(not c["mismatches"] for c in checks), [c["mismatches"] for c in checks if c["mismatches"]]
    defined = {n for c in checks for n in m.FEATURES if c["module"][n] is not None}
    assert defined == set(m.FEATURES)
    assert m.lookahead_proof(ctx, picks) and all(c["identical"] for c in m.lookahead_proof(ctx, picks))


# ---- the one pass ---------------------------------------------------------------------------------

def test_the_pass_refuses_without_a_finished_stage0_or_with_a_result(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "STAGE0_OUT", str(tmp_path / "l49_stage0.json"))
    monkeypatch.setattr(m, "RESULT_OUT", str(tmp_path / "l49_result.json"))
    assert any("no stage 0 record" in w for w in m.refusals())
    (tmp_path / "l49_stage0.json").write_text(json.dumps({"status": "HALTED"}))
    assert any("did not finish" in w for w in m.refusals())
    (tmp_path / "l49_result.json").write_text("{}")
    assert any("one run only" in w for w in m.refusals())
    with pytest.raises(SystemExit):
        m.main(["--measure"])                                  # no review note
