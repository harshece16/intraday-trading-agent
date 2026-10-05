# Pre-registration — Jev 2: a blind, decomposed LLM judge on the whole daily list (forward paper test)

**Written 2026-10-05, before any Jev 2 code exists and before any Jev 2
decision.** The owner wants the Jev idea improved. Jev 1's test
(`prereg-jev-book.md`, trial 123) is not changed: a test's questions, state
and rules are fixed before it starts, and its first rounds have been seen.
Jev 2 is a second book, with its own state, page, API and rules, that runs
beside Jev 1 on the same days and is judged on its own pre-registered rule.
Everything below is fixed now; **no number in this file may be refit while
the test runs.** A change needs a dated clarification, written before it is
deployed, that says what had been seen.

## Why Jev 2, and what the prior is

The research behind this design (`jev-research`, 2026-10-05) read TypeSafe's
own model notes and two independent benchmarks of Jev 1.13. Jev is not a
generative model: it scores fixed options in one parallel pass, answers each
question in isolation, and is near-deterministic. The vendor documents what
hurts it: a large noisy state, argumentative text in the state, numbers it
reads weakly, option-order bias in Choice, and a poorly calibrated Score. Its
prescription is to ask narrow questions and combine them in code. The
independent benchmark found Choice well calibrated, Noul slightly
**under-confident** (its probabilities sit nearer 0.5 than the truth), and
that withholding the least confident half of the answers raised accuracy a
lot.

Jev 1 breaks each of these: it sends the scanner's own side, score and
argued reasons in the state (so an agreeing answer is not evidence of
judgment), asks one broad "buy, short or skip" Choice, and uses a Score for
size. Jev 2 removes the scanner's opinions from the state, asks seven narrow
Nouls combined by a frozen equal-weight rule, trades only when the combined
probability is away from 0.5, drops size, and asks about all 25 names on the
day's list instead of 15.

**The prior is still that it will not beat costs.** No LLM trading agent in
the literature sweep (`prediction-engine-sweep-2026-09-26.md`) has a
cost-surviving intraday edge, and the same news that Jev 2 reads is dead at
20 bp intraday in the one careful study of it. Jev 2 is a better-run test of
the idea, not a reason to expect a different answer.

## Protocol (fixed)

### When, and on what

- Once per trading day, on the scanner's day list (`active`, 25 names in the
  scanner's turnover order; README §91 and §100). Jev 2 asks about **every
  name on the list**, at most 25 (`JEV2_BOOK.max_names`). Jev 1 asks the
  first 15; those are the **shared names**.
- The round starts at the **first open-phase engine tick at or after 09:45
  IST at which Jev 1's round for the day has ended** (its day is recorded and
  its decision thread is not running), or at once if Jev 1 is disabled or
  switched off. The scanner snapshot is **captured at Jev 2's first tick at
  or after 09:45**, the same tick at which Jev 1 starts, so both books read
  the same scan; the capture is held in memory until Jev 1 finishes. A day
  whose round has not started by **10:00 IST** (`decide_until`) is recorded
  as **missed** and is not a session (a restart between 09:45 and 10:00
  loses the captured snapshot and starts from the current scan; a restart
  after 10:00 records the day as missed).
- Jev 2 runs in its own thread and its own try/except: a Jev 2 failure can
  neither stop Jev 1 nor the engine, and nothing in Jev 2 writes Jev 1's
  state.

### What Jev 2 sees — the blind state

One JSON state per stock, these keys and no others:

```
time_ist, exit_rule ("close at 15:08 IST today, no stop, no target"),
round_trip_cost_pct (0.17 — the same line Jev 1 sends; see Costs),
market: { nifty: {ltp, chg_pct, above_open}, vix,
          breadth: {adv, dec, pct_adv}, fii_dii: {date, fii_net_cr, dii_net_cr} },
stock:  { symbol, name, industry, ltp, chg_pct, gap_pct, rvol, rs_today,
          vwap, vwap_distance_pct ((ltp / vwap − 1) × 100, computed),
          opening_range: {high, low}, sector_chg_pct, atr_pct, rs10,
          pct_from_high, pct_from_low, turnover_cr, beta, catalyst, event,
          large_deals, rsi, adx, support, resistance,
          headlines: [ {title, publisher, hours_before_decision} × up to 3 ] }
```

