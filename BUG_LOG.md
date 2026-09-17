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
| [#23](https://github.com/harshece16/intraday-trading-agent/issues/23) | 2026-09-17 | Engine stopped ticking for 5h20m after the Kite session expired (04:33:50 → 09:53:44). It recurred from 11:18 to 13:37: with Kite down, each tick waited 15–55 min on the yfinance fallback, and 19 Yahoo connections were left open. | No scans, reads or entries for the first 38 min of the 17 Sep session. Later, an open position's stop was checked only once per slow tick. |
| [#21](https://github.com/harshece16/intraday-trading-agent/issues/21) | 2026-09-17 | Recorded P&L leaves out brokerage and taxes. Only slippage is counted. PR #15's P&L/Net columns were wrongly described as net. | "Realized today", the Trades page, the 2% daily loss limit and the Scorecard all look better than reality. Across 5 trades: −₹183 shown vs −₹283 real; −0.41R shown vs −1.26R real. |
| [#22](https://github.com/harshece16/intraday-trading-agent/issues/22) | 2026-09-17 | A backend restart forgets today's per-stock entry count. | After a mid-session restart, a stock already traded today can be traded again, breaking the one-entry-per-day rule. Blocks deploying fixes mid-session. |
| [#24](https://github.com/harshece16/intraday-trading-agent/issues/24) | 2026-09-17 | The dashboard says "Kite live prices" after the Kite session has expired. The status only checks that a token exists. | You see live data while the engine is actually on the yfinance fallback. |
| [#25](https://github.com/harshece16/intraday-trading-agent/issues/25) | 2026-09-17 | Stops can be narrower than round-trip costs. The 33% notional cap, not the 1% rule, sets position size. | Charges averaged 0.84R per live trade. TMPV lost 4.33R net in 38 s. |
| [#28](https://github.com/harshece16/intraday-trading-agent/issues/28) | 2026-09-17 | The 60% size factor is applied after rounding to whole shares, so high-priced stocks get far less than 60%, or nothing. | DIVISLAB got 1 of 3 shares (33%). Stocks above ~₹16,500 can't take a reduced-size trade at all. |
| [#26](https://github.com/harshece16/intraday-trading-agent/issues/26) | 2026-09-17 | README §2 still says top 15 deep reads and a top-6 watchlist; config says 25 and 25. | Docs only. |

## Fixed

| Issue / section | Fixed | Bug | Fix |
|---|---|---|---|
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
