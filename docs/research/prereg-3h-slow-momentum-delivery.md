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
