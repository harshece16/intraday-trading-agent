# Pre-registration — 3h, slow momentum held in delivery, from NSE's own daily bhavcopies

**Date:** 2026-09-25. **Status:** pre-registered; **not run**. Stage 0 is a
data-coverage check with no forward return read. Stage 1 is **trial 118**,
one run. The held-out window is touched only under the rule in §Held-out.

**One sentence:** buy the 15 most liquid-universe stocks with the strongest
volatility-adjusted 6- and 12-month returns, hold them in delivery, re-check
once a month, and measure whether that beats holding the same universe
equal-weighted, **net of every delivery charge Zerodha publishes**.

---

## Why this, and why now

Every line of evidence this project has, plus a four-way literature sweep
done today (`literature-sweep-2026-09-25.md`), points the same way:

- **In-house:** 117 strategy trials at intraday horizons, zero passes;
  pre-friction expectancy ≈ 0 in all of them. The only replicated effect
  (volatile stocks earn overnight, lose intraday) lives in the part of the
  day an intraday book never holds. The intraday session drifts −6.4 bp/day.
- **Population studies:** SEBI (Jul 2024) 71% of cash-intraday individuals
  lose, 80% among those trading > 500 times a year; Barber–Odean (Taiwan)
  1.6% of day traders profitable in a typical year; Chague et al. (Brazil)
  97% of persistent day traders lose.
- **Cost studies:** Novy-Marx & Velikov (RFS 2016) — anomalies with < 50%
  one-sided monthly turnover mostly survive costs; the high-turnover panel
  nets −0.3 to −1.3%/month. Momentum at ~35%/month turnover nets
  +0.68%/month (t 2.45) in the US.
