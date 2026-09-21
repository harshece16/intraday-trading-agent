# Universe B replication — results

**Pre-registered:** `prereg-universe-b-replication.md`, commit `edd3471`,
written and committed **before** the measurement code existed.
**Run:** 2026-09-21. Selection split, daily bars, **no Kite calls**.
**Trial count:** unchanged at **34**. Research look **L26**.

---

## Verdict: the statistic PASSES. The economics get worse.

> **PRIMARY — PASS.** `atr_pct`'s rank IC replicates on 113 F&O-eligible
> names outside the NIFTY 100: **−0.0332, t = −6.68**, same sign as universe
> A and |t| well over the pre-committed bar of 2. It retains **0.85×** of
> universe A's effect size on an entirely different cross-section.
>
> **And it matters less, not more.** The quintile spread is **+5.97 bp**
> against universe B's **22.60 bp** cost bar — **0.26×**, against universe
> A's 0.49×. Replicating the statistic moved the economics in the wrong
> direction.

This is the strongest statistical evidence phase 2 has produced, and it does
not change the conclusion.

---

## Sample

| | |
| --- | --- |
| Symbols requested / with daily bars | 113 / **113** |
| Stock-sessions built | 96,942 |
| Dropped for the 252-bar warm-up | 28,295 |
| **Excluded by `tradability_exclusion()`** | **55,917 (58%)** |
| Usable sessions | **1,544** |
| **Per-session breadth** | **median 54** (min 27, max 103) |

The 58% tradability exclusion is expected — mid-caps fail the price and
liquidity floors far more often than NIFTY 100 names — but it means the
effective cross-section is **median 54 names**, against roughly 80 in
universe A. A rank IC on 54 names is noisier than one on 80. **This does not
affect the pass rule, which was fixed in advance**, but it is the right
context for reading the t-statistic.

---

## Primary test — `atr_pct`

**Pass rule, fixed before running: same sign as universe A, and |t| > 2.**

| | Mean IC | t |
| --- | --- | --- |
| Universe A (8y, 1,546 sessions) | −0.0388 | −7.32 |
| **Universe B (8y, 1,544 sessions)** | **−0.0332** | **−6.68** |

| Criterion | Result |
| --- | --- |
| Same sign | **yes** |
| \|t\| > 2 | **yes** (6.68) |
| **Verdict** | **PASS** |
| Effect retained | **0.85×** |

**What this earns.** Entry 6 §A's rationale was that universe B is a
cross-section no test here has ever seen — a more demanding replication than
a fresh date range on the same 100 stocks. That test was passed. The
volatility–intraday-return association is a property of the Indian
large/mid-cap cross-section, not an artefact of the 100 names step 2 happened
to look at.

**And the held-out window is still unspent.** This cost it nothing.

---

## The money, and why a pass does not help

Entry 6 §D's doubled slippage was fixed before the run: universe B's
round-trip bar is **22.60 bp**, not 16.60 bp.

### Mean open-to-close return by ATR% quintile

| | Q1 (quietest) | Q2 | Q3 | Q4 | Q5 (most volatile) |
| --- | --- | --- | --- | --- | --- |
| **Universe B** | **−9.01 bp** | −9.30 bp | −8.16 bp | −8.21 bp | **−14.63 bp** |
| Universe A | −0.08 bp | −2.86 bp | −3.61 bp | −5.42 bp | −8.55 bp |

**Two things differ from universe A, and both matter.**

1. **Universe B is not monotone.** Q1–Q4 sit flat between −8 and −9.3 bp and
   only Q5 separates. The clean gradient that made universe A's result look
   like a factor is **absent here**; what remains is "the most volatile
   quintile is worse", not "return declines with volatility".
2. **Every universe B bucket is far more negative.** The quietest mid-cap
   quintile loses **−9.01 bp** intraday where the quietest large-cap quintile
   lost −0.08 bp. Mid-caps bleed intraday across the board.

That second point is a strong independent corroboration of 3c §A — the
intraday session carries a negative drift — and it is **worse** outside the
NIFTY 100.

