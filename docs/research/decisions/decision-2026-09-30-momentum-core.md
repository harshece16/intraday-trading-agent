# Decision, 2026-09-30: the monthly momentum book is the core of Trader Sahab

**Taken 2026-09-30 at about 21:40 IST, the evening before the book's first rebalance (the 1 October 2026 close).** The book held nothing and had recorded no return when this was decided.

## The owner's words

The owner was told that 202 strategy trials and research looks L40 to L51 had found no intraday edge that pays the round-trip cost of about 16.6 bp, and that the only strategy to pass its gates was the monthly momentum book (trial 126), running on paper with ₹10 lakh since 2026-09-26. The recommendation put to the owner:

> Make the monthly momentum book the core of Trader Sahab, with the front page, an alert at each rebalance, and a monthly report against the index. Stop searching for an intraday edge, and keep the intraday engine in paper mode as a record, not as the strategy. Put real money in only after months of paper results agree with the backtest; the book's own band rule switches it off if, after six months, it trails too far.

The owner answered: **"ok go ahead"**.

"The index" in that recommendation means the book's own benchmark, the equal-weighted 200: the same 200 most-traded NSE stocks the book ranks, equal-weighted. The book is not built on a NIFTY index, and its report and band are measured against that benchmark.

## The evidence, in brief

The full ledger is [`trials.md`](../trials.md): 202 strategy trials as of 2026-09-30.

**The one strategy that passed.** Slow cross-sectional momentum held in delivery: rank the 200 most-traded NSE stocks (median traded value over 126 sessions, price at least ₹20), hold the 15 with the best volatility-adjusted 6- and 12-month return, keep a holding while it ranks in the top 30, rebalance monthly. Benchmark: the equal-weighted 200.

| Test | Result | Note |
| --- | --- | --- |
| Trial 120, 2010-02 to 2025-11 ([results](../results-3i-momentum-corrected-data.md)) | +0.82% a month over its benchmark, t 2.91, family DSR 0.98 | Passed the family-level bar at N_family = 3. Re-read months an earlier trial had seen |
| L38, ranks 201 to 400, never read before | +1.00% a month, t 3.31 | Confirmed |
| 2026 held-out, January to August | +1.28% a month, t 1.08, 6 of 8 months ahead | Confirmed as a sign check; eight months are weak evidence |
| **Trial 126**: trial 120's rule on repaired prices with orders that wait ([results](../results-universe-width.md)) | +0.71% a month, **t 2.51** against the 2.394 bar, DSR 0.952 | **The configuration the book runs.** It survives narrowly. At the family of 10 now counted it would not clear (bound 2.807, DSR 0.825), and at 0.07% slippage a side instead of 0.05% it would fail |
| L42, the same on ranks 201 to 400 (same file) | +0.91% a month, t 3.00 | Survives |
| Trial 127, a 400-stock book (same file) | Fail | A wider book is not shown to be better |

Momentum has losing years: about −12% to −13% against its benchmark in 2025 and −14% in 2016. None of this is a promise of future returns.

**No intraday edge.** Every intraday look since the checklist was retired failed or could not be run:

| Look | What was tested | Result | Note |
| --- | --- | --- | --- |
| L40 | Kronos forecasts, next 15/30/60 minutes | Fail at all three | [results](../results-kronos-feature-ic.md) |
| L46 | Six zero-shot forecasting models | Fail, 18 of 18 | [results](../results-tsfm-family.md) |
| L47 | LightGBM on Alpha158, trained on the project's bars | Fail at all three | [results](../results-qlib-lgbm-alpha158.md) |
| Trials 128 to 202 | Forecast × candlestick combinations | Fail, 0 of 75; none positive net | [results](../results-combo-search.md) |
| L48 | Market breadth and intermarket moves | No pass, 0 of 8 | [results](../results-3h-breadth-intermarket.md) |
| L49 | The scanner's four intraday features and the 09:45 gap reversal | Fail, 0 of 13 | [results](../results-scanner-features.md) |
| L50 | Bulk and block deals at the next open | Void at stage 0 (too few events) | [results](../results-bulk-block-deals.md) |
| L51 | Intraday index timing from lagged factor returns | Does not clear; no direction | [results](../results-index-timing.md) |

L41 was the data gate for the universe-width tests and L42 a momentum confirmation, both positional; L43 to L45 were not taken (too few months). The earlier intraday record, including the Varsity checklist at −0.36R a trade (t −3.59), is in README §51, §69 and §88.

## What changes

