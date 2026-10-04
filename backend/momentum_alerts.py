"""
Alerts for the momentum book's evening job (README section 116).

The engine starts the job with momentum_book.maybe_start_evening_job and then,
on the same closed-phase tick, calls check(). It says what the job did, once:

- **A rebalance the job completed.** One activity line of kind "momentum": the
  month, the stocks bought and sold, the book against its benchmark for the
  month just ended and since the start, the band, and the next rebalance.
- **A run that failed** (an exit code other than 0, 3, 4 or 5, or a signal) **or
  stopped early** (exit 4: the book stops before a day whose data is
  missing). One line with the reason, once per reason a day.
- **A day still not processed when the job's window closes** (23:30), after a
  run that day. One line.

Every line goes through AppState.log, so it is in the activity log and the
journal, and telegram_alerts sends it to the phone when Telegram is set up
and switched on: "momentum" is one of the kinds it always sends.

What was alerted is kept in data/momentum_book_alerts.json, written only
here, so a restart neither repeats an alert nor loses one. The rebalance
alert is driven by the state file's month points, not by the job's process
handle, which a restart loses. With no record yet, only the latest rebalance
is alerted, never the whole history. The record is written before the line
is logged: an alert may be lost, never sent twice.

Nothing here writes the book's state file, starts or stops the job, or
raises. It changes no rule of the book.
"""

import datetime
import json
import logging
import os

import momentum_book

logger = logging.getLogger("trading_bot")

KIND = "momentum"
ALERTS_PATH = os.path.join(momentum_book.DATA, "momentum_book_alerts.json")
NOT_PUBLISHED = 3        # daily()'s exit codes (momentum_book.daily)
STOPPED = 4
BUSY = 5                 # another evening job held the lock; it did nothing (momentum_book.BUSY)

_mem = {"record": None, "state_mtime": None, "watched": None, "handled": []}


def reset():
    """Forget everything held in memory, as a restart does. Tests use it."""
    _mem.update(record=None, state_mtime=None, watched=None, handled=[])


# --- the record of what was alerted ----------------------------------------------------

def _record():
    if _mem["record"] is None:
        rec = {}
        try:
            if os.path.exists(ALERTS_PATH):
                with open(ALERTS_PATH) as fh:
                    rec = json.load(fh)
        except (OSError, ValueError):
            logger.warning("Momentum book: the alert record is unreadable; starting a new one")
        _mem["record"] = rec if isinstance(rec, dict) else {}
    return _mem["record"]


def _save(rec):
    """Atomic, and best-effort: the record in memory already stops a repeat
    within this process, so a failed write can cost at most one repeat after
    a restart."""
    try:
        tmp = ALERTS_PATH + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(rec, fh, indent=1)
        os.replace(tmp, ALERTS_PATH)
    except OSError:
        logger.exception("Momentum book: could not save the alert record")


# --- wording -----------------------------------------------------------------------------

def _pct(x):
    return "n/a" if x is None else f"{x * 100:+.2f}%"


def _day(iso):
    d = datetime.date.fromisoformat(iso[:10])
    return f"{d.day} {d.strftime('%b %Y')}"


def _month(iso):
    return datetime.date.fromisoformat(iso[:10]).strftime("%B %Y")


def _names(trades):
    return ", ".join(sorted(t["symbol"] for t in trades)) if trades else "none"


def rebalance_message(state, date, conf=None):
    """The alert for the rebalance made at `date`'s close, from the state as
    the job saved it."""
    conf = conf or momentum_book.cfg()
    pts = state.get("month_points") or []
    k = next(i for i, p in enumerate(pts) if p["date"] == date)
    trades = state.get("trades") or []
    ordered = [t for t in trades if (t.get("ordered") or t["date"]) == date]
    bought = [t for t in ordered if t["side"] == "BUY"]
    sold = [t for t in ordered if t["side"] == "SELL"]
    waiting = [o for o in state["book"].get("orders", []) if o.get("placed") == date]
    parts = [f"Momentum book (paper): rebalanced at the {_day(date)} close for {_month(date)}.",
             f"Bought {len(bought)}: {_names(bought)}.", f"Sold {len(sold)}: {_names(sold)}."]
    if waiting:
        parts.append("Waiting to fill: " + ", ".join(f"{o['side'].lower()} {o['symbol']}" for o in waiting) + ".")
    if k == 0:
        parts.append("No month is complete yet: this is the book's first rebalance.")
    else:
        row = momentum_book.monthly_report({"month_points": pts[:k + 1], "trades": trades})["months"][-1]
        parts.append(f"{_month(row['start'])}: book {_pct(row['book_return'])}, benchmark {_pct(row['bench_return'])}, "
                     f"excess {_pct(row['excess'])}.")
    cap, p = state["capital"], pts[k]
    cum = sum((pts[i]["book"] / pts[i - 1]["book"] - 1) - (pts[i]["bench"] / pts[i - 1]["bench"] - 1)
              for i in range(1, k + 1))
    since = (f"Since the start ({_day(state['created'])}, Rs {cap / 1e5:g} lakh): book {_pct(p['book'] / cap - 1)}, "
             f"benchmark {_pct(p['bench'] / cap - 1)}")
    parts.append(since + (f"; cumulative excess {_pct(cum)} over {k} month{'s' if k != 1 else ''}." if k else "."))
    mean, sd, start = conf["expected_monthly_excess"], conf["monthly_excess_sd"], conf["band_from_month"]
    if k >= start:
        parts.append(f"Band: expected {_pct(k * mean)}, floor {_pct(momentum_book.band_threshold(k, mean, sd))}.")
    else:
        parts.append(f"The switch-off band applies from month {start} (floor then "
                     f"{_pct(momentum_book.band_threshold(start, mean, sd))}).")
    if state.get("status") == "switched_off":
        parts.append(f"The book has switched itself off: {state.get('status_reason') or 'below its band'}.")
    else:
        nxt, cal_ok = momentum_book.next_rebalance(date)
        parts.append(f"Next rebalance: the {_day(nxt)} close" + ("." if cal_ok else
                     " (no NSE holiday list for that year yet, so the date may move)."))
    parts.append("Benchmark: the equal-weighted 200 most-traded NSE stocks.")
    return " ".join(parts)


