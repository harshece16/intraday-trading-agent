# Pre-registration — step 2 follow-ups A, B and C

**Written and committed before any of these measurements were run**, and
before the held-out look. Directed by reviewer Entry 4 §A, §B and §C; the
rule changes they imply are in `prereg-step2-feature-ic.md` amendments 7–9,
committed in the same change.

**Trial count: unchanged at 34.** None of these selects a strategy, sizes a
position or runs a backtest. Each is logged in `trials.md` as a research look.

**Selection split only** — sessions before `splits.HELD_OUT_START`
(2026-01-02). **No held-out data is touched by any run in this file.**

---

## Why these three exist

Step 2 produced three survivors under BH and Bonferroni. Before any of them
is promoted, three things are unresolved:

1. They may be **one effect counted three times** (§A).
2. The target may be a **vendor artefact**, and part of it lies in the opening
   print, which is untradable (§B).
3. An IC is a rank correlation. **It cannot be compared with friction**, which
   is measured in basis points (§C).

Each is answered on selection data, and the answers gate the held-out look.

---

## A — are the three survivors one factor?

**Exploratory. No pass/fail, no p-value threshold, no promotion.** Labelled as
such so nothing here can later be reported as a confirmation.

`from_high` and `from_low` are both distances across a stock's 52-week range,
and a volatile stock has a wide range, so both should be large when `atr_pct`
is large. Read with the signs corrected, all three step-2 results say the same
thing: **high-volatility, wide-range stocks had lower open-to-close returns.**

### A1 — cross-correlations

Per session, cross-sectional **Spearman rank correlation** between each pair
of `atr_pct`, `from_high`, `from_low`. Report the mean across sessions and the
percentage of sessions above zero.

### A2 — partial ICs

Per session:

- residualise `from_high` on `atr_pct` (rank regression), then rank IC of the
  residual against the target;
- the same for `from_low`;
- and the reverse: `atr_pct` residualised on the other two.

Report mean, t across sessions and % positive for each. Signs as corrected.

**A2 is not purely descriptive**: amendment 8 condition 3 uses it as a gate —
`from_high` and `from_low` need **|t| > 2** here to qualify for the held-out
look. That threshold is fixed now, before the numbers exist.

---

## B — a tradable target

**This is the gate.** The rule below is committed before the run.

The registered target is yfinance open-to-close. Three reasons that is not
what a strategy could harvest: nobody can trade the opening print; the
official NSE close is a last-30-minute weighted average, not a last trade; and
18.55% of overlapping stock-sessions disagreed between vendors by more than
25 bp — on `atr_pct` in particular, vendor error plausibly scales with the
feature itself, which is the one way target noise can *manufacture*
association rather than attenuate it.

**Window:** open of the **09:20** bar → close of the **15:10** bar (the last
bar before the 15:15 square-off), from the Kite cache.

**Period:** the selection sessions that overlap the cache, **2024-09-20 →
2026-01-01**. This is a shorter sample than step 2's 561 sessions, so a weaker
t is expected from the sample size alone; the reported ratio of means is the
figure that separates "smaller sample" from "smaller effect".

**Same** eligibility, 252-bar warm-up and corrected signs as step 2.

### Pass rule, fixed before running

> A survivor keeps its status only if its Kite-target IC has the **same sign**
> and **|t| > 2** on the overlap.

### Reported either way

- Mean IC, t, % positive, sessions used, for each of the three.
- **Ratio of the Kite-target mean IC to the yfinance-target mean IC.**
- Plainly, if most of the effect disappears: **the effect lives in the opening
  print and cannot be captured.**

---

## C — the IC in basis points, against cost

**Descriptive. No pass/fail, no strategy trial.** An IC cannot be compared
with friction; this converts it into the same units so the comparison is
possible at all.

For **`atr_pct` only**, on the Kite target, selection overlap only:

1. Sort each session's eligible stocks into **quintiles** by `atr_pct`. Report
   mean target return per quintile in **bp**.
2. **Bottom-minus-top spread in bp per session**, with its t across sessions.
3. The same for a **top-5 / bottom-5** version, since the scanner trades five
   names and a quintile of ~20 is not the portfolio anyone would hold.
4. Set that beside the **measured round-trip cost in bp** for a full-day hold
   under the project's own cost model (`costs.py`), cash intraday.

**State explicitly whether the spread per unit of notional exceeds round-trip
cost.** The reviewer's stated expectation is that it does not in cash
equities. That expectation is recorded here so that confirming it is not
mistaken for a finding, and contradicting it is not quietly smoothed over.

---

## What none of this can establish

- **Nothing here is a strategy.** A cross-sectional spread is not a tradable
  rule: it assumes equal-weight exposure to both tails with no stop, no
  sizing and no gate.
- **Survivorship bias is worst exactly here.** A volatility sort is where
  today's NIFTY 100 applied to history distorts most, because the volatile
  names that left the index are the ones missing. This caveat is carried into
  every statement about the factor.
- **Selection-sample only.** Whatever survives A, B and C has still only been
  seen on data used to pick it. The held-out look is the test, and it does not
  happen until the reviewer has seen A, B and C.

---

## Logging

`trials.md` research looks: **L17** (A1), **L18** (A2), **L19** (B),
**L20** (C). Strategy trial count stays at **34**.
