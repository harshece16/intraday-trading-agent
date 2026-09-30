"""
The Jev book — a forward paper test of an LLM judge (TypeSafe Jev) on the
scanner's daily shortlist. Pre-registration: docs/research/prereg-jev-book.md
(trial 123). README section 86.

Once per trading day at the first tick at or after 09:45 IST, for each stock
on the scanner's active shortlist (up to 15), Jev is asked three typed
questions about a JSON snapshot of public market data — buy / short / skip,
the probability the price is higher at 15:08, and a position size — in one
request to TypeSafe's official System One API (https://api.typesafe.ai). A buy or
short "fills" at the live price when the answer returns and closes at the
live price at the 15:08 square-off, net of the engine's intraday round-trip
cost. The scanner's own side on the same stock-day is scored the same way,
so the book always shows whether Jev beats what the engine would do anyway.

Paper only: nothing here places an order, and Jev never sees keys, account
data or positions. The TypeSafe key comes from TYPESAFE_API_KEY or
backend/.typesafe_key.json (see typesafe_key.py); until one is stored, each
day is recorded as "Jev unavailable" and nothing is traded. The book stops itself
if, after 100 buy/short decisions, the cumulative net t is below -2.

While a round is open the page shows a live mark of its positions
(live_marks). That mark is for display only: it is never written to the state
file and never enters a score, the kill rule or the verdict. Those use the
15:08 close alone.
"""

import datetime
import json
import logging
import math
import os
import statistics as st
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "data", "jev_book_state.json")
logger = logging.getLogger("trading_bot")

DEFAULTS = {
    "enabled": True,
    "decide_at": "09:45",
    "max_names": 15,
    "notional": 100_000.0,
    "timeout_s": 90,
    "kill_after": 100,
    "kill_t": -2.0,
    "verdict_after_decisions": 300,
    "verdict_after_sessions": 60,
    "endpoint": "https://api.typesafe.ai/v1/systemone",
    "model": "jev-latest",
    "max_attempts": 4,
}

ACTION_Q = ("You are deciding an intraday paper trade in this NSE stock. A position opens now at the current "
            "price and closes at 15:08 IST today; there is no stop and no target; a round trip costs about 0.17% "
            "of the position. Choose the action with the best expected return after that cost.")
ACTION_OPTIONS = {"buy": "open a long position now",
                  "short": "open a short intraday position now",
                  "skip": "take no position: the expected move does not beat the cost"}
PUP_Q = "Will this stock's price at 15:08 IST today be higher than its current price?"
SIZE_Q = "How large should today's intraday position in this stock be, given your conviction and its risk?"
SIZE_LEVELS = ["no position", "half size", "normal size", "double size"]
SIZE_MULT = [0.0, 0.5, 1.0, 2.0]

_lock = threading.Lock()
_running = {"decide": False}


def cfg():
    try:
        import config
        return {**DEFAULTS, **getattr(config, "JEV_BOOK", {})}
    except Exception:
        return dict(DEFAULTS)


def load_state(path=None):
    path = path or STATE_PATH
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return {"days": {}, "status": "active", "status_reason": None}


def save_state(state, path=None):
    path = path or STATE_PATH
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, path)


# --- what Jev sees ---------------------------------------------------------------

ROW_FIELDS = ("symbol", "name", "industry", "ltp", "chg_pct", "gap_pct", "rvol", "rs_today", "vwap", "atr_pct",
              "daily_trend", "rs10", "pct_from_high", "pct_from_low", "turnover_cr", "beta", "catalyst", "event",
              "swing_patterns", "large_deals", "side", "final_score")
BRAIN_FIELDS = ("setup", "regime", "structure", "htf_trend", "bias", "rsi", "adx", "support", "resistance",
                "patterns", "news_headlines", "fundamentals_label")


