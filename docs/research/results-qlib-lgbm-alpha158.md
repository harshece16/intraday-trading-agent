# A LightGBM model on Qlib's Alpha158, trained on the project's own bars, does not rank the next intraday move past cost — research look L47: FAIL at all three horizons

**2026-09-30.** Pre-registration `prereg-qlib-lgbm-alpha158.md` (`dbdf872`, before any code), amendment 1 (`2a72ec3`, after the first independent review, before stage 0). Approved as decision D2b; code built by one agent and reviewed twice by another (not approved, then approved); stage 0 reviewed before training (D2f). On the owner's PC, CPU: stage 0 02:24–02:27, training once 02:33–02:34, the frozen hashes committed (`4dc366e`) before the one scoring pass 02:35–02:36. Records: `data/l47_stage0.json`, `data/l47_frozen.json`, `data/l47_result.json`. Nothing dated 2026 was read.

## Verdict

| Horizon | Top-minus-bottom spread, bp (t) | Bar | Rank IC (t) | Partial IC given m60 (t) | Halves, bp | Gate |
| --- | --- | --- | --- | --- | --- | --- |
| 15 min | +0.11 (0.22) | 33.26 bp, t > 2 | 0.018 (2.03) | 0.018 (1.95) | −0.19 / +0.42 | **fail** |
| 30 min | +0.03 (0.05) | 33.26 bp, t > 2 | 0.013 (2.16) | 0.013 (2.13) | −0.79 / +0.84 | **fail** |
| 60 min | +0.51 (0.64) | 33.26 bp, t > 2 | 0.014 (2.13) | 0.012 (1.81) | +1.83 / −0.81 | **fail** |

78 sessions, 43,362 stock-times. No survivor under BH within L47's three, and none under BH across the night's 24 forecast tests. **No trial is spent.** Research look L47 is closed.

## What the numbers say, plainly

- **The trained model ranks the next 15 to 60 minutes a little better than chance, and that is worth nothing in money.** Its rank correlation is about 0.013 to 0.018, with t just above 2, and it is not the last hour's move echoed back: controlling for that barely changes it. But the gap between its top and bottom fifth is 0.0 to 0.5 bp against 33.26 bp. The test could see gaps of about 1 to 1.6 bp.
- **It learned very little.** Training stopped after 12, 4 and 5 boosting rounds, because more rounds made the validation error worse. Its validation rank IC was 0.030, 0.020 and 0.024 (information only, as the pre-registration requires), about what it then showed on the test sessions.
- **Neither side pays alone.** The top fifth's mean move was −0.5 to −0.9 bp, the bottom fifth's −0.7 to −1.4 bp.
- **Ties did not drive the result.** With so few trees, predictions could have been coarse; each session had a median of 485 to 564 distinct predictions, and at most 0.15% of stock-times were tied at a quintile cut.

## What the bar asks for

Stage 0's positive control uses the true next-hour return as its own forecast. Even perfect foresight earns only 1.7 times the bar at 15 minutes, 2.4 times at 30 and 3.3 times at 60. A model would need to capture more than half of perfect foresight's spread at 15 minutes to pass. That is a statement about how strict an intraday long-short bar is after 33 bp of costs, not a defect in the pipeline.

## What to read with care

- **Coverage.** The cache holds 100 symbols, so about 87 of the 100 point-in-time members per training session had bars; the test sample is L40's fixed one.
- **Qlib's own benchmark pipeline differs.** Qlib's LightGBM benchmark feeds raw features with LightGBM's own missing-value handling and a z-scored label; the pre-registration chose `RobustZScoreNorm` on the features and `CSRankNorm` on the label. The code follows the pre-registration.
- **Precision.** The port computes in float64 and each window directly; Qlib casts to float32 and uses running sums. The differences are rounding, and stage 0's hand calculation confirmed the port to 1e-9.
- **An undefined-correlation rule** (amendment 1) set 462 correlation windows to missing where pandas returns a version-dependent value; it touched about two training rows.
- **`subsample` has no effect** in Qlib's published configuration, because `bagging_freq` is 0; the model is verbatim.

## Where this leaves the project

This is the first model trained on the project's own bars, and it closes this configuration: Qlib's Alpha158 with LightGBM at Qlib's parameters, on five-minute NIFTY 100 bars, scored against 15 to 60-minute moves. It does not close every trained model. With L40 and L46, eight forecasting models were tested tonight under one rule, and none comes within a tenth of the cost of trading on it.
