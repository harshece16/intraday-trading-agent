# Selling NIFTY option premium with defined risk: results. **FAIL (trials 208 and 209).** Over 471 front-cycle iron condors and 477 hedged straddles, 2009–2025, held to expiry at today's costs, the mean was **−0.042 R (t −2.18)** and **−0.085 R (t −2.43)** a cycle. Both lost money even before costs. Net of costs, both lost in each half, in the last three years and on BANKNIFTY. At the money, the options were priced about fairly, so there was no premium to sell. The family is closed.

**2026-11-23.** The pre-registration `prereg-index-premium.md` was merged in #328 (`7ac5e09`) before any option price or code was in the repo. Then, in order, in #329 (`5f4ba38`):
- The option extract, built on sahab-pc from the 2009–2025 F&O bhavcopy fetched for trial 207.
- Stage 0 run 1, which stopped both arms: settlement was present on 92.3% of NIFTY cycle expiries (98% required).
- Amendment 1 (the index close as a fourth settlement source) and amendments 2–11, all before any P&L. Stage 0 then passed every gate.
- An independent pre-run review, which found nothing blocking. Its nine items were settled as amendments 12–18, and stage 0's third run gave the same counts.

The trial ran once, at 00:25 IST on 2026-11-23, from `5f4ba38`. It is logged as entries 37 and 38 of `backend/data/backtest_trials.json`. No 2026 row was fetched or read.

The option extract (`backend/data/fo_oi/fo_opt_expiry.csv.gz`, sha256 `99c7631f…a959bb9f`) and the index closes (`index_close.csv`, sha256 `71f2c7a2…c0ca879b`) are not committed. These are: `data/trial208_result.json`, `data/trial208_cycles.csv` (one row per priced cycle, both arms and both indices) and `data/trial208_stage0.json` (run 3).

## Verdict, in the pre-registration's terms

Each arm is judged on its own, NIFTY for gates 1–7 and BANKNIFTY for gate 8.

| Check | Rule | Trial 208, iron condor | Trial 209, hedged straddle |
| --- | --- | --- | --- |
| 1. Mean and t | mean net R > 0, t ≥ 2.24 | **−0.042 R, t −2.18** (471 cycles) · **fail** | **−0.085 R, t −2.43** (477) · **fail** |
| 2. Deflated Sharpe | ≥ 0.95 at N = 2 | 0.002 (Sharpe per cycle −0.10) · **fail** | 0.002 (−0.11) · **fail** |
| 3. Both halves | > 0 before and from 2017-07-01 | **−0.017** (t −0.44); **−0.049** (t −2.20) · **fail** | **−0.099** (t −1.42); **−0.081** (t −2.01) · **fail** |
| 4. Last three years | > 0 from 2023 | **−0.063 R** (156) · **fail** | **−0.125 R** (156) · **fail** |
| 5. Short cycles | > 0, cycles of ≤ 10 days | **−0.043 R** (353) · **fail** | **−0.076 R** (356) · **fail** |
| 6. Costs | > 0 at 2× costs | **−0.056 R** · **fail** | **−0.117 R** · **fail** |
| 7. Sample | ≥ 100 cycles | 471 · pass | 477 · pass |
| 8. Cross-section | > 0 on BANKNIFTY | **−0.071 R** (469, t −3.38) · **fail** | **−0.071 R** (496, t −2.01) · **fail** |

The t is the smaller in size of the plain and Newey–West figures. The halves' t values are plain, computed from the per-cycle file. Seven of eight gates fail for each arm.

