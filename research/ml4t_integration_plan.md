# Machine Learning for Trading — what actually integrates, and what doesn't yet

Source: [stefan-jansen/machine-learning-for-trading](https://github.com/stefan-jansen/machine-learning-for-trading),
3rd edition (27 chapters; the `ml4trading.io/second-edition/chapter/1/` link
given serves the 2nd edition of the same book — read alongside the current
3rd-edition repo, since GitHub had already moved to the 3rd). Read: the
top-level README in full, and the chapter READMEs for ch1 and ch27 in full.
The remaining 25 chapters were surveyed by directory/notebook name and their
one-line descriptions in the top-level README, not read notebook-by-notebook
— see "What I didn't do" at the bottom.

## The one finding that matters most

Chapter 1 is titled **"The Process Is Your Edge"**, and chapter 27 — the
book's closing argument — repeats it in almost the same words:

> "the most important lesson of the book transcends any individual
> technique: process is the durable edge, not any single strategy."

That is the correct frame for this project right now. We have roughly a
week of forthcoming paper-trading data and, at most, a few dozen trades
(the backtests over 55 days produced 6–19 trades with the current
checklist). None of the book's model chapters — gradient boosting, deep
time series, latent factors, autoencoders, GANs, reinforcement learning —
are meant to run on a dataset that small. Using them anyway would not add
skill, it would fit noise and then confidently mislead. So the honest
"integration" this week is the *process* chapters, not the *model* chapters.

## What's already built, mapped to the book's workflow

| Book concept | Chapter | Already in Trader Sahab |
|---|---|---|
| Point-in-time-correct data, no look-ahead | ch1 (workflow), ch2 | `data_provider.py`'s UTC→IST fix; the backtester's `window = candles[:i+1]` no-lookahead slicing |
| The evidence boundary (exploration vs. confirmation) | ch1 §1.2 | New this session: `evaluation.log_trial()` counts every backtester.py run as a trial; `database.py`'s point-in-time snapshots mean nothing gets relabeled with hindsight |
| Alpha factor research, Information Coefficient | ch4 (2nd ed.) / factor work throughout | New this session: `database.factor_ic()` — rank correlation between a scan-time score and the stock's next-session move |
| Strategy evaluation, correcting for multiple testing | ch5 (2nd ed.) / ch19, ch27 | New this session: `evaluation.deflated_sharpe_ratio()` (Bailey & López de Prado), reported by the backtester alongside expectancy and Kelly |
| Regime awareness | ch1 §1.4 (`factor_regimes`, `macro_regimes`) | The scanner's risk-on/neutral/risk-off market bias is a hand-built version of the same idea, without the AQR/FRED datasets the book's notebooks use |
| Risk management as a dedicated stage | ch19 (new in 3rd ed.) | `risk_manager.py` (Tharp's Percent Risk / Percent Volatility models), daily loss limit, position caps |
| Transaction costs as a dedicated stage | ch18 (new in 3rd ed.) | `costs.py`, applied in every backtest |
| Live trading, kill switches | ch25, ch26 | `kite_broker.py`, the daily loss limit and max-open-positions caps are a crude circuit breaker; no drift detection yet (see below) |

## What a week of logging actually buys us

`database.py` now logs every scanner run and every live checklist read, not
only trades — because the checklist is deliberately strict, executed trades
will stay rare (single digits per week), but checklist *reads* on the
5–6 active-watchlist stocks happen roughly every 30 seconds during market
hours: on the order of a few thousand rows a week. That's still small by
ML4T standards, but it's enough for the two techniques already wired up:

1. **Information Coefficient** (ch1, Grinold's fundamental law of active
   management) — does the scanner's `final_score` actually rank stocks by
   what they do next? `database.factor_ic()` computes this and honestly
   returns "not enough data" below 20 session-pairs.
2. **Deflated Sharpe Ratio** (Bailey & López de Prado, cited in ch1's
   references) — corrects for the fact that we've already run many backtest
   configurations this week (strategies, entry modes, universes,
   intervals); `evaluation.py` counts every `backtester.py` invocation as a
   trial and reports the probability the result beats pure luck at that
   trial count, not just its raw Sharpe ratio.

## What's a reasonable next step, once there's more data — and what isn't yet

**Reasonable within a few weeks**, once dozens of closed trades and
thousands of checklist reads exist:
- A simple, linear model (ch7-equivalent: logistic regression) predicting
  P(target before stop) from the checklist's own features (bull/bear score,
  volume ratio, gap, catalyst score, pattern present/absent) — this is
  meta-labeling in López de Prado's sense, layered on top of the existing
  rule-based direction call rather than replacing it. `database.py`'s
  `checklist_json` snapshots already carry every input this would need.
- Formal walk-forward cross-validation in the backtester (train on one
  block of sessions, test on the next, roll forward) once there are months,
  not weeks, of history — Kite's historical API is the practical source
  once that subscription exists.

**Not reasonable yet, and why:**
- **Gradient boosting / deep time-series / latent-factor / autoencoder
  models (ch9-14)** need thousands to millions of labeled examples across
  many assets; a week of one desk's paper trades isn't in range.
- **NLP beyond the current lexicon (ch10 text features, topic modeling,
  RAG/knowledge graphs, ch22-23)** need a large corpus of *historical*
  labeled headlines to validate against — we don't have one archived yet,
  since news is fetched live and not currently retained beyond the 15-minute
  cache. (Worth logging headlines going forward if this becomes a priority.)
- **Reinforcement learning for execution/hedging (ch21)** assumes an agent
  gets many episodes to learn from; at a handful of trades a week, an RL
  policy would never see enough episodes to learn anything but noise.
- **Synthetic data / GANs (ch5, ch20)** exist to substitute for short real
  histories in *deep learning* pipelines. Our actual bottleneck isn't
  realism, it's volume for a rule-based system already grounded in real
  trades — synthetic data doesn't fix that.
- **Autonomous multi-agent research systems (ch24)** — interesting for
  scaling research across many hypotheses at once, but premature before a
  single hypothesis (the Varsity checklist) has been evaluated honestly.

## Concrete plan for the paper-trading week

1. **Trade paper money only**, as already running. Every scan, checklist
   read, and fill is now logged automatically — no extra step needed.
2. **Don't change `trader_brain.py`'s thresholds mid-week.** Per the
   evidence boundary, this week's run should be a sealed evaluation of the
   current checklist, not another tuning trial. If a bug is found and fixed,
   that's fine (bugs aren't "the strategy"); tuning the entry threshold
   because a trade lost is what breaks the boundary.
