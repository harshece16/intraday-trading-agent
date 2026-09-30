# Lagged factor-portfolio returns do not time the NIFTY past cost — research look L51: does not clear at either horizon, no direction from the predictors

**2026-09-30.**
- **Pre-registration:** `prereg-index-timing.md` (`769c21c`), amendments 1 to 6.
- **Code:** `index_timing_l51.py`, at `1ac6e2e` for the stage-0 run of record and at `c2d77c2` for the scoring pass.
- **Reviews:**
  - first independent review of `15f9015`: NOT APPROVED (B1, B2), both fixed by amendment 6;
  - second review: APPROVED at `c2d77c2`.
- **Stage 0 run of record:** run 4, 21:02:04 to 21:02:14 IST, record `data/l51_stage0.json`.
- **The one scoring pass:** at `c2d77c2` on the Mac, from 21:11:09 to 21:11:15 IST (times from `date`). It made its own commits: STARTED `eaf6152` at 21:11:09 and DONE `7696dd2` at 21:11:14.
- **Records:**
  - `data/l51_result.json`;
  - `data/l51_decisions.csv`, 3,200 rows, SHA-256 `55674ef2…fb16`;
  - `data/l51_models.json`, SHA-256 `949b6a0b…2f45`.

**Checked and recorded immediately before the pass** (review N2), at 21:11:09 IST:
- `git status` was clean and `git diff c2d77c2 --stat` was empty;
- HEAD was `c2d77c2c359f`;
- `kite_history.db` was last modified 2026-09-20 03:14:17 IST and `overnight_1m.db` 2026-09-27 15:07:07 IST, both before stage 0 run 4 started (21:02:04).

**Asserts that held during the pass:** stage 0's data fingerprints (2,316,288 stock rows, 118,620 index minutes), stage 0's α at both horizons, and the reproduction of all 1,342 + 610 pseudo-out-of-sample forecasts (largest difference 0.0 bp).

## Headline (amendment 6): the predictors carry no direction

xb is the forecast minus that month's intercept: the part the 92 lagged factor returns contribute. It is scored against the realised NIFTY 50 return on the 78 sessions from 2025-09-01 to 2025-12-23.

| Horizon | xb IC (pooled) | Session-clustered t | IC, first / second half | Mean of per-session xb ICs (t) | Hit rate of sign(xb) | sign(xb) × target, mean of session means (t) | Reading |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 30 minutes (858 decisions) | +0.039 | 1.16 | +0.099 / −0.014 | −0.006 (−0.15) | 51.2% | +0.32 bp (0.72) | **no direction** |
| 60 minutes (390 decisions) | +0.036 | 0.63 | +0.077 / −0.010 | −0.029 (−0.49) | 51.0% | +1.12 bp (1.30) | **no direction** |

**The reading rule** (fixed before the run) needed a clustered t above 2 and a positive IC in each half. Both horizons fail it on both counts: t 1.16 and 0.63, and the second half is negative at both.

**The pooled and per-session measures disagree in sign (review N6).**
- The pooled xb IC is slightly positive (+0.04) at both horizons; the mean of per-session ICs is slightly negative (−0.006 and −0.029).
- The per-session measure removes each session's own level, so whatever the pooled figure picks up comes from differences between sessions. Neither measure is distinguishable from zero.
- The two agree on the only question the rule asks: no direction.

## Verdict, in the pre-registration's terms (§8)

| Horizon | Decisions | Forecasts above 6.95 bp | Trades | Net per trade | t | Halves | DSR (N = 2) | Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 30 minutes | 858 | 0 | 0 | — | — | — | — | **fail** (fewer than 100 trades) |
| 60 minutes | 390 | 0 | 0 | — | — | — | — | **fail** (fewer than 100 trades) |

The verdict, in the wording amendment 6 fixed before the run:

> L51 does not clear at 30 minutes: the forecast exceeded the 6.95 bp round trip on 0 of 858 decisions. The 30-minute gate cannot be passed at any plausible IC: a planted forecast with an IC of 0.38 over 2025-03 to 2025-08 made +2.10 bp a trade, t 1.24; the same strength gave t 2.87 at 60 minutes. L51 does not clear at 60 minutes: the forecast exceeded the 6.95 bp round trip on 0 of 390 decisions. Stage 0's positive control was strengthened from a correlation of 0.5 to 0.7 after run 2 had failed at 30 minutes (amendment 5), so the halt it provides is weaker than first promised; the 0.5 figures are what a forecast of that strength earns.

**No trial is spent;** the count of record stays at 202. Research look L51 is closed.

## The pre-registered IC (§8), kept as written

These statistics are on the whole forecast, intercept included. On the scoring sample 99.1% (30 minutes) and 89.7% (60 minutes) of forecasts were negative, so they mostly measure "always short" (amendment 6, B2).

| Horizon | IC (naive t) | Rank IC (t) | Out-of-sample R², uncentred | Hit rate | Sign rule, gross | Largest \|forecast\| |
| --- | --- | --- | --- | --- | --- | --- |
| 30 minutes | +0.016 (0.48) | −0.004 (−0.10) | −0.00006 | 47.9% | +0.08 bp | 0.25 bp |
| 60 minutes | +0.013 (0.25) | +0.008 (0.16) | −0.0005 | 46.9% | −0.34 bp | 0.63 bp |

