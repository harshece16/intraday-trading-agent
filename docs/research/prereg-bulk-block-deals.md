# Pre-registration — does an NSE bulk or block deal disclosure move the stock at the next open past cost? (research look L50; a trial only if it clears)

**Written 2026-09-30, from 20:00 IST, and committed before any code for this look exists.** Source of the idea: `data/predictive-tools-sweep/predictive_tools_C.md`, candidate 4 ("one event look, next open → +60 min, only if n ≥ 60 in NIFTY 100"). The owner asked on 2026-09-30 for every open research item to be completed. This fixes the events, timing, cost, statistics, family and gate before any deal in the sample, or any return, has been read.

**What it is not.** Not a strategy, not a backtest, not a trial. No order path, no config, no gate changes. Nothing reaches the scanner, the checklist, the review queue or the engine. `nse_feed.large_deals_today()` stays informational, as README says.

## 1. Question and expected answer

NSE publishes the day's bulk deals (a client whose trades in one stock on one day exceed 0.5% of its equity) and block deals (trades in the separate block windows, 08:45–09:00 and 14:05–14:20) after the close. The first price a trader reading the disclosure can get is the next session. **Does the side of the disclosed deal predict the stock's move over the first 15, 30 or 60 minutes after the next session's opening five minutes, by more than the 16.63 bp round trip?**

The literature is gross, in-sample event studies: Rajvanshi & Paul (2022; NSE 2010–2019) find 5–7% abnormal returns in the week around bulk deals, mostly *before* the event (front-running), larger for buys; Chaturvedula et al. (2015; 2004–2012) find significant CARs around bulk buys; Agarwalla & Pandey (IIMA WP 2010-04-02; 1-minute data) find block purchases carry about 1.6% permanent impact and block sales revert, with prices rising in the 8 minutes before block purchases. None measures a tradable window after the disclosure, net of cost. **Expected answer: no.** The same shape as L36 (results direction right in the overnight gap, +5.9 bp at 30 minutes, 0 by the close): whatever the deal says is in the price before 09:20.

## 2. What has been seen before this was written

