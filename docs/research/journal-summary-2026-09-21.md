# Journal summary — 2026-09-21

**Reviewer Entry 5 §A.** Read-only: the journal was opened with SQLite's
`mode=ro` URI, nothing was written, migrated or vacuumed, and the running
backend was not touched. No gate, threshold or config was changed.
Reproduce with `python backend/research/journal_summary.py`.

**Source:** `backend/data/sahab_journal.db`, 198 MB, sessions
**2026-09-15 → 2026-09-21**.

**The journal is being written to as this is read.** The engine is running
and the market is open, so side-evaluation counts moved between queries
(82,448 → 82,548 in a few minutes). Every count here is a snapshot of a
moving target, accurate to within a few hundred rows, and the pass *rates*
are stable.

---

## 1. Mode — no real money has ever been at risk

> **All 16 trade legs in the journal are `mode = 'paper'`. Zero real Kite
> orders have been placed, ever. The engine is in paper mode right now.**

**How I determined it.** Two independent checks:

- **Per trade:** `trades.mode` is written at fill time, one row per leg.
  `SELECT mode, COUNT(*) FROM trades GROUP BY mode` returns exactly one
  group: `{'paper': 16}`.
- **Right now:** `/api/state` on the running backend reports
  `paper_mode: true`, `running: true`, 0 open positions, ₹0 realised today.

**There is no separate list of real-money orders, because there are none.**
`fno_trades` is empty too (0 rows).

A note on wording, since it matters: these eight round trips are often called
"live trades". They were taken by the **live running engine**, on real market
data, in **paper mode** — simulated fills, no broker order, no money. Both
halves of that are true and they are easy to conflate.

---

## 2. Closed round trips — 8 of them, and costs are ~all of the loss

| | |
| --- | --- |
| Trade legs | 16 |
| **Closed round trips** | **8** |
| **Net P&L** | **−₹168.71** |
| Gross P&L (before charges) | **−₹5.26** |
| Charges (all 16 legs) | **₹163.45** |
| Mean R | **−0.9912R** |
| Win rate | **25.0%** (2 of 8) |
| Exits | 6 `stop_loss`, 2 `take_profit` |

> **Gross was −₹5.26 across eight round trips — ₹0.66 per trade, which is
> nothing. Charges were ₹163.45. Costs are 97% of the entire loss.**

This is the live-sample version of exactly what the 495-session backtest
found: the entry has no edge in either direction, and friction converts a
fair game into a loss. Eight trades is far too few to prove anything on its
own — but it agrees with the large sample, which is worth noting.

### By day

| Session | Trades | Net | Gross | Mean R | Symbols |
| --- | --- | --- | --- | --- | --- |
| 2026-09-15 | 1 | −₹50.67 | −₹30.00 | −1.842 | BEL |
| 2026-09-16 | 4 | −₹232.44 | −₹152.95 | −1.111 | ENRIN, BPCL, TMPV, TCS |
| 2026-09-17 | 3 | **+₹114.40** | +₹177.69 | −0.548 | MAZDOCK, DIVISLAB, INDHOTEL |
| 2026-09-18 | 0 | — | — | — | — |
| 2026-09-21 | 0 | — | — | — | — |

**Nothing has traded since 17 September.** Two sessions have run since with
zero orders placed.

---

## 3. The funnel — which gate removes what

Every checklist evaluation is scored for **both** a long and a short side, so
82,448 side-evaluations come from 41,224 rows.

### All time

| Stage | Count | Pass rate |
| --- | --- | --- |
| Side-evaluations | **82,448** | — |
| passed `dow` (day-of-week) | 55,088 | 66.8% |
| passed `volume` | 17,554 | 21.3% |
| passed `pattern` | 8,705 | 10.6% |
| passed `sr` (support/resistance) | 6,087 | 7.4% |
| passed `rrr` (reward:risk) | 2,872 | 3.5% |
| **passed `cost` (stop vs cost)** | **220** | **0.27%** |
| **All required items passed** | **92** | **0.11%** |
| ...and cleared the **checklist entry threshold** | **51** | 0.06% |

