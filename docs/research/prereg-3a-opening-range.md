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
| Intraday drift against a long book | **−6.42 bp/day** | §D.1, **index-level, 2005–2025** (not survivorship-corrected; −6.73 bp on universe A's own window, L30) |
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

---

# Amendment 1 — Entry 8 §D (a–k)

**Committed before any 3a code is written or run.** The reviewer approved the
design as trial 35 and required these specifics fixed first. All defaults are
adopted as given; each deviation, if any, is stated here rather than
afterwards. **There are no deviations.**

### (a) Unit of the test

The original text said "mean net per round trip, t across sessions", which
conflates two units. **Fixed:**

> **Primary statistic:** per session, the mean net bp of that session's
> trades. The pass statistic is the **mean and t of those session means**,
> over sessions with **at least one trade**.
>
> **Secondary, no pass rule:** the pooled per-trade mean net bp.

### (b) Fill rule

**Signal** = the first 5-minute bar, from the **09:30** bar onward, that
**closes** beyond the opening range.
**Entry** = the **open of the next bar**. **Never the signal bar's close.**

### (c) Stop fill

- Stop touched intrabar → fills at the **stop price less modelled slippage**.
- A bar that **opens beyond** the stop → fills at **that bar's open**.
- If the **entry bar itself** touches the stop → **the stop is taken**.

### (d) Last entry time

**No signal bar after 14:30.** A signal at 14:30 enters at 14:35 and holds to
15:10 — 35 minutes. This keeps a five-minute hold out of the sample.

### (e) The five-position cap

When more than five names signal: **chronological by signal bar; ties within
the same bar broken by symbol, alphabetically.** Explicitly **not** by range
width, volume, or anything that is itself a signal.

**Secondary, no pass rule:** the **uncapped all-signals** mean.

### (f) R definition, and the pre-flight

**R = entry price to stop price, per trade.**

The **pre-flight check** uses the **median opening-range width in bp across
all eligible stock-sessions** — computable without reading any return.

> **A withdrawal does NOT count as a trial**, because no return is read. It
> is logged in `trials.md` as **withdrawn**, and **the design is not
> re-registered with a different range window.**

### (g) Halves

Selection sessions in the Kite cache, **split at the median session date**,
fixed now and computed before the run.

### (h) Sizing

**Fixed ₹33,000 notional per trade.** Basis points are the primary unit; R is
derived.

### (i) Power

Before the statistics are read, report **the smallest mean net bp detectable
at t = 2** given the session count, from the realised per-session dispersion.
A null then reads as *"no edge larger than X bp"* rather than "nothing found".

### (j) Code ordering

**The 3a script's commit must postdate this amendment commit.** Both hashes
are cited in the results file.

### (k) Harness

**`backtester.run_backtest()`**, the same harness as every other result here.
Its measured bias is **≈ −0.05R pessimistic** — and, per the null diagnostic,
that bias is **not a constant**: it is driven by side mix (longs −0.0947R,
shorts +0.0351R), so a direction-symmetric design carries less of it than the
59.7%-long strategy that figure was measured on. Recorded, not corrected for.

### Also carried (Entry 8 §B.7, §B.9)

- The **−6.42 bp** intraday drift is cited as **"index-level, 2005–2025"**
  — and now also **−6.73 bp on universe A's own window (L30)**. It is **not**
  a survivorship-corrected version of −6.94.
- **`costs.py`'s rates are unverified** against the broker's current tariff.
  That caveat sits under 3a's 16.60 bp hurdle and will be repeated in the
  results file.

### Run discipline

**One run.** A crash **before any statistic is seen** may be re-run and
recorded. Nothing else.

---

# Amendment 2 — a conflict inside amendment 1, found before writing code

**Committed before any 3a code exists.** Raised rather than resolved
silently, because it is a deviation from a clause I committed to one commit
earlier.

## The conflict

**Amendment 1 (k)** commits 3a to `backtester.run_backtest()`, "the same
harness as every other result here".

**Amendment 1 (b)** requires: *"Entry = open of the NEXT bar. **Never the
signal bar's close.**"*

**The harness does exactly what (b) forbids.** `backend/backtester.py:249`:

```python
_open_position(pos, side, bar["close"], qty, atr_val, costs_cfg, risk, ...)
```

It enters at `bar["close"]` — the close of the very bar that produced the
signal. There is no parameter to defer entry by one bar.

This was found by reading the harness before writing 3a, not assumed either
way.

## Resolution: (b) wins, (k) is amended

**(b) is a scientific requirement; (k) was a bookkeeping note.** Entering at
the close of the bar that just told you to enter is not executable — the
signal is only known once that bar has closed, at which point the close has
passed. The reviewer's emphasis ("Never") is on (b).

> **3a is therefore implemented as a self-contained measurement with the
> exact fill rules in (b) and (c), and does NOT use
> `backtester.run_backtest()`.**

## What this costs, stated plainly

1. **The −0.05R harness-bias figure does not transfer.** It was measured on
   `run_backtest()` and 3a does not use it. 3a's results carry **no harness
   bias estimate**, and none will be asserted.
2. **3a's fills are not directly comparable** to §51's −0.356R or to the null
   test, which used the shared harness with its close-fill convention. Any
   comparison to those numbers must be flagged.
3. **The benefit is that (b) and (c) are implemented exactly and verifiably**,
   rather than assumed to match a shared harness that, as it turns out, they
   do not.

## What is unchanged

Everything else in amendment 1 stands: the unit (a), the stop rules (c), the
14:30 cutoff (d), the five-position cap and its tie-break (e), R and the
pre-flight (f), the halves (g), ₹33,000 sizing (h), the power statement (i),
and the code-ordering requirement (j). Costs remain `config.COSTS` at the
full 16.60 bp, with `costs.leg_cost()` and `costs.apply_slippage()` — the
project's own cost functions — applied directly.

**Amendment 1 (c)'s stop rules happen to match the harness's** (stop price on
an intrabar touch, the bar's open on a gap-through), which is stated because
it means the deviation is confined to the entry fill.

---

# Amendment 3 — Entry 9 (external reviewer), reconciling with Entry 8 §D

**Committed before any 3a code exists** (`git ls-files` shows no 3a script;
the inbox entry is `ad7b05c`). **Where this amendment differs from the
original text or from amendments 1–2, it takes precedence.** Nothing has been
measured.

## 3.1 The hypothesis is restored to the original brief

> **Opening-range breakout on stocks with unusually high relative volume.**

The original pre-registration dropped the relative-volume condition. It is
part of the hypothesis, **fixed in advance, not a tie-break**.

**Relative volume, computed at 09:30 from information available at 09:30:**

```
or_vol(name, s)  = volume of the 09:15 + 09:20 + 09:25 bars on session s
rel_vol(name, s) = or_vol(name, s) / mean( or_vol(name, s') for the 14 most
                   recent prior cached sessions s' of that name )
```

- **Eligible** on session *s*: the name has all three opening-range bars on
  *s* **and** 14 prior cached sessions each with all three bars. A name with
  fewer is ineligible that session; nothing is imputed. **The first 14
  sessions of the cache therefore produce no trades.**
- **Only the top 20 eligible names by `rel_vol` are tradable that session.**
  A tie at rank 20 is broken by symbol, alphabetically.
- **Within that set, Entry 8 (e) stands unchanged:** five-position cap,
  chronological by signal bar, ties within a bar alphabetical.

**Order of operations, fixed:** eligibility → top-20 by `rel_vol` → signal
(amendment 1 b) → per-trade friction rule (3.2) → five-position cap.

**The primary statistic and the pass rule apply to this set only:** top-20,
friction rule applied, capped. Unit as amendment 1 (a).

**Two secondary lines, no pass rule, descriptive only:**

1. the **uncapped** mean over all signals **in the top-20 set**;
2. the **uncapped** mean over **all 100 names with no relative-volume
   filter**.

Both have the per-trade friction rule applied, so they are comparable with
the primary line. **They are not further trials, and neither can justify a
follow-up variant** — not "drop the filter" if line 2 looks better, and not
"raise the cap" if line 1 does.

## 3.2 The median-width withdrawal is replaced by a per-trade rule

Amendment 1 (f)'s pre-flight withdrawal ("median range width under 111 bp →
design withdrawn") **is removed.** In its place:

> **Skip any trade for which `16.60 / stop_bp > 0.15`** — that is,
> `stop_bp < 110.67`, where `stop_bp = |entry − stop| / entry × 10,000`,
> entry is the next-bar open (amendment 1 b) and stop is the opposite side
> of the opening range.

- **R is unchanged:** entry price to stop price, per trade (Entry 8 f).
- The rule is executable: `stop_bp` is known at the moment of entry.
- A skipped candidate **takes no cap slot**, and the name is **not
  re-entered** that session (one signal per name per session stands).
- **Reported before any return is read:** the number of candidate trades and
  the number this rule removes — for the top-20 set and for the all-100
  line — with the median opening-range width alongside as description only.
- **The rule is not loosened** — not to 0.20, not "0.15 on the median" — for
  any reason, including too few trades.

## 3.3 "Untestable at this frequency" — the threshold, fixed now

Entry 9 requires that if too few trades remain for the power statement (i)
to detect a plausible effect, 3a is reported **untestable**, not rescued. It
does not define "plausible". **That definition is mine, made here before any
number exists, and is flagged for the reviewer to overrule:**

| Check | When | Threshold | Consequence |
| --- | --- | --- | --- |
| **Count** | pre-flight, **no return read** | fewer than **60 sessions** with ≥ 1 surviving capped trade | **Untestable. Not run.** No return is read, so **not a trial**; logged in `trials.md` as *untestable — withdrawn at pre-flight*. |
| **Power** | after the run, from the realised dispersion | `MDE = 2 × sd(session means) / √n_sessions` **> 16.60 bp** net | The run is spent and **counts as trial 35**. Everything is reported; the verdict is **"untestable at this frequency: no edge larger than MDE bp can be excluded or confirmed"**, not pass and not fail. |

Why 16.60 bp: a **net** edge that size means a gross edge of twice the round
trip per trade. An opening-range effect larger than that on NIFTY 100 names
is not plausible, so a test that cannot see anything smaller cannot see
anything that could be there.

A **PASS** still requires everything in the original pass rule: net > 0,
t > 2 on session means, sign holding in both halves (amendment 1 g).

## 3.4 What stands exactly as written in Entry 8 §D / amendments 1–2

Next-bar-open fills (b) · stop fills (c) · **no signal bar after 14:30** (d)
· halves split at the median session date (g) · **fixed ₹33,000 notional**
(h) · power statement (i), now with 3.3's threshold · **code committed after
the amendment**, both hashes cited (j) — *the amendment hash to cite is now
this commit, the last one before code* · self-contained implementation with
no harness-bias figure asserted (amendment 2). One run.

## 3.5 Sequence from here

Reviewer reviews this amendment → **STOP** → **3a runs only after the user
confirms.** Then: code, pre-flight reported on its own, the single run,
`results-3a`, stop for review.