The out-of-sample R² is negative at both horizons: the forecast predicted the realised return worse than a forecast of zero. The paper's R² was +0.2%.

## What the numbers say, plainly

- **The model barely forecast anything.** Cross-validation in the first training window chose heavy shrinkage (α 100 at 30 minutes, 31.6 at 60), within 0.02% and 0.12% of the error of a constant forecast. On the scoring sample:
  - the forecast's largest size was 0.25 bp at 30 minutes and 0.63 bp at 60, against a 6.95 bp round trip;
  - the predictor part's standard deviation was 0.03 bp and 0.15 bp;
  - the realised moves' standard deviation was 11.6 bp and 15.7 bp.
- **Even a strong forecast would struggle to pay.** Half of the realised 30-minute moves and 36% of the 60-minute moves were smaller than 6.95 bp outright, so even a perfect forecast would have sat out that share. Before the scoring sample, a planted forecast with an IC of 0.38 earned only +2.10 bp a trade at 30 minutes. The paper's R² of 0.2% corresponds to an IC of about 0.045. The xb ICs here (0.036 to 0.039) are that size and not significant, and an IC ten times larger would still barely clear the cost at 30 minutes.
- **The pseudo-out-of-sample months agree.** Information only, not a gate: over 2025-03 to 2025-08 (122 sessions) no forecast exceeded 6.95 bp either. The xb IC was +0.035 (clustered t 1.01) at 30 minutes and +0.053 (t 1.10) at 60, reading no direction at both.
- **Nothing large sits in the model.** The December refit's largest standardised coefficients are 0.006 bp per standard deviation at 30 minutes and 0.038 bp at 60, led at both horizons by the previous session's turnover and financials factors.
- **The IC is an upper bound for futures.** It is measured on the index, whose constituents' last trades lag at the five-minute scale and make index returns a little predictable in a way futures prices are not.

## What was and was not seen

- **Read for the first time by this look:** the NIFTY 50's own 30- and 60-minute returns, paired with a forecast, on the L40 selection sample (2025-09-01 to 2025-12-23, 78 sessions). The same sessions' stock returns had been read by L40, L46, L47 and the combination search. The NIFTY 100's 09:20→15:10 session returns over them were read by L48.
- **Not read by the scoring pass or the stage-0 run of record:** anything dated in 2026, because after amendment 6 both loaders stop before 2026-01-01. Stage-0 runs 1 to 3 had loaded, and dropped unused, the stock bars of 2026-01-01, a session before the project's held-out boundary. The held-out window (from 2026-01-02) was not touched. No target after 2025-12-23 was built.
- **Stage 0 read no target on or after 2025-09-01** in any of its four runs; its fits trained to 2025-07-24 at the latest.

## How this fits with what was known

- **The paper transfers in form, not in value.** Aleti, Bollerslev and Siggaard found SPY timing profitable because their cost was half a quoted spread, a fraction of a basis point. Here a NIFTY futures round trip is 6.95 bp, the design's 23 factors are a tenth of their 272, and 30 to 60 minutes of NIFTY moves are small against that cost. The lagged factor returns show no significant direction on these 78 sessions, and a cost this large would have hidden one of the paper's size anyway.
- **The family "intraday index timing" now holds two negative looks.** L48 (breadth and intermarket, the 09:20→15:10 session) and L51 (factor returns, 30 and 60 minutes). A future trial in this family counts both (amendment 6, N10).

## What went wrong, and what to read with care

- **Four stage-0 runs, not one.**
  - Run 1 halted on a mis-written coverage check: the 2024 Muhurat session ran in the evening (amendment 4).
  - Run 2 halted on the positive control at 30 minutes. It was then strengthened from a correlation of 0.5 to 0.7 (amendment 5). The review judged this a weakening of the promised halt, mitigated because it was dated, came before scoring, and the 0.5 result is reported every run; the verdict carries that caveat.
  - Run 3 passed; run 4, the run of record, repeated it after amendment 6.
  - All four records are committed.
- **The first review was not approved.**
  - The scoring pass wrote aggregates only, so the one run could not have been rechecked (B1).
  - The pre-registered IC would mostly have measured the negative monthly intercept (B2).
  - Amendment 6 fixed both before any scoring target existed: the per-decision rows, the models file and the xb headline above.
- **Times written by estimate were wrong** in the pre-registration's header and in amendments 4 to 6. Each was corrected to its commit time in a later note. The times in this file come from `date` and from the commits.
- **The trade is in futures but measured on the index.** The futures' basis and fills were not modelled, and the 0.5 bp a leg of slippage is an assumption, not a measurement.
- **Other caveats:** the universe is today's NIFTY 100 names that were members at the time (85 to 94 a session); sector labels are today's.

## For the owner

Nothing goes into Trader Sahab. Timing NIFTY futures on lagged factor returns, as specified, makes no trade on these sessions, and its forecasts carry no direction that a 6.95 bp round trip could pay for. Futures would in any case need about ₹1.7 lakh of margin a lot, beyond the current account.
