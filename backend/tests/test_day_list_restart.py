"""The day's list survives a restart (#198).

The list was held in memory only, so a backend restart lost it and the
first scan after the restart chose it again. On 2026-09-29 that put
HINDALCO in place of TVSMOTOR. The list is now written to the journal when
it is fixed and read back when the scanner is built. A list already fixed
for the session is used as it is, with the time it was first fixed; a list
for an earlier session is not."""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database  # noqa: E402
import scanner  # noqa: E402
import trading_engine  # noqa: E402
from state import AppState, _new_position  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
CFG = {"active_count": 3, "selection": "liquidity", "freeze_min_coverage": 0.9}


def _row(sym, turnover):
    return {"symbol": sym, "turnover_cr": turnover, "score": 50.0, "final_score": 50.0, "side": "LONG",
            "daily_trend": "up", "excluded": None}


# D trades far more than the listed three: choosing again would take it
ROWS = [_row("A", 1), _row("B", 2), _row("C", 3), _row("D", 9000)]


# --- the scanner -------------------------------------------------------------------------------

def test_fixing_the_list_before_the_open_writes_it_to_the_journal():
    scanner.Scanner(CFG).fix_day_list("2026-09-29", ["A", "B", "C"], now=1000.0)
    assert database.get_day_list("2026-09-29") == {
        "session": "2026-09-29", "symbols": ["A", "B", "C"], "fixed_ts": 1000.0, "when": "before the open",
        "mode": "liquidity"}


def test_fixing_the_list_at_the_first_scan_writes_it_too():
    rows = [_row("A", 900), _row("B", 800), _row("C", 700), _row("D", 600)]
    scanner.Scanner(CFG).day_list_for("2026-09-29", rows, n_rows=100, n_universe=100, now=2000.0)
    stored = database.get_day_list("2026-09-29")
    assert stored["symbols"] == ["A", "B", "C"] and stored["fixed_ts"] == 2000.0
    assert stored["when"] == "at the first scan of the session"


def test_a_list_not_yet_fixed_is_not_written():
    thin = [_row("A", 900), _row("C", 700)]
    scanner.Scanner(CFG).day_list_for("2026-09-29", thin, n_rows=50, n_universe=100)
    assert database.get_day_list("2026-09-29") is None


def test_a_restarted_scanner_keeps_the_list_and_the_time_it_was_fixed():
    scanner.Scanner(CFG).fix_day_list("2026-09-29", ["A", "B", "C"], now=1000.0)
    restarted = scanner.Scanner(CFG)                         # a new process on the same journal
    assert restarted.list_fixed_for("2026-09-29")
    active, fixed = restarted.day_list_for("2026-09-29", ROWS, n_rows=100, n_universe=100, now=5000.0)
    assert active == ["A", "B", "C"] and fixed
    assert restarted.day_list["fixed_ts"] == 1000.0 and restarted.day_list["when"] == "before the open"
    assert not restarted.fix_day_list("2026-09-29", ["X", "Y", "Z"], now=6000.0)
    assert database.get_day_list("2026-09-29")["symbols"] == ["A", "B", "C"]


def test_a_list_fixed_at_the_first_scan_is_kept_across_a_restart_too():
    rows = [_row("A", 900), _row("B", 800), _row("C", 700), _row("D", 600)]
    scanner.Scanner(CFG).day_list_for("2026-09-29", rows, n_rows=100, n_universe=100, now=2000.0)
    restarted = scanner.Scanner(CFG)
    active, fixed = restarted.day_list_for("2026-09-29", ROWS, n_rows=100, n_universe=100, now=5000.0)
    assert active == ["A", "B", "C"] and fixed
    assert restarted.day_list["fixed_ts"] == 2000.0
    assert restarted.day_list["when"] == "at the first scan of the session"


def test_a_restart_before_the_open_keeps_todays_list_while_scans_read_yesterdays_bars():
    scanner.Scanner(CFG).fix_day_list("2026-09-29", ["A", "B", "C"], now=1000.0)
    restarted = scanner.Scanner(CFG)
    active, fixed = restarted.day_list_for("2026-09-28", ROWS, n_rows=100, n_universe=100, now=5000.0)
    assert active == ["A", "B", "C"] and fixed and restarted.day_list["session"] == "2026-09-29"


def test_a_list_for_an_earlier_session_is_not_reused():
    scanner.Scanner(CFG).fix_day_list("2026-09-28", ["A", "B", "C"], now=1000.0)
    restarted = scanner.Scanner(CFG)
    assert not restarted.list_fixed_for("2026-09-29")
    active, fixed = restarted.day_list_for("2026-09-29", ROWS, n_rows=100, n_universe=100, now=5000.0)
    assert active == ["D", "C", "B"] and fixed
    assert restarted.day_list["session"] == "2026-09-29" and restarted.day_list["fixed_ts"] == 5000.0
    assert database.get_day_list("2026-09-28")["symbols"] == ["A", "B", "C"]      # the old row is left alone
    assert database.get_day_list("2026-09-29")["symbols"] == ["D", "C", "B"]


