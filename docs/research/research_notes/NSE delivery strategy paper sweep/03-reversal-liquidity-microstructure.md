# Reversal, Liquidity, Volume and NSE-Microstructure Signals for NSE Delivery Trading

> Reading guide. Scope: a retail, long-only account trading NSE cash equities in delivery (held at least overnight), horizons of days to months. Cost hurdle used throughout: about 35-40 bp per round trip (22 bp charges + about 10 bp slippage + Rs 15.34 DP per sell; 33.05 bp at Rs 33,000 a name, about 41 bp at Rs 3 lakh, about 59 bp at Rs 6,667, 56.1 bp at Rs 5,500, per `00-already-covered.md` section 6). Monthly cost drag = one-sided monthly turnover x round trip (my arithmetic, 37.5 bp used): 91% turnover = about 34 bp/month; 59% = about 22 bp/month; weekly full turnover = about 160 bp/month; annual rebalance = about 3 bp/month; 3-year hold = about 1 bp/month. "C#" numbers candidates (31 in all). Overlap notes cite line numbers in `00-already-covered.md` ("00"). Verdict labels: CLEARS-ON-COST (turnover is low enough), MARGINAL, FAILS-ON-COST, NO-EVIDENCE, NOT-HARVESTABLE, CLOSED-IN-HOUSE. Nothing here is a net, India-specific, post-2010 measured edge: every Indian paper found reports gross figures, and most abstracts give no magnitude. Secondary figures are labelled as such.

## (a) Reversal: what do long-only delivery versions earn after costs, and does the effect survive post-2000 and in India?

### Takeaway
High-turnover reversal (weekly, monthly, residual, industry-relative) is a liquidity-provision return that US data show is wiped out by costs: value-weighted short-run reversal earns +0.37%/month gross and -1.28%/month net, and only a low-volatility, industry-relative version with a buy/hold band stays marginally positive (+0.28%/month net, t 2.41). The Indian evidence is gross-only; the one low-turnover result (3-year contrarian, 1995-2008, long-loser leg +0.49%/month) is the only reversal-type candidate that clears the cost hurdle on turnover, and it rests on a single old sample.

