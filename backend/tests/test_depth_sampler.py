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
