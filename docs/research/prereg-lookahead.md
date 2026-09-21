# Pre-registration — step 1b, lookahead proof

**Committed before the test was run.** Amendment 2 of the approved plan.

## Hypothesis under test

Each of the nine pre-open features in `scanner.premarket_score()` is
computable from information available before session T's open, and its value
does not depend on session T's own bar or on any later bar.

This is not a hypothesis about profit. It is a precondition: a feature that
fails it cannot be honestly measured in step 2, because its apparent
predictive power would partly be knowledge of the outcome.

## The rule being tested

For a feature value **F(T)** computed for session T:

> F(T) computed from the full daily series **must equal** F(T) computed from a
> series with session T and every later session physically removed.

Equality is exact, not approximate. Any divergence means a later bar reached
the value.

This is deliberately stronger than checking that the code filters by date.
Filtering can be correct in one branch and absent in another (a 52-week window,
a pattern's confirmation bar, an indicator warm-up that reaches forward), and
only recomputation on truncated data catches that.

## Features covered

| # | Feature | Profile field |
| --- | --- | --- |
| 1 | Seasonality (March effect) | — (calendar only) |
| 2 | Daily trend, close vs EMA20 vs EMA50 | `trend` |
| 3 | 10-day relative strength vs NIFTY | `rs10` |
| 4 | Proximity to 52-week high / low | `pct_from_high`, `pct_from_low` |
| 5 | NR7 / inside day | `nr7`, `inside_day` |
| 6 | Bulkowski daily swing patterns | `swing_patterns` |
| 7 | Murphy reversal day | `reversal_day` |
| 8 | Daily RSI zone | `rsi` |
| 9 | Daily ATR% band | `atr_pct` |

Three specific checks the reviewer required, beyond the blanket rule:

- **Day T's own bar is excluded**, not merely later ones. The last bar feeding
  the profile must be strictly earlier than T, and the profile's `close` must
  be that bar's close.
- **Bulkowski patterns use no confirmation bar after the signal.** Many pattern
  definitions require a confirming bar; if `scan_daily_patterns` did, the
  pattern list for T would change when future bars are removed.
- **Seasonality is a published constant, not an in-sample estimate.** Asserted
  structurally: `march_effect` takes `(month, side)` and no price data, its
  source contains no aggregation or fitting, and it fires only in March.

## Data, universe, period

- Real daily bars via `scanner.download_batch(..., "2y", "1d")` (yfinance;
  daily was never subject to the 60-day intraday cap and is what
  `premarket_picks()` actually reads).
- Six liquid symbols: RELIANCE, TCS, INFY, HDFCBANK, ITC, SBIN. Requires ≥300
  bars each.
- Sessions sampled from index 260 onward (so ≥60 prior bars exist) and
  stopping 30 bars before the end (so there *are* future bars available to
  leak in — a test where no future exists proves nothing).

## Cost model

Not applicable. This step computes no returns and places no trades.

## Metric and pass/fail threshold

**Metric:** exact equality of each feature value across the two computations.

**Pass:** every sampled (symbol, session, feature) pair matches, with a
minimum of 20 whole-profile comparisons and 10 per individual field, so a pass
cannot come from an empty sample.

**Fail:** any mismatch. **A failing feature is excluded from step 2, not
repaired.** Repairing it and re-testing would make the fix itself an untested
choice made after seeing the data.

Two guards against a vacuous pass:
- the whole-profile test asserts a minimum comparison count;
- the pattern test asserts at least one swing pattern actually fired, so it
  cannot pass merely because nothing ever triggers.

## Trial counting

**Not a strategy trial.** No strategy is selected, no returns are computed,
nothing is ranked. Recorded in `trials.md` under *research looks*.

## Known limitations, stated in advance

- Six symbols, not the full universe. A feature could in principle leak only
  on a symbol not sampled; the features are symbol-independent code paths, so
  this is judged low risk, but it is a sample, not a proof over the universe.
- Daily bars come from yfinance, whereas intraday comes from Kite. This tests
  the feature *code*, not agreement between the two vendors.
- Passing means no lookahead **of this kind**. It does not rule out
  survivorship bias in the universe list, which is a separate and
  unaddressed problem carried in every write-up.
