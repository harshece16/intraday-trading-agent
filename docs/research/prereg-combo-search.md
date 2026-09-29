# Pre-registration — forecast × candlestick combination search (trials 128 to 202, counted whether or not each runs)

**Written 2026-09-30 at 00:25 IST, before the result of L40 was read and before any model of L46 was run.** The owner asked, 2026-09-29: "try combinations with different set of rules maybe candle stick patterns or strategy combined with these or any permutation combination like if its possible to combine and see a profit."

**The concern, stated before the search.** Trying many combinations of forecasts and rules on the same past sessions will find some that look profitable by luck; with 75 combinations, about four would clear a plain t > 2 by chance. This search is therefore fixed in full here, every combination counts as a trial, and a combination passes only a bar corrected for all 75. A "profit" that does not clear that bar is reported as noise.

## 1. The grid, fixed

Every combination is a directional single-leg trade rule on the stock-times of the L40 sample.

**Signal source S** (up to 8): Kronos (L40 run of record) and each of the six L46 models that reaches a rows file, plus **Ensemble**: at each (session, decision time, horizon), the mean of the cross-sectional percentile ranks of every non-void model's forecast; its magnitude for rule R1 is the median of those models' forecasts in bp.

**Horizon H** (3): 15, 30, 60 minutes, each using the matching feature f15, f30, f60 and target.

**Candlestick pattern P** at the decision bar: `candlestick_patterns.detect_patterns` on the stock's closed bars up to and including the decision bar, with `indicators.atr(bars, 14)`. A **directional pattern** is any detected pattern with bias bullish or bearish and strength ≥ 2. If both a bullish and a bearish one are found, there is no pattern. Direction D = +1 for bullish, −1 for bearish.

**Rule R** (3 with a source, 1 without):
- **R1 forecast extreme:** long if the source's forecast is in the top quintile of that decision time and above +16.63 bp; short if in the bottom quintile and below −16.63 bp.
- **R2 pattern agrees with the forecast's sign:** trade D when a directional pattern is present and the forecast has the same sign.
- **R3 pattern agrees with the forecast's quintile:** trade D when a directional pattern is present and the forecast is in the top quintile (D = +1) or the bottom quintile (D = −1).
- **R4 pattern alone (control):** trade D whenever a directional pattern is present. One per horizon.

Count: 8 sources × 3 horizons × 3 rules + 3 controls = **75**. The count is fixed at 75 even if some sources are void, so a void cannot lower the bar.

## 2. Trades and costs

Entry at the open of the bar after the decision bar, exit at the close of the bar H minutes later: the target of L40 §6. **Net return per trade = direction × target − 16.63 bp.** A stock-time can be in several combinations; within a combination it is one trade.

## 3. Statistics

Per combination: number of trades; mean net bp per trade; the per-session mean of net bp (sessions with at least one trade); t across sessions; the same in each half of the sessions (L40's halves); and the deflated Sharpe ratio of the per-session series at **n_trials = 75** (`evaluation.deflated_sharpe_ratio`).

## 4. Pass rule, fixed now

A combination passes only if all hold:

1. at least 100 trades and at least 40 sessions with a trade;
2. mean net per trade above 0 bp;
3. t across sessions above **3.40**, the two-sided 5% Bonferroni bar for 75 tests (normal approximation);
4. positive in both halves;
5. deflated Sharpe ratio ≥ 0.95 at 75 trials.

A passing combination is a **candidate for confirmation on sessions it has not seen** (the live shadow's forward record from 2026-09-30, or the 2026 held-out window if the owner chooses). It is not a strategy, it is not wired into anything, and it does not reach the review queue.

## 5. One run

The search runs once, after every L46 model has a rows file or a void record. It reads the rows files and the candle cache only. No parameter here changes after the first number is seen.

## 6. Trial accounting

**Trials 128 to 202** (75), one ledger row for the block, whatever the result. The count of record becomes 202.
