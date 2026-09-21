# Pre-registration — 3b, first-half-hour intraday momentum

**Written and committed before any 3b code exists.** Directed by reviewer
Entry 11 §H.

**NOT RUN.** Two gates, both required: **reviewer review of this
pre-registration**, then **the user's explicit go-ahead** — the same two-step
that 3a went through.

---

## A proposed change to the trial accounting, raised before it matters

Entry 7 §A grouped 3a and 3b together as **event-conditioned** entries whose
"edge in bp is not known in advance", and therefore worth one trial each.

**That is true of 3a and I do not think it is true of 3b as usually framed.**
First-half-hour momentum in its natural form is a **cross-sectional sort** —
rank the universe by its 09:15→09:45 return, go long the top and short the
bottom, hold to 15:10. That is an **unconditional hold-to-close** signal, the
exact class Entry 7 §A says is subject to the invariance argument, and its
per-trade edge in bp **is** knowable in advance from a cheap measurement, in
precisely the way `atr_pct`'s +8.11 bp was.

**So I propose 3b runs in two stages:**

> **Stage 1 — a measurement, no trial (research look L31).** The
> cross-sectional bp spread of first-half-hour momentum against rest-of-day
> return. **If it does not clear 16.60 bp, 3b is withdrawn and no trial is
> spent.**
>
> **Stage 2 — trial 36, only if stage 1 clears.** The full strategy with
> stops, sizing and the position cap.

**Why this is worth doing rather than going straight to a trial:** the
Deflated Sharpe denominator is the project's scarcest resource, 3a's trial
bought a FAIL that a 20-minute measurement would have predicted (gross
+4.52 bp, not distinguishable from zero, against a 16.60 bp hurdle), and
every cross-sectional spread measured so far — 8.11, 5.97, 7.40 bp — has come
in **below half** the hurdle. Stage 1 is the same measurement those were.

**If the reviewer prefers the single-trial framing, say so and stage 2 runs
directly.** I am not making that call unilaterally; I am raising it before a
result exists, which is the only time raising it is worth anything.

---

## Stage 1 — the measurement (research look L31, no trial)

### Hypothesis

Stocks that move most in the first half hour continue in that direction for
the rest of the session, by more than the round trip costs.

### Construction

| | |
| --- | --- |
| Universe | **A** (NIFTY 100), the registered universe |
| Data | **Kite 5-min cache, already downloaded** — no Kite calls |
| Period | **Selection only**, before 2026-01-02; held-out untouched |
| Signal | **09:15 open → 09:45 close** return, per stock-session, in bp |
| Target | ~~09:45 close → 15:10 close~~ **SUPERSEDED by amendment 1 §3: the target is 09:50 OPEN → 15:10 close**, matching stage 2's entry |
| Eligibility | `scanner.tradability_exclusion()`, ≥ 20 stocks per session |

**The signal window and the target window do not overlap.** ~~The signal ends
at the 09:45 close and the target starts there.~~ **SUPERSEDED by amendment 1
§3:** the signal ends at the **09:45 close** and the target starts at the
**09:50 open** — a **five-minute gap between them, not touching**. That is
stated because an overlapping definition would manufacture correlation, and
it is the first thing a reader should check.

### What is reported

1. **Quintile table**: mean rest-of-day return in bp per momentum quintile.
2. **Top-minus-bottom spread in bp**, mean and **t across sessions**.
3. **Top-5 / bottom-5 spread**, since the live shape trades five names.
4. **Rank IC** of signal against target, mean and t across sessions.
5. **Both halves**, split at the median session date, fixed now.
6. **MDE at t = 2** from the realised session dispersion, reported before the
   spread is read.

### Stage-1 gate, fixed before running

> **Stage 1 clears only if the top-minus-bottom spread is positive with
> t > 2 AND exceeds 16.60 bp.**
>
> **SUPERSEDED by amendment 1 §1 — the correct hurdle is 33.20 bp**, because
> a spread is two positions each paying a round trip.
>
> Anything else **withdraws 3b**, no trial is spent, and the design is **not**
> re-registered with a different signal window, a different holding period or
> a filter.

**A positive spread below 16.60 bp is a withdrawal, not a near miss**, and
will not be described as one.

---

## Stage 2 — the strategy (trial 36, only if stage 1 clears)

Fixed now so it cannot be shaped by stage 1's numbers.

