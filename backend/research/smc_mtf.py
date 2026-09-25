"""3g — the "Smart Money" multi-timeframe setup, pre-registered in
docs/research/prereg-3g-smc-mtf.md (commit 48c36ed) before this file existed.

    daily bias  ->  4H liquidity sweep  ->  1H order block  ->  15m sweep + cemented candle

Every rule below is the pre-registration's, section by section. Higher
timeframes are aggregated from the 5-minute cache and a bar is used only once
it is complete. The bullish setup is the bearish one run on MIRRORED prices
(open/close negated, high and low swapped and negated), so the two sides share
one code path and cannot drift apart.

Usage:
    python research/smc_mtf.py stage0     # feasibility: reads no forward price, not a trial
    python research/smc_mtf.py stage1     # TRIAL 117 — selection sample only, one run
"""
import json
import math
import statistics as st
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUT = Path(__file__).resolve().parents[2] / "docs/research/smc_mtf_result.json"
DAYS = 730
N_TRIALS = 117                    # 116 before 3g + this one configuration
ENTRY_LAST_END = "14:30"          # the cemented candle must END no later than this
ROUND_TRIP_BP = 16.63             # config.COSTS round trip, as in the search pre-registration
OB_LOOKBACK = 6                   # 1H bars searched back from the peak bar for the OB candle
RR = 2.0

_4H = ("09:15", "13:15", "15:30")
_1H = ("09:15", "10:15", "11:15", "12:15", "13:15", "14:15", "15:15", "15:30")
_15M = tuple(f"{m // 60:02d}:{m % 60:02d}" for m in range(9 * 60 + 15, 15 * 60 + 31, 15))


# ------------------------------------------------------------------ bars ----

def _mins(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def _plus5(hhmm):
    m = _mins(hhmm) + 5
    return f"{m // 60:02d}:{m % 60:02d}"


def aggregate(bars5, bounds):
    """5m start-labelled bars -> bars on the slot boundaries `bounds` (HH:MM),
    in order, continuous across days. Each bar carries its date, start, end and
    `complete`: True once the data contains a 5m bar at or after its end, or
    its own last 5m bar ends exactly at the slot end. A partial final bar in a
    truncated series is therefore never treated as complete."""
    out, cur = [], None
    for b in bars5:
        d, hhmm = b["time"][:10], b["time"][11:16]
        m = _mins(hhmm)
        slot = None
        for i in range(len(bounds) - 1):
            if _mins(bounds[i]) <= m < _mins(bounds[i + 1]):
                slot = i
                break
        if slot is None:
            continue
        key = (d, slot)
        if cur is None or cur["key"] != key:
            if cur is not None:
                cur["complete"] = True                      # a later 5m bar exists
                out.append(cur)
            cur = {"key": key, "date": d, "start": bounds[slot], "end": bounds[slot + 1],
                   "open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"],
                   "complete": _plus5(hhmm) == bounds[slot + 1]}
        else:
            cur["high"] = max(cur["high"], b["high"])
            cur["low"] = min(cur["low"], b["low"])
            cur["close"] = b["close"]
            cur["complete"] = _plus5(hhmm) == bounds[slot + 1]
    if cur is not None:
        out.append(cur)
    return out


def daily(bars5):
    """Full-session OHLC by date. A day is used as D-1 or D-2 only when a
    later session exists, so it is always complete when read."""
    out = OrderedDict()
    for b in bars5:
        d = b["time"][:10]
        if d not in out:
            out[d] = {"open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"]}
        else:
            o = out[d]
            o["high"], o["low"], o["close"] = max(o["high"], b["high"]), min(o["low"], b["low"]), b["close"]
    return out


def mirror(bars5):
    """Prices negated with high and low swapped: a bullish pattern becomes the
    bearish one, exactly."""
    return [{**b, "open": -b["open"], "high": -b["low"], "low": -b["high"], "close": -b["close"]}
            for b in bars5]


# ------------------------------------------------------------- the rules ----

