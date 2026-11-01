# Gap sweep: practitioner and off-GitHub Indian stock/ETF backtests (Kaggle, QuantInsti, Varsity/Streak, Tradetron, QuantConnect, Capitalmind, Freefincal, Weekend Investing, Substack quants)

Scope and conventions. Written 2026-11-01. Exclusion map: 00-already-covered.md (sections 1 and 4, plus 3e/3f/3g and the L-table) and the GitHub section of 06-india-factor-zoo-and-open-source.md. Tags: [P] read on the fetched page, [S] search snippet or secondary summary, [C] my arithmetic. "Price-only" means implementable from daily bhavcopy price and volume (delivery quantity is in the full bhavcopy and is flagged separately). Entry IDs C01 to C30 are used across sections. The tool-call count went well past the 15-call guide because most platforms returned nothing; the negative results are recorded as findings. Most sources are gross-of-cost blogs; only the Freefincal/BacktestIndia studies state costs and tax.

## (a) Which signal families repeat in Indian practitioner net-of-cost backtests and are NOT in the covered file?

### Takeaway
Only one family is both absent from 00 and tested net of cost and tax by a practitioner: splitting momentum (and quality/value) by scaled turnover (daily turnover / market cap), where the premium sits in the low-turnover half and low-volatility is insensitive. Every other recurring family (monthly momentum, vol-adjusted momentum, weekly price-volume scoring, gold/Nifty dual momentum, low-vol) is either already closed or "Leave" in 00, or is reported gross with no costs, no tax and no drawdown.

