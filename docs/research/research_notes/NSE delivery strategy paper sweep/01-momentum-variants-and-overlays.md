# Momentum variants, trend-following and risk overlays for a monthly NSE delivery stock book

Scope: research date 2026-11-01. Reader runs a monthly top-15 book from the 200 most-traded NSE names, ranked on volatility-adjusted 6- and 12-month return, equal weight (backtest +0.71%/month net, t 2.51). Any NEW cross-sectional momentum ranking faces the family bar t >= 2.865 (N=12; next 2.891). Every candidate below is tagged ANOTHER MOMENTUM RANKING, DISTINCT SIGNAL or OVERLAY ON EXISTING BOOK. Reliability tags: [P] = primary source read (paper text or abstract), [S] = secondary summary (CXO, Quantpedia, blog, search digest), [U] = unverified / from memory. Numbers marked "my arithmetic" are conversions I made, not figures the source states.

## (a) Momentum variants: original paper, replication status, India evidence

### Takeaway
Every variant in the literature (52-week high, residual, 12-7, acceleration, earnings, industry, seasonal, enhanced relative+absolute, stock time-series momentum) is either a re-ranking of the same price history the live book already uses, or needs data the project does not hold. None has a published net-of-cost India test. The only Indian evidence that touches the book directly is Singh and Walia (BSE, 2002-2019): cross-sectional momentum is large pre-2010 (about 1.0-2.0%/month long-short, gross) but its FF3 alpha is statistically indistinguishable from zero in 2010-2019 (0.56%/month, t 0.71 at a 12-month hold).

### Cited Findings

#### Tags, bar and cost arithmetic used in every row
- Closed-item map and project bar come from the local exclusion file; family bar t >= 2.865 (N=12), next 2.891; trial 126 (the live book) +0.71%/month, t 2.51, "would not clear at the family of 10"; trials 119/127/204 and looks L31/L32/L56/L57 failed — [00-already-covered.md](00-already-covered.md).
- Round-trip delivery cost the book pays: 33.05 bp at about Rs 33,000 per position; 39.05 bp with doubled slippage; about 41 bp at a Rs 3 lakh book (Rs 20,000/name); about 59 bp at Rs 6,667/name; DP Rs 15.34 per sell-scrip; STCG 20%, LTCG 12.5% — [00-already-covered.md section 6](00-already-covered.md). I use 37.5 bp as the mid-point of the assignment's 35-40 bp.
- Incremental-cost rule I apply (my arithmetic): a variant that replaces an extra fraction f of the book each month costs about f x 37.5 bp per month (f=10% -> 3.75 bp/month; f=25% -> 9.4 bp/month; f=50% -> 18.8 bp/month; a full-book switch out of equities and back in is one round trip, about 37.5 bp, with the tax event on top).
- The live book's own realized one-sided monthly turnover is not in the files I read; every "cost-clear" verdict below is therefore conditional on that number (gap).
- Long-short academic results cannot be bought in cash delivery (no short leg). The long-only share of any long-short spread is almost never reported in the sources below (inference).

