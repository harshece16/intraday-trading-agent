# Pre-registration: trial 207, futures OI build-up held five sessions

**Written 2026-11-07, before any F&O history is in the repo and before any
code exists.** Issue #320. The owner sent a batch of trading reels and asked
that every new idea be tested. One reel (DfFrvCWTijy) sells an "OI build-up"
scanner: a stock whose price rose while its futures open interest rose is in
"long build-up" (new longs), so buy it. The reel shows no evidence, and its top
comment reads "Everything is fake". The idea is still standard F&O lore in India
and has never been tested in this project. This trial tests it once, long only,
at the delivery costs this project would actually pay.

**Family and bar.** A new family, **"futures positioning"**, with **N = 2 and
t ≥ 2.24** (two-sided Bonferroni at 5% across 2). This trial spends the
**first** slot. The second is kept for one later hypothesis, pre-registered
first (see "Not done here"). The trial counts toward the strategy-trial total
in `trials.md`. If the reviewer rules that the signal is mostly one-day price
direction, and so belongs to the momentum family (N = 11, t ≥ 2.865), the
mechanism gate below handles that. A pass needs OI to add information beyond
price.

## Why this exists: the prior

- **For:** Hong and Yogo (NBER w16712) find that growth in aggregate futures
  open interest predicts monthly returns. The evidence is strong for
  commodities and weaker for bonds and stocks. NSE working paper 81 finds that
  stock-option OI helps explain the underlying's price. Neither paper tests the
  four price/OI states on single-stock futures, and neither nets out costs.
- **Against:** a large share of Indian stock-futures OI is cash–futures
  arbitrage. Arbitrage funds hold the stock and short the future, and that
  position takes no view on direction. A rise in OI on an up day can be new
  arbitrage as easily as new speculative longs. The states are published
  free every evening by brokers and NSE, so any edge in them is crowded. A
  quick search (2026-11-07) found no net-of-cost result for this signal on
  any market.
- **Honest prior that this passes: low, about one in ten.** A sign-only filter
  that selects about a quarter of F&O stocks each day has to beat about
  42 bp of round-trip cost plus the floor (below). A fail closes OI build-up
  as a stock signal for this project.

## What had been seen

- One probe from sahab-pc on 2026-11-07 fetched two files: the F&O bhavcopy
  of 2015-01-01 (old format, 435 `FUTSTK` rows) and of 2025-01-02 (UDiFF,
  653 `STF` rows). Only the column names and the instrument counts were read.
  **No OI change and no return was computed.** The files stay on the PC
  probe folder and are not data for this trial.
- Cash prices 2009–2025 have been read many times by earlier trials. The 2026
  held-out window has not been read by any trial, but its prices were seen at
  index level (`trials.md`, 2026-10-01 note). Disclosed as the rule requires.
- One-day price direction at a five-session hold has not been tested here as
  a signal on its own. The Ranker (trials 121–122) used 1-month reversal.
- No futures OI of any kind has been used in this project.

## Rules that do not change

- **Prices and costs** are trial 126's: NSE bhavcopy chains from
  `nse_prices.load`, total-return adjusted closes for returns, the as-printed
  price for share counts, `slow_momentum.buy_cost` / `sell_cost` (STT, stamp,
  exchange, SEBI, GST, 5 bp slippage) and ₹15.34 DP per sell.
- **Held-out:** no F&O file dated 2026-01-01 or later is fetched before a
  pass. The cash loader drops 2026 sessions unless the held-out check is asked
  for.

## Data

- **Source.** NSE F&O bhavcopy, every session from 2009-01-01 to 2025-12-31.
  Old format `fo{DD}{MON}{YYYY}bhav.csv.zip` (`INSTRUMENT = FUTSTK`,
  `SYMBOL`, `EXPIRY_DT`, `OPEN_INT`) up to the switch in July 2024; UDiFF
  `BhavCopy_NSE_FO_0_0_0_{YYYYMMDD}_F_0000.csv.zip` (`FinInstrmTp = STF`,
  `TckrSymb`, `XpryDt`, `OpnIntrst`) after it.
