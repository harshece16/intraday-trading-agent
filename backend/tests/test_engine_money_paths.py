"""
Regression tests for the money-path bugs found by the 2026-10-05 logic
review of the intraday engine and its accounting (README section 121):

- #249 an approval skipped recheck_plan (min R:R, stop-to-cost floor)
- #250 the live square-off stopped at the first failed close, and a close
       could be sent into a flat Kite account
- #251 two entries on two threads both passed max positions / the sector cap
- #252 the daily loss limit pooled paper and live P&L
- #253 a failing journal write mid-order skipped the position's bookkeeping
- #254 a restart dropped a live position with a partial exit
- #255 a square-off with no readable price was booked at the entry price

Every test drives the real TradingEngine against a throwaway journal. No
real Kite call is made: config's token is blanked and orders go to a fake
KiteConnect or the paper broker.
"""
import sqlite3
import threading
import time
from datetime import datetime

import pytest

import config
import data_provider
import database
import liquidity
import review_queue
import trader_brain
import trading_engine
from kite_broker import KiteExecutor
from state import AppState, _new_position

IST = review_queue.IST
KEYS = ["pattern", "sr", "cost", "volume", "dow", "rrr"]
BARS = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}] * 30
FAILING = {"scorecard": [{"criterion": "x", "status": "fail", "detail": ""}]}


def plan(side="long", failing=(), stop=98.0, target=106.0, entry=100.0):
    items = [{"key": k, "label": f"{k} label", "ok": k not in failing, "detail": f"{k} detail", "required": True}
             for k in KEYS]
    return {"side": side, "items": items, "passed": not failing, "pattern": "Hammer", "entry": entry,
            "stop": stop, "target": target, "rrr": 1.0, "size_factor": 1.0}


def analysis(long_plan="default", short_plan=None, bar_time="2026-10-01T10:15:00+05:30"):
    return {"entry_mode": "checklist", "setup": "Hammer", "bar_time": bar_time,
            "checklist": {"long": plan() if long_plan == "default" else long_plan, "short": short_plan},
            "bull_score": 8.0, "bear_score": 8.0, "confirmations": ["trend", "levels", "volume"],
            "bear_confirmations": ["trend", "levels", "volume"], "adx": 30, "entry_threshold": 6.0}


class NoKite:
    def __getattr__(self, name):
        pytest.fail(f"a real Kite call was made ({name})")


@pytest.fixture(autouse=True)
def no_kite(monkeypatch):
    monkeypatch.setattr(config, "KITE_API_KEY", "")
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "")
    monkeypatch.setattr(config, "KITE_FILL_DEADLINE_S", 0.05)
    monkeypatch.setattr(config, "KITE_FILL_POLL_S", 0.01)


@pytest.fixture
def eng(monkeypatch):
    monkeypatch.setitem(config.REVIEW_QUEUE, "enabled", True)
    monkeypatch.setattr(review_queue, "now_ist", lambda: datetime(2026, 10, 1, 10, 20, tzinfo=IST))
    monkeypatch.setattr(liquidity, "check", lambda *a, **k: (True, None, {}))
    monkeypatch.setattr(database, "journal_summary", lambda: FAILING)
    state = AppState(watchlist=[], paper_mode=True)
    e = trading_engine.TradingEngine(state)
    monkeypatch.setattr(e, "_ensure_kite", lambda: NoKite())
    state.market = {"bias": "neutral", "reasons": []}
    state.market_status = "open"
    return e


def legs(symbol):
    return sorted((t for t in database.recent_trades() if t["symbol"] == symbol), key=lambda t: t["ts"])


