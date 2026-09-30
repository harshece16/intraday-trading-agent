# Phase 3 — scoping: which Kite segments can a ₹5,500 account reach, and is there anything documented to test in them?

> **Closed 2026-09-30.** This note stopped for review on 2026-09-23. Its finding is negative and it recommends no pre-registration (§3); the reviewer later used it as precedent (Entry 14), and nothing in it was disputed. Of the two issues it filed, #78 and #79 are closed. The one line it leaves open is a forward-collected 5-minute cache for CDS or MCX GOLDPETAL, which has low costs but no documented effect; opening it is the owner's decision, and nothing is collected until then. Since this note, the project tested eight forecasting models and 75 combinations on NSE cash (README §104), all failing, which lowers the prior for any exploratory search further.

**2026-09-23. Research only. Nothing in this document is a strategy, and no trial is spent.** No config was changed, no engine code was touched and no Kite order was placed. Every Kite call was read-only: the public instruments dump, `quote`, `historical_data`, and `order_margins`, which only calculates and places nothing. The trial count stands at 35, or 37 once PR #76 merges. Research looks are unchanged at 34.

**Stopped for review.** Nothing below runs without reviewer review and the user's go-ahead.

**How to read the prices.** The Kite calls ran at about 03:40 IST on 2026-09-23, before the open, so every price and margin is **the 2026-09-22 close**. Margins move daily with SPAN and volatility. Treat them as one day's reading, not constants.

---

## 1. Segments

### 1a. Contracts, lot sizes, notional and margin per lot

Sources:
- **Contracts and lot sizes:** the Kite instruments dump (`https://api.kite.trade/instruments`, retrieved 2026-09-23).
- **Prices:** Kite `quote`.
- **MCX multipliers:** MCX's own contract-specification PDFs (mcxindia.com product pages, read in a browser because the site returns 403 to scripts).
- **CDS multipliers:** NSE's CDS contract specification (`nseindia.com/static/products-services/currency-derivatives-contract-specification-inr`).
- **Margins:** Kite Connect `order_margins`, one lot, BUY, NRML and MIS. That is the calculation behind Zerodha's margin calculator. **MCX figures were cross-checked** against `zerodha.com/margin-calculator/Commodity/` ("Last updated: 22 Sep 2026"), and the implied multipliers matched within ~0.1%. **NFO and CDS margins were not cross-checked** against the web page; they come from the API only.

The dump lists MCX and CDS contracts with `lot_size = 1` because Kite quotes them per unit. Notional below is **LTP × the exchange's contract multiplier**, not LTP × lot size.

**MIS margin equals NRML margin for every NFO, MCX and CDS contract tested.** Intraday leverage exists only in cash equity. Zerodha's bulletin (`zerodha.com/marketintel/bulletin/249809`, dated 22 Sep 2026) says the same: "1X (100% of NRML margins(SPAN + Exposure))".

