"""
The Nifty overnight premium held in an ETF — stage 0, H1 (trial 124) and H2
(trial 125). Pre-registration: docs/research/prereg-overnight-etf.md.

    .venv/bin/python research/overnight_etf.py stage0    # facts only, no overnight return
    .venv/bin/python research/overnight_etf.py h1        # always hold (NIFTYBEES) + SETFNIF50 confirmation
    .venv/bin/python research/overnight_etf.py h2        # nightly go/no-go ridge, walk-forward

Reads backend/data/overnight_1m.db (Kite 1-minute bars, 2015-2025 only).
Writes docs/research/data/overnight_etf_*.json.
"""

import bisect
import collections
import datetime
import json
import math
import os
import sqlite3
import statistics as st
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

import evaluation  # noqa: E402

DB = os.path.join(BACKEND, "data", "overnight_1m.db")
OUT = os.path.join(BACKEND, "..", "docs", "research", "data")
ENTRY, EXIT = "15:24", "09:19"
N_FAMILY = 2
T_GATE = 2.24
NOTIONAL = 1_000_000.0
SPREAD_BP_PER_SIDE = 2.0
LAST3_START = "2023-01-01"
LIQ_GATE_RS = 5_000_000.0          # ₹50 lakh
COVERAGE_GATE = 0.95
UNIT_TOL = 0.15

# RBI policy repo rate (effective date, % a year); source BankBazaar's RBI history, retrieved 2026-09-27
REPO = [("2014-01-28", 8.00), ("2015-01-15", 7.75), ("2015-03-04", 7.50), ("2015-06-02", 7.25),
        ("2015-09-29", 6.75), ("2016-04-05", 6.50), ("2016-10-04", 6.25), ("2017-08-02", 6.00),
        ("2018-06-06", 6.25), ("2018-08-01", 6.50), ("2019-02-07", 6.25), ("2019-04-04", 6.00),
        ("2019-06-06", 5.75), ("2019-08-07", 5.40), ("2019-10-04", 5.15), ("2020-03-27", 4.40),
        ("2020-05-22", 4.00), ("2022-05-04", 4.40), ("2022-06-08", 4.90), ("2022-08-05", 5.40),
        ("2022-09-30", 5.90), ("2022-12-07", 6.25), ("2023-02-08", 6.50), ("2025-02-07", 6.25),
        ("2025-04-09", 6.00), ("2025-06-06", 5.50), ("2025-12-05", 5.25)]


def repo_on(d):
    k = bisect.bisect_right([x[0] for x in REPO], d) - 1
    return REPO[max(k, 0)][1]


# --- data ------------------------------------------------------------------------------

def load(symbol, minutes=None):
    """{date: {hhmm: (open, high, low, close, volume)}}; optionally only some minutes."""
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    out = collections.defaultdict(dict)
    for ts, o, h, l, cl, v in c.execute("SELECT ts, open, high, low, close, volume FROM bars WHERE symbol=? ORDER BY ts",
                                         (symbol,)):
        d, hm = ts[:10], ts[11:16]
        if minutes is None or hm in minutes:
            out[d][hm] = (o, h, l, cl, v)
    return out


def window(start, end):
    s = datetime.datetime.strptime(start, "%H:%M")
    e = datetime.datetime.strptime(end, "%H:%M")
    out = []
    while s <= e:
        out.append(s.strftime("%H:%M"))
        s += datetime.timedelta(minutes=1)
    return out


ENTRY_WIN, EXIT_WIN = window("15:20", "15:29"), window("09:15", "09:20")
NEEDED = set(ENTRY_WIN) | set(EXIT_WIN)


def calendar():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    return [r[0] for r in c.execute("SELECT DISTINCT substr(ts,1,10) FROM bars WHERE symbol='NIFTY 50' ORDER BY 1")]


def daily_close(bars):
    return {d: m[max(m)][3] for d, m in bars.items() if m}


