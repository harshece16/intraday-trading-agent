# Pre-registration — universe B replication of the step 2 volatility result

**Written and committed before the measurement code existed.**
Directed by reviewer **Entry 6 §C.1**.

**Trial count: stays at 34.** This is a measurement, not a strategy. It sizes
no position and runs no backtest. Logged as research look **L26**.

**Daily data only. No Kite calls.** Entry 6 §C.2 requires the user's explicit
approval before any 5-minute download for universe B, and none is requested
here.

---

## Why this is the strongest test available

Entry 6 §A makes the point that decides this: **names outside the NIFTY 100
are a cross-section no test in this project has ever seen.** The held-out
window is merely *later in time on the same 100 stocks*; universe B is
**different stocks over the same period**.

For a cross-sectional ranking result, a fresh cross-section is a more
demanding replication than a fresh date range, and it does not consume the
held-out window. **The held-out look remains unspent regardless of this
outcome.**

---

## Universe B

| | |
| --- | --- |
| Source | `https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv` — the official NSE F&O market-lots file |
| Construction | "Derivatives on Individual Securities" block (210 symbols) **minus** the 100 NIFTY 100 names |
| **Size** | **113 symbols** |
| Saved at | `backend/data/universe_b.csv`, with `universe_b.README.md` |
| Retrieved | 2026-09-21 |

The official F&O list was obtained, so **the NIFTY 200 fallback in Entry 6 §B
was not needed**.

F&O-eligible was chosen (per §B) because those names are liquid, shortable
intraday, and have stock futures — which matters for any later cost model.

---

## The test

**Identical to step 2's, in every respect that could be varied:**

| | |
| --- | --- |
| Test | Daily cross-sectional **Spearman rank IC**, mean and t **across sessions** |
| Target | **Open-to-close** return, same daily source |
| Split | **Selection only**, sessions before `splits.HELD_OUT_START` (2026-01-02) |
| **Window** | **8 years**, the same as the step-2 follow-ups and 3c |
| Warm-up | **252 prior daily bars** per tested stock-session; shortfalls dropped and counted |
| Eligibility | `scanner.tradability_exclusion()`, as in step 2 |
| Minimum | 20 eligible stocks per session |
| Sign | `atr_pct` sign **+1**, as corrected in amendment 5 |

**The window is stated explicitly because failing to pre-register it is
exactly what went wrong between step 2 and its follow-ups.** Eight years, not
four, and not chosen after seeing anything.

### Primary test — one look, one feature

**`atr_pct`.** It is the only feature that qualified under amendment 8
(survived BH, passed the tradable-target gate, and is the control in the
partial-IC test rather than a casualty of it).

> **Pass rule, fixed before running (Entry 6 §C.1): the universe B rank IC
> must have the SAME SIGN as universe A's and |t| > 2.**

Universe A's comparison points, both quoted so neither can be picked
afterwards:

| Universe A window | Mean IC | t |
| --- | --- | --- |
| **8y, 1,546 sessions** (the matching one) | **−0.0388** | **−7.32** |
| 4y, 561 sessions (step 2 as registered) | −0.0558 | −6.13 |

### Secondary — reported, with NO pass rule

Labelled exploratory, not part of the pass criterion, and **not** added to
any multiple-comparison family:

- `from_high` and `from_low` rank ICs. They survived BH on selection and were
  disqualified only by the partial-IC gate, so whether that verdict holds on
  a fresh cross-section is informative.
- The **partial ICs** (`from_high | atr_pct`, `from_low | atr_pct`,
  `atr_pct | both`). Universe A's conclusion was "one factor, not three". A
  fresh cross-section is the natural place to check that, and it is the
  single most load-bearing claim in Entry 4's review.

**A secondary result cannot rescue a failed primary, and will not be
presented as if it could.**

---

## Costs, fixed now (Entry 6 §D)

Any universe B figure expressed in money or R uses **double the configured
slippage per leg**, because names outside the NIFTY 100 have wider spreads
and no measured figure from this project's own fills exists.

| | Universe A | **Universe B** |
| --- | --- | --- |
| Slippage (round trip) | 6.00 bp | **12.00 bp** |
| Charges (round trip) | 10.60 bp | 10.60 bp |
| **Round-trip total** | **16.60 bp** | **22.60 bp** |

**This is not tunable afterwards.** If a bp spread is reported, 22.60 bp is
the bar it is compared against.

---

## Memory (Entry 6 §E)

Daily bars only — no 5-minute candles — so the footprint is far below the
null test's. Even so, universe B is downloaded and processed **on its own**;
universe A's bars are never loaded in the same process.

---

## What a pass would and would not mean

**Would:** the volatility–intraday-return association is a property of the
Indian large/mid-cap cross-section, not an artefact of the 100 names step 2
happened to look at. That is a genuine strengthening.

**Would not:**

- **It would still not be tradable.** Universe A's spread is 8.11 bp against
  16.60 bp of cost; universe B's bar is **22.60 bp**, which is higher. A
  replication of the *statistic* does not change the *economics*, and the
  economics are what the project needs.
- **It would not remove survivorship bias** — it would arguably worsen it.
  This is today's F&O-eligible list applied to history, and mid-caps enter
  and leave that list more often than large-caps, usually leaving after
  falling. On a volatility sort that distortion runs in the direction that
  flatters the finding.
- **It is still not out-of-time.** Same period, different stocks. Any
  market-wide regime effect over 2019–2026 is shared by both universes.

**A failure would be equally informative** and will be reported as plainly:
it would mean the step 2 result is specific to the NIFTY 100 cross-section,
which after 34 trials and 25 looks is the kind of finding this process exists
to produce.
