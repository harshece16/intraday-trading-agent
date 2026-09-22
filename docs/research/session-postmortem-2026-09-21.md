# Session post-mortem — 2026-09-21 and 2026-09-22

**Question:** both sessions ended with zero orders placed. Was that data
quality, engine stalls, or the gates working as designed?

**Answer: the gates.** Neither day had a data problem or an engine problem;
both were, on the measurable evidence, the two healthiest sessions in the
sample. The zero is decided entirely inside the Varsity checklist, and the
binding item is reward-to-risk.

Method: `data/sahab_journal.db` opened `mode=ro`, engine untouched and still
running throughout. Every figure below is a query against `checklist_evals`,
`activity` and `trades`, not a reading of the dashboard. Comparison days are
15–18 Sep, the last sessions that produced trades.

---

## 1. Kite session status

**Both days ran on live Kite data. Neither zero is a delayed-feed story.**

Kite-expired errors by hour (market hours are 09:15–15:30):

| Day | 00–08h | 09h | during market hours | `Kite connected` logged |
| --- | --- | --- | --- | --- |
| 21 Sep | 4/hour, steady | 1 (at 09:10) | **1** | **09:15 and 09:16** |
| 22 Sep | 04–07h only | 0 | **0** | **07:21** |

The dashboard's "connected" indicator is not the evidence here, deliberately:
**#51** is the open bug for it reading connected after a session has died, and
README §53 documents it holding that lie for two days. Two independent
journal facts are used instead:

1. A `Kite connected — real-time data and live order routing available`
   *event* row at 09:15/09:16 on the 21st and 07:21 on the 22nd, plus
   `Stop watcher connected to the Kite tick stream` at 09:16 on the 21st —
   the tick stream only attaches to a live session.
2. **The absence of the expired-error drumbeat.** A dead token logs that
   error roughly every 15 minutes — visibly 4/hour through the small hours
   of both days. It stops dead at 09:15 on the 21st and 07:21 on the 22nd
   and does not resume for the rest of the session. A token that was still
   dead during market hours could not have gone quiet.

Caveat worth stating: the journal has no historical `using_live_data` field,
so this is inference from event rows and error silence, not a stored flag.
It is strong, but it is indirect.

**The contrast is the important part.** The three days that *did* trade look
worse on this axis, not better:

| Day | `Kite connected` row | expired errors in market hours | positions opened |
| --- | --- | --- | --- |
| 15 Sep | none | 2 | 1 |
| 16 Sep | **yes** | 3 | **4** |
| 17 Sep | none | 13 | 3 |
| 18 Sep | none | — | 0 |
| 21 Sep | **yes** | 1 | **0** |
| 22 Sep | **yes** | 0 | **0** |

15 and 17 Sep ran on the delayed yfinance fallback and placed 1 and 3
positions. 16 Sep ran on live Kite and placed 4 — the best day in the
sample. Live data is present on both the best day and the two zero days.
**There is no association between data source and trades.**

## 2. Engine health

**Both days are the cleanest in the sample.** Heartbeat is taken from
distinct `checklist_evals` timestamps during market hours, collapsed into
cycles (evaluations within 20s are one tick).

| Day | cycles | first → last | span (of 375 min) | median gap | gaps > 5 min |
| --- | --- | --- | --- | --- | --- |
| 15 Sep | 577 | 09:15:25 → 15:14:45 | 359 | 38s | 0 |
| 16 Sep | 564 | 09:15:16 → 15:14:44 | 359 | 38s | 0 |
| 17 Sep | 217 | **09:53:52** → 15:14:30 | 321 | 39s | **5** |
| 18 Sep | 377 | 09:15 → 15:14 | 360 | — | **6** |
| **21 Sep** | **566** | 09:15:04 → 15:14:57 | **360** | 38s | **0** |
| **22 Sep** | **559** | 09:15:16 → 15:14:53 | **360** | 38s | **0** |

