"""The paper desk (paper_desk.py, README section 125): the four books' cards
and the unified process log, assembled read-only from a throwaway journal and
hand-written state files. conftest points database.DB_PATH and the momentum
state at a temporary folder; this file does the same for the Jev state and
the momentum job log, then checks that nothing here writes to any of them."""
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import database  # noqa: E402
import jev_book  # noqa: E402
import jev2_book  # noqa: E402
import momentum_book  # noqa: E402
import paper_desk  # noqa: E402

DAY = "2026-10-05"
PREV = "2026-10-01"
IST = paper_desk.IST


def at(day, hhmm, s=0):
    h, m = map(int, hhmm.split(":"))
    d = datetime.date.fromisoformat(day)
    return datetime.datetime(d.year, d.month, d.day, h, m, s, tzinfo=IST).timestamp()


def now_at(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    d = datetime.date.fromisoformat(day)
    return datetime.datetime(d.year, d.month, d.day, h, m, tzinfo=IST)


@pytest.fixture
def files(tmp_path, monkeypatch):
    """Every store the desk reads, pointed at tmp_path: the journal (conftest),
    the Jev state, the momentum state (conftest) and the momentum job log."""
    monkeypatch.setattr(jev_book, "STATE_PATH", str(tmp_path / "jev_book_state.json"))
    monkeypatch.setattr(jev2_book, "STATE_PATH", str(tmp_path / "jev2_book_state.json"))
    monkeypatch.setattr(momentum_book, "LOG_PATH", str(tmp_path / "momentum_book.log"))
    database._conn()                       # creates the throwaway journal's schema
    return tmp_path


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if os.path.exists(path) else None


def seed(files):
    """A day with something from every book."""
    conn = database._conn()
    with conn:
        conn.executemany("INSERT INTO activity (ts, kind, symbol, message, level) VALUES (?,?,?,?,?)", [
            (at(DAY, "09:16"), "scan", None, "Scanned 100 stocks in 18s.", "info"),
            (at(DAY, "09:40"), "setup", "BEL", "Breakdown forming (short)", "info"),
            (at(DAY, "10:05"), "trade", "APOLLOHOSP", "SELL 4 @ 8036.59 (Bearish Marubozu (short))", "trade"),
            (at(DAY, "11:36"), "system", None, "Jev book: asking Jev about today's shortlist", "info"),
            (at(DAY, "19:30"), "system", None, "Momentum book: evening job started", "info"),
            (at(DAY, "19:32"), "momentum", None, "Momentum book (paper): rebalanced at the 5 Oct 2026 close", "info"),
            (at(PREV, "09:16"), "scan", None, "Yesterday's scan", "info"),
        ])
        conn.executemany(
            "INSERT INTO trades (id, position_id, ts, symbol, side, quantity, price, mode, reason, note, realized, "
            "charges, initial_risk, r_multiple) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
                ("e1", "p1", at(DAY, "10:05"), "APOLLOHOSP", "SELL", 4, 8036.59, "paper", "Bearish Marubozu (short)",
                 "stop 8071", 0.0, 20.6, 34.4, None),
                ("x1", "p1", at(DAY, "12:25"), "APOLLOHOSP", "BUY", 4, 8078.92, "paper", "stop_loss", "stop 8071",
                 -203.58, 13.6, 34.4, -1.48),
                ("e0", "p0", at(PREV, "10:05"), "ADANIPOWER", "SELL", 98, 200.2, "paper", "signal", "", 0.0, 12.6, 1.0, None),
                ("x0", "p0", at(PREV, "10:07"), "ADANIPOWER", "BUY", 98, 199.9, "paper", "take_profit", "", 8.56, 8.26, 1.0, 0.14),
            ])
        conn.execute("INSERT INTO rule_lab_sessions (session_date, symbols, bars, feed, first_ts, last_ts) "
                     "VALUES (?,?,?,?,?,?)", (DAY, 25, 20, "kite", at(DAY, "09:20", 18), at(DAY, "10:55")))
        rows = []
        for rule, sym, side in [("R01", "BEL", "LONG"), ("R02", "BEL", "SHORT"), ("Y13L", "ADANIPORTS", "LONG")]:
            rows.append((rule, sym, DAY, side, f"{DAY}T09:20:00+05:30", f"{DAY}T09:25:00+05:30", 100.0, 10,
                         None, None, f"{DAY}T09:55:00+05:30", 101.0 if side == "LONG" else 99.5, "time",
                         90.0, 73.4, 73.4 if side == "LONG" else 40.0, None, "closed", "kite",
                         at(DAY, "09:25", 31), at(DAY, "09:55", 12)))
        rows.append(("R03", "INFY", DAY, "LONG", f"{DAY}T10:20:00+05:30", f"{DAY}T10:25:00+05:30", 50.0, 20,
                     None, None, None, None, None, None, None, None, None, "open", "kite", at(DAY, "10:25", 9), None))
        conn.executemany(
            "INSERT INTO rule_lab_trades (rule, symbol, session_date, side, signal_time, entry_time, entry_price, qty, "
            "stop_price, target_price, exit_time, exit_price, exit_reason, gross_bp, net_bp, net_rs, net_r, status, "
            "feed, opened_ts, closed_ts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    jev = {"status": "active", "status_reason": None, "days": {
        PREV: {"status": "closed", "closed": True, "decisions": [
            {"symbol": "ZYDUSLIFE", "action": "buy", "p_up": 0.57, "size_level": 2, "scanner_side": "LONG",
             "entry": 1219.1, "exit": 1212.7, "move_bp": -52.5, "net_bp": -66.8, "scanner_net_bp": -66.8,
             "asked_at": f"{PREV}T09:45:24", "exit_at": f"{PREV}T15:08:18"}]},
        DAY: {"status": "open", "decisions": [
            {"symbol": "PFC", "action": "short", "p_up": 0.17, "size_level": 2, "scanner_side": "SHORT",
             "entry": 332.55, "asked_at": f"{DAY}T09:45:25"},
            {"symbol": "INFY", "action": "skip", "p_up": 0.5, "size_level": 0, "scanner_side": "LONG",
             "entry": 1500.0, "asked_at": f"{DAY}T09:45:26"}]},
    }}
    Path(jev_book.STATE_PATH).write_text(json.dumps(jev))
    mom = momentum_book.new_state(1_000_000.0, "2026-09-26")
    mom.update(status="active", last_processed=DAY, latest_session=DAY, rebalances=1,
               nav=[{"date": DAY, "book": 998312.59, "bench": 998312.59}],
               month_points=[{"date": DAY, "book": 998312.594, "bench": 998312.594}],
               trades=[{"date": DAY, "side": "BUY", "symbol": "APARINDS", "value": 66666.67, "cost": 112.49},
                       {"date": DAY, "side": "BUY", "symbol": "RADICO", "value": 66666.67, "cost": 112.49}])
    mom["book"]["positions"] = {"APARINDS": {"symbol": "APARINDS", "fill_date": DAY, "amount": 66666.67, "fill_price": 10.0}}
    mom["book"]["cash"] = 1_000_000.0 - 66666.67
    Path(momentum_book.STATE_PATH).write_text(json.dumps(mom))
    Path(momentum_book.LOG_PATH).write_text(f"{PREV}T19:31:42 daily done code=0 in 97s\n"
                                            f"{DAY}T19:31:50 daily done code=0 in 93s\n"
                                            f"{DAY}T20:02:01 daily done code=4 in 12s\n")


