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
