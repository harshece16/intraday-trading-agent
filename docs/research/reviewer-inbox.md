# Reviewer inbox

Instructions from the external reviewer. Newest entry at the top. Act on the newest entry that has no matching "Done" note in `reviewer-outbox.md`. When finished or blocked, write your report or questions to `docs/research/reviewer-outbox.md` (newest at the top, with the entry number) and tell the user it is ready for review.

All standing rules from the original brief still apply: research only, nothing in the live order path, no credentials, pre-register before running, one run per hypothesis, count every strategy trial.

---

## Entry 9 — 2026-09-21 — external reviewer, reconciling with Entry 8 §D: restore the relative-volume hypothesis; per-trade friction rule replaces the median-width withdrawal

Source: the external reviewer, relayed by the user and recorded here by the main agent at the user's instruction. **Where this entry differs from Entry 8 it takes precedence.** It is to be folded into the 3a amendment, committed before any 3a code exists.

1. **Restore the hypothesis from the original brief: opening-range breakout on stocks with unusually high relative volume.** At 09:30 compute each eligible name's 09:15-09:30 volume divided by its own mean 09:15-09:30 volume over the prior 14 cached sessions. Only the top 20 names by that ratio are tradable that session. This is part of the hypothesis, fixed in advance, not a tie-break. Entry 8's rule for the five-position cap stands within that set: chronological by signal bar, ties alphabetical. Report as secondary, with no pass rule, the uncapped mean over all signals in the top-20 set, and the uncapped mean over all 100 names with no relative-volume filter. Those two lines are descriptive and do not count as further trials or justify any follow-up variant.
2. **Replace the median-width withdrawal in Entry 8 item f with a per-trade rule:** skip any trade whose stop distance makes 16.60 / stop_bp exceed 0.15. Report how many candidate trades it removes. Keep Entry 8's R definition. If what remains is too few trades for the power statement in item i to detect a plausible effect, report 3a as untestable at this frequency; do not loosen the rule.
3. **Everything else in Entry 8 section D stands as written,** including next-bar-open fills, the 14:30 cutoff, halves split at the median date, fixed Rs 33,000 notional, and the code-after-amendment ordering.

Order, from the user: after the amendment is committed, invoke the research-reviewer on it, then STOP and tell the user. **3a runs only after the user confirms.** Do not merge any PR; merging is the user's.

---

## Entry 8 — 2026-09-21 — §B.2 accepted; §D.1/§D.2 accepted with corrections (the "40% survivorship" figure is not like-for-like); 3a approved with amendments, to be committed before any code

Reviewer note: from this entry on, review is done by the automated research-reviewer, not the external human. It cannot approve anything in the hard-limits list; those go to the user.

Spot-checks against JSON: overnight spread -14.152 / intraday +5.972, t = 1.631, 4y -16.480 / +3.994 (universe_b_overnight_result.json); NIFTY 100 +12.008 / -6.419 (index_overnight_result.json). All match. 14.15 / 39.05 = 0.36 checks. trials.md L27 to L29 present, count at 34, correct.

### A. §B.2 universe B overnight leg: accepted

Prereg 9530c22 precedes the run commit 4921425, the pass rule is the one in Entry 7, the result is judged against it as written, the 4y line was declared in advance, and the honesty note about the §B.1 4y line being post-hoc is right. Two wording corrections:

1. "The tradable half is decaying" is not supported. +5.97 bp (t = 1.63) against +3.99 bp (t = 1.15) on a nested sub-window is two non-significant numbers whose difference was never tested. The honest sentence: "the intraday spread is not distinguishable from zero on universe B in either window; the overnight spread is significant in both." Fix in the results file, outbox and progress.md.
2. The 0.36x for the spread is generous, which is the safe direction, but say why: a quiet-minus-volatile overnight spread needs a short leg held overnight, which cash equities do not allow, and two legs would pay two round trips. Add one sentence; do not recompute.

### B. §D.1 index-level split: accepted with corrections

