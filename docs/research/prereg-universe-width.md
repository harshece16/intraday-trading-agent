# Pre-registration — universe width: does the momentum rule hold in less-traded stocks, and is a wider book better than the one running?

**Written 2026-09-28, before any code for it exists.** Owner's question the
same day: "start research on stock picking maybe increase from 100 to all
stocks not just 100 and if our first pick is wrong then whole analysis is
useless". Background reading: `stock-picking-sweep-2026-09-28.md`.

The paper momentum book picks 15 stocks from the 200 most-traded NSE shares.
This test asks two things about that first cut:

1. Does the same rule work on stocks ranked 401 to 1,000 by traded value,
   which no test in this project has read?
2. Is one book that picks from a wider list better than the book that is
   running?

It does not test the intraday scanner's list. That was measured in L26, L27
and L34 and widening did not help; the sweep note gives the figures.

## Parts

| Part | What | Ledger |
| --- | --- | --- |
| Stage 0 | Data gate and a tradability map. No strategy return is read | Look **L41** |
| A′, B′ | Trial 120 and L38 re-run on the repaired price panel with honest fills | Replications with a declared fix (#175). Not counted |
| T3, T4, T5 | The unchanged rule on ranks 401–600, 601–800, 801–1,000 | Look **L42**, three confirmations |
| W | One book that picks from ranks 1 to K | **Trial 126**, momentum family, N_family = 4 |

## What had been seen when this was written

- Trial 120 (top 200), L38 (ranks 201–400) and the 2026 held-out run of
  Part A, with their monthly series.
- The two sweeps of 2026-09-28. One read published returns of NSE factor
  indices to August 2026 and Indian momentum studies. The other computed
  descriptive statistics from the project's 2025 bhavcopies for ranks 1 to
  1,892: traded value, number of trades, days with no trade, band locks,
  series membership and two spread estimators. It read daily prices. It
  computed no momentum score and no strategy return.
- No return of any rule on ranks beyond 400 has been computed from project
  data.
- The slippage figures below are judgements drawn from a 2010 order-book
  study, not measurements. The project has not measured delivery slippage
  (#66).
- `entry-timing-sweep-2026-09-27.md` named ranks 401–600 as the unseen sample
  for a later "frog-in-the-pan" trial. This test reads the base rule on those
  ranks, so that sample is no longer unseen for the base rule.

## The price panel (the fix for #175)

3i's loader kept EQ-series rows only. The repaired panel:

- keeps rows of series **EQ, BE and BZ**. If a symbol has more than one of
  these on a day, EQ is used, then BE, then BZ. SME series (SM, ST, SZ) are
  never loaded;
- keeps, for each row: series, open, high, low, close, previous close as
  printed, traded value, ISIN;
- applies corporate actions and dividends exactly as 3i, over all rows;
- excludes fund units exactly as 3i;
- never loads a session on or after 2026-01-02.

The old loader's default output must not change, so trial 120 stays
reproducible.

## Rules that do not change

Signal, portfolio, rebalance, costs and benchmark are 3i's:

- **Signal:** mean(r6/σ, r12/σ), returns to month-end t−1, σ over 252
  sessions. Prices come from the repaired panel.
- **Portfolio:** long only, 15 names, equal weight at entry, keep while rank
  ≤ 30 within the universe being tested, replace from the top. Decided at
  month-end t, ordered for the next session.
- **Costs:** STT 0.1% each side, stamp 0.015% on buys, NSE 0.00307%, SEBI,
  GST on those, DP ₹15.34 per sell.
- **Benchmark:** the same universe equal-weighted, churn only, the same
  percentage costs and fill rules, no DP charge.
- **Capital:** ₹10,00,000. ₹1 L and ₹25 L columns reported.
- **Sample:** selection sample only, rebalances 2010-02 to 2025-11. 2026 is
  not read.

## Eligibility

Eligibility and the liquidity ranking are computed from **EQ rows only**, as
3i did. BE and BZ rows are used for pricing, for selling and for screen S1.

**E-3i (parts A′ and B′), unchanged.** At month-end t: at least 250 EQ rows
of history, an EQ row on t, as-printed close on t ≥ ₹20. Ranked by median
daily traded value over the trailing 126 sessions, absent days counted as
zero.

**E-wide (parts T3, T4, T5 and W).** E-3i, and all three screens:

| Screen | Rule | Why |
| --- | --- | --- |
| S1 | No BE or BZ row in the last 60 sessions | Trade-for-trade is a surveillance action. It is also the only trace of GSM and ESM in a bhavcopy |
| S2 | Traded on at least 120 of the last 126 sessions (any of the three series) | NSE asks 90% for the NIFTY 500 |
| S3 | Median daily traded value over 126 sessions ≥ ₹70 lakh | A ₹70,000 order is then at most 1% of a normal day |

The ranking is the E-3i ranking with the screened names removed. Removing
names can only move a stock up. A stock at E-wide rank 401 or lower is
therefore at E-3i rank 401 or lower, and was outside every universe trial
120 and L38 could read on that date.

**Tiers:** T3 = E-wide ranks 401–600, T4 = 601–800, T5 = 801–1,000.

## Honest fills

Orders decided at month-end t are placed for the next session, f. These
rules apply to every part, strategy and benchmark alike.

| | Rule |
| --- | --- |
| H1 | The fill price is the close of the stock's row on the fill session, in whichever of the three series it traded |
| H2 | No row on that session: no fill. The order is carried to the next session |
| H3 | **Band lock.** A buy is not filled on a session where close ≥ high and the day's return on the printed previous close lies between L − 0.30 and L + 0.10 percentage points, for L = 2, 5, 10 or 20%. A sell is not filled where close ≤ low and the return lies between −L − 0.10 and −L + 0.30. The order is carried. This is the rule the sweep's lock counts used |
| H4 | A buy is carried for at most 5 sessions after f, then cancelled. Its cash stays uninvested until the next rebalance. A sell is carried until it fills. Every order still open at the next month-end is dropped and decided again |
| H5 | **Ended chain.** A holding whose last row is before t is sold at its last close, as in 3i. Stress case: if any of its last 20 rows is BE or BZ, the proceeds are zero |
| H6 | **Slippage per side** follows the stock's E-3i rank at t (table below). A stock with no E-3i rank on t pays the last row. Parts A′ and B′ keep 3i's flat 0.05% and 0.10% |

| E-3i rank at t | Base | Stress |
| --- | --- | --- |
| 1–200 | 0.05% | 0.10% |
| 201–400 | 0.15% | 0.30% |
| 401–600 | 0.25% | 0.50% |
| 601–1,000 | 0.40% | 0.80% |
| beyond 1,000, or unranked (not in EQ, below ₹20, not traded) | 0.75% | 1.50% |

Each of T3, T4, T5 and W is simulated twice: base costs, and stress costs
with the H5 stress case. That is one configuration under two cost
assumptions, not two trials.

Known limits of these rules, accepted now:

- The printed close of most stocks is the average price of the last 30
  minutes. A stock that locks only in the final minutes closes below its high
  and H3 misses it.
- F&O stocks have no fixed band. H3 is applied to every stock, so an F&O
  stock that closes at its high about 10% up is treated as locked.
- Past membership of the surveillance lists (ASM, GSM, ESM) is not
  available. S1 and H3 stand in for it.
- S3 is set for a ₹10 lakh book. The simulated book compounds, so its later
  positions are larger than ₹70,000. The largest position as a share of the
  stock's median daily value is reported for each year.

## Stage 0 — L41 (no strategy return is read)

Gates. If one fails, the test stops and reports.

1. **Coverage**, as 3i: at least 240 sessions a year from 2009, a file within
   3 sessions of every month-end.
2. **Loader parity.** With the default arguments the refactored loader
   returns the panel 3i used, value for value.
3. **Universe parity.** On the repaired panel the E-3i ranked list, ranks 1
   to 400, has the same members as on 3i's panel at every month-end. Gate:
   at least 99.5% of member-months identical. Every difference is listed.
4. **Engine parity.** The new simulator with honest fills switched off, on
   3i's panel, reproduces the monthly excess series of trial 120 and of L38
   to within 1e-9. This re-reads known numbers only.
5. **Adjustment consistency**, as 3i but for chains inside the E-3i top 1,000
   at the month-end before the ex-date: at least 97% of official splits and
   bonuses give an adjusted ex-date return within ±20%. Failures listed.
6. **Residual jumps.** Every one-day adjusted return below −30% or above
   +30%, on a day with traded value above ₹1 crore, for a chain inside the
   E-3i top 1,000, is listed and checked against NSE's corporate-actions
   file within 5 sessions either side. Gate: after fixes, none has an action
   in NSE's file that the loader did not apply. A jump with no action in the
   file is kept as a real price.
7. **Tier existence.** The size of the E-wide list at every month-end. A
   part runs from the first month-end M0 ≥ 2010-02 such that the list holds
   its deepest rank at M0 and at every later month-end. A part with fewer
   than 120 monthly returns is **not testable** and is not judged.

A loader or parser defect found at stage 0 may be fixed and stage 0 re-run,
with both runs kept and an amendment written, as in 3i. No return is read
before stage 0 passes.

Also reported, by tier and year: share of stock-days with no trade, upper
and lower lock rates, share of names with a BE or BZ row, traded value at
each tier boundary.

## Parts A′ and B′ — the effect of the fix on results already recorded

Trial 120's and L38's rules, E-3i, flat slippage, on the repaired panel with
rules H1 to H5 (base case). One run each. Reported beside the recorded
results, month by month, with counts of carried fills, cancelled buys, sells
priced from BE or BZ rows and ended chains.

These are replications with a declared fix. They are not new trials and
cannot be selected.

**If A′ fails any of trial 120's six criteria, or B′ fails L38's rule,** the
3i results file is amended to say the result did not survive honest fills,
and the running paper book goes to the owner for a decision. The other parts
still run and are reported.

## Parts T3, T4, T5 — L42, confirmations on unseen stocks

The unchanged rule on each tier. They confirm or fail to confirm trial 120
on new stocks. They are not competing configurations.

A tier **confirms** if all hold:

1. Base costs: mean monthly net excess over its benchmark > 0 with
   **t ≥ 2.13** (one-sided 5%, Bonferroni across the three tiers).
2. Base costs: the mean is positive in both halves of the tier's own months.
   The first half takes the extra month, which gives 3i's split (2010-02 to
   2017-12, 2018-01 on) for a tier that runs the full sample.
3. Stress costs: mean monthly net excess > 0.

## Part W — trial 126, the wide book

**Universe:** E-wide ranks 1 to K, where K = 400 + 200 × (the number of
tiers that confirm, counted outward from T3 and stopping at the first tier
that fails or is not testable). K is 400, 600, 800 or 1,000. With K = 400
the book still runs: both halves of that list were tested separately, the
single book never was.

K is set by results on the same months, so W is not independent of the
tiers, of trial 120 or of L38. Its first five criteria are close to a
foregone conclusion if those passed. The criteria that carry information are
6 and 7.

**Passes** if all hold:

1. Base costs: mean monthly net excess over its own benchmark > 0 and
   **t ≥ 2.498** (two-sided 5%, Bonferroni across N_family = 4).
2. Corrected Deflated Sharpe ≥ 0.95 at N = 4.
3. Positive in both halves and over the last three years (2023-01 on).
4. Net CAGR minus benchmark net CAGR ≥ 2.0 points, and at least 100 round
   trips.
5. Stress costs: mean monthly net excess > 0.
6. **Better than the running book.** The paired monthly difference, W's net
   return minus A′'s net return over their common months, has mean > 0 with
   **t ≥ 1.65** (one-sided 5%), and the mean is positive in both halves.
7. **No worse for risk.** W's net Sharpe ratio (monthly mean over monthly
   standard deviation) is at least A′'s.

