"""Step 2 follow-ups A, B and C — pre-registered in
docs/research/prereg-step2-followups.md, committed before this file existed.

A  Are atr_pct, from_high and from_low one factor? Cross-correlations and
   partial ICs. A2 also gates the held-out look (amendment 8).
B  Do the three survivors survive a TRADABLE target — Kite 09:20 bar open to
   15:10 bar close? Rule fixed before running: same sign and |t| > 2.
C  What is the atr_pct effect worth in basis points, against round-trip cost?

Selection split only. Touches nothing in the live order path: this module is
under backend/research/, which tests/test_research_splits.py proves no live
module imports.
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
import costs
import kite_history
import scanner
import universe
from research import splits

YEARS = "8y"
WARMUP_BARS = 252
MIN_STOCKS_PER_SESSION = 20

# The tradable window, per prereg §B. 09:20 is the first bar after the
# opening print nobody can trade; 15:10 is the last 5-minute bar that closes
# before the 15:15 square-off.
ENTRY_BAR = "09:20"
EXIT_BAR = "15:10"

# Signs as corrected in prereg-step2-feature-ic.md amendment 5: positive means
# "the scanner's use of this feature is correct".
SURVIVORS = [("atr_pct", 1), ("from_high", -1), ("from_low", 1)]


def tstat(vals):
    if len(vals) < 3:
        return None, None, None
    m = st.mean(vals)
    se = st.stdev(vals) / math.sqrt(len(vals))
    return m, (m / se if se else None), se


def two_sided_p(t, df):
    """Normal approximation; df is large everywhere here (hundreds of sessions)."""
    if t is None:
        return None
    z = abs(t)
    return 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))


def ranks(xs):
    """Average ranks, ties shared — the same convention Spearman needs."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return num / den if den else None


def spearman(xs, ys):
    return pearson(ranks(xs), ranks(ys))


def residualise(y, x):
    """Least-squares residual of rank(y) on rank(x). Returns the residual
    series, which is what the partial IC is then computed against."""
    ry, rx = ranks(y), ranks(x)
    mx, my = st.mean(rx), st.mean(ry)
    sxx = sum((a - mx) ** 2 for a in rx)
    if not sxx:
        return None
    beta = sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / sxx
    return [b - (my + beta * (a - mx)) for a, b in zip(rx, ry)]


def residualise_multi(y, xs_list):
    """Sequentially residualise rank(y) on each of xs_list. Not identical to a
    joint regression when the controls are correlated, but they are being
    removed one at a time on purpose — the result is 'what is left of y after
    each control has had its turn', which is the conservative reading."""
    cur = y
    for x in xs_list:
        r = residualise(cur, x)
        if r is None:
            return None
        cur = r
    return cur


def session_ic(recs, key, sign, target_key):
    xs = [r[key] for r in recs if r[key] is not None and r[target_key] is not None]
    ys = [r[target_key] for r in recs if r[key] is not None and r[target_key] is not None]
    if len(xs) < MIN_STOCKS_PER_SESSION:
        return None
    ic = spearman(xs, ys)
    return None if ic is None else sign * ic


def report(name, series, extra=""):
    m, t, se = tstat(series)
    if m is None:
        print(f"  {name:<34} n={len(series)} — too few sessions", flush=True)
        return {"name": name, "n": len(series), "mean": None}
    p = two_sided_p(t, len(series) - 1)
    pos = 100 * sum(1 for v in series if v > 0) / len(series)
    print(f"  {name:<34} n={len(series):>4}  mean={m:+.4f}  t={t:+.2f}  "
          f"p={p:.4f}  pos={pos:.1f}%  {extra}", flush=True)
    return {"name": name, "n": len(series), "mean": m, "t": t, "se": se, "p": p, "pct_pos": pos}


def build_rows():
    """Selection-split feature rows, identical construction to step 2."""
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
    selection, _held = splits.selection_holdout(all_sessions)
    print(f"  {len(selection)} selection sessions (< {splits.HELD_OUT_START})", flush=True)

    cfg = config.SCANNER
    per_session = defaultdict(list)
    started = time.time()
    for si, sess in enumerate(selection):
        for sym, bars in bars_by.items():
            prior = [b for b in bars if b["time"][:10] < sess]
            if len(prior) < WARMUP_BARS:
                continue
            today = next((b for b in bars if b["time"][:10] == sess), None)
            if not today or not today.get("open"):
                continue
            prof = scanner.daily_profile(bars, ndates, ncloses, sess)
            if not prof or scanner.tradability_exclusion(prof, cfg):
                continue
            per_session[sess].append({
                "sym": sym,
                "target": (today["close"] - today["open"]) / today["open"] * 100,
                "kite_target": None,
                "from_high": prof["pct_from_high"],
                "from_low": prof["pct_from_low"],
                "atr_pct": prof["atr_pct"],
            })
        if (si + 1) % 100 == 0:
            el = (time.time() - started) / 60
            print(f"    feature build {si+1}/{len(selection)}, {el:.0f} min", flush=True)
    per_session = {s: v for s, v in per_session.items() if len(v) >= MIN_STOCKS_PER_SESSION}
    print(f"  {len(per_session)} usable sessions", flush=True)
    return per_session


