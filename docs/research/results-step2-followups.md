# Step 2 follow-ups — results for A, B and C

**Pre-registered:** `prereg-step2-followups.md` and
`prereg-step2-feature-ic.md` amendments 5–9, both committed (`74541e5`)
**before this measurement existed**.
**Run:** 2026-09-21. **Selection split only — the held-out look has NOT been
taken.**
**Trial count:** unchanged at **34**. Logged as research looks L17–L20.

---

## Verdict: the reviewer was right. Three survivors are one factor, and it does not clear cost.

> **Under amendment 8, only `atr_pct` qualifies for the held-out look.**
> `from_high` and `from_low` are **disqualified**: once `atr_pct` is
> controlled for, neither carries information (|t| = 1.05 and 1.90, both
> below the pre-committed bar of 2).
>
> **And §C answers the question that matters:** the effect is worth
> **+8.11 bp** per session as a quintile spread against a round-trip cost of
> **16.60 bp**. Even the most concentrated version (+16.30 bp) does not clear
> it. **There is no tradable edge here.**

---

## A correction to declare first: I changed the history window

Step 2 ran with `YEARS = "4y"`. The follow-ups script was written with
`YEARS = "8y"`. **I did not notice, and the window length was never
pre-registered** — the pre-registration said only "far enough back that
warm-up holds from the first session", which both satisfy.

The consequence is not small:

| | Step 2 | Follow-ups A |
| --- | --- | --- |
| Usable sessions | 561 | **1,546** |
| Earliest session | 2023-09-25 | **2019-10-03** |
| Share of A's sessions predating step 2 | — | **64%** |

So A's sample is a **superset**, and 64% of it is data step 2 never saw —
including the 2020 crash, which for a *volatility-sorted* result is the most
consequential period imaginable.

This means A2's partial ICs could not be compared against step 2's raw ICs.
I computed the raw ICs **on A's own sample** as the correct denominator
(`step2_a_raw_comparator.py`). That is not a new hypothesis; it is the same
measurement step 2 already ran, on the sample A actually used.

**It also produced a finding I was not looking for** — see A3.

---

## A — the three survivors are one factor

*Exploratory, as registered. A2 additionally gates the held-out look.*

### A1 — they are strongly related

Per-session cross-sectional Spearman, mean across 1,546 sessions:

| Pair | Mean ρ | t |
| --- | --- | --- |
| `atr_pct` vs `from_low` | **+0.4299** | +74.85 |
| `from_high` vs `from_low` | **−0.3811** | −70.65 |
| `atr_pct` vs `from_high` | **+0.1884** | +33.10 |

A volatile stock has a wide 52-week range, so it sits further from both ends.
The reviewer's read is confirmed at ρ = 0.43 between `atr_pct` and
`from_low`.

### A2 — and only `atr_pct` survives being controlled for

Rank-residualised, signs corrected, same 1,546 sessions. **The gate (|t| > 2)
was fixed in amendment 8 before these numbers existed.**

| Partial IC | Mean | t | Gate |
| --- | --- | --- | --- |
| `from_high` \| `atr_pct` | +0.0048 | **+1.05** | **DISQUALIFIED** |
| `from_low` \| `atr_pct` | −0.0079 | **−1.90** | **DISQUALIFIED** |
| `atr_pct` \| `from_high`, `from_low` | −0.0284 | **−6.59** | survives |

### A3 — the collapse, against the correct denominator

