"""
Market scanner — decides WHAT to trade (and which side); Sahab's Dimaag then
decides WHEN.

Professional intraday traders don't stare at a fixed list; before and during
the session they narrow a liquid universe down to the handful of stocks that
are actually "in play" — leaders to buy on strong days, laggards to short on
weak ones. This encodes that routine over the NIFTY 100:

  Market context   NIFTY trend and day change, breadth (advancers/decliners),
                   India VIX. The bias blocks entries against it (the engine's
                   market filter); only score mode also caps picks against it.
  Tradability      price, turnover and daily ATR% floors — a stock that
                   doesn't move 1.2%+ a day can't pay for intraday costs.
  Daily setup      daily trend (EMA20/50), 10-day relative strength vs NIFTY,
                   distance from 52-week high/low, NR7 / inside-day
                   compression, daily RSI.
  In play today    gap %, time-of-day-adjusted relative volume, relative
                   strength vs NIFTY today, VWAP side, opening-range
                   breakout/breakdown, sector leadership.
  Catalysts        NSE filings + market news mentioning the company.
  Event risk       results due today/next session → no new trades.

Every stock is scored as a long AND as a short; the stronger side is kept.

Which stocks are watched depends on SCANNER["selection"] (README section 91):
  "liquidity"      The default. The day's list is the active_count eligible
                   stocks with the highest 20-day average turnover, fixed
                   before the open and kept all day. No score chooses it; the
                   list gets the Sahab's Dimaag read (with per-stock news).
  "score"          The old list. The top candidates get the Dimaag read and
                   the best final scores become the active watchlist, chosen
                   again every scan (select_active).
"""

import bisect
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

import bulkowski
import config
import data_provider
import database
import fundamentals
import indicators as ind
import news_sentiment
import nse_feed
import seasonality
import sectoral_indices
import swing_patterns
import universe
from trader_brain import trader_brain_signal

logger = logging.getLogger("trading_bot")
IST = ZoneInfo("Asia/Kolkata")
NIFTY = "^NSEI"
VIX = "^INDIAVIX"
NIFTY_QUOTE = "NIFTY 50"        # the index's name in Kite's quotes
SESSION_OPEN_MINUTE = 9 * 60 + 15
SESSION_MINUTES = 375           # 09:15 to 15:30
BAR_MINUTES = 5
LIVE_DAY_MIN_SHARE = 0.5        # of the universe trading, for the quotes to count as a session


def yf_ticker(symbol):
    return symbol if symbol.startswith("^") or symbol.endswith(".NS") else f"{symbol}.NS"


def _r(x, nd=2):
    return round(x, nd) if isinstance(x, float) else x


def _date(bar):
    return bar["time"][:10]


def download_batch(tickers, period, interval):
    """One yfinance request for many tickers -> {ticker: [candle, ...]} with IST timestamps."""
    df = data_provider.yf_download(tickers=tickers, period=period, interval=interval, group_by="ticker",
                                   progress=False, threads=True, auto_adjust=False)
    out = {}
    if df is None or df.empty:
        return out
    if df.index.tz is not None:
        df.index = df.index.tz_convert(IST)
    multi = isinstance(df.columns, pd.MultiIndex)
    level0 = set(df.columns.get_level_values(0)) if multi else set()
    for t in tickers:
        if multi and t not in level0:
            continue
        sub = (df[t] if multi else df).dropna(subset=["Close"])
        if sub.empty:
            continue
        vols = sub["Volume"].fillna(0)
        out[t] = [
            {"time": ts.isoformat(), "open": float(o), "high": float(h), "low": float(l),
             "close": float(c), "volume": int(v)}
            for ts, o, h, l, c, v in zip(sub.index, sub["Open"], sub["High"], sub["Low"], sub["Close"], vols)
        ]
    return out


def _close_on_or_before(dates, closes, d):
    i = bisect.bisect_right(dates, d) - 1
    return closes[i] if i >= 0 else None


def daily_profile(bars, nifty_dates, nifty_closes, before_date):
    """Daily-chart facts using only sessions strictly before `before_date` (no look-ahead)."""
    bars = [b for b in bars if _date(b) < before_date]
    if len(bars) < 60:
        return None
    closes = [b["close"] for b in bars]
    last, prev = bars[-1], bars[-2]
    close = last["close"]
    atr_v = ind.atr(bars, 14)
    e20, e50 = ind.ema(closes, 20), ind.ema(closes, 50)
    trend = "up" if close > e20 > e50 else "down" if close < e20 < e50 else "sideways"
    ret10 = (close / closes[-11] - 1) * 100
    n_now = _close_on_or_before(nifty_dates, nifty_closes, _date(last))
    n_then = _close_on_or_before(nifty_dates, nifty_closes, _date(bars[-11]))
    rs10 = ret10 - (n_now / n_then - 1) * 100 if n_now and n_then else None
    year = bars[-250:]
    high52 = max(b["high"] for b in year)
    low52 = min(b["low"] for b in year)
    ranges = [b["high"] - b["low"] for b in bars[-7:]]
    # 60-day beta vs NIFTY (Varsity Futures ch 11): slope of stock returns on index returns.
    stock_rets, index_rets = [], []
    for a, b in zip(bars[-61:-1], bars[-60:]):
        na = _close_on_or_before(nifty_dates, nifty_closes, _date(a))
        nb = _close_on_or_before(nifty_dates, nifty_closes, _date(b))
        if na and nb:
            stock_rets.append(b["close"] / a["close"] - 1)
            index_rets.append(nb / na - 1)
    beta = None
    if len(index_rets) >= 30:
        mean_i, mean_s = sum(index_rets) / len(index_rets), sum(stock_rets) / len(stock_rets)
        var = sum((x - mean_i) ** 2 for x in index_rets)
        if var:
            beta = sum((x - mean_i) * (y - mean_s) for x, y in zip(index_rets, stock_rets)) / var
    swing = swing_patterns.scan_daily_patterns(bars, atr_v) if atr_v else []
    reversal_day = swing_patterns.detect_reversal_day(bars, atr_v) if atr_v else None
    return {
        "beta": beta,
        "swing_patterns": swing,
        "reversal_day": reversal_day,
        "close": close,
        "atr_pct": atr_v / close * 100 if atr_v else 0.0,
        "turnover_cr": sum(b["close"] * b["volume"] for b in bars[-20:]) / 20 / 1e7,
        "trend": trend,
        "rsi": ind.rsi(closes[-100:], 14),
        "rs10": rs10,
        "pct_from_high": (high52 - close) / high52 * 100,
        "pct_from_low": (close - low52) / low52 * 100,
        "nr7": ranges[-1] == min(ranges),
        "inside_day": last["high"] <= prev["high"] and last["low"] >= prev["low"],
    }


class _Points:
    def __init__(self):
        self.score = 0.0
        self.items = []

    def add(self, pts, text):
        self.score += pts
        self.items.append((pts, text))


def complete_daily(daily, today_iso):
    """Add the last completed session to the daily bars where the delayed
    feed has not published it, from NSE's own daily files. The session is
    looked for by date: during a session the feed already carries today's
    bar and can still lack yesterday's (#196), so the missing bar goes in its
    place, before any later one. Returns the number of series completed and
    the date they now run through."""
    try:
        last = nse_feed.last_session(datetime.fromisoformat(today_iso).date())
    except Exception:
        logger.exception("Could not read the last session from NSE's files")
        return 0, None
    added = 0
    for ticker, bars in daily.items():
        if not bars:
            continue
        at = len(bars)
        while at > 0 and _date(bars[at - 1]) > last["date"]:
            at -= 1
        if at == 0 or _date(bars[at - 1]) == last["date"]:
            continue   # nothing before the session to join it to, or it is there
        bar = last["indices"].get(ticker)
        if bar is None and ticker.endswith(".NS"):
            bar = last["stocks"].get(ticker[:-3])
        if bar:
            bars.insert(at, dict(bar))
            added += 1
    return added, last["date"]