The burden of proof is on the change. If W is not shown to be better, the
book stays as it is. The smallest difference this test could detect at 80%
power is reported with the result, so a miss reads as "no difference larger
than X".

## What a pass allows

Only this: a second paper sleeve running W's rule beside the present paper
book. The present book and its forward record are not touched. Moving the
main book to the wider list, a held-out check on 2026, and any real money
are the owner's decisions.

## Falsification branches, written now

| Tiers | W | Meaning | Action |
| --- | --- | --- | --- |
| none confirms | fails 6 or 7 | The rule is not shown to work beyond rank 400 at honest cost | No change. The line is closed: no re-run with other costs, screens or holdings |
| none confirms | passes all (K = 400) | A 400-stock list beats the 200-stock list | Paper sleeve beside the running book |
| one or more confirm | fails 6 or 7 | The effect reaches less-traded stocks, but a wider book is not shown to beat the running one | No change. The choice of 200 is not what makes or breaks the rule |
| one or more confirm | passes all | Wider is better on the selection sample | Paper sleeve beside the running book |
| any | passes 1–5 only | | FAIL |
| A′ or B′ fails 3i's rule | any | 3i did not survive honest fills | 3i results amended; owner decides on the running book |

## Also reported (information only)

Gross versions; the ₹1 L and ₹25 L columns; turnover and cost as a share of
the book; yearly excess; maximum drawdown and the longest time under water;
fills carried by reason, buys cancelled, sells priced from BE or BZ rows,
ended chains and how many ended in BE or BZ; largest position as a share of
median daily value; how many names W and A′ hold in common; the project-wide
Deflated Sharpe at the ledger's count.

