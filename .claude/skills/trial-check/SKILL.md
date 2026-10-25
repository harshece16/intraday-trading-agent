---
name: trial-check
description: Gate a new Trader Sahab strategy idea, backtest or forward test before it runs, and again before its verdict is written. Use for "test this strategy", "new idea", "backtest X", "is this an edge", a new prereg or a results file. Checklist adapted from ml4t/skills (backtest-overfitting, lookahead-bias, transaction-costs; Apache-2.0), rewritten for this repo's protocol.
---

Before any code:
1. **Is the line closed?** Check `docs/research/pivot-brief-2026-10-18.md` §1 and `docs/research/trials.md`. Intraday entries, the overnight ETF, PEAD, the Sahab Ranker, Kronos/TSFM and frog-in-the-pan are closed. If the idea is one of them, say so and stop.
2. **Read the count of record** at the top of `trials.md` and the family's bar. The momentum family has N = 11, so the next trial needs t ≥ 2.865. A new family starts its own count (§80).
3. **Write the prereg first.** It goes in `docs/research/prereg-<id>.md` and covers the hypothesis, pass rule, window, universe, sign convention, cost model and the falsification branch ("if X falls but Y does not rise, that is drift, not mechanism"). Commit order is prereg, then script, then run. The 2026 held-out window stays unread unless the prereg names it.

Running it:
4. **Costs in bp against the round trip.** Cash intraday is 16.60 bp, and a spread is two legs, so 33.20 bp. Delivery is about 22 bp plus 10 bp slippage plus ₹15.34 DP per stock sold (`costs.py`, `momentum_book.py`). Report at 1×, 2× and 3× cost. A t-stat or a rank IC is not money.
5. **Lookahead.** Shift rolling statistics by one bar. Time filings and results by announcement, not period end. Take universe membership point-in-time (#130 covers splits and ETFs in bhavcopy). Never shuffle time-series CV.
6. **One run per hypothesis.** Log it with `evaluation.log_trial(label)`. A re-run is allowed only after a crash before any statistic was seen, or for a declared bug fix with both runs recorded. A measurement that selects nothing is a research look, not a trial.

Judging it:
7. **Net of cost, both halves of the sample agree in sign.** Confirm on a fresh cross-section (another universe), not a later date range.
8. **Deflated Sharpe at the family count** (`evaluation.deflated_sharpe_ratio`). Treat these as red flags: Sharpe above 2 on daily data, out-of-sample within 5% of in-sample, or a complex model barely beating the one-signal rule.
9. **The results file** cites the prereg, script and run hashes and lists what went wrong. The trial is appended to `trials.md`. Research code stays in `backend/research/` and only reaches the live path through its own PR.
