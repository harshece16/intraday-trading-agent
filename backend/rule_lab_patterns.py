"""
Cohort 4 of the rule lab ("cohort 2b" on the page): the basic candlestick,
indicator and chart-pattern rules the lab lacked, fixed in
docs/research/prereg-rule-lab.md amendment 7 before any of them was computed
on data.

- The 16 directional candlestick patterns of candlestick_patterns.PATTERN_NAMES
  that cohort 1 did not trade, each through the engine's own detector; the two
  neutral patterns (Doji, Inside Bar) as both-side breakouts of the pattern bar.
- Standalone indicator rules: ADX(14) with a DI cross, a Fibonacci retracement
  of the day's range, Ichimoku, Keltner breakout and mean reversion, parabolic
  SAR, Donchian 20, VWAP sigma bands (bounce and fade), the VWAP cross, OBV
  divergence, and two time-of-day filters.
- Two chart patterns with exact 5-minute definitions: double top/bottom and
  bull/bear flag, on swings confirmed two bars later so nothing looks ahead.

Every rule trades the common exits (H30; the flags R3 with the stop beyond the
signal bar). Every series is causal: a value at bar k reads bars 0..k only.
tests/test_rule_lab.py checks that by truncation for every rule.

Imported by rule_lab at the end of its module; registers into its REGISTRY.
"""
import candlestick_patterns
import indicators
import market_structure

import rule_lab
from rule_lab import _bar, _patterns, register
from rule_lab_catalog import _cached, _closes, _minute, ema

COHORT = 4
COHORT_LABEL = "2b"

ADX_MIN = 25.0
FIB_MIN_RANGE = 0.005
KELTNER_MULT, KELTNER_ATR = 2.0, 10
SAR_AF, SAR_STEP, SAR_MAX = 0.02, 0.02, 0.20
DONCHIAN = 20
OBV_LOOKBACK = 20
DT_TOL, DT_MIN_GAP, DT_MAX_GAP = 0.002, 10, 40
FLAG_IMPULSE, FLAG_RETRACE, FLAG_MIN, FLAG_MAX, POLE_BARS = 0.01, 0.4, 2, 8, 12


# ---- causal series over the input ---------------------------------------------------

def adx_series(bars, period=14):
    """Wilder's ADX with +DI/-DI at every bar, equal to indicators.adx(bars[:k+1], period) at k
    (None before it has a value). Returns (adx, plus_di, minus_di)."""
    n = len(bars)
    adx = [None] * n
    pdi_s = [None] * n
    mdi_s = [None] * n
    if n < period * 2 + 1:
        return adx, pdi_s, mdi_s
    trs, pdm, mdm = [], [], []
    for i in range(1, n):
        h, l = bars[i]["high"], bars[i]["low"]
        ph, pl, pc = bars[i - 1]["high"], bars[i - 1]["low"], bars[i - 1]["close"]
        up, down = h - ph, pl - l
        pdm.append(up if up > down and up > 0 else 0.0)
        mdm.append(down if down > up and down > 0 else 0.0)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    tr_s, p_s, m_s = sum(trs[:period]), sum(pdm[:period]), sum(mdm[:period])
    dxs = []
    adx_v = None
    for i in range(period - 1, len(trs)):
        if i >= period:
            tr_s = tr_s - tr_s / period + trs[i]
            p_s = p_s - p_s / period + pdm[i]
            m_s = m_s - m_s / period + mdm[i]
        pdi = 100 * p_s / tr_s if tr_s else 0.0
        mdi = 100 * m_s / tr_s if tr_s else 0.0
        dxs.append(100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0.0)
        if len(dxs) == period:
            adx_v = sum(dxs) / period
        elif len(dxs) > period:
            adx_v = (adx_v * (period - 1) + dxs[-1]) / period
        k = i + 1                      # the bar this reading belongs to
        if adx_v is not None and k >= period * 2:   # indicators.adx needs 2 x period + 1 bars
            adx[k], pdi_s[k], mdi_s[k] = adx_v, pdi, mdi
    return adx, pdi_s, mdi_s


