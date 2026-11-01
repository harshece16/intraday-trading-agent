# India factor zoo, ML cross-section and open-source NSE/BSE backtests (06)

Scope: Part A is the systematic factor-zoo and machine-learning cross-sectional literature as it applies to Indian equities, plus the international replications that set priors, plus the niftyindices.com factor-index track records. Part B is open-source NSE/BSE strategy implementations that publish backtests. Today is 2026-11-01. The India evidence in this file runs to December 2025 for the JKP panel and to 30 September 2026 for the factor-index factsheets; no published ML study on Indian stocks that I could open runs later than 2017 on its test window (Choi-Jiang-Zhang) except the November 2025 LLM paper (Sodha).

Read first: `00-already-covered.md` in this folder. Section 1 of that file (tested and closed lines, trials 1-204) is closed and nothing here re-proposes it; where a row overlaps, the overlap note says which line. Cost hurdle used throughout: about 33-39 bp for a delivery round trip at Rs 33,000 notional (33.05 bp; 39.05 bp with slippage doubled; about 41 bp at Rs 3 lakh; 56.1 bp at Rs 5,500) per [00-already-covered.md section 6](00-already-covered.md); I use 38 bp as the single working number. All effect sizes are converted to percent per month (%/mo). Where a source reports a Sharpe ratio only, the conversion is impossible without the volatility and that is recorded as a gap, not guessed.

How to read the evidence grades in this file: "primary" = I opened the paper, data file, factsheet or README myself; "search-summary" = I only saw a search-result summary and did not open the full text, so the number is unverified and is flagged as such.

## 1. What do the replication and multiple-testing papers imply for how many anomalies survive, and do they cover India?

### Takeaway
Most published anomalies fail once microcaps, value-weighting and multiple-testing thresholds are applied (Hou-Xue-Zhang: 85% fail |t| >= 3; Harvey-Liu-Zhu: new factors need t > 3.0), yet Jensen-Kelly-Pedersen find replication above 75% in 10 of 13 themes across 93 countries, and Jacobs-Müller find a reliable post-publication decline only in the US. None of these papers' India-specific rows could be obtained, so the usable India evidence is the JKP India panel analysed in section 2.