## Not done here

- 2026 is not read. The momentum family's held-out look was spent once, on
  Part A.
- The number of holdings, the keep rank, the signal and the rebalance
  schedule are not varied.
- No live or paper configuration is changed by this test.

## Code boundary and order

`backend/research/nse_prices.py` gains the repaired panel as an option, with
its default output unchanged. `backend/research/momentum_width.py` holds
stage 0 and every part. Both are committed after this file. Nothing on the
live path imports them. One run per part, in the order stage 0, A′, B′, T3,
T4, T5, W. A crash before a statistic is printed may be fixed and re-run with
both recorded.

---

# Amendment 1 — 2026-09-28, after reviewer entry 20, before any run

**State when this was written.** Pre-registration `1e53917`. Code `946cc31`
was committed after it and before the review. No part has run and no
repaired panel has been built. One software check has run: the refactored
loader rebuilt 3i's panel with its default arguments and matched the cached
panel with 0 differences over 4,215 sessions and 2,883 chains. It read
nothing new. The 2025 descriptive script was run a second time to save its
printed output; the figures match the sweep note.

The code in `946cc31` is not approved. It is brought into line with this
amendment in a later commit. Where this amendment and the text above
disagree, the amendment governs.

## 1. What counts, and the ledger numbers (C2, C3)

