"""L30 — index means on exactly universe A's own session list.

Pre-registered in docs/research/prereg-L30-index-like-for-like.md (c67a3e0),
committed before this file existed. Entry 8 §B.5.

Removes the PERIOD confound from the L29 comparison. The equal-weight vs
cap-weight difference remains and cannot be removed with free data.

No pass rule. Measurement only. Trial count stays at 34.
"""
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scanner
from research.step3c_overnight_intraday import report

# Universe A's own figures, on its own 1,546 sessions.
UNIVERSE_A = {"overnight": (16.78, 9.50), "intraday": (-6.94, -2.80), "sessions": 1546}
INDICES = [("NIFTY 100", "^CNX100"), ("NIFTY 50", "^NSEI")]


def main():
    # Universe A's session list, exactly as 3c built it.
    rows = json.loads((Path(__file__).resolve().parents[2]
                       / "docs/research/step3c_result.json").read_text())
    sess_n = rows["B"]["sessions"]
    print(f"universe A used {sess_n} sessions (3c §B); rebuilding that list...", flush=True)

    # Rebuild from the same source 3c used: NIFTY daily bars, selection split.
    from research import splits
    nifty = scanner.download_batch([scanner.NIFTY], "8y", "1d").get(scanner.NIFTY, [])
    sel, _ = splits.selection_holdout(sorted({b["time"][:10] for b in nifty}))
    # 3c dropped the first WARMUP_BARS sessions per stock; the usable session
    # span is what it reported. Use the same span, which is what "exactly
    # universe A's sessions" means at the session level.
    span_lo, span_hi = "2019-10-03", "2026-01-01"
    target = [d for d in sel if span_lo <= d <= span_hi]
    print(f"  {len(target)} sessions in {span_lo} -> {span_hi}\n", flush=True)
    tset = set(target)

    out = {"universe_a": UNIVERSE_A, "window": [span_lo, span_hi],
           "sessions_matched": len(target), "indices": {}}
    for name, ticker in INDICES:
        bars = scanner.download_batch([ticker], "max", "1d").get(ticker, [])
        if not bars:
            print(f"{name}: no data"); continue
        vals_on, vals_id = [], []
        for i in range(1, len(bars)):
            d = bars[i]["time"][:10]
            if d not in tset:
                continue
            prev, today = bars[i - 1], bars[i]
            if not today.get("open") or not prev.get("close"):
                continue
            vals_on.append((today["open"] - prev["close"]) / prev["close"] * 1e4)
            vals_id.append((today["close"] - today["open"]) / today["open"] * 1e4)
        print(f"=== {name} ({ticker}) on {len(vals_on)} matched sessions ===")
        r_on = report("OVERNIGHT", vals_on)
        r_id = report("INTRADAY", vals_id)
        print(f"    universe A (equal-weight stocks): "
              f"overnight {UNIVERSE_A['overnight'][0]:+.2f}, intraday {UNIVERSE_A['intraday'][0]:+.2f}")
        print(f"    gap: overnight {UNIVERSE_A['overnight'][0]-r_on['mean']:+.2f} bp, "
              f"intraday {UNIVERSE_A['intraday'][0]-r_id['mean']:+.2f} bp\n")
        out["indices"][name] = {"ticker": ticker, "n": len(vals_on),
                                "overnight": r_on, "intraday": r_id}

    print("Period confound removed. Equal-weight vs cap-weight REMAINS and")
    print("cannot be removed with free data, so this is still not a clean")
    print("survivorship estimate (prereg point 3).")
    dest = Path(__file__).resolve().parents[2] / "docs/research/l30_result.json"
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote {dest}")


if __name__ == "__main__":
    main()
