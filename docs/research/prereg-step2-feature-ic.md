# Pre-registration — step 2, per-feature scanner IC

**Committed before the measurement was written or run** (`bc704e5`).
**Amended 2026-09-21 per reviewer Entry 3 §D, before any measurement was run**
— see "Amendments" at the foot. Incorporates amendments 1, 3, 4, 6 and 7 of
the approved plan.

## Why this step exists

The composite pre-market score has a daily rank IC of **−0.0021** (t = −0.26,
positive on 49% of days, 436 sessions). That is indistinguishable from zero.

A composite can be flat while a component is not: nine features are summed
into one number with hand-assigned weights, and a single informative feature
could be diluted by eight uninformative ones. This tests each separately.

**This is a measurement, not a strategy search.** No trading rule is built, no
position is sized, no backtest is run. It answers "does any of these nine
quantities carries information about the coming session?" — and the honest
expected answer, given the composite, is no.

## The nine features

All nine passed the step-1b lookahead proof (`prereg-lookahead.md`,
16 tests) — a feature's value for session T is bit-identical whether or not
the data contains T and everything after it. None is excluded.

| # | Feature | Type | Test |
| --- | --- | --- | --- |
| 1 | Daily trend (close vs EMA20 vs EMA50) | categorical | **one** test: per-session up minus down |
| 2 | 10-day relative strength vs NIFTY (`rs10`) | continuous | rank IC |
| 3a | % from 52-week high | continuous | rank IC |
| 3b | % from 52-week low | continuous | rank IC |
| 4 | Daily RSI | continuous | rank IC |
| 5 | Daily ATR % | continuous | rank IC |
| 6 | NR7 | binary | per-session flagged − unflagged |
| 7 | Inside day | binary | per-session flagged − unflagged |
| 8 | Bulkowski swing pattern present | binary | per-session flagged − unflagged |
| 9 | Murphy reversal day | binary | per-session flagged − unflagged |

Counting 3a and 3b separately, this is **ten tests**.

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

**Binary and sparse features** (amendment 4, as amended by Entry 3 §D1) —
**per-session** mean target return of flagged minus unflagged stocks, then the
mean of that difference across sessions and its t-statistic **across
sessions**, handled exactly like the rank-IC series.

*Not* a pooled two-sample t over stock-days. Returns within a session are
cross-sectionally correlated — one market-wide move affects every stock the
same day — so pooling treats correlated observations as independent and
inflates the t-statistic, often severely. Only sessions with **at least 3
stocks on each side** contribute. **Report sessions used per feature.**

**Categorical feature** (trend, as amended by Entry 3 §D2) — **one test**:
per-session mean return of *up*-trend stocks minus *down*-trend stocks, in the
direction the scanner uses it, then mean and t across sessions. Not a set of
pairwise comparisons.

Sign convention: every feature is tested in the direction the scanner uses it.
A feature the scanner scores **negatively** (e.g. RSI > 75 for longs) is tested
with its sign flipped so a positive result always means "the scanner's use of
this is correct". Stated so a negative result cannot later be reinterpreted as
a positive one by flipping the sign after the fact.

## Universe, period, split

- NIFTY 100 universe list, daily bars, same source `premarket_picks()` uses.
- **Warm-up (Entry 3 §D3): every tested stock-session must have at least 252
  prior daily bars**, so a "52-week high" is a real 52 weeks and EMA50 / ATR14
  are fully warmed. History is downloaded far enough back that this holds from
  the **first** selection session, matching what the live scanner sees rather
  than what a truncated download happens to allow. **Any stock-session still
  short of 252 prior bars is dropped and the count reported.**
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

## Data-quality gate, before any IC is computed (Entry 3 §D4)

The target is yfinance open-to-close; the intraday cache is Kite. **This is a
check, not a second test, and it produces no p-value.**

On the overlap between the two sources, per stock-session, correlate yfinance
open-to-close against Kite first-bar-open → last-bar-close. **Report the
correlation and the share of stock-sessions differing by more than 25 bp.**

**If agreement is poor, stop and report instead of running the ICs.** A
disagreement between sources would mean the target variable is partly vendor
artefact, and nine ICs measured against a corrupted target are worse than no
ICs at all. The threshold for "poor" is deliberately left to judgement and
will be stated with the number when reported, rather than pre-set to a value
that could be chosen to clear whatever comes back.

## Multiple-comparison correction

**Ten simultaneous tests** (Entry 3 §D2): trend counts as one, and the two
52-week features (3a from-high, 3b from-low) count separately. **The family
size is 10 and will be stated in the results.** Reported three ways (amendment 7):

1. **Raw** p-value per feature.
2. **Benjamini–Hochberg at q = 0.10** — the gate. Controls false discovery
   rate; chosen over family-wise control because at ten tests Bonferroni
   would require p < 0.005 and, given a composite IC of −0.002, would almost
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

