# Intraday Trading Agent — "Trader Brain" for NSE (Zerodha)

An intraday trading agent for Indian equities. It watches a list of NSE
stocks, analyses them the way a professionally trained technical trader
would — trend, market structure, momentum, support/resistance, candlestick
patterns, volume and news — and trades only when several independent pieces
of evidence agree. It runs in **paper mode** by default and can route real
orders through **Zerodha Kite Connect**. A web dashboard shows positions,
trades, and *why* the agent wants to buy, sell, or wait.

## ⚠️ Read this first

- **No strategy here is proven profitable, and none can guarantee profit.**
  Current honest backtest results are in [Backtest results](#backtest-results)
  — the agent is still net-negative after costs. Treat this as a disciplined,
  well-instrumented decision engine that still needs an edge, not a money
  machine. Never go live on anything the backtester (with costs on) says loses.
- **"Certified trader" means the knowledge, not a licence.** The rules are
  modelled on what CMT / NISM-certified technical traders study. Software
  can't hold a certification, and if you ever offer this agent's signals or
  trades *to other people*, SEBI's Research Analyst / Investment Adviser
  regulations apply to you.
- **Starts in paper mode.** No real orders until you click LIVE (with
  confirmation) *and* set up Kite credentials.
- **yfinance data is ~15 min delayed.** Fine for testing logic, not for real
  execution. Kite's paid data (~₹500/month) gives real-time candles.
- **Stops are checked every poll (30s)**, not by the broker. A fast move can
  blow through a stop before the engine sees it — use broker-side stop orders
  once live.
- **Auto square-off at 15:15 IST.** Confirm this matches your broker's MIS cut-off.
- **SEBI retail algo rules** (mandatory from 2026-04-01) require a static IP
  whitelisted on your Kite app, and market orders need `market_protection`
  (handled in `kite_broker.py`).

## The Trader Brain

`backend/trader_brain.py` is the default strategy (`STRATEGY = "trader_brain"`
in `config.py`). It encodes a trader's pre-trade checklist as a scored
**evidence ledger**: each rule adds (or subtracts) points to a *bullish* or
*bearish* case, tagged with a category.

### Knowledge base → code

| What a trained trader knows | Source discipline | Where it lives | How it's used |
|---|---|---|---|
| Identify the regime before choosing a playbook | CMT (ADX / Wilder) | `indicators.adx` | ADX ≥ 25 trending, < 20 ranging; RSI and Bollinger are read differently in each |
| Trade with the higher timeframe | Multi-timeframe analysis | `indicators.resample` | 5m bars merged into 15m; a long against a 15m downtrend is penalised |
| Trend = EMA alignment + price vs VWAP | CMT, institutional intraday practice | `indicators.ema`, `session_vwap` | Price > EMA20 > EMA50 and above VWAP builds the bull case |
| Higher highs & higher lows | Dow Theory | `market_structure.swing_points`, `structure_trend` | Confirms or breaks the trend; a broken structure below EMA50 exits longs |
| Support/resistance are where price turned before | Price action | `market_structure.key_levels` | Swing points clustered within ½ ATR, plus previous-day H/L/C and the opening range |
| Buy breakouts with volume, don't buy into resistance | Wyckoff / price action | `breakout_above`, `volume_ratio` | Breakout on ≥1.2× volume scores +2; resistance within 1 ATR scores −1.5 (poor reward:risk) |
| Momentum confirmation | CMT (MACD, RSI, Stochastic) | `indicators.macd`, `rsi`, `stochastic` | MACD crossovers/histogram; RSI 50–70 = strength in a trend, ≤ 35 = opportunity only in a range |
| Don't chase | Risk discipline | `trader_brain` | RSI ≥ 78 subtracts points |
| Candlestick patterns only matter in context | Nison, *Japanese Candlestick Charting* | `candlestick_patterns.py` | 20 patterns (hammer, engulfing, morning/evening star, soldiers/crows, harami, tweezers, marubozu…) conditioned on the prior trend; full weight only at a value area (support, EMA20, VWAP) |
| Ignore noise bars | Price action | `detect_patterns` | Bars with range < 0.3 ATR are ignored |
| News is a catalyst | Fundamental awareness | `news_sentiment.py` | Yahoo headlines scored with a finance lexicon (beats/misses, upgrades, order wins, probes, pledges…), recency-weighted; strongly negative news **vetoes** new longs |
| Avoid the open and late-session entries | Intraday discipline | `no_entry_before`, `last_entry_time` | No entries before 09:30 or after 14:30 |
| Several independent confirmations, not one indicator | Confluence trading | `min_confirmations`, `min_edge` | Needs a score ≥ 6, ≥ 3 agreeing categories, and bull − bear ≥ 2 |
| Size by risk, never over-leverage | Risk management | `risk_manager.py` | 1% risk per trade with an ATR stop, each position capped at 33% of capital, daily loss limit |

### Decision rules

- **BUY** when the bull score first crosses the threshold with enough
  confirmations, a clear margin over the bear score, inside the entry
  window, and no news veto. The signal is edge-triggered, so the agent won't
  re-enter the same setup right after being stopped out.
- **SELL (exit long)** when the bear score reaches `exit_threshold`, the trend
  structure breaks below EMA50, or strongly negative news appears. The
  ATR stop-loss / take-profit and 15:15 square-off still apply on top.
- Every decision is **explained**: the dashboard's *Trader Brain* panel shows
  the setup (Breakout / Trend pullback / Range reversal…), regime, bull vs.
  bear score bars, the top reasons on each side, detected patterns, key
  levels, news headlines, and what's blocking an entry.

All thresholds are in `STRATEGY_PARAMS["trader_brain"]` in `config.py`.

## Backtest results

55 days of 5-minute bars, RELIANCE / TCS / INFY / HDFCBANK, ₹1,00,000
capital, realistic Zerodha costs + slippage (run 2026-09-13):

| Strategy | Trades | Win rate | Gross P&L | Costs | **Net P&L** |
|---|---|---|---|---|---|
| `sma_crossover` (old default) | 92 | 23% | −₹36,559 | ₹18,520 | **−55.1%** |
| `trader_brain`, uncapped sizing | 65 | 29% | −₹15,774 | ₹14,358 | **−30.1%** |
| `trader_brain` + 33% position cap (current) | 70 | 24% | −₹1,089 | ₹2,430 | **−3.5%** |

What this says:

- The confluence engine loses far less than the simple crossover, and the
  sizing fix removed most of the damage. Before the cap, a tight 5-minute
  ATR stop sized trades at a median ₹4.8 lakh — about 5× the account.
- It is **still not profitable**. Gross P&L is roughly break-even, and costs
  make it negative. Stop-losses remain the largest source of losses.
- Changing the entry threshold (5–8) or confirmations (3→4) only moved net
  P&L between −1.7% and −3.9%. None of those is a real edge, and choosing
  the "best" one on 55 days would be curve-fitting.
- News is **neutral in backtests** because historical headlines aren't
  available, so the news rules are untested.

### Most promising next steps toward an actual edge

1. **More data and out-of-sample testing.** 55 days is tiny. Kite's
   historical API gives years of 5m data. Tune on one period, validate on another.
2. **Trade less, trade bigger moves.** At ~₹35 per trade in costs, 5-minute
   scalps need to capture more. Try 15-minute signals, or require
   ATR-to-cost ratios that make the trade worth taking.
3. **Short selling.** MIS allows intraday shorts. The bear ledger already
   exists but is only used for exits, which leaves half the opportunities unused.
4. **Stock selection.** Rank a larger universe (e.g. NIFTY 100) by relative
   strength and volume, and trade the day's leaders instead of a fixed list.
5. **Better stops.** Place the stop beyond the swing low/support that
   defined the setup, instead of a fixed ATR multiple.
6. **Better news understanding.** Replace the lexicon with an LLM or a
   FinBERT-style model, and record live headlines so they can be backtested later.

## Architecture

```
webapp/
├── backend/
│   ├── app.py                   # FastAPI: REST + WebSocket, runs the engine loop
│   ├── config.py                # watchlist, strategy + thresholds, risk, costs, market hours
│   ├── trader_brain.py          # ★ confluence strategy: evidence ledger → BUY / SELL / wait
│   ├── indicators.py            # EMA, RSI, MACD, Bollinger, VWAP, ADX, Stochastic, ATR, volume ratio, resampling
│   ├── candlestick_patterns.py  # context-aware candlestick pattern recognition
│   ├── market_structure.py      # swings, Dow trend, S/R zones, prev-day & opening range, breakouts
│   ├── news_sentiment.py        # Yahoo headlines → recency-weighted finance-lexicon sentiment
│   ├── strategy_engine.py       # strategy registry (+ legacy sma_crossover / rsi_reversion)
│   ├── risk_manager.py          # position sizing, notional cap, ATR stops/targets, daily loss limit
│   ├── trading_engine.py        # background loop: data → stops → signal → risk → execute
│   ├── backtester.py            # replays history through the same strategy/risk code, with costs
│   ├── costs.py                 # brokerage, STT, exchange, SEBI, GST, stamp duty, slippage
│   ├── data_provider.py         # Kite real-time data when connected, yfinance otherwise
│   ├── state.py                 # shared in-memory state + fill accounting
│   ├── paper_broker.py          # simulated execution (default)
│   ├── kite_broker.py           # live execution via Kite Connect
│   └── generate_access_token.py # daily Kite login (sessions expire each day)
└── frontend/
    └── index.html               # single-file dashboard (vanilla JS + lightweight-charts)
```

Every `POLL_INTERVAL_SECONDS` during market hours, for each symbol, the engine
fetches candles, checks the open position's stop/target first, runs the
strategy (fetching cached news sentiment if the strategy uses it), sizes the
trade through the risk manager, executes in paper or live mode, and publishes
the full analysis to the dashboard.

## Setup

1. **Install**
   ```bash
   cd webapp/backend
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Run the backend**
   ```bash
   uvicorn app:app --reload --port 8000
   ```
3. **Open the dashboard**: open `frontend/index.html` in a browser (or
   `python3 -m http.server 5500` from `frontend/`). Analysis appears once the
   market is open and enough candles have loaded (~80 bars).
4. **Configure** `backend/config.py`: `WATCHLIST`, `STRATEGY`,
   `STRATEGY_PARAMS["trader_brain"]`, `RISK`, market times.

### Backtesting

```bash
cd backend
python backtester.py --strategy trader_brain --days 55
python backtester.py --strategy sma_crossover --days 55
python backtester.py --symbols SBIN,ICICIBANK --strategy trader_brain
python backtester.py --no-costs   # frictionless, for reference only
```

Re-run with costs on after **every** rule change.

### Going live (only after paper + backtest results justify it)

1. Create an app at https://developers.kite.trade and subscribe to Kite
   Connect (~₹500/month, includes real-time data). Note the API key and secret.
2. **Whitelist a static IP** on the app (a SEBI requirement). Use an ISP
   static IP or an India-hosted VPS.
3. `export KITE_API_KEY=... KITE_API_SECRET=...`
4. Each morning: `python generate_access_token.py`, or click **Connect Kite**
   on the dashboard. The token is saved to `backend/.kite_session.json`
   (gitignored — never commit it).
5. Click **LIVE** and confirm.

This setup trades one personal account at well under 10 orders/second,
which is why it doesn't need formal algo registration. Don't scale order
frequency up without registering.

## Known limitations

- Still net-negative in backtests (see above). Building an edge is the main work left.
- Long-only. The bearish analysis is used for exits, not short entries.
- News can't be backtested, and lexicon sentiment is crude.
- The live loop evaluates the still-forming candle, so live signals can
  differ slightly from backtests, which use completed bars.
- State isn't persisted, so a restart clears positions and history.
- Live positions are a local mirror, not reconciled with `kite.positions()`.
  Partial fills, rejections, or manual trades will make them diverge.
- Single-user, no API auth, CORS open. Local use only.
- yfinance is unofficial and can rate-limit or change format.
