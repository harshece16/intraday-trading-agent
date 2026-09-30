# Pre-registration — do the scanner audit's four intraday features, or the overnight-gap reversal, rank the next intraday move past cost? (research look L49; a trial only if one clears)

**Written 2026-09-30 by 20:15 IST (its commit), before any L49 code exists and before any of the five features below has been computed on project data.** Sources: `scanner-audit-2026-09-28.md` §6 item 3, which asked for "one pre-registered look on the four features never measured here: gap, time-of-day relative volume, VWAP distance and sector strength ... against the 16.6 bp round trip. One run, both halves, corrected for four tests", and `data/predictive-tools-sweep/predictive_tools_C.md` candidate 1, which asked for "one measurement look at the 09:45 decision time only: feature = prev bhavcopy close → 09:45 close; 60-min target; partial IC given m60". The owner asked on 2026-09-30 for every open research item to be completed. The harness is L40's, unchanged.

**What it is not.** Not a strategy, not a backtest, not a trial. No order path, no config, no gate and no scanner rule changes. Nothing here reaches the engine.

## 0. What had been seen when this was written

Results that touch these features, all on the selection sample or earlier:

| Look or trial | What it measured | Result |
| --- | --- | --- |
| L40 | Kronos forecast in this harness, 78 sessions, 43,362 stock-times | FAIL; spreads +0.27 / +0.51 / +1.61 bp against 33.26 bp |
| L46 | Six zero-shot forecasting models, same harness | FAIL, 18 of 18; spreads −2.3 to +0.5 bp |
| L47 | LightGBM on Alpha158, same harness | FAIL; spreads +0.11 / +0.03 / +0.51 bp. **Its positive control: the target used as its own feature earns 1.7×, 2.4× and 3.3× the bar at 15, 30 and 60 minutes.** A feature here must capture more than about 59%, 42% or 30% of perfect foresight's spread to pass |
| L48 | Whole-market breadth and overnight intermarket moves against the NIFTY 100 session | 0 of 8 survive BH. Index level, not a per-stock gap |
| L31 (3b stage 1a) | Cross-sectional rank of the **09:15 open → 09:45 close** return against 09:50 → 15:10, 316 sessions from 2024-09-23 to 2026-01-01 (this look's sample is inside that span) | Top-minus-bottom quintile **−1.60 bp, t −0.48**. The open-to-09:45 part of feature F5 below, against a longer target, with no reversal worth anything |
| L32 (3b stage 1b) | sign(**previous close → 09:45 close**), market level, against 14:40 → 15:10; per-stock own signal reported as descriptive | +0.70 bp, t +0.61; per stock −0.38 bp. F5's window, as a sign, against a different target |
| L36 | Results-day gaps from the filed profit change | Overnight gap +82.7 bp aligned (t 4.78); after the open +5.9 bp at 30 minutes, zero by the close |
| L23–L28 (3c) | Overnight vs intraday return by volatility quintile | Volatile names earn overnight and give it back intraday; the tradable intraday spread is 0.24× the two-leg bar |
| Trial 35 (3a) | Opening-range breakout on the 20 names with the highest 09:15–09:30 relative volume (against 14 prior sessions) | FAIL, −12.09 bp a session; the relative-volume filter added nothing (+1.61 bp gross with it, +2.96 without) |
| Trials 93–116 | VWAP breakout on volume ≥ 2× (family VB), three timeframes | 24 of 24 FAIL |
| L8 | 10-day relative strength against the NIFTY, daily | IC −0.009, t −1.24 |
| Sweep C, candidate 1 | An outside repository's cross-sectional overnight-gap reversal, 10:00 → 15:20 | Decile spread −24.3 bp pooled 2018–25, but −11.0 (2024) and −9.6 bp (2025), −3.0 bp on continuously listed names. The sweep's expectation: FAIL here |

The scanner audit's own expectation was that none of the four clears. So is this one's: **FAIL on all thirteen tests.**

Data looked at while writing this, none of it a price, volume or return:

- The candle cache's table of contents: one interval (5-minute), 100 symbols, 2024-09-20 to 2026-09-18, **one fetch run** (2026-09-20, 1,302 spans).
- `backend/data/nifty100.csv`: its 100 symbols are exactly the cache's 100; its NSE industry labels give 17 industries, two of them with one member (Telecommunication: BHARTIARTL; Construction: LT).
- `nifty100_membership.csv` rows for ENRIN, ETERNAL, HYUNDAI, JIOFIN, LTM, TATACAP, TMCV, TMPV.
- NSE's corporate-actions file for 2025 (`ca_2025.csv`): ex-dates 2025-01-01 to 2025-12-26, and the rows for ITC, TMPV (a dividend in June, a **demerger on 2025-10-14**), HINDZINC, VEDL and SIEMENS.
- NSE's symbol-change file: ZOMATO → ETERNAL (2025-04-09), TATAMOTORS → TMPV (2025-10-24), LTIM → LTM (2026-02-27).
- The list of 2025 bhavcopy files (249) and their column names; the header line of one full bhavcopy.
- The scanner's code for gap, relative volume, VWAP and sector rank (`scanner.py` `intraday_metrics`, `intraday_score`, the sector ranking; `indicators.session_vwap`).

## 1. Hypotheses

Each feature is a number known at decision time *t*, oriented so that **a higher value predicts a higher signed return**. The sign is fixed here; a significant result of the opposite sign is reported and earns nothing (a new look would be needed for it).

| # | Feature | Source | Sign, and why |
| --- | --- | --- | --- |
| F1 | `gap` — the day's opening gap | audit | **+, continuation.** The scanner scores a gap of 0.3% up to its cap, and every "breakaway" gap, in the gap's direction |
| F2 | `rvol` — time-of-day relative volume | audit | **+.** The scanner gives relative volume no direction (the same points to a long and a short). A ranking of the signed move needs one; the published directional claim for volume alone is the high-volume return premium (Gervais, Kaniel and Mingelgrin, 2001): higher volume, higher later return |
| F3 | `vwap_dist` — distance from session VWAP | audit | **+, continuation.** The scanner scores "above VWAP" for a long |
| F4 | `sector` — the stock's sector's move today | audit | **+, continuation.** The scanner scores a top-three sector for a long |
| F5 | `gap_reversal` — previous official close → 09:45 close, negated | sweep C | **+ on the negated move, i.e. reversal.** The outside repository's H2 |

F1 and F5 are close to opposite bets at 09:45 (F5 contains F1's gap). Both are tested because two sources proposed them with opposite signs; at most one can pass.

## 2. Data, fixed

- **Bars:** the Kite 5-minute cache, the same bars L40 used, opened **read-only** (SQLite `mode=ro`) from the main checkout's `backend/data/kite_history.db`. The query itself stops before 2026-01-02 00:00 IST, and the loader asserts that the latest bar it read is dated 2025. `kite_history` is not imported (importing it imports `config`, which touches credential files).
- **NSE bhavcopies:** the 2025 files in `backend/data/bhav_daily/` (the same files the repaired panel of #175 is built from), read raw: symbol, series EQ, open, close and **last price** of each day. No file dated 2026-01-02 or later is opened.
- **Corporate actions:** `backend/data/corp_actions/ca_2025.csv` only. `ca_2026.csv` is not opened.
- **Symbols:** bhavcopy and corporate-action symbols are mapped to the cache's names through NSE's symbol-change file (`nse_prices.symbol_chains`, `canonical`), so TATAMOTORS rows land on TMPV and LTIM rows on LTM.
- **Industries:** NSE's own label from `backend/data/nifty100.csv`, copied into the repository as `backend/research/data/l49_industries.csv` in the code commit. The labels are as of the file's last refresh (September 2026), not point-in-time; an industry label rarely changes, and this is recorded as a caveat, not corrected.
- **Universe and sample:** L40's, exactly (§5).
- **The 2026 window is not read.**

## 3. The previous close: which one, and why

The sources name the **previous bhavcopy close**, NSE's official closing price (the volume-weighted price of the last 30 minutes). That is also the previous close the scanner and a live quote show. It is used here.

It cannot be taken from the repaired panel as it stands. The panel is total-return adjusted to its own end, with NSE's 2025 corporate actions; the Kite cache is adjusted, as of its fetch on 2026-09-20, for the dividends and splits Kite applies (#108). A price from one against a price from the other differs by the ratio of two adjustment factors, which is a dividend yield's worth (tens to hundreds of basis points) and differs from stock to stock: the size of the gaps being ranked. Kite's own last bar is on the right basis but is the last trade, not the official close.

So the official close is put on the cache's basis by a **same-day ratio**, which no adjustment can disturb:

    pc(s, d) = K_last(s, d⁻) × CLOSE(s, d⁻) / LAST(s, d⁻)

where `d⁻` is the market session before `d` (the previous date in the calendar of all cached sessions, which includes the Muhurat session of 2025-10-21), `K_last` is the close of the stock's last cached bar on `d⁻`, and `CLOSE` and `LAST` are that day's bhavcopy close and last price. Stage 0 check 4 tests the assumption this rests on, that Kite's last bar and NSE's last price are the same trade up to Kite's adjustment factor.

`pc(s, d)` is **undefined**, and every feature using it is undefined for that stock-day, when: the stock has no cached bar on `d⁻`; it has no EQ bhavcopy row on `d⁻`, or `LAST` or `CLOSE` is not positive; or **`d` is an ex-date of any corporate action of that stock in NSE's 2025 file**. Ex-dates are announced in advance, so the last exclusion uses nothing later than `t`; it removes the days on which a price step (a demerger such as TMPV's on 2025-10-14, a split, a dividend) could enter the gap through a difference in how Kite and NSE adjust.

## 4. Features, fixed (from closed bars ≤ t and the bhavcopy of `d⁻`, nothing later)

`t` is one of L40's six decision times (09:45, 10:30, 11:15, 12:00, 12:45, 13:30); the decision bar is the bar that closes at `t` (starts at `t − 5 min`), as `kronos_feature_ic.decision_bar_index` finds it; `c₀` is its close. All returns in basis points.

- **F1 `gap`** `= (O(s, d) / pc(s, d) − 1) × 10⁴`, where `O` is the open of the stock's 09:15 bar on `d`. The same value at all six times of a day. Undefined if the day has no 09:15 bar.
- **F2 `rvol`** `= V(s, d, t) / mean{ V(s, e, t) : e in B(s, d) }`, where `V(s, e, t)` is the total volume of the stock's bars on session `e` that start at or before the decision bar's start time, and `B(s, d)` is the **20** most recent sessions before `d` on which the stock has bars and whose first bar starts at 09:15 (so the Muhurat session is not a baseline day). The audit's rebuilt checklist asks for 20 sessions; the scanner uses at most 4. Undefined if fewer than 20 such sessions exist, if the mean is zero, or if a **split, bonus or consolidation** of the stock (a change in the unit volume is counted in) has its ex-date on `d` or on any day from the first baseline session to `d`.
- **F3 `vwap_dist`** `= (c₀ / VWAP(s, d, t) − 1) × 10⁴`, with `VWAP = Σ((H + L + C) / 3 × volume) / Σ volume` over the day's bars from the first through the decision bar: `indicators.session_vwap`'s formula on closed bars. Undefined if the volume sum is zero. It reads no previous close.
- **F4 `sector`** `= mean{ chg(p, d, t) : p ≠ s, industry(p) = industry(s) }`, where `chg(p, d, t) = (c₀(p) / pc(p, d) − 1) × 10⁴` is a peer's move since its previous official close, and the peers are the point-in-time NIFTY 100 members of day `d` in the cache that have a decision bar at `t` and a defined `pc`. **The stock itself is left out** (its own move is momentum, which L31 measured and m60 controls), so a sector here is the rest of its industry. Peers are chosen from bars at or before `t` only; in particular **not** from L40's sample, whose membership needs future bars (the targets). Undefined for a stock with no peer with a defined move: always for BHARTIARTL and LT, the only members of their industries.
- **F5 `gap_reversal`** `= −(c₀ / pc(s, d) − 1) × 10⁴`, **at 09:45 only**, where `c₀` is the close of the bar ending 09:45.

The scanner's own sector rank includes the stock and ranks sectors, not stocks, and it reads delayed data; F4 is its continuous, leave-one-out form on the cache. No other transformation, threshold, combination or window is read.

**Control:** L40's `m60` (`kronos_feature_ic.m60_bp`), the last twelve bars' close-to-close return ending at the decision bar. **Stated now, before any number:** at 09:45, `m60` runs from the close of the previous session's 14:55 bar (15:00) to 09:45, so it contains all of F5's window except the stretch between 15:00 and the official close. F5's partial IC given `m60` therefore asks whether the gap measured from the official close says anything the 15:00-to-09:45 move does not. That is nearly an identity and a severe condition. It is the condition the sweep named, and it stays. F1 at 09:45 overlaps `m60` the same way.

## 5. Sample, fixed

L40's selection sample exactly: `kronos_feature_ic.selection_sessions` on the cached sessions (2025-09-01 to 2025-12-31, less the 5-session embargo before 2026-01-02), which lists **79 sessions to 2025-12-23, 78 with stock-times** (the Muhurat session has none), and `kronos_feature_ic.build_samples` with point-in-time membership and L40's adjustment drops (none, one fetch run): **43,362 stock-times**.

Each feature is scored on the stock-times of that sample where it is defined; F5 on the sample's 09:45 stock-times. A session enters a test only with at least 20 stock-times for that feature (the harness's `MIN_STOCKS`).

## 6. Targets, fixed

`kronos_feature_ic.target_bp` for k = 3, 6 and 12: from the open of the bar after the decision bar to the close of the bar k bars later. F1–F4 are scored at all three horizons, F5 at 60 minutes only.

## 7. Measurement, fixed

L40 §7 and its code, unchanged: per session, over all of that session's stock-times for the feature (the six decision times pooled, as L40 pooled them), the rank IC, the partial rank IC given `m60`, and the top-minus-bottom quintile spread in bp with each quintile's own mean (`session_stats`); then mean, standard error, t and share positive across sessions, both halves (`summarise`), and the smallest spread detectable at t = 2. Ties in a feature (F1 repeats one value per stock across the day's six times) fall in the harness's stable sort order, as in L40.

**No per-decision-time statistic is computed.** The audit's words "at the six L40 decision times" are read as the sample (the stock-times L40 used), not as six separate tests; that is how L40 computed its three tests over the same six times.

## 8. Family, and the gate for a trial

**The family is 13 tests:** F1–F4 × {15, 30, 60} minutes (12) and F5 × 60 minutes (1). Benjamini–Hochberg at q = 0.10 across the 13 on the raw quintile-spread p-values, which the harness computes two-sided. The partial-IC condition sits outside the family, as in L40 amendment 1. A test that cannot be computed counts at p = 1.

> A feature and horizon earns a pre-registered trial only if, on the selection sample, its quintile spread **exceeds 33.26 bp with t > 2 across at least 60 sessions**, is **positive in both halves**, **survives BH at q = 0.10 across the 13**, and its **partial IC given m60 is positive with t > 2** — `kronos_feature_ic.gate` applied once to the 13 summaries. A single side clearing 16.63 bp with t > 2 is reported and earns only a note.

If one clears, the trial that follows is pre-registered separately, in a new family "scanner intraday features", judged at N_family by the owner's bar of 2026-09-26 (`decision-2026-09-26-overnight-and-significance.md`), and confirmed on sessions after `splits.UNSEEN_AFTER` (2026-09-20) before anything reaches even the review queue. Spending the 2026 window would be the owner's decision and is not made here.

**If nothing clears:** the four features the audit named, in their scanner orientation, and the cross-sectional gap reversal do not rank the next 15 to 60 minutes of NIFTY 100 stocks past cost. With trial 35 and trials 93–116 this closes the audit's intraday selection question (its §6 item 4), and the audit's rebuilt checklist keeps these rules tagged **failed**.

## 9. Stage 0 — before any feature is compared with any return; each check a halt

1. **Feature count:** five feature functions and a family of 13 named tests, asserted in code.
2. **Data and the 2026 guard:** one fetch run in the cache (a second would need L40's straddle rule over 21 sessions, not 8; stage 0 halts instead); the latest bar read is before 2026-01-02; no bhavcopy dated 2026 and no `ca_2026.csv` opened.
3. **L40's sample reproduced:** 79 sessions listed, 78 with stock-times, 43,362 stock-times, halves 39 and 40, no adjustment drop, matching `kronos_l40_result.json`'s stage 0.
4. **Kite and NSE describe the same trade.** For every stock-day whose last bar enters a `pc`, `r = K_last / LAST`. On consecutive sessions of a stock with no corporate-action ex-date on the second, `r` should not move. Halt unless at least 95% of those pairs move by 5 bp or less. Also reported, not a check: the median move, and Kite's first open against NSE's open on the same days.
5. **Coverage:** every stock-time's reason for being undefined, per feature, by reason and by stock. The pre-registered reasons are the corporate-action exclusions, a singleton industry and a short relative-volume baseline. **Halt if any other reason (missing data: no bar, no bhavcopy row, a non-positive price) removes more than 1% of a feature's stock-times**, or if any of the 13 tests has fewer than 30 sessions in a half.
6. **Hand calculation:** on 5 seeded stock-times, each feature recomputed by a separate path — the SQLite rows, the bhavcopy CSV inside its zip and the corporate-action CSV, read directly — equals the module's value to 1e-9 bp.
7. **Look-ahead proof:** on at least 200 seeded stock-times of the selection sample, each feature computed from the full data equals, bit for bit, the feature computed after removing **every bar of every stock that starts after the decision bar, and every bhavcopy dated `d` or later**. An undefined value must stay undefined.
8. **Positive control, on a segment before the sample:** the cached sessions from 2025-05-01 to 2025-08-29, with L40's `build_samples`, membership and rules. The target used as its own feature passes the harness's gate at all three horizons; its negation fails with a negative spread; a seeded random number fails. BH over those nine. Any other pattern halts. **No candidate feature is compared with a return on this segment or any other during stage 0.**
9. **Information, not a check:** each feature's distribution on the selection sample (count and quantiles), which reads no return.

Stage 0 is written to `docs/research/data/l49_stage0.json`, committed and pushed. **The run then stops for an independent review** of this text, the code and the stage 0 record. The measurement pass starts only after that review, on the main session's instruction. A finding is fixed by a dated amendment before any L49 statistic exists.

## 10. One run

One measurement pass. It writes `l49_result.json` with status STARTED before it reads any target, and refuses to start if that file exists or if the committed stage 0 record is missing or changed. A re-run only for a crash before any statistic was printed, or a declared bug with both runs recorded. Nothing in §2–§8 changes after the first number is seen.

## 11. Compute

On the Mac, from the worktree, reading the main checkout's cache and NSE files read-only. The Mac runs the trading engine from 08:30 to 15:45 IST, so heavy work runs outside those hours, at `nice 15`. No Kite call; no key or token read; nothing imports `app`.

## 12. Trial accounting

Research look **L49**. Trials remain **202**. If a test clears, the trial that follows has its own pre-registration and number.

## 13. Choices this text makes that its sources left open

Listed for the reviewer, so each can be challenged before any number exists:

1. **Thirteen tests, not seventy-three:** the six decision times are pooled per session, as in L40 (§7).
2. **The official close, on Kite's basis by a same-day ratio** (§3), rather than the repaired panel's close or Kite's last trade.
3. **`rvol` is scored unsigned with a positive sign** (§1), because the scanner gives it none; the opposite sign and a volume-signed-by-move variant are not tested.
4. **`gap` is the 09:15 open against the official close, continuation-signed**, the same at all six times of a day.
5. **`sector` is leave-one-out** over the universe's own members by NSE's current industry label.
6. **Exclusions by corporate action** (§3, §4), from dates announced in advance.
7. **F5 keeps the partial IC given `m60`** although the two overlap almost completely at 09:45 (§4).

## Amendments

1. **2026-09-30, 20:26 IST (its commit), while writing the code and its tests on synthetic data; before the code was committed, before stage 0, and before any L49 feature was computed on project data.** Three things the text above left open or got wrong:
   - **Check 8's positive control.** The target used as its own feature has a partial IC given `m60` of exactly 1 in every session, up to rounding. The harness's t across sessions is then either undefined (zero spread, where `tstat` returns no t) or a number of order 10¹⁷ made of rounding error, so whether `gate` passes it is floating-point luck: two synthetic runs gave one of each. The control is therefore **the target plus seeded Gaussian noise of 5 bp standard deviation** (seed 123), its negation, and a seeded random number, each through `gate` unchanged. Five basis points is small against the targets' spread (tens of basis points at every horizon), so the control still stands for near-perfect foresight.
   - **Check 6** picks five seeded stock-times from the sample and five more from its 09:45 stock-times, so F5 is hand-checked on at least five.
   - **Check 5's reasons.** A stock whose industry has peers, none of which has a defined move, counts as **missing data** unless every one of those peers is on a corporate-action ex-date. It then counts against the 1% halt instead of escaping it.

   Nothing in the features, the sample, the targets, the statistics, the family or the gate changes.

2. **2026-09-30, 20:34 IST (its commit), after stage 0 run 1 halted at check 4 (`data/l49_stage0_run1.json`, commit `57b9ffe`), before any feature was computed on project data and before any return was read.** Run 1 passed checks 1 to 3 (L40's sample reproduced exactly) and halted at check 4: Kite's last 5-minute close divided by NSE's LAST moved by 5 bp or less on only 72.75% of consecutive stock-days (median 0.6 bp, p95 20.3 bp, worst 279 bp), against the 95% required. The halt was correct: §3's ratio rested on an assumption that is false.

   **What was looked at to find out why**, all of it prices of the previous-session stock-days that check 4 reads, from both sources, and nothing else: NSE's LAST equals Kite's last close exactly on 58% of the 7,321 stock-days, and equals NSE's own CLOSE on 3%; on ULTRACEMCO's 2025-12-01, NSE's LAST was 12,013 while Kite's last bar closed at 11,453 and NSE's high was 12,021. LAST is not the trade that ends Kite's last bar. The same day's other three prices do line up: Kite's first open against NSE's OPEN, Kite's highest high against NSE's HIGH and Kite's lowest low against NSE's LOW each move by 5 bp or less on 99.8% to 99.97% of consecutive stock-days, with a median move of 0.00 bp, and their median moves by 5 bp or less on 99.97% of them. The two exceptions to the median were both demergers, where Kite's adjustment step falls one session after NSE's ex-date: TMPV (ex-date 2025-10-14, step 2,494 bp) and HINDUNILVR (ex-date 2025-12-05, step 74 bp). The official close's own distance from LAST is a median of 9.5 bp (p95 36 bp).

   **Changes**, made before any feature is computed:
   - **§3, the previous close:** `pc(s, d) = CLOSE(s, d⁻) × F(s, d⁻)`, where `F(s, e)` is the median of three same-day ratios: Kite's first bar's open over NSE's OPEN, Kite's highest high over NSE's HIGH, and Kite's lowest low over NSE's LOW, on session `e`. `F` is Kite's adjustment factor for that day; LAST is no longer used. `pc` is undefined if any of the four NSE prices is not positive.
   - **§3, the ex-date exclusion** widens to **`d` or `d⁻`**: `pc(s, d)` is undefined if either is an ex-date of the stock in NSE's 2025 file, because Kite can place a demerger's step on the session after NSE's ex-date. On the 09:45 stock-times this removes 28 more of 7,227 (0.4%).
   - **Check 4** now tests the assumption the new formula rests on: that Kite's price basis on `d` is the one measured on `d⁻`. For every selection session `d` and member `s` with both days' bars and NSE rows and neither day an ex-date, `|F(s, d) / F(s, d⁻) − 1|` must be 5 bp or less on at least 95% of stock-days. `F(s, d)` uses day `d`'s whole session; this is an audit of the data, not a feature, and no return enters it. Run 1's statistic (LAST) is reported beside it as information.
   - **The 2026 guard:** the loader's query now stops before **2026-01-01**, so nothing dated 2026 is loaded, as §2 says. Run 1's cutoff was the held-out start (2026-01-02), so the bars of the 2026-01-01 session were loaded, and no check used them. L40's sample does not change (its selection ends on 2025-12-23).
   - **Check 6's hand path** computes `F` from the SQLite rows and the bhavcopy zip in the same way.

   Nothing in the features' other definitions, the sample, the targets, the statistics, the family or the gate changes. Stage 0 is run again as **run 2**, whose record is `data/l49_stage0.json`.

3. **2026-09-30, after the independent review of this text, the code (`985bb62`) and stage 0 run 2 (`8103c21`), which was NOT APPROVED on one blocking finding; before the measurement pass, which has not run.** **What had been seen when this was written:** the definitions above, and stage 0's records, whose only statistics about the features are feature-only ones (coverage, distributions, look-ahead and hand checks). No feature has been compared with any return, no target in the selection sample has been read, and no `l49_result.json` exists. To check two of the review's facts, membership and corporate-action rows were read again (no price). This amendment changes no code, no feature, no sample, no statistic and no threshold. Stage 0 is not rerun. It changes how one outcome of the gate is read, and it discloses the review's other notes.

   **B1 — F5's partial IC given `m60` tests a hypothesis this text did not register.**
   - **The identity.** At 09:45, `m60 = c₀ / P₁₅:₀₀ − 1`, where `P₁₅:₀₀` is the close of the previous session's 14:55 bar (§4, Control). F5 is `−(c₀ / pc − 1)`. Since `c₀ / pc = (c₀ / P₁₅:₀₀) × (P₁₅:₀₀ / pc)`, to second order **F5 = −m60 + (pc / P₁₅:₀₀ − 1)**. The only part of F5 that `m60` does not already hold is the previous official close against the previous session's 15:00 price.
   - **That part is small.** Its size has not been measured. The nearest measured quantity is from amendment 2's diagnosis: NSE's CLOSE against its LAST, a median of 9.5 bp and a p95 of 36 bp. It is of that order, against F5's standard deviation of 86.3 bp (stage 0 check 9).
   - **So the partial IC asks something other than F5's hypothesis.** It asks whether the price gap between 15:00 and the official close ranks the next hour. §4 called the condition severe but did not draw this conclusion. It is recorded now, before any result.
   - **How F5's verdict is reported and read.** F5's result is reported condition by condition, as `gate` returns it: spread above 33.26 bp, t > 2, at least 60 sessions, both halves positive, BH, and partial IC.
     - **If F5 clears every condition except the partial IC**, the reading is: *a 09:45 reversal ranks the next 60 minutes past cost, but it cannot be told apart from `m60`'s own reversal*. **No trial is earned.** The gate is unchanged, and `gate` still returns "fails".
     - **If F5 fails any other condition**, §8's reading stands.
   - **§8's last paragraph is qualified accordingly.** In the case above, the sentence "the cross-sectional gap reversal does not rank the next 15 to 60 minutes ... past cost" is **not** made. The results note states the reading above instead.
   - **§1's table, row F5, is corrected.** F5 is **the sweep's form**, previous official close → 09:45 close, ranked at 09:45 against the next 60 minutes. It is **not the source repository's H2**, which ranks the close-to-open return and holds from 10:00 to 15:20 (`predictive_tools_C.md`, candidate 1). **This look does not close H2 as its source defined it.**

   **Notes from the review, disclosed (not blocking):**
   - **N3 — the universe is today's 100 cached names.** Point-in-time members missing from the cache:
     - on every selection session: BAJAJHFL, HAVELLS, ICICIGI, JSWENERGY, LICI and NAUKRI;
     - also, on sessions before 2025-09-30: DABUR, HEROMOTOCO, ICICIPRULI, INDUSINDBK and SWIGGY — 11 in all.

     They are not in the sample (as in L40), and they are not available as F4 peers either. This is the survivorship caveat L40 already carries, now affecting F4's sectors as well.
   - **N4 — pooling decision times mixes times inside the quintiles.** For `vwap_dist` and `sector`, the top and bottom quintiles of a session hold different mixes of decision times. The review's median per-session dissimilarity is 0.29 and 0.28, from features only. Part of those two spreads can therefore be the market's move between times of day, not the stock's ranking. That component should be mostly noise, since L32 found no market-level intraday momentum. It is disclosed, not corrected; the pooling is L40's.
   - **N5 — F4 is not free of the stock's own move.** §4's "the stock itself is left out" is inexact. Within one industry of `n` members, F4 is `(Σ chg − chg(s)) / (n − 1)`. So among the stocks of the same industry, F4 ranks them by **minus their own move**. By the review's measure that is about 1.6% of F4's rank variance. The rest ranks industries against each other.
   - **N6 — BH uses two-sided p-values on a family of signed hypotheses.** This is inherited unchanged from the harness (`kronos_feature_ic.gate`). A two-sided p-value is twice the one-sided p-value of an effect with the registered sign. A strongly wrong-signed test cannot pass, because the spread condition is signed, but it can loosen BH's step for the others. Disclosed, not changed.
   - **N7 — TVSMOTOR's 102 `rvol` exclusions come from the "Scheme of Arrangement — Bonus NCRPS 4:1"** (ex-date 2025-08-25). That is a bonus of preference shares, which does not change the count of equity shares. The exclusion is conservative (it drops stock-times it did not need to) and reads nothing later than `t`.
   - **N8 — F4 is the audit's "sector strength"** (its §2 row, the scanner's sector rank). It is not **rule 3.6**, the stock's change minus its sector index's change, which now runs as a live shadow under #219. L49 is not to be described as covering rule 3.6.

   **How the pass will be run:**
   - **By hand, outside 08:30–15:45 IST.** The refusals have no market-hours guard (review N1).
   - **`--owner-approved-rerun` will not be used.** It would overwrite the first result (review N2), which §10 forbids.
