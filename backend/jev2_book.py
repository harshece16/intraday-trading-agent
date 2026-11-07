"""
Jev 2 — a second forward paper test of an LLM judge (TypeSafe Jev), beside
Jev 1 (jev_book.py) and leaving it untouched. Pre-registration:
docs/research/prereg-jev2-book.md. README section 128.

What differs from Jev 1, all fixed in the pre-registration:

- a **blind state**: the scanner's side, score, reasons and the chart labels
  are withheld; only measurements, three dated headlines, the market summary
  and the cost line are sent (build_state);
- **seven narrow Nouls in two wordings each**, fourteen questions in one
  request per stock, combined in code by a frozen equal-weight rule
  (combine): buy if the combined probability is >= 0.65, short if <= 0.35,
  skip otherwise, and skip when the move looks exhausted (>= 0.70). No size;
- **all 25 names** on the day's list (Jev 1 asks the first 15, the shared
  names);
- **fills shared with Jev 1** on the shared names: Jev 2 reuses the Kite
  price Jev 1 recorded for the same stock-day when both read the same scan,
  so the paired comparison is exact; otherwise it fetches its own live price;
- the model pinned to jev-1.13.0, logged per decision;
- **session-clustered t** for the verdict, N_family = 3 (t >= 2.39).

The round starts once Jev 1's round for the day has ended, on the scan
captured at the first tick at or after 09:45, and in its own thread and
try/except: nothing here can stop Jev 1 or the engine. This module only
reads Jev 1's state file (jev_book.STATE_PATH); it never writes it. Paper
only: nothing here places an order, and Jev never sees keys, account data or
positions.
"""

import copy
import datetime
import json
import logging
import math
import os
import statistics as st
import threading
import time

import jev_book

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "data", "jev2_book_state.json")
logger = logging.getLogger("trading_bot")

DEFAULTS = {
    "enabled": True,
    "decide_at": "09:45",
    "decide_until": "10:00",      # a round not started by then is recorded as missed
    "max_names": 25,
    "notional": 100_000.0,
    "timeout_s": 90,
    "kill_after": 100,
    "kill_t": -2.0,
    "verdict_after_decisions": 300,
    "verdict_after_sessions": 60,
    "endpoint": "https://api.typesafe.ai/v1/systemone",
    "model": "jev-1.13.0",         # pinned; jev-latest is an alias that moves
    "max_attempts": 4,
    "buy_at": 0.65,                # p_combined >= buy_at -> buy
    "short_at": 0.35,              # p_combined <= short_at -> short
    "exhausted_veto": 0.70,        # move_exhausted >= this -> skip either way
}

# The seven questions, each a Noul in two wordings (A, B). Fixed in the
# pre-registration; the probability used is the mean of the two wordings.
QUESTIONS = (
    ("news_positive",
     "The headlines carry news that a trader would read as good for this stock's price today.",
     "Today's headlines about this company are favourable for its share price."),
    ("news_negative",
     "The headlines carry news that a trader would read as bad for this stock's price today.",
     "Today's headlines about this company are unfavourable for its share price."),
    ("strength_extending",
     "The stock is trading above its VWAP and above its opening range on heavier volume than usual, and is more "
     "likely to extend higher than to fade by 15:08.",
     "Intraday strength: price above VWAP and the opening-range high with high relative volume, likely to continue "
     "up into the close."),
    ("weakness_extending",
     "The stock is trading below its VWAP and below its opening range on heavier volume than usual, and is more "
     "likely to extend lower than to bounce by 15:08.",
     "Intraday weakness: price below VWAP and the opening-range low with high relative volume, likely to continue "
     "down into the close."),
    ("sector_up",
     "The stock's sector and the NIFTY are both rising today, which supports a further rise in this stock into "
     "the close.",
     "The market and this stock's sector are up today, a tailwind for the stock until 15:08."),
    ("sector_down",
     "The stock's sector and the NIFTY are both falling today, which supports a further fall in this stock into "
     "the close.",
     "The market and this stock's sector are down today, a headwind for the stock until 15:08."),
    ("move_exhausted",
     "Today's move in this stock is already large for its usual range, so the rest of the day is more likely to "
     "retrace than to extend.",
     "The stock has already moved more than it usually does in a day; the move looks spent."),
)
KEYS = tuple(q[0] for q in QUESTIONS)
BULLISH = ("news_positive", "strength_extending", "sector_up")
BEARISH = ("news_negative", "weakness_extending", "sector_down")
UNDATED_AGE_H = 24.0               # news_sentiment gives an unparsable date this age; such items are dropped

