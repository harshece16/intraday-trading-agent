# Pre-registration — does universe B clear the reward:risk gate more often than universe A?

**Written and committed before the measurement code existed.**
Requested by the user on 2026-09-22 ("go ahead for universe expansion").

**Trial count: stays at 35.** This is a measurement, not a strategy. It sizes
no position, places no order and runs no backtest. Logged as research look
**L34**.

**Daily data only. No Kite calls.** Entry 6 §C.2 requires the user's explicit
approval before any 5-minute download for universe B, and none is requested
here.

**Selection window only.** Sessions strictly before `splits.HELD_OUT_START`
(2026-01-02). The held-out window is not touched and remains unspent.

---

## Why this measurement, and why now

The live paper engine has produced **zero entries in five consecutive
sessions**. The activity log names the blocker directly and repeatedly: on
2026-09-22 the checklist evaluated 28,300 setups in 24 hours and **536 of the
near-misses were blocked by reward:risk alone** — more than volume (87),
pattern (15) and Dow (11) combined. Only **9.6%** of evaluations reached
RRR ≥ 1.5; the median RRR was **−0.16**.

The rejections are not marginal-conviction setups. Observed live today:

| Time | Setup | Score | Geometry | RRR after costs |
| --- | --- | --- | --- | --- |
| 10:32:22 | Breakdown (short) | bear 13.5 / 6 | target 995.70, stop 1000.90 | **0.00** |
| 09:35:39 | Breakdown (short) | bear 15.5 / 6 | target 3060.70, stop 3077.00 | **−0.12** |
| 10:35:41 | Breakdown (short) | bear 9.0 / 6 | target 390.20, stop 390.81 | **−0.38** |

The setups are strong. The distance to the next structural level is smaller
than the round trip costs to get there. This is the 16.60 bp friction from
phase 2 arriving one trade at a time.

**The hypothesis the user is proposing** is that a wider universe fixes this:
mid-caps have higher `atr_pct`, so target-to-stop distances should be wider
in percentage terms and should clear the gate more often.

**The counter-hypothesis, fixed here before any number exists,** is that
mid-cap spreads widen at least as fast as mid-cap ranges, so the gate gets no
easier — and under Entry 6 §D's doubled slippage it gets harder.

Both are plausible. Neither has been measured in this project. This look
decides which, for the price of one daily-bar pass and no trial.

---

## What this measurement is NOT

It is **not** a replication of the live 5-minute checklist. The live gate uses
intraday structure, candlestick patterns, VWAP and volume; this uses daily
bars. It cannot and does not claim to reproduce the live pass rate.

It is a **difference in fractions under one identical rule**. The same
geometry rule is applied to universe A and universe B over the same sessions,
and only the *difference* between them is interpreted. A proxy that is biased
is acceptable here **provided the bias is the same on both sides**, which it
is by construction — the rule does not read the universe label.

Stating this now so that a favourable result cannot later be re-described as
"universe B passes the live gate more often". It cannot show that.

---

## Universes

| | |
| --- | --- |
| **A** | `backend/data/nifty100.csv` — 100 names, today's membership applied to history |
| **B** | `backend/data/universe_b.csv` — 113 F&O-eligible names outside the NIFTY 100, retrieved 2026-09-21 |

Both carry survivorship distortion from today's membership applied to
history, and per Entry 6 §B that distortion is **likely larger in B**. A
result that favours B by less than a plausible survivorship margin is not a
result. Recorded now so it cannot be waved away afterwards.

---

## The geometry rule, fixed now

For each symbol and each session `t` in the window, on daily bars only:

- **Warm-up**: 252 bars. Sessions with fewer are skipped.
- **Entry**: `close[t]`.
- **ATR**: `atr(14)` at `t`.
- **Lookback for structure**: `N = 20` sessions strictly before `t`.
- **Long candidate**: `target` = highest high in the lookback that is above
  entry; `stop` = lowest low in the lookback that is below entry.
- **Short candidate**: `target` = lowest low below entry; `stop` = highest
  high above entry.
- **Validity**: both levels must exist, and `|entry − stop|` must be
  **≤ 1.5 × ATR**. Candidates failing either are skipped, not counted as
  failures. (A stop further than 1.5 ATR is not a stop the live engine would
  place.)

Every constant above — 252, 20, 1.5 — is fixed here and will not be varied.
If the code needs a different value to run at all, that is an amendment,
recorded with both the old and new value and the reason, before the run.

