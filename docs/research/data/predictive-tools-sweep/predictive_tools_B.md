# Predictive tools, scope B — finance ML libraries, model zoos, factor libraries, agent systems (2026-09-29)

Channels: agent-reach — Exa web search (`mcporter exa.web_search_exa`), GitHub via `gh` (repo metadata, issue search through `search/issues`, READMEs, releases, commits), page reads via `r.jina.ai` and raw.githubusercontent.com. No login-backed platform; nothing posted.

Bar for "test": can it be scored in the L40 harness (cross-sectional rank vs realised 15/30/60-minute return at six fixed times over ~79 sessions; spread > 33.26 bp, t > 2, both halves, BH q=0.10, partial IC given m60), on data already on disk, trained strictly out of sample, one run. Facts checked in the repo first: no trained model of any kind exists in `backend/research/` (trials 41–116 were hand-coded rules; L40 is zero-shot Kronos); the Kite depth sampler is 5 levels at ~30 s, recording since 2026-09-24; none of the names below appears in `docs/research/*.md` except Qlib (one row in the literature sweep).

## Ranked table

| # | Candidate | Licence | Runs on our data | Training | Independent net-of-cost OOS evidence on equities | Intraday / Indian | Sweep covered? | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | **Qlib LightGBM + Alpha158** (microsoft/qlib, 49k★) | MIT | Yes: daily via dump_bin; 5-min via ported expressions | LightGBM minutes on CPU | Third-party US walk-forward with 2+2 bp: mean Rank IC −0.005, gate RESEARCH_ONLY. Vendor 1-min CN benchmark: 0.74 bp/period gross | Intraday gross only; Indian none | Partly (one row, family rejected on outside evidence; never trained here) | **Test** — one look in the L40 harness |
| 2 | **Factor-zoo intraday market timing** (Aleti–Bollerslev–Siggaard, Mgmt Sci 2025) | paper | Partly (~20 NIFTY 100 factor portfolios buildable) | Ridge, seconds | Peer-reviewed: SPY intraday cost-adjusted Sharpe 1.37 vs 0.09 OOS | Intraday yes; Indian no | No | **Later** — own pre-reg, index-timing family |
| 3 | **Vibe-Trading Alpha Zoo** (HKUDS, 34k★, Apr 2026; qlib158/alpha101/gtja191 ports) | MIT | Probably, as a pandas library (unverified) | None | None; 104 leak/lookahead issue hits, repo fixing its own | None | No | **Use as the factor code for #1**; skip the agent |
| 4 | **DeepLOB / DeepLOB-Attn / TransLOB / TLOB** + LOBCAST, LOBFrame | mixed, mostly none | No: needs event-level 10-level LOB for months | From scratch, hours | Two independent benchmarks negative on transfer (F1 48–61% on unseen data; "not actionable") | No NSE study | DeepLOB named; successors/benchmarks not | **Skip**; revisit only if L37 clears and ≥3 months of depth exist |
| 5 | **Kronos NSE pre-registered negatives** (kronos-candlecast, OpenAlpha) | MIT | n/a (results) | none | Pre-registered: Kronos-small 81% worse CRPS than random walk on NSE daily; Kronos-base 0/4 US ETFs beat persistence | Indian daily yes | No | **Attach to L40 as prior evidence** |
| 6 | TradingAgents v0.5.0–0.5.2 (since 2026-09-18) | Apache-2.0 | No | none | Profit Mirage: 56% Sharpe decay after GPT-4o cutoff | None | Yes | Skip — new commits only fix back-dated-run leakage |
| 7 | virattt/ai-hedge-fund (+ Look-Ahead-Bench) | MIT | No | none | Look-Ahead-Bench: −15 to −22 pp alpha decay past cutoff | None | Family | Skip |
| 8 | FinMem / FinAgent / FinCon / QuantAgent / FinRobot | MIT / none / Apache | No news path | none | Profit Mirage (decay 50–72%), KTD-Fin (returns = beta+style), arXiv 2608.27734 (all rejected net of cost) | None | Family | Skip |
| 9 | FinGPT-Forecaster | MIT | No | optional | One-author pilot: +2.3% alpha decay over one month; leakage flagged elsewhere | None | Family | Skip |
| 10 | AlphaAgent / RD-Agent(Q) | none / MIT | Daily yes | many LightGBM fits + LLM API | Own Qlib backtests only; search-aware audit rejects LLM-mined strategies | None | No | Skip — trial multiplier |
| 11 | StockFormer (gsyyysg) | none | Daily | hours | None; issues #21 (whole-sample scaler leak) and #22 (cannot reproduce, suspicious test file) open | None | No | Skip |
| 12 | FinRL / FinRL-Meta / FinRL-DeepSeek | MIT | Daily | hours | None independent; #189 bfill look-ahead (closed) | None | Yes | Skip |
| 13 | Alpha101 libraries (yli188, popbo, KunQuant) | none / none / Apache | Daily | none | Paper in-sample only | None | No | Skip as separate look |
| 14 | tsfresh / featuretools | MIT / BSD-3 | Yes | none | None found | None | No | Skip |
| 15 | stockpy | MIT | Yes | small | None | None | No | Skip |
| 16 | 2026 "financial foundation model" repos (navyam-oss, pragma-ffm) | Apache / none | No | n/a | n/a (text LLM; transaction model) | None | No | Skip — listed to close the "2026 releases" question |

