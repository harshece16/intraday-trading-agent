"""Research look L50 (docs/research/prereg-bulk-block-deals.md): parsing, the event
rules, the timing, the statistics, and the guarantees stage 0 makes (no price read,
no bar after the sample, no deal after 2025-12-22, a read-only cache).

Nothing here touches the network or the real candle cache."""
import ast
import json
import math
import os
import sqlite3
import statistics as st
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pytest

from research import deals_l50 as L

HEADER = '\ufeff"Date ","Symbol ","Security Name ","Client Name ","Buy / Sell ","Quantity Traded ",' \
         '"Trade Price / Wght. Avg. Price ","Remarks "\n'


def _csv(rows):
    out = HEADER
    for d, sym, client, side, qty, price, rem in rows:
        out += '"%s","%s","%s Ltd","%s","%s","%s","%s","%s"\n' % (d, sym, sym, client, side, qty, price, rem)
    return out


# ---- the module stays out of the live path and off the network at import -------------

def test_module_imports_no_network_or_live_module_at_import_time():
    tree = ast.parse(open(L.__file__).read())
    top = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            top.add(node.module.split(".")[0])
    assert not top & {"requests", "app", "kite_history", "kite_broker", "nse_feed", "config"}


# ---- the fetch plan ---------------------------------------------------------------------

def test_month_windows_cover_exactly_the_deal_dates_and_nothing_in_2026():
    w = L.month_windows()
    assert w[0] == ("2024-09-19", "2024-09-30")
    assert w[-1] == ("2025-12-01", "2025-12-22")
    assert len(w) == 16
    assert all(a <= b for a, b in w)
    assert all(b[:4] != "2026" and a >= L.DEAL_FIRST and b <= L.DEAL_LAST for a, b in w)
    assert L.month_windows("2025-02-10", "2025-03-05") == [("2025-02-10", "2025-02-28"), ("2025-03-01", "2025-03-05")]


def test_dmy_is_the_report_query_format():
    assert L.dmy("2024-09-19") == "19-09-2024"


# ---- parsing ------------------------------------------------------------------------------

def test_parse_reads_bom_padded_header_indian_grouping_and_multiline_remarks():
    text = _csv([("01-AUG-2024", "AHL", "JAIN  VANIJYA", "BUY", "3,03,645", "581.32", "-"),
                 ("01-AUG-2024", "AHL", "JAIN VANIJYA", "SELL", "12,26,654", "2,232.10", "-\r\nmore")])
    rows = L.parse_deals_csv(text)
    assert len(rows) == 2
    assert rows[0] == {"date": "2024-08-01", "symbol": "AHL", "name": "AHL Ltd", "client": "JAIN VANIJYA",
                       "side": "BUY", "qty": 303645, "price": 581.32, "remarks": "-"}
    assert rows[1]["qty"] == 1226654 and rows[1]["price"] == 2232.10 and rows[1]["side"] == "SELL"


def test_parse_header_only_is_an_empty_day_and_an_error_page_is_unknown():
    assert L.parse_deals_csv(HEADER) == []
    assert L.parse_deals_csv('{"data": []}') == []
    assert L.parse_deals_csv("<html>Access Denied</html>") is None
    assert L.parse_deals_csv('{"error": "x"}') is None
    assert L.parse_deals_csv(None) is None


SYMCHANGE = ("SM_NAME,SM_KEY_SYMBOL,SM_NEW_SYMBOL,SM_APPLICABLE_FROM\n"
             "ETERNAL LIMITED,ZOMATO,ETERNAL,09-APR-2025\n"
             "LTIMindtree Limited,LTI,LTIM,05-DEC-2022\n"
             "LTM Limited,LTIM,LTM,27-FEB-2026\n"
             "Tata Motors Passenger Vehicles Limited,TATAMOTORS,TMPV,24-OCT-2025\n"
             "Old Co,OLDSYM,NEWSYM,01-JAN-2020\n")


