"""Step 2 — per-feature scanner IC. Pre-registered: prereg-step2-feature-ic.md
(bc704e5, amended d165699/535a082 before this was written).

Order enforced here:
  1. build features with a 252-bar warm-up requirement (D3)
  2. DATA-QUALITY GATE: yfinance open-to-close vs Kite (D4) — can halt the step
  3. ten tests: rank IC for continuous, per-session difference for binary and
     trend (D1, D2)
  4. raw / BH q=0.10 / Bonferroni over a family of ten (D2)

Measurements only. No strategy, no backtest, no trial. Logged as research
looks.
"""
import json
import math
import statistics as st
import sys
import time
from collections import defaultdict

sys.path.insert(0, "/Users/harshgupta/Projects/webapp/backend")

import config
import kite_history
import scanner
import universe
from research import splits

OUT = "/Users/harshgupta/.claude/jobs/2d14240a/tmp/step2_result.json"
PROGRESS = "/Users/harshgupta/Projects/webapp/docs/research/progress.md"
WARMUP_BARS = 252          # D3: a real 52 weeks
MIN_STOCKS_PER_SESSION = 20
MIN_PER_SIDE = 3           # D1
YEARS = "4y"               # far enough back that warm-up holds from session 1


def note(done, total, started, what):
    el = time.time() - started
    eta = time.strftime("%H:%M", time.localtime(started + el / max(done, 1) * total))
    try:
        with open(PROGRESS, "a") as f:
            f.write(f"| {time.strftime('%H:%M')} | step 2 {what}: {done}/{total}, "
                    f"{el/60:.0f} min elapsed, est. finish {eta} |\n")
    except OSError:
        pass


def tstat(vals):
    if len(vals) < 2:
        return None, None, None
    m, sd = st.mean(vals), st.stdev(vals)
    se = sd / math.sqrt(len(vals))
    return m, (m / se if se else None), se


def two_sided_p(t, df):
    """Normal approximation; df is large here (hundreds of sessions)."""
    if t is None:
        return None
    return 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))


