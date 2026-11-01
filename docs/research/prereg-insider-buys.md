# Pre-registration: trial 206, promoter open-market purchases held five sessions

**Written 2026-11-01, before any disclosure file is in the repo and before any
code exists.** The owner asked for a strategy the project has not tested, found
in the literature and on GitHub, and implemented. The sweep behind this choice
is `reports/NSE delivery strategy paper sweep.md` (notes in
`research_notes/NSE delivery strategy paper sweep/`). It found no price-only
family left with a demonstrated net-of-cost Indian edge among liquid NSE names,
so the candidate needs data the repo does not hold yet: SEBI insider-trading
(PIT) disclosures.

**Family and bar.** `entry-timing-sweep-2026-09-27.md` pre-allocated a family
"insider buying" with **N = 2 and t ≥ 2.24** (two-sided Bonferroni at 5%
across 2). This trial spends the **first** of those two slots. The second is
not spent here and is not read here (see "Not done here"). The bar is not
lowered because only one slot is used.

## Why this exists: the prior

- **Brochet, Lee and Srinivasan (2017)**, NSE–NYU Stern initiative, Indian
  insiders 2006–2014, Panel D: the five-session market-adjusted return starting
  on the day an insider *purchase* is reported through SEBI has mean **+1.82%**,
  median **+0.59%**, SD **10.80%**, N = 3,027 (several trades reported on one
  date are one event). The result is driven by promoters. Gross of costs.
- **Krishnan and Rangan** (NSE–IGIDR WP 4/14-15), 2008–2014, Table 6: the
  long-only drift *from day +2 after the trade* is negative at every horizon
  (−0.20% to day +22, −0.90% to day +253). The long–short spread they report
  comes from the sell side, which a delivery-only book cannot use.
- Read together: a short pop around the disclosure, then nothing for a long-only
  buyer. That is why this trial holds **five sessions**, not the 63 sessions the
  September sweep sketched. The change is made before any disclosure or return
  is read; it follows from the papers, not from data in this repo.
- **What is against it.** Both samples end in 2014, before the May 2015 PIT
  Regulations changed the disclosure rules and categories; no peer-reviewed
  study of the 2015–2026 regime was found. US evidence puts about a quarter of
  the insider-purchase gain in the first five days after the trade, and the
  Indian broadcast lags the trade by a median of two weekdays (Feb 2016 probe,
  55 rows), so part of the pop may be gone before the first open a retail buyer
  can join. The mean is a fat right tail: the median is a third of the mean.
- **Honest prior that this passes: below even.** A pass means the disclosure
  pop survived the regime change, the broadcast lag and 40 bp of costs. A fail
  closes long-only insider following for this project.

## What had been seen

- The Feb 2016 probe: one request to NSE's PIT endpoint for 1–7 Feb 2016
  (418 rows). Only counts, categories, modes, values and lags were read from it;
  **no return was read**. It is not in the repo and will not be used as data.
- Prices 2009–2025 have been read many times by the momentum trials; the
  2026 held-out window has never been read by any trial, but its prices were
  seen at the index level (`trials.md`, 2026-10-01 note). Disclosed, as the
  rule requires.
- No event return of any insider disclosure has been computed in this project
  (L35 had no insider class).

## Rules that do not change

- **Prices and costs** are trial 126's: NSE bhavcopy chains from
  `nse_prices.load`, total-return adjusted closes, the as-printed price for
  share counts, `slow_momentum.buy_cost` / `sell_cost` (STT, stamp, exchange,
  SEBI, GST, 5 bp slippage) and ₹15.34 DP per sell.
- **Held-out:** no session or disclosure dated 2026-01-01 or later is loaded in
  a selection run. The loader drops them unless asked for the held-out check.
- **Universe membership** uses trial 126's ranking: median traded value over
  the trailing 126 sessions, ≥ 250 sessions of history, printed close ≥ ₹20.

## The trial

**Events.** From the owner-exported NSE PIT disclosure files:

1. `CATEGORY OF PERSON` contains "Promoter" (Promoters, Promoter Group).
2. `MODE OF ACQUISITION` is "Market Purchase" and the transaction type is a buy.
3. The security is equity shares.
4. Rows for one symbol with one broadcast date are **one event**; its value is
   their sum and its timestamp the latest broadcast of the day.
5. Event value ≥ **₹10 lakh**.
6. The symbol maps to a bhavcopy chain (via `symbolchange.csv`) that is in the
   **top 500** by liquidity at the month-end before the entry session.
7. If the same symbol already has an open event (exit not yet reached), the new
   event is dropped and counted.