def test_symbol_changes_follow_chains_applicable_after_the_deal_date_only():
    ch = L.parse_symbol_changes(SYMCHANGE)
    assert L.canon("ZOMATO", "2024-10-01", ch) == "ETERNAL"
    assert L.canon("ZOMATO", "2025-05-01", ch) == "ZOMATO"      # already renamed: someone else's symbol
    assert L.canon("LTIM", "2025-01-10", ch) == "LTM"
    assert L.canon("LTI", "2022-01-10", ch) == "LTM"            # two steps
    assert L.canon("TATAMOTORS", "2025-06-02", ch) == "TMPV"
    assert L.canon("OLDSYM", "2024-10-01", ch) == "OLDSYM"      # change before the deal: not followed
    assert L.canon("RELIANCE", "2024-10-01", ch) == "RELIANCE"


def test_a_chain_step_ignores_a_rename_by_an_earlier_holder_of_the_new_symbol():
    # AAA traded on 2024-10-01, became BBB on 2025-06-01. A different company had held
    # BBB until it renamed to ZZZ on 2025-01-15: after the deal, but before AAA took BBB.
    ch = L.parse_symbol_changes("A Co,AAA,BBB,01-JUN-2025\nOld B Co,BBB,ZZZ,15-JAN-2025\n")
    assert L.canon("AAA", "2024-10-01", ch) == "BBB"
    # a genuine later rename of the new holder is still followed
    ch2 = L.parse_symbol_changes("A Co,AAA,BBB,01-JUN-2025\nOld B Co,BBB,ZZZ,15-JAN-2025\n"
                                 "A Co,BBB,CCC,01-MAR-2026\n")
    assert L.canon("AAA", "2024-10-01", ch2) == "CCC"


# ---- events ------------------------------------------------------------------------------

@pytest.mark.parametrize("b,s,side", [
    (704300, 704300, 0),        # a round-tripper nets to zero
    (2, 1, 1),                  # exactly twice: directional
    (1, 2, -1),
    (199, 100, 0),              # just under twice
    (0, 500, -1),
    (500, 0, 1),
    (0, 0, 0),
    (1523240, 2054795, 0),      # a stake transfer with listed buyers: MIXED
])
def test_bulk_side_is_the_net_with_the_two_to_one_rule(b, s, side):
    assert L.bulk_side(b, s) == side


def test_bulk_side_information_thresholds():
    assert L.bulk_side(101, 100, threshold=0.0) == 1
    assert L.bulk_side(100, 100, threshold=0.0) == 0
    assert L.bulk_side(3, 1, threshold=0.5) == 1 and L.bulk_side(2, 1, threshold=0.5) == 0


def test_aggregate_sums_a_stock_day_under_todays_symbol():
    ch = L.parse_symbol_changes(SYMCHANGE)
    rows = L.parse_deals_csv(_csv([
        ("02-OCT-2024", "ZOMATO", "A", "BUY", "1,000", "10", "-"),
        ("02-OCT-2024", "ZOMATO", "B", "BUY", "500", "10", "-"),
        ("02-OCT-2024", "ZOMATO", "C", "SELL", "200", "10", "-"),
        ("03-OCT-2024", "ZOMATO", "C", "SELL", "200", "10", "-")]))
    agg = L.aggregate(rows, "BULK", ch)
    a = agg[("ETERNAL", "2024-10-02", "BULK")]
    assert (a["B"], a["S"], a["rows"], a["deal_symbols"]) == (1500, 200, 3, {"ZOMATO"})
    assert ("ETERNAL", "2024-10-03", "BULK") in agg


def test_only_directional_bulk_events_enter_a_tested_class():
    assert L.classes_of({"kind": "BLOCK", "side": 0}) == []
    assert L.classes_of({"kind": "BULK", "side": 0}) == []
    assert L.classes_of({"kind": "BULK", "side": 1}) == ["BULK_BUY", "BULK_ALL"]
    assert L.classes_of({"kind": "BULK", "side": -1}) == ["BULK_SELL", "BULK_ALL"]


# ---- time ----------------------------------------------------------------------------------

def test_bar_epochs_are_ist_starts():
    assert L.ts_to_ist(1726803900) == ("2024-09-20", "09:15")      # the cache's first bar
    assert L.ts_to_ist(L.ist_midnight_epoch("2025-12-24")) == ("2025-12-24", "00:00")


