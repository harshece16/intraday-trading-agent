# Predictive tools sweep, 2026-09-29 — what else can be tested, now that a forecast harness exists

**Written 2026-09-29 to 30, while the Kronos look (L40) was running and before any statistic from it existed.** The owner asked for more predictive tools, libraries, agents and solutions that can be tested. Three research agents searched in parallel, each told not to redo the sweep of 2026-09-26 (`prediction-engine-sweep-2026-09-26.md`, 151 approaches), and to record for every candidate its licence, size, known leakage bugs and any independent out-of-sample evidence net of costs. Their full reports and machine-readable lists, with a source for every claim, are in `data/predictive-tools-sweep/`:

| Part | Scope | Candidates | Files |
| --- | --- | --- | --- |
| A | Time-series foundation models that fit the L40 harness | 26 | `predictive_tools_A.md`, `.json` |
| B | Finance ML libraries, model zoos, factor libraries, agent frameworks | 16 | `predictive_tools_B.md`, `.json` |
| C | India-specific tools, datasets and signals; anything new since 2026-09-20; practitioner reports | 13 | `predictive_tools_C.md`, `.json` |

Channels: Exa web search, the GitHub CLI (repository facts and issue trackers), the Hugging Face model API, and a page reader. Nothing was logged into. Reddit and X were reached only through Exa's index, so practitioner evidence is thin.

This is a list of candidates, not a result. No candidate was run. No look or trial is spent.

## The one finding that frames everything

**No candidate has independent out-of-sample evidence, net of costs, on intraday stocks, Indian or otherwise.** Every published finance test of these models is daily, gross of costs, and null or negative. The nearest evidence to this project's question is three outside tests of Kronos itself, all negative:

| Source | Setting | Result |
| --- | --- | --- |
| `sahil007123/kronos-nse-1d` (model card, 2026-07) | Kronos-small zero-shot, NSE daily, top 80 names, 100 held-out 2026 sessions | Rank IC −0.0116 (t −0.54); decile spread 0.046% against a ~10 bp round trip. 12-1 momentum on the same sessions: rank IC +0.0376 (t 3.51) |
| `neopentane7/kronos-candlecast` (pre-registered 2026-08-03) | Kronos-small zero-shot, NSE daily, 59 tickers, 708 windows | Forecast error (CRPS) 81% worse than a random walk; 80% intervals cover 41% |
| `ThomasCaruso/OpenAlpha` | Kronos-base zero-shot, four US ETFs, 1,600 forecasts | Beats "tomorrow equals today" on 0 of 4 |

These are daily, so they do not settle L40's intraday question. They lower its prior, and they belong in L40's results note.

Testing another model in the harness is cheap: each is a few lines of code and a couple of hours on the PC's GPU. That is the only reason to test any of them. The expected result for every one is a null.

## A constraint the sweep found: most new models are too new for the selection sample

L40's §2 requires the model's weights to predate the sample, so the model cannot have been trained on the prices it is examined on. The sample is 2025-09-01 to 2025-12-23. If the weights are later, the sample moves to start after them, and the look is void if fewer than 60 sessions remain before the 2026 held-out window.

