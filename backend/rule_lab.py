"""
The single-rule paper lab (research look L54, README section 124).

Small rules (twenty in cohort 1, 87 from the strategy catalogs in cohort 2,
rule_lab_catalog.py), each with a fixed side, entry and exit, are run as
shadow paper books on the day's list: on every finished 5-minute bar, each
rule asks only its own question ("a bullish engulfing bar?", "volume twice
the usual on an up bar?") and, if yes, records a virtual trade at the next
bar's open. Which rules, if any, earn more than they cost is decided only by
the pre-registered test in docs/research/prereg-rule-lab.md (with amendment
1), never by this module.

What it may and may not touch
-----------------------------
- It places no order and changes nothing the engine reads: positions,
  capital, the daily-loss counter, the review queue, the Scorecard. It reads
  the candles the tick already fetched and the scanner's long-only flag, and
  writes only its own two tables, rule_lab_trades and rule_lab_sessions.
- The engine calls RuleLab.run() after the tick's own work, inside a
  try/except, and run() catches everything itself as well. It re-reads a
  stock only when a new bar has arrived, and stops for the tick once it has
  used TIME_BUDGET_S; the rest wait for the next tick.
- No status here is read by any code that trades. "Candidate" and
  "confirmed" are for the page; promotion is the owner's decision (prereg §7).

The same simulate_session() is called by the historical screen
(research/rule_lab_screen.py, look L55), so both looks trade the same rules.
This module imports nothing from research/.
"""

import logging
import math
import random
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta

import candlestick_patterns
import costs
import indicators

logger = logging.getLogger("trading_bot")

# ---- fixed by the pre-registration (prereg-rule-lab.md §1, §2, amendment 1) ----

NOTIONAL = 50000.0            # Rs a trade: under Zerodha's Rs 20 brokerage cap, so 16.60 bp round trip
HOLD_BARS = 6                 # 30 minutes on 5-minute bars
BAR_MINUTES = 5
LAST_ENTRY = "14:30"          # the entry bar starts at or before this
SQUARE_OFF_BAR = "15:05"      # the last bar that starts before the engine's 15:08 square-off
GAP_MIN, GAP_MAX = 0.005, 0.10
RVOL_MIN = 2.0
RVOL_SESSIONS, RVOL_MIN_SESSIONS = 4, 2
PATTERN_WINDOW = 30
EMA_PERIOD = 20
TARGET_R = 3.0
VOID_AFTER_SESSIONS = 5

# The forward looks (prereg §6).
SCREEN_SESSIONS = 40
CONFIRM_SESSIONS = 40
MIN_SYMBOLS_FOR_SESSION = 10
SCREEN_MIN_TRADES, SCREEN_MIN_SESSIONS = 200, 20
CONFIRM_MIN_TRADES = 100
CONFIRM_MIN_SESSIONS = 10   # amendment 6: the floor for setting the bar at confirmation (passing needs §6 only)
ALPHA = 0.05                  # the lab's family-wise error over its whole life (prereg amendment 2)
BOOTSTRAP_B = 10000
BOOTSTRAP_SEED = 20261005
FORWARD_BLOCK = 3

# Rules that pass the historical screen go straight to forward confirmation
# (prereg §5). Empty until a reviewed change records L55's result here; the
# forward lab never depends on the screen.
HISTORICAL_CANDIDATES = {}    # rule id -> the first session of its confirmation period

# Where L55 writes its result; read only to show the historical column.
HISTORICAL_RESULT_PATH = None  # set below, next to the research data

# The first lab session of each cohort's forward screen; None = the lab's first session.
COHORT_START = {1: None, 2: None}

TIME_BUDGET_S = 1.5

# The registry is filled by register() below the signal functions (prereg
# amendment 2): a rule is data — an id, a name, a side, a family, a signal
# function of (ctx, pos) and its exit kind — so a rule or a combination added
# by a later amendment is one more register() line, not a code change.
REGISTRY = {}
RULES = []                    # (id, name, side, family), in registration order
RULE_IDS, RULE_SIDE, RULE_NAME, R_RULES = [], {}, {}, []


def register(rid, name, side, family, signal, exit_kind="fixed", cohort=1):
    """Add one rule. `signal(ctx, pos, cache)` -> bool on today's finished bar `pos`.
    `exit_kind` is "fixed" (30 minutes) or "r" (stop beyond the signal bar, 3R target).
    `cohort` is the amendment that added it (1 = the original twenty)."""
    if rid in REGISTRY:
        raise ValueError(f"rule {rid} is already registered")
    if side not in ("LONG", "SHORT") or exit_kind not in ("fixed", "r"):
        raise ValueError(f"bad rule {rid}")
    REGISTRY[rid] = {"id": rid, "name": name, "side": side, "family": family, "signal": signal,
                     "exit": exit_kind, "cohort": cohort}
    RULES.append((rid, name, side, family))
    RULE_IDS.append(rid)
    RULE_SIDE[rid] = side
    RULE_NAME[rid] = name
    if exit_kind == "r":
        R_RULES.append(rid)


def combination(rid, name, side, parts, exit_kind="fixed", cohort=2):
    """A rule that fires when every rule in `parts` fires on the same bar (prereg amendment 2)."""
    funcs = [REGISTRY[p]["signal"] for p in parts]
    register(rid, name, side, "combination", lambda ctx, pos, cache: all(f(ctx, pos, cache) for f in funcs),
             exit_kind=exit_kind, cohort=cohort)


def cohort_alpha(cohort):
    """The share of ALPHA a cohort's looks may spend: 1/2, 1/4, 1/8, ... (prereg amendment 2),
    so every rule and combination ever added stays inside one 5% family-wise error."""
    return ALPHA * 0.5 ** int(cohort)


def _default_costs():
    import config
    return config.COSTS


def _hhmm(t):
    return t[11:16]


def _add_minutes(t, minutes):
    """An ISO bar time plus `minutes`, same format and offset."""
    return (datetime.fromisoformat(t) + timedelta(minutes=minutes)).isoformat()


