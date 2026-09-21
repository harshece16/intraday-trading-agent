"""Supplementary null run that PERSISTS TRADE LISTS, for Entry 2 section B2.

Approved by the reviewer 2026-09-20 as an exception to "no new simulation",
because the main run discards per-trade records inside summarise() and the
B2 diagnostic needs bar geometry and per-side breakdowns.

Identical null construction to the main run (same seeds offset, same
bootstrap triples, same hour profile, same fire_p) so it samples the same
process — only the persistence differs.

Originally scoped to the negative-fail branch. **Reviewer Entry 3 §A directs
it to run anyway**, because the step-1 results file asserted that stop-first
and gap-through "account for" the −0.05R harness bias and nothing had
measured that. The reviewer's objection is the right one: positions are
intraday so there are no overnight gaps, and a single 5-minute bar spanning a
42 bp stop AND a ~95 bp target should be rare when the 5-minute ATR is ~12 bp.

Logged in trials.md as a research look, not a strategy trial: it selects no
strategy and measures the harness.

Diagnostics produced, all on the null's own trades:
  (a) trades where a single bar spanned both stop and target (stop-first rule)
  (b) stops filled at the open after a gap-through, and the extra loss in R
  (c) seed-mean gross excluding (a) and (b); and with (a) scored at midpoint
  (d) mean R by side — the null is 59.7% long, so market drift shows up here
"""
import json
from collections import defaultdict
import random
import statistics as st
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backtester
import config
import costs as costs_mod
import kite_history
from research import null_test as nt
import scanner
import strategy_engine
import universe

SEEDS = 20
OUT = str(Path(__file__).resolve().parents[2] / "docs/research/data/null_diagnostic.json")
PROGRESS = str(Path(__file__).resolve().parents[2] / "docs/research/progress.md")
NULL_NAME = "_null_diag"
# The backtester's own string for a target exit. Spelled wrong once
# ("target"), which silently made the (b2) sample empty and printed
# "0 of 0 target exits" as if it were a finding.
TARGET_REASON = "take_profit"
DAYS = 730


def note_progress(done, total, started):
    """Counts and timing only — no interim statistics (Entry 2 section A)."""
    el = time.time() - started
    eta = time.strftime("%Y-%m-%d %H:%M", time.localtime(started + el / done * total)) if done else "?"
    line = (f"| {time.strftime('%H:%M')} | supplementary null diagnostic: "
            f"{done}/{total} seeds, {el/60:.0f} min elapsed, est. finish {eta} |\n")
    try:
        with open(PROGRESS, "a") as f:
            f.write(line)
    except OSError:
        pass


# ---------------------------------------------------------------- analysis


def _ci95(vals):
    if len(vals) < 3:
        return (None, None, None)
    m = st.mean(vals)
    se = st.stdev(vals) / (len(vals) ** 0.5)
    return m, se, (m - 1.96 * se, m + 1.96 * se)


