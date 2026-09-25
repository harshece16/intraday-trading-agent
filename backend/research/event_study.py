"""Event study on NSE filings — research look L35, pre-registered in
docs/research/prereg-event-study.md and committed with this script before
the run. A measurement, not a trial: does a NIFTY 100 stock move by more
than the 16.63 bp round trip in a tradable window after a filing?

Selection sample only; the held-out window is never loaded. Raw filings are
cached to docs/research/data/events_raw.json so a fetch failure can be
completed without changing anything already fetched.
"""
import json
import math
import random
import statistics as st
import sys
import time
from bisect import bisect_left
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import kite_history
import nse_feed
import universe
from research import splits
from sentiment_lexicon import score_text

DATA = Path(__file__).resolve().parents[2] / "docs/research/data"
RAW = DATA / "events_raw.json"
OUT = Path(__file__).resolve().parents[2] / "docs/research/event_study_result.json"
HURDLE_BP = 16.63
CLASSES = [
    ("RESULTS", ("financial result", "results")),
    ("ORDERS", ("bagging", "receiving of order", "order", "contract")),
    ("DEALS", ("acquisition", "investment", "joint venture", "merger", "amalgamation", "demerger")),
    ("CAPITAL", ("buy back", "buyback", "bonus", "dividend", "rights", "qip", "preferential")),
    ("NEGATIVE", ("default", "fraud", "insolvency", "pledge", "resignation", "litigation", "penalty", "sebi")),
]
WINDOWS = ("30m", "60m", "close")


def classify(desc):
    d = (desc or "").lower()
    for name, keys in CLASSES:
        if any(k in d for k in keys):
            return name
    return "OTHER"


def sentiment_sign(desc, text):
    d = (desc or "").lower()
    tilt = next((w for k, w in nse_feed.TILTS if k in d), 0.0)
    score = max(-1.0, min(1.0, tilt + 0.6 * score_text(f"{desc}. {text or ''}")))
    return 0 if abs(score) < 0.1 else (1 if score > 0 else -1)


def fetch_events(symbols, years):
    raw = json.loads(RAW.read_text()) if RAW.exists() else {}
    for s in symbols:
        for y in years:
            key = f"{s}:{y}"
            if key in raw:
                continue
            path = (f"/api/corporate-announcements?index=equities&symbol={s}"
                    f"&from_date=01-01-{y}&to_date=31-12-{y}")
            data = nse_feed._fetch(path, "/companies-listing/corporate-filings-announcements", 5)
            raw[key] = [{"symbol": s, "desc": a.get("desc"), "text": (a.get("attchmntText") or "")[:400],
                         "an_dt": a.get("an_dt")} for a in data] if isinstance(data, list) else None
            RAW.write_text(json.dumps(raw))
            time.sleep(1.0)
    return raw


def _parse(an_dt):
    try:
        return datetime.strptime(an_dt, "%d-%b-%Y %H:%M:%S")
    except (TypeError, ValueError):
        return None


def build_index(candles):
    times = [datetime.fromisoformat(c["time"]) for c in candles]
    by_day = {}
    for i, t in enumerate(times):
        by_day.setdefault(t.date(), []).append(i)
    return times, by_day


def returns_for(event_dt, candles, times, by_day, sessions):
    """(entry_kind, entry_time, {window: bp}, gap_bp) or None."""
    day = event_dt.date()
    in_hours = (day in by_day and datetime(day.year, day.month, day.day, 9, 15) <= event_dt
                < datetime(day.year, day.month, day.day, 14, 30))
    if in_hours:
        i = bisect_left(times, event_dt)      # first bar starting after the filing
        if i >= len(times) or times[i].date() != day:
            return None
        kind, gap = "in_hours", None
    else:
        nxt = [d for d in sessions if d > day or (d == day and event_dt.hour < 9)]
        if not nxt or nxt[0] not in by_day:
            return None
        idxs = by_day[nxt[0]]
        i = next((k for k in idxs if times[k].strftime("%H:%M") >= "09:20"), None)
        if i is None:
            return None
        kind = "after_hours"
        prev_idx = idxs[0] - 1
        gap = (candles[idxs[0]]["open"] / candles[prev_idx]["close"] - 1) * 1e4 if prev_idx >= 0 else None
    entry = candles[i]["open"]
    day_idxs = by_day[times[i].date()]
    last = next((k for k in reversed(day_idxs) if times[k].strftime("%H:%M") <= "15:05"), day_idxs[-1])
    out = {}
    for w, bars in (("30m", 5), ("60m", 11)):
        k = i + bars
        out[w] = (candles[k]["close"] / entry - 1) * 1e4 if k <= last else None
    out["close"] = (candles[last]["close"] / entry - 1) * 1e4 if last > i else None
    return kind, times[i], out, gap


def baseline_abs(candles, times, by_day, sessions, entry_time, rng):
    """|return| over the same windows from the same time of day on a random other session."""
    for _ in range(10):
        d = rng.choice(sessions)
        if d == entry_time.date() or d not in by_day:
            continue
        idxs = by_day[d]
        i = next((k for k in idxs if times[k].time() >= entry_time.time()), None)
        if i is None:
            continue
        r = returns_for(datetime.combine(d, times[i].time()) - timedelta(seconds=1), candles, times, by_day, sessions)
        if r:
            return {w: abs(v) if v is not None else None for w, v in r[2].items()}
    return None


