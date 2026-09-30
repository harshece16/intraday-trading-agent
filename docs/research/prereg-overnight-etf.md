# Pre-registration — the Nifty overnight premium, held in an ETF (trials 124–125)

**Written 2026-09-27, before any overnight return is computed from the
minute data.** Owner decision 2026-09-26: overnight ETF holds are in scope
(paper), judged at the family level
(`decision-2026-09-26-overnight-and-significance.md`).

## What is already known, and what is not

The Nifty's return comes overnight (L29: +9.77 bp a night, t 11.45,
2007–2025, index level) — that is **not** in question and is not what this
tests. What has never been measured is whether a real, retail-tradable
version keeps any of it: an **ETF**, bought in the last minutes of the
session and sold **after 09:15** (NIFTYBEES is not in the pre-open auction,
verified 2026-09-26), paying delivery charges, the spread, and the interest
the money could have earned. The reviewers' back-of-envelope on index data
(prediction-engine sweep, completeness critic) put 2023–25 at about +2.7 bp
a night after the cost of capital (t ≈ 1.3) and 2025 negative. **The prior
is weak.**

## Family and count

Family "Nifty overnight premium": H1 and H2 below, **N_family = 2** (two-sided
Bonferroni at 5%: **t ≥ 2.24**). L29/L30 measured the index split
descriptively with no pass rule and are not counted.

## Data (selection sample only)

`backend/data/overnight_1m.db`: Kite 1-minute bars for NIFTYBEES,
SETFNIF50, the NIFTY 50 index and INDIA VIX, fetched 2026-09-27 for
2015-01-01 → 2025-12-31 (NIFTYBEES from 2015-02-02, SETFNIF50 from
2015-07-27). No 2026 bar has been requested.

## Stage 0 — facts only, no overnight return computed

1. **Coverage:** ≥ 95% of NIFTYBEES sessions from 2015-03 to 2025-12 have
   both the 15:24 bar and the next session's 09:19 bar.
2. **Unit changes:** discontinuities in NIFTYBEES/SETFNIF50 daily closes
   (a ratio to the index outside ±15% of its 20-day median) are listed; any
   night spanning one is excluded.
3. **Liquidity:** median traded value (volume × close) in the 15:20–15:29
   window and in the 09:16–09:20 window, per year. **Gate: median ≥ ₹50 lakh
   in both windows** in every year from 2020 on (a ₹10 lakh order then
   stays under a fifth of the window).
4. Reported, not gated: the ETF's deviation from its index-implied price at
   15:24 and 09:19 (ratio to its 20-session median ratio); Zerodha's BTST
   rule for ETFs; the RBI policy repo rate history used for the cost of
   capital.

If gate 1 or 3 fails, the line stops before any return is computed.

## H1 — always hold overnight (trial 124)

Every session d with a next session d+1: **buy NIFTYBEES at the close of
the 15:24 bar on d; sell at the close of the 09:19 bar on d+1.**

net bp per night = gross − charges − spread − cost of capital, where
- **charges** (Zerodha CNC, ETF, ₹10 lakh): stamp 0.015% on the buy, STT
  0.001% on the sell, NSE transaction 0.00307% each side, SEBI, GST on
  transaction + SEBI, DP ₹15.34 per sell — about 2.4 bp;
- **spread** 2 bp per side (4 bp a round trip), a fixed assumption until the
  forward order-book samples (README §81) measure it; 1 and 3 bp per side
  reported as sensitivity;
- **cost of capital** = RBI repo rate × calendar nights ÷ 365.

**Pass (all):** mean > 0 with **t ≥ 2.24**; corrected Deflated Sharpe
≥ 0.95 at N = 2; positive in both halves (split at the median night);
**positive over 2023-01 → 2025-12**; ≥ 500 nights. **Confirmation:** the same
rule on SETFNIF50: mean > 0, t ≥ 1.65.

## H2 — a nightly go/no-go model (trial 125)

At 15:24 on d, five inputs: (1) the Nifty's return 09:15 → 15:24 on d;
(2) INDIA VIX at 15:24 minus its 20-session mean; (3) realised volatility
of 1-minute Nifty returns 09:15 → 15:24 on d; (4) calendar nights to the
next session; (5) the previous night's Nifty return (15:24 on d−1 → 09:19
on d). Ridge regression of H1's net bp on the z-scored inputs, penalty
λ = 0.1 × rows, **refitted each January on all earlier years (at least
two)**; first test year 2017. **Hold only when the predicted net exceeds
1 bp.**

**Pass (all):** over the test nights, the gated book's net mean > 0 with
t ≥ 2.24, **and** the paired nightly difference (gated − always-hold,
skipped nights counting 0) mean > 0 with t ≥ 2.24, positive in both halves.

## Held-out and forward

Only if H1 passes **and** SETFNIF50 confirms: fetch 2026 bars and run H1
on 2026-01-02 → the last complete session, **excluding the sessions already
read** (2026-07-30, 07-31, 09-17 → 09-25); confirms if the mean is positive.
Then a paper overnight book in the engine, with a forward band. Real money
remains the owner's decision.

## Falsification branches

- Stage 0 fails → stop; the overnight line closes on liquidity or data.
- H1 fails overall → the premium does not survive retail costs in an ETF;
  the line closes.
- H1 passes but 2023–25 is not positive → decayed; FAIL (the safeguard).
- H1 passes but SETFNIF50 does not confirm → not robust to the vehicle; no
  held-out spend.
- H2 fails → no prediction engine for the overnight hold; if H1 passed, the
  always-hold version alone goes forward.

## Code and order

`backend/research/overnight_data.py` (the fetch, already run) and
`backend/research/overnight_etf.py` (stage 0, H1, H2), committed after this
file; one run of each stage.