| Segment | Instruments (dump count) | Representative contract | Multiplier | Notional, 1 lot | Margin, 1 lot | **Reachable at ₹5,500?** |
| --- | --- | --- | --- | --- | --- | --- |
| **NSE cash** | 10,133 | RELIANCE, 1 share @ ₹1,240.40 | — | ₹1,240 | **₹248 MIS** (5×), ₹1,240 CNC | **Yes**: up to ₹27,500 exposure on MIS |
| **BSE cash** | 12,788 | RELIANCE, 1 share @ ₹1,242 | — | ₹1,242 | **₹248 MIS** | **Yes**, the same as NSE |
| **NFO futures** | 647 | NIFTY 26SEP, lot 65 | — | ₹15,21,650 | **₹1,72,649** | **No** |
| | | BANKNIFTY 26SEP, lot 30 | — | ₹16,97,100 | ₹1,92,249 | No |
| | | Smallest stock future: VEDL, lot 1,150 (of 211 near-month stock futures) | — | ₹3,02,565 | ₹1,05,154 | No |
| **NFO options (bought)** | 35,560 | NIFTY 26SEP 23350 CE (ATM), lot 65 @ ₹160.05 | — | premium ₹10,403 | ₹10,403 | **No at ATM** |
| | | NIFTY 26SEP 23350 PE (ATM) @ ₹102.85 | — | premium ₹6,685 | ₹6,685 | No at ATM |
| | | Any NIFTY option with premium ≤ ₹84.6 | — | ≤ ₹5,500 | = premium | **Only OTM**, far enough out that the premium is ≤ ₹84.6 |
| **MCX futures** | 165 | **GOLDPETAL** SEP (1 g) @ ₹15,327 | ×1 | ₹15,327 | **₹1,422** | **Yes, and the only MCX contract that is** |
| | | GOLDGUINEA SEP (8 g) | ×1 | ₹1,22,710 | ₹11,380 | No |
| | | GOLDTEN SEP (10 g) | ×1 | ₹1,53,138 | ₹14,188 | No |
| | | LEADMINI SEP (1 MT) | ×1000 | ₹1,96,200 | ₹14,452 | No |
| | | NATGASMINI SEP (250 mmBtu) | ×250 | ₹70,650 | ₹16,698 | No |
| | | CRUDEOILM OCT (10 bbl) | ×10 | ₹85,760 | ₹27,582 | No |
| | | SILVERMIC NOV (1 kg) | ×1 | ₹2,41,898 | ₹30,764 | No |
| | | ALUMINI / ZINCMINI SEP (1 MT) | ×1000 | ₹3,50,450 / ₹4,32,250 | ₹32,381 / ₹40,403 | No |
| | | GOLDM, SILVERM, CRUDEOIL, NATURALGAS, GOLD, SILVER, COPPER, ZINC, ALUMINIUM, LEAD | ×10 to ×5000 | ₹3.5 lakh to ₹1.5 crore | ₹72,316 to ₹14,15,925 | No |
| **CDS futures** (monthly) | 154 | **USDINR** 26SEP @ 95.5825 | ×1000 | ₹95,583 | **₹2,288** | **Yes** |
| | | **EURINR** 26SEP @ 109.8475 | ×1000 | ₹1,09,848 | ₹2,851 | Yes |
| | | **GBPINR** 26SEP @ 127.8325 | ×1000 | ₹1,27,833 | ₹3,797 | Yes |
| | | **JPYINR** 26SEP @ 60.695 (per 100 JPY) | ×1000 | ₹60,695 | ₹2,443 | Yes |

**Reachable does not mean survivable.** One USDINR lot is about **42× leverage** on ₹2,288. A 1% rupee move is ₹956, which is **17% of the account**. One GOLDPETAL lot is about 10.8× on ₹1,422. Any hypothesis in these segments would have to size risk to the account, and one lot is the minimum size, not a free choice.

Not covered: BFO (BSE derivatives, 4,518 contracts), NCO (NSE commodities, 25,289), MCX options and CDS options. The brief did not ask for them. MCX and CDS options would be premium-only like NFO options, but they were not priced here.

### 1b. Round-trip charges, in bp of notional

Computed from Zerodha's published tariff (`https://zerodha.com/charges`, raw HTML, retrieved 2026-09-23), buy then sell:
- **Brokerage:** 0.03% or ₹20 per order, whichever is lower (flat ₹20 for options).
- **STT/CTT on the sell side:** equity intraday 0.025%, futures 0.05%, options 0.15% of premium, commodity 0.01%, currency none.
- **Exchange transaction charges:** NSE cash 0.00307%, BSE 0.00375%, NSE futures 0.00183%, NSE options 0.03553% of premium, MCX 0.0021%, NSE currency 0.00035%.
- **SEBI:** ₹10/crore.
- **Stamp duty on the buy side:** 0.003% for equity and options, 0.002% for futures and MCX, 0.0001% for currency.
- **GST:** 18% on brokerage + SEBI + transaction charges.
- **IPFT:** ₹0.01/crore; negligible.

**These are charges only.** Slippage is unmeasured everywhere: the live model assumes 3 bp per leg, and no real-money fill exists to check it against.

