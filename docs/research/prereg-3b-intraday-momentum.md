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
| Target | **09:45 close → 15:10 close** return, in bp — disjoint from the signal by construction, so no overlap |
| Eligibility | `scanner.tradability_exclusion()`, ≥ 20 stocks per session |

**The signal window and the target window do not overlap.** The signal ends
at the 09:45 close and the target starts there. That is stated because an
overlapping definition would manufacture correlation, and it is the first
thing a reader should check.

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
| Concurrent positions | **5**, slots reopen on exit; chronological, ties alphabetical | 3a amendment 1 (e), as Entry 11 §D.3 ruled |
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
