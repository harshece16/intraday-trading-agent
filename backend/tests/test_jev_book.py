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
