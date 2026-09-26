# 3i results — slow momentum in delivery on corrected data. **Part A PASSES (trial 120); Part B CONFIRMS on unseen stocks (L38); the 2026 held-out sign CONFIRMS.** Paper positional book authorised by the pre-registration.

**2026-09-26.** Pre-registration `prereg-3i-momentum-corrected-data.md`
(`1dc0501`), code `890dfba`, amendment 1 and loader fixes `3fbe5ed` (after
stage-0 run 1, before any return was read), stage 0 run 2 output, Part A
output, Part B output, held-out loader step `e28374c`, held-out output — in
that commit order. One run of Part A (20:06:59), one of Part B (20:07:56),
one held-out run (20:09:56).

## Verdict, in the pre-registration's terms

| | Rule | Result | |
| --- | --- | --- | --- |
| **Part A** (trial 120, top 200) | t ≥ 2.394 | **+0.82%/month net excess, t = 2.91** | pass |
| | family DSR ≥ 0.95 (N = 3) | **0.98** | pass |
| | both halves positive | +0.72% / +0.91% per month | pass |
| | last three years positive | +0.87%/month (t 1.17) | pass |
| | CAGR gap ≥ 2 pp | **22.3% vs 12.0%** (+10.3 pp) | pass |
| | ≥ 100 round trips | 519 | pass |
| **Part B** (L38, ranks 201–400, never read before) | t ≥ 1.65 and both halves positive | **+1.00%/month, t = 3.31**; +0.79% / +1.21% | **confirms** |
| **Held-out** (2026-01 → 2026-08, 8 months) | mean monthly net excess > 0 | **+1.28%/month** (6 of 8 months positive, t 1.08) | **confirms** |

Under the falsification table, "pass / pass / held-out positive" means a
**paper positional book** runs in the engine, with a forward band that
switches it off automatically. Real money stays the owner's decision.

## What this is, plainly

A slow, long-only momentum tilt — buy the 15 of the 200 most-traded NSE
stocks with the strongest volatility-adjusted 6- and 12-month returns, hold
them in delivery, revisit monthly — beat an equal-weighted basket of the
same stocks by roughly 0.8% a month net of every Zerodha delivery charge
over 2010–2025, on data now adjusted with NSE's own corporate-actions file
and dividends. The same rules on 200 stocks no test here had ever read did
slightly better (+1.0%/month) with double the slippage. The eight unseen
months of 2026 went the same way.

It is **not** a prediction engine in the sense of calling tomorrow's price,
and it is not smooth:

| Year | Part A excess | Part B excess |
| --- | --- | --- |
| 2010 | −0.7% | +8.4% |
| 2011 | +19.7% | +14.6% |
| 2013 | −6.9% | +24.3% |
| 2016 | −14.4% | −17.1% |
| 2020 | +21.7% | +27.5% |
| 2021 | +23.9% | +37.1% |
| 2023 | +29.5% | +27.9% |
| **2025** | **−13.3%** | **−14.0%** |
| 2026 (held-out, Jan–Aug) | +10.2% | — |

(Sums of monthly excess; every year is in the JSON.) Momentum has losing
years of 10–17% against its own universe; 2016 and 2025 were two. Maximum
drawdown was −33% (strategy) against −39% (benchmark).

## Disclosures — read before relying on any number

1. **Part A is not independent evidence.** It re-reads the 189 months trial
   119 read, and trial 119's result was seen. What Part A shows is that the
   effect **survives the data fix**: month by month, 3i-A's excess differs
   from trial 119's by +0.10%/month on average (sd 1.7%). The independent
   evidence is Part B and the held-out.
2. **The bar is the family-level one** the owner chose today, prospectively.
   At the project-wide count (N = 120, roughly t ≥ 4.3) Part A would **fail**
   (project-wide corrected DSR 0.62; Part B 0.74). That is stated so nobody
   later reads this as having cleared the stricter bar.
3. **The held-out is weak and partly seen.** Eight observations, t 1.08. The
   August 2026 month (+7.8%) carries much of it: without it the other seven
   average +0.35%. The literature sweep and edge-map had already read the
   published NIFTY200 Momentum 30 year-to-date figure for 2026 (logged in
   `trials.md`); that index is a related but different portfolio.
4. **Stage 0 needed a second run.** Run 1 (kept) exposed parser defects on
   NSE's abbreviated spellings, a "Division"-as-dividend bug and a dividend
   guard that rejected a real special dividend; amendment 1 added a demerger
   fallback. All before any return was read; both runs are committed.
5. **Residual data defects.** 25 one-day drops beyond −30% remain among
   top-400 names on liquid days. 21 are real events (DHFL 2018, Infibeam
   2018, Jet Airways 2019, the ADAG group 2019, Yes Bank 2020, Indiabulls
   Housing 2019/2020, Zee 2024, GTL 2011, IGL 2012, Core Education 2013, Opto
   Circuits 2013, Financial Technologies 2013, Ranbaxy 2013, Amtek Auto
   2015, Dish TV 2019); three are demergers NSE's file gives no ratio for and
   the price rule only partly adjusts (Zee Media 2010, Triveni 2011, Adani
   Enterprises 2015); one is unexplained (Suzlon 2013-02-28). Gate: ≤ 10
   unexplained — pass. Seven of 391 checked splits/bonuses land on a +20%
   ex-date move, consistent with an upper circuit.
6. **Not modelled:** short-term capital gains tax (20% on holdings under 12
   months — most exits here), and the closing auction introduced 2026-08-03:
   fills are at the next session's close, which since August is an auction
   price. Whether Zerodha routes delivery orders into that auction is
   unverified; the paper book will record it.
7. **Fractional shares** are assumed; at ₹10 L a name is ₹66,667, so this
   binds only for very high-priced stocks.

## Full numbers (₹10 L)

| | Part A strategy | Part A benchmark | Part B strategy | Part B benchmark |
| --- | --- | --- | --- | --- |
| CAGR | 22.3% | 12.0% | 28.6% | 15.4% |
| Annualised vol | 23.5% | 19.0% | 26.6% | 22.4% |
| Sharpe (rf 0) | 0.95 | 0.63 | 1.08 | 0.69 |
| Max drawdown | −33.0% | −38.8% | −35.3% | −51.6% |
| Months positive | 120/189 | 117/189 | 125/189 | 123/189 |

Costs: 0.69% of the average book a year (Part A), 1.16% (Part B); one-sided
turnover 213% and 273% of the book a year (~2.8 and ~3.4 names a month).
Capital columns (cost only; same picks): ₹1 L 22.0% / t 2.86; ₹25 L 22.3% /
t 2.91 — the DP charge stops mattering above about ₹1 L.

## What follows

1. **Paper positional book** (next PR): the engine holds the 15 names in
   paper CNC, rebalances after each month-end close, marks to market daily,
   and reports excess against the same equal-weighted benchmark.
2. **Forward band, fixed now:** expected excess +0.82%/month, monthly sd
   3.87%. After 6 months the book **switches itself off** if cumulative net
   excess is below 6 × 0.82% − 2 × 3.87% × √6 = **−14.0%**; after 12 months,
   below 12 × 0.82% − 2 × 3.87% × √12 = **−17.0%**.
3. **Real money** remains the owner's decision. At the real balance the DP
   charge makes 15 names impractical below about ₹1 L.