# --- the process log ----------------------------------------------------------------------------

def test_log_merges_every_book_newest_first_and_tags_each_line(files):
    seed(files)
    log = paper_desk.process_log(DAY)
    books = {ln["book"] for ln in log["items"]}
    assert books == {"intraday", "jev", "rule_lab", "momentum"}      # no Jev 2 state seeded: no jev2 lines
    ts = [ln["ts"] for ln in log["items"]]
    assert ts == sorted(ts, reverse=True)
    for ln in log["items"]:
        assert ln["book"] in paper_desk.BOOKS and ln["kind"] and ln["time"].count(":") == 2
    assert log["counts"]["intraday"] >= 3 and log["counts"]["jev"] >= 3
    assert log["counts"]["rule_lab"] == 4 and log["counts"]["momentum"] >= 5   # session, 2 entry bars, 1 exit bar
    assert log["books"] == ["intraday", "jev", "rule_lab", "momentum"] and log["counts"]["jev2"] == 0


def test_log_is_scoped_to_the_ist_day(files):
    seed(files)
    today = paper_desk.process_log(DAY)
    assert not any("Yesterday" in ln["message"] for ln in today["items"])
    prev = paper_desk.process_log(PREV)
    assert any("Yesterday" in ln["message"] for ln in prev["items"])
    assert any(ln["book"] == "jev" and ln["kind"] == "trade" and ln["symbol"] == "ZYDUSLIFE" for ln in prev["items"])
    assert not any(ln["book"] == "rule_lab" for ln in prev["items"])
    # the previous evening's job run belongs to its own day, not today's
    assert sum(1 for ln in prev["items"] if ln["kind"] == "job") == 1


