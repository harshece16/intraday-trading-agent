"""The paper desk (README section 125): the four paper books as equal
experiments, and one process log that merges every step and trade they
record.

Read side only. Everything here is assembled from what the books already
write: the `activity`, `trades`, `rule_lab_trades` and `rule_lab_sessions`
tables, the Jev book's state file, the momentum book's state file, its job
log and its alert record. Nothing is written, no book's logic is called, and
no order path is touched. A book whose files are missing or unreadable gives
a card that says so, never an exception.

Two functions serve the dashboard:

    cards(now, engine)      -> GET /api/paper-desk
    process_log(day, ...)   -> GET /api/process-log?day=&book=&kind=

`engine` is a small dict of what only the running engine knows (market
status, open positions), passed in by app.py so this module never imports
the app's state.
"""
import datetime
import json
import logging
import os
import re
import statistics as st
import time
from collections import defaultdict
from zoneinfo import ZoneInfo

import config
import database
import holidays
import jev_book
import momentum_book
import rule_lab

logger = logging.getLogger("trading_bot")
IST = ZoneInfo("Asia/Kolkata")

BOOKS = ("intraday", "jev", "rule_lab", "momentum")
BOOK_NAMES = {"intraday": "Intraday engine", "jev": "Jev book", "rule_lab": "Rule lab", "momentum": "Momentum book"}
BOOK_PAGES = {"intraday": "/intraday", "jev": "/jev-book", "rule_lab": "/rule-lab", "momentum": "/momentum-book"}

# What each book is in one line, and the one line that says what it must pass
# before any real money. The gates are the project's existing rules, unchanged
# by the desk: RES-27 (a pass authorises paper only), ENT-02/ENT-05 (the live
# confidence bar), RES-36 (the rule lab's promotion ladder), MOM-10/MOM-16
# (the momentum band) and L53 (the after-tax comparison).
ABOUT = {
    "intraday": "Scans the NIFTY 100 on 5-minute bars, labels setups with the Varsity checklist and takes every "
                "paper entry that clears the other rules (confidence gate off in paper since 2026-10-01).",
    "jev": "Each trading day at 09:45, TypeSafe Jev (an LLM judge) says buy, short or skip for each stock on the "
           "scanner's shortlist; paper positions fill at Kite's live price and close at the 15:08 square-off.",
    "rule_lab": "107 single rules, each its own shadow paper book on the day's list: a rule that fires on a finished "
                "5-minute bar trades ₹50,000 for 30 minutes (or to a 3R target), paying full costs.",
    "momentum": "Holds the 15 of NSE's 200 most-traded stocks with the strongest 6- and 12-month momentum, in "
                "delivery, with ₹10 lakh of paper capital, rebalanced at the close of each month's first session.",
}
GATES = {
    "intraday": "Live needs a confidence score of 60 or more (ENT-02, ENT-05); the Scorecard's failing backtest row "
                "holds every score at 25 or less, so no automatic live entry can pass. No intraday edge has been found.",
    "jev": "Trial 123's verdict after 300 buy/short trades or 60 sessions: positive after costs with t ≥ 2.24 in both "
           "halves, and ahead of the scanner's side. A pass authorises a paper book only (RES-27).",
    "rule_lab": "Screen after lab session 40 (Romano–Wolf over every rule), confirmation on the next 40 sessions, then a "
                "proposal that spends a strategy trial; live needs your yes and the engine's live gate (RES-36).",
    "momentum": "Months of paper results agreeing with the backtest, the band not breached (from month 6, floor −14.8%), "
                "L53's after-tax comparison, and a separate owner decision (RES-27). Nothing here sets a date.",
}

JOB_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2}) (\w+) done code=(\d+) in (\d+)s")
JOB_EXIT = {0: "processed the day", 3: "nothing new to process", 4: "stopped early: a day's file was missing or the "
                                                                   "ranking was empty", 5: "another job was running"}
SIZE = {0: "no position", 1: "half size", 2: "normal size", 3: "double size"}
ACTIVITY_KIND_BOOK = {"momentum": "momentum"}       # every other activity kind is the engine's own


# --- time helpers --------------------------------------------------------------------------

def _now():
    return datetime.datetime.now(IST)


def day_bounds(day):
    """(start_ts, end_ts) of an IST calendar day, as epoch seconds."""
    d = datetime.date.fromisoformat(day)
    start = datetime.datetime(d.year, d.month, d.day, tzinfo=IST)
    return start.timestamp(), (start + datetime.timedelta(days=1)).timestamp()