def test_sessions_next_and_previous():
    bt = {"A": {"2024-09-20": {"09:15", "09:20"}, "2024-09-23": {"09:20"}, "2024-11-01": {"18:00"}},
          "B": {"2024-09-20": {"09:20"}, "2024-09-23": {"09:20"}}}
    s = L.regular_sessions(bt, min_symbols=2)
    assert s == ["2024-09-20", "2024-09-23"]                        # no 09:20 bar on a Muhurat date
    assert L.next_session("2024-09-19", s) == "2024-09-20"
    assert L.next_session("2024-09-20", s) == "2024-09-23"          # strictly after the deal date
    assert L.next_session("2024-09-21", s) == "2024-09-23"
    assert L.next_session("2024-09-23", s) is None
    assert L.prev_session("2024-09-23", s) == "2024-09-20"
    assert L.prev_session("2024-09-20", s) is None


def test_entry_is_the_0920_open_and_exits_are_exact_bars():
    assert L.ENTRY_BAR == "09:20" and L.AUCTION_BAR == "09:15"
    assert dict(L.EXITS) == {"15m": "09:30", "30m": "09:45", "60m": "10:15"}
    full = {"09:15", "09:20", "09:25", "09:30", "09:45", "10:15"}
    assert all(L.bars_present(full, h) for h in L.EXITS)
    assert not L.bars_present(full - {"09:20"}, "15m")
    assert not L.bars_present(full - {"10:15"}, "60m") and L.bars_present(full - {"10:15"}, "30m")
    assert not L.bars_present(None, "15m")


def test_event_returns_use_the_0920_open_and_the_exit_close_signed_by_side():
    prices = {"AAA": {"2024-10-01": {"open": {"09:15": 90.0, "09:20": 100.0, "09:30": 1.0},
                                     "close": {"09:30": 101.0, "09:45": 99.0, "10:15": 102.0}}}}
    buy = {"symbol": "AAA", "entry": "2024-10-01", "side": 1}
    sell = dict(buy, side=-1)
    assert L.event_returns(buy, prices, "15m") == pytest.approx(100.0)
    assert L.event_returns(sell, prices, "15m") == pytest.approx(-100.0)
    assert L.event_returns(buy, prices, "30m") == pytest.approx(-100.0)
    assert L.event_returns(sell, prices, "60m") == pytest.approx(-200.0)
    assert L.event_returns(dict(buy, entry="2024-10-02"), prices, "15m") is None


def test_boundary_between_the_deal_and_the_entry():
    assert L.boundary_between(["2024-10-02T00:00:00"], "2024-10-01", "2024-10-02")
    assert not L.boundary_between(["2024-10-01T00:00:00"], "2024-10-01", "2024-10-02")
    assert not L.boundary_between(None, "2024-10-01", "2024-10-02")


def test_engine_hours_guard():
    assert L._engine_hours(datetime(2026, 10, 1, 10, 0))            # Thursday
    assert L._engine_hours(datetime(2026, 10, 1, 8, 30))
    assert not L._engine_hours(datetime(2026, 10, 1, 8, 29))
    assert not L._engine_hours(datetime(2026, 10, 1, 15, 45))
    assert not L._engine_hours(datetime(2026, 10, 3, 10, 0))        # Saturday


# ---- statistics ------------------------------------------------------------------------------

@pytest.mark.parametrize("t,df,p", [(2.228139, 10, 0.05), (2.570582, 5, 0.05), (1.959964, 10 ** 7, 0.05),
                                    (2.0, 10, 0.073388), (0.0, 7, 1.0), (-2.228139, 10, 0.05)])
def test_student_t_two_sided_p(t, df, p):
    assert L.t_two_sided_p(t, df) == pytest.approx(p, abs=2e-6)


def test_clustered_se_with_singleton_clusters_is_the_ordinary_se():
    v = [1.0, 3.0, -2.0, 5.0, 0.5]
    r = L.clustered_mean(v, ["a", "b", "c", "d", "e"])
    assert r["mean"] == pytest.approx(st.mean(v))
    assert r["se"] == pytest.approx(st.stdev(v) / math.sqrt(len(v)))
    assert r["t"] == pytest.approx(st.mean(v) / (st.stdev(v) / math.sqrt(len(v))))
    assert r["p"] == pytest.approx(L.t_two_sided_p(r["t"], 4))