def adx(ctx):
    return _cached(ctx, "adx14", lambda: adx_series(ctx["bars"], 14))


def _rolling_extremes(bars, n):
    """(highest high, lowest low) of bars k-n+1..k at each k; None before n bars."""
    hh, ll = [None] * len(bars), [None] * len(bars)
    for k in range(n - 1, len(bars)):
        w = bars[k - n + 1:k + 1]
        hh[k] = max(b["high"] for b in w)
        ll[k] = min(b["low"] for b in w)
    return hh, ll


def extremes(ctx, n):
    return _cached(ctx, ("hhll", n), lambda: _rolling_extremes(ctx["bars"], n))


def ichimoku(ctx):
    """(tenkan, kijun, senkou A at k, senkou B at k): the cloud at k is the span computed 26 bars back."""
    def f():
        bars = ctx["bars"]
        n = len(bars)
        h9, l9 = extremes(ctx, 9)
        h26, l26 = extremes(ctx, 26)
        h52, l52 = extremes(ctx, 52)
        tk = [None if h9[k] is None else (h9[k] + l9[k]) / 2 for k in range(n)]
        kj = [None if h26[k] is None else (h26[k] + l26[k]) / 2 for k in range(n)]
        sa, sb = [None] * n, [None] * n
        for k in range(26, n):
            j = k - 26
            if tk[j] is not None and kj[j] is not None:
                sa[k] = (tk[j] + kj[j]) / 2
            if h52[j] is not None:
                sb[k] = (h52[j] + l52[j]) / 2
        return tk, kj, sa, sb
    return _cached(ctx, "ichimoku", f)


def _atr_mean_series(bars, n):
    """indicators.atr(bars[:k+1], n) at each k."""
    out = [None] * len(bars)
    tr = [None] + [max(bars[i]["high"] - bars[i]["low"], abs(bars[i]["high"] - bars[i - 1]["close"]),
                       abs(bars[i]["low"] - bars[i - 1]["close"])) for i in range(1, len(bars))]
    s = 0.0
    for k in range(1, len(bars)):
        s += tr[k]
        if k > n:
            s -= tr[k - n]
        if k >= n:
            out[k] = s / n
    return out


def keltner(ctx):
    """(upper, lower): EMA20 +/- 2 x ATR10."""
    def f():
        e = ema(ctx, 20)
        a = _atr_mean_series(ctx["bars"], KELTNER_ATR)
        up = [None if x is None or y is None else x + KELTNER_MULT * y for x, y in zip(e, a)]
        lo = [None if x is None or y is None else x - KELTNER_MULT * y for x, y in zip(e, a)]
        return up, lo
    return _cached(ctx, "keltner", f)


def psar_direction(bars, af0=SAR_AF, step=SAR_STEP, cap=SAR_MAX):
    """Wilder's parabolic SAR direction (+1/-1) after each bar; None at the first bar."""
    n = len(bars)
    d = [None] * n
    if n < 2:
        return d
    up = bars[1]["close"] >= bars[0]["close"]
    sar = bars[0]["low"] if up else bars[0]["high"]
    ep = bars[1]["high"] if up else bars[1]["low"]
    af = af0
    d[1] = 1 if up else -1
    for k in range(2, n):
        b = bars[k]
        sar = sar + af * (ep - sar)
        if up:
            sar = min(sar, bars[k - 1]["low"], bars[k - 2]["low"])
            if b["low"] <= sar:
                up, sar, ep, af = False, ep, b["low"], af0
            elif b["high"] > ep:
                ep, af = b["high"], min(cap, af + step)
        else:
            sar = max(sar, bars[k - 1]["high"], bars[k - 2]["high"])
            if b["high"] >= sar:
                up, sar, ep, af = True, ep, b["high"], af0
            elif b["low"] < ep:
                ep, af = b["low"], min(cap, af + step)
        d[k] = 1 if up else -1
    return d


def psar(ctx):
    return _cached(ctx, "psar", lambda: psar_direction(ctx["bars"]))