def bias(dd, d1, d2):
    """§1. 'bull', 'bear' or None, from the completed sessions D-1 and D-2."""
    if dd[d1]["close"] > dd[d2]["high"]:
        return "bull"
    if dd[d1]["close"] < dd[d2]["low"]:
        return "bear"
    return None


def _first_index(bars):
    """date -> index of that date's first bar."""
    out = {}
    for i, b in enumerate(bars):
        out.setdefault(b["date"], i)
    return out


def _bearish_setup(h4, k, h1, m15, day, i1, i15):
    """§2-§4, bearish, on (possibly mirrored) bars. h4[k] is the candidate
    sweep bar; i1/i15 map a date to its first 1H/15m index. Returns the entry
    dict or None."""
    if k < 1 or not h4[k]["complete"] or not h4[k - 1]["complete"]:
        return None
    sw, prev = h4[k], h4[k - 1]
    # §2 — a high sweep: trades above the previous 4H high, closes back below it
    if not (sw["high"] > prev["high"] and sw["close"] < prev["high"]):
        return None
    hstar = sw["high"]

    # §3 — 1H bars inside the sweep bar; the first containing H* is the peak bar
    j0 = i1.get(sw["date"])
    if j0 is None:
        return None
    inside = []
    for j in range(j0, len(h1)):
        b = h1[j]
        if b["date"] != sw["date"]:
            break
        if _mins(sw["start"]) <= _mins(b["start"]) and _mins(b["end"]) <= _mins(sw["end"]):
            inside.append(j)
    peak = next((j for j in inside if h1[j]["high"] == hstar), None)
    if peak is None:
        return None
    ob = next((j for j in range(peak, max(-1, peak - OB_LOOKBACK - 1), -1)
               if h1[j]["close"] > h1[j]["open"]), None)
    if ob is None:
        return None
    ob_open = h1[ob]["open"]

    conf = None
    for j in range(peak + 1, len(h1)):
        b = h1[j]
        if b["date"] > day or (b["date"] == day and _mins(b["end"]) > _mins(ENTRY_LAST_END)):
            return None                          # no confirmation in time for an entry
        if not b["complete"]:
            return None
        if b["high"] > hstar:
            return None                          # traded through H*: setup cancelled
        if b["close"] < ob_open:
            conf = j
            break
    if conf is None:
        return None
    premium = (hstar + min(h1[j]["low"] for j in range(peak, conf + 1))) / 2
    # the 15m entry waits for BOTH the 1H confirmation and the 4H sweep bar's
    # close: the sweep is not known until that bar completes
    conf_at = max((h1[conf]["date"], _mins(h1[conf]["end"])), (sw["date"], _mins(sw["end"])))

    # §4 — 15m sweep candle, then the cemented candle
    s = None
    for i in range(max(1, i15.get(sw["date"], len(m15))), len(m15)):
        b = m15[i]
        at = (b["date"], _mins(b["end"]))
        if at <= conf_at:
            continue
        if b["date"] > day or not b["complete"]:
            return None
        if b["high"] > hstar:
            return None                          # cancelled before entry
        if b["date"] != day:
            continue
        if _mins(b["end"]) > _mins(ENTRY_LAST_END):
            return None
        if s is not None and b["high"] <= s["high"] and b["close"] < s["low"]:
            return {"end": f"{day}T{b['end']}", "entry": b["close"], "stop": s["high"],
                    "ob_open": ob_open, "hstar": hstar, "sweep_slot": sw["start"],
                    "sweep_date": sw["date"]}
        p = m15[i - 1]
        if (b["high"] > p["high"] and b["high"] >= ob_open and b["high"] >= premium
                and (s is None or b["high"] > s["high"])):
            s = b                                # a new, higher sweep candle re-arms
    return None


