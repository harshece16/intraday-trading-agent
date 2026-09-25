"""3h — does market breadth or an intermarket move predict the NSE intraday
session? Pre-registered in docs/research/prereg-3h-breadth-intermarket.md
(commit db82c9a) before this file existed. Research look L35, not a trial.

Usage: python research/breadth_intermarket.py      # one run; selection sample only
"""
import bisect
import json
import math
import statistics as st
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[2]
BHAV_DIR = ROOT / "backend/data/bhav"
BREADTH_CSV = ROOT / "backend/research/data/nse_breadth_daily.csv"
OUT = ROOT / "docs/research/breadth_intermarket_result.json"
BHAV_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{}.csv"
FETCH_FROM = date(2024, 6, 1)
ROUND_TRIP_BP = 16.63
YF = {"P4_india_vix_chg_pct": "^INDIAVIX", "P5_sp500_ret_pct": "^GSPC", "P6_usdinr_chg_pct": "INR=X",
      "P7_crude_ret_pct": "CL=F", "P8_us10y_chg_bp": "^TNX"}


# ------------------------------------------------------------- breadth ----

def breadth_from_bhav(text):
    """One bhavcopy -> the day's breadth over series EQ: advances, declines,
    unchanged, up/down volume and the EQ row count."""
    lines = text.splitlines()
    head = [h.strip() for h in lines[0].split(",")]
    ix = {h: i for i, h in enumerate(head)}
    adv = dec = unch = n = 0
    upv = dnv = 0.0
    for ln in lines[1:]:
        p = [x.strip() for x in ln.split(",")]
        if len(p) < len(head) or p[ix["SERIES"]] != "EQ":
            continue
        try:
            prev, close, vol = float(p[ix["PREV_CLOSE"]]), float(p[ix["CLOSE_PRICE"]]), float(p[ix["TTL_TRD_QNTY"]])
        except ValueError:
            continue
        n += 1
        if close > prev:
            adv, upv = adv + 1, upv + vol
        elif close < prev:
            dec, dnv = dec + 1, dnv + vol
        else:
            unch += 1
    return {"adv": adv, "dec": dec, "unch": unch, "up_vol": upv, "down_vol": dnv, "n_eq": n}


def trin(adv, dec, upv, dnv):
    if not dec or not dnv or not upv:
        return None
    return (adv / dec) / (upv / dnv)


def ema(values, n):
    a, out, cur = 2 / (n + 1), [], None
    for v in values:
        cur = v if cur is None else a * v + (1 - a) * cur
        out.append(cur)
    return out


def mcclellan(net_advances):
    """EMA19 - EMA39 of net advances, seeded with the first value."""
    return [f - s for f, s in zip(ema(net_advances, 19), ema(net_advances, 39))]


def fetch_bhav(until):
    """Cache every weekday's bhavcopy from FETCH_FROM to `until`; a 404 is a
    holiday. Returns {iso_date: text}."""
    import requests
    BHAV_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
    out, d = {}, FETCH_FROM
    while d <= until:
        if d.weekday() < 5:
            f = BHAV_DIR / f"{d.isoformat()}.csv"
            miss = BHAV_DIR / f"{d.isoformat()}.404"
            if f.exists():
                out[d.isoformat()] = f.read_text()
            elif not miss.exists():
                for attempt in range(3):
                    try:
                        r = requests.get(BHAV_URL.format(d.strftime("%d%m%Y")), headers=headers, timeout=30)
                        break
                    except requests.RequestException:
                        time.sleep(2 * (attempt + 1))
                else:
                    raise SystemExit(f"bhavcopy {d} unreachable after 3 attempts")
                if r.status_code == 200 and r.text.startswith("SYMBOL"):
                    f.write_text(r.text)
                    out[d.isoformat()] = r.text
                elif r.status_code == 404:
                    miss.write_text("")
                else:
                    raise SystemExit(f"bhavcopy {d}: HTTP {r.status_code}")
                time.sleep(0.3)
        d += timedelta(days=1)
    return out


