"""The Jev book (README section 86): decisions from a fake TypeSafe API, paper
fills, scoring against the scanner, retries, the kill rule, the key helper and
the 'Jev unavailable' path."""
import datetime
import io
import json
import os
import stat
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jev_book as jb  # noqa: E402
import typesafe_key  # noqa: E402

NOW = datetime.datetime(2026, 9, 28, 9, 46)


def _scanner(n=3, date="2026-09-28"):
    rows = [{"symbol": f"S{i}", "name": f"S{i} Ltd", "industry": "X", "ltp": 100.0, "side": "LONG" if i % 2 == 0 else "SHORT",
             "reasons": [{"text": "trend up"}], "brain": {"setup": "x", "news_headlines": ["h"]}} for i in range(n)]
    return {"session_date": date, "active": [r["symbol"] for r in rows], "rows": rows,
            "market": {"bias": "neutral", "nifty": {"chg_pct": 0.1}}}


def _resp(action="buy", p_up=0.62, size=2.2, status=200, headers=None):
    body = {"model": "jev-1.13.0", "usage": {"input_tokens": 900, "output_tokens": 40},
            "answers": {"action": {"type": "choice", "choice": action, "probabilities": {action: 0.7}, "confidence": 0.6},
                        "p_up": {"type": "noul", "noul": p_up},
                        "size": {"type": "score", "score": size, "confidence": 0.5}}}
    return types.SimpleNamespace(status_code=status, json=lambda: body, text=json.dumps(body), headers=headers or {})


def _post(responses):
    calls = []

    def post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers})
        return responses[min(len(calls) - 1, len(responses) - 1)]
    post.calls = calls
    return post


