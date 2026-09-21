"""Entry 7 §D.1 — the overnight/intraday split on the INDEX series itself.

Why this exists: universe A's +16.78 bp overnight / -6.94 bp intraday split
is measured on today's NIFTY 100 members applied to history, so it is
inflated by survivorship. An index series is point-in-time by construction —
it already contains the constituent changes — so it answers how much of the
split survives without that bias.

Measurement only. No trial. Research look L29. Selection dates only.
"""

import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scanner
from research import splits
from research.step3c_overnight_intraday import report

# yfinance tickers for the Indian index series.
INDICES = [("NIFTY 50", "^NSEI"), ("NIFTY 100", "^CNX100"), ("NIFTY BANK", "^NSEBANK")]
YEARS = "max"          # §D.1: the longest history yfinance gives


def main():
    out = {}
    for name, ticker in INDICES:
        print(f"\n{'='*70}\n{name}  ({ticker})\n{'='*70}", flush=True)
        try:
            bars = scanner.download_batch([ticker], YEARS, "1d").get(ticker, [])
        except Exception as exc:                       # noqa: BLE001
            print(f"  download failed: {exc}")
            out[name] = {"error": str(exc)}
            continue
        if not bars:
            print("  no data returned — NOT estimated, recorded as unavailable")
            out[name] = {"error": "no data"}
            continue

        sessions = [b["time"][:10] for b in bars]
        selection, _ = splits.selection_holdout(sessions)
        sel = set(selection)

        rows = []
        for i in range(1, len(bars)):
            d = bars[i]["time"][:10]
            if d not in sel:
                continue
            prev, today = bars[i - 1], bars[i]
            if not today.get("open") or not prev.get("close") or not today.get("close"):
                continue
            rows.append({
                "date": d,
                "overnight": (today["open"] - prev["close"]) / prev["close"] * 1e4,
                "intraday": (today["close"] - today["open"]) / today["open"] * 1e4,
            })
        if len(rows) < 100:
            print(f"  only {len(rows)} usable sessions — too few, recorded as unavailable")
            out[name] = {"error": f"only {len(rows)} sessions"}
            continue

        print(f"  {len(rows):,} sessions, {rows[0]['date']} -> {rows[-1]['date']}")
        r_on = report("OVERNIGHT", [r["overnight"] for r in rows])
        r_id = report("INTRADAY", [r["intraday"] for r in rows])
        tot = r_on["mean"] + r_id["mean"]
        print(f"  -> total {tot:+.2f} bp/day: overnight {r_on['mean']:+.2f}, "
              f"intraday {r_id['mean']:+.2f}")
        share = 100 * r_on["mean"] / tot if tot else float("nan")
        print(f"  -> overnight is {share:.0f}% of the total daily return")

        # §D.1: by calendar year, so concentration is visible.
        print(f"\n  {'year':<6} {'n':>5} {'overnight':>12} {'intraday':>12} {'total':>10}")
        by_year = defaultdict(list)
        for r in rows:
            by_year[r["date"][:4]].append(r)
        years = {}
        for y in sorted(by_year):
            v = by_year[y]
            if len(v) < 50:
                continue
            o = st.mean(r["overnight"] for r in v)
            i = st.mean(r["intraday"] for r in v)
            flag = "" if o > 0 and i < 0 else "  <- split does NOT hold"
            print(f"  {y:<6} {len(v):>5} {o:+10.2f}bp {i:+10.2f}bp {o+i:+8.2f}bp{flag}")
            years[y] = {"n": len(v), "overnight": o, "intraday": i}

        held = sum(1 for y in years.values() if y["overnight"] > 0 and y["intraday"] < 0)
        print(f"\n  the overnight>0 / intraday<0 split holds in "
              f"{held} of {len(years)} calendar years")
        out[name] = {"ticker": ticker, "sessions": len(rows),
                     "span": [rows[0]["date"], rows[-1]["date"]],
                     "overnight": r_on, "intraday": r_id,
                     "overnight_share_pct": share, "by_year": years,
                     "years_split_holds": held, "years_total": len(years)}

    dest = Path(__file__).resolve().parents[2] / "docs/research/index_overnight_result.json"
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote {dest}")


if __name__ == "__main__":
    main()
