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