_lock = threading.Lock()
_running = {"decide": False}
_pending = {"date": None, "scanner": None, "at": None}   # the scan captured at the first tick >= 09:45


def cfg():
    try:
        import config
        return {**DEFAULTS, **getattr(config, "JEV2_BOOK", {})}
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


# --- what Jev 2 sees: the blind state ---------------------------------------------------------

NUMBER_FIELDS = ("symbol", "name", "industry", "ltp", "chg_pct", "gap_pct", "rvol", "rs_today", "vwap",
                 "sector_chg_pct", "atr_pct", "rs10", "pct_from_high", "pct_from_low", "turnover_cr", "beta",
                 "event", "large_deals")
# `catalyst` is news_sentiment.market_catalysts' whole output for the stock (a sentiment score, per-headline
# scores, URLs and the raw age_h with its undated sentinel). It is not sent: news reaches Jev 2 only through
# headlines() (prereg-jev2-book.md, clarification 1).
CHART_NUMBERS = ("rsi", "adx", "support", "resistance")
WITHHELD = ("side", "score_side", "score", "final_score", "long_score", "short_score", "reasons", "shadow_side",
            "sector_trend", "daily_trend", "swing_patterns", "long_only", "setup", "bias", "regime", "structure",
            "htf_trend", "patterns", "fundamentals_label", "trend", "catalyst", "url", "llm_scored", "age_h")


def headlines(row):
    """The row's headlines with a parsable age, at most three, as
    {title, publisher, hours_before_decision}. An item whose publication time
    could not be parsed carries age_h = 24.0 (news_sentiment._aggregate) and
    may in truth be newer than the fill, so it is dropped; a genuinely
    24.0-hour-old item goes with it (pre-registration, Headlines)."""
    out = []
    for h in ((row.get("brain") or {}).get("news_headlines") or [])[:3]:
        age = h.get("age_h") if isinstance(h, dict) else None
        if not isinstance(age, (int, float)) or float(age) == UNDATED_AGE_H:
            continue
        out.append({"title": h.get("title"), "publisher": h.get("publisher"), "hours_before_decision": float(age)})
    return out


def build_state(row, market, now):
    stock = {k: row.get(k) for k in NUMBER_FIELDS}
    ltp, vwap = row.get("ltp"), row.get("vwap")
    stock["vwap_distance_pct"] = round((ltp / vwap - 1) * 100, 3) if ltp and vwap else None
    stock["opening_range"] = {"high": row.get("or_high"), "low": row.get("or_low")}
    brain = row.get("brain") or {}
    for k in CHART_NUMBERS:
        stock[k] = brain.get(k)
    stock["headlines"] = headlines(row)
    m = market or {}
    nifty = m.get("nifty") or {}
    breadth = m.get("breadth") or {}
    fii = m.get("fii_dii") or {}
    mkt = {"nifty": {k: nifty.get(k) for k in ("ltp", "chg_pct", "above_open")}, "vix": m.get("vix"),
           "breadth": {k: breadth.get(k) for k in ("adv", "dec", "pct_adv")},
           "fii_dii": {k: fii.get(k) for k in ("date", "fii_net_cr", "dii_net_cr")}}
    return {"time_ist": now.strftime("%Y-%m-%d %H:%M"), "exit_rule": "close at 15:08 IST today, no stop, no target",
            "round_trip_cost_pct": 0.17, "market": mkt, "stock": stock}


def questions():
    qs = {}
    for key, a, b in QUESTIONS:
        qs[key + "_a"] = {"type": "noul", "instructions": a}
        qs[key + "_b"] = {"type": "noul", "instructions": b}
    return qs


def parse_answers(resp):
    """The fourteen raw Nouls, their seven means, the model and the usage."""
    a = (resp or {}).get("answers") or {}
    raw, p = {}, {}
    for key in KEYS:
        vals = []
        for suffix in ("_a", "_b"):
            v = (a.get(key + suffix) or {}).get("noul")
            raw[key + suffix] = v if isinstance(v, (int, float)) else None
            if isinstance(v, (int, float)):
                vals.append(float(v))
        p[key] = st.mean(vals) if vals else None
    return {"p": p, "raw": raw, "model": (resp or {}).get("model"), "usage": (resp or {}).get("usage")}