**Entry.** The open of the first session after the broadcast timestamp. A
broadcast before 09:00 IST on a session day makes that day's open eligible;
otherwise the next session. A missing broadcast timestamp falls back to the
intimation date at 23:59, so entry is the following session; the count is
reported. No trade on the entry session → the event is skipped and counted.

**Exit.** The close of the 4th session after the entry session (five sessions
held, entry day included). No trade that day → the last close on or before it.

**Size.** One ticket of **₹50,000** per event, whole shares at the printed
open; zero shares → skipped and counted. Events are independent tickets;
there is no slot cap in the trial statistic (the capped book is reported as
information, below).

**Costs.** `buy_cost` and `sell_cost` plus **5 bp a side** more slippage, so
**10 bp a side** in total, as the September sweep set for this family, plus the
DP charge. Round trip ≈ 42 bp + ₹15.34.

**Benchmark.** The equal-weighted top-500 universe over the same sessions,
from the entry open to the exit close, gross. The per-event statistic is
**net excess = net event return − benchmark return**.

**Samples.** Broadcasts dated **2015-05-15 → 2025-12-19** (the last broadcast
whose five-session window closes inside 2025). Halves: S1 to **2020-12-31**,
S2 from **2021-01-01**. Last three years: from **2023-01-01**. Held-out: 2026.

**Statistic.** The mean of per-event net excess, with a standard error
**clustered by entry session** (events in results seasons share dates; the
plain t overstates). The Deflated Sharpe uses the per-event series at N = 2.

## Power

With BLS's SD of 10.8% per event, the bar of 2.24 detects a true mean of
2.24 × 10.8 / √N half the time: **0.54% at N = 2,000**, 0.76% at N = 1,000,
1.08% at N = 500 (80% power needs about 1.4× those). The September sweep
counted 1,646 disclosures of all kinds in 1–15 Mar 2016; the Feb 2016 week had
37 promoter market-purchase symbol-days across all listed names. If a third of
those are in the top 500 and that week is twice the annual rate, N is about
2,000–3,000 over 10.6 years. Clustering by date lowers the effective N; the
stage-0 count decides whether the trial is worth running (below). If BLS's
gross +1.82% survived at +1.3% net of cost and market drift, the expected
unclustered t at N = 2,000 is about 5; if only the median survived, the net is
about zero and the trial fails.

## Stage 0: data gate (no return is read)

Printed and saved to `docs/research/data/trial206_stage0.json` before the trial
runs:

1. **Column mapping.** Every required field maps to exactly one column of
   every export file. An unmapped or ambiguous field stops the run; the loader
   is then fixed by a dated amendment to this file, as 3i's amendment 1 was.
2. **Export completeness.** Every calendar month from 2015-06 to 2025-12 has at
   least one row of any kind. A missing month is a missing chunk: the owner
   re-exports it. This is not a trial failure.
3. **Counts.** Rows per file, rows per month, qualifying events per month,
   events dropped at each rule (category, mode, value, unmatched symbol, not in
   the top 500, overlap, no trade at entry, zero shares, missing timestamp).
4. **Lag.** Weekdays from the last transaction date to the broadcast, and from
   the broadcast to the entry session, as a distribution.
5. **Stop rule.** Fewer than **8 qualifying events a month** on average, or
   fewer than **100** in total, and the trial is not run; the reason is
   recorded in `trials.md` and the slot stays unspent.

## Review before the run

An independent reviewer reads this file and `insider_buys.py` and approves them
before the run, as `prereg-us-momentum.md` requires.

## Pass rule (trial 206): all six required

1. Mean per-event **net excess > 0** with clustered **t ≥ 2.24**.
2. Deflated Sharpe ≥ **0.95 at N = 2** (`evaluation.deflated_sharpe_ratio` on
   the per-event net-excess series).
3. Mean net excess **> 0 in both halves**.
4. Mean net excess **> 0 over the last three years**.
5. Mean net excess ≥ **+25 bp per event**: the economic floor, so that the
   result is not an artefact of a few basis points of modelled slippage.
6. **≥ 100 events**.

## What a pass allows

A held-out **sign check** on broadcasts 2026-01-01 → the last complete month,
once, with the held-out loader. If positive, a **paper book** of its own
beside the Jev book: 20 slots of ₹50,000, events taken in broadcast order and
skipped when full, the live disclosures read by the owner or under an NSE
licence. It never mixes into the momentum book. Real money is a separate owner
decision after paper, and the momentum book's go-live list comes first.

## Falsification branches, written now

