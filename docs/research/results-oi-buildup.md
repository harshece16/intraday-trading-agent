# Futures OI build-up, five sessions held: results. **FAIL (trial 207).** Over 89,232 LONG_BUILDUP events, 2009–2025, the mean net excess over the F&O universe was **−56.9 bp per entry session, Newey–West t −19.7**. Every year was negative, and the mechanism ran the wrong way: SHORT_COVERING beat LONG_BUILDUP. The line is closed.

**2026-11-08.** The pre-registration `prereg-oi-buildup.md` was merged in #321 (`0a06375`) before any F&O file or code existed. Then, in order:
- The aggregator and measurement script with Amendment 1, from the independent review, in #322 (`ffc6ea3`).
- The F&O history. The owner chose route (a) on 2026-11-07, and it was fetched on sahab-pc from 21:53 to 01:03 IST: 4,211 sessions, 0 bad files.
- Stage 0 run 1.
- Amendment 2: the holiday-expiry fix (#323) and the pre-run trial-check gaps, in #324 (`9bffa2c`).
- Stage 0 run 2, which passed every gate.

The trial ran once at 01:23 IST from `9bffa2c`. It is logged as entry 36 of `backend/data/backtest_trials.json`. No 2026 file was fetched, because the fetcher refuses the held-out window.

The OI file (`backend/data/fo_oi/`, 6.9 MB) and the 4,211 zips on sahab-pc's `/mnt/data` are not committed. These are: `data/trial207_result.json`, `data/trial207_stage0.json` (run 2) and `data/trial207_stage0_run1.json`.

## Verdict, in the pre-registration's terms

| Check | Rule | Result | |
| --- | --- | --- | --- |
| 1. Mean and t | mean session net excess > 0, NW t ≥ 2.24 | **−56.9 bp, t −19.74** (3,753 sessions) | **fail** |
| 2. Deflated Sharpe | ≥ 0.95 at N = 2 | 0.000 (session Sharpe −0.32) | **fail** |
| 3. Both halves | > 0 in 2009-01 → 2017-06 and 2017-07 → 2025-12 | **−56.2 bp** (t −12.56); **−57.6 bp** (t −15.85) | **fail** |
| 4. Last three years | > 0 from 2023 | **−52.5 bp** | **fail** |
| 5. Floor | mean event net excess ≥ 25 bp | **−53.2 bp** | **fail** |
| 6. Size | ≥ 100 events | 89,232 | pass |
| 7. Mechanism | LONG_BUILDUP − SHORT_COVERING > 0, NW t ≥ 1.65 | **−10.2 bp, t −2.95** (3,747 sessions) | **fail** |

The falsification row "fail on a half or the last three years: decayed, or never stable" applies. It says FAIL and closed. No row was written for a negative mean, because the pre-registration did not expect one. "Pass 1–6, fail 7" does not apply.

## What it means, plainly

**1. There is no gross edge for costs to take.** From the entry open to the fifth close, a LONG_BUILDUP event earned +2.2 bp gross. The equal-weighted F&O universe earned about +10 bp over the same sessions, so the gross excess is about −8 bp.
- Trial 126's charges plus 10 bp a side of slippage cost 45 bp a round trip. That is the rest of the −53 bp.
- Unlike trial 206, which had a +50 bp gross pop eaten by costs, nothing here is worth collecting at any cost.
- A cheaper vehicle cannot rescue it. Stock futures cost a few bp instead of 45, but they would still carry the −8 bp. Options add decay.

**2. The reel's mechanism is backwards in this sample.** Price up with OI up is supposed to mean fresh longs and continuation. Price up with OI down is supposed to mean short covering that fades.
- On the same entry sessions, SHORT_COVERING beat LONG_BUILDUP by 10 bp, t −2.95.
- SHORT_COVERING on its own is also negative net (−44.5 bp per event, gross +12.4 bp against a +11.5 bp universe).
- Neither state is a buy signal. Turning "buy short covering" into a trial now would be choosing a rule after reading its return. It would need its own pre-registration, and its gross excess of about +1 bp leaves nothing to test.

**3. It is not a regime story.** All 17 years are negative, from −42 bp (2011) to −81 bp (2015), and each has |t| ≥ 2.8. The two halves agree to within 1.5 bp.

| | LONG_BUILDUP | SHORT_COVERING |
| --- | --- | --- |
| Events (entry sessions) | 89,232 (3,753) | 84,456 (3,770) |
| Mean session net excess, NW t | −56.9 bp, −19.74 | −45.8 bp, −22.65 |
| Mean / median event net excess | −53.2 / −74.9 bp | −44.5 / −67.5 bp |
| Mean gross / net per event | +2.2 / −43.2 bp | +12.4 / −33.0 bp |
| SD per event, win rate | 465 bp, 41.3% | 448 bp, 42.0% |
| Excess at 1× / 2× / 3× cost | −53.2 / −98.6 / −144.0 bp | −44.5 / −89.9 / −135.3 bp |

## What went wrong, and what was checked

- **Holiday expiries (#323).** The April 2009 and April 2014 files list their expiries on market holidays. Run 1 missed both, so the next session's dOI would have carried the contract roll. Stage 0 listed them as months with no expiry day, and Amendment 2 fixed this before any return was read. Run 2 has 210 expiry days instead of 208. The fix cut LONG_BUILDUP events from 89,268 to 89,232.
- **Missing F&O files: 4 of 4,215 cash sessions (0.09%).** Two are Sunday special sessions (2010-05-16, 2012-11-11). Two are weekdays the archive has under neither file name (2013-10-09, 2021-03-30). The session after each is dropped, not compared across the gap.
- **OI units across the July 2024 switch to the UDiFF format.**
  - In both formats, the file's own change-in-OI column matches OI_t − OI_{t−1} (old format 99.86% of symbol-days, UDiFF 100%).
  - The median dOI across the first old → UDiFF pair of sessions is +0.55%, so both formats count shares.
- **Six single-stock early expiries** from corporate actions (IDFC, ITC, SIEMENS, ABFRL, TATAMOTORS, HINDUNILVR) flag the whole day, as written.
- **478 zero-share drops in each state.** These are MRF and PAGEIND above the ₹50k ticket: 469/470 and 9/8. The equal totals are a coincidence.
- **The overlap rule drops about half of the LONG_BUILDUP signal-days** (88,726): a stock in the state on consecutive days is held once. This was written into the prereg.
- **The trial-check gate before the run** added a one-run guard, the trial-log entry and the cost multiples. No return had been read.

## What next

Nothing in this trial supports buying on OI build-up, in cash or in F&O. The family's second slot is unspent. The prereg names its most likely use: the short-side states (SHORT_BUILDUP, LONG_UNWINDING) as put buys, which need option prices this repo does not have. That needs its own pre-registration and data first. Nothing goes to paper or live from this trial.
