# The scanner audit's four intraday features and the 09:45 gap reversal do not rank the next intraday move past cost — research look L49: FAIL, 0 of 13 tests

**2026-09-30.** Pre-registration `prereg-scanner-features.md` (`dc06a10`, before any code), amendment 1 (`6baae5a`, before the code was committed), amendment 2 (`2e3eeba`, after stage 0 run 1 halted at check 4, before any feature was computed), amendment 3 (`0fb4ecb`, after the independent review, before the pass) with the N5 correction (`30a5f27`). Code `scanner_features_l49.py` (`985bb62`). Stage 0 run 1 halted as the text required (`data/l49_stage0_run1.json`); run 2 passed all nine checks (`data/l49_stage0.json`, `8103c21`). The independent review approved the text, the code and stage 0. The one measurement pass ran on the Mac at 21:06 IST, outside market hours, at `nice 15`, with no rerun flag. Record: `data/l49_result.json` (`99d364d`). Nothing dated 2026 was loaded.

## Verdict, in the pre-registration's terms

Bar: top-minus-bottom quintile spread above **33.26 bp** (two legs at 16.63 bp), t > 2 over at least 60 sessions, positive in both halves, a Benjamini–Hochberg survivor at q = 0.10 across the 13 tests, and a partial IC given m60 that is positive with t > 2. Every test has 78 sessions.

| Test | Registered sign | Spread, bp (t) | Halves, bp | Rank IC (t) | Partial IC given m60 (t) | BH | Gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gap, 15 min | + continuation | −0.40 (−1.07) | −0.79 / −0.01 | −0.011 (−2.01) | −0.011 (−2.00) | no | **fail** |
| gap, 30 min | + | −0.48 (−0.84) | −0.77 / −0.19 | −0.017 (−3.04) | −0.016 (−2.76) | no | **fail** |
| gap, 60 min | + | −0.93 (−0.98) | −2.32 / +0.46 | −0.018 (−2.63) | −0.016 (−2.39) | no | **fail** |
| rvol, 15 min | + | +0.49 (1.40) | +0.19 / +0.79 | +0.001 (0.20) | +0.003 (0.45) | no | **fail** |
| rvol, 30 min | + | **+1.27 (2.26)** | +1.18 / +1.36 | +0.003 (0.40) | +0.004 (0.62) | **yes** | **fail** |
| rvol, 60 min | + | +0.30 (0.35) | +0.16 / +0.44 | −0.007 (−1.08) | −0.005 (−0.73) | no | **fail** |
| vwap_dist, 15 min | + continuation | +0.12 (0.21) | +0.85 / −0.62 | −0.011 (−1.27) | −0.003 (−0.40) | no | **fail** |
| vwap_dist, 30 min | + | **−2.29 (−2.77)** | −0.04 / −4.54 | −0.041 (−4.54) | −0.025 (−2.92) | yes | **fail** |
| vwap_dist, 60 min | + | **−3.53 (−2.81)** | −2.25 / −4.82 | −0.043 (−4.37) | −0.026 (−2.71) | yes | **fail** |
| sector, 15 min | + continuation | **−2.04 (−3.87)** | −1.77 / −2.32 | −0.040 (−4.79) | −0.039 (−4.92) | yes | **fail** |
| sector, 30 min | + | **−5.70 (−6.09)** | −3.76 / −7.64 | −0.080 (−8.13) | −0.075 (−8.10) | yes | **fail** |
| sector, 60 min | + | **−8.29 (−5.88)** | −5.80 / −10.78 | −0.087 (−7.71) | −0.082 (−7.41) | yes | **fail** |
| gap_reversal, 09:45 → 60 min | + reversal | −2.98 (−0.97) | −2.71 / −3.25 | +0.005 (0.26) | −0.016 (−1.10) | no | **fail** |

**No test clears. No trial is spent.** Research look L49 is closed.

