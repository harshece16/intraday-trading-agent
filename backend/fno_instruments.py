"""
Resolves a tradable NFO (NSE F&O) option contract for an underlying, from
Kite Connect's own live instrument dump — never a hardcoded lot size or
expiry list, since both change (SEBI reset the minimum index-contract value
to Rs 15-20 lakh in Nov 2024, which changed NIFTY's lot size outright; lot
sizes and expiries are reset by the exchange, not something to freeze in
code). Requires a working Kite connection; there is no options-chain data
source in this app otherwise (yfinance doesn't carry NSE F&O).
"""

import logging
import time
from datetime import datetime, date

import config

logger = logging.getLogger("trading_bot")

_cache = {"ts": 0.0, "rows": []}
CACHE_TTL_SECONDS = 3600  # the instrument list changes at most once a day (new expiries listed)


def _get_kite():
    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=config.KITE_API_KEY)
    kite.set_access_token(config.KITE_ACCESS_TOKEN)
    return kite


def _nfo_instruments():
    if time.time() - _cache["ts"] < CACHE_TTL_SECONDS and _cache["rows"]:
        return _cache["rows"]
    rows = _get_kite().instruments("NFO")
    _cache.update(ts=time.time(), rows=rows)
    return rows


def available() -> bool:
    return bool(config.KITE_API_KEY and config.KITE_ACCESS_TOKEN)


def nearest_expiry(underlying: str, min_days: int, max_days: int, prefer_weekly: bool, today: date = None):
    """The soonest listed expiry for this underlying that's at least
    `min_days` out — skipping this-week/near expiries is deliberate: NISM
    and Murphy both note time decay (theta) accelerates hardest in an
    option's final days, which is the single most-cited cause of retail
    option-buyer losses. `prefer_weekly` only matters for the two index
    underlyings NSE lists weeklies for; single-stock options are monthly
    only regardless."""
    today = today or datetime.now().date()
    rows = [r for r in _nfo_instruments() if r["name"] == underlying and r["instrument_type"] in ("CE", "PE")]
    expiries = sorted({r["expiry"] if isinstance(r["expiry"], date) else
                       datetime.strptime(str(r["expiry"])[:10], "%Y-%m-%d").date()
                       for r in rows})
    candidates = [e for e in expiries if min_days <= (e - today).days <= max_days]
    if not candidates:
        return None
    if prefer_weekly:
        return candidates[0]
    # Monthly = the last expiry in its calendar month; pick the nearest one of those.
    monthlies = [e for e in expiries if e == max(x for x in expiries if x.month == e.month and x.year == e.year)]
    monthly_candidates = [e for e in candidates if e in monthlies]
    return monthly_candidates[0] if monthly_candidates else candidates[0]


def find_contract(underlying: str, spot: float, expiry: date, is_call: bool, target_delta: float, greeks_fn):
    """Pick the strike closest to `target_delta` among this underlying's
    listed strikes for `expiry` — near-the-money without paying for pure
    time value deep in/out of the money. `greeks_fn(spot, strike, t_years,
    is_call) -> delta` lets the caller supply a live-IV-aware delta; this
    module only resolves the contract, options_pricing.py does the math."""
    rows = [r for r in _nfo_instruments() if r["name"] == underlying
            and r["instrument_type"] == ("CE" if is_call else "PE")]
    rows = [r for r in rows if (r["expiry"] if isinstance(r["expiry"], date) else
            datetime.strptime(str(r["expiry"])[:10], "%Y-%m-%d").date()) == expiry]
    if not rows:
        return None
    t_years = max((expiry - datetime.now().date()).days, 1) / 365
    scored = []
    for r in rows:
        try:
            d = abs(greeks_fn(spot, r["strike"], t_years, is_call))
        except Exception:
            continue
        scored.append((abs(d - target_delta), r))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0])
    best = scored[0][1]
    return {
        "tradingsymbol": best["tradingsymbol"], "instrument_token": best["instrument_token"],
        "strike": best["strike"], "lot_size": best["lot_size"], "expiry": expiry,
        "is_call": is_call, "underlying": underlying,
    }
