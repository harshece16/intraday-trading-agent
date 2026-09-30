# Morning note, 2026-09-30

Everything you asked for ran, and nothing passed. No forecasting model or combination earns more than it costs to trade, so nothing was added to Trader Sahab.

## What ran

| Test | Result |
| --- | --- |
| **Kronos** (L40), on your PC at three samples a forecast | **Fail** at 15, 30 and 60 minutes. The best gap between its top and bottom picks was +1.6 bp before costs; 33.26 bp was needed |
| **Six other forecasting models** (L46): Chronos-Bolt, TimesFM-2.5, Moirai 2.0, FlowState, TiRex, Sundial | **All six ran, all fail**, 18 of 18 tests. Gaps from −2.3 to +0.5 bp; 16 of 18 point slightly the wrong way |
| **A model trained on our own bars** (L47): Qlib's LightGBM on its 158 standard factors | **Fail.** Gaps 0.0 to +0.5 bp |
| **75 combinations** of those forecasts with candlestick patterns (trials 128–202) | **None passes; every one loses money after costs.** The best loses 13.8 bp a trade. Candlestick patterns alone earn about zero before costs over 5,074 trades |

So eight models ran, not the three you hoped for, and the 75 combinations were tried. The answer to "can we combine them and see a profit" is no. Every combination lost after costs, whether or not you correct for having tried 75.

## What it means

- Several models do rank the next hour slightly better, or worse, than chance, and some of those rankings are statistically real. In money they are worth a few basis points against a round trip of 16.63 bp per leg.
- This matches the project's earlier verdict: at these horizons and these costs, a better entry signal is not what is missing.
- The trial count of record is now **202**.

## What is running today

- **The Kronos shadow** runs on the Mac from 09:45 to 14:15, as a record only, labelled on the Kronos page as a failed model. Nothing reads it to trade.
- **Please reconnect Kite before 08:45.** The engine and the shadow both need it. Without it, the shadow uses the delayed feed and says so.

## How the night was run

- **Pre-registered first.** Every test was written down before its result could be seen: L46 and the combination search at 00:14, before Kronos's result was read.
- **Decisions logged before acting.** A decision agent took the judgement calls against a written charter (`charter-2026-09-30.md`), and every decision went into `log-2026-09-30.md` first, 13 entries in all.
- **The trained model was checked twice before it ran.** A separate agent reviewed it and rejected it the first time: it found a hole in the one-run rule and a small mismatch with Qlib's handling of zero-volume bars. Both were fixed and recorded as an amendment. The same agent then approved the fixed code, and checked the stage 0 output before the model was trained once.

## Your PC

- **Reachable from the Mac** over SSH, with key-only login.
- **Working folders:** `C:\Users\harsh\sahab-overnight`, `C:\Users\harsh\intraday-trading-agent`, one Python environment per model under `C:\Users\harsh\venvs`, and a full log in `C:\Users\harsh\kronos_pc.log`.
- **Sleep is off**, as you asked. Your old settings are saved in `C:\Users\harsh\kronos_power_before.txt`. Say if you want them back.
- **Nothing is running there now.** The GPU peaked at 74 °C.

## Waiting on you

No decision is required. Two optional ones:

- **The newest models.** Chronos-2, TiRex-2, Toto 2.0, Granite PatchTST-FM and TimesFM-3.0 were released after the test sample, so they can only be judged on sessions after their release. That means either the forward shadow (about 60 sessions, to the end of December) or the 2026 held-out window, which is your call. Given eight clean failures tonight, I would not spend the held-out window on them.
- **Issue #204.** It is a latent defect in L40's code that never triggered. It is a small fix whenever convenient.

## Where to read more

- `results-kronos-feature-ic.md`
- `results-tsfm-family.md`
- `results-qlib-lgbm-alpha158.md`
- `results-combo-search.md`
- README §104
