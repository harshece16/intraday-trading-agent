"""The scanner on live prices (README section 101): one Kite quote request for
the whole universe, NSE's opening price for the gap, a volume yardstick built
from earlier sessions, and the delayed feed whenever live prices cannot be
had."""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import data_provider  # noqa: E402
import nse_feed  # noqa: E402
import scanner  # noqa: E402

SESSION = "2026-09-29"
PRIOR = ["2026-09-24", "2026-09-25", "2026-09-28"]


def _bars(day, n=75, price=100.0, volume=1000, step=0.0):
    start = datetime.fromisoformat(f"{day}T09:15:00+05:30")
    out = []
    for k in range(n):
        p = price + step * k
        out.append({"time": (start + timedelta(minutes=5 * k)).isoformat(), "open": p, "high": p + 1, "low": p - 1,
                    "close": p, "volume": volume})
    return out


def _quote(ltp=102.0, open_=101.0, prev=100.0, volume=30000, vwap=101.5, day=SESSION, hhmm="10:00:00",
           lower=90.0, upper=110.0):
    return {"ltp": ltp, "open": open_, "high": max(ltp, open_), "low": min(ltp, open_), "prev_close": prev,
            "volume": volume, "vwap": vwap, "last_trade": f"{day}T{hhmm}+05:30", "at": f"{day}T{hhmm}+05:30",
            "lower_limit": lower, "upper_limit": upper}


# --- the volume yardstick ---------------------------------------------------------------------

def test_minutes_into_the_session():
    assert scanner.minutes_into_session("2026-09-29T09:15:00+05:30") == 0
    assert scanner.minutes_into_session("2026-09-29T10:00:30+05:30") == 45.5
    assert scanner.minutes_into_session("2026-09-29T09:00:00+05:30") == 0          # before the open
    assert scanner.minutes_into_session("2026-09-29T17:35:05+05:30") == 375        # after the close


def test_the_curve_is_the_average_volume_by_each_slot_over_earlier_sessions():
    candles = _bars(PRIOR[0], volume=1000) + _bars(PRIOR[1], volume=3000) + _bars(SESSION, n=9, volume=99999)
    curve = scanner.volume_curve(candles, SESSION)
    assert len(curve) == 75
    assert curve[0] == 2000 and curve[8] == 9 * 2000 and curve[-1] == 75 * 2000   # today's bars are left out


def test_a_bar_missing_from_a_session_does_not_shift_the_later_ones():
    day = [b for k, b in enumerate(_bars(PRIOR[0], volume=1000)) if k != 1]      # no trade 09:20 to 09:25
    curve = scanner.volume_curve(day, SESSION)
    assert curve[:3] == [1000, 1000, 2000]


def test_expected_volume_runs_in_a_straight_line_between_slots():
    curve = [1000.0, 3000.0, 6000.0]
    assert scanner.expected_volume(curve, 0) == 0
    assert scanner.expected_volume(curve, 5) == 1000
    assert scanner.expected_volume(curve, 7.5) == 2000
    assert scanner.expected_volume(curve, 15) == 6000 and scanner.expected_volume(curve, 400) == 6000
    assert scanner.expected_volume([], 30) == 0


# --- one stock from one quote -------------------------------------------------------------------

def test_live_metrics_read_the_gap_from_nses_open_and_volume_against_the_curve():
    candles = _bars(PRIOR[0], volume=1000) + _bars(PRIOR[1], volume=1000)
    m = scanner.live_metrics(_quote(volume=18000), SESSION, 45.0, candles)
    assert m["feed"] == "live" and m["ltp"] == 102.0
    assert m["chg_pct"] == pytest.approx(2.0) and m["gap_pct"] == pytest.approx(1.0)
    assert m["rvol"] == pytest.approx(2.0)                # 18,000 against the 9,000 usual by 10:00
    assert m["vwap"] == 101.5 and m["bars_today"] == 9
    assert m["or_high"] is None and m["or_low"] is None   # no bars for today yet


