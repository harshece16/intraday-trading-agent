# Six zero-shot foundation models do not rank the next intraday move past cost — research look L46: FAIL, 18 of 18 tests

**2026-09-30.** Pre-registration `prereg-tsfm-family.md` (`6921f08`, before L40's result was read), amendments 1 and 2 (after smoke tests on a synthetic series, before any model ran on project data). Harness `tsfm_family_ic.py` on L40's functions. Each model's stage 0 and one pass ran on the owner's PC (RTX 3060 Ti), 00:53 to 02:21 IST. Records: `data/l46_<model>_stage0.json`, `data/l46_<model>_result.json`, `data/l46_family_gate.json`. Nothing dated 2026 was read. Decisions: `decisions/log-2026-09-30.md`.

## Verdict

**No model clears the gate at any horizon.** The family gate (L40 §8 per model and horizon, Benjamini–Hochberg at q = 0.10 across all 18) has no survivor. **No trial is spent.**

| Model | Horizon | Sessions | Top-minus-bottom spread, bp (t) | Rank IC (t) | Partial IC given m60 (t) | Gate |
| --- | --- | --- | --- | --- | --- | --- |
| Chronos-Bolt base | 15 min | 78 | −0.9 (−2.44) | −0.0187 (−3.09) | −0.0175 (−2.92) | fail |
| Chronos-Bolt base | 30 min | 78 | −2.3 (−3.94) | −0.0244 (−3.76) | −0.0231 (−3.72) | fail |
| Chronos-Bolt base | 60 min | 78 | −1.7 (−1.84) | −0.0195 (−2.76) | −0.0196 (−2.82) | fail |
| TimesFM-2.5 | 15 min | 76 | −0.5 (−1.19) | +0.0004 (0.06) | −0.0006 (−0.10) | fail |
| TimesFM-2.5 | 30 min | 76 | −1.4 (−2.20) | −0.0057 (−0.84) | −0.0083 (−1.29) | fail |
| TimesFM-2.5 | 60 min | 76 | −1.7 (−1.84) | −0.0015 (−0.20) | −0.0081 (−1.12) | fail |
| Moirai 2.0 R-small | 15 min | 78 | −0.8 (−1.75) | −0.0099 (−1.48) | −0.0128 (−1.97) | fail |
| Moirai 2.0 R-small | 30 min | 78 | −1.4 (−2.33) | −0.0111 (−1.79) | −0.0146 (−2.39) | fail |
| Moirai 2.0 R-small | 60 min | 78 | −1.9 (−2.27) | −0.0118 (−1.77) | −0.0166 (−2.44) | fail |
| FlowState-r1 | 15 min | 69 | −1.1 (−1.87) | −0.0063 (−0.74) | −0.0100 (−1.26) | fail |
| FlowState-r1 | 30 min | 69 | −1.3 (−1.61) | −0.0010 (−0.14) | −0.0084 (−1.22) | fail |
| FlowState-r1 | 60 min | 69 | −1.5 (−1.31) | +0.0011 (0.14) | −0.0054 (−0.73) | fail |
| TiRex v1 | 15 min | 78 | +0.1 (0.12) | +0.0006 (0.08) | −0.0011 (−0.15) | fail |
| TiRex v1 | 30 min | 78 | −1.6 (−2.96) | −0.0097 (−1.44) | −0.0138 (−2.05) | fail |
| TiRex v1 | 60 min | 78 | −1.2 (−1.26) | −0.0057 (−0.79) | −0.0091 (−1.27) | fail |
| Sundial base 128m | 15 min | 78 | −0.3 (−0.49) | +0.0040 (0.54) | +0.0014 (0.18) | fail |
| Sundial base 128m | 30 min | 78 | −0.5 (−0.71) | +0.0043 (0.62) | −0.0030 (−0.44) | fail |
| Sundial base 128m | 60 min | 78 | +0.5 (0.49) | +0.0115 (1.55) | +0.0039 (0.53) | fail |

The bar is a spread above +33.26 bp with t > 2. TimesFM-2.5 and FlowState-r1 use fewer sessions because their first published weights postdate 2025-09-01 (amendment 1's rule); 2025-10-21, the one-hour Muhurat session, has no stock-times for any model.

## What the numbers say, plainly

- **Every model fails by more than thirty basis points.** The best spread of the 18 is +0.5 bp; the bar is +33.26 bp.
- **Sixteen of eighteen spreads are negative.** These models' forecasts, on the whole, rank the next hour slightly the wrong way round: the stocks they expect to rise do a little worse than the ones they expect to fall. The magnitude, −0.5 to −2.3 bp, is still a small fraction of what one leg costs, so reversing them would not pay either. A reversed signal was not pre-registered and is not tested here.
- **Controlling for the last hour's move makes most of them more negative.** A generic forecaster extrapolates recent movement; over 15 to 60 minutes these stocks lean slightly towards reversal. That reading is an interpretation, not a tested claim.

## Stage 0, per model

All six passed: the documented call on a synthetic series, revisions dated before the sample (or the moved window of amendment 1), 20 of 20 lookahead forecasts identical, timing, the adjustment check, and coverage.

| Model | Revision used | Dated | Seconds a forecast (RTX 3060 Ti) | Stock-times |
| --- | --- | --- | --- | --- |
| Chronos-Bolt base | 474f187 | 2025-02-17 | 0.002 | 43,362 |
| TimesFM-2.5 | d35e0e4 | 2025-09-02 | 0.092 (eager, no Triton) | 42,294 |
| Moirai 2.0 R-small | 5e57b91 | 2025-08-11 | 0.001 | 43,362 |
| FlowState-r1 | 533ab8d | 2025-09-11 | 0.003 | 38,556 |
| TiRex v1 | fa77b31 | 2025-06-06 | 0.017 | 43,362 |
| Sundial base 128m | 2f40cf7 | 2025-08-08 | 0.005 (mean of 3 samples) | 43,362 |

## What went wrong, and what to read with care

- **Three adapters failed their first smoke test** on a synthetic series, before any project data was read: TimesFM-2.5's and FlowState-r1's earliest Hugging Face revisions are README-only commits, and TiRex's loader wanted a repository name. Amendment 1 fixed the rule (the earliest revision that holds weights) and the loader. TimesFM-2.5's checkpoints keep query, key and value separate while the current library fuses them; amendment 2 fuses them in the library's own order when loading, an exact rearrangement. FlowState-r1's median sits in `quantile_outputs`.
- **TimesFM-2.5 ran eagerly** because `torch.compile` needs Triton, which Windows lacks. The same graph, slower.
- **Two environments first installed CPU-only torch** because their packages pin old versions; the same versions with CUDA were installed before any run.
- **The PowerShell run script failed to parse on its first start** (`"$m:"`), before any model ran; decision D1b.

## Where this leaves the family

With L40's Kronos, seven zero-shot forecasting models have now been tested on the project's own five-minute NIFTY 100 bars under one pre-registered rule, and none ranks the next 15, 30 or 60 minutes by even a tenth of the cost of trading on it. The newest models (Chronos-2, TiRex-2, Toto 2.0, Granite PatchTST-FM, TimesFM-3.0) postdate the sample and could only be judged forward (`predictive-tools-sweep-2026-09-29.md`).
