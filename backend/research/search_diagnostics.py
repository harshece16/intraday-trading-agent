"""Why the strategy-search configurations lose — a diagnostic REPLICATION,
not new trials (same precedent as R1, the Test A replication in trials.md).

strategy_search.py stores per-configuration summaries only. This re-runs a
chosen set of already-counted configurations on the same SELECTION sample
(held-out never loaded), with identical code and parameters, to recover
their trade lists, then measures:

  - gross R (after slippage, before charges) against net R, and the
    friction in R, per configuration
  - exit mix: stop / target / square-off / signal, with the mean net R of each
  - net R by entry hour and by side
  - MFE / MAE: the best and worst excursion in R from entry to exit, from
    the bars the trade was open on, so a target or stop that is systematically
    too near or too far shows up as a number

Nothing here selects a configuration or a parameter; its output is the
evidence a later pre-registration cites.

Usage: python research/search_diagnostics.py ID [ID ...]
"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import kite_history
import universe
from research import splits
from research import strategy_search as ss

OUT = Path(__file__).resolve().parents[2] / "docs/research/search_diagnostics.json"


def _r(t, key="pnl"):
    return t[key] / (t["risk_per_share"] * t["qty"])


def excursions(t, candles):
    """(MFE, MAE) in R over the bars the trade was open on, entry bar excluded."""
    sign = 1 if t["side"] == "LONG" else -1
    entry, rps = t["entry_price"], t["risk_per_share"]
    mfe = mae = 0.0
    for b in candles:
        if not (t["entry_time"][:19] < b["time"][:19] <= t["exit_time"][:19]):
            continue
        fav = (b["high"] - entry) if sign > 0 else (entry - b["low"])
        adv = (b["low"] - entry) if sign > 0 else (entry - b["high"])
        mfe, mae = max(mfe, fav / rps), min(mae, adv / rps)
    return mfe, mae


def diagnose(trades, candles_by_symbol):
    ok = [t for t in trades if t.get("risk_per_share") and t.get("qty")]
    if not ok:
        return {"n": 0}
    net, gross = [_r(t) for t in ok], [_r(t, "gross_pnl") for t in ok]
    pre = [t.get("pre_slippage_pnl", t["gross_pnl"]) / (t["risk_per_share"] * t["qty"]) for t in ok]
    by = lambda keyf: {k: {"n": len(v), "net_r": round(st.mean(v), 3)}
                       for k, v in sorted(_group(ok, keyf).items())}
    ex = [excursions(t, candles_by_symbol.get(t["symbol"], [])) for t in ok]
    return {
        "n": len(ok),
        "pre_friction_r": round(st.mean(pre), 3), "gross_r": round(st.mean(gross), 3),
        "net_r": round(st.mean(net), 3), "friction_r": round(st.mean(pre) - st.mean(net), 3),
        "win_pct": round(100 * sum(r > 0 for r in net) / len(net), 1),
        "exit_mix": by(lambda t: t["reason"]),
        "by_entry_hour": by(lambda t: (t.get("entry_time") or "")[11:13]),
        "by_side": by(lambda t: t["side"]),
        "mfe_r_median": round(st.median(m for m, _ in ex), 2),
        "mae_r_median": round(st.median(a for _, a in ex), 2),
        "share_reaching_1r": round(100 * sum(m >= 1 for m, _ in ex) / len(ex), 1),
        "share_reaching_2r": round(100 * sum(m >= 2 for m, _ in ex) / len(ex), 1),
    }


def _group(trades, keyf):
    g = defaultdict(list)
    for t in trades:
        g[keyf(t)].append(_r(t))
    return g


def main(ids):
    cfgs = {c["id"]: c for c in ss.grid()}
    unknown = [i for i in ids if i not in cfgs]
    if unknown:
        raise SystemExit(f"unknown configuration ids: {unknown}")
    symbols = [r["symbol"] for r in universe.load()]
    pre = kite_history.load_batch(symbols, interval=config.CANDLE_INTERVAL, days=ss.DAYS)
    selection, _ = splits.selection_holdout(splits.sessions_in(pre))
    first, second = splits.halves(selection)
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    halves = {}
    for name, sess in (("first", first), ("second", second)):
        sliced, _ = splits.slice_data(pre, {}, sess)
        halves[name] = ss.prepare(sliced)
    del pre
    for cid in ids:
        if cid in out:
            continue
        cfg = cfgs[cid]
        trades, candles = [], {}
        for name in ("first", "second"):
            by_tf, feats = halves[name]
            trades += ss.run_config(cfg, by_tf, feats)
            for s, c in by_tf[cfg["tf"]].items():
                candles.setdefault(s, []).extend(c)
        out[cid] = diagnose(trades, candles)
        OUT.write_text(json.dumps(out, indent=1))
        d = out[cid]
        print(f"{cid:<34} n={d['n']:>5} pre={d.get('pre_friction_r')} gross={d.get('gross_r')} "
              f"net={d.get('net_r')} friction={d.get('friction_r')} mfe~{d.get('mfe_r_median')} "
              f"mae~{d.get('mae_r_median')} >=1R {d.get('share_reaching_1r')}%", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