def attach_kite_target(per_session):
    """Tradable target: open of the 09:20 bar to close of the 15:10 bar."""
    syms = sorted({r["sym"] for recs in per_session.values() for r in recs})
    print(f"\nLoading Kite intraday for {len(syms)} symbols...", flush=True)
    kite = kite_history.load_batch(syms, interval=config.CANDLE_INTERVAL, days=730)
    by = defaultdict(dict)
    for sym, cs in kite.items():
        for c in cs:
            by[sym].setdefault(c["time"][:10], {})[c["time"][11:16]] = c

    attached = missing_bar = 0
    for sess, recs in per_session.items():
        for r in recs:
            day = by.get(r["sym"], {}).get(sess)
            if not day:
                continue
            entry, exit_ = day.get(ENTRY_BAR), day.get(EXIT_BAR)
            if not entry or not exit_ or not entry.get("open"):
                missing_bar += 1
                continue
            r["kite_target"] = (exit_["close"] - entry["open"]) / entry["open"] * 100
            attached += 1
    print(f"  tradable target on {attached:,} stock-sessions "
          f"({missing_bar:,} had the day but not both bars)", flush=True)
    return attached


def run_a(per_session):
    print("\n=== A — are the three survivors one factor? (EXPLORATORY) ===", flush=True)
    out = {}

    print("\nA1 cross-correlations (per-session Spearman, mean across sessions)", flush=True)
    pairs = [("atr_pct", "from_high"), ("atr_pct", "from_low"), ("from_high", "from_low")]
    for a, b in pairs:
        series = []
        for recs in per_session.values():
            xs = [r[a] for r in recs if r[a] is not None and r[b] is not None]
            ys = [r[b] for r in recs if r[a] is not None and r[b] is not None]
            if len(xs) >= MIN_STOCKS_PER_SESSION:
                c = spearman(xs, ys)
                if c is not None:
                    series.append(c)
        out[f"{a}~{b}"] = report(f"{a} vs {b}", series)

    print("\nA2 partial ICs vs the yfinance target (signs corrected)", flush=True)
    print("    amendment 8 gate: from_high and from_low need |t| > 2 here", flush=True)
    specs = [
        ("from_high | atr_pct", "from_high", ["atr_pct"], -1),
        ("from_low | atr_pct", "from_low", ["atr_pct"], 1),
        ("atr_pct | from_high,from_low", "atr_pct", ["from_high", "from_low"], 1),
    ]
    for label, key, controls, sign in specs:
        series = []
        for recs in per_session.values():
            usable = [r for r in recs
                      if all(r[k] is not None for k in [key, "target"] + controls)]
            if len(usable) < MIN_STOCKS_PER_SESSION:
                continue
            resid = residualise_multi([r[key] for r in usable],
                                      [[r[c] for r in usable] for c in controls])
            if resid is None:
                continue
            ic = spearman(resid, [r["target"] for r in usable])
            if ic is not None:
                series.append(sign * ic)
        gate = ""
        m, t, _ = tstat(series)
        if key in ("from_high", "from_low") and t is not None:
            gate = "QUALIFIES" if abs(t) > 2 else "**DISQUALIFIED**"
        out[label] = report(label, series, gate)
        if out[label].get("t") is not None:
            out[label]["qualifies"] = abs(out[label]["t"]) > 2
    return out


