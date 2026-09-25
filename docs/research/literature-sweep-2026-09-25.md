# Literature sweep, 2026-09-25 — what is documented to make money for a small retail account, and what isn't

**Why this exists.** The user asked, after 117 failed intraday trials, to
"research what would give profits — crypto, Sensex, buy/sell — and rewire
the whole process; research Reddit, GitHub, blogs, everywhere". This file is
that research. It was done by four independent sweeps (GitHub repositories;
academic papers and quant blogs; India-specific instrument costs, access and
tax; Reddit — the last only partially, see §4), each fetching primary pages rather than search snippets, and
it is written so the ranking can be audited. **It records no strategy trial
and spends no look.** The one test it motivates is pre-registered
separately: `prereg-3h-slow-momentum-delivery.md`.

**Headline.** Every sweep, independently, lands where the project's own
measurements already were: **no source documents net-of-cost profit from
intraday equity or index trading for a retail account — not in India, not
anywhere, not in open source, not in the literature.** What *is* documented
net of costs holds for **weeks to months**, in delivery or in derivatives
carry, and every such result carries its author's own overfitting caveat.
The "secrets" are structural, well known, and slow: low turnover, liquid
names, holding overnight, and paying the round trip a dozen times a year
instead of a few hundred.

---

## 1. Open source — what popular repos actually show (sweep 1)

Fetched: the repos' own READMEs, docs, issues and result pages.