Six tests survive BH: rvol at 30 minutes, vwap_dist at 30 and 60, and sector at all three. Five of the six have **the opposite of the registered sign**, and the spread condition is signed. None of the six is within a quarter of the bar. The largest spread in either direction is sector at 60 minutes, **8.29 bp, a quarter of the 33.26 bp bar**. No single quintile clears 16.63 bp with t > 2 on its own, so no single-side note is earned.

### F5, the 09:45 gap reversal, condition by condition (amendment 3)

| Condition | Value | Met? |
| --- | --- | --- |
| Spread above 33.26 bp | −2.98 bp | no |
| t > 2 | −0.97 | no |
| At least 60 sessions | 78 | yes |
| Positive in both halves | −2.71 / −3.25 bp | no |
| BH survivor across 13 | p 0.33 | no |
| Partial IC given m60 > 0 with t > 2 | −0.016 (t −1.10) | no |

F5 fails on the spread itself, not only on the partial IC. So amendment 3's special reading ("ranks past cost but cannot be told apart from m60's own reversal") does not apply, and §8's reading stands for F5. **The previous-official-close → 09:45 reversal, ranked at 09:45, does not rank the next 60 minutes past cost.** Its rank IC is +0.005 (t 0.26), which is nil. As amendment 3 says, this is the sweep's form, not the outside repository's H2 (close-to-open, held 10:00 to 15:20). **H2 as its source defined it is not closed by this look.**

## What the numbers say, plainly

- **None of the five features is worth trading intraday.** A long top fifth and short bottom fifth would have earned between −8.3 and +1.3 bp a pair before costs. The pair costs 33.26 bp.
- **The test could see small effects.** The smallest spread detectable at t = 2 was 0.7 to 2.8 bp for the four audit features and 6.1 bp for F5, which has only one decision time a day. The bar is 5 to 47 times those. These are measured absences, not a lack of power.
- **Two of the scanner's scoring rules point the wrong way, and by very little.** The scanner scores a top-three sector for a long and "above VWAP" for a long.
  - Stocks whose industry had risen most since yesterday's close did **worse** over the next 15 to 60 minutes. The rank IC is −0.04 to −0.09 (t −4.8 to −8.1), and negative in 82% of sessions at 30 and 60 minutes, in both halves.
  - Stocks above their session VWAP also did slightly worse at 30 and 60 minutes (IC −0.04, t about −4.5).
  - The last hour's move does not explain the sector result: its partial IC barely changes (−0.082 against −0.087 at 60 minutes).
  - Both results fail the gate twice over, on sign and on size. The sector effect, the larger, is 8.3 bp at 60 minutes: a quarter of what a pair costs. **A reversed-sign version is a new hypothesis this look did not register, and on this sample's size it would not clear either.**
- **Relative volume is noise.** Its 30-minute spread of +1.27 bp has the registered sign, both halves positive, t 2.26 and a BH survival. That is still 4% of the bar. Its rank IC is 0.003 (t 0.4), and the spread comes from the bottom fifth: low-volume stocks drifted down 1.3 bp. The BH survival also leans on the two-sided p-values (below).
- **The opening gap, in the scanner's continuation sense, does nothing useful.** The rank IC is slightly negative (−0.011 to −0.018, t −2 to −3), in the reversal direction, but the spreads are under 1 bp and insignificant.
- **For scale:** on 84 sessions before the sample, the positive control (the true target plus 5 bp of noise) earned 59, 82 and 115 bp at the three horizons. The best absolute spread here, 8.3 bp at 60 minutes, is 7% of that.

## How this fits with what was known

The audit expected none of the four to clear (§6 item 3), and the sweep expected F5 to fail. Both expectations held. This look joins:
- trial 35: opening-range breakout on relative volume, FAIL;
- trials 93–116: VWAP breakout on volume, 0 of 24;
- L31 and L32: intraday momentum, cross-sectional and time-series, withdrawn at stage 1;
- L8: 10-day relative strength, IC −0.009.

