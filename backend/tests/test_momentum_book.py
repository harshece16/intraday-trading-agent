"""The paper momentum book (README section 83): parity with the research code
that passed 3i, the month-turn rebalance, the switch-off band, and the
engine hook's timing."""
import csv
import datetime
import io
import os
import sys
import zipfile

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "research"))

import momentum_book as mb  # noqa: E402
import momentum_3i as m3  # noqa: E402  (research, for parity only)
import nse_prices as npx  # noqa: E402


# --- synthetic data ------------------------------------------------------------------

def _sessions(start="2024-01-01", n=470):
    d, out = datetime.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def _panel(n_stocks=20, n=470, drift_of=lambda k: 0.0004 * (k - 10)):
    sessions = _sessions(n=n)
    chains = {}
    for k in range(n_stocks):
        px, closes = 100.0, []
        for i in range(n):
            px *= 1 + drift_of(k) + 0.01 * (((i * 7 + k * 13) % 11) - 5) / 5
            closes.append(px)
        chains[f"S{k:02d}"] = {"idx": list(range(n)), "close": closes[:], "raw": closes[:],
                               "open": closes[:], "val": [1e8 + k * 1e6] * n, "isins": set()}
    return sessions, chains


# --- parity with research --------------------------------------------------------------

PURPOSES = [
    ("Face Value Split (Sub-Division) - From Rs 5/- Per Share To Rs 2/- Per Share", 5),
    ("Fv Splt Frm Rs 10 To Re 1", 1), ("Fv Spl-Rs10tore1/Div-1.50", 1), ("Bon 1:1/Fv Spl Rs.5tors.2", 2),
    ("Rights 87:38 @ Premium Of Rs 2.50 Per Share", 10), ("Special Dividend - Rs 500/- Per Share", 10),
    ("Final Dividend - Rs 2 Per Share / Special Dividend - Rs 1 Per Share", 1), ("Dividend-150%", 2),
    ("Scheme Of Arrangement", 1), ("Bonus 3:1", 10), ("Annual General Meeting", 10),
]


@pytest.mark.parametrize("purpose,fv", PURPOSES)
def test_parse_purpose_matches_research(purpose, fv):
    assert mb.parse_purpose(purpose, fv) == npx.parse_purpose(purpose, fv)


def test_parse_purpose_matches_research_on_nse_files_if_present():
    path = os.path.join(BACKEND, "data", "corp_actions", "ca_2016.csv")
    if not os.path.exists(path):
        pytest.skip("NSE corporate-actions cache not present")
    with open(path, encoding="utf-8-sig", errors="ignore") as fh:
        rows = [{k.strip().strip('"'): v for k, v in r.items() if k} for r in csv.DictReader(fh)]
    for r in rows:
        fv = float(r.get("FACE VALUE") or 0) if (r.get("FACE VALUE") or "").replace(".", "", 1).isdigit() else 0.0
        assert mb.parse_purpose(r["PURPOSE"], fv) == npx.parse_purpose(r["PURPOSE"], fv), r["PURPOSE"]


def test_ranking_matches_research():
    sessions, chains = _panel()
    mes = m3.month_ends(sessions)
    me_idx = {m: i for m, i in mes}
    months = [m for m, _ in mes]
    for month, idx in mes[-4:-1]:
        assert mb.ranked_universe(chains, idx) == m3.ranked_universe(chains, idx)
        names = mb.ranked_universe(chains, idx)
        assert mb.scores(chains, names, sessions, idx) == m3.scores(chains, names, me_idx, months, month, idx)


def _bhav_zip(path, day, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE", "TOTTRDQTY", "TOTTRDVAL",
                "TIMESTAMP", "TOTALTRADES", "ISIN"])
    for sym, op, close, prev in rows:
        w.writerow([sym, "EQ", op, close, close, close, close, prev, 100, close * 100,
                    day.strftime("%d-%b-%Y").upper(), 5, "INE000000001" if sym == "AAA" else ""])
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("b.csv", buf.getvalue())


def test_price_adjustment_matches_research(tmp_path, monkeypatch):
    bhav, ca = tmp_path / "bhav", tmp_path / "ca"
    bhav.mkdir()
    ca.mkdir()
    (bhav / "symbolchange.csv").write_text("SM_NAME,SM_KEY_SYMBOL,SM_NEW_SYMBOL,SM_APPLICABLE_FROM\n")
    days = [datetime.date(2025, 3, d) for d in (3, 4, 5, 6)]
    prices = {"AAA": [(100, 100, 99), (101, 101, 100), (50, 51, 101), (52, 52, 51)],       # 1:1 bonus on day 3
              "BBB": [(200, 200, 199), (198, 198, 200), (195, 190, 198), (191, 191, 190)]}  # Rs 5 dividend on day 3
    for i, day in enumerate(days):
        _bhav_zip(bhav / f"{day.strftime('%d%b%Y').upper()}.zip", day,
                  [(s, p[i][0], p[i][1], p[i][2]) for s, p in prices.items()])
    (ca / "ca_2025.csv").write_text(
        '"SYMBOL","COMPANY NAME","SERIES","PURPOSE","FACE VALUE","EX-DATE","RECORD DATE","BOOK CLOSURE START DATE","BOOK CLOSURE END DATE"\n'
        '"AAA","A Ltd","EQ","Bonus 1:1","10","05-Mar-2025","","",""\n'
        '"BBB","B Ltd","EQ","Dividend - Rs 5 Per Share","10","05-Mar-2025","","",""\n', encoding="utf-8")
    monkeypatch.setattr(npx, "CACHE", str(tmp_path / "p.pkl"))
    monkeypatch.setattr(npx, "HELD_OUT_DIR", str(tmp_path / "none"))
    r_sessions, r_chains, _, _ = npx.load(refresh=True, bhav_dir=str(bhav), ca_dir=str(ca))
    l_sessions, l_chains = mb.build_panel([str(bhav)], ca_dir=str(ca), symbolchange=str(bhav / "symbolchange.csv"))
    assert l_sessions == r_sessions
    for s in ("AAA", "BBB"):
        assert l_chains[s]["close"] == pytest.approx(r_chains[s]["close"])
    assert l_chains["AAA"]["close"][2] / l_chains["AAA"]["close"][1] == pytest.approx(51 / 50.5)   # bonus removed


