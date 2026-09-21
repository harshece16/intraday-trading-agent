# Pre-registration — 3c, the overnight vs intraday decomposition

**Written and committed before the measurement was written or run.**
**Selection split only.** Governed by reviewer Entry 4 §E and Entry 5 §C.

**Trial count: stays at 34.** 3c is a **measurement**, not a strategy. It
sizes no position, sets no stop and runs no backtest. Logged as research
looks **L23–L25**.

---

## Declared motivation, before any result

> **This hypothesis was motivated by step 2's selection-sample result.**

Step 2 found that daily ATR% predicts *negative* open-to-close returns
(−0.0388R over 1,546 sessions, t = −7.32; −0.0416 on the tradable Kite
target). The standard explanation is that volatile stocks earn their return
**overnight** and give part of it back **intraday**. That is 3c's territory,
and 3c exists to test the mechanism rather than re-observe the association.

**Consequence, stated now:** because the idea came from the selection sample,
**a selection-sample confirmation is not evidence.** Only data outside step
2's sample can confirm it. That is Entry 4 §E's rule and it is binding.

---

## An unresolved conflict I am not deciding alone

Entry 4 §E says only data outside step 2's sample counts as confirmation for
3c. Entry 4 §D reserves **one** held-out look for `atr_pct`.

**These compete for the same scarce resource.** Step 2's feature and 3c's
mechanism are the same volatility factor. Looking at the held-out period for
3c spends part of what makes the step-2 look informative, and vice versa.

**I am not resolving this.** This pre-registration covers **selection-split
measurement only** (§A–§C below). The held-out component (§D) is specified so
it is fixed in advance, but **it does not run until the reviewer says which
question the held-out period is spent on.** Options, without a
recommendation beyond the note in §D:

1. Spend it on step 2's `atr_pct` IC as already planned, and 3c stays
   descriptive on selection data only.
2. Spend it on 3c's decomposition, and step 2's look is forfeited.
3. Spend it on a single combined test — **only if the reviewer specifies
   that test now**, before either result is seen.

---

## The measurement

Universe, eligibility, the 252-bar warm-up and the corrected sign
conventions are **identical to step 2** (`prereg-step2-feature-ic.md`), so
results are comparable without re-deriving anything.

**Window:** the selection split, using the **8-year** history (1,546 usable
sessions, 2019-10-03 → 2026-01-01). Stated explicitly this time because
failing to pre-register the window is exactly what went wrong between step 2
and its follow-ups.

### Two return components, per stock-session

- **Overnight:** `(open_T − close_{T−1}) / close_{T−1}`
- **Intraday:** `(close_T − open_T) / open_T`

Both from the same daily source, so they are consistent with each other and
with step 2's target. The intraday leg is the one a day strategy could
capture; the overnight leg is not capturable by an intraday agent and is
measured to explain, not to trade.

### §A — the unconditional decomposition (L23)

Per session, the cross-sectional mean of each component in bp, then the mean
and t across sessions. Reports whether the index-level return over this
sample is earned overnight or intraday.

### §B — the volatility-sorted decomposition (L24, Entry 4 §E's requirement)

Per session, sort eligible stocks into **ATR% quintiles** (same construction
as step 2 §C). For each quintile report, in **bp**:

- mean overnight return
- mean intraday return
- their sum

with the **bottom-minus-top quintile spread for each component** and its t
across sessions.

**The prediction this tests, fixed now:** if the "volatile stocks earn
overnight and give it back intraday" story is right, then across quintiles
**overnight return rises with ATR% while intraday return falls**, and the
intraday spread reproduces step 2's ATR% effect.

**What would falsify it:** the intraday component falls with ATR% but the
overnight component does *not* rise. That would mean volatile stocks simply
lose money intraday without an overnight compensation — a different and
worse fact, since it implies no mechanism, only a drift.

### §C — the same on the tradable Kite target (L25)

Repeat §B with intraday defined as the **09:20 bar open → 15:10 bar close**,
on the Kite overlap (316 selection sessions). This is the only version a
strategy could act on, and step 2 already showed it retains 0.77× of the
daily-bar effect.

### §D — held-out, SPECIFIED BUT NOT RUN

If and only if the reviewer directs it: repeat §C on sessions from
2026-01-02, one look, reporting the intraday quintile spread with the same
sign and **|t| > 1.5**. **Not run under this pre-registration.**

---

## Entry 5 §C's friction constraint, applied

§C requires every design to state expected friction up front, as
`friction_R = round_trip_bp / stop_bp`, and forbids pre-registering anything
above **0.15R**.

**3c is a measurement and has no stop, so the constraint does not gate it.**
Stating the arithmetic anyway, because it governs whatever 3a/3b build on
this:

| Design | Round trip | Stop | friction_R |
| --- | --- | --- | --- |
| **The current agent** | 17 bp | 42 bp (5-min ATR) | **0.40R** — far over the bar |
| A daily-ATR stop | 17 bp | ~150 bp | **0.11R** — passes |
| An opening-range stop | 17 bp | ~120 bp | **0.14R** — passes, barely |

> **The lever is the denominator.** No entry signal fixes 0.40R; a stop three
> times wider does. Any 3a/3b design must state its own figure from its own
> stop distance and clear 0.15R before it is pre-registered.

**And 3c already tells us whether that is worth attempting**, because §B's
intraday spread in bp is directly comparable to the 16.60 bp round trip.
If the spread does not clear cost at a wide stop either, the factor is dead
regardless of trade structure.

---

## What 3c cannot establish

- **It is not a strategy and produces no expectancy.** A quintile spread
  assumes equal weight on both tails, no stop, no sizing, no gate, and a
  short leg that may not be borrowable.
- **Selection-sample only** for §A–§C. By this pre-registration's own
  declared-motivation rule, none of it confirms anything.
- **Survivorship bias is at its worst on a volatility sort** — the volatile
  names that left the index are the ones missing, and this is a volatility
  sort of a volatility finding.
- **An overnight return is not free money.** It cannot be captured without
  holding overnight, which changes the cost model (delivery charges, not
  intraday), the risk profile and the entire mandate of the agent.

---

## Pass / fail

**There is no pass or fail.** 3c is descriptive. It reports the
decomposition, states plainly whether the mechanism holds, and compares the
intraday spread with round-trip cost. A null result — no relationship between
ATR% and either component — is a complete result and will be reported as one.
