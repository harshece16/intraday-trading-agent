# Issue #74 — cost_pct correction, before/after backtest

**2026-09-23.** A declared bug-fix pair, not a hypothesis. The pass rule, window and harness were committed in the script's docstring before the run (`backend/research/fix74_cost_pct.py`, commit `dbe7514`). One run, no re-run.

## What changed

The checklist's reward-to-risk gate and stop-to-cost floor deducted a hardcoded **0.12%** round trip. Phase 2 measured **16.60 bp** (10.60 bp charges + 6.00 bp slippage), and `costs.py` already books exactly that on every P&L. `cost_pct` is now `costs.round_trip_pct()` = **0.166%**, flat at any notional under the ₹20 brokerage cap (~₹66,667).

## Setup

Test A's harness: `run_backtest()`, NIFTY 100, scanner top 5/day, `min_confidence_to_trade = 0`, `scorecard = []`, `config.COSTS`, 5m Kite bars.

- **Selection only**: 318 sessions, 2024-09-23 → 2026-01-01. The **176 held-out sessions were never loaded** into any run.
- Halves: 159 / 159 sessions, split at 2025-05-16.
- Pass rule: ships unless the fix's net expectancy is below the baseline's in **both** halves.

## Result — PASS (worse in the first half only)

| Half | Arm | Trades | Net R/trade | t | 95% CI | Win | Net ₹ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| First | baseline 0.12 | 71 | −0.302 | −1.85 | [−0.62, +0.02] | 33.8% | −3,666 |
| First | **fixed 0.166** | **33** | −0.354 | −1.44 | [−0.84, +0.13] | 30.3% | −2,423 |
| Second | baseline 0.12 | 51 | −0.207 | −1.00 | [−0.61, +0.20] | 37.3% | +77 |
| Second | **fixed 0.166** | **12** | +0.032 | +0.07 | [−0.86, +0.92] | 41.7% | +476 |

## What this does and does not show

- **The fix removes 63% of trades** (122 → 45). That is the intended effect: those setups cleared 1.5 only because the gate priced their cost at 12 bp.
- **It creates no edge.** Every confidence interval spans zero and the two arms' intervals overlap almost completely. The second half's +0.03R is **12 trades**, which is not evidence of anything.
- **Losses fall because trading falls**: −₹3,590 → −₹1,947 across both halves. Per trade, it is worse in one half and better in the other, which is noise.
- The ship decision rests on the measurement (the gate should price what the P&L charges), not on this backtest. The backtest only shows the correction does no harm.

Counted as **trials 36 and 37**.
