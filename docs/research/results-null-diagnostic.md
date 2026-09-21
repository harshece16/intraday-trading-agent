# Null diagnostic — what actually causes the −0.05R harness bias

**Directed by:** reviewer Entry 3 §A, against the procedure fixed in Entry 2 §B2.
**Run:** 2026-09-21. 20 seeds, zero-cost, trade lists persisted.
**Trial count:** unchanged at **34**. Research look **L22**.

---

## Verdict: the explanation in the step-1 results file was wrong

`results-step1-null-test.md` said stop-first-on-same-bar and gap-through-at-open
"are the expected sources" of the −0.05R bias. **Measured over 4,327 null
trades, they are not.**

| Candidate | Share of the bias |
| --- | --- |
| **(a)** a single bar spanning both stop and target → stop-first | **0.00%** — it never happened once |
| **(b)** stops gapping through their price | **6.8%** |
| (a) and (b) together | **13%** |
| **Unexplained by fill rules** | **87%** |

**The reviewer's objection was correct and the arithmetic behind it was
right.** A 5-minute bar with ~12 bp of ATR spanning a 42 bp stop *and* a
~95 bp target should be rare — and it turns out to be not merely rare but
**absent from 4,327 trades**. The stop-first rule, the first thing the results
file blamed, has never once been invoked.

---

## The measurements

Baseline seed-mean gross over 20 seeds: **−0.0557R** (SE 0.0222, 95% CI
[−0.0991, −0.0122]). The main run's 200-seed figure was −0.0495R; this is the
same quantity estimated more noisily, and the two agree.

### (a) Single bar spanning both barriers — never occurs

**0 of 4,327 trades (0.00%).** Scoring the (a) trades at the stop/target
midpoint moves the seed-mean by **+0.0000R**, because there are none to score.

### (b) Stops filling beyond the stop price — real but small

**18 of 4,327 trades (0.42%).** Mean extra loss on those is a substantial
**0.9079R**, but spread across every trade it is **0.0038R**, or 6.8% of the
bias.

### (b2) Targets never fill better than their price — the rule is asymmetric

**0 of 792 target exits gapped through**, against 18 of 2,392 stops that did.

**This is the genuine asymmetry**, and it is the one thing in the original
"conservative conventions" story that survives: a stop can fill *worse* than
its price, a target can never fill *better* than its price. It is real, it is
in the pessimistic direction, and it is worth 0.0038R — not 0.05R.

### (c) Removing both barely moves anything

| | Seed-mean gross | Move |
| --- | --- | --- |
| Baseline | −0.0557R | — |
| Excluding (a) and (b) | −0.0483R | **+0.0074R** |
| (a) scored at midpoint | −0.0557R | +0.0000R |

### (d) And here is where the bias actually lives

| Side | Share of trades | Mean gross | 95% CI |
| --- | --- | --- | --- |
| **LONG** | 71.4% | **−0.0947R** | [−0.1439, −0.0455] |
| **SHORT** | 28.6% | **+0.0351R** | [−0.0414, +0.1116] |

A 0.13R gap between sides. Random entries held intraday **lose on the long
side and gain on the short side** — negative intraday drift, which was the
fourth candidate on the reviewer's list and the one nobody pursued.

**The side mix alone accounts for the entire bias:**

```
0.714 × (−0.0947)  +  0.286 × (+0.0351)  =  −0.0576R
```

against a measured baseline of −0.0557R. There is nothing left over for fill
rules to explain.

---

## A correction this forces: the bias is smaller than −0.05R for the real strategy

**The null realised 71.4% long. The real strategy is 59.7% long** (120 of 201
trades). The null was constructed to match the real book's side mix and did
not — it came out 12 points more long-heavy.

That matters precisely because the bias lives in the side mix:

| Side mix | Implied harness bias |
| --- | --- |
| Null as realised, 71.4% long | −0.0576R |
| **Real strategy, 59.7% long** | **−0.0424R** |
| Balanced, 50% long | −0.0298R |

> **Every result in this project has been carrying "−0.05R of pessimistic
> harness bias". At the real strategy's own side mix the figure is about
> −0.042R.**

The direction of this correction is against us: a smaller pessimistic bias
means less of the strategy's loss is the harness's fault. The verdict is
unaffected — net −0.356R at t = −3.59 — but the adjustment that could be
claimed is roughly 25% smaller than stated.

**This also means the −0.05R is not a fixed property of the harness.** It is a
function of how long-heavy the book is. A strategy with a different side mix
carries a different bias, and any future hypothesis must compute its own
rather than inherit this one.

---

## What I got wrong in this diagnostic, recorded

**The (b2) filter tested the wrong string.** I filtered exits on
`reason == "target"`; the backtester's actual string is `"take_profit"`. The
first run printed **"0 of 0 target exits"** — an empty set presented in the
same format as a finding, which is the kind of line that reads as a result
and is nothing of the sort.

Caught by noticing that zero target exits is impossible when the main run
reported a 25% resolved-target rate. Fixed, and re-derived **from the
persisted trades without re-simulating**, which is why the trade lists were
persisted in the first place. The corrected figure (0 of 792) happens to be
genuinely zero — but that is a coincidence, and it was not measured until the
filter was right.

The script now names the string in a module constant with a comment, and
takes `--analyse-only` so the analysis can be re-derived from saved trades.

---

## Consequences

1. **`results-step1-null-test.md` must stop saying fill rules explain the
   bias.** Replaced with the measured attribution above.
2. **The harness bias is −0.042R at the real strategy's side mix**, not
   −0.05R, and it is side-mix dependent rather than constant.
3. **Any long-biased intraday strategy on this universe starts behind.**
   Random long entries lose 0.095R per trade before any cost. That is a
   property of the market in this sample, not of the harness, and it is worth
   more attention than the fill rules were given.
4. The null's failure to reproduce the real book's side mix is a construction
   defect worth fixing before the null is reused.
