"""
PEAD Stage A — the statistic (research look L39, no trial).
Pre-registration: docs/research/prereg-pead-stage-a.md. Reads the event table
built by pead_events.py and total-return prices from nse_prices.py.

    .venv/bin/python research/pead_stage_a.py      # one run; writes docs/research/data/pead_stage_a.json
"""

import bisect
import collections
import datetime
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

import nse_prices as npx  # noqa: E402
import pead_events as pe  # noqa: E402

OUT = os.path.join(pe.DOCS_DATA, "pead_stage_a.json")
SLOTS = 30
HOLD = 60
WARMUP_EVENTS = 150
PCTL = 0.67
GO_MEAN = 0.0037
GO_T = 1.8
NW_LAGS = 3
CAPITAL = 1_000_000.0
STT, STAMP_BUY, NSE_TXN, SEBI, GST, SLIP, DP = 0.0010, 0.00015, 0.0000307, 0.000001, 0.18, 0.0005, 15.34
BUY_PCT = STT + STAMP_BUY + NSE_TXN + SEBI + GST * (NSE_TXN + SEBI) + SLIP
SELL_PCT = STT + NSE_TXN + SEBI + GST * (NSE_TXN + SEBI) + SLIP + DP / (CAPITAL / SLOTS)


def pctl(xs, p):
    s = sorted(xs)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def nw_t(xs, lags=NW_LAGS):
    n = len(xs)
    if n < 3:
        return None
    m = st.mean(xs)
    d = [x - m for x in xs]
    g0 = sum(v * v for v in d) / n
    var = g0
    for l in range(1, lags + 1):
        gl = sum(d[i] * d[i - l] for i in range(l, n)) / n
        var += 2 * (1 - l / (lags + 1)) * gl
    se = math.sqrt(var / n) if var > 0 else None
    return m / se if se else None


def qualify(events):
    """Expanding 67th-percentile breakpoint over all earlier events (by broadcast)."""
    ev = sorted(events, key=lambda e: e["broadcast"])
    out, prior = [], []
    i = 0
    while i < len(ev):
        j = i
        while j < len(ev) and ev[j]["broadcast"] == ev[i]["broadcast"]:
            j += 1
        for e in ev[i:j]:
            if len(prior) >= WARMUP_EVENTS:
                e = dict(e, breakpoint=pctl(prior, PCTL))
                e["top"] = e["sue_m"] >= e["breakpoint"]
            else:
                e = dict(e, breakpoint=None, top=False, warmup=True)
            out.append(e)
        prior += [e["sue_m"] for e in ev[i:j]]
        i = j
    return out


