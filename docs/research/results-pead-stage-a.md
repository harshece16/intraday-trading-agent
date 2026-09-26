# PEAD Stage A results — **NO-GO. Post-earnings drift is dropped.** (Research look L39, no trial.)

**2026-09-26.** Pre-registration `prereg-pead-stage-a.md` (`4d95f58`),
clarification 1 (`a8a9293`), event builder (`f4aef1b`), data and statistic
script (`3d5a820`), one run of the statistic at 23:38:38.

| Rule (fixed in advance) | Result | |
| --- | --- | --- |
| Gross mean monthly excess ≥ +0.37% | **+0.25%** | fail |
| Newey–West (3) t ≥ 1.8 | **1.41** | fail |

**Verdict: NO-GO.** Under the pre-registration PEAD is dropped: no second
signal, window, universe or holding period will be tried — and the earnings
surprise will not be slipped into any later model as a feature either.

## What was measured

Point-in-time NIFTY 100, XBRL-era quarterly filings (mid-2018 → the season
that exits by 2025-12-31). Buy the top third of earnings surprises —
(PAT_q − PAT_q−4) / market value six sessions before the filing, breakpoint
from all earlier events — at the close of the first session after the
filing; hold 60 sessions; 30 slots; benchmark the equal-weighted
point-in-time NIFTY 100 with total-return prices.

| | |
| --- | --- |
| Events kept / top tercile / entered | 2,115 / 647 / 496 (72 clock resets, 79 skipped when full) |
| Months | 73 (2019-11 → 2025-11), 22.6 positions held on average |
| Gross excess | **+0.25%/month**, NW t 1.41, sd 1.70% |
| Net excess at ₹10 L | **+0.11%/month**, NW t 0.62 |
| Halves (gross) | +0.36%/month (t 1.38) then +0.14%/month (t 0.54) |
| Per year (gross, summed) | 2019 +0.5% · 2020 −3.5% · 2021 +2.8% · **2022 +11.7%** · 2023 +5.6% · 2024 −1.7% · 2025 +2.7% |
| Correlation with 3i momentum's monthly excess | 0.18 |

The drift exists in the sign — as in the literature — but it is about a
third of what the Indian gross literature reports, most of it sits in 2022,
the second half is weaker, and costs take more than half of it.

## Data notes

- Data gate: 82.9% of 2,508 point-in-time member-quarters (2019-Q2 → 2025-Q2)
  produced a usable surprise (gate ≥ 60%).
- Dropped before any return was read: 148 events whose broadcast trailed the
  XBRL file date by ≥ 2 days (the 2018–2020 dating defect), 57 with no XBRL
  values (24 files 404), 17 non-quarterly filings, 1,189 outside NIFTY 100
  membership at entry, 449 without a price (all 2026 filings, after the
  selection data), 87 that would exit in 2026.
- Shares from paid-up capital ÷ face value in 3,817 filings, profit ÷ EPS in
  23; 86% of events have shares within ±5% of a year earlier (the rest are
  splits, bonuses, buybacks and issues).
- **Found along the way:** L36 read only `ProfitLossForPeriod`, which banks do
  not use (`ProfitLossForThePeriod`), so L36 had no bank profit figures.
  Recorded; L36 is not re-run.
