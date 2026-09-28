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

---

# Amendment 1 — 2026-09-26, before any `depth_samples` row has been joined to a return

Two reviews (the 2026-09-26 edge-map and prediction-engine workflows) found
three things this pre-registration left undefined. They are fixed now,
before the data is read, and none of them moves the gate.

1. **Late-day horizons.** Samples run until the engine's square-off at 15:08
   (`SQUARE_OFF_TIME`); Zerodha squares off F&O-stock MIS at 15:12, and since
   2026-08-03 continuous trading ends at 15:15 with a closing auction. A
   target that ends after 15:08 would be scored on a price the engine could
   not trade at. **Rule:** an observation is scored only if its entry (the
   next 5-minute bar's open) plus the horizon is at or before 15:08. Others
   are dropped, not truncated, and the dropped count per horizon is
   reported.
2. **Which stocks.** `depth_samples` holds one row per stock on the engine's
   *current watchlist* per ~30 s tick, and the watchlist rotates with the
   scanner. A stock seen for an hour is not a stock observed for a session.
   **Rule:** a stock-session is scored only if the stock was sampled in at
   least 90% of that session's ticks between 09:20 and 15:08. The count of
   stock-sessions kept and dropped is reported.
3. **Which sessions.** 2026-09-25 began at 13:37 and is partial; it is
   excluded. "15 full sessions" starts from 2026-09-28. A session with a
   sampling gap longer than 5 minutes inside 09:20–15:08 (the session
   summary's coverage check) is excluded and counted.

**Stated in advance:** the literature expects this test to fail. Three NSE
studies find order-imbalance predictability strong in the first five
minutes and gone within thirty (see
`prediction-engine-sweep-2026-09-26.md`), and Kite's depth is 5 levels at
~30 s, not tick-by-tick. A failure will therefore not be reinterpreted as
"needs deeper or faster data" — that is a different, costlier product, and
it would be a new pre-registration. The 33.26 bp hurdle, the
Benjamini–Hochberg family of 15 and the ≥ 15-session requirement are
unchanged.

---

# Amendment 2 — 2026-09-28, after the first full session was recorded and before any `depth_samples` row has been joined to a return

**What had been seen:** row counts only. On 2026-09-28 the watchlist
rotated with the scanner: 51 stocks were sampled at least once, and only 10
met the 90% coverage rule of Amendment 1. No feature has been computed and
no sample has been joined to a return.

**The change:** from the first session on which this is deployed (expected
2026-09-29; the actual date is added below once it is live), the engine's
watchlist is fixed for each session. It is the 25 eligible NIFTY 100 stocks with the highest 20-day
average turnover, chosen before the open from daily data and kept all day
(README §91). A stock that becomes ineligible during the day is dropped and
not replaced. The choice uses no price move, order-book reading or return.

**Why:** a rotating list leaves most stock-sessions unusable, which cuts the
test's sample by more than half. A fixed list gives up to 25 whole-session
stocks a day. The most-traded names also have the tightest spreads, which is
where a book signal would be cheapest to trade.

**Unchanged:** the five features, the three horizons, the 15-session
requirement, the 90% coverage rule, the 33.26 bp hurdle and the
Benjamini–Hochberg family of 15. The 2026-09-28 session stays in the sample
with the stock-sessions it has.

**A consequence to state now:** the stocks in the sample become the most
liquid NIFTY 100 names. A result will describe those stocks, not the whole
index.

