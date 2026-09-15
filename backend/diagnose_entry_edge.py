"""
Diagnose WHY the checklist loses, and test the two cheapest candidate
fixes, before touching config.py.

Background (README §36): a 55-day backtest with the confidence gate off
showed two separate problems — (1) the stop is the candlestick pattern's
own high/low, which on 5-minute bars is tiny (median 0.19% of price)
next to ~0.106% round-trip costs, so friction costs ~0.56R per trade;
and (2) even before costs, expectancy was negative (-0.42R). Separately,
the scanner's stock RANKING has a positive Information Coefficient
(+0.29 to +0.32), while nothing shows the intraday ENTRY TIMING adds
anything.

So this script runs four configs on the same data, confidence gate OFF
for all four (the gate throttles volume; it's the entry logic being
judged here, and the no-timing baseline has no checklist score for the
gate to read):

  checklist @ 5m   — control, today's live entry logic
  checklist @ 30m  — same logic where one bar's range dwarfs costs
                     (Nison's patterns were built for daily charts)
  baseline  @ 5m   — no entry timing at all: enter the scanner's pick at
                     09:45 on its picked side, 1.5 ATR stop / 3 ATR target
  baseline  @ 30m  — same, on 30-minute bars

Each result is split into a SELECTION period (all but the last
HELD_OUT_SESSIONS sessions) and a HELD-OUT period (the last
HELD_OUT_SESSIONS). A fix only counts if it holds up on held-out days it
wasn't chosen on — same "evidence boundary" discipline evaluation.py
already follows. Every config logs one real trial (evaluation.log_trial).

Caveats that change what the 30m numbers mean (not bugs, but real):
opening range becomes the first 90 minutes (3 bars) and the "15-min
trend" becomes a 90-minute trend (htf_factor=3), since trader_brain
counts bars, not minutes.

Nothing here edits config.py or anything the live engine reads.

Usage:
    cd webapp/backend
    python diagnose_entry_edge.py
"""

import argparse
import statistics as st
from datetime import datetime

import backtester
import config
import evaluation
import scanner
import universe
from strategy_engine import STRATEGY_FUNCTIONS

HELD_OUT_SESSIONS = 20
BASELINE_NAME = "_rank_baseline"


def rank_baseline_signal(candles, prev_state=None, entry_time="09:45", **_):
    """Enter once per day, on the first bar at or after entry_time, on
    whatever side the scanner picked (backtester maps "ENTER" to it). No
    pattern, no confluence — exits are the ATR stop/target and the 15:15
    square-off. If this matches or beats the checklist, the checklist's
    timing isn't adding anything over the ranking it starts from."""
    last_time = candles[-1]["time"]
    day, hhmm = last_time[:10], last_time[11:16]
    state = dict(prev_state or {})
    if hhmm >= entry_time and state.get("entered_day") != day:
        state["entered_day"] = day
        return "ENTER", state
    return None, state


def _download(days, scan_top):
    rows = universe.load()
    tickers = [scanner.yf_ticker(r["symbol"]) for r in rows]
    print(f"Downloading daily, 5m and 30m history for {len(rows)} NIFTY 100 stocks...")
    daily = scanner.download_batch(tickers + [scanner.NIFTY], "2y", "1d")
    by_interval = {}
    for iv in ("5m", "30m"):
        intraday = scanner.download_batch(tickers, f"{days}d", iv)
        by_interval[iv] = {t[:-3]: c for t, c in intraday.items() if len(c) >= 60}
    sessions = sorted({c["time"][:10] for cs in by_interval["5m"].values() for c in cs})
    picks = scanner.premarket_picks(daily, rows, sessions, scan_top, config.SCANNER, allow_shorts=True)
    print(f"{len(sessions)} sessions; held-out = last {HELD_OUT_SESSIONS} ({sessions[-HELD_OUT_SESSIONS]} onward)\n")
    return by_interval, sessions, picks


def _per_trade(t):
    rps = t.get("risk_per_share")
    if not rps or not t["qty"]:
        return None
    risk = rps * t["qty"]
    return {
        "gross_r": t["gross_pnl"] / risk, "net_r": t["pnl"] / risk, "cost_r": t["cost"] / risk,
        "stop_pct": rps / t["entry_price"] * 100,
    }


