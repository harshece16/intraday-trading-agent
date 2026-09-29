# Kronos, zero-shot, does not rank the next intraday move past cost — research look L40: FAIL at all three horizons

**2026-09-30.** Pre-registration `prereg-kronos-feature-ic.md` (`0657a0e`), amendments 1 to 4. Harness `kronos_feature_ic.py` (unchanged since `8d709c6`) and `kronos_l40_launch.py`. Stage 0 on the PC (`kronos_l40_stage0_pc.json`), then the one measurement pass on the PC's GPU at three samples a forecast, 22:56 on 2026-09-29 to 00:49:50 on 2026-09-30: the run of record under amendment 4. Record: `data/kronos_l40_result.json`. Nothing dated 2026 was read.

## Verdict, in the pre-registration's terms

| Horizon | Top-minus-bottom quintile spread | t | Bar | Rank IC (t) | Partial IC given m60 (t) | Halves | Gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 15 minutes | +0.27 bp | 0.63 | 33.26 bp, t > 2 | 0.010 (1.57) | 0.008 (1.36) | +0.34 / +0.20 | **fail** |
| 30 minutes | +0.51 bp | 0.78 | 33.26 bp, t > 2 | 0.018 (2.61) | 0.011 (1.74) | −0.41 / +1.43 | **fail** |
| 60 minutes | +1.61 bp | 1.43 | 33.26 bp, t > 2 | 0.022 (2.86) | 0.013 (1.90) | −0.36 / +3.57 | **fail** |

78 sessions scored, 43,362 stock-times. Benjamini–Hochberg at q = 0.10 over the three: no survivor (spread p 0.53, 0.44, 0.15). **No trial is spent.** Research look L40 is closed.

## What the numbers say, plainly

- **The forecast is not worth trading.** Going long Kronos's top fifth and short its bottom fifth would have earned 0.3 to 1.6 bp a pair before costs. The pair costs 33.26 bp. The shortfall is twenty to a hundred times the edge.
- **The test could see a small effect.** The smallest spread detectable at t = 2 was 0.9, 1.3 and 2.3 bp. An edge of the size needed would have shown clearly. This is a measured absence, not a lack of power.
- **There is a faint, real ranking signal at 30 and 60 minutes.** The rank correlation is positive in two sessions out of three and its t is 2.6 and 2.9. Between a fifth and two fifths of it is the last hour's move echoed back: controlling for that, the IC falls by 18%, 41% and 38%, and its t falls below 2 at every horizon. It is the kind of signal a statistics test notices and a trading account does not.
- **Neither side alone pays.** The top quintile's mean move was −0.3 to +0.3 bp and the bottom's −0.6 to −1.3 bp. Nothing is near the 16.63 bp one leg costs.

## The model disagrees with itself

Amendment 4 allowed one use of the Mac's stopped run: comparing its forecasts with the PC's on the same stock-times, without reading any return. The Mac drew one sample a forecast on the CPU; the PC averaged three on the GPU. On the 3,649 stock-times both computed (7 sessions):

| Horizon | Correlation of the two forecasts | Rank correlation | Same direction |
| --- | --- | --- | --- |
| 15 minutes | 0.32 | 0.27 | 60% |
| 30 minutes | 0.36 | 0.31 | 62% |
| 60 minutes | 0.49 | 0.41 | 65% |

Two runs of the same model on the same bars called the direction differently a third of the time. Most of what a single Kronos forecast says about the next hour is its own sampling noise. The three-draw forecasts vary less across stocks (their spread is about 30% narrower), but averaging draws does not create an edge. File: `data/kronos_l40_mac_vs_pc_forecasts.json`.

## How this fits with what was known

Three outside tests of Kronos, all daily, were negative (`predictive-tools-sweep-2026-09-29.md`): an NSE rank IC of −0.012, a forecast error 81% worse than a random walk, and 0 of 4 US funds beating persistence. This look adds the intraday answer on the project's own stocks and costs. With §69's hand-coded rules and the 2026-09-26 sweep, it closes "a model trained on bars elsewhere, used zero-shot here" as a way to rank NIFTY 100 stocks within the hour. The family look L46 tests six more such models under the same rules and is running.

## What went wrong, and what to read with care

- **78 sessions, not 79.** The selection holds 2025-10-21, the one-hour Muhurat session (13:45 to 14:40). No decision time falls inside it, so it has no stock-times. Stage 0's coverage counted it among the 79 sessions (39 and 40 a half); the statistics, and their halves, use the 78 sessions that have data. It does not change the verdict: 78 is above the 60 the gate needs.
- **The run of record changed machine before any result** (amendment 4): the Mac's CPU run at one sample a forecast was stopped at 3,649 of 43,362 and the PC's GPU run at three samples, already running, became the record. The Mac's rows were used only for the comparison above.
- **A latent defect in the moved-window rule**, never triggered here: `moved_window` starts the window at the earliest revision but the code then loads the latest revision. Both of this look's revisions predated the cutoff, so it did not apply. L46's harness follows the pre-registration's words instead.

## For the owner

Kronos does not go into Trader Sahab. The overnight decision agent (decision D1, `decisions/log-2026-09-30.md` on the overnight branch) kept the live shadow of 2026-09-30 as a display-only record, labelled as a failed model: it costs nothing, changes no trade, and is the forward record the combination search names as its confirmation sample. It is stopped if it slows the engine.
