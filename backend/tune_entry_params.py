"""
Grid-search RISK["min_confidence_to_trade"] and
STRATEGY_PARAMS["sahab_dimaag"]["min_rrr"] against the real backtest
infrastructure (backtester.run_backtest(), called directly — not the CLI),
ranked by Deflated Sharpe Ratio, not raw return.

Why DSR and not return: DSR (Bailey & López de Prado, 2014, already
implemented in evaluation.py, cited throughout this codebase) is
specifically built to correct for exactly what grid-searching many
configs and picking the best one does — try enough configurations and one
will look good by chance alone, even with zero real edge. Ranking by
return would just re-commit that mistake with extra steps.

What this does NOT touch: config.py, PAPER_MODE_DEFAULT, FNO["enabled"],
app.py, trading_engine.py. It reads config.py's current defaults as the
grid's fixed baseline and calls backtester.run_backtest() with modified
copies — nothing written back until you pick a result yourself.

A real, permanent side effect worth knowing: every config tried here is
logged via evaluation.log_trial() (backend/data/backtest_trials.json), so
running this script grows the trial count that gates every DSR this
codebase computes from now on — including the live journal's own
Scorecard once real trades accumulate. That's the correct behavior (DSR's
whole point is knowing the true number of things tried), not a bug, but
it means this script's own cost is a stricter bar for every future
backtest, forever. Don't run the same grid twice expecting a fresh trial
count.

Applies the SAME confidence gate trading_engine._try_enter() applies
live (confidence.score_trade(), gated at RISK["min_confidence_to_trade"])
— backtester.run_backtest() didn't do this before this script was built
(see README / tracking issue); without that fix, varying
min_confidence_to_trade here would have had zero effect on results. Uses
the REAL current journal scorecard (database.journal_summary()), fixed
for every cell in the grid — the same system-evidence state live paper
trading operates under right now, not a hypothetical fully-proven one.

Usage:
    cd webapp/backend
    python tune_entry_params.py
    python tune_entry_params.py --days 55 --scan-top 5
"""

import argparse
import copy

import backtester
import config
import database
import evaluation
import scanner
import universe

MIN_CONFIDENCE_GRID = [40, 50, 60, 70]
MIN_RRR_GRID = [1.2, 1.5, 1.8]
DSR_BAR = 0.95  # same bar evaluation.scorecard() already holds a live backtest's DSR to


def _load_universe_data(days, interval, scan_top):
    rows = universe.load()
    tickers = [scanner.yf_ticker(r["symbol"]) for r in rows]
    print(f"Downloading daily + {interval} history for {len(rows)} NIFTY 100 stocks "
         f"(shared across every grid cell — one download, not {len(MIN_CONFIDENCE_GRID) * len(MIN_RRR_GRID)})...")
    daily = scanner.download_batch(tickers + [scanner.NIFTY], "2y", "1d")
    intraday = scanner.download_batch(tickers, f"{days}d", interval)
    preloaded = {t[:-3]: c for t, c in intraday.items()}
    symbols = sorted(preloaded)
    sessions = sorted({c["time"][:10] for cs in preloaded.values() for c in cs})
    picks = scanner.premarket_picks(daily, rows, sessions, scan_top, config.SCANNER, allow_shorts=True)
    print(f"{len(symbols)} symbols with data, {len(sessions)} sessions, top {scan_top}/day picks computed once.\n")
    return preloaded, symbols, picks


