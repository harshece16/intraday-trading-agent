"""
Cohort 2 of the rule lab: intraday entry conditions translated from the two
strategy catalogs (popular YouTube trading videos; named practitioners,
GitHub, Reddit, Quantpedia and SSRN), fixed in docs/research/prereg-rule-lab.md
amendment 4 before any of them was computed on data.

Each condition is an entry signal on a finished 5-minute bar, with a side.
Every one trades through the lab's common exits (H30, or R3 with the stop
beyond the signal bar); the catalogs' own stops, targets and signal exits are
not modelled (amendment 4 §3). Every series here is causal: a value at bar k
reads bars 0..k only, and a 15- or 60-minute bar is read only once its last
5-minute bar has finished. tests/test_rule_lab.py checks that by truncation.

Imported by rule_lab at the end of its module; registers into its REGISTRY.
"""
import indicators

import rule_lab
from rule_lab import _bar, _patterns, _rvol, register

COHORT = 2


# ---- causal series over the input, computed once per stock-session --------------

def _cached(ctx, key, fn):
    store = ctx.setdefault("_series", {})
    if key not in store:
        store[key] = fn()
    return store[key]


def _closes(ctx):
    return _cached(ctx, "closes", lambda: [b["close"] for b in ctx["bars"]])


def ema(ctx, n):
    return _cached(ctx, ("ema", n), lambda: indicators.ema_series(_closes(ctx), n))


def _ema_of(values, n):
    """EMA of a series that starts with None values (seeded on the first n valid ones)."""
    out = [None] * len(values)
    start = next((i for i, v in enumerate(values) if v is not None), None)
    if start is None:
        return out
    tail = indicators.ema_series(values[start:], n)
    out[start:] = tail
    return out


def dema(ctx, n):
    def f():
        e = ema(ctx, n)
        ee = _ema_of(e, n)
        return [None if a is None or b is None else 2 * a - b for a, b in zip(e, ee)]
    return _cached(ctx, ("dema", n), f)


def rsi(ctx, n):
    def f():
        c = _closes(ctx)
        out = [None] * len(c)
        if len(c) <= n:
            return out
        gains = [max(0.0, c[i] - c[i - 1]) for i in range(1, n + 1)]
        losses = [max(0.0, c[i - 1] - c[i]) for i in range(1, n + 1)]
        ag, al = sum(gains) / n, sum(losses) / n
        out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
        for i in range(n + 1, len(c)):
            d = c[i] - c[i - 1]
            ag = (ag * (n - 1) + max(0.0, d)) / n
            al = (al * (n - 1) + max(0.0, -d)) / n
            out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
        return out
    return _cached(ctx, ("rsi", n), f)


def _sma_of(values, n):
    out = [None] * len(values)
    for i in range(len(values)):
        w = values[max(0, i - n + 1):i + 1]
        if len(w) == n and all(v is not None for v in w):
            out[i] = sum(w) / n
    return out


def stoch_rsi(ctx):
    """Stochastic RSI (RSI 14, stochastic 14, %K smoothed 3, %D 3): (%K, %D) series."""
    def f():
        r = rsi(ctx, 14)
        raw = [None] * len(r)
        for i in range(len(r)):
            w = r[max(0, i - 13):i + 1]
            if len(w) == 14 and all(v is not None for v in w):
                hi, lo = max(w), min(w)
                raw[i] = 100 * (r[i] - lo) / (hi - lo) if hi > lo else 50.0
        k = _sma_of(raw, 3)
        return k, _sma_of(k, 3)
    return _cached(ctx, "stochrsi", f)


def stoch(bars, n=14, sk=3, sd=3):
    raw = [None] * len(bars)
    for i in range(n - 1, len(bars)):
        w = bars[i - n + 1:i + 1]
        hh, ll = max(b["high"] for b in w), min(b["low"] for b in w)
        raw[i] = 100 * (bars[i]["close"] - ll) / (hh - ll) if hh > ll else 50.0
    k = _sma_of(raw, sk)
    return k, _sma_of(k, sd)


def macd(ctx):
    def f():
        e12, e26 = ema(ctx, 12), ema(ctx, 26)
        line = [None if a is None or b is None else a - b for a, b in zip(e12, e26)]
        return line, _ema_of(line, 9)
    return _cached(ctx, "macd", f)


def _atr_series(bars, n):
    """Mean true range over n bars at each bar (indicators.atr's definition)."""
    tr = [None] + [max(bars[i]["high"] - bars[i]["low"], abs(bars[i]["high"] - bars[i - 1]["close"]),
                       abs(bars[i]["low"] - bars[i - 1]["close"])) for i in range(1, len(bars))]
    return _sma_of(tr, n)


def supertrend(bars, p, m):
    """Supertrend on (high+low)/2 with ATR(p) x m: (direction +1/-1, line) per bar, None before ATR."""
    atr = _atr_series(bars, p)
    d, line = [None] * len(bars), [None] * len(bars)
    fu = fl = None
    for i, b in enumerate(bars):
        if atr[i] is None:
            continue
        mid = (b["high"] + b["low"]) / 2
        bu, bl = mid + m * atr[i], mid - m * atr[i]
        prev_c = bars[i - 1]["close"]
        fu = bu if fu is None or bu < fu or prev_c > fu else fu
        fl = bl if fl is None or bl > fl or prev_c < fl else fl
        prev = d[i - 1] if i and d[i - 1] is not None else 1
        if prev == 1:
            cur = -1 if b["close"] < fl else 1
        else:
            cur = 1 if b["close"] > fu else -1
        d[i], line[i] = cur, (fl if cur == 1 else fu)
    return d, line


def st(ctx, p, m):
    return _cached(ctx, ("st", p, m), lambda: supertrend(ctx["bars"], p, m))


def bollinger(ctx, n, k):
    def f():
        c = _closes(ctx)
        mid, up, lo = [None] * len(c), [None] * len(c), [None] * len(c)
        s1 = s2 = 0.0
        for i, x in enumerate(c):
            s1 += x
            s2 += x * x
            if i >= n:
                s1 -= c[i - n]
                s2 -= c[i - n] ** 2
            if i >= n - 1:
                mu = s1 / n
                sd = max(0.0, s2 / n - mu * mu) ** 0.5
                mid[i], up[i], lo[i] = mu, mu + k * sd, mu - k * sd
        return mid, up, lo
    return _cached(ctx, ("bb", n, k), f)