| Part | Ledger |
| --- | --- |
| Stage 0 | Look L41 |
| A′ | **Trial 126** |
| B′ | Look L42 |
| T3, T4, T5 | Looks L43, L44, L45 |
| W | **Trial 127** |

- **A′ is a counted trial.** It changes the price panel and the fill model,
  so it is not an identical configuration. The declared fix for #175 is the
  pricing of BE and BZ rows (H1, H2). H3 and H4 are new fill assumptions.
- **N_family = 10**, by the owner's rule of 2026-09-26, which counts every
  configuration and every look that tested the mechanism against a pass
  rule: trials 118, 119, 120; L38; A′ and B′; T3, T4, T5; W.
- **W, criterion 1:** t ≥ **2.807** (two-sided 5%, Bonferroni across 10).
  **Criterion 2:** Deflated Sharpe ≥ 0.95 at **N = 10**.
- A′ is judged by trial 120's own six criteria, as written above. Its t is
  also reported against 2.807.

## 2. K is fixed now (C4, option a)

**K = 800.** W picks from E-wide ranks 1 to 800. The sweep recommended 800
as the floor before any return was read, and NSE's own NIFTY 500 rules stop
at rank 800.

- If stage 0 shows W at K = 800 would have fewer than 120 monthly returns,
  K = 600. If that would too, K = 400. This is decided from list sizes only.
