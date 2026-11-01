"""Trial 206's loader and rules (prereg-insider-buys.md) on a synthetic
fixture. No real NSE disclosure is used or committed."""
import csv
import datetime as dt
import json
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "research"))

import insider_buys as ib  # noqa: E402
import slow_momentum as sm  # noqa: E402

CSV_HEADERS = ["SYMBOL", "COMPANY", "CATEGORY OF PERSON", "TYPE OF SECURITY (ACQUIRED/DISPLOSED)",
               "VALUE OF SECURITY (ACQUIRED/DISPLOSED)", "ACQUISITION/DISPOSAL TRANSACTION TYPE",
               "DATE OF ALLOTMENT/ACQUISITION FROM", "DATE OF ALLOTMENT/ACQUISITION TO",
               "DATE OF INITMATION TO COMPANY", "MODE OF ACQUISITION", "BROADCASTE DATE AND TIME"]


def _csv_row(symbol="RAYMOND", category="Promoters", sectype="Equity Shares", value="2798547.88",
             txn="Buy", to="04-Feb-2016", intim="05-Feb-2016", mode="Market Purchase",
             broadcast="05-Feb-2016 18:40"):
    return dict(zip(CSV_HEADERS, [symbol, "Raymond Limited", category, sectype, value, txn, to, to,
                                  intim, mode, broadcast]))


def _json_row(**kw):
    r = {"symbol": "RAYMOND", "company": "Raymond Limited", "personCategory": "Promoters",
         "acqMode": "Market Purchase", "tdpTransactionType": "Buy", "secType": "Equity Shares",
         "secVal": "2798547.88", "acqfromDt": "04-Feb-2016", "acqtoDt": "04-Feb-2016",
         "intimDt": "05-Feb-2016", "date": "05-Feb-2016 18:40", "exchange": "BSE,NSE"}
    r.update(kw)
    return r


