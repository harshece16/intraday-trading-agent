# Pre-registration — event study on NSE filings (research look L35, no trial)

**Written and committed before the script runs.** The user asked (2026-09-25) to backtest the event idea, use it to predict, and verify. This is step 1, the **measurement**: does a stock move by more than the round trip after a filing? Step 2 (a rule) and step 3 (held-out) happen only if step 1 clears, each pre-registered on its own. Runs at the user's direction without external reviewer review.

## Data

- **Events:** NSE corporate announcements for each NIFTY 100 symbol (`/api/corporate-announcements`, per symbol, per calendar year), timestamped `an_dt` to the second, in IST. The feed's own `ROUTINE` list drops housekeeping filings.
- **Prices:** the Kite 5m cache, **selection sample only** (sessions before 2026-01-02). The held-out window is not loaded.
- **Costs:** the 16.63 bp round trip.

## Event classes, fixed now (by `desc` keyword, first match wins)

| Class | Keywords in `desc` |
| --- | --- |
| RESULTS | "financial result", "results" |
| ORDERS | "bagging", "receiving of order", "order", "contract" |
| DEALS | "acquisition", "investment", "joint venture", "merger", "amalgamation", "demerger" |
| CAPITAL | "buy back", "buyback", "bonus", "dividend", "rights", "qip", "preferential" |
| NEGATIVE | "default", "fraud", "insolvency", "pledge", "resignation", "litigation", "penalty", "sebi" |
| OTHER | any other non-routine filing |

## Reaction windows, fixed now

Timing is decided by `an_dt`:
- **In-hours event** (09:15 ≤ an_dt < 14:30 on a trading day): entry is the **open of the first 5m bar starting after `an_dt`**. Windows: +30 min, +60 min, and to the **15:08 close**. (Filings at or after 14:30 are treated as after-hours: too late for an intraday trade.)
- **After-hours event** (any other time): the next session's **09:20 bar open** (the first bar after the opening five minutes). Windows: +30 min, +60 min, and to the close. The **gap** (previous close → 09:15 open) is reported for information only: it is not tradable.

## What is measured

Per class and window, in bp of the entry price:
1. **Mean signed return**, with t across events, **direction-aligned** to the feed's sentiment sign (`TILTS` + `score_text` on desc and attachment text; events scoring 0 are dropped for this line). That is what a rule could trade.
2. **Mean absolute return**, against the same window's absolute return on **matched non-event bars** (same symbol, same time of day, a random other session), so "events move stocks" is tested against a baseline rather than asserted.
3. Event counts. A class-window with under **50 events** is reported as underpowered, not as a result.

## Gate for going to step 2, fixed now

> A class-window earns a step-2 pre-registration only if its **direction-aligned mean signed return exceeds 16.63 bp with t > 2** on ≥ 50 events, **after Benjamini–Hochberg at 5% across every class × window tested here** (6 classes × 6 windows = 36 tests).
>
> Otherwise the answer is **"filings do not move NIFTY 100 stocks by more than the round trip in a tradable window"**, and no rule is written. A large *absolute* move with no aligned *signed* move is a volatility finding, not a directional edge, and is reported as such.

## Accounting

Research look **L35**. No trial. Held-out untouched. One run; a re-run only for a crash before any statistic was printed (fetch failures for some symbols are recorded as missing, not re-run for a better sample).