def test_clustering_widens_the_se_when_same_date_events_move_together():
    v = [10.0, 10.0, -2.0, -2.0, 4.0, 4.0]
    flat = L.clustered_mean(v, list(range(6)))
    by_day = L.clustered_mean(v, ["d1", "d1", "d2", "d2", "d3", "d3"])
    assert by_day["clusters"] == 3 and by_day["se"] > flat["se"]
    # CR1 by hand: sums of deviations per cluster, G/(G-1) * sum^2 / n^2
    m = st.mean(v)
    sums = [2 * (10 - m), 2 * (-2 - m), 2 * (4 - m)]
    assert by_day["se"] == pytest.approx(math.sqrt(1.5 * sum(s * s for s in sums) / 36))


def test_one_cluster_gives_no_t():
    r = L.clustered_mean([1.0, 2.0, 3.0], ["d", "d", "d"])
    assert r["t"] is None and r["mean"] == 2.0
    assert L.clustered_mean([], [])["mean"] is None


def test_cell_gate_needs_sixty_events_positive_t_and_both_halves():
    def cell(n, mean, t, h1, h2):
        return {"stats": {"n": n, "mean": mean, "t": t}, "halves": {"first": {"mean": h1}, "second": {"mean": h2}}}
    assert all(L.cell_gate(cell(60, 5.0, 2.1, 1.0, 2.0)).values())
    assert not L.cell_gate(cell(59, 5.0, 2.1, 1.0, 2.0))["events_ge_60"]
    assert not L.cell_gate(cell(80, 5.0, 1.9, 1.0, 2.0))["mean_net_positive_t_gt_2"]
    assert not L.cell_gate(cell(80, -5.0, -3.0, 1.0, 2.0))["mean_net_positive_t_gt_2"]
    assert not L.cell_gate(cell(80, 5.0, 3.0, -1.0, 2.0))["both_halves_positive"]
    assert not L.cell_gate(cell(80, 5.0, 3.0, None, 2.0))["both_halves_positive"]
    assert L.COST_BP == 16.63 and L.BH_Q == 0.10 and L.MIN_EVENTS == 60


# ---- the candle cache: read-only, bounded, and stage 0 selects no price -------------------------

def _db_without_prices(path, bars):
    """A candle table with NO price columns: a loader that reads a price cannot run on it."""
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts INTEGER)")
    c.execute("CREATE TABLE fetched (symbol TEXT, interval TEXT, from_date TEXT, to_date TEXT, rows INTEGER, "
              "fetched_at REAL)")
    c.executemany("INSERT INTO candles VALUES (?, '5m', ?)", bars)
    c.commit()
    c.close()


def _ts(d, hm):
    return L.ist_midnight_epoch(d) + int(hm[:2]) * 3600 + int(hm[3:]) * 60


def test_stage0_bar_loader_reads_no_price_and_nothing_after_the_sample(tmp_path):
    p = str(tmp_path / "c.db")
    _db_without_prices(p, [("AAA", _ts("2025-12-23", "09:20")), ("AAA", _ts("2025-12-24", "09:20")),
                           ("AAA", _ts("2026-01-02", "09:20"))])
    conn = L.open_candles_ro(p)
    bt = L.load_bar_times(conn)
    assert dict(bt["AAA"]) == {"2025-12-23": {"09:20"}}
    with pytest.raises(sqlite3.OperationalError):
        L.load_bar_prices(conn)                       # the price loader does need prices
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO candles VALUES ('X', '5m', 1)")   # read-only


# ---- stage 0 end to end, on a fake NSE and a price-free cache ----------------------------------------

SYMS = ["S%02d" % i for i in range(70)]
SESSIONS = ["2024-09-20", "2024-09-23", "2024-09-24", "2024-09-25", "2025-12-22", "2025-12-23"]


