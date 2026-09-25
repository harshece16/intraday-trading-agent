# 3h results — slow momentum held in delivery. **FAIL** on the pre-registered rule (DSR 0.24 < 0.95). Four of five gates pass. Held-out not spent.

**2026-09-25.** Pre-registration `prereg-3h-slow-momentum-delivery.md`
(`adb24af`, clarifications `2a6cbe7`), script
`backend/research/slow_momentum.py` (`18971d0`), amendment 1 (`f55da3c`,
before stage 0 on full data), **amendment 2 (`0b81a1e`, after run 1 was
seen — read it first)**, run 2 output `963b0b2`, replication R2 `6f55920`.
Runs: run 1 at 21:20:45 (**void, trial 118**), run 2 at 21:39:49
(**trial 119, of record**), R2 at ~21:50 (identical statistics, not
counted). Data: 4,215 NSE bhavcopy sessions 2009-01-01 → 2025-12-31,
including 21 weekend special sessions; 3,205 symbol chains.

## The verdict, in the pre-registration's own terms

| Gate (fixed before running) | Result | |
| --- | --- | --- |
| Net monthly excess over the equal-weighted universe: mean > 0, **t > 2.0** (189 months) | **+0.72%/month, t = 2.48** | pass |
| Positive in **both halves** | 2010-02→2017-12 **+0.58%/mo** (t 1.33); 2018-01→2025-11 **+0.86%/mo** (t 2.22) | pass |
| Net CAGR − benchmark net CAGR **≥ 2.0 pp** | **18.4% vs 9.6% = +8.8 pp** | pass |
| **DSR ≥ 0.95** at n_trials = 119 | **0.24** (monthly excess Sharpe 0.18; luck baseline for 119 tries 0.23) | **FAIL** |
| ≥ 100 round trips | 523 | pass |

**All five were required. 3h FAILS.** There is no partial pass; the prereg
said so. **The held-out window (2026) is not opened.** Under the prereg's
own consequence clause, **no engine work follows**, and the slow-horizon
equity line closes for this project unless the reviewer reopens it.

## What the numbers say, plainly

This is the first strategy in 119 trials whose **net** excess return is
positive in both halves with t above 2. Every intraday trial before it had
a pre-friction expectancy of about zero; this one has a gross excess of
+0.79%/month (t 2.72) and loses only 0.07%/month to costs, because it pays
a delivery round trip on about 2.8 names a month, not on every bar. That is
the horizon effect the literature sweep predicted (`literature-sweep-2026-09-25.md`),
and the size — +0.7%/month net at ~35%/month one-sided turnover — is almost
exactly Novy-Marx & Velikov's US figure for momentum at that turnover
(+0.68%/month). Nothing here contradicts the literature; it matches it.

**Why it still fails.** The Deflated Sharpe Ratio asks: across 119
attempted configurations, is a monthly excess Sharpe of 0.18 distinguishable
from the best of 119 lucky nulls? At 189 observations it is not. To clear
DSR 0.95 at this trial count the excess would have needed a monthly Sharpe
near 0.35 — an **annualised excess Sharpe of about 1.2 against its own
universe**. No published long-only factor return delivers that; momentum's
documented long-only excess Sharpe is 0.5–0.7, and this strategy's is 0.62.
So the gate, applied at the project's full trial count, is asking a monthly
factor tilt to look like a statistical-arbitrage book. **It was
pre-registered that way, by me, and it stands.** I record the arithmetic so
the reviewer can decide whether the gate design, rather than the strategy,
is what failed — that is the reviewer's call, not the author's.

## Full statistics (₹1,00,000, 2010-02 → 2025-11, 189 months)

| | Strategy net | Strategy gross | EW universe (benchmark) | Buy & hold universe of 2010-02 |
| --- | --- | --- | --- | --- |
| CAGR | **18.4%** | 19.5% | 9.6% | 8.8% |
| Annualised vol | 22.8% | 22.8% | 18.6% | 18.3% |
| Sharpe (rf 0) | 0.81 | 0.86 | 0.52 | 0.48 |
| Max drawdown | −34.6% | −34.1% | −39.6% | −40.6% |
| Worst month | −23.4% | −23.3% | −25.6% | −24.3% |
| Months positive | 121/189 | 122/189 | 116/189 | 112/189 |
| ₹1,00,000 became | **₹14.35 L** | | ₹4.25 L | ₹3.75 L |

Costs: ₹58,744 over 15.8 years = **0.81% of the average book per year**;
one-sided turnover 211% of the average book per year (about 2.8 of 15 names
replaced per month, max 7). 538 buys, 523 sells, 3 forced exits
(delistings), 6 picks priced above the ₹6,667 allocation (fractional shares
assumed; would have been skipped live).

**Year by year, net excess over the benchmark (sum of monthly excess):**
2010 −2.2 · 2011 +26.7 · 2012 0.0 · 2013 −7.7 · 2014 +27.5 · 2015 +13.8 ·
2016 −13.3 · 2017 +9.7 · 2018 +11.0 · 2019 +1.3 · 2020 +6.0 · 2021 +36.9 ·
2022 +11.2 · 2023 +12.9 · 2024 +9.7 · 2025 −7.1 (to November). Eleven of
sixteen years positive; the worst months for the tilt were 2010-12,
2012-01, 2014-03 and 2023-01 (−10 to −13% each) — the reversals that
momentum is known for.