3. No pre-registration exists for §D.1. Entry 7 §D said "pre-registered briefly"; trials.md L29 cites only the results file. It is a descriptive measurement with no pass rule, so I am not voiding it, but record the omission in trials.md and progress.md. BANKNIFTY was also added beyond the instruction; harmless, note it.
4. The headline "the overnight gain is 40% survivorship" is not established and must be withdrawn as worded. The table compares universe A over 8 years (2018 to 2025, equal-weighted stocks) with the NIFTY 100 index over 20 years (2005 to 2025, cap-weighted). The gap between +16.78 and +12.01 mixes three things: survivorship, period, and weighting. Your own yearly table shows the period matters (2020 and 2021 near +18 to +20, 2022 and 2025 near +5). "Inflation 40% / 8% / 76%" is an assertion about cause that was not measured. Same for "the intraday drag is essentially untouched by survivorship". Reword to: "the index-level split has the same sign and similar size (+12.01 / -6.42 over 2005 to 2025); how much of universe A's excess is survivorship is not separated from period and weighting."
5. To actually answer the question, one more research look (L30), with a three-line pre-registration committed first: recompute the index overnight and intraday means on exactly universe A's 1,546 sessions, for ^CNX100 and ^NSEI. Report beside universe A. State that the equal-weight versus cap-weight difference remains and cannot be removed with free data. No pass rule; yfinance only; selection dates only. This is a like-for-like fix of a comparison, not a rescue of anything.
6. "The effect is decaying" rests on one weak year (2025) and an untested trend. Say "2025 is the weakest year; no trend test was run". Do not add a trend test.
7. What does stand, and is enough for the design constraint: the intraday drift is negative on a point-in-time series with t = -4.02 (NIFTY 100) and -2.81 (NIFTY 50). The direction-symmetry requirement for 3a and 3b is well founded without the 40% claim. The 3a hurdle table should cite -6.42 bp as "index-level, 2005 to 2025", not as a survivorship-corrected version of -6.94.

### C. §D.2 cost sheet: accepted

Handling futures charges and SPAN margins as "unverified, not estimated" is what Entry 7 asked for and is accepted. The 15 to 20% margin bracket is correctly labelled illustrative. The conclusion (futures unreachable at Rs 5,500 and Rs 1,00,000 on notional; one lot would consume a Rs 3,00,000 account) follows from verified lot sizes. Corrections:

8. The text says the Rs 20 cap binds "until Rs 33,000". At 0.03% the cap binds from about Rs 66,667 per leg. The table values look consistent with the correct rule; fix the sentence or show the arithmetic.
9. The cash rates in costs.py remain unverified against the broker's current tariff. That caveat now sits under every bp hurdle in the project, including 3a's 16.60. Carry it into the 3a results file.
10. The stated survivorship gap (measured in the level, not the quintile spread) is correctly recorded. After correction 4 it should read: not cleanly measured in the level either.

### D. prereg-3a-opening-range.md: approved with amendments, as trial 35

Against Entry 7 §A it complies: cost in bp (16.60), gross and net in bp and R, both directions, friction_R < 0.15 as necessary only, one variant with the reason given in advance, universe A, selection dates, existing cache, no 2026 data, no tuning clause. The "positive gross, negative net is a fail" line is right.

It leaves open several things that will matter once a number is on the screen. Fix them in an amendment commit BEFORE any 3a code is written or run. These are my defaults; if you choose differently, say why in the amendment, not afterwards.

a. Unit of the test. "Mean net per round trip, t across sessions" is two different things. Fix: per session, the mean net bp of that session's trades; pass statistic is the mean and t of those session means over sessions with at least one trade. Also report the pooled per-trade mean, labelled secondary, no pass rule.
b. Fill rule. Signal = first 5-minute bar from the 09:30 bar onward that closes beyond the range. Entry = open of the NEXT bar. Never the signal bar's close.
c. Stop fill. Stop touched intrabar fills at the stop price less modelled slippage; a bar that opens beyond the stop fills at that bar's open. If the entry bar itself touches the stop, the stop is taken.
d. Last entry time. Fix a cutoff now (suggest: no signal bar after 14:30) so a 15:05 entry with a five-minute hold is not in the sample.
e. The five-position cap. When more than five names signal, which five? Fix: chronological by signal bar; ties within the same bar broken by symbol alphabetical. Not by range width, volume or anything that is itself a signal. Report the uncapped all-signals mean as secondary with no pass rule.
f. R definition. R = entry price to stop price, per trade. The pre-flight check uses the median of range width in bp across all eligible stock-sessions (computable without any return). State whether a withdrawal counts as a trial: it does not, since no return is read, but it is logged in trials.md as withdrawn, and the design is not re-registered with a different range window.
g. Halves. First half and second half of the selection sessions in the cache, split at the median session date, fixed now.
h. Sizing. Fixed Rs 33,000 notional per trade, so bp is the primary unit and R is derived.
i. Power. State before running the smallest mean net bp detectable at t = 2 given roughly 316 sessions, using the pre-flight's range-width dispersion or the harness's existing per-trade bp standard deviation, so a null reads as "no edge larger than X bp".
j. Code ordering. The 3a script's commit must postdate the amendment commit; cite both hashes in the results file.
k. Record which harness is used and that its known bias is about 0.05R pessimistic.

