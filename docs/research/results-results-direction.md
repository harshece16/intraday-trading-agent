# Results — results direction from the filed YoY profit number (research look L36)

**2026-09-25. Step 2 not earned.** Pre-registered in `prereg-results-direction.md` (commit `ec17d77`, before the run). One run. Selection sample only; held-out untouched. Ran at the user's direction without external reviewer review.

## Sample and its limit

100 NIFTY 100 companies indexed (0 fetch failures). **NSE's quarterly-results index thins out after January 2025**: ~700 filings a year through 2024, then 191 for all of 2025. So the selection window holds 377 raw rows → **188 results events** (one per company-quarter, consolidated preferred) → **167 with a year-on-year direction** (36 of 370 XBRL files had no `OneD` profit figure). That is about **two quarters** of results, not the five the window spans. Above the 50-event floor, but under-covered, and stated as such. A later query form for the missing quarters is the first thing to fix if this line is revisited.

## Result (bp of the entry price, aligned to the sign of YoY profit change)

| Window | n | Aligned mean | t | Share positive |
| --- | --- | --- | --- | --- |
| Next open +30 min | 167 | +5.92 | +0.60 | 53.3% |
| +60 min | 165 | +0.53 | +0.04 | 50.3% |
| To the 15:08 close | 167 | −0.63 | −0.04 | 50.9% |
| **Overnight gap (not tradable)** | 139 | **+82.71** | **+4.78** | — |

139 of 167 results were broadcast after hours; 28 in hours.

## Reading it

- **The direction is right.** The overnight gap moves **83 bp in the direction of the YoY profit change, t = 4.8**. Good results gap up, bad results gap down, on the filed numbers alone, with no analyst estimates.
- **And it is all priced by the open.** After the 09:20 entry the aligned drift is 6 bp at 30 minutes and zero by the close, against a 16.63 bp round trip. The tradable part of a results move, for a cash intraday account, is nothing. To earn the gap you would need to hold through the announcement, which is an overnight delivery trade with its own 33 bp two-leg hurdle and the whole-position risk of a bad print, and is outside this project's intraday scope.
- **Gate:** no window has aligned mean > 16.63 bp with t > 2. Step 2 is not earned. No rule is written.

## What this closes, and what it doesn't

It closes **"trade the results move intraday from the filed numbers."** It does not test surprise against expectations (no estimates in the data), and it under-covers 2025. Neither would change the structural finding that the move happens in the gap, not after the open.

Research look **L36**. No trial. Held-out untouched.