def benjamini_hochberg(pvals, q=0.10):
    """Returns the set of indices that survive BH at level q."""
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    survivors, kmax = set(), -1
    for rank, i in enumerate(idx, start=1):
        if pvals[i] <= q * rank / m:
            kmax = rank
    if kmax > 0:
        survivors = set(idx[:kmax])
    return survivors


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def main():
    started = time.time()
    rows = universe.load()
    symbols = [r["symbol"] for r in rows]
    print(f"Downloading {YEARS} daily for {len(symbols)} symbols + NIFTY "
          f"(warm-up needs {WARMUP_BARS} prior bars)...", flush=True)
    daily = scanner.download_batch([scanner.yf_ticker(s) for s in symbols] + [scanner.NIFTY],
                                   YEARS, "1d")
    nd = daily.get(scanner.NIFTY, [])
    ndates = [b["time"][:10] for b in nd]
    ncloses = [b["close"] for b in nd]

    bars_by = {s: daily.get(scanner.yf_ticker(s), []) for s in symbols}
    bars_by = {s: b for s, b in bars_by.items() if b}
    print(f"  {len(bars_by)} symbols with daily bars", flush=True)

    # sessions in the SELECTION split only, with enough warm-up
    all_sessions = sorted({b["time"][:10] for b in nd})
    selection, _held = splits.selection_holdout(all_sessions)
    print(f"  {len(all_sessions)} sessions total, {len(selection)} in selection "
          f"(< {splits.HELD_OUT_START})", flush=True)

    # ---- build feature rows -------------------------------------------
    cfg = config.SCANNER
    per_session = defaultdict(list)
    dropped_warmup = 0
    kept = 0
    for si, sess in enumerate(selection):
        for sym, bars in bars_by.items():
            prior = [b for b in bars if b["time"][:10] < sess]
            if len(prior) < WARMUP_BARS:            # D3
                dropped_warmup += 1
                continue
            today = next((b for b in bars if b["time"][:10] == sess), None)
            if not today or not today.get("open"):
                continue
            prof = scanner.daily_profile(bars, ndates, ncloses, sess)
            if not prof or scanner.tradability_exclusion(prof, cfg):
                continue
            target = (today["close"] - today["open"]) / today["open"] * 100   # open-to-close %
            per_session[sess].append({
                "sym": sym, "target": target,
                "trend": prof["trend"],
                "rs10": prof["rs10"],
                "from_high": prof["pct_from_high"],
                "from_low": prof["pct_from_low"],
                "rsi": prof["rsi"],
                "atr_pct": prof["atr_pct"],
                "nr7": bool(prof["nr7"]),
                "inside": bool(prof["inside_day"]),
                "pattern": bool(prof.get("swing_patterns")),
                "reversal": bool(prof.get("reversal_day")),
                "kite_target": None,
            })
            kept += 1
        if (si + 1) % 25 == 0:
            note(si + 1, len(selection), started, "feature build")
    per_session = {s: v for s, v in per_session.items() if len(v) >= MIN_STOCKS_PER_SESSION}
    print(f"  built {kept} stock-sessions over {len(per_session)} usable sessions; "
          f"{dropped_warmup} dropped for warm-up", flush=True)

    # ---- D4 data-quality gate ------------------------------------------
    print("\n=== D4 data-quality gate: yfinance vs Kite open-to-close ===", flush=True)
    pairs = []
    cache_syms = set()
    for sess, recs in per_session.items():
        for r in recs:
            cache_syms.add(r["sym"])
    kite = kite_history.load_batch(sorted(cache_syms), interval=config.CANDLE_INTERVAL, days=730)
    by_sym_sess = defaultdict(dict)
    for sym, cs in kite.items():
        for c in cs:
            by_sym_sess[sym].setdefault(c["time"][:10], []).append(c)
    for sess, recs in per_session.items():
        for r in recs:
            day = by_sym_sess.get(r["sym"], {}).get(sess)
            if not day or len(day) < 2:
                continue
            day = sorted(day, key=lambda c: c["time"])
            kt = (day[-1]["close"] - day[0]["open"]) / day[0]["open"] * 100
            r["kite_target"] = kt
            pairs.append((r["target"], kt))
    if len(pairs) < 100:
        print(f"GATE INCONCLUSIVE: only {len(pairs)} overlapping stock-sessions", flush=True)
        corr, share_off = None, None
    else:
        ys, ks = [p[0] for p in pairs], [p[1] for p in pairs]
        my, mk = st.mean(ys), st.mean(ks)
        num = sum((a - my) * (b - mk) for a, b in zip(ys, ks))
        den = math.sqrt(sum((a - my) ** 2 for a in ys) * sum((b - mk) ** 2 for b in ks))
        corr = num / den if den else None
        share_off = 100 * sum(1 for a, b in pairs if abs(a - b) > 0.25) / len(pairs)
        print(f"  overlap {len(pairs):,} stock-sessions", flush=True)
        print(f"  correlation {corr:.4f}", flush=True)
        print(f"  share differing by > 25 bp: {share_off:.2f}%", flush=True)

    gate = {"overlap": len(pairs), "correlation": corr, "share_over_25bp": share_off}

    # ---- the ten tests --------------------------------------------------
    CONTINUOUS = [("rs10", 1), ("from_high", -1), ("from_low", -1), ("rsi", 1), ("atr_pct", 1)]
    BINARY = [("nr7", 1), ("inside", 1), ("pattern", 1), ("reversal", 1)]

    results = {}
    for name, sign in CONTINUOUS:
        ics = []
        for sess, recs in per_session.items():
            xs = [r[name] for r in recs if r[name] is not None]
            ys = [r["target"] for r in recs if r[name] is not None]
            if len(xs) < MIN_STOCKS_PER_SESSION:
                continue
            ic = spearman(xs, ys)
            if ic is not None:
                ics.append(sign * ic)
        m, t, se = tstat(ics)
        results[name] = {"kind": "rank_ic", "sessions": len(ics), "mean": m, "t": t,
                         "se": se, "p": two_sided_p(t, len(ics)),
                         "pct_positive": 100 * sum(1 for x in ics if x > 0) / len(ics) if ics else None}

    for name, sign in BINARY:
        diffs = []
        for sess, recs in per_session.items():
            flag = [r["target"] for r in recs if r[name]]
            unflag = [r["target"] for r in recs if not r[name]]
            if len(flag) < MIN_PER_SIDE or len(unflag) < MIN_PER_SIDE:
                continue
            diffs.append(sign * (st.mean(flag) - st.mean(unflag)))
        m, t, se = tstat(diffs)
        results[name] = {"kind": "session_diff", "sessions": len(diffs), "mean": m, "t": t,
                         "se": se, "p": two_sided_p(t, len(diffs)),
                         "pct_positive": 100 * sum(1 for x in diffs if x > 0) / len(diffs) if diffs else None}

    # trend: ONE test, up minus down
    diffs = []
    for sess, recs in per_session.items():
        up = [r["target"] for r in recs if r["trend"] == "up"]
        dn = [r["target"] for r in recs if r["trend"] == "down"]
        if len(up) < MIN_PER_SIDE or len(dn) < MIN_PER_SIDE:
            continue
        diffs.append(st.mean(up) - st.mean(dn))
    m, t, se = tstat(diffs)
    results["trend"] = {"kind": "session_diff", "sessions": len(diffs), "mean": m, "t": t,
                        "se": se, "p": two_sided_p(t, len(diffs)),
                        "pct_positive": 100 * sum(1 for x in diffs if x > 0) / len(diffs) if diffs else None}

    # ---- corrections over a family of TEN -------------------------------
    names = list(results)
    ps = [results[n]["p"] if results[n]["p"] is not None else 1.0 for n in names]
    bh = benjamini_hochberg(ps, q=0.10)
    bonf = 0.05 / len(names)
    for i, n in enumerate(names):
        results[n]["bh_survives"] = i in bh
        results[n]["bonferroni_survives"] = ps[i] < bonf

    # detectable effect size from the data (amendment 1)
    for n in names:
        r = results[n]
        r["detectable_at_t2"] = 2 * r["se"] if r["se"] else None

    print(f"\n=== TEN TESTS (family size {len(names)}), selection split only ===")
    print(f"{'feature':<12}{'kind':<14}{'sessions':>9}{'mean':>10}{'t':>8}{'p':>9}"
          f"{'%pos':>7}  BH  Bonf")
    for n in sorted(names, key=lambda k: abs(results[k]["t"] or 0), reverse=True):
        r = results[n]
        print(f"{n:<12}{r['kind']:<14}{r['sessions']:>9}"
              f"{(r['mean'] or 0):>10.4f}{(r['t'] or 0):>8.2f}{(r['p'] or 1):>9.4f}"
              f"{(r['pct_positive'] or 0):>7.1f}"
              f"{'   Y' if r['bh_survives'] else '   .'}"
              f"{'    Y' if r['bonferroni_survives'] else '    .'}")
    print(f"\nBonferroni threshold p < {bonf:.4f}; BH at q=0.10")
    surv = [n for n in names if results[n]["bh_survives"]]
    print(f"Survivors of BH: {surv if surv else 'NONE'}")

    with open(OUT, "w") as f:
        json.dump({"gate": gate, "family_size": len(names), "results": results,
                   "sessions_usable": len(per_session), "stock_sessions": kept,
                   "dropped_warmup": dropped_warmup,
                   "selection_span": [min(per_session), max(per_session)] if per_session else None},
                  f, default=str, indent=1)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
