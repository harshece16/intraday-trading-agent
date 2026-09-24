"""
Manual review queue: setups that miss the entry by exactly one gate, put in
front of the user as a card to approve or reject.

A card is offered when, for one side of one stock:

- exactly one **required** checklist item failed (R:R, volume, trend, S/R,
  pattern or cost), and the plan still has a stop and a target; or
- every checklist item passed and the **confidence gate** alone stopped it.

Nothing here places an order. `TradingEngine.approve_review()` does, and
only after the user clicks Approve. That approval overrides the one gate
named on the card, plus the confidence gate. It **re-checks every risk
limit**: daily loss, max positions, sector cap, one entry per stock per day,
the entry window, the scanner/market filters, sizing and liquidity.

The card is a numbers card, deterministic and free. Its one derived judgement
is arithmetic: the win rate a trade at this R:R needs to break even, set
against the win rate this checklist has actually measured.
"""

import threading
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import config
import costs
import database
import trader_brain

IST = ZoneInfo("Asia/Kolkata")

# The checklist's own measured record: 201 checklist-passing trades over 495
# sessions, net of costs (README §51). The card compares every setup with
# this, because the user's approvals are drawn from the same entry rule.
BACKTEST_REFERENCE = {
    "win_rate": 0.32, "expectancy_r": -0.356, "trades": 201,
    "source": "README §51: 201 checklist trades over 495 sessions, net of costs",
}


def now_ist():
    return datetime.now(IST)


def single_blocker(plan):
    """The one required checklist item that failed, or None when none or
    several did."""
    failing = [i for i in (plan or {}).get("items", []) if i.get("required") and not i.get("ok")]
    return failing[0] if len(failing) == 1 else None


def build_card(symbol, side, plan, blocker, ltp, cost_pct, qty, setup=None, confidence=None,
               mode="paper", bar_time=None, expiry_seconds=None, now=None):
    """The numbers the user decides on. `side` is "LONG"/"SHORT"; `blocker`
    is {"key", "label", "detail"}; `cost_pct` is the round trip as a % of
    price, the same figure the checklist's R:R deducts."""
    now = now or now_ist()
    created = now.timestamp()
    expiry = expiry_seconds if expiry_seconds is not None else config.REVIEW_QUEUE["expiry_seconds"]
    stop, target = plan["stop"], plan["target"]
    risk_ps, reward_ps = abs(ltp - stop), abs(target - ltp)
    rrr = trader_brain._net_rrr(ltp, stop, target, cost_pct)
    stop_pct = risk_ps / ltp * 100
    breakeven = 1 / (1 + rrr) if rrr > 0 else None
    p = BACKTEST_REFERENCE["win_rate"]
    # In units of (risk + cost): a win nets rrr, a loss costs 1.
    expected_r = p * rrr - (1 - p)

    if breakeven is None:
        verdict = (f"The target doesn't cover the round trip's cost, so no win rate breaks even. At the "
                   f"checklist's measured {p:.0%} win rate this averages {expected_r:+.2f}R.")
    else:
        verdict = (f"Breaks even only if {breakeven:.0%} of trades like this win. The checklist wins {p:.0%}, "
                   f"which averages {expected_r:+.2f}R per trade.")

    return {
        "id": uuid.uuid4().hex[:12],
        "symbol": symbol, "side": side, "setup": setup or plan.get("pattern") or "Setup",
        "session_date": now.date().isoformat(),
        "created_ts": created, "expires_ts": created + expiry,
        "status": "pending", "mode": mode, "bar_time": bar_time,
        "blocker": {k: blocker.get(k) for k in ("key", "label", "detail")},
        "entry": round(ltp, 2), "stop": round(stop, 2), "target": round(target, 2),
        "net_rrr": round(rrr, 2), "stop_pct": round(stop_pct, 3),
        "target_pct": round(reward_ps / ltp * 100, 3), "cost_pct": cost_pct,
        "friction": round(cost_pct / stop_pct, 2) if stop_pct else None,
        "size_factor": plan.get("size_factor", 1.0),
        "qty": qty, "risk_rs": round(qty * risk_ps, 2), "reward_rs": round(qty * reward_ps, 2),
        "cost_rs": round(qty * ltp * cost_pct / 100, 2),
        "breakeven_win_rate": round(breakeven, 3) if breakeven is not None else None,
        "reference_win_rate": p, "expected_r": round(expected_r, 2),
        "reference_source": BACKTEST_REFERENCE["source"],
        "confidence": confidence,
        "verdict": verdict,
        "decided_ts": None, "position_id": None, "outcome": None,
    }