def _ts_of_iso(s):
    """Epoch seconds of an ISO time the books write (naive = IST)."""
    if not s:
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(s))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.timestamp()


def _hhmm(ts):
    return datetime.datetime.fromtimestamp(ts, IST).strftime("%H:%M")


def _hhmmss(ts):
    return datetime.datetime.fromtimestamp(ts, IST).strftime("%H:%M:%S")


def _rs(x):
    return None if x is None else round(float(x), 2)


def _is_session(d):
    return d.weekday() < 5 and not holidays.is_holiday(d)


def _next_session(d):
    """The next trading day strictly after `d`."""
    return holidays.next_trading_day(d)


def _line(ts, book, kind, message, symbol=None, money=None, level="info", details=None):
    out = {"ts": ts, "time": _hhmmss(ts), "book": book, "kind": kind, "symbol": symbol,
           "message": message, "money": _rs(money), "level": level}
    if details:
        out["details"] = details
    return out


# --- sources, each wrapped so one broken file never empties the desk --------------------------

def _safe(fn, default):
    try:
        return fn()
    except Exception:
        logger.exception("Paper desk: %s failed", getattr(fn, "__name__", "a read"))
        return default


def _activity_rows(start, end):
    with database._conn() as c:
        rows = c.execute("SELECT ts, kind, symbol, message, level FROM activity WHERE ts >= ? AND ts < ? "
                         "ORDER BY ts DESC", (start, end)).fetchall()
    return [dict(r) for r in rows]


def _trade_rows(start, end):
    with database._conn() as c:
        rows = c.execute("SELECT ts, symbol, side, quantity, price, mode, reason, realized, charges, r_multiple "
                         "FROM trades WHERE ts >= ? AND ts < ? ORDER BY ts DESC", (start, end)).fetchall()
    return [dict(r) for r in rows]


def _lab_rows(start, end):
    with database._conn() as c:
        rows = c.execute(
            "SELECT rule, symbol, side, signal_time, entry_time, entry_price, qty, exit_time, exit_price, exit_reason, "
            "net_bp, net_rs, net_r, status, opened_ts, closed_ts FROM rule_lab_trades "
            "WHERE (opened_ts >= ? AND opened_ts < ?) OR (closed_ts >= ? AND closed_ts < ?)",
            (start, end, start, end)).fetchall()
    return [dict(r) for r in rows]


def _lab_session_row(day):
    with database._conn() as c:
        r = c.execute("SELECT session_date, symbols, bars, feed, first_ts, last_ts FROM rule_lab_sessions "
                      "WHERE session_date = ?", (day,)).fetchone()
    return dict(r) if r else None


def _jev_state():
    return jev_book.load_state(jev_book.STATE_PATH)


def _momentum_state():
    # The path is passed, not left to the default bound at import: tests and
    # the mock API point momentum_book.STATE_PATH elsewhere (as conftest does).
    return momentum_book.load_state(momentum_book.STATE_PATH) or {}


def _job_log_lines(day):
    """The evening job's own log, one line per finished run on `day`."""
    path = momentum_book.LOG_PATH
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - 65536))          # the last 64 KB holds months of runs
        tail = fh.read().decode("utf-8", "replace")
    for raw in tail.splitlines():
        m = JOB_LINE.match(raw.strip())
        if m and m.group(1) == day:
            out.append({"day": m.group(1), "time": m.group(2), "cmd": m.group(3), "code": int(m.group(4)),
                        "seconds": int(m.group(5))})
    return out


# --- the process log -------------------------------------------------------------------------

def _trade_message(t):
    side = t.get("side") or ""
    reason = t.get("reason") or ""
    is_exit = t.get("realized") is not None and t.get("r_multiple") is not None
    verb = {"BUY": "Bought", "SELL": "Sold"}.get(side, side)
    head = f"{verb} {t.get('quantity')} @ {float(t.get('price') or 0):,.2f}"
    if is_exit:
        why = {"stop_loss": "stop hit", "take_profit": "target hit", "auto_square_off": "square-off",
               "brain_exit": "exit signal", "brain_cover": "cover signal"}.get(reason, reason)
        pnl = float(t.get("realized") or 0)
        ch = float(t.get("charges") or 0)
        r = t.get("r_multiple")
        return (f"{head} · {why} · P&L {'+' if pnl >= 0 else '−'}₹{abs(pnl):,.0f} after ₹{ch:,.0f} charges"
                + (f" · {r:+.2f}R" if r is not None else ""))
    return f"{head} · entry: {reason}" if reason else head


