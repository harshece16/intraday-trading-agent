"""3b stage 1 — a measurement, NO trial. Trial count stays at 35.

Pre-registered in docs/research/prereg-3b-intraday-momentum.md, amendment 1
(Entry 12, `fef1fd7`) and amendment 2 (Entry 13, `9d8d892`), both committed
before this file existed.

Two pre-declared lines, each with its own gate fixed before running:

  L31  stage 1a — CROSS-SECTIONAL. Rank by 09:15 open -> 09:45 close return;
       target 09:50 OPEN -> 15:10 close (amendment 1 §3, matching stage 2's
       entry). GATE = the QUINTILE top-minus-bottom spread (amendment 2 §F.1),
       positive, t > 2, and above 33.20 bp — TWO legs, each paying a 16.60 bp
       round trip (amendment 1 §1). The top-5/bottom-5 line is DESCRIPTIVE
       ONLY, no pass rule.

  L32  stage 1b — TIME-SERIES, the original brief's 3b, adapted. Market proxy
       = equal-weighted mean of the universe. Signal = sign(prev close ->
       09:45 close), including the overnight gap. Target = 14:40 open ->
       15:10 close. GATE = ONE round trip: positive, t > 2, above 16.60 bp.
       The per-stock line uses THAT STOCK'S OWN signal and is DESCRIPTIVE
       ONLY (amendment 2 §F.2).

Universe A, selection dates only, existing Kite cache. No Kite calls.
Held-out data is excluded before anything can see it.
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
import universe
from research import splits

# --- bars, all from the pre-registration -------------------------------
RANGE_OPEN = "09:15"     # signal window start (open of this bar)
SIGNAL_END = "09:45"     # signal window end (close of this bar)
TARGET_OPEN = "09:50"    # amendment 1 §3 — matches stage 2's entry
LAST_HALF_OPEN = "14:40"  # stage 1b target start
EXIT_BAR = "15:10"       # last bar before the 15:15 square-off

MIN_STOCKS_PER_SESSION = 20
QUINTILES = 5
GATE_CROSS_BP = 33.20    # TWO legs (amendment 1 §1)
GATE_TS_BP = 16.60       # ONE leg
TOP_N = 5


def tstat(vals):
    if len(vals) < 3:
        return None, None, None
    m = st.mean(vals)
    se = st.stdev(vals) / math.sqrt(len(vals))
    return m, (m / se if se else None), se


def report(label, vals, unit="bp"):
    m, t, se = tstat(vals)
    if m is None:
        print(f"  {label:<44} n={len(vals)} — too few")
        return {"name": label, "n": len(vals)}
    pos = 100 * sum(1 for v in vals if v > 0) / len(vals)
    print(f"  {label:<44} n={len(vals):>5}  {m:+8.2f} {unit}  t={t:+6.2f}  pos={pos:5.1f}%")
    return {"name": label, "n": len(vals), "mean": m, "t": t, "se": se, "pct_pos": pos}


def load_sessions():
    """Kite 5-min cache, selection dates only. Held-out dropped before use."""
    rows = universe.load()
    symbols = [r["symbol"] for r in rows]
    print(f"Loading Kite cache for {len(symbols)} symbols (no network)...", flush=True)
    cache = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=730)

    per = defaultdict(dict)   # date -> symbol -> {hh:mm: bar}
    dropped_heldout = 0
    for sym, candles in cache.items():
        for c in candles:
            d = c["time"][:10]
            if d >= splits.HELD_OUT_START:        # excluded before anything sees it
                dropped_heldout += 1
                continue
            per[d].setdefault(sym, {})[c["time"][11:16]] = c
    print(f"  {len(per)} cached sessions; {dropped_heldout:,} held-out bars dropped", flush=True)
    return per


def build(per):
    """Per session, the per-stock quantities both lines need."""
    out = {}
    skipped_prev = 0
    dates = sorted(per)
    prev_close = {}   # symbol -> previous session's 15:10 close (for stage 1b)
    for d in dates:
        recs = []
        for sym, bars in per[d].items():
            o = bars.get(RANGE_OPEN)
            s_end = bars.get(SIGNAL_END)
            t_open = bars.get(TARGET_OPEN)
            lh = bars.get(LAST_HALF_OPEN)
            ex = bars.get(EXIT_BAR)
            if not (o and s_end and t_open and ex and o.get("open") and t_open.get("open")):
                continue
            mom = (s_end["close"] - o["open"]) / o["open"] * 1e4          # signal, bp
            tgt = (ex["close"] - t_open["open"]) / t_open["open"] * 1e4    # target, bp
            rec = {"sym": sym, "mom": mom, "target": tgt}
            # stage 1b pieces
            pc = prev_close.get(sym)
            if pc and lh and lh.get("open"):
                rec["gap_signal"] = (s_end["close"] - pc) / pc * 1e4       # prev close -> 09:45
                rec["last_half"] = (ex["close"] - lh["open"]) / lh["open"] * 1e4
            else:
                skipped_prev += 1
            recs.append(rec)
        for sym, bars in per[d].items():
            ex = bars.get(EXIT_BAR)
            if ex:
                prev_close[sym] = ex["close"]
        if len(recs) >= MIN_STOCKS_PER_SESSION:
            out[d] = recs
    print(f"  {len(out)} usable sessions (>= {MIN_STOCKS_PER_SESSION} stocks); "
          f"{skipped_prev:,} stock-sessions had no prior close for the 1b line", flush=True)
    return out


def main():
    started = time.time()
    per = load_sessions()
    sessions = build(per)
    if not sessions:
        print("no usable sessions"); return
    dates = sorted(sessions)
    mid = dates[len(dates) // 2]
    print(f"  span {dates[0]} -> {dates[-1]}; halves split at {mid}", flush=True)

    # ================= STAGE 1a — cross-sectional =====================
    print("\n" + "=" * 74)
    print("STAGE 1a (L31) — CROSS-SECTIONAL.  GATE = QUINTILE spread > 33.20 bp, t > 2")
    print("=" * 74)
    quint = defaultdict(list)
    sp_q, sp_5 = [], []
    sp_q_h = {"first": [], "second": []}
    for d in dates:
        u = sorted(sessions[d], key=lambda r: r["mom"])
        n = len(u)
        for qi in range(QUINTILES):
            lo, hi = qi * n // QUINTILES, (qi + 1) * n // QUINTILES
            if hi > lo:
                quint[qi].append(st.mean(r["target"] for r in u[lo:hi]))
        k = n // QUINTILES
        # top = highest momentum, bottom = lowest. Momentum predicts continuation,
        # so the tradable spread is TOP minus BOTTOM.
        s = st.mean(r["target"] for r in u[-k:]) - st.mean(r["target"] for r in u[:k])
        sp_q.append(s)
        sp_q_h["first" if d < mid else "second"].append(s)
        if n >= 2 * TOP_N:
            sp_5.append(st.mean(r["target"] for r in u[-TOP_N:])
                        - st.mean(r["target"] for r in u[:TOP_N]))

    print(f"\n  mean 09:50->15:10 return by momentum quintile (Q1 = weakest):")
    for qi in range(QUINTILES):
        if quint[qi]:
            tag = "weakest" if qi == 0 else "STRONGEST" if qi == QUINTILES - 1 else ""
            print(f"    Q{qi+1}  {st.mean(quint[qi]):+8.2f} bp   {tag}")
    print()
    r_q = report("QUINTILE top-minus-bottom  [THE GATE]", sp_q)
    r_5 = report("top-5/bottom-5  [descriptive only]", sp_5)
    rh1 = report("  first half", sp_q_h["first"])
    rh2 = report("  second half", sp_q_h["second"])

    sd = st.stdev(sp_q)
    mde = 2 * sd / math.sqrt(len(sp_q))
    print(f"\n  MDE at t=2: {mde:.2f} bp  (sd {sd:.2f}, n {len(sp_q)})")
    a_pass = bool(r_q.get("mean", 0) > 0 and r_q.get("t") and r_q["t"] > 2
                  and r_q["mean"] > GATE_CROSS_BP)
    print(f"  gate: >0? {r_q.get('mean',0)>0}   t>2? {bool(r_q.get('t') and r_q['t']>2)}   "
          f">{GATE_CROSS_BP}bp? {r_q.get('mean',0)>GATE_CROSS_BP}")
    print(f"\n  >>> STAGE 1a: {'CLEARS' if a_pass else 'DOES NOT CLEAR'} <<<")

    # ================= STAGE 1b — time series =========================
    print("\n" + "=" * 74)
    print("STAGE 1b (L32) — TIME-SERIES, adapted.  GATE = > 16.60 bp, t > 2")
    print("=" * 74)
    print("  ADAPTED: the literature's window runs to the CLOSE, which an intraday")
    print("  cash position cannot hold. Measured to the 15:10 bar instead.")
    mkt, mkt_h = [], {"first": [], "second": []}
    per_stock = []
    for d in dates:
        have = [r for r in sessions[d] if "gap_signal" in r]
        if len(have) < MIN_STOCKS_PER_SESSION:
            continue
        sig = st.mean(r["gap_signal"] for r in have)     # equal-weighted market proxy
        tgt = st.mean(r["last_half"] for r in have)
        v = (1 if sig > 0 else -1 if sig < 0 else 0) * tgt
        mkt.append(v)
        mkt_h["first" if d < mid else "second"].append(v)
        # descriptive: each stock's OWN signal (amendment 2 §F.2)
        per_stock.append(st.mean((1 if r["gap_signal"] > 0 else -1 if r["gap_signal"] < 0 else 0)
                                 * r["last_half"] for r in have))
    print()
    r_m = report("market sign(prev close->09:45) x 14:40->15:10  [GATE]", mkt)
    report("  first half", mkt_h["first"])
    report("  second half", mkt_h["second"])
    r_ps = report("per-stock own signal  [descriptive only]", per_stock)
    b_pass = bool(r_m.get("mean", 0) > 0 and r_m.get("t") and r_m["t"] > 2
                  and r_m["mean"] > GATE_TS_BP)
    print(f"\n  >>> STAGE 1b: {'CLEARS' if b_pass else 'DOES NOT CLEAR'} <<<")

    # ================= verdict ========================================
    print("\n" + "=" * 74)
    if a_pass:
        print("STAGE 1a CLEARS -> stage 2 is DEFINED but NOT AUTHORISED. Stop and ask the user.")
    elif b_pass:
        print("ONLY the time-series line clears -> STOP and report (amendment 1 §4);")
        print("it would need its own pre-registration. Stage 2 does not cover it.")
    else:
        print("NEITHER line clears -> 3b is WITHDRAWN. No trial spent; count stays at 35.")
        print("Per the pre-registration, it is NOT re-registered with a different")
        print("signal window, holding period or filter.")
    print("=" * 74)

    out = {"sessions": len(dates), "span": [dates[0], dates[-1]], "halves_split_at": mid,
           "stage1a": {"quintiles": {f"Q{i+1}": st.mean(quint[i]) for i in range(QUINTILES) if quint[i]},
                       "gate_spread": r_q, "top5_descriptive": r_5,
                       "first_half": rh1, "second_half": rh2,
                       "mde_bp": mde, "gate_bp": GATE_CROSS_BP, "clears": a_pass},
           "stage1b": {"market_gate": r_m, "per_stock_descriptive": r_ps,
                       "gate_bp": GATE_TS_BP, "clears": b_pass}}
    dest = Path(__file__).resolve().parents[2] / "docs/research/step3b_stage1_result.json"
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote {dest}   ({(time.time()-started)/60:.1f} min)")


if __name__ == "__main__":
    main()
