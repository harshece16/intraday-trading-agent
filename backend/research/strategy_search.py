"""The bounded strategy search, pre-registered in
docs/research/prereg-strategy-search.md and committed with this script
before it runs. 76 configurations on the SELECTION sample only (trials
41-116); the held-out window is loaded only if a configuration passes all
four selection rules, and then only for the single best one (trial 117).

Usage:  python research/strategy_search.py            # the grid, then held-out if anything passes
Results are written after every configuration, so an interrupted run
resumes by skipping configurations already finished rather than re-running
them; any such resume is disclosed in the results file.
"""
import json
import math
import statistics as st
import sys
import time
from datetime import datetime, timedelta
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backtester
import config
import evaluation
import indicators
import kite_history
import universe
from research import splits
from strategy_engine import STRATEGY_FUNCTIONS

OUT = Path(__file__).resolve().parents[2] / "docs/research/strategy_search_result.json"
DAYS = 730
N_TRIALS = 116                     # 40 before this search + 76 configurations
ENTRY_FROM, ENTRY_TO = "09:45", "14:30"
LAST_BAR_END = "15:10"             # every session ends on a bar that closes here (>= 15:08 square-off)


# ---------------------------------------------------------------- bars ----

def _parse(t):
    return datetime.fromisoformat(t)


def aggregate(bars5, minutes):
    """5-minute bars (start-labelled) -> `minutes` bars labelled by their END
    time, one session at a time. Only 5m bars starting at or before 15:05 are
    used, so each session's last bar is a partial bar ending at 15:10 and the
    15:08 square-off fires at its close. A start-labelled 15m/60m bar never
    reaches 15:08 and would carry positions overnight."""
    if minutes == 5:
        return bars5
    out, cur, cur_end = [], None, None
    for b in bars5:
        t = _parse(b["time"])
        if t.strftime("%H:%M") > "15:05":
            continue
        open_t = t.replace(hour=9, minute=15, second=0, microsecond=0)
        k = int((t - open_t).total_seconds() // (minutes * 60))
        end = open_t + timedelta(minutes=minutes * (k + 1))
        last_end = t.replace(hour=15, minute=10, second=0, microsecond=0)
        if end > last_end:
            end = last_end
        if cur is not None and end != cur_end:
            out.append(cur)
            cur = None
        if cur is None:
            cur = {"time": end.isoformat(), "open": b["open"], "high": b["high"], "low": b["low"],
                   "close": b["close"], "volume": b.get("volume") or 0}
            cur_end = end
        else:
            cur["high"] = max(cur["high"], b["high"])
            cur["low"] = min(cur["low"], b["low"])
            cur["close"] = b["close"]
            cur["volume"] += b.get("volume") or 0
    if cur is not None:
        out.append(cur)
    return out


# ------------------------------------------------------ indicator series ----
# Series versions of indicators.py's formulas, computed once per symbol and
# timeframe; test_strategy_search.py proves they equal indicators.py's value
# at every bar they are checked on.

def rsi_series(closes, period=14):
    out = [None] * len(closes)
    if len(closes) < period + 1:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        ch = closes[i] - closes[i - 1]
        gains += max(ch, 0.0)
        losses += max(-ch, 0.0)
    ag, al = gains / period, losses / period
    out[period] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(period + 1, len(closes)):
        ch = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(ch, 0.0)) / period
        al = (al * (period - 1) + max(-ch, 0.0)) / period
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def adx_series(c, period=14):
    n = len(c)
    out = [None] * n
    if n < period * 2 + 1:
        return out
    trs, pdm, mdm = [], [], []
    for i in range(1, n):
        h, l = c[i]["high"], c[i]["low"]
        ph, pl, pc = c[i - 1]["high"], c[i - 1]["low"], c[i - 1]["close"]
        up, down = h - ph, pl - l
        pdm.append(up if up > down and up > 0 else 0.0)
        mdm.append(down if down > up and down > 0 else 0.0)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    tr_s, p_s, m_s = sum(trs[:period]), sum(pdm[:period]), sum(mdm[:period])
    dxs = []
    for j in range(period - 1, len(trs)):
        if j >= period:
            tr_s = tr_s - tr_s / period + trs[j]
            p_s = p_s - p_s / period + pdm[j]
            m_s = m_s - m_s / period + mdm[j]
        pdi = 100 * p_s / tr_s if tr_s else 0.0
        mdi = 100 * m_s / tr_s if tr_s else 0.0
        dxs.append(100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0.0)
    # indicators.adx(c[:i+1]) uses dxs[0 .. i-period]; it needs i >= 2*period.
    adx_v = None
    for i in range(2 * period, n):
        k = i - period          # index of the last dx for window c[:i+1]
        if adx_v is None:
            adx_v = sum(dxs[:period]) / period
            for dx in dxs[period:k + 1]:
                adx_v = (adx_v * (period - 1) + dx) / period
        else:
            adx_v = (adx_v * (period - 1) + dxs[k]) / period
        out[i] = adx_v
    return out


