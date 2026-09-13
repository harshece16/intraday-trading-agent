"""
Backtester — replays historical intraday candles bar-by-bar through the
exact same strategy + risk logic used live (strategy_engine.py,
risk_manager.py), so you can see a strategy's actual historical win rate,
expectancy, and drawdown *before* trusting it with paper or real money.

All symbols are walked on one shared timeline (not one-symbol-at-a-time),
so portfolio-level risk controls — max_open_positions, max_daily_loss_pct —
interact across symbols the same way they do in the live engine.

Every entry and exit models realistic Zerodha-style intraday-equity costs
(brokerage, STT, exchange/SEBI charges, stamp duty, GST) and slippage — see
config.COSTS / costs.py. A strategy that looks profitable gross-of-costs can
easily be a net loser once these are applied, especially at higher trade
frequency; use --no-costs to see the (unrealistic) frictionless comparison.

This is not a guarantee of future performance — it's a sanity check.
Past bars behaving a certain way says nothing certain about future ones.
yfinance intraday history is also limited (5m bars: ~60 days; 1m: ~7 days),
so this is a small, recent sample, not a robust multi-year backtest.

Usage:
    cd webapp/backend
    python backtester.py --symbols RELIANCE,TCS,INFY --strategy sma_crossover --days 55
    python backtester.py --strategy rsi_reversion --days 55
    python backtester.py --no-costs   # frictionless comparison, for reference only
"""

import argparse
import math
from datetime import datetime
from zoneinfo import ZoneInfo

import config
import data_provider
import evaluation
from strategy_engine import STRATEGY_FUNCTIONS, atr as compute_atr
from risk_manager import RiskManager
from trading_engine import _parse_hhmm
from costs import apply_slippage, leg_cost, ZERO_COSTS

IST = ZoneInfo("Asia/Kolkata")


class _Position:
    __slots__ = ("quantity", "avg_price", "entry_atr", "entry_cost", "stop", "target", "risk_ps")

    def __init__(self):
        self.quantity = 0
        self.avg_price = 0.0
        self.entry_atr = None
        self.entry_cost = 0.0
        self.stop = None
        self.target = None
        self.risk_ps = None


def _to_ist(iso_time: str) -> datetime:
    ts = datetime.fromisoformat(iso_time)
    return ts.astimezone(IST) if ts.tzinfo else ts.replace(tzinfo=IST)


def _open_position(pos, side, raw_price, qty, atr_val, costs_cfg, risk, stop=None, target=None):
    fill_price = apply_slippage(side, raw_price, costs_cfg)
    pos.quantity = qty if side == "BUY" else -qty
    pos.avg_price = fill_price
    pos.entry_atr = atr_val
    pos.entry_cost = leg_cost(side, fill_price, qty, costs_cfg)
    pos.stop = stop if stop is not None else risk.stop_loss_price(fill_price, side, atr=atr_val)
    pos.target = target if target is not None else risk.take_profit_price(fill_price, side, atr=atr_val)
    pos.risk_ps = abs(fill_price - pos.stop)


def _close_position(pos, raw_exit_price, risk, trades, symbol, ts, reason, costs_cfg):
    exit_side = "SELL" if pos.quantity > 0 else "BUY"
    fill_price = apply_slippage(exit_side, raw_exit_price, costs_cfg)
    side_sign = 1 if pos.quantity > 0 else -1
    qty = abs(pos.quantity)

    gross_pnl = (fill_price - pos.avg_price) * qty * side_sign
    exit_cost = leg_cost(exit_side, fill_price, qty, costs_cfg)
    total_cost = pos.entry_cost + exit_cost
    net_pnl = gross_pnl - total_cost

    risk.record_realized_pnl(net_pnl)
    trades.append({
        "symbol": symbol, "exit_time": ts.isoformat(), "side": "LONG" if side_sign > 0 else "SHORT",
        "qty": qty, "entry_price": pos.avg_price, "exit_price": fill_price,
        "gross_pnl": gross_pnl, "cost": total_cost, "pnl": net_pnl, "reason": reason,
        "r": net_pnl / (pos.risk_ps * qty) if pos.risk_ps else None,
    })
    pos.quantity, pos.avg_price, pos.entry_atr, pos.entry_cost = 0, 0.0, None, 0.0
    pos.stop = pos.target = pos.risk_ps = None
    risk.open_positions_count = max(0, risk.open_positions_count - 1)
    return net_pnl


