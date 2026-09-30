# Pre-registration — do the five newest forecasting models rank the next intraday move past cost, on sessions after they were released? (research look L52, forward; a trial only if one clears)

**Written 2026-09-30 at about 20:15 IST, before any of the sessions it scores exists.** The owner asked on 2026-09-30 to complete every open research item. The predictive-tools sweep (`predictive-tools-sweep-2026-09-29.md`) recommended that the models released after the L40 selection sample be judged forward only, on sessions after their release, and not on the 2026 held-out window. This fixes that test now.

**Seen before this was written:** L40 (Kronos) FAIL; L46 (six zero-shot models) FAIL 18 of 18; L47 (LightGBM on Alpha158) FAIL; the 75-combination search FAIL; one day of the Kronos live shadow (2026-09-30). None of the five models below has been run on any project data.

**What it is not.** Not a strategy, not a trial. Nothing enters the engine.

## 1. The five models, pinned now

The revision is the latest on Hugging Face at the time of writing. It is fixed: later revisions are not used, so no model can have seen a scored session.

| Model | Repository | Revision | Revision dated | Licence |
| --- | --- | --- | --- | --- |
| Chronos-2 | `amazon/chronos-2` | `29ec3766d36d6f73f0696f85560a422f50e8498c` | 2026-06-05 | Apache-2.0 |
| TiRex-2 | `NX-AI/TiRex-2` | `05e5b26db52bfb256f1ae1bdf785589850482de3` | 2026-07-21 | Apache-2.0 |
| Toto 2.0 313m | `Datadog/Toto-2.0-313m` | `a7bab288f5e95f8606f8306f86659357e1c001ef` | 2026-06-04 | Apache-2.0 |
| Granite PatchTST-FM r2 | `ibm-granite/granite-timeseries-patchtst-fm-r2` | `b125275f9204d37cbb81fe47b9cf5e08a521e829` | 2026-09-09 | OpenMDW-1.0 |
| TimesFM-3.0 | `google/timesfm-3.0-pytorch` | `43046b85ec22d584a13f8098c2ed39c889e129c2` | 2026-09-02 | Non-commercial (research only; never near the engine) |

- **Input:** the close of the last 512 closed five-minute bars, univariate, for every model (no covariates; the same input as L46).
- **Output:** the median (0.5 quantile) of the next 12 bars' forecast closes; for a model that only gives a point forecast, the point forecast. Features `f15`, `f30`, `f60` as L40 §5.
- **Device:** the owner's PC GPU or CPU, recorded; fp32.

## 2. Sample

- **Sessions from 2026-10-01**, the first session after this text, through the 60th session with data. At about 22 sessions a month, that is late December 2026.
- **The lookback** may reach back into the sessions of 2026-09-21 to 2026-09-30 as input only; no target before 2026-10-01 is scored.
- **Universe and decision times:** point-in-time NIFTY 100 members with bars, at L40's six decision times (09:45 to 13:30). Kite five-minute bars fetched after the 60th session.
- **The 2026 held-out window (2026-01-02 to 2026-09-20) is not read.**

## 3. Statistics and gate

L40's §7 statistics and §8 gate, per model and horizon: quintile spread above 33.26 bp with t > 2 over at least 60 sessions, positive in both halves, partial IC given the last hour's return positive with t > 2, and **Benjamini–Hochberg at q = 0.10 across the 15 tests** (five models × three horizons). A void model counts at p = 1.

## 4. Stage 0, before any target is read

Per model: the documented call on a synthetic series; the pinned revision loads and holds weights; the look-ahead proof on 20 stock-times; timing; the adjustment check on the new fetch; coverage (at least 30 sessions a half). A model that cannot run is void and is not replaced. The code is written and reviewed by an agent that did not write it, before stage 0.

## 5. One run

One scoring pass per model, after the 60th session. A re-run only for a crash before any statistic, or a declared bug, both recorded.

## 6. Trial accounting

Research look **L52**. No trial is spent unless a model clears; a pass earns a separately pre-registered trial in the family "foundation-model price forecast", judged at N_family.
