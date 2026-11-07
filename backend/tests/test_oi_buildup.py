"""Trial 207's aggregator and rules (prereg-oi-buildup.md) on synthetic data.
No real NSE file is used or committed."""
import io
import os
import sys
import zipfile

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "research"))

import fo_oi_aggregate as agg  # noqa: E402
import oi_buildup as ob  # noqa: E402


def _zip(text, name="x.csv"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, text)
    return buf.getvalue()


def test_parse_old_format_sums_expiries_and_skips_index_futures_and_options():
    text = ("INSTRUMENT,SYMBOL,EXPIRY_DT,STRIKE_PR,OPTION_TYP,OPEN,HIGH,LOW,CLOSE,SETTLE_PR,CONTRACTS,"
            "VAL_INLAKH,OPEN_INT,CHG_IN_OI,TIMESTAMP,\n"
            "FUTIDX,NIFTY,29-Jan-2015,0,XX,1,1,1,1,1,1,1,999,0,01-JAN-2015,\n"
            "FUTSTK,ACC,29-Jan-2015,0,XX,1,1,1,1,1,1,1,1000,0,01-JAN-2015,\n"
            "FUTSTK,ACC,26-Feb-2015,0,XX,1,1,1,1,1,1,1,250,0,01-JAN-2015,\n"
            "OPTSTK,ACC,29-Jan-2015,1400,CE,1,1,1,1,1,1,1,777,0,01-JAN-2015,\n")
    day, syms, expiry_day = agg.parse(_zip(text))
    assert day == "2015-01-01"
    assert syms == {"ACC": [1250, 2]}
    assert expiry_day is False


def test_parse_udiff_format_and_flags_an_expiry_day():
    text = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,"
            "StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,"
            "SttlmPric,OpnIntrst,ChngInOpnIntrst\n"
            "2025-01-30,2025-01-30,FO,NSE,STF,1,,TCS,,2025-01-30,2025-01-30,,,X,1,1,1,1,1,1,1,1,500,0\n"
            "2025-01-30,2025-01-30,FO,NSE,STF,2,,TCS,,2025-02-27,2025-02-27,,,X,1,1,1,1,1,1,1,1,4000.0,0\n"
            "2025-01-30,2025-01-30,FO,NSE,IDF,3,,NIFTY,,2025-02-27,2025-02-27,,,X,1,1,1,1,1,1,1,1,9,0\n")
    day, syms, expiry_day = agg.parse(_zip(text))
    assert (day, syms, expiry_day) == ("2025-01-30", {"TCS": [4500, 2]}, True)


def test_state_needs_both_signs_nonzero():
    assert ob.state(0.01, 0.02) == ob.LB
    assert ob.state(0.01, -0.02) == ob.SC
    assert ob.state(-0.01, 0.02) == ob.SB
    assert ob.state(-0.01, -0.02) == ob.LU
    assert ob.state(0.0, 0.02) is None and ob.state(0.01, 0.0) is None


def _market(n=12):
    sessions = [f"2015-02-{d:02d}" for d in range(2, 2 + n)]
    up = {"idx": list(range(n)), "close": [100.0 + i for i in range(n)], "raw": [100.0 + i for i in range(n)],
          "open": [100.0 + i for i in range(n)]}
    return sessions, {"UP": up, "UP2": dict(up)}


def _days(sessions, chains, by_date, expiries=(), share_days=()):
    f_dates = sorted(by_date)
    return ob.signal_days(by_date, f_dates, set(expiries), sessions, chains, lambda s: s, set(share_days))


def test_signal_days_drop_expiry_the_day_after_first_day_and_share_changes():
    sessions, chains = _market()
    by_date = {d: {"UP": 100 + i, "UP2": 100 + i} for i, d in enumerate(sessions)}
    by_date[sessions[1]]["NEW"] = 50          # first futures day; also not in the cash chains
    by_date[sessions[2]]["NEW"] = 60
    days, drops, match = _days(sessions, chains, by_date, expiries=[sessions[3]],
                               share_days=[("UP2", sessions[6])])
    got = {d: states for d, _k, states in days}
    assert sessions[3] not in got and sessions[4] not in got      # expiry, then the session after it
    assert got[sessions[1]] == {"UP": ob.LB, "UP2": ob.LB}
    assert got[sessions[6]] == {"UP": ob.LB}                       # UP2's split day is dropped
    assert drops["expiry"] == 2 and drops["after_expiry"] == 2 and drops["share_change"] == 1
    assert drops["unmatched"] == 2 and match["matched"] < match["symbol_days"]


def test_a_missing_previous_fo_file_drops_the_day_instead_of_comparing_across_a_gap():
    sessions, chains = _market()
    by_date = {d: {"UP": 100 + i} for i, d in enumerate(sessions) if i != 4}
    days, drops, _ = _days(sessions, chains, by_date)
    assert sessions[5] not in {d for d, _k, _s in days}
    assert drops["gap"] == 1


def test_build_events_enter_next_open_and_drop_overlaps_and_late_exits():
    sessions, chains = _market()
    by_date = {d: {"UP": 100 + i} for i, d in enumerate(sessions)}
    days, _, _ = _days(sessions, chains, by_date)
    events, drops = ob.build_events(days, sessions, chains, ob.LB)
    assert [(e["entry"], e["exit"]) for e in events] == [(2, 6), (7, 11)]   # signals on 1 and 6
    assert drops["overlap"] == 4 and drops["window"] == 5                    # signals 7-11 exit past session 11
    assert events[0]["universe"] == frozenset({"UP"})


def test_verdict_runs_end_to_end_on_synthetic_priced_events():
    lb = [{"date": f"20{10 + i // 100:02d}-01-01", "entry": i, "excess": 0.003 + (i % 7) * 1e-4,
           "gross": 0.01, "net": 0.006} for i in range(0, 1500, 5)]
    sc = [{**p, "excess": p["excess"] - 0.002} for p in lb]
    out = ob.verdict(lb, sc)
    assert out["long_buildup"]["events"] == len(lb)
    assert out["checks"]["6_n_events"] and out["checks"]["5_floor_25bp"]
    assert out["mechanism"]["mean_bp"] == 20.0


def test_stage0_gates_on_missing_files_and_lists_parse_counts_by_month():
    sessions, chains = _market()
    by_date = {d: {"UP": 100 + i} for i, d in enumerate(sessions) if i != 4}
    contracts = {d: 3 for d in by_date}
    days, sdrops, match = _days(sessions, chains, by_date)
    events, edrops = {}, {}
    for s in (ob.LB, ob.SC):
        events[s], edrops[s] = ob.build_events(days, sessions, chains, s)
    s0 = ob.stage0(sessions, by_date, sorted(by_date), set(), contracts, days, sdrops, match, events, edrops)
    assert s0["missing"] == [sessions[4]] and not s0["gates"]["completeness"] and not s0["proceed"]
    assert s0["parse_by_month"]["2015-02"] == {"days": 11, "stocks_per_day": 1.0, "contracts_per_day": 3.0}
    assert s0["months_without_one_expiry"] == {"2015-02": 0}