def _engine_lines(start, end, rows_activity, rows_trades):
    out = []
    for a in rows_activity:
        kind = a.get("kind") or "system"
        book = ACTIVITY_KIND_BOOK.get(kind)
        msg = a.get("message") or ""
        if book is None:
            if msg.startswith("Jev book:"):
                book, kind = "jev", "round"
            elif msg.startswith("Momentum book:"):
                book, kind = "momentum", "job"
            else:
                book = "intraday"
        if book == "momentum" and a.get("kind") == "momentum":
            kind = "alert"
        if book == "intraday" and kind == "trade":
            continue                     # the trades table carries the same fill with its money
        out.append(_line(a["ts"], book, kind, msg, symbol=a.get("symbol"), level=a.get("level") or "info"))
    for t in rows_trades:
        is_exit = t.get("realized") is not None and t.get("r_multiple") is not None
        out.append(_line(t["ts"], "intraday", "trade", _trade_message(t), symbol=t.get("symbol"),
                         money=t.get("realized") if is_exit else None, level="trade"))
    return out


def _jev_lines(day, state):
    out = []
    d = (state.get("days") or {}).get(day)
    if not d:
        return out
    conf = jev_book.cfg()
    notional = float(conf.get("notional") or 0)
    status = d.get("status")
    decisions = d.get("decisions") or []
    if status in ("no_live_prices", "jev_unavailable") and not decisions:
        # A skipped day has no time of its own; the round was due at decide_at.
        ts = _ts_of_iso(f"{day}T{conf.get('decide_at', '09:45')}:00") or day_bounds(day)[0]
        why = "no live prices" if status == "no_live_prices" else "Jev unavailable"
        out.append(_line(ts, "jev", "round", f"Round skipped: {why}. {d.get('error') or ''}".strip(),
                         level="warn"))
        return out
    asked = [x for x in decisions if x.get("asked_at")]
    if asked:
        first = min(_ts_of_iso(x["asked_at"]) for x in asked)
        out.append(_line(first, "jev", "round", f"Round started: asking Jev about {len(decisions)} shortlisted "
                                                f"stock{'s' if len(decisions) != 1 else ''}"))
    for x in decisions:
        ts = _ts_of_iso(x.get("asked_at"))
        if ts is None:
            continue
        act = x.get("action") or "—"
        parts = [f"Jev says {act}"]
        if x.get("p_up") is not None:
            parts.append(f"P(up) {x['p_up']:.2f}")
        if x.get("size_level") is not None:
            parts.append(SIZE.get(x["size_level"], str(x["size_level"])))
        if x.get("scanner_side"):
            parts.append(f"scanner {str(x['scanner_side']).lower()}")
        if x.get("entry") is not None:
            parts.append(f"paper entry @ {float(x['entry']):,.2f}")
        elif x.get("excluded"):
            parts.append(x["excluded"])
        out.append(_line(ts, "jev", "decision", " · ".join(parts), symbol=x.get("symbol")))
        xt = _ts_of_iso(x.get("exit_at"))
        if xt is not None and x.get("net_bp") is not None and act in ("buy", "short"):
            net_bp = float(x["net_bp"])
            money = net_bp / 1e4 * notional if notional else None
            out.append(_line(xt, "jev", "trade", f"Closed {act} @ {float(x.get('exit') or 0):,.2f} · "
                                                 f"{net_bp:+.1f} bp after costs"
                                                 + (f" (≈ on ₹{notional:,.0f})" if notional else ""),
                             symbol=x.get("symbol"), money=money, level="trade"))
    intr = d.get("interrupted")
    if intr and intr.get("at"):
        ts = _ts_of_iso(intr["at"])
        if ts is not None:
            why = "Kite stopped giving live prices" if intr.get("reason") == "no_live_prices" else "Jev unavailable"
            out.append(_line(ts, "jev", "round", f"Round stopped after {intr.get('asked')} stocks: {why}", level="warn"))
    if d.get("closed") and decisions:
        exits = [_ts_of_iso(x.get("exit_at")) for x in decisions if x.get("exit_at")]
        if exits:
            traded = [x for x in decisions if x.get("net_bp") is not None and x.get("action") in ("buy", "short")]
            nets = [float(x["net_bp"]) for x in traded]
            mean = st.mean(nets) if nets else None
            msg = f"Round closed at the square-off: {len(traded)} position{'s' if len(traded) != 1 else ''} scored"
            if mean is not None:
                msg += f", {mean:+.1f} bp a position after costs"
            out.append(_line(max(exits) + 0.5, "jev", "round", msg,
                             money=(sum(nets) / 1e4 * notional) if (nets and notional) else None))
    return out


