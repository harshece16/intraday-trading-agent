"""The scanner's tradability guards and the list fixed before the open
(README section 100): NSE's F&O ban list and price-band list, a stock with a
fixed band held to longs and left alone near the band, and the day's list
fixed from the pre-market read."""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import nse_feed  # noqa: E402
import scanner  # noqa: E402
import trading_engine  # noqa: E402
from state import AppState  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
CFG = {"active_count": 3, "selection": "liquidity", "freeze_min_coverage": 0.9, "near_band_pct": 2.0}
BAN = "Securities in Ban For Trade Date 29-SEP-2026:\n1,LICHSGFIN\n2,SAIL\n"
BANDS = ('Symbol,Series,Security Name,Band,Remarks\n'
         'RELIANCE,EQ,RELIANCE INDUSTRIES LIMITED,No Band,"-"\n'
         'ENRIN,EQ,SIEMENS ENERGY INDIA LIMITED,20,"-"\n'
         'TATACAP,EQ,TATA CAPITAL LIMITED,10,"-"\n'
         'ABAN,BE,ABAN OFFSHORE LIMITED,2,"-"\n'
         'ANKITMETAL,BZ,ANKIT METAL & POWER LIMITED,2,"GSM STAGE - 0"\n'
         'WATCHED,EQ,A WATCHED COMPANY,5,"GSM STAGE - I"\n'
         'TWICE,BE,LISTED TWICE LIMITED,5,"-"\n'
         'TWICE,EQ,LISTED TWICE LIMITED,20,"-"\n'
         'ODD,EQ,ODD BAND LIMITED,n/a,"-"\n')


def _guards():
    return {"ban": nse_feed.parse_fno_ban(BAN), "bands": nse_feed.parse_price_bands(BANDS)}


# --- the two NSE files --------------------------------------------------------------------

def test_the_ban_list_is_read_with_its_trade_date():
    assert nse_feed.parse_fno_ban(BAN) == {"trade_date": "2026-09-29", "symbols": {"LICHSGFIN", "SAIL"}}
    assert nse_feed.parse_fno_ban("Securities in Ban For Trade Date 30-SEP-2026:\n") == {
        "trade_date": "2026-09-30", "symbols": set()}


@pytest.mark.parametrize("text", ["", "<html>Access denied</html>", "Securities in Ban For Trade Date soon:\n1,SAIL"])
def test_a_ban_file_that_cannot_be_read_is_unknown_not_empty(text):
    assert nse_feed.parse_fno_ban(text) is None


def test_the_band_list_is_read_with_series_and_remarks():
    bands = nse_feed.parse_price_bands(BANDS)
    assert bands["RELIANCE"] == {"series": "EQ", "band": None, "remarks": ""}
    assert bands["ENRIN"]["band"] == 20.0 and bands["TATACAP"]["band"] == 10.0
    assert bands["ABAN"] == {"series": "BE", "band": 2.0, "remarks": ""}
    assert bands["ANKITMETAL"]["remarks"] == "GSM STAGE - 0"
    assert bands["TWICE"] == {"series": "EQ", "band": 20.0, "remarks": ""}     # the EQ row is kept
    assert "ODD" not in bands


@pytest.mark.parametrize("text", ["", "<html>Access denied</html>", "Name,Band\nA,5\n",
                                  "Symbol,Series,Security Name,Band,Remarks\n"])
def test_a_band_file_that_cannot_be_read_is_unknown(text):
    assert nse_feed.parse_price_bands(text) is None


def test_a_file_that_cannot_be_fetched_is_unknown_and_the_last_good_one_is_kept(monkeypatch):
    class Resp:
        def __init__(self, code, text):
            self.status_code, self.text = code, text
    calls = []

    def get(url, **kw):
        calls.append(url)
        return Resp(200, BAN) if len(calls) == 1 else Resp(503, "")
    monkeypatch.setattr(nse_feed.requests, "get", get)
    monkeypatch.setattr(nse_feed, "_ban_cache", {"at": 0.0, "value": None})
    assert nse_feed.fno_ban_list(ttl=0)["symbols"] == {"LICHSGFIN", "SAIL"}
    assert nse_feed.fno_ban_list(ttl=0) is None                                 # the second fetch failed
    assert nse_feed.fno_ban_list(ttl=3600)["symbols"] == {"LICHSGFIN", "SAIL"}   # within the cache's life


# --- the guards ---------------------------------------------------------------------------

def test_a_stock_in_the_ban_is_left_alone():
    why, long_only = scanner.guard_check("SAIL", _guards(), "2026-09-29", CFG)
    assert "F&O ban for 2026-09-29" in why and not long_only


