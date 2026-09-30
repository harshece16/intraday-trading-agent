"""The momentum book's evening job never trades past data it doesn't have
(#159): a day whose bhavcopy failed is fetched again and the book waits for
it, an empty month-end ranking stops the job instead of skipping the month,
and a failed corporate-actions refresh is logged and shown."""
import datetime
import json
import logging
import math
import os
import sys
import zipfile

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

import momentum_book as mb  # noqa: E402

D = datetime.date


# --- fetching: a failed day is tried again ------------------------------------------------

class _FakeNse:
    """NSE's archive for a few days: each day answers "ok", "404" or "fail"."""

    def __init__(self, cached, answers):
        self.have, self.answers, self.asked = set(cached), dict(answers), []

    def download(self, d, out_dir=None):
        self.asked.append(d)
        answer = self.answers.get(d, "404")
        if answer == "ok":
            self.have.add(d)
            return "/x/%s.zip" % d.isoformat(), "fetched"
        return None, "no_file" if answer == "404" else "failed"


def _fake_nse(monkeypatch, cached, answers):
    nse = _FakeNse(cached, answers)
    monkeypatch.setattr(mb, "cached_dates", lambda: set(nse.have))
    monkeypatch.setattr(mb, "download_bhavcopy", nse.download)
    monkeypatch.setattr(mb.time, "sleep", lambda s: None)
    return nse


def test_a_day_that_failed_is_fetched_again_after_a_later_day_succeeded(monkeypatch):
    # Friday 25 Sep is cached. On Tuesday 29 Sep, Monday's download fails but Tuesday's succeeds.
    nse = _fake_nse(monkeypatch, {D(2026, 9, 25)}, {D(2026, 9, 28): "fail", D(2026, 9, 29): "ok"})
    got, failed = mb.update_bhavcopies(D(2026, 9, 29), lookback_days=10)
    assert got == 1 and failed == [D(2026, 9, 28)]
    assert D(2026, 9, 26) in nse.asked and D(2026, 9, 27) in nse.asked      # weekends: NSE answers 404
    # The next evening the newest cached day is Tuesday, and Monday is asked for again.
    nse.answers[D(2026, 9, 28)] = "ok"
    nse.answers[D(2026, 9, 30)] = "ok"
    nse.asked.clear()
    got, failed = mb.update_bhavcopies(D(2026, 9, 30), lookback_days=10)
    assert D(2026, 9, 28) in nse.asked and got == 2 and failed == []
    assert D(2026, 9, 25) not in nse.asked and D(2026, 9, 29) not in nse.asked   # cached days aren't fetched


def test_the_window_reaches_back_to_the_newest_cached_day_when_that_is_older(monkeypatch):
    nse = _fake_nse(monkeypatch, {D(2026, 8, 3)}, {})
    mb.update_bhavcopies(D(2026, 9, 30), lookback_days=5)
    assert nse.asked[0] == D(2026, 8, 4) and nse.asked[-1] == D(2026, 9, 30)


def test_a_404_is_no_session_and_anything_else_is_a_failed_download(tmp_path, monkeypatch):
    def curl(answer, body=None):
        def run(url, out, extra=None):
            if body is not None:
                with open(out, "wb") as fh:
                    fh.write(body)
            return answer
        return run
    day = D(2026, 9, 30)
    monkeypatch.setattr(mb, "_curl", curl("404", b"<html>not found</html>"))
    assert mb.download_bhavcopy(day, str(tmp_path)) == (None, "no_file")
    monkeypatch.setattr(mb, "_curl", curl("000"))
    assert mb.download_bhavcopy(day, str(tmp_path)) == (None, "failed")
    monkeypatch.setattr(mb, "_curl", curl("403", b"blocked"))
    assert mb.download_bhavcopy(day, str(tmp_path)) == (None, "failed")
    monkeypatch.setattr(mb, "_curl", curl("200", b"<html>an error page</html>"))
    assert mb.download_bhavcopy(day, str(tmp_path)) == (None, "failed")
    assert os.listdir(str(tmp_path)) == []                                      # nothing half-written is kept
    zpath = tmp_path / "z.zip"
    with zipfile.ZipFile(str(zpath), "w") as z:
        z.writestr("b.csv", "x" * 6000)
    monkeypatch.setattr(mb, "_curl", curl("200", zpath.read_bytes()))
    path, outcome = mb.download_bhavcopy(day, str(tmp_path))
    assert outcome == "fetched" and path.endswith("20260930.zip")
    assert mb.download_bhavcopy(day, str(tmp_path)) == (path, "cached")
    assert mb.fetch_bhavcopy(day, str(tmp_path)) == path


