# Bug log

Every bug found in Trader Sahab gets:

1. A GitHub issue labeled `bug` (or `documentation` for doc errors), with the
   evidence that proves it.
2. A row in this file.

When a fix merges, move the row to **Fixed** with the PR. The fix only
counts as live once the backend has been restarted, so record that date
too.

Bugs from before issues were used are listed with their README section
and fix commit instead.

## Open

| Issue | Found | Bug | Impact |
|---|---|---|---|
| [#35](https://github.com/harshece16/intraday-trading-agent/issues/35) | 2026-09-18 | F&O P&L ignores charges entirely — `_record_fno_trade()` hardcodes `charges: 0.0` and never calls `costs.leg_cost()`, unlike the equity path. Found while fixing #21. | Options "net" P&L equals gross, in the header, the journal, the 2% daily loss limit and the F&O confidence IC. Worse than for equity: options brokerage is a flat ₹20/leg, so it doesn't scale down with a small position. |
| [#22](https://github.com/harshece16/intraday-trading-agent/issues/22) | 2026-09-17 | A backend restart forgets today's per-stock entry count. | After a mid-session restart, a stock already traded today can be traded again, breaking the one-entry-per-day rule. Blocks deploying fixes mid-session. |
| [#24](https://github.com/harshece16/intraday-trading-agent/issues/24) | 2026-09-17 | The dashboard says "Kite live prices" after the Kite session has expired. The status only checks that a token exists. | You see live data while the engine is actually on the yfinance fallback. |
| [#26](https://github.com/harshece16/intraday-trading-agent/issues/26) | 2026-09-17 | README §2 still says top 15 deep reads and a top-6 watchlist; config says 25 and 25. | Docs only. |

## Fixed

| Issue / section | Fixed | Bug | Fix |
|---|---|---|---|
| [#28](https://github.com/harshece16/intraday-trading-agent/issues/28), §46 | 2026-09-18, PR #37. Deployed 2026-09-18 (backend restarted with 0 positions open). | The share count was rounded twice: `position_size()` returned whole shares and the caller then applied the checklist's reduced size factor and truncated again, so 60% of a 3-share cap became 1 share (33%) and 60% of a 1-share cap became 0 and blocked the trade. Live on 17 Sep: DIVISLAB entered at 1 share while the note said "60% size". | The size factor is passed into `position_size()`, which now rounds once, at the end. DIVISLAB's case goes 1 -> 2 shares. Rounding stays downward so a reduced position can never exceed the caps. A skipped reduced-size trade now says which of the two reasons applied. |
| [#25](https://github.com/harshece16/intraday-trading-agent/issues/25), §46 | 2026-09-18, PR #37. Deployed 2026-09-18. | A pattern stop could sit closer to the entry than the round trip costs to make, so losing at the stop cost more than 2R by construction. TMPV's stop was 0.41x the cost and lost 4.33R net in 38 s; a nominal 3:1 at that stop is really 0.60:1 after costs. | A required checklist rule, `min_stop_to_cost`, re-applied at the live fill price. Set to **1x**, not higher: over 54 sessions of NIFTY 100 a 2x floor made expectancy worse (-0.50R -> -0.61R) and on the 8 real trades a 3x floor blocked both winners and landed at -1.37R/trade. Not claimed as an edge — all 8 live trades predate the §42 candle fix, and the backtest has no trade under 1x at all. |
| [#21](https://github.com/harshece16/intraday-trading-agent/issues/21), §45 | 2026-09-18, PR #34. Deployed 2026-09-18 at 00:33 IST (backend restarted with 0 positions open; journal backed up first, then restated on open). | Every P&L the app showed was gross. Brokerage, STT, exchange fees, GST and stamp duty were stored in `charges` and never subtracted — not from "Realized today", the Trades page, the 2% daily loss limit, or the Scorecard's R-multiples, so live R was never comparable with the backtester's net R. PR #15's columns carried a comment wrongly claiming they were net. Over the 8 closed round trips: −₹5.26 gross vs −₹168.71 net; −0.25R vs −0.99R expectancy; 0.74R of charges per trade. | The opening leg's charges ride on the position and are released when it closes, so `realized` is net of both legs; `realized_gross` keeps the old figure beside it. The existing journal was restated by pairing legs on `position_id` — gross − net came to ₹163.45, matching the charges column exactly. Turnover stays gross for tax. F&O charges are still not modelled at all. |
| [#23](https://github.com/harshece16/intraday-trading-agent/issues/23), §43 | 2026-09-17, PR #31 (`a84bb05`). Deployed 2026-09-17 at 15:02 IST; cycles finished every 30–81 s afterwards with Kite still down. | With Kite's session expired, the engine stalled: no cycle finished from 04:33 to 09:53, then cycles finished only every 15–55 min. Overlapping yfinance downloads returned each other's tickers (the engine-sized call got 25 of the scan's and none of its own) and could wait forever. Every cycle also re-sent all 25 stocks to a rejected Kite token. | One yfinance download at a time (120 s lock timeout); a rejected token is skipped until it changes; a watchdog logs thread stacks when a cycle runs past 2 min. The overnight stall's exact call is still unproven; the watchdog will capture it. |
| [#18](https://github.com/harshece16/intraday-trading-agent/issues/18), §42 | 2026-09-17, PR #20 (`7557653`). Deployed 2026-09-17 at 14:44 IST (backend restarted with 0 positions open). | The live checklist read the unfinished 5-minute candle. Volume passes ranged from 5.7% in a candle's first minute to 32% in its last. In 3 of the first 5 trades, the pattern that triggered the entry was gone once its candle closed. On 17 Sep, before the deploy, the same happened to MAZDOCK and DIVISLAB (both lost), while INDHOTEL's pattern survived (it won). | The checklist reads only finished candles, and the plan is re-checked at the live price before entry. |
| §38 | 2026-09-16, PR #10 (`701a1d7`) | The Scorecard's IC row counted stocks, not separate days, so one day's market-wide move passed it. | One rank IC per session, at least 20 sessions, t-stat ≥ 2. |
| §37, §30 | 2026-09-16, PR #9 (`ec29411`) | "+0.29 IC, a real edge" was reported from a single day's cross-section. | Corrected. Measured across 434 sessions, the daily IC is 0.000. |
| — | 2026-09-16, PR #8 (`1c6fa7e`) | Restart-rehydration tests used `now − 3600`, which fails in the hour after IST midnight. | A `_today_ts()` helper that always lands on today. |
| [#1](https://github.com/harshece16/intraday-trading-agent/issues/1), §35 | 2026-09-15, PR #6 (`846587e`) | `backtester.py` never applied the confidence gate, so tuning its threshold changed nothing. | The backtester applies the same gate as live, using the real Scorecard. |
| §33 | 2026-09-15 (`6ff3cdf`) | Slippage was applied in backtests but never to live or paper fills. | `apply_slippage()` added to `_execute()`. |
| §33 | 2026-09-15 (`6ff3cdf`) | A restart erased today's trades from the dashboard, and the daily-loss counter's memory of them. | `_rehydrate_today()`, plus the engine's day and loss counters seeded from it. |
| §32 | 2026-09-15 (`974b637`) | Confidence gate deadlock: the maximum possible score (100 × 0.5 = 50) could never reach the bar of 60. | The "not proven yet" multiplier went from 0.5 to 0.6. (This was a policy decision, made with the user.) |
| §30 | 2026-09-15 (`2dd07b6`) | IC was computed on 8,091 near-duplicate "pairs" from repeated scans, and reported −0.124. | One reading per (symbol, session). |
| §30 | 2026-09-15 (`2dd07b6`) | `round(_spearman(...))` crashed when every value on one side was tied. | The helper reports "no variance" instead. |
| §28 | 2026-09-15 (`59aeaf4`) | `get_candles_batch()` raised an error when the yfinance fallback also failed. | `_safe_yfinance_batch()`. |
| §27 | 2026-09-15 (`59aeaf4`) | The reward:risk target was always the nearest level, so R:R failed 99% of the time (median 0.06). | Walk outward to the first level that clears 1.5R, within 3 ATR. |
| §26 | 2026-09-15 (`3f9b108`) | The test suite wrote fake rows into the live production journal. | An autouse fixture gives each test its own database. |
| §25 | 2026-09-15 (`3f9b108`) | Candles were fetched one symbol at a time (too slow for 25), and unpaced Kite calls hit "Too many requests". | Concurrent, paced batch fetch. |
| §24 | 2026-09-15 (`3f9b108`) | An entry blocked by a later gate still used up the stock's one entry for the day. | Roll back the entry count when no order is placed. |
| §24 | 2026-09-15 (`3f9b108`) | An untracked real Kite position raised an alert but didn't stop a second real entry in that stock. | Entries are blocked while the mismatch lasts. |
| §24 | 2026-09-15 (`3f9b108`) | The one-position-per-sector cap silently did nothing when a stock had no scanner row. | Falls back to the universe list's industry. |
| §9, §19 | 2026-09-15 (`6b6ea7f`) | The confidence gate only applied to F&O; cash equity traded on the checklist alone. | The same gate now applies to cash equity, with a regression test. |
| §19 | 2026-09-15 (`6b6ea7f`) | One uncaught exception outside the per-symbol loop could permanently kill the engine loop. | `tick()` wraps `_tick_impl()`, and `run_forever()` guards its executor call. |
| §19 | 2026-09-15 (`6b6ea7f`) | The Portfolio page described paper capital as the real, synced Kite balance. | Paper/live-aware wording. |
| §19 | 2026-09-15 (`6b6ea7f`) | Security: CORS allowed every origin, and the dashboard key was printed in full on every restart. | CORS limited to the dashboard origins; the key is masked after first generation. |