def test_the_first_list_written_for_a_session_stands():
    database.record_day_list("2026-09-29", ["A", "B", "C"], 1000.0, "before the open")
    stored = database.record_day_list("2026-09-29", ["X", "Y", "Z"], 2000.0, "at the first scan of the session")
    assert stored["symbols"] == ["A", "B", "C"] and stored["fixed_ts"] == 1000.0


def test_score_mode_reads_nothing_back():
    scanner.Scanner(CFG).fix_day_list("2026-09-29", ["A", "B", "C"], now=1000.0)
    assert scanner.Scanner({**CFG, "selection": "score"}).day_list is None


def test_a_journal_that_cannot_be_written_still_leaves_the_list_fixed_in_memory(monkeypatch):
    def fail(*a, **k):
        raise RuntimeError("disk full")
    monkeypatch.setattr(database, "record_day_list", fail)
    sc = scanner.Scanner(CFG)
    assert sc.fix_day_list("2026-09-29", ["A", "B", "C"], now=1000.0)
    active, fixed = sc.day_list_for("2026-09-29", ROWS, n_rows=100, n_universe=100)
    assert active == ["A", "B", "C"] and fixed


def test_a_journal_that_cannot_be_read_starts_with_no_list(monkeypatch):
    def fail(*a, **k):
        raise RuntimeError("locked")
    monkeypatch.setattr(database, "latest_day_list", fail)
    assert scanner.Scanner(CFG).day_list is None


# --- the engine ----------------------------------------------------------------------------------

def _engine(monkeypatch):
    monkeypatch.setattr(config, "SCANNER", {**config.SCANNER, "enabled": True, "selection": "liquidity",
                                            "fix_list_from": "08:45", "pinned": []})
    return trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))


def _today():
    return datetime.now(IST).date().isoformat()


def test_the_engines_pre_open_fix_is_written_and_a_restarted_engine_watches_it(monkeypatch):
    engine = _engine(monkeypatch)
    result = {"watchlist": ["RELIANCE", "HDFCBANK", "ICICIBANK"], "market": {"bias": "neutral"}}
    monkeypatch.setattr(trading_engine, "run_premarket", lambda cfg: result)
    engine._run_premarket_scan(fix_list_for=_today())
    stored = database.get_day_list(_today())
    assert stored["symbols"] == ["RELIANCE", "HDFCBANK", "ICICIBANK"] and stored["when"] == "before the open"

    # The restart. The order-book sampler reads state.watchlist on every open-phase
    # tick, so the list is watched from the first tick, not from the first scan.
    restarted = _engine(monkeypatch)
    assert restarted.scanner.list_fixed_for(_today())
    assert restarted.scanner.day_list["fixed_ts"] == stored["fixed_ts"]
    assert list(restarted.state.watchlist) == ["RELIANCE", "HDFCBANK", "ICICIBANK"]
    assert any("read back from the journal after a restart" in a["message"] for a in restarted.state.activity)

    # The ordinary pre-market read after the restart chooses again from newer data;
    # it neither seeds the watchlist nor moves the list.
    moved = {"watchlist": ["RELIANCE", "HDFCBANK", "HINDALCO"], "market": {"bias": "neutral"}}
    monkeypatch.setattr(trading_engine, "run_premarket", lambda cfg: moved)
    restarted._run_premarket_scan()
    assert list(restarted.state.watchlist) == ["RELIANCE", "HDFCBANK", "ICICIBANK"]
    restarted._run_premarket_scan(fix_list_for=_today())
    assert restarted.scanner.day_list["symbols"] == ["RELIANCE", "HDFCBANK", "ICICIBANK"]
    assert database.get_day_list(_today())["symbols"] == ["RELIANCE", "HDFCBANK", "ICICIBANK"]


def test_a_restarted_engine_keeps_a_held_stock_in_the_watchlist(monkeypatch):
    database.record_day_list(_today(), ["RELIANCE", "HDFCBANK"], 1000.0, "before the open")
    monkeypatch.setattr(config, "SCANNER", {**config.SCANNER, "enabled": True, "selection": "liquidity",
                                            "pinned": []})
    state = AppState(watchlist=[], paper_mode=True)
    state.positions["TVSMOTOR"] = {**_new_position(), "quantity": 5, "avg_price": 100.0}
    engine = trading_engine.TradingEngine(state)
    assert list(engine.state.watchlist) == ["RELIANCE", "HDFCBANK", "TVSMOTOR"]


def test_a_list_from_an_earlier_day_does_not_seed_the_watchlist(monkeypatch):
    database.record_day_list("2026-09-28", ["RELIANCE", "HDFCBANK"], 1000.0, "before the open")
    engine = _engine(monkeypatch)
    assert list(engine.state.watchlist) == []