def combine(p, conf=None):
    """The frozen rule. Returns (action, p_combined, S); action None when a
    directional answer is missing."""
    conf = conf or cfg()
    if any(p.get(k) is None for k in BULLISH + BEARISH):
        return None, None, None
    s = sum(p[b] - p[r] for b, r in zip(BULLISH, BEARISH)) / 3.0
    pc = 0.5 + s / 2.0
    exhausted = p.get("move_exhausted")
    # The veto can't be checked without the answer, so the decision is a skip (clarification 1, item 3).
    if exhausted is None or exhausted >= conf["exhausted_veto"]:
        return "skip", pc, s
    if pc >= conf["buy_at"]:
        return "buy", pc, s
    if pc <= conf["short_at"]:
        return "short", pc, s
    return "skip", pc, s


# --- Jev 1's record, read only ---------------------------------------------------------------------

def jev1_day(date):
    """Jev 1's record of `date`, a copy, or None. Read only: this module never
    writes jev_book's state."""
    try:
        return copy.deepcopy(jev_book.load_state(jev_book.STATE_PATH)["days"].get(date))
    except Exception:
        logger.exception("Jev 2 book: could not read Jev 1's state")
        return None


def jev1_finished(date):
    """Whether Jev 1's round for `date` has ended, so Jev 2 may start. True
    when Jev 1 is disabled or switched off, or its state can't be read: then
    Jev 2 runs on its own fills."""
    try:
        if not jev_book.cfg()["enabled"]:
            return True
        s1 = jev_book.load_state(jev_book.STATE_PATH)
        if s1.get("status") == "switched_off":
            return True
        return date in s1["days"] and not jev_book._running["decide"]
    except Exception:
        return True


def same_scan(d1, row):
    """Jev 1's decision read the same scan as Jev 2's captured row: same last
    price and VWAP for the stock."""
    try:
        s = d1["state"]["stock"]
        return s.get("ltp") == row.get("ltp") and s.get("vwap") == row.get("vwap")
    except (KeyError, TypeError):
        return False


# --- the daily round --------------------------------------------------------------------------------

def _record_skip(state, day, state_path, status, error, remaining):
    if not day["decisions"]:
        day["status"] = status
        day["error"] = error
    else:
        day["status"] = "open"
        day["interrupted"] = {"at": datetime.datetime.now().isoformat(timespec="seconds"), "reason": status,
                              "error": error, "asked": len(day["decisions"]), "not_asked": list(remaining)}
    save_state(state, state_path)


def decide_round(scanner, now, get_ltp, post=None, state_path=None, sleep=time.sleep, live=None, jev1=None):
    """Ask Jev 2's fourteen Nouls about every stock on the day's list and open
    paper positions. `jev1` is Jev 1's record of the day (jev1_day), whose
    fills are reused on the shared names when both books read the same scan.
    Runs in a background thread from the engine; callable directly in tests."""
    conf = cfg()
    today = now.date().isoformat()
    state = load_state(state_path)
    day = state["days"].setdefault(today, {"status": "deciding", "decisions": []})
    if live is not None and not day["decisions"] and not live():
        _record_skip(state, day, state_path, "no_live_prices", jev_book.NO_LIVE_AT_DECISION, [])
        logger.warning("Jev 2 book: no live Kite prices at the decision time; today's round is skipped")
        return state
    rows = {r["symbol"]: r for r in (scanner or {}).get("rows") or []}
    names = [s for s in ((scanner or {}).get("active") or []) if s in rows][:conf["max_names"]]
    j1 = {d["symbol"]: d for d in ((jev1 or {}).get("decisions") or []) if d.get("symbol")}
    done = {d["symbol"] for d in day["decisions"]}
    todo = [s for s in names if s not in done]
    for n, sym in enumerate(todo):
        if live is not None and not live():
            _record_skip(state, day, state_path, "no_live_prices", jev_book.NO_LIVE_MID_ROUND, todo[n:])
            logger.warning(f"Jev 2 book: Kite stopped giving live prices after {len(day['decisions'])} stocks")
            return state
        row = rows[sym]
        snap = build_state(row, (scanner or {}).get("market"), now)
        resp, err = jev_book.system_one(snap, questions(), conf, post=post, sleep=sleep)
        if err:
            _record_skip(state, day, state_path, "jev_unavailable", err, todo[n:])
            logger.warning(f"Jev 2 book: Jev unavailable after {len(day['decisions'])} stocks ({err[:120]})")
            return state
        ans = parse_answers(resp)
        action, pc, s = combine(ans["p"], conf)
        d = {"symbol": sym, "asked_at": datetime.datetime.now().isoformat(timespec="seconds"),
             "action": action, "p_combined": pc, "S": s, **ans,
             "scanner_side": jev_book.scanner_side(row), "shared": sym in j1, "state": snap}
        d1 = j1.get(sym)
        if d1 and d1.get("entry") is not None and same_scan(d1, row):
            d["entry"], d["fill_source"] = float(d1["entry"]), "jev1"
        else:
            d["fill_source"] = "own"
            try:
                d["entry"] = float(get_ltp(sym))
            except Exception as exc:
                d["entry"], d["entry_error"] = None, str(exc)[:120]
                d["excluded"] = "no live entry price"
        if action is None:
            d["excluded"] = "a directional answer was missing"
        elif ans["p"].get("move_exhausted") is None:
            d["skip_reason"] = "move_exhausted was not answered, so the veto could not be checked"
        day["decisions"].append(d)
        save_state(state, state_path)
    day["status"] = "open"
    save_state(state, state_path)
    return state