1. **The dashboard's front page is the Momentum Book** (`/`). It adds a monthly report against the benchmark (one row per completed month: the book's return, the benchmark's, the excess, the cumulative excess, turnover and costs), where the book stands against its band, the next rebalance date, and what the book holds. Before the first month completes it says there is no month yet. The intraday Overview moves to `/intraday`; `/momentum-book` and `/overview` still open their pages.
2. **An alert at each rebalance**, and when the evening job fails, stops early, or has not processed the day by 23:30. One line in the activity log, and on the phone through Telegram when Telegram is set up and switched on. Exactly one per rebalance, kept across a restart (`backend/momentum_alerts.py`).
3. **The intraday pages are labelled as the intraday paper record**, with a banner that says no intraday edge was found and that the strategy is the momentum book.
4. **No new intraday looks.** The research programme stops searching for an intraday edge.

## What does not change

- **No real money.** The engine starts in paper and stays there; F&O stays off. Nothing here sets a date or a threshold for real money. The band can say something from month 6 at the earliest, the rebalance at the first session of April 2027. Moving any money is a separate decision for the owner, after months of paper results have been compared with the backtest.
- **The book's rule.** Its universe, signal, portfolio, fills, costs, benchmark and band are unchanged. The band stays n × 0.71% − 2 × 3.89% × √n from month 6 (−14.8% at six months, −18.4% at twelve); below it the book switches itself off and nothing turns it back on. The parity tests in `backend/tests/test_momentum_book.py` are unchanged and pass.
- **The benchmark** stays the pre-registered one, the equal-weighted 200: the same 200 most-traded NSE stocks, equal-weighted, with the same percentage costs. The monthly report is against that benchmark, which is what the band measures. It is not a NIFTY index.
- **The intraday engine** keeps running in paper with every rule, gate and order path as it was. Its automatic entries stay blocked by the confidence gate; the review queue stays off unless the owner turns it on. *(2026-10-01: no longer true in paper; the paper engine takes automatic trades. See the addendum below and README §118.)*
- **L52** (the five newest forecasting models, forward, [`prereg-2026-models-forward.md`](../prereg-2026-models-forward.md)) stays pre-registered and on hold. It is scored only if the owner asks, after its 60th session (about late December 2026). Nothing needs to run daily for it: its bars are fetched after the 60th session.
- **The Kronos shadow** stays display-only (README §102), unchanged: the engine does not read it.

## Open for the owner

Two tests registered before this decision are not intraday-edge searches started after it, and this record leaves them as registered: the Jev book (trial 123, a forward paper test judged after 300 trades or 60 sessions) and the order-book test (its one pre-registered analysis is due after 15 full sessions, about 19 October 2026). Whether either should stop, or run when due, like L52 only on request, is the owner's call.

## Addendum — 2026-10-01: automatic trades in the paper engine (README §118)

Two later messages from the owner, the same night, after this decision:

> "we should not have stopped intraday, keep it running in paper too"

> "let it take automatic trades in paper mode"

The first needed no change: the intraday engine was never stopped. It has run in paper throughout, as this record says above. The second changes one line of "What does not change": **"Its automatic entries stay blocked by the confidence gate" stops being true in paper.**

- **What changes.** The cash confidence gate has two bars. In Paper the bar is `RISK["paper_min_confidence_to_trade"] = 0`, so the paper engine takes every checklist pass that clears every other rule. In Live it stays `RISK["min_confidence_to_trade"] = 60`. The bar is read at the moment of each entry, so a switch to Live restores 60 for the very next entry, and a position opened in paper stays a paper position. Every paper entry journals its confidence score, the bar applied, and whether the live bar would have blocked it (`trades.confidence_json`).
- **What does not change.** No real money: the engine stays in paper and F&O stays off (its own bar, `FNO["min_confidence_to_trade"] = 60`, is unchanged). Every other entry rule, risk limit, sizing, stop, square-off and cost is as it was. The momentum book is still the strategy; nothing here says the intraday engine has an edge (it has none: §51, §69, §88). The paper trades are a record, not evidence for going live.
- **A trade-off the owner should know.** The Dimaag Scorecard, which sets the live gate's multiplier, reads every closed trade in the journal, paper and live together (`database.trade_stats()` and the Deflated Sharpe row). Paper results now feed the live gate's evidence. Today this cannot open the live gate: the backtest-evidence row is a FAIL, and any FAIL holds the multiplier at 0.25 whatever the trades say. It would matter only if that row stopped failing. Left as is tonight; see README §118.
