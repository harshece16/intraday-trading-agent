"""Trials 208 and 209: selling NIFTY option premium with defined risk, held to expiry.

Rules, samples and the pass rule are fixed in docs/research/prereg-index-premium.md,
written and merged before this file. The option history is the expiry-day extract that
fo_options_aggregate.py builds on sahab-pc (backend/data/fo_oi/, gitignored).

    python research/index_premium.py selftest   # strike, payoff, cost and verdict logic on made-up data
    python research/index_premium.py stage0     # data gate: counts and source checks, no P&L
    python research/index_premium.py trial      # both arms, one run each, logged as trials
"""
import collections
import csv
import datetime as dt
import gzip
import itertools
import json
import math
import os
import pathlib
import statistics as st
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, BACKEND)

import insider_buys as ib  # noqa: E402  (write() and OUT_DIR)
import nse_prices  # noqa: E402  (the cash calendar; DATA honours SAHAB_RESEARCH_DATA)
from costs import FNO_OPTION_COSTS, leg_cost  # noqa: E402
from pead_stage_a import nw_t  # noqa: E402

OPT_FILE = os.path.join(nse_prices.DATA, "fo_oi", "fo_opt_expiry.csv.gz")
FIRST, LAST_EXIT = "2009-01-01", "2025-12-31"
HALF_SPLIT, LAST3_START = "2017-07-01", "2023-01-01"
FAMILY_N, FAMILY_T, MIN_DSR = 2, 2.24, 0.95
MIN_CYCLES, MIN_CONTRACTS, SHORT_DAYS, NW_LAGS = 100, 100, 10, 4
SD, WING, HOLE = 1.25, 1.875, 0.75     # in straddles: one standard deviation, one and a half, the widest hole
REF_DAY, REF_NIFTY = "2025-12-30", 25938.85    # costs are charged at this day's index level
LOT = {"NIFTY": 65, "BANKNIFTY": 30}           # the lots since January 2026
ARMS = {"208": "condor", "209": "straddle"}
LABELS = {"208": "trial 208 NIFTY front-cycle iron condor, held to expiry",
          "209": "trial 209 NIFTY front-cycle hedged straddle, held to expiry"}


def _f(text):
    try:
        return float(text)
    except ValueError:
        return 0.0