# --- the evening job ------------------------------------------------------------------------

def _sessions(start="2025-01-01", n=340):
    d, out = D.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def _panel(n_stocks=30, n=340):
    """A panel with every field build_panel makes, 14 month-ends deep."""
    sessions, chains = _sessions(n=n), {}
    for k in range(n_stocks):
        px, closes = 100.0, []
        for i in range(n):
            px *= 1 + 0.002 * math.sin(2 * math.pi * (i / 180.0 + k / n_stocks)) + 0.01 * (((i * 7 + k * 13) % 11) - 5) / 5
            closes.append(px)
        c = {"idx": list(range(n)), "close": closes[:], "raw": closes[:], "open": closes[:],
             "val": [1e8 + k * 1e6] * n, "isins": set(), "high": [x * 1.01 for x in closes],
             "low": [x * 0.99 for x in closes], "prev": [closes[0]] + closes[:-1], "ser": [mb.EQ] * n}
        c["eq"] = {f: c[f][:] for f in ("idx", "raw", "val")}
        chains["S%02d" % k] = c
    return sessions, chains


def _turn(sessions, after=320):
    return next(i for i in range(after, len(sessions)) if sessions[i][:7] != sessions[i - 1][:7])


def _job(monkeypatch, tmp_path, sessions, chains, failed=(), ca_ok=True):
    monkeypatch.setattr(mb, "build_panel", lambda: (sessions, chains))
    monkeypatch.setattr(mb, "refresh_reference_files", lambda: None)
    monkeypatch.setattr(mb, "update_corporate_actions", lambda year: ca_ok)
    monkeypatch.setattr(mb, "update_bhavcopies", lambda today: (0, sorted(failed)))
    monkeypatch.setattr(mb, "CA_DIR", str(tmp_path))
    return str(tmp_path / "state.json")


def _state_at(path, sessions, idx):
    state = mb.new_state(1_000_000.0, sessions[idx - 5])
    state["last_processed"] = sessions[idx]
    mb.save_state(state, path)
    return state


def _record(state):
    """The part of the state that is the book's record."""
    return json.dumps({k: state[k] for k in ("status", "last_processed", "book", "bench", "nav", "month_points",
                                             "trades", "rebalances", "fills")}, sort_keys=True)


def test_the_book_waits_at_a_day_whose_download_failed(monkeypatch, tmp_path):
    sessions, chains = _panel()
    t = _turn(sessions)
    path = _job(monkeypatch, tmp_path, sessions[:t + 3], chains)
    _state_at(path, sessions, t - 1)                                  # processed through the month-end
    before = _record(mb.load_state(path))
    missing = D.fromisoformat(sessions[t])                            # the month's first session failed to download
    monkeypatch.setattr(mb, "update_bhavcopies", lambda today: (0, [missing]))
    assert mb.daily(D.fromisoformat(sessions[t + 2]), state_path=path) == 4
    state = mb.load_state(path)
    assert _record(state) == before                                   # nothing processed past the hole
    assert sessions[t] in state["data"]["problem"] and state["data"]["failed_downloads"] == [sessions[t]]
    # the next run gets the file, and the book rebalances on the right session
    monkeypatch.setattr(mb, "update_bhavcopies", lambda today: (1, []))
    assert mb.daily(D.fromisoformat(sessions[t + 2]), state_path=path) == 0
    state = mb.load_state(path)
    assert state["last_processed"] == sessions[t + 2] and state["rebalances"] == 1
    assert {tr["date"] for tr in state["trades"] if tr["side"] == "BUY"} == {sessions[t]}
    assert state["data"]["problem"] is None and state["data"]["failed_downloads"] == []


