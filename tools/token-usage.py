#!/usr/bin/env python3
"""Token usage per Claude Code session, from the real transcripts.

Reads the JSONL transcripts Claude Code writes under
~/.claude/projects/<project>/ and sums the usage each API call actually
reported. Nothing here is estimated from message lengths.

Why the headline number needs care: **cache reads dominate the raw count and
cost a fraction of fresh input.** A session can show 500M "tokens" and be
mostly the same context re-read each turn. So this reports three things:

  raw        every token the API counted, cache reads included
  billable   cost-weighted equivalent, at the multipliers below
  fresh      input + output only — the work that was genuinely new

Usage:
    python3 token-usage.py                 # all sessions, newest first
    python3 token-usage.py --top 5         # the 5 largest
    python3 token-usage.py --session 2d14  # one session, by id prefix
    python3 token-usage.py --detail 2d14   # per-model breakdown for one
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / ".claude" / "projects"

# Per-million-token list prices. EDIT IF THESE HAVE CHANGED — they are not
# fetched from anywhere and will silently go stale.
PRICING = {
    "opus":   {"in": 15.00, "out": 75.00},
    "sonnet": {"in": 3.00,  "out": 15.00},
    "haiku":  {"in": 0.80,  "out": 4.00},
    "fable":  {"in": 3.00,  "out": 15.00},
}
CACHE_READ_MULT = 0.10    # cache reads bill at ~10% of fresh input
CACHE_WRITE_MULT = 1.25   # writing to cache bills at ~125% of fresh input


def price_for(model):
    m = (model or "").lower()
    for key, p in PRICING.items():
        if key in m:
            return p, key
    return None, None


def usage_of(entry):
    """Return (input, cache_write, cache_read, output) for one record.

    Top-level counters are sometimes zero with the real figures split across
    `iterations`; prefer whichever is populated rather than trusting one.
    """
    msg = entry.get("message") or {}
    u = msg.get("usage")
    if not isinstance(u, dict):
        return None
    top = (u.get("input_tokens") or 0, u.get("cache_creation_input_tokens") or 0,
           u.get("cache_read_input_tokens") or 0, u.get("output_tokens") or 0)
    if any(top):
        return top
    it = u.get("iterations")
    if isinstance(it, list) and it:
        return (sum(i.get("input_tokens") or 0 for i in it),
                sum(i.get("cache_creation_input_tokens") or 0 for i in it),
                sum(i.get("cache_read_input_tokens") or 0 for i in it),
                sum(i.get("output_tokens") or 0 for i in it))
    return None


def scan(path):
    per_model = defaultdict(lambda: [0, 0, 0, 0])   # in, cw, cr, out
    calls = 0
    first = last = None
    seen_ids = set()
    with path.open(errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            ts = e.get("timestamp")
            if ts:
                first = first or ts
                last = ts
            if e.get("type") != "assistant":
                continue
            # the same assistant message can appear more than once; count once
            mid = (e.get("message") or {}).get("id")
            if mid:
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
            u = usage_of(e)
            if not u:
                continue
            calls += 1
            model = (e.get("message") or {}).get("model") or "unknown"
            slot = per_model[model]
            for i in range(4):
                slot[i] += u[i]
    return per_model, calls, first, last


def cost_of(per_model):
    total = 0.0
    unknown = 0
    for model, (i, cw, cr, o) in per_model.items():
        p, _ = price_for(model)
        if not p:
            unknown += i + cw + cr + o
            continue
        total += (i / 1e6) * p["in"]
        total += (cw / 1e6) * p["in"] * CACHE_WRITE_MULT
        total += (cr / 1e6) * p["in"] * CACHE_READ_MULT
        total += (o / 1e6) * p["out"]
    return total, unknown


def human(n):
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n/div:.2f}{unit}"
    return str(int(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0, help="show only the N largest")
    ap.add_argument("--session", help="filter by session-id prefix")
    ap.add_argument("--detail", help="per-model breakdown for one session-id prefix")
    args = ap.parse_args()

    files = sorted(ROOT.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print(f"no transcripts under {ROOT}", file=sys.stderr)
        return 1

    want = args.detail or args.session
    if want:
        files = [f for f in files if f.stem.startswith(want)]
        if not files:
            print(f"no session starting with {want!r}", file=sys.stderr)
            return 1

    rows = []
    for f in files:
        per_model, calls, first, last = scan(f)
        if not calls:
            continue
        i = sum(v[0] for v in per_model.values())
        cw = sum(v[1] for v in per_model.values())
        cr = sum(v[2] for v in per_model.values())
        o = sum(v[3] for v in per_model.values())
        cost, unknown = cost_of(per_model)
        rows.append({"file": f, "per_model": per_model, "calls": calls,
                     "in": i, "cw": cw, "cr": cr, "out": o,
                     "raw": i + cw + cr + o, "fresh": i + o,
                     "cost": cost, "unknown": unknown, "first": first, "last": last})

    rows.sort(key=lambda r: r["raw"], reverse=True)
    if args.top:
        rows = rows[: args.top]

    if args.detail:
        r = rows[0]
        print(f"session {r['file'].stem}")
        print(f"  project   {r['file'].parent.name}")
        print(f"  span      {(r['first'] or '?')[:19]} -> {(r['last'] or '?')[:19]}")
        print(f"  API calls {r['calls']:,}\n")
        print(f"  {'model':<26}{'input':>11}{'cache wr':>11}{'cache rd':>11}{'output':>11}")
        for model, (i, cw, cr, o) in sorted(r["per_model"].items(),
                                            key=lambda kv: -sum(kv[1])):
            print(f"  {model:<26}{human(i):>11}{human(cw):>11}{human(cr):>11}{human(o):>11}")
        print(f"\n  raw      {human(r['raw']):>10}   every token counted, cache reads included")
        print(f"  fresh    {human(r['fresh']):>10}   input + output only — genuinely new work")
        print(f"  cache rd {human(r['cr']):>10}   {100*r['cr']/max(r['raw'],1):.1f}% of raw, billed at {CACHE_READ_MULT:g}x")
        print(f"\n  estimated cost  ${r['cost']:,.2f}   (list prices in this file; edit if stale)")
        if r["unknown"]:
            print(f"  NOT PRICED      {human(r['unknown'])} tokens on an unrecognised model")
        return 0

    print(f"{'session':<14}{'calls':>7}{'raw':>10}{'fresh':>9}{'cache rd':>10}{'output':>9}{'cost':>10}  last")
    print("-" * 88)
    tot_raw = tot_fresh = tot_out = tot_cost = 0
    for r in rows:
        tot_raw += r["raw"]; tot_fresh += r["fresh"]; tot_out += r["out"]; tot_cost += r["cost"]
        print(f"{r['file'].stem[:12]:<14}{r['calls']:>7,}{human(r['raw']):>10}{human(r['fresh']):>9}"
              f"{human(r['cr']):>10}{human(r['out']):>9}{'$'+format(r['cost'],',.2f'):>10}  {(r['last'] or '')[:10]}")
    print("-" * 88)
    print(f"{'TOTAL':<14}{'':>7}{human(tot_raw):>10}{human(tot_fresh):>9}{'':>10}{human(tot_out):>9}{'$'+format(tot_cost,',.2f'):>10}")
    print(f"\n{len(rows)} sessions. 'raw' is inflated by cache reads — 'fresh' and 'cost' are")
    print("the honest measures of how much work a session actually did.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