**Nothing in the audit's intraday selection framework (gap, relative volume, VWAP, sector, opening range, relative strength) ranks NIFTY 100 stocks within the hour by anything close to the cost of trading them.** The audit's §6 item 4 said that if none cleared, the intraday selection question is closed. It is closed. The rebuilt checklist's tags for these rules become **failed**.

## What went wrong, and what to read with care

- **Stage 0 run 1 halted, correctly, on a false assumption in my own design.** §3 used NSE's LAST to carry the official close onto Kite's price basis. LAST is not the trade that ends Kite's last bar: they agree exactly on only 58% of stock-days. Amendment 2 replaced LAST with the median of the open, high and low ratios, which agree to 0.00 bp at the median, and widened the ex-date exclusion to the session before. This was fixed before any feature was computed, and run 2 passed.
- **Run 1 also loaded the 2026-01-01 session's bars.** Its cutoff was the held-out start, not the end of 2025 as the text said. No check used them, and nothing from 2026-01-02 on was read. Amendment 2 moved the cutoff.
- **N3, survivorship.** The universe is today's 100 cached names. Six point-in-time members are missing on every session (BAJAJHFL, HAVELLS, ICICIGI, JSWENERGY, LICI, NAUKRI), and five more before 2025-09-30. They are absent from the sample and as sector peers.
- **N4, pooled decision times.** The six decision times are pooled per session, as L40 did. For vwap_dist and sector, the top and bottom fifths hold different mixes of times of day (the review's median dissimilarity is 0.29 and 0.28). So **part of those two negative spreads can be the market's own move between times of day, not the stocks' ranking.** This look cannot separate the two. It is one more reason not to read their sign as an edge.
- **N5, F4 is not free of the stock's own move.** Within an industry, F4 ranks stocks by minus their own move. In the four two-member industries (Services, Consumer Durables, Realty, Chemicals) it is simply the partner's move. The within-industry part holds about 12% of F4's rank variance (the reviewer's measure); the rest ranks industries against each other. No decomposition of the negative sector result was computed; that would be a new look.
- **N6, two-sided BH.** BH ran on two-sided p-values, as the harness does. The five strongly wrong-signed tests rank first and loosen BH's step for the rest. That is how rvol at 30 minutes (p 0.024) survives: with one-sided p-values, the wrong-signed tests would not have ranked first and it would not. It fails on the spread either way.
- **N8, rule 3.6.** F4 is the audit's "sector strength" (the scanner's sector rank). It is not the audit's rule 3.6 (the stock's change minus its sector's change), which runs as a live shadow under #219. This look does not test rule 3.6.
- **Industry labels** are NSE's current ones, not point-in-time.
- **Sample.** This is the selection sample only: 78 sessions, September to December 2025. The costs rest on `costs.py`, whose rates are unverified against the broker's tariff. The 2026 window is not read.

## For the owner

Nothing here goes into Trader Sahab. No feature passed, so no trial follows. Even a pass would have been a research-look pass: under the protocol, nothing enters the engine without its own pre-registered trial, the family gate and your confirmation.

Two practical points:
- **The intraday selection question from the 2026-09-28 audit is closed.** Gap, relative volume, VWAP distance and sector strength do not pick stocks that move past the cost of a round trip within the hour. Selection work is better spent on the delivery book, where the momentum rule has passed its tests (the audit's §6 item 4).
- **The scanner's sector and VWAP points lean slightly the wrong way.** The live scanner still awards points for a top-three sector and for trading above VWAP in the trade's direction (`scanner.py` `intraday_score`). On this sample both went slightly the other way at 30 to 60 minutes, by 2 to 8 bp. That is far too small to trade in reverse, but it means those points add nothing. Since #219 the scanner sets no side, so they no longer drive an entry. Whether to drop them from the display score is your call; it changes no order.
