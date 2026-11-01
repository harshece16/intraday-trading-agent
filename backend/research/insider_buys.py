"""Trial 206: promoter open-market purchases held five sessions.

Rules, samples and the pass rule are fixed in
docs/research/prereg-insider-buys.md, written and committed before this file.
The disclosures are NOT fetched here: NSE's terms forbid automated collection,
so the owner exports them by hand into backend/data/pit/ (gitignored), as CSV
from the NSE page or as the page's JSON. Prices and costs are trial 126's.

    python research/insider_buys.py stage0      # counts and lags, no return read
    python research/insider_buys.py trial       # one run, logged as a trial
    python research/insider_buys.py heldout     # 2026 sign check, only after a pass
"""
import bisect
import csv
import datetime as dt
import glob
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, BACKEND)

import nse_prices  # noqa: E402
import slow_momentum as sm  # noqa: E402

PIT_DIR = os.path.join(BACKEND, "data", "pit")
OUT_DIR = os.path.join(BACKEND, "..", "docs", "research", "data")

FIRST_BROADCAST = "2015-11-19"   # NSE's archive starts here; prereg amendment 1
LAST_BROADCAST = "2025-12-19"      # the last window that closes inside 2025
HALF_SPLIT = "2021-01-01"
LAST3_START = "2023-01-01"
HELD_OUT_START = "2026-01-01"
EXPORT_MONTHS = ("2015-12", "2025-12")

UNIVERSE_N = 500
MIN_VALUE = 1_000_000.0           # ₹10 lakh per symbol per broadcast date
TICKET = 50_000.0
HOLD = 5                          # sessions held, entry day included
EXTRA_SLIP = 0.0005               # on top of slow_momentum's 5 bp: 10 bp a side
OPEN_CUTOFF = dt.time(9, 0)       # a broadcast before this joins the same day's open
FAMILY_N = 2
FAMILY_T = 2.24
MIN_EVENTS = 100
MIN_PER_MONTH = 8
FLOOR_BP = 25.0

# required field -> (the page's JSON key, substrings of the CSV export's header).
# The CSV headers are as far as known, including the page's "INITMATION"
# spelling; stage 0 stops on any file where a field does not map to one column.
FIELDS = {
    "symbol": ("symbol", ("symbol",)),
    "category": ("personcategory", ("category of person",)),
    "mode": ("acqmode", ("mode of acquisition",)),
    "txn": ("tdptransactiontype", ("transaction type",)),
    "sectype": ("sectype", ("type of security (acquired",)),
    "value": ("secval", ("value of security (acquired",)),
    "to_date": ("acqtodt", ("acquisition to",)),
    "intim": ("intimdt", ("intimation", "initmation")),
    "broadcast": ("date", ("broadcast",)),
}
DATE_FORMATS = ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y", "%d-%m-%Y %H:%M:%S",
                "%d-%m-%Y %H:%M", "%d-%m-%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d")


# --- loading -----------------------------------------------------------------

def load_rows(pit_dir=PIT_DIR):
    """Every row of every export file, as dicts, with the file it came from."""
    rows = []
    for path in sorted(glob.glob(os.path.join(pit_dir, "*"))):
        name = os.path.basename(path)
        if path.endswith(".json"):
            with open(path) as fh:
                doc = json.load(fh)
            batch = doc["data"] if isinstance(doc, dict) else doc
        elif path.endswith(".csv"):
            with open(path, encoding="utf-8-sig", newline="") as fh:
                batch = list(csv.DictReader(fh))
        else:
            continue
        for r in batch:
            r["_file"] = name
        rows += batch
    return rows


def map_columns(headers):
    """(mapping field -> column, unmapped fields, ambiguous fields)."""
    low = {h.strip().lower(): h for h in headers if h}
    mapping, unmapped, ambiguous = {}, [], []
    for field, (key, needles) in FIELDS.items():
        hit = [low[key]] if key in low else []
        for needle in needles:
            if hit:
                break
            hit = [h for k, h in low.items() if needle in k]
        if not hit:
            unmapped.append(field)
        elif len(hit) > 1:
            ambiguous.append((field, hit))
        else:
            mapping[field] = hit[0]
    return mapping, unmapped, ambiguous


