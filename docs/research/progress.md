# Phase 2 — progress

**PHASE 2 CLOSED. 3b WITHDRAWN at stage 1 — cross-sectional −1.60 bp (t=−0.48) vs a 33.20 bp gate, time-series +0.70 bp (t=+0.61) vs 16.60 bp. NO TRIAL SPENT; count stays at 35. Closing report: `report-phase-2-closing.md`. The 2026 held-out window has NEVER been looked at. Stage 2 is defined but UNAUTHORISED. Updated 2026-09-21.**

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

## Why the held-out window is still unspent (Entry 7 §C)

The reviewer's call, recorded here as §C directs. **Do not spend the 2026
held-out window on `atr_pct` or on 3c.**

The reason is **decision value, not caution**. Step 2 §C already established
that the intraday `atr_pct` effect cannot clear cash costs, so confirming it
on held-out data would change no decision anyone would take. Universe B
answered "is the association real" at **no cost to the held-out window** —
and it passed, twice.

The 2026 window is therefore reserved for a hypothesis whose confirmation
**would** change what gets built: 3a, 3b, or something arising from Entry 7
§D. It has never been looked at for any of this work.

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
| 2-A — are the three survivors one factor? | **done — YES, one factor** | `results-step2-followups.md` · ρ(atr_pct, from_low) = +0.43; partials collapse to \|t\| = 1.05 and 1.90 |
| 2-B — Kite tradable-target robustness | **done — all three pass** | 09:20 open → 15:10 close, 316 sessions; `atr_pct` retains 0.77× |
| 2-C — IC translated into bp vs round-trip cost | **done — does NOT clear cost** | +8.11 bp quintile / +16.30 bp top-5 vs **33.20 bp** (two legs) = **0.24× / 0.49×** round trip |
| §A null diagnostic | **done — explanation refuted** | `results-null-diagnostic.md` · (a) 0.00%, (b) 6.8%; drift explains the rest |
| §B friction decomposition | **done** | slippage 0.144R + charges 0.254R = **0.398R** · README §51 corrected |
| §C verdict correction | **done** | README §51/§52 + issue #49 comment |
| Ten-section standalone report | **done** | `report-2026-09-21.md` |
| Entry 5 §A journal summary | **done — accepted** | `journal-summary-2026-09-21.md` · all legs paper, 0 live orders |
| 3c §A–C | **done — mechanism HOLDS** | `results-3c-overnight-intraday.md` · overnight +16.78bp, intraday −6.94bp |
| Entry 7 §B.2 universe B overnight | **done — PASS** | `results-universe-b-overnight.md` · overnight −14.15bp t=−8.55 significant in both windows; intraday **not distinguishable from zero in either** (§A.1 correction: "decaying" withdrawn) |
| Entry 7 §D.1 index-level split | **done, corrected** | `results-entry7-d-feasibility.md` · split holds (+12.01 / −6.42); the **40% survivorship claim is withdrawn** (Entry 8 §B.4) — it confounds survivorship, period and weighting. **Was not pre-registered** (§B.3) |
| L30 like-for-like index fix | **next** | `prereg-L30-index-like-for-like.md` · index means on universe A's own 1,546 sessions |
| Entry 7 §D.2 cost sheet | **done** | delivery 33.05bp vs intraday 16.60bp at ₹33k; futures unreachable at all three capital levels |
| Entry 7 §C held-out decision | **recorded — DO NOT SPEND** | reviewer's call: no decision changes, so save 2026 for 3a/3b |
| Universe B replication (Entry 6 §C.1) | **done — PASS** | `results-universe-b-replication.md` · t = −6.68, but 0.26× cost |
| 3c pre-registration | **done — §A–C ready to run** | `prereg-3c-overnight-intraday.md` · §D held-out specified but NOT run |
| 2 — held-out look | **blocked — awaiting reviewer** | Only `atr_pct` qualifies → a single test at α = 0.05. **Not taken.** Entry 4 §F says stop here. |
| 3a — opening-range breakout | **done — FAIL (trial 35)** | `results-3a-opening-range.md` · net −12.09 bp, t = −2.71; gross +4.52 bp, t = +1.01 · amendment `815ba4c` → code `3841124` → pre-flight `9f9ac61` → run `f4f1d3c` |
| 3b — intraday momentum | **WITHDRAWN at stage 1, no trial** | `prereg-3b-intraday-momentum.md` · stage 1 = research look L31 (no trial); stage 2 = trial 36 only if stage 1 clears 16.60 bp |
| 3c — overnight vs intraday split | queued | Entry 4 §E — must include the volatility-sorted decomposition, and declare step 2 as its motivation |
| 3d — post-earnings drift | **skipped** | `5ba1d93` · `skipped-3d-earnings-drift.md` |
| **3f — stage 0 feasibility** | **done — 0c source CONFIRMED, 0b PASS 95.17%, 0c vendor HALT (38%)** | `results-3f-stage0.md` · membership rebuilt from 547 NSE press releases, consistent to 2009-01-12 · **stopped for reviewer**; stage 1 not written |