def _lab_lines(day, rows, session):
    out = []
    if session and session.get("first_ts"):
        out.append(_line(session["first_ts"], "rule_lab", "session",
                         f"Lab session started on {session.get('symbols')} stocks ({session.get('feed') or 'kite'} bars)"))
    start, end = day_bounds(day)
    opens = defaultdict(list)
    closes = defaultdict(list)
    for r in rows:
        if r.get("opened_ts") is not None and start <= r["opened_ts"] < end:
            opens[(r.get("entry_time") or "")[:16]].append(r)
        if r.get("closed_ts") is not None and start <= r["closed_ts"] < end and r.get("status") in ("closed", "void"):
            closes[(r.get("exit_time") or "")[:16] or "void"].append(r)
    for key, group in opens.items():
        ts = max(r["opened_ts"] for r in group)
        syms = sorted({r["symbol"] for r in group})
        longs = sum(1 for r in group if r.get("side") == "LONG")
        bar = key[11:16] if len(key) >= 16 else ""
        msg = (f"Opened {len(group)} paper trade{'s' if len(group) != 1 else ''} on the {bar} bar across "
               f"{len(syms)} stock{'s' if len(syms) != 1 else ''}: {longs} long, {len(group) - longs} short")
        details = [{"rule": r["rule"], "symbol": r["symbol"], "side": r["side"], "qty": r.get("qty"),
                    "price": r.get("entry_price"), "signal": (r.get("signal_time") or "")[11:16]}
                   for r in sorted(group, key=lambda r: (r["symbol"], r["rule"]))]
        out.append(_line(ts, "rule_lab", "lab_entry", msg, symbol=syms[0] if len(syms) == 1 else None,
                         details=details))
    for key, group in closes.items():
        ts = max(r["closed_ts"] for r in group)
        void = [r for r in group if r.get("status") == "void"]
        done = [r for r in group if r.get("status") == "closed"]
        if void and not done:
            out.append(_line(ts, "rule_lab", "lab_exit", f"{len(void)} open trade{'s' if len(void) != 1 else ''} "
                                                         f"from earlier sessions voided: no exit bar arrived",
                             level="warn"))
            continue
        net = sum(float(r.get("net_rs") or 0) for r in done)
        wins = sum(1 for r in done if (r.get("net_rs") or 0) > 0)
        bar = key[11:16] if len(key) >= 16 else ""
        msg = (f"Closed {len(done)} paper trade{'s' if len(done) != 1 else ''} at the {bar} bar: "
               f"{wins} won, {len(done) - wins} lost, net {'+' if net >= 0 else '−'}₹{abs(net):,.0f} after costs")
        details = [{"rule": r["rule"], "symbol": r["symbol"], "side": r["side"], "qty": r.get("qty"),
                    "price": r.get("exit_price"), "reason": r.get("exit_reason"), "net_rs": _rs(r.get("net_rs")),
                    "net_bp": _rs(r.get("net_bp"))} for r in sorted(done, key=lambda r: (r["symbol"], r["rule"]))]
        syms = sorted({r["symbol"] for r in done})
        out.append(_line(ts, "rule_lab", "lab_exit", msg, symbol=syms[0] if len(syms) == 1 else None, money=net,
                         level="trade", details=details))
    return out