def test_the_opening_range_comes_from_todays_first_three_bars_once_they_exist():
    today = _bars(SESSION, n=5, price=100.0, step=2.0)
    assert scanner.opening_range(today, SESSION) == (105.0, 99.0)
    assert scanner.opening_range(today[:2], SESSION) == (None, None)
    assert scanner.opening_range(_bars(PRIOR[0]), SESSION) == (None, None)
    m = scanner.live_metrics(_quote(), SESSION, 45.0, _bars(PRIOR[0]) + today)
    assert (m["or_high"], m["or_low"]) == (105.0, 99.0)


def test_no_yardstick_means_no_relative_volume_not_a_made_up_one():
    assert scanner.live_metrics(_quote(), SESSION, 45.0, [])["rvol"] is None


def test_an_unknown_opening_range_adds_nothing_to_the_score():
    m = scanner.live_metrics(_quote(), SESSION, 45.0, [])
    prof = {"trend": "up", "pct_from_high": 5.0, "pct_from_low": 30.0, "atr_pct": 2.0}
    ctx = {"nifty": {"chg_pct": 0.0}}
    _, items, _ = scanner.intraday_score(m, prof, ctx, None, 0, "IT", None, config.SCANNER, "long")
    assert not [t for _, t in items if "opening range" in t]


# --- which session the quotes describe -------------------------------------------------------------

def test_the_quotes_describe_a_session_when_half_the_universe_traded_that_day():
    symbols = ["A", "B", "C", "D"]
    quotes = {"A": _quote(), "B": _quote(), "C": _quote(day=PRIOR[-1]), "D": _quote(volume=0)}
    assert scanner.live_day(quotes, symbols) == SESSION
    quotes["B"] = _quote(open_=0.0)                        # not opened yet
    assert scanner.live_day(quotes, symbols) is None
    assert scanner.live_day({}, symbols) is None


def test_before_the_open_the_quotes_still_describe_the_last_session():
    symbols = ["A", "B"]
    quotes = {s: _quote(day=PRIOR[-1], hhmm="15:59:57") for s in symbols}
    assert scanner.live_day(quotes, symbols) == PRIOR[-1]


# --- the band guard on the exchange's own limits -------------------------------------------------

def test_the_band_guard_uses_the_exchanges_limits_when_they_are_known():
    guards = {"ban": None, "bands": {"TATACAP": {"series": "EQ", "band": 10.0, "remarks": ""}}}
    cfg = {"near_band_pct": 2.0}
    near = scanner.guard_check("TATACAP", guards, SESSION, cfg, ltp=354.0, prev_close=339.15, limits=(295.3, 360.9))
    assert "upper price band (₹360.90" in near[0] and near[1]
    away = scanner.guard_check("TATACAP", guards, SESSION, cfg, ltp=340.0, prev_close=339.15, limits=(295.3, 360.9))
    assert away == (None, True)
    # with no limits it is worked out from the previous close, as before
    assert "upper price band (₹373.0" in scanner.guard_check(
        "TATACAP", guards, SESSION, cfg, ltp=370.0, prev_close=339.15, limits=(0.0, 0.0))[0]


# --- Kite's quotes ------------------------------------------------------------------------------------

class _Kite:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def quote(self, keys):
        self.calls.append(list(keys))
        if self.fail:
            raise RuntimeError("Too many requests")
        out = {}
        for k in keys:
            if k == "NSE:NIFTY 50":
                out[k] = {"last_price": 22780.25, "ohlc": {"open": 23064.9, "high": 23080.25, "low": 22762.2,
                                                           "close": 23140.5},
                          "volume": None, "average_price": None, "last_trade_time": None,
                          "timestamp": datetime(2026, 9, 28, 17, 35, 5), "lower_circuit_limit": None,
                          "upper_circuit_limit": None}
            else:
                out[k] = {"last_price": 1197.6, "ohlc": {"open": 1218, "high": 1219.7, "low": 1197, "close": 1226},
                          "volume": 13602349, "average_price": 1205.86,
                          "last_trade_time": datetime(2026, 9, 28, 15, 59, 57),
                          "timestamp": datetime(2026, 9, 28, 17, 30, 34),
                          "lower_circuit_limit": 1077.9, "upper_circuit_limit": 1317.3}
        return out