**The full table is reported including every failure.** A table of ten
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


---

## Amendments

### 2026-09-21 — reviewer Entry 3 §D. Committed before any measurement ran.

1. **Binary and categorical tests are per-session differences, not pooled
   two-sample t-tests.** Returns within a session are cross-sectionally
   correlated, so pooling stock-days inflates the t-statistic. Sessions need
   ≥3 stocks on each side to contribute; sessions used are reported per
   feature.
2. **Trend is one test, not several.** Up minus down in the scanner's
   direction. With 3a and 3b counted separately the BH family is **ten**, and
   the family size is stated in the results.
3. **52-week features require 252 prior daily bars** per tested stock-session,
   with history downloaded far enough back that this holds from the first
   selection session. Same warm-up check for EMA50 and ATR. Dropped
   stock-sessions are counted and reported.
4. **A data-quality gate is added before the ICs**: yfinance open-to-close
   versus Kite first-open-to-last-close on the overlap, reporting correlation
   and the share differing by more than 25 bp. Poor agreement stops the step
   rather than being noted in passing.

None of these amendments changes what counts as a pass. They change how the
statistics are computed and add a gate that can halt the step, both of which
make a false positive less likely rather than more.

### 2026-09-21 — reviewer Entry 4 §B and §D. Committed before any of the new measurements ran, and before the held-out look.

**This amendment makes the promotion rule strictly harder than registered.**
It is being written after the selection-split results are known, which is
normally the shape of a rule bent to fit a result. It is recorded here in the
other direction: three features already qualified under the original rule and
this amendment can only disqualify them. Nothing here can promote a feature
that did not already survive BH.

#### 5. `from_low`'s sign is corrected by relabelling, not by re-running

The scanner awards `pct_from_low <= 3` its +10 on the **short** side, so "the
scanner is correct" requires sign **+1**, and the run used −1. The measured
statistic is unchanged — p depends on |t| — so **no rerun happens**. The
results table carries the corrected sign, with the original figure kept
visible as a footnote so the history is auditable.

#### 6. No band tests are added for `atr_pct` or `rsi`

The composite is already dead, so whether the scanner's bands are well chosen
is no longer a live question, and each extra test enlarges the BH family for
no gain. Both are recorded as **"monotonic association measured; the
scanner's banded use is not tested"**. `atr_pct`'s result stands as a
measurement of ATR against return, **not** as support for the scanner.

#### 7. A tradable target, and a robustness rule committed before it is run

The registered target is yfinance open-to-close. Nobody can trade the opening
print, the official NSE close is a last-30-minute weighted average rather than
a last trade, and 18.55% of stock-sessions disagreed between vendors by more
than 25 bp.

So on the selection sessions that overlap the Kite cache
(**2024-09-20 → 2026-01-01**), the three survivors are re-measured against a
**tradable Kite target**: open of the **09:20** bar → close of the **15:10**
bar, the last bar before the 15:15 square-off. Same eligibility, same 252-bar
warm-up, signs as corrected in amendment 5.

> **Committed before running:** a survivor keeps its status only if the
> Kite-target IC has the **same sign** and **|t| > 2** on the overlap.

The ratio of the Kite-target mean IC to the yfinance-target mean IC is
reported, so how much of the effect survives is a number rather than an
impression. **If most of it disappears once the first five minutes are
excluded, that is stated plainly**: it would mean the effect lives in the
opening print and cannot be captured.

#### 8. The promotion rule for the held-out look is tightened

A feature gets the **one** held-out look only if **all three** hold:

1. it survived **BH at q = 0.10** on the selection split (already true for
   `atr_pct`, `from_low`, `from_high`);
2. it **passes amendment 7** on the Kite target; and
3. for `from_high` and `from_low` only — its **partial IC controlling for
   `atr_pct`** has **|t| > 2** on selection.

**Bonferroni across however many qualify.** If only `atr_pct` qualifies it is
a single test at α = 0.05. The held-out look uses the **Kite target**, since
that is the tradable one, and the registered pass rule is unchanged: same
sign, **|t| > 1.5**.

Condition 3 exists because `atr_pct`, `from_high` and `from_low` are probably
**one factor, not three** — a volatile stock has a wide 52-week range, so all
three move together. Treating them as three independent discoveries would
triple-count a single association.

#### 9. Two caveats to carry into the write-up

- **The held-out window has not been examined for this particular
  relationship before**, so this look is cleaner than most in this phase. The
  general contamination note (earlier work ran against 2026-01-02 onward)
  still applies and is stated alongside it.
- **Survivorship bias is worst exactly here.** A volatility sort is where
  today's-NIFTY-100-applied-to-history distorts most, because the volatile
  names that fell out of the index are the ones missing.
