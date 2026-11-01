# Flow, Ownership, Insider and Corporate-Action Signals for NSE Delivery Equities (literature sweep, 2026-11-01)

Scope: days-to-months horizon signals a retail NSE delivery account could run. India evidence first, US/international as benchmark. Cost hurdle used throughout: about 35-40 bp round trip (the covered file gives 33.05 bp delivery round trip at a Rs 33,000 ticket, 39.05 bp with doubled slippage, 60.08 bp at Rs 5,000 — [00-already-covered.md section 6b](00-already-covered.md)). Effect sizes are market-adjusted and gross unless stated. "Read" means I downloaded the paper and read the table; "snippet" means a search-result summary only and the number is unverified against the paper. Computed numbers are marked "(my arithmetic)". Search budget ran out before the analyst, rating-in-India, news, OFS/disinvestment and budget topics; those are in Gaps, not invented.

Overall finding up front: the Indian evidence is thin, old (most samples end 2011-2015) and mostly about the SELL / bad-news side. Only one candidate (insider purchases around earnings) has a gross India number that clears the hurdle on its mean, and its median barely does. Nothing in this sweep reaches the project's pre-registration bar (momentum-family t >= 2.865) on India data. Several items are useful as avoid-list overlays on the existing momentum book rather than as entries.

## 1. Do SEBI PIT insider disclosures (promoter, director, KMP buys and sells) predict returns at tradable horizons in India?

### Takeaway
Indian insider buys do not earn positive market-adjusted returns on average over 1-12 months (2008-2014), the long-short spread comes from the sell side, and the only positive buy-side number is a 5-day post-disclosure CAR (median +59 bp, mean +182 bp) in trades that precede earnings announcements. Nothing is promoter-specific, and nothing post-2015 was found in read form.

