# Pre-registration: trials 208 and 209, selling NIFTY option premium with defined risk

**Written 2026-11-22, before any option price is in the repo and before any
code exists.** Issue #327. The owner asked for a better F&O (put/call)
strategy and a running flow. This project has already refuted option buying
and option-chain positioning (PCR, OI, max pain) from the literature, and the
engine's own F&O path has never traded (`FNO["enabled"] = False`). The one
option idea never tested here is the other side: **selling** premium. It was
left alone on 2026-09-26 for want of option price history
(`prediction-engine-sweep-2026-09-26.md`: "would need option-chain fills data
first"). The F&O bhavcopy archive fetched for trial 207 holds a daily row for
every NIFTY and BANKNIFTY option, 2009–2025, so it can now be tested once, at
the costs this project would pay today.

**Family and bar.** A new family, **"index option premium selling"**: selling
index option premium in any structure and holding it to collect the gap
between the move the options price in and the move that happens.
**N = 2 and t ≥ 2.24** (two-sided Bonferroni at 5% across 2), plus a Deflated
Sharpe Ratio ≥ 0.95 at N = 2. **This document spends both slots**: trial 208
(iron condor) and trial 209 (hedged straddle). Each arm is judged on its own
against that bar. No trial or look on this project's own data has tested the
mechanism before; the two earlier mentions are literature sweeps. A third
configuration later (other strikes, stops, entry filters, other days) raises N
to 3 (t ≥ 2.39) and needs its own pre-registration. This is not the second
slot of the "futures positioning" family that trial 207 kept for put buys.

## Why this exists: the prior

- **For:** index options are priced for more movement than arrives, on
  average, in most markets studied (Coval and Shumway 2001; Bakshi and Kapadia
  2003; Carr and Wu 2009). For India the sweep of 2026-09-26 recorded implied
  minus realised volatility at +1.96 vol points (t 3.76). Buying a further
  option on each side caps the loss, which makes the trade possible on a
  small account and bounds the tail that ruins naked sellers.
- **Against:** Pillai (SSRN, NIFTY monthly 2015–2025, with STT, brokerage and
  slippage) finds the ATM straddle, the put-write and the delta-hedged
  straddle **all negative net**. STT on option sales has risen from 0.0625%
  to 0.1% to 0.15% of premium, and today's rate is charged on the whole
  history here. The bought wings are themselves overpriced options, so a
  hedged seller hands back part of what it collects. Weekly expiries are the
  most crowded trade in the Indian market. A day's closing price is not a
  price anyone was filled at. The base rate in this project is one pass in
  205 trials.
- **Honest prior that either arm passes: low, about one in six.** A fail
  closes premium selling for this project.

## What had been seen

- Probes on sahab-pc on 2026-11-22, on the archive only:
  the column names of both file formats; the list of NIFTY option expiries
  listed on eight dates (2009-01-29, 2016-06-01, 2019-02-11, 2019-02-14,
  2021-06-01, 2024-07-04, 2025-09-02, 2025-12-23) with row counts; and the
  settlement columns on three expiry days. On 2021-06-03 every expiring NIFTY
  option row carries `SETTLE_PR` 15690.35, the index's final value, and two
  expiring rows were read in full (15000 CE close 687.1, 14000 CE close
  1689.7, both deep in the money on their last day); that day's three futures
  closes were read (15712.4, 15760.55, 15805.6). On 2015-06-25 the expiring
  options show `SETTLE_PR` 0 and the expiring future settles at 8398 (close
  8397.1). On 2025-12-30 the UDiFF rows carry 25938.85 as the underlying and
  settlement value and a lot of 75. One futures row of 2009-01-02 was used to
  infer a lot of 50.
- **No premium of any strike on any entry day was read. No straddle price,
  credit, payoff or P&L was computed.**
- The index's path 2009–2025 is known (it rose about ninefold; March 2020
  fell hard) and its prices have been read by many earlier trials. That
  knowledge cannot be unseen. It is why both trades are neutral at entry and
  why the put side and the call side are reported apart (see the
  falsification branches).
- The 2026 held-out window: `backend/data/nse_indices/` holds only 2026 files
  and was listed by name, not opened. Its prices were seen at index level by
  the 2026-10-01 note in `trials.md`. No 2026 option row has been read.