| Family | Best-known repos | Documented live or out-of-sample net profit? |
| --- | --- | --- |
| Indicator / hyperopt crypto bots | freqtrade + freqtrade-strategies (5.5k★), NostalgiaForInfinity | **No.** freqtrade's own docs: "most public strategies are not good performers"; issue #3930 backtested 18 public strategies, all −100% to −2000%. Maintainer: "not a magic money machine". |
| Market making, grid, funding arb tooling | hummingbot (20k★) | **No P&L published**, only "$34bn volume". Funding-arb script exists; no returns. |
| Engines and tutorials | backtrader, backtesting.py, QuantConnect Lean, jesse | Frameworks; the shipped demos lose to buy-and-hold (backtesting.py's SMA-cross 589% vs 703% B&H). QuantConnect's Overnight Anomaly write-up: "returns are canceled out once transaction costs are taken into account". |
| ML alpha pipelines | microsoft/qlib, stefan-jansen ML4T | qlib: CSI300 LightGBM IR 2.00 gross → **1.44 with cost, backtest only, no live record**. ML4T: no numeric OOS results. |
| Curated lists | awesome-quant, awesome-systematic-trading | The latter's own statistic on 4,843 coded papers: **"median replication Sharpe 0.37; 48% clear t = 1.96"** — half the published record is indistinguishable from zero. |
| **Indian intraday** (ORB, EMA/Supertrend, VWAP reversion, 09:20 straddles) | md0n-cmd/indian-equity-backtests, nifty-banknifty-intraday-trend-algo, vijaxx, buzzsubash, Chinmaec, umeshpalai | **The two repos that model full statutory costs and test out of sample both fail.** ORB on NIFTY 100 2021–25: −21.8%, gross ₹173 on 759 trades vs ₹2,357 costs. Intraday momentum: 1.5 bp captured vs ~20 bp cost. Trend algo: gross ₹58k → **net ₹1,652**; at 4 bp slippage net −₹28.6k — "your real slippage decides, not the parameters." Option-selling bots ship **no backtests**; one README warns 90% lose. |
| **Indian slow factor / allocation** | md0n-cmd (Dual Momentum, Turn-of-Month), MARK5, Nifty-Quant, india-factor-backtest | md0n-cmd: Dual Momentum **12.1% vs 9.2% (2008–26), held-out 15.4% vs 10.1%**, full costs. MARK5: net 21.8% vs Nifty TRI 10.95% but the author discloses **PBO 42% (fails its own <20% bar)** and a 15-day live record. Others are gross or in-sample. |
| Crypto funding carry | zwmjj/funding-rate-arb (walk-forward, 16 bp RT) | **Positive but decayed**: BTC 9.0%/ETH 11.4% gross annual 2020–26, MDD < 2%, but **79–82% of P&L from pre-2022 entries, no trade since Dec 2024, 2025 ≈ 4% — below the cost of capital.** "A 100% win rate is a warning label." |
| Cross-sectional momentum replications | ahish-avg (CRSP, 23.7k stocks), triasha72, asoracca | 12-1 alpha **fails** in full CRSP 1990–2025 (t −0.72); 6-1 nets 0.62%/mo (t 2.60), positive across 0–50 bp costs. Small-universe replications ≈ 0. |
| Overnight-hold effect | alimuqeem/overnight-intraday-edge (33 US large caps, 1962–2026) | Effect real (26/30 survive FDR) but **median break-even cost 4.2 bp**; best cases tolerate 13–15 bp. Our cash round trip is 16.6 bp. |

**Reading.** The open-source record contradicts nothing this project
measured. Where costs are modelled and the test is out of sample, NSE
intraday loses; the positives hold for months.

---

## 2. Papers and quant blogs (sweep 2)

Full text read where not paywalled (Novy-Marx–Velikov, Lou–Polk–Skouras,
Frazzini–Israel–Moskowitz, SEBI releases, NSE factsheet, Zerodha posts).
SSRN/Elsevier/Wiley/Alpha Architect were bot-walled: **snippet-only, so
their numbers are "as reported"**.

**Cost is the binding variable, and the literature has measured where it
binds.** Novy-Marx & Velikov (RFS 2016, US 1963–2012): anomalies with
< 50% one-sided monthly turnover mostly survive costs; the high-turnover
panel (≈ 90%/month) nets **−0.3 to −1.3% per month**; only 2 of 23
high-turnover strategies survive, and only after stacking hysteresis,
low-cost universe and staggered rebalancing — at which point they are
monthly strategies. Momentum at ~35%/month turnover nets **+0.68%/month
(t 2.45)**. AQR's live-trade study (Frazzini et al., 19 markets) puts
short-term reversal's break-even capacity below $9bn while momentum's is
$52bn.

**Overnight vs intraday.** Lou–Polk–Skouras (JFE 2019): all momentum-family
profits accrue **overnight**; intraday winners lose overnight and vice
versa. Kelly & Clark: QQQQ 1999–2006 close-to-open +23.7%/yr vs
open-to-close −23.3%. Zerodha's own post shows the Nifty pattern turning
consistently positive-overnight/negative-intraday from 2011 (pre-open
auction). **This is the one effect the project replicated on NSE.** Every
net test of trading it in cash fails (Alpha Architect: SPY overnight-only
becomes noise after spread + commission); the literature says test it in
**futures**, where a round trip is 2–6 bp — an instrument out of reach
below roughly ₹1.7 lakh margin per lot.

**Momentum in India.** Chui et al. (PBFJ 2023, BSE 2000–2021, 3,956
stocks): significant intermediate momentum, strongest in the **most liquid
tercile**, reversing in illiquid names — **gross, no cost or turnover
figures.** NSE runs a live index on it (NIFTY200 Momentum 30): 5-year
11.0% CAGR to Aug 2026, 1-year 6.4%, in a 2024–25 drawdown longer than its
parent's. SSRN claims of Sharpe 1.7–3 on Indian momentum are unrefereed
and treated as overfit. **No India-specific long-only net-of-cost effect
size exists in the literature.** That gap is exactly what 3h measures.

**Option selling / variance premium.** Pillai (SSRN, Nifty monthly
2015–2025, with STT, brokerage and slippage): ATM straddle, put-write,
delta-hedged straddle **all negative net; straddles ≈ −44%/yr on margin**.
SEBI's Sept-2024 study: **93% of 1.13 crore F&O individuals lost
FY22–24, ₹1.81 lakh crore in aggregate; only 1% earned > ₹1 lakh after
costs**; FY25 update: 91% lost, ₹1.06 lakh crore. Since then STT on options
has risen twice (0.0625% → 0.1% → 0.15% of premium), weeklies are one per
exchange, expiry-day shorts carry +2% ELM, and options turnover has fallen
by half. The premium exists in implied-vs-realised; retail cannot collect it
at this microstructure.

**PEAD in India.** Nifty 500 2002–2017, SUE deciles: top-minus-bottom
**+6% per quarter from day +2 to +64**, gross, low-tier journal, no
post-2017 replication. Our L36 result (results day sign predicts the gap,
+83 bp t 4.8; post-open drift ≈ 0) is consistent: Indian PEAD is a
multi-week drift starting day +2, not a day-0 trade. It is a candidate for
a later slow-horizon test, not for now.

**Crypto.** Funding carry: documented, low-vol, **decayed to ≈ 0 excess
over USD cash in 2025**. Time-series momentum: ~32%/yr gross 2020–25 at
15 bp in one study; cross-sectional dies; many portfolios liquidated.
Market making: no published retail profitability. For an Indian account the
tax regime dominates all of this (§3).

**Retail intraday, population evidence.** Barber–Lee–Liu–Odean (Taiwan
1992–2006): **1.6% of day traders profitable in an average year**; Chague
et al. (Brazil mini-index futures, 19,646 starters): **97% of those
persisting > 300 days lose**, no learning curve; SEBI (Jul 2024, cash
intraday FY23): **71% lose; 80% among those trading > 500 times a year;
loss-makers paid an extra 57% of their losses in costs.** No published
study anywhere shows a retail intraday equity strategy beating costs.

---

## 3. India: instruments, costs, access, tax (sweep 3)

Verified against Zerodha's tariff page (already reflecting the 1 Apr 2026
STT hike), Kite's public instruments dump (111,802 rows; NSE, BSE, NFO,
BFO, CDS, MCX present), Kite's public margin JSON (stale snapshot; scaled),
SEBI circulars and FIU-IND's registry. Index levels 24 Sep 2026: Nifty
23,129, Sensex 73,847.

