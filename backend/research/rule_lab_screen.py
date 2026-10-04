"""
L55 — the rule lab's historical combinatorial search (docs/research/prereg-rule-lab.md,
amendment 3, which replaces §5).

Every registered rule's signal is a boolean entry condition. The search tries
all singles, pairs and triples of same-side conditions (AND), and a bounded
greedy forward selection for larger sets, each with both exits (H30 and R3),
on every NIFTY 100 stock in the Kite 5-minute cache, sessions 2024-09-20 to
2025-12-31. It is judged by the Romano-Wolf stepdown over every combination
evaluated, with the probability of backtest overfitting (CSCV) and the
deflated Sharpe ratio of the best, and keeps at most 5 survivors for one pass
on 2026, after an independent review.

The conditions and the trade come from backend/rule_lab.py, the forward lab's
own code, so the two looks cannot define a rule differently.

Modes (one per run, the order is the protocol):

  --stage0          data checks, condition and combination signal counts, the
                    family size, a runtime estimate. Reads no exit price and
                    computes no return. 2026: a row count only.
  --discover        the search, on 2024-09-20 .. 2025-12-31. Writes the result
                    and the survivors. Only after stage 0 and the review.
  --confirm-2026    the survivors only, on 2026-01-01 .. the newest cached
                    session, once, after the review of the discovery result.

Data: the candle cache, opened read-only (mode=ro), path from --db or
KRONOS_CANDLE_DB. kite_history is not imported (it opens the file for
writing). Every query has an explicit time bound; the loader asserts it.

RESEARCH ONLY. Nothing in the live path imports this.
"""
import argparse
import itertools
import json
import math
import os
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import rule_lab  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
DISCOVERY_FIRST = "2024-09-20"
DISCOVERY_LAST = "2025-12-31"
HISTORY_SESSIONS = 2          # the cache's first two sessions are history only
INPUT_PRIOR_SESSIONS = 4      # bars of up to 4 earlier sessions go with each session, like the engine's 5-day fetch
EXITS = ("H30", "R3")
MIN_TRADES, MIN_SESSIONS = 200, 40
GREEDY_STARTS, GREEDY_MAX = 5, 20
GREEDY_MIN_TRADES = 200
CSCV_BLOCKS, CSCV_MIN_IS_TRADES = 16, 50
MAX_SURVIVORS = 5
CONFIRM_MIN_TRADES = 100
BLOCK = 5


def _epoch(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST).timestamp())


DISCOVERY_END_TS = _epoch("2026-01-01")      # exclusive: no bar of 2026 in discovery


def default_db():
    return os.environ.get("KRONOS_CANDLE_DB") or os.path.join(os.path.dirname(HERE), "data", "kite_history.db")


def connect(db):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    return conn


