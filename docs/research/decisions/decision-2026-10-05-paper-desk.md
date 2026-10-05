# Decision, 2026-10-05: the paper desk — four paper books as equal experiments

**Taken 2026-10-05, in the morning, during the first session of the rule lab.** An addendum to the decision of 2026-09-30 ([`decision-2026-09-30-momentum-core.md`](decision-2026-09-30-momentum-core.md)) and its addendum of 2026-10-01. It changes how the dashboard presents the books. It changes no book's rule, gate or order path, and it promotes nothing.

## The owner's words

> "instead of momentum book as strategy can we open all like intraday jev book rules log all process trade in paper"

Read as: the front page should no longer present the momentum book as *the* strategy. All four paper books are equal experiments. Each trades in paper and logs every process step and every trade, and nothing is "the strategy" until it earns that under the project's gates.

## What changes

1. **The front page is the paper desk** (`/`). One card per book, equal in size and in wording: what the book is in one line; its status now (running, waiting, skipped today and why, switched off); today's trades and money; its record so far with the book's own headline statistic (the intraday engine's expectancy in R, the Jev book's net bp a position, the rule lab's rules and candidates, the momentum book's cumulative excess); its next event (the square-off, the next round, the screen, the next rebalance); the gate it must pass before any real money, in one line; and a link to its page. The momentum book's landing moves to `/momentum-book`. The intraday Overview stays at `/intraday`; `/overview` still redirects there.
2. **One process log** (`/process-log`, and a compact strip of today's newest lines on the desk). It merges, newest first, every process step and trade of the four books on one IST day: the engine's scans, setups, entries, exits, review cards and square-off; the Jev book's rounds and decisions; the rule lab's sessions and the trades it opened and closed, grouped by bar with each trade expandable; the momentum book's evening-job runs, trades, rebalances and alerts. Each line carries the book, the kind, the time, the symbol where there is one, and money where there is money. Filters by book and kind; today by default, with a day picker.
3. **Two read-only endpoints**: `GET /api/paper-desk` for the cards and `GET /api/process-log?day=&book=&kind=` for the log (`backend/paper_desk.py`). Both are assembled from what the books already write: the `activity`, `trades`, `rule_lab_trades` and `rule_lab_sessions` tables, the Jev book's state file, the momentum book's state file, its job log and its alert record. **No new writes, no new table, no new log line in any book**, and no change to any book's logic or to any order path. The two lines the engine already logs about the Jev book and the momentum book's job are re-tagged to their books in the merged view.
4. **The wording.** "The strategy" leaves the sidebar, the intraday banner and the momentum page. The banner keeps the honest line: no intraday edge was found, and every book is paper.

## What does not change

- **The live gate is unchanged.** RES-27: a pass authorises a paper book only; real money is a separate owner decision. ENT-02 and ENT-05: in Live, no automatic entry can pass the confidence bar of 60 while the Scorecard's backtest row fails. RES-36: the rule lab's promotion ladder (screen at session 40, confirmation on the next 40, a proposal that spends a trial, the owner's yes, the engine's live gate). MOM-10 and MOM-16: the momentum band from month 6, and the alert at each rebalance. L53, the after-tax comparison of the momentum book with a harvested index fund, is still the measurement that has to be made before its gate can be said to be passed.
- **Nothing is promoted or demoted by this change.** The momentum book is still the one rule that passed a pre-registered test, narrowly (trial 126). The desk says so on its card. The intraday engine still has no edge (§51, §69, §88). The Jev book (trial 123) and the rule lab (L54) are forward tests with no verdict yet.
- **No real money.** The engine stays in paper; F&O stays off. No date or threshold for real money is set anywhere.
- **No book's rule.** The momentum book's universe, signal, fills, costs, benchmark and band; the Jev book's questions, fills and kill rule; the rule lab's rules, exits, costs and looks; the intraday engine's rules, gates, sizing, stops and square-off. The parity tests of each are untouched.
- **RES-33** (no new intraday look) is unchanged. The desk is a view, not a look.

## Why this is the right reading

The 2026-09-30 decision made the momentum book the core because it was the one thing that had passed. The owner's new framing does not dispute the evidence; it refuses to let a narrow backtest pass stand in for a live record. Under the project's own rule (nothing trades until it passes a test written down before its data was read), a book that has run on paper for four sessions is an experiment, however good its backtest. Showing all four as experiments, with their gates beside them, is the more honest page. It also makes the one thing the owner asked for visible: every step and every paper trade of every book, in one place, with the money.