def test_a_ban_list_for_an_earlier_day_is_not_used():
    assert scanner.guard_check("SAIL", _guards(), "2026-09-30", CFG) == (None, False)


def test_a_stock_with_no_band_is_free_on_both_sides():
    assert scanner.guard_check("RELIANCE", _guards(), "2026-09-29", CFG, ltp=1500, prev_close=1200) == (None, False)


def test_a_stock_with_a_fixed_band_is_long_only():
    assert scanner.guard_check("ENRIN", _guards(), "2026-09-29", CFG) == (None, True)
    assert scanner.guard_check("ENRIN", _guards(), "2026-09-29", CFG, ltp=3000, prev_close=2900) == (None, True)


@pytest.mark.parametrize("ltp,near", [(1078.0, "upper"), (1100.0, "upper"), (918.0, "lower"), (900.0, "lower")])
def test_a_banded_stock_near_its_band_is_left_alone(ltp, near):
    why, long_only = scanner.guard_check("TATACAP", _guards(), "2026-09-29", CFG, ltp=ltp, prev_close=1000.0)
    assert f"Within 2% of its {near} price band" in why and long_only       # bands at 1,100 and 900; near is from 1,078 up and from 918 down


@pytest.mark.parametrize("ltp", [1077.0, 1000.0, 919.0])
def test_a_banded_stock_away_from_its_band_can_be_bought(ltp):
    assert scanner.guard_check("TATACAP", _guards(), "2026-09-29", CFG, ltp=ltp, prev_close=1000.0) == (None, True)


def test_a_stock_in_trade_for_trade_or_under_surveillance_is_left_alone():
    assert "trade-for-trade (series BE)" in scanner.guard_check("ABAN", _guards(), "2026-09-29", CFG)[0]
    assert "GSM STAGE - I" in scanner.guard_check("WATCHED", _guards(), "2026-09-29", CFG)[0]


def test_unknown_files_exclude_nothing():
    unknown = {"ban": None, "bands": None}
    for sym in ("SAIL", "ENRIN", "ABAN"):
        assert scanner.guard_check(sym, unknown, "2026-09-29", CFG, ltp=100, prev_close=100) == (None, False)
    assert scanner.guards_summary(unknown, ["SAIL"]) == {"off": False, "ban": None, "bands": None}


def test_guards_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(nse_feed, "fno_ban_list", lambda: pytest.fail("not fetched when off"))
    assert scanner.load_guards({"guards": False}) == {"ban": None, "bands": None, "off": True}


def test_the_page_is_told_what_the_guards_touch():
    out = scanner.guards_summary(_guards(), ["RELIANCE", "SAIL", "ENRIN", "TATACAP", "ABAN", "WATCHED"])
    assert out["ban"] == {"trade_date": "2026-09-29", "count": 2, "in_universe": ["SAIL"]}
    assert out["bands"] == {"banded": ["ABAN", "ENRIN", "TATACAP", "WATCHED"], "not_eq": ["ABAN"],
                            "surveillance": ["WATCHED"]}


# --- the list fixed before the open -----------------------------------------------------------

def _row(sym, turnover):
    return {"symbol": sym, "turnover_cr": turnover, "score": 50.0, "final_score": 50.0, "side": "LONG",
            "daily_trend": "up", "excluded": None}


def test_a_list_fixed_before_the_open_is_the_days_list():
    sc = scanner.Scanner(CFG)
    assert sc.fix_day_list("2026-09-29", ["A", "B", "C"], now=1.0)
    assert sc.list_fixed_for("2026-09-29") and not sc.list_fixed_for("2026-09-30")
    rows = [_row("A", 1), _row("B", 2), _row("C", 3), _row("D", 9000)]        # D trades far more today
    active, fixed = sc.day_list_for("2026-09-29", rows, n_rows=100, n_universe=100, now=2.0)
    assert active == ["A", "B", "C"] and fixed
    assert sc.day_list["when"] == "before the open" and sc.day_list["fixed_ts"] == 1.0


def test_it_is_not_fixed_twice():
    sc = scanner.Scanner(CFG)
    sc.fix_day_list("2026-09-29", ["A", "B", "C"], now=1.0)
    assert not sc.fix_day_list("2026-09-29", ["X", "Y", "Z"], now=2.0)
    assert sc.day_list["symbols"] == ["A", "B", "C"]