## Rules that do not change

- **Costs** are today's tariff applied to all 17 years:
  `costs.leg_cost` with `costs.FNO_OPTION_COSTS` (₹20 an order, STT 0.15% of
  premium on sales, NSE 0.03553%, SEBI, IPFT, stamp 0.003% on buys, GST 18%),
  plus the exercise STT of 0.15% of intrinsic value on a bought option that
  expires in the money (in force from 2026-04-01;
  [Zerodha](https://support.zerodha.com/category/account-opening/resident-individual/ri-charges/articles/how-is-the-securities-transaction-tax-stt-calculated)).
- **Held-out:** no row dated 2026-01-01 or later is read. The extract drops
  them and the last cycle expires on or before 2025-12-31.
- **One run per arm.** Each is logged with `evaluation.log_trial`.

## Data

- **Source.** The NSE F&O bhavcopy archive already on sahab-pc at
  `/mnt/data/trader-sahab/fo_bhav/` (4,211 sessions, 2009-01-01 to
  2025-12-31, fetched for trial 207 on the owner's explicit choice). **Nothing
  new is fetched.** Old format: `INSTRUMENT` `OPTIDX`/`FUTIDX`, `STRIKE_PR`,
  `OPTION_TYP`, `CLOSE`, `SETTLE_PR`, `CONTRACTS`. UDiFF (from 2024-07-08):
  `FinInstrmTp` `IDO`/`IDF`, `StrkPric`, `OptnTp`, `ClsPric`, `SttlmPric`,
  `UndrlygPric`, `TtlTradgVol`, `NewBrdLotQty`.
- **Extract.** `backend/research/fo_options_aggregate.py` (stdlib, run on the
  PC as one copied file) writes every NIFTY and BANKNIFTY index-option and
  index-future row **on that symbol's expiry days only** (options with an
  expiry within 45 days) to one gzip CSV, with a sidecar listing bad files
  and every session date. It is a few MB, is copied to
  `backend/data/fo_oi/` (git-ignored) and is not committed.
- **Calendar.** Trial 207's stage 0 found four cash sessions with no F&O file
  (2010-05-16, 2012-11-11, 2013-10-09, 2021-03-30). Stage 0 here checks that
  none is an entry or expiry day.

## The two trades

Both are built the same way and differ only in the strikes sold.

- **Expiry day.** A session on which a NIFTY option series expires. A listed
  expiry that is a market holiday (no cash session and no F&O file) expired
  on the last F&O session before it (trial 207, amendment 2). A listed expiry
  that is a cash session with no F&O file is a missing file: cycles that
  touch it are dropped and counted.
- **Cycle.** Start at the first expiry day on or after 2009-01-01. At its
  close, trade the **front series**: the NIFTY option series with the nearest
  expiry after that day, as listed in that day's file. Hold to that expiry.
  The next cycle starts at the close of that expiry day, and so on, so cycles
  never overlap. The chain of dates does not depend on whether a trade could
  be built. The front series is monthly until weekly options are listed
  (February 2019; the files decide the date) and weekly after. A cycle whose
  expiry falls in 2026 is not used.
- **Liquid contract.** At least 100 contracts traded that day (in UDiFF,
  `TtlTradgVol` expressed in contracts; stage 0 settles the unit from the
  turnover column before any price is used).
- **Prices.** The file's closing price (`CLOSE` / `ClsPric`) of each leg on
  the entry day.
- **Forward and implied move.** K0 is the front-series strike where the call
  and the put are both liquid and |C − P| is smallest (tie: the lower
  strike). The forward is **F = K0 + C(K0) − P(K0)** and the straddle is
  **S0 = C(K0) + P(K0)**. Under a normal model one standard deviation of the
  move to expiry is 1.25 × S0. No volatility model, rate or dividend is used.
- **Trial 208, iron condor.** Sell the call at the lowest liquid strike at or
  above F + 1.25·S0 and the put at the highest liquid strike at or below
  F − 1.25·S0 (about one standard deviation out). Buy the call at the lowest
  liquid strike at or above F + 1.875·S0 and above the sold call, and the put
  at the highest liquid strike at or below F − 1.875·S0 and below the sold
  put (about one and a half).
- **Trial 209, hedged straddle.** Sell the call and the put at K0. Buy the
  call at the lowest liquid strike at or above F + 1.25·S0 and the put at the
  highest liquid strike at or below F − 1.25·S0.
- **Skips, each counted by reason.** No K0; a leg not found, or found more
  than 0.75·S0 beyond its threshold (a hole in the chain); a bought option
  priced at or above the option sold on its side, a credit ≤ 0 or a maximum
  loss ≤ 0 (a bad quote); no final settlement price.
- **Exit.** None is traded. Every leg settles at its intrinsic value against
  the **final settlement price** of the expiry day: the UDiFF underlying
  value; before UDiFF, the settle price of the future expiring that day, else
  the one value carried by every expiring option row when it is above zero.
- **Size.** One lot. The unit is **R = net P&L ÷ maximum loss**, where
  maximum loss = the wider of the two spreads − the credit received, before
  costs. A book sized to lose the same rupees at worst each cycle earns the
  mean R.
- **Costs.** Each cycle is costed as today's contract at today's index
  level: prices are scaled by 25,938.85 ÷ F (the NIFTY settlement of
  2025-12-30) and one lot is 65 (the lot since January 2026), the rupee cost
  comes from `leg_cost`, and it is scaled back to points. Four entry orders.
  **Slippage** on each entry leg is the largest of 1% of the premium (half of
  the 2% spread limit in `FNO["max_spread_pct_of_premium"]`), 0.25 point at
  today's index level, and one tick (0.05). At expiry every leg that finishes
  in the money is costed as one more order at its intrinsic value: a bought
  leg as a sale (which charges the 0.15% exercise STT), a sold leg as a
  purchase. Charging brokerage there is the conservative reading. Results are
  reported at 1×, 2× and 3× of all costs.
- **Benchmark.** Zero. Margin earns nothing in this accounting.
- **Samples.** Full: 2009–2025. Halves by entry date: S1 to 2017-06-30, S2
  from 2017-07-01 (as trial 207). Last three years: entries from 2023-01-01.
  Short cycles: expiry within 10 calendar days of entry, the form a running
  book would trade today.
- **Statistic.** One net R per cycle, in entry order. t is the smaller in
  size of the plain one-sample t and the Newey–West t with 4 lags
  (`pead_stage_a.nw_t`). DSR from `evaluation.deflated_sharpe_ratio(xs, 2)`,
  which penalises the negative skew that short options carry.
- **Cross-section.** BANKNIFTY under the same rules on its own expiry days
  (lot 30, scaled to its own 2025-12-30 value). It is a sign check, not a
  third arm.
- **Mechanism series (reported, not judged).** The share of cycles that
  finish beyond F ± 1.25·S0 and beyond F ± 1.875·S0, against the 31.7% and
  13.4% a correctly priced normal move would give (one and one and a half
  standard deviations: 2·(1 − Φ(1)) and 2·(1 − Φ(1.5))); and the P&L of the
  put side and of the call side.

## Power

The front series gives about 120 monthly and 355 weekly cycles, about 475 in
all. At that count t ≥ 2.24 needs a mean net R of 0.103 standard deviations.
The standard deviation of R is not known before the run. Arithmetic on a
normal model, not on data: the condor's credit is about 0.28 of its maximum
loss, so it wins about +0.28R when the index stays inside the sold strikes
and loses up to −1R outside the bought ones; that shape has a standard
deviation near 0.4, so the bar is near **+0.04R a cycle net**. Costs are about
0.02–0.03R a cycle at today's index level. If realised volatility runs at 85%
of implied, the expected gross is about +0.09R and the expected t about 3. At
95% of implied the expected net is about zero. Fat tails and the extra price
of the put wing push both figures down. So the trial has power against a
premium of the size the literature reports, and none against a small one.

## Stage 0: data gate (no P&L is read)

Saved to `docs/research/data/trial208_stage0.json`. It reads entry prices only
to build strikes and reads settlement prices only to check their sources. It
never puts the two together: no payoff, credit-against-outcome, win rate or R
is computed.

1. **Files.** Sessions parsed in each format; bad files listed. No bad or
   missing file is an entry or expiry day of a cycle that is kept.
2. **Expiry days.** The list from the files, the moved ones named, cycles per
   year, the date of the first weekly cycle.
3. **Final settlement price.** Present for at least 98% of cycle expiries.
   Where two sources exist on one day they agree within 0.05% on at least 99%
   of such days. Every value is within 1% of the nearest future's close that
   day (a wrong-column check).
4. **Entry quotes.** The forward read at the next liquid strike on each side
   of K0 agrees with F: the median gap is at most 0.1% of F and at least 95%
   of cycles are within 0.3% (stale or unsynchronised closes fail this).
5. **Volume unit** in UDiFF settled from the turnover column.
6. **Counts.** Cycles buildable per arm and per symbol; skips by reason.

**Stop rule.** If check 3 or 4 fails, or NIFTY has fewer than 100 buildable
cycles in an arm, that arm is not run and the reason is recorded.

## Review before the run

A reviewer with no part in writing this reads the pre-registration and the
script before the run. Each objection is fixed by a dated amendment below
before any P&L is computed, or recorded with the reason it was not.

## Pass rule: all eight required, for each arm on its own

1. **Full sample:** mean net R > 0 and t ≥ 2.24.
2. **Deflated Sharpe Ratio** ≥ 0.95 at N = 2.
3. **Both halves:** mean net R > 0 in S1 and in S2.
4. **Last three years:** mean net R > 0 for entries from 2023-01-01.
5. **Short cycles:** mean net R > 0.
6. **Costs:** mean net R > 0 at 2× costs.
7. **Sample:** at least 100 cycles.
8. **Cross-section:** mean net R > 0 on BANKNIFTY.

## What a pass allows

Nothing by itself (decision of 2026-09-26, safeguard 3). In order:

1. **A held-out check on 2026, run once.** The same rules on every cycle that
   expires in 2026. It confirms if the 2026 mean net R is above zero and no
   lower than the selection mean minus two standard errors (selection
   standard deviation ÷ √ of the 2026 cycle count). It needs the 2026 F&O
   files. NSE's Terms of Use forbid scripted collection, so that fetch waits
   on the owner's explicit word, as it did for trial 207.
2. **Then a paper book**, paper only: the confirmed arm traded on live Kite
   quotes near the close of each NIFTY expiry day (sold at the bid, bought at
   the ask), one lot, held to expiry, with a forward band written in its own
   pre-registration before the first paper trade and an automatic switch-off
   on a breach.
3. **Real money** is a separate decision by the owner, never automatic.

**A fail** sends nothing to paper and spends no held-out window (safeguard
5). `FNO["enabled"]` stays off. The family is closed at N = 2.

## Falsification branches, written now

| Result | Meaning | Action |
| --- | --- | --- |
| All eight gates met | Selling this premium paid net of today's costs, in both eras and on both indices | Pass: held-out check next |
| Mean above zero, t below 2.24 | Not told apart from zero at the family bar | FAIL; nothing to paper |
| Gross above zero, net at or below zero, or positive at 1× and not at 2× | The premium exists and costs take it (Pillai's result) | FAIL; record the break-even cost |
| Put side positive, call side negative, total not significant | The index rose; that is drift, not a volatility premium | FAIL |
| Positive in S1, negative in S2 or in short cycles | The premium was competed away once weeklies drew a crowd | FAIL |
| NIFTY positive, BANKNIFTY negative | No confirmation on a second index | FAIL |
| Passes with a negative call side | Stays a pass as registered; a put-spread-only version would be a new hypothesis at N = 3 | Pass as written |
| More cycles finish outside the sold strikes than the normal share | The options were priced too cheaply, not too dearly | FAIL explained |

## Also reported (information, not gates)

Win rate, mean win and mean loss, the five worst cycles, the longest losing
run and the deepest drawdown in R; mean R by year and by cycle length
(monthly, weekly); credit as a share of maximum loss; costs as a share of
credit; the mean P&L in basis points of the forward; cycles skipped by reason;
BANKNIFTY in full.

## Not done here

No stop-loss, adjustment, early exit or intraday management. No delta
hedging. No entry filter (VIX level, event days, trend). No strike or day
search: the two arms above are the only configurations computed. No naked
selling. No stock options. No 2026 row. No order, live or paper.

## Amendments

None yet.
