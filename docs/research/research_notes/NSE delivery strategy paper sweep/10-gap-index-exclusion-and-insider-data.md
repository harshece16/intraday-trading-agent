# Index-exclusion / inclusion and insider-purchase strategies on NSE: literature and data feasibility

Scope: two strategies flagged by the prior sweep as having the largest documented Indian effect sizes but thin evidence. (A) Long-only buying after exclusion from Nifty 50 / Next 50 / 100 / 500, plus the mirror inclusion effect. (B) Buying after disclosed insider/promoter open-market purchases under SEBI PIT rules. Date of research: 2026-11-01. Tags: [P] number read in the primary source text; [S] secondary (abstract, search summary, Wikipedia, blog); [C] my own arithmetic. Cost bar used throughout: 33.05 bp delivery round trip at a Rs 33,000 ticket, 39.05 bp with doubled slippage, 60.08 bp at Rs 5,000 (project note 00-already-covered.md, quoted in the assignment). Prior sweep notes relied on for candidates: [04-calendar-and-index-events.md](04-calendar-and-index-events.md) (index events, C21/C22) and [05-flows-insider-corporate-actions.md](05-flows-insider-corporate-actions.md) (insider candidates C1-C7; it is also where the unofficial NSE PIT API gist and the NSE insider-trading page were first cited). Downloaded files sit in the scratchpad (`/private/tmp/claude-501/-Users-harshgupta/13d79bc2-a7ee-412d-a857-9f750c4239cd/scratchpad/`, sub-folders `indexchanges/`, `papers/`, `pit/`, `terms/`) and were treated as untrusted data (parsed with `python3 -I`, never executed).

## Part A1. Is a post-exclusion rebound in India a documented, long-only, net-of-cost tradeable effect?

### Takeaway
Not established. The only paper claiming a rebound (Chhatwani 2020, +4 to +7% over 60-240 days) I could read only at abstract level, while the one primary Indian paper I could read that studies clean Nifty deletions (Parthasarathy 2019, 28 deletions 2009-2018) finds the opposite: a permanent negative drift and no bounce in the 10 days after the effective date. Even if the rebound were real, Nifty 50 has only about 3 exclusions a year, so it cannot be validated or traded as a standalone strategy.