def test_a_scan_that_still_reads_yesterdays_bars_does_not_move_todays_list():
    sc = scanner.Scanner(CFG)
    sc.fix_day_list("2026-09-29", ["A", "B", "C"], now=1.0)
    rows = [_row("A", 1), _row("B", 2), _row("C", 3), _row("D", 9000)]
    active, fixed = sc.day_list_for("2026-09-28", rows, n_rows=100, n_universe=100, now=2.0)
    assert active == ["A", "B", "C"] and fixed and sc.day_list["session"] == "2026-09-29"


def test_without_a_pre_open_read_the_first_scan_fixes_the_list():
    sc = scanner.Scanner(CFG)
    rows = [_row("A", 900), _row("B", 800), _row("C", 700), _row("D", 600)]
    active, fixed = sc.day_list_for("2026-09-29", rows, n_rows=100, n_universe=100)
    assert active == ["A", "B", "C"] and fixed and sc.day_list["when"] == "at the first scan of the session"


def _engine(monkeypatch):
    monkeypatch.setattr(config, "SCANNER", {**config.SCANNER, "selection": "liquidity", "fix_list_from": "08:45"})
    engine = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    engine.scanner = scanner.Scanner(config.SCANNER)
    return engine


def _at(hh, mm, day=29):
    return datetime(2026, 9, day, hh, mm, tzinfo=IST)          # 29 Sep 2026 is a Tuesday


@pytest.mark.parametrize("hh,mm,day,holiday,expected", [
    (8, 44, 29, None, False), (8, 45, 29, None, True), (9, 14, 29, None, True), (9, 15, 29, None, False),
    (12, 0, 29, None, False), (8, 50, 27, None, False),          # 27 Sep is a Sunday
    (8, 50, 29, "A holiday", False),
])
def test_the_list_is_fixed_in_the_window_before_the_open_on_a_trading_day(monkeypatch, hh, mm, day, holiday,
                                                                          expected):
    assert _engine(monkeypatch).should_fix_list(_at(hh, mm, day), holiday) is expected


def test_it_is_not_asked_for_again_once_fixed_nor_in_score_mode(monkeypatch):
    engine = _engine(monkeypatch)
    engine.scanner.fix_day_list("2026-09-29", ["A"])
    assert not engine.should_fix_list(_at(8, 50), None)
    monkeypatch.setattr(config, "SCANNER", {**config.SCANNER, "selection": "score"})
    engine.scanner = scanner.Scanner(config.SCANNER)
    assert not engine.should_fix_list(_at(8, 50), None)


def test_a_failed_read_is_tried_again_after_five_minutes(monkeypatch):
    engine = _engine(monkeypatch)
    engine._list_fix_attempt_ts = trading_engine.time.time() - 60
    assert not engine.should_fix_list(_at(8, 50), None)
    engine._list_fix_attempt_ts = trading_engine.time.time() - 301
    assert engine.should_fix_list(_at(8, 50), None)


def test_the_pre_open_read_fixes_the_list_and_the_engine_watches_it(monkeypatch):
    engine = _engine(monkeypatch)
    result = {"watchlist": ["RELIANCE", "HDFCBANK", "ICICIBANK"], "market": {"bias": "neutral"}}
    monkeypatch.setattr(trading_engine, "run_premarket", lambda cfg: result)
    engine._run_premarket_scan(fix_list_for="2026-09-29")
    assert engine.scanner.day_list["symbols"] == ["RELIANCE", "HDFCBANK", "ICICIBANK"]
    assert engine.scanner.day_list["when"] == "before the open"
    assert list(engine.state.watchlist) == ["RELIANCE", "HDFCBANK", "ICICIBANK"]
    # the ordinary daily read does not fix anything
    other = _engine(monkeypatch)
    monkeypatch.setattr(trading_engine, "run_premarket", lambda cfg: result)
    other._run_premarket_scan()
    assert other.scanner.day_list is None


# --- the last completed session, from NSE's own files -------------------------------------------

import datetime as _dt  # noqa: E402
import io  # noqa: E402
import zipfile  # noqa: E402

INDEX_FILE = ("Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,"
              "Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield\n"
              "Nifty 50,28-09-2026,23064.9,23080.25,22762.2,22780.25,-360.25,-1.56,261457054,20620.36,19.26,2.75,1.24\n"
              "Nifty IT,28-09-2026,28214.65,28261.3,27822,28086.5,-74.4,-.26,27219480,2832.26,17.92,4.93,2.86\n"
              "India VIX,28-09-2026,12.16,14.145,12.16,13.64,1.48,12.15,-,-,-,-,-\n"
              "Nifty Bank,25-09-2026,1,2,1,2,0,0,1,1,1,1,1\n")


def _bhavcopy(rows):
    head = "TradDt,TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("b.csv", head + "".join(",".join(str(x) for x in r) + "\n" for r in rows))
    return buf.getvalue()