def build_state(row, market, now):
    stock = {k: row.get(k) for k in ROW_FIELDS}
    stock["scanner_reasons"] = [r.get("text") for r in (row.get("reasons") or [])][:10]
    brain = row.get("brain") or {}
    stock["chart"] = {k: brain.get(k) for k in BRAIN_FIELDS}
    mkt = {k: (market or {}).get(k) for k in ("bias", "reasons", "nifty", "vix", "breadth", "fii_dii")}
    return {"time_ist": now.strftime("%Y-%m-%d %H:%M"), "exit_rule": "close at 15:08 IST today, no stop, no target",
            "round_trip_cost_pct": 0.17, "market": mkt, "stock": stock}


# --- calling Jev (TypeSafe's official HTTP API) ---------------------------------------

KEY_PATH = os.path.join(HERE, ".typesafe_key.json")


def api_key():
    """TYPESAFE_API_KEY, else backend/.typesafe_key.json. Never logged."""
    k = os.environ.get("TYPESAFE_API_KEY")
    if k:
        return k.strip()
    try:
        with open(KEY_PATH) as fh:
            return (json.load(fh).get("key") or "").strip() or None
    except (OSError, ValueError):
        return None


def questions():
    return {
        "action": {"type": "choice", "instructions": ACTION_Q, "criteria": dict(ACTION_OPTIONS)},
        "p_up": {"type": "noul", "instructions": PUP_Q},
        "size": {"type": "score", "instructions": SIZE_Q, "criteria": list(SIZE_LEVELS)},
    }


def system_one(state, qs, conf, post=None, key=None, sleep=time.sleep):
    """One System One request. Returns (response dict, error string). Retries
    429 / 529 / 5xx / connection errors with exponential backoff, honouring
    retry-after, as TypeSafe's API reference asks."""
    key = key or api_key()
    if not key:
        return None, "no TypeSafe API key stored (set TYPESAFE_API_KEY or run typesafe_key.py set)"
    if post is None:
        import requests
        post = requests.post
    body = {"state": state, "model": conf["model"], "questions": qs}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    err = None
    for attempt in range(conf["max_attempts"]):
        try:
            r = post(conf["endpoint"], json=body, headers=headers, timeout=conf["timeout_s"])
        except Exception as exc:
            err = f"{type(exc).__name__}: {str(exc)[:160]}"
            sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            try:
                return r.json(), None
            except ValueError:
                return None, "TypeSafe returned a non-JSON body"
        if r.status_code in (401, 403):
            return None, f"TypeSafe rejected the API key (HTTP {r.status_code})"
        if r.status_code == 422:
            return None, f"TypeSafe could not validate the request (HTTP 422): {r.text[:200]}"
        err = f"HTTP {r.status_code}"
        if r.status_code in (429, 529) or r.status_code >= 500:
            try:
                wait = float((r.headers or {}).get("retry-after") or 0)
            except (TypeError, ValueError):
                wait = 0
            sleep(max(wait, 2 ** attempt))
            continue
        return None, f"{err}: {r.text[:200]}"
    return None, f"TypeSafe unavailable after {conf['max_attempts']} attempts ({err})"


def parse_answers(resp):
    a = (resp or {}).get("answers") or {}
    act, pup, size = a.get("action") or {}, a.get("p_up") or {}, a.get("size") or {}
    choice = act.get("choice")
    level = None
    if isinstance(size.get("score"), (int, float)):
        level = max(0, min(len(SIZE_LEVELS) - 1, int(round(size["score"]))))
    return {"action": choice if choice in ACTION_OPTIONS else None,
            "action_probabilities": act.get("probabilities"), "action_confidence": act.get("confidence"),
            "p_up": pup.get("noul") if isinstance(pup.get("noul"), (int, float)) else None,
            "size_level": level, "size_score": size.get("score"), "size_confidence": size.get("confidence"),
            "model": (resp or {}).get("model"), "usage": (resp or {}).get("usage")}


# --- the daily round ------------------------------------------------------------------

def round_trip_bp():
    import config
    import costs
    return costs.round_trip_pct(DEFAULTS["notional"], config.COSTS) * 100.0


