# Phase 2 — progress

**IDLE: step 2 COMPLETE and reviewed. Three of ten features survived BH + Bonferroni on selection; the held-out look is NOT taken. Reviewer Entry 4 received — next action is committing its §B and §D amendments, then runs A, B and C on selection data. Updated 2026-09-21 08:05.**

> **Step 2's three survivors are not three results.** The reviewer's Entry 4 §A
> reads `atr_pct`, `from_high` and `from_low` as one volatility factor, and
> requires partial ICs before any of them is promoted. Two of the three also
> carried interpretation problems of my own finding — see
> `results-step2-feature-ic.md`.
>
> **A process failure is on the record**: the §D4 data-quality gate was coded
> as a report rather than a halt, so its "agreement is adequate" judgement was
> made after seeing the ICs. Separately, the step-1b lookahead proof test file
> had never been committed — only its pre-registration was (fixed in `c681bc4`).

---

## Steps

| Step | State | Evidence |
| --- | --- | --- |
| 0 — orientation | **done** | `560aa50` · `orientation.md` |
| 0b — plan amendments recorded | **done** | `a7eeaf1` · `report-2026-09-20.md` §8 |
| — trials.md mirror (34 entries) | **done** | `e7320e5` · `trials.md` |
| — splits.py + import boundary test | **done** | `e1db066` · 20 tests, suite 244 green |
| — Test A replication (R1, not a trial) | **done** | `testA_trades.json`; gross t = −1.038, CI [−0.2949, +0.0907] |
| **1b — lookahead proof** | **done — PASS** | `e340127` (prereg) · `c681bc4` (the test file itself, which had never been committed) · 16 tests, all nine features clean |
| **1 — random-entry null test** | **done — PASS (marginal)** | `e4545e0` (prereg) · `results-step1-null-test.md` · −0.0495R vs ±0.05R, CI [−0.0616, −0.0373] straddles the band edge |
| **2 — per-feature scanner IC** | **done — 3 of 10 survive, reviewed** | `bc704e5` (prereg) · `d165699`/`535a082` (amendments) · `4c503ad` · `results-step2-feature-ic.md` |
| 2-A — are the three survivors one factor? | **next** | Entry 4 §A — cross-correlations + partial ICs, exploratory |
| 2-B — Kite tradable-target robustness | queued | Entry 4 §B — 09:20 open → 15:10 close; amendment to commit first |
| 2-C — IC translated into bp vs round-trip cost | queued | Entry 4 §C — descriptive, no trial |
| 2 — held-out look | **blocked, deliberately** | Entry 4 §D — needs BH + §B + partial IC \|t\|>2 to qualify. **One look, not yet taken.** |
| 3a — opening-range breakout | queued | — |
| 3b — intraday momentum | queued | — |
| 3c — overnight vs intraday split | queued | Entry 4 §E — must include the volatility-sorted decomposition, and declare step 2 as its motivation |
| 3d — post-earnings drift | **skipped** | `5ba1d93` · `skipped-3d-earnings-drift.md` |

Carried over from Entry 3, after the step-2 block clears: null diagnostic,
friction decomposition from `testA_trades.json`, the README §51/§52 diff shown
to the user before committing, and the ten-section standalone report.

Strategy trial count: **34**, unchanged. Research looks: **16** (L1–L16).
Replications: 1.

---

## Step 1 — null test, live status

Derived from the run's own log without touching the process, as Entry 2 §A
requires. The script prints a line every 25 seeds; nothing finer is available
and it is not being restarted to add logging.

| | |
| --- | --- |
| Started | 2026-09-20 09:11:16 |
| Elapsed | 6 h 40 m |
| Completed | **300 of 400** (zero-cost: 200/200 DONE; with-cost: 100/200) |
| Rate | ~80 s per seed including one-off setup |
| Zero-cost phase | **complete** — pass statistic available |
| Est. all 400 done | within ~1–2 h of 2026-09-20 16:00 |

**Interim statistics are not reproduced here**, per Entry 2 §A — with one
exception the reviewer's own branch logic requires: the zero-cost seed-mean
gross expectancy of **−0.0495R**, which *is* the pre-registered pass statistic
and determines which branch of §B runs next. Full distributions, percentiles
and findings appear once, in the results file, when all 400 runs finish.

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
| 2026-09-20 16:05 | Step 2 pre-registered (`bc704e5`) while step 1 still running, so its result could not shape the design |
| 2026-09-20 16:20 | Step 1 COMPLETE, 400/400. PASS at −0.0495R. Results: `results-step1-null-test.md` |
| 2026-09-20 16:20 | Found and corrected my own error: the script compared real gross against the ZERO-cost null, but the real figure includes slippage. Correct comparator is the with-cost null |
| 2026-09-20 16:20 | **Verdict correction queued**: README §51 / artifact / issue #49 say the signal is "worse than a coin flip" on a 31.9% formula benchmark. Measured null is 25.02%; the signal is +0.94σ BETTER than random, not worse |
| 07:32 | step 2 feature build: 25/813, 0 min elapsed, est. finish 07:34 |
| 07:32 | step 2 feature build: 50/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 75/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 100/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 125/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 150/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 175/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 200/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 225/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 250/813, 0 min elapsed, est. finish 07:32 |
| 07:32 | step 2 feature build: 275/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 300/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 325/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 350/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 375/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 400/813, 0 min elapsed, est. finish 07:33 |
| 07:32 | step 2 feature build: 425/813, 0 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 450/813, 0 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 475/813, 0 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 500/813, 0 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 525/813, 0 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 550/813, 0 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 575/813, 1 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 600/813, 1 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 625/813, 1 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 650/813, 1 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 675/813, 1 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 700/813, 1 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 725/813, 1 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 750/813, 1 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 775/813, 1 min elapsed, est. finish 07:33 |
| 07:33 | step 2 feature build: 800/813, 1 min elapsed, est. finish 07:33 |