class FakeKiteConnect:
    """Kite with a day book that follows its own fills. `reject` symbols get
    every order rejected; a symbol held at 0 is one Zerodha's own square-off
    already closed."""

    def __init__(self, held=None, reject=()):
        self.held, self.reject, self.placed = dict(held or {}), set(reject), []

    def place_order(self, **kw):
        self.placed.append(kw)
        return f"ord{len(self.placed)}"

    def order_history(self, order_id):
        kw = self.placed[int(order_id[3:]) - 1]
        sym = kw["tradingsymbol"]
        if sym in self.reject:
            return [{"status": "REJECTED", "filled_quantity": 0, "average_price": 0.0,
                     "status_message": "RMS: test rejection"}]
        if not kw.get("_booked"):
            kw["_booked"] = True
            sign = 1 if kw["transaction_type"] == "BUY" else -1
            self.held[sym] = self.held.get(sym, 0) + sign * kw["quantity"]
        return [{"status": "COMPLETE", "filled_quantity": kw["quantity"], "average_price": 101.0}]

    def positions(self):
        return {"day": [{"tradingsymbol": s, "quantity": q, "product": "MIS"} for s, q in self.held.items()],
                "net": []}


def live_engine(fake, positions, paper_mode=False):
    state = AppState(watchlist=[], paper_mode=paper_mode)
    eng = trading_engine.TradingEngine(state)
    ex = KiteExecutor.__new__(KiteExecutor)
    ex.kite = fake
    eng.kite_executor = ex
    for sym, qty in positions.items():
        state.positions[sym] = {**_new_position(), "quantity": qty, "avg_price": 100.0, "stop_price": 98.0,
                                "target_price": 106.0, "position_id": f"P-{sym}", "live": True}
    eng.risk.open_positions_count = len(positions)
    return eng


def quiet_tick(monkeypatch, eng, phase):
    monkeypatch.setattr(trading_engine, "market_phase", lambda now=None: phase)
    monkeypatch.setattr(trading_engine.holidays, "holiday_name", lambda now: None)
    monkeypatch.setattr(eng, "should_fix_list", lambda *a, **k: False)
    monkeypatch.setattr(eng, "request_premarket_scan", lambda *a, **k: False)
    monkeypatch.setattr(eng, "request_scan", lambda: False)
    monkeypatch.setattr(eng, "_check_preopen_kite", lambda *a, **k: None)
    monkeypatch.setattr(trading_engine.depth_sampler, "sample", lambda *a, **k: None)
    monkeypatch.setattr(trading_engine.depth_sampler, "sample_windows", lambda *a, **k: None)
    monkeypatch.setattr(trading_engine.jev_book, "maybe_close", lambda *a, **k: False)
    monkeypatch.setattr(trading_engine.jev_book, "maybe_decide", lambda *a, **k: False)
    monkeypatch.setattr(trading_engine.momentum_book, "maybe_start_evening_job", lambda *a, **k: False)
    monkeypatch.setattr(trading_engine.momentum_alerts, "check", lambda *a, **k: None)
    monkeypatch.setattr(trading_engine.chaywanaprash, "maybe_start_review", lambda *a, **k: False)
    monkeypatch.setattr(data_provider, "get_candles_batch", lambda syms, **k: {})


# ---------------------------------------------------------------------------
# #249 an approval is held to recheck_plan at the live price
# ---------------------------------------------------------------------------

def _volume_card(eng, stop=98.0, target=104.0, ltp=100.0, failing=("volume",)):
    eng.state.positions["AAA"] = _new_position()
    p = plan(failing=failing, stop=stop, target=target)
    eng._offer_near_misses("AAA", ltp, BARS, analysis(p))
    cards = eng.review_queue.snapshot()["cards"]
    return p, (cards[0] if cards else None)


def test_an_approval_below_min_rrr_at_the_live_price_is_refused(eng, monkeypatch):
    p, card = _volume_card(eng)
    assert card["blocker"]["key"] == "volume" and card["net_rrr"] >= 1.5
    monkeypatch.setattr(data_provider, "get_ltp", lambda s: 102.5)      # moved toward the target
    assert trader_brain.recheck_plan(p, "long", 102.5, eng.strategy_params)["ok"] is False
    r = eng.approve_review(card["id"])
    assert r["ok"] is False and r["status"] == "refused"
    assert "reward-to-risk at the live price 102.50" in r["reason"]
    assert eng.state.positions["AAA"]["quantity"] == 0 and legs("AAA") == []