| Instrument | All-in round trip | Minimum capital, one unit | Horizon it suits | Kite | Tax |
| --- | --- | --- | --- | --- | --- |
| **NSE cash delivery** (₹50k trade) | **~25 bp charges** (STT 20 bp of it) + slippage; fixed regardless of hold | any | multi-day to months; punitive for 1–2 day churn | Yes (CNC) | STCG 20% < 12m; LTCG 12.5% |
| NSE cash intraday | 16.6 bp with slippage | any | — | Yes (MIS) | business income |
| Nifty futures (lot 65, ₹15 L) | **6.0 bp** + ~6 bp per monthly roll | **≈ ₹1.7 L margin**; MIS = NRML, no intraday discount | days–weeks | Yes | business income |
| Sensex futures (lot 20, ₹14.8 L) | 5.5 bp | ≈ ₹1.6–1.8 L (unverified for BFO) | days–weeks | Yes | business income |
| Nifty weekly option, short 1 lot | ₹70 ≈ 72 bp of premium at ₹150 | ≈ ₹1.25–1.5 L + 2% ELM on expiry Tuesday | intraday–1 week | Yes | business income |
| MCX crude mini / natgas mini | 7–8 bp | ₹28–31k / ₹10–12k margin (elevated now) | hours–days, to 23:30 | Yes | business income |
| MCX gold mini | 2.0 bp | ≈ ₹1.57 L | days–weeks | Yes | business income |
| Crypto spot (CoinDCX et al.) | 47 bp fees **+ 100 bp TDS withheld on every sale** | any | — | No | **30% + cess, no loss set-off, no carry-forward** |
| Delta Exchange India perps | 11.8 bp taker / 4.7 bp maker | tiny (0.001 BTC contracts) | hours–days | No | exchange *claims* no TDS/30% on F&O; **no CBDT ruling** |

**What this settles.**

- **At the real balance (₹5,500)** the only executable instruments are cash
  intraday (16.6 bp, measured no edge) and cash delivery — where the flat
  ₹18.10 DP charge per sell makes a 15-stock book cost ~500 bp per round
  trip. **A stock-picking book is not executable at ₹5,500.** The
  executable form of any slow-equity idea at that size is an **ETF**
  (STT 0.001%, no DP-per-name problem).
- **At ₹1 lakh (paper)** delivery costs ~59 bp per round trip on ₹6,667
  positions. Paid monthly on part of the book that is ~1%/yr; paid daily it
  is ~150%/yr. Horizon, not signal, sets whether this is survivable.