17 Sep — a day that placed 3 positions — lost 71.7 minutes in one gap
(12:08→13:20) plus four more over 5 minutes, and started 39 minutes late.
21 and 22 Sep lost nothing.

**Watchdog: no fires.** `com.tradersahab.watchdog` is loaded with last exit
status 0, and `watchdog.log`, `launchd.out.log` and `launchd.err.log` are
all 0 bytes. Nothing needed restarting by the watchdog.

**Restarts:** 21 Sep has three pre-open restarts (07:48–07:50) and one
**mid-session restart at 13:19**, with the stop watcher reattaching the same
minute. It cost under five minutes — no gap that day exceeds that.

**Research-run overlap: none.** The two research runs on 21 Sep were the
supplementary null diagnostic (09:14–09:19, from `progress.md`) and 3a
(code `3841124` 10:58:40, pre-flight `9f9ac61` 10:59:23, result `f4f1d3c`
11:00:37 — a ~2-minute window). Neither overlaps a gap, because **21 Sep has
no gaps over 5 minutes at all**. The research runs did not starve the engine.

## 3. The funnel

Distinct `(symbol, side)` pairs, not rows.

| Day | evaluated | ≥ entry threshold | **full checklist pass** | blocked at entry | opened |
| --- | --- | --- | --- | --- | --- |
| 15 Sep | 110 | 72 | **8** | 21 | 1 |
| 16 Sep | 134 | 100 | **19** | 18 | 4 |
| 17 Sep | 132 | 87 | **10** | 8 | 3 |
| 18 Sep | 140 | 90 | **1** | 1 | 0 |
| **21 Sep** | 138 | 100 | **0** | **0** | **0** |
| **22 Sep** | 140 | 104 | **0** | **0** | **0** |

Blocked-at-entry rows by reason:

| Day | confidence gate | direction conflict | other | total |
| --- | --- | --- | --- | --- |
| 15 Sep | 13 | 1 | 7 (untracked Kite position) | 21 |
| 16 Sep | 1 | 16 | 1 (position/sector cap) | 18 |
| 17 Sep | 4 | 4 | 0 | 8 |
| 18 Sep | 1 | 0 | 0 | 1 |
| 21 Sep | 0 | 0 | 0 | **0** |
| 22 Sep | 0 | 0 | 0 | **0** |

**The top of the funnel is intact and normal.** 21–22 Sep evaluated *more*
symbol-sides (138, 140) and cleared the entry threshold *more* often (100,
104) than any of the days that traded. Nothing is under-scanning.

**The break is at the checklist, and it is total.** Zero full passes on both
days. Because nothing passed, nothing reached `_try_enter()` — hence zero
blocked rows. The confidence gate, the sector cap, sizing and the market-bias
filter were never consulted on either day. They cannot be the explanation.

18 Sep is a different zero and worth separating: it produced one full
checklist pass (09:45, an Inverted Hammer long) and the **confidence gate**
stopped it — 53/100 against the 60 bar, a local setup of 88 scaled by the
0.60× "not enough data" Scorecard factor. That is a zero decided *downstream*
of the checklist. 21–22 Sep never got that far.

## 4. Which of the three explains the zero

**Not data quality.** 16 Sep ran on live Kite and produced the most trades in
the sample; 21–22 ran on live Kite and produced none. 15 and 17 ran on the
delayed feed and traded. The variable does not sort the outcomes.

**Not engine stalls.** 21–22 are the only two days besides 15–16 with zero
gaps over five minutes, and they cover the full 360-minute span. 17 Sep lost
71 minutes in one stretch and still placed three positions.

**The gates, working as specified.** The checklist rejected everything, and
the item doing the rejecting is `rrr`:

