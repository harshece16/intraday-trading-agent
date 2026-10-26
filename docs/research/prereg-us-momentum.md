# Pre-registration: trial 205, trial 126's momentum rule on US stocks

**Written 2026-10-26, before any US price is downloaded and before any code
exists.** The owner asked on 2026-10-26 about trading international markets
through IBKR or Alpaca, then said "yes" to pre-registering this trial. The
desk review behind it is `international-brokers-2026-10-26.md`. That review
rules out US day trading, so this trial is about the monthly book only.

**Family and bar.** This is the 12th trial in the slow cross-sectional
momentum family (trial 204 was the 11th). The bar is two-sided Bonferroni
at 5% across 12, so **t ≥ 2.865**. Once spent, the family's next bar is
2.891.

## Read this first: power and prior

- **Power.** Trial 126's monthly net excess had a standard deviation of
  about 3.89%. The US figure is unknown, so this uses India's. The window
  below has 335 months. At t ≥ 2.865, that window detects a true +0.61% a
  month half the time and +0.79% a month 80% of the time. If the US effect
  equals India's +0.71%, the expected t is 3.34. A 10-year source (97
  months) would give an expected t of 1.80 for the same effect. That is
  why the window is fixed long and **a source that can't cover it is not
  used**.
- **Prior.** Published work finds US momentum weaker after 2000 than
  before, especially among large stocks. The 2009 reversal is the largest
  crash on record. That literature counts as **partly seen**: it describes
  the factor, not this rule on this universe, but a pass or a fail is no
  surprise either way. The honest prior that this passes is low.
- **What a pass is worth.** It says the rule travels to a second market on
  stocks this project has never read. It doesn't say the book beats a US
  index fund after Indian tax (see "After tax" below).

## Rules: trial 126's, translated, not re-tuned

- **Universe at each month-end t:** US common stocks listed on the NYSE,
  NASDAQ or NYSE American. ETFs, funds, ADRs, preferreds, warrants, units
  and rights are excluded. Each chain needs ≥ 250 sessions of history, an
  **as-printed** close ≥ $5 on t, and a trade on t. Chains are ranked by
  median daily dollar volume over the trailing 126 sessions, with absent
  days counted as zero. **One share class per issuer**, the more traded
  one. **Trial: ranks 1–200. Confirmation: ranks 201–400.**
- **Signal:** mean(r6/σ, r12/σ). Returns run to month-end t−1 (skipping a
  month); σ is daily over 252 sessions.
- **Portfolio:** long only, 15 names, equal weight at entry, keep a name
  while its rank is ≤ 30, refill vacancies from the top. Fills are at the
  next session's close. Fractional shares, so no rounding.
- **Total return:** prices are split-adjusted and dividends are added as
  cash on the ex-date, for the strategy and the benchmark alike.
- **Delistings:** a held stock that stops trading is sold at its last
  close. If the source records no merger or acquisition for it, a further
  **−30%** is applied (Shumway 1997's average performance-delisting
  return). The count is reported.
- **Costs (Alpaca, self-directed, 2026):** commission $0; regulatory fees
  on sells at a flat **0.3 bp**; slippage **5 bp a side** in the trial and
  **10 bp a side** in the confirmation. Reported at 1×, 2× and 3×.
  Information column: IBKR Pro Tiered ($0.0035 a share, $0.35 minimum)
  at $12,000 of capital, where the minimum is about 4.6 bp an order.
- **Benchmark:** the same universe equal-weighted, rebalanced only for
  churn, same percentage costs.
- **Window, fixed now:** rebalances at month-ends **1998-01 → 2025-11**
  (335 months). Data is loaded from 1996-10. **No 2026 session is loaded**
  in a selection run. Halves: 1998-01 → 2011-12 and 2012-01 → 2025-11.
  Last three years: 2023-01 → 2025-11.

## Data source

