import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import database
import depth_sampler


def _quote(bid=100.0, ask=100.1, q=1000):
    return {"last_price": 100.05, "volume": 5000, "buy_quantity": 40000, "sell_quantity": 30000,
            "depth": {"buy": [{"price": bid - i * 0.05, "quantity": q, "orders": 2} for i in range(5)],
                      "sell": [{"price": ask + i * 0.05, "quantity": q * 2, "orders": 2} for i in range(5)]}}


def test_snapshot_measures_spread_depth_and_imbalance():
    r = depth_sampler.snapshot("TESTCO", _quote(), 1.0)
    assert r["bid"] == 100.0 and r["ask"] == 100.1 and abs(r["spread_bp"] - 9.995) < 0.01
    assert r["bid_qty5"] == 5000 and r["ask_qty5"] == 10000
    assert abs(r["imbalance5"] - (-1 / 3)) < 1e-4          # asks twice the bids -> leans to the sell side
    assert r["total_buy_qty"] == 40000


def test_an_empty_book_gives_no_row():
    assert depth_sampler.snapshot("TESTCO", {"depth": {"buy": [], "sell": []}}, 1.0) is None
    assert depth_sampler.snapshot("TESTCO", {}, 1.0) is None


def test_sample_writes_one_row_per_symbol_and_survives_a_bad_quote():
    fetched = []
    def fetch(symbols):
        fetched.append(list(symbols))
        return {"NSE:A": _quote(), "NSE:B": {"depth": {"buy": [], "sell": []}}}
    n = depth_sampler.sample(["A", "B", "C"], 1700000000.0, fetch=fetch)
    assert fetched == [["A", "B", "C"]]                      # one quote call for the whole list
    assert n == 1
    st = database.depth_sample_stats()
    assert st["rows"] == 1 and st["symbols"] == 1


def test_a_failing_fetch_never_raises():
    def boom(symbols):
        raise RuntimeError("Kite down")
    assert depth_sampler.sample(["A"], 1.0, fetch=boom) == 0


def _at(hhmm):
    from datetime import datetime
    import trading_engine
    h, m = map(int, hhmm.split(":"))
    return datetime(2026, 9, 28, h, m, tzinfo=trading_engine.IST)


def test_window_sampler_is_a_no_op_outside_its_windows():
    calls = []
    for hhmm in ("09:14", "09:30", "12:00", "14:59", "15:30"):
        assert depth_sampler.sample_windows(_at(hhmm), 1.0, fetch=lambda i: calls.append(i) or {}) == 0
    assert calls == []


def test_window_sampler_records_etf_books_and_the_index_level():
    fetched = []
    def fetch(instruments):
        fetched.append(list(instruments))
        return {"NSE:NIFTYBEES": _quote(bid=265.0, ask=265.02), "NSE:SETFNIF50": _quote(),
                "NSE:NIFTY 50": {"last_price": 23129.4}}
    n = depth_sampler.sample_windows(_at("15:25"), 1790332500.0, fetch=fetch)
    assert fetched == [["NSE:NIFTYBEES", "NSE:SETFNIF50", "NSE:NIFTY 50"]]   # one call per tick
    assert n == 3
    n = depth_sampler.sample_windows(_at("09:16"), 1790386560.0, fetch=fetch)
    assert n == 3


def test_window_sampler_never_raises():
    def boom(instruments):
        raise RuntimeError("kite down")
    assert depth_sampler.sample_windows(_at("09:20"), 1.0, fetch=boom) == 0


def test_index_row_needs_a_level():
    assert depth_sampler.index_row("NIFTY 50", {}, 1.0) is None
    assert depth_sampler.index_row("NIFTY 50", {"last_price": 1.0}, 2.0) == {"ts": 2.0, "symbol": "NIFTY 50", "ltp": 1.0}


# ---- the book level by level (#188) ----------------------------------------

import json
import sqlite3

import pytest

# The shape Kite's quote() returns for one instrument (kiteconnect's documented
# payload; keys in Kite's order). Levels are best first on both sides.
KITE_QUOTE = {
    "instrument_token": 408065, "last_price": 4084.5, "volume": 12510, "buy_quantity": 4596,
    "sell_quantity": 6385, "ohlc": {"open": 4088.0, "high": 4093.0, "low": 4080.0, "close": 4065.0},
    "depth": {
        "buy": [{"price": 4084.0, "orders": 5, "quantity": 53}, {"price": 4083.0, "orders": 12, "quantity": 145},
                {"price": 4082.0, "orders": 11, "quantity": 63}, {"price": 4081.0, "orders": 18, "quantity": 69},
                {"price": 4080.0, "orders": 27, "quantity": 89}],
        "sell": [{"price": 4085.0, "orders": 10, "quantity": 43}, {"price": 4086.0, "orders": 27, "quantity": 134},
                 {"price": 4087.0, "orders": 17, "quantity": 133}, {"price": 4088.0, "orders": 13, "quantity": 70},
                 {"price": 4089.0, "orders": 10, "quantity": 46}],
    },
}


def test_snapshot_records_all_five_levels_with_orders_from_a_kite_quote():
    r = depth_sampler.snapshot("INFY", KITE_QUOTE, 1790000000.0)
    assert json.loads(r["bid_levels_json"]) == [[4084.0, 53, 5], [4083.0, 145, 12], [4082.0, 63, 11],
                                                [4081.0, 69, 18], [4080.0, 89, 27]]
    assert json.loads(r["ask_levels_json"]) == [[4085.0, 43, 10], [4086.0, 134, 27], [4087.0, 133, 17],
                                                [4088.0, 70, 13], [4089.0, 46, 10]]