def test_an_approval_inside_the_stop_to_cost_floor_is_refused(eng, monkeypatch):
    _, card = _volume_card(eng)
    monkeypatch.setattr(data_provider, "get_ltp", lambda s: 98.1)       # 0.10 above a 98.00 stop
    r = eng.approve_review(card["id"])
    assert r["ok"] is False and "floor" in r["reason"]
    assert eng.state.positions["AAA"]["quantity"] == 0


def test_the_approval_still_goes_through_at_a_price_every_other_rule_accepts(eng, monkeypatch):
    _, card = _volume_card(eng)
    monkeypatch.setattr(data_provider, "get_ltp", lambda s: 100.0)
    r = eng.approve_review(card["id"])
    assert r["ok"] is True and eng.state.positions["AAA"]["quantity"] > 0


def test_a_card_is_not_offered_when_the_live_price_already_fails_recheck_plan(eng):
    _, card = _volume_card(eng, ltp=102.5)
    assert card is None


def test_a_card_blocked_on_rrr_is_exempt_from_min_rrr_but_not_from_the_cost_floor(eng, monkeypatch):
    # net R:R ~1.2 at 100: under min_rrr 1.5, over the queue floor of 1.0
    _, card = _volume_card(eng, stop=98.0, target=102.6, failing=("rrr",))
    assert card is not None and card["blocker"]["key"] == "rrr"
    assert eng._card_recheck("LONG", 98.0, 102.6, 100.0, "rrr")["ok"] is True
    assert eng._card_recheck("LONG", 98.0, 102.6, 98.1, "rrr")["ok"] is False     # cost floor still applies
    monkeypatch.setattr(data_provider, "get_ltp", lambda s: 100.0)
    assert eng.approve_review(card["id"])["ok"] is True


# ---------------------------------------------------------------------------
# #250 the live square-off closes every position; nothing is sent into a flat account
# ---------------------------------------------------------------------------

def test_one_rejected_close_does_not_stop_the_rest_of_the_square_off(monkeypatch):
    fake = FakeKiteConnect(held={"AAA": 10, "BBB": 10}, reject={"AAA"})
    eng = live_engine(fake, {"AAA": 10, "BBB": 10})
    monkeypatch.setattr(data_provider, "get_ltp", lambda sym: 101.0)
    quiet_tick(monkeypatch, eng, "square_off_window")
    closes_recorded = []
    monkeypatch.setattr(eng, "_record_session_closes", lambda now: closes_recorded.append(now))
    fno_closed = []
    eng.state.fno_positions["NIFTY"] = {"tradingsymbol": "NIFTY26OCT25000CE", "live": False}
    monkeypatch.setattr(eng, "_close_fno", lambda u, reason, note=None: fno_closed.append(u) or True)

    assert eng._square_off_all() == ["BBB"]                          # no exception out of the loop
    failed = []
    eng._square_off_all(failed=failed)
    assert [f["symbol"] for f in failed] == ["AAA"]
    for _ in range(2):
        eng.tick()
    sent = [(kw["tradingsymbol"], kw["transaction_type"]) for kw in fake.placed]
    assert ("BBB", "SELL") in sent and sent.count(("BBB", "SELL")) == 1
    assert eng.state.positions["BBB"]["quantity"] == 0
    assert eng.state.positions["AAA"]["quantity"] == 10             # still open, retried each tick
    assert sent.count(("AAA", "SELL")) == 4
    assert len(closes_recorded) == 2 and fno_closed == ["NIFTY", "NIFTY"]
    errors = [a for a in eng.state.activity if a["level"] == "error" and "Couldn't close AAA" in a["message"]]
    assert len(errors) == 1                                          # logged once, not every tick