def analyse(all_trades, seeds):
    """Entry 2 §B2 (a)-(d) plus Entry 3 §A's two additions. Every figure is a
    SEED-MEAN where the main run reported seed-means, so the numbers are
    comparable with the -0.0495R the pass rule was judged on."""
    rows = []
    for t in all_trades:
        rps, qty = t.get("risk_per_share"), t.get("qty")
        if not rps or not qty:
            continue
        long = t["side"] == "LONG"
        bar = t.get("_exit_bar")
        stop, target, entry = t.get("stop"), t.get("target"), t["entry_price"]
        r = {
            "seed": t["_seed"], "side": t["side"], "reason": t["reason"],
            "gross_r": t["gross_pnl"] / (rps * qty),
            "spanned": False, "stop_gapped": False, "extra_loss_r": 0.0,
            "target_gapped": False, "target_gain_r": 0.0,
        }
        # (a) did the EXIT BAR contain both barriers?
        if bar and stop and target:
            lo, hi = bar["low"], bar["high"]
            r["spanned"] = (lo <= stop <= hi) and (lo <= target <= hi)
        # (b) stop filled materially beyond the stop price
        if t["reason"] == "stop_loss" and stop:
            beyond = (stop - t["exit_price"]) if long else (t["exit_price"] - stop)
            if beyond > rps * 0.05:
                r["stop_gapped"] = True
                r["extra_loss_r"] = beyond / rps
        # Entry 3 §A: when a TARGET gaps through, does it fill at the open
        # (better than target) or at the target price?
        if t["reason"] == TARGET_REASON and target:
            better = (t["exit_price"] - target) if long else (target - t["exit_price"])
            if better > rps * 0.05:
                r["target_gapped"] = True
                r["target_gain_r"] = better / rps
        r["mid_r"] = (abs(target - entry) / rps - 1.0) / 2 if target else 0.0
        rows.append(r)

    n = len(rows)
    by_seed = defaultdict(list)
    for r in rows:
        by_seed[r["seed"]].append(r)

    def seed_mean(pick, score=lambda r: r["gross_r"]):
        per = []
        for s_ in sorted(by_seed):
            vals = [score(r) for r in by_seed[s_] if pick(r)]
            if vals:
                per.append(st.mean(vals))
        return _ci95(per)

    print("\n" + "=" * 70)
    print(f"NULL DIAGNOSTIC — {n:,} trades across {seeds} seeds, zero-cost")
    print("=" * 70)

    base_m, base_se, base_ci = seed_mean(lambda r: True)
    print(f"\nBaseline seed-mean gross: {base_m:+.4f}R  "
          f"(SE {base_se:.4f}, CI [{base_ci[0]:+.4f}, {base_ci[1]:+.4f}])")
    print("  main run reported -0.0495R over 200 seeds — this is 20 seeds, so")
    print("  it is a noisier estimate of the same quantity.")

    # (a)
    spanned = [r for r in rows if r["spanned"]]
    print(f"\n(a) single bar spanned BOTH stop and target (stop-first rule applied)")
    print(f"    {len(spanned):,} of {n:,} trades = {100*len(spanned)/n:.2f}%")
    if spanned:
        print(f"    their mean gross: {st.mean(r['gross_r'] for r in spanned):+.4f}R")

    # (b)
    gapped = [r for r in rows if r["stop_gapped"]]
    print(f"\n(b) stops filled materially beyond the stop price (gap-through)")
    print(f"    {len(gapped):,} of {n:,} trades = {100*len(gapped)/n:.2f}%")
    if gapped:
        print(f"    mean EXTRA loss on those: {st.mean(r['extra_loss_r'] for r in gapped):.4f}R")
        print(f"    spread over ALL trades:   "
              f"{sum(r['extra_loss_r'] for r in gapped)/n:.4f}R per trade")

    # Entry 3 §A addition — the symmetric question
    tg = [r for r in rows if r["target_gapped"]]
    targets = [r for r in rows if r["reason"] == TARGET_REASON]
    print(f"\n(b2) targets that gapped through and filled BETTER than target")
    print(f"    {len(tg):,} of {len(targets):,} target exits = "
          f"{100*len(tg)/len(targets) if targets else 0:.2f}%")
    if tg:
        print(f"    mean EXTRA gain on those: {st.mean(r['target_gain_r'] for r in tg):.4f}R")
        print(f"    spread over ALL trades:   "
              f"{sum(r['target_gain_r'] for r in tg)/n:.4f}R per trade")
    print("    -> if stops gap but targets do not, the fill rule is asymmetric")

    # (c)
    print(f"\n(c) recomputed seed-mean gross")
    ex_m, _, ex_ci = seed_mean(lambda r: not r["spanned"] and not r["stop_gapped"])
    print(f"    excluding (a) and (b):          {ex_m:+.4f}R  "
          f"CI [{ex_ci[0]:+.4f}, {ex_ci[1]:+.4f}]   "
          f"(moves {ex_m-base_m:+.4f}R)")
    mid_m, _, mid_ci = seed_mean(lambda r: True,
                                 lambda r: r["mid_r"] if r["spanned"] else r["gross_r"])
    print(f"    (a) scored at stop/target mid: {mid_m:+.4f}R  "
          f"CI [{mid_ci[0]:+.4f}, {mid_ci[1]:+.4f}]   "
          f"(moves {mid_m-base_m:+.4f}R)")

    # (d)
    print(f"\n(d) mean gross R by side  (the null is ~59.7% long)")
    for side in ("LONG", "SHORT"):
        sm, sse, sci = seed_mean(lambda r, s_=side: r["side"] == s_)
        share = 100 * sum(1 for r in rows if r["side"] == side) / n
        if sm is not None:
            print(f"    {side:<6} {share:5.1f}% of trades   {sm:+.4f}R   "
                  f"CI [{sci[0]:+.4f}, {sci[1]:+.4f}]")
    print("    -> a market-wide drift would show as long and short differing")

    print("\n" + "=" * 70)
    out = {
        "seeds": seeds, "trades": n, "baseline_seed_mean_gross": base_m,
        "spanned_pct": 100 * len(spanned) / n,
        "stop_gapped_pct": 100 * len(gapped) / n,
        "stop_gap_cost_r_per_trade": sum(r["extra_loss_r"] for r in gapped) / n,
        "target_gapped_pct": 100 * len(tg) / len(targets) if targets else None,
        "target_gap_gain_r_per_trade": sum(r["target_gain_r"] for r in tg) / n,
        "excl_ab_seed_mean": ex_m, "mid_scored_seed_mean": mid_m,
    }
    dest = Path(__file__).resolve().parents[2] / "docs/research/null_diagnostic_result.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"Wrote {dest}")
    return out


