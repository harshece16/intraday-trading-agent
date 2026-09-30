"""#135 / #136 regression tests: the research loader's held-out guard and
as-printed price floor, and the Scorecard's trial count of record."""
import csv
import io
import os
import sys
import zipfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "research"))

import evaluation  # noqa: E402
import slow_momentum as sm  # noqa: E402


def _bhav(path, date_dd_mmm_yyyy, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE",
                "TOTTRDQTY", "TOTTRDVAL", "TIMESTAMP", "TOTALTRADES", "ISIN"])
    for sym, close, prev in rows:
        w.writerow([sym, "EQ", close, close, close, close, close, prev, 1000, close * 1000,
                    date_dd_mmm_yyyy, 10, ""])
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("bhav.csv", buf.getvalue())


def test_loader_drops_held_out_sessions_unless_asked(tmp_path, monkeypatch):
    d = tmp_path / "bhav"
    d.mkdir()
    (d / "symbolchange.csv").write_text("SM_NAME,SM_KEY_SYMBOL,SM_NEW_SYMBOL,SM_APPLICABLE_FROM\n")
    _bhav(d / "31DEC2025.zip", "31-DEC-2025", [("AAA", 100, 99)])
    _bhav(d / "02JAN2026.zip", "02-JAN-2026", [("AAA", 101, 100)])
    monkeypatch.setattr(sm, "CACHE", str(tmp_path / "parsed.pkl"))
    monkeypatch.setattr(sm, "HELD_OUT_DIR", str(tmp_path / "none"))
    sessions, chains, _ = sm.load_all(data_dir=str(d), refresh=True)
    assert sessions == ["2025-12-31"]
    sessions2, _, _ = sm.load_all(data_dir=str(d), refresh=True, include_held_out=True)
    assert sessions2 == ["2025-12-31", "2026-01-02"]


def test_price_floor_uses_the_price_as_printed_not_split_adjusted():
    # 300 sessions at Rs 200 as printed; a later 1:10 split adjusted them to Rs 20 - 0.01
    n = 300
    chain = {"idx": list(range(n)), "close": [19.99] * n, "raw": [200.0] * n, "val": [1e7] * n}
    assert sm.universe_at({"AAA": chain}, n - 1) == ["AAA"]
    cheap = {"idx": list(range(n)), "close": [19.0] * n, "raw": [19.0] * n, "val": [1e7] * n}
    assert sm.universe_at({"BBB": cheap}, n - 1) == []


def test_dp_charge_is_zerodhas_gst_inclusive_figure():
    assert sm.DP_PER_SELL == pytest.approx(15.34)


def test_trial_count_uses_the_ledger_of_record(tmp_path, monkeypatch):
    ledger = tmp_path / "trials.md"
    ledger.write_text("| # | What |\n| --- | --- |\n| 1 | a |\n| 118 | b |\n| 119 | c |\n| R1 | replication |\n")
    monkeypatch.setattr(evaluation, "TRIALS_LEDGER_PATH", ledger)
    log = tmp_path / "log.json"
    log.write_text("[1, 2, 3]")
    monkeypatch.setattr(evaluation, "TRIAL_LOG_PATH", log)
    assert evaluation.trials_of_record() == 119
    assert evaluation.trial_count() == 119
    log.write_text("[" + ",".join(["1"] * 150) + "]")
    assert evaluation.trial_count() == 150


def test_trial_count_without_ledger_falls_back_to_log(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluation, "TRIALS_LEDGER_PATH", tmp_path / "missing.md")
    monkeypatch.setattr(evaluation, "TRIAL_LOG_PATH", tmp_path / "missing.json")
    assert evaluation.trial_count() == 0
