# Backtest trial log

Committed, append-only mirror of `backend/data/backtest_trials.json`, which is
gitignored and therefore does not survive a clone. This file exists so the
multiple-testing count can be audited by someone who was not at the machine
that produced it.

**Why it matters.** The Deflated Sharpe Ratio
(`evaluation.deflated_sharpe_ratio`) discounts an observed Sharpe by the
number of configurations tried. That count is the denominator of every
significance claim in this project. Losing it, or understating it, makes every
backtest look better than it is.

## Rules

- **Every backtest run of a strategy variant increments the count.** The
  counter is `evaluation.log_trial(label)`.
- **Measurements do not increment it.** An IC computation, a return
  decomposition, or any read that does not select a strategy is a *research
  look*, recorded in its own section below.
- **A replication of an already-counted run does not increment it.**
  Re-running an identical configuration to recover its trade list is not a new
  attempt at finding an edge. Such runs are recorded here explicitly, marked
  *replication, not counted*.
- When the JSON and this file disagree, **the JSON is the source of truth** for
  the count; this file is the auditable record of what those counts were.

---

## Strategy trials — count as of 2026-09-20: **34**

| n | Label |
| --- | --- |
| 1 | `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d` |
| 2 | `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d` |
| 3 | `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d` |
| 4 | `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d` |
| 5 | `sahab_dimaag ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK'] 5m 55d walk-forward-3` |
| 6 | `sahab_dimaag NIFTY 100 scanner, top 25/day 5m 55d` |
| 7 | `grid-search min_confidence_to_trade=60 min_rrr=1.5 nifty100 top5 5m 10d` |
| 8 | `grid-search min_confidence_to_trade=40 min_rrr=1.2 nifty100 top5 5m 55d` |
| 9 | `grid-search min_confidence_to_trade=40 min_rrr=1.5 nifty100 top5 5m 55d` |
| 10 | `grid-search min_confidence_to_trade=40 min_rrr=1.8 nifty100 top5 5m 55d` |
| 11 | `grid-search min_confidence_to_trade=50 min_rrr=1.2 nifty100 top5 5m 55d` |
| 12 | `grid-search min_confidence_to_trade=50 min_rrr=1.5 nifty100 top5 5m 55d` |
| 13 | `grid-search min_confidence_to_trade=50 min_rrr=1.8 nifty100 top5 5m 55d` |
| 14 | `grid-search min_confidence_to_trade=60 min_rrr=1.2 nifty100 top5 5m 55d` |
| 15 | `grid-search min_confidence_to_trade=60 min_rrr=1.5 nifty100 top5 5m 55d` |
| 16 | `grid-search min_confidence_to_trade=60 min_rrr=1.8 nifty100 top5 5m 55d` |
| 17 | `grid-search min_confidence_to_trade=70 min_rrr=1.2 nifty100 top5 5m 55d` |
| 18 | `grid-search min_confidence_to_trade=70 min_rrr=1.5 nifty100 top5 5m 55d` |
| 19 | `grid-search min_confidence_to_trade=70 min_rrr=1.8 nifty100 top5 5m 55d` |
| 20 | `diagnostic re-run at live default config for segmentation analysis` |
| 21 | `diagnostic re-run, confidence gate off, for checklist-entry segmentation` |
| 22 | `diagnose_entry_edge checklist 5m 55d top5 gate-off` |
| 23 | `diagnose_entry_edge checklist 30m 55d top5 gate-off` |
| 24 | `diagnose_entry_edge baseline 5m 55d top5 gate-off` |
| 25 | `diagnose_entry_edge baseline 30m 55d top5 gate-off` |
| 26 | `swing_backtester long-only hold=1 top5 2y stop_atr=None` |
| 27 | `swing_backtester long-only hold=2 top5 2y stop_atr=None` |
| 28 | `swing_backtester long-only hold=3 top5 2y stop_atr=None` |
| 29 | `swing_backtester long-only hold=5 top5 2y stop_atr=None` |
| 30 | `sahab_dimaag NIFTY 100 scanner, top 5/day 5m 730d` — the gated deep backtest (report Test B) |
| 31 | `swing_backtester long-only hold=1 top5 2y stop_atr=None` |
| 32 | `swing_backtester long-only hold=2 top5 2y stop_atr=None` |
| 33 | `swing_backtester long-only hold=3 top5 2y stop_atr=None` |
| 34 | `swing_backtester long-only hold=5 top5 2y stop_atr=None` |

### What a reviewer should notice in this list

- **Entries 7–19 are a single 13-point grid search** over
  `min_confidence_to_trade` × `min_rrr`. That is 38% of the entire trial
  count spent on one parameter sweep of a strategy later shown to have no
  edge. It is exactly the search behaviour the DSR exists to penalise, and it
  is correctly counted.
- **Entries 26–29 and 31–34 are the same four swing configurations run
  twice.** The second run (31–34) was a re-execution on 2026-09-20. Under the
  replication rule above it arguably should not have incremented the counter,
  but `swing_backtester.py` logs unconditionally and it did. **The count is
  therefore conservative by up to 4** — it may overstate the number of
  genuinely distinct attempts. Left as-is: an overstated trial count makes the
  DSR stricter, not laxer, and correcting it downward would weaken a
  significance bar in our own favour.
- Entries 20–25 are diagnostics and segmentation runs. They re-ran strategy
  configurations, so counting them is defensible, though several are closer to
  measurement than to search.

**Test A of the status report — the 201-trade ungated run — is not in this
list.** It was executed through `run_backtest()` directly by an ad-hoc script
rather than through `backtester.py`'s `main()`, which is where `log_trial()`
is called. That is a gap in the counter's coverage: **driving `run_backtest()`
programmatically bypasses the trial log entirely.** Every phase-2 run does
exactly that, so phase 2 must log its trials here by hand.

---

## Research looks — measurements, not strategy selections

These do **not** increment the DSR trial count. They are recorded because a
look at the data is still a look, and a reviewer should be able to count them.

| # | Look | Date | Counted? |
| --- | --- | --- | --- |
| L1 | Daily rank IC of the composite pre-market score vs session return (436 days) — reported in `swing_backtester.py` output | 2026-09-20 | No — measurement |
| L2 | Loss attribution over the 201-trade sample: exit-reason split, gross vs net, by side, payoff arithmetic, holding time | 2026-09-20 | No — measurement on an existing trade list |

---

## Replications — re-runs of already-counted configurations

| # | What | Reason | Counted? |
| --- | --- | --- | --- |
| *(none yet)* | | | |

---

## Phase-2 runs

Nothing yet. Every phase-2 strategy run will be appended to the strategy table
above with its pre-registration file named, and every measurement to the
research-looks table.