def obv(ctx):
    return _cached(ctx, "obv", lambda: indicators.obv_series(ctx["bars"]))


def vwap_sd(ctx):
    """SD(i) for each of today's bars: the volume-weighted standard deviation of typical price
    about the session VWAP through that bar."""
    def f():
        out, pv, pv2, vol = {}, 0.0, 0.0, 0.0
        for k in ctx["today"]:
            c = ctx["bars"][k]
            tp = (c["high"] + c["low"] + c["close"]) / 3
            pv += tp * c["volume"]
            pv2 += tp * tp * c["volume"]
            vol += c["volume"]
            if vol > 0:
                m = pv / vol
                out[k] = max(0.0, pv2 / vol - m * m) ** 0.5
        return out
    return _cached(ctx, "vwapsd", f)


def swings(ctx, upto_pos):
    """Today's swing highs and lows (as (pos, price)) confirmed by today's bar `upto_pos`:
    market_structure.swing_points(left=2, right=2) on T[0..upto_pos]. Cached per bar."""
    def f():
        bars = [_bar(ctx, j) for j in range(upto_pos + 1)]
        return market_structure.swing_points(bars, left=2, right=2)
    return _cached(ctx, ("swings", upto_pos), f)


def day_range(ctx, pos):
    """(DH, DL, aH, aL) over T[0..pos-1], or None."""
    if pos < 1:
        return None
    hi = lo = None
    ah = al = None
    for j in range(pos):
        b = _bar(ctx, j)
        if hi is None or b["high"] > hi:
            hi, ah = b["high"], j
        if lo is None or b["low"] < lo:
            lo, al = b["low"], j
    return hi, lo, ah, al


# ---- candlestick patterns (P01-P18) -----------------------------------------------------

DIRECTIONAL = [
    ("P01", "Hanging Man", "SHORT"), ("P02", "Inverted Hammer", "LONG"),
    ("P03", "Piercing Line", "LONG"), ("P04", "Dark Cloud Cover", "SHORT"),
    ("P05", "Bullish Harami", "LONG"), ("P06", "Bearish Harami", "SHORT"),
    ("P07", "Tweezer Bottom", "LONG"), ("P08", "Tweezer Top", "SHORT"),
    ("P09", "Morning Star", "LONG"), ("P10", "Evening Star", "SHORT"),
    ("P11", "Three White Soldiers", "LONG"), ("P12", "Three Black Crows", "SHORT"),
    ("P13", "Abandoned Baby Bottom", "LONG"), ("P14", "Abandoned Baby Top", "SHORT"),
    ("P15", "Rising Three Methods", "LONG"), ("P16", "Falling Three Methods", "SHORT"),
]
COHORT1_PATTERNS = {"Bullish Engulfing", "Bearish Engulfing", "Hammer", "Shooting Star",
                    "Bullish Marubozu", "Bearish Marubozu"}


def pattern(name):
    def sig(ctx, pos, cache):
        return name in _patterns(ctx, ctx["today"][pos], cache)
    return sig


def pattern_bar_break(name, up):
    """The neutral pattern on the previous bar, this bar closing beyond that bar's extreme."""
    def sig(ctx, pos, cache):
        if pos < 1 or name not in _patterns(ctx, ctx["today"][pos - 1], cache):
            return False
        p, c = _bar(ctx, pos - 1), _bar(ctx, pos)
        return c["close"] > p["high"] if up else c["close"] < p["low"]
    return sig


# ---- indicator rules (I01-I11) -----------------------------------------------------------

def adx_cross(long):
    def sig(ctx, pos, cache):
        k = ctx["today"][pos]
        a, p, m = adx(ctx)
        if k < 1 or None in (a[k], p[k], m[k], p[k - 1], m[k - 1]) or a[k] <= ADX_MIN:
            return False
        if long:
            return p[k] > m[k] and p[k - 1] <= m[k - 1]
        return m[k] > p[k] and m[k - 1] <= p[k - 1]
    return sig