def gap_days(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


# --- the extract ------------------------------------------------------------------

def day_record(date, rows):
    """One index on one of its expiry days. rows are extract rows without date and symbol:
    (kind, expiry, expiry2, strike, close, settle, vol, val, oi, und, lot, fmt)."""
    opts = [r for r in rows if r[0] != "F"]
    futs = sorted((r for r in rows if r[0] == "F"), key=lambda r: r[1])
    actual = {r[1] for r in opts if r[2] == date}            # UDiFF names the actual expiry date
    exp = min(actual) if actual else min(r[1] for r in opts if r[1] >= date)
    later = [r[1] for r in opts if r[1] > exp]
    expiring = [r for r in opts if r[1] == exp]
    und = {_f(r[9]) for r in expiring} - {0.0}
    settles = {_f(r[5]) for r in expiring}                   # "the one value every expiring row carries"
    fut = [_f(r[5]) for r in futs if r[1] == exp or r[2] == date]
    chain = {}
    for r in opts:
        if later and r[1] == min(later):
            chain.setdefault(_f(r[3]), {})[r[0]] = (_f(r[4]), _f(r[6]), _f(r[10]))   # close, volume, lot
    return {"exp": exp, "front": min(later) if later else None, "fmt": rows[0][11],
            "und": und.pop() if len(und) == 1 else None, "fut": fut[0] if fut else None,
            "opt": settles.pop() if len(settles) == 1 else None,
            "near_fut": _f(futs[0][4]) if futs else None, "chain": chain,
            "exp2_differs": sum(1 for r in opts if r[2] and r[2] != r[1])}


def load(path=OPT_FILE):
    """({symbol: {expiry day: record}}, futures rows for the volume-unit check). 2026 is never read."""
    days, samples = {}, []
    with gzip.open(path, "rt", newline="") as fh:
        rd = csv.reader(fh)
        next(rd)
        for (date, sym), grp in itertools.groupby(rd, key=lambda r: (r[0], r[1])):
            rows = [r[2:] for r in grp]
            if not FIRST <= date <= LAST_EXIT:
                continue
            days.setdefault(sym, {})[date] = day_record(date, rows)
            samples += [(r[11], _f(r[7]), _f(r[6]), _f(r[4]), _f(r[10])) for r in rows if r[0] == "F"]
    return days, samples


def volume_unit(samples):
    """Stage 0 item 5: is UDiFF's TtlTradgVol in contracts or in units? On a futures row
    turnover / (volume x close) is 1 when volume counts units and the lot when it counts contracts
    (times 1e-5 when turnover is in lakh). UDiFF rows carry the lot; the old format's CONTRACTS is the control."""
    votes, old = collections.Counter(), []
    for fmt, val, vol, close, lot in samples:
        if val <= 0 or vol <= 0 or close <= 0:
            continue
        a = val / (vol * close)
        a = a * 1e5 if a < 0.01 else a
        if fmt == "old":
            old.append(a)
        elif abs(a - 1) < 0.05:
            votes["units"] += 1
        elif lot > 0 and abs(a / lot - 1) < 0.05:
            votes["contracts"] += 1
        else:
            votes["unclear"] += 1
    total = sum(votes.values())
    unit = next((u for u in ("units", "contracts") if total and votes[u] >= 0.95 * total), None)
    return {"unit": unit, "udiff_votes": dict(votes),
            "old_format_median_turnover_per_contract_in_units": round(st.median(old), 2) if old else None}


def to_contracts(days, unit):
    """Chain legs become (close, contracts traded)."""
    for recs in days.values():
        for rec in recs.values():
            div = rec["fmt"] == "udiff" and unit == "units"
            rec["chain"] = {k: {t: (c, (v / lot if lot > 0 else 0.0) if div else v) for t, (c, v, lot) in legs.items()}
                            for k, legs in rec["chain"].items()}


# --- the rules --------------------------------------------------------------------

def cycles(recs):
    """([(entry day, expiry day)], re-linked). From the first expiry day, each cycle holds the front
    series (the nearest one listed after the series expiring on the entry day) to the day it expires
    and the next cycle starts there: no overlap, and the chain ignores whether a trade can be built."""
    days = sorted(recs)
    ends = {recs[d]["exp"]: d for d in days}                 # a series' listed expiry -> the day it expired
    out, relinked, day = [], [], days[0]
    while recs[day]["front"] and recs[day]["front"] <= LAST_EXIT:
        front = recs[day]["front"]
        end = ends.get(front)
        if end is None or end <= day:
            # the listed date changed after the entry day: the expiry day nearest to it, within four days
            near = [d for d in days if d > day and abs(gap_days(d, front)) <= 4]
            if not near:
                raise SystemExit("no expiry day for the series listed as %s on %s" % (front, day))
            end = min(near, key=lambda d: abs(gap_days(d, front)))
            relinked.append([day, front, end])
        out.append((day, end))
        day = end
    return out, relinked


def settlement(rec):
    """(final settlement price, source): the UDiFF underlying value, else the settle price of the
    future expiring that day, else the one value every expiring option row carries."""
    for src in ("und", "fut", "opt"):
        if rec[src] and rec[src] > 0:
            return rec[src], src
    return None, None


def liquid(leg):
    return leg is not None and leg[1] >= MIN_CONTRACTS and leg[0] > 0


def forward(chain):
    """(K0, F, S0, strikes with a liquid call and put) or None."""
    both = sorted(k for k, legs in chain.items() if liquid(legs.get("CE")) and liquid(legs.get("PE")))
    if not both:
        return None
    k0 = min(both, key=lambda k: (abs(chain[k]["CE"][0] - chain[k]["PE"][0]), k))
    c, p = chain[k0]["CE"][0], chain[k0]["PE"][0]
    return k0, k0 + c - p, c + p, both


def build(chain, arm):
    """(trade, None) or (None, skip reason), from the entry day's front chain alone."""
    fw = forward(chain)
    if fw is None:
        return None, "no_k0"
    k0, f, s0, _ = fw
    calls = sorted(k for k, legs in chain.items() if liquid(legs.get("CE")))
    puts = sorted((k for k, legs in chain.items() if liquid(legs.get("PE"))), reverse=True)
    up = lambda at, above: next((k for k in calls if k >= at and k > above), None)  # noqa: E731
    down = lambda at, below: next((k for k in puts if k <= at and k < below), None)  # noqa: E731
    if arm == "condor":
        sc, sp = up(f + SD * s0, -math.inf), down(f - SD * s0, math.inf)
        bc = up(f + WING * s0, sc) if sc is not None else None
        bp = down(f - WING * s0, sp) if sp is not None else None
        marks = [(sc, f + SD * s0), (sp, f - SD * s0), (bc, f + WING * s0), (bp, f - WING * s0)]
    else:
        sc = sp = k0
        bc, bp = up(f + SD * s0, -math.inf), down(f - SD * s0, math.inf)
        marks = [(bc, f + SD * s0), (bp, f - SD * s0)]
    if any(k is None for k, _ in marks):
        return None, "no_leg"
    if any(abs(k - at) > HOLE * s0 for k, at in marks):
        return None, "hole"
    prem = {"sc": chain[sc]["CE"][0], "bc": chain[bc]["CE"][0], "sp": chain[sp]["PE"][0], "bp": chain[bp]["PE"][0]}
    credit = prem["sc"] + prem["sp"] - prem["bc"] - prem["bp"]
    max_loss = max(bc - sc, sp - bp) - credit
    if prem["bc"] >= prem["sc"] or prem["bp"] >= prem["sp"] or credit <= 0 or max_loss <= 0:
        return None, "bad_quote"
    return {"k0": k0, "f": f, "s0": s0, "sc": sc, "bc": bc, "sp": sp, "bp": bp, "prem": prem,
            "credit": credit, "max_loss": max_loss}, None


def price(t, settle, ref, lot):
    """{"call": (gross, cost), "put": (gross, cost)} in index points, costs at 1x."""
    k = ref / t["f"]                                         # today's index level over the cycle's

    def fee(side, value):                                    # one order of today's lot, back in points
        return leg_cost(side, value * k, lot, FNO_OPTION_COSTS) / (lot * k)

    out = {}
    for name, sold, bought, sign in (("call", "sc", "bc", 1), ("put", "sp", "bp", -1)):
        gross = cost = 0.0
        for leg, received in ((sold, 1), (bought, -1)):      # +1: the premium is received at entry
            prem, worth = t["prem"][leg], max(0.0, sign * (settle - t[leg]))
            gross += received * (prem - worth)
            cost += fee("SELL" if received > 0 else "BUY", prem) + max(0.01 * prem, 0.25 / k, 0.05)
            if worth > 0:                                    # settled in the money: one more order at intrinsic value
                cost += fee("BUY" if received > 0 else "SELL", worth)
        out[name] = (gross, cost)
    return out


def run_arm(recs, cyc, arm, bad_days, ref=None, lot=None):
    """(cycles kept, skips, skipped). Without ref (stage 0) nothing is priced: the entry chain decides
    the strikes, the expiry day is asked only whether it has a settlement price."""
    rows, skips, skipped = [], collections.Counter(), []
    for day, end in cyc:
        t, why = (None, "missing_file") if day in bad_days or end in bad_days else build(recs[day]["chain"], arm)
        settle = None if why else settlement(recs[end])[0]
        why = why or (None if settle else "no_settlement")
        if why:
            skips[why] += 1
            skipped.append([day, why])
            continue
        row = {"entry": day, "expiry": end, "days": gap_days(day, end)}
        if ref:
            side = price(t, settle, ref, lot)
            gross, cost, ml = side["call"][0] + side["put"][0], side["call"][1] + side["put"][1], t["max_loss"]
            row.update({"f": t["f"], "s0": t["s0"], "bp_strike": t["bp"], "sp_strike": t["sp"], "sc_strike": t["sc"],
                        "bc_strike": t["bc"], "credit": t["credit"], "max_loss": ml, "settle": settle,
                        "gross": gross, "cost": cost, "r": (gross - cost) / ml, "r2": (gross - 2 * cost) / ml,
                        "r3": (gross - 3 * cost) / ml, "r_gross": gross / ml, "r_cost": cost / ml,
                        "r_call": (side["call"][0] - side["call"][1]) / ml,
                        "r_put": (side["put"][0] - side["put"][1]) / ml, "bp": (gross - cost) / t["f"] * 1e4})
        rows.append(row)
    return rows, dict(skips), skipped


# --- stage 0 ----------------------------------------------------------------------

def stage0(days, unit, sessions, meta):
    cash = {s for s in sessions if FIRST <= s <= LAST_EXIT}
    out = {"files": {"per_format": meta["files_per_format"], "bad_files": meta["bad_files"],
                     "fo_sessions": len(meta["sessions"]), "cash_sessions": len(cash),
                     "cash_sessions_without_a_file": sorted(cash - set(meta["sessions"]))},
           "volume_unit": unit, "symbols": {}}
    for sym, recs in sorted(days.items()):
        cyc, relinked = cycles(recs)
        moved = [[d, r["exp"]] for d, r in sorted(recs.items()) if r["exp"] != d]
        bad_days = sorted(d for d, e in moved if e in cash)   # the listed expiry was a session: its file is missing
        ends = [end for _, end in cyc]
        srcs, two, agree, disagree, far = collections.Counter(), 0, 0, [], []
        for d in ends:
            rec = recs[d]
            s, src = settlement(rec)
            if s is None:
                continue
            srcs[src] += 1
            vals = [rec[k] for k in ("und", "fut", "opt") if rec[k] and rec[k] > 0]
            if len(vals) > 1:
                two += 1
                if max(vals) / min(vals) - 1 <= 0.0005:
                    agree += 1
                else:
                    disagree.append([d, vals])
            if not rec["near_fut"] or abs(s / rec["near_fut"] - 1) > 0.01:
                far.append([d, s, rec["near_fut"]])
        gaps, unchecked = [], 0
        for day, _ in cyc:                                   # check 4: the forward one strike either side of K0
            chain = recs[day]["chain"]
            fw = forward(chain)
            if fw is None:
                continue
            k0, f, _s0, both = fw
            i = both.index(k0)
            near = both[max(0, i - 1):i] + both[i + 1:i + 2]
            if not near:
                unchecked += 1
                continue
            gaps.append(max(abs(k + chain[k]["CE"][0] - chain[k]["PE"][0] - f) for k in near) / f)
        have = sum(srcs.values())
        short = [c for c in cyc if gap_days(*c) <= SHORT_DAYS]
        gates = {"3_settlement_present": bool(ends) and have >= 0.98 * len(ends),
                 "3_sources_agree": two == 0 or agree >= 0.99 * two,
                 "3_near_future_close": not far,
                 "4_forward_median": bool(gaps) and st.median(gaps) <= 0.001,
                 "4_forward_within": bool(gaps) and sum(g <= 0.003 for g in gaps) >= 0.95 * (len(gaps) + unchecked)}
        arms = {}
        for num, arm in ARMS.items():
            rows, skips, skipped = run_arm(recs, cyc, arm, set(bad_days))
            arms[num] = {"buildable": len(rows), "buildable_short": sum(r["days"] <= SHORT_DAYS for r in rows),
                         "skips": skips, "skipped": skipped}
        ref = settlement(recs[REF_DAY])[0] if REF_DAY in recs else None
        out["symbols"][sym] = {
            "expiry_days": len(recs), "moved": moved, "missing_file_expiries": bad_days, "relinked": relinked,
            "rows_where_actual_expiry_differs": {d: r["exp2_differs"] for d, r in sorted(recs.items()) if r["exp2_differs"]},
            "cycles": len(cyc), "first_entry": cyc[0][0], "last_expiry": cyc[-1][1],
            "short_cycles": len(short), "first_short_cycle": short[0] if short else None,
            "cycles_per_year": dict(sorted(collections.Counter(c[0][:4] for c in cyc).items())),
            "settlement": {"present": have, "by_source": dict(srcs), "days_with_two_sources": two,
                           "agree_within_0.05pct": agree, "disagree": disagree, "beyond_1pct_of_near_future": far},
            "entry_quotes": {"checked": len(gaps), "no_neighbour": unchecked,
                             "median_gap": st.median(gaps) if gaps else None,
                             "within_0.3pct": sum(g <= 0.003 for g in gaps),
                             "worst": sorted(gaps)[-5:]},
            "arms": arms, "gates": gates, "data_ok": all(gates.values()), "ref_level": ref,
            "cycle_list": cyc}
    nifty = out["symbols"]["NIFTY"]
    assert nifty["ref_level"] is not None and abs(nifty["ref_level"] - REF_NIFTY) < 0.01, nifty["ref_level"]
    out["proceed"] = {num: bool(unit["unit"]) and nifty["data_ok"] and nifty["arms"][num]["buildable"] >= MIN_CYCLES
                      for num in ARMS}
    return out


# --- the verdict ------------------------------------------------------------------

def tstat(xs):
    """(t, plain, Newey-West): t is the smaller in size of the two."""
    plain = st.mean(xs) / (st.stdev(xs) / math.sqrt(len(xs)))
    nw = nw_t(xs, NW_LAGS)
    return min((t for t in (plain, nw) if t is not None), key=abs), plain, nw


def summ(xs):
    return {"n": len(xs), "mean_r": st.mean(xs) if xs else None}


def report(rows):
    """Every figure the prereg asks of one arm on one index. rows are priced cycles in entry order."""
    import evaluation
    xs = [r["r"] for r in rows]
    if len(xs) < 3 or st.stdev(xs) == 0:
        return {"cycles": len(xs)}
    t, plain, nw = tstat(xs)
    part = lambda pred: summ([r["r"] for r in rows if pred(r)])  # noqa: E731
    avg = lambda key: st.mean(r[key] for r in rows)  # noqa: E731
    wins, losses = [x for x in xs if x > 0], [x for x in xs if x <= 0]
    run = worst_run = 0
    total = peak = drawdown = 0.0
    for x in xs:
        run = run + 1 if x <= 0 else 0
        worst_run = max(worst_run, run)
        total += x
        peak = max(peak, total)
        drawdown = min(drawdown, total - peak)
    return {
        "cycles": len(xs), "mean_r": st.mean(xs), "sd_r": st.stdev(xs), "t": t, "t_plain": plain, "t_nw4": nw,
        "dsr": evaluation.deflated_sharpe_ratio(xs, FAMILY_N),
        "mean_r_gross": avg("r_gross"), "mean_r_2x": avg("r2"), "mean_r_3x": avg("r3"),
        "break_even_cost_multiple": avg("r_gross") / avg("r_cost"),
        "s1": part(lambda r: r["entry"] < HALF_SPLIT), "s2": part(lambda r: r["entry"] >= HALF_SPLIT),
        "last3": part(lambda r: r["entry"] >= LAST3_START),
        "short": part(lambda r: r["days"] <= SHORT_DAYS), "long": part(lambda r: r["days"] > SHORT_DAYS),
        "call_side_mean_r": avg("r_call"), "put_side_mean_r": avg("r_put"),
        "win_rate": len(wins) / len(xs), "mean_win": st.mean(wins) if wins else None,
        "mean_loss": st.mean(losses) if losses else None,
        "worst5": [[r["entry"], r["expiry"], r["r"]] for r in sorted(rows, key=lambda r: r["r"])[:5]],
        "longest_losing_run": worst_run, "deepest_drawdown_r": drawdown, "total_r": total,
        "by_year": {y: part(lambda r, y=y: r["entry"][:4] == y) for y in sorted({r["entry"][:4] for r in rows})},
        "credit_share_of_max_loss": st.mean(r["credit"] / r["max_loss"] for r in rows),
        "cost_share_of_credit": st.mean(r["cost"] / r["credit"] for r in rows),
        "mean_bp_of_forward": avg("bp"),
    }


def verdict(rep, bank):
    """The eight gates of one arm. bank is BANKNIFTY's report for the same arm, {} if its data gate failed."""
    pos = lambda x: x is not None and x > 0  # noqa: E731
    m = lambda key: (rep.get(key) or {}).get("mean_r")  # noqa: E731
    checks = {
        "1_mean_positive_t": pos(rep.get("mean_r")) and (rep.get("t") or 0) >= FAMILY_T,
        "2_dsr": ((rep.get("dsr") or {}).get("dsr") or 0) >= MIN_DSR,
        "3_both_halves": pos(m("s1")) and pos(m("s2")),
        "4_last_three_years": pos(m("last3")),
        "5_short_cycles": pos(m("short")),
        "6_costs_2x": pos(rep.get("mean_r_2x")),
        "7_cycles": rep.get("cycles", 0) >= MIN_CYCLES,
        "8_banknifty": pos(bank.get("mean_r")),
    }
    return {"checks": checks, "pass": all(checks.values())}


def mechanism(recs, cyc, bad_days):
    """Reported, not judged: how often the index finished beyond one and one and a half standard
    deviations of the move the straddle priced in, against 31.7% and 13.4% for a normal move."""
    moves = []
    for day, end in cyc:
        fw, settle = forward(recs[day]["chain"]), settlement(recs[end])[0]
        if fw and settle and day not in bad_days and end not in bad_days:
            moves.append((settle - fw[1]) / fw[2])
    share = lambda pred: sum(1 for m in moves if pred(m)) / len(moves) if moves else None  # noqa: E731
    return {"cycles": len(moves), "beyond_1sd": share(lambda m: abs(m) > SD), "normal_1sd": 0.3173,
            "beyond_1_5sd": share(lambda m: abs(m) > WING), "normal_1_5sd": 0.1336,
            "above_1sd": share(lambda m: m > SD), "below_1sd": share(lambda m: m < -SD)}


def trial(days, s0):
    """Both arms on both indices: (result, one row per priced cycle). Nothing is logged or saved here."""
    out, detail = {"proceed": s0["proceed"], "arms": {}, "mechanism": {}}, []
    cyc = {sym: cycles(recs)[0] for sym, recs in days.items()}
    bad = {sym: set(s0["symbols"][sym]["missing_file_expiries"]) for sym in days}
    for num, arm in ARMS.items():
        if not s0["proceed"][num]:
            out["arms"][num] = {"label": LABELS[num], "not_run": "stage 0 stop rule", "pass": False}
            continue
        per = {}
        for sym in sorted(days):
            rows, skips, _ = run_arm(days[sym], cyc[sym], arm, bad[sym], s0["symbols"][sym]["ref_level"], LOT[sym])
            per[sym] = dict(report(rows), skips=skips)
            detail += [dict({"trial": num, "symbol": sym}, **r) for r in rows]
        res = verdict(per["NIFTY"], per["BANKNIFTY"] if s0["symbols"]["BANKNIFTY"]["data_ok"] else {})
        res.update({"label": LABELS[num], "NIFTY": per["NIFTY"], "BANKNIFTY": per["BANKNIFTY"]})
        out["arms"][num] = res
    if detail:
        out["mechanism"] = {sym: mechanism(days[sym], cyc[sym], bad[sym]) for sym in sorted(days)}
    return out, detail


def save_cycles(detail, path):
    if detail:
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(detail[0]))
            w.writeheader()
            w.writerows(rounded(detail, 4))


