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


def decide_round(scanner, now, get_ltp, post=None, state_path=None, sleep=time.sleep):
    """Ask Jev about each shortlisted stock and open paper positions. Runs in a
    background thread from the engine; also callable directly in tests."""
    conf = cfg()
    today = now.date().isoformat()
    state = load_state(state_path)
    day = state["days"].setdefault(today, {"status": "deciding", "decisions": []})
    rows = {r["symbol"]: r for r in (scanner or {}).get("rows") or []}
    names = [s for s in ((scanner or {}).get("active") or []) if s in rows][:conf["max_names"]]
    done = {d["symbol"] for d in day["decisions"]}
    for sym in names:
        if sym in done:
            continue
        row = rows[sym]
        snap = build_state(row, (scanner or {}).get("market"), now)
        resp, err = system_one(snap, questions(), conf, post=post, sleep=sleep)
        if err:
            day["status"] = "jev_unavailable"
            day["error"] = err
            save_state(state, state_path)
            logger.warning(f"Jev book: Jev unavailable ({err[:120]})")
            return state
        d = {"symbol": sym, "asked_at": datetime.datetime.now().isoformat(timespec="seconds"),
             **parse_answers(resp), "scanner_side": row.get("side"), "state": snap}
        try:
            d["entry"] = float(get_ltp(sym))
        except Exception as exc:
            d["entry"], d["entry_error"] = None, str(exc)[:120]
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
                import data_provider
                decide_round(scanner, now, data_provider.get_ltp)
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
        if not day or day.get("closed") or _running["decide"]:
            return False
        import data_provider
        close_round(now, data_provider.get_ltp)
        return True
    except Exception:
        logger.exception("Jev book: square-off close failed")
        return False


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
    sessions = [k for k, v in state["days"].items() if v.get("closed")]
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
                                                           "entry", "exit", "move_bp", "net_bp", "scanner_net_bp")}
                                    for d in state["days"][last]["decisions"]]} if last else None),
    }