Carried over from Entry 3, after the step-2 block clears: null diagnostic,
friction decomposition from `testA_trades.json`, the README §51/§52 diff shown
to the user before committing, and the ten-section standalone report.

Strategy trial count: **35** (3a, 2026-09-21). Research looks: **16** (L1–L16).
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
| 09:14 | supplementary null diagnostic: 1/20 seeds, 0 min elapsed, est. finish 2026-09-21 09:18 |
| 09:14 | supplementary null diagnostic: 2/20 seeds, 0 min elapsed, est. finish 2026-09-21 09:19 |
| 09:14 | supplementary null diagnostic: 3/20 seeds, 1 min elapsed, est. finish 2026-09-21 09:19 |
| 09:15 | supplementary null diagnostic: 4/20 seeds, 1 min elapsed, est. finish 2026-09-21 09:19 |
| 09:15 | supplementary null diagnostic: 5/20 seeds, 1 min elapsed, est. finish 2026-09-21 09:19 |
| 09:15 | supplementary null diagnostic: 6/20 seeds, 2 min elapsed, est. finish 2026-09-21 09:19 |
| 09:15 | supplementary null diagnostic: 7/20 seeds, 2 min elapsed, est. finish 2026-09-21 09:19 |
| 09:16 | supplementary null diagnostic: 8/20 seeds, 2 min elapsed, est. finish 2026-09-21 09:19 |
| 09:16 | supplementary null diagnostic: 9/20 seeds, 2 min elapsed, est. finish 2026-09-21 09:19 |
| 09:16 | supplementary null diagnostic: 10/20 seeds, 3 min elapsed, est. finish 2026-09-21 09:19 |
| 09:16 | supplementary null diagnostic: 11/20 seeds, 3 min elapsed, est. finish 2026-09-21 09:19 |
| 09:17 | supplementary null diagnostic: 12/20 seeds, 3 min elapsed, est. finish 2026-09-21 09:19 |
| 09:17 | supplementary null diagnostic: 13/20 seeds, 3 min elapsed, est. finish 2026-09-21 09:19 |
| 09:17 | supplementary null diagnostic: 14/20 seeds, 4 min elapsed, est. finish 2026-09-21 09:19 |
| 09:17 | supplementary null diagnostic: 15/20 seeds, 4 min elapsed, est. finish 2026-09-21 09:19 |
| 09:18 | supplementary null diagnostic: 16/20 seeds, 4 min elapsed, est. finish 2026-09-21 09:19 |
| 09:18 | supplementary null diagnostic: 17/20 seeds, 4 min elapsed, est. finish 2026-09-21 09:19 |
| 09:18 | supplementary null diagnostic: 18/20 seeds, 5 min elapsed, est. finish 2026-09-21 09:19 |
| 09:18 | supplementary null diagnostic: 19/20 seeds, 5 min elapsed, est. finish 2026-09-21 09:19 |
| 09:19 | supplementary null diagnostic: 20/20 seeds, 5 min elapsed, est. finish 2026-09-21 09:19 |
| 2026-09-21 | Loop handed to this session; the other session stopped. Outbox corrections it missed are made. Entry 9 recorded (`ad7b05c`), 3a amendment 3 committed (`815ba4c`), no 3a code. STOPPED for reviewer + user |
| 2026-09-21 | User confirmed 3a. Code `3841124`, pre-flight `9f9ac61` (303 sessions, 1,139/5,275 removed), single run `f4f1d3c`: **FAIL**, net −12.09 bp, t = −2.71. STOPPED for review |
| 2026-09-24 | 3f stage 0 run (no look, no trial). 0c closing-price rule confirmed from NSE/CMTR/61813 §3.4 and Fact Book 2010; 0b membership rebuilt and consistent to 2009-01-12, start 2010-01, coverage 95.17%; 0c vendor check **HALTS as pre-registered** (Kite cache is dividend-adjusted and its last bar is not the close; 99.4% of yfinance closes equal the NSE bhavcopy). STOPPED for reviewer |