- **Criterion 8, new:** every tier inside K confirms. For K = 800 that is T3
  and T4.
- T5 is reported and changes nothing.
- Criterion 6 stays at t ≥ 1.65.

## 3. Thresholds (C1)

The code uses 2.13 and 1.65, as written. It had 2.128 and 1.645.

## 4. Halves (C5)

The sentence "the first half takes the extra month" was wrong. **A part with
n monthly returns puts the first floor(n/2) in the first half.** A return is
labelled by the rebalance month that ends it. For n = 189 this is 3i's
split: 94 returns to 2017-12, then 95 from 2018-01.

This rule serves the tiers, W's criterion 3 on its own months, and criterion
6 on the months W and A′ have in common. Criterion 7 uses the common months.

## 5. Order of operations on the fill session (C6)

On session f, sells that can fill are filled first. A holding whose sell is
carried stays in the book and counts as held. Vacancies are 15 minus the
names held. Each buy's rupee amount is fixed on f as cash after f's filled
sells divided by vacancies, and does not change while the buy is carried.
Cash never goes below zero. Proceeds of a sell that fills after f stay in
cash until the next rebalance. The benchmark follows the same sequence.

## 6. Small definitions (C7)

- A row with zero traded value is "no trade": no fill under H2, and not a
  traded day under S2. Eligibility and ranking keep 3i's definition, a row
  with a close, so the E-3i lists can match 3i's.
- H3 uses the close, high, low and previous close as printed.
- A buy is tried on f and on the five sessions after it.
- Ties break as in 3i's code. Monthly value is measured at the close of f.

## 7. H3 for low-priced stocks (C8)

Below about ₹17 one tick is wider than the 0.30-point window, so a lock
could be missed. A stock is ≥ ₹20 when bought, not when sold. Added: where
the printed previous close is below ₹20, a row is also locked if the close
is at the day's high (low) and within ₹0.05 of previous close × (1 + L)
(1 − L).

## 8. Known limits, added (C9, C10)

- **H5.** Whether a chain has ended is known from the whole panel, not at t.
  A chain that stops near the end of 2025 cannot be told from a suspension.
  The base case flatters failures. Every ended chain that was held is
  reported: month, last series, last close, base and stress proceeds.
- **H6.** The last row charges 0.75% where the sweep's own table says
  "exclude". The stress figures for ranks beyond 600 sit below the top of
  the 2010 ranges the sweep cites. Stress means twice base. It is not an
  upper bound. Reported for each part: the count and turnover share of fills
  charged at the last row, and the slippage per side at which the base
  result would be zero.

## 9. Stage 0 (C11, C12, C13, C15, C16)

- **Gates 5 and 6** cover every chain that is in E-wide ranks 1–1,000 or
  E-3i ranks 1–1,000 at the month-end before. The ₹1 crore floor is dropped.
  "One-day" means row to row, so a jump across a gap in trading is listed.
- **Consolidations.** The loader applies none, and an unadjusted
  consolidation looks like a very large gain to a momentum rank. The
  repaired panel applies "consolidation from Rs a to Rs b", b > a, as prices
  before the ex-date × (b/a). The default panel is unchanged.
- **Gate 3** is evaluated for ranks 1–200 and ranks 201–400 separately, each
  at 99.5%.
- **At most two rounds** of fix and re-run. No rule under Eligibility,
  Honest fills or the pass criteria changes after any stage-0 output or any
  part's result has been seen.
- **Also reported:** for each tier, the member-months that were inside the
  universes trial 120 and L38 read that month; the share of tier
  member-months that belong to chains ever ranked 1–400; and how many
  member-months in ranks 1–200 and 201–400 fail S1, S2 or S3.