def test_engine_trades_carry_money_and_are_not_doubled(files):
    seed(files)
    items = paper_desk.process_log(DAY, book="intraday")["items"]
    trades = [ln for ln in items if ln["kind"] == "trade"]
    assert len(trades) == 2                               # the entry and the exit, from the trades table
    exit_line = next(ln for ln in trades if ln["money"] is not None)
    assert exit_line["money"] == -203.58 and "stop hit" in exit_line["message"] and "-1.48R" in exit_line["message"]
    entry_line = next(ln for ln in trades if ln["money"] is None)
    assert entry_line["message"].startswith("Sold 4 @ 8,036.59")
    assert all(ln["book"] == "intraday" for ln in items)
    assert not any(ln["message"].startswith("Jev book:") or ln["message"].startswith("Momentum book:") for ln in items)


def test_jev_round_decisions_and_scored_trades(files):
    seed(files)
    items = paper_desk.process_log(DAY, book="jev")["items"]
    kinds = [ln["kind"] for ln in items]
    assert "round" in kinds and kinds.count("decision") == 2
    pfc = next(ln for ln in items if ln["kind"] == "decision" and ln["symbol"] == "PFC")
    assert "Jev says short" in pfc["message"] and "P(up) 0.17" in pfc["message"] and "332.55" in pfc["message"]
    assert not any(ln["kind"] == "trade" for ln in items)     # today's round is still open: nothing scored
    # the engine's own "Jev book:" system line is re-tagged to this book
    assert any(ln["message"].startswith("Jev book:") for ln in items)
    prev = paper_desk.process_log(PREV, book="jev")["items"]
    scored = next(ln for ln in prev if ln["kind"] == "trade")
    assert scored["symbol"] == "ZYDUSLIFE" and scored["money"] == pytest.approx(-66.8 / 1e4 * 100_000, abs=0.01)
    assert any(ln["kind"] == "round" and "Round closed" in ln["message"] for ln in prev)


def test_jev_skipped_day_is_one_warning_line(files):
    seed(files)
    state = json.loads(Path(jev_book.STATE_PATH).read_text())
    state["days"][DAY] = {"status": "no_live_prices", "error": "Kite had no live session", "decisions": []}
    Path(jev_book.STATE_PATH).write_text(json.dumps(state))
    items = paper_desk.process_log(DAY, book="jev")["items"]
    skipped = [ln for ln in items if "Round skipped" in ln["message"]]
    assert len(skipped) == 1 and skipped[0]["level"] == "warn" and skipped[0]["time"] == "09:45:00"


def test_rule_lab_trades_are_grouped_by_bar_with_details(files):
    seed(files)
    items = paper_desk.process_log(DAY, book="rule_lab")["items"]
    assert sorted(ln["kind"] for ln in items) == ["lab_entry", "lab_entry", "lab_exit", "session"]
    exit_line = next(ln for ln in items if ln["kind"] == "lab_exit")
    assert "Closed 3 paper trades at the 09:55 bar" in exit_line["message"]
    assert exit_line["money"] == pytest.approx(73.4 + 40.0 + 73.4, abs=0.01)
    assert len(exit_line["details"]) == 3 and {d["rule"] for d in exit_line["details"]} == {"R01", "R02", "Y13L"}
    opened = [ln for ln in items if ln["kind"] == "lab_entry"]
    first = next(ln for ln in opened if "09:25 bar" in ln["message"])
    assert "Opened 3 paper trades" in first["message"] and "2 long, 1 short" in first["message"]
    later = next(ln for ln in opened if "10:25 bar" in ln["message"])
    assert later["symbol"] == "INFY" and later["details"][0]["rule"] == "R03"