def close_round(now, get_ltp, state_path=None, jev1=None):
    """At the square-off, close today's paper positions and score them. A
    shared name reuses Jev 1's recorded exit when there is one."""
    state = load_state(state_path)
    today = now.date().isoformat()
    day = state["days"].get(today)
    if not day or day.get("status") not in ("open", "deciding") or day.get("closed"):
        return state
    rt = jev_book.round_trip_bp()
    j1 = {d["symbol"]: d for d in ((jev1 or {}).get("decisions") or []) if d.get("symbol")}
    for d in day["decisions"]:
        if d.get("entry") is None or d.get("excluded"):
            continue
        d1 = j1.get(d["symbol"])
        if d1 and d1.get("exit") is not None and d.get("fill_source") == "jev1":
            d["exit"], d["exit_source"] = float(d1["exit"]), "jev1"
        else:
            d["exit_source"] = "own"
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


# --- statistics --------------------------------------------------------------------------------------

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


def clustered_t(xs, groups):
    """t of the mean with a cluster-robust standard error, one cluster per
    session: variance of the mean = G/(G-1) * sum_g (sum of g's residuals)^2
    / N^2. None with fewer than two clusters."""
    n = len(xs)
    if n < 2:
        return None
    m = st.mean(xs)
    sums = {}
    for x, g in zip(xs, groups):
        sums[g] = sums.get(g, 0.0) + (x - m)
    G = len(sums)
    if G < 2:
        return None
    var = (G / (G - 1)) * sum(s * s for s in sums.values()) / (n * n)
    return m / math.sqrt(var) if var > 0 else None


def _apply_kill_rule(state):
    conf = cfg()
    tr = [d["net_bp"] for _, d in _traded(state)]
    if len(tr) >= conf["kill_after"]:
        t = _t(tr)
        if t is not None and t < conf["kill_t"]:
            state["status"] = "switched_off"
            state["status_reason"] = (f"After {len(tr)} buy/short decisions the cumulative net is "
                                      f"{st.mean(tr):+.1f} bp per decision (t {t:.2f}), below the pre-registered kill line")


# --- engine hooks ------------------------------------------------------------------------------------

def _record_missed(today, why):
    state = load_state()
    if today not in state["days"]:
        state["days"][today] = {"status": "missed", "decisions": [], "error": why}
        save_state(state)
        logger.warning(f"Jev 2 book: today's round is recorded as missed: {why}")