def test_no_closing_order_is_sent_for_a_position_kite_no_longer_holds(monkeypatch):
    # Zerodha's MIS square-off flattened BBB after the engine's own close failed.
    fake = FakeKiteConnect(held={"BBB": 0})
    eng = live_engine(fake, {"BBB": 10})
    assert eng.check_stop_from_tick("BBB", 97.0) is False
    assert fake.placed == []
    assert eng.state.positions["BBB"]["quantity"] == 0
    assert eng.risk.open_positions_count == 0
    assert any("closed outside the engine" in a["message"] for a in eng.state.activity)


def test_a_close_is_cut_to_what_kite_holds(monkeypatch):
    fake = FakeKiteConnect(held={"BBB": 4})
    eng = live_engine(fake, {"BBB": 10})
    assert eng._check_stop_take("BBB", 97.0) is True
    assert [(kw["transaction_type"], kw["quantity"]) for kw in fake.placed] == [("SELL", 4)]
    assert eng.state.positions["BBB"]["quantity"] == 0


def test_the_kill_switch_reflatten_is_retried_until_it_succeeds(monkeypatch):
    fake = FakeKiteConnect(held={"AAA": 10}, reject={"AAA"})
    eng = live_engine(fake, {"AAA": 10})
    monkeypatch.setattr(data_provider, "get_ltp", lambda sym: 101.0)
    quiet_tick(monkeypatch, eng, "open")
    out = eng.stop_and_flatten()
    assert out["failed"] and eng._reflatten_pending is True
    eng.tick()
    assert eng._reflatten_pending is True and eng.state.positions["AAA"]["quantity"] == 10
    fake.reject.clear()                                              # Kite accepts the order now
    eng.tick()
    assert eng.state.positions["AAA"]["quantity"] == 0
    assert eng._reflatten_pending is False


def test_a_live_entry_confirmed_after_the_close_is_reconciled_with_kite(monkeypatch):
    fake = FakeKiteConnect()
    eng = live_engine(fake, {})
    eng.state.positions["AAA"] = _new_position()
    fake.placed.append({"tradingsymbol": "AAA", "quantity": 10, "transaction_type": "BUY", "_booked": True})
    eng._unconfirmed_orders["AAA"] = {"order_id": "ord1", "side": "BUY", "qty": 10, "price": 100.0, "context": {
        "reason": "Hammer (long)", "note": "Varsity checklist passed: stop 98.00, target 106.00",
        "checklist_snapshot": None, "position_id": "P1", "initial_risk": None, "confidence": None}}
    quiet_tick(monkeypatch, eng, "closed")
    eng.tick()                         # Kite answers at 15:35: filled. Zerodha already squared it off.
    assert eng.state.positions["AAA"]["quantity"] == 0
    assert eng.risk.open_positions_count == 0
    assert [kw["tradingsymbol"] for kw in fake.placed] == ["AAA"]    # no order after the close
    assert any("closed outside the engine" in a["message"] for a in eng.state.activity)


def test_a_live_position_kite_still_holds_after_the_close_is_reported(monkeypatch):
    fake = FakeKiteConnect(held={"AAA": 10})
    eng = live_engine(fake, {"AAA": 10})
    quiet_tick(monkeypatch, eng, "closed")
    eng.tick()
    eng.tick()
    assert fake.placed == [] and eng.state.positions["AAA"]["quantity"] == 10
    msgs = [a["message"] for a in eng.state.activity if "Kite still holds +10 in AAA" in a["message"]]
    assert len(msgs) == 1


# ---------------------------------------------------------------------------
# #251 concurrent entries can't exceed max positions or the sector cap
# ---------------------------------------------------------------------------