def breadth_table(bhav):
    rows = []
    for d in sorted(bhav):
        b = breadth_from_bhav(bhav[d])
        rows.append({"date": d, **b, "ratio": b["adv"] / (b["adv"] + b["dec"]) if b["adv"] + b["dec"] else None,
                     "trin": trin(b["adv"], b["dec"], b["up_vol"], b["down_vol"])})
    for r, m in zip(rows, mcclellan([r["adv"] - r["dec"] for r in rows])):
        r["mcclellan"] = m
    return rows


# ---------------------------------------------------------- alignment ----

def last_before(dates, values, d):
    """(value at the last date strictly before d, value at the one before
    that), or None. `dates` sorted ISO strings."""
    i = bisect.bisect_left(dates, d) - 1
    if i < 1:
        return None
    return values[i], values[i - 1]


def yf_predictor(name, dates, closes, d):
    pair = last_before(dates, closes, d)
    if pair is None or pair[1] in (None, 0) or pair[0] is None:
        return None
    cur, prev = pair
    if name == "P8_us10y_chg_bp":
        return (cur - prev) * 100
    return (cur / prev - 1) * 100


# ------------------------------------------------------------- target ----

def intraday_target(bars_by_symbol, session):
    """Equal-weighted mean over stocks of close(09:15 bar) -> close(15:05
    bar), in bp. None when fewer than 50 stocks have both bars."""
    rets = []
    for bars in bars_by_symbol.values():
        a = b = None
        for x in bars:
            if x["time"][:10] != session:
                continue
            hm = x["time"][11:16]
            if hm == "09:15":
                a = x["close"]
            elif hm == "15:05":
                b = x["close"]
        if a and b:
            rets.append((b / a - 1) * 1e4)
    return st.mean(rets) if len(rets) >= 50 else None


# -------------------------------------------------------------- stats ----

def tercile_spread(xs, ys):
    """Sessions split into terciles of x. Returns the spread top-bottom,
    its Welch t and two-sided p, and each tercile's mean and n."""
    pairs = sorted(zip(xs, ys))
    k = len(pairs) // 3
    lo, mid, hi = [y for _, y in pairs[:k]], [y for _, y in pairs[k:len(pairs) - k]], [y for _, y in pairs[len(pairs) - k:]]
    m_lo, m_hi = st.mean(lo), st.mean(hi)
    se = math.sqrt(st.variance(lo) / len(lo) + st.variance(hi) / len(hi))
    t = (m_hi - m_lo) / se if se else 0.0
    p = math.erfc(abs(t) / math.sqrt(2))          # normal approx; n > 100 per tercile
    return {"spread_bp": m_hi - m_lo, "t": t, "p": p,
            "bottom": {"mean_bp": m_lo, "n": len(lo), "x_max": pairs[k - 1][0]},
            "middle": {"mean_bp": st.mean(mid), "n": len(mid)},
            "top": {"mean_bp": m_hi, "n": len(hi), "x_min": pairs[len(pairs) - k][0]}}


