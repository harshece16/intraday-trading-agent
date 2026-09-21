## Re: Entry 4 — A, B and C done. Your §A read is confirmed: one factor, and it does not clear cost. STOPPED before the held-out look.

**Current state as of 2026-09-21 09:20.** Amendments committed first
(`74541e5`), then A, B and C run on selection data only.
`results-step2-followups.md`. **The held-out look has not been taken** — §F
says stop here, and this is the stop.

### The headline

**Your §A read was right, and the partial-IC gate you asked for does the
work.** `ρ(atr_pct, from_low) = +0.43`. Controlling for `atr_pct`:
`from_high` falls to |t| = **1.05** and `from_low` to **1.90** — both under
the bar of 2 that amendment 8 fixed before the numbers existed. `atr_pct`
controlled for both keeps t = **−6.59**.

**Three survivors reduce to one qualifier**, so the held-out look would be a
single test at α = 0.05 rather than a Bonferroni family of three.

**And §C settles it.** Quintile spread **+8.11 bp** (t = 1.68) against a
round-trip cost of **16.60 bp**. The top-5/bottom-5 version is **+16.30 bp**
(t = 2.12) — **0.98× cost**. Your stated expectation holds: it does not
exceed round-trip cost in cash equities. Every quintile is also negative
outright (Q1 −0.08 bp to Q5 −8.55 bp), so **there is no long-only version**;
the whole effect is long-quiet against short-volatile.

### §B did not find what it was looking for, and that is worth saying

The tradable target (09:20 open → 15:10 close) **kept the effect**:
`atr_pct` retains 0.77×, `from_low` 1.06×, `from_high` 0.93×, all three still
|t| > 2. The effect does **not** live in the opening print, and the 18.55%
vendor disagreement was not driving it. §B was a real test that could have
killed the result and did not.

### A mistake of mine, and a finding that fell out of it

**I changed the history window without noticing.** Step 2 ran `YEARS = "4y"`;
the follow-ups script was written `"8y"`. The window was never
pre-registered — the prereg said only "far enough back that warm-up holds" —
so both comply, but A's sample is a **superset**: 1,546 sessions from
2019-10-03, of which **64% predate step 2's earliest session**, including
2020. For a volatility sort that is not a neutral extension.

I computed the raw ICs on A's own sample as the correct denominator (L21),
rather than compare partials against step 2's numbers. That produced a
finding I was not looking for:

> **`from_high` does not replicate.** Step 2: **+0.0258, t = +3.33** over 561
> sessions, through BH and Bonferroni. Over 1,546 sessions: **+0.0086,
> t = +1.73** — it would not have survived BH. That is a second, independent
> reason to doubt it, separate from the partial-IC argument.

`atr_pct` is also weaker on the long sample (−0.0388 vs −0.0558) while
staying strongly significant; the effect is larger in recent years. Regime or
noise is not established.

### One decision I need from you

**Do you want the held-out look spent on `atr_pct`?**

My recommendation is yes, **and not because I expect it to pass**. §C has
already shown it does not clear cost on selection data, so a held-out
confirmation cannot produce a tradable result. What it can do is settle
whether the association is real before 3c is pre-registered on top of it,
since your §E commits 3c to a volatility-sorted decomposition motivated by
exactly this. Keeping the look unspent for 3c is equally defensible. Your
call; I have not taken it either way.

### Still outstanding from Entry 3

**§A null diagnostic, §B friction decomposition, §C the README/#49 diff.**
Not started. **README §51 still carries the wrong "worse than a coin flip"
claim**, which I am flagging for the third time because it is the only item
here that leaves a known-false statement in the user's own documents. Say the
word and it moves ahead of everything else.

---

## Re: Entry 3 — step 2 run and reported; §A, §B and §C not started; two process failures on the record

**Current state as of 2026-09-21 08:05.** Step 2 is complete and written up
(`results-step2-feature-ic.md`, commit `4c503ad`). **Three of ten features
survive both BH at q=0.10 and Bonferroni.** The held-out look has **not** been
taken. Entry 4 has since been received and read; its §F order supersedes what
follows, and its §B/§D amendments are the next thing to commit.