def vwap_series(c):
    out, day, pv, vol = [], None, 0.0, 0.0
    for b in c:
        d = b["time"][:10]
        if d != day:
            day, pv, vol = d, 0.0, 0.0
        pv += (b["high"] + b["low"] + b["close"]) / 3 * b["volume"]
        vol += b["volume"]
        out.append(pv / vol if vol > 0 else None)
    return out


def atr_series(c, period=14):
    out = [None] * len(c)
    for i in range(period, len(c)):
        trs = []
        for k in range(i - period + 1, i + 1):
            h, l, pc = c[k]["high"], c[k]["low"], c[k - 1]["close"]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        out[i] = sum(trs) / period
    return out


def features(c):
    closes = [b["close"] for b in c]
    vols = [b["volume"] for b in c]
    vmean = [None] * len(c)
    run = 0.0
    for i, v in enumerate(vols):
        if i >= 20:
            vmean[i] = run / 20
            run -= vols[i - 20]
        run += v
    return {"ema20": indicators.ema_series(closes, 20), "ema50": indicators.ema_series(closes, 50),
            "rsi": rsi_series(closes), "adx": adx_series(c), "vwap": vwap_series(c),
            "atr": atr_series(c), "vmean20": vmean}


# ------------------------------------------------------------ families ----

def _entry_ok(bar):
    hhmm = bar["time"][11:16]
    return ENTRY_FROM <= hhmm <= ENTRY_TO


def make_family(family, side, feats_by_first):
    """A strategy_fn for run_backtest(). Features are looked up by the
    identity of the symbol's first candle (window slices share candle
    objects) and the bar index; nothing past the current bar is read."""
    def fn(window, prev_state=None, **params):
        f = feats_by_first.get(id(window[0]))
        i = len(window) - 1
        bar = window[-1]
        state = dict(prev_state or {})
        day = bar["time"][:10]
        if state.get("day") != day:
            state = {"day": day, "entered": False}
        if f is None or i < 51:
            return None, state
        e20, e50, rsi, adx, vwap, atr, vm = (f["ema20"][i], f["ema50"][i], f["rsi"][i], f["adx"][i],
                                             f["vwap"][i], f["atr"][i], f["vmean20"][i])
        close, prev = bar["close"], window[-2]
        if family == "MR" and vwap is not None:
            state["exit_long"] = close >= vwap
            state["exit_short"] = close <= vwap
        if state["entered"] or not _entry_ok(bar) or None in (e20, e50, rsi, vwap):
            return None, state
        long_sig = short_sig = False
        if family == "PB":
            pe20 = f["ema20"][i - 1]
            if pe20 is not None:
                long_sig = e20 > e50 and close > vwap and prev["low"] <= pe20 and close > e20 and 40 <= rsi <= 70
                short_sig = e20 < e50 and close < vwap and prev["high"] >= pe20 and close < e20 and 30 <= rsi <= 60
        elif family == "MR":
            if adx is not None and atr is not None and adx < 20:
                long_sig = rsi <= 30 and close < vwap - atr
                short_sig = rsi >= 70 and close > vwap + atr
        elif family == "VB":
            pv = f["vwap"][i - 1]
            if vm and pv is not None:
                vol_ok = bar["volume"] >= 2 * vm
                long_sig = vol_ok and prev["close"] <= pv and close > vwap and e20 > e50
                short_sig = vol_ok and prev["close"] >= pv and close < vwap and e20 < e50
        if side == "short":
            long_sig = False
        if long_sig and not short_sig:
            state["entered"] = True
            state["exit_long"] = state["exit_short"] = False
            return "BUY", state
        if short_sig and not long_sig:
            state["entered"] = True
            state["exit_long"] = state["exit_short"] = False
            return "SHORT", state
        return None, state
    return fn