def heikin_ashi(ctx):
    def f():
        out = []
        for i, b in enumerate(ctx["bars"]):
            hc = (b["open"] + b["high"] + b["low"] + b["close"]) / 4
            ho = (b["open"] + b["close"]) / 2 if i == 0 else (out[-1]["open"] + out[-1]["close"]) / 2
            out.append({"open": ho, "close": hc, "high": max(b["high"], ho, hc), "low": min(b["low"], ho, hc)})
        return out
    return _cached(ctx, "ha", f)


# ---- higher timeframes: bars resampled from today's 5-minute bars ---------------

def resampled(ctx, minutes):
    """Today's bars grouped into `minutes` bars aligned to 09:15, with all earlier sessions'
    bars before them grouped the same way. Each item: a bar and the input index of its last
    5-minute bar, so it is used only once that 5-minute bar has finished."""
    per = minutes // 5

    def f():
        out = []
        by_day = {}
        for k, b in enumerate(ctx["bars"]):
            by_day.setdefault(b["time"][:10], []).append(k)
        for day in sorted(by_day):
            ks = by_day[day]
            for s in range(0, len(ks), per):
                grp = ks[s:s + per]
                if len(grp) < per:
                    break
                bs = [ctx["bars"][j] for j in grp]
                out.append(({"time": bs[0]["time"], "open": bs[0]["open"], "high": max(b["high"] for b in bs),
                             "low": min(b["low"] for b in bs), "close": bs[-1]["close"],
                             "volume": sum(b["volume"] for b in bs)}, grp[-1]))
        return out
    return _cached(ctx, ("rs", minutes), f)


def _htf_maps(ctx, minutes):
    """(input index -> the last finished higher-timeframe bar, input index -> the bar it completes)."""
    def f():
        rs = resampled(ctx, minutes)
        last, completes = [None] * len(ctx["bars"]), {}
        j = -1
        ends = [end for _, end in rs]
        for k in range(len(ctx["bars"])):
            while j + 1 < len(ends) and ends[j + 1] <= k:
                j += 1
            last[k] = j if j >= 0 else None
        for jj, end in enumerate(ends):
            completes[end] = jj
        return last, completes
    return _cached(ctx, ("htfmaps", minutes), f)


def htf_index(ctx, minutes, k):
    """Index into resampled(minutes) of the last higher-timeframe bar finished by input bar k, or None."""
    return _htf_maps(ctx, minutes)[0][k]


def completes_htf(ctx, minutes, k):
    """The higher-timeframe bar index whose last 5-minute bar is input bar k, or None."""
    return _htf_maps(ctx, minutes)[1].get(k)


def htf_ema(ctx, minutes, n):
    return _cached(ctx, ("hema", minutes, n),
                   lambda: indicators.ema_series([b["close"] for b, _ in resampled(ctx, minutes)], n))


def htf_adx(ctx, minutes, j):
    bars = [b for b, _ in resampled(ctx, minutes)[:j + 1]]
    a = indicators.adx(bars, 14)
    return a["adx"] if a else None


# ---- the previous session's levels -----------------------------------------------

