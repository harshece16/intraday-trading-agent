"""
Configuration for the intraday trading dashboard.
"""

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

# Both generate_access_token.py (CLI) and the dashboard's in-app "Connect
# Kite" flow (app.py's /kite/callback) write today's session here via
# save_kite_session(), so you don't have to manually export env vars every
# morning (access tokens expire daily). Env vars still take priority if set.
# This file holds a live credential — make sure it's gitignored (it is, see
# .gitignore) and never committed.
SESSION_FILE = Path(__file__).parent / ".kite_session.json"
_session = {}
if SESSION_FILE.exists():
    try:
        _session = json.loads(SESSION_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        _session = {}

# Required on every dashboard request except the two Kite OAuth endpoints
# Zerodha itself must reach (/kite/login, /kite/callback) — see app.py's
# ApiKeyMiddleware. Exists because this backend sometimes needs to be
# reachable from the public internet (e.g. an ngrok tunnel, just to let
# Zerodha's login redirect through) and has real control surface — flipping
# to live trading, enabling F&O — that must not be reachable by anyone who
# merely finds that URL. Auto-generated once and persisted locally so you
# never have to think of one; read it from backend/.dashboard_key.json (or
# the startup log) and enter it into the dashboard once when it asks.
_KEY_FILE = Path(__file__).parent / ".dashboard_key.json"


DASHBOARD_API_KEY_IS_NEW = False  # set True below only when a key is freshly generated this run


def _load_or_create_dashboard_key() -> str:
    global DASHBOARD_API_KEY_IS_NEW
    if _KEY_FILE.exists():
        try:
            return json.loads(_KEY_FILE.read_text())["key"]
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    key = secrets.token_urlsafe(32)
    _KEY_FILE.write_text(json.dumps({"key": key}))
    DASHBOARD_API_KEY_IS_NEW = True
    return key


DASHBOARD_API_KEY = os.environ.get("DASHBOARD_API_KEY") or _load_or_create_dashboard_key()

# PAPER_MODE True = simulated orders only (default, safe).
# Flip via the dashboard toggle or by setting this False + restarting.
PAPER_MODE_DEFAULT = True

# NSE symbols (without the .NS suffix — that's added automatically for yfinance).
WATCHLIST = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]

# Intraday candle interval used for signals. yfinance supports 1m/2m/5m/15m/30m/60m.
# 5m is a reasonable default — 1m data is noisy and yfinance only keeps ~7 days of it.
CANDLE_INTERVAL = "5m"

STRATEGY = "sahab_dimaag"  # or "sma_crossover" / "rsi_reversion" — displayed as "Sahab's Dimaag"
STRATEGY_DISPLAY_NAMES = {
    "sahab_dimaag": "Sahab's Dimaag", "sma_crossover": "SMA Crossover", "rsi_reversion": "RSI Reversion",
}
STRATEGY_PARAMS = {
    # Sahab's Dimaag ("Sahab's brain") — the Varsity-checklist decision engine.
    # Implemented in trader_brain.py; see that file for every rule.
    "sahab_dimaag": {
        "entry_threshold": 6.0,     # bullish evidence points needed to buy
        "min_confirmations": 3,     # distinct categories that must agree (trend, momentum, levels, ...)
        "min_edge": 2.0,            # bull score must beat bear score by this much
        "exit_threshold": 5.0,      # bearish evidence that closes a long
        "no_entry_before": "09:30", # skip the opening-auction volatility
        "last_entry_time": "14:30", # no fresh intraday risk late in the session
        # One shot per stock per day. Cut losses in every backtest variant and both
        # halves of the sample (it stops re-entering a setup that just failed).
        "max_entries_per_day": 1,
        # Intraday (MIS) shorts: mirror-image rules on the bearish evidence.
        "allow_shorts": True,
        # Zerodha Varsity's Grand Checklist (Technical Analysis module, ch 11-18). Required:
        # candlestick pattern, stop at S&R, above-average volume, Dow trend, reward-to-risk.
        # Indicators only scale the size. "confluence" uses the older score-based rules.
        "entry_mode": "checklist",
        # Varsity: at least 1.5 for an active trader. Also the value
        # tune_entry_params.py's grid search validated (see README) — 6.2%
        # DSR, best of 12 configs tried but still well under the 95% bar,
        # so kept because nothing tried beat it, not because it's proven.
        "min_rrr": 1.5,
        "sr_tolerance_atr": 0.5,      # how close the stop must be to support/resistance
        "volume_lookback": 10,        # Varsity compares volume with its 10-period average
        "indicator_miss_size": 0.6,   # size when MACD/RSI don't confirm (Varsity's 300 vs 500 shares)
        "min_pattern_atr": 0.3,       # ignore candles too small to mean anything...
        "max_pattern_atr": 3.0,       # ...or abnormally long (stop too far away)
        # cost_pct is derived from COSTS in trader_brain.DEFAULTS (issue #74) — don't hardcode it here.
        # rrr_without_level: None since #40 — no formulaic target when no level lies beyond (see trader_brain.DEFAULTS).
        "use_news": True,
        "news_weight": 2.0,
        "news_veto": -0.5,          # sentiment at/below this blocks new longs
        "use_fundamentals": True,
        # Real ROE/margin/PEG/debt-equity (fundamentals.py) as a tilt, never a
        # veto — smaller than news_weight since this is a brand-new, not yet
        # IC/DSR-validated signal (see README's "validate before trusting" process).
        "fundamentals_weight": 1.5,
    },
    # tuned shorter for 5-min intraday bars. trend_period filters out
    # counter-trend entries; volume_filter requires above-average volume.
    "sma_crossover": {"fast": 9, "slow": 21, "trend_period": 50, "volume_filter": True},
    "rsi_reversion": {"period": 14, "oversold": 30, "overbought": 70, "trend_period": 50},
}