NO_LIVE_SESSION = "Kite is not connected, or its session ended at the 06:00 IST cutoff, so there is no live price"


def kite_live():
    """Whether Kite should give a live price right now (#158).

    data_provider.kite_data_active() alone is true whenever a token is stored
    and Kite has not yet rejected it. Zerodha ends every session at 06:00 IST,
    so on a morning without a reconnect it stayed true until the first price
    call failed. data_provider.kite_session_live() adds that expiry, the same
    clock the dashboard's Kite status and the pre-open reminder use."""
    import data_provider
    return bool(data_provider.kite_data_active() and data_provider.kite_session_live())


def live_ltp(symbol):
    """Kite's last traded price, or an exception. Never the ~15-minute-delayed
    yfinance fallback that data_provider.get_ltp uses when Kite isn't connected:
    the pre-registration fills at the live price, and a delayed fill against
    live headlines would leak information in Jev's favour (#151)."""
    import data_provider
    if not kite_live():
        raise RuntimeError(NO_LIVE_SESSION)
    key = f"NSE:{symbol}"
    try:
        return float(data_provider._get_kite().ltp([key])[key]["last_price"])
    except Exception as exc:
        data_provider._note_kite_failure(exc)
        raise


NO_LIVE_AT_DECISION = ("Kite had no live session when the round was due (not connected, or past the 06:00 IST "
                       "cutoff without a reconnect), so there were no live prices to fill at")
NO_LIVE_MID_ROUND = "Kite stopped giving live prices during the round (its session was rejected or ended)"


def _stop_round(state, day, state_path, status, error, remaining):
    """End today's round early. With no decision yet the day is recorded as
    `status` ("jev_unavailable" or "no_live_prices") and does not count. With
    decisions already made, the day stays open: they close at the 15:08
    square-off like any other round, and the interruption is recorded beside
    them (#158). Until then an interrupted day was marked "Jev unavailable",
    which the close skips, so its paper positions never closed."""
    if not day["decisions"]:
        day["status"] = status
        day["error"] = error
    else:
        day["status"] = "open"
        day["interrupted"] = {"at": datetime.datetime.now().isoformat(timespec="seconds"), "reason": status,
                              "error": error, "asked": len(day["decisions"]), "not_asked": list(remaining)}
    save_state(state, state_path)


def decide_round(scanner, now, get_ltp, post=None, state_path=None, sleep=time.sleep, live=None):
    """Ask Jev about each shortlisted stock and open paper positions. Runs in a
    background thread from the engine; also callable directly in tests. `live`
    says whether live prices exist; without them the day is recorded as "no
    live prices", Jev is not asked, and the day does not count (#151). It is
    asked again before each stock, so a Kite session that dies mid-round stops
    the round instead of spending a Jev call on each stock it can't fill (#158)."""
    conf = cfg()
    today = now.date().isoformat()
    state = load_state(state_path)
    day = state["days"].setdefault(today, {"status": "deciding", "decisions": []})
    if live is not None and not day["decisions"] and not live():
        _stop_round(state, day, state_path, "no_live_prices", NO_LIVE_AT_DECISION, [])
        logger.warning("Jev book: no live Kite prices at the decision time; today's round is skipped (#151)")
        return state
    rows = {r["symbol"]: r for r in (scanner or {}).get("rows") or []}
    names = [s for s in ((scanner or {}).get("active") or []) if s in rows][:conf["max_names"]]
    done = {d["symbol"] for d in day["decisions"]}
    todo = [s for s in names if s not in done]
    for n, sym in enumerate(todo):
        if live is not None and not live():
            _stop_round(state, day, state_path, "no_live_prices", NO_LIVE_MID_ROUND, todo[n:])
            logger.warning(f"Jev book: Kite stopped giving live prices after {len(day['decisions'])} stocks; "
                           "the round stops and the decisions made so far close at the square-off (#158)")
            return state
        row = rows[sym]
        snap = build_state(row, (scanner or {}).get("market"), now)
        resp, err = system_one(snap, questions(), conf, post=post, sleep=sleep)
        if err:
            _stop_round(state, day, state_path, "jev_unavailable", err, todo[n:])
            logger.warning(f"Jev book: Jev unavailable after {len(day['decisions'])} stocks ({err[:120]})"
                           + ("; the decisions made so far close at the square-off (#158)" if day["decisions"] else ""))
            return state
        d = {"symbol": sym, "asked_at": datetime.datetime.now().isoformat(timespec="seconds"),
             **parse_answers(resp), "scanner_side": row.get("side"), "state": snap}
        try:
            d["entry"] = float(get_ltp(sym))
        except Exception as exc:
            d["entry"], d["entry_error"] = None, str(exc)[:120]
            d["excluded"] = "no live entry price"
        day["decisions"].append(d)
        save_state(state, state_path)
    day["status"] = "open"
    save_state(state, state_path)
    return state


