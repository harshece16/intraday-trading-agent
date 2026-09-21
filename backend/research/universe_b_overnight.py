"""Universe B overnight/intraday decomposition — Entry 7 §B.2.

Pre-registered in docs/research/prereg-universe-b-addendum-overnight.md,
committed (9530c22) before this file existed and before any universe B
overnight value was computed.

PASS RULE, fixed before running: the quiet-minus-volatile OVERNIGHT spread
must have the same sign as universe A's and |t| > 2. The intraday spread is
reported whatever it is, with no pass rule.

Selection dates only; universe B's 2026 data is not touched. Daily bars,
no Kite calls.
"""

import csv
import json
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import scanner
from research import splits
from research.step2_followups import MIN_STOCKS_PER_SESSION, WARMUP_BARS
from research.step3c_overnight_intraday import QUINTILES, report

YEARS = "8y"
CHUNK = 40
UNIVERSE_B = Path(__file__).resolve().parents[1] / "data/universe_b.csv"
CACHE = Path(__file__).resolve().parents[1] / "data/universe_b_overnight_rows.json"

# Universe A, quoted in the prereg before this ran.
A_UNCONDITIONAL = {"overnight": (16.78, 9.50), "intraday": (-6.94, -2.80)}
A_SPREAD = {"overnight": (-13.83, -9.79), "intraday": (7.40, 2.38)}

SUBWINDOW_YEARS = 4          # declared in the prereg as a secondary line


def build():
    if CACHE.exists():
        blob = json.loads(CACHE.read_text())
        print(f"Reusing {CACHE.name} ({blob['sessions']} sessions)", flush=True)
        return blob["per_session"]

    with UNIVERSE_B.open() as f:
        symbols = [r["Symbol"].strip() for r in csv.DictReader(f) if r["Symbol"].strip()]
    print(f"Universe B: {len(symbols)} symbols", flush=True)

    daily = {}
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i:i + CHUNK]
        print(f"  downloading {i+1}-{i+len(chunk)}...", flush=True)
        daily.update(scanner.download_batch([scanner.yf_ticker(s) for s in chunk], YEARS, "1d"))
    nifty = scanner.download_batch([scanner.NIFTY], YEARS, "1d").get(scanner.NIFTY, [])
    ndates = [b["time"][:10] for b in nifty]
    ncloses = [b["close"] for b in nifty]

    bars_by = {s: b for s in symbols if (b := daily.get(scanner.yf_ticker(s)))}
    print(f"  {len(bars_by)} symbols with bars", flush=True)

    selection, _ = splits.selection_holdout(sorted({b["time"][:10] for b in nifty}))
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
                "atr_pct": prof["atr_pct"],
                "overnight": (today["open"] - prev["close"]) / prev["close"] * 1e4,
                "intraday": (today["close"] - today["open"]) / today["open"] * 1e4,
            })
        if (si + 1) % 400 == 0:
            print(f"    {si+1}/{len(selection)}, {(time.time()-started)/60:.0f} min", flush=True)

    usable = {s: v for s, v in per_session.items() if len(v) >= MIN_STOCKS_PER_SESSION}
    print(f"  {len(usable)} usable sessions", flush=True)
    CACHE.write_text(json.dumps({"per_session": usable, "sessions": len(usable)}))
    return usable


