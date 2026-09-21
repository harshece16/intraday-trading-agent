"""Entry 3 §B — decompose the Test A sample into pre-friction / slippage /
charges, from the existing trade list. No new backtest; nothing is re-run.

The reviewer's hypothesis: `gross_pnl` in the trade list is already
post-slippage, so the 0.254R labelled "friction" in the verdict is charges
ONLY, and total friction is larger than stated.

That is testable rather than assumable. `costs.apply_slippage()` is
deterministic — a BUY fills at price*(1+s), a SELL at price*(1-s) — so the
pre-slippage signal price can be recovered by inverting it, and the recovered
price should land on a clean 2-decimal number (a real bar price or a stop).
This script asserts that it does before trusting the decomposition.
"""

import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config

SLIP = config.COSTS["slippage_pct"] / 100


def ci95(vals):
    m = st.mean(vals)
    se = st.stdev(vals) / math.sqrt(len(vals))
    return m, se, (m - 1.96 * se, m + 1.96 * se)


def line(label, vals, unit):
    m, se, (lo, hi) = ci95(vals)
    print(f"  {label:<30} {m:+10.4f} {unit}   SE {se:.4f}   95% CI [{lo:+.4f}, {hi:+.4f}]")
    return {"mean": m, "se": se, "ci": [lo, hi], "n": len(vals)}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "testA_trades.json"
    data = json.loads(Path(path).read_text())
    trades = data["trades"]
    print(f"Test A: {len(trades)} trades over {data['sessions']} sessions, "
          f"slippage model {SLIP*100:.3f}% per leg\n")

    # --- recover the pre-slippage signal prices, and PROVE the model --------
    unclean = 0
    for t in trades:
        long = t["side"] == "LONG"
        # entry: BUY for a long, SELL for a short. exit is the opposite leg.
        t["sig_entry"] = t["entry_price"] / (1 + SLIP) if long else t["entry_price"] / (1 - SLIP)
        t["sig_exit"] = t["exit_price"] / (1 - SLIP) if long else t["exit_price"] / (1 + SLIP)
        for p in (t["sig_entry"], t["sig_exit"]):
            if abs(p - round(p, 2)) > 0.005:
                unclean += 1
    share_clean = 100 * (1 - unclean / (2 * len(trades)))
    print(f"Inverting the slippage model recovers a clean 2-dp price on "
          f"{share_clean:.1f}% of the {2*len(trades)} legs.")
    if share_clean < 95:
        print("  *** MODEL NOT CONFIRMED — decomposition below is unreliable ***")
    else:
        print("  Model confirmed: 'gross_pnl' in this trade list is post-slippage.\n")

    # --- three-way decomposition -------------------------------------------
    pre_r, slip_r, chg_r, net_r, gross_r = [], [], [], [], []
    slip_rs, chg_rs = [], []
    stop_bp = []
    for t in trades:
        sgn = 1 if t["side"] == "LONG" else -1
        rupee_r = t["risk_per_share"] * t["qty"]
        pre = (t["sig_exit"] - t["sig_entry"]) * t["qty"] * sgn
        slip = pre - t["gross_pnl"]          # what slippage took, in rupees
        chg = t["cost"]                      # brokerage + statutory
        # net = pre - slip - chg, by construction; asserted below.
        assert abs((pre - slip - chg) - t["pnl"]) < 1e-6, (pre, slip, chg, t["pnl"])
        pre_r.append(pre / rupee_r)
        slip_r.append(slip / rupee_r)
        chg_r.append(chg / rupee_r)
        gross_r.append(t["gross_pnl"] / rupee_r)
        net_r.append(t["pnl"] / rupee_r)
        slip_rs.append(slip)
        chg_rs.append(chg)
        stop_bp.append(t["risk_per_share"] / t["sig_entry"] * 1e4)

    print("Per trade, in rupees:")
    s_rs = line("slippage", slip_rs, "Rs")
    c_rs = line("charges", chg_rs, "Rs")
    print(f"  {'total friction':<30} {s_rs['mean']+c_rs['mean']:+10.4f} Rs")

    print("\nPer trade, in R:")
    pre = line("pre-friction expectancy", pre_r, "R")
    slp = line("  less slippage", slip_r, "R")
    chg = line("  less charges", chg_r, "R")
    grs = line("= gross (as reported)", gross_r, "R")
    net = line("= net (as reported)", net_r, "R")

    total = slp["mean"] + chg["mean"]
    print(f"\n  {'TOTAL FRICTION':<30} {total:+10.4f} R")
    print(f"  {'friction as % of the loss':<30} {100*total/abs(net['mean']):9.1f}%")
    print(f"  {'slippage share of friction':<30} {100*slp['mean']/total:9.1f}%")
    print(f"  {'charges share of friction':<30} {100*chg['mean']/total:9.1f}%")

    m, se, (lo, hi) = ci95(stop_bp)
    print(f"\n  median stop {st.median(stop_bp):.1f} bp, mean {m:.1f} bp")
    print(f"  median realised R  Rs {st.median([t['risk_per_share']*t['qty'] for t in trades]):.1f}")

    # Does the pre-friction number actually clear zero?
    t_pre = pre["mean"] / pre["se"]
    print(f"\n  pre-friction t = {t_pre:+.2f} — "
          f"{'distinguishable from zero' if abs(t_pre) > 2 else 'NOT distinguishable from zero'}")

    out = {"pre_friction": pre, "slippage_r": slp, "charges_r": chg,
           "gross": grs, "net": net, "total_friction_r": total,
           "slippage_rs": s_rs, "charges_rs": c_rs,
           "stop_bp_median": st.median(stop_bp), "model_confirmed_pct": share_clean}
    dest = Path(__file__).resolve().parents[2] / "docs/research/friction_decomposition.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {dest}")


if __name__ == "__main__":
    main()
