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

import pytest

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


def _job(monkeypatch, tmp_path, sessions, chains, failed=(), ca_ok=True, aliases=None):
    def build_panel(report=None):
        if report is not None:
            report.update(aliases=dict(aliases or {}), unreadable=[])
        return sessions, chains
    monkeypatch.setattr(mb, "build_panel", build_panel)
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


# --- a held stock whose NSE symbol changes (#261) -------------------------------------------

def _bhav_rows(path, day, rows):
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE", "TOTTRDQTY", "TOTTRDVAL",
                "TIMESTAMP", "TOTALTRADES", "ISIN"])
    for sym, close, isin in rows:
        w.writerow([sym, "EQ", close, close, close, close, close, close, 100, close * 100,
                    day.strftime("%d-%b-%Y").upper(), 5, isin])
    with zipfile.ZipFile(str(path), "w") as z:
        z.writestr("b.csv", buf.getvalue())


def test_build_panel_reports_the_chain_a_renamed_symbol_went_into(tmp_path):
    bhav, ca = tmp_path / "bhav", tmp_path / "ca"
    bhav.mkdir()
    ca.mkdir()
    days = [D(2025, 3, d) for d in (3, 4, 5, 6, 7)]
    for i, day in enumerate(days):
        sym = "OLDSYM" if i < 3 else "NEWSYM"                  # NSE renames it on day 4; same ISIN
        _bhav_rows(bhav / ("%s.zip" % day.strftime("%d%b%Y").upper()), day, [(sym, 100 + i, "INE000X01011")])
    stale = bhav / "stale.csv"
    stale.write_text("SM_NAME,SM_KEY_SYMBOL,SM_NEW_SYMBOL,SM_APPLICABLE_FROM\n")
    fresh = bhav / "fresh.csv"
    fresh.write_text("SM_NAME,SM_KEY_SYMBOL,SM_NEW_SYMBOL,SM_APPLICABLE_FROM\nX Ltd,OLDSYM,NEWSYM,06-MAR-2025\n")
    before, after = {}, {}
    _, c_before = mb.build_panel([str(bhav)], ca_dir=str(ca), symbolchange=str(stale), report=before)
    _, c_after = mb.build_panel([str(bhav)], ca_dir=str(ca), symbolchange=str(fresh), report=after)
    # a missed rename does not split the history: the ISIN keeps it in one chain
    assert set(c_before) == {"OLDSYM"} and len(c_before["OLDSYM"]["idx"]) == 5
    assert before["aliases"] == {"OLDSYM": "OLDSYM", "NEWSYM": "OLDSYM"}
    # once the file learns it, the chain takes the new name, and the report says where the old one went
    assert set(c_after) == {"NEWSYM"} and len(c_after["NEWSYM"]["idx"]) == 5
    assert after["aliases"]["OLDSYM"] == "NEWSYM" and after["unreadable"] == []


def _renamed(chains, old, new):
    out = dict(chains)
    out[new] = out.pop(old)
    return out


def _turns(sessions, after):
    return [i for i in range(after, len(sessions)) if sessions[i][:7] != sessions[i - 1][:7]]