## 10. What the tiers are, in plain words (C15)

The rank claim is true on the repaired panel by construction. It is not
exactly true of what trial 120 and L38 read, because gate 3 lets 0.5% of
member-months differ. "Unseen stocks" is replaced by **"stock-months not
read"**, and stage 0 reports the exceptions.

The tiers share their calendar months with trial 120 and L38. The monthly
excess of those two correlates 0.37, so the tiers are new stocks in old
months, not independent samples.

## 11. Criterion 6 (C16)

**Added to "What had been seen"**, from the recorded series of trial 120 and
L38:

- L38's book minus trial 120's book: +0.50% a month, t 1.42, positive in
  both halves. Sharpe 0.314 against 0.282.
- Ranks 201–400 equal-weighted beat the 200 most-traded equal-weighted by
  0.31% a month (t 1.64).

So the bound of 1.65 sits just above a known 1.42 for the nearest comparison
that exists.

| Asymmetry between W and A′ | Direction |
| --- | --- |
| W pays slippage by rank; A′ pays a flat 0.05% | Against W, about 0.5% a year for each 10 bp a side |
| W applies screens S1 to S3 inside ranks 1–200; A′ does not | Unknown; stage 0 counts the names affected |
| Less-traded stocks returned more over these months | For W, about 3.8% a year between the two 200-stock lists |

- W minus A′ is reported in two parts: the difference in excess over each
  book's own benchmark, and the difference between the benchmarks.
- If criterion 6 passes and the difference in excess is zero or less, the
  result is recorded as: "the wider universe returned more in this sample;
  the rule did not add more there".
- "A 400-stock list beats the 200-stock list" is replaced by "the screened
  wide book beat the running book on the selection sample".

**Power, stated now.** With the spread seen between the two recorded books,
criterion 6 needs +0.58% a month, and 80% power needs about 0.87%. A tier
needs +0.64% a month to confirm, and 80% power needs 0.90% (1.13% for a tier
with 120 months). A miss is weak evidence of absence.

## 12. Falsification branches (C14) — replaces the table above

| Tiers inside K | W | Meaning | Action |
| --- | --- | --- | --- |
| any | fails any of 1 to 5 | The wide book does not clear the family bar | FAIL |
| one or more fails | any | The rule is not shown to hold across the wider list | FAIL (criterion 8). No re-run with other costs, screens or holdings |
| all confirm | fails 6 or 7 | The effect reaches less-traded stocks; a wider book is not shown to beat the running one | No change |
| all confirm | passes 1 to 8 | The screened wide book beat the running book on the selection sample | A recommendation to the owner (section 13) |
| A′ or B′ fails 3i's rule | any | 3i did not survive honest fills | 3i's results file is amended. If W passes, nothing goes to a sleeve. The owner decides |

## 13. What a pass allows (O1) — replaces the section above

**A recommendation only.** The owner's decision of 2026-09-26 requires a
held-out confirmation before any paper deployment, and this family's 2026
look was spent on Part A. A paper sleeve, its forward band and any 2026
check are the owner's decisions.

## 14. The sample named in the entry-timing sweep (O2)

Ranks 401–600 were named there for a later trial. The owner's request of
2026-09-28, to research picking from more stocks, cannot be answered without
reading returns on those ranks. That request is read as the choice to spend
the sample here, and the owner is told so with the result. A later
frog-in-the-pan trial can still run its paired test on these ranks, and must
disclose that the base rule was read first.

## 15. Wording elsewhere (C17, C18)

- The sentence at the top, "widening did not help", is replaced by: "on the
  one wider list measured, no rule cleared costs; L34's proxy is weak
  evidence by the ledger's own note".
- Seven statements in the sweep note claimed more than its sources show.
  They are reworded in the same commit as this amendment.
- The ledger gains a held-out exposure row for the published 2026 index
  returns the sweep read, a row for the 2025 descriptive read with the
  script's printed output, and a note that ranks 401–600 stop being unread
  for the base rule once T3 runs.
