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
the moment it runs** — ~~expected **L36** (stage 1) and **trial 39** (stage 2),
or L35 / trial 38 if 3e is withdrawn first.~~ **SUPERSEDED by amendment 1
§D: two research looks and no trial** — expected **L36** (quintile gate) and
**L37** (the descriptive one-position report), or L35 / L36 if 3e is
withdrawn first. The count is read from
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
brokerage, STT 0.1% each side, NSE 0.00307%, stamp 0.015% buy, GST ~~on
SEBI + exchange~~ **on the exchange charge only, as `leg_cost()` computes
it — SEBI charges are outside the GST base in the code; amendment 1 §C.1**),
plus the modelled 3 bp/leg slippage:

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
  confirm that from an NSE source and cite it.** ~~If it cannot, report it as
  an open caveat on tradability.~~ **SUPERSEDED by amendment 1 §A: this is
  now a HARD HALT, structured like 0b.**

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
| **Holding return** | Adjusted **close of the first session of month m → close of the first session of month m+1**. One full session after the signal date: never the signal bar. **Tradable only under amendment 1 §A's hard halt; a picked stock with no exit close follows amendment 1 §B** |
| **Benchmark** | **Equal-weight mean of the holding returns of that month's eligible set** — the same set used for quintile assignment, with amendment 1 §B applied to every member, not only to picked names (amendment 1 §C.2) |
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
   variant.** **Amendment 1 §D: logged as its own research look, and every
   citation carries its power caveat inline.**

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

## ~~Stage 2 — the strategy (trial 39, only if stage 1 clears)~~ **WITHDRAWN by amendment 1 §D — no trial is spent. The mechanics table below is kept because stage 1 item 5 uses it.**

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
- **The ≤ ₹5,500 price filter selects on nominal share price** (amendment 1
  §C.3), which tracks sector and split history rather than size or
  liquidity. It is an uncorrected source of non-representativeness in every
  stage, separate from survivorship.

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

---

# Amendment 1 — Entry 14 (research-reviewer)

**Committed before any 3f code exists.** Entry 14 accepted the
pre-registration with corrections: §A and §B are design gaps that must close
before stage-0 code is written; §C is text; §D answers the outbox's three
questions. Each is resolved below, **the choice stated in the file rather
than decided in code**, and the superseded text is struck in place above,
not deleted.

## §A — the fill price: closing price kept, tradability made a HARD HALT

Entry 14 offered two options: **(a)** fill at the open of the session after
the signal, or **(b)** keep close-to-close and make stage 0c's
closing-price check a hard halt.

**Option (b) is adopted, because (a) breaks the same rule it is meant to
satisfy.** With **daily** bars, a session's open is the result of NSE's
**pre-open call auction** (09:00–09:08) — the **opening print**, which the
standing rule ("not the opening print, not the closing auction") bars in the
same sentence. 3b and 3e avoided both prints only because they priced on
**5-minute** bars (the 09:50 open, the open of the bar after the signal).
That cache starts **2024-09-20**; 3f's window starts in **2010**, so a
mid-session 5-minute price does not exist for most of the sample. Daily data
offers only the open and the close, and the open is the print the rule
names first.

**The close is different in the selection window, provided one fact holds.**
Every holding month in stage 1 ends on the first session of January 2026, so
**the whole sample predates the 2026-08-03 closing auction**. If NSE's
official closing price for equities in that period was a **weighted average
of trades over the last 30 minutes**, it is not a single print. A trader can
approximate it by executing through that half hour, and the 3 bp/leg
modelled slippage is the allowance for how far a real fill lands from that
average (**still unmeasured**).

> **HARD HALT — stage 0c.** 3f proceeds only if an **NSE primary source**
> (circular, FAQ or market-timings page, cited in the stage-0 output) confirms
> that the official closing price of cash-market equities was the weighted
> average of the last 30 minutes' trades **for the whole selection window**.
> The same source, or another NSE source, must confirm that the daily open
> is set by the pre-open call auction. This makes the reasoning above
> sourced, not assumed.
>
> **If either cannot be confirmed, 3f STOPS at stage 0.** No look is spent,
> exactly as for a failed membership reconstruction (0b). 3f is not
> re-registered with a different fill.

**Stated so it cannot be forgotten later:** the post-2026-08-03 regime
(closing auction for F&O stocks) does **not** apply to stage 1. It **would**
apply to any forward paper tracking (see "Held-out"). That tracking would
need its own fill rule, fixed before it starts.

## §B — a picked stock with no exit price