def _minutes_of(t):
    return int(t[11:13]) * 60 + int(t[14:16])


# ---- the context of one stock-session -----------------------------------------

def session_context(candles, session, n_closed=None):
    """Everything the rules read for `session`, computed once.

    `candles` are the stock's 5-minute bars, oldest first, today's and up to
    a few earlier sessions; a later session's bars are ignored. The first
    `n_closed` bars are finished (default: all). Rules read finished bars
    only; an open may be read from the bar still forming, because a bar's
    open is final once it starts."""
    bars = [c for c in candles if c["time"][:10] <= session]
    if n_closed is None:
        n_closed = len(bars)
    n_closed = min(n_closed, len(bars))
    today = [k for k, c in enumerate(bars) if c["time"][:10] == session]
    ctx = {"bars": bars, "session": session, "today": today, "n_closed": n_closed}
    if not today:
        return ctx
    closes = [c["close"] for c in bars]
    ctx["ema"] = indicators.ema_series(closes, EMA_PERIOD)
    # session VWAP at each of today's bars, cumulative (indicators.session_vwap on T[0..i])
    vwap, pv, vol = {}, 0.0, 0.0
    for k in today:
        c = bars[k]
        pv += (c["high"] + c["low"] + c["close"]) / 3 * c["volume"]
        vol += c["volume"]
        vwap[k] = pv / vol if vol > 0 else None
    ctx["vwap"] = vwap
    # earlier sessions, most recent last
    prior_days = sorted({c["time"][:10] for c in bars if c["time"][:10] < session})
    recent = prior_days[-RVOL_SESSIONS:]
    slot_vols = defaultdict(list)
    for c in bars:
        if c["time"][:10] in recent:
            slot_vols[_hhmm(c["time"])].append(c["volume"])
    ctx["slot_vols"] = slot_vols
    prior = [c for c in bars if c["time"][:10] < session]
    ctx["prev_close"] = prior[-1]["close"] if prior else None
    first = [bars[k] for k in today[:3]]
    # scanner.opening_range: the high and low of the session's first three bars
    ctx["or"] = (max(c["high"] for c in first), min(c["low"] for c in first)) if len(first) == 3 else None
    return ctx


def _patterns(ctx, k, cache=None):
    key = ctx["bars"][k]["time"]
    if cache is not None and key in cache:
        return cache[key]
    window = ctx["bars"][max(0, k - PATTERN_WINDOW + 1):k + 1]
    atr = indicators.atr(window, 14)
    names = {p["name"] for p in candlestick_patterns.detect_patterns(window, atr)} if atr else set()
    if cache is not None:
        cache[key] = names
    return names


def _rvol(ctx, k):
    c = ctx["bars"][k]
    vols = ctx["slot_vols"].get(_hhmm(c["time"]), [])
    if len(vols) < RVOL_MIN_SESSIONS:
        return None
    avg = sum(vols) / len(vols)
    return c["volume"] / avg if avg > 0 else None


def _trend(ctx, k, up):
    """U(i) (or D(i)): above VWAP and EMA20, EMA20 rising (the mirror for down)."""
    ema = ctx["ema"]
    v = ctx["vwap"].get(k)
    if k < 3 or v is None or ema[k] is None or ema[k - 3] is None:
        return None
    c = ctx["bars"][k]["close"]
    if up:
        return c > v and c > ema[k] and ema[k] > ema[k - 3]
    return c < v and c < ema[k] and ema[k] < ema[k - 3]


def _bar(ctx, pos):
    return ctx["bars"][ctx["today"][pos]]


def _pattern(name):
    def sig(ctx, pos, cache):
        return name in _patterns(ctx, ctx["today"][pos], cache)
    return sig


def _inside_break(up):
    def sig(ctx, pos, cache):
        if pos < 2:
            return False
        a, b, c = _bar(ctx, pos - 2), _bar(ctx, pos - 1), _bar(ctx, pos)
        if not (b["high"] <= a["high"] and b["low"] >= a["low"]):
            return False
        return c["close"] > b["high"] if up else c["close"] < b["low"]
    return sig


def _volume(up):
    def sig(ctx, pos, cache):
        c = _bar(ctx, pos)
        rv = _rvol(ctx, ctx["today"][pos])
        if rv is None or rv < RVOL_MIN:
            return False
        return c["close"] > c["open"] if up else c["close"] < c["open"]
    return sig


def _trend_turn(up):
    def sig(ctx, pos, cache):
        if pos < 1:
            return False
        now, before = _trend(ctx, ctx["today"][pos], up), _trend(ctx, ctx["today"][pos - 1], up)
        return bool(now) and before is not None and not before
    return sig


def _range_break(up):
    def sig(ctx, pos, cache):
        rng = ctx.get("or")
        if pos < 3 or not rng:
            return False
        hi, lo = rng
        close = _bar(ctx, pos)["close"]
        earlier = [_bar(ctx, j)["close"] for j in range(3, pos)]
        if up:
            return close > hi and not any(x > hi for x in earlier)
        return close < lo and not any(x < lo for x in earlier)
    return sig


def _gap(gap_up, bar_up):
    def sig(ctx, pos, cache):
        pc = ctx.get("prev_close")
        if pos != 0 or not pc:
            return False
        c = _bar(ctx, 0)
        gap = c["open"] / pc - 1
        if not (GAP_MIN <= abs(gap) <= GAP_MAX) or (gap > 0) != gap_up:
            return False
        return c["close"] > c["open"] if bar_up else c["close"] < c["open"]
    return sig


def _pullback(up):
    def sig(ctx, pos, cache):
        k = ctx["today"][pos]
        ema = ctx["ema"]
        if pos < 1 or k < 3 or None in (ema[k], ema[k - 1], ema[k - 3]):
            return False
        c, p = ctx["bars"][k], ctx["bars"][k - 1]
        if up:
            return ema[k] > ema[k - 3] and p["close"] > ema[k - 1] and c["low"] <= ema[k] < c["close"]
        return ema[k] < ema[k - 3] and p["close"] < ema[k - 1] and c["high"] >= ema[k] > c["close"]
    return sig