- **Futures need ₹1.7 L per lot plus MTM room**; a ₹3 L account carries
  one lot and nothing else. The overnight-premium test the literature
  recommends is therefore unreachable until capital is ~₹3–5 L.
- **Crypto is closed by tax mechanics, not law.** Daily turnover on ₹1 L
  locks ₹2.5 L a year in TDS receivable (refundable only after the ITR);
  losses on one coin cannot offset gains on another. Perps on Delta avoid
  the spot TDS but sit outside SEBI, outside Kite, and on an unsettled tax
  claim. A funding-carry trade needs a taxed spot leg, so the asymmetry
  kills it.
- **Option selling is capital-feasible at ₹1.5 L and the population
  evidence is one-sided against it** (§2).
- **MCX minis are the cheapest reachable leveraged instruments** (₹10–31k
  margin, 7–8 bp) and Kite supports them — but no documented effect exists
  to test there (`phase3-scoping.md` §3 said the same). Opening that line
  means collecting data first, not pre-registering a strategy.

---

## 4. Reddit (sweep 4) — partial: 12 threads read in full, ~55 by title

Reddit blocks direct fetching; the sweep read full thread text through
archived captures for 12 threads (r/algotrading, r/IndianStreetBets) and has
titles and snippets only for about 55 more. **Every profit figure on Reddit
is a self-report; none is broker-verified.** The value of the sweep is the
base rates and the failure modes people describe, not the P&L claims.

**What the community's own numbers say.**

- The most-upvoted answer to "how much have your running algos made this
  year?" (r/algotrading, Dec 2024, 141 points) is *"the lack of clear
  answers is extremely telling"* (174 points). The runner-up: *"I lost 20%
  buying calls."* The one concrete positive was a stock market-maker
  running 800 trades a day whose business scaled only after commissions
  fell from 3.4 to 0.9 bp — cost, again, as the edge.
- *"450 systems tested, 425 led to nothing"* (r/algotrading, Aug 2024) —
  a self-reported base rate of about 5%, before any live decay.
- A survivorship demonstration with a hard number (r/algotrading, 2020,
  NorgateData): monthly top-10 momentum on the NASDAQ-100 shows **46%
  CAGR on today's constituents and 16.4% survivorship-free**, with the
  drawdown doubling. Any momentum backtest on a current index list is
  inflated by roughly this factor — which is why 3h uses daily bhavcopies
  (every stock that traded that day) rather than an index list.
- "Lessons from live testing" (r/algotrading, Jul 2024): a Binance
  TA-feature signal that "wasn't bad" was killed by fees; the ex-HFT reply
  *"the actual edge is low transaction costs"*; the rule of thumb *"if five
  minutes of slippage matters you're not in the position long enough."*
- Nine years of indicator strategies on crypto/FX by a data scientist with
  walk-forward tuning: *"worked for a couple of months then died…
  TA-indicator strategies just don't work consistently."*
- **India (r/IndianStreetBets).** The most-upvoted "this works" post is a
  Friday-3pm naked Nifty strangle at 5–6 delta claiming ~20%/yr; every
  experienced reply says the same thing: one gap, one circuit, and the
  year is gone (*"seven winning weeks, then a crash took them all"*). A
  BankNifty 09:25 straddle "220% in 2.3 years" was a backtest whose
  ~₹120/day costs, once added, cut the net by roughly a third. An intraday
  pivot/EMA/RSI algo posted after 3–4 days drew the top replies *"every
  strategy works in a bull run"* and *"backtest 2–3 years."*
