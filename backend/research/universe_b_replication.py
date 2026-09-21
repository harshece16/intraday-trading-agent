"""Universe B replication of the step 2 volatility result.

Pre-registered in docs/research/prereg-universe-b-replication.md, committed
(edd3471) before this file existed.

Primary: atr_pct rank IC on 113 F&O-eligible names outside the NIFTY 100,
same selection dates, same 252-bar warm-up, same test, same sign.
PASS RULE, fixed before running: same sign as universe A AND |t| > 2.

Secondary (no pass rule, not in any family): from_high, from_low, partials.

Daily data only — no Kite calls. Universe A's bars are never loaded here
(Entry 6 §E).
"""

import csv
import json
import math
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import scanner
from research import splits
from research.step2_followups import (MIN_STOCKS_PER_SESSION, WARMUP_BARS, report,
                                      residualise_multi, session_ic, spearman)

YEARS = "8y"                       # stated in the prereg, not chosen after
UNIVERSE_B = Path(__file__).resolve().parents[1] / "data/universe_b.csv"
CHUNK = 40                         # §E: download in chunks

# Universe A comparison points, both quoted in the prereg so neither can be
# picked afterwards. The 8y figure is the matching one.
UNIVERSE_A = {"atr_pct": {"8y": (-0.0388, -7.32), "4y": (-0.0558, -6.13)},
              "from_high": {"8y": (+0.0086, +1.73)},
              "from_low": {"8y": (-0.0254, -5.25)}}

# Entry 6 §D — double slippage on universe B, fixed now.
ROUND_TRIP_BP_B = 22.60


def load_universe_b():
    with UNIVERSE_B.open() as f:
        return [r["Symbol"].strip() for r in csv.DictReader(f) if r["Symbol"].strip()]


CACHE = Path(__file__).resolve().parents[1] / "data/universe_b_rows.json"


def main():
    started = time.time()
    symbols = load_universe_b()
    if CACHE.exists():
        blob = json.loads(CACHE.read_text())
        print(f"Reusing cached feature rows from {CACHE.name} "
              f"({blob['sessions']} sessions) — no yfinance download.", flush=True)
        return analyse({k: v for k, v in blob["per_session"].items()},
                       blob["symbols"], blob["built"], blob["dropped_warmup"],
                       blob["excluded"], started)
    print(f"Universe B: {len(symbols)} symbols (F&O-eligible minus NIFTY 100)", flush=True)

    # NIFTY is needed for rs10 inside daily_profile; it is an index, not a
    # universe A constituent, so this does not violate §E.
    daily = {}
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i:i + CHUNK]
        print(f"  downloading {i+1}-{i+len(chunk)} of {len(symbols)}...", flush=True)
        daily.update(scanner.download_batch([scanner.yf_ticker(s) for s in chunk], YEARS, "1d"))
    nifty = scanner.download_batch([scanner.NIFTY], YEARS, "1d").get(scanner.NIFTY, [])
    ndates = [b["time"][:10] for b in nifty]
    ncloses = [b["close"] for b in nifty]

    bars_by = {s: daily.get(scanner.yf_ticker(s), []) for s in symbols}
    missing = [s for s, b in bars_by.items() if not b]
    bars_by = {s: b for s, b in bars_by.items() if b}
    print(f"  {len(bars_by)} symbols with daily bars"
          f"{f'; {len(missing)} had none: {missing}' if missing else ''}", flush=True)

    all_sessions = sorted({b["time"][:10] for b in nifty})
    selection, _ = splits.selection_holdout(all_sessions)
    print(f"  {len(selection)} selection sessions (< {splits.HELD_OUT_START})", flush=True)

    cfg = config.SCANNER
    per_session = defaultdict(list)
    dropped_warmup = excluded = 0
    for si, sess in enumerate(selection):
        for sym, bars in bars_by.items():
            idx = next((k for k, b in enumerate(bars) if b["time"][:10] == sess), None)
            if idx is None:
                continue
            if idx < WARMUP_BARS:
                dropped_warmup += 1
                continue
            today = bars[idx]
            if not today.get("open"):
                continue
            prof = scanner.daily_profile(bars, ndates, ncloses, sess)
            if not prof:
                continue
            if scanner.tradability_exclusion(prof, cfg):
                excluded += 1
                continue
            per_session[sess].append({
                "sym": sym,
                "target": (today["close"] - today["open"]) / today["open"] * 100,
                "atr_pct": prof["atr_pct"],
                "from_high": prof["pct_from_high"],
                "from_low": prof["pct_from_low"],
            })
        if (si + 1) % 300 == 0:
            print(f"    {si+1}/{len(selection)}, {(time.time()-started)/60:.0f} min", flush=True)

    usable = {s: v for s, v in per_session.items() if len(v) >= MIN_STOCKS_PER_SESSION}
    built = sum(len(v) for v in per_session.values())
    print(f"\n  built {built:,} stock-sessions; {len(usable)} usable sessions "
          f"(>= {MIN_STOCKS_PER_SESSION} stocks)")
    print(f"  {dropped_warmup:,} dropped for the 252-bar warm-up, "
          f"{excluded:,} excluded by tradability", flush=True)
    CACHE.write_text(json.dumps({"per_session": usable, "symbols": len(bars_by),
                                 "built": built, "dropped_warmup": dropped_warmup,
                                 "excluded": excluded, "sessions": len(usable)}))
    return analyse(usable, len(bars_by), built, dropped_warmup, excluded, started)