def _momentum_lines(day, state, job_runs):
    out = []
    for run in job_runs:
        ts = _ts_of_iso(f"{run['day']}T{run['time']}")
        code = run["code"]
        what = JOB_EXIT.get(code, f"failed with exit code {code}")
        level = "info" if code in (0, 3) else ("warn" if code in (4, 5) else "error")
        out.append(_line(ts, "momentum", "job", f"Evening job finished in {run['seconds']} s: {what} (exit {code})",
                         level=level))
    # Trades are dated by session, not timed: the job books them at the close.
    close_ts = _ts_of_iso(f"{day}T{config.MARKET_CLOSE}:00")
    for i, t in enumerate(state.get("trades") or []):
        if t.get("date") != day:
            continue
        side = t.get("side") or ""
        verb = {"BUY": "Bought", "SELL": "Sold", "CANCELLED BUY": "Buy cancelled"}.get(side, side)
        value = float(t.get("value") or 0)
        cost = t.get("cost")
        msg = f"{verb} ₹{value:,.0f} at the {day} close"
        if side == "CANCELLED BUY":
            msg = f"Buy given up: no fill in five sessions since {t.get('ordered') or '—'}"
        elif cost is not None:
            msg += f" · ₹{float(cost):,.0f} charges and slippage"
        if t.get("ordered") and side != "CANCELLED BUY":
            msg += f" · waited since {t['ordered']}"
        out.append(_line(close_ts + i * 1e-3, "momentum", "trade", msg, symbol=t.get("symbol"),
                         money=-float(cost) if cost is not None and side != "CANCELLED BUY" else None, level="trade"))
    for p in state.get("month_points") or []:
        if p.get("date") == day:
            out.append(_line(close_ts + 0.5, "momentum", "rebalance",
                             f"Rebalanced at the {day} close: book ₹{float(p.get('book') or 0):,.0f}, "
                             f"benchmark ₹{float(p.get('bench') or 0):,.0f}"))
    for o in (state.get("book") or {}).get("orders") or []:
        if o.get("placed") == day:
            out.append(_line(close_ts + 0.25, "momentum", "trade",
                             f"{'Buy' if o.get('side') == 'BUY' else 'Sell'} order placed, waiting for a fill",
                             symbol=o.get("symbol")))
    return out


def process_log(day=None, book=None, kind=None, limit=400):
    """Every process step and trade of every book on one IST day, newest first."""
    day = day or _now().date().isoformat()
    try:
        start, end = day_bounds(day)
    except ValueError:
        raise ValueError("day must be YYYY-MM-DD")
    lines = []
    lines += _safe(lambda: _engine_lines(start, end, _activity_rows(start, end), _trade_rows(start, end)), [])
    lines += _safe(lambda: _jev_lines(day, _jev_state()), [])
    lines += _safe(lambda: _lab_lines(day, _lab_rows(start, end), _lab_session_row(day)), [])
    lines += _safe(lambda: _momentum_lines(day, _momentum_state(), _job_log_lines(day)), [])
    lines = [ln for ln in lines if ln["ts"] is not None and start <= ln["ts"] < end + 1]
    lines.sort(key=lambda ln: ln["ts"], reverse=True)
    books = sorted({ln["book"] for ln in lines}, key=BOOKS.index)
    kinds = sorted({ln["kind"] for ln in lines})
    counts = {b: sum(1 for ln in lines if ln["book"] == b) for b in BOOKS}
    if book:
        lines = [ln for ln in lines if ln["book"] == book]
    if kind:
        lines = [ln for ln in lines if ln["kind"] == kind]
    total = len(lines)
    return {"day": day, "items": lines[:max(0, int(limit))], "total": total, "truncated": total > limit,
            "books": books, "kinds": kinds, "counts": counts, "book_names": BOOK_NAMES}


# --- the cards ---------------------------------------------------------------------------------

def _status(state, label, detail=None):
    return {"state": state, "label": label, "detail": detail}


