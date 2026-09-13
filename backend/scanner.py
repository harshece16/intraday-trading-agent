"""
Market scanner — decides WHAT to trade; Trader Brain then decides WHEN.

Professional intraday traders don't stare at a fixed list; before and during
the session they narrow a liquid universe down to the handful of stocks that
are actually "in play". This encodes that routine over the NIFTY 100:

  Market context   NIFTY trend and day change, breadth (advancers/decliners),
                   India VIX. Risk-off days get fewer, smaller trades.
  Tradability      price, turnover and daily ATR% floors — a stock that
                   doesn't move 1.2%+ a day can't pay for intraday costs.
  Daily setup      daily trend (EMA20/50), 10-day relative strength vs
                   NIFTY, distance from 52-week high, NR7 / inside-day
                   compression, daily RSI.
  In play today    gap %, time-of-day-adjusted relative volume, relative
                   strength vs NIFTY today, VWAP side, opening-range
                   breakout, sector leadership.
  Catalysts        NSE filings + market news mentioning the company.
  Event risk       results due today/next session → no new longs.

The top candidates get a full Trader Brain read (with per-stock news); the
best of those become the engine's active watchlist.
"""

import bisect
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

import config
import indicators as ind
import news_sentiment
import nse_feed
import universe
from trader_brain import trader_brain_signal

logger = logging.getLogger("trading_bot")
IST = ZoneInfo("Asia/Kolkata")
NIFTY = "^NSEI"
VIX = "^INDIAVIX"


def yf_ticker(symbol):
    return symbol if symbol.startswith("^") or symbol.endswith(".NS") else f"{symbol}.NS"


def _r(x, nd=2):
    return round(x, nd) if isinstance(x, float) else x


def _date(bar):
    return bar["time"][:10]


