# Intraday Trading Agent — NSE (Zerodha)

An intraday trading agent for Indian equities. It works like a disciplined
technical trader. It **scans the NIFTY 100** to decide *what* is worth trading
today, using market context, relative strength, volume, sector leadership,
news and results-day risk. The **Trader Brain** then decides *when* to enter
and exit, using trend, structure, momentum, levels, candlestick patterns and
volume. It sizes every trade by risk and explains each decision on a live
dashboard.

It runs in **paper mode** by default and can route real orders through
**Zerodha Kite Connect**.

## ⚠️ Read this first

- **It is not profitable yet.** Every configuration in the
  [backtests](#backtest-results) loses money after costs. The best current
  default loses ~10% over 55 days. This is a well-instrumented, explainable
  decision engine that still needs an edge. Don't trade real money with it.
- **Most retail intraday traders lose.** SEBI's own studies of Indian
  retail traders found large majorities losing money in both intraday cash
  and F&O. Costs (brokerage, STT, slippage) are the main reason, and the
  backtests here show the same thing.
- **Earlier results in this README were wrong.** yfinance returns
  timestamps in UTC, and the strategy read them as IST. Its 09:30–14:30
  entry window therefore only allowed trades from about 15:00 to 15:15 IST.
  That's fixed (`data_provider.py`, `scanner.download_batch`), and all
  numbers below are from the corrected code.
- **"Certified trader" describes the knowledge, not a licence.** The rules
  follow what CMT/NISM-trained technical traders study. If you ever offer
  this agent's signals to other people, SEBI's Research Analyst / Investment
  Adviser rules apply.
- **Starts in PAPER mode.** No real orders until you click LIVE and set up Kite.
- **Data caveats:** yfinance is ~15 minutes delayed. The NSE feeds are the
  JSON endpoints behind nseindia.com's own pages, not a documented API, so
  they can change or rate-limit. Google News RSS is unofficial.
- **Live trading needs a static IP** whitelisted on your Kite app (a SEBI
  rule). Run the backend on a VPS with a fixed IPv4 and whitelist that.

## How the agent decides

### 1. Market context (every scan)

| Signal | Effect |
|---|---|
| NIFTY daily trend (EMA20/50), day change, holding above its open | Market bias score |
| Breadth: advancers vs decliners across the NIFTY 100 | ≥ 60% up adds to the score, ≤ 40% subtracts |
| India VIX ≥ 20 | Counts as risk; new position sizes halved |
| **Bias** = risk-on / neutral / **risk-off** | Risk-off: at most 2 active stocks and **no new longs** |

### 2. Scanner — *what* to trade (`scanner.py`, every 5 min open / 60 min closed)

The universe is the NIFTY 100 (large, liquid, F&O-eligible stocks), refreshed
weekly from NSE's list.

| Stage | Rules (points) |
|---|---|
| **Tradability filters** | Price ≥ ₹100 · turnover ≥ ₹50 cr/day · daily ATR ≥ 1.2% (anything slower can't beat costs) · **results due today or next session → excluded** |
| **Daily setup** | Daily uptrend +20 / downtrend −15 · 10-day relative strength vs NIFTY up to +20 · within 3% of 52-week high +10 · NR7 +8 / inside day +6 · daily RSI 45–70 +5, > 75 −8 |
| **In play today** | Gap 0.3–3% +6, > 3% −10 · relative volume vs the same time of day ≥ 2× +15, ≥ 1.3× +8, < 0.7× −8 · beating NIFTY today up to +15 · above VWAP ±5 · above the 15-min opening range +8 · top-3 sector +8, bottom-3 −5 |
| **Catalysts** | Positive filing or news up to +12 · clearly negative −15 |
| **Deep read** | The top 15 get a full Trader Brain analysis with per-stock news; the bull−bear edge adjusts their score by up to ±15 |
| **Active watchlist** | Top 6 by final score that aren't in a daily downtrend (2 on risk-off days), plus pinned stocks and open positions |

### 3. Trader Brain — *when* to trade (`trader_brain.py`)

| What a trained trader checks | Source | Rule |
|---|---|---|
| Regime first | CMT / Wilder ADX | ADX ≥ 25 trending, < 20 ranging; RSI and Bollinger are read differently in each |
| Higher timeframe | Multi-timeframe analysis | 5m resampled to 15m; a long against the 15m downtrend −2 |
| Trend + VWAP | CMT, institutional practice | Price > EMA20 > EMA50 +2 · above session VWAP +1 |
| Structure | Dow Theory | Higher highs + higher lows +1; a broken structure below EMA50 forces an exit |
| Location | Price action | S/R zones from clustered swing points, previous-day H/L/C, opening range · breakout on volume +2 · resistance within 1 ATR −1.5 |
| Momentum | CMT | MACD crossover/histogram · RSI 50–70 in trends, ≤ 35 in ranges · stochastic turns · RSI ≥ 78 −1.5 (don't chase) |
| Trigger | Nison candlesticks | 20 patterns conditioned on the prior trend; full weight only at a value area; noise bars ignored |
| Participation | Wyckoff | Volume ≥ 1.5× average on the trigger bar +1 |
| Catalyst | News | Sentiment × 2; strongly negative news **vetoes** new longs |
| **Discipline** | Intraday practice | No entries before 09:30 or after 14:30 · ≥ 3 agreeing categories · bull ≥ 6 and beats bear by ≥ 2 · **one entry per stock per day** |

Exits: ATR stop-loss and take-profit, a Trader Brain exit (bear score ≥ 5
or broken structure), and auto square-off at 15:15.

### 4. News sources (`news_sentiment.py`, `nse_feed.py`)

| Source | Cost | Used for | Weight |
|---|---|---|---|
| **NSE corporate announcements** | Free | Order wins, acquisitions, buybacks, resignations, pledges, credit ratings (routine filings ignored) | 1.5 |
| **NSE event calendar** | Free | Results due today/next session → stock excluded | filter |
| **Google News RSS (India)** | Free, no key | Per-stock headlines plus market-wide "stocks in news" discovery | 1.0 |
| **Marketaux** (optional) | Free tier 100 requests/day | Per-entity sentiment scores; set `MARKETAUX_API_KEY` | 1.2 |
| Yahoo Finance | Free | Fallback when Google returns nothing | 0.6 |

Headlines are de-duplicated and must actually name the company. They're
scored with an India-tuned finance lexicon (`sentiment_lexicon.py`), unless
the source provides its own sentiment. Each is weighted by source × recency
(12h half-life), and the total is scaled by the amount of evidence.
Marketaux's handling of Indian symbols hasn't been checked against a live key.

**Why not other APIs:** Finnhub's news sentiment covers US companies only,
EODHD's free tier gives about 2–4 news calls a day, and Alpha Vantage allows
25 requests a day in total. NSE filings plus Google News cover Indian
large caps better, and they're free.

## Dashboard

- **Market strip:** risk-on/off bias (hover for the reasons), NIFTY, VIX,
  breadth, leading and lagging sectors, last scan time, **Scan now** button.
- **Opportunities:** all 100 stocks ranked, with change, relative volume,
  score and status (`ENTRY OK` / `ACTIVE` / `HELD` / `watch` / `avoid`).
  Hover for the top reasons. Filtered-out stocks show their reason.
- **Chart:** candles with support, resistance and VWAP lines from the brain.
- **Why this stock:** the scanner's score breakdown, gap, relative strength,
  relative volume, ATR, distance from the 52-week high, catalyst, and any
  event-risk warning.
- **Trader Brain:** setup, regime, bull vs bear score bars, evidence on
  each side, patterns, and what's holding an entry back.
- **Agent Activity:** a plain-English log of scans, watchlist changes,
  forming setups, trades and **skipped signals with the reason** (risk-off,
  max positions, event risk…).
- **Trade Blotter:** every fill with its *why* (setup plus top reasons, or the exit reason).
- **News:** the selected stock's headlines with source and sentiment, plus
  today's market catalysts across the universe.

## Backtest results

55 days of 5-minute bars (2026-06-29 → 2026-09-11), ₹1,00,000 capital,
realistic Zerodha costs + slippage. H1/H2 are the two halves of the sample.

| Setup | Trades | Win % | Gross | Costs | **Net** | H1 / H2 |
|---|---|---|---|---|---|---|
| SMA crossover, 4 fixed stocks | 108 | 19% | −₹4,178 | ₹3,699 | **−7.9%** | — |
| Trader Brain, 4 fixed stocks, unlimited re-entries | 452 | 19% | −₹13,602 | ₹15,485 | **−29.1%** | −12.6k / −16.4k |
| **Trader Brain, 4 fixed stocks, 1 entry/stock/day (current default)** | 162 | 21% | −₹4,938 | ₹5,548 | **−10.5%** | −4.3k / −6.2k |
| Trader Brain + scanner top-5/day, 1 entry/day | 218 | 20% | −₹6,767 | ₹6,979 | **−13.7%** | −5.9k / −7.8k |
| Same on **15-minute** bars, 4 fixed stocks | 103 | 23% | −₹2,736 | ₹3,525 | **−6.3%** | −3.3k / −3.0k |
| 15-minute bars, scanner top-5/day | 177 | 23% | −₹8,796 | ₹5,668 | **−14.5%** | −5.7k / −8.8k |

What this shows:

- **Overtrading was the biggest leak.** Allowing unlimited re-entries
  produced 8 trades a day on 4 stocks. Limiting each stock to one entry a day
  cut losses in every variant and in both halves, so it's now the default.
- **Slower bars help.** 15-minute bars roughly halved the loss on fixed
  stocks, because fewer, larger moves are less eaten by costs. The live
  scanner is still built around 5-minute bars, so switching needs care.
- **The scanner's daily-only picks didn't beat a fixed list** of four mega-caps
  in backtest. The backtest can't replay the scanner's intraday relative
  volume, gap, news or results-day filters, which is most of what it does live.
- **Gross P&L is negative everywhere.** This isn't only a cost problem:
  the entries themselves don't have an edge yet.

```bash
cd backend
python backtester.py --strategy trader_brain --days 55
python backtester.py --strategy trader_brain --universe nifty100 --scan-top 5
python backtester.py --strategy trader_brain --interval 15m
python backtester.py --no-costs   # frictionless, for reference only
```

## Improving the brain

The highest-leverage next steps:

1. **Longer history + out-of-sample.** 55 days is tiny. Kite's historical
   API gives years of data. Tune on one period, validate on another.
2. **Short selling.** The bearish evidence ledger already exists. Risk-off days
   (74 of 100 stocks down on the last session) currently mean doing nothing.
3. **Structure-based stops** below the swing low that defined the setup,
   instead of a fixed ATR multiple.
4. **Record live news + scanner snapshots** so catalysts and intraday scan
   rules can be backtested later.
5. **Learn from better sources.** Books worth adding as knowledge (bring
   your own legally obtained copies): Zerodha Varsity modules (free, Indian
   markets), NISM Series VIII workbook, Murphy's *Technical Analysis of the
   Financial Markets*, Nison's *Japanese Candlestick Charting Techniques*,
   Brooks' *Trading Price Action* series, Bulkowski's *Encyclopedia of Chart
   Patterns*, Tharp's *Trade Your Way to Financial Freedom* (position sizing),
   Chan's *Algorithmic Trading*, and López de Prado's *Advances in Financial
   Machine Learning* (backtest overfitting).

## Architecture

```
webapp/
├── backend/
│   ├── app.py                   # FastAPI: REST + WebSocket, runs the engine
│   ├── config.py                # SCANNER, MARKET_FILTER, NEWS, STRATEGY_PARAMS, RISK, COSTS
│   ├── trading_engine.py        # loop: scan → per-stock brain → market/risk gates → execute → activity log
│   ├── scanner.py               # ★ NIFTY 100 ranking: market context, tradability, setup, in-play, catalysts
│   ├── trader_brain.py          # ★ confluence timing strategy with explanations
│   ├── news_sentiment.py        # ★ multi-source news aggregation + market catalyst discovery
│   ├── nse_feed.py              # ★ NSE announcements + results calendar
│   ├── sentiment_lexicon.py     # India-tuned finance sentiment lexicon
│   ├── universe.py              # NIFTY 100 list (cached in data/nifty100.csv)
│   ├── indicators.py            # EMA, RSI, MACD, Bollinger, VWAP, ADX, Stochastic, ATR, resampling
│   ├── candlestick_patterns.py  # context-aware pattern recognition
│   ├── market_structure.py      # swings, Dow trend, S/R zones, breakouts
│   ├── risk_manager.py          # risk sizing, 33% notional cap, ATR stops, daily loss limit
│   ├── backtester.py            # same strategy/risk code over history, with costs; --universe mode
│   ├── costs.py · data_provider.py · state.py · paper_broker.py · kite_broker.py · generate_access_token.py
│   └── data/nifty100.csv
└── frontend/index.html          # single-file dashboard
```

## Setup

```bash
cd webapp/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MARKETAUX_API_KEY=...        # optional
uvicorn app:app --port 8000
```

Then open `frontend/index.html`, or serve it with `python3 -m http.server 5500`
from `frontend/`. The first scan runs within a minute, even when the market is
closed (it shows the last session). To point the dashboard at a backend on
another local port, add `?api=http://localhost:8765` to the URL.

Main settings in `config.py`: `SCANNER` (universe filters, active count,
pinned symbols), `MARKET_FILTER` (risk-off / VIX behaviour), `NEWS` (sources),
`STRATEGY_PARAMS["trader_brain"]`, and `RISK`.

### Going live (only once backtests and paper results justify it)

1. Create an app at https://developers.kite.trade and subscribe (~₹500/month, includes real-time data).
2. Whitelist a **static IPv4** on the app. Use a VPS in India, and run the backend there.
3. `export KITE_API_KEY=... KITE_API_SECRET=...`, then log in each morning
   (`python generate_access_token.py` or **Connect Kite**). The token is
   saved to the gitignored `.kite_session.json`.
4. Click **LIVE** and confirm.

## Known limitations

- Net-negative in every backtest. There's no edge yet.
- Long-only.
- News, gaps, relative volume and results-day filters can't be backtested
  (no historical data for them).
- Live analysis uses the still-forming candle, unlike backtests.
- State isn't persisted, and live positions aren't reconciled with `kite.positions()`.
- Single-user, no API auth, CORS open. Local use only.