# Market scanner — picks WHAT to trade from the NIFTY 100 (see scanner.py).
# When enabled, the engine's watchlist = pinned + the scanner's active picks
# + any symbol with an open position; WATCHLIST above is used only when disabled.
SCANNER = {
    "enabled": True,
    "interval_minutes_open": 5,
    "interval_minutes_closed": 60,   # still scans when closed, so the dashboard shows a plan
    # Raised from 6 to 25 after a live session showed 6 real setups can all
    # stall on genuine intraday chop at once (verified with real candle data,
    # not assumed — see README) with nothing else to fall back on. More
    # independent picks = more chances one of them shows a real confirmed
    # pattern on a given tick — the checklist rigor per stock doesn't change,
    # just how many get evaluated. Real costs, worth knowing: ~4x the
    # intraday candle fetches per 30s tick (25 vs 6), and picks ranked
    # beyond the old top-6 are, by definition, lower-conviction than the
    # ones that used to be the whole list.
    "active_count": 25,
    # How the active_count stocks are chosen (README section 91):
    #   "liquidity" - the most-traded eligible stocks by 20-day average turnover,
    #                 chosen once per session and kept all day. One rule, known
    #                 before the open; the cheapest names to trade; every stock
    #                 watched for the whole session.
    #   "score"     - the old list: best final_score first, re-chosen every scan.
    #                 Its ranking was measured to carry no information (README
    #                 sections 37 and 52), and it rotated about 50 names a day.
    # Scores, sides and reasons are still computed and shown in both modes.
    "selection": "liquidity",
    # Fix the day's list only once the scan has data for this share of the
    # universe, so one missing download can't drop a stock for the whole day.
    "freeze_min_coverage": 0.9,
    "allow_shorts": True,            # rank each stock long AND short; keep the stronger side
    "counter_trend_active_count": 2, # max picks against the market bias (longs on risk-off, shorts on risk-on)
    # Raised alongside active_count — this is what selects which candidates
    # get the full Sahab's Dimaag + news read (final_score) BEFORE the top
    # active_count are chosen; leaving this at 15 while active_count is 25
    # would mean picks ranked 16-25 get selected on their raw pre-brain
    # score, a real quality gap between what's tracked and what's ranked.
    "deep_analysis": 25,
    "min_score": 20,
    "pinned": [],                    # always tracked, e.g. ["RELIANCE"]
    # Tradability floors (intraday checklist: liquid, moves enough to beat costs)
    "min_price": 100,
    "min_turnover_cr": 50,
    "min_atr_pct": 1.2,
    "max_gap_pct": 3.0,
    "use_news": True,
    "use_fundamentals": True,
}