def complete_sector_history(daily, session, industries):
    """Complete the real sector indices of `industries` that the delayed feed
    served short of history (#197) from NSE's own index closing files.
    Returns the tickers that now have enough. NSE is not asked when none of
    them is short."""
    tickers = {sectoral_indices.SECTOR_INDEX_TICKERS[i] for i in industries
               if i in sectoral_indices.SECTOR_INDEX_TICKERS}
    short = [t for t in sectoral_indices.short_of_history(daily, session) if t in tickers]
    if not short:
        return []
    try:
        history = nse_feed.index_history(datetime.fromisoformat(session).date())
    except Exception:
        logger.exception("Could not read the sector indices' history from NSE's files")
        return []
    return sectoral_indices.complete_from_nse(daily, session, history, tickers=short)


def load_guards(cfg):
    """The day's tradability guards from NSE. Either file may be missing, in
    which case its guard is unknown and excludes nothing."""
    if not cfg.get("guards", True):
        return {"ban": None, "bands": None, "off": True}
    return {"ban": nse_feed.fno_ban_list(), "bands": nse_feed.price_bands()}


def guard_check(symbol, guards, session, cfg, ltp=None, prev_close=None, limits=None):
    """(why the stock is left alone today, or None; whether it is long-only).
    A stock with a fixed price band can lock: a short caught at the upper
    band cannot be covered, so it is long-only, and it is left alone when the
    price is close to either band."""
    ban = guards.get("ban")
    if ban and ban["trade_date"] >= session and symbol in ban["symbols"]:
        return (f"In the F&O ban for {ban['trade_date']}: market-wide positions are above 95% of the limit", False)
    row = (guards.get("bands") or {}).get(symbol)
    if not row:
        return None, False
    if row["series"] and row["series"] != "EQ":
        return (f"In trade-for-trade (series {row['series']}): a position cannot be squared off the same day", True)
    if row["remarks"]:
        return f"Under surveillance: {row['remarks']}", row["band"] is not None
    band = row["band"]
    if band is None:
        return None, False
    if ltp and (prev_close or limits):
        near = cfg.get("near_band_pct", 2.0) / 100
        if limits and limits[0] > 0 and limits[1] > 0:
            lower, upper = limits                          # the exchange's own limits for the day
        else:
            upper, lower = prev_close * (1 + band / 100), prev_close * (1 - band / 100)
        if ltp >= upper * (1 - near):
            return f"Within {near * 100:.0f}% of its upper price band (₹{upper:,.2f}, {band:.0f}%)", True
        if ltp <= lower * (1 + near):
            return f"Within {near * 100:.0f}% of its lower price band (₹{lower:,.2f}, {band:.0f}%)", True
    return None, True


def guards_summary(guards, symbols):
    """What the page shows about the guards: what was read, and which of the
    universe's stocks they touch."""
    ban, bands = guards.get("ban"), guards.get("bands")
    uni = set(symbols)
    return {
        "off": bool(guards.get("off")),
        "ban": None if not ban else {"trade_date": ban["trade_date"], "count": len(ban["symbols"]),
                                     "in_universe": sorted(ban["symbols"] & uni)},
        "bands": None if not bands else {
            "banded": sorted(s for s in uni if s in bands and bands[s]["band"] is not None),
            "not_eq": sorted(s for s in uni if s in bands and bands[s]["series"] not in ("", "EQ")),
            "surveillance": sorted(s for s in uni if s in bands and bands[s]["remarks"]),
        },
    }


def tradability_exclusion(p, cfg):
    if p["close"] < cfg["min_price"]:
        return f"Price ₹{p['close']:.0f} below ₹{cfg['min_price']}"
    if p["turnover_cr"] < cfg["min_turnover_cr"]:
        return f"Turnover ₹{p['turnover_cr']:.0f} cr/day too thin (min ₹{cfg['min_turnover_cr']} cr)"
    if p["atr_pct"] < cfg["min_atr_pct"]:
        return f"Daily ATR {p['atr_pct']:.1f}% — too sluggish to cover costs (min {cfg['min_atr_pct']}%)"
    return None


def premarket_score(p, cfg, side="long", date_iso=None):
    """Daily-data-only ranking for one side (usable before the open and in backtests).
    Returns (score, [(points, reason)], excluded_reason_or_None). date_iso, when given,
    is the session being scored (YYYY-MM-DD) — feeds seasonality.march_effect() so the
    same real, cited calendar evidence applies identically live and in backtests."""
    excluded = tradability_exclusion(p, cfg)
    if excluded:
        return 0.0, [], excluded
    s = 1 if side == "long" else -1
    pts = _Points()

    if date_iso:
        eff = seasonality.march_effect(int(date_iso[5:7]), side)
        if eff:
            pts.add(*eff)

    if p["trend"] == ("up" if s > 0 else "down"):
        pts.add(20, "Daily uptrend (close > EMA20 > EMA50)" if s > 0 else "Daily downtrend (close < EMA20 < EMA50)")
    elif p["trend"] == ("down" if s > 0 else "up"):
        pts.add(-15, "Daily downtrend — longs fight the bigger picture" if s > 0
                else "Daily uptrend — shorts fight the bigger picture")

    rs = p["rs10"]
    if rs is not None:
        edge = rs * s
        if edge > 0.5:
            pts.add(min(20.0, edge * 4), f"{'Beat' if rs > 0 else 'Lagged'} NIFTY by {abs(rs):.1f}% over 10 days "
                                         f"(relative {'strength' if rs > 0 else 'weakness'})")
        elif edge < -0.5:
            pts.add(-min(15.0, -edge * 3), f"{'Beat' if rs > 0 else 'Lagged'} NIFTY by {abs(rs):.1f}% over 10 days")

    if s > 0 and p["pct_from_high"] <= 3:
        pts.add(10, f"{p['pct_from_high']:.1f}% from 52-week high — little overhead supply")
    if s < 0 and p["pct_from_low"] <= 3:
        pts.add(10, f"{p['pct_from_low']:.1f}% from 52-week low — no support underneath")
    if p["nr7"]:
        pts.add(8, "NR7: narrowest daily range in 7 sessions — compression before expansion")
    elif p["inside_day"]:
        pts.add(6, "Inside day — compression before expansion")

    swing_side = "long" if s > 0 else "short"
    for sw in p.get("swing_patterns", []):
        if sw["side"] != swing_side:
            continue
        stats = bulkowski.PATTERN_STATS.get(sw["name"])
        if stats:
            regime = stats["bull"]  # bull/bear-market split needs a longer regime read than we track; use bull stats
            pts.add(15, f"Confirmed {sw['name']} on the daily chart (Bulkowski: {regime['failure_rate_pct']}% "
                        f"historical failure rate, average move {regime['avg_move_pct']}%, US stocks)")

    rd = p.get("reversal_day")
    if rd:
        wants = "bottom" if s > 0 else "top"
        if rd["kind"] == wants:
            base = 10
            if rd["heavy_volume"]:
                base += 5
            if rd["outside_day"]:
                base += 3
            label = "bottom reversal day" if wants == "bottom" else "top reversal day"
            climax = " (selling climax — heavy volume)" if wants == "bottom" and rd["heavy_volume"] else \
                     " (heavy volume)" if rd["heavy_volume"] else ""
            pts.add(base, f"Murphy {label}{climax}" + (", outside day" if rd["outside_day"] else ""))

    r = p["rsi"]
    if r is not None:
        if s > 0:
            if r > 75:
                pts.add(-8, f"Daily RSI {r:.0f} overbought")
            elif 45 <= r <= 70:
                pts.add(5, f"Daily RSI {r:.0f} in a healthy momentum zone")
        else:
            if r < 25:
                pts.add(-8, f"Daily RSI {r:.0f} oversold — short-squeeze risk")
            elif 30 <= r <= 55:
                pts.add(5, f"Daily RSI {r:.0f} in a bearish momentum zone")
    if 1.5 <= p["atr_pct"] <= 4.0:
        pts.add(5, f"Daily ATR {p['atr_pct']:.1f}% — enough range to trade")
    return pts.score, pts.items, None