def tstat(vals):
    if len(vals) < 2:
        return None
    sd = st.stdev(vals)
    return st.mean(vals) / (sd / math.sqrt(len(vals))) if sd else None


def bh_pass(pvals, alpha=0.05):
    """Benjamini-Hochberg: which of the (name, p) pairs survive."""
    ranked = sorted(pvals, key=lambda x: x[1])
    m, passed, cutoff = len(ranked), set(), None
    for k, (name, p) in enumerate(ranked, 1):
        if p <= alpha * k / m:
            cutoff = k
    for k, (name, p) in enumerate(ranked, 1):
        if cutoff and k <= cutoff:
            passed.add(name)
    return passed


def p_from_t(t, n):
    # two-sided normal approximation; n is large everywhere it matters
    if t is None:
        return 1.0
    z = abs(t)
    return 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))


def main():
    rows = universe.load()
    symbols = [r["symbol"] for r in rows]
    pre = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=730)
    selection, _ = splits.selection_holdout(splits.sessions_in(pre))
    pre, _ = splits.slice_data(pre, {}, selection)
    sessions = [datetime.fromisoformat(d).date() for d in selection]
    print(splits.describe_split("selection", selection), flush=True)

    raw = fetch_events(symbols, (2024, 2025))
    missing = [k for k, v in raw.items() if v is None]
    print(f"filings fetched for {sum(v is not None for v in raw.values())} symbol-years; missing: {len(missing)}", flush=True)

    rng = random.Random(35)
    per = {}       # (class, window) -> {"signed": [], "abs": [], "base": [], "gap": []}
    n_events = n_routine = n_used = 0
    for key, items in raw.items():
        if not items:
            continue
        sym = key.split(":")[0]
        candles = pre.get(sym)
        if not candles:
            continue
        times, by_day = build_index(candles)
        for a in items:
            n_events += 1
            d = (a["desc"] or "").lower()
            if any(k in d for k in nse_feed.ROUTINE):
                n_routine += 1
                continue
            dt = _parse(a["an_dt"])
            if not dt or not (sessions[0] <= dt.date() <= sessions[-1]):
                continue
            r = returns_for(dt, candles, times, by_day, sessions)
            if not r:
                continue
            kind, entry_time, rets, gap = r
            sign = sentiment_sign(a["desc"], a["text"])
            base = baseline_abs(candles, times, by_day, sessions, entry_time, rng)
            n_used += 1
            cls = classify(a["desc"])
            for w in WINDOWS:
                v = rets.get(w)
                if v is None:
                    continue
                b = per.setdefault((cls, w), {"signed": [], "abs": [], "base": [], "gap": [], "kinds": {}})
                if sign:
                    b["signed"].append(v * sign)
                b["abs"].append(abs(v))
                if base and base.get(w) is not None:
                    b["base"].append(base[w])
                if gap is not None and w == "close":
                    b["gap"].append(gap)
                b["kinds"][kind] = b["kinds"].get(kind, 0) + 1

    results, pvals = {}, []
    for (cls, w), b in sorted(per.items()):
        s, ab, ba = b["signed"], b["abs"], b["base"]
        t = tstat(s)
        res = {"n_events": len(ab), "n_signed": len(s), "kinds": b["kinds"],
               "signed_mean_bp": round(st.mean(s), 2) if s else None, "signed_t": round(t, 2) if t else None,
               "abs_mean_bp": round(st.mean(ab), 2) if ab else None,
               "baseline_abs_mean_bp": round(st.mean(ba), 2) if ba else None,
               "gap_mean_bp": round(st.mean(b["gap"]), 2) if b["gap"] else None,
               "underpowered": len(s) < 50}
        results[f"{cls}:{w}"] = res
        if len(s) >= 50 and res["signed_mean_bp"] is not None and res["signed_mean_bp"] > HURDLE_BP and (t or 0) > 2:
            pvals.append((f"{cls}:{w}", p_from_t(t, len(s))))
    survivors = bh_pass(pvals) if pvals else set()
    out = {"selection": [selection[0], selection[-1], len(selection)], "filings_total": n_events,
           "routine_dropped": n_routine, "events_used": n_used, "hurdle_bp": HURDLE_BP,
           "results": results, "candidates_before_bh": [p[0] for p in pvals], "step2_earned": sorted(survivors),
           "missing_symbol_years": missing}
    OUT.write_text(json.dumps(out, indent=1))
    print(f"\nfilings {n_events}, routine dropped {n_routine}, events measured {n_used}")
    print(f"{'class:window':<18}{'n':>6}{'nSgn':>6}{'signed bp':>11}{'t':>7}{'|ret| bp':>10}{'base |ret|':>11}")
    for k, r in results.items():
        print(f"{k:<18}{r['n_events']:>6}{r['n_signed']:>6}{str(r['signed_mean_bp']):>11}{str(r['signed_t']):>7}"
              f"{str(r['abs_mean_bp']):>10}{str(r['baseline_abs_mean_bp']):>11}{'  underpowered' if r['underpowered'] else ''}")
    print(f"\nstep-2 candidates after BH: {sorted(survivors) or 'NONE'}")


if __name__ == "__main__":
    main()
