"""
Step 3a — opening-range breakout on high relative volume. TRIAL 35.

Implements docs/research/prereg-3a-opening-range.md as amended (amendments
1-3; amendment 3, commit 815ba4c, takes precedence). Self-contained: it does
NOT use backtester.run_backtest(), which enters at the signal bar's close
(amendment 2).

    python -m research.step3a_opening_range --preflight   # counts only, no return read
    python -m research.step3a_opening_range --run         # the single run

Order of operations (amendment 3.1): eligibility -> top-20 by rel_vol ->
signal -> per-trade friction rule -> five-position cap.
"""
import argparse
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

import config
import costs
import kite_history
import universe
from research import splits

OR_BARS = ("09:15", "09:20", "09:25")
FIRST_SIGNAL_BAR = "09:30"
LAST_SIGNAL_BAR = "14:30"          # amendment 1 (d)
EXIT_BAR = "15:10"
REL_VOL_LOOKBACK = 14              # amendment 3.1
TOP_N = 20
MAX_POSITIONS = 5
NOTIONAL = 33000.0                 # amendment 1 (h)
ROUND_TRIP_BP = 16.60
MAX_FRICTION_R = 0.15
MIN_STOP_BP = ROUND_TRIP_BP / MAX_FRICTION_R   # 110.67
MIN_SESSIONS = 60                  # amendment 3.3, count check
OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "research"


def load_days(symbols):
    """{sym: {date: {HH:MM: bar}}}, selection dates only. Held-out bars are
    dropped here, before anything else can see them."""
    kite = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL)
    by = {}
    for sym, cs in kite.items():
        days = defaultdict(dict)
        for c in cs:
            d = c["time"][:10]
            if d < splits.HELD_OUT_START:
                days[d][c["time"][11:16]] = c
        by[sym] = dict(days)
    return by


def opening_range(day):
    """(high, low, volume) of the 09:15-09:30 range, or None if any bar is missing."""
    bars = [day.get(t) for t in OR_BARS]
    if not all(bars):
        return None
    return (max(b["high"] for b in bars), min(b["low"] for b in bars),
            sum(b["volume"] or 0 for b in bars))


def rel_vol_table(by):
    """{date: {sym: rel_vol}} for eligible stock-sessions only (amendment 3.1)."""
    out = defaultdict(dict)
    for sym, days in by.items():
        prior = []                                   # this name's own OR volumes, oldest first
        for d in sorted(days):
            rng = opening_range(days[d])
            if rng is None:
                continue
            if len(prior) >= REL_VOL_LOOKBACK:
                base = st.mean(prior[-REL_VOL_LOOKBACK:])
                if base > 0:
                    out[d][sym] = rng[2] / base
            prior.append(rng[2])
    return out


def top_names(rel):
    """Top 20 by rel_vol; a tie at the boundary is broken alphabetically."""
    return {s for s, _ in sorted(rel.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]}


def find_signal(day):
    """First bar from 09:30 to 14:30 that CLOSES beyond the range; entry is the
    open of the NEXT bar, never the signal bar's close (amendment 1 b)."""
    rng = opening_range(day)
    if rng is None:
        return None
    hi, lo, _ = rng
    times = sorted(day)
    for i, t in enumerate(times):
        if t < FIRST_SIGNAL_BAR or t > LAST_SIGNAL_BAR:
            continue
        close = day[t]["close"]
        side = "BUY" if close > hi else "SELL" if close < lo else None
        if side is None:
            continue
        if i + 1 >= len(times) or times[i + 1] > EXIT_BAR:
            return None
        entry_t = times[i + 1]
        entry = day[entry_t]["open"]
        stop = lo if side == "BUY" else hi
        if not entry or (side == "BUY" and entry <= stop) or (side == "SELL" and entry >= stop):
            return None
        return {"signal_t": t, "entry_t": entry_t, "side": side, "entry": entry,
                "stop": stop, "stop_bp": abs(entry - stop) / entry * 1e4,
                "range_bp": (hi - lo) / lo * 1e4}
    return None


