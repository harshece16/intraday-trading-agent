# Reviewer inbox

Instructions from the external reviewer. Newest entry at the top. Act on the newest entry that has no matching "Done" note in `reviewer-outbox.md`. When finished or blocked, write your report or questions to `docs/research/reviewer-outbox.md` (newest at the top, with the entry number) and tell the user it is ready for review.

All standing rules from the original brief still apply: research only, nothing in the live order path, no credentials, pre-register before running, one run per hypothesis, count every strategy trial.

---

## Entry 4 — 2026-09-21 — step 2 reviewed: decisions on Problems 1-3, and two checks before the held-out look

Reviewed results-step2-feature-ic.md. The write-up is honest and the three problems are the right ones to raise. Holding back the held-out look was the correct call. Decisions below. Nothing here authorises a held-out look yet; section D says when.

### A. The three survivors are probably one effect, not three

`from_high` and `from_low` are both distances across a stock's 52-week range, and a volatile stock has a wide range, so both are large when `atr_pct` is large. Read with the signs corrected, all three results say the same thing: stocks with high volatility / wide ranges had lower open-to-close returns, and quiet stocks near either end of a narrow range had higher ones. That is also a documented pattern (high-volatility stocks earn their return overnight and give it back intraday), which is hypothesis 3c's territory. So treat this as one candidate factor until shown otherwise.

Measure it, selection split only, labelled exploratory, logged as research looks:
1. Per-session cross-sectional rank correlations among `atr_pct`, `from_high`, `from_low` (mean across sessions).
2. Partial ICs: each session, residualise `from_high` and `from_low` on `atr_pct` (rank regression is fine), then rank IC of the residual against the target; mean, t, % positive. And the reverse: `atr_pct` residualised on the other two.

### B. Robustness to the target, because 18.55% disagreement is not small

I left "poor agreement" undefined in Entry 3 D4, so the unenforced gate is partly my gap. A 0.983 correlation is accepted as passing. But the 18.55% tail is large, the official NSE close is a last-30-minute weighted average rather than the last trade, and your own concern that vendor error may scale with volatility is exactly the concern for `atr_pct`. Also, nobody can trade the opening print.

So before any held-out look, on the selection sessions that overlap the Kite cache (2024-09-20 to 2026-01-01), recompute the rank IC for the three survivors against a tradable Kite target: open of the 09:20 bar to close of the 15:10 bar (the last bar before the 15:15 square-off). Same eligibility, same 252-bar rule, same sign conventions as corrected. Pre-commit this rule before running: a survivor keeps its status only if the Kite-target IC has the same sign and |t| > 2 on the overlap. Report how much of the yfinance-target IC survives (ratio of means). If most of the effect disappears when the first five minutes are excluded, say so plainly: it would mean the effect lives in the opening print and cannot be captured.

### C. Translate the IC into money, since an IC cannot be compared with friction

For `atr_pct` on the Kite target, selection overlap only: sort each session into quintiles, report mean target return per quintile in bp, the bottom-minus-top spread in bp per session with its t-stat across sessions, and the same for a top-5 / bottom-5 version (the scanner trades five names). Set that beside the measured round-trip cost in bp for a full-day hold at the project's cost model, for cash intraday. State clearly whether the spread per unit of notional exceeds round-trip cost. My rough expectation is that it does not in cash equities; measure it rather than taking my word. No backtest, no strategy trial: this is descriptive.

### D. Decisions on your three problems

- Problem 1 (`from_low` sign): agreed, relabel, no rerun. Record the corrected sign in the table itself, not only in the prose, and keep the original line visible as struck or footnoted so the history is auditable.
- Problem 2 (band-shaped `atr_pct` and `rsi`): do not add band tests. The composite is already dead, so validating the scanner's bands is no longer the question, and each extra test enlarges the family. Record both as "monotonic association measured; scanner's banded use not tested". The `atr_pct` result stands as a measurement, not as support for the scanner.
- Problem 3 (held-out look): amend the promotion rule, stricter than registered, and commit the amendment before looking. A feature gets the held-out look only if it (i) survived BH on selection, (ii) passes B on the Kite target, and (iii) for `from_high` / `from_low`, its partial IC controlling for `atr_pct` has |t| > 2 on selection. Bonferroni across however many qualify. The held-out look uses the Kite target from B, since that is the tradable one, with the registered pass rule: same sign and |t| > 1.5. One look. If only `atr_pct` qualifies, it is one test at alpha 0.05.
- The held-out window has not been examined for this particular relationship before, so this look is cleaner than most in this phase. Say that in the write-up, along with the general contamination note.

