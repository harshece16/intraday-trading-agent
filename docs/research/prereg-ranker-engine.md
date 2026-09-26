# Pre-registration — Sahab Ranker: our own prediction engine for next-month stock returns (trials 121–122)

**Written 2026-09-26, before any engine code exists.** The owner: "let's
build a prediction engine on our own, use whatever research you want."

## What the research allows it to be

Four literature sweeps, a 35-agent prediction-engine sweep and 120 trials
here agree: **price direction at intraday horizons is not predictable after
costs**, by any model family. What is predictable, and survives delivery
costs, is the **cross-section of next-month returns** among liquid stocks:
which names will beat the others. The only strategy to pass here (3i,
momentum) is one such ranking. So the engine is a **monthly cross-sectional
return forecaster**: at each month-end it scores the most-traded NSE stocks
on their expected return over the next month, relative to each other, and
the book holds the top of the list.

It is judged against a hard baseline: **the 3i momentum rule already running
in paper**. An engine that does not beat it is not adopted.

## Inputs (14, from the literature; none invented here)

All computed at month-end t from prices up to t (`research/nse_prices.py`:
total-return adjusted closes, as-printed closes, traded value, NSE's
dividend records). Each is converted to a cross-sectional rank in [−0.5, 0.5]
within the month's universe.

| # | Input | Source idea |
| --- | --- | --- |
| 1 | return t−12 → t−1 | 12-1 momentum (Jegadeesh–Titman) |
| 2 | return t−6 → t−1 | 6-1 momentum |
| 3 | return t−3 → t−1 | 3-1 momentum |
| 4 | return t−1 → t | one-month reversal |
| 5 | 3i's score, mean(r6/σ, r12/σ) | the baseline's own signal |
| 6 | daily volatility, 252 sessions | low-volatility effect |
| 7 | daily volatility, 63 sessions | short-window volatility |
| 8 | close ÷ 252-session high | 52-week-high (George–Hwang) |
| 9 | log median traded value, 126 sessions | liquidity |
| 10 | median of |return| ÷ traded value, 63 sessions | Amihud illiquidity |
| 11 | beta to the equal-weighted universe, 252 sessions | betting-against-beta |
| 12 | residual volatility from that regression | idiosyncratic volatility |
| 13 | dividends in the last 252 sessions ÷ price | dividend yield |
| 14 | log as-printed price | low-price effect |

**Not used:** the earnings surprise (barred when PEAD failed Stage A, L39),
anything from 2026, any input chosen after looking at its returns here.

## Target and models

Target for month-end t: the stock's total return from the close of the
session after t to the close of the session after the next month-end, minus
the universe's mean, converted to a cross-sectional rank in [−0.5, 0.5].

Two configurations, **both fitted walk-forward and never tuned**:

- **C1 — IC-weighted composite.** Each input's weight is its mean monthly
  rank correlation (Spearman) with the target over all training months;
  score = Σ weight × input rank.
- **C2 — ridge regression.** Pooled least squares of the target rank on the
  14 input ranks over all training rows, penalty λ = 0.1 × (number of
  training rows), fixed now, no intercept (ranks are centred).

**Walk-forward:** at month-end t, train on every month s with s ≤ t − 2
(the target of month t − 1 is not complete until the session after t), from
the first month with all inputs (2010-02). The first prediction is the first
month with **36 training months**. Refitted every month.

## Book (identical to 3i, so the comparison is only the ranking)

Universe: the 200 most-traded stocks at each month-end (3i's rule; fund
units excluded). Hold 15, equal weight at entry, keep while ranked ≤ 30 by
the engine's score, replace from the top, fills at the next session's close,
Zerodha delivery costs, DP ₹15.34, 0.05% slippage, ₹10 L. Benchmark: the
universe equal-weighted. **The baseline** is 3i Part A's rule simulated over
the **same months**.

## Pass rules (family "cross-sectional return forecasting", N_family = 2)

**Gate 1 — the engine is a valid strategy** (each configuration separately):
monthly net excess over the benchmark with **t ≥ 2.24** (two-sided
Bonferroni at 5% across 2); corrected Deflated Sharpe ≥ 0.95 at N = 2;
positive in both halves (split at the median month); positive over
2023-01 → 2025-11; net CAGR gap ≥ 2 pp; ≥ 100 round trips.

**Gate 2 — it beats the baseline:** the paired monthly difference (engine
net excess − momentum-rule net excess, same months) has mean > 0 with
**t ≥ 1.65**, and is positive in both halves.

**Gate 3 — it travels to unseen stocks:** the configuration, trained only on
the top-200 data, scores **ranks 201–400** (0.10% slippage, their own
equal-weighted benchmark): net excess t ≥ 1.65, positive in both halves,
and a positive paired difference against the momentum rule on the same
stocks.

**Adoption:** a configuration passing all three gates is adopted; if both
pass, the one with the higher Gate-2 t. An adopted engine runs as a **second
paper book beside the momentum book** for at least six months before the
owner decides whether it replaces it. Passing Gate 1 but not Gate 2 is
recorded as "a valid strategy that does not beat momentum" — nothing
changes in the engine.

## Held-out, stated plainly

The 2026 months were spent once for the momentum family (3i) and the
momentum book's 2026 result is known; any ranking that leans on momentum
would inherit it. **The 2026 window is not used as evidence here.**
Confirmation is Gate 3 (unseen stocks) and the forward paper book.

## What this cannot show

A backtest cannot show the future. Momentum-like rankings have losing years
(−13% against the benchmark in 2025). Tax (20% STCG) is not modelled.

## Code and order

`backend/research/ranker.py` — inputs, both models, walk-forward, the book,
all three gates — committed after this file and before its one run.
Trials 121 (C1) and 122 (C2).
