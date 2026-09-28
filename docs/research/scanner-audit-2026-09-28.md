# Intraday stock-selection audit (2026-09-28)

**Asked by the owner on 2026-09-28:** audit the agent's intraday stock
selection against a standard scanner framework (pre-open, liquidity, relative
volume, sector, news, timing gates), name the top three structural flaws,
list the Indian-market data to add, and rebuild the checklist as a
multi-pass filter.

This audit reads the code as it is on `main` (`3c515d1`) and the project's
own measurements. It runs nothing and changes no rule. Every figure is
quoted from the file named beside it.

## Verdict

1. Stock selection is not the weakest link. **No stage of the intraday
   funnel has a measured edge after costs**: not the old selection score,
   not the entry checklist, and not any of the 117 intraday rule sets on
   the trials ledger.
2. The selection stage does have three real engineering faults: it reads
   delayed data, it fixes the day's list after the open, and it has no
   guard for F&O bans or price bands.
3. Two of the framework's filters were tested here and failed (relative
   volume, opening range). Two were partly tested (VWAP, news events). Four
   have never been tested (gap, time-of-day relative volume as a ranking,
   VWAP distance, sector strength).
4. The rebuilt checklist below fixes the faults and marks every rule with
   its evidence. It is a cleaner funnel. **Nothing here shows it would make
   money**, and nothing in it should reach the engine without a
   pre-registered test.

## 1. What runs today

| Stage | What the code does | Where | Evidence that it helps |
| --- | --- | --- | --- |
| Universe | NIFTY 100, today's list, refreshed weekly | `backend/universe.py:17-46` | None needed; it is a cost choice |
| Floors | Price ≥ ₹100, 20-day turnover ≥ ₹50 cr, daily ATR ≥ 1.2% | `scanner.py:161-168` | Not tested as predictors |
| Exclusions | Results today or next weekday; ex-date today | `scanner.py:619-624` | Results move 3× normal with no readable direction (L35) |
| The day's 25 | The most-traded eligible stocks, fixed for the day | `scanner.py:523-555` | Chosen for cost and coverage, not as a prediction (README section 91) |
| Side | Each stock scored as a long and as a short from about 20 components; the higher side is kept | `scanner.py:171-351, 627-634` | The composite's rank IC is 0.000 over 434 sessions and −0.0021 over 436 (README sections 37, 52) |
| Market bias | NIFTY trend, day change, breadth, VIX, FII flow; risk-off blocks longs, risk-on blocks shorts | `scanner.py:354-443`, `trading_engine.py:679-682` | Never tested as a gate |
| Entry checklist | Six required items: pattern, level, cost, volume, trend, reward-to-risk | `trader_brain.py:228-384` | **−0.356R a trade, t −3.59, 201 trades, 495 sessions** (README section 51) |
| Confidence gate | Bar of 60; the multiplier is 0.25 because the backtest evidence fails | `confidence.py`, README section 70 | It stops every automatic entry. That is the evidence working as designed |

Automatic entries are therefore off. The only intraday positions are the
Jev book's paper round and review-queue approvals.

## 2. The framework, item by item

### Selection

