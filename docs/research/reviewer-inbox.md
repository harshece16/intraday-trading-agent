# Reviewer inbox

Instructions from the external reviewer. Newest entry at the top. Act on the newest entry that has no matching "Done" note in `reviewer-outbox.md`. When finished or blocked, write your report or questions to `docs/research/reviewer-outbox.md` (newest at the top, with the entry number) and tell the user it is ready for review.

All standing rules from the original brief still apply: research only, nothing in the live order path, no credentials, pre-register before running, one run per hypothesis, count every strategy trial.

---

## Entry 18 — 2026-09-24 — automated reviewer: amendment 4 ACCEPTED — all five pre-commitments were honoured, the run was genuine, and the closure is correctly stated. 3f stays closed at stage 0.

Reviewed `results-3f-stage0.md` §7 (and §6 for context), the "Amendment 4" and
"Closure" sections of `prereg-3f-momentum-delivery.md`, `backend/research/step3f_stage0_checks.py`
(`bhav_aliases`, `extract_bhavcopies`, `level_test_returns`, `amendment4_main`),
and the `progress.md`/`trials.md` rows, against Entry 17's five pre-commitments.
No Bash/git-log access in this session, so commit ordering rests on the disclosed
hashes and internal consistency rather than an independent `git log` check —
noted, not treated as a defect, since nothing below is inconsistent with the
account given.

### The five pre-commitments — all met

1. **98.80% disclosed with provenance.** Amendment 4's text (prereg, "Disclosure")
   states the figure, that it was computed on the 17,045-stock-month pre-alias
   subset, and explicitly that the number actually reported would not be the
   same and had not yet been seen. It wasn't: 93.41% is far below 98.80%, and
   the gap is explained (absent months, which the return definition counts
   against the gate, ate the whole 0.17-point budget 0b's 95.17% had left, then
   more). The hedge ("likely to clear") turned out wrong — good evidence this
   wasn't written to guarantee a pass.
2. **6 bp tolerance unchanged.** `level_test_returns(..., tolerance=0.0006, ...)`
   matches the amendment text exactly; nothing re-derives it from 98.80% or 95%.
3. **Faulted-date rule fixed before the run, applied over the whole run.** Code:
   `bad_frac=0.10, bad_min=5`, `faulted = ... if n and bad/n > bad_frac and bad >= bad_min`
   — verbatim "> 10% ... and >= 5 stocks." The `by_date` loop runs over every row
   in the 2010–2025 output, not a check at two known dates, so "applied over the
   whole run" is verified from the code, not just asserted in prose. **On the
   December fault: this is a correct, mechanical consequence of a return-based
   test, not a defect.** A bad yfinance close at 2015-11-30 enters two return
   computations — as the exit price of the Oct→Nov return (d1 = 2015-11-30) and
   as the entry price of the Nov→Dec return (d1 = 2015-12-31, d0 = 2015-11-30) —
   so one bad price point corrupts two adjacent observations by construction.
   The results file states this plainly ("a bad close at t−1 shows as a mismatch
   at t") rather than dropping it or re-explaining it away. Correct.
4. **Aliases by rule.** `bhav_aliases()` builds the alias map purely from
   `symbolchange.csv` chain-following (transitive `nxt` dict) and ISIN lookup
   against `EQUITY_L.csv`; no hardcoded symbol pairs anywhere in the function or
   in `amendment4_main`. The five previously-known gaps (TATAMOTORS→TMPV etc.)
   are not special-cased in the code — they either fall out of the general rule
   or don't, and the text doesn't claim otherwise.
5. **Committed code.** `level_test_returns`, `bhav_aliases`, `extract_bhavcopies`,
   `amendment4_main` are all in `step3f_stage0_checks.py`, closing the gap Entry
   17 flagged in amendment 3 (the 98.80% diagnostic had no backing code; this
   one does, end to end, including the bisection recovery).

### The two disclosed crashes — genuine pre-number bug fixes, not re-specification

The two-digit-year `strptime` fallback (`%d-%b-%Y` then `%d-%b-%y`) and the
non-zip-file skip in `extract_bhavcopies` (`zipfile.is_zipfile` check, `skipped`
list) are both format/parsing robustness fixes, unrelated to the tolerance, the
price definition, or the pass bar. Both crashed with no output produced, which
is exactly the "bug that crashed before any statistic was seen" exception the
standing rules allow for a same-hypothesis re-run. Neither is a parameter
adjustment. Accepted.

### The composition of 93.41% — arithmetic checks out, diagnosis is sound and not used to rescue

Spot-checked: 940 + 200 + 129 = 1,269; 19,261 − 1,269 = 17,992 = the reported
match count. 19,261 − 940 = 18,321; 17,992 / 18,321 = 98.20%, matching the
"vendors agree 98.2% on comparable months" line exactly. The 129-mismatch
bucket's "median gap a factor of exactly 2" is correctly attributed to the
recovery formula's assumption (NSE's ex-date `PREVCLOSE` is exchange-adjusted)
holding for splits but not for bonuses on the older bhavcopy format — reported
as a limitation of the data, not patched to pass. No fifth amendment was
proposed to fix it, consistent with Entry 17's "no amendment 5."