def test_a_holding_whose_symbol_changes_follows_its_chain_and_is_sold_at_its_price(monkeypatch, tmp_path):
    sessions, chains = _panel(n=390)
    t1, t2 = _turns(sessions, 300)[:2]
    # the control: nothing is renamed
    path = _job(monkeypatch, tmp_path, sessions[:t1 + 3], chains)
    _state_at(path, sessions, t1 - 1)
    assert mb.daily(D.fromisoformat(sessions[t1 + 2]), state_path=path) == 0
    opened = mb.load_state(path)
    held = sorted(opened["book"]["positions"])[0]
    bench_held = sorted(set(opened["bench"]["positions"]) - {held})[0]
    ctl_dir = tmp_path / "control"
    ctl_dir.mkdir()
    ctl = str(ctl_dir / "state.json")
    mb.save_state(opened, ctl)
    _job(monkeypatch, ctl_dir, sessions[:t2 + 2], chains)
    assert mb.daily(D.fromisoformat(sessions[t2 + 1]), state_path=ctl) == 0
    control = mb.load_state(ctl)
    # the same book, after NSE renamed one book holding and one benchmark holding and the weekly file learnt it
    renamed = _renamed(_renamed(chains, held, held + "NEW"), bench_held, bench_held + "NEW")
    _job(monkeypatch, tmp_path, sessions[:t2 + 2], renamed,
         aliases={held: held + "NEW", bench_held: bench_held + "NEW"})
    assert mb.daily(D.fromisoformat(sessions[t2 + 1]), state_path=path) == 0
    state = mb.load_state(path)
    # valued and traded at its price, as if nothing had been renamed: the same marks, month point and trades
    assert state["nav"] == control["nav"] and state["month_points"] == control["month_points"]
    strip = lambda trades: [dict(t, symbol=t["symbol"].replace("NEW", "")) for t in trades]  # noqa: E731
    assert strip(state["trades"]) == strip(control["trades"])
    assert state["fills"].get("ended") == control["fills"].get("ended")
    assert state["data"]["problem"] is None
    assert held not in state["book"]["positions"] and held not in state["bench"]["positions"]
    assert bench_held not in state["bench"]["positions"]
    assert {(c["side"], c["from"], c["to"]) for c in state["symbol_changes"]} >= {
        ("book", held, held + "NEW"), ("bench", held, held + "NEW"), ("bench", bench_held, bench_held + "NEW")}


def test_a_holding_with_no_chain_and_no_symbol_change_stops_the_job(monkeypatch, tmp_path):
    sessions, chains = _panel(n=390)
    t1 = _turns(sessions, 300)[0]
    path = _job(monkeypatch, tmp_path, sessions[:t1 + 3], chains)
    _state_at(path, sessions, t1 - 1)
    assert mb.daily(D.fromisoformat(sessions[t1 + 2]), state_path=path) == 0
    held = sorted(mb.load_state(path)["book"]["positions"])[0]
    before = _record(mb.load_state(path))
    gone = dict(chains)
    del gone[held]                                              # the panel lost it, and nothing says where it went
    _job(monkeypatch, tmp_path, sessions[:t1 + 6], gone)
    assert mb.daily(D.fromisoformat(sessions[t1 + 5]), state_path=path) == 4
    state = mb.load_state(path)
    assert _record(state) == before                             # never valued or sold at its cost
    assert held in state["data"]["problem"] and "at its cost" in state["data"]["problem"]


# --- a bhavcopy cut off part-way (#262) -----------------------------------------------------

def _zip_bytes(tmp_path, n=6000):
    zpath = tmp_path / "src.zip"
    with zipfile.ZipFile(str(zpath), "w") as z:
        z.writestr("b.csv", "x" * n)
    blob = zpath.read_bytes()
    zpath.unlink()
    return blob


