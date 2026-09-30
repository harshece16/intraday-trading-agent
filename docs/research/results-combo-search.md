# Forecast × candlestick combinations — trials 128 to 202: none passes; every one of the 75 loses money after costs

**2026-09-30.** Pre-registration `prereg-combo-search.md` (`6921f08`, before L40's result was read and before any L46 model ran). Code `combo_search.py` (`74bfa0a`). One run on the owner's PC at 02:22 IST, after all six L46 models had results. Record: `data/combo_search_result.json`.

## Verdict

**0 of 75 combinations pass.** **Not one has a positive mean net return per trade.** The trial count of record becomes **202**.

| | |
| --- | --- |
| Combinations run | 75 of 75 (no source void) |
| Stock-times | 43,362 |
| Stock-times with a directional candlestick pattern (strength ≥ 2) | 5,074 (11.7%) |
| Best mean net per trade | −13.8 bp (Moirai 2.0, 15 min, forecast extreme; 409 trades) |
| Best mean gross per trade (net + 16.63) | +2.9 bp, the same combination |
| Candlestick pattern alone (the control), net per trade | −16.4 bp (15 min), −16.4 bp (30 min), −17.0 bp (60 min), 5,074 trades each |

## What the numbers say, plainly

- **The candlestick patterns carry no edge on these stocks at these horizons.** Trading every directional pattern of strength two or more in its direction earns about +0.2 bp before costs over 5,074 trades, so it loses almost exactly the round trip, 16.4 bp a trade. This matches the project's earlier finding that the entry signal was indistinguishable from random entry.
- **Combining a pattern with a model's forecast does not change that.** Requiring the forecast to agree (by sign or by quintile) selects fewer trades that are no better: the best combinations earn +1 to +3 bp before costs against 16.63 bp.
- **Trading only the forecasts' extremes loses more.** Taking the top and bottom fifth when the forecast exceeds the cost loses 14 to 24 bp a trade.
- **"See a profit" has a plain answer:** no combination of these seven forecasters and these candlestick rules earns more than it costs, before or after the correction for trying 75. Nothing here is a candidate for confirmation.

## What to read with care

- The search reuses L40's sample, which the seven looks had already scored. That is why every combination was fixed before any of them was read, and why the bar was set for 75 tries.
- The Ensemble averages the percentile ranks of all seven models at each decision time; its magnitude for the extreme rule is the models' median forecast.
- Each combination's trades overlap within a session; the t-statistics are across per-session means, which absorbs that.