### Reward:risk after costs

```
reward_bp = |target − entry| / entry × 10_000  −  round_trip_bp
risk_bp   = |entry − stop|   / entry × 10_000  +  round_trip_bp
rrr       = reward_bp / risk_bp
```

Costs are charged **against** the trade on both sides — the target is reached
net of the round trip, the stop is hit after paying it. This is the same
direction the live engine applies them.

### Costs, per Entry 6 §D

| Universe | Round trip | Basis |
| --- | --- | --- |
| **A** | **16.60 bp** | measured in phase 2 (charges + 3 bp/leg slippage) |
| **B** | **22.60 bp** | Entry 6 §D — **double the configured slippage per leg**, charges unchanged |

The 22.60 bp figure is the one already used in `universe_b_replication.py`.
It is an assumption, not a measurement, and is stated with every universe B
number. **It will not be tuned after seeing the result.**

---

## Primary test — one look

**Quantity**: `p_A` and `p_B`, the fraction of valid candidates with
`rrr ≥ 1.5`, pooled across symbols and sessions, computed separately per
universe over the **same session dates**.

**PASS RULE, fixed before running:**

> `p_B > p_A` **and** the two-proportion z-statistic **z > 2**.

**One run.** A re-run is legitimate only for a crash before any statistic is
seen, or a declared bug fix with both runs recorded.

### The falsification branch, fixed now

Per the phase-2 protocol, the null is not the only way this fails, and the
alternatives mean different things:

1. **`p_B > p_A`, z > 2** — PASS. Expansion has a measured basis. It licenses
   the next step, not the live change itself (see below).
2. **`p_B ≈ p_A`** — null. Expansion is neutral on the binding constraint; it
   would add names and candidates without improving the gate.
3. **B's raw geometry is wider but `p_B ≤ p_A`** — the mechanism the user
   expects is *real and insufficient*: mid-cap ranges are wider, and costs eat
   the whole gain. **This is a worse fact for expansion than the plain null**,
   because it forecloses the obvious remedy of hunting for wider-range names.
4. **`p_B < p_A`, z > 2** — expansion is actively harmful at this trade
   structure.

To make branch 3 decidable, the **median `reward_bp` and median `risk_bp` are
reported per universe** alongside the fractions, and they are reported
whatever the primary result is.

### Secondary, reported with NO pass rule

- `p_A`, `p_B` at the **zero-cost** gate (`round_trip_bp = 0`), to separate
  geometry from friction.
- Per-universe distribution of `rrr`: min, median, mean, 90th percentile.
- Candidate counts and skip counts, so the denominators are auditable.
- Long/short split of the pass fraction.

These are descriptive. They are not tested, not corrected for multiplicity,
and **cannot rescue a failed primary**.

---

## Memory (Entry 6 §E)

Symbols are downloaded and reduced in **chunks of 40**, the same as
`universe_b_replication.py`. Per-symbol candidate rows are accumulated as
counters, never as a full candle set. **Both universes' bars are never held in
memory at once** — universe A is processed to completion and released before
universe B is loaded.

---

## What a pass would and would not mean

**Would**: justify Entry 6 §C.2's next step — extending the 5-minute cache to
universe B so the *live* gate, not this daily proxy, can be measured there.
That download needs a live Kite session, is rate-limited, and must not compete
with the running engine during market hours. It needs the user's go-ahead
separately.

**Would not**: justify adding universe B to the running paper engine's
scanner. Entry 6 §F makes that a separate decision, and the phase-2 verdict
still stands — **there is no measured edge at this trade structure**, and a
wider universe does not create one. Expansion changes how many candidates
clear a gate; it does not change that entries were indistinguishable from a
matched random-entry null.

A pass here means the *gate* is less binding on B. It says nothing about
whether trades taken through that gate make money.

---

## Known defect this measurement sits on top of

`backend/costs.py:11` applies a single global `slippage_pct` to every symbol,
and `backend/config.py:332` sets it to 0.03% per leg with the comment *"a
rough estimate, not measured"*. The live engine therefore models mid-cap
slippage as if it were large-cap slippage.

Entry 6 §D's doubling is a research-side workaround, applied only in research
scripts. **The live path has no such correction.** If universe B is ever added
to the live scanner, the RRR gate would be systematically optimistic on
exactly the new names. Filed separately; not fixed by this measurement.
