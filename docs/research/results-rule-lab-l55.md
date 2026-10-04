# L55, the rule lab's historical search, look 1 — no survivor among 104,655 combinations; every eligible single rule loses after costs; the stepdown itself was vacuous

**2026-10-05.** Pre-registration `prereg-rule-lab.md` (base `3584b57`, amendments 1–5 and the correction of 02:10 IST). Code `backend/research/rule_lab_screen.py` at `b065fff` (the merge of #272). **One run**, 02:23–02:30 IST (450 s), on the Mac, from the detached worktree `l55-run` with a clean tree; the record names the commit and the family hash, which matched stage 0's. Record: `data/l55_result.json`, committed byte-for-byte. Not re-run, and it will not be.

## Verdict

**In the reviewer's words, which are the record's:** RW stepdown vacuous (critical value 7.17e7 from n ≤ 6 sets in the unfiltered family); no survivor under the prereg as written; the evidence that no edge exists is the 105 powered singles, all negative net of costs (best −12.8 bp, t −4.4), and PBO 0.33; whether any ≥ 200-trade combination has a positive mean was not tested.

**No combination survives.** Of 104,655 combinations of the 107 conditions × 2 exits (102,296 enumerated, 2,359 reached by the greedy search), **none has a positive mean net return per trade with 200 or more trades**, so none is eligible and none is rejected by the Romano–Wolf stepdown. The probability of backtest overfitting is 0.33. **The 2026 confirmation pass does not run**: there is no survivor to confirm, and `--confirm-2026` will not be invoked. No historical candidate enters the forward lab. No trial is spent; the count of record stays **202**.

In the prereg's terms (§5, amendment 3): no rule passes D (there is no D/C split any more — amendment 3 made it one discovery period, 2024-09-24 to 2025-12-31, 316 sessions, 2.3 million stock-bars, with 2026 as the one confirmation window); the expectation written in §0, *no rule passes*, holds.

| | |
| --- | --- |
| Combinations evaluated | 104,655 (enumerated 102,296, greedy 2,359) |
| Eligible combinations (n ≥ 200, G ≥ 40, mean > 0, both halves positive) | **0** |
| Survivors | **0** |
| Single rules with ≥ 200 trades | 105 of 107 (Y15L and Y15S never fire: DEMA200 needs more history than the input holds, as amendment 4 expected) |
| Single rules with a positive net mean | **0 of 105** |
| Best single rule, net | R17 gap up fades, short: **−12.8 bp** a trade, t −4.4, 3,753 trades |
| Median single rule, net | −16.6 bp a trade (the round trip is 16.6 bp: the median rule earns nothing before costs) |
| Worst single rule, net | R16 gap and go, down: −27.8 bp, 1,124 trades |
| Total single-rule trades scored | 4.93 million |
| PBO (CSCV, 16 blocks, 12,870 splits) | 0.33 |

## What the numbers say, plainly

- **The round trip eats everything.** The 105 eligible single rules have a median net of −16.6 bp a trade, within a tenth of a basis point of the 16.6 bp cost. Before costs the typical rule earns about zero; this is the same finding as the candlestick control of trials 128–202 (+0.2 bp gross), now over 4.9 million trades and 105 rules instead of 5,074 trades and one.
- **The rare, "hand-crafted" rules do worst.** The gap rules with the fewest trades are the most negative: R16 −27.8 bp, O07L −24.7 bp, O04L −24.4 bp, O02L −24.0 bp, Y11S −17.3 bp. Y11S (three up days, gap up, first red bar broken) earned 0.7 bp gross over 240 trades.
- **The catalog's rules are not better than the lab's own.** Cohort 2's best is Williams' volatility breakout, short, at −13.4 bp (gross +3.2); its filters alone (F01–F09) sit at −15.8 to −17.5 bp over 120,000–250,000 trades each, which is the base rate of a random entry on these bars.
- **Combining conditions did not help.** No pair, triple, named combination (CMB-3) or greedy set reached a positive net mean with 200 trades. The combinations the record ranks highest are 2-trade accidents (below).
- **Gross is not shown by the record.** The record carries net figures only; the gross column in the tables is net + 16.6 bp, the pre-registered round trip, and is approximate for the two R3 rules, whose cost depends on the exit price.

## Two reporting defects in the record, disclosed, not fixed by a re-run

1. **`top` and `best` are ranked by raw t with no minimum-trade filter.** The record's "best" is the triple Y02S + Y04S + Y19S with the R3 exit: **2 trades**, t 2,761. All 50 rows of `top` have 2 to 6 trades. None is eligible (eligibility needs 200 trades), so nothing was judged on them, but the field is misleading and `dsr_best` is `None` for the same reason. The eligible single-rule tables below are the figures to read.
2. **The Romano–Wolf critical value is 71,694,244.** Combinations with 2 trades and a near-zero standard error enter the bootstrap maximum, so the stepdown's bar is astronomically high and the test is **vacuous**: nothing could have passed it. The verdict is unaffected, because no combination was eligible in the first place (every one with 200 trades has a negative mean), but had one been, this run could not have rejected it. The forward lab has the same shape of test (`rule_lab.romano_wolf`, all registered rules in the maximum, including rules with few trades).
3. (Smaller.) The record's per-rule block (`rules`) has n, mean, t and passed, not the halves; the halves exist only in the `top` rows. The tables below therefore show no halves. Nothing in the halves could turn a negative mean into a pass.

**Amendment 6 (written 2026-10-05 after this result, in the prereg) declares look 2 of L55**: a filtered re-judgement of the same data, counted as a deliberate second look, with sets of ≥ 200 trades and ≥ 40 sessions in the bootstrap maximum and a ≥ 5-effective-cluster guard per replicate; it will be run by the owner after its review and written up as look 2. The same amendment fixes the forward lab's screen. The original proposal, for the record:

**Proposed amendment to the forward screen** (which is at least 40 lab sessions away, so there is time for a review): a combination or rule enters the Romano–Wolf maximum **only if it has at least the stage's minimum trades** (200 at the screen, 100 at confirmation; `MIN_TRADES` in L55). Rules below the minimum stay in the family count and cannot pass, but do not set the bar. Also: rank `top` by t among eligible combinations only, and write the halves into the per-rule block. The amendment should be written and reviewed before any forward figure is judged; the forward lab's running page is unaffected, because it tests nothing before the look.

## The eligible single rules

Net bp a trade after `config.COSTS` (slippage and Zerodha MIS charges, about 16.6 bp a round trip); t clustered by session. Sorted by net within cohort. Every one is negative.

### Cohort 1: 20 eligible rules, 0 with a positive net mean

| Rule | Condition | Side | Exit | Trades | Net bp a trade | Gross bp (net + 16.6) | t |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R17 | Gap up fades | Short | H30 | 3,753 | -12.8 | +3.8 | -4.4 |
| R18 | Gap down fills | Long | H30 | 2,139 | -13.4 | +3.2 | -2.8 |
| R14 | Opening-range breakdown | Short | H30 | 17,680 | -14.8 | +1.8 | -10.8 |
| R20 | Pullback to a falling EMA20, stop above the bar, 3R target | Short | R3 | 28,831 | -15.3 | +1.3 | -20.1 |
| R12 | Trend turns down (below VWAP, EMA20 falling) | Short | H30 | 73,011 | -16.1 | +0.5 | -34.6 |
| R06 | Bearish marubozu | Short | H30 | 27,423 | -16.3 | +0.3 | -25.8 |
| R02 | Bearish engulfing | Short | H30 | 123,051 | -16.5 | +0.1 | -44.5 |
| R10 | Sellers in control (volume 2x on a down bar) | Short | H30 | 79,328 | -16.5 | +0.1 | -39.5 |
| R09 | Buyers in control (volume 2x on an up bar) | Long | H30 | 80,192 | -16.6 | +0.0 | -39.0 |
| R04 | Shooting star | Short | H30 | 14,842 | -16.6 | +0.0 | -31.0 |
| R08 | Inside-bar breakdown | Short | H30 | 85,831 | -16.6 | +0.0 | -44.7 |
| R05 | Bullish marubozu | Long | H30 | 25,080 | -16.9 | -0.3 | -33.7 |
| R13 | Opening-range breakout | Long | H30 | 15,715 | -16.9 | -0.3 | -18.8 |
| R11 | Trend turns up (above VWAP, EMA20 rising) | Long | H30 | 70,110 | -17.1 | -0.5 | -40.1 |
| R07 | Inside-bar breakout up | Long | H30 | 82,214 | -17.4 | -0.8 | -45.5 |
| R01 | Bullish engulfing | Long | H30 | 121,011 | -17.5 | -0.9 | -47.5 |
| R03 | Hammer | Long | H30 | 17,294 | -17.7 | -1.1 | -35.1 |
| R19 | Pullback to a rising EMA20, stop below the bar, 3R target | Long | R3 | 28,696 | -17.9 | -1.3 | -25.7 |
| R15 | Gap and go, up | Long | H30 | 2,205 | -19.2 | -2.6 | -5.7 |
| R16 | Gap and go, down | Short | H30 | 1,124 | -27.8 | -11.2 | -3.6 |

### Cohort 2: 85 eligible rules, 0 with a positive net mean

| Rule | Condition | Side | Exit | Trades | Net bp a trade | Gross bp (net + 16.6) | t |
| --- | --- | --- | --- | --- | --- | --- | --- |
| O01S | Williams volatility breakout (0.6 x yesterday's range), short | Short | H30 | 9,332 | -13.4 | +3.2 | -9.8 |
| Y26S | VWAP side, level break, relative volume 1.5, short | Short | H30 | 7,998 | -14.5 | +2.1 | -14.9 |
| O06S | Narrow CPR trend day, opening-range break, short | Short | H30 | 1,253 | -14.6 | +2.0 | -8.0 |
| O08S | Supertrend(10,3) flip, 15-minute, short | Short | H30 | 9,071 | -14.6 | +2.0 | -13.4 |
| Y12BS | Narrow CPR, close through R1/PDH (S1/PDL), short | Short | H30 | 7,107 | -14.7 | +1.9 | -16.6 |
| Y02S | EMA9/15 trend, touch of EMA9, trigger candle, short | Short | H30 | 15,908 | -14.9 | +1.7 | -14.3 |
| Y26L | VWAP side, level break, relative volume 1.5, long | Long | H30 | 9,175 | -14.9 | +1.7 | -19.0 |
| O09S | TTM squeeze release, 15-minute, short | Short | H30 | 5,112 | -15.0 | +1.6 | -17.4 |
| O04S | Raschke 80-20, short | Short | H30 | 921 | -15.1 | +1.5 | -5.2 |
| O01L | Williams volatility breakout (0.6 x yesterday's range), long | Long | H30 | 8,003 | -15.3 | +1.3 | -13.5 |
| Y09S | First-hour sweep reversal, short | Short | H30 | 8,843 | -15.6 | +1.0 | -22.7 |
| F04S | Filter: 15-minute EMA20/50 trend, short | Short | H30 | 150,572 | -15.8 | +0.8 | -34.3 |
| F05S | Filter: beyond EMA200, short | Short | H30 | 180,834 | -15.8 | +0.8 | -35.9 |
| O03S | Turtle soup, 5-minute, short | Short | H30 | 26,095 | -15.9 | +0.7 | -23.7 |
| F09S | Filter: VWAP side, short | Short | H30 | 211,186 | -15.9 | +0.7 | -39.5 |
| Y03S | EMA9 crosses EMA21 (control), short | Short | H30 | 39,782 | -15.9 | +0.7 | -28.0 |
| O06L | Narrow CPR trend day, opening-range break, long | Long | H30 | 1,591 | -16.0 | +0.6 | -10.5 |
| O05L | Raschke anti, 15-minute, long | Long | H30 | 18,328 | -16.1 | +0.5 | -31.0 |
| Y12AS | Narrow CPR, bounce off its edge, short | Short | H30 | 7,387 | -16.1 | +0.5 | -20.3 |
| Y24S | 15-minute inside candle breakout, short | Short | H30 | 33,007 | -16.1 | +0.5 | -35.5 |
| F01S | Filter: ATR rising, short | Short | H30 | 224,528 | -16.1 | +0.5 | -36.9 |
| Y21S | Inside bar, mother-bar break, in an EMA10 trend, short | Short | H30 | 17,572 | -16.1 | +0.5 | -32.1 |
| O09L | TTM squeeze release, 15-minute, long | Long | H30 | 4,607 | -16.1 | +0.5 | -17.4 |
| Y07L | One-hour opening-range breakout, long | Long | H30 | 11,826 | -16.2 | +0.4 | -20.8 |
| Y16S | Triple Supertrend, EMA200, Stoch RSI, short | Short | H30 | 21,185 | -16.2 | +0.4 | -24.5 |
| Y13S | Close through a classic pivot level, short | Short | H30 | 89,976 | -16.3 | +0.3 | -35.1 |
| Y22S | False break of a 20-bar extreme, short | Short | H30 | 16,831 | -16.3 | +0.3 | -26.3 |
| O07S | RDP: open above yesterday's high, close below the first bar's low, short | Short | H30 | 571 | -16.3 | +0.3 | -5.8 |
| Y06S | VWAP side, Fibonacci pivot break, Stoch RSI, after 10:45, short | Short | H30 | 24,004 | -16.3 | +0.3 | -31.6 |
| Y23S | Previous session's point of control retest, short | Short | H30 | 3,204 | -16.3 | +0.3 | -21.1 |
| Y08S | Failed opening-range break, faded, short | Short | H30 | 15,338 | -16.3 | +0.3 | -20.0 |
| F07S | Filter: ADX(15m) above 20, short | Short | H30 | 247,129 | -16.3 | +0.3 | -44.3 |
| Y24L | 15-minute inside candle breakout, long | Long | H30 | 30,869 | -16.3 | +0.3 | -39.1 |
| F03S | Filter: by 11:00, short | Short | H30 | 122,608 | -16.3 | +0.3 | -22.3 |
| O02S | Williams oops, short | Short | H30 | 330 | -16.3 | +0.3 | -3.3 |
| F02S | Filter: relative volume 1.5, short | Short | H30 | 160,534 | -16.4 | +0.2 | -43.4 |
| Y14S | ADX(15m) > 20, Supertrend, Fibonacci pivot break, short | Short | H30 | 26,958 | -16.4 | +0.2 | -26.6 |
| Y05S | VWAP hold-and-bounce / rejection, short | Short | H30 | 14,456 | -16.4 | +0.2 | -41.0 |
| Y20S | Heikin-Ashi reversal after a stochastic extreme, short | Short | H30 | 15,890 | -16.5 | +0.1 | -27.3 |
| F08S | Engulfing or hammer (shooting star), short | Short | H30 | 129,806 | -16.5 | +0.1 | -45.5 |
| Y21L | Inside bar, mother-bar break, in an EMA10 trend, long | Long | H30 | 16,088 | -16.5 | +0.1 | -34.1 |
| Y02L | EMA9/15 trend, touch of EMA9, trigger candle, long | Long | H30 | 16,301 | -16.5 | +0.1 | -20.1 |
| Y04S | EMA200 trend, EMA20 pullback, Stoch RSI reset, short | Short | H30 | 34,682 | -16.6 | +0.0 | -26.2 |
| Y14L | ADX(15m) > 20, Supertrend, Fibonacci pivot break, long | Long | H30 | 27,337 | -16.6 | +0.0 | -33.7 |
| Y06L | VWAP side, Fibonacci pivot break, Stoch RSI, after 10:45, long | Long | H30 | 21,304 | -16.6 | -0.0 | -34.8 |
| Y07S | One-hour opening-range breakout, short | Short | H30 | 13,552 | -16.6 | -0.0 | -18.4 |
| Y19S | MACD cross beyond zero with EMA200, short | Short | H30 | 13,331 | -16.6 | -0.0 | -22.8 |
| O05S | Raschke anti, 15-minute, short | Short | H30 | 18,350 | -16.8 | -0.2 | -32.6 |
| F06S | Supertrend(10,3) flip, 5-minute, short | Short | H30 | 25,438 | -16.8 | -0.2 | -19.6 |
| F04L | Filter: 15-minute EMA20/50 trend, long | Long | H30 | 147,781 | -16.8 | -0.2 | -46.1 |
| F09L | Filter: VWAP side, long | Long | H30 | 189,499 | -16.8 | -0.2 | -44.4 |
| F05L | Filter: beyond EMA200, long | Long | H30 | 178,302 | -16.8 | -0.2 | -47.0 |
| Y27S | Bollinger(20,2)/RSI(14) extreme, then a reversal close, short | Short | H30 | 5,084 | -16.9 | -0.3 | -12.5 |
| Y05L | VWAP hold-and-bounce / rejection, long | Long | H30 | 13,431 | -16.9 | -0.3 | -40.6 |
| F02L | Filter: relative volume 1.5, long | Long | H30 | 160,534 | -16.9 | -0.3 | -44.9 |
| F03L | Filter: by 11:00, long | Long | H30 | 122,608 | -16.9 | -0.3 | -23.1 |
| F07L | Filter: ADX(15m) above 20, long | Long | H30 | 247,129 | -17.0 | -0.4 | -46.2 |
| Y01S | 5-EMA alert candle broken, short | Short | H30 | 56,513 | -17.1 | -0.5 | -39.1 |
| Y20L | Heikin-Ashi reversal after a stochastic extreme, long | Long | H30 | 16,211 | -17.1 | -0.5 | -28.2 |
| Y16L | Triple Supertrend, EMA200, Stoch RSI, long | Long | H30 | 22,649 | -17.1 | -0.5 | -34.4 |
| F01L | Filter: ATR rising, long | Long | H30 | 224,528 | -17.1 | -0.5 | -39.3 |
| Y11S | Gap up after three up days, first red bar broken, short | Short | H30 | 240 | -17.3 | -0.7 | -3.0 |
| O08L | Supertrend(10,3) flip, 15-minute, long | Long | H30 | 9,030 | -17.4 | -0.8 | -15.9 |
| Y03L | EMA9 crosses EMA21 (control), long | Long | H30 | 39,327 | -17.5 | -0.9 | -34.0 |
| F08L | Engulfing or hammer (shooting star), long | Long | H30 | 128,910 | -17.5 | -0.9 | -48.2 |
| Y04L | EMA200 trend, EMA20 pullback, Stoch RSI reset, long | Long | H30 | 35,163 | -17.5 | -0.9 | -39.2 |
| Y18L | Bollinger(30,2) and RSI(13) extreme, long | Long | H30 | 12,106 | -17.6 | -1.0 | -10.9 |
| Y09L | First-hour sweep reversal, long | Long | H30 | 9,833 | -17.6 | -1.0 | -21.7 |
| Y12BL | Narrow CPR, close through R1/PDH (S1/PDL), long | Long | H30 | 6,901 | -17.7 | -1.1 | -26.3 |
| Y13L | Close through a classic pivot level, long | Long | H30 | 87,905 | -17.7 | -1.1 | -40.0 |
| Y18S | Bollinger(30,2) and RSI(13) extreme, short | Short | H30 | 12,494 | -17.7 | -1.1 | -16.4 |
| Y23L | Previous session's point of control retest, long | Long | H30 | 4,741 | -17.7 | -1.1 | -25.6 |
| Y19L | MACD cross beyond zero with EMA200, long | Long | H30 | 13,491 | -17.8 | -1.2 | -33.0 |
| F06L | Supertrend(10,3) flip, 5-minute, long | Long | H30 | 25,264 | -17.8 | -1.2 | -24.4 |
| Y12AL | Narrow CPR, bounce off its edge, long | Long | H30 | 10,453 | -18.0 | -1.4 | -28.1 |
| Y08L | Failed opening-range break, faded, long | Long | H30 | 17,073 | -18.1 | -1.5 | -18.3 |
| Y22L | False break of a 20-bar extreme, long | Long | H30 | 19,502 | -18.2 | -1.6 | -30.5 |
| Y01L | 5-EMA alert candle broken, long | Long | H30 | 60,138 | -18.2 | -1.6 | -39.2 |
| O03L | Turtle soup, 5-minute, long | Long | H30 | 27,162 | -18.2 | -1.6 | -32.0 |
| Y17L | Supertrend, MACD cross, near VWAP, long | Long | H30 | 2,733 | -18.3 | -1.7 | -11.2 |
| Y27L | Bollinger(20,2)/RSI(14) extreme, then a reversal close, long | Long | H30 | 4,959 | -19.7 | -3.1 | -11.7 |
| Y17S | Supertrend, MACD cross, near VWAP, short | Short | H30 | 1,857 | -19.8 | -3.2 | -8.1 |
| O02L | Williams oops, long | Long | H30 | 336 | -24.0 | -7.4 | -3.2 |
| O04L | Raschke 80-20, long | Long | H30 | 1,109 | -24.4 | -7.8 | -6.4 |
| O07L | GFR: gap below yesterday's low after a weak close, close back above, long | Long | H30 | 947 | -24.7 | -8.1 | -5.3 |
## What was and was not read

- **Read:** every NIFTY 100 symbol's 5-minute bars in `kite_history.db`, 2024-09-20 to 2025-12-31 (the first two sessions as history only), opened read-only; the newest bar read is dated 2025-12-31 (asserted in code). The result file, written once.
- **Not read:** any 2026 bar. The confirmation pass, which would have read 2026, does not run. 2026 remains as disclosed in the prereg's correction (N6): partly seen through the first phase's backtests of 2026-06-29 to 09-11, the momentum book's held-out check, the exposure-log rows, and the engine's daily paper trading; nothing of it was used here.
- **Not corrected:** survivorship (today's NIFTY 100), the calendar-day history difference between the looks (N2), and the universe difference (L55 trades every symbol; the forward lab the day's 25).

## What follows

- The forward lab (L54) continues as pre-registered; its first screen is after its 40th lab session. Its expectation is unchanged by this result, which if anything strengthens it: the same rules, on 316 sessions of history, lost the round trip.
- Amendment 6 (above) before that screen.
- No rule is proposed to the owner. Nothing changes in the engine.