def fib_retrace(long):
    def sig(ctx, pos, cache):
        if pos < 6:
            return False
        dh, dl, ah, al = day_range(ctx, pos)
        if dl <= 0 or dh / dl - 1 < FIB_MIN_RANGE:
            return False
        c = _bar(ctx, pos)
        rng = dh - dl
        if long:
            f38, f62 = dh - 0.382 * rng, dh - 0.618 * rng
            return al < ah and f62 <= c["low"] <= f38 and c["close"] > f38 and c["close"] > c["open"]
        f38, f62 = dl + 0.382 * rng, dl + 0.618 * rng
        return ah < al and f38 <= c["high"] <= f62 and c["close"] < f38 and c["close"] < c["open"]
    return sig


def ichimoku_cross(long):
    def sig(ctx, pos, cache):
        k = ctx["today"][pos]
        tk, kj, sa, sb = ichimoku(ctx)
        if k < 1 or None in (tk[k], kj[k], tk[k - 1], kj[k - 1], sa[k], sb[k]):
            return False
        c = ctx["bars"][k]["close"]
        if long:
            return tk[k] > kj[k] and tk[k - 1] <= kj[k - 1] and c > max(sa[k], sb[k])
        return tk[k] < kj[k] and tk[k - 1] >= kj[k - 1] and c < min(sa[k], sb[k])
    return sig


def keltner_break(long):
    def sig(ctx, pos, cache):
        k = ctx["today"][pos]
        up, lo = keltner(ctx)
        band = up if long else lo
        if k < 1 or band[k] is None or band[k - 1] is None:
            return False
        c, p = ctx["bars"][k]["close"], ctx["bars"][k - 1]["close"]
        return (c > band[k] and p <= band[k - 1]) if long else (c < band[k] and p >= band[k - 1])
    return sig


def keltner_revert(long):
    def sig(ctx, pos, cache):
        k = ctx["today"][pos]
        up, lo = keltner(ctx)
        band = lo if long else up
        if k < 1 or band[k] is None or band[k - 1] is None:
            return False
        c, p = ctx["bars"][k]["close"], ctx["bars"][k - 1]["close"]
        return (p < band[k - 1] and c >= band[k]) if long else (p > band[k - 1] and c <= band[k])
    return sig


def sar_flip(long):
    def sig(ctx, pos, cache):
        k = ctx["today"][pos]
        d = psar(ctx)
        if k < 1 or d[k] is None or d[k - 1] is None:
            return False
        want = 1 if long else -1
        return d[k] == want and d[k - 1] == -want
    return sig


def donchian(long):
    def sig(ctx, pos, cache):
        k = ctx["today"][pos]
        hh, ll = extremes(ctx, DONCHIAN)
        if k < 1 or hh[k - 1] is None:
            return False
        c = ctx["bars"][k]["close"]
        return c > hh[k - 1] if long else c < ll[k - 1]
    return sig


def vwap_band_bounce(long):
    def sig(ctx, pos, cache):
        if pos < 6:
            return False
        k = ctx["today"][pos]
        v, sd = ctx["vwap"].get(k), vwap_sd(ctx).get(k)
        if v is None or not sd:
            return False
        c = _bar(ctx, pos)
        if long:
            band = v - sd
            return c["low"] <= band < c["close"] and c["close"] > c["open"]
        band = v + sd
        return c["high"] >= band > c["close"] and c["close"] < c["open"]
    return sig


def vwap_band_fade(long):
    def sig(ctx, pos, cache):
        if pos < 6:
            return False
        k = ctx["today"][pos]
        v, sd = ctx["vwap"].get(k), vwap_sd(ctx).get(k)
        if v is None or not sd:
            return False
        c = _bar(ctx, pos)["close"]
        return c < v - 2 * sd if long else c > v + 2 * sd
    return sig


def vwap_cross(long):
    def sig(ctx, pos, cache):
        if pos < 1:
            return False
        k, kp = ctx["today"][pos], ctx["today"][pos - 1]
        v, vp = ctx["vwap"].get(k), ctx["vwap"].get(kp)
        if v is None or vp is None:
            return False
        c, p = ctx["bars"][k]["close"], ctx["bars"][kp]["close"]
        return (c > v and p <= vp) if long else (c < v and p >= vp)
    return sig


