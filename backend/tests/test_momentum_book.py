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
import momentum_width as mw  # noqa: E402  (research, for parity only)
import nse_prices as npx  # noqa: E402

EQ, BE = 0, 1


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
    ("Consolidation Of Equity Shares From Re 1 Per Share To Rs 10 Per Share", 10),
    ("Capital Reduction Rs 10 To Rs 3.30 / Consolidation Rs 3.30 To Rs.10", 10),
    ("Annual General Meeting / Div. Of Rs. 1.50/- Per Equity Share Of Rs. 10/- Each.", 10),
    ("Dividend-Rs.8.50 Per Share (Including Special Dividend Of Rs.2/- Per Share).", 1),
    ("Interim Dividend Rs 6/- Per Share 9purpose Revised)", 2),
    ("Interim Dividend - Rs 974 Per Share", 10),
]


@pytest.mark.parametrize("purpose,fv", PURPOSES)
def test_parse_purpose_matches_research(purpose, fv):
    """The book reads corporate actions as the research loader's repaired panel does."""
    assert mb.parse_purpose(purpose, fv) == npx.parse_purpose(purpose, fv, repaired=True)


def test_parse_purpose_reads_what_the_old_loader_got_wrong():
    assert mb.parse_purpose("Consolidation Of Equity Shares From Re 1 Per Share To Rs 10 Per Share", 10) == [
        ("consolidation", 10.0)]
    assert mb.parse_purpose("Interim Div. Of Rs.5/- Per Share Of Rs. 10/- Each.", 10) == [("dividend", 5.0)]
    assert mb.parse_purpose("Dividend-Rs.8.50 Per Share (Including Special Dividend Of Rs.2/- Per Share).", 1) == [
        ("dividend", 8.5)]


def test_parse_purpose_matches_research_on_nse_files_if_present():
    path = os.path.join(BACKEND, "data", "corp_actions", "ca_2016.csv")
    if not os.path.exists(path):
        pytest.skip("NSE corporate-actions cache not present")
    with open(path, encoding="utf-8-sig", errors="ignore") as fh:
        rows = [{k.strip().strip('"'): v for k, v in r.items() if k} for r in csv.DictReader(fh)]
    for r in rows:
        fv = float(r.get("FACE VALUE") or 0) if (r.get("FACE VALUE") or "").replace(".", "", 1).isdigit() else 0.0
        assert mb.parse_purpose(r["PURPOSE"], fv) == npx.parse_purpose(r["PURPOSE"], fv, repaired=True), r["PURPOSE"]


def test_ranking_matches_research():
    sessions, chains = _panel()
    mes = m3.month_ends(sessions)
    me_idx = {m: i for m, i in mes}
    months = [m for m, _ in mes]
    for month, idx in mes[-4:-1]:
        assert mb.ranked_universe(chains, idx) == m3.ranked_universe(chains, idx)
        names = mb.ranked_universe(chains, idx)
        assert mb.scores(chains, names, sessions, idx) == m3.scores(chains, names, me_idx, months, month, idx)


def _with_series(chains, t2t=None):
    """Give a synthetic panel the series column and the EQ view build_panel makes."""
    for name, c in chains.items():
        away = set((t2t or {}).get(name, ()))
        c["ser"] = [BE if i in away else EQ for i in c["idx"]]
        keep = [j for j, series in enumerate(c["ser"]) if series == EQ]
        c["eq"] = {k: [c[k][j] for j in keep] for k in ("idx", "raw", "val")}
    return chains


def test_the_universe_is_chosen_from_eq_rows_as_research_does():
    sessions, chains = _panel()
    idx = m3.month_ends(sessions)[-2][1]
    _with_series(chains, {"S15": [idx], "S16": range(idx - 100, idx - 20)})
    got = mb.ranked_universe(chains, idx)
    assert got == [n for _, n in mw.ranked(mw.eq_view(chains), idx)]
    assert "S15" not in got                    # in trade-for-trade on the ranking day
    assert "S16" in got and got.index("S16") > got.index("S17")   # its 80 days away count as no trade


