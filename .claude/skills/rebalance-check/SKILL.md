---
name: rebalance-check
description: Discipline gate before and after each momentum-book rebalance, and before any step toward real money (MOMENTUM_LIVE, a Kite order path, a backend restart in market hours). Use for "rebalance", "month-end", "go live", "is it safe to restart", "post-mortem the rebalance". Adapted from tradermonty/claude-trading-skills (pre-trade-discipline-gate, signal-postmortem; MIT) and ml4t/skills (kill-switch, production-readiness; Apache-2.0).
---

Before. The book rebalances at the close of each month's first session. Check the evening before, then again by 15:00 IST on the day:
1. **Kite is connected.** `GET /api/kite/status` reports `connected`. The key is in `backend/.dashboard_key.json` and goes in the `X-Api-Key` header. A token made before 06:00 today is dead, whatever the file says.
2. **The book is on.** `GET /api/momentum-book` gives holdings, NAV against the benchmark and the switch-off band. If the status is `switched_off`, report that and do not rebalance.
3. **Prices are today's.** Every holding must have a fresh close (#263: a holding with no month-end row gets sold at a stale close). A data failure means no rebalance. Never trade on stale prices.
4. **The rule is still trial 126.** Changing the universe, lookback, holdings count or band makes a new trial (`trial-check`), not an edit.
5. **Real money needs all of these.** Every `live` issue (G1–G15, `gh issue list -l live`) is closed. The kill switch has been tripped once in a drill and shown to flatten the book. The owner has said yes in this session. Until then the book trades in paper.

Restarts: never between 09:15 and 15:30 IST with open positions. Wait for the old PID to exit, then check that the "Restored N open position(s)" line matches `/api/state`.

After, the evening of the rebalance:
6. **Post-mortem against the plan.** Compare names sold and bought against the rule's ranking. Measure fills against the model's price in bp, and charges and DP against the model. List any order that waited at a price band, and why.
7. **Anything that departs from the rule is a bug.** File an issue (label `bug`) and add a `BUG_LOG.md` row. Report the month plainly, including a loss to the benchmark.