def main():
    blob, real_trades, triples, hour_weights = nt.load_real()
    long_frac = sum(1 for t in real_trades if t["side"] == "LONG") / len(real_trades)

    rows = universe.load()
    symbols = [r["symbol"] for r in rows]
    preloaded = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=DAYS)
    sessions = sorted({c["time"][:10] for cs in preloaded.values() for c in cs})
    daily = scanner.download_batch([scanner.yf_ticker(s) for s in symbols] + [scanner.NIFTY], "2y", "1d")
    picks = scanner.premarket_picks(daily, rows, sessions, 5, config.SCANNER, allow_shorts=True)

    # bar lookup so (a) can be reconstructed: did the exit bar span both barriers?
    bars_by = {s: {c["time"]: c for c in cs} for s, cs in preloaded.items()}

    risk_cfg = {**config.RISK, "min_confidence_to_trade": 0}
    params = {"entry_mode": "checklist", "max_entries_per_day": 1}
    started = time.time()
    all_trades = []

    for seed in range(SEEDS):
        rng = random.Random(10_000 + seed)       # same seeds as the main run
        strategy_engine.STRATEGY_FUNCTIONS[NULL_NAME] = nt.make_null(
            rng, triples, hour_weights, long_frac, 0.0073)
        trades, _ = backtester.run_backtest(
            sorted(preloaded), NULL_NAME, params, risk_cfg, config.CANDLE_INTERVAL, DAYS,
            costs_cfg=costs_mod.ZERO_COSTS, preloaded=preloaded,
            allowed_by_day=picks, scorecard=[])
        for t in trades:
            if t.get("r") is None or not t.get("risk_per_share"):
                continue
            bar = bars_by.get(t["symbol"], {}).get(t.get("exit_time"))
            t["_exit_bar"] = {"high": bar["high"], "low": bar["low"], "open": bar["open"]} if bar else None
            t["_seed"] = seed
            all_trades.append(t)
        note_progress(seed + 1, SEEDS, started)
    strategy_engine.STRATEGY_FUNCTIONS.pop(NULL_NAME, None)

    with open(OUT, "w") as f:
        json.dump({"seeds": SEEDS, "trades": all_trades}, f, default=str)
    print(f"persisted {len(all_trades)} null trades across {SEEDS} seeds -> {OUT}")
    analyse(all_trades, SEEDS)


def analyse_only():
    """Re-derive the diagnostics from persisted trades. No simulation."""
    with open(OUT) as f:
        blob = json.load(f)
    analyse(blob["trades"], blob["seeds"])


if __name__ == "__main__":
    if "--analyse-only" in sys.argv:
        analyse_only()
        raise SystemExit(0)
    main()