def _intraday_card(now, engine, day):
    start, end = day_bounds(day)
    trades = _safe(lambda: _trade_rows(start, end), [])
    exits = [t for t in trades if t.get("realized") is not None and t.get("r_multiple") is not None]
    entries = [t for t in trades if not (t.get("realized") is not None and t.get("r_multiple") is not None)]
    net_today = sum(float(t["realized"] or 0) for t in exits)
    stats = _safe(database.trade_stats, {"closed_trades": 0, "expectancy_r": None, "win_rate_pct": None})
    with database._conn() as c:
        all_net = c.execute("SELECT COALESCE(SUM(realized), 0), COUNT(*) FROM trades WHERE r_multiple IS NOT NULL").fetchone()
    engine = engine or {}
    market = engine.get("market_status")
    open_pos = int(engine.get("open_positions") or 0)
    session = _is_session(now.date())
    if engine.get("entries_paused"):
        status = _status("waiting", "Entries paused", "Stops, targets and the square-off still run")
    elif market == "open":
        status = _status("running", "Running", f"{open_pos} open paper position{'s' if open_pos != 1 else ''}; "
                                                f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} today")
    elif session and now.strftime("%H:%M") < config.MARKET_OPEN:
        status = _status("waiting", "Waiting for the open", f"The list is fixed before {config.MARKET_OPEN}; scans run on the open")
    elif session:
        status = _status("waiting", "Session over", f"Square-off was at {config.SQUARE_OFF_TIME}; "
                                                    f"{len(exits)} exit{'s' if len(exits) != 1 else ''} today")
    else:
        status = _status("waiting", "Market closed", "No session today (weekend or NSE holiday)")
    if market == "open":
        nxt = {"label": "Square-off", "when": f"{day}T{config.SQUARE_OFF_TIME}", "text": f"today {config.SQUARE_OFF_TIME}"}
    else:
        d = _next_session(now.date()) if not (session and now.strftime("%H:%M") < config.MARKET_OPEN) else now.date()
        nxt = {"label": "Next session", "when": f"{d.isoformat()}T{config.MARKET_OPEN}",
               "text": f"{d.strftime('%a %-d %b')}, {config.MARKET_OPEN}"}
    exp = stats.get("expectancy_r")
    return {
        "id": "intraday", "name": BOOK_NAMES["intraday"], "about": ABOUT["intraday"], "page": BOOK_PAGES["intraday"],
        "mode": "paper" if engine.get("paper_mode", True) else "LIVE",
        "status": status,
        "today": {"trades": len(exits), "entries": len(entries), "net": _rs(net_today), "open": open_pos,
                  "unrealized": _rs(engine.get("unrealized_pnl"))},
        "record": {"trades": int(all_net[1] or 0), "net": _rs(all_net[0]), "since": "the first paper fill",
                   "headline": {"label": "Expectancy", "value": (f"{exp:+.2f}R a trade" if exp is not None else "—"),
                                "note": (f"win rate {stats.get('win_rate_pct')}% over {stats.get('closed_trades')} closed"
                                         if stats.get("closed_trades") else "no closed trade yet")}},
        "next": nxt, "gate": GATES["intraday"],
    }


def _jev_card(now, day):
    state = _safe(_jev_state, {"days": {}, "status": None})
    summary = _safe(lambda: jev_book.summary(jev_book.STATE_PATH), {})
    conf = jev_book.cfg()
    notional = float(conf.get("notional") or 0)
    d = (state.get("days") or {}).get(day) or {}
    decisions = d.get("decisions") or []
    traded = [x for x in decisions if x.get("action") in ("buy", "short") and x.get("entry") is not None]
    scored = [float(x["net_bp"]) for x in traded if x.get("net_bp") is not None]
    session = _is_session(now.date())
    hhmm = now.strftime("%H:%M")
    if state.get("status") == "switched_off":
        status = _status("off", "Switched off", state.get("status_reason"))
    elif not conf.get("enabled"):
        status = _status("off", "Disabled in config", None)
    elif not summary.get("key_stored"):
        status = _status("waiting", "No TypeSafe key stored", "No round can run until a key is stored")
    elif d.get("status") == "no_live_prices":
        status = _status("skipped", "Skipped today: no live prices", d.get("error"))
    elif d.get("status") == "jev_unavailable":
        status = _status("skipped", "Skipped today: Jev unavailable", d.get("error"))
    elif d.get("status") in ("open", "deciding"):
        status = _status("running", f"Round open until {config.SQUARE_OFF_TIME}",
                         f"{len(traded)} paper position{'s' if len(traded) != 1 else ''}, "
                         f"{sum(1 for x in decisions if x.get('action') == 'skip')} skipped")
    elif d.get("closed"):
        status = _status("waiting", "Closed today", f"{len(scored)} position{'s' if len(scored) != 1 else ''} scored")
    elif session and hhmm < conf.get("decide_at", "09:45"):
        status = _status("waiting", f"Round at {conf.get('decide_at', '09:45')}", "Needs Kite's live prices and today's shortlist")
    elif session:
        status = _status("waiting", "No round today", "The round did not start (no shortlist, or the engine was down at 09:45)")
    else:
        status = _status("waiting", "No session today", None)
    if d.get("status") in ("open", "deciding"):
        nxt = {"label": "Square-off", "when": f"{day}T{config.SQUARE_OFF_TIME}", "text": f"today {config.SQUARE_OFF_TIME}"}
    else:
        nd = now.date() if (session and hhmm < conf.get("decide_at", "09:45") and not d) else _next_session(now.date())
        nxt = {"label": "Next round", "when": f"{nd.isoformat()}T{conf.get('decide_at', '09:45')}",
               "text": f"{nd.strftime('%a %-d %b')}, {conf.get('decide_at', '09:45')}"}
    mean = summary.get("mean_net_bp")
    t = summary.get("t")
    return {
        "id": "jev", "name": BOOK_NAMES["jev"], "about": ABOUT["jev"], "page": BOOK_PAGES["jev"], "mode": "paper",
        "status": status,
        "today": {"trades": len(traded), "scored": len(scored),
                  "net": _rs(sum(scored) / 1e4 * notional) if (scored and notional) else None,
                  "net_bp": _rs(st.mean(scored)) if scored else None,
                  "skips": sum(1 for x in decisions if x.get("action") == "skip")},
        "record": {"trades": summary.get("traded", 0), "sessions": summary.get("sessions_closed", 0),
                   "net": _rs(mean / 1e4 * notional * summary.get("traded", 0)) if (mean is not None and notional) else None,
                   "since": "2026-09-28",
                   "headline": {"label": "Net per trade", "value": (f"{mean:+.1f} bp" if mean is not None else "—"),
                                "note": (f"t {t:.2f} · scanner's side {summary.get('scanner_mean_net_bp'):+.1f} bp"
                                         if (t is not None and summary.get("scanner_mean_net_bp") is not None)
                                         else f"{summary.get('sessions_closed', 0)} sessions scored")}},
        "next": nxt, "gate": GATES["jev"],
    }