MARKET_FILTER = {
    "block_new_longs_when_risk_off": True,
    "block_new_shorts_when_risk_on": True,
    "vix_high": 20.0,
    "vix_high_size_multiplier": 0.5,
}

NEWS = {
    "use_nse_filings": True,         # official NSE corporate announcements
    "use_google_news": True,         # Google News RSS, India edition (free, no key)
    "use_yahoo": True,               # fallback when Google returns nothing
    # Optional: free key (100 requests/day) from marketaux.com adds entity-level sentiment.
    "marketaux_api_key": os.environ.get("MARKETAUX_API_KEY", ""),
    "marketaux_daily_limit": 90,
    # Optional: free key from alphavantage.co adds real sentiment-scored articles
    # (not lexicon-scored) to the broad market discovery feed only — its free tier
    # is a hard 25 requests/day, far too tight to spend on a per-stock request, and
    # its ticker filter is US-market-centric so it can't reliably target NSE symbols
    # anyway. One discovery call a day, filtered locally by company name, is the
    # efficient way to spend that budget.
    "alphavantage_api_key": os.environ.get("ALPHAVANTAGE_API_KEY", ""),
    "alphavantage_daily_limit": 20,
    # Optional: reads each headline's actual text via Claude Haiku instead of the
    # keyword lexicon — see llm_sentiment.py's docstring for exactly what this
    # does and doesn't claim. Off by default even with a key present; flip
    # "use_llm_sentiment" on once you've set ANTHROPIC_API_KEY.
    "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
    "use_llm_sentiment": bool(os.environ.get("ANTHROPIC_API_KEY")),
    "llm_daily_limit": 500,
}

# Chaywanaprash (chyawanprash — the Ayurvedic general tonic; same naming
# spirit as Trader Sahab / Sahab's Dimaag): the platform's own research
# analyst, not a trading signal — see chaywanaprash.py's docstring. A
# separate, small daily cap from NEWS['llm_daily_limit'] since this is one
# heavier on-demand call, not hundreds of small per-headline ones. Shares
# NEWS['anthropic_api_key'] rather than duplicating the key.
CHAYWANAPRASH = {
    # It runs when asked (POST /api/chaywanaprash/analyze) and once a week on
    # its own (the review below), so it is on whenever there is something to call.
    "enabled": True,
    # "auto" uses the Anthropic API when ANTHROPIC_API_KEY is set, and the
    # Claude Code CLI (`claude -p`, billed to your Claude plan) otherwise or
    # when the API call fails. Or pick one: "anthropic_api" / "claude_cli".
    "llm_backend": "auto",
    "daily_limit": 12,
    "lookback_hours": 24,
    # The fortnightly review: after the close, once every 7 days, it reads the
    # last 14 days of the journal with every change merged in that time and
    # the rules as they stand, and proposes. It changes nothing. 0 turns it off.
    "review_every_days": 7,
    "review_lookback_days": 14,
    "review_after": "15:40",
}

# Sahab's Research Desk (research_desk.py): TradingAgents-style research briefs.
# Research only — it never places an order and feeds no gate or position size.
# Off until switched on from the stock page, since one brief is about a dozen model calls.
RESEARCH_DESK = {
    "enabled": False,
    # "auto" uses the Anthropic API when ANTHROPIC_API_KEY is set, otherwise the
    # Claude Code CLI (`claude -p`, billed to your Claude plan). Or pick one:
    # "anthropic_api" / "claude_cli".
    "llm_backend": "auto",
    "analyst_model": "claude-haiku-4-5-20251001",  # the four analysts
    "team_model": "claude-sonnet-5",  # researchers, research manager, trader, risk team, portfolio manager
    # Thinking effort per call on the CLI backend (low / medium / high). At the CLI's default, one
    # brief took 317 s and the research manager alone used 68k input tokens across internal turns.
    "analyst_effort": "low",
    "team_effort": "medium",
    "debate_rounds": 1,
    # The rating's IC only counts sessions with 20+ rated stocks
    # (database.research_rating_ic), so a cap below that means it can never be measured.
    "daily_brief_limit": 25,
    "daily_cost_limit_usd": 10.0,  # list-price cost; on the CLI this is usage of your plan, not a bill
    "max_symbols_per_run": 25,
    "cli_timeout_s": 240,
}