def maybe_decide(scanner, now, holiday=None):
    """Called every engine tick in the open phase. Captures the scan at the
    first tick at or after 09:45, then starts today's round once Jev 1's has
    ended. Never raises."""
    try:
        conf = cfg()
        hhmm = now.strftime("%H:%M")
        if not conf["enabled"] or holiday or now.weekday() >= 5 or hhmm < conf["decide_at"]:
            return False
        today = now.date().isoformat()
        state = load_state()
        if state.get("status") == "switched_off" or today in state["days"]:
            return False
        with _lock:
            if _running["decide"]:
                return False
            if _pending["date"] != today:
                # The deadline comes first: a day whose scan never produced a list must still be
                # recorded as missed, not left out of the record (#318).
                if hhmm > conf["decide_until"]:
                    _record_missed(today, f"no round had started by {conf['decide_until']} (engine restarted, "
                                          "or no list at 09:45)")
                    return False
                if not scanner or scanner.get("session_date") != today or not scanner.get("active"):
                    return False
                _pending.update(date=today, scanner=scanner, at=now)
            if not jev1_finished(today):
                if hhmm > conf["decide_until"]:
                    _record_missed(today, f"Jev 1's round had not ended by {conf['decide_until']}")
                return False
            _running["decide"] = True
            snap, at = _pending["scanner"], _pending["at"]

        def work():
            try:
                decide_round(snap, at, jev_book.live_ltp, live=jev_book.kite_live, jev1=jev1_day(today))
            except Exception:
                logger.exception("Jev 2 book: decision round failed")
            finally:
                _running["decide"] = False

        threading.Thread(target=work, name="jev2-book", daemon=True).start()
        return True
    except Exception:
        logger.exception("Jev 2 book: could not start the decision round")
        return False


def maybe_close(now):
    """Called in the square-off phase, after Jev 1's close. Closes today's
    positions once. Never raises."""
    try:
        state = load_state()
        today = now.date().isoformat()
        day = state["days"].get(today)
        if not day or day.get("closed") or _running["decide"] or day.get("status") not in ("open", "deciding"):
            return False
        close_round(now, jev_book.live_ltp, jev1=jev1_day(today))
        return True
    except Exception:
        logger.exception("Jev 2 book: square-off close failed")
        return False


# --- the read side -------------------------------------------------------------------------------------

def _jev1_nets(jev1_state):
    """Jev 1's closed net_bp by (date, symbol), from its state, read only."""
    out = {}
    for date, day in ((jev1_state or {}).get("days") or {}).items():
        for d in day.get("decisions") or []:
            if d.get("net_bp") is not None and not d.get("excluded"):
                out[(date, d.get("symbol"))] = float(d["net_bp"])
    return out


def jev1_by_band(jev1_state, band=0.15):
    """Information only (pre-registration, pass rule item 5): Jev 1's closed
    buy/short decisions cut by |p_up - 0.5| inside and outside the band."""
    inside, outside = [], []
    for day in ((jev1_state or {}).get("days") or {}).values():
        for d in day.get("decisions") or []:
            if d.get("action") in ("buy", "short") and d.get("net_bp") is not None and d.get("p_up") is not None:
                (outside if abs(d["p_up"] - 0.5) >= band else inside).append(float(d["net_bp"]))
    return {"band": band,
            "inside": {"n": len(inside), "mean_bp": st.mean(inside) if inside else None},
            "outside": {"n": len(outside), "mean_bp": st.mean(outside) if outside else None}}