A rule that exists for selection but not for exit reintroduces survivorship
at the exit step, and it is biased toward exactly the names momentum picks.
Fixed now, for **every member of the eligible set** (quintile members, the
benchmark, and item 5's single position alike), whenever a stock has **no
adjusted close on its exit date**:

| Case | Realised holding return | Classification source |
| --- | --- | --- |
| **(i) Short gap**: missing for ≤ 5 sessions, trading resumes | Exit at the **first close after resumption** — the exit is delayed, not dropped | Price series |
| **(ii) Merger, amalgamation or scheme** — holders receive shares or cash | Return to the **last available adjusted close**, then **0% (cash)** for the rest of the month | NSE corporate announcement, recorded in the stage-0b membership file's `reason` column |
| **(iii) Suspension beyond 5 sessions, compulsory or involuntary delisting, insolvency** | **−100%** | Same |
| **(iv) Cannot be classified** | **Treated as (iii), −100%** | — |

- Case (iv) defaults to the punitive case on purpose: an unclassified
  disappearance must not be able to flatter the result.
- **Reported**: the count of each case, which quintile they fell in, and the
  gate statistic **with and without** cases (ii)–(iv). The **with** figure
  is the one that gates.
- **Item 5 (one position):** a case (iii) or (iv) takes the whole account to
  zero, and the series **ends there**. It is reported as a ruin event, not
  restarted with fresh capital.

## §C — text, no figure changes

1. **GST base.** The prose said GST is on "SEBI + exchange"; `leg_cost()`
   computes it on brokerage + exchange only. Corrected in place to match the
   code. Entry 14 recomputed the table from the code's formula and every
   figure stands (SEBI charges are ~150× smaller than the exchange charge).
   The code-versus-tariff difference is already tracked as **#79**.
2. **Benchmark.** Defined in the stage-1 table: the equal-weight mean of the
   holding returns of that month's eligible set, with §B applied.
3. **Nominal-price filter.** Added to "What 3f cannot establish".

## §D — the three outbox answers, adopted

1. **Point-in-time membership stays a hard stop.** Unchanged.
2. **Stage 2 is withdrawn before running. No trial is spent.** Two
   conditions from Entry 14, adopted:
   - **Item 5 is logged as its own research look** in `trials.md` (expected
     **L37**), separate from the quintile gate (**L36**). It computes a full
     return series for a specific tradeable configuration, and its audit
     trail should not rest on "no pass rule" alone. It uses the withdrawn
     stage-2 mechanics table exactly as written, with §B applied.
   - **Every citation of item 5**, in a results file, a progress update, a
     README section or a conversation, **carries the caveat inline**:
     *"MDE ≈ 130 bp a month; this cannot be distinguished from luck."*
3. **The held-out window is not requested.** Forward paper tracking stays
   the **user's decision**, and needs its own fill rule (§A).

## Unchanged

Everything else stands: universe, score, eligibility, dates, halves, the
stage-1 gate (quintile excess > 56.1 bp a month, t > 2, both halves), the
untestable branch, the survivorship hard stop and the code boundary.

**Stopped again for review**, as Entry 14 directs, before any stage-0 code is
written. Nothing runs without the reviewer's review of this amendment **and**
the user's explicit go-ahead.

---

# Amendment 2 — Entry 15 (research-reviewer)

**Committed before any 3f code exists and before any NSE source on the
closing price has been read.** Entry 15 accepted amendment 1 with one
correction: §A's hard halt had no rule for a closing-price method that
**changed partway through** 2010–2025. Fixed now, by rule, the same way
stage 0b fixes the membership start date.

> **Mid-window change — TRUNCATE, decided now.** If the NSE source shows the
> equity closing-price method changed within the selection window, the
> window **starts at the first month of the regime in force on the last
> selection session (Dec 2025)**. That holds **only if that regime is the
> last-30-minute weighted average**. The stage-1 start date becomes the
> **latest** of:
> 2010-01-01; the first month with complete point-in-time membership (0b);
> and the first full month of that regime.
>
> - If the regime in force at Dec 2025 is **not** a weighted average of the
>   last 30 minutes, **3f STOPS** (§A's halt, unchanged).
> - If the source dates the change only approximately, the regime is taken
>   to start at the **first month the source confirms without qualification**.
>   The window is never extended backwards on an inference.
> - Truncation is **mechanical**. It is applied whatever the shortened window
>   looks like, and it can only **shorten** the sample, never choose between
>   samples. If the shorter window pushes the realised MDE above 56.1 bp,
>   stage 1's **untestable branch** applies, exactly as written.

**Stage 0 still needs the user's explicit go-ahead to run.** Entry 15's
"stage 0b/0c can then be written and run" is read as *the reviewer has no
further objection*, not as authorisation. Neither stage reads a forward
return, and neither spends a look or a trial.

---

# Amendment 3 — Entry 16 (research-reviewer) — the 0c vendor check, re-specified after its HALT

**Committed after stage 0 ran and before any stage-1 code exists.** Stage 0
(`results-3f-stage0.md`) halted on the vendor check as written: 38 of 100
stocks reached a 0.98 daily-return correlation between yfinance and the Kite
5-minute cache's last bar. The diagnosis was that the comparator, not the
data, was wrong — the cache is dividend-adjusted and its last bar is a last
trade, not the official close. Entry 16 accepted that reading, **rejected
outright** re-running the same correlation against the NSE bhavcopy at a bar
chosen now (its result, 93.8%, is already known), and allowed a level test
only if its tolerance is derived from the study's economics rather than
from the number already seen.

**Disclosure, so nobody reads the gate below as fixed blind:** stage 0 §4.3
already reported that yfinance's Close is within **0.5%** of the NSE
bhavcopy close on **99.4%** of stock-days over 2024-09-20 → 2025-12-31. That
figure was seen before this amendment was written. The gate below uses a
tolerance eight times tighter, on a different set of prices (the signal-date
closes over the whole window, not daily closes over fifteen months), and its
outcome has **not** been computed at the time of writing.

> **0c vendor check — REPLACED.** The correlation test is withdrawn as
> mis-specified: a strategy that trades once a month at the close never
> touches day-to-day noise, so a daily-return correlation measures the
> wrong thing. In its place, a **level test on exactly the prices 3f uses**:
>
> - **Prices tested:** the yfinance unadjusted `Close` of every
>   point-in-time member on every **signal date** — the last session of
>   each month from **2009-01 to 2025-12** (2009 closes feed the first
>   12-month lookbacks) — against NSE's own **official close** for that
>   session, read from the daily bhavcopy (`cm<DDMMMYYYY>bhav.csv.zip`,
>   series EQ, column CLOSE), downloaded from `nsearchives.nseindia.com`.
> - **Tolerance: 6 bp** — the round trip of the **3 bp/leg slippage this
>   pre-registration already models** (0a table). A vendor error larger
>   than the friction we allow for would be a larger unknown than the
>   friction itself. The tolerance is not derived from any observed match
>   rate.
> - **Rule:** a signal-date close that differs from the official close by
>   more than 6 bp, or is absent from yfinance, is **missing** for that date
>   — amendment 1 §B's cases apply to it exactly as to a delisting. The
>   0b coverage gate is then re-applied to the **surviving** closes:
>   **3f proceeds only if ≥ 95% of member-months (2010-01 → 2025-12) have a
>   signal-date close that exists and matches within 6 bp.** Stage 0 found
>   95.17% exist; the match condition can only lower that, and if it falls
>   below 95% **3f STOPS**, by the same halt as 0b. There is no second
>   tolerance to fall back to.
> - **Reported alongside, not gated:** the match rate by year, every
>   mismatch beyond 6 bp with both prices, and the number of stock-months a
>   mismatch converts from "held" into a §B case.
>
> **What this does not verify:** the dividend and split factor that turns
> `Close` into `Adj Close`. The bhavcopy carries no adjusted series. Stage 1
> therefore reports each quintile's gross return **with and without the
> dividend adjustment** so that the adjustment's contribution is visible;
> a difference in sign between the two is reported as a caveat, not
> resolved.

**Two standing caveats travel with every later citation of stage 0 (Entry
16):** "0c CONFIRMED" rests on circulars at 2010, 2019, 2024 and 2025 with
identical wording — 2011–2018 is an inference, not a citation; "0b PASS"
carries a first-half concentration — 7.9% of 2010–17 member-months, all
failures or absorptions, have no price history. If stage 1's first half
fails while the second passes, that gap is reported as a candidate
explanation, and it is not grounds to backfill and rerun.

**Stage 1 is still not written.** If the level test clears, stage 1 (L36)
may be written and stops again for review before it runs — the first step
that reads a return.

---

# Amendment 4 — Entry 17 (research-reviewer) — the vendor gate, corrected once, as the last correction it gets

**Committed before its run; no stage-1 code exists.** Amendment 3's level
test **failed as written (53.98%)** because its text called yfinance's
`Close` "unadjusted"; that column is unadjusted for dividends but adjusted
for splits and bonuses, so the test counted months after a split
(`results-3f-stage0.md` §6). Entry 17 accepted the diagnosis and permits one
disclosed correction under five pre-commitments, **with no amendment 5: if
this run fails its own gate, or any pre-commitment below is skipped, 3f
halts at stage 0 permanently and is not re-registered with a fourth vendor
specification.**

**Disclosure (pre-commitment 1).** Before this amendment was written, a
diagnostic computed the signal-date-to-signal-date return, yfinance vs NSE
official close, at 6 bp, on the **17,045 stock-months** that were comparable
under amendment 3's extraction: **98.80% agreed**; the 205 that did not were
109 months containing a split or bonus and 96 others, a block of them on the
2015-11 signal date. That figure was seen. It was computed **before** the
alias fix and the split-month recovery below, on a subset that excluded
2,202 stock-months, so the number this amendment reports is not the same
number and has not been seen — though, the components being additive, it is
likely to clear. The reviewer knows this; it is written here so no later
reader mistakes the gate for one fixed blind.

> **0c vendor gate — corrected form.**
>
> - **Quantity compared:** the return from one signal date to the next
>   (the last NSE session of month t−1 to that of month t), yfinance `Close`
>   vs NSE's official close from the bhavcopy, for every point-in-time member
>   on the month-t signal date, 2010-01 → 2025-12. A stock-month **matches**
>   if |(1 + r_yfinance) / (1 + r_NSE) − 1| ≤ **6 bp**.
> - **Tolerance: 6 bp, unchanged from amendment 3** (pre-commitment 2) — the
>   round trip of the modelled 3 bp/leg slippage. Nothing here re-derives it.
> - **Split and bonus months (recovered from NSE's own data):** a month in
>   which the yfinance/NSE close ratio at t differs from that at t−1 by more
>   than 6 bp contains a corporate action. The ex-date is found by bisection
>   over that month's sessions, downloading NSE's daily bhavcopy for each
>   probe (the ratio is constant on either side of the ex-date). On the
>   ex-date NSE's `PREVCLOSE` is the exchange's own adjusted previous close,
>   so NSE's return for the month is `close(t) / close(ex) × close(ex) /
>   prevclose(ex) × close(ex−1) / close(t−1)`, entirely from NSE. A month
>   with more than one ratio step, or whose ex-date file cannot be
>   retrieved, is **unrecovered and counts as a mismatch**.
> - **Whole-cross-section bad signal date (pre-commitment 3), fixed now, not
>   fitted:** after split recovery, a signal date on which **more than 10% of
>   that date's comparable members, and at least 5 stocks, mismatch** is a
>   **faulted date**. Every close on a faulted date is missing for every
>   member: no positions are entered on it, and positions due to exit on it
>   exit at the next non-faulted signal date's close (amendment 1 §B's
>   short-gap case). The rule is applied over the whole 2009-01 → 2025-12 run;
>   whether it catches 2015-11 is **reported**, and if it does not, that is a
>   miss on record, not a reason to change 10% or 5.
> - **Symbol aliases (pre-commitment 4), by rule:** a bhavcopy row belongs
>   to a current symbol if its symbol is anywhere in that symbol's chain in
>   NSE's `symbolchange.csv` (followed transitively), **or** its ISIN (present
>   in bhavcopies from 2011) equals the symbol's ISIN in NSE's `EQUITY_L.csv`.
>   No hand entries. Disclosed: amendment 3's run stored only rows whose
>   symbol was already the current one, which is why its 2,202 "absent"
>   stock-months included names the bhavcopy carried under an earlier symbol;
>   the extraction is redone from the same downloaded files under this rule.
> - **Gate:** counting every member-month 2010-01 → 2025-12, **3f proceeds
>   only if ≥ 95% have a signal-date close that exists on both sides, is not
>   on a faulted date, and matches within 6 bp** (a recovered split month
>   that matches counts as a match). A member-month with no comparable
>   return — either close absent on either side, at t or t−1 — counts
>   against the gate. Below 95%, **3f STOPS, permanently.**
> - **Committed code (pre-commitment 5):** the extraction, the alias rule,
>   the bisection, the faulted-date rule and the gate are
>   `backend/research/step3f_stage0_checks.py` (`level_test_returns` and its
>   helpers); the reported number is reproducible from the repository and
>   the downloaded bhavcopies.
> - **Reported alongside, not gated:** match rate by year; the list of
>   faulted dates; the split months recovered and unrecovered; every
>   mismatch with both returns.

**What this still does not verify:** yfinance's dividend adjustment (`Adj
Close` / `Close`). Stage 1 reports each quintile's gross return with and
without it, as amendment 3 already requires.

**One run.** Stage 1 (L36) stops for review before it runs whichever way
this goes; a fail here is the closure of 3f, brought back for review as
such.