**Capital columns (same picks, only the DP charge's share changes):**

| Account | Net CAGR | Costs paid | Net excess/month | t |
| --- | --- | --- | --- | --- |
| **₹5,500** (₹367 per name; DP ₹18.10 per sell) | **9.6%** — equal to the benchmark | ₹10,484 | +0.07% | 0.25 |
| ₹1,00,000 | 18.4% | ₹58,744 | +0.72% | 2.48 |
| ₹3,00,000 | 18.6% | ₹1,60,881 | +0.74% | 2.53 |

At the real account size the entire excess is eaten by the per-scrip DP
charge — **as the prereg said before running**. The executable form of this
idea at ₹5,500 is an ETF, not a stock book.

## Disclosures — read these before the table above

1. **Run 1 was void and its result was seen.** Amendment 2 records it:
   run 1 (trial 118) gave t 1.99, DSR 0.28, both halves positive, +6.9 pp —
   a FAIL — before phantom −90% split days were found in the data. The
   amendment was written with that knowledge and stated the expected
   direction of the fix (up for the strategy). The fix raised t from 1.99
   to 2.48 and the CAGR gap from 6.9 to 8.8 pp. **It did not, and could not,
   move the DSR gate**, which is where the trial fails either way. Both
   outputs are committed (`data/slow_momentum_stage1_run1_void.json`,
   `data/slow_momentum_stage1.json`).
2. **Remaining phantom drops, all against the strategy.** The amended
   detector still misses splits where the volume regime changed around the
   ex-date. Of 64 one-day drops beyond 30% left on liquid days, **4 fell on
   names the strategy held**: LAURUSLABS 2020-09-29 (−80%, a 1:5 split),
   BSE 2022-03-21 (−67%, a 2:1 bonus), VAKRANGEE 2017-12-21 (−48%, a 1:1
   bonus), NBCC 2024-10-07 (−31%, a 1:2 bonus). Each cost the book roughly
   its 1/15 share times the drop: about −5.3%, −4.4%, −3.2% and −2.1% in
   those months, so the strategy's CAGR is **understated by about 1 pp**.
   The 200-name benchmark carries all 64 phantoms at 1/200 each, which
   understates it by a similar order. The excess is roughly unbiased; the
   verdict is unaffected. Filed as **#130** with the fix (an NSE
   corporate-actions file); not done here because the stop rule forbids a
   third amendment.
3. **ETFs got in.** The prereg's universe rule ("EQ-series chains") did
   not exclude exchange-traded funds, which trade in the EQ series. A
   vol-scaled score is gamed by low-volatility instruments: **LIQUIDCASE**
   (a liquid-fund ETF, return ~6.5%/yr at near-zero vol) held 7 months in
   2025; **GOLDBEES** 29 months (2010–12, 2019, 2025); SILVERBEES 2. About
   **1.5% of the 2,850 holding-months**. Direction: the metals ETFs helped
   in 2025 and 2011, the liquid ETF cost a slot in 2025. Not re-run (stop
   rule); the fix is in #130 (exclude ISINs beginning `INF`).
4. **Dividends omitted, STCG tax not modelled.** Both true for strategy and
   benchmark; dividends favour the benchmark slightly (momentum names yield
   less); STCG at 20% on sub-12-month holdings would take a material slice
   of the strategy's net.
5. **The sample ends 2025-11.** The 2025-12 month-end's fill would be the
   first 2026 session, which is held-out.
6. **82 contiguous PREVCLOSE mismatches remain** after adding weekend
   sessions (down from 1,612). They indicate sessions still missing (241
   weekday dates returned no file; most are holidays). Not adjustments.
7. **Fractional shares.** Six picks were priced above the per-name
   allocation at ₹1,00,000; a live book would have skipped them.

## Falsification branches, as written in advance

- "Gross excess > 0 but net fails" — **not this case**; net passes t.
- "Gross ≈ 0" — **not this case**; gross +0.79%/mo, t 2.72.
- "Passes in one half only" — **not this case**; both positive.
- The case that occurred — passes every economic gate and fails the
  multiple-testing gate — **was not written down as a branch.** That is a
  gap in the pre-registration, recorded here rather than papered over.

## What follows

- **No engine work.** The prereg bound a fail to that, and the autonomous-
  mode rule (`feedback_trader_sahab_autonomous_mode`) says a raw positive
  that fails a gate is not wired in. Nothing is built.
- **The held-out window stays unspent.** It remains the one clean sample
  the project has.
- **For the reviewer:** three questions worth a ruling — (a) whether DSR at
  the *project-wide* trial count is the right gate for a hypothesis family
  the other 117 trials never touched; (b) whether a corrected data pipeline
  (#130) plus an equities-only universe warrants a *new* pre-registration
  (3i) with the held-out check as the decisive test; (c) whether, at the
  real account's size, any of this matters, given that the ETF exists.
  None of those is decided here.
- **For the owner:** the measured fact is that a slow, liquid, long-only
  momentum tilt earned about +0.7%/month over its own universe net of
  costs for sixteen years, matching the published literature, and that this
  project's gate — built to catch 119 tries at curve-fitting — does not
  certify it as more than luck. At ₹5,500 it cannot be run as stocks at all.
  What to do with that is an investment decision, not this agent's.

## Reproducibility

```
cd backend && .venv/bin/python research/slow_momentum.py stage0 --refresh
cd backend && .venv/bin/python research/slow_momentum.py stage1
```
Inputs: `backend/data/bhav_daily/*.zip` (4,215 files, 315 MB, re-downloadable
with `step3f_stage0_checks.fetch_bhavcopy` over every calendar day 2009-01-01
→ 2025-12-31), `symbolchange.csv`, `EQUITY_L.csv` (NSE archives, fetched
2026-09-25). Outputs in `docs/research/data/slow_momentum_*.json`.