def run_backtest(symbols, strategy_name, strategy_params, risk_cfg, interval, days, costs_cfg=None,
                 preloaded=None, allowed_by_day=None):
    """preloaded: {symbol: candles} to skip per-symbol downloads.
    allowed_by_day: {"YYYY-MM-DD": [symbols]} — new entries only in that day's picks."""
    costs_cfg = costs_cfg if costs_cfg is not None else config.COSTS
    risk = RiskManager(risk_cfg)
    strategy_fn = STRATEGY_FUNCTIONS[strategy_name]
    market_open_t = _parse_hhmm(config.MARKET_OPEN)
    square_off_t = _parse_hhmm(config.SQUARE_OFF_TIME)

    data = {}
    for symbol in symbols:
        candles = preloaded.get(symbol, []) if preloaded is not None else \
            data_provider.get_intraday_candles(symbol, interval=interval, period=f"{days}d")
        if len(candles) < 60:
            print(f"  skipping {symbol}: only {len(candles)} bars returned (need >=60)")
            continue
        data[symbol] = candles

    if not data:
        return [], [float(risk_cfg["total_capital"])]

    # Index each symbol's bars by IST timestamp, then build one shared,
    # sorted timeline across all symbols so risk state (open position count,
    # daily P&L) is evaluated at the portfolio level, in real chronological
    # order — the same way the live engine sees it.
    ts_index = {s: {_to_ist(c["time"]): i for i, c in enumerate(candles)} for s, candles in data.items()}
    timeline = sorted({ts for idx in ts_index.values() for ts in idx})

    positions = {s: _Position() for s in data}
    strat_states = {s: None for s in data}

    equity = float(risk_cfg["total_capital"])
    equity_curve = [equity]
    trades = []
    current_day = None

    for ts in timeline:
        if current_day != ts.date():
            risk.reset_day()
            current_day = ts.date()
        t = ts.time()

        for symbol, candles in data.items():
            i = ts_index[symbol].get(ts)
            if i is None or i == 0:
                continue  # this symbol has no bar at this instant, or it's the first bar (no history yet)

            bar = candles[i]
            pos = positions[symbol]

            # 1) Stop-loss / take-profit against this bar's high/low (more
            #    realistic than only checking the close).
            if pos.quantity != 0:
                sign = 1 if pos.quantity > 0 else -1
                hit_stop = (pos.quantity > 0 and bar["low"] <= pos.stop) or (pos.quantity < 0 and bar["high"] >= pos.stop)
                hit_target = (pos.quantity > 0 and bar["high"] >= pos.target) or (pos.quantity < 0 and bar["low"] <= pos.target)
                if hit_stop or hit_target:
                    exit_price = pos.stop if hit_stop else pos.target
                    if hit_stop and (bar["open"] - pos.stop) * sign < 0:
                        exit_price = bar["open"]  # gapped through the stop: fill at the open, not the stop
                    equity += _close_position(pos, exit_price, risk, trades, symbol, ts,
                                               "stop_loss" if hit_stop else "take_profit", costs_cfg)
                    equity_curve.append(equity)
                    continue
                trail_after = risk_cfg.get("trail_after_r")
                if trail_after and pos.risk_ps:
                    steps = math.floor((bar["close"] - pos.avg_price) * sign / pos.risk_ps)
                    if steps >= trail_after:
                        new_stop = pos.avg_price + sign * pos.risk_ps * (steps - trail_after)
                        if (new_stop - pos.stop) * sign > 0:
                            pos.stop = new_stop

            # 2) Auto square-off window / outside market hours.
            if t >= square_off_t:
                if pos.quantity != 0:
                    equity += _close_position(pos, bar["close"], risk, trades, symbol, ts, "auto_square_off", costs_cfg)
                    equity_curve.append(equity)
                continue
            if t < market_open_t:
                continue

            allowed = allowed_by_day.get(ts.date().isoformat(), {}) if allowed_by_day is not None else None
            if allowed is not None and pos.quantity == 0 and symbol not in allowed:
                strat_states[symbol] = None
                continue

            # 3) Strategy signal, computed only from bars up to and
            #    including this one — no look-ahead.
            window = candles[: i + 1]
            signal, strat_states[symbol] = strategy_fn(window, prev_state=strat_states[symbol], **strategy_params)
            st = strat_states[symbol] or {}

            # Exits mirror the live engine: the brain's exit condition, or a signal for the other side.
            if pos.quantity > 0 and (signal in ("SELL", "SHORT") or st.get("exit_long")):
                equity += _close_position(pos, bar["close"], risk, trades, symbol, ts, "signal", costs_cfg)
                equity_curve.append(equity)
            elif pos.quantity < 0 and (signal in ("BUY", "COVER") or st.get("exit_short")):
                equity += _close_position(pos, bar["close"], risk, trades, symbol, ts, "signal", costs_cfg)
                equity_curve.append(equity)
            elif pos.quantity == 0 and signal in ("BUY", "SHORT"):
                side = "BUY" if signal == "BUY" else "SELL"
                if isinstance(allowed, dict) and allowed.get(symbol) != ("LONG" if side == "BUY" else "SHORT"):
                    continue
                if not risk.can_open_new_position():
                    continue
                atr_val = compute_atr(window, risk_cfg.get("atr_period", 14)) if risk_cfg.get("use_atr_risk") else None
                plan = None
                if st.get("entry_mode") == "checklist":
                    plan = (st.get("checklist") or {}).get("long" if side == "BUY" else "short")
                    if not plan or plan.get("stop") is None:
                        plan = None
                qty = int(risk.position_size(bar["close"], atr=atr_val, stop_price=plan["stop"] if plan else None)
                          * (plan["size_factor"] if plan else 1.0))
                if qty <= 0:
                    continue
                _open_position(pos, side, bar["close"], qty, atr_val, costs_cfg, risk,
                               stop=plan["stop"] if plan else None, target=plan["target"] if plan else None)
                risk.open_positions_count += 1

    # Mark-to-market any positions still open at the end of the sample.
    for symbol, pos in positions.items():
        if pos.quantity != 0:
            last = data[symbol][-1]
            equity += _close_position(pos, last["close"], risk, trades, symbol, _to_ist(last["time"]),
                                       "end_of_backtest", costs_cfg)
            equity_curve.append(equity)

    return trades, equity_curve