| Result | Meaning | Action |
| --- | --- | --- |
| Stage 0 stops | Too few events or an incomplete export | Fix the export or record "not run"; no re-tuning of the ₹10 lakh or top-500 rules to raise N |
| Fail on t or DSR, mean > 0 | Pop exists but is not distinguishable from luck at this bar | FAIL; line closed for this project |
| Fail on a half or the last three years | Pop did not survive the regime change or decayed | FAIL; closed |
| Fail on the 25 bp floor only | Statistically present, economically worthless after costs | FAIL; closed |
| Pass | The disclosure pop survives costs and the lag | Held-out sign check, then paper |

No hold length, value threshold, universe size, entry bar or category filter is
changed after a return is read. A crash before a statistic is printed may be
fixed and re-run with both runs recorded.

## Also reported (information, not gates)

Gross and net means, medians, SD, win rate, per-year means, the lag
distribution, and the capped book: 20 slots of ₹50,000 in broadcast order,
its annual net return against the benchmark. The capped book is not a gate
because it depends on capital, which is the owner's choice.

## Not done here

- **No cut by category, stake change, hold length, value band or lag bucket**
  is computed. Each is a candidate second hypothesis; reading it now would make
  a later pre-registration of it a post-hoc choice. The family's second slot
  (t ≥ 2.24) stays available for one of them, pre-registered first.
- **No pre-earnings subset** (BLS's strongest cell). It needs results dates
  for 500 names over ten years, which the repo only has for Nifty 100 names
  from 2017 (`pead_events.py`) and which the NSE terms (below) stop it from
  collecting by script.
- No short side, no sell-disclosure signal, no intraday entry.

## Data source and terms

- **Source.** NSE's insider-trading disclosure page
  (`nseindia.com/companies-listing/corporate-filings-insider-trading`), which
  shows a date-range table with a CSV download. The fields needed are the
  symbol, category of person, mode of acquisition, transaction type, security
  type, value, transaction dates, intimation date and **broadcast date and
  time**.
- **Terms.** NSE's Terms of Use (updated 29/10/2025) prohibit "any systematic
  or automated data collection activities (including scraping, data mining,
  data extraction and data harvesting)". So **no script in this repo fetches
  the disclosures.** The owner exports the ranges by hand in a browser into
  `backend/data/pit/` (gitignored), or licenses the history from NSE Data &
  Analytics. The Feb 2016 probe was a single request made during the sweep to
  learn the field shape; it is disclosed here and not repeated. Earlier research
  in this repo (`deals_l50.py`, `pead_events.py`, `event_study.py`) fetched
  NSE JSON by script; that precedent is now flagged for the owner, not followed.
- **Export plan.** Date-range chunks small enough for the page to return
  completely (a month at a time is the safe default; the Feb 2016 week was
  418 rows). Files are named `pit_YYYY-MM.csv` or `pit_<from>_<to>.json` and
  are never committed. Stage 0 item 2 catches a missing chunk.

## Ledger

`trials.md`: 206 registered 2026-11-01, not spent, waits on the owner's PIT
export. Count of record stays 203 spent, numbered to 206. The family bar
t ≥ 2.24 (N = 2) is unchanged from the September allocation.

## Code boundary and order

Everything goes in `backend/research/insider_buys.py` (loader, stage 0, the
trial, the held-out check) with tests on a **synthetic** fixture in
`backend/tests/test_insider_buys.py`. Nothing on the live path imports it.
Order: this file → export (owner) → stage 0 → review → one trial run logged
with `evaluation.log_trial` → `results-insider-buys.md` and the `trials.md`
row → held-out sign check only on a pass.

## Owner decisions

1. Export the disclosures by hand (about 128 monthly files) or buy the history
   from NSE Data & Analytics. Nothing runs until one of these is done.
2. Confirm 10 bp a side slippage and the ₹50,000 ticket, or amend before stage 0.
3. Whether the earlier scripted NSE fetches in research code should stay.

## Amendment 1 (2026-11-02): data start, provenance, held-out coverage

Written after stage 0 ran on the owner's export and before any return was
read. The first run failed only the 2015-06 completeness gate (every other
item passed); `trial206_stage0.json` is the rerun under this amendment.

- **Provenance.** The export was not a hand download. At the owner's
  instruction the data was fetched from inside the owner's own Chrome tab on
  NSE's insider-trading *archive* page, through the page's own date-range data
  URL, in six two-year calls paced three seconds apart (341,240 rows, one file
  `pit_2015-05-15_2026-11-02.json`, never committed). NSE's terms treat this
  as automated collection; the owner chose it knowing that. No script in the
  repo fetches NSE data. The acquirer's name was dropped from the saved rows;
  the trial does not use it.
- **Data start.** NSE's archive holds no row before **19 Nov 2015** (the
  regime began 15 May 2015; the exchange's archive does not reach back to
  it). The sample therefore starts at **2015-11-19**, and the completeness
  gate runs over **2015-12 → 2025-12** (November 2015 is a part month).
  `FIRST_BROADCAST` and `EXPORT_MONTHS` change accordingly. Nothing else in
  the trial changes.