| Segment | ₹5,500 | ₹1,00,000 | ₹3,00,000 | **At the size ₹5,500 can actually hold** |
| --- | --- | --- | --- | --- |
| NSE cash intraday | 10.63 | 8.27 | 5.12 | **10.63** at ₹27,500 (MIS 5×) |
| BSE cash intraday | 10.79 | 8.43 | 5.28 | **10.79** at ₹27,500 |
| NFO futures | 12.74 | 10.38 | 7.23 | unreachable |
| NFO options (bp of premium) | 109.53 | 28.43 | 25.28 | **110.16** at ₹5,460 premium |
| MCX futures, non-agri | 8.80 | 6.44 | 3.29 | **8.80** at ₹15,327 (GOLDPETAL) |
| CDS futures | 7.20 | 4.84 | 1.69 | **5.05** USDINR, 4.41 EURINR, 3.81 GBPINR, 7.20 JPYINR (one lot each) |

₹5,500 of *notional* is below one contract in NFO futures, MCX and CDS, so that column is arithmetic only for those rows. The last column is the cost of the smallest trade actually possible.

**Checks against earlier work:**
- NSE cash at ₹5,500 gives **10.63 bp**, against phase 2's measured **10.60 bp** of charges. The difference is the tariff drift filed as **#79**.
- Adding the modelled 6 bp of slippage reproduces the 16.60 bp hurdle.
- **The two-leg rule applies to every row:** a spread is two positions and pays two round trips (Entry 12 §1).

### 1c. Session hours

| Segment | Hours (IST) | Source |
| --- | --- | --- |
| NSE cash | Pre-open 09:00–09:08; normal market 09:15–15:30. **Since 2026-08-03, continuous trading in F&O-eligible stocks stops at 15:15**, followed by a closing auction from 15:15 to 15:35. Non-F&O stocks still close at 15:30. | `nseindia.com/static/market-data/market-timings`; Zerodha support, "closing-auction-session" |
| BSE cash | The same, and the closing auction covers "Both NSE and BSE" | Zerodha support; **not checked on bseindia.com** |
| NFO | 09:15–15:30, and F&O contracts "continue trading until 3:40 PM" from 2026-08-03 | Zerodha support only; **not confirmed on NSE's site** |
| MCX non-agri | 09:00–23:30 during US daylight saving, 09:00–23:55 otherwise | MCX contract PDFs; Zerodha bulletin 441795 (from 2026-03-09) |
| NSE CDS | 09:00–17:00, Mon–Fri | NSE CDS contract specification |