def _bhav_zip(path, day, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE", "TOTTRDQTY", "TOTTRDVAL",
                "TIMESTAMP", "TOTALTRADES", "ISIN"])
    for row in rows:
        sym, op, close, prev = row[:4]
        series = row[4] if len(row) > 4 else "EQ"
        w.writerow([sym, series, op, close, close, close, close, prev, 100, close * 100,
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
    monkeypatch.setattr(npx, "HELD_OUT_DIR", str(tmp_path / "none"))
    r_sessions, r_chains, _, _ = npx.build(bhav_dir=str(bhav), ca_dir=str(ca), wide=True)
    l_sessions, l_chains = mb.build_panel([str(bhav)], ca_dir=str(ca), symbolchange=str(bhav / "symbolchange.csv"))
    assert l_sessions == r_sessions
    for s in ("AAA", "BBB"):
        assert l_chains[s]["close"] == pytest.approx(r_chains[s]["close"])
    assert l_chains["AAA"]["close"][2] / l_chains["AAA"]["close"][1] == pytest.approx(51 / 50.5)   # bonus removed


def test_the_panel_is_the_research_loaders_repaired_panel(tmp_path, monkeypatch):
    """Trade-for-trade rows, a consolidation, a dividend with a face value in
    its text, and a dividend of nearly the whole price (#175, #177, #178)."""
    bhav, ca = tmp_path / "bhav", tmp_path / "ca"
    bhav.mkdir()
    ca.mkdir()
    (bhav / "symbolchange.csv").write_text("SM_NAME,SM_KEY_SYMBOL,SM_NEW_SYMBOL,SM_APPLICABLE_FROM\n")
    days = [datetime.date(2025, 3, d) for d in (3, 4, 5, 6, 7)]
    prices = {"AAA": [(100, 100, 99, "EQ"), (102, 102, 100, "EQ"), (90, 90, 102, "BE"), (80, 80, 90, "BE"),
                      (85, 85, 80, "EQ")],                       # a dividend on day 4, while in trade-for-trade
              "BBB": [(20, 20, 20, "EQ"), (21, 21, 20, "EQ"), (205, 210, 21, "EQ"), (212, 212, 210, "EQ"),
                      (214, 214, 212, "EQ")],                    # ten shares became one on day 3
              "CCC": [(500, 500, 499, "EQ"), (510, 510, 500, "EQ"), (12, 12, 510, "EQ"), (13, 13, 12, "EQ"),
                      (13, 13, 13, "EQ")]}                       # a dividend of Rs 498 on Rs 510 on day 3
    for i, day in enumerate(days):
        rows = [(s, p[i][0], p[i][1], p[i][2], p[i][3]) for s, p in prices.items()]
        if i == 1:
            rows.insert(0, ("AAA", 555, 555, 100, "BE"))         # both series on one day: EQ wins
        _bhav_zip(bhav / f"{day.strftime('%d%b%Y').upper()}.zip", day, rows)
    (ca / "ca_2025.csv").write_text(
        '"SYMBOL","COMPANY NAME","SERIES","PURPOSE","FACE VALUE","EX-DATE","RECORD DATE","BOOK CLOSURE START DATE","BOOK CLOSURE END DATE"\n'
        '"AAA","A Ltd","EQ","Div. Of Rs. 9/- Per Equity Share Of Rs. 10/- Each.","10","06-Mar-2025","","",""\n'
        '"BBB","B Ltd","EQ","Consolidation Of Equity Shares From Re 1 Per Share To Rs 10 Per Share","10","05-Mar-2025","","",""\n'
        '"CCC","C Ltd","EQ","Interim Dividend - Rs 498 Per Share","10","05-Mar-2025","","",""\n', encoding="utf-8")
    monkeypatch.setattr(npx, "HELD_OUT_DIR", str(tmp_path / "none"))
    r_sessions, r_chains, _, _ = npx.build(bhav_dir=str(bhav), ca_dir=str(ca), wide=True)
    l_sessions, l_chains = mb.build_panel([str(bhav)], ca_dir=str(ca), symbolchange=str(bhav / "symbolchange.csv"))
    assert l_sessions == r_sessions and set(l_chains) == set(r_chains) == {"AAA", "BBB", "CCC"}
    for s in l_chains:
        for k in ("idx", "raw", "val", "ser"):
            assert l_chains[s][k] == r_chains[s][k], (s, k)
        assert l_chains[s]["close"] == pytest.approx(r_chains[s]["close"])
    assert l_chains["AAA"]["eq"] == mw.eq_view(r_chains)["AAA"]
    a = l_chains["AAA"]
    assert a["ser"] == [EQ, EQ, BE, BE, EQ] and a["raw"] == [100, 102, 90, 80, 85] and a["eq"]["idx"] == [0, 1, 4]
    assert a["close"][2] == pytest.approx(90 * (1 - 9 / 90))     # Rs 9, not Rs 19, off the trade-for-trade close
    assert l_chains["BBB"]["close"][:2] == pytest.approx([200.0, 210.0])
    assert l_chains["CCC"]["close"][1] == pytest.approx(510 * (1 - 498 / 510))


def test_a_holding_in_trade_for_trade_is_valued_and_sold_at_what_it_traded_for():
    sessions, chains = _panel()
    turn = next(i for i in range(330, len(sessions)) if sessions[i][:7] != sessions[i - 1][:7])
    conf = {**mb.DEFAULTS, "universe": 20, "capital": 1_000_000.0}
    state = mb.new_state(conf["capital"], sessions[turn - 30])
    state["last_processed"] = sessions[turn - 30]
    _with_series(chains)
    for d in sessions[turn - 29:turn + 1]:
        mb.process_session(state, chains, sessions, d, conf)
    held = sorted(state["book"]["positions"])[0]
    nxt = next(i for i in range(turn + 1, len(sessions)) if sessions[i][:7] != sessions[i - 1][:7])
    c = chains[held]
    for j in range(turn + 5, len(c["idx"])):                     # it halves and moves to trade-for-trade
        c["close"][j] *= 0.5
        c["raw"][j] *= 0.5
    _with_series(chains, {held: range(turn + 5, len(sessions))})
    for d in sessions[turn + 1:nxt + 1]:
        mb.process_session(state, chains, sessions, d, conf)
    assert held not in state["book"]["positions"]                # not eligible at the month-end, so sold
    sale = [t for t in state["trades"] if t["symbol"] == held and t["side"] == "SELL"][0]
    bought = [t for t in state["trades"] if t["symbol"] == held and t["side"] == "BUY"][0]
    worth = (bought["value"] - bought["cost"]) * c["close"][nxt] / c["close"][sessions.index(bought["date"])]
    assert sale["date"] == sessions[nxt] and sale["value"] == pytest.approx(worth, rel=1e-6)
    assert sale["value"] < 0.75 * bought["value"]                # the fall is in the sale, not hidden


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
