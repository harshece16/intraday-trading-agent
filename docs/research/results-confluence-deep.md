# Results — the confluence engine on the deep Kite cache (trial 40)

**2026-09-24. FAIL.** Pre-registered in `prereg-confluence-deep.md`, script `backend/research/confluence_deep.py`, both committed in `08524d1` before the run. One run, no re-run. Run at the user's direction **without external reviewer review**.

## Setup

- `entry_mode: "confluence"`, live parameters unchanged, with the 1.5 / 3.0 ATR stop and target.
- Harness identical to trials 36–39: NIFTY 100, scanner top 5/day, confidence gate off, 16.60 bp round trip.
- **Selection only**: 317 sessions, 2024-09-24 → 2026-01-01. **The 176 held-out sessions were never loaded.**
- Halves: 158 / 159 sessions.

## Result

| Sample | Trades | Gross R | **Net R** | t | 95% CI | Win | Median stop | Net ₹ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| First half | 243 | −0.155 | **−0.359** | −5.02 | [−0.50, −0.22] | 25.9% | 54.8 bp | −17,014 |
| Second half | 425 | −0.206 | **−0.471** | −8.53 | [−0.58, −0.36] | 25.9% | 41.9 bp | −27,861 |
| **Selection** | **668** | **−0.188** | **−0.430** | **−9.84** | **[−0.52, −0.34]** | 25.9% | 45.4 bp | **−44,875** |

The comparator is the current checklist (trial 39, same harness and window): 38 trades, −0.360R and +0.089R by half, not significant.

## Reading it

- **The pass rule fails on every clause.** Net R is negative with t = −9.84, and negative in both halves.
- **It loses before costs.** Gross is −0.188R per trade, about t ≈ −4.3 (sd ≈ 1.13, n = 668). The random-entry null through this harness is about −0.05R to −0.09R, from intraday drift on a long-heavy book. So confluence entries are **worse than random**, not merely no better.
- **The falsification branch fired as stated:** confluence trades **17×** as often as the checklist at a worse gross R, so the extra trades only multiply friction. Trials 1–6 are confirmed on proper data.
- **Friction** at the 45 bp median stop is about 0.37R per trade, close to the checklist's 0.40R. The difference is the trade count, not the cost per trade.

## Decision

**The live engine stays on the Varsity checklist.** The confluence "supporting evidence" read stays on the dashboard as context, but it is measured as a *negative* signal for entries and should not be used to take trades. No held-out look is earned.

Counted as **trial 40**.
