"""
Multi-day hold backtest — does the scanner's stock ranking pay if you hold
long enough to collect what it actually predicts?

Why this exists (README §36/§37): the scanner's ranking has a positive
Information Coefficient against NEXT-SESSION returns, but the intraday
agent exits the same day, usually within a few bars, and loses money in
every variant tried. This tests the other side of that mismatch: enter
the scanner's picks at the session open, hold 1/2/3/5 sessions, exit at
the close — daily bars, no intraday timing at all.

What it deliberately is, and isn't:
- LONG only. Holding a cash-equity short overnight isn't possible in India
  (short delivery goes to exchange auction), so a multi-day short would
  need futures — a different instrument this doesn't model.
- Picks come from scanner.premarket_picks(), which only uses data from
  before each session's open. The ATR used as a risk unit uses bars before
  the entry day only. No look-ahead.
- Costs by actual holding: exited the same day it was bought → intraday
  costs (config.COSTS); held overnight → delivery costs
  (costs.DELIVERY_COSTS, with its own verify-the-tariff caveat).
- A BENCHMARK runs the exact same rules on every universe stock, every day.
  A long-only strategy can look good just because the market rose; the
  number that matters is picks MINUS benchmark, not picks alone.
- SURVIVORSHIP BIAS: the universe is today's NIFTY 100 list applied to
  history. Stocks that dropped out of the index (usually because they fell)
  are missing, which flatters every long-only result here — picks and
  benchmark alike. The picks-minus-benchmark comparison partly cancels it;
  it doesn't remove it.
- R is a risk UNIT, not a stop: R = risk_atr (default 2) x daily ATR(14)
  at entry, so numbers are comparable in spirit to the intraday R-multiples
  elsewhere in this project. An optional real stop (--stop-atr) can be
  added; it's off by default.

Every hold length tried on the picks logs one DSR trial
(evaluation.log_trial). The benchmark isn't a candidate strategy and isn't
logged. Nothing here edits config.py or anything the live engine reads.

Usage:
    cd webapp/backend
    python swing_backtester.py
    python swing_backtester.py --years 2 --scan-top 5 --holds 1,2,3,5
"""

import argparse
import math
import statistics as st

import config
import evaluation
import indicators as ind
from costs import DELIVERY_COSTS, apply_slippage, leg_cost


def _manage(pos, bar, hold_sessions):
    """Advance one session for an open position. Returns (exit_price, reason)
    or (None, None) to keep holding. Entry is at the open, so the entry day
    itself counts as the first held session."""
    pos["sessions_held"] += 1
    stop = pos["stop"]
    if stop is not None and bar["low"] <= stop:
        return (bar["open"] if bar["open"] <= stop else stop), "stop"
    if pos["sessions_held"] >= hold_sessions:
        return bar["close"], "time"
    return None, None


def _close(pos, exit_price, exit_date, reason, intraday_costs, delivery_costs):
    same_day = exit_date == pos["entry_date"]
    costs_cfg = intraday_costs if same_day else delivery_costs
    fill = apply_slippage("SELL", exit_price, costs_cfg)
    qty = pos["qty"]
    gross = (fill - pos["entry_price"]) * qty
    cost = leg_cost("BUY", pos["entry_price"], qty, costs_cfg) + leg_cost("SELL", fill, qty, costs_cfg)
    risk = pos["risk_ps"] * qty
    return {
        "symbol": pos["symbol"], "side": "LONG", "entry_date": pos["entry_date"], "exit_date": exit_date,
        "sessions_held": pos["sessions_held"], "entry_price": pos["entry_price"], "exit_price": fill,
        "qty": qty, "gross_pnl": gross, "cost": cost, "pnl": gross - cost, "reason": reason,
        "risk_per_share": pos["risk_ps"], "gross_r": gross / risk, "cost_r": cost / risk,
        "r": (gross - cost) / risk, "cost_model": "intraday" if same_day else "delivery",
    }


