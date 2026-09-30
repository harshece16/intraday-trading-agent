"""The universe-width research code (prereg-universe-width.md): the repaired
price panel, the screens, the honest-fill rules, and parity with the 3i
simulator it extends."""
import csv
import datetime
import io
import math
import os
import sys
import zipfile

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "research"))

import momentum_3i as m3  # noqa: E402
import momentum_width as mw  # noqa: E402
import nse_prices as npx  # noqa: E402

EQ, BE = 0, 1


# --- synthetic data ------------------------------------------------------------------

def _sessions(start="2020-01-01", n=700):
    d, out = datetime.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def _panel(n_stocks=40, n=700, wide=False):
    """Prices whose leaders rotate, so the book has to trade."""
    sessions = _sessions(n=n)
    chains = {}
    for k in range(n_stocks):
        px, closes = 100.0, []
        for i in range(n):
            px *= 1 + 0.002 * math.sin(2 * math.pi * (i / 180.0 + k / n_stocks)) \
                + 0.01 * (((i * 7 + k * 13) % 11) - 5) / 5
            closes.append(px)
        c = {"idx": list(range(n)), "close": closes[:], "raw": closes[:], "open": closes[:],
             "val": [1e8 + k * 1e6] * n, "isins": set()}
        if wide:
            c.update({"high": [x * 1.01 for x in closes], "low": [x * 0.99 for x in closes],
                      "prev": [closes[0]] + closes[:-1], "ser": [EQ] * n})
        chains["S%02d" % k] = c
    return sessions, chains


def _chain(rows):
    """rows: (session index, close, previous close, high, low, series)."""
    return {"idx": [r[0] for r in rows], "close": [r[1] for r in rows], "raw": [r[1] for r in rows],
            "open": [r[1] for r in rows], "val": [1e8] * len(rows), "isins": set(),
            "prev": [r[2] for r in rows], "high": [r[3] for r in rows], "low": [r[4] for r in rows],
            "ser": [r[5] for r in rows]}


def _flat(n, price=100.0, series=EQ, start=0):
    return [(start + i, price, price, price * 1.01, price * 0.99, series) for i in range(n)]


# --- the band-lock rule (H3) ------------------------------------------------------------

@pytest.mark.parametrize("close,prev,high,low,expected", [
    (105.0, 100.0, 105.0, 101.0, 1),      # closed at the 5% band
    (104.75, 100.0, 104.75, 101.0, 1),    # band rounded down to the tick
    (104.6, 100.0, 104.6, 101.0, 0),      # closed at its high, but not at a band
    (105.0, 100.0, 105.5, 101.0, 0),      # came off the band before the close
    (103.0, 100.0, 103.0, 100.0, 0),      # a strong close is not a lock
    (120.0, 100.0, 120.0, 101.0, 1),
    (102.0, 100.0, 102.0, 100.0, 1),
    (95.0, 100.0, 99.0, 95.0, -1),
    (90.0, 100.0, 99.0, 90.0, -1),
    (95.0, 100.0, 99.0, 94.0, 0),
    (105.0, 0.0, 105.0, 101.0, 0),        # no previous close printed
    (9.55, 10.0, 10.0, 9.55, -1),         # below Rs 20 a tick is wider than the window: -4.5% is the 5% band
    (9.40, 10.0, 10.0, 9.40, 0),          # two ticks from any band
    (10.45, 10.0, 10.45, 9.9, 1),
    (95.5, 100.0, 99.0, 95.5, 0),         # the same move at Rs 100 is not a lock
])
def test_lock(close, prev, high, low, expected):
    assert mw.lock(_chain([(0, close, prev, high, low, EQ)]), 0) == expected


# --- eligibility, ranking and screens ------------------------------------------------------

def test_ranking_is_3is_ranking():
    sessions, chains = _panel()
    for _, idx in m3.month_ends(sessions)[-4:-1]:
        assert [n for _, n in mw.ranked(mw.eq_view(chains), idx)] == m3.ranked_universe(chains, idx)


