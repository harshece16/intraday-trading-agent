# Pre-registration — do lagged intraday returns of factor portfolios predict the NIFTY's next 30 or 60 minutes past cost? (research look L51; a trial only if it clears)

**Written 2026-09-30 at about 20:30 IST, before any L51 code exists and before any number in this document was computed from a forecast.** Requested by the main session: the owner asked for every open research item to be completed, and this is candidate 2 of `data/predictive-tools-sweep/predictive_tools_B.md`, which recommended it for its own pre-registration in a new family, **"intraday index timing"**. Seen before this was written: the results of L40, L46 and L47 (all FAIL, all cross-sectional stock ranking, not index timing), and the bar and session counts of the data sources in §2. No factor return, forecast or index return over any horizon has been computed.

**What it is not.** Not a strategy, not a backtest, not a trial. Nothing enters the engine. It is a measurement look: does a model of this kind produce forecasts that would pay for a NIFTY futures round trip, on the L40 selection sample?

## 1. Hypothesis and prior

Aleti, Bollerslev and Siggaard (*Management Science* 71(9), 2025, pp. 7731–7751) show that lagged 15-minute returns on 272 US factor portfolios (218 characteristic sorts, 48 industries, the Fama–French six), fed to regularised regressions in an expanding window, predict the market's next 15-minute return out of sample (2004–2020, R² 0.2%). Trading SPY on the ensemble forecast gives an intraday Sharpe ratio of 1.37 after costs; Ridge alone gives 0.79 under the same rule. Their cost is half SPY's quoted spread per rebalance, a fraction of a basis point.

**Hypothesis:** a Ridge forecast built from the lagged five-minute returns of about 20 factor portfolios on NIFTY 100 stocks predicts the NIFTY 50's return over the next 30 or 60 minutes well enough that trading NIFTY futures only when the forecast exceeds the round-trip cost earns a positive net return.

**Expected answer: no.** The cost here is 6.95 bp a round trip (§7), an order of magnitude above the paper's. With a forecast R² near the paper's 0.2%, and a 30-minute index return whose standard deviation is roughly 20 to 30 bp (a daily volatility near 1%), the forecast's typical size is about one basis point, so few forecasts should ever exceed 6.95 bp. The likeliest outcome is too few trades to pass. The IC is reported regardless, so the look still says whether the lagged factor returns carry any direction at all.

## 2. Data, fixed