### Cited Findings
- Krishnan and Rangan (NSE-IGIDR working paper, 2015/16): Indian insider trades 2008-2014, 22,035 buying days and 9,926 selling days out of 32,576 trading days (the paper's wording; I read them as firm-days). Market-adjusted CAR after trade (days +2 onward): buys -0.20% (1m), -0.48% (3m), -0.82% (6m), -0.90% (12m); sells -0.48%, -1.39%, -4.22%, -7.32%. Buy minus sell: 0.28% (t 1.94), 1.53% (t 3.43), 5.04% (t 8.12), 8.22% (t 10.16). Pre-trade days -64 to -2: buys -3.87%, sells +2.39% (insiders are contrarian). The authors note trades are clustered in time, so the t-stats are likely overstated. — [Krishnan & Rangan, NSE-IGIDR WP 4/14-15](https://nsearchives.nseindia.com/research/content/NSE-IGIDR-WP4-14-15.pdf) (read)
- Brochet, Lee and Srinivasan (2017): Indian insiders 2006-2014; little evidence they trade on near-term earnings news except in value stocks; trades do precede abnormal returns ("fads" more than fundamentals); informed trading is stronger in non-conglomerates, non-government-affiliated firms and low-FII-ownership firms; little evidence of informed trades ahead of M&A. For trades before earnings announcements with reporting dates, the 5-day CAR from the disclosure day has median +0.59% for purchases and -0.41% for sales (Panel D: 3,027 purchases, mean +1.82%, sd 10.80%; 769 sales, mean +0.77%). Most reporting firms are among the larger ones. — [Brochet, Lee & Srinivasan](https://www.stern.nyu.edu/sites/default/files/assets/documents/Brochet%20Lee%20Srinivasan%202017%20-%20The%20Role%20of%20Insider%20Trading%20in%20the%20Market%20Reaction%20to%20Earnings%20News.pdf) (read)
- Deuskar, Khatri and Sunder (2019, preliminary, "do not circulate or cite"): 1,231 insiders, 60,127 trades, 56% buys, built by linking masked BSE trader IDs to insiders. Own-stock purchases earn DGTW-adjusted abnormal profits of about 3% over 3 months and 5.9% over 6 months; the same insiders do better in same-industry stocks than unrelated ones. — [Deuskar, Khatri & Sunder](https://www.stern.nyu.edu/sites/default/files/assets/documents/DKS_Insiders_Other_Trades_201904.pdf) (read; sample years not extracted)
- Kumar (NITK thesis, 2018), snippet only: BSE insider disclosures April 2007 to March 2015; purchase portfolios earn positive and sale portfolios negative four-factor abnormal returns; "outsiders" earn nothing. Magnitudes not read (PDF fetch 404). — [NITK repository](https://idr.nitk.ac.in/handle/123456789/14150) (snippet)
- Enforcement is not a signal: an event study of SEBI adjudication orders and SAT appeals for insider trading finds no statistically significant market reaction (SAT sample only 42 events). — [LEAP blog, May 2026](https://blog.theleapjournal.org/2026/05/market-reaction-to-insider-trading.html) (snippet)
- Leads not read: "Are insider purchases informative? Evidence from Indian firms" (2026) — [Springer](https://link.springer.com/article/10.1007/s40622-026-00473-3) (title only, page not retrievable); Raje, "Estimates of Insider Trading in India" — [SSRN 1210600](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1210600) (title only); Chauhan, Kumar and Chaturvedula (2016) — [J. Multinational Finance](https://ideas.repec.org/a/eee/mulfin/v34y2016icp65-79.html) (title only); "Regulatory reforms, share buyback and institutional monitoring of insider trading: Evidence from India" — [Finance Research Letters](https://www.sciencedirect.com/science/article/abs/pii/S1544612325018483) (title only, 403).
- US benchmarks: Jeng, Metrick and Zeckhauser find insider purchase portfolios earn more than 50 bp per month abnormal returns (raw 10.2% per year over the market, 1975-1996, 563,863 transactions), about one-quarter of it within five days and one-half within a month, with no abnormal return on the sale portfolio. — [JMZ, NBER w6913](https://www.nber.org/papers/w6913) (read). Cohen, Malloy and Pomorski: "opportunistic" insiders (no calendar-month trading pattern) earn 82 bp per month value-weighted abnormal returns, "routine" insiders (about 55% of trades) essentially zero; Thomson Reuters data 1986-2007. — [NBER digest](https://www.nber.org/digest/apr11/decoding-inside-information), [SSRN 1692517](https://papers.ssrn.com/abstract=1692517) (snippet). Lakonishok and Lee (2001) — [RFS](https://ideas.repec.org/a/oup/rfinst/v14y2001i1p79-111.html) (numbers not retrieved).
- Data: NSE publishes PIT disclosures at [nseindia.com PIT page](https://www.nseindia.com/companies-listing/corporate-filings-insider-trading); community code pulls them from the `api/corporates-pit` endpoint with `from_date` and `to_date` (DD-MM-YYYY), which needs a browser-like User-Agent, a Referer and a cookie session — [community gist](https://gist.github.com/Varad2305/41f3064c58e55d859bb079f92a93503f) (unofficial, may have changed). NSE robots.txt reads "Allow: /" with "Disallow: /market-data-test" — [robots.txt](https://www.nseindia.com/robots.txt) (fetched 2026-11-01); I did not read NSE's terms of use.

### Inferences
- The Indian long-short spread of 8.22% at 12 months is mostly an "insider sells predict losers" result (sells -7.32% vs buys -0.90%). For a long-only delivery account, the actionable form is an avoid/exit screen on stocks with heavy insider selling, not a buy list.
- The 5-day pre-earnings purchase CAR is the only buy-side number near tradable size: mean 182 bp and median 59 bp against a 35-40 bp round trip leaves about 144 bp (mean) or 21 bp (median) before entry lag, which is a thin and skewed margin (sd 10.8%).
- All India samples end by 2015 and predate the 2015 PIT Regulations (date recalled, see Gaps), so none of it is out of sample for the current regime.
- Because insider buys are contrarian (down 3.9% in the prior quarter), any insider-buy rule will collide with the momentum book's selection and should be tested as an overlay or a separate sleeve with its own family count.

### Gaps
- No Indian estimate that separates promoter open-market buys from director/KMP buys; no post-2015 read result.
- No Indian replication of the opportunistic vs routine split (needs per-insider multi-year history; NSE PIT back-history depth not verified).
- NSE PIT archive depth, field list (acquirer category, mode of acquisition, pre/post holding) and whether bulk CSV download exists were not verified; only the community API pattern was found.
- The date and content of the SEBI PIT Regulations 2015 (Rs 10 lakh quarterly threshold, 2+2 trading days disclosure) is from memory and unsourced.
- Seyhun (1986/1998) numbers: search budget exhausted before retrieval.

## 2. Do pledges, pledge releases and creeping acquisitions (SAST) predict returns?

### Takeaway
Pledge disclosures are mildly negative or mixed at announcement and are linked to higher crash risk and weaker performance over years; I found no India return numbers for pledge releases or for SAST Reg 29 creeping acquisitions.

### Cited Findings
- Bang, Sonti and Thirumalai (ISB): univariate tests show a negative market reaction to share pledges; in multivariate tests the average reaction is positive and the negativity is driven by promoter characteristics and the stated reason. The listing date (1985) is obviously wrong and no magnitudes were extracted. — [ISB research directory](https://www.isb.edu/faculty-and-research/research-directory/market-reaction-to-share-pledges-evidence-from-india) (snippet)
- Kalia (2024): 257 S&P BSE 500 firms 2011-2020, promoter pledging significantly raises future stock-price crash risk and lowers future financial performance. Chauhan, Mishra and Spahr (2021, Financial Management): 1,452 Indian firms, large pledged fractions raise volatility and lower firm value. — search-result summary only; the exact URLs for these two papers were not retained, and the likely listings are [Emerald JAMR-01-2023-0003](https://emerald.com/insight/content/doi/10.1108/JAMR-01-2023-0003/full/pdf) and [Memphis repository, "Stock pledging and firm risk: Evidence from India"](https://digitalcommons.memphis.edu/facpubs/11664) (mapping of paper to link unconfirmed; underlying papers not opened)
- SAST/creeping acquisition: no Indian return study found.

### Inferences
- Pledging is a risk/avoid flag for a long-only book, with crash-risk framing (rare, large losses), not a short-horizon return forecast.
- A pledge-ratio screen would need quarterly shareholding-pattern data (see section 3) rather than event timing.

### Gaps
- No magnitude, t-stat or horizon for Indian pledge announcement or release returns.
- No India evidence on SAST Reg 29 (5% crossing, 2% change) or creeping-acquisition disclosures; exact NSE/BSE feed for SAST filings not verified.
- "Pledge release is bullish" has no source at all in this run.

## 3. Do institutional flows and ownership changes (FII/DII, shareholding pattern, mutual-fund holdings) predict returns?

### Takeaway
Stock-level FII flows move prices on the day and the sell-side shock partly reverses within a week (+28 bp over 5 days), which does not clear costs; the data is not public at stock level; no India evidence was found for quarterly holding changes or MF "best ideas".

### Cited Findings
- Acharya, Anshuman and Kumar (2014, preliminary): stock-level daily FII purchase and sale data 2006-2011. High-innovation stocks show a coincident, permanent price rise; low-innovation stocks a coincident decline that partly reverses within two weeks. Day-0 differential (high minus low) 1.88% (daily innovation) or 0.81% (cumulative -5..0 innovation). Post-formation window (0,5): low-innovation portfolio +0.28% (panel model) and high-innovation -0.08% (marginal); Q5-Q1 differential -0.36%. Out-of-sample January 2012 to June 2013: Day-0 +0.76% vs -0.79%, differential 1.55%, reversal weaker, only on the low-innovation side. Effect is largest in market stress. — [NSE research BS1.pdf](https://archives.nseindia.com/research/content/BS1.pdf), [IGC summary](https://www.theigc.org/collections/foreign-fund-flows-and-stock-returns-evidence-india) (read)
- Aggregate FPI flows are public by category and sector: [NSDL FPI Monitor](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx), [monthly](https://fpi.nsdl.co.in/web/Reports/Monthly.aspx), [SEBI FPI statistics](https://www.sebi.gov.in/statistics/fpi-investment/latest.html). These are not per-stock. (Pages listed in search results; machine-readability and history depth not verified.)
- The project already rejected FII/DII flows as a market timer ("Reject", Part B rank 11) — [00-already-covered.md](00-already-covered.md).

### Inferences
- The day-0 effect (155-188 bp) cannot be captured by a retail account that sees data after the close; the capturable leg is the post-formation reversal, which is 28 bp (5 days) and is below the 35-40 bp hurdle even gross.
- I cannot tell from the sources whether stock-level daily FII data is available to a retail user at any price; the paper states its stock-wise daily FII data is "proprietary data ... obtained from the National Stock Exchange" ([BS1.pdf](https://archives.nseindia.com/research/content/BS1.pdf)); whether a retail user can buy it is not stated.

### Gaps
- No Indian study found on quarterly shareholding-pattern changes (FII, MF, promoter, public) and next-quarter returns, on MF holdings changes, or on "best ideas" concentration.
- No India study of DII (mutual fund) daily flows as a stock-level signal.
- BSE/NSE shareholding-pattern filing format, lag after quarter end (about 21 days is recalled, unsourced) and history not verified.
- FII flow momentum at the aggregate level in India: no read paper.

## 4. Do buybacks (tender vs open market, completion, the October 2024 tax change) offer a tradable edge?

### Takeaway
Indian buyback announcements carry large [-10,+10] CARs (tender 13.7%, open market 5.3%), but open-market announcements are preceded by sharp price falls, long-run drift is insignificant or negative, and the 2024 tax change collapsed event frequency; with the tax reversed from April 2026 nothing is yet measurable.

### Cited Findings
- Agarwalla, Jacob and Vasudevan (IIMA): 225 buyback announcements to June 2012 (176 open market, 49 tender). Event-window [-10,+10] abnormal return about 7% overall; tender 13.7%, open market 5.3%; prior quarter -8.5% overall, open-market prior -11.7%; small firms 13.7%, large firms insignificant. Long-run buy-and-hold abnormal returns over 1-3 years are insignificant for both types and negative over 3 years for open market, against a US 12.6% annualised size-value abnormal return reported by Ikenberry et al. Tender firms show post-event positive abnormal returns, open-market firms a post-event correction. Open-market buyers underperform operationally and are often used for price support. — [Agarwalla, Jacob & Vasudevan](https://www.iima.ac.in/sites/default/files/rnpfiles/19823076152015-02-01.pdf) (read)
- Srivastava, Jacob and Pandey: SEBI required open-market buybacks to complete at least 50% from 8 August 2013 (195 programs before, 73 after, my reading of their sample table). After the rule, firms' market-timing gains from execution fell, insider purchases rise during execution (stronger signal), and timing-constrained firms are more likely to choose tender offers. — [IIMA WP 2021-04-02](https://iima.ac.in/sites/default/files/rnpfiles/20626518232021-04-02.pdf) (abstract read)
- International: Manconi, Peyer and Vermaelen report significant long-run excess returns after buybacks in the US and many countries (as characterised by Agarwalla et al.; paper numbers not retrieved). — [ECGI working paper](https://www.ecgi.global/sites/default/files/working_papers/documents/finalmanconipeyervermaelen_0.pdf) (not read)
- Tax: from 1 October 2024 to 31 March 2026 buyback proceeds were taxed as deemed dividends in the shareholder's hands (no cost deduction); one secondary report says 38 buybacks worth over Rs 8,000 crore in the previous calendar year versus 4 offers worth Rs 186 crore by 26 June 2025 (the search summary did not say which of the links below carries that figure). From 1 April 2026 the Income Tax Act 2025 restores capital-gains treatment with cost of acquisition deducted. — [Business Standard](https://www.business-standard.com/amp/markets/news/buybacks-grind-to-a-halt-after-tax-burden-shifts-from-firms-to-shareholders-125050500702_1.html), [TaxGuru](https://taxguru.in/income-tax/buy-back-shares-taxability-income-tax-act-2025.html), [Finnovate](https://www.finnovate.in/learn/blog/share-buyback-taxation-india-2025) (secondary; not checked against exchange filings or the Act)
- Project status: "Buyback tender reserve: Leave (grade C, small)"; "buyback/promoter-buy events" listed as untested family in section 4 — [00-already-covered.md](00-already-covered.md).

### Inferences
- The 13.7% tender CAR is dominated by the announcement jump and pre-event drift; the post-event positive abnormal return for tender is the only retail-capturable part, and its size was not extracted (the paper reports the pattern, not a clean per-event number in the passage I read).
- The 2024-26 regime (tax on shareholders) makes pre-2024 event counts a poor guide to future frequency; the post-April-2026 regime has no data yet.

### Gaps
- Size of post-announcement drift in bp (t+1 to t+60) for Indian tender and open-market buybacks; the paper's Table 3 values were not extracted.
- Open-market completion-rate drift in India (Peyer-Vermaelen style) not found.
- The small-shareholder reserve (15%) and acceptance-ratio arithmetic for tender arbitrage is recalled, not sourced.
- Whether the local NSE corporate-actions feed carries a "Buy Back" purpose field (the repo has `backend/data/corp_actions/`) is unchecked.

## 5. Do equity-issuance and lock-in events (rights, FPOs, QIPs, preferential allotments, IPO/anchor expiry, OFS) offer an edge?

### Takeaway
Indian SEO issuers (rights and FPOs) underperform matched peers by 17% over five years; anchor-investor 30-day unlock is followed by price falls when anchors sell more than 10%; QIP, preferential and OFS have no India return evidence in what I could retrieve.

### Cited Findings
- Deb and Kamisetty (NSE WP 15/2015): 144 rights issues and 33 FPOs, 2000-2014; buying at the first-day close and holding five years earned 17% (about 3% annualised) less than matched industry/size/age/P-B firms; pattern mostly independent of market regime. — [NSE WP 15](https://nsearchives.nseindia.com/research/content/res_WorkingPaper15.pdf) (read)
- SEBI study of 242 mainboard IPOs (April 2022 to October 2025): around the 30-day anchor unlock (trading days 29-33) average raw price move is about -0.4% if anchors sell 2.5% or less and about -3.5% (median near -6%) if anchors sell more than 10%; the 90-day unlock has small impact; the report states these are averages, not abnormal returns, and not proof of causation. Aggregate anchor exit by day 30/60/90 is 3.5%/9.3%/18.5% in one summary and 3.2%/8%/17.3% in another; about 51% by day 365; FPIs exit about 60% and mutual funds about 38%. — [TaxGuru](https://taxguru.in/sebi/ipo-anchored-anchor-investors-exit.html), [TeamLease RegTech](https://teamleaseregtech.com/updates/article/58782/sebi-issued-the-study-on-exit-behaviour-of-anchor-investors-in-mainboard-ipo/) (secondary summaries of the SEBI study; the figures disagree slightly)
- Rule structure: anchors face a 30-day lock-in on half their shares and 90 days on the rest — [Business Standard](https://www.business-standard.com/amp/markets/news/anchor-lock-in-expiry-to-unlock-rs-5-300-crore-worth-shares-this-week-125031700066_1.html) (snippet).
- QIPs, preferential allotments, OFS: no Indian event study retrieved. IPO lock-up expiry internationally is negative (Brau, Carter, Christophe and Key 2004) — [Emerald](https://www.emerald.com/insight/content/doi/10.1108/03074350410768859/full/html) (snippet).

### Inferences
- Both findings are avoid-list rules for a long-only account: do not buy rights/FPO issuers for multi-year holds, do not hold new listings through the day-30 unlock window. Neither is a long entry.
- 242 IPOs in about 3.6 years is about 68 per year (my arithmetic), but most are outside a NIFTY-100-to-500 delivery universe at day 30, so the usable count is far lower.

### Gaps
- No India event study of QIPs, preferential allotments to promoters/investors, OFS discounts, or warrant conversions.
- Anchor study: the number of >10%-selling events, abnormal (benchmark-adjusted) returns and t-stats were not available; the SEBI primary document was not opened.
- Net share issuance as a cross-sectional factor in India (Pontiff-Woodgate style): no read paper.

## 6. Do restructuring and credit events (demergers, mergers, open offers, delistings, rating changes) offer an edge?

### Takeaway
Indian demerger announcement CARs are positive (about 5-7% over 5-21 days in small samples) but events are about 2-3 per year and US long-run results are fragile; delisting prices fade back toward pre-announcement levels; rating-change evidence is US-only (downgrades -10 to -14% in year one).

### Cited Findings
- Demergers India: a study of 51 Indian demergers finds about 1.74% average abnormal return at announcement; a study of 24 spin-offs 2009-10 to 2018-19 (market model) reports CAAR 5.088% over (-2,+2) and 6.609% over (-10,+10). A thesis finds only resulting companies gain in the long run. — search-result summary of four listings, number-to-paper mapping unconfirmed: [ICMAI](https://icmai-rnj.in/index.php/maj/article/view/172388), [NMIMS](https://management-review.nmims.edu/wp-content/uploads/2022/03/NMIMS_Issue_1_Jan-March22_Article_7.pdf), [IIMB repository](https://repository.iimb.ac.in/handle/123456789/4028), [Nirma repository](https://repository.nirmauni.ac.in/jspui/handle/123456789/8105?mode=full) (snippets; methods unchecked)
- US spin-offs: Cusatis, Miles and Woolridge (1965-1988) report significantly positive 3-year abnormal returns for spin-offs and parents, attributed to takeovers; McConnell, Ozbilgin and Wahal (2001) find results depend on horizon and benchmark and lean on one outlier. — [SUFE listing](https://academicnewsletter.sufe.edu.cn/info/358257), [IDEAS](https://ideas.repec.org/a/ucp/jnlbus/v74y2001i2p245-80.html) (snippets)
- Delisting India: SEBI's 2018 discussion paper reports seven delistings at the floor price (zero premium) and eight at premiums from 7.69% to 242.02%; law-firm commentary says prices often rise on announcement then pare gains toward pre-announcement levels; no formal event study found. — [SEBI 2018 paper](https://www.sebi.gov.in/sebi_data/attachdocs/jul-2018/1532603980878.pdf), [Cyril Amarchand Mangaldas report](https://www.cyrilshroff.com/publications/voluntary-delisting-current-trends-a-detailed-report) (snippets)
- Rating changes: Dichev and Piotroski (2001, Moody's 1970-1997): no reliable abnormal returns after upgrades; downgrades show about -10 to -14% in the first year, concentrated in small, low-quality firms, partly at subsequent earnings announcements. — [SUFE listing of JF paper](https://academicnewsletter.sufe.edu.cn/info/361535) (abstract via snippet; table values not verified)

### Inferences
- Demerger/spin-off CARs are pre-announcement or announcement-day moves; with 24 events over 10 years (about 2.4 per year, my arithmetic) even a +5% edge adds almost nothing to a diversified book.
- Rating downgrades are most naturally used as an avoid/exit flag; the Indian data feed (CRISIL, ICRA, CARE, India Ratings press releases or exchange filings) is unverified.

### Gaps
- No Indian merger-arbitrage, open-offer (SAST Reg 3/4/5) or delisting-offer return study retrieved; no Indian rating-change event study found (search budget exhausted before this query).
- Demerger evidence is from snippets only; no Table values, benchmark or t-stat verified.

## 7. Do analyst recommendations, target-price revisions, small-cap coverage gaps or news signals predict daily-to-monthly returns in India?

### Takeaway
I found nothing usable: the search budget ran out before these queries, and the project's own record already marks sentiment labels as circular and LLM news checks as "Leave".

### Cited Findings
- NifSent50 labels are "derived from the price move (circular)"; "LLM news check on the book: Leave; forward-only after a memory audit, if ever"; "News-day stocks in play ORB: low prior" — [00-already-covered.md](00-already-covered.md) (local file).

### Inferences
- Any news-sentiment candidate would be new, with no published India daily-return numbers behind it; it should not be ranked above the event candidates in section 9.

### Gaps
- Indian analyst recommendation/target-price event studies, SEBI RA (research analyst) registry data and coverage-gap (neglected-firm) evidence: not searched successfully.
- News-based return evidence for NSE stocks with documented returns (not classifier accuracy): not searched successfully.

## 8. Do government and policy events (PSU disinvestment/OFS, budget-sector effects) offer an edge?

### Takeaway
Not researched successfully (search budget exhausted); the only related finding is that OFS and disinvestment are covered by the issuance item in section 5, where no India return numbers were retrieved.

### Cited Findings
- None retrieved.

### Inferences
- OFS discount and bounce is a plausible short-horizon event but unevidenced here.

### Gaps
- DIPAM/OFS announcement-to-listing returns, budget-day sector returns and PSU disinvestment pipelines: no sources found. NSE OFS window notices and DIPAM press releases are the likely data sources (not verified).

## 9. Candidate catalogue: what could a retail NSE delivery account run, and what clears a 35-40 bp round trip?

### Takeaway
Of 26 candidates, one has an India number that clears the hurdle on its mean (C1), five are better used as avoid-list overlays on the momentum book (C3, C9, C20, C22, C26), three depend on the post-April-2026 buyback regime (C17-C19), and the rest have no India return evidence, are not reproducible with public data, or fail the cost test outright. None meets t >= 2.865 on India data.

### Cited Findings
Format per record: citation; sample; effect (bp); t; events per year in India; holding; gross/net; replication; India evidence; data source; clears 35-40 bp?; overlap. "n/f" = not found.

**C1. Insider purchases around earnings, 5-day post-disclosure drift**
- [Brochet, Lee & Srinivasan 2017](https://www.stern.nyu.edu/sites/default/files/assets/documents/Brochet%20Lee%20Srinivasan%202017%20-%20The%20Role%20of%20Insider%20Trading%20in%20the%20Market%20Reaction%20to%20Earnings%20News.pdf); India 2006-2014, 3,027 purchases (pre-earnings with report dates).
- Effect: mean +182 bp, median +59 bp, 5-day CAR from disclosure day (market-adjusted, gross). t: mean about 8 naive (my arithmetic: 1.82/(10.80/sqrt(3,027))), clustering ignored.
- Events/yr: about 340 (3,027/9, my arithmetic) before liquidity filters. Hold 5 days. Replication: none; sample ends 2014.
- Source: NSE PIT page and `api/corporates-pit` ([NSE](https://www.nseindia.com/companies-listing/corporate-filings-insider-trading), [gist](https://gist.github.com/Varad2305/41f3064c58e55d859bb079f92a93503f)); JSON behind cookies; robots allows; depth unverified.
- Clears? Mean yes (+144 bp net), median marginal (+21 bp net); entry lag not measured. Overlap: "Trial 2, insider buying family N=2, t >= 2.24" never run; L35 (9,586 filings events) did not report PIT classes in the covered file's one-line summary.

**C2. All insider trades, 1-12 month hold (buy leg and sell leg)**
- [Krishnan & Rangan](https://nsearchives.nseindia.com/research/content/NSE-IGIDR-WP4-14-15.pdf); 2008-2014, 22,035 buy and 9,926 sell firm-days (about 3,100 and 1,400 per year, my arithmetic).
- Buy leg: -90 bp at 12 months (market-adjusted), no edge. Sell leg: -732 bp at 12 months (about -61 bp/month, my arithmetic). Buy-sell t 10.16 (clustered, overstated).
- Clears? Buy leg no. Sell leg only as an avoid/exit flag (C3). Overlap: none with closed items.

**C3. Insider-sell avoid/exit screen on the momentum book**
- Same sample as C2; BLS median sale 5-day CAR -41 bp. Gross; no replication; data as C1.
- Clears? Not an entry, so no round trip; value is avoided losses. Test as a non-inferiority overlay (like the low-vol overlay). Overlap: momentum book (core, trial 126).

**C4. Opportunistic vs routine insider classification**
- [Cohen, Malloy & Pomorski](https://papers.ssrn.com/abstract=1692517); US 1986-2007; 82 bp/month value-weighted, equal-weighted higher (not retrieved); post-publication behaviour n/f; India n/f.
- Needs per-insider multi-year PIT history; events/yr unknown. Clears? Unknown. Overlap: refines C1/C6.

**C5. Insider cluster buying / officer buys in small caps**
- [Jeng, Metrick & Zeckhauser](https://www.nber.org/papers/w6913): US 1975-1996, more than 50 bp/month, 25% in first five days; stronger in small firms. India n/f. Clears? Unknown.

**C6. Promoter open-market buys (section-4 priority)**
- No India study isolating promoters; closest are C1/C2 (all insiders) and the NITK thesis (insiders; snippet). Events/yr unknown (needs PIT filter on category "Promoter"). Clears? Unknown. Overlap: "Trial 2" untested; would be one trial in a new family and would raise the count of record.

**C7. Insider trades in related stocks**
- [Deuskar, Khatri & Sunder](https://www.stern.nyu.edu/sites/default/files/assets/documents/DKS_Insiders_Other_Trades_201904.pdf): preliminary; own-stock purchases about 3% (3m), 5.9% (6m) DGTW; uses masked BSE trader IDs not public. Clears? Not reproducible with public data.

**C8. SAST Reg 29 / creeping acquisitions / open-offer triggers**
- n/f. Data: NSE/BSE SAST filings (feed not verified). Clears? Unknown.

**C9. Promoter pledge creation as avoid flag**
- [Bang, Sonti & Thirumalai (ISB)](https://www.isb.edu/faculty-and-research/research-directory/market-reaction-to-share-pledges-evidence-from-india) mixed announcement reaction; Kalia 2024 crash risk (snippets). No bp. Data: quarterly shareholding pattern and Reg 31 filings. Clears? Avoid-list only.

**C10. Pledge release as buy signal**
- n/f. Clears? Unknown.

**C11. Insider-enforcement news (SEBI orders, SAT)**
- [LEAP 2026](https://blog.theleapjournal.org/2026/05/market-reaction-to-insider-trading.html): no significant reaction. Negative finding; not a candidate.

**C12. Stock-level FII flow reversal (buy FII-sold stocks for 5 days)**
- [Acharya, Anshuman & Kumar](https://archives.nseindia.com/research/content/BS1.pdf); 2006-2011 plus OOS 2012-13; +28 bp (0,5) low-innovation; t not extracted. Data proprietary stock-level. Clears? No (28 bp < 35-40 bp gross).

**C13. Stock-level FII flow momentum (day 0)**
- Same paper; 155-188 bp day-0 differential, coincident, not capturable after the close; largest in stress. Clears? Not tradable.

**C14. Aggregate FPI/DII daily flows as market timer**
- [NSDL FPI Monitor](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx); no new evidence; project rejected (Part B rank 11). Clears? No (already closed).

**C15. Quarterly shareholding-pattern changes (FII/MF/promoter)**
- n/f. Data: exchange shareholding filings (quarterly, lag unverified). Events: 4 dates/yr x universe. Clears? Unknown.

**C16. Mutual-fund holding changes / best ideas**
- n/f for India. Data: AMFI/fund monthly portfolio disclosures (not verified). Clears? Unknown.

**C17. Tender-offer buyback event**
- [Agarwalla et al.](https://www.iima.ac.in/sites/default/files/rnpfiles/19823076152015-02-01.pdf); 49 tender announcements to 2012; [-10,+10] 1,370 bp, post-event positive; t n/f. Events/yr: 38 buybacks in 2024, 4 by June 2025 (secondary). Hold ~1-3 months. Replication: n/f. Source: NSE announcements/SEBI offer documents; corp_actions feed unchecked. Clears? Gross maybe, but capturable post-announcement share unmeasured. Overlap: "Buyback tender reserve: Leave (grade C, small)".

**C18. Open-market buyback announcement**
- Same paper; 176 announcements; [-10,+10] 530 bp, prior -11.7%, long-run negative over 3 years. Fails as long entry (overreaction). Overlap: untested family.

**C19. Buyback completion / min-50% rule effect**
- [Srivastava, Jacob & Pandey](https://iima.ac.in/sites/default/files/rnpfiles/20626518232021-04-02.pdf); post-2013 data; qualitative, no bp extracted. Clears? Unknown.

**C20. Avoid rights/FPO issuers**
- [Deb & Kamisetty](https://nsearchives.nseindia.com/research/content/res_WorkingPaper15.pdf): -17% over 5 years vs matched peers. 177 events 2000-2014 (about 12 per year, my arithmetic). Paper states 17% total, about 3% annualised, so the per-year figure is not a simple division. Avoid-list only.

**C21. QIP / preferential allotment**
- n/f. Clears? Unknown.

**C22. Anchor 30-day lock-in expiry (avoid holding through)**
- [SEBI study via TaxGuru](https://taxguru.in/sebi/ipo-anchored-anchor-investors-exit.html): -350 bp average (raw) if anchors sell >10%, -40 bp if <=2.5%. About 68 IPOs per year (my arithmetic). Avoid rule only; the anchor sale size is not known in advance. Replication: n/a (single 2022-25 sample).

**C23. IPO lock-up expiry (non-anchor promoters/pre-IPO)**
- International negative expiry-day abnormal returns (Brau et al., snippet); India n/f.

**C24. Demerger / spin-off**
- India: +509 bp (-2,+2), +661 bp (-10,+10), 24 events 2009-2019 (snippet). Events about 2.4/yr. US long-run fragile (McConnell et al.). Clears? Too rare; announcement jump not capturable.

**C25. Delisting / open-offer special situations**
- [SEBI 2018](https://www.sebi.gov.in/sebi_data/attachdocs/jul-2018/1532603980878.pdf): floor-price outcomes 7, premium outcomes 8 (7.69% to 242.02%); price fades after announcement. Too rare; no event study.

**C26. Credit-rating downgrade as avoid flag / upgrade as buy**
- [Dichev & Piotroski](https://academicnewsletter.sufe.edu.cn/info/361535): US downgrades -10 to -14% first year; upgrades none; India n/f. Avoid-list only.

**Cross-cutting notes**
- Post-publication decay: McLean and Pontiff's working paper reports about 35% average post-publication decay across 82 characteristics (May 2013 version); the published JF version's figures (26% out-of-sample, 58% post-publication) are recalled and unverified. Apply a haircut of one-third or more to US-derived sizes. — [McLean & Pontiff WP](https://ivey.uwo.ca/media/3775549/pontiff.pdf)
- Machine-readability summary: NSE PIT (JSON, cookie session, unofficial); nsearchives.nseindia.com and bseindia.com robots.txt requests returned HTML pages rather than a robots file (no rules readable); NSDL FPI and SEBI FPI pages are HTML reports (aggregate only).

### Inferences
- If the project spends one pre-registered trial on this sweep, C1 (pre-earnings insider purchases, disclosure-day entry) is the only candidate with an India number above the hurdle, and it needs a PIT history pull and a measure of entry lag first; the covered file's family-N rules mean it would count as a new family or add to "insider buying" (N=2).
- The avoid-list items (C3, C9, C20, C22, C26) share one design: a non-inferiority overlay that drops flagged names from the momentum book. They need no round trips of their own but need the same filings history.
- The buyback family (C17-C19) is the other priority named in section 4 of the covered file, but its India frequency collapsed in 2024-26 and the reversal from April 2026 has produced no measurable sample.

### Gaps
- Per-candidate t-stats for most India results are not extracted; only Krishnan-Rangan reports t-values in the retrieved tables.
- Events-per-year are arithmetic from sample sizes or secondary news, not counted from current exchange data.
- Licence terms for NSE/BSE data re-use were not read; robots.txt is not a licence.
- Post-2015 (PIT 2015 regime) Indian performance of insider-based signals is unmeasured in anything I read.
- Analyst, news, OFS/disinvestment, budget and India rating-change candidates (C26 India side) have no retrieved evidence; the web-search budget for this session was exhausted.
