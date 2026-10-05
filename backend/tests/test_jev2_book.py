"""Jev 2 (jev2_book.py, README section 128, prereg-jev2-book.md): the blind
state, the fourteen Nouls and the frozen combination rule, fills shared with
Jev 1 on the common names (read-only), the clustered statistics, the missed
day, and that nothing here writes Jev 1's state. TypeSafe is a fake; no
Kite call is made."""
import datetime
import hashlib
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jev_book as jb  # noqa: E402
import jev2_book as j2  # noqa: E402

NOW = datetime.datetime(2026, 10, 6, 9, 45)
DAY = "2026-10-06"


def _row(i, side="LONG"):
    return {"symbol": f"S{i}", "name": f"S{i} Ltd", "industry": "Banks", "ltp": 100.0 + i, "vwap": 99.0 + i,
            "chg_pct": 0.5, "gap_pct": 0.2, "rvol": 1.4, "rs_today": 0.3, "or_high": 101.0 + i, "or_low": 99.5 + i,
            "sector_chg_pct": 0.4, "atr_pct": 1.8, "rs10": 2.0, "pct_from_high": 5.0, "pct_from_low": 20.0,
            "turnover_cr": 500.0, "beta": 1.0, "event": None, "large_deals": None,
            # The real shape of market_catalysts' output: a sentiment score, per-headline scores, URLs, raw ages
            "catalyst": {"score": 0.42, "count": 3, "top": "dated",
                         "headlines": [{"title": "dated", "score": 0.6, "llm_scored": True, "url": "u", "age_h": 0.5},
                                       {"title": "undated", "score": 0.2, "llm_scored": False, "url": "u", "age_h": 24.0},
                                       {"title": "old", "score": 0.4, "llm_scored": False, "url": "u", "age_h": 30.0}]},
            "score_side": side, "side": "", "final_score": 61.0, "score": 61.0, "daily_trend": "up",
            "reasons": [{"text": "Above VWAP"}], "swing_patterns": ["flag"], "shadow_side": "LONG",
            "sector_trend": "up", "long_only": False,
            "brain": {"setup": "Bullish confluence", "bias": "long", "regime": "trending", "structure": "range",
                      "htf_trend": "flat", "rsi": 60.0, "adx": 25.0, "support": 98.0, "resistance": 103.0,
                      "patterns": [{"name": "Hammer", "bias": "bullish"}], "fundamentals_label": "Strong",
                      "news_headlines": [{"title": "dated", "age_h": 0.5, "publisher": "P1", "url": "u"},
                                         {"title": "undated", "age_h": 24.0, "publisher": "P2", "url": "u"},
                                         {"title": "old", "age_h": 30.0, "publisher": "P3", "url": "u"}]}}


def _scanner(n=3, date=DAY):
    rows = [_row(i, "LONG" if i % 2 == 0 else "SHORT") for i in range(n)]
    return {"session_date": date, "active": [r["symbol"] for r in rows], "rows": rows,
            "market": {"bias": "risk-on", "reasons": ["NIFTY up"], "nifty": {"ltp": 22500.0, "chg_pct": 0.4,
                                                                             "trend": "down", "above_open": True},
                       "vix": 14.0, "breadth": {"adv": 60, "dec": 40, "pct_adv": 60.0},
                       "fii_dii": {"date": "05-Oct-2026", "fii_net_cr": -100.0, "dii_net_cr": 200.0}}}


def _resp(p=None, status=200, model="jev-1.13.0"):
    """A fake System One response: every Noul at `p` (a dict by key, or one number)."""
    answers = {}
    for key in j2.KEYS:
        v = p.get(key, 0.5) if isinstance(p, dict) else (p if p is not None else 0.5)
        answers[key + "_a"] = {"type": "noul", "noul": v}
        answers[key + "_b"] = {"type": "noul", "noul": v}
    body = {"model": model, "usage": {"input_tokens": 1500, "output_tokens": 0}, "answers": answers}
    return types.SimpleNamespace(status_code=status, json=lambda: body, text=json.dumps(body), headers={})


def _post(responses):
    calls = []

    def post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers})
        return responses[min(len(calls) - 1, len(responses) - 1)]
    post.calls = calls
    return post


BULL = {"news_positive": 0.8, "news_negative": 0.2, "strength_extending": 0.7, "weakness_extending": 0.3,
        "sector_up": 0.7, "sector_down": 0.3, "move_exhausted": 0.2}      # S = 0.467, p = 0.733 -> buy
