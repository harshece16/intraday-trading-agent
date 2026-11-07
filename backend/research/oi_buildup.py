"""Trial 207: futures OI build-up (price up, OI up) held five sessions.

Rules, samples and the pass rule are fixed in docs/research/prereg-oi-buildup.md,
written and merged before this file. The OI history is the aggregate that
fo_oi_aggregate.py builds on sahab-pc (backend/data/fo_oi/, gitignored). Prices,
costs, the ticket and the event pricing are trial 206's (insider_buys).

    python research/oi_buildup.py stage0      # counts only, no return read
    python research/oi_buildup.py trial       # one run, logged as a trial
"""
import bisect
import csv
import gzip
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, BACKEND)

import insider_buys as ib  # noqa: E402  (trial 206: ticket, costs, event and benchmark pricing)
import nse_prices  # noqa: E402
from pead_stage_a import nw_t  # noqa: E402

OI_FILE = os.path.join(BACKEND, "data", "fo_oi", "fo_oi_daily.csv.gz")
FIRST = "2009-01-01"
LAST_EXIT = "2025-12-31"
HALF_SPLIT = "2017-07-01"
LAST3_START = "2023-01-01"
HOLD = ib.HOLD                 # five sessions, entry day included
NW_LAGS = HOLD - 1             # consecutive holds overlap for four sessions
FAMILY_N, FAMILY_T, MECH_T = 2, 2.24, 1.65
MIN_EVENTS, MIN_SESSIONS, FLOOR_BP = 100, 1000, 25.0
MAX_MISSING, MIN_MATCH = 0.01, 0.95
SHARE_CHANGES = ("split", "bonus", "consolidation")
LB, SC, SB, LU = "LONG_BUILDUP", "SHORT_COVERING", "SHORT_BUILDUP", "LONG_UNWINDING"


def load_oi(path=OI_FILE):
    """({date: {symbol: oi}}, sorted F&O dates, expiry dates, {date: contracts}). 2026 is never read."""
    by_date, expiries, contracts = {}, set(), {}
    with gzip.open(path, "rt") as fh:
        for r in csv.DictReader(fh):
            d = r["date"]
            if d < FIRST or d > LAST_EXIT:
                continue
            by_date.setdefault(d, {})[r["symbol"]] = int(r["oi"])
            contracts[d] = contracts.get(d, 0) + int(r["n_exp"])
            if r["expiry_day"] == "1":
                expiries.add(d)
    return by_date, sorted(by_date), expiries, contracts


def state(r, doi):
    if r > 0 and doi > 0:
        return LB
    if r > 0 and doi < 0:
        return SC
    if r < 0 and doi > 0:
        return SB
    if r < 0 and doi < 0:
        return LU
    return None


def signal_days(by_date, f_dates, expiries, sessions, chains, canon, share_days):
    """[(signal date, session index, {chain: state})], drops. Exclusions 1-4 of the prereg."""
    drops = {k: 0 for k in ("expiry", "after_expiry", "no_session", "gap", "first_day", "zero_oi",
                            "unmatched", "share_change", "no_close", "no_state")}
    matched = total = 0
    after = {f_dates[i + 1] for i, d in enumerate(f_dates[:-1]) if d in expiries}
    out = []
    for i in range(1, len(f_dates)):
        d, prev = f_dates[i], f_dates[i - 1]
        syms = by_date[d]
        if d in expiries or d in after:
            drops["expiry" if d in expiries else "after_expiry"] += len(syms)
            continue
        k = bisect.bisect_left(sessions, d)
        if k >= len(sessions) or sessions[k] != d or k == 0:
            drops["no_session"] += len(syms)
            continue
        if sessions[k - 1] != prev:          # the previous session's F&O file is missing
            drops["gap"] += len(syms)
            continue
        states = {}
        for sym, oi in syms.items():
            total += 1
            name = canon(sym)
            if name not in chains:
                drops["unmatched"] += 1
                continue
            matched += 1
            oi0 = by_date[prev].get(sym)
            if oi0 is None:
                drops["first_day"] += 1
                continue
            if oi0 <= 0:
                drops["zero_oi"] += 1
                continue
            if (name, d) in share_days:
                drops["share_change"] += 1
                continue
            c = chains[name]
            j = bisect.bisect_left(c["idx"], k)
            if j == 0 or j >= len(c["idx"]) or c["idx"][j] != k or c["idx"][j - 1] != k - 1:
                drops["no_close"] += 1
                continue
            s = state(c["close"][j] / c["close"][j - 1] - 1.0, oi / oi0 - 1.0)
            if s is None:
                drops["no_state"] += 1
                continue
            states[name] = s
        if states:
            out.append((d, k, states))
    return out, drops, {"symbol_days": total, "matched": matched}