RISK = {
    "max_risk_per_trade_pct": 1.0,
    "stop_loss_pct": 0.8,       # fallback when ATR isn't available yet
    "take_profit_pct": 1.6,
    "max_open_positions": 3,
    # Caps concurrent positions in the same industry (scanner row "industry"),
    # independent of max_open_positions — without this, 3 open positions could
    # easily all be the same sector on a strong-trend day (the scanner ranks by
    # sector momentum, so correlated picks are the *expected* output), which
    # undermines max_daily_loss_pct's implicit assumption of some independence
    # between positions. None disables the check.
    "max_positions_per_sector": 1,
    # Check stops on Kite's tick stream as well as on the 30-second poll, so a
    # breached stop is acted on in milliseconds instead of waiting up to a
    # full poll interval (worth ~Rs 12 on a Rs 33,000 position at the worst
    # case, on every losing trade). Needs a live Kite session for the feed,
    # but not live trading. Turning this off loses nothing else: the poll
    # keeps checking stops exactly as it always has. See stop_watcher.py.
    "tick_stops": True,
    # Cap each position's value at this % of capital. Without it, 1% risk
    # with a tight 5-min ATR stop sized trades at ~5x the account (median
    # Rs 4.8L notional on Rs 1L) and multiplied both losses and costs.
    "max_position_notional_pct": 33.0,
    "max_daily_loss_pct": 2.0,
    # Same confidence.py gate F&O uses (config.FNO["min_confidence_to_trade"]),
    # now applied to cash equity too: a checklist pass alone isn't enough — the
    # Dimaag Scorecard's system-wide evidence multiplier can cap confidence to
    # 0.25x when expectancy/DSR/IC haven't proven a real edge, which at this
    # threshold blocks entries outright until the Scorecard actually passes.
    # Validated (not "improved") via tune_entry_params.py's grid search (see
    # README): 60, paired with min_rrr=1.5 below, was the least-bad of 12
    # configs tried on a 55-day/100-stock backtest — still DSR 6.2%, well
    # under the 95% bar this codebase requires, so this is the current
    # default because nothing tried beat it, not because it's proven.
    "min_confidence_to_trade": 60,
    # Fallback only — overwritten in-process by trading_engine._sync_capital()
    # with the real Kite equity live_balance whenever Kite is connected (see
    # sync_capital_with_kite below), so position sizing is never computed
    # against a stale number that doesn't match what's actually funded.
    "total_capital": 100000,
    # In LIVE mode, keep total_capital equal to the real Kite account balance
    # instead of a static number — sizing math against a fictional capital
    # figure can pass every check here and still get rejected by Kite for
    # insufficient margin on a live order; syncing removes that whole failure
    # class. Set False to pin total_capital manually (both modes) instead.
    "sync_capital_with_kite": True,
    # In PAPER mode, size against this fixed figure instead of the real Kite
    # balance — real accounts are often funded far below what a realistic
    # test day needs (₹683 sizes to 0 shares for nearly every NIFTY-100
    # stock at 1% risk), which would make paper mode produce no trades to
    # review. This never touches real money either way; it only changes what
    # the simulator sizes against. Live mode always uses the real balance
    # above, regardless of this number.
    "paper_capital": 100000.0,
    # ATR-based stop/target adapt to each symbol's actual volatility instead
    # of a flat percentage — set False to use stop_loss_pct/take_profit_pct only.
    "use_atr_risk": True,
    "atr_period": 14,
    "atr_sl_multiplier": 1.5,
    "atr_tp_multiplier": 3.0,
    # Step trailing stop: after this many R in profit, move the stop up 1R at a time
    # (1 = breakeven at +1R, +1R locked at +2R). None disables it.
    "trail_after_r": None,
}

