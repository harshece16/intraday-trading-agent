# Pre-registration — post-earnings drift in delivery, Stage A (research look L39, no trial)

**Written 2026-09-26, before any PEAD code or data build exists.** Step 3 of
the plan the owner approved ("go go go") after the move to delivery. The
design is the edge-map's PEAD design with **every fix its two adversarial
reviewers required** (edge-map workflow `wf_9c71500e-bc1`). This is a
measurement with a go/no-go rule: **no trial is spent**, and a failure
closes PEAD for this project.

## Hypothesis

NIFTY 100 stocks whose filed quarterly profit rose most against the same
quarter a year earlier, scaled by market value, keep outperforming the
NIFTY 100 for about three months after the result becomes public — the
post-earnings-announcement drift, measured from the first session *after*
the announcement (day +2 onward, not the gap, which L36 already showed is
priced by the open).

## Data

- **Universe:** point-in-time NIFTY 100
  (`backend/research/data/nifty100_membership_monthly.csv`; 167 symbols
  since 2018). An event counts if its stock is a member in the month of its
  entry session. Today's list is never used.
- **Filings:** NSE's quarterly results index per symbol
  (`api/corporates-financial-results`) and, for periods from 2025 on, NSE's
  integrated-filing results (`api/integrated-filing-results`). XBRL era only
  (mid-2018 onward). Pre-2018 HTML-era filings are **not read** in Stage A;
  they are reserved as Stage B's untouched sample.
- **Prices:** `research/nse_prices.py` (corporate-action and dividend
  adjusted), selection sessions only.

## Event construction (the reviewers' fixes)

1. **Basis.** For company-quarter q, use consolidated numbers if a
   consolidated filing exists for both q and q−4 (the same quarter a year
   earlier); otherwise standalone for both; otherwise no event.
2. **Event time = the broadcast of the exact filing whose numbers are
   used**, taking the earliest broadcast of that basis for q ("as first
   filed"). q−4 is taken as first filed too.
3. **Dating defect filter.** If that broadcast is two or more calendar days
   after the date stamped in the filing's own XBRL filename, the event is
   **dropped** and counted (2018–2020 broadcasts lag by weeks in hundreds of
   filings). The filename's time of day is never used.
4. **Profit:** `ProfitLossForPeriod` in the `OneD` context (as L36).
5. **Shares:** `PaidUpValueOfEquityShareCapital / FaceValueOfEquityShareCapital`
   from the same filing. Fallback: profit ÷ basic EPS only if |EPS| ≥ ₹1;
   else the previous quarter's share count; else the event is dropped and
   counted.
6. **Surprise:** SUE_M = (PAT_q − PAT_q−4) / (shares_q × as-printed close six
   sessions before the broadcast). Price and share count are both on the
   filing-date basis.
7. **Top tercile, known at the event:** the 67th percentile of **all
   earlier events' SUE_M** (expanding window), with at least 150 earlier
   events; events before that are warm-up and not traded.

## Portfolio and statistic

- **Entry:** the official close of the first session after the broadcast's
  calendar date (after-hours and weekend broadcasts: the next session; an
  in-hours broadcast: the next session too, so day 0 is always skipped).
- **Hold 60 sessions**, exit at the close. 30 equal slots; a new event when
  all slots are full is skipped and counted; a re-qualifying event on a held
  stock resets its clock without a round trip.
- **Sample:** events whose 60th session is on or before **2025-12-31**; the
  Q2-FY26 season that would exit in 2026 is excluded (held-out untouched).
- **Benchmark:** the equal-weighted point-in-time NIFTY 100, daily,
  total-return prices.
- **Statistic:** the book's **gross** monthly excess over the benchmark
  (daily book return = mean of active positions; months with no active
  position are skipped), with a **Newey–West (3 lags) t**.

## Go / no-go (fixed now)

**GO to Stage B only if the gross mean monthly excess is ≥ +0.37% and the
Newey–West t ≥ 1.8.** Otherwise **PEAD is dropped**: no second signal,
window, universe or holding period will be tried.

Reported whatever the answer: net at ₹10 L (Zerodha CNC costs, DP ₹15.34,
0.05% slippage per side), both halves (split at the median month), per-year
excess, the number of events kept and dropped at each step, and the
correlation of the monthly excess with 3i Part A's (is it a second,
different source of return?).

## Data gate before any return is read

1. At least **60%** of point-in-time member-quarters from 2019-Q2 to
   2025-Q2 produce a usable SUE_M. Below that, stop and report.
2. Share-count consistency: shares_q vs shares_q−4 within ±5% unless a
   split, bonus or rights issue lies between them; the share of events
   failing this is reported (not a gate).

## Stage B, only on GO (written now, pre-registered in detail later)

A trial under the family-level bar (family "earnings drift": this look plus
Stage B → N_family = 2, two-sided Bonferroni t ≥ 2.24, plus the standing
safeguards), on the **2010–2018 HTML-era events**, which Stage A does not
read. If Stage B cannot be powered on that sample, it is declared dropped
rather than run.

## Code and order

`backend/research/pead_events.py` (fetch and build the event table — data
only, no returns) and `backend/research/pead_stage_a.py` (data gate,
statistic), each committed before it runs. One run of the statistic.