| Day | median R:R | R:R ≥ 1.5 | median stop (% of price) | median target (% of price) |
| --- | --- | --- | --- | --- |
| 15 Sep | 0.16 | 26.0% | 0.140 | 0.165 |
| 16 Sep | 0.09 | 38.2% | 0.149 | 0.156 |
| 17 Sep | 0.00 | 40.1% | 0.140 | 0.149 |
| 18 Sep | −0.08 | 30.5% | 0.129 | 0.145 |
| **21 Sep** | **−0.15** | **10.5%** | **0.180** | **0.094** |
| **22 Sep** | **−0.14** | **9.1%** | **0.196** | **0.104** |

Both terms of the ratio moved against a pass at once: stops widened by
roughly 35% and target distance fell by roughly 35%.

The mechanism is visible in which branch of `trader_brain.py` picks the
target:

| Day | A: level that clears 1.5R | B: nearest level (fallback) | C: formulaic 2R |
| --- | --- | --- | --- |
| 15 Sep | 20.6% | 70.1% | 9.4% |
| 16 Sep | 36.4% | 60.2% | 3.4% |
| 17 Sep | 40.0% | 59.5% | 0.5% |
| 18 Sep | 28.3% | 66.3% | 5.5% |
| **21 Sep** | **9.6%** | **85.6%** | 4.8% |
| **22 Sep** | **7.0%** | **87.1%** | 5.9% |

Branch A's share tracks the R:R pass rate almost exactly, by construction —
branch A *is* "a level within `max_target_atr` (3 ATR) that clears 1.5R net
of costs". Its collapse from 20–40% to 7–10%, with the fallback to the
nearest level rising to 85–87%, is the whole story: the search walks outward,
finds nothing that qualifies inside 3 ATR, and settles for a level close
enough that R:R cannot clear the bar.

### The most likely proximate cause, and what is not established

`min_stop_atr = 1.0` was **added by `d789481`, merged Sat 19 Sep 15:58** — the
1-ATR stop floor. 18 Sep is the last session before it (median stop 0.129%);
21 and 22 Sep are the first two after it (0.180%, 0.196%). The stop widening
lands exactly on that boundary, and that commit's own message predicted this
tradeoff in terms: *"a wider stop pushes the required target further out in
absolute terms, [and] shoves good setups past `max_target_atr`."* That is
precisely the branch-A collapse measured above. The floor did what it was
designed to do to the stop; the second-order effect on target selection is
larger than the backtest that justified it suggested.

Three honest limits on that attribution:

1. **The zero-trade streak starts before the floor.** 18 Sep was also a zero
   day, pre-floor. The floor changed the *shape* of the zero — from "passed
   the checklist once, then blocked by the confidence gate" to "never passed
   at all" — not the fact of it.
2. **The floor and the data-source switch are not fully separable here.** No
   session in this sample is post-floor *and* on delayed data. What makes the
   data-source explanation implausible is 16 Sep (live Kite, pre-floor, 4
   trades) — but that is a single day.
3. **Two sessions is a small sample.** 21–22 Sep is not enough to distinguish
   a parameter effect from a quiet-market effect. Median target distance can
   fall because ranges genuinely tightened.

**No gate should be loosened on the strength of this document.** §48 already
measured relaxing the R:R rule, §51 measured what the strategy is worth when
it does fire (−0.356R per trade, friction 0.398R), and a setup missing the
bar by 0.24 is not evidence the bar is wrong. The finding here is narrower
and only diagnostic: the zero is not a fault, the gates are doing what they
were specified to do, and the one parameter change that plausibly tightened
them is identified with its commit and its date for whoever decides to look
at it deliberately.

---

## Data hygiene note

The `activity` rows timestamped **22:37 on 22 Sep** on this database (18 rows
plus one scan, including a `[summary]` row) were written by a second backend
started for testing during the session that produced this document, not by the
live engine. No `checklist_evals` and no `trades` were affected, and every
figure above is drawn from market-hours data. `database.DB_PATH` is hardcoded
with no override, which is what made that possible.
