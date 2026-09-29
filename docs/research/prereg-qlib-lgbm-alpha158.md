# Pre-registration — does a LightGBM model on Qlib's Alpha158 factors, trained on the project's own five-minute bars, rank the next intraday move? (research look L47; a trial only if it clears)

**Written 2026-09-30 at about 01:10 IST, before any L47 code exists.** Approved by the overnight decision agent as decision D2b (`decisions/log-2026-09-30.md`), with the conditions this text turns into rules. Background: `predictive-tools-sweep-2026-09-29.md`, part B. Seen before this was written: L40's result (Kronos, FAIL) and the first L46 model's (Chronos-Bolt, FAIL). Neither shapes anything below: the design is the sweep's, written before either.

**What it is not.** Not a strategy, not a backtest, not a trial. Nothing enters the engine. It is kept outside the combination search (trials 128 to 202), whose grid is fixed.

## 1. Hypothesis

A gradient-boosted model on Qlib's standard price and volume factors, trained on NIFTY 100 five-minute bars before the sample, ranks the signed return over the next 15, 30 or 60 minutes by more than the round-trip cost. Expected answer: no. This is the first model trained on the project's own bars; the null it would give closes this configuration, not every trained model.

## 2. Features, fixed

- **Qlib's Alpha158**, default configuration of `Alpha158DL.get_feature_config()` in `qlib/contrib/data/loader.py` at Qlib commit **`be725493eb1a6bbb42bf11b37aa7669f59610ff1`**: the 9 k-bar features; price features OPEN0, HIGH0, LOW0 and VWAP0; and the rolling operators at windows 5, 10, 20, 30, 60. Ported to plain pandas, expression by expression; no other port is used.
- **Windows are bars**, on each stock's continuous series of closed five-minute bars across sessions (the §42 closed-bar rule): "5" means the last five closed bars.
- **VWAP0 is dropped**: Kite's five-minute bars carry no VWAP. That leaves **157 features**. No other feature is added.

## 3. Training data, fixed

- **Rows:** point-in-time NIFTY 100 members (`nifty100_membership.set_asof`) in the Kite cache, at every closed five-minute bar whose close falls from 09:45 to 13:30, on sessions from **2024-09-20 to 2025-08-14**.
- **Label:** `kronos_feature_ic.target_bp` for k = 3, 6 and 12 (the next bar's open to the close k bars later), one model per horizon; rows whose target would leave the session are dropped. The label is ranked across stocks at each timestamp, as Qlib's `CSRankNorm` does.
- **Normalisation:** Qlib's `RobustZScoreNorm` on the features, with its statistics fitted on the training segment only, clipped at ±3; missing values filled with 0.
- **Split:** training; a **5-session purge**; validation = the last **40 sessions** up to 2025-08-14, used only to stop training early. The L40 sample starts on 2025-09-01, about nine sessions after the last validation label. The L40 sample never enters fitting, early stopping or the normaliser.
- **The 2026 window is not read**: the loader filters to timestamps before 2026-01-02 and asserts the latest timestamp it read.

## 4. Model, fixed

One LightGBM per horizon with Qlib's published Alpha158 LightGBM hyperparameters (`examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml` at the same commit), verbatim: loss mse, colsample_bytree 0.8879, learning_rate 0.2, subsample 0.8789, lambda_l1 205.6999, lambda_l2 580.9768, max_depth 8, num_leaves 210. Up to 1,000 rounds with early stopping after 50 on validation l2. CPU; `deterministic = true`; seed 123; `num_threads` fixed at 16 (the PC's threads) and recorded. No tuning, and no refit on training plus validation.

## 5. The test, fixed

The frozen models score exactly L40's stock-times (`kronos_feature_ic.build_samples` on L40's selection: 78 sessions, 43,362 stock-times). The model's prediction for a horizon is that horizon's feature. Statistics are the harness's, unchanged (`session_stats`, `summarise`), including partial IC given m60.

