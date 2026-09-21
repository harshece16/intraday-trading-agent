# Orientation — research phase 2

Written before any hypothesis was run. Everything below marked **[verified]**
was checked by running code or reading the file named; **[read]** means I read
the implementation but did not execute it this phase.

---

## 0. Three mismatches with the brief, flagged first

**1. `docs/verdict-2026-09-20.md` does not exist.** There is no `docs/`
directory in this repo at all (this file creates it). **[verified]**

The verdict is real and the brief's numbers are exact — they are the ones
measured on 2026-09-20 — but it lives in three other places:

| Where | What |
| --- | --- |
| `README.md` §51 | the verdict, attribution, and what would change it |
| `README.md` §52 | the multi-day hold result and the scanner IC |
| GitHub issue #49 | the same, recorded as a closed issue |

**2. The Deflated Sharpe trial count is 34, not 30.** **[verified]** —
`evaluation.trial_count()` returns 34. The last four entries are the swing
backtester logging one trial per hold length on 2026-09-20:

```
{'n': 31, 'label': 'swing_backtester long-only hold=1 top5 2y stop_atr=None'}
{'n': 32, 'label': 'swing_backtester long-only hold=2 top5 2y stop_atr=None'}
{'n': 33, 'label': 'swing_backtester long-only hold=3 top5 2y stop_atr=None'}
{'n': 34, 'label': 'swing_backtester long-only hold=5 top5 2y stop_atr=None'}
```

This matters directly: it is the denominator of the DSR pass threshold in the
brief. **Any DSR I report will use the count at the time of the run, stated
explicitly.**

**3. The intraday backtester has no selection/held-out split.** **[verified]**
— zero matches for `held.out` in `backtester.py`. Only `swing_backtester.py`
implements one (`--held-out-frac`, default 0.4). The verdict's "both halves"
numbers came from a script I wrote that split by date, not from a repo
feature. **Rule 5 therefore needs harness work before step 2**, not just a
flag to pass. See §7.

Nothing else in the verdict contradicts the code.

---

## 1. Backtester — where it lives and how to run it

`backend/backtester.py` **[read]**, entry point `main()`, core
`run_backtest(symbols, strategy_name, strategy_params, risk_cfg, interval,
days, costs_cfg, preloaded, allowed_by_day, scorecard)`.

```bash
cd backend
.venv/bin/python backtester.py --universe nifty100 --source kite --days 730
```

Key arguments: `--universe nifty100` (scanner picks per day), `--scan-top N`
(picks/day, default 5), `--source {auto,kite,yfinance}`, `--days`,
`--no-costs`, `--long-only`, `--walk-forward N`.

`--source kite` **refuses to run** on an empty cache rather than silently
falling back to ~60 days of yfinance.

`run_backtest` is importable and is how I will drive every hypothesis, since
the CLI does not expose the splits rule 5 requires.

**Trades returned** carry: `symbol, entry_time, exit_time, side, qty,
entry_price, exit_price, gross_pnl, cost, pnl, reason, r, stop, target,
risk_per_share`. `r` is already **net** of costs (`net_pnl / (risk_ps ×
qty)`), which is the unit every result below uses.

`swing_backtester.py` **[read]** is a separate multi-day harness on daily
bars, long-only by design (overnight cash shorts are not possible in India),
with its own benchmark, held-out split and delivery-cost model.

## 2. Candle cache

`backend/kite_history.py` → `backend/data/kite_history.db` (SQLite,
gitignored). **[verified]** via `kite_history.status("5m")`:

| | |
| --- | --- |
| Symbols | 100 |
| Candles | 3,633,891 |
| Sessions | **495** |
| Range | 2024-09-20 → 2026-09-18 |
| Size | 409 MB |

API: `load(symbol, interval, days)`, `load_batch(symbols, ...)`,
`available(interval)`, `status(interval)`. Returns `{"time", "open", "high",
"low", "close", "volume"}` oldest-first, `time` an ISO string.