def _seed_two_open(eng):
    s = eng.state
    for sym in ("TCS", "RELIANCE"):                     # IT and Oil & Gas: no sector overlap
        s.positions[sym] = {**_new_position(), "quantity": 1, "avg_price": 100.0, "stop_price": 98.0,
                            "target_price": 106.0, "live": False}
    eng.risk.open_positions_count = 2
    for sym in ("HDFCBANK", "ICICIBANK"):               # both Financial Services
        s.positions[sym] = _new_position()
    assert eng._industry_for("HDFCBANK", None) == eng._industry_for("ICICIBANK", None)


def _card(eng, symbol):
    eng._offer_near_misses(symbol, 100.0, BARS, analysis(plan(failing=("volume",))))
    return next(c for c in eng.review_queue.snapshot()["cards"] if c["symbol"] == symbol)


@pytest.mark.parametrize("second", ["approval", "engine_entry"])
def test_concurrent_entries_respect_max_positions_and_the_sector_cap(eng, monkeypatch, second):
    _seed_two_open(eng)
    monkeypatch.setattr(data_provider, "get_ltp", lambda sym: 100.0)
    c1 = _card(eng, "HDFCBANK")
    c2 = _card(eng, "ICICIBANK") if second == "approval" else None
    meet = threading.Barrier(2, timeout=3)

    def liq(*a, **k):        # both entries reach the depth read, after their first gates, together
        try:
            meet.wait()
        except threading.BrokenBarrierError:
            pass
        return True, None, {}

    monkeypatch.setattr(liquidity, "check", liq)
    t1 = threading.Thread(target=lambda: eng.approve_review(c1["id"]))
    if second == "approval":
        t2 = threading.Thread(target=lambda: eng.approve_review(c2["id"]))
    else:
        t2 = threading.Thread(target=lambda: eng._try_enter("ICICIBANK", "LONG", 100.0, BARS, analysis()))
    t1.start(); t2.start(); t1.join(10); t2.join(10)
    assert not meet.broken, "the two entries did overlap in the gate-to-count window"
    held = sorted(s for s, p in eng.state.positions.items() if p["quantity"])
    assert len(held) == config.RISK["max_open_positions"] == 3
    assert eng.risk.open_positions_count == 3
    assert len({"HDFCBANK", "ICICIBANK"} & set(held)) == 1
    assert eng._reserved == set() and eng._entering == set()


def test_a_failed_order_gives_its_reserved_slot_back(eng, monkeypatch):
    _seed_two_open(eng)

    seen = []

    def rejected(symbol, *a, **k):
        seen.append(set(eng._reserved))                              # the slot is held during the order
        raise trading_engine.OrderNotFilled("Kite rejected the order")

    monkeypatch.setattr(eng, "_execute", rejected)
    assert eng._try_enter("HDFCBANK", "LONG", 100.0, BARS, analysis()) is False
    assert seen == [{"HDFCBANK"}]
    assert eng._reserved == set() and eng._entering == set()
    assert eng._cap_block_reason("ICICIBANK") is None


def test_the_engine_entry_claims_the_symbol_against_an_approval(eng, monkeypatch):
    _, card = _volume_card(eng)
    answers = []

    def order(symbol, *a, **k):          # an approval click lands while the engine's order is out
        answers.append(eng.approve_review(card["id"]))
        raise trading_engine.OrderNotFilled("test: stop here")

    monkeypatch.setattr(eng, "_execute", order)
    eng._try_enter("AAA", "LONG", 100.0, BARS, analysis(plan(stop=98.0, target=104.0)))
    [r] = answers
    assert r["ok"] is False and "being entered" in r["reason"]
    assert eng._entering == set()


# ---------------------------------------------------------------------------
# #252 the daily loss limit counts paper and live separately
# ---------------------------------------------------------------------------

