# Ideas from the reels (2026-09-28) — what each one is, where it would plug in, and what it is worth here

The owner shared 14 Instagram screenshots: Kronos, TradingAgents, a
"price range" reel, Awesome Systematic Trading, Agent-Reach, OpenAlice /
"Krypt Trader", a set of Claude Code dev tools (Ponytail, Graphify, RTK,
UI UX Pro Max), and a gamified habit tracker. This note says, for each,
what the thing actually is (fetched from its own repo where the proxy
allowed it, not read off the screenshot), what Trader Sahab already has,
how it could be wired in, and how much it would be worth.

**Read this against where the project stands.** README §69–§76: 119
trials, every price-only entry rule at ≈ 0 R before costs, the Varsity
checklist retired as decision-maker (§75), automatic entries held at zero
by the evidence gate (§70), the review queue as the trading path (§64),
the order book as the one open intraday line (§71, pre-registered as L37),
and the literature sweep's conclusion that the question at this capital is
horizon and instrument, not the rule (§76). Real balance ₹5,500; paper
capital ₹1,00,000. Nothing below changes that conclusion, and the note
says so where it matters.

## Verification status

| Source | Fetched | Notes |
| --- | --- | --- |
| shiyu-coder/Kronos README | yes (github.com) | The arXiv paper (2508.02739) and the Hugging Face model card are blocked by this session's egress proxy, so the paper's own numbers are **not** quoted here. |
| TauricResearch/TradingAgents README | yes (raw) | Already integrated (§41, §44); re-read for completeness. |
| Panniantong/Agent-Reach README | yes (raw, Chinese original) | |
| wangzhe3224/awesome-systematic-trading | yes (github.com) | Already read for the 2026-09-25 literature sweep. |
| TraderAlice/OpenAlice README | yes (github.com) | |
| rtk-ai/rtk, Graphify-Labs/graphify, Ponytail | web search only | Dev tooling, not trading; claims are the vendors' plus one independent Ponytail test. |
| careerintrading.in "price range concept", thedashbit habit tracker, thequantbros "1 lakh / 3 trades" | screenshot only | No repo, no numbers shown. The thequantbros reel shows a Kronos setup but no result frame. |

---

## 1. Kronos — an open-source foundation model for candlesticks

**What it is (README).** "The first open-source foundation model for
financial candlesticks (K-lines), trained on data from over 45 global
exchanges." A BSQ tokenizer turns OHLCV bars into discrete tokens; a
decoder-only Transformer is pre-trained on them. Open weights: mini
(4.1M params, 2048 context), small (24.7M, 512), base (102.3M, 512);
large (499M) is not released. `predict(lookback, pred_len, sample_count,
T, top_p)` returns sampled future bars. MIT. The README's example is a
5-minute Shanghai stock file; the live demo forecasts BTC/USDT 24 h ahead.
**It reports no net-of-cost result**, and its own backtest section says the
demo is "not a production-ready quantitative trading system" and that a
real backtest "should meticulously model transaction costs, slippage, and
market impact." Its training corpus is described only as "45+ exchanges";
whether NSE 2024–2026 bars are in it is not stated.

**What we already have.** 495 sessions of NIFTY 100 5-minute bars in the
Kite cache (`kite_history.py`, §50), a per-session rank-IC harness with
the t ≥ 2 bar (`database.factor_ic()`, `research/step2_feature_ic.py`),
and a pre-registered gate template for "does feature X predict the next
15/30/60 minutes past 16.63 bp" (`docs/research/prereg-orderbook.md`).

**Why it is not just another indicator, and why it probably still fails.**
§69's finding is that hand-coded functions of NIFTY 100 bars carry nothing
before costs. Kronos is a different function class: nonlinear, pretrained
across markets. That is a real, distinct hypothesis. It is also the exact
item the literature sweep lists under "consistently reported as NOT
working": "ML on price alone" (sweep §4), with qlib's LightGBM as the
best-documented case at IR 2.00 gross → 1.44 with cost, backtest only,
no live record (sweep §1). The prior is poor, but one clean measurement
closes it, and closing it is worth something given how often this idea
will keep arriving in reels.

**How to integrate — as a research look, never as an engine change.**

