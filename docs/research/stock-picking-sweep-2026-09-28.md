# Stock-picking sweep: should the first pick come from more stocks? (2026-09-28)

**Owner's question, 2026-09-28:** "start research on stock picking maybe
increase from 100 to all stocks not just 100 and if our first pick is wrong
then whole analysis is useless".

**Reworded on 2026-09-28 after reviewer entry 20** (seven statements that
claimed more than the sources show; listed in the pre-registration's
amendment 1).

This note is a reading of outside evidence and of trading frictions. It
computes no strategy return from project data. The test that follows from it
is pre-registered in `prereg-universe-width.md`.

## Where the first pick is made today

| Book | Picks from | Picks | Evidence for the rule |
| --- | --- | --- | --- |
| Intraday scanner (`backend/scanner.py`) | NIFTY 100 | the 25 most-traded, fixed for the day (README section 91) | None. No intraday rule tested here has an edge after costs |
| Paper momentum book (`backend/momentum_book.py`) | every NSE equity share, ranked by traded value; the 200 most-traded | 15, monthly | Trial 120 passed; the same rule worked as a separate book on ranks 201–400 (L38); the 8 held-out months of 2026 had the same sign (a sign check, t 1.08, and 2026 was partly seen) |

So the two books have different answers.

- **Intraday.** One wider list was measured: 113 F&O stocks outside the
  NIFTY 100. There the one real intraday effect was worth 0.26× of its cost
  (L26) and the intraday return was negative on average (L27). Those stocks
  also cleared the reward-to-risk gate less often than the NIFTY 100, even
  at zero cost (L34), though the ledger calls that proxy weak evidence.
  Less-traded stocks cost more to trade. On the two lists measured no rule
  cleared costs, so a third list is not tested here.
- **Delivery.** The rule already starts from all listed shares and keeps the
  200 most-traded. Whether 200 is the right cut is an open question, and it
  can be tested on stocks no test here has read. That is what the
  pre-registration does.

## Short answer from the two sweeps

1. In published backtests, which are gross of costs, momentum shows up in
   every size tier studied in India. Whether it survives costs in
   less-traded stocks is the question the pre-registered test asks.
2. Backtests say a wider universe earns more (one study: about 35% a year
   from the top 750 against 25% from the top 200), with more volatility and
   much longer recoveries.
3. The live record does not agree so far. NSE's three wider momentum indices
   launched in 2023–24 trail their parent indices by 2 to 6 points a year
   (to 31 August 2026; 3 to 7 points to 30 June 2026).
   Their live periods are short (2.2 to 2.7 years) and include the 2024–25
   momentum slump.
4. "All stocks" is not tradable. Beyond about rank 1,500 by traded value,
   13% of stock-days have no trade and half the names spent part of 2025 in
   trade-for-trade. A ₹1–10 lakh book can trade honestly to about rank
   800–1,000.
5. The cost figures for less-traded stocks are judgements, not measurements.
   The only tiered order-book study found is from 2010.