def obv_divergence(long):
    def sig(ctx, pos, cache):
        k = ctx["today"][pos]
        if k < OBV_LOOKBACK:
            return False
        closes, o = _closes(ctx), obv(ctx)
        # indicators.obv_divergence(bars, 20) reads closes[-1] - closes[-20]: the bar 19 back
        back = OBV_LOOKBACK - 1
        price_chg = closes[k] - closes[k - back]
        obv_chg = o[k] - o[k - back]
        return (price_chg < 0 and obv_chg > 0) if long else (price_chg > 0 and obv_chg < 0)
    return sig


def f_first_30(ctx, pos, cache):
    """Filter: the signal bar starts before 09:45 (bars 09:15 to 09:40)."""
    return _minute(ctx, pos) < 9 * 60 + 45


def f_last_hour(ctx, pos, cache):
    """Filter: the signal bar starts at or after 13:30 (the last hour of lab entries)."""
    return _minute(ctx, pos) >= 13 * 60 + 30


# ---- chart patterns (C01, C02) -------------------------------------------------------------

def double_top_bottom(long):
    """Two swing highs (lows) within 0.2%, 10 to 40 bars apart, both confirmed by this bar, the
    tops (bottoms) the extreme of the span to this bar; the first close beyond the neckline."""
    def sig(ctx, pos, cache):
        if pos < DT_MIN_GAP + 2:
            return False
        highs, lows = swings(ctx, pos)
        pts = lows if long else highs
        if len(pts) < 2:
            return False
        j2, p2 = pts[-1]
        candidates = [(j1, p1) for j1, p1 in pts[:-1]
                      if DT_MIN_GAP <= j2 - j1 <= DT_MAX_GAP and abs(p2 - p1) <= DT_TOL * p1]
        if not candidates:
            return False
        j1, p1 = candidates[-1]
        span = [_bar(ctx, j) for j in range(j1, pos + 1)]
        between = [_bar(ctx, j) for j in range(j1, j2 + 1)]
        after = [_bar(ctx, j) for j in range(j2 + 1, pos)]
        c = _bar(ctx, pos)["close"]
        if long:
            if min(b["low"] for b in span) < min(p1, p2):
                return False
            nl = max(b["high"] for b in between)
            return c > nl and all(b["close"] <= nl for b in after)
        if max(b["high"] for b in span) > max(p1, p2):
            return False
        nl = min(b["low"] for b in between)
        return c < nl and all(b["close"] >= nl for b in after)
    return sig


def flag(long):
    """A pole of at least 1% in at most 12 bars to a swing extreme p (confirmed by T[i-1]), a flag of
    2 to 8 bars holding above 40% retracement without a close beyond the pole, then a close beyond it."""
    def sig(ctx, pos, cache):
        if pos < 5:
            return False
        c = _bar(ctx, pos)["close"]
        highs, lows = swings(ctx, pos - 1)
        pts = highs if long else lows
        for p, extreme in reversed(pts):
            n_flag = pos - 1 - p
            if n_flag > FLAG_MAX:
                break
            if n_flag < FLAG_MIN or p < 2:
                continue
            pole = [_bar(ctx, j) for j in range(max(0, p - POLE_BARS + 1), p + 1)]
            fl = [_bar(ctx, j) for j in range(p + 1, pos)]
            if long:
                pl = min(b["low"] for b in pole)
                if pl <= 0 or extreme / pl - 1 < FLAG_IMPULSE:
                    continue
                floor_ = extreme - FLAG_RETRACE * (extreme - pl)
                if all(b["low"] >= floor_ and b["close"] <= extreme for b in fl) and c > extreme:
                    return True
            else:
                ph = max(b["high"] for b in pole)
                if extreme <= 0 or ph / extreme - 1 < FLAG_IMPULSE:
                    continue
                ceil_ = extreme + FLAG_RETRACE * (ph - extreme)
                if all(b["high"] <= ceil_ and b["close"] >= extreme for b in fl) and c < extreme:
                    return True
        return False
    return sig