**Deliberately withheld** (every one is a judgment, not a measurement): the
scanner's `side` and `score_side`, `score`, `final_score`, `long_score`,
`short_score`, `reasons`, `shadow_side`, `sector_trend`, `daily_trend`,
`swing_patterns`, `long_only`; the chart's `setup`, `bias`, `regime`,
`structure`, `htf_trend`, `patterns`, `fundamentals_label`; the market's
`bias`, `reasons` and the NIFTY `trend`. Never keys, account data or
positions.

**Headlines.** The scanner row carries up to three headlines with an age in
hours (`age_h`) at the time of the scan. An item whose publication time could
not be parsed is given `age_h = 24.0` by `news_sentiment._aggregate`
(line 237) and still passes the 72-hour filter, so such a story can in fact
be newer than Jev 2's fill. **Jev 2 drops every item with `age_h` missing or
exactly 24.0** (a genuinely 24.0-hour-old story is dropped with them; that is
accepted). Jev 2 sends `hours_before_decision = age_h`, a number, never a
clock time. The bug is filed against Jev 1's path and is not changed there.

### The questions — seven Nouls, two wordings each

Every question is a Noul (a probability that a statement is true), asked in
**two wordings** (A and B below) in the **same request**, so one request per
stock carries 14 questions. TypeSafe answers each in isolation; the two
wordings are a perturbation ensemble, and the probability used is their
**mean**. All 14 raw values, the response's `model` and `usage` are logged
for every decision.

| key | A | B |
| --- | --- | --- |
| `news_positive` | The headlines carry news that a trader would read as good for this stock's price today. | Today's headlines about this company are favourable for its share price. |
| `news_negative` | The headlines carry news that a trader would read as bad for this stock's price today. | Today's headlines about this company are unfavourable for its share price. |
| `strength_extending` | The stock is trading above its VWAP and above its opening range on heavier volume than usual, and is more likely to extend higher than to fade by 15:08. | Intraday strength: price above VWAP and the opening-range high with high relative volume, likely to continue up into the close. |
| `weakness_extending` | The stock is trading below its VWAP and below its opening range on heavier volume than usual, and is more likely to extend lower than to bounce by 15:08. | Intraday weakness: price below VWAP and the opening-range low with high relative volume, likely to continue down into the close. |
| `sector_up` | The stock's sector and the NIFTY are both rising today, which supports a further rise in this stock into the close. | The market and this stock's sector are up today, a tailwind for the stock until 15:08. |
| `sector_down` | The stock's sector and the NIFTY are both falling today, which supports a further fall in this stock into the close. | The market and this stock's sector are down today, a headwind for the stock until 15:08. |
| `move_exhausted` | Today's move in this stock is already large for its usual range, so the rest of the day is more likely to retrace than to extend. | The stock has already moved more than it usually does in a day; the move looks spent. |

No `size` question: the Score primitive is the worst-calibrated of the three
and the research found sizing by confidence needs joint fitting. Every
position is the book's fixed ₹1,00,000 notional.

### The combination rule (frozen, every number fixed)

Let each `p_k` be the mean of the two wordings. Then

```
S = ( (news_positive − news_negative)
    + (strength_extending − weakness_extending)
    + (sector_up − sector_down) ) / 3          # in [−1, 1]
p_combined = 0.5 + S / 2                        # in [0, 1]
```

- **buy** if `p_combined ≥ 0.65` and `move_exhausted < 0.70`;
- **short** if `p_combined ≤ 0.35` and `move_exhausted < 0.70`;
- **skip** otherwise.

So the **abstention band** is `|p_combined − 0.5| < 0.15` (equivalently
`|S| < 0.30`), and an exhausted move (`move_exhausted ≥ 0.70`) is a veto in
either direction. The 0.65 / 0.35 / 0.70 figures are set once, now, knowing
that Noul is under-confident on the benchmark: they are modest on purpose,
so that the band does not swallow every decision. **A skip scores 0 and is
counted** as a decision; the skip rate is reported.

### Model

`JEV2_BOOK.model = "jev-1.13.0"`, pinned. `jev-latest` is an alias that
moves; Jev 1 uses it. The `model` field of every response is logged with
the decision, so a silent change at TypeSafe would show in the record. The
endpoint, key and retry policy are Jev 1's (`jev_book.system_one`,
JEV-05): the same key file, never logged.

### Fills — shared with Jev 1 where it has one

