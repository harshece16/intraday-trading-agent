"""
Black-Scholes-Merton pricing and Greeks for a European-style equity/index
option, plus an implied-volatility solve from a live market premium.

The Greeks themselves — Delta, Gamma, Theta, Vega — are defined here exactly
as NISM Series VIII (Equity Derivatives workbook, ch on Option Trading
Strategies / Greeks) defines them:
  Delta = change in option premium / unit change in the underlying's price
  Gamma = change in an option's delta / unit change in the underlying's price
  Theta = change in an option premium / change in time to expiry
  Vega  = change in an option premium / change in (assumed) volatility

NSE options are American-style, but Black-Scholes (European) is the
standard, industry-normal approximation for near-the-money index/liquid
single-stock options where early exercise is rarely optimal — it is not a
perfect model, and its own limits (constant volatility, no dividends here)
are real. Kite Connect gives OHLC + open interest for F&O contracts but not
implied volatility or Greeks directly, so IV is solved for here, by
inverting Black-Scholes against the option's own live premium (bisection),
rather than assumed.
"""

import math
from statistics import NormalDist

_N = NormalDist()


def _d1_d2(spot, strike, t_years, vol, r):
    if t_years <= 0 or vol <= 0:
        return None, None
    d1 = (math.log(spot / strike) + (r + 0.5 * vol ** 2) * t_years) / (vol * math.sqrt(t_years))
    d2 = d1 - vol * math.sqrt(t_years)
    return d1, d2


def price(spot, strike, t_years, vol, r, is_call: bool) -> float:
    """Black-Scholes-Merton theoretical premium."""
    d1, d2 = _d1_d2(spot, strike, t_years, vol, r)
    if d1 is None:
        return max(0.0, (spot - strike) if is_call else (strike - spot))
    if is_call:
        return spot * _N.cdf(d1) - strike * math.exp(-r * t_years) * _N.cdf(d2)
    return strike * math.exp(-r * t_years) * _N.cdf(-d2) - spot * _N.cdf(-d1)


def greeks(spot, strike, t_years, vol, r, is_call: bool) -> dict:
    """Delta, Gamma, Theta (per calendar day), Vega (per 1 vol point) — the
    four Greeks NISM Series VIII actually covers for a retail option buyer.
    Delta sign matches NISM's own convention: positive for a long call,
    negative for a long put."""
    d1, d2 = _d1_d2(spot, strike, t_years, vol, r)
    if d1 is None:
        return {"delta": 1.0 if (is_call and spot > strike) else (-1.0 if not is_call and spot < strike else 0.0),
                "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    pdf_d1 = _N.pdf(d1)
    gamma = pdf_d1 / (spot * vol * math.sqrt(t_years))
    vega = spot * pdf_d1 * math.sqrt(t_years) / 100  # per 1 percentage-point change in vol
    if is_call:
        delta = _N.cdf(d1)
        theta_year = (-spot * pdf_d1 * vol / (2 * math.sqrt(t_years))
                      - r * strike * math.exp(-r * t_years) * _N.cdf(d2))
    else:
        delta = _N.cdf(d1) - 1
        theta_year = (-spot * pdf_d1 * vol / (2 * math.sqrt(t_years))
                      + r * strike * math.exp(-r * t_years) * _N.cdf(-d2))
    return {"delta": round(delta, 4), "gamma": round(gamma, 6),
            "theta": round(theta_year / 365, 4), "vega": round(vega, 4)}


def implied_volatility(market_premium, spot, strike, t_years, r, is_call: bool,
                        lo=0.01, hi=4.0, tol=1e-4, max_iter=60):
    """Solve for the volatility Black-Scholes needs to reproduce the option's
    actual traded premium, by bisection (monotonic in vol, so bisection is
    robust even though it's slower than Newton-Raphson). Returns None if the
    premium is outside any volatility's reachable range (e.g. stale/bad
    quote) rather than returning a meaningless number."""
    if t_years <= 0 or market_premium <= 0:
        return None
    lo_price, hi_price = price(spot, strike, t_years, lo, r, is_call), price(spot, strike, t_years, hi, r, is_call)
    if not (lo_price <= market_premium <= hi_price):
        return None
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        p = price(spot, strike, t_years, mid, r, is_call)
        if abs(p - market_premium) < tol:
            return round(mid, 4)
        if p < market_premium:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 4)


def analyze(market_premium, spot, strike, t_years, r, is_call: bool) -> dict:
    """One call for everything a trade decision needs: the solved IV, and
    the Greeks at that IV. Returns a `note` instead of numbers when the
    quote can't be solved (e.g. zero open interest, stale premium)."""
    iv = implied_volatility(market_premium, spot, strike, t_years, r, is_call)
    if iv is None:
        return {"iv": None, "note": "Could not solve implied volatility from this premium — "
                                     "likely a stale or illiquid quote. Skipping this contract."}
    g = greeks(spot, strike, t_years, iv, r, is_call)
    return {"iv_pct": round(iv * 100, 1), **g}