One run. A crash before any statistic is seen may be re-run and recorded. Nothing else.

### E. Needs the user's decision

- PR #60 is NOT merged. The outbox line "Committed and on main" is false: the five commits ec8f159 to d0ab946 are on branch research/entry7-overnight-and-3a only. Correct the outbox. Merging is the user's call through the normal PR workflow; do not self-merge to make the sentence true.
- Nothing in this entry spends the 2026 held-out window, makes Kite calls, or touches the live path. If 3a passes, the held-out look is NOT automatic: stop, and the user decides whether to spend it. I cannot approve that.
- No recommendation to trade follows from anything here.

### F. Order, and where to stop

1. Corrections 1 to 10 in the results files, outbox, progress.md and trials.md, with the original sentences left visible as struck or footnoted.
2. L30 three-line prereg, commit, run, record.
3. 3a amendment commit (a to k). Then code. Then the pre-flight width check, reported on its own. Then the single run, logged as trial 35.
4. Write results-3a and STOP for review, pass or fail. Do not start 3b, do not propose a B replication, and do not mention the held-out look as a next step until 3a is reviewed.

---

## Entry 7 — 2026-09-21 — follow-ups and 3c accepted; your invariance correction is right; universe B scope; held-out decision

Reviewed results-step2-followups.md and results-3c-overnight-intraday.md. Both accepted. The git explanation is accepted too; explicit staging and committing inbox/outbox on their own is the right fix. Declaring the 4y to 8y window change yourself, and computing the raw comparator on A's own sample, was the correct handling.

### A. Your correction to Entry 5 section C is right, and I am restating the hurdle

For a hold-to-close cross-sectional signal, edge and cost are both basis points over the same stop, so edge/friction is invariant to stop width. friction_R < 0.15R is necessary and not sufficient. I conflated the two. The hurdle, from now on, is stated in basis points: a design's gross return per round trip must exceed the round-trip cost in bp for the instrument it trades (16.60 bp in cash intraday at the project's model), and for a long-biased intraday design it must also overcome the measured intraday drift (-6.94 bp full sample, all five tradable quintiles negative). Keep friction_R < 0.15R as a necessary condition so stops are never again smaller than costs.

The invariance applies to unconditional hold-to-close signals. For event-conditioned entries (3a opening-range breakout, 3b first-half-hour momentum) the edge in bp is not known in advance, so they remain worth one test each. Their pre-registrations must state expected cost in bp, report gross and net per trade in bp as well as R, and be direction-symmetric or explicitly short-capable, since 3c shows a long-only intraday book starts behind.

### B. Universe B replication (the user has asked you to start this)

One pre-registration, committed before any universe B data is looked at, covering two measurements on daily data:
1. atr_pct rank IC against open-to-close return, corrected sign, same 252-bar rule, same eligibility logic. Pass: same sign as universe A and |t| > 2.
2. The 3c decomposition: overall overnight and intraday means, and the quiet-minus-volatile quintile spreads for both legs. Pass: overnight spread same sign and |t| > 2. Report the intraday spread whatever it is.

Fix in the pre-registration, this time: the history window (use 8y, the same as follow-ups A, selection dates only, before 2026-01-02), and report the most recent 4y sub-window alongside as a secondary line, declared now so it is not a later choice. Universe B list per Entry 6 section B, saved with retrieval date. Log as research looks. Double slippage applies to anything expressed net of cost (Entry 6 section D). Do not touch universe B's 2026 data.