**Gate, per horizon: L40 §8 exactly** — quintile spread above 33.26 bp with t > 2 over at least 60 sessions, positive in both halves, partial IC given m60 positive with t > 2 — **and** Benjamini–Hochberg at q = 0.10 both across L47's 3 tests and across the night's **24** forecast tests (L40's 3, L46's 18 and L47's 3, voids at p = 1). A pass earns a separately pre-registered trial in a new family, "model trained on the project's bars", judged at N_family by the owner's bar of 2026-09-26, and confirmed on unseen sessions before anything else.

## 6. Stage 0, on the PC, each check a halt

1. The feature count is 157, and the Qlib commit is recorded.
2. **Look-ahead proof:** for at least 200 random stock-times across training, validation and test, the features are bit-identical with every bar after t removed from the source.
3. **Hand calculation:** at least one feature from each operator family (k-bar; ROC; MA; STD; BETA, RSQR, RESI; MAX, MIN, QTLU, QTLD; RANK, RSV; IMAX, IMIN, IMXD; CORR, CORD; CNTP, CNTN, CNTD; SUMP, SUMN, SUMD; VMA, VSTD, WVMA; VSUMP, VSUMN, VSUMD) on 5 stock-times matches a direct computation to 1e-9.
4. **Purge assertions:** the latest label end in training and validation is at least 5 sessions before the first L40 session; the gap between training and validation is at least 5 sessions; the normaliser's statistics come from training only; no timestamp on or after 2026-01-02 was read.
5. **Adjustment check:** L40's fetch-run check, extended to the training window; stock-sessions straddling a step are dropped and listed.
6. **L40's sample reproduced:** 78 sessions and 43,362 stock-times.
7. **Positive control, on validation only:** the target used as the feature gives a spread far above the bar, and the recomputed m60 equals the harness's.

A second agent, not the builder, reviews the code against this text and the stage 0 output before the models are frozen. A finding is fixed by a dated amendment before any test-sample number exists.

## 7. One run

Training runs once; a refit only for a crash or a declared bug before freezing, both recorded. The three model files and the normaliser's statistics are hashed, and the hashes are committed and pushed **before** the scoring pass reads any target in the L40 sample. The validation IC is recorded as information; it is not a gate and cannot change the design. The scoring pass runs once.

**Cut-off:** if the scoring pass has not started by 07:30 IST on 2026-09-30, it is not started; whatever exists is committed, and L47 waits for the owner under the same one-run rule.

## 8. Trial accounting

Research look **L47**. No trial is spent unless it clears.

## Amendments

1. **2026-09-30, 02:17 IST, after the independent review of the L47 code (head 61bf565, NOT APPROVED, two blocking findings) and before stage 0 or any training.** No L47 number exists on project data. The review's findings are fixed as follows.
   - **B2, the port and Qlib's handling of infinite values.** Qlib runs Mean, Sum, Std, Corr, Max, Min, Quantile, Rank and the IdxMax/IdxMin apply through pandas' rolling functions, and pandas (`Window._prep_values`) treats +inf and -inf as missing. The port now does the same. This matters for CORD: `Log($volume/Ref($volume, 1)+1)` is +inf after a zero-volume bar. That pair is now skipped, as in Qlib, instead of turning the whole window NaN. The inputs to Corr's 2e-5 std masks are treated the same way. Slope, Rsquare and Resi are unchanged: Qlib's Cython sees their raw input, the close. The §6.3 hand calculation now treats non-finite values as missing, as pandas does.
   - **B2, undefined correlations.** Corr is NaN when the paired values of either input are all equal, because the correlation is undefined there. Qlib's mask catches that case unless a skipped pair hides it. When it does not, pandas returns a value that depends on its version: ±inf under pandas 2.3.3, and 0 or about 1e-5 under 3.0.6 (both measured on synthetic bars). The port's NaN is filled with 0 by §3's normaliser.
   - **B2, float error.** Where both are finite, the port's Corr differs from pandas' only by pandas' float error (its mean(xy) − mean(x)·mean(y) cancels): on synthetic bars, up to 1.7e-4 (CORD5, windows with few pairs) and 7e-7 (CORR10), falling to about 6e-9 at 20 bars and 1.2e-9 at 30 bars. §6.3's 1e-9 check requires the exact value. Stage 0 now records this comparison on the project's bars as information, not as a check: CORR and CORD against Qlib's own pandas computation, counted by kind, with the number of zero-volume bars.
   - **B1, one-run holes.**
     - The scoring pass writes `l47_result.json` with status STARTED once every refusal has passed and before any bar or target is read. It refuses to run if that file exists with any status, unless the owner gives `--owner-approved-rescore "<reason>"`, which is recorded.
     - Training refuses, even with `--refit-reason`, once `l47_frozen.json` is committed, or once `l47_result.json`, `l47_rows.jsonl` or `l47_rows.jsonl.tmp` exists: no refit after freezing (§7).
     - Training writes `l47_train_started.json` (time and environment) before the first `lgb.train`. Any earlier attempt (that marker, a model file, or an uncommitted frozen record) needs `--refit-reason`, which is recorded.
   - **Determinism.** LightGBM runs with `force_col_wise = true`. This is an execution option, not a model hyperparameter. LightGBM's documentation asks for it (or `force_row_wise`) with `deterministic = true`, because otherwise a timing test at construction chooses the histogram layout.
   - **Extra refusals before scoring:**
     - `l47_stage0.json` must be committed and its SHA-256 must equal the one `l47_frozen.json` recorded at training.
     - All six L46 results must exist with a final status (DONE or VOID); a missing one means L46 has not finished.
     - lightgbm must be installed.
   - **Extra halts after loading, before any target is scored:**
     - The adjustment-dropped stock-sessions must equal L40's (`kronos_l40_result.json`, `stage0.adjustment.dropped_stock_sessions`).
     - When L40's rows file of record is given (`--l40-rows`; the PC script passes it), the per-session stock-time counts must equal its counts.
   - **Information in the result:** each horizon's best iteration, the distinct predictions per session (median, min), and the share of stock-times tied across the harness's quintile cut points. The harness is unchanged.
   - **PC script:** it checks that the clone is on `research/overnight-2026-09-30` before pulling. It pins lightgbm 4.7.0, pandas 3.0.6, numpy 2.4.6 and scipy 1.17.1, the versions installed. It re-checks that no L46 model is running immediately before each mode runs.

   Nothing in the features, labels, split, model parameters, test or gate changes. B2 makes the port match Qlib, which is what §2 already says.