def _feature(ctx, pos, name, cache):
    """A named feature of today's bar `pos` for declarative rules; "prev_" reads bar pos-1."""
    if name.startswith("prev_"):
        return None if pos < 1 else _feature(ctx, pos - 1, name[5:], cache)
    k = ctx["today"][pos]
    c = ctx["bars"][k]
    ema = ctx["ema"]
    if name in ("open", "high", "low", "close", "volume"):
        return c[name]
    if name == "vwap":
        return ctx["vwap"].get(k)
    if name == "ema20":
        return ema[k]
    if name == "ema20_3ago":
        return ema[k - 3] if k >= 3 else None
    if name == "rvol":
        return _rvol(ctx, k)
    if name == "atr":
        return indicators.atr(ctx["bars"][max(0, k - PATTERN_WINDOW + 1):k + 1], 14)
    if name == "body":
        return abs(c["close"] - c["open"])
    if name == "range":
        return c["high"] - c["low"]
    if name == "gap":
        pc = ctx.get("prev_close")
        return (_bar(ctx, 0)["open"] / pc - 1) if pc else None
    if name in ("or_high", "or_low"):
        rng = ctx.get("or")
        return None if not rng or pos < 3 else (rng[0] if name == "or_high" else rng[1])
    if name == "prev_close_day":
        return ctx.get("prev_close")
    if name == "pos":
        return pos
    if name == "minute":
        return _minutes_of(c["time"])
    raise ValueError(f"unknown feature {name}")


_OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b}


def spec_signal(spec):
    """A signal from a declarative spec (prereg amendment 2), for rules added from the catalog:
    {"all": [["close", ">", "vwap"], ["rvol", ">=", 2], ["pattern", "Hammer"], ["minute", "<=", 600]]}.
    A term's right side is a feature name or a number; ["x", ">", "y", 1.5] compares x with 1.5 * y.
    Any missing feature makes the signal false, like the coded rules."""
    terms = spec.get("all") or []
    for term in terms:
        if term[0] != "pattern" and term[1] not in _OPS:
            raise ValueError(f"bad term {term}")

    def sig(ctx, pos, cache):
        for term in terms:
            if term[0] == "pattern":
                if term[1] not in _patterns(ctx, ctx["today"][pos], cache):
                    return False
                continue
            lhs = _feature(ctx, pos, term[0], cache)
            rhs = term[2] if isinstance(term[2], (int, float)) else _feature(ctx, pos, term[2], cache)
            if lhs is None or rhs is None:
                return False
            if len(term) > 3:
                rhs = rhs * term[3]
            if not _OPS[term[1]](lhs, rhs):
                return False
        return True
    return sig


def signals_at(ctx, pos, cache=None):
    """The registered rule ids that fire on today's finished bar number `pos` (0 = 09:15).
    With a cache (the forward lab keeps one per stock), a finished bar is read once: its
    answer cannot change, because every signal reads only bars up to it."""
    key = ("_signals", ctx["bars"][ctx["today"][pos]]["time"], len(REGISTRY))
    if cache is not None and key in cache:
        return cache[key]
    fired = [rid for rid, r in REGISTRY.items() if r["signal"](ctx, pos, cache)]
    if cache is not None:
        cache[key] = fired
    return fired


# Cohort 1: the twenty rules of prereg §1 and amendment 1, in this order.
register("R01", "Bullish engulfing", "LONG", "pattern", _pattern("Bullish Engulfing"))
register("R02", "Bearish engulfing", "SHORT", "pattern", _pattern("Bearish Engulfing"))
register("R03", "Hammer", "LONG", "pattern", _pattern("Hammer"))
register("R04", "Shooting star", "SHORT", "pattern", _pattern("Shooting Star"))
register("R05", "Bullish marubozu", "LONG", "pattern", _pattern("Bullish Marubozu"))
register("R06", "Bearish marubozu", "SHORT", "pattern", _pattern("Bearish Marubozu"))
register("R07", "Inside-bar breakout up", "LONG", "price", _inside_break(True))
register("R08", "Inside-bar breakdown", "SHORT", "price", _inside_break(False))
register("R09", "Buyers in control (volume 2x on an up bar)", "LONG", "volume", _volume(True))
register("R10", "Sellers in control (volume 2x on a down bar)", "SHORT", "volume", _volume(False))
register("R11", "Trend turns up (above VWAP, EMA20 rising)", "LONG", "trend", _trend_turn(True))
register("R12", "Trend turns down (below VWAP, EMA20 falling)", "SHORT", "trend", _trend_turn(False))
register("R13", "Opening-range breakout", "LONG", "range", _range_break(True))
register("R14", "Opening-range breakdown", "SHORT", "range", _range_break(False))
register("R15", "Gap and go, up", "LONG", "gap", _gap(True, True))
register("R16", "Gap and go, down", "SHORT", "gap", _gap(False, False))
register("R17", "Gap up fades", "SHORT", "gap", _gap(True, False))
register("R18", "Gap down fills", "LONG", "gap", _gap(False, True))
register("R19", "Pullback to a rising EMA20, stop below the bar, 3R target", "LONG", "pullback",
         _pullback(True), exit_kind="r")
register("R20", "Pullback to a falling EMA20, stop above the bar, 3R target", "SHORT", "pullback",
         _pullback(False), exit_kind="r")


# ---- the trade ---------------------------------------------------------------

