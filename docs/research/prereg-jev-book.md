# Pre-registration — the Jev book: can an LLM judge beat the scanner on the day's shortlist? (forward paper test, trial 123)

**Written 2026-09-27, before any Jev decision exists.** The owner: "integrate
Jev with Trader Sahab — on the top 10–15 shortlisted, ask Jev whether you
should buy, sell, short, increase."

## Why a forward test, and what the prior is

Jev (TypeSafe Jev 0.6.2, `jev` CLI) answers typed questions — a choice, a
probability, an ordered score — about a JSON state, using a large language
model. The prediction-engine sweep (`prediction-engine-sweep-2026-09-26.md`)
found **no LLM trading agent with a cost-surviving edge**; the one
broker-verified example netted +₹5,114 before its AI bill. An LLM cannot be
backtested honestly here either: it has read the history it would be
tested on. So the only fair test is **forward, in paper**, with the rules
fixed now. The prior is that it will not beat costs.

## Protocol (fixed)

- **When:** once per trading day, at the first engine tick at or after
  **09:45 IST**, on the scanner's **active shortlist** for that day (up to
  15 names, in the scanner's order).
- **What Jev sees:** only public market data — the scanner's row for the
  stock (sector, price, day change, gap, relative volume, relative strength
  today and over 10 days, VWAP, ATR %, daily trend, distance from the
  52-week high and low, turnover, beta, catalyst, event, swing patterns,
  large deals, the scanner's side, score and reasons, the chart-setup
  labels), the scanner's market summary, the time, the exit rule and the
  cost. Never keys, account data or positions.
- **Three questions per stock:**
  1. `action` (choice): **buy** — open a long intraday position now;
     **short** — open a short intraday position now; **skip** — no position,
     the expected move does not beat costs.
  2. `p_up` (probability): will the price at 15:08 IST be above the current
     price?
  3. `size` (score): none / half / normal / double — conviction.
- **Fills:** entry at the live price when Jev's answer returns
  (`data_provider.get_ltp`); exit at the live price at the engine's
  square-off (15:08); no stop, no target. Costs: the engine's intraday
  round trip (`costs.round_trip_pct`, ~16.6 bp including slippage), charged
  on every buy or short.
- **Measured per decision:** net return in bp of notional, at fixed size
  (the test of skill); a size-weighted version is reported for information.
- **Baseline, on exactly the same stocks and prices:** the scanner's own
  side (LONG → buy, SHORT → short), which is what the engine would do
  without Jev. Always-skip is 0.

## Pass rule — family "LLM judgment", N_family = 2 (the floor)

Evaluated once, when **300 buy/short decisions** have closed or after **60
sessions**, whichever comes first:

1. Mean net bp per buy/short decision > 0 with **t ≥ 2.24**.
2. Positive in **both halves** (by decision date).
3. **Beats the scanner** on the same stock-days: paired (Jev net − scanner
   net) mean > 0 with t ≥ 1.65.
4. Reported, not gated: hit rate, the `p_up` Brier score against 0.25 (a
   coin), net by size level, cost share.

**Kill rule:** after 100 buy/short decisions, if the cumulative net t is
below −2, the book stops itself. A pass gives Jev no authority by itself:
using it in real decisions (as a filter in the review queue, say) is a
separate owner decision after this test.

## Code

`backend/jev_book.py` (live, paper only): the daily decision round in a
background thread, the square-off close, the verdict statistics; state in
`backend/data/jev_book_state.json`; `GET /api/jev-book`; a dashboard page.
Committed after this file. Until a Jev API key is stored (`jev auth set`),
the book records "Jev unavailable" and trades nothing.

---

# Clarification 1 — 2026-09-27, before any Jev decision exists

The cost rule is `costs.round_trip_pct` at the book's ₹1,00,000 position,
which is **14.3 bp** including slippage, not the "~16.6 bp" quoted above
(16.6 bp is the round trip at the old ₹5,000 position size). The rule is
unchanged; only the quoted figure was wrong.

---

# Clarification 2 — 2026-09-27, before any Jev decision exists

At the owner's request the book calls **TypeSafe's official System One API**
(`POST https://api.typesafe.ai/v1/systemone`, model `jev-latest`) instead of
the community `jev` CLI. The three questions, their wording, the state and
the fills are unchanged; they now travel in **one request per stock**
(same state, three typed questions), which also returns each answer's
probabilities and confidence — recorded for information, not used in the
rule. The size answer is TypeSafe's probability-weighted score, rounded to
the nearest level. The key comes from `TYPESAFE_API_KEY` or
`backend/.typesafe_key.json` (`typesafe_key.py`).

---

# Clarification 3 — 2026-09-27, before any Jev decision exists

The Fills rule says entry and exit are at **the live price**, and names
`data_provider.get_ltp`. That function silently falls back to yfinance,
about 15 minutes behind, when Kite isn't connected (#151). A fill from that
feed is not the live price. Worse, Jev's snapshot carries live headlines,
so a delayed entry would let Jev see news newer than its own fill price. So
that the rule means what it says:

- Fills come only from Kite's last traded price (`jev_book.live_ltp`),
  never from the delayed feed.
- If Kite isn't connected when the round is due, the day is recorded as
  **"no live prices"**. Jev is not asked, and the day is not a session.
- A decision whose entry or exit can't be read from Kite is **excluded**
  from every figure, with the reason recorded. A session counts toward the
  60 only if at least one decision was priced live at both ends.

The questions, state, costs, pass rule and kill rule are unchanged.

---

# Clarification 4 — 2026-09-28, after the first round opened and before any round has closed