# ---- registration ------------------------------------------------------------------------

def _reg(rid, name, side, family, fn, exit_kind="fixed", note=None):
    register(rid, name, side, family, fn, exit_kind=exit_kind, cohort=COHORT)
    rule_lab.REGISTRY[rid]["sources"] = ["prereg-rule-lab.md amendment 7"]
    rule_lab.REGISTRY[rid]["label"] = COHORT_LABEL
    if note:
        rule_lab.REGISTRY[rid]["prior"] = note


def _mirror(rid, name, family, fn_long, fn_short, exit_kind="fixed", note=None):
    _reg(rid + "L", name + ", long", "LONG", family, fn_long, exit_kind, note)
    _reg(rid + "S", name + ", short", "SHORT", family, fn_short, exit_kind, note)


R4 = "candlestick patterns as a family: control R4 of trials 128-202, +0.2 bp gross, -16.4 bp net"


def register_all():
    names = set(candlestick_patterns.PATTERN_NAMES)
    for rid, name, side in DIRECTIONAL:
        assert name in names, name
        _reg(rid, name, side, "pattern", pattern(name), note=R4)
    _mirror("P17", "Doji breakout", "pattern", pattern_bar_break("Doji", True), pattern_bar_break("Doji", False))
    _mirror("P18", "Inside bar (detector) breakout", "pattern", pattern_bar_break("Inside Bar", True),
            pattern_bar_break("Inside Bar", False), note="R07/R08 are cohort 1")
    _mirror("I01", "ADX(14) > 25 with a DI cross", "trend", adx_cross(True), adx_cross(False),
            note="ADX(15m) > 20 only as filter F07 and inside Y14")
    _mirror("I02", "Fibonacci 38.2-61.8% retracement of the day's range, reversal bar", "price",
            fib_retrace(True), fib_retrace(False), note="only Fibonacci pivots of the previous day (Y06, Y14, Y26)")
    _mirror("I03", "Ichimoku tenkan/kijun cross beyond the cloud", "trend", ichimoku_cross(True), ichimoku_cross(False))
    _mirror("I04", "Keltner channel breakout", "volatility", keltner_break(True), keltner_break(False),
            note="Keltner only inside O09's squeeze")
    _mirror("I05", "Keltner channel mean reversion", "volatility", keltner_revert(True), keltner_revert(False))
    _mirror("I06", "Parabolic SAR flip", "trend", sar_flip(True), sar_flip(False))
    _mirror("I07", "Donchian 20-bar breakout", "range", donchian(True), donchian(False),
            note="the opposite trade is Y22/O03 (false breaks)")
    _mirror("I08", "VWAP 1-sigma band bounce", "vwap", vwap_band_bounce(True), vwap_band_bounce(False),
            note="VWAP: trials 93-116, L49, Y05, F09")
    _mirror("I09", "VWAP 2-sigma band fade", "vwap", vwap_band_fade(True), vwap_band_fade(False),
            note="VWAP: trials 93-116, L49, Y05, F09")
    _mirror("I10", "VWAP cross (the session's anchored VWAP)", "vwap", vwap_cross(True), vwap_cross(False),
            note="VWAP: trials 93-116, L49, Y05, F09")
    _mirror("I11", "OBV divergence over 20 bars", "volume", obv_divergence(True), obv_divergence(False),
            note="a factor of the confluence engine, trial 40")
    _mirror("F10", "Filter: the first 30 minutes", "filter", f_first_30, f_first_30, note="L49")
    _mirror("F11", "Filter: the last hour of entries (from 13:30)", "filter", f_last_hour, f_last_hour, note="L49")
    _mirror("C01", "Double bottom (long) / double top (short), neckline break", "chart",
            double_top_bottom(True), double_top_bottom(False), note="double tops: the swing book, daily bars only")
    _mirror("C02", "Bull (long) / bear (short) flag breakout, stop beyond the bar, 3R", "chart",
            flag(True), flag(False), exit_kind="r")


register_all()
