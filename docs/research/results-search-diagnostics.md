# Diagnostics — why the 76 search configurations lose

**2026-09-25.** A **replication, not new trials**. `search_diagnostics.py` (commit `9629318`, before it ran) re-ran 11 already-counted configurations on the same selection sample to recover their trade lists: the best of each family × timeframe, plus the checklist on 15m and 60m. The held-out window was never loaded. **It reproduces the grid exactly** (for example MR-60m −0.062R, PB-60m −0.077R, VB-60m −0.074R), so the numbers below describe the same trades.

## The finding: the entries carry no information, and the loss is friction

| Configuration | Trades | **Pre-friction R** | Gross R | Net R | Friction R | MFE median | Reach ≥ 1R |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MR 5m, 3 ATR, hold, short | 1,272 | −0.034 | −0.144 | −0.340 | 0.306 | 0.51 | 19.0% |
| MR 15m, 3 ATR, 2R, both | 1,215 | −0.054 | −0.109 | −0.208 | 0.154 | 0.34 | 1.6% |
| MR 60m, 3 ATR, 2R, short | 97 | +0.010 | −0.016 | −0.062 | 0.073 | 0.18 | 0.0% |
| PB 5m, 3 ATR, hold, both | 1,332 | +0.039 | −0.037 | −0.170 | 0.208 | 0.60 | 31.6% |
| PB 15m, 3 ATR, hold, short | 1,161 | +0.014 | −0.041 | −0.138 | 0.152 | 0.50 | 23.5% |
| PB 60m, 3 ATR, 2R, short | 877 | −0.008 | −0.033 | −0.077 | 0.069 | 0.21 | 1.3% |
| VB 5m, 3 ATR, 2R, both | 1,394 | +0.044 | −0.050 | −0.216 | 0.260 | 0.62 | 33.9% |
| VB 15m, 3 ATR, 2R, short | 897 | +0.026 | −0.025 | −0.116 | 0.142 | 0.44 | 20.8% |
| VB 60m, 3 ATR, 2R, short | 597 | −0.010 | −0.033 | −0.074 | 0.064 | 0.21 | 2.2% |
| Checklist 15m | 1,670 | −0.012 | −0.127 | −0.332 | 0.321 | 0.69 | 39.5% |
| Checklist 60m | 992 | −0.004 | −0.068 | −0.182 | 0.178 | 0.43 | 20.3% |

**Pre-friction R, the result at signal prices before slippage and charges, sits between −0.054 and +0.044 for all 11**: four entry ideas and three timeframes. That is zero. Every configuration's net loss is its friction.

## What this says about improving the rules

- **Stops, targets and timeframes cannot fix this.** They change how much friction a trade pays (0.06R at 60m with 3 ATR stops, 0.3R at 5m), not whether the entry has an edge. The 60m configurations lose least only because friction is smallest there, and their pre-friction R is still about 0.
- **Slow trades barely move.** At 60m the median trade's best excursion is **0.2R** and only 0–2% ever reach 1R before the square-off. The stop is simply too wide for an intraday move to matter, so R collapses toward 0 and the costs remain.
- **Fast trades move but pay for it.** At 5m a third of trades reach 1R, but friction is 0.2–0.3R, and the stop-outs (−1.2R) outweigh what the square-offs and targets bring in.
- **Consistent smaller effects**, each already known:
  - **Shorts lose less than longs** in 3 of 4 configurations with both sides. That's the −6.4 bp intraday drift (phase 2).
  - **Later entries lose more.** 14:xx entries are the worst in every configuration shown.
  - Neither turns anything positive.

## Conclusion

**Price-and-volume technical entry rules on NIFTY 100 intraday bars carry no measurable edge before costs, and the round trip makes every one of them lose.** This is the pre-registered falsification branch, now confirmed from the inside: not "the best config was a bit short of the bar", but "the entries are zero and the costs are the loss". **Tuning parameters further on the same inputs is curve-fitting, and is not proposed.** A next round has to change the **information**, not the rule. Options and their evidence are listed in README §69.