| Parameter | Value | Why |
| --- | --- | --- |
| Entry | **Open of the 09:50 bar** | One bar after the signal window closes — never the signal bar's own close (3a amendment 1 b) |
| **Direction** | **Long top, short bottom — symmetric** | §D.1: intraday drift is −6.42 bp (index-level 2005–2025), −6.73 bp on universe A's window. A long-only intraday book starts behind. |
| Stop | **1 × the 09:15–09:45 range**, either side of entry | The signal's own structure, as in 3a; one variant only |
| Exit | **15:10 bar close**, or stop | Same tradable window used throughout |
| Stop fills | **Identical to 3a amendment 1 (c)** | Intrabar touch → stop price less slippage; bar opening beyond → that open; entry bar may stop |
| Entries per name per session | **1** | Entry 5 §C |
| Concurrent positions | ~~5, slots reopen on exit; chronological, ties alphabetical~~ **SUPERSEDED by amendment 1 §4: TEN positions — long top 5, short bottom 5 — all entered simultaneously at the 09:50 open. The tie-break is deleted.** | Nothing to order when every entry is simultaneous |
| Sizing | **Fixed ₹33,000 notional** | bp primary, R derived |
| Costs | `config.COSTS`, full **16.60 bp** | Unverified against the broker's tariff — caveat carried |
| Harness | **Self-contained**, as 3a | `run_backtest()` enters at the signal bar's close, which the fill rule forbids (3a amendment 2) |

**`friction_R`** is reported before the statistics, as `16.60 / stop_bp` from
the realised median stop. **Necessary, not sufficient** (Entry 7 §A).

### Stage-2 pass rule

> **Mean NET bp per session > 0 with t > 2, and the sign holding in both
> halves.** Primary statistic is the **session mean**; the pooled per-trade
> mean is secondary with no pass rule.
>
> **Positive gross with negative net is a FAIL.**

**Untestable branch:** if MDE at t = 2 exceeds 16.60 bp, the run is reported
as **untestable**, not as a null.

---

## What 3b cannot establish

- **One variant is not a search.** No second signal window, no second holding
  period, no filter, whatever the result.
- **Selection sample only.** A pass earns nothing automatically: Entry 11 §G
  and Entry 8 §E both put the held-out look with the user.
- **Survivorship bias** applies as everywhere.
- **The Kite cache starts 2024-09-20**, so the sample is ~316 sessions and
  power is correspondingly limited — which is exactly why the MDE is reported
  before the result.
- **No harness-bias figure transfers.** 3b is self-contained like 3a, so the
  −0.05R measured on `run_backtest()` does not apply and none is asserted.

---

## Stop

**Stopped here for review.** No 3b code exists. Nothing runs without the
reviewer's review of this file **and** the user's explicit go-ahead.

---

# Amendment 1 — Entry 12 (external reviewer)

**Committed before any 3b code exists.** Staging approved: stage 1 is a
research look with no trial; trial 36 is spent only if stage 1 clears.

## 1. The stage-1 gate was wrong by a factor of two

**A top-minus-bottom spread is TWO positions**, long and short, and **each
pays its own 16.60 bp round trip.** Comparing the spread against a single
round trip understated the hurdle by half.

> **CORRECTED STAGE-1 GATE: the cross-sectional spread clears only if it is
> positive, with t > 2, AND exceeds 33.20 bp** — equivalently, the **mean
> per-leg return exceeds 16.60 bp**.
>
> The superseded gate (16.60 bp) is struck, not deleted: ~~"Stage 1 clears
> only if the top-minus-bottom spread is positive with t > 2 AND exceeds
> 16.60 bp."~~

A spread between 16.60 and 33.20 bp is **a withdrawal**, not a near miss.

## 2. Restore the original brief's 3b as a second pre-declared line

The published effect is a **time-series** one, not the cross-sectional sort:
the market's first-half-hour return predicts the last half hour.

| | |
| --- | --- |
| Market proxy | **equal-weighted mean of the universe** |
| Signal | **sign(previous close → 09:45 close)** — includes the overnight gap |
| Target | **14:40 open → 15:10 close** (the last tradable half hour) |
| Statistic | mean of **`sign(signal) × target`** in bp, **t across sessions** |
| Also reported | **both halves**, and the same statistic **per stock, pooled by session** |
| **Gate** | **ONE round trip: positive, t > 2, and above 16.60 bp** |

One leg, so one round trip — unlike the cross-sectional line.

**This is an adapted version, stated plainly:** the literature's window runs
**to the close**, which an intraday cash position cannot hold. Measuring to
the 15:10 bar is a change to the published design, forced by the square-off,
and any result is a result about the adapted version only.

## 3. The cross-sectional target starts at the 09:50 OPEN

Not the 09:45 close. **This matches stage 2's entry exactly**, so stage 1
measures the return a stage-2 trade could actually have captured. The signal
window still ends at the 09:45 close, so signal and target remain disjoint —
with a five-minute gap between them rather than touching.

## 4. Stage 2's position rule

- **Long the top 5 and short the bottom 5 by signal rank — ten positions,
  all entered at the 09:50 open.**