BEAR = {k: 1 - v for k, v in BULL.items()}
BEAR["move_exhausted"] = 0.2                                              # p = 0.267 -> short
FLAT = {**BULL, "news_positive": 0.6, "strength_extending": 0.5, "sector_up": 0.5}   # S = 0.267, p = 0.633 -> skip


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")


def _digest(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest() if os.path.exists(path) else None


# --- the blind state ---------------------------------------------------------------------------------

def stock_keys(state):
    return set(state["stock"])


def test_the_state_is_blind_and_drops_undated_headlines():
    s = j2.build_state(_row(0), _scanner()["market"], NOW)
    text = json.dumps(s)
    for k in j2.WITHHELD:
        assert f'"{k}"' not in text, k
    assert "Bullish confluence" not in text and "Above VWAP" not in text and "risk-on" not in text
    assert "catalyst" not in stock_keys(s) and "0.42" not in text and "llm_scored" not in text and '"url"' not in text
    assert "24.0" not in text and json.dumps(s).count('"dated"') == 1          # no second copy of the headlines
    stock = s["stock"]
    assert stock["ltp"] == 100.0 and stock["vwap"] == 99.0 and stock["vwap_distance_pct"] == pytest.approx(1.01, abs=0.001)
    assert stock["opening_range"] == {"high": 101.0, "low": 99.5} and stock["sector_chg_pct"] == 0.4
    assert stock["rsi"] == 60.0 and stock["support"] == 98.0
    assert [h["title"] for h in stock["headlines"]] == ["dated", "old"]      # the 24.0 sentinel is dropped
    assert stock["headlines"][0] == {"title": "dated", "publisher": "P1", "hours_before_decision": 0.5}
    assert s["market"] == {"nifty": {"ltp": 22500.0, "chg_pct": 0.4, "above_open": True}, "vix": 14.0,
                           "breadth": {"adv": 60, "dec": 40, "pct_adv": 60.0},
                           "fii_dii": {"date": "05-Oct-2026", "fii_net_cr": -100.0, "dii_net_cr": 200.0}}
    assert s["round_trip_cost_pct"] == 0.17 and s["time_ist"] == "2026-10-06 09:45"


# --- the questions and the frozen rule -------------------------------------------------------------------

def test_fourteen_nouls_in_one_pinned_request_and_the_rule_decides(tmp_path, key):
    path = str(tmp_path / "s.json")
    post = _post([_resp(BULL), _resp(BEAR), _resp(FLAT)])
    j2.decide_round(_scanner(), NOW, lambda s: 100.0, post=post, state_path=path, sleep=lambda s: None)
    assert len(post.calls) == 3
    c = post.calls[0]["json"]
    assert c["model"] == "jev-1.13.0" and len(c["questions"]) == 14
    assert all(q["type"] == "noul" for q in c["questions"].values())
    assert set(c["questions"]) == {k + s for k in j2.KEYS for s in ("_a", "_b")}
    assert "test-key" not in json.dumps(c)
    ds = j2.load_state(path)["days"][DAY]["decisions"]
    assert [d["action"] for d in ds] == ["buy", "short", "skip"]
    assert ds[0]["p_combined"] == pytest.approx(0.5 + 0.4667 / 2, abs=0.001)
    assert ds[0]["model"] == "jev-1.13.0" and ds[0]["usage"]["input_tokens"] == 1500
    assert ds[0]["raw"]["news_positive_a"] == 0.8 and ds[0]["p"]["news_positive"] == 0.8
    assert ds[0]["fill_source"] == "own" and ds[0]["entry"] == 100.0 and ds[0]["shared"] is False


def test_the_combination_rule_thresholds_and_the_exhaustion_veto():
    conf = j2.cfg()
    assert conf["buy_at"] == 0.65 and conf["short_at"] == 0.35 and conf["exhausted_veto"] == 0.70
    edge = {"news_positive": 0.65, "news_negative": 0.35, "strength_extending": 0.65, "weakness_extending": 0.35,
            "sector_up": 0.65, "sector_down": 0.35, "move_exhausted": 0.1}       # S = 0.30 exactly -> p 0.65
    assert j2.combine(edge, conf)[0] == "buy"
    assert j2.combine({**edge, "sector_up": 0.64}, conf)[0] == "skip"               # just inside the band
    assert j2.combine({**edge, "move_exhausted": 0.70}, conf)[0] == "skip"          # veto at the threshold
    assert j2.combine({**edge, "move_exhausted": 0.69}, conf)[0] == "buy"
    assert j2.combine(BEAR, conf)[0] == "short" and j2.combine({**BEAR, "move_exhausted": 0.9}, conf)[0] == "skip"
    assert j2.combine({**edge, "sector_up": None}, conf) == (None, None, None)
    act, pc, s = j2.combine({**edge, "move_exhausted": None}, conf)          # veto unanswerable -> skip
    assert act == "skip" and pc == pytest.approx(0.65) and s == pytest.approx(0.30)


def test_the_two_wordings_are_averaged():
    body = _resp(BULL).json()
    body["answers"]["news_positive_b"]["noul"] = 0.4
    p = j2.parse_answers(body)["p"]
    assert p["news_positive"] == pytest.approx(0.6)


# --- fills shared with Jev 1, read only ------------------------------------------------------------------

def _jev1_day(scanner, entries, exits=None):
    """Jev 1's record of the day, as jev_book writes it, on the first two names."""
    decs = []
    for sym, entry in entries.items():
        row = next(r for r in scanner["rows"] if r["symbol"] == sym)
        d = {"symbol": sym, "action": "buy", "p_up": 0.6, "entry": entry,
             "state": {"stock": {"ltp": row["ltp"], "vwap": row["vwap"]}}}
        if exits and sym in exits:
            d["exit"] = exits[sym]
            d["net_bp"] = (exits[sym] / entry - 1) * 1e4 - jb.round_trip_bp()
            d["move_bp"] = (exits[sym] / entry - 1) * 1e4
        decs.append(d)
    return {"status": "open", "decisions": decs}


def test_shared_names_reuse_jev1s_fills_and_the_rest_fetch_their_own(tmp_path, key, monkeypatch):
    path = str(tmp_path / "s.json")
    j1_path = str(tmp_path / "jev1.json")
    sc = _scanner(3)
    jev1 = _jev1_day(sc, {"S0": 100.25, "S1": 101.5})
    jb.save_state({"days": {DAY: jev1}, "status": "active"}, j1_path)
    monkeypatch.setattr(jb, "STATE_PATH", j1_path)
    before = _digest(j1_path)
    sc["rows"][1]["ltp"] = 101.9                         # S1: Jev 1 read a different scan -> own fill
    fetched = []

    def ltp(sym):
        fetched.append(sym)
        return 100.0

    j2.decide_round(sc, NOW, ltp, post=_post([_resp(BULL)]), state_path=path, sleep=lambda s: None,
                    jev1=j2.jev1_day(DAY))
    ds = {d["symbol"]: d for d in j2.load_state(path)["days"][DAY]["decisions"]}
    assert ds["S0"]["entry"] == 100.25 and ds["S0"]["fill_source"] == "jev1" and ds["S0"]["shared"]
    assert ds["S1"]["entry"] == 100.0 and ds["S1"]["fill_source"] == "own" and ds["S1"]["shared"]
    assert ds["S2"]["entry"] == 100.0 and ds["S2"]["fill_source"] == "own" and not ds["S2"]["shared"]
    assert fetched == ["S1", "S2"]
    # The close: S0 reuses Jev 1's exit, S1 and S2 fetch their own.
    jev1_closed = _jev1_day(sc, {"S0": 100.25, "S1": 101.5}, exits={"S0": 102.0, "S1": 103.0})
    jb.save_state({"days": {DAY: jev1_closed}, "status": "active"}, j1_path)
    closed_digest = _digest(j1_path)
    fetched.clear()
    j2.close_round(NOW.replace(hour=15, minute=8), lambda s: 101.0, state_path=path, jev1=j2.jev1_day(DAY))
    ds = {d["symbol"]: d for d in j2.load_state(path)["days"][DAY]["decisions"]}
    assert ds["S0"]["exit"] == 102.0 and ds["S0"]["exit_source"] == "jev1"
    assert ds["S1"]["exit"] == 101.0 and ds["S1"]["exit_source"] == "own"
    rt = jb.round_trip_bp()
    assert ds["S0"]["net_bp"] == pytest.approx((102.0 / 100.25 - 1) * 1e4 - rt)
    s = j2.summary(state_path=path)
    # "Without own shared fills" drops S1 (own entry) but keeps S0 (Jev 1's at both ends) and S2 (not shared).
    assert s["mean_net_bp_without_own_shared_fills"] == pytest.approx(st_mean([ds["S0"]["net_bp"], ds["S2"]["net_bp"]]))
    assert ds["S0"]["scanner_net_bp"] == pytest.approx((102.0 / 100.25 - 1) * 1e4 - rt)      # S0 scanner LONG
    assert ds["S1"]["scanner_net_bp"] == pytest.approx(-(101.0 / 100.0 - 1) * 1e4 - rt)      # S1 scanner SHORT
    assert _digest(j1_path) == closed_digest                      # Jev 1's file untouched by the close
    # The summary pairs Jev 2 with Jev 1 on S0 only (S1's Jev 1 decision is read from the closed record too).
    s = j2.summary(state_path=path)
    assert s["paired_vs_jev1_n"] == 2 and s["shared_n"] == 2 and s["extra_n"] == 1
    assert s["paired_vs_jev1_bp"] == pytest.approx(st_mean([ds["S0"]["net_bp"] - jev1_closed["decisions"][0]["net_bp"],
                                                            ds["S1"]["net_bp"] - jev1_closed["decisions"][1]["net_bp"]]))
    assert s["models"] == ["jev-1.13.0"] and s["skip_rate"] == 0.0
    assert _digest(j1_path) == closed_digest and before is not None   # nor by the summary


def st_mean(xs):
    return sum(xs) / len(xs)


def test_jev2_never_writes_jev1s_state(tmp_path, key, monkeypatch):
    j1_path = str(tmp_path / "jev1.json")
    jb.save_state({"days": {DAY: _jev1_day(_scanner(2), {"S0": 100.0})}, "status": "active"}, j1_path)
    monkeypatch.setattr(jb, "STATE_PATH", j1_path)
    before = _digest(j1_path)
    path = str(tmp_path / "s.json")
    j2.decide_round(_scanner(2), NOW, lambda s: 100.0, post=_post([_resp(BULL)]), state_path=path,
                    sleep=lambda s: None, jev1=j2.jev1_day(DAY))
    j2.close_round(NOW.replace(hour=15, minute=8), lambda s: 101.0, state_path=path, jev1=j2.jev1_day(DAY))
    j2.summary(state_path=path)
    assert _digest(j1_path) == before


# --- skips, exclusions, outages, the missed day ---------------------------------------------------------

def test_a_missing_move_exhausted_answer_is_a_skip_with_its_reason(tmp_path, key):
    path = str(tmp_path / "s.json")
    body = _resp(BULL).json()
    del body["answers"]["move_exhausted_a"], body["answers"]["move_exhausted_b"]
    resp = types.SimpleNamespace(status_code=200, json=lambda: body, text="", headers={})
    j2.decide_round(_scanner(1), NOW, lambda s: 100.0, post=_post([resp]), state_path=path, sleep=lambda s: None)
    d = j2.load_state(path)["days"][DAY]["decisions"][0]
    assert d["action"] == "skip" and "move_exhausted" in d["skip_reason"] and not d.get("excluded")
    assert d["p_combined"] == pytest.approx(0.7333, abs=1e-3)


def test_beats_the_scanner_is_scored_on_every_decision_with_skips_at_zero(tmp_path, key):
    path = str(tmp_path / "s.json")
    j2.decide_round(_scanner(3), NOW, lambda s: 100.0, post=_post([_resp(BULL), _resp(FLAT), _resp(FLAT)]),
                    state_path=path, sleep=lambda s: None)
    j2.close_round(NOW.replace(hour=15, minute=8), lambda s: 101.0, state_path=path)     # +100 bp move everywhere
    rt = jb.round_trip_bp()
    s = j2.summary(state_path=path)
    # S0 buy (scanner LONG), S1 skip (scanner SHORT), S2 skip (scanner LONG): three decisions, one trade.
    assert s["traded"] == 1 and s["decisions"] == 3 and s["scanner_n"] == 3
    assert s["mean_net_bp"] == pytest.approx(100.0 - rt)                                      # item 1: trades only
    scanner = [100.0 - rt, -100.0 - rt, 100.0 - rt]
    assert s["scanner_mean_net_bp"] == pytest.approx(sum(scanner) / 3)
    assert s["paired_vs_scanner_bp"] == pytest.approx(((100.0 - rt) - scanner[0] + (0 - scanner[1]) + (0 - scanner[2])) / 3)


def test_a_skip_costs_nothing_and_counts(tmp_path, key):
    path = str(tmp_path / "s.json")
    j2.decide_round(_scanner(1), NOW, lambda s: 100.0, post=_post([_resp(FLAT)]), state_path=path, sleep=lambda s: None)
    j2.close_round(NOW.replace(hour=15, minute=8), lambda s: 90.0, state_path=path)
    d = j2.load_state(path)["days"][DAY]["decisions"][0]
    s = j2.summary(state_path=path)
    assert d["action"] == "skip" and d["net_bp"] == 0.0 and d["scanner_net_bp"] != 0.0
    assert s["traded"] == 0 and s["decisions"] == 1 and s["skips"] == 1 and s["skip_rate"] == 1.0


def test_no_live_prices_skips_the_day_and_jev_unavailable_records_the_error(tmp_path, key):
    path = str(tmp_path / "s.json")
    post = _post([_resp(BULL)])
    j2.decide_round(_scanner(2), NOW, lambda s: 100.0, post=post, state_path=path, sleep=lambda s: None, live=lambda: False)
    assert j2.load_state(path)["days"][DAY]["status"] == "no_live_prices" and post.calls == []
    path2 = str(tmp_path / "s2.json")
    j2.decide_round(_scanner(2), NOW, lambda s: 100.0, post=_post([_resp(status=503)]), state_path=path2, sleep=lambda s: None)
    day = j2.load_state(path2)["days"][DAY]
    assert day["status"] == "jev_unavailable" and "unavailable" in day["error"] and day["decisions"] == []
    assert j2.summary(state_path=path2)["sessions_closed"] == 0


def test_a_fill_without_a_live_price_is_excluded(tmp_path, key):
    path = str(tmp_path / "s.json")

    def ltp(sym):
        raise RuntimeError("Kite is not connected")

    j2.decide_round(_scanner(1), NOW, ltp, post=_post([_resp(BULL)]), state_path=path, sleep=lambda s: None)
    j2.close_round(NOW.replace(hour=15, minute=8), lambda s: 101.0, state_path=path)
    d = j2.load_state(path)["days"][DAY]["decisions"][0]
    assert d["entry"] is None and d["excluded"] == "no live entry price" and "net_bp" not in d
    assert j2.summary(state_path=path)["traded"] == 0


def test_maybe_decide_waits_for_jev1_captures_the_0945_scan_and_records_a_missed_day(tmp_path, monkeypatch):
    j1_path = str(tmp_path / "jev1.json")
    monkeypatch.setattr(jb, "STATE_PATH", j1_path)
    monkeypatch.setattr(j2, "STATE_PATH", str(tmp_path / "s.json"))
    monkeypatch.setattr(j2, "_pending", {"date": None, "scanner": None, "at": None})
    started = []
    monkeypatch.setattr(j2.threading, "Thread", lambda target, name, daemon: types.SimpleNamespace(start=lambda: started.append(name)))
    sc = _scanner(2)
    # Before 09:45: nothing. At 09:45 Jev 1 is running: the scan is captured, the round waits.
    assert j2.maybe_decide(sc, NOW.replace(hour=9, minute=44)) is False and j2._pending["date"] is None
    monkeypatch.setattr(jb, "_running", {"decide": True})
    assert j2.maybe_decide(sc, NOW) is False and j2._pending["scanner"] is sc
    # Jev 1 finished and recorded its day: Jev 2 starts on the captured scan, not the newer one.
    jb.save_state({"days": {DAY: {"status": "open", "decisions": []}}, "status": "active"}, j1_path)
    monkeypatch.setattr(jb, "_running", {"decide": False})
    newer = _scanner(2)
    assert j2.maybe_decide(newer, NOW.replace(minute=47)) is True and started == ["jev2-book"]
    assert j2._pending["scanner"] is sc and j2._running["decide"] is True
    j2._running["decide"] = False
    # A day on which Jev 1 never finished by 10:00 is recorded as missed, once, and never re-run.
    monkeypatch.setattr(j2, "_pending", {"date": None, "scanner": None, "at": None})
    monkeypatch.setattr(j2, "STATE_PATH", str(tmp_path / "s3.json"))
    monkeypatch.setattr(jb, "_running", {"decide": True})
    assert j2.maybe_decide(sc, NOW.replace(minute=50)) is False
    assert j2.maybe_decide(sc, NOW.replace(hour=10, minute=1)) is False
    day = j2.load_state()["days"][DAY]
    assert day["status"] == "missed" and "10:00" in day["error"]
    monkeypatch.setattr(jb, "_running", {"decide": False})
    assert j2.maybe_decide(sc, NOW.replace(hour=10, minute=2)) is False and len(started) == 1


def test_jev1_disabled_or_switched_off_lets_jev2_run_alone(tmp_path, monkeypatch):
    j1_path = str(tmp_path / "jev1.json")
    monkeypatch.setattr(jb, "STATE_PATH", j1_path)
    monkeypatch.setattr(jb, "_running", {"decide": False})
    assert j2.jev1_finished(DAY) is False                      # nothing recorded yet, Jev 1 enabled
    jb.save_state({"days": {}, "status": "switched_off"}, j1_path)
    assert j2.jev1_finished(DAY) is True
    jb.save_state({"days": {}, "status": "active"}, j1_path)
    monkeypatch.setattr(jb, "cfg", lambda: {**jb.DEFAULTS, "enabled": False})
    assert j2.jev1_finished(DAY) is True


# --- the statistics and the kill rule -----------------------------------------------------------------

def test_clustered_t_treats_a_session_as_one_cluster():
    xs = [10.0, 12.0, 8.0, 10.0, -10.0, -8.0, -12.0, -10.0]
    g = ["d1"] * 4 + ["d2"] * 4
    assert j2.clustered_t(xs, g) == pytest.approx(0.0, abs=1e-9)
    xs2 = [10.0, 12.0, 8.0, 10.0, 14.0, 12.0, 16.0, 14.0]          # session means 10 and 14, overall 12
    plain = j2._t(xs2)
    cl = j2.clustered_t(xs2, g)
    assert plain == pytest.approx(12.0 / (2.6186 / 8 ** 0.5), abs=0.01)
    assert cl == pytest.approx(6.0)                                # se = sqrt(2 * (64 + 64) / 64) = 2
    assert j2.clustered_t(xs2, ["d1"] * 8) is None


def test_kill_rule_switches_the_book_off(tmp_path, key, monkeypatch):
    path = str(tmp_path / "s.json")
    monkeypatch.setattr(j2, "cfg", lambda: {**j2.DEFAULTS, "kill_after": 4})
    j2.decide_round(_scanner(4), NOW, lambda s: 100.0, post=_post([_resp(BULL)]), state_path=path, sleep=lambda s: None)
    j2.close_round(NOW.replace(hour=15, minute=8), lambda s: 95.0, state_path=path)     # four buys, each -500 bp
    # Every loss is identical: sd 0 gives no t, so the rule can't fire. Vary one.
    st = j2.load_state(path)
    st["days"][DAY]["decisions"][0]["net_bp"] = -400.0
    j2._apply_kill_rule(st)
    assert st["status"] == "switched_off" and "kill line" in st["status_reason"]


def test_summary_reports_briers_halves_and_the_jev1_band_cut(tmp_path, key, monkeypatch):
    path = str(tmp_path / "s.json")
    j2.decide_round(_scanner(4), NOW, lambda s: 100.0, post=_post([_resp(BULL)]), state_path=path, sleep=lambda s: None)
    j2.close_round(NOW.replace(hour=15, minute=8), lambda s: 101.0, state_path=path)
    jev1 = {"days": {DAY: {"status": "closed", "decisions": [
        {"symbol": "A", "action": "buy", "p_up": 0.55, "net_bp": 5.0},
        {"symbol": "B", "action": "short", "p_up": 0.2, "net_bp": -15.0},
        {"symbol": "C", "action": "skip", "p_up": 0.5, "net_bp": 0.0}]}}}
    s = j2.summary(state_path=path, jev1_state=jev1)
    assert s["traded"] == 4 and s["halves"][0] == pytest.approx(s["halves"][1])
    assert s["jev1_by_band"] is None and s["verdict_due"] is False          # item 5 is reported at the verdict only
    monkeypatch.setattr(j2, "cfg", lambda: {**j2.DEFAULTS, "verdict_after_decisions": 4})
    s = j2.summary(state_path=path, jev1_state=jev1)
    assert s["verdict_due"] is True
    assert s["briers"]["news_positive"] == pytest.approx(0.04) and s["briers"]["news_negative"] == pytest.approx(0.04)
    assert s["briers"]["p_combined"] == pytest.approx((1 - 0.73333) ** 2, abs=1e-3)
    assert s["jev1_by_band"] == {"band": 0.15, "inside": {"n": 1, "mean_bp": 5.0}, "outside": {"n": 1, "mean_bp": -15.0}}
    assert s["paired_vs_jev1_n"] == 0 and s["thresholds"]["buy_at"] == 0.65