def test_a_download_cut_off_part_way_never_looks_cached(tmp_path, monkeypatch):
    day = D(2026, 9, 30)
    out = tmp_path / "bhav"
    blob = _zip_bytes(tmp_path, 20000)
    asked = []

    def killed(url, part, extra=None):                          # curl dies part-way: no 200, half a file
        asked.append(part)
        with open(part, "wb") as fh:
            fh.write(blob[: len(blob) * 6 // 10])
        return "000"
    monkeypatch.setattr(mb, "_curl", killed)
    assert mb.download_bhavcopy(day, str(out)) == (None, "failed")
    assert asked[0].endswith(".zip.part") and os.listdir(str(out)) == []
    # a broken file already in place (left by the old code) is not "cached": it is fetched again
    final = out / "20260930.zip"
    final.write_bytes(blob[: len(blob) * 6 // 10])
    assert final.stat().st_size > 5000 and not zipfile.is_zipfile(str(final))
    monkeypatch.setattr(mb, "BHAV_DIRS", [str(out)])
    assert mb.cached_dates() == set()

    def ok(url, part, extra=None):
        with open(part, "wb") as fh:
            fh.write(blob)
        return "200"
    monkeypatch.setattr(mb, "_curl", ok)
    assert mb.download_bhavcopy(day, str(out)) == (str(final), "fetched")
    assert zipfile.is_zipfile(str(final)) and sorted(os.listdir(str(out))) == ["20260930.zip"]
    assert mb.cached_dates() == {day}


def _write_day(path, day, prices):
    import csv
    import io
    import random
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE", "TOTTRDQTY", "TOTTRDVAL",
                "TIMESTAMP", "TOTALTRADES", "ISIN"])
    for sym, (close, prev) in prices.items():
        w.writerow([sym, "EQ", close, close * 1.01, close * 0.99, close, close, prev, 1000, close * 1e6,
                    day.strftime("%d-%b-%Y").upper(), 50, ""])
    rnd = random.Random(day.toordinal())
    for k in range(600):                                        # SME rows the parser ignores: a realistic size
        w.writerow(["SME%d" % k, "SM", rnd.random(), 1, 1, 1, 1, 1, 1, 1, day.strftime("%d-%b-%Y").upper(), 1, ""])
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("cm.csv", buf.getvalue())


def _bhav_cache(bhav, last=D(2024, 3, 1)):
    d, days = D(2022, 11, 1), []
    while d <= last:
        if d.weekday() < 5:
            days.append(d)
        d += datetime.timedelta(days=1)
    px = {"S%02d" % k: 100.0 for k in range(40)}
    for i, day in enumerate(days):
        new = {}
        for k, s in enumerate(sorted(px)):
            drift = 0.0005 * (k - 20) + 0.01 * (((i * 7 + k * 13) % 11) - 5) / 5
            new[s] = (px[s] * (1 + drift), px[s])
        _write_day(bhav / ("%s.zip" % day.strftime("%d%b%Y").upper()), day, new)
        px = {s: v[0] for s, v in new.items()}


def test_a_half_written_bhavcopy_stops_the_job_and_is_fetched_again(tmp_path, monkeypatch):
    """The month's first session (1 March 2024) is cut to 60% of its bytes.
    The old job took it as cached, dropped the day and made the rebalance a
    session late, exit 0. Now the job stops until it is fetched again, then
    rebalances on the right session."""
    bhav, ca, data = tmp_path / "bhav", tmp_path / "ca", tmp_path / "data"
    for p in (bhav, ca, data / "bhav_daily"):
        p.mkdir(parents=True)
    _bhav_cache(bhav)
    real_build = mb.build_panel
    monkeypatch.setattr(mb, "DATA", str(data))
    monkeypatch.setattr(mb, "BHAV_DIRS", [str(bhav)])
    monkeypatch.setattr(mb, "LIVE_DIR", str(bhav))
    monkeypatch.setattr(mb, "CA_DIR", str(ca))
    monkeypatch.setattr(mb, "build_panel", lambda report=None: real_build(
        [str(bhav)], ca_dir=str(ca), **({} if report is None else {"report": report})))
    monkeypatch.setattr(mb, "cfg", lambda: {**mb.DEFAULTS, "universe": 40})
    monkeypatch.setattr(mb, "refresh_reference_files", lambda: None)
    monkeypatch.setattr(mb, "update_corporate_actions", lambda year: True)
    monkeypatch.setattr(mb, "update_bhavcopies", lambda today: (0, []))
    path = str(tmp_path / "state.json")
    state = mb.new_state(1_000_000.0, "2024-02-20")
    mb.save_state(state, path)
    f = bhav / "01MAR2024.zip"
    blob = f.read_bytes()
    f.write_bytes(blob[: len(blob) * 6 // 10])                  # the job was killed mid-download
    assert f.stat().st_size > 5000 and not zipfile.is_zipfile(str(f))
    # without fetching, the job can't repair it: it stops, processes nothing, and says why
    assert mb.daily(D(2024, 3, 1), state_path=path, fetch=False) == 4
    stopped = mb.load_state(path)
    assert stopped["month_points"] == [] and stopped["trades"] == []
    assert "01MAR2024.zip" in stopped["data"]["problem"] and stopped["data"]["unreadable_files"] == ["01MAR2024.zip"]
    # the next run deletes it and fetches it again
    fetched = []

    def download(d, out_dir=None):
        fetched.append(d)
        f.write_bytes(blob)
        return str(f), "fetched"
    monkeypatch.setattr(mb, "download_bhavcopy", download)
    assert mb.daily(D(2024, 3, 1), state_path=path) == 0
    done = mb.load_state(path)
    assert fetched == [D(2024, 3, 1)]
    assert [p["date"] for p in done["month_points"]] == ["2024-03-01"]
    assert {t["date"] for t in done["trades"]} == {"2024-03-01"}
    assert done["data"]["problem"] is None and done["data"]["unreadable_files"] == []


# --- #220: the symbol-change refresh is recorded, and a failing day is never dropped --------

def test_the_symbol_change_refresh_is_recorded_and_a_failure_is_logged(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(mb, "DATA", str(tmp_path))
    answers = ["503"]

    def curl(url, out, extra=None):
        with open(out, "w") as fh:
            fh.write("SM_NAME,SM_KEY_SYMBOL,SM_NEW_SYMBOL,SM_APPLICABLE_FROM\n" + "X,A,B,01-JAN-2025\n" * 60)
        return answers[0]
    monkeypatch.setattr(mb, "_curl", curl)
    assert mb.refresh_reference_files() is False
    assert not os.path.exists(mb.symbolchange_path()) and os.listdir(str(tmp_path / "bhav_daily")) == []
    answers[0] = "200"
    assert mb.refresh_reference_files() is True and os.path.exists(mb.symbolchange_path())
    assert mb.refresh_reference_files() is None                 # a week old at most: not due
    # in the evening job: a failure is a warning and is kept in state["data"] with the file's date
    sessions, chains = _panel()
    t = _turn(sessions)
    path = _job(monkeypatch, tmp_path, sessions[:t - 3], chains)
    _state_at(path, sessions, t - 6)
    monkeypatch.setattr(mb, "refresh_reference_files", lambda: False)
    with caplog.at_level(logging.WARNING, logger="trading_bot"):
        assert mb.daily(D.fromisoformat(sessions[t - 4]), state_path=path) == 0
    assert any("symbol-change file could not be refreshed" in r.getMessage() for r in caplog.records)
    data = mb.summary(state_path=path)["data"]
    assert data["symbol_changes_refreshed"] is False and data["symbol_changes_as_of"]
    # a run where it was not due keeps the last answer; a refresh that works says so
    monkeypatch.setattr(mb, "refresh_reference_files", lambda: None)
    mb.daily(D.fromisoformat(sessions[t - 4]), state_path=path)
    assert mb.summary(state_path=path)["data"]["symbol_changes_refreshed"] is False
    monkeypatch.setattr(mb, "refresh_reference_files", lambda: True)
    mb.daily(D.fromisoformat(sessions[t - 4]), state_path=path)
    assert mb.summary(state_path=path)["data"]["symbol_changes_refreshed"] is True


def test_a_day_that_keeps_failing_still_stops_the_book_after_it_leaves_the_window(monkeypatch, tmp_path):
    sessions, chains = _panel(n=390)
    t = _turn(sessions)
    path = _job(monkeypatch, tmp_path, sessions[:t + 30], chains)
    _state_at(path, sessions, t - 1)
    before = _record(mb.load_state(path))
    missing = D.fromisoformat(sessions[t])
    monkeypatch.setattr(mb, "update_bhavcopies", lambda today: (0, [missing]))
    assert mb.daily(D.fromisoformat(sessions[t + 1]), state_path=path) == 4
    assert mb.load_state(path)["data"]["failed_days_pending"] == [sessions[t]]
    # 40 days on, the day has left the window update_bhavcopies asks about; it is asked for here, and still fails
    later = D.fromisoformat(sessions[t + 29])
    assert (later - missing).days > mb.REFETCH_DAYS
    asked = []

    def download(d, out_dir=None):
        asked.append(d)
        return None, "failed"
    monkeypatch.setattr(mb, "update_bhavcopies", lambda today: (0, []))
    monkeypatch.setattr(mb, "download_bhavcopy", download)
    assert mb.daily(later, state_path=path) == 4
    state = mb.load_state(path)
    assert asked == [missing] and _record(state) == before
    assert sessions[t] in state["data"]["problem"] and state["data"]["failed_days_pending"] == [sessions[t]]
    # when it comes in, the list empties and the book catches up from the right session
    monkeypatch.setattr(mb, "download_bhavcopy", lambda d, out_dir=None: ("/x.zip", "fetched"))
    assert mb.daily(later, state_path=path) == 0
    state = mb.load_state(path)
    assert state["data"]["failed_days_pending"] == [] and state["last_processed"] == sessions[t + 29]
    assert {tr["date"] for tr in state["trades"] if tr["side"] == "BUY"} >= {sessions[t]}


def test_the_owner_can_clear_a_failed_day_that_was_not_a_session(tmp_path):
    path = str(tmp_path / "state.json")
    state = mb.new_state(1_000_000.0, "2026-09-26")
    state["data"] = {"failed_days_pending": ["2026-10-02", "2026-10-06"]}
    mb.save_state(state, path)
    assert mb.clear_failed_day("2026-10-02", state_path=path) is True
    assert mb.load_state(path)["data"]["failed_days_pending"] == ["2026-10-06"]
    assert mb.clear_failed_day("2026-10-02", state_path=path) is False


# --- #227: a switched-off book; two jobs at once ---------------------------------------------

class _Proc:
    started = 0

    def __init__(self, *a, **k):
        _Proc.started += 1

    def poll(self):
        return 0


def _evening(monkeypatch, tmp_path, state):
    import trading_engine
    _Proc.started = 0
    monkeypatch.setattr(mb, "load_state", lambda path=None: state)
    monkeypatch.setattr(mb.subprocess, "Popen", _Proc)
    monkeypatch.setattr(mb, "LOG_PATH", str(tmp_path / "log"))
    monkeypatch.setattr(mb, "_last_attempt", {"date": None, "ts": 0.0, "proc": None})
    clock = [1_000_000.0]
    monkeypatch.setattr(mb.time, "time", lambda: clock[0])
    for minute in range(19 * 60 + 30, 23 * 60 + 30, 5):
        clock[0] += 300
        mb.maybe_start_evening_job(datetime.datetime(2026, 10, 5, minute // 60, minute % 60,
                                                     tzinfo=trading_engine.IST), None)
    return _Proc.started


def test_a_switched_off_book_does_not_rerun_the_job_every_half_hour(monkeypatch, tmp_path):
    # process_session leaves last_processed at the switch-off day (MOM-10), so "today is done" never holds
    state = {"status": "switched_off", "last_processed": "2026-06-01", "latest_session": "2026-10-05"}
    assert _evening(monkeypatch, tmp_path, state) == 0
    # an active book that never gets today's file still retries every half hour, as before
    active = {"status": "active", "last_processed": "2026-10-01", "latest_session": "2026-10-01"}
    assert _evening(monkeypatch, tmp_path, active) == 8


def test_a_second_evening_job_does_not_run_beside_one_still_running(monkeypatch, tmp_path):
    path = str(tmp_path / "state.json")
    mb.save_state(mb.new_state(1_000_000.0, "2026-09-26"), path)
    before = open(path).read()
    held = mb._take_lock(path)                                  # the job started before an engine restart
    try:
        assert open(path + ".lock").read() == str(os.getpid())
        assert mb.job_running(path)
        monkeypatch.setattr(mb, "build_panel", lambda report=None: pytest.fail("a second job built the panel"))
        assert mb.daily(D(2026, 10, 5), state_path=path, fetch=False) == mb.BUSY
        assert open(path).read() == before
        # the restarted engine does not start one at all
        monkeypatch.setattr(mb, "STATE_PATH", path)
        active = {"status": "active", "last_processed": "2026-10-01", "latest_session": "2026-10-01"}
        assert _evening(monkeypatch, tmp_path, active) == 0
    finally:
        held.close()
    assert not mb.job_running(path)                              # released when the job ends
    assert _evening(monkeypatch, tmp_path, active) == 8