**Found while scoping, filed as a live-path bug (#78):** Zerodha auto-squares MIS positions at **15:12** for closing-auction (F&O) stocks and 15:25 for the rest, and charges "₹50 per order ... including auto square off orders". The engine's `SQUARE_OFF_TIME` is **15:15**. Not fixed, because this brief is read-only.

### 1d. Kite historical 5-minute data

Checked empirically (read-only `historical_data`, 60-day window) and against the Kite docs (`kite.trade/docs/connect/v3/historical/`) and forum answers from Kite staff.

| Segment | 5-min bars returned for a live contract | Expired contracts, intraday | Local cache |
| --- | --- | --- | --- |
| NSE cash | Yes: 2,967 bars, RELIANCE, 2026-07-27 → 09-22. "for minute level data it starts somewhere around early 2015" (forum 14149) | n/a | **Yes.** NIFTY 100, 2024-09-20 → 2026-09-18, 3.63M bars. **The only segment cached.** |
| BSE cash | Yes: 2,967 bars, RELIANCE | n/a | No |
| NFO futures | Yes, for the live contract (3,147 bars) | **No.** `continuous=True` returns "invalid interval for continuous data" at 5 minutes; it gives **day** candles only ("You can get day candles data, for an expired contract not minute level data", forum 4369). Daily continuous NIFTY futures reach back to 2021-04-05. | No |
| NFO options | Yes, from listing only: 1,093 bars for the ATM call, from 2026-08-04 | **No.** "Historical data won't be available for the expired option contract" (forum 15361) | No |
| MCX futures | Yes: 7,212 bars for GOLDPETAL and CRUDEOILM, 09:00–23:25 | **No intraday.** Continuous **day** candles "from 2011 onwards" (forum 10751) | No |
| CDS futures | **Monthly contracts only**: USDINR 26SEPFUT returned 1,824 bars from 2026-08-25. **Weekly contracts returned 0 bars.** | **None, not even daily continuous**: "continuous data for an expired contract are only for NFO and MCX FUT contracts not for CDS contracts" (forum 6662, 2019, may be stale) | No |

**This is the binding data constraint for every non-equity segment.** Kite cannot supply multi-year 5-minute history for NFO, MCX or CDS, because expired contracts have no intraday bars and their tokens aren't even listed ("It is not possible to retrieve instrument_tokens for expired contracts from the API, unless you regularly download and cache them"). **A non-equity intraday backtest on Kite data needs a forward-collected cache**: months of collection before the first test, or a paid third-party history source.

---

## 2. Documented effects, for reachable segments only

Reachable segments: **NSE cash, BSE cash, NFO options bought OTM, MCX GOLDPETAL, and CDS futures.**

Every source below was opened. That means the abstract or the paper, through OpenAlex, RePEc, arXiv or an open PDF. SSRN, ScienceDirect full text and sebi.gov.in could not be reached. Three citations were **re-checked by hand**: Muravyev & Ni's abstract (verbatim, RePEc); SEBI's 91.5% and ₹26,000 (verbatim in the full study, read from a third-party copy); and Gao et al.'s JFE record (OpenAlex, DOI 10.1016/j.jfineco.2018.05.009).

**Bottom line: no reachable segment has a documented, India-specific effect with a stated size in bp.** Where a size exists, it is non-Indian, gross of costs, or both.

### NSE and BSE cash

| Effect | Source | Size, as stated | bp estimate vs cost |
| --- | --- | --- | --- |
| Market intraday momentum: the first half hour predicts the last half hour | Gao, Han, Li & Zhou, "Market intraday momentum", *JFE* 2018 (DOI 10.1016/j.jfineco.2018.05.009). The number is from the SSRN 2552752 draft: "6.67% per annum with a standard deviation of 6.19%". **US, SPY 1993–2013.** | 6.67% a year | **≈ +2.6 bp per trade gross** (667 bp ÷ 252 days) against 10.63 bp charges = **0.25×**. **The in-house Indian measurement is +0.70 bp** (3b stage 1, "market sign × last half hour"), or **0.04×** the 16.60 bp hurdle. **Already measured and withdrawn.** |
| Overnight gains, intraday losses | Practitioner only: P. Kumar (LinkedIn, Nifty 2011–2020), "92% of the total up move comes in the overnight session"; Zerodha's *In The Money* substack (Nifty/Sensex 2000–2025). Saji, Raghunandanan & Nair, *Vision* 2024 (DOI 10.1177/09722629241281021): overnight returns "do not reverse". | Sign only, no size | **In-house: the best spread is 16.30 bp against a 33.20 bp two-leg hurdle, 0.49×** (phase-2 closing report §3). Closed. |
| Expiry-day effects on the underlying | Vipul, *J. Futures Markets* 2005 (monthly-expiry era), "marginally depressed a day prior"; Samineni et al. 2020, Bank Nifty 2010–2020, "no effect on the mean returns" | Sign only, or none | No size, so it cannot be ranked |
| Opening auction, intraday volatility shape | Acharya & Gaikwad 2014 (no market-quality effect); Singh & Gangwar 2018 (U-shaped volatility) | Volatility, not returns | Not a return effect |
| Retail intraday outcomes | SEBI FY23 study via NewsOnAir: "more than 70 per cent of individual intra-day traders in the equity cash segment have incurred losses" | Net loss rate | Not an effect. Base rate. |

### NFO options, bought OTM

| Effect | Source | Size, as stated | bp estimate vs cost |
| --- | --- | --- | --- |
| Option returns flip sign from day to night | Muravyev & Ni, *JFE* 136(1), 2020. **US, S&P 500 index options.** "Average delta hedged returns ... −0.7% per day ... close-to-open returns are −1% per day and open-to-close returns are positive, 0.3%" | Buyer: **+30 bp intraday, −100 bp overnight** (of premium, delta-hedged, gross) | The intraday +30 bp against **110 bp** round-trip charges on a ₹5,460 premium = **0.27×**. **Delta-hedged**: the hedge needs futures, which are **unreachable** at ₹5,500. Unhedged buyer returns are not documented. |
| The same asymmetry in NIFTY options | Bhat, Pandey & Nageswara Rao, *J. Futures Markets* 44(8), 2024 (DOI 10.1002/fut.22512): positive overnight returns for **short** positions, negative intraday; selling at the close and covering at the open "is not profitable after factoring in the explicit and implicit transaction costs" (quoted second-hand) | Sign only | **No size**, so it cannot be ranked. The edge belongs to **sellers**, and selling needs margin far above ₹5,500. |
| Retail options outcomes | SEBI study (PR 22/2024, FY22–FY24, full study): "In FY24, about 60% of traders made net losses in Futures, compared to **91.5% in Options**"; "on an average, individual traders spent **₹26,000** per person on F&O transaction costs in FY24" | Net loss rate | Base rate. ₹26,000 a year of average cost is **4.7×** this account. |

### MCX GOLDPETAL

| Effect | Source | Size, as stated | bp estimate vs cost |
| --- | --- | --- | --- |
| MCX calendar and expiry anomalies | Chhabra & Gupta, *Resources Policy* 79, 2022, MCX 2008–2018: anomalies found, "diminished in recent periods" | No size in the abstract | Cannot be ranked. Daily, gross, and decaying. |
| Gold night-session momentum | Ma, Bouri, Xu & Zhou, *Global Finance Journal* 64, 2025. **China, SHFE.** | No size | Cannot be ranked. Not India. |

**No documented intraday or overnight effect with a size was found for MCX gold.** Searches: EIA pass-through to MCX, MCX–NYMEX high-frequency lead-lag, MCX evening session.

### CDS futures

**None found.** Searched: USDINR intraday seasonality, day-of-week and expiry effects, RBI reference-rate and fixing-time effects, RBI intervention intraday. The nearest results are non-Indian FX time-of-day effects (Khademalomoom & Narayan 2019, majors only, no size) and a BRICS study finding intervention reduced volatility but not the level (Chaudhari & Trivedi 2022). **CDS has the lowest hurdle of any reachable segment (3.81–7.20 bp) and no documented effect to test.**

---

## 3. Candidate hypotheses, ranked by effect ÷ round-trip cost

**None of them clears 1×.** The three with a stated size are ranked below. Every one is either already tested in-house or needs an instrument this account can't reach, so **this section recommends no pre-registration**. It is recorded so the ranking isn't rediscovered.

| Rank | Candidate | Effect | Hurdle | **Ratio** | Data it needs | In the cache? | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | NSE cash: short high-`atr_pct`, long low-`atr_pct`, intraday | +16.30 bp top-5/bottom-5 (in-house, replicated on universe B) | **33.20 bp (two-leg)** | **0.49×** | NSE 5m, 2+ years | **Yes** | **Closed.** Phase 2 §3. Subject to the negative-intraday-drift caveat: the long leg starts −6.4 bp behind. |
| 2 | NIFTY options bought at the open, sold at the close (Muravyev & Ni direction) | +30 bp of premium, **US, delta-hedged**, gross | 110 bp (one leg, premium ≤ ₹84.6) | **0.27×** | NIFTY option 5m history | **No, and not obtainable from Kite**: expired options have no history | Not viable. The hedge is unreachable, the unhedged effect is undocumented, and there's no data. |
| 3 | NSE cash: Gao-style last-half-hour timing on the index's first-half-hour sign | +2.6 bp **US**; **+0.70 bp India in-house** | 10.63 bp charges / 16.60 bp with slippage | **0.25× US; 0.04× India** | NSE 5m | **Yes** | **Withdrawn** (3b stage 1). 3b's pre-registration forbids re-registering it. |

What a pre-registration would look like, for the record only:
- **Rank 1:** already written as 3c/Universe B, and it failed on cost.
- **Rank 2:** a stage-1 measurement of NIFTY option open-to-close returns in bp of premium, split by moneyness, gated at 110 bp. It **cannot be run**: Kite has no expired-option history, and none is cached.
- **Rank 3:** 3b's stage-1 design, which is forbidden from being re-registered.

**What is not a candidate, and why:**
- **CDS and MCX GOLDPETAL** have low hurdles (3.8–8.8 bp) but **no documented effect**. A CDS or MCX hypothesis would be an exploratory search, not a literature-backed test. It would also need a **forward-collected 5-minute cache** (§1d) before it could run. If the user wants that line opened, the honest first step is to start collecting data, not to pre-register.
- **3e** (PR #77, wide-structure NSE shorts) is already pre-registered and not run. It has no literature effect size, so it isn't ranked here. Its case is the friction arithmetic, not a documented effect.

---

## 4. Engine implications: what would have to change to run one non-equity segment

A list only. Nothing here is implemented.

1. **Instrument model.** Symbols are bare NSE equity tickers today. A contract needs exchange, tradingsymbol, instrument token, expiry, a contract multiplier (from the exchange specification, since Kite's `lot_size` is 1 for MCX and CDS), tick size, and a rollover rule, because a position can't be held through expiry without physical-delivery rules.
2. **Lot sizing.** `RiskManager.position_size()` returns shares. It would have to return whole lots, where one lot is the minimum, and **refuse** a trade whose one-lot risk exceeds `max_risk_per_trade_pct`, rather than rounding to zero or up. At ₹5,500, one USDINR lot at a 0.5% stop risks ₹478, or 8.7% of the account.
3. **Session hours.** `MARKET_OPEN`, `MARKET_CLOSE` and `SQUARE_OFF_TIME` are single NSE-cash constants. They would need to be per segment (MCX 09:00–23:30/23:55 with a daylight-saving switch; CDS 09:00–17:00) with a separate holiday calendar per exchange. They would also need the broker's per-segment auto square-off ("Commodities 10 minutes before close"; see **#78** for the equity case).
4. **Cost model.** `config.COSTS` holds one set of equity-intraday rates. It would need per-segment tables (§1b): CTT for commodities, no STT for currency, a flat ₹20 per options order, STT on premium, and per-exchange transaction charges. The checklist's `cost_pct` (now derived, #74) would have to be derived per segment. **#35** (F&O P&L ignores charges) would need fixing first.
5. **Margin checks.** Sizing checks notional against capital today. Non-equity segments need a **pre-trade margin check** (Kite `order_margins`) against the live margin balance, because SPAN moves daily and MIS gives no extra leverage outside equity.
6. **Data pipeline.** `kite_history.py` caches NSE equity by symbol. It would need contract-level caching with expired tokens recorded before expiry, plus a continuous-series builder for backtests.
7. **Backtester.** It would need per-contract P&L multipliers, lot rounding, a per-segment session and square-off, and expiry handling.
8. **Market data and quotes.** `data_provider` and the tick stop-watcher subscribe to NSE equity tokens. They would need segment-aware tokens, and the correct quote unit (for example JPYINR is quoted per 100 JPY).
9. **Risk limits.** `max_position_notional_pct` (33%, or ₹1,815 at ₹5,500) can't be met by **any** non-equity contract. Even GOLDPETAL's one-lot notional is ₹15,327, which is 8× the cap. The cap would need a per-segment definition, in margin or risk terms rather than notional.

---

## 5. Statement

**Nothing in this document is a strategy. No trial is spent, no research look is spent, and the held-out window is untouched.**

It records what is reachable, what it costs, what the literature documents and what data exists, so that any phase-3 pre-registration starts from verified numbers. **Its finding is negative:** the only documented effects with a size are non-Indian, gross of costs, already refuted in-house, or need an instrument or data this account can't reach. The cheapest segments (CDS and MCX GOLDPETAL) have no documented effect at all.

### Found along the way and filed (not fixed; read-only brief)

- **#78**: the engine's square-off time is 15:15, but Zerodha auto-squares F&O-stock MIS positions at 15:12 (₹50 + GST per order) since the 2026-08-03 closing auction. Live-path.
- **#79**: `config.COSTS` has NSE's transaction charge at 0.00297%, but Zerodha publishes 0.00307%; the GST base also omits SEBI charges, and IPFT isn't modelled. Worth about 0.03 bp. It also partly retires the standing "costs unverified" caveat: charges are verified, slippage still isn't.

### Reproducibility

The raw outputs were gathered by scripts in the untracked `.scratch/` folder:
- `seg_quotes.json`, `seg_margins.json`, `seg_cds_monthly.json`, `seg_hist.json`
- `seg_costs.py` (the §1b arithmetic)
- the instruments dump

They are kept out of the repo because the dump is 9 MB and changes daily. Every figure above can be regenerated from the cited public sources and read-only Kite calls.
