# Pre-registration — 3h: does new information (market breadth and intermarket moves) predict the intraday session?

**Written and committed before any code for this measurement exists.** On
2026-09-25 the owner asked to stop working on the Varsity checklist and focus
on the methods page's "Read, but not (yet) built in" list. Two items on that
list bring information the search never used:

- **Market breadth** (Murphy ch 10): the advance-decline ratio, the McClellan
  Oscillator and TRIN, computed over **every NSE equity**, not the watchlist.
- **Intermarket analysis** (Murphy ch 17): the dollar, crude, bond yields and
  foreign equities.

The 76-configuration search concluded that "a next round has to change the
**information**, not the rule". This is the first test of that kind. It runs
at the owner's direction without external reviewer review.

**This is a measurement, research look L35. It is not a strategy trial.** It
selects no parameter and trades nothing. If a predictor passes, turning it into
a rule is a separate, pre-registered trial.

The other list items are **not tested**, with reasons recorded in the results:
Elliott Wave (subjective counts), Point & Figure and time cycles (price-only,
the class the search already falsified), and ML models (the same price inputs).

## The target — what an intraday engine could capture

For each selection session D: the **equal-weighted mean, over NIFTY 100
stocks in the Kite cache, of the return from the close of the 09:15 bar
(09:20) to the close of the 15:05 bar (15:10)**, in basis points. Opening
gaps are excluded; an intraday engine cannot trade them.

## The predictors — all known before 09:20 on D, fixed now

| # | Predictor | Source | Value used for session D |
| --- | --- | --- | --- |
| P1 | **Breadth ratio** adv / (adv + dec) | NSE bhavcopy, series EQ, CLOSE vs PREV_CLOSE | session D−1 |
| P2 | **McClellan Oscillator**: EMA19 − EMA39 of (adv − dec) | same | session D−1 |
| P3 | **TRIN**: (adv / dec) ÷ (up volume / down volume), volume = TTL_TRD_QNTY | same | session D−1 |
| P4 | **India VIX** change, % | yfinance `^INDIAVIX` | close D−1 vs D−2 |
| P5 | **S&P 500** return, % | yfinance `^GSPC` | the last US session dated **before** D |
| P6 | **USD/INR** change, % | yfinance `INR=X` | the last bar dated before D |
| P7 | **Crude (WTI)** return, % | yfinance `CL=F` | the last bar dated before D |
| P8 | **US 10-year yield** change, bp | yfinance `^TNX` | the last bar dated before D |

- EMAs use the standard α = 2/(n+1), seeded with the first value. Bhavcopies
  are fetched from **2024-06-01**, so the McClellan EMA has at least 60
  sessions of warm-up before the first scored session.
- A session with a predictor missing is dropped for that predictor only.
  Sessions used are reported per predictor.

## The statistic, fixed now

For each predictor, sessions are split into **terciles** of the predictor on
the selection sample.

- **Spread** = mean target in the top tercile − mean target in the bottom
  tercile, with a Welch t-statistic.
- **Family**: the 8 spreads. **Benjamini-Hochberg at 5%**, two-sided.

## Pass rule — both parts, fixed now

A predictor **PASSES** only if:

1. its spread **survives BH at 5%**, and
2. **it is tradable**: the tercile the spread points to has a mean target with
   the **right sign and at least 16.63 bp in magnitude**, the cash round trip.
   The top tercile is used for a positive spread (go long there); the bottom
   tercile for a negative one (go short there, or long if its mean is
   positive, whichever the spread implies).

Rule 2 is because the engine takes one position per stock per day. Trading on
the signal would earn the conditional mean and pay a full round trip on every
stock. **A significant spread whose extreme tercile cannot pay 16.63 bp is not
tradable**, the same test `atr_pct` failed in phase 2.

## Data gate, a hard halt before any statistic

- Bhavcopies must exist for **≥ 95% of selection sessions**, each with **≥
  1,500 EQ rows**. Otherwise stop and report.
- For P4–P8, the yfinance series must cover **≥ 90%** of selection sessions.
  A predictor below that is dropped and reported, not imputed.

## What follows, decided now

- **No predictor passes** → information of this kind does not move the NSE
  intraday session enough to pay for a round trip. Reported as such. Breadth
  stays a context label on the dashboard; no rule is built.
- **A predictor passes** → confirm it on **Universe B** (the 113 F&O names
  outside NIFTY 100, `universe_b.csv`) with the same code. A Universe B pass
  earns a pre-registered strategy trial (118), whose selection pass, and only
  that, earns the held-out look.
- **Falsification:** if a spread is significant but its extreme tercile is
  under 16.63 bp, it is reported as a ratio of cost, and no filter or tweak is
  proposed from it.

## Accounting

- **L35**, one run. The held-out window (2026-01-02 onward) is not loaded.
- Raw bhavcopies are cached under `backend/data/bhav/` (gitignored). The
  derived daily breadth table is committed so the numbers can be reproduced.
