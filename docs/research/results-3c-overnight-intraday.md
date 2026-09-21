# 3c results — overnight vs intraday

**Pre-registered:** `prereg-3c-overnight-intraday.md`, commit `8306b2c`,
written and committed **before** the measurement code existed.
**Run:** 2026-09-21. **Selection split only** — §D (held-out) was specified
in advance and **was not run**.
**Trial count:** unchanged at **34**. Research looks **L23–L25**.

---

## Verdict: the mechanism holds, and it is in the half we cannot trade

> **The pre-registered prediction was: overnight return rises with ATR% while
> intraday falls. Both legs behave exactly as predicted, monotonically across
> all five quintiles.**
>
> **And it changes nothing about tradability.** The intraday leg — the only
> one an intraday agent can touch — is worth **+8.11 bp** against a
> **16.60 bp** round trip. The big, strongly significant effect lives
> **overnight**, where this system structurally cannot reach it.

---

## §A — the whole equity return in this sample is earned overnight (L23)

1,544 selection sessions, 2019-10-03 → 2026-01-01.

| Component | Mean | t |
| --- | --- | --- |
| **Overnight** (prev close → open) | **+16.78 bp** | **+9.50** |
| **Intraday** (open → close) | **−6.94 bp** | **−2.80** |
| Total daily | +9.84 bp | — |

**Intraday return is significantly negative across the whole universe.** Not
flat — negative, at t = −2.80. Holding NIFTY 100 names from open to close, on
average, loses money before any cost at all.

**This independently corroborates the null diagnostic.** That measurement,
by a completely different route — random entries pushed through the
backtester — found longs at −0.0947R and shorts at +0.0351R. Two methods, one
fact: **the intraday session has a negative drift in this sample, and any
long-biased intraday book starts behind.**

It also reframes the project's central result. The agent was built to trade
open-to-close. That window has a −6.94 bp headwind before friction, and
friction is another 16.60 bp.

---

## §B — volatility-sorted, and the mechanism is confirmed (L24)

ATR% quintiles, 1,544 sessions, daily bars.

| Quintile | Overnight | Intraday | Sum |
| --- | --- | --- | --- |
| **Q1** (quietest) | +10.67 bp | −2.97 bp | +7.70 bp |
| Q2 | +13.92 bp | −5.38 bp | +8.54 bp |
| Q3 | +16.20 bp | −8.25 bp | +7.95 bp |
| Q4 | +18.57 bp | −7.66 bp | +10.91 bp |
| **Q5** (most volatile) | **+24.23 bp** | **−10.31 bp** | +13.92 bp |

**Both legs are monotone across all five buckets.** Overnight rises from
+10.67 to +24.23 bp; intraday falls from −2.97 to −10.31 bp.

| Spread (quiet − volatile) | Mean | t |
| --- | --- | --- |
| **Overnight** | **−13.83 bp** | **−9.79** |
| **Intraday** | **+7.40 bp** | **+2.38** |

> **MECHANISM HOLDS, as pre-registered.** Volatile stocks earn their return
> overnight and give part of it back intraday. That is the textbook
> explanation, and it survived a test designed to falsify it.

**The falsification branch did not fire.** The pre-registration stated that
if intraday fell while overnight did *not* rise, the result would be drift
rather than mechanism — a worse fact. Overnight rose, strongly (t = −9.79 on
the spread, the largest |t| anywhere in phase 2).

**Note the asymmetry in strength.** The overnight spread is nearly **twice**
the intraday spread and **four times** as significant. The effect is
predominantly an overnight phenomenon that leaves an intraday residue.

---

## §C — on the tradable window, it still does not pay (L25)

Kite **09:20 open → 15:10 close**, 316 overlapping selection sessions.

| Quintile | Overnight | Intraday (tradable) | Sum |
| --- | --- | --- | --- |
| **Q1** (quietest) | +3.75 bp | **−0.08 bp** | +3.67 bp |
| Q2 | +6.54 bp | −2.86 bp | +3.68 bp |
| Q3 | +9.45 bp | −3.61 bp | +5.84 bp |
| Q4 | +11.44 bp | −5.42 bp | +6.02 bp |
| **Q5** (most volatile) | **+16.24 bp** | **−8.55 bp** | +7.69 bp |

