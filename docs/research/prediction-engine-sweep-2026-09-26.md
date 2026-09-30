# Prediction-engine sweep, 2026-09-26 — is there a prediction engine worth building for 2026 intraday or F&O?

**The owner's question:** "go to GitHub, Reddit, Instagram, Twitter … and see
the best prediction engine we can build for 2026 intraday or F&O trading
which guarantees the profit."

**The answer:** no engine guarantees profit, and none of the 151 approaches
logged across eight sweeps shows a verified net profit from *predicting*
Indian intraday or F&O prices. What is genuinely predictable is
**volatility**, not direction, and the price of volatility (India VIX) is
already the market's best forecast of it. The one design that survived two
rounds of adversarial review (an overnight Nifty-ETF hold with a nightly
gate) then failed a completeness check on facts verified directly: its exit
auction does not exist for that ETF, and after the cost of capital its
recent-years edge is not significant. **Nothing is built; no trial is
spent; the held-out window is not opened.**

This file records no trial and no research look. It was produced by a
35-agent workflow (six platform sweeps, two direct re-sweeps after the owner
logged in, a merge into 12 approach families, two adversarial verifiers per
family, a design stage and a completeness critic), plus direct checks by the
main session. The companion `literature-sweep-2026-09-25.md` covers the
general literature; this one covers prediction engines specifically.

---

## 1. How it was gathered, and what it could not reach

| Platform | Access | Coverage |
| --- | --- | --- |
| GitHub | `gh` (authenticated): 55+ searches, READMEs, issue trackers (Kronos ~300 issues, TradingAgents ~600, FinRL ~1,200) | Full |
| Reddit | First via Exa's index (31 threads in full), then **direct through OpenCLI with the owner's logged-in session**, read-only (≈45 more threads with comments, user post histories for follow-ups) | Good |
| Instagram | Exa's index of captions; then OpenCLI direct: account search worked, post reads mostly failed (HTTP 429, HTML instead of JSON) | Partial |
| X / Twitter | Exa and search snippets only — **not logged in**, no thread read in full | Weak |
| Research | Exa search + full text where not paywalled; arXiv, SSRN, NSE/SEBI documents | Good until Exa's free tier rate-limited (HTTP 429) around 11:50 IST |
| Rules and data | SEBI/NSE circulars, Zerodha docs, broker APIs, data vendors | Good |

Every agent used read-only commands only. No login was automated, no
cookie was read, nothing was posted, liked or followed.

---

## 2. What each platform showed