def unit_breaks(etf, idx):
    """Dates where the ETF/index close ratio leaves ±15% of its 20-day median."""
    ce, ci = daily_close(etf), daily_close(idx)
    days = sorted(set(ce) & set(ci))
    ratios = [(d, ce[d] / ci[d]) for d in days if ci[d] > 0]
    out = []
    for i in range(20, len(ratios)):
        med = st.median(r for _, r in ratios[i - 20:i])
        if abs(ratios[i][1] / med - 1) > UNIT_TOL:
            out.append({"date": ratios[i][0], "ratio_vs_median": round(ratios[i][1] / med, 4)})
    return out


def charges_bp():
    v = NOTIONAL
    txn, sebi, gst = 0.0000307, 0.000001, 0.18
    buy = v * (0.00015 + txn + sebi + gst * (txn + sebi))
    sell = v * (0.00001 + txn + sebi + gst * (txn + sebi)) + 15.34
    return (buy + sell) / v * 1e4


def nights(etf_sym, spread_per_side=SPREAD_BP_PER_SIDE, start="2015-03-01"):
    """Every night d -> next session: gross / net bp (H1's series)."""
    cal = [d for d in calendar() if d >= start]
    etf = load(etf_sym, NEEDED)
    idx = load("NIFTY 50")
    breaks = {b["date"] for b in unit_breaks(load(etf_sym), idx)}
    ch = charges_bp()
    rows, missing = [], 0
    for i in range(len(cal) - 1):
        d, n = cal[i], cal[i + 1]
        if n in breaks:
            continue
        a, b = etf.get(d, {}).get(ENTRY), etf.get(n, {}).get(EXIT)
        if not a or not b:
            missing += 1
            continue
        gross = (b[3] / a[3] - 1) * 1e4
        nights_cal = (datetime.date.fromisoformat(n) - datetime.date.fromisoformat(d)).days
        coc = repo_on(d) / 100 * nights_cal / 365 * 1e4
        rows.append({"d": d, "n": n, "gross": gross, "net": gross - ch - 2 * spread_per_side - coc,
                     "coc": coc, "nights": nights_cal})
    return rows, missing, sorted(breaks)


def tstat(xs):
    if len(xs) < 2:
        return None
    sd = st.stdev(xs)
    return st.mean(xs) / sd * math.sqrt(len(xs)) if sd > 0 else None