### E. What this result does and does not change

It does not revive the old strategy and is not a reason to build a new one yet. It is a selection-sample association of modest size in a universe with survivorship bias, and a volatility sort is where survivorship distortion is likely to be strongest (the volatile names that fell out of the index are missing). Carry that caveat explicitly.

It does change 3c. When you pre-register 3c, include the volatility-sorted version of the overnight/intraday decomposition, and state in the pre-registration that it was motivated by step 2's selection-sample result, so only data outside that sample counts as confirmation.

### F. Order

Commit the amendments in B and D first. Then A, B, C on selection data. Then write results and stop for review BEFORE the held-out look; I want to see A to C first. The Entry 3 items still stand and follow after: null diagnostic, friction decomposition, README diff shown to the user, ten-section report. Keep progress.md and the top of the outbox current.

---

## Entry 3 — 2026-09-21 — step 1 accepted as a marginal pass; three corrections; step 2 amendments

Reviewed results-step1-null-test.md, progress.md and prereg-step2-feature-ic.md. Step 1 is accepted as a PASS under the pre-registered rule, and your own framing of it as marginal is right: record the harness bias as -0.05R, 95% CI [-0.062, -0.037], pessimistic direction. Catching your own zero-cost vs with-cost comparator error was good work. Four things before and around step 2.

### A. The attribution of the -0.05R is asserted, not measured. Run the diagnostic.

The results file says stop-first-on-same-bar and gap-through-at-open "account for it". Nothing measured that. It is also not obviously true: positions are intraday, so there are no overnight gaps, and a single 5-minute bar spanning a 42 bp stop plus a ~95 bp target should be rare when the 5-minute ATR is ~12 bp. Other candidates are bar-to-bar overshoot on stop fills, any asymmetry between how stops and targets fill on a gap, and negative intraday drift acting on a 59.7% long book.

Run null_diagnostic.py as written (20 seeds, zero-cost, trade lists persisted) and report (a) to (d) from Entry 2 section B2, plus: whether a target gapped through fills at the open (better than target) or at the target price, and mean R for longs and shorts separately. Log it as a research look. It is memory-heavy, so run it on its own, after step 2, not alongside anything. This also answers your open question about why the higher target rate does not show up proportionally in gross. Until it lands, change "account for it" in the results file to "are the expected sources; attribution not yet measured".

### B. Friction is probably larger than the verdict says. Verify.

Your with-cost null gross (-0.179R) differs from the zero-cost gross (-0.0495R) by 0.13R, and you explain that as slippage being inside "gross". That is consistent with 6 bp round-trip slippage on a ~45 bp stop. If so, then for the real strategy too: "gross -0.102R" already contains ~0.13R of slippage, the 0.254R labelled "friction" is charges only, total friction is about 0.38R per trade, and the pre-friction expectancy is about +0.03R rather than -0.10R. The verdict's "friction 0.254R, 71% of the loss" would then be understated.

Verify from testA_trades.json rather than by inference: per-trade slippage in rupees and in R, per-trade charges in rupees and in R, and the three-way decomposition pre-friction / slippage / charges with means and CIs. No new backtest needed. State the result in the results file and carry the total-friction figure into every step 3 pre-registration as the hurdle a hypothesis must clear at comparable stop sizes.

### C. The verdict correction: make it, but narrowly