1. Pre-register `docs/research/prereg-kronos-feature-ic.md` (research
   look L38, after L37 runs). Feature: Kronos-small's mean forecast of the
   close `pred_len` bars ahead minus the last close, in bp, from a 512-bar
   (≈ 7 session) lookback, sampled at fixed times (e.g. every 15 min from
   09:45), for the 25-stock watchlist or the scanner's top 20. Targets and
   gate copied from the order-book prereg: signed return to +15/+30/+60
   min from the next bar's open; quintile spread must clear 16.63 bp
   single-side with t > 2 across ≥ 15 sessions, Benjamini–Hochberg across
   the horizons.
2. **Contamination rule, fixed now.** Because the pretraining corpus is
   undisclosed, only sessions after the model's public release (paper
   August 2025; take 2025-09-01) count. That leaves roughly 250 sessions
   of the cache, split first half / second half as every other test here.
   No fine-tuning on any session the look is measured on.
3. Run it in `backend/research/`, with `torch` and the Kronos package as
   research-only dependencies (a `requirements-research.txt`), never in
   `backend/requirements.txt`, so the engine and CI stay unchanged. CPU
   inference of a 24.7M-param model on ~20 stocks × ~24 samples/day × 250
   sessions is ~120k forward passes; feasible overnight on the Mac,
   nothing that belongs in the 30 s tick.
4. If the gate clears, it becomes a pre-registered trial in the existing
   `strategy_search.py` harness with the same costs, and only then a
   review-queue describer, never an automatic entry (§70 still holds).

**Benefit.** Low probability of a positive, but the highest information
value of anything in this batch: it is the one idea that is genuinely new
information relative to the 119 trials (a different model class on the
same bars), and it reuses every harness the project already has. The
reel's framing — "paper capital 1 lakh, max 3 trades per day" — is the
"max trades" framing §39 already rejected; the reel shows no result.

**Cost/risk.** A day of setup, a night of compute, no product change.
Risk is only wasted time, and the contamination rule above is the thing
that keeps the result honest.

## 2. TradingAgents (and the ITN "AI rebuilt a Wall Street firm" reel)

Both reels are the same repo: TauricResearch/TradingAgents — four
analysts, a bull/bear debate, a trader, a risk team, a portfolio manager,
explicitly for research and simulated exchanges only.

**Already integrated**, twice: §41 took the one deterministic piece
(fundamentals scoring), §44 built the whole desk as `research_desk.py`,
on the Research desk tab, with three rules the original does not have:
it cannot reach an order, every statement must cite the snapshot or is
dropped, and its rating carries no weight until `research_rating_ic()`
passes t ≥ 2 over 20 sessions of 20+ rated stocks. It reads "0 of 20
sessions" because the desk is off by default and runs on demand.

**The only open item is the measurement, and it has a price.** One brief
measured at $0.32 and 110 s (§44). Rating 20 stocks a session for 20
sessions is 400 briefs ≈ $130 ≈ ₹11,000 — twice the real account — to
learn whether an LLM debate ranks tomorrow's movers. Against §73/§74
(even official filings and filed profit numbers are priced by the open),
the prior for a news-and-fundamentals read predicting the next intraday
session is poor. **Recommendation: nothing to build.** If the owner wants
the IC read, a cheaper design is analysts-only (Haiku) ratings, but that
measures a different signal than the desk's rating and would need its own
pre-registration. Do not run it at the ₹5,500 balance.

## 3. "Price range concept" (careerintrading.in)

**What it is (screenshot).** Range trading: mark the range's high and low
(the shaded supply/demand boxes), fade the extremes, target the far side.
The chart's time axis runs 12:00–21:00, so it is a 24-hour FX/crypto
chart, the same transfer problem §72 found with the Smart Money setup.

**Already here.** `market_structure.structure_trend()` labels a "range"
regime; `key_levels()` clusters swing turns into zones with touch counts;
the scanner has NR7 / inside-day compression; the checklist's "location"
item scores distance to zones; the S/R rule was inside the 76-config
search (§69). The nearest tested cousin, order blocks + sweeps (§72,
trial 117), lost −0.299 R with 4.7 % of trades reaching 2R.

**Integration path, if the owner wants it counted.** One pre-registered
trial in `strategy_search.py`: range = no new swing high/low for N bars on
15m, entry on a 5m rejection bar at the range edge, stop beyond it, target
the opposite edge, costs at 16.63 bp. That is a day of work and one more
trial against the DSR count.