def test_trade_for_trade_rows_do_not_count_towards_eligibility():
    sessions, chains = _panel(wide=True)
    idx = m3.month_ends(sessions)[-2][1]
    before = [n for _, n in mw.ranked(mw.eq_view(chains), idx)]
    chains["S30"]["ser"][idx] = BE                   # in trade-for-trade on the month-end
    after = [n for _, n in mw.ranked(mw.eq_view(chains), idx)]
    assert "S30" in before and "S30" not in after
    assert [n for n in before if n != "S30"] == after


def test_screen_s1_needs_60_sessions_clear_of_trade_for_trade():
    sessions, chains = _panel(wide=True)
    idx = 600
    c = chains["S01"]
    assert mw.passes_screens(c, idx, 1e8)
    c["ser"][idx - 59] = BE
    assert not mw.passes_screens(c, idx, 1e8)
    c["ser"][idx - 59], c["ser"][idx - 60] = EQ, BE
    assert mw.passes_screens(c, idx, 1e8)


def test_screen_s2_needs_120_traded_days_of_126():
    rows = [r for r in _flat(700) if not 500 <= r[0] < 507]      # seven days with no trade
    c = _chain(rows)
    assert not mw.passes_screens(c, 600, 1e8)                    # 119 of the last 126
    assert mw.passes_screens(c, 640, 1e8)                        # the gap has left the window
    c = _chain([r for r in _flat(700) if not 500 <= r[0] < 506])
    assert mw.passes_screens(c, 600, 1e8)                        # 120 of 126


def test_a_row_with_no_traded_value_is_not_a_traded_day():
    c = _chain(_flat(700))
    for j in range(500, 507):
        c["val"][j] = 0.0
    assert mw.screens_failed(c, 600, 1e8) == ["S2"]
    b = _book()
    b.order("buy", "X", 0.0, placed=502, amount=1000.0)
    b.work({"X": c}, 502, _sessions(n=700))
    assert not b.pos and b.count["carried_buy_no_trade"] == 1


def test_screens_failed_names_each_screen():
    c = _chain(_flat(700))
    c["ser"][590] = BE
    assert mw.screens_failed(c, 600, 1.0) == ["S1", "S3"]
    assert mw.passes_screens(_chain(_flat(700)), 600, 1e8)


def test_screen_s3_is_a_floor_on_median_traded_value():
    c = _chain(_flat(700))
    assert mw.passes_screens(c, 600, 7_000_000.0)
    assert not mw.passes_screens(c, 600, 6_999_999.0)


def test_a_screened_list_never_moves_a_stock_down():
    sessions, chains = _panel(wide=True)
    for k in (22, 27, 33):
        for j in range(560, 640):
            chains["S%02d" % k]["ser"][j] = BE
    unis = mw.universes(sessions, chains)
    month = m3.month_ends(sessions)[-2][0]
    u = unis[month]
    assert len(u["ewide"]) < len(u["e3i"])
    for place, name in enumerate(u["ewide"], 1):
        assert place <= u["rank3i"][name]


def test_start_month_needs_the_list_full_from_then_on():
    unis = {"2010-01": {"ewide": ["x"] * 900}, "2010-02": {"ewide": ["x"] * 1000},
            "2010-03": {"ewide": ["x"] * 999}, "2010-04": {"ewide": ["x"] * 1000},
            "2010-05": {"ewide": ["x"] * 1200}}
    assert mw.start_month(unis, "ewide", 1000) == "2010-04"
    assert mw.start_month(unis, "ewide", 900) == "2010-01"
    assert mw.start_month(unis, "ewide", 1500) is None


