# Results — event study on NSE filings (research look L35)

**2026-09-25. No filing class earns a step-2 rule.** Pre-registered in `prereg-event-study.md` (commit `ea4bab6`, before the run). One run. Selection sample only (316 sessions, 2024-09-25 → 2026-01-01); the held-out window was not loaded. Ran without external reviewer review, at the user's direction.

## Sample

30,085 filings for 100 symbol-years (0 fetch failures), 14,216 routine ones dropped by the feed's own list, **9,586 events measured** against the Kite 5m cache. Costs: 16.63 bp round trip.

## Results (bp of the entry price)

| Class : window | Events | Signed events | **Direction-aligned mean** | t | Mean absolute move | Normal-bar baseline |
| --- | --- | --- | --- | --- | --- | --- |
| ORDERS : 30m | 539 | 539 | **−8.64** | **−2.97** | 46.2 | 41.6 |
| ORDERS : 60m | 530 | 530 | −7.05 | −2.00 | 55.0 | 52.7 |
| ORDERS : close | 539 | 539 | −10.58 | −1.99 | 84.5 | 92.4 |
| NEGATIVE : 30m | 312 | 305 | +5.35 | +1.56 | 42.5 | 46.5 |
| NEGATIVE : 60m / close | 308 / 312 | 301 / 305 | −2.43 / −0.22 | −0.54 / −0.03 | 56.9 / 96.8 | 59.9 / 101.4 |
| DEALS : 30m / 60m / close | 248 / 242 / 248 | 205 / 200 / 205 | +2.94 / +1.81 / +7.11 | +0.65 / +0.31 / +0.74 | 49.7 / 60.9 / 102.7 | 43.7 / 52.8 / 92.2 |
| CAPITAL : 30m / 60m / close | 203 / 195 / 203 | 200 / 192 / 200 | +0.72 / +4.01 / −1.76 | +0.09 / +0.44 / −0.13 | 79.4 / 92.3 / 139.2 | 39.8 / 48.9 / 79.7 |
| OTHER : 30m / 60m / close | 8,081 / 7,927 / 8,081 | 542 / 535 / 542 | −0.57 / −0.87 / +3.88 | −0.16 / −0.19 / +0.54 | 55.6 / 69.2 / 107.6 | 45.4 / 56.9 / 93.5 |
| **RESULTS : 30m / 60m / close** | 203 / 192 / 203 | **0** | **unmeasurable** | — | **121.2 / 134.6 / 175.3** | 41.7 / 54.8 / 82.9 |

**Gate:** a class-window needed a direction-aligned mean above 16.63 bp with t > 2 on ≥ 50 events, after Benjamini–Hochberg across the 18 populated tests. **None qualified; the candidate list before correction was already empty.**

## Reading it

- **Order wins are "sell the news".** The one significant signed effect is the *wrong* way for the feed's tilt, and at 8.6 bp it is half the round trip. A contrarian short would be a new hypothesis, and it cannot clear cost; it is not proposed.
- **Results move stocks about 3× normal**, 121 bp in the first 30 minutes against 42 on ordinary bars, and 175 bp by the close. But **every result scored 0 for direction**: the keyword lexicon cannot read whether numbers are good or bad, so nothing could be aligned. This is a **volatility finding, not a directional edge**, exactly the case the pre-registration said to report as such.
- **Filings in general do not move NIFTY 100 stocks by more than the round trip in a tradable window.**

## What follows

The results-day finding is the one lead that involves **new information**: the direction of a result has to be *read*. `llm_sentiment.py` already scores text with Claude Haiku. A follow-up look (L36) would score each results filing's text, then test whether that direction predicts the 30-minute and to-close move by more than 16.63 bp. It is a measurement, pre-registered on its own, and the only version of an event rule this study leaves open.

Research look **L35**. No trial. Held-out untouched.