def test_one_official_request_per_stock_then_close_scores_jev_and_the_scanner(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    path = str(tmp_path / "s.json")
    post = _post([_resp()])
    jb.decide_round(_scanner(), NOW, lambda s: 100.0, post=post, state_path=path, sleep=lambda s: None)
    assert len(post.calls) == 3                                                   # one request per stock
    c = post.calls[0]
    assert c["url"] == "https://api.typesafe.ai/v1/systemone" and c["json"]["model"] == "jev-latest"
    assert set(c["json"]["questions"]) == {"action", "p_up", "size"}
    assert c["json"]["state"]["stock"]["symbol"] == "S0"
    assert c["headers"]["Authorization"] == "Bearer test-key"
    assert "test-key" not in json.dumps(c["json"])                               # the key never enters the state
    day = jb.load_state(path)["days"]["2026-09-28"]
    d = day["decisions"][0]
    assert d["action"] == "buy" and d["p_up"] == 0.62 and d["size_level"] == 2 and d["usage"]["input_tokens"] == 900
    jb.close_round(NOW.replace(hour=15, minute=8), lambda s: 101.0, state_path=path)
    rt = jb.round_trip_bp()
    for d in jb.load_state(path)["days"]["2026-09-28"]["decisions"]:
        assert abs(d["net_bp"] - (100.0 - rt)) < 1e-6
        want = (100.0 - rt) if d["scanner_side"] == "LONG" else (-100.0 - rt)
        assert abs(d["scanner_net_bp"] - want) < 1e-6
    s = jb.summary(state_path=path)
    assert s["traded"] == 3 and s["input_tokens"] == 2700 and s["key_stored"]


def test_retries_overload_then_succeeds(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    waits = []
    post = _post([_resp(status=529, headers={"retry-after": "3"}), _resp(status=429), _resp()])
    resp, err = jb.system_one({"x": 1}, jb.questions(), jb.cfg(), post=post, sleep=waits.append)
    assert err is None and resp["answers"]["action"]["choice"] == "buy"
    assert waits == [3.0, 2]                                                      # retry-after honoured, then backoff


def test_rejected_key_is_not_retried(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "bad")
    post = _post([_resp(status=401)])
    resp, err = jb.system_one({"x": 1}, jb.questions(), jb.cfg(), post=post, sleep=lambda s: None)
    assert resp is None and "rejected" in err and len(post.calls) == 1


def test_skip_costs_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    path = str(tmp_path / "s.json")
    jb.decide_round(_scanner(1), NOW, lambda s: 100.0, post=_post([_resp(action="skip", size=0.1)]),
                    state_path=path, sleep=lambda s: None)
    jb.close_round(NOW.replace(hour=15, minute=8), lambda s: 90.0, state_path=path)
    d = jb.load_state(path)["days"]["2026-09-28"]["decisions"][0]
    assert d["net_bp"] == 0.0 and d["size_level"] == 0 and jb.summary(state_path=path)["traded"] == 0


def test_no_key_records_unavailable_and_trades_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(jb, "KEY_PATH", str(tmp_path / "missing.json"))
    path = str(tmp_path / "s.json")
    post = _post([_resp()])
    jb.decide_round(_scanner(), NOW, lambda s: 100.0, post=post, state_path=path, sleep=lambda s: None)
    day = jb.load_state(path)["days"]["2026-09-28"]
    assert day["status"] == "jev_unavailable" and "no TypeSafe API key" in day["error"]
    assert day["decisions"] == [] and post.calls == []


def test_kill_rule_switches_the_book_off(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    path = str(tmp_path / "s.json")
    monkeypatch.setattr(jb, "cfg", lambda: {**jb.DEFAULTS, "kill_after": 4})
    for i, date in enumerate(("2026-09-28", "2026-09-29")):
        now = datetime.datetime.fromisoformat(date + "T09:46")
        jb.decide_round(_scanner(3, date), now, lambda s: 100.0, post=_post([_resp(size=3)]), state_path=path,
                        sleep=lambda s: None)
        jb.close_round(now.replace(hour=15, minute=8), lambda s: 97.0 - i * 0.5 - int(s[1:]) * 0.1, state_path=path)
    st = jb.load_state(path)
    assert st["status"] == "switched_off" and "kill" in st["status_reason"]


def test_maybe_decide_gates(monkeypatch, tmp_path):
    monkeypatch.setattr(jb, "STATE_PATH", str(tmp_path / "s.json"))
    started = []
    monkeypatch.setattr(jb.threading, "Thread", lambda target, name, daemon: types.SimpleNamespace(start=lambda: started.append(1)))
    sc = _scanner()
    assert not jb.maybe_decide(sc, NOW.replace(minute=30), None)
    assert not jb.maybe_decide(sc, NOW, "Holiday")
    assert not jb.maybe_decide({**sc, "session_date": "2026-09-25"}, NOW, None)
    assert jb.maybe_decide(sc, NOW, None) and started == [1]


def test_key_helper_stores_privately_and_never_prints_the_key(tmp_path, monkeypatch, capsys):
    path = str(tmp_path / "k.json")
    stream = io.StringIO("ts_live_abc123\n")
    stream.isatty = lambda: False
    assert typesafe_key.set_key(stream, path=path) == 0
    assert json.load(open(path))["key"] == "ts_live_abc123"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    out = capsys.readouterr().out
    assert "ts_live_abc123" not in out and "14-character" in out
    empty = io.StringIO("  \n")
    empty.isatty = lambda: False
    assert typesafe_key.set_key(empty, path=str(tmp_path / "none.json")) == 1


# --- live prices only (#151) ---------------------------------------------------------------

def test_no_live_prices_skips_the_day_without_asking_jev(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    path = str(tmp_path / "s.json")
    post = _post([_resp()])
    jb.decide_round(_scanner(), NOW, lambda s: 100.0, post=post, state_path=path, sleep=lambda s: None,
                    live=lambda: False)
    day = jb.load_state(path)["days"]["2026-09-28"]
    assert day["status"] == "no_live_prices" and "Kite" in day["error"]
    assert day["decisions"] == [] and post.calls == []
    # nothing to close, and the engine hook doesn't claim it closed anything
    monkeypatch.setattr(jb, "STATE_PATH", path)
    assert not jb.maybe_close(NOW.replace(hour=15, minute=8))
    s = jb.summary(path)
    assert s["sessions_closed"] == 0 and s["traded"] == 0


def test_live_ltp_never_falls_back_to_delayed_prices(monkeypatch):
    import data_provider as dp

    def no_yfinance(*a, **k):
        raise AssertionError("the delayed yfinance feed must not be used")
    monkeypatch.setattr(dp, "_get_intraday_candles_yfinance", no_yfinance)
    monkeypatch.setattr(dp, "kite_data_active", lambda: False)
    try:
        jb.live_ltp("RELIANCE")
        assert False, "expected no live price"
    except RuntimeError as exc:
        assert "not connected" in str(exc)

    noted = []
    monkeypatch.setattr(dp, "kite_data_active", lambda: True)
    monkeypatch.setattr(dp, "kite_session_live", lambda: True)
    monkeypatch.setattr(dp, "_note_kite_failure", lambda exc: noted.append(exc))
    monkeypatch.setattr(dp, "_get_kite", lambda: types.SimpleNamespace(
        ltp=lambda keys: {"NSE:RELIANCE": {"last_price": 1412.5}}))
    assert jb.live_ltp("RELIANCE") == 1412.5

    def broken(keys):
        raise ValueError("token expired")
    monkeypatch.setattr(dp, "_get_kite", lambda: types.SimpleNamespace(ltp=broken))
    try:
        jb.live_ltp("RELIANCE")
        assert False, "expected the Kite error to surface"
    except ValueError:
        pass
    assert len(noted) == 1


def test_a_fill_without_a_live_price_is_excluded(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    path = str(tmp_path / "s.json")
    jb.decide_round(_scanner(2), NOW, lambda s: 100.0, post=_post([_resp()]), state_path=path,
                    sleep=lambda s: None, live=lambda: True)

    def no_price(sym):
        raise RuntimeError("Kite is not connected, so there is no live price")
    jb.close_round(NOW.replace(hour=15, minute=8), no_price, state_path=path)
    decisions = jb.load_state(path)["days"]["2026-09-28"]["decisions"]
    assert all(d["excluded"] == "no live exit price" and d.get("net_bp") is None for d in decisions)
    s = jb.summary(path)
    assert s["traded"] == 0 and s["sessions_closed"] == 0

    path2 = str(tmp_path / "s2.json")
    jb.decide_round(_scanner(2), NOW, no_price, post=_post([_resp()]), state_path=path2,
                    sleep=lambda s: None, live=lambda: True)
    decisions = jb.load_state(path2)["days"]["2026-09-28"]["decisions"]
    assert all(d["entry"] is None and d["excluded"] == "no live entry price" for d in decisions)


def test_engine_hooks_fill_only_at_live_kite_prices(monkeypatch, tmp_path):
    import data_provider as dp
    path = str(tmp_path / "s.json")
    monkeypatch.setattr(jb, "STATE_PATH", path)
    monkeypatch.setattr(jb.threading, "Thread",
                        lambda target, name, daemon: types.SimpleNamespace(start=target))
    # test_maybe_decide_gates never runs its thread, so it leaves the flag set
    monkeypatch.setitem(jb._running, "decide", False)
    seen = {}
    monkeypatch.setattr(jb, "decide_round", lambda scanner, now, get_ltp, **k: seen.update(decide=(get_ltp, k)))
    assert jb.maybe_decide(_scanner(), NOW, None)
    get_ltp, kw = seen["decide"]
    assert get_ltp is jb.live_ltp and kw.get("live") is jb.kite_live           # the expiry-aware gate (#158)

    jb.save_state({**jb.load_state(path), "days": {"2026-09-28": {"status": "open", "decisions": []}}}, path)
    monkeypatch.setattr(jb, "close_round", lambda now, get_ltp, **k: seen.update(close=get_ltp))
    assert jb.maybe_close(NOW.replace(hour=15, minute=8))
    assert seen["close"] is jb.live_ltp


# --- an interrupted round, and the 06:00 expiry (#158) -----------------------------------------

def test_a_round_typesafe_interrupts_keeps_its_decisions_and_closes_them(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    path = str(tmp_path / "s.json")
    monkeypatch.setattr(jb, "STATE_PATH", path)
    monkeypatch.setitem(jb._running, "decide", False)
    post = _post([_resp(action="buy"), _resp(action="short"), _resp(status=401)])
    jb.decide_round(_scanner(4), NOW, lambda s: 100.0, post=post, state_path=path, sleep=lambda s: None,
                    live=lambda: True)
    day = jb.load_state(path)["days"]["2026-09-28"]
    assert len(post.calls) == 3                                   # the round stopped at the error
    assert day["status"] == "open" and "error" not in day         # not "Jev unavailable": it has positions
    assert [d["symbol"] for d in day["decisions"]] == ["S0", "S1"]
    intr = day["interrupted"]
    assert intr["reason"] == "jev_unavailable" and "rejected" in intr["error"]
    assert intr["asked"] == 2 and intr["not_asked"] == ["S2", "S3"] and intr["at"]
    # the engine's square-off closes it like any other round
    monkeypatch.setattr(jb, "live_ltp", lambda s: 101.0)
    assert jb.maybe_close(NOW.replace(hour=15, minute=8))
    closed = jb.load_state(path)["days"]["2026-09-28"]
    assert closed["status"] == "closed" and closed["interrupted"] == intr
    rt = jb.round_trip_bp()
    assert abs(closed["decisions"][0]["net_bp"] - (100.0 - rt)) < 1e-6
    assert abs(closed["decisions"][1]["net_bp"] - (-100.0 - rt)) < 1e-6
    s = jb.summary(path)
    assert s["traded"] == 2 and s["sessions_closed"] == 1 and s["decisions"] == 2
    assert s["last_day"]["interrupted"]["not_asked"] == ["S2", "S3"]


def test_an_error_on_the_first_stock_still_records_jev_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    path = str(tmp_path / "s.json")
    jb.decide_round(_scanner(), NOW, lambda s: 100.0, post=_post([_resp(status=401)]), state_path=path,
                    sleep=lambda s: None, live=lambda: True)
    day = jb.load_state(path)["days"]["2026-09-28"]
    assert day["status"] == "jev_unavailable" and "rejected" in day["error"] and day["decisions"] == []
    assert "interrupted" not in day
    monkeypatch.setattr(jb, "STATE_PATH", path)
    assert not jb.maybe_close(NOW.replace(hour=15, minute=8))


def test_a_kite_session_that_dies_mid_round_stops_asking_jev(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    path = str(tmp_path / "s.json")
    answers = iter([True, True, False, False])                    # the start, S0, then Kite is gone
    post = _post([_resp()])
    jb.decide_round(_scanner(3), NOW, lambda s: 100.0, post=post, state_path=path, sleep=lambda s: None,
                    live=lambda: next(answers))
    day = jb.load_state(path)["days"]["2026-09-28"]
    assert len(post.calls) == 1                                   # no Jev call for stocks it can't fill
    assert day["status"] == "open" and [d["symbol"] for d in day["decisions"]] == ["S0"]
    assert day["interrupted"]["reason"] == "no_live_prices" and day["interrupted"]["not_asked"] == ["S1", "S2"]
    jb.close_round(NOW.replace(hour=15, minute=8), lambda s: 101.0, state_path=path)
    assert jb.summary(path)["traded"] == 1


def _kite_config(monkeypatch, generated_at):
    import config
    import data_provider as dp
    monkeypatch.setattr(config, "USE_KITE_DATA", True)
    monkeypatch.setattr(config, "KITE_API_KEY", "test-api-key")
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "test-access-token")
    monkeypatch.setattr(config, "KITE_SESSION_GENERATED_AT", generated_at)
    monkeypatch.setattr(dp, "_kite_rejected_token", None)
    return dp


def test_the_live_price_gate_knows_the_0600_expiry(tmp_path, monkeypatch):
    now_ist = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    dp = _kite_config(monkeypatch, (now_ist - datetime.timedelta(days=2)).isoformat())
    assert dp.kite_data_active()                                  # the old gate: a stored, unrejected token
    assert not jb.kite_live()                                     # but it died at 06:00

    def no_kite():
        raise AssertionError("an expired session must not be asked for a price")
    monkeypatch.setattr(dp, "_get_kite", no_kite)
    try:
        jb.live_ltp("RELIANCE")
        assert False, "expected no live price"
    except RuntimeError as exc:
        assert "06:00" in str(exc)

    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    path = str(tmp_path / "s.json")
    post = _post([_resp()])
    jb.decide_round(_scanner(), NOW, jb.live_ltp, post=post, state_path=path, sleep=lambda s: None,
                    live=jb.kite_live)
    day = jb.load_state(path)["days"]["2026-09-28"]
    assert day["status"] == "no_live_prices" and "06:00" in day["error"] and post.calls == []

    _kite_config(monkeypatch, now_ist.isoformat())                # reconnected this morning
    assert jb.kite_live()
    dp.mark_kite_token_rejected()                                 # Kite said no: the gate closes again
    assert not jb.kite_live()


# --- the live mark of an open round: display only (README section 90) ------------------------

def _open_round(tmp_path, monkeypatch, responses=None, n=3):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setitem(jb._mark_cache, "key", None)
    path = str(tmp_path / "s.json")
    responses = responses or [_resp(action="buy"), _resp(action="short"), _resp(action="skip", size=0.1)]
    jb.decide_round(_scanner(n), NOW, lambda s: 100.0, post=_post(responses), state_path=path,
                    sleep=lambda s: None, live=lambda: True)
    return path


def _prices(**by_symbol):
    calls = []

    def quotes(keys):
        calls.append(list(keys))
        return {"NSE:" + s: {"last_price": p} for s, p in by_symbol.items()}
    quotes.calls = calls
    return quotes


def test_the_live_mark_prices_an_open_round_after_costs(tmp_path, monkeypatch):
    path = _open_round(tmp_path, monkeypatch)          # S0 buy (scanner LONG), S1 short (SHORT), S2 skip (LONG)
    rt = jb.round_trip_bp()
    live = jb.live_marks(path, quotes=_prices(S0=101.0, S1=99.0, S2=102.0), now=NOW.replace(hour=12))
    assert live["status"] == "open" and live["positions"] == 2 and live["skips"] == 1 and live["priced"] == 2
    assert live["closes_at"] == "15:08" and live["opened_at"] and live["marked_at"] and live["reason"] is None
    m = live["marks"]
    assert abs(m["S0"]["move_bp"] - 100.0) < 1e-6 and abs(m["S0"]["net_bp"] - (100.0 - rt)) < 1e-6
    assert abs(m["S1"]["net_bp"] - (100.0 - rt)) < 1e-6                     # a short gains when the price falls
    assert m["S2"]["net_bp"] == 0.0 and abs(m["S2"]["scanner_net_bp"] - (200.0 - rt)) < 1e-6   # a skip costs nothing
    assert abs(live["mean_net_bp"] - (100.0 - rt)) < 1e-6                   # over Jev's two positions only
    assert abs(live["scanner_mean_net_bp"] - (100.0 - rt)) < 1e-6


def test_the_live_mark_is_never_stored_and_never_scored(tmp_path, monkeypatch):
    path = _open_round(tmp_path, monkeypatch)
    with open(path, "rb") as fh:
        before = fh.read()
    scored = jb.summary(path)
    page = jb.page(path, quotes=_prices(S0=150.0, S1=50.0, S2=100.0), now=NOW.replace(hour=12))
    with open(path, "rb") as fh:
        assert fh.read() == before, "the mark must not touch the state file"
    assert page["live"]["priced"] == 2 and page["live"]["mean_net_bp"] > 4000
    for k in ("traded", "mean_net_bp", "t", "hit_rate", "sessions_closed", "scanner_mean_net_bp", "verdict_due"):
        assert page[k] == scored[k], k
    assert page["traded"] == 0 and page["mean_net_bp"] is None
    # the close scores the 15:08 price alone, whatever the mark said
    jb.close_round(NOW.replace(hour=15, minute=8), lambda s: 100.0, state_path=path)
    closed = jb.summary(path)
    assert closed["traded"] == 2 and abs(closed["mean_net_bp"] + jb.round_trip_bp()) < 1e-6


def test_no_live_mark_without_kite_and_never_from_the_delayed_feed(tmp_path, monkeypatch):
    import data_provider as dp
    path = _open_round(tmp_path, monkeypatch)

    def no_yfinance(*a, **k):
        raise AssertionError("the delayed yfinance feed must not be used")
    monkeypatch.setattr(dp, "_get_intraday_candles_yfinance", no_yfinance)
    monkeypatch.setattr(dp, "get_ltp", no_yfinance)
    monkeypatch.setattr(dp, "kite_data_active", lambda: False)
    live = jb.live_marks(path, now=NOW.replace(hour=12))
    assert live["positions"] == 2 and live["priced"] == 0 and live["marks"] == {} and live["mean_net_bp"] is None
    assert "Kite is not connected" in live["reason"]

    monkeypatch.setitem(jb._mark_cache, "key", None)
    noted = []
    monkeypatch.setattr(dp, "kite_data_active", lambda: True)
    monkeypatch.setattr(dp, "kite_session_live", lambda: True)
    monkeypatch.setattr(dp, "_note_kite_failure", lambda exc: noted.append(exc))

    def broken(keys):
        raise ValueError("token expired")
    monkeypatch.setattr(dp, "_get_kite", lambda: types.SimpleNamespace(ltp=broken))
    live = jb.live_marks(path, now=NOW.replace(hour=12))
    assert live["priced"] == 0 and "token expired" in live["reason"] and len(noted) == 1


def test_a_stock_kite_cannot_price_is_left_out_of_the_mark(tmp_path, monkeypatch):
    path = _open_round(tmp_path, monkeypatch)
    live = jb.live_marks(path, quotes=_prices(S1=99.0), now=NOW.replace(hour=12))
    assert set(live["marks"]) == {"S1"} and live["positions"] == 2 and live["priced"] == 1


def test_only_a_round_opened_today_and_still_open_is_marked(tmp_path, monkeypatch):
    path = _open_round(tmp_path, monkeypatch)
    q = _prices(S0=101.0, S1=99.0, S2=100.0)
    assert jb.live_marks(path, quotes=q, now=NOW.replace(day=29, hour=12)) is None      # yesterday's round
    jb.close_round(NOW.replace(hour=15, minute=8), lambda s: 100.0, state_path=path)
    monkeypatch.setitem(jb._mark_cache, "key", None)
    assert jb.live_marks(path, quotes=q, now=NOW.replace(hour=15, minute=9)) is None    # closed
    assert jb.page(path, quotes=q, now=NOW.replace(hour=15, minute=9))["live"] is None
    assert q.calls == []
    empty = str(tmp_path / "none.json")
    assert jb.live_marks(empty, quotes=q, now=NOW) is None and jb.page(empty, quotes=q, now=NOW)["live"] is None


def test_a_skipped_day_has_no_live_mark(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    path = str(tmp_path / "s.json")
    jb.decide_round(_scanner(), NOW, lambda s: 100.0, post=_post([_resp()]), state_path=path,
                    sleep=lambda s: None, live=lambda: False)
    assert jb.live_marks(path, quotes=_prices(S0=1.0), now=NOW.replace(hour=12)) is None


def test_one_kite_call_serves_page_refreshes_for_thirty_seconds(tmp_path, monkeypatch):
    path = _open_round(tmp_path, monkeypatch)
    q = _prices(S0=101.0, S1=99.0, S2=100.0)
    t = {"now": 1000.0}
    for _ in range(3):
        live = jb.live_marks(path, quotes=q, now=NOW.replace(hour=12), clock=lambda: t["now"])
        t["now"] += 10
    assert len(q.calls) == 1 and live["priced"] == 2
    t["now"] = 1000.0 + jb.MARK_TTL_S + 1
    jb.live_marks(path, quotes=q, now=NOW.replace(hour=12), clock=lambda: t["now"])
    assert len(q.calls) == 2
    assert q.calls[0] == ["NSE:S0", "NSE:S1", "NSE:S2"]                     # one batched call, every priced decision


def test_a_failing_mark_never_breaks_the_page(tmp_path, monkeypatch):
    path = _open_round(tmp_path, monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("unexpected")
    monkeypatch.setattr(jb, "live_marks", boom)
    page = jb.page(path)
    assert page["live"] is None and page["decisions"] == 3


# --- the interim read (prereg clarification 12): information only ------------------------------

def _closed_state(path, nets_by_session, p_up=0.6):
    """A state file of closed sessions. nets_by_session: list of lists of net bp,
    one list per session, every decision a buy with the scanner on the same side
    minus 1 bp, so the paired difference is +1 bp on every decision."""
    days = {}
    for i, nets in enumerate(nets_by_session):
        date = (datetime.date(2026, 10, 1) + datetime.timedelta(days=i)).isoformat()
        days[date] = {"status": "closed", "closed": True,
                      "decisions": [{"symbol": f"S{j}", "action": "buy", "p_up": p_up, "size_level": 2, "scanner_side": "LONG",
                                     "entry": 100.0, "exit": 101.0, "move_bp": x + 14.27, "net_bp": x, "scanner_net_bp": x - 1.0}
                                    for j, x in enumerate(nets)]}
    jb.save_state({"days": days, "status": "active", "status_reason": None}, path)
    return path


def test_no_interim_read_before_fifteen_closed_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(jb, "round_trip_bp", lambda: 14.27)
    path = _closed_state(str(tmp_path / "s.json"), [[10.0, 20.0]] * 14)
    assert jb.summary(path)["sessions_closed"] == 14
    assert jb.interim(path) is None
    assert jb.page(path, quotes=lambda keys: {}, now=NOW)["interim"] is None


def test_the_interim_read_appears_at_fifteen_sessions_and_marks_the_checkpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(jb, "round_trip_bp", lambda: 14.27)
    path = _closed_state(str(tmp_path / "s.json"), [[10.0, 20.0]] * 15)
    r = jb.interim(path)
    assert r["checkpoint"] == 15 and r["next_checkpoint"] == 30
    assert r["sessions"] == 15 and r["decisions"] == 30
    assert r["sessions_remaining"] == 45 and r["decisions_remaining"] == 270
    assert "Information only" in r["note"]
    s = jb.summary(path)
    for k in ("mean_net_bp", "t", "hit_rate", "paired_vs_scanner_bp", "paired_t", "brier"):
        assert r[k] == s[k]
    assert jb.page(path, quotes=lambda keys: {}, now=NOW)["interim"] == r
    path30 = _closed_state(str(tmp_path / "s30.json"), [[10.0, 20.0]] * 30)
    r30 = jb.interim(path30)
    assert r30["checkpoint"] == 30 and r30["next_checkpoint"] == 45 and r30["sessions_remaining"] == 30
    r45 = jb.interim(_closed_state(str(tmp_path / "s45.json"), [[10.0, 20.0]] * 45))
    assert r45["checkpoint"] == 45 and r45["next_checkpoint"] is None


def test_interim_projection_and_mde_arithmetic_when_sessions_arrive_first(tmp_path, monkeypatch):
    """15 sessions of 2 decisions: 2 a session x 60 sessions = 120 < 300, so the
    verdict comes at 60 sessions on 120 decisions. Everything is recomputed by
    hand here from the net list."""
    import math
    import statistics
    monkeypatch.setattr(jb, "round_trip_bp", lambda: 14.27)
    sessions = [[float(i), float(i)] for i in range(15)]           # session i holds two decisions of i bp
    nets = [x for s in sessions for x in s]
    r = jb.interim(_closed_state(str(tmp_path / "s.json"), sessions))
    n, mean, sd = 30, 7.0, statistics.stdev(nets)
    t = mean / sd * math.sqrt(n)
    assert r["mean_net_bp"] == mean and r["sd_bp"] == sd and abs(r["t"] - t) < 1e-12
    assert r["verdict_at"]["first"] == "sessions"
    assert r["verdict_at"]["expected_decisions"] == 120 and r["verdict_at"]["expected_sessions"] == 60
    assert r["expected_decisions_remaining"] == 90 and r["expected_sessions_remaining"] == 45
    assert abs(r["t_projected"] - t * math.sqrt(120 / 30)) < 1e-12       # = 2 t
    assert abs(r["mde_remaining_bp"] - 2 * sd / math.sqrt(90)) < 1e-12
    assert abs(r["mde_full_bp"] - 2 * sd / math.sqrt(120)) < 1e-12
    assert abs(r["required_mean_remaining_bp"] - (2 * sd * math.sqrt(120) - sum(nets)) / 90) < 1e-12
    # Session-clustered t: residual sum of session i is 2(i - 7); sum of squares 4 x 280 = 1120;
    # var(mean) = 15/14 x 1120 / 900 = 4/3; t = 7 / sqrt(4/3).
    assert abs(r["t_clustered"] - 7 / math.sqrt(4 / 3)) < 1e-12
    assert abs(r["t_clustered_projected"] - r["t_clustered"] * math.sqrt(60 / 15)) < 1e-12
    # Paired difference is +1 bp on every decision: no spread, so neither t exists.
    assert r["paired_vs_scanner_bp"] == 1.0 and r["paired_t"] is None and r["paired_t_clustered"] is None
    assert r["pass_rule"] == {"t": 2.24, "paired_t": 1.65, "both_halves_positive": True}


def test_interim_projection_when_decisions_arrive_first(tmp_path, monkeypatch):
    """15 sessions of 15 decisions: 15 a session x 60 = 900 >= 300, so the verdict
    comes at 300 decisions, after 20 sessions."""
    import math
    monkeypatch.setattr(jb, "round_trip_bp", lambda: 14.27)
    sessions = [[5.0 + (j % 3) + (i % 4) for j in range(15)] for i in range(15)]
    r = jb.interim(_closed_state(str(tmp_path / "s.json"), sessions))
    assert r["decisions"] == 225 and r["decisions_per_session"] == 15
    assert r["verdict_at"]["first"] == "decisions"
    assert r["verdict_at"]["expected_decisions"] == 300 and r["verdict_at"]["expected_sessions"] == 20
    assert r["expected_decisions_remaining"] == 75 and r["decisions_remaining"] == 75
    assert r["expected_sessions_remaining"] == 5 and r["sessions_remaining"] == 45
    assert abs(r["t_projected"] - r["t"] * math.sqrt(300 / 225)) < 1e-12
    assert abs(r["t_clustered_projected"] - r["t_clustered"] * math.sqrt(20 / 15)) < 1e-12
    assert abs(r["mde_remaining_bp"] - 2 * r["sd_bp"] / math.sqrt(75)) < 1e-12


def test_the_interim_read_writes_nothing_and_leaves_the_summary_and_verdict_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(jb, "round_trip_bp", lambda: 14.27)
    path = _closed_state(str(tmp_path / "s.json"), [[10.0, -20.0, 30.0]] * 15)
    before_bytes, before = open(path, "rb").read(), jb.summary(path)
    r = jb.interim(path)
    assert r is not None
    assert open(path, "rb").read() == before_bytes
    after = jb.summary(path)
    assert after == before
    assert "interim" not in after and not after["verdict_due"] and after["status"] == "active"
    assert "interim" not in json.load(open(path))
    # The kill rule and the verdict flag read the same functions they did before.
    state = jb.load_state(path)
    jb._apply_kill_rule(state)
    assert state["status"] == "active"


def test_a_failing_interim_read_never_breaks_the_page(tmp_path, monkeypatch):
    monkeypatch.setattr(jb, "round_trip_bp", lambda: 14.27)
    path = _closed_state(str(tmp_path / "s.json"), [[10.0]] * 15)
    monkeypatch.setattr(jb, "interim", lambda p=None: 1 / 0)
    out = jb.page(path, quotes=lambda keys: {}, now=NOW)
    assert out["interim"] is None and out["sessions_closed"] == 15