def test_slippage_follows_the_rank_at_the_month_end():
    uni = {"rank3i": {"a": 1, "b": 200, "c": 201, "d": 600, "e": 601, "f": 1000, "g": 1001}}
    tiered = {"ranks": (1, 1000)}
    assert [mw.slippage(n, uni, tiered, False) for n in "abcdefg"] == [
        0.0005, 0.0005, 0.0015, 0.0025, 0.0040, 0.0040, 0.0075]
    assert [mw.slippage(n, uni, tiered, True) for n in "abcdefg"] == [
        0.0010, 0.0010, 0.0030, 0.0050, 0.0080, 0.0080, 0.0150]
    assert mw.slippage("unranked", uni, tiered, False) == 0.0075
    assert mw.slippage("g", uni, mw.PARTS["B"], True) == 0.0010      # the replications keep 3i's flat rate


# --- parity with the 3i simulator --------------------------------------------------------

def test_with_honest_fills_off_the_simulator_is_3is():
    sessions, chains = _panel()
    ranked = {m: m3.ranked_universe(chains, i) for m, i in m3.month_ends(sessions) if m >= m3.SELECTION_START}
    old, _, _, old_holdings = m3.simulate(sessions, chains, ranked, "A", m3.CAPITAL, m3.SELECTION_START)
    unis = mw.universes(sessions, chains, screens=False)
    new, strat, _, holdings = mw.simulate(sessions, chains, unis, mw.PARTS["A"], m3.CAPITAL,
                                          m3.SELECTION_START, honest=False)
    assert len(new) == len(old) > 10
    for a, b in zip(new, old):
        assert a[:2] == b[:2]
        assert a[2] == pytest.approx(b[2], rel=1e-12)
        assert a[3] == pytest.approx(b[3], rel=1e-12)
    assert holdings == old_holdings
    assert strat.sells > 0


def test_honest_fills_change_nothing_when_every_stock_trades_freely():
    sessions, chains = _panel(wide=True)
    unis = mw.universes(sessions, chains)
    off, _, _, _ = mw.simulate(sessions, chains, unis, mw.PARTS["A"], m3.CAPITAL, m3.SELECTION_START, honest=False)
    on, strat, _, _ = mw.simulate(sessions, chains, unis, mw.PARTS["A"], m3.CAPITAL, m3.SELECTION_START)
    assert [s[2] for s in on] == pytest.approx([s[2] for s in off], rel=1e-12)
    assert not [k for k in strat.count if k.startswith("carried")]


# --- the fill rules (H1 to H5) -------------------------------------------------------------

def _book(**kw):
    return mw.Book(1_000_000.0, dp=True, **kw)


def test_a_buy_at_the_upper_band_is_carried_to_the_next_session():
    sessions = _sessions(n=20)
    c = _chain([(0, 100, 100, 101, 99, EQ), (1, 105, 100, 105, 100, EQ), (2, 110, 105, 111, 104, EQ)])
    b = _book()
    b.order("buy", "X", 0.0, placed=1, amount=100_000.0)
    b.work({"X": c}, 1, sessions)
    assert not b.pos and len(b.orders) == 1 and b.count["carried_buy_locked"] == 1
    b.work({"X": c}, 2, sessions)
    assert not b.orders and b.buys == 1
    cost = 100_000.0 * (m3.STT + m3.STAMP_BUY + m3.NSE_TXN + m3.SEBI + m3.GST * (m3.NSE_TXN + m3.SEBI))
    assert b.pos["X"] == pytest.approx((100_000.0 - cost) / 110)       # filled at the later close


def test_a_buy_that_cannot_fill_in_five_sessions_is_cancelled():
    sessions = _sessions(n=20)
    c = _chain([(0, 100, 100, 101, 99, EQ), (9, 100, 100, 101, 99, EQ)])
    b = _book()
    b.order("buy", "X", 0.0, placed=1, amount=100_000.0)
    for s in range(1, 7):
        b.work({"X": c}, s, sessions)
    assert len(b.orders) == 1 and b.count["carried_buy_no_trade"] == 1      # still open on session 6
    b.work({"X": c}, 7, sessions)
    assert not b.orders and b.count["buys_cancelled"] == 1
    assert b.cash == 1_000_000.0 and not b.pos