# ---------------------------------------------------------------- grid ----

def grid():
    cfgs = [{"id": f"A-ck43-k{k}", "kind": "checklist", "tf": 5, "widen": k} for k in (2, 3)]
    cfgs += [{"id": f"B-ck-{tf}m", "kind": "checklist", "tf": tf, "widen": None} for tf in (15, 60)]
    for fam, tf, stop, exit_, side in product(("PB", "MR", "VB"), (5, 15, 60), (1.5, 3.0), ("2R", "hold"),
                                              ("both", "short")):
        cfgs.append({"id": f"C-{fam}-{tf}m-s{stop}-{exit_}-{side}", "kind": "family", "family": fam,
                     "tf": tf, "stop": stop, "exit": exit_, "side": side})
    assert len(cfgs) == 76
    return cfgs


def run_config(cfg, candles_by_tf, feats_by_tf):
    candles = candles_by_tf[cfg["tf"]]
    risk_cfg = {**config.RISK, "min_confidence_to_trade": 0}
    if cfg["kind"] == "checklist":
        name = "sahab_dimaag"
        params = {**config.STRATEGY_PARAMS["sahab_dimaag"], "min_stop_cost_widen": cfg["widen"]}
    else:
        name = "_search_family"
        STRATEGY_FUNCTIONS[name] = make_family(cfg["family"], cfg["side"], feats_by_tf[cfg["tf"]])
        params = {}
        risk_cfg["atr_sl_multiplier"] = cfg["stop"]
        risk_cfg["atr_tp_multiplier"] = 2 * cfg["stop"] if cfg["exit"] == "2R" else 100.0
    try:
        trades, _ = backtester.run_backtest(sorted(candles), name, params, risk_cfg, f"{cfg['tf']}m", DAYS,
                                            costs_cfg=config.COSTS, preloaded=candles, allowed_by_day=None,
                                            scorecard=[])
    finally:
        STRATEGY_FUNCTIONS.pop("_search_family", None)
    return trades


def summarise(trades):
    ok = [t for t in trades if t.get("risk_per_share") and t.get("qty")]
    rs = [t["pnl"] / (t["risk_per_share"] * t["qty"]) for t in ok]
    if len(rs) < 2:
        return {"n": len(rs), "net_r": rs[0] if rs else None, "t": None, "rs": rs}
    m, sd = st.mean(rs), st.stdev(rs)
    se = sd / math.sqrt(len(rs))
    return {"n": len(rs), "net_r": m, "sd": sd, "t": m / se if se else None,
            "gross_r": st.mean([t["gross_pnl"] / (t["risk_per_share"] * t["qty"]) for t in ok]),
            "net_rs": sum(t["pnl"] for t in ok), "win_pct": 100 * sum(r > 0 for r in rs) / len(rs),
            "stop_bp_median": st.median([t["risk_per_share"] / t["entry_price"] * 1e4 for t in ok]), "rs": rs}


def passes(first, second, pooled, dsr):
    return (pooled["net_r"] is not None and pooled["net_r"] > 0 and (pooled["t"] or 0) > 2
            and (first["net_r"] or -1) > 0 and (second["net_r"] or -1) > 0
            and (dsr.get("dsr") or 0) >= 0.95 and pooled["n"] >= 100)


def prepare(preloaded):
    by_tf, feats = {}, {}
    for tf in (5, 15, 60):
        by_tf[tf] = {s: aggregate(bars, tf) for s, bars in preloaded.items()}
        feats[tf] = {id(c[0]): features(c) for c in by_tf[tf].values() if c}
    return by_tf, feats