def parse_dt(s):
    s = (s or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def parse_num(s):
    s = str(s or "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def normalise(rows):
    """Rows -> dicts with the fields in FIELDS, parsed. Returns (rows, report).
    Column mapping is per file; a file with an unmapped or ambiguous field
    makes report['mapping_ok'] False (stage-0 gate 1)."""
    by_file = {}
    for r in rows:
        by_file.setdefault(r["_file"], []).append(r)
    out, report = [], {"files": {}, "mapping_ok": True, "bad_dates": 0, "missing_broadcast": 0}
    for name, batch in by_file.items():
        mapping, unmapped, ambiguous = map_columns(batch[0].keys())
        report["files"][name] = {"rows": len(batch), "mapping": mapping,
                                 "unmapped": unmapped, "ambiguous": ambiguous}
        if unmapped or ambiguous:
            report["mapping_ok"] = False
            continue
        for r in batch:
            g = lambda f: str(r.get(mapping[f]) or "").strip()  # noqa: E731
            bc = parse_dt(g("broadcast"))
            if bc is None:
                intim = parse_dt(g("intim"))
                if intim is None:
                    report["bad_dates"] += 1
                    continue
                bc = dt.datetime.combine(intim.date(), dt.time(23, 59))
                report["missing_broadcast"] += 1
            out.append({"symbol": g("symbol").upper(), "category": g("category"), "mode": g("mode"),
                        "txn": g("txn"), "sectype": g("sectype"), "value": parse_num(g("value")),
                        "to_date": parse_dt(g("to_date")), "broadcast": bc, "file": name})
    return out, report


# --- events ------------------------------------------------------------------

def qualifies(r):
    """Rule 1-3 of the prereg; returns the first failing rule's name or None."""
    if "promoter" not in r["category"].lower():
        return "category"
    if r["mode"].lower() != "market purchase" or r["txn"].lower().startswith("sell"):
        return "mode"
    if not r["sectype"].lower().startswith("equity"):
        return "sectype"
    return None


def aggregate(rows, drops):
    """One event per symbol per broadcast date: value summed, latest timestamp."""
    ev = {}
    for r in rows:
        why = qualifies(r)
        if why:
            drops[why] += 1
            continue
        key = (r["symbol"], r["broadcast"].date())
        e = ev.get(key)
        if e is None:
            ev[key] = {"symbol": r["symbol"], "broadcast": r["broadcast"], "value": r["value"],
                       "to_date": r["to_date"], "rows": 1}
        else:
            e["value"] += r["value"]
            e["broadcast"] = max(e["broadcast"], r["broadcast"])
            e["to_date"] = max(filter(None, (e["to_date"], r["to_date"])), default=None)
            e["rows"] += 1
    out = []
    for e in sorted(ev.values(), key=lambda e: e["broadcast"]):
        if e["value"] < MIN_VALUE:
            drops["value"] += 1
        else:
            out.append(e)
    return out


def entry_session(sessions, broadcast):
    """Index of the first session whose open follows the broadcast, or None."""
    d = broadcast.date().isoformat()
    if broadcast.time() < OPEN_CUTOFF:
        k = bisect.bisect_left(sessions, d)
    else:
        k = bisect.bisect_right(sessions, d)
    return k if k < len(sessions) else None


def liquid_at(chains, idx, n=UNIVERSE_N):
    """Trial 126's ranking (slow_momentum.universe_at) for the top n."""
    cands = []
    for name, c in chains.items():
        k = sm.rows_before(c, idx)
        if k < sm.MIN_HISTORY or c["idx"][k - 1] != idx or c["raw"][k - 1] < sm.MIN_PRICE:
            continue
        lo = bisect.bisect_left(c["idx"], idx - sm.LIQ_WINDOW + 1)
        vals = c["val"][lo:k] + [0.0] * (sm.LIQ_WINDOW - (k - lo))
        cands.append((st.median(vals), name))
    cands.sort(reverse=True)
    return [name for _, name in cands[:n]]


class Universes:
    """Top-n at the month-end before a session, computed once per month-end."""

    def __init__(self, sessions, chains):
        self.chains = chains
        self.me_idx = [i for _, i in sm.month_ends(sessions)]
        self.cache = {}

    def before(self, idx):
        k = bisect.bisect_left(self.me_idx, idx) - 1
        if k < 0:
            return None
        me = self.me_idx[k]
        if me not in self.cache:
            self.cache[me] = frozenset(liquid_at(self.chains, me))
        return self.cache[me]


def build_events(norm, sessions, chains, nxt, include_held_out=False):
    """Apply rules 1-7 plus the sample window. Returns (events, drops)."""
    drops = {k: 0 for k in ("category", "mode", "sectype", "value", "window", "held_out",
                            "unmatched", "universe", "no_entry", "overlap")}
    cache = {}
    unis = Universes(sessions, chains)
    first = HELD_OUT_START if include_held_out else FIRST_BROADCAST
    last = "9999" if include_held_out else LAST_BROADCAST
    out, open_until = [], {}
    for e in aggregate(norm, drops):
        d = e["broadcast"].date().isoformat()
        if d >= HELD_OUT_START and not include_held_out:
            drops["held_out"] += 1
            continue
        if not (first <= d <= last):
            drops["window"] += 1
            continue
        canon = nse_prices.canonical(e["symbol"], nxt, cache)
        if canon not in chains:
            drops["unmatched"] += 1
            continue
        k = entry_session(sessions, e["broadcast"])
        if k is None or k + HOLD - 1 >= len(sessions):
            drops["no_entry"] += 1
            continue
        uni = unis.before(k)
        if uni is None or canon not in uni:
            drops["universe"] += 1
            continue
        if open_until.get(canon, -1) >= k:
            drops["overlap"] += 1
            continue
        open_until[canon] = k + HOLD - 1
        e.update({"chain": canon, "entry": k, "exit": k + HOLD - 1, "universe": uni})
        out.append(e)
    return out, drops


# --- returns -----------------------------------------------------------------

def adjusted_open(c, k):
    """nse_prices adjusts closes only; scale the open by the same day's factor."""
    return c["open"][k] * c["close"][k] / c["raw"][k] if c["raw"][k] > 0 else 0.0


def event_return(c, entry, exit_):
    """(gross return, net return, shares) for one ticket, or None if untradable."""
    k = bisect.bisect_left(c["idx"], entry)
    if k >= len(c["idx"]) or c["idx"][k] != entry or c["open"][k] <= 0:
        return None
    shares = int(TICKET // c["open"][k])
    if shares == 0:
        return None
    out = sm.close_on_or_before(c, exit_)
    gross = out / adjusted_open(c, k) - 1.0
    value_in = shares * c["open"][k]
    value_out = value_in * (1.0 + gross)
    net = (value_out - value_in - sm.buy_cost(value_in) - value_in * EXTRA_SLIP
           - sm.sell_cost(value_out) - value_out * EXTRA_SLIP)
    return gross, net / value_in, shares


def benchmark_return(chains, names, entry, exit_, cache):
    """Equal-weighted gross return of the universe, entry open to exit close."""
    key = (entry, exit_)
    if key not in cache:
        rets = []
        for n in names:
            c = chains[n]
            k = bisect.bisect_left(c["idx"], entry)
            if k < len(c["idx"]) and c["idx"][k] == entry and c["open"][k] > 0:
                rets.append(sm.close_on_or_before(c, exit_) / adjusted_open(c, k) - 1.0)
        cache[key] = st.mean(rets) if rets else 0.0
    return cache[key]


def price_events(events, chains, drops):
    bench_cache = {}
    priced = []
    for e in events:
        r = event_return(chains[e["chain"]], e["entry"], e["exit"])
        if r is None:
            drops["no_fill"] = drops.get("no_fill", 0) + 1
            continue
        gross, net, shares = r
        bench = benchmark_return(chains, e["universe"], e["entry"], e["exit"], bench_cache)
        priced.append({**{k: v for k, v in e.items() if k != "universe"},
                       "gross": gross, "net": net, "bench": bench, "excess": net - bench, "shares": shares})
    return priced


# --- statistics --------------------------------------------------------------

def clustered_t(xs, groups):
    """t of the mean with standard errors clustered by group (Liang-Zeger)."""
    if len(xs) < 2:
        return None
    m = st.mean(xs)
    by = {}
    for x, g in zip(xs, groups):
        by[g] = by.get(g, 0.0) + (x - m)
    g = len(by)
    if g < 2:
        return None
    se = math.sqrt(sum(v * v for v in by.values()) * g / (g - 1)) / len(xs)   # CR1 small-sample factor
    return m / se if se > 0 else None


def block(priced):
    xs = [p["excess"] for p in priced]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean_excess_bp": round(st.mean(xs) * 1e4, 1),
            "median_excess_bp": round(st.median(xs) * 1e4, 1),
            "sd_bp": round(st.stdev(xs) * 1e4, 1) if len(xs) > 1 else None,
            "t_clustered": round(clustered_t(xs, [p["entry"] for p in priced]), 2) if len(xs) > 1 else None,
            "t_plain": round(sm.t_stat(xs), 2) if len(xs) > 1 else None,
            "mean_gross_bp": round(st.mean(p["gross"] for p in priced) * 1e4, 1),
            "mean_net_bp": round(st.mean(p["net"] for p in priced) * 1e4, 1),
            "win_rate": round(sum(1 for x in xs if x > 0) / len(xs), 3)}


def capped_book(priced, sessions, slots=20):
    """Information only: 20 slots of one ticket, events in broadcast order,
    skipped when full. Returns the book's net and benchmark return per year."""
    busy, taken = [], []
    for p in sorted(priced, key=lambda p: p["broadcast"]):
        busy = [x for x in busy if x >= p["entry"]]
        if len(busy) < slots:
            busy.append(p["exit"])
            taken.append(p)
    years = {}
    for p in taken:
        y = years.setdefault(sessions[p["entry"]][:4], {"events": 0, "net": 0.0, "bench": 0.0})
        y["events"] += 1
        y["net"] += p["net"] * TICKET
        y["bench"] += p["bench"] * TICKET
    capital = slots * TICKET
    return {y: {"events": v["events"], "net_pct": round(100 * v["net"] / capital, 2),
                "bench_pct": round(100 * v["bench"] / capital, 2)} for y, v in sorted(years.items())}


def verdict(priced, sessions, n_trials=FAMILY_N):
    import evaluation
    xs = [p["excess"] for p in priced]
    date = lambda p: sessions[p["entry"]]  # noqa: E731
    halves = (block([p for p in priced if date(p) < HALF_SPLIT]),
              block([p for p in priced if date(p) >= HALF_SPLIT]))
    last3 = block([p for p in priced if date(p) >= LAST3_START])
    whole = block(priced)
    dsr = evaluation.deflated_sharpe_ratio(xs, n_trials) if xs else {"dsr": None}
    checks = {
        "mean_positive_t": bool(xs) and whole["mean_excess_bp"] > 0 and (whole["t_clustered"] or 0) >= FAMILY_T,
        "dsr": (dsr.get("dsr") or 0) >= 0.95,
        "both_halves": all(h["n"] and h["mean_excess_bp"] > 0 for h in halves),
        "last_three_years": bool(last3["n"]) and last3["mean_excess_bp"] > 0,
        "floor_25bp": bool(xs) and whole["mean_excess_bp"] >= FLOOR_BP,
        "n_events": len(xs) >= MIN_EVENTS,
    }
    per_year = {}
    for p in priced:
        per_year.setdefault(date(p)[:4], []).append(p)
    return {"whole": whole, "halves": halves, "last_three_years": last3, "dsr": dsr,
            "per_year": {y: block(v) for y, v in sorted(per_year.items())},
            "capped_book": capped_book(priced, sessions), "checks": checks,
            "pass": all(checks.values())}


# --- stage 0 and the run --------------------------------------------------------

def lag_distribution(events, sessions):
    tx, entry = {}, {}
    for e in events:
        if e.get("to_date"):
            t0, days = e["to_date"].date(), (e["broadcast"].date() - e["to_date"].date()).days
            wd = sum(1 for i in range(1, days + 1) if (t0 + dt.timedelta(days=i)).weekday() < 5)
            tx[wd] = tx.get(wd, 0) + 1
        if "entry" in e:
            gap = (dt.date.fromisoformat(sessions[e["entry"]]) - e["broadcast"].date()).days
            entry[gap] = entry.get(gap, 0) + 1
    return {"transaction_to_broadcast_weekdays": dict(sorted(tx.items())),
            "broadcast_to_entry_days": dict(sorted(entry.items()))}


def months_between(a, b):
    y, m = int(a[:4]), int(a[5:7])
    out = []
    while f"{y:04d}-{m:02d}" <= b:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def stage0(norm, report, events, drops, sessions):
    rows_per_month = {}
    for r in norm:
        k = r["broadcast"].strftime("%Y-%m")
        rows_per_month[k] = rows_per_month.get(k, 0) + 1
    missing = [m for m in months_between(*EXPORT_MONTHS) if m not in rows_per_month]
    per_month = {}
    for e in events:
        k = e["broadcast"].strftime("%Y-%m")
        per_month[k] = per_month.get(k, 0) + 1
    n_months = len(months_between(FIRST_BROADCAST[:7], LAST_BROADCAST[:7]))
    avg = len(events) / n_months if n_months else 0.0
    out = {"mapping_ok": report["mapping_ok"], "files": report["files"],
           "bad_dates": report["bad_dates"], "missing_broadcast": report["missing_broadcast"],
           "rows": len(norm), "rows_per_month": rows_per_month, "missing_months": missing,
           "events": len(events), "events_per_month": per_month, "events_per_month_avg": round(avg, 2),
           "drops": drops, "lags": lag_distribution(events, sessions)}
    out["gate"] = {"columns": report["mapping_ok"], "export_complete": not missing,
                   "enough_events": avg >= MIN_PER_MONTH and len(events) >= MIN_EVENTS}
    out["proceed"] = all(out["gate"].values())
    return out


def write(name, obj):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1, default=str)
    return path


def load_everything(include_held_out=False):
    sessions, chains, _meta, _events = nse_prices.load(include_held_out=include_held_out)
    nxt = nse_prices.symbol_chains(os.path.join(nse_prices.BHAV_DIR, "symbolchange.csv"))
    norm, report = normalise(load_rows())
    events, drops = build_events(norm, sessions, chains, nxt, include_held_out)
    return sessions, chains, norm, report, events, drops


def main(argv):
    mode = argv[1] if len(argv) > 1 else "stage0"
    held_out = mode == "heldout"
    sessions, chains, norm, report, events, drops = load_everything(held_out)
    s0 = stage0(norm, report, events, drops, sessions)
    print(json.dumps({k: v for k, v in s0.items() if k not in ("rows_per_month", "events_per_month", "files")},
                     indent=1, default=str))
    if mode == "stage0":
        print("saved", write("trial206_stage0.json", s0))
        return 0
    if not s0["proceed"] and not held_out:
        print("stage 0 did not pass; the trial is not run")
        return 1
    import evaluation
    priced = price_events(events, chains, drops)
    label = "trial 206 promoter market purchases, 5-session hold" + (" HELD-OUT sign check" if held_out else "")
    n = evaluation.log_trial(label)
    out = verdict(priced, sessions)
    out.update({"trial_logged_as": n, "label": label, "drops": drops})
    print(json.dumps({k: v for k, v in out.items() if k != "per_year"}, indent=1, default=str))
    print("saved", write("trial206_heldout.json" if held_out else "trial206_result.json", out))
    with open(os.path.join(OUT_DIR, "trial206_events.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "chain", "broadcast", "entry", "exit", "value", "shares", "gross", "net", "bench", "excess"])
        for p in priced:
            w.writerow([p["symbol"], p["chain"], p["broadcast"], sessions[p["entry"]], sessions[p["exit"]],
                        round(p["value"]), p["shares"], round(p["gross"], 6), round(p["net"], 6),
                        round(p["bench"], 6), round(p["excess"], 6)])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