Falsification rows:
- **"More cycles finish outside the sold strikes than the normal share"** applies to trial 208 (amendment 13), narrowly. The index finished beyond the condor's sold strikes in 32.2% of NIFTY cycles, against 31.7% for a normal move. The row reads: the options were priced too cheaply, not too dearly.
- **"Put side positive, call side negative"** shows in trial 209's split (+0.011 R and −0.096 R), but the total is negative, not merely insignificant.
- **"Gross above zero, net at or below zero"** (Pillai's result) does **not** apply: the gross is below zero too. No row was written for a negative gross, because the pre-registration expected a premium.

## What it means, plainly

**1. There was no premium for costs to take.** The gross is the settlement payoff at the entry day's closing prices, with no charges and no slippage. It was negative for both arms on both indices: −0.028 R and −0.054 R on NIFTY, −0.058 R and −0.040 R on BANKNIFTY.
- Costs were small: 7% of the condor's credit and 2% of the straddle's.
- A cheaper broker, the old STT rate or a better fill could not rescue it. Each only shrinks a cost the trade never earned back.

**2. The options were not priced for more movement than arrived.**
- **The straddle, trial 209.** It sold a call and a put at the strike where they cost the same. That pair alone lost 0.039 of its price before costs (t −1.04, BANKNIFTY −0.050, t −1.29). The index's average move to expiry was 1.04× the straddle's price. The median move was 0.86×, so the seller won 57% of the time, but the large moves cost more than the small ones paid.
- **The bought wings** gained slightly before costs (+0.006 and +0.024 of the straddle price), so the hedge did not cause the loss.
- **The condor, trial 208.** The index finished beyond its sold strikes in 32.2% of NIFTY cycles (normal 31.7%) and beyond its bought wings in 15.9% (normal 13.4%). That is as many breaches as a fairly priced option implies, with fatter tails.
- The +1.96 vol points of implied over realised volatility in the 2026-09-26 sweep compares 30-day VIX with realised volatility. It does not show up as a premium in front-cycle options sold at the expiry-day close. (Computed after the run from `trial208_cycles.csv`, as explanation only. Not a gate, and it selects nothing.)

**3. The usual short-premium shape, with no edge.**
- **Condor:** won 75% of cycles, but the mean win was +0.18 R against a mean loss of −0.71 R. 10.8% of cycles lost 0.9 R or more. The deepest drawdown was −24.5 R.
- **Straddle:** won 46% (+0.65 R against −0.71 R), with a −47.2 R drawdown.
- **In money:** at today's NIFTY level and lot, that is about ₹550 lost per lot per cycle for the condor and ₹1,600 for the straddle.

**4. It is not a regime story.** Both halves, the last three years, short cycles and long cycles are all negative for both arms. Of 17 years, the condor lost in 12 and the straddle in 11.
- The call side lost most: the index rose, and it finished above the sold call strike more often (18.4%) than below the sold put strike (13.8%).
- The put side was near zero (−0.009 R and +0.011 R). That is no basis for a put-spread trial: choosing it now would be choosing a rule after reading its return.

| | 208 NIFTY | 208 BANKNIFTY | 209 NIFTY | 209 BANKNIFTY |
| --- | --- | --- | --- | --- |
| Cycles (skipped) | 471 (7) | 469 (71) | 477 (1) | 496 (44) |
| Mean net R, t (plain / NW) | −0.042, −2.18 / −2.24 | −0.071, −3.38 / −3.41 | −0.085, −2.43 / −2.61 | −0.071, −2.01 / −2.21 |
| Gross R / cost R | −0.028 / 0.014 | −0.058 / 0.013 | −0.054 / 0.031 | −0.040 / 0.031 |
| At 1× / 2× / 3× cost | −0.042 / −0.056 / −0.070 | −0.071 / −0.084 / −0.097 | −0.085 / −0.117 / −0.148 | −0.071 / −0.102 / −0.133 |
| Call side / put side R | −0.033 / −0.009 | −0.054 / −0.018 | −0.096 / +0.011 | −0.076 / +0.005 |
| Win rate, mean win / loss | 75.4%, +0.18 / −0.71 | 72.3%, +0.19 / −0.76 | 46.1%, +0.65 / −0.71 | 47.8%, +0.66 / −0.74 |
| Cycles losing ≥ 0.9 R | 10.8% | 13.9% | 22.9% | 23.0% |
| Deepest drawdown, longest losing run | −24.5 R, 5 | −33.8 R, 4 | −47.2 R, 8 | −38.9 R, 8 |
| Credit ÷ max loss, cost ÷ credit | 0.19, 7.3% | 0.21, 6.3% | 1.30, 2.4% | 1.32, 2.4% |
| Mean P&L, bp of the forward | −3.3 | −8.2 | −9.5 | −5.1 |
| ₹ per lot per cycle, at today's level | −553 | −1,462 | −1,603 | −909 |
| Skipped cycles at the worst case (amendment 17) | −0.056 | −0.195 | −0.087 | −0.149 |

R is net P&L over the money at risk (the wider spread less the credit), so −0.042 R lost 4.2% of it per cycle. Rupees use NIFTY 25,938.85 × 65 and BANKNIFTY 59,171.25 × 30.

## What went wrong, and what was checked

- **The settlement gap (amendment 1).** Old-format weekly expiries before February 2020 carry no final settlement price. The index close fills them, and where both exist it equals the file's value to within 0.01 point on 440 of 440 NIFTY and 396 of 396 BANKNIFTY expiries. Its median gap from the expiring series' own put-call parity is 0.037%, about as close as the file's own values (0.028%).
- **Check 4's BANKNIFTY count (amendment 12)** decided nothing. Both arms fail gates 1–6 on NIFTY, so the reading that let gate 8 be met is moot.
- **Skipped cycles cluster in turbulent years (amendment 17).** NIFTY skipped only 7 and 1. Even if each had earned the arm's average maximum gain, the means stay negative (−0.039 R and −0.082 R; a hand bound, not registered). BANKNIFTY skipped 71 and 44, mostly 2009–17 when its far strikes barely traded.
- **Entry at the closing price, not the bid or ask.** The slippage term stands in for the spread. With the gross already negative before any slippage, a truer fill can only make it worse.
- **Today's costs and lots on the whole history.** This was written into the pre-registration. It does not touch the sign either, for the same reason.
- **The rounded DSR (amendment 15).** The independent review found that `evaluation.deflated_sharpe_ratio` rounded the DSR to three places before gates read it, so a DSR just under 0.95 (0.9496, say) would have passed. It is fixed for the whole project. No recorded verdict sat in that band: the nearest is trial 126's 0.952, which passes either way.
- **The one run.** The guard (amendment 14) checked the log and both output files, and the entries were logged before anything was written or shown.

## What next

Nothing goes to paper. `FNO["enabled"]` stays off, no held-out 2026 window is spent, and the "index option premium selling" family is closed at N = 2.

Another structure (put spreads only, other strikes, stops, a VIX or event filter, monthly cycles only, another entry day) would be a new hypothesis at N = 3 (t ≥ 2.39) and would need its own pre-registration. Nothing here suggests one would pass: the at-the-money straddle itself was priced about fairly, so a hedged seller has nothing to collect. Trial 126's momentum book remains the project's one surviving line.