**GitHub.** The most-starred engines (TradingAgents 109k stars, Kronos 39k,
FinRL 16k, DeepLOB) have issue trackers full of leakage bugs (Kronos #227,
FinRL #938, TradingAgents #1007) and irreproducible papers. Tested after a
model's release they are a coin flip: Kronos called NSE index direction
right 49.3% of the time over 1,047 sessions; a user's live ETH fine-tune was
measured by commenters at −11.87%, later −67%. The honest repos agree with
this project: an ML trade filter on Nifty weekly option selling did not beat
simply trading every day (Romano–Wolf p 0.21–0.32). Recurring red flags:
75–97% win rates with no costs; the final model fitted on the year called
out-of-sample; slippage charged on P&L instead of on notional.

**Reddit.** The best posts are negative and well built: a 21-year NSE
panel including delisted stocks found the opening-range breakout makes
+7.87 bp gross and **−12.47 bp net, positive in 0 of 10 years**; a
pre-registered ledger of 155 strategies found intraday ATM Nifty option
buying negative in **all 78** cells. Every "Day N" bot journal followed up
by the direct sweep (Tyson-Jod, Chennai_data_guy, TastyTrading,
lightWeightFounder) went quiet or restarted within one to three weeks;
Tyson-Jod retracted his first week as a logging bug. The P&L commenters
trust comes from **selling option premium** and **slow momentum**, not from
predicting direction.

**Instagram.** A sales funnel: sureshot/jackpot tip groups, "AI" indicators
claiming 92–99% accuracy, option-chain "prediction for tomorrow", account
handling. No account showed a SEBI RA number together with a net-of-cost
record. The only regulator-verified numbers attached to the platform's
largest trading personalities are losses (Baap of Chart lost ₹2.89 Cr on
his own account; 186 of Avadhut Sathe's students lost ₹1.93 Cr in six
months).

**X.** A loud layer sells "AI predicts the future" and single-day Sensibull
P&L cards; a quieter practitioner layer says ML direction calls at intraday
horizons are noise after costs and that 0DTE premium selling has been
decaying since 2023. This is the weakest-covered platform.

**Research.** Every family collapses once costs are counted: time-series
foundation models' long–short Sharpe goes from 6.44 to −3.62 at 20 bp;
Krauss et al.'s daily ML stat-arb nets −18%/yr over 2010–15; NSE
order-imbalance predictability "perishes within thirty minutes".
Volatility is predictable out of sample (R² 0.4–0.58), but a HAR forecast
does not beat India VIX, which is the price an option seller is already
paid.

**Rules and data.** SEBI's FY26 study (reported by the sweep; the exact
figures were not re-verified here) found 87.7% of individual F&O traders
lost money, while almost all prop and FPI gross profit went to algorithmic
entities with colocation and scale. Since 1 Apr 2026 API orders need a
static IP; self-built algos under 10 orders a second need tagging, not
registration; advertising accuracy percentages or assured returns is
penalised. Kite gives 5-level depth, no history for expired options, and
daily candles only for expired futures.

**The two most-cited "verified" wins fell apart when read in full:** the
Groww page of the "117% in 37 days" LLM option system shows +₹5,114 net,
before a ₹34–44k/month AI bill; the ₹5.96 Cr Sensibull "option seller" made
the money in MCX gold and silver while losing ₹6.16 L in F&O.

---

## 3. Scoreboard — 12 approach families, two adversarial verdicts each

Verdicts are *evidence lens / applicability lens*. Cost hurdles: cash
intraday 16.6 bp round trip; Nifty futures ~6–7 bp (+~2.5 bp nightly
premium decay if held overnight); index options ~72 bp of premium at one
lot (26–29 bp at 10–20 lots per order).

| Family | Best evidence found | Verdicts | Status |
| --- | --- | --- | --- |
| Order-book microstructure | OOS with costs: every taker test loses; maker +0.36 bp/trade needs rebates | not supported / not supported | Let L37 run as pre-registered (amended today); expect a fail |
| ML on OHLCV bars | ~300 live trades, 70% losers; best OOS test ≈ random null | refuted / not supported | Reject (repeats trials 41–116) |
| Time-series foundation models | OOS with costs, negative | refuted / refuted | Reject |
| LLM agents and sentiment | Broker-verified: +₹5,114 before the AI bill | refuted / not supported | Reject |
| Deep reinforcement learning | Paper, US weekly, t ≈ 1.2 | refuted / not supported | Reject |
| Option-chain positioning (OI, PCR, max pain, GEX) | Forward-graded max pain lost to "no move" | refuted / not supported | Reject as signals |
| Short premium (variance risk premium) | Premium real (IV − RV +1.96 vol pts, t 3.76); no net-positive OOS record | not supported / not supported | Would need option-chain fills data first; outside today's mandate |
| Volatility forecasting | Forecast skill real (R² 0.4–0.58); P&L conversions fail | not supported / not supported | Sizing input only |
| Rule/indicator intraday, option buying | OOS with costs, negative | refuted / refuted | Reject (done here 117 times) |
| Overnight drift and gaps | In-house +9.8 bp/night gross, t 11.5 | not supported / plausible untested | See §4 — fails the completeness check |
| Flow and calendar (last-30-min momentum, auction) | In-sample, gross | refuted / not supported | Reject (L32 measured +0.70 bp here) |
| Slow cross-sectional (momentum, low-vol) | Live NAV: momentum fund ≈ its parent index, twice the drawdown | refuted / not supported | Reject as an engine (trial 119) |