# Order-book sampling (depth_sampler.py): one Kite quote call per engine tick
# for the watchlist, rows to depth_samples. Pure data collection for a future
# brain built on the book rather than on candle shapes (README section 69/71).
DEPTH_SAMPLER = {
    "enabled": True,
    # Overnight-hold research (README section 81): the ETFs' own books and the
    # index level, only inside the exit window after the open and the entry
    # window before the close. Times are IST, [start, end).
    "window_symbols": ["NIFTYBEES", "SETFNIF50"],
    "window_indices": ["NIFTY 50"],
    "windows": [["09:15", "09:30"], ["15:00", "15:30"]],
}

# The paper momentum book (momentum_book.py, README section 83): the
# positional strategy that passed 3i. Paper only; an evening job in its own
# process after the close. The forward band switches it off automatically.
MOMENTUM_BOOK = {
    "enabled": True,
    "capital": 1_000_000.0,        # paper capital for the book (separate from intraday)
    "universe": 200,
    "hold": 15,
    "rank_keep": 30,
    "slippage": 0.0005,
    # Trial 126's figures: the rule on repaired prices with orders that wait
    # (README section 99). They were 0.0082 and 0.0387, trial 120's, until the
    # owner's decision of 2026-09-29. The change moves the six-month floor from
    # -14.0% to -14.8%.
    "expected_monthly_excess": 0.0071,
    "monthly_excess_sd": 0.0389,
    "band_from_month": 6,
    "job_after": "19:30",
    "job_until": "23:30",
    "retry_minutes": 30,
}

# The Jev book (jev_book.py, README section 86): a forward paper test of the
# TypeSafe Jev LLM judge on the scanner's daily shortlist — buy / short / skip
# at 09:45, closed at the 15:08 square-off. Paper only; never places an order.
# Needs a TypeSafe API key (TYPESAFE_API_KEY, or `typesafe_key.py set`);
# until then it records "Jev unavailable" and trades nothing.
JEV_BOOK = {
    "enabled": True,
    "decide_at": "09:45",
    "max_names": 15,
    "notional": 100_000.0,
    "timeout_s": 90,
    "kill_after": 100,          # pre-registered kill rule (prereg-jev-book.md)
    "kill_t": -2.0,
    "endpoint": "https://api.typesafe.ai/v1/systemone",   # TypeSafe's official API
    "model": "jev-latest",
}

# Liquidity check (liquidity.py): read Kite's five-level book just before an
# entry, and refuse it when the spread is wider than the cost model allows
# (2 x COSTS["slippage_pct"], derived rather than set here), when filling our
# quantity walks the book further than that slippage, or when either the
# entry or the exit side holds under min_depth_multiple x our quantity.
# Paper entries go ahead when no depth can be read (recorded as unchecked);
# live entries do not. Every reading is logged to liquidity_checks.
LIQUIDITY = {
    "enabled": True,
    "min_depth_multiple": 3.0,
}

# NSE cash market hours (IST)
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"
# Auto square-off: close all open positions at this time to avoid overnight risk
# (or an MIS auto square-off penalty from the broker).
# 15:08, not 15:15 (#78). Since the closing auction started on 2026-08-03,
# Zerodha auto-squares MIS positions in closing-auction (F&O-eligible) stocks
# at 15:12 and charges Rs 50 + GST per auto square-off order; continuous
# trading in them stops at 15:15. Nearly the whole NIFTY 100 is F&O-eligible,
# so one time for every stock, with room for order latency before 15:12.
# Non-auction stocks could run to 15:25; one earlier cutoff costs them little.
SQUARE_OFF_TIME = "15:08"

POLL_INTERVAL_SECONDS = 30

# Pre-open Kite check (trading_engine._check_preopen_kite): Zerodha ends every
# session at 06:00 IST, so a trading day that starts without a fresh login runs
# on delayed data and can't place live orders. From this time until the close,
# the first tick of a trading day that finds Kite not live raises one
# error-level alert (browser push). Later than 08:45 still counts: a Mac that
# slept through the morning alerts on its first tick after waking.
PREOPEN_KITE_CHECK_TIME = "08:45"