def _paper_live_day(monkeypatch):
    monkeypatch.setitem(config.RISK, "total_capital", 100000.0)
    st = AppState(["AAA", "BBB"], paper_mode=True)
    eng = trading_engine.TradingEngine(st)
    eng._execute("AAA", "BUY", 100, 1000.0, reason="sig", position_id="p1", live=False)
    eng._execute("AAA", "SELL", 100, 1015.0, reason="take_profit", position_id="p1", initial_risk=10, live=False)
    paper = st.realized_by_mode["paper"]
    st.paper_mode = False
    eng._execute("BBB", "BUY", 100, 1000.0, reason="sig", position_id="l1", confirmed=(100, 1000.0, "OID1"))
    eng._execute("BBB", "SELL", 100, 970.0, reason="stop_loss", position_id="l1", initial_risk=10,
                 confirmed=(100, 970.0, "OID2"), live=True)
    return eng, st, paper


def test_paper_profits_do_not_cancel_a_real_money_loss(monkeypatch):
    eng, st, paper = _paper_live_day(monkeypatch)
    live = st.realized_by_mode["live"]
    assert paper > 1000 and live < -2000                             # +1,356 paper, -3,082 live
    assert eng.risk.daily_realized == pytest.approx({"paper": paper, "live": live})
    assert eng.risk.daily_loss_limit_hit() is True                   # the engine is in Live
    assert eng._entry_block_reason("AAA", "LONG") == "daily loss limit reached"
    assert st.snapshot()["realized_pnl_today"] == pytest.approx(live)
    assert st.snapshot()["realized_pnl_today_by_mode"] == pytest.approx({"paper": paper, "live": live})


def test_a_restart_seeds_each_mode_from_the_journal(monkeypatch):
    _paper_live_day(monkeypatch)
    eng2 = trading_engine.TradingEngine(AppState([], paper_mode=True))
    assert eng2.risk.daily_realized["live"] < -2000 < 1000 < eng2.risk.daily_realized["paper"]
    assert eng2.risk.daily_loss_limit_hit() is False                 # Paper: its own figure is a profit
    assert eng2.risk.daily_loss_limit_hit("live") is True


def test_paper_losses_do_not_refuse_live(monkeypatch):
    monkeypatch.setitem(config.RISK, "total_capital", 100000.0)
    monkeypatch.setattr(data_provider, "kite_session_status",
                        lambda probe=False: {"connected": True, "state": "connected", "reason": "ok"})
    eng = trading_engine.TradingEngine(AppState([], paper_mode=True))
    eng.risk.record_realized_pnl(-5000.0, "paper")
    assert eng.risk.daily_loss_limit_hit() is True                   # paper entries stop
    assert eng.live_readiness()["ready"] is True                     # but Live has lost nothing
    eng.risk.record_realized_pnl(-5000.0, "live")
    assert eng.live_readiness()["ready"] is False


# ---------------------------------------------------------------------------
# #253 a failing journal write can't skip the position's bookkeeping
# ---------------------------------------------------------------------------

APOLLO_BARS = [{"open": 8040, "high": 8050, "low": 8030, "close": 8040, "volume": 1000}] * 30


def apollo_entry(eng):
    s = eng.state
    s.positions["APOLLOHOSP"] = _new_position()
    s.market = {"bias": "risk-off", "reasons": ["NIFTY in a daily downtrend"]}
    p = plan(side="short", stop=8071.0, target=7910.0, entry=8039.0)
    a = analysis(long_plan=None, short_plan=p, bar_time="2026-10-01T12:40:00+05:30")
    return eng._try_enter("APOLLOHOSP", "SHORT", 8039.0, APOLLO_BARS, a)


def _locked_once(monkeypatch, fn_name, when):
    real = getattr(database, fn_name)
    fired = []

    def flaky(*a, **k):
        if not fired and when(*a, **k):
            fired.append(True)
            raise sqlite3.OperationalError("database is locked")
        return real(*a, **k)

    monkeypatch.setattr(database, fn_name, flaky)
    return fired


