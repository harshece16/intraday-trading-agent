# Pre-registration — frog-in-the-pan tie-break: does filling the book's vacancies with "continuous-information" winners beat filling them by rank?

**Written 2026-10-14, before any code for it exists.** No
information-discreteness value, holding list or return of this rule has been
computed from project data. This file is committed before
`backend/research/momentum_fip.py` exists and before `momentum_width.py` is
touched; the results file cites the three commits in order.

**No reviewer has read this file.** The last momentum pre-registration
(`prereg-universe-width.md`) went through four reviewer rounds before a
return was read. This one runs on the owner's instruction without that step.
The results go to `reviewer-outbox.md` for review afterwards, and the
results file says so.

## Why this exists, and what the prior is

The owner asked on 2026-10-14 for the frog-in-the-pan idea to be drafted as a
pre-registration, was told the recommendation was to leave it, and then
instructed: "go do it and add the strategy result". The idea is not new to
this project:

- `entry-timing-sweep-2026-09-27.md` sketched it as "Trial 3 (only after 1
  and 2)": a tie-break inside the top 30, shadow sleeve only. Trials 1 (a
  volatility overlay) and 2 (promoter purchases) of that sketch never ran.
- `profitability-sweep-2026-10-01.md` §5 then decided **Leave**, with a prior
  of **5–8%** of passing the project's gate: "long-only return unchanged; a
  live US fund gained nothing from frog-in-the-pan".
- §4 of the same sweep allows "at most one or two trials", the first a
  tax-aware hold rule. This would be an extra one.

