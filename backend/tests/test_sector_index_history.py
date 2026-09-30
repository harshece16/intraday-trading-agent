"""The sector trend's daily history from NSE's own index closing files
(README section 107, #197). Since 16 Sep 2026 the delayed feed has served one
daily bar for six of the eight sector indices, and the trend needs 51. No
test here touches the network: every download is a stand-in."""
import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nse_feed  # noqa: E402
import scanner  # noqa: E402
import sectoral_indices  # noqa: E402

HEAD = ("Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,"
        "Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield\n")
NAMES = {t: nse_feed.INDEX_NAMES[t] for t in sectoral_indices.TICKERS + ["^NSEI"]}


def _file(day, closes, other_day=None):
    """One session's index closing file. `closes` is {ticker: close}."""
    stamp = day.strftime("%d-%m-%Y")
    rows = [f"{NAMES[t]},{stamp},{c},{c + 5},{c - 5},{c},0,0,1000,1,1,1,1\n" for t, c in closes.items()]
    rows.append(f"Nifty Some Other Index,{stamp},1,2,1,2,0,0,1,1,1,1,1\n" * 20)      # padding NSE's file has
    if other_day:
        rows.append(f"Nifty Auto,{other_day.strftime('%d-%m-%Y')},1,1,1,1,0,0,1,1,1,1,1\n")
    return HEAD + "".join(rows)


def _sessions(before, n):
    out, d = [], before
    for _ in range(n):
        d = nse_feed.previous_trading_day(d)
        out.append(d)
    return out[::-1]


def _bar(day, close):
    return {"time": f"{day}T00:00:00+05:30", "open": close, "high": close, "low": close, "close": close,
            "volume": 1}


# --- parsing and assembly -----------------------------------------------------------------------------

def test_the_files_give_one_bar_per_session_oldest_first_for_every_index():
    days = _sessions(dt.date(2026, 9, 30), 3)
    # The later two files also carry a stray row dated the first session; it is not read.
    files = [(d.isoformat(), _file(d, {t: 1000.0 + 10 * i for t in NAMES}, other_day=days[0] if i else None))
             for i, d in enumerate(days)]
    bars = nse_feed.index_history_from_files([files[2], files[0], files[1], files[0]])
    assert set(bars) == set(NAMES)
    for t in NAMES:
        assert [b["time"][:10] for b in bars[t]] == [d.isoformat() for d in days]
    assert [b["close"] for b in bars["^CNXAUTO"]] == [1000.0, 1010.0, 1020.0]
    assert bars["NIFTY_FIN_SERVICE.NS"][0] == {"time": f"{days[0].isoformat()}T00:00:00+05:30", "open": 1000.0,
                                               "high": 1005.0, "low": 995.0, "close": 1000.0, "volume": 1000}


def test_a_file_with_only_another_sessions_rows_gives_nothing():
    d = dt.date(2026, 9, 29)
    assert nse_feed.index_history_from_files([(d.isoformat(), _file(dt.date(2026, 9, 28), {"^CNXIT": 5.0}))]) == {}
    assert nse_feed.index_history_from_files([(d.isoformat(), "<html>Not found</html>"), ("2026-09-28", None)]) == {}


# --- downloading: once per file, capped, spaced -------------------------------------------------------

@pytest.fixture
def nse(tmp_path, monkeypatch):
    """A stand-in for NSE's archive: `absent` dates answer 404, `down` raise."""
    monkeypatch.setattr(nse_feed, "_index_history", {})
    monkeypatch.setattr(nse_feed, "_index_history_absent", set())
    slept = []
    monkeypatch.setattr(nse_feed.time, "sleep", lambda s: slept.append(s))
    site = {"asked": [], "absent": set(), "down": set(), "refused": set(), "slept": slept, "dir": str(tmp_path)}

    class Resp:
        def __init__(self, status, text):
            self.status_code, self.text, self.content = status, text, text.encode()

    def get(url, **kw):
        tag = url.rsplit("_", 1)[1][:8]
        day = dt.datetime.strptime(tag, "%d%m%Y").date().isoformat()
        site["asked"].append(day)
        if day in site["down"]:
            raise nse_feed.requests.ConnectionError("no route to host")
        if day in site["refused"]:
            return Resp(403, "<html>" + "x" * 3000 + "</html>")
        if day in site["absent"]:
            return Resp(404, "<html>" + "x" * 3000 + "</html>")
        d = dt.date.fromisoformat(day)
        return Resp(200, _file(d, {t: 100.0 + d.toordinal() % 97 for t in NAMES}))
    monkeypatch.setattr(nse_feed.requests, "get", get)
    return site