**Benefit.** Lowest in the batch. It is a price-only 5m rule on NSE cash,
the class 119 trials have already measured at zero before friction.
Recommendation: skip unless the owner wants trial 120 for the record.

## 4. Awesome Systematic Trading

A curated directory (libraries, strategies, books, papers). **Already
used**: the 2026-09-25 sweep took its own replication statistic (median
replication Sharpe 0.37; 48 % clear t = 1.96 over 4,843 coded papers).
Nothing here is a product change. The one concrete thing the reel's
author is visibly using — the "Nautilus – Trading Control Room" tab is
nautilus_trader, an event-driven backtest/live engine on the list — would
be a rewrite of `backtester.py` and the engine for no evidence gain; the
project's harness already models the costs the shipped demos do not.
Recommendation: bookmark; nothing to do.

## 5. Agent-Reach

**What it is (README).** A CLI plus a SKILL.md that gives any
command-line agent (Claude Code, Cursor, OpenClaw…) read access to
YouTube subtitles and search (yt-dlp), Reddit (login state via OpenCLI or
rdt-cli with cookies — "no zero-config path; the anonymous endpoints are
blocked"), X/Twitter (user-exported cookies), Xiaohongshu, Bilibili,
Facebook, Instagram, LinkedIn, Exa semantic search and Jina Reader. Free.
Its own README warns of **account bans** on cookie-based platforms and
tells you to use a throwaway account.

**Where it could plug in.**

- *As a research tool for the sessions that build this repo:* the
  literature sweep's Reddit section was done by hand (12 threads in
  full, ~55 by title). Agent-Reach would make the next sweep, and any
  future "test this reel" request, cheaper. Zero product change; install
  on the Mac, not in the repo.
- *As a signal:* social mentions are the one information source besides
  the order book that no trial has used. But Agent-Reach reads live, it
  has no archive, so a test needs weeks of collection first (the same
  path as `depth_samples`), and the prior is worse than for filings:
  §73 found even official filings do not clear the cost and §74 found
  filed results are priced in the overnight gap. Social chatter arrives
  later and noisier than both. Using the owner's own X/Reddit cookies for
  scripted reads also risks those accounts.

**Benefit.** Moderate for research productivity, ≈ 0 for P&L.
Recommendation: install as a dev tool with a burner account if the owner
wants faster sweeps; do **not** wire it into `news_sentiment.py` or the
engine, and do not start a collection until L37 (order book) has reported.

## 6. OpenAlice / "Krypt Trader"

**What OpenAlice is (README).** "Your one-person Wall Street": a local
workspace that connects coding agents (Claude Code, Codex, OpenCode, Pi)
to market data, research workspaces, scheduled tasks and trading accounts
through a "Unified Trading Account". No Indian broker is named. AGPL-3.0.
"Trading execution is beta. Start with simulator, paper, demo, or testnet
accounts." "…provides no guarantees of correctness, reliability,
profitability, or loss prevention." **No P&L record is published.** The
reel's caption ("will make u money") is the reel's, not the repo's.

**Overlap.** It is the generic, multi-asset version of what this repo
already is, minus everything that makes this one measurable: Kite, NSE
costs (`costs.py`), the journal, IC/DSR gates, the evidence gate, the
kill switch. "Krypt Trader" in the Instagram search result sits in a
tool pack next to a location spoofer and "LARP" tools; not a source.
Recommendation: nothing to integrate.

## 7. Claude Code dev tooling: Ponytail, Graphify, RTK, UI UX Pro Max

These are about the cost of the sessions that build the repo, not about
trading.

| Tool | What it claims | Independent check | Fit here |
| --- | --- | --- | --- |
| RTK (rtk-ai/rtk, MIT, Rust) | CLI proxy that compresses git/pytest/npm/docker output 60–90 % before it reaches the model; a Claude Code hook rewrites Bash calls | Widely used; no contrary report found | **Best fit.** Sessions here run pytest, npm build and git constantly. Check the hook does not rewrite the `lsof -i :8000` / uvicorn commands CLAUDE.md relies on. |
| Ponytail | Minimalism rules skill; maker: 54 % fewer LOC, 22 % fewer tokens | One 80-task test: 15 % fewer LOC, 10 % lower cost | Marginal; CLAUDE.md already enforces minimal, evidence-backed changes. |
| Graphify | AST knowledge graph skill; "up to 70x" on 500+ file projects | Vendor claim | Repo is ~14k lines of Python plus a small React app, under its own threshold. Skip. |
| UI UX Pro Max | Design skill | Not researched | The dashboard has a settled style (§59, §63); skip. |

