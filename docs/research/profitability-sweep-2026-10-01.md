# Profitability sweep, 2026-10-01: how the project could make money, and what current technology does for an individual

**Written 2026-10-01, after midnight IST.** On 2026-09-30 the owner made the monthly momentum book the core of Trader Sahab and stopped the search for an intraday edge (PR #228). 202 trials and looks L40 to L51 had found none that pays the ~16.6 bp round trip. The owner then asked how to make the project profitable, from many sources and as deeply as possible, and how people use current technology to make money. Four research agents searched in parallel:

| Part | Scope | Report in `data/profitability-sweep/` |
| --- | --- | --- |
| R1 | India's momentum and factor evidence, live index products, costs, tax | `R1-india-momentum-evidence.md` |
| R2 | Improving momentum: literature, robustness, what is worth a trial | `R2-improving-momentum.md` |
| R3 | How people make money with AI, ML, automation and data, 2023–26 | `R3-tech-and-money.md` |
| R4 | Low-turnover strategy families for an individual in India | `R4-low-turnover-families.md` |

The reports are kept as written; §7 lists where they were wrong. Their raw notes and scripts stayed in the session scratchpad and were not kept, so R1's computations from NSE index data cannot be rerun from this repository. Reddit and X were read only through a search index, and three agents ran out of web-search budget.

**This reads published evidence; it tests nothing.** No trial or look is spent. One figure in §2 was computed here from trial 126's stored monthly series, already read; no new return.

**The book** means trial 126's rule as `backend/momentum_book.py` runs it. It ranks the 200 most-traded NSE EQ stocks (price ≥ ₹20) by volatility-adjusted 6- and 12-month return. It holds the top 15 equal-weighted, keeps a holding while it ranks ≤ 30, and rebalances monthly. The benchmark is the same 200, equal-weighted. Backtest 2010-02 to 2025-11: +0.71% a month net excess, sd 3.89%, t 2.51. It is not a NIFTY 100 book.

**Evidence grades.**
- **A**: regulator's data, law, audited accounts, or a live or out-of-sample record. R1's own computations from NSE and AMFI data count as A.
- **B**: one study, a backtest, a foreign result, or a self-reported figure.
- **C**: press, blogs, forums, marketing.

## Verdict

**The money current technology makes in markets is well documented, and most of it is out of an individual's reach: it goes to market makers and to firms with speed, capital and exchange access, much of it from individual F&O traders. No AI or machine-learning trading agent has a live record, net of costs, that beats holding the index by more than luck explains. What an individual can hold is a slow factor premium, and here that is the monthly momentum book. Its premium is real but much smaller live than in backtests: expect about +1 to +3 points a year over its equal-weighted benchmark after trading costs and before tax, with zero not ruled out. Tax, which no test has modelled, is the largest friction: the book needs about +2.3 to +2.8 points a year more than a harvested index fund just to tie after tax. On current evidence a Nifty200 Momentum 30 index fund is the better route for an individual, and the book must earn its place through measurements not yet made. Next come five measurements that spend no trial, then at most one or two trials, the first a tax-aware hold rule. This is a research finding, not investment advice.**

## 1. What makes money with current technology

**Who takes the profits** (SEBI, August 2026, https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787236407005.pdf and https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf; A):

| Group | FY26 |
| --- | --- |
| Prop firms and FPIs | Gross F&O profit about ₹44,000 cr and ₹14,000 cr; 99% from algorithms; the top 10 prop firms (2.3%) took 74.5% of prop profit |
| Individuals | Net loss ₹91,685 cr; 87.7% lost (90.9% in FY25); average net loss ₹1.17 lakh per trader, ₹1.47 lakh per loss-maker; ~₹25,000 cr a year in costs |
| Option sellers (~2% of traders) | Median return on peak margin +1% (FY25: −0.4%); a losing seller lost ₹39–52 lakh on average. Buyers' median −114% (FY25: −187%) |

Speed is winner-take-all. Latency races are about a fifth of FTSE 100 volume, and six firms win most of them (Aquilina, Budish and O'Neill, *QJE* 2022; A). XTX earns roughly 0.8 bp of volume by R3's arithmetic, against our 16.6 bp round trip. SEBI's interim order puts Jane Street's Indian net profit at ₹36,502 cr, 2023-01 to 2025-03 (A for the numbers; the allegations are not adjudicated). AI-branded funds lag: Eurekahedge's AI hedge-fund index made 9.8% a year against 13.7% for the S&P 500, 2009–24 (A/B).

**AI trading agents, tested:**

| Test | Result | Grade |
| --- | --- | --- |
| Alpha Arena S1: six LLMs, real $10k each, crypto, 18 Oct–3 Nov 2025 | Qwen3-Max +22%, DeepSeek +5%, the other four −30% to −63%. Random traders at the same leverage matched the winner about 10% of the time (https://magnusross.github.io/posts/nof1-analysis/) | A trades; C skill |
| Backtest → paper → real money, crypto (https://arxiv.org/abs/2609.34510) | No LLM agent profitable in the 2025 backtest. Real money, 24 Aug–21 Sep 2026: 1 of 4 finalists made money; none beat holding bitcoin (+11.6%) | A− |
| After the training cutoff (https://arxiv.org/abs/2510.07920) | Agents lose 51–62% of their Sharpe; the model recalls past market direction by date over 85% of the time | B |
| NSE, an LLM ranking NIFTY stocks for the next day (https://arxiv.org/abs/2511.08608) | No edge after costs over ridge regression | B |

The rest agree. With commissions over 2004–24 the LLM advantage vanishes (https://arxiv.org/abs/2505.07078). A user's rerun of TradingAgents lost 25.4% against 7.6% for buy-and-hold, and the repository keeps fixing look-ahead leaks. Across Quantopian's 888 algorithms, backtest Sharpe explained under 2.5% of live Sharpe (https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2745220).

**One backtest fits a monthly book.** Anic et al. (https://arxiv.org/abs/2510.26228) had GPT-4o-mini read news on each stock entering a long-only S&P 500 momentum book. Over 2024-01 to 2025-03, after the model's cutoff, Sharpe rose from 0.79 to 1.06, alpha 3.26% a year (p < 0.10), at 2 bp costs and about two-thirds more turnover (B). It is one US paper, not a live record; R3 expects far less at NSE costs.

**What technology is good for, for an individual:**
- **Cost and tax discipline:** hysteresis bands, sizing aware of the flat DP charge, lot-aware selling (§3).
- **Risk control:** frozen parameters and change logs. Two Sigma paid a $90m SEC penalty after one modeller changed 14 live models without approval (A).
- **Compliance** (§6).
- **Checking claims:** for example a pre-registered memory probe (B, unreviewed). It found the Jev book's model at 0.504, no recall of 2023–24 earnings outcomes; four frontier models scored 0.69–0.90.

It is not good for prediction.

## 2. Momentum is real, but weaker live and in large caps

Momentum replicates across markets, and outside the US it has not decayed after publication (https://doi.org/10.1111/jofi.13249, https://doi.org/10.1016/j.jfineco.2019.06.004; A). But live results lag backtests everywhere: bank strategies lost a median 73% of Sharpe going live (https://doi.org/10.3905/jpm.2017.43.2.090). In India:

| Evidence | Figure | Grade |
| --- | --- | --- |
| NSE factor indices, backtest → live excess over parent | A median of about 20% kept, across six indices live ≥ 6 years. Nifty200 Momentum 30: +6.1 → +1.7 points a year (73 months, t 0.64). The exception is Nifty Alpha 50: +5.1 → +7.2 (t 2.34). R1, from NSE TRI | A |
| Momentum 30 against Nifty100 Equal Weight TRI | Live 2020-09 to 2026-09: −0.01% a month, t −0.02. Over trial 126's window: +0.41% a month, about 58% of the book's excess | A |
| IIMA big stocks, long-only winners minus market (https://faculty.iima.ac.in/iffm/Indian-Fama-French-Momentum/) | 1994–2025: +0.57% a month (t 3.06, ~6.3% a year). After 2013: +0.25% (t 1.19, ~2.6% a year). Gross, value-weighted | A / B |
| Long-only share of long-short | About half: the top tercile earns 45–50% of the spread (JKP data); AQR's long side earned 5.5 of 10.6 points | A |

**Forward expectation: +1 to +3 points a year over an equal-weighted benchmark, after trading costs, before tax (R1).** The backtest's one-SE band is about ±3.4 points, so zero is inside. R2's planning figure, 0.3–0.5% a month (+3.6 to +6), is the optimistic end. The project's own checks were positive: unseen ranks 201–400 (L38, L42), and 2026 January to August at +1.28% a month, t 1.08. But they share the backtest's era, and eight months are weak evidence.

**The 2024–26 momentum drawdown is still open.** Momentum 30 TRI fell 31.6% from 2024-09-27 to 2025-04-07 and was still 21.5% down on 2026-09-30. Against the Nifty 200 it is 17.8% below its relative peak, the worst since 2007–13 (R1, A). The book's backtest trailed its benchmark by 13.0% in 2016 and 11.7% in 2025.

**The band would have switched off a book started in September 2024.** Over trial 126's stored series (`data/momentum_width_A.json`), 184 start months have at least six months after them. The band trips for exactly one, the September 2024 start: −15.2% at month 6 against a floor of −14.8%. An ordinary momentum drawdown can trip the band.

**Crowding.** Momentum 30's rebalances move about ₹16,000 cr, and in December 2025, 27 stocks needed more than a day's volume (https://www.business-standard.com/markets/news/nifty200-momentum30-a-flip-of-index-switch-jolts-16k-cr-across-the-grid-125121400388_1.html; C). That does not limit a ₹10 lakh book. It is a reason to avoid trading into the late-June and late-December closes.

## 3. Tax is the largest friction no test has modelled

**The rules** (A; https://www.indiabudget.gov.in/budget2024-25/doc/Budget_Speech.pdf, https://www.indiabudget.gov.in/doc/budget_speech.pdf):
- Gains on listed shares held 12 months or less are taxed at 20%; above that, 12.5% on gains over ₹1.25 lakh a year; 4% cess on both.
- Dividends are taxed at the slab rate. There is no wash-sale rule.
- The February 2026 budget changed neither rate.

The book turns over about 211% a year one way, with an average holding of about 5.6 months. Most gains are short-term. Its modelled trading costs are 0.69% a year; tax is several times that.

**Extra pre-tax return the book needs to tie a harvested index fund after tax** (R4's model, B):

| Capital | No harvesting | Harvesting ₹1.25 lakh a year |
| --- | --- | --- |
| ₹1 lakh | +2.26 points | +2.76 |
| ₹10 lakh | +1.64 | +2.33 |

R1's model gives +2.4 to +2.7. On backtest numbers the book's 20.6% becomes 16.3–16.7% after tax, against 11.6–12.0% for a harvested index fund. Tax takes about 40% of the edge.

**Against a momentum index fund.** A fund's internal trading is not taxed to its investor until redemption. Nifty200 Momentum 30 funds trail their index by 0.3–1.0 points a year; UTI's is the lowest (R1, from AMFI NAVs; A). Real investors in UTI's fund made 9.0% a year over five years, against 7.1% for the Nifty 100 TRI. R1's central case (B) assumes the market makes 12% pre-tax with 20% volatility:

| Route | After tax, a year |
| --- | --- |
| The book at +2 points over the market | 9.5–9.7% |
| Nifty 100 index fund | 10.0–10.2% |
| Momentum 30 index fund (live +1.7, less tracking) | 10.8–11.0% |

The book beats the momentum fund after tax only if its pre-tax edge over the market exceeds about **4 to 4.5 points a year**. The +1 to +3 in §2 is over the equal-weighted 200, not the cap-weighted market, so the two are not directly comparable; measurement (b) closes that gap. **On current evidence the momentum index fund is the better route for an individual; the book's after-tax edge over it is unproven and may be negative.** This is a research finding, not investment advice.

Two assumptions went unchecked:
- Frequent short-term trading could be taxed as business income (CBDT Circular 6/2016 was not fetched).
- Funds are assumed not to pass their gains through to investors (section 10(23D), renumbered in the Income-tax Act 2025; not fetched).

## 4. What to do next, in order

**Measurements that spend no trial:**

- **(a) After-tax replay of trial 126's trades** against a harvested index fund and the Momentum 30 fund, same months. It uses FIFO lots, set-off, carry-forward, the ₹1.25 lakh exemption, dividend tax and DP charges. It is being pre-registered separately as **look L53**; not designed here.
- **(b) Benchmark realism.**
  - Measure trial 126's 2020-09 to 2025-11 excess against the Momentum 30 TRI and the Nifty100 EW TRI. Their files are not in the repository yet.
  - Ask whether the band's expected +0.71% should be lower. That is the owner's decision, as on 2026-09-29. The floor is mostly the two-SE term: at +0.25% a month it would be −17.6% at six months (now −14.8%) and −24.0% at twelve (now −18.4%).
- **(c) Turnover-only diagnostics** for keep ranks 30/45/60 and 1-, 3- and 6-month rebalancing. Report turnover, holding periods and the share of sales that would be long-term. Compute no return. The literature finds monthly rebalancing fine. NSE's quarterly Momentum 30 beat its semi-annual version in only 6 of 20 years.
- **(d) Real fills and slippage from the paper book (#66).** Trial 126 fails at 0.07% slippage a side instead of 0.05%. The first rebalance is at the 2026-10-01 close.
- **(e) Correlation** of the book's monthly excess with IIMA's HML and WML, on the 2010–25 series already read.

R2 adds one for the owner to decide: **confirm the unchanged rule on 2002–09**, the only unread stretch of the momentum family's history. It needs a 2002–09 price and corporate-action build. It is partly seen at the index level (§9). It can be spent once: on the unchanged rule, or kept as one trial's primary sample.

**Then at most one or two trials.** The gate is strict: t ≥ 2.807 at the family of 10, and trial 126 itself is at 2.51. A new configuration needs a 13–17% higher information ratio. Paired tests over 190 months detect only about 0.4% a month (R2).

1. **Tax-aware hold rule.** R1's version: defer a sale that falls within about a month of the 12-month anniversary, while the holding ranks ≤ 45. R2's version: holdings aged 9–12 months stay while ranked ≤ 60, until day 366.
   - The tax saving's sign is known. The cost of holding a weaker stock for up to a month is not.
   - Priors (R2): ~45% on an after-tax rule fixed before data; under 10% on the pre-tax bar.
   - Likely size: +0.3 to +1 point a year after tax (C).
   - **Before any data, the owner fixes the judging rule and the family:** a new tax family, or momentum at N = 11.
2. **Only if the owner wants a second trial: a drawdown overlay, judged on a drawdown rule.** Move half the book to NIFTYBEES when momentum's volatility is in its top fifth, never leveraged, tested on 2002–09 first. The inputs disagree about it (§7). Priors (R2): 10–15% on excess, ~40% on a risk rule.

## 5. Every candidate

"Prior" is the agents' estimate of passing the project's gate. "Size" is after Indian costs and tax, where the evidence allows.

| Candidate | Grade | Realistic size | Prior | Decision |
| --- | --- | --- | --- | --- |
| Measurements (a)–(e) of §4 | A / own data | Tell whether the book beats the index-fund routes, and by how much | No gate | **Measure** (a is L53) |
| Tax-loss and ₹1.25 lakh gain harvesting | A (law) | Up to ~₹16,250 a year | Not a trial | **Measure** inside L53 |
| 2002–09 confirmation, unchanged rule | Own data, partly seen | Out-of-sample sign and size | Confirmation | **Owner decides** |
| Tax-aware hold rule | B; C for size | +0.3 to +1 point a year after tax | ~45% after-tax rule; <10% pre-tax bar | **Pre-register** once the owner fixes rule and family |
| Conditional volatility overlay, de-risk only | A (US long-short); B (long-only) | Long-only Sharpe ~unchanged (IIMA 0.56 → 0.57); smaller crash losses | 10–15%; ~40% on a risk rule | **Leave** unless the owner wants a drawdown trial |
| Bear-market filter | A (US); B/C (India) | None for long-only in India; fires rarely, missed 2024–25 | Low | **Leave** |
| Residual momentum; frog-in-the-pan tie-break | A (long-short); B/C (ours) | Risk-adjusted gain; long-only return unchanged; a live US fund gained nothing from frog-in-the-pan | ~10%; 5–8% | **Leave** (2026-09-27 sweep also rejected residual) |
| 52-week high, lookback grids, industry momentum, weighting, 30 names | A / B | Zero or below after costs | Low | **Leave** |
| Alpha 50-style signal (1-year Jensen alpha) | A (index live) | Alpha 50 +7.2 points a year live, relative drawdowns −29.9% and −20.1% | Not estimated; a signal swap needs +13–17% IR | **Leave**; its index fund is a product route |
| Restrict to NIFTY 100; widen to 400 | A; own trial 127 | Lower excess; failed | Low; spent | **Leave** |
| Low-vol sleeve, momentum × low-vol | A live; B backtest | Nifty100 Low Vol 30 +0.7 to +1.4 points a year live; ETF net t 0.36 | ~10%; 35–40% on a drawdown rule | **Leave** (risk reduction) |
| Dividend-yield sleeve; value; quality | A live, regime-bound | Div Opp 50 +3.8 points over five years (PSU re-rating), slab tax −0.5 to −0.9; HML ~0 in 2010–19; Quality 30 −1.44 live | 10–15%; low; not testable | **Leave** |
| Dual momentum NIFTYBEES/GOLDBEES/liquid; static Nifty–gold mix | B abroad; C India | ≤ +1 point after switch tax, drawdown −16% vs −47%, gold-driven; 0.5–0.75% diversification return | ~10%; ~35% do-no-harm | **Leave** (allocation, not excess); runnable at ₹5,500 |
| Buyback tender reserve | C | ≤ ₹2 lakh a company, 25–40 dates a year; tax changed April 2026 | ~20% | **Leave** (grade C, small) |
| Turn-of-month; pre-announcement; sector rotation | B | ~41 bp gross vs ~10 bp round trip, negative after tax; unknown; ≤ 0 | <5%; 5–10%; low | **Leave** |
| LLM news check on the book | B (one US backtest) | +3.26% a year at 2 bp in the US; possibly zero at NSE costs | Low | **Leave**; forward-only after a memory audit, if ever |
| Covered calls, put-writing | B | Lower return, higher volatility; business income; a lot (~₹15 lakh) exceeds the book | <5% after tax | **Leave** |
| Option buying, 0DTE, "sure-shot" selling, copy trading, smallcases, marketplaces | A / B | 87.7% of F&O traders lose; smallcases no alpha even gross (https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4344044) | None | **Leave** |
| LLM trading agents, AI funds, leaderboards | A / B | No net-of-cost live record (§1) | None | **Leave** |
| Pairs, overnight; market making, speed | Own (L23–L30, 124–125); A | ≤ 0; not available | ≤ 5%; none | **Leave** |
| Selling research (WorldQuant BRAIN, Numerai) | B / C | Income, not trading; Numerai's token taxed as crypto (30%) | n/a | **Leave** (outside the project) |

## 6. Defence

**SEBI's retail algo rules**: circular of 4 Feb 2025 (https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1738665456458.pdf), fully in force from **2026-04-01**. Kite's version: https://kite.trade/forum/discussion/15912/preparing-to-comply-with-sebis-retail-algo-rules-static-ip-ratelimits-order-types (A).

| Rule | Engine today |
| --- | --- |
| API orders only from a whitelisted static IP (up to two a key) | Not in place. The README requires one before going live. A static IP costs ~₹1,500 a year, or run on a VPS in India |
| MARKET and SL-M orders need non-zero market protection | Done: `kite_broker.py` sends 1% (`config.KITE_MARKET_PROTECTION_PCT`) |
| No registration under 10 orders a second | Fine: the book sends a handful a month |
| A self-written algo is for its author and immediate family only | Fine while it stays the owner's. Offering it to others needs NSE empanelment, and a black box needs a registered Research Analyst |
| OAuth and two-factor login; an algo ID per order; Kite Connect ₹500 a month a key | The daily login exists; the fee is a cost |

The momentum book places no order (`momentum_book.py` is paper only). Before any real order it needs the static IP, orders through the protected path, and the owner's separate decision on real money.

**Checking anyone who sells a strategy:**
- **PaRRVA**, SEBI's performance verification, has run from 4 May 2026 (https://www.sebi.gov.in/sebi_data/attachdocs/apr-2026/1777472194521.pdf). No verified record predates May 2026.
- **NSE's empanelled algo providers**: 15 names on 22 Sep 2026 (https://nsearchives.nseindia.com//web/mediaattachment/2026-09/ap_vendors_2026_20260922190839.xlsx).
- **SEBI's March 2026 order on Tradetron** concerned advertised fixed daily income; 111 brokers settled (https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/ORDER_1774439178.pdf).
- **Fraud patterns:** fake FPI and IPO WhatsApp groups, fake "AI prediction" software, influencer pump-and-dumps.
- **Red flags:** guaranteed returns; a free strategy with referrals; a black box from someone unregistered; a vendor not on NSE's list; any request for broker logins or Kite tokens; no PaRRVA record.

## 7. Where the inputs disagreed or were wrong

- **R3 calls the book a NIFTY 100 book.** Wrong: it ranks the 200 most-traded stocks (code; R2's correction).
- **R1 says the band's +0.82% looks too high.** Stale: the band has used +0.71% since 2026-09-29.
- **Volatility scaling.** R1 finds no long-only gain in Indian data. R2 and R3 rank an overlay second for crash protection. §4 keeps it only as an optional drawdown trial.
- **Forward expectation.** R1 says +1 to +3 points; R2 says 0.3–0.5% a month (+3.6 to +6).
- **Momentum 30's live excess over its parent.** R1 computes +1.7 points a year from launch. R2 cites ~+2.2 from launch and ~+1.0 over five years; the factsheet shows 9.28% against 8.30%.
- **Momentum fund tracking difference.** R4 says 0.67–1.01 points; R1's fund-by-fund range is 0.30–0.97.
- **R4 compares mismatched windows.** It sets the book's 2010–25 CAGR against a mostly-backtested Momentum 30 CAGR for 2010-02 to 2024-05 (~21.8%). Its "17.5% momentum fund" is an assumption.
- **Residual momentum.** R2 ranks it third; the 2026-09-27 sweep had rejected it.
- **JKP replication rate.** R2 cites 82.4%, R3 84%.
- **Tax drag.** R3's 1.5–3 points runs below R1 and R4's 2.3–2.8 with harvesting.
- **Two corrections to the main session's synthesis.**
  - One post-cutoff backtest did improve a US momentum book (§1), so "no post-cutoff record" needs that caveat. It is not a live record.
  - ₹1.17 lakh is the average net loss per trader, not per loss-maker.

## 8. What we could not verify

Merged from the four reports.

- **Tax:** CBDT Circular 6/2016; the fund pass-through section; US tax-aware momentum figures (Israel–Moskowitz, AQR). Every prior and tax-drag figure is an estimate.
- **Regulators and industry:**
  - the SEBI algo circular text (R1 could not fetch it; R3 cites it);
  - the SPIVA India report (403);
  - PMS returns and fees, smallcase fees, RA/IA fee caps, Capitalmind's PMS pages;
  - SEBI's 2024 IPO study, and any intraday cash study after FY23;
  - user P&L at Streak, AlgoTest, Quantiply, Sensibull, Dhan and Upstox;
  - Zerodha API user numbers;
  - whether the option-seller sample is representative.
- **Products:** momentum ETF TERs, spreads and iNAV premia; UTI's 0.89% TER; the Low Vol 30 and Value 50 launch dates (assumed); one garbled NSE whitepaper figure; Raju's rounded index file; ETF STT (inferred); stock lending at Zerodha.
- **Literature not retrieved or from memory:**
  - R1's McLean–Pontiff and Jacobs–Müller figures;
  - Patton–Weller; frog-in-the-pan break-even; Faber 2018; dual momentum after 2014;
  - Blitz–Hanauer–Vidojevic; Hanauer–Linhart; Cakici et al.; Chang et al.;
  - Raju's SSRN tables; SSRN 4163613;
  - MSCI's momentum risk control;
  - Shahu et al.; Aggarwal–Aggarwal; Kamath 2026; Raju–Teli's correlation;
  - whether McConnell–Xu and Barber include India;
  - Chen–Kelly–Xiu after costs; EAR-AI; InvestorBench, FinBen, CLQT.
- **Firms and contests:**
  - nof1's site (404); conflicting season-1 losses; season 1.5 rows;
  - ML P&L at Man, AQR and Bridgewater; Medallion after 2021; Numerai 2025;
  - Tower, Quadeye and NK profits;
  - Jane Street's final order (none by 4 Sep 2026);
  - XTX's margin (R3's arithmetic);
  - the memory audit (unreviewed).
- **Evidence gaps:**
  - no peer-reviewed Indian net-of-cost long-only momentum study, and none for residual or frog-in-the-pan;
  - no Indian net-of-cost news or earnings-call result;
  - practitioner figures are self-reported;
  - India's post-bear momentum needs a 2000–09 build;
  - buyback acceptance ratios come from press and Reddit;
  - no sourced account of value's 2010–19 drought;
  - trend-following power assumes 10–12% tracking error.

## 9. Held-out exposure

`HELD_OUT_START` is 2026-01-02. Every 2026 datum the agents reported reading, also logged in `trials.md`:

| Agent | 2026 data read | Statistic computed? |
| --- | --- | --- |
| R1 | NSE daily TRI for 16 Nifty indices (momentum, quality, low-vol, value, alpha, parents) to 2026-09-30 and their 2026-09-30 factsheets; AMFI NAVs of 43 funds through 2026-09; NSE's 2026 momentum whitepaper (to 2026-02-27); Motilal Oswal ETF document (May 2026); passive AUM at 2026-02-27; NSE methodology (June 2026); February 2026 Budget; Zerodha's tariff | **Yes**: index excess over parents and over Nifty100 EW through 2026-09; drawdowns to 2026-09-30; 2026 year-to-date; fund returns and tracking. No project strategy return |
| R2 | 2026-09-30 factsheets of Momentum 30, Alpha Low-Vol 30 and Quality 30; a point-in-time momentum × low-vol NIFTY 500 table 2014–26; five-year live figures to 2026-09-30 | Read as literature |
| R3 | SEBI's FY25–26 F&O studies (FY26 includes 2026-01 to 03); SEBI orders of March and May 2026; the PaRRVA circular; NSE's vendor list of 2026-09-22; Tradetron's August 2026 aggregate; India VIX in March 2026; the September 2026 F&O series (Nifty −6.7%); a forum trader's January–May 2026 account; arXiv 2609.34510 (crypto, August–September 2026); the September 2026 memory probe; GitHub stars at 2026-09-30 | Read as literature |
| R4 | 2026 rows of the Quality 30, Value 20, Dividend Opportunities 50 and Nifty 50 factsheets to 2026-09-30; GOLDBEES 2026 monthly prices; balanced-advantage fund pages (March and July 2026); an overnight/intraday repository to 2026-09-30 and another to May 2026; md0n's NIFTYBEES turn-of-month and dual-momentum results 2021–26; mfapi files with 2026 rows (filtered out); a count of 25 buyback rows in `corp_actions/ca_2026.csv`; two 2026 buyback articles | Dividend Opportunities 50's five-year excess read; no strategy return |
| This note | None; the band count uses 2010-03 to 2025-11 | — |

**Consequence.** A 2026 confirmation of any of these families is partly seen:
- momentum at the index level;
- low-vol, quality, value, dividend yield, alpha;
- dual momentum and gold;
- turn-of-month and overnight;
- buybacks.

Prefer forward confirmation. The book's own 2026 held-out statistic was already spent once (L38).

**2002–09 is partly seen too.** R1 read NSE momentum index history from 2005. R2 read the 2008 momentum crash and a split overlapping 2002–09. R4 read dual momentum from 2008. A 2002–09 confirmation must disclose this.