def simulate(day, sig):
    """Walk from the entry bar to the 15:10 close. Stop fills per amendment 1 (c):
    a bar opening beyond the stop fills at its open, an intrabar touch fills at
    the stop price, and the entry bar itself can stop the trade."""
    long = sig["side"] == "BUY"
    stop = sig["stop"]
    exit_px, exit_t, reason = None, None, "timeout"
    for t in sorted(day):
        if t < sig["entry_t"] or t > EXIT_BAR:
            continue
        b = day[t]
        exit_px, exit_t = b["close"], t              # overwritten until the last bar <= 15:10
        gapped = t != sig["entry_t"] and (b["open"] <= stop if long else b["open"] >= stop)
        if gapped:
            exit_px, reason = b["open"], "stop_gap"
            break
        if (b["low"] <= stop) if long else (b["high"] >= stop):
            exit_px, reason = stop, "stop"
            break
    sign = 1 if long else -1
    entry = sig["entry"]
    gross_bp = sign * (exit_px - entry) / entry * 1e4

    cfg = config.COSTS
    exit_side = "SELL" if long else "BUY"
    e_fill = costs.apply_slippage(sig["side"], entry, cfg)
    x_fill = costs.apply_slippage(exit_side, exit_px, cfg)
    qty = NOTIONAL / entry
    charges = costs.leg_cost(sig["side"], e_fill, qty, cfg) + costs.leg_cost(exit_side, x_fill, qty, cfg)
    net_bp = (sign * (x_fill - e_fill) * qty - charges) / NOTIONAL * 1e4
    return {**sig, "exit_t": exit_t, "exit": exit_px, "reason": reason,
            "gross_bp": gross_bp, "net_bp": net_bp,
            "gross_r": gross_bp / sig["stop_bp"], "net_r": net_bp / sig["stop_bp"]}


def candidates(by, sessions, rel):
    """Per session: every signal, tagged with top-20 membership and whether the
    friction rule keeps it. No return is computed here."""
    out = {}
    for d in sessions:
        top = top_names(rel.get(d, {}))
        sigs = []
        for sym, days in by.items():
            day = days.get(d)
            sig = find_signal(day) if day else None
            if sig:
                sigs.append({**sig, "sym": sym, "date": d, "top20": sym in top,
                             "kept": sig["stop_bp"] >= MIN_STOP_BP})
        out[d] = sorted(sigs, key=lambda s: (s["signal_t"], s["sym"]))
    return out


def capped(by, sigs):
    """Five concurrent positions, chronological by signal bar, ties alphabetical
    (Entry 8 e). A friction-skipped signal takes no slot."""
    taken = []
    for s in sigs:                                   # already sorted (signal_t, sym)
        open_now = sum(1 for tr in taken
                       if tr["reason"] == "timeout" or tr["exit_t"] >= s["entry_t"])
        if open_now < MAX_POSITIONS:
            taken.append({**simulate(by[s["sym"]][s["date"]], s), "sym": s["sym"], "date": s["date"]})
    return taken


def summarise(trades, label):
    """Session means are the unit (amendment 1 a); pooled per-trade is secondary."""
    if not trades:
        return {"label": label, "n_trades": 0, "n_sessions": 0}
    by_d = defaultdict(list)
    for t in trades:
        by_d[t["date"]].append(t)
    out = {"label": label, "n_trades": len(trades), "n_sessions": len(by_d),
           "trades_per_session": len(trades) / len(by_d)}
    n = len(by_d)
    for k in ("net_bp", "gross_bp", "net_r", "gross_r"):
        means = [st.mean(t[k] for t in ts) for ts in by_d.values()]
        sd = st.stdev(means) if n > 1 else float("nan")
        out[k] = {"session_mean": st.mean(means), "sd": sd,
                  "t": st.mean(means) / (sd / math.sqrt(n)) if n > 1 and sd > 0 else None,
                  "pooled_trade_mean": st.mean(t[k] for t in trades)}
    out["mde_net_bp_at_t2"] = 2 * out["net_bp"]["sd"] / math.sqrt(n) if n > 1 else None
    out["exit_mix"] = {r: sum(1 for t in trades if t["reason"] == r) for r in ("stop", "stop_gap", "timeout")}
    out["median_stop_bp"] = st.median(t["stop_bp"] for t in trades)
    return out