Daily bars are **not** in this cache — `swing_backtester.py` and
`scanner.premarket_picks()` pull 2y daily from yfinance, which was never
subject to the 60-day intraday cap.

## 3. Cost model

`backend/costs.py` **[read]**. `leg_cost(side, price, qty, costs_cfg)` per
executed leg: brokerage `min(₹20, 0.03% of turnover)`, STT (sell-side only
intraday), exchange transaction, SEBI charges, stamp duty (buy only), GST on
(brokerage + exchange), DP charge (delivery sells only).

`apply_slippage(side, price, costs_cfg)` moves the fill against you by
`slippage_pct` (0.03% each way).

Measured round trip on a ₹33,000 position: **₹34.98 ≈ 10.6 bp**, plus 6 bp
slippage ≈ **17 bp total**. **[verified]** this session.

`ZERO_COSTS` exists for frictionless comparison; `DELIVERY_COSTS` for
overnight holds. **Every number I report will use `config.COSTS`.**

## 4. Deflated Sharpe and the trial counter

`backend/evaluation.py` **[read]**.

- `sharpe_of_r_multiples(r_values)` — per-trade Sharpe, not annualised.
- `expected_max_sharpe(n_trials, sharpe_std)` — the Sharpe the *best* of
  `n_trials` no-edge strategies would show by luck.
- `deflated_sharpe_ratio(r_values, n_trials, sharpe_std=None)` — probability
  the observed Sharpe is real given that many attempts, correcting for
  skew/kurtosis. Its own docstring: *"Below 0.95, don't trust the backtest."*
- `log_trial(label)` — appends to `backend/data/backtest_trials.json` and
  returns the new count.
- `trial_count()` — reads without incrementing.

**The log is gitignored** (`backend/data/backtest_trials.json` matches
`backend/data/*.db`… actually it is listed explicitly in `.gitignore`). So
per rule 4 I will **also** maintain `docs/research/trials.md` as a committed,
append-only mirror, since the JSON will not survive a clone.

## 5. Scanner features (what step 2 decomposes)

`scanner.premarket_score(profile, cfg, side, date_iso)` **[read]** — daily
data only, usable before the open. Nine scoring components:

| # | Feature | Points | Source field |
| --- | --- | --- | --- |
| 1 | Seasonality (March effect) | varies | `seasonality.march_effect(month, side)` |
| 2 | Daily trend, close vs EMA20 vs EMA50 | +20 / −15 | `trend` |
| 3 | 10-day relative strength vs NIFTY | +min(20, edge×4) / −min(15, ·×3) | `rs10` |
| 4 | Within 3% of 52-week high (long) / low (short) | +10 | `pct_from_high`, `pct_from_low` |
| 5 | NR7 (narrowest range in 7) or inside day | +8 / +6 | `nr7`, `inside_day` |
| 6 | Confirmed Bulkowski daily swing pattern | +15 each | `swing_patterns` |
| 7 | Murphy reversal day (+heavy volume, +outside day) | +10…+18 | `reversal_day` |
| 8 | Daily RSI zone | +5 / −8 | `rsi` |
| 9 | Daily ATR% in 1.5–4.0% band | +5 | `atr_pct` |

`final_score` = this score **+ clamped intraday brain edge** (`bull_score −
bear_score`, ×2, clamped ±15) — but that adjustment uses **intraday** bars,
so it is *not* available pre-open. `premarket_picks()` (the backtest path)
uses `premarket_score` only. **Step 2 must decompose the nine above**, which
are genuinely pre-open and lookahead-free.