BEFORE = dt.date(2026, 9, 30)


def test_sixty_sessions_are_downloaded_newest_first_and_kept(nse):
    out = nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=1000.0)
    want = [d.isoformat() for d in _sessions(BEFORE, 60)]
    assert out["sessions"] == want and out["missing"] == []
    assert nse["asked"] == want[::-1]                                         # newest first
    assert "2026-09-14" not in want                                           # Ganesh Chaturthi is skipped
    for t in sectoral_indices.TICKERS:
        assert [b["time"][:10] for b in out["bars"][t]] == want
    assert len(nse["slept"]) == 59 and set(nse["slept"]) == {nse_feed.INDEX_HISTORY_SPACING_S}
    assert len(os.listdir(os.path.join(nse["dir"], "nse_indices"))) == 60
    # One pass a day: asked again the same day, nothing is downloaded.
    assert nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=90000.0) is out
    assert len(nse["asked"]) == 60
    # The next session costs one download; the rest is read from the folder.
    nxt = nse_feed.index_history(dt.date(2026, 10, 1), data_dir=nse["dir"], now=90000.0)
    assert nse["asked"][60:] == ["2026-09-30"] and nxt["sessions"][-1] == "2026-09-30"
    assert len(nxt["sessions"]) == 60 and nxt["sessions"][0] == want[1]


def test_downloads_stop_at_the_cap_and_the_rest_is_missing(nse, monkeypatch):
    monkeypatch.setattr(nse_feed, "INDEX_HISTORY_MAX_DOWNLOADS", 10)
    out = nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=1000.0)
    assert len(nse["asked"]) == 10 and len(out["sessions"]) == 10 and len(out["missing"]) == 50
    assert out["sessions"][-1] == "2026-09-29"                                # the newest ten
    # Tried again after an hour, but the day's cap is spent: nothing more is asked.
    nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=1000.0 + nse_feed.INDEX_HISTORY_RETRY_S)
    assert len(nse["asked"]) == 10


def test_a_session_nse_has_no_file_for_is_a_holiday_and_the_window_reaches_one_further(nse):
    nse["absent"].add("2026-09-10")
    out = nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=1000.0)
    assert "2026-09-10" not in out["sessions"] and out["missing"] == [] and len(out["sessions"]) == 60
    assert out["sessions"][0] == _sessions(BEFORE, 61)[0].isoformat()
    nse_feed.index_history(dt.date(2026, 10, 1), data_dir=nse["dir"], now=1000.0)
    assert nse["asked"].count("2026-09-10") == 1                              # not asked again


def test_a_download_with_no_answer_stops_the_pass_which_is_tried_again_after_an_hour(nse):
    nse["down"].add("2026-09-22")
    out = nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=1000.0)
    assert out["sessions"] == ["2026-09-23", "2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29"]
    assert len(out["missing"]) == 55 and "2026-09-22" in out["missing"]
    assert len(nse["asked"]) == 6                                             # nothing after the failure
    assert nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=2000.0) is out
    assert len(nse["asked"]) == 6                                             # not before the hour is up
    nse["down"].clear()
    again = nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=1000.0 + nse_feed.INDEX_HISTORY_RETRY_S)
    assert again["missing"] == [] and len(again["sessions"]) == 60
    assert nse["asked"][6] == "2026-09-22" and len(nse["asked"]) == 61       # the five on disk are not asked again


def test_a_refusal_is_not_taken_for_a_holiday(nse):
    nse["refused"].add("2026-09-24")
    out = nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=1000.0)
    assert "2026-09-24" in out["missing"] and "2026-09-24" not in nse_feed._index_history_absent
    assert len(nse["asked"]) == 4


def test_the_latest_session_without_a_file_is_missing_not_a_holiday(nse):
    nse["absent"].add("2026-09-29")
    out = nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=1000.0)
    assert out["missing"] == ["2026-09-29"] and "2026-09-29" not in nse_feed._index_history_absent
    assert len(out["sessions"]) == 59


def test_two_sessions_in_a_row_without_a_file_stop_the_pass(nse):
    """A moved or renamed file would otherwise cost a request for every session, every hour."""
    nse["absent"].update(d.isoformat() for d in _sessions(BEFORE, 70))
    out = nse_feed.index_history(BEFORE, data_dir=nse["dir"], now=1000.0)
    assert out["sessions"] == [] and len(out["missing"]) == 60
    assert nse["asked"] == ["2026-09-29", "2026-09-28"] and not nse_feed._index_history_absent


