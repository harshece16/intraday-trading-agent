"""A restart restores today's open positions (current mode) from the
journal, so stops, targets and the square-off keep watching them. Found
2026-09-25: a deploy restart orphaned two manually approved paper shorts."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import database
import trading_engine
from state import AppState


def _leg(pid, symbol, side, qty, price, mode="paper", note=None, realized=0.0, charges=10.0, ago=60):
    # realized defaults to 0.0: that is what the engine journals on an entry leg
    # (the first version of this test used None, and passed on data the engine never writes)
    database.record_trade({"id": f"{pid}-{side}-{ago}", "position_id": pid, "ts": time.time() - ago,
                           "symbol": symbol, "side": side, "quantity": qty, "price": price, "mode": mode,
                           "reason": "test", "note": note, "realized": realized, "charges": charges})


MANUAL = ('Manually approved — overrode "Reward-to-risk at least 1.5" (Target 3170.36 (next support), '
          'stop 3180.70: -0.31 after costs). Stop 3180.70, target 3170.36, reward-to-risk -0.14 at the entry price.')
CHECKLIST = "Varsity checklist passed on the 11:20 candle: stop 101.00, target 98.00, reward-to-risk 1.57 at the entry price"


def test_an_open_short_is_restored_with_its_stop_target_and_entry_charges():
    _leg("P1", "GRASIM", "SELL", 6, 3172.95, note=MANUAL, charges=12.5)
    s = AppState(watchlist=[], paper_mode=True)
    p = s.positions["GRASIM"]
    assert p["quantity"] == -6 and p["avg_price"] == 3172.95
    assert p["stop_price"] == 3180.70 and p["target_price"] == 3170.36      # the last "Stop X, target Y"
    assert p["position_id"] == "P1" and p["charges"] == 12.5
    assert abs(p["initial_risk"] - 7.75) < 1e-9
    assert s.restored_positions == ["GRASIM"]


def test_a_checklist_long_is_restored_from_its_lowercase_note():
    _leg("P2", "TESTCO", "BUY", 10, 100.0, note=CHECKLIST)
    p = AppState(watchlist=[], paper_mode=True).positions["TESTCO"]
    assert p["quantity"] == 10 and p["stop_price"] == 101.0 and p["target_price"] == 98.0


def test_a_closed_position_is_not_restored():
    _leg("P3", "CHOLAFIN", "SELL", 19, 1667.8, note=MANUAL, ago=120)                   # entry: realized 0.0
    _leg("P3", "CHOLAFIN", "BUY", 19, 1670.5, realized=-60.0, ago=60)
    assert "CHOLAFIN" not in AppState(watchlist=[], paper_mode=True).positions


def test_only_the_current_mode_is_restored():
    _leg("P4", "LIVECO", "BUY", 5, 200.0, mode="live", note=CHECKLIST)
    assert "LIVECO" not in AppState(watchlist=[], paper_mode=True).positions
    assert AppState(watchlist=[], paper_mode=False).positions["LIVECO"]["quantity"] == 5


def test_yesterdays_open_leg_is_not_restored():
    _leg("P5", "OLDCO", "BUY", 5, 200.0, note=CHECKLIST, ago=2 * 86400)
    assert "OLDCO" not in AppState(watchlist=[], paper_mode=True).positions


def test_the_engine_counts_restored_positions_and_logs_them():
    _leg("P6", "GRASIM", "SELL", 6, 3172.95, note=MANUAL)
    _leg("P7", "HYUNDAI", "SELL", 9, 2099.37, note=MANUAL.replace("3180.70", "2108.59").replace("3170.36", "2076.83"))
    e = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    assert e.risk.open_positions_count == 2
    assert any("Restored 2 open position(s)" in a["message"] for a in e.state.activity)


def test_a_restored_short_stops_out_when_price_is_past_its_stop(monkeypatch):
    _leg("P8", "GRASIM", "SELL", 6, 3172.95, note=MANUAL)
    e = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    closed = []
    monkeypatch.setattr(e, "_exit_position", lambda sym, ltp, reason, note=None: closed.append((sym, reason)) or True)
    e._check_stop_take("GRASIM", 3181.0)
    assert closed and closed[0][0] == "GRASIM"