- **The chronological / alphabetical tie-break is DELETED.** It selected
  nothing: every entry is simultaneous, so there is no ordering to break.
  ~~"Concurrent positions: 5, slots reopen on exit; chronological, ties
  alphabetical."~~
- **3a's per-trade friction rule is carried**: skip a candidate if
  `16.60 / stop_bp > 0.15`, and **report how many it removes**.
- **Stage 2 is defined for the cross-sectional version only.**

> **If only the time-series line clears, STOP and report.** It would need its
> own pre-registration; stage 2 as written does not cover it.

## 5. Everything else stands

Universe A, selection dates only, existing Kite cache, no Kite calls,
direction-symmetric, self-contained harness, no harness-bias figure asserted,
one variant, MDE reported before the statistics, halves at the median session
date.

## Authorisation, recorded

- **Stage 1: the user has given a standing go-ahead**, effective once this
  amendment is committed and the research-reviewer has signed off. It spends
  no trial and touches no held-out data.
- **Stage 2: NOT authorised.** If stage 1 clears, **stop and ask the user.**
- Afterwards, whatever stage 1 shows: the results file, then a **closing
  phase-2 report**, then stop. **No new hypotheses are to be proposed in it.**

---

# Amendment 2 — Entry 13 (research-reviewer)

**Committed before any 3b code exists.** Entry 13 accepted amendment 1 and
required §B and §F fixed before stage 1 is coded. §B is annotated in place
above. §F's two ambiguities are resolved below, **stating the choice in the
file rather than deciding it silently in code**.

## §F.1 — which spread gates stage 1a

The reviewer is right that this was ambiguous and that it matters: this
project's two measured quintile-vs-top-5 pairs run **1.5× to 2× apart**
(8.11 → 16.30 bp; 5.97 → 9.03 bp), so the two constructions can land on
**opposite sides of 33.20 bp**.

> **THE GATE IS THE QUINTILE TOP-MINUS-BOTTOM SPREAD** — item 2 of "What is
> reported". It must be positive, t > 2, and **above 33.20 bp**.
>
> **The top-5 / bottom-5 spread (item 3) is DESCRIPTIVE ONLY. It has no pass
> rule, cannot clear stage 1 on its own, and cannot justify a follow-up
> variant** — the same wording Entry 9 §1 required of 3a's broader lines.

The reviewer's default is adopted. The reason to prefer it, stated rather
than assumed: the quintile spread is the **more conservative and better-powered**
of the two — it averages ~20 names a side instead of 5, so it is less
sensitive to a handful of outliers, and it is the construction every earlier
spread in this project was measured on, which keeps the 33.20 bp comparison
like-for-like.

**Noted honestly:** stage 2 would trade top-5/bottom-5, so the gate is
*stricter* than the thing stage 2 would do. That is the intended direction —
a gate should not be easier than the trade it authorises.

## §F.2 — the per-stock time-series line

> **The per-stock line uses THAT STOCK'S OWN signal** — `sign(that stock's
> previous close → its own 09:45 close)` — i.e. true per-stock momentum, not
> the market-level sign applied to every name.
>
> **It is DESCRIPTIVE ONLY, with no pass rule.** Only the market-level line
> (amendment 1 §2) has a gate, and only that gate can clear stage 1b.

## §G — the minor items, all adopted

1. **Stage 2 rank tie at the 5th/6th boundary.** A genuine tie in the signal
   ranking, distinct from the deleted entry-order rule. **Tie-break: symbol
   alphabetical.** Expected to be vanishingly rare at bp precision, and fixed
   now so it is never a decision made at runtime.
2. **Stage 2 inherits stage 1's universe, eligibility, data, period and cost
   model** — universe A, `scanner.tradability_exclusion()`, ≥ 20 eligible
   stocks per session, the existing Kite 5-min cache, selection dates only,
   `config.COSTS`. Stated explicitly rather than left to context.
3. **Amendment 1 §1's "equivalently, the mean per-leg return exceeds
   16.60 bp" is a loose paraphrase and is withdrawn.** Only the **sum** of
   the two legs must exceed 33.20 bp; neither leg individually has to clear
   16.60. **The gate is the 33.20 bp figure on the spread**, and nothing else.

## §D and §E — the stale figures elsewhere

Fixed in the same commit as this amendment: the three stale prose passages
(§E.1–E.3) are struck in their own files, and `report-2026-09-21.md` gets a
pointer footnote. The **closing phase-2 report will restate these at
33.20 bp / 0.24× and 0.49×**, never the withdrawn figures.

## Unchanged

Everything else in the pre-registration and amendment 1 stands. **Stage 1 may
now be coded and run** under the standing go-ahead Entry 12 recorded and
Entry 13 §J confirmed. **Stage 2 remains unauthorised.**
