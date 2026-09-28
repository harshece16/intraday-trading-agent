# Pre-registration — 3i: slow momentum in delivery on corrected NSE data, with a fresh-stock confirmation

**Written 2026-09-26, before any 3i code exists.** Owner direction the same
day: shift the product from intraday leverage to delivery ("normal buy and
sell") and judge new work by the family-level bar
(`decision-2026-09-26-overnight-and-significance.md`). This is the first
test under that bar.

**Two parts, one family ("slow cross-sectional momentum"):**
- **Part A — trial 120.** 3h's exact rules on corrected data, NSE's 200
  most-traded stocks, 2010-02 → 2025-11.
- **Part B — research look L38, a confirmation.** The same rules on the
  **next 200 stocks by liquidity (ranks 201–400)**, which no test in this
  project has ever read.

## Read this first — what Part A can and cannot show

Part A re-reads the 189 months trial 119 already read. Trial 119's result
(net excess +0.72%/month, t 2.48) was seen, and it was contaminated by a
look-ahead (#135) and two data defects (#130). **A Part A pass is therefore
not independent evidence**: the rules and the months were both known when
this was written. Its job is to say whether the effect survives clean data.
The independent evidence is Part B (unseen stocks), then the 2026 held-out
months, then forward paper trading. Nothing reaches paper without all
three.

The 2026 held-out is already partly seen for this family: the literature
sweep and the edge-map read NIFTY200 Momentum 30's published 1-year and
year-to-date figures (logged in `trials.md`). That is disclosed, not fixed.

## Rules — identical to 3h, not re-tuned

Universe, signal, portfolio, fills and costs are 3h's as amended
(`prereg-3h-slow-momentum-delivery.md`), with the #135 fixes:

- **Universe at each month-end t:** EQ-series chains with ≥ 250 sessions of
  history, **as-printed** close ≥ ₹20 on t, traded on t; ranked by median
  daily traded value over the trailing 126 sessions (absent days count as
  zero). Part A: ranks 1–200. Part B: ranks 201–400.
- **Signal:** mean(r6/σ, r12/σ), returns to month-end t−1 (skip-month), σ
  over 252 sessions.
- **Portfolio:** long only, 15 names, equal weight at entry, keep while rank
  ≤ 30, replace from the top; fills at the next session's close.
- **Costs (Zerodha CNC, 2026):** STT 0.1% each side, stamp 0.015% buy, NSE
  0.00307%, SEBI, GST on those, **DP ₹15.34 per scrip per sell (GST
  included)**. Slippage per side: **0.05% in Part A; 0.10% in Part B**
  (ranks 201–400 are mid-caps with wider spreads).
- **Benchmark:** the same universe equal-weighted, churn only, same
  percentage costs, no DP charge.
- **Capital:** ₹10,00,000 (the owner is adding funds; at ₹10 L a name is
  ₹66,667, so DP is ~2.3 bp). ₹1 L and ₹25 L columns reported, cost only.

## The data fix (the reason 3i exists)

Source: NSE's corporate-actions files (`api/corporates-corporateActions`,
equities, one file per year 2008–2025) and the daily bhavcopies already
cached. Adjustments are applied **backward from the ex-date**:

| Action | Adjustment | Note |
| --- | --- | --- |
| Split / sub-division "From Rs a To Rs b" | prices before ÷ (a/b) | ratio from the text |
| Bonus a:b (a new for b held) | prices before ÷ ((a+b)/b) | |
| Rights a:b @ premium p | factor = TERP / P, TERP = (b·P + a·(FV+p)) / (a+b), P = close(t−1) | rights with no parseable price are counted, not adjusted |
| Demerger / scheme of arrangement | factor = OPEN(t) / CLOSE(t−1) on the ex-date | the special pre-open sets the parent's ex-value; the demerged shares' value is not in the parent's series (checked: ITC 2025-01-06 and TATAMOTORS 2025-10-14 carry an unadjusted PREVCLOSE) |
| Dividend (Rs per share, or % of face value) | added as cash on the ex-date: total return | strategy and benchmark alike |

- **Equities only:** a chain is excluded if any of its ISINs starts with
  `INF` (fund units). Chains with no ISIN (pre-2011) are excluded if their
  symbol is in NSE's ETF list or ends in BEES/ETF/IETF. Counts reported.
- The price-and-quantity split detector from 3h becomes a **check only**.
- 2026 sessions are never loaded in a selection run.

## Stage 0 — data gate (no forward return is read)

1. Coverage as 3h (≥ 240 sessions a year, a file within 3 sessions of every
   month-end, ≥ 400 eligible chains at every month-end so Part B exists).
2. **Adjustment consistency:** for every official split or bonus on a chain
   in the top 400 on its ex-date, the adjusted ex-date return must lie
   within ±20%. Gate: **≥ 97%** of such events consistent. Every failure
   listed.
3. **Residual phantoms:** one-day adjusted returns below −30% on liquid days
   (traded value > ₹5 Cr) among top-400 chains are listed; each must be
   explained (a real crash with news, or a missing corporate action). Gate:
   no more than 10 unexplained.

If stage 0 fails, 3i stops and reports. One re-fetch for download failures
is allowed; no other amendment.

## Part A — trial 120, the pass rule (family-level bar)

N_family = 3 (trial 118 void, trial 119, trial 120). All required:

1. Monthly net excess over the benchmark: mean > 0 and **t ≥ 2.394**
   (two-sided Bonferroni at 5% across 3).
2. **Corrected Deflated Sharpe ≥ 0.95 at N = 3**, on the series' own skew
   and kurtosis.
3. Positive in **both halves** (2010-02 → 2017-12, 2018-01 → 2025-11).
4. Positive over the **last three years** (2023-01 → 2025-11).
5. Net CAGR minus benchmark net CAGR ≥ 2.0 pp.
6. ≥ 100 round trips.

## Part B — L38, the confirmation (unseen stocks)

Same rules on ranks 201–400, same months. It is a confirmation of Part A,
not a competing configuration, so it does not raise Part A's N; requiring
both to pass is stricter than either alone. **Confirms** if: monthly net
excess mean > 0 with **t ≥ 1.65** (one-sided 5%), and positive in both
halves. Reported whatever Part A shows.

## Held-out and forward

Only if Part A passes **and** Part B confirms: Part A's rules on the 2026
month-ends through the last complete month (about 8 observations). Confirms
if the mean monthly net excess is **positive** (sign check; the band of
±2 SE is ±2.8%/month and cannot bind). Then a **paper positional book** in
the engine with a forward band: switched off if, after 6 months, the
cumulative net excess is below −2 SE of its expectation.

## Falsification branches, written now

| Part A | Part B | Meaning | Action |
| --- | --- | --- | --- |
| fail | fail | Momentum does not survive clean data here | Close the momentum line |
| pass | fail | The effect does not travel to unseen stocks | No held-out, no paper |
| fail | pass | Interesting, but A's gate is the gate | FAIL; record B |
| pass (economics only) | any | Fails the multiple-testing gate | FAIL, per the standing rule |
| pass | pass | Held-out sign check | Paper book only if the sign is positive |

## Also reported (information only)

Gross versions of everything; the ₹1 L/₹25 L cost columns; turnover; the
number of ETFs, rights, demergers and dividends applied; per-year excess;
the difference between 3i Part A and trial 119 month by month (what the
data fix changed); and a comparison with the published NIFTY200 Momentum 30
index over its live period (2020-08 onward).

## Code boundary and order

`backend/research/nse_prices.py` (corporate-action loader, data only) and
`backend/research/momentum_3i.py` (stage 0, Part A, Part B), committed after
this file. Nothing on the live path imports them. One run per part. A crash
before a statistic is printed may be fixed and re-run with both recorded.

---

# Amendment 1 — 2026-09-26, after the first stage-0 run, before any return is read

The first stage-0 run (output kept as `data/momentum_3i_stage0_run1.json`)
passed gates 1 and 2 (98.7% of 382 splits/bonuses consistent) and listed 35
residual drops beyond −30%. Checking each against NSE's file found two
kinds of loader defect and one rule gap:

- **Parser defects (fixed; this implements the rule as written).** NSE's
  older rows use abbreviations the parser missed: "Fv Splt Frm Rs 10 To
  Re 1" (JSWSTEEL 2017, KARURVYSYA, ICIL, ALANKIT 2016), "Fv
  Spl-Rs10tore1/Div-1.50" (KRBL 2010), "Bon 1:1/Fv Spl Rs.5tors.2"
  (STLTECH 2010), "Fv Spl-Rs10tors5/Bon-2:1" (ENGINERSIN 2010), "Rights
  87:38 @ Premium Of Rs 2.50" (IDEA 2019), and bare "Div-1.50" amounts.
- **An implementation guard that was not in the rule (removed).** The
  loader refused dividends above 50% of the previous close, which rejected
  Strides' real ₹500 special dividend (STAR, 2013-12-19). The cap is now 90%.
- **Rule gap (amended).** The demerger rule uses OPEN(ex)/CLOSE(ex−1),
  assuming the ex-date open is the special pre-open's discovered ex-value.
  For older demergers (TRIVENI 2011, ZEEMEDIA 2010, SINTEX 2017) the open is
  not a discovered value, and ADANIENT 2015's ratio (≈ 0.19) fell below an
  implementation bound. **Amended rule:** use OPEN(ex)/CLOSE(ex−1) when it
  is between 0.05 and 0.98; otherwise CLOSE(ex)/CLOSE(ex−1) — the ex-date's
  whole move is attributed to the demerger, losing that one day's market
  return. Applied identically to strategy and benchmark.

Stage 0 is re-run after this commit; both runs are kept. No forward return
has been read by either.

---

# Note on the forward paper book — 2026-09-28, before its first rebalance

**Owner's decision, 2026-09-28:** "yes fix the momentum book loader before 1
october".

The paper book (`backend/momentum_book.py`) had held nothing and recorded no
return when this was written. Its first rebalance is on the evening of
2026-10-01.

**What changes.** Its price loader becomes a copy of the research loader's
repaired panel (`prereg-universe-width.md`; #175, #177, #178): it reads
trade-for-trade rows, adjusts consolidations, reads seven dividend amounts
correctly and applies two kinds of action the old bounds refused. On the
bhavcopy cache to 2025-12-31 the book's panel and the research panel have 0
differences.

**What does not change.** The universe, the signal, the portfolio rule, the
costs, the benchmark and the band. The universe is still chosen from EQ rows
only. The band still expects +0.82% a month with a standard deviation of
3.87%.

**What the forward test now measures.** The rule on repaired prices with the
simple fill assumption: every order fills at the close. That is neither
trial 120's configuration (old prices) nor trial 126's (repaired prices,
carried orders). Trial 126 gave +0.71% a month. Keeping 0.82% makes the band
stricter than either figure would. Adding the fill rules, and changing the
expected figure, are the owner's decisions and have not been made (#180).
