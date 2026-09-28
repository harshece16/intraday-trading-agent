# Universe width — results. **The running rule survives repaired data and honest fills (trial 126), with a smaller edge. The 400-stock book FAILS (trial 127). Ranks 401 to 1,000 could not be tested.**

**2026-09-28.** Pre-registration `prereg-universe-width.md` (`1e53917`),
amendments 1 to 4 (`a2372f8`, `ac42d2d`, `142134c`, `c93936e`), code
`3d210ce`, in that order with the reviews between them (entries 20 to 23).
Stage 0 ran twice. Each other part ran once: A′ 23:08, B′ 23:09, the three
tier records 23:11, W 23:11. Nothing dated 2026 was read.

## Verdict, in the pre-registration's terms

| Part | Rule | Result | |
| --- | --- | --- | --- |
| **Stage 0** (L41) | six gates | run 1 failed gate 6; run 2 passed all six | pass |
| **A′** (trial 126): trial 120's rule, repaired data, honest fills | trial 120's six criteria | **+0.71% a month net excess, t 2.51**; all six met | **survives** |
| **B′** (L42): L38's rule, the same | t ≥ 1.65, both halves positive | **+0.91% a month, t 3.00**; +0.57% / +1.24% | **survives** |
| **T3, T4, T5** (ranks 401–1,000) | at least 120 months | 63, 56 and 30 months | **not testable, not run** |
| **W** (trial 127): one book over the 400 most-traded | eight criteria | fails 1, 2 and 6 | **FAIL** |

Under the falsification table, W failing any of criteria 1 to 5 is a FAIL,
and the action is **no change**. The paper book stays on the 200
most-traded. A′ and B′ survived, so nothing about the running book goes to
the owner for a decision under this test.

## The three answers, plainly

**1. Does the rule work beyond rank 400? This test cannot say.** The
pre-registration required a stock to trade ₹70 lakh a day, so that a ₹70,000
order is at most 1% of a normal day, and it required 120 months to judge a
part. With that floor the list reaches 600 stocks only from August 2020. The
floor was my choice and it cost the main answer. It was not changed after
the list sizes were seen, and no return beyond rank 419 was read.

**2. Is a 400-stock book better than the 200-stock book? Not shown.**

| Over 2014-06 to 2025-11 (138 months) | 400-stock book (W) | Running book (A′) |
| --- | --- | --- |
| Net CAGR | 29.0% | 25.1% |
| Its own benchmark's CAGR | 16.1% | 14.3% |
| Maximum drawdown | −31.9% | −33.1% |
| Monthly Sharpe | 0.319 | 0.304 |

- W minus A′ is **+0.31% a month, t 0.97**. The rule needed t ≥ 1.65.
- More than half of that gap is the universe, not the rule. Less-traded
  stocks returned more in these years: the benchmarks differ by +0.17% a
  month (t 1.36). The rule's own edge differs by +0.14% (t 0.47).
- The two books hold 7 of 15 names in common on average.
- The test could detect a gap of 0.80% a month or more with 80% power. So
  the honest sentence is "no difference larger than about 0.8% a month", not
  "no difference".
- W also missed the family bar: t 2.76 against 2.807, Deflated Sharpe 0.871
  against 0.95 at a family of 10.

**3. Was the recorded result right? It was too high by about a ninth.**

| | Recorded (trial 120) | Repaired data, honest fills (A′) |
| --- | --- | --- |
| Net excess a month | +0.82% | **+0.71%** |
| t | 2.91 | **2.51** |
| Net CAGR | 22.3% | **20.6%** |
| Benchmark CAGR | 12.0% | 11.9% |
| Deflated Sharpe, family of 3 | 0.98 | **0.952** |

A′ clears trial 120's bar, and only just: t 2.51 against 2.394, Deflated
Sharpe 0.952 against 0.95. **At the family of 10 this project now counts, it
would not clear**: t 2.51 against 2.807, Deflated Sharpe 0.825. That
sentence is information, as amendment 2 wrote before the run. It does not
re-grade trial 120.

## What changed the numbers

A′ and B′ measure the repaired data and the fill rules together. They cannot
say how much comes from each (amendment 4).