SHADOW_BASIS = ("Hypothetical, not a trade: entered at the price when the card was offered; exits only at "
                "the stop, the target or the square-off, whichever comes first, checked on the 5-minute bars "
                "after the offer (the stop is assumed first if one bar touches both); same slippage and "
                "charges as a real fill. An exit seen only in the latest price or a bar still forming is "
                "provisional until a completed bar settles it. The engine's own early-exit signal is not modelled.")


def _bar_ts(bar):
    return datetime.fromisoformat(bar["time"]).timestamp()


def _interval_seconds(interval):
    """"5m" -> 300. The bar length, so a bar still forming can be told apart
    from a completed one."""
    unit = interval[-1]
    return int(interval[:-1]) * {"m": 60, "h": 3600, "d": 86400}.get(unit, 60)


def shadow_outcome(card, bars, ltp=None, now=None, costs_cfg=None, square_off=None, interval=None):
    """What approving `card` the moment it was offered would have done.

    Walks the bars that START after the offer (a bar already running at the
    offer holds prices from before it) and exits at the first of: the
    square-off time (at that bar's open), the stop (at the stop, or the bar's
    open if it gapped through), or the target. Still open, it is marked to
    `ltp` — or closed at `ltp` if the price is already past the stop or
    target, or the square-off time has passed. P&L is net of the same
    slippage and charges _execute() applies to a real fill, both legs.

    `final` is True only when a COMPLETED bar settled the exit (or the
    square-off bar has opened). An exit decided from the last price, or from
    a bar still forming, is provisional and must be re-evaluated: on delayed
    data the bar that actually settles it can arrive minutes later, and one
    bar can still go on to touch the stop after touching the target (#102)."""
    now = now or now_ist()
    cfg = costs_cfg or config.COSTS
    s = 1 if card["side"] == "LONG" else -1
    entry, stop, target, qty = card["entry"], card["stop"], card["target"], card["qty"]
    created = card["created_ts"]
    day = datetime.fromtimestamp(created, IST).date()
    hh, mm = (square_off or config.SQUARE_OFF_TIME).split(":")
    square_ts = datetime(day.year, day.month, day.day, int(hh), int(mm), tzinfo=IST).timestamp()

    bar_len = _interval_seconds(interval or config.CANDLE_INTERVAL)
    exit_price = exit_ts = None
    status, final = "open", False
    for bar in sorted((b for b in bars or [] if _bar_ts(b) > created), key=_bar_ts):
        t = _bar_ts(bar)
        if t > now.timestamp():
            break
        complete = t + bar_len <= now.timestamp()
        if t >= square_ts:
            # The open is known the moment the square-off bar starts.
            status, exit_price, exit_ts, final = "squared_off", bar["open"], t, True
            break
        hit_stop = (bar["low"] <= stop) if s > 0 else (bar["high"] >= stop)
        hit_target = (bar["high"] >= target) if s > 0 else (bar["low"] <= target)
        if hit_stop:
            gapped = (bar["open"] - stop) * s < 0
            status, exit_price, exit_ts, final = "stopped", bar["open"] if gapped else stop, t, complete
            break
        if hit_target:
            status, exit_price, exit_ts, final = "target", target, t, complete
            break

    mark = ltp if ltp is not None else ((bars or [{}])[-1].get("close") if bars else None)
    if status == "open" and mark is not None:
        if now.timestamp() >= square_ts:
            status, exit_price, exit_ts = "squared_off", mark, now.timestamp()
        elif (mark - stop) * s <= 0:
            status, exit_price, exit_ts = "stopped", mark, now.timestamp()
        elif (mark - target) * s >= 0:
            status, exit_price, exit_ts = "target", mark, now.timestamp()

    price_out = exit_price if exit_price is not None else mark
    result = {"status": status, "final": final, "exit_price": exit_price, "exit_ts": exit_ts,
              "mark_price": mark, "as_of": now.timestamp(), "basis": SHADOW_BASIS}
    if price_out is None or not qty:
        result.update({"gross_rs": None, "charges_rs": None, "net_rs": None, "r": None})
        return result
    open_side, close_side = ("BUY", "SELL") if s > 0 else ("SELL", "BUY")
    fill_in = costs.apply_slippage(open_side, entry, cfg)
    fill_out = costs.apply_slippage(close_side, price_out, cfg)
    charges = costs.leg_cost(open_side, fill_in, qty, cfg) + costs.leg_cost(close_side, fill_out, qty, cfg)
    gross = (fill_out - fill_in) * qty * s
    net = gross - charges
    risk = abs(entry - stop) * qty
    result.update({"gross_rs": round(gross, 2), "charges_rs": round(charges, 2), "net_rs": round(net, 2),
                   "r": round(net / risk, 2) if risk else None})
    return result