def test_a_locked_journal_on_the_entry_log_line_keeps_the_plan_stop(eng, monkeypatch):
    fired = _locked_once(monkeypatch, "record_activity", lambda kind, *a, **k: kind == "trade")
    assert apollo_entry(eng) is True
    assert fired
    pos = eng.state.positions["APOLLOHOSP"]
    assert pos["quantity"] == -4
    assert (pos["stop_price"], pos["target_price"]) == (8071.0, 7910.0)
    assert pos["position_id"] and pos["initial_risk"] == pytest.approx(34.4117, abs=1e-4)
    assert eng.risk.open_positions_count == 1
    assert eng.check_stop_from_tick("APOLLOHOSP", 8076.5) is True    # the plan's stop, not the 0.8% fallback
    [entry, exit_] = legs("APOLLOHOSP")
    assert entry["position_id"] == exit_["position_id"] and exit_["r_multiple"] == pytest.approx(-1.479, abs=1e-3)


def test_a_locked_journal_on_the_entry_row_keeps_the_plan_and_is_retried(eng, monkeypatch):
    _locked_once(monkeypatch, "record_trade", lambda trade, **k: trade["side"] == "SELL")
    assert apollo_entry(eng) is True
    pos = eng.state.positions["APOLLOHOSP"]
    assert pos["stop_price"] == 8071.0 and eng.risk.open_positions_count == 1
    assert legs("APOLLOHOSP") == [] and len(eng.state.unjournaled) == 1
    assert eng.state.retry_journal() == 1
    [entry] = legs("APOLLOHOSP")
    assert entry["position_id"] == pos["position_id"]


def test_a_locked_journal_on_the_exit_row_still_frees_the_slot_and_counts_the_loss(eng, monkeypatch):
    assert apollo_entry(eng) is True
    _locked_once(monkeypatch, "record_trade", lambda trade, **k: trade["side"] == "BUY")
    assert eng.check_stop_from_tick("APOLLOHOSP", 8076.5) is True
    assert eng.state.positions["APOLLOHOSP"]["quantity"] == 0
    assert eng.risk.open_positions_count == 0
    assert eng.risk.daily_realized_pnl == pytest.approx(-203.5756, abs=1e-3)
    assert len(legs("APOLLOHOSP")) == 1                              # the exit row is queued...
    eng.state.retry_journal()
    assert len(legs("APOLLOHOSP")) == 2                              # ...and written on the retry
    restarted = AppState(watchlist=[], paper_mode=True)
    assert restarted.restored_positions == []                       # a restart doesn't reopen it


# ---------------------------------------------------------------------------
# #254 a live position with a partial exit is restored at its open quantity
# ---------------------------------------------------------------------------

def test_a_part_closed_live_position_is_restored_at_its_open_quantity():
    note = "Varsity checklist passed on the 11:20 candle: stop 98.00, target 104.00, reward-to-risk 1.57"
    database.record_trade({"id": "L1-BUY", "position_id": "L1", "ts": time.time() - 120, "symbol": "AAA",
                           "side": "BUY", "quantity": 10, "price": 100.0, "mode": "live", "reason": "test",
                           "note": note, "realized": 0.0, "charges": 10.0})
    database.record_trade({"id": "L1-SELL", "position_id": "L1", "ts": time.time() - 60, "symbol": "AAA",
                           "side": "SELL", "quantity": 4, "price": 97.9, "mode": "live", "reason": "stop_loss",
                           "note": "partial", "realized": -12.4, "charges": 6.0})
    s = AppState(watchlist=["AAA"], paper_mode=True)
    assert s.restored_positions == ["AAA"]
    pos = s.positions["AAA"]
    assert (pos["quantity"], pos["live"], pos["stop_price"], pos["position_id"]) == (6, True, 98.0, "L1")
    assert pos["charges"] == pytest.approx(6.0)                      # the entry charges of the 6 still open