def test_a_failed_day_the_book_already_passed_or_today_does_not_stop_it(monkeypatch, tmp_path):
    sessions, chains = _panel()
    t = _turn(sessions)
    path = _job(monkeypatch, tmp_path, sessions[:t + 2], chains)
    _state_at(path, sessions, t - 3)
    today = D.fromisoformat(sessions[t + 1])
    old = D.fromisoformat(sessions[t - 4])                            # before last_processed
    monkeypatch.setattr(mb, "update_bhavcopies", lambda d: (0, [old, today]))
    assert mb.daily(today, state_path=path) == 0
    assert mb.load_state(path)["last_processed"] == sessions[t + 1]


def test_an_empty_month_end_ranking_stops_the_job_and_leaves_the_book_as_it_was(monkeypatch, tmp_path):
    sessions, chains = _panel()
    t = _turn(sessions)
    me = t - 1
    for c in chains.values():                                         # the month-end file came in without EQ rows
        c["ser"][me] = 1
        keep = [j for j, s in enumerate(c["ser"]) if s == mb.EQ]
        c["eq"] = {f: [c[f][j] for j in keep] for f in ("idx", "raw", "val")}
    assert mb.ranked_universe(chains, me) == []
    path = _job(monkeypatch, tmp_path, sessions[:t + 2], chains)
    _state_at(path, sessions, me)
    before = _record(mb.load_state(path))
    assert mb.daily(D.fromisoformat(sessions[t + 1]), state_path=path) == 4
    state = mb.load_state(path)
    assert _record(state) == before                                   # no skipped month, no mark, no last_processed
    assert "ranking" in state["data"]["problem"] and sessions[me] in state["data"]["problem"]
    # the same session outside the job (research parity, a young panel) is still skipped as before
    loose = mb.load_state(path)
    mb.process_session(loose, chains, sessions, sessions[t], mb.cfg())
    assert loose["last_processed"] == sessions[me] and loose["rebalances"] == 0
    try:
        mb.process_session(mb.load_state(path), chains, sessions, sessions[t], mb.cfg(), strict=True)
        assert False, "expected IncompleteData"
    except mb.IncompleteData:
        pass


def test_a_failed_corporate_actions_refresh_is_logged_and_shown(monkeypatch, tmp_path, caplog):
    sessions, chains = _panel()
    t = _turn(sessions)
    path = _job(monkeypatch, tmp_path, sessions[:t - 3], chains, ca_ok=False)
    _state_at(path, sessions, t - 6)
    (tmp_path / ("ca_%s.csv" % sessions[t - 4][:4])).write_text("SYMBOL\n")
    with caplog.at_level(logging.WARNING, logger="trading_bot"):
        assert mb.daily(D.fromisoformat(sessions[t - 4]), state_path=path) == 0
    assert any("corporate-actions" in r.getMessage() and r.levelno == logging.WARNING for r in caplog.records)
    out = mb.summary(state_path=path)
    assert out["data"]["corporate_actions_refreshed"] is False and out["data"]["corporate_actions_as_of"]
    assert out["data"]["problem"] is None
    # a successful refresh says so, and a run without fetching leaves the last answer in place
    monkeypatch.setattr(mb, "update_corporate_actions", lambda year: True)
    mb.daily(D.fromisoformat(sessions[t - 4]), state_path=path)
    assert mb.summary(state_path=path)["data"]["corporate_actions_refreshed"] is True
    mb.daily(D.fromisoformat(sessions[t - 4]), state_path=path, fetch=False)
    assert mb.summary(state_path=path)["data"]["corporate_actions_refreshed"] is True