- The literature summaries above, `entry-timing-sweep-2026-09-27.md` row 9, and README's note on the live bulk/block panel (one day in September 2026: 218 bulk, 39 block, concentrated in small names). No earlier look used deal data. L35's DEALS class was corporate filings (acquisitions, mergers), not market deals.
- **One pre-sample month of NSE's archive, August 2024** (before the sample starts), fetched on 2026-09-30 to learn the format, and nothing inside the sample window:
  - The report's JSON endpoint returns **at most 70 rows a query** (2 August 2024: 70 rows as JSON, 154 as CSV). Its CSV download returns every row; the August month file held the same 154 rows for 2 August as the one-day file. The CSV is therefore the source, and completeness is checked in stage 0 (§8).
  - Columns: Date, Symbol, Security Name, Client Name, Buy / Sell, Quantity Traded, Trade Price / Wght. Avg. Price, Remarks. **No client type.** Quantities carry Indian digit grouping ("3,03,645"); some Remarks cells hold a line break, so the file must be read with a CSV parser, not by lines.
  - **Block deals list both counterparties**: buy quantity equals sell quantity on 40 of 41 stock-days in August 2024 (the exception, KALYANKJIL on 22 August, 57.2 m bought against 66.5 m sold). The file therefore gives a block deal no side.
  - **Bulk-deal rows include intraday round-trippers** that appear on both sides with near-equal quantities (for example GRAVITON RESEARCH CAPITAL LLP, 704,300 bought and 704,300 sold in one stock on 1 August 2024). 310 of 1,094 bulk stock-days in August 2024 had buy quantity exactly equal to sell quantity. A block trade by a client above 0.5% also appears in the bulk file (NETWEB, 2 August 2024: the four sellers' 2,054,795 shares appear in both files, with the large buyers on the bulk side).
  - Two NIFTY 100 names were visible in that month's block rows (ADANIENSOL, TRENT, small blocks on 7 August). No price or return of any kind was computed.
- The Kite 5-minute cache's symbol list and date range (100 symbols, bars 2024-09-20 to 2026-09-18, one fetch run, 2026-09-20). No price was read.

## 3. Data, fixed

- **Deals.** NSE's historical bulk and block deal report (`nseindia.com/report-detail/display-bulk-and-block-deals`), CSV download: `/api/historicalOR/bulk-block-short-deals?optionType={bulk_deals|block_deals}&from=DD-MM-YYYY&to=DD-MM-YYYY&csv=true`. No login. One query per calendar month and type, at least 2.5 seconds apart, run under `nice`. Raw files cached unchanged under `backend/data/nse_deals/` (gitignored). **Deal dates 2024-09-19 to 2025-12-22 only** (the sessions before the first and after the last sample session); nothing later is requested.
- **Symbols.** NSE's `symbolchange.csv` (`nsearchives.nseindia.com/content/equities/symbolchange.csv`), cached the same way, maps each deal's symbol to today's symbol, following chains (the cache and the membership file use today's symbols; for example ZOMATO → ETERNAL).
- **Universe.** Point-in-time NIFTY 100 membership on the entry session (`backend/research/data/nifty100_membership.csv`, `kronos_feature_ic.membership_asof`), intersected with the cache. A member with events but no cached bars loses those events; stage 0 lists them.
- **Bars.** The Kite 5-minute cache, opened **read-only** (`sqlite3` `mode=ro`), with the SQL itself bounded to bars before 2025-12-24 IST. **The 2026 window is not read.** Bar times are IST starts; the bar starting 09:20 covers 09:20–09:25.
- **Sessions.** A date is a regular session if at least 50 cached symbols have a bar starting 09:20 (this excludes Muhurat trading). **Sample: regular sessions from 2024-09-20 to 2025-12-23**, which is the selection window ending five sessions before `splits.HELD_OUT_START`.
- **Cost.** 16.63 bp per event: the round trip of one directional position (one leg in L40's sense, where a long-short spread paid two).
- BSE's own bulk and block lists are not used; a deal executed on BSE alone is not an event here.

## 4. Events, fixed now

**Unit.** One stock-day per deal type: (today's symbol, deal date D, BULK or BLOCK).

**BULK side.** Over every bulk row of the stock-day, B = total quantity bought, S = total quantity sold, net N = B − S, gross G = B + S.
- **Directional** if |N| ≥ G/3, that is, the larger side is at least twice the smaller. Side = sign(N): **BUY** (+1, long) or **SELL** (−1, short).
- Otherwise **MIXED**: counted, never tested. This covers the round-trippers of §2 (N ≈ 0) and a stake transfer whose buyers are each large enough to be listed, where the file names both sides and claims no direction.

**BLOCK.** NSE lists both counterparties of every block trade, so the file gives no side (§2). **BLOCK is not directional and is not tested.** Its count, and its absolute move against a baseline, are reported as description (§6). A side from the block price's premium or discount was considered and not adopted: the file does not say which window a block traded in, so its reference price is unknown, and a comparison with the previous close would fold the deal day's own move into the side. Stage 0 reports how many block stock-days have B ≠ S.

**Client type.** The files carry a client name and no type. No client-type class is tested. The derived events file keeps the names, for reading only.

**Classes tested, direction-aligned:**

| Class | Events | Position |
| --- | --- | --- |
| BULK_BUY | directional BULK, side +1 | long |
| BULK_SELL | directional BULK, side −1 | short |
| BULK_ALL | BULK_BUY ∪ BULK_SELL | long for BUY, short for SELL |

**Filters, and no others:** the symbol maps to a NIFTY 100 member on the entry session and is in the cache; the entry session is in the sample; the entry bar and the horizon's exit bar exist at their exact times (§5). No price, volume, size or news filter.

## 5. Timing, fixed now

- **Entry session:** the first regular session after the deal date D (the disclosure comes after D's close).
- **Entry:** the **open of the 5-minute bar starting 09:20:00 IST** on the entry session, the first price after the opening five minutes. The 09:15 bar's open is the pre-open auction price and is not used. This is L35's and L36's after-hours entry.
- **Exits:** the close of the bar starting **09:30** (+15 minutes, at 09:35), **09:45** (+30, at 09:50) and **10:15** (+60, at 10:20). A missing entry or exit bar drops that event-horizon; nothing is shifted to a neighbouring bar.
- **Return:** r = side × (exit / entry − 1) × 10⁴ bp; **net = r − 16.63**.

## 6. Measurement

Per class × horizon:
- n events, number of distinct entry sessions (clusters), **mean net**, its standard error **clustered by entry session** (CR1: SE² = G/(G−1) · Σ_g (Σ_{i∈g} e_i)² / n², with e_i the deviation from the mean and G the number of sessions), t = mean / SE, and the two-sided p from Student's t with G − 1 degrees of freedom.
- Mean net in each **half**: `splits.halves` of the sample's session list; each event belongs to the half of its entry session.
- Share of events with net > 0; the **power line**: the smallest mean net detectable at t = 2 with the SE obtained (2 × SE), so a null reads "no effect larger than X".

**Description only** (not gated, not in the family, cannot promote anything):
- The aligned move on the deal day itself (D's first bar open → D's last cached bar close), the aligned gap (D's last cached bar close → the entry session's 09:15 open), and the aligned 09:15 open → 09:20 open: where any move happened, before the tradable entry.
- The aligned net return minus the same window's equal-weight mean return of the point-in-time NIFTY 100 members in the cache (market-adjusted).
- For BULK_ALL, MIXED and BLOCK: mean |r| against the same stock's mean |r| over sample sessions that are not the entry session of any of its events (a volatility read, as L35's baseline).

## 7. Family and gate, fixed now

**Family.** The class × horizon cells of §4 × §5 (at most 3 × 3 = 9) whose event count at stage 0 is **at least 60**. The counts need bar timestamps only, no price, so the family is fixed before any return exists. Cells below 60 are reported as underpowered, outside the family, and cannot pass. **Benjamini–Hochberg at q = 0.10** across the family, on the p-values of §6.

**Gate for a trial.** A cell clears only if, on the sample:
1. it has **at least 60 events** after the filters of §4 and §5;
2. its **mean net is above 0 with clustered t > 2**;
3. its mean net is **above 0 in both halves**;
4. it **survives BH at q = 0.10** across the family.

**If a cell clears:** a trial is pre-registered separately, in the family "disclosed large-deal flow", judged at N_family by the owner's bar of 2026-09-26 (`decision-2026-09-26-overnight-and-significance.md`), and confirmed on forward sessions after `splits.UNSEEN_AFTER` or on the 2026 window, at the owner's choice. Nothing is traded or wired before that.

**If none clears:** the finding is that **a bulk-deal disclosure does not move a NIFTY 100 stock past cost in the first hour of the next session**, and the bulk/block candidate is closed on record.

## 8. Stage 0 — before any price is read, each a halt if it fails

Stage 0 reads **no price**: its query selects only symbol and bar time from the cache. Output: `docs/research/data/l50_stage0.json`, and the derived NIFTY 100 events file `docs/research/data/l50_events.csv` (deal date, entry session, symbols, type, B, S, class, row count, client names with side, bar availability per horizon).

1. **Source.** Every month × type fetched: HTTP status, bytes and rows recorded. A fetch that fails after three attempts halts the stage. **Completeness:** for six deal dates drawn with a fixed seed (123) from the dates present, a one-day CSV query per type must return exactly the rows of the month file for that date; any mismatch halts.
2. **Boundaries.** No deal after 2025-12-22 in the parsed set; no bar after 2025-12-23 loaded (asserted from the loaded data, not assumed from the query).
3. **Symbols.** Deal symbols mapped through `symbolchange.csv`; stock-days on NIFTY 100 members (on the entry session) counted, and those lost because the member is not in the cache listed.
4. **Classes.** Stock-days per class: BULK_BUY, BULK_SELL, MIXED, BLOCK (and block stock-days with B ≠ S). For information only, the directional counts at thresholds 0 (any non-zero net) and 1/2 are listed next to the 1/3 of record.
5. **Bars.** Per class × horizon, events with both the entry and the exit bar (timestamps only). **The family of §7 is fixed here.**
6. **Void rule.** If BULK_ALL has fewer than 60 events at every horizon, the family is empty: **stage 0 halts and L50 is recorded VOID**, with no price read. That is a complete result.
7. **Halves and adjustment.** Events per half. Kite back-adjusts history as of the fetch date (#108); the stage records the cache's fetch runs. The gated returns lie inside one session and are unaffected by a constant adjustment factor; the descriptive lines that cross sessions (§6) exclude an event if a fetch-run boundary falls between D and its entry session.

## 9. One run, and the review checkpoint

Stage 0 is committed and pushed, then **stops for an independent review**. The measurement pass runs **once**, only after that review and on the main session's instruction, and only outside 08:30–15:45 IST (the engine's hours on the Mac). A re-run is allowed only for a crash before any statistic was printed, or a declared bug with both runs recorded. No parameter of §3–§7 changes after stage 0's counts are seen, except by a dated amendment written before the measurement pass; none may change after a return is seen.

## 10. Accounting

Research look **L50**. Trials remain **202**. The 2026 held-out window is not read. If a cell clears, the trial that follows has its own pre-registration and its own number.