#### Baseline: stock momentum in India (context for every variant)
- Singh and Walia (2020), Copernican Journal of Finance and Accounting 9(3):161-176, DOI 10.12775/CJFA.2020.018 [P]: 458 BSE-listed stocks with complete monthly data, Jan 2002-Oct 2019, penny stocks dropped, CMIE Prowess, formation t-12 to t-2 with a one-month gap, top/bottom decile, monthly buy-and-hold, no transaction costs. Cross-sectional (CS) long-short raw return by holding period K=1/3/6/9/12 months: 1.954 (NW t 4.48), 1.735 (3.63), 1.367 (2.98), 1.135 (2.65), 1.038 (2.20) %/month; FF3 alpha 1.661 (4.03), 1.427 (3.09), 1.087 (2.32), 0.854 (1.90), 0.782 (1.66); Sharpe 0.689, 0.578, 0.349, 0.283, 0.153. — [Singh and Walia abstract page](https://apcz.umk.pl/CJFA/article/view/CJFA.2020.018)
- Same paper, 12-month hold sub-periods (raw / FF3 alpha, %/month): 2002-07 CS 2.058 (t 4.30) / 2.164 (t 3.72); 2008-09 CS -1.326 / -1.220 (t -1.89); 2010-19 CS 1.249 (t 1.65) / 0.558 (t 0.71). Interpretation in the paper: CS alpha insignificant after 2010. — [Singh and Walia](https://apcz.umk.pl/CJFA/article/view/CJFA.2020.018)
- Survivorship caveat (my inference): requiring 458 stocks to have complete monthly data across Jan 2002-Oct 2019 drops delisted and non-surviving names, which flatters winner-minus-loser spreads and the TS result.
- IIMA Agarwalla, Jacob and Varma, four-factor model for India (IIMA WP 2013-09-05) [P]: momentum factor (WML) built on an 11-month return window, top/bottom 30% with a size split, equal weights inside, monthly, CMIE Prowess; average WML 21.9%/yr stated for Jan 1994-Dec 2014 (about 1.8%/month, my arithmetic) while another passage of the same PDF says Oct 1993-Dec 2013 and an earlier version says 21.2% — conflict inside the source, not resolved. — [IIMA PDF](https://iima.ac.in/sites/default/files/rnpfiles/1970004922013-09-05.pdf)
- Later IIMA release (search snippet only, page itself would not load) [S]: annualised WML 11.34% with volatility 17.65%, data through Mar 2023 — roughly half the 2013 paper's average (11.34% vs 21.9%; different release and window, so not like-for-like). Library: [IIMA India Fama-French-Momentum factors](https://web.iima.ac.in/~iffm/Indian-Fama-French-Momentum/).
- Ansari and Khan (2012), Managerial Finance 38(2):206-223 [abstract only]: strong momentum profits in India 1995-2006; CAPM and Fama-French fail to explain; idiosyncratic risk positively related to profits. — [Emerald](https://emerald.com/insight/content/doi/10.1108/03074351211193730/full/html)
- Sehgal and Jain (2011), J. Advances in Management Research 8(1):99-122 [abstract]: momentum larger for 6-6 than 12-12 formation-holding; sectoral momentum captures part of stock momentum; winners are mostly large-firm, high price-to-book stocks; CAPM/FF3 do not explain it. — [Emerald](https://www.emerald.com/insight/content/doi/10.1108/09727981111129327/full/html)
- Mixed older Indian findings (as described by later papers, not the originals) [S]: Sehgal and Balakrishnan (2002, Vikalpa 27(1):13-19) is the first Indian cross-sectional paper; a later re-test found significant contrarian profits instead of their "moderately positive" payoffs; a separate 1991-2006 study found no momentum profits or reversals with simple non-overlapping medium/long strategies; a thesis found neither strategy beat; one NSE 1997-2013 study found momentum with no January/April seasonality. — [search digest on Sehgal-Balakrishnan](https://www.publishingindia.com/archive/jcar/seasonality-in-momentum-profits-evidence-from-the-indian-stock-market)
- Maheshwari and Dhankar (2017 and related) [S]: winners drive the Indian effect; not a size/value/illiquidity artefact; profits strongest after UP markets; market-state-dependent pricing model failed to explain them. — [Addleton, "Evidence and sources of momentum profits: a study on Indian stock market"](https://www.addletonacademicpublishers.com/contents-emfm/248-volume-9-3-2014/2268-evidence-and-sources-of-momentum-profits-a-study-on-indian-stock-market) and [Publishing India seasonality paper](https://www.publishingindia.com/archive/jcar/seasonality-in-momentum-profits-evidence-from-the-indian-stock-market)
- Cross-country: Rouwenhorst (1999) emerging-market momentum — one source says 17 of 20 markets show momentum, another says 6 of 20; the sources conflict and the paper was not read, no India-specific series found. — [search digest](https://www.publishingindia.com/storage/PDFBrochures/2192.pdf). Chui, Titman and Wei find momentum weaker in East Asia (individualism) with nothing India-specific found. — [HKUST summary](https://bm.hkust.edu.hk/bizinsight/2010/05/roll-cross-cultural-differences-momentum-profits)

#### A1. 52-week-high proximity ranking (George and Hwang 2004) — ANOTHER MOMENTUM RANKING (needs t >= 2.865)
- Cite: George and Hwang (2004), "The 52-Week High and Momentum Investing", Journal of Finance 59(5) — [Quantpedia](https://quantpedia.com/strategies/52-weeks-high-effect-in-stocks), [CXO](https://www.cxoadvisory.com/1284/technical-trading/the-52-week-high-as-a-momentum-indicator-for-individual-stocks/) [S]. Original-sample %/month, t and turnover: not retrieved (gap).
- Claim in summaries: the ratio price / 52-week high forecasts better than past returns and industry factors. — [Alpha Architect](https://alphaarchitect.com/2014/11/the-secret-to-momentum-is-the-52-week-high) [S]
- Replication / international: Bornholt and Malin find ordinary momentum beats 52-week-high momentum in developed and emerging index markets; 52-week-high is unprofitable in emerging-market indices — [Griffith repository item 1](https://research-repository.griffith.edu.au/items/7519d620-c8d2-55df-984d-4293560ba0f8), [item 2](https://research-repository.griffith.edu.au/items/007b71f1-d78c-57a9-8ad4-84690e1371c2) [S; these are index-level, not stock-level tests].
- India: Quantpedia write-up of an Indian out-of-sample test, 2014-2017: total return 17%, Sharpe about 0.4, described as "not very stellar" (about 0.35-0.5%/month depending on whether the window is 3 or 4 years, my arithmetic; gross; window length not stated). No peer-reviewed NSE stock test found; an MBA project (NSE 50 stocks, 2006-2010) reports positive results but is unrefereed. — [Quantpedia India](https://quantpedia.com/an-analysis-of-52-weeks-high-effect-on-indian-stocks/) [S]
- Data: daily adjusted close and rolling 252-day high — daily prices plus corporate actions only (already held).
- Cost-clear: same monthly cadence as the live book, so incremental cost is only the extra name churn the new rank causes (unknown); edge needed is the t-bar, not the cost. Not testable from the sources.
- Overlap: profitability-sweep and stock-picking sweep both say "Skip/Leave" for 52-week-high proximity — [00-already-covered.md](00-already-covered.md). It is highly correlated with 12-month return (inference), so it would be an extra trial in the momentum family.

#### A2. Residual (idiosyncratic) momentum (Blitz, Huij and Martens 2011) — ANOTHER MOMENTUM RANKING
- Cite: Blitz, Huij and Martens (2011), "Residual momentum", Journal of Empirical Finance 18(3):506-521 — [IDEAS](https://ideas.repec.org/r/eee/empfin/v18y2011i3p506-521.html), [Quantpedia](https://quantpedia.com/strategies/residual-momentum-factor) [S].
- Effect: 12-1 month residual momentum 9.18%/yr (0.76%/month, my arithmetic) with volatility 15.27% (Sharpe about 0.60, my arithmetic), gross, long-short; secondary sources say similar returns at about half the volatility of total-return momentum, i.e. roughly double the Sharpe. Sample years and t-stat not captured (gap). — [Quantpedia](https://quantpedia.com/strategies/residual-momentum-factor)
- Turnover / holding: monthly rebalance; turnover figure not retrieved. Net-of-cost: no.
- Replication: the only emerging-market evidence found is an Erasmus master's thesis, not a refereed test — [Giakoumakis thesis](https://thesis.eur.nl/pub/66795/Emmanouil_Giakoumakis_641404_FinalThesis_FE_Masters.pdf) [S]. India: none found (a targeted search returned only generic Indian momentum papers). — [search digest](https://emerald.com/insight/content/doi/10.1108/03074351211193730/full/html)
- Data: daily/monthly prices plus a market (and ideally size/value) return series for rolling 36-month beta regressions — Nifty/index levels (held) and IIMA factor library (public).
- Cost-clear: unknown; an equal-weight monthly top-15 on residuals will turn over at least as much as raw momentum (inference), so the book's ~37.5 bp round trip applies in full to whatever extra names change.
- Overlap: entry-timing sweep "Defer, ranks below #6" and listed in Part B rejected; profitability sweep "Leave" — [00-already-covered.md](00-already-covered.md).

#### A3. Intermediate-horizon momentum, 12-7 (Novy-Marx 2012) — ANOTHER MOMENTUM RANKING (a lookback change)
- Cite: Novy-Marx (2012), "Is momentum really momentum?", Journal of Financial Economics — [CXO](https://www.cxoadvisory.com/momentum-investing/isolating-the-decisive-momentum-echo/) [S].
- Claim: momentum is driven mainly by returns 12 to 7 months before formation; the 6-2 signal faded in recent decades, 12-7 did not; 12-7 Sharpe ratios generally more than double those of 6-2 (US, gross, long-short). — same CXO page.
- Challenges: Goyal and Wahal, "Is Momentum an Echo?" question the 12-7 variable; a long-only practitioner replication found 12-2 momentum "very similar" to 12-7 for long-only investors. — [Alpha Architect](https://alphaarchitect.com/2016/01/is-price-momentum-a-brother-from-another-mother/) [S]
- India: no test found. Sehgal and Jain (2011) find 6-6 beats 12-12 in India, which points the other way for long formation windows — [Emerald](https://www.emerald.com/insight/content/doi/10.1108/09727981111129327/full/html).
- Data: daily prices only. Turnover: lower than 6-month (slower signal) in principle, not measured in sources.
- Cost-clear: a slower signal would plausibly reduce churn (inference), the only reason it could matter for a 37.5 bp round trip.
- Overlap: the book already blends 6- and 12-month volatility-adjusted returns; "lookback grids: Leave" in the profitability sweep — [00-already-covered.md](00-already-covered.md). Counts as another momentum trial.

#### A4. Price acceleration (Chen and Yu) — ANOTHER MOMENTUM RANKING
- Cite: Li-Wen Chen and Hsin-Yi Yu (and related), acceleration of the 12-month price path — [CXO](https://www.cxoadvisory.com/momentum-investing/stock-price-acceleration-as-a-momentum-investing-enhancement/), [CXO 2](https://cxoadvisory.com/momentum-investing/return-acceleration-more-effective-than-momentum) [S; the papers themselves were not read].
- Effect (US, 1962-2014, gross, long-short): conventional momentum 0.63%/month (monthly Sharpe 0.12); acceleration 0.95%/month (0.17); deceleration 0.50%/month (0.09).
- Flags in the summary: data-snooping in the chosen ranking interval, semi-annual reformation frictions and shorting costs would reduce returns, and acceleration/deceleration perform similarly at 1-2 month holding — which is the book's monthly horizon.
- India: none found. Data: daily prices only. Cost-clear: the 1-2 month result being weak means the monthly book is the wrong horizon for it (inference).
- Overlap: not named in the exclusion file; frog-in-the-pan (path-shape variant) failed twice (trial 204; L56/L57), which is the closest closed sibling — [00-already-covered.md](00-already-covered.md).

#### A5. Earnings / fundamental momentum (Novy-Marx; Sehgal and Jain 2015) — DISTINCT SIGNAL (price-independent in construction) or momentum overlay
- Cite: Novy-Marx, "Fundamentally, momentum is fundamental momentum" (NBER number not verified, [U]); India: Sehgal and Jain (2015), AAMJAF 11(1) [abstract] — [USM journal](https://ejournal.usm.my/aamjaf/article/view/aamjaf_vol11-no1-2015_3), [IDEAS](https://ideas.repec.org/a/usm/journl/aamjaf01101_47-84.html). Summary of Novy-Marx via [fffinstill](https://fffinstill.com/learning/concepts/fundamental-momentum-novy-marx-2015) [S].
- India sample: 493 BSE-500 stocks, Jan 2002-Jun 2010. Price winners beat earnings or revenue winners as a long-only leg, but on the long-short the earnings-based strategy performs best and subsumes price and revenue momentum; momentum persists up to six months. %/month, t and costs: not in the abstract (gap).
- Data: quarterly results / earnings surprise. The project holds 9,586 NSE filing events but no fundamentals database; PEAD was already tested and failed — [00-already-covered.md](00-already-covered.md) (L39: gross +0.25%/month, NW t 1.41, NO-GO).
- Cost-clear: earnings events are quarterly so a turnover of roughly 4 events a year per name is plausible (inference); the cost is not the issue, the signal already failed the closest test.
- Overlap: "earnings momentum closed by section 84" in the stock-picking sweep; PEAD NO-GO. Treat as closed; listed only because the question asked for it.

#### A6. Industry (sector) momentum (Moskowitz and Grinblatt 1999) — DISTINCT SIGNAL on a sector index, or another momentum ranking if used to tilt stock picks
- Cite: Moskowitz and Grinblatt (1999), "Do industries explain momentum?", Journal of Finance 54(4):1249-1290 — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html) [P abstract].
- Effect: stock momentum is significantly less profitable once industry momentum is controlled; industry predictability strongest at 1 month and lasting up to a year; industries ranked on prior six-month return, top/bottom 20% (secondary description). Return magnitudes not retrieved (gap). No consensus: Nijman et al. (2004) find individual-stock effects dominate in Europe; Research Affiliates argues industry momentum stems from factor momentum. — [Research Affiliates](https://www.researchaffiliates.com/insights/journal-papers/709-factor-momentum) [S]
- India: Sehgal and Jain (2011) find sectoral momentum captures part of stock momentum — [Emerald](https://www.emerald.com/insight/content/doi/10.1108/09727981111129327/full/html). No NSE sector-index test with costs found.
- Data: sector classification (NSE sector indices or the project's nse_indices) plus daily prices.
- Cost-clear: sector rotation across 10-15 sector ETFs/baskets; in cash delivery most sector indices have no liquid cheap ETF (inference, not verified), so the book would hold stocks inside winning sectors — churn similar to the live book.
- Overlap: "industry momentum: Leave" and "sector rotation: Leave" in the profitability sweep; sector rotation is a section 4 untested priority — [00-already-covered.md](00-already-covered.md).

#### A7. Sector rotation on NSE sector indices (priority item from section 4) — DISTINCT SIGNAL
- Evidence base is only A6 (US 1999; India Sehgal-Jain 2011 abstract). No Indian sector-rotation paper with t-statistics and costs was retrieved; no sector-ETF liquidity check done. — [Emerald](https://www.emerald.com/insight/content/doi/10.1108/09727981111129327/full/html)
- Cost-clear: unknown. Honest verdict: no published number to carry into a pre-registration; the candidate would need its own test.
- Overlap: section 4 priority, expected hit rate "low" in the exclusion file — [00-already-covered.md](00-already-covered.md).

#### A8. Same-calendar-month seasonality in the cross-section (Heston and Sadka) — DISTINCT SIGNAL
- Cite: Heston and Sadka (2010), JFQA 45(5):1133-1160 — [IDEAS](https://ideas.repec.org/a/cup/jfinqa/v45y2010i05p1133-1160_00.html) [S]. Stocks that beat their domestic market in a given calendar month tend to beat it again in the same month for up to five years; found in Canada, Japan and 12 European countries.
- US long-short on same-calendar-month returns, 1963-2011: about 13%/yr (about 1.1%/month, my arithmetic), gross — NBER w20815 (authorship from memory, likely Keloharju-Linnainmaa-Nyberg [U]) — [NBER w20815](https://www.nber.org/papers/w20815.pdf). A 42-market extension reports about 13%/yr too but its abstract says emerging markets are an open question with widely varying results [S; not verified in full text].
- India: no test found. Data: 5+ years of daily prices (held). Turnover: the signal is recomputed each month and leans on lags 12, 24, 36, 48, 60, so churn would be high (inference).
- Cost-clear: unlikely — gross 1.1%/month long-short with near-full monthly turnover leaves little after 37.5 bp x ~50-100% turnover (about 19-38 bp/month, my arithmetic) and no short leg. Candidate is a pre-registration idea only.
- Overlap: not in the exclusion file; the nearest closed item is the calendar sweep (turn-of-month is a section 4 item belonging to another researcher).

#### A9. "Enhanced" relative-plus-absolute momentum (Sehgal, Pandey and Sen 2025) — ANOTHER MOMENTUM RANKING (adds a filter)
- Cite: Sehgal, Pandey and Sen (2025), International Journal of Emerging Markets 20(10):4288-4307, DOI 10.1108/IJOEM-09-2023-1518 [abstract only; paywalled] — [Emerald](https://www.emerald.com/insight/content/doi/10.1108/IJOEM-09-2023-1518/full/html).
- Claim: six strategies on NSE-listed companies; the enhanced relative+absolute strategy beats conventional price momentum; multifactor models do not explain it; attributed to overreaction. No numbers, sample dates, turnover or costs available (gap).
- Data: daily prices only (the absolute filter is "own return > 0 or > risk-free").
- Cost-clear: unknown; the absolute filter shrinks the invested set in down markets so net turnover could be lower or higher (inference).
- Overlap: the closest closed item is the bear-market filter "Leave" and trend filter "Reject as a lead"; per-stock absolute filter is not listed as tested — [00-already-covered.md](00-already-covered.md).

#### A10. Stock-level time-series (absolute) momentum (Moskowitz, Ooi and Pedersen 2012; Singh and Walia 2020) — DISTINCT SIGNAL (long own-trend stocks, no ranking)
- Cite (original): Moskowitz, Ooi and Pedersen (2012), futures — numbers not retrieved (gap). Challenge: Huang, Li, Wang and Zhou (2020, JFE), 55 contract series Jan 1985-Dec 2015: asset-by-asset regressions show little evidence of time-series momentum in and out of sample; pooled t-stats can be inflated; the paper does not test single stocks. — [CXO](https://www.cxoadvisory.com/momentum-investing/intrinsic-time-series-momentum-does-not-really-exist/), [WashU](https://profiles.wustl.edu/en/publications/time-series-momentum-is-it-there/) [S].
- India: Singh and Walia time-series (TS) strategy invests in 20% of stocks with positive own trend: raw return by hold K=1/3/6/9/12: 2.326 (t 4.82), 1.876 (3.91), 1.672 (3.63), 1.392 (3.33), 1.764 (3.60) %/month; FF3 alpha 2.149 (4.62) down to 1.637 (3.49); Sharpe 0.830, 0.654, 0.471, 0.434, 0.453; 2010-19 12-month hold raw 2.091 (t 2.87), FF3 1.417 (t 1.69); 2008-09 raw -0.764. The authors find TS spans CS; TS has net-long exposure, so part of its return is market beta in a bull market. Gross, no costs. — [Singh and Walia](https://apcz.umk.pl/CJFA/article/view/CJFA.2020.018) [P]
- Conflict to flag: HLWZ find weak TSMOM in futures while Singh-Walia find strong TSMOM in Indian stocks; the latter has survivorship and bull-market-beta problems (inference), so neither contradicts the other cleanly.
- Data: daily prices only. Cost-clear: a stock-level absolute filter changes the number of names held, not the rank — likely changes cash weight (inference).
- Overlap: L32 time-series momentum was tested INTRADAY only (+0.70 bp, t 0.61, does not clear); monthly stock-level TS was not tested. Index-level trend filters are rated "Reject as a lead" — [00-already-covered.md](00-already-covered.md).

#### A11. Factor momentum (rank factors or NSE factor indices by their own trailing return) — DISTINCT SIGNAL / allocation
- Research Affiliates argues industry momentum largely reflects factor momentum — [Research Affiliates](https://www.researchaffiliates.com/insights/journal-papers/709-factor-momentum) [S]. No effect size, India test or cost data retrieved.
- Implementation would use NSE factor indices as ETFs/funds ("fallback implementation, not a signal" in the entry-timing sweep). Data: index levels only. Cost-clear: unknown.
- Overlap: NSE factor indices listed as fallback implementation, not a signal — [00-already-covered.md](00-already-covered.md). Little evidence; include for completeness.

#### A12. Liquidity-conditioned momentum (rank only within liquid or illiquid halves) — ANOTHER MOMENTUM RANKING
- Chui, Ranganathan, Rohit and Veeraraghavan (2023), Pacific-Basin Finance Journal 82:102193 [abstract]: 3,956 BSE stocks 2000-2021; momentum stronger in the most liquid stocks; the most illiquid show short/intermediate reversals; no magnitudes. — [Manipal repository](https://impressions.manipal.edu/open-access-archive/9369)
- Opposite reading (vendor-affiliated blog, flag: author runs BacktestIndia; byline conflict between T. Desai and M. Pattabiraman) [S]: Dec 2006-Jun 2025, Nifty200 Momentum 30 constituents' top 30 by 12-month return split by scaled turnover, annual rebalance, equal weight, net of brokerage/slippage/tax; net CAGR / max drawdown: low-turnover half 19.43% / -66.41%; base Momentum 30 14.60% / -70.61%; Nifty 50 10.41% / -55.12%; high-turnover half 8.51% / -75.09% (recovery over 8 years). The author reads it as an illiquidity premium. — [freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
- Conflict: Chui et al. (liquid = stronger) vs freefincal (low-turnover = stronger). Definitions differ (liquidity measure, annual vs monthly rebalance, ETF-constituent universe) so they are not directly contradictory; the book's universe is already the 200 most-traded names, so the liquid-half effect is largely built in (inference).
- Overlap: ranks 201-400 (L38: +1.00%/month, t 3.31; L42 repaired panel +0.91%/month, t 3.00) is the closed expansion of the same universe question — [00-already-covered.md](00-already-covered.md).

#### A13. Physical momentum / daily reversal (Tripurana and Devulapally 2023, arXiv 2302.13245) — NEGATIVE / low quality
- NSE 500, 2014-2021, mass-weighted "physical momentum" (turnover, inverse turnover, inverse volatility): daily contrarian/reversal portfolios beat Nifty (Sharpe 0.38-0.62; best reached about 16x final wealth); short/medium/long traditional momentum portfolios have Sharpe about 0.11-0.39 and max drawdown -9% to -32%; the authors state all Sharpe < 1. No costs. Not usable as evidence for a monthly delivery book (daily rebalance with zero costs cannot clear a 37.5 bp round trip). — [arXiv](https://arxiv.org/pdf/2302.13245) [P]
- Overlap: intraday/short-horizon reversal is closed (L31 -1.60 bp, t -0.48; intraday-3b stage 1a does not clear) — [00-already-covered.md](00-already-covered.md).

### Inferences
- The variants are mostly alternative weightings of the same 6-12 month price history; they will be highly correlated with trial 126, so each is effectively another entry in the momentum family and must beat t >= 2.865 on its own (and pay the multiple-testing penalty), not on "improvement over the base".
- India evidence says cross-sectional momentum was strong through the 2000s and had a statistically weaker 2010-2019 (Singh-Walia), and the most recent global index (IIMA through Mar 2023, snippet only) shows a lower factor premium than the 2013 paper. A variant can only be expected to add if it addresses that decay, which none of the retrieved Indian studies show.
- A10/A9 (absolute-trend filters) have the strongest Indian numbers on paper, but those are gross, survivorship-prone and partly bull-market beta; they are not a basis for a trial without a fresh pre-registration on the project's own panel.

### Gaps
- Jegadeesh-Titman (1993), Asness-Moskowitz-Pedersen "Value and momentum everywhere" (2013) and Moskowitz-Ooi-Pedersen (2012) effect sizes, t-stats and turnover were not retrieved; the "momentum everywhere" claim therefore rests on the Rouwenhorst/Chui/Singh-Walia items above, not on the original.
- George-Hwang, Blitz-Huij-Martens and Novy-Marx original %/month, t-stats and samples were not retrieved from primary text; only secondary summaries.
- No Indian test (NSE or BSE) of residual momentum, acceleration, 12-7, Heston-Sadka seasonality or factor momentum was found.
- Sehgal-Pandey-Sen (2025) and Sehgal-Jain (2015) have no accessible numbers (paywall/abstract only).
- Novy-Marx earnings-momentum NBER number not verified; NBER w20815 authorship not verified.
- The live book's realized one-sided monthly turnover is not in the files read.

## (b) Overlays that change risk rather than picks: trend filters, vol-scaling, stops, crash hedges, turnover control

### Takeaway
The published overlay gains (volatility scaling roughly doubling the momentum Sharpe, stop-loss cutting the worst month from about -50% to about -11%, Faber trend filters) are all gross, mostly US/global, mostly long-short, and none was found tested on NSE stocks with costs. In cash delivery the book cannot lever up or short, so only the de-risk half of each overlay is available; Indian tests are blog-grade and mixed (a drawdown cut with lower CAGR, or failure around sharp reversals such as March 2020).

### Cited Findings

#### B1. Market trend filter to cash (Faber 10-month SMA / 200-day SMA on an index) — OVERLAY ON EXISTING BOOK
- Cite: Faber (2007), "A Quantitative Approach to Tactical Asset Allocation", Journal of Wealth Management; 2018 update in Journal of Portfolio Management — figures below are from a search digest of secondary pages (candidates: [etf.com Swedroe](https://www.etf.com/sections/index-investor-corner/swedroe-why-financial-trends-persist), [FedSmith](https://www.fedsmith.com/2010/07/28/asset-allocation-your-tsp/)); the paper itself was not read [S].
- Effect (US, multi-asset): a secondary summary says the strategy raised annual return from 9.8% to 11.3% with only +0.2% volatility; a blog reports 1901-2008 stock market above the 10-month SMA +14.42%/yr (vol 14.30%) vs below +3.03% (vol 24.18%); the 2018 update finds similar results for 6-, 8- and 12-month windows. Drawdown and Sharpe figures were not in any retrieved source (gap). Independent JSE test (Pretoria MBA dissertation, 1961-2010): risk-adjusted gain survives high transaction costs [S]. Newfound Research: the result is sensitive to which day of the month trades; reported without costs. — [Pretoria repository](https://repository.up.ac.za/items/7f27d00d-4c0e-4826-acf0-1a7db806d25d)
- India (all blog/forum-grade, none refereed): a 200-day EMA hold-NIFTYBEES-only rule over 10 years cut the maximum drawdown to -20.19% from -36.34% buy-and-hold but with a lower CAGR — [blog/forum digest](https://tradingqna.com/t/dual-momentum-strategy-with-niftybees-goldbees/174470) (the specific post URL was not captured); a Momo India test of a 200-day MA on a momentum portfolio's NAV (move to cash when NAV falls below the average, checked on monthly rebalance days) is paywalled with results unseen — [Momo India](https://momoindia.substack.com/p/backtest-reducing-momentum-drawdowns).
- Turnover / cost: freefincal's version switches about 0.4 times per year. If one switch is one full-book one-way trade (about half the 37.5 bp round trip, ~19 bp, my arithmetic) that is under 10 bp/year, so costs do not bind; the tax event (STCG 20% on realized gains) does matter and belongs to the L53 after-tax replay. Gross/net: the Indian blog numbers are net of nothing stated.
- Data: index levels (Nifty 50/200 daily) already in nse_indices — held.
- Overlap: the entry-timing sweep says "index trend filter to cash: Reject as a lead; at most a reported-only variant"; the profitability sweep says bear-market filter "Leave"; L48 breadth/intermarket gating had 0 of 8 survive — [00-already-covered.md](00-already-covered.md).

#### B2. 6-month > 12-month moving-average crossover on a momentum index (freefincal 2022) — OVERLAY
- Setup: Nifty Midcap150 Momentum 50 index with a 6m-MA vs 12m-MA crossover, 50/50 equity/debt split (debt at 6% post-tax), about 0.4 switches per year. Result: worked "quite well" over 5 years but often with a higher maximum drawdown than a systematic-investment benchmark and failed around sharp moves such as March 2020; no t-stat. — [freefincal](https://freefincal.com/momentum-index-fund-will-tactical-entry-exit-give-better-results/) [S]
- Cost-clear: yes on cost alone (about 0.4 switches/yr); the evidence is that it does not reliably cut drawdown, which is the only reason to use it.
- Overlap: same closed bucket as B1.

#### B3. Dual momentum across NIFTYBEES / GOLDBEES / liquid (Antonacci) — DISTINCT SIGNAL (allocation, not stock selection)
- Cite: Antonacci, Global Equities Momentum (GEM), 1974-2013 (monthly, US/global equities vs bonds), figures as reported by CXO from the book: 17.43%/yr (about 1.45%/month, my arithmetic), SD 12.64%, Sharpe 0.87, max drawdown 22.7%, gross; benchmark figures conflict across sources (ACWI 9.55%/yr per CXO; 8.85% with a 60.21% max drawdown per Quant-Investing; a Scribd summary gives 45.7% and Sharpe 0.22). — [CXO](https://cxoadvisory.com/momentum-investing/a-few-notes-on-dual-momentum-investing) [S]
- India (unverified, forum/blog): quarterly 3-month-lookback NIFTYBEES vs GOLDBEES, 14 years: 16.06% CAGR / -23.51% max drawdown vs NIFTYBEES 11.93% / -55.15% and GOLDBEES 11.43% / -24.38% (the poster ran the backtest with ChatGPT, not independently verified) — [tradingqna thread](https://tradingqna.com/t/dual-momentum-strategy-with-niftybees-goldbees/174470); a Substack index-level test 2014-2024 reports 18.79% CAGR / -11.42% vs Nifty 12.13% / -34.00% and gold 10.86% / -21.44% (index, not ETFs; post URL not captured) [S]. A separate post tests 42 lookback combinations over 2000-2025 but shows setup only and appears to contain a label-shift bug in its random forest, so no number is usable — [quantindia Substack](https://quantindia.substack.com/p/momentum-in-the-indian-market).
- Conflict / caution: the Indian numbers are gross CAGRs of a chosen lookback, with no costs and multiple-testing across lookbacks; the comparison gold-vs-equity period 2014-2024 favoured gold late in the sample (inference).
- Cost-clear: if the book is rotated S times a year the cost is up to S x 37.5 bp (my arithmetic; STT may not apply to gold/liquid ETFs, not verified). Low cost, but the alpha is an allocation effect, not excess over the stock book.
- Data: NIFTYBEES/GOLDBEES/liquid ETF daily prices.
- Overlap: "dual momentum NIFTYBEES/GOLDBEES/liquid: Leave (allocation, not excess); runnable at Rs 5,500" and "static Nifty-gold mix: Leave"; gold/debt dual momentum is also a section 4 priority — [00-already-covered.md](00-already-covered.md).

#### B4. Constant-volatility scaling of momentum (Barroso and Santa-Clara 2015) — OVERLAY
- Cite: Barroso and Santa-Clara (2015), "Momentum has its moments", Journal of Financial Economics, DOI 10.1016/j.jfineco.2014.11.010 — [CXO summary](https://www.cxoadvisory.com/momentum-investing/avoiding-momentum-strategy-crashes/) [S].
- Effect (US 1926-2011, long-short, gross, 12% volatility target on 6-month daily realised volatility): Sharpe 0.53 -> 0.97; worst monthly loss -80.0% -> -28.4%; worst annual drawdown -97.0% -> -45.2%; abnormal return 1.75%/month. Turnover described as virtually unchanged (not quantified).
- Replication outside the US: Hanauer and Windmueller compare idiosyncratic momentum, constant-vol and dynamic scaling in the US 1930-2017 and 48 markets 1991-2017: scaling roughly doubles the Sharpe ratio and t-stat in the US; scaling raises turnover but the strategies have higher break-even cost — [Quantpedia](https://quantpedia.com/three-methods-to-fix-momentum-crashes/) [S].
- India: none found. Delivery constraint (my inference): the 12% target in calm periods requires leverage; a cash delivery book can only cut exposure toward a liquid ETF, which is the de-risk-only form the profitability sweep already considered.
- Cost-clear: if average monthly exposure change is 10-20% of the book, cost is about 3.75-7.5 bp/month (45-90 bp/yr, my arithmetic); benefit is in drawdown not in mean return, so the correct test is drawdown/Sharpe on the project's own panel, not the excess-return t-stat.
- Overlap: entry-timing sweep Part B: vol-scaled momentum is labelled "Trial 1" (no trial row exists in trials.md); profitability sweep: "conditional volatility overlay de-risk only: Leave unless the owner wants a drawdown trial" — [00-already-covered.md](00-already-covered.md).

#### B5. Volatility-managed portfolios (Moreira and Muir 2017) — OVERLAY
- Cite: Moreira and Muir (2017), Journal of Finance 72(4):1611-1644 — [NBER w22208](https://www.nber.org/papers/w22208.pdf), [CXO](https://cxoadvisory.com/volatility-effects/varying-risk-inversely-with-recentexpected-volatility) [S].
- Effect (gross, mostly long-short factors, US plus international indices): Sharpe up 50-100% across factors; momentum gross annualised alpha 12.5% (about 1.0%/month, my arithmetic; from the CXO summary, not the paper); market alpha 4.9%/yr, appraisal ratio 0.33, Sharpe +25%. The abstract says it survives transaction costs and works for most international indices, but a reviewer notes shorting and costs, especially for momentum, are not fully reflected.
- India: none found. Data: daily prices (realised variance), held.
- Cost-clear / overlap: same as B4 (same family, monthly rescaling by prior-month variance).

#### B6. Dynamic momentum / bear-market-rebound forecast (Daniel and Moskowitz 2016) — OVERLAY (state-dependent weight)
- Cite: Daniel and Moskowitz (2016), "Momentum crashes", Journal of Financial Economics — [NBER w20439](https://www.nber.org/papers/w20439), [PDF read in full](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf) [P].
- Effect (long-short, gross): dynamic weighting "approximately doubles the alpha and Sharpe ratio" of static momentum; in most markets the dynamic Sharpe is about double the static one; applied across all markets and asset classes the dynamic strategy delivers an annualised Sharpe of 1.18, four times the static US equity momentum Sharpe over the same period; Japan, where static momentum failed, goes from Sharpe 0.07 to 0.42; dynamic does not deliver a significant Sharpe for fixed income. For the US sample the text gives a WML Sharpe of 0.71 (market 0.40, WML beta -0.58) while a decile table extraction shows a lower WML-type Sharpe near 0.60; the paper's own numbers were not reconciled here. A master's-thesis figure of "1.19" circulating in secondary material is NOT from this paper.
- Mechanism: crashes occur in "panic" states, after market declines and in high volatility, when losers rebound — a long-short phenomenon; a long-only top-15 book is not short the rebounding losers, but momentum indices still fell hard (see section c).
- India: not tested in any source found. Data: daily prices and index levels, held.
- Cost-clear / overlap: weight changes are monthly like B4; the second arm of "Trial 1" in the entry-timing sweep ("market-state/dynamic crash protection") is this idea; unrun — [00-already-covered.md](00-already-covered.md).

#### B7. Idiosyncratic-momentum and scaled momentum comparison (Hanauer and Windmueller) — mixed: ANOTHER MOMENTUM RANKING (idiosyncratic) + OVERLAY (scaling)
- Already given above (B4): idiosyncratic momentum best reduces maximum drawdown; constant-vol and dynamic scaling roughly double Sharpe and t-stat in the US; 48 markets 1991-2017 — [Quantpedia](https://quantpedia.com/three-methods-to-fix-momentum-crashes/) [S]. Tag the idiosyncratic leg as A2 for trial counting.

#### B8. Momentum stop-loss (Han, Zhou and Zhu) — OVERLAY
- Cite: Han, Zhou and Zhu, "Taming momentum crashes: a simple stop-loss strategy" — [CXO](https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/) [S].
- Effect (US 1926-2013, long-short, gross): 10% stop; equal-weighted worst monthly loss -49.79% -> -11.36%, value-weighted -64.97% -> -23.28%; Sharpe ratios more than double. Earlier version (data to 2011) -11.34% / -23.69%.
- Replication: Alpha Architect found the long-only plain portfolio had better CAGR and Sharpe; the 5% and 10% stop-loss portfolios had lower drawdown and higher Sortino with more trading and expense — [Alpha Architect](https://alphaarchitect.com/2016/08/taming-the-momentum-roller-coaster-fact-or-fiction/) [S]. CXO flags data-snooping in lookback/threshold choice and that trading frictions for stocks in stop conditions may be extraordinarily high because of illiquidity.
- India: none found. Cost-clear: each stop-out is a half round trip plus re-entry at the next rebalance; frequency not given. For a long-only delivery book the long-only replication (worse CAGR and Sharpe, better Sortino) is the relevant one, not the headline.
- Overlap: not listed as tested; stop rules on individual names appear in the intraday work only — [00-already-covered.md](00-already-covered.md).

#### B9. Momentum turning points: slow-fast signal disagreement (Goulding, Harvey and Mazzoleni 2023) — OVERLAY (market-state)
- Cite: Goulding, Harvey and Mazzoleni, "Momentum turning points", Journal of Financial Economics 149(3):378-406, DOI 10.1016/j.jfineco.2023.05.007 — [CXO](https://www.cxoadvisory.com/technical-trading/mitigating-impact-of-price-turning-points-on-trend-following/), [IBKR Quant](https://www.interactivebrokers.com/campus/ibkr-quant-news/trend-following-and-momentum-turning-points/) [S].
- Finding: time-series momentum is prone to losses at and after turning points; when slow and fast signals disagree the market is more likely at a turning point; intermediate-speed blends of slow and fast signals earn positive unconditional alpha. No Sharpe or drawdown figures retrieved (gap). The paper works on equity market cycles (Bull, Correction, Bear, Rebound), i.e. an index-level state, not a stock ranking.
- India: none. Data: index levels. Cost-clear: signal flips rarely (as B1); cost not binding; evidence is thin.
- Overlap: nearest closed items are the market-state arm of "Trial 1" and the bear-market filter "Leave" — [00-already-covered.md](00-already-covered.md).

#### B10. Comomentum as a crowding / reversal warning (Lou and Polk 2022) — OVERLAY (state variable)
- Cite: Lou and Polk (2022), "Comomentum: inferring arbitrage activity from return correlations", Review of Financial Studies 35(7):3272-3302, DOI 10.1093/rfs/hhab117 — [LSE PDF](https://personal.lse.ac.uk/polk/research/hhab117.pdf), [LSE Research Online](https://researchonline.lse.ac.uk/id/eprint/119033) [P abstract].
- Finding: comomentum is the high-frequency abnormal return correlation among stocks a momentum strategy would trade; low comomentum -> momentum profitable and stabilising; high comomentum -> momentum stocks strongly revert (crowded overreaction); Polk says the measure rose sharply before the March 2014 US momentum crash [S]. Effect size per month not retrieved (gap). India: none found.
- Data: daily returns for the winner and loser deciles plus a factor model to form abnormal returns — computable from daily bhav (held) and the IIMA factor library.
- Cost-clear: signal is a regime switch (cost like B1); unknown benefit; crowding in India's top-200 is unmeasured.

#### B11. Rank bands / buy-hold spread to cut turnover (Novy-Marx and Velikov 2016) — OVERLAY (cost-side)
- Cite: Novy-Marx and Velikov (2016), "A taxonomy of anomalies and their trading costs", Review of Financial Studies — [NBER w20721](https://www.nber.org/papers/w20721.pdf) [S via digest; PDF fetched but not read in full].
- Findings: most anomalies with one-sided monthly turnover below 50% stay significant net of costs only when designed to mitigate costs; few high-turnover strategies do; the buy/hold spread (stricter to enter than to retain) is the standout single mitigation; rule of thumb that costs reduce a value-weighted long-short by about 1% of monthly one-sided turnover (a 20% monthly turnover loses at least 20 bp/month); a blog reading says momentum costs about 48.4 bp/month vs 5.5-5.7 bp for size and value in 1963-2013 (unverified, check paper tables). — [Alpha Architect summary](https://alphaarchitect.com/2017/05/trading-costs-destroy-factor-investing/)
- Related: Frazzini, Israel and Moskowitz find institutional trading costs less than one tenth of academic assumptions; AQR "Fact, Fiction and Momentum": gross large-cap momentum 4.5%/yr vs small-cap 8.1%/yr (1991-2013, blog summary); momentum is tax-friendly because it holds winners and sells losers. — [CXO](https://www.cxoadvisory.com/value-premium/mocking-momentum-myths) [S]
- Arithmetic for this book (mine): at 37.5 bp round trip, replacing 20% of the book each month costs 7.5 bp/month; a band that cuts name churn from, say, 40% to 25% saves about 5.6 bp/month (about 67 bp/yr); the saving must exceed any alpha lost by holding stale ranks, which is unmeasured for this panel.
- India: none found. Data: existing rank history.
- Overlap: profitability sweep "tax-aware hold rule: pre-register once the owner fixes the rule"; trials 126/127 touched weighting; rank bands as such not listed as tested — [00-already-covered.md](00-already-covered.md).

#### B12. Slower rebalance (semi-annual, as in NSE index design) — OVERLAY (cadence)
- NSE factor indices rebalance semi-annually (June/December; Nifty200 Momentum 30 uses 6- and 12-month volatility-adjusted returns, weight cap min(5%, free-float cap x score)); freefincal's illiquidity study rebalances annually. No Indian head-to-head of monthly vs semi-annual turnover and net return was retrieved. — [Tata MF explainer on Midcap150 Momentum 50 selection](https://www.tatamutualfund.com/blogs/nifty-midcap150-momentum-50-index-how-stocks-are-selected-and-rebalanced), [freefincal Nifty200 Momentum 30 intro](https://freefincal.com/nifty200-momentum-30-index-a-new-strategy-index-from-the-nse/) [S]
- Cost-clear: halving rebalance frequency roughly halves churn (inference); signal staleness cost unknown. Singh-Walia's holding-period table suggests the pre-cost spread falls with longer holds (1-month 1.954%/month vs 6-month 1.367%, 12-month 1.038% on the CS leg) while the Sharpe falls from 0.689 to 0.153 — so slower rebalancing gave up pre-cost return in India's 2002-2019 sample — [Singh and Walia](https://apcz.umk.pl/CJFA/article/view/CJFA.2020.018) [P].
- Overlap: "rebalance date/tranching: no trial (forward shadow only)" — [00-already-covered.md](00-already-covered.md).

#### B13. Low-volatility / quality filter on the momentum book (section 4 priority, non-inferiority rule) — OVERLAY
- No quantitative evidence for the momentum-by-low-vol combination was retrieved in this sweep; the low-risk anomalies researcher covers it. NSE's Alpha 50 is built on 1-year Jensen's alpha rather than raw return (see section c). I record it here only so the catalogue is complete.
- Overlap: "low-vol sleeve and momentum x low-vol: Leave (risk reduction)" in the profitability sweep, and a section 4 priority as a non-inferiority rule — [00-already-covered.md](00-already-covered.md).

### Inferences
- All the headline overlay benefits are risk numbers (worst month, worst drawdown, Sharpe) in long-short US/global samples; the book cannot short or lever, so the transferable part is de-risking only, and the correct acceptance test is drawdown and Sharpe on the project's own panel rather than the excess-return t that the 2.865 bar refers to.
- The Alpha Architect long-only replication (stop-loss lowers CAGR and Sharpe, raises Sortino) and the Indian 200-day EMA result (lower drawdown, lower CAGR) point the same way: protection costs mean return; whether that is worth it depends on the owner's drawdown tolerance, which the sweeps already framed as a "drawdown trial".
- Trend-filter and regime-switch overlays are cheap in transaction costs (a handful of full-book switches a year) but expensive in taxes if they realize gains; B11 is the only overlay whose entire purpose is cost reduction and is untested.

### Gaps
- No Indian test (NSE or BSE, with costs) of vol-scaling, Daniel-Moskowitz, stop-loss, comomentum, turning points or rank bands was found.
- Faber drawdown and Sharpe, Goulding-Harvey-Mazzoleni Sharpe, Lou-Polk monthly effect sizes, and Novy-Marx-Velikov momentum net returns were not retrieved from primary text.
- Barroso-Santa-Clara and Han-Zhou-Zhu figures come from CXO/Alpha Architect summaries, not the papers.
- The original URLs of the Indian blog backtests (200-day EMA, Substack 2014-2024 dual momentum) were not captured; the digest page is cited instead.
- Momo India's 200-day-on-NAV result is behind a paywall.

## (c) India evidence: NSE momentum indices (live vs backfill, drawdowns) and Indian academic papers, including weakness after 2010

### Takeaway
The NSE momentum indices (Nifty200 Momentum 30 live since 25 Aug 2020; Midcap150 Momentum 50 since 16 Aug 2022) are mostly backfilled, were not defensive in 2008 (-67.9% vs Nifty 50 -64.6%), cushioned 2020 (-34.2% vs -39.6%), and fell about 34% from the Sep 2024 peak to Dec 2025 (my arithmetic from secondary index levels). Indian academic evidence supports momentum in the 1990s-2000s but shows it much weaker after 2010 in the one paper that splits the sample (Singh-Walia), and no paper dedicated to post-2015 decay was found.

### Cited Findings

#### C1. Nifty200 Momentum 30 (and the fund/ETF versions) — implementation fallback, not a signal
- Spec: launched 25 Aug 2020, base 1 Apr 2005 = 1000 (so everything before Aug 2020 is a backfill), 30 stocks from the Nifty 200, score from 6- and 12-month volatility-adjusted returns, semi-annual rebalance (June/December), weight capped at min(5%, free-float cap x score). The official factsheet (28 Mar 2025 edition) exists but the PDF could not be read; return and drawdown tables are unread. — [NSE Indices factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Momentum30.pdf), [freefincal intro](https://freefincal.com/nifty200-momentum-30-index-a-new-strategy-index-from-the-nse/) [S]
- Drawdowns from all-time highs (analysis through Feb 2025, so before the 2025 slide): 2008 GFC -67.9% vs Nifty 50 -64.6%; 2020 Covid -34.2% vs -39.6%; 2022-23 correction -14.8% vs -13.2%; later "recent slump" of about -27% over 6 months vs Nifty 50 about -12% in 2025; beat Nifty 200 TRI in 100% of rolling 7- and 10-year windows 2005-2024 (mostly backfilled history). — [Curious Investing Insights](https://curiousinvestinginsights.substack.com/p/momentum-or-mayhem-unpacking-the) [S]
- 2024-26 path from CEIC and Tickertape pages as relayed by a search digest (pages not fetched): all-time high 38,115.25 on 27 Sep 2024; 52-week low 25,133.95 as of 18 Dec 2025 (about -34% from the peak, my arithmetic; the source does not call it the exact trough); 30,718.25 on 4 Sep 2026 (about -19% below the peak, my arithmetic). The digest also notes sources disagree: one says the index followed a steadier path citing an NSE white paper, another says it fell hard after its Sep 2024 peak. — [Dealplexus on momentum funds](https://www.dealplexus.com/blog/momentum-funds-india) [S]
- A Business Standard article on the Dec 2025 index switch ("Nifty200 Momentum 30: a flip of index switch jolts 16k cr across the grid") could not be opened; only the headline was seen, so the size of the flow is unverified. — [Business Standard](https://www.business-standard.com/markets/news/nifty200-momentum30-a-flip-of-index-switch-jolts-16k-cr-across-the-grid-125121400388_1.html)
- Live-since-launch vs backfill: live history is about 6.2 years (Aug 2020-Nov 2026) and covers a bull run (2020-24) plus the 2024-25 slide; the 2008 and 2020 drawdown history before Aug 2020 is NSE back-calculation. Live annualised return since launch was not retrieved (gap).
- Cost-clear: index funds hold the basket and rebalance semi-annually, so the reader's 37.5 bp round trip is replaced by the fund's internal cost and expense ratio (not retrieved). L53 (local after-tax replay) found the book's after-tax CAGR 17.67% vs 17.28% for a Nifty200 Momentum 30 fund — a tie — [00-already-covered.md](00-already-covered.md).
- Overlap: "NSE factor indices: fallback implementation, not a signal" (entry-timing sweep). The reader's own ranking is the same 6/12-month volatility-adjusted score, so the book is a monthly, 15-name, uncapped-equal-weight version of this index (inference).

#### C2. Nifty Midcap150 Momentum 50 — implementation fallback in a different universe
- Launched 16 Aug 2022 (NSE press release), base 1 Apr 2005 = 1000 (backfilled before Aug 2022), 50 stocks from the Nifty Midcap 150, weight blends normalised momentum score and free-float cap, 6- and 12-month volatility-adjusted returns, semi-annual rebalance. Live history is about 4.2 years (Aug 2022-Nov 2026), almost entirely a bull run plus the 2025 slide. NSE's Jan 2023 whitepaper could not be opened. — [NSE press release](https://niftyindices.com/Press_Release/ind_prs16082022.pdf), [factsheet](https://www.niftyindices.com/Factsheet/Factsheet_NiftyMidcap150Momentum50.pdf), [Tata MF explainer](https://www.tatamutualfund.com/blogs/nifty-midcap150-momentum-50-index-how-stocks-are-selected-and-rebalanced) [S]
- Return and drawdown numbers: not retrieved from a reliable source (live pages are time-sensitive and were left out). freefincal's 2022 test of a 6m/12m moving-average crossover on this index (see B2) is the only quantitative claim, and it is a timing test, not a track record. Tata Midcap150 fund review: [freefincal](https://freefincal.com/tata-nifty-midcap-150-momentum-50-index-fund-review/) (not read).
- Overlap: not in the exclusion file as a universe; the project's 200-name universe sits in large/upper-mid; ranks 201-400 were tested (L38 +1.00%/month, t 3.31) — [00-already-covered.md](00-already-covered.md).

#### C3. Nifty500 Momentum 50 and Nifty Alpha 50 — implementation fallback (Alpha 50 is a distinct, alpha-ranked signal)
- Nifty500 Momentum 50: launch date, rules and index factsheet not retrieved. The only number found is a fund-house article (Motilal Oswal AMC, a vendor) reporting that its "Gold + Nifty 500 Momentum 50" strategy had a maximum drawdown of -32.58% against -63.71% for the Nifty 500 itself; the sample window is not given in the digest and the article was not opened, so treat it as a marketing figure, and note the strategy is a gold-plus-momentum blend, not the pure index. - [Motilal Oswal AMC](https://www.motilaloswalmf.com/motilal-oswal-edge/articles/gold-momentum-a-balanced-way-to-navigate-the-markets) [S/vendor]
- Nifty Alpha 50 [S]: selects on the past year's Jensen's alpha (HDFC Sky); about 17.5% CAGR over a decade, compared by the source with a low-volatility index at 12% rather than with Nifty 50; fell 38.3% in about 32 days in the March 2020 crash; Bandhan's Alpha 50 fund shows maximum drawdown 31.0-31.8% (Sep 2024-Feb 2025) and had not recovered its peak as of Aug 2026; MarketCalls warns backtests from today's constituents have survivorship bias. — [Groww digest](https://digest.groww.in/p/what-if-we-compare-the-calmest-stocks), [Arthgyaan, Bandhan fund](https://arthgyaan.com/fund/bandhan-nifty-alpha-50-index-fund-direct-growth/152177), [HDFC Sky](https://hdfcsky.com/news/nifty-alpha-50-sinks-1-01-percent-as-92-percent-stocks-decline), [MarketCalls](https://www.marketcalls.in/?p=64824)
- Overlap: "Alpha 50-style signal: Leave" in the profitability sweep — [00-already-covered.md](00-already-covered.md). As a signal it is another momentum-family ranking (a one-year residual relative to the market; compare A2).

#### Indian academic evidence, ordered by date, with what each says about weakness
- Pre-2010 strength: Sehgal and Balakrishnan (2002), Ansari and Khan (2012, 1995-2006), Sehgal and Jain (2011), IIMA WML (1994-2014, 21.9%/yr) — see section (a) links.
- Weakness / mixed: a 1991-2006 study with no momentum profits or reversals; a thesis with no superior returns; contrarian profits in other samples (as relayed by later papers); Singh and Walia (2020): cross-sectional alpha not significant in 2010-19 (FF3 alpha 0.56%/month, t 0.71, 12-month hold) while it was 2.16%/month (t 3.72) in 2002-07 and the 2008-09 crash cost -1.2 to -1.3%/month — [Singh and Walia](https://apcz.umk.pl/CJFA/article/view/CJFA.2020.018) [P].
- Liquidity conditioning: Chui et al. (2023; BSE, 2000-2021) say the effect is stronger in the most liquid stocks and reverses in the most illiquid ones — [Manipal](https://impressions.manipal.edu/open-access-archive/9369); freefincal (2026) says the opposite for the Nifty200 Momentum 30 constituents — [freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/). Conflict noted in A12.
- A search for a paper documenting a decline in Indian momentum profits over 2016-2023 specifically returned none; the most recent NSE-based momentum paper found is Sehgal, Pandey and Sen (2025), abstract only. — [search digest](https://www.publishingindia.com/archive/jcar/seasonality-in-momentum-profits-evidence-from-the-indian-stock-market)

### Inferences
- The NSE momentum index track record that investors cite is predominantly backfill; the live record spans one bull market and one 30%+ drawdown, so it cannot validate a monthly 15-name version, and it already shows that a momentum tilt did not protect in 2008 or 2025.
- The reader's t 2.51 backtest sits against a literature where the Indian cross-sectional premium shrank after 2010 (Singh-Walia), so a smaller-than-published premium is the base case for new variants.
- Because the live book is a close cousin of Nifty200 Momentum 30, fund-level data (Nifty200 Momentum 30 funds) is a cheap out-of-sample monitor of the strategy family from Aug 2020, which the reader's own panel cannot provide for 2026.

### Gaps
- Official NSE factsheets/whitepapers (Nifty200 Momentum 30, Midcap150 Momentum 50) could not be opened; return-since-inception and index-level drawdown tables were not read.
- Nifty500 Momentum 50 and Alpha 50 official factsheets, launch dates and live-vs-backfill splits were not retrieved.
- Expense ratios and tracking error of the momentum index funds were not retrieved.
- Business Standard (Dec 2025) article unreadable; flow impact of the index switch unverified.
- No refereed Indian paper on post-2015 momentum decay or on costs net of Indian delivery charges was found.

## (d) Post-publication decay and replication status of the variants

### Takeaway
Broad replication studies agree momentum survives but with smaller magnitudes, and they disagree on how many anomalies survive (Hou-Xue-Zhang: most fail at high bars; Jensen-Kelly-Pedersen: most replicate). Variant-level decay is rarely measured; the clearest cases are Novy-Marx's 6-2 signal fading while 12-7 did not, Indian cross-sectional momentum losing significance after 2010, and long-only stop-loss/vol-scaling replications giving lower CAGR than the headline long-short papers.

### Cited Findings
- McLean and Pontiff (2016, Journal of Finance), 97 characteristics: portfolio returns are 26% lower out-of-sample and 58% lower post-publication, i.e. 32 percentage points attributed to publication-informed trading; press coverage of earlier drafts reports about 35% post-publication decay ([MoneySense, via search digest, not opened](https://moneysense.ca/?p=36813)). A momentum-specific post-publication figure was not extracted (gap). — [McLean-Pontiff PDF](https://Www.Gwern.net/doc/economics/2016-mclean.pdf), [alt copy](https://counterpointfunds.com/wp-content/uploads/2017/07/PredictabilityMcleanPontiff.pdf) [P as to the headline numbers; my recollection of the published version cross-checked against two copies]
- Hou, Xue and Zhang (2020, Review of Financial Studies 33(5)): of 452 anomalies, 65% fail the |t| >= 1.96 hurdle and 82% fail |t| >= 2.78 under their value-weighted, NYSE-breakpoint replication; momentum replicates but with much smaller magnitudes; failures are concentrated in microcaps. — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2019-2133..html) [P/S; the 65%/82% figures are as I recorded them from the paper abstract and a digest]
- Jensen, Kelly and Pedersen (2023, Journal of Finance 78(5):2465-2518): most factors replicate, cluster into 13 themes, and work out-of-sample in 93 countries. A claimed "82% replicate" figure could NOT be found in any source I read; an earlier draft reports 63.9% after an adjustment for insignificant raw returns, and a secondary summary reports 85% (CAPM, Bayesian). Treat any single replication-rate number as version-dependent. — [NBER w28432](https://www.nber.org/papers/w28432), [CBS PDF](https://research-api.cbs.dk/ws/portalfiles/portal/95651880/theis_ingerslev_jensen_et_al_is_there_a_replication_crisis_in_finance_publishersversion.pdf)
- Conflict between the two replication papers: HXZ (US, value-weighted, microcap-controlled) finds most anomalies fail; JKP (global, cluster-level, Bayesian) finds most replicate. They answer different questions (individual anomalies at a high hurdle vs themed factors), and momentum is in the surviving group in both. — same sources.
- Novy-Marx intermediate momentum: the predictive power of the 6-2 return faded in recent decades while 12-7 did not, per CXO — a measured within-variant decay, with the Goyal-Wahal "echo" challenge. — [CXO](https://www.cxoadvisory.com/momentum-investing/isolating-the-decisive-momentum-echo/)
- 52-week high: George-Hwang out-of-sample India test 2014-2017 gave Sharpe about 0.4 and total return 17% (described as "not very stellar"), and the index-level international tests find it unprofitable in emerging indices. — [Quantpedia India](https://quantpedia.com/an-analysis-of-52-weeks-high-effect-on-indian-stocks/)
- Indian cross-sectional momentum, same paper across eras (12-month hold FF3 alpha, %/month): 2002-07 2.164 (t 3.72); 2010-19 0.558 (t 0.71). IIMA WML: 21.9%/yr (1994-2014) vs 11.34%/yr (through Mar 2023, snippet only, different release). — [Singh and Walia](https://apcz.umk.pl/CJFA/article/view/CJFA.2020.018), [IIMA](https://iima.ac.in/sites/default/files/rnpfiles/1970004922013-09-05.pdf)
- Overlays: Alpha Architect's replication of the stop-loss paper finds the headline long-short gains shrink to a drawdown/Sortino improvement in a long-only portfolio with higher costs — [Alpha Architect](https://alphaarchitect.com/2016/08/taming-the-momentum-roller-coaster-fact-or-fiction/); Newfound Research found Faber's monthly timing model implicitly trades on the first day of the month and that results on SPY differ across 21 offset trade days, with no costs or slippage modelled — [Newfound](https://blog.thinknewfound.com/2013/08/) [S, via search digest]; Chen-Yu acceleration has acknowledged data-snooping and a weak 1-2 month result — [CXO](https://www.cxoadvisory.com/momentum-investing/acceleration-stock-momentum-strategy/).
- Trading-cost counterpoint: Frazzini, Israel and Moskowitz report institutional costs less than one tenth of those assumed in academic papers; AQR's "Fact, Fiction and Momentum" reports gross large-cap momentum 4.5%/yr vs small-cap 8.1%/yr (1991-2013) — evidence that gross large-cap momentum premiums are a half of small-cap ones, relevant to a top-200 universe. — [CXO](https://www.cxoadvisory.com/value-premium/mocking-momentum-myths) [S]

### Inferences
- For any variant the sensible prior is "published effect minus roughly half (McLean-Pontiff post-publication decline), minus costs, further shrunk by moving from long-short to long-only top-15 and from small/mid to the 200 most-traded names" (my arithmetic on the cited ratios, not a model).
- Because published long-short Sharpe gains from overlays were measured on US samples that include 1932 and 2009, they are driven by a handful of crash months; whether India's 2008 and 2020 months play the same role is untested.

### Gaps
- Momentum-only post-publication decline from McLean-Pontiff and the HXZ momentum t-stats were not extracted.
- JKP "82%" is unverified; the replication-rate numbers differ across versions.
- Variant-level decay (residual momentum, industry momentum, seasonality, acceleration) after publication was not found beyond the items above.

## (e) Catalogue summary: 29 candidates, tag, best evidence, India status, cost verdict

### Takeaway
No candidate has a published net-of-cost India number, and none can be said to clear the t >= 2.865 bar for a new ranking on the evidence found; the plausible tests are a rank-band cost overlay (B11), de-risk-only volatility or trend overlays judged on drawdown, and allocation rules (B3), almost all of which the earlier sweeps already rated "Leave" or "reported-only".

### Cited Findings
Legend. Tag: RANK = another momentum ranking (needs t >= 2.865, N=12); SIGNAL = distinct signal; OVERLAY = overlay on the existing book (judged on paired difference, drawdown, Sharpe, not the family t); ALLOC = allocation rule. Cost verdict at 37.5 bp: YES = cost not binding; MAYBE = depends on turnover not in the files; NO = gross edge in the source is below plausible monthly cost or the evidence is negative; N/A = benefit is risk, not excess return. "Overlap" shorthand: CLOSED = closed in 00-already-covered.md; LEAVE/REJECT/DEFER = the sweep's own label; OPEN = not in the file. Every row's sources are in the section noted.

| ID | Candidate | Tag | Best number found (units as source) | India evidence | Cost verdict | Overlap |
|---|---|---|---|---|---|---|
| A1 | 52-week-high proximity | RANK | Sharpe ~0.4, 17% total, India 2014-17 | Quantpedia only; EM indices unprofitable | MAYBE | LEAVE/Skip |
| A2 | Residual momentum | RANK | 0.76%/month, vol 15.27%, gross, US | none (thesis only for EM) | MAYBE | DEFER/LEAVE |
| A3 | Intermediate 12-7 | RANK | 12-7 Sharpe >2x 6-2, US, gross | none; 6-6 beats 12-12 in India | MAYBE | LEAVE (lookback grids) |
| A4 | Acceleration | RANK | 0.95% vs 0.63%/month, US 1962-2014, gross | none | NO (weak at 1-2 month hold) | OPEN (sibling CLOSED: frog-in-the-pan) |
| A5 | Earnings / fundamental momentum | SIGNAL | India: earnings strategy best long-short, no numbers | Sehgal-Jain 2015 abstract | N/A (data not held) | CLOSED (sec. 84, L39 PEAD NO-GO) |
| A6 | Industry momentum | SIGNAL/RANK | stock momentum less profitable once controlled | Sehgal-Jain 2011 | MAYBE | LEAVE |
| A7 | Sector rotation (NSE sector indices) | SIGNAL | none retrieved | none | MAYBE | LEAVE (sec. 4 priority, low hit rate) |
| A8 | Same-calendar-month seasonality | SIGNAL | ~13%/yr US long-short (~1.1%/month), gross | none | NO (near-full monthly turnover) | OPEN |
| A9 | Relative + absolute "enhanced" momentum | RANK | beats price momentum, no numbers | Sehgal-Pandey-Sen 2025 (NSE) | MAYBE | OPEN (bear filter LEAVE) |
| A10 | Stock-level time-series momentum | SIGNAL | India TS 1.4-2.3%/month raw gross; 2010-19 FF3 1.42%/month t 1.69 | Singh-Walia (BSE 2002-19) | MAYBE | OPEN (L32 intraday only, no clear) |
| A11 | Factor momentum | SIGNAL/ALLOC | none | none | MAYBE | LEAVE (factor indices fallback) |
| A12 | Liquidity-conditioned momentum | RANK | conflicting: liquid stronger vs illiquid stronger | Chui et al. vs freefincal | MAYBE | CLOSED-adjacent (L38) |
| A13 | Physical momentum / daily reversal | SIGNAL | Sharpe 0.38-0.62, no costs | arXiv NSE 500 2014-21 | NO (daily, no costs) | CLOSED (L31) |
| B1 | Index trend filter (Faber / 200-day) | OVERLAY | US 9.8% -> 11.3%; India MDD -20.19% vs -36.34% | blog/forum only | YES | REJECT as lead |
| B2 | 6m>12m MA crossover on momentum index | OVERLAY | worked "quite well", failed Mar 2020 | freefincal 2022 | YES | REJECT/Leave |
| B3 | Dual momentum NIFTYBEES/GOLDBEES/liquid | ALLOC | GEM 17.43%/yr, Sharpe 0.87, MDD 22.7%; India forum 16.06% / -23.51% (unverified) | forum/Substack | YES | LEAVE (sec. 4 priority) |
| B4 | Constant-vol scaling (Barroso-SC) | OVERLAY | Sharpe 0.53 -> 0.97; worst month -80% -> -28% | none | MAYBE (de-risk only) | "Trial 1" never run |
| B5 | Vol-managed (Moreira-Muir) | OVERLAY | momentum alpha 12.5%/yr gross, Sharpe +50-100% | none | MAYBE | as B4 |
| B6 | Dynamic momentum (Daniel-Moskowitz) | OVERLAY | dynamic Sharpe ~2x static; Japan 0.07 -> 0.42 | none | MAYBE | second arm of "Trial 1" |
| B7 | Hanauer-Windmueller scaling / idiosyncratic | OVERLAY/RANK | Sharpe and t about doubled, US 1930-2017 | none | MAYBE | as B4/A2 |
| B8 | Stop-loss (Han-Zhou-Zhu) | OVERLAY | worst month -49.79% -> -11.36%; long-only replication: lower CAGR, higher Sortino | none | MAYBE | OPEN |
| B9 | Turning points (GHM 2023) | OVERLAY | intermediate-speed blend alpha, no numbers | none | YES | OPEN |
| B10 | Comomentum (Lou-Polk) | OVERLAY | high comomentum -> reversal, no numbers | none | YES | OPEN |
| B11 | Rank bands / buy-hold spread | OVERLAY | saves ~5.6 bp/month at 40% -> 25% churn (my arithmetic) | none | YES (that is its job) | OPEN (tax-hold rule pending owner) |
| B12 | Semi-annual cadence | OVERLAY | India CS Sharpe 0.689 (1m hold) -> 0.349 (6m hold) | Singh-Walia | MAYBE | no trial |
| B13 | Low-vol / quality overlay | OVERLAY | none retrieved here | none | N/A | LEAVE (sec. 4 priority) |
| C1 | Nifty200 Momentum 30 fund | implementation | MDD -67.9% (2008), ~-34% Sep24-Dec25 | live since Aug 2020, mostly backfill | N/A (L53 tie) | fallback, not a signal |
| C2 | Midcap150 Momentum 50 fund | implementation | no reliable number | live since Aug 2022 | N/A | not in file |
| C3 | Nifty500 Momentum 50 / Alpha 50 | implementation / RANK | Alpha 50 ~17.5% CAGR, -38.3% in 32 days (2020) | thin | N/A | LEAVE |

### Inferences
- If the reader wants to spend trials, the order the evidence supports is: (1) B11 rank bands, because it is the only cost-side lever and cuts per-name round trips of ~37.5 bp; (2) de-risk-only drawdown overlays (B4/B6, optionally B1) as reported-only arms, because published drawdown cuts are large and Indian momentum indices drew down 34-68%; (3) B3 as an allocation question, not an alpha claim. All three were previously rated "Leave" or "reported-only" in the sweeps, so this is a question of whether the owner wants a drawdown trial, not a new edge.
- Ranking variants (A1-A4, A9, A12) are the least promising uses of trial budget: they are correlated with the base, none has an Indian net-of-cost test, and each costs one step up the t-bar ladder (N=12 -> 2.865, next 2.891).
- A8 and A13 are rejected on cost grounds before any test (gross effect near or below the monthly cost of near-full turnover).

### Gaps
- Turnover of the live book, per-candidate incremental turnover, and Indian after-tax effects are not measured in any source; all cost verdicts rest on my arithmetic at the 37.5 bp mid-point.
- Section 4 items outside this scope (turn-of-month, buyback/promoter buys) are covered by other researchers and are not in this catalogue.
- The 2026 held-out window in the project data is unread by this research; I did not look at any project data (no code or data access beyond the exclusion file).