def build_events(days, sessions, chains, want):
    """Events of one state: entry the next session, overlap rule per state. No price is read
    beyond 'is there an open to fill at', as in trial 206's build_events."""
    drops = {k: 0 for k in ("window", "no_trade", "zero_shares", "overlap")}
    out, open_until = [], {}
    for d, k, states in days:
        entry, exit_ = k + 1, k + HOLD
        if exit_ >= len(sessions) or sessions[exit_] > LAST_EXIT:
            drops["window"] += sum(1 for s in states.values() if s == want)
            continue
        universe = frozenset(states)
        for name in sorted(n for n, s in states.items() if s == want):
            c = chains[name]
            j = bisect.bisect_left(c["idx"], entry)
            if j >= len(c["idx"]) or c["idx"][j] != entry or c["open"][j] <= 0:
                drops["no_trade"] += 1
                continue
            if int(ib.TICKET // c["open"][j]) == 0:
                drops["zero_shares"] += 1
                continue
            if open_until.get(name, -1) >= entry:
                drops["overlap"] += 1
                continue
            open_until[name] = exit_
            out.append({"date": d, "chain": name, "entry": entry, "exit": exit_, "universe": universe})
    return out, drops


def session_series(priced):
    """[(signal date, entry, mean excess)] in entry order."""
    by = {}
    for p in priced:
        by.setdefault((p["date"], p["entry"]), []).append(p["excess"])
    return [(d, e, st.mean(v)) for (d, e), v in sorted(by.items(), key=lambda kv: kv[0][1])]


def summary(priced, series):
    xs = [m for _, _, m in series]
    if not xs:
        return {"events": 0, "sessions": 0}
    ev = [p["excess"] for p in priced]
    t = nw_t(xs, NW_LAGS)
    return {"events": len(ev), "sessions": len(xs), "mean_session": st.mean(xs), "t_nw": t,
            "mean_session_bp": round(st.mean(xs) * 1e4, 1), "t_nw_r": round(t, 2) if t else None,
            "mean_event_bp": round(st.mean(ev) * 1e4, 1), "median_event_bp": round(st.median(ev) * 1e4, 1),
            "sd_event_bp": round(st.stdev(ev) * 1e4, 1) if len(ev) > 1 else None,
            "mean_gross_bp": round(st.mean(p["gross"] for p in priced) * 1e4, 1),
            "mean_net_bp": round(st.mean(p["net"] for p in priced) * 1e4, 1),
            "win_rate": round(sum(1 for x in ev if x > 0) / len(ev), 3)}


def verdict(lb, sc):
    import evaluation
    s_lb, s_sc = session_series(lb), session_series(sc)
    part = lambda pred: [x for x in s_lb if pred(x[0])]  # noqa: E731
    whole = summary(lb, s_lb)
    halves = [part(lambda d: d < HALF_SPLIT), part(lambda d: d >= HALF_SPLIT)]
    last3 = part(lambda d: d >= LAST3_START)
    xs = [m for _, _, m in s_lb]
    dsr = evaluation.deflated_sharpe_ratio(xs, FAMILY_N) if len(xs) > 2 else {"dsr": None}
    sc_by_entry = {e: m for _, e, m in s_sc}
    diff = [m - sc_by_entry[e] for _, e, m in s_lb if e in sc_by_entry]
    t_diff = nw_t(diff, NW_LAGS) if len(diff) > 2 else None
    mean = lambda s: st.mean(m for _, _, m in s) if s else 0.0  # noqa: E731
    checks = {
        "1_mean_positive_t": bool(xs) and whole["mean_session"] > 0 and (whole["t_nw"] or 0) >= FAMILY_T,
        "2_dsr": (dsr.get("dsr") or 0) >= 0.95,
        "3_both_halves": all(h and mean(h) > 0 for h in halves),
        "4_last_three_years": bool(last3) and mean(last3) > 0,
        "5_floor_25bp": bool(lb) and st.mean(p["excess"] for p in lb) * 1e4 >= FLOOR_BP,
        "6_n_events": len(lb) >= MIN_EVENTS,
        "7_mechanism": bool(diff) and st.mean(diff) > 0 and (t_diff or 0) >= MECH_T,
    }
    per_year = {}
    for p in lb:
        per_year.setdefault(p["date"][:4], []).append(p)
    return {"long_buildup": whole, "short_covering": summary(sc, s_sc),
            "halves_mean_bp": [round(mean(h) * 1e4, 1) for h in halves],
            "halves_t_nw": [round(nw_t([m for _, _, m in h], NW_LAGS) or 0, 2) for h in halves],
            "last_three_years_mean_bp": round(mean(last3) * 1e4, 1), "dsr": dsr,
            "mechanism": {"sessions": len(diff), "mean_bp": round(st.mean(diff) * 1e4, 1) if diff else None,
                          "t_nw": round(t_diff, 2) if t_diff else None},
            "per_year": {y: summary(v, session_series(v)) for y, v in sorted(per_year.items())},
            "checks": checks, "pass": all(checks.values())}


def stage0(sessions, by_date, f_dates, expiries, contracts, days, sdrops, match, events, edrops):
    cash = [s for s in sessions if FIRST <= s <= LAST_EXIT]
    have = set(f_dates)
    missing = [s for s in cash if s not in have]
    by_month = {}
    for d in expiries:
        by_month[d[:7]] = by_month.get(d[:7], 0) + 1
    months = sorted({s[:7] for s in cash})
    bad_months = {m: by_month.get(m, 0) for m in months if by_month.get(m, 0) != 1}
    parse = {}   # prereg stage 0 item 2: rows and stocks per day, by month
    for d in f_dates:
        m = parse.setdefault(d[:7], {"days": 0, "stocks": 0, "contracts": 0})
        m["days"] += 1
        m["stocks"] += len(by_date[d])
        m["contracts"] += contracts[d]
    parse = {k: {"days": v["days"], "stocks_per_day": round(v["stocks"] / v["days"], 1),
                 "contracts_per_day": round(v["contracts"] / v["days"], 1)} for k, v in parse.items()}
    counts = {}
    for d, _k, states in days:
        c = counts.setdefault(d[:7], {LB: 0, SC: 0, SB: 0, LU: 0})
        for s in states.values():
            c[s] += 1
    n_ev = len(events[LB])
    n_sessions = len({e["entry"] for e in events[LB]})
    rate = match["matched"] / match["symbol_days"] if match["symbol_days"] else 0.0
    gates = {"completeness": len(missing) <= MAX_MISSING * len(cash), "symbol_match": rate >= MIN_MATCH,
             "events": n_ev >= MIN_EVENTS, "sessions": n_sessions >= MIN_SESSIONS}
    return {"cash_sessions": len(cash), "fo_sessions": len(f_dates), "missing": missing,
            "missing_frac": round(len(missing) / len(cash), 4) if cash else None,
            "expiry_days": len(expiries), "months_without_one_expiry": bad_months, "parse_by_month": parse,
            "symbol_match_rate": round(rate, 4), "signal_drops": sdrops,
            "event_drops": edrops, "events": {s: len(v) for s, v in events.items()},
            "lb_entry_sessions": n_sessions, "states_per_month": counts,
            "gates": gates, "proceed": all(gates.values())}


def main(argv):
    mode = argv[1] if len(argv) > 1 else "stage0"
    if mode not in ("stage0", "trial"):
        sys.exit(__doc__)
    sessions, chains, meta, ca = nse_prices.load(wide=True)
    aliases = {a: c for c, names in meta.get("aliases", {}).items() for a in names}
    nxt = nse_prices.symbol_chains(os.path.join(nse_prices.BHAV_DIR, "symbolchange.csv"))
    cache = {}
    canon = lambda s: aliases.get(s) or nse_prices.canonical(s, nxt, cache)  # noqa: E731
    # the session the factor lands on (an ex-date on a holiday moves to the next session)
    share_days = {(e[0], sessions[chains[e[0]]["idx"][e[1]]]) for e in ca if e[2] in SHARE_CHANGES}
    by_date, f_dates, expiries, contracts = load_oi()
    days, sdrops, match = signal_days(by_date, f_dates, expiries, sessions, chains, canon, share_days)
    events, edrops = {}, {}
    for s in (LB, SC):
        events[s], edrops[s] = build_events(days, sessions, chains, s)
    s0 = stage0(sessions, by_date, f_dates, expiries, contracts, days, sdrops, match, events, edrops)
    print(json.dumps({k: v for k, v in s0.items() if k not in ("states_per_month", "missing", "parse_by_month")}, indent=1))
    if mode == "stage0":
        print("saved", ib.write("trial207_stage0.json", s0))
        return 0
    if not s0["proceed"]:
        print("stage 0 did not pass; the trial is not run")
        return 1
    drops = {}
    lb = ib.price_events(events[LB], chains, drops)
    sc = ib.price_events(events[SC], chains, drops)
    out = verdict(lb, sc)
    out["pricing_drops"] = drops
    print(json.dumps({k: v for k, v in out.items() if k != "per_year"}, indent=1, default=str))
    print("saved", ib.write("trial207_result.json", out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