The 31.9% benchmark and "a shade worse than a coin flip" are wrong and should be corrected. But "better than random" and "real-ish" overstate the other way. At the 82nd percentile and under 1 sigma the supportable sentence is: "indistinguishable from random entries (82nd percentile of a matched random-entry null; resolved-target rate 28.4% against a simulated 25.0%)". Also, gross, net and target rate are not three independent statistics; they are largely the same information, so drop "consistently across three independent statistics".

Limit the edit to those sentences plus the friction decomposition from B once verified. Show the user the exact diff for README section 51/52 and the issue #49 comment before committing or posting; those are the user's documents. The conclusion (no edge, do not trade it) does not change, and nothing here is a reason to revisit or re-tune the old strategy: an unproven +0.08R excess against ~0.38R of friction is not a lead.

### D. Step 2 pre-registration: amend before running, commit the amendment first

1. Binary and categorical tests must not pool stock-days into one two-sample t. Returns within a session are cross-sectionally correlated, so that t is inflated. Instead compute, per session, mean target return of flagged minus unflagged stocks (for trend: up minus down), using only sessions with at least 3 stocks on each side, then take the mean across sessions and its t-stat across sessions, the same way the rank-IC series is handled. Report sessions used per feature.
2. Trend is one test (up minus down per the scanner's direction), not a set of pairwise t-stats. That makes ten tests in the BH family (3a and 3b count separately). State the family size in the results.
3. 52-week features need a real 52 weeks. For every tested session each stock must have at least 252 prior daily bars; download enough history to make that true from the first selection session (this matches what the live scanner sees), and report how many stock-sessions are dropped if any still fall short. The same check applies to EMA50 and ATR warm-up.
4. Keep the yfinance open-to-close target as registered, but add a data-quality check that is not a second test: on the overlap with the Kite cache, correlate yfinance open-to-close with Kite first-bar-open to last-bar-close per stock-session, and report the correlation and the share of stock-sessions differing by more than 25 bp. If agreement is poor, stop and report instead of running the ICs.

### E. Housekeeping

- The top of reviewer-outbox.md was stale when I read it (it still showed the withdrawn blockers as open). The newest block at the top of the outbox must always reflect the current state.
- The ten-section standalone report from Entry 2 section D has not been written. Write it after step 2 and the diagnostic, as a new dated file.
- Order: step 2 amendment commit, step 2 run, results file, then the diagnostic, then B's decomposition and C's diff for the user, then the report and outbox summary. Do not start step 3 pre-registrations until I have reviewed step 2.

---

## Entry 2 — 2026-09-20 — progress updates, and what happens after the null test lands

Reviewed your partial reply to Entry 1. Steps 1b, trials.md, splits.py, the Test A replication and the 3d skip are all accepted as written. The 31.26% correction is right. Leaving the ±0.05R band alone after seeing the two probes was the correct call. Do NOT restart or alter the running null test for anything in this entry.

### A. Progress updates the user can see

Create `docs/research/progress.md` and keep it current. The user and the reviewer will read this file instead of interrupting you.

- Top of file: one status line — what is running now, when it started, runs completed out of total, estimated finish time, and the timestamp of this update.
- Below it: a short checklist of every step in the phase (0, 1, 1b, 2, 3a, 3b, 3c, 3d) marked done / running / queued / skipped, each with its commit hash or results file once it exists.
- For the null test that is already running: derive progress from whatever it already writes (output file, log, process state). If it writes nothing you can read without touching it, say so in progress.md and give the estimated finish from the start time. Do not restart it to add logging.
- For every long run from now on (anything over ~10 minutes): have the script append a line to progress.md after each seed or chunk — count completed, elapsed, estimated finish. Counts and timing only. Do not write running means or any interim statistic; results appear once, when the run is complete.
- Update progress.md whenever a step starts, finishes, fails or is blocked. Commit it at step boundaries, not on every line.

### B. When the null test finishes — decided now, before the result exists

The pass rule stays exactly as pre-registered: zero-cost seed-mean gross expectancy within ±0.05R of zero. Report pass or fail plainly against that band. What follows depends on the outcome:

1. PASS: write the results file, update the report, proceed to step 2 (per-feature IC) without waiting for me. Pre-register step 2 first, as always.

2. FAIL on the NEGATIVE side (mean below -0.05R): record it as a fail. Do not widen the band and do not re-run with different settings. Then run this diagnostic on the trade lists the null already produced, with no new simulation: (a) count and share of trades where a single bar spanned both the stop and the target (stop-first rule); (b) count and share of stops filled at the open after a gap-through, and the average extra loss in R on those; (c) recompute the seed-mean gross expectancy excluding (a) and (b) trades, and separately with (a) trades scored at the midpoint of stop and target. (d) mean R by side, since the null is 59.7% long and a drifting market would show up there. Report how much of the shortfall each accounts for. If (a) to (d) explain the gap, the harness is conservative by a measured amount: state that amount, note that every strategy result carries it as a pessimistic bias, and proceed to step 2. If they do not explain it, stop and write to the outbox; nothing further runs until I have looked.

3. FAIL on the POSITIVE side (mean above +0.05R): stop everything. This means the harness may be manufacturing edge. Write what you have to the outbox and wait. Do not start step 2.

One known caveat to state in the results, not to fix: stop distances are bootstrapped in bp, so a 42 bp stop can land on a stock whose volatility makes that unusually tight or loose. That does not affect the gross-expectancy check, but it shifts time-to-resolution and the timeout share, so the resolved-only target-rate comparison (finding 1) is approximate.

### C. Machine load

The run leaves almost no free RAM and file access from outside has been timing out. While it runs, do not start anything else memory-heavy. Writing docs and progress.md is fine.

### D. When done

After the null test (and step 2 if the pass or explained-negative branch applies), write the standalone ten-section status report as a new dated file, summarise it at the top of reviewer-outbox.md under "Re: Entry 2", update progress.md, and tell the user it is ready for review.

---

## Entry 1 — 2026-09-20 — go-ahead for steps 1 and 1b, with corrections

Go. Order: trials.md mirror, splits.py with the import-boundary test, step 1b lookahead proof, then the step 1 null test. Q1: option (a). Q2: do the 15-minute check; if a free source doesn't cover earnings dates across 2024-09 to 2026-09 for most of the universe, skip 3d and record why.

Before any run: create docs/research/trials.md now with all 34 existing entries copied from backtest_trials.json (the report only read the last six), plus the separate "research looks" heading. Commit it.

Q3 and amendment 5 need a correction, and this supersedes the "compare 31.9% against resolved trades" line in amendment 5 and the expected result in report §4. Whether the real strategy's 28.4% falls inside the null distribution is a finding about the strategy, not a harness check, so it is not the pass rule. And 31.9% is not the right benchmark for resolved-only trades: with a 15:15 timeout the nearer barrier (the 1R stop) resolves faster, so trades heading for the far target are disproportionately timed out, and the resolved-only target rate under a driftless null sits below 1/(1+RR). Use the simulated null as the benchmark. Compute the formula per trade from each trade's actual target/stop ratio only as a reference line.

Harness pass rule, to pre-register before running: run the null with ZERO_COSTS and zero slippage; the seed-mean gross expectancy must be within ±0.05R of zero (expect slightly negative, because stop-first-on-same-bar and gap-through-at-open are conservative). Report it again with costs on. Then report where the real 28.4% and the real gross expectancy sit in the null distributions, as results about the strategy.

The null test needs the real strategy's trade list (entry times, sides, stop sizes). Re-running the identical Test A configuration to regenerate it is a replication, not a new trial: log it in trials.md as "replication, not counted" and do not increment the counter. While you have that list, compute the gross expectancy's standard deviation, t-stat and 95% CI properly, replacing the inferred t ≈ -1.0 in report §7.

Also record: trail_after_r is None so brackets are fixed, and the 33% notional cap (not the 1% risk rule) is what sizes positions, so realised R is about Rs 100-115. State realised R in rupees and stop distance in bp for every hypothesis, since friction as a fraction of R depends on it.

Update orientation.md and the report to reflect these corrections. When steps 1 and 1b are done, write the standalone status report (same ten-section format as report-2026-09-20.md) and summarise it in reviewer-outbox.md.