def close_round(now, get_ltp, state_path=None):
    """At the square-off, close today's paper positions and score them."""
    state = load_state(state_path)
    today = now.date().isoformat()
    day = state["days"].get(today)
    if not day or day.get("status") not in ("open", "deciding") or day.get("closed"):
        return state
    rt = round_trip_bp()
    for d in day["decisions"]:
        if d.get("entry") is None:
            continue
        try:
            d["exit"] = float(get_ltp(d["symbol"]))
        except Exception as exc:
            d["exit_error"] = str(exc)[:120]
            d["excluded"] = "no live exit price"
            continue
        move = (d["exit"] / d["entry"] - 1) * 1e4
        d["exit_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        sign = {"buy": 1, "short": -1}.get(d.get("action"))
        d["net_bp"] = (sign * move - rt) if sign else 0.0
        ssign = {"LONG": 1, "SHORT": -1}.get((d.get("scanner_side") or "").upper())
        d["scanner_net_bp"] = (ssign * move - rt) if ssign else 0.0
        d["move_bp"] = move
    day["closed"] = True
    day["status"] = "closed"
    _apply_kill_rule(state)
    save_state(state, state_path)
    return state


def _traded(state):
    out = []
    for date in sorted(state["days"]):
        for d in state["days"][date]["decisions"]:
            if d.get("action") in ("buy", "short") and d.get("net_bp") is not None:
                out.append((date, d))
    return out


def _t(xs):
    if len(xs) < 2:
        return None
    sd = st.stdev(xs)
    return st.mean(xs) / sd * math.sqrt(len(xs)) if sd > 0 else None


def _apply_kill_rule(state):
    conf = cfg()
    tr = [d["net_bp"] for _, d in _traded(state)]
    if len(tr) >= conf["kill_after"]:
        t = _t(tr)
        if t is not None and t < conf["kill_t"]:
            state["status"] = "switched_off"
            state["status_reason"] = (f"After {len(tr)} buy/short decisions the cumulative net is "
                                      f"{st.mean(tr):+.1f} bp per decision (t {t:.2f}), below the pre-registered kill line")


# --- engine hooks -----------------------------------------------------------------------

def maybe_decide(scanner, now, holiday=None):
    """Called every engine tick in the open phase. Starts today's round once."""
    try:
        conf = cfg()
        if not conf["enabled"] or holiday or now.weekday() >= 5 or now.strftime("%H:%M") < conf["decide_at"]:
            return False
        if not scanner or scanner.get("session_date") != now.date().isoformat() or not scanner.get("active"):
            return False
        state = load_state()
        if state.get("status") == "switched_off" or now.date().isoformat() in state["days"]:
            return False
        with _lock:
            if _running["decide"]:
                return False
            _running["decide"] = True

        def work():
            try:
                decide_round(scanner, now, live_ltp, live=kite_live)
            except Exception:
                logger.exception("Jev book: decision round failed")
            finally:
                _running["decide"] = False

        threading.Thread(target=work, name="jev-book", daemon=True).start()
        return True
    except Exception:
        logger.exception("Jev book: could not start the decision round")
        return False


def maybe_close(now):
    """Called in the square-off phase. Closes today's positions once."""
    try:
        state = load_state()
        day = state["days"].get(now.date().isoformat())
        # A skipped day ("Jev unavailable", "no live prices") has nothing to close. A round
        # interrupted after some decisions stays "open", so those close here (#158).
        if not day or day.get("closed") or _running["decide"] or day.get("status") not in ("open", "deciding"):
            return False
        close_round(now, live_ltp)
        return True
    except Exception:
        logger.exception("Jev book: square-off close failed")
        return False


# --- live mark of the open round (display only) ---------------------------------------------

MARK_TTL_S = 30                      # one Kite call serves every page refresh for this long
_mark_lock = threading.Lock()
_mark_cache = {"key": None, "at": 0.0, "value": None}


def _kite_quotes(keys):
    """Kite's last traded prices for `keys` ("NSE:SYMBOL"), or an exception.
    Never the delayed feed, for the same reason the fills don't use it (#151)."""
    import data_provider
    if not kite_live():
        raise RuntimeError(NO_LIVE_SESSION)
    try:
        return data_provider._get_kite().ltp(keys)
    except Exception as exc:
        data_provider._note_kite_failure(exc)
        raise


def _now_ist():
    from zoneinfo import ZoneInfo
    return datetime.datetime.now(ZoneInfo("Asia/Kolkata"))


def live_marks(state_path=None, quotes=None, now=None, clock=time.time):
    """Where today's open paper positions stand right now, at Kite's prices.

    Display only. It reads the state file and writes nothing; no figure here
    reaches summary(), the kill rule or the verdict. Returns None unless a
    round opened today is still open."""
    now = now or _now_ist()
    today = now.date().isoformat()
    day = load_state(state_path)["days"].get(today)
    if not day or day.get("closed") or day.get("status") not in ("open", "deciding"):
        return None
    priced_at_entry = [d for d in day["decisions"] if d.get("entry") is not None]
    held = [d for d in priced_at_entry if d.get("action") in ("buy", "short")]
    try:
        import config
        closes_at = config.SQUARE_OFF_TIME
    except Exception:
        closes_at = "15:08"
    out = {
        "date": today, "status": day["status"], "closes_at": closes_at,
        "opened_at": min((d["asked_at"] for d in day["decisions"] if d.get("asked_at")), default=None),
        "positions": len(held),
        "skips": sum(1 for d in day["decisions"] if d.get("action") == "skip"),
        "excluded": sum(1 for d in day["decisions"] if d.get("excluded")),
        "marked_at": None, "priced": 0, "mean_net_bp": None, "scanner_mean_net_bp": None,
        "reason": None, "marks": {},
    }
    if not priced_at_entry:
        return out

    key = (state_path or STATE_PATH, today, tuple(d["symbol"] for d in priced_at_entry))
    with _mark_lock:
        if _mark_cache["key"] == key and clock() - _mark_cache["at"] < MARK_TTL_S:
            return {**out, **_mark_cache["value"]}
    try:
        got = (quotes or _kite_quotes)(["NSE:" + d["symbol"] for d in priced_at_entry])
    except Exception as exc:
        fresh = {"reason": str(exc)[:160] or type(exc).__name__}
    else:
        rt, marks, jev, scan = round_trip_bp(), {}, [], []
        for d in priced_at_entry:
            q = (got or {}).get("NSE:" + d["symbol"]) or {}
            ltp = q.get("last_price")
            if not isinstance(ltp, (int, float)) or ltp <= 0:
                continue
            move = (ltp / d["entry"] - 1) * 1e4
            sign = {"buy": 1, "short": -1}.get(d.get("action"))
            ssign = {"LONG": 1, "SHORT": -1}.get((d.get("scanner_side") or "").upper())
            m = {"ltp": float(ltp), "move_bp": move,
                 "net_bp": (sign * move - rt) if sign else 0.0,
                 "scanner_net_bp": (ssign * move - rt) if ssign else 0.0}
            marks[d["symbol"]] = m
            if sign:
                jev.append(m["net_bp"])
                scan.append(m["scanner_net_bp"])
        fresh = {"marked_at": now.isoformat(timespec="seconds"), "priced": len(jev), "marks": marks,
                 "mean_net_bp": st.mean(jev) if jev else None,
                 "scanner_mean_net_bp": st.mean(scan) if scan else None,
                 "reason": None if marks else "Kite returned no price for these stocks"}
    with _mark_lock:
        _mark_cache.update(key=key, at=clock(), value=fresh)
    return {**out, **fresh}


def page(state_path=None, quotes=None, now=None):
    """What the Jev Book page shows: the scored summary and, while today's
    round is open, the live mark of its positions under "live"."""
    out = summary(state_path)
    try:
        out["live"] = live_marks(state_path, quotes=quotes, now=now)
    except Exception:
        logger.exception("Jev book: live mark failed")
        out["live"] = None
    return out


# --- the read side -------------------------------------------------------------------------

def summary(state_path=None):
    conf = cfg()
    state = load_state(state_path)
    tr = _traded(state)
    nets = [d["net_bp"] for _, d in tr]
    scan = [d["scanner_net_bp"] for _, d in tr]
    paired = [a - b for a, b in zip(nets, scan)]
    half = len(tr) // 2
    briers = [((d["p_up"] - (1 if d.get("move_bp", 0) > 0 else 0)) ** 2)
              for date in state["days"].values() for d in date["decisions"]
              if d.get("p_up") is not None and d.get("move_bp") is not None]
    by_size = {}
    for _, d in tr:
        lv = SIZE_LEVELS[d["size_level"]] if d.get("size_level") is not None else "unknown"
        by_size.setdefault(lv, []).append(d["net_bp"])
    # A session counts only if at least one decision was priced live at both ends (#151).
    sessions = [k for k, v in state["days"].items()
                if v.get("closed") and any(d.get("net_bp") is not None for d in v["decisions"])]
    last = sorted(state["days"])[-1] if state["days"] else None
    return {
        "enabled": conf["enabled"], "status": state.get("status"), "status_reason": state.get("status_reason"),
        "sessions_closed": len(sessions), "decisions": sum(len(v["decisions"]) for v in state["days"].values()),
        "traded": len(tr), "skips": sum(1 for v in state["days"].values() for d in v["decisions"] if d.get("action") == "skip"),
        "mean_net_bp": st.mean(nets) if nets else None, "t": _t(nets),
        "halves": [st.mean(nets[:half]) if half else None, st.mean(nets[half:]) if nets[half:] else None],
        "hit_rate": (sum(1 for x in nets if x > 0) / len(nets)) if nets else None,
        "scanner_mean_net_bp": st.mean(scan) if scan else None,
        "paired_vs_scanner_bp": st.mean(paired) if paired else None, "paired_t": _t(paired),
        "brier": st.mean(briers) if briers else None,
        "net_by_size": {k: {"n": len(v), "mean_bp": st.mean(v)} for k, v in by_size.items()},
        "round_trip_bp": round_trip_bp(),
        "input_tokens": sum(((d.get("usage") or {}).get("input_tokens") or 0)
                            for v in state["days"].values() for d in v["decisions"]),
        "key_stored": bool(api_key()), "model": conf["model"],
        "verdict_due": len(tr) >= conf["verdict_after_decisions"] or len(sessions) >= conf["verdict_after_sessions"],
        "last_day": ({"date": last, **{k: v for k, v in state["days"][last].items() if k != "decisions"},
                      "decisions": [{k: d.get(k) for k in ("symbol", "action", "p_up", "size_level", "scanner_side",
                                                           "entry", "exit", "move_bp", "net_bp", "scanner_net_bp", "excluded",
                                                           "asked_at")}
                                    for d in state["days"][last]["decisions"]]} if last else None),
    }