def _write(tmp_path, csv_rows=(), json_rows=()):
    if csv_rows:
        with open(tmp_path / "pit_2016-02.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(csv_rows[0].keys()))
            w.writeheader()
            w.writerows(csv_rows)
    if json_rows:
        (tmp_path / "pit_2016-02-01_2016-02-07.json").write_text(json.dumps({"data": list(json_rows)}))
    return ib.normalise(ib.load_rows(str(tmp_path)))


def test_csv_export_and_page_json_normalise_to_the_same_event(tmp_path):
    norm, report = _write(tmp_path, [_csv_row()], [_json_row()])
    assert report["mapping_ok"], report
    a, b = norm
    for k in ("symbol", "category", "mode", "txn", "sectype", "value", "to_date", "broadcast"):
        assert a[k] == b[k], k
    assert a["broadcast"] == dt.datetime(2016, 2, 5, 18, 40)
    assert a["value"] == 2798547.88


def test_a_missing_column_fails_the_stage_zero_gate(tmp_path):
    row = _csv_row()
    del row["BROADCASTE DATE AND TIME"]
    norm, report = _write(tmp_path, [row])
    assert not report["mapping_ok"]
    assert "broadcast" in report["files"]["pit_2016-02.csv"]["unmapped"]
    assert norm == []


def test_a_missing_broadcast_time_falls_back_to_the_intimation_date(tmp_path):
    norm, report = _write(tmp_path, [_csv_row(broadcast="-")])
    assert report["missing_broadcast"] == 1
    assert norm[0]["broadcast"] == dt.datetime(2016, 2, 5, 23, 59)


def test_event_rules_and_same_day_aggregation(tmp_path):
    rows = [
        _csv_row(value="600000"), _csv_row(value="500000"),            # one event, ₹11 L
        _csv_row(symbol="DIRCO", category="Director", value="5000000"),  # category
        _csv_row(symbol="ESOPCO", mode="ESOP", value="5000000"),         # mode
        _csv_row(symbol="SELLCO", mode="Market Sale", txn="Sell", value="5000000"),
        _csv_row(symbol="PLEDGECO", txn="Pledge Revoke", value="5000000"),      # not a buy
        _csv_row(symbol="SMALLCO", value="900000"),                      # under ₹10 L
        _csv_row(symbol="WARRCO", sectype="Warrants", value="5000000"),  # not equity
    ]
    norm, _ = _write(tmp_path, rows)
    drops = {k: 0 for k in ("category", "mode", "sectype", "value")}
    events = ib.aggregate(norm, drops)
    assert [e["symbol"] for e in events] == ["RAYMOND"]
    assert events[0]["value"] == 1_100_000 and events[0]["rows"] == 2
    assert drops == {"category": 1, "mode": 3, "sectype": 1, "value": 1}


SESSIONS = ["2016-02-01", "2016-02-02", "2016-02-03", "2016-02-04", "2016-02-05", "2016-02-08", "2016-02-09"]


def test_entry_is_the_first_open_after_the_broadcast():
    at = lambda s: ib.entry_session(SESSIONS, dt.datetime.fromisoformat(s))  # noqa: E731
    assert SESSIONS[at("2016-02-02 18:40")] == "2016-02-03"   # evening -> next session
    assert SESSIONS[at("2016-02-02 08:30")] == "2016-02-02"   # before the open -> same day
    assert SESSIONS[at("2016-02-05 18:00")] == "2016-02-08"   # Friday evening -> Monday
    assert SESSIONS[at("2016-02-06 11:00")] == "2016-02-08"   # Saturday -> Monday
    assert at("2016-02-09 16:00") is None                     # nothing after the last session


def _chain(n, price=100.0):
    return {"idx": list(range(n)), "close": [price] * n, "raw": [price] * n,
            "open": [price] * n, "val": [1e7] * n}


def test_ticket_return_is_net_of_trial_126_costs_plus_the_extra_slippage():
    c = _chain(10)
    c["close"][6] = c["raw"][6] = 105.0
    gross, net, shares = ib.event_return(c, 2, 6)
    assert shares == 500 and abs(gross - 0.05) < 1e-12
    vin, vout = 50_000.0, 52_500.0
    expected = (vout - vin - sm.buy_cost(vin) - vin * 0.0005 - sm.sell_cost(vout) - vout * 0.0005) / vin
    assert abs(net - expected) < 1e-12
    assert net < gross - 0.004          # about 42 bp plus the DP charge came off


def test_adjusted_open_uses_the_same_factor_as_that_days_close():
    c = _chain(3)
    c["raw"][1], c["close"][1], c["open"][1] = 200.0, 100.0, 198.0   # a 2:1 split adjusted later
    assert abs(ib.adjusted_open(c, 1) - 99.0) < 1e-12


def test_no_trade_on_the_entry_day_or_a_price_above_the_ticket_is_untradable():
    c = _chain(10)
    del c["idx"][3], c["close"][3], c["raw"][3], c["open"][3], c["val"][3]
    assert ib.event_return(c, 3, 7) is None
    assert ib.event_return(_chain(10, price=60_000.0), 2, 6) is None


def test_clustered_t_matches_the_plain_t_for_singleton_clusters_and_falls_with_clustering():
    xs = [0.01, -0.02, 0.03, 0.005, -0.01, 0.02]
    assert abs(ib.clustered_t(xs, list(range(6))) - sm.t_stat(xs)) < 1e-9
    dup = xs + xs
    assert ib.clustered_t(dup, list(range(6)) * 2) < sm.t_stat(dup)


def _market(n_sessions=420, names=("RAYMOND", "DIRCO", "THIRD")):
    d, sessions = dt.date(2014, 6, 2), []
    while len(sessions) < n_sessions:
        if d.weekday() < 5:
            sessions.append(d.isoformat())
        d += dt.timedelta(days=1)
    return sessions, {n: _chain(n_sessions) for n in names}


def test_build_events_applies_universe_overlap_and_held_out_rules(tmp_path):
    sessions, chains = _market()
    chains["PRICEY"] = _chain(len(sessions), price=60_000.0)          # one share is over the ticket
    assert sessions[-1] >= "2016-01-04"
    rows = [
        _csv_row(broadcast="01-Dec-2015 18:00", to="30-Nov-2015"),
        _csv_row(broadcast="03-Dec-2015 18:00", to="02-Dec-2015"),   # inside the open window: overlap
        _csv_row(broadcast="15-Dec-2015 18:00", to="14-Dec-2015"),   # after the exit: a new event
        _csv_row(symbol="NOCHAIN", broadcast="02-Dec-2015 18:00"),   # no price chain
        _csv_row(symbol="DIRCO", broadcast="05-Jan-2026 18:00"),     # held out
        _csv_row(symbol="THIRD", broadcast="01-Mar-2015 18:00"),     # before the PIT regime
        _csv_row(symbol="PRICEY", broadcast="02-Dec-2015 18:00"),    # untradable at one ticket
        _csv_row(symbol="OLDRAY", broadcast="28-Dec-2015 18:00"),    # an old name of RAYMOND
    ]
    norm, report = _write(tmp_path, rows)
    assert report["held_out"] == 1 and len(norm) == len(rows) - 1      # 2026 never reaches the run
    events, drops = ib.build_events(norm, sessions, chains, {}, False, aliases={"OLDRAY": "RAYMOND"})
    assert [(e["symbol"], e["chain"], sessions[e["entry"]], sessions[e["exit"]]) for e in events] == [
        ("RAYMOND", "RAYMOND", "2015-12-02", "2015-12-08"), ("RAYMOND", "RAYMOND", "2015-12-16", "2015-12-22"),
        ("OLDRAY", "RAYMOND", "2015-12-29", "2016-01-04")]
    assert drops["overlap"] == 1 and drops["unmatched"] == 1 and drops["window"] == 1
    assert drops["held_out"] == 0 and drops["zero_shares"] == 1 and drops["no_trade"] == 0
    priced = ib.price_events(events, chains, drops)
    assert len(priced) == 3 and all(abs(p["bench"]) < 1e-12 for p in priced)   # flat market, zero benchmark
    assert all(p["excess"] == p["net"] for p in priced)


def test_the_universe_is_the_top_n_by_trial_126s_ranking():
    sessions, chains = _market()
    chains["BEONLY"] = dict(_chain(len(sessions)), ser=[1] * len(sessions))   # BE rows: never ranked
    assert "BEONLY" not in ib.mw.eq_view(chains)
    chains["THIRD"]["raw"] = [10.0] * len(sessions)                  # under the ₹20 floor
    chains["DIRCO"]["val"] = [1e5] * len(sessions)                   # thinnest
    assert ib.liquid_at(chains, 400, n=1) == ["RAYMOND"]
    assert set(ib.liquid_at(ib.mw.eq_view(chains), 400)) == {"RAYMOND", "DIRCO"}
    assert ib.liquid_at(chains, 100) == []                           # under 250 sessions of history


def test_stage_zero_flags_missing_months_and_too_few_events(tmp_path):
    sessions, chains = _market()
    norm, report = _write(tmp_path, [_csv_row(broadcast="01-Dec-2015 18:00", to="30-Nov-2015")])
    events, drops = ib.build_events(norm, sessions, chains, {}, False)
    s0 = ib.stage0(norm, report, events, drops, sessions)
    assert s0["gate"]["columns"] and not s0["gate"]["export_complete"] and not s0["gate"]["enough_events"]
    assert "2016-01" in s0["missing_months"] and not s0["proceed"]
    assert s0["lags"]["transaction_to_broadcast_weekdays"] == {1: 1}   # 30 Nov (Mon) -> 1 Dec (Tue)
    assert s0["lags"]["broadcast_to_entry_days"] == {1: 1}


def test_verdict_requires_every_check():
    sessions, _ = _market()
    priced = [{"entry": 300 + i, "exit": 304 + i, "broadcast": dt.datetime(2015, 8, 1), "gross": 0.01,
               "net": 0.006, "bench": 0.0, "excess": 0.006 if i % 7 else -0.002} for i in range(100)]
    v = ib.verdict(priced, sessions)
    assert v["checks"]["mean_positive_t"] and v["checks"]["floor_25bp"] and v["checks"]["n_events"]
    assert v["whole"]["t"] >= 2.24 and v["whole"]["t_clustered"] == round(v["whole"]["t"], 2)
    assert not v["checks"]["both_halves"]        # no event after 2021 -> the second half is empty
    assert not v["pass"]
