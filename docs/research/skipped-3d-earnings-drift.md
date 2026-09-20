# Step 3d — post-earnings drift: SKIPPED

**Decision:** skipped, on reviewer instruction (2026-09-20), after the
time-boxed feasibility check the brief allowed.

**Reason in one line:** no free source reaches historical earnings
*announcement* dates across 2024-09 → 2026-09 for the NIFTY 100, and the
sources that do work return fiscal quarter-**end** dates, which are not the
same event.

---

## What was checked

Six liquid symbols (RELIANCE, TCS, INFY, HDFCBANK, ITC, SBIN) against
`yfinance`, which the repo already depends on — `fundamentals.py` calls
`Ticker(...).get_info()` — so no new dependency was needed to try.

| Path | Result |
| --- | --- |
| `Ticker.get_earnings_dates()` | **Blocked.** `ImportError: Missing optional dependency 'lxml'` on all six symbols. |
| `Ticker.calendar` | Returns the **next** earnings date only (Oct 2026). No history. |
| `Ticker.quarterly_income_stmt` | 5 columns, **2025-03-31 → 2026-06-30**. Does not reach 2024-09. |
| `Ticker.get_info()` | Single `earningsTimestamp`, plus `isEarningsDateEstimate: True`. No history. |

## Why quarter-end dates are not a substitute

`quarterly_income_stmt` gives the *period* a result covers (2025-03-31), not
the date the market learned of it. Indian companies announce anywhere from a
few days to six-plus weeks after quarter end, and the lag varies by company
and by quarter.

Post-earnings drift is defined relative to the **announcement**. Using
quarter-end as a proxy would place the event window at an unknown, variable
offset from the actual information release — which does not merely add noise,
it misaligns the thing being measured. A drift measured from the wrong day is
not a weaker version of the result; it is a different and uninterpretable one.

Even setting that aside, five quarters reaching back only to 2025-03 covers
roughly the second half of the sample. The window required is 2024-09 →
2026-09.

## What was NOT established

**`earnings_dates` was blocked, not proven empty.** Installing `lxml` might
unblock it. That was not done, for two reasons:

1. It is a dependency addition, which the brief asks be raised rather than
   taken unilaterally.
2. Even unblocked, yfinance's historical earnings-date depth for NSE
   symbols is uncertain — it commonly returns a handful of recent quarters,
   which is the same coverage problem seen in `quarterly_income_stmt`.

So the honest statement is: **one path is blocked and untested; every path
that does work fails on coverage.** If a reviewer wants 3d revisited, the
cheapest next step is to install `lxml` and re-run the same six-symbol check
before committing to anything larger.

## Alternatives not pursued

- **NSE corporate-announcements API / bhavcopy** — plausibly has the dates,
  but scraping or ingesting it is a new data source and a meaningful piece of
  work, not a 15-minute check.
- **Paid vendors** — outside the brief.

## Consequence for the phase

Step 3 now has three hypotheses (3a opening-range breakout, 3b intraday
momentum, 3c overnight-vs-intraday decomposition) rather than four.

This is recorded rather than quietly dropped because an absent test is itself
information: **post-earnings drift is one of the better-documented anomalies
in the academic literature, and it remains untested here.** If the three
remaining hypotheses all fail, "we never tested the one with the strongest
prior" is a real gap in the phase's coverage, and a reviewer should be able to
see it stated.

## Trial counting

No trial. Nothing was backtested and no strategy was selected. Recorded in
`trials.md` under *research looks* as a feasibility check.