- **Entry.** For a shared name whose Jev 1 decision on the same day recorded
  a live entry, Jev 2 **reuses that entry price** (`fill_source: "jev1"`),
  provided the scan Jev 2 captured is the scan Jev 1 used: the row's `ltp`
  and `vwap` in Jev 1's recorded state equal those in Jev 2's captured row.
  Otherwise, and for every name Jev 1 did not price (the 10 extra names, an
  excluded Jev 1 decision, a Jev 1 day recorded as unavailable), Jev 2
  fetches Kite's last traded price when its own answer returns
  (`jev_book.live_ltp`; `fill_source: "own"`). Never the delayed feed
  (Clarification 3 of Jev 1 applies: without a live Kite session the day is
  "no live prices" and does not count).
- **Why reusing a price fetched before Jev 2 was asked is fair.** Jev 2's
  decision uses the captured scan, which is the same scan Jev 1 had and
  predates Jev 1's fill. Nothing Jev 2 sees post-dates the price it is
  filled at; it merely answers a few minutes later on the same information.
  It does not touch Jev 1's code path or timing.
- **Exit.** At the engine's 15:08 square-off, in the same tick and
  immediately after Jev 1's close: a shared name reuses Jev 1's recorded exit
  when there is one, otherwise Jev 2 fetches its own. The tick difference for
  an "own" fill against a "jev1" fill is the time Jev 1's close took, seconds;
  it is disclosed per decision by `fill_source`.
- A decision that cannot be priced at either end is **excluded** with the
  reason, as in Jev 1. A session counts only if at least one decision was
  priced live at both ends.
- Jev 2 only ever **reads** Jev 1's state file.

### Costs

Every buy or short is charged the engine's intraday round trip at the
₹1,00,000 notional, `costs.round_trip_pct(100000, config.COSTS)`, **14.27 bp**
including 3 bp of slippage a side — the same function and figure Jev 1
charges (Jev 1's Clarification 1, JEV-11; verified in code on 2026-10-05).
The state line `round_trip_cost_pct: 0.17` is kept word for word from Jev 1
so that the cost wording is not a difference between the two books; it is
the charge at the old ₹5,000 size and is conservative. The questions above
never mention cost.

### Scoring, per decision

`net_bp = sign × move_bp − 14.27` for a buy (+1) or short (−1), where
`move_bp = (exit / entry − 1) × 10,000`; 0 for a skip. Measured at fixed
size (there is no other size).

Three comparisons on the same stock-days and the same prices:

1. **Jev 2 − scanner side**: the scanner's old score's stronger side
   (`jev_book.scanner_side`, i.e. `score_side`, the baseline Jev 1 keeps
   under its Clarification 10), scored the same way, on every Jev 2 decision.
2. **Jev 2 − Jev 1**, paired, on the shared names only: Jev 1's `net_bp` is
   read from Jev 1's state at the verdict; a pair needs both decisions priced
   at both ends. A skip is 0 on either side.
3. The 10 extra names enter only Jev 2's own verdict (rule 1 and the
   unpaired mean), never the Jev 2 − Jev 1 pair.

**Standard errors are session-clustered.** The decisions of one session share
that day's market (Jev 1's three closed sessions had means of +22.8, −33.0
and +36.0 bp against a per-decision sd of 95 bp), so the plain t counts
fifteen partly shared outcomes as fifteen independent ones. The verdict's t
is the mean divided by a cluster-robust standard error with one cluster per
session (variance of the mean = G/(G−1) · Σ_g (Σ residuals in g)² / N²).
The plain t is reported beside it, for comparison with Jev 1.

### Pass rule — family "LLM judgment", N_family = 3

Jev 1's pre-registration set the family bar at N_family = 2 (t ≥ 2.24, a
one-sided 2.5% test split in two, with 2 as the floor for a family of one
test). Jev 2 is a second, distinct test of the same idea in the same family,
so the family's count rises by one: **N_family = 3 and the bar is
t ≥ 2.39** (one-sided 0.025/3 = 0.00833; the same rule gave trial 120 its
2.394). Evaluated **once**, when **300 buy/short decisions** have closed or
after **60 counted sessions**, whichever comes first:

1. Mean net bp per buy/short decision > 0 with **session-clustered t ≥ 2.39**.
2. Positive in **both halves** by decision date.
3. **Beats the scanner's side** on the same stock-days: paired mean > 0 with
   session-clustered t ≥ 1.65.
