# Pre-registration — the confluence engine on the deep Kite cache

**Written and committed before any result exists**, together with its script (`backend/research/confluence_deep.py`). **Requested by the user on 2026-09-24**, who asked for the "supporting evidence / live read" engine to be tested on the long data instead of the Varsity checklist. **It runs at the user's direction without external reviewer review**, unlike 3a/3b/3e. That is recorded here so the gap is visible.

## Why

`entry_mode: "confluence"` (README §5) scores ADX regime, swing structure, the 15-minute trend, trend and VWAP, location, momentum and candle triggers into bull/bear points. It was the engine before the checklist. **Its only measurement is trials 1–6**: 15 and 55 days of delayed yfinance data, before the Kite cache, the #74 cost fix and the §48 stop floor. There it lost before costs in every variant. Every deep run since (trials 30, 35–39 and Test A) used the checklist, so this engine has never met the phase-2 standard.

## Fixed in advance

| | |
| --- | --- |
| Arm | **Confluence only**, `config.STRATEGY_PARAMS["sahab_dimaag"]` with `entry_mode: "confluence"`, nothing else changed: entry_threshold 6.0, min_confirmations 3, min_edge 2.0, exit_threshold 5.0, max_entries_per_day 1, shorts allowed. Stops and targets are RiskManager's 1.5 / 3.0 ATR (confluence has no checklist plan). Exits also fire on the score swing, as live. |
| Comparator | **Trial 39** (the current checklist, same harness, costs and window): first half −0.360R (n 31), second +0.089R (n 7). Not re-run, which saves a trial. |
| Harness | Identical to fix74/fix40: `run_backtest()`, NIFTY 100, scanner top 5/day, confidence gate off, `scorecard = []`, `config.COSTS` (16.60 bp round trip), 5m Kite bars |
| Window | **Selection only**, before `splits.HELD_OUT_START` (2026-01-02). The held-out window is never loaded. `DAYS = 730` from the run date. |
| Split | `splits.halves()` of the selection sessions |
| Metric | Net R per trade, `pnl / (risk_per_share × qty)`. Also reported: trades, win %, gross R (post-slippage, pre-charges) and the stop in bp, so friction is visible. |

## Pass rule

> **PASS only if** net R per trade over the whole selection sample is **> 0 with t > 2**, **and** net R per trade is **positive in both halves**.
>
> **Anything else is a FAIL, and the live engine stays on the checklist.** A positive gross with a negative net is a FAIL. A positive mean with t < 2 is a FAIL, not "promising".
>
> **A PASS does not switch the live engine either.** It earns a held-out look, which needs the user's explicit say-so.

**Falsification stated in advance:** if confluence trades several times more often than the checklist at a similar or worse gross R, its larger trade count only multiplies friction. That confirms trials 1–6 on proper data, and the write-up will say so.

## Accounting

One run. A re-run only for a crash before any statistic was printed. **Counted as trial 40.**
