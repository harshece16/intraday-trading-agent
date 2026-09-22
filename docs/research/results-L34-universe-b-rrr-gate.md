# Results — L34: does universe B clear the reward:risk gate more often than universe A?

**Pre-registered**: `prereg-L34-universe-b-rrr-gate.md`, commit **d879219**
**Script**: `backend/research/universe_b_rrr_gate.py`, commit **2063266**
**Run**: 2026-09-22, one run, 39.0 s. Raw output: `L34_universe_b_rrr_result.json`

Commit order holds: pre-registration precedes script precedes run.

**Trial count stays at 35.** Research look **L34**. Daily bars only, no Kite
calls. Selection window only — **177 held-out sessions were not touched.**

---

## Verdict

> **FAIL against the registered pass rule. Widening the universe does not
> loosen the reward:risk gate — it tightens it slightly.**

| | Universe A (NIFTY 100) | Universe B (F&O ex-NIFTY 100) |
| --- | --- | --- |
| Symbols used | 97 | 112 |
| Valid candidates | 86,869 | 91,593 |
| **Pass fraction at RRR ≥ 1.5** | **93.17%** | **92.83%** |
| Pass fraction at **zero cost** | 95.02% | 94.85% |
| Median reward | 945.90 bp | **1148.55 bp** |
| Median risk | 215.41 bp | **273.03 bp** |
| Median RRR | 3.985 | 3.811 |
| Round trip charged | 16.60 bp | 22.60 bp |

**p_B − p_A = −0.34 pp, two-proportion z = −2.80.**

The pass rule required `p_B > p_A` **and** `z > 2`. Neither held. B is lower,
and the difference is statistically distinguishable in the wrong direction.

Universes are disjoint (**overlap 0**), measured on **identical sessions**
(1,794 sessions, 2018-09-24 → 2026-01-01) taken from the index calendar.

---

## What actually happened — and it is not what branch 3 said

The pre-registration's branch 3 predicted *"B's raw geometry is wider but its
pass fraction is not higher: costs eat the whole gain"*, and the script
reported that branch. **The data say something more specific, and the
difference matters.**

Both sides of B's geometry are wider, but **not by the same factor**:

| | A → B | Change |
| --- | --- | --- |
| Median reward | 945.90 → 1148.55 bp | **+21.4%** |
| Median risk | 215.41 → 273.03 bp | **+26.8%** |

**The risk side widens faster than the reward side.** That is the whole
result. The user's hypothesis — mid-caps move more, so targets should be
easier to reach — *is true in absolute terms*: B's targets genuinely sit 21%
further away. But B's stops sit 27% further away too, and reward:risk is a
ratio.

The decisive evidence that this is geometry and not friction: **at zero cost,
B is still worse** — 94.85% vs 95.02%. If costs were eating the gain, B would
lead before costs and trail after. It trails in both. The doubled slippage
(22.60 vs 16.60 bp) widens the gap from 0.17 pp to 0.34 pp; it does not create
it.

So the honest branch is **neither 3 nor 4 as written** — see the defects
section. The finding is: *mid-cap ranges are wider on both sides and slightly
worse in ratio, and costs then make that slightly worse again.*

---

## Secondary, no pass rule

| | A | B |
| --- | --- | --- |
| RRR min | 0.268 | 0.307 |
| RRR median | 3.985 | 3.811 |
| RRR mean | 7.072 | 6.541 |
| RRR p90 | 14.797 | 13.538 |
| Long pass fraction | 92.10% | 92.07% |
| Short pass fraction | 93.98% | 93.47% |
| Skipped — no level on that side | 33,640 | 33,596 |
| Skipped — stop wider than 1.5 ATR | 167,683 | 180,233 |

B is lower at every point of the RRR distribution, on both sides of the book.
B also loses more candidates to the 1.5 ATR stop filter (180k vs 168k) —
consistent with wider ranges.

---

## Defects in this look, recorded

### 1. The proxy saturates. This is the serious one.

**93% of candidates clear the gate here. The live engine's rate is 9.6%.** A
factor of roughly ten.

The pre-registration anticipated that the level would not match and
restricted the claim to the *difference* between universes. That defence
still holds — the rule never reads the universe label, so the bias is
identical on both sides. But saturation has a consequence the
pre-registration did not name: **with both universes at ~93%, there is only
7 pp of headroom, so the metric cannot express a large improvement even if
one existed.** The test is well powered statistically (n ≈ 87k and 92k, it
resolves 0.34 pp at z = 2.80) and poorly powered *semantically*.

The cause is the geometry rule itself. A 20-session daily high/low sits a
median **9.5%** away, while the stop is capped at 1.5 ATR ≈ **2.2%**. A ratio
of ~4 clears a 1.5 bar almost always. The live engine reads 5-minute
structure where the next level is minutes away, not 9.5% away — a different
regime, not a scaled version of this one.

**This measurement should be read as evidence about mid-cap daily range
geometry, which is what it actually measures, and only weakly as evidence
about the live intraday gate.** I designed the proxy and it is weaker than I
expected when I registered it.

### 2. Branches 3 and 4 overlap in the pre-registration

Branch 3 ("wider geometry, no better pass fraction") and branch 4 ("p_B < p_A
with |z| > 2") are both true of this result. They were written as if
exclusive and the script's `if/elif` chain silently resolved the ambiguity by
ordering. No number changed, but the reported branch label is an artefact of
code order rather than of the registered logic. **A branch tree must be
mutually exclusive or it is not a pre-commitment.**

### 3. The 22.60 bp figure is still an assumption

Entry 6 §D fixed it as double the configured slippage. It has never been
measured from this project's own fills, because **no real-money order has
ever been placed**. The zero-cost column is reported precisely so this
result does not rest on it — and it does not.

### 4. Survivorship is larger in B, and it cuts the wrong way

Today's F&O membership applied to eight years of history flatters mid-caps
more than large-caps (Entry 6 §B). Any such bias would make B look *better*
than it should. **B still lost.** The finding is therefore conservative.

---

## What this does and does not license

**Does not license** adding universe B to the live scanner. The measured
basis for expansion that this look was built to find is absent. Entry 6 §F
keeps that a separate decision regardless, and the phase-2 verdict is
unchanged: entries are indistinguishable from a matched random-entry null,
and a wider universe does not create an edge.

**Does not license** Entry 6 §C.2's 5-minute download for universe B either.
That step was gated on something surviving here. Nothing did.

**Does record** one fact worth keeping, which cost no trial: **the binding
constraint is not universe breadth.** Going from 100 large-caps to 113
liquid mid-caps widens targets by 21% and stops by 27%. Whatever is wrong
with this trade structure, it is not that the scanner was looking at too few
stocks.

**Leaves open**, honestly: this measured daily geometry, not the live
intraday gate. A proxy built on 5-minute structure could still answer the
original question properly. It would need Kite data for universe B, which
Entry 6 §C.2 gates behind a user go-ahead — and on this evidence it is not
worth asking for.

---

## The live defect this sits on

`backend/costs.py:11` applies one global `slippage_pct` to every symbol;
`backend/config.py:332` sets it to 0.03% per leg, described in its own
comment as *"a rough estimate, not measured"*. Entry 6 §D's doubling exists
only in research scripts. **The live path has no per-symbol slippage at all**,
so if universe B were ever added to the live scanner, its RRR gate would
price mid-cap slippage as large-cap slippage and pass trades it should
reject. Filed as a GitHub issue; not fixed here.