# --- the scanner ---------------------------------------------------------------------------------------

SESSION = "2026-09-30"


def _year(before, n, start=1000.0, step=2.0):
    return [_bar(d.isoformat(), start + step * i) for i, d in enumerate(_sessions(dt.date.fromisoformat(before), n))]


def _history(n=60, step=5.0):
    """What index_history gives: n rising sessions for every index."""
    bars = {t: _year(SESSION, n, start=500.0, step=step) for t in NAMES}
    return {"bars": bars, "sessions": [b["time"][:10] for b in bars["^NSEI"]], "missing": []}


def _daily():
    """The delayed feed as it has been since 16 Sep: a year for IT, one bar (today's) for Auto."""
    return {"^NSEI": _year(SESSION, 250), "^CNXIT": _year(SESSION, 250, step=-1.0),
            "^CNXAUTO": [_bar(SESSION, 26383.1)]}


def test_the_scanner_uses_nses_history_when_the_feed_is_short(monkeypatch):
    daily = _daily()
    asked = []
    monkeypatch.setattr(nse_feed, "index_history", lambda before: asked.append(before) or _history())
    done = scanner.complete_sector_history(daily, SESSION, ["Automobile and Auto Components",
                                                            "Information Technology", "Banks"])
    assert done == ["^CNXAUTO"] and asked == [dt.date(2026, 9, 30)]
    dates = [b["time"][:10] for b in daily["^CNXAUTO"]]
    assert len(dates) == 61 and dates == sorted(set(dates)) and dates[-1] == SESSION   # today's bar kept once
    assert len(daily["^CNXIT"]) == 250                                                  # a full series is not touched
    nifty = daily["^NSEI"]
    nd, nc = [b["time"][:10] for b in nifty], [b["close"] for b in nifty]
    auto = sectoral_indices.sector_trend(daily, "Automobile and Auto Components", nd, nc, SESSION)
    assert auto["ticker"] == "^CNXAUTO" and auto["trend"] == "up" and auto["rs10"] is not None
    assert sectoral_indices.sector_trend(daily, "Information Technology", nd, nc, SESSION)["trend"] == "down"


def test_nses_bar_wins_on_a_session_both_have_and_none_appears_twice():
    daily = {"^CNXAUTO": [_bar("2026-09-28", 1.0), _bar("2026-09-29", 2.0), _bar(SESSION, 3.0)]}
    done = sectoral_indices.complete_from_nse(daily, SESSION, _history(), tickers=["^CNXAUTO"])
    assert set(daily) == {"^CNXAUTO"}                                   # only the tickers asked for
    bars = daily["^CNXAUTO"]
    by_day = {b["time"][:10]: b["close"] for b in bars}
    assert done == ["^CNXAUTO"] and len(by_day) == len(bars) == 61
    assert by_day["2026-09-29"] == _history()["bars"]["^CNXAUTO"][-1]["close"] and by_day[SESSION] == 3.0


def test_nse_is_not_asked_when_no_needed_index_is_short(monkeypatch):
    def boom(before):
        raise AssertionError("NSE should not be asked")
    monkeypatch.setattr(nse_feed, "index_history", boom)
    daily = _daily()
    assert scanner.complete_sector_history(daily, SESSION, ["Information Technology", "Banks"]) == []
    assert scanner.complete_sector_history(daily, SESSION, []) == []


@pytest.mark.parametrize("history", ["raises", "empty", "too_short"])
def test_with_neither_source_the_trend_is_unavailable_and_named(monkeypatch, history):
    def fetch(before):
        if history == "raises":
            raise RuntimeError("NSE is down")
        return {"bars": {}, "sessions": [], "missing": []} if history == "empty" else _history(n=30)
    monkeypatch.setattr(nse_feed, "index_history", fetch)
    daily = _daily()
    industries = ["Automobile and Auto Components", "Information Technology", "Banks"]
    assert scanner.complete_sector_history(daily, SESSION, industries) == []
    nd, nc = [b["time"][:10] for b in daily["^NSEI"]], [b["close"] for b in daily["^NSEI"]]
    trends = {i: sectoral_indices.sector_trend(daily, i, nd, nc, SESSION) for i in industries}
    assert trends["Automobile and Auto Components"] is None
    # Banks has no real index mapped, so it is not checked at all and is not "unavailable".
    assert sectoral_indices.unavailable(trends) == ["Automobile and Auto Components"]


# --- a whole scan -------------------------------------------------------------------------------------