Applied to the shortlist, by the release dates the sweep recorded (the exact revision dates are checked in each look's stage 0, as they were for Kronos):

| Model | First release | Can use the 2025 sample? |
| --- | --- | --- |
| Moirai 2.0 R-small | 2025-08-06 | Yes |
| Sundial base 128m | 2025-05-13 | Yes |
| TiRex v1 | 2025-05-26 | Yes |
| Chronos-Bolt | 2024-11-25 | Yes |
| TimesFM-2.5 | 2025-09-02 | Yes, on the moved window (about 77 sessions) |
| Granite FlowState-r1 | 2025-09-10 | Yes, on the moved window (about 72 sessions) |
| Chronos-2 | 2025-10-30 | **No**: about 37 sessions remain, under 60 |
| TiRex-2, Toto 2.0, Granite PatchTST-FM-r2, TimesFM-3.0 | 2026 | **No** |

The strongest current models are therefore untestable on the 2025 sample. They can be tested honestly only on sessions after their release: the 2026 held-out window, which is the owner's decision to spend, or the forward record the Kronos shadow began on 2026-09-30, which reaches 60 sessions around the end of December 2026.

## Ranked shortlist

### Test in the L40 harness, zero-shot (part A)

One pre-registered look for the family, not one look per model. Every model shares the harness, the sample, the features, the targets and the pass rule. The family's multiple-comparison correction covers models × three horizons, and it is fixed before the first run. Each model gets its own stage 0.

| Rank | Model | Licence | Why it is on the list | Handle |
| --- | --- | --- | --- | --- |
| 1 | TimesFM-2.5 (`google/timesfm-2.5-200m-pytorch`) | Apache-2.0 | The most-tested foundation model in finance; eligible on the moved window | Use `forecast()`, not the covariate path (open leak #338); guard flat windows that return NaN |
| 2 | Moirai 2.0 R-small (`Salesforce/moirai-2.0-R-small`) | CC-BY-NC, research only | Eligible; best average rank in the one five-stock daily comparison, gross | Close only (#224: accuracy drops with covariates) |
| 3 | Sundial base 128m (`thuml/sundial-base-128m`) | Apache-2.0 | Eligible; generative like Kronos, so the same sampling discipline applies | Pin transformers 4.40.1; fix seeds and sample count as L40 §2 |
| 4 | FlowState-r1 (`ibm-granite/granite-timeseries-flowstate-r1`) | Apache-2.0 | Eligible on the moved window; small and cheap | Record the `scale_factor` used |
| 5 | Chronos-Bolt / TiRex v1 | Apache-2.0 / NXAI community | Eligible; older versions of the two leading families | Chronos: fp32 or a build after 2026-09-08 (PR #532 precision bug) |

**Forward only, on sessions after their release:** Chronos-2, TiRex-2 (the cleanest multivariate OHLCV comparison to Kronos), Granite PatchTST-FM-r2, Toto 2.0, TimesFM-3.0 (non-commercial weights). The Kronos shadow's code can run them on the same live windows from any date, with a dated note first.

**Test with a change:** FinCast v1, the only other finance-pretrained model with public weights. Its checkpoint (2025-08-26) predates the sample, but its size and input format were not verified.

**Skip:** Time-MoE and Timer (stale or too large), Lag-Llama (open scaler bug #130 that a thin stock would trigger), MOMENT, UniTS and TOTEM (need training), TabPFN-TS (fits a curve on calendar features), TimeGPT (closed API; every window would leave the machine), TimeCopilot (an LLM agent choosing models), and every Kronos fork (all fine-tuned; one card shows the upstream fine-tuning script still normalised windows with the future included as of 2026-09).

### Test as its own pre-registered look, trained (part B)

**Qlib LightGBM on the Alpha158 factor set.** The project has never trained a model on its own bars; trials 41 to 116 were hand-coded rules, and the 2026-09-26 sweep rejected "ML on bars" on other people's evidence. This closes that gap with a number. Port the 158 expressions to five-minute bars, train one LightGBM per horizon on 2024-09 to 2025-08-15 with a five-session purge, freeze, and score at the six decision times on the L40 sample with L40's statistics. Prior: Qlib's own intraday benchmark earns 0.74 bp a period before costs; the only independent cost-aware test found a rank IC of −0.005; open issue #1668 says Qlib's published table does not reproduce. The deep models in Qlib's zoo add nothing in Qlib's own tables and several are broken or pinned to Python 3.6, so they are not separate looks.

### Later, each needing its own design and an owner decision

- **Intraday index timing from a factor library** (Aleti, Bollerslev and Siggaard, *Management Science* 2025). The only peer-reviewed intraday factor result found that is out of sample and net of cost: a SPY strategy with Sharpe 1.37 against 0.09. It times the index rather than ranking stocks, so it needs a new family; US only, no replication.
- **Cross-sectional overnight-gap reversal**, from an independent NSE repository (`ullasgh/nifty-intraday-quant-research`). The top decile of overnight losers reverses by −24.3 bp by 15:20 over 2018 to 2025, but by −9.6 bp in 2025 and −3.0 bp on continuously listed names. It cannot reach 33 bp inside an hour. At most one measurement look at 09:45 to close the line on record.
- **NSE bulk and block deal disclosures.** Uncovered by earlier sweeps. The literature is gross event studies where most of the move comes before the disclosure. One event look at the next open, only if the NIFTY 100 has at least 60 events.

### Skip, with the reason

- **LLM agent frameworks** (TradingAgents 0.5.x, ai-hedge-fund, FinMem, FinAgent, FinCon, FinGPT, AlphaAgent, RD-Agent). Independent audits find 50 to 72% of reported performance disappears after the model's training cutoff, and a search-aware evaluation from August 2026 rejects every LLM-discovered strategy net of costs. Their own trackers are still patching look-ahead leaks. The factor-mining agents would also multiply the trial count.
- **Order-book deep models** (DeepLOB, TransLOB, TLOB). Two independent benchmarks find they do not transfer to unseen data, and they need months of 10-level books. Revisit only if L37 clears and three months of depth exist.
- **DRL** (FinRL family, ViperQ), **StockFormer** (open whole-sample scaler leak), **Alpha101 libraries, tsfresh, featuretools** (no evidence; a multiple-comparison search), **GIFT Nifty** (price discovery only, no costed result), and the tools and systems with no record (kronos-nse-terminal, Warren Duffer, Nightwatch, vajra-quant).

## Corroborating negatives on the project's own instrument

- **`Vaunox/quant-intraday`**, a closed program on liquid NSE cash equities at 15-minute decisions with Kite: out-of-sample AUC 0.520 and a net CPCV Sharpe of −0.977 at a 17 to 21 bp round trip. It matches trials 41 to 116.
- **`rachitranka25/accuracy-illusion`** (2026-09-14), fourteen months of NIFTY, BANKNIFTY and FINNIFTY minute data: 0 of 86 rules survive correction, direction accuracy 50.4% per event against 71.5% needed to break even at 4 bp. Volatility is forecastable (68 to 74%), which matches the in-house verdict that volatility is a sizing input only.
- **A live vendor Nifty long-short** reports −25.25% for 2026 to 2026-09-25 after brokerage and taxes, against −11.44% for the index.

## One method worth adopting

The accuracy-illusion study shows that per-bar hit rates overstate their sample when calls persist and outcomes overlap; the effective count is n·E[L]/E[L²], about 6 per 69 forecasts in its data. The project's per-session rank IC is immune. Any per-bar share the dashboard shows is not, including the Kronos page's "share of forecasts on the scanner's side". That figure should be read as descriptive, never as evidence.

## What was not verified

Each part lists its own gaps. The main ones: speed per forecast on an 8 GB card for every model except Kronos; FinCast's size and inputs; whether Vibe-Trading's Alpha158 port runs on an arbitrary five-minute frame; whether Qlib's bin store accepts a five-minute NSE calendar; Reddit and X bodies, which were unreadable; and the exact Hugging Face revision dates, which each look's stage 0 would record.

## What this recommends

1. **Let L40 finish and report first.** If Kronos fails, the prior for its family falls further, and the owner can decide whether a family look is still worth two hours of GPU.
2. **If the owner wants more tested,** write one pre-registration for the zero-shot family (TimesFM-2.5, Moirai 2.0, Sundial, FlowState, Chronos-Bolt, TiRex v1) on the L40 sample, and a separate one for Qlib LightGBM with Alpha158.
3. **For the 2026 models,** extend the Kronos shadow to run them forward from a dated note, and judge them only after 60 sessions.
4. **Nothing here goes near the engine** without the gate, a trial and confirmation, as for Kronos.