def test_momentum_job_runs_trades_rebalance_and_alert(files):
    seed(files)
    items = paper_desk.process_log(DAY, book="momentum")["items"]
    kinds = [ln["kind"] for ln in items]
    assert kinds.count("job") == 3                        # started (activity) + two finished runs (job log)
    assert kinds.count("trade") == 2 and kinds.count("rebalance") == 1 and kinds.count("alert") == 1
    bad = next(ln for ln in items if "exit 4" in ln["message"])
    assert bad["level"] == "warn" and "stopped early" in bad["message"]
    buy = next(ln for ln in items if ln["kind"] == "trade" and ln["symbol"] == "APARINDS")
    assert buy["money"] == -112.49 and "₹66,667" in buy["message"]
    assert all(ln["book"] == "momentum" for ln in items)


def test_filters_and_limit(files):
    seed(files)
    assert all(ln["kind"] == "scan" for ln in paper_desk.process_log(DAY, kind="scan")["items"])
    both = paper_desk.process_log(DAY, book="momentum", kind="trade")
    assert both["total"] == 2 and len(both["items"]) == 2
    capped = paper_desk.process_log(DAY, limit=2)
    assert len(capped["items"]) == 2 and capped["truncated"] and capped["total"] > 2
    with pytest.raises(ValueError):
        paper_desk.process_log("not-a-day")


def test_log_survives_missing_files_and_an_empty_journal(files):
    log = paper_desk.process_log(DAY)
    assert log["items"] == [] and log["total"] == 0 and log["counts"] == {b: 0 for b in paper_desk.BOOKS}
    Path(jev_book.STATE_PATH).write_text("{not json")
    Path(momentum_book.STATE_PATH).write_text("{not json")
    assert paper_desk.process_log(DAY)["items"] == []


# --- the cards -----------------------------------------------------------------------------------

def test_cards_one_per_book_equal_shape_none_called_the_strategy(files):
    seed(files)
    out = paper_desk.cards(now=now_at(DAY, "10:30"), engine={"market_status": "open", "paper_mode": True,
                                                            "entries_paused": False, "open_positions": 1,
                                                            "unrealized_pnl": -40.0})
    assert [b["id"] for b in out["books"]] == list(paper_desk.BOOKS)
    for b in out["books"]:
        for key in ("name", "about", "page", "status", "today", "record", "next", "gate"):
            assert key in b, key
        assert b["status"]["state"] in ("running", "waiting", "skipped", "off")
        assert b["record"]["headline"]["value"]
        assert "strategy" not in b["about"].lower() and "strategy" not in b["name"].lower()
    assert "strategy" in out["note"].lower() and "none is the strategy" in out["note"].lower()


def test_intraday_card_today_and_record(files):
    seed(files)
    card = paper_desk.cards(now=now_at(DAY, "12:30"), engine={"market_status": "open", "paper_mode": True,
                                                             "open_positions": 0})["books"][0]
    assert card["status"]["state"] == "running"
    assert card["today"] == {"trades": 1, "entries": 1, "net": -203.58, "open": 0, "unrealized": None}
    assert card["record"]["trades"] == 2 and card["record"]["net"] == pytest.approx(-203.58 + 8.56, abs=0.01)
    assert card["next"]["label"] == "Square-off" and "15:08" in card["next"]["text"]
    paused = paper_desk.cards(now=now_at(DAY, "12:30"), engine={"market_status": "open", "entries_paused": True})["books"][0]
    assert paused["status"]["label"] == "Entries paused"
    weekend = paper_desk.cards(now=now_at("2026-10-04", "12:30"), engine={"market_status": "closed"})["books"][0]
    assert weekend["status"]["label"] == "Market closed" and weekend["next"]["text"].startswith("Mon 5 Oct")


