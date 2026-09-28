# Kronos, researched — what the model is, what its own issue tracker says, what independent tests found, and how it will be tested here

**2026-09-28. Research note. No code was run against project data; no trial or research look was spent.** Companion to `docs/research/prereg-kronos-feature-ic.md` (research look L38), which fixes the test before any of it is run.

## 1. Sources, and what this session could and could not reach

This session's network proxy allows github.com and raw.githubusercontent.com but blocks arxiv.org, huggingface.co, ojs.aaai.org, alphaxiv, and every blog that summarises the paper. So:

| Verified directly | How |
| --- | --- |
| Kronos code, README, tests, fine-tune scripts | `git clone` of shiyu-coder/Kronos (2026-09-28 head) |
| Issues #199, #227, #234, #254, #265, #277, #307, #326, #354 | github.com pages |
| chandewardnyanesh/kronos-nse-terminal README | github.com |
| georgiag7652/kronos-india README | raw README |
| CPU inference timing | run here, random weights, same architecture (weights are on Hugging Face, blocked) |

| Not verified, quoted from search snippets only | |
| --- | --- |
| Paper abstract numbers (12 billion K-lines, 45 exchanges, RankIC +93 % over the best TSFM, +87 % over the best non-pretrained baseline, −9 % volatility MAE, +22 % generative fidelity; AAAI 2026) | consistent across several snippets |
| The paper's backtest tables (annualised excess return, information ratio on CSI300/CSI1000, top-K rule, cost assumption) | **not obtained**; no number from them is used here |
| Rahimikia, Ni & Wang, "Re(Visiting) Time Series Foundation Models in Finance" (arXiv 2511.18578) and "Pretrained Time-Series Foundation Models for Financial Return Forecasting" (arXiv 2606.27100) | abstracts via snippets; neither tests Kronos |

Anything below marked *snippet* carries that caveat.

## 2. What Kronos is (from the code)

