# Pre-registration — step 2, per-feature scanner IC

**Committed before the measurement was written or run.** Incorporates
amendments 1, 3, 4, 6 and 7 of the approved plan.

## Why this step exists

The composite pre-market score has a daily rank IC of **−0.0021** (t = −0.26,
positive on 49% of days, 436 sessions). That is indistinguishable from zero.

A composite can be flat while a component is not: nine features are summed
into one number with hand-assigned weights, and a single informative feature
could be diluted by eight uninformative ones. This tests each separately.

**This is a measurement, not a strategy search.** No trading rule is built, no
position is sized, no backtest is run. It answers "does any of these nine
quantities carry information about the next session?" — and the honest
expected answer, given the composite, is no.

## The nine features

All nine passed the step-1b lookahead proof (`prereg-lookahead.md`,
16 tests) — a feature's value for session T is bit-identical whether or not
the data contains T and everything after it. None is excluded.

| # | Feature | Type | Test |
| --- | --- | --- | --- |
| 1 | Daily trend (close vs EMA20 vs EMA50) | categorical (up/down/sideways) | group means |
| 2 | 10-day relative strength vs NIFTY (`rs10`) | continuous | rank IC |
| 3a | % from 52-week high | continuous | rank IC |
| 3b | % from 52-week low | continuous | rank IC |
| 4 | Daily RSI | continuous | rank IC |
| 5 | Daily ATR % | continuous | rank IC |
| 6 | NR7 | binary | flagged vs unflagged |
| 7 | Inside day | binary | flagged vs unflagged |
| 8 | Bulkowski swing pattern present | binary | flagged vs unflagged |
| 9 | Murphy reversal day | binary | flagged vs unflagged |

March seasonality is **not tested**: it is a published constant keyed on the
calendar month, not a per-stock quantity, so a cross-sectional IC is undefined
for it. Stated rather than silently dropped.

## Target variable

**Open-to-close return of the same session** (amendment 3), not
previous-close-to-close.

`(close_T − open_T) / open_T`

Rationale: the decision this feature would inform is taken before session T's
open, and the position would be entered at or after that open. Overnight gap
return is not capturable by an intraday strategy, and including it measures
something the strategy could never harvest.

## Test per feature type

**Continuous features** — daily cross-sectional **Spearman rank IC**: for each
session, rank every eligible stock by the feature and by the target, take the
rank correlation. Report the mean IC across sessions, its t-statistic
(mean / standard error across sessions), and the percentage of sessions with
IC > 0.

**Binary and sparse features** (amendment 4) — **flagged-vs-unflagged mean
return with a two-sample t-statistic**. Rank IC on a mostly-zero column is
ill-defined and would be dominated by tie-handling. Report flagged n,
unflagged n, both means, the difference, and its t.

**Categorical feature** (trend) — group means per category with an F-style
comparison reported as pairwise t-statistics against the pooled remainder.

Sign convention: every feature is tested in the direction the scanner uses it.
A feature the scanner scores **negatively** (e.g. RSI > 75 for longs) is tested
with its sign flipped so a positive result always means "the scanner's use of
this is correct". Stated so a negative result cannot later be reinterpreted as
a positive one by flipping the sign after the fact.

## Universe, period, split

- NIFTY 100 universe list, daily bars, same source `premarket_picks()` uses.
- **Selection split only** for this pass: sessions **before 2026-01-02**
  (`splits.HELD_OUT_START`).
- Eligibility per session follows `scanner.tradability_exclusion()`, so the
  measurement covers the same stocks the scanner would actually rank.
- Minimum 20 eligible stocks per session for that session to count, matching
  `IC_MIN_T_STAT`'s companion rule used elsewhere in the project.

**The held-out split is not pristine** (amendment 6). Earlier work already ran
against 2026-01-02 onward. Any held-out confirmation here is a *second* look
at seen data and is weaker than the term normally implies. This will be
restated in the results. The only genuinely unseen sample is data after
2026-09-20, of which there is currently none.

## Multiple-comparison correction

Nine simultaneous tests. Reported three ways (amendment 7):

1. **Raw** p-value per feature.
2. **Benjamini–Hochberg at q = 0.10** — the gate. Controls false discovery
   rate; chosen over family-wise control because at nine tests Bonferroni
   would require p < 0.0056 and, given a composite IC of −0.002, would almost
   certainly pass nothing. Reporting all three lets a stricter reviewer apply
   their own standard without a rerun.
3. **Bonferroni at α = 0.05** alongside.

**Promotion rule:** only a feature surviving **BH at q = 0.10** on the
selection split gets a held-out look, **once**. If **more than one** survives,
**Bonferroni across the survivors** is applied on the held-out look.

## Pass / fail

**A feature passes** if it survives BH at q = 0.10 on selection, and then on
the held-out look retains the **same sign** with **|t| > 1.5** (and clears
Bonferroni across survivors if more than one was promoted).

**The full table is reported including every failure.** A table of nine
failures is the expected outcome and is a complete result, not an absence of
one.

**No feature is promoted on the basis of the held-out look alone**, and no
feature that fails selection is re-examined on held-out to see whether it
"would have" passed.

## Power

Per amendment 1, required sample is computed from **this measurement's own**
spread, not inherited from the trade-level 1.41R. For a daily IC series the
relevant quantity is the standard deviation of per-session IC across sessions;
with ~297 selection sessions, the detectable mean IC at t = 2 is
`2 × sd(IC) / sqrt(297)`. That figure will be **computed from the data and
reported**, so a null result can be read as "no effect larger than X" rather
than merely "nothing found".

## Trial counting

**Not strategy trials.** Nine measurements that select no strategy, size no
position and run no backtest. Logged in `trials.md` under **research looks**,
as amendment 7 directs — one line per feature, so the count of looks is
auditable even though the DSR trial count stays at 34.

## Known limitations, stated in advance

- **Survivorship bias**: today's NIFTY 100 applied to history. Stocks that
  left the index, usually by falling, are absent. This distorts
  cross-sectional ranks, and the direction of the distortion is not obvious —
  unlike in a long-only return series, where it simply flatters.
- **A per-feature IC says nothing about interaction.** Two features could each
  be flat and jointly informative. This design cannot detect that, and no
  claim to the contrary will be made from a null result.
- **Daily bars come from yfinance**, while the intraday cache is Kite. The
  target (open-to-close) is computed from the same daily source as the
  features, so the two are at least consistent with each other.
- A null result here does **not** establish that no pre-open signal exists —
  only that these nine, as currently computed, do not carry one.