def symbols(conn):
    return [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM candles WHERE interval='5m' ORDER BY symbol")]


def load_bars(conn, symbol, start_ts, end_ts):
    """A symbol's 5-minute bars with start_ts <= ts < end_ts, as rule_lab candles (IST times)."""
    rows = conn.execute("SELECT ts, open, high, low, close, volume FROM candles WHERE symbol=? AND interval='5m' "
                        "AND ts >= ? AND ts < ? ORDER BY ts", (symbol, start_ts, end_ts)).fetchall()
    out = []
    for ts, o, h, l, c, v in rows:
        assert start_ts <= ts < end_ts, "a bar outside the query's bounds"
        out.append({"time": datetime.fromtimestamp(ts, IST).isoformat(), "open": o, "high": h, "low": l,
                    "close": c, "volume": v or 0})
    return out


def count_2026_rows(conn):
    """Stage 0's only read of 2026: how many rows there are, by symbol. No price."""
    return dict(conn.execute("SELECT symbol, COUNT(*) FROM candles WHERE interval='5m' AND ts >= ? GROUP BY symbol",
                             (DISCOVERY_END_TS,)).fetchall())


# ---- catalog conditions (prereg amendment 2) ---------------------------------------

def canonical_spec(spec):
    return json.dumps(sorted(json.dumps(t) for t in (spec.get("all") or [])))


def load_catalog_rules(paths, cohort=2):
    """Register catalog rules written in rule_lab.spec_signal's format.

    Each file is a JSON list (or {"rules": [...]}) of {"id", "name", "side", "spec",
    "sources": [...]}. Two entries with the same side and the same terms are one
    rule, with every source kept. An entry without a usable spec is returned in
    `skipped` with the reason, never guessed at. Returns (registered ids, skipped)."""
    seen, registered, skipped = {}, [], []
    for path in paths or []:
        with open(path) as fh:
            data = json.load(fh)
        for e in (data.get("rules") if isinstance(data, dict) else data) or []:
            spec, side = e.get("spec"), (e.get("side") or "").upper()
            if not isinstance(spec, dict) or side not in ("LONG", "SHORT"):
                skipped.append({"id": e.get("id"), "file": path, "reason": "no spec in rule_lab's format, or no side"})
                continue
            key = (side, canonical_spec(spec))
            if key in seen:
                rule_lab.REGISTRY[seen[key]["id"]]["sources"] += e.get("sources") or [path]
                continue
            try:
                sig = rule_lab.spec_signal(spec)
            except ValueError as exc:
                skipped.append({"id": e.get("id"), "file": path, "reason": str(exc)})
                continue
            rid = e.get("id") or f"C{len(registered) + 1:03d}"
            rule_lab.register(rid, e.get("name") or rid, side, e.get("family") or "catalog", sig,
                              exit_kind="fixed", cohort=cohort)
            rule_lab.REGISTRY[rid]["sources"] = list(e.get("sources") or [path])
            seen[key] = {"id": rid}
            registered.append(rid)
    return registered, skipped


# ---- per-symbol precompute (the forward lab's own functions) ----------------------

def sessions_of(bars):
    out = defaultdict(list)
    for c in bars:
        out[c["time"][:10]].append(c)
    return out


def precompute_symbol(args):
    """Every condition on every finished bar of every evaluable session of one stock,
    and, with outcomes, each exit's trade from that bar. Returns compact lists."""
    db, symbol, start_ts, end_ts, first, last, conds, outcomes, warm_ts = args
    conn = connect(db)
    bars = load_bars(conn, symbol, warm_ts, end_ts)
    conn.close()
    by_day = sessions_of(bars)
    days = sorted(by_day)
    costs_cfg = _costs()
    rows = []          # (day, pos, indices of the conditions that fired, entry_ok, outcomes or None)
    for di, day in enumerate(days):
        if day < first or day > last or di < HISTORY_SESSIONS:
            continue
        prior = days[max(0, di - INPUT_PRIOR_SESSIONS):di]
        candles = [c for d in prior for c in by_day[d]] + by_day[day]
        ctx = rule_lab.session_context(candles, day)
        today = ctx["today"]
        cache = {}
        for pos, k in enumerate(today):
            mask = tuple(ci for ci, rid in enumerate(conds) if rule_lab.REGISTRY[rid]["signal"](ctx, pos, cache))
            entry_ok = (pos + 1 < len(today)
                        and ctx["bars"][today[pos + 1]]["time"] == rule_lab._add_minutes(ctx["bars"][k]["time"], 5)
                        and rule_lab._minutes_of(ctx["bars"][today[pos + 1]]["time"]) <= rule_lab._minutes_of(
                            "2000-01-01T" + rule_lab.LAST_ENTRY))
            out = _outcomes(ctx, pos, costs_cfg) if (outcomes and entry_ok and mask) else None
            rows.append((day, pos, mask, entry_ok, out))
    return symbol, len(bars), {d: len(v) for d, v in by_day.items()}, rows


def _costs():
    import costs  # noqa: F401  (rule_lab prices with costs.py; config.COSTS is the cost model)
    import config
    return config.COSTS


def _outcomes(ctx, pos, costs_cfg):
    """{side: (h30, r3)} for a signal on today's bar `pos`, through rule_lab's own exit and
    pricing code. Each is (exit pos in today, net bp, gross bp, net R), (-1, ...) for a
    void, or None for no trade (R3's stop below the cost floor, or entry at/past the stop)."""
    today, bars = ctx["today"], ctx["bars"]
    k, nxt = today[pos], today[pos + 1]
    e = bars[nxt]["open"]
    qty = max(1, int(rule_lab.NOTIONAL // e)) if e > 0 else 0
    floor = rule_lab.costs.round_trip_pct(rule_lab.NOTIONAL, costs_cfg)
    res = {}
    xk, _ = rule_lab._fixed_exit(ctx, nxt)
    for side in ("LONG", "SHORT"):
        if xk is None:
            h = (-1, None, None, None)
        else:
            t = rule_lab._price_trade({"side": side, "entry_price": e, "qty": qty,
                                       "exit_price": bars[xk]["open"]}, costs_cfg)
            h = (today.index(xk), t["net_bp"], t["gross_bp"], None)
        stop = bars[k]["low"] if side == "LONG" else bars[k]["high"]
        risk = (e - stop) if side == "LONG" else (stop - e)
        if risk <= 0 or risk / e * 100 < floor:
            r = None
        else:
            target = e + rule_lab.TARGET_R * risk if side == "LONG" else e - rule_lab.TARGET_R * risk
            xk2, xp, _ = rule_lab._r_exit(ctx, nxt, side, stop, target)
            if xk2 is None:
                r = (-1, None, None, None)
            else:
                t2 = rule_lab._price_trade({"side": side, "entry_price": e, "qty": qty, "exit_price": xp,
                                            "stop_price": stop}, costs_cfg)
                r = (today.index(xk2), t2["net_bp"], t2["gross_bp"], t2.get("net_r"))
        res[side] = (h, r)
    return res


# ---- the panel: all stocks' bars as flat arrays ----------------------------------

class Panel:
    """Flat arrays over every evaluable stock-bar: session index, condition masks, and per
    (exit, side) the exit bar's flat index (-1 void, -2 no trade) and net bp."""

    def __init__(self, results, conds, outcomes):
        import numpy as np
        self.conds = conds
        days = sorted({r[0] for _, _, _, rows in results for r in rows})
        self.days = days
        day_ix = {d: i for i, d in enumerate(days)}
        sess, ok, ends, sym = [], [], [], []
        fired_at = defaultdict(list)
        ex = {(x, s): ([], [], [], []) for x in EXITS for s in ("LONG", "SHORT")}
        base = 0
        for si, (symbol, _, _, rows) in enumerate(results):
            # rows are in (day, pos) order; a stock-session is a run of rows with the same day
            start_of = {}
            for j, r in enumerate(rows):
                start_of.setdefault(r[0], base + j)
            end_of = {}
            for j, r in enumerate(rows):
                end_of[r[0]] = base + j
            for j, (day, pos, mask, entry_ok, out) in enumerate(rows):
                sess.append(day_ix[day])
                for ci in mask:
                    fired_at[ci].append(base + j)
                ok.append(entry_ok)
                ends.append(end_of[day])
                sym.append(si)
                for side in ("LONG", "SHORT"):
                    pair = out.get(side) if out else None
                    for x, val in zip(EXITS, pair or (None, None)):
                        arrs = ex[(x, side)]
                        if val is None:
                            arrs[0].append(-2), arrs[1].append(0.0), arrs[2].append(0.0), arrs[3].append(0.0)
                        elif val[0] == -1:
                            arrs[0].append(-1), arrs[1].append(0.0), arrs[2].append(0.0), arrs[3].append(0.0)
                        else:
                            arrs[0].append(start_of[day] + val[0]), arrs[1].append(val[1]), arrs[2].append(val[2])
                            arrs[3].append(val[3] if val[3] is not None else 0.0)
            base += len(rows)
        self.session = np.array(sess, dtype=np.int32)
        self.entry_ok = np.array(ok, dtype=bool)
        self.end = np.array(ends, dtype=np.int64)
        self.symbol = np.array(sym, dtype=np.int32)
        self.exit_ix = {k: np.array(v[0], dtype=np.int64) for k, v in ex.items()}
        self.net = {k: np.array(v[1], dtype=np.float64) for k, v in ex.items()}
        self.gross = {k: np.array(v[2], dtype=np.float64) for k, v in ex.items()}
        self.net_r = {k: np.array(v[3], dtype=np.float64) for k, v in ex.items()}
        self.cond_bits = {}
        for i, rid in enumerate(conds):
            bits = np.zeros(len(sess), dtype=bool)
            bits[np.array(fired_at.get(i, []), dtype=np.int64)] = True
            self.cond_bits[rid] = bits

    def signals(self, combo):
        import numpy as np
        m = self.entry_ok.copy()
        for rid in combo:
            m &= self.cond_bits[rid]
        return np.nonzero(m)[0]

    def trades(self, combo, side, exit_kind):
        """Flat indices of the trades taken, with one open trade per stock at a time."""
        ix = self.signals(combo)
        exit_ix = self.exit_ix[(exit_kind, side)]
        taken = []
        free_from = -1
        for i in ix:
            if i < free_from:
                continue
            x = exit_ix[i]
            if x == -2:                      # no trade on this bar (R3's stop floor)
                continue
            taken.append(i)
            # entry is bar i+1; the next signal may enter at the exit bar's open, so from x-1
            free_from = (self.end[i] + 1) if x == -1 else x - 1
        return taken

    def session_sums(self, taken, side, exit_kind):
        import numpy as np
        taken = np.asarray(taken, dtype=np.int64)
        valid = taken[self.exit_ix[(exit_kind, side)][taken] >= 0] if len(taken) else taken
        G = len(self.days)
        S = np.bincount(self.session[valid], weights=self.net[(exit_kind, side)][valid], minlength=G)
        N = np.bincount(self.session[valid], minlength=G).astype(float)
        return S, N, valid


# ---- the search ----------------------------------------------------------------

def git_state(repo_dir=None):
    """(commit hash, dirty flag) of the working tree the search runs from. Monkeypatched in tests."""
    import subprocess
    repo_dir = repo_dir or os.path.dirname(os.path.abspath(__file__))
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True,
                                check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo_dir,
                                    capture_output=True, text=True, check=True).stdout.strip())
    except Exception as e:  # not a git checkout: refuse, the record would have no provenance
        raise RefusedRun(f"cannot read the git state ({e}); a run must come from a committed tree")
    return commit, dirty


class RefusedRun(RuntimeError):
    """A run the prereg (correction of 2026-10-05, B2) does not allow: an existing result, a dirty
    tree, or a family that is not the one stage 0 recorded."""


def family_hash(conds, look=1):
    """sha256 over the sorted condition ids with their sides and the family's size by part.
    Stage 0 writes it; discover() must produce the same; confirm_2026() must match discover()'s.
    Look 2 (amendment 6) hashes the filter too, so its records cannot be mistaken for look 1's."""
    import hashlib
    enum, greedy = max_family_size(conds)
    desc = {"conditions": sorted((c, rule_lab.REGISTRY[c]["side"]) for c in conds),
            "enumerated": enum, "greedy_max": greedy, "named": len(named_combinations(conds)) * len(EXITS),
            "exits": list(EXITS)}
    if look != 1:
        desc["look"] = look
        desc["max_filter"] = {"min_trades": MIN_TRADES, "min_sessions": MIN_SESSIONS,
                              "min_clusters": rule_lab.MIN_CLUSTERS_IN_MAX}
    return hashlib.sha256(json.dumps(desc, sort_keys=True).encode()).hexdigest()


def stage0_family_hash(rec, look=1):
    """The family hash of a stage 0 record, from the record's own fields (never from the run's
    condition list, or the check would bind nothing). Look 2 adds the same look and filter fields
    as family_hash(look=2)."""
    if look == 1 and rec.get("family_hash"):
        return rec["family_hash"]
    import hashlib
    desc = {"conditions": sorted((c, v["side"]) for c, v in rec["conditions"].items()),
            "enumerated": rec["family"]["enumerated"], "greedy_max": rec["family"]["greedy_max"],
            "named": rec["family"].get("named_combinations", 0), "exits": list(EXITS)}
    if look != 1:
        desc["look"] = look
        desc["max_filter"] = {"min_trades": MIN_TRADES, "min_sessions": MIN_SESSIONS,
                              "min_clusters": rule_lab.MIN_CLUSTERS_IN_MAX}
    return hashlib.sha256(json.dumps(desc, sort_keys=True).encode()).hexdigest()


def refuse_unless_allowed(out, conds, expected_hash, what, look=1):
    """The three refusals of the prereg correction (B2). Returns the provenance to record."""
    if os.path.exists(out):
        raise RefusedRun(f"{out} exists: the prereg allows one {what} run; move the old record aside by hand "
                         f"only for a crash before any statistic was written")
    commit, dirty = git_state()
    if dirty:
        raise RefusedRun("the working tree has uncommitted changes; commit first so the record names the code")
    got = family_hash(conds, look)
    if expected_hash is not None and got != expected_hash:
        raise RefusedRun(f"the family hash {got[:12]} is not the one on record ({str(expected_hash)[:12]}): "
                         f"the condition list or the family changed since")
    return {"commit": commit, "dirty": dirty, "family_hash": got}


def side_conditions(conds):
    by = defaultdict(list)
    for rid in conds:
        by[rule_lab.REGISTRY[rid]["side"]].append(rid)
    return by


def named_combinations(conds):
    """The catalogs' named combinations of more than three conditions (amendment 4 §4)."""
    try:
        import rule_lab_catalog
    except ImportError:
        return []
    have = set(conds)
    return [(side, tuple(parts)) for _, side, parts in rule_lab_catalog.NAMED_COMBINATIONS
            if set(parts) <= have]


def enumerate_family(conds):
    """Singles, pairs and triples of same-side conditions, and the named combinations, x the exits."""
    out = []
    for side, cs in side_conditions(conds).items():
        for size in (1, 2, 3):
            for combo in itertools.combinations(cs, size):
                for x in EXITS:
                    out.append((side, x, combo))
    for side, parts in named_combinations(conds):
        for x in EXITS:
            out.append((side, x, parts))
    return out


def max_family_size(conds):
    by = side_conditions(conds)
    enum = len(enumerate_family(conds))
    greedy = 0
    for side, cs in by.items():
        m = len(cs)
        per_start = sum(m - k for k in range(3, min(GREEDY_MAX, m)))
        greedy += GREEDY_STARTS * len(EXITS) * per_start
    return enum, greedy


def stats_of(S, N):
    import numpy as np
    m, t, n, g = rule_lab.clustered_matrix(S[None, :], N[None, :])
    return float(m[0]) if np.isfinite(m[0]) else None, (None if np.isnan(t[0]) else float(t[0])), int(n[0]), int(g[0])


def halves_positive(S, N):
    G = len(S)
    mid = G // 2
    a, b = S[:mid].sum() / max(N[:mid].sum(), 1), S[mid:].sum() / max(N[mid:].sum(), 1)
    return bool(N[:mid].sum() and N[mid:].sum() and a > 0 and b > 0), float(a), float(b)


def run_search(panel, conds, log=print):
    import numpy as np
    evaluated = {}

    def evaluate(side, x, combo, origin="enumerated"):
        key = (side, x, tuple(sorted(combo)))
        if key in evaluated:
            return evaluated[key]
        taken = panel.trades(key[2], side, x)
        S, N, valid = panel.session_sums(taken, side, x)
        mean, t, n, g = stats_of(S, N)
        evaluated[key] = {"S": S.astype("float32"), "N": N.astype("float32"), "mean": mean, "t": t, "n": n,
                          "sessions": g, "origin": origin}
        return evaluated[key]

    family = enumerate_family(conds)
    t0 = time.time()
    for i, (side, x, combo) in enumerate(family):
        evaluate(side, x, combo)
        if i % 5000 == 0:
            log(f"  enumerated {i}/{len(family)} ({time.time() - t0:.0f}s)")
    by = side_conditions(conds)
    for side, cs in by.items():
        for x in EXITS:
            triples = [(k, v) for k, v in evaluated.items() if k[0] == side and k[1] == x and len(k[2]) == 3
                       and v["n"] >= GREEDY_MIN_TRADES and v["t"] is not None]
            triples.sort(key=lambda kv: -kv[1]["t"])
            for (s_, x_, combo), v in triples[:GREEDY_STARTS]:
                current, cur_t = list(combo), v["t"]
                while len(current) < min(GREEDY_MAX, len(cs)):
                    best = None
                    for c in cs:
                        if c in current:
                            continue
                        r = evaluate(side, x, current + [c], origin="greedy")
                        if r["n"] >= GREEDY_MIN_TRADES and r["t"] is not None and r["t"] > cur_t and (
                                best is None or r["t"] > best[1]):
                            best = (c, r["t"])
                    if best is None:
                        break
                    current.append(best[0])
                    cur_t = best[1]
    return evaluated


def cscv_pbo(S_all, N_all, blocks=CSCV_BLOCKS, min_is=CSCV_MIN_IS_TRADES):
    """Probability of backtest overfitting (Bailey, Borwein, Lopez de Prado, Zhu 2017)."""
    import numpy as np
    K, G = S_all.shape
    edges = np.linspace(0, G, blocks + 1).astype(int)
    Sb = np.stack([S_all[:, edges[i]:edges[i + 1]].sum(axis=1) for i in range(blocks)], axis=1)
    Nb = np.stack([N_all[:, edges[i]:edges[i + 1]].sum(axis=1) for i in range(blocks)], axis=1)
    lambdas = []
    for is_blocks in itertools.combinations(range(blocks), blocks // 2):
        m = np.zeros(blocks, dtype=bool)
        m[list(is_blocks)] = True
        s_is, n_is = Sb[:, m].sum(axis=1), Nb[:, m].sum(axis=1)
        s_os, n_os = Sb[:, ~m].sum(axis=1), Nb[:, ~m].sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            perf_is = np.where(n_is >= min_is, s_is / n_is, -np.inf)
            perf_os = np.where(n_os > 0, s_os / n_os, np.nan)
        if not np.isfinite(perf_is).any():
            continue
        best = int(np.argmax(perf_is))
        if np.isnan(perf_os[best]):
            continue
        valid = perf_os[~np.isnan(perf_os)]
        omega = (np.sum(valid < perf_os[best]) + 0.5 * np.sum(valid == perf_os[best])) / (len(valid) + 1)
        omega = min(max(omega, 1e-6), 1 - 1e-6)
        lambdas.append(math.log(omega / (1 - omega)))
    if not lambdas:
        return None, 0
    return float(sum(1 for x in lambdas if x <= 0) / len(lambdas)), len(lambdas)


def judge(evaluated, days, alpha=rule_lab.ALPHA, b=rule_lab.BOOTSTRAP_B, log=print, look=1):
    """Look 1 (as run): every combination with a t enters the maximum. Look 2 (amendment 6): only
    combinations with MIN_TRADES trades and MIN_SESSIONS sessions set the bar, with the cluster guard."""
    import numpy as np
    import evaluation
    keys = list(evaluated)
    S = np.stack([evaluated[k]["S"] for k in keys])
    N = np.stack([evaluated[k]["N"] for k in keys])
    eligible, in_max = [], []
    for k in keys:
        v = evaluated[k]
        hp, h1, h2 = halves_positive(v["S"], v["N"])
        G = len(v["N"])
        v["halves"] = [h1 if v["N"][:G // 2].sum() else None, h2 if v["N"][G // 2:].sum() else None]
        powered = bool(v["n"] >= MIN_TRADES and v["sessions"] >= MIN_SESSIONS)
        in_max.append(powered if look != 1 else True)
        eligible.append(bool(powered and v["mean"] and v["mean"] > 0 and hp))
    log(f"  Romano-Wolf over {len(keys)} combinations ({sum(in_max)} in the maximum), B={b}")
    t_hat, rej, step, crits = rule_lab.romano_wolf_matrix(
        S, N, BLOCK, b=b, alpha=alpha, eligible=eligible, in_max=in_max,
        min_clusters=rule_lab.MIN_CLUSTERS_IN_MAX if look != 1 else 0)
    log("  CSCV")
    pbo, n_splits = cscv_pbo(S, N)
    order = sorted(range(len(keys)), key=lambda i: -(t_hat[i] if np.isfinite(t_hat[i]) else -1e9))
    best = order[0] if order else None
    dsr = None
    if best is not None:
        series = [float(x) for x, n in zip(S[best], N[best]) if n > 0]
        dsr = evaluation.deflated_sharpe_ratio(series, n_trials=len(keys))
    survivors = []
    if pbo is not None and pbo < 0.5:
        for i in order:
            if not rej[i]:
                continue
            side, x, combo = keys[i]
            if any(s["side"] == side and s["exit"] == x and set(s["conditions"]) <= set(combo) for s in survivors):
                continue
            survivors.append({"side": side, "exit": x, "conditions": list(combo), "t": float(t_hat[i]),
                              "mean": evaluated[keys[i]]["mean"], "n": evaluated[keys[i]]["n"],
                              "origin": evaluated[keys[i]].get("origin", "enumerated")})
            if len(survivors) >= MAX_SURVIVORS:
                break
    return keys, t_hat, rej, crits, pbo, n_splits, dsr, survivors, best, sum(in_max)


# ---- modes ------------------------------------------------------------------------

def _pool_map(func, args, workers):
    if workers <= 1:
        return [func(a) for a in args]
    import multiprocessing as mp
    with mp.Pool(workers) as pool:
        return pool.map(func, args, chunksize=1)


def build(db, conds, outcomes, workers, first=DISCOVERY_FIRST, last=DISCOVERY_LAST,
          start_ts=None, end_ts=DISCOVERY_END_TS, warm_ts=None, syms=None):
    conn = connect(db)
    syms = syms or symbols(conn)
    conn.close()
    start_ts = start_ts if start_ts is not None else _epoch(DISCOVERY_FIRST)
    warm_ts = warm_ts if warm_ts is not None else start_ts
    args = [(db, s, start_ts, end_ts, first, last, conds, outcomes, warm_ts) for s in syms]
    return _pool_map(precompute_symbol, args, workers)


def stage0(db, out, conds, workers, log=print):
    import numpy as np
    t0 = time.time()
    conn = connect(db)
    syms = symbols(conn)
    rows_2026 = count_2026_rows(conn)
    conn.close()
    # timing sample on 3 symbols, outcomes included only for timing (nothing from it is kept)
    sample = syms[:3]
    ts = time.time()
    _ = build(db, conds, outcomes=False, workers=1, syms=sample)
    t_cond = (time.time() - ts) / len(sample)
    results = build(db, conds, outcomes=False, workers=workers)
    newest = max((d for _, _, per_day, _ in results for d in per_day), default=None)
    assert newest is None or newest < "2026-01-01", "a 2026 bar was read"
    panel = Panel(results, conds, outcomes=False)
    per_day_bars = [n for _, _, per_day, _ in results for d, n in per_day.items()
                    if DISCOVERY_FIRST <= d <= DISCOVERY_LAST]
    complete = sum(1 for n in per_day_bars if n >= 70) / max(1, len(per_day_bars))
    cond_counts = {rid: int(panel.signals((rid,)).size) for rid in conds}
    family = enumerate_family(conds)
    combo_counts = {}
    tc = time.time()
    for side, x, combo in family:
        if x != EXITS[0]:
            continue
        combo_counts["+".join(combo)] = int(panel.signals(combo).size)
    t_combo = (time.time() - tc) / max(1, len(combo_counts))
    enum, greedy_max = max_family_size(conds)
    n200 = sum(1 for v in combo_counts.values() if v >= 200)
    est_cond_s = t_cond * len(syms) / max(1, workers)
    rec = {
        "look": "L55", "mode": "stage0", "written": datetime.now(IST).isoformat(timespec="seconds"),
        "db": os.path.basename(db), "symbols": len(syms),
        "sessions": len(panel.days), "first_session": panel.days[0] if panel.days else None,
        "last_session": panel.days[-1] if panel.days else None, "newest_bar_read": newest,
        "stock_sessions": len(per_day_bars), "share_with_70_bars": round(complete, 4),
        "bars_evaluated": int(panel.session.size),
        "rows_2026_count_only": {"symbols": len(rows_2026), "rows": int(sum(rows_2026.values()))},
        "conditions": {rid: {"side": rule_lab.REGISTRY[rid]["side"], "signals": cond_counts[rid]} for rid in conds},
        "family": {"enumerated": enum, "greedy_max": greedy_max, "max_total": enum + greedy_max,
                   "named_combinations": len(named_combinations(conds)) * len(EXITS),
                   "conditions_by_cohort": {str(c): sum(1 for r in conds if rule_lab.REGISTRY[r]["cohort"] == c)
                                            for c in sorted({rule_lab.REGISTRY[r]["cohort"] for r in conds})},
                   "condition_sets_with_200_signals": n200,
                   "combinations_with_200_signals": n200 * len(EXITS)},
        "timing": {"seconds_per_symbol_conditions": round(t_cond, 2), "workers": workers,
                   "estimate_discovery_precompute_s": round(est_cond_s * 3, 0),
                   "seconds_per_combination_signals": round(t_combo, 5),
                   "estimate_search_s": round((enum + greedy_max) * t_combo * 4, 0),
                   "estimate_romano_wolf_pass_s": round((enum + greedy_max) * rule_lab.BOOTSTRAP_B * len(panel.days)
                                                        * 10 / 5e10, 0),
                   "stage0_wall_s": round(time.time() - t0, 1)},
        "memory_estimate_mb": round(panel.session.size * (8 + 8 + 4 * 8 * 2 + len(conds)) / 1e6
                                    + (enum + greedy_max) * len(panel.days) * 8 / 1e6
                                    + 500 * 4000 * 8 * 8 / 1e6, 0),
        "family_hash": family_hash(conds),
        "halts": [],
    }
    if newest and newest >= "2026-01-01":
        rec["halts"].append("a 2026 bar was read")
    if complete < 0.9:
        rec["halts"].append("fewer than 90% of stock-sessions have 70 bars")
    if n200 * len(EXITS) < 50:
        rec["halts"].append("fewer than 50 combinations have 200 signals")
    rec["verdict"] = "HALT" if rec["halts"] else "OK: ready for review; no return was computed"
    with open(out, "w") as fh:
        json.dump(rec, fh, indent=1)
    log(json.dumps({k: rec[k] for k in ("sessions", "symbols", "share_with_70_bars", "family", "timing",
                                         "memory_estimate_mb", "verdict")}, indent=1))
    return rec


def default_stage0():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "research", "data",
                        "l55_stage0.json")


def discover(db, out, conds, workers, log=print, stage0_path=None, look=1):
    """The discovery run: look 1 as run on 2026-10-05, or look 2, amendment 6's filtered re-judgement.
    Refuses (RefusedRun) when `out` exists, the tree is dirty, or the family is not the one the stage 0
    record names (prereg correction of 2026-10-05, B2); look 2's hash includes its filter."""
    stage0_path = stage0_path or default_stage0()
    with open(stage0_path) as fh:
        s0 = json.load(fh)
    if sorted(s0["conditions"]) != sorted(conds):
        raise RefusedRun("the condition list is not the one stage 0 recorded")
    expected = stage0_family_hash(s0, look)
    prov = refuse_unless_allowed(out, conds, expected, f"look-{look} discovery", look=look)
    t0 = time.time()
    log("precomputing conditions and exits")
    results = build(db, conds, outcomes=True, workers=workers)
    newest = max((d for _, _, per_day, _ in results for d in per_day), default=None)
    assert newest is None or newest < "2026-01-01", "a 2026 bar was read"
    panel = Panel(results, conds, outcomes=True)
    log(f"  {panel.session.size} stock-bars, {len(panel.days)} sessions ({time.time() - t0:.0f}s)")
    evaluated = run_search(panel, conds, log)
    keys, t_hat, rej, crits, pbo, n_splits, dsr, survivors, best, n_in_max = judge(evaluated, panel.days, log=log,
                                                                                 look=look)
    rows = []
    for i, k in enumerate(keys):
        v = evaluated[k]
        rows.append({"side": k[0], "exit": k[1], "conditions": list(k[2]), "n": v["n"], "sessions": v["sessions"],
                     "mean": v["mean"], "t": None if math.isnan(t_hat[i]) else float(t_hat[i]),
                     "halves": v.get("halves"), "rejected": bool(rej[i]), "origin": v.get("origin", "enumerated")})
    rows.sort(key=lambda r: -(r["t"] if r["t"] is not None else -1e9))
    singles = {}
    for r in rows:
        if len(r["conditions"]) == 1:
            rid = r["conditions"][0]
            own = "R3" if rule_lab.REGISTRY[rid]["exit"] == "r" else "H30"
            if r["exit"] == own:
                singles[rid] = {"n": r["n"], "mean": r["mean"], "t": r["t"], "passed": r["rejected"]}
    powered_rows = [r for r in rows if r["n"] >= MIN_TRADES and r["sessions"] >= MIN_SESSIONS]
    rec = {"look": "L55", "look_number": look, "mode": "discover" if look == 1 else f"discover-look{look}",
           "written": datetime.now(IST).isoformat(timespec="seconds"),
           "sessions": [panel.days[0], panel.days[-1], len(panel.days)], "newest_bar_read": newest,
           "family_size": len(keys), "family_in_max": n_in_max,
           "max_filter": None if look == 1 else {"min_trades": MIN_TRADES, "min_sessions": MIN_SESSIONS,
                                                   "min_clusters": rule_lab.MIN_CLUSTERS_IN_MAX},
           "romano_wolf_critical_values": crits, "pbo": pbo, "cscv_splits": n_splits, "dsr_best": dsr,
           "best": (powered_rows[0] if look != 1 else rows[0]) if rows else None, "survivors": survivors,
           "top": rows[:50] if look == 1 else powered_rows[:50], "powered_rows": powered_rows, "rules": singles,
           "provenance": {**prov, "stage0": os.path.basename(stage0_path)}, "wall_s": round(time.time() - t0, 1)}
    with open(out, "w") as fh:
        json.dump(rec, fh, indent=1)
    log(json.dumps({k: rec[k] for k in ("family_size", "pbo", "dsr_best", "survivors", "wall_s")}, indent=1,
                   default=str))
    return rec


def confirm_2026(db, discovery_path, out, conds, workers, log=print):
    import numpy as np
    with open(discovery_path) as fh:
        disc = json.load(fh)
    survivors = disc.get("survivors") or []
    assert len(survivors) <= MAX_SURVIVORS, "more survivors than the prereg allows"
    if not survivors:
        log("no survivors: nothing to confirm, 2026 not read")
        return None
    need = sorted({c for s in survivors for c in s["conditions"]})
    prov = refuse_unless_allowed(out, conds, (disc.get("provenance") or {}).get("family_hash"), "confirmation")
    conn = connect(db)
    # The only 2026 metadata read before any bar: the cache's newest timestamp (N9).
    last_ts = conn.execute("SELECT MAX(ts) FROM candles WHERE interval='5m'").fetchone()[0]
    conn.close()
    end_ts = last_ts + 1
    first = "2026-01-01"
    last = datetime.fromtimestamp(last_ts, IST).date().isoformat()
    # history: the last sessions of 2025 feed the first 2026 sessions' inputs, like any session
    warm = _epoch("2025-12-15")
    results = build(db, need, outcomes=True, workers=workers, first=first, last=last,
                    start_ts=warm, end_ts=end_ts, warm_ts=warm)
    panel = Panel(results, need, outcomes=True)
    S_rows, N_rows, out_rows = [], [], []
    for s in survivors:
        taken = panel.trades(tuple(s["conditions"]), s["side"], s["exit"])
        S, N, _ = panel.session_sums(taken, s["side"], s["exit"])
        mean, t, n, g = stats_of(S, N)
        hp, h1, h2 = halves_positive(S, N)
        S_rows.append(S), N_rows.append(N)
        out_rows.append({**s, "n_2026": n, "sessions_2026": g, "mean_2026": mean, "t_2026": t,
                         "halves_2026": [h1, h2], "eligible": bool(n >= CONFIRM_MIN_TRADES and mean and mean > 0 and hp)})
    t_hat, rej, step, crits = rule_lab.romano_wolf_matrix(np.stack(S_rows), np.stack(N_rows), BLOCK,
                                                          eligible=[r["eligible"] for r in out_rows])
    for r, ok in zip(out_rows, rej):
        r["passed"] = bool(ok)
    rec = {"look": "L55", "mode": "confirm-2026", "written": datetime.now(IST).isoformat(timespec="seconds"),
           "window": [first, last], "survivors": out_rows, "critical_values": crits,
           "metadata_2026_read_before_bars": "MAX(ts) of candles only", "newest_ts": int(last_ts),
           "provenance": {**prov, "discovery": os.path.basename(discovery_path)}}
    with open(out, "w") as fh:
        json.dump(rec, fh, indent=1)
    log(json.dumps(rec, indent=1, default=str))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stage0", action="store_true")
    mode.add_argument("--discover", action="store_true")
    mode.add_argument("--confirm-2026", action="store_true")
    ap.add_argument("--db", default=default_db())
    ap.add_argument("--out", required=True)
    ap.add_argument("--catalog-rules", action="append", default=[],
                    help="a committed JSON of catalog rules in rule_lab.spec_signal's format (amendment 2)")
    ap.add_argument("--discovery-result", help="--confirm-2026: the discovery run's result file")
    ap.add_argument("--look", type=int, default=1, choices=(1, 2),
                    help="--discover: 1 = as run on 2026-10-05; 2 = amendment 6's filtered re-judgement")
    ap.add_argument("--stage0-record", help="--discover: the stage 0 record whose family this run must match "
                                             "(default docs/research/data/l55_stage0.json)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args(argv)
    registered, skipped = load_catalog_rules(args.catalog_rules)
    if skipped:
        print(f"{len(skipped)} catalog entries skipped (no usable spec): " + ", ".join(str(s["id"]) for s in skipped))
    conds = list(rule_lab.RULE_IDS)
    if args.stage0:
        stage0(args.db, args.out, conds, args.workers)
    elif args.discover:
        try:
            if args.look != 1 and "look2" not in os.path.basename(args.out):
                ap.error("--look 2 writes to its own file: name it ...look2...json")
            discover(args.db, args.out, conds, args.workers, stage0_path=args.stage0_record, look=args.look)
        except RefusedRun as e:
            sys.exit(f"REFUSED: {e}")
    else:
        if not args.discovery_result:
            ap.error("--confirm-2026 needs --discovery-result")
        try:
            confirm_2026(args.db, args.discovery_result, args.out, conds, args.workers)
        except RefusedRun as e:
            sys.exit(f"REFUSED: {e}")


if __name__ == "__main__":
    main()