class FakeNse(object):
    """Serves the report's CSV for any from/to from a fixed list of rows."""

    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def get_csv(self, path):
        q = parse_qs(urlparse(path).query)
        kind = q["optionType"][0]
        lo = datetime.strptime(q["from"][0], "%d-%m-%Y").date().isoformat()
        hi = datetime.strptime(q["to"][0], "%d-%m-%Y").date().isoformat()
        self.calls.append((kind, lo, hi))
        sel = [r for r in self.rows[kind]
               if lo <= datetime.strptime(r[0], "%d-%b-%Y").date().isoformat() <= hi]
        text = _csv(sel)
        return 200, text.encode("utf-8"), L.parse_deals_csv(text), 1

    def get_archive(self, url):
        return 200, SYMCHANGE.encode()


def _fixture(tmp_path, monkeypatch, n_buy):
    bars = []
    for s in SYMS:
        for d in SESSIONS:
            for hm in ("09:15", "09:20", "09:30", "09:45", "10:15"):
                bars.append((s, _ts(d, hm)))
    bars.append(("S00", _ts("2025-12-24", "09:20")))          # after the sample: must not load
    p = str(tmp_path / "c.db")
    _db_without_prices(p, bars)
    bulk = [("19-SEP-2024", SYMS[i], "FUND %d" % i, "BUY", "1,000", "10", "-") for i in range(n_buy)]
    bulk += [("20-SEP-2024", "S01", "HFT", "BUY", "500", "10", "-"),
             ("20-SEP-2024", "S01", "HFT", "SELL", "500", "10", "-"),          # MIXED
             ("22-DEC-2025", "S02", "PROMOTER", "SELL", "900", "10", "-"),     # entry 2025-12-23: in sample
             ("23-SEP-2024", "NOTMEMBER", "X", "BUY", "900", "10", "-")]
    block = [("24-SEP-2024", "S03", "A", "BUY", "100", "10", ""), ("24-SEP-2024", "S03", "B", "SELL", "100", "10", "")]
    monkeypatch.setattr(L, "CACHE_DIR", str(tmp_path / "nse_deals"))
    monkeypatch.setattr(L, "STAGE0_OUT", str(tmp_path / "l50_stage0.json"))
    monkeypatch.setattr(L, "EVENTS_CSV", str(tmp_path / "l50_events.csv"))
    monkeypatch.setattr(L, "RESULT_OUT", str(tmp_path / "l50_result.json"))
    monkeypatch.setattr(L, "MIN_SYMBOLS_REGULAR", 1)
    monkeypatch.setattr(L, "load_membership_rows", lambda: [{"symbol": s, "from": "", "to": ""} for s in SYMS])
    return L.open_candles_ro(p), FakeNse({"bulk_deals": bulk, "block_deals": block})


def test_stage0_end_to_end_fixes_the_family_and_reads_no_price(tmp_path, monkeypatch):
    conn, nse = _fixture(tmp_path, monkeypatch, n_buy=62)
    s0 = L.run_stage0(conn, client=nse)
    assert s0["status"] == "STAGE0_DONE", s0.get("halt")
    assert s0["reads_price"] is False
    assert s0["completeness"]["all_identical"] and len(s0["completeness"]["dates"]) <= 6
    assert all(to <= L.DEAL_LAST for _, _, to in nse.calls)
    assert s0["boundaries"]["last_bar_date_loaded"] == "2025-12-23"
    assert s0["sessions"]["deal_dates_in_sample_not_regular"] == []
    assert s0["sessions"]["regular_sessions_with_no_bulk_row"] == ["2024-09-24", "2024-09-25"]
    assert s0["classes"]["BULK_BUY"] == 62 and s0["classes"]["BULK_SELL"] == 1
    assert s0["classes"]["MIXED"] == 1 and s0["classes"]["BLOCK"] == 1
    assert s0["symbols"]["stock_days_not_nifty100_on_entry"] == 1
    cells = s0["bars"]["cells"]
    assert cells["BULK_ALL:60m"]["events"] == 63 and cells["BULK_SELL:60m"]["events"] == 1
    assert s0["family"]["cells"] == ["BULK_BUY:15m", "BULK_BUY:30m", "BULK_BUY:60m",
                                     "BULK_ALL:15m", "BULK_ALL:30m", "BULK_ALL:60m"]
    written = json.load(open(L.STAGE0_OUT))
    assert written["status"] == "STAGE0_DONE"
    lines = open(L.EVENTS_CSV).read().splitlines()
    assert len(lines) == 1 + 62 + 1 + 1 + 1
    assert os.path.exists(os.path.join(L.CACHE_DIR, "bulk_deals_2024-09-19_2024-09-30.csv"))
    # the measurement pass cannot run on this price-free cache, and refuses a second run
    open(L.RESULT_OUT, "w").write("{}")
    with pytest.raises(SystemExit):
        L.run_measurement(conn, written)