- **India:** Chui et al. (PBFJ 2023, BSE 2000–2021) find significant
  intermediate momentum, strongest in the most liquid tercile, gross. NSE
  runs a live index on the same idea (NIFTY200 Momentum 30, live since
  Aug 2020; 5-year 11.0% CAGR to Aug 2026 per its factsheet — not smooth,
  and I could not fetch the parent index's matching figure).
- **Open source:** the only cost-aware Indian repos with out-of-sample
  positives hold for months (dual momentum, turn-of-month); every intraday
  one lands on "friction took the edge".

**What has never been measured here** is exactly that horizon. 3f
(`prereg-3f-momentum-delivery.md`) was designed for it and **closed at
stage 0** on a vendor-agreement gate (yfinance vs bhavcopy, 93.41% < 95%),
without reading a single forward return. Entry 17 barred a fourth vendor
specification of 3f. **3h is not one:** it has **no vendor** and **no
membership reconstruction**. Every price comes from NSE's daily bhavcopy,
which lists every stock that traded that day, delisted names included, so
the universe is point-in-time by construction. That removes the two things
that closed 3f (a second vendor to agree with, and a membership file to
cover). It is the same economic hypothesis with a different, simpler
construction, and this paragraph exists so nobody mistakes it for a rescue:
**3f's stage 0 produced no number about momentum**, so there is nothing to
have been rescued from. The reviewer may still object; the objection and
the reply go in the results file.

The user directed a rewire of the whole process on 2026-09-25. This is the
only rewire the evidence supports, so it is tested first and alone.

---

## Capital, and who this is for

| Account | Delivery round trip at the position size | Verdict |
| --- | --- | --- |
| **₹5,500 real** (15 names → ₹367 each) | DP ₹18.10 per sell alone = **493 bp** | **Not executable as stocks.** If 3h passes, the ₹5,500 account's version of it is the NIFTY200 Momentum 30 ETF, not this book. Stated now so it isn't discovered later. |
| **₹1,00,000 paper** (15 names → ₹6,667 each) | **~59 bp** (§Costs) | The test is run at this size. |
| ₹3,00,000 (15 names → ₹20,000 each) | ~41 bp | Reported for information. |

---

## Data — stage 0 (no look)

**Source:** NSE daily bhavcopies, `nsearchives.nseindia.com`, both formats
(`cm<DDMMMYYYY>bhav.csv.zip` to 2024-07-05, `BhavCopy_NSE_CM_…` after),
**2009-01-01 → 2025-12-31**, EQ series only. Fields used: SYMBOL, CLOSE,
PREVCLOSE, TOTTRDVAL, ISIN (present from late 2011), TIMESTAMP.
Symbol changes: NSE's `symbolchange.csv` (as 3f stage 0 used). Nothing else.

**Identity:** a stock is a chain of symbols joined by `symbolchange.csv`;
ISIN is used to confirm joins where both files carry it. A chain that ends
(delisting, merger, unmapped rename) is **sold at its last available close**
on the first month-end after the end. Unmapped renames therefore bias
returns *down* (a forced exit); the count is reported.

**Corporate actions:** on any session where `PREVCLOSE(t) / CLOSE(t−1)`
differs from 1 by more than 5%, the ratio is an adjustment factor applied to
all earlier prices of that chain. 3f stage 0 found older files where
PREVCLOSE is *not* adjusted on a bonus ex-date; fallback: a daily return
below −33% whose reciprocal is within 1% of a ratio of integers ≤ 10 is
treated as an adjustment. Both counts are reported. **Dividends are not
added back** — the strategy's return is understated by roughly the
universe's dividend yield, which is conservative for a long-only test.

**Stage-0 gate (mechanical, one re-fetch allowed for download failures,
no other amendment):**

1. ≥ 240 session files per calendar year 2009–2025, and a file within
   3 sessions of every month-end.
2. At every month-end from 2010-01 on, ≥ 200 chains satisfy the liquidity
   rule below.

If either fails after the re-fetch, **3h stops and reports**. No stage 1.

---

## Stage 1 — the measurement, trial 118

### Universe (point-in-time, at each month-end *t*)

EQ-series chains with ≥ 250 sessions of history before *t*, close ≥ ₹20 at
*t*, ranked by **median daily TOTTRDVAL over the trailing 126 sessions**;
the **top 200** form the universe at *t*. No index membership is used.

### Signal (fixed; NSE's own construction, not fitted)

For each universe member at *t*:
- `r6` = close(month-end *t−1*) / close(month-end *t−7*) − 1 and
  `r12` = close(month-end *t−1*) / close(month-end *t−13*) − 1: six and
  twelve months of return, **each ending one month before *t*** (the
  standard skip-month). "Close at a month-end" means the chain's last close
  on or before that date.
- `σ` = standard deviation of daily close-to-close returns over the
  trailing 252 sessions to *t*.
- `score` = mean( r6/σ , r12/σ ).

### Portfolio

- **Long only, 15 names, equal weight** at entry, no re-weighting between
  rebalances. Fractional shares are allowed in the measurement; the number
  of picks whose price exceeds the per-name allocation (unbuyable as one
  share at ₹1,00,000) is reported.
- **Hysteresis (the Novy-Marx–Velikov cost mitigation):** a holding stays
  while its score rank is ≤ 30; it is sold when its rank exceeds 30 or it
  leaves the universe; each sale is replaced by the highest-ranked stock not
  already held. Initial portfolio: top 15.
- **Timing:** scores use closes to *t*; all trades fill at the **close of
  the next session** after *t*. Returns run close(*t*+1 session) to
  close(*t′*+1 session).
- Cash from a forced exit mid-month sits idle until the next rebalance.

### Costs (per leg, on the leg's value; Zerodha CNC, 2026 tariff)

| Item | Buy | Sell |
| --- | --- | --- |
| Brokerage | 0 | 0 |
| STT | 0.100% | 0.100% |
| Stamp | 0.015% | — |
| NSE transaction | 0.00307% | 0.00307% |
| SEBI | 0.0001% | 0.0001% |
| GST 18% on transaction + SEBI | ✓ | ✓ |
| DP charge | — | **₹15.34 + 18% GST = ₹18.10 per scrip per sell-day** |
| Slippage against the close | 0.05% | 0.05% |

At ₹6,667 per name: buy 16.9 bp, sell 15.4 bp + 27.2 bp DP → **~59 bp
round trip**. `costs.DELIVERY_COSTS` is the reference for the percentages;
the script prints its own table and the two are compared in the results.

### Benchmark

The **same 200-name universe, equal-weighted at entry, no re-weighting,
traded at the same fills**: names leaving the universe are sold, entrants
are bought with the proceeds split equally, so its turnover is universe
churn only. It is charged the percentage costs and slippage but **not the
per-scrip DP charge**, which on 200 positions of ₹500 would be a
3.6%-per-sale artefact of the benchmark's construction rather than a cost
of the idea; leaving it out makes the benchmark *stronger*, which is the
conservative direction for the strategy's test. This asks "is the *selection* worth anything", which is the question
the engine would be built for. Buy-and-hold of the universe at 2010-01 and
the NIFTY 200 level (if a clean series is available; otherwise omitted, not
substituted) are reported alongside for information.

### Sample and split

Selection sample **2010-01 month-end → 2025-12 month-end** (192 months).
Halves: **2010-01 → 2017-12** and **2018-01 → 2025-12**. Held-out is
2026-01 onward (`research/splits.py`, `HELD_OUT_START`).

### Reported, in this order

1. Stage-0 coverage table; corporate-action and rename counts.
2. Turnover per year (one-sided, % of book), total cost drag per year in bp.
3. Strategy vs benchmark: net CAGR, annualised volatility, Sharpe (0 risk
   free, stated), max drawdown, worst month, best month, months positive.
4. **Monthly net excess return** (strategy − benchmark): mean, sd, t
   (192 obs), and the same in each half.
5. Gross-of-cost versions of 3 and 4, so the cost share is visible.
6. Deflated Sharpe ratio of the strategy's monthly net excess series at
   **n_trials = 118** (`evaluation.deflated_sharpe_ratio`).
7. The ₹5,500 and ₹3,00,000 cost columns re-run (cost only; same trades).

### Pass rule (fixed before running)

All of:
- monthly net excess mean > 0 with **t > 2.0** over 192 months;
- net excess **positive in both halves** (mean of monthly excess);
- **net CAGR − benchmark net CAGR ≥ 2.0 percentage points** (economic
  size: roughly twice the strategy's own annual friction);
- **DSR ≥ 0.95** at 118 trials;
- ≥ 100 round trips in the sample (a formality here).

Anything less is a **FAIL**, recorded as trial 118 in `trials.md`. There is
no partial pass and no "promising".

### Falsification branches, written now

- Gross excess > 0 but net fails → the premium exists and friction eats it
  at this account size. Then the ETF is the honest instrument, and no engine
  work follows.
- Gross excess ≈ 0 → Indian momentum in liquid large-caps 2010–2025 is not
  there at this construction. That is a worse fact than cost, and it ends
  the slow-horizon line for equities at this project.
- Passes in one half only → **not** reinterpreted; FAIL.

---

## Held-out

**Only if stage 1 passes:** the same rules are run on 2026-01 → the last
complete month before the run (≈ 8 months). The user authorised spending the
held-out window on a configuration that passes selection (2026-09-24).
Eight months of a monthly strategy is **8 observations**; the confirmation
is a **sign check** (mean monthly net excess > 0) and is reported as weak
evidence, not as a second pass. It is spent once.

---

## What follows a pass, and what does not

A pass → a **positional book** in the engine, **paper mode only**, as
README §76 describes: CNC product, no square-off, a month-end rebalance
job, delivery costs in the cost model, positions carried across restarts.
Real money remains the user's separate decision, and at ₹5,500 the answer is
the ETF regardless.

A fail → no engine work. The result is written up and the slow-horizon
equity line closes.

---

## What 3h cannot establish

- Whether the premium persists after 2026. A backtest can't.
- Tax: STCG at 20% on holdings under 12 months applies to most exits here
  and is **not modelled**; it lowers every net figure for a taxable account.
- Dividend income (omitted; conservative).
- Anything about intraday. This is a different product.

---

## Code boundary

`backend/research/slow_momentum.py` (new). Read-only against
`backend/data/bhav_daily/` (gitignored). Imports nothing from the live path;
the live path imports nothing from it (`test_research_fence`). Data
download uses `step3f_stage0_checks.fetch_bhavcopy` and `bhav_aliases`.

## Commit order

This file is committed **before** any of the script exists. The results
file cites the prereg hash, the script hash and the run time, in that order.

## Stop

If stage 0 fails, or stage 1 fails, 3h stops. No amendment revises the
signal, the universe rule, the portfolio size, the hysteresis band, the
costs or the pass rule. A crash before any statistic is printed may be
fixed and re-run with both runs recorded.

---

# Amendment 1 — 2026-09-25, before stage 0 ran on the full data, no forward return read

The stage-0 crash test on the first 606 sessions counted **903**
PREVCLOSE-based adjustments across 1,557 chains — several times the rate of
real splits, bonuses and rights. Cause: the chain is EQ-series only, so a
stock's spell in the BE/BZ series (or a suspension) leaves a gap, and the
PREVCLOSE on its return refers to a close the chain never saw. A plain
ratio there is noise and would rescale the whole earlier history.

**Rule as amended:** across a gap of more than one session, the PREVCLOSE
ratio counts as an adjustment **only if it snaps to a clean p/q with
p, q ≤ 10 within 1%**; ratios that don't snap are skipped and counted
(`ca_gap_skipped`). With no gap the rule is unchanged. This touches data
hygiene only; the signal, universe, portfolio, costs and pass rule are as
written. Committed before stage 0 is run on the full download.

---

# Amendment 2 — 2026-09-25, AFTER run 1 was seen. Run 1 is VOID (trial 118); run 2 is trial 119

**Disclosure first.** Stage 1 was run once under amendment 1 (code
`18971d0`/`f55da3c`, output kept as
`data/slow_momentum_stage1_run1_void.json`). Its result was seen before this
amendment was written: **FAIL** on the pre-registered rule — net monthly
excess +0.61% (t = 1.99, rule t > 2.0), both halves positive, net CAGR gap
+6.9 pp, DSR 0.28 (rule ≥ 0.95). A post-hoc amendment after a near-miss is
the exact shape of a rescue, so the reader should hold what follows to a
higher standard, and the held-out check (which this amendment cannot touch)
is the arbiter if run 2 passes.

**Why run 1 is void rather than a fail.** Auditing the adjusted prices
after the run found phantom one-day drops of −90% to −95% on well-known
split dates in liquid names (TATASTEEL 2022-07-28, SBIN 2014-11-20,
NESTLEIND 2024-01-05, BAJFINANCE 2016-09-08, BEL 2017-03-16, BAJAJFINSV
2022-09-13, TITAN 2011-06-23, …). Two defects, both checkable without
reference to any result:

1. **NSE's bhavcopy PREVCLOSE is never adjusted for a split or bonus.**
   Read directly from the files: TATASTEEL 2022-07-28 close 100.35,
   PREVCLOSE 959.4; INFY bonus 2018-09-04 close 737.15, PREVCLOSE 1434.25;
   the same on every split/bonus date checked. The pre-registered primary
   rule (PREVCLOSE ratio) therefore catches **no** corporate action, and the
   fallback's 1% snap tolerance rejected every split day on which the stock
   also moved more than 1% (TATASTEEL moved +4.6% split-adjusted).
2. **What the PREVCLOSE rule did catch were missing sessions**: the
   weekday-only download skipped NSE's Saturday/Sunday special sessions
   (Budget Saturdays 2015-02-28, 2020-02-01, 2025-02-01; Muhurat Sundays;
   the 2012-03-03 special session). On the following Monday, PREVCLOSE is
   the weekend close, my chain's previous row is Friday, and the ratio was
   applied as a "corporate action", erasing the weekend session's move from
   every earlier price. 1,612 such contiguous mismatches; not one a real
   corporate action.

A phantom −90% on a held name costs the strategy ~6% of the book and the
200-name benchmark ~0.45%; several of the affected names (BAJFINANCE 2016,
BEL 2017, SBIN 2014) are plausible momentum holdings. **The likely direction
of the fix is therefore to raise the strategy relative to the benchmark.**
That is stated before run 2 so it cannot be claimed as a surprise.

**Rules as amended (data hygiene only; signal, universe, portfolio, costs
and the five-part pass rule are untouched):**

- **Weekend sessions are downloaded**; stage 0 reports contiguous PREVCLOSE
  mismatches (> 2%) as a missing-session count, and they are **not**
  adjustments.
- **Corporate action = price + quantity, never PREVCLOSE.** A one-day drop
  of ≥ 25% whose ratio close(t−1)/close(t) snaps within 10% to a standard
  factor {4/3, 3/2, 5/3, 2, 5/2, 3, 4, 5, 6, 8, 10, 20, 25, 50, 100}, **and**
  whose implied traded quantity (value ÷ close, median over 20 sessions
  either side) scales by the same factor within [0.5f, 2f] — share-count
  conservation — is adjusted by exactly 1/f; the day's residual move stays
  a return. YESBANK 2020-03-06 (−56%, quantity ratio 0.37f) is correctly
  left as a crash under this rule; it was wrongly erased by the 5-day-median
  variant tried during diagnosis, which is why the one-day ratio is used.
- **Factors 1.2 and 1.25 (1:5 and 1:4 bonuses) are not adjusted.** A −17%
  or −20% day is too often a real fall, and erasing real falls flatters the
  test. Those bonuses remain as phantom drops, which hurt a 15-name book
  more than a 200-name benchmark: conservative for the strategy.
- The excess series starts at the **first month-end with a signal
  (2010-02)**; in run 1 the strategy sat in cash for 2010-01 while the
  benchmark was invested.
- Turnover and cost drag are reported as % of the **average** book, not of
  starting capital (run 1's 544%/yr figure was inflated by growth).
- **DSR at n_trials = 119.** Run 1 is counted as trial 118 (void); run 2 is
  trial 119.
- The last rebalance is the **2025-11** month-end: the 2025-12 month-end's
  fill would be the first 2026 session, which is held-out data.

**Stop rule stands:** run 2 is the run of record; there is no amendment 3.