def run():
    data = json.load(open(pe.EVENTS_PATH))
    events = qualify(data["events"])
    sessions, chains, _, _ = npx.load()
    by_month, _ = pe.membership()
    nxt = npx.symbol_chains(os.path.join(npx.BHAV_DIR, "symbolchange.csv"))
    cache = {}
    sidx = {d: i for i, d in enumerate(sessions)}

    def ret(chain_name, i):
        c = chains.get(chain_name)
        if c is None:
            return None
        k = bisect.bisect_left(c["idx"], i)
        if k < len(c["idx"]) and c["idx"][k] == i and k > 0 and c["idx"][k - 1] == i - 1:
            return c["close"][k] / c["close"][k - 1] - 1
        return None

    member_chain = {}
    for m, syms in by_month.items():
        member_chain[m] = [npx.canonical(s, nxt, cache) for s in syms]

    tops = sorted((e for e in events if e.get("top")), key=lambda e: (e["entry"], e["symbol"]))
    entries_by_day = collections.defaultdict(list)
    for e in tops:
        entries_by_day[e["entry"]].append(e)
    first = sidx[tops[0]["entry"]] if tops else 0
    last = max(sidx[e["exit"]] for e in tops) if tops else 0

    active = {}          # chain -> exit index
    counts = collections.Counter()
    daily = []           # (date, book_gross, bench, book_net, n_active)
    for i in range(first, last + 1):
        d = sessions[i]
        # returns for positions held into today (entered at an earlier close)
        rs = [r for r in (ret(ch, i) for ch in active) if r is not None]
        mem = member_chain.get(d[:7], [])
        br = [r for r in (ret(ch, i) for ch in mem) if r is not None]
        n_before = len(active)
        cost = 0.0
        # exits at today's close
        for ch in [ch for ch, x in active.items() if x == i]:
            del active[ch]
            cost += SELL_PCT
            counts["exits"] += 1
        # entries at today's close
        for e in entries_by_day.get(d, []):
            ch = e["chain"]
            exit_i = sidx[e["exit"]]
            if ch in active:
                active[ch] = max(active[ch], exit_i)
                counts["resets"] += 1
                continue
            if len(active) >= SLOTS:
                counts["skipped_full"] += 1
                continue
            active[ch] = exit_i
            cost += BUY_PCT
            counts["entries"] += 1
        if rs and br:
            g = st.mean(rs)
            b = st.mean(br)
            daily.append((d, g, b, g - cost / max(n_before, 1), n_before))
    # months
    months = collections.OrderedDict()
    for d, g, b, net, n in daily:
        months.setdefault(d[:7], []).append((g, b, net))

    def comp(xs):
        v = 1.0
        for x in xs:
            v *= 1 + x
        return v - 1

    mrows = [(m, comp([x[0] for x in v]) - comp([x[1] for x in v]), comp([x[2] for x in v]) - comp([x[1] for x in v]))
             for m, v in months.items()]
    gross = [r[1] for r in mrows]
    net = [r[2] for r in mrows]
    half = len(mrows) // 2
    h1, h2 = gross[:half], gross[half:]
    yearly = collections.defaultdict(float)
    for m, g, _ in mrows:
        yearly[m[:4]] += g
    corr = None
    p3i = os.path.join(pe.DOCS_DATA, "momentum_3i_partA.json")
    if os.path.exists(p3i):
        a = json.load(open(p3i))
        ex3 = dict(zip(a["months"][1:], a["excess_net_series"]))
        pairs = [(g, ex3[m]) for m, g, _ in mrows if m in ex3]
        if len(pairs) > 5:
            xs, ys = zip(*pairs)
            mx, my = st.mean(xs), st.mean(ys)
            cov = sum((x - mx) * (y - my) for x, y in pairs)
            corr = cov / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    mean_g, t_g = st.mean(gross), nw_t(gross)
    out = {"prereg": "prereg-pead-stage-a.md", "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "events_total": len(events), "events_warmup": sum(1 for e in events if e.get("warmup")),
           "events_top_tercile": len(tops), "portfolio_counts": dict(counts),
           "first_month": mrows[0][0] if mrows else None, "last_month": mrows[-1][0] if mrows else None,
           "months": len(mrows),
           "gross": {"mean_monthly": mean_g, "nw_t": t_g, "sd": st.stdev(gross) if len(gross) > 1 else None},
           "net_10L": {"mean_monthly": st.mean(net), "nw_t": nw_t(net)},
           "halves_gross": {"first": {"mean": st.mean(h1), "nw_t": nw_t(h1), "months": len(h1)},
                            "second": {"mean": st.mean(h2), "nw_t": nw_t(h2), "months": len(h2)}},
           "yearly_gross_sum": dict(yearly),
           "avg_active_positions": st.mean([n for *_, n in daily]) if daily else None,
           "corr_with_3i_partA_monthly_excess": corr,
           "GO": bool(mean_g >= GO_MEAN and (t_g or 0) >= GO_T),
           "go_rule": {"mean_ge_0_37pct": mean_g >= GO_MEAN, "nw_t_ge_1_8": (t_g or 0) >= GO_T},
           "monthly": [{"month": m, "gross_excess": g, "net_excess": n} for m, g, n in mrows]}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "monthly"}, indent=1, default=str))
    return out


if __name__ == "__main__":
    run()