- **Where.** Fetched on sahab-pc into `/mnt/data/trader-sahab/fo_bhav/`, at
  about 1.6 GB of zips (the Mac is on an away network, rule 23). One
  aggregate is made there and moved to the Mac:
  `backend/data/fo_oi/fo_oi_daily.csv.gz` (gitignored). It holds date,
  symbol, total stock-futures OI in shares across all expiries, the number
  of live expiries, and whether any stock future expires that day.
- **Symbols** map to cash chains through `symbolchange.csv`, as the cash
  loader does. An unmatched symbol-day is dropped and counted.

## The trial

**Signal day t.** For each stock with stock futures on t and on the previous
F&O session:

- `OI_t` = the sum of open interest in shares over all its stock-futures
  expiries on t.
- `dOI = OI_t / OI_{t−1} − 1`.
- `r_t` = the cash close-to-close return on t, from total-return adjusted
  closes.
- State on t:

  | State | `r_t` | `dOI` |
  | --- | --- | --- |
  | **LONG_BUILDUP** | > 0 | > 0 |
  | SHORT_COVERING | > 0 | < 0 |
  | SHORT_BUILDUP | < 0 | > 0 |
  | LONG_UNWINDING | < 0 | < 0 |

  A zero in either sign gives no state. These are the reel's definitions and
  the usual market ones. **No threshold on either size is used.**

**Exclusions** (each counted):

1. t is a stock-futures expiry day, or the first F&O session after one. The
   expiring series leaves the sum, and roll-over moves OI between expiries.
2. The stock's first day with futures (it has no `OI_{t−1}`).
3. A split, bonus or consolidation with ex-date t on the stock's chain (from
   `nse_prices` events). OI is counted in shares, so these change it
   mechanically.
4. No cash close on t or on the session before.

**Universe on t.** Every stock with a state on t after the exclusions. F&O
membership is taken from that day's file, so stocks that left the F&O list
stay in the history and there is no survivor bias.

**Events.** Every LONG_BUILDUP stock-day. If the same stock already has an
open event (its exit not yet reached), the new one is dropped and counted.

**Entry.** The open of the first cash session after t. The bhavcopy is
published after the close, so t's states are known that evening. No trade on
the entry session → skipped and counted.

**Exit.** The close of the 4th session after the entry session (five sessions
held, entry day included). No trade that day → the last close on or before it.

**Size.** One ticket of **₹50,000** per event, whole shares at the printed
open; zero shares → skipped and counted.

**Costs.** `buy_cost` and `sell_cost` plus **5 bp a side** more slippage, so
**10 bp a side** in all, as in trial 206, plus the DP charge. Round trip
≈ 42 bp + ₹15.34.

**Benchmark.** The equal-weighted universe of signal day t, from the same
entry open to the same exit close, gross. **Net excess = net event return −
benchmark return.**

**Samples.** Signal days from 2009-01-01 whose exit session falls on or before
2025-12-31. Halves: S1 is signal days to **2017-06-30**, S2 is from
**2017-07-01**. Last three years: from **2023-01-01**. Held-out: 2026.

**Statistic.** For each entry session with at least one event, the mean net
excess of its events. That gives one series of session means. The t is the
**Newey–West t with 4 lags** (`pead_stage_a.nw_t`), because holds that
start on consecutive sessions overlap for four of their five sessions. A
plain or session-clustered t would overstate. The Deflated Sharpe uses the
same series at N = 2.

**Mechanism series.** SHORT_COVERING events are built the same way (their
own overlap rule, the same entry, exit, costs and benchmark). For every entry
session that has both, the difference is the LONG_BUILDUP session mean minus
the SHORT_COVERING session mean. Both states had a rising price on t. The
difference measures what the direction of OI adds beyond the price.

## Power

A five-session excess return of one F&O stock has an SD of about 5%. With
about 20 events per session and an average pairwise correlation of excess
returns near 0.1, a session mean has an SD of about 1.9%. About 3,800 sessions
qualify after the expiry exclusions. The overlap leaves about 760 independent
five-session blocks. The bar of 2.24 then detects a true net mean of about
**15 bp** half the time, so the +25 bp floor binds before the t does. To
reach the floor net, the gross excess has to be about **67 bp per five
sessions** for a filter that takes a quarter of the universe. These are
assumptions, not reads. Stage 0 prints the real counts.