Separately, `premarket_context()` scores the *market* (NIFTY trend,
yesterday's change, FII/DII flow) and sets `bias`, which caps counter-trend
picks in `select_active()`.

## 6. Checklist entry rules, Scorecard, confidence gate

**`trader_brain._checklist()`** **[read]** — nine items, five *required*:

| Key | Required | Rule |
| --- | --- | --- |
| `pattern` | yes | a candlestick pattern whose range is 0.3–3.0 ATR |
| `sr` | yes | the pattern's extreme sits within 0.5 ATR of a real level |
| `cost` | yes | stop ≥ `min_stop_to_cost` (1.0) × round-trip cost — §46 |
| `volume` | yes | volume > its 10-candle average |
| `dow` | yes | 15-min trend agrees, or Brooks always-in agrees |
| `rrr` | yes | net reward:risk ≥ `min_rrr` (1.5) after costs |
| `indicators` | no | MACD + RSI agree — else 60% size |
| `catalyst` | no | news doesn't contradict — else 60% size |
| `fundamentals` | no | fundamentals don't contradict — else 60% size |

Stop = pattern extreme, floored at `min_stop_atr` (1.0) ATR from entry (§48).
Target = first level ≥ `min_rrr` net within `max_target_atr` (3.0) ATR.

**Dimaag Scorecard** (`evaluation.scorecard()`) — three independent rows,
each grading real logged data and saying *"not enough data"* rather than
guessing: **expectancy** (needs ≥10 closed trades), **Deflated Sharpe**
(statistical significance after multiple testing), **Information Coefficient**
(needs ≥20 sessions with 20+ rated stocks, `IC_MIN_T_STAT = 2.0`).

**Confidence gate** (`confidence.score_trade()`) — `final = local_setup_score
× system_multiplier`, where the multiplier comes from the Scorecard. With no
proven edge the multiplier caps the product at ~60 against a bar of 60
(`RISK["min_confidence_to_trade"]`), so only a *perfect* setup passes. This
is why the gated deep backtest produced 75 trades where the ungated produced
201. **It is a deadlock by construction**, noted in README §48: the gate needs
trades to prove an edge and blocks trades until one is proven. For research
it must be switched off (`min_confidence_to_trade: 0`, `scorecard=[]`), and
I will state that on every run.

## 7. What rule 5 needs that the repo does not have

`run_backtest` takes `allowed_by_day`, so restricting a run to a date range
means filtering both the candles and the picks. The verdict's both-halves
numbers were produced that way by a throwaway script.

For this phase I will add **`backend/research/splits.py`** — a small, tested
helper giving:

- `selection_holdout(sessions, frac=0.4)` → the same 60/40 chronological
  boundary `swing_backtester.py` uses, so the two harnesses agree;
- `halves(sessions)` → the both-halves boundary;
- `slice_data(preloaded, picks, lo, hi)` → candles and picks restricted to a
  window, built one slice at a time (holding three copies of 3.6M candle
  dicts is several GB).

This is harness code, not a strategy. It touches nothing the live engine
reads.

## 8. Power — what any hypothesis must clear to be confirmable

Per-trade R standard deviation measured on the 201-trade sample: **1.41**.
At t = 2, trades needed:

| Edge | Trades |
| --- | --- |
| +0.10R | ~**1,570** |
| +0.25R | ~**250** |
| +0.50R | ~**63** |

**Superseded by amendment 1 (2026-09-20).** Significance is required on the
*selection* split (~297 sessions), not the full 495, and at 80% power rather
than at the t = 2 boundary. That puts the testability bar at **0.85
trades/session**, not 0.5.

The 1.41R spread above belongs to the *old* brackets and must not be assumed
to carry: required trades will be recomputed from each hypothesis's own
per-trade spread. Anything below the bar is reported **untestable at this
frequency**, never as promising. Trades/session is reported for every
hypothesis.

## 9. Known biases carried into every write-up

- **Survivorship**: the universe is today's NIFTY 100 applied to history.
  Stocks that dropped out (usually by falling) are absent. Flatters long-only.
- **Backtest picks use daily data only** — the live scanner also applies gap,
  relative-volume, news and results-day filters that need intraday context
  and are not replayed.
- **Backtest fills at the signal candle's close**; live fills a few seconds
  later at the live price (issue #13, README §42).