def bh(pvals, q=0.05):
    """Benjamini-Hochberg: which of `pvals` (dict) are rejected at q."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, cut = len(items), 0
    for i, (_, p) in enumerate(items, 1):
        if p <= q * i / m:
            cut = i
    return {k for k, _ in items[:cut]}


def tradable(res):
    """Rule 2: the tercile the spread points to must have the right sign and
    at least a round trip in magnitude."""
    if res["spread_bp"] > 0:
        m = res["top"]["mean_bp"]
        return m >= ROUND_TRIP_BP or res["bottom"]["mean_bp"] <= -ROUND_TRIP_BP
    m = res["bottom"]["mean_bp"]
    return m >= ROUND_TRIP_BP or res["top"]["mean_bp"] <= -ROUND_TRIP_BP


# --------------------------------------------------------------- main ----

def main():
    import config
    import kite_history
    import universe
    import yfinance as yf
    from research import splits

    if OUT.exists():
        raise SystemExit("L35 already ran — one run per measurement")
    symbols = [r["symbol"] for r in universe.load()]
    pre = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=730)
    selection, held_out = splits.selection_holdout(splits.sessions_in(pre))
    sel, _ = splits.slice_data(pre, {}, selection)
    del pre
    print(splits.describe_split("selection", selection), f"| held-out {len(held_out)} sessions NOT loaded", flush=True)

    bhav = fetch_bhav(date.fromisoformat(selection[-1]))
    table = breadth_table(bhav)
    BREADTH_CSV.parent.mkdir(parents=True, exist_ok=True)
    cols = ["date", "adv", "dec", "unch", "n_eq", "up_vol", "down_vol", "ratio", "trin", "mcclellan"]
    BREADTH_CSV.write_text("\n".join([",".join(cols)] + [",".join(str(r[c]) for c in cols) for r in table]) + "\n")

    # data gate — hard halt
    bdates = [r["date"] for r in table]
    covered = [s for s in selection if s in set(bdates) and next(r for r in table if r["date"] == s)["n_eq"] >= 1500]
    gate = {"bhav_coverage_pct": 100 * len(covered) / len(selection)}
    if gate["bhav_coverage_pct"] < 95:
        OUT.write_text(json.dumps({"halted": gate}, indent=1))
        raise SystemExit(f"HALT: bhavcopy coverage {gate['bhav_coverage_pct']:.1f}% < 95%")

    yfd = {}
    raw = yf.download(list(YF.values()), start="2024-05-01", end=selection[-1], progress=False, auto_adjust=False)["Close"]
    for name, tick in YF.items():
        s = raw[tick].dropna()
        yfd[name] = ([d.strftime("%Y-%m-%d") for d in s.index], [float(v) for v in s.values])

    target = {s: intraday_target(sel, s) for s in selection}
    bidx = {r["date"]: i for i, r in enumerate(table)}
    rows = []
    for s in selection:
        if target[s] is None:
            continue
        i = bisect.bisect_left(bdates, s) - 1                 # breadth of the last session before s
        prev = table[i] if i >= 0 else None
        row = {"session": s, "target_bp": target[s],
               "P1_breadth_ratio": prev["ratio"] if prev else None,
               "P2_mcclellan": prev["mcclellan"] if prev and i >= 60 else None,
               "P3_trin": prev["trin"] if prev else None}
        for name in YF:
            row[name] = yf_predictor(name, *yfd[name], s)
        rows.append(row)

    preds = ["P1_breadth_ratio", "P2_mcclellan", "P3_trin"] + list(YF)
    results, dropped = {}, {}
    for p in preds:
        pts = [(r[p], r["target_bp"]) for r in rows if r[p] is not None]
        cov = 100 * len(pts) / len(selection)
        if p in YF and cov < 90:
            dropped[p] = cov
            continue
        results[p] = {**tercile_spread([x for x, _ in pts], [y for _, y in pts]), "sessions": len(pts),
                      "coverage_pct": cov}
    rejected = bh({p: r["p"] for p, r in results.items()})
    for p, r in results.items():
        r["bh_survives"] = p in rejected
        r["tradable"] = tradable(r)
        r["pass"] = r["bh_survives"] and r["tradable"]
    tgt = [r["target_bp"] for r in rows]
    out = {"look": "L35", "selection": [selection[0], selection[-1], len(selection)], "gate": gate,
           "dropped_low_coverage": dropped, "target_mean_bp": st.mean(tgt), "target_sd_bp": st.stdev(tgt),
           "target_sessions": len(tgt), "family_size": len(results), "results": results,
           "passes": [p for p, r in results.items() if r["pass"]]}
    OUT.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