**Nothing read on 2026-10-14 changes that prior.** That session re-read the
abstract of Da, Gurun & Warachka (*RFS* 2014,
https://academicweb.nd.edu/~zda/Frog.pdf), which both sweeps already cite. It
retrieved no new evidence, and nothing Indian, net of costs or long-only.

**The expected result is a fail for lack of power, even if the effect is
real** (see "Power"). The file is written so that outcome is read correctly,
and so a cheap stage 0 can withdraw the trial before it is spent.

## What had been seen when this was written

- **The base rule's returns, in full.** Top 200, 2010-02 → 2025-11: trials
  119, 120 and 126 (+0.71% a month net excess, t 2.51). Ranks 201–400: L38,
  L42 (+0.91%, t 3.00) and trial 127. The 2026 held-out months were read once
  for the momentum family (3i confirmation).
- **Nothing of this rule.** No script or data file in the repository computes
  information discreteness; only the two sweeps mention it.
- **Published results on overlapping data.** Goyal, Jegadeesh & Subrahmanyam
  (49 countries including India, to 2020, gross long-short) and SSRN 4977717
  (India 2008–24, gross, abstract only) both report that it helps. So others
  have tested the idea on largely these stocks and years. **A pass here is
  not out-of-sample evidence for the idea.** It would show only that a
  long-only version, net of costs and with honest fills, improves this book.
- **Samples the 2026-09-27 sketch named, and why they are not used.**
  - 2002–09, top 200: the repository has no price panel before 2009. The
    stretch is partly seen at the index level and can be spent once (sweep
    §4, §9). Not used here (decision 5).
  - 2010–25, ranks 401–600: not testable. The screened list reaches 600
    names only from 2020-08 (`results-universe-width.md`).

## Rules that do not change

Everything in trial 126's configuration: the repaired price panel,
eligibility, the score (`momentum_3i.scores`: the mean of the 6- and 12-month
returns to the previous month-end, each divided by the daily volatility), 15
equal-weighted holdings, the sell rule (listing ended, left the list, or rank
above 30), the fill session, honest fills, charges, slippage, the
equal-weighted benchmark and the capital.

**Parity first.** The base arm, run through the new script, must reproduce
the stored holdings of `momentum_width_A.json` and `momentum_width_B.json`
for every month. If it does not, nothing else is read.

## The one change: the order in which vacancies are filled

The base fills vacancies with the best-ranked names not already held
(`momentum_width.py` lines 379–386). This rule fills them by lowest
information discreteness instead.

**Information discreteness (ID)**, as Da et al. define it, for a name ranked
30 or better at a month-end:

- **Window:** the sessions after the month-end 13 months back, up to the
  previous month-end. These are the same 12 months as the score's 12-month
  return.
- **Daily returns:** on the panel's adjusted closes, between the name's
  consecutive rows inside the window.
- `pos` is the share of those returns above zero and `neg` the share below
  zero. A zero return counts in the denominator only.
- `PRET` is the score's own 12-month return.
- **ID = sign(PRET) × (neg − pos).** Lower means the return arrived in many
  small steps.
- A name with fewer than 200 daily returns in the window, or `PRET` = 0, has
  no ID.

**Filling.** Candidates are the names ranked 30 or better that are not held.
They are taken in ascending ID, ties to the better rank. Names with no ID
come after every name that has one, in rank order. If vacancies remain, the
base order continues below rank 30.

There is no threshold and nothing to tune. The window, the cut at 30 and the
direction are fixed here. No other window, no magnitude-weighted ID and no
other cut may be run under this file.

## Samples

| | Stocks | Months | Slippage a side |
| --- | --- | --- | --- |
| **S1** | Top 200 (configuration A′) | 2010-02 → 2025-11, 190 | 0.05% |
| **S2** | Ranks 201–400 (configuration B′) | the same 190 | 0.10% |

Halves: 2010-02 → 2017-12 and 2018-01 → 2025-11. Last three years: 2023-01 →
2025-11. No 2026 session is read.

## Stage 0 — a look, no return is read

Stage 0 writes holdings and counts only. The simulator values both books
internally to size orders; stage 0 neither prints nor stores those values.

1. Parity of the base arm, as above.
2. **Coverage:** the share of top-30 name-months that have an ID.
3. **How different the two books are:** the mean number of the 15 holdings
   that differ between the arms, by month, in S1 and S2.
4. **Name turnover:** buys a year in each arm.
5. The mean monthly rank correlation between ID and score rank inside the top
   30, and the spread of ID across those 30.

**Withdrawal rules, fixed now.**

- Parity fails: stop. It is a bug; file it.
- Coverage below 97%: stop and report.
- **Fewer than 2.0 of 15 holdings differ on average in S1: withdraw, and no
  trial is spent.** The two books are then too alike for a paired test to
  separate, and a change that size would not matter to the book.

The rules above are mechanical, so the trial runs straight after a stage 0
that passes them; the owner asked for the result, not for a stop. Stage 0's
output is committed before the trial runs, and the commit order shows it.

## The trial — S1, and S2 as its confirmation

One run. It simulates both arms on both samples and reads their net monthly
returns. All of the following are required for a pass:

1. **Paired, S1:** the mean of (this rule's net monthly return − the base's)
   is above zero, with **t ≥ 1.65** (one-sided 5%).
2. **Paired, S2:** the same, t ≥ 1.65.
3. **The family bar, S1, on this rule's own net excess over the benchmark,**
   at N_family = 11 (decision 2):
   - t ≥ **2.838** (two-sided Bonferroni at 5% across 11);
   - corrected Deflated Sharpe ≥ 0.95 at N = 11;
   - positive in both halves and over the last three years;
   - net CAGR at least 2.0 points above the benchmark's;
   - at least 100 round trips.

The base rule itself is at t 2.51, below this bar. Item 3 therefore needs the
tie-break to lift the book's information ratio by about 13%.

## Power, stated up front

These figures are rough arithmetic, not measurements.

- If *d* of the 15 holdings differ, the monthly difference between the arms
  has a standard deviation of roughly √*d* × 1%. That assumes a pair of
  swapped stocks differs by about 15% a month.
- Over 190 months the smallest difference detectable with 80% power is then
  about 0.27% a month at a 1.5% standard deviation, 0.36% at 2.0% and 0.49%
  at 2.7%.
- The US spread between the most continuous and most discrete winners,
  gross, suggests an edge per swapped name of perhaps 0.3% a month. At
  *d* = 6 that is a difference of 0.12% a month and an expected paired t of
  about 0.7.
- `R2-improving-momentum.md` reached the same place: a real +0.15% a month
  gives t ≈ 0.9 over 190 months.

**So items 1 and 2 are likely to fail even if the published effect holds in
India.** This agrees with the sweep's 5–8%.

## What a pass allows

A shadow sleeve inside the daily `momentum_book.py` job, with its own NAV on
the Momentum Book page. The paper book, its band and its switch-off stay as
they are. Nothing else.

The sleeve would be a record, not a test. By the arithmetic above, a forward
paired comparison cannot conclude in any useful time.

## Falsification branches, written now

| Outcome | Reading |
| --- | --- |
| Both paired t between −1.65 and +1.65 (the expected result) | **FAIL.** The book cannot measure the effect at this size. It is not evidence against the published effect. The candidate is closed; no variant follows without a new family count. |
| Items 1 and 2 pass, item 3 fails | **FAIL.** The tie-break helps, but the book still does not clear its family bar. Recorded as information for the owner. |
| Item 1 passes, item 2 fails | **FAIL.** Specific to one set of stocks. No third rank band is tried. |
| Either paired t ≤ −1.65 | **FAIL.** Continuous-information winners did worse here. The sign is not flipped and re-tested. |
| The difference is positive gross and negative net | **FAIL.** The tie-break buys names nearer the rank-30 exit and pays for it in turnover. |

## Also reported (information only)

The gross difference; turnover and all costs in each arm; holdings in common;
Sharpe ratio and deepest drawdown in each arm; the difference by half; the
smallest difference detectable at 80% power, from the measured standard
deviation; the mean ID of the holdings in each arm; project-wide Deflated
Sharpe at the full trial count.

## Not done here

No long-short book. No 2026 data. No 2002–09 build. No ranks beyond 400. No
change to the score, the sell rule or the paper book. No second variant.

## Ledger

- Stage 0 is a look: **L56**.
- S1 is one strategy trial, the next free number (204 unless another is
  registered first), counted when its statistics are read.
- S2 is its confirmation, a look: **L57**, as L38 was for trial 120.
- Momentum family: N = 11 (trials 118–120, L38, A′, B′, T3, T4, T5, W and
  this one).

## Code boundary and order

- `backend/research/momentum_width.py` gains one optional argument to
  `simulate` that orders the vacancy candidates. Its default leaves every
  recorded result unchanged, and the parity check proves it.
- `backend/research/momentum_fip.py` holds the ID calculation, stage 0 and
  the trial. Both are committed after this file.
- Nothing on the live path imports them
  (`tests/test_research_splits.py::test_no_live_module_imports_research`).
- Order: stage 0, the owner reads it, then one run of the trial. A crash
  before any statistic is printed may be fixed and re-run, with both runs
  recorded.

## Owner decisions, as taken on 2026-10-14

The owner's instruction was "go do it and add the strategy result". It
settles decisions 1 and 3 in words. Decisions 2, 4 and 5 are this file's
defaults; the owner did not confirm them one by one.

1. **Run it.** The 2026-10-01 decision was Leave, and nothing since has
   changed the evidence. The owner chose to run it. If stage 0 does not
   withdraw it, the trial costs one count and raises the bar for every later
   momentum trial.
2. **The family** is momentum at N = 11, t ≥ 2.838. No tax-aware hold rule
   has been registered; the highest trial on the ledger is 203.
3. **The order.** It runs now, ahead of the tax-aware hold rule that sweep §4
   put first.
4. **What a pass changes:** a shadow sleeve only, which by the arithmetic
   above cannot conclude. The paper book does not change on this result,
   whatever it is.
5. **2002–09** is not used and stays unread for the base rule.