### Spread against cost

| Version | Spread | t | vs 22.60 bp bar |
| --- | --- | --- | --- |
| Bottom-minus-top quintile | **+5.97 bp** | +1.63 | **0.26× — does not clear** |
| Bottom-5 minus top-5 | +9.03 bp | +1.85 | **0.40× — does not clear** |
| *Universe A, for reference* | *+8.11 bp* | *+1.68* | *0.49× vs 16.60 bp* |

> **A smaller spread against a higher cost bar. Universe B is a worse place
> to trade this than universe A, not a better one.**

Neither spread reaches |t| = 2, unlike the rank IC. A rank correlation is
unitless and scale-free; a bp spread is neither. **The statistic strengthened
and the tradable quantity weakened — the two are not the same claim, and only
the second one pays for anything.**

---

## Secondary — exploratory, no pass rule, not in any family

Pre-registered as such. **A secondary result cannot rescue a failed primary,
and does not promote anything here either.**

| Test | Universe B | Universe A (8y) |
| --- | --- | --- |
| `from_high` raw IC | +0.0104 (t = +2.11) | +0.0086 (t = +1.73) |
| `from_low` raw IC | −0.0167 (t = −3.60) | −0.0254 (t = −5.25) |

### Does "one factor, not three" replicate?

| Partial IC | Universe B | Universe A |
| --- | --- | --- |
| `from_low` \| `atr_pct` | **−0.0006 (t = −0.14)** | −0.0079 (t = −1.90) |
| `atr_pct` \| both | **−0.0269 (t = −6.18)** | −0.0284 (t = −6.59) |
| `from_high` \| `atr_pct` | **+0.0104 (t = +2.24)** | +0.0048 (t = +1.05) |

**Two of three replicate, decisively.** `from_low` collapses to t = −0.14 —
essentially zero, an even cleaner demonstration of a pure proxy than universe
A gave. `atr_pct` survives controlling for both at t = −6.18, near-identical
to A's −6.59.

**`from_high` disagrees between universes.** Disqualified in universe A at
t = +1.05; here it reaches t = +2.24, which would clear amendment 8's bar.

**I am not promoting it, and the disagreement is the finding.** Three
reasons: it was disqualified on universe A under a rule fixed in advance;
this test was pre-registered as exploratory with **no** pass rule; and
t = 2.24 against a bar of 2.0 is marginal on a test that was never given one.
A feature that qualifies in one universe and not another is **less** credible
than one that does neither, because it means the earlier verdict was
sample-dependent — which is exactly what happened to `from_high`'s raw IC
between the 4y and 8y windows (t = +3.33 → +1.73).

---

## What this changes

**It strengthens the science and changes nothing about the trade.**

- The volatility effect is **real and cross-sectionally general**. That is a
  genuine result and the best this project has produced.
- It is **not tradable at any stop width**. The edge-to-cost ratio is
  invariant to the stop (both numerator and denominator are bp over the same
  stop), and here it is **0.26×**. Widening the stop cannot fix a ratio.
- **The held-out window remains unspent**, and after this it is worth less
  as a test: universe B already answered the "is it real" question more
  demandingly than a later date range on the same stocks would.

---

## Caveats carried

- **Survivorship bias is worse here, not better.** Today's F&O-eligible list
  applied to history. Mid-caps enter and leave that list more often than
  large-caps and usually leave after falling — on a volatility sort, in the
  direction that flatters the finding.
- **Median breadth 54 names**, against ~80 in universe A.
- **Same period, different stocks.** Any market-wide regime effect over
  2019–2026 is shared by both universes, so this is not an out-of-time test.
- **The 22.60 bp bar is an assumption, not a measurement.** Entry 6 §D fixed
  double slippage in advance precisely because no measured universe B fill
  exists. If real mid-cap slippage is worse than 2×, the 0.26× is optimistic.
- **A quintile spread is not a strategy**: equal weight on both tails, no
  stop, no sizing, no gate, and a short leg that may not be borrowable —
  which is a sharper objection for mid-caps than for the NIFTY 100.
