# Sahab Ranker results — **both configurations FAIL (trials 121, 122); neither beats the momentum rule. Not adopted.**

**2026-09-26.** Pre-registration `prereg-ranker-engine.md` (`9756ca5`), code
`e31114c`, one run. Evaluation 2013-03 → 2025-11 (152 months after 36
training months), walk-forward, refitted monthly; selection data only.

| Gate (fixed in advance) | C1 IC-weighted | C2 ridge |
| --- | --- | --- |
| 1 — valid strategy: net excess t ≥ 2.24, DSR ≥ 0.95 (N = 2), both halves, last 3 yrs, +2 pp CAGR | **fail** (t 0.23) | **fail** (t 0.41) |
| 2 — beats the momentum rule (paired t ≥ 1.65) | **fail** (paired −0.77%/mo, t −1.90) | **fail** (−0.71%/mo, t −1.77) |
| 3 — unseen ranks 201–400 | **fail** (t 0.80) | **fail** (t 0.78) |

## Side by side (net of delivery costs, ₹10 L, same months)

| | Excess/month | t | 1st half | 2nd half | 2023–25 | CAGR (vs benchmark) | Max DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Momentum rule — top 200** | **+0.84%** | **2.63** | +0.67% | +1.01% | +0.80% | 26.8% (15.8%) | −33.0% |
| C1 — top 200 | +0.08% | 0.23 | +0.61% | −0.46% | −0.23% | 17.7% | −20.0% |
| C2 — top 200 | +0.14% | 0.41 | +0.47% | −0.20% | −0.06% | 18.6% | −19.7% |
| Momentum rule — ranks 201–400 | +0.94% | 2.61 | +0.56% | +1.31% | +1.02% | 32.1% (19.6%) | −35.3% |
| C1 — ranks 201–400 | +0.25% | 0.80 | +0.57% | −0.06% | −0.15% | 24.9% | −17.2% |
| C2 — ranks 201–400 | +0.26% | 0.78 | +0.49% | +0.04% | −0.28% | 25.1% | −18.7% |

## What the engine learned, and why it lost

The final C1 weights (mean past rank correlation with next-month return):
momentum inputs +0.01 to +0.05; **volatility −0.06, beta −0.06,
idiosyncratic volatility −0.05**; 52-week-high proximity +0.05; dividend
yield +0.04; price level +0.04. The engine learned the two families the
literature documents — momentum and "defensive" (low volatility, low beta,
high dividend) — and blended them. Through 2013–2019 the blend roughly
matched momentum. **From 2019 to 2025, India's small- and high-beta rally
punished the defensive tilt**, so the blend kept a third less drawdown but
gave up most of the momentum premium. Pooling signals by their average past
correlation weighted the defensive signals, which were strong on average in
the training years, and those were the wrong bets for the evaluation years.

This is the result the prediction-engine sweep warned of: more signals and
a fitted model did not beat the one robust signal; architecture was not the
bottleneck.

## What follows

- **The momentum book stays the engine.** It is itself a prediction engine —
  a one-signal monthly ranking — and it is the only one that passed.
- Trials 121 and 122 are recorded as FAIL. No configuration is re-tuned;
  any further engine is a new pre-registration and raises this family's N.
- The 2026 window was not used (it was spent on the momentum family).
