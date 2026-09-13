# Trader Sahab: an intraday trading agent for NSE (Zerodha)

Trader Sahab is an intraday trading agent for Indian equities and, now,
options-buying. It works like a disciplined technical trader. It **scans the
NIFTY 100** to decide *what* is worth trading today and on which side: strong
stocks to buy on strong days, weak stocks to **short** on weak days. It uses
market context, relative strength, volume, sector leadership, news and
results-day risk. The **Sahab's Dimaag** then decides *when* to enter and
exit, following **Zerodha Varsity's own Grand Checklist** — a candlestick
pattern, a stop at support or resistance, above-average volume, Dow Theory
trend agreement, and a minimum reward-to-risk — the same checklist Varsity's
Technical Analysis module teaches a retail trader to run before every trade.
It sizes every trade by risk and explains each decision in plain language,
with a link to the exact source behind it, on a live multi-page dashboard.

It runs in **paper mode** by default and can route real orders through
**Zerodha Kite Connect** — for cash equity, and (opt-in, separately) for
buying calls/puts once the checklist and a confidence gate both clear.

## ⚠️ Read this first

- **It is not profitable yet.** Every configuration in the
  [backtests](#backtest-results) loses money after costs. The best current
  default loses ~10% over 55 days. This is a well-instrumented, explainable
  decision engine that still needs an edge. Don't trade real money with it.
- **Most retail intraday traders lose.** SEBI's own study (Jul 2024) found
  71% of individual intraday cash traders net-lost in FY23, rising to 80%
  above 500 trades/year. A separate SEBI study (Sep 2024) found 93% of
  individual F&O traders lost money over FY22–FY24, averaging ~₹2 lakh loss
  each. The dashboard's Journal page shows these numbers directly instead of
  a made-up return target — see "What good actually looks like here."
- **F&O here means buying calls/puts only** — never writing/selling options,
  never futures. NISM Series VIII is explicit that a long option's maximum
  loss is the premium paid, full stop, while a short call's "has to be
  unlimited" — a fundamentally different risk shape from everything else
  this codebase sizes to a known, bounded loss. See
  [F&O (options-buying only)](#fo-options-buying-only) below.
- **F&O trades are gated by a confidence score**, not just the checklist —
  it's deliberately capped low whenever the Dimaag Scorecard (expectancy,
  Deflated Sharpe Ratio, Information Coefficient) hasn't proven a real
  system-wide edge yet. Right now, on real logged data, it hasn't — so F&O
  effectively won't trade until that changes. This is by design, not a bug.
- **The dashboard now requires an API key** on every route except the Kite
  OAuth redirect (`/kite/callback`) — see [Setup](#setup). Without this,
  anyone who could reach the backend (e.g. via a tunnel used for the Kite
  login step) could flip it to live trading or enable F&O.
- **"Certified trader" describes the knowledge, not a licence.** The rules
  follow what CMT/NISM-trained technical traders study. If you ever offer
  this agent's signals to other people, SEBI's Research Analyst / Investment
  Adviser rules apply.
- **Starts in PAPER mode, F&O starts disabled.** No real orders until you
  click LIVE and set up Kite; no options orders until you also separately
  turn F&O on from the Portfolio page.
- **Data caveats:** yfinance is ~15 minutes delayed. The NSE feeds are the
  JSON endpoints behind nseindia.com's own pages, not a documented API, so
  they can change or rate-limit. Google News RSS is unofficial. Kite Connect
  gives F&O OHLC + open interest, not implied volatility — this app solves
  for IV itself from each contract's live premium (`options_pricing.py`).
- **Live trading needs a static IP** whitelisted on your Kite app (a SEBI
  rule). A home internet connection is often dynamic; a small cloud VM
  usually isn't. Run the backend there if you need this reliably.
- **NSE holidays are hardcoded for 2026** (`holidays.py`, pulled from NSE's
  own holiday-master API) — re-pull and update the list each year.

## How the agent decides

### 1. Market context (every scan)

| Signal | Effect |
|---|---|
| NIFTY daily trend (EMA20/50), day change, holding above its open | Market bias score |
| Breadth: advancers vs decliners across the NIFTY 100 | ≥ 60% up adds to the score, ≤ 40% subtracts |
| India VIX ≥ 20 | Counts as risk; new position sizes halved |
| **Bias** = risk-on / neutral / **risk-off** | Risk-off: **no new longs**, shorts get the slots (at most 2 long picks kept on watch). Risk-on: the mirror image, no new shorts. Neutral: both sides |

### 2. Scanner — *what* to trade (`scanner.py`, every 5 min open / 60 min closed)

The universe is the NIFTY 100 (large, liquid, F&O-eligible stocks), refreshed
weekly from NSE's list. The engine won't scan or trade on an NSE holiday or
weekend (`holidays.py`) — the dashboard shows "Markets are shut today for
X" and when trading resumes instead of treating it as an ordinary closed day.

| Stage | Rules (points) |
|---|---|
| **Tradability filters** | Price ≥ ₹100 · turnover ≥ ₹50 cr/day · daily ATR ≥ 1.2% (anything slower can't beat costs) · **results due today or next session → excluded** |
| **Daily setup** | Daily uptrend +20 / downtrend −15 · 10-day relative strength vs NIFTY up to +20 · within 3% of 52-week high +10 · NR7 +8 / inside day +6 · daily RSI 45–70 +5, > 75 −8 · confirmed Bulkowski daily pattern +15 · Murphy reversal day/selling climax +10 to +18 |
| **In play today** | Gap 0.3–3% +6, > 3% −10 · relative volume vs the same time of day ≥ 2× +15, ≥ 1.3× +8, < 0.7× −8 · beating NIFTY today up to +15 · above VWAP ±5 · above the 15-min opening range +8 · top-3 sector +8, bottom-3 −5 |
| **Catalysts** | Positive filing or news up to +12 · clearly negative −15 |
| **Both sides** | Every rule above is scored twice, once as a long and once as a mirrored short (daily downtrend, lagging NIFTY, near the 52-week low, gap down, below VWAP, broke the opening range, bottom-3 sector, negative catalyst). The stronger side is kept |
| **Deep read** | The top 15 get a full Sahab's Dimaag analysis with per-stock news; the timing edge for their side adjusts the score by up to ±15 |
| **Active watchlist** | Top 6 by final score whose daily trend doesn't fight their side, with at most 2 against the market bias, plus pinned stocks and open positions |

### 3. The Rule Book — how the sources connect

Every trade decision is one connected chain, not separate silos: a chart
pattern (Nison, Bulkowski, or Murphy) needs a stop at a real level (Varsity)
needs volume behind it (Varsity, plus Murphy's On Balance Volume divergence)
needs the trend to agree (Dow Theory *or* Brooks' "always-in" direction)
needs the day's news to not contradict it (NSE filings + Google News +
Marketaux + Alpha Vantage) needs a reward-to-risk worth taking (Varsity,
with Bulkowski's measured average move as the target when a daily pattern
applies) needs a position size that survives a string of losses (Tharp).
Every one of those checks is visible on the dashboard's Timing Read tab and
the dedicated **Technical Analysis** page, with its exact source cited, both
while a trade is being considered and afterwards in the journal — so the
reasoning is never hidden in a score.

| Source | What it contributes |
|---|---|
| Zerodha Varsity, Technical Analysis | The Grand Checklist itself: pattern, S/R stop, volume, Dow Theory, RRR |
| Nison, *Japanese Candlestick Charting Techniques* | Candlestick patterns, incl. Abandoned Baby and Rising/Falling Three Methods |
| Bulkowski, *Encyclopedia of Chart Patterns* | Daily-chart Double Top/Bottom and Head-and-Shoulders detection, gap classification, real failure-rate/average-move stats |
| Brooks, *Trading Price Action Trends* | The "always-in" trend direction, alongside Dow Theory |
| Murphy, *Technical Analysis of the Financial Markets* | Reversal days / selling climaxes (daily scanner) and On Balance Volume divergence (intraday checklist, ch 4 & 7). OCR'd this session — see below |
| News (NSE filings + Google News + Marketaux + Alpha Vantage) | The catalyst check — degrades or vetoes a trade the news contradicts |
| Tharp, *Trade Your Way to Financial Freedom* | Percent Risk / Percent Volatility position sizing, R-multiples, expectancy, Kelly fraction |
| NISM Series VIII | Options Greeks and long-option payoff definitions (now used by F&O below); F&O contract specs and the Market Wide Position Limit ban otherwise still unused |
| Bailey & López de Prado (2014); Grinold (cited in Jansen, *Machine Learning for Trading*) | Deflated Sharpe Ratio and Information Coefficient — the two statistics the Dimaag Scorecard is built on |

Murphy's book is a scanned PDF with no text layer. `tesseract` + `poppler`
were installed and used to OCR all 574 pages this session. Two concrete,
verifiable rules from it are wired into the engine (reversal days, OBV
divergence); Elliott Wave, Point & Figure, time cycles, intermarket analysis
and market-breadth indicators were read but deliberately not built in — each
for a specific reason (too subjective to encode reliably, redundant with
what's implemented, needs data this app doesn't fetch, or the wrong asset
class) documented on the dashboard's Technical Analysis page.

### 4. The Varsity Checklist — *when* to trade (`trader_brain.py`)

Trader Sahab's default entry logic (`entry_mode: "checklist"`) is Zerodha
Varsity's **Grand Checklist**, read directly from the Technical Analysis
module (chapters 4–18) and implemented rule for rule instead of paraphrased:

| Varsity rule | Chapter | What Trader Sahab checks |
|---|---|---|
| A recognisable candlestick pattern, after the right prior trend | ch 4–10 | One of 24 patterns (`candlestick_patterns.py`), sized sanely (0.3–3× ATR) — includes Nison's Abandoned Baby and Rising/Falling Three Methods |
| The stop-loss sits at support or resistance | ch 11 | The pattern's low/high must land within 0.5 ATR of a swing, previous-day, opening-range, Fibonacci or CPR level |
| Above-average volume on the signal candle | ch 12 | Volume vs its 10-candle average (Varsity's volume-trend table), **plus** On Balance Volume divergence over a longer window (Murphy ch 7) as an earlier warning than a single bar's volume ratio can show |
| The trend agrees | ch 17–18 | Dow Theory (15-minute trend, swing structure) **or** Brooks' "always-in" direction (`brooks.py`) — either confirms |
| Indicators confirm, but only to size the bet | ch 15.4 | MACD and RSI: if they agree, full size; if not, Varsity's own worked example ("300 shares instead of 500") — 60% size |
| *(new, not in Varsity)* News doesn't contradict the trade | — | NSE filings + Google News + Marketaux + Alpha Vantage sentiment; strongly opposed news vetoes the entry outright, mildly opposed news sizes it down like a missed indicator |
| Reward-to-risk of at least 1.5, net of costs | ch 18.5 | Target = next level beyond entry (or 2R if none); RRR is computed after estimated round-trip costs |

**A trade needs every required point** (pattern, S/R, volume, trend, RRR);
indicators and news only scale the size. This is stricter than the older
confluence-score system (`entry_mode: "confluence"`, kept for comparison) and
trades far less often — see the backtest table below.

Two more Varsity concepts feed the checklist as extra support/resistance
sources: **Fibonacci retracements** (ch 16 — 23.6/38.2/50/61.8% of the last
swing) and the **Central Pivot Range** (ch 22 — pivot, top and bottom from
the previous session's high/low/close), in `market_structure.py`.

Separately, at the **scanner** level (daily bars, not the intraday
checklist), `swing_patterns.py` detects confirmed Bulkowski Double
Top/Bottom and Head-and-Shoulders patterns (scored with his actual measured
failure rate and average move), Murphy reversal days / selling climaxes, and
`bulkowski.classify_gap()` labels today's gap as
area/breakaway/continuation/exhaustion using his gap-closure statistics —
all surfaced as cited reasons in the scanner's "Why it ranks" tab.

### 5. The confluence engine (legacy, `entry_mode: "confluence"`)

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

**Shorts** use the same checklist on the bearish evidence: bear score ≥ 6,
at least 3 agreeing categories, and an edge of 2 or more over the bull score.
They get the same discipline penalties as longs (fighting the 15-min uptrend
−2, support within 1 ATR −1.5, thin volume −0.5, RSI washed out −1.5), and
strongly positive news blocks a new short. The engine also refuses a short
the scanner ranked as a long, and vice versa. Shorts are MIS (intraday)
orders and are always covered by the 15:15 square-off. Never hold a cash
short overnight, because a short delivery goes to exchange auction.

Exits for both sides: the ATR stop-loss and take-profit (or the checklist's
own pattern-based stop and level-based target, when `entry_mode: "checklist"`),
the opposite case reaching 5 or the swing structure breaking, and the 15:15
square-off. `allow_shorts` in `STRATEGY_PARAMS["trader_brain"]` and
`SCANNER` turns shorting off.

### 6. Position sizing and stops (Varsity Risk Management module)

- **Percentage-risk sizing** (ch 11–13): risk 1% of capital divided by the
  stop distance — the pattern's structural stop when the checklist supplies
  one, ATR otherwise (`risk_manager.py`).
- **Step trailing stop** (Futures Trading ch 7): optional, off by default
  (`RISK["trail_after_r"]`) — after N·R profit, lock in (N−1)·R, one R at a
  time, the way Varsity describes a trailing SL on a Bracket Order.
- **R-multiples and expectancy** (ch 11, 14 — Kelly's Criterion): the
  backtester reports each trade's result as a multiple of its initial risk,
  the system's expectancy in R per trade, and the Kelly fraction (negative
  means the correct bet size is zero, however good the entries feel).

### 7. F&O (options-buying only)

Added this session, off by default (`config.FNO["enabled"] = False`). Buys a
**call** on a LONG checklist signal, a **put** on a SHORT signal — the same
signal engine as cash equity, just expressed through a different, capped-risk
instrument. Deliberately excludes writing/selling options and futures:

> "A long option position has limited risk (premium paid) and unlimited
> profit potential... if maximum loss for a long call position is equal to
> the premium paid, then... even maximum loss for the short call position
> has to be unlimited." — NISM Series VIII

| Piece | Module | What it does |
|---|---|---|
| Pricing + Greeks | `options_pricing.py` | Black-Scholes-Merton, with implied volatility solved from the contract's own live premium (Kite gives F&O OHLC + open interest, not IV). Delta, Gamma, Theta, Vega defined exactly as NISM Series VIII defines them |
| Contract selection | `fno_instruments.py` | Resolves the live NFO contract via Kite's own instrument dump — never a hardcoded lot size or expiry, since both are exchange-reset (SEBI changed NIFTY's lot size outright in Nov 2024). Skips expiries under 5 days out (theta decay) |
| Position sizing | `fno_risk.py` | The trade's entire max loss (premium × lots × lot size) is capped at a % of a *ring-fenced* F&O capital allocation (default ₹10,000 of ₹1,00,000), decided before the order is placed |
| Confidence gate | `confidence.py` | See below — the thing that actually decides whether a qualifying setup is allowed to fire |
| Knowledge base | `database.py` (`fno_evaluations`, `fno_trades`) | Every confidence read is logged, executed or not — same principle as `checklist_evals` logging every read, not just fills |

Exits are in **premium terms** (default: stop at −40%, target at +80% of
entry premium), because premium doesn't move linearly with the underlying.
Every F&O position shares the same `max_open_positions` and daily-loss-limit
counters as cash equity — one account, one risk budget, not two independent
ones. Live order placement uses Kite's `NFO` exchange and `MIS` product,
same same-day-square-off discipline as everything else here.

### 8. The confidence check — not a probability of profit

`confidence.py` scores every F&O candidate on two things: **local setup
strength** (how far past its own bar the checklist's edge margin cleared,
how many independent categories agreed, how clear the trend regime is) and
**system-wide evidence** (whether the Dimaag Scorecard's expectancy, DSR and
IC currently show a real, proven edge). The two multiply — a locally
"perfect" checklist pass on a system with zero proven edge is capped low,
by design, because a clean-looking setup means nothing statistically until
the system around it has demonstrated it beats chance. This is deliberately
*not* a calibrated probability: nothing here has enough closed trades yet to
calibrate one, and presenting a precise-looking number nobody's earned would
be exactly the fabricated-precision this project has tried to avoid
everywhere else. `config.FNO["min_confidence_to_trade"]` (default 60/100)
is the bar an order actually has to clear.

### 9. The Dimaag Scorecard — grading the system honestly

Added to the Journal page this session. Not a single "IQ" number — no such
validated measure exists for a trading system, and compressing independent,
differently-uncertain metrics into one score would hide the exact
uncertainty this project tries hard to keep visible. Three rows instead,
each graded against a bar already used elsewhere in this codebase, computed
from real logged data:

| Criterion | Source | Gate |
|---|---|---|
| Trading edge (expectancy) | Tharp, ch 6 | Needs ≥ 10 closed trades; pass if expectancy > 0R |
| Statistical significance (Deflated Sharpe Ratio) | Bailey & López de Prado (2014) | Needs ≥ 10 trades; pass if DSR ≥ 0.95 |
| Predictive skill (Information Coefficient) | Grinold, cited in Jansen ch 1 | Needs ≥ 20 (session, symbol) pairs; pass if IC > 0 |

Each row says "not enough data yet" rather than guessing below its sample
threshold. This same Scorecard is what gates F&O's confidence multiplier —
see above.

### 10. Position sizing and stops, News sources, Taxation panel

*(unchanged from before — see below)*

`risk_manager.py` implements Van Tharp's Percent Risk Model (ch 9, Model 3)
and Percent Volatility Model (ch 9, Model 4) for cash equity stop distance
and sizing; `costs.py` models Zerodha's published intraday tariff.

| News source | Cost | Used for | Weight |
|---|---|---|---|
| NSE corporate announcements | Free | Order wins, acquisitions, buybacks, resignations, pledges, credit ratings | 1.5 |
| NSE event calendar | Free | Results due today/next session → stock excluded | filter |
| Google News RSS (India) | Free, no key | Per-stock headlines plus market-wide "stocks in news" discovery | 1.0 |
| Marketaux (optional) | Free tier 100/day | Per-entity sentiment scores; set `MARKETAUX_API_KEY` | 1.2 |
| **Alpha Vantage (optional, added this session)** | Free tier 25/day (used at 20/day) | Real per-article sentiment, **market-wide discovery only** — its `tickers` filter can't reliably target NSE symbols and its budget is too tight for per-stock calls; set `ALPHAVANTAGE_API_KEY` | 1.2 |
| Yahoo Finance | Free | Fallback when Google returns nothing | 0.6 |

NSE bulk/block deals ("smart money" signal) were researched as a possible
addition but not built — it needs scraping an undocumented NSE endpoint, not
yet worth the added dependency.

Intraday equity is **speculative business income** under Indian tax law
(Varsity Markets & Taxation, ch 3–6) — the Trades tab shows running
trade-wise turnover, net P&L, estimated charges, and the relevant carry-
forward/advance-tax rules. Informational only, not tax advice.

### 11. Sahab's Journal — a persistent audit trail (`database.py`)

Everything above is written to a local SQLite database
(`backend/data/sahab_journal.db`, gitignored — runtime data, not source):

- **Every scan**, with the full ranked list, not just the picks.
- **Every checklist read** on an active-watchlist stock, roughly every 30
  seconds during market hours — whether or not it led to a trade.
- **Every fill**, with the checklist snapshot that justified an entry
  attached, and the realized R-multiple once the matching exit closes the
  position (linked by a shared `position_id`).
- **Every F&O confidence read**, executed or blocked, with the full
  breakdown and why (`fno_evaluations`) — and **every F&O position**, with
  the Greeks/IV/confidence frozen at entry and the outcome filled in at exit
  (`fno_trades`), never edited before that so no hindsight leaks in.

This is built around the [ML4Trading](https://github.com/stefan-jansen/machine-learning-for-trading)
book's own opening argument, "the process is your edge" — see
`research/ml4t_integration_plan.md` for the full reasoning. Two things from
it power the Scorecard above: the **Information Coefficient**
(`database.factor_ic()`, honestly "not enough data" below 20 session-pairs)
and the **Deflated Sharpe Ratio** (`evaluation.py`, every `backtester.py` run
logged as a trial in `backend/data/backtest_trials.json`).

## Dashboard

Rebuilt this session as a multi-page site (hash-routed, single HTML file)
instead of a fixed three-pane layout — it follows your system's dark mode,
and colour only means something: green for long/profit, red for short/loss,
amber for waiting, violet for a book/rule citation.

- **Overview** — one-sentence headline of what the agent is doing, a market
  countdown ("opens in 2h 14m" / a live session-progress bar, computed
  server-side in IST and holiday-aware), NIFTY/VIX/breadth/sectors, today's
  picks, open positions, and the activity log.
- **Screener** — every NIFTY 100 stock, ranked. Click a column header
  (Score / Change % / Symbol) to sort; click a row to expand its full rule
  book inline without leaving the page, with an "Open full page →" link.
- **Technical Analysis** — a dedicated reference page assembled from the
  live code constants (not hand-written text that could drift): the
  checklist categories, all 24 candlestick patterns, Bulkowski's daily
  patterns and gap stats, Murphy's reversal days and OBV divergence, trend/
  level/momentum rules, news source weights, position-sizing methods, the
  F&O section (Greeks, pricing model), and an honest "read but not (yet)
  built in" list with the specific reason each item doesn't apply.
- **Portfolio** — real Kite holdings + margins once connected (free Kite
  Connect endpoints), today's paper/live positions regardless of Kite, open
  F&O positions with live Greeks/confidence, and the F&O on/off toggle (its
  own confirmation dialog, separate from the cash-equity Live switch).
- **Journal** — the Dimaag Scorecard, the F&O knowledge base summary, the
  honest SEBI-sourced benchmark panel ("What good actually looks like
  here" — not a promised return number), trade record, which checklist
  rules actually mattered, and the Information Coefficient read.
- **Trades** — the fill-by-fill blotter.
- **Selected stock page** — a plan box (*Ready to short*, *Waiting to buy*
  with which checklist points fail, *Holding N shares*, or *No trade
  today*), key levels on the chart, the full Timing Read checklist, why the
  scanner ranked it where it did, and its news.

Every clickable item is a real button/div with a visible keyboard focus
ring. The layout stacks to one column on narrow screens.

## Backtest results

55 days of 5-minute bars (2026-06-29 → 2026-09-11), ₹1,00,000 capital,
realistic Zerodha costs + slippage. H1/H2 are the two halves of the sample.
These predate the Murphy/OBV-divergence and F&O additions — not yet re-run
with them.

| Setup | Trades | Win % | Gross | Costs | **Net** | H1 / H2 |
|---|---|---|---|---|---|---|
| SMA crossover, 4 fixed stocks | 108 | 19% | −₹4,178 | ₹3,699 | **−7.9%** | — |
| Sahab's Dimaag, 4 fixed stocks, unlimited re-entries | 452 | 19% | −₹13,602 | ₹15,485 | **−29.1%** | −12.6k / −16.4k |
| **Sahab's Dimaag, 4 fixed stocks, 1 entry/stock/day (current default)** | 162 | 21% | −₹4,938 | ₹5,548 | **−10.5%** | −4.3k / −6.2k |
| Sahab's Dimaag + scanner top-5/day, 1 entry/day | 218 | 20% | −₹6,767 | ₹6,979 | **−13.7%** | −5.9k / −7.8k |
| Same on **15-minute** bars, 4 fixed stocks | 103 | 23% | −₹2,736 | ₹3,525 | **−6.3%** | −3.3k / −3.0k |
| 15-minute bars, scanner top-5/day | 177 | 23% | −₹8,796 | ₹5,668 | **−14.5%** | −5.7k / −8.8k |

**Varsity checklist mode** (`entry_mode: "checklist"`, now the default —
same 55 days, long + short):

| Setup | Trades | Win % | Net | Expectancy | Kelly |
|---|---|---|---|---|---|
| 4 fixed stocks | 6 | 17% | **−0.5%** | −0.69R/trade | −36% (bet size should be 0) |
| Scanner top-10/day, NIFTY 100 | 19 | 26% | **−1.9%** | −0.60R/trade | −43% (bet size should be 0) |

The checklist requires a pattern, a stop at a real level, above-average
volume, Dow Theory agreement and a 1.5+ reward-to-risk all at once — so it
trades far less often (6–19 times in 55 days, versus 150–450 for the
confluence engine) and loses far less in rupee terms. But **it is not an
edge**: the expectancy per trade is still negative, and the Kelly fraction
says the mathematically correct position size is zero. Both figures come
from far too few trades (6 and 19) to trust — a sanity check on the logic,
not a verdict on the checklist.

**With short selling, confluence engine** (same period, symmetric long/short rules):

| Setup | Trades | Win % | Gross | Costs | **Net** | Longs / Shorts net |
|---|---|---|---|---|---|---|
| 4 fixed stocks, long-only (`--long-only`) | 162 | 20% | −₹5,613 | ₹5,548 | **−11.2%** | −11.2k / — |
| 4 fixed stocks, long + short | 202 | 25% | −₹3,999 | ₹6,920 | **−10.9%** | −6.3k / −4.6k |
| **Scanner top-5/day, long + short** | 146 | 25% | −₹3,788 | ₹4,741 | **−8.5%** | −5.8k / −2.7k |
| 15-minute bars, 4 fixed stocks, long + short | 189 | 29% | −₹5,020 | ₹6,470 | **−11.5%** | −5.6k / −5.9k |

What this shows:

- **Overtrading was the biggest leak.** Limiting each stock to one entry a
  day cut losses in every variant and in both halves.
- **Slower bars help.** 15-minute bars roughly halved the loss on fixed
  stocks — fewer, larger moves are less eaten by costs.
- **The scanner's daily-only picks didn't beat a fixed list** of four
  mega-caps in backtest — it can't replay the scanner's intraday relative
  volume, gap, news or results-day filters, which is most of what it does live.
- **Gross P&L is negative everywhere.** Not only a cost problem — the
  entries themselves don't have an edge yet.

```bash
cd backend
python backtester.py --strategy trader_brain --days 55
python backtester.py --strategy trader_brain --universe nifty100 --scan-top 5
python backtester.py --strategy trader_brain --interval 15m
python backtester.py --no-costs   # frictionless, for reference only
```

## Improving the brain

1. **Longer history + out-of-sample.** 55 days is tiny. Kite's historical
   API gives years of data. Tune on one period, validate on another.
2. **Separate thresholds per side.** Shorts behaved differently from longs
   here — test on more data than 55 days.
3. **Structure-based stops** below the swing low that defined the setup,
   instead of a fixed ATR multiple.
4. **Record live news + scanner snapshots** so catalysts and intraday scan
   rules can be backtested later.
5. **Let real F&O data answer its own open question.** `fno_journal_summary()`'s
   confidence-to-outcome rank correlation (needs ≥ 10 closed F&O trades)
   will show whether F&O confidence — currently borrowed from cash equity's
   Scorecard — actually predicts F&O outcomes, or whether F&O needs a
   separately-earned Scorecard of its own.
6. **Learn from better sources.** Already integrated: Varsity, NISM Series
   VIII, Murphy, Nison, Brooks, Bulkowski, Tharp. Still open: Chan's
   *Algorithmic Trading*, López de Prado's *Advances in Financial Machine
   Learning* (backtest overfitting), and the ML4Trading chapters on
   gradient boosting / deep learning / RL once there's enough real trade
   history to justify them (see `research/ml4t_integration_plan.md`).

## Architecture

```
webapp/
├── backend/
│   ├── app.py                   # FastAPI: REST + WebSocket, API-key middleware, runs the engine
│   ├── config.py                # SCANNER, MARKET_FILTER, NEWS, STRATEGY_PARAMS, RISK, COSTS, FNO, DASHBOARD_API_KEY
│   ├── trading_engine.py        # loop: scan → per-stock brain → market/risk gates → execute (cash + F&O) → activity log
│   ├── scanner.py               # ★ NIFTY 100 ranking: market context, tradability, setup, in-play, catalysts
│   ├── trader_brain.py          # ★ confluence timing strategy with explanations (shared by cash and F&O)
│   ├── confidence.py            # ★ F&O per-trade confidence check, scaled by the Dimaag Scorecard
│   ├── options_pricing.py       # ★ Black-Scholes-Merton pricing, Greeks, implied-volatility solve
│   ├── fno_instruments.py       # ★ resolves live NFO contracts via Kite's own instrument dump
│   ├── fno_risk.py              # ★ premium-based position sizing (options-buying only, capped max loss)
│   ├── evaluation.py            # ★ Deflated Sharpe Ratio + the Dimaag Scorecard
│   ├── methods.py               # ★ assembles the Technical Analysis page from real code constants
│   ├── holidays.py              # NSE trading holiday calendar
│   ├── news_sentiment.py        # ★ multi-source news aggregation (NSE, Google, Marketaux, Alpha Vantage) + market catalyst discovery
│   ├── nse_feed.py              # ★ NSE announcements + results calendar
│   ├── sentiment_lexicon.py     # India-tuned finance sentiment lexicon
│   ├── universe.py              # NIFTY 100 list (cached in data/nifty100.csv)
│   ├── indicators.py            # EMA, RSI, MACD, Bollinger, VWAP, ADX, Stochastic, ATR, OBV, resampling
│   ├── candlestick_patterns.py  # context-aware pattern recognition (24 patterns)
│   ├── swing_patterns.py        # Bulkowski daily patterns + Murphy reversal days (scanner only)
│   ├── market_structure.py      # swings, Dow trend, S/R zones, breakouts, Fibonacci, CPR
│   ├── risk_manager.py          # cash-equity risk sizing, 33% notional cap, ATR stops, daily loss limit
│   ├── database.py              # ★ Sahab's Journal — scans, checklist reads, trades, F&O evaluations/trades
│   ├── backtester.py            # same strategy/risk code over history, with costs; --universe mode
│   ├── costs.py · data_provider.py · state.py · paper_broker.py · kite_broker.py · generate_access_token.py
│   └── data/nifty100.csv
└── frontend/index.html          # multi-page dashboard (hash-routed), single file
```

## Setup

```bash
cd webapp/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MARKETAUX_API_KEY=...        # optional
export ALPHAVANTAGE_API_KEY=...     # optional — market-wide news discovery only
uvicorn app:app --port 8000
```

On first run, the backend auto-generates a **dashboard API key**
(`backend/.dashboard_key.json`, gitignored) and logs it on startup. Every
route except `/kite/callback` requires it (`X-Api-Key` header, or `?key=`
for the WebSocket and the Kite-login popup, since neither can set a custom
header). Open `frontend/index.html` (or serve it with
`python3 -m http.server 5500` from `frontend/`) and it'll prompt for the key
once, then remember it via `localStorage`. This exists because the backend
sometimes needs to be reachable from the public internet (see "Connecting
Kite locally" below) and has real control surface — without a key, anyone
with the URL could flip it to live trading or turn on F&O.

The first scan runs within a minute, even when the market is closed (it
shows the last session). To point the dashboard at a backend on another
local port, add `?api=http://localhost:8765` to the URL.

Main settings in `config.py`: `SCANNER` (universe filters, active count,
pinned symbols), `MARKET_FILTER` (risk-off / VIX behaviour), `NEWS`
(sources), `STRATEGY_PARAMS["trader_brain"]`, `RISK`, and `FNO` (capital
allocation, confidence bar, expiry window — disabled by default).

### Connecting Kite locally

Kite Connect's app registration requires an **HTTPS** Redirect URL, even for
local testing — `http://127.0.0.1:8000/kite/callback` will be rejected by
the form. Two ways around it:

1. **CLI script, no exposure needed** — `python generate_access_token.py`
   opens the login in your browser; after you log in, the `request_token` is
   in the browser's address bar even if the redirect page fails to load. You
   paste it into the terminal; nothing on the internet ever needs to receive
   the redirect. Register *any* real, resolving `https://` URL as the
   Redirect URL just to satisfy the form — it never needs to actually
   respond. This is the recommended daily routine (see below).
2. **In-app "Connect Kite" button, needs a real tunnel** — install `ngrok`
   (`brew install ngrok`), get a free authtoken from
   [dashboard.ngrok.com](https://dashboard.ngrok.com), `ngrok config
   add-authtoken <token>`, then `ngrok http 8000`. Register the printed
   `https://....ngrok-free.dev/kite/callback` as the Redirect URL. This
   exposes the *whole* backend while the tunnel runs — the dashboard API key
   (above) is what makes that safe, but still stop the tunnel once the login
   completes; you don't need it running again until you change it.
   ngrok's free tier now includes one permanent static domain per account
   (Gateway → Domains in its dashboard) — use `ngrok http 8000 --url
   https://<your-static-domain>` to avoid re-registering a new Redirect URL
   every time you restart the tunnel.

**Kite sessions expire daily.** Whichever method you used, you'll need to
redo it each morning before trading live —
`python generate_access_token.py` doesn't depend on any tunnel still being
up, which is why it's the more durable daily habit.

### Going live (only once backtests and paper results justify it)

1. Create an app at https://developers.kite.trade and subscribe to the
   **Connect** tier (needed for historical data + live market quotes —
   Personal tier explicitly excludes both, and F&O has no other data source).
2. Whitelist a **static IPv4** on the app. Use a VPS in India, and run the
   backend there, if your home connection doesn't have one.
3. `export KITE_API_KEY=... KITE_API_SECRET=...`, then log in each morning
   (`python generate_access_token.py` or **Connect Kite**). The token is
   saved to the gitignored `.kite_session.json`.
4. Click **LIVE** and confirm.
5. **Separately**, if you also want F&O: open the Portfolio page and turn
   F&O on (its own confirmation dialog). It stays off by default even once
   cash equity is live — an order only reaches Kite when both are on.

## Known limitations

- Net-negative in every backtest. There's no edge yet, in cash equity or F&O.
- F&O confidence currently borrows cash equity's Scorecard rather than
  having its own — untested assumption, not a proof (see "Improving the
  brain" above).
- Shorts (cash) are intraday cash (MIS) only. No check for stocks in the
  exchange's short-sell ban or circuit limits. No Market Wide Position Limit
  check for F&O either (documented, not yet built).
- News, gaps, relative volume and results-day filters can't be backtested
  (no historical data for them). F&O hasn't been backtested at all yet —
  only the pricing/Greeks/sizing math has been unit-tested with synthetic data.
- Live analysis uses the still-forming candle, unlike backtests.
- Live positions and the current watchlist still reset on restart (only
  history is persisted, in `sahab_journal.db`), and aren't reconciled with
  `kite.positions()`.
- Single-user. An API key now gates every route, but there's still no
  per-user auth, rate limiting, or HTTPS termination built in — treat this
  as "safe enough to expose briefly via a tunnel," not "safe to run
  permanently on the open internet" without more hardening.