def download_batch(tickers, period, interval):
    """One yfinance request for many tickers -> {ticker: [candle, ...]} with IST timestamps."""
    import yfinance as yf
    df = yf.download(tickers, period=period, interval=interval, group_by="ticker",
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
    high52 = max(b["high"] for b in bars[-250:])
    ranges = [b["high"] - b["low"] for b in bars[-7:]]
    return {
        "close": close,
        "atr_pct": atr_v / close * 100 if atr_v else 0.0,
        "turnover_cr": sum(b["close"] * b["volume"] for b in bars[-20:]) / 20 / 1e7,
        "trend": trend,
        "rsi": ind.rsi(closes[-100:], 14),
        "rs10": rs10,
        "pct_from_high": (high52 - close) / high52 * 100,
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


def premarket_score(p, cfg):
    """Daily-data-only ranking (usable before the open and in backtests).
    Returns (score, [(points, reason)], excluded_reason_or_None)."""
    if p["close"] < cfg["min_price"]:
        return 0.0, [], f"Price ₹{p['close']:.0f} below ₹{cfg['min_price']}"
    if p["turnover_cr"] < cfg["min_turnover_cr"]:
        return 0.0, [], f"Turnover ₹{p['turnover_cr']:.0f} cr/day too thin (min ₹{cfg['min_turnover_cr']} cr)"
    if p["atr_pct"] < cfg["min_atr_pct"]:
        return 0.0, [], f"Daily ATR {p['atr_pct']:.1f}% — too sluggish to cover costs (min {cfg['min_atr_pct']}%)"

    pts = _Points()
    if p["trend"] == "up":
        pts.add(20, "Daily uptrend (close > EMA20 > EMA50)")
    elif p["trend"] == "down":
        pts.add(-15, "Daily downtrend — longs fight the bigger picture")
    rs = p["rs10"]
    if rs is not None:
        if rs > 0.5:
            pts.add(min(20.0, rs * 4), f"Beat NIFTY by {rs:.1f}% over 10 days (relative strength)")
        elif rs < -0.5:
            pts.add(-min(15.0, -rs * 3), f"Lagged NIFTY by {-rs:.1f}% over 10 days")
    if p["pct_from_high"] <= 3:
        pts.add(10, f"{p['pct_from_high']:.1f}% from 52-week high — little overhead supply")
    if p["nr7"]:
        pts.add(8, "NR7: narrowest daily range in 7 sessions — compression before expansion")
    elif p["inside_day"]:
        pts.add(6, "Inside day — compression before expansion")
    r = p["rsi"]
    if r is not None:
        if r > 75:
            pts.add(-8, f"Daily RSI {r:.0f} overbought")
        elif 45 <= r <= 70:
            pts.add(5, f"Daily RSI {r:.0f} in a healthy momentum zone")
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
    cum_today = sum(c["volume"] for c in today)
    # Relative volume at the same time of day: first n bars of each prior session.
    prior_cums = [sum(c["volume"] for c in bars[:n]) for bars in prior.values() if len(bars) >= n]
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
    }


def intraday_score(m, ctx, sector_rank, n_sectors, industry, catalyst, cfg):
    pts = _Points()
    g = m["gap_pct"]
    if g > cfg["max_gap_pct"]:
        pts.add(-10, f"Gapped up {g:.1f}% — chase and gap-fill risk")
    elif g >= 0.3:
        pts.add(6, f"Gap up {g:.1f}% — overnight demand")
    elif g <= -cfg["max_gap_pct"]:
        pts.add(-8, f"Gapped down {-g:.1f}%")
    rv = m["rvol"]
    if rv is not None:
        if rv >= 2:
            pts.add(15, f"Relative volume {rv:.1f}× — unusual participation")
        elif rv >= 1.3:
            pts.add(8, f"Relative volume {rv:.1f}×")
        elif rv < 0.7:
            pts.add(-8, f"Relative volume {rv:.1f}× — little interest today")
    rs_today = m["chg_pct"] - ctx["nifty"]["chg_pct"]
    if rs_today > 0.3:
        pts.add(min(15.0, rs_today * 5), f"Outperforming NIFTY today by {rs_today:.1f}%")
    elif rs_today < -0.3:
        pts.add(-min(10.0, -rs_today * 4), f"Underperforming NIFTY today by {-rs_today:.1f}%")
    if m["vwap"]:
        if m["ltp"] > m["vwap"]:
            pts.add(5, "Holding above VWAP")
        else:
            pts.add(-5, "Below VWAP")
    if m["bars_today"] > 3:
        if m["ltp"] > m["or_high"]:
            pts.add(8, "Trading above its 15-min opening range")
        elif m["ltp"] < m["or_low"]:
            pts.add(-6, "Below its 15-min opening range")
    if sector_rank is not None and n_sectors >= 6:
        if sector_rank < 3:
            pts.add(8, f"{industry} is a top-3 sector today")
        elif sector_rank >= n_sectors - 3:
            pts.add(-5, f"{industry} is a bottom-3 sector today")
    if catalyst:
        s = catalyst["score"]
        if s >= 0.2:
            pts.add(min(12.0, s * 15), f"Positive catalyst: {catalyst['top'][:80]}")
        elif s <= -0.3:
            pts.add(-15, f"Negative catalyst: {catalyst['top'][:80]}")
    return pts.score, pts.items, rs_today


def market_context(daily, nifty_5m, rows, session, filter_cfg):
    nd = [b for b in daily.get(NIFTY, []) if _date(b) < session]
    closes = [b["close"] for b in nd]
    today = [c for c in nifty_5m if c["time"][:10] == session]
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

    bias = "risk-on" if score >= 2 else "risk-off" if score <= -2 else "neutral"
    if not reasons:
        reasons.append("No strong market-wide signal")
    return {
        "bias": bias, "score": score, "reasons": reasons, "session_date": session,
        "nifty": {"ltp": _r(ltp), "chg_pct": _r(chg), "trend": trend, "above_open": above_open},
        "vix": _r(vix), "vix_high": vix_high,
        "breadth": {"adv": adv, "dec": dec, "pct_adv": _r(pct_adv, 0)},
    }


class Scanner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_run = 0.0
        self.result = None
        self.intraday = {}

    def due(self, market_open):
        minutes = self.cfg["interval_minutes_open"] if market_open else self.cfg["interval_minutes_closed"]
        return time.time() - self.last_run >= minutes * 60

    def run(self):
        started = time.time()
        self.last_run = started
        cfg = self.cfg
        uni = universe.load()
        if not uni:
            raise RuntimeError("Universe list is empty")
        tickers = [yf_ticker(u["symbol"]) for u in uni]
        daily = download_batch(tickers + [NIFTY, VIX], "1y", "1d")
        intraday = download_batch(tickers + [NIFTY], "5d", "5m")
        nifty_5m = intraday.get(NIFTY)
        if not nifty_5m or NIFTY not in daily:
            raise RuntimeError("NIFTY data unavailable")
        session = nifty_5m[-1]["time"][:10]
        nifty_dates = [_date(b) for b in daily[NIFTY]]
        nifty_closes = [b["close"] for b in daily[NIFTY]]

        events = nse_feed.results_calendar()
        catalysts = news_sentiment.market_catalysts(uni) if cfg.get("use_news", True) else {}

        rows = []
        for u in uni:
            t = yf_ticker(u["symbol"])
            candles = intraday.get(t)
            prof = daily_profile(daily.get(t, []), nifty_dates, nifty_closes, session)
            if not prof or not candles or candles[-1]["time"][:10] != session:
                continue
            rows.append({**u, "_prof": prof, "_m": intraday_metrics(candles, prof), "_candles": candles})
        for r in rows:
            r["chg_pct"] = r["_m"]["chg_pct"]

        ctx = market_context(daily, nifty_5m, rows, session, config.MARKET_FILTER)

        by_sector = {}
        for r in rows:
            by_sector.setdefault(r["industry"], []).append(r["chg_pct"])
        sectors = sorted(
            ({"industry": k, "chg_pct": _r(sum(v) / len(v)), "count": len(v)} for k, v in by_sector.items()),
            key=lambda s: -s["chg_pct"],
        )
        sector_rank = {s["industry"]: i for i, s in enumerate(sectors)}

        for r in rows:
            prof, m, sym = r["_prof"], r["_m"], r["symbol"]
            pre, pre_items, excluded = premarket_score(prof, cfg)
            if not excluded and sym in events:
                ev = events[sym]
                excluded = f"{ev['purpose']} on {ev['date']} — event risk, no new longs"
            intra, intra_items, rs_today = intraday_score(
                m, ctx, sector_rank.get(r["industry"]), len(sectors), r["industry"], catalysts.get(sym), cfg)
            items = sorted(pre_items + intra_items, key=lambda x: -abs(x[0]))
            r.update({
                "score": _r(pre + intra, 1), "final_score": _r(pre + intra, 1), "excluded": excluded,
                "reasons": [{"points": _r(float(p), 1), "text": t} for p, t in items[:7]],
                "ltp": _r(m["ltp"]), "gap_pct": _r(m["gap_pct"]), "rvol": _r(m["rvol"]),
                "rs_today": _r(rs_today), "vwap": _r(m["vwap"]), "atr_pct": _r(prof["atr_pct"]),
                "daily_trend": prof["trend"], "rs10": _r(prof["rs10"]), "pct_from_high": _r(prof["pct_from_high"]),
                "turnover_cr": _r(prof["turnover_cr"], 0), "chg_pct": _r(m["chg_pct"]),
                "catalyst": catalysts.get(sym), "event": events.get(sym), "brain": None,
            })

        eligible = sorted((r for r in rows if not r["excluded"]), key=lambda r: -r["score"])
        brain_params = config.STRATEGY_PARAMS.get("trader_brain", {})
        for r in eligible[: cfg["deep_analysis"]]:
            news = None
            if cfg.get("use_news", True):
                try:
                    news = news_sentiment.get_sentiment(r["symbol"], r["name"])
                except Exception as exc:
                    logger.warning(f"News failed for {r['symbol']}: {exc}")
            _, brain = trader_brain_signal(r["_candles"], prev_state=None, news=news, **brain_params)
            if brain and "bull_score" in brain:
                r["brain"] = brain
                edge = brain["bull_score"] - brain["bear_score"]
                r["final_score"] = _r(r["score"] + max(-15.0, min(15.0, edge * 2)), 1)

        eligible.sort(key=lambda r: -r["final_score"])
        active = [r["symbol"] for r in eligible
                  if r["daily_trend"] != "down" and r["final_score"] >= cfg["min_score"]][: cfg["active_count"]]
        if ctx["bias"] == "risk-off":
            active = active[: cfg["risk_off_active_count"]]

        excluded_rows = sorted((r for r in rows if r["excluded"]), key=lambda r: -r["score"])
        ranked = eligible + excluded_rows
        self.intraday = {r["symbol"]: r["_candles"][-200:] for r in rows}
        for i, r in enumerate(ranked, 1):
            r["rank"] = i
            r["status"] = "AVOID" if r["excluded"] else "ACTIVE" if r["symbol"] in active else "WATCH"
            for k in ("_prof", "_m", "_candles"):
                r.pop(k, None)

        self.result = {
            "ts": time.time(),
            "session_date": session,
            "duration_s": _r(time.time() - started, 1),
            "scanned": len(rows),
            "excluded_count": len(excluded_rows),
            "active": active,
            "market": ctx,
            "sectors": sectors,
            "rows": ranked,
        }
        return self.result


def premarket_picks(daily, universe_rows, session_dates, top_n, cfg):
    """Backtest helper: for each session, the top_n stocks by daily-data-only score,
    ranked with information available before that session's open."""
    nd = daily.get(NIFTY, [])
    nifty_dates = [_date(b) for b in nd]
    nifty_closes = [b["close"] for b in nd]
    picks = {}
    for d in session_dates:
        scored = []
        for u in universe_rows:
            prof = daily_profile(daily.get(yf_ticker(u["symbol"]), []), nifty_dates, nifty_closes, d)
            if not prof or prof["trend"] == "down":
                continue
            score, _, excluded = premarket_score(prof, cfg)
            if not excluded:
                scored.append((score, u["symbol"]))
        picks[d] = [s for _, s in sorted(scored, reverse=True)[:top_n]]
    return picks
