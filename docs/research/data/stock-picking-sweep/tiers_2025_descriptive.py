# Read-only descriptive statistics from the repo's 2025 bhavcopies (all before the
# held-out start 2026-01-02). No strategy return is computed. Nothing is written to the repo.
import zipfile, io, csv, os, re, math, statistics as st, collections, glob, json, sys
D = "/Users/harshgupta/Projects/webapp/backend/data/bhav_daily"
ETF = re.compile(r"(BEES|ETF|IETF|CASE)$")
files = sorted(f for f in glob.glob(os.path.join(D, "2025*.zip")))
days = []
rows_by_day = []
series_seen = collections.defaultdict(set)   # symbol -> set of series seen in window
for f in files:
    with zipfile.ZipFile(f) as z, z.open(z.namelist()[0]) as fh:
        day = {}
        for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="ignore")):
            srs = (r.get("SctySrs") or "").strip()
            sym = (r.get("TckrSymb") or "").strip()
            if srs in ("EQ", "BE", "BZ", "SM", "ST", "SZ"):
                series_seen[sym].add(srs)
            if srs not in ("EQ", "BE", "BZ"):
                continue
            isin = (r.get("ISIN") or "").strip()
            if isin.startswith("INF") or ETF.search(sym):
                continue
            try:
                o, h, l, c, last, pc = (float(r[k] or 0) for k in ("OpnPric", "HghPric", "LwPric", "ClsPric", "LastPric", "PrvsClsgPric"))
                val = float(r.get("TtlTrfVal") or 0); ntr = int(float(r.get("TtlNbOfTxsExctd") or 0))
            except ValueError:
                continue
            day[sym] = (srs, o, h, l, c, last, pc, val, ntr)
        days.append(os.path.basename(f)[:8]); rows_by_day.append(day)
N = len(days)
W = 126
win = rows_by_day[-W:]
print("sessions 2025:", N, "window:", days[-W], "->", days[-1])
# ranking like the repo: EQ rows only, median traded value over 126 sessions, absent = 0; price >= 20 and traded (EQ) on last session
last = rows_by_day[-1]
cands = []
for sym, rec in last.items():
    if rec[0] != "EQ" or rec[4] < 20:
        continue
    vals = [(d[sym][7] if sym in d and d[sym][0] == "EQ" else 0.0) for d in win]
    cands.append((st.median(vals), sym))
cands.sort(reverse=True)
print("eligible EQ names (price>=20, traded last session):", len(cands))
for rk in (1, 50, 100, 200, 300, 400, 500, 600, 800, 1000, 1250, 1500, 1750, 2000):
    if rk <= len(cands):
        print(f"rank {rk:5d}: median daily traded value = Rs {cands[rk-1][0]/1e7:9.2f} crore")
tiers = [(1, 200), (201, 400), (401, 600), (601, 800), (801, 1000), (1001, 1500), (1501, len(cands))]
BANDS = (0.02, 0.05, 0.10, 0.20)
def lock(rec):
    srs, o, h, l, c, lastp, pc, val, ntr = rec
    if pc <= 0 or c <= 0: return 0
    ret = c / pc - 1
    for b in BANDS:
        if c >= h - 1e-9 and (b - 0.0030) <= ret <= (b + 0.0010): return +1
        if c <= l + 1e-9 and (-b - 0.0010) <= ret <= (-b + 0.0030): return -1
    return 0
def cs(h0, l0, c0, h1, l1):
    # Corwin-Schultz with overnight adjustment
    if l1 > c0: g = l1 - c0; h1 -= g; l1 -= g
    elif h1 < c0: g = c0 - h1; h1 += g; l1 += g
    if min(h0, l0, h1, l1) <= 0: return None
    b = math.log(h0 / l0) ** 2 + math.log(h1 / l1) ** 2
    g = math.log(max(h0, h1) / min(l0, l1)) ** 2
    k = 3 - 2 * math.sqrt(2)
    a = (math.sqrt(2 * b) - math.sqrt(b)) / k - math.sqrt(g / k)
    return 2 * (math.exp(a) - 1) / (1 + math.exp(a))
out = []
for lo, hi in tiers:
    names = [n for _, n in cands[lo - 1:hi]]
    meds = [v for v, _ in cands[lo - 1:hi]]
    sd = up = dn = onep = absent = 0
    ntrs = []; locked_names = set(); cs_list = []; ar_list = []; prices = []; be_names = 0
    for n in names:
        if series_seen[n] & {"BE", "BZ"}: be_names += 1
        seq = [d.get(n) for d in win]
        prices.append(last[n][4])
        cs_vals = []; prods = []
        for i, rec in enumerate(seq):
            sd += 1
            if rec is None or rec[8] == 0:
                absent += 1; continue
            ntrs.append(rec[8])
            k = lock(rec)
            if k > 0: up += 1; locked_names.add(n)
            if k < 0: dn += 1; locked_names.add(n)
            if abs(rec[2] - rec[3]) < 1e-9: onep += 1
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            if nxt is not None and nxt[8] > 0 and rec[2] > 0 and rec[3] > 0 and nxt[2] > 0 and nxt[3] > 0 and rec[5] > 0:
                v = cs(rec[2], rec[3], rec[5], nxt[2], nxt[3])
                if v is not None: cs_vals.append(max(v, 0.0))
                eta0 = (math.log(rec[2]) + math.log(rec[3])) / 2
                eta1 = (math.log(nxt[2]) + math.log(nxt[3])) / 2
                cl = math.log(rec[5])
                prods.append((cl - eta0) * (cl - eta1))
        if len(cs_vals) >= 40: cs_list.append(st.mean(cs_vals))
        if len(prods) >= 40: ar_list.append(math.sqrt(max(4 * st.mean(prods), 0.0)))
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))] if xs else float("nan")
    out.append({
        "tier": f"{lo}-{hi}", "n": len(names),
        "adv_median_cr": st.median(meds) / 1e7, "adv_min_cr": min(meds) / 1e7, "adv_max_cr": max(meds) / 1e7,
        "median_trades_per_day": st.median(ntrs) if ntrs else None,
        "pct_stockdays_absent": 100 * absent / sd,
        "pct_stockdays_locked_up": 100 * up / sd, "pct_stockdays_locked_down": 100 * dn / sd,
        "pct_stockdays_one_price": 100 * onep / sd,
        "pct_names_locked_at_least_once": 100 * len(locked_names) / len(names),
        "pct_names_seen_in_BE_BZ_2025": 100 * be_names / len(names),
        "CS_spread_bp_median": 1e4 * st.median(cs_list) if cs_list else None,
        "CS_spread_bp_p75": 1e4 * q(cs_list, .75),
        "AR_spread_bp_median": 1e4 * st.median(ar_list) if ar_list else None,
        "AR_spread_bp_p75": 1e4 * q(ar_list, .75),
        "AR_pct_zero": 100 * sum(1 for x in ar_list if x == 0) / len(ar_list) if ar_list else None,
        "median_price": st.median(prices),
        "order_70k_pct_of_adv_at_tier_median": 100 * 70000 / st.median(meds),
        "order_70k_pct_of_adv_at_tier_min": 100 * 70000 / max(min(meds), 1),
    })
for o in out:
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items()}))
# series population on last session
c = collections.Counter()
for sym, s in series_seen.items():
    for x in s: c[x] += 1
print("symbols seen per series during 2025:", dict(c))
both = sum(1 for s in series_seen.values() if "EQ" in s and (s & {"BE", "BZ"}))
print("symbols seen in both EQ and BE/BZ during 2025:", both)