> **CORRECTION, 2026-09-21.** This row was originally labelled *"cleared the
> confidence gate"*. **That was wrong.** It counts
> `bull_score >= entry_threshold`, which is the **checklist's own entry
> threshold**, not the confidence gate. The confidence gate is a separate,
> later check — `confidence.score_trade()` against
> `min_confidence_to_trade = 60` — and it does not appear in
> `checklist_evals` at all. The real record of it is the `blocked` rows in
> the `activity` table. See the new section **§3b**.
| Signals recorded | 45 | — |
| **Orders placed** | **8** | **0.0097%** |

### Which gate is really binding

Two different questions, two different answers:

- **Scarcest pass rate: `cost`.** But it is only *assessed* when a setup has
  a stop to assess — **2,950 of 82,548 side-evaluations (3.6%)**, verified
  directly rather than inferred. Of those it passes **220, or 7.5%**. The
  other five items are required on 100% of side-evaluations.
- **Most common sole blocker: `rrr`**, the single failing item in **857**
  near-misses, against 771 for `volume` and 79 for `dow`. `cost` is the sole
  blocker **zero** times — it never fails alone, always alongside something
  else.

**And the R:R distribution says why.** Across 8,770 setups with a computed
figure: **median 0.050**, p90 1.94, max 15.42.

> **The median setup offers a reward-to-risk of 0.05 after costs.** Not 0.5 —
> 0.05. That is not a gate being too strict; it is a setup population with
> almost nothing worth trading in it, because friction of ~0.40R eats a
> 42 bp stop before the market moves.

### Last five sessions

| Session | Side-evals | Passed checklist | Cleared **entry threshold** (not confidence — see §3b) | Top blockers |
| --- | --- | --- | --- | --- |
| 2026-09-15 | 23,984 | 20 | 14 | rrr, sr, pattern |
| 2026-09-16 | 28,240 | 47 | 17 | rrr, sr, pattern |
| 2026-09-17 | 10,724 | 16 | 11 | rrr, sr, pattern |
| 2026-09-18 | 18,550 | 9 | 9 | rrr, sr, pattern |
| 2026-09-21 | 950 | **0** | **0** | rrr, pattern, sr |

`rrr` is the top blocker on every single session.

---

## 3b. What actually blocks a trade after the checklist — the `blocked` log

**Added 2026-09-21**, after the §3 correction above. The post-checklist gate
is not visible in `checklist_evals`; it is the `activity` table's `blocked`
rows. There are **52 of them in the whole journal**.

| Reason | Count |
| --- | --- |
| **Confidence gate** (`confidence N/100 below the 60 bar`) | **21** |
| **Direction conflict** — *"scanner favours SHORT/LONG for this name"* | **19** |
| Test-harness artefacts (`TESTCO`, untracked Kite position) | 7 |
| F&O premium × lot too large for the capital | 2 |
| Already at the max of 1 open position | 1 |
| Other | 2 |

### Distinct setups, not evaluation rows

| Day | Distinct (symbol, side) clearing the checklist | Blocked rows |
| --- | --- | --- |
| 2026-09-13 | 0 | 4 |
| 2026-09-15 | 8 | 21 |
| 2026-09-16 | 19 | 18 |
| 2026-09-17 | 10 | 8 |
| **2026-09-18** | **1** | **1** |

Far smaller than the row counts in §3 suggest, and the right denominator for
any statement about how often a real opportunity appears.

### The finding nobody was looking for

> **19 of 52 blocks — almost as many as the confidence gate — are the two
> halves of the system disagreeing about direction.** The checklist fires
> long while the scanner ranks that name short, or the reverse.

Neither the original funnel nor any phase-2 measurement surfaced this. It is
recorded here as an observation, **not** a proposal: phase 2 established that
the entry has no edge in either direction, so making the two halves agree
would change which losing trades get taken, not whether they lose.