def _rule_lab_card(now, day):
    page = _safe(rule_lab.page, {"rules": [], "sessions": 0, "screen_at": rule_lab.SCREEN_SESSIONS})
    start, end = day_bounds(day)
    rows = _safe(lambda: _lab_rows(start, end), [])
    sess = _safe(lambda: _lab_session_row(day), None)
    opened = [r for r in rows if r.get("opened_ts") is not None and start <= r["opened_ts"] < end]
    closed = [r for r in rows if r.get("status") == "closed" and r.get("closed_ts") is not None
              and start <= r["closed_ts"] < end]
    net_today = sum(float(r.get("net_rs") or 0) for r in closed)
    with database._conn() as c:
        tot = c.execute("SELECT COUNT(*), COALESCE(SUM(net_rs), 0) FROM rule_lab_trades WHERE status = 'closed'").fetchone()
        open_n = c.execute("SELECT COUNT(*) FROM rule_lab_trades WHERE status = 'open'").fetchone()[0]
    rules = page.get("rules") or []
    by_status = defaultdict(int)
    for r in rules:
        by_status[r.get("status") or "collecting"] += 1
    session = _is_session(now.date())
    market_open = config.MARKET_OPEN <= now.strftime("%H:%M") < config.MARKET_CLOSE
    enabled = bool(getattr(config, "RULE_LAB", {}).get("enabled", True))
    if not enabled:
        status = _status("off", "Switched off in config", None)
    elif sess and session and market_open and (time.time() - float(sess.get("last_ts") or 0)) < 1200:
        status = _status("running", "Running", f"{sess.get('symbols')} stocks read this session; "
                                                f"{len(opened)} trade{'s' if len(opened) != 1 else ''} opened today")
    elif sess:
        status = _status("waiting", "Session recorded", f"{len(opened)} opened, {len(closed)} closed today")
    elif session and market_open:
        status = _status("waiting", "No bar read yet today", "The lab reads the candles the engine's tick fetches")
    else:
        status = _status("waiting", "Waiting for the next session", None)
    left = max(0, int(page.get("screen_at") or 0) - int(page.get("sessions") or 0))
    nxt = {"label": "The screen", "when": None,
           "text": (f"after {left} more lab session{'s' if left != 1 else ''}" if left else "due: read once")}
    return {
        "id": "rule_lab", "name": BOOK_NAMES["rule_lab"], "about": ABOUT["rule_lab"], "page": BOOK_PAGES["rule_lab"],
        "mode": "paper", "status": status,
        "today": {"trades": len(closed), "opened": len(opened), "open": int(open_n or 0), "net": _rs(net_today)},
        "record": {"trades": int(tot[0] or 0), "net": _rs(tot[1]), "sessions": page.get("sessions", 0),
                   "since": page.get("first_session") or "2026-10-05",
                   "headline": {"label": "Rules",
                                "value": f"{len(rules)} · {by_status.get('candidate', 0)} candidate{'s' if by_status.get('candidate', 0) != 1 else ''}",
                                "note": (f"{by_status.get('confirmed', 0)} confirmed · "
                                         f"{page.get('sessions', 0)} of {page.get('screen_at')} sessions to the screen")}},
        "next": nxt, "gate": GATES["rule_lab"],
    }