def intraday_metrics(candles, prof):
    session = candles[-1]["time"][:10]
    today = [c for c in candles if c["time"][:10] == session]
    prior = {}
    for c in candles:
        d = c["time"][:10]
        if d != session:
            prior.setdefault(d, []).append(c)
    n = len(today)
    # Relative volume at the same time of day, on finished bars only: this delayed feed's newest row may still be filling.
    today_done = [c for c in data_provider.closed_bars(candles, "5m", delayed=True) if c["time"][:10] == session]
    cum_today = sum(c["volume"] for c in today_done)
    prior_cums = [sum(c["volume"] for c in bars[:len(today_done)])
                  for bars in prior.values() if len(bars) >= len(today_done)]
    avg_prior = sum(prior_cums) / len(prior_cums) if prior_cums else 0
    ltp = today[-1]["close"]
    opening = today[:3]
    return {
        "ltp": ltp,
        "chg_pct": (ltp / prof["close"] - 1) * 100,
        "gap_pct": (today[0]["open"] / prof["close"] - 1) * 100,
        "rvol": cum_today / avg_prior if avg_prior > 0 else None,
        "vwap": ind.session_vwap(candles),
        "or_high": max(c["high"] for c in opening),
        "or_low": min(c["low"] for c in opening),
        "bars_today": n,
        "feed": "delayed",
    }


# --- live prices (README section 101) ----------------------------------------------------

def _minute_of_day(iso):
    t = datetime.fromisoformat(iso)
    return t.hour * 60 + t.minute + t.second / 60.0


def minutes_into_session(iso):
    """Minutes of the session that had passed at this time, from 0 to 375."""
    return max(0.0, min(float(SESSION_MINUTES), _minute_of_day(iso) - SESSION_OPEN_MINUTE))


