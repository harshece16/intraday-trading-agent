"""L34 — does universe B clear the reward:risk gate more often than universe A?

Pre-registered in docs/research/prereg-L34-universe-b-rrr-gate.md, committed
(d879219) before this file existed.

The live engine's binding blocker is reward:risk, not the entry signal: 536 of
one day's near-misses were blocked by RRR alone and only 9.6% of 28,300
evaluations reached 1.5. The user asked to widen the universe. This measures
whether a wider universe actually loosens that gate, or whether mid-cap
spreads eat the wider ranges.

PASS RULE, fixed before running: p_B > p_A AND two-proportion z > 2.

Daily data only, no Kite calls, selection window only (held-out untouched).
This is a daily-bar PROXY for the live 5-minute checklist, not a replication
of it — only the DIFFERENCE between the two universes under one identical
rule is interpreted. See the pre-registration's "What this measurement is
NOT".

Universe A's bars and universe B's bars are never held in memory at once
(Entry 6 §E): each chunk is reduced to counters and released.
"""

import json
import math
import statistics as st
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import indicators as ind
import scanner
import universe
from research import splits

YEARS = "8y"                       # matches universe_b_replication.py
CHUNK = 40                         # §E: download and reduce in chunks

# Every constant below is fixed in the pre-registration and is not varied.
WARMUP_BARS = 252
LOOKBACK = 20                      # sessions of structure, strictly before t
MAX_STOP_ATR = 1.5                 # a stop further than this is not a stop
GATE = 1.5                         # the live checklist's reward:risk gate

# Entry 6 §D — universe B pays double the configured slippage per leg.
# 16.60 = charges + 3bp/leg slippage (phase 2, measured).
# 22.60 = the same charges + 6bp/leg. An ASSUMPTION, never tuned afterwards.
ROUND_TRIP_BP = {"A": 16.60, "B": 22.60}

UNIVERSE_B_CSV = Path(__file__).resolve().parents[1] / "data/universe_b.csv"


def universe_b_symbols():
    import csv
    with UNIVERSE_B_CSV.open() as fh:
        return [r["Symbol"].strip().upper() for r in csv.DictReader(fh) if r.get("Symbol")]


class Acc:
    """Counters for one universe. Holds floats, never candles."""

    def __init__(self, label, round_trip_bp):
        self.label = label
        self.cost = round_trip_bp
        self.n_valid = 0
        self.n_pass = 0
        self.n_pass_zero_cost = 0
        self.n_skipped_no_level = 0
        self.n_skipped_wide_stop = 0
        self.symbols_used = 0
        self.by_side = {"long": [0, 0], "short": [0, 0]}   # [valid, pass]
        self.rrr = []
        self.reward_bp = []
        self.risk_bp = []

    def add(self, side, reward_bp_raw, risk_bp_raw):
        reward = reward_bp_raw - self.cost
        risk = risk_bp_raw + self.cost
        rrr = reward / risk
        self.n_valid += 1
        self.rrr.append(rrr)
        self.reward_bp.append(reward_bp_raw)
        self.risk_bp.append(risk_bp_raw)
        self.by_side[side][0] += 1
        if rrr >= GATE:
            self.n_pass += 1
            self.by_side[side][1] += 1
        if reward_bp_raw / risk_bp_raw >= GATE:
            self.n_pass_zero_cost += 1

    @property
    def p(self):
        return self.n_pass / self.n_valid if self.n_valid else float("nan")

    def summary(self):
        q = lambda xs, f: round(st.quantiles(xs, n=100)[f - 1], 4) if len(xs) > 2 else None
        return {
            "universe": self.label,
            "round_trip_bp": self.cost,
            "symbols_used": self.symbols_used,
            "candidates_valid": self.n_valid,
            "candidates_passing": self.n_pass,
            "pass_fraction": round(self.p, 6) if self.n_valid else None,
            "pass_fraction_zero_cost": round(self.n_pass_zero_cost / self.n_valid, 6) if self.n_valid else None,
            "skipped_no_level": self.n_skipped_no_level,
            "skipped_stop_wider_than_1.5atr": self.n_skipped_wide_stop,
            "reward_bp_median": round(st.median(self.reward_bp), 2) if self.reward_bp else None,
            "risk_bp_median": round(st.median(self.risk_bp), 2) if self.risk_bp else None,
            "rrr_min": round(min(self.rrr), 4) if self.rrr else None,
            "rrr_median": round(st.median(self.rrr), 4) if self.rrr else None,
            "rrr_mean": round(st.fmean(self.rrr), 4) if self.rrr else None,
            "rrr_p90": q(self.rrr, 90),
            "long": {"valid": self.by_side["long"][0], "pass": self.by_side["long"][1],
                     "pass_fraction": round(self.by_side["long"][1] / self.by_side["long"][0], 6)
                     if self.by_side["long"][0] else None},
            "short": {"valid": self.by_side["short"][0], "pass": self.by_side["short"][1],
                      "pass_fraction": round(self.by_side["short"][1] / self.by_side["short"][0], 6)
                      if self.by_side["short"][0] else None},
        }