def measure(per_session, label):
    print(f"\n{'='*74}\n{label}\n{'='*74}")
    sessions = sorted(per_session)
    print(f"  {len(sessions)} sessions, {sessions[0]} -> {sessions[-1]}")
    breadth = [len(v) for v in per_session.values()]
    print(f"  per-session breadth: median {st.median(breadth):.0f}")

    print("\n-- L27 unconditional means --")
    on = [st.mean(r["overnight"] for r in v) for v in per_session.values()]
    idy = [st.mean(r["intraday"] for r in v) for v in per_session.values()]
    r_on = report("OVERNIGHT", on)
    r_id = report("INTRADAY", idy)
    for k, (m, t) in A_UNCONDITIONAL.items():
        print(f"      universe A {k}: {m:+.2f} bp (t={t:+.2f})")

    print("\n-- L28 volatility-sorted --")
    on_q, id_q = defaultdict(list), defaultdict(list)
    sp_on, sp_id = [], []
    for v in per_session.values():
        u = sorted([r for r in v if r["atr_pct"] is not None], key=lambda r: r["atr_pct"])
        n = len(u)
        if n < MIN_STOCKS_PER_SESSION:
            continue
        for qi in range(QUINTILES):
            lo, hi = qi * n // QUINTILES, (qi + 1) * n // QUINTILES
            if hi > lo:
                on_q[qi].append(st.mean(r["overnight"] for r in u[lo:hi]))
                id_q[qi].append(st.mean(r["intraday"] for r in u[lo:hi]))
        k = n // QUINTILES
        sp_on.append(st.mean(r["overnight"] for r in u[:k]) - st.mean(r["overnight"] for r in u[-k:]))
        sp_id.append(st.mean(r["intraday"] for r in u[:k]) - st.mean(r["intraday"] for r in u[-k:]))

    print(f"  {'quintile':<10} {'overnight':>12} {'intraday':>12} {'sum':>12}")
    quints = {}
    for qi in range(QUINTILES):
        if not on_q[qi]:
            continue
        o, i = st.mean(on_q[qi]), st.mean(id_q[qi])
        tag = "quietest" if qi == 0 else "MOST VOL" if qi == QUINTILES - 1 else ""
        print(f"  Q{qi+1:<9} {o:+10.2f}bp {i:+10.2f}bp {o+i:+10.2f}bp  {tag}")
        quints[f"Q{qi+1}"] = {"overnight": o, "intraday": i}

    print()
    s_on = report("quiet-minus-volatile OVERNIGHT", sp_on)
    s_id = report("quiet-minus-volatile INTRADAY", sp_id)
    for k, (m, t) in A_SPREAD.items():
        print(f"      universe A {k} spread: {m:+.2f} bp (t={t:+.2f})")

    # ---- the pre-registered pass rule ----------------------------------
    a_m, _ = A_SPREAD["overnight"]
    same_sign = s_on.get("mean") is not None and s_on["mean"] * a_m > 0
    big = s_on.get("t") is not None and abs(s_on["t"]) > 2
    passed = bool(same_sign and big)
    print(f"\n  PASS RULE (overnight spread): same sign? {same_sign}  |t|>2? {big}")
    print(f"  >>> {'PASS' if passed else 'FAIL'} <<<")
    if s_on.get("mean"):
        print(f"      retained {s_on['mean']/a_m:.2f}x of universe A's overnight spread")
    print("\n  Intraday spread carries NO pass rule and is reported as measured.")
    print("  No overnight figure is compared against a cost bar here: capturing")
    print("  it is cash DELIVERY, and that sheet is Entry 7 §D.2.")

    return {"sessions": len(per_session), "unconditional": {"overnight": r_on, "intraday": r_id},
            "quintiles": quints, "spread_overnight": s_on, "spread_intraday": s_id,
            "passed": passed}


def main():
    per_session = build()
    primary = measure(per_session, "UNIVERSE B — OVERNIGHT vs INTRADAY (8y, PRIMARY)")

    # Secondary, declared in the prereg before running.
    cutoff = f"{int(max(per_session)[:4]) - SUBWINDOW_YEARS}{max(per_session)[4:]}"
    recent = {s: v for s, v in per_session.items() if s >= cutoff}
    secondary = measure(recent, f"SECONDARY — most recent {SUBWINDOW_YEARS}y (>= {cutoff}), NO pass rule")

    dest = Path(__file__).resolve().parents[2] / "docs/research/universe_b_overnight_result.json"
    dest.write_text(json.dumps({"primary_8y": primary, f"secondary_{SUBWINDOW_YEARS}y": secondary},
                               indent=2, default=str))
    print(f"\nWrote {dest}")


if __name__ == "__main__":
    main()