def test_the_trading_day_before_skips_weekends_and_holidays():
    assert nse_feed.previous_trading_day(_dt.date(2026, 9, 29)) == _dt.date(2026, 9, 28)
    assert nse_feed.previous_trading_day(_dt.date(2026, 9, 28)) == _dt.date(2026, 9, 25)      # a Monday
    assert nse_feed.previous_trading_day(_dt.date(2026, 10, 5)) == _dt.date(2026, 10, 1)      # 2 Oct is a holiday


def test_the_equity_file_gives_the_days_bar_for_eq_stocks_only():
    raw = _bhavcopy([("2026-09-28", "RELIANCE", "EQ", 1218.0, 1219.7, 1197.0, 1197.6, 13602349),
                     ("2026-09-28", "M&M", "EQ", 3000, 3010, 2950, 2960, 100),
                     ("2026-09-28", "ABAN", "BE", 50, 51, 49, 50, 10),
                     ("2026-09-25", "OLDROW", "EQ", 1, 1, 1, 1, 1),
                     ("2026-09-28", "NOPRICE", "EQ", 0, 0, 0, 0, 0)])
    bars = nse_feed.parse_bhavcopy_bars(raw, "2026-09-28")
    assert set(bars) == {"RELIANCE", "M&M"}
    assert bars["RELIANCE"] == {"time": "2026-09-28T00:00:00+05:30", "open": 1218.0, "high": 1219.7, "low": 1197.0,
                                "close": 1197.6, "volume": 13602349}


def test_the_index_file_gives_the_indices_the_scanner_reads():
    bars = nse_feed.parse_index_bars(INDEX_FILE, "2026-09-28")
    assert set(bars) == {"^NSEI", "^CNXIT", "^INDIAVIX"}
    assert bars["^NSEI"]["close"] == 22780.25 and bars["^INDIAVIX"] == {
        "time": "2026-09-28T00:00:00+05:30", "open": 12.16, "high": 14.145, "low": 12.16, "close": 13.64, "volume": 0}
    assert nse_feed.parse_index_bars("<html>no</html>", "2026-09-28") == {}


def _bar(date, close):
    return {"time": f"{date}T00:00:00+05:30", "open": close, "high": close, "low": close, "close": close, "volume": 1}


def test_a_missing_last_session_is_added_and_nothing_else_is_touched(monkeypatch):
    last = {"date": "2026-09-28",
            "stocks": {"RELIANCE": _bar("2026-09-28", 1197.6), "M&M": _bar("2026-09-28", 2960.0)},
            "indices": {"^NSEI": _bar("2026-09-28", 22780.25), "NIFTY_FIN_SERVICE.NS": _bar("2026-09-28", 24671.65)}}
    monkeypatch.setattr(nse_feed, "last_session", lambda today: last)
    daily = {"RELIANCE.NS": [_bar("2026-09-24", 1219.2), _bar("2026-09-25", 1226.0)],
             "M&M.NS": [_bar("2026-09-25", 3000.0)],
             "TCS.NS": [_bar("2026-09-25", 2082.0)],                         # not in NSE's file: left as it is
             "INFY.NS": [_bar("2026-09-25", 1000.0), _bar("2026-09-28", 990.0)],   # already there
             "^NSEI": [_bar("2026-09-25", 23140.5)],
             "NIFTY_FIN_SERVICE.NS": [_bar("2026-09-25", 25000.0)],
             "EMPTY.NS": []}
    added, through = scanner.complete_daily(daily, "2026-09-29")
    assert (added, through) == (4, "2026-09-28")
    assert [b["close"] for b in daily["RELIANCE.NS"]] == [1219.2, 1226.0, 1197.6]
    assert daily["M&M.NS"][-1]["close"] == 2960.0 and daily["^NSEI"][-1]["close"] == 22780.25
    assert daily["NIFTY_FIN_SERVICE.NS"][-1]["close"] == 24671.65          # an index, though its ticker ends .NS
    assert len(daily["TCS.NS"]) == 1 and len(daily["INFY.NS"]) == 2 and daily["EMPTY.NS"] == []
    assert scanner.complete_daily(daily, "2026-09-29") == (0, "2026-09-28")   # a second pass adds nothing