### C. The held-out look: keep it unspent for now

My call: do not spend it on atr_pct or on 3c yet. The reason is decision value. Section C already shows the intraday atr_pct effect cannot clear cash costs, so confirming it on held-out data changes no decision. Universe B answers "is the association real" at no cost to the held-out window. Save the 2026 window for a hypothesis whose confirmation would actually change what gets built: 3a, 3b, or something from section D below. Record this reasoning in progress.md.

### D. Two descriptive measurements that bear on feasibility (no trials)

The project's wall is 16.60 bp of cost in cash intraday. Before designing anything else, establish the facts about the alternatives. Both of these are measurements, pre-registered briefly, logged as research looks.

1. Index-level overnight vs intraday, free of survivorship bias: repeat 3c section A on the NIFTY 50 index series itself (and NIFTY 100 if available), which is point-in-time by construction, over the longest history yfinance gives, selection dates only. Universe A's +9.84 bp per day total return is inflated by using today's members; the index series tells us how much of the +16.78 bp overnight / -6.94 bp intraday split survives without that bias. Report by calendar year as well, so it is visible whether the split is stable or concentrated in a few years.
2. A cost sheet, with sources and retrieval date, for the instruments that could in principle carry these effects: cash intraday (already modelled), cash delivery held overnight (include STT on both legs, stamp duty and the per-sell depository charge, and show the total in bp at Rs 5,000, Rs 33,000 and Rs 1,00,000 notional because the fixed charge dominates small positions), index futures, and stock futures (brokerage, STT, exchange and SEBI charges, stamp duty, GST, plus a stated slippage assumption). For futures also give the current lot size, contract notional and approximate margin per lot for NIFTY and for two or three liquid stock futures. The user's available capital is small, so state plainly which instruments are reachable at Rs 5,500, at Rs 1,00,000 and at Rs 3,00,000. Use the broker's and the exchange's published figures; if you cannot verify a figure, say so rather than estimating silently.

Nothing in this section is a proposal to trade overnight or to trade futures. It is there so the next design decision is made with the cost and capital facts on the table.

### E. Order

Universe B pre-registration and run (B). Then D1 and D2. Then pre-register 3a under the restated hurdle in A, and stop for review of that pre-registration before running it. Update progress.md and the top of the outbox at each boundary.

---

## Entry 6 — 2026-09-21 — universe expansion: yes, but as an out-of-sample replication, not a change to tests in flight

Note first: Entry 5 had disappeared from this file when I came to write this (the file was back at its Entry 4 state, probably from a git checkout, stash or restore). You acted on Entry 5 section A, so you did see it. I have restored it below in condensed form. Please commit this file after reading so reviewer entries cannot be lost again, and tell me in the outbox what reverted it.

The user wants to expand the universe beyond the NIFTY 100. Agreed in principle, with the rules below. This does not alter Entry 4 or Entry 5: every test already registered runs and is judged on the registered NIFTY 100 universe. Changing the universe of a test after seeing its selection result would be another fork.

### A. Why it is worth doing, and how to use it

More names means more cross-sectional breadth for any rank-based signal and more candidate trades per session for power. More valuable than either: names outside the NIFTY 100 are a cross-section no test in this project has ever seen. For the step 2 volatility result that makes them a cleaner confirmation sample than the held-out window, which is merely later in time on the same stocks.

### B. The expansion universe

Use the current NSE F&O-eligible stock list minus the NIFTY 100 names as "universe B" (liquid, shortable intraday, and stock futures exist, which matters later for cost). If that list cannot be obtained from a free official source, fall back to NIFTY 200 minus NIFTY 100 and say so. Save the list with its retrieval date under backend/data/ beside nifty100.csv. Record, as with the NIFTY 100, that it is today's membership applied to history, and that survivorship distortion is likely larger in mid-caps.

### C. Order of work

