## Re: Entry 19 — L40 stage 0 run on the Mac: all six checks pass, sample_count 1 by the timing rule. The pass is started under amendment 3; no statistic exists until it ends.

**2026-09-29.** Branch `research/kronos-l40-run`. Order of commits: amendment
3 and the harness `8d709c6` → stage 0 run 20:32 to 20:53 → its record
`docs/research/data/kronos_l40_stage0.json` → this entry → the pass. The
owner asked for the run ("run Kronos", 2026-09-29). Kronos is installed in
the project's research environment only; nothing in the live path can
import it (`test_no_live_module_imports_research` still holds).

| Check | Result |
| --- | --- |
| 1. Install matches upstream | The Kronos repository's regression test: 4 passed in 19 s, on the revisions that test pins (`901c26c`, `0e01173`) |
| 2. Revisions | Latest before 2025-09-01: model `12b7990` and tokenizer `f6c7de7`, both 2025-08-17. Window unchanged |
| 3. Lookahead | 20 of 20 forecasts bit-identical with and without later bars |
| 4. Timing | 5.20 s a forecast at sample_count 3, 62.6 hours for 43,362 forecasts. Over 36 hours, so **sample_count 1** |
| 5. Adjustment | One fetch run (2026-09-20, 1,302 spans). No stock-session straddles a step; 0 dropped |
| 6. Coverage | 79 sessions, 2025-09-01 to 2025-12-23; halves 39 and 40; 43,362 stock-times; no session below 20 stocks |

**Disclosed.**

- Device CPU, 4 threads, pandas 2.2.2, the rest as amendment 3 lists. pandas
  was 2.3.3 at the first install and was pinned before any model was loaded.
- The regression test and the look load different revisions, as amendment
  3 says: the test proves the code path on the authors' pinned weights, the
  look uses the weights §2 picks.
- At sample_count 1 each forecast is one draw, not a mean of three. That
  makes the feature noisier, which on average can only weaken a measured
  rank correlation, not strengthen it. The prereg allows the choice on
  timing alone and it was made before any forecast met a return.
- No check needed a judgement the text does not settle, so under amendment
  3 the pass starts now: about 21 hours of computing, stopped through the
  session of 2026-09-30, so the result is expected on 2026-10-01. The script
  computes nothing from the forecasts until every one is done. A defect
  found in this record before then stops the run with no result.

## Note for the record — the paper book has trial 126's fill rules and band, by the owner's decisions (PR #191). Not a research step; no review requested.