One wording nit, not a numbers problem: §7's sentence "the two-ended return
definition alone cost more than that [0.17-point budget]" over-attributes to
just the two-ended requirement — by itself that only adds 9 stock-months (940
vs 0b's 931, 0.05 points), well under the 0.17-point budget. It's the combined
machinery (two-ended requirement + faulted dates + mismatches, 338 stock-months
beyond 0b's residual) that blows the budget. The breakdown table right above it
is correct and lets a careful reader verify this regardless, so this is a
clarity nit, not a finding — no correction needed to the closure.

One implementation ambiguity worth naming for the record, immaterial to the
verdict: the faulted-date test's denominator (`by_date`) only counts rows with
status `match` or `mismatch`, excluding `absent` and `unrecovered_split` rows
from "that date's comparable members." The amendment text doesn't pin down
whether an unrecovered split should count as a comparable failure for
date-fault purposes. Reasonable either way, and 93.41% clears or fails the 95%
gate by a wide enough margin (200 faulted stock-months) that this choice
doesn't change the outcome.

### Closure — correctly stated

The prereg's "Closure" section and `results-3f-stage0.md` §7 agree: amendment 4
FAILed its own pre-committed gate (93.41% < 95%), there is no amendment 5 under
Entry 17, and 3f is closed at stage 0 permanently — not re-registered with a
fourth vendor specification. No look and no trial were spent (stage 1 was never
written), and the 2026 held-out window is untouched — all confirmed against
`trials.md` (no new L-number, no new trial number added for 3f) and
`progress.md` line 68 (already updated per Entry 17's "smaller correction," and
line 274/276 record both the pre-registered HALT and the amendment 4 FAIL
correctly). Issue #108 (the Kite cache's dividend-adjustment finding, §4.4) is
properly filed in `BUG_LOG.md` with evidence, as CLAUDE.md requires for a
confirmed bug outside the research path. The "what survives" list in the
outbox (membership rebuild + tests, 0c citations with Entry 16's caveats,
bhavcopy tooling, issue #108) is accurate and doesn't overstate: none of it is
a claim about momentum, only about reusable infrastructure and one live-cache
defect found along the way. Nothing in the results file or the closure claims
or implies anything about whether 12-month momentum works — correctly scoped
to "the data gate could not be cleared," not to the hypothesis itself.

### Needs the user's decision

Nothing here does. No held-out spend, no live-path change, no credentials, no
new Kite download, no new paid data source (bhavcopy downloads are NSE-public,
already the established pattern from earlier stages).

### Next step, and where to stop

Nothing further on 3f — it is closed, permanently, at stage 0. The membership
rebuild, the 0c citations (with their standing caveats) and the bhavcopy
tooling are available to a future pre-registration; issue #108 is open and
independent of 3f. No further review is needed on this thread unless the main
agent proposes reopening it, which the standing rules and Entry 17 both already
bar.

---

## Entry 17 — 2026-09-24 — automated reviewer: Entry 16's corrections ACCEPTED; amendment 3's FAIL was handled correctly and its diagnosis is sound; a disclosed amendment 4 MAY be written, once, as the last correction this gate gets — with five pre-commitments below, none of them optional

Reviewed `results-3f-stage0.md` §6 and the Entry-16-directed fixes to §1.2/§2
and the standing caveats, `prereg-3f-momentum-delivery.md` amendment 3,
`step3f_stage0_checks.py::level_test`, and the `progress.md`/`trials.md` rows,
against Entry 16 and the outbox's "Re: Entry 16" reply.

### Entry 16's corrections — made as directed

§1.2 no longer claims the pre-open auction covers the whole window: it now
dates the auction to Oct 18 2010 (Nifty 50) and Apr 1 2013 (the rest) and
says plainly that Jan–Sep 2010 had an ordinary first trade, not a call
auction — exactly the fix required, and it correctly notes this doesn't
reopen §A since the close is kept regardless. The spell count is now "271
spells over 215 symbols," matching a direct count of `nifty100_membership.csv`
(272 lines minus the header). Both standing caveats (2011–2018 is an
inference; 0b's first-half concentration) are written inline at every point
in both `results-3f-stage0.md` and the amendment-3 preamble where "0c
CONFIRMED" or "0b PASS" is cited — checked at both locations, not just once.
Option (b) (bhavcopy correlation, same 0.98/95% bar) is not revisited
anywhere in the new text. All four items: done.

### Amendment 3, and the level test's FAIL — process is clean

Amendment 3's text satisfies all three of Entry 16's conditions on option
(c): the tolerance is anchored to the 3 bp/leg slippage already modelled (6
bp round trip), not to any observed match rate; the 99.4%/0.5% figure
already seen is disclosed in the amendment's own preamble, in writing,
before the gate is stated; and the test was run once, on the amendment's
own specification, with the raw result reported before diagnosis —
**10,397/19,261 = 53.98%, FAIL** — spot-checked and correct. `level_test()`
computes `gate_95pct` as a reported field only; `main()` never branches or
exits on it, so nothing halted the process automatically — consistent with
how 0b and 0c's own gates are handled, decided by the reader, not by a
`sys.exit`. This is one run, reported as written, then diagnosed. Correct.

### The diagnosis — sound, but the diagnostic code is missing from the repo

The claim that yfinance's `Close` is split-adjusted (not "unadjusted" as
amendment 3's text called it) is well evidenced: the yfinance/bhavcopy ratio
sits at exactly 1.000 on 10,395 of 17,059 comparable stock-months and at a
short list of clean split/bonus fractions (0.5, 0.2, 0.1, 0.667, 0.25) on
the rest, constant per stock and stepping only at corporate actions (one
value for 82 of 177 stocks, two to four for 87). Random data noise does not
cluster into 1:2, 1:5, 1:10, 2:3 and 1:4 ratios; a genuinely unadjusted
series compared to a genuinely adjusted one does, on exactly the pattern
described. I accept this as the correct diagnosis, not a rescue narrative.
Spot-check: 10,397/19,261 = 53.98% ✓; 16,840/17,045 = 98.80% ✓ (both
recomputed by hand from the numbers given).

**But the 98.80% return-based diagnostic in §6, including the 2015-11
clustering and the split-month/absent-month breakdown, is not backed by any
code in this repository.** `step3f_stage0_checks.py` contains only
`level_test()` (raw `Close` vs bhavcopy `close`, amendment 3 as written) —
no function computes a signal-date-to-signal-date return, and none reads
`prev_close`/`PREVCLOSE` for this purpose (it does for the unrelated 0c
`vendor()` comparison, which is a different code path over a different
window). The 98.80% figure, the 109/96 split, and the "2015-11" clustering
are therefore prose, not verifiable from the tree the way the level test's
53.98% is. That is a real gap, not a rejection: it must be closed before
amendment 4 is written, per the requirements below.

### The question: is a disclosed amendment 4 permitted, or does 3f halt here?

**Amendment 4 may be written and run once, as the last correction this gate
gets.** My reasoning: the standing rule bars re-runs "for adjusted
parameters," but allows one "for a declared bug fix, with both runs
recorded." What failed in amendment 3 was not a threshold that didn't
clear — it was a factual mislabelling of a data column (calling a
split-adjusted series "unadjusted"), independently evidenced by a
corporate-action-stepped ratio, not chosen to make a number pass. The
tolerance itself (6 bp) is not moving. That is the shape of a bug fix, not
of tuning a gate to rescue a result, and it is the second such fix in a row
only because both vendor instruments happened to carry adjustment
conventions the pre-registration didn't anticipate — a fact about the data
landscape, not a pattern of parameter search. I would rule differently if
the tolerance, the price definition, or the pass bar were moving toward the
number already seen; none of them are.

That said, this is the third attempt at the same gate (Kite cache, raw
`Close`, now returns), the diagnostic pass rate (98.80%) is already known
and comfortably clears 95%, and the discipline this project exists to
enforce is unforgiving of exactly this pattern when it repeats. So amendment
4 is conditional on all five of the following, and there is no amendment 5:
if it fails at its own pre-committed gate, or if any of the five is skipped,
3f halts at stage 0, permanently, and is not re-registered with a fourth
vendor specification.

1. **Disclose the 98.80% figure and its provenance in the amendment's own
   text**, exactly as amendment 3 disclosed 99.4%/0.5% — including that it
   was computed on the 17,045-stock-month subset *before* aliases and
   split-month recovery are added, so the number amendment 4 will actually
   report (on close to the full 19,261, with aliases and PREVCLOSE-recovered
   split months added back in) is not identical to 98.80% and has not yet
   been seen, even though it is very likely to clear given the components
   are additive.
2. **The tolerance stays 6 bp, unchanged.** Nothing about amendment 4 may
   re-derive it from 98.80%, 95%, or any other number now on the page.
3. **A mechanical rule for a whole-cross-section bad signal date, stated
   before the run, not fitted to 2015-11 or 2025-03-18.** E.g., "a signal
   date is faulted if more than N stocks (or more than X% of that date's
   cross-section) mismatch beyond 6 bp on the same date" — with N or X fixed
   in the amendment text, and the rule then applied over the *whole*
   2009–2025 run, not checked only at the two dates already known to fail.
   If the rule as written does not catch 2015-11 and 2025-03-18, that is
   reported as a miss, not adjusted until it does.
4. **The alias map is built from a general rule** (bhavcopy symbol history /
   `symbolchange.csv` gaps), not as five hand-added entries for the five
   names already found missing. If building it that way is not practical in
   the time available, the five may be added by hand, but the amendment must
   say so plainly rather than presenting it as a systematic fix.
5. **All of this computation lives in committed code** (extend
   `step3f_stage0_checks.py` or add a sibling module), so the reported
   number is reproducible from the repository the way `level_test()`'s
   53.98% already is, not read off a prose paragraph.

Run once, report whichever way it goes, before stage 1 is written.

### A smaller correction, not blocking

`progress.md` line 68 and `trials.md`'s "3f stage 0" line (155–157) both
predate amendment 3 and still describe stage 0 as ending at the 0c vendor
HALT (38%); neither mentions the level test's 53.98% FAIL or the unresolved
diagnostic. Update both to the current state before amendment 4 is written,
so the record of record doesn't read one step behind the results file.

### Needs the user's decision

Nothing here does. No held-out spend, no live-path change, no credentials,
no new Kite download. (The NSE bhavcopy downloads already used for the
level test are not Kite calls and do not compete with the live engine's API
budget; amendment 4's alias/PREVCLOSE work reads the same already-downloaded
bhavcopy files, so this doesn't newly trigger that limit either — but if
amendment 4's authors find they need to download *additional* bhavcopy
files or any other new data source to build the alias map, that new
acquisition is unremarkable NSE-public data, not a paid source, and does not
need the user's sign-off either.)

### Next step, and where to stop

Update the two stale progress/trials lines. Write amendment 4 with the five
pre-commitments above, run it once, and report the result — pass or fail —
before stage 1 is written. Stop again for review before stage 1 (L36) runs,
whether amendment 4 passes or fails: a pass opens stage 1; a fail, or a
skipped pre-commitment, closes 3f at stage 0 and that closure is itself the
thing to bring back for review.

---

## Entry 16 — 2026-09-24 — automated reviewer: 3f stage 0 ACCEPTED WITH CORRECTIONS — 0c source and 0b membership check out; the vendor HALT was handled correctly (no substituted pass); §5's own option (b) is rejected outright and option (c) may proceed only if its threshold is re-derived, not the one already seen passing

Reviewed `results-3f-stage0.md` against `prereg-3f-momentum-delivery.md`
(stage 0, amendments 1–2), `nifty100_membership.py`,
`step3f_stage0_checks.py`, `test_nifty100_membership.py`,
`nifty100_membership_build.json`, `trials.md` and `progress.md`. Confirmed
`backend/research/step3f_momentum.py` (stage 1) does not exist — stage 0
really did stop where it says it stopped.

### Process: clean

Every gate in the results table is stated verbatim from the prereg, then the
raw pass/fail is given, and only then diagnosed — the §D4 failure mode
(judging a gate after seeing the number) is not repeated. `coverage()` and
`vendor()` in `step3f_stage0_checks.py` read closes and correlations only,
never a forward return; `trials.md` and `progress.md` both say "no look, no
trial" for this run and I agree — data-adequacy and vendor-agreement checks
are infrastructure, not measurements of the hypothesis. No Kite download was
made (`--kite` reads the existing `kite_history.db` read-only, matching the
prereg's "no Kite calls").

**Spot-checks.** 18,330/19,261 = 95.165% → 95.17% (0b overall); 8,860/9,621 =
92.09% → 92.1% (2010–17); the dedupe log's 22 "voided" + 1 "superseded" = 23
entries matches the prose's "23 superseded/voided announcements" exactly;
`test_nifty100_membership.py` has 14 `test_` functions, matching the claimed
count. One figure does not reconcile: the results file says "272 spells over
204 symbols," but `nifty100_membership.csv` has 272 *lines including the
header* — 271 data rows by my count reading the file directly (rows run
`ABB,...` at line 2 through `ZYDUSLIFE,2023-09-29,,...` at line 272). Minor,
almost certainly an off-by-one in the prose rather than in the CSV, but
check it — `wc -l` minus one — before it is repeated in the stage-1 results.

### 0c source — the citations support CONFIRMED, with two gaps that should travel with the claim

The closing-price definition is attested by an NSE Capital-Market-segment
circular at both ends of the window (Fact Book 2010, CMTR/61813 2024,
CMTR/67774 2025) plus one in the middle (CMTR/40962, 2019) with byte-for-byte
identical wording, and independently corroborated by §4.3's own finding that
yfinance's Close matches the NSE bhavcopy's official close on 99.4% of
stock-days — that's empirical support for the same claim from a different
direction, not just textual continuity. I accept CONFIRMED.

Two gaps are disclosed but their consequences are not fully drawn out:

1. **2011–2018 has no circular on file** (404s at current NSE URLs). The
   "two ends plus unchanged wording" argument is reasonable, but it is an
   inference over eight years, not a citation. This should be stated as a
   standing caveat on the 0c CONFIRMED verdict every time it is cited later
   (the same discipline amendment 1 §D imposed on the item-5 power caveat),
   not just once here.
2. **The pre-open call auction did not exist for the whole window either.**
   §1.2 says the auction "confirms... the next-session open is a call-auction
   print for the whole window (for Next 50 names only from April 2013)" —
   but the SEBI circulars cited in the same paragraph date the auction's
   introduction to **October 18, 2010** for Nifty 50 names, and stage 1's
   window starts **January 2010** (0b's own start date). For roughly the
   first nine months of the sample, the open was *not yet* a call-auction
   print, so the stated reason for barring it does not apply there — it
   happens not to matter, because 3f keeps the close regardless (option (b)
   is independently justified as the literature's standard convention), but
   the claim as written overstates what the SEBI sources actually cover.
   Fix the sentence to say so, or restrict the "whole window" claim to
   post-Oct-2010 (and post-Apr-2013 for Next 50 names).

Neither gap changes the CONFIRMED verdict or blocks stage 1. Both are text
fixes.

### 0b coverage — accept the 95.17% pass as written; do not add a per-half gate now

The prereg's 0b gate is a single number (≥ 95% overall), and it is met. The
concentration of the missing 4.83% in 2010–17 (92.1%, 20 names entirely
absent from yfinance because they delisted or merged before its coverage
starts) is real and is exactly the kind of residual survivorship the
standing rules say matters most for a long-only winners-sort. But **writing
a stricter per-half gate now, having already seen that 2010–17 would fail
it, is itself the thing this project's discipline exists to prevent** — a
gate tightened after the number that would fail it is known. I will not
require one.

What I do require: the first-half concentration is a caveat that must travel
with every future citation of "0b PASS," the same way the item-5 power
caveat travels (amendment 1 §D). And if stage 1's first-half result is
negative or fails while the second half passes, that must be reported
together with this coverage gap as a candidate (not confirmed) explanation —
not used as grounds to backfill the 20 missing names from NSE's bhavcopy
archive (§5.2's option (b)) and rerun. Backfilling data *because* a result
you don't like showed up in the half where the data is worse is the same
rescue pattern as re-testing a variant, aimed at the universe instead of the
strategy. If the backfill is ever done, it must be decided and completed
**before** stage 1 is run, not after, and it is not justified by this run's
numbers alone.

### 0c vendor check — HALT is correct and correctly not substituted

The pre-registered comparator (Kite cache's last 5-minute bar) fails its own
0.98/95% bar (38%), and the report does not quietly swap in a different
number that happens to pass — §4.3's bhavcopy comparisons are presented
alongside the failure as diagnosis, with their own pass/fail stated plainly
(93.8%, still short of 95% at the same bar). This is the right way to
diagnose a halt. Confirmed from the code: `vendor()` never marks
`corr_ex_corporate_action_days` or the bhavcopy comparisons as gating
anything; `main()` prints all of them as reported measurements.

### §5.1 — the three options

**(a) hold the halt.** Available, but not required by anything found here —
the pre-registered comparator was simply the wrong instrument (a
dividend-adjusted last trade, not the official close), which is a comparator
defect, not a defect in yfinance's data. Ending 3f over a mis-specified
diagnostic when the primary-source comparison (§4.3) shows the data itself
is sound would be the same error in the other direction as an unjustified
rescue.

**(b) amend the check to the bhavcopy correlation, same 0.98/95% bar —
reject outright.** It already failed at 93.8% (94.8% even after excluding
the two merged no-data names), and the write-up's own suggestion — "the bar
is set before the comparison is rerun" — cannot be done honestly now: the
number it would need to clear is already known. Do not choose a new
threshold for this comparator. This option is closed.

**(c) a level test — conditional approval, not as numbered.** A level check
("close matched to the official close within X%, on ≥ Y% of stock-days") is
the statistically correct instrument for a design that trades once a month
at the close — daily-return correlation penalises small, uncorrelated daily
noise that a monthly close-to-close strategy never touches, which is exactly
what §4.2 shows is driving the pre-registered check's failure. In principle
this is not a rescue; it is recognising the original comparator measured the
wrong thing.

**But the specific numbers offered (0.5% / ≥99%) are not usable as written,
because they were read off the data before being proposed as a gate:** the
results file already reports "99.4% of stock-days... within 0.5%" in §4.3,
before §5 proposes 0.5%/99% as the pass rule. A threshold chosen after
seeing it clear by that exact margin is the same failure mode as a
Sharpe-tuned parameter, applied to a data gate instead of a strategy. Before
this is used as 3f's vendor gate:

1. **Derive the tolerance from the study's own economics, not from the
   observed pass rate.** Anchor it to something fixed before this run — the
   3 bp/leg modelled slippage, or a stated fraction of the 56.1 bp round-trip
   gate (e.g. "no looser than the slippage already assumed," ~3–6 bp, not
   50 bp). A 0.5% (50 bp) band is close to the entire monthly effect size
   stage 1 is trying to detect; a vendor gate that loose could pass while
   contributing noise or bias comparable to the effect itself.
2. **State plainly in the amendment that the 99.4%/0.5% number was already
   seen when the tighter threshold was chosen**, rather than presenting the
   new gate as if it were fixed blind. That transparency is the minimum
   needed given true blindness is no longer possible.
3. **Recompute at the tightened threshold and report whatever it gives,
   pass or fail**, before stage 1 is written. If it fails at a properly
   anchored tolerance, that is a valid HALT, not a reason to loosen further.

### Needs the user's decision

Nothing here does. No held-out spend, no live-path change, no credentials,
no new Kite download.

### Next step, and where to stop

Fix the two 0c-source sentences (§1.2's "whole window" overstatement) and the
272-vs-271 spell count; write the 0c vendor level-test as a numbered
amendment with a pre-committed, cost-anchored tolerance per the three points
above, disclosing that 99.4%/0.5% was already observed; carry the 0b
first-half caveat forward. Then, and only if the level test clears at its
new (not-yet-seen-as-passing) threshold, stage 1 (L36, the quintile gate) may
be written. Stop again for review before it runs — that is still the first
step that reads a return.

---

## Entry 15 — 2026-09-23 — automated reviewer: 3f amendment 1 ACCEPTED WITH ONE CORRECTION — §A's argument for keeping the close is right and the hard halt is real, but it has no rule for a closing-methodology change found mid-window; §B, §C, §D check out

Reviewed `prereg-3f-momentum-delivery.md` amendment 1 (§A–§D, appended, no
code exists — confirmed by `Glob`/`Grep` for `step3f*`: nothing in the tree)
against Entry 14, the outbox reply, `costs.py`, `trials.md` and `progress.md`.

### §A — the argument for option (b) is sound, and there is no alternative in this repo's data

The main agent's claim is that on **daily** bars the next session's open is
itself the **pre-open call-auction print** (09:00–09:08), the exact print the
standing rule bars, and that this is a different thing from what 3b/3e used.
That distinction holds up: 3b/3e's "open" is the open of a **5-minute
continuous-trading bar** (09:50, or "the bar after the signal bar") — a
genuinely liquid, continuously-traded price captured well after the actual
market-opening auction — not the day's literal opening print. A raw daily
`Open` field, by contrast, is the auction's equilibrium price (or the first
print struck at it). These are not the same thing, and treating them as
interchangeable would have been the error. I checked whether a third option
exists in this repo's data for the full 2010–2025 window and it does not:
the only daily-cadence source is yfinance (open/close only), and the only
sub-daily source, the Kite 5-minute cache, starts 2024-09-20 — 14 of the
window's 16 years short. **Option (b) is the only one that exists in this
repo's data for the stated period, not merely the one that was easiest to
defend.** Agreed.

**One gap, needs fixing before stage 0c is executed.** The hard halt requires
an NSE source confirming the 30-minute-VWAP close "for the whole selection
window," but has no rule for what happens if the source instead shows the
methodology **changed partway through** 2010–2025 (a different VWAP window,
or the closing auction phased in for some segment of stocks before
2026-08-03 — this project has not checked whether that happened, and it is a
real possibility, not a hypothetical one, since closing-auction mechanisms
were phased in for other NSE segments in stages over the past decade). As
written, a partial confirmation reads as "cannot be confirmed for the whole
window" → full stop. That may be the right rule, but stage 0b already solved
the analogous problem for membership by fixing the start date **in the file,
before any signal is computed**, rather than leaving it to be decided once
the source is in hand ("the later of 2010-01-01 and the first month with
complete membership"). §A's hard halt needs the same treatment: state now,
not when the NSE source is read, whether a documented mid-window change (a)
halts 3f entirely, or (b) truncates the start date to the confirmed regime's
start — and if (b), that this is decided by the rule, not by whether the
truncated window still looks favourable. Add one sentence to the hard halt
before stage 0c runs.

### §B — the four-case exit rule is complete

The 5-session threshold is unambiguous at the boundary (`≤5` vs `beyond 5`,
no overlap), and a suspension lasting beyond 5 sessions is case (iii) —
`−100%` — **regardless of whether it later resumes**; the case list reads as
three independent triggers ("suspension beyond 5 sessions," "compulsory or
involuntary delisting," "insolvency"), not one trigger requiring all three
qualifiers, so a stock that resumes trading after 20 sessions does not
retroactively become case (i). Applying the same rule to the benchmark's
members, not only picked names, is the right, symmetric choice — an
asymmetric rule would have let survivorship back in through the benchmark
side while the gate statistic looked clean. "The with-cases figure gates,"
stated before any case is observed, leaves no room to pick between the two
reported figures after the fact. One simplification worth naming, not
correcting: case (ii)'s merger rule assigns `0%` cash for the remainder of
the month even when the consideration is shares in an acquirer that is
itself a universe member — a conservative, stated simplification, not an
ambiguity.

### §C — all three fixes verified

1. **GST base**, checked against `backend/costs.py::leg_cost` directly:
   `gst = (brokerage + exchange_txn) * gst_pct / 100` — SEBI is outside the
   base, matching the corrected prose exactly.
2. Re-derived the ₹5,500 round-trip figure independently from the published
   tariff (DP ₹15.34, NSE 0.00307%) rather than trusting Entry 14's number:
   buy leg ₹6.5297, sell leg ₹21.0447, charges 50.14 bp + 6.0 bp slippage =
   **56.1 bp**, exact match. The amendment changed no figures, as claimed.
3. Benchmark definition and the nominal-price-filter caveat are both present
   and cross-referenced correctly in the stage-1 table and "What 3f cannot
   establish."

All struck/superseded markers are internally consistent: the numbering
header, the stage-2 heading, stage-1 item 5, and stage-0c's closing-price
line all point to the amendment section that actually superseded them, and
nothing was left half-edited.

### §D — accounting checks out

L36 (quintile gate, gated but still a cross-sectional measurement, not a
strategy selection) and L37 (item 5, logged separately per Entry 14) follow
the same precedent as 3b's L31/L32, which were gated research looks, not
trials. `trials.md`'s actual state (looks through L34, trials through 37)
is consistent with 3f's "expected L36/L37, or L35/L36 if 3e is withdrawn
first" — nothing here pre-claims a number, it states what the next free one
would be, same as 3e's own "expected L35/trial 38" framing. `trials.md` and
`progress.md` contain no reference to 3f, which is correct — nothing has run.
Noted, not a defect in this amendment: `progress.md`'s "Trials: 35, Research
looks: 16" line is stale narrative from 2026-09-21 and predates L17–L34 and
trials 36–37; it is not the count of record (`trials.md` is) and this
amendment did not touch it.

### Spot-checks

`leg_cost`'s GST formula (above) and the independently re-derived 56.1 bp
round-trip figure (above), both against `backend/costs.py` directly, not
against the document's own arithmetic.

### Next step, and where to stop

Add the one sentence to §A's hard halt (mid-window methodology change: halt
or truncate, decided now). That is a text fix, not a new look or trial. Then
stage 0b/0c can be written and run — still no look or trial spent by either,
since stage 0 reads no forward return. Stop again for review before stage 1
runs (the quintile gate, L36) — that is the first step that reads a return.

---

## Entry 14 — 2026-09-23 — automated reviewer: 3f pre-registration ACCEPTED WITH CORRECTIONS — the survivorship gate is right, the cost/power arithmetic is right, and the stage-2 proposal is right, but the holding-return fill uses the session close, which the tradability rule bars, and the delisting case in the holding window is unhandled

Reviewed `prereg-3f-momentum-delivery.md` (commit `6a970b3`, no code exists)
against the standing rules, the three questions in the outbox's top entry,
and precedent (`prereg-3b-intraday-momentum.md`, `prereg-3e-wide-structure-short.md`,
`phase3-scoping.md`, `report-phase-2-closing.md`, `trials.md`). Independently
recomputed the delivery round-trip table and the months-needed/MDE table from
`backend/costs.py` (`leg_cost`) and `backend/research/splits.py`
(`required_trades`) by hand, not by running code. Confirmed no `step3f_*` or
other momentum code exists anywhere in the tree.

### Verdict: ACCEPTED WITH CORRECTIONS. Fix §A before stage 0 code is written; §B–§D are smaller and can go in the same amendment.

### §A — the fill rule for the holding return needs to change or be gated, before any code exists

Stage 1's "Holding return" and stage 2's "Exit"/entry rule both price the
trade at the **adjusted close of a session** — entry at "close of the first
session of month m," exit at "close of the first session of month m+1."
That is the closing print, and the reviewer's standing rule is explicit:
"not the opening print, **not the closing auction**, fills after the signal
bar." Two prior pre-registrations already moved off the close for exactly
this reason — 3b's amendment 1 §3 moved its target from the 09:45 close to
the 09:50 open specifically because "the target starts there" was false once
scrutinised, and 3e's stage-2 entry fill is explicitly "open of the bar after
the signal bar... never the signal bar's own close." 3f is the one design in
this family that still fills at a close, and the document knows it: stage 0c
itself flags "to verify, not assumed" that NSE's close (a 30-minute VWAP
before 2026-08-03, a closing-auction print after) is "something a trader can
approximate," and its remedy is "**report it as an open caveat on
tradability**" if it can't be confirmed. A caveat carried silently into a
"clears 56.1 bp" verdict is the exact failure mode this project's rules exist
to catch — it is not a caveat, it is whether the number means anything.

Pick one, in the amendment:
- **(a)** Redefine the entry and exit fills to the **open of the session
  after** the signal/rebalance date, matching 3b and 3e's precedent, and
  re-derive the 3 bp/leg slippage assumption at that price point instead of
  the close; or
- **(b)** Keep close-to-close (defensible — it's the standard convention in
  the momentum literature the "why this" section cites), but make stage 0c's
  closing-price check a **hard halt**, structured exactly like 0b's
  membership gate: 3f proceeds only if an NSE source positively confirms the
  historical close is capturable by a retail MOC/closing-limit order, for
  both the pre- and post-2026-08-03 regimes. If it can't be confirmed, 3f
  stops at stage 0, the same as a failed membership reconstruction.

Either is fine; leaving it as a prose caveat that gets carried into a pass/fail
verdict is not.

### §B — the holding period has no rule for a stock that delists or suspends after selection

Stage 0b's ≥95% coverage gate and the "residual survivorship" caveat cover
**eligibility at selection time** — a stock with no price history doesn't
become an eligible member and can't be picked. They say nothing about a
stock that **is** picked (top quintile, or the single top-scored name in
stage 2) and then is suspended, delisted, or merged before the month-end
close that prices the exit. Does that trade get dropped from the sample
(which reintroduces the same survivorship failure mode 0b's hard gate exists
to prevent — now in the return-realisation step instead of the eligibility
step, and specifically biased toward the momentum-selected names, which are
disproportionately likely to be the ones that later fail) or is a specific
realised return assigned (last traded price before suspension, a punitive
floor, something else)? Fix this in the same amendment as §A, since it's the
same class of gap: a rule that exists for the selection side of the trade but
not the exit side.

### §C — minor, cosmetic, no figure changes

1. The cost-table prose says GST is charged "on SEBI + exchange," but
   `leg_cost()` computes `gst = (brokerage + exchange_txn) * gst_pct / 100` —
   SEBI charges are **not** in the GST base. I recomputed the round-trip
   table (56.1 / 84.0 / 111.9 / 167.7 / 865.0 bp) from the formula the code
   actually uses, not the prose description, and every figure checks out
   exactly (SEBI is ~150× smaller than the exchange charge, so this is
   sub-0.01 bp either way and changes nothing). Fix the sentence to match the
   code, not the numbers.
2. "Equal-weight eligible universe," the benchmark subtracted in every gate
   statistic, never gets the formula treatment the Score row got. State in
   one line that it's the equal-weight mean of holding returns across that
   month's eligible set — the same set used for quintile assignment — so a
   reader doesn't have to infer it.
3. Add one sentence to "What 3f cannot establish": the ≤₹5,500 unadjusted-
   price eligibility filter selects on **nominal share price**, which
   correlates with sector and split history, not market cap or liquidity.
   It's a real, uncorrected source of non-representativeness in both stages,
   distinct from the delisting/survivorship caveats already listed there.

### §D — the three outbox questions, answered

1. **Point-in-time NIFTY 100 membership as a hard stop: yes, correctly.** No
   weaker fallback is defensible. A winners-sort on today's membership
   selects, by construction, the names that rose into the index — this is
   not the same failure mode as the quintile-spread survivorship caveats
   carried elsewhere in this project (those don't bias toward the specific
   direction being traded); a "buy last year's winners, held in delivery"
   design does. Keep it as written.
2. **Dropping trial 39: agreed.** The power table is not close — 900 bp
   assumed sd against 192 available months gives an MDE of ~130 bp/month,
   an order of magnitude above any plausible edge, so a trial here can only
   end "untestable" and would buy nothing but a DSR debit. One correction:
   when stage 1 runs, log item 5 (the descriptive one-position report) as
   its own numbered **research look** in `trials.md`, not folded silently
   into stage 1's look number — it computes a full return series (mean, sd,
   worst month, drawdown) for a specific tradeable configuration, which is
   closer to a strategy backtest than a feature measurement, and its
   auditability shouldn't depend on the "no pass rule" framing alone. And:
   every future citation of that number — in a results file, a progress
   update, or a conversation with the user — must repeat the power caveat
   inline ("MDE ~130 bp/month; this cannot be distinguished from luck"), not
   just once in the pre-registration. A positive-looking mean/drawdown
   computed on one stock over a couple of hundred months is exactly the kind
   of number that gets requoted without its error bars if the caveat isn't
   attached every time.
3. **Not spending the held-out window, proposing forward tracking instead:
   agreed.** ~8 observations at an assumed 300 bp sd gives an MDE around
   210 bp/month — it cannot confirm a monthly strategy and the project's own
   rule (spending the held-out look needs the user's decision) is correctly
   never touched here. Forward paper tracking is correctly marked "needs the
   user's decision" rather than started — starting a multi-year forward
   collection commits future resources the main agent can't authorise alone,
   and I'm not authorising it either; that stays with the user.

### Spot-checks

Recomputed both numeric tables by hand from the cited source functions
(`leg_cost` on `DELIVERY_COSTS` with the two published figures substituted;
`required_trades(sd, 56.1)`): the delivery round-trip table and the
months-needed table (224 / 399 / 2,020 / 3,591) both check out exactly, as
does the 130 bp / 43 bp MDE pair. No number in the draft is wrong.

### Next step, and where to stop

Amend §A and §B (design decisions, not measurements — no look or trial is
spent by writing an amendment), fold in §C as text edits, then stop again for
review before stage 0b (the membership builder) is written. Stage 0b needs
its own look at what NSE source data is actually available before anything
downstream is worth reviewing again in detail.

---

## Entry 13 — 2026-09-21 — automated reviewer: 3b amendment 1 ACCEPTED WITH CORRECTIONS — Entry 12 §1–§5 faithfully implemented and all footnote arithmetic checks out, but two original-table rows still contradict it, two gate definitions are ambiguous, and a fifth file was missed

Reviewed `prereg-3b-intraday-momentum.md` amendment 1 (commit `fef1fd7`) against
Entry 12 §1–§5, independently recomputed all footnote arithmetic in the four
results files it names, grepped `docs/research/` for anything the footnote
pass missed, and checked `trials.md` and the working tree. No 3b code or
results exist anywhere (`find . -iname "*3b*"` matches only the prereg
itself); branch `research/entry12-3b-stage1` is clean.

### Verdict: ACCEPTED WITH CORRECTIONS.

Entry 12 §1–§5 are all faithfully and substantively implemented in the
amendment's own new text (§A), and every footnote arithmetic check I ran —
six ratio pairs across four files — is correct (§C). But the amendment was
not fully back-applied: two rows in the pre-registration's own original
tables still state the superseded rule with no strike or pointer (§B), two
gate definitions are genuinely ambiguous in a way that could change Stage
1's outcome (§F), and a fifth document carries the same uncorrected figures
with no footnote at all (§D). None of this is a design problem — it is a
"the document isn't tightened yet" problem, and every item below is
specific enough to fix without a new design decision. **Fix §B and §F
before writing Stage 1 code**; §D and §E should also be fixed, and §D
matters for the closing phase-2 report Entry 12 already commits to writing.

### A. Amendment 1 against Entry 12 §1–§5 — the new text is faithful

1. **§1 (factor-of-two gate):** corrected gate states 33.20 bp, positive,
   t > 2; the arithmetic is exactly 2×16.60; a spread between 16.60 and
   33.20 bp is explicitly recorded as a withdrawal, not a near miss, matching
   the requirement. The superseded 16.60 bp gate is struck (`~~...~~`) inside
   the amendment section, not deleted.
2. **§2 (time-series line):** market proxy, signal, target, statistic,
   both-halves and per-stock-pooled reporting, and the one-round-trip
   16.60 bp gate all match Entry 12 point 2 exactly, including the explicit
   "adapted version" framing and why.
3. **§3 (target at the 09:50 open):** matches Entry 12 point 3 exactly, and
   correctly restates that signal and target remain disjoint, now with a
   5-minute gap. See §B.1–§B.2 for where this wasn't back-applied.
4. **§4 (stage 2 position rule):** ten positions (5 long top / 5 short
   bottom) at the 09:50 open, tie-break deleted with sound reasoning (every
   entry is simultaneous, so there is nothing to order), 3a's friction rule
   carried with a reporting requirement, cross-sectional-only scope, and the
   "stop and report" branch if only the time-series line clears — all match
   Entry 12 point 4. See §B.3 for where this wasn't back-applied.
5. **§5 ("everything else stands"):** spot-checked — universe A,
   selection-only, existing cache, no Kite calls, direction-symmetric,
   self-contained harness, one variant, MDE-before-statistics, halves at the
   median date are all still present elsewhere in the document.

### B. Two places in the ORIGINAL document now contradict the amendment — strike them

1. **The Stage 1 "Construction" table's Target row still states the
   superseded rule**, with no pointer at all: `| Target | 09:45 close →
   15:10 close return, in bp — disjoint from the signal by construction, so
   no overlap |`. Amendment §3 moves this to the 09:50 open. Unlike the
   stage-1 gate — which got an inline "SUPERSEDED by amendment 1 §1" note at
   its original location, in addition to the strike in the amendment
   section — this row has nothing. A reader who stops at "Construction," the
   natural first place to look for what to build, gets the wrong target.
2. **The paragraph right after it is now flatly false, not just
   superseded:** "The signal window and the target window do not overlap.
   The signal ends at the 09:45 close **and the target starts there**."
   Amendment §3 explicitly says the opposite: a "five-minute gap between
   them **rather than touching**."
3. **The Stage 2 table's "Concurrent positions" row is the same problem,
   twice over:** `| Concurrent positions | 5, slots reopen on exit;
   chronological, ties alphabetical | 3a amendment 1 (e), as Entry 11 §D.3
   ruled |`. Amendment §4 changes both the count (10, not 5 — 5 long + 5
   short) and deletes the tie-break. The amendment section strikes the
   tie-break text in a quote, but this row at its original location is
   untouched and still says "5" with a live tie-break rule.

Same fix for all three: annotate in place with "SUPERSEDED by amendment 1
§3 / §4," the way the stage-1 gate paragraph was handled, so a reader never
sees only the stale version.

### C. Footnote arithmetic — independently recomputed, all six ratio pairs check out

| File | Spread | Old (quoted) | New (quoted) |
| --- | --- | --- | --- |
| results-step2-followups.md | +8.11 bp quintile, vs 16.60/33.20 bp | 0.49× | 0.24× |
| results-step2-followups.md | +16.30 bp top-5/bottom-5 | 0.98× | 0.49× |
| results-universe-b-replication.md | +5.97 bp quintile, vs 22.60/45.20 bp | 0.26× | 0.13× |
| results-universe-b-replication.md | +9.03 bp top-5/bottom-5 | 0.40× | 0.20× |
| results-universe-b-overnight.md | +14.15 bp overnight, vs 39.05/78.10 bp | 0.36× | 0.18× |
| results-3c-overnight-intraday.md | +8.11 bp tradable intraday, vs 16.60/33.20 bp | 0.49× | 0.24× |

All six check out. The universe-b-replication.md top-5/bottom-5 row (0.40×
→ 0.20×) is correct but wasn't named in Entry 12's brief or in commit
`fef1fd7`'s own message, which lists only five — worth knowing it's there
too. Every footnote is an addition below the original table, not a rewrite;
the original numbers and ratios stay visible. In every case the corrected
ratio is further from break-even, so no PASS/FAIL verdict flips anywhere —
I checked each file's headline verdict before and after: all four stayed
"does not clear cost" / "it does not pay." `results-entry7-d-feasibility.md`'s
own 0.36× (+12.01 bp index-level overnight return vs one 33.05 bp delivery
round trip) is a different, single-leg quantity — a lone long position pays
exactly one round trip — and correctly does *not* need this correction; I
checked it specifically because `results-universe-b-overnight.md` calls it
"the same 0.36× ... by a different route," and confirmed the two are
unrelated figures that happened to coincide before the fix (see §E.3).

### D. A fifth file has the identical uncorrected figures and was not touched

`report-2026-09-21.md` — the standalone status report explicitly written
"for a reviewer with no access to this repository and no memory of the
session" — still has, unfootnoted: `| Quintile | +8.11 bp (t = 1.68) | 0.49×
— does not clear | | Top-5 / bottom-5 | +16.30 bp (t = 2.12) | 0.98× — does
not clear |`. `git log` confirms its last touching commit (`7162c76`)
predates the footnote commit (`fef1fd7`); it was simply out of scope, not
deliberately excluded. This is exactly the reader Entry 12's correction
most needs to reach. Since this report explicitly supersedes
`report-2026-09-20.md` in a dated chain rather than being a living document,
the cleanest fix is not to rewrite it now: make sure the **closing phase-2
report** Entry 12 already commits to writing (after stage 1 runs) restates
these figures at 33.20 bp / 0.24× and 0.49×, not the stale ones. A one-line
pointer added to this file now, mirroring the other four, is also fine if
it's quicker.

### E. Three footnotes leave stale prose nearby that restates exactly the reading just withdrawn

1. **results-step2-followups.md**, eight lines after the footnote:** "The
   top-5 version comes within 0.3 bp of break-even... landing at **0.98×
   cost** means an expectancy of **approximately zero**..." — the exact
   reading the footnote three paragraphs earlier calls "the single most
   encouraging number this project produced and it was wrong by a factor of
   two." Commit `fef1fd7`'s own message says this line is "explicitly
   withdrawn" — but the file still states it as live analysis a few lines
   down.
2. **results-3c-overnight-intraday.md**, just after its footnote:** "...the
   spread exists only as long-quiet against short-volatile, and even then it
   returns **half the cost** of executing it." 0.49× ≈ half; 0.24× (the
   corrected figure, one paragraph up) is closer to a quarter.
3. **results-universe-b-overnight.md**, just after its footnote:** "The same
   0.36× the index-level calculation gave by a different route" — no longer
   true; the spread is now 0.18×, and the index-level figure is a genuinely
   different, unrelated 0.36× that was never wrong (§C above). And: "The
   true figure is worse than 0.36×; **it is not recomputed here** because
   the conclusion does not turn on it" — six lines above this sentence, the
   footnote already recomputed it, to 0.18×.

None of these change any verdict, and this isn't a rewrite request — just
strike or update these specific sentences the same way the tables above them
were footnoted, so a reader who reaches the prose after the footnote isn't
told the withdrawn number again as if it still stands.

### F. Ambiguity hunt — two items that could change what Stage 1 computes, not just how it's read

1. **Which spread is the Stage-1a gate: the quintile-based "top-minus-bottom
   spread" (item 2 of "What is reported"), or the "top-5/bottom-5 spread"
   (item 3)?** The gate paragraph's own wording ("the top-minus-bottom
   spread") textually matches item 2. But Stage 2 trades top-5/bottom-5, not
   quintiles, and nothing marks item 3 as descriptive-only. Not hypothetical:
   this project's two measured pairs of quintile vs. top-5/bottom-5 spreads
   run 1.5× to 2× apart (8.11→16.30 bp; 5.97→9.03 bp, §C), so the two
   constructions can plausibly land on opposite sides of 33.20 bp. Direct
   precedent: Entry 9 §1 required 3a's analogous broader lines to be stated
   as "descriptive, with no pass rule, cannot justify a follow-up variant" —
   3b's item 3 needs the same explicit sentence, one way or the other.
2. **In Amendment §2's "same statistic per stock, pooled by session," is the
   per-stock signal that stock's own sign(prior close → 09:45), or the
   single market-level sign applied to every stock that session?** Both are
   plausible readings of "the same statistic per stock" — per-stock momentum
   vs. market-wide timing applied to individual names are different
   hypotheses that could disagree. Also needs an explicit "no independent
   pass rule" statement; only the market-level line has a stated gate.

My default for both, if no one has a reason to prefer otherwise: item 2
(quintile) governs the Stage-1a gate, item 3 is descriptive only; and the
per-stock line reuses that stock's own signal (true per-stock momentum),
also descriptive only. State the choice in the file rather than deciding it
silently in code, per this project's own standing rule (Entry 8's own
"these are my defaults; if you choose differently, say why in the amendment,
not afterwards").

### G. Minor, not blocking

- Stage 2's top-5/bottom-5 **selection** could still tie at the 5th/6th rank
  boundary — a genuine bp tie in the ranking, unlike the deleted
  entry-order tie-break, which was about simultaneous entries, not rank
  ties. Needs its own tie-break if it isn't already vanishingly rare at bp
  precision.
- Stage 2's table doesn't restate eligibility/universe/data/period; it's
  clearly inherited from Stage 1 by context (every other row cites back to
  3a/stage 1), but was never made explicit the way 3a's amendments always
  did.
- §1's "equivalently, the mean per-leg return exceeds 16.60 bp" is a loose
  paraphrase — only the *sum* of both legs needs to exceed 33.20 bp, not
  each leg individually — but the bolded primary gate criterion is
  unambiguous, so this is wording only.
- `trials.md` L25 and `progress.md`'s step-2C row both still frame the
  8.11/16.30 bp spreads as "vs 16.60 bp," without a ratio number. No wrong
  number is stated and no conclusion is affected; optional cleanup, lower
  priority than §D.

### H. Trial accounting and housekeeping — checked, correct

`trials.md` L31 and L32 are both `pending`, the strategy-trial count is
unchanged at **35**, and the research-looks table has exactly 32 rows
(L1–L32), matching its own "Thirty-two looks, thirty-five trials" line. No
3b script or results file exists anywhere in the tree. Working tree is clean
on `research/entry12-3b-stage1`. The amendment's "Authorisation, recorded"
section matches Entry 12's own authorisation text verbatim in substance.

### I. Needs the user's decision

Nothing new. Everything above is editorial (strike/annotate existing text)
or a documentation default consistent with established precedent (Entry 9
§1) — none of it touches a gate, threshold, live path, credentials, or the
held-out window.

### J. Next step, and where to stop

Fix §B (two struck/annotated rows) and §F (two explicit gate statements) in
the pre-registration; they are what Stage 1 code will actually be written
against. Once fixed, Stage 1 may be coded and run under the standing
go-ahead Entry 12 already recorded — this does not need another review
round, since none of the fixes change a computed rule, only remove a
contradiction or fill a stated gap with an explicit default. Fix §E and, at
minimum, note §D's fifth file before or alongside the closing phase-2
report so it doesn't inherit the same stale figures. **Stage 2 remains
unauthorised regardless of what Stage 1 shows — stop and ask the user,
exactly as Entry 12 already says.**

---

## Entry 12 — 2026-09-21 — external reviewer: 3a FAIL accepted, no follow-ups; 3b staging approved with four amendments; the spread gate was wrong by a factor of two

3a: **FAIL accepted as written. No follow-ups.**

3b staging: **approved.** Stage 1 runs as a research look with no trial; trial 36 is spent only if stage 1 clears. Amend before running:

1. **The gate is wrong by a factor of two.** A top-minus-bottom spread is two positions, each paying a 16.60 bp round trip. **Stage 1 clears only if the spread is positive with t > 2 AND exceeds 33.20 bp** (equivalently, the mean per-leg return exceeds 16.60 bp). Apply the same correction wherever earlier spreads were compared with a single round trip, **as a footnote, not a recomputation**.

2. **Restore the original brief's 3b — the published time-series effect** — as a second pre-declared line in stage 1. The market's first-half-hour return, measured from the **previous close** to 09:45 so it includes the overnight gap, predicting the last half hour. Market proxy = equal-weighted mean of the universe; signal = sign of previous close → 09:45 close; target = return over the last tradable half hour, **14:40 open → 15:10 close**; report the mean of `sign(signal) × target` in bp with t across sessions, both halves, and the same statistic per stock pooled by session. **Its gate is one round trip: positive, t > 2, and above 16.60 bp.** State plainly that the literature's window runs to the close, which intraday cash positions cannot hold, so this is an **adapted** version.

3. **Stage 1's cross-sectional target starts at the 09:50 bar's OPEN**, matching stage 2's entry, not the 09:45 close.

4. **Stage 2 position rule:** long the top 5 and short the bottom 5 by signal rank, **ten positions, all entered at the 09:50 open**. **Delete the chronological/alphabetical rule** — it selects nothing when every entry is simultaneous. Carry 3a's per-trade friction rule (skip if `16.60 / stop_bp > 0.15`) and report how many it removes. Stage 2 stays defined for the **cross-sectional version only**. If only the time-series line clears, **stop and report**; it would need its own pre-registration.

5. Everything else in the pre-registration stands.

### The user's go-ahead, given directly

Once the amendment is committed and the research-reviewer has signed off on it, **stage 1 may run without coming back to the user**, since it spends no trial and touches no held-out data.

**Stage 2 does NOT have the user's go-ahead. If stage 1 clears, stop and ask.**

Whatever stage 1 shows: write the results file, then a **closing phase-2 report** (what was tested, what was found, trial count, what remains unspent), and stop. **Do not propose new hypotheses in it.**

---

## Entry 11 — 2026-09-21 — automated reviewer: 3a run ACCEPTED, trial 35 is a clean FAIL; one wording correction; the four flagged items all rule in the main agent's favour; 3b needs its own pre-registration and the user's go-ahead

Reviewed `results-3a-opening-range.md`, `step3a_result.json`, `step3a_preflight.json`,
`prereg-3a-opening-range.md` (amendments 1–3), `backend/research/step3a_opening_range.py`,
`backend/tests/test_step3a_fills.py`, `trials.md`, `progress.md`, and the outbox
entry "Re: Entry 10". The user's "go-ahead" after Entry 10 is noted as the
user's own confirmation, not mine, and is the only thing that authorised the
run — consistent with the hard limit that I cannot spend or authorise a run
myself.

### Verdict: **ACCEPTED with one wording correction.** Trial 35 stands as FAIL.

### A. Every figure checked against the two JSON files — all match

Primary: net −12.086 → −12.09 bp, t −2.709 → −2.71, gross +4.517 → +4.52 bp,
t +1.012 → +1.01, net R −0.0781 → −0.08, 1,656 trades, 303 sessions — all
exact. Halves (−1.18/t −0.15/gross +15.43/t +1.93 and −21.96/t −5.03/gross
−5.36/t −1.23), sides (longs −14.72/t −2.09/gross +1.89/t +0.27, shorts
−13.31/t −1.77/gross +3.29/t +0.44), secondary lines (−14.99/t −5.38 and
−13.64/t −6.25), the power line (sd 77.67 bp, n 303, MDE 8.92 bp), the
pre-flight line (1,139 of 5,275, 21.6%; 12,745 of 28,600; median width 107.3
bp; min stop 110.67 bp) and the pooled per-trade mean (−15.87 bp) all
reproduce the JSON to the reported precision. Internal cross-checks also
close: longs (891) + shorts (765) = 1,656; first half (801) + second half
(855) = 1,656; every exit-mix row sums to its trade count. Nothing in the
prose overstates or rounds favourably.

### B. The script against the pre-registration as amended

Read `step3a_opening_range.py` line by line against amendments 1–3. Order of
operations is `eligibility → top-20 by rel_vol → signal → friction rule →
cap`, exactly as 3.1 fixes it, and it is enforced by construction: `rel_vol`
only exists for a (symbol, date) once 14 prior cached sessions with all three
opening bars exist (`rel_vol_table` checks `len(prior) >= REL_VOL_LOOKBACK`
*before* appending the current session — no lookahead, and the synthetic test
`test_rel_vol_needs_14_prior_sessions_and_uses_only_the_past` proves it).
Entry is the open of the bar *after* the signal bar, never the signal bar's
close (amendment 1 b, tested). Stop fills match amendment 1 (c) exactly: an
intrabar touch fills at the stop price, a bar that opens beyond the stop fills
at that open, and the entry bar itself can stop the trade — all three paths
have a synthetic test with a hand-computed expected fill. The 14:30 cutoff is
enforced in `find_signal`'s bar loop, and a signal with no following bar
before 15:10 returns no trade. The top-20 tie-break is alphabetical, proven
by `test_top20_tie_is_alphabetical`. The friction rule (`stop_bp >=
110.666...`) is applied identically to all three lines and a skipped
candidate takes no cap slot, because the capped-list comprehension filters on
`kept` before `capped()` ever sees it. Halves are split at the median of the
full 319-session cache list (not the 303 live-only sessions), which is the
literal reading of amendment 1 (g) — "selection sessions in the Kite cache" —
and the reported 144/159 split is internally consistent with the 16
non-eligible sessions falling near the start of the series. Sizing is a fixed
₹33,000 notional; gross uses raw fills, net applies `costs.apply_slippage`
and `costs.leg_cost` on both legs, and the synthetic zero-gross test proves
net − gross ≈ −16.60 bp. `load_days` drops any bar dated on or after
`splits.HELD_OUT_START` before anything else can see it, and `kite_history.load`
only reads the local sqlite cache — no network path exists in it — so "no
Kite calls" is not just asserted, it is structurally true.

### C. The verdict logic

`untestable if MDE > 16.60`, else `PASS if net>0 and t>2 and both halves >0`,
else `FAIL` — read directly from `main()` — is exactly amendment 3.3 plus the
original pass rule. MDE (8.92 bp) is well under 16.60, so the untestable
branch correctly did not fire, and the results file states the exact number
that would have triggered it either way, honouring Entry 10 §A.1. Entry 10
§D (state the verdict as the headline, secondary lines last) is honoured —
`## Verdict: FAIL` is the first line under the title, the two descriptive
lines are the last section.

### D. Ruling on the four items the main agent flagged

1. **Not calling the half-to-half drop "decay": correct.** The results file
   says so explicitly and gives the reason (two sub-sample numbers, no trend
   test registered). No correction needed.
2. **The all-100 line restricted to the primary line's 303 sessions: accepted.**
   The restriction is in a code comment inside `3841124`, which predates both
   the pre-flight commit and the run commit, so it was a pre-run design
   decision, not a post-hoc adjustment — and it is disclosed in the results
   file itself with the exact number. It is descriptive-only, carries no pass
   rule, and is barred from justifying a variant either way, so it cannot
   move the verdict. The 319-session figure is not needed; do not compute it.
3. **"Max concurrent positions" read as concurrent (slots reopen on exit),
   giving 5.47 trades/session: correct, and self-consistently verified.** A
   literal daily cap of 5 could not produce an average of 5.47 trades per
   session; the observed rate is only possible under the reopening reading,
   which also matches the original hypothesis text ("Max concurrent
   positions... matches the live engine's shape") more literally than a
   fixed daily cap would. Ruled: this is the correct reading, not a
   researcher degree of freedom that needs to be re-litigated.
4. **Gross on raw fills, slippage and charges both inside net: confirmed** by
   reading `simulate()` and by the synthetic zero-gross test, which asserts
   net ≈ −16.60 bp when gross ≈ 0.

### E. One correction — wording, not a number

"**It is the fifth time the project has found gross ≈ 0 and net ≈ −cost.**"
This is a count claim without a citation. Most of the project's other
findings (the `atr_pct` quintile spreads, the universe B replication, 3c's
intraday leg) found a small but *non-zero, sometimes significant* gross edge
that fell short of cost — a different and more informative pattern than
"gross indistinguishable from zero." The pattern this sentence describes
(gross statistically indistinguishable from zero, net ≈ −cost) most cleanly
matches only the original checklist result (§51) and this one. **Fix:** name
the specific instance(s) being counted, or drop the ordinal and say "another
instance of the same shape: no measurable edge before cost, cost eats what
was there." This does not change the verdict or any number; it is a claims-
match-evidence correction only.

### F. Trial accounting

`trials.md` shows trial 35 with the correct label, hashes and the FAIL result,
count 35 as of 2026-09-21, and logs it under "Phase-2 runs" as one run, no
re-run. Matches the JSON and the results file. No replication, no withdrawal.

### G. Needs the user's decision

Nothing new. A FAIL earns no held-out look — this was already the rule, and
the main agent has correctly not touched it. Nothing here makes a Kite call,
spends the 2026 window, or touches the live path. Branch `research/entry8-3a`
remains unpushed; merging is the user's alone.

### H. Next step, and where to stop

3b ("intraday momentum," `progress.md`, queued) is the natural next item, but
it needs its own pre-registration — hypothesis, one variant, fill and stop
rules, pass rule in bp against 16.60, halves, power statement — committed
*before* any 3b code, exactly as 3a's was. Fix the one wording item above in
the results file (or note it in the next commit; it does not need its own
commit). **Do not write or run 3b code until that pre-registration is written
and reviewed, and do not run it even then without the user's explicit
go-ahead**, the same two-step gate 3a went through. Stop again after the
pre-registration for review, and again after any run, before touching the
held-out window or proposing anything further.

---

## Entry 10 — 2026-09-21 — automated reviewer: amendment 3 accepted with corrections; still STOPPED for the user's go-ahead on 3a; nothing here to merge or run

Reviewed `prereg-3a-opening-range.md` amendment 3 (`815ba4c`) against Entry 9
and against Entry 8 §D / amendments 1–2. Spot-checked: `results-universe-b-replication.md`
against the outbox's cited −0.0332/t=−6.68/+5.97bp/0.26x/0.85x — all match.
`results-entry7-d-feasibility.md` §D.1 correction and §D.2 correction
against Entry 8 §B.4/§B.6/§B.10's required wording — match near-verbatim.
`git ls-files` and the stated branch history (`0332ffb` → `ba75b15` →
`ad7b05c` → `815ba4c` → `52eec60`) confirm no 3a script exists anywhere in
that sequence. `trials.md` still shows 34, correctly unchanged since nothing
has run.

### Verdict: amendment 3 is sound. Approved with corrections (documentation only, no threshold changed).

Amendment 3 correctly takes precedence over Entry 8 §D where the two differ,
restores the relative-volume hypothesis exactly as Entry 9 specified it
(`or_vol`/`rel_vol` formula, top-20, 14-session eligibility, both secondary
lines carrying no pass rule and barred from justifying a follow-up variant),
and replaces the median-width withdrawal with the per-trade friction rule as
instructed. Nothing in 3.4 weakens what amendments 1–2 already fixed
(next-bar-open fill, stop rules, 14:30 cutoff, halves, ₹33,000 sizing,
self-contained implementation with no harness-bias figure asserted). One run,
stated once more.

### A. The three open choices — ruling

1. **§3.3 thresholds: accepted as written.** The pre-flight count check
   (< 60 sessions with a surviving capped trade → untestable, not run, not a
   trial) and the post-run MDE check (`2·sd(session means)/√n > 16.60 bp net`
   → untestable, trial 35 still counted) are consistent with the project's
   own trial-accounting rule: no return is read in the first branch, a return
   is read in the second. The post-run formula is exactly what Entry 8 (i)
   asked for — the smallest bp effect detectable at the pre-registered t = 2
   — so it isn't a new invention, it's (i) applied as a decision rule instead
   of only a reported number. 60 sessions is a coarse backstop, not a precise
   power calibration, and that's fine: the real power statement is the MDE,
   computed from realised dispersion after the run. **One correction:**
   whichever branch fires, report the exact number that triggered it — the
   pre-flight session count, or the realised sd and MDE — in the results
   file, not just the word "untestable". A reader needs to see how close to
   60 (or to 16.60 bp) it landed, precisely because the threshold is fixed
   and auditable and should stay that way.
2. **§3.1 eligibility and the alphabetical tie-break: accepted.** Both are
   forced by Entry 9's own wording ("its own mean ... over the prior 14
   cached sessions" requires 14 prior sessions to exist) or are a direct,
   symmetric extension of the tie-break Entry 8 (e) already fixed for the
   five-position cap. Neither introduces a new researcher degree of freedom
   that could move the result.
3. **Skipped-trade handling: accepted.** No cap slot, no re-entry, and
   applying the friction rule to both secondary lines is the right call —
   without it the two secondary lines would not be comparable to the primary
   one, and a design could otherwise look better only because it kept
   costlier-to-cross trades in the descriptive lines.

### B. Order of operations, lookahead, and the R/stop_bp consistency

`eligibility → top-20 by rel_vol → signal → friction rule → cap` has no
lookahead: `rel_vol` and the opening range both resolve at 09:30 from the
three 09:15/09:20/09:25 bars, before any signal bar (earliest close at 09:35)
can fire; the cap is applied chronologically as signals arrive, not with
foreknowledge of later signals in the session. `stop_bp` is computed from the
next-bar open (amendment 1 b) and the opposite side of the opening range,
which is exactly Entry 8 (f)'s `R = entry price to stop price` restated in
bp — consistent, not a redefinition.

### C. Outbox corrections footnote — satisfies Entry 8 corrections 1, 4, 6, 10 and §E

Confirmed against source files, not just the outbox's own claim:
`results-universe-b-overnight.md` withdraws "decaying" and states the
supportable sentence (correction 1); `results-entry7-d-feasibility.md`
withdraws "40% survivorship" and gives the required reworded sentence
(correction 4), states "2025 is the weakest year... no trend test was run"
without adding one (correction 6), and reads "not cleanly measured even in
the level" (correction 10). The outbox's footnote under the Entry 7 block
corrects "Committed and on main" to name PR #60 and its merge commit
(§E). All four plus §E are done, with the original wording left visible
rather than deleted, as the project's standing rule requires.

### D. For the results-file step, not a correction to the amendment

When 3a is eventually run: state the primary verdict (pass / fail /
untestable) as the headline before either secondary line is shown, regardless
of which of the three numbers looks best. That already follows from Entry
9's "no pass rule, cannot justify a follow-up variant" language; flagging it
now so it isn't relitigated after a number is on screen.

### E. Needs the user's decision

- **3a still does not run without the user's explicit confirmation.** I
  cannot give that confirmation; nothing in this review is it. The amendment
  is approved as a design; executing it is the user's call, as Entry 9's own
  final line already says.
- Nothing here touches the held-out 2026 window, makes a Kite call, or
  changes anything in the live path. Branch `research/entry8-3a` remains
  unpushed and unmerged; merging is the user's alone, not mine or the main
  agent's.

### F. Next step, and where to stop

With the one documentation correction in §A.1 folded into the amendment file
by the main agent (or simply honoured in the results file when it's written
— either is fine, it doesn't require a new commit on its own), the design is
ready. **Stop here.** Do not write 3a code or run it until the user
confirms. When the user does confirm: code, pre-flight reported on its own
(with the exact count either way, per §A.1), the single run as trial 35,
`results-3a`, and stop for review again before 3b or any mention of the
held-out window.

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
