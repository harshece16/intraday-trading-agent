# Universe B overnight leg — results

**Pre-registered:** `prereg-universe-b-addendum-overnight.md`, commit
`9530c22`, written before any universe B overnight value was computed.
**Run:** 2026-09-21. Selection dates only; **universe B's 2026 data untouched.**
**Trial count:** 34. Research looks **L27–L28**.

---

## Verdict: PASS — and the two legs now point in opposite directions

> **The overnight spread replicates almost exactly: −14.15 bp, t = −8.55,
> against universe A's −13.83 bp. Retained 1.02×. PASS.**
>
> **The intraday spread does not: +5.97 bp, t = +1.63 — below significance,
> against universe A's +7.40 bp at t = +2.38.** It carried no pass rule, and
> it is reported as measured.

> **Corrected (Entry 8 §A.1).** The original sentence read *"the strong,
> replicating, strengthening effect is the one we cannot trade; the weak,
> **decaying**, universe-specific effect is the one an intraday agent could
> reach."* **"Decaying" is withdrawn.** +5.97 bp (t = 1.63) against +3.99 bp
> (t = 1.15) on a *nested* sub-window is two non-significant numbers whose
> difference was never tested.

**The supportable statement: the intraday spread is not distinguishable from
zero on universe B in either window; the overnight spread is significant in
both.**

---

## L27 — unconditional means

| | Universe B (8y) | Universe A (8y) |
| --- | --- | --- |
| **Overnight** | **+19.84 bp** (t = +10.57) | +16.78 bp (t = +9.50) |
| **Intraday** | **−9.93 bp** (t = −3.45) | −6.94 bp (t = −2.80) |

Both legs are **larger in mid-caps** than in the NIFTY 100 — more overnight
gain and a worse intraday drag. 1,544 sessions, median breadth 54.

---

## L28 — volatility-sorted, and the pass rule

| Quintile | Overnight | Intraday | Sum |
| --- | --- | --- | --- |
| **Q1** (quietest) | +14.40 bp | −9.01 bp | +5.39 bp |
| Q2 | +16.26 bp | −9.30 bp | +6.96 bp |
| Q3 | +18.39 bp | −8.16 bp | +10.22 bp |
| Q4 | +21.70 bp | −8.21 bp | +13.49 bp |
| **Q5** (most volatile) | **+28.03 bp** | **−14.63 bp** | +13.40 bp |

**The overnight leg is cleanly monotone across all five buckets.** The
intraday leg is not — Q1 through Q4 sit flat between −8.2 and −9.3 bp and
only Q5 separates, the same non-monotonicity found in the §B.1 run.

| Spread (quiet − volatile) | Universe B | Universe A | Retained |
| --- | --- | --- | --- |
| **OVERNIGHT** — *pass rule* | **−14.15 bp** (t = **−8.55**) | −13.83 bp (t = −9.79) | **1.02×** |
| Intraday — *no pass rule* | +5.97 bp (t = +1.63) | +7.40 bp (t = +2.38) | 0.81× |

**PASS.** Same sign, |t| = 8.55 against a bar of 2.

---

## The 4-year secondary window (declared in advance)

989 sessions, 2022-01-03 → 2026-01-01, median breadth 82.

| Spread | 8-year | **Recent 4-year** | Direction |
| --- | --- | --- | --- |
| **Overnight** | −14.15 bp (t = −8.55) | **−16.48 bp (t = −10.70)** | **stronger** |
| **Intraday** | +5.97 bp (t = +1.63) | **+3.99 bp (t = +1.15)** | **weaker** |

> **Read carefully: the 4-year window is NESTED inside the 8-year one, and no
> test was run on the difference.** The overnight spread is significant in
> both windows (t = −8.55 and −10.70). The intraday spread is **not
> distinguishable from zero in either** (t = +1.63 and +1.15). Saying the
> intraday effect "weakened" compares two nulls and is not supported
> (Entry 8 §A.1).

What can be said: **the leg that is statistically solid in both windows is
the overnight one, and the leg an intraday agent could reach is not
distinguishable from zero in either.**

---

## The economics, with Entry 6 §D's doubled slippage

Capturing an overnight spread means a **delivery** round trip every day, not
an intraday one. From the §D.2 cost sheet, at ₹33,000 notional with universe
B's doubled slippage:

```
delivery charges          27.05 bp
slippage, doubled (§D)    12.00 bp
                          --------
round trip                39.05 bp
```

| | |
| --- | --- |
| Overnight spread (universe B, 8y) | **+14.15 bp** |
| Delivery round trip at ₹33,000, doubled slippage | **39.05 bp** |
| **Ratio** | **0.36× — it does not pay** |

> **Correction footnote (Entry 12 §1, 2026-09-21).** The comparison above
> measures a **top-minus-bottom spread against ONE round trip**. A spread is
> **two positions** — long and short — and **each pays its own round trip**,
> so the correct hurdle is **double** the figure quoted. As a footnote, not a
> recomputation: the overnight spread is **+14.15 bp against 78.10 bp (2 × 39.05), not 39.05 — 0.18×, not 0.36×**. This compounds the point already made in the paragraph above: a short leg held overnight is not available in cash equities at all.
>
> **This makes every spread result worse, never better**, so no conclusion
> here is reversed — each was already a failure against the single-round-trip
> bar, and the corrected bar is twice as far away.


~~The same 0.36× the index-level calculation gave by a different route. Both
the level and the spread cost about three times what they yield.~~
**CORRECTED (Entry 13 §E.3): the spread is 0.18× at the two-leg hurdle, not
0.36×. The index-level 0.36× is a genuinely different, single-leg figure that
was never wrong — a lone long position pays exactly one round trip — so the
two only coincided before this correction. The spread costs about FIVE times
what it yields; the level about three.**

**And 0.36× is generous, in the safe direction (Entry 8 §A.2).** A
quiet-minus-volatile *spread* requires a **short leg held overnight, which
cash equities do not permit at all**, and a two-legged position would pay
**two** round trips rather than one. The true figure is worse than 0.36×;
~~it is not recomputed here because the conclusion does not turn on it.~~ **It has since been recomputed — see the correction footnote above: 0.18×.**

---

## One thing §D.1 did **not** settle, stated explicitly

§D.1 measured survivorship bias in the **level** of the overnight return
(+16.78 → +12.01 on the index, 40% inflated). **It says nothing about the
spread**, because an index has no cross-section to sort into quintiles.

**So the overnight quintile spread's survivorship exposure is unmeasured.**
It is a relative, cross-sectional quantity and therefore *less* exposed than
a level — but "less" is not "none", and on a volatility sort the missing
names are the volatile ones. I am not claiming the −14.15 bp is
survivorship-free; I am saying nothing yet measures how much of it is.

---

## Caveats carried

- **Today's F&O-eligible list applied to history.** Mid-caps leave that list
  more often than large-caps and usually after falling.
- **Median breadth 54** over the 8-year window (82 over the recent 4).
- **Same period, different stocks** — not an out-of-time test.
- **No overnight figure here was compared against an intraday cost bar**, per
  the pre-registration.
- **Nothing in this system holds overnight**, so none of the overnight
  results describe a trade this agent could place.