def report(trades, equity_curve, starting_capital, costs_enabled, n_trials=1):
    if not trades:
        print("\nNo trades were generated — try a longer --days window, a different")
        print("strategy, or check that the symbols/interval returned data at all.")
        return

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    total_pnl = sum(t["pnl"] for t in trades)
    total_gross_pnl = sum(t["gross_pnl"] for t in trades)
    total_costs = sum(t["cost"] for t in trades)

    peak = equity_curve[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        dd = peak - e
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak * 100) if peak else 0.0

    print(f"\n{'='*50}\nBACKTEST REPORT\n{'='*50}")
    print(f"Trades:            {len(trades)}")
    print(f"Win rate:          {len(wins) / len(trades) * 100:.1f}%  ({len(wins)}W / {len(losses)}L)")
    print(f"Avg win:           {(gross_profit / len(wins)) if wins else 0:.2f}")
    print(f"Avg loss:          {-(gross_loss / len(losses)) if losses else 0:.2f}")
    print(f"Profit factor:     {(gross_profit / gross_loss) if gross_loss else float('inf'):.2f}")
    print(f"{'-'*50}")
    if costs_enabled:
        print(f"Gross P&L:         {total_gross_pnl:.2f}  (before costs/slippage)")
        print(f"Costs + slippage:  {total_costs:.2f}  (avg {total_costs / len(trades):.2f}/trade, "
              f"{total_costs / total_gross_pnl * 100:.1f}% of gross profit)" if total_gross_pnl > 0
              else f"Costs + slippage:  {total_costs:.2f}  (avg {total_costs / len(trades):.2f}/trade)")
    print(f"Net P&L:           {total_pnl:.2f}  ({total_pnl / starting_capital * 100:.2f}% of starting capital)")
    print(f"Max drawdown:      {max_dd:.2f}  ({max_dd_pct:.2f}%)")
    print(f"Exit reasons:      {_count_reasons(trades)}")
    by_side = {}
    for t in trades:
        by_side.setdefault(t["side"], []).append(t)
    for side, ts_ in sorted(by_side.items()):
        w = sum(1 for t in ts_ if t["pnl"] > 0)
        print(f"{side + ':':19s}{len(ts_)} trades, win {w / len(ts_) * 100:.0f}%, "
              f"gross {sum(t['gross_pnl'] for t in ts_):.0f}, net {sum(t['pnl'] for t in ts_):.0f}")
    rs = [t["r"] for t in trades if t.get("r") is not None]
    if rs:
        wins_r = [x for x in rs if x > 0]
        losses_r = [x for x in rs if x <= 0]
        w = len(wins_r) / len(rs)
        avg_w = sum(wins_r) / len(wins_r) if wins_r else 0.0
        avg_l = sum(losses_r) / len(losses_r) if losses_r else 0.0
        if avg_w > 0 and avg_l < 0:
            kelly = w - (1 - w) / (avg_w / abs(avg_l))
        else:
            kelly = 1.0 if not losses_r else 0.0
        print(f"Expectancy:        {sum(rs) / len(rs):+.2f}R per trade (avg win {avg_w:+.2f}R, avg loss {avg_l:+.2f}R)")
        print(f"Kelly fraction:    {kelly:.1%}" + ("  (no edge: the right bet size is zero)" if kelly <= 0 else ""))
        dsr = evaluation.deflated_sharpe_ratio(rs, n_trials)
        if dsr["dsr"] is not None:
            print(f"Deflated Sharpe:   {dsr['dsr']:.1%} probability of real skill, after correcting for "
                  f"{n_trials} backtest configurations tried so far (raw Sharpe {dsr['sharpe']:+.2f})")
        else:
            print(f"Deflated Sharpe:   n/a — {dsr['note']}")
    print(f"{'='*50}")
    if not costs_enabled:
        print("NOTE: run with costs disabled (--no-costs) — this is a frictionless,")
        print("unrealistic number. Drop --no-costs to see the number that matters.")
    print("Reminder: this is a small, recent, delayed-data sample from yfinance —")
    print("treat it as a sanity check on the strategy's logic, not proof of an edge.")


