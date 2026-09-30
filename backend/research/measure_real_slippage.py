"""Issue #66 — measure per-leg slippage from the recorded order book.

costs.py charges every symbol config.COSTS["slippage_pct"] per leg, a figure
config.py itself calls "a rough estimate, not measured". No real order has
been placed, so there are no fills. This reads the journal's order-book
samples (depth_samples), the entry-time liquidity checks (liquidity_checks)
and the checklist reads (checklist_evals) and reports, in basis points per
leg: the quoted half-spread, the cost of crossing the touch against the
signal price, and the impact of filling a realistic order size.

Read-only: the journal is opened with SQLite's mode=ro URI. It is a
measurement, not a strategy trial: no forward return or P&L is read.

What counts as a signal (one per symbol, side and 5-minute bar, first read):
  pass       every required checklist item passed on that side
  near-miss  exactly one required item failed (the lone blocker)
The reference price is the row's ltp, the price the engine saw when it read
the checklist.

TWO KINDS OF depth_samples ROW. Every row has the best bid and ask, the
quantity at level 1 and the summed quantity of five levels. Rows recorded
since #188 was deployed also carry each level's price and quantity
(bid_levels_json, ask_levels_json); rows from before it do not, and never
will. So a fill is one of:
  level1        the order fits at the touch: impact is exact (half-spread)
  recorded      it fits inside the recorded levels: walked on the real
                prices and quantities of levels 2-5 (a measurement)
  ladder        a row without recorded levels, and the order fits inside the
                five-level sum: the price is MODELLED by putting the rest of
                the quantity evenly on levels 2-5, one tick apart (tick = the
                symbol's smallest spread seen). A real book with gaps is worse
                than this; treat it as a floor.
  insufficient  five levels do not hold the size: counted, never extrapolated
The output counts each kind, so it says which rows were walked on real levels
and which on the model. liquidity_checks holds true five-level walks too, but
only for entries taken.

Usage:
  python research/measure_real_slippage.py --db /path/to/snapshot.db [--out result.json|.md]
"""
import argparse
import json
import math
import os
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_DB = os.environ.get("SAHAB_DB_PATH") or str(
    Path(__file__).resolve().parents[1] / "data" / "sahab_journal.db")
TABLES = ("depth_samples", "liquidity_checks", "checklist_evals")
NEED = {"depth_samples": {"ts", "symbol", "ltp", "bid", "ask", "bid_qty1", "ask_qty1", "bid_qty5", "ask_qty5"},
        "checklist_evals": {"ts", "symbol", "ltp", "checklist_json"}}
LEVELS = ("bid_levels_json", "ask_levels_json")    # since #188; optional, older rows are NULL
MEASURES = ("half_spread_bp", "cross_bp", "impact_bp")
MIN_SESSIONS, MIN_SIGNALS = 5, 30      # below either, no conclusion is offered


def day(ts):
    return datetime.fromtimestamp(ts, IST).strftime("%Y-%m-%d")


def walk(levels, qty):
    """Volume-weighted fill price of `qty` against [(price, quantity), ...]
    best first, or None when the levels do not hold it. Same arithmetic as
    liquidity._walk; not imported because that pulls in database.py."""
    left, cost = qty, 0.0
    for price, q in levels:
        take = min(left, q)
        cost += take * price
        left -= take
        if left <= 0:
            return cost / qty
    return None


def parse_levels(text):
    """[(price, quantity), ...] best first from a stored *_levels_json cell
    ([[price, quantity, orders], ...]), or None when the row has none (a row
    from before #188) or the cell cannot be read."""
    if not text:
        return None
    try:
        levels = [(float(lv[0]), float(lv[1])) for lv in json.loads(text) if lv[0] and lv[1]]
    except (TypeError, ValueError, IndexError):
        return None
    return levels or None


def ladder(best, qty1, qty5, tick, buy):
    """The modelled five levels: level 1 as recorded, the rest of the
    five-level quantity spread evenly over levels 2-5, one tick apart."""
    rest = max(qty5 - qty1, 0) / 4.0
    step = tick if buy else -tick
    return [(best, qty1)] + [(best + i * step, rest) for i in range(1, 5)]