| Spread (quiet − volatile) | Mean | t |
| --- | --- | --- |
| Overnight | −12.40 bp | −4.50 |
| **Intraday (tradable)** | **+8.11 bp** | **+1.68** |

> **+8.11 bp against a 16.60 bp round trip = 0.49×. It does not clear cost.**

> **Correction footnote (Entry 12 §1, 2026-09-21).** The comparison above
> measures a **top-minus-bottom spread against ONE round trip**. A spread is
> **two positions** — long and short — and **each pays its own round trip**,
> so the correct hurdle is **double** the figure quoted. As a footnote, not a
> recomputation: 3c's tradable intraday spread is **+8.11 bp against 33.20 bp, not 16.60 — 0.24×, not 0.49×**. The `edge / friction = 0.49` invariance figure quoted further down is likewise **0.24**.
>
> **This makes every spread result worse, never better**, so no conclusion
> here is reversed — each was already a failure against the single-round-trip
> bar, and the corrected bar is twice as far away.


This reproduces step 2 §C's figure exactly (+8.11 bp, t = 1.68), computed by
a different script on the same window — a consistency check that passes.

**And every tradable intraday bucket is negative**, Q1 through Q5. There is
no long-only version of this. The spread exists only as long-quiet against
short-volatile, and even then it returns half the cost of executing it.

---

## What would it take, and why I am not proposing it

The honest reading is that **the money is overnight**, and the arithmetic
there is much better: a −12.40 bp spread at t = −4.50 on the tradable-window
sample, −13.83 bp at t = −9.79 on the full one.

**Capturing it means going long the most volatile names and holding through
the close.** Three reasons that is not a proposal:

1. **It is a different system.** Overnight holding changes the cost model to
   delivery (STT on both legs, higher stamp duty, a depository charge), the
   risk profile to gap risk, and the mandate from intraday to swing. Nothing
   in the current agent applies.
2. **Survivorship bias is at its most dangerous precisely here.** This is
   today's NIFTY 100 applied to history. A strategy that buys the most
   volatile names and holds them overnight is the exact strategy that the
   missing names — the volatile ones that fell out of the index — would have
   punished. The measured +24.23 bp for Q5 is an overestimate by an unknown
   amount, and the bias is not small on this cut.
3. **Selection sample only, and motivated by it.** Per the pre-registration's
   own declared-motivation rule, none of this confirms anything. It was
   derived from the sample it is measured on.

---

## What this settles for step 3

**Entry 5 §C's constraint is vindicated, and then some.** The design lever is
cost as a fraction of R — but 3c shows the intraday window itself carries a
**−6.94 bp headwind** before cost. A 3a/3b hypothesis must now clear both:

```
friction_R = round_trip_bp / stop_bp   <   0.15R      (Entry 5 §C)
and the entry must overcome a structurally negative intraday drift
```

At the wide stops §C's constraint implies (~150 bp daily-ATR), friction falls
to ~0.11R — but the best cross-sectional signal found so far returns 8.11 bp
on a 150 bp stop, which is **0.054R of edge against 0.11R of friction**.
Still negative.

> **Widening the stop fixes the friction ratio and does not fix the
> arithmetic**, because the edge scales down with the same denominator the
> cost does. Both are basis points divided by the stop, so
> `edge / friction = 8.11 / 16.60 = 0.49` **whatever the stop width is**.
> The ratio is invariant. That is worth stating plainly before 3a and 3b are
> designed around a wider stop.

And that comparison is already **generous to the strategy**: it credits a
trade with the full cross-sectional spread, which assumes capturing both
tails perfectly with no slippage beyond the modelled figure and no gate
losses. The real number is lower.

---

## Caveats carried

- **Selection sample only.** §D was specified and not run; the held-out
  period remains unspent and contested between this and step 2's `atr_pct`
  look. Universe B (Entry 6) may be the better confirmation sample for both.
- **Survivorship bias is worst on this exact cut** — a volatility sort of a
  volatility finding, in an index whose volatile dropouts are missing.
- **Overnight return is not free money.** It requires holding through the
  close, which no part of this system does.
- **A quintile spread is not a strategy**: equal weight on both tails, no
  stop, no sizing, no gate, and a short leg that may not be borrowable.
