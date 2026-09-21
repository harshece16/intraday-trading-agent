"""3c — overnight vs intraday decomposition, volatility-sorted.

Pre-registered in docs/research/prereg-3c-overnight-intraday.md, committed
before this file existed (8306b2c).

Selection split only. §D (held-out) is specified in the prereg and is NOT
implemented here, deliberately: the held-out period is contested between
step 2's atr_pct look and 3c's confirmation, and the reviewer decides which.

Measurement only — no stop, no sizing, no backtest. Trial count stays at 34.
"""

import json
import math
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import kite_history
import scanner
import universe
from research import splits

YEARS = "8y"                 # stated in the prereg, not chosen afterwards
WARMUP_BARS = 252
MIN_STOCKS_PER_SESSION = 20
QUINTILES = 5
ENTRY_BAR = "09:20"
EXIT_BAR = "15:10"
ROUND_TRIP_BP = 16.60        # measured; see friction_decomposition.json


def ci95(vals):
    if len(vals) < 3:
        return None, None, (None, None)
    m = st.mean(vals)
    se = st.stdev(vals) / math.sqrt(len(vals))
    return m, se, (m - 1.96 * se, m + 1.96 * se)


def report(label, vals, unit="bp"):
    m, se, (lo, hi) = ci95(vals)
    if m is None:
        print(f"  {label:<38} n={len(vals)} — too few")
        return {"name": label, "n": len(vals)}
    t = m / se if se else float("nan")
    pos = 100 * sum(1 for v in vals if v > 0) / len(vals)
    print(f"  {label:<38} n={len(vals):>5}  {m:+8.2f} {unit}  t={t:+6.2f}  "
          f"pos={pos:5.1f}%  CI [{lo:+.2f}, {hi:+.2f}]")
    return {"name": label, "n": len(vals), "mean": m, "t": t, "se": se,
            "ci": [lo, hi], "pct_pos": pos}


def build():
    rows = universe.load()
    symbols = [r["symbol"] for r in rows]
    print(f"Downloading {YEARS} daily for {len(symbols)} symbols + NIFTY...", flush=True)
    daily = scanner.download_batch([scanner.yf_ticker(s) for s in symbols] + [scanner.NIFTY],
                                   YEARS, "1d")
    nd = daily.get(scanner.NIFTY, [])
    ndates = [b["time"][:10] for b in nd]
    ncloses = [b["close"] for b in nd]
    bars_by = {s: daily.get(scanner.yf_ticker(s), []) for s in symbols}
    bars_by = {s: b for s, b in bars_by.items() if b}

    all_sessions = sorted({b["time"][:10] for b in nd})
    selection, _ = splits.selection_holdout(all_sessions)
    print(f"  {len(selection)} selection sessions (< {splits.HELD_OUT_START})", flush=True)

    cfg = config.SCANNER
    per_session = defaultdict(list)
    started = time.time()
    for si, sess in enumerate(selection):
        for sym, bars in bars_by.items():
            idx = next((k for k, b in enumerate(bars) if b["time"][:10] == sess), None)
            if idx is None or idx < WARMUP_BARS:
                continue
            today, prev = bars[idx], bars[idx - 1]
            if not today.get("open") or not prev.get("close"):
                continue
            prof = scanner.daily_profile(bars, ndates, ncloses, sess)
            if not prof or scanner.tradability_exclusion(prof, cfg):
                continue
            per_session[sess].append({
                "sym": sym,
                "atr_pct": prof["atr_pct"],
                # bp, both from the same daily source
                "overnight": (today["open"] - prev["close"]) / prev["close"] * 1e4,
                "intraday": (today["close"] - today["open"]) / today["open"] * 1e4,
                "kite_intraday": None,
            })
        if (si + 1) % 200 == 0:
            print(f"    {si+1}/{len(selection)}, {(time.time()-started)/60:.0f} min", flush=True)
    per_session = {s: v for s, v in per_session.items()
                   if len(v) >= MIN_STOCKS_PER_SESSION}
    print(f"  {len(per_session)} usable sessions", flush=True)
    return per_session


def attach_kite(per_session):
    syms = sorted({r["sym"] for recs in per_session.values() for r in recs})
    print(f"\nLoading Kite intraday for {len(syms)} symbols...", flush=True)
    kite = kite_history.load_batch(syms, interval=config.CANDLE_INTERVAL, days=730)
    by = defaultdict(dict)
    for sym, cs in kite.items():
        for c in cs:
            by[sym].setdefault(c["time"][:10], {})[c["time"][11:16]] = c
    n = 0
    for sess, recs in per_session.items():
        for r in recs:
            day = by.get(r["sym"], {}).get(sess)
            if not day:
                continue
            a, b = day.get(ENTRY_BAR), day.get(EXIT_BAR)
            if a and b and a.get("open"):
                r["kite_intraday"] = (b["close"] - a["open"]) / a["open"] * 1e4
                n += 1
    print(f"  tradable intraday on {n:,} stock-sessions", flush=True)