| Framework item | Today | Measured here |
| --- | --- | --- |
| Pre-open orders and imbalance (09:00–09:08) | **Not implemented.** No code fetches NSE pre-open data. The pre-market read uses daily bars and runs at the first engine tick of the day, not at 09:08 (`scanner.py:803-937`, `trading_engine.py:1409-1413`) | Not tested |
| Gap % | Computed in the live scanner from yfinance 5-minute bars, which are about 15 minutes late. Scored, never a filter (`scanner.py:272, 285-302`) | Not tested as a predictor. On results days the gap is right (+82.7 bp, t 4.78) and nothing is left after the open: +5.9 bp at 30 minutes, −0.6 bp by the close (L36) |
| Turnover and price floors | Yes (table above) | Not tested |
| Bid-ask spread | Not in selection. Checked at entry: spread ≤ 6 bp, impact ≤ 3 bp, depth ≥ 3× the order (`liquidity.py:94-108`) | Median spread on 2026-09-28: 1.0 bp for the most-traded third of the index, 2.5 bp for the least-traded third |
| F&O eligibility | Not checked. 97 of the 100 are F&O stocks; ENRIN, TATACAP and TMCV are not | — |
| F&O ban list | **Not implemented** | — |
| Price bands, ASM, GSM | **Not implemented** | — |
| Relative volume | Cumulative volume against the same time of day on at most 4 earlier sessions. Scored +15 at 2×. The checklist needs the last bar above its 10-bar average (`scanner.py:262-311`, `trader_brain.py:308-309`) | **Tested, failed.** Opening-range breakout on the 20 stocks with the highest relative volume: net −12.1 bp a session, t −2.71, 303 sessions. "The relative-volume filter adds nothing measurable": +1.61 bp gross with it, +2.96 bp without (`results-3a-opening-range.md`). VWAP cross with volume ≥ 2×: every configuration failed (trials 93–116) |
| Sector strength | Sector rank from the universe's own members, and the sector index's daily trend. Scored (`scanner.py:329-342, 604-611`) | Not tested |
| Strength against the NIFTY | 10-day relative strength, up to +20 | **Tested, nothing.** IC −0.0090, t −1.24, 561 sessions (L8) |
| Beta | Computed and shown. Not used | Not tested intraday |
| News | Five sources, weighted, 12-hour half-life. A veto at ±0.5 and a size cut (`news_sentiment.py`, `trader_brain.py:558-609`) | The sentiment score has never been tested. Filings were: 9,586 events, six classes, **none clears the cost** (L35) |
| Results, ex-dates | Excluded | See above |
| Bulk and block deals | Fetched and shown. Not used | +2.9 / +1.8 / +7.1 bp at three horizons, t below 1 (L35) |

### Timing

| Framework item | Today | Measured here |
| --- | --- | --- |
| Opening 15 minutes | No entry before 09:30. The first bar that can trigger ends at 09:35 (`config.py:78`, `trader_brain.py:187-193`) | Opening-range breakout failed (trial 35). Removing the first five minutes and the closing auction costs the one real feature 23% of its strength |
| Last entry | 14:30. Square-off 15:08 | "Later entries lose more. 14:xx entries are the worst in every configuration shown" (`results-search-diagnostics.md`) |
| VWAP | Scored ±5 in the scanner. Not a checklist item | VWAP rule families: 0 of 76 configurations passed |
| Institutional flow | Yesterday's FII net beyond ±₹1,000 cr moves the bias by one point. DII is shown only | Not tested. The change in FII index-futures positioning was one input of trial 125, which failed |
| Delivery %, open interest | Not used | Not tested here. The literature read found no support |
| Index alignment | Market bias gate (table in section 1). NIFTY and VIX only; BANKNIFTY is not used | Never tested as a gate. The index itself loses 6.4 bp intraday on average (t −4.02) |
| Volatility | Floor of 1.2% and a bonus between 1.5% and 4% | **The one feature that survived.** High-volatility stocks do worse intraday, not better: the top fifth loses 8.6 bp, the bottom fifth 0.1 bp. The spread is worth 0.24× of what trading it costs (`results-step2-followups.md`) |

## 3. The three structural flaws

### Flaw 1. Every stage is scored, none is proven, and costs are larger than any effect found

A round trip costs 16.6 bp. Before costs the checklist earns +0.042R a trade
(t 0.42), which is nothing. Costs then take 0.398R. Its entries land at the
82nd percentile of random entries in the same stocks, which is not
distinguishable from random. The credible gross edges in the literature for
this market are 1 to 8 bp a trade.

So the premise of the question needs correcting. Better selection helps only
if it finds stocks that move more than 16.6 bp in a direction known in
advance. Nothing tested here does. The old score did not (rank IC 0). The
volatility floor works against longs: it keeps the stocks that lose the most
intraday.

### Flaw 2. The scanner sees the market late

- The scanner reads **yfinance**, never Kite, even with a Kite session open
  (`rules.json` SCN-01). yfinance is about 15 minutes late. Gap, relative
  volume, VWAP side and the opening-range break are all computed on it.
- Relative volume is measured against **at most four** earlier sessions.
- There is **no pre-open data** at all.
- The day's list is fixed at the first scan during the session that has
  bars for 90% of the universe, not before the open
  (`scanner.py:541-555, 575`). The README says "before trading".

An in-play scanner on delayed bars reports what happened a quarter of an
hour ago. This is worth fixing whatever else is decided, because every
later measurement of these features depends on it.

### Flaw 3. Rules are stacked, some are dead, and the tradability guards are missing

- About 20 score components are still computed. Since the move to the
  liquidity list they choose nothing, but the **side** they produce still
  blocks entries (`trading_engine.py:677-678`). A direction gate is being
  driven by a score with no predictive value.
