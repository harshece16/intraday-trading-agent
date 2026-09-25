# Pre-registration — does the order book predict the next move? (research look L37, then a trial only if it clears)

**Written 2026-09-25, before the data exists.** `depth_samples` began collecting at 13:37 IST today (README §71). This fixes what will be measured and the gate, so the test cannot be shaped by the data. It runs at the user's direction without external reviewer review. The user's decision (2026-09-25): the Varsity checklist is retired as a decision-maker; it remains only as the review queue's describer. **This is the only open line for a replacement.**

## When
After **15 full sessions** of samples (about 3 weeks). Not earlier: a shorter sample can't reach the trade counts below.

## Data
`depth_samples` (one row per watched stock per 30 s tick) joined to the Kite 5m cache for the same sessions. **The first 15 sessions are the selection sample for this question**; sessions after the measurement date are its held-out. The 2026 price held-out window is not involved (it predates the book data).

## Features, fixed now (all from the sample at time t, nothing later)
1. `imbalance5` at t.
2. Change in `imbalance5` over the previous 5 minutes.
3. Spread in bp at t, relative to the stock's own median that session.
4. Change in total 5-level depth over the previous 5 minutes (a pull of liquidity from one side).
5. Exchange total buy − sell quantity, normalised by their sum.

## Targets
Signed return in bp from the next 5m bar's open to +15, +30 and +60 minutes (**entry at the next bar, never the current one**).

## Measurement
Per feature × horizon: rank IC across stock-times, with t across sessions (as step 2 did), and the **top-minus-bottom quintile spread in bp** against the **16.63 bp round trip** (a spread is two positions: **33.26 bp two-leg hurdle** where both legs would be traded; single-side rules face 16.63 bp).

## Gate for a trial, fixed now
> A feature-horizon earns a pre-registered trial only if its quintile spread **exceeds 33.26 bp with t > 2 across ≥ 15 sessions**, surviving Benjamini–Hochberg across the 15 tests (5 features × 3 horizons). The trial then runs the rule on the selection sessions, and confirms once on the sessions that accrue after the measurement date.

**If nothing clears:** the finding is that **the visible book does not predict NIFTY 100 intraday moves past cost**, and with §69, §73 and §74 that closes every information source this account can reach. The write-up will say the remaining questions are capital, horizon and instrument, not the rule.

Research look **L37**. No trial spent by the measurement.
