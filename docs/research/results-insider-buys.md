# Promoter open-market purchases, five sessions held — results. **FAIL (trial 206). Over 2,579 disclosure events the net excess over the universe was +4.4 bp per event, clustered t 0.37, against a bar of t ≥ 2.24 and ≥ 25 bp. The first half was negative. The line is closed.**

**2026-11-02.** Pre-registration `prereg-insider-buys.md` (`d091ea6`, 1 Nov,
before any disclosure file or code existed), then the module, then the owner's
export, then stage 0 and amendment 1 (data start 2015-11-19, provenance),
then an independent review and amendment 2 (the price panel and five smaller
fixes), then stage 0 again, all merged in #313 and #314 (`7a7f726`). The trial
ran once at 01:05 IST from that code, logged as entry 35 of
`backend/data/backtest_trials.json`. Rows broadcast in 2026 (4,458) were
dropped as the export was read and no 2026 session was loaded; no Kite data.
The export itself (`backend/data/pit/`, 128 MB) is not committed; the priced
events are, in `data/trial206_events.csv`, with `data/trial206_result.json`
and `data/trial206_stage0.json`.

## Verdict, in the pre-registration's terms

| Check | Rule | Result | |
| --- | --- | --- | --- |
| Mean and t | mean net excess > 0, clustered t ≥ 2.24 | **+4.4 bp, t 0.37** | **fail** |
| Deflated Sharpe | ≥ 0.95 at N = 2 | 0.447 | **fail** |
| Both halves | mean > 0 in 2015-11 → 2020 and in 2021 → 2025 | **−2.7 bp** (n 1,852, t −0.18); +22.5 bp (n 727, t 1.22) | **fail** |
| Last three years | mean > 0 from 2023 | +22.3 bp (n 312, t 0.94) | pass |
| Floor | mean ≥ 25 bp | 4.4 bp | **fail** |
| Size | ≥ 100 events | 2,579 | pass |

Two falsification rows apply: "fail on t or DSR, mean > 0: pop exists but
is not distinguishable from luck at this bar" and "fail on a half: did not
survive the regime change". Both say FAIL and close the line for this
project. The pre-registration's own prior was a pass "below even"; this is
the expected outcome, not a surprise.

## What it means, plainly

**1. There is a gross pop, and costs take it.** An event earned +67 bp gross
from the entry open to the fifth close, against +17 bp for the equal-weighted
universe over the same sessions: about 50 bp of gross excess in five
sessions, in the direction the literature predicts. Trial 126's charges plus
10 bp a side of slippage cost 45 bp a round trip, leaving +22 bp net and
+4 bp over the benchmark. At a 5-session holding period the edge is the
same size as the cost of collecting it.

**2. The median event loses.** Median net excess is −39 bp and 46% of events
beat the benchmark; the positive mean comes from the right tail (SD 577 bp).
A book of these would spend most sessions behind the universe and rely on a
few large winners.

**3. The second half looks better, but cannot be told from noise.** 2021
onward: +22.5 bp with t 1.22 on 727 events; the last three years +22.3 bp
with t 0.94 on 312. Events thinned from about 30 a month before 2021 to
6–8 a month in 2024–2025 (amendment 1 recorded this before the run), so the
recent period has about a quarter of the power the September estimate
assumed. The pre-registration does not allow reading the second half as a
separate result, and this note does not.

**4. The capped book did not earn its risk.** Twenty slots of ₹50,000,
events in broadcast order, skipped when full: the sum of annual net returns
2015–2025 is +31% against +20% for the benchmark on the same capital, with
−10% in 2018 and three other losing years. Information only; it is not a
gate, and it is not a reason to run paper.

## Per year (broadcast date; mean net excess per event)

| Year | Events | Mean excess bp | Clustered t | Mean net bp | Win rate | Capped book net % | Benchmark % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2015 (from 19 Nov) | 39 | −136.4 | −3.61 | −167.6 | 0.28 | −1.96 | 0.10 |
| 2016 | 341 | 6.6 | 0.24 | −0.9 | 0.46 | −1.98 | −2.94 |
| 2017 | 286 | 54.6 | 1.90 | 136.4 | 0.48 | 19.82 | 12.16 |
| 2018 | 406 | −16.4 | −0.53 | −60.0 | 0.44 | −9.64 | −6.71 |
| 2019 | 384 | 3.7 | 0.11 | 22.8 | 0.48 | 4.42 | 3.18 |
| 2020 | 396 | −31.1 | −0.73 | −22.2 | 0.44 | −3.68 | −1.69 |
| 2021 | 205 | 0.8 | 0.02 | 72.8 | 0.43 | 7.64 | 7.37 |
| 2022 | 210 | 44.0 | 1.25 | 64.6 | 0.52 | 6.29 | 2.41 |
| 2023 | 143 | −12.0 | −0.33 | 55.2 | 0.43 | 4.12 | 4.76 |
| 2024 | 68 | 51.1 | 1.05 | 108.1 | 0.50 | 3.67 | 1.94 |
| 2025 | 101 | 51.3 | 1.30 | 45.6 | 0.52 | 2.31 | −0.29 |

The capped book's event counts differ slightly from the sample's (it skips
when its twenty slots are full and groups by entry date).

## Sample, as built

336,782 rows in the sample window; drops in order: not a promoter 250,451;
not an open-market buy 57,239; not equity 90; under ₹10 lakh 5,703; outside
the window 64; no price chain 367; not in the top 500 at the month-end
before 8,072; no whole share at ₹50,000 41; overlapping an open position
2,080. Entry fell the next session for 1,821 events, three days later for
493 (Friday broadcasts); 21 events broadcast before 09:00 joined the same
day's open. Busiest entry sessions: 2020-04-03 (14 events), 2020-09-28 (13),
2020-03-23 (12), which is why the standard error is clustered by entry
session.

## Not read, not done

- No cut by category, stake change, hold length, value band, lag bucket or
  pre-earnings timing was computed; each remains a candidate for the
  family's second slot, which stays unspent and would need its own
  pre-registration first.
- The 2026 rows (January–April, 4,458) were not read; a sign check was
  earned only by a pass.
- No hold length, threshold, universe or entry rule was changed after the
  return was read; the only code after stage 0 was the review's fixes,
  recorded in amendment 2 before the run.
- The paper book this would have earned is not started. The momentum book is
  unchanged.
