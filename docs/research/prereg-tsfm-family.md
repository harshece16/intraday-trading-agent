# Pre-registration — do six zero-shot time-series foundation models rank the next intraday move? (research look L46; a trial only if one clears)

**Written 2026-09-30 by 00:14 IST (its commit), before the result of L40 was read, and before any of these six models has been loaded or run on project data or any other.** Background: `predictive-tools-sweep-2026-09-29.md` (part A). Owner's instruction, 2026-09-29: "if not then test the other models ... lets hope atleast 3 models are run". This look runs whatever L40's result is.

**What it is not.** Not a strategy, not a backtest, not a trial. No order path, no config, no gate changes.

## 1. Hypothesis

At least one of six generic time-series foundation models, used zero-shot on the close series of NIFTY 100 five-minute bars, produces a forecast whose cross-sectional rank predicts the signed return over the next 15, 30 or 60 minutes by more than the round-trip cost. Expected answer: no, for every model, as for the family's published record.

## 2. The six models, fixed, in the order they run

| Order | Model | Hugging Face repository | Output used |
| --- | --- | --- | --- |
| 1 | Chronos-Bolt base | `amazon/chronos-bolt-base` | median quantile |
| 2 | TimesFM-2.5 | `google/timesfm-2.5-200m-pytorch` | point forecast (`forecast()`, no covariates) |
| 3 | Moirai 2.0 R-small | `Salesforce/moirai-2.0-R-small` | median quantile |
| 4 | FlowState-r1 | `ibm-granite/granite-timeseries-flowstate-r1` | median quantile; `scale_factor` 1.0 unless its documentation fixes a value for 5-minute data, recorded either way |
| 5 | TiRex v1 | `NX-AI/TiRex` | median quantile |
| 6 | Sundial base 128m | `thuml/sundial-base-128m` | mean of 3 generated samples, seeds fixed as L40 §2 |

- **Input:** the close of the last 512 closed five-minute bars, as a univariate series. No covariates, for any model (TimesFM #338 and Moirai #224 both concern the covariate path).
- **Output:** the 12 forecast closes. Features `f15`, `f30`, `f60` exactly as L40 §5.
- **Revisions:** for each model, the latest Hugging Face revision dated before 2025-09-01. If none exists, L40 §2's moved-window rule applies to that model alone: its sessions start after its earliest revision's date, and it is **void** if fewer than 60 sessions remain before 2026-01-02. By the sweep's dates, Chronos-Bolt, Moirai 2.0, TiRex v1 and Sundial have revisions before the cutoff; TimesFM-2.5 (2025-09-02) and FlowState-r1 (2025-09-10) move to about 77 and 71 sessions. Stage 0 records the actual revisions.
- **Device:** the owner's PC (RTX 3060 Ti), CUDA, fp32. A separate Python environment per model is allowed where their packages conflict; every package version is recorded.
- A model that cannot be installed, or fails stage 0, is **void** and is not replaced.

## 3. Data, decision times, targets, statistics

Identical to `prereg-kronos-feature-ic.md` §3, §4, §6 and §7, and to the run of record's sample (79 sessions, 2025-09-01 to 2025-12-23, 43,362 stock-times), except where a model's moved window shortens its sessions. The same harness functions compute the samples, targets and statistics (`kronos_feature_ic.build_samples`, `target_bp`, `m60_bp`, `session_stats`, `summarise`), so the only thing that differs between L40 and each model is the forecaster.

## 4. Gate, fixed now

Per model and horizon, L40 §8 exactly: quintile spread above 33.26 bp with t > 2 across at least 60 sessions, positive in both halves, and partial IC given m60 positive with t > 2. **Multiple comparisons: Benjamini–Hochberg at q = 0.10 across all 18 tests (six models × three horizons)**, on the raw quintile-spread p-values. The partial-IC condition sits outside the family, as in L40 amendment 1. Void models are counted in the family at p = 1, so a void cannot make the bar easier.

A model and horizon that clears earns a trial pre-registered separately, in the family "foundation-model price forecast", judged at N_family by the owner's bar of 2026-09-26, and confirmed before anything reaches even the review queue.

## 5. Stage 0, per model, before any IC is computed

1. **The model runs as its authors document:** the package's own example forecast on a synthetic series returns finite values of the right shape.
2. **Revisions** recorded; §2's rule applied.
3. **Lookahead:** 20 stock-times, forecast identical with and without later bars present (the harness's check).
4. **Timing:** 200 forecasts; recorded, for information.
5. **Adjustment check:** as L40 (one fetch run; no stock-session dropped on the run of record).
6. **Coverage:** at least 30 sessions in each half, else void.

## 6. One run each

One IC pass per model. A re-run only for a crash before any statistic, or a declared bug with both runs recorded.

## 7. Trial accounting

Research look **L46**. No trial is spent unless a model clears, and then the trial is pre-registered separately.

## Amendments

1. **2026-09-30, 00:36 IST, after a smoke test on a synthetic series and before any of the six models was run on project data.** The smoke test (`--smoke`, which reads no project data) showed that for TimesFM-2.5 and FlowState-r1 the earliest revision on Hugging Face is an initial commit that holds only a README: no model. §2's "earliest revision" is read as **the earliest revision that holds the model's weights** (a file ending `.safetensors`, `.bin`, `.ckpt` or `.pth`), and "latest revision before the cutoff" likewise counts only revisions with weights. For TimesFM-2.5 that is `d35e0e4`, dated 2025-09-02, the same day, so its window is unchanged; for FlowState-r1 it is `533ab8d`, dated 2025-09-11, one day later than the sweep's date. The same smoke test showed TiRex's loader takes the repository name and a revision, not a file path; the adapter was corrected. Chronos-Bolt, Moirai 2.0 and Sundial passed the smoke test unchanged. Nothing else changes.
2. **2026-09-30, 00:42 IST, after a second smoke test, before any model ran on project data.** TimesFM-2.5's published checkpoints (every revision from 2025-09-02 to 2025-09-29 holds identical tensors, checked one by one) store the attention's query, key and value projections as three matrices; the current `timesfm` code fuses them into one projection and splits its output in the order query, key, value. The adapter concatenates the three matrices in that order when the checkpoint is loaded. This is an exact rearrangement of the same weights, not a change to the model. FlowState-r1's median now sits in `quantile_outputs` (nine quantiles, 0.1 to 0.9), not `prediction_outputs`, which returns the mean; the adapter reads the 0.5 quantile, as §2 says. Nothing else changes.