def preflight(by, sessions, rel):
    cand = candidates(by, sessions, rel)
    alls = [s for d in sessions for s in cand[d]]
    top = [s for s in alls if s["top20"]]
    widths = [(r[0] - r[1]) / r[1] * 1e4 for days in by.values() for day in days.values()
              for r in [opening_range(day)] if r and r[1]]
    res = {
        "sessions_in_cache_selection": len(sessions),
        "sessions_with_a_top20_set": sum(1 for d in sessions if rel.get(d)),
        "eligible_stock_sessions": sum(len(rel.get(d, {})) for d in sessions),
        "median_opening_range_width_bp_descriptive": st.median(widths) if widths else None,
        "min_stop_bp": MIN_STOP_BP,
        "top20": {"candidates": len(top), "removed_by_friction_rule": sum(1 for s in top if not s["kept"]),
                  "surviving": sum(1 for s in top if s["kept"])},
        "all100": {"candidates": len(alls), "removed_by_friction_rule": sum(1 for s in alls if not s["kept"]),
                   "surviving": sum(1 for s in alls if s["kept"])},
        # The first surviving signal of a session always gets a slot, so this
        # equals sessions with >= 1 surviving CAPPED trade without simulating exits.
        "sessions_with_surviving_top20_trade": len({s["date"] for s in top if s["kept"]}),
        "min_sessions_required": MIN_SESSIONS,
    }
    res["untestable_at_preflight"] = res["sessions_with_surviving_top20_trade"] < MIN_SESSIONS
    return res, cand


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--preflight", action="store_true")
    g.add_argument("--run", action="store_true")
    args = ap.parse_args()

    symbols = [r["symbol"] for r in universe.load()]
    by = load_days(symbols)
    sessions = sorted({d for days in by.values() for d in days})
    assert all(d < splits.HELD_OUT_START for d in sessions)
    first, second = splits.halves(sessions)          # amendment 1 (g)
    rel = rel_vol_table(by)
    pf, cand = preflight(by, sessions, rel)
    pf["symbols_with_cache"] = len(by)
    pf["span"] = [sessions[0], sessions[-1]]
    pf["halves_split_at"] = second[0]
    print(json.dumps(pf, indent=2))
    (OUT_DIR / "step3a_preflight.json").write_text(json.dumps(pf, indent=2))
    if args.preflight:
        return
    if pf["untestable_at_preflight"]:
        print("UNTESTABLE at pre-flight - not run, no return read.")
        return

    # Sessions before any name is eligible have no top-20 set; the all-100 line
    # uses the same sessions so the three lines are comparable.
    live = [d for d in sessions if rel.get(d)]
    primary = [t for d in live for t in capped(by, [s for s in cand[d] if s["top20"] and s["kept"]])]
    sim = lambda s: {**simulate(by[s["sym"]][s["date"]], s), "sym": s["sym"], "date": s["date"]}
    unc_top = [sim(s) for d in live for s in cand[d] if s["top20"] and s["kept"]]
    unc_all = [sim(s) for d in live for s in cand[d] if s["kept"]]

    h1 = set(first)
    res = {
        "preflight": pf,
        "primary": summarise(primary, "PRIMARY top-20, friction rule, capped at 5"),
        "primary_first_half": summarise([t for t in primary if t["date"] in h1], "first half"),
        "primary_second_half": summarise([t for t in primary if t["date"] not in h1], "second half"),
        "primary_long": summarise([t for t in primary if t["side"] == "BUY"], "longs"),
        "primary_short": summarise([t for t in primary if t["side"] == "SELL"], "shorts"),
        "secondary_uncapped_top20": summarise(unc_top, "SECONDARY uncapped top-20 (no pass rule)"),
        "secondary_uncapped_all100": summarise(unc_all, "SECONDARY uncapped all-100, no rel-vol filter (no pass rule)"),
    }
    p = res["primary"]
    mde = p["mde_net_bp_at_t2"]
    print(f"\nPOWER: sd(session means) = {p['net_bp']['sd']:.2f} bp, n = {p['n_sessions']}, "
          f"MDE at t=2 = {mde:.2f} bp (untestable if > {ROUND_TRIP_BP})")
    halves_ok = (res["primary_first_half"]["net_bp"]["session_mean"] > 0
                 and res["primary_second_half"]["net_bp"]["session_mean"] > 0)
    if mde > ROUND_TRIP_BP:
        verdict = "UNTESTABLE"
    elif p["net_bp"]["session_mean"] > 0 and p["net_bp"]["t"] > 2 and halves_ok:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    res["verdict"] = verdict
    print(f"VERDICT: {verdict}\n")
    print(json.dumps(res, indent=2))
    (OUT_DIR / "step3a_result.json").write_text(json.dumps(res, indent=2))
    (OUT_DIR / "data").mkdir(exist_ok=True)
    (OUT_DIR / "data" / "step3a_trades.json").write_text(json.dumps(primary))


if __name__ == "__main__":
    main()