import config  # noqa: E402
import data_provider  # noqa: E402

UNIVERSE = [{"symbol": sym, "name": sym.title(), "industry": ind} for sym, ind in (
    ("AAA", "Information Technology"), ("BBB", "Information Technology"),
    ("CCC", "Automobile and Auto Components"), ("DDD", "Automobile and Auto Components"),
    ("EEE", "Realty"), ("FFF", "Banks"))]
CFG = {**config.SCANNER, "active_count": 3, "deep_analysis": 3, "use_news": False, "use_fundamentals": False,
       "guards": False, "selection": "liquidity", "min_price": 10, "min_turnover_cr": 0, "min_atr_pct": 0}


def _five_minute(day, price):
    start = dt.datetime.fromisoformat(f"{day}T09:15:00+05:30")
    return [{"time": (start + dt.timedelta(minutes=5 * k)).isoformat(), "open": price, "high": price + 1,
             "low": price - 1, "close": price, "volume": 1000} for k in range(75)]


def _scan(monkeypatch, history):
    """One delayed-feed scan of a six-stock universe on SESSION. The feed has a
    year for Nifty IT and one bar, today's, for Nifty Auto and Nifty Realty."""
    prices = {u["symbol"]: 100.0 + 50 * i for i, u in enumerate(UNIVERSE)}
    daily = {scanner.yf_ticker(sym): _year(SESSION, 260, start=p, step=0.05) for sym, p in prices.items()}
    daily.update({scanner.NIFTY: _year(SESSION, 260, start=22000.0), scanner.VIX: _year(SESSION, 260, 13.0, 0.0),
                  "^CNXIT": _year(SESSION, 247, start=28000.0), "^CNXAUTO": [_bar(SESSION, 26383.1)],
                  "^CNXREALTY": [_bar(SESSION, 838.4)]})
    days = [d.isoformat() for d in _sessions(dt.date.fromisoformat(SESSION), 3)] + [SESSION]
    intraday = {scanner.yf_ticker(sym): [b for d in days for b in _five_minute(d, p)] for sym, p in prices.items()}
    intraday[scanner.NIFTY] = [b for d in days for b in _five_minute(d, 22000.0)]

    def download(tickers, period, interval):
        return {t: list(v) for t, v in (daily if interval == "1d" else intraday).items() if t in tickers}
    monkeypatch.setattr(scanner, "download_batch", download)
    monkeypatch.setattr(scanner.universe, "load", lambda: UNIVERSE)
    monkeypatch.setattr(scanner, "complete_daily", lambda d, today: (0, None))
    monkeypatch.setattr(data_provider, "kite_quotes", lambda symbols, indices=(): {})
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: False)
    monkeypatch.setattr(nse_feed, "results_calendar", lambda: {})
    monkeypatch.setattr(nse_feed, "corporate_actions_on", lambda day: {})
    monkeypatch.setattr(scanner.database, "record_market_breadth", lambda *a, **k: None)
    monkeypatch.setattr(nse_feed, "index_history", lambda before: history)
    return scanner.Scanner(CFG).run()


def test_a_scan_takes_the_trend_from_nses_history_and_names_what_it_could_not_work_out(monkeypatch):
    # NSE's files give Auto 60 rising sessions but Realty only 30.
    history = {"bars": {"^CNXAUTO": _year(SESSION, 60, start=500.0, step=5.0),
                        "^CNXREALTY": _year(SESSION, 30, start=800.0)}, "sessions": [], "missing": []}
    res = _scan(monkeypatch, history)
    assert res["session_date"] == SESSION and res["scanned"] == 6 and res["feed"]["prices"] == "delayed"
    assert res["sector_history_from_nse"] == ["^CNXAUTO"]
    assert res["sector_trends_unavailable"] == ["Realty"]              # Banks has no index: not checked, not listed

    bare = _scan(monkeypatch, {"bars": {}, "sessions": [], "missing": []})
    assert bare["sector_history_from_nse"] == []
    assert bare["sector_trends_unavailable"] == ["Automobile and Auto Components", "Realty"]
    rows, bare_rows = ({r["symbol"]: r for r in x["rows"]} for x in (res, bare))
    for sym in ("CCC", "DDD"):                                          # Auto's daily uptrend now counts: +6 long
        assert rows[sym]["long_score"] - bare_rows[sym]["long_score"] == pytest.approx(6.0)
    for sym in ("AAA", "BBB", "EEE", "FFF"):
        assert rows[sym]["long_score"] == bare_rows[sym]["long_score"]