def test_one_request_covers_the_universe_and_the_fields_are_named_plainly(monkeypatch):
    kite = _Kite()
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: True)
    monkeypatch.setattr(data_provider, "_get_kite", lambda: kite)
    out = data_provider.kite_quotes(["RELIANCE", "M&M"], indices=("NIFTY 50",))
    assert kite.calls == [["NSE:RELIANCE", "NSE:M&M", "NSE:NIFTY 50"]]
    assert out["RELIANCE"] == {
        "ltp": 1197.6, "open": 1218.0, "high": 1219.7, "low": 1197.0, "prev_close": 1226.0, "volume": 13602349,
        "vwap": 1205.86, "last_trade": "2026-09-28T15:59:57+05:30", "at": "2026-09-28T17:30:34+05:30",
        "lower_limit": 1077.9, "upper_limit": 1317.3}
    assert out["NIFTY 50"]["volume"] == 0 and out["NIFTY 50"]["last_trade"] is None
    assert out["NIFTY 50"]["at"] == "2026-09-28T17:35:05+05:30"


def test_a_large_universe_is_asked_for_in_chunks(monkeypatch):
    kite = _Kite()
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: True)
    monkeypatch.setattr(data_provider, "_get_kite", lambda: kite)
    out = data_provider.kite_quotes([f"S{i}" for i in range(450)], indices=("NIFTY 50",))
    assert [len(c) for c in kite.calls] == [400, 51] and len(out) == 451


def test_no_kite_or_a_failed_request_gives_nothing_so_the_delayed_feed_is_used(monkeypatch):
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: False)
    monkeypatch.setattr(data_provider, "_get_kite", lambda: pytest.fail("not asked when Kite is off"))
    assert data_provider.kite_quotes(["RELIANCE"]) == {}
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: True)
    monkeypatch.setattr(data_provider, "_get_kite", lambda: _Kite(fail=True))
    assert data_provider.kite_quotes(["RELIANCE"]) == {}
    assert scanner.fetch_live_quotes({"live_feed": False}, ["RELIANCE"]) == {}


def test_historical_requests_are_spaced_whoever_makes_them(monkeypatch):
    now, slept = [100.0], []

    def sleep(s):
        slept.append(round(s, 3))
        now[0] += s
    monkeypatch.setattr(data_provider, "_kite_historical_last", [0.0])
    for advance in (0.0, 0.1, 1.0):
        now[0] += advance
        data_provider._wait_for_kite_historical(clock=lambda: now[0], sleep=sleep)
    assert slept == [0.25]              # the first had nothing before it; the third came late enough


# --- a whole scan ---------------------------------------------------------------------------------------

UNIVERSE = [{"symbol": s, "name": s.title(), "industry": ind} for s, ind in (
    ("AAA", "IT"), ("BBB", "IT"), ("CCC", "Banks"), ("DDD", "Banks"), ("EEE", "Auto"), ("FFF", "Auto"))]
CFG = {**config.SCANNER, "active_count": 3, "deep_analysis": 3, "use_news": False, "use_fundamentals": False,
       "guards": False, "selection": "liquidity", "min_price": 10, "min_turnover_cr": 0, "min_atr_pct": 0}


def _daily(price, n=260):
    start = datetime.fromisoformat("2025-09-01T00:00:00+05:30")
    out, d, k = [], start, 0
    while len(out) < n:
        if d.weekday() < 5 and d.date().isoformat() < SESSION:
            p = price * (1 + 0.0005 * k)
            out.append({"time": d.isoformat(), "open": p, "high": p * 1.01, "low": p * 0.99, "close": p,
                        "volume": 1_000_000 + 10_000 * (hash(str(price)) % 7)})
            k += 1
        d += timedelta(days=1)
        if d.date().isoformat() >= SESSION:
            break
    return out