def _write(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as fh:
        json.dump(obj, fh, indent=1, default=str)


# --- stage 0 ----------------------------------------------------------------------------------

def stage0():
    cal = [d for d in calendar() if "2015-03-01" <= d <= "2025-12-31"]
    etf = load("NIFTYBEES", NEEDED)
    have = sum(1 for i in range(len(cal) - 1)
               if etf.get(cal[i], {}).get(ENTRY) and etf.get(cal[i + 1], {}).get(EXIT))
    coverage = have / (len(cal) - 1)
    liq = {}
    for sym in ("NIFTYBEES", "SETFNIF50"):
        b = load(sym, NEEDED)
        per_year = collections.defaultdict(lambda: {"entry": [], "exit": []})
        for d, m in b.items():
            per_year[d[:4]]["entry"].append(sum(m[h][4] * m[h][3] for h in ENTRY_WIN if h in m))
            per_year[d[:4]]["exit"].append(sum(m[h][4] * m[h][3] for h in window("09:16", "09:20") if h in m))
        liq[sym] = {y: {"entry_median_rs": st.median(v["entry"]), "exit_median_rs": st.median(v["exit"])}
                    for y, v in sorted(per_year.items())}
    liq_gate = all(v["entry_median_rs"] >= LIQ_GATE_RS and v["exit_median_rs"] >= LIQ_GATE_RS
                   for y, v in liq["NIFTYBEES"].items() if y >= "2020")
    idx_full = load("NIFTY 50")
    breaks = {s: unit_breaks(load(s), idx_full) for s in ("NIFTYBEES", "SETFNIF50")}
    # deviation of the ETF from its index-implied price at the entry and exit minutes
    idx_m = load("NIFTY 50", NEEDED)
    dev = {"entry_bp": [], "exit_bp": []}
    days = sorted(set(etf) & set(idx_m))
    ratios = []
    for d in days:
        e, i_ = etf[d].get(ENTRY), idx_m[d].get(ENTRY)
        if e and i_:
            ratios.append((d, e[3] / i_[3]))
    rmap = dict(ratios)
    for k, d in enumerate(days):
        prior = [r for dd, r in ratios if dd < d][-20:]
        if len(prior) < 20:
            continue
        med = st.median(prior)
        for key, hm in (("entry_bp", ENTRY), ("exit_bp", EXIT)):
            e, i_ = etf[d].get(hm), idx_m[d].get(hm)
            if e and i_:
                dv = (e[3] / i_[3] / med - 1) * 1e4
                if abs(dv) < 1000:          # ignore unit-change days
                    dev[key].append(dv)
    dev_s = {k: {"median_abs_bp": st.median([abs(x) for x in v]), "p90_abs_bp": sorted(abs(x) for x in v)[int(0.9 * len(v))],
                 "n": len(v)} for k, v in dev.items() if v}
    out = {"coverage": coverage, "coverage_gate": coverage >= COVERAGE_GATE, "nights_checked": len(cal) - 1,
           "liquidity": liq, "liquidity_gate": liq_gate, "unit_breaks": breaks, "deviation_from_index": dev_s,
           "charges_bp_round_trip": charges_bp(), "repo_schedule": REPO,
           "PASS": coverage >= COVERAGE_GATE and liq_gate}
    _write("overnight_etf_stage0.json", out)
    print(json.dumps({k: v for k, v in out.items() if k not in ("repo_schedule",)}, indent=1, default=str)[:5000])
    return out


# --- H1 -------------------------------------------------------------------------------------------

def summarise(rows):
    net = [r["net"] for r in rows]
    half = len(net) // 2
    l3 = [r["net"] for r in rows if r["d"] >= LAST3_START]
    return {"nights": len(net), "mean_net_bp": st.mean(net), "t": tstat(net),
            "mean_gross_bp": st.mean(r["gross"] for r in rows), "mean_coc_bp": st.mean(r["coc"] for r in rows),
            "half1": st.mean(net[:half]), "half2": st.mean(net[half:]), "half1_t": tstat(net[:half]), "half2_t": tstat(net[half:]),
            "last3_mean": st.mean(l3) if l3 else None, "last3_t": tstat(l3), "last3_n": len(l3),
            "dsr_family": evaluation.deflated_sharpe_ratio(net, N_FAMILY),
            "by_year": {y: round(st.mean([r["net"] for r in rows if r["d"][:4] == y]), 2)
                        for y in sorted({r["d"][:4] for r in rows})}}


def h1():
    rows, missing, breaks = nights("NIFTYBEES")
    s = summarise(rows)
    sens = {}
    for sp in (1.0, 3.0):
        r2, _, _ = nights("NIFTYBEES", spread_per_side=sp)
        sens[f"spread_{sp:g}bp_per_side"] = {"mean_net_bp": st.mean(r["net"] for r in r2), "t": tstat([r["net"] for r in r2])}
    conf_rows, conf_missing, _ = nights("SETFNIF50", start="2015-08-01")
    c = summarise(conf_rows)
    rule = {"t_ge_2_24": (s["t"] or 0) >= T_GATE and s["mean_net_bp"] > 0,
            "dsr_family_ge_0_95": (s["dsr_family"].get("dsr") or 0) >= 0.95,
            "both_halves_positive": s["half1"] > 0 and s["half2"] > 0,
            "last3_positive": (s["last3_mean"] or 0) > 0, "nights_ge_500": s["nights"] >= 500}
    confirm = {"t_ge_1_65": (c["t"] or 0) >= 1.65 and c["mean_net_bp"] > 0}
    out = {"prereg": "prereg-overnight-etf.md", "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "niftybees": s, "missing_nights": missing, "unit_break_nights_excluded": breaks, "sensitivity": sens,
           "setfnif50": c, "setfnif50_missing": conf_missing, "pass_rule": rule, "PASS": all(rule.values()),
           "confirm_rule": confirm, "CONFIRMS": all(confirm.values()),
           "series": [{"d": r["d"], "net": r["net"], "gross": r["gross"]} for r in rows]}
    _write("overnight_etf_h1.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "series"}, indent=1, default=str)[:6000])
    return out


# --- H2 -------------------------------------------------------------------------------------------

def features():
    idx = load("NIFTY 50")
    vix = load("INDIA VIX", {ENTRY})
    cal = calendar()
    feats = {}
    vix_hist = []
    for k, d in enumerate(cal):
        m = idx.get(d, {})
        if "09:15" not in m or ENTRY not in m:
            vix_hist.append(None)
            continue
        closes = [m[h][3] for h in sorted(m) if h <= ENTRY]
        day_ret = m[ENTRY][3] / m["09:15"][0] - 1
        lr = [math.log(closes[j] / closes[j - 1]) for j in range(1, len(closes)) if closes[j - 1] > 0]
        rv = math.sqrt(sum(x * x for x in lr))
        v = vix.get(d, {}).get(ENTRY)
        v_now = v[3] if v else None
        prior = [x for x in vix_hist[-20:] if x is not None]
        vix_dev = (v_now - st.mean(prior)) if (v_now is not None and len(prior) >= 10) else None
        vix_hist.append(v_now)
        prev_night = None
        if k > 0:
            pm = idx.get(cal[k - 1], {})
            if ENTRY in pm and EXIT in m:
                prev_night = m[EXIT][3] / pm[ENTRY][3] - 1
        nxt = cal[k + 1] if k + 1 < len(cal) else None
        n_cal = (datetime.date.fromisoformat(nxt) - datetime.date.fromisoformat(d)).days if nxt else None
        if None in (vix_dev, prev_night, n_cal):
            continue
        feats[d] = [day_ret, vix_dev, rv, float(n_cal), prev_night]
    return feats


def h2():
    rows, _, _ = nights("NIFTYBEES")
    y = {r["d"]: r["net"] for r in rows}
    fx = features()
    days = sorted(d for d in y if d in fx)
    years = sorted({d[:4] for d in days})
    held, always, test_days = [], [], []
    weights = {}
    for Y in years:
        if Y < "2017":
            continue
        train = [d for d in days if d[:4] < Y]
        test = [d for d in days if d[:4] == Y]
        if len({d[:4] for d in train}) < 2 or not test:
            continue
        X = np.array([fx[d] for d in train])
        mu, sd = X.mean(axis=0), X.std(axis=0)
        sd[sd == 0] = 1.0
        Z = (X - mu) / sd
        t = np.array([y[d] for d in train])
        lam = 0.1 * len(t)
        A = np.hstack([np.ones((len(t), 1)), Z])
        reg = lam * np.eye(A.shape[1])
        reg[0, 0] = 0.0                      # the intercept (the unconditional premium) is not penalised
        w = np.linalg.solve(A.T @ A + reg, A.T @ t)
        weights[Y] = w.tolist()
        for d in test:
            z = (np.array(fx[d]) - mu) / sd
            pred = float(w[0] + z @ w[1:])
            hold = pred > 1.0
            held.append(y[d] if hold else 0.0)
            always.append(y[d])
            test_days.append((d, hold, pred))
    diff = [a - b for a, b in zip(held, always)]
    half = len(diff) // 2
    rule = {"gated_t_ge_2_24": (tstat(held) or 0) >= T_GATE and st.mean(held) > 0,
            "paired_t_ge_2_24": (tstat(diff) or 0) >= T_GATE and st.mean(diff) > 0,
            "paired_both_halves_positive": st.mean(diff[:half]) > 0 and st.mean(diff[half:]) > 0}
    out = {"prereg": "prereg-overnight-etf.md", "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "test_nights": len(held), "held_share": sum(1 for _, h, _ in test_days if h) / len(test_days),
           "gated_mean_bp": st.mean(held), "gated_t": tstat(held),
           "always_mean_bp": st.mean(always), "always_t": tstat(always),
           "paired_mean_bp": st.mean(diff), "paired_t": tstat(diff),
           "paired_halves": [st.mean(diff[:half]), st.mean(diff[half:])],
           "features": ["day_return_to_1524", "vix_minus_20d_mean", "intraday_realised_vol", "calendar_nights", "previous_night_return"],
           "weights_by_year": weights, "pass_rule": rule, "PASS": all(rule.values())}
    _write("overnight_etf_h2.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "weights_by_year"}, indent=1, default=str))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stage0"
    {"stage0": stage0, "h1": h1, "h2": h2}[cmd]()