# F&O (options-buying only — see backend/fno_risk.py's docstring for why
# writing/selling and futures are deliberately out of scope). This is a
# SEPARATE opt-in from PAPER_MODE_DEFAULT/the dashboard's Live toggle: an
# order only reaches Kite when BOTH paper_mode is off AND enabled is True
# here, so switching cash equity live never silently turns this on too.
# Manual review queue (review_queue.py). A setup that misses the entry by
# exactly one required checklist item — or passes the checklist and is
# stopped only by the confidence gate — is put in front of the user as a card
# instead of being skipped. Approving overrides that ONE gate; every risk
# limit (daily loss, max positions, sector cap, one entry per stock per day,
# entry window, sizing, liquidity) is re-checked at the moment of approval.
# Off by default and not persisted: a restart turns it off again. In live
# mode each approval needs its own real-money confirmation.
REVIEW_QUEUE = {
    "enabled": False,
    "expiry_seconds": 300,          # a card older than this can't be approved; prices move
}

FNO = {
    "enabled": False,
    "capital": 10000.0,             # ring-fenced sub-allocation of RISK.total_capital, not the whole account
    "max_premium_risk_pct": 20.0,   # % of FNO capital a single trade's premium may risk (its whole max loss)
    "min_confidence_to_trade": 60,  # 0-100 confidence.py score; below this, no order (see confidence.py)
    "underlyings": [],              # NSE symbols to trade options on; empty = every symbol the scanner already tracks
    "index_underlyings": ["NIFTY", "BANKNIFTY"],
    "prefer_weekly_for_index": False,   # nearest MONTHLY expiry by default — weekly theta decay is the
                                         # single biggest documented cause of retail option-buyer losses
    "min_days_to_expiry": 5,        # skip contracts expiring too soon — same theta-decay reasoning
    "max_days_to_expiry": 35,
    "target_delta": 0.45,           # near-the-money: enough sensitivity to the underlying's move to matter,
                                     # without paying for pure time value far ITM/OTM
    "stop_loss_pct_of_premium": 40.0,   # exit if premium held falls this % from entry
    "target_pct_of_premium": 80.0,      # exit if premium held rises this % from entry
    "risk_free_rate_pct": 7.0,      # for the Black-Scholes IV solve — approx. India 91-day T-bill
}

# Approximate retail intraday-equity (MIS) cost structure, modeled on
# Zerodha's published tariff (percentages change occasionally — check your
# broker's current cost sheet before relying on these for sizing decisions).
# Used by backend/costs.py, currently applied in the backtester.
COSTS = {
    "brokerage_per_order": 20.0,     # flat fee per executed order (buy or sell)...
    "brokerage_pct": 0.03,           # ...or this % of order value, whichever is lower
    "stt_pct_sell": 0.025,           # securities transaction tax, sell side only (intraday equity)
    # Rates below re-checked against zerodha.com/charges on 2026-09-23 (#79).
    "exchange_txn_pct": 0.00307,     # NSE transaction charges, both sides (BSE is 0.00375)
    "sebi_charges_pct": 0.0001,      # both sides (Rs 10/crore)
    "ipft_pct": 0.0000001,           # NSE Investor Protection Fund Trust, Rs 0.01/crore, both sides
    "stamp_duty_pct_buy": 0.003,     # buy side only
    "gst_pct": 18.0,                 # on (brokerage + SEBI charges + transaction charges + IPFT)
    # Estimated slippage per leg between the price a signal fires at and the
    # actual fill — market orders on 5-min bars won't fill at the exact
    # close. This is a rough estimate, not measured; real slippage depends
    # on the symbol's liquidity, order size, and volatility at that moment.
    "slippage_pct": 0.03,
}

# Zerodha Kite Connect — needed for live order placement, and used for
# real-time market data (instead of yfinance's ~15-min-delayed feed) when
# credentials are present. Requires the paid Kite Connect API subscription
# (~Rs 500/month at developers.kite.trade) for market data; order placement
# alone is free. Run generate_access_token.py each morning to refresh
# KITE_ACCESS_TOKEN (Kite sessions expire daily) — env vars below take
# priority over the .kite_session.json file that script writes.
KITE_API_KEY = os.environ.get("KITE_API_KEY", _session.get("api_key", ""))
KITE_API_SECRET = os.environ.get("KITE_API_SECRET", _session.get("api_secret", ""))
KITE_ACCESS_TOKEN = os.environ.get("KITE_ACCESS_TOKEN", _session.get("access_token", ""))
KITE_SESSION_GENERATED_AT = _session.get("generated_at")