class ReviewQueue:
    """Today's cards, in memory and in the `manual_reviews` table. One card
    per stock, side and session: the same rule as max_entries_per_day, so a
    setup that hovers near the bar all afternoon is asked about once."""

    def __init__(self):
        self._lock = threading.Lock()
        self.cards = {}
        self._seen = set()
        self._day = None

    def enabled(self):
        return bool(config.REVIEW_QUEUE.get("enabled"))

    def _roll(self, day):
        """Start a new day, rebuilt from the journal so a restart neither
        forgets today's cards nor asks about the same setup twice."""
        if self._day == day:
            return
        self._day = day
        self.cards, self._seen = {}, set()
        now = now_ist().timestamp()
        for card in database.reviews_on(day):
            if card.get("status") == "pending" and now > card.get("expires_ts", 0):
                card["status"], card["decided_ts"] = "expired", card["expires_ts"]
                database.update_review(card["id"], "expired", card["decided_ts"])
            self.cards[card["id"]] = card
            self._seen.add((card["symbol"], card["side"]))

    def seen(self, symbol, side, day=None):
        with self._lock:
            self._roll(day or now_ist().date().isoformat())
            return (symbol, side) in self._seen

    def add(self, card):
        """Offer a card. Returns it, or None if this stock and side were
        already asked about today."""
        with self._lock:
            self._roll(card["session_date"])
            key = (card["symbol"], card["side"])
            if key in self._seen:
                return None
            self._seen.add(key)
            self.cards[card["id"]] = card
        database.record_review(card)
        return card

    def get(self, review_id):
        with self._lock:
            card = self.cards.get(review_id)
            return dict(card) if card else None

    def decide(self, review_id, status, position_id=None, outcome=None):
        with self._lock:
            card = self.cards.get(review_id)
            if card is None:
                return None
            card.update({"status": status, "decided_ts": now_ist().timestamp(), "position_id": position_id,
                         "outcome": outcome})
            snapshot = dict(card)
        database.update_review(review_id, status, snapshot["decided_ts"], position_id=position_id,
                               outcome=outcome, card=snapshot)
        return snapshot

    def shadow_candidates(self):
        """Today's cards that were NOT approved (an approved card is a real
        position) and whose hypothetical trade isn't settled yet: not computed,
        still open, or exited provisionally (#102). An outcome saved before the
        `final` flag existed counts as provisional, so it is re-checked once."""
        with self._lock:
            return [dict(c) for c in self.cards.values()
                    if c["status"] != "approved" and not (c.get("shadow") or {}).get("final", False)]

    def set_shadow(self, review_id, shadow):
        with self._lock:
            card = self.cards.get(review_id)
            if card is None:
                return
            card["shadow"] = shadow
        database.update_review_shadow(review_id, shadow)

    def expire_due(self, now=None):
        now = now or now_ist().timestamp()
        with self._lock:
            due = [cid for cid, c in self.cards.items() if c["status"] == "pending" and now > c["expires_ts"]]
        for cid in due:
            self.decide(cid, "expired")
        return due

    def snapshot(self, limit=20):
        """For the dashboard: pending cards first, newest first, then today's
        decided ones."""
        try:
            with self._lock:
                self._roll(now_ist().date().isoformat())
            self.expire_due()
        except Exception:
            pass  # a journal hiccup must never break the state snapshot
        with self._lock:
            # The checklist copy is kept for the journal, not the dashboard.
            cards = [{k: v for k, v in c.items() if k != "checklist"} for c in self.cards.values()]
        pending = sorted((c for c in cards if c["status"] == "pending"), key=lambda c: -c["created_ts"])
        decided = sorted((c for c in cards if c["status"] != "pending"),
                         key=lambda c: -(c.get("decided_ts") or c["created_ts"]))
        shadows = [c["shadow"] for c in cards
                   if c["status"] != "approved" and (c.get("shadow") or {}).get("net_rs") is not None]
        return {
            "enabled": self.enabled(),
            "expiry_seconds": config.REVIEW_QUEUE["expiry_seconds"],
            "server_ts": now_ist().timestamp(),
            "cards": (pending + decided)[:limit],
            # "If every card today that wasn't approved had been": the day's
            # hypothetical total, so the queue's value is visible, not assumed.
            "shadow_summary": {
                "trades": len(shadows),
                "open": sum(1 for x in shadows if x["status"] == "open"),
                "provisional": sum(1 for x in shadows if x["status"] != "open" and not x.get("final")),
                "net_rs": round(sum(x["net_rs"] for x in shadows), 2),
                "r": round(sum(x["r"] or 0 for x in shadows), 2),
                "basis": SHADOW_BASIS,
            },
        }