def _summarise(trades, n_trials):
    rows = [x for x in (_per_trade(t) for t in trades) if x]
    if not rows:
        return {"n": 0}
    net = [r["net_r"] for r in rows]
    dsr = evaluation.deflated_sharpe_ratio(net, n_trials)
    return {
        "n": len(rows),
        "win_pct": sum(x > 0 for x in net) / len(net) * 100,
        "gross_exp": st.mean(r["gross_r"] for r in rows),
        "net_exp": st.mean(net),
        "cost_r": st.median(r["cost_r"] for r in rows),
        "stop_pct": st.median(r["stop_pct"] for r in rows),
        "dsr": dsr["dsr"],
    }


def _stopout_excursions(trades, candles_by_symbol):
    """For stop-outs: bars held, max favorable excursion in R before the
    stop, and whether price later reached the trade's own target the same
    day — using the recorded entry_time, not an inferred entry bar."""
    out = []
    for t in trades:
        if t["reason"] != "stop_loss" or not t.get("entry_time") or not t.get("risk_per_share"):
            continue
        entry = datetime.fromisoformat(t["entry_time"])
        exit_ = datetime.fromisoformat(t["exit_time"])
        day = [b for b in candles_by_symbol.get(t["symbol"], [])
               if datetime.fromisoformat(b["time"]).date() == entry.date()]
        long = t["side"] == "LONG"
        held = [b for b in day if entry < datetime.fromisoformat(b["time"]) <= exit_]
        after = [b for b in day if datetime.fromisoformat(b["time"]) > exit_]
        if not held:
            continue
        rps = t["risk_per_share"]
        mfe = max(((b["high"] - t["entry_price"]) if long else (t["entry_price"] - b["low"])) for b in held) / rps
        reached = t.get("target") is not None and any(
            (b["high"] >= t["target"]) if long else (b["low"] <= t["target"]) for b in after)
        out.append({"bars": len(held), "mfe_r": mfe, "target_later": reached})
    return out


def _fmt(s):
    if not s.get("n"):
        return "   0 trades"
    dsr = f"{s['dsr']:.1%}" if s["dsr"] is not None else "n/a"
    return (f"{s['n']:>4} trades  win {s['win_pct']:>3.0f}%  gross {s['gross_exp']:+.2f}R  "
            f"net {s['net_exp']:+.2f}R  cost {s['cost_r']:.2f}R  stop {s['stop_pct']:.2f}%  DSR {dsr}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=55)
    parser.add_argument("--scan-top", type=int, default=5)
    args = parser.parse_args()

    by_interval, sessions, picks = _download(args.days, args.scan_top)
    held_out_start = sessions[-HELD_OUT_SESSIONS]
    risk_cfg = {k: v for k, v in config.RISK.items() if k != "min_confidence_to_trade"}
    STRATEGY_FUNCTIONS[BASELINE_NAME] = rank_baseline_signal

    configs = [
        ("checklist", "5m", "sahab_dimaag", dict(config.STRATEGY_PARAMS["sahab_dimaag"])),
        ("checklist", "30m", "sahab_dimaag", dict(config.STRATEGY_PARAMS["sahab_dimaag"])),
        ("baseline", "5m", BASELINE_NAME, {}),
        ("baseline", "30m", BASELINE_NAME, {}),
    ]
    try:
        for label, iv, strat, params in configs:
            data = by_interval[iv]
            trades, _ = backtester.run_backtest(
                sorted(data), strat, params, risk_cfg, iv, args.days, costs_cfg=config.COSTS,
                preloaded=data, allowed_by_day=picks, scorecard=[],
            )
            n_trials = evaluation.log_trial(f"diagnose_entry_edge {label} {iv} {args.days}d top{args.scan_top} gate-off")
            sel = [t for t in trades if (t.get("entry_time") or t["exit_time"])[:10] < held_out_start]
            held = [t for t in trades if (t.get("entry_time") or t["exit_time"])[:10] >= held_out_start]
            print(f"== {label} @ {iv} ==")
            print(f"  all       {_fmt(_summarise(trades, n_trials))}")
            print(f"  selection {_fmt(_summarise(sel, n_trials))}")
            print(f"  held-out  {_fmt(_summarise(held, n_trials))}")
            exc = _stopout_excursions(trades, data)
            if exc:
                print(f"  stop-outs: {len(exc)}, median bars held {st.median(e['bars'] for e in exc):.0f}, "
                      f"reached >=1R in profit first: {sum(e['mfe_r'] >= 1 for e in exc)}, "
                      f"price hit their own target later that day: {sum(e['target_later'] for e in exc)}")
            print()
    finally:
        STRATEGY_FUNCTIONS.pop(BASELINE_NAME, None)

    print("R-multiples and DSR only — no expected-return figure is implied (see README / day_plan.py).")
    print("config.py is unchanged.")


if __name__ == "__main__":
    main()
