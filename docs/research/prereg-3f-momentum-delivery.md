# Pre-registration — 3f, 12-month momentum, held in delivery, one position at a time

**Written and committed before any 3f code exists.** Requested by the user on
2026-09-23 ("draft the phase-3 momentum prereg"), after a review of why the
session produced zero trades. The **portfolio rule** is the user's own, from
the same conversation: *"invest all money in one … and use the same on
another trade"* — one position, the whole account, rolled into the next pick.

**NOT RUN.** Two gates, both required, the same two-step as 3a, 3b and 3e:
**reviewer review of this pre-registration**, then **the user's explicit
go-ahead to run it**. Writing it is not the go-ahead.

**Numbering.** 3e (PR #77) is pre-registered and not run; it holds research
look **L35** and trial **38**. 3f therefore takes **the next free numbers at
the moment it runs** — expected **L36** (stage 1) and **trial 39** (stage 2),
or L35 / trial 38 if 3e is withdrawn first. The count is read from
`trials.md` at run time and stated in the results file.

**Nothing here recommends investing or trading real money.** It asks one
research question and fixes, in advance, what answer would count.

---

## Why this, and why now

Phase 2 closed with one binding constraint: **cost per unit of edge at the
holding period.** A cash-intraday round trip costs 16.60 bp against a typical
5-minute move smaller than that, and the intraday session itself drifts
**−6.42 bp** (index-level) against the trade. The only real effect it found —
volatile stocks earn **overnight** and give it back **intraday** — lives in the
part of the day an intraday book never holds (`report-phase-2-closing.md` §1,
§3). `phase3-scoping.md` then looked at every segment ₹5,500 can reach and
found no documented intraday effect that clears its cost.

What has **not** been tested is the opposite end: a **slow, documented**
signal, held in **delivery** so the overnight return is kept, where the round
trip is paid **once a month at most** instead of every session.

§52 (holding the scanner's picks 1–5 days) is **not** this test and does not
pre-empt it. §52 held the **scanner's ranking**, whose own daily IC measured
**−0.0021, t = −0.26** — it tested a signal with no predictive power. 3f tests
a different signal (past 12-month return), at a different horizon (a month),
that has independent published support.

### What the literature says, and how firmly it was checked

| Claim | Source | Checked how |
| --- | --- | --- |
| Buying past 3–12-month winners and selling losers earned significant returns over 3–12-month holds (US, 1965–1989) | Jegadeesh & Titman, *J. Finance* 48(1), 1993 | Abstract, via search, 2026-09-23 |
| Indian momentum factor, Oct 1993 onwards, survivorship-corrected, illiquid firms excluded: **21.9% a year** average, Jan 1994 – Dec 2014 | Agarwalla, Jacob & Varma, IIMA WP 2013-09-05 | Abstract/summary, via search. **Long-short, gross of costs** — not a long-only or net figure |
| Anomalies with **< 50% monthly turnover** usually survive trading costs; few above do. Mid-turnover monthly strategies pay **20–57 bp a month** | Novy-Marx & Velikov, *RFS* 29(1), 2016 | Abstract, via search |
| NSE runs **NIFTY200 Momentum 30**: 6- and 12-month returns, volatility-adjusted, 30 stocks, rebalanced **June and December**. **Launched 25 Aug 2020, base date 1 Apr 2005** | niftyindices.com | **Secondary sources only** (UTI, Angel One). The NSE factsheet and whitepaper **timed out twice** and were not read. Everything before Aug 2020 is NSE's back-calculation, not live history |
| The "skip the most recent month" convention (12-to-2-month window) | Standard in factor libraries (Carhart 1997; Fama–French UMD) | **Not re-verified this session** — stated as convention |

**No India-specific, long-only, net-of-cost effect size was found.** The one
Indian number with a size (21.9%) is a gross long-short factor return. 3f has
to measure the effect itself, which is what stage 1 is for.

---

## The user's portfolio rule, and why it is the design rather than a variant

At ₹5,500, Zerodha's DP charge — **₹15.34 per scrip, per sell, GST
included, "irrespective of quantity"** (zerodha.com/charges, read 2026-09-23)
— dominates everything else. Delivery round trip, published tariff (zero
brokerage, STT 0.1% each side, NSE 0.00307%, stamp 0.015% buy, GST on
SEBI + exchange), plus the modelled 3 bp/leg slippage:

| Positions | Size of each | Charges | + slippage | **Round trip** |
| --- | --- | --- | --- | --- |
| **1 (the user's rule)** | ₹5,500 | 50.1 bp | 6.0 bp | **56.1 bp** |
| 2 | ₹2,750 | 78.0 bp | 6.0 bp | 84.0 bp |
| 3 | ₹1,833 | 105.9 bp | 6.0 bp | 111.9 bp |
| 5 | ₹1,100 | 161.7 bp | 6.0 bp | 167.7 bp |
| 30 (the index's size) | ₹183 | 859.0 bp | 6.0 bp | **865.0 bp** |

Computed with `costs.leg_cost()` on `DELIVERY_COSTS` with the two published
figures substituted. **No market data was read to produce this table.**

**One position is the only structure this account can afford.** Replicating a
30-stock momentum index costs 865 bp per rotation. The user's rule is
therefore fixed as the stage-2 design, not tested against alternatives.

**Found while drafting, not fixed here:** `costs.DELIVERY_COSTS` carries
`dp_charge_per_sell = 15.93` and `exchange_txn_pct = 0.00297`; the published
figures are **15.34** and **0.00307** (the second is #79). The stale values
make the round trip **57.2 bp**, 1.1 bp too high — the safe direction. 3f uses
the published figures in its own research-only cost table and does **not**
edit `costs.py`.

### What the rule costs in evidence

The rule's weakness is statistical, and it is stated now rather than
discovered. A single stock's monthly excess return is far noisier than a
portfolio's. Using `splits.required_trades()` (two-sided 5%, 80% power) to
detect **+56.1 bp a month** — one round trip:

| Construction | Monthly sd of excess (**ASSUMED**, not measured) | Months needed |
| --- | --- | --- |
| Top quintile of ~100 stocks | 300 bp | 224 |
| Top quintile | 400 bp | 399 |
| **One stock (the user's rule)** | 900 bp | **2,020** |
| One stock | 1,200 bp | 3,591 |

The selection window below allows **at most 192 months**. So:

> **The one-position rule cannot be confirmed statistically on any history
> that exists.** At 900 bp sd and 192 months, its minimum detectable effect at
> t = 2 is **130 bp a month** — about 16% a year of excess return. Only the
> quintile measurement has a realistic chance of being testable
> (**MDE ≈ 43 bp** at 300 bp sd).

This is why stage 1 gates on the **quintile** and reports the one-position
rule as descriptive only.

---

## What was deliberately NOT included

Each of these is a variant that will **not** be run later, whatever 3f shows:

- Other formation windows (3, 6, 9 months), no skip month, or the raw
  (not volatility-adjusted) score.
- Other rebalance frequencies (weekly, quarterly, NSE's semi-annual).
- Two to five positions, sector caps, or a stop-loss.
- A market-regime filter (e.g. "only when NIFTY is above its 200-day average").
- A short leg. Overnight cash shorts are not possible in India, and futures are
  out of reach at ₹5,500 (`phase3-scoping.md` §1a).
- Another universe (NIFTY 200, NIFTY 500, mid-caps, universe B).

---

## Stage 0 — feasibility (no look, no trial)

Stage 0 reads **no forward return**. It builds the universe and checks the
data, and each step is a **halt, coded as a halt** — the lesson of §D4 in
step 2, where a gate coded as a report was judged after the ICs were seen.

### 0a — cost arithmetic — **done at drafting**

The table above. Nothing further.

### 0b — point-in-time membership — **HARD GATE**

**Survivorship bias is not a caveat for this signal; it is the most likely
source of a false positive.** Today's NIFTY 100 contains the stocks that rose
into it. A "buy last year's winners" sort run on today's members selects,
disproportionately, the stocks that went on to be included — by construction.
Every earlier phase-2 test carried survivorship as a stated caveat; a
winners-sort cannot.

Stage 0b must produce `backend/research/data/nifty100_membership.csv` —
`symbol, from, to, source` — from **NSE's published index-change
announcements** (niftyindices.com / NSE press releases on semi-annual
reviews and replacements), with symbol changes and mergers mapped.

> **3f proceeds only if** point-in-time membership is reconstructed for every
> month from its start date through Dec 2025, **and** adjusted daily closes
> exist for **≥ 95% of member-months** (delisted and merged names included).
> Otherwise **3f STOPS** — no look is spent, and it is not re-registered on
> today's membership "with survivorship noted".

The **start date** is fixed by rule, not chosen: **the later of 2010-01-01
and the first month with complete membership**, set in stage 0b before any
signal is computed.

### 0c — price data

- **Source: yfinance daily**, as in universe B. No Kite calls.
- **Returns use dividend- and split-adjusted closes.** The scanner's
  `download_batch` uses `auto_adjust=False` (unadjusted for dividends); 3f
  loads adjusted closes in its own research code and does not change the
  scanner. The **eligibility price test** uses the unadjusted close, since
  that is what a share actually costs.
- **Vendor check — HALT:** over the overlap with the Kite 5-min cache
  (2024-09-20 → 2025-12-31, no Kite calls), the correlation of daily
  close-to-close returns (yfinance vs the cache's last bar each session) must
  be **≥ 0.98 for ≥ 95% of stocks**. Otherwise stop and report.
- **Closing-price definition — to verify, not assumed:** entries and exits
  below happen at the session close. Before the 2026-08-03 closing auction,
  NSE's official close was, to this author's understanding, a weighted average
  of the last 30 minutes, which a trader can approximate. **Stage 0 must
  confirm that from an NSE source and cite it.** If it cannot, report it as an
  open caveat on tradability.

---

## Stage 1 — the measurement (research look, no trial)

### Hypothesis

Among point-in-time NIFTY 100 members, the stocks with the highest
volatility-adjusted 12-to-2-month return outperform the equal-weight universe
over the following month, by more than one delivery round trip at this
account's size.

### Construction

| | |
| --- | --- |
| Universe | **Point-in-time NIFTY 100** (stage 0b), per signal date |
| Eligible | Member on the signal date · ≥ 252 sessions of history with ≤ 5% missing · **unadjusted close ≤ ₹5,500** (one share must be affordable — applied at every stage, so stage 2 inherits the same universe) · ≥ 20 eligible stocks, else the month is skipped |
| Signal date | Close of the **last session** of month *m−1* |
| **Score** | `r / σ`, where `r` = adjusted close at *t−21* ÷ adjusted close at *t−252* − 1, and `σ` = sd of daily log returns over *t−252 … t−21*, × √252. Ties broken by symbol, alphabetical |
| **Holding return** | Adjusted **close of the first session of month m → close of the first session of month m+1**. One full session after the signal date: never the signal bar |
| Period | Holding months from the stage-0b start (≥ Jan 2010) **through Dec 2025** — the last one ends on the first session of Jan 2026, before `splits.HELD_OUT_START` (2026-01-02). **Nothing on or after 2026-01-02 is loaded past the loader** |
| Halves | Split at the median holding month, fixed now |

Holding periods do not overlap (one per month), so the per-month statistics
are tested with a plain t across months.

### What is reported, in this order

1. **Realised monthly sd of the quintile excess, and the MDE at t = 2 —
   before any mean is read.**
2. Quintile table: mean monthly return per score quintile.
3. **Gate statistic: top quintile minus the equal-weight eligible universe**,
   per month; mean and t across months.
4. Both halves, each with (3).
5. **Descriptive only — the user's rule on the same months:** the single
   top-scored eligible stock, net of 56.1 bp on each month it changes: mean
   monthly excess, sd, share of months it changes, worst month, maximum
   drawdown. **No pass rule. It cannot clear stage 1 and cannot justify a
   variant.**

### Stage-1 gate, fixed before running

> **Stage 1 clears only if the quintile excess (item 3) is positive, with
> t > 2, AND exceeds 56.1 bp a month, AND is positive in both halves.**
>
> The hurdle is one **K = 1 round trip per month** — the worst case, as if
> the single position changed every month. It is deliberately stricter than
> the trade it would authorise, which changes only when the top name changes.
>
> Anything else **withdraws 3f**. No trial is spent, and the design is **not**
> re-registered with another window, score, rebalance frequency or universe.

A positive excess below 56.1 bp is **a withdrawal, not a near miss**, and will
not be described as one.

**Untestable branch:** if the realised MDE (item 1) exceeds 56.1 bp, stage 1
is reported as **untestable on this history**, not as a null and not as
"promising".

---

## Stage 2 — the strategy (trial 39, only if stage 1 clears)

**A proposal to the reviewer, raised before any number exists:** the power
table above says the one-position rule **cannot produce a statistical PASS**
on any available history — its MDE is about 130 bp a month. A trial that can
only end "untestable" still adds to the Deflated Sharpe count and buys
nothing. **I propose stage 2 is not run as a trial,** and that stage 1's
descriptive report of the user's rule (item 5) is the full answer at this
capital. If the reviewer prefers the trial framing, stage 2 is fixed below and
runs as written.

| Parameter | Value |
| --- | --- |
| Signal, universe, eligibility, dates, halves | **Exactly as stage 1** |
| Product | **CNC delivery.** Long only |
| Position | **One stock, the whole account.** On each signal date, if the top-scored eligible stock is the one already held, **do nothing** (no cost). Otherwise sell the holding at the next session's close and buy the new one at the same close with the **entire proceeds**, in whole shares; the remainder stays in cash at 0% |
| Starting capital | **₹5,500** |
| Exit | Only by replacement. **No stop, no target** |
| Costs | Published tariff, as in the table: DP ₹15.34/sell, STT 0.1% each side, NSE 0.00307%, stamp 0.015% buy, GST, **3 bp/leg slippage** (modelled, never measured) |
| Confidence gate | Not applicable — this is not the checklist engine |

### What is reported

1. Months, number of changes, cost drag in bp per year.
2. **Monthly net excess over the equal-weight eligible universe**: mean, sd,
   t, 95% CI. **Primary statistic.** Gross alongside, so friction is visible.
3. Both halves, each with (2).
4. Net CAGR, worst month, maximum drawdown, longest drawdown in months.
5. The NIFTY 50 price index (`^NSEI`) over the same months, as context only —
   it excludes dividends, and it is cap-weighted.
6. MDE at t = 2 from the realised sd, before the mean.
7. Deflated Sharpe at the trial count at run time.

### Stage-2 pass rule

> **PASS only if** mean monthly net excess is **> 0 with t > 2**, **positive
> in both halves**, and **DSR ≥ 0.95**. Anything else is a **FAIL**. Positive
> gross with negative net is a FAIL.
>
> **Untestable branch:** if the realised MDE exceeds 56.1 bp, the result is
> **untestable**, not a null and not a pass. **This is the expected outcome**,
> stated in advance from the power table.

---

## Held-out — not proposed for 3f

The 2026 window (from 2026-01-02 to the cache freeze) holds about **eight
monthly observations**. At a 300 bp sd its MDE at t = 2 is about **210 bp a
month** — it cannot confirm anything a monthly strategy could show. It was
also already seen once on daily data by §52's swing backtest.

> **3f does not ask for the held-out window.** Spending the project's most
> valuable evidence on a test it cannot power would be a waste of it.
>
> On a stage-1 clear, the only confirmation that means anything is **forward
> tracking**: the rule computed each month from October 2026 onward, paper
> only, one observation a month. That is **years** of observations, not
> weeks. **Starting it needs the user's decision.**

---

## What 3f cannot establish

- **One variant is not a search.** See "deliberately NOT included".
- **Not a replication of NSE's index**, whose exact score definition was not
  read (the whitepaper timed out), and **not evidence about any fund**.
- **Taxes are not modelled.** A monthly rotation realises nearly every gain
  as short-term capital gain (20% under Section 111A since 23 July 2024 —
  **not re-verified this session**). A net-of-charges PASS would still be
  gross of tax.
- **Concentration risk is not a statistic.** With one stock and no stop, one
  bad month can take a large share of the account. Item 4 reports the
  realised worst case; it does not bound the future one.
- **Slippage is modelled at 3 bp per leg, never measured.** No real-money
  order has ever been placed.
- **Residual survivorship**: member-months with no price history (at most 5%,
  by stage 0b's gate) are dropped, and they are more likely to be failures.

---

## Code boundary

All 3f code lives in `backend/research/` (`step3f_momentum.py`, plus the
stage-0b membership builder). **No live module changes**: not the scanner,
not `costs.py`, not `config.py`. The AST fence test
(`tests/test_research_splits.py::test_no_live_module_imports_research`)
stands. The score, the holding-return window and the "do nothing if already
held" rule each get a unit test on synthetic prices before the run —
including one proving that no price on or after the holding month's first
session enters the score.

---

## Stop

**Stopped here for review.** No 3f code exists. Nothing runs — not even
stage 0b — without the reviewer's review of this file **and** the user's
explicit go-ahead.