- The SEBI 93% figure, the ~₹26k/yr per-trader cost, and the 1% crypto
  TDS ("high-turnover crypto trading in India is structurally dead;
  volumes fell ~70% in July 2022") recur across the unread India threads'
  titles and snippets.

**Ranked by how consistently Reddit reports it as positive for retail:**
(1) low-turnover trend/momentum on daily or 4-hour bars across several
uncorrelated strategies — the only style with repeated, numerically stated
live results, all self-reported and mostly from the 2023–24 bull tape;
(2) structural near-arbitrage niches (funding carry, low-fee market
making) — capacity- and latency-limited, unverified; (3) far-OTM index
option selling in India — with the tail-loss objection from everyone who
has traded it for long; (4) cost minimisation itself; (5) buy-and-hold
index — not a strategy, but the benchmark the live algos in these threads
failed to beat.

**Ranked by how consistently it is reported as NOT working:** indicator
intraday (EMA/RSI/MACD/pivots); ML on price alone; grid and martingale
bots ("works until it doesn't"); short-horizon strategies whose backtest
ignores fees and slippage; backtests on current constituents, single-stock
fits, or bull-run-only samples.

Reddit adds no evidence that contradicts §1–§3; it adds the social base
rate (most people who try this lose, and the ones who don't answer) and one
number for the survivorship inflation the 3h data design avoids.

---

## 5. Ranking — edges with net-of-cost evidence for a small retail account

| # | Edge | Net evidence | Horizon | Instrument | Reachable at ₹5,500 / ₹1 L / ₹3 L | Status here |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Long-only momentum in liquid large/mid-caps, monthly-or-slower** | US net +0.68%/mo (t 2.45); India gross significant 2000–21; live NSE index 5y 11%; cost-aware Indian repos positive OOS | ≥ 1 month | Cash delivery (or the momentum ETF) | ETF / **yes** / yes | **Pre-registered as 3h, trial 118** |
| 2 | Overnight index premium, close→open | Replicated on Nifty since 2011 and in our data; US net result fragile | 1 night | **Nifty futures only** | no / no / one lot, marginal | Blocked by capital; revisit at ≥ ₹3–5 L |
| 3 | PEAD long-only, day +2 → +60 | India +6%/qtr L/S gross; US net t 1.6 | 1–3 months | Cash delivery | ETF-less; **yes** / yes | Candidate after 3h; needs post-2017 data (our results index thins after Jan 2025) |
| 4 | Crypto funding carry | Positive, low-vol, ≈ 0 excess since 2025 | weeks | spot + perp, offshore | tax-closed | Not pursued |
| 5 | Crypto time-series momentum | ~32%/yr gross in one study; CS dies | weekly–monthly | perps | tax-closed | Not pursued |
| 6 | Short Nifty variance premium | retail **net −44%/yr on margin** | monthly | index options | no / no / yes | Not pursued |
| 7 | **Intraday cash equity** | zero published survivors; 117 in-house trials at ≈ 0 pre-friction | — | — | — | **Retired as the product** |

---

## 6. What "rewire the whole process" means, given this

1. **The product changes horizon, not indicators.** An intraday scalper
   with a better entry rule is what 117 trials tested. The evidence-backed
   rewire is a **positional book**: delivery holdings, monthly rebalance,
   liquid large-caps, long only. This is pre-registered as 3h and runs
   today; it is built into the engine (paper mode) only if it passes its
   own gates. If it fails, this line closes too, and that is recorded.
2. **The real account is too small for stock selection.** At ₹5,500 the
   honest instrument for any slow-equity result is the ETF that already
   tracks it. The agent's value at that size is *not* trading.
3. **Crypto and Sensex are not the answer for this account.** Crypto is
   closed by the 30%/1%-TDS regime; Sensex and Nifty derivatives need
   ~₹1.7 L per lot before the cheap round trips (2–6 bp) exist. When
   capital reaches that level, the first test is the overnight premium in
   index futures, which is the one sub-day effect with replicated evidence
   here.
4. **Nothing above is a secret.** Every ranked item is in a refereed
   journal or an exchange's own index methodology. What separates the
   sources that report profit from those that don't is turnover and
   honesty about costs, not information.

## 7. Provenance and limits

- Four sweeps, 2026-09-25, each fetching primary pages. URLs are in the
  sweep reports summarised here; the ranking is mine.
- Snippet-only sources are marked; their numbers are as reported.
- The India cost table uses Zerodha's tariff as of 25 Sep 2026 and
  Kite's public instruments dump; futures margin percentages come from a
  stale public snapshot rescaled to today's notional (flagged).
- **No number here was produced by a backtest run today.** Trials of
  record remain 117 until 3h runs.
