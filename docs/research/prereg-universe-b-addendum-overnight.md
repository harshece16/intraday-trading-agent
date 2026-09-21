# Addendum pre-registration — the overnight leg on universe B

**Written and committed before any universe B overnight data is computed.**
Directed by reviewer **Entry 7 §B.2**, which the original
`prereg-universe-b-replication.md` **did not cover**.

**Trial count: stays at 34.** Measurements only. Research looks **L27–L28**.

---

## Why an addendum was needed, stated plainly

Entry 7 §B asked for **one** pre-registration covering **two** measurements on
universe B:

1. `atr_pct` rank IC against open-to-close — **done**, pre-registered at
   `edd3471`, PASS at −0.0332 / t = −6.68.
2. **The 3c decomposition** — overall overnight and intraday means, plus
   quiet-minus-volatile spreads for both legs. **I omitted this.** My
   pre-registration covered only §B.1.

**The omitted data has not been looked at.** Verified before writing this,
not asserted: the cached universe B feature rows contain exactly
`{sym, target, atr_pct, from_high, from_low}` — no overnight field — and
`universe_b_replication.py` contains **zero** occurrences of "overnight" or
"prev". The previous-close price needed to compute an overnight return was
never even loaded into the row set.

So this is a genuine pre-registration of an unseen measurement, not a
retrofit. It requires a fresh download of universe B's daily bars, because
the cache cannot produce an overnight return.

---

## What runs

Universe B (113 F&O-eligible names outside the NIFTY 100,
`backend/data/universe_b.csv`, retrieved 2026-09-21), **selection dates
only** — sessions before `splits.HELD_OUT_START` (2026-01-02).
**Universe B's 2026 data is not touched**, per Entry 7 §B.

**Window: 8 years**, the same as follow-ups A, 3c and the §B.1 run.

Eligibility, the 252-bar warm-up, the ≥20-stock session minimum and the
corrected sign conventions are **identical to 3c**, whose helper functions
this reuses rather than re-implements.

### The two components, per stock-session

- **Overnight:** `(open_T − close_{T−1}) / close_{T−1}`
- **Intraday:** `(close_T − open_T) / open_T`

Both in basis points, both from the same daily source.

### L27 — unconditional means

Per session, the cross-sectional mean of each component; then the mean and t
across sessions. Universe A's figures, quoted now so neither can be selected
afterwards:

| Universe A (8y, 1,546 sessions) | Mean | t |
| --- | --- | --- |
| Overnight | +16.78 bp | +9.50 |
| Intraday | −6.94 bp | −2.80 |

### L28 — volatility-sorted spreads, and the pass rule

ATR% quintiles per session, identical construction to 3c §B. Report mean
overnight and intraday per quintile, and the **quiet-minus-volatile spread
for each leg** with its t across sessions.

> **PASS RULE, fixed before running (Entry 7 §B.2): the OVERNIGHT spread must
> have the same sign as universe A's and |t| > 2.**
>
> **The intraday spread is reported whatever it is, with no pass rule.**

Universe A's comparison points:

| Universe A spread (quiet − volatile) | Mean | t |
| --- | --- | --- |
| **Overnight** | **−13.83 bp** | **−9.79** |
| Intraday | +7.40 bp | +2.38 |

---

## The 4-year sub-window, and an honesty note about it

Entry 7 §B asks for the most recent 4-year sub-window reported alongside as a
**secondary line, declared now so it is not a later choice**.

**Declared for L27 and L28**: the same statistics recomputed on selection
sessions from the most recent 4 years only. Secondary, no pass rule.

**But it cannot be a clean pre-declaration for the already-run §B.1 IC.**
That measurement was run and its 8-year result seen before Entry 7 arrived.
If the 4y line is reported for `atr_pct`'s IC it will be **labelled
post-hoc**, because that is what it is. Declaring it now does not retroactively
make it pre-registered, and pretending otherwise is exactly the kind of
bookkeeping this process exists to prevent.

---

## Costs

Entry 6 §D still binds: **anything expressed net of cost on universe B uses
double slippage**, a **22.60 bp** round trip rather than 16.60 bp.

**Overnight returns are not comparable to that bar at all.** Capturing an
overnight leg means holding through the close, which is cash *delivery*, a
different cost model entirely — STT on both legs, higher stamp duty, a
per-sell depository charge. Entry 7 §D.2's cost sheet exists to establish
those figures, and **no overnight number in this addendum will be compared
against a cost bar until that sheet is built.**

---

## What a pass would and would not mean

**Would:** the overnight/intraday split is a property of the wider Indian
cross-section, not of the NIFTY 100 — the same strengthening the §B.1 pass
delivered for the intraday leg.

**Would not:**

- **Make anything tradable by this system.** Nothing here holds overnight.
- **Escape survivorship bias.** Today's F&O-eligible list applied to history,
  and mid-caps leave that list more often than large-caps, usually after
  falling. On a volatility sort this runs in the direction that flatters the
  finding — and Entry 7 §D.1's index-level measurement exists precisely
  because neither universe answers it.
- **Be out-of-time.** Same period, different stocks.

**A failure is equally informative** and will be reported as plainly: it
would mean 3c's mechanism is specific to large-caps.
