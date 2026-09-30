# Overnight ETF results — **stage 0 passes; H1 FAILS (trial 124), SETFNIF50 does not confirm; H2 FAILS (trial 125). The overnight line closes.**

**2026-09-27.** Pre-registration `prereg-overnight-etf.md` with the fetcher
(`d9a56ea`), analysis script (`b192b90`), stage 0 output, H1 (15:10:37),
H2 (15:11:02) — one run each. Data: Kite 1-minute bars, NIFTYBEES from
2015-02, SETFNIF50 from 2015-07, NIFTY 50 and INDIA VIX, through 2025-12. No
2026 bar was requested; the held-out window is untouched.

## Stage 0 — passes

| Gate | Result |
| --- | --- |
| Nights with both the 15:24 and next 09:19 bar (≥ 95%) | **98.96%** of 2,683 |
| NIFTYBEES window liquidity ≥ ₹50 lakh from 2020 | **passes**: entry/exit medians ₹94/66 lakh (2020) → ₹546/374 lakh (2025) |
| Unit changes | none |
| Charges, round trip at ₹10 lakh | 2.50 bp |

Recorded, not gated: **before 2020 NIFTYBEES traded only ₹1–2 lakh in these
windows**, so 2015–2019 minute prices are often stale; the ETF's minute
price sits a median **11–12 bp** (90th percentile ~31–33 bp) from its
index-implied value at both the entry and the exit minute.

## H1 — always hold 15:24 → 09:19 (trial 124): FAIL

| | Nights | Gross | Net | t |
| --- | --- | --- | --- | --- |
| **NIFTYBEES** | 2,655 | **+2.41 bp** | **−6.42 bp** | **−5.88** |
| with 1 bp spread per side | | | −4.42 bp | −4.05 |
| with 3 bp spread per side | | | −8.42 bp | −7.71 |
| **SETFNIF50** (confirmation) | 2,224 | +4.44 bp | −4.35 bp | −2.71 |

Net = gross − 2.5 bp charges − 4 bp spread − 2.33 bp forgone interest (RBI
repo × nights/365). Negative in both halves (−8.0, −4.8) and over 2023–25
(−5.7 bp, t −3.9); **negative in every year 2015–2025** for NIFTYBEES and in
10 of 11 for SETFNIF50.

**Why the famous overnight premium does not reach a retail ETF trade:** the
index's close-to-open return (+9.8 bp a night, L29) is measured from the
last-half-hour VWAP to the pre-open **auction** price. An ETF bought at 15:24
and sold at 09:19 captures only +2.4 bp of it: the part that exists is
concentrated in the auction open and in the move into the close, neither of
which this trade can take (NIFTYBEES is not in the pre-open auction). What
is left is smaller than the forgone interest alone.

## H2 — nightly go/no-go (trial 125): FAIL

Ridge on five inputs (day's return to 15:24, VIX versus its 20-day mean,
intraday realised volatility, calendar nights, previous night's return),
refitted each January, hold when predicted net > 1 bp. Test years
2017–2025, 2,195 nights.

| | Mean per night | t |
| --- | --- | --- |
| Gated book (held 8.8% of nights) | **−0.09 bp** | −0.15 |
| Always hold, same nights | −5.79 bp | −4.78 |
| Gated minus always (paired) | +5.70 bp | +5.34 |

The model learned to stay out, which is the right answer to a losing trade,
but it found no nights that pay: the gated book is zero. **The pass rule
requires the gated book itself to make money (t ≥ 2.24); it does not.**
Implementation detail, declared: the ridge had an unpenalised intercept
(standard practice; the pre-registration did not specify it).

## What follows

- **The overnight line closes.** Held-out and forward paper are not run;
  nothing is built. Overnight ETF holds stay allowed in scope, with nothing
  to hold.
- The finding generalises beyond this account: **the Nifty's overnight
  premium is an index-construction artefact for a retail ETF trader** —
  real in the index series, gone by the time it is tradable.