def summary(state_path=None, jev1_state=None):
    conf = cfg()
    state = load_state(state_path)
    if jev1_state is None:
        try:
            jev1_state = jev_book.load_state(jev_book.STATE_PATH)
        except Exception:
            jev1_state = {"days": {}}
    tr = _traded(state)
    dates = [date for date, _ in tr]
    nets = [d["net_bp"] for _, d in tr]
    # Pass rule item 3, Jev 2 - the scanner's side: every closed decision, a skip at 0 (clarification 1, item 2).
    scored = [(date, d) for date in sorted(state["days"]) for d in state["days"][date]["decisions"]
              if d.get("net_bp") is not None and d.get("scanner_net_bp") is not None]
    scan_dates = [date for date, _ in scored]
    scan = [d["scanner_net_bp"] for _, d in scored]
    paired_scan = [d["net_bp"] - d["scanner_net_bp"] for _, d in scored]
    # Jev 2 - Jev 1 on the shared names: every Jev 2 decision (a skip is 0) on a stock-day Jev 1 also scored.
    j1 = _jev1_nets(jev1_state)
    pj, pj_dates = [], []
    for date in sorted(state["days"]):
        for d in state["days"][date]["decisions"]:
            if d.get("shared") and d.get("net_bp") is not None and (date, d["symbol"]) in j1:
                pj.append(d["net_bp"] - j1[(date, d["symbol"])])
                pj_dates.append(date)
    half = len(tr) // 2
    all_dec = [(date, d) for date in sorted(state["days"]) for d in state["days"][date]["decisions"]]
    closed = [d for _, d in all_dec if d.get("move_bp") is not None]
    briers = {}
    for key in BULLISH + ("p_combined",):
        xs = [((d["p_combined"] if key == "p_combined" else d["p"].get(key)) - (1 if d["move_bp"] > 0 else 0)) ** 2
              for d in closed if (d.get("p_combined") if key == "p_combined" else (d.get("p") or {}).get(key)) is not None]
        briers[key] = st.mean(xs) if xs else None
    for key in BEARISH:
        xs = [(d["p"][key] - (1 if d["move_bp"] < 0 else 0)) ** 2 for d in closed if (d.get("p") or {}).get(key) is not None]
        briers[key] = st.mean(xs) if xs else None
    shared = [d["net_bp"] for _, d in tr if d.get("shared")]
    extra = [d["net_bp"] for _, d in tr if not d.get("shared")]
    own = [d["net_bp"] for _, d in tr
           if not (d.get("shared") and "own" in (d.get("fill_source"), d.get("exit_source")))]
    sessions = [k for k, v in state["days"].items()
                if v.get("closed") and any(d.get("net_bp") is not None for d in v["decisions"])]
    n_dec = len(all_dec)
    skips = sum(1 for _, d in all_dec if d.get("action") == "skip")
    last = sorted(state["days"])[-1] if state["days"] else None
    verdict_due = len(tr) >= conf["verdict_after_decisions"] or len(sessions) >= conf["verdict_after_sessions"]
    return {
        "enabled": conf["enabled"], "status": state.get("status"), "status_reason": state.get("status_reason"),
        "sessions_closed": len(sessions), "decisions": n_dec, "traded": len(tr), "skips": skips,
        "skip_rate": (skips / n_dec) if n_dec else None,
        "mean_net_bp": st.mean(nets) if nets else None, "t": _t(nets), "t_clustered": clustered_t(nets, dates),
        "halves": [st.mean(nets[:half]) if half else None, st.mean(nets[half:]) if nets[half:] else None],
        "hit_rate": (sum(1 for x in nets if x > 0) / len(nets)) if nets else None,
        "scanner_mean_net_bp": st.mean(scan) if scan else None, "scanner_n": len(scan),
        "paired_vs_scanner_bp": st.mean(paired_scan) if paired_scan else None,
        "paired_t": _t(paired_scan), "paired_t_clustered": clustered_t(paired_scan, scan_dates),
        "paired_vs_jev1_bp": st.mean(pj) if pj else None, "paired_vs_jev1_n": len(pj),
        "paired_vs_jev1_t": _t(pj), "paired_vs_jev1_t_clustered": clustered_t(pj, pj_dates),
        "shared_mean_net_bp": st.mean(shared) if shared else None, "shared_n": len(shared),
        "extra_mean_net_bp": st.mean(extra) if extra else None, "extra_n": len(extra),
        "mean_net_bp_without_own_shared_fills": st.mean(own) if own else None,
        "briers": briers,
        "round_trip_bp": jev_book.round_trip_bp(),
        "input_tokens": sum(((d.get("usage") or {}).get("input_tokens") or 0) for _, d in all_dec),
        "models": sorted({d["model"] for _, d in all_dec if d.get("model")}),
        "key_stored": bool(jev_book.api_key()), "model": conf["model"],
        "thresholds": {"buy_at": conf["buy_at"], "short_at": conf["short_at"], "exhausted_veto": conf["exhausted_veto"]},
        "verdict_due": verdict_due,
        # Pre-registration, pass rule item 5: reported at Jev 2's verdict, not before. Until then the
        # page and the API carry nothing of Jev 1's record cut this way.
        "jev1_by_band": jev1_by_band(jev1_state) if verdict_due else None,
        "last_day": ({"date": last, **{k: v for k, v in state["days"][last].items() if k != "decisions"},
                      "decisions": [{**{k: d.get(k) for k in ("symbol", "action", "p_combined", "S", "p", "scanner_side",
                                                                "shared", "fill_source", "exit_source", "entry", "exit",
                                                                "move_bp", "net_bp", "scanner_net_bp", "excluded", "skip_reason",
                                                                "asked_at", "model")}}
                                    for d in state["days"][last]["decisions"]]} if last else None),
    }


def page(state_path=None):
    """What the Jev 2 page shows: the scored summary. No live mark: the
    record is the 15:08 close alone."""
    return summary(state_path)
