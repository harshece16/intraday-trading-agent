"""The Jev book (README section 86): decisions from a fake Jev, paper fills,
scoring against the scanner, the kill rule, and the 'Jev unavailable' path."""
import datetime
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jev_book as jb  # noqa: E402


def _scanner(n=3, date="2026-09-28"):
    rows = [{"symbol": f"S{i}", "name": f"S{i} Ltd", "industry": "X", "ltp": 100.0, "side": "LONG" if i % 2 == 0 else "SHORT",
             "reasons": [{"text": "trend up"}], "brain": {"setup": "x", "news_headlines": ["h"]}} for i in range(n)]
    return {"session_date": date, "active": [r["symbol"] for r in rows], "rows": rows,
            "market": {"bias": "neutral", "nifty": {"chg_pct": 0.1}}}


def _runner(answers):
    """answers: kind -> value; records every command."""
    calls = []

    def run(cmd, input=None, capture_output=True, text=True, timeout=None):
        calls.append((cmd, input))
        kind = cmd[1]
        return types.SimpleNamespace(returncode=0, stdout=str(answers[kind]) + "\n", stderr="")
    run.calls = calls
    return run


NOW = datetime.datetime(2026, 9, 28, 9, 46)


def test_decide_then_close_scores_jev_and_the_scanner(tmp_path):
    path = str(tmp_path / "s.json")
    run = _runner({"choice": "buy", "noul": "0.62", "score": "2"})
    jb.decide_round(_scanner(), NOW, lambda s: 100.0, runner=run, state_path=path)
    st = jb.load_state(path)
    day = st["days"]["2026-09-28"]
    assert day["status"] == "open" and len(day["decisions"]) == 3
    d = day["decisions"][0]
    assert d["action"] == "buy" and d["p_up"] == 0.62 and d["size_level"] == 2 and d["entry"] == 100.0
    assert '"symbol": "S0"' in run.calls[0][1] and "--json-state" in run.calls[0][0]     # state sent as JSON
    assert all("key" not in c[1].lower() for c in run.calls)                              # no secrets in the state
    jb.close_round(NOW.replace(hour=15, minute=8), lambda s: 101.0, state_path=path)
    rt = jb.round_trip_bp()
    day = jb.load_state(path)["days"]["2026-09-28"]
    assert day["closed"]
    for d in day["decisions"]:
        assert abs(d["net_bp"] - (100.0 - rt)) < 1e-6                                   # long, +1% move
        want = (100.0 - rt) if d["scanner_side"] == "LONG" else (-100.0 - rt)
        assert abs(d["scanner_net_bp"] - want) < 1e-6
    s = jb.summary(state_path=path)
    assert s["traded"] == 3 and abs(s["mean_net_bp"] - (100 - rt)) < 1e-6 and s["brier"] is not None


def test_skip_costs_nothing(tmp_path):
    path = str(tmp_path / "s.json")
    jb.decide_round(_scanner(1), NOW, lambda s: 100.0, runner=_runner({"choice": "skip", "noul": "0.5", "score": "0"}),
                    state_path=path)
    jb.close_round(NOW.replace(hour=15, minute=8), lambda s: 90.0, state_path=path)
    d = jb.load_state(path)["days"]["2026-09-28"]["decisions"][0]
    assert d["net_bp"] == 0.0 and jb.summary(state_path=path)["traded"] == 0


def test_missing_key_records_unavailable_and_trades_nothing(tmp_path):
    path = str(tmp_path / "s.json")

    def run(cmd, **k):
        return types.SimpleNamespace(returncode=1, stdout="", stderr='{"ok": false, "error": "official API key is not stored"}')
    jb.decide_round(_scanner(), NOW, lambda s: 100.0, runner=run, state_path=path)
    day = jb.load_state(path)["days"]["2026-09-28"]
    assert day["status"] == "jev_unavailable" and "not stored" in day["error"] and day["decisions"] == []


def test_kill_rule_switches_the_book_off(tmp_path, monkeypatch):
    path = str(tmp_path / "s.json")
    monkeypatch.setattr(jb, "cfg", lambda: {**jb.DEFAULTS, "kill_after": 4})
    for i, date in enumerate(("2026-09-28", "2026-09-29")):
        now = datetime.datetime.fromisoformat(date + "T09:46")
        sc = _scanner(3, date)
        jb.decide_round(sc, now, lambda s: 100.0, runner=_runner({"choice": "buy", "noul": "0.9", "score": "3"}),
                        state_path=path)
        jb.close_round(now.replace(hour=15, minute=8), lambda s: 97.0 - i * 0.5 - int(s[1:]) * 0.1, state_path=path)
    st = jb.load_state(path)
    assert st["status"] == "switched_off" and "kill" in st["status_reason"]


def test_maybe_decide_gates(monkeypatch, tmp_path):
    monkeypatch.setattr(jb, "STATE_PATH", str(tmp_path / "s.json"))
    started = []
    monkeypatch.setattr(jb.threading, "Thread", lambda target, name, daemon: types.SimpleNamespace(start=lambda: started.append(1)))
    sc = _scanner()
    assert not jb.maybe_decide(sc, NOW.replace(minute=30), None)                   # before 09:45
    assert not jb.maybe_decide(sc, NOW, "Holiday")
    assert not jb.maybe_decide({**sc, "session_date": "2026-09-25"}, NOW, None)   # stale scan
    assert jb.maybe_decide(sc, NOW, None) and started == [1]