def test_the_existing_columns_keep_their_meaning():
    """The pre-registered order-book test (L37) reads these columns; #188
    must not change a single value."""
    r = depth_sampler.snapshot("INFY", KITE_QUOTE, 1790000000.0)
    assert (r["bid"], r["ask"], r["bid_qty1"], r["ask_qty1"]) == (4084.0, 4085.0, 53, 43)
    assert (r["bid_qty5"], r["ask_qty5"]) == (419, 426)                 # sums of the five levels
    assert r["spread_bp"] == round(1.0 / 4084.5 * 1e4, 3)
    assert r["imbalance5"] == round((419 - 426) / (419 + 426), 4)
    assert (r["ltp"], r["volume"], r["total_buy_qty"], r["total_sell_qty"]) == (4084.5, 12510, 4596, 6385)
    # the stored levels agree with the summary columns
    bids = json.loads(r["bid_levels_json"])
    assert bids[0][:2] == [r["bid"], r["bid_qty1"]] and sum(lv[1] for lv in bids) == r["bid_qty5"]


def test_a_thin_book_stores_only_its_real_levels():
    """Kite pads a thin book with zero levels; they are not stored, and
    `orders` is None if Kite leaves it out."""
    quote = {"last_price": 50.0, "depth": {
        "buy": [{"price": 49.95, "quantity": 10, "orders": 1}, {"price": 49.9, "quantity": 5}]
               + [{"price": 0, "quantity": 0, "orders": 0}] * 3,
        "sell": [{"price": 50.05, "quantity": 7, "orders": 2}] + [{"price": 0, "quantity": 0, "orders": 0}] * 4}}
    r = depth_sampler.snapshot("THIN", quote, 1.0)
    assert json.loads(r["bid_levels_json"]) == [[49.95, 10, 1], [49.9, 5, None]]
    assert json.loads(r["ask_levels_json"]) == [[50.05, 7, 2]]
    assert (r["bid_qty5"], r["ask_qty5"]) == (15, 7)


def test_sample_writes_the_levels_and_an_index_row_leaves_them_null():
    def fetch(instruments):
        return {"NSE:NIFTYBEES": KITE_QUOTE, "NSE:SETFNIF50": {}, "NSE:NIFTY 50": {"last_price": 23129.4}}
    assert depth_sampler.sample_windows(_at("15:25"), 1790332500.0, fetch=fetch) == 2
    rows = {r["symbol"]: r for r in database._conn().execute(
        "SELECT symbol, bid, bid_levels_json, ask_levels_json FROM depth_samples")}
    assert json.loads(rows["NIFTYBEES"]["ask_levels_json"])[4] == [4089.0, 46, 10]
    assert rows["NIFTY 50"]["bid_levels_json"] is None and rows["NIFTY 50"]["ask_levels_json"] is None
    assert database.depth_sample_stats()["rows_with_levels"] == 1


OLD_DEPTH_SCHEMA = """
CREATE TABLE depth_samples (
    ts REAL NOT NULL, symbol TEXT NOT NULL, ltp REAL, bid REAL, ask REAL, spread_bp REAL,
    bid_qty1 INTEGER, ask_qty1 INTEGER, bid_qty5 INTEGER, ask_qty5 INTEGER, imbalance5 REAL,
    volume INTEGER, total_buy_qty INTEGER, total_sell_qty INTEGER
);
CREATE INDEX idx_depth_symbol_ts ON depth_samples(symbol, ts);
"""
OLD_COLS = ["ts", "symbol", "ltp", "bid", "ask", "spread_bp", "bid_qty1", "ask_qty1", "bid_qty5", "ask_qty5",
            "imbalance5", "volume", "total_buy_qty", "total_sell_qty"]


def test_the_migration_adds_the_level_columns_to_an_old_journal_and_rewrites_nothing(tmp_path, monkeypatch):
    path = tmp_path / "old_journal.db"
    old = sqlite3.connect(path)
    old.executescript(OLD_DEPTH_SCHEMA)
    old.executemany("INSERT INTO depth_samples VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(1790000000.0 + i, "RELIANCE", 1400.1, 1400.0, 1400.2, 1.428, 50 + i, 70, 900, 1100,
                      -0.1, 12345, 40000, 30000) for i in range(3)]
                    + [(1790000001.0, "NIFTY 50", 25000.5) + (None,) * 11])
    old.commit()
    before = old.execute(f"SELECT rowid, {', '.join(OLD_COLS)} FROM depth_samples ORDER BY rowid").fetchall()
    old.close()

    monkeypatch.setattr(database, "DB_PATH", path)
    database._local.conn = None
    conn = database._conn()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(depth_samples)")]
    assert cols == OLD_COLS + ["bid_levels_json", "ask_levels_json"]      # appended; nothing moved
    after = conn.execute(f"SELECT rowid, {', '.join(OLD_COLS)} FROM depth_samples ORDER BY rowid").fetchall()
    assert [tuple(r) for r in after] == before                            # every old value as it was
    assert conn.execute("SELECT COUNT(*) FROM depth_samples WHERE bid_levels_json IS NOT NULL "
                        "OR ask_levels_json IS NOT NULL").fetchone()[0] == 0

    database.record_depth_samples([depth_sampler.snapshot("INFY", KITE_QUOTE, 1790000100.0)])
    database._local.conn.close()
    database._local.conn = None            # a second start on the same journal: idempotent
    conn = database._conn()
    assert [r[1] for r in conn.execute("PRAGMA table_info(depth_samples)")] == cols
    stats = database.depth_sample_stats()
    assert stats["rows"] == 5 and stats["rows_with_levels"] == 1
    new = conn.execute("SELECT bid_qty5, ask_levels_json FROM depth_samples WHERE symbol='INFY'").fetchone()
    assert new["bid_qty5"] == 419 and json.loads(new["ask_levels_json"])[0] == [4085.0, 43, 10]
