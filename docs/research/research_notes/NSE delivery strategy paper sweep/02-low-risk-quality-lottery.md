# Low-risk, quality and lottery anomalies: evidence, Indian record, and feasibility for an NSE delivery account

Scope and conventions (read first). Written 2026-11-01. Target: long-only NSE cash-equity delivery, weekly-to-quarterly holding, monthly/quarterly rebalance, daily price + volume + corporate actions back to about 2010, NO fundamentals database. Evidence tags: [P] = I opened the primary paper or NSE document this session and read the number; [S] = search-result snippet or secondary summary (treat as unverified); [C] = my own arithmetic from sourced numbers; anything I could not source is under Gaps and is NOT stated as fact. Cost convention: round trip (RT) = 22 bp charges + ~10 bp slippage + DP Rs 15.34 per sell, so RT(bp) = 32 + 15.34 / position_in_rupees x 10,000 [C]. That is about 40 bp at Rs 20,000 per name, 47 bp at Rs 10,000, 55 bp at Rs 6,667. Cost drag per month = one-way annual turnover x RT / 12 [C]: at 50% / 100% / 200% turnover and 40 bp RT that is 1.7 / 3.3 / 6.7 bp per month; at 60 bp RT (small account) it is 2.5 / 5.0 / 10 bp per month. Effect sizes are converted to %/month (annual / 12). Family bar for any new momentum-family trial in this repo: t >= 2.865 (00-already-covered.md lines 150-151). Everything below that overlaps a closed item in 00-already-covered.md says so in its row.

## Low volatility, low beta, idiosyncratic volatility and the defensive-equity critique

### Takeaway
The low-risk anomaly is real in long histories (US 1968-2008, 19 of 20 developed countries for BAB) but (a) most of the long-short return sits on the short side, which a delivery account cannot take, (b) the long-only version has a weak information ratio (0.08-0.17 vs 0.51 value / 0.64 momentum in the US), (c) it is largely explained by size, profitability and value tilts, and (d) a clean value-weighted, NYSE-breakpoint replication finds the volatility and IVOL spreads insignificant. In India the live NSE record of the Nifty100 Low Volatility 30 is a modest edge over Nifty 50 (about +1.1 pt/yr 2017-2024) and a loss to Nifty 500, after a large backfilled edge (+5.0 pt/yr 2006-2015).