### Two further things the 09-18 trail exposed

- **76 `Kite session has expired` errors** — that session ran entirely on
  delayed yfinance data. This is the defect later fixed as #24/#51.
- **One watchdog fire:** *"The engine has been stuck on one cycle for 26 min,
  so stops and entries aren't being checked."*

---

## 4. Plain language — why so few trades, and what loosening would do

**Why the trade count is low.** Six required checks are applied to every
candidate, and they compound. Two-thirds survive the day-of-week filter, a
fifth the volume test, a tenth the pattern test, and so on — and then the
reward-to-risk test rejects 96.5% of what is left. Multiply them and 82,448
side-evaluations become 92 complete passes and 8 orders.

**But the observed rate does not match the backtest, and I cannot explain the
gap.** The journal shows **8 orders across 5 sessions — 1.6 per session** —
while the gated 495-session backtest produced 75 trades, or **0.15 per
session**. That is a **10× discrepancy**, and it is not resolved by anything
in this data. Candidates, none verified: the live sessions ran before the
19 Sep R:R and stop-floor fixes landed (#42/#44), the live config may differ
from the backtest config, or five sessions is simply too few to compare. It
is flagged here rather than smoothed over, because the funnel above is only
trustworthy to the extent this is understood.

Note also that **all 8 trades fell on 15–17 September and none since**.

> **RESOLVED, 2026-09-21 — and the original framing was wrong.** This
> paragraph said 2026-09-18 *"recorded 9 complete checklist passes that
> cleared the confidence gate and still produced zero orders"*, and guessed
> at one-entry-per-day, one-per-sector or capital.
>
> **It was never 9 setups.** It was **one** — JINDALSTEL long — re-evaluated
> **nine times over four minutes** by the 30-second polling loop, logging an
> identical row each time (score 13.38, threshold 6.0, rrr 2.39). The funnel
> counted rows and called them setups.
>
> **And nothing was unexplained.** One `blocked` row that day names the
> reason in full:
>
> ```
> 09:45:39 JINDALSTEL: Inverted Hammer (long) signal skipped —
> confidence 53/100 below the 60 bar
> (Local setup scored 88/100, scaled by a 0.60x system-evidence factor)
> ```
>
> **The confidence gate stopped it** — a locally strong setup scaled down
> because the Scorecard cannot confirm an edge. The gate worked as designed.
> The gap was in this analysis, not the engine.

**The reason it bites so hard is cost, not caution.** At a median stop of
42 bp, a 17 bp round trip is **0.40R of friction** before the market moves
(measured — issue #53). A setup must clear that before it can offer any
reward at all, which is why the median R:R sits at 0.05.

**What would happen if the gates were loosened.** This is measured, not
guessed, over 495 sessions:

| Configuration | Trades | Net expectancy |
| --- | --- | --- |
| **Gated** (as it runs now) | 75 | **−0.41R** |
| **Ungated** (confidence gate off) | 201 | **−0.356R** |

Removing the gates produced **2.7× the trades at a similar loss per trade**.
Both are significantly negative; the ungated run's −0.356R has t = −3.59 and
a confidence interval clear of zero.

> **Loosening the gates does not make money. It loses money faster.** The
> expectancy is negative per trade, so more trades is strictly worse. The
> gates are the reason this has cost ₹169 in simulation rather than
> thousands.

**The honest conclusion.** There is no edge to collect at this trade
structure. The problem is not that good setups are being filtered out — it is
that 0.40R of friction on a 42 bp stop leaves nothing for any entry signal to
win. That is a structural problem with the *trade design*, not the
*filtering*, and it is why the reviewer's Entry 5 §C now requires any new
hypothesis to show expected friction below 0.15R before it can even be
pre-registered.

---

## What this summary did not do

No gate, threshold or configuration was changed. Nothing was written to the
journal. The engine was not restarted and is still running in paper mode.