def _momentum_card(now, day):
    s = _safe(lambda: momentum_book.summary(momentum_book.STATE_PATH),
              {"status": "not_started", "months": [], "next_rebalance": None})
    state = _safe(_momentum_state, {})
    runs = _safe(lambda: _job_log_lines(day), [])
    trades_today = [t for t in (state.get("trades") or []) if t.get("date") == day]
    cost_today = sum(float(t.get("cost") or 0) for t in trades_today if t.get("side") != "CANCELLED BUY")
    status_key = s.get("status")
    problem = (s.get("data") or {}).get("problem")
    conf = momentum_book.cfg()
    session = _is_session(now.date())
    hhmm = now.strftime("%H:%M")
    if status_key == "switched_off":
        status = _status("off", "Switched off", s.get("status_reason"))
    elif status_key == "not_started":
        status = _status("waiting", "Not started", s.get("note"))
    elif problem:
        status = _status("skipped", "Last run stopped early", problem)
    elif runs and any(r["code"] == 0 for r in runs):
        status = _status("waiting", "Today's session processed", f"Evening job done at {runs[-1]['time'][:5]}")
    elif session and hhmm >= conf.get("job_after", "19:30"):
        status = _status("running", "Evening job due", f"Runs after {conf.get('job_after', '19:30')} when NSE's file is in")
    elif session:
        status = _status("waiting", "Holding", f"{len(s.get('holdings') or [])} stocks; marked after the close")
    else:
        status = _status("waiting", "Holding", f"{len(s.get('holdings') or [])} stocks; no session today")
    nr = s.get("next_rebalance")
    nxt = {"label": "Next rebalance", "when": f"{nr}T{config.MARKET_CLOSE}" if nr else None,
           "text": (datetime.date.fromisoformat(nr).strftime("%a %-d %b") + " close") if nr else "—"}
    since = s.get("since_start") or {}
    months = s.get("excess_months") or 0
    ce = s.get("cumulative_excess")
    headline_value = (f"{ce * 100:+.2f}% over {months} month{'s' if months != 1 else ''}" if (months and ce is not None)
                      else "no month complete yet")
    return {
        "id": "momentum", "name": BOOK_NAMES["momentum"], "about": ABOUT["momentum"], "page": BOOK_PAGES["momentum"],
        "mode": "paper", "status": status,
        "today": {"trades": len(trades_today), "net": _rs(-cost_today) if trades_today else None,
                  "note": "costs and slippage paid" if trades_today else None},
        "record": {"trades": len(state.get("trades") or []), "rebalances": s.get("rebalances", 0),
                   "net": _rs((s.get("book_value") or 0) - (s.get("capital") or 0)) if s.get("capital") else None,
                   "since": s.get("created") or "2026-09-26",
                   "book": _rs(since.get("book") * 100) if since.get("book") is not None else None,
                   "bench": _rs(since.get("bench") * 100) if since.get("bench") is not None else None,
                   "headline": {"label": "Cumulative excess", "value": headline_value,
                                "note": (f"book {since.get('book', 0) * 100:+.2f}% · benchmark {since.get('bench', 0) * 100:+.2f}% since the start"
                                         if since else "the book holds cash until its first rebalance")}},
        "next": nxt, "gate": GATES["momentum"],
    }


def cards(now=None, engine=None):
    """GET /api/paper-desk: one card per book, equal weight, nothing called the strategy."""
    now = now or _now()
    day = now.date().isoformat()
    books = [
        _safe(lambda: _intraday_card(now, engine, day), _fallback("intraday")),
        _safe(lambda: _jev_card(now, day), _fallback("jev")),
        _safe(lambda: _rule_lab_card(now, day), _fallback("rule_lab")),
        _safe(lambda: _momentum_card(now, day), _fallback("momentum")),
    ]
    return {"as_of": now.isoformat(timespec="seconds"), "day": day, "session": _is_session(now.date()),
            "paper_mode": (engine or {}).get("paper_mode", True), "books": books,
            "note": "Four paper books, each an equal experiment. None is the strategy until it passes its own gate; "
                    "no real-money order has ever been placed."}


def _fallback(book):
    return {"id": book, "name": BOOK_NAMES[book], "about": ABOUT[book], "page": BOOK_PAGES[book], "mode": "paper",
            "status": _status("unknown", "Could not read this book", "See the backend log"),
            "today": {}, "record": {"headline": {"label": "", "value": "—", "note": ""}},
            "next": {"label": "", "when": None, "text": "—"}, "gate": GATES[book]}