def test_a_sell_at_the_lower_band_waits_until_the_stock_comes_off_it():
    sessions = _sessions(n=20)
    rows = [(0, 100, 100, 101, 99, EQ)] + [(i, 100 * 0.95 ** i, 100 * 0.95 ** (i - 1), 100 * 0.95 ** (i - 1) * 0.99,
                                            100 * 0.95 ** i, EQ) for i in range(1, 9)]
    rows.append((9, 70.0, rows[-1][1], 71.0, 66.0, EQ))
    c = _chain(rows)
    b = _book()
    b.pos["X"] = 1000.0
    b.order("sell", "X", 0.0, placed=1)
    for s in range(1, 9):
        b.work({"X": c}, s, sessions)
    assert "X" in b.pos and b.count["carried_sell_locked"] == 1
    b.work({"X": c}, 9, sessions)
    assert "X" not in b.pos and b.sells == 1
    assert b.cash - 1_000_000.0 == pytest.approx(
        70_000.0 * (1 - m3.STT - m3.NSE_TXN - m3.SEBI - m3.GST * (m3.NSE_TXN + m3.SEBI)) - m3.DP_PER_SELL)


def test_a_holding_in_trade_for_trade_is_priced_and_sold_from_its_own_rows():
    sessions = _sessions(n=20)
    c = _chain(_flat(5) + [(5 + i, 60.0, 60.0, 61.0, 59.0, BE) for i in range(5)])
    b = _book()
    b.pos["X"] = 1000.0
    assert b.value({"X": c}, 8) == pytest.approx(1_000_000.0 + 60_000.0)     # not the stale 100
    b.order("sell", "X", 0.0075, placed=8)
    b.work({"X": c}, 8, sessions)
    assert b.count["sells_priced_in_t2t"] == 1 and "X" not in b.pos
    assert b.turnover == pytest.approx(60_000.0)


def test_an_ended_chain_pays_its_last_close_or_nothing_under_stress():
    ended = _chain(_flat(30) + [(30 + i, 40.0, 40.0, 41.0, 39.0, BE) for i in range(3)])
    clean = _chain(_flat(30))
    for stress, chain, proceeds in ((False, ended, 40_000.0), (True, ended, 0.0), (True, clean, 100_000.0)):
        b = mw.Book(0.0, dp=False, stress=stress)
        b.pos["X"] = 1000.0
        b.sell_ended("X", chain, 0.0, "2020-05")
        assert "X" not in b.pos and b.forced == 1
        assert b.ended[0]["month"] == "2020-05" and b.ended[0]["ended_in_t2t"] == (chain is ended)
        assert b.ended[0]["last_series"] == ("BE" if chain is ended else "EQ")
        assert b.ended[0]["proceeds"] == pytest.approx(b.cash)
        assert b.cash == pytest.approx(proceeds * (1 - m3.STT - m3.NSE_TXN - m3.SEBI
                                                   - m3.GST * (m3.NSE_TXN + m3.SEBI)))


def test_a_cancelled_buy_is_decided_again_at_the_next_month_end():
    sessions, chains = _panel(n_stocks=20, wide=True)
    first_fill = m3.month_ends(sessions)[13][1] + 1
    halted = range(first_fill, first_fill + 10)             # no trade for ten sessions from the first fill
    c = chains["S19"]
    keep = [j for j, i in enumerate(c["idx"]) if i not in halted]
    for k in ("idx", "close", "raw", "open", "val", "prev", "high", "low", "ser"):
        c[k] = [c[k][j] for j in keep]
    unis = mw.universes(sessions, chains)
    series, _, bench, _ = mw.simulate(sessions, chains, unis, mw.PARTS["A"], m3.CAPITAL, m3.SELECTION_START)
    assert bench.count["carried_buy_no_trade"] >= 1 and bench.count["buys_cancelled"] >= 1
    assert "S19" in bench.pos                               # bought at a later month-end
    assert all(v > 0 for s in series for v in s[2:])


def test_open_orders_are_dropped_at_the_month_end():
    b = _book()
    b.order("sell", "X", 0.0, placed=3)
    b.order("buy", "Y", 0.0, placed=3, amount=1000.0)
    b.drop_orders()
    assert not b.orders and b.count["orders_dropped_at_month_end"] == 2