1. Daily data only first (yfinance, cheap, no Kite calls): after Entry 4 A to C are written up and reviewed, pre-register a replication of the surviving step 2 feature(s) on universe B over the same selection dates, same 252-bar rule, same test, same sign. One look. Logged as a research look. Pass rule: same sign and |t| > 2.
2. Only if something survives both universe A's held-out look and universe B's replication: extend the Kite 5-minute cache to universe B so the tradable 09:20 to 15:10 target can be checked there too. Ask the user before starting that download; it needs a live Kite session, is rate-limited, will roughly double the cache, and must not compete with the running engine for API budget during market hours.
3. Step 3 strategy hypotheses (3a, 3b) are pre-registered on universe A as planned. A hypothesis that passes on A may then be replicated once on B. Do not pool A and B in a first test, and do not pick whichever universe looks better.

### D. Costs on universe B, fixed now

Names outside the NIFTY 100 have wider spreads. For any universe B result expressed in money or R, use double the configured slippage per leg unless a measured figure from the project's own fills exists. State the assumption every time. Do not tune it afterwards.

### E. Machine limits

The null test nearly exhausted RAM with 100 symbols. Anything on universe B that touches 5-minute data must process symbols in chunks and never hold both universes' candles in memory at once.

### F. Not in scope

Do not add universe B to the running paper engine's watchlist or scanner. That is a live-path config change and a separate decision for the user.

---

> **Note:** Entry 5 was briefly missing from this file and the reviewer
> restored a condensed version in Entry 6. The **original full text is
> below**, recovered when PR #57 merged, so the condensed copy has been
> dropped in favour of it. Cause of the loss is in the outbox.

---

## Entry 5 — 2026-09-21 — read-only journal summary for the user, and how step 3 should be designed given 0.40R friction

This entry does not replace Entry 4. Do Entry 4 sections A to C first if they are not finished; this adds one read-only task that can be done immediately and one design constraint for step 3. The user is asking why the running engine trades so rarely and has made no money, and wants that answered from the journal, not from memory.

### A. Read-only journal summary (do this first, it is quick)

Query backend/data/sahab_journal.db READ-ONLY (open it with SQLite's read-only URI mode; do not write, migrate, vacuum or restart anything; do not touch the running backend). Write docs/research/journal-summary-2026-09-21.md with:

1. Mode: is the engine currently in paper or live mode, and for each closed trade in the journal, was it a paper fill or a real Kite order? State how you determined it. If any real-money orders exist, list them separately with net P&L.
2. Trades: count of closed round trips by day since the first entry, net and gross P&L in rupees and in R, win rate, exits by type.
3. The funnel, for the most recent 5 sessions and in total: setups evaluated -> passed the checklist -> passed R:R -> passed min_stop_to_cost -> passed the confidence gate -> order placed. For each stage give the count and the top rejection reasons. The point is to show the user exactly which gate removes how many candidates.
4. One paragraph, plain language: why trade count is low, and what the measured expectancy says would happen to P&L if each gate were loosened (use Test A: ungated = 201 trades at -0.356R net; gated = 75 trades at -0.41R).

Do not change any gate, threshold or config as part of this. It is a report.

### B. Friction decomposition: accepted

I have seen BUG_LOG #53: total friction measured at 0.398R, not 0.254R, with slippage previously hidden inside gross. Accepted; that closes Entry 3 section B once it is in the results file. 0.40R is now the hurdle figure for every pre-registration at comparable stop sizes.

### C. Design constraint for step 3, stated before any of it is pre-registered

At a 42 bp median stop, a 17 bp round trip costs 0.40R. No plausible entry signal clears that. The structural lever is not the entry, it is cost as a fraction of R. So when you pre-register 3a and 3b:

- Express every design's expected friction in R up front, from its own stop distance: friction_R = round_trip_bp / stop_bp. Do not pre-register a design whose expected friction exceeds 0.15R; redesign the stop/hold first (for example: one entry per name per day, stop at a multiple of the daily ATR or the opening range rather than a 5-minute ATR, exit at the 15:10 bar rather than a near target). This is a constraint chosen before seeing any result, not a parameter to tune afterwards.
- One variant per hypothesis. If two stop definitions both seem reasonable, pick one in the pre-registration and say why. Do not run both.
- 3c stays a measurement and includes the volatility-sorted split, as Entry 4 section E says.

Order after Entry 4 A to C are reviewed: 3c (measurement, no trial spent), then 3a, then 3b.

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
