# Step 1 results — random-entry null test

**Pre-registered:** `prereg-null-test.md`, commit `e4545e0`, written and
committed before the test code existed.
**Run:** 2026-09-20 09:11 → 16:0x, 400 runs (200 seeds × 2 cost modes),
~6 h 50 m.
**Trial count:** unchanged at **34**. Logged as research look **L5** — the
test measures the instrument and selects no strategy.

---

## Verdict: PASS, marginally

> **Pass rule (pre-registered):** zero-cost seed-mean gross expectancy within
> **±0.05R** of zero.
>
> **Result: −0.0495R → PASS**, by 0.0005R.

**This is not a robust pass and should not be read as one.** Across 200 seeds
the spread is sd 0.0880, giving a standard error of 0.0062 and a 95%
confidence interval of **[−0.0616, −0.0373]**. The band edge −0.05 sits
**inside** that interval. The true harness bias could plausibly be anywhere
from −0.037R to −0.062R; the rule could have gone either way on a different
draw.

The checkpoint sequence converged onto the boundary rather than away from it:
−0.0585, −0.0535, −0.0591, −0.0533, −0.0484, −0.0517, −0.0509, **−0.0495**.

**What this means in practice:** the harness is conservative by very close to
the maximum the rule tolerates. **Every strategy result this project has
produced carries roughly −0.05R per trade of pessimistic bias**, and that
includes the verdict. It is bias in the safe direction — the harness
understates edge rather than manufacturing it — which was the outcome that
mattered.

Two deliberately conservative conventions account for it, as predicted in the
pre-registration: **stop-first when a single bar spans both barriers**, and
**gap-through fills at the open** rather than at the barrier price.

---

## Distributions

### Zero-cost (the pass-rule run)

| | mean | sd | SE | 95% CI | p2.5 | p97.5 |
| --- | --- | --- | --- | --- | --- | --- |
| Gross expectancy | **−0.0495R** | 0.0880 | 0.0062 | [−0.0616, −0.0373] | −0.2369 | — |
| Net expectancy | −0.0495R | 0.0880 | — | — | — | — |
| Resolved-target % | 25.02 | 3.24 | — | — | 18.07 | 31.58 |

Net equals gross exactly, as it must when costs are zero — a sanity check the
run passes.

Trades/seed **214** (real: 201). Realised R median **₹100.6** (real: ₹101.2).
Stop median **42.4 bp** (real: 42.4 bp). The matching worked.

### With-cost

| | mean | sd | SE | 95% CI |
| --- | --- | --- | --- | --- |
| Gross expectancy | −0.1790R | 0.0817 | 0.0058 | [−0.1903, −0.1677] |
| Net expectancy | −0.4135R | 0.0825 | — | — |

Trades/seed 214. Realised R median ₹108.3. Stop median 45.4 bp.

**Why with-cost "gross" differs from zero-cost gross.** `ZERO_COSTS` zeroes
*slippage* as well as charges, so fill prices differ between the two runs and
the pre-cost P&L is genuinely not the same number. Friction between the two
with-cost figures is 0.2345R, against the real strategy's 0.2539R — the gap
follows from the null's slightly larger R (₹108.3 vs ₹101.2), since charges
are roughly fixed in rupees.

---

## Findings about the strategy (not pass conditions)

### Correction: the benchmark used in the verdict was wrong

The verdict (README §51) states the strategy's resolved trades come in at
28.4% targets against a random-walk expectation of 31.9%, and concludes the
signal performs **"like a coin flip, a shade worse"**.

That comparison used the **formula** 1/(1+RR). The pre-registration, following
the reviewer's Entry 1 correction, predicted the formula would be too high for
a resolved-only rate under a 15:15 timeout, because the nearer barrier
resolves faster and far-target trades are disproportionately timed out.

**Measured: the null's resolved-target rate is 25.02%, which is 6.24
percentage points below the 31.26% reference.** The prediction is confirmed
and quantified — and it is a magnitude no formula supplies.

### Against the correct benchmark, the signal is better than random

All three comparisons below are like-for-like: the real figures come from a
`config.COSTS` run, so they include slippage, and are therefore compared
against the **with-cost** null, not the zero-cost one.

| | Real | Null (mean) | Excess | In σ | Percentile |
| --- | --- | --- | --- | --- | --- |
| Gross expectancy | −0.1021R | −0.1790R | **+0.0769R** | +0.94 | 82.5th |
| Net expectancy | −0.3560R | −0.4135R | **+0.0575R** | +0.70 | 74.5th |
| Resolved-target rate | 28.41% | 25.02% | **+3.39pp** | +1.05 | 86th |

**The entry signal is modestly better than random, consistently across three
independent statistics — and not significantly so.** Every margin is under
1σ. The honest reading is *"indistinguishable from random, leaning slightly
positive"*, not *"worse than random"*.

**This does not rescue the strategy.** Net expectancy is still −0.356R with
t = −3.59 and a confidence interval clear of zero. Being marginally better
than random while losing 0.356R per trade means the signal is real-ish but far
too small to cover 0.254R of friction. What changes is the *diagnosis*: the
entry is not actively harmful, it is insufficient.

### An unresolved tension

The strategy's resolved-target rate sits at the **86th** percentile while its
gross sits at the **82.5th** — consistent. But against the *zero-cost* null
its gross would sit at the 26th percentile. That apparent contradiction is
entirely the slippage mismatch described above, and resolving it correctly is
what produced the corrected table.

One genuine open question remains: **why the higher target rate does not
translate into proportionally higher gross.** Answering it needs per-trade bar
geometry, which the main run does not persist. `null_diagnostic.py` (20 seeds,
trade lists retained) was approved for the negative-fail branch and **was not
run**, since the result is a pass. It could answer this if the reviewer wants
it.

---

## Caveat carried, stated not fixed

Per Entry 2 §B: stop distances are bootstrapped in **basis points**, so a
42 bp stop can land on a stock whose volatility makes that unusually tight or
loose. This does not affect the gross-expectancy gate — R-multiples are
scale-invariant at zero cost — but it shifts time-to-resolution and the
timeout share. **The resolved-only target-rate comparison is therefore
approximate**, and the 86th-percentile figure should be read with that
looseness in mind. The gross and net comparisons are not affected in the same
way.

---

## What I got wrong, recorded

1. **The findings line in `null_test.py` compared the real gross against the
   zero-cost null.** Not like-for-like: the real figure includes slippage and
   the zero-cost null does not. The script's printed "26.0th percentile" is
   wrong; the correct figure is the 82.5th. Found while writing this file, by
   checking which cost model produced each number rather than trusting the
   labels.
2. **The script does not persist trade lists**, which would have made the
   §B2 diagnostic impossible on a negative fail. Raised as blocker B-2 before
   the run finished; moot on the pass branch, but it was a design error.
3. **The 238 s/seed rate reported mid-run was wrong** — a stale log read under
   swap pressure, with fixed setup cost wrongly attributed to the per-seed
   rate. Withdrawn as blocker B-1.

---

## Consequences for the record

**README §51, the verdict artifact and issue #49 all contain the
"worse than a coin flip" claim and the 31.9% benchmark.** Both are wrong on
the evidence above. They need correcting, and that correction is queued as the
next action after this file is committed.

The overall verdict — no edge, net expectancy significantly negative, do not
trade it — is **unchanged**. What changes is one mechanism sentence inside it.

---

## Next

Pass branch (Entry 2 §B1) applies: proceed to **step 2**, per-feature scanner
IC, pre-registered at `prereg-step2-feature-ic.md` (commit `bc704e5`,
committed before this result existed).