def analyse(usable, n_symbols, built, dropped_warmup, excluded, started):

    print("\n" + "=" * 74)
    print("UNIVERSE B REPLICATION — selection split, daily bars")
    print("=" * 74)

    # ---- PRIMARY ------------------------------------------------------
    print("\n=== PRIMARY: atr_pct (the only amendment-8 qualifier) ===")
    print("    pass rule fixed before running: same sign as A, and |t| > 2")
    series = [ic for recs in usable.values()
              if (ic := session_ic(recs, "atr_pct", 1, "target")) is not None]
    prim = report("atr_pct (universe B)", series)
    a_mean, a_t = UNIVERSE_A["atr_pct"]["8y"]
    same_sign = prim.get("mean") is not None and prim["mean"] * a_mean > 0
    big_enough = prim.get("t") is not None and abs(prim["t"]) > 2
    passed = bool(same_sign and big_enough)
    print(f"\n    universe A (8y): {a_mean:+.4f}  t={a_t:+.2f}")
    print(f"    universe B     : {prim.get('mean', float('nan')):+.4f}  "
          f"t={prim.get('t', float('nan')):+.2f}")
    print(f"    same sign? {same_sign}   |t| > 2? {big_enough}")
    print(f"\n    >>> {'PASS' if passed else 'FAIL'} <<<")
    if prim.get("mean") is not None and a_mean:
        print(f"    retained {prim['mean']/a_mean:.2f}x of universe A's effect size")

    # ---- SECONDARY ----------------------------------------------------
    print("\n=== SECONDARY (exploratory, NO pass rule, not in any family) ===")
    sec = {}
    for key, sign in (("from_high", -1), ("from_low", 1)):
        s2 = [ic for recs in usable.values()
              if (ic := session_ic(recs, key, sign, "target")) is not None]
        sec[key] = report(f"{key} (universe B)", s2)
        if key in UNIVERSE_A:
            am, at = UNIVERSE_A[key]["8y"]
            print(f"      universe A 8y was {am:+.4f} (t={at:+.2f})")

    print("\n  partial ICs — does 'one factor, not three' replicate?")
    for label, key, controls, sign in (
            ("from_high | atr_pct", "from_high", ["atr_pct"], -1),
            ("from_low | atr_pct", "from_low", ["atr_pct"], 1),
            ("atr_pct | from_high,from_low", "atr_pct", ["from_high", "from_low"], 1)):
        vals = []
        for recs in usable.values():
            u = [r for r in recs if all(r[k] is not None for k in [key, "target"] + controls)]
            if len(u) < MIN_STOCKS_PER_SESSION:
                continue
            resid = residualise_multi([r[key] for r in u],
                                      [[r[c] for r in u] for c in controls])
            if resid is None:
                continue
            ic = spearman(resid, [r["target"] for r in u])
            if ic is not None:
                vals.append(sign * ic)
        sec[label] = report(label, vals)

    print(f"\n  Entry 6 §D: any money figure here uses DOUBLE slippage — "
          f"round trip {ROUND_TRIP_BP_B:.2f} bp, not 16.60 bp.")

    out = {"universe": "B", "symbols": n_symbols, "sessions": len(usable),
           "stock_sessions": built, "dropped_warmup": dropped_warmup,
           "primary": {**prim, "passed": passed, "same_sign": same_sign,
                       "abs_t_over_2": big_enough,
                       "universe_a_8y": {"mean": a_mean, "t": a_t}},
           "secondary": sec, "round_trip_bp": ROUND_TRIP_BP_B}
    dest = Path(__file__).resolve().parents[2] / "docs/research/universe_b_result.json"
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote {dest}   ({(time.time()-started)/60:.1f} min)")


if __name__ == "__main__":
    main()