def test_stage0_is_void_under_sixty_directional_events(tmp_path, monkeypatch):
    conn, nse = _fixture(tmp_path, monkeypatch, n_buy=58)
    s0 = L.run_stage0(conn, client=nse)
    assert s0["status"] == "VOID" and s0["halt"]["step"] == 6
    assert s0["family"]["cells"] == []
    with pytest.raises(SystemExit):
        L.run_measurement(conn, s0)


def test_stage0_halts_when_a_one_day_query_disagrees_with_its_month(tmp_path, monkeypatch):
    conn, nse = _fixture(tmp_path, monkeypatch, n_buy=62)
    real = nse.get_csv

    def lossy(path):
        status, raw, rows, a = real(path)
        q = parse_qs(urlparse(path).query)
        if q["from"] == q["to"] and rows:
            rows = rows[1:]
        return status, raw, rows, a
    nse.get_csv = lossy
    s0 = L.run_stage0(conn, client=nse)
    assert s0["status"] == "HALTED" and s0["halt"]["step"] == 1


def test_measurement_pass_on_a_priced_fixture(tmp_path, monkeypatch):
    """Stage 0 then the one pass on known prices: BUY events gain 50 + i%5 bp by 09:35,
    SELL events are shorted; the market moves the same for everyone."""
    conn, nse = _fixture(tmp_path, monkeypatch, n_buy=62)
    p = str(tmp_path / "priced.db")
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts INTEGER, open REAL, high REAL, low REAL, "
              "close REAL, volume INTEGER)")
    c.execute("CREATE TABLE fetched (symbol TEXT, interval TEXT, from_date TEXT, to_date TEXT, rows INTEGER, "
              "fetched_at REAL)")
    for i, s in enumerate(SYMS):
        up = 1 + (0.0050 + 0.0001 * (i % 5))
        for d in SESSIONS:
            for hm, o, cl in (("09:15", 99.0, 99.5), ("09:20", 100.0, 100.1), ("09:30", 100.2, 100.0 * up),
                              ("09:45", 100.0, 100.0), ("10:15", 100.0, 99.0)):
                c.execute("INSERT INTO candles VALUES (?, '5m', ?, ?, ?, ?, ?, 1)", (s, _ts(d, hm), o, o, cl, cl))
    c.commit()
    c.close()
    conn = L.open_candles_ro(p)
    s0 = L.run_stage0(conn, client=nse)
    assert s0["status"] == "STAGE0_DONE"
    res = L.run_measurement(conn, json.load(open(L.STAGE0_OUT)))
    buy = res["cells"]["BULK_BUY:15m"]["stats"]
    expected = st.mean(50 + (i % 5) for i in range(62)) - 16.63
    assert buy["n"] == 62 and buy["mean"] == pytest.approx(expected, abs=1e-6)
    assert res["cells"]["BULK_SELL:60m"]["stats"]["mean"] == pytest.approx(100.0 - 16.63)   # short gains 100 bp
    assert res["cells"]["BULK_BUY:60m"]["stats"]["mean"] == pytest.approx(-100.0 - 16.63)
    # one entry session for all 62 buys: one cluster, so no t, and the gate cannot pass
    assert buy["clusters"] == 1 and buy["t"] is None and not res["any_pass"]
    assert res["family"] == s0["family"]["cells"]
    assert res["descriptive"]["BULK_BUY"]["open_0915_to_0920"]["mean"] == pytest.approx(1e4 * (100 / 99 - 1))
    with pytest.raises(SystemExit):
        L.run_measurement(conn, json.load(open(L.STAGE0_OUT)))                        # one run only
