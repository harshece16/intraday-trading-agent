"""
Real NSE sectoral indices — not the scanner's own same-universe-subset
average (`by_sector` in scanner.py, still computed as before), but the
actual published index level (Nifty Bank, Nifty IT, Nifty Auto, ...). This
adds one more confluence check to intraday_score()'s existing sector-rank
evidence; it doesn't replace it. The two are complementary, not redundant:
`sector_rank` reads today's live move across this universe's own subset of
each sector, while this module reads the real index's own slower-moving
daily trend (EMA20/50, same computation daily_profile() uses elsewhere) —
one same-day, one structural.

Only industries with a verified, real, sufficient-history yfinance ticker
are mapped here; every other industry simply isn't checked by this module
(falls through to sector_rank alone), rather than being assigned an
invented ticker. Checked live via yfinance on 2026-09-15 (6mo daily
history): NIFTY_FIN_SERVICE.NS, ^CNXAUTO, ^CNXPHARMA, ^CNXFMCG, ^CNXMETAL,
^CNXENERGY, ^CNXIT and ^CNXREALTY all returned ~80+ real daily bars.
NIFTY_OIL_AND_GAS.NS and NIFTY_CONSR_DURBL.NS resolved as tickers but
returned only 1 row of history each — left out rather than used with
insufficient data to compute a trend from.

"Healthcare" is mapped to Nifty Pharma as the closest real index available;
this is a stated approximation, not an exact match — this universe's
Healthcare category also includes hospital/diagnostics names Nifty Pharma
doesn't track. "Power" and "Oil Gas & Consumable Fuels" both map to Nifty
Energy, which genuinely spans both in NSE's own index construction, not an
approximation.

Since 16 Sep 2026 yfinance has served one daily bar, today's, for six of
the eight (all but ^CNXIT and ^CNXPHARMA), and the trend was silently
skipped for 61 of the 100 stocks (#197). A series short of MIN_BARS is now
completed from NSE's own index closing files for the last 60 sessions
(nse_feed.index_history), and the scanner result names every industry whose
trend still could not be worked out.
"""

import bisect

import indicators as ind

SECTOR_INDEX_TICKERS = {
    "Financial Services": "NIFTY_FIN_SERVICE.NS",
    "Automobile and Auto Components": "^CNXAUTO",
    "Healthcare": "^CNXPHARMA",
    "Fast Moving Consumer Goods": "^CNXFMCG",
    "Metals & Mining": "^CNXMETAL",
    "Power": "^CNXENERGY",
    "Oil Gas & Consumable Fuels": "^CNXENERGY",
    "Information Technology": "^CNXIT",
    "Realty": "^CNXREALTY",
}

TICKERS = sorted(set(SECTOR_INDEX_TICKERS.values()))
MIN_BARS = 51    # EMA50 plus one; also covers the 10-session relative strength


def _date(bar):
    return bar["time"][:10]


def _before(bars, session):
    return [b for b in bars if _date(b) < session]


def short_of_history(daily_batch, session):
    """The sector index tickers with fewer than MIN_BARS daily bars before `session`."""
    return [t for t in TICKERS if len(_before(daily_batch.get(t) or [], session)) < MIN_BARS]


def complete_from_nse(daily_batch, session, history, tickers=None):
    """Complete each sector index series that is short of history with NSE's
    own daily bars (nse_feed.index_history). NSE's bar is kept for every
    session its files have, and the feed's only for a session they lack, so
    no session appears twice. Changes `daily_batch` in place and returns the
    tickers (of `tickers`, or all) that now have MIN_BARS bars before `session`."""
    nse = (history or {}).get("bars") or {}
    done = []
    for t in short_of_history(daily_batch, session):
        if (tickers is not None and t not in tickers) or not nse.get(t):
            continue
        by_date = {_date(b): b for b in daily_batch.get(t) or []}
        by_date.update({_date(b): dict(b) for b in nse[t]})
        daily_batch[t] = [by_date[d] for d in sorted(by_date)]
        if len(_before(daily_batch[t], session)) >= MIN_BARS:
            done.append(t)
    return done


def unavailable(sector_trends):
    """The industries with a real index whose trend could not be worked out."""
    return sorted(i for i, tr in sector_trends.items() if tr is None and i in SECTOR_INDEX_TICKERS)


def _close_on_or_before(dates, closes, d):
    i = bisect.bisect_right(dates, d) - 1
    return closes[i] if i >= 0 else None


def sector_trend(daily_batch, industry, nifty_dates, nifty_closes, session):
    """Real index-level daily trend + 10-day relative strength vs NIFTY for
    one industry, computed the same way daily_profile() computes it for a
    single stock. Returns None when this industry has no verified real
    ticker, or fewer than MIN_BARS sessions are known for it even after
    complete_from_nse()."""
    ticker = SECTOR_INDEX_TICKERS.get(industry)
    if not ticker:
        return None
    bars = _before(daily_batch.get(ticker, []), session)
    if len(bars) < MIN_BARS:
        return None
    closes = [b["close"] for b in bars]
    close = closes[-1]
    e20, e50 = ind.ema(closes, 20), ind.ema(closes, 50)
    trend = "up" if close > e20 > e50 else "down" if close < e20 < e50 else "sideways"

    rs10 = None
    ret10 = (close / closes[-11] - 1) * 100
    n_now = _close_on_or_before(nifty_dates, nifty_closes, _date(bars[-1]))
    n_then = _close_on_or_before(nifty_dates, nifty_closes, _date(bars[-11]))
    if n_now and n_then:
        rs10 = round(ret10 - (n_now / n_then - 1) * 100, 2)

    return {"ticker": ticker, "trend": trend, "rs10": rs10}