@pytest.fixture
def feeds(monkeypatch):
    """A universe of six on the delayed feed, which has no bar for today yet."""
    prices = {u["symbol"]: 100.0 + 50 * i for i, u in enumerate(UNIVERSE)}
    daily = {scanner.yf_ticker(s): _daily(p) for s, p in prices.items()}
    daily[scanner.NIFTY] = _daily(22000.0)
    daily[scanner.VIX] = _daily(13.0)
    intraday = {scanner.yf_ticker(s): [b for d in PRIOR for b in _bars(d, price=p, volume=2000)]
                for s, p in prices.items()}
    intraday[scanner.NIFTY] = [b for d in PRIOR for b in _bars(d, price=22000.0, volume=0)]

    def download(tickers, period, interval):
        return {t: list(v) for t, v in (daily if interval == "1d" else intraday).items() if t in tickers}
    monkeypatch.setattr(scanner, "download_batch", download)
    monkeypatch.setattr(scanner.universe, "load", lambda: UNIVERSE)
    monkeypatch.setattr(scanner, "complete_daily", lambda d, today: (0, None))
    monkeypatch.setattr(nse_feed, "results_calendar", lambda: {})
    monkeypatch.setattr(nse_feed, "corporate_actions_on", lambda day: {})
    monkeypatch.setattr(scanner.database, "record_market_breadth", lambda *a, **k: None)
    last = {s: daily[scanner.yf_ticker(s)][-1]["close"] for s in prices}
    return {"prices": prices, "last": last, "intraday": intraday}


def _live(feeds, monkeypatch, hhmm="09:40:00", skip=()):
    quotes = {s: _quote(ltp=c * 1.02, open_=c * 1.01, prev=c, volume=20000, vwap=c * 1.015, hhmm=hhmm)
              for s, c in feeds["last"].items() if s not in skip}
    quotes["NIFTY 50"] = {**_quote(ltp=22100.0, open_=22050.0, prev=22000.0, volume=0, vwap=0.0, hhmm=hhmm),
                          "last_trade": None}
    asked = []

    def candles(symbols, interval, period):
        asked.append(list(symbols))
        return {s: [b for d in PRIOR for b in _bars(d, price=feeds["prices"][s])]
                + _bars(SESSION, n=5, price=feeds["last"][s] * 1.01) for s in symbols}
    monkeypatch.setattr(data_provider, "kite_quotes", lambda symbols, indices=(): quotes)
    monkeypatch.setattr(data_provider, "get_candles_batch", candles)
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: True)
    return asked


def test_with_kite_connected_the_scan_describes_today_before_the_delayed_feed_has_a_bar(feeds, monkeypatch):
    asked = _live(feeds, monkeypatch)
    res = scanner.Scanner(CFG).run()
    assert res["session_date"] == SESSION and res["scanned"] == 6
    assert res["feed"]["prices"] == "live" and res["feed"]["rows_live"] == 6 and res["feed"]["why_delayed"] is None
    assert res["feed"]["quotes_at"] == f"{SESSION}T09:40:00+05:30"
    for r in res["rows"]:
        assert r["feed"] == "live" and r["chg_pct"] == pytest.approx(2.0, abs=0.01)
        assert r["gap_pct"] == pytest.approx(1.0, abs=0.01)
        assert r["rvol"] == pytest.approx(20000 / (5 * 2000), abs=0.01)       # 25 minutes in: five slots
    assert res["market"]["nifty"]["chg_pct"] == pytest.approx(0.45, abs=0.01) and res["market"]["nifty"]["above_open"]
    assert len(res["active"]) == 3 and len(asked) == 1 and sorted(asked[0]) == sorted(res["active"])