At the owner's request the Jev Book page shows, while a round is open, where
its positions stand at Kite's last traded prices ("if closed now", after the
same round-trip cost). Until now the page showed nothing between the 09:45
entries and the 15:08 close, and read as if the book were not trading.

**What had been seen when this was written:** the first round's 15 entries
(2 buys, 13 shorts, no skips, every one on the scanner's own side), and two
interim marks of it, −9.9 bp a position at 12:14 and −10.7 bp at 12:22. No
round has closed, so no scored result exists.

**What this changes: nothing in the test.**

- The mark is display only. It is computed on request, never written to the
  state file, and never enters the summary, the kill rule or the verdict.
- The record of a decision is still its entry when Jev answered and its exit
  at the 15:08 square-off, both from Kite. The pass rule is evaluated once,
  at 300 decisions or 60 sessions, on those closes alone.
- Jev is shown nothing new. Its snapshot and questions are unchanged.
- Nothing acts on the mark: no stop, no target, no early close.
- Prices for the mark come from Kite only, as for the fills (Clarification 3).
  Without Kite the page says there is no live mark.

An interim mark can tempt a reader to judge the test early. The page says
beside the figure that it is a live mark and not a result.

---

# Clarification 5 — 2026-09-28, after the first round closed

**What had been seen:** the first round, closed at 15:08. 15 decisions, all
on the scanner's own side, +22.8 bp net a position (t 0.86), identical to
the scanner, while the NIFTY fell 36 bp over the same window.

**The change:** from the first session on which this is deployed (expected
2026-09-29; the actual date is added below once it is live), the scanner's
list is chosen differently (README §91). It becomes the 25 eligible stocks with the highest 20-day
average turnover, fixed for the day, in turnover order. The Jev book still
takes the first 15 names on that list, so from then on Jev judges the 15
most-traded eligible NIFTY 100 stocks each day.

**Unchanged:** the snapshot Jev sees, including the scanner's side and
reasons; the three questions; the fills from Kite only; the cost; the
comparison with the scanner's own side; the pass rule; the kill rule.

**How the record is read:** the list was always a daily choice by the
scanner, and only the way it is chosen changes. 2026-09-28 stays in the
record. The verdict will also be reported with that day left out, so the
reader can see whether it moves the result.

This change was not made to improve Jev's score. It follows from the
scanner's ranking carrying no information and from the list rotating, both
found in the same review.

**Clarification 5, deploy date.** **Deployed 2026-09-28 at 20:37 IST** (backend restarted from `main` at `f0a1287`). The first session chosen by the new rule is **2026-09-29**. Every session before it used the old rotating list. Jev's first round on the new list is 2026-09-29 at 09:45.

---

# Clarification 6 — 2026-09-29, written before the change is deployed

**What had been seen:** one closed round (2026-09-28), as in clarification 5.
The 2026-09-29 round had not run when this was written.

**The change**, from the first session after it is deployed (the date is
added below once it is live). README §100.

1. **The day's list is fixed before the open**, at the first pre-market read
   at or after 08:45. Until now it was fixed at the first scan of the
   session. Both use daily data only. So clarification 5 was right about what
   the list is and wrong about when it was fixed: on 2026-09-29, and on any
   session before this is deployed, it was fixed at the first scan.
2. **The daily data runs through the last completed session.** The delayed
   feed's daily bars can end a session early. When they do, the last session
   is added from NSE's own files (#192). In-session scans were not affected
   by this; a read before the open was.
3. **Guards.** A stock on the F&O ban list, in trade-for-trade, under graded
   surveillance, or within 2% of a fixed price band is left out of the list.
   A stock with a fixed price band is scored as a long only, so its row's
   side is always LONG. Three NIFTY 100 stocks have a fixed band on
   2026-09-29 (ENRIN, TATACAP, TMCV); none of them is among the 15 most-traded.

**Unchanged:** Jev still takes the first 15 names on the list; the snapshot,
the three questions, the fills from Kite only, the cost, the comparison with
the scanner's side, the pass rule and the kill rule.

**Not part of this change:** the scanner's intraday numbers (gap, relative
volume, VWAP side) still come from the delayed feed. Its gap differs from
NSE's opening gap by 0.3 points or more on 7 of 20 stock-days checked (#193).
Jev's fills have used live Kite prices since clarification 3. A move of the
scanner to live prices will get its own note.

**How the record is read:** as before. The guards can only remove a name from
the list; they were not made to improve Jev's score.

---

# Clarification 7 — 2026-09-29, written before the change is deployed

**What had been seen:** as in clarification 6.

**The change**, from the first session after it is deployed (the date is
added below once it is live). README §101.

**The scanner row Jev sees is built from live prices.** Until now the
scanner's numbers for the day (last price, change, gap, relative volume, VWAP
side) came from a feed about 15 minutes late. At the 09:45 round Jev's
snapshot therefore described the market of about 09:30. From this change the
row comes from one live Kite quote. The gap is measured from NSE's opening
price; the delayed feed's was not, and differed by 0.3 points or more on 7 of
20 stock-days checked (#193). The scanner's side and reasons are worked out
from those numbers, so they can differ from what the delayed feed would have
given.

**What this does not change:** Jev's fills have been live Kite prices since
clarification 3, so no recorded fill is affected. The list, the three
questions, the cost, the comparison with the scanner's side, the pass rule
and the kill rule are unchanged.

**How the record is read:** rounds before the change were judged on a
snapshot about 15 minutes old, and rounds after it on a current one. The
verdict is reported for all rounds, and for the rounds after the change
alone. The change was made because the delayed numbers were wrong, not to
improve Jev's score; it could move the score either way.

If Kite is not connected at 09:45 the round is skipped, as before.