- **Two models.** `KronosTokenizer` (encoder–decoder Transformer, Binary Spherical Quantization, 4.0 M parameters at the repo's default shape) turns each OHLCV(+amount) bar into two sub-tokens (coarse s1, fine s2, 10 bits each). `Kronos` (decoder-only Transformer) predicts the next bar's token pair autoregressively. Open weights: mini 4.1 M (context 2048), small 24.7 M, base 102.3 M (context 512). Large (499 M) not released. MIT.
- **`KronosPredictor.predict(df, x_timestamp, y_timestamp, pred_len, T, top_k, top_p, sample_count)`** (`model/kronos.py:519`): z-scores the six columns **over the lookback only** (`x_mean, x_std = np.mean(x, axis=0), np.std(x, axis=0)` on `x` = lookback rows), clips at ±5, tokenises, samples `pred_len` bars `sample_count` times, decodes, averages the samples, and de-normalises. If `amount` is missing it is derived as `volume × mean(open, high, low, close)`; if `volume` is missing both are set to 0. Time stamps (minute, hour, weekday, day, month) are embedded, so the model knows where a bar sits in the day.
- **The autoregressive loop** (`auto_regressive_inference`, `model/kronos.py:389`) re-runs the full 512-token context for every predicted bar; no KV cache. Cost is therefore linear in `pred_len` and in `sample_count`.
- **Sampling is stochastic** (`T=1.0, top_p=0.9` defaults). The same input gives different outputs unless the seed is fixed; the repo's own regression test seeds `random`, `numpy` and `torch` and pins the model and tokenizer to Hugging Face revisions (`tests/test_kronos_regression.py`: `MODEL_REVISION`, `TOKENIZER_REVISION`, `MSE_EXPECTED = [0.008979, 0.003741]` at context 512/256, pred_len 30 on its sample file).
- **The repo's backtest** is a fine-tuned, daily-frequency, CSI300 top-K portfolio through Qlib (`finetune/config.py`: lookback 90, predict 10, train 2011–2022, test 2024-04 → 2025-06, hold 50 names), with no transaction cost in the demo. Its README says so: "a high-fidelity backtest should meticulously model transaction costs, slippage, and market impact." **Nothing in the repo is an intraday result, and nothing is net of cost.**

## 3. What the issue tracker says (all read 2026-09-28; none has a maintainer reply unless stated)

| Issue | What it establishes | Bearing on L38 |
| --- | --- | --- |
| **#354** Reproducibility report | Kronos-mini zero-shot on AAPL **daily** bars, 1,800 rolling forecasts (lookback 250/280, horizons 2/3/5 days, sample_count 3): close-price MAPE **12–22 % worse than a persistence forecast** in every configuration; direction accuracy **48.5–54.3 %**. | The right prior for zero-shot use. Note it measures level error, which persistence wins by construction when returns are near-zero-mean; L38 measures rank correlation with returns, which is the question that matters for trading and which #354 does not settle either way. |
| **#254** Short-horizon intraday question | 1-minute bars, lookback 240, horizons 3/5/10 bars, Kronos-small: as a filter it kept 4 of 37 trades, removing 27 losers and 6 winners; "too aggressive overall ... to justify hard live gating." Six days of data. | The only intraday evidence anywhere; too small to mean anything, and the author says so. |
| **#227 → PR #234** (merged 2026-04-13) | The **fine-tuning** dataset z-scored over lookback + horizon, so training targets leaked into normalisation. Fixed for fine-tuning. **#307** and **#277** ask whether the released checkpoints were retrained after the fix: unanswered. | Zero-shot `predict()` was never affected (normalisation on the lookback only, verified in the code above). It is one reason L38 is **zero-shot only**: fine-tuning on our sample would add our own selection risk to a pipeline that leaked until April. |
| **#199** "Data leakage during eval" | `MultiHeadCrossAttentionWithRoPE` sets `is_causal = self.training`, so in `eval()` the cross-attention is bidirectional. | **Read the code: no leak at inference.** The cross-attention (`DependencyAwareLayer`) is applied inside a window that contains only observed or already-sampled bars, and the loop reads logits at the last position only (`s1_logits[:, -1, :]`, `s2_logits[:, -1, :]`), for which a causal and a full mask are the same set of keys. It is a train/inference mismatch at interior positions, not access to future bars. L38's lookahead proof (stage 0) checks this empirically anyway. |
| **#265, #326** Training-data cutoff and coverage | Asked for the earliest/latest bar date and whether US equities are included. **Unanswered.** The paper says "45 global exchanges"; whether NSE bars are in the corpus, and through what date, is not public. | The contamination problem. Handled by date: L38 uses only sessions after a pinned model revision's publication date, and voids itself if no revision predates the window. |
| #352, #357 | Requests to train Large / collaborate. | none |

## 4. Independent literature on foundation models for returns (*snippet*)

- **2511.18578** (Rahimikia, Ni, Wang): off-the-shelf Chronos and TimesFM on daily excess returns; zero-shot R² of −2.80 % (TimesFM 500 M) and −1.37 % (Chronos-large); "portfolio returns from such models far inferior to benchmark ensemble models" (CatBoost, LightGBM); long-short results without transaction costs.
- **2606.27100**: TimeGPT, TimesFM-2.5, Moirai-2.0, Chronos, Chronos-2 on five US large caps; Diebold–Mariano rejects "no better than baseline" in 2 of the model×stock cells; conclusion: "useful practical priors ... not universal engines for statistically reliable alpha."
- Neither tests Kronos, which is the only one of these trained on bars rather than generic series. That is exactly the gap L38 measures, on the one market this project can trade.

## 5. The two Indian-market projects the search found

- **chandewardnyanesh/kronos-nse-terminal**: a terminal that runs Kronos on yfinance/Kite data and prints "sample numbers" (hit rate 63.4 %, Sharpe 1.47, P&L ₹12,840 on ₹1,00,000 over 60 trades). No cost model stated, no method, no data window, "educational and research purposes only." Not evidence.
- **georgiag7652/kronos-india**: README describes a Windows `.exe` that "connects to our servers ... to fetch stock prices and model updates" and asks users to click through the SmartScreen warning. **Do not install.** Not a source.

## 6. Feasibility measured here

Random-weight models of the published sizes, this container's 4 CPU threads, lookback 512 bars, `predict()` end to end:

| Model shape | Params | pred_len 6, samples 1 | pred_len 6, samples 5 | pred_len 12, samples 1 |
| --- | --- | --- | --- | --- |
| tokenizer (repo defaults) | 4.0 M | | | |
| small-sized (512 × 12 layers) | 35 M | 1.24 s | 4.75 s | 2.07 s |
| base (repo defaults, 832 × 12) | 102.3 M | 2.33 s | 10.63 s | 4.37 s |

Real Kronos-small is 24.7 M, so a little faster than the row above. `predict_batch` batches stocks and will amortise part of this. For L38 as pre-registered (≤ 100 stocks × 6 times × ~83 sessions ≈ 50,000 forecasts, pred_len 12, sample_count decided in stage 0), that is on the order of **30 CPU-hours at sample_count 1** on this machine, less on the Mac's GPU. Overnight-to-weekend work, never inside the engine.

## 7. Where the project's own constraints bite, and the decisions taken in the pre-registration

1. **The candle cache is not in this container** (`backend/data/*.db` is gitignored), so nothing was run against project data. The run happens on the Mac.
2. **The 2026 price held-out window (`splits.HELD_OUT_START` = 2026-01-02) is reserved** (reviewer Entry 7 §C). A "sessions after the model's release" sample would overlap it for eight months. L38 therefore uses **2025-09-01 → 2025-12-31 minus a 5-session embargo** as its selection sample and does not read 2026 at all. Confirmation, if the gate clears, uses sessions accruing after `UNSEEN_AFTER` (2026-09-20) or the held-out, which is the user's decision.
3. **Contamination is unresolvable from documentation**, so it is handled by pinning the Hugging Face revision and its commit date. If the earliest available revision post-dates 2025-09-01, the sample moves forward or the look is void. Recorded in the results file either way.
4. **Kite back-adjusts history as of the fetch date (#108)**, so spans fetched on different days can step where they meet. A 512-bar z-scored window straddling a step is an artefact. Stage 0 reports `kite_history.fetch_runs()` and requires one run for the sample.
5. **Zero-shot only, no fine-tuning** (section 3, #227).
6. **Persistence is not the comparator; the last hour's return is.** #354's MAPE test is the wrong question for trading. L38 tests whether the forecast *ranks* the next 15/30/60 minutes across stocks, and reports the partial IC after controlling for the last 60 minutes' return, so momentum in the lookback cannot be reported as a model finding.
7. **Heavy dependency.** torch and the Kronos package go into a research-only venv (`backend/research/requirements-kronos.txt`), never `backend/requirements.txt`; `tests/test_research_splits.py::test_no_live_module_imports_research` already guarantees the engine cannot import it. The reviewer's rules make a heavy dependency the user's call; the user's instruction on 2026-09-28 ("let's go with Kronos") is taken as that call, for research use only.

## 8. What would change the project's conclusion, and what would not

- **Gate clears** (quintile spread > 33.26 bp two-leg, t > 2, BH-corrected, both halves positive, partial IC survives): Kronos's forecast becomes a pre-registered *trial* candidate in the existing search harness with the 16.63 bp cost, then a review-queue describer. Not an automatic entry: §70 holds.
- **Gate fails**: the finding is that a bar-trained foundation model, zero-shot, does not rank NIFTY 100 intraday moves past cost either, which closes the "nonlinear ML on price" line next to §69's hand-coded one. That is a useful negative and the expected outcome.
- Nothing about L38 touches capital, horizon or instrument, which §76 identified as the real constraints.