The panel must be **survivorship-free by construction**: every listed
stock on every date, including those that later delisted, as with NSE's
bhavcopy here. The source has to provide: daily OHLCV for active and
delisted tickers back to 1996-10, splits, cash dividends, a permanent
security ID (FIGI, CIK or the vendor's own) so that renames don't break a
chain, and a security type so the exclusions above can be applied.

Candidates, none verified against these needs:

| Source | Price | History | Delisted |
| --- | --- | --- | --- |
| EODHD "Historian" | $19.99 a month | 30+ years | Not stated on the pricing page |
| Massive (Polygon) Advanced | $199 a month | "20+ years" (may not reach 1996) | Claimed on a landing page |
| Norgate US Stocks | Not checked | 1950 onward, delisted included | Windows only (could run on `sahab-pc-win`) |

Buying data is the owner's decision. The chosen source is recorded in a
dated amendment before the first download. Stage 0 then decides whether
it is good enough.

## Stage 0: data gate (no forward return is read)

1. **Coverage:** ≥ 240 sessions in every year from 1997 to 2025, a file
   within 3 sessions of every month-end, and ≥ 400 eligible chains at
   every month-end.
2. **Survivorship:** each of these must be in the panel, with its last
   exchange trade within 3 months of the date shown: Enron (2001-12),
   WorldCom (2002-07), Lehman Brothers (2008-09), Washington Mutual
   (2008-09), the old General Motors (2009-06), Sears Holdings (2018-10),
   Celgene (2019-11), Twitter (2022-10), SVB Financial (2023-03) and
   Bed Bath & Beyond (2023-04). **All 10 are required.**
3. **Continuity:** Facebook → Meta (2022-06), Kraft → Mondelez (2012-10)
   and Priceline → Booking (2018-02) must each be one chain.
4. **Split consistency:** for every split on a chain in the top 400 on
   its ex-date, the adjusted ex-date return lies within ±20%. Gate:
   **≥ 97%**, every failure listed.
5. **Residual phantoms:** one-day adjusted returns below −30% among
   top-400 chains with dollar volume above $50 M are listed, and each one
   is explained by news or a missing corporate action. Gate: **≤ 10
   unexplained.**

If stage 0 fails, the trial stops and the failure is reported. One
re-fetch for download failures is allowed. A loader defect found by stage 0
is fixed by a dated amendment before any return is read, as in 3i's
amendment 1. **The window is never shortened to fit a source.**

## Review before the run

An independent reviewer reads this file and the script and must approve
them before the run. Trial 204 ran without that step, and this one won't.

## Pass rule (trial 205): all six required

1. Monthly net excess over the benchmark: mean > 0 and **t ≥ 2.865**.
2. Deflated Sharpe ≥ 0.95 at **N = 12**
   (`evaluation.deflated_sharpe_ratio`), using the series' own skew and
   kurtosis.
3. Positive in **both halves**.
4. Positive over the **last three years**.
5. Net CAGR minus the benchmark's net CAGR ≥ 2.0 pp.
6. ≥ 100 round trips.

## Confirmation: ranks 201–400

Same rules and months, with 10 bp slippage. This is a confirmation of the
trial, not a competing configuration, so it doesn't raise N. **It
confirms if** the monthly net excess has mean > 0 with t ≥ 1.65 and is
positive in both halves. It is reported whatever the trial shows.

## After tax (information only, reported with the trial)

The trade list goes through a FIFO tax engine using the rules for an
Indian resident in FY 2026-27, applied to every year. Foreign shares are
taxed as unlisted: short-term gains (held < 24 months) at **31.2%** (the
30% slab plus 4% cess, no surcharge), long-term gains at 12.5%. Dividends
lose 25% to US withholding, credited against 31.2% in India. This is
compared with SPY bought at the start and sold at the end (long-term).
TCS is a timing cost, not a tax, and is left out. FX conversion happens
once, at funding, so it is left out of the comparison and noted.

## Falsification branches, written now

| Trial | Confirmation | Meaning | Action |
| --- | --- | --- | --- |
| fail | fail | The rule doesn't work on US stocks | Close the US line; no broker code |
| fail | pass | Interesting, but the trial's gate is the gate | FAIL; record the confirmation |
| pass | fail | Works only on the top 200 | No held-out look, no paper book |
| pass on economics, fails t or DSR | any | Fails the multiple-testing gate | FAIL, per the standing rule |
| pass | pass | Held-out sign check, 2026-01 → the last complete month | If the sign is positive: an Alpaca **paper** book beside the Indian one, with the same switch-off band shape |

Real money is a separate owner decision after paper trading, and only once
the after-tax figure beats SPY. The Indian book's go-live list (G1–G15)
comes first.

## Code boundary and order

The loader goes in `backend/research/us_prices.py` (data only) and stage 0,
the trial and the confirmation go in `backend/research/momentum_us.py`.
Both are committed after this file, and nothing on the live path imports
them. Order: this file → source amendment → loader and stage 0 → stage-0
run → review → one trial run, logged with `evaluation.log_trial` → results
in `results-us-momentum.md` and a row in `trials.md`. A crash before a
statistic is printed may be fixed and re-run, with both runs recorded.
