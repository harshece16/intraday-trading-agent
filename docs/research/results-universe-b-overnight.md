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

**The strong, replicating, strengthening effect is the one we cannot trade.
The weak, decaying, universe-specific effect is the one an intraday agent
could reach.**

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

> **This is the most decision-relevant line in the file. Over the recent four
> years the overnight volatility effect got stronger and the intraday one got
> weaker.** The tradable half is decaying; the untradable half is not.

It also corroborates §D.1's year-by-year finding from a completely different
angle: the index-level split weakened through 2022–2025, and here the
*intraday* component is what weakened.

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

The same 0.36× the index-level calculation gave by a different route. **Both
the level and the spread cost about three times what they yield.**

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