def detect(bars5):
    """Every entry signal in a symbol's 5m series, in time order. One per
    session. Each is {'end', 'side', 'entry', 'stop', 'target', ...}; 'end' is
    the cemented 15m bar's end, the instant the order is placed."""
    dd = daily(bars5)
    days = list(dd)
    views = {"bear": bars5, "bull": mirror(bars5)}
    built = {}
    for kind, v in views.items():
        h4, h1, m15 = aggregate(v, _4H), aggregate(v, _1H), aggregate(v, _15M)
        built[kind] = (h4, h1, m15, {(x["date"], x["start"]): k for k, x in enumerate(h4)},
                       _first_index(h1), _first_index(m15))
    events = []
    for di in range(2, len(days)):
        day, d1, d2 = days[di], days[di - 1], days[di - 2]
        b = bias(dd, d1, d2)
        if b is None:
            continue
        h4, h1, m15, k4, i1, i15 = built["bear" if b == "bear" else "bull"]
        # candidate sweep bars for session D: B of D-1, then A of D
        cands = [k4[c] for c in ((d1, "13:15"), (day, "09:15")) if c in k4]
        found = [e for e in (_bearish_setup(h4, k, h1, m15, day, i1, i15) for k in cands) if e]
        if not found:
            continue
        e = min(found, key=lambda x: x["end"])
        sign = -1 if b == "bull" else 1          # undo the mirror
        entry, stop = sign * e["entry"], sign * e["stop"]
        risk = abs(stop - entry)
        target = entry - RR * risk if b == "bear" else entry + RR * risk
        events.append({"day": day, "end": e["end"], "side": "SHORT" if b == "bear" else "BUY",
                       "entry": entry, "stop": stop, "target": target,
                       "sweep": "B-of-D-1" if e["sweep_date"] == d1 else "A-of-D",
                       "stop_bp": risk / entry * 1e4})
    return events


# ------------------------------------------------------------- harness ----

def strategy_fn_for(events_by_symbol_first):
    """A strategy_fn for backtester.run_backtest() on 5m bars. The signal
    fires on the 5m bar that ENDS when the cemented 15m bar ends, so the fill
    is the 15m close. Stop and target go through the checklist-plan path the
    backtester already has; nothing else reads the plan."""
    def fn(window, prev_state=None, **params):
        evs = events_by_symbol_first.get(id(window[0]))
        bar = window[-1]
        state = {"exit_long": False, "exit_short": False}
        if not evs:
            return None, state
        key = f"{bar['time'][:10]}T{_plus5(bar['time'][11:16])}"
        e = evs.get(key)
        if e is None or abs(bar["close"] - e["entry"]) > 1e-9:
            return None, state
        leg = "long" if e["side"] == "BUY" else "short"
        state.update(entry_mode="checklist",
                     checklist={leg: {"stop": e["stop"], "target": e["target"], "size_factor": 1.0}})
        return e["side"], state
    return fn


def _load():
    import config
    import kite_history
    import universe
    from research import splits
    symbols = [r["symbol"] for r in universe.load()]
    pre = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=DAYS)
    selection, held_out = splits.selection_holdout(splits.sessions_in(pre))
    sel, _ = splits.slice_data(pre, {}, selection)
    del pre
    return sel, selection, held_out


def stage0():
    from research import splits
    sel, selection, held_out = _load()
    print(splits.describe_split("selection", selection))
    print(f"held-out: {len(held_out)} sessions, NOT loaded\n", flush=True)
    evs = [dict(e, symbol=s) for s, bars in sel.items() for e in detect(bars)]
    bps = sorted(e["stop_bp"] for e in evs)
    q = (lambda p: bps[min(len(bps) - 1, int(p * len(bps)))]) if bps else (lambda p: None)
    med = st.median(bps) if bps else None
    res = {
        "raw_signals": len(evs),
        "by_side": dict(Counter(e["side"] for e in evs)),
        "by_sweep": dict(Counter(e["sweep"] for e in evs)),
        "by_entry_hour": dict(sorted(Counter(e["end"][11:13] for e in evs).items())),
        "symbols_with_signals": len({e["symbol"] for e in evs}),
        "sessions_with_signals": len({e["day"] for e in evs}),
        "stop_bp": {"q25": q(0.25), "median": med, "q75": q(0.75), "min": bps[0] if bps else None},
        "implied_friction_r_at_median": ROUND_TRIP_BP / med if med else None,
        "gate_raw_ge_100": len(evs) >= 100,
        "gate_median_stop_ge_round_trip": bool(med and med >= ROUND_TRIP_BP),
    }
    res["stage0_pass"] = res["gate_raw_ge_100"] and res["gate_median_stop_ge_round_trip"]
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    out["stage0"] = res
    OUT.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