### Cited Findings
- Hou-Xue-Zhang (NBER w23394, RFS 2020) build 447 anomalies; with microcaps neutralised by NYSE breakpoints and value-weighting, 286 (64%) are insignificant at the 5% level, 380 (85%) fail a |t| >= 3 bar, and 95 of 102 liquidity-related variables fail — [NBER w23394](https://www.nber.org/papers/w23394)
- Harvey-Liu-Zhu (NBER w20592, RFS 2016) argue that, after accounting for the number of factors tried, a newly proposed factor needs a t-statistic above 3.0 rather than 2.0 — [NBER w20592](https://www.nber.org/papers/w20592)
- Jensen-Kelly-Pedersen (Journal of Finance 78(5), 2465-2518, 2023; NBER w28432) study 153 factors in 13 themes across 93 countries and report that replication exceeds 75% in 10 of the 13 themes; the exceptions are Seasonality, Leverage and Size — [NBER w28432](https://www.nber.org/papers/w28432); [JF page](https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13249)
- The JKP factor data (country-level, EW and capped-VW, monthly) is public, so the India panel can be rebuilt from their files rather than from the paper — [jkpfactors.com](https://jkpfactors.com); [JKP documentation](https://jkpfactors-data.s3.amazonaws.com/documents/Documentation.pdf)
- Jacobs-Müller (Journal of Financial Economics 135, 213-230, 2020, "Anomalies across the world: once public, no longer existent?") test 241 anomalies in 39 markets; the US is the only market with a reliable post-publication decline in anomaly returns — [SSRN 2816490](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2816490) (abstract only; the full country table was not retrievable)
- Choi-Jiang-Zhang (2023) state that their machine-learning Sharpe ratios "do not take into account transaction costs or other frictions, such as short-sale constraints" — [Choi-Jiang-Zhang, ABFER 2023 PDF](https://www.abfer.org/media/abfer-events-2023/annual-conference/papers-investment/AC23P3084-Alpha-Go-Everywhere-Machine-Learning-and-International-Stock-Returns.pdf)

### Inferences
- The two literatures are consistent once the weighting is specified: equal-weighted tercile spreads include the microcap tail and overstate what a tradable book earns (HXZ), while value-weighted spreads are weaker but more replicable internationally (JKP, Jacobs-Müller). That is exactly the pattern in the India JKP panel (section 2): 32 equal-weighted factors clear t >= 3 but only six value-weighted ones do.
- Because Jacobs-Müller find no reliable post-publication decay outside the US, "it was published, so it is arbitraged away" is a weak argument against a non-US factor; the stronger arguments against any single India candidate are the HLZ bar, the correlation among the 153 factors, and the 204-trial count of record in the project file.
- A candidate drawn from this file would have to be pre-registered as a new family (lower bar than the momentum family's t >= 2.865) but would still face the project-wide deflated Sharpe penalty; a naive JKP t of 2.5-4 is not a pass.

### Gaps
- McLean-Pontiff (Journal of Finance 2016, "Does academic research destroy stock return predictability?"): the source page returned 403 and no mirror was opened. My recollection (unverified, from memory, not for citation) is a post-publication decline of roughly 58% of in-sample returns, about 26% attributable to data-mining; no India subset is reported in what I remember. Treat as unsourced.
- Jacobs-Müller India country row (anomaly-by-anomaly long-short %/mo for India and the pre/post-publication split): not obtained; SSRN and ScienceDirect returned 403 and the HU-Berlin PDF was blocked by an anti-bot page.
- Griffin-Kelly-Nardari (Review of Financial Studies 2010, emerging versus developed market efficiency measures, includes India): I did not obtain the paper or any summary of its India results within the search budget; nothing from it is used here.
- Gu-Kelly-Xiu (RFS 2020) has no India sample; its US neural-net long-short Sharpe (about 1.35 value-weighted in a search-result summary, not opened) is therefore only a US baseline, and the nearest India extension is Choi-Jiang-Zhang in section 3.
- The WebSearch budget ran out partway through the task, so items that would normally have been closed by a second search (for example the Dividend Opportunities 50 factsheet, additional India anomaly papers) are listed as gaps rather than chased.

## 2. What does the systematic factor zoo look like in India (Jensen-Kelly-Pedersen panel, 153 factors, to December 2025)?

### Takeaway
India is in the JKP panel, and rebuilding it from their public files gives the only complete, current, same-method anomaly table for Indian stocks: 32 of 153 factors clear t >= 3 equal-weighted but only six clear it value-weighted (fcf_me, mispricing_mgmt, noa_gr1a, ret_6_1, ret_9_1, seas_1_1na; ret_12_1 sits at t 2.97). The India winners are momentum (stronger value-weighted than equal-weighted), accruals and net-operating-asset growth, free-cash-flow value, and earnings surprise (equal-weighted only); the classic profitability, quality, leverage and low-risk factors are about zero or negative. All numbers are gross, tercile long-short, and the equal-weighted ones are dominated by small stocks.

### Cited Findings
Construction (JKP documentation, primary):
- JKP factors are tercile long-short portfolios formed with non-micro-cap breakpoints, held one month, available equal-weighted (EW) and capped value-weighted (VW-cap), gross of costs, with a four-month lag on accounting data, and each factor is signed to its published direction — [JKP documentation](https://jkpfactors-data.s3.amazonaws.com/documents/Documentation.pdf)
- I downloaded the India files (`[ind]_all_factors_monthly_ew` and `..._vw_cap`, plus the `all_themes` files) and recomputed mean, naive t-statistic (mean / (sd / sqrt(n))), and the splits before and after 1 January 2015 for every factor — [jkpfactors.com data page](https://jkpfactors.com/data); S3 bucket `jkpfactors-data.s3.amazonaws.com/public/` (file names as above). The statistics are mine, computed with throwaway scripts in the scratchpad, not JKP's published numbers. The t-statistics are naive: not Newey-West, not adjusted for 153 x 2 tests, and the factors are highly correlated.
- Coverage: 153 factors, India monthly series start between 1988 and 2008 depending on the factor and run to 2025-12; the average cross-section is roughly 1,000-2,000 stocks per month for most factors (for example 1,309 for ret_12_1), far wider than the tradable top 400-800 by traded value in the project's universe definition.

Headline counts (primary, my computation on the JKP India files):
- EW tercile spread: 114 of 153 factor means are positive; mean of the 153 factor means +0.24 %/mo; 32 factors have t >= 3; 25 more have 2 <= t < 3.
- VW-cap tercile spread: 111 of 153 means are positive; mean of means +0.16 %/mo; 27 factors have t >= 2; six have t >= 3: noa_gr1a +0.81 %/mo (t 4.3), ret_6_1 +0.96 (3.6), mispricing_mgmt +0.90 (3.6), fcf_me +0.94 (3.1), ret_9_1 +0.91 (3.1), seas_1_1na +0.93 (3.1); ret_12_1 +0.93 (2.97).
- The positive-mean counts are not independent evidence: every factor is signed to its US-published direction, so a positive mean is the default expectation.
- Mean of the 153 factor means before 2015 versus 2015-2025: EW +0.21 to +0.29 %/mo (no decay); VW-cap +0.21 to +0.10 %/mo (halved).
- VW-cap t >= 2 list (27): noa_gr1a, mispricing_mgmt, ret_6_1, fcf_me, ret_9_1, seas_1_1na, ret_12_1, oaccruals_ni, ret_12_7, ami_126d, cowc_gr1a, oaccruals_at, dolvol_126d, ocf_at_chg1, nncoa_gr1a, coa_gr1a, inv_gr1, prc_highprc_252d, ni_inc8q, inv_gr1a, lnoa_gr1a, ncoa_gr1a, chcsho_12m, mispricing_perf, ret_3_1, noa_at, corr_1260d. Of these, only the momentum family, fcf_me, mispricing_mgmt, noa_gr1a, ni_inc8q and inv_gr1 keep t >= 1.7 in 2015-2025 VW-cap.
- Negative list (EW or VW-cap t <= -2; the sign is opposite to the US-published one): age, aliq_mat, capx_gr1, dolvol_var_126d, dsale_drec, iskew_ff3_21d, iskew_hxz4_21d, ni_ar1, o_score, saleq_gr1, turnover_var_126d, z_score. Largest: saleq_gr1 EW -0.91 %/mo (t -6.7), aliq_mat EW -1.49 (-6.0), dsale_drec EW -0.34 (-4.0), o_score EW -0.99 (-3.3), ni_ar1 EW -0.31 (-3.2), age VW -1.15 (-2.9).

Theme level (JKP's 13 clusters; mean-return series of the themes; %/mo, naive t in brackets; EW all / EW pre-2015 / EW 2015-25 // VW-cap all / VW pre-2015 / VW 2015-25; primary, my computation on the JKP India theme files):

| Theme | EW all | EW pre-15 | EW 15-25 | VW all | VW pre-15 | VW 15-25 |
|---|---|---|---|---|---|---|
| Accruals | +0.31 (2.7) | +0.47 (2.3) | +0.13 (1.5) | +0.25 (1.3) | +0.37 (1.1) | +0.11 (0.9) |
| Debt issuance | +0.06 (0.6) | +0.01 (0.1) | +0.11 (2.1) | +0.13 (0.6) | +0.20 (0.6) | +0.03 (0.4) |
| Investment | -0.00 (-0.0) | -0.03 (-0.1) | +0.04 (0.4) | +0.14 (0.7) | +0.11 (0.4) | +0.19 (1.5) |
| Low leverage | -0.46 (-1.5) | -0.57 (-1.3) | -0.20 (-1.9) | -0.53 (-1.6) | -0.71 (-1.5) | -0.15 (-0.9) |
| Low risk | +0.30 (1.7) | +0.19 (0.8) | +0.55 (3.5) | +0.10 (0.5) | +0.12 (0.4) | +0.06 (0.3) |
| Momentum | +0.39 (2.0) | +0.27 (1.0) | +0.67 (3.5) | +0.79 (3.4) | +0.90 (2.8) | +0.51 (2.4) |
| Profit growth | +0.47 (4.3) | +0.46 (3.0) | +0.49 (7.5) | +0.39 (2.4) | +0.50 (2.2) | +0.14 (1.6) |
| Profitability | -0.28 (-1.2) | -0.47 (-1.3) | +0.03 (0.2) | -0.10 (-0.5) | -0.12 (-0.4) | -0.08 (-0.4) |
| Quality | +0.21 (1.0) | +0.21 (0.7) | +0.21 (1.4) | +0.28 (1.3) | +0.41 (1.4) | -0.01 (-0.0) |
| Seasonality | +0.32 (3.2) | +0.37 (2.5) | +0.21 (4.0) | +0.09 (0.5) | +0.07 (0.3) | +0.12 (2.1) |
| Short-term reversal | +0.56 (4.6) | +0.62 (3.8) | +0.41 (3.3) | -0.26 (-1.7) | -0.35 (-1.7) | -0.07 (-0.6) |
| Size | +0.50 (2.1) | +0.32 (1.0) | +0.93 (2.7) | +0.19 (1.0) | +0.14 (0.6) | +0.31 (1.3) |
| Value | +0.37 (2.3) | +0.29 (1.3) | +0.54 (4.0) | +0.25 (1.1) | +0.27 (0.8) | +0.20 (1.0) |

(JKP's cluster labels are data-driven and can look odd: ret_12_7 sits in Profit growth and seas_16_20na in Accruals. The Quality? flags in the appendix mark two Stambaugh-Yuan mispricing factors that the documentation file did not label; I assigned them by judgement.)

Factors relevant to the project's candidate lines (primary; %/mo, naive t; the "Data" column is P = prices and corporate actions only, F = needs fundamentals; the last column compares with `00-already-covered.md`):

| Factor (original paper) | EW all | VW-cap all | VW-cap 2015-25 | Data | Overlap with 00-already-covered.md |
|---|---|---|---|---|---|
| ret_12_1 (Jegadeesh-Titman 1993) | +0.65 (2.7) | +0.93 (3.0) | +0.81 (2.7) | P | Closed: slow cross-sectional momentum family, trials 119, 120, 126, 127, 204 (section 1c) |
| ret_9_1, ret_6_1 | +0.47 (2.1), +0.35 (1.6) | +0.91 (3.1), +0.96 (3.6) | +0.80 (2.7), +0.66 (2.5) | P | Closed: same family; lookback grids "Leave" (3g) |
| ret_12_7 (Novy-Marx 2012 intermediate momentum) | +0.64 (3.3) | +0.71 (2.6) | +0.57 (2.2) | P | Same family; not run as a separate trial |
| seas_1_1na (Heston-Sadka 2008) | +0.35 (1.5) | +0.93 (3.1) | +0.69 (2.4) | P | Not in 00 as such; correlated with momentum, treat as a momentum variant |
| prc_highprc_252d (George-Hwang 2004) | +0.53 (1.9) | +0.70 (2.3) | +0.38 (1.2) | P | 3g "Leave": 52-week high; 3f "Skip" |
| resff3_12_1 (Blitz et al. residual momentum) | +0.91 (6.6) | +0.25 (1.4) | +0.41 (2.3) | P | 3e #5 "Defer", 3g "Leave" |
| ret_1_0 (Jegadeesh 1990 reversal) | +0.45 (2.2) | -0.36 (-1.4) | +0.27 (1.2) | P | 3e #12 "Reject"; trials 121-122; 3f "Skip" |
| fcf_me (Lakonishok et al. 1994) | +0.74 (6.0) | +0.94 (3.1) | +0.36 (2.1) | F | Value composite: 3f lists it among "worth a test"; 3g labels value "Leave"; never run |
| be_me, ebitda_mev, sale_me, ni_me, div12m_me | +0.63 (1.3), +0.36 (1.4), +0.79 (1.9), +0.55 (2.5), +0.39 (1.8) | -0.07 (-0.1), -0.01 (-0.0), +0.32 (0.7), +0.12 (0.3), +0.26 (1.0) | +0.23, +0.29, +0.35, +0.23, +0.11 (all t < 1.1) | F | 3g "Leave" (value, dividend yield); EW-only effects |
| noa_gr1a (Hirshleifer et al. 2004) | +0.66 (3.3) | +0.81 (4.3) | +0.33 (1.7) | F | Not in 00 (no investment or net-operating-asset line) |
| oaccruals_at (Sloan 1996) | +0.56 (3.9) | +0.63 (2.5) | +0.21 (1.2) | F | Not in 00 (grep for accruals returns nothing) |
| oaccruals_ni, cowc_gr1a | +0.42 (3.5), +0.34 (2.8) | +0.68 (2.9), +0.48 (2.5) | +0.16 (0.8), +0.20 (1.3) | F | Not in 00 |
| mispricing_mgmt (Stambaugh-Yuan 2016) | +0.70 (2.7) | +0.90 (3.6) | +0.38 (1.9) | F | Not in 00; a composite of management-related anomalies |
| chcsho_12m (Pontiff-Woodgate), netis_at (Bradshaw et al.) | +0.33 (1.3), +0.77 (4.0) | +0.68 (2.1), +0.56 (1.6) | -0.15 (-0.5), +0.08 (0.3) | F | Partial: Pivot B names buyback/promoter events (section 4 of 00); share-count issuance is a different, fundamentals-derived signal |
| inv_gr1 (Belo-Lin), inv_gr1a | -0.01 (-0.1), +0.09 (0.7) | +0.36 (2.3), +0.44 (2.2) | +0.48 (3.1), +0.21 (1.3) | F | Not in 00; EW zero, so a large-cap-only effect, likely noise |
| niq_su (Foster-Olsen-Shevlin 1984), saleq_su | +0.91 (7.5), +0.72 (5.7) | +0.26 (1.2), -0.22 (-0.6) | +0.23, +0.11 | F | Closed: PEAD stage A NO-GO (L39, gross +0.25 %/mo, NW t 1.41), 3f "earnings momentum closed by §84" |
| f_score (Piotroski 2000) | +0.68 (4.7) | +0.30 (1.6) | +0.01 (0.0) | F | 3f "Skip" quality (ROE, leverage); 3g quality "Leave" |
| qmj, qmj_prof | +0.04 (0.2), +0.09 (0.3) | +0.09 (0.3), -0.06 (-0.2) | -0.00, -0.12 | F | 3g quality "Leave"; zero in India |
| op_at, gp_at, ope_be (profitability) | -0.38 (-1.2), +0.16 (0.6), +0.07 (0.3) | -0.02, -0.20, +0.45 | -0.07, -0.26, +0.19 (all t < 1) | F | 3f "Skip" quality; zero or negative in India |
| z_score, o_score (Dichev 1998) | -1.01 (-2.5), -0.99 (-3.3) | +0.10 (0.2), -0.55 (-1.7) | -0.44, -0.44 | F | Not in 00; opposite sign to the US (distressed names outperform in EW) |
| beta_60m, ivol_ff3_21d, rvol_21d | +0.20 (0.8), +0.19 (0.8), +0.08 (0.3) | -0.14 (-0.4), -0.05 (-0.2), +0.03 (0.1) | -0.28, -0.00, +0.03 | P | 3f "Skip" beta/IVOL (tested in §85); 3g low-vol sleeve "Leave"; Pivot B low-vol overlay untested as a trial |
| market_equity (Banz), ami_126d (Amihud), turnover_126d, zero_trades_252d | +0.60 (2.2), +1.01 (3.0), +1.30 (4.9), +1.28 (5.0) | +0.18 (0.8), +0.60 (2.5), +0.43 (1.9), +0.40 (1.8) | +0.39, +0.40, +0.17, +0.18 (all t < 1.4) | P | 3f "Skip" size tilt, liquidity, illiquidity; "Deliverable %" 3e #10 "Reject for now" |

(Full 153-row table at the end of this section as an appendix.)

Cross-checks against in-house results (primary for JKP, secondary for the in-house numbers):
- JKP India SUE (niq_su) is +0.91 %/mo EW (t 7.5) but +0.26 %/mo VW-cap (t 1.2); the in-house PEAD stage A on NIFTY 100 found gross +0.25 %/mo with Newey-West t 1.41 — [00-already-covered.md section 1d](00-already-covered.md). The two agree once the universe is large caps: the earnings-surprise effect in India lives in the small-cap tail.
- JKP India 12-1 momentum VW-cap +0.93 %/mo gross (t 3.0) against the in-house slow momentum book's net excess +0.71 to +1.02 %/mo (t 2.5-2.8) for trials 126-127 — [00-already-covered.md section 1c](00-already-covered.md); the magnitudes line up, so JKP is corroboration, not an independent test.
- JKP India EW short-term reversal is positive to 2014 (+0.84 %/mo, t 3.1) and negative from 2015 (ret_1_0 EW -0.48 %/mo, t -1.7), and the VW-cap sign is negative over the full sample (-0.36, t -1.4): consistent with the closed reversal trials 121-122.
- JKP India low-risk theme VW-cap is +0.10 %/mo (t 0.5) and the three headline low-vol factors are not distinguishable from zero: a negative prior for the Pivot B low-vol/quality overlay line in [00-already-covered.md section 4](00-already-covered.md).

### Inferences
- The tradable question is the VW-cap column in 2015-2025, not the EW column. On that screen, price-only factors that survive are the momentum family (ret_6_1, ret_9_1, ret_12_1, ret_12_7, seas_1_1na), all already represented by the closed momentum family. Everything new in the survivors list needs fundamentals (accruals, noa_gr1a, fcf_me, mispricing_mgmt).
- Among the fundamentals-based survivors, the 2015-2025 VW-cap spreads are small and mostly below t 2 (accruals +0.2 %/mo, noa_gr1a +0.33, fcf_me +0.36, mispricing_mgmt +0.38). Using a rule of thumb that the long-only half captures at most half to two thirds of a spread (an assumption; the JKP India file stores only the long-short return), the long leg would be worth perhaps 0.1-0.25 %/mo gross. That is comparable to or below the cost drag of a monthly re-sort, but above it for a slow annual re-sort (see section 7).
- EW anomalies that vanish in VW-cap (SUE, F-score, reversal, liquidity, residual momentum, most value ratios) are almost certainly microcap or illiquidity premia: they cannot be harvested through delivery-only buys at Rs 33,000 per position without paying a spread and impact that the 22 bp + 10 bp schedule does not include.
- Pre-2015 versus 2015-2025 splits show the VW-cap spreads of the accruals, investment and quality themes roughly halving or vanishing after 2015 (accruals +0.37 to +0.11, quality +0.41 to -0.01), while momentum fell from +0.90 to +0.51 but stayed above t 2. This is the ordinary post-publication pattern, not proof of decay: 132 months have a standard error near 0.3 %/mo.
- The negative list matters as much as the positive one: the quality/leverage/profitability family (the factors a practitioner would reach for first) has the wrong sign in India, and the Indian value premium is carried by cash-flow and earnings multiples in the EW sort, not book-to-market in the VW sort.

### Gaps
- The JKP India panel is gross, long-short and tercile-based. It does not give the long-only leg, turnover, or capacity, so net-of-cost %/mo cannot be computed from it; the register in section 7 uses stated turnover assumptions instead.
- JKP's India stock universe (Compustat Global-type coverage, 1,000-2,000 names) is not the project's top-400-to-800 universe, and I did not re-run any factor on the project's universe or bhavcopy data.
- The t-statistics are naive; no Newey-West, no correction for 153 x 2 tests, no adjustment for the roughly 0.5-0.8 correlations inside each theme.
- JKP's India fundamental data begins around 1999-2000 for most accounting factors, which is short against 20-year-plus US samples.
- I used throwaway Python descriptive-statistics scripts on the downloaded JKP files (disclosed in the final hand-off); no code was added to the repo.

### Appendix: all 153 JKP factors, India (primary, my computation)
Columns: JKP id; description (truncated); JKP theme; sign of the long leg in the original paper (+ high value is long, - low value is long); original paper; India sample start-end; EW tercile long-short %/mo (naive t); VW-cap tercile long-short %/mo (naive t); EW 2015-2025; VW-cap 2015-2025; data need (P = prices and corporate actions only, F = fundamentals). Source: [JKP data files](https://jkpfactors.com/data) plus [JKP documentation](https://jkpfactors-data.s3.amazonaws.com/documents/Documentation.pdf). Factors are signed to the published direction, so a positive number means the published long-short worked in India.

| JKP id | Description | JKP theme | Long leg (orig. sign) | Original paper | India sample | EW tercile L-S %/mo (t) | VW-cap L-S %/mo (t) | EW 2015-25 %/mo (t) | VW 2015-25 %/mo (t) | Data |
|---|---|---|---|---|---|---|---|---|---|---|
| cowc_gr1a | Change in current operating working capital | Accruals | - | Richardson et al. (2005) | 2000-2025 | +0.34 (+2.8) | +0.48 (+2.5) | +0.11 (+1.2) | +0.20 (+1.3) | F |
| oaccruals_at | Operating accruals | Accruals | - | Sloan (1996) | 2000-2025 | +0.56 (+3.9) | +0.63 (+2.5) | +0.25 (+2.0) | +0.21 (+1.2) | F |
| oaccruals_ni | Percent operating accruals | Accruals | - | Hafzalla Lundholm and Van Winkle (2011 | 2000-2025 | +0.42 (+3.5) | +0.68 (+2.9) | +0.17 (+1.4) | +0.16 (+0.8) | F |
| seas_16_20na | Years 16-20 lagged returns, nonannual | Accruals | - | Heston and Sadka (2008) | 2008-2025 | -0.25 (-1.0) | -0.16 (-0.5) | +0.09 (+0.4) | +0.05 (+0.2) | P |
| taccruals_at | Total accruals | Accruals | - | Richardson et al. (2005) | 2000-2025 | +0.37 (+2.0) | -0.20 (-0.8) | +0.06 (+0.5) | +0.02 (+0.1) | F |
| taccruals_ni | Percent total accruals | Accruals | - | Hafzalla Lundholm and Van Winkle (2011 | 2000-2025 | +0.12 (+1.0) | -0.15 (-0.7) | +0.08 (+0.7) | +0.03 (+0.2) | F |
| capex_abn | Abnormal corporate investment | Debt Issuance | - | Titman Wei and Xie (2004) | 2003-2025 | -0.08 (-0.9) | +0.09 (+0.6) | -0.02 (-0.2) | +0.01 (+0.1) | F |
| debt_gr3 | Growth in book debt (3 years) | Debt Issuance | - | Lyandres Sun and Zhang (2008) | 2003-2025 | +0.31 (+2.3) | +0.13 (+0.6) | +0.31 (+3.0) | +0.13 (+0.9) | F |
| fnl_gr1a | Change in financial liabilities | Debt Issuance | - | Richardson et al. (2005) | 2000-2025 | +0.20 (+1.7) | +0.16 (+0.6) | +0.25 (+2.6) | +0.02 (+0.1) | F |
| ncol_gr1a | Change in noncurrent operating liabilities | Debt Issuance | - | Richardson et al. (2005) | 2000-2025 | +0.15 (+1.2) | +0.06 (+0.3) | +0.26 (+2.3) | +0.10 (+0.7) | F |
| nfna_gr1a | Change in net financial assets | Debt Issuance | + | Richardson et al. (2005) | 2000-2025 | -0.06 (-0.4) | +0.27 (+1.0) | +0.22 (+2.2) | +0.14 (+1.0) | F |
| ni_ar1 | Earnings persistence | Debt Issuance | + | Francis et al. (2004) | 2004-2025 | -0.31 (-3.2) | -0.16 (-0.9) | -0.42 (-4.1) | -0.21 (-1.6) | F |
| noa_at | Net operating assets | Debt Issuance | - | Hirshleifer et al. (2004) | 2000-2025 | +0.47 (+2.9) | +0.44 (+2.1) | +0.18 (+1.3) | +0.04 (+0.2) | F |
| aliq_at | Liquidity of book assets | Investment | - | Ortiz-Molina and Phillips (2014) | 2000-2025 | +0.32 (+1.2) | +0.37 (+1.5) | -0.14 (-0.8) | +0.20 (+0.9) | F |
| at_gr1 | Asset Growth | Investment | - | Cooper Gulen and Schill (2008) | 2000-2025 | +0.33 (+1.0) | +0.47 (+1.6) | -0.06 (-0.4) | +0.20 (+1.0) | F |
| be_gr1a | Change in common equity | Investment | - | Richardson et al. (2005) | 2000-2025 | +0.54 (+1.6) | +0.51 (+1.5) | +0.02 (+0.1) | +0.24 (+1.1) | F |
| capx_gr1 | CAPEX growth (1 year) | Investment | - | Xie (2001) | 2000-2025 | -0.23 (-2.6) | +0.01 (+0.1) | -0.15 (-2.0) | -0.01 (-0.1) | F |
| capx_gr2 | CAPEX growth (2 years) | Investment | - | Anderson and Garcia-Feijoo (2006) | 2003-2025 | -0.08 (-0.9) | +0.27 (+1.5) | -0.01 (-0.1) | +0.15 (+1.0) | F |
| capx_gr3 | CAPEX growth (3 years) | Investment | - | Anderson and Garcia-Feijoo (2006) | 2003-2025 | +0.04 (+0.4) | +0.15 (+0.8) | -0.03 (-0.3) | -0.02 (-0.1) | F |
| coa_gr1a | Change in current operating assets | Investment | - | Richardson et al. (2005) | 2000-2025 | +0.29 (+1.9) | +0.47 (+2.3) | -0.01 (-0.1) | +0.43 (+2.6) | F |
| col_gr1a | Change in current operating liabilities | Investment | - | Richardson et al. (2005) | 2000-2025 | -0.06 (-0.4) | +0.22 (+1.1) | -0.23 (-2.4) | +0.16 (+1.0) | F |
| emp_gr1 | Hiring rate | Investment | - | Belo Lin and Bazdresch (2014) | 2004-2025 | +0.22 (+1.3) | +0.30 (+1.4) | -0.03 (-0.2) | +0.16 (+0.9) | F |
| inv_gr1 | Inventory growth | Investment | - | Belo and Lin (2011) | 2003-2025 | -0.01 (-0.1) | +0.36 (+2.3) | -0.10 (-0.8) | +0.48 (+3.1) | F |
| inv_gr1a | Inventory change | Investment | - | Thomas and Zhang (2002) | 2000-2025 | +0.09 (+0.7) | +0.44 (+2.2) | -0.10 (-0.8) | +0.21 (+1.3) | F |
| lnoa_gr1a | Change in long-term net operating assets | Investment | - | Fairfield Whisenant and Yohn (2003) | 2000-2025 | +0.39 (+2.7) | +0.51 (+2.2) | +0.39 (+2.9) | +0.20 (+1.3) | F |
| ncoa_gr1a | Change in noncurrent operating assets | Investment | - | Richardson et al. (2005) | 2000-2025 | +0.43 (+3.1) | +0.51 (+2.1) | +0.42 (+2.7) | +0.26 (+1.4) | F |
| nncoa_gr1a | Change in net noncurrent operating assets | Investment | - | Richardson et al. (2005) | 2000-2025 | +0.40 (+2.9) | +0.54 (+2.3) | +0.46 (+3.2) | +0.18 (+1.0) | F |
| noa_gr1a | Change in net operating assets | Investment | - | Hirshleifer et al. (2004) | 2000-2025 | +0.66 (+3.3) | +0.81 (+4.3) | +0.28 (+2.1) | +0.33 (+1.7) | F |
| ppeinv_gr1a | Change PPE and Inventory | Investment | - | Lyandres Sun and Zhang (2008) | 2000-2025 | +0.40 (+2.3) | +0.41 (+1.9) | +0.22 (+1.3) | +0.20 (+1.1) | F |
| ret_60_12 | Long-term reversal | Investment | - | De Bondt and Thaler (1985) | 1993-2025 | +0.37 (+1.5) | +0.10 (+0.4) | +0.77 (+3.0) | +0.03 (+0.1) | P |
| sale_gr1 | Sales Growth (1 year) | Investment | - | Lakonishok Shleifer and Vishny (1994) | 2000-2025 | -0.11 (-0.5) | +0.41 (+1.4) | -0.45 (-3.9) | +0.16 (+0.9) | F |
| sale_gr3 | Sales Growth (3 years) | Investment | - | Lakonishok Shleifer and Vishny (1994) | 2003-2025 | +0.07 (+0.5) | +0.09 (+0.4) | -0.04 (-0.3) | +0.11 (+0.6) | F |
| saleq_gr1 | Sales growth (1 quarter) | Investment | - |  | 2001-2025 | -0.91 (-6.7) | +0.00 (+0.0) | -0.93 (-6.4) | +0.08 (+0.3) | F |
| seas_2_5na | Years 2-5 lagged returns, nonannual | Investment | - | Heston and Sadka (2008) | 1993-2025 | +0.10 (+0.5) | +0.05 (+0.2) | +0.44 (+2.1) | +0.04 (+0.1) | P |
| age | Firm age | Low Leverage | - | Jiang Lee and Zhang (2005) | 1989-2025 | -0.33 (-0.9) | -1.15 (-2.9) | +0.15 (+0.5) | +0.03 (+0.1) | P |
| aliq_mat | Liquidity of market assets | Low Leverage | - | Ortiz-Molina and Phillips (2014) | 2000-2025 | -1.49 (-6.0) | -0.29 (-1.0) | -2.01 (-6.2) | -0.70 (-2.1) | F |
| at_be | Book leverage | Low Leverage | - | Fama and French (1992) | 1999-2025 | -0.39 (-1.5) | -0.48 (-1.5) | -0.04 (-0.2) | -0.25 (-0.9) | F |
| bidaskhl_21d | The high-low bid-ask spread | Low Leverage | + | Corwin and Schultz (2012) | 1995-2025 | +0.08 (+0.4) | -0.06 (-0.3) | -0.12 (-0.6) | +0.31 (+1.3) | P |
| cash_at | Cash-to-assets | Low Leverage | + | Palazzo (2012) | 1999-2025 | -0.38 (-1.3) | -0.57 (-1.8) | -0.09 (-0.5) | -0.28 (-1.1) | F |
| netdebt_me | Net debt-to-price | Low Leverage | - | Penman Richardson and Tuna (2007) | 1999-2025 | -0.41 (-1.5) | -0.19 (-0.5) | -0.25 (-1.2) | -0.30 (-1.0) | F |
| ni_ivol | Earnings volatility | Low Leverage | + | Francis et al. (2004) | 2004-2025 | +0.04 (+0.4) | -0.05 (-0.2) | +0.33 (+2.7) | +0.02 (+0.1) | F |
| rd5_at | R&D capital-to-book assets | Low Leverage | + | Li (2011) | 2006-2025 | +0.28 (+1.3) | +0.45 (+1.6) | +0.32 (+1.4) | -0.08 (-0.2) | F |
| rd_sale | R&D-to-sales | Low Leverage | + | Chan Lakonishok and Sougiannis (2001) | 2003-2025 | -0.06 (-0.3) | +0.10 (+0.4) | +0.28 (+1.6) | -0.18 (-0.7) | F |
| tangibility | Asset tangibility | Low Leverage | + | Hahn and Lee (2009) | 1999-2025 | +0.32 (+1.8) | +0.11 (+0.4) | +0.44 (+3.9) | +0.18 (+1.0) | F |
| z_score | Altman Z-score | Low Leverage | + | Dichev (1998) | 1999-2025 | -1.01 (-2.5) | +0.10 (+0.2) | -1.24 (-4.1) | -0.44 (-1.4) | F |
| beta_60m | Market Beta | Low Risk | - | Fama and MacBeth (1973) | 1991-2025 | +0.20 (+0.8) | -0.14 (-0.4) | +0.42 (+1.1) | -0.28 (-0.7) | P |
| beta_dimson_21d | Dimson beta | Low Risk | - | Dimson (1979) | 1988-2025 | +0.31 (+1.6) | -0.08 (-0.3) | +0.80 (+4.1) | +0.20 (+0.8) | P |
| betabab_1260d | Frazzini-Pedersen market beta | Low Risk | - | Frazzini and Pedersen (2014) | 1993-2025 | +0.12 (+0.4) | +0.20 (+0.7) | +0.23 (+0.7) | +0.03 (+0.1) | P |
| betadown_252d | Downside beta | Low Risk | - | Ang Chen and Xing (2006) | 1989-2025 | +0.13 (+0.6) | +0.07 (+0.2) | +0.32 (+1.0) | -0.16 (-0.4) | P |
| dolvol_var_126d | Coefficient of variation for dollar trading  | Low Risk | - | Chordia Subrahmanyam and Anshuman (200 | 1997-2025 | -0.65 (-2.6) | -0.42 (-2.2) | -0.43 (-1.7) | -0.23 (-1.2) | P |
| earnings_variability | Earnings variability | Low Risk | - | Francis et al. (2004) | 2004-2025 | -0.07 (-0.6) | +0.02 (+0.2) | +0.03 (+0.2) | +0.19 (+1.1) | F |
| ivol_capm_21d | Idiosyncratic volatility from the CAPM (21 d | Low Risk | - |  | 1988-2025 | +0.06 (+0.2) | +0.09 (+0.4) | +0.50 (+1.8) | +0.09 (+0.3) | P |
| ivol_capm_252d | Idiosyncratic volatility from the CAPM (252  | Low Risk | - | Ali Hwang and Trombley (2003) | 1989-2025 | -0.56 (-1.9) | -0.11 (-0.4) | -0.78 (-1.8) | -0.12 (-0.3) | P |
| ivol_ff3_21d | Idiosyncratic volatility from the Fama-Frenc | Low Risk | - | Ang et al. (2006) | 2002-2025 | +0.19 (+0.8) | -0.05 (-0.2) | +0.47 (+1.7) | -0.00 (-0.0) | P |
| ivol_hxz4_21d | Idiosyncratic volatility from the q-factor m | Low Risk | - |  | 2005-2025 | +0.31 (+1.5) | +0.04 (+0.2) | +0.51 (+1.9) | +0.08 (+0.3) | P |
| ocfq_saleq_std | Cash flow volatility | Low Risk | - | Huang (2009) | 2005-2025 | +0.07 (+0.4) | +0.24 (+1.1) | -0.09 (-0.5) | -0.06 (-0.3) | F |
| rmax1_21d | Maximum daily return | Low Risk | - | Bali Cakici and Whitelaw (2011) | 1988-2025 | -0.03 (-0.1) | -0.29 (-1.0) | +0.43 (+2.0) | +0.09 (+0.4) | P |
| rmax5_21d | Highest 5 days of return | Low Risk | - | Bali, Brown, Murray and Tang (2017) | 1988-2025 | -0.28 (-1.0) | -0.15 (-0.5) | -0.03 (-0.1) | +0.15 (+0.6) | P |
| rmax5_rvol_21d | Highest 5 days of return scaled by volatilit | Low Risk | - | Assness, Frazzini, Gormsen, Pedersen ( | 1989-2025 | +0.85 (+5.0) | +0.18 (+0.8) | +0.94 (+5.1) | +0.31 (+1.7) | P |
| rvol_21d | Return volatility | Low Risk | - | Ang et al. (2006) | 1988-2025 | +0.08 (+0.3) | +0.03 (+0.1) | +0.68 (+2.4) | +0.03 (+0.1) | P |
| seas_6_10na | Years 6-10 lagged returns, nonannual | Low Risk | - | Heston and Sadka (2008) | 1998-2025 | +0.69 (+3.3) | +0.44 (+1.8) | +0.53 (+2.3) | +0.15 (+0.7) | P |
| turnover_var_126d | Coefficient of variation for share turnover | Low Risk | - | Chordia Subrahmanyam and Anshuman (200 | 1997-2025 | -0.63 (-2.6) | -0.42 (-2.2) | -0.52 (-2.2) | -0.27 (-1.3) | P |
| prc_highprc_252d | Current price to high price over last year | Momentum | + | George and Hwang (2004) | 1989-2025 | +0.53 (+1.9) | +0.70 (+2.3) | +0.91 (+2.6) | +0.38 (+1.2) | P |
| resff3_12_1 | Residual momentum t-12 to t-1 | Momentum | + | Blitz Huij and Martens (2011) | 2004-2025 | +0.91 (+6.6) | +0.25 (+1.4) | +1.03 (+6.5) | +0.41 (+2.3) | P |
| resff3_6_1 | Residual momentum t-6 to t-1 | Momentum | + | Blitz Huij and Martens (2011) | 2004-2025 | +0.55 (+3.9) | +0.21 (+1.1) | +0.45 (+3.0) | +0.12 (+0.6) | P |
| ret_12_1 | Price momentum t-12 to t-1 | Momentum | + | Jegadeesh and Titman (1993) | 1989-2025 | +0.65 (+2.7) | +0.93 (+3.0) | +0.81 (+3.0) | +0.81 (+2.7) | P |
| ret_3_1 | Price momentum t-3 to t-1 | Momentum | + | Jegedeesh and Titman (1993) | 1988-2025 | -0.11 (-0.5) | +0.53 (+2.1) | +0.28 (+1.3) | +0.24 (+1.0) | P |
| ret_6_1 | Price momentum t-6 to t-1 | Momentum | + | Jegadeesh and Titman (1993) | 1989-2025 | +0.35 (+1.6) | +0.96 (+3.6) | +0.53 (+2.4) | +0.66 (+2.5) | P |
| ret_9_1 | Price momentum t-9 to t-1 | Momentum | + | Jegedeesh and Titman (1993) | 1989-2025 | +0.47 (+2.1) | +0.91 (+3.1) | +0.71 (+2.9) | +0.80 (+2.7) | P |
| seas_1_1na | Year 1-lagged return, nonannual | Momentum | + | Heston and Sadka (2008) | 1989-2025 | +0.35 (+1.5) | +0.93 (+3.1) | +0.61 (+2.5) | +0.69 (+2.4) | P |
| dsale_dinv | Change sales minus change Inventory | Profit Growth | + | Abarbanell and Bushee (1998) | 2003-2025 | +0.20 (+2.4) | +0.22 (+1.2) | +0.07 (+0.8) | +0.15 (+1.0) | F |
| dsale_drec | Change sales minus change receivables | Profit Growth | - | Abarbanell and Bushee (1998) | 2002-2025 | -0.34 (-4.0) | -0.32 (-1.8) | -0.29 (-3.9) | -0.37 (-2.3) | F |
| dsale_dsga | Change sales minus change SG&A | Profit Growth | + | Abarbanell and Bushee (1998) | 2003-2025 | +0.14 (+1.6) | +0.17 (+0.8) | +0.22 (+2.7) | -0.07 (-0.5) | F |
| niq_at_chg1 | Change in quarterly return on assets | Profit Growth | + |  | 2003-2025 | +0.94 (+5.2) | +0.43 (+1.7) | +1.24 (+7.0) | +0.63 (+2.3) | F |
| niq_be_chg1 | Change in quarterly return on equity | Profit Growth | + |  | 2003-2025 | +1.03 (+6.8) | +0.29 (+1.3) | +1.21 (+9.5) | +0.33 (+1.9) | F |
| niq_su | Standardized earnings surprise | Profit Growth | + | Foster Olsen and Shevlin (1984) | 2005-2025 | +0.91 (+7.5) | +0.26 (+1.2) | +0.94 (+7.3) | +0.23 (+1.3) | F |
| ocf_at_chg1 | Change in operating cash flow to assets | Profit Growth | + | Bouchard, Krüger, Landier and Thesmar  | 2000-2025 | +0.48 (+3.4) | +0.51 (+2.4) | +0.25 (+3.2) | -0.03 (-0.2) | F |
| ret_12_7 | Price momentum t-12 to t-7 | Profit Growth | + | Novy-Marx (2012) | 1989-2025 | +0.64 (+3.3) | +0.71 (+2.6) | +0.74 (+3.2) | +0.57 (+2.2) | P |
| sale_emp_gr1 | Labor force efficiency | Profit Growth | + | Abarbanell and Bushee (1998) | 2004-2025 | +0.33 (+2.5) | +0.19 (+1.0) | -0.02 (-0.3) | -0.23 (-1.6) | F |
| saleq_su | Standardized Revenue surprise | Profit Growth | + | Jegadeesh and Livnat (2006) | 2006-2025 | +0.72 (+5.7) | -0.22 (-0.6) | +0.90 (+6.8) | +0.11 (+0.6) | F |
| seas_1_1an | Year 1-lagged return, annual | Profit Growth | + | Heston and Sadka (2008) | 1989-2025 | +0.39 (+2.4) | +0.17 (+0.8) | +0.38 (+2.1) | +0.09 (+0.4) | P |
| tax_gr1a | Tax expense surprise | Profit Growth | + | Thomas and Zhang (2011) | 2000-2025 | -0.08 (-0.4) | +0.08 (+0.3) | +0.22 (+1.8) | +0.26 (+1.6) | F |
| ebit_bev | Return on net operating assets | Profitability | + | Soliman (2008) | 1999-2025 | -0.55 (-1.8) | +0.07 (+0.2) | -0.31 (-1.3) | -0.18 (-0.7) | F |
| ebit_sale | Profit margin | Profitability | + | Soliman (2008) | 1999-2025 | -0.34 (-1.8) | -0.46 (-2.0) | -0.27 (-1.7) | -0.22 (-1.2) | F |
| f_score | Pitroski F-score | Profitability | + | Piotroski (2000) | 2003-2025 | +0.68 (+4.7) | +0.30 (+1.6) | +0.57 (+3.9) | +0.01 (+0.0) | F |
| ni_be | Return on equity | Profitability | + | Haugen and Baker (1996) | 1999-2025 | -0.14 (-0.5) | -0.22 (-0.7) | +0.29 (+1.5) | +0.02 (+0.1) | F |
| niq_be | Quarterly return on equity | Profitability | + | Hou Xue and Zhang (2015) | 2002-2025 | +0.64 (+3.5) | +0.35 (+1.3) | +0.77 (+3.9) | +0.14 (+0.5) | F |
| o_score | Ohlson O-score | Profitability | - | Dichev (1998) | 2000-2025 | -0.99 (-3.3) | -0.55 (-1.7) | -0.66 (-2.7) | -0.44 (-1.5) | F |
| ocf_at | Operating cash flow to assets | Profitability | + | Bouchard, Krüger, Landier and Thesmar  | 1999-2025 | -0.05 (-0.2) | +0.11 (+0.3) | +0.24 (+1.4) | +0.03 (+0.1) | F |
| ope_be | Operating profits-to-book equity | Profitability | + | Fama and French (2015) | 1999-2025 | +0.07 (+0.3) | +0.45 (+1.4) | +0.30 (+1.4) | +0.19 (+0.7) | F |
| ope_bel1 | Operating profits-to-lagged book equity | Profitability | + |  | 2000-2025 | -0.17 (-0.6) | +0.05 (+0.2) | +0.30 (+1.4) | +0.12 (+0.5) | F |
| at_turnover | Capital turnover | Quality | + | Haugen and Baker (1996) | 2000-2025 | +0.08 (+0.4) | -0.08 (-0.3) | +0.36 (+1.7) | +0.02 (+0.1) | F |
| cop_at | Cash-based operating profits-to-book assets | Quality | + |  | 2000-2025 | +0.09 (+0.6) | +0.40 (+1.5) | +0.12 (+0.8) | -0.06 (-0.2) | F |
| cop_atl1 | Cash-based operating profits-to-lagged book  | Quality | + | Ball et al. (2016) | 2000-2025 | -0.02 (-0.1) | +0.26 (+1.0) | +0.11 (+0.7) | -0.16 (-0.6) | F |
| dgp_dsale | Change gross margin minus change sales | Quality | + | Abarbanell and Bushee (1998) | 2002-2025 | +0.15 (+1.5) | +0.26 (+1.7) | +0.31 (+3.7) | +0.34 (+2.1) | F |
| gp_at | Gross profits-to-assets | Quality | + | Novy-Marx (2013) | 1999-2025 | +0.16 (+0.6) | -0.20 (-0.5) | +0.09 (+0.4) | -0.26 (-0.9) | F |
| gp_atl1 | Gross profits-to-lagged assets | Quality | + |  | 2000-2025 | +0.25 (+1.0) | -0.23 (-0.8) | +0.13 (+0.6) | -0.42 (-1.5) | F |
| ni_inc8q | Number of consecutive quarters with earnings | Quality | + | Barth Elliott and Finn (1999) | 2006-2025 | +0.43 (+3.0) | +0.56 (+2.2) | +0.49 (+3.6) | +0.32 (+1.7) | F |
| niq_at | Quarterly return on assets | Quality | + | Balakrishnan Bartov and Faurel (2010) | 2003-2025 | +0.71 (+2.8) | +0.06 (+0.2) | +0.98 (+3.3) | +0.03 (+0.1) | F |
| op_at | Operating profits-to-book assets | Quality | + |  | 1999-2025 | -0.38 (-1.2) | -0.02 (-0.1) | -0.11 (-0.4) | -0.07 (-0.2) | F |
| op_atl1 | Operating profits-to-lagged book assets | Quality | + | Ball et al. (2016) | 2000-2025 | -0.51 (-1.6) | -0.46 (-1.2) | -0.12 (-0.5) | -0.17 (-0.5) | F |
| opex_at | Operating leverage | Quality | + | Novy-Marx (2011) | 1999-2025 | +0.41 (+2.2) | +0.33 (+1.2) | +0.45 (+2.8) | +0.13 (+0.6) | F |
| qmj | Quality minus Junk: Composite | Quality | + | Assness, Frazzini and Pedersen (2018) | 2004-2025 | +0.04 (+0.2) | +0.09 (+0.3) | +0.03 (+0.1) | -0.00 (-0.0) | F |
| qmj_growth | Quality minus Junk: Growth | Quality | + | Assness, Frazzini and Pedersen (2018) | 2004-2025 | +0.45 (+4.3) | +0.34 (+1.8) | +0.60 (+4.9) | +0.35 (+2.3) | F |
| qmj_prof | Quality minus Junk: Profitability | Quality | + | Assness, Frazzini and Pedersen (2018) | 1999-2025 | +0.09 (+0.3) | -0.06 (-0.2) | +0.12 (+0.5) | -0.12 (-0.4) | F |
| qmj_safety | Quality minus Junk: Safety | Quality | + | Assness, Frazzini and Pedersen (2018) | 1993-2025 | -0.42 (-1.7) | -0.09 (-0.3) | -0.63 (-2.5) | -0.33 (-0.9) | F |
| sale_bev | Asset turnover | Quality | + | Soliman (2008) | 1999-2025 | +0.12 (+0.5) | +0.15 (+0.5) | +0.40 (+2.2) | +0.13 (+0.5) | F |
| mispricing_mgmt | Mispricing factor: Management | Quality? | + | Stambaugh and Yuan (2016) | 2000-2025 | +0.70 (+2.7) | +0.90 (+3.6) | +0.22 (+1.7) | +0.38 (+1.9) | F |
| mispricing_perf | Mispricing factor: Performance | Quality? | + | Stambaugh and Yuan (2016) | 1989-2025 | +0.47 (+2.0) | +0.60 (+2.1) | +0.28 (+1.1) | +0.14 (+0.4) | F |
| corr_1260d | Market correlation | Seasonality | - | Assness, Frazzini, Gormsen, Pedersen ( | 1993-2025 | +0.61 (+2.4) | +0.45 (+2.0) | +0.56 (+1.5) | +0.02 (+0.1) | P |
| coskew_21d | Coskewness | Seasonality | - | Harvey and Siddique (2000) | 1988-2025 | +0.09 (+0.7) | +0.09 (+0.4) | -0.14 (-1.2) | +0.05 (+0.3) | P |
| dbnetis_at | Net debt issuance | Seasonality | - | Bradshaw Richardson and Sloan (2006) | 1999-2025 | +0.36 (+3.1) | +0.05 (+0.2) | +0.14 (+1.8) | -0.09 (-0.6) | F |
| kz_index | Kaplan-Zingales index | Seasonality | + | Lamont Polk and Saa-Requejo (2001) | 2000-2025 | +0.50 (+1.8) | +0.21 (+0.9) | +0.29 (+1.4) | +0.42 (+1.5) | F |
| lti_gr1a | Change in long-term investments | Seasonality | - | Richardson et al. (2005) | 2000-2025 | +0.27 (+1.3) | +0.00 (+0.0) | +0.02 (+0.2) | -0.23 (-1.8) | F |
| pi_nix | Taxable income-to-book income | Seasonality | + | Lev and Nissim (2004) | 1999-2025 | -0.17 (-1.1) | -0.33 (-0.9) | -0.27 (-2.3) | +0.07 (+0.5) | F |
| seas_11_15an | Years 11-15 lagged returns, annual | Seasonality | + | Heston and Sadka (2008) | 2003-2025 | +0.25 (+1.4) | +0.22 (+1.0) | +0.36 (+1.9) | +0.39 (+1.7) | P |
| seas_11_15na | Years 11-15 lagged returns, nonannual | Seasonality | - | Heston and Sadka (2008) | 2003-2025 | +0.47 (+2.0) | +0.15 (+0.5) | +0.51 (+2.7) | +0.31 (+1.2) | P |
| seas_16_20an | Years 16-20 lagged returns, annual | Seasonality | + | Heston and Sadka (2008) | 2008-2025 | +0.29 (+1.4) | -0.19 (-0.7) | +0.40 (+1.8) | +0.04 (+0.2) | P |
| seas_2_5an | Years 2-5 lagged returns, annual | Seasonality | + | Heston and Sadka (2008) | 1993-2025 | +0.46 (+3.3) | +0.26 (+1.3) | +0.44 (+3.3) | +0.28 (+1.3) | P |
| seas_6_10an | Years 6-10 lagged returns, annual | Seasonality | + | Heston and Sadka (2008) | 1998-2025 | -0.05 (-0.2) | -0.20 (-0.8) | +0.37 (+2.0) | +0.33 (+1.5) | P |
| sti_gr1a | Change in short-term investments | Seasonality | + | Richardson et al. (2005) | 2000-2025 | +0.01 (+0.0) | +0.02 (+0.1) | -0.14 (-1.1) | -0.10 (-0.9) | F |
| iskew_capm_21d | Idiosyncratic skewness from the CAPM | Short-Term Reversal | - |  | 1988-2025 | +0.39 (+2.8) | -0.36 (-2.0) | +0.61 (+3.1) | -0.32 (-2.2) | P |
| iskew_ff3_21d | Idiosyncratic skewness from the Fama-French  | Short-Term Reversal | - | Bali Engle and Murray (2016) | 2002-2025 | +0.46 (+3.5) | -0.37 (-2.7) | +0.60 (+3.2) | -0.29 (-2.1) | P |
| iskew_hxz4_21d | Idiosyncratic skewness from the q-factor mod | Short-Term Reversal | - |  | 2005-2025 | +0.38 (+3.1) | -0.39 (-3.0) | +0.45 (+2.5) | -0.27 (-1.9) | P |
| ret_1_0 | Short-term reversal | Short-Term Reversal | - | Jegadeesh (1990) | 1988-2025 | +0.45 (+2.2) | -0.36 (-1.4) | -0.48 (-1.7) | +0.27 (+1.2) | P |
| rskew_21d | Total skewness | Short-Term Reversal | - | Bali Engle and Murray (2016) | 1988-2025 | +0.46 (+3.0) | -0.18 (-0.9) | +0.36 (+2.0) | -0.12 (-0.9) | P |
| ami_126d | Amihud Measure | Size | + | Amihud (2002) | 1997-2025 | +1.01 (+3.0) | +0.60 (+2.5) | +0.98 (+2.3) | +0.40 (+1.3) | P |
| dolvol_126d | Dollar trading volume | Size | - | Brennan Chordia and Subrahmanyam (1998 | 1997-2025 | +1.00 (+3.0) | +0.60 (+2.5) | +0.98 (+2.3) | +0.34 (+1.2) | P |
| market_equity | Market Equity | Size | - | Banz (1981) | 1988-2025 | +0.60 (+2.2) | +0.18 (+0.8) | +1.04 (+2.5) | +0.39 (+1.1) | P |
| prc | Price per share | Size | - | Miller and Scholes (1982) | 1988-2025 | +0.30 (+1.1) | -0.07 (-0.3) | +0.79 (+2.1) | +0.19 (+0.5) | P |
| rd_me | R&D-to-market | Size | + | Chan Lakonishok and Sougiannis (2001) | 2003-2025 | +0.75 (+4.2) | +0.26 (+1.2) | +0.83 (+4.2) | +0.21 (+0.9) | F |
| turnover_126d | Share turnover | Size/liquidity | - | Datar Naik and Radcliffe (1998) | 1997-2025 | +1.30 (+4.9) | +0.43 (+1.9) | +1.47 (+5.3) | +0.17 (+0.7) | P |
| zero_trades_126d | Number of zero trades with turnover as tiebr | Size/liquidity | + | Liu (2006) | 1997-2025 | +1.30 (+4.9) | +0.45 (+2.0) | +1.47 (+5.3) | +0.17 (+0.7) | P |
| zero_trades_21d | Number of zero trades with turnover as tiebr | Size/liquidity | + | Liu (2006) | 1997-2025 | +1.17 (+4.7) | +0.26 (+1.2) | +1.46 (+5.5) | +0.15 (+0.6) | P |
| zero_trades_252d | Number of zero trades with turnover as tiebr | Size/liquidity | + | Liu (2006) | 1998-2025 | +1.28 (+5.0) | +0.40 (+1.8) | +1.47 (+5.3) | +0.18 (+0.7) | P |
| at_me | Assets-to-market | Value | + | Fama and French (1992) | 1999-2025 | +0.42 (+1.1) | +0.05 (+0.1) | +1.16 (+3.4) | +0.28 (+0.8) | F |
| be_me | Book-to-market equity | Value | + | Rosenberg Reid and Lanstein (1985) | 1999-2025 | +0.63 (+1.3) | -0.07 (-0.1) | +0.96 (+3.3) | +0.23 (+0.6) | F |
| bev_mev | Book-to-market enterprise value | Value | + | Penman Richardson and Tuna (2007) | 1999-2025 | +0.74 (+1.5) | +0.06 (+0.1) | +0.82 (+2.8) | +0.29 (+0.8) | F |
| chcsho_12m | Net stock issues | Value | - | Pontiff and Woodgate (2008) | 1989-2025 | +0.33 (+1.3) | +0.68 (+2.1) | -0.00 (-0.0) | -0.15 (-0.5) | F |
| debt_me | Debt-to-market | Value | + | Bhandari (1988) | 1999-2025 | +0.49 (+1.8) | +0.30 (+0.8) | +0.59 (+2.3) | +0.32 (+0.9) | F |
| div12m_me | Dividend yield | Value | + | Litzenberger and Ramaswamy (1979) | 1989-2025 | +0.39 (+1.8) | +0.26 (+1.0) | +0.59 (+3.6) | +0.11 (+0.5) | F |
| ebitda_mev | Ebitda-to-market enterprise value | Value | + | Loughran and Wellman (2011) | 1999-2025 | +0.36 (+1.4) | -0.01 (-0.0) | +0.61 (+2.5) | +0.29 (+1.0) | F |
| eq_dur | Equity duration | Value | - | Dechow Sloan and Soliman (2004) | 2000-2025 | +0.41 (+2.2) | +0.30 (+0.9) | +0.68 (+3.9) | +0.31 (+1.0) | F |
| eqnetis_at | Net equity issuance | Value | - | Bradshaw Richardson and Sloan (2006) | 1999-2025 | +0.44 (+2.0) | +0.35 (+1.0) | -0.03 (-0.1) | +0.04 (+0.2) | F |
| eqnpo_12m | Equity net payout | Value | + | Daniel and Titman (2006) | 1989-2025 | +0.35 (+1.9) | +0.33 (+1.3) | -0.03 (-0.1) | +0.29 (+1.3) | F |
| eqnpo_me | Net payout yield | Value | + | Boudoukh et al. (2007) | 1999-2025 | +0.38 (+2.1) | +0.08 (+0.2) | +0.35 (+1.7) | +0.18 (+0.6) | F |
| eqpo_me | Payout yield | Value | + | Boudoukh et al. (2007) | 2000-2025 | -0.08 (-0.3) | +0.03 (+0.1) | +0.10 (+0.2) | -0.38 (-0.8) | F |
| fcf_me | Free cash flow-to-price | Value | + | Lakonishok Shleifer and Vishny (1994) | 1999-2025 | +0.74 (+6.0) | +0.94 (+3.1) | +0.44 (+4.1) | +0.36 (+2.1) | F |
| ival_me | Intrinsic value-to-market | Value | + | Frankel and Lee (1998) | 2000-2025 | +0.77 (+3.2) | +0.39 (+1.2) | +0.54 (+2.4) | +0.17 (+0.6) | F |
| netis_at | Net total issuance | Value | - | Bradshaw Richardson and Sloan (2006) | 1999-2025 | +0.77 (+4.0) | +0.56 (+1.6) | +0.32 (+2.0) | +0.08 (+0.3) | F |
| ni_me | Earnings-to-price | Value | + | Basu (1983) | 1999-2025 | +0.55 (+2.5) | +0.12 (+0.3) | +0.99 (+5.3) | +0.23 (+1.0) | F |
| ocf_me | Operating cash flow-to-market | Value | + | Desai Rajgopal and Venkatachalam (2004 | 1999-2025 | +0.57 (+3.1) | +0.13 (+0.3) | +0.65 (+3.5) | +0.36 (+1.5) | F |
| sale_me | Sales-to-market | Value | + | Barbee Mukherji and Raines (1996) | 1999-2025 | +0.79 (+1.9) | +0.32 (+0.7) | +0.81 (+2.5) | +0.35 (+1.1) | F |


## 3. Do Gu-Kelly-Xiu style machine-learning cross-sectional models work on Indian stocks, and do any results survive costs?

### Takeaway
The only paper I found that runs a Gu-Kelly-Xiu pipeline on India as a separate market is Choi-Jiang-Zhang (2023): market-specific neural nets reach an annualised Sharpe of about 4.4-4.6 equal-weighted but only about 2.1-2.8 value-weighted on a five-year India test window (2013-2017), gross of all costs and with unconstrained shorting. Every other NSE "deep learning" paper I found is index-level or accuracy-only, and the single net-of-cost ML study (Sodha 2025, LLM ranking of Nifty stocks) finds no net advantage. For a delivery-only, long-only book on prices and corporate actions, no ML result here is usable as-is.

### Cited Findings
Choi-Jiang-Zhang, "Alpha Go Everywhere: Machine Learning and International Stock Returns" (CUHK/Oxford working paper, March 2023 draft; ABFER 2023 annual conference). Primary: I read the PDF and the India rows of Tables 1 and 2.
- Design: DataStream returns and FactSet accounting data; 36 firm characteristics (a subset of Green-Hand-Zhang's 94); 32 markets, each required to have at least 100 stocks for at least three years; the models are the Gu-Kelly-Xiu set (OLS-3, OLS, LASSO, RIDGE, random forest, GBRT with Huber loss, neural nets NN1-NN5); stocks are sorted into deciles on predicted next-month return and the long-short is decile 10 minus decile 1 — [Choi-Jiang-Zhang, ABFER 2023 PDF](https://www.abfer.org/media/abfer-events-2023/annual-conference/papers-investment/AC23P3084-Alpha-Go-Everywhere-Machine-Learning-and-International-Stock-Returns.pdf)
- India sample: training 2007-2010, validation 2010-2012, test 2013-2017, 230,459 stock-month observations — same PDF (India row of the sample table).
- India, market-specific models, annualised Sharpe of the decile long-short (Table 2). Equal-weighted: market 1.26, OLS-3 0.95, OLS 2.50, LASSO 2.01, RIDGE 2.46, RF 3.02, GBRT+H 3.17, NN1 to NN5 4.14, 4.52, 4.59, 4.44, 4.53. Value-weighted: market 0.96, OLS-3 0.70, OLS 0.35, LASSO 0.80, RIDGE 0.20, RF 1.23, GBRT+H 0.31, NN1 to NN5 1.88, 2.78, 2.06, 2.83, 2.05 — same PDF.
- US-trained models applied to India's full sample (Table 1): equal-weighted NN Sharpe about 2.0-2.25 against a market Sharpe of 0.65; value-weighted NN about 0.5-0.9 against a market Sharpe of 0.52. Estimating on India's own data therefore roughly doubles the equal-weighted Sharpe, which is the paper's central claim — same PDF.
- Rank correlation between predicted and realised returns for India NNs is about 8.0-8.4 per cent, against about 6.0 per cent for the US — same PDF.
- US baseline in the same paper: equal-weighted NN Sharpe about 2.3-2.9 and value-weighted about 1.0-1.3 — same PDF. India's equal-weighted NN Sharpe is therefore well above the US figure in this paper, and its value-weighted figure is in line with it or a little higher.
- Pooled global portfolio (all stocks pooled, test sample 1992-2017, Table 4): NN equal-weighted long-short Sharpe 3.75-3.90, value-weighted 1.45-1.69, against market Sharpe 0.96 and 0.53; mean monthly NN long-short return about 4.0-4.1 per cent equal-weighted and about 2.0-2.2 per cent value-weighted; average monthly turnover of the NN strategies about 150 per cent, "about 20 to 30% higher" than Gu-Kelly-Xiu's US figure — same PDF (global figures, not India-specific).
- The authors warn that "the estimates here do not take into account transaction costs or other frictions, such as short-sale constraints, in the international equity markets" — same PDF.

Other machine-learning work on NSE stocks (abstract-level reading; all arXiv):
- Mehtab-Sen-Dutta: LSTM walk-forward prediction of the NIFTY 50 index level, 2014-2020. Index-level price prediction, not a cross-section, no trading-cost model — [arXiv 2009.10819](https://arxiv.org/abs/2009.10819)
- Sen-Mondal-Mehtab: LSTM for 70 NSE stocks in seven sectors, January 2010 to August 2021, framed as "sectoral profitability"; accuracy-style claims — [arXiv 2111.04976](https://arxiv.org/abs/2111.04976)
- Sen-Waghela-Rakshit: 180 stocks in 18 sectors, same genre — [arXiv 2407.01572](https://arxiv.org/abs/2407.01572)
- LSTM-based portfolio on NIFTY thematic sectors — [arXiv 2202.02723](https://arxiv.org/abs/2202.02723)
- Sodha, "When Reasoning Fails" (November 2025): Nifty constituents, rolling 48-month training with 1-month steps, 1-day horizon, universe sizes of 5, 11, 21 and 36 stocks, gpt-4o-mini and gpt-5 against ridge and random forest, long/short with realistic costs. The language model's ranking quality deteriorates as the universe grows, and the portfolio results under costs do not support a net advantage for the language model — [arXiv 2511.08608](https://arxiv.org/abs/2511.08608)

### Inferences
- The India equal-weighted Sharpe of 4.4-4.6 and value-weighted 2.1-2.8 are gross, from a five-year window (2013-2017), and decile-10-minus-decile-1 long-shorts that include illiquid microcaps and shorts. They cannot be mapped to %/month without the long-short volatility, which the India panel does not report; the nearest figures are the pooled global ones (about 4.1 per cent a month equal-weighted, about 2.1 per cent value-weighted), which are not India. I do not convert them.
- Costs alone do not kill the ML long-short on those pooled numbers: 150 per cent monthly turnover at roughly 19 bp a side is about 0.3 per cent a month, against 2.0-4.1 per cent gross. The binding constraints are different: the short leg (not executable in delivery), the microcap-heavy decile 10 in the equal-weighted version, the five-year India test window, and the fundamentals the 36 characteristics need. A long-only top decile from the value-weighted version would earn some fraction of 2.1 per cent a month gross, but I have no India long-leg number, so I cannot say how much.
- The equal-weighted versus value-weighted gap (4.5 versus 2.0-2.8 Sharpe) repeats the JKP India pattern in section 2: much of the apparent edge lives in small stocks. That is the same reason I would not carry the equal-weighted figures over to a top-400-by-traded-value universe.
- The project's data is prices and corporate actions. The CJZ models use fundamentals (book-to-market, accruals, profitability, investment and similar among their 36 inputs), so a price-only reduction of this approach is a different and untested model; the price-only inputs (momentum, reversal, volatility, turnover) are the families already closed in `00-already-covered.md` (sections 1b to 1d). Overlap note: closed or untestable at the project's data level; no new signal.
- The Indian LSTM literature is not evidence of a tradable edge: index-level or accuracy metrics, no costs, no multiple-testing control, and long contiguous-window designs that invite look-ahead and overfitting. Sodha 2025 is the only item that reports costs, and it is negative.

### Gaps
- Gu-Kelly-Xiu (RFS 2020) has no India sample; its US baseline is available here only through Choi-Jiang-Zhang. No separate India replication of Gu-Kelly-Xiu with a long-only leg, turnover or costs was found.
- Choi-Jiang-Zhang is a working paper (March 2023 draft; first draft 2019); I did not find a published version or a replication, and the India test window ends in 2017, so nothing here tests 2018-2026.
- India long-short mean returns, volatility, turnover and drawdown from Choi-Jiang-Zhang were not extracted (only Sharpe ratios are in the per-market table), so no %/month figure for India.
- Net-of-cost ML on NSE cross-sections beyond Sodha 2025: none found. The WebSearch budget ran out before I could run further queries (for example SSRN or Indian journal ML papers on the Nifty 500); this is a limit of my search, not proof that none exist.
- I did not open the LSTM papers' full text, only abstracts; the descriptions above are of what they claim, not of whether their methods are sound.

## 4. What do the older Indian factor and anomaly papers say (IIMA four-factor library, Cakici et al., the Sehgal group, momentum and low-volatility studies), and how reliable is that evidence?

### Takeaway
The older Indian literature agrees with the JKP panel on one point and is thin on everything else: momentum is a robust premium in India (about 0.9-2.0 %/month depending on the study and construction), value is positive, and the five-factor profitability and investment add-ons contribute little. Almost all of it comes from abstracts and search summaries that I could not open (SSRN, Wiley, ScienceDirect, Sage and Emerald returned 403 or paywalls), so every number in this section other than my own conversions is unverified and none of it carries a net-of-cost figure.

### Cited Findings
Evidence grade for this whole section: search-summary only. I saw abstracts, repository pages or search-engine summaries, not the full papers; every figure is flagged "unverified".

Indian Fama-French-Carhart factors (IIMA):
- Agarwalla, Jacob and Varma, "Four factor model in Indian equities market" (IIMA Working Paper 2013-09-05, revised September 2014): size (SMB), value (HML), market and momentum (WML) factors from CMIE Prowess data covering October 1993 to December 2013, covering more firms than earlier studies, excluding illiquid firms so the portfolios are investible, and with returns corrected for survival bias — [IIMA publication page](https://www.iima.ac.in/publication/four-factor-model-indian-equities-market); [working paper PDF](https://iima.ac.in/sites/default/files/rnpfiles/1970004922013-09-05.pdf) (search summary only; the PDF was not parsed)
- The authors maintain a public daily, monthly and yearly factor library for India that Varma says is updated monthly — [Jayanth Varma, India Fama-French-Momentum data](https://www.jrvarma.in/fama-french.html)
- The authors' drawdown page, citing their Vikalpa 2017 paper "Size, Value, and Momentum in Indian Equities", gave annualised factor returns for October 1993 to March 2023 of value +6.77 per cent, size -4.80 per cent and momentum +11.34 per cent (unverified: that page was bot-gated, and the figures came from a search summary). By my geometric conversion that is about +0.55, -0.40 and +0.90 %/month — same IIMA source plus [Varma](https://www.jrvarma.in/fama-french.html)

Emerging-market and cross-country papers that include India:
- Cakici, Fabozzi and Tan (Emerging Markets Review 16, 46-65, 2013): 18 emerging markets, stock-level data 1990-2011; a value effect in all markets and a momentum effect in all but Eastern Europe; local factors explain returns better than global ones, which the authors read as market segmentation. No India-specific row was obtained — [EDHEC listing](https://climateinstitute.edhec.edu/publications/size-value-and-momentum-emerging-market-stock-returns)
- A Quantpedia summary of a different paper (Cakici, Tang and Yan, 1990-2013) reports average UMD positive in 14 markets, from 0.05 %/month (Malaysia) to 1.99 %/month in India, and an India value factor of about 2.34 %/month. Unverified, and the summary does not give t-statistics or portfolio construction — [Quantpedia](https://quantpedia.com/do-the-size-value-and-momentum-factors-exist-in-emerging-markets/)

Five-factor and risk-model tests (explanatory power rather than tradable spreads):
- Tripathi and Singh (2021): 486 CNX 500 firms, 2000-2015; the five-factor model beats CAPM but the adjusted R-squared does not rise significantly over the three-factor model — [Inderscience](https://www.inderscience.com/filter.php?aid=111959)
- Prakash, Singh and Singh (2023): BSE-500, 1999-2020; the five-factor and an alternative four-factor model beat the three-factor model; the investment factor has no explanatory power once profitability is included; unlike the US, the value factor is significant in India — [IDEAS/RePEc](https://ideas.repec.org/a/eme/ijmfpp/ijmf-05-2021-0245.html) (search summary; I matched the paper to this link by topic and did not verify the match)
- Sagar, Sehgal, Jain and Gupta: 64 NSE-100 firms, 2012-2021, 18 portfolios sorted on size, value, profitability and investment; R-squared of 95.8 per cent for the five-factor model against 95.6 per cent for the three-factor model and 89.9 per cent for CAPM — [Business Perspectives, Sehgal author page](https://businessperspectives.org/journals/author/deepak-sehgal)
- Thekdi and Maithani (2025), Nifty 500: size (SMB) and investment (CMA) not significant; the five-factor model improves explanatory power only slightly. Foye (2017) is cited there for the limits of five-factor models in emerging markets — [Missouri State BearWorks listing](https://bearworks.missouristate.edu/articles00/620) (search summary; the link is one of the results returned for the five-factor query and I did not confirm it is this paper)
- A Sage paper using July 2001 to June 2019 data finds that the Fama-French three-factor model subsumes most of the alpha of its sample anomalies, but no factor model fully explains all of them — [Sage](https://journals.sagepub.com/doi/full/10.1177/0019466220951978)
- Balakrishnan (Vision, 2016): size, value and momentum effects in India; the Fama-French three-factor model partly explains average returns on size-value sorted portfolios — [IDEAS/RePEc](https://ideas.repec.org/a/sae/vision/v20y2016i1p1-8.html)

The Sehgal group on anomaly decay, sentiment and accruals:
- Sharma, Subramaniam and Sehgal (Global Business Review 22(1), 2021): size and volume anomalies still yield returns but have weakened over time; value and momentum are said to be explained by risk models — [IDEAS/RePEc](https://ideas.repec.org/a/sae/globus/v22y2021i1p255-270.html)
- Pandey and Sehgal (IIMB Management Review, June 2019): a sentiment factor appears to capture the small-firm effect that the Fama-French five-factor model leaves unexplained — [DOAJ](https://doaj.org/article/715e62653d644b1cba50fcb58b54bbb0)
- Sehgal, Subramaniam and Deisting (IMFI, 2012): accrual and cash-flow anomalies do not seriously challenge standard asset-pricing models in India — [Business Perspectives PDF](https://businessperspectives.org/images/pdf/applications/publishing/templates/article/assets/4888/imfi_en_2012_04_Sehgal.pdf)

Momentum specifically:
- A 2020 study in the Copernican Journal of Finance and Accounting finds both time-series and cross-sectional momentum significant in India, significant after adjusting for market, size and value factors, with time-series momentum earning more than cross-sectional — [CJFA 2020.018](https://apcz.umk.pl/CJFA/article/view/CJFA.2020.018)
- A study using NSE data from 1997 to 2013 finds no January or April seasonality in Indian momentum profits and reports short-term momentum with long-term over-reaction — [Journal of Commerce and Accounting Research (via search result)](https://www.publishingindia.com/archive/ijfm/a-study-of-contrarian-and-momentum-profits-in-indian-stock-market) (the search result gave the summary but not t-statistics; the link is the International Journal of Financial Management listing returned for that query and I did not confirm it is the 1997-2013 study)

Low volatility:
- Joshipura and Joshipura (2016) report that low-volatility and low-beta stocks earned higher risk-adjusted returns than high-volatility and high-beta stocks in India — [IUP Journal listing](https://www.iupindia.in/1503/Financial%20Risk%20Management/Risk_Anomaly.html) (search summary; matched by topic)
- Saraf and Kayal (2022), Nifty 500, 2010-2020: the volatility anomaly shows up at 5-10 year horizons and is negligible at 6 months to 3 years — [MSE Working Paper 215](https://mse.ac.in/wp-content/uploads/2022/03/Working-Paper-215.pdf) (search summary; matched by topic)
- An Alpha Architect summary of an out-of-sample test for January 1994 to June 2010 reports that the high-volatility quintile earned high returns in India, which cuts against the anomaly — [Alpha Architect](https://alphaarchitect.com/2014/03/low-volatility-anomaly-lacks-robustness)

Anomaly by India summary (older literature plus my JKP row for comparison; %/month converted by me where only annual figures were given):

| Anomaly | India direction | %/month | t-stat | Sample | Universe | Grade |
|---|---|---|---|---|---|---|
| Momentum (WML, IIMA) | Positive | about +0.90 (from +11.34 per cent a year, geometric) | not reported | Oct 1993 to Mar 2023 | CMIE Prowess, illiquid firms excluded | search summary |
| Momentum (UMD, Cakici-Tang-Yan via Quantpedia) | Positive, highest of 14 markets | +1.99 | not reported | 1990-2013 | not stated | search summary |
| Momentum, JKP ret_12_1 VW-cap (section 2) | Positive | +0.93 | 3.0 | to Dec 2025 | JKP India, non-micro breakpoints | primary |
| Value (HML, IIMA) | Positive | about +0.55 (from +6.77 per cent a year) | not reported | Oct 1993 to Mar 2023 | as above | search summary |
| Value (Cakici-Tang-Yan via Quantpedia) | Positive | +2.34 | not reported | 1990-2013 | not stated | search summary |
| Value theme, JKP VW-cap (section 2) | Positive, weak | +0.25 | 1.1 | to Dec 2025 | JKP India | primary |
| Size (SMB, IIMA) | Negative (small stocks lag) | about -0.40 (from -4.80 per cent a year) | not reported | Oct 1993 to Mar 2023 | as above | search summary |
| Size theme, JKP EW (section 2) | Positive (small beat big) | +0.50 | 2.1 | to Dec 2025 | JKP India, equal-weighted | primary |
| Profitability and investment (five-factor) | Small or none; investment drops out given profitability | not reported | not reported | 1999-2021 across studies | BSE-500 / Nifty 500 / NSE-100 | search summary |
| Accruals / cash-flow | "Do not seriously challenge" asset-pricing models | not reported | not reported | IMFI 2012 | not stated | search summary |
| Low volatility | Mixed; horizon dependent | not reported | not reported | 2010-2020 (Saraf-Kayal); 1994-2010 reverse | Nifty 500 | search summary |
| Momentum seasonality (no January or April effect) | None | not reported | not reported | 1997-2013 | NSE | search summary |

### Inferences
- Momentum is the one anomaly where the old and new evidence line up: IIMA WML about +0.90 %/month and JKP VW-cap ret_12_1 +0.93 %/month are the same order, from independent factor constructions. That corroborates, but does not add to, the closed momentum family in `00-already-covered.md` (section 1c).
- The size premium contradicts itself: IIMA's SMB is negative (small lag big) while JKP's India size theme is positive when equal-weighted. Different weighting, liquidity filters and sample ends could explain both, but I could not read the IIMA construction and cannot resolve it. This reinforces the section 2 point that equal-weighted India results include a tail that the project's top-400 universe cannot trade.
- The five-factor and Sehgal-group papers test whether factors explain returns, not whether a factor earns money net of costs. Nothing in this section yields a net-of-cost %/month figure, so none of it can be compared with the 33-39 bp hurdle directly. For scale, one full re-sort a year costs about 38 bp / 12 = 3 bp a month, while a full monthly re-sort costs 38 bp a month; that is arithmetic from my cost assumption, not a result from these papers.
- Overlap with `00-already-covered.md`: momentum is closed (section 1c); value and dividend yield are "Leave" (3g); quality, size, beta, IVOL are "Skip" (3f); accruals and investment are not in the file. The only candidates this section adds beyond section 2 are accruals and investment, which are fundamentals-based.

### Gaps
- None of the Indian papers above were opened in full; every number is from an abstract, repository page or search summary and is unverified. The IIMA drawdown page returned a bot-check page when fetched directly.
- No t-statistics for the IIMA factors, Cakici-Tang-Yan India rows or the momentum papers; no portfolio breakpoints, weighting or turnover for any of them.
- Several summaries were matched to links by topic rather than by title; those are labelled in the bullet. Treat them as pointers to find the papers, not as verified citations.
- Atodaria (2025, three-factor, five-factor and Carhart models on S&P BSE 100, 2005-2021): the search summary gave no findings.
- No older India paper with a net-of-cost long-only result was found.

## 5. How have the niftyindices.com factor indices performed live against the Nifty 200 / Nifty 100 TRI, and how much of the published record is backtest?

### Takeaway
Over the last five years to 30 September 2026, a window that is entirely post-launch for ten of the eleven factor indices I could read, the factor indices beat the Nifty 200 TRI by a median of only about +0.6 percentage points a year (about +0.05 %/month), with six of ten ahead; the long record that makes them look strong (momentum 18.3 per cent since 2005 against about 13.5 per cent) is mostly backtested index history. For the Nifty200 Momentum 30 the excess shrinks from +4.3 points a year over ten years to +0.8 over five (HDFC deck, June 2026), and the pre-launch backtest beat the live record by about 3 points a year of excess CAGR. Index returns are gross of trading costs and impact.

### Cited Findings
Method and caveats first:
- The factsheet "Total Return" row gives quarter-to-date, year-to-date, 1-year (absolute), 5-year (CAGR) and since-base-date (CAGR) returns; standard deviation and beta (against the Nifty 50) are shown for 1, 3 and 5 years. All factsheets I used are dated 30 September 2026, except the Nifty 50 factsheet (30 October 2026), which I left out because it is not comparable — factsheet pattern `https://www.niftyindices.com/Factsheet/<name>.pdf`, for example [Nifty200 Momentum 30](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Momentum30.pdf)
- Base dates differ: April 2005 for the Nifty200 Momentum 30, Alpha Low-Volatility 30, Alpha Quality Low-Volatility 30, Alpha Quality Value Low-Volatility 30, Quality Low-Volatility 30, Nifty200 Quality 30 and Nifty200 Value 30; December 2003 for the Nifty Alpha 50 and Low Volatility 50; January 2009 for the Nifty50 Value 20; November 1995 for the Nifty50 Equal Weight. Comparators: Nifty 100 TR base January 2003, Nifty 200 TR base January 2004, Nifty 500 TR base January 1995, Nifty Midcap 150 TR base April 2005 — same factsheets, e.g. [Nifty 200](https://www.niftyindices.com/Factsheet/ind_nifty_200.pdf), [Nifty50 Value 20](https://www.niftyindices.com/Factsheet/Nifty50_Value20.pdf)
- Launch dates matter because everything before launch is a backtest: Nifty200 Momentum 30, 25 August 2020; Alpha Low-Volatility 30, Quality Low-Volatility 30 and Alpha Quality Low-Volatility 30, 10 July 2017; Alpha Quality Value Low-Volatility 30, 3 July 2017; Nifty200 Quality 30, 17 April 2018; Nifty Alpha 50 and Low Volatility 50, 19 November 2012; Nifty50 Equal Weight, 13 April 2017; Nifty50 Value 20, 28 March 2014; Nifty200 Value 30, 12 June 2024 — same factsheets.

Factsheet total returns at 30 September 2026 (per cent; QTD and YTD are not annualised, 1Y is absolute, 5Y and since-base are CAGR; excess is my subtraction of the Nifty 200 TR figure of -3.23 for 1Y and 8.30 for 5Y):

| Index | Rebalance | Launch | 1Y | 5Y | Since base | 1Y excess | 5Y excess | Standard deviation 5Y, beta |
|---|---|---|---|---|---|---|---|---|
| Nifty200 Momentum 30 | Semi-annual | Aug 2020 | -0.47 | 9.28 | 18.30 | +2.8 | +1.0 | 19.4, 1.18 |
| Nifty Alpha Low-Volatility 30 | Semi-annual | Jul 2017 | -1.91 | 8.57 | 17.71 | +1.3 | +0.3 | 13.4, 0.86 |
| Nifty Alpha Quality Low-Volatility 30 | Semi-annual | Jul 2017 | -1.58 | 9.41 | 17.03 | +1.7 | +1.1 | not recorded |
| Nifty Alpha Quality Value Low-Volatility 30 | Semi-annual | Jul 2017 | -6.17 | 12.90 | 16.90 | -2.9 | +4.6 | not recorded |
| Nifty Alpha 50 | Quarterly | Nov 2012 | +11.44 | 12.03 | 20.21 | +14.7 | +3.7 | 21.7, 1.19 |
| Nifty Low Volatility 50 | Quarterly | Nov 2012 | -4.96 | 8.30 | 16.49 | -1.7 | 0.0 | 12.1, 0.79 |
| Nifty Quality Low-Volatility 30 | Semi-annual | Jul 2017 | -6.38 | 5.81 | 15.46 | -3.2 | -2.5 | not recorded |
| Nifty200 Quality 30 | Semi-annual | Apr 2018 | -5.42 | 6.40 | 16.64 | -2.2 | -1.9 | 13.5, 0.82 |
| Nifty200 Value 30 | Semi-annual | Jun 2024 | +7.89 | 22.91 | 16.12 | +11.1 | +14.6 | 20.1, 1.12 |
| Nifty50 Equal Weight (parent Nifty 50, not Nifty 200) | Semi-annual | Apr 2017 | -1.08 | 10.71 | 13.73 | +2.2 | +2.4 | not recorded |
| Nifty50 Value 20 (parent Nifty 50) | Semi-annual | Mar 2014 | -9.51 | 6.20 | 16.77 | -6.3 | -2.1 | not recorded |

Comparators at 30 September 2026 (1Y, 5Y, since base): Nifty 100 TR -5.18, 7.06, 15.84; Nifty 200 TR -3.23, 8.30, 13.46; Nifty 500 TR -2.03, 9.04, 11.89; Nifty Midcap 150 TR +4.57, 14.76, 16.75 — [Nifty 100](https://www.niftyindices.com/Factsheet/ind_nifty_100.pdf), [Nifty 200](https://www.niftyindices.com/Factsheet/ind_nifty_200.pdf), [Nifty 500](https://www.niftyindices.com/Factsheet/ind_nifty_500.pdf), [Nifty Midcap 150](https://www.niftyindices.com/Factsheet/ind_nifty_midcap_150.pdf)

My arithmetic on that table (primary, throwaway script in the scratchpad):
- Excluding the Nifty200 Value 30 (launched June 2024, so its 5Y figure is mostly backtest), the ten indices' 5Y excess over the Nifty 200 TR has mean +0.66 and median +0.62 percentage points a year; six of ten are positive; the range is -2.5 (Quality Low-Volatility 30) to +4.6 (Alpha Quality Value Low-Volatility 30). For the Nifty200 Momentum 30 alone it is +0.98 points a year (about +0.08 %/month). The Nifty50 Equal Weight and Value 20 are measured against the wrong parent in this comparison and are included only for completeness.
- The Nifty 200 TR since an April 2005 base is about 13.5 per cent a year at 30 September 2026 by my derivation (the HDFC deck's 13.9 per cent at June 2026 compounded through the Q3 2026 return of -4.30 per cent), close to the 13.46 per cent printed for the January 2004 base. Against that, the April-2005-base indices lead by about 4.8 (Momentum 30), 4.2 (Alpha Low-Volatility 30), 3.5, 3.4, 3.1 (Quality 30), 2.6 (Value 30, almost all backtest) and 2.0 points a year (Quality Low-Volatility 30). These are the long, mostly backtested records.
- The Nifty200 Momentum 30 factsheet says the index weights by free-float market cap times a normalised momentum score (6- and 12-month returns divided by volatility), with a cap at the lower of 5 per cent or five times the free-float weight; capital goods 24.1 per cent, financials 21.2 per cent, metals 18.7 per cent and power 14.2 per cent at 30 September 2026; standard deviation 18.6 per cent (1 year) and 19.4 per cent (5 years), beta 1.18 against the Nifty 50 — [Nifty200 Momentum 30 factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Momentum30.pdf)

Backtest versus live for the Nifty200 Momentum 30 (the one index with a long public record and an AMC deck):
- NSE's whitepaper (data to 31 August 2020, just before launch; all of it backtest) shows an 18.6 per cent CAGR since April 2005 against 12.7 per cent for the Nifty 200, outperformance of the Nifty 200 on 98.3 per cent of daily-rolling 5-year windows and 100 per cent of 7- and 10-year windows, and a 5-year excess above 4 points a year on 65.5 per cent of windows — [NSE Indices whitepaper, September 2020](https://www.niftyindices.com/docs/default-source/indices/nifty200-momentum-30/nifty200_momentum_30_index_whitepaper_sep_20.pdf)
- The HDFC AMC deck for its index fund (data to 30 June 2026) shows CAGR for the Momentum 30 TRI, Nifty 200 TRI and Nifty 50 TRI of: 1 year -2.5, -2.2, -5.4; 3 years 14.1, 12.1, 8.8; 5 years 12.6, 11.8, 10.0; 7 years 16.6, 13.6, 11.9; 10 years 17.8, 13.5, 12.5; 15 years 18.1, 12.3, 11.4; since April 2005 18.8, 13.9, 13.6. Excess over the Nifty 200 TRI therefore runs +4.3 (10 years), +3.0 (7), +0.8 (5), +2.0 (3) and -0.3 (1) points a year — [HDFC Nifty200 Momentum 30 Index Fund deck, July 2026](https://files.hdfcfund.com/s3fs-public/Others/2026-07/HDFC%20NIFTY200%20Momentum%2030%20Index%20Fund_PPT%20%28July%202026%29.pdf) (fund-house marketing material)
- The same deck gives financial-year returns (Momentum 30 TRI / Nifty 200 TRI / Nifty 50 TRI, per cent): FY06 79.7/63.7/67.4; FY07 4.7/11.0/14.3; FY08 40.9/23.5/25.1; FY09 -34.9/-38.5/-35.4; FY10 62.9/86.4/75.3; FY11 14.1/9.5/12.4; FY12 -0.3/-7.9/-8.2; FY13 16.4/7.6/8.7; FY14 21.4/19.3/19.5; FY15 60.2/33.1/28.2; FY16 -4.4/-6.9/-7.8; FY17 40.2/24.0/20.2; FY18 21.6/12.4/11.8; FY19 11.6/11.9/16.4; FY20 -16.4/-26.1/-25.0; FY21 62.4/74.6/72.5; FY22 37.7/21.4/20.3; FY23 -9.2/-1.1/0.6; FY24 70.0/38.3/30.1; FY25 -7.6/6.4/6.7; FY26 -3.4/-2.8/-4.0; FY27 to date 14.4/10.9/7.4. It states 14 of 21 financial years (66.7 per cent) of outperformance over the Nifty 200 TRI and 15 of 21 over the Nifty 50 TRI — same HDFC deck.
- My arithmetic on those FY rows (primary): compounded FY06-FY26 18.3 / 13.5 / 13.4 per cent; FY06-FY21 (launch falls in FY21, so this is mostly backtest) 19.7 / 14.1 / 14.5; FY22-FY26 (live) 13.7 / 11.4 / 10.0. The CAGR gap over the Nifty 200 falls from 5.6 to 2.3 points a year. The mean annual excess is about the same (+5.2 pre-launch, +5.1 live) but its standard deviation rises from 12.2 to 18.7 points, so the live record is much noisier. Relative losses to the Nifty 200 TRI came in FY07, FY10, FY19, FY21, FY23, FY25 and FY26, with the worst at -23.5 (FY10) and -14.0 (FY25); absolute losses in FY09 (-34.9), FY20 (-16.4), FY23, FY25, FY26, FY12 and FY16 — from the HDFC deck rows above.
- Whitepaper for the Alpha Low-Volatility 30 (data to 30 September 2020, backtest): 19.0 per cent CAGR since April 2005 against 13.2 per cent for the Nifty 100 and 9.9 per cent for the Nifty Midcap 50, annualised volatility 18.5 / 22.6 / 26.9 per cent, 99.6 per cent of 5-year rolling windows ahead of the Nifty 100 — [NSE Indices whitepaper](https://www.niftyindices.com/docs/default-source/indices/nifty-alpha-low-volatility-30/nifty-alpha-low-volatility-30-whitepaper_2020.pdf). The live factsheet shows 5Y +8.57 per cent against +7.06 for the Nifty 100 TR (+1.5 points) and +0.3 against the Nifty 200 TR; the implied CAGR from September 2020 to September 2026 is about 14.4 per cent (my derivation from the 19.0-equivalent and 17.71 per cent since-base figures, rounding-sensitive) — [Alpha Low-Volatility 30 factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Alpha_Low-Volatility_30.pdf); [Nippon India fund note, September 2026](https://mf.nipponindiaim.com/FundsAndPerformance/ProductNotes/NipponIndia-Nifty-Alpha-Low-Volatility-30-Index-Fund-Sep-2026.pdf)

### Inferences
- The factor-index record is a ceiling, not a forecast. Backtested history before launch looked better than live history for the momentum index (CAGR gap of 5.6 versus 2.3 points a year, and the 5-year excess of +0.8 to +1.0 points against the whitepaper's 65.5 per cent of windows above +4). That is the usual selection pattern for published index backtests: index design is fitted on history that is then displayed as if out of sample. The decay also shows that the headline long-run CAGR numbers on factsheets should not be quoted as expected returns.
- Live five-year excess is small (median about +0.05 %/month) and the dispersion is wide, with three indices below the Nifty 200 TR (one of them, the Value 20, against the wrong parent) and one tied. Quality-flavoured indices (Nifty200 Quality 30, Quality Low-Volatility 30) have lagged, consistent with the section 2 finding that quality and profitability have about zero or wrong-signed premia in India. Low volatility is roughly neutral against the Nifty 200 (Low Volatility 50 at 0.0, Alpha Low-Volatility 30 at +0.3) with much lower risk (5-year standard deviation 12.1-13.4 per cent against about 19-22 for the momentum and alpha indices), which fits the section 2 low-risk result (about zero return premium) rather than a free lunch.
- The exception is the Nifty Alpha 50 (+3.7 points a year over five years, +14.7 in the last year, quarterly rebalance, beta 1.19). By its name I take it to be a past-alpha (trailing-return) sort, which would make it a momentum relative closed in `00-already-covered.md` (section 1c); I did not open its methodology, so this is unverified. One strong live record out of eleven, in a window dominated by 2023-2025 mid-cap and momentum conditions, is not evidence of a stable edge.
- None of this is cost-adjusted or beta-adjusted. Index total-return series carry no trading costs or impact, and these indices rebalance semi-annually or quarterly with sector-concentrated, tilt-weighted portfolios; the Momentum 30 has beta 1.18 against the Nifty 50, so part of its excess over the Nifty 200 is market exposure. As a bound using only my own 38 bp round-trip figure: two rebalances a year that replaced the whole book would cost 76 bp a year (about 6 bp a month), against a five-year Momentum 30 excess of about 98 bp a year (about 8 bp a month), so the excess would be mostly consumed at full replacement and mostly kept if 30-50 per cent of the book were replaced at each rebalance (an assumed range, roughly 23-38 bp a year). I have no actual turnover figure, so this is a bound, not a result.
- Use for the project: these indices are a benchmark for the closed momentum book, not a signal. They are also another view that momentum has been weak relative to the broad index in 2021-2026 (5-year excess +0.8 to +1.0 points a year). The in-house trial-126 net excess of +0.71 to +1.02 %/month (section 1c of the covered file) is against a different benchmark and design and is not directly comparable.

### Gaps
- Calendar-year or financial-year returns and drawdowns for the other factor indices (value, quality, low-volatility, alpha, equal-weight): the niftyindices.com history API needs a login, and the factsheets and whitepapers I could read show only 1 to 15 year point-to-point returns. Only the Nifty200 Momentum 30 has a year-by-year table (via the HDFC deck), and only for financial years; its whitepaper's calendar-year chart has no readable numbers.
- Factsheets for the Dividend Opportunities 50, Nifty100 Quality 30, Nifty100 Equal Weight 100, Nifty Midcap150 Momentum 50 and Nifty500 Multicap factor indices were not retrievable (the downloaded files were 77.5 KB placeholders, not PDFs); the Nifty 50 factsheet is dated 30 October 2026 and was excluded as not comparable. The Nifty 50 TRI at 30 September 2026 is therefore missing, so the Nifty50 Equal Weight and Value 20 cannot be compared with their parent index.
- Turnover per rebalance and tracking error for each index: not on the factsheets I read. The cost arithmetic above is therefore a bound from my own assumptions.
- The Nifty Alpha 50 methodology and the Nifty200 Value 30 backtest start were not read.
- Backtest dates for several indices (the portion of the "since base" record before launch) are inferred from launch and base dates in the factsheets; whether NSE restated or smoothed anything is not stated.

## 6. What do open-source NSE/BSE strategy implementations report, and how reliable are they?

### Takeaway
The public GitHub space for NSE/BSE strategy backtests is almost entirely zero-star individual repositories, most created in 2026, mostly gross of costs, on current index members (survivorship), and nearly all of them re-run 12-1 momentum, which is already closed in the covered file. The only credible repos are the ones that report negatives: a point-in-time Nifty 50 study that finds no momentum rotation or dip-buying variant beats a Momentum 30 fund after costs and tax, and a 45-stock study in which a short-term reversal signal dies at 10-20 bp of cost. None of the repos I could read uses a return-predicting signal that is absent from `00-already-covered.md`.

### Cited Findings
How I searched, and what is out of reach (primary):
- GitHub only, through the REST search API (sorted by stars) and the repository README and report files; nothing was cloned. Star counts, creation and last-push dates below were read from the API on 1 November 2026. Queries covered nse backtest, nifty strategy backtest, nsepy, jugaad-data, india momentum, vectorbt nse, backtrader nifty, zipline india, bhavcopy and delivery volume.
- Kaggle, QuantConnect, QuantInsti, Zerodha Varsity, Streak and Tradetron were not reached (WebSearch budget exhausted, and those sites are not served by the GitHub API). They are listed under Gaps, not summarised.

Data tools (primary, repository metadata):
- [swapniljariwala/nsepy](https://github.com/swapniljariwala/nsepy): 808 stars, last push 24 December 2023 (stale; NSE changed its site after that, so treat as unmaintained).
- [jugaad-py/jugaad-data](https://github.com/jugaad-py/jugaad-data): 590 stars, last push 22 October 2026 (maintained; bhavcopy, index data and historical quotes).
- [girishg4t/nse-bse-bhavcopy](https://github.com/girishg4t/nse-bse-bhavcopy): 32 stars, last push 18 October 2026 (bhavcopy downloader; the best-quality momentum repo below builds on it).
- [deshwalmahesh/NSE-Stock-Scanner](https://github.com/deshwalmahesh/NSE-Stock-Scanner): 350 stars, last push 28 March 2025 (scanner with a backtesting module; I did not inspect its results).
- [ShlokVasandani/nse-backtester](https://github.com/ShlokVasandani/nse-backtester): 0 stars, created 8 September 2026, Apache-2.0. Builds an engine from bhavcopy back to 2000, adjusts for corporate actions from NSE filings, stores in DuckDB and models real delivery costs (STT, exchange charges, stamp duty, GST, DP charge, slippage). No strategy results published; useful as a cost-model cross-check only.
- [Mitul2002/nse_numba_backtester](https://github.com/Mitul2002/nse_numba_backtester): 0 stars, created 8 August 2026, pushed 24 August. Numba engine checked against vectorbt on 2,050 NSE symbols with 10 bp fees plus 10 bp slippage per fill; the strategy is an RSI(14) cross above 40 with EMA(10) above EMA(50) and ATR stops. An engine, not an edge claim; its README documents a look-ahead problem in its vectorbt baseline.

Momentum and factor repos (primary: README or report read in full; every figure is the author's own claim, not independently reproduced):

| Repo (stars; created / last push) | Strategy and claimed result | Period, universe | Costs | Data and obvious flaws | Overlap with 00 |
|---|---|---|---|---|---|
| [bHandreaPeR/nse-momentum-research](https://github.com/bHandreaPeR/nse-momentum-research) (0; 25 Oct 2026) | 12-1 momentum, top quintile (about 40 names), rebalanced quarterly, held only while the market is above its 8-month SMA: 16.2% CAGR, Sharpe 0.60, max drawdown -27.3%. Monthly rebalance with the filter 15.1% / 0.54 / -25.5%. Always invested 12.7% / 0.39 / -74.0%. Equal-weight top-200 buy and hold 11.2% / 0.33 / -70.2%. A 2-state HMM (10.1% / 0.30 / -59.5%) and an EWMA volatility switch (11.9% / 0.39 / -38.0%) both lost to the plain SMA | March 2004 to November 2024; monthly top 200 by turnover, includes later-delisted stocks | 25 bp per side plus holding-aware tax (20% short term, 12.5% long term) | Month-end data (intra-month drawdowns understated); some gold and silver ETFs in the universe; the author publishes a list of failed iterations (nine documented); the README does not say how the 8-month length was chosen, and the SMA, HMM and EWMA were all compared on the same sample, so the filter is in-sample selected | Closed momentum family (1c, trials 119, 120, 126, 127, 204) plus the index trend filter (3e row 3 "Reject as a lead") |
| [shekhar-atulya/india-factor-backtest](https://github.com/shekhar-atulya/india-factor-backtest) (0; 6 Apr 2026) | 12-1 momentum about 22.4% CAGR / Sharpe 0.92; low volatility about 21.7% / 0.89; reversal about 23.7% / 0.89; combined about 21.8% / 1.08 / -13.7%. High-volatility stocks beat low-volatility | March 2020 to March 2026; 18-20 Nifty large caps | None (gross) | Survivorship; a six-year bull-market window; 18-20 names; no costs | Closed (momentum; low-vol sleeve 3g "Leave"; reversal trials 121-122) |
| [Anyaverse/momentum-factor-backtest](https://github.com/Anyaverse/momentum-factor-backtest) (0; 16 Aug 2026) | 12-month momentum on 40 stocks: 25.2% CAGR / Sharpe 1.29 against equal weight 23.4% / 1.39 (the momentum portfolio has the lower Sharpe) | 2015-2025 | Unfilled README template | Survivorship; unverified | Closed |
| [Saru312/nifty500-momentum-backtest](https://github.com/Saru312/nifty500-momentum-backtest) (0; 31 Aug 2026; MIT) | 12-1 momentum, top quintile of the Nifty 500, monthly; README gives ranges, strategy CAGR 16.5-22.8% against 12.2-14.5% for the benchmark, Sharpe 0.85-1.15, excess +4.5 to +8.5% net of 30 bp | 10+ years | Scenarios at 10, 30 and 50 bp | README admits survivorship; `data_loader.py` mentions a synthetic fallback, so I cannot tell whether the quoted numbers use real prices; results are ranges, not one run | Closed |
| [jalajsingh1987/nifty500-momentum](https://github.com/jalajsingh1987/nifty500-momentum) (0; 10 Oct 2026) | 12-month / 6-month rotation, top 20, 200-day regime exit, stop at 2x ATR(15) | 2005 onwards | 20 bp per side | Liquidity-proxy point-in-time universe; about 300 documented Yahoo corporate-action fixes; benchmark is a price index, not a TRI; cash earns 0%; no headline results | Closed (momentum plus a regime exit and a stop layer) |
| [rishabhjain0295-web/nifty500-momentum-backtest](https://github.com/rishabhjain0295-web/nifty500-momentum-backtest) (0; 25 Jul 2026, pushed 31 Oct) | Streamlit momentum backtester with point-in-time Nifty 500 membership (470 extra historical constituents added) and an India cost and tax simulator | 1998 onwards, Yahoo | Cost and tax toggles | Membership is "best-effort"; pre-2008 data artefacts filtered; no headline numbers | Closed |
| [ninad164/auto-portfolio-management](https://github.com/ninad164/auto-portfolio-management) (1; 21 Jun 2026) | Monthly rebalanced top-15 portfolio of a Nifty 500-style universe ranked on a momentum, quality and liquidity composite, with stock and sector caps and a monthly contribution | 2020-2025 demo | 0.20% default | README says the demo outputs are synthetic and "must not be used for performance conclusions"; no headline numbers | Closed (momentum; quality "Skip" in 3f) |
| [Hari-sh-S/investing-scanner](https://github.com/Hari-sh-S/investing-scanner) (0) | Streamlit momentum ranking and regime filters | n/a | n/a | No results published | Closed |
| [rraju26/pyIndiaFactorInvesting](https://github.com/rraju26/pyIndiaFactorInvesting) (8; last push June 2026) | Teaching notebooks on the Invespar Indian factor library (SMB, HML, WML, Fama-French four and five factor, momentum crashes) | n/a | n/a | Education only | n/a |
| [kethan-git/delivery-volume-trigger-engine](https://github.com/kethan-git/delivery-volume-trigger-engine) (0; Jan 2026) | Screen that flags weekly delivery quantity above a multiple (X_TIMES) of its historical average, using jugaad-data bhavcopy | n/a | n/a | A screen only; no backtest and no returns claimed | Deliverable % is "Reject for now" (3e row 10); this is delivery quantity, but no evidence either way |

Negative or sceptical repos (primary: README plus reports read in full):
- [vishalvx/niftyshop-backtester](https://github.com/vishalvx/niftyshop-backtester) (0 stars; created 28 June 2026, pushed 4 October; MIT) is the most careful repo I found: point-in-time Nifty 50 membership, total-return benchmarks, a deflated Sharpe ratio, start-date and capital jitter, and a written retraction of its own earlier numbers (the original engine was retired in October 2026 because "its published numbers came from a data-loader bug"). Its long-run study finds that no variant of its dip-buying ("NiftyShop") strategy clears 15% a year after costs and tax, and none reliably beats its own index after tax — [README](https://github.com/vishalvx/niftyshop-backtester) and [long-run-findings.md](https://github.com/vishalvx/niftyshop-backtester/blob/main/reports/long-run-findings.md).
- Same repo, frozen-in-advance momentum study (Nifty 50 members, February 2008 to August 2025, statutory charges, 10 bp slippage a side and dated capital-gains tax): eight momentum rotations; the best matches or beats the Nifty 50 after costs and tax (the 6-month, top-20, unfiltered NSE-style rotation is +1.10 points a year), but every one trails an index fund tracking the Nifty200 Momentum 30 by 4.5 to 11.1 points a year in the typical window, so "none is kept". The 200-day market filter hurt most: the four filtered variants hold cash about a quarter of the time and trail the index by 4.3 to 4.8 points a year, 4.75 points a year on the paired comparison (no filter +0.17, with filter -4.57), and still 2.9 to 3.4 with idle cash earning 6% — [momentum-nifty50-findings.md](https://github.com/vishalvx/niftyshop-backtester/blob/main/reports/momentum-nifty50-findings.md). Limits stated by the author: nine Nifty 50 members lack price history, and the Midcap list is not point-in-time (2019-2026 only).
- [abhinav77071/nse-reversal-momentum](https://github.com/abhinav77071/nse-reversal-momentum) (0 stars; 16 Oct 2026): sector-neutral, dollar-neutral long-short on 45 Nifty large caps, Yahoo daily data 2016-2026, next-day execution, 10 bp per unit of turnover, smoothing span chosen on 2016-2022 only. Full-period Sharpe, gross and net: momentum -0.22 and -0.33; raw 5-day reversal 1.37 and -0.06; EWM-smoothed reversal 1.57 and 0.53. Smoothed reversal net Sharpe is 0.53 at 10 bp but -0.51 at 20 bp. Out of sample (2023-2026) the smoothed reversal falls to gross 0.89 and net -0.37; mean daily IC fell from about 0.035 (2016-17) to 0.01-0.02 (2023-25), which the author reads as alpha decay. Short leg needs futures or securities lending, so it is not a delivery-only strategy.

Other strategy repos (primary):
- [AtharvaMistry/ou-pairs-trading-nse](https://github.com/AtharvaMistry/ou-pairs-trading-nse) (1 star; 12 Oct 2026): Ornstein-Uhlenbeck and cointegration pairs on 5 IT stocks (10 pairs), 2019-2026, 0.2% per leg round trip: +13.0% with a 3x half-life stop and Sharpe 0.88 (11.5% and 0.67 with no stop); most of the profit is in 2019-2021 and then fades. Tiny universe, and the short leg is not available in delivery.
- [devil0026/pairs-trading-nse](https://github.com/devil0026/pairs-trading-nse) (0; March 2026): sector-constrained cointegration pairs, 60/40 walk-forward, 0.1% commission plus 0.05% slippage per leg; no headline numbers; short leg needs futures.
- [niranjan-bhol/nse-index-momentum-research](https://github.com/niranjan-bhol/nse-index-momentum-research) and [srini182004/stocks-analyzer](https://github.com/srini182004/stocks-analyzer) have empty READMEs; [jesso1908/Backtesting](https://github.com/jesso1908/Backtesting) (backtrader on the Nifty 50, 2021) has a 128-byte README. Not usable as evidence.
- Not read (README unopened or no reported results): [aryashreep/nse-ai-agent](https://github.com/aryashreep/nse-ai-agent) (momentum-screening CLI), [RupeezyTech/algo_ai_skill](https://github.com/RupeezyTech/algo_ai_skill), [piyushdave6/algo-trading-backtesting-engine](https://github.com/piyushdave6/algo-trading-backtesting-engine), [DoRmAmMu1997/My-Algo-Trading-Code](https://github.com/DoRmAmMu1997/My-Algo-Trading-Code), [rugvedshete/Cointegration-StatArb-PairsTrading-NSE](https://github.com/rugvedshete/Cointegration-StatArb-PairsTrading-NSE), [builditwithgk/dhan-nifty-algo-trading-lab](https://github.com/builditwithgk/dhan-nifty-algo-trading-lab), [chandewardnyanesh/vol-target-bot](https://github.com/chandewardnyanesh/vol-target-bot) (options).

Which repos use a signal not in `00-already-covered.md` (my read):
- None of the readable repos does. Momentum (12-1, 6-month, 12-month), 5-day reversal, low volatility, an index moving-average regime exit, ATR stops, dip buying, RSI/EMA crossovers and pairs trading are all either closed lines in 00 (section 1c; trials 121-122; 3g "Leave") or are not delivery strategies (pairs, long-short).
- The nearest thing to a new input is delivery quantity (kethan-git), but it is a screen without a backtest, and 00 carries deliverable percent as "Reject for now" (3e row 10) and lists it among the rejected Part B items.
- The one useful import is methodological: bHandreaPeR's published list of failures and vishalvx's paired with/without-filter table are both worked examples of reporting a selected parameter honestly.

### Inferences
- Treat this section as a catalogue of what is not worth a pre-registered trial. The positive headline numbers (16-25% CAGR) come from gross or lightly costed runs on 18-45 current large caps or on a top-200 turnover universe with a hand-picked filter, over windows dominated by the 2020-2025 bull market; the only two repos that tested rigorously (vishalvx, abhinav77071) report the signal does not survive costs or trails a cheap factor fund.
- The two momentum-with-trend-filter results conflict: bHandreaPeR's top-200 universe 2004-2024 finds the 8-month SMA lifts CAGR from 12.7% to 15.1-16.2% and cuts drawdown from -74% to about -26%, while vishalvx's Nifty 50 rotation 2008-2025 finds a 200-day filter costs about 4.75 points a year. The difference is the universe, the filter length, the benchmark (equal-weight market against an index fund) and the tax model, and both are single backtests with the filter chosen in-sample. This is consistent with 00's verdict (3e row 3: at most a reported-only variant); it adds no reason to reopen it.
- For the reversal result, the sign agrees with 00 (reversal closed at trials 121-122): even a long-short version with next-day execution loses its net edge by 10-20 bp of cost, which is below the 38 bp delivery hurdle used here.

### Gaps
- Kaggle notebooks, QuantConnect algorithms and forum posts, QuantInsti and Zerodha Varsity articles, Streak and Tradetron strategy marketplaces: not searched (WebSearch budget exhausted; these sites are not on the GitHub API). Marketplace strategies on Streak and Tradetron are mostly intraday or derivatives and, if they publish backtests, are unlikely to be net of realistic costs; that expectation is untested.
- vectorbt-, backtrader- and zipline-based NSE repos: the few I found (jesso1908/Backtesting and similar) had empty READMEs. I did not read any code, only READMEs and, for vishalvx, the report files.
- None of the readable repos' numbers was re-run by me; all figures are the authors' own claims. Several are inconsistent with themselves (Saru312 reports ranges; Anyaverse's momentum Sharpe is below equal weight despite the higher CAGR).
- Star counts are tiny (0-8 for every repo with a backtest), so there is no community scrutiny; popularity gives no information about correctness.
- Whether any maintained repo adjusts for delisted-stock returns correctly beyond bHandreaPeR (which includes delisted names) and vishalvx (point-in-time membership, with nine Nifty 50 members lacking history): not checked.

## 7. Candidate register: which factor-zoo and open-source signals are worth a pre-registered test for a long-only delivery book, and what are the negative findings?

### Takeaway
No candidate is a new price-only signal: every price-only survivor in the Indian factor zoo (momentum variants, 52-week high, residual momentum) is a closed or deferred line in `00-already-covered.md`, and the open-source scan added nothing new. The only genuinely new lines are accounting-based (net operating assets growth, free cash flow to price, the Stambaugh-Yuan management composite, accruals); their value-weighted 2015-2025 spreads are +0.2 to +0.4 %/month with t-statistics of 1.2 to 2.1, below the multiple-testing bar, they need a point-in-time fundamentals dataset that the project does not hold, and they clear the roughly 38 bp hurdle only if re-sorted about once a year. The negative list below is longer than the positive one.

### Cited Findings
Method for this register (primary unless marked):
- Effect sizes are JKP tercile long-short returns (top third minus bottom third by the factor, one-month hold, gross of costs, shorts included), India, to December 2025, recomputed by me from the JKP files; "EW" is equal-weighted and "VW" is value-weighted with capped weights; t is the naive mean over standard error — [JKP data](https://jkpfactors.com/data). Original-paper author, year and in-sample period come from JKP's factor-details file — [factor_details.xlsx](https://github.com/bkelly-lab/jkp-data/raw/main/src/jkp/data/resources/factor_details.xlsx). Journal names and DOIs are not in that file and were not fetched (see Gaps).
- The tradable screen is the VW 2015-2025 column, because the project's universe is the top 400-800 by traded value (section 2).
- JKP stores only the long-short return, so the long-only leg and the costs are my assumptions, labelled as such: long leg earns 0.5 to 0.67 of the long-short spread (rule of thumb carried over from section 2, not measured); a full re-sort costs one round trip of 38 bp (working number, from the hurdle paragraph at the top), so 38 bp a month if re-sorted monthly, about 12.7 bp a month quarterly, about 6.3 bp semi-annually and about 3.2 bp annually. These are upper bounds for turnover (full replacement) and ignore tax and the DP charge's dependence on position size.

Register part 1: evidence (JKP India, %/mo with naive t in brackets; EW = equal-weighted tercile spread, VW = capped value-weighted):

| ID | Candidate (JKP id) | Original paper (JKP cite; original US in-sample) | India sample | EW all | VW all | EW 2015-25 | VW 2015-25 | Replicates in India? |
|---|---|---|---|---|---|---|---|---|
| C1 | 12-1 momentum (ret_12_1) | Jegadeesh-Titman 1993; 1965-1989 | 1989-2025 | +0.65 (2.7) | +0.93 (3.0) | +0.81 (3.0) | +0.81 (2.7) | Yes, VW t just under 3 |
| C2 | 6-1 and 9-1 momentum (ret_6_1, ret_9_1) | Jegadeesh-Titman 1993; 1965-1989 | 1989-2025 | +0.35 (1.6); +0.47 (2.1) | +0.96 (3.6); +0.91 (3.1) | +0.53 (2.4); +0.71 (2.9) | +0.66 (2.5); +0.80 (2.7) | Yes, VW |
| C3 | Intermediate momentum (ret_12_7) | Novy-Marx 2012; 1925-2010 | 1989-2025 | +0.64 (3.3) | +0.71 (2.6) | +0.74 (3.2) | +0.57 (2.2) | Yes |
| C4 | Year-1 lagged return, non-annual (seas_1_1na), classed by JKP as momentum | Heston-Sadka 2008; 1965-2002 | 1989-2025 | +0.35 (1.5) | +0.93 (3.1) | +0.61 (2.5) | +0.69 (2.4) | VW yes, EW no |
| C5 | 52-week-high proximity (prc_highprc_252d) | George-Hwang 2004; 1963-2001 | 1989-2025 | +0.53 (1.9) | +0.70 (2.3) | +0.91 (2.6) | +0.38 (1.2) | Weak |
| C6 | Residual momentum (resff3_12_1) | Blitz-Huij-Martens 2011; 1930-2009 | 2004-2025 | +0.91 (6.6) | +0.25 (1.4) | +1.03 (6.5) | +0.41 (2.3) | EW strongly, VW weakly (small-cap driven) |
| C7 | Change in net operating assets (noa_gr1a) | Hirshleifer et al. 2004; 1964-2002 | 2000-2025 | +0.66 (3.3) | +0.81 (4.3) | +0.28 (2.1) | +0.33 (1.7) | Yes full sample, fades after 2015 |
| C8 | Free cash flow to price (fcf_me) | Lakonishok-Shleifer-Vishny 1994; 1963-1990 | 1999-2025 | +0.74 (6.0) | +0.94 (3.1) | +0.44 (4.1) | +0.36 (2.1) | Yes |
| C9 | Stambaugh-Yuan mispricing, management (mispricing_mgmt) | Stambaugh-Yuan 2016; 1967-2013 | 2000-2025 | +0.70 (2.7) | +0.90 (3.6) | +0.22 (1.7) | +0.38 (1.9) | Yes full sample, fades |
| C10 | Operating accruals, percent accruals, working-capital change (oaccruals_at, oaccruals_ni, cowc_gr1a) | Sloan 1996 (1962-1991); Hafzalla-Lundholm-Van Winkle 2011 (1989-2008); Richardson et al. 2005 (1962-2001) | 2000-2025 | +0.56 (3.9); +0.42 (3.5); +0.34 (2.8) | +0.63 (2.5); +0.68 (2.9); +0.48 (2.5) | +0.25 (2.0); +0.17 (1.4); +0.11 (1.2) | +0.21 (1.2); +0.16 (0.8); +0.20 (1.3) | Yes full sample, VW gone after 2015 |
| C11 | Consecutive quarters of rising earnings (ni_inc8q) | Barth-Elliott-Finn 1999; 1982-1992 | 2006-2025 | +0.43 (3.0) | +0.56 (2.2) | +0.49 (3.6) | +0.32 (1.7) | Yes, EW stable |
| C12 | Net share issuance (chcsho_12m; netis_at) | Pontiff-Woodgate 2008 (1970-2003); Bradshaw-Richardson-Sloan 2006 (1971-2000) | 1989-2025; 1999-2025 | +0.33 (1.3); +0.77 (4.0) | +0.68 (2.1); +0.56 (1.6) | -0.00 (0.0); +0.32 (2.0) | -0.15 (-0.5); +0.08 (0.3) | Gone after 2015 |
| C13 | Inventory and asset growth (inv_gr1; at_gr1) | Belo-Lin 2011 (1965-2009); Cooper-Gulen-Schill 2008 (1968-2003) | 2003-2025; 2000-2025 | -0.01 (-0.1); +0.33 (1.0) | +0.36 (2.3); +0.47 (1.6) | -0.10 (-0.8); -0.06 (-0.4) | +0.48 (3.1); +0.20 (1.0) | No (EW and VW disagree on sign for inv_gr1) |
| C14 | Illiquidity and trading volume (ami_126d, dolvol_126d) | Amihud 2002 (1964-1997); Brennan-Chordia-Subrahmanyam 1998 (1966-1995) | 1997-2025 | +1.01 (3.0); +1.00 (3.0) | +0.60 (2.5); +0.60 (2.5) | +0.98 (2.3); +0.98 (2.3) | +0.40 (1.3); +0.34 (1.2) | EW yes (illiquidity premium), VW weak |
| C15 | Classic value ratios (be_me, sale_me, ebitda_mev, div12m_me) | Rosenberg-Reid-Lanstein 1985; Barbee et al. 1996; Loughran-Wellman 2011; Litzenberger-Ramaswamy 1979 | 1989-2025 | +0.63 (1.3); +0.79 (1.9); +0.36 (1.4); +0.39 (1.8) | -0.07 (-0.1); +0.32 (0.7); -0.01 (0.0); +0.26 (1.0) | +0.96 (3.3); +0.81 (2.5); +0.61 (2.5); +0.59 (3.6) | +0.23 (0.6); +0.35 (1.1); +0.29 (1.0); +0.11 (0.5) | EW only |
| C16 | Low risk (corr_1260d, beta_60m, ivol_capm_21d, rmax5_21d) | Asness et al. 2020; Fama-MacBeth 1973; Bali et al. 2017 | 1988-2025 | +0.61 (2.4); +0.20 (0.8); +0.06 (0.2); -0.28 (-1.0) | +0.45 (2.0); -0.14 (-0.4); +0.09 (0.4); -0.15 (-0.5) | +0.56 (1.5); +0.42 (1.1); +0.50 (1.8); -0.03 (-0.1) | +0.02 (0.1); -0.28 (-0.7); +0.09 (0.3); +0.15 (0.6) | No |
| C17 | Change in operating cash flow to assets (ocf_at_chg1) | Bouchard et al. 2019; 1990-2015 | 2000-2025 | +0.48 (3.4) | +0.51 (2.4) | +0.25 (3.2) | -0.03 (-0.2) | VW gone after 2015 |
| C18 | Short-term reversal (ret_1_0) | Jegadeesh 1990; 1929-1982 | 1988-2025 | +0.45 (2.2) | -0.36 (-1.4) | -0.48 (-1.7) | +0.27 (1.2) | No (sign flips between EW and VW) |

All rows: JKP India panel via the [JKP data page](https://jkpfactors.com/data); the original in-sample periods via [factor_details.xlsx](https://github.com/bkelly-lab/jkp-data/raw/main/src/jkp/data/resources/factor_details.xlsx); statistics mine.

Register part 2: tradability, with my cost arithmetic (assumptions as stated above; "arithmetic" means the cost hurdle only, not the statistical bar). Long leg = 0.5 to 0.67 of the VW 2015-25 spread; net = long leg minus re-sort cost at the stated frequency.

| ID | Turnover and holding assumed | Gross or net | Data | Long-leg estimate and net, %/mo | Clears the ~38 bp hurdle? | Overlap with 00-already-covered.md |
|---|---|---|---|---|---|---|
| C1 | JKP monthly formation, 1-month hold; in-house book is slower | JKP gross; in-house trial 126 is net | P | n/a, already run: in-house net excess +0.71 to +1.02 %/mo (section 1c) | In-house momentum book is positive after costs but borderline: trial 126 net excess +0.71 %/mo (t 2.51), trial 127 +1.02 %/mo (t 2.76, below its 2.807 gate, FAIL) | Closed: slow cross-sectional momentum family, trials 119, 120, 126, 127, 204 (1c) |
| C2 | As C1 | Gross | P | ret_6_1 0.33-0.44; ret_9_1 0.40-0.53 gross; monthly full re-sort costs 0.38, which would consume ret_6_1 | Marginal at monthly, fine at slower rebalance | Closed: same family; lookback grids "Leave" (3g) |
| C3 | As C1 | Gross | P | 0.29-0.38 gross | Marginal at monthly | Same family; not a separate trial; lookback grids "Leave" (3g) |
| C4 | Monthly (price signal) | Gross | P | 0.35-0.46 gross | Marginal at monthly | Not in 00 as such; a momentum variant by JKP's own classification and correlated with C1; at most a test of incremental value over the momentum book |
| C5 | Monthly | Gross | P | 0.19-0.25 gross | No | 3g "52-week high: Leave"; 3f "Skip: 52-week-high proximity" |
| C6 | Monthly | Gross | P | 0.21-0.27 gross | No at monthly (0.38 cost) | 3e row 5 "Defer"; 3g "Residual momentum: Leave"; 2026-09-27 sweep also rejected it |
| C7 | Annual statements, annual re-sort assumed | Gross | F | 0.17-0.22 gross; 0.14-0.19 net of 3.2 bp | Yes on arithmetic; t 1.7 is not distinguishable from zero | Not in 00 |
| C8 | Annual statements, price in the denominator drifts; annual or semi-annual re-sort assumed | Gross | F | 0.18-0.24 gross; 0.15-0.21 net at annual, 0.12-0.18 at semi-annual | Yes on arithmetic; t 2.1 | Not run as such; "value composite in the top 400-500" is a listed pre-registration item in 3f, but 3g says "Dividend-yield sleeve; value; quality: Leave" |
| C9 | Annual, composite of several accounting signals | Gross | F | 0.19-0.25 gross; 0.16-0.22 net at annual | Yes on arithmetic; t 1.9 | Not in 00 as a composite; it embeds net issuance, accruals and asset growth items that are C7, C10, C12 and C13, so it is one family with them, not four |
| C10 | Annual | Gross | F | oaccruals_at 0.11-0.14 gross, 0.08-0.11 net; cowc_gr1a 0.13-0.17 gross | Yes on arithmetic but tiny; t 0.8-1.3 | Not in 00 |
| C11 | Quarterly results, quarterly re-sort assumed | Gross | F (quarterly) | 0.16-0.21 gross; 0.03-0.08 net of 12.7 bp | Marginal; t 1.7 | Partial: earnings momentum "closed by §84" (3f Skip) and PEAD L39 NO-GO; this is earnings persistence, not surprise, but the same data and the same family |
| C12 | Event-like, annual re-sort assumed | Gross | F | VW 2015-25 is -0.15 and +0.08, so no long-leg estimate | No | Partial: buyback/promoter events are Pivot B (section 4); "Buyback tender reserve: Leave" (3g) |
| C13 | Annual | Gross | F | inv_gr1 0.24-0.32 gross but sign unstable | No (thin, unstable evidence) | Not in 00 |
| C14 | Monthly, illiquid names | Gross | P | 0.20-0.27 gross | No: these stocks sit outside the top 400-800 by traded value, where slippage is far above the 10 bp assumed | 3f "Skip: liquidity, illiquidity" and micro-caps; "tested in §85" |
| C15 | Annual to semi-annual | Gross | F | VW 2015-25 +0.11 to +0.35, t 0.5-1.1 | No | 3f "value composite in the top 400-500" (pre-register candidate); 3g "value: Leave" |
| C16 | Monthly or quarterly | Gross | P | VW 2015-25 about 0 | No | 3f "Skip: beta, IVOL"; 3g "Low-vol sleeve: Leave"; Pivot B low-vol overlay (section 4) |
| C17 | Quarterly | Gross | F | VW 2015-25 -0.03 | No | Not in 00 |
| C18 | Weekly to monthly | Gross | P | VW sign negative | No | Closed: trials 121-122; 3e #12 "Reject"; 3f "Skip" |

Register part 3: non-JKP candidates and benchmarks from the scan:

| ID | Candidate | Evidence (source) | Net or gross; sample | Data | Clears ~38 bp? | Overlap with 00 |
|---|---|---|---|---|---|---|
| C19 | Gu-Kelly-Xiu style neural net on India | Choi-Jiang-Zhang 2023: India NN Sharpe 4.4-4.6 EW, 2.1-2.8 VW, test 2013-2017 — [PDF](https://www.abfer.org/media/abfer-events-2023/annual-conference/papers-investment/AC23P3084-Alpha-Go-Everywhere-Machine-Learning-and-International-Stock-Returns.pdf) | Gross, shorts included, small stocks included; five-year test | F (36 characteristics) | Not testable: no long-only leg, no costs, no turnover for India | Closed or untestable: the price-only inputs are the closed families (1b to 1d) |
| C20 | LLM ranking of Nifty stocks | Sodha 2025: no net advantage under realistic costs — [arXiv 2511.08608](https://arxiv.org/abs/2511.08608) | Net; 5-36 stocks, 1-day horizon | Text and prices | No | LLM news check "Leave" (3h); Kronos/TSFM family closed |
| C21 | Nifty200 Momentum 30 index fund as a benchmark, not a signal | Live 5-year excess over the Nifty 200 TR about +0.8 to +1.0 points a year; backtest-to-live CAGR gap shrinks from 5.6 to 2.3 points a year — [HDFC deck](https://files.hdfcfund.com/s3fs-public/Others/2026-07/HDFC%20NIFTY200%20Momentum%2030%20Index%20Fund_PPT%20%28July%202026%29.pdf), [factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Momentum30.pdf) | TRI, gross of fund costs and trading | P | n/a | 3e row 13 "NSE factor indices: fallback implementation, not a signal" |
| C22 | Nifty Alpha 50 past-alpha sort | Factsheet: 5Y +12.03% vs Nifty 200 TR +8.30%, i.e. +3.7 points a year, quarterly rebalance, beta 1.19 — [factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Alpha_50.pdf) | Index return, gross; methodology unverified | P | Quarterly re-sort would cost up to 12.7 bp a month on my assumption | 3g "Alpha 50-style signal (1-year Jensen alpha): Leave" |
| C23 | Index moving-average regime exit | bHandreaPeR: 8-month SMA lifts momentum from 12.7% to 15.1-16.2% CAGR and drawdown from -74% to about -26%, net of 25 bp and tax, 2004-2024 — [repo](https://github.com/bHandreaPeR/nse-momentum-research); against vishalvx: a 200-day filter costs 4.75 points a year on Nifty 50 rotations, 2008-2025 — [report](https://github.com/vishalvx/niftyshop-backtester/blob/main/reports/momentum-nifty50-findings.md) | Net in both; the two disagree | P | Not a return source | 3e row 3 "Reject as a lead. At most a reported-only variant"; 3g "Bear-market filter: Leave" |
| C24 | Delivery-quantity trigger | [kethan-git](https://github.com/kethan-git/delivery-volume-trigger-engine): a screen, no backtest | None | P (delivery % in bhavcopy) | Unknown | 3e row 10 "Deliverable %: Reject for now" |

Negative findings, listed explicitly (every one is primary evidence read or computed in this note):
- Quality, profitability and leverage factors have the wrong sign in India: Profitability theme EW -0.28 %/mo (t -1.2), VW -0.10; Low-leverage theme EW -0.46 (t -1.5), VW -0.53 (t -1.6); of the individual factors, o_score, z_score, saleq_gr1 (EW -0.91, t -6.7) and aliq_mat (EW -1.49, t -6.0) are significantly negative — section 2 and the appendix, from the [JKP data](https://jkpfactors.com/data).
- The equal-weighted effects that look strongest vanish under value weighting: earnings surprise (niq_su EW +0.91, t 7.5; VW +0.26, t 1.2), residual momentum (EW +0.91, t 6.6; VW +0.25, t 1.4), liquidity (EW about +1.0; VW +0.6 falling to +0.34-0.40 after 2015) and short-term reversal (EW positive to 2014, VW negative) — same source. In-house PEAD stage A on the NIFTY 100 found gross +0.25 %/mo with Newey-West t 1.41 (L39 NO-GO).
- Accounting-factor spreads roughly halve or vanish after 2015 on a value-weighted basis: accruals theme VW +0.37 to +0.11, quality theme VW +0.41 to -0.01, net issuance (chcsho_12m) VW -0.15 and ocf_at_chg1 VW -0.03 in 2015-2025 — same source.
- The classic book-to-market ratio does not pay in India on a value-weighted basis (be_me VW -0.07, t -0.1; value theme VW +0.25, t 1.1) — same source.
- The low-risk theme is indistinguishable from zero value-weighted (+0.10 %/mo, t 0.5); only equal-weighted low risk after 2015 shows a premium (+0.55, t 3.5) — same source.
- Live factor-index track records are weaker than backtests: the Nifty200 Momentum 30 CAGR gap over the Nifty 200 falls from 5.6 to 2.3 points a year pre- to post-launch, and its 5-year excess is +0.8 to +1.0 points against a whitepaper in which 65.5 per cent of five-year windows exceeded +4 points; the quality indices (Nifty200 Quality 30 5Y excess -1.9, Quality Low-Volatility 30 -2.5 points a year) lag the Nifty 200 TR — section 5 and the [factsheets](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Momentum30.pdf).
- Machine learning: the only net-of-cost NSE study I found (Sodha 2025) is negative, and the one multi-factor India ML result (Choi-Jiang-Zhang) is gross, includes shorts and small stocks, and ends in 2017 — [arXiv 2511.08608](https://arxiv.org/abs/2511.08608).
- Short-term reversal does not survive costs even with smoothing: abhinav77071 reports smoothed reversal net Sharpe 0.53 at 10 bp but -0.51 at 20 bp, and net -0.37 out of sample 2023-2026 — [repo](https://github.com/abhinav77071/nse-reversal-momentum).
- DIY momentum on large caps trails a cheap factor fund: eight frozen Nifty 50 momentum rotations all trail a Nifty200 Momentum 30 index fund by 4.5 to 11.1 points a year after costs and tax; no dip-buying variant clears 15% a year after costs and tax; a 200-day filter cost about 4.75 points a year — [vishalvx reports](https://github.com/vishalvx/niftyshop-backtester/blob/main/reports/momentum-nifty50-findings.md).
- Low-volatility results depend on horizon: Saraf and Kayal (2022, Nifty 500, 2010-2020) find the volatility anomaly at 5-10 year horizons and negligible at 6 months to 3 years (search summary, matched by topic, unverified) — [MSE Working Paper 215](https://mse.ac.in/wp-content/uploads/2022/03/Working-Paper-215.pdf); the live Low Volatility 50 5-year excess is 0.0 against the Nifty 200 TR — [Low Volatility 50 factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Low_Volatility_50.pdf).
- Open-source repos: none of the readable ones reports a net-of-cost, point-in-time, out-of-sample edge that beats a cheap benchmark (section 6). The two repos that apply realistic costs and compare against a benchmark (vishalvx, abhinav77071) find the edge negative or gone; the one positive net-of-cost result (bHandreaPeR, 16.2% CAGR with an 8-month SMA filter) selected its filter in-sample and is contradicted on a different universe by vishalvx.

### Inferences
- Priority order if the owner wants any of this tested (my judgement, not a finding): (1) nothing price-only; (2) if a point-in-time fundamentals source is ever added, one pre-registered accounting-quality family test, using fcf_me first (VW t 2.1 and EW t 4.1 in 2015-25, positive in both halves, but the VW spread fell from +1.37 %/mo, t 2.7, before 2015 to +0.36 after) with noa_gr1a and the accruals items treated as the same family for trial counting; (3) keep C21 (the Momentum 30 fund) as the benchmark that any momentum change has to beat.
- The accounting candidates fail the multiple-testing bar on their own numbers: VW 2015-25 t-statistics of 1.2 to 2.1 sit under the Harvey-Liu-Zhu bar of 3 cited in section 1, and they are one of 153 x 2 JKP cells examined, so a 2.1 here is what chance would produce. They are worth more as a diversifier question (do they add to the momentum book?) than as a standalone edge.
- Annual re-sort is the only cadence at which the cost hurdle is cleared by the arithmetic: at monthly cadence the 38 bp hurdle equals or exceeds the long-leg estimate for every factor in the table.
- C4 (seas_1_1na) looks new on the "price-only survivor" screen but is momentum by JKP's classification, with a VW spread nearly identical to ret_9_1 and ret_6_1; it is not independent evidence.
- The conflict between the two trend-filter repos (C23) is not resolvable from public READMEs; neither alters 00's verdict.

### Gaps
- No point-in-time Indian fundamentals dataset is named in section 5a of the covered file (local data are bhavcopy, corporate actions, 5-minute Kite bars for the NIFTY 100, NSE filings events, index files). I did not find or verify a free point-in-time source; NSE XBRL results and commercial vendors are untested ideas. Every F candidate depends on this.
- JKP gives no long-only leg, no turnover, no capacity and no costs; the long-leg fraction (0.5 to 0.67) and the full-replacement turnover are my assumptions, not measurements. A direct long-only test on the project's top-400 universe would be needed to replace them.
- The t-statistics are naive (no Newey-West, no multiple-testing correction, correlated within themes), and the JKP universe is wider than the project's. None of the register was re-run on the project's data.
- Journal names, DOIs and URLs for the original papers were not fetched (JKP's file has author, year and sample only); McLean-Pontiff post-publication decay and Griffin-Kelly-Nardari India results were unobtainable (section 1 Gaps). The original-paper t-statistics in JKP's factor-details file have inconsistent signs and are not used.
- Nifty Alpha 50 methodology (C22) not read; Dividend Opportunities 50, Nifty100 Quality 30 and Midcap150 Momentum 50 factsheets not retrievable.
- Kaggle, QuantConnect, QuantInsti, Zerodha Varsity, Streak and Tradetron were not searched, so absence of a new signal in the open-source scan is a statement about GitHub only.
- Fresh-sample evidence after December 2025 for the JKP factors does not exist in the files I used; the 2026 window is untouched here.