def prev_day(ctx):
    def f():
        days = sorted({b["time"][:10] for b in ctx["bars"] if b["time"][:10] < ctx["session"]})
        if not days:
            return None
        bs = [b for b in ctx["bars"] if b["time"][:10] == days[-1]]
        h, l, c, o = max(b["high"] for b in bs), min(b["low"] for b in bs), bs[-1]["close"], bs[0]["open"]
        p = (h + l + c) / 3
        bc = (h + l) / 2
        tc = 2 * p - bc
        lv = {"PDH": h, "PDL": l, "PDC": c, "PDO": o, "P": p, "BC": bc, "TC": tc,
              "CPR_TOP": max(tc, bc), "CPR_BOT": min(tc, bc), "WIDTH": abs(tc - bc) / p * 100,
              "R1": 2 * p - l, "S1": 2 * p - h, "R2": p + (h - l), "S2": p - (h - l),
              "FR1": p + 0.382 * (h - l), "FR2": p + 0.618 * (h - l), "FR3": p + (h - l),
              "FS1": p - 0.382 * (h - l), "FS2": p - 0.618 * (h - l), "FS3": p - (h - l)}
        # point of control: 0.1%-of-close bins of typical price, by volume
        width = c * 0.001
        vol = {}
        for b in bs:
            key = int(((b["high"] + b["low"] + b["close"]) / 3) // width)
            vol[key] = vol.get(key, 0) + b["volume"]
        lv["POC"] = (max(vol, key=lambda x: (vol[x], -x)) + 0.5) * width if vol else None
        # the day before, for "today's CPR above yesterday's"
        if len(days) >= 2:
            b2 = [b for b in ctx["bars"] if b["time"][:10] == days[-2]]
            h2, l2, c2 = max(b["high"] for b in b2), min(b["low"] for b in b2), b2[-1]["close"]
            p2 = (h2 + l2 + c2) / 3
            bc2 = (h2 + l2) / 2
            tc2 = 2 * p2 - bc2
            lv["PREV_CPR_TOP"], lv["PREV_CPR_BOT"] = max(tc2, bc2), min(tc2, bc2)
        lv["DAYS_UP_3"] = None
        if len(days) >= 4:
            closes = [[b for b in ctx["bars"] if b["time"][:10] == d][-1]["close"] for d in days[-4:]]
            lv["DAYS_UP_3"] = all(closes[i] > closes[i - 1] for i in range(1, 4))
        return lv
    return _cached(ctx, "prevday", f)


# ---- helpers ----------------------------------------------------------------------

def _k(ctx, pos):
    return ctx["today"][pos]


def _minute(ctx, pos):
    return rule_lab._minutes_of(_bar(ctx, pos)["time"])


def _crosses_up(ctx, pos, level):
    return pos >= 1 and level is not None and _bar(ctx, pos)["close"] > level >= _bar(ctx, pos - 1)["close"]


def _crosses_down(ctx, pos, level):
    return pos >= 1 and level is not None and _bar(ctx, pos)["close"] < level <= _bar(ctx, pos - 1)["close"]


def _first_today(ctx, pos, test):
    """test(pos) holds on `pos` and on no earlier bar of today."""
    return test(pos) and not any(test(j) for j in range(pos))


def _mirror(fn_long, fn_short, rid, name, family, sources):
    register(rid + "L", name + ", long", "LONG", family, fn_long, cohort=COHORT)
    register(rid + "S", name + ", short", "SHORT", family, fn_short, cohort=COHORT)
    rule_lab.REGISTRY[rid + "L"]["sources"] = sources
    rule_lab.REGISTRY[rid + "S"]["sources"] = sources


# ---- the conditions (amendment 4 §2) ------------------------------------------------

def y01(long):
    """5-EMA alert candle (Power of Stocks; also subasish_pani_5ema): the previous bar lies
    wholly on one side of EMA5 and this bar closes beyond its far extreme."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        e = ema(ctx, 5)
        if pos < 1 or e[k - 1] is None:
            return False
        p, c = ctx["bars"][k - 1], ctx["bars"][k]
        if long:
            return p["high"] < e[k - 1] and c["close"] > p["high"]
        return p["low"] > e[k - 1] and c["close"] < p["low"]
    return sig


def y02(long):
    """EMA9/15 trend, EMA9 slope >= 0.10% over 3 bars, touch of EMA9, trigger candle."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        e9, e15 = ema(ctx, 9), ema(ctx, 15)
        if k < 3 or None in (e9[k], e15[k], e9[k - 3]):
            return False
        c = ctx["bars"][k]
        body, rng = abs(c["close"] - c["open"]), c["high"] - c["low"]
        pats = _patterns(ctx, k, cache)
        slope = e9[k] / e9[k - 3] - 1
        if long:
            trig = bool(pats & {"Bullish Engulfing", "Hammer"}) or (rng > 0 and body >= 0.6 * rng and c["close"] > c["open"])
            return e9[k] > e15[k] and slope >= 0.001 and c["low"] <= e9[k] < c["close"] and trig
        trig = bool(pats & {"Bearish Engulfing", "Shooting Star"}) or (rng > 0 and body >= 0.6 * rng and c["close"] < c["open"])
        return e9[k] < e15[k] and slope <= -0.001 and c["high"] >= e9[k] > c["close"] and trig
    return sig


def y03(long):
    """EMA9 crosses EMA21 (the catalog's control)."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        a, b = ema(ctx, 9), ema(ctx, 21)
        if k < 1 or None in (a[k], b[k], a[k - 1], b[k - 1]):
            return False
        return (a[k] > b[k] and a[k - 1] <= b[k - 1]) if long else (a[k] < b[k] and a[k - 1] >= b[k - 1])
    return sig


def y04(long):
    """EMA200 trend, EMA20 over EMA50, touch of EMA20 in the last 3 bars, Stoch RSI reset (CMB-1)."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        e200, e20, e50 = ema(ctx, 200), ema(ctx, 20), ema(ctx, 50)
        kk, dd = stoch_rsi(ctx)
        if k < 3 or None in (e200[k], e20[k], e50[k], kk[k], dd[k], kk[k - 1], dd[k - 1]):
            return False
        bars = ctx["bars"]
        c = bars[k]["close"]
        if long:
            return (c > e200[k] and e20[k] > e50[k] and min(b["low"] for b in bars[k - 2:k + 1]) <= e20[k]
                    and kk[k] > dd[k] and kk[k - 1] <= dd[k - 1] and kk[k - 1] < 20)
        return (c < e200[k] and e20[k] < e50[k] and max(b["high"] for b in bars[k - 2:k + 1]) >= e20[k]
                and kk[k] < dd[k] and kk[k - 1] >= dd[k - 1] and kk[k - 1] > 80)
    return sig


def y05(long):
    """VWAP hold-and-bounce (long) or rejection (short): six closes on one side, a touch
    within 0.1%, a close back on that side with the bar's colour, volume at least its 6-bar mean."""
    def sig(ctx, pos, cache):
        if pos < 6:
            return False
        k = _k(ctx, pos)
        v = ctx["vwap"]
        c = ctx["bars"][k]
        prior = [ctx["today"][pos - j] for j in range(1, 7)]
        if v.get(k) is None or any(v.get(j) is None for j in prior):
            return False
        mean_vol = sum(ctx["bars"][j]["volume"] for j in prior) / 6
        if c["volume"] < mean_vol:
            return False
        if long:
            return (all(ctx["bars"][j]["close"] > v[j] for j in prior) and c["low"] <= v[k] * 1.001
                    and c["close"] > v[k] and c["close"] > c["open"])
        return (all(ctx["bars"][j]["close"] < v[j] for j in prior) and c["high"] >= v[k] * 0.999
                and c["close"] < v[k] and c["close"] < c["open"])
    return sig


def y06(long):
    """From 10:45: VWAP side, a close through a Fibonacci pivot level, Stoch RSI %K over %D."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        k = _k(ctx, pos)
        kk, dd = stoch_rsi(ctx)
        if not lv or _minute(ctx, pos) < 10 * 60 + 45 or ctx["vwap"].get(k) is None or None in (kk[k], dd[k]):
            return False
        c = _bar(ctx, pos)["close"]
        if long:
            levels = [lv[x] for x in ("P", "FR1", "FR2", "FR3")]
            return c > ctx["vwap"][k] and kk[k] > dd[k] and any(_crosses_up(ctx, pos, x) for x in levels)
        levels = [lv[x] for x in ("P", "FS1", "FS2", "FS3")]
        return c < ctx["vwap"][k] and kk[k] < dd[k] and any(_crosses_down(ctx, pos, x) for x in levels)
    return sig


def y07(long):
    """One-hour opening range (09:15-10:10): the first close beyond it (also unger_first_hour_breakout)."""
    def sig(ctx, pos, cache):
        if pos < 12:
            return False
        first = [_bar(ctx, j) for j in range(12)]
        hi, lo = max(b["high"] for b in first), min(b["low"] for b in first)
        if long:
            return _first_today(ctx, pos, lambda j: j >= 12 and _bar(ctx, j)["close"] > hi)
        return _first_today(ctx, pos, lambda j: j >= 12 and _bar(ctx, j)["close"] < lo)
    return sig


def y08(long):
    """Failed opening-range break, faded: a bar pokes beyond the 15-minute range and closes back
    inside, the first time today (short above the high; long below the low)."""
    def sig(ctx, pos, cache):
        rng = ctx.get("or")
        if pos < 3 or not rng:
            return False
        hi, lo = rng
        if long:
            return _first_today(ctx, pos, lambda j: j >= 3 and _bar(ctx, j)["low"] < lo < _bar(ctx, j)["close"])
        return _first_today(ctx, pos, lambda j: j >= 3 and _bar(ctx, j)["high"] > hi > _bar(ctx, j)["close"])
    return sig


def y09(long):
    """First-hour sweep: a later hourly bar trades beyond the first hour's extreme and closes back
    inside it, first time today; read when that hourly bar finishes."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        j = completes_htf(ctx, 60, k)
        if j is None:
            return False
        rs = resampled(ctx, 60)
        day_bars = [(i, b) for i, (b, _) in enumerate(rs) if b["time"][:10] == ctx["session"]]
        if len(day_bars) < 2 or day_bars[0][0] == j:
            return False
        h1 = day_bars[0][1]
        mine = [b for i, b in day_bars if i <= j][1:]
        if long:
            hits = [b["low"] < h1["low"] < b["close"] for b in mine]
        else:
            hits = [b["high"] > h1["high"] > b["close"] for b in mine]
        return hits[-1] and not any(hits[:-1])
    return sig


def y11(ctx, pos, cache):
    """After three up days and a gap up of 0.5% or more, the first red bar of the morning is
    broken: short (Power of Stocks)."""
    lv = prev_day(ctx)
    pc = ctx.get("prev_close")
    if not lv or not lv.get("DAYS_UP_3") or not pc or not (1 <= pos <= 24):
        return False
    if _bar(ctx, 0)["open"] / pc - 1 < 0.005:
        return False
    reds = [j for j in range(pos) if _bar(ctx, j)["close"] < _bar(ctx, j)["open"]]
    return bool(reds) and reds[0] == pos - 1 and _bar(ctx, pos)["close"] < _bar(ctx, pos - 1)["low"]


def y12(long, kind):
    """Narrow CPR (width <= 0.25%): A, a bounce off the CPR edge after opening beyond it;
    B, a close through max(R1, PDH) (min(S1, PDL) for shorts)."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        if not lv or lv["WIDTH"] > 0.25:
            return False
        c = _bar(ctx, pos)
        o = _bar(ctx, 0)["open"]
        if kind == "A":
            if long:
                return o > lv["CPR_TOP"] and c["low"] <= lv["CPR_TOP"] * 1.001 and c["close"] > lv["CPR_TOP"] and c["close"] > c["open"]
            return o < lv["CPR_BOT"] and c["high"] >= lv["CPR_BOT"] * 0.999 and c["close"] < lv["CPR_BOT"] and c["close"] < c["open"]
        if long:
            return _crosses_up(ctx, pos, max(lv["R1"], lv["PDH"]))
        return _crosses_down(ctx, pos, min(lv["S1"], lv["PDL"]))
    return sig


def y13(long):
    """A close through a classic pivot level (S2, S1, BC, P, TC, R1, R2)."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        if not lv:
            return False
        levels = [lv[x] for x in ("S2", "S1", "BC", "P", "TC", "R1", "R2")]
        test = _crosses_up if long else _crosses_down
        return any(test(ctx, pos, x) for x in levels)
    return sig


def y14(long):
    """From 09:40: ADX(14) on 15-minute bars above 20, Supertrend(10,3) on side, a close through a
    Fibonacci pivot level."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        k = _k(ctx, pos)
        d, _ = st(ctx, 10, 3)
        if not lv or _minute(ctx, pos) < 9 * 60 + 40 or d[k] is None:
            return False
        j = htf_index(ctx, 15, k)
        if j is None:
            return False
        a = _cached(ctx, ("hadx", j), lambda: htf_adx(ctx, 15, j))
        if a is None or a <= 20:
            return False
        if long:
            return d[k] == 1 and any(_crosses_up(ctx, pos, lv[x]) for x in ("P", "FR1", "FR2", "FR3"))
        return d[k] == -1 and any(_crosses_down(ctx, pos, lv[x]) for x in ("P", "FS1", "FS2", "FS3"))
    return sig


def y15(long):
    """Supertrend(12,3) flips with price beyond DEMA200."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        d, _ = st(ctx, 12, 3)
        dm = dema(ctx, 200)
        if k < 1 or None in (d[k], d[k - 1], dm[k]):
            return False
        c = ctx["bars"][k]["close"]
        return (c > dm[k] and d[k] == 1 and d[k - 1] == -1) if long else (c < dm[k] and d[k] == -1 and d[k - 1] == 1)
    return sig


def y16(long):
    """EMA200 side, Stoch RSI crossing back from an extreme within 4 bars and short of 50,
    at least two of Supertrend (12,3), (11,2), (10,1) on side."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        e200 = ema(ctx, 200)
        kk, dd = stoch_rsi(ctx)
        if k < 4 or None in (e200[k], kk[k], dd[k], kk[k - 1], dd[k - 1]) or any(x is None for x in kk[k - 3:k + 1]):
            return False
        dirs = [st(ctx, p, m)[0][k] for p, m in ((12, 3), (11, 2), (10, 1))]
        c = ctx["bars"][k]["close"]
        if long:
            return (c > e200[k] and kk[k] > dd[k] and kk[k - 1] <= dd[k - 1] and min(kk[k - 3:k + 1]) < 20
                    and kk[k] < 50 and sum(1 for x in dirs if x == 1) >= 2)
        return (c < e200[k] and kk[k] < dd[k] and kk[k - 1] >= dd[k - 1] and max(kk[k - 3:k + 1]) > 80
                and kk[k] > 50 and sum(1 for x in dirs if x == -1) >= 2)
    return sig


def y17(long):
    """MACD crosses its signal, Supertrend(10,3) flipped to the same side within 3 bars, price near VWAP."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        line, sigl = macd(ctx)
        d, _ = st(ctx, 10, 3)
        v = ctx["vwap"].get(k)
        if k < 3 or v is None or None in (line[k], sigl[k], line[k - 1], sigl[k - 1]) or any(x is None for x in d[k - 3:k + 1]):
            return False
        c = ctx["bars"][k]["close"]
        want = 1 if long else -1
        flipped = any(d[j] == want and d[j - 1] == -want for j in range(k - 2, k + 1))
        if long:
            return line[k] > sigl[k] and line[k - 1] <= sigl[k - 1] and d[k] == 1 and flipped and c <= v * 1.002
        return line[k] < sigl[k] and line[k - 1] >= sigl[k - 1] and d[k] == -1 and flipped and c >= v * 0.998
    return sig


def y18(long):
    """Close beyond Bollinger(30,2) with RSI(13) below 25 (above 75), not in a squeeze (band width
    at the bar before in the bottom 20% of its last 100 bars)."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        mid, up, lo = bollinger(ctx, 30, 2)
        r = rsi(ctx, 13)
        if k < 100 or None in (lo[k], up[k], r[k]):
            return False
        widths = [(up[j] - lo[j]) / mid[j] for j in range(k - 100, k) if mid[j]]
        if len(widths) < 100:
            return False
        w_prev = widths[-1]
        if sum(1 for w in widths if w < w_prev) < 0.2 * len(widths):
            return False
        c = ctx["bars"][k]["close"]
        return (c < lo[k] and r[k] < 25) if long else (c > up[k] and r[k] > 75)
    return sig


def y19(long):
    """MACD crosses its signal on the far side of zero, with price beyond EMA200."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        line, sigl = macd(ctx)
        e200 = ema(ctx, 200)
        if k < 1 or None in (line[k], sigl[k], line[k - 1], sigl[k - 1], e200[k]):
            return False
        c = ctx["bars"][k]["close"]
        if long:
            return c > e200[k] and line[k] > sigl[k] and line[k - 1] <= sigl[k - 1] and line[k] < 0 and sigl[k] < 0
        return c < e200[k] and line[k] < sigl[k] and line[k - 1] >= sigl[k - 1] and line[k] > 0 and sigl[k] > 0
    return sig


def y20(long):
    """Heikin-Ashi: two strong candles without a wick against them after a doji 2 to 4 bars back,
    and a stochastic extreme in the 6 bars before."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        if k < 8:
            return False
        ha = heikin_ashi(ctx)
        sk, _ = _cached(ctx, "stoch", lambda: stoch(ctx["bars"]))

        def strong(h):
            rng = h["high"] - h["low"]
            body = abs(h["close"] - h["open"])
            if rng <= 0 or body < 0.5 * rng:
                return False
            if long:
                return h["close"] > h["open"] and h["low"] >= min(h["open"], h["close"]) - 1e-12
            return h["close"] < h["open"] and h["high"] <= max(h["open"], h["close"]) + 1e-12
        doji = any((ha[j]["high"] - ha[j]["low"]) > 0 and abs(ha[j]["close"] - ha[j]["open"]) <= 0.2 * (ha[j]["high"] - ha[j]["low"])
                   for j in range(k - 4, k - 1))
        window = [x for x in sk[k - 6:k - 1] if x is not None]
        extreme = any(x < 20 for x in window) if long else any(x > 80 for x in window)
        return strong(ha[k]) and strong(ha[k - 1]) and doji and extreme
    return sig


def y21(long):
    """Inside bar, then a close beyond the mother bar, in a trend: five closes on side of a
    rising (falling) EMA10."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        e10 = ema(ctx, 10)
        if pos < 2 or k < 8 or any(e10[j] is None for j in range(k - 8, k + 1)):
            return False
        bars = ctx["bars"]
        a, b, c = bars[k - 2], bars[k - 1], bars[k]
        if not (b["high"] <= a["high"] and b["low"] >= a["low"]):
            return False
        if long:
            return (c["close"] > a["high"] and all(bars[k - j]["close"] > e10[k - j] for j in range(1, 6))
                    and e10[k - 1] > e10[k - 4])
        return (c["close"] < a["low"] and all(bars[k - j]["close"] < e10[k - j] for j in range(1, 6))
                and e10[k - 1] < e10[k - 4])
    return sig


def y22(long):
    """False break: the previous bar made a new 20-bar extreme, and this bar engulfs it or sweeps
    beyond it and closes past its other end."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        if k < 22:
            return False
        bars = ctx["bars"]
        p, c = bars[k - 1], bars[k]
        window = bars[k - 21:k - 1]
        if long:
            if not p["low"] < min(b["low"] for b in window):
                return False
            engulf = c["close"] > p["open"] and c["open"] <= p["close"] and p["close"] < p["open"]
            sweep = c["low"] < p["low"] and c["close"] > p["high"]
            return engulf or sweep
        if not p["high"] > max(b["high"] for b in window):
            return False
        engulf = c["close"] < p["open"] and c["open"] >= p["close"] and p["close"] > p["open"]
        sweep = c["high"] > p["high"] and c["close"] < p["low"]
        return engulf or sweep
    return sig


def y23(long):
    """A retest of the previous session's point of control with a wick (volume profile)."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        if not lv or not lv.get("POC") or pos < 1:
            return False
        poc = lv["POC"]
        c, p = _bar(ctx, pos), _bar(ctx, pos - 1)
        body = abs(c["close"] - c["open"])
        o = _bar(ctx, 0)["open"]
        if long:
            wick = min(c["open"], c["close"]) - c["low"]
            return (o > poc and c["low"] <= poc * 1.001 and c["close"] > poc and wick >= 1.5 * body
                    and c["close"] > c["open"] and p["close"] < p["open"])
        wick = c["high"] - max(c["open"], c["close"])
        return (o < poc and c["high"] >= poc * 0.999 and c["close"] < poc and wick >= 1.5 * body
                and c["close"] < c["open"] and p["close"] > p["open"])
    return sig


def y24(long):
    """15-minute inside candle, then a 15-minute close beyond the inside candle."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        j = completes_htf(ctx, 15, k)
        if j is None or j < 2:
            return False
        rs = resampled(ctx, 15)
        a, b, c = rs[j - 2][0], rs[j - 1][0], rs[j][0]
        if c["time"][:10] != ctx["session"] or not (b["high"] <= a["high"] and b["low"] >= a["low"]):
            return False
        return c["close"] > b["high"] if long else c["close"] < b["low"]
    return sig


def y26(long):
    """VWAP side, a close through the highest of the opening-range high, PDH and the next
    Fibonacci pivot above, on relative volume of at least 1.5 (CMB-2)."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        k = _k(ctx, pos)
        rng = ctx.get("or")
        rv = _rvol(ctx, k)
        if not lv or not rng or pos < 3 or rv is None or rv < 1.5 or ctx["vwap"].get(k) is None:
            return False
        if not (9 * 60 + 30 <= _minute(ctx, pos) <= 14 * 60 + 30):
            return False
        prev_c = _bar(ctx, pos - 1)["close"]
        c = _bar(ctx, pos)["close"]
        if long:
            fib = [lv[x] for x in ("P", "FR1", "FR2", "FR3") if lv[x] > prev_c]
            level = max([rng[0], lv["PDH"]] + ([min(fib)] if fib else []))
            return c > ctx["vwap"][k] and _crosses_up(ctx, pos, level)
        fib = [lv[x] for x in ("P", "FS1", "FS2", "FS3") if lv[x] < prev_c]
        level = min([rng[1], lv["PDL"]] + ([max(fib)] if fib else []))
        return c < ctx["vwap"][k] and _crosses_down(ctx, pos, level)
    return sig


def y27(long):
    """Close beyond Bollinger(20,2) with RSI(14) past 30 (70) on the previous bar, then a close
    past that bar's other extreme (CMB-7)."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        _, up, lo = bollinger(ctx, 20, 2)
        r = rsi(ctx, 14)
        if k < 1 or None in (lo[k - 1], up[k - 1], r[k - 1]):
            return False
        p, c = ctx["bars"][k - 1], ctx["bars"][k]
        if long:
            return p["close"] < lo[k - 1] and r[k - 1] < 30 and c["close"] > p["high"]
        return p["close"] > up[k - 1] and r[k - 1] > 70 and c["close"] < p["low"]
    return sig


def o01(long):
    """Williams volatility breakout: the first close beyond today's open +/- 0.6 x the previous session's range."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        if not lv:
            return False
        o = _bar(ctx, 0)["open"]
        d = 0.6 * (lv["PDH"] - lv["PDL"])
        if long:
            return _first_today(ctx, pos, lambda j: _bar(ctx, j)["close"] > o + d)
        return _first_today(ctx, pos, lambda j: _bar(ctx, j)["close"] < o - d)
    return sig


def o02(long):
    """Williams 'oops': an open beyond the previous session's low (high) by at least 0.3 x its range,
    then the first close back inside it, before 11:00."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        if not lv or _minute(ctx, pos) > 11 * 60:
            return False
        o = _bar(ctx, 0)["open"]
        r = lv["PDH"] - lv["PDL"]
        if long:
            return o <= lv["PDL"] - 0.3 * r and _first_today(ctx, pos, lambda j: _bar(ctx, j)["close"] > lv["PDL"])
        return o >= lv["PDH"] + 0.3 * r and _first_today(ctx, pos, lambda j: _bar(ctx, j)["close"] < lv["PDH"])
    return sig


def o03(long):
    """Turtle soup on 5-minute bars: a new 20-bar extreme beyond one at least 4 bars old, then a
    close back inside it (Raschke)."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        if k < 21:
            return False
        bars = ctx["bars"]
        prior = bars[k - 20:k]
        if long:
            j = min(range(len(prior)), key=lambda x: prior[x]["low"])
            ext = prior[j]["low"]
            return len(prior) - j >= 4 and bars[k]["low"] < ext < bars[k]["close"]
        j = max(range(len(prior)), key=lambda x: prior[x]["high"])
        ext = prior[j]["high"]
        return len(prior) - j >= 4 and bars[k]["high"] > ext > bars[k]["close"]
    return sig


def _running(ctx, key):
    """Today's running low (key "low") or high ("high") through each bar."""
    def f():
        out, cur = [], None
        for k in ctx["today"]:
            v = ctx["bars"][k][key]
            cur = v if cur is None else (min(cur, v) if key == "low" else max(cur, v))
            out.append(cur)
        return out
    return _cached(ctx, ("running", key), f)


def o04(long):
    """Raschke 80-20: yesterday opened in the top 20% of its range and closed in the bottom 20%
    (mirror for shorts); before 11:00 price trades 0.1 x that range past its low, then the first
    close back above it."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        if not lv or _minute(ctx, pos) > 11 * 60:
            return False
        r = lv["PDH"] - lv["PDL"]
        if r <= 0:
            return False
        o_rel, c_rel = (lv["PDO"] - lv["PDL"]) / r, (lv["PDC"] - lv["PDL"]) / r
        if long:
            lows = _running(ctx, "low")
            hit = lambda j: lows[j] <= lv["PDL"] - 0.1 * r and _bar(ctx, j)["close"] > lv["PDL"]  # noqa: E731
            return o_rel >= 0.8 and c_rel <= 0.2 and _first_today(ctx, pos, hit)
        highs = _running(ctx, "high")
        hit = lambda j: highs[j] >= lv["PDH"] + 0.1 * r and _bar(ctx, j)["close"] < lv["PDH"]  # noqa: E731
        return o_rel <= 0.2 and c_rel >= 0.8 and _first_today(ctx, pos, hit)
    return sig


def o05(long):
    """Raschke 'anti' on 15-minute bars: slow stochastic %D rising for 3 bars, fast %K turning up
    after at least two declines (mirror for shorts); read as the 15-minute bar finishes."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        j = completes_htf(ctx, 15, k)
        if j is None or j < 4:
            return False
        bars = [b for b, _ in resampled(ctx, 15)]
        fk, _ = _cached(ctx, "stoch15f", lambda: stoch(bars, 7, 1, 1))
        _, sd = _cached(ctx, "stoch15s", lambda: stoch(bars, 7, 10, 1))
        w = fk[j - 3:j + 1]
        d = sd[j - 3:j + 1]
        if any(x is None for x in w + d) or bars[j]["time"][:10] != ctx["session"]:
            return False
        if long:
            return d[3] > d[2] > d[1] > d[0] and w[1] < w[0] and w[2] < w[1] and w[3] > w[2]
        return d[3] < d[2] < d[1] < d[0] and w[1] > w[0] and w[2] > w[1] and w[3] < w[2]
    return sig


def o06(long):
    """Narrow CPR trend day: narrow (<= 0.25%), open beyond the CPR, today's CPR wholly beyond
    yesterday's, and the first close beyond the 15-minute opening range."""
    def sig(ctx, pos, cache):
        lv = prev_day(ctx)
        rng = ctx.get("or")
        if not lv or not rng or "PREV_CPR_TOP" not in lv or lv["WIDTH"] > 0.25 or pos < 3:
            return False
        o = _bar(ctx, 0)["open"]
        if long:
            return (o > lv["TC"] and lv["CPR_BOT"] > lv["PREV_CPR_TOP"]
                    and _first_today(ctx, pos, lambda j: j >= 3 and _bar(ctx, j)["close"] > rng[0]))
        return (o < lv["BC"] and lv["CPR_TOP"] < lv["PREV_CPR_BOT"]
                and _first_today(ctx, pos, lambda j: j >= 3 and _bar(ctx, j)["close"] < rng[1]))
    return sig


def o07l(ctx, pos, cache):
    """GFR: yesterday closed in the bottom quarter of its range, today opens below its low, and a
    bullish 5-minute close back above it before 12:00."""
    lv = prev_day(ctx)
    if not lv or _minute(ctx, pos) > 12 * 60:
        return False
    r = lv["PDH"] - lv["PDL"]
    if r <= 0 or (lv["PDC"] - lv["PDL"]) / r > 0.25 or _bar(ctx, 0)["open"] >= lv["PDL"]:
        return False
    return _first_today(ctx, pos, lambda j: _bar(ctx, j)["close"] > lv["PDL"] and _bar(ctx, j)["close"] > _bar(ctx, j)["open"])


def o07s(ctx, pos, cache):
    """RDP: open above yesterday's high, the first bar bullish, then a close below the first bar's low."""
    lv = prev_day(ctx)
    if not lv or pos < 1:
        return False
    f = _bar(ctx, 0)
    if f["open"] <= lv["PDH"] or f["close"] <= f["open"]:
        return False
    return _first_today(ctx, pos, lambda j: j >= 1 and _bar(ctx, j)["close"] < f["low"])


def o08(long):
    """Supertrend(10,3) on 15-minute bars flips; read as the 15-minute bar finishes."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        j = completes_htf(ctx, 15, k)
        if j is None or j < 1:
            return False
        d, _ = _cached(ctx, "st15", lambda: supertrend([b for b, _ in resampled(ctx, 15)], 10, 3))
        if d[j] is None or d[j - 1] is None:
            return False
        return (d[j] == 1 and d[j - 1] == -1) if long else (d[j] == -1 and d[j - 1] == 1)
    return sig


def o09(long):
    """TTM squeeze on 15-minute bars: Bollinger(20,2) inside Keltner(20, 1.5 ATR) for at least 6 bars,
    then released, with momentum (close minus the mean of the 20-bar mid-range and SMA20) on side."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        j = completes_htf(ctx, 15, k)
        if j is None or j < 27:
            return False
        bars = [b for b, _ in resampled(ctx, 15)]

        def squeezed(x):
            w = bars[x - 19:x + 1]
            cl = [b["close"] for b in w]
            mu = sum(cl) / 20
            sd = (sum((c - mu) ** 2 for c in cl) / 20) ** 0.5
            e = indicators.ema(cl, 20)
            a = indicators.atr(bars[x - 20:x + 1], 20)
            if e is None or a is None:
                return None
            return mu + 2 * sd < e + 1.5 * a and mu - 2 * sd > e - 1.5 * a
        now = squeezed(j)
        before = [squeezed(x) for x in range(j - 6, j)]
        if now is None or any(b is None for b in before) or now or not all(before):
            return False
        w = bars[j - 19:j + 1]
        mom = w[-1]["close"] - ((max(b["high"] for b in w) + min(b["low"] for b in w)) / 2 + sum(b["close"] for b in w) / 20) / 2
        return mom > 0 if long else mom < 0
    return sig


def f_atr_rising(ctx, pos, cache):
    """Filter: ATR(14) on 5-minute bars above its value 3 bars before (Market Gurukul)."""
    k = _k(ctx, pos)
    if k < 20:
        return False
    atr = _cached(ctx, "atr14", lambda: _atr_series(ctx["bars"], 14))
    return atr[k] is not None and atr[k - 3] is not None and atr[k] > atr[k - 3]


def f_rvol15(ctx, pos, cache):
    """Filter: relative volume at least 1.5."""
    rv = _rvol(ctx, _k(ctx, pos))
    return rv is not None and rv >= 1.5


def f_before_11(ctx, pos, cache):
    """Filter: the signal bar starts at or before 11:00."""
    return _minute(ctx, pos) <= 11 * 60


def f_htf_trend(long):
    """Filter: 15-minute EMA20 beyond EMA50 and the close beyond EMA50, on the last finished 15-minute bar."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        j = htf_index(ctx, 15, k)
        if j is None:
            return False
        e20, e50 = htf_ema(ctx, 15, 20), htf_ema(ctx, 15, 50)
        if e20[j] is None or e50[j] is None:
            return False
        c = ctx["bars"][k]["close"]
        return (e20[j] > e50[j] and c > e50[j]) if long else (e20[j] < e50[j] and c < e50[j])
    return sig


def f_above_ema200(long):
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        e = ema(ctx, 200)
        return e[k] is not None and (ctx["bars"][k]["close"] > e[k] if long else ctx["bars"][k]["close"] < e[k])
    return sig


def f_st_flip(long):
    """Supertrend(10,3) on 5-minute bars flips on this bar."""
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        d, _ = st(ctx, 10, 3)
        if k < 1 or d[k] is None or d[k - 1] is None:
            return False
        return (d[k] == 1 and d[k - 1] == -1) if long else (d[k] == -1 and d[k - 1] == 1)
    return sig


def f_adx15_over_20(ctx, pos, cache):
    k = _k(ctx, pos)
    j = htf_index(ctx, 15, k)
    if j is None:
        return False
    a = _cached(ctx, ("hadx", j), lambda: htf_adx(ctx, 15, j))
    return a is not None and a > 20


def f_engulf_or_hammer(long):
    def sig(ctx, pos, cache):
        pats = _patterns(ctx, _k(ctx, pos), cache)
        return bool(pats & ({"Bullish Engulfing", "Hammer"} if long else {"Bearish Engulfing", "Shooting Star"}))
    return sig


def f_above_vwap(long):
    def sig(ctx, pos, cache):
        k = _k(ctx, pos)
        v = ctx["vwap"].get(k)
        return v is not None and (ctx["bars"][k]["close"] > v if long else ctx["bars"][k]["close"] < v)
    return sig


YT = "yt-strategies/catalog.json"
OT = "strategies-other/catalog.json"


def register_all():
    _mirror(y01(True), y01(False), "Y01", "5-EMA alert candle broken", "moving average",
            [YT + " YT-MA-01", OT + " subasish_pani_5ema"])
    _mirror(y02(True), y02(False), "Y02", "EMA9/15 trend, touch of EMA9, trigger candle", "moving average", [YT + " YT-MA-02"])
    _mirror(y03(True), y03(False), "Y03", "EMA9 crosses EMA21 (control)", "moving average", [YT + " YT-MA-03"])
    _mirror(y04(True), y04(False), "Y04", "EMA200 trend, EMA20 pullback, Stoch RSI reset", "moving average",
            [YT + " YT-MA-04", YT + " CMB-1"])
    _mirror(y05(True), y05(False), "Y05", "VWAP hold-and-bounce / rejection", "vwap", [YT + " YT-VW-01"])
    _mirror(y06(True), y06(False), "Y06", "VWAP side, Fibonacci pivot break, Stoch RSI, after 10:45", "pivot",
            [YT + " YT-VW-02"])
    _mirror(y07(True), y07(False), "Y07", "One-hour opening-range breakout", "range",
            [YT + " YT-OR-02", OT + " unger_first_hour_breakout"])
    _mirror(y08(True), y08(False), "Y08", "Failed opening-range break, faded", "range", [YT + " YT-OR-03"])
    _mirror(y09(True), y09(False), "Y09", "First-hour sweep reversal", "range", [YT + " YT-OR-04"])
    register("Y11S", "Gap up after three up days, first red bar broken, short", "SHORT", "gap", y11, cohort=COHORT)
    rule_lab.REGISTRY["Y11S"]["sources"] = [YT + " YT-GP-02"]
    _mirror(y12(True, "A"), y12(False, "A"), "Y12A", "Narrow CPR, bounce off its edge", "pivot", [YT + " YT-PV-01"])
    _mirror(y12(True, "B"), y12(False, "B"), "Y12B", "Narrow CPR, close through R1/PDH (S1/PDL)", "pivot",
            [YT + " YT-PV-01", YT + " CMB-6"])
    _mirror(y13(True), y13(False), "Y13", "Close through a classic pivot level", "pivot", [YT + " YT-PV-02"])
    _mirror(y14(True), y14(False), "Y14", "ADX(15m) > 20, Supertrend, Fibonacci pivot break", "pivot", [YT + " YT-PV-03"])
    _mirror(y15(True), y15(False), "Y15", "Supertrend(12,3) flip beyond DEMA200", "supertrend", [YT + " YT-ST-01"])
    _mirror(y16(True), y16(False), "Y16", "Triple Supertrend, EMA200, Stoch RSI", "supertrend", [YT + " YT-ST-02"])
    _mirror(y17(True), y17(False), "Y17", "Supertrend, MACD cross, near VWAP", "supertrend", [YT + " YT-ST-03"])
    _mirror(y18(True), y18(False), "Y18", "Bollinger(30,2) and RSI(13) extreme", "oscillator", [YT + " YT-OS-04"])
    _mirror(y19(True), y19(False), "Y19", "MACD cross beyond zero with EMA200", "oscillator", [YT + " YT-OS-05"])
    _mirror(y20(True), y20(False), "Y20", "Heikin-Ashi reversal after a stochastic extreme", "oscillator", [YT + " YT-OS-06"])
    _mirror(y21(True), y21(False), "Y21", "Inside bar, mother-bar break, in an EMA10 trend", "price", [YT + " YT-PA-01"])
    _mirror(y22(True), y22(False), "Y22", "False break of a 20-bar extreme", "price", [YT + " YT-PA-02"])
    _mirror(y23(True), y23(False), "Y23", "Previous session's point of control retest", "volume", [YT + " YT-PA-04"])
    _mirror(y24(True), y24(False), "Y24", "15-minute inside candle breakout", "price", [YT + " YT-PA-05"])
    _mirror(y26(True), y26(False), "Y26", "VWAP side, level break, relative volume 1.5", "vwap", [YT + " CMB-2"])
    _mirror(y27(True), y27(False), "Y27", "Bollinger(20,2)/RSI(14) extreme, then a reversal close", "oscillator",
            [YT + " CMB-7"])
    _mirror(o01(True), o01(False), "O01", "Williams volatility breakout (0.6 x yesterday's range)", "range",
            [OT + " williams_volatility_breakout"])
    _mirror(o02(True), o02(False), "O02", "Williams oops", "gap", [OT + " williams_oops_smash"])
    _mirror(o03(True), o03(False), "O03", "Turtle soup, 5-minute", "price", [OT + " raschke_turtle_soup"])
    _mirror(o04(True), o04(False), "O04", "Raschke 80-20", "price", [OT + " raschke_80_20"])
    _mirror(o05(True), o05(False), "O05", "Raschke anti, 15-minute", "oscillator", [OT + " raschke_anti"])
    _mirror(o06(True), o06(False), "O06", "Narrow CPR trend day, opening-range break", "pivot",
            [OT + " cpr_narrow_trend_day"])
    register("O07L", "GFR: gap below yesterday's low after a weak close, close back above, long", "LONG", "gap", o07l,
             cohort=COHORT)
    register("O07S", "RDP: open above yesterday's high, close below the first bar's low, short", "SHORT", "gap", o07s,
             cohort=COHORT)
    rule_lab.REGISTRY["O07L"]["sources"] = rule_lab.REGISTRY["O07S"]["sources"] = [OT + " cpr_untested_short_index_patterns"]
    _mirror(o08(True), o08(False), "O08", "Supertrend(10,3) flip, 15-minute", "supertrend", [OT + " supertrend_10_3"])
    _mirror(o09(True), o09(False), "O09", "TTM squeeze release, 15-minute", "volatility", [OT + " ttm_squeeze_lazybear"])
    # filters: side copies, so a filter joins same-side combinations; as a single rule it trades alone
    _mirror(f_atr_rising, f_atr_rising, "F01", "Filter: ATR rising", "filter", [YT + " YT-FL-01"])
    _mirror(f_rvol15, f_rvol15, "F02", "Filter: relative volume 1.5", "filter", [YT + " YT-OR-01", YT + " CMB-3"])
    _mirror(f_before_11, f_before_11, "F03", "Filter: by 11:00", "filter", [YT + " YT-OR-01", YT + " CMB-3"])
    _mirror(f_htf_trend(True), f_htf_trend(False), "F04", "Filter: 15-minute EMA20/50 trend", "filter",
            [YT + " CMB-3", YT + " CMB-8"])
    _mirror(f_above_ema200(True), f_above_ema200(False), "F05", "Filter: beyond EMA200", "filter", [YT + " CMB-5"])
    _mirror(f_st_flip(True), f_st_flip(False), "F06", "Supertrend(10,3) flip, 5-minute", "supertrend",
            [YT + " CMB-5", OT + " supertrend_10_3"])
    _mirror(f_adx15_over_20, f_adx15_over_20, "F07", "Filter: ADX(15m) above 20", "filter", [YT + " CMB-5"])
    _mirror(f_engulf_or_hammer(True), f_engulf_or_hammer(False), "F08", "Engulfing or hammer (shooting star)",
            "pattern", [YT + " CMB-4"])
    _mirror(f_above_vwap(True), f_above_vwap(False), "F09", "Filter: VWAP side", "filter", [YT + " CMB-6"])


# The catalogs' named combinations of more than three conditions, added to the family explicitly
# (amendment 4 §4). Pairs and triples are already in the enumeration.
NAMED_COMBINATIONS = [
    ("CMB-3", "LONG", ["R13", "F02L", "F03L", "F04L"]),
    ("CMB-3", "SHORT", ["R14", "F02S", "F03S", "F04S"]),
]

register_all()
