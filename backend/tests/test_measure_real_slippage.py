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


# ---- recorded levels (#188) --------------------------------------------------

ASKS = [(100.1, 100), (100.2, 100), (100.5, 300)]        # a book with a gap: 100.2 -> 100.5
BIDS = [(99.9, 100), (99.7, 200), (99.6, 200)]


def test_an_order_past_level_1_walks_the_recorded_levels_not_the_ladder():
    # buy 250: 100 @ 100.1 + 100 @ 100.2 + 50 @ 100.5 = 25055 -> vwap 100.22 -> 22 bp from mid 100.
    # The one-tick ladder on the same summary columns says 14 bp: the gap is what it cannot see.
    r = m.measure(99.9, 100.1, 100, 100, 500, 500, "long", 250, 100.0, 0.05, levels=ASKS)
    assert r["fill"] == "recorded" and r["impact_bp"] == pytest.approx(22.0)
    assert m.measure(99.9, 100.1, 100, 100, 500, 500, "long", 250, 100.0, 0.05)["impact_bp"] == pytest.approx(14.0)
    # sell 300 on the bids: 100 @ 99.9 + 200 @ 99.7 = 29930 -> vwap 99.7667 -> 23.33 bp
    s = m.measure(99.9, 100.1, 100, 100, 500, 500, "short", 300, 100.0, 0.05, levels=BIDS)
    assert s["fill"] == "recorded" and s["impact_bp"] == pytest.approx((100 - 29930 / 300) / 100 * 1e4)


def test_recorded_levels_leave_level_1_and_insufficient_as_they_were():
    r = m.measure(99.9, 100.1, 100, 100, 500, 500, "long", 80, 100.0, 0.05, levels=ASKS)
    assert r["fill"] == "level1" and r["impact_bp"] == pytest.approx(10.0)
    r = m.measure(99.9, 100.1, 100, 100, 500, 500, "long", 501, 100.0, 0.05, levels=ASKS)
    assert r["fill"] == "insufficient" and r["impact_bp"] is None


def test_parse_levels_reads_the_stored_json_and_tolerates_old_rows():
    assert m.parse_levels("[[100.1,100,3],[100.2,100,null],[0,0,0]]") == [(100.1, 100.0), (100.2, 100.0)]
    assert m.parse_levels(None) is None                  # a row from before #188
    assert m.parse_levels("not json") is None
    assert m.parse_levels("[]") is None


def _db_with_levels(path, evals, samples):
    """samples: (ts, symbol, ltp, bid, ask, bq1, aq1, bq5, aq5, bid_levels_json, ask_levels_json)."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE depth_samples (ts REAL, symbol TEXT, ltp REAL, bid REAL, ask REAL, spread_bp REAL,"
                " bid_qty1 INTEGER, ask_qty1 INTEGER, bid_qty5 INTEGER, ask_qty5 INTEGER,"
                " bid_levels_json TEXT, ask_levels_json TEXT)")
    con.execute("CREATE TABLE checklist_evals (id INTEGER PRIMARY KEY, ts REAL, symbol TEXT, ltp REAL,"
                " checklist_json TEXT, bar_time TEXT)")
    con.executemany("INSERT INTO depth_samples VALUES (?,?,?,?,?,NULL,?,?,?,?,?,?)", samples)
    con.executemany("INSERT INTO checklist_evals (ts, symbol, ltp, checklist_json, bar_time) VALUES (?,?,?,?,?)", evals)
    con.commit()
    con.close()


def test_main_uses_recorded_levels_where_a_row_has_them_and_says_so(tmp_path, capsys):
    T = 1790000000.0
    db = str(tmp_path / "j.db")
    lv = lambda levels: json.dumps([[p, q, 1] for p, q in levels])
    samples = [(T + 10, "AAA", 100.0, 99.9, 100.1, 100, 100, 500, 500, lv(BIDS), lv(ASKS)),   # since #188
               (T + 10, "BBB", 100.0, 99.9, 100.1, 100, 100, 500, 500, None, None),           # before #188
               (T + 10, "CCC", 100.0, 99.9, 100.1, 100, 100, 500, 500, None, None)]
    evals = [(T, "AAA", 100.0, _passing("long"), "b1"), (T, "BBB", 100.0, _passing("long"), "b1")]
    _db_with_levels(db, evals, samples)
    out = m.main(["--db", db, "--notional", "25000"])       # 25000 / mid 100 = 250 shares
    got = {r["symbol"]: r for r in out["matched"]}
    assert got["AAA"]["fill"] == "recorded" and got["AAA"]["impact_bp"] == pytest.approx(22.0)
    # the ladder's tick is the symbol's smallest spread seen, 0.20 here:
    # 100 @ 100.1 + 100 @ 100.3 + 50 @ 100.5 -> vwap 100.26 -> 26 bp
    assert got["BBB"]["fill"] == "ladder" and got["BBB"]["impact_bp"] == pytest.approx(26.0)
    assert (out["book_samples"], out["book_samples_with_levels"]) == (3, 1)
    assert out["all_samples"]["ALL"]["fills"] == {"recorded": 2, "ladder": 4}
    text = capsys.readouterr().out
    assert "Samples with the book recorded level by level (#188): 1 of 3" in text
    assert "walked recorded levels=1 modelled ladder=1" in text
    assert "2 of 3 book samples predate #188" in text


def test_an_old_journal_without_the_level_columns_still_measures_on_the_ladder(tmp_path, capsys):
    T = 1790000000.0
    db = str(tmp_path / "old.db")
    _db(db, [(T, "AAA", 100.0, _passing("long"), "b1")],
        [(T + 10, s, 100.0, 99.9, 100.1, 100, 100, 500, 500) for s in ("AAA", "BBB", "CCC")])
    out = m.main(["--db", db, "--notional", "25000"])
    assert out["matched"][0]["fill"] == "ladder" and out["book_samples_with_levels"] == 0
    assert "Samples with the book recorded level by level (#188): 0 of 3" in capsys.readouterr().out