# --- statistics and the rule for K -----------------------------------------------------------

def test_halves_are_3is_for_a_full_run():
    months = ["%d-%02d" % (y, m) for y in range(2010, 2026) for m in range(1, 13)]
    months = [m for m in months if "2010-02" <= m <= "2025-11"]
    xs = list(range(len(months) - 1))
    h1, h2 = mw.halves(xs)
    assert (len(h1), len(h2)) == (94, 95)
    assert mw.series_stats([0.01, 0.02] * 94 + [0.01], months)["second_half_from"] == m3.HALF_SPLIT


def _lists(sizes):
    sessions = _sessions(start="2009-01-01", n=4400)
    months = [m for m, _ in m3.month_ends(sessions) if m >= m3.SELECTION_START]
    return sessions, {m: {"ewide": ["x"] * sizes(m)} for m in months}


def test_k_is_800_unless_the_list_is_too_short_for_120_months():
    sessions, unis = _lists(lambda m: 900)
    assert mw.fixed_k(sessions, unis) == 800
    sessions, unis = _lists(lambda m: 900 if m >= "2017-01" else 650)
    assert mw.fixed_k(sessions, unis) == 600          # 800 names only from 2017: under 120 months
    sessions, unis = _lists(lambda m: 450)
    assert mw.fixed_k(sessions, unis) == 400
    sessions, unis = _lists(lambda m: 300)
    assert mw.fixed_k(sessions, unis) is None


def test_the_tiers_inside_k():
    assert mw.tiers_inside(800) == ["T3", "T4"]
    assert mw.tiers_inside(600) == ["T3"]
    assert mw.tiers_inside(400) == [] and mw.tiers_inside(None) == []


def test_thresholds_are_the_written_ones():
    assert (mw.T_TIER, mw.T_PAIRED, mw.T_FAMILY, mw.N_FAMILY) == (2.13, 1.65, 2.807, 10)


def test_a_fill_at_the_last_slippage_row_is_counted():
    sessions = _sessions(n=20)
    c = _chain(_flat(10))
    b = _book()
    b.order("buy", "X", 0.0075, placed=1, amount=100_000.0)
    b.order("buy", "Y", 0.0040, placed=1, amount=100_000.0)
    b.work({"X": c, "Y": c}, 1, sessions)
    assert b.count["fills_at_last_slippage_row"] == 1
    assert mw.book_report(b)["share_of_turnover_at_last_slippage_row"] == pytest.approx(0.5)


def test_paired_test_uses_the_months_both_books_have():
    months = ["2020-%02d" % m for m in range(1, 13)]
    wide = {"months": months[2:], "values": {"strategy": [100 * 1.03 ** i for i in range(10)]},
            "holdings": [{"month": m, "holdings": ["a", "b"]} for m in months[2:]]}
    running = {"months": months, "values": {"strategy": [100 * 1.01 ** i * (1 + 0.001 * (i % 3)) for i in range(12)]},
               "holdings": [{"month": m, "holdings": ["b", "c"]} for m in months]}
    wide["values"]["benchmark"] = [100 * 1.02 ** i for i in range(10)]
    running["values"]["benchmark"] = [100 * 1.01 ** i for i in range(12)]
    out = mw.paired_test(wide, running)
    assert out["n"] == 9 and out["mean"] > 0 and out["names_held_in_common_mean"] == 1
    assert out["difference_in_excess"]["mean"] + out["difference_in_benchmarks"]["mean"] == pytest.approx(out["mean"])
    assert out["difference_in_benchmarks"]["mean"] == pytest.approx(0.01)
    assert out["smallest_difference_detectable_at_80pct_power"] > 0


