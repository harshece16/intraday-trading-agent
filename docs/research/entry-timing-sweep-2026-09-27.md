# What should decide when to trade, now the Varsity checklist is retired? Sweep, 2026-09-27

The owner asked (2026-09-27) for research into a better way to decide *when*
to trade than Zerodha Varsity's Grand Checklist, which was measured (§51,
§69) and retired as the decision-maker (§75). Two read-only sweeps ran in
parallel: one on intraday entry timing, one on daily-to-monthly timing for
the delivery book. **No trial and no research look was spent**; no strategy
return was computed and no held-out data was read. The trial count stays 125.

## Bottom line

- **Intraday: nothing clears costs.** No published, practitioner or in-house
  source shows an intraday entry-timing rule for NSE cash equity above the
  14–17 bp round trip. Every credible figure is about 1–8 bp gross per trade.
  The one open line is the pre-registered order-book test (L37), which runs
  as written from 15 full sessions starting 2026-09-28; the literature
  expects it to fail (NSE order-flow predictability fades within 30 minutes,
  and every L37 horizon is 15 minutes or longer).
- **Positional: the leads are about how much momentum to hold, not new
  entry signals.** In order: (0) confirm the unchanged 3i rule on 2002–2009,
  years no test has read; (1) a volatility-scaled momentum overlay that
  moves part of the book into NIFTYBEES when momentum's own volatility is
  high; (2) promoter open-market purchases from SEBI insider-trading
  disclosures, as the one new daily-horizon signal.
- **Owner decision needed before (1) is pre-registered:** judge a risk
  overlay on alpha (the family bar, which the sweep's own power estimate
  says it will probably fail even if it cuts drawdowns as the literature
  says), or on a pre-set non-inferiority rule (return within 1 pp of the
  base in both samples and drawdown cut by at least 25%). The current rule
  says a pass on economics alone is a fail, so the second option would be a
  new owner decision, not a reading of the old one.
- **The cost model's slippage is unmeasured** (0.03% per leg, issue #66).
  At ₹2–3 lakh positions it is the largest part of the intraday hurdle, and
  measuring it from `liquidity_checks` and `depth_samples` spends no trial.

## Checked against the repo before this note was committed

- Trial 35 (opening-range breakout on relative volume): gross +4.52 bp,
  net −12.09 bp, t −2.71 (`results-3a-opening-range.md`).
- L32 (market intraday momentum): +0.70 bp, t 0.61 (`results-3b-stage1.md`).
- No timing, regime, trend-filter, volatility-scaling or rebalance-date
  idea appears among the 125 trials (`trials.md`).
- NSE corporate actions for 2000–2026 are cached in
  `backend/data/corp_actions/`; `load_corporate_actions` defaults to
  `first_year=2008`.
- Family bars match `decision-2026-09-26-overnight-and-significance.md`
  (N = 2 → t 2.24; N = 3 → 2.39; N = 5 → 2.58).

Not re-checked here, and labelled as such in the parts below: the NSE
insider-trading API count (1,646 disclosures for 1–15 Mar 2016), the
availability of 2000–2009 bhavcopies (two sample years returned HTTP 200),
the Reddit and vendor figures (self-reported), and the sweeps' own
back-of-envelope conversions.

# Part A — intraday entry timing

Research memo, 2026-09-27. Read-only on `~/Projects/webapp`. **No trial and no research look was spent.** The only data read: row counts in `depth_samples`, file headers of the bhavcopy folders, and two NIFTY 50 closing levels from 2025 (selection period) to check a vendor's claim. No strategy return was computed.

### Bottom line

**No published or practitioner source shows an intraday entry-timing rule for NSE cash equity that clears a 14–17 bp round trip, and neither does anything this project has measured.** Every credible figure for entry timing lands at roughly 1–8 bp gross per trade:

- The most-cited "profitable day trading" papers make their money on US costs of about 0.2–2 bp.
- The best Indian panel finds a real opening-range-breakout signal of +7.87 bp gross that nets −12.47 bp.
- NSE order-flow predictability fades within 30 minutes.

The checklist was not a bad choice among good ones. The whole class of price-timing rules sits below cost at this size.

The one evidence-backed intraday line is **the order-book test that is already pre-registered (L37)**. Its data has barely started: one partial session so far, and 15 full sessions are needed from 2026-09-28. It should run as written, and the literature expects it to fail.

If the owner wants exactly one more trial, the only candidate with a mechanism for a larger gross move is a **news-day "stocks in play" opening-range breakout**: trade only on results or filing days with extreme opening volume. Its prior is low. Before it spends a trial, a stage-0 count must show it can be powered, because it needs event data and minute bars this project does not yet hold.

The more useful cost-side step is to measure real slippage first. At ₹2–3 lakh per position, the assumed 6 bp slippage is more than half of the ~11–12 bp hurdle, and it has never been measured.

### 1. What this project has already settled (do not redo)

| Idea | Where tested | Result |
| --- | --- | --- |
| Varsity checklist | §51 (495 sessions), trials 36–39, §69 trials 41–44 | net −0.356R, t −3.59; pre-friction +0.042R (t 0.42); indistinguishable from random entries (`README.md` §51) |
| Trend pullback, range mean reversion, VWAP breakout on volume, on 5m/15m/60m | §69, trials 45–116 (`prereg-strategy-search.md`) | 0/76 with positive net R; every entry −0.05R to +0.04R before costs (`results-search-diagnostics.md`) |
| **Opening-range breakout, top-20 relative volume, NIFTY 100** | trial 35 (`results-3a-opening-range.md`) | gross +4.52 bp (t 1.01), net −12.09 bp (t −2.71); **relative-volume filter added nothing** (+1.61 bp with it vs +2.96 bp without) |
| Intraday cross-sectional momentum (09:15–09:45 → 09:50–15:10) | L31 (`results-3b-stage1.md`) | −1.60 bp, t −0.48 |
| **Market intraday momentum** (first half hour → 14:40–15:10) | L32 (same file) | **+0.70 bp**, t 0.61: right sign, 4% of cost |
| Overnight vs intraday split; volatility sort | L23–L25, L27–L28 | intraday −6.94 bp; tradable-window spread 0.24× cost |
| Filings / results-day direction | L35, L36 (§73–74) | results gap +83 bp priced by the open; post-09:20 drift 6 bp at 30 min, 0 by close |
| SMC multi-timeframe | trial 117 | −0.299R, t −5.56 |
| LLM judge on the shortlist | trial 123, forward, pending | — |
| Order book | L37, `prereg-orderbook.md` | **pending**: 15 sessions from 2026-09-28 |