**Benefit.** Modest dev-cost saving, zero P&L. Recommendation: try RTK
on the Mac; leave the others.

## 8. The gamified habit tracker (thedashbit)

**What it is (screenshot).** A daily grid — one row per habit, one cell
per day — with streaks and a monthly summary, built as a game.

**Why it fits, and why it is the one UI idea worth building.** Since §75
the human is the decision-maker: setups arrive as review-queue cards and
the owner approves or rejects. The Dimaag Scorecard grades the *system*;
nothing grades the *operator*. SEBI's FY23 cash-intraday study
(`research/findings_verified.json`, E24b) is the population evidence for
what kills retail accounts: 71 % lose, 80 % of those with >500 trades a
year, and loss-makers spend 57 % of their losses on costs. Overtrading and
rule-breaking are measurable per day, they need no forecast, and they are
what a streak grid rewards.

**Integration.** A `database.operator_discipline(days=30)` query over
`trades`, the review-queue decisions (§68 saves the counterfactual) and
`activity`, returning per-session booleans such as:

- no trade outside the entry window or after the daily loss limit;
- no approval on a card whose one failed gate was R:R or cost (§46);
- size ≤ 1 % risk and ≤ the notional cap on every fill;
- the close summary (§56) was read (a simple "acknowledged" click);
- zero trades on a day the scanner's market filter said stand aside.

Rendered on the Journal page as the grid with per-rule streaks and a
30-day summary; a `GET /api/journal/discipline` route behind the usual key.
About a day of work, a test on a fixture journal, and a README section.
No gate, no weight, no prediction: it measures, like `session_summary`.

**Benefit.** Moderate for process, the only kind of benefit available at
this capital. Recommendation: build it.

## 9. "Paper capital 1 lakh, max 3 trades per day" (thequantbros)

Already the configuration: `paper_capital` ₹1,00,000,
`max_open_positions` 3, `max_entries_per_day` 1 per stock, daily loss
limit 2 %, one position per sector. The "how many trades" framing was
answered in §39. Nothing to change.

---

## Ranking

| # | Idea | What it would add | Evidence today | Effort | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1 | Discipline grid (habit tracker) | Measures the operator, the decision-maker since §75 | Population evidence (SEBI FY23); no forecast needed | ~1 day | **Build** |
| 2 | Kronos as feature-IC look L38 | A new model class on the bars; closes the "ML on price" question | README: no net-of-cost result; sweep prior negative | 1 day + overnight compute | **Pre-register, run after L37** |
| 3 | RTK | Cheaper build sessions | Widely used | 1 hour | Optional |
| 4 | Agent-Reach | Faster literature/social sweeps | n/a | 1 hour, burner account | Optional, dev-only; not a signal |
| 5 | TradingAgents | Already built (§44); only the IC measurement is open | 0 of 20 sessions; ≈ ₹11k to measure | none | No new work; do not fund at ₹5,500 |
| 6 | Price-range rule | One more price-only 5m rule | 119 trials at ≈ 0 pre-friction; §72 cousin failed | 1 day, 1 trial | Skip unless the owner wants it on record |
| 7 | Awesome Systematic Trading | Directory | Already used in the sweep | none | Bookmark |
| 8 | Ponytail / Graphify / UI UX Pro Max | Dev tooling | Marginal at this repo size | — | Skip |
| 9 | OpenAlice / Krypt Trader | Generic agent harness, no NSE, no P&L record | Its own disclaimer | — | No |

**The honest bottom line.** None of these changes §76: at ₹5,500 the
executable instruments have no measured intraday edge, and the only
net-positive result in the project's history is a monthly delivery tilt
that failed its own multiple-testing gate. Of the nine, one (Kronos) is a
genuinely new hypothesis and deserves one pre-registered look; one (the
discipline grid) improves the part of the process that is now human and
needs no evidence gate; the rest are either already here, already
measured, or tooling. Nothing here justifies switching automatic entries
back on, and this note proposes no engine change.