4. Reported, not gated: the paired Jev 2 − Jev 1 mean and its clustered t on
   the shared names; the plain t of 1 and 3; the skip rate and the mean net
   on the shared 15 and on the extra 10 separately; hit rate; each
   directional Noul's Brier score against the realised sign of `move_bp`
   (a coin scores 0.25); the cost share; input tokens; the record with
   `fill_source: "own"` shared names left out.
5. Also reported at Jev 2's verdict, information only: Jev 1's record cut by
   `|p_up − 0.5| < 0.15` and `≥ 0.15`, to show whether an abstention band
   would have helped Jev 1. It changes nothing in Jev 1's test.

**Kill rule:** after **100 buy/short decisions**, if the cumulative net
**plain t < −2** (the same statistic and line as Jev 1, JEV-12), the book
switches itself off. A pass gives Jev 2 no authority: using it anywhere is a
separate owner decision after this test (RES-27 applies: a pass authorises
paper only).

### Power, written before the first round

From Jev 1's record (below): per-decision sd 95.3 bp, session-mean sd
36.6 bp on 15 names. Jev 2 traded on, say, 70% of 25 names over 60 sessions
is about 1,050 decisions: a plain se of 2.9 bp, but a session-clustered se
near 36.6/√60 ≈ 4.7 bp. **At the clustered bar of 2.39, the test can call a
true mean of about +11 bp a decision; it cannot call +8.6 bp** (clustered t
≈ 1.8). Sixty sessions is the floor, not a choice; 300 decisions will arrive
first if fewer than 70% are skipped. Cost: about ₹0.5 a round at list price.

## What had been seen when this was written (disclosure)

The researcher who designed Jev 2 printed Jev 1's per-decision rows and
summaries. Everything seen, so a reader can judge whether the design fits
the data it will be tested on:

- Jev 1's three closed rounds (2026-09-28, 2026-09-29, 2026-09-30, 15
  decisions each) and the open round of 2026-10-05 (15 entries, no exits):
  **60 decisions, 9 buy / 50 short / 1 skip**; 41 of the 45 closed decisions
  on the scanner's side; the first round was +22.8 bp a position (t 0.86),
  identical to the scanner's side (Jev 1 Clarification 5); session means
  **+22.8, −33.0, +36.0 bp** (sd 36.6); the page's summary of the three
  closed rounds **+8.6 bp a decision, t 0.61** (Jev 1 Clarification 12);
  per-decision sd **95.3 bp**; paired (Jev 1 − scanner) sd **75.8 bp**; mean
  `p_up` **0.30** against a realised up-rate of **0.38**; Brier **0.268**
  against a 0.235 base-rate Brier. 2026-10-01 was "no live prices".
- The two external benchmarks of Jev 1.13 and TypeSafe's model notes, as
  summarised above; none of them used market data.
- No Jev 2 question has been asked of any stock. The thresholds 0.65 / 0.35
  / 0.70 were not tuned on anything: there is nothing to tune them on.

The design decisions that this seen record could have biased, named: the
abstention band (motivated by the external benchmark, not by Jev 1's Brier,
but the Brier was seen first); the removal of the scanner's side (motivated
by 41/45 agreement, which was seen). Both are stated here so the reader can
discount them; neither is a number fitted to Jev 1's returns.

## Code

`backend/jev2_book.py` (paper only): the daily round in its own thread, the
square-off close, the clustered statistics; state in
`backend/data/jev2_book_state.json`; `GET /api/jev2-book`; a dashboard page;
a fifth card on the paper desk; process-log tag `jev2`; rules `JEV2-*`.
Committed **after** this file. Stage 0 before the first live round: a dry
round on a copy of a recent day's list with the TypeSafe call mocked, one
real call on a single synthetic state to confirm the response schema, and an
independent review. The first live round is the first trading day after a
backend restart that follows that review.

---

# Disclosure addendum — 2026-10-05, after stage 0 and before any Jev 2 decision

While checking the Jev 2 page against a mock API during stage 0, the page's
"Jev 1's record cut by |p_up − 0.5|" line (pass rule item 5) was computed
from Jev 1's real state and read: **inside the 0.15 band, 13 closed trades,
+11.2 bp a trade; outside it, 32 trades, +7.6 bp.** Those two figures are
hereby added to what had been seen. They were not used to change anything:
the 0.65 / 0.35 band and every other number above stand as written. So that
the same thing cannot happen daily, the page and `GET /api/jev2-book` carry
that cut **only once the verdict is due** (`verdict_due`), as item 5 says;
until then the field is null. The paper desk's Jev 1 card, read on the same
mock, also showed Jev 1's scanner-side mean, **+7.6 bp a trade** over the same
45 closed decisions, and that 14 of its 15 positions of 2026-10-05 were open;
both are added to what had been seen.

