# Pre-registration — 3a, opening-range breakout

**Written and committed before any 3a measurement exists.**
**NOT RUN.** Entry 7 §E requires reviewer approval of this pre-registration
before it executes. Nothing in it has been measured.

**This costs one strategy trial: 34 → 35 on execution**, not on writing.

---

## Why this is worth one trial when the cross-sectional signals were not

Entry 7 §A establishes that for an **unconditional hold-to-close**
cross-sectional signal, edge and cost are both basis points over the same
stop, so `edge/friction` is invariant to stop width and no redesign helps.
`atr_pct` returns 0.49× its cost in universe A and 0.26× in universe B, and
widening the stop cannot move either.

**3a is not that.** It is an **event-conditioned entry**: it only trades a
stock on a session where a specific thing happened, so its per-trade gross
return is **not knowable in advance from the cross-sectional figures** and
has to be measured. That is what earns it a trial.

**What it must beat, stated before running:**

| Hurdle | Value | Source |
| --- | --- | --- |
| Round-trip cost, cash intraday, ₹33,000 | **16.60 bp** | `costs.py`, §D.2 sheet |
| Intraday drift against a long book | **−6.42 bp/day** | §D.1, index-level, survivorship-free |
| `friction_R < 0.15R` (necessary, not sufficient) | — | Entry 5 §C, retained |

> **PASS RULE, fixed now: mean NET return per round trip must be positive
> with t > 2 across sessions, where net is gross minus the full 16.60 bp.**
> Reported in **bp and in R**, gross and net, as §A requires.

A design that clears `friction_R < 0.15R` but not the bp hurdle **fails**.
That was the confusion in Entry 5 §C which §A corrected, and it is not
repeated here.

---

## The hypothesis

**Opening-range breakout.** Price that establishes a range in the first
fifteen minutes and then breaks out of it continues in the breakout
direction far enough to cover 16.60 bp.

This is the most-documented intraday pattern in the literature and the one
the current agent does *not* implement — it enters on candlestick patterns
against support/resistance, which §51 measured at no edge.

---

## One variant only (Entry 5 §C, Entry 7 §A)

Two stop definitions were plausible. **The opening range is chosen; daily ATR
is not run.** Reason, stated in advance: the range is the structure the
signal is defined by, so a stop outside it is the natural invalidation level,
and it adapts to the session rather than to the previous fortnight. Daily ATR
would be a second variant of the same hypothesis and is therefore excluded by
the one-variant rule, not by preference after seeing a result.

| Parameter | Value | Why this and not another |
| --- | --- | --- |
| Opening range | **09:15–09:30** (three 5-min bars) | Standard definition; also the window §B of the tradable target already excludes |
| Entry | First 5-min **close** beyond the range, from **09:30** | A close, not a touch — avoids the same intrabar ambiguity the null diagnostic found in stop fills |
| **Direction** | **Both long and short** | §D.1: a long-only intraday book starts −6.42 bp behind. §A requires symmetry. |
| Stop | Opposite side of the opening range | The signal's own invalidation level |
| Exit | **15:10 bar close**, or stop | Matches the tradable window used throughout; no near target, per §C |
| Entries per name per session | **1** | Entry 5 §C |
| Max concurrent positions | 5 | Matches the live engine's shape |
| Universe | **A** (NIFTY 100) | Entry 6 §C.3: 3a is registered on A; B is a replication only if A passes |
| Data | Kite 5-min cache, **already downloaded** | No new Kite calls; no user approval needed |
| Period | **Selection only**, before 2026-01-02 | Held-out stays unspent |
| Costs | `config.COSTS`, full 16.60 bp | Not ZERO_COSTS |

**`friction_R` for this design**, computed in advance as §A requires:

```
opening-range width, median, to be reported before the result
friction_R = 16.60 bp / range_width_bp
```

**If the median range width is under 111 bp, `friction_R` exceeds 0.15 and
the design is withdrawn before the statistics are read.** That check runs
first and its outcome is reported either way.

---

## What is measured

Per trade: entry time, side, entry and exit price, gross and net in **bp and
in R**, exit reason. Then across sessions:

1. **Mean net bp per round trip**, t across sessions — **the pass rule**.
2. Mean gross bp, so the cost share is visible.
3. Mean net R and gross R.
4. **By side.** §D.1 predicts longs do worse; if the result is carried
   entirely by shorts that is a different finding from a symmetric one.
5. Trade count and trades per session — power, and whether it is tradable at
   all at one entry per name.
6. Exit mix: stop / 15:10 timeout.

**Both halves of the selection period reported separately**, per the
project's standing rule, and neither half is allowed to carry the result
alone.

---

## Pass / fail

**PASS:** mean net bp per round trip **> 0 with t > 2**, and the sign holds
in **both halves**.

**FAIL:** anything else, including a positive gross with a negative net.
That case is expected and is not a partial success — it is the same finding
the project has already made four times.

**No parameter is tuned after seeing a result.** If 3a fails, the recorded
outcome is that opening-range breakout on the NIFTY 100 at 5-minute
resolution does not clear 16.60 bp. It is **not** an invitation to try
09:15–09:45, or a 2×ATR stop, or a filter.

---

## Counted as a trial

**This is trial 35**, logged in `trials.md` on execution. It is a strategy
variant with entries, stops, sizing and a backtest — categorically unlike the
29 research looks, and the Deflated Sharpe denominator moves.

---

## What it cannot establish

- **One variant is not a search.** A failure does not prove no
  opening-range design works; it establishes that this one, pre-specified,
  does not.
- **Selection sample only.** A pass would earn the held-out look that Entry 7
  §C reserved for exactly this kind of hypothesis — it would **not** be a
  result on its own.
- **Survivorship bias** applies as everywhere: today's NIFTY 100 on history.
- **The Kite cache starts 2024-09-20**, so 3a's sample is ~316 sessions, far
  shorter than the daily-bar work. Power is correspondingly lower and the
  detectable effect size will be reported alongside the result.