### 2. Cost reality (from `backend/config.py` `COSTS` and `backend/costs.py`)

I recomputed the round trip from the repo's rates (brokerage ₹20 or 0.03%, STT 0.025% on the sell side, exchange 0.00307%, stamp 0.003%, GST 18%, slippage 0.03% per leg):

| Position | Stock: charges + 6 bp slippage | ETF (STT 0.001%): charges + 6 bp |
| --- | --- | --- |
| ₹33k | 10.6 + 6 = **16.6 bp** | 8.2 + 6 = 14.2 bp |
| ₹1 L | 8.3 + 6 = **14.3 bp** | 5.9 + 6 = 11.9 bp |
| ₹2 L | 5.9 + 6 = **11.9 bp** | 3.5 + 6 = 9.5 bp |
| ₹3 L | 5.1 + 6 = **11.1 bp** | 2.7 + 6 = 8.7 bp |

- Charges fall toward a floor of about 3.6 bp as size grows (STT alone is 2.5 bp).
- At ₹2–3 L, the **unmeasured** 6 bp slippage assumption is the largest line.
- Even at the most favourable row, every gross figure in §3 except the Reddit panel's ORB (+7.87 bp) is below 5 bp. That one clears only the ₹3 L ETF row (8.7 bp), and a stock ORB faces the 11.1 bp stock row.

### 3. Ranked candidates

"Gross/trade" is in bp of position, before costs. Hurdle: 14–17 bp (≥ ~9 bp for an ETF at ₹2–3 L).