The largest single cause is visible. In June 2021 three Adani stocks (ATGL,
ADANIGREEN, ADANIENSOL) moved to trade-for-trade and fell to their lower
band for days. The recorded book sold them at their last EQ close, a price
that no longer existed. The honest book could not sell at the band, held
them, and lost 4.4 points against the recorded book in June and 3.6 in July.

| | A′ | B′ | W |
| --- | --- | --- | --- |
| Buys carried past the fill day (upper band) | 7 | 14 | 14 |
| Buys cancelled after five sessions | 0 | 1 | 1 |
| Sells carried (lower band) | 9 | 4 | 9 |
| Sells filled from a trade-for-trade row | 14 | 15 | 18 |
| Held stocks whose listing ended | 2 | 3 | 2 |
| Months whose holdings differ from the recorded book | 97 of 190 | 98 of 190 | — |

No ended listing was in trade-for-trade at the end, so the stress case for
ended listings changed nothing. The five were mergers, takeovers or
buy-outs by the parent (BANKRAJAS, CAIRN, UTVSOF, ALFALAVAL, PRICOL).

**Corporate actions on a name the book held** (amendment 4, section 8):

| Book | Name and ex-date | What differs | On the name | On the book |
| --- | --- | --- | --- | --- |
| A′ | FRETAIL 2017-11-29 | The recorded panel applied a demerger ten sessions late; on the ex-date's own prices the rule refuses it | −5.5% | about −0.37 points |
| B′ | AARTIIND 2019-07-03 | Demerger applied on the ex-date, not ten sessions later | −3.5% | −0.23 points |
| B′, W | STAR 2024-12-06 | The same | +9.7% | +0.65 points |
| B′, W | AURUM 2020-12-23 | A dividend of ₹974 on ₹986, refused by the old cap | a 98.8% loss removed | B′'s month was +7.8 points against L38 |
| A′, W | ATGL 2021-06-24 | Dividend applied on the ex-date | under 0.01% | nil |

The AURUM fix was forced by stage 0 and was known to help B′ before B′ ran.
Without that one month B′'s mean would be about 0.04% a month lower.

**Demerger residuals.** Nine one-day jumps beyond ±30% sit on demerger dates
where the rule did adjust. None was held by any book on its date. One was
bought afterwards: A′ bought SINTEX at the 2017-08 and 2017-09 rebalances,
while its six-month return still held a +44.4% jump that is an artefact of
the demerger adjustment. Trial 120 did the same.

## Costs

| | A′ | B′ | W, base | W, stress |
| --- | --- | --- | --- | --- |
| Slippage per side | 0.05% flat | 0.10% flat | by rank, 0.05% to 0.75% | twice base |
| Net excess a month | +0.71% | +0.91% | +1.02% | +0.97% |
| Gross excess a month | +0.76% | +0.96% | +1.10% | — |
| One-sided turnover a year | 211% | 269% | 288% | 287% |
| All costs, share of the book a year | 0.69% | 1.14% | 1.33% | 2.01% |
| Added slippage per side that would zero the excess | 2.2% | 3.4% | 2.3% | 2.2% |
| Net excess at ₹1 lakh | +0.69% (t 2.45) | +0.89% (t 2.95) | +1.00% (t 2.72) | — |