def _count_reasons(trades):
    counts = {}
    for t in trades:
        counts[t["reason"]] = counts.get(t["reason"], 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--symbols", default=",".join(config.WATCHLIST), help="Comma-separated NSE symbols")
    parser.add_argument("--strategy", default=config.STRATEGY, choices=list(STRATEGY_FUNCTIONS))
    parser.add_argument("--interval", default=config.CANDLE_INTERVAL)
    parser.add_argument("--days", type=int, default=55, help="yfinance caps 5m history at ~60 days")
    parser.add_argument("--capital", type=float, default=config.RISK["total_capital"])
    parser.add_argument("--no-costs", action="store_true",
                         help="Disable brokerage/STT/slippage modeling (frictionless, for comparison only)")
    parser.add_argument("--universe", choices=["nifty100"],
                        help="Scan the NIFTY 100 each day and trade only the scanner's top picks")
    parser.add_argument("--scan-top", type=int, default=5, help="Picks per day in --universe mode")
    parser.add_argument("--long-only", action="store_true", help="Disable short selling (sahab_dimaag)")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    strategy_params = dict(config.STRATEGY_PARAMS[args.strategy])
    if args.long_only and args.strategy == "sahab_dimaag":
        strategy_params["allow_shorts"] = False
    risk_cfg = {**config.RISK, "total_capital": args.capital}
    costs_cfg = ZERO_COSTS if args.no_costs else config.COSTS

    preloaded = picks = None
    label = str(symbols)
    if args.universe:
        from collections import Counter
        import scanner
        import universe
        rows = universe.load()
        tickers = [scanner.yf_ticker(r["symbol"]) for r in rows]
        print(f"Downloading daily + {args.interval} history for {len(rows)} NIFTY 100 stocks...")
        daily = scanner.download_batch(tickers + [scanner.NIFTY], "2y", "1d")
        intraday = scanner.download_batch(tickers, f"{args.days}d", args.interval)
        preloaded = {t[:-3]: c for t, c in intraday.items()}
        symbols = sorted(preloaded)
        sessions = sorted({c["time"][:10] for cs in preloaded.values() for c in cs})
        picks = scanner.premarket_picks(daily, rows, sessions, args.scan_top, config.SCANNER,
                                        allow_shorts=not args.long_only)
        freq = Counter(s for day in picks.values() for s in day)
        print(f"Scanner picked {len(freq)} distinct stocks over {len(sessions)} sessions; most often: "
              + ", ".join(f"{s}×{n}" for s, n in freq.most_common(6)))
        print("(Backtest picks use daily data only — gap, relative volume, news and results-day "
              "filters need live/intraday context and aren't replayed.)")
        label = f"NIFTY 100 scanner, top {args.scan_top}/day"

    print(f"Backtesting {args.strategy} on {label} ({args.interval} bars, {args.days} days)"
          f"{' [costs disabled]' if args.no_costs else ' [with realistic costs]'}...")
    trades, equity_curve = run_backtest(symbols, args.strategy, strategy_params, risk_cfg,
                                         args.interval, args.days, costs_cfg,
                                         preloaded=preloaded, allowed_by_day=picks)
    trial_label = f"{args.strategy} {label} {args.interval} {args.days}d" + (" long-only" if args.long_only else "")
    n_trials = evaluation.log_trial(trial_label)
    report(trades, equity_curve, args.capital, costs_enabled=not args.no_costs, n_trials=n_trials)


if __name__ == "__main__":
    main()