def main():
    rows = universe.load()
    symbols = [r["symbol"] for r in rows]
    preloaded = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=DAYS)
    all_sessions = splits.sessions_in(preloaded)
    selection, held_out = splits.selection_holdout(all_sessions)
    first, second = splits.halves(selection)
    out = json.loads(OUT.read_text()) if OUT.exists() else {"configs": {}, "resumed": 0}
    if out["configs"]:
        out["resumed"] += 1
    out.update(selection=[selection[0], selection[-1], len(selection)],
               halves=[[first[0], first[-1], len(first)], [second[0], second[-1], len(second)]],
               n_trials=N_TRIALS, held_out_sessions=len(held_out))
    print(splits.describe_split("selection", selection))
    print(f"held-out: {len(held_out)} sessions, NOT loaded into the grid\n", flush=True)

    halves_data = {}
    for name, sess in (("first", first), ("second", second)):
        sliced, _ = splits.slice_data(preloaded, {}, sess)
        halves_data[name] = prepare(sliced)
        del sliced
    del preloaded

    for cfg in grid():
        if cfg["id"] in out["configs"]:
            continue
        t0 = time.time()
        res = {}
        for name in ("first", "second"):
            by_tf, feats = halves_data[name]
            res[name] = summarise(run_config(cfg, by_tf, feats))
        pooled = summarise([])
        pooled_rs = res["first"]["rs"] + res["second"]["rs"]
        if len(pooled_rs) >= 2:
            m, sd = st.mean(pooled_rs), st.stdev(pooled_rs)
            pooled = {"n": len(pooled_rs), "net_r": m, "sd": sd, "t": m / (sd / math.sqrt(len(pooled_rs))) if sd else None}
        dsr = evaluation.deflated_sharpe_ratio(pooled_rs, N_TRIALS) if pooled_rs else {"dsr": None}
        ok = passes(res["first"], res["second"], pooled, dsr)
        strip = lambda d: {k: v for k, v in d.items() if k != "rs"}
        out["configs"][cfg["id"]] = {"cfg": cfg, "first": strip(res["first"]), "second": strip(res["second"]),
                                     "pooled": pooled, "dsr": dsr.get("dsr"), "pass": ok}
        OUT.write_text(json.dumps(out, indent=1, default=float))
        print(f"{cfg['id']:<34} n={pooled['n']:>5}  net={pooled['net_r'] if pooled['net_r'] is not None else float('nan'):+.3f}R"
              f"  t={pooled['t'] if pooled['t'] is not None else float('nan'):+.2f}  dsr={dsr.get('dsr')}"
              f"  {'PASS' if ok else 'fail'}  ({time.time() - t0:.0f}s)", flush=True)

    passers = [c for c in out["configs"].values() if c["pass"]]
    out["selection_passes"] = [c["cfg"]["id"] for c in passers]
    print(f"\nSelection passes: {len(passers)} of {len(out['configs'])}")
    if not passers:
        out["verdict"] = "NO PASS — no held-out look taken; nothing deployed"
        OUT.write_text(json.dumps(out, indent=1, default=float))
        print(out["verdict"])
        return
    best = max(passers, key=lambda c: c["dsr"])
    print(f"Best by DSR: {best['cfg']['id']} — running the held-out window ONCE (trial 117)", flush=True)
    held = splits.slice_data(kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=DAYS), {}, held_out)[0]
    by_tf, feats = prepare(held)
    h = summarise(run_config(best["cfg"], by_tf, feats))
    one_sided_ok = h["net_r"] is not None and h["net_r"] > 0 and (h["t"] or 0) > 1.65 and h["n"] >= 50
    out["held_out"] = {"config": best["cfg"]["id"], **{k: v for k, v in h.items() if k != "rs"},
                       "confirms": one_sided_ok}
    out["verdict"] = f"{'CONFIRMED' if one_sided_ok else 'HELD-OUT FAIL'} — {best['cfg']['id']}"
    OUT.write_text(json.dumps(out, indent=1, default=float))
    print(f"held-out: n={h['n']} net={h['net_r']} t={h['t']}  ->  {out['verdict']}")


if __name__ == "__main__":
    main()