## Candidates

### 1. Qlib LightGBM on Alpha158 (and the deep zoo) — test
`https://github.com/microsoft/qlib`, MIT, pushed 2026-09-22. Alpha158 is 158 rolling price/volume expressions (`qlib/contrib/data/loader.py`); Alpha360 is the raw last-60-bar window. The vendor's own daily CSI300 table (20 seeds) gives LightGBM IC 0.040, Rank IC 0.048, AR 12.8%, IR 1.57; every deep model in the zoo sits within ±0.01 IC of it (HIST 0.052 needs a stock-to-concept matrix that does not exist for NSE; TRA 0.044–0.049; IGMTF 0.048; ADD 0.043; TFT 0.036 and pinned to Python 3.6–3.7 + CUDA 10.0; KRNN 0.017 with a negative return, and issue #2029 reports it does not train). Issue #1668 (open) says `run_all_model.py` does not reproduce the table. The one intraday number the vendor publishes (`examples/highfreq`, Chinese 1-minute bars, Alpha158 + LightGBM) is IC 0.035 and a long-short average return of 0.000074 — 0.74 bp per period, gross — against the project's 16.63 bp round trip. The only independent, cost-aware test found (Pangqiang-Gary/qlib-us-walk-forward, 2026-08, US daily, 2+2 bp, three expanding folds) reports mean Rank IC −0.005, not positive in every fold, on a survivorship-biased universe; its author's own gate refused to promote it. There is no Indian evidence. An IN-region Yahoo collector was merged in 2021 (PR #513) but the project's Kite bars are better data.

Why test anyway: the engine sweep rejected "ML on OHLCV bars" on other people's evidence, and the project has never trained a model on its own bars; this is the cheapest way to close that gap with a number. How: one pre-registered look in the L40 harness — port the Alpha158 expressions to the 5-minute bars (windows in bars; the Vibe-Trading qlib158 port may save the typing, see #3), train one LightGBM per horizon on 2024-09 to 2025-08-15 with a 5-session purge, targets = the harness's next-bar-open to bar-close returns cross-sectionally ranked, freeze, then score at the six decision times on the 2025-09..12 selection sample with the same statistics, BH family of 3, partial IC given m60. Expected outcome: null. Do not run TFT/HIST/TRA/KRNN/ADD/IGMTF as separate looks; the vendor's own tables say they add nothing LightGBM lacks.