# Where the backend itself is reachable — used only to build the Kite
# "Redirect URL" you must register in your Kite Connect app's settings
# (developers.kite.trade) so Kite knows where to send the user back to
# after login. Override with BACKEND_BASE_URL if not running on localhost:8000.
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://127.0.0.1:8000")

# The Kite login tunnel (kite_tunnel.py). Kite only accepts an HTTPS Redirect
# URL, so the one registered at developers.kite.trade is this ngrok static
# domain. The backend starts ngrok on it when a login starts and stops it once
# the callback arrives (or after max_seconds), so nobody has to remember to
# run ngrok before clicking Reconnect. Set NGROK_DOMAIN to change it, or
# "enabled": False to manage the tunnel by hand.
KITE_TUNNEL = {
    "enabled": True,
    "domain": os.environ.get("NGROK_DOMAIN", "ambiguity-patchy-untold.ngrok-free.dev"),
    "backend_port": 8000,
    "api_port": 4040,          # ngrok's local agent API, used to see when the tunnel is up
    "start_timeout_s": 15,
    "max_seconds": 600,
}
# What to register as the Redirect URL at developers.kite.trade, and what the
# dashboard shows as the redirect: the tunnel's HTTPS URL when it's on.
KITE_REDIRECT_URL = (f"https://{KITE_TUNNEL['domain']}/kite/callback" if KITE_TUNNEL["enabled"] and KITE_TUNNEL["domain"]
                     else f"{BACKEND_BASE_URL}/kite/callback")

# CORS — was wide open ("*"), flagged by a multi-expert review since this API carries
# real trading control behind an X-Api-Key/?key= param, and a wildcard plus a key that
# can travel in a URL is a worse combination than either alone. Defaults to the actual
# dev origins this app uses (Vite's localhost:5500 and both IPv4/hostname spellings);
# override with a comma-separated CORS_ALLOWED_ORIGINS env var if you serve the frontend
# from somewhere else. This does NOT affect the Kite OAuth redirect (a server-side
# redirect, not a browser CORS request) or the ngrok tunnel used only for that redirect.
CORS_ALLOWED_ORIGINS = (
    os.environ["CORS_ALLOWED_ORIGINS"].split(",") if os.environ.get("CORS_ALLOWED_ORIGINS") else
    ["http://localhost:5500", "http://127.0.0.1:5500"]
)


def save_kite_session(access_token: str) -> None:
    """Persist today's Kite access token and update the already-imported
    config values in-process, so callers don't need a restart to pick it
    up — used by both generate_access_token.py and the dashboard's in-app
    'Connect Kite' flow (app.py)."""
    global KITE_ACCESS_TOKEN, KITE_SESSION_GENERATED_AT
    KITE_SESSION_GENERATED_AT = datetime.now(timezone.utc).isoformat()
    SESSION_FILE.write_text(json.dumps({
        "api_key": KITE_API_KEY,
        "api_secret": KITE_API_SECRET,
        "access_token": access_token,
        "generated_at": KITE_SESSION_GENERATED_AT,
    }, indent=2))
    SESSION_FILE.chmod(0o600)  # contains a live credential — owner-read/write only
    KITE_ACCESS_TOKEN = access_token

# SEBI's retail algo framework (mandatory from 2026-04-01) requires MARKET
# orders to carry a market_protection percentage or they're rejected — see
# kite_broker.py. It also requires a static IP whitelisted on your Kite
# Connect developer dashboard before placing any live order — this is not
# optional and isn't something this code can do for you.
KITE_MARKET_PROTECTION_PCT = 1

# After a live order is sent, how long to wait for Kite to report it finished
# before cancelling whatever hasn't filled, and how often to ask (#155). The
# wait runs on the thread that sent the order, so it holds up the tick.
KITE_FILL_DEADLINE_S = 5
KITE_FILL_POLL_S = 0.25

# Whether to use Kite for market data (real-time) instead of yfinance
# (~15-min delayed). Only takes effect once KITE_API_KEY/KITE_ACCESS_TOKEN
# are set — falls back to yfinance automatically otherwise. See
# data_provider.py.
USE_KITE_DATA = True