def _price_trade(trade, costs_cfg):
    """Fill both legs with slippage and charge both legs (config.COSTS via costs.py)."""
    sign = 1 if trade["side"] == "LONG" else -1
    e, x, q = trade["entry_price"], trade["exit_price"], trade["qty"]
    buy_first = sign > 0
    e_fill = costs.apply_slippage("BUY" if buy_first else "SELL", e, costs_cfg)
    x_fill = costs.apply_slippage("SELL" if buy_first else "BUY", x, costs_cfg)
    charges = (costs.leg_cost("BUY" if buy_first else "SELL", e_fill, q, costs_cfg)
               + costs.leg_cost("SELL" if buy_first else "BUY", x_fill, q, costs_cfg))
    net_rs = sign * (x_fill - e_fill) * q - charges
    trade["gross_bp"] = sign * (x / e - 1) * 1e4
    trade["net_rs"] = net_rs
    trade["net_bp"] = net_rs / (e * q) * 1e4
    if trade.get("stop_price") is not None:
        risk = abs(e - trade["stop_price"]) * q
        trade["net_r"] = net_rs / risk if risk > 0 else None
    return trade


def _bar_at_or_after(ctx, t, upto=None):
    """Index of the first input bar of the session starting at or after `t`."""
    for k in ctx["today"]:
        if upto is not None and k >= upto:
            break
        if ctx["bars"][k]["time"] >= t:
            return k
    return None


def _fixed_exit(ctx, entry_k):
    """(exit bar index, reason) for the fixed-horizon rules, or (None, None) while it hasn't arrived."""
    bars = ctx["bars"]
    entry_t = bars[entry_k]["time"]
    due = _add_minutes(entry_t, HOLD_BARS * BAR_MINUTES)
    sq = entry_t[:11] + SQUARE_OFF_BAR + entry_t[16:]
    if due >= sq:
        k = _bar_at_or_after(ctx, sq)
        return (k, "square_off") if k is not None else (None, None)
    k = _bar_at_or_after(ctx, due)
    if k is not None and bars[k]["time"] >= sq:
        return k, "square_off"
    return (k, "horizon") if k is not None else (None, None)


def _r_exit(ctx, entry_k, side, stop, target):
    """Walk the finished bars from the entry bar: stop first when one bar reaches both,
    a gap past a level fills at the bar's open; the 15:05 bar's open otherwise."""
    bars, n_closed = ctx["bars"], ctx["n_closed"]
    sq = bars[entry_k]["time"][:11] + SQUARE_OFF_BAR + bars[entry_k]["time"][16:]
    sign = 1 if side == "LONG" else -1
    for k in ctx["today"]:
        if k < entry_k:
            continue
        b = bars[k]
        if b["time"] >= sq:
            return k, b["open"], "square_off"
        if k >= n_closed:
            return None, None, None
        opened_past_stop = (b["open"] - stop) * sign <= 0
        if k > entry_k and opened_past_stop:
            return k, b["open"], "stop"
        if k > entry_k and (b["open"] - target) * sign >= 0:
            return k, b["open"], "target"
        if (b["low"] if sign > 0 else b["high"]) * sign <= stop * sign:
            return k, stop, "stop"
        if (b["high"] if sign > 0 else b["low"]) * sign >= target * sign:
            return k, target, "target"
    return None, None, None