def volume_curve(candles, session):
    """Average volume traded by the end of each 5-minute slot of the day,
    over the sessions before `session`: the yardstick for today's volume."""
    slots = SESSION_MINUTES // BAR_MINUTES
    days = {}
    for c in candles:
        d = c["time"][:10]
        if d >= session:
            continue
        k = int((_minute_of_day(c["time"]) - SESSION_OPEN_MINUTE) // BAR_MINUTES)
        if 0 <= k < slots:
            days.setdefault(d, [0] * slots)[k] += c["volume"]
    curves = []
    for per_slot in days.values():
        run, cum = 0, []
        for v in per_slot:
            run += v
            cum.append(run)
        if run > 0:
            curves.append(cum)
    if not curves:
        return []
    return [sum(c[k] for c in curves) / len(curves) for k in range(slots)]


def expected_volume(curve, minutes):
    """What the curve expects to have traded `minutes` into the session,
    in a straight line between the ends of two slots."""
    if not curve or minutes <= 0:
        return 0.0
    k, part = divmod(min(minutes, len(curve) * BAR_MINUTES), BAR_MINUTES)
    k = int(k)
    if k >= len(curve):
        return curve[-1]
    before = curve[k - 1] if k else 0.0
    return before + (curve[k] - before) * part / BAR_MINUTES


def live_day(quotes, symbols):
    """The session the quotes describe: the day on which at least half the
    universe last traded, with volume and an opening price. None before the
    open, or when the quotes are too thin to read."""
    days = {}
    for s in symbols:
        q = quotes.get(s)
        if q and q["last_trade"] and q["volume"] > 0 and q["open"] > 0 and q["prev_close"] > 0:
            days[q["last_trade"][:10]] = days.get(q["last_trade"][:10], 0) + 1
    if not days:
        return None
    day = max(days, key=days.get)
    return day if days[day] >= LIVE_DAY_MIN_SHARE * len(symbols) else None


def opening_range(candles, session):
    """(high, low) of the session's first 15 minutes, once those three bars exist."""
    first = [c for c in candles or [] if c["time"][:10] == session][:3]
    if len(first) < 3:
        return None, None
    return max(c["high"] for c in first), min(c["low"] for c in first)


def live_metrics(q, session, minutes, delayed_candles):
    """The same facts intraday_metrics reads from 5-minute bars, from one live
    quote. The gap is from NSE's opening price. The opening range needs bars,
    so it comes from whichever candles hold today's first three."""
    prev = q["prev_close"]
    expected = expected_volume(volume_curve(delayed_candles or [], session), minutes)
    or_high, or_low = opening_range(delayed_candles, session)
    return {
        "ltp": q["ltp"],
        "chg_pct": (q["ltp"] / prev - 1) * 100,
        "gap_pct": (q["open"] / prev - 1) * 100,
        "rvol": q["volume"] / expected if expected > 0 else None,
        "vwap": q["vwap"] or None,
        "or_high": or_high, "or_low": or_low,
        "bars_today": int(minutes // BAR_MINUTES),
        "feed": "live",
    }


def _why_delayed(cfg):
    if not cfg.get("live_feed", True):
        return "Live prices are switched off in the settings."
    if not data_provider.kite_data_active():
        return "Kite is not connected."
    return "Kite's quotes could not be read, or describe an earlier session than the delayed bars."


def fetch_live_quotes(cfg, symbols):
    if not cfg.get("live_feed", True):
        return {}
    try:
        return data_provider.kite_quotes(symbols, indices=(NIFTY_QUOTE,))
    except Exception:
        logger.exception("Live quotes failed; using the delayed feed")
        return {}


def intraday_score(m, prof, ctx, sector_rank, n_sectors, industry, catalyst, cfg, side="long", sector_trend=None):
    s = 1 if side == "long" else -1
    pts = _Points()

    g = m["gap_pct"]
    word = "up" if g > 0 else "down"
    if abs(g) >= 0.5:
        kind, close_pct = bulkowski.classify_gap(g, prof["trend"], prof["pct_from_high"], prof["pct_from_low"],
                                                  prof["atr_pct"])
        if kind == "breakaway" and g * s > 0:
            pts.add(10, f"{word.capitalize()} breakaway gap {abs(g):.1f}% (Bulkowski: only {close_pct}% of "
                        f"breakaway gaps close within a week — likely to persist)")
        elif kind == "exhaustion":
            pts.add(-8 if g * s > 0 else 6,
                    f"{word.capitalize()} gap {abs(g):.1f}% looks like exhaustion, not breakaway (Bulkowski: "
                    f"{close_pct}% of these close within a week — extended trend, high fade risk)")
        elif g * s > cfg["max_gap_pct"]:
            pts.add(-10, f"Gapped {word} {abs(g):.1f}% — chase and gap-fill risk")
        elif g * s >= 0.3:
            pts.add(6, f"{kind.capitalize()} gap {word} {abs(g):.1f}%")
        elif g * s <= -cfg["max_gap_pct"]:
            pts.add(-8, f"Gapped {word} {abs(g):.1f}% against the trade")

    rv = m["rvol"]
    if rv is not None:
        if rv >= 2:
            pts.add(15, f"Relative volume {rv:.1f}× — unusual participation")
        elif rv >= 1.3:
            pts.add(8, f"Relative volume {rv:.1f}×")
        elif rv < 0.7:
            pts.add(-8, f"Relative volume {rv:.1f}× — little interest today")

    rs_today = m["chg_pct"] - ctx["nifty"]["chg_pct"]
    verb = "Outperforming" if rs_today > 0 else "Underperforming"
    if rs_today * s > 0.3:
        pts.add(min(15.0, abs(rs_today) * 5), f"{verb} NIFTY today by {abs(rs_today):.1f}%")
    elif rs_today * s < -0.3:
        pts.add(-min(10.0, abs(rs_today) * 4), f"{verb} NIFTY today by {abs(rs_today):.1f}%")

    if m["vwap"]:
        above = m["ltp"] > m["vwap"]
        pts.add(5 if above == (s > 0) else -5, "Holding above VWAP" if above else "Below VWAP")
    if m["bars_today"] > 3 and m.get("or_high") is not None:
        if m["ltp"] > m["or_high"]:
            pts.add(8 if s > 0 else -6, "Trading above its 15-min opening range")
        elif m["ltp"] < m["or_low"]:
            pts.add(8 if s < 0 else -6, "Broke below its 15-min opening range")

    if sector_rank is not None and n_sectors >= 6:
        if sector_rank < 3:
            pts.add(8 if s > 0 else -5, f"{industry} is a top-3 sector today")
        elif sector_rank >= n_sectors - 3:
            pts.add(8 if s < 0 else -5, f"{industry} is a bottom-3 sector today")

    # Same-day sector_rank above reads this universe's own subset; this reads
    # the real published NSE sectoral index's own slower daily trend — a
    # structural confluence check, not a duplicate of the live one above.
    if sector_trend and sector_trend["trend"] in ("up", "down"):
        agrees = (sector_trend["trend"] == "up") == (s > 0)
        pts.add(6 if agrees else -6,
                f"{industry}'s real index ({sector_trend['ticker']}) is in a daily {sector_trend['trend']}trend"
                + (" — agrees with this trade" if agrees else " — this trade fights its own sector's real trend"))

    if catalyst:
        c = catalyst["score"]
        tone = "Positive" if c > 0 else "Negative"
        if c * s >= 0.2:
            pts.add(min(12.0, abs(c) * 15), f"{tone} catalyst: {catalyst['top'][:80]}")
        elif c * s <= -0.3:
            pts.add(-15, f"{tone} catalyst against the trade: {catalyst['top'][:80]}")
    return pts.score, pts.items, rs_today


def market_context(daily, nifty_5m, rows, session, filter_cfg, fii_dii=None, real_breadth=None, nifty_live=None):
    """nifty_live, when given, is the index's live quote: its last price and
    opening value replace the delayed bars'."""
    nd = [b for b in daily.get(NIFTY, []) if _date(b) < session]
    closes = [b["close"] for b in nd]
    today = [c for c in nifty_5m or [] if c["time"][:10] == session]
    if nifty_live:
        today = [{"open": nifty_live["open"], "close": nifty_live["ltp"]}]
    score, reasons = 0.0, []

    trend = "sideways"
    if len(closes) >= 50:
        e20, e50 = ind.ema(closes, 20), ind.ema(closes, 50)
        trend = "up" if closes[-1] > e20 > e50 else "down" if closes[-1] < e20 < e50 else "sideways"
    if trend == "up":
        score += 1
        reasons.append("NIFTY in a daily uptrend")
    elif trend == "down":
        score -= 1
        reasons.append("NIFTY in a daily downtrend")

    ltp = today[-1]["close"]
    prev_close = closes[-1] if closes else today[0]["open"]
    if nifty_live and nifty_live.get("prev_close"):
        prev_close = nifty_live["prev_close"]
    chg = (ltp / prev_close - 1) * 100
    if chg >= 0.3:
        score += 1
        reasons.append(f"NIFTY {chg:+.2f}% on the day")
    elif chg <= -0.3:
        score -= 1
        reasons.append(f"NIFTY {chg:+.2f}% on the day")
    above_open = ltp >= today[0]["open"]
    score += 0.5 if above_open else -0.5

    moved = [r["chg_pct"] for r in rows]
    adv = sum(1 for x in moved if x > 0)
    dec = sum(1 for x in moved if x < 0)
    pct_adv = adv / len(moved) * 100 if moved else 50.0
    if pct_adv >= 60:
        score += 1
        reasons.append(f"Broad participation: {adv} advancing / {dec} declining")
    elif pct_adv <= 40:
        score -= 1
        reasons.append(f"Weak breadth: {adv} advancing / {dec} declining")

    vix_bars = daily.get(VIX, [])
    vix = vix_bars[-1]["close"] if vix_bars else None
    vix_high = vix is not None and vix >= filter_cfg["vix_high"]
    if vix_high:
        score -= 1
        reasons.append(f"India VIX {vix:.1f} elevated — expect whipsaws")

    if fii_dii and fii_dii.get("fii_net_cr") is not None:
        fii_net = fii_dii["fii_net_cr"]
        # Real, documented relationship (SJCC Management Research Review study
        # on FII flows vs NIFTY returns, strongest when the market is falling)
        # — but the exact meaningful threshold isn't crisply established in
        # that literature, so ₹1,000 cr is a round, honestly-unvalidated cut,
        # not a precisely backtested one. Small weight accordingly.
        if fii_net <= -1000:
            score -= 1
            reasons.append(f"FII net sold ₹{abs(fii_net):,.0f} cr on {fii_dii['date']} — real flow-based headwind")
        elif fii_net >= 1000:
            score += 1
            reasons.append(f"FII net bought ₹{fii_net:,.0f} cr on {fii_dii['date']} — real flow-based tailwind")

    budget_note = seasonality.budget_day_note(session)
    if budget_note:
        reasons.append(budget_note)  # informational only — never scored, see seasonality.py

    if real_breadth and real_breadth.get("trin") is not None:
        # TRIN (Arms Index, Murphy ch 10): volume-weighted breadth across the
        # WHOLE exchange (~3,700 stocks), not just this scanner's NIFTY 100
        # universe. Classical reference bands (>1.2 oversold/bearish tape,
        # <0.8 overbought/bullish tape) are Murphy's own rules of thumb, not
        # backtested on this system yet — informational only, never scored,
        # same discipline as budget_note above, pending a real
        # database.factor_ic() check once enough days of history exist.
        trin = real_breadth["trin"]
        if trin >= 1.2:
            reasons.append(f"TRIN {trin:.2f} — volume favors declining stocks (informational, not scored)")
        elif trin <= 0.8:
            reasons.append(f"TRIN {trin:.2f} — volume favors advancing stocks (informational, not scored)")

    bias = "risk-on" if score >= 2 else "risk-off" if score <= -2 else "neutral"
    if not reasons:
        reasons.append("No strong market-wide signal")
    return {
        "bias": bias, "score": score, "reasons": reasons, "session_date": session,
        "nifty": {"ltp": _r(ltp), "chg_pct": _r(chg), "trend": trend, "above_open": above_open},
        "vix": _r(vix), "vix_high": vix_high,
        "breadth": {"adv": adv, "dec": dec, "pct_adv": _r(pct_adv, 0)},
        "fii_dii": fii_dii,
        "real_market_breadth": real_breadth,
    }


def premarket_context(daily, session, filter_cfg, fii_dii=None):
    """market_context()'s market-wide read, shifted one session earlier so it
    only uses data that exists before today's candle does: yesterday's NIFTY
    close (not a live intraday price) and yesterday's advance/decline count.
    Same scoring as market_context() so a pre-market read and the live
    intraday read are directly comparable, not two different systems."""
    nd = [b for b in daily.get(NIFTY, []) if _date(b) < session]
    closes = [b["close"] for b in nd]
    score, reasons = 0.0, []

    trend = "sideways"
    if len(closes) >= 51:
        e20, e50 = ind.ema(closes, 20), ind.ema(closes, 50)
        trend = "up" if closes[-1] > e20 > e50 else "down" if closes[-1] < e20 < e50 else "sideways"
    if trend == "up":
        score += 1
        reasons.append("NIFTY closed yesterday in a daily uptrend")
    elif trend == "down":
        score -= 1
        reasons.append("NIFTY closed yesterday in a daily downtrend")

    chg = (closes[-1] / closes[-2] - 1) * 100 if len(closes) >= 2 else None
    if chg is not None:
        if chg >= 0.3:
            score += 1
            reasons.append(f"NIFTY {chg:+.2f}% in yesterday's session")
        elif chg <= -0.3:
            score -= 1
            reasons.append(f"NIFTY {chg:+.2f}% in yesterday's session")

    if fii_dii and fii_dii.get("fii_net_cr") is not None:
        fii_net = fii_dii["fii_net_cr"]
        if fii_net <= -1000:
            score -= 1
            reasons.append(f"FII net sold ₹{abs(fii_net):,.0f} cr on {fii_dii['date']} — real flow-based headwind")
        elif fii_net >= 1000:
            score += 1
            reasons.append(f"FII net bought ₹{fii_net:,.0f} cr on {fii_dii['date']} — real flow-based tailwind")

    budget_note = seasonality.budget_day_note(session)
    if budget_note:
        reasons.append(budget_note)  # informational only — never scored, see seasonality.py

    return closes, score, reasons, trend, chg


def _trend_agrees(daily_trend, side):
    return daily_trend != ("down" if side == "LONG" else "up")


def select_active(eligible, bias, cfg):
    """Best final scores first; the side against the market bias gets at most
    counter_trend_active_count slots (longs on risk-off days, shorts on risk-on days)."""
    against = "LONG" if bias == "risk-off" else "SHORT" if bias == "risk-on" else None
    active, n_against = [], 0
    for r in eligible:
        if len(active) >= cfg["active_count"]:
            break
        if not _trend_agrees(r["daily_trend"], r["side"]) or r["final_score"] < cfg["min_score"]:
            continue
        if r["side"] == against:
            if n_against >= cfg["counter_trend_active_count"]:
                continue
            n_against += 1
        active.append(r["symbol"])
    return active


LIQUIDITY_RULE = ("The {n} most-traded eligible NIFTY 100 stocks by 20-day average turnover, "
                  "chosen once for the session and kept all day.")
SCORE_RULE = "The best {n} by scan score, re-chosen every scan."


def selection_mode(cfg):
    return "score" if cfg.get("selection") == "score" else "liquidity"


def select_liquid(eligible, cfg):
    """The active_count eligible stocks with the highest 20-day average
    turnover, most-traded first (ties by symbol, so the list is reproducible).
    No score, side or trend enters: the list is chosen for cost and coverage,
    not as a prediction."""
    ranked = sorted(eligible, key=lambda r: (-(r.get("turnover_cr") or 0.0), r["symbol"]))
    return [r["symbol"] for r in ranked[: cfg["active_count"]]]


class Scanner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_run = 0.0
        self.result = None
        self.intraday = {}
        # The session's fixed list in "liquidity" mode: {"session", "symbols", "fixed_ts", "when"}.
        # It is written to the journal when it is fixed and read back here, so a
        # restart keeps the list the session started with, and the time it was
        # fixed (#198). A list for an earlier session is read back too, as a
        # running scanner would still hold it; day_list_for() chooses again
        # when a scan reads a later session.
        self.sector_trends_unavailable = None
        self.day_list = self._stored_list()

    def _stored_list(self):
        if selection_mode(self.cfg) != "liquidity":
            return None
        try:
            return database.latest_day_list(mode="liquidity")
        except Exception:
            logger.exception("Could not read the day's list back from the journal")
            return None

    def _keep(self, session, symbols, when, now):
        """Fix the list for a session, in memory and in the journal. If the
        journal already holds a list for the session, that one stands."""
        dl = {"session": session, "symbols": list(symbols), "fixed_ts": now or time.time(), "when": when,
              "mode": "liquidity"}
        try:
            dl = database.record_day_list(session, dl["symbols"], dl["fixed_ts"], when) or dl
        except Exception:
            logger.exception("Could not write the day's list to the journal; it is kept in memory only")
        self.day_list = dl
        return dl

    def fix_day_list(self, session, symbols, now=None):
        """Fix the day's list before the open, from the pre-market read. It
        is not moved once fixed."""
        if self.list_fixed_for(session):
            return False
        self._keep(session, symbols, "before the open", now)
        return True

    def list_fixed_for(self, session):
        return bool(self.day_list and self.day_list["session"] == session)

    def day_list_for(self, session, eligible, n_rows, n_universe, now=None):
        """Today's list in "liquidity" mode. Chosen once per session and then
        kept; a stock that stops being eligible later in the day (a results
        announcement, a missing download) is dropped, not replaced, so the list
        only ever shrinks during the session. It is normally fixed before the
        open (fix_day_list). If it was not, the first scan with data for
        enough of the universe fixes it; until then it is recomputed."""
        eligible_syms = {r["symbol"] for r in eligible}
        dl = self.day_list
        if dl and dl["session"] >= session:
            # >: today's list is fixed and this scan still reads the last session's bars
            return [s for s in dl["symbols"] if s in eligible_syms], True
        chosen = select_liquid(eligible, self.cfg)
        if n_universe and n_rows >= self.cfg.get("freeze_min_coverage", 0.9) * n_universe:
            kept = self._keep(session, chosen, "at the first scan of the session", now)["symbols"]
            return [s for s in kept if s in eligible_syms], True
        return chosen, False

    def due(self, market_open):
        minutes = self.cfg["interval_minutes_open"] if market_open else self.cfg["interval_minutes_closed"]
        return time.time() - self.last_run >= minutes * 60

    def run(self):
        started = time.time()
        self.last_run = started
        cfg = self.cfg
        sides = ("long", "short") if cfg.get("allow_shorts", True) else ("long",)
        uni = universe.load()
        if not uni:
            raise RuntimeError("Universe list is empty")
        tickers = [yf_ticker(u["symbol"]) for u in uni]
        symbols = [u["symbol"] for u in uni]
        daily = download_batch(tickers + [NIFTY, VIX] + sectoral_indices.TICKERS, "1y", "1d")
        intraday = download_batch(tickers + [NIFTY], "5d", "5m")
        nifty_5m = intraday.get(NIFTY)
        if NIFTY not in daily:
            raise RuntimeError("NIFTY data unavailable")
        # Live prices when Kite is connected and its quotes describe a session
        # at least as recent as the delayed bars do; the delayed feed otherwise.
        quotes = fetch_live_quotes(cfg, symbols)
        nifty_q = quotes.get(NIFTY_QUOTE)
        live = live_day(quotes, symbols) if nifty_q and nifty_q["ltp"] > 0 and nifty_q["open"] > 0 else None
        delayed_session = nifty_5m[-1]["time"][:10] if nifty_5m else None
        if live and (not delayed_session or live >= delayed_session):
            session, feed = live, "live"
            at = nifty_q["at"] if nifty_q.get("at") and nifty_q["at"][:10] == session else None
            minutes = minutes_into_session(at) if at else float(SESSION_MINUTES)
        elif delayed_session:
            session, feed, quotes, nifty_q, minutes = delayed_session, "delayed", {}, None, None
        else:
            raise RuntimeError("NIFTY data unavailable")
        completed, _ = complete_daily(daily, session)
        nifty_dates = [_date(b) for b in daily[NIFTY]]
        nifty_closes = [b["close"] for b in daily[NIFTY]]

        events = nse_feed.results_calendar()
        ex_actions = nse_feed.corporate_actions_on(session)
        catalysts = news_sentiment.market_catalysts(uni) if cfg.get("use_news", True) else {}
        fii_dii = nse_feed.fii_dii_flows() if cfg.get("use_news", True) else None
        large_deals = nse_feed.large_deals_today() if cfg.get("use_news", True) else {}
        real_breadth = nse_feed.market_breadth() if cfg.get("use_news", True) else None
        guards = load_guards(cfg)
        if real_breadth:
            try:
                database.record_market_breadth(session, real_breadth)
            except Exception:
                logger.exception("Failed to persist today's market breadth")

        rows = []
        for u in uni:
            t = yf_ticker(u["symbol"])
            candles = intraday.get(t) or []
            prof = daily_profile(daily.get(t, []), nifty_dates, nifty_closes, session)
            if not prof:
                continue
            q = quotes.get(u["symbol"])
            traded = (q and q["last_trade"] and q["last_trade"][:10] == session and q["volume"] > 0
                      and q["open"] > 0 and q["prev_close"] > 0 and q["ltp"] > 0)
            if traded:
                m = live_metrics(q, session, minutes, candles)
            elif candles and candles[-1]["time"][:10] == session:
                m, q = intraday_metrics(candles, prof), None
            else:
                continue
            rows.append({**u, "_prof": prof, "_m": m, "_candles": candles, "_q": q, "_live_candles": False})
        for r in rows:
            r["chg_pct"] = r["_m"]["chg_pct"]

        ctx = market_context(daily, nifty_5m, rows, session, config.MARKET_FILTER, fii_dii=fii_dii,
                             real_breadth=real_breadth,
                             nifty_live={"open": nifty_q["open"], "ltp": nifty_q["ltp"],
                                         "prev_close": nifty_q["prev_close"]} if feed == "live" else None)

        by_sector = {}
        for r in rows:
            by_sector.setdefault(r["industry"], []).append(r["chg_pct"])
        sectors = sorted(
            ({"industry": k, "chg_pct": _r(sum(v) / len(v)), "count": len(v)} for k, v in by_sector.items()),
            key=lambda s: -s["chg_pct"],
        )
        sector_rank = {s["industry"]: i for i, s in enumerate(sectors)}
        sector_from_nse = complete_sector_history(daily, session, by_sector)
        sector_trends = {
            industry: sectoral_indices.sector_trend(daily, industry, nifty_dates, nifty_closes, session)
            for industry in by_sector
        }
        trends_unavailable = sectoral_indices.unavailable(sector_trends)
        if trends_unavailable and trends_unavailable != self.sector_trends_unavailable:
            logger.warning(f"Sector trend unavailable for {', '.join(trends_unavailable)}: "
                           f"too little daily history for their index, so that check is skipped")
        self.sector_trends_unavailable = trends_unavailable

        def score(r):
            """Both sides scored from the row's profile and today's metrics; the stronger is kept."""
            prof, m, sym = r["_prof"], r["_m"], r["symbol"]
            scored, rs_today = {}, None
            for side in (("long",) if r["long_only"] else sides):
                pre, pre_items, _ = premarket_score(prof, cfg, side, date_iso=session)
                intra, intra_items, rs_today = intraday_score(
                    m, prof, ctx, sector_rank.get(r["industry"]), len(sectors), r["industry"], catalysts.get(sym),
                    cfg, side, sector_trend=sector_trends.get(r["industry"]))
                scored[side] = (pre + intra, sorted(pre_items + intra_items, key=lambda x: -abs(x[0])))
            best = max(scored, key=lambda k: scored[k][0])
            total, items = scored[best]
            r.update({
                "side": best.upper(),
                "long_score": _r(scored["long"][0], 1),
                "short_score": _r(scored["short"][0], 1) if "short" in scored else None,
                "score": _r(total, 1), "final_score": _r(total, 1),
                "reasons": [{"points": _r(float(p), 1), "text": t} for p, t in items[:7]],
                "rs_today": _r(rs_today),
            })

        for r in rows:
            prof, m, sym, q = r["_prof"], r["_m"], r["symbol"], r["_q"]
            excluded = tradability_exclusion(prof, cfg)
            if not excluded and sym in events:
                ev = events[sym]
                excluded = f"{ev['purpose']} on {ev['date']} — event risk, no new trades"
            if not excluded and sym in ex_actions:
                excluded = f"Ex-date today ({ex_actions[sym]}), so the price gap is mechanical, not a signal"
            guarded, long_only = guard_check(sym, guards, session, cfg, ltp=m["ltp"], prev_close=prof["close"],
                                             limits=(q["lower_limit"], q["upper_limit"]) if q else None)
            excluded = excluded or guarded
            r.update({
                "long_only": long_only, "excluded": excluded, "feed": m["feed"],
                "ltp": _r(m["ltp"]), "gap_pct": _r(m["gap_pct"]), "rvol": _r(m["rvol"]),
                "vwap": _r(m["vwap"]), "atr_pct": _r(prof["atr_pct"]),
                "daily_trend": prof["trend"], "rs10": _r(prof["rs10"]),
                "pct_from_high": _r(prof["pct_from_high"]), "pct_from_low": _r(prof["pct_from_low"]),
                "turnover_cr": _r(prof["turnover_cr"], 0), "chg_pct": _r(m["chg_pct"]), "beta": _r(prof["beta"]),
                "catalyst": catalysts.get(sym), "event": events.get(sym), "brain": None,
                "swing_patterns": prof.get("swing_patterns", []),
                "large_deals": large_deals.get(sym),
            })
            score(r)

        eligible = sorted((r for r in rows if not r["excluded"]), key=lambda r: -r["score"])
        mode = selection_mode(cfg)
        fixed = False
        if mode == "liquidity":
            active, fixed = self.day_list_for(session, eligible, len(rows), len(uni))
            chosen = set(active)
            deep = [r for r in eligible if r["symbol"] in chosen]
        else:
            deep = eligible[: cfg["deep_analysis"]]
        brain_params = config.STRATEGY_PARAMS.get("sahab_dimaag", {})
        # The stocks that get the checklist read get live bars for it. The
        # opening range, which needs bars, is then known at 09:30 and not a
        # quarter of an hour later, so their score is worked out again.
        live_candles = {}
        if feed == "live" and deep:
            try:
                live_candles = data_provider.get_candles_batch([r["symbol"] for r in deep], "5m", "5d")
            except Exception:
                logger.exception("Live candles for the day's list failed; using the delayed bars")
        for r in deep:
            mine = live_candles.get(r["symbol"])
            if mine and not mine[-1].get("delayed"):
                r["_candles"], r["_live_candles"] = mine, True
                if r["_m"]["feed"] == "live" and r["_m"]["or_high"] is None:
                    r["_m"]["or_high"], r["_m"]["or_low"] = opening_range(mine, session)
                    if r["_m"]["or_high"] is not None:
                        score(r)
            news = None
            if cfg.get("use_news", True):
                try:
                    news = news_sentiment.get_sentiment(r["symbol"], r["name"])
                except Exception as exc:
                    logger.warning(f"News failed for {r['symbol']}: {exc}")
            fund = None
            if cfg.get("use_fundamentals", True):
                try:
                    fund = fundamentals.get_fundamentals(r["symbol"])
                except Exception as exc:
                    logger.warning(f"Fundamentals failed for {r['symbol']}: {exc}")
            finished = data_provider.closed_bars(r["_candles"], "5m", delayed=not r["_live_candles"])
            _, brain = trader_brain_signal(finished, prev_state=None, news=news, fundamentals=fund, **brain_params)
            if brain and "bull_score" in brain:
                r["brain"] = brain
                edge = brain["bull_score"] - brain["bear_score"]
                if r["side"] == "SHORT":
                    edge = -edge
                r["final_score"] = _r(r["score"] + max(-15.0, min(15.0, edge * 2)), 1)

        eligible.sort(key=lambda r: -r["final_score"])
        if mode == "score":
            active = select_active(eligible, ctx["bias"], cfg)

        excluded_rows = sorted((r for r in rows if r["excluded"]), key=lambda r: -r["score"])
        ranked = eligible + excluded_rows
        self.intraday = {r["symbol"]: r["_candles"][-200:] for r in rows if r["_candles"]}
        n_live = sum(1 for r in rows if r["feed"] == "live")
        for i, r in enumerate(ranked, 1):
            r["rank"] = i
            r["status"] = "AVOID" if r["excluded"] else "ACTIVE" if r["symbol"] in active else "WATCH"
            for k in ("_prof", "_m", "_candles", "_q", "_live_candles"):
                r.pop(k, None)

        active_sides = {r["symbol"]: r["side"] for r in ranked if r["symbol"] in active}
        self.result = {
            "ts": time.time(),
            "session_date": session,
            "duration_s": _r(time.time() - started, 1),
            "scanned": len(rows),
            "excluded_count": len(excluded_rows),
            "active": active,
            "active_sides": active_sides,
            "selection": {
                "mode": mode,
                "rule": (LIQUIDITY_RULE if mode == "liquidity" else SCORE_RULE).format(n=cfg["active_count"]),
                "fixed": fixed,
                "fixed_at": (self.day_list or {}).get("fixed_ts") if mode == "liquidity" and fixed else None,
                "fixed_when": (self.day_list or {}).get("when") if mode == "liquidity" and fixed else None,
            },
            "guards": guards_summary(guards, [u["symbol"] for u in uni]),
            "feed": {"prices": feed, "rows_live": n_live, "rows_delayed": len(rows) - n_live,
                     "quotes_at": nifty_q["at"] if nifty_q else None,
                     "why_delayed": None if feed == "live" else _why_delayed(cfg)},
            "daily_completed_from_nse": completed,
            "sector_history_from_nse": sector_from_nse,
            "sector_trends_unavailable": trends_unavailable,
            "market": ctx,
            "sectors": sectors,
            "rows": ranked,
        }
        return self.result


def premarket_picks(daily, universe_rows, session_dates, top_n, cfg, allow_shorts=True):
    """Backtest helper: for each session, {symbol: "LONG"|"SHORT"} for the top_n stocks by
    daily-data-only score, using only information available before that session's open."""
    nd = daily.get(NIFTY, [])
    nifty_dates = [_date(b) for b in nd]
    nifty_closes = [b["close"] for b in nd]
    sides = ("LONG", "SHORT") if allow_shorts else ("LONG",)
    picks = {}
    for d in session_dates:
        scored = []
        for u in universe_rows:
            prof = daily_profile(daily.get(yf_ticker(u["symbol"]), []), nifty_dates, nifty_closes, d)
            if not prof or tradability_exclusion(prof, cfg):
                continue
            best = None
            for side in sides:
                if not _trend_agrees(prof["trend"], side):
                    continue
                score, _, _ = premarket_score(prof, cfg, side.lower(), date_iso=d)
                if best is None or score > best[0]:
                    best = (score, side)
            if best:
                scored.append((best[0], u["symbol"], best[1]))
        picks[d] = {sym: side for _, sym, side in sorted(scored, reverse=True)[:top_n]}
    return picks


def _premarket_narrative(bias, mkt_reasons, vix, vix_high, top_picks, events, ex_actions):
    """Stitches the same facts already in the response into a few sentences of
    trader-style prose — how an experienced trader actually talks through a
    morning read, not a bullet dump of scores. Every clause here maps to a
    real, already-computed field (nothing new is inferred or predicted); this
    is presentation, not a second source of truth. Returns a list of short
    paragraphs, not one wall of text, since that's how a real pre-market note
    reads — market read, then the shortlist, then the catch, then the plan."""
    paras = []

    mood = {"risk-on": "constructive", "risk-off": "defensive", "neutral": "mixed, no strong lean"}[bias]
    lead = f"Yesterday's tape reads {mood}: " + "; ".join(mkt_reasons[:2]) + "."
    if vix is not None:
        lead += f" VIX at {vix:.1f} is {'hot enough to trim size on' if vix_high else 'quiet, so no reason to size down for volatility'}."
    paras.append(lead)

    longs = [r for r in top_picks if r["side"] == "LONG"]
    shorts = [r for r in top_picks if r["side"] == "SHORT"]

    def _name_with_reason(r):
        top_reason = r["reasons"][0]["text"] if r["reasons"] else "screens strongest on setup"
        return f"{r['symbol']} ({top_reason})"

    if bias == "risk-off" and longs and not shorts:
        pick_line = "Even on a weak tape the cleanest names are still longs — worth noting, since that's relative strength, not just a lagging short."
    elif bias == "risk-on" and shorts and not longs:
        pick_line = "Even on a strong tape a couple of names still screen as shorts — real relative weakness, not just noise."
    else:
        pick_line = None

    watch_bits = []
    if longs:
        watch_bits.append("On the long side, watching " + ", ".join(_name_with_reason(r) for r in longs[:3]) + ".")
    if shorts:
        watch_bits.append("On the short side, watching " + ", ".join(_name_with_reason(r) for r in shorts[:3]) + ".")
    if watch_bits:
        if pick_line:
            watch_bits.append(pick_line)
        paras.append(" ".join(watch_bits))
    else:
        paras.append("Nothing cleanly qualifies yet — no forced trade today if the shortlist stays this thin.")

    caveats = []
    if events:
        caveats.append(f"{len(events)} name(s) report results today — off the table regardless of how the setup looks.")
    if ex_actions:
        caveats.append(f"{len(ex_actions)} name(s) go ex-date today — any gap there is mechanical, not a signal.")
    if caveats:
        paras.append(" ".join(caveats))

    paras.append(
        "This is prep, not a trigger: it's last night's close, no live tape yet. The plan is to watch these names "
        "from the open and let the opening range, volume, and Sahab's Dimaag checklist confirm (or kill) the idea "
        "before anything is sized — exactly what a discretionary trader's watchlist is for, and exactly what it isn't."
    )
    return paras


def run_premarket(cfg):
    """Live pre-market ranking for the dashboard: the same premarket_score()
    component the intraday scanner blends with live-tape evidence, but run on
    its own using only yesterday's daily close — no 5-min candles needed, so
    this works before 09:15 IST (or any time the intraday feed is empty).
    Deliberately does NOT invent a gap/open/SGX-Nifty style pre-open number;
    everything here is a daily-chart fact as of last night's close, same
    honesty rule as the rest of the codebase."""
    started = time.time()
    uni = universe.load()
    if not uni:
        raise RuntimeError("Universe list is empty")
    today = datetime.now(IST).date().isoformat()
    tickers = [yf_ticker(u["symbol"]) for u in uni]
    daily = download_batch(tickers + [NIFTY, VIX], "1y", "1d")
    completed, expected = complete_daily(daily, today)
    nifty_bars = [b for b in daily.get(NIFTY, []) if _date(b) < today]
    if len(nifty_bars) < 60:
        raise RuntimeError("NIFTY data unavailable")
    nifty_dates = [_date(b) for b in nifty_bars]
    nifty_closes = [b["close"] for b in nifty_bars]
    session = nifty_dates[-1]  # last completed session (usually yesterday)

    fii_dii = nse_feed.fii_dii_flows() if cfg.get("use_news", True) else None
    nifty_closes_all, mkt_score, mkt_reasons, nifty_trend, nifty_chg = premarket_context(
        daily, today, config.MARKET_FILTER, fii_dii=fii_dii)
    vix_bars = [b for b in daily.get(VIX, []) if _date(b) < today]
    vix = vix_bars[-1]["close"] if vix_bars else None
    vix_high = vix is not None and vix >= config.MARKET_FILTER["vix_high"]
    if vix_high:
        mkt_score -= 1
        mkt_reasons.append(f"India VIX {vix:.1f} elevated — expect whipsaws")

    events = nse_feed.results_calendar()
    ex_actions = nse_feed.corporate_actions_on(today)
    catalysts = news_sentiment.market_catalysts(uni) if cfg.get("use_news", True) else {}
    large_deals = nse_feed.large_deals_today() if cfg.get("use_news", True) else {}
    guards = load_guards(cfg)

    sides = ("long", "short") if cfg.get("allow_shorts", True) else ("long",)
    rows, adv, dec = [], 0, 0
    for u in uni:
        t = yf_ticker(u["symbol"])
        bars = [b for b in daily.get(t, []) if _date(b) < today]
        if len(bars) < 2:
            continue
        prev_chg = (bars[-1]["close"] / bars[-2]["close"] - 1) * 100
        if prev_chg > 0:
            adv += 1
        elif prev_chg < 0:
            dec += 1
        prof = daily_profile(daily.get(t, []), nifty_dates, nifty_closes, today)
        if not prof:
            continue
        rows.append({**u, "_prof": prof, "prev_chg_pct": _r(prev_chg)})

    pct_adv = adv / len(rows) * 100 if rows else 50.0
    if pct_adv >= 60:
        mkt_score += 1
        mkt_reasons.append(f"Broad participation yesterday: {adv} advancing / {dec} declining")
    elif pct_adv <= 40:
        mkt_score -= 1
        mkt_reasons.append(f"Weak breadth yesterday: {adv} advancing / {dec} declining")
    bias = "risk-on" if mkt_score >= 2 else "risk-off" if mkt_score <= -2 else "neutral"
    if not mkt_reasons:
        mkt_reasons.append("No strong market-wide signal yet")

    for r in rows:
        prof, sym = r["_prof"], r["symbol"]
        excluded = tradability_exclusion(prof, cfg)
        if not excluded and sym in events:
            ev = events[sym]
            excluded = f"{ev['purpose']} on {ev['date']} — event risk, no new trades"
        if not excluded and sym in ex_actions:
            excluded = f"Ex-date today ({ex_actions[sym]}), so the price gap is mechanical, not a signal"
        guarded, long_only = guard_check(sym, guards, today, cfg)
        excluded = excluded or guarded
        scored = {}
        for side in (("long",) if long_only else sides):
            pre, pre_items, _ = premarket_score(prof, cfg, side, date_iso=today)
            scored[side] = (pre, pre_items)
        best = max(scored, key=lambda k: scored[k][0])
        score, items = scored[best]
        r.update({
            "side": best.upper(), "score": _r(score, 1),
            "long_score": _r(scored["long"][0], 1),
            "short_score": _r(scored["short"][0], 1) if "short" in scored else None,
            "long_only": long_only,
            "excluded": excluded,
            "reasons": [{"points": _r(float(p), 1), "text": t} for p, t in sorted(items, key=lambda x: -abs(x[0]))[:7]],
            "close": _r(prof["close"]), "atr_pct": _r(prof["atr_pct"]), "daily_trend": prof["trend"],
            "rs10": _r(prof["rs10"]) if prof["rs10"] is not None else None,
            "pct_from_high": _r(prof["pct_from_high"]), "pct_from_low": _r(prof["pct_from_low"]),
            "turnover_cr": _r(prof["turnover_cr"], 0), "beta": _r(prof["beta"]) if prof["beta"] is not None else None,
            "catalyst": catalysts.get(sym), "event": events.get(sym),
            "swing_patterns": prof.get("swing_patterns", []),
            "large_deals": large_deals.get(sym),
        })
        del r["_prof"]

    eligible = sorted((r for r in rows if not r["excluded"]), key=lambda r: -r["score"])
    excluded_rows = sorted((r for r in rows if r["excluded"]), key=lambda r: -r["score"])
    ranked = eligible + excluded_rows
    mode = selection_mode(cfg)
    if mode == "liquidity":
        picked = select_liquid(eligible, {**cfg, "active_count": cfg.get("active_count", 6)})
        by_sym = {r["symbol"]: r for r in eligible}
        top_picks = [by_sym[s] for s in picked]
    else:
        top_picks = eligible[: cfg.get("active_count", 6)]
    chosen = {r["symbol"] for r in top_picks}
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
        r["status"] = "AVOID" if r["excluded"] else "WATCHLIST" if r["symbol"] in chosen else "WATCH"

    narrative = _premarket_narrative(bias, mkt_reasons, vix, vix_high, top_picks, events, ex_actions)

    return {
        "ts": time.time(),
        "session_date": session,
        "daily": {"through": session, "last_session": expected, "completed_from_nse": completed,
                  "stale": bool(expected and session < expected)},
        "as_of_note": (f"Ranked on the {session} close — the last completed session. " if not (expected and session < expected)
                       else f"Ranked on the {session} close. The {expected} session is not in the daily data yet. ")
                      + "Refreshes once today's candles exist and the live intraday scanner takes over.",
        "duration_s": _r(time.time() - started, 1),
        "scanned": len(rows),
        "excluded_count": len(excluded_rows),
        "watchlist": [r["symbol"] for r in top_picks],
        "selection": {"mode": mode, "rule": (LIQUIDITY_RULE if mode == "liquidity" else SCORE_RULE).format(
            n=cfg.get("active_count", 6))},
        "guards": guards_summary(guards, [u["symbol"] for u in uni]),
        "narrative": narrative,
        "market": {
            "bias": bias, "score": mkt_score, "reasons": mkt_reasons, "session_date": session,
            "nifty": {"close": _r(nifty_closes_all[-1]) if nifty_closes_all else None, "chg_pct": _r(nifty_chg) if nifty_chg is not None else None, "trend": nifty_trend},
            "vix": _r(vix) if vix is not None else None, "vix_high": vix_high,
            "breadth": {"adv": adv, "dec": dec, "pct_adv": _r(pct_adv, 0)},
            "fii_dii": fii_dii,
        },
        "events_today": events,
        "ex_actions_today": ex_actions,
        "rows": ranked,
    }
