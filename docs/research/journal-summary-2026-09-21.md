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
| ...and cleared the confidence gate | **51** | 0.06% |
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

| Session | Side-evals | Passed checklist | Cleared confidence | Top blockers |
| --- | --- | --- | --- | --- |
| 2026-09-15 | 23,984 | 20 | 14 | rrr, sr, pattern |
| 2026-09-16 | 28,240 | 47 | 17 | rrr, sr, pattern |
| 2026-09-17 | 10,724 | 16 | 11 | rrr, sr, pattern |
| 2026-09-18 | 18,550 | 9 | 9 | rrr, sr, pattern |
| 2026-09-21 | 950 | **0** | **0** | rrr, pattern, sr |

`rrr` is the top blocker on every single session.

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

Note also that **all 8 trades fell on 15–17 September and none since**, while
2026-09-18 recorded 9 complete checklist passes that cleared the confidence
gate and still produced zero orders. Something downstream of the gates —
one-entry-per-day, one-per-sector, or capital — stopped those, and this
summary does not isolate which.

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