- **Stock bars:** the Kite five-minute cache `backend/data/kite_history.db`, opened read-only, the 100 symbols it holds, sessions from 2024-09-20. Rows with a timestamp on or after 2026-01-02 are excluded in the SQL, and the loader asserts the latest timestamp it read.
- **Index bars.** The five-minute cache has **no index bars**: its 100 symbols are all stocks. **The NIFTY 50 index's own bars do exist**, as Kite one-minute bars in `backend/data/overnight_1m.db` (symbol `NIFTY 50`, instrument 256265, fetched for the overnight-ETF line by `research/overnight_data.py`, 2015-01-01 to 2025-12-31, no 2026 row by construction). From 2024-09-20 to 2025-12-31 it has 318 sessions, the same 318 as the stock cache; every session has 375 minutes except the Muhurat sessions of 2024-11-01 and 2025-10-21 (60 each). **L51 uses the index itself, aggregated to five-minute bars, not a proxy.** A five-minute bar starting at hh:mm takes the open of the hh:mm minute and the close of the hh:mm+4 minute, the same start-time labelling as the stock cache. Stage 0 checks that labelling (§9.2). An equal-weight average of the stocks appears only as that check and inside factor EWX (§3).
- **Tradable versus measured.** The trade is in NIFTY futures, but futures bars are not on disk. Returns are measured on the index. Over 30 or 60 minutes the futures' basis moves by a fraction of a basis point; this is stated as a caveat, not modelled.
- **Daily characteristics:** from the repaired bhavcopy panel, `research/nse_prices.load(wide=True)` (#175, #177, #178): the total-return adjusted close, the raw traded value in rupees, and the raw high and low. The five-minute cache is not used for characteristics because it starts on 2024-09-20, and 12-month momentum and 250-session beta need a year of history before the first training session. The panel excludes 2026 unless asked, and is not asked.
- **Universe:** point-in-time NIFTY 100 members (`nifty100_membership.csv`, `kronos_feature_ic.membership_asof`) that have bars in the cache on that session. The cache holds today's members, so members that have since left the index are missing (as in L40). Stage 0 counts how many members each session has.
- **Sectors:** the Industry column of `backend/data/nifty100.csv`, the committed list whose 100 symbols are exactly the cache's. The labels are today's, applied to history; industry labels rarely change, and no return is read from them.
- **Sessions:** a session is used only if the index has all 75 five-minute bars from 09:15 to 15:25 and at least 60 members have all 75. This drops the two Muhurat sessions. The "previous session" is the previous session so used.

## 3. The factor portfolios, fixed: 23

For each session d, every characteristic is computed from panel rows dated strictly before d. On each five-minute bar, a stock's return is close over the previous bar's close, minus one. For the first bar (09:15) it is close over open, minus one, so the overnight gap never enters (and no corporate action with it). A factor's bar return is the equal-weighted mean bar return of the top third of the members, ranked on the characteristic, minus that of the bottom third (n // 3 stocks each). Stocks without a valid characteristic, or without both bars, are left out of that factor on that bar. A factor needs at least 30 ranked members on the session, else its returns for that session are missing.

Notation: t is the last panel session before d; C is the adjusted close, V the traded value in rupees, H and L the raw high and low; R is the daily return C/C(previous panel session) − 1. Windows count panel sessions ending at t, and need at least 80% valid observations; a ratio of two closes needs both. R is missing when either close is. M is the equal-weighted mean R of the point-in-time NIFTY 100 members on that day, taken from the panel for all members, including the ones the cache lacks.

| # | Factor | Characteristic, top third minus bottom third |
| --- | --- | --- |
| 1 | LIQ | log of mean V over 60 sessions (size and liquidity; the panel has no share count, so no market value) |
| 2 | TURN | mean V over 5 sessions / mean V over 60 |
| 3 | ILLIQ | Amihud: mean over 60 sessions of \|R\| / V |
| 4 | MOM | C(t−21) / C(t−252) − 1 |
| 5 | REV21 | C(t) / C(t−21) − 1 |
| 6 | REV5 | C(t) / C(t−5) − 1 |
| 7 | REV1 | R(t) |
| 8 | VOL | standard deviation of R over 60 sessions |
| 9 | IVOL | standard deviation of the residual of R on M (OLS with intercept) over 60 sessions |
| 10 | BETA | OLS slope of R on M over 250 sessions |
| 11 | HIGH52 | C(t) / max C over 252 sessions |
| 12 | RANGE | mean of log(H/L) over 21 sessions |
| 13–21 | sector (9) | equal-weighted mean bar return of a sector's members minus that of all members: Financial Services (23 names), Capital Goods (9), Automobile and Auto Components (9), Healthcare (8), Fast Moving Consumer Goods (8), Metals & Mining (7), Power (6), Oil Gas & Consumable Fuels (6), Information Technology (6). The sectors with at least six names |
| 22 | MKT | the NIFTY 50 index's own bar return (not a sort) |
| 23 | EWX | the equal-weighted mean bar return of all members minus the index's: small against large within the NIFTY 100 (not a sort) |

That is 12 characteristic sorts, 9 sectors, MKT and EWX: **23 series**, fixed.

Characteristics are ratios of adjusted closes inside their window, or raw traded values. A corporate action after t multiplies every earlier adjusted close by the same factor, which cancels, so the adjusted panel carries no look-ahead into them. Stage 0 checks this directly (§9.3).

## 4. Predictors, fixed: 92

Decision time: the close of bar i on session d. For each of the 23 series, four lagged returns, after the paper's cascade (15 minutes, an hour, the previous day), scaled to five-minute bars:

1. the last bar (bar i);
2. the last six bars, 30 minutes (bars i−5 to i, summed);
3. the session so far (bars 0 to i, summed);
4. the previous session, all 75 bars summed (open to close, no overnight gap).

23 × 4 = **92 predictors.** At 09:45, items 2 and 3 coincide; Ridge copes with collinearity. Nothing else is added, not even time of day.

## 5. Target and decision grid, fixed

- **Target:** the NIFTY 50's return in bp from the open of bar i+1 to the close of bar i+k, with k = 6 (30 minutes) and k = 12 (60 minutes). This is `kronos_feature_ic.target_bp`'s definition, applied to the index. One model per horizon.
- **Training rows:** every bar i whose close falls from 09:45 onward and whose exit bar closes by 15:15. That is 61 rows a session for 30 minutes, 55 for 60. The training labels overlap; the cross-validation folds are whole sessions (§6).
- **Scoring grid:** non-overlapping decisions, so at most one position is open at a time per horizon.
  - 30 minutes: decisions at 09:45, 10:15, and every 30 minutes to 14:45. That is 11 a session, the last one exiting at 15:15.
  - 60 minutes: decisions at 09:45, 10:45, 11:45, 12:45 and 13:45. That is 5 a session, the last one exiting at 14:45.

## 6. Model, fixed

- **Ridge regression**, implemented in numpy (scikit-learn is not installed): minimise ‖y − ȳ − Xb‖² + λ‖b‖² with λ = α·n. X is the predictors standardised with the training rows' mean and standard deviation (ddof 0), clipped at ±5; a constant column is set to 0. The intercept is the training mean of y, unpenalised. Forecast = ȳ + x·b.
- **Regressand:** the target, winsorised at the training rows' 0.5% and 99.5% quantiles. This is a simple analogue of the paper's best specification, which drops jumps from the regressand. The scoring always uses the raw, unwinsorised return.
- **Penalty, chosen once per horizon, inside the first training window only.** Grid α = 10^k for k = −3, −2.5, …, 4 (15 values). The first training window is the sessions from the second cached session (the first has no previous session) to six sessions before the first session of March 2025. Split it into 5 contiguous blocks of sessions. For each block v = 2 to 5, train on blocks 1 to v−1 less the last 5 sessions before block v, and validate on block v. The winsorisation thresholds and the standardisation come from each fold's own training rows. Choose the α with the lowest mean squared error, pooled over the four validation blocks (on the winsorised target); a tie goes to the larger α. **That α is then fixed for every monthly refit.** If the largest α wins, the forecast is close to the intercept and there will be few or no trades; that is a result, not a reason to change the grid.
- **Expanding-window refits, monthly.** For each calendar month from 2025-03 to 2025-12, the model is refitted on every training row from the second cached session to the session six before the month's first session (**a 5-session purge**), and it forecasts every decision of that month. The forecasts from 2025-03 to 2025-08 lie outside the scoring sample; §8 reports them as information only.

## 7. Trade rule and cost, fixed

- **Rule:** at each scoring-grid decision, if forecast > C, go long one NIFTY futures lot from the open of bar i+1 to the close of bar i+k; if forecast < −C, go short; otherwise no trade. Net return = direction × target − C. No netting of consecutive trades in the same direction.
- **C = 6.95 bp**, computed with `costs.round_trip_pct` on this futures tariff:
  - Tariff, from zerodha.com/charges, read 2026-09-30 (equity futures):
    - brokerage 0.03% or ₹20 per executed order, whichever is lower;
    - STT 0.05% on the sell side;
    - NSE transaction charge 0.00183%;
    - SEBI ₹10 a crore;
    - IPFT ₹0.01 a crore;
    - stamp duty 0.002% on the buy side;
    - GST 18% on brokerage, SEBI, transaction and IPFT charges.
  - Slippage: 0.5 bp a leg, an assumption rather than a measurement (the project has never measured a futures fill). It is meant to cover the quoted spread and the gap between the futures' and the index's price at entry and exit.
  - Notional: one lot of 65 at 25,000 = ₹16.25 lakh.
  - Result: charges 5.95 bp plus slippage 1.00 bp = **6.95 bp**. The sweeps' 6–7 bp.
- The rates are 2026's, after the 1 April 2026 STT increase. The 2025 tariff (STT 0.02%, NSE 0.00173%) would have cost 2.87 bp in charges; §8 reports the same trades netted at that cost, as information only. The rule's threshold does not change.
- Capital: one lot needs about ₹1.7 lakh of margin (`literature-sweep-2026-09-25.md` §3), beyond the current account. A pass would therefore not be executable today.

## 8. Statistics and gate, fixed

**Scoring sample:** the L40 selection sessions (`kronos_feature_ic.selection_sessions`: 2025-09-01 to 2025-12-23, 79 sessions) that are full sessions by §2, which should be **78** (the Muhurat session of 2025-10-21 drops out). Halves: `splits.halves` of those sessions. **The 2026 window is not read.**

**Gate, per horizon (two configurations):**

1. at least 100 trades, and at least 40 sessions with a trade (as in `prereg-combo-search.md`);
2. mean net return per trade above 0 bp;
3. t above 2 for the per-session series: in each session with a trade, the mean net per trade; t across those sessions;
4. both halves positive: the per-session series' mean in each half is above 0;
5. deflated Sharpe ratio ≥ 0.95 for the per-session series (`evaluation.deflated_sharpe_ratio`) at **n_trials = 2**, the look's number of configurations.

**L51 clears if either horizon passes all five.** A clearing horizon earns a trial, pre-registered separately in the family "intraday index timing". That trial is judged at N_family by the owner's bar of 2026-09-26 and confirmed on sessions no test has seen before anything else. Clearing does not make L51 a trial.

**Reported, not gated:**

- **IC:** Pearson and Spearman correlation of forecast and realised target over every scoring-grid decision, traded or not, with the naive t, IC × √((n − 2)/(1 − IC²)). The grid's decisions do not overlap.
- The paper's out-of-sample R², uncentred: 1 − Σ(r − f)² / Σ r².
- Hit rate of the forecast's sign.
- Mean of sign(forecast) × target over every decision, gross (the paper's "Sign" rule at zero cost).
- Trades by decision time and by side.
- The same trades netted at the 2025 tariff (3.87 bp).
- Every statistic above for the pseudo-out-of-sample months 2025-03 to 2025-08.
- The ten largest coefficients of the December refit, in standardised units.

## 9. Stage 0, each check a halt, no scoring-sample target read

1. **Coverage:**
   - the index has all 75 bars on every cached session except the two Muhurat sessions;
   - the stock cache and the index agree on the session list;
   - every used session has at least 60 members with all 75 bars;
   - the scoring sample is 78 sessions with at least 30 in each half;
   - no timestamp on or after 2026-01-02 was read from either database, and the panel's last session is before 2026-01-02.
2. **Bar alignment:** the correlation between the index's five-minute return and the equal-weighted member return must be highest at lag 0 among lags −2 to +2, and at least 0.7. This catches an end-labelled series against a start-labelled one, which would turn a lagged predictor into a contemporaneous one.
   - Kite's as-of-fetch adjustment (#108): no fetched span of the stock cache starts or ends inside a session (spans are whole days), so returns within a session are never affected. Recorded.
3. **Characteristics, by hand:** each of the 12 characteristics recomputed with plain loops for 5 random (stock, session) pairs matches to a relative 1e-12. Recomputing after multiplying the adjusted closes before a random date by a constant (a later corporate action) changes none by more than a relative 1e-12. Coverage recorded: members ranked per factor per session, minimum and median.
4. **Factors, by hand:** 5 random (session, bar) pairs, all 23 series, recomputed by sorting and averaging in plain Python, match the vectorised values to 1e-12. The factors' correlation matrix and standard deviations are recorded.
5. **Look-ahead proof:** for at least 200 random (session, decision bar) pairs, drawn across the first training window, the pseudo-out-of-sample months and the scoring sample, the 92 predictors are bit-identical when rebuilt from sources with every bar after the decision bar's close, and every panel row dated on or after the session, removed.
6. **Purge:**
   - for each refit month, at least 5 sessions lie between the latest training session and the month's first session;
   - for each cross-validation fold, at least 5 sessions lie between its last training session and its validation block;
   - no scoring decision is forecast by a model whose training includes its session or any of the 5 before it;
   - no stage-0 fit reads a target dated on or after 2025-09-01.
7. **Positive control** (pseudo-out-of-sample months 2025-03 to 2025-08 only). Add a 93rd predictor to every row, training and forecast alike: the row's realised target plus Gaussian noise whose standard deviation is 3.18 times that of the target over the first training window's rows (a correlation of about 0.3; seed 51). Run the whole pipeline: cross-validation, monthly refits, the §7 rule, the §8 gate over those months' full sessions. **It must pass both horizons.**
   - **Negative control:** every row's 92 real predictors, training and forecast alike, replaced by the same bar's predictors on another session: a fixed random derangement of the used sessions up to 2025-08-29, seed 51. The same pipeline over the same months. **It must not pass either horizon.**
   - Neither control's number describes the real forecast.

**Also recorded, as information:**

- the α chosen for each horizon and the full cross-validation curve;
- the cost computation;
- the distribution of the real forecast's magnitude over 2025-03 to 2025-08, and the share above C. These are forecasts only, from models trained before each month; no realised return is compared with them.

The share above C, times 78 sessions and the grid, gives the number of trades to expect. It does not stop the scoring pass, and the IC is informative either way.

**Stage 0 stops there.** An agent other than the builder reviews the code against this text and the stage-0 output before the scoring pass. A finding is fixed by a dated amendment below, before any scoring-sample target is read.

## 10. One run

The scoring pass needs the main session's go-ahead, recorded in its arguments. It refuses to start unless `docs/research/data/l51_stage0.json` is committed, has status STAGE0_DONE and has no halt. It writes `l51_result.json` with status STARTED before it reads any scoring-sample target, and it refuses to run if that file exists, whatever its status, unless given a recorded owner-approved reason. It uses the α values recorded in stage 0, and asserts that they are the ones it would choose. It runs once.

## 11. Trial accounting

Research look **L51**, two configurations (30 and 60 minutes), in the new family "intraday index timing". **No trial is spent.** The count of record stays at 202.

## Amendments

All three are dated 2026-09-30, about 20:25 IST, written while the code was being built and before stage 0 ran. No L51 check, statistic, target or forecast existed on project data. One smoke run had loaded the data and built the factors and predictors, and printed only their shapes: 316 sessions, 23 factors, 92 predictors.

A correction to the header: this text was committed at 20:13 IST (769c21c), so "about 20:30" should read "by 20:14".

1. **The positive control's planted signal is stronger: noise 1.732 times the target's standard deviation, a correlation of about 0.5, instead of 3.18 and 0.3.**
   - Why: at a correlation of 0.3, the forecast's standard deviation is about 0.3 times the target's, roughly 6 to 8 bp. Only about a quarter to two-fifths of decisions would clear 6.95 bp, at a net of 3 to 4 bp a trade against a per-trade standard deviation of 20 to 30 bp. The expected t over 2025-03 to 2025-08 is then about 2.5 to 2.8, so the control would fail by chance often enough to make its halt uninformative.
   - At 0.5 the expected t is well above 5 at both horizons. The control still tests the whole pipeline end to end: predictors, Ridge, refits, the trade rule's sign and timing, the statistics.
   - Seed 51, as before.
2. **The 2025-tariff figure in §7 and §8 is corrected to 2.92 bp in charges, 3.92 bp with slippage.** The 2.87 in §7 was computed at 75 × 25,900 (₹19.4 lakh), not at the fixed notional of 65 × 25,000. It is information only and changes no threshold.
3. **Implementation choices the text left open, fixed now:**
   - **Missing factor bars.** A factor bar return that is missing counts as 0 in the predictors (no information). Stage 0 counts them.
   - **Statistics.** VOL uses ddof 1. IVOL is the residual standard deviation with n − 2. BETA and IVOL use the rows where both the stock's and the market's return exist. M needs at least 50 members with a return. REV1 is C(t)/C(t−1) − 1, i.e. R(t).
   - **Ties.** Tercile ties are broken by symbol, alphabetically.
   - **Who is ranked** is decided by point-in-time membership and the characteristic alone. No bar of the session decides it. A stock that stops trading later in the session stays in its group, and simply drops out of the bars it lacks.
   - **The §2 session filter** uses whole-session completeness, so it is a sample definition, not a predictor. The §9.5 proof keeps the session list and removes everything else after the decision.
   - **Stage 0 and scoring-window returns.** Stage 0 computes no target on or after 2025-09-01 (those targets are left missing). §9.2's alignment correlation uses sessions before 2025-09-01.
   - **The negative control's derangement** leaves out the first session, which has no predictors.
   - **The look-ahead proof** draws 240 pairs, 80 per window, at decision bars closing 09:45 to 15:15.
   - **The threshold C** is the computed 6.946 bp, which the text rounds to 6.95.
   - **§9.4's hand check** re-reads the two bars from the cache rather than from the loaded arrays.
4. **2026-09-30, 20:35 IST, after the first stage-0 run halted at §9.1 and before any other check ran.** That run computed nothing beyond the session lists: no characteristic check, factor, predictor check, target, fit or forecast had run. The halt was in the check's definition, not the data:
   - **The Muhurat session of 2024-11-01 ran 18:00 to 19:00 IST.** Both databases have it: 60 index minutes, and 12 stock bars from 18:00 to 18:55. None of it falls in the 09:15–15:25 window, so the index has no regular-hours bars that day, and the check, written for a 60-minute session inside the window, misfiled it. The 2025-10-21 session (13:45 to 14:45) fell as expected.
   - **The stock cache has a session on 2026-01-01** (100 symbols, 75 bars each). The loader's pre-registered cut, before 2026-01-02 (`splits.HELD_OUT_START`, as L47), keeps it. The index database ends on 2025-12-31, so that session has no index bars and is dropped. It lies after the scoring sample, in the embargo before the held-out window, and nothing uses it. It is not held-out data by the project's definition, but it is a 2026 date; recorded here.
   - **§9.1 now reads:**
     - the dropped sessions are exactly 2024-11-01 (no regular-hours bars), 2025-10-21 (60 index minutes) and 2026-01-01 (no index bars);
     - the stock cache's sessions up to 2025-12-31 equal the index database's, counting any minute of the day.
   - Every other condition of §9.1 is unchanged.
5. **2026-09-30, 20:50 IST, after stage-0 run 2 halted at §9.7 (`data/l51_stage0_run2.json`, head e5ed55d). No scoring-sample target has been read.**
   - **Checks 1 to 6 passed** in run 2:
     - coverage (78 scoring sessions, 39 per half, 85 to 94 members a session);
     - alignment (correlation 0.888 at lag 0, |r| < 0.02 at lags ±1 and ±2);
     - characteristics and factors by hand, and scale invariance: no mismatch;
     - the look-ahead proof: 240 of 240 bit-identical;
     - the purge: every gap 5 sessions; the latest training session of any stage-0 fit is 2025-07-24.
   - **The negative control passed** (0 trades at either horizon).
   - **The positive control failed at 30 minutes.** With a planted correlation of 0.51, the pipeline's forecast had an IC of 0.38 with the realised return over 2025-03 to 2025-08, and made 365 trades. They netted +2.1 bp a trade, with a t of 1.24 and a second half of −0.75 bp. At 60 minutes it passed: IC 0.39, 143 trades, +7.0 bp, t 2.87, DSR 0.998.
   - **Why:** amendment 1's calculation assumed a 30-minute standard deviation of 20 to 30 bp, but that was not measured. Measured before the scoring sample, the 30-minute target's standard deviation is 19.1 bp in the first training window and 15.2 bp over 2025-03 to 2025-08. The 60-minute target's is 26.4 and 22.5 bp. Only 52% of realised 30-minute moves over 2025-03 to 2025-08 exceed 6.95 bp at all, so even a perfect forecast would trade barely half the time.
   - **The failure is economic, not mechanical.** An IC of 0.38 on the pseudo-out-of-sample months, from a planted correlation of 0.51, shows that the sign and timing of forecasts, targets and trades are right. A misaligned target or a flipped sign would give an IC near zero or negative.
   - **Change:**
     - the positive control's planted correlation is raised to **0.7** (noise 1.02 times the target's standard deviation, seed 51). This is chosen after seeing run 2, and it calibrates a check of the machinery: can a strong enough forecast pass the gate? It is not a test of the hypothesis;
     - the 0.5 control is kept and reported every run as **information on the design's power**, not as a halt;
     - the halt rule otherwise stands: at 0.7 the control must pass both horizons, and the negative control must pass neither.
   - **What run 2 already says about L51, before any scoring target is read:** a forecast needs an IC of roughly 0.4 with the realised return just to break even on 6.95 bp at 30 minutes. The paper's R² of 0.2% corresponds to an IC of about 0.045. The first-window cross-validation picked α = 100 at 30 minutes and α = 31.6 at 60 minutes. Their validation MSE is 0.02% and 0.12% below the intercept-only level, so the 92 predictors add almost nothing there. L51 is expected to fail on the trade count, and its IC is the informative number.

