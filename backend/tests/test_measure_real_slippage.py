import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from research import measure_real_slippage as m


def test_spread_and_crossing_cost():
    # bid 99.9 / ask 100.1: mid 100, half-spread 0.1/100 = 10 bp
    r = m.measure(99.9, 100.1, 500, 500, 2000, 2000, "long", 100, 100.0, 0.05)
    assert r["half_spread_bp"] == pytest.approx(10.0)
    assert r["cross_bp"] == pytest.approx(10.0)            # buy at 100.1 against a 100.0 signal
    assert r["fill"] == "level1" and r["impact_bp"] == pytest.approx(10.0)
    s = m.measure(99.9, 100.1, 500, 500, 2000, 2000, "short", 100, 100.1, 0.05)
    assert s["cross_bp"] == pytest.approx((100.1 - 99.9) / 100.1 * 1e4)   # sell at the bid, 19.98 bp


def test_book_walk_on_the_modelled_ladder():
    # ask 100.1 x 100, five levels hold 500 -> levels 2-5 hold 100 each at 100.15, 100.20, ...
    # buy 250: 100 @ 100.10 + 100 @ 100.15 + 50 @ 100.20 = 25035 -> vwap 100.14 -> 14 bp from mid 100
    r = m.measure(99.9, 100.1, 100, 100, 500, 500, "long", 250, 100.0, 0.05)
    assert r["fill"] == "ladder" and r["impact_bp"] == pytest.approx(14.0)
    assert m.walk([(100.1, 100), (100.15, 100), (100.2, 100)], 250) == pytest.approx(100.14)


def test_insufficient_depth_is_counted_not_extrapolated():
    r = m.measure(99.9, 100.1, 100, 100, 500, 500, "long", 501, 100.0, 0.05)
    assert r["fill"] == "insufficient" and r["impact_bp"] is None
    assert m.walk([(100.1, 100)], 101) is None


def _db(path, evals, samples):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE depth_samples (ts REAL, symbol TEXT, ltp REAL, bid REAL, ask REAL, spread_bp REAL,"
                " bid_qty1 INTEGER, ask_qty1 INTEGER, bid_qty5 INTEGER, ask_qty5 INTEGER)")
    con.execute("CREATE TABLE checklist_evals (id INTEGER PRIMARY KEY, ts REAL, symbol TEXT, ltp REAL,"
                " checklist_json TEXT, bar_time TEXT)")
    con.executemany("INSERT INTO depth_samples VALUES (?,?,?,?,?,NULL,?,?,?,?)", samples)
    con.executemany("INSERT INTO checklist_evals (ts, symbol, ltp, checklist_json, bar_time) VALUES (?,?,?,?,?)", evals)
    con.commit()
    con.close()


def _passing(side):
    ok = {"side": side, "items": [{"key": "pattern", "ok": True, "required": True}]}
    blocked = {"side": "x", "items": [{"key": "pattern", "ok": False, "required": True},
                                      {"key": "sr", "ok": False, "required": True}]}
    return json.dumps({"long": ok if side == "long" else blocked, "short": ok if side == "short" else blocked})


def test_max_gap_drops_a_signal_with_no_nearby_sample(tmp_path, capsys):
    T = 1790000000.0
    db = str(tmp_path / "j.db")
    samples = [(T + 10, s, 100.0, 99.9, 100.1, 500, 500, 2000, 2000) for s in ("AAA", "BBB", "CCC")]
    evals = [(T, "AAA", 100.0, _passing("long"), "b1"),          # sample 10s later: matched
             (T + 1, "AAA", 100.0, _passing("long"), "b1"),      # same bar: not a second signal
             (T - 100, "BBB", 100.0, _passing("short"), "b0"),   # sample 110s later: dropped
             (T, "ZZZ", 100.0, _passing("long"), "b1")]          # no samples for the symbol
    _db(db, evals, samples)
    out = m.main(["--db", db, "--max-gap", "60", "--notional", "10000"])
    assert out["dropped_gap"] == 1 and len(out["matched"]) == 1
    assert out["matched"][0]["half_spread_bp"] == pytest.approx(10.0)
    assert out["too_thin"]
    assert "TOO LITTLE DATA" in capsys.readouterr().out


def test_empty_tables_exit_cleanly(tmp_path):
    db = str(tmp_path / "e.db")
    _db(db, [], [])
    with pytest.raises(SystemExit) as e:
        m.main(["--db", db])
    assert "Too little data" in str(e.value)