def run_swing_backtest(daily, picks, sessions, hold_sessions, notional_per_trade, stop_atr=None,
                       risk_atr=2.0, intraday_costs=None, delivery_costs=None):
    """daily: {SYMBOL: [daily bars, oldest first]} (bare NSE symbols).
    picks: {"YYYY-MM-DD": {SYMBOL: "LONG" | "SHORT"}} — only LONG is traded.
    sessions: sorted trading dates to walk. Returns a list of closed trades;
    positions still open when the data ends are dropped, not marked to
    market (their exit isn't known yet)."""
    intraday_costs = intraday_costs if intraday_costs is not None else config.COSTS
    delivery_costs = delivery_costs if delivery_costs is not None else DELIVERY_COSTS
    by_date = {s: {b["time"][:10]: i for i, b in enumerate(bars)} for s, bars in daily.items()}
    open_pos, trades = {}, []

    for d in sessions:
        # Entries happen at the open, exits at the stop or close — so a
        # position closing today was still held at today's open and must
        # not be re-bought at that same open.
        held_at_open = set(open_pos)
        for sym in list(open_pos):
            i = by_date[sym].get(d)
            if i is None:
                continue  # no bar today (holiday/halt for this stock) — keep holding
            exit_price, reason = _manage(open_pos[sym], daily[sym][i], hold_sessions)
            if exit_price is not None:
                trades.append(_close(open_pos.pop(sym), exit_price, d, reason, intraday_costs, delivery_costs))

        for sym, side in (picks.get(d) or {}).items():
            if side != "LONG" or sym in held_at_open or sym in open_pos or sym not in by_date:
                continue
            i = by_date[sym].get(d)
            if i is None or i < 15:
                continue
            atr_v = ind.atr(daily[sym][max(0, i - 30):i], 14)  # bars BEFORE the entry day only
            if not atr_v:
                continue
            bar = daily[sym][i]
            fill = apply_slippage("BUY", bar["open"], intraday_costs)
            qty = int(notional_per_trade // fill)
            if qty <= 0:
                continue
            pos = {
                "symbol": sym, "entry_date": d, "entry_price": fill, "qty": qty, "sessions_held": 0,
                "stop": fill - stop_atr * atr_v if stop_atr else None,
                "risk_ps": (stop_atr or risk_atr) * atr_v,
            }
            exit_price, reason = _manage(pos, bar, hold_sessions)
            if exit_price is not None:
                trades.append(_close(pos, exit_price, d, reason, intraday_costs, delivery_costs))
            else:
                open_pos[sym] = pos
    return trades


def summarise(trades, n_trials=None):
    if not trades:
        return {"n": 0}
    net = [t["r"] for t in trades]
    out = {
        "n": len(trades),
        "win_pct": sum(x > 0 for x in net) / len(net) * 100,
        "gross_r": st.mean(t["gross_r"] for t in trades),
        "net_r": st.mean(net),
        "cost_r": st.median(t["cost_r"] for t in trades),
        "held": st.mean(t["sessions_held"] for t in trades),
        "dsr": None,
    }
    if n_trials is not None:
        out["dsr"] = evaluation.deflated_sharpe_ratio(net, n_trials)["dsr"]
    return out


def ic_summary(daily_ics):
    """Mean daily rank IC, its t-stat, and the share of days it was positive
    — how a ranking signal is judged over many sessions, not one cross-section
    (Grinold's breadth is independent bets over time; one day's stocks all
    move with the same market)."""
    if len(daily_ics) < 2:
        return {"days": len(daily_ics), "mean_ic": None, "t_stat": None, "pct_positive": None}
    m, s = st.mean(daily_ics), st.stdev(daily_ics)
    return {"days": len(daily_ics), "mean_ic": m,
            "t_stat": (m / s * math.sqrt(len(daily_ics))) if s > 0 else None,
            "pct_positive": sum(x > 0 for x in daily_ics) / len(daily_ics) * 100}


def daily_ranking_ic(raw, rows, sessions, cfg):
    """For each session: Spearman rank correlation, across every eligible
    universe stock, between the pre-market LONG score (data before that
    session only) and that session's open->close return. A measurement of
    the ranking itself, independent of any entry/exit rules."""
    import database
    import scanner

    nifty = raw[scanner.NIFTY]
    ndates = [b["time"][:10] for b in nifty]
    ncloses = [b["close"] for b in nifty]
    index = {t: {b["time"][:10]: i for i, b in enumerate(bars)} for t, bars in raw.items()}
    out = []
    for d in sessions:
        xs, ys = [], []
        for r in rows:
            t = scanner.yf_ticker(r["symbol"])
            bars = raw.get(t)
            if not bars or d not in index[t]:
                continue
            prof = scanner.daily_profile(bars, ndates, ncloses, d)
            if not prof or scanner.tradability_exclusion(prof, cfg):
                continue
            score, _, _ = scanner.premarket_score(prof, cfg, "long", date_iso=d)
            bar = bars[index[t][d]]
            xs.append(score)
            ys.append(bar["close"] / bar["open"] - 1)
        if len(xs) >= 20:
            ic = database._spearman(xs, ys)
            if ic is not None:
                out.append(ic)
    return out


def _fmt(s):
    if not s.get("n"):
        return "     0 trades"
    dsr = "" if s["dsr"] is None else f"  DSR {s['dsr']:.1%}"
    return (f"{s['n']:>6} trades  win {s['win_pct']:>3.0f}%  gross {s['gross_r']:+.3f}R  "
            f"net {s['net_r']:+.3f}R  cost {s['cost_r']:.3f}R  held {s['held']:.1f}d{dsr}")


def main():
    import scanner
    import universe

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--scan-top", type=int, default=5)
    parser.add_argument("--holds", default="1,2,3,5")
    parser.add_argument("--stop-atr", type=float, default=None, help="Optional real stop, in daily ATRs (off by default)")
    parser.add_argument("--held-out-frac", type=float, default=0.4)
    parser.add_argument("--skip-ic", action="store_true", help="Skip the daily ranking-IC measurement")
    args = parser.parse_args()
    holds = [int(h) for h in args.holds.split(",")]

    rows = universe.load()
    tickers = [scanner.yf_ticker(r["symbol"]) for r in rows]
    print(f"Downloading {args.years}y of daily bars for {len(rows)} NIFTY 100 stocks + NIFTY...")
    raw = scanner.download_batch(tickers + [scanner.NIFTY], f"{args.years}y", "1d")
    daily = {t[:-3]: bars for t, bars in raw.items() if t.endswith(".NS")}
    sessions = [b["time"][:10] for b in raw[scanner.NIFTY]][60:]  # skip warm-up; profiles need history
    held_out_start = sessions[int(len(sessions) * (1 - args.held_out_frac))]
    print(f"{len(sessions)} sessions {sessions[0]} to {sessions[-1]}; held-out from {held_out_start}")

    print("Computing daily scanner picks (long-only, pre-open data only)...")
    picks = scanner.premarket_picks(raw, rows, sessions, args.scan_top, config.SCANNER, allow_shorts=False)
    dates_by_sym = {s: {b["time"][:10] for b in bars} for s, bars in daily.items()}
    bench = {d: {s: "LONG" for s, ds in dates_by_sym.items() if d in ds} for d in sessions}
    capital = float(config.RISK["total_capital"])

    for h in holds:
        notional = capital / (args.scan_top * h)  # equal slots, fully cash-funded, no leverage
        kw = dict(sessions=sessions, hold_sessions=h, notional_per_trade=notional, stop_atr=args.stop_atr)
        p_trades = run_swing_backtest(daily, picks, **kw)
        b_trades = run_swing_backtest(daily, bench, **kw)
        n_trials = evaluation.log_trial(
            f"swing_backtester long-only hold={h} top{args.scan_top} {args.years}y stop_atr={args.stop_atr}")
        print(f"\n== hold {h} session{'s' if h > 1 else ''} ==")
        for label, sel in (("all", lambda t: True),
                           ("selection", lambda t: t["entry_date"] < held_out_start),
                           ("held-out", lambda t: t["entry_date"] >= held_out_start)):
            ps = summarise([t for t in p_trades if sel(t)], n_trials)
            bs = summarise([t for t in b_trades if sel(t)])
            excess = (ps["net_r"] - bs["net_r"]) if ps.get("n") and bs.get("n") else None
            print(f"  {label:<9} picks     {_fmt(ps)}")
            print(f"  {'':<9} benchmark {_fmt(bs)}")
            if excess is not None:
                print(f"  {'':<9} picks minus benchmark: {excess:+.3f}R net per trade")

    if not args.skip_ic:
        print("\nMeasuring the ranking itself — daily rank IC of the pre-market long score vs that session's "
              "open->close return, every eligible stock (a measurement, not a strategy: no DSR trial)...")
        ics = daily_ranking_ic(raw, rows, sessions, config.SCANNER)
        cut = int(len(ics) * (1 - args.held_out_frac))
        for label, vals in (("all days", ics), (f"first {1 - args.held_out_frac:.0%}", ics[:cut]),
                            (f"last {args.held_out_frac:.0%}", ics[cut:])):
            s = ic_summary(vals)
            if s["mean_ic"] is None:
                print(f"  {label:<10} not enough days")
            else:
                t = f"{s['t_stat']:+.2f}" if s["t_stat"] is not None else "n/a"
                print(f"  {label:<10} days {s['days']}  mean IC {s['mean_ic']:+.4f}  t-stat {t}  "
                      f"days IC>0 {s['pct_positive']:.0f}%")

    print("\nLong-only; survivorship-biased universe (today's NIFTY 100 applied to history); R = "
          f"{'stop' if args.stop_atr else '2x daily ATR'} risk unit. R-multiples and DSR only — no expected "
          "return is implied. config.py unchanged.")


if __name__ == "__main__":
    main()