6. A data gap was found on the way: the price loaders read the EQ series
   only, so a held stock that moves to trade-for-trade is priced at a stale
   close (#175).

## Data read by this sweep (for the ledger)

- Published 2020–2026 returns of NSE momentum, value, quality and
  low-volatility indices and of index funds tracking them. This partly
  exposes 2026 for any later trial in those families.
- The project's 2025 bhavcopies, for descriptive statistics by liquidity
  tier: traded value, number of trades, days with no trade, band locks,
  series membership, and two spread estimators built from daily high, low
  and last price. Ranks 1 to 1,892. No momentum score and no strategy return
  was computed. Script and its printed output:
  `data/stock-picking-sweep/tiers_2025_descriptive.py` and `.out.txt`.
- Nothing dated 2026 was read from project data.

---

## Part A — evidence on universe width and on other signals

Read-only. No repo file changed, no `backend/research` script run, no return computed from project data. Repo paths are relative to `~/Projects/webapp`. Figures marked **(own calc)** were computed in this sweep from NSE Indices' monthly dashboards and factsheets, or from AMFI fund NAVs; the working files were throwaway and are not in the repo; every source is linked.

**Data-read disclosure for `docs/research/trials.md`:** this sweep read published 2024–2026 returns of NSE momentum, value, quality and low-volatility indices and of index funds tracking them. That partly exposes 2026 for any later value or low-volatility trial.

### Bottom line

On the project's own data the rule also worked as a separate book on ranks 201–400 (+1.00%/month net, t 3.31; `docs/research/results-3i-momentum-corrected-data.md`). No single book picking from ranks 1–400 has been run. It supports *testing* ranks 401–800, not adopting them, and it does not support "all stocks". Backtests say wider is better: about 35%/yr from the top 750 against 25% from the top 200 in one long study, and NSE's own mid- and small-cap momentum backtests show 6–7 pp/yr over their parents. The live record says otherwise so far. NSE's large/mid-cap momentum index is about 2 pp/yr ahead of its parent over six live years, the mid-cap one is level over four, and the three wider-tier indices launched in 2023–24 trail their parents by 2–6 pp/yr to 31 August 2026 (3–7 to 30 June). Those wider windows are only 2–2.7 years and contain the 2024–25 momentum slump, so they do not show small-cap momentum is absent; they show the backtested premium has not been earned live. In the one survivorship-corrected academic table, small-cap winners earned no more than large-cap winners, with more volatility. The owner's worry is not answered by these sources: they show momentum in every tier in gross backtests, and whether it survives costs in less-traded tiers is what the pre-registered test asks. Cautions: spreads and circuit locks are unmeasured here, drawdowns deepen with width, and nothing below is a forecast or a promise of profit.

### Evidence

| Source | Universe tier | Period | Signal | Result | Live / backtest | Relevance |
|---|---|---|---|---|---|---|
| Project 3i, `README.md` §82 | 200 most-traded; ranks 201–400 | 2010–25; 2026 held-out | Vol-adjusted 6/12-month momentum, 15 names | +0.82%/month (t 2.91); +1.00% (t 3.31); 2026 +1.28%. Net, long-only | Backtest + 8 held-out months | The only net, clean-data evidence; already reaches mid-caps |
| Agarwalla, Jacob & Varma, [IIMA WP](https://faculty.iima.ac.in/~iffm/Indian-Fama-French-Momentum/four-factors-India-90s-onwards-IIM-WP-Version.pdf), Table 5 | All liquid listed, small vs big | 1994–2013 | 12-1 momentum × size | Winners: small 17.1%/yr, big 16.9%; SD 58% vs 46%. Losers: −3.5% vs −1.8%. Gross, value-weighted, survivorship-corrected | Backtest | The long-only leg earned nothing extra in small caps; the wider spread sat in losers a long-only book cannot short |
| Same authors, [Vikalpa 2017](https://journals.sagepub.com/doi/10.1177/0256090917733848) | Same | 1994–2017 | Factors | Momentum 17.3%/yr, worst drawdown 49%; size factor 0.36%/yr. Gross, long-short | Backtest | No size premium from simply going smaller |
| Raju, [SSRN 4453680](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4453680); numbers from a [secondary summary](https://factorlab.medium.com/the-impact-of-universe-selection-on-momentum-portfolio-returns-in-the-indian-equity-market-0a6e60a4f35b) | Top 200 to top 750 by market cap | 2004–23 | 12-1 momentum, 5–80 names | Top 200: 24.5%/yr, vol 25.8%, recovery 214 days. Top 750: 35.1%, vol 31.9%, recovery 914 days. Long-only; costs UNVERIFIED | Backtest | Wider raises return, risk and time under water. [Abstract](https://factorinvestor.substack.com/p/factor-investor-report-may-2023): concentrated books no better risk-adjusted |
| Raju, [SSRN 4687044](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4687044) | 200 / 500 / 750 | UNVERIFIED | Rebalance every 1, 2, 3, 6 months | Shorter intervals capture momentum better | Backtest | Supports monthly over NSE's semi-annual schedule |
| Raju & Chandrasekaran, [SSRN 3510433](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3510433) | NIFTY 100 | UNVERIFIED | Top decile, monthly | +10.7%/yr over index; turnover 32%/month | Backtest | Momentum exists in the largest tier too |
| Sharma, Subramaniam & Sehgal, [2021](https://journals.sagepub.com/doi/10.1177/0972150918811248) | NSE 500 | 2005–16 | Size, value, volume, momentum | Value and momentum explained by risk models; size and volume faded | Backtest | Contrary evidence; anomalies weaken over time |
| [Small-investor study](https://publishingindia.com/storage/PDFBrochures/3815.pdf) | CNX 500 | UNVERIFIED | Long-only momentum, 16 horizon pairs | Profitable net of costs only at short formation and holding periods | Backtest | One of few net, long-only Indian studies |
| NSE momentum indices (own calc; next table) | Large to micro | 2020–26 | Vol-adjusted 6/12-month momentum | Live excess from +3.4 to −5.8 pp/yr | **Live** | The central evidence |
| Live index funds, AMFI NAVs via [mfapi.in](https://api.mfapi.in/mf/150738) (own calc) | Mid, small | 2021–26 | Same | Momentum funds lag their own index by 0.5–1.5 pp/yr; plain parent index funds by about 0.2 | **Live, net** | Real running cost of momentum at fund scale; fund-of-fund layers included |
| Capitalmind Adaptive Momentum PMS, [APMI-sourced](https://www.altportfunds.com/investments/capitalmind-adaptive-momentum-pms/), [PMS Bazaar](https://pmsbazaar.com/AMC/Capitalmind-Financial-Services/PMS) | Multi-cap | Mar 2019–Jul 2026 | Momentum | 16.6%/yr since inception vs 12.7% Nifty 50 TRI; 5-year 6.2% vs 10.4%; 2-year −9.9% vs +0.1%. Net of fees | **Live**, provider-reported, [not SEBI-verified](https://www.capitalmind.in/portfolio-management-service/momentum) | Longest real-money record; five years behind benchmark |
| Wright Momentum [smallcase](https://wealth.moolaah.com/product_master/smallcase_stacks_detail_page?sc_id=WRTNM_0001) | Top 500 | Since launch | Momentum + low volatility | 31.1% CAGR shown; no benchmark or cost basis | **Self-reported** | Not usable as evidence |

### NSE momentum indices by tier

All six score 6- and 12-month return adjusted for volatility, weight by free-float cap × score, and rebalance semi-annually in June and December; the three "Momentum Quality" indices add a quality score (ROE, leverage, earnings variability). All except the Nifty200 version exclude non-F&O stocks that hit a circuit on 20% or more of sessions in six months; all except the Nifty200 and mid-cap versions also drop promoter pledges above 20% and the bottom tenth by turnover (factsheets linked below). Returns are total-return.

| Index (names from universe) | Launch | Backtest excess vs parent, Apr 2005 → launch | Live excess, launch month-end → 30 Jun / 31 Aug 2026 | Sep 2024 → Feb 2025, index vs parent | 2025 | 2026 to Aug |
|---|---|---|---|---|---|---|
| [Nifty200 Momentum 30](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Momentum30.pdf) (30 of 200) | 25 Aug 2020 | not computed | **+2.3 / +2.2 pp/yr** (6.0 y); last 5 years +0.6 | −28.8% vs −16.8% | −4.6% vs +9.6% | +1.2% vs −2.5% |
| [Midcap150 Momentum 50](https://www.niftyindices.com/Factsheet/Factsheet_NiftyMidcap150Momentum50.pdf) (50 of 150) | 16 Aug 2022 | +6.8 pp/yr | **−0.2 / −0.1** (4.0 y) | −24.1% vs −20.3% | −3.5% vs +6.0% | +6.0% vs +6.2% |
| [Nifty500 Momentum 50](https://www.niftyindices.com/Factsheet/FactsheetNifty500Momentum50.pdf) (50 of 500) | 4 Jun 2024 | not computed | **−7.4 / −5.8** (2.2 y) | −29.6% vs −17.7% | −7.6% vs +7.7% | +6.7% vs −1.0% |
| [Smallcap250 Momentum Quality 100](https://www.niftyindices.com/Factsheet/Factsheet_NiftySmallcap250MomentumQuality100.pdf) (100 of 250) | 21 Dec 2023 | +7.2 | **−5.0 / −3.9** (2.7 y); monthly excess t −2.0 | −27.0% vs −24.7% | −11.6% vs −5.5% | +11.8% vs +10.6% |
| [MidSmallcap400 Momentum Quality 100](https://www.niftyindices.com/Factsheet/Factsheet_NiftyMidSmallcap400MomentumQuality100.pdf) (100 of 400) | 8 Feb 2024 | +6.1 | **−2.8 / −2.2** (2.5 y) | −24.8% vs −21.9% | −6.8% vs +1.8% | +11.1% vs +7.6% |
| [Total Market Momentum Quality 50](https://www.niftyindices.com/Factsheet/Factsheet_NiftyTotalMarketMomentumQuality50.pdf) (50 of 750) | 6 Aug 2025 | +6.7 | **+3.4** (1.0 y) | pre-launch | pre-launch | +9.7% vs −0.3% |

Sources: factsheets above and parents' ([200](https://www.niftyindices.com/Factsheet/ind_nifty_200.pdf), [Midcap 150](https://www.niftyindices.com/Factsheet/ind_nifty_midcap_150.pdf), [500](https://www.niftyindices.com/Factsheet/ind_nifty_500.pdf), [Smallcap 250](https://www.niftyindices.com/Factsheet/ind_nifty_smallcap_250.pdf), [MidSmallcap 400](https://www.niftyindices.com/Factsheet/ind_nifty_midsmallcap_400.pdf), [Total Market](https://www.niftyindices.com/Factsheet/Factsheet_NiftyTotalMarket.pdf)), dated 31 Aug 2026; monthly dashboards such as [June 2026](https://www.niftyindices.com/Index_Dashboard/Index_Dashboard_JUN2026.pdf). Chained monthly returns reconcile to NSE's own 1- and 3-year figures within 0.02 pp through June 2026; the July–August leg disagrees with factsheet 1-year figures by up to 0.5 pp. Backtest excess is implied from since-inception returns, so treat it as ±0.3 pp/yr.

How to read it: every tier fell harder than its parent in the 2024–25 slump, as the project's own rule did (−13% and −14% in 2025). These indices hold 50–100 names, cap-weight and rebalance twice a year, so they are relatives of the project's 15-name monthly rule, not replicas.

### Signals for the wider universe

**Worth a pre-registered test, in order:**

1. **The unchanged 3i rule on ranks 401–600, then 601–800**, as a confirmation like L38. Why: it is the direct answer to the owner's question and changes no rule. Data: in hand (bhavcopies, corporate actions). Two notes: slippage must be fixed above Part B's 0.10% a side before returns are read, and the entry-timing sweep earmarked ranks 401–600 as the unseen sample for a later trial, so the owner must choose which use spends it.
2. **NSE-style tradability screens as part of the universe definition beyond rank 400** (circuit-hit share, turnover floor, one year listed). Why: NSE applies them exactly where operator risk starts. Data: bhavcopy price bands and traded value; the pledge screen needs shareholding filings.
3. **A value composite** (earnings, book and dividend yield) in the top 400–500. Why: value averaged 15.3%/yr in the IIMA data, and the live [Nifty500 Value 50](https://www.niftyindices.com/Factsheet/FactsheetNifty500Value50.pdf) shows 25.8%/yr over five years against 11.1% for its parent; the §85 ranker had dividend yield only. Caveats: that run coincides with one re-rating of cheap sectors, and Sharma et al. found value explained by risk. Data: point-in-time fundamentals from NSE filings, built so far only for the NIFTY 100 (§84).
4. **Low volatility as a separate sleeve.** Why: [Peswani & Joshipura](https://businessperspectives.org/images/pdf/applications/publishing/templates/article/assets/12360/IMFI_2019_03_Peswani.pdf) find the effect in every size bucket, strongest risk-adjusted in large caps. Low priority: §85 already used volatility and beta as inputs, and that tilt cost return in 2019–25. Data: in hand.

**Skip:**

- **Quality (ROE, leverage):** the long-only backtest alpha of [0.69%/month](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4284686) has not shown up live; [Smallcap250 Quality 50](https://www.niftyindices.com/Factsheet/Factsheet_NiftySmallcap250Quality50.pdf) trails its parent by 6.0 pp/yr since June 2023 (own calc), and a [2026 study](https://exa.ai/library/publication/vvjsc4tpbw1) reports a negative post-COVID effect (abstract only).
- **Momentum-plus-quality blends:** the live index record above is the test, and it is negative in both small-cap tiers.
- **52-week-high proximity:** already a §85 input; [international evidence](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1364566) finds profits mostly insignificant after costs, and an [Indian replication](https://quantpedia.com/an-analysis-of-52-weeks-high-effect-on-indian-stocks/) was weak.
- **Size tilt alone:** the size factor earned about zero.
- **Earnings momentum:** closed by §84, no retries.
- **Reversal, beta, idiosyncratic volatility, liquidity, illiquidity, price:** tested in §85.
- **Micro-caps and SME listings:** no live evidence, and the failure modes below concentrate there.

### Breadth and concentration

Fifteen names from 200 is a 7.5% selection; NSE takes 7–40% of each universe. Keeping 15 names while widening to 800 means holding the top 2%, the most extreme winners and the likeliest operator stocks. Raju's abstract says concentrated books raise idiosyncratic risk without better risk-adjusted return. Rebalance-date luck is variance, not edge (`docs/research/entry-timing-sweep-2026-09-27.md`, Part B row 4). Any change in the number of holdings is a new configuration and raises the momentum family's count, so fix one value before data is read.

### Failure modes and guards

| Failure mode | Evidence | Guard |
|---|---|---|
| Operator-driven stocks, pump-and-dump | SEBI's May 2026 [interim order](https://www.sebi.gov.in/enforcement/orders/may-2026/interim-order-in-the-matter-of-trading-in-certain-scrips-through-stock-recommendations-given-on-social-media-platforms-ltd-_101597.html): 82 scrips pushed over Telegram, WhatsApp and X, ₹20.25 crore impounded ([ET](https://economictimes.indiatimes.com/markets/stocks/news/explained-modus-operandi-and-how-sebi-cracked-whip-in-alleged-pump-and-dump-scheme-involving-82-stocks/articleshow/131276202.cms)). A momentum rank puts a pumped stock first | Exclude names on a surveillance list at rebalance; apply the 20% circuit-hit screen; keep a traded-value floor |
| Stuck at circuit limits | The [surveillance framework](https://www.nseindia.com/static/regulations/enhanced-surveillance-measure-esm) covers companies under ₹1,000 crore with bands of [5% or 2%](https://economictimes.indiatimes.com/markets/stocks/news/bourses-include-companies-up-to-rs-1000-crore-m-cap-under-esm/articleshow/112416511.cms) | In the simulator, a close at the band limit is not a fill; count such days at stage 0 |
| Move to trade-for-trade | Surveillance moves a stock to the [BE series](https://www.nseindia.com/static/market-data/legend-of-series). The loaders read the EQ series only (`backend/research/nse_prices.py` line 60); a spell outside it leaves a gap (`docs/research/prereg-3h-slow-momentum-delivery.md`, amendment 1) | Load the other series for held names' exits; report gaps per rank band |
| Survivorship in vendor data | The IIMA authors correct for vanished companies | Keep NSE bhavcopies as the only price source; delisted names exit at the last close, as now |
| SME-board listings | SEBI found diverted proceeds and circular transactions ([Business Standard](https://www.business-standard.com/markets/news/sebi-considers-overhauling-sme-listing-regulations-amid-rising-concerns-124111901210_1.html)) | Never eligible; SME shares trade in their [own series](https://www.nseindia.com/static/market-data/legend-of-series), so the EQ filter already excludes them |
| Backtest-to-live decay | +6–7 pp/yr backtested against −5.8 to +3.4 live | Judge width only on unseen ranks plus a forward paper sleeve with its own switch-off band |
| Costs | Momentum funds lag their index 0.5–1.5 pp/yr; project slippage is unmeasured (#66) | Measure spreads by rank band first; this spends no trial |

### Limits

- SSRN pages were blocked; Raju's papers were read as abstracts, and his universe numbers come from a secondary summary.
- APMI's own page did not render its table; the Capitalmind figures come from two aggregators that agree.
- Spreads for ranks above 400 are UNVERIFIED everywhere; no Indian study found here reports them.
- Reddit and GitHub were not searched: the web-search budget ran out and the Exa free tier rate-limited part-way.
- Short-term capital gains tax is not modelled in any source above.

---

## Part B — cost, tradability and honest-fill rules

Sweep date 2026-09-28. Read-only on the repo. "Own calc" means a throwaway script (`docs/research/data/stock-picking-sweep/tiers_2025_descriptive.py`) that read only `backend/data/bhav_daily/2025*.zip` (before the held-out start, `backend/research/splits.py:30`) for liquidity, lock and spread statistics; no strategy return was computed.

### Bottom line

A Rs 1-10 lakh delivery book can trade honestly down to about **rank 800-1,000 by median daily traded value** (Rs 3-6 crore a day in H2 2025), where a Rs 70,000 order is about 0.2% of a day's turnover. Size is never the constraint at this capital; **spread, price-band locks and surveillance moves to trade-for-trade are**. My judgement for per-leg slippage on closing-window fills of small orders: **5 bp (ranks 1-200), 15 bp (201-400), 25 bp (401-600), 40 bp (601-1,000), 75 bp (1,001-1,500), exclude beyond 1,500**. These are judgements, not measurements: the only tiered order-book evidence found is from 2010, and daily-data spread estimators proved too noisy to set levels. At 273% one-sided turnover, which is Part B's (the running book's is 213%; `docs/research/results-3i-momentum-corrected-data.md`), every extra 10 bp per leg costs about 0.55% a year, so 75 bp per leg is roughly 4% a year. "All stocks" is not honest: below rank 1,500 about 13% of stock-days have no trade and half the names spent part of 2025 in trade-for-trade.

### Table 1. Cost by tier

Tier = rank by 126-session median traded value, price >= Rs 20, EQ series, close to how `momentum_3i.py:87` ranks. The script applies no 250-session rule and does not chain symbol changes. 1,892 names qualified on 2025-12-31.

| Tier | Daily traded value, H2 2025 (own calc) | Spread / impact evidence | Per-leg slippage, base / stress (bp) | Source | Confidence |
| --- | --- | --- | --- | --- | --- |
| 1-200 | Rs 77-1,630 cr | Largest market-cap decile, Rs 1 lakh round trip 0.18% in 2010, so ~9 bp a leg | 5 / 10 | [Shah 2010](https://www.mayin.org/ajayshah/MEDIA/2010/ownership_and_liq.html); repo `slow_momentum.py:69` | Medium |
| 201-400 | Rs 24-77 cr | 2010 deciles 8-9: 0.30-0.56% round trip, 15-28 bp a leg | 15 / 30 | Shah 2010 | Medium-low |
| 401-600 | Rs 11.5-24 cr | 2010 deciles 6-7: 0.64-0.90%, 32-45 bp a leg | 25 / 50 | Shah 2010 | Low |
| 601-1,000 | Rs 3.0-11.5 cr | 2010 deciles 3-5: 1.24-3.06%, 62-153 bp a leg; index ceiling is average impact cost <= 1% | 40 / 80 | Shah 2010; [NSE methodology](https://archives.nseindia.com/content/indices/Method_NIFTY_Equity_Indices.pdf) | Low |
| 1,001-1,500 | Rs 0.2-3.0 cr | 2010 decile 2: 5.84% round trip, ~290 bp a leg | 75 / 150 | Shah 2010 | Low |
| 1,501+ | under Rs 0.2 cr | 2010 smallest decile: a Rs 1 lakh order failed more than half the time | exclude | Shah 2010 | Medium (that it is untradable) |

Caveats. Shah's deciles are by market cap over 1,262 firms; mapping them to traded-value ranks is my approximation. Spreads have very likely narrowed since 2010: algorithmic trading lowered NSE spreads and impact cost ([Aggarwal and Thomas](https://ifrogs.org/PDF/2014ThomasAggarwal_atpaper.pdf)) and NSE cut the tick to 1 paisa for stocks under Rs 250 in June 2024 ([CNBC-TV18](https://www.cnbctv18.com/market/nse-lowers-tick-size-1-paisa-stocks-below-rs-250-from-june-10-bse-explainer-liquidity-19418016.htm)). The 2010 figures are therefore an upper bound and my base numbers sit below them. The repo's Part B used 10 bp for ranks 201-400 (`momentum_3i.py:49`); I would raise it to 15.

### Table 2. What the repo's own 2025 bhavcopies show (own calc, H2 2025)

| Tier | Rs 70k order as % of median daily value | Stock-days likely locked, up / down | Names locked at least once | Names seen in BE/BZ during 2025 | Median trades a day |
| --- | --- | --- | --- | --- | --- |
| 1-200 | 0.005% | 0.06% / 0.02% | 2% | 2% | 47,463 |
| 201-400 | 0.02% | 0.10% / 0.11% | 5.5% | 3.5% | 21,715 |
| 401-600 | 0.04% | 0.19% / 0.10% | 9% | 8.5% | 12,909 |
| 601-800 | 0.08% | 0.17% / 0.06% | 9% | 7% | 8,087 |
| 801-1,000 | 0.17% | 0.29% / 0.18% | 16.5% | 8% | 4,845 |
| 1,001-1,500 | 0.7% (3.5% at rank 1,500) | 0.52% / 0.23% | 19% | 24% | 1,572 |
| 1,501-1,892 | 16% | 1.95% / 1.43% | 45% | 52% | 274 |

Lock rule: close equals high (or low) and the return is within about 0.3% of +/-2, 5, 10 or 20%. Rates are unconditional; a momentum screen buys recent winners, so its upper-lock rate on buy days will be higher (not measured).

### Spread estimators from daily data

- Corwin-Schultz uses two-day high-low ranges ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1106193)); Abdi-Ranaldo adds the close and claims better accuracy in less liquid stocks ([RFS](https://ideas.repec.org/a/oup/rfinst/v30y2017i12p4437-4480..html)).
- Known biases: both go negative about half the time in liquid assets, and resetting negatives to zero changes the average ([Tremacoldi-Rossi and Irwin](https://scotthirwin.com/wp-content/uploads/2019/08/rossi_and_irwin_full_paper_feb_2019.pdf)); Roll, CS and AR are biased under infrequent trading, which the EDGE estimator addresses ([Ardia, Guidotti, Kroencke](https://sites.insead.edu/facultyresearch/research/file.cfm?fid=68847)).
- Emerging markets: across 21 markets the LOT measure tracked spreads best and Amihud tracked price impact best ([MDPI 2018](https://www.mdpi.com/2227-7099/6/4/67)); Fong, Holden and Trzcinka test daily proxies globally ([Review of Finance](https://revfin.org/what-are-the-best-liquidity-proxies-for-global-research/)).
- **Own test, negative result.** On H2 2025 data the tier medians of the full spread were CS 57 / 76 / 84 / 86 / 93 / 101 / 144 bp and AR 19 / 45 / 45 / 55 / 53 / 98 / 164 bp, top tier first. A 57 bp spread for the 200 most-traded stocks is not credible, and AR was zero for 43% of them. Use these estimators to rank stocks, not to set cost levels. India-specific trap: the bhavcopy CLOSE is a 30-minute VWAP, not a trade, so the estimators need the LAST column (I used it).

### Table 3. Tradability rules a backtest must apply

| Rule | Why | Detect from daily data | Source |
| --- | --- | --- | --- |
| No buy on an upper-band lock; no sell on a lower-band lock. Defer to the next unlocked session at that session's price | Bands are 2, 5, 10 or 20% either way; at the limit only one side has orders | Close = high (low) and return near a band level. Needs HIGH and LOW, which `nse_prices.py:48-68` does not parse | [NSE price bands](https://www.nseindia.com/static/products-services/equity-market-price-bands) |
| Treat F&O stocks as unbanded | No fixed band; a 10% operating range is flexed in 5% steps | F&O membership list by date (not in repo) | [NSE flex FAQ](https://www.nseindia.com/static/trade/price-band-operating-range-flex-faqs); [SEBI](https://www.sebi.gov.in/sebi_data/attachdocs/feb-2019/1549883290545.pdf) |
| Buy only EQ-series names; keep pricing and selling held names that move to BE/BZ | BE/BZ is trade-for-trade, compulsory delivery, which a CNC book can still trade. The loader drops those rows, so a held name shows a stale price | Series column. 611 symbols appeared in both EQ and BE/BZ during 2025 (own calc) | [NSE series legend](https://www.nseindia.com/static/market-data/legend-of-series); [Zerodha T2T](https://support.zerodha.com/category/trading-and-markets/trading-faqs/general/articles/what-are-trade-to-trade-stocks) |
| Exclude GSM names | Stage I: 5% band; II: trade-for-trade plus 50% buyer deposit; III-IV: once-a-week trading. Zerodha blocks buys at stage 2 and above | BE series catches stage II+; stage I is not visible in a bhavcopy | [NSE GSM](https://www.nseindia.com/static/regulations/graded-surveillance-measure); [Zerodha](https://support.zerodha.com/category/trading-and-markets/trading-faqs/trading-categories-and-groups/articles/gsm-stage-2-and-above) |
| Exclude ESM names | Market cap under Rs 1,000 cr; stage I is trade-for-trade with a 5% or 2% band, stage II a 2% band under periodic call auction. Entry needs a large price rise, which is what momentum selects | BE series plus a narrow band | [NSE ESM FAQ](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/FAQs%20-%20Enhanced%20Surveillance%20Measure%20%28ESM%29_25.7.2025.pdf) |
| ASM: allow margin-only stages, exclude long-term stage IV | Stage I is 100% margin, irrelevant to a fully paid book; II-III cut the band a level each; IV is gross settlement with a 5% band. Short-term ASM is margin only | Not in the bhavcopy; a narrower band shows up as locks at smaller moves | [NSE ASM FAQ](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/FAQs%20-%20Additional%20Surveillance%20Measure%20%28ASM%29_1.pdf) |
| Exclude SME series SM, ST, SZ | Lot trading: every SM/ST row on 2025-12-31 had a lot above 1, median lot value Rs 88,800 (SM) | Series, or `NewBrdLotQty` > 1 | Own calc; NSE series legend |
| Exclude IPOs and relistings for 250 sessions | First day uses a special call auction with a wide range; some names then trade trade-for-trade for 10 days | First appearance date; `MIN_HISTORY = 250` already does this | [NSE special pre-open](https://www.nseindia.com/static/products-services/equity-market-special-pre-open-session); [NSE T2T review](https://www.nseindia.com/static/regulations/movement-securities-periodic-review) |
| No fill when the stock did not trade; cap the order at 1% of median daily value | 13% of stock-days beyond rank 1,500 have no trade | Missing row or zero trades | Own calc |
| Treat the close as a target, not a fill | Non-F&O close is a VWAP of the last 30 minutes; F&O stocks close by auction since 2026-08-03, 15:15-15:35, within 3% of a reference price | F&O membership by date | [SEBI circular](https://www.sebi.gov.in/sebi_data/attachdocs/jan-2026/1768576287344.pdf); [NSE CAS](https://www.nseindia.com/static/products-services/closing-auction-session); [Zerodha](https://support.zerodha.com/category/trading-and-markets/trading-faqs/market-sessions/articles/closing-auction-session) |

**Executing the rebalance.** The signal is fixed at the month-end close and the fill is the next session's close (`momentum_3i.py:177`), so there is a full day to work the order. For non-F&O names, slicing limit orders through 15:00-15:30 tracks the VWAP that becomes the close; the cost is about half the spread plus noise, which is what the per-leg figures stand for. In a name with a few hundred trades a day the window may hold a handful of trades, so the printed close is not a price available in size.

### Recommended floor and exclusion list

1. **Floor: within the top 800 by 126-session median traded value**, loosest defensible 1,000. Use rank, not a rupee figure, because Rs 5 crore in 2025 is far deeper in the list than in 2010. NSE itself stops at rank 800 on turnover and market cap for the NIFTY 500 and at 1,000 for the Microcap 250 (NSE methodology).
2. **Traded on at least 95% of the last 126 sessions.** NSE asks 90% for the NIFTY 500.
3. **EQ series on every one of the last 60 sessions.**
4. **Price >= Rs 20 and 250 sessions of history** (already in `momentum_3i.py:42-43`).
5. **Exclude:** BE, BZ, SM, ST, SZ; GSM and ESM names; long-term ASM stage IV; ETFs and fund units; any name locked at a band on the rebalance day (defer).
6. **Minimum position about Rs 15,000.** The Rs 15.34 DP charge is 22 bp of a Rs 7,000 sale (`slow_momentum.py:70`).
7. **Report every result at base and stress slippage.**

Correction to the brief: the 0.50% impact-cost test at a Rs 10 crore basket is the NIFTY 50 rule. NIFTY 500 and Microcap 250 members need average impact cost of 1% or less (NSE methodology).

Fund stress tests (March 2024) do not bind here: SBI's Rs 25,500 crore small-cap fund needed 60 days to sell half at 10% participation, funds under Rs 5,000 crore under five ([Business Standard](https://www.business-standard.com/markets/news/stress-test-underscore-liquidity-risk-in-small-cap-investing-124031500993_1.html)). A Rs 10 lakh book is far below that scale.

### Data hazards in bhavcopies for small names

| Hazard | Check |
| --- | --- |
| Series migration EQ to BE and back leaves gaps and stale prices in an EQ-only loader | Load BE/BZ rows for pricing; flag any held name with no EQ row |
| Splits, bonuses, rights, demergers; PREVCLOSE is not adjusted (`slow_momentum.py:72`) | Compare close/PREVCLOSE against the corporate-actions file; list one-day moves beyond 30% |
| Symbol changes | `symbolchange.csv` chains (`nse_prices.py:72`); confirm with ISIN |
| Suspension and relisting: the first day back has a very wide range | Any gap over 5 sessions: freeze the position, exit at the first traded price, exclude re-entry for 250 sessions |
| Delisting: the series just ends, and the last close overstates what a holder got in insolvency cases | For a name whose last rows were BE/BZ, apply a haircut (judgement) and report the count |
| Survivorship: `EQUITY_L.csv` lists only current names | Build the universe from bhavcopies by date, as the repo does |

### UNVERIFIED

- Current NSE-published impact cost for any index. None was found with a figure; NSE publishes a NIFTY 50 figure monthly for a Rs 50 lakh basket (Aggarwal and Thomas), not by tier.
- The basket size behind the 1% impact-cost rule.
- Any validation of CS, AR or EDGE against NSE order-book data. The MDPI study's country list was not checked for India.
- Whether the post-close session fills at the closing price with usable depth in small names, and which stocks enter the pre-open auction.
- Historical ASM, GSM and ESM membership. The daily REG_IND file dates from January 2024 ([NSE circular](https://nsearchives.nseindia.com/content/circulars/SURV64402.pdf)); whether NSE serves past dates was not tested. Earlier history would need the circulars.
- A historical F&O membership list and historical price band per stock.
- SME lot rules from an NSE document; the lot evidence is from one bhavcopy.
- How often a momentum buy lands on an upper-band lock, and the effect of stale BE prices on the 3i results. Neither was measured.
- Practitioner floors. The write-ups found were unsourced; one claims momentum returns in the NIFTY 200 sit in the less-traded half ([freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)), not reproduced.

Tool note: Exa was rate-limited and the WebSearch budget was already spent, so academic coverage of Indian spreads is thin.
