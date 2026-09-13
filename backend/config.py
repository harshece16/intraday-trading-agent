"""
Configuration for the intraday trading dashboard.
"""

import json
import os
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

# PAPER_MODE True = simulated orders only (default, safe).
# Flip via the dashboard toggle or by setting this False + restarting.
PAPER_MODE_DEFAULT = True

# NSE symbols (without the .NS suffix — that's added automatically for yfinance).
WATCHLIST = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]

# Intraday candle interval used for signals. yfinance supports 1m/2m/5m/15m/30m/60m.
# 5m is a reasonable default — 1m data is noisy and yfinance only keeps ~7 days of it.
CANDLE_INTERVAL = "5m"

STRATEGY = "trader_brain"  # or "sma_crossover" / "rsi_reversion"
STRATEGY_PARAMS = {
    # Multi-factor confluence engine — see trader_brain.py for every rule.
    "trader_brain": {
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
        "use_news": True,
        "news_weight": 2.0,
        "news_veto": -0.5,          # sentiment at/below this blocks new longs
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
    "active_count": 6,               # stocks the engine actively evaluates for entries
    "allow_shorts": True,            # rank each stock long AND short; keep the stronger side
    "counter_trend_active_count": 2, # max picks against the market bias (longs on risk-off, shorts on risk-on)
    "deep_analysis": 15,             # top candidates that get a full Trader Brain + news read
    "min_score": 20,
    "pinned": [],                    # always tracked, e.g. ["RELIANCE"]
    # Tradability floors (intraday checklist: liquid, moves enough to beat costs)
    "min_price": 100,
    "min_turnover_cr": 50,
    "min_atr_pct": 1.2,
    "max_gap_pct": 3.0,
    "use_news": True,
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
}

RISK = {
    "max_risk_per_trade_pct": 1.0,
    "stop_loss_pct": 0.8,       # fallback when ATR isn't available yet
    "take_profit_pct": 1.6,
    "max_open_positions": 3,
    # Cap each position's value at this % of capital. Without it, 1% risk
    # with a tight 5-min ATR stop sized trades at ~5x the account (median
    # Rs 4.8L notional on Rs 1L) and multiplied both losses and costs.
    "max_position_notional_pct": 33.0,
    "max_daily_loss_pct": 2.0,
    "total_capital": 100000,
    # ATR-based stop/target adapt to each symbol's actual volatility instead
    # of a flat percentage — set False to use stop_loss_pct/take_profit_pct only.
    "use_atr_risk": True,
    "atr_period": 14,
    "atr_sl_multiplier": 1.5,
    "atr_tp_multiplier": 3.0,
}

# NSE cash market hours (IST)
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"
# Auto square-off: close all open positions at this time to avoid overnight risk
# (or an MIS auto square-off penalty from the broker).
SQUARE_OFF_TIME = "15:15"

POLL_INTERVAL_SECONDS = 30

# Approximate retail intraday-equity (MIS) cost structure, modeled on
# Zerodha's published tariff (percentages change occasionally — check your
# broker's current cost sheet before relying on these for sizing decisions).
# Used by backend/costs.py, currently applied in the backtester.
COSTS = {
    "brokerage_per_order": 20.0,     # flat fee per executed order (buy or sell)...
    "brokerage_pct": 0.03,           # ...or this % of order value, whichever is lower
    "stt_pct_sell": 0.025,           # securities transaction tax, sell side only (intraday equity)
    "exchange_txn_pct": 0.00297,     # NSE transaction charges, both sides
    "sebi_charges_pct": 0.0001,      # both sides
    "stamp_duty_pct_buy": 0.003,     # buy side only
    "gst_pct": 18.0,                 # on (brokerage + exchange transaction charges)
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
KITE_REDIRECT_URL = f"{BACKEND_BASE_URL}/kite/callback"


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

# Whether to use Kite for market data (real-time) instead of yfinance
# (~15-min delayed). Only takes effect once KITE_API_KEY/KITE_ACCESS_TOKEN
# are set — falls back to yfinance automatically otherwise. See
# data_provider.py.
USE_KITE_DATA = True