def scan_symbol(bars, sessions_allowed, acc):
    """Reduce one symbol's daily bars to counters. Bars are released by the caller."""
    if len(bars) < WARMUP_BARS + LOOKBACK + 1:
        return False
    used = False
    for i in range(WARMUP_BARS, len(bars)):
        if bars[i]["time"][:10] not in sessions_allowed:
            continue
        entry = bars[i]["close"]
        if entry <= 0:
            continue
        atr = ind.atr(bars[i - 14:i + 1], 14)   # atr() reads only the last 15 bars
        if not atr or atr <= 0:
            continue
        window = bars[i - LOOKBACK:i]          # strictly before t
        hi = max(b["high"] for b in window)
        lo = min(b["low"] for b in window)
        for side in ("long", "short"):
            target, stop = (hi, lo) if side == "long" else (lo, hi)
            if not (target > entry > stop if side == "long" else target < entry < stop):
                acc.n_skipped_no_level += 1
                continue
            if abs(entry - stop) > MAX_STOP_ATR * atr:
                acc.n_skipped_wide_stop += 1
                continue
            acc.add(side,
                    abs(target - entry) / entry * 10_000,
                    abs(entry - stop) / entry * 10_000)
            used = True
    return used


def run_universe(label, symbols, sessions_allowed):
    acc = Acc(label, ROUND_TRIP_BP[label])
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i:i + CHUNK]
        daily = scanner.download_batch([scanner.yf_ticker(s) for s in chunk], YEARS, "1d")
        for s in chunk:
            bars = daily.get(scanner.yf_ticker(s), [])
            if scan_symbol(bars, sessions_allowed, acc):
                acc.symbols_used += 1
        daily.clear()                          # §E: release before the next chunk
        del daily
        print(f"  {label}: {min(i + CHUNK, len(symbols))}/{len(symbols)} symbols, "
              f"{acc.n_valid} candidates", flush=True)
    return acc


def two_proportion_z(x_a, n_a, x_b, n_b):
    p_a, p_b = x_a / n_a, x_b / n_b
    pool = (x_a + x_b) / (n_a + n_b)
    se = math.sqrt(pool * (1 - pool) * (1 / n_a + 1 / n_b))
    return (p_b - p_a) / se if se else float("nan")


def main():
    started = time.time()
    print("L34 — universe B vs A on the reward:risk gate", flush=True)
    print(f"prereg d879219 · gate {GATE} · lookback {LOOKBACK} · warmup {WARMUP_BARS} "
          f"· max stop {MAX_STOP_ATR} ATR", flush=True)

    # The NSE calendar, taken from the index, defines the session set so both
    # universes are measured on IDENTICAL dates by construction.
    nifty = scanner.download_batch([scanner.NIFTY], YEARS, "1d").get(scanner.NIFTY, [])
    all_sessions = sorted({b["time"][:10] for b in nifty})
    selection, held_out = splits.selection_holdout(all_sessions)
    sessions_allowed = set(selection)
    print(f"{len(selection)} selection sessions (< {splits.HELD_OUT_START}), "
          f"{len(held_out)} held-out sessions NOT touched", flush=True)
    print(f"window: {selection[0]} .. {selection[-1]}", flush=True)

    syms_a = [r["symbol"] for r in universe.load()]
    syms_b = universe_b_symbols()
    overlap = sorted(set(syms_a) & set(syms_b))
    print(f"universe A: {len(syms_a)} · universe B: {len(syms_b)} · overlap: {len(overlap)}", flush=True)

    acc_a = run_universe("A", syms_a, sessions_allowed)     # processed and released
    acc_b = run_universe("B", syms_b, sessions_allowed)     # before B is loaded

    z = two_proportion_z(acc_a.n_pass, acc_a.n_valid, acc_b.n_pass, acc_b.n_valid)
    passed = acc_b.p > acc_a.p and z > 2

    # Branch 3 of the falsification tree: wider raw geometry, no better gate.
    wider_geometry = st.median(acc_b.reward_bp) > st.median(acc_a.reward_bp)
    if passed:
        branch = "1 — PASS: p_B > p_A with z > 2"
    elif abs(z) <= 2:
        branch = "2 — null: the two universes are not distinguishable on this gate"
    elif wider_geometry:
        branch = ("3 — B's raw geometry is wider but its pass fraction is not higher: "
                  "costs eat the whole gain")
    else:
        branch = "4 — B is worse on this gate, distinguishably"

    out = {
        "look": "L34",
        "prereg_commit": "d879219",
        "pass_rule": "p_B > p_A AND two-proportion z > 2",
        "result": "PASS" if passed else "FAIL",
        "falsification_branch": branch,
        "z": round(z, 4),
        "p_A": round(acc_a.p, 6),
        "p_B": round(acc_b.p, 6),
        "delta_pp": round((acc_b.p - acc_a.p) * 100, 4),
        "sessions": {"n": len(selection), "first": selection[0], "last": selection[-1],
                     "held_out_untouched": len(held_out)},
        "universe_overlap": len(overlap),
        "A": acc_a.summary(),
        "B": acc_b.summary(),
        "runtime_s": round(time.time() - started, 1),
    }
    dest = Path(__file__).resolve().parents[2] / "docs/research/L34_universe_b_rrr_result.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2), flush=True)
    print(f"\nwrote {dest}", flush=True)


if __name__ == "__main__":
    main()
