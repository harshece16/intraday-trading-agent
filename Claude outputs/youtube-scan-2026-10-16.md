# YouTube scan, 13–16 Oct 2026: what it means for Trader Sahab

28 Indian-market videos with transcripts, published 13–16 Oct, fetched with
agent-reach (yt-dlp). The raw extraction, with every video id, is in
`youtube-raw-2026-10-16.md` next to this file. Prices below are live Kite
quotes from Fri 16 Oct, about 11:35 IST.

## Bottom line

- **Trading decision: no change to any paper book.** No call or idea in these
  videos meets the project's standard: a pre-registered test that stays
  positive after the 16.60 bp round-trip cost in both halves of the sample.
  The momentum book keeps its 15 names until the 2 Nov rebalance.
- **Improvements: none of the 12 strategy ideas is new.** Each one is either a
  family the project has already refuted or a rule already running in the
  rule lab. Only one hypothesis is new: whether the YouTube consensus itself
  predicts the market. It is proposed below, not built.

## What the videos say, checked against Kite

- **Nifty bias for next week:** 10 bullish, 6 neutral, 3 bearish. The 3
  bearish views were mostly posted before Thursday's rally.
- **Context (verified):** Nifty closed at 22,997.35 on 15 Oct and is at
  23,124.70 (+0.55%). Bank Nifty is −0.16%, Midcap 100 −0.08%, and India VIX
  is 14.01.
- **Levels cited most often:** support at 22,800 and 22,200; resistance at
  23,175–23,200 and 23,500.
- **How to read it:** the bullish majority came straight after a +2% day, so
  it mostly repeats yesterday's move rather than forecasting the next one.
  The project measured intraday session drift at −6.4 bp, so a long bias
  starts behind.

### The stock calls

Only 3 of the 28 videos gave a full entry, stop-loss and target.

| Call (channel) | Stated | Kite LTP | Does the price match? |
|---|---|---|---|
| Kotak Bank buy (ET Now Swadesh) | 445–448, SL 428, T 460/475/488 | 446.50 | yes |
| Chola Finance buy (ET Now Swadesh) | 1580–1585, SL 1558, T 1598/1625/1650 | 1579.60 | yes |
| Rain Industries hold (Profit Ahead) | SL 225 close, T 240/250 | 229.79 | yes |
| BEL sell futures (Moneycontrol Hindi) | ~436, SL 442, T 428/420 | 379.95 | **no**: wrong name or price in the captions |
| BSE breakout (Invest Easy) | above 1647, support 1467 | 3,368.30 | **no**: garbled numbers |

For 2 of the 5 calls that can be checked, the price doesn't match the market.
An automated YouTube feed would therefore be trading on garbled auto-captions.
That alone rules out wiring these calls into the engine.

Overlap with the momentum book: MCX is the only holding in the "exchanges
benefit" theme (with BSE). That is a coincidence, not a confirmation.

## The ideas compared with what Trader Sahab already knows

| # | Idea from the videos | Status here |
|---|---|---|
| S1 | 15-min opening-range break + VWAP pullback | Opening range (prereg 3a) **failed**. VWAP rules are live in the rule lab (cohort 2b). |
| S2 | 3-min Heikin-Ashi + 100 EMA scalp with a 10-point target | 10 points is 4.3 bp, a quarter of the 16.60 bp round trip, so costs kill it. Heikin-Ashi rules are in the lab. |
| S3 | VWAP + CMF(20) breakout, buying ATM options | Option buying is **refuted** out of sample (prediction-engine sweep). CMF is the only indicator not in the lab. |
| S4 | Narrow prior-day pivot range + Supertrend breakout | Volatility breakout family: all 24 variants **failed** (trials 93–116). Pivot, Supertrend and narrow-range rules are in the lab. |
| S5 | Monthly short 30-delta Bank Nifty put | The premium is real (IV − RV, t 3.76), but there is no option-chain fill data to test it. Outside the current mandate. |
| S6 | PCR above ~1.5 means "overbought" | Option-chain positioning is **refuted**. Near-expiry PCR was a feature in overnight ETF H2, which **failed**. |
| S7 | Index +1.5% while FIIs sell cash = short covering that fades | FII futures positioning was in H2 (**failed**). Index timing (L51) didn't trade enough to pass. |
| S8 | Risk-reward ≥ 1:2, risk 2–3% per trade | Generic risk advice, not an edge. |
| S9 | Exchange stocks gain if the SEBI settlement rule changes | A one-off event, not repeatable. |
| S10 | Post-results growth screen | Post-earnings drift (PEAD) **NO-GO**: +0.25%/month against a +0.37% bar, t 1.41. |
| S11 | No longs until Midcap closes above 60,000 | Breadth (L48): **no pass**, 0 of 8 predictors survived. |
| S12 | Nifty reclaims its 20-DMA | 20-DMA rules are in the rule lab, at 10 of 40 sessions so far. |

## The one new hypothesis: YouTube consensus as a signal

- **Test:** each evening, classify the bias of the daily "Nifty prediction
  for tomorrow" videos (15–20 channels post one every day) and score it
  against the next session's Nifty move.
- **Why it could work:** in Kakhbod et al., *Finfluencers* (2023, US data),
  most finfluencers were "antiskilled" and betting against them made money.
  This hasn't been tested on Indian data.
- **Why it probably won't pay:** at this capital the only instrument is
  NIFTYBEES (2.4–2.7 bp in charges). Both overnight-ETF tests failed with FII
  and PCR inputs, and L48 and L51 found no index-direction signal.
- **Cost:** one research look, not a strategy trial. It can be run
  retrospectively on videos up to the end of 2025, which keeps it out of the
  untouched 2026 held-out window. The practical limit is caption download
  rate limits (this run hit HTTP 429).

## Calendar items

- **Tue 20 Oct, Dussehra holiday:** already in `backend/holidays.py:42`.
- **Nifty weekly expiry on Mon 19 Oct (as claimed):** the intraday engine
  trades cash, so no action.
- **SEBI closing auction / 30-min VWAP settlement change (as claimed, "panel
  likely backs"):** if a closing auction replaces the 30-min VWAP close, the
  momentum book's close-fill assumption changes. Worth watching; no change
  now.

## Operations

- Jev 1 and Jev 2 skipped today's 09:45 round because Kite connected at
  11:13. The next round is Mon 19 Oct at 09:45, provided Kite is connected
  before then.