### Cited Findings
- C01. Freefincal / BacktestIndia, "Is Indian Momentum Investing Just a Liquidity Illusion?" (T. Desai, 2026, March per search listing). Scaled-turnover split of a 12-month-return top-30 momentum book. — [Freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
  - Rule: top 30 by 12-month return, split into two groups of 15 by scaled turnover (daily turnover divided by market capitalisation); annual rebalance, equal weight [P].
  - Period/universe: Dec 2006 to Jun 2025, called 18.5 years and also "19-year"; NSE stocks including delisted names per the platform bio [P].
  - Net CAGR / max drawdown: low-turnover 19.43% / -66.41%; base momentum 14.60% / -70.61%; Nifty 50 10.41% / -55.12%; high-turnover 8.51% / -75.09% [P]. Gap low minus high = 10.92 pp; high-turnover is 1.90 pp below Nifty 50 [C].
  - Other: 97% of rolling 3-year windows positive for the low-turnover half, worst 3-year CAGR -8.9%; high-turnover drawdown took over 8 years to recover [P]. Sharpe and turnover not given.
  - Costs/tax: brokerage, slippage, LTCG 12.5%, STCG 20% included [P]. The platform FAQ states 0.11% transaction cost per trade plus 0.05% slippage (see C03) [P]; if "per trade" means per leg, the round trip is 0.32% [C], close to the 33.20 bp delivery two-leg figure in 00 section 6.
  - Flaws: hypothetical backtest, no significance tests, one annual-rebalance path, survivorship handling in this specific study not explained, drawdowns of -66% to -75% mean the 15-stock groups are very concentrated, and the 15/15 split is a post-hoc cut.
  - Price-only: price + volume + shares outstanding (market cap). No fundamentals.
  - Overlap with 00: slow cross-sectional momentum is closed (trials 119-127, 204; family N=12, next bar t >= 2.865). A scaled-turnover conditioner is not listed in 00; 3f lists "liquidity, illiquidity ... tested in section 85" only as standalone factors, and L42 shows ranks 201-400 survive at +0.91%/month (t 3.00).
- C02. Freefincal / BacktestIndia, "Does factor investing outperformance fail for high-turnover stocks?" (same author, Dec 2025 data). — [Freefincal](https://freefincal.com/does-factor-investing-outperformance-fail-for-high-turnover-stocks/)
  - Rule: Nifty 500, top 50 per factor, split 25/25 by scaled turnover; annual rebalance, equal weight; factors: Quality (high ROE), Value (low PE, low PB, high dividend yield), Low-vol (36-month price standard deviation), Momentum (12-month return / 12-month volatility) [P].
  - Period: Dec 2006 to Dec 2025; net of brokerage, slippage, LTCG 12.5%, STCG 20%; Nifty 50 net CAGR 10.41%; Nifty 500 Sharpe 0.51 [P].
  - Net CAGR low vs high scaled turnover: Quality 15.45% vs 8.16%; Value 13.74% vs 12.23%; Low-vol 14.11% vs 14.03% (Sharpe 0.87 vs 0.85); Momentum 15.04% vs 11.89% [P]. Gaps: 7.29, 1.51, 0.08, 3.15 pp [C]. Max drawdowns -42.80% to -77.70% [P].
  - Author reads scaled turnover as a near-universal filter for factor premia except low-vol, and warns large factor funds must buy high-turnover stocks [P].
  - Flaws: same as C01; survivorship handling not described for this study [P]. Momentum gap here (3.15 pp) is far below C01's (10.92 pp), so the effect size depends on construction.
  - Price-only: momentum and low-vol legs yes (plus market cap); quality/value need fundamentals.
  - Overlap with 00: low-vol sleeve and momentum x low-vol are "Leave" (3g); Pivot B "low-vol/quality overlay" is untested. The turnover conditioner is new.
- C03. BacktestIndia site summary of published studies (low-vol, multi-factor, momentum). — [BacktestIndia](https://www.backtestindia.com)
  - Low-vol 18-year: 12.38% net CAGR, -44% drawdown, 20% less volatile, 7-month recovery; sample "Top 20 Low Volatility" annual: 14.2% (2006-2024), -32%, volatility 15.8%, Sharpe 0.90; multi-factor sequential: 14.61%, -55%, Sharpe 0.48; "Lost Decade" test: low-vol beat the Nifty 50 in all 102 rolling 10-year windows 2007-2025 [P].
  - Costs: 0.11% transaction cost per trade, 0.05% slippage, 12.5% LTCG over one year, 20% STCG, Rs 1.25 lakh exemption [P]. Delisted stocks included [P].
  - Flaws: the site's own numbers disagree (14.2% vs 12.38% for low-vol; end date Dec 2025 vs Jun 2025) [P]; it is a vendor page, rebalance annual, 102 rolling windows are heavily overlapping so they are not independent (my reading).
  - Price-only: low-vol yes.
  - Overlap: low-vol Leave in 3g.
- C04. Capitalmind, "Momentum investing basics India" (2019). Monthly top-30 by 52-week return. — [Capitalmind](https://www.capitalmind.in/insights/momentum-investing-basics-india)
  - Rule: first trading day of month, rank by 252-day return, buy top 30 equal weight, long-only [P].
  - Period: Jan 2007 to 2019; includes bankrupt/stopped-trading companies; only about 750 of 2,000+ securities traded above Rs 1 crore [P].
  - Result: 12.6% vs Nifty 8.9% and Nifty 500 8.7% (+3.7 and +3.9 pp [C]); Rs 100 to Rs 464; beat the index in 6 of 13 years; sharp underperformance 2008 and 2016; random 30-stock portfolios 99% of the time under 7% [P].
  - Variants: gain-loss momentum (share of up-days x return) 14.7%, Rs 594; volatility-adjusted (excess 52-week return / annualised daily volatility) 16.8%, Rs 749 [P]. Both reduced drawdowns per the article; drawdown table was an image [P].
  - Costs: excludes transaction costs, short-term capital gains tax and dividends [P]. Only monthly rebalance and 52-week lookback tested [P].
  - Price-only: yes.
  - Overlap: slow momentum closed; gain-loss is a cousin of frog-in-the-pan (trial 204 FAIL, L57 FAIL); vol-adjusted ranking is close to 3e row 1 (volatility-scaled momentum, sweep-local "Trial 1", no trial row). Old (2019), gross.
- C05. Curious Investor (Manu Vatayan Jha), "Weekend Stats 5th Nov'23". Delivery-volume multiplier screen. — [Substack](https://curiousinvestinginsights.substack.com/p/weekend-stats-5th-nov23)
  - Screen: stocks whose end-of-day BSE+NSE delivery volume is at least 2x their average monthly delivery volume ("Volume Multiplier"); pools Nifty 50 or Nifty 500; monthly or quarterly rebalance [P].
  - Claimed: monthly rebalance "drops significantly"; quarterly with Nifty 500 pool best; Nifty 50 pool only gives a "meagre 107%", below Nifty 50 CAGR; a benchmark line "281% to 241%" is ambiguous [P]. Result tables are images.
  - Missing: period, CAGR, drawdown, costs, tax, data vendor, survivorship, weighting and exit rules [P].
  - Price-only: no, needs delivery quantity (in the full NSE bhavcopy).
  - Overlap: 3e row 10 "Deliverable %" is "Reject for now" and 00 has no look on delivery quantity multipliers; this evidence is too thin to change that. The same post's 52-week-high backtest (5 years vs Nifty 500) is image-only [P]; 52-week high is "Leave"/"Skip" in 3f/3g.

### Inferences
- The only actionable new item here is the scaled-turnover conditioner (C01/C02). It is computable from bhavcopy price x volume and shares outstanding, and it could first be run as a measurement on the existing trial 126 trade list (split trades by scaled turnover), not as a new trial. That is my inference; 00 does not record such a split.
- C01 reads the premium as an illiquidity premium; the project's own L42 result (ranks 201-400 survive) neither confirms nor refutes this, because rank by size or traded value is not scaled turnover. Do not treat C01 as evidence for or against trial 126.
- Costs in C01-C03 (0.16% per trade including slippage, taxes at 12.5%/20%) are in line with the project's 33-59 bp delivery round trip, so these are the closest to net-of-cost evidence found outside GitHub.
- Catalogue index (IDs only, no new facts). Section (a): C01 scaled-turnover momentum, C02 factor x turnover, C03 BacktestIndia low-vol/multi-factor, C04 Capitalmind basics, C05 delivery-volume multiplier. Section (b): C06. Section (c): C07 Capitalmind live, C08 Capitalmind page rules, C09 Weekend Investing Mi_LT, C10 Weekend Investing Mi 20/EverGreen, C11 Nifty200 Momentum 30 fund vs index, C12 StockViz HTP, C13 Momo India. Section (d): C14 QuantConnect Nifty/USDINR, C15 Kaggle (none), C16 Sharpely/DEV.to leads. Section (e): C17 gap trading, C18 data insights, C19 ML long-only, C20 pairs/other EPAT. Section (f): C21 Samasthiti dual momentum, C22 Momentum Lab dual momentum, C23 QuantIndia gold rotation, C24 turn-of-month, C25 index inclusion/exclusion, C26 insider, C27 buyback, C28 NSE low-vol 30, C29 delivery % / F&O ban / 52-week-low / sector rotation (negatives), C30 arXiv lead (unread; the Joshipura paper is inside C29).

### Gaps
- No net-of-cost practitioner study found for: weekly-rebalanced momentum, breakout, relative strength vs index, volatility-targeting, gold/Nifty switching with tax, turn-of-month, sector rotation, or insider/promoter buys. The covered families are reported gross or not at all.
- The Freefincal methodology page on BacktestIndia was not read, so the survivorship, delisting-return and corporate-action treatment behind C01-C03 is unknown.
- Momo India pages (momoindia.substack.com post and archive) returned 404; MarketCalls and Zerodha Varsity backtest modules were not read.

## (b) Live-verified results: Tradetron and Streak delivery-horizon strategies with a 12+ month track record

### Takeaway
I found no verifiable 12+ month live record for any Tradetron or Streak delivery-horizon (equity CNC) strategy. Streak has no marketplace, Tradetron's marketplace page did not load for me, and both platforms are discussed mainly for F&O and intraday.

### Cited Findings
- C06. Tradetron/Streak track records. — [AlgoTest comparison (vendor)](https://algotest.in/blog/streak-vs-tradetron.md)
  - Only Tradetron has a marketplace; Streak does not [P]. The article does not say whether Tradetron verifies marketplace returns, and warns that marketplace past returns do not guarantee future results [P]. It does not mention equity delivery (CNC) for any platform; AlgoTest itself is focused on F&O [P]. The article is published by a competitor.
  - Tradetron marketplace page fetch returned 404 [P] ([tradetron.tech/marketplace](https://tradetron.tech/marketplace)). Search for verified one-year positional returns found only platform descriptions and reviews; none cites verified multi-year or one-year returns [S] ([Tradetron review](https://www.techjockey.com/reviews/tradetron)). A critical thread says marketplace strategies are often tested only briefly and cherry-picked years mislead [S] ([thread](https://threadreaderapp.com/thread/1344935532032266240.html)).
  - Streak: backtests report maximum gain/loss and drawdown [S]; one user found turning on brokerage flipped a profitable backtest to a deep loss because delivery trades carry higher STT [S] ([TradingQnA](https://tradingqna.com/t/zerodha-streak-brokerage-issue/46202)); another user reports backtest vs paper-trade results "pretty close", anecdotal [S] ([TradingQnA](https://tradingqna.com/t/backtest-vs-papertrading-results-from-streak-pretty-close/116932)); a user reports wrong Renko backtests for MIS orders [S] ([TradingQnA](https://tradingqna.com/t/zerodha-streak-issue-backtesting-results-are-wrong-for-renko-chart-for-mis-orders/111488)).
  - Quantman and AlgoTest backtests are for futures and options (positional means expiry-cycle positions); no Nifty 500 or stock-universe momentum results found [S] ([AlgoTest vs Quantman](https://algotest.in/blog/algotest-vs-quantman.md), [MarketCalls on Quantman](https://www.marketcalls.in/quantman/quantman-simplified-backtesting-and-automated-trading-interface-for-futures-and-options-traders.html)).
  - Price-only: not applicable (platforms, not signals). Overlap with 00: smallcases and marketplaces are "Leave" in 3g.

### Inferences
- This is a negative finding: no third-party-verifiable delivery-horizon record exists in what is publicly reachable. Nothing here can be used as out-of-sample evidence for any signal.
- Streak's brokerage anecdote supports the project's existing cost-first stance (delivery costs dominate high-turnover rules) but is anecdotal.

### Gaps
- Tradetron marketplace listings need a login or did not render; a logged-in check of "months live", ROI, drawdown on equity-delivery strategies was not possible.
- Streak has no public strategy leaderboard; Zerodha Z-Connect posts found were product announcements, not results.

## (c) Weekend Investing, Capitalmind Momentum, Samasthiti: published live returns vs Nifty 200 Momentum 30, and rules that differ from plain 6/12-month momentum

### Takeaway
No public page I could read compares a live momentum smallcase with the Nifty 200 Momentum 30 index. Vendors benchmark against Nifty, CNX 500, CNX 200 or mid/small indices, publish NAVs that Capitalmind itself says overstate investor returns (about 60% vs about 46% [S]), and the only index-vs-fund material is back-cast index CAGR plus a note that realised 3 and 5 year CAGRs fall well short of circulated backtests [S].

### Cited Findings
- C07. Capitalmind Momentum, live record (smallcase live since January 2019). — [Capitalmind review Jan 2022](https://premium.capitalmind.in/2022/01/capitalmind-momentum-review/)
  - December 2021 +7% vs Nifty +2.2% and CNX 500 +2.4%; calendar 2021 +83% vs 24% and 30% (index mapping not stated explicitly) [P].
  - Since-inception CAGR, volatility and max drawdown are described as outperforming but the numbers are not in the text [P].
  - Admission: smallcase NAV returns "seemed stretched compared to realised returns for most investors"; the firm now reports a "CM NAV" using closing prices as entry and exit on the rebalance day [P]. Costs mentioned only as the objective "to outperform net of costs"; tax not mentioned [P].
  - May 2021 factsheet: smallcase CAGR about 60%, estimated actual investor returns closer to about 46%; only live data used [S] ([factsheet May 2021](https://premium.capitalmind.in/2021/06/cm-momentum-monthly-fact-sheet-may-2021/)). Nov 2021 factsheet: backtests show about 30% chance of underperforming the index over one year, about 11% over three years, about 2% over five years [S] ([factsheet Nov 2021](https://premium.capitalmind.in/2021/12/cm-momentum-monthly-fact-sheet-nov-2021/)). By May 2022 the portfolio trailed the Nifty and CNX 500 on a one-year basis [S] ([May 2022 factsheet](https://premium.capitalmind.in/2022/06/momentum-factsheet-may-2022-ouch/)).
  - Flaws: 2019-2021 was a momentum/smallcap bull; the record found stops mid-2022; no Nifty 200 Momentum 30 comparison. Not price-only because the vendor's score is its own, but see C08.
  - Overlap with 00: slow momentum closed; smallcases "Leave" (3g).
- C08. Capitalmind Momentum Model, current rules (page copyright 2025). — [Capitalmind model page](https://premium.capitalmind.in/momentum-portfolio/)
  - Rule: 15 to 25 stocks, long-only, weekly rebalancing; stays in cash when opportunities are scarce; NSE stocks meeting minimum daily volume and market-cap criteria (about 90% of Indian market cap); a quantitative model scores price and volume parameters, candidates at the 90th percentile and above, Sharpe ratio used to rank candidates, weights set by rank and relative volatility; benchmark Nifty 500 [P].
  - No performance table, CAGR, volatility, drawdown or as-of date on the page; charts exclude transaction fees [P].
  - Price-only: price and volume yes (the exact score is not disclosed).
  - Overlap with 00: differs from plain 6/12-month momentum in four ways (weekly cadence, percentile price-volume score, Sharpe ranking, rank-and-volatility weights). 00 lists no weekly-cadence momentum trial and 3e row 1 only covers volatility-scaled momentum; weekly turnover against a 33-59 bp round trip is the likely obstacle (my inference).
- C09. Weekend Investing Mi_LT_CNX200 (smallcase page). — [smallcase](https://www.smallcase.com/smallcase/mi_lt_cnx200-WKIMO_0005)
  - Rule: non-discretionary 20-stock momentum portfolio from CNX 200, weekly rebalance, may hold cash via liquid ETFs such as LIQUIDBEES; "Recommended size 5-15L CAGR>15%" is the only return claim [P].
  - Status: the page says the smallcase is "played out" and will have no further rebalance updates, so it is retired [P].
  - 1y/3y/5y returns, drawdown and benchmark are not stated; live vs backtest is not specified [P].
  - Price-only: appears so (momentum rule), but the rule is not disclosed.
  - Overlap: weekly CNX 200 momentum is a cadence variant of closed slow momentum.
- C10. Weekend Investing performance claims (Mi 20, Mi EverGreen). — [Weekly review 19 Jul 2024](https://weekendinvesting.beehiiv.com/p/good-bad-ugly-weekly-review-19-jul-2024)
  - The 19 Jul 2024 review gives only weekly and FY25-to-date numbers (Mi 20 -6.8% week, +32% FY25; Mi 35 +25%; Mi EverGreen +24%); no since-launch, CAGR, 1y or 3y, no live/backtest label [P].
  - Mi 20 three-year CAGR 54% vs 26.4% for a mid and small cap benchmark (gap 27.6 pp [C]) in a July 2024 review [S] ([Weekly review 12 Jul 2024](https://weekendinvesting.beehiiv.com/p/good-bad-ugly-weekly-review-12-jul-2024); exact July page not confirmed). Mi 20 FY24 119.3% by late January 2024, later 123% [S] ([Weekly review 25 Jan 2024](https://weekendinvesting.beehiiv.com/p/good-bad-ugly-weekly-review-25-jan-2024)).
  - Mi EverGreen live on smallcase since 28 Sep 2021: +81% absolute, 27% CAGR vs CNX 200 +29% absolute, 11% CAGR [S] ([Weekly review 7 Mar 2024](https://weekendinvesting.beehiiv.com/p/good-bad-ugly-weekly-review-07-mar-2024)); the two CAGRs are consistent with the absolute numbers over about 2.4 years [C]; excess +16 pp.
  - Weekend Investing says backtest data is coloured black and real data blue in its own reports [S] ([smallcase blog 2021](https://www.smallcase.com/blog/the-good-bad-and-ugly-weekly-review-17-sep-2021/)).
  - Flaws: vendor marketing; benchmark chosen by the vendor (mid/small index, CNX 200) not Nifty 200 Momentum 30; window 2021-2024 was a strong small/mid-cap and momentum period; smallcase NAV vs investor return gap (see C07); no costs or tax shown.
  - Overlap: smallcases "Leave" (3g); L53 already ties the fund (17.28% after tax) with trial 126.
- C11. Nifty200 Momentum 30: index vs funds (the benchmark). — [HDFC leaflet June 2026](https://files.hdfcfund.com/s3fs-public/Others/2026-06/Leaflet%20-HDFC%20NIFTY200%20Momentum%2030%20Index%20Fund%20%28June%202026%29.pdf)
  - HDFC leaflet (data as of 29 May 2026): index TRI 18.8% CAGR vs Nifty 200 TRI 13.9% since index inception on 1 Apr 2005 [S]; gap 4.9 pp [C]. The index was launched long after 2005, so most of this is back-calculated (launch date not verified in my sources).
  - Tracking: HDFC ETF tracking error 0.22 and 3-year tracking difference -0.61%; Motilal Oswal ETF 0.44 and -0.68; Bandhan 0.31%; UTI 0.15% [S] ([sharpely HDFC ETF](https://sharpely.in/etfs/hdfc-nifty200-momentum-30-etfgrowth/42569)). Aggregator pages with inconsistent dates; verify against AMC factsheets.
  - Tickertape notes the index's widely circulated backtest figures are much higher than realised 3 and 5 year CAGRs as of January 2026 [S] (search summary; the Tickertape page itself was not retrieved). The NSE 2026 whitepaper cites Nifty500 Momentum 50 at 21.94% annualised since inception vs 18.85% for the Nifty 500 [S] ([whitepaper](https://www.niftyindices.com/docs/default-source/indices/nifty200-momentum-30/momentum-strategy-whitepaper_2026.pdf)).
  - Price-only: yes (index rule).
  - Overlap: this is the L53/C21 benchmark in 00; nothing here changes the tie.
- C12. StockViz, "Momentum without the Crash" (2 Oct 2021): High-To-Price (HTP) momentum, a 52-week-high variant. — [StockViz](https://stockviz.substack.com/p/momentum-without-the-crash)
  - No rule formula, period, CAGR, Sharpe or costs in the text; says naive monthly momentum portfolios suffer +50% drawdowns every 3-4 years and "the jury is still out" on crash avoidance in Indian equities [P]. Survivorship not addressed [P].
  - Negative finding: no usable numbers. Overlap: 52-week high is "Leave"/"Skip" (3f/3g).
- C13. Momo India (Substack). — [Momo India](https://momoindia.substack.com/p/backtest-reducing-momentum-drawdowns)
  - Search snippets only: DIY momentum typically rebalances monthly or weekly and goes to cash if too few stocks pass filters; backtests use only currently listed stocks (survivorship bias) [S]. Page fetch and archive returned 404 [P]. SSRN paper "Long Factors Not Short Change" mentioned in a call announcement [S] ([announcement](https://momoindia.substack.com/p/zoom-call-to-discuss-long-factors)).
  - Samasthiti: only the dual-momentum post was found (C21); no Samasthiti momentum smallcase record found.

### Inferences
- Plain monthly 12-month momentum is the reference; the vendor rules that differ are cadence (weekly), score (percentile of price and volume, Sharpe ranking) and cash fallback. None has a verified live record against the Nifty 200 Momentum 30; the closest verified-by-vendor number (Mi EverGreen +16 pp over CNX 200) is on a mismatched benchmark in a bull window.
- Capitalmind's own 60% vs 46% gap is a direct measurement of NAV-vs-investor slippage and a warning that any smallcase "live" CAGR is an upper bound.
- The only record in this group with a 3+ year live history is Capitalmind (2019-mid 2022), and its last found datapoint shows underperformance (May 2022), so the record is incomplete rather than damning.

### Gaps
- Current (2025-2026) live CAGR, drawdown and benchmark comparison for Capitalmind Momentum, Weekend Investing Mi 20/Mi 35, and any Samasthiti smallcase: not found; pages were paywalled, image-only or retired.
- Tickertape pages (WKIMO_0019 and others) returned 404; the exact Nifty 200 Momentum 30 3y/5y fund CAGRs versus backtest were not retrievable from a reliable primary page.

## (d) Kaggle notebooks (and QuantConnect posts) with a real out-of-sample test and net results

### Takeaway
No Kaggle notebook with an out-of-sample test and net-of-cost results was reachable; Kaggle pages are JavaScript-rendered and search returned none. The one QuantConnect-hosted Indian example is a 2014-era gross backtest with a look-ahead allegation.

### Cited Findings
- C14. QuantConnect / MarketCalls, "Rotating inversely correlated assets: Nifty and USDINR" (approx. 2014, comment dated 12 Sep 2014). — [MarketCalls](https://www.marketcalls.in/algo-trading/rotating-inversely-correlated-assets-nifty-usdinr.html)
  - Rule: hold whichever of Nifty and USDINR had the best return over a rolling 3 to 30-day window [P].
  - Claimed: Sharpe 1.3 vs 0.7 for Nifty; 42x returns vs 7x over 16 years (the intro says 15 years); CAGR and drawdown not reported [P]. Costs, slippage, rolls not stated [P].
  - Flaws: hypothesis (negative correlation) failed in the author's own words; a commenter alleges look-ahead in the selection code; curve-fitting risk acknowledged; strongly trending sample; no out-of-sample [P].
  - Price-only: yes, but needs Nifty and USDINR futures.
  - Overlap: 00 (phase3-scoping section 1) records no documented USDINR effect for intraday; this is a daily rotation and is not delivery-horizon cash equity. Old and unusable as evidence.
- C15. Kaggle search for Nifty backtest notebooks. — [Kaggle search](https://www.kaggle.com/search?q=nifty+backtest+momentum)
  - Fetch returned only a title (rendered by JavaScript) [P]; web search for Kaggle Nifty 500 out-of-sample notebooks returned none [S] ([search result: Sharpely](https://sharpely.in/blogs/backtesting-101-how-to-know-if-strategy-works/)). Negative finding.
- C16. Related leads, not verified.
  - Sharpely warns that a backtest on current Nifty 500 constituents back to 2015 selects its universe from the future (survivorship); its worked example is a top-20 by 6-month momentum, held one month, rebalanced monthly, with no results quoted [S] ([Sharpely](https://sharpely.in/blogs/backtesting-101-how-to-know-if-strategy-works/)).
  - A DEV Community article on walk-forward out-of-sample Nifty backtesting appeared in results but was not opened [S] ([DEV](https://dev.to/shaktitiwari/walk-forward-out-of-sample-backtesting-for-nifty-no-lookahead-bias-python-guide-3ji7)).

### Inferences
- Platform-hosted Indian notebooks and posts are rarely out-of-sample and rarely net; absence here is itself informative for the "which numbers to trust" question.

### Gaps
- Kaggle needs a browser session to list notebooks; the DEV.to walk-forward article was not read; no QuantConnect Indian equity momentum posts after 2014 were found.

## (e) QuantInsti EPAT NSE reports: strategy, result, flaws

### Takeaway
The EPAT NSE projects I could read report gross returns, exclude transaction costs, choose stocks with hindsight and use short or no out-of-sample windows; none supports a delivery-horizon signal. The headline "24.9% CAGR, drawdown 2.4%" gap strategy has implausible risk figures and no costs.

### Cited Findings
- C17. Hetansh Gosar (EPAT batch 61), "Gap Trading Strategy: Based on the Markov Rule" (24 Dec 2024). — [QuantInsti](https://blog.quantinsti.com/epat-project-gap-trading-strategy-based-on-the-markov-rule)
  - Rule: long-only, enter at the day's close, exit at the next open when today's candle body exceeds yesterday's, close above open and change under 2%; stay in cash when Nifty ATR/price exceeds 3% [P].
  - Universe/period: ten hand-picked stocks (Bharti Airtel, Coal India, Colpal, L&T, M&M, Reliance, SBI, Solaris, Trent, Zydus), 1 Jan 2014 to 1 Jan 2024, yfinance; no in/out-of-sample split [P].
  - Claimed: CAGR about 24.9%, cumulative 771.6%, volatility about 4.1%, max drawdown about 2.4%; "theoretical" Sharpe above 5, untested live [P]. 771.6% over ten years implies 24.2% a year [C], slightly under the stated 24.9%.
  - Costs: excluded; author says they "could be pretty high" because trades are daily [P].
  - Flaws: stock choice unexplained; assumes fills at exact open and signals computed from the same close; text and code disagree (candle body vs true range, one-sided vs two-sided 2% band) [P]. A Sharpe of about 6 from ten single stocks is not credible without a look-ahead or execution-price explanation (my inference).
  - Price-only: yes (OHLC).
  - Overlap with 00: overnight and gap lines are closed (trials 124-125 FAIL; L23 overnight +16.78 bp unconditional; L36 results-gap aligned drift 0 by close; L49). At 33.20 bp two-leg, a daily-turnover rule needs a large gross edge.
- C18. Lokesh Kumar, "Data insights trading strategy" (28 Sep 2020). — [QuantInsti](https://blog.quantinsti.com/data-insights-trading-strategy-python-project-lokesh-kumar/)
  - Rules: short when volume is below its 3-day average and price below its 3-day average; sector pair mean reversion; RSI-21 on one stock. 20 stocks (two per sector) chosen from 126 candidates by rolling return and volatility [P].
  - In-sample Oct 2010 to Dec 2018: volume/price 55% hit ratio, 9.7% average annualised return; pairs 52%, 13.7%; RSI 69% on 67 trades, 6.5%. Out-of-sample Jan to Mar 2019 (three months): volume/price 55%, 25.3% (nine pre-selected stocks); pairs 45%, 5.4%; RSI 50% on 4 trades, 4.5% [P].
  - Costs excluded; Sharpe and drawdown named but not reported; Yahoo data [P].
  - Flaws: parameters tuned on the same data; stock selection uses full-period return and volatility (look-ahead and survivorship); three-month out-of-sample; only two pairs cointegrated; some out-of-sample names lost heavily (TVTODAY pair -38.1%) [P].
  - Price-only: yes (price and volume).
  - Overlap: short-term reversal lost here (trials 121-122); volume-price rules closed with the rule lab (L55, 0 survivors).
- C19. Pranav Lal, "Machine learning model for a long-only strategy" (retail trader project). — [QuantInsti](https://blog.quantinsti.com/machine-learning-model-long-only-strategy-retail-trader-project-pranav-lal/)
  - Rule: decision tree on encoded buy indicators, one model per stock, signal 1 long and 0 sell; Nifty 50 stocks, about ten years, Yahoo adjusted close; split ratio not stated [P].
  - Claimed "annual return of 28%" and "drawdown in some cases -22%", but the per-stock outputs shown give 11.95, 14.40, 12.97, 25.34% annualised, Sharpe 2.43, 1.27, -0.18, 4.32, drawdown -5.34 to -11.40%; accuracy 0.55 to 0.61 [P].
  - Costs not mentioned; pooling several stocks produced implausible returns, which the author flagged [P].
  - Overlap: ML/TSFM and Ranker lines are closed (L46-L47, trials 121-122).
- C20. Other EPAT India projects. — [EPAT projects list](https://www.quantinsti.com/articles/algo-trading-projects/)
  - Pairs trading across NSE sectors (data 1 Jan 2008 to 31 Dec 2014, Yahoo adjusted close, ADF at 90% significance, Bollinger better than z-score): no returns, Sharpe or drawdown quantified; costs "may affect" profitability; no out-of-sample [P] ([QuantInsti](https://blog.quantinsti.com/epat-project-mean-reversion-statistical-arbitrage-pair-trading-strategy-indian-market-sectors/)).
  - Bank Nifty deep learning, Bank Nifty stock NN allocation, and dispersion trading projects list no results [P]. A 2015-2025 stat-arb project on cointegrated Indian pairs appears in search results but was not opened [S] ([tag page](https://blog.quantinsti.com/tag/epat-trading-projects/)).
  - Overlap: pairs are "Leave" (3g).

### Inferences
- The EPAT corpus is educational. Every reachable NSE project fails at least two of: net of costs, true out-of-sample, point-in-time universe. Treat as idea source only.

### Gaps
- Many EPAT project pages (batch 2020-2025) were not opened; the "linear and logistic regression Nifty 50" and "2015-2025 stat-arb walk-forward" projects were seen only as titles.

## (f) Index inclusion/exclusion, insider/promoter, low-vol, 52-week-low and 3-year loser, sector rotation, gold-Nifty, turn-of-month, F&O ban and delivery-percentage evidence

### Takeaway
Practitioner evidence is thin and mostly gross: gold/Nifty dual momentum and turn-of-month have blog numbers without costs or tax, index exclusion rebound (+4 to 7% at 60 to 240 days) and insider purchases have academic support from older samples, and I found no usable Indian studies for F&O ban, delivery percentage, 52-week-low contrarian screens or sector rotation.

### Cited Findings
- C21. Samasthiti, "Indian edition of the Dual Momentum Strategy with Nifty/Gold" (data to Jan 2024). — [Samasthiti](https://samasthiti.substack.com/p/indian-edition-of-the-dual-momentum)
  - Rule: monthly, fully in one of Nifty 50, ABSL Income Fund or Gold BeES; absolute momentum test on Nifty vs debt, then relative test vs gold; 12-month lookback excluding the current month [P].
  - Period: Dec 1996 to Jan 2024, month-end values; CAGR Nifty 12.4% vs Dual Momentum 14.0% (+1.6 pp [C]); drawdown not given for the full period, but Nov 2008 about 21% vs Nifty more than 50% and 2020 about 11% vs about 30%; Sharpe not reported [P].
  - Costs and tax: not addressed; a reader comment asked about capital gains with monthly switching (2024 rules) and got no modelled reply [P]. Gold uses a spot price series before Nov 2009, not an ETF [P]. Data source for the index and debt fund not stated [P].
  - Flaws: starting-point sensitivity tested (start years from 1996 with at least 15 years; strategy beats buy-and-hold in all but one) but table is an image; monthly switching creates STCG at 20% (my inference).
  - Price-only: price series for Nifty, gold and a debt fund NAV; not bhavcopy-only.
  - Overlap: dual momentum NIFTYBEES/GOLDBEES/liquid is "Leave" in 3g; "gold/debt dual momentum" is an untested Pivot B family in 00 section 4.
- C22. Momentum Lab, "Backtesting Dual Momentum Strategy: Nifty and Gold" (2014 to 2024). — [Momentum Lab](https://momentumlab.substack.com/p/backtesting-dual-momentum-strategy)
  - Rule: 200-day returns of Nifty and gold vs a 200-day fixed deposit return; hold the winner if it beats FD, else FD [P].
  - Claimed: CAGR 18.79% vs Nifty 12.13% vs gold 10.86%; max drawdown -11.42% vs -34.00% vs -21.44%; absolute returns 382.33%, 184.65%, 156.50% [P]. The stated totals imply about 9.1 years, not ten [C].
  - Costs/tax, data source, rebalance frequency and FD assumption: not disclosed; promotional (links to a video and paid course) [P].
  - Overlap: same as C21. Do not use without the missing assumptions.
- C23. QuantIndia Substack, "Momentum in the Indian market" (data to 9 Jan 2025). — [QuantIndia](https://quantindia.substack.com/p/momentum-in-the-indian-market)
  - Rule: hold NIFTYBEES if short-term (1-6 month) or long-term (6-12 month) momentum ratio is positive, else GOLDBEES; monthly, one-month signal lag; ETFs from Yahoo Finance, GOLDBEES from March 2010 [P].
  - No CAGR, drawdown or Sharpe values in the text; no costs, taxes or survivorship; text says "> 0", code tests "> 1"; also a random-forest drawdown predictor with non-time-aware cross-validation and a possibly misaligned label [P].
  - Negative finding: no numbers to quote. Overlap: as C21.
- C24. Turn-of-month on Indian indices. — [Satish and Bheemanagouda, RFB 2023](https://rfb.ase.ro/Vol15-2023/dec2a.asp)
  - Nifty 50, Sensex, Nifty SmallCap 50 and BSE SmallCap, April 2007 to February 2023; t-tests and Mann-Whitney tests conclude the TOM effect is significant and stronger in smaller indices; no day-window, mean returns, t-statistics or cost discussion in the abstract; DIIs trade more toward month-end [P].
  - Older: Mangala and Sharma on Nifty 1994 to 2005 found high returns around the month turn [S] ([Paradigm 2007](https://ideas.repec.org/a/sae/padigm/v11y2007i2p16-22.html)). QuantifiedStrategies claims a 10.5% CAGR TOM strategy on Nifty 50 since 2007 using Yahoo data [S] ([article](https://www.quantifiedstrategies.com/end-of-month-effect-in-nifty-50-does-it-exist-turn-of-the-month/)); the page was bot-blocked so the rule, exit and costs are unread.
  - Flaws: index-level, no costs, indices (especially small cap) are not cheaply tradable; the published effect sizes are missing.
  - Price-only: yes.
  - Overlap: rejected in 3e ("timing luck is variance"), "Leave" in 3g, and an untested Pivot B family; 00 section 6 records about 41 bp gross per window vs about 10 bp ETF round trip.
- C25. Nifty 50 inclusion/exclusion. — [Chhatwani, JCAR 2020 (IIM Indore)](https://publishingindia.com/archive/jcar/price-and-volume-effects-of-nifty-50-index-reorganization)
  - Event study 2000 to 2016: inclusions earn positive abnormal returns that reverse within 60 days; exclusions show negative returns only in the first ten days and then about +4% to +7% abnormal returns at 60 to 240 days [P]. Event count, windows and test statistics not visible (full text restricted) [P].
  - Another search snippet: announcement-day abnormal returns for scheduled reorganisations not significant, effective-day positive but not sustained; exclusions negative [S] ([RPM paper](https://rpm.ndimdelhi.org/doi/pdf/10.1177/rpm.2015.13.1.1.pdf); claim-to-URL mapping not confirmed).
  - Flaws: no costs, abnormal returns vs a model benchmark, a handful of events per year (my inference, count unverified), post-exclusion rebound could be mean reversion in losers.
  - Price-only after the event list (NSE press releases).
  - Overlap: 3e row 8 "Later: an event-study look first, not a trial"; no L-row for it. This is the one event family with a numeric effect (+4 to 7% over 60 to 240 days) that could be tested from price data plus a list of exclusions.
- C26. Insider purchases. — [NITK thesis (Anil Kumar M., 2018)](https://idr.nitk.ac.in/handle/123456789/14150); [NSE working paper (Brochet, Lee, Srinivasan)](https://nsearchives.nseindia.com/research/content/1516_BS3.pdf)
  - Thesis: BSE insider transactions April 2007 to March 2015, four-factor model plus event study, purchase portfolios earn positive abnormal returns and sales negative [S]. Brochet et al., 2006 to 2014: positive significant relation between net insider purchases and future returns, insiders trade ahead of earnings news, overall opportunistic trading limited [S]. Both fetches failed (404, timeout), so these are snippets only.
  - Both pre-date the 2015 PIT Regulations; no promoter-specific or post-2015 backtest found [S]. Reg 7(2) Form C filings (promoter trades above Rs 10 lakh a quarter, per a secondary source, to be verified) are public on NSE/BSE [S] ([Ziromarket](https://ziromarket.com/blog/insider-trading-disclosures-sast-sebi-india)). Late or missing disclosures have drawn SEBI penalties, a data-quality risk [S] ([Business Standard](https://www.business-standard.com/amp/article/pti-stories/sebi-fines-2-promoters-of-aadi-industries-rs-30-lakh-for-disclosure-lapses-119050100694_1.html)).
  - Costs not stated. Price-only: no (needs filings; event date vs filing date matters for look-ahead).
  - Overlap: 3e row 7 "Trial 2" (family N=2, t >= 2.24), no trial row; Pivot B untested; L50 (bulk/block) VOID for too few events.
- C27. Buybacks. — [Business Perspectives, "Trading strategy using share buybacks: evidence from India"](https://businessperspectives.org/journals/investment-management-and-financial-innovations/issue-351/trading-strategy-using-share-buybacks-evidence-from-india)
  - Title seen in results; fetch returned 403. Rule, period and results not read [P]. Overlap: buyback tender reserve is "Leave" (grade C, small) in 3g.
- C28. NSE Nifty100 Low Volatility 30. — [NSE white paper Jun 2018](https://archives.nseindia.com/content/indices/NIFTY100_Low_Vol30_White_paper_Jun2018.pdf)
  - Rule: 30 least-volatile Nifty 100 stocks by one-year standard deviation of daily log returns, quarterly review, incumbents kept within top 60; outpaced Nifty 100 by 400 bp a year since 1 Apr 2005, highest drawdown -49.5% [S]. An aggregator reports June 2026 one-year total return -1.23% and five-year +11.40% annualised, beta 0.87 [S] ([Sharpely](https://sharpely.in/indices/nifty-100-low-volatility-30/49/fundamentals)); aggregators disagree on dates, treat with caution.
  - S&P DJI (2017, S&P BSE LargeMidCap, 2005 to 2016): low-vol excess returns significant, more in down markets [S] ([S&P DJI](https://www.spglobal.com/en/research-insights/market-insights/exploring-low-volatility-over-the-long-term-in-india)).
  - Flaws: index backtest is back-cast; gross vs net unclear; 2018 white paper pre-dates the recent period.
  - Price-only: yes. Overlap: low-vol sleeve "Leave" (3g); see C02/C03 for net evidence.
- C29. Negatives: delivery percentage, F&O ban, 52-week-low and 3-year losers, sector rotation.
  - Delivery percentage: no multi-year Indian study with next-day or multi-day returns found; Trendlyne "rising delivery percentage" backtests exist but results are subscription-only [S] ([Trendlyne](https://trendlyne.com/fundamentals/back-tests/9913)); the only data piece is a single-month Capitalmind analysis (January 2016) whose author says it is "not very useful to use this data to trade per se" [S] ([Capitalmind](https://premium.capitalmind.in/2016/02/delivery-shockers-the-january-2016-edition/)). BSE shows higher delivery percentages because some stocks are compulsorily delivered, so cross-exchange comparisons mislead [S] ([Business Standard](https://www.business-standard.com/markets/news/confidence-delivered-domestic-markets-sustain-40-trade-triumph-124021100339_1.html)). Overlap: 3e row 10 "Reject for now".
  - F&O ban: no NSE study found; only explainers (ban at 95% of market-wide position limit, lifted below 80%; cash trading continues) [S] ([Wright Research](https://www.wrightresearch.in/blog/fando-ban-what-it-is-and-how-it-affects-stock-prices/)) and a US 2008 short-sale ban paper (shorting down about 65%, banned-stock prices rose but attribution unclear) that does not transfer [S] ([Boehmer, Jones, Zhang](https://www.johnhcochrane.com/s/Boehmer_Jones_Zhang_ShacklingShorSellers.pdf)). Not in 00.
  - 52-week-low contrarian and 3-year losers: no Indian backtest found. An NSE working paper by Mayank Joshipura reports contrarian returns evident over a three-year horizon and momentum/contrarian effects not explained by risk alone [S] ([NSE paper](https://nsearchives.nseindia.com/content/research/res_paperfinal223.pdf)); PDF fetch timed out, so formation periods, size and costs are unread. Not in 00 as a family (reversal is closed only at short horizons, trials 121-122).
  - Sector rotation: no backtest with CAGR found; trackers (StockeZee) show relative-strength quadrants only [S] ([StockeZee](https://www.stockezee.com/sector-rotation)); the US calendar sector-seasonality strategy shows decay (20.1% CAGR 1985-2017, -4.6% over the last three years per the source) [S] ([CXO Advisory](https://www.cxoadvisory.com/calendar-effects/kaeppels-sector-seasonality-strategy/)). Overlap: "Leave" in 3g; Pivot B untested.
- C30. Unread leads. An arXiv paper 2302.13245 surfaced in a search for Indian momentum, but the PDF came back as binary and was not read, so the title and market are unverified [S] ([RePEc entry](https://ideas.repec.org/p/arx/papers/2302.13245.html)).

### Inferences
- Event families with a numeric Indian effect (exclusion rebound, insider purchases) are the least tested in 00 and the only ones with academic support; both need event lists, not just bhavcopy, and both have small event counts.
- Dual momentum with gold shows lower drawdown rather than extra return (Samasthiti +1.6 pp CAGR over 27 years [C]), consistent with 00's "allocation, not excess" label; the Momentum Lab figure is unusable without costs and assumptions.
- The absence of any Indian study on delivery %, F&O ban, 52-week-low contrarian and sector rotation means these cannot be dismissed or supported from literature; they would need in-house pre-registered tests.

### Gaps
- Magnitudes for TOM (window, mean return) are not in any source I reached; Chhatwani's event count and the Joshipura formation/holding periods are unread; NITK and NSE insider papers were read only as snippets; the buyback paper was blocked; the QuantifiedStrategies TOM page was bot-blocked.
- No Zerodha Varsity or Streak worked-example backtests were found for delivery-horizon strategies; none of the Varsity modules was opened.
- IIT/IIM/NISM student project reports beyond the Chhatwani paper were not searched in depth.