The break-even figure is a first-order estimate that holds the trades fixed.
It says the result does not hang on the slippage guess: every fill would
have to cost about 2 percentage points more, per side, to erase it. The
slippage rates themselves are still judgements, not measurements (#66).

W charged 22 fills (2.2% of its turnover) at the last row of the slippage
table, 0.75% a side. Those are sales of names that had left the ranked list.

W's largest single buy was 0.94% of the stock's median day, inside the 1%
the liquidity floor was set for.

## Year by year

Sums of monthly net excess.

| Year | A′ | B′ | W |
| --- | --- | --- | --- |
| 2010 | −0.6% | +4.2% | — |
| 2011 | +21.4% | +19.4% | — |
| 2012 | +2.7% | +15.2% | — |
| 2013 | −6.4% | +17.9% | — |
| 2014 | +29.8% | −1.0% | +28.8% (from June) |
| 2015 | +9.2% | +10.2% | +22.5% |
| 2016 | −13.0% | −17.7% | −25.8% |
| 2017 | +18.0% | +5.2% | +26.4% |
| 2018 | +4.3% | +5.7% | +10.1% |
| 2019 | +1.9% | +15.0% | +8.6% |
| 2020 | +20.6% | +24.1% | +42.3% |
| 2021 | +14.4% | +27.6% | −4.1% |
| 2022 | +4.4% | +7.3% | +12.6% |
| 2023 | +28.6% | +30.6% | +31.6% |
| 2024 | +10.4% | +21.3% | +10.7% |
| 2025 | −11.7% | −14.0% | −23.5% |

The wider book's bad years are worse: −25.8% in 2016 and −23.5% in 2025,
against −13.0% and −11.7% for the running book. Over the last three years W's
excess is +0.54% a month (t 0.67) against A′'s +0.78% (t 1.13).

## Disclosures — read before relying on any number

1. **Nothing here is independent of trial 120.** A′ re-reads its months and
   its stocks. B′ re-reads L38's. W reads the same stocks over a shorter
   window, except 192 of its 55,600 member-months (0.35%) that rank 401 to
   419 without the screens.
2. **The family is now 10, and nothing in it clears the bar at 10.** Trial
   120 was judged at a family of 3. A′ is judged on trial 120's own criteria
   because it cannot create a new claim.
3. **The slippage table is a judgement.** The only tiered order-book study
   found is from 2010.
4. **Demergers.** The series assumes the value that left was put back into
   the parent at the ex-date open, which a holder could not do. For a stub
   that kept 5% of the price, the series applies the stub's move to the
   whole position. Inside the 400 most-traded this has no direction (14 of
   30 positive) and a wide spread (−46% to +77%).
5. **Band locks are under-counted.** The printed close is an average of the
   last 30 minutes, so a stock that locks only in the final minutes is
   missed. F&O stocks have no fixed band and are treated as if they had.
6. **Ended listings** are known from the whole panel, not at the time. The
   base case sells at the last close.
7. **Gate 6** takes membership at the month-end before a jump, so a jump
   after a gap longer than a month is not listed.
8. **Tax is not modelled.** Short-term capital gains tax applies to a book
   that turns over two to three times a year.
9. **The project-wide Deflated Sharpe for W is 0.553** at 126 trials.

## What this does not settle

- Whether the rule works beyond rank 400. For a later test: two jumps in DVL
  (+171% and +126%, on days with ₹13 lakh and ₹2 lakh traded) are kept as
  real prices and are not credible one-day returns for a banded stock.
- How much of the drop from +0.82% to +0.71% is the data and how much the
  fills. A run that separates them would be a new counted trial.
- What slippage really is for a small order in these stocks.

## What follows

1. **No change to the paper book's universe.**
2. **The paper book's own loader has the three defects** this test repaired
   in the research loader: #175 (trade-for-trade rows), #177
   (consolidations) and #178 (dividend amounts). Its first rebalance is on
   the evening of 2026-10-01. The fix belongs before that.
3. **The paper book's forward band** expects +0.82% a month, trial 120's
   figure. A′ says +0.71%. Keeping 0.82 makes the band stricter. Changing it
   is the owner's decision.
4. **A test of ranks beyond 400 needs a new pre-registration** with a floor
   set by a rule that uses no return, new ledger numbers counted in the same
   family, the fill rules and slippage table unchanged, and these
   disclosures: the list sizes, the tradability map, the traded value at
   each rank and the jump list have been seen; and a floor that lets the
   tiers start in 2010 adds years whose results for ranks 1 to 400 are
   known. Whether to have one is the owner's decision.

## Files

| File | What |
| --- | --- |
| `data/momentum_width_stage0_run1.json`, `_run2.json` | Stage 0, both runs |
| `data/momentum_width_panel_differences.json` | The 743 corporate actions that differ between the panels |
| `data/momentum_width_A.json`, `_B.json`, `_W.json` | The three runs, with monthly series and holdings |
| `data/momentum_width_T3.json`, `_T4.json`, `_T5.json` | "Not testable" records; no simulation |
| `data/momentum_width_report.json` | Actions and residuals on held names |
| `backend/research/momentum_width.py`, `panel_differences.py`, `width_report.py` | Code |