def test_a_hole_at_the_last_session_is_filled_when_todays_bar_is_already_there(monkeypatch):
    """#196: in a session the delayed feed carries today's bar and can lack yesterday's."""
    last = {"date": "2026-09-28",
            "stocks": {"JINDALSTEL": _bar("2026-09-28", 1139.6), "RELIANCE": _bar("2026-09-28", 1197.6),
                       "NEWLIST": _bar("2026-09-28", 50.0)},
            "indices": {"^CNXAUTO": _bar("2026-09-28", 27000.0)}}
    monkeypatch.setattr(nse_feed, "last_session", lambda today: last)
    daily = {"JINDALSTEL.NS": [_bar("2026-09-24", 1157.8), _bar("2026-09-25", 1164.8), _bar("2026-09-29", 1145.9)],
             "RELIANCE.NS": [_bar("2026-09-25", 1226.0), _bar("2026-09-28", 1197.0), _bar("2026-09-29", 1189.3)],
             "^CNXAUTO": [_bar("2026-09-25", 27300.0), _bar("2026-09-29", 26900.0)],
             "NEWLIST.NS": [_bar("2026-09-29", 51.0)]}          # listed today: nothing before to join it to
    assert scanner.complete_daily(daily, "2026-09-29") == (2, "2026-09-28")
    assert [(b["time"][:10], b["close"]) for b in daily["JINDALSTEL.NS"]] == [
        ("2026-09-24", 1157.8), ("2026-09-25", 1164.8), ("2026-09-28", 1139.6), ("2026-09-29", 1145.9)]
    assert [b["time"][:10] for b in daily["^CNXAUTO"]] == ["2026-09-25", "2026-09-28", "2026-09-29"]
    assert [b["close"] for b in daily["RELIANCE.NS"]] == [1226.0, 1197.0, 1189.3]     # the feed's own bar is kept
    assert len(daily["NEWLIST.NS"]) == 1
    assert scanner.complete_daily(daily, "2026-09-29") == (0, "2026-09-28")


def test_the_previous_close_is_the_last_sessions_once_the_hole_is_filled(monkeypatch):
    """The fact the scanner reads: the profile before today ends at NSE's close."""
    last = {"date": "2026-09-28", "stocks": {"JINDALSTEL": _bar("2026-09-28", 1139.6)}, "indices": {}}
    monkeypatch.setattr(nse_feed, "last_session", lambda today: last)
    days = [(_dt.date(2026, 9, 25) - _dt.timedelta(days=i)).isoformat() for i in range(89, -1, -1)]
    bars = [_bar(d, 1100.0 + i) for i, d in enumerate(days)] + [_bar("2026-09-29", 1145.9)]
    daily = {"JINDALSTEL.NS": bars}
    dates, closes = [b["time"][:10] for b in bars], [b["close"] for b in bars]
    before = scanner.daily_profile(daily["JINDALSTEL.NS"], dates, closes, "2026-09-29")
    assert before["close"] == 1189.0                                                 # the close of 25 September
    scanner.complete_daily(daily, "2026-09-29")
    after = scanner.daily_profile(daily["JINDALSTEL.NS"], dates, closes, "2026-09-29")
    assert after["close"] == 1139.6


def test_files_that_cannot_be_read_leave_the_daily_data_as_it_is(monkeypatch):
    def boom(today):
        raise RuntimeError("NSE is down")
    monkeypatch.setattr(nse_feed, "last_session", boom)
    daily = {"RELIANCE.NS": [_bar("2026-09-25", 1226.0)]}
    assert scanner.complete_daily(daily, "2026-09-29") == (0, None)
    assert len(daily["RELIANCE.NS"]) == 1


def test_the_last_session_is_read_from_the_cache_folder_or_fetched_once(tmp_path, monkeypatch):
    monkeypatch.setattr(nse_feed, "_last_session_cache", {})
    (tmp_path / "bhav_live").mkdir()
    (tmp_path / "bhav_live" / "20260928.zip").write_bytes(
        _bhavcopy([("2026-09-28", "RELIANCE", "EQ", 1218.0, 1219.7, 1197.0, 1197.6, 13602349)] * 40))
    fetched = []

    class Resp:
        status_code, text, content = 200, INDEX_FILE * 3, (INDEX_FILE * 3).encode()

    def get(url, **kw):
        fetched.append(url)
        return Resp()
    monkeypatch.setattr(nse_feed.requests, "get", get)
    out = nse_feed.last_session(_dt.date(2026, 9, 29), data_dir=str(tmp_path))
    assert out["date"] == "2026-09-28" and set(out["stocks"]) == {"RELIANCE"} and "^NSEI" in out["indices"]
    assert len(fetched) == 1 and fetched[0].endswith("ind_close_all_28092026.csv")    # the bhavcopy was on disk
    assert (tmp_path / "nse_indices" / "ind_close_all_28092026.csv").exists()
    nse_feed.last_session(_dt.date(2026, 9, 29), data_dir=str(tmp_path))
    assert len(fetched) == 1                                                           # remembered