Stage 0 also read, for the shared-fill check, Jev 1's fifteen entry prices
of 2026-10-05 (already listed above) and nothing else of its record.

One wording made exact, before any decision: under Fills, "a shared name
reuses Jev 1's recorded exit when there is one" means a shared name **whose
entry was Jev 1's** (`fill_source: "jev1"`); a shared name filled at Jev 2's
own entry also takes Jev 2's own exit, so no decision mixes the two books'
ticks. That is what the code does (`close_round`).

---

# Clarification 1 — 2026-10-05, after the independent review and before any Jev 2 decision

**What had been seen:** nothing new. No Jev 2 round has run; no Jev 2
decision exists. The review (of PR #280, merged and deployed, first round due
2026-10-06 09:45) found two things the code did not do as this file says,
and three places where this file was silent. Each is fixed here, in text
first, then in code, before the first round.

**1. The state was not blind: `catalyst` is dropped.** The scanner row's
`catalyst` field is not a label but the whole output of
`news_sentiment.market_catalysts` for the stock: an aggregate sentiment
**score** in [−1, 1], a count, the top title and the same three headlines
again, each with its own sentiment score, an LLM-scored flag, a URL and the
raw `age_h` — including the 24.0 undated sentinel that the Headlines rule
drops. `build_state` copied it whole. That sent a sentiment judgment and
undated news, contrary to the blind-state rule. **From the first round,
`catalyst` is not sent at all.** The stock's news reaches Jev 2 only through
`headlines` (title, publisher, hours before the decision). The dry round's
claim in README §128 that "every withheld key was absent from every state"
was true of the listed keys and not of this nested content; the stage-0 copy
of 2026-10-05's list carried it on 5 of the 25 rows. The fixture in the tests held `catalyst:
None`, which is why the blind-state test passed; the fixture now carries the
real shape and the test asserts that no `score`, `url`, `llm_scored`, raw
`age_h` or duplicate title appears anywhere in the state. JEV2-02 is
reworded to say so.

**2. "Beats the scanner" is scored on every decision, skips at 0.** The
Scoring section says the scanner's side is scored "on every Jev 2 decision"
and that a skip scores 0; `summary()` computed pass-rule item 3 on buy/short
decisions only. The text is right and the code is aligned to it: the paired
Jev 2 − scanner figure and its clustered t run over **every closed decision**,
a skip contributing 0 − scanner_net. That is what the abstention band is for:
a skip on a stock-day the scanner would have traded is a decision, and it
counts against or for Jev 2. Item 1 (Jev 2's own mean and t) stays on
buy/short decisions, as written. The Jev 2 − Jev 1 pair already counted
skips at 0 on both sides.

**3. A missing `move_exhausted` answer means no trade.** The rule did not say
what happens if TypeSafe returns the six directional Nouls but not
`move_exhausted`. Now: the veto cannot be checked, so the decision is a
**skip** (recorded with `p_combined` and `S`, and the reason). A missing
directional Noul was already an excluded decision; that is unchanged.

**4. Reusing Jev 1's fill after a restart.** If the engine restarts between
Jev 1's round and Jev 2's, and the scan Jev 2 then captures carries the same
`ltp` and `vwap` for a shared name as the scan Jev 1 recorded, Jev 2 reuses
Jev 1's earlier fill for that name, as the Fills section says: the match is
on the scan, not on the clock. Jev 2's decision still uses nothing newer than
that scan for the name. The 10:00 limit on starting the round is unchanged.

**5. The "record without own shared fills" figure looks at both ends.** Pass
rule item 4 reports Jev 2's mean with shared names that took Jev 2's own fill
left out. "Own fill" means **own entry or own exit** (`fill_source` or
`exit_source` equal to "own"); the code looked at the entry only.

**Unchanged:** the questions and their wordings, the combination rule and its
thresholds, the band, the list, the model, the costs, the session-clustered
t, the pass rule's bar, the kill rule and the verdict's timing. No number was
refit; no Jev 2 answer has been read.