def test_a_row_the_loader_skipped_is_reported_as_not_applied():
    assert mw.not_applied("Consolidation Of Shares From Re 1 To Rs 10", 10, set())
    assert not mw.not_applied("Consolidation Of Shares From Re 1 To Rs 10", 10, {"consolidation"})
    assert mw.not_applied("Capital Reduction", 10, set())
    assert mw.not_applied("Bonus 1:1", 10, {"dividend"})
    assert not mw.not_applied("Bonus 1:1", 10, {"bonus"})
    assert not mw.not_applied("Annual General Meeting", 10, set())


# --- the repaired panel ------------------------------------------------------------------------

OLD_HEADER = ["SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE", "TOTTRDQTY", "TOTTRDVAL",
              "TIMESTAMP", "TOTALTRADES", "ISIN"]
NEW_HEADER = ["TradDt", "ISIN", "TckrSymb", "SctySrs", "OpnPric", "HghPric", "LwPric", "ClsPric", "LastPric",
              "PrvsClsgPric", "TtlTradgVol", "TtlTrfVal"]


def _zip(path, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("b.csv", buf.getvalue())


def _old_row(sym, series, close, prev, day, isin=""):
    return [sym, series, close, close + 1, close - 1, close, close, prev, 100, close * 100,
            day.strftime("%d-%b-%Y").upper(), 5, isin]


def test_wide_parser_reads_both_bhavcopy_formats(tmp_path):
    day = datetime.date(2025, 3, 3)
    _zip(tmp_path / "old.zip", OLD_HEADER, [_old_row("AAA", "EQ", 100, 99, day), _old_row("BBB", "BE", 50, 49, day),
                                            _old_row("CCC", "SM", 10, 10, day)])
    _zip(tmp_path / "new.zip", NEW_HEADER, [["2025-03-03", "INE1", "AAA", "EQ", 100, 101, 99, 100, 100, 99, 10, 1000],
                                            ["2025-03-03", "INE2", "BBB", "BZ", 50, 51, 49, 50, 50, 49, 10, 500],
                                            ["2025-03-03", "INE3", "CCC", "ST", 10, 10, 10, 10, 10, 10, 10, 100]])
    old = npx.parse_bhavcopy_wide(str(tmp_path / "old.zip"))
    new = npx.parse_bhavcopy_wide(str(tmp_path / "new.zip"))
    assert [(r[0], r[-1]) for r in old] == [("AAA", 0), ("BBB", 1)]
    assert [(r[0], r[-1]) for r in new] == [("AAA", 0), ("BBB", 2)]
    assert old[0][:7] == npx.parse_bhavcopy(str(tmp_path / "old.zip"))[0]
    assert (old[1][7], old[1][8]) == (51.0, 49.0) and (new[1][7], new[1][8]) == (51.0, 49.0)


def _cache(tmp_path, monkeypatch):
    bhav, ca = tmp_path / "bhav", tmp_path / "ca"
    bhav.mkdir()
    ca.mkdir()
    (bhav / "symbolchange.csv").write_text("SM_NAME,SM_KEY_SYMBOL,SM_NEW_SYMBOL,SM_APPLICABLE_FROM\n")
    days = [datetime.date(2025, 3, d) for d in (3, 4, 5, 6, 7)]
    series = ["EQ", "EQ", "BE", "BE", "EQ"]
    closes = [100, 102, 90, 80, 85]
    for i, day in enumerate(days):
        rows = [_old_row("AAA", series[i], closes[i], closes[i - 1] if i else 99, day, "INE000000001"),
                _old_row("BBB", "EQ", 200 + i, 199 + i, day, "INE000000002")]
        if i == 1:
            rows.insert(0, _old_row("AAA", "BE", 555, 100, day, "INE000000001"))    # both series on one day
        _zip(bhav / ("%s.zip" % day.strftime("%d%b%Y").upper()), OLD_HEADER, rows)
    (ca / "ca_2025.csv").write_text(
        '"SYMBOL","COMPANY NAME","SERIES","PURPOSE","FACE VALUE","EX-DATE","RECORD DATE",'
        '"BOOK CLOSURE START DATE","BOOK CLOSURE END DATE"\n'
        '"AAA","A Ltd","EQ","Dividend - Rs 9 Per Share","10","06-Mar-2025","","",""\n', encoding="utf-8")
    monkeypatch.setattr(npx, "HELD_OUT_DIR", str(tmp_path / "none"))
    return str(bhav), str(ca)


def test_repaired_panel_keeps_trade_for_trade_rows_and_prefers_eq(tmp_path, monkeypatch):
    bhav, ca = _cache(tmp_path, monkeypatch)
    sessions, chains, meta, events = npx.build(bhav_dir=bhav, ca_dir=ca, wide=True)
    a = chains["AAA"]
    assert a["idx"] == [0, 1, 2, 3, 4] and a["ser"] == [0, 0, 1, 1, 0]
    assert a["raw"] == [100, 102, 90, 80, 85]                       # the EQ row won on the day with both
    assert a["high"][2] == 91 and a["low"][2] == 89 and a["prev"][2] == 102
    assert meta["rows_by_series"]["BE"] == 2 and "AAA" in meta["aliases"]["AAA"]
    # the dividend is taken off the trade-for-trade close before its ex-date, not a stale EQ close
    assert events[0][2] == "dividend" and events[0][3] == pytest.approx(1 - 9 / 90)


def test_default_panel_is_unchanged_by_the_refactor(tmp_path, monkeypatch):
    bhav, ca = _cache(tmp_path, monkeypatch)
    sessions, chains, meta, events = npx.build(bhav_dir=bhav, ca_dir=ca)
    a = chains["AAA"]
    assert sorted(a) == ["close", "idx", "isins", "open", "raw", "val"]
    assert a["idx"] == [0, 1, 4] and a["raw"] == [100, 102, 85]     # EQ rows only, as 3i read them
    assert "rows_by_series" not in meta and "aliases" not in meta
    assert events[0][3] == pytest.approx(1 - 9 / 102)               # the stale close #175 describes


def test_load_caches_the_two_panels_apart(tmp_path, monkeypatch):
    bhav, ca = _cache(tmp_path, monkeypatch)
    monkeypatch.setattr(npx, "CACHE", str(tmp_path / "p.pkl"))
    narrow = npx.load(refresh=True, bhav_dir=bhav, ca_dir=ca)
    wide = npx.load(refresh=True, bhav_dir=bhav, ca_dir=ca, wide=True)
    assert os.path.exists(tmp_path / "p.pkl") and os.path.exists(tmp_path / "p_wide.pkl")
    assert "ser" in wide[1]["AAA"] and "ser" not in narrow[1]["AAA"]
    assert npx.load(bhav_dir=bhav, ca_dir=ca)[1]["AAA"]["raw"] == narrow[1]["AAA"]["raw"]


def test_a_consolidation_is_applied_in_the_repaired_panel_only(tmp_path, monkeypatch):
    bhav, ca = _cache(tmp_path, monkeypatch)
    with open(os.path.join(ca, "ca_2025.csv"), "a", encoding="utf-8") as fh:
        fh.write('"BBB","B Ltd","EQ","Consolidation Of Equity Shares From Re 1 Per Share To Rs 10 Per Share",'
                 '"10","05-Mar-2025","","",""\n')
    _, wide, meta, events = npx.build(bhav_dir=bhav, ca_dir=ca, wide=True)
    assert meta["actions_applied"]["consolidation"] == 1
    assert ("BBB", 2, "consolidation", 10.0) == tuple(e[:4] for e in events if e[0] == "BBB")[0]
    assert wide["BBB"]["close"][:2] == pytest.approx([2000.0, 2010.0]) and wide["BBB"]["close"][2] == 202
    _, narrow, meta, events = npx.build(bhav_dir=bhav, ca_dir=ca)
    assert "consolidation" not in meta["actions_applied"] and not [e for e in events if e[0] == "BBB"]
    assert narrow["BBB"]["close"] == narrow["BBB"]["raw"]


@pytest.mark.parametrize("purpose,expected", [
    ("Consolidation Of Equity Shares From Re 1 Per Share To Rs 10 Per Share", [("consolidation", 10.0)]),
    ("Capital Reduction Rs 10 To Rs 3.30 / Consolidation Rs 3.30 To Rs.10", [("consolidation", 10 / 3.3)]),
    ("Bonus 1:1", [("bonus", 2.0)]),
])
def test_parse_purpose_with_consolidations(purpose, expected):
    got = npx.parse_purpose(purpose, 10, repaired=True)
    assert [k for k, _ in got] == [k for k, _ in expected]
    assert [v for _, v in got] == pytest.approx([v for _, v in expected])
    assert npx.parse_purpose(purpose, 10) == [a for a in expected if a[0] != "consolidation"]


def test_consolidations_are_listed_with_their_ratio_and_who_they_touch():
    unis = {"2025-05": {"e3i": ["AAA"] + ["x"] * 500}, "2025-06": {"e3i": ["x"] * 500}}
    events = [("AAA", 7, "consolidation", 10.0, "2025-06-25", "Consolidation"), ("BBB", 3, "bonus", 0.5, "2025-06-25", "Bonus"),
              ("CCC", 9, "consolidation", 3.03, "2025-06-02", "Consolidation")]
    out = mw.consolidations(events, unis, held={"CCC"})
    assert [(o["symbol"], o["ratio"], o["inside_ranks_1_to_400"], o["held_by_this_book"]) for o in out] == [
        ("AAA", 10.0, True, False), ("CCC", 3.03, False, True)]


@pytest.mark.parametrize("purpose,fv,old,new", [
    ("Annual General Meeting / Div. Of Rs. 1.50/- Per Equity Share Of Rs. 10/- Each.", 10, 11.5, 1.5),
    ("Interim Div. Of Re. 0.70/- Per Equity Share Re.1/- Each", 1, 1.7, 0.7),
    ("Annual General Meeting And Dividend Rs.50/- Per Share (Special Dividend Rs.25/- Per Share And "
     "Final Dividend Rs.25/- Per Share)", 10, 100.0, 50.0),
    ("Dividend-Rs.8.50 Per Share (Including Special Dividend Of Rs.2/- Per Share).", 1, 10.5, 8.5),
    ("Interim Dividend Rs 6/- Per Share 9purpose Revised)", 2, 15.0, 6.0),
    ("Interim Dividend - Rs 17 Per Share Special Dividend - Rs 15 Per Share", 5, 32.0, 32.0),
    ("First Interim Dividend Rs.2/- Per Share (Purpose Revised)", 2, 2.0, 2.0),
    ("Dividend-150%", 2, 3.0, 3.0),
    ("Agm/Div-Rs.2.50 Per Share", 10, 2.5, 2.5),
    ("Dividend (Rs 5 Per Share)", 10, 5.0, 5.0),
])
def test_the_repaired_panel_reads_a_dividend_without_face_values_or_remarks(purpose, fv, old, new):
    assert npx.parse_purpose(purpose, fv) == [("dividend", pytest.approx(old))]
    assert npx.parse_purpose(purpose, fv, repaired=True) == [("dividend", pytest.approx(new))]


def test_the_repaired_panel_applies_a_dividend_of_nearly_the_whole_price(tmp_path, monkeypatch):
    bhav, ca = _cache(tmp_path, monkeypatch)
    with open(os.path.join(ca, "ca_2025.csv"), "a", encoding="utf-8") as fh:
        fh.write('"BBB","B Ltd","EQ","Interim Dividend - Rs 199 Per Share","10","05-Mar-2025","","",""\n')
    _, wide, meta, events = npx.build(bhav_dir=bhav, ca_dir=ca, wide=True)
    assert [e[2] for e in events if e[0] == "BBB"] == ["dividend"]
    assert wide["BBB"]["close"][1] == pytest.approx(201 * (1 - 199 / 201))
    _, narrow, meta, events = npx.build(bhav_dir=bhav, ca_dir=ca)
    assert not [e for e in events if e[0] == "BBB"] and meta["actions_applied"]["rejected"] == 1