def test_the_days_list_gets_live_bars_and_with_them_its_opening_range(feeds, monkeypatch):
    _live(feeds, monkeypatch)
    sc = scanner.Scanner(CFG)
    res = sc.run()
    for sym in res["active"]:
        assert sc.intraday[sym][-1]["time"][:10] == SESSION                    # live bars, today's
    others = [r["symbol"] for r in res["rows"] if r["symbol"] not in res["active"]]
    assert all(sc.intraday[s][-1]["time"][:10] == PRIOR[-1] for s in others)   # the rest keep the delayed bars
    # the opening range is worth points, and only the stocks with live bars have one yet
    monkeypatch.setattr(data_provider, "get_candles_batch", lambda symbols, interval, period: {})
    bare = {r["symbol"]: r for r in scanner.Scanner(CFG).run()["rows"]}
    for r in res["rows"]:
        if r["symbol"] in res["active"]:
            assert r["long_score"] - bare[r["symbol"]]["long_score"] == pytest.approx(8.0)
        else:
            assert r["long_score"] == bare[r["symbol"]]["long_score"]


def test_after_a_restart_the_scan_keeps_the_list_and_the_time_it_was_fixed(feeds, monkeypatch):
    """#198: the list was held in memory only, and the first scan after a
    restart chose it again. The engine's watchlist, the order-book sampler
    and Jev's round all take the scan's `active`."""
    _live(feeds, monkeypatch)
    scanner.Scanner(CFG).fix_day_list(SESSION, ["AAA", "BBB", "CCC"], now=1000.0)   # before the restart
    res = scanner.Scanner(CFG).run()                                                 # the first scan after it
    assert res["active"] == ["AAA", "BBB", "CCC"]
    assert res["selection"]["fixed"] and res["selection"]["fixed_at"] == 1000.0
    assert res["selection"]["fixed_when"] == "before the open"
    # choosing again would have taken the most-traded three
    assert scanner.select_liquid([r for r in res["rows"] if not r["excluded"]], CFG) == ["FFF", "EEE", "DDD"]


def test_without_kite_the_scan_is_the_delayed_one_and_says_why(feeds, monkeypatch):
    monkeypatch.setattr(data_provider, "kite_quotes", lambda symbols, indices=(): {})
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: False)
    res = scanner.Scanner(CFG).run()
    assert res["session_date"] == PRIOR[-1] and res["feed"]["prices"] == "delayed"
    assert res["feed"]["why_delayed"] == "Kite is not connected." and res["feed"]["rows_delayed"] == 6
    assert all(r["feed"] == "delayed" for r in res["rows"])


def test_quotes_from_before_the_open_do_not_start_a_new_session(feeds, monkeypatch):
    quotes = {s: _quote(ltp=c, open_=c, prev=c, day=PRIOR[-1], hhmm="15:59:57") for s, c in feeds["last"].items()}
    quotes["NIFTY 50"] = _quote(ltp=22000.0, open_=22000.0, prev=21900.0, day=PRIOR[-1], hhmm="17:35:05")
    monkeypatch.setattr(data_provider, "kite_quotes", lambda symbols, indices=(): quotes)
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: True)
    monkeypatch.setattr(data_provider, "get_candles_batch", lambda symbols, interval, period: {})
    res = scanner.Scanner(CFG).run()
    assert res["session_date"] == PRIOR[-1] and res["feed"]["prices"] == "live"


def test_a_stock_that_has_not_traded_today_is_left_out_of_a_live_scan(feeds, monkeypatch):
    _live(feeds, monkeypatch, skip=("FFF",))
    res = scanner.Scanner(CFG).run()
    assert res["scanned"] == 5 and "FFF" not in [r["symbol"] for r in res["rows"]]


def test_live_prices_can_be_switched_off(feeds, monkeypatch):
    monkeypatch.setattr(data_provider, "kite_quotes", lambda *a, **k: pytest.fail("not asked when switched off"))
    res = scanner.Scanner({**CFG, "live_feed": False}).run()
    assert res["feed"] == {"prices": "delayed", "rows_live": 0, "rows_delayed": 6, "quotes_at": None,
                           "why_delayed": "Live prices are switched off in the settings."}