### Cited Findings
- Chhatwani (2020), JCAR 9(4), "Price and Volume Effects of Nifty 50 Index Reorganization": brief states +4-7% over 60-240 days after exclusion. I could access only the abstract page; the full-text link (publishingindia.com/downloads/6125.pdf) returned an HTML 404 and the journal is subscription-only, so sample years, event count, benchmark and t-stats are NOT verified [S] — [Publishing India abstract page](https://publishingindia.com/archive/jcar/price-and-volume-effects-of-nifty-50-index-reorganization); [i-scholar mirror](https://mail.i-scholar.in/index.php/jcar/article/view/206932)
- Parthasarathy (2019), Int. J. Accounting and Financial Reporting 9(3), Nifty reconstitutions 2009-2018: 36 stocks added/deleted in the raw sample; clean sample (no merger/spin-off/name change, at least one year of history) = 30 additions and 28 deletions; announcement-to-inclusion gap 18-29 days, mean about 25 days (NSE "normally makes the announcement four weeks before") [P] — [IJAFR 15320](https://macrothink.org/journal/index.php/ijafr/article/view/15320)
- Same paper, deletions (three abnormal-return methods labelled MCAR / CCAR / OCAR in the paper; I did not record their exact definitions): announcement-window CAR -2.12% / -2.33% / -2.01%; effective-day window -0.96% / -1.86% / -1.60%; AD40 -3.33% / -3.81% / -3.62%; AD60 -8.26% / -8.52% / -7.50%, all described as statistically significant (t-stats not in the text extract I read) [P]. Authors conclude "long term, permanent, negative abnormal return following index deletion announcements" and that the evidence favours the downward-sloping-demand-curve hypothesis — [IJAFR 15320](https://macrothink.org/journal/index.php/ijafr/article/view/15320)
- Same paper, Table 4, deletions: cumulative mean CAR from ED+1 to ED+T is -0.54% at T=1, +0.14% at T=3, +0.84% at T=5 (peak), +0.18% at T=10 [P]. So there is no measurable post-effective-date rebound over 10 days; significance not shown for these cells — [IJAFR 15320](https://macrothink.org/journal/index.php/ijafr/article/view/15320)
- Same paper, additions (30 events): announcement-window CAR +1.73% / +1.67% / +1.72%; effective-day +1.18% / +1.14% / +1.46%; AD40 +3.01% / +2.74% / +2.96%; the ED+1 to ED+3 window is significantly negative (partial reversal) [P] — [IJAFR 15320](https://macrothink.org/journal/index.php/ijafr/article/view/15320)
- Parthasarathy (2019), Asian J. Finance & Accounting 11(1), additions 2000-2018: abstract says the addition effect is permanent in the full, first (2000-2009) and second (2010-2018) periods "however, the index effect has diminished in the second period", and the second period supports the demand-curve explanation [P, abstract and text read] — [AJFA 14866](https://macrothink.org/journal/index.php/ajfa/article/view/14866)
- Parthasarathy (2010), AJFA 2(2), additions 1999-2010: significant positive permanent abnormal returns around announcement and inclusion; supports neither price pressure nor demand-curve as the main explanation (information effect) [P abstract] — [AJFA 469](https://macrothink.org/journal/index.php/ajfa/article/view/469)
- NSE working paper 90 (comppaper90), "Price and Volume Effects of S&P CNX Nifty Index Reorganizations", 1996-2003 (36 Nifty changes in the initial sample): no price effect on announcement day; Nifty effective-day effect averages 1.47% for inclusions and is "subsequently reversed by ninth day"; "similar results were found for the Nifty deletions too"; no effect for Junior Nifty; supports price pressure, not certification [P abstract and text] — [NSE comppaper90](https://nsearchives.nseindia.com/content/research/comppaper90.pdf)
- Selvam (2012), Global Business Review 13(1): earlier summary of the abstract is that no permanent price effect is found; paywalled, no numbers read [S] — [IDEAS record](https://ideas.repec.org/a/sae/globus/v13y2012i1p39-50.html)
- Joshipura and Janakiramanan (2015), Afro-Asian J. Finance & Accounting 5(1) 21-36: paywalled, abstract only, no event counts or CARs recorded [S] — [IDEAS record](https://ideas.repec.org/a/ids/afasfa/v5y2015i1p21-36.html); [Inderscience](https://www.inderscience.com/filter.php?aid=67824)
- Event count by [C] arithmetic from the Wikipedia replacement table: Nifty 50 exclusions 2010-2025 = 50 over 32 distinct effective dates; per year 2010-2025: 4, 2, 4, 3, 3, 4, 3, 6, 4, 2, 4, 1, 2, 1, 3, 4 [S, Wikipedia] — [NIFTY 50, Wikipedia](https://en.wikipedia.org/wiki/NIFTY_50)
- Secondary commentary on Nifty reshuffles (market-press, not peer reviewed): [Upstox on BSE replacing Wipro in Nifty 50](https://upstox.com/news/market-news/stocks/bse-to-replace-wipro-in-nifty-50-how-index-reshuffles-impact-stock-prices/article-200747/); [Angel One, Nifty 50 rebalancing since 2017](https://angelone.in/blog/analysis-of-nifty50-rebalancing-since-2017). Fetched only as leads; I did not extract numbers from them [S].
- Khatri and Johri (2015), Review of Professional Management, on predictability of Nifty changes: PDF downloaded, not read — [RPM PDF](https://rpm.ndimdelhi.org/doi/pdf/10.1177/rpm.2015.13.1.1.pdf)

### Inferences
- [C] Cost test: Parthasarathy's 10-day post-ED cumulative deletion CAR (+0.18%, peak +0.84%) is 18-84 bp against a 33-39 bp bar. It does not reliably clear, and the sign of the longer drift (AD60 -7.5% to -8.5%, partly measured before the effective date) is against a long entry, not for it. A 60-240 day rebound as Chhatwani reports is not testable from Parthasarathy's table because he reports no window past ED+10 for deletions that I could find.
- [C] Power: 50 Nifty 50 exclusions on 32 dates. If the dispersion of a 60-day abnormal return were about 15% (my assumption, not sourced), SE = 15%/sqrt(50) = 2.1%, so a +5% mean gives t of about 2.4, and about 1.9 if clustering cuts the effective N to 32. So even a true +5% would be borderline significant, many events are forced (merger, demerger), and a clean sample is nearer 28 (Parthasarathy). At about 3 events a year the strategy is a rare-event overlay, not a daily system.
- The conflict (Chhatwani rebound versus Parthasarathy, Kumar-NSE and Selvam) cannot be resolved without Chhatwani's full text. Different windows (60-240 days post effective date versus AD-anchored windows), different benchmark and different sample years are the likely causes; this is an inference, not a verified reason.
- Inclusion (mirror) is better documented in magnitude (about +1.7% announcement window, +3.0% AD40 in 2009-2018, gross) but its tradeable portion for a retail buyer after the announcement is unknown, and the effect diminished in 2010-2018.

### Gaps
- Chhatwani full text (sample years, N, CAR by window, t-stats, benchmark): not accessible; owner could request it via the journal or an institutional login (JCAR vol 9 no 4).
- Joshipura-Janakiramanan 2015 and Selvam 2012 numbers: paywalled.
- No 2016-2026 Nifty/Sensex inclusion/exclusion paper beyond Parthasarathy 2019 found in my searches (the sample ends 2018); nothing covering the 2020-2025 period.
- Post-ED+10 windows (20/60/120/240 days) for Indian deletions: not reported in any paper I could read.
- Whether Nifty announcements are made before or after the close (determines whether a next-open buy captures the announcement-day move): not verified.
- Next 50 / Nifty 100 / Nifty 500 exclusion event studies: none found.

## Part A2. US and global exclusion-reversal evidence and decay with passive ownership

### Takeaway
The US exclusion effect has essentially disappeared: S&P 500 deletion abnormal returns went from -16.6% (1990s) and -12.3% (2000s) to -0.6% in 2010-2020, which is not statistically different from zero, so there is no reversal to harvest there. The classic asymmetry result (additions permanent, deletions temporary) is contested by a 2023 paper that finds symmetry.

### Cited Findings
- Greenwood and Sammon, "The Disappearing Index Effect" (NBER w30748; Journal of Finance 2025): S&P 500 addition announcement abnormal return fell from 3.4% (1980s) and 7.6% (1990s) to 5.2% (2000s) and 0.8% in 2010-2020 (statistically indistinguishable from zero); deletions were -4.6% (1980s), -16.6% (1990s), -12.3% (2000-2009) and -0.6% (2010-2020), also not significant [P], despite rising indexation. In the late 2010s direct additions earned 2.2% while migrations earned -2.3% — [NBER w30748 PDF](https://www.nber.org/system/files/working_papers/w30748/w30748.pdf); [JF 80(2) record](https://ideas.repec.org/a/bla/jfinan/v80y2025i2p657-698.html)
- Chen, Noronha and Singal (2004), Journal of Finance, "The Price Response to S&P 500 Index Additions and Deletions": reported asymmetry, additions permanent and deletions largely temporary (I could read only an abstract mirror; no numbers recorded) [S] — [abstract mirror](https://academicnewsletter.sufe.edu.cn/info/361234)
- Kumar et al. (2023), Journal of Banking & Finance 154: finds the index effect symmetric rather than asymmetric (record only; not read) [S] — [IDEAS record](https://ideas.repec.org/a/eee/jbfina/v154y2023ics0378426623001747.html)
- India-specific decay: Parthasarathy (2019, AJFA) reports the Nifty addition effect diminished in 2010-2018 [P abstract] — [AJFA 14866](https://macrothink.org/journal/index.php/ajfa/article/view/14866)

### Inferences
- A post-deletion reversal in large caps is the kind of effect that arbitrage and passive-fund pre-positioning have already removed in the US; India's smaller index-tracking share (not measured here) is the only reason to expect a residual, and no paper tests that.
- If an Indian reversal exists, the likely sizes are well below Chhatwani's 4-7%; the 2010-2018 evidence points to decay, not growth.

### Gaps
- Petajisto (2011) "The Index Premium and Its Hidden Cost for Index Funds" was not retrieved; not used.
- Chen-Noronha-Singal numbers (t-stats, windows) not read at primary level.
- Passive AUM tracking Nifty 50/Next 50 over time (needed to link decay to indexation in India): not sourced.

## Part A3. Data feasibility: historical Nifty 50 / Next 50 / 100 / 500 change lists with announcement and effective dates

### Takeaway
Feasible and free. niftyindices.com publishes every index press release back to 1998 with a machine-readable date and a PDF per notice, and it did not block a plain browser-User-Agent download. Wikipedia gives a clean Nifty 50-only list (70 exclusion rows 2005-2026). Nifty 50 exclusions 2010-2025 = 50. Next 50 counts are only reliable by my parser for 2010-2016.

### Cited Findings
- Master list: [niftyindices.com press-release page](https://www.niftyindices.com/press-release) returned a static HTML list of 1,525 press releases (1998 to 2026) with date, PDF link and title; saved at `.../scratchpad/indexchanges/nifty_pr/press-release.html` and parsed to `.../indexchanges/press_releases_parsed.tsv` (date, PDF filename, title) [P, my fetch]. Review/replacement titles carry the index and the effective date; the release date is the announcement date.
- PDF URL pattern: `https://www.niftyindices.com/Press_Release/ind_prsDDMMYYYY.pdf` (suffix `_1`, `_2` when several notices in one day) [P, my fetch]. 339 equity index change/replacement releases were identified for 2010-2025 (by year 2010-2025: 14, 17, 9, 17, 8, 11, 7, 26, 59, 63, 26, 10, 16, 15, 22, 19) [C]; 338 PDFs were on disk at the last count, 318 converted to text (`.../indexchanges/pdfs/`, `.../indexchanges/txt/`). Old-format notices list one index per page; later ones list per-index tables (Nifty 50, Next 50, 100, 200, 500 and sectoral) with company name, symbol, excluded/included, effective date and rule text. No ISIN column was checked.
- Wikipedia replacement table (https://en.wikipedia.org/wiki/NIFTY_50): date (effective), excluded company, included company; first row 25 Feb 2005; extracted to `.../indexchanges/wiki_events_filled.tsv`. It carries effective dates only, so announcement dates must come from the press-release list [P, my fetch; S for content] — [NIFTY 50, Wikipedia](https://en.wikipedia.org/wiki/NIFTY_50)
- Nifty 50 exclusions per year, Wikipedia, 2010-2025: 2010:4, 2011:2, 2012:4, 2013:3, 2014:3, 2015:4, 2016:3, 2017:6, 2018:4, 2019:2, 2020:4, 2021:1, 2022:2, 2023:1, 2024:3, 2025:4; total 50 over 32 distinct effective dates [C]
- My PDF-text parser agrees with Wikipedia for Nifty 50 in 2010-2016 and 2021-2023 only; it over-counts 2017-2020 and mis-reads 2024-2025 (format changes, and the 2025 PDFs were not yet on disk) [C]. Treat Wikipedia as authoritative for Nifty 50.
- Next 50 exclusions per year by parser (2010-2016 reliable; the 2016 value of 19 is higher than neighbours and I did not verify it): 8, 8, 9, 6, 5, 9, 19 = 64 [C]. 2017-2024 parser output (11, 13, 10, 11, 8, 15, 6, 5) is NOT verified. Nifty 100 parser output is similar in size; Nifty 500 parser output ranges from 18 to 231 per year and is unreliable (the 2020 figure of 231 is almost certainly inflated by the format).
- Announcement-to-effective gap: about 4 weeks, 18-29 days, mean about 25 trading days in 2009-2018 [P] — [IJAFR 15320](https://macrothink.org/journal/index.php/ijafr/article/view/15320)
- Access: niftyindices.com and Wikipedia served pages with a browser User-Agent; no block encountered. The niftyindices terms of use (https://niftyindices.com/terms-of-use) were not read; the search excerpt did not show a scraping clause [S].

### Inferences
- A one-off, auditable build of an event table (index, symbol, announcement date, effective date, excluded or included) is a few hours of PDF parsing, but only the Nifty 50 list is already clean. Next 50 would need a better per-heading parser or manual checks for 2017-2025.
- Event counts: Nifty 50 about 3 a year, Next 50 about 5-9 a year in 2010-2015, so a combined Nifty 50 + Next 50 exclusion sample over 2010-2025 would be roughly 50 + 100 to 130 [C, rough; Next 50 2017+ unverified]. That is enough for a descriptive study but not for a strong long-only claim, and Next 50 names have higher costs than the Nifty 50.

### Gaps
- NSE or niftyindices machine-readable constituent-history file (CSV with both dates): not found; the press-release PDFs are the source.
- Classification of exclusions into forced (merger/demerger/delisting) versus rule-based (market-cap rank) deletions: not done; matters for the clean sample (Parthasarathy's clean N is 28 of 36).
- Next 50 / 100 / 500 per-year exclusion counts 2017-2025: parser unreliable, not verified.

## Part B1. India evidence on returns after insider/promoter open-market purchase disclosures

### Takeaway
The Indian evidence is positive at the five-day disclosure window for pre-earnings purchases (Brochet-Lee-Srinivasan: mean +182 bp, median +59 bp, N=3,027, driven by promoters) but weak or negative on a long-only basis over 1-12 months (Krishnan-Rangan: insider-buy days earn -0.20% to -0.90% market-adjusted, the signal lives on the sell side). Both are 2006-2014 samples under the older disclosure regime; no peer-reviewed post-2015 PIT study was found.

### Cited Findings
- Brochet, Lee and Srinivasan (2017), "The Role of Insider Trading in the Market Reaction to Earnings News" (NYU Stern-NSE initiative): sample 2006-2014 (insider data not available before 2006), 19,259 firm-year earnings announcements; insider transactions reported in only about a quarter of firm-years; data from Prowess, Compustat Global and SEBI-reported insider trades [P] — [BLS PDF](https://www.stern.nyu.edu/sites/default/files/assets/documents/Brochet%20Lee%20Srinivasan%202017%20-%20The%20Role%20of%20Insider%20Trading%20in%20the%20Market%20Reaction%20to%20Earnings%20News.pdf)
- BLS Panel D (reporting-date analysis): CAR_BUY is the five-day market-adjusted cumulative abnormal return "starting from the day an insider purchase (sale) is reported through SEBI"; several trades reported on one date are one event. Purchases: N=3,027, mean +1.82%, SD 10.80%, 25th percentile -4.21%, median +0.59%, 75th percentile +6.01%. Sales: N=769, mean +0.77%, median -0.41% [P]
- BLS "pre-earnings" subset: the event is the disclosure date of an open-market insider purchase or sale made between fiscal year end and the earnings broadcast date; BUY indicator is one if the number of open-market purchases exceeds sales in that window [P]
- BLS: a significantly positive BUY coefficient and negative SELL coefficient on the 30-day post-announcement return (starting day +2), i.e. pre-announcement insider purchases are profitable and information keeps arriving after earnings; the main results are driven by promoters, whose annual net purchases precede greater abnormal returns, and promoters report more transactions and buy more than they sell, unlike non-promoters. For non-promoters the coefficients are directionally similar but the extract I read cuts off before stating significance [P]
- Krishnan and Rangan, NSE-IGIDR working paper, 2008-2014 (18,269 quarterly earnings announcements by 1,398 NSE firms; 32,576 insider trading days, 22,035 buy days and 9,926 sell days; median trade 20,000 shares, median value Rs 1.8 million, median 0.03% of shares outstanding) [P] — [NSE-IGIDR WP 4/14-15](https://nsearchives.nseindia.com/research/content/NSE-IGIDR-WP4-14-15.pdf)
- KR Table 6 Panel A, mean market-adjusted CAR measured from day +2 after the insider trade date: buys -0.20% (days +2 to +22), -0.48% (+2 to +64), -0.82% (+2 to +127), -0.90% (+2 to +253); sells -0.48%, -1.39%, -4.22%, -7.32%; buy minus sell +0.28% (t=1.94), +1.53% (t=3.43), +5.04% (t=8.12), +8.22% (t=10.16); mean CAR in the 3 months BEFORE buys is -3.87% and before sells +2.39% (contrarian). The authors caution that trades are clustered in time and "hesitate to emphasize" the t-statistics [P]
- KR pre-earnings link: net insider buying in days -64 to -2 (scaled by shares outstanding) predicts unexpected earnings with coefficient 0.09, t=2.29; scaled by promoter holdings 0.03, t=1.46 (not significant) [P]. They call this "modest evidence" and do not claim it is tradeable.
- Anil Kumar M. (2018), NITK PhD thesis "An Empirical Analysis of Legal Insider Trading in India": BSE-filed insider disclosures April 2007 to March 2015, four-factor model plus event study; per a search summary, insider-purchase portfolios earn positive abnormal returns, sale portfolios negative, and outsiders earn none; both also show positive pre-event returns. I could not download the PDF (404) so no numbers [S] — [NITK repository record](https://idr.nitk.ac.in/handle/123456789/14150)
- Gupta, Patel and Sane (2026), enforcement-announcement event study (SEBI final orders N=176, SAT decisions N=42, NSE firms 2009-2023): no significant market reaction to insider-trading enforcement; irrelevant to buy returns, noted so it is not mistaken for PIT-buy evidence [S] — [LEAP blog](https://blog.theleapjournal.org/2026/05/market-reaction-to-insider-trading.html)

### Inferences
- [C] BLS events per year: 3,027 pre-earnings purchase-disclosure events over 2006-2014 (9 years) is about 336 a year; KR buy trading-days about 3,500 a year (22,035 over 25 quarters). These are order-of-magnitude, definitions differ, and KR buy days probably include non-open-market acquisitions (not verified).
- [C] Naive t for BLS mean: 1.82 / (10.80 / sqrt(3027)) = 9.3, but events cluster by firm and date, so the true t is lower; BLS's own clustered statistic for this cell was not captured. Per-event Sharpe is 1.82/10.80 = 0.17 over five days, i.e. a mean dominated by a fat right tail (median is a third of the mean).
- BLS (positive after disclosure, pre-earnings subset, window starts on the disclosure day) and KR (negative long-only drift from trade day +2) are not contradictory: a short pop around disclosure, then drift that is below the market for the average buy. The long-short spread in KR comes mostly from sells (-7.32% over 12 months), which a delivery-only long book cannot use.
- Both samples are before the May 2015 PIT regime (disclosure rules and categories changed); extrapolating the numbers to 2016-2026 is untested.

### Gaps
- BLS clustered t-statistic for CAR_BUY, the promoter-only CAR, the number of promoter purchase events, and any buy-size threshold: not extracted (the paper uses trade size as a share of shares outstanding, median 0.06%, mean 0.38% for purchases, not a rupee threshold).
- KR: no promoter-only or open-market-only split of Table 6 found in the text I read; the insider definition covers promoters and other persons (promoters, directors, officers and 5%+ holders); exact composition of "buys" not confirmed.
- Any 2015-2026 peer-reviewed India paper on promoter open-market buys under the 2015 PIT regime: none found. Leads from the earlier sweep that I did not read: Deuskar-Khatri-Sunder NYU Stern working paper ([PDF](https://www.stern.nyu.edu/sites/default/files/assets/documents/DKS_Insiders_Other_Trades_201904.pdf)), a Springer 2026 article (s40622-026-00473-3), a Finance Research Letters 2025 article, Chauhan-Kumar-Chaturvedula (2016), Raje (SSRN 1210600).
- Whether the BLS CAR day 0 return is earned before or after the market learns the disclosure (disclosures broadcast after market close in my sample) is not stated.

## Part B2. Newest US evidence and its read-across

### Takeaway
US evidence says what separates a profitable insider purchase from noise is opportunistic versus routine timing and, secondarily, cluster size and firm size, and I found no study that directly measures post-2010 decay. Evidence quality for the cluster and small-cap points from this search is weak (secondary summaries).

### Cited Findings
- Cohen, Malloy and Pomorski (2012), Journal of Finance 67(3) 1009-1043 (NBER w16454): a strategy on opportunistic insider trades earns value-weighted abnormal returns of 82 bp per month while routine trades earn about zero; routine insiders are those who trade in the same calendar month for at least a few years running and make up about 55% of insider trades; an AQR summary gives equal-weighted 180 bp per month for the opportunistic portfolio [S, from search summaries; paper not opened] — [NBER w16454](https://www.nber.org/papers/w16454); [HBS Working Knowledge summary](https://hbswk.hbs.edu/item/decoding-inside-information)
- Cluster buys: one blog-level summary reports purchases within two days of another insider purchase followed by about 2.1% abnormal return in the next month, and a small-cap cluster study of 7.4% over 12 months; both secondhand, no sample period or benchmark [S, weak] — [Interactive Brokers Campus review](https://www.interactivebrokers.com/campus/traders-insight/securities/stocks/what-corporate-insider-buying-can-tell-investors-evidence-from-academic-research/)
- Size: per the same secondary source Lakonishok and Lee (2001) find the buy-sell gap largest in small stocks, while Jeng, Metrick and Zeckhauser (2003) find no statistically significant size difference; about a quarter of the gains accrue within five days of the trade [S, weak] — [Interactive Brokers Campus review](https://www.interactivebrokers.com/campus/traders-insight/securities/stocks/what-corporate-insider-buying-can-tell-investors-evidence-from-academic-research/)
- A 2022-2024 Swedish event study finds small-cap firms with higher CARs after insider purchases [S, student-level source, weak] — [Lund University record](https://www.lunduniversity.lu.se/lup/publication/7793807)

### Inferences
- Read-across to India: the opportunistic/routine filter needs several years of per-insider trade history in the PIT feed (the `acqName` field and a calendar-month history make it computable) and is not tested in India. Promoter open-market buying is not "routine" in the CMP sense for most promoters, which fits BLS's finding that promoters drive the result, but this is an inference.
- Front-loading (a quarter of the US gain in five days) combined with an India reporting lag of up to about three weekdays means a meaningful share of the pop may be gone at the next open after the broadcast.

### Gaps
- Primary-source decay evidence for US insider purchases after 2010: not found.
- Jeng-Metrick-Zeckhauser, Lakonishok-Lee and the cluster/small-cap figures are from secondary summaries; verify before quoting in the final report.
- Cost-adjusted (net) US insider-purchase returns: none found.

## Part B3. Data feasibility: NSE PIT disclosures, history depth, fields, terms of use

### Takeaway
Technically feasible: one `api/corporates-pit` request for 1-7 Feb 2016 returned HTTP 200 with 418 rows and 32 fields, including trade date, intimation date and exchange broadcast timestamp. Contractually it is not: NSE's Terms of Use prohibit "systematic or automated data collection", so a bulk history pull needs written permission or a manual download through the NSE page.

### Cited Findings
- One fetch done (as instructed): a homepage GET with a browser User-Agent returned HTTP 403 (368 bytes), then a single `GET https://www.nseindia.com/api/corporates-pit?index=equities&from_date=01-02-2016&to_date=07-02-2016` with a Chrome User-Agent, `Referer: https://www.nseindia.com/companies-listing/corporate-filings-insider-trading` and `Accept: application/json` returned HTTP 200, `application/json`, 311,463 bytes; saved to `.../scratchpad/pit/pit_feb2016.json` [P, my fetch]. The cookie jar held no usable session (the homepage was refused), so cookies were not needed for this one call from this IP; I did not test whether they become necessary under repeated use.
- Result: 418 rows with broadcast timestamps from 01 Feb 2016 09:23 to 05 Feb 2016 19:13 (7 Feb 2016 was a Sunday) [P, my fetch]. Top-level keys `acqNameList` (distinct acquirer names) and `data`. Fields per row: `symbol`, `company`, `acqName`, `personCategory`, `acqMode`, `tdpTransactionType`, `secType`, `secAcq` (quantity), `secVal` (value, Rs), `buyQuantity`, `buyValue`, `sellquantity`, `sellValue`, `befAcqSharesNo/Per`, `afterAcqSharesNo/Per`, `acqfromDt`, `acqtoDt` (transaction dates), `intimDt` (intimation date), `date` (exchange broadcast datetime), `exchange`, `anex`, `derivativeType`, `tdpDerivativeContractType`, `securitiesTypePost`, `remarks`, `xbrl`, `xbrlFileSize`, `pid`, `did`, `tkdAcqm`.
- Category values in that week: Employees/Designated Employees 241, Promoters 93, Other 44, Director 18, Key Managerial Personnel 16, Immediate relative 6. Mode values: Market Sale 171, ESOP 93, Market Purchase 64, Pledge Creation 34, Revokation of Pledge 21, Inter-se-Transfer 10, Gift 9, others 16. Exchange field takes NSE, BSE, `BSE,NSE` and others, so the feed is not NSE-only [C on my file].
- Promoter open-market buys that week: 47 rows (21 symbols; 37 symbol-days after aggregating), median value per symbol-day Rs 39.8 lakh, 81% at or above Rs 10 lakh; all market-purchase rows 64 (29 symbols) [C]. One week in the Q3-results season is not an annual rate.
- Disclosure lag in that sample [C]: for 55 director/KMP/promoter market-purchase rows, weekdays from the transaction end date to the exchange broadcast date: median 2 (0 days: 1 row; 1: 14; 2: 23; 3: 9; 4: 3; 6: 2; and 3 rows at 44 weekdays, i.e. late filings); 38 of 55 (69%) at 2 or fewer, 47 of 55 (85%) at 3 or fewer. Holidays were not removed.
- NSE Terms of Use clause (quoted verbatim, page marked "Updated on: 29/10/2025"): "User is prohibited to conduct any systematic or automated data collection activities (including scraping, data mining, data extraction and data harvesting) on or in relation to our Website / Mobile Application." The same page also states that content or data on the site shall not be "copied, modified, reverse engineer, reproduced, uploaded, transmitted, posted, stored (either in hardcopy or in an electronic retrieval system) ... without prior written permission" [P, my fetch] — [NSE Terms of Use](https://www.nseindia.com/static/nse-terms-of-use)
- `https://www.nseindia.com/robots.txt` (96 bytes): `User-agent: * Allow: / Disallow: /market-data-test`. robots.txt does not override the Terms of Use [P, my fetch] — [NSE robots.txt](https://www.nseindia.com/robots.txt)
- The user-facing page the owner can open to inspect or manually export a date range: [NSE corporate filings, insider trading](https://www.nseindia.com/companies-listing/corporate-filings-insider-trading). The unofficial gist describing the API call (cookie priming, headers) is [Varad2305 gist](https://gist.github.com/Varad2305/41f3064c58e55d859bb079f92a93503f) (from the earlier sweep note 05; not re-verified).
- Third-party archives: Trendlyne shows per-company "Insider Trading & SAST disclosures" with holder, category (promoter, promoter group), acquisition or disposal, date and post-transaction holding, plus pledges and block deals in the same tables; alerts and screeners on insider/SAST parameters exist; export format and plan limits unknown [S] — [Trendlyne help](https://help.trendlyne.com/support/solutions/articles/84000348381-insider-trading-sast-trades-of-superstar-investors); example page [Trendlyne, Den Networks](https://trendlyne.com/equity/insider-trading-sast/all/DEN/322/den-networks-ltd/)

### Inferences
- [C] Storage and effort if one built a decade of history: one week is about 0.3 MB and 418 rows; 520 weeks is about 160 MB and about 220,000 rows at that week's rate, but that is a single-week extrapolation and Q3-results weeks may be above the annual average.
- The feed has the three dates needed for the entry-lag analysis (trade date, intimation date, broadcast datetime), which most third-party pages do not show in one table.
- Given the Terms of Use, the sensible routes are: ask NSE for written permission, use NSE Data and Analytics' licensed products, or have the owner export ranges manually from the NSE page. Bulk scripted pulls should not be run on the strength of this feasibility test.

### Gaps
- History depth (first available date) and maximum date range per request: not tested (no loops allowed); only that Feb 2016 works. The PIT regime start (May 2015) is not independently sourced here.
- Rate limits and whether cookies become necessary under repeated calls: untested.
- BSE insider-disclosure page and archive depth: not checked.
- Tickertape, StockEdge, moneycontrol and Screener insider pages: not checked; Trendlyne export and plan limits: not found.
- Whether NSE Data and Analytics sells a PIT history product, and at what price: not checked.
- niftyindices.com terms (for Part A3 data): not read.

## Part B4. Entry lag: what the papers measured versus what a retail buyer at the next open can capture

### Takeaway
BLS measures a five-day CAR that starts on the disclosure day itself, so its +182 bp mean and +59 bp median are an upper bound for a buyer who can act only at the next open after the broadcast; KR starts at trade day +2. In the 2016 sample the median trade-to-broadcast lag is 2 weekdays and many broadcasts land after the close, so the earliest realistic retail entry is about 3-4 trading days after the trade.

### Cited Findings
- BLS window: starts "from the day an insider purchase ... is reported" through the exchange/SEBI filing, five days long, market-adjusted; includes the disclosure-day return [P] — [BLS PDF](https://www.stern.nyu.edu/sites/default/files/assets/documents/Brochet%20Lee%20Srinivasan%202017%20-%20The%20Role%20of%20Insider%20Trading%20in%20the%20Market%20Reaction%20to%20Earnings%20News.pdf)
- KR window: horizons start on day +2 relative to the insider trade date, similar to Lakonishok and Lee (2001); they do not measure from the disclosure date [P] — [NSE-IGIDR WP 4/14-15](https://nsearchives.nseindia.com/research/content/NSE-IGIDR-WP4-14-15.pdf)
- Lag in the 1-5 Feb 2016 PIT sample: median 2 weekdays from transaction to broadcast, 69% at 2 or fewer, 85% at 3 or fewer, and example broadcast timestamps of 18:40 and 19:13 (after the 15:30 close), meaning the earliest executable buy is the next session [C on my fetched file `.../scratchpad/pit/pit_feb2016.json`]

### Inferences
- [C] Earliest practical entry for a retail buyer is the open after the broadcast day: trade day + broadcast lag (median 2 weekdays) + 1 session for after-hours broadcasts, so about T+3 to T+4. KR's window (start T+2) therefore partly overlaps the buyer's window but BLS's does not align with it.
- [C] Against the cost bar: BLS mean +182 bp is 4.7x to 5.5x the 33.05-39.05 bp bar, but the median +59 bp is only 1.5x to 1.8x and about 1.0x of the 60.08 bp bar at a Rs 5,000 ticket; any day-0 jump already taken before the next open reduces it further. A realistic net expectation is therefore below the mean and probably near the median or lower; KR's 1-12 month long-only drift is negative.

### Gaps
- No paper measures returns from the next open after the broadcast for India; this is the single number that decides Strategy B and can only be computed by building the PIT event table (needs permitted data access, see Part B3) plus daily NSE prices.
- Timing of broadcasts relative to the close across the full PIT history: only the one 2016 week was examined.

## Cost-bar clearance and verdict (both strategies)

### Takeaway
Neither strategy has demonstrated a long-only net edge. A (post-exclusion rebound) fails on evidence conflict and sample size; B (insider/promoter buys) has a documented gross five-day pop that probably does not survive next-open entry plus costs at the median, and long-only multi-month returns were negative in the other Indian study. Only B is worth a cheap local test, and only if data access is permitted.

### Cited Findings
- A, Nifty 50 exclusion: 50 events 2010-2025 (about 3 a year) [S, Wikipedia]; clean-deletion post-ED+10 cumulative CAR +0.18% (peak +0.84%) [P, Parthasarathy 2019]; AD60 -7.5% to -8.5% [P]; Chhatwani +4-7% over 60-240 days [S, abstract only] — [IJAFR 15320](https://macrothink.org/journal/index.php/ijafr/article/view/15320); [Chhatwani abstract](https://publishingindia.com/archive/jcar/price-and-volume-effects-of-nifty-50-index-reorganization)
- A, inclusion: announcement-window +1.7%, AD40 +3.0%, 30 events 2009-2018 gross [P]; diminished in 2010-2018 [P] — [IJAFR 15320](https://macrothink.org/journal/index.php/ijafr/article/view/15320); [AJFA 14866](https://macrothink.org/journal/index.php/ajfa/article/view/14866)
- B: BLS mean +182 bp / median +59 bp, N=3,027, five days from disclosure, 2006-2014 [P]; KR long-only buys -20 to -90 bp over 1-12 months from trade day +2 [P] — [BLS PDF](https://www.stern.nyu.edu/sites/default/files/assets/documents/Brochet%20Lee%20Srinivasan%202017%20-%20The%20Role%20of%20Insider%20Trading%20in%20the%20Market%20Reaction%20to%20Earnings%20News.pdf); [NSE-IGIDR WP 4/14-15](https://nsearchives.nseindia.com/research/content/NSE-IGIDR-WP4-14-15.pdf)

### Inferences
- A: evidence quality for India is low (abstract-only claim versus contradicting primary paper), data feasibility high, events too few; verdict: do not build as a strategy; at most use the free event list to test Chhatwani's claim once, descriptively.
- B: evidence quality for India is moderate for the five-day pop (one good paper, 2006-2014), data feasibility technical yes but ToS-restricted, entry-lag cut unknown. The decisive test is the next-open CAR from broadcast, split promoter versus others and large versus small trades.
- Each row is stated gross unless noted; none of the cited Indian numbers is net of costs.

### Gaps
- Net-of-cost figures for both strategies: not in any source; only my comparison to the project cost bar.
- All A inclusion/exclusion windows after 2018 and all B windows after 2014: no evidence.