def measure(bid, ask, bid_qty1, ask_qty1, bid_qty5, ask_qty5, side, qty, ref, tick, levels=None):
    """Costs of one leg in bp. side is "long" (buy at the ask) or "short"
    (sell at the bid). Positive = a cost. None for a crossed/empty book.
    `levels` is the recorded book of the side the order crosses, best first
    (the asks for a buy), or None for a row from before #188: an order past
    level 1 is then walked on the modelled ladder instead."""
    if not bid or not ask or ask < bid or not ref:
        return None
    mid = (bid + ask) / 2
    buy = side == "long"
    best, q1, q5 = (ask, ask_qty1 or 0, ask_qty5 or 0) if buy else (bid, bid_qty1 or 0, bid_qty5 or 0)
    out = {"half_spread_bp": (ask - bid) / 2 / mid * 1e4,
           "cross_bp": ((best - ref) if buy else (ref - best)) / ref * 1e4,
           "impact_bp": None}
    if qty <= 0:
        out["fill"] = "zero_qty"
    elif qty <= q1:
        out["fill"], out["impact_bp"] = "level1", out["half_spread_bp"]
    elif levels:
        vwap = walk(levels, qty)
        if vwap is None:
            out["fill"] = "insufficient"
        else:
            out["fill"], out["impact_bp"] = "recorded", abs(vwap - mid) / mid * 1e4
    elif qty <= q5:
        vwap = walk(ladder(best, q1, q5, tick, buy), qty)
        out["fill"] = "ladder"
        out["impact_bp"] = abs(vwap - mid) / mid * 1e4
    else:
        out["fill"] = "insufficient"
    return out


def engine_qty(side_json, price, capital, risk_pct, cap_pct):
    """The quantity the engine would have sized, rebuilt from the checklist's
    entry/stop/size_factor: risk-based, capped by notional, scaled by
    size_factor. None when the row carries no stop."""
    entry, stop = side_json.get("entry"), side_json.get("stop")
    if not entry or not stop or entry == stop or not price:
        return None
    by_risk = capital * risk_pct / 100 / abs(entry - stop)
    by_cap = capital * cap_pct / 100 / price
    return int(min(by_risk, by_cap) * (side_json.get("size_factor") or 1.0))


def pct(vals, p):
    """Percentile by linear interpolation; vals sorted."""
    if not vals:
        return None
    k = (len(vals) - 1) * p / 100
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)


def stats(vals):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return {"n": 0}
    return {"n": len(v), "median": pct(v, 50), "mean": st.mean(v),
            "p25": pct(v, 25), "p75": pct(v, 75), "p90": pct(v, 90)}


def columns(con, table):
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}


def inventory(con):
    out = {}
    for t in TABLES:
        cols = columns(con, t)
        if not cols:
            out[t] = {"exists": False}
            continue
        info = {"exists": True, "columns": sorted(cols), "rows": con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]}
        if {"ts", "symbol"} <= cols and info["rows"]:
            lo, hi, syms = con.execute(f"SELECT MIN(ts), MAX(ts), COUNT(DISTINCT symbol) FROM {t}").fetchone()
            days = {day(r[0]) for r in con.execute(f"SELECT DISTINCT CAST(ts/3600 AS INT)*3600 FROM {t}")}
            info.update(first=str(datetime.fromtimestamp(lo, IST)), last=str(datetime.fromtimestamp(hi, IST)),
                        symbols=syms, sessions=len(days), session_dates=sorted(days))
        out[t] = info
    return out