- **Held-out coverage.** The archive thins to 3 rows in May 2026 and stops;
  NSE moved new filings to an XBRL-based page whose data URL returns filing
  metadata, not transaction rows. The 2026 sign check, if a pass earns it,
  covers **January–April 2026** only unless that page is mapped later.
- **Stage 0 as run.** Column mapping clean, no bad dates, no missing
  broadcast time. **2,600 qualifying events**, 21.31 a month on
  average over 122 months (gate: 8; amendment 2 corrects the 20.31 first written here), none of the stop rules hit. Drops: category 252,450,
  mode 58,220, security type 95, value 6,020, outside the window 64,
  held out 608, no price chain 480, not in the top 500 7,967,
  overlap 2,095. Lag from last transaction to broadcast: mode 2
  weekdays, long tail. Entry falls the day after the broadcast for most
  events, three days later after a Friday broadcast.
- **Thinning.** Events a month fall from about 30 (2016–2020) to about 6–8
  (2024–2025) while rows per month stay in the hundreds to thousands, so the
  second half and the last three years rest on fewer events than the first
  half. The gates are unchanged; the power is lower than the September
  estimate and is recorded here before the run.
- **Housekeeping.** The `.gitignore` line for `backend/data/pit/` carried a
  trailing comment, which gitignore reads as part of the pattern; fixed.

## Amendment 2 (2026-11-02): independent review

Written after an independent review of the pre-registration, the module and
the stage-0 output, and before any return was read. One blocking finding and
five should-fix items; every one is applied here, stage 0 was rerun and
`trial206_stage0.json` replaced. No rule, sample, gate or bar changes.

- **Blocking: price panel.** The module loaded `nse_prices`' default panel.
  Trial 126's universe and prices come from `momentum_width.load_panel()`,
  which is `nse_prices.load(wide=True)`: the repaired panel with BE/BZ rows,
  consolidations and the dividend fix. Fixed: the wide panel is loaded, the
  top-500 ranking reads its EQ rows only through `momentum_width.eq_view`
  as trial 126 does, and entry and exit are priced on the chain as traded.
  Symbols are matched through the panel's own alias table first, then the
  symbol-change chain.
- **Held-out guard.** The held-out check refuses to run unless
  `trial206_result.json` exists with `pass: true` and no
  `trial206_heldout.json` exists; it is no longer logged as a trial; it
  writes its own events file; its window is January–April 2026
  (`HELD_OUT_END = 2026-04-30`). The trial refuses a second run once its
  result file exists. Rows broadcast in 2026 are dropped as the export is
  read, so not even stage 0's row counts see them (4,458 rows).
- **Gates on unrounded values.** The six checks read the unrounded mean and
  clustered t; the rounded figures are for display. The Deflated Sharpe
  comes back from the shared `evaluation` module rounded to three places, so
  a value within 0.0005 of 0.95 would be a tie; noted before the run.
- **Rule 2 tightened.** The transaction type must be exactly "Buy" (the
  export has 131 "Sell", 13 "-" and 5 pledge rows among market purchases).
  "Non-promoter" does not occur as a category in the export, so no clause
  for it.
- **Tradability before the overlap rule.** An event with no row at the entry
  session, a zero open, or an open above the ticket (no whole share for
  ₹50,000) is dropped while events are built, so it no longer blocks a later
  event of the same name. New counters `no_trade` and `zero_shares`.
- **Split by broadcast date.** Halves, last three years and per-year blocks
  split on the broadcast date, as the Samples paragraph says; the code had
  split on the entry session.
- **Amendment 1 correction.** The average was written as 20.31; 2,600
  events over 122 months (2015-11 → 2025-12) is 21.31.
- **Stage 0 as rerun.** Column mapping clean, no bad dates, no missing
  broadcast time, every month 2015-12 → 2025-12 present; 336,782 rows in
  sample. **2,579 qualifying events, 21.14 a month** (gate 8). Drops:
  category 250,451, mode 57,239, security type 90, value 5,703, outside the
  window 64, no price chain 367, not in the top 500 8,072, no whole share at
  one ticket 41, no trade at entry 0, overlap 2,080. Events per year: 2015
  39, 2016 341, 2017 286, 2018 406, 2019 384, 2020 396, 2021 205, 2022 210,
  2023 143, 2024 68, 2025 101; so S2 rests on 727 events and the last three
  years on 312. Lag from last transaction to broadcast: mode 2 weekdays.
  Entry is the next day for 1,821 events, three days later for 493.