### Cited Findings
- Baker-Bradley-Wurgler (FAJ 2011), US top-1,000 stocks Jan 1968-Dec 2008, quintiles on 5-year trailing volatility or beta: $1 in the lowest-volatility quintile grew to $59.55 (about $10.12 in real terms) while $1 in the highest-volatility quintile fell to 58 cents (under 10 cents real), before transaction costs [P] — [Baker, Bradley, Wurgler](https://pages.stern.nyu.edu/~jwurgler/papers/faj-benchmarks.pdf)
- Same paper: the information ratio of a simple long-only low-volatility strategy is "unappealing at 0.08 to 0.17" vs 0.51 for a long-only top-quintile value strategy and 0.64 for a long-only top-quintile momentum strategy over 1968-2008; the authors' explanation is that fixed-benchmark, no-leverage institutional mandates do not exploit it [P] — [Baker, Bradley, Wurgler](https://pages.stern.nyu.edu/~jwurgler/papers/faj-benchmarks.pdf)
- Frazzini-Pedersen BAB (draft May 2013, later JFE 2014): US BAB factor Sharpe 0.78 for 1926-March 2012 (about twice value, 40% above momentum); US BAB alpha 0.73%/mo (t 7.39) vs the three-factor model, 0.55%/mo (t 5.59) after adding momentum, 0.55%/mo (t 4.09) with a liquidity factor; international pooled alpha 0.28-0.64%/mo (t 2.09-4.81); positive Sharpe in 18 of 19 developed markets, positive 4-factor alpha in 13 of 19, significant in 6 [P] — [Frazzini, Pedersen](https://pages.stern.nyu.edu/~lpederse/papers/BettingAgainstBeta.pdf)
- Novy-Marx-Velikov, "Betting against betting against beta" (data Jan 1968-Dec 2017): BAB turnover is 214.7% per year with $1.33 round-trip trading on the long side and $0.82 on the short side; two thirds of the trading is in the smallest NYSE decile; transaction cost averages 60 bp/month (26 bp/month over the last ten years of the sample); net average return 48 bp/month (t 3.30) so costs remove "more than 55%" of gross (implied gross about 108 bp/month = 48 + 60 [C]); generalized alpha vs the Fama-French 5-factor model only 16 bp/month, t 1.20 [P] — [Novy-Marx, Velikov](https://mysimon.rochester.edu/novy-marx/research/BABAB.pdf)
- Same paper: value-weighted BAB earns 56 bp/month (t 3.48) with Sharpe 0.49 vs 1.08 for the equal-weighted version, loads 0.45 on RMW and 0.50 on CMA, 5-factor alpha 24 bp/month (t 1.63, insignificant); an "implementable" rank- and cap-weighted BAB costs 8 bp/month to trade and nets 43 bp/month (t 2.75) [P] — [Novy-Marx, Velikov](https://mysimon.rochester.edu/novy-marx/research/BABAB.pdf)
- Novy-Marx, "Understanding defensive equity" (NBER WP 20591, Oct 2014): high-volatility / high-beta stocks tilt to small, unprofitable, growth firms; controlling for size, profitability and relative valuation explains defensive-strategy performance, while the reverse is false (value and profitability cannot be explained by defensive equity) [P] — [Novy-Marx](https://www.nber.org/system/files/working_papers/w20591/w20591.pdf)
- Hou-Xue-Zhang replication (447 anomalies, Jan 1967-Dec 2014, NYSE breakpoints, value-weighted): idiosyncratic volatility (3-factor residual) high-minus-low earns -0.51%, -0.33%, -0.18%/mo at 1, 6, 12-month horizons (t = -1.62, -1.11, -0.62) and total volatility earns -0.40%, -0.25%, -0.20%/mo (t = -1.16, -0.77, -0.62); the abstract lists Ang-Hodrick-Xing-Zhang idiosyncratic, total and systematic volatility among results that do not survive [P] — [Hou, Xue, Zhang](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf)
- Quantpedia's summary of Blitz-van Vliet (2007) gives a 12%/yr (about 1.0%/mo) alpha spread between lowest and highest volatility deciles for 1986-2006 and a long-short Sharpe of 0.72 [S] — [Quantpedia low-volatility](https://quantpedia.com/strategies/low-volatility-factor-effect-in-stocks); decomposition and long-only caveats at [Quantpedia deconstructing](https://quantpedia.com/deconstructing-the-low-volatility-anomaly/)
- Emerging markets: Blitz-Pang-van Vliet (Robeco, 2012/13) long-short volatility portfolio beat the EM index by 8.8%/yr (about 0.73%/mo), mostly from the short (high-vol) side; beta spread 5.4%/yr; 3.1%/yr in 1989-1999 and 14.4%/yr in 2000-2010; 15 of 19 countries showed at least 5%/yr; gross of costs and some stocks cannot be shorted. Secondary summary only (the Robeco PDF came back as HTML) [S] — [CXO Advisory](https://www.cxoadvisory.com/?p=20977)
- Hanauer-Lauterbach (Emerging Markets Review): 28 emerging markets, about 21 years, micro stocks excluded, no positive cross-sectional risk-return link; cash-flow-to-price, gross profitability, composite equity issuance and momentum pervasive, ROE/ROA/size no clear relationship; India not broken out [S] — [Quantpedia pointer](https://quantpedia.com/?p=28261)
- NSE Nifty100 Low Volatility 30: top 30 of Nifty 100 by lowest 1-year standard deviation of daily log returns, quarterly review, a holding is retained while its rank is within 60, volatility-based (inverse) weights with caps; launched 8 Jul 2016, base 1 Apr 2005 = 1000 (so 2005-2016 is backfilled) [P] — [Methodology](https://archives.nseindia.com/content/indices/Method_Nifty100_Low_Volatility_30.pdf), [Factsheet](https://www.niftyindices.com/Factsheet/Nifty100_LowVolatility30.pdf)
- Mirae Nifty100 LowVol30 note, total-return calendar years (NSE data to 31 Dec 2024): LV30 vs Nifty 50 vs Nifty 500: 2017 30.3/30.3/55.7, 2018 7.4/4.6/-12.6, 2019 5.2/13.5/0.6, 2020 24.3/16.1/25.6, 2021 24.2/25.6/48.2, 2022 2.0/5.7/3.9, 2023 31.9/21.3/26.9, 2024 12.4/10.1/16.2 [P] — [Mirae note](https://www.miraeassetmf.co.in/docs/default-source/product-guides/note---low-volatility-strategy-jan-2025.pdf). My compounding of that table [C]: 2006-2015 (backfilled) LV30 17.2% CAGR vs Nifty 50 12.2% vs Nifty 500 13.9%; 2017-2024 (live, full calendar years) LV30 16.7% vs Nifty 50 15.6% vs Nifty 500 18.6%; 2020-2024 LV30 18.5% vs 15.5% vs 23.3%. LV30 beat Nifty 50 in 4 of 8 live years (2018, 2020, 2023, 2024), tied 2017, lost 2019 (-8.3 pt), 2021, 2022; it lost to Nifty 500 in 5 of 8.
- NSE Index Dashboard, total return, 30 Sep 2026: Nifty100 LV30 1Y -4.68%, 3Y 8.99%, 5Y 8.12%, 1Y volatility 12.18%, beta 0.87 vs Nifty 50 1Y -7.09%, 3Y 6.06%, 5Y 6.38%; Nifty500 Low Volatility 50 5Y 11.51% (beta 0.79); Nifty Low Volatility 50 5Y 8.30% [P] — [NSE dashboard](https://niftyindices.com/Index_Dashboard/Index_Dashboard_SEP2026.pdf)
- Robustness against a community backtest: a QuantConnect MAX/low-risk style test with VIX leverage scaling reports Sharpe 0.57 since 1998 vs 0.335 for SPY (community code, not peer-reviewed) [S] — [QuantConnect](https://www.quantconnect.com/research/20886/the-max-effect-with-vix-based-leverage-scaling/)

### Inferences
- A long-only delivery version cannot harvest the short leg that carries the BAB/volatility premia; what remains is "avoid the worst decile" plus lower beta. The honest long-only edge is the NSE live record: roughly +9 bp/month vs Nifty 50 in 2017-2024 [C], with a lower beta (0.87) and lower volatility (12.2% vs 13.5%), not alpha over a broad index.
- Because defensive performance is explained by profitability, size and value tilts (Novy-Marx), a low-volatility screen added on top of a momentum book is probably a cheap proxy for "exclude junk" and should be tested as a gate, not as an independent return source.
- Backfill flatters: LV30's +5.0 pt/yr (about 41 bp/month [C]) 2006-2015 advantage includes 2008 (-42.3% vs -51.3% for Nifty 50) and is NSE-computed after the fact; the live era delivered about a fifth of that.

### Gaps
- AHXZ (2006, JF), Blitz-van Vliet (2007, JPM) and Robeco's conservative-formula papers were not retrieved; the numbers above for them come through Hou-Xue-Zhang or Quantpedia only.
- Indian turnover of the NSE low-vol and quality indices is not in the factsheets/methodologies I read; I cannot quantify index turnover or a net-of-cost version. 2025-2026 calendar-year returns for LV30 are not in my sources (only YTD -10.24% total return to 30 Sep 2026 and the dashboard windows).
- India-specific IVOL and BAB studies (AFL 2016, a 2019 study showing a 25.53%/yr low-minus-high-volatility alpha spread over Jan 2000-Sep 2018, MSE WP 215 by Saraf and Kayal for 2010-2020, a 2021 leverage-constraint paper) are known only from search snippets (see the India section); I did not open them.

## Lottery and skewness (MAX, expected idiosyncratic skewness, MIN)

### Takeaway
The MAX effect is large in the original sample (-1.03%/mo value-weighted, 1962-2005) but the entire effect sits in the top three MAX deciles (a short-side or "avoid" effect), a clean replication finds it insignificant, and the only Indian test I found reports no lottery overpricing. For a long-only delivery account this is at best an exclusion screen, not a return source.

### Cited Findings
- Bali-Cakici-Whitelaw, "Maxing out" (NBER WP 14804; JFE 2011), all NYSE/AMEX/NASDAQ stocks, July 1962-Dec 2005, deciles on the prior month's maximum daily return: value-weighted decile 10 minus decile 1 raw return -1.03%/mo (Newey-West t -2.83), four-factor alpha -1.18%/mo (t -4.71); equal-weighted -0.65%/mo (t -1.83), alpha -0.66%/mo (t -2.31); after size control -1.22%/mo (t -4.49), alpha -1.19%/mo (t -5.98) [P] — [Bali, Cakici, Whitelaw](https://www.nber.org/papers/w14804.pdf)
- Same paper, the long-only reading: value-weighted average returns of deciles 1 to 7 are all about 1.00-1.16%/mo; deciles 8, 9, 10 drop to 0.86%, 0.52%, -0.02%/mo, with average maximum daily returns of 9%, 12%, 24% in those deciles [P] — [Bali, Cakici, Whitelaw](https://www.nber.org/papers/w14804.pdf)
- Hou-Xue-Zhang replication: the maximum-daily-return high-minus-low decile earns -0.34%, -0.17%, -0.07%/mo (t = -1.14, -0.62, -0.24) at 1, 6, 12 months, "much lower" than -1.03% (t = -2.83); the abstract lists Bali-Cakici-Whitelaw MAX among the insignificant results [P] — [Hou, Xue, Zhang](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf)
- Same replication, skewness: high-minus-low deciles on realized total skewness, idiosyncratic skewness (3-factor) and idiosyncratic skewness (q-factor) earn +0.23%, +0.34%, +0.27%/mo (t = 2.11, 3.50, 2.88) at 1 month, with q-factor alphas about 0.31%/mo (t 2.64-3.01). The sign is positive: high realized skewness did not underperform in that test, which is the opposite of the lottery-overpricing story [P] — [Hou, Xue, Zhang](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf)
- Gorman et al.: the MAX result "could be overreaction, not lottery seeking" [S] — [Gorman et al.](https://cfr.ivo-welch.info/published/papers/gorman2021could.pdf); a Handbook paper finds MAX is concentrated in stocks with the worst past returns and weak among the best past performers [S] — [IDEAS record](https://ideas.repec.org/a/taf/hbhfxx/v23y2022i3p338-352.html)
- India: Sharma and Chakraborty, "Investing in lottery-like stocks in India" (Studies in Economics and Finance), conclude Indian investors do not overpay for lottery stocks, link this to India's social/regulatory setting, and suggest a long-high-MAX / short-low-MAX strategy could be profitable (sign opposite to the US) — I saw the abstract only [S] — [Sharma, Chakraborty](https://www.doi.org/10.1108/SEF-04-2018-0099)
- India: a 1999-2014 Indian study finds a "MIN effect" (higher monthly minimum return predicts higher next-month return), concentrated in small-cap, illiquid stocks with low institutional holdings [S] — [IDEAS record](https://ideas.repec.org/a/bor/bistre/v18y2018i1p76-90.html); a 2021 Emerging Markets Finance and Trade paper reports that higher volatility amplifies lottery preference and that the leverage-constraint explanation dominates the low-risk effect in India [S] — [IDEAS record](https://ideas.repec.org/a/sae/emffin/v20y2021i2p192-217.html)

### Inferences
- Long-only MAX is an avoid-the-top-3-deciles filter. The saving is about 0.14% to 1.0%/mo on the excluded names relative to deciles 1-7 [C from the decile averages above], which on a portfolio that holds none of them is realized only as "not losing", and the replication says even that is noise in value-weighted NYSE-breakpoint tests.
- India points the wrong way for a MAX avoidance rule (no overpricing found, possibly a positive MAX premium), so a MAX screen needs its own Indian test before it is used as a momentum-book filter; price-only data suffices to run it.

### Gaps
- Boyer-Mitton-Vorkink (2010, RFS) expected idiosyncratic skewness: not retrieved; no number or India test found. Realized-skewness numbers above are Hou-Xue-Zhang's, which are not the same object.
- Sharma-Chakraborty and MIN-effect effect sizes (bp per month, sample, t-stats) are not in the abstracts; full texts not opened.
- No post-2010 US or India out-of-sample MAX study retrieved beyond the community backtest cited in the previous section.

## Quality and accounting anomalies (gross profitability, QMJ, RMW/CMA, accruals, asset growth, issuance, F-score, G-score)

### Takeaway
Profitability/quality is the most robust family: gross profitability and QMJ survive in long samples and internationally, and quality also explains why low-vol works. Replication is mixed: gross profitability and F-score survive, accruals and asset growth are weaker in modern value-weighted tests, and the Indian evidence is a single strong QMJ paper built on paid CMIE Prowess data. Price-only proxies for quality are not established; the nearest is low volatility/beta.

### Cited Findings
- Novy-Marx, "The other side of value: the gross profitability premium" (JFE 2013), Compustat, July 1963-Dec 2010: gross profits-to-assets (revenue minus COGS over total assets) earns a most-minus-least profitable spread of 0.31%/mo (t 2.49) despite being a growth strategy (Spearman correlation with book-to-market -18%); a mixed profitability/value strategy has t 5.87 and Sharpe 0.85 vs 0.34 for the market over the sample; profitability and value correlation -0.57 [P] — [Novy-Marx](https://mysimon.rochester.edu/novy-marx/research/QDoVI.pdf) (the copy I read: [OSoV working paper](https://www.johnhcochrane.com/s/Novy_marx_OSoV.pdf))
- Hou-Xue-Zhang replication on the same signal: gross profits-to-assets (current assets) high-minus-low 0.38%/mo (t 2.62), but scaling by LAGGED assets gives only 0.16%/mo (t 1.04): a lag-convention sensitivity worth pre-registering [P] — [Hou, Xue, Zhang](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf)
- Asness-Frazzini-Pedersen, "Quality minus junk" (draft Oct 2013): quality = profitable, growing, safe, high-payout; US long sample 1956-2012 and 24 developed countries 1986-2012; highest minus lowest quality decile 47-68 bp/mo raw (t 2.80-3.22); QMJ factor 1-, 3-, 4-factor alphas 55, 68, 66 bp/mo in the US (t 7.27, 11.10, 11.20) and 52, 61, 45 bp/mo globally (t 5.75, 7.68, 5.50); positive returns in 23 of 24 countries; including quality revives the size effect (SMB alpha 13 bp -> 64 bp, t 6.39) [P] — [AFP working paper](https://conference.nber.org/conf_papers/f69835.pdf)
- Hou-Xue-Zhang replication, investment/accrual/issuance family (Jan 1967-Dec 2014): asset growth (investment-to-assets) high-minus-low -0.46%/mo (t -2.92) vs -1.05% (t -5.04) value-weighted and -1.73% (t -8.45) equal-weighted in Cooper-Gulen-Schill (2008); operating accruals (Sloan 1996) -0.27%/mo (t -2.13) vs -10.4%/yr (t -4.71) in Sloan, with a q-factor alpha of -0.54% (t -3.77), i.e. NOT explained by the q-model; Richardson et al. total accruals -0.23%/mo (t -1.63); composite equity issuance -0.56%/mo (t -3.16), q-alpha -0.24% (t -1.85); accruals quality -0.07%/mo [P] — [Hou, Xue, Zhang](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf)
- Same replication, F-score: quarterly Piotroski F-score high-minus-low earns 0.58%, 0.53%, 0.42%/mo at 1, 6, 12 months (t 2.47, 2.52, 2.22) but q-factor alphas of only 0.13%, 0.15%, 0.07% (t 0.58, 0.86, 0.49); Mohanram (2005) and Piotroski (2000) appear in the reference list, no G-score number extracted [P] — [Hou, Xue, Zhang](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf)
- Same replication, overall: 286 of 447 anomalies (64%) are insignificant at 5% with NYSE breakpoints and value weights, 380 (85%) at t >= 3; 95 of 102 liquidity/friction variables fail; of 161 significant anomalies the q-model leaves 115 alphas insignificant [P] — [Hou, Xue, Zhang](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf)
- Hanauer-Lauterbach (28 EMs): gross profitability and composite equity issuance among the anomalies that look pervasive in emerging markets [S] — [Quantpedia pointer](https://quantpedia.com/?p=28261)
- NSE's own quality definition (Nifty Midcap150 Quality 50 methodology): Z-scores of ROE, debt-to-equity (not used for financials) and EPS growth variability computed on the latest fiscal-year data and adjusted EPS of the previous 6 years, consolidated figures where available else standalone, weights 0.33/0.33/0.33 (0.5/0.5 for financials); Quality Score = 1 + Z if Z > 0 and (1 - Z)^-1 if Z < 0; stock cap lower of 5% or 5x free-float weight; semi-annual reconstitution June and December, the top 25 ranked are compulsory inclusions; the MQ50 factsheet gives data cut-off dates of 31 May and 30 Nov [P] — [Method Midcap150 Quality 50](https://www.niftyindices.com/Methodology/Method_NIFTYMidcap150_Quality50.pdf), [MQ50 factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty500MulticapMQ50.pdf)

### Inferences
- Quality is the better-supported leg than low volatility, and a quality gate on the momentum book is the more defensible Section 4 test. But the strongest published numbers (QMJ, F-score) are long-short; the delivery-feasible slice is the long leg, which Indian evidence (next section) puts at about 0.7%/mo of four-factor alpha.
- Lag handling can swing a result from t 2.6 to t 1.0 (gross profitability scaling), so any fundamentals-based trial must pre-register the information lag per field, using the filing date rather than the period-end date.
- A partly price-only quality route exists inside the corporate-actions file: dividends, buybacks and rights/QIP issuance give a net-payout/issuance proxy (payout and issuance are two of the four QMJ dimensions in JPV below); I did not find a paper that tests that exact Indian proxy.

### Gaps
- Primary sources not retrieved: Sloan (1996), Cooper-Gulen-Schill (2008), Pontiff-Woodgate (2008) net share issuance, Piotroski (2000), Mohanram (2005), Fama-French (2015) RMW/CMA. Their original sample statistics are therefore quoted only as reported inside Hou-Xue-Zhang.
- No Indian study found on accruals, asset growth, net issuance, RMW/CMA or the G-score (searched via general queries only; absence of hits is not proof of absence).
- US lag conventions (e.g. June t with fiscal t-1 data) of AFP and Novy-Marx were not extracted from the PDFs.

## India: NSE factor indices (methodology, live vs backfilled record, 2020-2026) and Indian academic evidence

### Takeaway
Indian quality evidence is strong in the academic record (QMJ four-factor alpha 0.917%/mo, 1995-2021) but the NSE quality and low-volatility indices did NOT beat Nifty 50 or Nifty 500 by much in the live era, and over the five years to 30 Sep 2026 they sit at or below the broad indices while Nifty200 Value 30 returned 22.91%/yr. Low-vol and quality indices lose in strong rallies (2017, 2019, 2021) and win in drawdowns (2008, 2018, 2020).

### Cited Findings
- NSE Index Dashboard (total return, 30 Sep 2026; 1Y / 3Y / 5Y CAGR %, 1Y volatility %, beta, P/E) [P] — [NSE dashboard](https://niftyindices.com/Index_Dashboard/Index_Dashboard_SEP2026.pdf):

| Index | Launch (live from) | 1Y | 3Y | 5Y | Vol | Beta | P/E |
|---|---|---|---|---|---|---|---|
| Nifty 50 | n/a | -7.09 | 6.06 | 6.38 | 13.46 | 1.00 | 19.4 |
| Nifty 500 | n/a | -2.03 | 9.52 | 9.04 | 14.21 | 1.03 | 21.8 |
| Nifty100 Low Volatility 30 | 8 Jul 2016 | -4.68 | 8.99 | 8.12 | 12.18 | 0.87 | 23.7 |
| Nifty Low Volatility 50 | not retrieved | -4.96 | 9.01 | 8.30 | 11.98 | 0.84 | 22.6 |
| Nifty500 Low Volatility 50 | not retrieved | -3.52 | 12.20 | 11.51 | 11.77 | 0.79 | 20.8 |
| Nifty Alpha Low-Volatility 30 | 10 Jul 2017 | -1.91 | 9.32 | 8.57 | 13.24 | 0.90 | 24.2 |
| Nifty100 Quality 30 | not retrieved | -3.17 | 7.78 | 7.25 | 12.75 | 0.82 | 25.6 |
| Nifty200 Quality 30 | 17 Apr 2018 | -5.42 | 6.64 | 6.40 | 13.58 | 0.86 | 25.7 |
| Nifty500 Quality 50 | not retrieved | -1.14 | 11.29 | 9.77 | 15.79 | 0.98 | 24.5 |
| Nifty Midcap150 Quality 50 | 24 Oct 2019 | -2.55 | 7.44 | 6.29 | 15.45 | 0.98 | 29.7 |
| Nifty500 Multicap Momentum Quality 50 | 4 Sep 2024 | -0.43 | 10.32 | 9.83 | 17.27 | 1.07 | 29.0 |
| Nifty Quality Low-Vol 30 | not retrieved | -6.38 | 5.43 | 5.81 | 11.93 | 0.80 | 25.5 |
| Nifty Alpha Quality Value Low-Vol 30 | not retrieved | -6.17 | 12.01 | 12.90 | 11.79 | 0.80 | 15.7 |
| Nifty200 Momentum 30 | 25 Aug 2020 | -0.47 | 9.21 | 9.28 | 18.63 | 1.18 | 23.2 |
| Nifty200 Value 30 | not retrieved | 7.89 | 21.22 | 22.91 | 16.83 | 1.00 | 8.9 |
| Nifty200 Alpha 30 | not retrieved | 6.01 | 13.92 | 13.62 | 19.17 | 1.18 | 17.9 |

- Live vs backfilled [P]: every index above has base date 1 Apr 2005 = 1000, so history before the launch date is NSE's retroactive computation. Nifty500 Multicap Momentum Quality 50 launched 4 Sep 2024, so roughly 3 of its 5 dashboard years are backfilled; Nifty200 Momentum 30 launched Aug 2020 and Midcap150 Quality 50 in Oct 2019, so their 5-year windows are almost fully live. Since-inception figures on the factsheets (LV30 16.45%, Nifty200 Quality 30 16.64%, Alpha LV30 17.71% from April 2005) are dominated by backfill and should not be quoted as track records — [LV30 factsheet](https://www.niftyindices.com/Factsheet/Nifty100_LowVolatility30.pdf), [Q30 factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Quality30.pdf), [Alpha LV30 factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Alpha_Low-Volatility_30.pdf)
- YTD 2026 total return to 30 Sep 2026 [P]: LV30 -10.24%, Nifty200 Quality 30 -10.40%, Alpha LV30 -6.09%, Midcap150 Quality 50 -4.58%, Momentum 30 -4.65%, MQ50 -2.23% — same factsheets plus [Momentum 30](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Momentum30.pdf), [Midcap150 Q50](https://www.niftyindices.com/Factsheet/Factsheet_NIFTYMidcap150_Quality50.pdf), [MQ50](https://www.niftyindices.com/Factsheet/Factsheet_Nifty500MulticapMQ50.pdf)
- Methodology: Nifty200 Quality 30 and Midcap150 Quality 50 are tilt-weighted Z-score ROE / D/E / EPS-variability indices with semi-annual reconstitution (June, December); Nifty100 LV30 is inverse-volatility weighted with quarterly review; the 12-month "volatility-adjusted" momentum scores of the NSE momentum indices are in [Momentum 30](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Momentum30.pdf) [P]
- Mirae note commentary: LV30 outperformed Nifty 50 and Nifty 100 in 2008-2011, 2018 and 2020, and underperformed in the bull markets of 2007, 2017 and 2021 [P] — [Mirae note](https://www.miraeassetmf.co.in/docs/default-source/product-guides/note---low-volatility-strategy-jan-2025.pdf)
- Jacob-Pradeep-Varma, "Performance of Quality Factor in Indian Equity Market" (IIMA WP 2022-11-01; SSRN 4284686), April 1995-March 2021, CMIE Prowess data, 312 months, universes of top 1,000 / 500 / 250 firms by market cap: quality = average of z-scores across profitability (gross profit/assets, ROE, ROA, cash flow/assets, gross margin, accruals), growth (5-year changes in those), safety (low beta, low leverage, Ohlson O-score and Altman Z, low ROE volatility) and payout (net equity issuance, net debt issuance, net payout) [P] — [IIMA WP](https://www.iima.ac.in/sites/default/files/2022-12/Wp-2022-11-01.pdf)
- JPV results [P]: QMJ four-factor alpha 0.917%/mo (top 1,000), 1.017%/mo (top 500), 0.875%/mo (top 250), standard errors 0.288 / 0.315 / 0.337 so t about 3.2 / 3.2 / 2.6 [C]; long-only quality (LQ) alpha 0.700 / 0.765 / 0.668%/mo with standard errors 0.171 / 0.180 / 0.201 so t about 4.1 / 4.3 / 3.3 [C] (abstract rounds LQ to 0.69%); QMJ loads positively on momentum (0.135 / 0.086 / 0.115) and negatively on value (-0.54 / -0.56 / -0.42), size (-0.17 / -0.22 / -0.36) and market (-0.19 / -0.23 / -0.29); LQ market loading 0.81-0.85, LQ size loading +0.31 / +0.30 / +0.34 (a small-cap tilt), LQ value loading -0.12 / -0.12 / 0.00 — Table A4 of the same [IIMA WP](https://www.iima.ac.in/sites/default/files/2022-12/Wp-2022-11-01.pdf)
- JPV continued [P]: quality-factor annual churn about 87% vs about 249% for momentum; alpha is driven mainly by profitability and payout; they argue quality is more important in India than in developed markets because of governance and profit-tunnelling concerns [P/S] — [IIMA WP](https://www.iima.ac.in/sites/default/files/2022-12/Wp-2022-11-01.pdf); Quantpedia summary (QMJ drawdown 9.76% average vs momentum 12.13%, QMJ monthly volatility 6.71%, D10 minus D1 four-factor alpha 0.98%/mo) [S] — [Quantpedia India factors](https://quantpedia.com/performance-of-factor-strategies-in-india/)
- IIMA four-factor library (Agarwalla-Jacob-Varma) provides India market, size, value, momentum factor series, but I found no published RMW/CMA series there [S] — [IIMA library](https://faculty.iima.ac.in/~iffm/Indian-Fama-French-Momentum/), [four-factor WP](https://www.iima.ac.in/publication/four-factor-model-indian-equities-market)
- Indian low-risk papers, snippet level only [S]: low-volatility stocks earn higher risk-adjusted returns but the effect largely proxies value (Applied Finance Letters 2016) — [AFL](https://ojs.aut.ac.nz/applied-finance-letters/article/download/65/63); IIMB Management Review 2017 "Volatility effect and the role of firm quality factor" finds low-risk stocks earn higher long-run returns — [IIMB 2017](https://www.iimb.ac.in/imr/previous-issues/volatility-march-2017.php); IIMB Management Review June 2023 is described in a search snippet as finding high-volatility stocks OUTPERFORM low-volatility stocks, in conflict with the above — [IIMB 2023](https://iimb.ac.in/imr/previous-issues/volatility-june-2023.php) (the title "How much does volatility influence stock market returns?" suggests it may concern market-level volatility; I could not open the page: 403/host not found); Saraf and Kayal (MSE WP 215, NSE 2010-2020) find the volatility anomaly shows up over 5-10 year horizons and is negligible over short windows — [MSE WP 215](https://mse.ac.in/wp-content/uploads/2022/03/Working-Paper-215.pdf)
- Piotroski F-score in India, snippet level only [S]: Singh and Kaur (2015) high-F-score value stocks beat the value portfolio by 18.4%/yr in one-year market-adjusted terms, 4.9% per F-score point — [Emerald](https://www.emerald.com/insight/content/doi/10.1108/IJLMA-09-2014-0055/full/html); an ISB dissertation on Prowess data 2013-2022 reports a 17.6% mean market-adjusted buy-and-hold return for strong signals and about 3.7% per F point — [ISB](https://eprints.exchange.isb.edu/id/eprint/2415/); an IIM Calcutta working paper (2009) reports high F-scores (7-9) well above market — [IIMC](https://ir.iimcal.ac.in:8443/jspui/handle/123456789/4128). All gross of costs, small-cap-heavy value universes. Screener.in publishes a Piotroski screen, evidence the score is computable from public Indian filings — [Screener](https://screener.in/screens/233559/Piotroski-FScore)

### Inferences
- The academic Indian quality alpha (about 0.7-0.9%/mo, top-250 robust) and the weak NSE quality-index record are not necessarily in conflict: the paper is a decile/long-short design on the top 1,000 with Prowess point-in-time-ish data over 26 years, the indices are 30-50 name Z-score tilts that only started live trading in 2018-2019 and whose live window coincided with a value rally. But the five-year dashboard record does mean any quality overlay has no demonstrated recent edge on NSE.
- At about 87% annual churn, quality costs roughly 87% x 40 bp = 35 bp/yr (about 3 bp/month) [C]; the cost barrier is not what stops it, the data availability and the post-2021 record are.
- With the Nifty200 Value 30 index at 22.91% 5Y, a quality tilt that is value-blind carried an opportunity cost in 2021-2026; JPV's own result that QMJ loads negatively on value says the same.

### Gaps
- Launch dates for Nifty100 Quality 30, Nifty500 Quality 50, Nifty Low Volatility 50, Nifty500 Low Volatility 50, Quality Low-Vol 30, Alpha Quality Value Low-Vol 30, Nifty200 Value 30 and Nifty200 Alpha 30 were not retrieved.
- No NSE index turnover figures; no benchmark for Midcap150 Quality 50 (Nifty Midcap 150 TRI was not extracted) so its 6.29% 5Y cannot be read as under- or over-performance.
- JPV's information-lag convention, portfolio rebalance month and the per-year (rather than full-sample) alpha stability were not extracted from the text; JPV quality alpha post-2018 or post-publication is not reported (sample ends March 2021).
- Indian academic evidence on lottery/skewness, accruals, asset growth, issuance, and RMW/CMA: none found. IIMB, AFL and MSE papers were not opened in full.
- Free Indian data availability: I verified only that Screener.in exposes a Piotroski screen and that NSE builds its quality indices from company financial filings (consolidated else standalone). I did not open NSE/BSE XBRL portals, Trendlyne, Tickertape or moneycontrol to confirm download terms, point-in-time filing dates, or restatement behaviour.

## Post-publication decay, replication and transaction-cost survival

### Takeaway
Across the broad literature most anomalies shrink or vanish under clean replication (64% insignificant in Hou-Xue-Zhang), costs remove more than half of BAB's gross return and all of its five-factor alpha, and the US is the only market with a reliable post-publication decline, so India decay is not established either way. Quality/profitability is the family with the best survival record; MAX/IVOL/accrual-type signals the worst.

### Cited Findings
- Jacobs-Müller, "Anomalies across the globe: Once public, no longer existent?" (JFE 135(1), 2020, 213-230): 241 anomalies in 39 markets, over two million anomaly-country-months; the US is the only country with a reliable post-publication decline in long/short returns [S] — [Jacobs, Müller](https://hemf.wiwi.uni-due.de/en/research/publications/anomalies-across-the-globe-once-public-no-longer-existent-14591)
- Chen-Velikov, "Zeroing in on the expected returns of anomalies" (JFQA 2022): net-of-cost anomaly returns after 2005 are close to zero for original implementations (second-hand figures: about -1 bp/month, about +4 bp/month with cost-minimizing execution; a secondary source said about 1%/yr average long-short net) — I could not confirm these against the paper [S] — [Chen, Velikov (Federal Reserve)](https://www.federalreserve.gov/econres/feds/zeroing-in-on-the-expected-returns-of-anomalies.htm)
- Hou-Xue-Zhang: 64% of 447 anomalies fail at t < 1.96 and 85% at t < 3 under NYSE breakpoints and value weights; MAX, IVOL, total volatility, accruals quality, Amihud illiquidity and short-term reversal are among the failures [P] — [Hou, Xue, Zhang](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf)
- Novy-Marx-Velikov: BAB costs 60 bp/month (26 bp over the last ten years) and its net five-factor generalized alpha is 16 bp/month, t 1.20; excluding the bottom NYSE decile cuts costs to 23 bp/month but net performance is unchanged (47 bp/month) [P] — [Novy-Marx, Velikov](https://mysimon.rochester.edu/novy-marx/research/BABAB.pdf)
- Blitz-Pang-van Vliet EM volatility premium was 3.1%/yr in 1989-1999 and 14.4%/yr in 2000-2010 (increasing, not decaying, in that sample) [S] — [CXO Advisory](https://www.cxoadvisory.com/?p=20977)

### Inferences
- The delivery-account question is net-of-cost long-only: the costs that sank BAB (small-cap shorting, 215% turnover in nano-caps) mostly do not apply to a liquid 30-50 name long-only book, where the drag is 3-7 bp/month at 100-200% turnover [C]. The binding problems are instead (1) that the long leg is a small share of the published premium, (2) the 2021-2026 Indian record, and (3) the missing fundamentals.
- Because the US-only decay evidence rests on US-centric publication timing, absence of decay in India does not mean the Indian effect is stable; the five-year NSE record is the best direct evidence and it is poor.

### Gaps
- McLean-Pontiff (2016, JF) and Jensen-Kelly-Pedersen (2023, JF, "Is there a replication crisis in finance?") were not retrieved. I recall McLean-Pontiff reporting about 26% lower out-of-sample and about 58% lower post-publication returns, and JKP reporting that most factors replicate with an India-inclusive global panel; these are from memory and should be verified before use.
- No retrieved study of decay for the Indian versions of any of these anomalies.

## Candidate catalogue (26 strategies), cost clearance, data needs and overlap with 00-already-covered.md

### Takeaway
Twenty-six candidates are listed below. Only a handful are both runnable on price-and-corporate-actions data alone and not already closed in 00-already-covered.md: a low-volatility gate or rank blend on the momentum book (C6, C7), a MAX gate (C9), and a rights/QIP/preferential-issue avoidance gate (C19). A quality gate (C23) is the best-supported by the literature but needs a fundamentals feed the repo does not have. Cost is not the binding constraint for any long-only, 30-50 name candidate (drag 1.7-7 bp/month at 40-60 bp round trip); the binding constraints are (1) whether the edge survives modern replication (HXZ: 64% of anomalies fail), (2) the poor 2021-2026 NSE record of low-vol and quality indices against Nifty 500, and (3) point-in-time fundamentals availability. Effects are the published ones, mostly long-short and gross; none is a forecast for this account.

Legend. Cost verdict: CLEARS = cost drag at 40-60 bp RT is below about 7 bp/month and well below the published effect; EDGE UNPROVEN = costs are fine but the edge is not shown net of replication or in India; INFEASIBLE = needs shorting or illiquid names. "Overlap" cites 00-already-covered.md ("3f"/"3g" = its sections 3f/3g; "Section 4" = the untested overlay list; line numbers as in my reading of that file). Data sources: "free source" = a place where the field can be obtained without paying; whether it is point-in-time is stated per row or in Gaps.

### Cited Findings

#### A. Low risk (C1-C8)

- **C1. Long-only low total volatility (own version of Nifty100 Low Vol 30: lowest 1-year daily-return stdev, inverse-vol weights, quarterly)**
  - Source and sample: Baker-Bradley-Wurgler FAJ 2011 (US top 1,000, 1968-2008) — [BBW](https://pages.stern.nyu.edu/~jwurgler/papers/faj-benchmarks.pdf); NSE Nifty100 LV30 methodology — [Method](https://archives.nseindia.com/content/indices/Method_Nifty100_Low_Volatility_30.pdf).
  - Effect and statistic: long-only information ratio 0.08-0.17 (US) [P]; HXZ total-volatility high-minus-low -0.40%/mo (t -1.16) at 1 month, insignificant [P] — [HXZ](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf); India live 2017-2024 LV30 16.7% vs Nifty 50 15.6% CAGR, about +9 bp/month [C], and 5Y to Sep 2026 8.12% vs 6.38% [P] — [NSE dashboard](https://niftyindices.com/Index_Dashboard/Index_Dashboard_SEP2026.pdf).
  - Turnover and cost: index turnover not retrieved; at 50-100% one-way and 40 bp RT the drag is 1.7-3.3 bp/month [C]. CLEARS on cost.
  - OOS / India / negatives: live era lost to Nifty 500 in 5 of 8 calendar years (2017 -25.4 pt, 2021 -24.0 pt) and lost 2019, 2021, 2022 to Nifty 50 [C from Mirae table]; Mirae says it beat its parent Nifty 100 in only 10 of 19 calendar years since 2006 (10 of those 19 years predate the July 2016 launch [C]) [P] — [Mirae](https://www.miraeassetmf.co.in/docs/default-source/product-guides/note---low-volatility-strategy-jan-2025.pdf). Edge over Nifty 50 is small and index-relative, not absolute.
  - Data: daily closes only; no fundamentals. Free.
  - Overlap: 3f line 120 lists a low-volatility sleeve as "worth a pre-registered test", while 3f line 127 and 3g (about lines 325-332) say Leave/skip as risk reduction; the file contradicts itself, so a sleeve is an open question and a family-bar test is needed to close it either way.
- **C2. Long-only low beta (lowest 60-month or 1-year market beta quintile)**
  - Source: Frazzini-Pedersen BAB (JFE 2014) — [FP](https://pages.stern.nyu.edu/~lpederse/papers/BettingAgainstBeta.pdf); BBW above.
  - Effect: BAB is long-short with leverage: US Sharpe 0.78 1926-2012 and alpha 0.55%/mo (t 5.59 with momentum) [P]; the long leg alone is not reported there (Gap). NMV: net BAB 48 bp/mo (t 3.30) but 5-factor alpha 16 bp/mo, t 1.20 [P] — [NMV](https://mysimon.rochester.edu/novy-marx/research/BABAB.pdf).
  - Turnover and cost: BAB turnover 214.7%/yr with $1.33 round-trip on the long side; for a 30-50 name liquid book 100-200% turnover costs 3.3-6.7 bp/month at 40 bp RT [C]. CLEARS on cost.
  - OOS / India / negatives: NSE Nifty100 LV30 beta 0.87, Low Vol 50 0.84, Nifty500 Low Vol 50 0.79 [P]; no Indian long-only beta study retrieved. Defensive equity is explained by profitability/size/value (Novy-Marx) [P].
  - Data: daily closes plus index returns. Free.
  - Overlap: 3f line 127 lists beta as skipped ("tested in section 85"); closed, do not re-propose except as part of C7.
- **C3. Low idiosyncratic volatility (AHXZ 2006)**
  - Source: Ang-Hodrick-Xing-Zhang (JF 2006) — not retrieved; numbers via HXZ only.
  - Effect: HXZ idiosyncratic-volatility high-minus-low -0.51%, -0.33%, -0.18%/mo at 1, 6, 12 months, t -1.62, -1.11, -0.62: insignificant [P] — [HXZ](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf).
  - Turnover and cost: monthly signal, same as C1. EDGE UNPROVEN.
  - OOS / India / negatives: HXZ lists it among results that do not survive; no Indian IVOL-specific test retrieved beyond snippets (AFL 2016: low vol earns higher risk-adjusted returns but mostly proxies value) [S] — [AFL](https://ojs.aut.ac.nz/applied-finance-letters/article/download/65/63).
  - Data: daily returns and index factors. Free.
  - Overlap: 3f line 127 lists IVOL as skipped ("tested in section 85"). Closed.
- **C4. Multi-factor defensive stack (low vol + quality + value; NSE Alpha Quality Value Low-Vol 30 and Quality Low-Vol 30 as the observable instances)**
  - Source and sample: NSE Index Dashboard, total return to 30 Sep 2026 [P] — [NSE dashboard](https://niftyindices.com/Index_Dashboard/Index_Dashboard_SEP2026.pdf).
  - Effect: Nifty Alpha Quality Value Low-Vol 30 returned 12.01% 3Y and 12.90% 5Y with beta 0.80, 1Y volatility 11.79% and P/E 15.7, vs Nifty 50 6.38% and Nifty 500 9.04% over 5Y; Nifty Quality Low-Vol 30 (no value leg) returned only 5.43% 3Y and 5.81% 5Y at P/E 25.5; Nifty Alpha Quality Low-Vol 30 9.41% 5Y [P].
  - Turnover and cost: not retrieved. EDGE UNPROVEN; launch dates not retrieved so the backfilled share of each 5Y window is unknown.
  - OOS / India / negatives: the 7-point 5Y gap between the version with a value leg and the one without suggests the value leg, not low vol or quality, drove 2021-2026 [C]; consistent with JPV's finding that QMJ loads negatively on value.
  - Data: price for vol; trailing earnings/book for value and quality. Fundamentals needed for two of three legs.
  - Overlap: 3g Leave on value, quality and low-vol sleeves; line 313 says use NSE factor indices as a fallback implementation, not a signal.
- **C5. Robeco "conservative formula" (low volatility + 12-1 momentum + net payout yield, rank-combined)**
  - Source: Blitz and van Vliet, Robeco — not retrieved (Gap); no sourced number.
  - Effect and statistic: none sourced.
  - Turnover and cost: unknown. EDGE UNPROVEN.
  - OOS / India / negatives: none found; the Robeco EM PDF I tried returned HTML.
  - Data: price for two of three legs; net payout needs dividends + buybacks - issuance (the corporate-actions file covers dividends and part of the rest).
  - Overlap: momentum x low-vol (3g Leave), dividend-yield sleeve (3g Leave), buyback tender reserve (3g Leave); the incremental piece is the three-way rank combination.
- **C6. Momentum x low-volatility rank blend (select on a combined rank, e.g. 12-1 momentum rank + low-vol rank, instead of momentum alone)**
  - Source: no paper retrieved with this exact design; the observable analogue is NSE Nifty Alpha Low-Vol 30 (5Y 8.57%, 1Y vol 13.24%, beta 0.90) vs Nifty200 Momentum 30 (5Y 9.28%, vol 18.63%, beta 1.18) [P] — [NSE dashboard](https://niftyindices.com/Index_Dashboard/Index_Dashboard_SEP2026.pdf). The two are built differently (Alpha = 1-year Jensen alpha), so the comparison is only indicative of the trade-off: about 0.7 pt/yr less return for about 5.4 pt less volatility [C].
  - Effect: untested here; the family bar t >= 2.865 applies (momentum family, 00-already-covered.md lines 150-151).
  - Turnover and cost: depends on the rank weights; adds a slower-moving signal, likely lowering turnover; CLEARS on cost.
  - OOS / India / negatives: Momentum 30's own dashboard beta (1.18) shows the momentum book is a high-beta book; HXZ says volatility itself is not priced cleanly, so the blend is a risk-shape change and may cost return.
  - Data: price only. Free.
  - Overlap: 3g Leave (momentum x low-vol "risk reduction"), but Section 4 lists low-vol/quality overlays on the momentum book as untested at the family bar, both halves. This is the Section 4 item.
- **C7. Low-volatility gate on the momentum book (exclude momentum candidates in the top vol tercile or require 1-year vol rank below a cutoff)** — SECTION 4 PRIORITY
  - Source and rationale: Novy-Marx 2014: high vol/beta stocks are small, unprofitable, growth [P] — [Novy-Marx](https://www.nber.org/system/files/working_papers/w20591/w20591.pdf); NSE Momentum 30 beta 1.18 and 1Y vol 18.63% vs Nifty 50 13.46% [P].
  - Effect: unknown; this is a non-inferiority and drawdown test (the 00 file's own wording: "low-vol/quality overlay as a non-inferiority rule"), not a return source. HXZ's insignificant volatility spreads warn that return improvement is not to be expected.
  - Turnover and cost: a gate removes names rather than adding trades; expected drag change near zero. CLEARS.
  - OOS / India / negatives: LV30 lost to Nifty 500 in 5 of 8 live years, so a hard low-vol requirement can force the book out of rallies (2017, 2021) where momentum earns most [C from Mirae table]; use a loose cutoff and test both halves.
  - Data: price only. Free.
  - Overlap: Section 4 untested overlay (pivot brief lines 30 and 46). Not closed.
- **C8. Betting-against-beta long-short (reference only)**
  - Source: FP and NMV as in C2.
  - Effect: gross about 108 bp/month = 48 net + 60 cost [C]; after costs 5-factor alpha 16 bp/month, t 1.20 [P].
  - Cost: INFEASIBLE for a delivery account (short leg, leverage, nano-cap trading, 214.7%/yr turnover).
  - OOS / India / negatives: 18 of 19 developed markets positive Sharpe, 4-factor alpha significant in 6 of 19 [P]; Blitz-Pang-van Vliet EM long-short 8.8%/yr, mostly from shorting high-vol [S] — [CXO](https://www.cxoadvisory.com/?p=20977).
  - Data: not needed.
  - Overlap: none; shorting is out of scope. Listed to bound what the long leg can capture.

#### B. Lottery and skewness (C9-C12)

- **C9. MAX avoidance screen (drop names whose largest daily return in the prior month is in the top 3 deciles, as a gate on the momentum book)**
  - Source and sample: Bali-Cakici-Whitelaw, NBER WP 14804 / JFE 2011, 1962-2005 — [BCW](https://www.nber.org/papers/w14804.pdf).
  - Effect and statistic: value-weighted decile 10 minus 1 -1.03%/mo (t -2.83), 4-factor alpha -1.18%/mo (t -4.71); long-only reading: deciles 1-7 average about 1.00-1.16%/mo vs 0.86%, 0.52%, -0.02%/mo in deciles 8, 9, 10 [P].
  - Turnover and cost: monthly signal, but as a gate only names that flip into the excluded set trade. CLEARS.
  - OOS / India / negatives: HXZ replication -0.34%/mo (t -1.14) at 1 month, insignificant [P] — [HXZ](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf); Gorman et al. say MAX may be overreaction not lottery demand [S] — [Gorman](https://cfr.ivo-welch.info/published/papers/gorman2021could.pdf); India: Sharma-Chakraborty find no lottery overpricing (sign possibly reversed) [S] — [SEF](https://www.doi.org/10.1108/SEF-04-2018-0099). This is the weakest-supported of the Section 4 gate candidates.
  - Data: daily returns. Free.
  - Overlap: not in 3f/3g; a MAX gate on the momentum book is a variant of the Section 4 untested overlay.
- **C10. Expected idiosyncratic skewness (Boyer-Mitton-Vorkink 2010)**
  - Source: not retrieved.
  - Effect: none sourced; HXZ's realized-skewness high-minus-low is POSITIVE (+0.23% to +0.34%/mo, t 2.11-3.50), the wrong sign for a lottery-overpricing story [P] — [HXZ](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf).
  - Cost: EDGE UNPROVEN; estimation (cross-sectional regression of skewness on lagged characteristics) is non-trivial.
  - India: none found.
  - Data: daily returns, volume. Free.
  - Overlap: none found; do not pre-register without retrieving the source.
- **C11. MIN effect (buy names with high prior-month minimum return)**
  - Source: Indian study of 1999-2014 data (abstract only) [S] — [IDEAS](https://ideas.repec.org/a/bor/bistre/v18y2018i1p76-90.html).
  - Effect: no bp/month or t-stat retrieved; concentrated in small-cap, illiquid stocks with low institutional holdings.
  - Cost: INFEASIBLE or EDGE UNPROVEN: where the effect lives (illiquid small caps) is where Rs 10-20k positions suffer the widest spreads.
  - Data: daily returns. Free.
  - Overlap: none found.
- **C12. Long high-MAX (the opposite sign, India only)**
  - Source: Sharma-Chakraborty (SEF) abstract suggests a long-high-MAX strategy could be profitable in India [S] — [SEF](https://www.doi.org/10.1108/SEF-04-2018-0099).
  - Effect: no magnitude retrieved; contradicts the US result and HXZ's insignificance.
  - Cost: EDGE UNPROVEN; high-MAX names are volatile, probably also high-momentum (inference), so it overlaps the momentum book rather than diversifying it.
  - Data: daily returns. Free.
  - Overlap: indirect with the momentum family; it would be a momentum-family trial under the same t bar.

#### C. Quality and accounting (C13-C24)

- **C13. Gross profitability (gross profit / assets, long the top profitability tercile or quintile)**
  - Source and sample: Novy-Marx, JFE 2013, Compustat July 1963-Dec 2010 — [Novy-Marx](https://mysimon.rochester.edu/novy-marx/research/QDoVI.pdf).
  - Effect and statistic: 0.31%/mo (t 2.49) most-minus-least profitable; mixed with value t 5.87 and Sharpe 0.85 [P]. HXZ replication: 0.38%/mo (t 2.62) scaling by current assets, but 0.16%/mo (t 1.04) scaling by lagged assets [P] — [HXZ](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf).
  - Turnover and cost: annual re-rank; turnover not sourced, at 50% one-way and 40 bp RT the drag is 1.7 bp/month [C]. CLEARS on cost.
  - OOS / India / negatives: pervasive in 28 emerging markets [S] — [Quantpedia pointer](https://quantpedia.com/?p=28261); in India it enters only as one component of JPV's QMJ (gpoa); no standalone Indian GP/A test retrieved. The lag-convention swing (t 2.6 to 1.0) is the negative finding.
  - Data: revenue, cost of goods sold (or a gross-profit line), total assets, from annual results. Free source: NSE/BSE filed results (exist; download terms and point-in-time behaviour unverified). Screener.in shows derived ratios but I did not verify filing dates or restatement behaviour. No price-only proxy shown; the nearest is low volatility (C1).
  - Overlap: 3f line 127 skips quality (ROE, leverage); 3g Leave on quality. GP/A is a different measure but the same family, so it is "quality" for the closure; the Section 4 quality gate is the open exception.
- **C14. Composite long-only quality (JPV "LQ": z-score average of profitability, growth, safety, payout)**
  - Source and sample: Jacob-Pradeep-Varma, IIMA WP 2022-11-01, April 1995-March 2021, 312 months, CMIE Prowess — [IIMA WP](https://www.iima.ac.in/sites/default/files/2022-12/Wp-2022-11-01.pdf).
  - Effect and statistic: LQ four-factor alpha 0.700 / 0.765 / 0.668%/mo for top 1,000 / 500 / 250 firms, t about 4.1 / 4.3 / 3.3 [C from the table's standard errors]; the long-short QMJ alpha is 0.917 / 1.017 / 0.875%/mo [P].
  - Turnover and cost: churn about 87%/yr vs about 249% for momentum (one-way or two-way not stated) [P]; drag about 2.9 bp/month at 40 bp RT (4.4 at 60 bp) if one-way [C]. CLEARS on cost.
  - OOS / India / negatives: sample ends March 2021, nothing post-publication reported; the LQ portfolio has a market loading of 0.81-0.85 and a size loading of +0.31 to +0.34, i.e. a small-cap-tilted portfolio, so some of the alpha is a size-tilt capacity question [P]. The NSE quality indices (C15) show no comparable edge in 2021-2026.
  - Data: about 13 fields across income statement, balance sheet, cash flow and equity/debt issuance; Prowess is paid. Free replication would need NSE/BSE filings for all fields, which I did not test.
  - Overlap: 3f line 127 skip, 3g Leave on quality. Not a Section 4 item unless used as a gate (C23).
- **C15. NSE-style quality Z-score tilt (ROE, debt/equity, EPS-growth variability; hold the top 30-50 by score, or simply hold the NSE quality index constituents)**
  - Source: NSE methodology — [Method Midcap150 Quality 50](https://www.niftyindices.com/Methodology/Method_NIFTYMidcap150_Quality50.pdf) [P]; performance from the NSE dashboard — [NSE dashboard](https://niftyindices.com/Index_Dashboard/Index_Dashboard_SEP2026.pdf) [P].
  - Effect: 5Y total return Nifty100 Quality 30 7.25%, Nifty200 Quality 30 6.40%, Nifty500 Flexicap Quality 30 6.18%, Midcap150 Quality 50 6.29% against Nifty 50 6.38% and Nifty 500 9.04%; only Nifty500 Quality 50 (9.77% 5Y, 11.29% 3Y vs Nifty 500 9.52% 3Y) edges the broad market (+0.7 pt/yr 5Y, +1.8 pt/yr 3Y) [P/C]. Smallcap250 Quality 50 returned 11.71% 5Y (no benchmark extracted).
  - Turnover and cost: semi-annual reconstitution (June, December), top 25 ranks compulsory [P]; index turnover not retrieved. CLEARS on cost if turnover is under 100%.
  - OOS / India / negatives: Nifty200 Quality 30 YTD 2026 -10.40% to 30 Sep [P]; launch dates for most quality indices not retrieved so the backfilled share of the 5Y is unknown (Nifty200 Quality 30 launched 17 Apr 2018, Midcap150 Quality 50 24 Oct 2019) [P]. No recent edge shown for the large-cap versions.
  - Data: latest-fiscal-year net profit, equity, debt, and six years of adjusted EPS, consolidated else standalone [P]. Free source: filings (unverified); NSE publishes constituents and weights, which makes the index itself a free "signal" (the 313-line fallback in 00-already-covered.md).
  - Overlap: 3f skip (quality), 3g Leave (quality), line 313 (NSE factor indices as a fallback implementation, not a signal).
- **C16. Operating profitability / RMW (Fama-French 2015)**
  - Source: Fama-French (2015) — not retrieved (Gap).
  - Effect: none sourced directly. NMV report BAB loads 0.45 on RMW and 0.50 on CMA, which is why its 5-factor alpha vanishes (t 1.63) [P] — [NMV](https://mysimon.rochester.edu/novy-marx/research/BABAB.pdf).
  - Cost: EDGE UNPROVEN; same cost profile as C13.
  - OOS / India / negatives: no Indian RMW series found in the IIMA four-factor library page [S] — [IIMA library](https://faculty.iima.ac.in/~iffm/Indian-Fama-French-Momentum/).
  - Data: revenue, COGS, SG&A, interest expense, book equity, from annual filings.
  - Overlap: same closure as C13; fold into C13 rather than test separately.
- **C17. Asset-growth / investment avoidance (CMA; exclude the highest asset-growth decile)**
  - Source: Cooper-Gulen-Schill 2008 (not retrieved); numbers via HXZ — [HXZ](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf).
  - Effect and statistic: HXZ value-weighted high-minus-low -0.46%/mo (t -2.92) vs -1.05%/mo (t -5.04) value-weighted and -1.73%/mo (t -8.45) equal-weighted in the original [P]; the short leg dominates, so long-only means "avoid", not "buy".
  - Turnover and cost: annual; CLEARS.
  - OOS / India / negatives: no Indian study found. For banks, NBFCs and insurers asset growth is structural and would need sector-relative treatment (my inference).
  - Data: total assets at t and t-1 from annual filings. Free source as above (unverified).
  - Overlap: not named in 3f/3g; the adjacent closure is "quality (ROE, leverage)".
- **C18. Accruals (low operating or total accruals)**
  - Source: Sloan 1996 (not retrieved); via HXZ.
  - Effect and statistic: operating accruals high-minus-low -0.27%/mo (t -2.13) vs -10.4%/yr (t -4.71) in Sloan; q-factor alpha -0.54%/mo (t -3.77); Richardson total accruals -0.23%/mo (t -1.63) [P] — [HXZ](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf).
  - Turnover and cost: annual; CLEARS. A short-leg effect, so long-only is an avoid screen.
  - OOS / India / negatives: no Indian test found; JPV includes an accrual measure inside the quality composite [P].
  - Data: net income, cash flow from operations, total assets (annual cash-flow statement). Free source as above (unverified).
  - Overlap: none explicit; adjacent to quality closure.
- **C19. Net or composite equity issuance avoidance (exclude names with rights issues, QIPs, preferential allotments or large ESOP dilution in the past 12 months)**
  - Source: Pontiff-Woodgate (2008) (not retrieved); numbers via HXZ — [HXZ](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf).
  - Effect and statistic: composite equity issuance high-minus-low -0.56%/mo (t -3.16), q-alpha -0.24%/mo (t -1.85) [P]; payout/issuance is one of the two dimensions that drives JPV's Indian QMJ alpha [P] — [IIMA WP](https://www.iima.ac.in/sites/default/files/2022-12/Wp-2022-11-01.pdf); pervasive in 28 EMs [S] — [Quantpedia pointer](https://quantpedia.com/?p=28261).
  - Turnover and cost: event-driven gate; CLEARS.
  - OOS / India / negatives: no Indian standalone test; whether the repo's corporate-actions file records rights, QIP and preferential issues with dates is not known to me (check before pre-registering). Share-count changes are not a clean proxy because bonuses and splits change counts without issuance.
  - Data: corporate-actions file (partial price-only proxy, an inference not shown in any paper I found); full version needs shares outstanding history.
  - Overlap: 3g Leave on the buyback tender reserve covers only the buy side; I found no closed item for issuance avoidance.
- **C20. Piotroski F-score within a value universe (long F >= 7 among cheap stocks)**
  - Source and sample: Piotroski 2000 (not retrieved); US replication in HXZ; Indian studies at snippet level.
  - Effect and statistic: quarterly F-score high-minus-low 0.58%, 0.53%, 0.42%/mo (t 2.47, 2.52, 2.22) but q-factor alphas 0.13%, 0.15%, 0.07%/mo (t 0.58, 0.86, 0.49) [P] — [HXZ](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf). India: +18.4%/yr one-year market-adjusted return for high-F value stocks, 4.9% per F point (Singh-Kaur 2015) [S] — [Emerald](https://www.emerald.com/insight/content/doi/10.1108/IJLMA-09-2014-0055/full/html); ISB dissertation on Prowess 2013-2022: 17.6% and about 3.7% per point [S] — [ISB](https://eprints.exchange.isb.edu/id/eprint/2415/).
  - Turnover and cost: one-year holds, 100% annual turnover implies 3.3 bp/month [C]; the Indian studies are gross of costs and small-cap-value heavy.
  - OOS / India / negatives: the US alpha disappears once controlled for the q-model; the Indian numbers are market-adjusted buy-and-hold returns, not factor alphas, and not tradeable-size-checked.
  - Data: nine binary accounting signals from current and prior-year statements (definition recalled from Piotroski, not retrieved). Screener.in publishes an F-score screen, so the score is computable from public filings — [Screener](https://screener.in/screens/233559/Piotroski-FScore).
  - Overlap: 3g Leave on value; F-score requires a value sleeve first.
- **C21. Mohanram G-score (growth-stock analogue of F-score)**
  - Source: Mohanram 2005 (not retrieved); HXZ lists it in references only; no number extracted.
  - Effect: none sourced. EDGE UNPROVEN.
  - Data: R&D, capex, advertising and earnings-variability fields, which are sparse in Indian filings (my inference, unverified).
  - India: none found.
  - Overlap: none found; do not pre-register.
- **C22. Quality plus momentum blend (select on a momentum and quality combined rank)**
  - Source: NSE Index Dashboard [P] — [NSE dashboard](https://niftyindices.com/Index_Dashboard/Index_Dashboard_SEP2026.pdf); AFP QMJ and JPV for the factor evidence.
  - Effect: 5Y total return Nifty500 Multicap MQ50 9.83% (1Y vol 17.27%, beta 1.07) vs Nifty200 Momentum 30 9.28% (18.63%, 1.18); Nifty MidSmallcap400 MQ100 12.87% 5Y, 12.31% 3Y; Nifty Smallcap250 MQ100 11.87%; Nifty Total Market MQ50 10.57% [P]. MQ50 launched 4 Sep 2024, so about 3 of its 5 dashboard years are backfilled; launch dates of the others not retrieved. QMJ alpha survives a momentum control (US 4-factor alpha 66 bp/mo, t 11.20) [P] — [AFP](https://conference.nber.org/conf_papers/f69835.pdf), as does JPV's (0.917%/mo with momentum in the model) [P], so quality is not repackaged momentum.
  - Turnover and cost: two signals with different speeds; below 150% likely; CLEARS on cost.
  - OOS / India / negatives: the blends' lower volatility vs pure momentum is the consistent feature; the backfill share and absence of any live multi-year record limit it.
  - Data: price plus the C15 fundamentals.
  - Overlap: 3f skips momentum-plus-quality blends; Section 4 lists quality/low-vol overlays on the momentum book as untested. A blend is the same idea as the gate in C23 but implemented as rank-weighting.
- **C23. Quality gate on the momentum book (exclude momentum candidates with negative earnings, ROE below a floor, or leverage above a ceiling; the minimal NSE-component version)** — SECTION 4 PRIORITY
  - Source and rationale: AFP and JPV (quality survives momentum control and is negatively correlated with market/high-vol junk), Novy-Marx 2014 (high-vol winners tilt to unprofitable growth) [P]; the field set mirrors NSE's own quality score (ROE, D/E, EPS variability) [P] — [Method](https://www.niftyindices.com/Methodology/Method_NIFTYMidcap150_Quality50.pdf).
  - Effect: untested for this book; a non-inferiority and drawdown test at the family bar, not a new return source.
  - Turnover and cost: a gate removes names; expected drag change near zero. CLEARS.
  - OOS / India / negatives: in India the NSE quality indices show no 2021-2026 edge (C15), and QMJ is negatively loaded on value; a hard quality gate may cut cheap, rebounding momentum names. No Indian paper tests a quality gate on momentum.
  - Data: latest-annual PAT, shareholders' equity and borrowings (three fields) for every name and year since about 2010. Free source: NSE/BSE results filings (not verified as bulk-downloadable); Screener.in, Trendlyne, Tickertape display these but I did not verify point-in-time behaviour.
  - Overlap: Section 4 untested overlay. Not closed.
- **C24. Net payout yield from the corporate-actions file (dividends plus buybacks minus issuance, scaled by price)**
  - Source: payout as a QMJ dimension and driver of the Indian alpha — [IIMA WP](https://www.iima.ac.in/sites/default/files/2022-12/Wp-2022-11-01.pdf) [P]; Robeco's conservative formula uses it (not retrieved).
  - Effect: no standalone number retrieved.
  - Turnover and cost: annual; CLEARS. Dividend per share over price needs only the corporate-actions file; buyback and issuance yields need share counts or market cap, which a price-and-volume file lacks (my inference).
  - OOS / India / negatives: none found.
  - Data: corporate-actions file (dividends: yes; buybacks and issuance: depends on what is recorded).
  - Overlap: 3g Leave on the dividend-yield sleeve and the buyback tender reserve; only the net (issuance-adjusted) composite is new.

#### D. Implementation and conditional variants (C25-C26)

- **C25. Factor-index product route (hold an NSE low-vol or quality index fund or ETF in place of a self-built sleeve)**
  - Source: NSE Index Dashboard [P]; Mirae's LV30 note implies a Mirae product tracks Nifty100 LV30 (not verified) [P/S] — [Mirae](https://www.miraeassetmf.co.in/docs/default-source/product-guides/note---low-volatility-strategy-jan-2025.pdf).
  - Effect: Nifty100 LV30 5Y 8.12%, Nifty500 Low Vol 50 11.51%, Alpha Low-Vol 30 8.57%, Alpha Quality Value Low-Vol 30 12.90% vs Nifty 500 9.04% [P]. Net of expense ratio, tracking error and the delivery-account friction: not retrieved.
  - Cost: EDGE UNPROVEN; avoids stock-level DP charges but adds a fund expense ratio (unknown).
  - Data: none.
  - Overlap: 00-already-covered.md line 313 says use NSE factor indices as a fallback implementation, not a signal. Consistent with this row.
- **C26. Regime-conditional low-vol or quality (switch into LV30 when a bear-market filter fires)**
  - Source: Mirae: LV30 outperformed Nifty 50 in 2008-2011, 2018 and 2020 and underperformed in 2007, 2017 and 2021 [P] — [Mirae](https://www.miraeassetmf.co.in/docs/default-source/product-guides/note---low-volatility-strategy-jan-2025.pdf).
  - Effect: the 2008 gap was -42.3% vs -51.3% (+9.0 pt) [P]; no regime-switch backtest retrieved.
  - Cost: EDGE UNPROVEN; adds regime-timing error.
  - Data: price only.
  - Overlap: 3g Leave on conditional volatility overlay and bear-market filter. Closed.

### Inferences
- Ranking for a pre-registered next step (data cost low to high): (1) C7 low-vol gate and C6 rank blend on the momentum book, both price-only, both Section 4 items, tested as non-inferiority on both halves under the family bar; (2) C19 issuance-avoidance gate if the corporate-actions file carries rights/QIP/preferential-issue dates; (3) C9 MAX gate, last of the gates because the only Indian evidence points the opposite way; (4) C23 quality gate, the best-supported on theory but gated on building a three-field annual-fundamentals table; (5) standalone sleeves C13, C14, C15, C17, C18, C20 need a statement-level feed and have no demonstrated recent NSE edge; (6) Leave: C8, C10, C11, C12, C16, C21, C26, plus C2 and C3 (already closed in 3f).
- Cost arithmetic is not what rules candidates in or out: at 40-60 bp RT the drag for the long-only 30-50 name candidates is 1.7-10 bp/month even at 200% turnover [C], against published gross effects of 30-100 bp/month. What rules them out is replication (HXZ 64% fail), the single-country decay evidence, and in India the weak 2021-2026 quality and low-vol index record against Nifty 500.
- Data tiers: price-only (C1-C3, C6-C12, C26); price plus corporate actions (C19, C24, partially); three annual fields PAT, equity, debt (C15, C23); statement-level, eight or more fields (C13, C14, C16-C18, C20-C22). The tier is the real cost of each idea.
- Free-source assessment (inference, not tested): NSE builds its quality indices from company financial filings, and Screener.in's public Piotroski screen shows the nine-signal score can be computed from public filings, so the fields exist publicly. What I did not verify: bulk download terms, XBRL availability back to 2010, filing dates, and restatement/point-in-time behaviour of Screener.in, Trendlyne, Tickertape and moneycontrol. Scraped current-vintage ratios risk look-ahead bias (restated, survivorship-biased); a filing-date table from NSE/BSE announcements is the safe route.
- Lag convention to pre-register: the HXZ result that gross profitability is t 2.62 with one denominator and t 1.04 with another says the information-lag choice can flip a result. Use the filing date; NSE's own quality indices use data cut-offs of 31 May and 30 Nov for June and December reconstitution [P], consistent with FY-end 31 March plus about 60 days for annual results (my inference; I did not verify the SEBI deadline). If filing dates are unavailable, a design choice (not from a source) is to use March-FY annual data no earlier than 1 July.
- Negative findings in one place: (i) HXZ finds MAX, total volatility, IVOL and accruals-type signals insignificant under value-weighted NYSE-breakpoint tests; (ii) BAB net of costs has a 5-factor alpha of 16 bp/month, t 1.20; (iii) long-only low-vol information ratio 0.08-0.17 vs 0.51 value and 0.64 momentum; (iv) Sharma-Chakraborty find no lottery overpricing in India; (v) NSE LV30 lost to Nifty 500 in 5 of 8 live years and to Nifty 50 in 3, and Nifty200 Quality 30 and Midcap150 Quality 50 returned about the same as Nifty 50 over 5 years; (vi) the F-score's US alpha vanishes under the q-model; (vii) the only IIMB paper snippet found on volatility may say high-vol outperforms (unverified, may be about market-level volatility).
- Evidence stops: Indian academic evidence I could read ends March 2021 (JPV); NSE index evidence runs to 30 Sep 2026 but is index-level, partly backfilled and gross of fund costs; I found no 2021-2026 Indian academic test of any of these anomalies.

### Gaps
- Not retrieved, so nothing above relies on them: AHXZ 2006, Blitz-van Vliet 2007, Robeco conservative formula (from memory it ranks on low volatility, 12-1 momentum and net payout yield; unverified and unsourced), Boyer-Mitton-Vorkink 2010, Fama-French 2015 RMW/CMA, Sloan 1996, Cooper-Gulen-Schill 2008, Pontiff-Woodgate 2008, Piotroski 2000, Mohanram 2005, McLean-Pontiff 2016, Jensen-Kelly-Pedersen 2023.
- Indian turnover and fund expense ratios for the NSE factor indices; launch dates for most quality and combined indices; Midcap150 and Smallcap250 benchmark returns.
- Free-source verification (NSE/BSE XBRL back to 2010, Screener.in/Trendlyne/Tickertape/moneycontrol point-in-time behaviour and terms): not done; SEBI result-filing deadlines not verified.
- Whether the repo's corporate-actions file records rights, QIP, preferential allotments and buybacks, with dates: unknown to me; this decides C19 and C24.
- Indian evidence on accruals, asset growth, issuance, RMW/CMA, G-score, skewness: none found; the Indian MAX, MIN, volatility and F-score items are abstract/snippet level only and their effect sizes in bp per month were not retrieved.
- No post-2021 Indian academic replication of any anomaly here; no net-of-cost Indian long-only test of any of them.