# --- the check ---------------------------------------------------------------------------

def check(now, holiday, log):
    """Called by the engine on every closed-phase tick, after
    maybe_start_evening_job. Never raises."""
    try:
        _check(now, holiday, log)
    except Exception:
        logger.exception("Momentum book: the alert check failed")


def _finished_jobs():
    """Exit codes of jobs started in this process that have ended since the
    last check. Holds its own reference to each job, so a job replaced by a
    retry is still read."""
    cur = momentum_book._last_attempt.get("proc")
    out = []
    for proc in (_mem["watched"], cur):
        if proc is None or any(proc is h for h in _mem["handled"]):
            continue
        rc = proc.poll()
        if rc is not None:
            _mem["handled"] = (_mem["handled"] + [proc])[-4:]
            out.append(rc)
    _mem["watched"] = cur
    return out


def _problem(rec, today, reason, level, log):
    """One alert per distinct reason a day."""
    seen = rec.get("problems") or {}
    if seen.get("date") != today:
        seen = {"date": today, "sent": []}
    if reason in seen["sent"]:
        return
    seen["sent"].append(reason)
    rec["problems"] = seen
    _save(rec)
    log(KIND, reason, level=level)


def _last_log_line():
    try:
        with open(momentum_book.LOG_PATH, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 4096))
            lines = [x.strip() for x in fh.read().decode("utf-8", "replace").splitlines() if x.strip()]
        return lines[-1][:240] if lines else None
    except OSError:
        return None


def _check(now, holiday, log):
    rec = _record()
    today = now.date().isoformat()
    conf = momentum_book.cfg()

    codes = _finished_jobs()
    state_path = momentum_book.STATE_PATH
    try:
        mtime = os.path.getmtime(state_path)
    except OSError:
        mtime = None
    state = None
    if mtime is not None and (mtime != _mem["state_mtime"] or codes):
        state = momentum_book.load_state(state_path)
        _mem["state_mtime"] = mtime

    for rc in codes:
        if rc in (0, NOT_PUBLISHED, STOPPED, BUSY):
            continue                      # a stop is read from the state below, restart or not; a busy run did nothing
        how = f"was stopped by signal {-rc}" if rc < 0 else f"failed with exit code {rc}"
        tail = _last_log_line()
        where = f" The book is unchanged since {state['last_processed']}." if state and state.get("last_processed") else ""
        _problem(rec, today, f"Momentum book: the evening job {how}."
                             + (f" Last line of momentum_book.log: {tail}." if tail else "") + where
                             + f" It is tried again every {conf['retry_minutes']} minutes until {conf['job_until']}.",
                 "error", log)

    if state:
        dates = [p["date"] for p in state.get("month_points") or []]
        last = rec.get("rebalance")
        new = dates[-1:] if last is None else [d for d in dates if d > last]
        for d in new:
            rec["rebalance"] = d
            _save(rec)
            log(KIND, rebalance_message(state, d, conf),
                level="warn" if state.get("status") == "switched_off" else "info")
        problem = (state.get("data") or {}).get("problem")
        if problem and (state.get("updated_at") or "")[:10] == today:
            _problem(rec, today, f"Momentum book: the evening job stopped early: {problem}.", "warn", log)

    if (not holiday and now.weekday() < 5 and now.strftime("%H:%M") >= conf["job_until"]
            and rec.get("window_closed") != today):
        state = state or momentum_book.load_state(state_path)
        if (state and state.get("status") != "switched_off" and (state.get("updated_at") or "")[:10] == today
                and state.get("last_processed") != today):
            rec["window_closed"] = today
            _save(rec)
            if (state.get("data") or {}).get("problem"):
                return                    # its own alert has said why
            turn = momentum_book.next_rebalance(state["last_processed"])[0] if state.get("last_processed") else None
            log(KIND, f"Momentum book: today's session ({today}) was not processed by {conf['job_until']}: "
                      f"NSE's bhavcopy for it was not in (the job's last session is {state.get('latest_session')}). "
                      f"The book stays at {state.get('last_processed')}; tomorrow evening's run catches up"
                      + (", and makes this month's rebalance at today's close." if turn == today else "."),
                level="warn")