3. **At the end of the week**, read `/api/journal/summary` (or the
   dashboard's Journal tab): the Information Coefficient, the Deflated
   Sharpe Ratio, and the checklist-item breakdown (which of pattern / S/R /
   volume / trend / indicators / catalyst / RRR actually separated winners
   from losers). That breakdown, even on a dozen trades, is a legitimate
   first look — treat it as a hypothesis for the following week, not a
   verdict.
4. **Only after a few weeks of this** does a linear meta-labeling model
   (see above) become a reasonable next step, and only on trades outside
   whatever week generated the hypothesis being tested (a fresh holdout).

## What I didn't do

- Did not read the 3rd edition's notebooks chapter-by-chapter; that's
  25+ Jupyter notebooks of Python/Polars code, most of it deep-learning
  architecture (PatchTST, TCN, Mamba, autoencoders, GANs) that has no
  honest use case against our current data volume. Surveyed the README and
  the ch1/ch27 chapter READMEs, which state the book's own thesis directly.
- Did not install PyTorch, LightGBM, or any ML framework — nothing in this
  system currently needs one, and adding heavy dependencies before there's
  a concrete model to run them would be premature.
- Did not attempt regime detection via GMM on AQR/FRED datasets (ch1) —
  those are US factor/macro datasets not obviously mapped to NSE
  intraday equities; the scanner's existing risk-on/off bias is the
  low-cost equivalent for now.