# --- the book --------------------------------------------------------------------------

def _run(sessions, chains, conf, created_idx):
    state = mb.new_state(conf["capital"], sessions[created_idx])
    state["last_processed"] = sessions[created_idx]
    for d in sessions[created_idx + 1:]:
        mb.process_session(state, chains, sessions, d, conf)
    return state


def test_book_rebalances_on_the_first_session_of_each_month_and_marks_daily():
    sessions, chains = _panel()
    conf = {**mb.DEFAULTS, "universe": 20, "capital": 1_000_000.0}
    state = _run(sessions, chains, conf, created_idx=300)
    assert state["status"] == "active"
    assert len(state["book"]["positions"]) == 15
    first_fills = sorted({p["fill_date"] for p in state["book"]["positions"].values()})
    for d in first_fills:
        i = sessions.index(d)
        assert sessions[i - 1][:7] != d[:7]          # fills only on a month's first session
    assert state["nav"][-1]["date"] == sessions[-1]
    assert state["rebalances"] == len(state["month_points"]) >= 6
    buys = [t for t in state["trades"] if t["side"] == "BUY"]
    assert all(t["cost"] > 0 for t in buys)


def test_book_does_not_rebalance_on_months_before_it_existed():
    sessions, chains = _panel()
    conf = {**mb.DEFAULTS, "universe": 20}
    state = mb.new_state(conf["capital"], sessions[-3])
    state["last_processed"] = sessions[-3]
    for d in sessions[-2:]:
        mb.process_session(state, chains, sessions, d, conf)
    if sessions[-2][:7] == sessions[-3][:7] and sessions[-1][:7] == sessions[-2][:7]:
        assert state["rebalances"] == 0 and state["status"] == "waiting_for_month_end"


def test_book_switches_itself_off_below_the_band():
    sessions, chains = _panel()
    # an impossible expectation puts the floor above any plausible result
    conf = {**mb.DEFAULTS, "universe": 20, "expected_monthly_excess": 0.50}
    state = _run(sessions, chains, conf, created_idx=300)
    assert state["status"] == "switched_off"
    assert "floor" in state["status_reason"]
    frozen = state["nav"][-1]["date"]
    mb.process_session(state, chains, sessions, sessions[-1], conf)
    assert state["nav"][-1]["date"] == frozen


def test_band_threshold_is_the_preregistered_formula():
    assert mb.band_threshold(6, 0.0082, 0.0387) == pytest.approx(-0.1404, abs=5e-4)
    assert mb.band_threshold(12, 0.0082, 0.0387) == pytest.approx(-0.1697, abs=5e-4)


def test_summary_before_the_first_job(tmp_path):
    out = mb.summary(state_path=str(tmp_path / "missing.json"))
    assert out["status"] == "not_started"


def test_summary_reads_the_state(tmp_path):
    sessions, chains = _panel()
    conf = {**mb.DEFAULTS, "universe": 20}
    state = _run(sessions, chains, conf, created_idx=300)
    path = str(tmp_path / "s.json")
    mb.save_state(state, path)
    out = mb.summary(state_path=path)
    assert out["status"] == "active" and len(out["holdings"]) == 15 and out["nav"]


# --- engine hook -----------------------------------------------------------------------

class _FakeProc:
    def __init__(self, *a, **k):
        _FakeProc.calls += 1

    def poll(self):
        return 0


def _at(y, mo, d, h, mi):
    import trading_engine
    return datetime.datetime(y, mo, d, h, mi, tzinfo=trading_engine.IST)


def test_evening_job_starts_once_after_the_close_and_retries_later(monkeypatch, tmp_path):
    _FakeProc.calls = 0
    monkeypatch.setattr(mb.subprocess, "Popen", _FakeProc)
    monkeypatch.setattr(mb, "load_state", lambda path=None: None)
    monkeypatch.setattr(mb, "LOG_PATH", str(tmp_path / "log"))
    monkeypatch.setattr(mb, "_last_attempt", {"date": None, "ts": 0.0, "proc": None})
    assert not mb.maybe_start_evening_job(_at(2026, 9, 28, 15, 45), None)      # before 19:30
    assert not mb.maybe_start_evening_job(_at(2026, 9, 26, 20, 0), None)       # Saturday
    assert not mb.maybe_start_evening_job(_at(2026, 10, 2, 20, 0), "Gandhi Jayanti")
    assert mb.maybe_start_evening_job(_at(2026, 9, 28, 19, 31), None)
    assert not mb.maybe_start_evening_job(_at(2026, 9, 28, 19, 45), None)      # inside the retry gap
    assert _FakeProc.calls == 1


def test_evening_job_is_skipped_once_today_is_processed(monkeypatch, tmp_path):
    _FakeProc.calls = 0
    monkeypatch.setattr(mb.subprocess, "Popen", _FakeProc)
    monkeypatch.setattr(mb, "load_state", lambda path=None: {"latest_session": "2026-09-28", "last_processed": "2026-09-28"})
    monkeypatch.setattr(mb, "_last_attempt", {"date": None, "ts": 0.0, "proc": None})
    assert not mb.maybe_start_evening_job(_at(2026, 9, 28, 21, 0), None)
    assert _FakeProc.calls == 0
