# Phase 2 — progress

**RUNNING: step 1 null test — started 2026-09-20 09:11:16, 300 of 400 runs complete. Zero-cost phase DONE; pass rule PASSES at −0.0495R against ±0.05R. With-cost phase 100/200. Updated 2026-09-20 15:55.**

> **Two problems need a reviewer decision — see "Blockers" below.** The run is
> 5.3× slower than measured, and the diagnostic Entry 2 §B2 specifies cannot
> be executed on this run's output. Neither is being acted on unilaterally,
> and the run has **not** been restarted or altered.

---

## Steps

| Step | State | Evidence |
| --- | --- | --- |
| 0 — orientation | **done** | `560aa50` · `orientation.md` |
| 0b — plan amendments recorded | **done** | `a7eeaf1` · `report-2026-09-20.md` §8 |
| — trials.md mirror (34 entries) | **done** | `e7320e5` · `trials.md` |
| — splits.py + import boundary test | **done** | `e1db066` · 20 tests, suite 244 green |
| — Test A replication (R1, not a trial) | **done** | `testA_trades.json`; gross t = −1.038, CI [−0.2949, +0.0907] |
| **1b — lookahead proof** | **done — PASS** | `e340127` (prereg) · 16 tests, all nine features clean |
| **1 — random-entry null test** | **RUNNING** | `e4545e0` (prereg) · 100/400 runs |
| 2 — per-feature scanner IC | queued | blocked on step 1's outcome |
| 3a — opening-range breakout | queued | — |
| 3b — intraday momentum | queued | — |
| 3c — overnight vs intraday split | queued | — |
| 3d — post-earnings drift | **skipped** | `5ba1d93` · `skipped-3d-earnings-drift.md` |

Strategy trial count: **34**, unchanged. Research looks: 5. Replications: 1.

---

## Step 1 — null test, live status

Derived from the run's own log without touching the process, as Entry 2 §A
requires. The script prints a line every 25 seeds; nothing finer is available
and it is not being restarted to add logging.

| | |
| --- | --- |
| Started | 2026-09-20 09:11:16 |
| Elapsed | 6 h 37 m |
| Completed | **100 of 400** (zero-cost phase: 100/200; with-cost phase: 0/200) |
| Rate | **238 s per seed** |
| Est. zero-cost phase done | 2026-09-20 ~22:20 |
| Est. all 400 done | 2026-09-21 ~11:30 |

**Interim statistics are deliberately not reproduced here**, per Entry 2 §A.
Results appear once, when the run completes.

---

## Blockers — reviewer decision needed

### B-1. WITHDRAWN 2026-09-20 15:55 — my rate figure was wrong

The 238 s/seed and ~20 h ETA below were **incorrect**. The zero-cost phase is
complete and the with-cost phase is at 100/200: **300 of 400 runs in 6 h 40 m**,
about 80 s/seed including setup.

The earlier reading showed 100/200 when the run was substantially further
along. Under the swap pressure Entry 2 §C describes ("file access from outside
has been timing out"), that read appears to have returned a stale view of the
log, and I then attributed fixed setup cost — the 2-year daily download and
`premarket_picks()` over 100 stocks × 495 sessions — to the per-seed rate.

Reviewer chose option (b) on the strength of a wrong number. The decision
turns out not to matter: the zero-cost phase finished on its own and the pass
statistic is available. **No action was taken on the run, and none is needed.**

Original, incorrect text follows.

### B-1 (superseded). The run is 5.3× slower than measured, so the ETA is ~20 h, not ~5 h

Calibration measured **45 s per seed** with memory free. Under sustained swap
pressure (swap 5.5 GB of 7 GB used; ~0.76 GB reclaimable) the realised rate is
**238 s per seed**.

The pass rule depends only on the **zero-cost** phase, which finishes in
~6.6 h. The **with-cost** phase is a further ~13.2 h and is "report it again
with costs on" — secondary to the gate.

*Options:* (a) let all 400 finish, ~20 h; (b) take the pass-rule decision when
the zero-cost phase completes (~6.6 h) and let the with-cost phase continue in
the background; (c) something else.

**Not acted on.** The run continues untouched.

### B-2. RESOLVED — approved, and now NOT NEEDED

The reviewer approved the supplementary run. It is written and ready at
`null_diagnostic.py` (20 seeds, persists trade lists and exit-bar geometry).

**It will not be run.** It exists for the negative-fail branch, and the result
is a pass. Recorded here so the approval and the non-use are both on record.

Original text follows.

### B-2 (resolved). Entry 2 §B2's diagnostic cannot be run on this run's output

§B2 specifies, on a negative fail, a diagnostic over "the trade lists the null
already produced, with no new simulation":

> (a) bars spanning both barriers · (b) gap-through stops filled at the open ·
> (c) seed-mean recomputed excluding those, and with (a) scored at the midpoint
> · (d) mean R by side

**The running script does not persist trade lists.** It keeps one summary dict
per seed — `n`, `gross`, `net`, `target_rate`, median R in rupees, median stop
in bp — and writes only those to `null_result.json`. Per-trade records, exit
bar geometry and per-side breakdowns are computed and discarded inside
`summarise()`.

So if the result lands on the negative-fail branch, (a)–(d) are **not
computable from what will exist**. This is my error in the script's design,
found now rather than in 20 hours.

*Options:*
- (a) if the negative branch triggers, run a **small supplementary null** (e.g.
  20 seeds) that persists trade lists — this is new simulation, which §B2
  explicitly excludes, so it needs approval;
- (b) run (a)–(d) on the **real** 201-trade list instead — available now, but
  it measures the harness on *signalled* trades rather than null ones, which
  is a different question;
- (c) accept that the negative branch cannot be diagnosed on this run and
  treat the fail as unexplained, which under §B2 means stopping.

**Recommendation: (a)**, decided now so it can run immediately if needed.
Twenty seeds at ~238 s is ~1.3 h, it is a diagnostic rather than a strategy
selection, and it would be recorded as a research look, not a trial. But it is
new simulation and §B2 forbids it, so it is the reviewer's call.

**Nothing has been started for either option.**

---

## Note on the running test's own caveat

Entry 2 §B records, to state rather than fix: stop distances are bootstrapped
in **bp**, so a 42 bp stop can land on a stock whose volatility makes that
unusually tight or loose. This does not affect the gross-expectancy gate, but
it shifts time-to-resolution and the timeout share, so the resolved-only
target-rate comparison (finding 1) is **approximate**. This will be repeated
in the results file.

---

## Machine load

Per Entry 2 §C, nothing memory-heavy has been started alongside the run. The
null test holds 1,220 MB; the user's backend (17 MB) and dashboard (3 MB) are
negligible and have been left running — stopping them would recover ~20 MB and
is not worth the disruption.

---

## Log

| When | What |
| --- | --- |
| 2026-09-20 09:11 | Step 1 null test started, as pre-registered |
| 2026-09-20 ~14:00 | Step 3d skipped and recorded (`5ba1d93`) |
| 2026-09-20 15:48 | progress.md created; B-1 and B-2 raised; run untouched |
| 2026-09-20 15:55 | B-1 WITHDRAWN — rate figure was wrong, read a stale log under swap pressure |
| 2026-09-20 15:55 | Zero-cost phase complete: seed-mean gross −0.0495R → **PASS** against ±0.05R, by 0.0005R |
| 2026-09-20 15:55 | B-2 approved but not needed — pass branch, not negative-fail |