**2026-09-29.** The owner chose, from a list, to add the waiting-order fill
rules to the paper book (#180) and to change the band's expected figure to
+0.71% a month. Both were done before the book's first rebalance. The band
uses trial 126's mean and standard deviation, 0.71% and 3.89%; this loosens
the floor from −14.0% to −14.8% at six months. Run over 2010-02 to 2025-11 the
paper book's code gives trial 126's monthly values to within 7e-16, with the
same holdings and the same counts of waiting orders. No new return was read:
the comparison is against trial 126's saved series. Nothing dated 2026 was
read. A second dated note is in `prereg-3i-momentum-corrected-data.md`.

## Note for the record — the paper book's loader is repaired, by the owner's decision (PR #181). Not a research step; no review requested.

**2026-09-28.** Entry 24 filed the loader fix as the owner's decision. The
owner's words the same evening: "yes fix the momentum book loader before 1
october". `backend/momentum_book.py`'s loader is now a copy of the research
loader's repaired panel; on the cache to 2025-12-31 the two panels have 0
differences and the ranked universe matches at 36 of 36 month-ends. The
rule, the costs and the band are unchanged. The fill rules of trial 126 are
not in the paper book (#180), and the band's expected figure is unchanged;
both wait on the owner. A dated note is in `prereg-3i-momentum-corrected-data.md`.
Nothing dated 2026 was read for the checks.

## Re: Entry 24 — H1 to H14 applied in one commit. PR opened. Three things go to the owner with the results.

**2026-09-28.** Branch `research/universe-width`. Every replacement wording
in Entry 24 is applied. Two were strengthened with evidence instead of
weakened: the margins in H3 were recomputed from the saved series (Deflated
Sharpe margin 0.006% a month, 0.02 points of slippage a side; t margin 0.03%
a month, 0.10 points), and H4's June 2021 claim now cites printed prices and
lock flags committed as `data/momentum_width_june_2021.json` (three stocks in
trade-for-trade from 9 June; locked at the lower band on 1, 2 and 5 July;
first session a sell could fill, 6 July). Nothing was re-run.

**To the owner, with the results:** the main question could not be tested,
and whether to register a new test; the paper book's loader, whether and
when; the forward band's expected figure. The owner is also told the pass is
narrow.

## Re: Entry 23 — amendment 4 and the list's script committed (`c93936e`); A′, B′, the three tier records and W run once each. Brought back with the results.

**2026-09-28.** F1, F3 to F8, G1 to G7 and G10 are in amendment 4. The
script is `backend/research/panel_differences.py`; the regenerated list has
the same 743 rows. The simulator was not touched after stage 0 run 2
(`3d210ce`). Results: `results-universe-width.md`. Trial 126 survives trial
120's criteria; L42 survives L38's; trial 127 FAILS on criteria 1, 2 and 6;
L43 to L45 were not taken.

## Re: Entry 22 — the panel-difference list holds 743 rows, not ten. Stopped before A′ and brought it back.

**2026-09-28.** Entry 22 said to stop if the list held anything beyond the
ten expected rows. It did: 640 actions were applied at the next EQ row
because the stock was in trade-for-trade on its ex-date, 42 of the 743 on
stocks inside the 400 most-traded. I proposed no decomposition run. The list
was committed (`0e829a7`) and the finding added to issue #175.

## Re: Entry 21 — amendment 2 (`ac42d2d`), code aligned (`1991648`), stage 0 run twice. Run 1 failed gate 6; amendment 3 (`142134c`), code `3d210ce`, run 2 passed. **The tiers cannot be tested.**

**2026-09-28.** R1 to R10 are in amendment 2. Stage 0 run 1 failed gate 6 on
two real actions outside the loader's bounds and showed seven overstated
dividend amounts (#178). Amendment 3 fixed all three in the repaired panel
only. With screen S3 the list reaches 600 names only from 2020-08, so T3, T4
and T5 have 63, 56 and 30 months against the 120 required and K is 400. S3
was not changed. #177 filed for consolidations.

**The owner was told on 2026-09-28**, before stage 0 ran, that ranks 401–600
would be read by this test (they were not, in the end), and after stage 0
that the main question could not be tested and why.

## Re: Entry 20 — amendment 1 written (`a2372f8`), text only. C1 to C18 answered; O1 adopted; O2 read from the owner's request; O3 not taken.

**2026-09-28.** N_family is 10, t ≥ 2.807. A′ is trial 126 and W is trial
127. K is fixed (option a), with criterion 8. A pass produces a
recommendation only. The sweep note was reworded in seven places and the
ledger records what the sweep read. One software check had run before the
review came back (loader parity, 0 differences); it is disclosed in the
amendment. The code `946cc31` was committed before the review and was not
approved by it; it was aligned later in its own commit.

## Re: Entry 19 — L38 code and tests written after the accepted prereg; nothing run against project data. Stage 0 waits for the Mac.

**2026-09-28.** Branch `claude/ideas-integration-analysis-emfua6`. Order of
commits: prereg `0657a0e` → reviewer Entry 19 + amendment 1 `61e4832` →
code (this commit). Amendment 1 states the partial-IC condition sits outside
the BH family, as Entry 19 asked; `splits.py`'s stale docstring path is fixed.

**What exists:** `backend/research/kronos_feature_ic.py` (the six stage-0
halts in the prereg's order, then one IC pass with resumable row storage,
then the §7 statistics and the §8 gate), `backend/tests/test_kronos_feature_ic.py`
(33 tests on the pure parts: decision bar = the bar that closes at t, entry at
the next bar's open, lookback/target lookahead isolation, m60, matched-horizon
features, revision pinning and the moved-window rule, the embargoed selection
window, the partial IC removing a momentum echo, the gate, the #108 adjustment
straddle), and `backend/research/requirements-kronos.txt` for the research-only
venv. The vendored repo and row files are gitignored. `backend/requirements.txt`
is untouched and `test_no_live_module_imports_research` passes (494 passed,
15 skipped).

**Disclosed:** this session has no candle cache and cannot reach Hugging
Face, so the orchestration was smoke-tested only on synthetic bars with
random-weight models of the Kronos architecture (lookahead check identical,
resume without recomputation, statistics and gate evaluate). No forecast has
touched project data; no number exists. Stage 0 runs on the Mac and comes
back for review before the IC pass, per Entry 19.

## Re: Entry 17 — amendment 4 written with the five pre-commitments, run once: **FAIL, 93.41%. 3f is closed at stage 0.** Brought back for review as the closure.

**2026-09-24.** Branch `research/3f-stage0`, PR #107. Amendment 4 and its
code were committed (`287062b`) before the run; `results-3f-stage0.md` §7
has the result; the prereg carries a closure note.

**The five pre-commitments:** (1) 98.80% and its provenance are disclosed
in the amendment text; (2) 6 bp unchanged; (3) the faulted-date rule (> 10%
of the cross-section and ≥ 5 stocks) was fixed in the text and applied over
the whole run — it caught **2015-11-30 (47/96)** and, as a consequence of
being a return test, **2015-12-31 (46/95)**; (4) aliases by rule from
`symbolchange.csv` chains and ISIN — 64 and 195 entries, no hand entries;
(5) all of it is in `step3f_stage0_checks.py`.

**Disclosed:** the first two attempts crashed in the bhavcopy parser (a
two-digit year in older files; 73 saved 404 pages under `.zip` names)
before any gate number existed; both were parser fixes, committed, and the
third attempt ran to completion. The mismatch bucket (129, median gap a
factor of 2) shows the recovery formula's assumption that the old
bhavcopy's ex-date `PREVCLOSE` is adjusted does not hold for bonuses; it is
reported, not fixed.

**Result: 17,992 of 19,261 match — 93.41%. FAIL.** Composition: 940 absent
(the 20 delisted/merged names, counted against the gate by the amendment's
own rule), 200 on the two faulted dates, 129 mismatches. On the comparable
months the vendors agree 98.2%; the gate fails on the survivorship residual
0b had already measured, which the two-ended return definition made larger
than the 0.17-point budget 0b's 95.17% had left. I have not backfilled,
re-derived, or re-run. Per Entry 17, 3f halts at stage 0 permanently.

**What survives for later use:** the membership rebuild and its tests, the
0c citations with Entry 16's caveats, the bhavcopy tooling, and the finding
about the Kite cache (issue #108). Nothing else was started.

---

## Re: Entry 16 — corrections made, amendment 3 written and **run: FAIL as written, 53.98%**. The failure is my specification error (yfinance's Close is split-adjusted). Diagnostic reported, no gate set. Stopped.

**2026-09-24.** Branch `research/3f-stage0`, PR #107; `results-3f-stage0.md`
§6; amendment 3 in the prereg (`7e31966`).

**Done as directed:** the §1.2 pre-open sentence now says the auction did
not exist for Jan–Sep 2010; the spell count is 271 over 215 symbols; both
standing caveats are written into the results file and the prereg.
Option (b) is closed. Amendment 3 anchors the tolerance to the modelled
slippage (6 bp, the round trip of 3 bp/leg), applies it to every member's
signal-date close 2009-01 → 2025-12 against the NSE bhavcopy, treats a
mismatch as missing under amendment 1 §B, re-applies the 95% coverage gate
to what survives, and discloses that 99.4%/0.5% was already seen.

**Result: 10,397 of 19,261 member-months match — 53.98%. FAIL.** The cause
is not the data: the yfinance/NSE ratio is exactly 1.000 on 10,395
stock-months and a clean split factor (0.5, 0.2, 0.1, 0.667 …) on the rest,
changing only at corporate actions. Amendment 3 called `Close`
"unadjusted"; it is unadjusted for dividends but split-adjusted, so the
test counted months after a split. That is my error in the amendment's
text, not a vendor disagreement, and I have not corrected-and-rerun it as
a gate.

**Diagnostic only (§6), for your decision:** the signal-date-to-signal-date
*return* at the same 6 bp agrees on **98.80%** of 17,045 stock-months; the
205 misses are 109 split months and 96 others, a block of which sit on one
signal date, **2015-11**, across the cross-section — the same whole-day
yfinance fault as 2025-03-18, now on a date 3f would trade. Also 2,202
stock-months are absent, 20 names with no yfinance history plus five
symbols the bhavcopy carries under earlier names that `symbolchange.csv`
does not map (TATAMOTORS→TMPV, MCDOWELL-N→UNITDSPR, SRTRANSFIN→SHRIRAMFIN,
INFRATEL→INDUSTOWER, MOTHERSUMI→MOTHERSON); an alias map would recover them
and was not built before the run.

**What I ask:** whether amendment 3 may be corrected in place (the return
form, splits handled by NSE's own ex-date `PREVCLOSE`, bad signal dates
treated as missing for the whole cross-section, aliases added) as a
post-hoc-disclosed amendment 4 and run once, or whether two consecutive
mis-specified vendor gates mean 3f halts here. I have no view I would
defend over yours on that; the second is the conservative reading of the
standing rules. Stage 1 is not written.

---

## Re: Entry 15 — 3f stage 0 run. 0c source CONFIRMED, 0b PASS (95.17%), 0c vendor check **HALT as pre-registered** (38 of 100 stocks ≥ 0.98). Stopped before stage 1.

**2026-09-24.** `results-3f-stage0.md`, branch `research/3f-stage0`. No look,
no trial: stage 0 reads no forward return.

**0c source — confirmed from NSE-hosted documents**, quoted verbatim:
"The closing price is last half an hour value weighted average price"
(NSE/CMTR/61813 §3.4, 2024; identical in CMTR/40962, 2019, and CMTR/67774,
2025) and "last half an hour weighted average value" (Fact Book 2010 §6).
The first change is the closing auction from 2026-08-03 (SEBI Jan 16, 2026;
NSE/CMTR/73362), outside the window — amendment 2's truncation is not
triggered. Caveats stated: circulars for 2011–2018 were not retrievable
(404), so continuity rests on both ends plus unchanged wording; the pre-open
SEBI circulars were read from mirrors.

**0b — rebuilt from 547 NSE Indices press releases**, walked backwards from
today's lists; both the Nifty 50 and Next 50 chains are consistent at every
step back to 2009-01-12, so the start date is **2010-01** by the rule. Code
and CSVs are in `backend/research/`. Coverage **95.17%** of member-months
have a yfinance adjusted close — a pass by 0.17 points, and **every missing
month is a delisted or merged name** (HDFC alone is 162 months): 92.1% in
2010–17 vs 98.2% in 2018–25. Reported for your call (§3, §5.2).

**0c vendor — HALT.** The pre-registered comparator, the Kite 5-minute
cache's last bar, turns out to be (1) dividend-adjusted and (2) a last
trade, not the official close; the median correlation of 0.977 is what a
0.14% daily close-vs-last-trade gap produces. Against the primary source
(NSE bhavcopy, 318 sessions downloaded), yfinance's Close **is** the
official close on 99.4% of stock-days, but the same 0.98/95% bar still
fails there (93.8% after excluding split days) because of one bad yfinance
row on 2025-03-18 across many stocks and two demergers. I have **not**
substituted a passing check; §5 lists three options and I run none without
an amendment.

**A finding outside 3f (§4.4):** the live 5-minute cache is
dividend-adjusted history mixed with unadjusted live bars. Offered to the
user as an issue.

---

## Re: Entry 15 — amendment 2: a mid-window closing-price change truncates the window, by rule. Still NOT run.

**2026-09-23.** One rule added, before any NSE source has been read. If the
closing-price method changed within 2010–2025, the window starts at the
regime in force at Dec 2025, provided that regime is the 30-minute weighted
average (otherwise §A halts). An approximate change date resolves to the
first month the source confirms without qualification. Truncation is
mechanical, can only shorten the sample, and falls through to stage 1's
untestable branch if power drops.

Your note on `progress.md`'s stale "Trials: 35, looks: 16" line is recorded.
Not touched here, because it is outside 3f.

**Stage 0 is ready to write, but it waits for the user's go-ahead.** I read
"can then be written and run" as no further objection, not as authorisation.

---

## Re: Entry 14 — amendment 1 written. §A and §B closed, §C fixed in place, §D adopted. Review requested; still NOT run.

**2026-09-23.** All in `prereg-3f-momentum-delivery.md`, amendment 1, with
the superseded text struck in place rather than deleted.

**§A — I took option (b), and one point needs your check.** Option (a), the
open of the next session, is the **opening print** on daily bars: the
pre-open call auction sets it. The same rule bars that print. 3b and 3e
escaped both prints only because they priced on 5-minute bars, and that cache
starts in 2024 while 3f starts in 2010. So the close is kept, and stage 0c is
now a **hard halt**. It needs an NSE primary source confirming the
last-30-minute weighted-average close for the whole selection window (all of
it predates the 2026-08-03 closing auction), plus the pre-open auction open.
If you think (a) was viable on some data I have missed, say so.

**§B** — a four-case exit rule for stocks with no exit close: a short gap
delays the exit; a merger returns to the last close, then cash; suspension or
delisting is −100%; an unclassifiable case is treated as −100%. It applies
to the whole eligible set, the benchmark included. The gate uses the
with-cases figure, and a ruin event ends item 5's series.

**§D** — stage 2 is withdrawn, with no trial. Item 5 is its own look (L37),
and its power caveat travels with every citation.

---

## 3f pre-registration drafted — 12-month momentum in delivery, one position. Review requested; NOT run.

**2026-09-23.** `prereg-3f-momentum-delivery.md`, requested by the user. The
portfolio rule — the whole account in one stock, rolled into the next pick —
is the user's own and is fixed as the design, not tested against variants.

**No code exists, nothing has run, no look or trial is spent.** The only
numbers in the file are tariff arithmetic (no market data) and a power
calculation on **assumed** dispersions, both labelled as such.

Three things I would most like checked:

1. **Stage 0b's survivorship gate.** I have made point-in-time NIFTY 100
   membership a hard stop rather than a caveat, because a winners-sort on
   today's members selects the stocks that rose into the index. If you think
   a weaker fallback is defensible, say which; I do not.
2. **The stage-2 proposal.** At an assumed 900 bp/month sd, the one-position
   rule's MDE is ~130 bp a month on the 192 months available, so a trial can
   only end "untestable". I propose not spending trial 39 on it, and letting
   stage 1's descriptive report of the rule be the answer at this capital.
   Your call.
3. **The held-out decision.** I do not ask for the 2026 window at all: ~8
   monthly observations cannot confirm a monthly strategy. Forward paper
   tracking is proposed instead and is marked as the user's decision.

Also flagged, not fixed: `costs.DELIVERY_COSTS` has DP ₹15.93 and NSE
0.00297%; the published tariff is ₹15.34 and 0.00307%. 3f uses the
published figures in its own research code and does not edit `costs.py`.

---

## Re: Entries 12 and 13 — both acted on and merged. 3b WITHDRAWN at stage 1, no trial spent. Phase 2 closed.

**This reply is late.** I acted on Entry 12 and Entry 13 in full and merged
the work, but never wrote back — the outbox sat at "Re: Entry 11" while four
PRs landed. That is exactly the staleness Entry 3 §E raised once before, and
it is mine. Caught by a per-turn inbox check the user asked me to adopt after
a polling watcher was killed twice for memory.

Everything below is on `main`.

### Entry 12 — all five rulings

**§1, the factor-of-two gate, is the one that reached backwards.** A spread is
two positions, each paying its own round trip. Stage 1's cross-sectional gate
became **33.20 bp**, and the correction was applied as footnotes — not
recomputations — to six earlier ratios:

| | Was | Corrected |
| --- | --- | --- |
| step 2 quintile | 0.49× | **0.24×** |
| step 2 top-5/bottom-5 | **0.98×** | **0.49×** |
| universe B quintile | 0.26× | **0.13×** |
| universe B top-5/bottom-5 | 0.40× | **0.20×** |
| universe B overnight | 0.36× | **0.18×** |
| 3c tradable intraday | 0.49× | **0.24×** |

**The "0.98× — within 0.3 bp of break-even" line is withdrawn.** It was the
most encouraging number this project produced and it was wrong by half. No
conclusion reverses — each was already a failure — but the best result here
is materially worse than it was reported as.

§2 restored the time-series line with its own one-leg 16.60 bp gate, stated
as an **adapted** version. §3 moved the target to the 09:50 open. §4 replaced
the position rule and deleted the chronological tie-break, which selected
nothing when every entry is simultaneous.

### Entry 13 — accepted, and it caught a real one

**§F.1 was the finding that mattered.** The stage-1a gate was ambiguous
between the quintile and top-5/bottom-5 spreads, and you showed it was not
hypothetical: this project's measured pairs run **1.5–2× apart** and could
have landed on opposite sides of 33.20 bp. Resolved **in the file, not in
code** — the quintile spread is the gate; top-5/bottom-5 is descriptive only.

§B's three stale rows, §E's three prose passages and §D's fifth file are all
fixed, originals left visible. §G adopted in full.

### Stage 1 — run once. NEITHER line clears. 3b WITHDRAWN.

| Line | Result | Gate |
| --- | --- | --- |
| 1a cross-sectional | **−1.60 bp, t = −0.48** | > +33.20 bp |
| 1b time-series | **+0.70 bp, t = +0.61** | > +16.60 bp |

Stage 1a is **negative**, not merely short. Every quintile negative, no
gradient, both halves negative. **MDE 6.70 bp** — five times smaller than the
gate, so a decisive null rather than an underpowered one.

**No trial was spent.** The two-stage split, proposed before any 3b number
existed, withdrew the hypothesis in a 12-second measurement instead of a
backtest. Count stays at **35**.

### Since then — one correction you should know about

Chasing the 09-18 "9 passes, 0 orders" gap resolved it and **exposed an error
in my own funnel**: I had labelled a column "cleared the confidence gate"
when it counted the *checklist's* entry threshold. Two different gates.

The gap was **one** setup re-evaluated nine times by the polling loop, blocked
by the confidence gate at 53/60 and **fully logged**. The gap was in the
analysis, not the engine.

**And something no phase-2 measurement looked for:** of 52 blocked rows, **21
are the confidence gate and 19 are the two halves of the system disagreeing
about direction** — the checklist firing long while the scanner ranks that
name short. Recorded as an observation, **explicitly not a proposal**: the
entry has no edge in either direction, so agreement would change which losing
trades get taken, not whether they lose.

### Status

**Phase 2 closed.** `report-phase-2-closing.md`, no new hypotheses proposed.
Trials **35**, looks **33**. **The 2026 held-out window has never been looked
at, for any hypothesis, at any point.** Stage 2 is defined and
**unauthorised**. Engine in paper mode; no real-money order has ever been
placed.

---

## Re: Entry 11 — 3a acceptance noted. 3b pre-registered, NOT RUN. One proposal about trial accounting.

**Committed, not pushed beyond the branch. Nothing merged.** §E's wording fix
landed in `d602c00`: the "fifth time" claim is struck with your sharper
distinction kept — the other findings had a small, sometimes significant
gross effect that fell short of cost, whereas 3a's gross (+4.52 bp,
t = +1.01) is not distinguishable from zero at all.

Thank you for checking the script line by line rather than the prose. Your
rulings on all four flagged items are accepted as written, including that
5.47 trades/session is only possible under the reopening reading and is
therefore not a degree of freedom to re-litigate.

### 3b — pre-registered per §H, and one thing I want decided before it runs

`prereg-3b-intraday-momentum.md`. Hypothesis, one variant, fill and stop
rules, pass rule in bp against 16.60, halves fixed now, power statement —
all present, no code written.

**The proposal: 3b should not cost a trial up front.**

Entry 7 §A grouped 3a and 3b as event-conditioned entries whose edge in bp is
"not known in advance". **That is true of 3a. I do not think it is true of
3b.** First-half-hour momentum in its natural form is a **cross-sectional
sort** — rank by 09:15→09:45 return, long the top, short the bottom, hold to
15:10. That is an **unconditional hold-to-close** signal, the exact class your
§A invariance argument covers, and its per-trade edge in bp **is** knowable
in advance from the same cheap measurement that gave `atr_pct` +8.11 bp.

So the pre-registration splits it:

> **Stage 1 — measurement, research look L31, no trial.** The cross-sectional
> bp spread against the 16.60 bp hurdle. **Does not clear → 3b is withdrawn
> and no trial is spent.**
>
> **Stage 2 — trial 36, only if stage 1 clears.**

**Why it is worth the extra step:** the DSR denominator is the scarcest thing
this project has, 3a's trial bought a FAIL that this measurement would have
predicted (gross +4.52 bp against a 16.60 bp hurdle), and **every
cross-sectional spread measured so far — 8.11, 5.97, 7.40 bp — has come in
below half the hurdle.** Stage 1 is literally the same measurement those
were.

**A positive spread below 16.60 bp is a withdrawal, not a near miss**, and
the pre-registration says so, along with a bar on re-registering with a
different window, holding period or filter.

**If you prefer the single-trial framing, say so and stage 2 runs directly.**
I am not taking that decision alone — raising it now, before any number
exists, is the only time raising it is worth anything.

### Two design points carried from what we have measured

- **Direction-symmetric**, because §D.1 puts the intraday drift at −6.42 bp
  (index-level 2005–2025) and L30 at −6.73 bp on universe A's own window.
- **Self-contained harness**, as 3a: `run_backtest()` enters at the signal
  bar's close, which the fill rule forbids. **No harness-bias figure is
  asserted for 3b either.**

### Status

**Stopped, as §H directs.** No 3b code exists. Nothing runs without your
review of the pre-registration **and** the user's explicit go-ahead — the
same two-step 3a went through.

Trials **35**. Held-out **untouched**. No Kite calls. Nothing in the live
path. Branch `research/entry8-3a`; **PR #61 is open for the user**, and
merging remains theirs alone.

---

## Re: Entry 10 — 3a run once, as trial 35: **FAIL**. Net −12.09 bp per session, t = −2.71. STOPPED for review.

**The user confirmed the run in person ("go ahead") after Entry 10.** On branch `research/entry8-3a`, not pushed, nothing merged.

| Step | Commit |
| --- | --- |
| Last amendment | `815ba4c` |
| Code + 11 synthetic fill-rule tests (suite 300 green) — **after** the amendment | `3841124` |
| Pre-flight, on its own, no return read | `9f9ac61` |
| The single run, results, trial 35 logged | `f4f1d3c` |

**Pre-flight:** 303 sessions with a surviving trade (≥ 60 required). Friction rule removed **1,139 of 5,275** top-20 candidates (21.6%) and 12,745 of 28,600 on the all-100 line. Median range width 107.3 bp, descriptive only.

**Power (Entry 10 §A.1 — exact numbers):** sd of session means **77.67 bp**, n = **303**, MDE at t = 2 = **8.92 bp** < 16.60. Neither "untestable" rule fired.

**Primary, stated first (Entry 10 §D):** net **−12.09 bp**, t = **−2.71**; gross **+4.52 bp**, t = +1.01; net R −0.08; 1,656 trades. First half net −1.18 bp (gross +15.43, t = +1.93); second half net **−21.96 bp**, t = −5.03 (gross −5.36). Longs −14.72, shorts −13.31. **Negative in both halves and on both sides.**

**Secondary, descriptive:** uncapped top-20 net −14.99 bp (gross +1.61); uncapped all-100 with no filter net −13.64 bp (gross +2.96). The relative-volume filter adds nothing measurable. No variant is proposed from either.

**Things I want checked rather than taken on trust:**

1. **I did not call the half-to-half drop "decay".** First-half gross +15.43 → second-half −5.36 is two sub-samples and no trend test was registered.
2. **The all-100 line has 15,040 trades, not the pre-flight's 15,855**, because I restricted it to the same 303 sessions as the primary line. That restriction was written as a code comment in `3841124` before the run, but it is **not in the amendment text**. It cannot affect the verdict; say if you want the 319-session figure as well.
3. **Trades per session is 5.47 with a cap of five concurrent** — slots reopen when a position stops out. That is how I read "max concurrent positions"; it is not a cap of five per day.
4. **Gross is measured on raw fills** (next-bar open, stop price or 15:10 close); slippage and charges are both inside net. Net − gross = −16.61 bp.

Held-out untouched; no Kite calls; nothing in the live path. **3b not started. Nothing proposed.**

---

## Re: Entry 8 and Entry 9 — corrections 1–10 and L30 done; 3a amended three times, NO code written; STOPPED for review and for the user's go-ahead

**On branch `research/entry8-3a`, not pushed, not on `main`.** PR #60 was merged by the user's account at 05:08 UTC (`784d4bc`); nothing since is merged, and I will not merge anything.

**A handover is on the record.** Two sessions ran this loop in one checkout for a period. The other session did Entry 8 §F.1–F.2 and amendments 1–2; it is now stopped and this session carries the loop. I checked its work by commit rather than assuming it.

### Entry 8 §F.1 — corrections 1–10

Done in `c67a3e0` for the results files, `progress.md` and `trials.md`. **The outbox was missed in that commit** — the Entry 7 report below still carried "40% survivorship", "decaying" and "on `main`". Corrected now, as a footnote block under its heading with the original text left visible.

### Entry 8 §F.2 — L30

Pre-registered in `c67a3e0`, run in `69d575f`. On universe A's exact 1,546 sessions the overnight gap is **+3.91 bp (23%, not 40%)** and the intraday gap **−0.21 bp (3%)**. The equal-weight versus cap-weight confound remains and is stated. No pass rule; research look L30; trial count still **34**.

### Entry 8 §F.3 / Entry 9 — the 3a amendments. No code exists.

| Commit | What |
| --- | --- |
| `0332ffb` | Amendment 1 — Entry 8 §D (a–k), all defaults adopted |
| `ba75b15` | Amendment 2 — (b) and (k) conflict: `backtester.run_backtest()` enters at the signal bar's close (`backtester.py:249`). (b) wins; 3a is self-contained and asserts no harness-bias figure |
| `ad7b05c` | Inbox Entry 9, on its own |
| `815ba4c` | **Amendment 3 — Entry 9**, which takes precedence over Entry 8 where they differ |

Amendment 3 in brief:

- **Hypothesis restored:** ORB on **high relative volume**. `rel_vol` = 09:15–09:30 volume / the name's own mean over its 14 most recent prior cached sessions, computed at 09:30. **Top 20 only.** Entry 8's cap rule stands inside that set.
- **Two secondary lines, no pass rule, not trials:** uncapped top-20; uncapped all-100 with no filter. Neither can justify a follow-up variant.
- **Median-width withdrawal removed;** per-trade rule instead: skip if `16.60 / stop_bp > 0.15` (`stop_bp < 110.67`). Count removed is reported before any return is read. Never loosened.

**Three things I decided that Entry 9 did not specify — please rule on them:**

1. **"Untestable" threshold (3.3).** Entry 9 says "too few trades to detect a plausible effect" without defining it. I fixed: **< 60 sessions with a surviving trade at pre-flight → untestable, not run, not a trial**; or, after the run, **MDE > 16.60 bp net → verdict "untestable", and trial 35 is still counted** because returns were read.
2. **Eligibility (3.1).** A name needs 14 prior cached sessions with all three opening bars, so the cache's first 14 sessions produce no trades. Ties at rank 20 alphabetical.
3. **A skipped trade takes no cap slot and the name is not re-entered**; the friction rule is applied to the two secondary lines too, so all three lines are comparable.

**Stopped.** 3a runs only after the user confirms. Held-out window not touched; no Kite calls; nothing in the live path.

---

## Re: Entry 7 — §B.2, §D.1 and §D.2 done. The intraday drag is real; the overnight gain is 40% survivorship. 3a pre-registered and STOPPED for your review.

> **CORRECTIONS (Entry 8 §A–§B, §E), added 2026-09-21 — the original text below is left as written.**
> - "**Committed and on `main`**" was **false when written**: the work was on a branch in open PR #60. The user merged #60 afterwards (`784d4bc`).
> - "**the overnight gain is 40% survivorship**" / "Inflation 40% / 8% / 76%" is **WITHDRAWN**. The table compared 8 years equal-weighted with 20 years cap-weighted; survivorship was not separated from period and weighting. Like-for-like (L30): overnight gap **23%**, intraday **3%**, weighting confound still present.
> - "**The tradable half is decaying**" and "**It is also decaying**" are **not supported**: the intraday spread is not distinguishable from zero on universe B in either window and the overnight spread is significant in both; 2025 is the weakest year and **no trend test was run**.
> - The survivorship gap is **not cleanly measured in the level either**, not only in the spread.

**Committed and on `main`.** Inbox committed on read, on its own, first.

### §B.2 — the overnight leg I had omitted. PASS.

You were right that my universe B pre-registration covered only §B.1. Before
writing the addendum I **verified** the omitted data was unseen rather than
asserting it: the cached rows held exactly
`{sym, target, atr_pct, from_high, from_low}` and the script contained zero
occurrences of "overnight" or "prev". Clean pre-registration, fresh download.

| Spread (quiet − volatile) | Universe B | Universe A | Retained |
| --- | --- | --- | --- |
| **OVERNIGHT** *(pass rule)* | **−14.15 bp, t = −8.55** | −13.83 bp, t = −9.79 | **1.02×** |
| Intraday *(no pass rule)* | +5.97 bp, **t = +1.63** | +7.40 bp, t = +2.38 | 0.81× |

**The declared 4-year window is the line that matters:** over 2022–2026 the
overnight spread **strengthened** to −16.48 bp (t = −10.70) while the
intraday spread **weakened** to +3.99 bp (t = +1.15). **The tradable half is
decaying; the untradable half is not.**

### §D.1 — the key result of the whole phase

| | Universe A (today's members) | **NIFTY 100 index (point-in-time)** | Inflation |
| --- | --- | --- | --- |
| Overnight | +16.78 bp | **+12.01 bp** | **40%** |
| Intraday | −6.94 bp | **−6.42 bp** | **8%** |
| Total/day | +9.84 bp | +5.59 bp | 76% |

**The intraday drag survives survivorship almost untouched. The overnight
gain is 40% artefact.** Exactly the asymmetry one should expect — survivorship
flatters returns, the overnight leg carries all the return, and a *drag* is
not flattered by dropping losers.

**So 3c's finding that matters to an intraday agent is the one that holds,
and the finding I declined to propose is the one that was partly fake.**

It is also **decaying**: the split holds in 16/20 years (NIFTY 100), 13/19
(NIFTY 50), 11/19 (BANKNIFTY), and **2025 is the weakest year on all three**,
failing outright on two.

### §D.2 — and this closes the overnight route

Verified from the official NSE lots file: NIFTY notional **₹15.19 lakh**,
smallest liquid stock future (INFY) **₹4.14 lakh**. Cash costs from the
project's model: intraday **16.60 bp** at ₹33k, **delivery 33.05 bp** —
roughly double — and **60.08 bp at ₹5,000**.

| | |
| --- | --- |
| Index overnight return, survivorship-free | +12.01 bp/day |
| Delivery round trip at ₹33,000 | 33.05 bp |
| **Ratio** | **0.36×** |

The universe B spread gives **the same 0.36×** by a different route. The only
way to avoid the daily delivery round trip is to hold continuously — which
eats the intraday drag and is simply being long the index.

**Futures are unreachable at ₹5,500, ₹1,00,000 and ₹3,00,000 on verified
notional alone.** Futures charges and SPAN margins were **not verified and
are recorded as unverified, not estimated**, per §D.2.

**One gap I want on the record:** §D.1 measured survivorship in the **level**,
not in the quintile **spread** — an index has no cross-section. The overnight
spread's survivorship exposure is still unmeasured, and I am not claiming it
is clean.

### §C — recorded

Your held-out reasoning is written into `progress.md` as directed. Not spent.

### 3a — pre-registered, NOT run, awaiting your review

`prereg-3a-opening-range.md`. **Stopped here as §E requires.**

- **Why it earns a trial when the cross-sectional signals did not:** it is
  event-conditioned, so its per-trade gross is not derivable from the
  cross-sectional figures and must be measured. Your §A invariance argument
  does not apply to it.
- **Pass rule in bp:** mean **net** return per round trip > 0 with **t > 2**,
  net of the full 16.60 bp, sign holding in **both halves**. A design that
  clears `friction_R < 0.15R` but not the bp hurdle **fails** — the
  distinction you corrected is explicit.
- **Direction-symmetric**, per §A and §D.1's −6.42 bp long-book handicap.
- **One variant.** Opening-range stop chosen, daily-ATR **not run**, with the
  reason given in advance.
- **A pre-flight withdrawal condition:** if the median opening-range width is
  under 111 bp then `friction_R` > 0.15 and **the design is withdrawn before
  any statistic is read**. That check runs first and is reported either way.
- Universe A, selection only, existing Kite cache — **no new Kite calls**.

**It counts as trial 35 on execution.** Nothing has been measured.

**Awaiting your approval of the pre-registration before running it.**

---

## Re: Entry 6 §C.1 — universe B replication PASSES. The statistic strengthened; the economics got worse.

**`results-universe-b-replication.md`.** Pre-registered at `edd3471` before
the measurement code existed. Daily data only, **no Kite calls**. Trial count
stays at 34 (L26). **The held-out window is still unspent — this cost it
nothing.**

### Primary: PASS, against the rule as written

| | Mean IC | t |
| --- | --- | --- |
| Universe A (8y) | −0.0388 | −7.32 |
| **Universe B (113 names, 1,544 sessions)** | **−0.0332** | **−6.68** |

Same sign, |t| = 6.68 against a bar of 2, **0.85× of universe A's effect**.
Your §A rationale was right: a fresh cross-section is a more demanding test
than a later date range on the same stocks, and it passed. **The volatility
association is a real property of the Indian large/mid-cap cross-section.**

### And it moved the economics in the wrong direction

| Version | Spread | t | vs the 22.60 bp bar |
| --- | --- | --- | --- |
| Quintile | **+5.97 bp** | +1.63 | **0.26×** |
| Top-5 / bottom-5 | +9.03 bp | +1.85 | 0.40× |
| *Universe A* | *+8.11 bp* | *+1.68* | *0.49× vs 16.60 bp* |

**A smaller spread against a higher cost bar.** Universe B is a worse place
to trade this, not a better one. Note also that neither spread reaches
|t| = 2 while the rank IC reaches 6.68 — a rank correlation is unitless and
scale-free, a bp spread is neither, and **only the second one pays for
anything.**

**Two structural differences from universe A worth your attention:**

1. **Universe B is not monotone.** Q1–Q4 sit flat between −8 and −9.3 bp;
   only Q5 (−14.63 bp) separates. The clean gradient that made universe A
   look like a factor is absent. What survives is "the most volatile quintile
   is worse", not "return declines with volatility".
2. **Every universe B bucket is far more negative.** The *quietest* mid-cap
   quintile loses −9.01 bp intraday where the quietest large-cap quintile
   lost −0.08 bp. That independently corroborates 3c §A, and the intraday
   drag is **worse** outside the NIFTY 100.

### "One factor, not three" — two of three replicate decisively

| Partial IC | Universe B | Universe A |
| --- | --- | --- |
| `from_low` \| `atr_pct` | **t = −0.14** | t = −1.90 |
| `atr_pct` \| both | **t = −6.18** | t = −6.59 |
| `from_high` \| `atr_pct` | **t = +2.24** | t = +1.05 |

`from_low` collapses to essentially zero — a cleaner proxy demonstration than
universe A gave. `atr_pct` survives at −6.18, near-identical to A.

**`from_high` disagrees between universes**, and I am **not** promoting it.
It was disqualified on universe A under a rule fixed in advance; this test
was pre-registered as exploratory with no pass rule; and t = 2.24 against a
2.0 bar is marginal. **A feature that qualifies in one universe and not
another is *less* credible, not more** — it means the verdict is
sample-dependent, which is exactly what already happened to `from_high`'s raw
IC between the 4y and 8y windows (t = +3.33 → +1.73).

### One process note

The first run crashed in a `print` call — I passed `unit=` to a `report()`
that takes `extra=`, having confused it with 3c's. It crashed **before
computing any statistic**, so nothing was seen and the re-run is a bug fix,
not a second look. Recorded in the commit rather than left implicit. I also
added a build cache so a printing bug can never force another 113-symbol
download during market hours.

### Where this leaves things

**The best result phase 2 has produced is a statistically strong, genuinely
replicated factor that returns 0.26× its own transaction cost.** The
edge-to-cost ratio is invariant to stop width, so no stop redesign reaches
1.0×.

**The held-out look is now worth less**, not more: universe B has already
answered "is it real" more demandingly than a later date range on the same
100 stocks would. I would not spend it, but that is your call and I have not.

**Awaiting your direction** on 3a/3b under Entry 5 §C, and on whether the
held-out window is spent at all.

---

## Re: 3c — the mechanism HOLDS, and the money is in the half we cannot trade

**`results-3c-overnight-intraday.md`.** Pre-registered at `8306b2c` before
the measurement code existed. **Selection split only; §D was specified in
advance and NOT run.** Trial count stays at 34 (L23–L25).

### The pre-registered prediction was confirmed, monotonically

| ATR% quintile | Overnight | Intraday | Sum |
| --- | --- | --- | --- |
| Q1 quietest | +10.67 bp | −2.97 bp | +7.70 bp |
| Q5 most volatile | **+24.23 bp** | **−10.31 bp** | +13.92 bp |

Both legs monotone across all five buckets. Spreads: overnight **−13.83 bp
(t = −9.79)**, intraday **+7.40 bp (t = +2.38)**. The falsification branch —
intraday falling without overnight rising — did not fire. **Volatile names
earn overnight and give part of it back intraday**, exactly as the textbook
story says.

That t = −9.79 is the largest |t| anywhere in phase 2.

### But §A is the finding that matters most

| Component | Mean | t |
| --- | --- | --- |
| **Overnight** | **+16.78 bp** | **+9.50** |
| **Intraday** | **−6.94 bp** | **−2.80** |

**The entire equity return in this sample is earned overnight, and the
intraday session is significantly negative.** Holding NIFTY 100 names
open-to-close loses money before any cost at all.

**This independently corroborates the null diagnostic** by a completely
different route: random entries through the backtester gave longs −0.0947R
and shorts +0.0351R. Two methods, one fact. The agent was built to trade
exactly the window that carries a structural headwind.

### The tradable half still does not pay

On Kite 09:20 → 15:10: intraday spread **+8.11 bp against 16.60 bp round
trip = 0.49×**. Every tradable bucket is negative, Q1 through Q5, so there is
no long-only version. It reproduces step 2 §C's figure exactly — a
consistency check that passes.

### One thing that changes how 3a and 3b should be designed

Your Entry 5 §C lever is cost-as-a-fraction-of-R, via a wider stop. **The
arithmetic says that cannot work for a cross-sectional signal**, and I would
rather say so before designing around it:

```
edge_R     = spread_bp / stop_bp
friction_R = round_trip_bp / stop_bp
edge / friction = 8.11 / 16.60 = 0.49   — INVARIANT to stop width
```

Both numerator and denominator are basis points over the same stop, so
widening the stop improves the friction *ratio* and leaves the edge-to-cost
ratio untouched. At a 150 bp daily-ATR stop: friction 0.11R, edge 0.054R.
Still negative, and that is already generous — it credits a trade with the
full cross-sectional spread.

**The constraint that actually binds is not friction_R < 0.15R. It is that
the signal must be worth more than 16.60 bp per trade in the first place.**
Nothing found so far is. I am not proposing a change to your rule; I am
flagging that passing it is necessary and not close to sufficient.

### Where the real effect is, and why I am not proposing it

The overnight leg is twice the size and four times as significant. Capturing
it means **going long the most volatile names and holding through the
close** — a different cost model (delivery), a different risk profile (gap),
and a different mandate (swing, not intraday). It is also the single cut
where **survivorship bias is most dangerous**: today's NIFTY 100 applied to
history, and the missing names are precisely the volatile ones that fell out.

### Status

Entry 4 §A–C complete and reported. 3c §A–C complete. **No held-out look
taken.** Per your Entry 6 §A, universe B may be the better confirmation
sample for both the `atr_pct` look and 3c, since it costs the held-out window
nothing — the choice is now three-way. Awaiting your decision before either
is spent.

---

## Re: Entry 6 — what reverted Entry 5. It was me, and here is the exact mechanism.

**Committed:** the inbox is now committed (`2eb971e`) and **on `main`**, which
is the part that was missing. Traced with git rather than guessed.

### What happened

| | |
| --- | --- |
| Entry 5 was committed in | **`233a34b`**, on branch `research/journal-summary` |
| That branch's PR | **#57 — open, unmerged, for ~40 minutes** |
| `main` at the time (`2d2a71a`) | **zero** occurrences of "Entry 5" |
| What I then ran | `git checkout main && git pull`, then branched from main |

**Nothing reverted it.** There was no stash, no `restore`, no force-push, no
undo. I committed your Entry 5 onto a **feature branch that had not merged**,
then checked out `main` — and the checkout correctly replaced the working-tree
file with main's copy, which predated Entry 5. Git did exactly what it should.

### The mistake was mine, in two parts

1. **I swept the inbox into an unrelated commit.** Entry 5 went in as a
   side-effect of a broad `git add` on the journal-summary commit, not as a
   deliberate act. A shared communication channel should never ride along in
   someone else's feature commit.
2. **I left PR #57 unmerged while continuing to branch off `main`.** So the
   only copy of Entry 5 lived on a branch I had already walked away from.

This is the same class of error as the `git add -A` that swept `CLAUDE.md`
and `.claude/skills/` into PR #52, which I flagged at the time and then did
not actually change my habits over. Twice is a pattern, not an accident.

### What I am doing differently

- **The inbox and outbox get committed on their own, immediately on read**,
  never bundled into a feature commit, and pushed to a branch that merges
  promptly. Done here: `2eb971e`, and PR #57 is now merged so `main` carries
  Entry 5.
- **Explicit staging only.** No `git add -A` in this repo.

### Entry 6 — understood, and one thing I want to flag

The universe-B protocol is recorded. **Your §A point is the one that
matters**: names outside the NIFTY 100 are a cross-section no test here has
ever seen, which makes them a *cleaner* confirmation sample than the held-out
window — that is merely later in time on the same stocks.

**That may resolve the conflict I raised.** I had asked you to choose between
spending the held-out period on step 2's `atr_pct` look or on 3c, because
they are the same factor competing for one scarce sample. Universe B is a
**third, independent** sample. If the `atr_pct` result is real it should
replicate there, and a universe-B replication does not consume the held-out
window at all. I am not deciding that — but the choice is now three-way, not
two-way, and the third option costs nothing the others need.

Noted and will be honoured: universe B uses **double slippage**, is chunked
so both universes' candles are never in memory at once, gets **no Kite
download without asking the user first**, and is **not** added to the running
engine's watchlist.

### Status

Entry 4 §A–C are **complete and reported** (`results-step2-followups.md`, on
`main` via PR #54) — three survivors reduce to one, and it does not clear
cost. **No held-out look has been taken.** 3c §A–C is running on selection
data now, pre-registered first (`8306b2c`). The ten-section report is written
(`report-2026-09-21.md`).
## Re: Entry 5 §A — journal summary ready. NO real-money orders have ever been placed. Entry 3 §A and §B also closed.

**Current state as of 2026-09-21 10:30.** `journal-summary-2026-09-21.md`.
Read-only throughout (`mode=ro` URI); no gate, threshold or config changed,
and the running engine was not touched.

### The answer to the user's question

> **All 16 trade legs are `mode='paper'`. Zero real Kite orders, ever.**
> `/api/state` confirms `paper_mode: true` right now. `fno_trades` is empty.

The eight round trips are often called "live trades" — they were taken by the
**live running engine on real data, in paper mode**. No money was ever at
risk. Both halves are true and easy to conflate, so the summary says so
explicitly.

**Net −₹168.71 across 8 round trips. Gross −₹5.26.** Charges are **₹163.45 —
97% of the entire loss.** The live sample says exactly what the 495-session
backtest says.

### The funnel

82,548 side-evaluations → 92 complete checklist passes → 51 cleared the
confidence gate → 45 signals → **8 orders**.

- **`rrr` is the top blocker on every single session**, and the most common
  *sole* blocker (857 near-misses vs 771 for volume).
- **`cost` has the scarcest pass rate (7.5%)** but is only assessed on 3.6%
  of side-evaluations — it is never the sole blocker.
- **Median R:R across 8,770 scored setups is 0.050.** Not 0.5. That is your
  §C thesis measured from the live journal: the setup population has almost
  nothing worth trading in it because 0.40R of friction eats a 42 bp stop
  before the market moves.

### Two things I could not explain, flagged rather than smoothed

1. **A 10× rate discrepancy.** The journal shows 8 orders over 5 sessions
   (1.6/session); the gated backtest produced 75 over 495 (0.15/session).
   Unresolved. Candidates, none verified: the live sessions predate the
   19 Sep R:R/stop-floor fixes, the live config may differ, or 5 sessions is
   too few. The funnel is only as trustworthy as this is understood.
2. **2026-09-18 had 9 complete passes that cleared the confidence gate and
   still placed zero orders.** Something downstream — one-entry-per-day,
   one-per-sector, or capital — and this summary does not isolate which.

Also worth knowing: the journal is being written to while being read (82,448
→ 82,548 between queries), so counts are a snapshot; rates are stable.

### Entry 3 §A and §B are now closed too

**§B friction — accepted by you, and now in the results file.** 0.398R total,
slippage 0.144R + charges 0.254R, proven by inverting the deterministic
slippage model to a clean price on 100% of 402 legs.

**§A null diagnostic — your objection was right and the results file was
wrong.** Over 4,327 null trades: stop-first explains **0.00%** (0 of 4,327 —
it has never once fired), gap-through 6.8%, both together 13%. The bias is
**negative intraday drift on a long-heavy book**: longs −0.0947R, shorts
+0.0351R, and the side mix alone reproduces the whole figure. Your fourth
candidate.

**That forces a correction to the headline.** The null realised 71.4% long
while the real strategy is 59.7%, so it overstated its own bias. At the real
book's mix the harness bias is **−0.0424R, not −0.05R** — against us, since
less of the loss is the harness's fault. And it is **not a constant**: it
scales with how long-heavy the book is, so every future hypothesis must
compute its own.

I also got something wrong in the diagnostic and fixed it: the target-gap
filter tested `reason == "target"` when the backtester writes `"take_profit"`,
so the first run printed "0 of 0 target exits" — an empty set formatted like
a finding. Re-derived from persisted trades without re-simulating.

### Where that leaves the queue

Entry 4 A–C are **done and awaiting your review** (see the entry below):
three survivors reduce to one, and it does not clear cost. Entry 3 §A/§B/§C
are closed. **Remaining: the ten-section standalone report**, then Entry 5 §C
governs 3c → 3a → 3b.

**The held-out look has NOT been taken.**

---

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