---

## 4. The one design that survived review, and why it still isn't built

**The design.** Hold a Nifty ETF (NIFTYBEES; SETFNIF50 as replication)
overnight only: buy 15:20–15:29, sell in the 09:00–09:08 pre-open auction.
Each afternoon a ridge regression on five fixed features (change in FII
index-futures positioning, change in near-expiry PCR, VIX² minus a HAR
forecast, the open-to-15:20 return, night length) predicts whether
tonight's hold is worth its cost; hold only if the net-of-cost prediction
exceeds 1 bp. ETF charges are 2.4–2.7 bp at ₹5–25 L (futures would cost
~9.2 bp including nightly premium decay, so they are out). H1: always-hold
beats zero; H2: the gate beats always-hold.

**Why it isn't built — the completeness critic's findings, the first one
verified directly:**

1. **The exit auction does not exist for this ETF.** NSE's pre-open
   snapshot for 2026-09-25 09:08 lists 2,147 securities, including gold and
   silver ETFs, but **not NIFTYBEES or SETFNIF50** (re-fetched and checked
   by the main session today). The exit is therefore the 09:15 continuous
   market, whose first NIFTYBEES prints sat on average 17.5 bp away from the
   index-implied move on the sessions sampled — larger than the edge. The
   bhavcopy OPEN is not a tradable exit price.
2. **Cost of capital.** Holding ₹5–25 L overnight gives up about 2.5 bp a
   night in interest. On the project's own index figures at 3.5 bp cost:
   2009–25 nets 4.2 bp after it (t 4.7, barely over the corrected gate);
   **2023–25 nets 2.7 bp (t 1.3); 2025 is −2.2 bp.**
3. **The market changed under the data.** The closing auction (since
   2026-08-03) ends continuous trading in the ETF's underlying at 15:15 while
   the ETF trades to 15:30; the pre-open was restructured on 2026-09-07. All
   training data is from the old regime.
4. **Power.** H1 is the already-measured overnight premium, not a fresh
   test. H2 needs a prediction R² of about 5% at the project-wide trial
   count (2.7% at family level) — above the best intraday R² ever published
   (2.9%, Baltussen et al.).

**Verdict:** the overnight line stays closed unless the owner changes the
mandate (overnight delivery holds are outside the intraday scope) *and* a
stage-0 check measures a tradable 09:16–09:20 exit cost small enough to
leave an edge. That check computes no returns and spends no trial.

---

## 5. What this changes

- **The order-book test (L37)** keeps its gate but was amended before any
  data was read: horizons must end by 15:08, only stocks sampled through the
  whole session count, the partial first session is excluded, and a fail
  will not be reinterpreted as "needs deeper data".
- **No prediction engine is added to Trader Sahab.** Automatic entries stay
  off behind the evidence gate; the review queue remains the trading path.
- **Owner decisions this leaves open:** (1) whether overnight ETF delivery
  holds are in scope for the agent at all; (2) the family-level versus
  project-wide trial count (also pending for 3h); (3) whether to buy options
  data (Dhan ₹499/month or ICICI Breeze, free) to study option-premium
  selling, the only family with a real, measured premium — which is a
  risk-premium business, not prediction.
- **Candidates the critic named that were not covered:** index-rebalance
  (passive-flow) events — the repo already holds 894 NIFTY 100
  inclusion/exclusion events in `backend/research/data/nifty100_changes.csv`
  — and the audited records of Indian systematic funds (APMI PMS returns,
  CRISIL Category III AIF benchmarks).

## 6. Provenance

Workflow runs `wf_9c71500e-bc1` (edge map, 22 agents) and `wf_de5a9d1e-2d4`
(this sweep, 35 agents), 2026-09-26. Per-agent outputs were saved in the
session scratchpad; the numbers above are theirs unless marked as verified
by the main session. Held-out reads made by either workflow are logged in
`trials.md` → "Held-out exposure log".
