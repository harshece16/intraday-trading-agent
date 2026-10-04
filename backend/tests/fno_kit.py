"""Shared stand-ins for the F&O engine tests (#157, #186, #187): a Kite that
scripts NFO order states, and an engine whose option entry reaches the order
without the network (instruments, ban list, confidence and depth patched).
Not a test module itself."""
from datetime import datetime, timedelta

import confidence
import config
import database
import fno_instruments
import liquidity
import nse_feed
import trading_engine
from kite_broker import KiteExecutor
from state import AppState

LOT = 25
STRIKE = 1000.0
SPOT = 1000.0


def order(status, filled=0, avg=0.0, message=None):
    return {"status": status, "filled_quantity": filled, "average_price": avg, "status_message": message}


class FakeKite:
    """kiteconnect.KiteConnect, for NFO: a script of order states, one quote
    for every contract, and a day book of positions. With no `positions`
    given, the day book agrees with whatever the engine holds (every live
    close reads it first since #250)."""

    def __init__(self, states=(), quote=20.0, positions=None, fail_reads=0, cancel_to=None, down=False):
        self.states, self.quote = list(states), quote
        self.day = None if positions is None else list(positions)
        self.eng = None
        self.fail_reads, self.cancel_to, self.down = fail_reads, cancel_to, down
        self.placed, self.cancelled = [], []

    def place_order(self, **kw):
        self.placed.append(kw)
        return f"ord{len(self.placed)}"

    def order_history(self, order_id):
        if self.fail_reads:
            self.fail_reads -= 1
            raise ConnectionError("Kite is unreachable")
        state = self.states[0] if len(self.states) == 1 else self.states.pop(0)
        return [{"status": "PUT ORDER REQ RECEIVED"}, state]

    def cancel_order(self, variety, order_id):
        self.cancelled.append(order_id)
        if self.cancel_to:
            self.states = [self.cancel_to]

    def ltp(self, key):
        return {key: {"last_price": self.quote}}

    def positions(self):
        if self.down:
            raise ConnectionError("Kite is unreachable")
        if self.day is None:
            return {"day": self._mirror(), "net": []}
        return {"day": self.day, "net": []}

    def _mirror(self):
        if self.eng is None:
            return []
        rows = [{"tradingsymbol": p["tradingsymbol"], "quantity": p["lots"] * p["lot_size"], "product": "MIS"}
                for p in self.eng.state.fno_positions.values()]
        rows += [{"tradingsymbol": s, "quantity": p["quantity"], "product": "MIS"}
                 for s, p in self.eng.state.positions.items() if p["quantity"]]
        return rows


def use(eng, fake):
    ex = KiteExecutor.__new__(KiteExecutor)  # skip __init__: no real KiteConnect
    ex.kite = fake
    eng.kite_executor = ex
    fake.eng = eng
    return fake


def book(bid, ask, qty=5000, levels=5, step=0.05):
    return {"buy": [{"price": round(bid - i * step, 2), "quantity": qty} for i in range(levels)],
            "sell": [{"price": round(ask + i * step, 2), "quantity": qty} for i in range(levels)]}


def expiry():
    return datetime.now(trading_engine.IST).date() + timedelta(days=20)


def contract(underlying="ACME", is_call=True):
    return {"tradingsymbol": f"{underlying}26OCT1000{'CE' if is_call else 'PE'}", "instrument_token": 1,
            "strike": STRIKE, "lot_size": LOT, "expiry": expiry(), "is_call": is_call, "underlying": underlying}


def analysis():
    return {"ltp": SPOT, "bull_score": 20.0, "bear_score": 0.0, "setup": "Test", "checklist": None}


def engine(monkeypatch, paper=True, kite=None, depth=None):
    """An engine whose option buy reaches the order: confidence 90, a clear
    ban list, one listed contract per underlying and side, and `depth` for
    every contract's book (a deep, 1%-wide book unless given; "none" for no
    book at all)."""
    monkeypatch.setattr(config, "KITE_FILL_DEADLINE_S", 0.05)
    monkeypatch.setattr(config, "KITE_FILL_POLL_S", 0.01)
    today = datetime.now(trading_engine.IST).date().isoformat()
    monkeypatch.setattr(database, "journal_summary", lambda *a, **k: {"scorecard": []})
    monkeypatch.setattr(confidence, "score_trade",
                        lambda *a, **k: {"score": 90, "label": "high", "explanation": "test"})
    monkeypatch.setattr(nse_feed, "fno_ban_list", lambda *a, **k: {"trade_date": today, "symbols": set()})
    monkeypatch.setattr(fno_instruments, "nearest_expiry", lambda *a, **k: expiry())
    monkeypatch.setattr(fno_instruments, "find_contract",
                        lambda underlying, spot, exp, is_call, *a, **k: contract(underlying, is_call))
    the_book = None if depth == "none" else (depth or book(19.9, 20.1))
    monkeypatch.setattr(liquidity, "_fetch_option_depth", lambda tradingsymbol: the_book)
    eng = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=paper))
    eng.state.market = {"bias": "neutral", "reasons": []}     # the first scan has finished (#256)
    if kite is not None:
        use(eng, kite)
    return eng


def evaluations():
    with database._conn() as c:
        return [dict(r) for r in c.execute("SELECT underlying, side, executed, block_reason FROM fno_evaluations "
                                           "ORDER BY id").fetchall()]


def fno_row(position_id):
    with database._conn() as c:
        r = c.execute("SELECT * FROM fno_trades WHERE position_id = ?", (position_id,)).fetchone()
    return dict(r) if r else None