### 2. Intraday market-return predictability from the factor zoo — later
Aleti, Bollerslev and Siggaard, *Management Science* 71(9) 2025 (`https://public.econ.duke.edu/~boller/Papers/MS_2025.pdf`). Not a repo. Lagged intraday returns on 200+ characteristic-sorted portfolios, regularised (ridge/LASSO/boosting), predict the aggregate market's next intraday return; a SPY strategy on the forecasts has an annualised transaction-cost-adjusted Sharpe of 1.37 out of sample against 0.09 for SPY, with gains concentrated in high-uncertainty periods and a few liquidity/tail-risk factors. This is the only intraday factor-library result found that is peer-reviewed, out of sample and net of cost. It does not fit the L40 harness (it times the index; the harness ranks stocks) and needs its own pre-registration in a new family: build ~20 intraday factor-portfolio return series from the NIFTY 100 5-minute bars and bhavcopy characteristics, expanding-window ridge, target NIFTY futures (6–7 bp) over 30/60 minutes, Bonferroni family of 1. Open questions: whether a 20-factor NSE zoo carries the slow-moving-capital signal the 200-factor US zoo does; no third-party replication exists. Recommend only if the owner opens an index-timing family.

### 3. Vibe-Trading Alpha Zoo — use as factor code for #1; skip the agent
`https://github.com/HKUDS/Vibe-Trading`, MIT, created 2026-04-01, 34k★, v0.1.16 released 2026-09-29. Release v0.1.8 (2026-05-17) bundled 452 formulaic alphas: an Apache-2.0 port of Qlib's Alpha158 (154 alphas, upstream SHA pinned), Alpha101 from the Kakushadze appendix, GTJA191, and an "academic" set, "lookahead-banned at the operator layer". No net-of-cost result anywhere; the surrounding product is an LLM agent with a shadow account. Its tracker has 104 hits for leak/lookahead in five months, all the repo fixing itself: options signals filled at the same-day close (#1293/#1304, closed 2026-08-31), Carhart momentum leaking today's price (#1578, open 2026-09-24), and a proposed warning when a backtest window lies inside the LLM's training data (#1613, open). Verdict: the factor port is worth a look as an implementation shortcut for candidate 1 if it accepts an arbitrary OHLCV frame (not verified); run the L40 stage-0 lookahead proof on it first. Never run its "bench any zoo on your universe" CLI as a search: 452 × 3 comparisons.

### 4. DeepLOB family and the LOB benchmark frameworks — skip
Originals: zcakhaa/DeepLOB (611★, no licence, last push 2021), jwallbridge/translob (125★), LeonardoBerti00/TLOB (178★, MIT, 2025). Benchmarks: matteoprata/LOBCAST (123★) and FinancialComputingUCL/LOBFrame (261★). DeepLOB's own profit simulation is mid-to-mid with no costs, in the paper's words. Three independent reads are negative on transfer: LOBCAST (Prata et al., *AI Review* 2024) re-implemented 15 models and found all of them drop to F1 48–61% on unseen NASDAQ 2021/22 data, "inadequate for practical applications"; LOBFrame (Briola et al., 2025) finds DeepLOB's forecasting power "does not necessarily correspond to actionable trading signals"; TLOB's own abstract says existing models "fail to generalize across different market conditions and assets". The data requirement is event-level 10-level books for months per stock; the project has 5 levels at ~30 s for five sessions. No NSE study found. Revisit only if L37 clears its gate and ≥3 months of snapshots exist, and then at the L40 horizons, not the papers' 10-event horizons.

### 5. Kronos NSE pre-registered negatives — attach to L40
Not tools, but the closest thing to independent NSE evidence on the model L40 is about to test. neopentane7/kronos-candlecast (MIT; acceptance rule committed 2026-08-03, grid run five days later): Kronos-small zero-shot on NSE daily bars, 708 windows, 59 tickers, 30-session horizon — fair CRPS 121.9 vs 67.2 for a random walk with drift (81% worse), 80% intervals covering 41%; conformal repair does not fix it; the defect is variance that stops growing with horizon. ThomasCaruso/OpenAlpha (MIT): Kronos-base zero-shot on four US ETFs, 1,600 generations — median relative skill vs persistence −0.04 to −0.08, 0/4 assets, CI excluding zero on the wrong side; 12–25% of tokenizer round-trips produce invalid candles and repairing them changes forecast error by exactly 0.0. abhijatchaturvedi/FineForecast (proprietary licence) fine-tunes Kronos-base on NSE with QLoRA plus a MASTER-style ranking head and reports no number in its README; jvaidya10/kronos-india says results are "being collected". Both negatives are daily-horizon, so they do not shorten L40; they lower its prior. Cite them in the L40 results file.

### 6. TradingAgents since 2026-09-26 — skip
v0.5.0 (09-18), v0.5.1 (09-24), v0.5.2 (09-29). The commit log is data-provider hygiene for back-dated runs: withhold insider trades without a filing date, serve past-run financial statements only with a known filing date, treat Yahoo's empty window as no data. That is the leakage the sweep cited (#1007) being patched, not new evidence. Profit Mirage (arXiv 2510.07920) measured a 55.7% Sharpe decay after the backbone's cutoff.

### 7. ai-hedge-fund — skip
MIT, 63.8k★. Look-Ahead-Bench (arXiv 2601.13770, code benstaf/lookaheadbench) used it as the harness: Llama 3.1 8B/70B and DeepSeek 3.2 lose 15–22 pp of alpha between an in-training period and a post-cutoff one; point-in-time models do not. The repo's own issues #720/#721 (closed 2026-09-25) admit "model memory can still leak into backtests through the ticker and filing dates" and blind all prompts from v2.4.0. No net-of-cost record.

### 8. FinMem, FinAgent, FinCon, QuantAgent, HedgeAgents, FinRobot — skip
FinMem (MIT, dormant since 2024-08); FinAgent has no public code I could find. Profit Mirage: post-cutoff total-return decay 50–72% across five agents, FinMem worst (72%, prediction consistency 0.82 under counterfactual perturbation). KTD-Fin (arXiv 2605.28359, May 2026): ten frontier LLM agents on CSI300 2024–26 with identifiers masked — returns explained by market and style exposure, little stock-selection alpha. "What survives honest evaluation?" (arXiv 2608.27734, Aug 2026): with look-ahead excluded by construction and Deflated Sharpe indexed to the search's own trial count, every LLM-discovered strategy is rejected on a 453-stock point-in-time universe with realistic costs, while passive benchmarks are certified.

### 9. FinGPT-Forecaster — skip
MIT, 21k★. Weekly direction from headlines. The only independent read is a one-author Research Square case report (posted 2026-07-01) plugging it into Look-Ahead-Bench for one month per period: alpha decay +2.27%, which says nothing about edge net of cost. Profit Mirage groups it with the leaky fine-tuned financial LLMs. Sentiment family already rejected.

### 10. AlphaAgent and RD-Agent(Q) — skip
AlphaAgent (RndmVariableQ, 418★, no licence; KDD 2025) and RD-Agent(Q) (Microsoft, MIT; NeurIPS 2025 D&B) mine formulaic factors in an LLM loop and backtest each candidate in Qlib. All evidence is their own Qlib backtests (daily, CN/US); AlphaAgent's paper uses RD-Agent as a baseline and reports it worse, which is one framework's word against another. Every loop iteration is a search trial the project's one-run rule would have to count, and the one search-aware independent evaluation (arXiv 2608.27734) rejects everything of this kind. Also a GPT-4-class API bill per run.

### 11. StockFormer — skip
gsyyysg/StockFormer (357★, no licence). Issue #21 (open since 2024-12, six agreeing comments): features standardised with the whole dataset's mean/std, i.e. the test period leaks into training. Issue #22 (open, 2025-05): the released model produces all-zero actions while the shipped asset curve rises; "cannot reproduce ... faked?". Unanswered.

### 12. FinRL / FinRL-Meta / FinRL-DeepSeek — skip
Family rejected by the sweep (FinRL #938). Added here: FinRL #189 (closed 2021) — `fillna(bfill)` look-ahead in the feature engineer; FinRL-Meta's tracker has no leakage report at all (only #83, a normalisation suggestion), which is absence of reports, not evidence. FinRL-DeepSeek's evaluation is its own (its author also wrote Look-Ahead-Bench).

### 13. Alpha101 libraries — skip as a separate look
yli188/WorldQuant_alpha101_code (876★, no licence, last push 2019), popbo/alphas (591★, no licence), Menooker/KunQuant (Apache-2.0, a compiler for Alpha101/Alpha158 expressions), and the Vibe-Trading MIT port. Kakushadze's paper reports in-sample statistics only; the literature sweep already cites the median replication Sharpe of 0.37. Alpha158 spans the same operator family, so adding Alpha101 to candidate 1 would be a second search shot for no new information class.

### 14. tsfresh / featuretools — skip
Generic feature generators (~800 statistics per window). No finance evidence of any kind surfaced; on bars they are the function class trials 41–116 measured at about zero, and their selection step is a multiple-comparison search.

### 15. stockpy — skip
SilvioBaratto/stockpy, MIT, 20★: PyTorch/Pyro regression wrappers with a stock-themed name. No evidence.

### 16. 2026 "financial foundation model" releases — skip
Searches for new open-weight finance price models in 2026 returned Kronos (AAAI 2026 acceptance, no new weights), navyam-oss (an Indian-finance *text* LLM, Apache-2.0, 0★, created 2026-09-08) and a hobby reimplementation of Revolut's PRAGMA transaction model. Nothing that forecasts prices.

## Shortlist

1. **Qlib LightGBM + Alpha158 on the 5-minute bars** — test, one look in the L40 harness; expected null; closes the "never trained a model on our own bars" gap.
2. **Factor-zoo intraday market timing (Bollerslev et al. 2025)** — later; the only peer-reviewed net-of-cost intraday factor result; needs its own index-timing pre-registration.
3. **Vibe-Trading's qlib158/alpha101 ports** — as the factor implementation for #1 only, after a lookahead proof; not the agent.
4. **DeepLOB/TLOB via LOBCAST/LOBFrame** — skip; two independent benchmarks say the models do not transfer, and the depth data does not exist here.
5. **kronos-candlecast / OpenAlpha** — not tools; two pre-registered negatives on zero-shot Kronos to cite in L40.

## What I could not verify

- Whether Vibe-Trading's qlib158 module computes on an arbitrary OHLCV frame at 5-minute cadence without Qlib's bin store — not executed.
- Whether Qlib's bin format accepts a 5-minute NSE calendar without code (docs list "day" and "1min") — not executed.
- Whether Qlib's published CSI300 table already nets the default open/close costs; the README does not say (the literature sweep recorded IR 2.00 gross → 1.44 with cost).
- Pangqiang-Gary/qlib-us-walk-forward was read through a GitHub mirror Exa returned (github.laiyagushi.com); numbers are as that page shows.
- The FinGPT case report is a one-author preprint with one month per period; treated as weak.
- FineForecast's Phase 4 cost-adjusted backtest numbers: not in the README, notebooks not opened (proprietary licence).
- Aleti–Bollerslev–Siggaard: authors' own OOS numbers, peer-reviewed, no third-party replication found; transfer to a ~20-portfolio NSE zoo unknown.
- LOBCAST/LOBFrame P&L tables were not read; the F1 collapse figures are from the papers' text.
- No Reddit or X reads (out of scope here). Exa was the only web index used; it may miss very recent releases.