def test_jev_card_states(files, monkeypatch):
    seed(files)
    monkeypatch.setattr(jev_book, "api_key", lambda: "k")
    open_round = paper_desk.cards(now=now_at(DAY, "10:30"))["books"][1]
    assert open_round["status"]["state"] == "running" and "1 paper position" in open_round["status"]["detail"]
    assert open_round["today"]["trades"] == 1 and open_round["today"]["skips"] == 1
    assert open_round["record"]["trades"] == 1 and open_round["record"]["headline"]["value"] == "−66.8 bp".replace("−", "-")
    state = json.loads(Path(jev_book.STATE_PATH).read_text())
    state["days"][DAY] = {"status": "no_live_prices", "error": "Kite had no live session", "decisions": []}
    Path(jev_book.STATE_PATH).write_text(json.dumps(state))
    skipped = paper_desk.cards(now=now_at(DAY, "10:30"))["books"][1]
    assert skipped["status"]["state"] == "skipped" and "no live prices" in skipped["status"]["label"]
    assert skipped["next"]["label"] == "Next round" and skipped["next"]["text"].startswith("Tue 6 Oct")
    del state["days"][DAY]
    Path(jev_book.STATE_PATH).write_text(json.dumps(state))
    early = paper_desk.cards(now=now_at(DAY, "09:30"))["books"][1]
    assert early["status"]["label"] == "Round at 09:45" and early["next"]["text"].startswith("Mon 5 Oct")
    monkeypatch.setattr(jev_book, "api_key", lambda: None)
    assert paper_desk.cards(now=now_at(DAY, "09:30"))["books"][1]["status"]["label"] == "No TypeSafe key stored"


def test_rule_lab_card(files, monkeypatch):
    seed(files)
    monkeypatch.setattr(paper_desk.time, "time", lambda: at(DAY, "11:00"))
    card = paper_desk.cards(now=now_at(DAY, "11:00"))["books"][3]
    assert card["status"]["state"] == "running" and "25 stocks" in card["status"]["detail"]
    assert card["today"] == {"trades": 3, "opened": 4, "open": 1, "net": pytest.approx(186.8, abs=0.01)}
    assert card["record"]["trades"] == 3 and card["record"]["sessions"] == 1
    assert card["record"]["headline"]["value"].startswith("157 · 0 candidate")
    assert card["next"]["text"] == "after 39 more lab sessions"
    monkeypatch.setattr(paper_desk.time, "time", lambda: at(DAY, "11:00") + 3600)
    assert paper_desk.cards(now=now_at(DAY, "12:00"))["books"][3]["status"]["label"] == "Session recorded"


def test_momentum_card(files):
    seed(files)
    card = paper_desk.cards(now=now_at(DAY, "21:00"))["books"][4]
    assert card["status"]["label"] == "Today's session processed"
    assert card["today"] == {"trades": 2, "net": pytest.approx(-224.98, abs=0.01), "note": "costs and slippage paid"}
    assert card["record"]["rebalances"] == 1 and card["record"]["headline"]["value"] == "no month complete yet"
    assert card["next"]["label"] == "Next rebalance" and card["next"]["text"].endswith("close")
    os.remove(momentum_book.STATE_PATH)
    fresh = paper_desk.cards(now=now_at(DAY, "21:00"))["books"][4]
    assert fresh["status"]["label"] == "Not started"


def test_desk_reads_only(files):
    seed(files)
    before = {p: _digest(p) for p in (jev_book.STATE_PATH, momentum_book.STATE_PATH, momentum_book.LOG_PATH)}
    conn = database._conn()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("activity", "trades", "rule_lab_trades", "rule_lab_sessions")}
    paper_desk.cards(now=now_at(DAY, "12:00"), engine={"market_status": "open"})
    for d in (DAY, PREV):
        for b in (None,) + paper_desk.BOOKS:
            paper_desk.process_log(d, book=b)
    assert {p: _digest(p) for p in before} == before
    assert counts == {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in counts}