### Cited Findings
- Jegadeesh (1990, J. Finance 45:881-898) one-month reversal is reported by a secondary summary at about 2.49%/month gross in the US; Lehmann (1990, QJE 105:1-28) weekly reversal at about 1.79% per week gross. Both figures are secondary and neither is net of costs — [Quantpedia reversal tag](https://quantpedia.com/strategy-tags/reversal); [Columbia summary of Lehmann](https://business.columbia.edu/sites/default/files-efs/pubfiles/11568/str1.pdf)
- Nagel (2012, RFS 25(7):2005-2039): short-term reversal returns are a proxy for the return to liquidity provision and are predictable with the VIX; industry-portfolio reversals pay off when VIX is high. Magnitudes were not retrievable — [Nagel, Evaporating Liquidity (NBER w17653)](https://nber.org/papers/w17653)
- Avramov-Chordia-Goyal (2006, J. Finance 61(5):2365-2394): reversals are concentrated in high-turnover, low-liquidity stocks, and contrarian profits are smaller than likely transaction costs — [ACG on RePEc](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html)
- Cooper (1999, RFS 12(4):901-935), weekly reversals in large-cap NYSE/AMEX: decreasing-volume stocks reverse more; increasing-volume stocks show weaker reversal and positive autocorrelation. A net-of-cost claim appears only in an academia.edu snippet I did not rely on — [Cooper on RePEc](https://ideas.repec.org/a/oup/rfinst/v12y1999i4p901-35.html)
- Blitz-Huij-Lansdorp-Verbeek (2013, J. Financial Markets 16(3):477-504): residual reversal earns about twice the risk-adjusted return of conventional reversal. Working-paper gross figures 1.34%/month vs 0.97%/month (1926-2008); CXO summary (secondary) says net annual return above 8% with breakeven round-trip friction about 0.56% — [EUR repository](https://repub.eur.nl/pub/40707); [CXO Advisory summary](https://www.cxoadvisory.com/technical-trading/purified-short-term-stock-reversal/)
- Da-Liu-Schaumburg (Management Science 60(3):658-674): the part of reversal not explained by fundamentals or analyst revisions is what is tradable; their enhanced strategy has about 4x the risk-adjusted return (3x in the NY Fed 2011 version, 1982-2009) — [NY Fed SR513](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr513.html); [RePEc](https://econpapers.repec.org/RePEc:fip:fednsr:513)
- Tetlock (2011, RFS 24(5):1481-1512): the return on a stale-news day negatively predicts the next week's return, and individual investors trade more on stale news — [Tetlock on RePEc](https://ideas.repec.org/a/oup/rfinst/v24y2011i5p1481-1512.html)
- Hameed-Mian (2015, JFQA 50(1-2):89-117): industry-relative monthly reversals are larger than market-relative ones, also in large liquid stocks; interpreted as liquidity provision; stronger after market declines and in volatile periods — [Cambridge](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/industries-and-stock-return-reversals/92B5101FBEA7B40717D46DB60913BF41); [RePEc](https://econpapers.repec.org/RePEc:cup:jfinqa:v:50:y:2015:i:1-2:p:89-117_00)
- Novy-Marx & Velikov (2016, RFS 29(1):104-147), Table 3, value-weighted deciles with NYSE breakpoints: short-run reversal gross 0.37%/month (t 1.71), one-sided monthly turnover 90.9%, trading costs 1.65, net -1.28%/month (t -6.02). Industry-relative reversal gross 0.98, turnover 90.3, costs 1.78, net -0.80. Industry-relative reversal restricted to low volatility: gross 1.25 (t 9.36), turnover 94.0, costs 1.06, net +0.19 (t 1.41); under a buy/hold (10%/50%) rule gross 0.95 (t 7.93), turnover 58.8, costs 0.67, net +0.28 (t 2.41). Momentum net about 0.68. Text: most strategies with monthly one-sided turnover under 50% keep significant net spreads, few higher-turnover ones do, and a buy/hold spread is the most effective simple mitigation — [Novy-Marx & Velikov, Table 3](https://mysimon.rochester.edu/novy-marx/research/ToAatTC.pdf)
- India, long-term: Joshipura (NSE research paper, monthly NSE data 1995-2008), 3-year formation and test: contrarian monthly average abnormal return +0.87% (long-loser leg 0.49%, short-winner leg 0.38%, all significant); loser cumulative abnormal return significant from month 25 (17.89%); long-loser/short-winner peaks at 34.46% in month 35; loser beta 1.16 vs winner 1.03, not significantly different. 1-year: -2.03%/month contrarian (i.e. momentum; winners +5.4% to +15.55% cumulative over 12 months); 6-month: -0.96%/month. Gross, no costs, no long-only version — [Joshipura, NSE](https://nsearchives.nseindia.com/content/research/res_paperfinal223.pdf)
- India, medium-term: Parthasarathy & Sendilvelu (2022, Economic Thought 67(3):249-268): large monthly moves in large liquid Indian stocks show significant reversals after both declines and increases, for up to six months; larger shocks reverse more. No magnitudes and no sample period on the page — [RePEc](https://ideas.repec.org/a/bas/econth/y2022i3p249-268.html)
- India, daily: Parthasarathy (2019, Review of Behavioral Finance 11(4):393-405): large one-day moves alone show no abnormal returns; low-volume moves reverse over 20 days (contrarian profits significant) and high-volume moves continue. No magnitudes or sample period — [RePEc](https://ideas.repec.org/a/eme/rbfpps/rbf-06-2018-0058.html)
- India, other: Tripathi & Aggarwal (2009) find reversal significant for losers only (from a search listing, secondary); Saji (2023) monthly mean reversal in Nifty stocks 2008-2016 (abstract only); Dhankar & Maheshwari find short-term momentum and long-term overreaction in data 1997-2013 — [Publishing India listing](https://www.publishingindia.com/archive/ijfm/a-study-of-contrarian-and-momentum-profits-in-indian-stock-market); [Saji 2023 on RePEc](https://ideas.repec.org/a/ids/afasfa/v13y2023i4p467-477.html)

### Candidate catalogue (reversal)

**C1. Weekly / monthly short-term reversal, buy last week's or month's losers (long-only half)** — FAILS-ON-COST
- Citation: Jegadeesh 1990 J. Finance 45:881-898; Lehmann 1990 QJE 105:1-28 ([Quantpedia](https://quantpedia.com/strategy-tags/reversal), [Columbia](https://business.columbia.edu/sites/default/files-efs/pubfiles/11568/str1.pdf)).
- Sample: US stocks, original samples pre-1990 (years not retrieved).
- Effect: about 2.49%/month (monthly) and 1.79%/week (weekly), gross long-short, secondary figures. In the modern US value-weighted decile sample it is 0.37%/month gross ([NMV Table 3](https://mysimon.rochester.edu/novy-marx/research/ToAatTC.pdf)); a long-only half is at most about that.
- t / Sharpe: t 1.71 gross (NMV); originals not retrieved.
- Turnover / holding: one-sided about 91%/month (NMV) = about 34 bp/month cost drag on the long leg at 37.5 bp round trip; weekly version far more.
- Gross / net: gross 0.37%/month, net -1.28%/month, t -6.02 (NMV).
- Out of sample: gross effect shrinks sharply from the original samples to the NMV sample; Griffin-Kelly-Nardari find similar reversal returns in 56 markets ([GKN](https://ideas.repec.org/a/oup/rfinst/v23y2010i8p3225-3277.html)).
- India: reversal significant for losers only (Tripathi & Aggarwal 2009, secondary); Nifty monthly mean reversion 2008-2016 (Saji 2023, abstract only) — no net figure ([listing](https://www.publishingindia.com/archive/ijfm/a-study-of-contrarian-and-momentum-profits-in-indian-stock-market), [Saji](https://ideas.repec.org/a/ids/afasfa/v13y2023i4p467-477.html)).
- Data: closes from bhavcopy plus corporate-action adjustment; yes.
- Clears 35-40 bp? No at full monthly turnover. A long-only leg would need at least about 34 bp/month gross just to break even, which exceeds the whole modern US long-short spread.
- Overlap: 00 line 309 "Short-term reversal: Reject" and line 312 "already lost here (121-122)" (Sahab Ranker C1/C2 FAIL, +0.08% and +0.14%/month). Closed; do not re-propose.

**C2. Residual (factor-purged) reversal** — MARGINAL, needs inputs bhavcopy lacks
- Citation: Blitz, Huij, Lansdorp, Verbeek 2013 J. Financial Markets 16(3):477-504 ([EUR](https://repub.eur.nl/pub/40707), [CXO](https://www.cxoadvisory.com/technical-trading/purified-short-term-stock-reversal/)).
- Sample: US 1926-2008 (working paper), long-short.
- Effect: 1.34%/month residual vs 0.97%/month conventional, gross (working-paper figures); CXO (secondary): net above 8%/year, breakeven round-trip friction about 0.56% = 56 bp.
- t / Sharpe: not retrieved.
- Turnover / holding: monthly rebalance; turnover not retrieved (comparable to C1, so about 90% one-sided).
- Gross / net: gross 1.34%/month; net claim secondary.
- Out of sample: not found for post-2010; NMV's modern-sample result suggests the conventional version has faded.
- India: none found for residual reversal.
- Data: a market-beta residual can be built from bhavcopy closes plus an index series; size and value residuals need market cap and book value, which bhavcopy lacks.
- Clears 35-40 bp? The CXO breakeven of about 56 bp exceeds the hurdle on paper, but that is US, long-short, pre-2009 and secondary; at 90% monthly turnover the drag is about 34 bp/month, which a long-only leg would not clear unless the gross spread is above about 40 bp/month on the long side. Unproven.
- Overlap: 00 line 316 skips "reversal ... tested in section 85"; line 312 lists "residual momentum" as rejected (a different object). Same family as C1, so treat as covered unless the residual step is shown to matter.

**C3. Industry-relative reversal, low-volatility, with a buy/hold band** — MARGINAL (best US net)
- Citation: Novy-Marx & Velikov 2016 RFS 29(1):104-147 ([Table 3](https://mysimon.rochester.edu/novy-marx/research/ToAatTC.pdf)); Hameed & Mian 2015 JFQA 50:89-117 ([Cambridge](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/industries-and-stock-return-reversals/92B5101FBEA7B40717D46DB60913BF41)).
- Sample: US value-weighted deciles, NYSE breakpoints (years not recorded in these notes).
- Effect: gross 0.95%/month, net +0.28%/month under the 10%/50% buy/hold rule; without the band net +0.19%.
- t / Sharpe: gross t 7.93, net t 2.41 (band) vs 1.41 (no band).
- Turnover / holding: one-sided about 58.8%/month with the band (about 22 bp/month drag at 37.5 bp), vs 94.0% without.
- Gross / net: net +0.28%/month is long-short and uses NMV's own cost model, not India's.
- Out of sample: Hameed-Mian report it holds in large liquid stocks and is stronger after market declines.
- India: none found.
- Data: industry labels are not in bhavcopy. `backend/data/nse_indices/` exists locally (00 section 5a) but whether it holds sector-index membership history was not checked.
- Clears 35-40 bp? Net t 2.41 is below the momentum-family bar of 2.865 and this is not a momentum rule, but the lesson stands: only banded, low-volatility, industry-relative reversal survives US costs. A long-only leg gets roughly half the spread, so net would be about zero to slightly positive before India costs.
- Overlap: same family as C1 (00 lines 309, 312). Industry-relative is new, but the in-house reversal losses and the "sector rotation: Leave" line (00 line 335) point the same way.

**C4. Volume-conditioned reversal: buy large one-day or one-week losers that fell on low volume** — NO-EVIDENCE net, plausible
- Citation: Cooper 1999 RFS 12(4):901-935 ([RePEc](https://ideas.repec.org/a/oup/rfinst/v12y1999i4p901-35.html)); Parthasarathy 2019 RBF 11(4):393-405 ([RePEc](https://ideas.repec.org/a/eme/rbfpps/rbf-06-2018-0058.html)).
- Sample: Cooper NYSE/AMEX large caps weekly; Parthasarathy Indian large moves (period not on the page).
- Effect: no magnitudes retrieved for either. Direction: low-volume moves reverse over 20 days, high-volume moves continue.
- t / Sharpe: described as significant (India); not quantified.
- Turnover / holding: 20-trading-day hold, event-driven (a few names a month): about 1 round trip a month on the names held, drag about 37.5 bp a month on that sleeve.
- Gross / net: gross only.
- Out of sample: Cooper (US) and Parthasarathy (India) agree on direction, which is the only replication-like evidence.
- India: yes, Parthasarathy 2019 (no magnitude).
- Data: bhavcopy has daily volume and number of trades. Delivery quantity could add a "quality of volume" cut, but no study links it to this effect.
- Clears 35-40 bp? Unknown. It needs a gross of at least about 40 bp per 20-day trade; no source gives the gross.
- Overlap: 00 line 278 "relative-volume gating: Not on its own" (intraday gating context) and the short-term reversal rejection (line 309). The volume split is the new part.

**C5. Reversal after large monthly moves in large liquid stocks, holding up to six months (both directions)** — NO-EVIDENCE net, conflicts with the momentum book
- Citation: Parthasarathy & Sendilvelu 2022 Economic Thought 67(3):249-268 ([RePEc](https://ideas.repec.org/a/bas/econth/y2022i3p249-268.html)).
- Sample: large liquid Indian stocks; period not on the page.
- Effect: significant reversals after declines and after increases, up to six months, larger for larger shocks. No bp figure.
- t / Sharpe: not retrieved.
- Turnover / holding: up to 6 months, so at most about 17% one-sided a month, about 6 bp/month drag.
- Gross / net: gross, no cost.
- Out of sample: none found.
- India: yes (this is the Indian paper).
- Data: bhavcopy closes; yes.
- Clears 35-40 bp? On turnover yes. On evidence unknown.
- Overlap: contradicts the project's momentum book (trial 126, +0.71%/month, t 2.51; 00 section 1c) and Joshipura's 6- and 12-month momentum (see C8). Buying losers after a large drop and buying 12-month winners can hold opposite names. Any trial would need to say which definition of "large single-month move" it uses and be tested as its own family.

**C6. News-purged / stale-news reversal (buy losers whose fall had no news)** — NOT-HARVESTABLE with bhavcopy
- Citation: Da, Liu, Schaumburg, Management Science 60(3):658-674 ([NY Fed SR513](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr513.html)); Tetlock 2011 RFS 24(5):1481-1512 ([RePEc](https://ideas.repec.org/a/oup/rfinst/v24y2011i5p1481-1512.html)).
- Sample: US, 1982-2009 (NY Fed version).
- Effect: about 3x to 4x the risk-adjusted return of plain reversal (ratio, not bp); Tetlock: stale-news-day return negatively predicts the next week.
- t / Sharpe: not retrieved.
- Turnover / holding: weekly to monthly; high.
- Gross / net: not reported net in my sources.
- Out of sample: not found.
- India: none found.
- Data: needs analyst revisions and news flow. Bhavcopy has neither. The local NSE filings event set (9,586 events, L35, 00 section 5a) could proxy "no filing on the day", untested.
- Clears 35-40 bp? Unknown; high turnover makes it unlikely.
- Overlap: 00 line 309 (reversal rejected); NSE filings were measured as L35 (00 section 5a), not for this purpose.

**C7. VIX-state-conditioned reversal (trade reversal only when volatility is high)** — NO-EVIDENCE, partly covered
- Citation: Nagel 2012 RFS 25(7):2005-2039 ([NBER](https://nber.org/papers/w17653)); Hameed & Mian 2015 (stronger after market declines, volatile periods) ([RePEc](https://econpapers.repec.org/RePEc:cup:jfinqa:v:50:y:2015:i:1-2:p:89-117_00)).
- Sample: US.
- Effect: not retrieved.
- t / Sharpe: not retrieved.
- Turnover / holding: conditioning lowers the number of trading months but not the per-month cost.
- Gross / net: not reported.
- Out of sample: none found; India VIX version not found.
- India: none found.
- Data: India VIX is not in bhavcopy (a market-realised-volatility proxy can be built from index closes).
- Clears 35-40 bp? Cannot say.
- Overlap: 00 line 278 "Volatility / India VIX / relative-volume gating: Not on its own".

**C8. 3-year contrarian: buy 3-year losers, hold up to 3 years, long-only** — CLEARS-ON-COST (turnover), evidence thin
- Citation: Joshipura, NSE research paper ([NSE PDF](https://nsearchives.nseindia.com/content/research/res_paperfinal223.pdf)). The original US result (De Bondt-Thaler 1985) was not retrieved in this sweep.
- Sample: NSE monthly data 1995-2008.
- Effect: +0.87%/month long-short, of which the long-loser leg is +0.49%/month (about 5.9%/year) and the short-winner leg 0.38%/month. Loser cumulative abnormal return significant from month 25 (17.89%).
- t / Sharpe: described as significant; figures not extracted.
- Turnover / holding: 36-month hold; one round trip of about 37.5 bp over 36 months is about 1 bp/month.
- Gross / net: gross, market-adjusted, no cost, no long-only version in the paper (the long leg is reported separately).
- Out of sample: none found after 2008. 1995-2008 is one regime; the bhavcopy panel from 2010 supports only about four non-overlapping 36-month test windows (2013-2025) (my arithmetic), so the t-statistics will be driven by overlapping, autocorrelated observations.
- India: this is the Indian evidence. Loser beta 1.16 vs winner 1.03, not significantly different, so the loser leg is not obviously just beta.
- Data: 36-month returns from bhavcopy, corporate-action adjusted; yes.
- Clears 35-40 bp? On turnover yes by a wide margin (about 1 bp/month vs 49 bp/month gross). Risks: 3-year losers in India include distressed, illiquid and surveillance-listed names (see C20-C22), where slippage exceeds 10 bp and the per-name DP charge is a larger share at small position size.
- Overlap: not listed in 00. Nearest are 00 line 316 ("reversal, beta, IVOL ... tested in section 85") and the momentum family. It is the opposite sign of momentum at a longer horizon, so it is partly a complement to the trial-126 book, not a replacement.

**C9. Reversal in illiquid, high-turnover stocks** — NEGATIVE finding
- Citation: Avramov, Chordia, Goyal 2006 J. Finance 61(5):2365-2394 ([RePEc](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html)).
- Sample: US.
- Effect: reversals are concentrated in high-turnover, low-liquidity stocks; contrarian profits are smaller than likely transaction costs.
- t / Sharpe: not retrieved.
- Turnover / holding: as C1.
- Gross / net: the paper's own conclusion is net-negative.
- Out of sample: consistent with NMV's modern result for the plain version.
- India: none found; Joshipura and Parthasarathy do not report this split.
- Data: bhavcopy; yes.
- Clears 35-40 bp? No: the profits sit where costs are highest.
- Overlap: 00 line 316 lists illiquidity as "tested in section 85". Record as a negative that also applies to C1 and C4 when run on the small-cap tail.

### Inferences
- A weekly or monthly reversal sleeve cannot clear 35-40 bp round trip at 90% monthly turnover: the drag (about 34 bp/month) exceeds the whole modern US value-weighted long-short gross (0.37%/month), and the US net is -1.28%/month. The in-house Ranker losses (00 line 312) agree.
- Only reversal variants that cut turnover (the buy/hold band in C3, the 6-month hold in C5, the 3-year hold in C8) are cost-feasible. Of these, only C8 has Indian evidence with a stated magnitude, and it is gross, old and un-replicated.
- India's own evidence cuts both ways: 6- and 12-month momentum (Joshipura: 12-month winners-minus-losers +2.03%/month, 6-month +0.96%/month, 1995-2008, gross) coexists with 3-year contrarian and with reversal after large monthly moves. A reversal tilt at 1-6 months would fight the project's momentum book, so C5 should only be tested as a separate, pre-registered family with its own bar.
- Because the long-only half of a reversal spread is roughly half the long-short spread (my assumption; no source states the split), every long-short number above should be halved before comparing it with a cost.
- Reversal close-to-close returns include bid-ask bounce; an NSE buyer executing at the next open or the next close will see less than the studies report (my reasoning, not measured here).

### Gaps
- No Indian reversal study reports net-of-cost or long-only returns; the abstracts for Parthasarathy 2019/2022, Tripathi & Aggarwal 2009 and Saji 2023 give no magnitude or no sample period.
- Jegadeesh 1990 and Lehmann 1990 figures are secondary (Quantpedia and a Columbia summary); original tables not read. Blitz et al. net figures come from a CXO summary.
- Nagel 2012 and Hameed-Mian magnitudes not retrieved. De Bondt-Thaler (1985) not retrieved.
- NMV Table 3 sample years not recorded in these notes.
- No post-2010 India test of reversal on a bhavcopy-style panel was found; the 2010-2026 sample is where a test would be new.

## (b) Liquidity and volume: Amihud, turnover, Pastor-Stambaugh, Liu, high-volume return premium, Lee-Swaminathan, attention

### Takeaway
Liquidity and volume effects are the lowest-turnover family in this sweep (annual to monthly rebalancing), so cost is not the binding constraint; evidence is. The Indian studies agree on direction (less liquid stocks earn more; a high-volume premium exists but is weak) yet none gives a bp magnitude I could retrieve, and the retail slippage assumption of about 10 bp is least safe exactly in the illiquid tail where the premium lives.

### Cited Findings
- Gervais-Kaniel-Mingelgrin (2001, J. Finance 56(3):877-919): stocks with unusually high trading volume have abnormally positive returns afterward; explained by a visibility / investor-recognition effect — [GKM, Wharton](https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/9901.pdf)
- Kaniel-Ozoguz-Starks (2012, JFE 103(2):255-279): the high-volume premium is present across 41 countries, in developed and emerging markets, and is not explained by risk or liquidity — [RePEc](https://ideas.repec.org/a/eee/jfinec/v103y2012i2p255-279.html)
- India high-volume return premium: Singh-Wang-Hua (2025, Pacific-Basin Finance Journal 91, DOI 10.1016/j.pacfin.2025.102789) find it small and weaker than the US: value-weighted significant at 10%, equal-weighted at 5%; no predictive power for industrial production. No % magnitude on the page — [RePEc](https://ideas.repec.org/a/eee/pacfin/v91y2025ics0927538x2500126x.html)
- Lee-Swaminathan (2000, J. Finance 55(5):2017-2069): past volume predicts the magnitude and persistence of momentum; low-volume losers rebound in 3-12 months, high-volume winners reverse faster, and low-volume stocks earn higher returns — [RePEc](https://ideas.repec.org/a/bla/jfinan/v55y2000i5p2017-2069.html); [Cochrane-hosted copy](https://www.johnhcochrane.com/s/lee_swaminathan_returns_volume_JF.pdf)
- Amihud (2002, J. Financial Markets 5:31-56) documents a positive cross-sectional illiquidity premium; Amihud-Hameed-Kang-Zhang (2015, JFE 117(2):350-368) find a positive, significant premium across 45 countries (per-country sizes and the India row not retrieved); a follow-up, "Global Evidence on the Premium for Market Illiquidity" (2019), reports about 0.85%/month as the global average with the sample extended to 2015 — [JCU record](https://researchonline.jcu.edu.au/42806/); [JCU portfolio](https://portfolio.jcu.edu.au/publications/JCU177601)
- Pastor-Stambaugh (2003): stocks with higher liquidity betas earn higher returns. The oft-quoted 7.5%/year appears only in secondary papers (one says its replication gives a smaller premium) and is unverified here — [Pastor-Stambaugh](https://www.cis.upenn.edu/~mkearns/finread/pastor.pdf)
- Datar-Naik-Radcliffe (1998, J. Financial Markets 1:203-219): turnover as a liquidity proxy; returns decrease in turnover. Evidence on turnover as a predictor is contested — [Semantic Scholar entry](https://www.semanticscholar.org/paper/Liquidity-and-stock-returns:-An-alternative-test-Datar-Naik/b231827ec4090cc7558d446f6979c6db570f0c23)
- Liu (2006) proposes a zero-trading-day (turnover-adjusted) liquidity measure inside a liquidity-augmented CAPM — [Liu on ResearchGate](https://www.researchgate.net/publication/4787047_A_Liquidity-Augmented_Capital_Asset_Pricing_Model)
- India liquidity: an NMIMS study on Nifty 500, 2000-2018, with four liquidity proxies including Amihud, finds less liquid portfolios earn higher returns and a liquidity-augmented Fama-French three-factor model explains best — [NMIMS Management Review](https://management-review.nmims.edu/?p=737). Cheriyan & Lazar use 2016 one-minute NIFTY 50 data to find a liquidity-risk premium (narrow sample) — [Cheriyan & Lazar](https://www.dlib.si/stream/URN:NBN:SI:doc-H31Y5LHJ/fb56bfd2-414e-43b3-8904-13063620caeb/PDF). A MEJ 2020 paper reports seasonality in the liquidity premium — [MEJ 2020](https://maims.ac.in/wp-content/uploads/2021/10/MEJ_Vol.1-No.2_July-Dec-2020_01-1.pdf)
- A turnover-based India study over 2003-2008 found turnover played no role in market return (seen only in a search listing) — [Publishing India listing](https://www.publishingindia.com/archive/ijfm/a-study-of-contrarian-and-momentum-profits-in-indian-stock-market)
- Barber-Odean (2008, RFS): individual investors are net buyers of attention-grabbing stocks (news, abnormal volume, extreme one-day returns); selling is not attention-driven — [Barber & Odean](https://faculty.haas.berkeley.edu/odean/papers/Attention/All%20that%20Glitters.pdf)
- Da-Engelberg-Gao (2011, J. Finance): Google Search Volume Index as an attention proxy on the Russell 3000, 2004-2008. A CXO summary (secondary, unverified here) says high-search small caps outperform by about 0.08% weekly over two weeks — [CXO Advisory](https://www.cxoadvisory.com/sentiment-indicators/google-search-data-as-a-measure-of-investor-attention/)
- India Google SVI: Swamy & Dharani (2019): weekly Nifty 50 data, July 2012 to June 2017 (260 weeks); high SVI predicts positive returns in weeks 4-5, domestic searches matter more. Whether the test is index- or stock-level is not clear on the page — [RePEc](https://ideas.repec.org/a/eme/rbfpps/rbf-04-2018-0033.html)
- MAX / lottery effect, India: Sharma & Chakraborty (2021, Studies in Economics and Finance 38(3):640-658) use January 2003 to March 2017, an average 2,949 firms a month; high-MAX deciles outperform low-MAX (opposite of the US), raw and risk-adjusted, and long-high / short-low could be profitable. No magnitude retrieved — [Emerald](http://www.emerald.com/sef/article/38/3/640-658/456919); [DOI](https://www.doi.org/10.1108/SEF-04-2018-0099)

### Candidate catalogue (liquidity and volume)

**C10. Amihud illiquidity tilt, long-only (buy the least liquid decile of a defined universe)** — CLEARS-ON-COST (turnover), slippage is the risk
- Citation: Amihud 2002 J. Financial Markets 5:31-56; Amihud, Hameed, Kang, Zhang 2015 JFE 117(2):350-368 ([JCU](https://researchonline.jcu.edu.au/42806/)); NMIMS Nifty 500 study ([NMIMS](https://management-review.nmims.edu/?p=737)).
- Sample: 45 countries (2015 paper); Nifty 500 2000-2018 (India).
- Effect: positive and significant premium; the 2019 market-level follow-up reports about 0.85%/month global average ([JCU portfolio](https://portfolio.jcu.edu.au/publications/JCU177601)). Per-stock cross-sectional size and the India magnitude not retrieved.
- t / Sharpe: described as significant; not extracted.
- Turnover / holding: annual or semi-annual rebalance; drag about 3 bp/month annual, about 6 bp/month semi-annual.
- Gross / net: gross; no net figure.
- Out of sample: replicated across 45 countries and, directionally, in Nifty 500 (2000-2018).
- India: yes, direction only.
- Data: Amihud ratio = |daily return| / rupee volume, both derivable from bhavcopy (value traded = volume x price if no turnover field). Days with no row for a stock matter for thin names (check whether `bhav_daily` keeps non-trading days).
- Clears 35-40 bp? Turnover is fine. The weak link is slippage: the 10 bp assumption is for liquid names; in the bottom liquidity decile a retail order of Rs 5,500-33,000 per name may still be small versus daily value, but the fixed Rs 15.34 DP charge is 56-59 bp at Rs 5,500-6,667 per name (00 section 6), so the premium must exceed about 60 bp per round trip at small tickets.
- Overlap: 00 line 316 "reversal, beta, IVOL, liquidity, illiquidity, price (tested in section 85)" and "micro-caps and SME" skipped. Treat as already tried as a Ranker input; a standalone low-turnover tilt was not recorded as run.

**C11. Pastor-Stambaugh liquidity-beta tilt** — NO-EVIDENCE for a bhavcopy implementation
- Citation: Pastor & Stambaugh 2003 ([PDF](https://www.cis.upenn.edu/~mkearns/finread/pastor.pdf)).
- Sample: US.
- Effect: higher liquidity beta earns higher returns; the 7.5%/year figure is secondary and unverified.
- t / Sharpe: not retrieved.
- Turnover / holding: annual to monthly; betas are noisy, so the sort changes name by name.
- Gross / net: gross.
- Out of sample: one secondary paper reports a smaller premium on replication (not verified).
- India: none found with this exact measure; NMIMS uses a liquidity-augmented three-factor model ([NMIMS](https://management-review.nmims.edu/?p=737)).
- Data: needs a market-wide liquidity innovation series (can be built from aggregate Amihud) and per-stock regressions; derivable, but noisy at monthly frequency.
- Clears 35-40 bp? Unknown; the cost is low if rebalanced annually, but beta-estimation noise is a bigger problem than cost.
- Overlap: same line as C10 (00 line 316).

**C12. Turnover / low-turnover premium (Datar-Naik-Radcliffe)** — NO-EVIDENCE, contested
- Citation: Datar, Naik, Radcliffe 1998 J. Financial Markets 1:203-219 ([Semantic Scholar](https://www.semanticscholar.org/paper/Liquidity-and-stock-returns:-An-alternative-test-Datar-Naik/b231827ec4090cc7558d446f6979c6db570f0c23)).
- Sample: US.
- Effect: returns decrease in turnover; size not retrieved.
- t / Sharpe: not retrieved.
- Turnover / holding: monthly to annual.
- Gross / net: gross.
- Out of sample: contested as a predictor; an India study over 2003-2008 found turnover played no role in market return ([listing](https://www.publishingindia.com/archive/ijfm/a-study-of-contrarian-and-momentum-profits-in-indian-stock-market)).
- India: weak negative.
- Data: turnover ratio needs shares outstanding or free float, which bhavcopy lacks; traded value or own-history-normalised volume are proxies.
- Clears 35-40 bp? Cannot say.
- Overlap: 00 line 316 (liquidity / illiquidity). Note the sign conflicts with C14 (high volume predicts higher returns), which is a timing-versus-level distinction, not a contradiction.

**C13. Liu zero-trading-day liquidity measure** — NO-EVIDENCE
- Citation: Liu 2006 ([ResearchGate](https://www.researchgate.net/publication/4787047_A_Liquidity-Augmented_Capital_Asset_Pricing_Model)).
- Sample: US; effect size not retrieved.
- Effect: not retrieved.
- t / Sharpe: not retrieved.
- Turnover / holding: low (slow-moving measure).
- Gross / net: not retrieved.
- Out of sample: none found.
- India: none found.
- Data: needs the count of zero-volume days per stock over 12 months; derivable if the panel keeps non-traded days, and relevant mainly to the illiquid tail and surveillance-listed names.
- Clears 35-40 bp? Cannot say.
- Overlap: 00 line 316 (illiquidity); effectively a variant of C10.

**C14. High-volume return premium: buy stocks after an abnormal-volume day or week** — MARGINAL, weak in India
- Citation: Gervais, Kaniel, Mingelgrin 2001 J. Finance 56(3):877-919 ([Wharton](https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/9901.pdf)); Kaniel, Ozoguz, Starks 2012 JFE 103(2):255-279 ([RePEc](https://ideas.repec.org/a/eee/jfinec/v103y2012i2p255-279.html)); Singh, Wang, Hua 2025 Pacific-Basin Finance Journal 91 ([RePEc](https://ideas.repec.org/a/eee/pacfin/v91y2025ics0927538x2500126x.html)).
- Sample: US (GKM); 41 countries (Kaniel); India (Singh); India sample years not on the page.
- Effect: positive; India described as small and weaker than the US. No bp figure retrieved for any.
- t / Sharpe: India VW significant at 10%, EW at 5%.
- Turnover / holding: depends on the holding window (not retrieved); event-driven, so turnover is roughly one round trip per event.
- Gross / net: gross.
- Out of sample: yes, 41 countries, but India is the weakest case.
- India: yes (Singh et al.).
- Data: bhavcopy has daily volume; the ratio to a trailing average is straightforward.
- Clears 35-40 bp? Unknown; a 10% / 5% significance in India suggests a small gross per event.
- Overlap: 00 line 278 "relative-volume gating: Not on its own" and L50 bulk/block VOID (disclosed deals, a different object). Not run as a standalone cross-sectional signal.

**C15. Volume-conditioned momentum (Lee-Swaminathan: low-volume losers rebound, high-volume winners reverse)** — NO-EVIDENCE for India, is a momentum-family trial
- Citation: Lee & Swaminathan 2000 J. Finance 55(5):2017-2069 ([RePEc](https://ideas.repec.org/a/bla/jfinan/v55y2000i5p2017-2069.html), [PDF](https://www.johnhcochrane.com/s/lee_swaminathan_returns_volume_JF.pdf)).
- Sample: US.
- Effect: not retrieved in bp; low-volume losers rebound in 3-12 months, high-volume winners reverse faster, low-volume stocks earn more.
- t / Sharpe: not retrieved.
- Turnover / holding: 3-12 months; moderate to low turnover.
- Gross / net: gross.
- Out of sample: a European replication reportedly differs (see Gaps; source not recorded).
- India: none found.
- Data: bhavcopy volume; yes.
- Clears 35-40 bp? On turnover yes.
- Overlap: it is a conditioning of the momentum book (trial 126, +0.71%/month, t 2.51; frog-in-the-pan trial 204 FAIL as an earlier conditioning, 00 section 1c). It would count as another momentum-family trial, so the bar is t >= 2.865 for N = 12 and 2.891 after (00 section 1c, prereg-us-momentum.md line 9).

**C16. Google-search-attention (SVI) tilt** — NO-EVIDENCE net; data outside bhavcopy
- Citation: Da, Engelberg, Gao 2011 J. Finance ([CXO summary](https://www.cxoadvisory.com/sentiment-indicators/google-search-data-as-a-measure-of-investor-attention/)); Swamy & Dharani 2019 ([RePEc](https://ideas.repec.org/a/eme/rbfpps/rbf-04-2018-0033.html)).
- Sample: Russell 3000 2004-2008 (US); weekly Nifty 50, July 2012 to June 2017, 260 weeks (India).
- Effect: US, secondary and unverified: about 0.08% weekly over two weeks for high-search small caps, about 8 bp/week, below one round trip. India: high SVI predicts positive returns in weeks 4-5; no bp figure.
- t / Sharpe: not retrieved.
- Turnover / holding: weekly; high.
- Gross / net: gross.
- Out of sample: Indian result is in a different window, not a replication of the stock-level design.
- India: yes, with caveat; other Indian attention papers (Dharani et al. 2022; Saxena & Chakraborty 2022) are in Gaps.
- Data: Google Trends series per stock; not in bhavcopy and not a point-in-time vintage.
- Clears 35-40 bp? No at weekly turnover given about 8 bp/week.
- Overlap: not covered in 00.

**C17. Retail-attention fade: avoid or fade stocks on abnormal volume and extreme one-day returns** — NO-EVIDENCE net (avoid-list use)
- Citation: Barber & Odean 2008 RFS ([PDF](https://faculty.haas.berkeley.edu/odean/papers/Attention/All%20that%20Glitters.pdf)).
- Sample: US individual and institutional accounts.
- Effect: individuals are net buyers of attention-grabbing stocks; no return follow-up figure retrieved.
- t / Sharpe: not retrieved.
- Turnover / holding: event-driven.
- Gross / net: not reported here.
- Out of sample: none found for India.
- India: none found.
- Data: bhavcopy volume and daily return; yes.
- Clears 35-40 bp? Long-only cannot short the fade; usable only as an exclusion filter on purchases.
- Overlap: nearest are L50 (bulk / block VOID) and C14; the exclusion-filter use is untested.

**C18. MAX / lottery effect: buy high-MAX deciles (India sign is opposite to the US)** — NO-EVIDENCE net; partly NOT-HARVESTABLE
- Citation: Sharma & Chakraborty 2021 Studies in Economics and Finance 38(3):640-658 ([Emerald](http://www.emerald.com/sef/article/38/3/640-658/456919), [DOI](https://www.doi.org/10.1108/SEF-04-2018-0099)).
- Sample: India January 2003 to March 2017, about 2,949 firms a month.
- Effect: high-MAX deciles outperform low-MAX, raw and risk-adjusted; no magnitude retrieved.
- t / Sharpe: not retrieved.
- Turnover / holding: monthly rebalance; high.
- Gross / net: gross.
- Out of sample: none; the opposite sign to the US could reflect circuit-limit dynamics or a small-cap tilt (my speculation, untested).
- India: this is the Indian paper.
- Data: bhavcopy; max daily return over the prior month; yes.
- Clears 35-40 bp? At monthly turnover the drag is about 34 bp/month; the high-MAX decile is likely heavy in stocks that hit upper circuits (my inference), which a retail buyer cannot buy at that close (see C23).
- Overlap: 00 line 316 skips IVOL and price; MAX is not named there. L49 (09:45 gap reversal) and gap lines (00 line 276) concern intraday gaps, a different object.

### Inferences
- The only candidates in this section that are cost-feasible by construction are the slow ones (C10, C11, C13, annual or semi-annual). But the illiquidity premium sits in the thin tail where the retail slippage assumption and the fixed Rs 15.34 DP charge hurt most, and the project already lists illiquidity as tested as a Ranker input (00 line 316). A standalone low-turnover Amihud tilt is the one clean untested form, but it needs a slippage model that scales with order size over daily value, not the flat 10 bp.
- C14 and C15 are volume conditionings of effects the project has already tried to trade (reversal, momentum). They add a degree of freedom, and a momentum-conditioned rule raises the momentum-family count.
- The Indian high-volume premium is documented as small (significance only at 5% or 10%), and no bp figure exists, so I would not budget a gross edge for it above the noise floor.
- Attention strategies (C16, C17) need data outside bhavcopy and at weekly turnover are too costly; their value is as filters, not as signals.
- Sign inconsistency worth flagging: liquid-stock volume surges predict positive returns (C14) while the illiquid-stock tilt (C10) earns more from low volume; both can hold, but a single score combining them needs an explicit pre-registered definition.

### Gaps
- No Indian magnitude (bp or %/month) for the high-volume premium, the liquidity premium or the MAX effect; abstracts only for Singh et al. 2025, Sharma & Chakraborty 2021 and the NMIMS paper.
- Amihud et al. 2015 per-country size and India row not retrieved; the 0.85%/month in the follow-up is a global average for a market-illiquidity premium, not a stock-sort spread.
- Pastor-Stambaugh 7.5%/year is secondary and unverified; Da-Engelberg-Gao 0.08%/week is a CXO figure and unverified.
- Liu 2006 effect size and Datar et al. magnitudes not retrieved. A claimed European replication of Lee-Swaminathan (Lopes 2018, only low-volume stocks show momentum) was in my working notes without a recorded source URL, so it is excluded from Cited Findings.
- Other Indian attention papers (Dharani et al. 2022, Borsa Istanbul Review; Saxena & Chakraborty 2022, Managerial Finance) were seen only in search listings; no URL recorded.
- Whether `bhav_daily` retains non-trading days or a value-traded field was not checked.

## (c) NSE-specific: delivery %, price bands and circuits, ASM / GSM / T2T, F&O ban, SEBI margin and expiry changes, order-flow imbalance

### Takeaway
There is no peer-reviewed evidence that NSE delivery % predicts returns, and no event study of F&O bans, peak-margin, the 2025 weekly-expiry or lot-size changes, or margin-trading eligibility. The measured NSE regime evidence (ASM, GSM, T2T) shows a pre-event run-up followed by flat-to-negative returns, which a long-only delivery account can use only as an avoid-list; circuit-continuation statistics are real but not harvestable by a retail buyer.

### Cited Findings
- Delivery %: I found no peer-reviewed study linking NSE delivery percentage to subsequent returns. Practitioner view: Capitalmind says delivery shocks are not very useful to trade on their own — [Capitalmind](https://premium.capitalmind.in/2016/02/delivery-shockers-the-january-2016-edition/). Business Standard notes delivery % rose in 2022 with new margin norms in a muted-return year, i.e. the ratio moves with market structure — [Business Standard](https://www.business-standard.com/article/markets/delivery-percentage-improved-in-2022-amid-new-margin-norms-shows-data-123010800460_1.html)
- Adjacent Indian work: an NSE500 abnormal-volume / disposition-effect paper (abnormal volume, not delivery) — [RePEc](https://ideas.repec.org/a/eme/rbfpps/rbf-12-2018-0132.html); a 2004 option-expiration working paper — [RePEc](https://ideas.repec.org/p/wpa/wuwpfi/0411035.html)
- ASM / STASM (Chari & Inamdar, NISM, NSE-NYU initiative): 218 events (188 unique stocks), 21 Nov 2018 to 28 Feb 2019. In the 5-day window cumulative average abnormal return falls from +10.51% (pre-inclusion) to -0.92% (post-inclusion), significant at 1%. Pre-exclusion -1.10% to post +0.73% (not significant). Prices stabilise and volume falls after inclusion; stocks with negative CAR are less liquid. Short sample — [Chari & Inamdar, NSE](https://nsearchives.nseindia.com/s3fs-public/inline-files/Effectiveness%20of%20additional%20surveillance%20measures_WorkingPaper.pdf)
- GSM (Aggarwal, Bhatia, Zaveri, "Rules vs discretion in market surveillance"): 121 stocks entered Mar 2017 to Mar 2019; propensity-matched difference-in-differences shows entry into stage 1 causes a significant price decline and a fall in trading activity. Nearly a third did not meet the criteria; more than half of exiters still showed the characteristics; the illiquidity ratio falls after exit — [Aggarwal et al., NSE](https://nsearchives.nseindia.com/s3fs-public/inline-files/Rules_vs_discretion_in_market_surveillance_Aggarwal_Bhatia_Zaveri_0.pdf); [Business Standard](https://www.business-standard.com/amp/article/markets/how-sebi-s-warning-system-curbs-gamestop-like-gains-in-indian-stock-markets-121021000097_1.html)
- T2T moves: Parmar & Chaturvedula (2017, Accounting and Finance Research 6(1):1-9) find large positive pre-event (30-day) abnormal returns, significantly negative post-announcement returns and higher volatility; no figures or sample on the page — [RePEc](https://ideas.repec.org/a/jfr/afr111/v6y2017i1p9.html). NSE T2T mechanics (fortnightly identification, quarterly moves) — [NSE periodic review of securities](https://www.nseindia.com/static/regulations/movement-securities-periodic-review)
- Circuits: Das, arXiv:2608.08625 (preprint, not peer reviewed), NSE daily data Nov 2007 to Jun 2026, 898,689 observations after exclusions (band changes, corporate actions and fixed-band stocks excluded). Probability of closing at the same boundary the next day: 2% band 78.85% (n = 83 upper, 144 lower, small); 5% band 44.78% (11,129 upper closes of which 46.3% repeat upper; 8,696 lower closes, 42.8% repeat lower); 10% band 26.74% (1,542 upper; 25.1%); 20% band 14.52% (1,230 upper; 13.25%). The same-sign next-day response rises with band width. Mean next-day return values exist only in a figure and were not extracted — [Das, arXiv](https://arxiv.org/pdf/2608.08625)
- Price bands: NSE uses 2/5/10/20% bands, F&O stocks have a dynamic 10% band, and bands are revised for the next trading day (practitioner sources) — [Rupeezy](https://support.rupeezy.in/support/solutions/articles/21000004845-what-are-circuit-limits-or-price-bands); [One Trade Journal](https://onetradejournal.com/glossary/upper-circuit); [TradingQnA](https://tradingqna.com/t/is-there-any-way-to-know-tomorrow-circuit-limit-of-any-stocks-in-adv/97857)
- F&O ban: a stock enters the ban at 95% of market-wide position limit (MWPL) and exits below 80%; penalty is 1% of the increased position (minimum Rs 5,000, maximum Rs 1,00,000); the MWPL formula moved to delta-adjusted open interest on 1 Oct 2025 (sources disagree; check the circular). No event study found. Example: Kaynes and SAIL under F&O ban on 29 Oct 2026 — [Share.Market](https://www.share.market/support/home/trading-investment/futures-and-options/other-frequently-asked-questions/why-do-fo-contracts-enter-a-ban-period/); [ICICI Direct](https://www.icicidirect.com/ilearn/stocks/articles/future-and-options-ban-impact-on-stock); [Angel One](https://angelone.in/news/market-updates/sensex-monthly-expiry-kaynes-and-sail-under-f-o-ban-on-october-29-2026)
- SEBI peak margin: phased in from December 2020 and fully enforced 1 September 2021 — [One Trade Journal](https://onetradejournal.com/glossary/upfront-margin). Only pre-implementation expectations of lower F&O volume exist — [Business Standard](https://www.business-standard.com/amp/article/markets/volumes-in-f-o-segment-to-shrink-as-peak-margin-rules-kick-in-today-120120100063_1.html). No measured study found.
- SEBI F&O study FY25 (July 2025), as reported by secondary sources: about 91% of individual F&O traders lost money; aggregate net loss about Rs 1,05,603 crore (up 41% from Rs 74,812 crore in FY24); average about Rs 1.1 lakh; unique traders fell from about 61.4 lakh (Q1 FY25) to about 42.7 lakh (Q4). Context only, not a delivery-signal result — [InvestWhat](https://www.investwhat.in/india/investment/investor-news/25062/91-lose-rs106-lakh-crore-written-off-whats-going-on-in-indias-fo-arena); [HDFC Sky](https://hdfcsky.com/sky-learn/derivatives/most-retail-fno-traders-lose-money-sebi-study-10-million-accounts)
- Order-flow imbalance, India: Tripathi-Dixit-Vipul (2021, Finance Research Letters 41), 195 active NSE stocks, find predictability strong for the first 5 minutes and gone within 30 minutes — [RePEc](https://ideas.repec.org/a/eee/finlet/v41y2021ics1544612320316779.html). Also: open limit-order-book information content on NSE data 2014-18 — [CORE](https://core.ac.uk/outputs/657648290); Rastogi-Reddy-Kotha (2013, IJMF) find the order-imbalance / return link weakened post-2002 — [RePEc](https://ideas.repec.org/a/eme/ijmfpp/v9y2013i2p92-109.html); Anantha-Jain-Maiti on BANKNIFTY futures — [arXiv 2507.22712](https://arxiv.org/pdf/2507.22712v2). All are intraday-horizon.

### Candidate catalogue (NSE-specific)

**C19. Delivery % as an accumulation signal (buy on high delivery % plus volume spike)** — NO-EVIDENCE
- Citation: none peer-reviewed. Practitioner: [Capitalmind](https://premium.capitalmind.in/2016/02/delivery-shockers-the-january-2016-edition/); [Business Standard](https://www.business-standard.com/article/markets/delivery-percentage-improved-in-2022-amid-new-margin-norms-shows-data-123010800460_1.html).
- Sample: none.
- Effect: none measured. Screener-style rules such as "delivery above 60% with a volume spike means accumulation" are unmeasured claims.
- t / Sharpe: none.
- Turnover / holding: event-driven; undefined.
- Gross / net: none.
- Out of sample: none.
- India: no study found; Capitalmind calls it not very useful to trade per se; the ratio shifts with margin rules (2022).
- Data: bhavcopy has delivery quantity and delivery % directly. Note (my inference, check): stocks in trade-for-trade (BE) segments settle every trade for delivery, so their delivery share is mechanically high and should be excluded or controlled.
- Clears 35-40 bp? Untestable until measured. It is the one signal in this sweep the user's own data can measure directly.
- Overlap: 00 line 307 "Deliverable %: Reject for now" and line 312 (Part B rejected "deliverable %"). My grep of 00 finds the rejection lines but no look row that measured it, so the rejection appears to be a prior, not a result. Closed by decision; do not re-propose without the owner reopening it.

**C20. ASM / STASM inclusion: avoid-list, or fade the run-up** — NOT-HARVESTABLE long-only (avoid-list value)
- Citation: Chari & Inamdar, NISM / NSE-NYU ([NSE PDF](https://nsearchives.nseindia.com/s3fs-public/inline-files/Effectiveness%20of%20additional%20surveillance%20measures_WorkingPaper.pdf)).
- Sample: 218 events (188 unique stocks), 21 Nov 2018 to 28 Feb 2019.
- Effect: 5-day CAAR +10.51% pre-inclusion to -0.92% post-inclusion; pre-exclusion -1.10% to post +0.73% (not significant). The roughly 11-point swing is probably a selection effect, since stocks are listed after a run-up (my inference), and cannot be traded in advance.
- t / Sharpe: significant at 1% (inclusion); exclusion not significant.
- Turnover / holding: single event, 5-day window.
- Gross / net: gross abnormal return; no costs.
- Out of sample: short sample; not replicated in the sources found.
- India: this is the Indian evidence.
- Data: needs the point-in-time ASM list (NSE circulars), not in bhavcopy.
- Clears 35-40 bp? A long-only account cannot short the post-inclusion drop; post-inclusion drift of -0.92% over 5 days is a reason to avoid buying newly included stocks, not a trade.
- Overlap: not covered in 00. Related to the micro-cap / SME skip (00 line 316).

**C21. GSM stage entry / exit** — NOT-HARVESTABLE long-only; exit side untested
- Citation: Aggarwal, Bhatia, Zaveri ([NSE PDF](https://nsearchives.nseindia.com/s3fs-public/inline-files/Rules_vs_discretion_in_market_surveillance_Aggarwal_Bhatia_Zaveri_0.pdf)).
- Sample: 121 stocks entering Mar 2017 to Mar 2019, propensity-matched difference-in-differences.
- Effect: entry causes a significant price decline and a fall in trading activity; magnitude not extracted. Illiquidity ratio falls after exit.
- t / Sharpe: described as significant; not extracted.
- Turnover / holding: single event.
- Gross / net: gross.
- Out of sample: none found.
- India: this is the Indian evidence. Nearly a third of entrants did not meet the criteria, and more than half of exiters still showed them, so the list is partly discretionary.
- Data: point-in-time GSM list from NSE circulars; not in bhavcopy.
- Clears 35-40 bp? Entry is an avoid. A "buy after GSM exit" candidate has no price evidence (only the liquidity change), so it is untested.
- Overlap: not covered in 00.

**C22. T2T (BE-series) moves** — NOT-HARVESTABLE long-only (avoid-list)
- Citation: Parmar & Chaturvedula 2017 Accounting and Finance Research 6(1):1-9 ([RePEc](https://ideas.repec.org/a/jfr/afr111/v6y2017i1p9.html)); NSE rules ([NSE](https://www.nseindia.com/static/regulations/movement-securities-periodic-review)).
- Sample: not on the page.
- Effect: positive 30-day pre-event abnormal returns, significantly negative post-announcement returns, higher volatility. No figures.
- t / Sharpe: described as significant; not quantified.
- Turnover / holding: single event.
- Gross / net: gross.
- Out of sample: none found.
- India: this is the Indian evidence.
- Data: T2T lists from NSE circulars (not in bhavcopy); the series code in bhavcopy (EQ vs BE) may mark membership after the fact.
- Clears 35-40 bp? As an avoid-filter only.
- Overlap: not covered in 00.

**C23. Circuit-hit continuation (buy after an upper-circuit close)** — NOT-HARVESTABLE
- Citation: Das, arXiv:2608.08625 preprint ([arXiv](https://arxiv.org/pdf/2608.08625)).
- Sample: NSE daily data Nov 2007 to Jun 2026, 898,689 observations after exclusions.
- Effect: next-day same-boundary persistence 2%: 78.85% (n small), 5%: 44.78%, 10%: 26.74%, 20%: 14.52%. Mean next-day returns are in a figure only; no bp number extracted.
- t / Sharpe: none.
- Turnover / holding: next-day.
- Gross / net: close-to-close; no cost.
- Out of sample: single preprint, not peer reviewed.
- India: this is the Indian evidence.
- Data: bhavcopy plus the band for each stock-day (the paper had to exclude band changes). Band history is not in bhavcopy.
- Clears 35-40 bp? No. A retail buyer cannot get filled at the circuit price (the queue is one-sided), so the close-to-close continuation return is not what a delivery account earns. An open-to-close version after the gap would be a different (and costly) object.
- Overlap: 00 line 276 and line 289 (gap-and-go / gap-fade "already refuted", "results gaps are priced by the open (L36)") are the nearest; circuits are not named.

**C24. F&O ban entry / exit effects on the cash stock** — NO-EVIDENCE
- Citation: no event study found. Mechanics: [Share.Market](https://www.share.market/support/home/trading-investment/futures-and-options/other-frequently-asked-questions/why-do-fo-contracts-enter-a-ban-period/); [ICICI Direct](https://www.icicidirect.com/ilearn/stocks/articles/future-and-options-ban-impact-on-stock).
- Sample: none.
- Effect: none.
- t / Sharpe: none.
- Turnover / holding: event-driven.
- Gross / net: none.
- Out of sample: none.
- India: none found. The rule changed on 1 Oct 2025 (delta-adjusted OI; sources disagree), so any pre-2025 study would not describe current dynamics.
- Data: the daily ban list is not in bhavcopy.
- Clears 35-40 bp? Unknown.
- Overlap: 00 line 279 "Expiry-day effects: Out of mandate" is the nearest (derivatives-driven); F&O ban is not named.

**C25. Regime changes: SEBI peak margin (2020-21), the 2025 weekly-expiry and lot-size changes, margin-trading eligibility** — NO-EVIDENCE
- Citation: peak-margin timing only ([One Trade Journal](https://onetradejournal.com/glossary/upfront-margin)); pre-implementation expectation ([Business Standard](https://www.business-standard.com/amp/article/markets/volumes-in-f-o-segment-to-shrink-as-peak-margin-rules-kick-in-today-120120100063_1.html)). Nothing sourced for the 2025 weekly-expiry or lot-size changes or margin-trading eligibility.
- Sample: none.
- Effect: none measured on delivery-stock returns.
- t / Sharpe: none.
- Turnover / holding: not applicable.
- Gross / net: not applicable.
- Out of sample: not applicable.
- India: SEBI F&O FY25 study (about 91% of individual traders lost money; unique traders fell from about 61.4 lakh to about 42.7 lakh over FY25) shows the retail F&O base shrank, but that is not a delivery signal ([InvestWhat](https://www.investwhat.in/india/investment/investor-news/25062/91-lose-rs106-lakh-crore-written-off-whats-going-on-in-indias-fo-arena)).
- Data: structural-break dates only.
- Clears 35-40 bp? Not a trading signal; relevant as a regime flag when judging whether a pre-2021 backtest transfers to 2026.
- Overlap: not covered in 00.

**C26. NSE order-flow imbalance (limit-order-book signals)** — NOT-HARVESTABLE at delivery horizon
- Citation: Tripathi, Dixit, Vipul 2021 FRL 41 ([RePEc](https://ideas.repec.org/a/eee/finlet/v41y2021ics1544612320316779.html)); Rastogi, Reddy, Kotha 2013 ([RePEc](https://ideas.repec.org/a/eme/ijmfpp/v9y2013i2p92-109.html)).
- Sample: 195 active NSE stocks (Tripathi et al.).
- Effect: predictability strong for 5 minutes, gone within 30 minutes.
- t / Sharpe: not retrieved.
- Turnover / holding: minutes.
- Gross / net: gross.
- Out of sample: Rastogi et al. report the link weakened post-2002.
- India: yes, all intraday.
- Data: depth data does not exist in the local history (00 section 5b).
- Clears 35-40 bp? No: horizons of minutes against a 35-40 bp round trip.
- Overlap: 00 L37 (order-book imbalance, pending) and 00 section 5b ("the depth data does not exist here"); intraday is out of scope for this sweep.

### Inferences
- The NSE-specific literature supports one clean statement: newly surveilled stocks (ASM, GSM, T2T) have already run up before the flag and drift flat or down after it. For a long-only delivery account that is an exclusion filter on purchases, worth coding as a point-in-time list if the owner wants one, not a source of returns.
- Delivery % is the only unmeasured signal that the owner's existing data can test directly, but the project rejected it by decision (00 lines 307, 312), and no external evidence exists to give it a prior. Any look at it should be treated as a fresh family with its own trial count and should control for BE-series names and for the 2022 margin-norm shift.
- Circuit persistence is a market-microstructure fact (the Das preprint) but a retail buyer is not filled at the circuit; the number is not an edge.
- The F&O-ban, peak-margin, weekly-expiry and lot-size items have no measured delivery-stock evidence, so they cannot be ranked. They matter as structural-break dates for backtests that straddle 2020-21 and 2025.
- The NSE order-flow papers agree that the predictability decays within minutes, which is consistent with the project's own intraday closure.

### Gaps
- No study of NSE delivery % and returns; the "2019 report: NSE delivery 37% vs BSE 50%" figure was seen only in a secondary listing with no URL recorded, so it is not cited.
- No event study of F&O ban entry/exit, peak margin, the 2025 weekly-expiry / lot-size changes or margin-trading eligibility.
- Das preprint mean next-day returns are only in a figure; ASM, GSM and T2T magnitudes after exit are not reported; Parmar & Chaturvedula's sample and figures are not on the abstract page.
- The 1 Oct 2025 MWPL change is from sources that disagree; the circular was not read.
- Point-in-time ASM, GSM, T2T and ban lists would have to be assembled from NSE circulars; not tested here.

## (d) 52-week high/low, technical patterns, moving averages, gap continuation, overnight vs intraday

### Takeaway
Everything in this group is either closed in-house (patterns, rule lab, gaps, overnight) or has no Indian stock-level test (52-week high/low, moving-average timing). The one place the literature suggests a stock-level or conditioned difference, the overnight/intraday split, is already measured here at +16.78 bp overnight vs -6.94 bp intraday per stock, which is about half the 35-40 bp round trip even before conditioning.

### Cited Findings
- George-Hwang (2004, J. Finance): nearness to the 52-week high forecasts returns, in US data 1963-2001, dominating past-return forecasting with no long-run reversal. Huddart-Lang-Yetman (2009) conflicts with George-Hwang on 52-week lows — as described in [AUT working paper on 52-week high and low](https://acfr.aut.ac.nz/__data/assets/pdf_file/0011/56468/657406-H-Yu-Nearness-to-the-52-week-high-and-low-prices,-past-returns,-and-average-stock-returns.pdf). An Oslo 1990-2019 replication is positive — [NHH](https://openaccess.nhh.no/nhh-xmlui/handle/11250/2777302). Practitioner summary — [Alpha Architect](https://alphaarchitect.com/the-secret-to-momentum-is-the-52-week-high/). No Indian stock-level test found.
- Lo-Mamaysky-Wang (2000, J. Finance 55:1705-1765): kernel-regression pattern recognition on US stocks 1962-1996; several technical patterns carry some incremental information — [NBER w7613](https://www.nber.org/papers/w7613); [MIT PDF](https://web.mit.edu/wangj/www/pap/LoMamayskyWang00.pdf)
- Han-Yang-Zhou (JFQA 2013; working paper 2011; citation year differs across sources): 10-day moving-average timing applied to volatility-sorted deciles, NYSE/Amex 1963-2009; high-volatility portfolios earn large abnormal returns, above momentum, and survive transaction costs — [Han, Yang, Zhou PDF](https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Han_Yang_Zhou.pdf); [Alpha Architect](https://alphaarchitect.com/technical-analysis-may-actually-work/); [Cambridge](https://resolve.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/new-anomaly-the-crosssectional-profitability-of-technical-analysis/B9E41049F2E55B4F274D46E72ECA8E29)
- Moving averages in emerging markets: a cross-market study says rules do better in emerging markets but costs can erase profits; Dhaka, Saudi and European studies are mixed. No NSE-specific moving-average study found — [Dobbs, Newcastle](https://www.staff.ncl.ac.uk/i.m.dobbs/Files/Jordan%20n.pdf); [Dundee](https://discovery.dundee.ac.uk/en/publications/the-predictive-ability-and-profitability-of-moving-average-rules-/)
- Lou-Polk-Skouras (2019, JFE): momentum and reversal profits are earned almost entirely in one session, with opposite signs overnight and intraday (US evidence) — [LSE Research Online](https://researchonline.lse.ac.uk/id/eprint/87481); [NBER conference paper](https://conference.nber.org/conf_papers/f78239/f78239.pdf). A Thai 2014-2024 "tug-of-war" study exists — [TCI Thai](https://so09.tci-thaijo.org/index.php/PMR/article/view/8411). An Indian intraday prior-return paper finds reversals within minutes, not an overnight/intraday split — [Publishing India](https://publishingindia.com/archive/ijfm/prior-return-effect-in-indian-stock-market-an-intra-day-analysis)
- Project's own measurements (not external): stock-level overnight +16.78 bp (t +9.50) vs intraday -6.94 bp (t -2.80) (L23, 00 line 194); universe B overnight +19.84 bp vs intraday -9.93 bp (L27, line 198); volatility-sorted overnight -14.15 bp, t -8.55 (L28, line 199); index-level like-for-like overnight +3.91 bp vs intraday -0.21 bp (L30, line 201); overnight ETF trials 124 and 125 FAIL, net -6.42 bp a night at t -5.88 (00 section 1c); results gaps priced by the open (L36, line 207); 09:45 gap reversal FAIL, 0 of 13 (L49, line 220); rule-lab search 104,655 combinations, 0 survivors (L55); combo search 0 of 75 passes (trials 128-202) (00 section 1c)
- Adjacent: "Physical Momentum in the Indian Stock Market" is a momentum paper, not a 52-week test — [arXiv 2302.13245](https://arxiv.org/pdf/2302.13245)

### Candidate catalogue (52-week, technical, overnight, gap)

**C27. 52-week-high proximity (and 52-week low) as a stock-selection signal** — NO-EVIDENCE for India; CLOSED-IN-HOUSE as an input
- Citation: George & Hwang 2004 J. Finance ([AUT summary](https://acfr.aut.ac.nz/__data/assets/pdf_file/0011/56468/657406-H-Yu-Nearness-to-the-52-week-high-and-low-prices,-past-returns,-and-average-stock-returns.pdf)); Oslo replication ([NHH](https://openaccess.nhh.no/nhh-xmlui/handle/11250/2777302)).
- Sample: US 1963-2001; Oslo 1990-2019.
- Effect: magnitude not retrieved; direction positive, with no long-run reversal.
- t / Sharpe: not retrieved.
- Turnover / holding: monthly to quarterly; the ranking moves slowly, so turnover is lower than reversal (not measured).
- Gross / net: not retrieved.
- Out of sample: Oslo positive; Huddart-Lang-Yetman 2009 conflict on lows.
- India: none found at stock level.
- Data: bhavcopy closes (rolling 252-day high); yes, with corporate-action adjustment.
- Clears 35-40 bp? Plausible on turnover; unknown on gross.
- Overlap: 00 line 316 "52-week-high proximity (section 85 input)" and line 328 "52-week high, lookback grids ... Leave". Closed as a momentum-book variant.

**C28. Moving-average timing on volatility-sorted portfolios (Han-Yang-Zhou), or single-stock MA rules** — FAILS-ON-COST likely; CLOSED-IN-HOUSE
- Citation: Han, Yang, Zhou JFQA 2013 ([PDF](https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Han_Yang_Zhou.pdf)); EM rules ([Dobbs](https://www.staff.ncl.ac.uk/i.m.dobbs/Files/Jordan%20n.pdf)).
- Sample: NYSE/Amex 1963-2009.
- Effect: large abnormal returns in high-volatility deciles, above momentum, surviving transaction costs (US); no bp figure retrieved.
- t / Sharpe: not retrieved.
- Turnover / holding: 10-day MA crossing signals trade often per name; turnover high (not measured in my sources).
- Gross / net: the paper claims it survives US costs; the EM cross-market study says costs can erase profits.
- Out of sample: no replication found for India.
- India: none found.
- Data: bhavcopy closes; yes.
- Clears 35-40 bp? Unlikely at single-stock signal frequency with a Rs 15.34 DP per sell; the high-volatility decile is also the most illiquid.
- Overlap: 00 line 312 lists "trend filter" as rejected; L55 rule lab 0 survivors of 104,655; combo search 0 of 75 (00 section 1c). Closed.

**C29. Chart-pattern recognition (Lo-Mamaysky-Wang)** — CLOSED-IN-HOUSE
- Citation: Lo, Mamaysky, Wang 2000 J. Finance 55:1705-1765 ([NBER](https://www.nber.org/papers/w7613)).
- Sample: US 1962-1996.
- Effect: patterns carry some information; no bp conversion retrieved.
- t / Sharpe: not retrieved.
- Turnover / holding: days to weeks.
- Gross / net: gross information content, not a net strategy.
- Out of sample: none found for India.
- India: none found.
- Data: bhavcopy OHLC; yes.
- Clears 35-40 bp? Not shown.
- Overlap: L15 (Bulkowski swing patterns), L55 rule lab (0 survivors), trial 117 (Smart Money, FAIL, net -0.299R, t -5.56) and the combo search (0 of 75) (00 sections 1c, 1d, look table). Do not re-propose.

**C30. Overnight vs intraday at stock level, plain or conditioned** — CLOSED-IN-HOUSE for the plain version; conditioned version untested
- Citation: Lou, Polk, Skouras 2019 JFE ([LSE](https://researchonline.lse.ac.uk/id/eprint/87481)).
- Sample: US (paper); NIFTY 100 and universe B (in-house L23, L27, L28, L30).
- Effect: in-house stock-level overnight +16.78 bp vs intraday -6.94 bp; universe B +19.84 vs -9.93 bp. The paper's headline is that momentum and reversal profits sit in opposite sessions.
- t / Sharpe: +9.50 overnight, -2.80 intraday (L23).
- Turnover / holding: one round trip per night; buy at close, sell at next open.
- Gross / net: the in-house figures are gross; the overnight ETF version nets -6.42 bp a night (trial 124, t -5.88).
- Out of sample: ETF overnight FAIL; index-level overnight shrinks to +3.91 bp (L30).
- India: the in-house numbers are the India evidence; no external stock-level study found.
- Data: bhavcopy open and close are enough.
- Clears 35-40 bp? No as stated. The unconditional average (about 17-20 bp) would have to roughly double to clear a 35-40 bp round trip, so a conditioned version needs a bucket averaging above about 40 bp a night. Nothing found measures that.
- Overlap: 00 lines 194-201 and the pivot brief's closed list ("overnight ETF"). Plain version closed; conditioned (by prior-day reversal, volume or delivery %) is the only open variant.

**C31. Gap continuation / fade at daily-plus horizon** — CLOSED-IN-HOUSE
- Citation: in-house L36, L49 (00 lines 207, 220); Indian intraday prior-return paper ([Publishing India](https://publishingindia.com/archive/ijfm/prior-return-effect-in-indian-stock-market-an-intra-day-analysis)).
- Sample: NIFTY 100 5-minute data 2024-09 to 2026-09.
- Effect: results gaps priced by the open (aligned drift +5.9 bp at 30 minutes, 0 by the close); 09:45 gap reversal FAIL, 0 of 13.
- t / Sharpe: aligned gap +82.7 bp, t 4.78 (L36).
- Turnover / holding: intraday.
- Gross / net: gross.
- Out of sample: external Indian paper finds reversals within minutes.
- India: yes.
- Data: bhavcopy has the daily gap; Kite 5-minute for NIFTY 100.
- Clears 35-40 bp? No at intraday horizon.
- Overlap: 00 lines 276 and 289 "Gap-and-go / gap-fade: Already refuted".

### Inferences
- The overnight/intraday decomposition is the most promising of the "conditioned difference" ideas the literature suggests, but the in-house baseline (about 17-20 bp gross a night) is already half the cost hurdle, and the ETF version lost money net. Only a conditioning signal that doubles the gross per night would change that, and no source reports one.
- 52-week-high and moving-average rules are momentum cousins. Any new trial on them counts toward the momentum family (bar t >= 2.865 at N = 12, 2.891 next), which is a high bar for effects with no Indian estimate.
- The technical-pattern line has been searched as exhaustively as it can be with this data (104,655 + 24,026 rule combinations, 75 combo-search tests, all zero survivors), so the external papers add no case for reopening it.

### Gaps
- No Indian stock-level 52-week-high/low study, no Indian moving-average study (Marshall et al. on emerging markets was not retrieved), no Indian stock-level overnight/intraday decomposition outside the project's own.
- George-Hwang return magnitudes not retrieved. A Taiwan 52-week replication and an index-level emerging-market result (weak or negative) were in my working notes without a pinned URL, so they are excluded from Cited Findings.
- Han-Yang-Zhou bp figures and the exact citation year (2011 working paper vs 2013 JFQA) not pinned.
- Lo-Mamaysky-Wang effect sizes not retrieved.

## (e) Post-publication decay and emerging-market replication: do these effects still pay, and in India?

### Takeaway
Published anomalies shrink in the US (McLean-Pontiff: 26% lower out of sample, 58% lower post-publication) but Jacobs-Muller find no reliable post-publication decline outside the US across 38 other markets, so decay is not the main risk for an Indian test; costs, thin samples and the 2008-2026 regime are. Short-term reversal, post-earnings drift and momentum earn similar returns in emerging and developed markets (Griffin-Kelly-Nardari), yet the net-of-cost US evidence for reversal is negative.

### Cited Findings
- McLean & Pontiff (2016, J. Finance): across 97 return predictors, returns are 26% lower out of sample and 58% lower post-publication — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623); [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365)
- Jacobs & Muller (2020, JFE 135(1):213-230): 241 anomalies in 39 markets; the US is the only country with a reliable post-publication decline (62% equal-weighted, 66% value-weighted post-publication; post-sample 38% and 37%); no reliable decline in the other 38 markets — [RePEc](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html)
- Griffin-Kelly-Nardari (2010, RFS 23(8):3225-3277): across 56 markets, short-term reversal, post-earnings drift and momentum earn similar returns in emerging and developed markets — [RePEc](https://ideas.repec.org/a/oup/rfinst/v23y2010i8p3225-3277.html)
- Reversal costs in the modern US sample: gross 0.37%/month turns into -1.28%/month net; the best banded low-volatility industry-relative variant is +0.28%/month net — [Novy-Marx & Velikov](https://mysimon.rochester.edu/novy-marx/research/ToAatTC.pdf)
- Indian momentum, gross, 1995-2008: 12-month winners-minus-losers +2.03%/month, 6-month +0.96%/month — [Joshipura](https://nsearchives.nseindia.com/content/research/res_paperfinal223.pdf). The project's own momentum book, 2010-2025, nets +0.71%/month at t 2.51 (trial 126, 00 section 1c).
- India's high-volume return premium is weaker than the US and significant only at 5% / 10% — [Singh, Wang, Hua 2025](https://ideas.repec.org/a/eee/pacfin/v91y2025ics0927538x2500126x.html)

### Candidate catalogue (decay status, all 31 candidates)
- Negative on cost in the modern US sample: C1, C9 (C2 shows a 56 bp breakeven, but that figure is secondary and pre-2009). Surviving only with turnover cuts: C3, C5, C8.
- No decay estimate exists for India for any candidate. India-specific post-publication tests: none found.
- External-evidence-only (US or cross-country, no Indian magnitude): C2, C3, C6, C7, C11, C12, C13, C14, C15, C16, C17, C27, C28, C29.
- Indian evidence exists but is gross or direction-only: C1 (monthly Nifty mean reversion), C4, C5, C8, C10, C14, C16, C18, C20, C21, C22, C23, C26.
- No study: C19, C24, C25. Closed in-house: C1 (via Sahab Ranker), C27 (as an input), C28, C29, C30 (plain), C31.

### Inferences
- Triage by feasibility on cost, Indian support and non-closure (my judgement):
  - Tier A (cost-feasible by turnover, Indian evidence, not closed in-house): C8 (3-year contrarian, long leg +0.49%/month gross, one 1995-2008 sample), C5 (reversal after large monthly moves, up to 6 months, no magnitude), C10 (standalone Amihud / illiquidity tilt, direction only; tested before as a Ranker input), C4 (low-volume-shock reversal over 20 days, no magnitude). Not one of them has a net, post-2010 Indian estimate. Each would need its own pre-registration and family count.
  - Tier B (evidence elsewhere, bhavcopy can implement, no Indian magnitude): C2, C3 (needs industry labels), C11, C12, C13, C14, C15 (momentum-family trial), C18, C27.
  - Tier C (not harvestable long-only, no evidence, wrong data or wrong horizon): C6, C16, C17, C19 to C26, and the closed lines C28 to C31 and C1. C20 to C22 are worth keeping as exclusion filters.
- Honest bottom line: nothing in this sweep demonstrably clears 35-40 bp net in India. The reversal literature's own cost arithmetic (breakeven turnover, NMV's banded variant) says that only slow sleeves can survive, and the Indian papers behind those slow sleeves are gross-only, old and unreplicated.
- Decay is likely not the dominant risk (Jacobs-Muller), but a haircut convention is still prudent: McLean-Pontiff's 26% out-of-sample and 58% post-publication shrinkage are US averages across all anomalies, not India measurements, so they are a ceiling on optimism rather than an estimate.
- The gap between Joshipura's gross 12-month momentum (+2.03%/month, 1995-2008) and the project's net +0.71%/month (2010-2025) is consistent with decay plus costs, but the constructions differ (long-short vs long-only book, gross vs net), so it is not a clean decay measurement.

### Gaps
- No post-publication decay estimates for India for any individual candidate; Jacobs-Muller report the pooled non-US result, not per-country or per-anomaly India figures.
- McLean-Pontiff shrinkage is a US average over 97 predictors, not for reversal or liquidity signals in particular.
- NMV Table 3 sample years and the exact cost model were not carried into these notes.
- A clean out-of-sample Indian test of any candidate would require running it on the 2010-2026 bhavcopy panel with the 2026 window held out (00 section 5), which is outside this sweep.