def _run_one(min_conf, min_rrr, preloaded, symbols, picks, days, interval, scorecard, scan_top):
    risk_cfg = copy.deepcopy(config.RISK)
    risk_cfg["min_confidence_to_trade"] = min_conf

    strategy_params = copy.deepcopy(config.STRATEGY_PARAMS["sahab_dimaag"])
    strategy_params["min_rrr"] = min_rrr

    label = f"grid-search min_confidence_to_trade={min_conf} min_rrr={min_rrr} " \
           f"nifty100 top{scan_top} {interval} {days}d"
    trades, equity_curve = backtester.run_backtest(
        symbols, "sahab_dimaag", strategy_params, risk_cfg, interval, days,
        costs_cfg=config.COSTS,  # WITH costs — a no-costs run would be misleading for this
        preloaded=preloaded, allowed_by_day=picks, scorecard=scorecard,
    )
    n_trials = evaluation.log_trial(label)

    rs = [t["r"] for t in trades if t.get("r") is not None]
    wins = [x for x in rs if x > 0]
    dsr = evaluation.deflated_sharpe_ratio(rs, n_trials) if rs else \
        {"dsr": None, "note": f"0 trades — this cell never got an entry (min_confidence_to_trade="
                              f"{min_conf}, min_rrr={min_rrr} was too strict for this sample)."}
    return {
        "min_confidence_to_trade": min_conf, "min_rrr": min_rrr,
        "trades": len(trades), "closed": len(rs),
        "win_rate_pct": round(len(wins) / len(rs) * 100, 1) if rs else None,
        "expectancy_r": round(sum(rs) / len(rs), 3) if rs else None,
        "net_pnl": round(sum(t["pnl"] for t in trades), 2),
        "dsr": dsr, "n_trials": n_trials,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interval", default=config.CANDLE_INTERVAL)
    parser.add_argument("--days", type=int, default=55, help="yfinance caps 5m history at ~60 days")
    parser.add_argument("--scan-top", type=int, default=5, help="Picks per day (same as backtester.py's --scan-top)")
    args = parser.parse_args()

    preloaded, symbols, picks = _load_universe_data(args.days, args.interval, args.scan_top)

    # Fixed once for the whole grid — the real, current system-evidence
    # state (see module docstring for why this, not a hypothetical one).
    scorecard = database.journal_summary(include_backtest_evidence=False).get("scorecard", [])  # tuning a new config: not vetoed by the old verdict
    print("Current real Dimaag Scorecard (fixed for every cell below):")
    for row in scorecard:
        print(f"  {row['criterion']}: {row['status']}")
    print()

    grid = [(c, r) for c in MIN_CONFIDENCE_GRID for r in MIN_RRR_GRID]
    print(f"Running {len(grid)} configs: min_confidence_to_trade in {MIN_CONFIDENCE_GRID}, "
         f"min_rrr in {MIN_RRR_GRID}\n")

    results = []
    for i, (min_conf, min_rrr) in enumerate(grid, 1):
        print(f"[{i}/{len(grid)}] min_confidence_to_trade={min_conf}, min_rrr={min_rrr} ...")
        r = _run_one(min_conf, min_rrr, preloaded, symbols, picks, args.days, args.interval, scorecard, args.scan_top)
        results.append(r)
        dsr_str = f"{r['dsr']['dsr']:.1%}" if r["dsr"]["dsr"] is not None else "n/a"
        print(f"    -> {r['trades']} trades, expectancy {r['expectancy_r']}, DSR {dsr_str}")

    _print_ranked_report(results)


def _print_ranked_report(results):
    # None-DSR (not enough trades to say anything) sorts last — a cell
    # that never traded isn't a "good" result just because it can't be
    # proven bad.
    ranked = sorted(results, key=lambda r: (r["dsr"]["dsr"] is None, -(r["dsr"]["dsr"] or -1)))

    print(f"\n{'='*100}")
    print("RANKED BY DEFLATED SHARPE RATIO (probability of real skill, corrected for every config tried)")
    print(f"{'='*100}")
    print(f"{'min_conf':>9} {'min_rrr':>8} {'trades':>7} {'win%':>6} {'expct(R)':>9} {'net P&L':>10} {'DSR':>8}")
    for r in ranked:
        dsr = r["dsr"]["dsr"]
        dsr_str = f"{dsr:.1%}" if dsr is not None else "n/a"
        win = f"{r['win_rate_pct']:.0f}" if r["win_rate_pct"] is not None else "n/a"
        exp = f"{r['expectancy_r']:+.3f}" if r["expectancy_r"] is not None else "n/a"
        print(f"{r['min_confidence_to_trade']:>9} {r['min_rrr']:>8} {r['trades']:>7} {win:>6} "
             f"{exp:>9} {r['net_pnl']:>+10.2f} {dsr_str:>8}")

    qualifying = [r for r in ranked if r["dsr"]["dsr"] is not None and r["dsr"]["dsr"] >= DSR_BAR]
    print(f"\n{'-'*100}")
    if not qualifying:
        best_with_data = next((r for r in ranked if r["dsr"]["dsr"] is not None), None)
        print(f"NONE of the {len(results)} configs tried clear DSR >= {DSR_BAR:.0%} — the same bar this "
             f"codebase's own Scorecard requires (evaluation.scorecard(), database.journal_summary()).")
        if best_with_data:
            print(f"The closest was min_confidence_to_trade={best_with_data['min_confidence_to_trade']}, "
                 f"min_rrr={best_with_data['min_rrr']} at DSR {best_with_data['dsr']['dsr']:.1%} — that is "
                 f"NOT a recommendation, it's the least-bad of a batch that didn't clear the bar. Don't treat "
                 f"picking it as finding an edge.")
        print("Honest read: this grid, on this sample, did not find a configuration with demonstrated real "
             "skill. That's a legitimate result, not a failed search — see the 55-day full-frequency backtest "
             "run earlier this project (DSR ~0%) for the same conclusion from a different angle.")
    else:
        print(f"{len(qualifying)} of {len(results)} configs cleared DSR >= {DSR_BAR:.0%}:")
        for r in qualifying:
            print(f"  min_confidence_to_trade={r['min_confidence_to_trade']}, min_rrr={r['min_rrr']} — "
                 f"DSR {r['dsr']['dsr']:.1%}, {r['trades']} trades, expectancy {r['expectancy_r']:+.3f}R")
        print("Still worth checking trade count on any of these before trusting it — a handful of trades "
             "clearing 0.95 by luck is exactly what DSR tries to catch, not something it can catch with "
             "certainty on a small sample.")
    print(f"{'='*100}")
    print("No R-multiple, DSR, or win-rate figure above implies an expected daily or annual return — this "
         "codebase deliberately never states one (see day_plan.py / README). config.py has NOT been changed; "
         "pick a row yourself and it'll be applied as a single, explicit edit.")


if __name__ == "__main__":
    main()