def quintile_table(per_session, intraday_key, label):
    """Mean overnight / intraday per ATR% quintile, plus bottom-minus-top
    spreads with a t across sessions."""
    print(f"\n--- {label} ---", flush=True)
    on_q = defaultdict(list)
    id_q = defaultdict(list)
    spread_on, spread_id = [], []
    used = 0
    for recs in per_session.values():
        u = [r for r in recs if r["atr_pct"] is not None
             and r["overnight"] is not None and r[intraday_key] is not None]
        if len(u) < MIN_STOCKS_PER_SESSION:
            continue
        used += 1
        u.sort(key=lambda r: r["atr_pct"])
        n = len(u)
        for qi in range(QUINTILES):
            lo, hi = qi * n // QUINTILES, (qi + 1) * n // QUINTILES
            if hi > lo:
                on_q[qi].append(st.mean(r["overnight"] for r in u[lo:hi]))
                id_q[qi].append(st.mean(r[intraday_key] for r in u[lo:hi]))
        k = n // QUINTILES
        # bottom minus top, i.e. quiet minus volatile
        spread_on.append(st.mean(r["overnight"] for r in u[:k])
                         - st.mean(r["overnight"] for r in u[-k:]))
        spread_id.append(st.mean(r[intraday_key] for r in u[:k])
                         - st.mean(r[intraday_key] for r in u[-k:]))

    print(f"  sessions used: {used}")
    print(f"  {'quintile':<10} {'overnight':>12} {'intraday':>12} {'sum':>12}")
    q_out = {}
    for qi in range(QUINTILES):
        if not on_q[qi]:
            continue
        o, i = st.mean(on_q[qi]), st.mean(id_q[qi])
        tag = "quietest" if qi == 0 else "MOST VOL" if qi == QUINTILES - 1 else ""
        print(f"  Q{qi+1:<9} {o:+10.2f}bp {i:+10.2f}bp {o+i:+10.2f}bp  {tag}")
        q_out[f"Q{qi+1}"] = {"overnight": o, "intraday": i, "sum": o + i}

    print()
    s_on = report("quiet-minus-volatile OVERNIGHT", spread_on)
    s_id = report("quiet-minus-volatile INTRADAY", spread_id)
    return {"quintiles": q_out, "spread_overnight": s_on, "spread_intraday": s_id,
            "sessions": used}


def main():
    started = time.time()
    per_session = build()
    attach_kite(per_session)

    print("\n" + "=" * 74)
    print("3c — OVERNIGHT vs INTRADAY, selection split only")
    print("=" * 74)

    # --- §A unconditional -------------------------------------------------
    print("\n=== §A unconditional decomposition (L23) ===")
    on, idy = [], []
    for recs in per_session.values():
        on.append(st.mean(r["overnight"] for r in recs))
        idy.append(st.mean(r["intraday"] for r in recs))
    a_on = report("mean OVERNIGHT per session", on)
    a_id = report("mean INTRADAY per session", idy)
    print(f"  -> of the {a_on['mean']+a_id['mean']:+.2f}bp total daily return, "
          f"overnight is {a_on['mean']:+.2f}bp and intraday {a_id['mean']:+.2f}bp")

    # --- §B volatility-sorted, daily bars ---------------------------------
    print("\n=== §B volatility-sorted, daily bars (L24) ===")
    b = quintile_table(per_session, "intraday", "ATR% quintiles, yfinance daily")

    # --- §C the tradable window -------------------------------------------
    print("\n=== §C volatility-sorted, TRADABLE Kite window (L25) ===")
    c = quintile_table(per_session, "kite_intraday",
                       f"ATR% quintiles, Kite {ENTRY_BAR} open -> {EXIT_BAR} close")

    # --- the pre-registered verdict ---------------------------------------
    print("\n" + "=" * 74)
    print("THE PRE-REGISTERED PREDICTION")
    print("=" * 74)
    q = b["quintiles"]
    if q:
        on_rises = q["Q5"]["overnight"] > q["Q1"]["overnight"]
        id_falls = q["Q5"]["intraday"] < q["Q1"]["intraday"]
        print(f"  overnight RISES with ATR%?  {on_rises}   "
              f"(Q1 {q['Q1']['overnight']:+.2f} -> Q5 {q['Q5']['overnight']:+.2f} bp)")
        print(f"  intraday FALLS with ATR%?   {id_falls}   "
              f"(Q1 {q['Q1']['intraday']:+.2f} -> Q5 {q['Q5']['intraday']:+.2f} bp)")
        if on_rises and id_falls:
            print("  -> MECHANISM HOLDS: volatile names earn overnight, give it back intraday")
        elif id_falls:
            print("  -> FALSIFIED as pre-registered: intraday falls but overnight does NOT rise.")
            print("     That is drift, not a mechanism — a worse fact, not a better one.")
        else:
            print("  -> neither leg behaves as predicted")

    sid = c.get("spread_intraday", {}).get("mean")
    if sid is not None:
        print(f"\n  TRADABLE intraday spread {sid:+.2f} bp vs round trip {ROUND_TRIP_BP:.2f} bp"
              f"  -> {'CLEARS' if sid > ROUND_TRIP_BP else 'does NOT clear'} cost "
              f"({sid/ROUND_TRIP_BP:.2f}x)")

    out = {"A": {"overnight": a_on, "intraday": a_id}, "B": b, "C": c,
           "round_trip_bp": ROUND_TRIP_BP}
    dest = Path(__file__).resolve().parents[2] / "docs/research/step3c_result.json"
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote {dest}   ({(time.time()-started)/60:.1f} min)")


if __name__ == "__main__":
    main()