def run_b(per_session):
    print("\n=== B — the tradable Kite target (THE GATE) ===", flush=True)
    print(f"    {ENTRY_BAR} bar open -> {EXIT_BAR} bar close", flush=True)
    print("    rule, committed before running: same sign AND |t| > 2", flush=True)
    out = {}
    for key, sign in SURVIVORS:
        yf_series, kt_series = [], []
        for recs in per_session.values():
            with_kt = [r for r in recs if r["kite_target"] is not None]
            a = session_ic(recs, key, sign, "target")
            b = session_ic(with_kt, key, sign, "kite_target")
            # Compare like with like: only sessions where BOTH exist.
            if a is not None and b is not None:
                yf_series.append(a)
                kt_series.append(b)
        yf = report(f"{key} (yfinance, same sessions)", yf_series)
        kt = report(f"{key} (KITE TRADABLE)", kt_series)
        ratio = (kt["mean"] / yf["mean"]) if yf.get("mean") else None
        same_sign = (kt.get("mean") or 0) * (yf.get("mean") or 0) > 0
        passes = bool(same_sign and kt.get("t") is not None and abs(kt["t"]) > 2)
        print(f"    -> retained {ratio:.2f}x of the yfinance IC; "
              f"{'PASSES' if passes else '**FAILS**'} the gate", flush=True)
        out[key] = {"yfinance": yf, "kite": kt, "ratio": ratio,
                    "same_sign": same_sign, "passes": passes}
    return out


def run_c(per_session):
    print("\n=== C — atr_pct in basis points, against round-trip cost ===", flush=True)
    quint = defaultdict(list)
    spreads, spreads5 = [], []
    for recs in per_session.values():
        usable = [r for r in recs if r["atr_pct"] is not None and r["kite_target"] is not None]
        if len(usable) < MIN_STOCKS_PER_SESSION:
            continue
        usable.sort(key=lambda r: r["atr_pct"])
        n = len(usable)
        for qi in range(5):
            lo, hi = qi * n // 5, (qi + 1) * n // 5
            if hi > lo:
                quint[qi].append(st.mean(r["kite_target"] for r in usable[lo:hi]) * 100)  # bp
        # Corrected sign is +1: the scanner is "right" if HIGH atr_pct means
        # low return, so the tradable side is long the quiet names.
        spreads.append((st.mean(r["kite_target"] for r in usable[:n // 5])
                        - st.mean(r["kite_target"] for r in usable[-(n // 5):])) * 100)
        if n >= 10:
            spreads5.append((st.mean(r["kite_target"] for r in usable[:5])
                             - st.mean(r["kite_target"] for r in usable[-5:])) * 100)

    print("\n  mean tradable return by atr_pct quintile (bp), Q1 = quietest", flush=True)
    for qi in range(5):
        if quint[qi]:
            print(f"    Q{qi+1}  {st.mean(quint[qi]):+7.2f} bp   ({len(quint[qi])} sessions)", flush=True)

    print("", flush=True)
    sp = report("bottom-minus-top quintile (bp)", spreads)
    sp5 = report("bottom-5 minus top-5 (bp)", spreads5)

    # Round-trip cost in bp for a full-day hold, cash intraday, at a notional
    # typical of this project's sizing (33% cap on 1L -> ~33k per position).
    notional = 33000.0
    price = 1000.0
    qty = int(notional / price)
    buy = costs.apply_slippage("BUY", price, config.COSTS)
    sell = costs.apply_slippage("SELL", price, config.COSTS)
    charges = (costs.leg_cost("BUY", buy, qty, config.COSTS)
               + costs.leg_cost("SELL", sell, qty, config.COSTS))
    slip_bp = (buy - price) / price * 1e4 + (price - sell) / price * 1e4
    charge_bp = charges / (price * qty) * 1e4
    rt_bp = slip_bp + charge_bp
    print(f"\n  round-trip cost at Rs {notional:,.0f} notional: "
          f"{slip_bp:.2f} bp slippage + {charge_bp:.2f} bp charges = **{rt_bp:.2f} bp**", flush=True)
    for label, res in (("quintile", sp), ("top5/bottom5", sp5)):
        if res.get("mean") is not None:
            verdict = "EXCEEDS" if res["mean"] > rt_bp else "does NOT exceed"
            print(f"  {label} spread {res['mean']:+.2f} bp {verdict} round-trip cost "
                  f"of {rt_bp:.2f} bp", flush=True)
    return {"quintiles": {f"Q{i+1}": st.mean(quint[i]) for i in range(5) if quint[i]},
            "spread": sp, "spread_top5": sp5,
            "round_trip_bp": rt_bp, "slippage_bp": slip_bp, "charges_bp": charge_bp}


def main():
    started = time.time()
    per_session = build_rows()
    attach_kite_target(per_session)
    result = {"A": run_a(per_session), "B": run_b(per_session), "C": run_c(per_session)}
    out = Path(__file__).resolve().parents[2] / "docs/research/step2_followups_result.json"
    out.write_text(json.dumps(result, indent=2, default=str))
    print(f"\nWrote {out}  ({(time.time()-started)/60:.1f} min)", flush=True)


if __name__ == "__main__":
    main()