def test_a_fully_closed_position_in_two_legs_is_not_restored():
    for i, (side, qty) in enumerate((("BUY", 10), ("SELL", 4), ("SELL", 6))):
        database.record_trade({"id": f"L1-{i}", "position_id": "L1", "ts": time.time() - 100 + i, "symbol": "AAA",
                               "side": side, "quantity": qty, "price": 100.0, "mode": "live", "reason": "t",
                               "note": "stop 98.00, target 104.00", "realized": 0.0, "charges": 1.0})
    assert AppState(watchlist=["AAA"], paper_mode=True).restored_positions == []


# ---------------------------------------------------------------------------
# #255 a close with no readable price isn't booked at the entry price
# ---------------------------------------------------------------------------

def test_a_paper_square_off_without_a_price_is_retried_not_booked_at_the_entry(eng, monkeypatch):
    assert apollo_entry(eng) is True

    def no_price(symbol):
        raise RuntimeError(f"Could not fetch price for {symbol}")

    monkeypatch.setattr(data_provider, "get_ltp", no_price)
    assert eng._square_off_all() == []                               # not booked at the entry price
    assert eng.state.positions["APOLLOHOSP"]["quantity"] == -4 and len(legs("APOLLOHOSP")) == 1
    failed = []
    eng._square_off_all(failed=failed)
    assert "no live price" in failed[0]["error"]
    assert any("Couldn't close APOLLOHOSP" in a["message"] for a in eng.state.activity)
    monkeypatch.setattr(data_provider, "get_ltp", lambda symbol: 8050.0)
    assert eng._square_off_all() == ["APOLLOHOSP"]
    assert legs("APOLLOHOSP")[-1]["signal_price"] == 8050.0


def test_the_kill_switch_without_a_price_reports_the_paper_position_and_retries(eng, monkeypatch):
    assert apollo_entry(eng) is True
    def no_price(symbol):
        raise RuntimeError(f"Could not fetch price for {symbol}")

    monkeypatch.setattr(data_provider, "get_ltp", no_price)
    out = eng.stop_and_flatten()
    assert out["closed"] == [] and out["failed"][0]["symbol"] == "APOLLOHOSP"
    assert eng._reflatten_pending is True and len(legs("APOLLOHOSP")) == 1


def test_a_live_square_off_without_a_price_is_still_sent(monkeypatch):
    fake = FakeKiteConnect(held={"AAA": 10})
    eng = live_engine(fake, {"AAA": 10})
    monkeypatch.setattr(data_provider, "get_ltp", lambda symbol: None)
    assert eng._square_off_all() == ["AAA"]
    assert [(kw["transaction_type"], kw["quantity"]) for kw in fake.placed] == [("SELL", 10)]
    exit_ = legs("AAA")[-1]
    assert exit_["signal_price"] is None and "no live price" in exit_["note"]


def test_a_live_option_kite_no_longer_holds_gets_no_sell(monkeypatch):
    from tests.fno_kit import LOT, FakeKite, engine as fno_engine, order
    from tests.fno_kit import analysis as fno_analysis
    fake = FakeKite([order("COMPLETE", 4 * LOT, 20.0)], quote=20.0)
    e = fno_engine(monkeypatch, paper=False, kite=fake)
    assert e._try_enter_fno("ACME", "LONG", fno_analysis()) is True
    sent = len(fake.placed)
    fake.day = []                                    # Zerodha squared the option off
    assert e._close_fno("ACME", "fno_auto_square_off") is True
    assert len(fake.placed) == sent and e.state.fno_positions == {}
    assert any("closed outside the engine" in a["message"] for a in e.state.activity)


def test_the_day_plan_outcome_judges_the_loss_cap_in_the_current_mode(monkeypatch):
    import day_plan
    _paper_live_day(monkeypatch)
    live = day_plan.outcome(100000.0, paper_mode=False)
    paper = day_plan.outcome(100000.0, paper_mode=True)
    assert live["hit_daily_loss_limit"] is True and live["realized_pnl"] < -2000
    assert paper["hit_daily_loss_limit"] is False and paper["realized_pnl"] > 1000