| # | Approach | Mechanism | Best evidence (source, market, period; net? OOS?) | Indian evidence | Tested here? | Gross/trade vs hurdle | Data have / need | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Order-book imbalance / depth pull** | Informed flow shows in the book before price | Cont–Kukanov–Stoikov: order-flow imbalance explains *contemporaneous* price changes, 50 US stocks, TAQ ([arXiv 1011.6402](https://arxiv.org/abs/1011.6402)); predictive, not just contemporaneous, only at seconds–minutes | NSE, 195 stocks: predictability strong in the first 5 min and gone within 30 ([Tripathi, Dixit & Vipul, FRL 2021](https://ideas.repec.org/a/eee/finlet/v41y2021ics1544612320316779.html)); an hourly order-imbalance strategy's abnormal returns vanish after costs ([UBPLJ 2026](https://www.ubplj.org/index.php/jpm/article/view/2235)) | L37 pre-registered, not run | Unknown at 15–60 min; literature says ≈ 0 past 30 min | Have: 1 partial session (2026-09-25 13:37–15:08, 49 symbols, 3,575 rows). Need: 15 full sessions | **Run L37 as registered; expect a fail.** Do not add features. |
| 2 | **News-day "stocks in play" ORB** | Fundamental news → abnormal opening volume → continuation | Zarattini, Barbon & Aziz: 5-min ORB on the top-20 relative-volume US stocks, 2016–23, 1,637% / Sharpe 2.81 net of commission only ([SSRN 4729284](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284)) | 21-year NSE panel incl. delisted names: ORB gross **+7.87 bp, t 19.8, 10/10 years; net −12.47 bp, 0/10 years** ([r/IndiaAlgoTrading](https://www.reddit.com/r/IndiaAlgoTrading/comments/1w48gks/i_backtested_25_indian_retail_strategies_on_21/)); NSE results days move 3× normal (L35) | The ORB family yes (trial 35); news-day conditioning **no** | Unconditional ORB 4.5–7.9 bp; a news-day version is unmeasured and would need ~2–3× that | Have: NIFTY 100 5-min 2024-09→; L35 filings 2024-09→2026-01. Need: 5-min bars for ~200 F&O names 2019–25, NSE announcement timestamps 2019–25, point-in-time F&O list | **Only candidate for one new trial, low prior**, and only after a stage-0 power count (§4B). |
| 3 | SIP ORB exactly as published (10%-of-ATR stop, all names) | Same as 2 | Same paper; costs = $0.0035/share and **no slippage** (paper PDF, [Concretum](https://concretumgroup.com/wp-content/uploads/2026/02/A-Profitable-Day-Trading-Strategy-For-The-U.S.-Equity-Market.pdf)); without the volume filter it made 3.2%/yr, Sharpe 0.48 | Vendor claim (Wizzer/CastleGate): 6-month backtest, Sharpe ~4, "NIFTY +25%" over 15 May–14 Nov 2025 ([AlphaQ](https://alphaq.wizzer.in/t/from-chaos-to-code-a-rules-based-opening-range-breakout-strategy-for-indian-equities/18)). **NIFTY actually went 25,035 → 25,917 (+3.5%)** in `backend/data/overnight_1m.db`; not credible | Close variant: trial 35 | My estimate: ~16.5 bp/day of equity at a mostly binding 4× leverage cap is **~4–8 bp per rupee of position**, below our hurdle before any Indian costs. A 10%-ATR stop on a 2–3% ATR stock is 20–30 bp, so our 14–17 bp is 0.5–0.8R of friction per trade | — | **Already refuted in family; do not run as published.** |
| 4 | QQQ 5-min ORB (Zarattini & Aziz 2023) | Index opening momentum | Replication on common data 2010–2026: **full-sample Sharpe −0.06**, 0.16 in-sample ([paperswithbacktest](https://paperswithbacktest.com/strategies/orb-trading-strategy)) | [md0n-cmd](https://github.com/md0n-cmd/indian-equity-backtests): 15-min ORB, NIFTY 100 2021–25, **−21.8%**, gross ₹173 vs ₹2,357 costs; +10.4% only in its tuned year | Trial 35 | ≈ 0 | — | **Refuted.** |
| 5 | Market intraday momentum (first half hour → last half hour) | Late informed trading or gamma-hedging flow | Gao, Han, Li & Zhou (JFE 2018), SPY 1993–2013: R² 1.6%, OOS R² 1.7%; timing strategy 6.67%/yr ≈ **2.6 bp/day**, Sharpe 1.08 ([PDF](https://www.smallake.kr/wp-content/uploads/2015/01/SSRN-id2440866.pdf)); SPY 2010–18 at $0.01/share was net negative ([Marwood](https://stocksoftresearch.com/the-truth-about-intraday-momentum/)) | md0n-cmd: NIFTY 100 **1.5 bp vs ~20 bp cost**; the international study covers 16 *developed* markets, not India ([Li et al.](http://wp.lancs.ac.uk/fofi2020/files/2020/04/FoFI-2020-092-Zeming-Li.pdf)) | **L32: +0.70 bp** | 1–3 bp vs ≥ 9 bp | Have: NIFTY/NIFTYBEES 1-min 2015–25 | **Refuted; do not reopen.** The window it traded no longer exists: since 2026-08-03 continuous trading in F&O stocks ends at 15:15 with a closing auction to 15:35 ([NSE CAS](https://www.nseindia.com/static/products-services/closing-auction-session)). |
| 6 | Trend-day "noise area" + VWAP trailing stop | Intraday momentum once price leaves a volatility band | Zarattini, Aziz & Barbon, SPY 2007–24: 19.6%/yr, Sharpe 1.33 net of $0.0035 commission + $0.001 slippage per share, vol-targeted up to 4× ([SSRN 4824172](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172)); unlevered VWAP version 9.7%/yr ≈ 4 bp/day. **Independent OOS May 2024–Mar 2026: Sharpe 0.39, 9.4% vs 29.5% buy-and-hold** ([Paz, SSRN 7290621](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7290621)) | None found | VWAP-breakout family: trials 93–116 | ~4 bp at US costs of ~0.2 bp | Have: NIFTYBEES 1-min | **Not worth a trial**: gross is a third to a half of the ETF hurdle, and the edge decayed out of sample. |
| 7 | Gap-and-go / gap-fade, first-hour range | Opening overreaction or continuation | NIFTY 2,747 sessions: open→close −6.69 bp; last 491 sessions first hour −4.43 bp; only two adjacent 15:05/15:10 bins survive FDR (+1.55/−1.28 bp) ([BazaarBaazi](https://bazaarbaazi.com/research/nifty-regime/)) | Same | L23–L25, L36 (results gaps priced by the open) | ≤ 7 bp, mostly not tradable in the Kite window (L25: 0.24× cost) | Have | **Already refuted.** |
| 8 | Meta-labeling (López de Prado) | Secondary model decides whether and how much to act on a primary signal | Hudson & Thames: precision rose 0.21 → 0.39 on a Bollinger primary, judged on classification metrics, not returns across periods ([H&T](https://hudsonthames.org/does-meta-labeling-add-to-signal-efficacy-triple-barrier-method/)); [Joubert, SSRN 4032018](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4032018) | An ML trade filter on Nifty option selling did not beat trading every day (Romano–Wolf p 0.21–0.32; `prediction-engine-sweep-2026-09-26.md` §2) | Equivalent to the step-2 feature ICs and trials 41–116 | Can only filter a primary's trades; with a primary at gross ≈ 0 it is a new classifier on the same features, and it cuts n | — | **Not a source of edge.** Revisit only as a sizing layer on a primary that has already passed. |
| 9 | Volatility / India VIX / relative-volume gating | Edges measured in bp scale with volatility; costs don't | Gao et al.: stronger on high-volatility and high-volume days (same PDF) | 3a: relative-volume filter added nothing; L24 volatility-sort mechanism holds but is short of cost | Trial 35 secondary; L24 | Scales a ≤ 3 bp gross, doesn't create one | Have | **Not on its own.** It is the conditioning inside candidate 2, not a separate trial. |
| 10 | Expiry-day effects (cash market) | Hedging and pinning around derivative expiry | Indian studies are daily-scale and pre-2016 ([Vipul, JFM 2005](http://ideas.repec.org/a/wly/jfutmk/v25y2005i11p1045-1065.html); [Mahalwala 2016](https://journals.sagepub.com/doi/10.1177/0972622516629029)) | The concentration practitioners report is in **option writing** (09:20 straddle: most P&L on expiry days; live stop fills averaged +2.98 points of slippage, [r/IndiaAlgoTrading](https://www.reddit.com/r/IndiaAlgoTrading/comments/1wfc7nr/backtested_over_800_yt_trading_videos_on_12_years/)) | No | Not sized for cash | — | **Out of mandate** (no option writing); intraday option *buying* was negative in 78/78 cells (prediction sweep §2). |
| 11 | Closing-auction imbalance | Auction imbalance → closing price pressure | NSE publishes indicative imbalance during 15:20–15:25 order entry ([NSE CAS](https://www.nseindia.com/static/products-services/closing-auction-session); [SEBI circular, Jan 2026](https://www.sebi.gov.in/legal/circulars/jan-2026/introduction-of-closing-auction-session-cas-in-the-equity-cash-segment-and-certain-modifications-in-the-pre-open-auction-session_99122.html)) | None: live since 2026-08-03 | No | Unknown | No history; the engine squares off at 15:08 | **Collect data first**; not testable this year. |
| 12 | Index-rebalance effective-day pressure | Passive funds trade the close | NIFTY 1996–2003: effective-day price effect, reversed by day 9 ([SAGE 2007](https://journals.sagepub.com/doi/10.1177/0972622520070103)); 81 NIFTY events 2010–24 ([Marisetty](https://www.allfinancejournal.com/article/view/599/8-2-82)) | Same | No (894 events in `backend/research/data/nifty100_changes.csv`) | Daily, not intraday | Have | **Reject for intraday**: too few events, and the effect is multi-day. |

### 4. Test sketches for the top two

#### A. L37, the order-book test (already pre-registered, change nothing)

- **What is fixed.** Everything is in `docs/research/prereg-orderbook.md` plus amendment 1:
  - 5 features × 3 horizons (+15/+30/+60 min), entry at the next 5-min bar;
  - only horizons ending by 15:08, and only stocks sampled in ≥ 90% of ticks;
  - gate: quintile spread > 33.26 bp with t > 2 across ≥ 15 sessions, BH across 15 tests.
- **Watch.** `depth_samples` follows the rotating watchlist, so the 90% coverage rule may leave few stock-sessions. The prereg already reports kept and dropped counts; a thin sample is a stop, not a redesign.
- **Timing.** 15 full sessions from 2026-09-28 is roughly mid-October, allowing for exchange holidays.
- **Expectation, stated now:** fail. The Tripathi et al. 30-minute decay is shorter than every L37 horizon.

#### B. News-day stocks-in-play ORB (one trial, only if stage 0 passes)

- **Family.** Opening-range breakout. Trial 35 is its first member, so **N_family = 2**: two-sided Bonferroni **t ≥ 2.24**, corrected DSR ≥ 0.95 at N = 2. If the reviewer rules that news-day conditioning is the same test as trial 35's relative-volume filter, it is not run at all.
- **Universe.** NSE stocks with single-stock F&O on each date, point-in-time from NSE F&O bhavcopies. Include delisted and dropped names.
- **Event day, fixed in advance:**
  - an NSE results or board-outcome announcement disseminated between the previous day's 15:30 and 09:15 (timestamped NSE announcements, classified as in L35);
  - **and** first-5-minute volume ≥ 3× that bar's 14-session mean.
- **Entry.** Opening range 09:15–09:20. Direction is the sign of the first 5-minute bar. Stop-order entry at the range high (long) or low (short), valid 09:20–10:15, one entry per stock-day.
- **Exit.** Stop at the opposite side of the opening range, else 15:05. One variant only: no ATR stop, no targets. A 10%-ATR stop is excluded in advance because it costs 0.5–0.8R per trade here.
- **Costs.** `costs.py` at ₹1 L as primary (14.3 bp), with the ₹33k 16.6 bp row reported. Gap-through stops fill at the next bar's open.
- **Split.**
  - Selection: 2019-01 → 2025-12.
  - Halves: split at the median event date.
  - "Last 3 years": 2023–2025.
  - Held-out: 2026-01 → 2026-09, once, same sign required. Then a forward paper band.
- **Stage 0 (no returns read).**
  1. Count qualifying events. At a per-trade sd of ~200 bp (results days move ~175 bp by the close, L35), detecting a **+10 bp net** at t 2.24 needs about **(2.24×200/10)² ≈ 2,000 trades**.
  2. If fewer than 2,000 events exist in 2019–25, **withdraw without spending the trial**, as 3b did.
  3. Also confirm the data exists: announcement timestamps before 2024-09 (L36 found NSE's XBRL index thin), and Kite 5-minute history for the names.
- **Pass rule.** Mean net per trade > 0 with t ≥ 2.24 (session-clustered), family DSR ≥ 0.95, both halves positive, 2023–25 positive, held-out same sign.
- **Prior: low.** Three results point against it: 3a's relative-volume filter added nothing, L36's post-open results drift was ≈ 0, and the NSE panel's ORB gross is half the cost.

#### Stage-0 measurement worth doing regardless: real slippage

- **Why.** `COSTS.slippage_pct` = 0.03% per leg is an assumption ("rough estimate, not measured", `backend/config.py`). At ₹2–3 L it is more than half the hurdle.
- **How.** `liquidity_checks` and `depth_samples` already record spreads. Measuring median half-spread and 5-level impact at ₹1–3 L sets the true hurdle for every test above.
- **Cost of doing it.** It computes no return and spends no trial. It cannot create an edge, but a wrong hurdle mis-grades every test.

### 5. Rejected, one line each

- **SIP ORB as published:** its edge is ~4–8 bp per rupee of position (my estimate) and relies on ~1–2 bp US commissions with no slippage modelled.
- **QQQ/NIFTY index ORB:** full-sample replication Sharpe −0.06; Indian out-of-sample −21.8%; trial 35.
- **Market intraday momentum:** L32 +0.70 bp; ~2.6 bp in the US original; its last-half-hour window was restructured on 2026-08-03.
- **Noise-area / VWAP trend-day momentum:** ~4 bp gross even at US costs; out-of-sample Sharpe fell from 1.34 to 0.39.
- **VWAP breakout, pullback, mean reversion, checklist on any timeframe:** trials 41–116, gross −0.05R to +0.04R.
- **Gap-and-go / gap-fade:** results gaps are priced by the open (L36); the open→close drag is not tradable in the Kite window (L25).
- **Meta-labeling:** it filters a primary, and ours has nothing to filter. It also cuts sample size.
- **VIX / volatility gating alone:** scales a sub-cost gross; 3a's relative-volume filter added nothing.
- **Expiry-day plays:** the documented edge is option writing, which is outside the mandate; option buying measured negative.
- **Closing-auction imbalance:** no history yet, and the engine squares off before the auction.
- **Index-rebalance close:** daily-scale, reverses within days, about 5 events a year per index.
- **Vendor or community "high Sharpe" ORB/intraday claims:** 6-month samples, no out-of-sample, benchmark misstated (Wizzer: the "+25%" was +3.5%).

### 6. Data notes

- **Delivery quantity.** Only `backend/data/bhav/` (sec_bhavdata_full, 414 files, 2024-06-03 → 2026-01-01) carries `DELIV_QTY`/`DELIV_PER`. `backend/data/bhav_daily/` (2009–2026, old CM and UDiFF formats) does not.
- **Minute bars.** `backend/data/kite_history.db` is 5-minute NIFTY 100 only, 2024-09-20 onward. `backend/data/overnight_1m.db` is 1-minute NIFTY 50, India VIX, NIFTYBEES and SETFNIF50, 2015–2025.
- **Order book.** `depth_samples` holds 3,575 rows from one partial session (2026-09-25).

### Provenance

- **Repo:** `README.md` §51, 52, 57, 58, 61, 69–76, 79–87; `docs/research/trials.md`; `literature-sweep-2026-09-25.md`; `prediction-engine-sweep-2026-09-26.md`; `prereg-orderbook.md`; `decision-2026-09-26-overnight-and-significance.md`; `results-3a-opening-range.md`; `results-3b-stage1.md`; `results-overnight-etf.md`.
- **External:** fetched 2026-09-27 via Exa, r.jina.ai, gh and opencli (Reddit, read-only). SSRN abstracts were read through Exa; the two Zarattini papers and Gao et al. were read in full from author-hosted PDFs.
- **Figures that are mine, not a source's:** the SIP bp-per-notional figure, the Gao and BTM per-day conversions, and the stage-0 sample-size arithmetic. They are back-of-envelope and flagged as such.
- **Self-reported:** Reddit figures are unverified by any broker.

# Part B — daily-to-monthly timing for the delivery book

Read-only sweep. No repo file was changed, no strategy return was computed, and no held-out data was read. Repo paths are relative to `~/Projects/webapp`.

### Bottom line

Nothing here is a proven way to time entries on NSE at daily-to-monthly horizons after costs. The best evidence is about **how much momentum to hold**, not about new entry signals.

Worth pre-registering, in this order:

- **Step 0 (a confirmation, not a trial).** Rebuild NSE bhavcopies back to 2000 and run the unchanged 3i rule on 2002–2009. The files are free (2001 and 2005 zips returned HTTP 200), and NSE corporate actions for 2000–2008 are already cached in `backend/data/corp_actions/`. No test here has read those years, and they contain the 2008 crash and 2009 rebound.
- **Trial 1: a volatility-scaled momentum tilt.** When the momentum spread's own 6-month volatility is high, move part of the book into NIFTYBEES. The primary test is on 2002–2009, and it runs as a shadow sleeve next to the paper book.
  - Candid caveat: even if it works, it will probably not reach an alpha gate of t ≥ 2.2–2.6 in about 24 years of one market. The owner should decide **before any data is read** whether a risk overlay is judged on alpha or on a pre-set "do no harm, and cut drawdown" rule.
- **Trial 2: promoter open-market purchases** from SEBI insider-trading (PIT) disclosures, as the one new daily-horizon signal.
  - It has Indian evidence.
  - It has a clean sample: 2016–2025 through NSE's API, never read here.
  - Its 3-month holds are slow enough for delivery costs.

Nothing else I checked earns a trial. Trend filters to cash, deliverable %, FII/DII flows, short-term reversal, bulk deals and turn-of-month all have weak, gross-only or contrary evidence, or have already lost here.

### What this builds on (not redone)

- **3i passed** (README §82): +0.82%/month net excess, t 2.91.
  - Monthly excess sd is 3.87%, costs 0.69%/yr, one-sided turnover 213%/yr.
  - Losing years: −14.4% in 2016 and −13.3% in 2025.
  - Part A re-reads trial 119's months. Part B (ranks 201–400) is also read now.
  - The 2026 held-out was spent once, for the momentum family.
  - Source: `docs/research/results-3i-momentum-corrected-data.md`.
- **Momentum family N = 3** (trials 118, 119, 120). The Sahab Ranker (trials 121–122) lost to plain momentum. It already used volatility, beta, idiosyncratic volatility, 1-month reversal and 52-week high as cross-sectional inputs (§85, `results-ranker-engine.md`).
- **No timing, regime, trend, volatility-scaling or rebalance-date idea has been tried** in any of the 125 trials (`docs/research/trials.md`).
  - The closest items: FII futures positioning was one feature of the failed overnight gate (trial 125), and a DEALS filing class was measured intraday only (L35: +7.1 bp to the close, t 0.74; `results-event-study.md`).
  - PEAD (§84), overnight ETF (§87) and daily swing holds of 1–5 days (trials 26–34, §37) are closed.
- **Data the loader has.** `backend/research/nse_prices.py` and `slow_momentum.py` parse only OPEN, CLOSE, PREVCLOSE, ISIN and TOTTRDVAL.
  - They do not read delivery quantity.
  - `load_corporate_actions` defaults to `first_year=2008`.
  - `backend/research/data/nifty100_changes.csv` holds NIFTY 100 inclusion/exclusion events.

### Ranked candidates

"Tested here" refers to trial or look numbers in `docs/research/trials.md`.

| # | Approach | Mechanism | Best evidence | Indian evidence | Tested here? | Effect vs our costs | Data | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | **Volatility-scaled momentum** (Barroso & Santa-Clara 2015; Moreira & Muir 2017) | Momentum's risk is predictable; crashes cluster when volatility is high | US 1927–2011, plus France, Germany, Japan and the UK: scaling by 6-month volatility "virtually eliminates crashes and nearly doubles the Sharpe ratio" ([JFE](https://www.sciencedirect.com/science/article/pii/S0304405X14002566)). **Out of sample:** managing volatility usually does *not* help real-time investors across 103 strategies; momentum is one of three exceptions among the nine Moreira–Muir factors ([Cederburg et al. 2020](https://www.lehigh.edu/~xuy219/research/COWY.pdf)). After costs, long-short non-market versions earn about zero alpha, and 1-month variance scaling raises turnover up to 15× ([Barroso & Detzel 2021](https://www.sciencedirect.com/science/article/abs/pii/S0304405X21000775)) | 450 BSE stocks: adjusted Sharpe doubles; gross, long-short ([Singh et al. 2021](https://journals.sagepub.com/doi/10.1177/23197145211023001)). BSE 1996–2020 time-series version, gross ([JEFAS 2022](https://revistas.esan.edu.pe/index.php/jefas/article/view/638)) | No. The ranker's volatility input was cross-sectional, not time-series scaling | Moving Δw of the book between 15 names and NIFTYBEES costs about 0.35–0.4% per unit moved at ₹10 L. With 25% steps that is maybe 0.2–0.4%/yr, against the book's 0.69%/yr. The benefit sits in rare crash months | Prices: have. Need 2000–09 bhavcopies (free) | **Trial 1** |
| 2 | **Market state / dynamic crash protection** (Cooper, Gutierrez & Hameed 2004; Daniel & Moskowitz 2016) | Momentum pays after UP markets. It crashes in "panic" states (after declines, high volatility) when the market rebounds | US 1929–95: +0.93%/month after UP markets, −0.37% after DOWN ([CGH](https://finance.martinsewell.com/stylized-facts/dependence/CooperGutierrezHameed2004.pdf)). Crash losses come mostly from the **loser (short) leg** ([Daniel & Moskowitz](https://www.kentdaniel.net/papers/published/jfe_16.pdf)), which a long-only book holds less of | India: strong momentum after "up" markets ([2018 study](https://journals.sagepub.com/doi/10.1177/2277975218769501)). International, including emerging markets: stronger in up and low-volatility markets ([Goyal, Jegadeesh & Subrahmanyam 2022](https://ssrn.com/abstract=4012902)) | No | A whole-book switch to NIFTYBEES happens a few times a decade, so cost is negligible. But 2010–25 had few DOWN states, so there is little to learn from those years | Same as #1 | Second arm of Trial 1 |
| 3 | **Index trend filter to cash** (10-month SMA / 200-DMA) | Time-series momentum at market level | The Indian 10-month SMA backtest mainly reduced risk, with mixed returns ([freefincal](https://freefincal.com/market-timing-with-ten-month-moving-average-tactical-asset-allocation-backtest-part-2/)). Dual momentum (Nifty/gold/cash): 12.1% vs 9.2% over 2008–26. That result is price-return only, a single run with no t-stat, and the author flags gold's exceptional run ([md0n-cmd](https://github.com/md0n-cmd/indian-equity-backtests)) | As left | No | Each whipsaw costs a full round trip plus 15 DP charges, and V-shaped rebounds (e.g., 2020) get missed. It times market beta, not the momentum premium | Have | Reject as a lead. At most a reported-only variant |
| 4 | **Rebalance date / tranching** | Not an edge: the date only adds variance ("timing luck") | US long-only factor indices: timing luck often above 100 bp/yr; 4.4% for 100-stock semi-annual momentum; no schedule reliably best ([Hoffstein et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3673910), [blog](https://blog.thinknewfound.com/2019/11/the-dumb-timing-luck-of-smart-beta/)) | Turn-of-month effect: persistent in mid/small-cap indices 2009–17, insignificant in large caps after 2006 ([Sage 2021 study](https://journals.sagepub.com/doi/10.1177/2278533721994713)) | No | Tranches add sell-days, each with ₹15.34 DP per scrip. Costly at ₹1 L | Have | No trial. Record forward shadow tranches as a measurement |
| 5 | **Residual momentum** (Blitz, Huij & Martens 2011) | Rank on returns net of market/factor exposure: less beta, smaller crashes | Not explained by other factors or crash risk; holds internationally, including emerging markets ([Blitz, Hanauer & Vidojevic 2020](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2947044)) | India 2008–24, gross, abstract only: volatility-adjusted and information-discreteness momentum beat idiosyncratic momentum on risk-adjusted terms ([SSRN 4977717](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4977717)). **We already use volatility-adjusted momentum** | No. The ranker had idiosyncratic volatility, not residual momentum | Turnover about the same as the base book | Have | Defer. Ranks below #6 |
| 6 | **Frog-in-the-pan / information discreteness** (Da, Gurun & Warachka 2014) | Investors underreact to news that arrives gradually | US: 6-month momentum is +5.94% for continuous-information stocks vs −2.07% for discrete; no long-run reversal ([paper](https://academicweb.nd.edu/~zda/Frog.pdf)). Wins an out-of-sample international horse race, including emerging markets ([Goyal et al.](https://ssrn.com/abstract=4012902)) | Better risk-adjusted returns in India; gross ([SSRN 4977717](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4977717)) | No | Turnover no higher than the base; continuous-information winners persist about 8 months | Have (daily closes) | Trial 3, shadow only |
| 7 | **Promoter open-market buying** (SEBI PIT disclosures) | Insiders, mostly promoters, buy ahead of returns | India: net insider purchases precede abnormal returns, driven by promoters, with little link to near-term earnings ([Brochet, Lee & Srinivasan](https://www.stern.nyu.edu/sites/default/files/assets/documents/Brochet%20Lee%20Srinivasan%202017%20-%20The%20Role%20of%20Insider%20Trading%20in%20the%20Market%20Reaction%20to%20Earnings%20News.pdf)). Gross, academic | As left | No (L35 had no insider class) | 3-month holds mean about 4 round trips a year per slot, roughly 1.4%/yr at ₹10 L. It needs gross excess above about 2%/yr | NSE API: **verified** 1,646 disclosures for 1–15 Mar 2016, with acquisition mode, stake % before and after, and dissemination timestamp ([page](https://www.nseindia.com/companies-listing/corporate-filings-insider-trading)) | **Trial 2** |
| 8 | **NIFTY inclusion / exclusion** | Price pressure from passive flows | Mixed. 1996–2003: an effective-day effect that reversed within 9 days ([study](https://journals.sagepub.com/doi/10.1177/0972622520070103)). 2009–18: additions earned permanent positive abnormal returns ([study](https://www.macrothink.org/journal/index.php/ijafr/article/view/15320)) | As left | No. The events already sit in `nifty100_changes.csv` | One round trip per event | Have events; announcement dates must be checked | Later: an event-study look first, not a trial |
| 9 | **Bulk/block deal buys** | Informed large buyers | India 2004–12: significant abnormal returns around bulk buys, plus front-running ([Chaturvedula et al. 2015](https://ideas.repec.org/a/eee/ememar/v23y2015icp26-45.html)) | As left | Intraday only: L35 DEALS, t 0.74 | Deals are disclosed after hours; the drift after disclosure is unmeasured | NSE archives (today's file verified) | Low. A look only |
| 10 | **Deliverable %** | Volume from "conviction" buyers | Only tiny studies: 2 of 13 bank stocks showed a Granger link ([review](https://oldror.lbp.world/UploadedData/7885.pdf)) | Weak | No; not parsed | — | MTO files are free back to at least 2005 (verified); `sec_bhavdata_full` only from about 2020 (2011 returned 404, 2020 returned 200) | Reject for now |
| 11 | **FII/DII flows as a timer** | Flow pressure | FIIs trade on positive feedback (flows follow returns); DIIs trade the other way ([study](https://journals.sagepub.com/doi/10.1177/0972150916630830), [study](https://journals.sagepub.com/doi/10.1177/0972150920915330)) | As left | Feature in trial 125 (FAIL) | — | NSE shows only the latest day (§20) | Reject |
| 12 | **Short-term reversal** | Payment for providing liquidity | Weak in large caps recently ([Da, Liu & Schaumburg](https://academicweb.nd.edu/~zda/Reversal.pdf)). Indian weekly reversal: −3.8% CAGR, with costs eating ₹44.6k of ₹50k ([md0n-cmd](https://github.com/md0n-cmd/indian-equity-backtests)) | As left | Ranker input, trials 121–122 (FAIL) | High turnover | Have | Reject |
| 13 | **NSE factor indices** (Momentum 30, Alpha/Quality/Low-Vol, multifactor) | Packaged factor exposures | The whitepapers are backtests: e.g., Alpha Low-Vol 30 beat NIFTY 50 by 6.86%/yr since 2005, as of 2017 ([NSE](https://archives.nseindia.com/content/indices/NIFTY%5FMulti-Factor%5FIndices%5Fwhitepaper.pdf)). Live NIFTY200 Momentum 30: 5-year CAGR 11.0% to Aug 2026 (`literature-sweep-2026-09-25.md`). Drawdown from Sep 2024: −31.8% ([Wright](https://www.wrightresearch.in/blog/momentum-strategies-underperforming-2025-data-insights/)). In the 2024–25 decline: −21.75% vs its parent's −12.61% ([Value Research](https://www.valueresearchonline.com/stories/222938/momentum-funds-performance-12-months/)) | — | Read as literature | ETF costs are tiny | — | Use as a fallback implementation, not a signal |
| 14 | **Timing new capital** (lump sum vs staggered) | — | Lump sum beat cost averaging about two-thirds of the time ([Vanguard](https://corporate.vanguard.com/content/dam/corp/research/pdf/cost_averaging_invest_now_or_temporarily_hold_your_cash.pdf)) | — | — | — | — | No trial. Add new money at the next monthly rebalance |

### Would overlays have cut 2016- and 2025-type losses?

The mechanism targets exactly those episodes.

- **2016** followed a market decline with high volatility.
- **2024–25** was a momentum-specific slump in India: winners fell harder than the market ([Value Research](https://www.valueresearchonline.com/stories/222938/momentum-funds-performance-12-months/)).

Whether a lagged volatility estimate cuts exposure *before* the loss or only after it is an empirical question, and I did not compute it. Computing it on 2010–2025 now would be a contaminated look: those losses are already known, and they motivate the overlay. That is why the primary test sample below is 2002–2009.

### Test sketches

#### Step 0: confirm the base rule on 2002–2009 (a confirmation like L38, not a trial)

1. Download bhavcopies from 2000-01 to 2009-03 from `nsearchives.nseindia.com/content/historical/EQUITIES/`.
2. Lower `first_year` to 2000.
3. Rerun 3i's stage-0 gates: split consistency ≥ 97%, and no more than 10 unexplained phantom drops.
4. Run 3i Part A's rules unchanged.
   - Confirms if: mean net excess > 0 with t ≥ 1.65.
   - Report 2008–09 separately.

Caveats: pre-2011 rows have no ISIN, and the NIFTYBEES start date is unverified; check both at stage 0. Whatever the result, the forward band stays fixed.

#### Trial 1: volatility-scaled momentum tilt (pre-register before building the 2000s data)

**Family.** Conservatively, it joins the momentum family.

- M1 alone makes N = 4 (t ≥ 2.50); adding M2 makes N = 5 (t ≥ 2.58), per `decision-2026-09-26-overnight-and-significance.md`.
- If the reviewer rules "momentum risk timing" a new family, N = 2 (t ≥ 2.24).
- Record that ruling before any data is read.

**Rules, fixed in advance.**

- **Base book:** exactly as 3i and the paper book.
- **M1:**
  - At each month-end, σ̂ = annualised standard deviation, over the prior 126 sessions, of the daily spread "equal-weighted top 30 by the 3i score minus the equal-weighted universe".
  - σ* = the median of σ̂ over the prior 36 month-ends (expanding window). No full-sample parameter is used.
  - Target weight w = min(1, σ*/σ̂), floored at 0.25, rounded down to steps of 0.25.
  - The book holds w in the 15 names and 1−w in NIFTYBEES.
  - The split changes only at the monthly rebalance, and only when the 0.25 step changes.
- **M2:** if the universe's trailing 36-month return is below 0 (Cooper et al.'s definition), hold 100% NIFTYBEES until the state flips.

**Costs.** 3i's delivery costs. ETF sells pay 0.001% STT plus DP.

**Samples.**

- **Primary:** 2002 → 2010-01, never read.
- **Secondary:** 2010-02 → 2025-11, disclosed as already read for the base rule.
- **Statistic:** the monthly net difference, overlay minus base (Newey-West t), plus a Ledoit–Wolf test of the Sharpe difference.
- **Gate:** the family bar on the difference, positive in both samples and in 2023–25. Maximum drawdown and worst 12 months are reported.

**Power, stated up front (my rough arithmetic).**

- Suppose the overlay de-risks about 30% of months by about 0.4.
- The difference series then has an sd of about 0.4 × 3.9% × √0.3 ≈ 0.85%/month.
- Reaching t 2.5 over about 288 months needs an average benefit of about 1.5%/yr.
- So an alpha-bar FAIL is the likely outcome even if the overlay reduces risk as the literature says.

**Owner decision needed beforehand.** Either keep the alpha bar and accept the likely fail, or adopt, for overlays only, a non-inferiority rule: CAGR within 1 pp of the base in both samples, and drawdown cut by at least 25% in both. The current rule says a pass on economics alone is a fail.

**How it plugs in.** A shadow sleeve inside the daily `momentum_book.py` job, with its own NAV on the Momentum Book page. The main book, its band and its switch-off stay untouched. Because live code cannot import research code, the logic has to be duplicated.

#### Trial 2: promoter open-market purchases (new family "insider buying", N = 2, t ≥ 2.24)

**Events.**

- `personCategory` is promoter or promoter group, `acqMode` = "Market Purchase", equity shares, value ≥ ₹10 lakh.
- The company is in the top 500 by liquidity at the prior month-end.
- One event per company per 60 days.
- **H1:** all qualifying events.
- **H2:** only events where the stake rises by at least 0.10 percentage points, measured from the API's before/after percentages.

**Trades.** Buy at the close of the first session after the dissemination timestamp. Hold 63 sessions. Equal weight, at most 20 slots; overflow events are skipped in timestamp order. The benchmark is the equal-weighted universe. Costs follow 3i, with slippage of 0.10%/side.

**Samples.**

- Selection: 2016–2025. Halves are 2016–20 and 2021–25; the last three years are 2023–25.
- Held-out: 2026-01 → 2026-08. This data has not been read for this family, but its prices were seen through momentum; disclose that.
- Then forward paper.

**Stage 0 (no returns read).** Events per month, disclosure lags, and parse rates. If the universe averages fewer than about 8 events a month, stop.

**Pass.** The full family bar: t ≥ 2.24, DSR ≥ 0.95, both halves, last three years, CAGR gap ≥ 2 pp, ≥ 100 round trips.

**How it plugs in.** Its own paper book, like the Jev book. It never mixes into the momentum book unless a later combination test passes.

#### Trial 3 (only after 1 and 2): frog-in-the-pan tie-break

- Information discreteness (ID) follows Da et al.: sign(formation return) × (% negative days − % positive days) over 12 months.
- The 15 holdings are filled from the top 30 by lowest ID. The rank-30 hysteresis is unchanged.
- Paired test against the base on 2002–09 (top 200) and on 2010–25 **ranks 401–600**, which no test has read.
- Gate: paired t ≥ 1.65 in both samples, plus the momentum-family bar.
- Shadow sleeve only.

### Rejected, one line each

- **Trend filter to cash:** it times beta, not momentum, and the Indian evidence shows risk reduction with mixed returns.
- **Deliverable %:** no credible return evidence.
- **FII/DII flows:** they follow returns rather than lead them.
- **Short-term reversal:** it already lost here (121–122) and costs eat it.
- **Bulk/block deals:** the effect sits around the trade, before public disclosure.
- **Turn-of-month and rebalance day:** timing luck is variance, not edge.
- **Residual momentum:** the Indian evidence favours the volatility-adjusted rule we already run.
- **Re-weighting inside the book** (inverse volatility or score weights): no evidence it adds net return, and it changes the tested rule.
- **PEAD, the overnight ETF, and 1–5-day swings:** already closed (§84, §87, §37).

### Limits

- SSRN, Elsevier and Sage pages were read as abstracts or snippets, so their numbers are as reported.
- The Indian studies are mostly gross and long-short.
- Short-term capital gains tax (20% under 12 months) is not modelled. Overlays that sell holdings realise gains earlier.
- Nothing here predicts prices or guarantees profit.