- Three rules are inert in the default mode: the cap of two picks against
  the bias, the minimum score of 20, and the daily-trend agreement test
  (`scanner.py:496-511, 684-685`).
- The funnel is almost closed: 82,448 evaluations gave 92 passes and 8
  orders. The median setup offers a reward-to-risk of 0.05 after costs.
- No F&O ban check, no price-band check, no surveillance-list check. The
  results exclusion skips weekends but not holidays (#162).
- The README and the code disagree in eight places (section 7).

## 4. Indian-market data to add

"Evidence" is this project's own. None of these is known to predict
direction.

| Data | Source | Today | Why it matters | Evidence |
| --- | --- | --- | --- | --- |
| Live 5-minute bars for the scanner | Kite, already connected | yfinance, 15 minutes late | Every in-play number is stale without it | — |
| Pre-open snapshot at 09:08: indicative price, gap, buy and sell quantity | NSE's pre-open page. Not a documented API | None | The only view of the open before it happens | Not tested |
| F&O ban list | NSE daily file | None | A stock in the ban is crowded and its futures cannot take new positions | Not tested |
| Price band for each stock | NSE daily file | None | The three non-F&O names have fixed bands. A short locked at the upper band cannot be covered | — |
| Holiday-aware results calendar | NSE event calendar, already fetched | Skips weekends only (#162) | A results day after a holiday is missed | Results days move 3× normal (L35) |
| Expiry calendar (weekly, monthly) | NSE | None | Expiry days trade differently | Not tested |
| Relative volume against 20 sessions, same time of day | Kite 5-minute cache, from 2024-09-20 | 4 sessions | Four days is too short a baseline | As a filter it added nothing (trial 35) |
| Sector index, live | Kite | yfinance daily trend | The framework's "confluence" | Not tested |
| Order book, five levels | Already recorded every tick | Recorded, unused | The one input still under test | L37, due about 2026-10-19. Stated expectation: fail |
| Delivery %, open interest, put-call ratio | Bhavcopy, Kite | Not used | Often quoted | No support found |

Live institutional flow is not observable. FII and DII figures are published
after the close, so any "institutional footprint" rule uses yesterday's
number. The block-deal windows are the only institutional prints visible
during the day, and block deals showed no usable drift here (L35).

## 5. The rebuilt checklist

One pass per stage. A stock that fails a pass is dropped for the day, or for
that bar in passes 3 and 4.

Tags: **[in code]** runs today. **[change]** runs today and needs a fix.
**[new]** does not exist. **[failed]** was tested here and did not clear
costs. **[untested]** has never been measured here. Thresholds marked
*template* come from the framework that was supplied, not from any
measurement.

### 08:45 – 09:00 · Pass 1: universe (daily data only)

| # | Rule | Tag |
| --- | --- | --- |
| 1.1 | Universe is the NIFTY 100 | in code |
| 1.2 | Price ≥ ₹100, 20-day average turnover ≥ ₹50 cr | in code |
| 1.3 | Drop: results today or on the next **trading** day; ex-date today | change (#162) |
| 1.4 | Drop: in the F&O ban today | new |
| 1.5 | Non-F&O stock: longs only, and not at all within 2% of its band (a judgement, not a measured figure) | new |
| 1.6 | Keep the 25 most-traded. **Fix the list now**, from daily data, and do not change it | change |
| 1.7 | Record the regime: NIFTY daily trend, India VIX, yesterday's FII net | in code |

The daily ATR floor of 1.2% is left out on purpose. It selects the stocks
that lose the most intraday on the long side, and it was never tested as a
filter.

### 09:00 – 09:15 · Pass 2: pre-open and catalyst

| # | Rule | Tag |
| --- | --- | --- |
| 2.1 | At 09:08 read each stock's indicative open. Gap = indicative open ÷ previous close − 1 | new, untested |
| 2.2 | In play if the gap is 0.8% to 2.5% either way (*template*). Above 3%: mark as stretched | untested |
| 2.3 | Imbalance = (buy quantity − sell quantity) ÷ total at the indicative price | new, untested |
| 2.4 | Tag a catalyst: a filing or a news item since yesterday's close | in code; events **failed** (L35) |
| 2.5 | Sector: rank the sector indices by their own gap | new, untested |

### 09:15 – 09:30 · Pass 3a: watch, do not trade

| # | Rule | Tag |
| --- | --- | --- |
| 3.1 | No entry before 09:30 | in code |
| 3.2 | Build from **live** bars: the 15-minute opening range, session VWAP, relative volume against the same 15 minutes over the last 20 sessions | change |
| 3.3 | NIFTY state: above or below its own VWAP, and the day's change | in code, untested as a gate |

### 09:30 – 14:30 · Pass 3b: in-flight filter, every finished 5-minute bar

| # | Rule | Tag |
| --- | --- | --- |
| 3.4 | Relative volume ≥ 2.0 (*template*) | **failed** as a filter (trial 35) |
| 3.5 | Long only above VWAP, short only below | **failed** as a rule family (0 of 76) |
| 3.6 | Stock's change minus its sector index's change has the sign of the trade | untested |
| 3.7 | Long only if the NIFTY is above its VWAP, short only if below | untested |
| 3.8 | Direction comes from 3.5 to 3.7 together. The old score no longer sets the side | change |

### Pass 4: entry and execution

| # | Rule | Tag |
| --- | --- | --- |
| 4.1 | Candle pattern at a level, volume above its 10-bar average, 15-minute trend agrees | in code; the set **failed** (−0.356R) |
| 4.2 | Stop at least 1× ATR and at least 1× the round-trip cost | in code |
| 4.3 | Net reward-to-risk ≥ 1.5 after costs, to a real level | in code |
| 4.4 | Spread ≤ 6 bp, impact ≤ 3 bp, depth ≥ 3× the order | in code |
| 4.5 | One entry a stock a day, one stock a sector, three positions, 2% daily loss limit | in code |
| 4.6 | The confidence gate stays as it is | in code |

### 14:30 – 15:30 · Close

| # | Rule | Tag |
| --- | --- | --- |
| 5.1 | No new entry after 14:30 | in code |
| 5.2 | Square off at 15:08 | in code |
| 5.3 | Log every stock that passed each stage, with its return to 15:08 | new |

Rule 5.3 is the one that matters most. Without it nobody can say whether a
pass helped.

## 6. What to do with it

1. **Fix the faults that do not depend on any edge:** live bars for the
   scanner, the list fixed before the open, the ban and band guards, the
   holiday bug, the side no longer set by the old score. Automatic entries
   are off, so none of these changes an order. Two running tests take the
   list and the side as input, the Jev book (trial 123) and the order-book
   look (L37). A change to either needs a dated note in their
   pre-registrations first, as the move to the liquidity list did.
2. **Run passes 1 to 3 in shadow.** Log candidates, place no orders.
3. **One pre-registered look** on the four features never measured here:
   gap, time-of-day relative volume, VWAP distance and sector strength, on
   the Kite 5-minute cache, against the 16.6 bp round trip. One run, both
   halves, corrected for four tests. The honest expectation is that none
   clears, given what the related tests found.
4. If none clears, the intraday selection question is closed and the work
   goes to the delivery book, where the rule has passed its tests.

## 7. Where the README and the code disagree

| # | Subject | README or comment | Code |
| --- | --- | --- | --- |
| 1 | Rule count | 227 (section 89) | `rules.json` holds 232 |
| 2 | Active list | By final score, at most 2 against the bias (lines 133, 151) | Liquidity list; the cap is inert |
| 3 | Live gate | Includes VWAP side and opening range (line 495; `trading_engine.py:360-362`) | The checklist has neither |
| 4 | Gap threshold | 0.3% to 3% (line 147) | Nothing is scored under 0.5% (`scanner.py:287`) |
| 5 | When the list is fixed | "chosen once before trading" (section 91); "before the open" (`prereg-orderbook.md`) | At the first scan in the session with 90% coverage |
| 6 | What volatility is worth | 8 bp against a 16.6 bp round trip (section 91) | Two legs, so the hurdle is 33.2 bp and the ratio 0.24× (`results-step2-followups.md`) |
| 7 | Composite IC | 0.000 over 434 sessions (section 37) | −0.0021 over 436 (section 52). Two runs; both are nil |
| 8 | Can relative volume and news be backtested | "can't be backtested" (README, limitations) | Trial 35 computed relative volume from the Kite cache; L35 and L36 measured filings |

## Limits of this audit

- It ran nothing. Journal and order-book figures are quoted from documents,
  not re-queried.
- It did not check NSE's pre-open, ban-list or price-band files for format
  or reliability. The project dropped the surveillance lists earlier because
  no reliable public endpoint was found (README section 20).
- The thresholds marked *template* are not recommendations.