| Feature | Raw IC (A's sample) | t | Partial IC | t | Retained |
| --- | --- | --- | --- | --- | --- |
| `atr_pct` | −0.0388 | −7.32 | **−0.0284** | **−6.59** | **73%** |
| `from_low` | −0.0254 | −5.25 | −0.0079 | −1.90 | **31%** |
| `from_high` | +0.0086 | +1.73 | +0.0048 | +1.05 | 56% |

This is the signature of a proxy. `atr_pct` keeps three-quarters of its
association and all of its significance when the other two are removed;
`from_low` keeps under a third and loses significance entirely.

**The unlooked-for finding: `from_high` does not replicate on the longer
sample at all.** Step 2 measured **+0.0258, t = +3.33** over 561 sessions —
comfortably through BH and Bonferroni. Over 1,546 sessions it is **+0.0086,
t = +1.73**, which would not have survived BH. Its step-2 result is
sample-dependent, and that is a second, independent reason to doubt it,
separate from the partial-IC argument.

`atr_pct` is also weaker on the longer sample (−0.0388 vs −0.0558) while
staying strongly significant. The effect is **larger in recent years**; §B's
316-session recent window gives −0.0542, close to step 2's figure. Whether
that is a regime or noise is not established here.

---

## B — the tradable target: all three pass, but it barely matters now

Kite **09:20 bar open → 15:10 bar close**, on the 316 selection sessions
overlapping the cache (29,757 stock-sessions; 192 had the day but not both
bars). The yfinance column is computed on **the same 316 sessions**, so the
ratio isolates the target change rather than the sample change.

**Rule, committed before running: same sign and |t| > 2.**

| Feature | yfinance (same 316) | Kite tradable | Retained | Gate |
| --- | --- | --- | --- | --- |
| `atr_pct` | −0.0542 (t = −4.40) | **−0.0416 (t = −3.43)** | 0.77× | **PASSES** |
| `from_low` | −0.0282 (t = −3.14) | **−0.0300 (t = −3.31)** | 1.06× | **PASSES** |
| `from_high` | +0.0279 (t = +2.47) | **+0.0259 (t = +2.31)** | 0.93× | **PASSES** |

**The effect does not live in the opening print.** Excluding the first five
minutes and the closing auction costs `atr_pct` 23% of its IC and leaves the
other two untouched. That was the failure mode §B existed to catch, and it
did not happen — the 18.55% vendor disagreement was not driving the result.

**This does not rescue `from_high` or `from_low`.** Passing B was necessary,
not sufficient; amendment 8 requires the partial-IC gate as well, and both
fail it.

---

## C — what it is worth, in basis points

`atr_pct` only, Kite tradable target, 316 sessions. **Descriptive.**

### Every quintile loses money

Mean tradable return by `atr_pct` quintile, Q1 = quietest:

| | Q1 | Q2 | Q3 | Q4 | Q5 |
| --- | --- | --- | --- | --- | --- |
| Mean return | **−0.08 bp** | −2.86 bp | −3.61 bp | −5.42 bp | **−8.55 bp** |

Monotone across all five — the cleanest picture of the effect in this
document. **And every single bucket is negative.** The quietest quintile
returns −0.08 bp *gross*, before any cost at all.

**So there is no long-only version of this.** The entire effect is relative:
it exists only as long-quiet against short-volatile. A strategy that simply
buys the calmest names does not make money; it loses slightly less.

### And the spread does not cover the cost of capturing it

| | Spread | t | p |
| --- | --- | --- | --- |
| Bottom-minus-top quintile | **+8.11 bp** | +1.68 | 0.093 |
| Bottom-5 minus top-5 | **+16.30 bp** | +2.12 | 0.034 |

Round-trip cost, ₹33,000 notional, cash intraday, at the project's own cost
model: **6.00 bp slippage + 10.60 bp charges = 16.60 bp**.

| Version | Spread | vs cost | |
| --- | --- | --- | --- |
| Quintile (~20 names/side) | +8.11 bp | 16.60 bp | **does not exceed — 0.49×** |
| Top-5 / bottom-5 | +16.30 bp | 16.60 bp | **does not exceed — 0.98×** |

**The reviewer's stated expectation is confirmed: the spread does not exceed
round-trip cost in cash equities.** That expectation was recorded in the
pre-registration precisely so confirming it could not be dressed up as a
discovery, and it isn't one.

The top-5 version comes within 0.3 bp of break-even, which is worth stating
honestly in both directions. **Against it:** that is the noisiest slice
(t = 2.12 on a 316-session sample), it needs *both* legs including a short,
and it is a gross spread against a cost figure that already includes the
slippage estimate — landing at 0.98× cost means an expectancy of
**approximately zero before any of the things a real implementation adds**
(borrow, impact at size, the days you cannot short, the 33% notional cap).

---

## Where this leaves the held-out look

Amendment 8 requires all three conditions. Measured:

| Feature | BH on selection | Passes B | Partial IC \|t\| > 2 | Qualifies? |
| --- | --- | --- | --- | --- |
| `atr_pct` | yes | **yes** | n/a (it is the control) | **YES** |
| `from_low` | yes | yes | **no — 1.90** | **no** |
| `from_high` | yes | yes | **no — 1.05** | **no** |

**One qualifier, so the held-out look is a single test at α = 0.05**, not a
Bonferroni family of three. Three survivors became one, which is what the
amendment was written to do.

**I have not taken it.** Entry 4 §F says to stop for review before the
held-out look, and this file is that stopping point.

**My recommendation is to spend the look anyway, and my reason is not that I
expect it to pass.** §C has already established that `atr_pct` does not clear
cost on selection data, so a held-out confirmation cannot produce a tradable
result. What it can do is settle whether the association is real at all,
which is worth knowing before 3c is pre-registered on top of it — Entry 4 §E
already commits 3c to a volatility-sorted decomposition motivated by this
result. If the reviewer would rather keep the look unspent for 3c, that is
equally defensible and the decision is theirs.

---

## Caveats carried

- **Survivorship bias is worst exactly here.** Today's NIFTY 100 applied to
  history, on a volatility sort: the volatile names that fell out of the
  index are the ones missing. A2's finding that volatility predicts *negative*
  intraday returns is measured in a universe scrubbed of the volatile names
  that did worst.
- **The window length was not pre-registered**, and I changed it between step
  2 and the follow-ups without noticing. Both samples are reported; neither
  was chosen after seeing the other.
- **64% of A's sample is pre-2023**, including the 2020 crash. For a
  volatility-sorted result that is not a neutral extension of the period.
- **None of this is a strategy.** A cross-sectional spread assumes equal
  weight on both tails, no stop, no sizing, no gate, and a short leg that may
  not be available.
- **Selection sample only.** Everything here has been seen by the process
  that chose it.
