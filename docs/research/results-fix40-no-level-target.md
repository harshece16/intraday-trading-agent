# Issue #40 — no formulaic target when no level lies beyond, before/after backtest

**2026-09-23.** A declared bug-fix pair. The pass rule, window and harness were committed in the script's docstring before the run (`backend/research/fix40_no_level_target.py`, commit `d79eeb9`). One run, no re-run.

## What changed

When no support/resistance lay beyond the entry, the checklist aimed at a **gross** `rrr_without_level × risk` target (2.0) and judged it **net** of costs. The fix gives such a setup **no target**, so it fails the R:R item. It can only remove trades.

## #40's premise was wrong, and it was measured

#40 said the branch "can never pass". Across the whole journal, **920 evaluation-sides took it, 186 cleared R:R (net median 1.14, max 1.92) and 9 passed the full checklist**. The 1-ATR stop floor (§48) widened stops enough that the cost fraction sometimes fell below the 0.2 the arithmetic needs. No paper trade ever used it.

The fix that #40 proposed, placing the target at the distance that nets 2.0, would have made the branch pass **more** often: a loosening. It was not taken.

## Setup

Identical to fix74 except the arm variable:
- run_backtest(), NIFTY 100, scanner top 5/day, confidence gate off, `config.COSTS`, cost_pct 0.166 in both arms.
- **Selection only**: 317 sessions, 2024-09-24 → 2026-01-01. **The 176 held-out sessions were never loaded.**
- The window starts one day later than fix74's because `DAYS = 730` is counted from the run date.
- Halves: 158 / 159 sessions, split at 2025-05-16.

**Consistency check:** this baseline reproduces fix74's *fixed* arm exactly in both halves (33 trades at −0.3544R, 12 at +0.0322R), as it should, since it is the same configuration.

## Result — PASS (worse in the first half only)

| Half | Arm | Trades | Net R/trade | t | 95% CI | Win | Net ₹ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| First | baseline, 2R gross | 33 | −0.354 | −1.44 | [−0.84, +0.13] | 30.3% | −2,423 |
| First | **no target** | **31** | −0.360 | −1.38 | [−0.87, +0.15] | 29.0% | −1,978 |
| Second | baseline, 2R gross | 12 | +0.032 | +0.07 | [−0.86, +0.92] | 41.7% | +476 |
| Second | **no target** | **7** | +0.089 | +0.13 | [−1.25, +1.43] | 42.9% | +284 |

## What this does and does not show

- **7 of 45 trades removed (16%)**, which is the intended effect.
- **No measurable change in expectancy.** The first half moves −0.006R and the second +0.057R on 7 trades; every interval spans zero. This is noise, and it is not evidence either way.
- The ship decision rests on correctness, not on this backtest: a target should be a level the checklist can name, and a gross multiple judged net was a unit error.

Counted as **trials 38 and 39**. 3e and 3f have not run, and their numbers are assigned at run time.