## Stage 0: data gate (no return is read)

Printed and saved to `docs/research/data/trial207_stage0.json` before the
trial runs:

1. **Completeness.** Every cash session of 2009–2025 in `bhav_daily` has an
   F&O file. Missing files are listed. More than **1%** missing stops the
   run until they are re-fetched; this is not a trial failure.
2. **Parse.** Every required column maps in both formats. Stock-futures rows
   per file, stocks per day, and expiries per day are listed by month.
3. **Expiries.** Each calendar month has exactly one stock-futures expiry day.
   Months with none or with two are listed, and the exclusion uses the
   detected days.
4. **Symbols.** At least **95%** of F&O symbol-days map to a cash chain. If
   fewer do, the mapping is fixed by a dated amendment to this file before
   any return is read.
5. **Counts.** State counts per month, and events dropped at each rule.
6. **Stop rule.** Fewer than **100** LONG_BUILDUP events, or fewer than
   **1,000** entry sessions with an event, and the trial is not run. The reason
   is recorded in `trials.md` and the slot stays unspent.

## Review before the run

An independent reviewer reads this file and the trial script, and approves
them before the run, as `prereg-us-momentum.md` requires.

## Pass rule (trial 207): all seven required

1. Mean session net excess **> 0** with Newey–West **t ≥ 2.24**.
2. Deflated Sharpe ≥ **0.95 at N = 2** (`evaluation.deflated_sharpe_ratio`
   on the session series).
3. Mean net excess **> 0 in both halves**.
4. Mean net excess **> 0 over the last three years**.
5. Mean event net excess ≥ **+25 bp**, the economic floor.
6. **≥ 100 events.**
7. **Mechanism:** the mean LONG_BUILDUP − SHORT_COVERING difference is
   **> 0** with Newey–West **t ≥ 1.65** (one-sided 5%).

## What a pass allows

A held-out **sign check**, run once: fetch the 2026 F&O files through the last
complete month and run the same rules. If it is positive, a **paper book** of
its own beside the Jev books: 20 slots of ₹50,000, events taken in symbol
order each evening, and skipped when the book is full. It never mixes into the
momentum book. A pass is a stock signal, not an options strategy. Buying
calls on it would need its own pre-registration on option prices. Real money
is a separate owner decision after paper, and the momentum book's go-live list
comes first.

## Falsification branches, written now

| Result | Meaning | Action |
| --- | --- | --- |
| Stage 0 stops | Missing files, an unmapped format or too few events | Fix the data or record "not run"; no change to the state rules to raise N |
| Fail on t or DSR, mean > 0 | Not distinguishable from luck at this bar | FAIL; line closed |
| Fail on a half or the last three years | Decayed, or never stable | FAIL; closed |
| Fail on the 25 bp floor only | Real but worthless after delivery costs | FAIL; closed for cash delivery |
| Pass 1–6, fail 7 | The gain comes from the up day, not from OI | FAIL for this family. A price-only version belongs to the momentum family and needs its own pre-registration at t ≥ 2.865 |
| Pass | OI build-up predicts a five-session excess net of costs | Held-out sign check, then paper |

No hold length, threshold, universe, entry bar or state definition is changed
after a return is read. A crash before a statistic is printed may be fixed and
re-run, with both runs recorded.

## Also reported (information, not gates)

Gross and net means, the median, the SD, the win rate, per-year means, the
share of events in each month, and the SHORT_COVERING series on its own,
because the mechanism gate needs it.

## Not done here

- **No short-side states.** SHORT_BUILDUP and LONG_UNWINDING are not
  computed as outcomes. Their natural use is buying puts, which needs option
  prices this trial does not load. That is the most likely use of the
  family's second slot, pre-registered first.
- **No size thresholds** on `dOI` or `r_t`, no top-quintile cut, no hold
  length other than five sessions, no intraday OI, and no index futures.
  Each would be a new hypothesis, and computing one now would make a later
  pre-registration of it post hoc.
- **No futures as the vehicle.** The README limits F&O to buying calls and
  puts, so the trial uses cash delivery, the instrument this project can
  hold.
