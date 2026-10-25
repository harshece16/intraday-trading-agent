---
name: New strategy checklist
about: The steps every new trading idea goes through before it may run
title: "New strategy: <name>"
labels: []
---

Rule ids point into [the rules checklist](https://github.com/harshece16/intraday-trading-agent/blob/main/docs/architecture/RULES.md).
A step that fails stops the line. It is not retried with a different setting.

## Before any code

- [ ] Checked what is already known: the trial ledger, the sweeps, the closed lines in the README and `docs/history.md`
- [ ] Named the family (one economic mechanism) and counted N, at least 2 (`EVL-01`)
- [ ] The effect is stated in basis points and compared with the round-trip cost (`EVL-13`)
- [ ] **Pre-registration committed**: rule, universe, period, costs, metric, pass rule, what would falsify it (`RES-01`)
- [ ] If scope or the bar changes, the owner's decision is recorded first

## Data

- [ ] Stage 0 ran and read no return (`RES-16`)
- [ ] Only sessions before 2026-01-02 were read (`RES-03`)
- [ ] Any read of 2026 data is in the held-out exposure log (`RES-07`)
- [ ] Features use only data available before the decision (`RES-20`)

## The run

- [ ] One run (`RES-02`)
- [ ] Results file opens with the verdict in the pre-registration's own terms
- [ ] Ledger row added; the trial count went up (`RES-10`)
- [ ] Survivorship, contamination, universe and cost model are stated (`RES-31`)

## The gates

- [ ] Net-of-cost t clears the family's Bonferroni bound (`EVL-01`)
- [ ] Corrected Deflated Sharpe is 0.95 or more at N (`EVL-03`)
- [ ] Positive in both halves (`EVL-07`)
- [ ] Positive in the most recent three years (`EVL-08`)
- [ ] Every gate holds. A raw positive backtest is not a pass (`EVL-10`)

## Only after a pass

- [ ] Confirmed on data the test never read
- [ ] Held-out look approved by the owner, then taken once (`RES-06`, `RES-25`)
- [ ] Paper book built with a switch-off band fixed in advance (`RES-26`)
- [ ] `docs/history.md` section added (`WFL-06`)
- [ ] Nothing describes the result as a guarantee. Real money is a separate owner decision (`RES-27`)

## Verdict