def stage1():
    import backtester
    import config
    import evaluation
    from research import splits
    from research.search_diagnostics import diagnose
    from strategy_engine import STRATEGY_FUNCTIONS
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    if not out.get("stage0", {}).get("stage0_pass"):
        raise SystemExit("stage 0 has not passed — stage 1 must not run")
    if "stage1" in out:
        raise SystemExit("stage 1 already ran — one run per hypothesis")
    sel, selection, _ = _load()
    first, second = splits.halves(selection)
    events = {s: detect(bars) for s, bars in sel.items()}   # causal: each uses only earlier bars
    risk_cfg = {**config.RISK, "min_confidence_to_trade": 0}
    res, all_trades, candles_all = {}, [], {}
    for name, sess in (("first", first), ("second", second)):
        keep = set(sess)
        half, _ = splits.slice_data(sel, {}, sess)
        by_first = {id(c[0]): {e["end"]: e for e in events[s] if e["day"] in keep}
                    for s, c in half.items() if c}
        STRATEGY_FUNCTIONS["_smc_mtf"] = strategy_fn_for(by_first)
        try:
            trades, _ = backtester.run_backtest(sorted(half), "_smc_mtf", {}, risk_cfg, "5m", DAYS,
                                                costs_cfg=config.COSTS, preloaded=half,
                                                allowed_by_day=None, scorecard=[])
        finally:
            STRATEGY_FUNCTIONS.pop("_smc_mtf", None)
        rs = [t["pnl"] / (t["risk_per_share"] * t["qty"]) for t in trades if t.get("risk_per_share") and t.get("qty")]
        res[name] = _summ(rs)
        all_trades += trades
        for s, c in half.items():
            candles_all.setdefault(s, []).extend(c)
    pooled_rs = [t["pnl"] / (t["risk_per_share"] * t["qty"]) for t in all_trades if t.get("risk_per_share") and t.get("qty")]
    pooled = _summ(pooled_rs)
    dsr = evaluation.deflated_sharpe_ratio(pooled_rs, N_TRIALS) if len(pooled_rs) >= 2 else {"dsr": None}
    ok = (pooled["net_r"] is not None and pooled["net_r"] > 0 and (pooled["t"] or 0) > 2
          and (res["first"]["net_r"] or -1) > 0 and (res["second"]["net_r"] or -1) > 0
          and (dsr.get("dsr") or 0) >= 0.95 and pooled["n"] >= 100)
    out["stage1"] = {"trial": 117, "first": res["first"], "second": res["second"], "pooled": pooled,
                     "dsr": dsr.get("dsr"), "pass": ok,
                     "diagnostics": diagnose(all_trades, candles_all),
                     "halves": [[first[0], first[-1], len(first)], [second[0], second[-1], len(second)]]}
    OUT.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out["stage1"], indent=1, default=float))


def _summ(rs):
    if len(rs) < 2:
        return {"n": len(rs), "net_r": rs[0] if rs else None, "t": None}
    m, sd = st.mean(rs), st.stdev(rs)
    return {"n": len(rs), "net_r": m, "sd": sd, "t": m / (sd / math.sqrt(len(rs))) if sd else None,
            "win_pct": 100 * sum(r > 0 for r in rs) / len(rs)}


if __name__ == "__main__":
    {"stage0": stage0, "stage1": stage1}[sys.argv[1]]()