### What is done

- **§D (step 2 amendments)** — all four committed before any measurement ran
  (`d165699`, `535a082`): per-session differences instead of pooled stock-day
  t-tests, trend as one test giving a family of ten, the 252-bar warm-up with
  history downloaded far enough back to hold from the first selection session,
  and the yfinance-vs-Kite data-quality gate.
- **Step 2 itself** — 561 usable sessions, 51,962 stock-sessions, 27,626
  dropped for warm-up. Survivors: `atr_pct` (t = −6.13), `from_low`
  (|t| = 5.23), `from_high` (t = +3.33). Full table, detectable effect sizes
  and all seven nulls are in the results file.
- **Trials** — L6–L16 logged; strategy trial count unchanged at **34**.

### What is NOT done

**§A (null diagnostic), §B (friction decomposition) and §C (the README /
issue #49 diff)** have not been started. Entry 3 §E put them after step 2, and
Entry 4 §F puts them after the step-2 block clears. Flagging it explicitly so
the ordering is a decision rather than a slip: **the verdict correction in §C
is still unmade, and README §51 still carries the wrong "worse than a coin
flip" claim.** If you would rather that were fixed before more measurement,
say so and it moves to the front.

### Three problems I found in my own step 2, and two process failures

Problems 1–3 are in the results file and Entry 4 §D has already ruled on them.
Two failures are worth stating here rather than only in a results file:

1. **The §D4 gate was coded as a report, not a halt.** The script printed
   r = 0.9832 and 18.55% > 25 bp, then ran the ten ICs unconditionally. So my
   judgement that agreement is adequate was made *after* seeing the results —
   the exact contamination the gate existed to prevent. I believe I would have
   passed 0.983 either way, but I cannot demonstrate it. Noted that Entry 4 §B
   takes part of this on the undefined threshold; the un-enforcement is mine.

2. **The step-1b lookahead proof test file had never been committed.** Only
   its pre-registration (`e340127`) was. Entry 2 accepted step 1b on the basis
   of a report about a file that was not in version control and that nobody
   could have re-run. Committed unchanged as `c681bc4`, 16 tests still
   passing. No result changes; the evidence simply did not exist in the repo
   for a day.

### One thing I did not do, deliberately

The pre-registration permitted the held-out look as soon as a feature survived
BH. **I did not take it**, because two of the three survivors had known
interpretation problems and the look is available only once. Entry 4 §D has
since made the promotion rule stricter, which is the right outcome — but the
decision to hold was taken before that entry arrived, not because of it.

### Next, per Entry 4 §F

Commit the §B and §D amendments, then run A (cross-correlations and partial
ICs), B (Kite tradable target, 09:20 open → 15:10 close) and C (quintile
spread in bp against round-trip cost) on selection data only. Write results
and **stop for review before the held-out look**.

---

## Re: Entry 2 — CLOSED. §A done; both blockers resolved; step 1 complete and PASSED

**Current state as of 2026-09-20 16:20.** Both blockers below are closed:
**B-1 was withdrawn** (my rate figure was wrong — stale log read under swap
pressure) and **B-2 was approved but not needed** (the result is a pass, not a
negative fail). Step 1 finished all 400 runs and **PASSED** at −0.0495R
against ±0.05R. Results: `results-step1-null-test.md`. The null test was never
restarted or altered.

*Historical text of the original reply follows, kept for the record.*

`docs/research/progress.md` is created and current: one status line at the
top, the full step checklist with commit hashes, live status for the running
test derived from its own log (it prints every 25 seeds; nothing finer exists
and I did not restart it to add logging), and counts/timing only — no interim
statistics, per §A.

### B-1. The run is 5.3x slower than measured — ETA ~20 h, not ~5 h

Calibration gave **45 s/seed** with memory free. Under sustained swap pressure
the realised rate is **238 s/seed**.

- Started 09:11:16, now 100 of 400 runs done
- **Zero-cost phase** (which the pass rule depends on): ~6.6 h remaining
- **With-cost phase** ("report it again with costs on"): a further ~13.2 h
- All 400: finishes ~2026-09-21 11:30

*Options:* (a) let all 400 finish; (b) take the pass-rule decision when the
zero-cost phase completes in ~6.6 h, leaving the with-cost phase running in the
background; (c) something else.
**Recommendation: (b).** The gate is defined purely on the zero-cost run, so
the decision is available 13 h before the rest of the data is, and nothing
about the pass rule changes by waiting.

### B-2. The §B2 diagnostic cannot be run on this run's output — my error

§B2 specifies, on a negative fail, (a) bars spanning both barriers, (b)
gap-through stops filled at the open, (c) the seed-mean recomputed excluding
those and with (a) at the midpoint, (d) mean R by side — all "on the trade
lists the null already produced, with no new simulation".

**The running script does not persist trade lists.** It keeps one summary dict
per seed (`n`, gross, net, target rate, median R in rupees, median stop in bp)
and writes only those. Per-trade records and exit geometry are computed inside
`summarise()` and discarded. So on the negative branch, (a)-(d) are **not
computable from what will exist**.

That is a design error in my script, surfaced now rather than in 20 hours.

*Options:* (a) on a negative fail, run a small supplementary null (~20 seeds,
~1.3 h) that persists trade lists — but this is new simulation, which §B2
excludes, so it needs your approval; (b) run (a)-(d) on the real 201-trade list
instead, which exists now but measures the harness on *signalled* trades rather
than null ones — a different question; (c) accept the negative branch cannot be
diagnosed, which under §B2 means stopping.

**Recommendation: (a)**, decided now so it can start the moment it is needed.
It is a diagnostic rather than a strategy selection and would be logged as a
research look, not a trial.

**Nothing started for either. Awaiting your call on both.**

---

# Reviewer outbox

Replies to `reviewer-inbox.md`. Newest at the top, with the entry number.

---

## Re: Entry 1 — partial. Steps 1b, trials.md and splits.py done; step 1 running; two decisions needed

**Status: NOT done.** Step 1b is complete and passed. Step 1 (null test) is
**running now** and will take ~5 hours; it is not finished, so the full
ten-section status report is not yet written. Per the inbox's "or blocked"
clause this is going back early, because there are two decisions I should not
take alone and one of them is blocking the schedule.

Full detail: `docs/research/report-2026-09-20.md` is the previous report and
has **not** been rewritten yet — it will be, once step 1 lands.

### Done

| Item | Result |
| --- | --- |
| `trials.md` mirror, all 34 entries | `e7320e5` |
| `splits.py` + import-boundary test | `e1db066` — 20 tests, suite 244 green |
| Pre-registration, step 1b | `e340127`, committed **before** the run |
| **Step 1b lookahead proof** | **PASS — all nine features** |
| Pre-registration, step 1 | `e4545e0`, committed **before** the code was written |
| Test A replication | exact: 201 trades, net −0.3560R, t = −3.589 |
| Q2 earnings feasibility | **recommend skipping 3d** — see below |

### Step 1b — no lookahead in any of the nine features

16 tests. The assertion is that a feature computed for session T is
**bit-identical whether or not the input series contains session T and
everything after it**. Day T's own bar is excluded (profile close equals the
last *prior* bar's close), Bulkowski patterns change not at all when future
bars are removed, and `march_effect` takes `(month, side)` and no price data —
a published constant, not an in-sample fit.

Vacuity guards held: ≥20 whole-profile comparisons, ≥10 per field, and at
least one swing pattern actually fired. **Nothing is excluded from step 2.**

### Test A replication — the inferred t is now measured

My earlier `t ≈ −1.0` for gross was an estimate. Measured:

| | n | mean | sd | t | 95% CI |
| --- | --- | --- | --- | --- | --- |
| NET | 201 | −0.3560R | 1.4063 | **−3.589** | [−0.5504, −0.1616] |
| GROSS | 201 | −0.1021R | 1.3948 | **−1.038** | **[−0.2949, +0.0907]** |

Friction +0.2539R. The gross interval contains zero, so the estimate was
right and is now properly derived.

**Sizing facts you asked to be recorded**, and they confirm your description:

| | |
| --- | --- |
| Realised R | median **₹101.2**, mean ₹122.2 (₹35.5 – ₹603.2) |
| Stop distance | median **42.4 bp**, mean 50.9 bp |
| Notional | median ₹19,702 = the ₹33,000 cap × the 0.6 size factor |
| Cost/trade | ₹25.55 |
| `trail_after_r` | `None` — brackets are fixed, confirmed |

The 1% risk rule never binds: at a 42 bp stop it would permit ~₹236k of
notional against a ₹33k cap. **The cap sizes every position**, then the size
factor scales it.

One correction to your figure: the per-trade average of 1/(1+RR) over the real
trades' actual ratios (median 2.238) is **31.26%**, not 31.9%. Used as the
reference line only, per your instruction.

### Step 1 — running, ~5 hours, and this is the blocker

Pre-registered and started as specified: real harness (`run_backtest` with the
null injected, not a re-implementation), 200 seeds × 2 cost modes, matched on
frequency, brackets, hour profile, long/short mix and stop sizing via joint
bootstrap triples.

**Measured cost: ~45 s per seed → ~5 hours for 400 runs.** Parallelising is
not available: each worker needs ~1.2 GB for the candle cache and the machine
has ~1.1 GB free.

Two single-seed probes during calibration gave gross **−0.068R** and
**−0.029R** (one seed's standard error is ~0.06R, so these are noise
individually). I mention them only because their midpoint sits near the
**±0.05R** band, so the pass rule may turn out to be tight. I am **not**
adjusting it — it is pre-registered.

### Decisions I need from you

**D1 — RESOLVED 2026-09-20: let the faithful run finish.** No deviation; the
pre-registered design (100 symbols, 495 sessions, 200 seeds × 2 cost modes)
runs to completion. Original question below for the record.

**D1 — accept the 5-hour serial run, or approve a documented deviation?**
The prereg says 100 symbols, 495 sessions, 200 seeds. Running each seed on a
random ~25-symbol subset would cut it to ~75 minutes.
*Options:* (a) let the faithful run finish, ~5 h; (b) approve the subset
deviation, recorded as resource-driven.
**Recommendation: (a).** It is already running, the deviation is not settled
by the pre-registration, and changing the design for speed right after seeing
a preliminary number is the habit this process exists to prevent. Take (b)
only if the schedule matters more than the cleanliness.

**D2 — RESOLVED 2026-09-20: skip 3d.** Recorded in
`docs/research/skipped-3d-earnings-drift.md`. Original question below for the
record.

**D2 — install `lxml` to retry earnings dates, or skip 3d now?**
The 15-minute check found no free path to historical earnings *announcement*
dates for 2024-09 → 2026-09:
- `earnings_dates` — blocked, missing `lxml`
- `calendar` — next earnings date only (Oct 2026), no history
- `quarterly_income_stmt` — 5 quarters, only back to **2025-03**, and these
  are fiscal quarter-**end** dates, not announcement dates; the lag between
  them varies by weeks per company and would misdate the event
- `info` — one timestamp, flagged `isEarningsDateEstimate: True`

*Options:* (a) skip 3d and record why; (b) install `lxml` and retry.
**Recommendation: (a).** `lxml` is small and reversible, but it is a
dependency addition your brief says to check first, and even with it
yfinance's historical depth for NSE names is uncertain — likely spending the
dependency and still missing the window.

### Repo state

Branch `research/phase-2-new-hypotheses`, 6 commits, 1,403 insertions.

Added: `docs/research/{orientation,report-2026-09-20,trials,prereg-lookahead,prereg-null-test}.md`,
`backend/research/{__init__,splits}.py`, `backend/tests/{test_research_splits,test_lookahead_proof}.py`.
**Modified: none. Deleted: none.**

**Live order path and credentials untouched.** The only `backend/` additions
are the research package and two test files; no engine, broker, risk, config
or credential file was read, modified or executed. `min_confidence_to_trade:
0` is passed per-run as a research override — the live default is unchanged
and the gate is not "fixed".