def simulate_session(candles, session, n_closed=None, long_only=False, allow_shorts=True,
                     costs_cfg=None, outcomes=True, cache=None, rules=None):
    """Every rule's virtual trades in one stock on one session (prereg §2).

    Returns a list of dicts with rule, side, signal_time, entry_time,
    entry_price, qty and, once the exit bar is in the input, exit_time,
    exit_price, exit_reason, gross_bp, net_bp, net_rs (net_r for R19/R20) and
    status "closed"; "open" while the exit hasn't arrived. With
    outcomes=False no exit price is read and nothing is priced: only which
    trades exist (stage 0 of the historical screen)."""
    costs_cfg = costs_cfg or _default_costs()
    rules = set(rules or RULE_IDS)
    ctx = session_context(candles, session, n_closed)
    today, bars, n_closed = ctx["today"], ctx["bars"], ctx["n_closed"]
    if not today:
        return []
    last_entry_min = _minutes_of("2000-01-01T" + LAST_ENTRY)
    busy_until = {}                      # rule -> the time its open trade exits (None = still open)
    trades = []
    for pos, k in enumerate(today):
        if k >= n_closed or pos + 1 >= len(today):
            break
        nxt = today[pos + 1]
        entry_bar = bars[nxt]
        if entry_bar["time"] != _add_minutes(bars[k]["time"], BAR_MINUTES):
            continue
        if _minutes_of(entry_bar["time"]) > last_entry_min:
            break
        for rid in signals_at(ctx, pos, cache):
            if rid not in rules:
                continue
            side = RULE_SIDE[rid]
            if side == "SHORT" and (long_only or not allow_shorts):
                continue
            if rid in busy_until and (busy_until[rid] is None or busy_until[rid] > entry_bar["time"]):
                continue
            e = entry_bar["open"]
            t = {"rule": rid, "side": side, "session": session, "signal_time": bars[k]["time"],
                 "entry_time": entry_bar["time"], "entry_price": e,
                 "qty": max(1, int(NOTIONAL // e)) if e > 0 else 0, "status": "open"}
            if t["qty"] <= 0:
                continue
            if rid in R_RULES:
                stop = bars[k]["low"] if side == "LONG" else bars[k]["high"]
                risk = (e - stop) if side == "LONG" else (stop - e)
                if risk <= 0 or risk / e * 100 < costs.round_trip_pct(NOTIONAL, costs_cfg):
                    continue
                target = e + TARGET_R * risk if side == "LONG" else e - TARGET_R * risk
                t["stop_price"], t["target_price"] = stop, target
                xk, xp, why = _r_exit(ctx, nxt, side, stop, target)
            else:
                xk, why = _fixed_exit(ctx, nxt)
                xp = bars[xk]["open"] if xk is not None else None
            busy_until[rid] = bars[xk]["time"] if xk is not None else None
            if xk is not None:
                t["exit_time"], t["exit_reason"], t["status"] = bars[xk]["time"], why, "closed"
                if outcomes:
                    t["exit_price"] = xp
                    _price_trade(t, costs_cfg)
            if not outcomes:
                t.pop("entry_price", None)
            trades.append(t)
    return trades


# ---- statistics (prereg §3, §4) ---------------------------------------------

def clustered(xs_by_session):
    """Mean per trade and its session-clustered t. `xs_by_session`: {session: [x, ...]}."""
    groups = [v for v in xs_by_session.values() if v]
    n = sum(len(v) for v in groups)
    g = len(groups)
    if n == 0:
        return {"n": 0, "sessions": 0, "mean": None, "se": None, "t": None, "ci": None}
    m = sum(sum(v) for v in groups) / n
    if g < 2:
        return {"n": n, "sessions": g, "mean": m, "se": None, "t": None, "ci": None}
    ss = sum((sum(v) - m * len(v)) ** 2 for v in groups)
    se = math.sqrt(g / (g - 1) * ss) / n
    t = m / se if se > 0 else None
    return {"n": n, "sessions": g, "mean": m, "se": se, "t": t,
            "ci": [m - 1.96 * se, m + 1.96 * se] if se else None}


def halves_means(xs_by_session, sessions):
    """Mean per trade in each chronological half of `sessions` (research/splits.halves)."""
    ordered = sorted(sessions)
    mid = len(ordered) // 2
    out = []
    for part in (ordered[:mid], ordered[mid:]):
        xs = [x for s in part for x in xs_by_session.get(s, [])]
        out.append(sum(xs) / len(xs) if xs else None)
    return out


def stationary_indices(n, block, rng):
    """One stationary-bootstrap draw of n indices (Politis and Romano, 1994)."""
    p = 1.0 / block
    out = [rng.randrange(n)]
    while len(out) < n:
        out.append(rng.randrange(n) if rng.random() < p else (out[-1] + 1) % n)
    return out


def clustered_matrix(S, N):
    """Mean per trade and clustered t for each row of per-session sums S and counts N (K x G)."""
    import numpy as np
    n = N.sum(axis=1)
    g = (N > 0).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        m = S.sum(axis=1) / n
        ss = ((S - m[:, None] * N) ** 2).sum(axis=1)
        se = np.sqrt(g / (g - 1) * ss) / n
        t = m / se
    t[~np.isfinite(t)] = np.nan
    return m, t, n, g


def bootstrap_weights(G, block, b, seed):
    """b stationary-bootstrap draws of G sessions, as multiplicity counts (b x G)."""
    import numpy as np
    rng = random.Random(seed)
    W = np.zeros((b, G), dtype=np.float32)
    for rep in range(b):
        for j in stationary_indices(G, block, rng):
            W[rep, j] += 1
    return W


MIN_CLUSTERS_IN_MAX = 5


def romano_wolf_matrix(S, N, block, b=BOOTSTRAP_B, seed=BOOTSTRAP_SEED, alpha=ALPHA, eligible=None,
                       chunk_b=500, chunk_k=4000, in_max=None, min_clusters=MIN_CLUSTERS_IN_MAX):
    """Studentised one-sided Romano-Wolf stepdown on K rules' per-session sums S and counts N (K x G).

    Streams over replicates and rules, so memory stays O(b + chunk) whatever K is: each step
    recomputes every replicate's maximum over the rules still in. `in_max` (amendment 6): the
    rules allowed to set the bar; the others are void (never in the maximum, never rejected).
    Inside a replicate a rule enters the maximum only with at least `min_clusters` effective
    session clusters (the replicate's weight over the sessions it traded in). Returns (t_hat,
    rejected bool array, step array, the critical value of each step)."""
    import numpy as np
    S = np.asarray(S, dtype=np.float64)
    N = np.asarray(N, dtype=np.float64)
    K, G = S.shape
    m_hat, t_hat, _, _ = clustered_matrix(S, N)
    W = bootstrap_weights(G, block, b, seed).astype(np.float64)
    eligible = np.ones(K, dtype=bool) if eligible is None else np.asarray(eligible, dtype=bool)
    in_max = np.ones(K, dtype=bool) if in_max is None else np.asarray(in_max, dtype=bool)
    eligible = eligible & in_max
    active = np.isfinite(t_hat) & in_max
    rejected = np.zeros(K, dtype=bool)
    step_of = np.zeros(K, dtype=int)
    crits = []
    step = 0

    def replicate_max(mask):
        mx = np.full(b, -np.inf)
        idx = np.nonzero(mask)[0]
        for k0 in range(0, len(idx), chunk_k):
            ks = idx[k0:k0 + chunk_k]
            Sk, Nk = S[ks], N[ks]
            S2, SN, N2, has = (Sk ** 2).T, (Sk * Nk).T, (Nk ** 2).T, (Nk > 0).astype(np.float64).T
            for lo in range(0, b, chunk_b):
                w = W[lo:lo + chunk_b]
                n_s, s_s, g_s = w @ Nk.T, w @ Sk.T, w @ has
                with np.errstate(divide="ignore", invalid="ignore"):
                    m_s = s_s / n_s
                    ss = w @ S2 - 2 * m_s * (w @ SN) + m_s ** 2 * (w @ N2)
                    se_s = np.sqrt(np.clip(g_s / (g_s - 1), 0, None) * np.clip(ss, 0, None)) / n_s
                    ts = (m_s - m_hat[ks][None, :]) / se_s
                ts[~np.isfinite(ts)] = -np.inf
                ts[g_s < min_clusters] = -np.inf
                np.maximum(mx[lo:lo + chunk_b], ts.max(axis=1), out=mx[lo:lo + chunk_b])
        return mx

    while active.any():
        step += 1
        mx = replicate_max(active)
        finite = mx[np.isfinite(mx)]
        # a replicate in which no rule met the cluster guard contributes nothing; if that is every
        # replicate, nothing can be rejected
        crit = float(np.quantile(finite, 1 - alpha)) if finite.size else float("inf")
        crits.append(crit)
        newly = active & eligible & (np.nan_to_num(t_hat, nan=-np.inf) > crit)
        if not newly.any():
            break
        rejected |= newly
        step_of[newly] = step
        active &= ~newly
    return t_hat, rejected, step_of, crits


def romano_wolf(data, sessions, block, b=BOOTSTRAP_B, seed=BOOTSTRAP_SEED, alpha=ALPHA, eligible=None,
                in_max=None):
    """romano_wolf_matrix on {rule: {session: [net bp, ...]}}. Returns {rule: {"t", "rejected",
    "step", "critical", "in_max"}}; only rules in `eligible` can be rejected, and only rules in
    `in_max` (amendment 6: those at the look's floor) set each step's maximum."""
    import numpy as np
    sessions = sorted(sessions)
    rules = sorted(data)
    if len(sessions) < 2 or not rules:
        return {r: {"t": None, "rejected": False, "in_max": False} for r in rules}
    S = np.array([[sum(data[r].get(s) or []) for s in sessions] for r in rules], dtype=float)
    N = np.array([[len(data[r].get(s) or []) for s in sessions] for r in rules], dtype=float)
    elig = set(eligible if eligible is not None else rules)
    inm = set(in_max if in_max is not None else rules)
    t_hat, rej, step, crits = romano_wolf_matrix(S, N, block, b=b, seed=seed, alpha=alpha,
                                                 eligible=[r in elig for r in rules],
                                                 in_max=[r in inm for r in rules])
    out = {}
    for i, r in enumerate(rules):
        st = int(step[i])
        out[r] = {"t": None if np.isnan(t_hat[i]) else float(t_hat[i]), "rejected": bool(rej[i]),
                  "step": st or None, "in_max": r in inm,
                  "critical": crits[st - 1] if st else (crits[-1] if crits else None)}
    return out


def max_consecutive_losses(xs):
    run = best = 0
    for x in xs:
        run = run + 1 if x <= 0 else 0
        best = max(best, run)
    return best


def describe(trades):
    """The page's figures for one rule's closed trades (prereg §3, amendment 1 §2)."""
    trades = sorted(trades, key=lambda t: (t["session"], t["entry_time"]))
    by = defaultdict(list)
    for t in trades:
        by[t["session"]].append(t["net_bp"])
    st = clustered(by)
    xs = [t["net_bp"] for t in trades]
    wins = [x for x in xs if x > 0]
    losses = [-x for x in xs if x <= 0]
    payoff = (sum(wins) / len(wins)) / (sum(losses) / len(losses)) if wins and losses and sum(losses) > 0 else None
    rs = [t.get("net_r") for t in trades if t.get("net_r") is not None]
    return {**st,
            "win_rate": len(wins) / len(xs) if xs else None,
            "break_even_win_rate": 1 / (1 + payoff) if payoff else None,
            "payoff": payoff,
            "max_consecutive_losses": max_consecutive_losses(xs),
            "gross_mean": (sum(t["gross_bp"] for t in trades) / len(trades)) if trades else None,
            "expectancy_r": (sum(rs) / len(rs)) if rs else None}


# ---- the journal -------------------------------------------------------------

def _db():
    import database
    return database._conn()


def lab_sessions():
    """Ordered sessions that count (prereg §6: at least MIN_SYMBOLS_FOR_SESSION stocks evaluated)."""
    rows = _db().execute("SELECT session_date FROM rule_lab_sessions WHERE symbols >= ? ORDER BY session_date",
                         (MIN_SYMBOLS_FOR_SESSION,)).fetchall()
    return [r[0] for r in rows]


def closed_trades():
    rows = _db().execute("SELECT * FROM rule_lab_trades WHERE status = 'closed'").fetchall()
    return [dict(r) for r in rows]


def _row(t, symbol, feed, now_ts):
    return (t["rule"], symbol, t["session"], t["side"], t["signal_time"], t["entry_time"], t["entry_price"],
            t["qty"], t.get("stop_price"), t.get("target_price"), t.get("exit_time"), t.get("exit_price"),
            t.get("exit_reason"), t.get("gross_bp"), t.get("net_bp"), t.get("net_rs"), t.get("net_r"),
            t["status"], feed, now_ts, now_ts if t["status"] == "closed" else None)


def record(symbol, trades, feed, now_ts=None):
    """Write new trades and close open ones. A closed row is never changed.
    Returns (inserted, closed)."""
    now_ts = now_ts or time.time()
    conn = _db()
    ins = clo = 0
    with conn:
        for t in trades:
            cur = conn.execute(
                "INSERT OR IGNORE INTO rule_lab_trades (rule, symbol, session_date, side, signal_time, entry_time, "
                "entry_price, qty, stop_price, target_price, exit_time, exit_price, exit_reason, gross_bp, net_bp, "
                "net_rs, net_r, status, feed, opened_ts, closed_ts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                _row(t, symbol, feed, now_ts))
            if cur.rowcount:
                ins += 1
                clo += t["status"] == "closed"
            elif t["status"] == "closed":
                cur = conn.execute(
                    "UPDATE rule_lab_trades SET exit_time=?, exit_price=?, exit_reason=?, gross_bp=?, net_bp=?, "
                    "net_rs=?, net_r=?, status='closed', closed_ts=? WHERE rule=? AND symbol=? AND session_date=? "
                    "AND entry_time=? AND status='open'",
                    (t["exit_time"], t["exit_price"], t["exit_reason"], t["gross_bp"], t["net_bp"], t["net_rs"],
                     t.get("net_r"), now_ts, t["rule"], symbol, t["session"], t["entry_time"]))
                clo += cur.rowcount
    return ins, clo


def note_session(session, symbols, bars, feed, now_ts=None):
    now_ts = now_ts or time.time()
    conn = _db()
    with conn:
        conn.execute(
            "INSERT INTO rule_lab_sessions (session_date, symbols, bars, feed, first_ts, last_ts) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(session_date) DO UPDATE SET symbols=MAX(symbols, excluded.symbols), "
            "bars=MAX(bars, excluded.bars), feed=excluded.feed, last_ts=excluded.last_ts",
            (session, symbols, bars, feed, now_ts, now_ts))


def void_stale(today, now_ts=None):
    """An open trade whose exit has not arrived within VOID_AFTER_SESSIONS lab sessions is void."""
    sessions = [s for s in lab_sessions() if s < today]
    if len(sessions) < VOID_AFTER_SESSIONS:
        return 0
    cutoff = sessions[-VOID_AFTER_SESSIONS]
    conn = _db()
    with conn:
        cur = conn.execute("UPDATE rule_lab_trades SET status='void', closed_ts=? WHERE status='open' "
                           "AND session_date < ?", (now_ts or time.time(), cutoff))
    return cur.rowcount


def open_sessions_by_symbol():
    rows = _db().execute("SELECT DISTINCT symbol, session_date FROM rule_lab_trades WHERE status='open'").fetchall()
    out = defaultdict(set)
    for r in rows:
        out[r[0]].add(r[1])
    return out


# ---- the forward lab, called by the engine ---------------------------------------

class RuleLab:
    """State kept between ticks: which bar each stock was last read at, and
    the candlestick detector's answers for bars already read."""

    def __init__(self, budget_s=TIME_BUDGET_S):
        self.budget_s = budget_s
        self._seen = {}
        self._pattern_cache = defaultdict(dict)
        self._rotate = 0
        self._session = None
        self._session_symbols = set()
        self._session_bars = 0
        self._lock = threading.Lock()
        self.last_run = {}
        self._errors_logged = set()

    def run(self, now, candles_map, watchlist, scan_row=None, allow_shorts=None):
        """One pass. Never raises. Returns a small dict for the log and the tests."""
        if not self._lock.acquire(blocking=False):
            return {"skipped": "busy"}
        started = time.perf_counter()
        cpu0 = time.process_time()
        info = {"symbols": 0, "inserted": 0, "closed": 0, "deferred": 0}
        try:
            self._run(now, candles_map or {}, list(watchlist or []), scan_row, allow_shorts, started, info)
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            if msg not in self._errors_logged:
                self._errors_logged.add(msg)
                logger.exception("Rule lab failed this pass (the tick is unaffected)")
            info["error"] = msg
        finally:
            info["wall_ms"] = round((time.perf_counter() - started) * 1000, 2)
            info["cpu_ms"] = round((time.process_time() - cpu0) * 1000, 2)
            self.last_run = info
            self._lock.release()
        return info

    def _run(self, now, candles_map, watchlist, scan_row, allow_shorts, started, info):
        import config
        import data_provider
        session = now.date().isoformat()
        if self._session != session:
            self._session, self._session_symbols, self._session_bars = session, set(), 0
            self._seen.clear()
            self._pattern_cache.clear()
            void_stale(session)
        if allow_shorts is None:
            # Shadow trades are not orders, so the engine's switch for shorts does not apply
            # (prereg amendment 4 §6); a long-only stock still skips its shorts.
            allow_shorts = True
        open_by_sym = open_sessions_by_symbol()
        n = len(watchlist)
        if not n:
            return
        start = self._rotate % n
        order = watchlist[start:] + watchlist[:start]
        for i, symbol in enumerate(order):
            if time.perf_counter() - started > self.budget_s:
                info["deferred"] = n - i
                self._rotate = (start + i) % n
                break
            candles = candles_map.get(symbol)
            if not candles:
                continue
            key = (candles[-1]["time"], len(candles))
            if self._seen.get(symbol) == key:
                continue
            closed = data_provider.closed_bars(candles, config.CANDLE_INTERVAL, now=now)
            row = scan_row(symbol) if scan_row else None
            long_only = bool(row and row.get("long_only"))
            sessions = {session} | {s for s in open_by_sym.get(symbol, ()) if s < session}
            trades = []
            for s in sorted(sessions):
                n_closed = len(closed)
                trades += simulate_session(candles, s, n_closed=n_closed, long_only=long_only,
                                           allow_shorts=allow_shorts, cache=self._pattern_cache[symbol])
            feed = "delayed" if candles[-1].get("delayed") else "kite"
            ins, clo = record(symbol, trades, feed)
            info["inserted"] += ins
            info["closed"] += clo
            info["symbols"] += 1
            self._seen[symbol] = key
            if any(c["time"][:10] == session for c in closed):
                self._session_symbols.add(symbol)
                self._session_bars = max(self._session_bars,
                                         sum(1 for c in closed if c["time"][:10] == session))
                note_session(session, len(self._session_symbols), self._session_bars, feed)
        else:
            self._rotate = 0


# ---- the page -------------------------------------------------------------------

_page_cache = {"at": 0.0, "data": None}


def _historical():
    import json
    import os
    path = HISTORICAL_RESULT_PATH or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                  "docs", "research", "data", "l55_result.json")
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _by_rule_session(trades, sessions):
    keep = set(sessions)
    out = {r: defaultdict(list) for r in RULE_IDS}
    for t in trades:
        if t["session_date"] in keep and t["rule"] in out:
            out[t["rule"]][t["session_date"]].append(t["net_bp"])
    return out


def _stage(trades, sessions, rules, min_trades, min_sessions, block, family=None, alpha=None, floor_sessions=None):
    data = _by_rule_session(trades, sessions)
    fam = family if family is not None else rules
    stats = {r: clustered(data[r]) for r in fam}
    eligible = [r for r in rules if (stats[r]["n"] >= min_trades and stats[r]["sessions"] >= min_sessions
                                     and stats[r]["mean"] is not None and stats[r]["mean"] > 0
                                     and all(h is not None and h > 0 for h in halves_means(data[r], sessions)))]
    if alpha is None:
        alpha = cohort_alpha(max(REGISTRY[r]["cohort"] for r in rules))
    # amendment 6: only rules at this look's floor set the bar; the rest are void at this look
    floor_sessions = min_sessions if floor_sessions is None else floor_sessions
    in_max = [r for r in fam if stats[r]["n"] >= min_trades and stats[r]["sessions"] >= floor_sessions]
    rw = romano_wolf({r: data[r] for r in fam if stats[r]["n"]}, sessions, block, eligible=eligible, alpha=alpha,
                     in_max=in_max)
    crit = next((v["critical"] for v in rw.values() if v.get("critical") is not None), None)
    return {r: {"passed": bool(rw.get(r, {}).get("rejected")), "eligible": r in eligible,
                "void": r not in in_max, "n": stats[r]["n"], "sessions": stats[r]["sessions"],
                "t": stats[r]["t"], "critical": rw.get(r, {}).get("critical", crit),
                "family_in_max": len(in_max), "family": len(fam)} for r in rules}


def evaluate(trades=None, sessions=None, open_left=None):
    """Each rule's status under prereg §6, from the journal. Deterministic: the
    same journal gives the same answer, so computing it on every page load is
    the one look, not many."""
    trades = closed_trades() if trades is None else trades
    sessions = lab_sessions() if sessions is None else sessions
    status = {r: {"status": "collecting"} for r in RULE_IDS}
    for r, first in HISTORICAL_CANDIDATES.items():
        status[r] = {"status": "candidate", "route": "historical", "confirm_from": first}
    if open_left is None:
        try:
            open_left = {r[0] for r in _db().execute(
                "SELECT DISTINCT session_date FROM rule_lab_trades WHERE status='open'")}
        except Exception:
            open_left = set()
    for cohort in sorted({r["cohort"] for r in REGISTRY.values()}):
        members = [r for r in RULE_IDS if REGISTRY[r]["cohort"] == cohort and r not in HISTORICAL_CANDIDATES]
        start = COHORT_START.get(cohort)
        own = [s for s in sessions if start is None or s >= start]
        screen = own[:SCREEN_SESSIONS]
        if not members or len(screen) < SCREEN_SESSIONS or (open_left & set(screen)):
            continue
        # every rule ever registered enters the bootstrap's maximum; only this cohort can pass
        res = _stage(trades, screen, members, SCREEN_MIN_TRADES, SCREEN_MIN_SESSIONS, FORWARD_BLOCK,
                     family=RULE_IDS, alpha=cohort_alpha(cohort))
        after = own[SCREEN_SESSIONS] if len(own) > SCREEN_SESSIONS else None
        for r in members:
            status[r] = ({"status": "candidate", "route": "forward", "confirm_from": after}
                         if res[r]["passed"] else {"status": "screen_failed"})
            status[r]["screen"] = res[r]
    # confirmation: candidates grouped by the period they confirm on
    groups = defaultdict(list)
    for r, st in status.items():
        if st["status"] == "candidate":
            first = st.get("confirm_from")
            if first:
                groups[first].append(r)
    for first, rules in groups.items():
        period = [s for s in sessions if s >= first][:CONFIRM_SESSIONS]
        if len(period) < CONFIRM_SESSIONS or (open_left & set(period)):
            continue
        res = _stage(trades, period, rules, CONFIRM_MIN_TRADES, 1, FORWARD_BLOCK, floor_sessions=CONFIRM_MIN_SESSIONS)
        for r in rules:
            status[r]["status"] = "confirmed" if res[r]["passed"] else "confirmation_failed"
            status[r]["confirmation"] = res[r]
    return status


def page(max_age_s=60):
    """GET /api/rule-lab: the leaderboard (README section 124)."""
    now = time.time()
    if _page_cache["data"] is not None and now - _page_cache["at"] < max_age_s:
        return _page_cache["data"]
    trades = closed_trades()
    sessions = lab_sessions()
    conn = _db()
    open_n = conn.execute("SELECT rule, COUNT(*) FROM rule_lab_trades WHERE status='open' GROUP BY rule").fetchall()
    open_by_rule = {r[0]: r[1] for r in open_n}
    void_n = dict(conn.execute("SELECT rule, COUNT(*) FROM rule_lab_trades WHERE status='void' GROUP BY rule")
                  .fetchall())
    statuses = evaluate(trades, sessions)
    hist = _historical()
    hist_rules = (hist or {}).get("rules", {}) if isinstance(hist, dict) else {}
    by_rule = defaultdict(list)
    for t in trades:
        by_rule[t["rule"]].append({"session": t["session_date"], **t})
    rows = []
    for rid, name, side, family in RULES:
        d = describe(by_rule.get(rid, []))
        h = hist_rules.get(rid) or {}
        hmean = h.get("mean")
        rows.append({"rule": rid, "name": name, "side": side, "family": family,
                     "cohort": REGISTRY[rid]["cohort"], "sources": REGISTRY[rid].get("sources") or [],
                     "r_based": rid in R_RULES, **d,
                     "open": open_by_rule.get(rid, 0), "void": void_n.get(rid, 0),
                     **statuses[rid],
                     "historical": ({"n": h.get("n"), "mean": hmean, "win_rate": h.get("win_rate"),
                                     "passed": h.get("passed")} if h else None),
                     "decay_bp": (d["mean"] - hmean) if (hmean is not None and d["mean"] is not None) else None})
    last = conn.execute("SELECT MAX(last_ts) FROM rule_lab_sessions").fetchone()[0]
    data = {
        "rules": rows,
        "sessions": len(sessions),
        "first_session": sessions[0] if sessions else None,
        "last_session": sessions[-1] if sessions else None,
        "screen_at": SCREEN_SESSIONS, "confirm_sessions": CONFIRM_SESSIONS,
        "cohort_alpha": {str(c): cohort_alpha(c) for c in sorted({r["cohort"] for r in REGISTRY.values()})},
        "screen_min_trades": SCREEN_MIN_TRADES,
        "notional": NOTIONAL, "hold_minutes": HOLD_BARS * BAR_MINUTES,
        "round_trip_bp": costs.round_trip_pct(NOTIONAL, _default_costs()) * 100,
        "historical_run": bool(hist),
        "last_update_ts": last,
        "prereg": "docs/research/prereg-rule-lab.md",
    }
    _page_cache.update(at=now, data=data)
    return data


# Cohort 2 (prereg amendment 4): the catalogs' intraday conditions, registered on import.
import rule_lab_catalog  # noqa: E402,F401