def load_samples(con):
    """{symbol: [(ts, ltp, bid, ask, bq1, aq1, bq5, aq5, bid_levels, ask_levels), ...]
    sorted by ts}, rows with a real two-sided book only (index rows carry a
    level, no book). bid_levels/ask_levels are parse_levels() of the recorded
    book, None for a row without one (every row of a journal from before #188)."""
    has_levels = set(LEVELS) <= columns(con, "depth_samples")
    book = defaultdict(list)
    for r in con.execute("SELECT symbol, ts, ltp, bid, ask, bid_qty1, ask_qty1, bid_qty5, ask_qty5, %s "
                         "FROM depth_samples WHERE bid > 0 AND ask >= bid ORDER BY symbol, ts"
                         % (", ".join(LEVELS) if has_levels else "NULL, NULL")):
        book[r[0]].append(tuple(r[1:9]) + (parse_levels(r[9]), parse_levels(r[10])))
    return book


def load_signals(con, universe):
    """One would-be entry per (symbol, side, bar): passes and lone-blocker near-misses."""
    has_bar = "bar_time" in columns(con, "checklist_evals")
    sql = "SELECT ts, symbol, ltp, checklist_json, %s FROM checklist_evals ORDER BY ts" % (
        "bar_time" if has_bar else "NULL")
    seen, out, bad = set(), [], 0
    for ts, symbol, ltp, cj, bar in con.execute(sql):
        if universe and symbol not in universe:
            continue
        # cheap pre-filter: a side with 2+ failing required items is most rows
        try:
            cl = json.loads(cj)
        except (TypeError, ValueError):
            bad += 1
            continue
        for side in ("long", "short"):
            s = cl.get(side) or {}
            req = [i for i in s.get("items") or [] if i.get("required")]
            failing = [i.get("key") for i in req if not i.get("ok")]
            if not req or len(failing) > 1:
                continue
            key = (symbol, side, bar or int(ts // 300))
            if key in seen:
                continue
            seen.add(key)
            out.append({"ts": ts, "symbol": symbol, "side": side, "ref": ltp, "json": s,
                        "kind": "pass" if not failing else "near-miss", "blocker": failing[0] if failing else None})
    return out, bad


def first_at_or_after(rows, ts):
    lo, hi = 0, len(rows)
    while lo < hi:
        m = (lo + hi) // 2
        if rows[m][0] < ts:
            lo = m + 1
        else:
            hi = m
    return rows[lo] if lo < len(rows) else None


def terciles(book):
    """Rank symbols by median five-level depth in rupees, (bid_qty5+ask_qty5)/2 x mid,
    most liquid first, and cut into three equal-count groups."""
    med = {s: st.median(((r[6] or 0) + (r[7] or 0)) / 2 * (r[2] + r[3]) / 2 for r in rows)
           for s, rows in book.items()}
    ranked = sorted(med, key=med.get, reverse=True)
    n = len(ranked)
    names = ("T1 most liquid", "T2 middle", "T3 least liquid")
    return {s: names[min(i * 3 // n, 2)] for i, s in enumerate(ranked)}, med


def summarise(recs):
    """recs: dicts with symbol, day, tercile, fill and the three measures."""
    out = {}
    groups = defaultdict(list)
    for r in recs:
        groups[r["tercile"]].append(r)
        groups["ALL"].append(r)
    for g, rs in groups.items():
        fills = defaultdict(int)
        for r in rs:
            fills[r["fill"]] += 1
        out[g] = {"n": len(rs), "sessions": len({r["day"] for r in rs}), "symbols": len({r["symbol"] for r in rs}),
                  "fills": dict(fills), **{m: stats([r[m] for r in rs]) for m in MEASURES}}
    return out


def table(title, summary, say):
    say(f"\n=== {title} ===")
    if not summary:
        say("  (no rows)")
        return
    say(f"  {'group':<16}{'measure':<16}{'n':>8}{'median':>9}{'mean':>9}{'p25':>9}{'p75':>9}{'p90':>9}")
    for g in ("T1 most liquid", "T2 middle", "T3 least liquid", "ALL"):
        S = summary.get(g)
        if not S:
            continue
        f = S["fills"]
        say(f"  {g}: legs={S['n']:,} sessions={S['sessions']} symbols={S['symbols']}  "
            f"fill at level1={f.get('level1', 0):,} walked recorded levels={f.get('recorded', 0):,} "
            f"modelled ladder={f.get('ladder', 0):,} "
            f"five levels insufficient={f.get('insufficient', 0):,} zero qty={f.get('zero_qty', 0):,}")
        for m in MEASURES:
            x = S[m]
            if not x["n"]:
                say(f"  {'':<16}{m:<16}{0:>8}")
                continue
            say(f"  {'':<16}{m:<16}{x['n']:>8,}{x['median']:>9.2f}{x['mean']:>9.2f}"
                f"{x['p25']:>9.2f}{x['p75']:>9.2f}{x['p90']:>9.2f}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=DEFAULT_DB, help="journal to read (opened read-only); use a snapshot")
    ap.add_argument("--max-gap", type=float, default=60.0, help="seconds from signal to the first book sample")
    ap.add_argument("--notional", type=float, default=None,
                    help="order value in Rs when the signal carries no stop, and for all-sample rows "
                         "(default: RISK total_capital x max_position_notional_pct)")
    ap.add_argument("--universe", default=None, help="comma-separated symbols to keep (default: all in the data)")
    ap.add_argument("--out", default=None, help="write the result to this .json or .md file")
    a = ap.parse_args(argv)

    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    capital = config.RISK["total_capital"]
    cap_pct = config.RISK["max_position_notional_pct"]
    risk_pct = config.RISK["max_risk_per_trade_pct"]
    notional = a.notional or capital * cap_pct / 100
    assumed_bp = config.COSTS["slippage_pct"] * 100
    universe = {s.strip().upper() for s in a.universe.split(",")} if a.universe else None

    if not Path(a.db).exists():
        sys.exit(f"No database at {a.db}")
    con = sqlite3.connect("file:" + str(Path(a.db).resolve()) + "?mode=ro", uri=True)

    inv = inventory(con)
    say(f"Database: {a.db} (read-only)")
    say("\n=== WHAT DATA EXISTS ===")
    for t, i in inv.items():
        if not i["exists"]:
            say(f"  {t}: table missing")
        elif "sessions" not in i:
            say(f"  {t}: {i['rows']:,} rows")
        else:
            say(f"  {t}: {i['rows']:,} rows, {i['symbols']} symbols, {i['sessions']} sessions "
                f"{i['session_dates']}, {i['first']} -> {i['last']}")
    for t, need in NEED.items():
        missing = need - set(inv[t].get("columns", []))
        if missing:
            sys.exit(f"\nCannot measure: {t} is missing {sorted(missing)}.")

    book = load_samples(con)
    if universe:
        book = {s: r for s, r in book.items() if s in universe}
    n_samples = sum(len(r) for r in book.values())
    if len(book) < 3 or not n_samples:
        sys.exit(f"\nToo little data: {n_samples} two-sided book samples over {len(book)} symbols; "
                 "three symbols are needed to form terciles.")
    sample_days = sorted({day(r[0]) for rows in book.values() for r in rows})
    with_levels = sum(1 for rows in book.values() for r in rows if r[8] and r[9])

    tercile, depth_rs = terciles(book)
    tick = {s: max(min([round(r[3] - r[2], 2) for r in rows if r[3] > r[2]] or [0.05]), 0.01)
            for s, rows in book.items()}
    say(f"\nTwo-sided book samples used: {n_samples:,} over {len(book)} symbols, sessions {sample_days}")
    say(f"Samples with the book recorded level by level (#188): {with_levels:,} of {n_samples:,}. "
        "An order past level 1 is walked on the recorded levels in those, and on the modelled "
        "one-tick ladder in the rest.")
    say("Liquidity measure: each symbol's median five-level depth in rupees, (bid_qty5+ask_qty5)/2 x mid.")
    for name in ("T1 most liquid", "T2 middle", "T3 least liquid"):
        d = sorted(depth_rs[s] for s in book if tercile[s] == name)
        say(f"  {name}: {len(d)} symbols, median depth Rs {st.median(d):,.0f} (range Rs {d[0]:,.0f} - {d[-1]:,.0f})")

    # ---- signals matched to the book -------------------------------------
    signals, bad_json = load_signals(con, universe)
    recs, dropped_gap, no_samples, sized = [], 0, 0, {"engine": 0, "notional": 0}
    kinds = defaultdict(int)
    for s in signals:
        rows = book.get(s["symbol"])
        if not rows:
            no_samples += 1
            continue
        hit = first_at_or_after(rows, s["ts"])
        if hit is None or hit[0] - s["ts"] > a.max_gap:
            dropped_gap += 1
            continue
        _, _ltp, bid, ask, bq1, aq1, bq5, aq5, bid_lv, ask_lv = hit
        qty = engine_qty(s["json"], s["ref"], capital, risk_pct, cap_pct)
        how = "engine"
        if qty is None:
            qty, how = int(notional / ((bid + ask) / 2)), "notional"
        m = measure(bid, ask, bq1, aq1, bq5, aq5, s["side"], qty, s["ref"], tick[s["symbol"]],
                    levels=ask_lv if s["side"] == "long" else bid_lv)
        if m is None:
            continue
        sized[how] += 1
        kinds[s["kind"]] += 1
        recs.append({"symbol": s["symbol"], "day": day(s["ts"]), "tercile": tercile[s["symbol"]],
                     "kind": s["kind"], "side": s["side"], "qty": qty, "gap_s": hit[0] - s["ts"], **m})
    say(f"\nSignals (passes + lone-blocker near-misses, one per symbol/side/bar): {len(signals):,}"
        f"  [unreadable checklist rows skipped: {bad_json}]")
    say(f"  dropped, symbol has no book samples at all: {no_samples:,}")
    say(f"  dropped, no book sample within {a.max_gap:g}s after the signal: {dropped_gap:,}")
    say(f"  matched: {len(recs):,}  ({dict(kinds)})")
    say(f"  order size: {sized['engine']:,} rebuilt from the row's entry/stop/size_factor "
        f"(capital Rs {capital:,.0f}, {risk_pct:g}% risk, {cap_pct:g}% notional cap); "
        f"{sized['notional']:,} at the Rs {notional:,.0f} notional fallback")
    sig_sum = summarise(recs)
    table("A. SIGNAL-MATCHED LEGS (per leg, bp)", sig_sum, say)
    pass_sum = summarise([r for r in recs if r["kind"] == "pass"])
    table("A2. of which FULL PASSES only", pass_sum, say)

    # ---- every book sample, both sides -----------------------------------
    allrecs = []
    for sym, rows in book.items():
        for ts, ltp, bid, ask, bq1, aq1, bq5, aq5, bid_lv, ask_lv in rows:
            qty = int(notional / ((bid + ask) / 2))
            for side in ("long", "short"):
                m = measure(bid, ask, bq1, aq1, bq5, aq5, side, qty, ltp or (bid + ask) / 2, tick[sym],
                            levels=ask_lv if side == "long" else bid_lv)
                if m:
                    allrecs.append({"symbol": sym, "day": day(ts), "tercile": tercile[sym], **m})
    all_sum = summarise(allrecs)
    table(f"B. ALL BOOK SAMPLES, a buy and a sell leg each, Rs {notional:,.0f} order, reference = the sample's ltp "
          "(per leg, bp)", all_sum, say)

    # ---- the only true five-level walks ----------------------------------
    lc = []
    if {"impact_bp", "spread_bp", "status"} <= set(inv["liquidity_checks"].get("columns", [])):
        lc = con.execute("SELECT symbol, side, qty, spread_bp, impact_bp FROM liquidity_checks "
                         "WHERE status='checked' AND impact_bp IS NOT NULL").fetchall()
    say(f"\n=== C. liquidity_checks: TRUE five-level walks at entries taken, n={len(lc)} ===")
    for r in lc:
        say(f"  {r[0]:<12}{r[1]:<6} qty {r[2]:>5}  spread {r[3]:.2f} bp  impact {r[4]:.2f} bp from mid")
    con.close()

    # ---- conclusion -------------------------------------------------------
    say(f"\n=== CONCLUSION (per leg; the cost model assumes {assumed_bp:g} bp for every symbol) ===")
    say(f"  {'group':<18}{'signals: median / p90 impact':<32}{'all samples: median / p90 impact':<34}")
    for g in ("T1 most liquid", "T2 middle", "T3 least liquid", "ALL"):
        def cell(S):
            x = (S.get(g) or {}).get("impact_bp") or {"n": 0}
            return f"{x['median']:.2f} / {x['p90']:.2f} bp (n={x['n']:,})" if x["n"] else "no data"
        say(f"  {g:<18}{cell(sig_sum):<32}{cell(all_sum):<34}")
    thin = []
    if len(sample_days) < MIN_SESSIONS:
        thin.append(f"the book covers {len(sample_days)} session(s), under the {MIN_SESSIONS} this script asks for")
    if len(recs) < MIN_SIGNALS:
        thin.append(f"{len(recs)} matched signals, under {MIN_SIGNALS}")
    if kinds.get("pass", 0) < MIN_SIGNALS:
        thin.append(f"only {kinds.get('pass', 0)} of them are full passes")
    if thin:
        say("\n  TOO LITTLE DATA FOR A CONCLUSION: " + "; ".join(thin) + ".")
        say(f"  The figures above are a first reading. They do not support replacing the {assumed_bp:g} bp yet.")
    say("\n  What this can support: the quoted half-spread and the touch-crossing cost at the moments sampled,")
    say("  and whether five levels held the order size. Those are observations of the book, per symbol group.")
    say("  What it cannot support:")
    say("   - These are snapshots, not executed fills. No real order has ever been placed.")
    say("   - A MARKET order's real fill can be worse: latency between signal and order, queue position,")
    say("     and the book moving (or being pulled) before the order arrives.")
    if with_levels < n_samples:
        say(f"   - {n_samples - with_levels:,} of {n_samples:,} book samples predate #188 and have no prices for")
        say("     levels 2-5, so an impact beyond level 1 on those rows is MODELLED on a one-tick ladder and is a")
        say("     floor, not a measurement (fill 'modelled ladder'). Rows counted under 'walked recorded levels'")
        say("     and section C walk real levels.")
    else:
        say("   - Every book sample carries its recorded levels: impact beyond level 1 is walked on real prices.")
    say("   - cross_bp compares against ltp, a last trade that may be stale or on either side of the book;")
    say("     it can be negative. The sample is taken up to --max-gap seconds after the signal.")
    say(f"   - The samples cover {len(sample_days)} session(s) ({sample_days[0]} -> {sample_days[-1]}); that window may not be")
    say("     representative (no expiry day, event day or stressed open is known to be in it).")
    say("   - Exit legs (stops in a fast market) are likely costlier than the entry-time books measured here.")

    if a.out:
        if a.out.endswith(".json"):
            Path(a.out).write_text(json.dumps({
                "db": a.db, "assumed_bp_per_leg": assumed_bp, "max_gap_s": a.max_gap, "notional": notional,
                "book_samples": n_samples, "book_samples_with_levels": with_levels,
                "inventory": inv, "signals": {"found": len(signals), "matched": len(recs), "kinds": dict(kinds),
                                              "dropped_gap": dropped_gap, "no_samples": no_samples, "sized": sized},
                "signal_matched": sig_sum, "full_passes": pass_sum, "all_samples": all_sum,
                "liquidity_checks": [list(r) for r in lc], "too_thin": thin}, indent=2, default=str))
        else:
            Path(a.out).write_text("```\n" + "\n".join(lines) + "\n```\n")
        print(f"\nwrote {a.out}")
    return {"signal_matched": sig_sum, "all_samples": all_sum, "dropped_gap": dropped_gap,
            "matched": recs, "too_thin": thin, "book_samples": n_samples, "book_samples_with_levels": with_levels}


if __name__ == "__main__":
    main()