def rounded(o, n=5):
    if isinstance(o, float):
        return round(o, n)
    if isinstance(o, dict):
        return {k: rounded(v, n) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [rounded(v, n) for v in o]
    return o


def selftest():
    # --- strikes, payoff and costs on a chain with F = 10,000 and S0 = 400 (time value by distance from the money)
    tv = {0: 200, 100: 160, 200: 125, 300: 95, 400: 70, 500: 50, 600: 34, 700: 22, 800: 14, 900: 8, 1000: 4}
    chain = {10000.0 + d * s: {"CE": (max(0, -d * s) + v, 500), "PE": (max(0, d * s) + v, 500)}
             for d, v in tv.items() for s in (1, -1)}
    assert forward(chain)[:3] == (10000.0, 10000.0, 400.0)
    t, why = build(chain, "condor")          # 1 sd = 500, 1.5 sd = 750: sells 10500/9500, buys 10800/9200
    assert why is None and (t["bp"], t["sp"], t["sc"], t["bc"]) == (9200, 9500, 10500, 10800), t
    assert (t["credit"], t["max_loss"]) == (72, 228)
    s, _ = build(chain, "straddle")          # sells 10000 twice, buys 10500/9500
    assert (s["bp"], s["sp"], s["sc"], s["bc"], s["credit"], s["max_loss"]) == (9500, 10000, 10000, 10500, 300, 200)
    thin = dict(chain)
    thin[10800.0] = {"CE": (14, 99), "PE": chain[10800.0]["PE"]}
    t2, _ = build(thin, "condor")            # 10800 call too thin: 10900, and the wider (call) spread sets the loss
    assert (t2["bc"], t2["max_loss"]) == (10900, 400 - (100 - 8 - 14))
    holes = {k: v for k, v in chain.items() if not 10500 <= k <= 10800}
    assert build(holes, "condor") == (None, "hole")          # sold call found at 10900 > 10500 + 0.75 x 400
    assert build({k: v for k, v in chain.items() if k < 10500}, "condor") == (None, "no_leg")
    assert build({}, "condor") == (None, "no_k0")
    dear = dict(chain)
    dear[10800.0] = {"CE": (60, 500), "PE": chain[10800.0]["PE"]}
    assert build(dear, "condor") == (None, "bad_quote")      # the bought call costs more than the sold one
    gross = lambda tr, settle: sum(g for g, _ in price(tr, settle, 20000.0, 65).values())  # noqa: E731
    assert [gross(t, x) for x in (10000, 10650, 11500, 9000, 9400)] == [72, -78, -228, -228, -28]
    assert [gross(s, x) for x in (10000, 10300, 12000, 9000)] == [300, 0, -200, -200]

    def rupees(side, value):                 # the tariff as the prereg states it, restated on its own
        turnover = value * 2 * 65            # index level doubled (ref 20,000 over F 10,000), lot 65
        levies = turnover * (0.03553 + 0.0001 + 0.0000001) / 100
        return 20 + turnover * (0.15 if side == "SELL" else 0.003) / 100 + levies + 0.18 * (20 + levies)
    side = price(t, 10650, 20000.0, 65)
    call = (rupees("SELL", 50) + rupees("BUY", 14) + rupees("BUY", 150)) / 130 + 0.5 + 0.14
    put = (rupees("SELL", 50) + rupees("BUY", 14)) / 130 + 0.5 + 0.14
    assert abs(side["call"][1] - call) < 1e-9 and abs(side["put"][1] - put) < 1e-9, (side, call, put)
    assert abs(rupees("SELL", 50) - 36.08282867) < 1e-6      # worked by hand
    deep = price(t, 11500, 20000.0, 65)      # the bought call is exercised: a sale at intrinsic, with its STT
    assert abs(deep["call"][1] - (rupees("SELL", 50) + rupees("BUY", 14) + rupees("BUY", 1000)
                                  + rupees("SELL", 700)) / 130 - 0.64) < 1e-9
    # slippage floors: a quarter point at today's level and one tick, on a 2-point option
    cheap = {"f": 10000.0, "sc": 10500, "bc": 10800, "sp": 9500, "bp": 9200,
             "prem": {"sc": 2.0, "bc": 1.0, "sp": 2.0, "bp": 1.0}}
    fees = (rupees("SELL", 2) + rupees("BUY", 1)) / 130
    assert abs(price(cheap, 10000, 20000.0, 65)["call"][1] - fees - 2 * 0.125) < 1e-9
    assert abs(price(cheap, 10000, 1e6, 65)["call"][1]
               - (leg_cost("SELL", 200, 65, FNO_OPTION_COSTS) + leg_cost("BUY", 100, 65, FNO_OPTION_COSTS)) / 6500
               - 2 * 0.05) < 1e-9

    # --- the extract's day record: old format (settlement on the option rows) and UDiFF (a moved expiry)
    row = lambda kind, exp, k, close, settle, exp2="", und="", fmt="old": (  # noqa: E731
        kind, exp, exp2, str(k), str(close), str(settle), "500", "9.5", "1000", und, "75" if und else "", fmt)
    rec = day_record("2021-06-03", [row("CE", "2021-06-03", 15000, 687.1, 15690.35),
                                    row("PE", "2021-06-03", 15000, 0.05, 15690.35),
                                    row("CE", "2021-06-10", 15700, 90, 90), row("PE", "2021-06-10", 15700, 95, 95),
                                    row("PE", "2021-06-24", 15700, 200, 200), row("F", "2021-06-24", 0, 15712.4, 15712.4)])
    assert (rec["exp"], rec["front"], rec["opt"], rec["fut"], rec["und"], rec["near_fut"]) == \
        ("2021-06-03", "2021-06-10", 15690.35, None, None, 15712.4)
    assert rec["chain"] == {15700.0: {"CE": (90.0, 500.0, 0.0), "PE": (95.0, 500.0, 0.0)}}
    assert settlement(rec) == (15690.35, "opt")
    rec = day_record("2025-03-12", [row("CE", "2025-03-13", 22000, 400, 22400.5, "2025-03-12", "22400.5", "udiff"),
                                    row("CE", "2025-03-20", 22400, 150, 150, "2025-03-20", "22400.5", "udiff"),
                                    row("F", "2025-03-13", 0, 22399, 22400.5, "2025-03-12", "22400.5", "udiff")])
    assert (rec["exp"], rec["front"], rec["exp2_differs"]) == ("2025-03-13", "2025-03-20", 1)   # option rows only
    assert settlement(rec) == (22400.5, "und") and rec["fut"] == 22400.5
    days = {"X": {"2025-03-12": rec}}
    to_contracts(days, "units")
    assert days["X"]["2025-03-12"]["chain"][22400.0]["CE"] == (150.0, 500 / 75)
    unit = volume_unit([("udiff", 75 * 100 * 22000.0, 75 * 100, 22000.0, 75.0)] * 20 + [("old", 1650.0, 100, 22000.0, 0.0)])   # 100 contracts of 75 = Rs 1,650 lakh
    assert unit["unit"] == "units" and unit["old_format_median_turnover_per_contract_in_units"] == 75.0
    assert volume_unit([("udiff", 75 * 100 * 22000.0, 100, 22000.0, 75.0)])["unit"] == "contracts"

    # --- the chain of cycles: a weekly listed mid-cycle is ignored, a moved and a re-dated expiry are followed
    r = lambda exp, front: {"exp": exp, "front": front}  # noqa: E731
    recs = {"2021-01-28": r("2021-01-28", "2021-02-25"), "2021-02-11": r("2021-02-11", "2021-02-18"),
            "2021-02-25": r("2021-02-25", "2021-03-04"), "2021-03-03": r("2021-03-04", "2021-03-10"),
            "2021-03-10": r("2021-03-10", "2021-03-18"), "2021-03-17": r("2021-03-17", "2026-01-06")}
    assert cycles(recs) == ([("2021-01-28", "2021-02-25"), ("2021-02-25", "2021-03-03"), ("2021-03-03", "2021-03-10"),
                             ("2021-03-10", "2021-03-17")], [["2021-03-10", "2021-03-18", "2021-03-17"]])

    # --- an arm end to end on made-up days, then the report and the gates on made-up R
    mk = lambda exp, front, settle: {"exp": exp, "front": front, "und": settle, "fut": None, "opt": None,  # noqa: E731
                                     "chain": chain}
    recs = {"2021-01-07": mk("2021-01-07", "2021-01-14", 0), "2021-01-14": mk("2021-01-14", "2021-01-21", 10650.0),
            "2021-01-21": mk("2021-01-21", "2021-01-28", None), "2021-01-28": mk("2021-01-28", "2021-02-25", 9000.0),
            "2021-02-25": mk("2021-02-25", "2026-01-06", 10000.0)}
    cyc, _ = cycles(recs)
    rows, skips, skipped = run_arm(recs, cyc, "condor", {"2021-02-25"})
    assert [x["expiry"] for x in rows] == ["2021-01-14", "2021-01-28"] and "r" not in rows[0]   # stage 0 prices nothing
    assert skips == {"no_settlement": 1, "missing_file": 1} and skipped[0] == ["2021-01-14", "no_settlement"]
    rows, skips, _ = run_arm(recs, cyc, "condor", set(), 20000.0, 65)
    assert [x["expiry"] for x in rows] == ["2021-01-14", "2021-01-28", "2021-02-25"] and skips == {"no_settlement": 1}
    a = rows[0]
    assert a["gross"] == -78 and abs(a["cost"] - call - put) < 1e-9 and abs(a["r"] - (-78 - call - put) / 228) < 1e-12
    assert abs(a["r_call"] + a["r_put"] - a["r"]) < 1e-12 and abs(a["r2"] - (a["r"] - a["r_cost"])) < 1e-12
    assert rows[1]["r_gross"] == -1 and rows[1]["days"] == 7 and rows[2]["days"] == 28
    assert mechanism(recs, cyc, set())["beyond_1sd"] == 2 / 3          # moves of +1.625, -2.5 and 0 straddles
    two = {"NIFTY": recs, "BANKNIFTY": recs}                           # the whole trial path, three cycles an index
    out, detail = trial(two, {"proceed": {"208": True, "209": False}, "symbols": {
        s: {"missing_file_expiries": [], "ref_level": 20000.0, "data_ok": s == "NIFTY"} for s in two}})
    assert out["arms"]["209"]["not_run"] and not out["arms"]["208"]["pass"] and len(detail) == 6
    assert out["arms"]["208"]["NIFTY"]["cycles"] == 3 and out["arms"]["208"]["checks"]["8_banknifty"] is False
    with tempfile.TemporaryDirectory() as tmp:
        save_cycles(detail, os.path.join(tmp, "cycles.csv"))
    json.dumps(rounded(out))

    import random
    rnd = random.Random(7)
    fake = []
    for i in range(400):
        x = rnd.gauss(0.08, 0.4)
        day = (dt.date(2009, 1, 29) + dt.timedelta(days=15 * i)).isoformat()
        fake.append({"entry": day, "expiry": day, "days": 7 if i % 2 else 28, "r": x, "r2": x - 0.02, "r3": x - 0.04,
                     "r_gross": x + 0.02, "r_cost": 0.02, "r_call": x / 2, "r_put": x / 2, "bp": x * 30,
                     "credit": 70.0, "max_loss": 230.0, "cost": 4.0})
    good = report(fake)
    assert abs(good["t"]) <= abs(good["t_plain"]) and good["cycles"] == 400 and len(good["worst5"]) == 5
    assert good["s1"]["n"] + good["s2"]["n"] == 400 and good["short"]["n"] == 200
    assert verdict(good, good)["pass"] and not verdict(good, {})["pass"]
    assert verdict(good, {})["checks"] == dict(verdict(good, good)["checks"], **{"8_banknifty": False})
    bad = report([dict(x, r=-x["r"], r2=-x["r"] - 0.02) for x in fake])
    assert not any(v for k, v in verdict(bad, good)["checks"].items() if k[0] in "123456")
    assert verdict(report(fake[:50]), good)["checks"]["7_cycles"] is False
    assert verdict(report(fake[:2]), good)["pass"] is False
    json.dumps(rounded({"a": good, "b": verdict(good, good)}))
    print("selftest ok")
    return 0


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "selftest":
        return selftest()
    if mode not in ("stage0", "trial"):
        sys.exit(__doc__)
    days, samples = load()
    unit = volume_unit(samples)
    to_contracts(days, unit["unit"])
    with open(OPT_FILE + ".meta.json") as fh:
        meta = json.load(fh)
    # ponytail: the whole price panel is loaded for its session dates alone; trial 207's calendar, kept the same
    sessions = nse_prices.load(wide=True)[0]
    s0 = stage0(days, unit, sessions, meta)
    quiet = ("cycle_list", "moved", "arms", "cycles_per_year")
    brief = dict(s0, symbols={s: dict({k: v for k, v in d.items() if k not in quiet},
                                      moved=len(d["moved"]),
                                      arms={n: {k: v for k, v in a.items() if k != "skipped"} for n, a in d["arms"].items()})
                              for s, d in s0["symbols"].items()})
    print(json.dumps(rounded(brief), indent=1))
    if mode == "stage0":
        print("saved", ib.write("trial208_stage0.json", rounded(s0, 6)))
        return 0
    if os.path.exists(os.path.join(ib.OUT_DIR, "trial208_result.json")):
        print("trials 208 and 209 have been run; one run per hypothesis")
        return 1
    import evaluation
    if os.environ.get("SAHAB_RESEARCH_DATA"):     # the run log lives with the data, not in a worktree's empty folder
        evaluation.TRIAL_LOG_PATH = pathlib.Path(nse_prices.DATA) / "backtest_trials.json"
    out, detail = trial(days, s0)
    save_cycles(detail, os.path.join(ib.OUT_DIR, "trial208_cycles.csv"))
    for num in ARMS:                              # logged once everything is computed, before anything is shown
        if "not_run" not in out["arms"][num]:
            out["arms"][num]["trial_logged_as"] = evaluation.log_trial(LABELS[num])
    print("saved", ib.write("trial208_result.json", rounded(out)))
    print(json.dumps(rounded({n: {k: v for k, v in a.items() if k != "BANKNIFTY"} for n, a in out["arms"].items()}, 4),
                     indent=1))
    print(json.dumps(rounded({"BANKNIFTY": {n: a.get("BANKNIFTY") for n, a in out["arms"].items()},
                              "mechanism": out["mechanism"]}, 4), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
