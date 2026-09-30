"""Research look L50 — does an NSE bulk or block deal disclosure move the stock at the
next open past cost?

Pre-registered: docs/research/prereg-bulk-block-deals.md (commit 66c1ed3), committed
before this file was written. Measurement only: no strategy, no backtest, no trial
(the count stays at 202). Nothing in the live path imports this
(tests/test_research_splits.py).

Order the prereg fixes:
  stage 0 (reads NO price; its only query on the candle table selects symbol and time)
    1. source: every month x type fetched as NSE's CSV; six fixed-seed dates re-queried
       one day at a time must return exactly the month file's rows
    2. boundaries: no deal after 2025-12-22, no bar after 2025-12-23
    3. symbols mapped through NSE's symbolchange.csv; point-in-time NIFTY 100 on the
       entry session; members with events but no cached bars listed
    4. classes: BULK_BUY / BULK_SELL / MIXED by the 2:1 net-quantity rule, BLOCK
    5. bars (timestamps only) per class x horizon -> the family (cells with >= 60)
    6. void rule: BULK_ALL under 60 at every horizon -> VOID, no price read
    7. halves and Kite fetch runs (#108)
  then, only with --measure and after review, ONE pass: direction-aligned net return,
  SE clustered by entry session, Student-t p, halves, BH q=0.10 over the family, gate.

Run from backend/ against the main checkout's cache (read-only):
    L50_CANDLE_DB=/Users/harshgupta/Projects/webapp/backend/data/kite_history.db \\
        nice -n 15 .venv/bin/python -m research.deals_l50 --stage0-only
"""
import argparse
import bisect
import csv
import io
import json
import math
import os
import random
import sqlite3
import statistics as st
import sys
import time
from collections import OrderedDict, defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/

from research import splits  # noqa: E402
from research.kronos_feature_ic import (adjustment_boundaries, benjamini_hochberg,  # noqa: E402
                                        load_membership_rows, membership_asof)

# ---- the pre-registration's constants, named once ---------------------------------

DEAL_FIRST = "2024-09-19"          # the session before the first sample session
DEAL_LAST = "2025-12-22"           # the session before the last sample session
SAMPLE_START = "2024-09-20"
SAMPLE_END = "2025-12-23"          # five sessions before splits.HELD_OUT_START
BAR_BOUND_EXCLUSIVE = "2025-12-24"  # no bar at or after this IST midnight is loaded
ENTRY_BAR = "09:20"                # entry at this bar's open (the 09:15 open is the auction)
AUCTION_BAR = "09:15"
EXITS = OrderedDict([("15m", "09:30"), ("30m", "09:45"), ("60m", "10:15")])  # exit at these bars' close
COST_BP = 16.63
MIN_EVENTS = 60
BH_Q = 0.10
DOMINANCE = 1.0 / 3.0              # |B - S| >= G/3: the larger side at least twice the smaller
INFO_THRESHOLDS = (0.0, 0.5)       # counts only, for information
MIN_SYMBOLS_REGULAR = 50           # a regular session: >= 50 symbols with a 09:20 bar
SEED = 123
N_COMPLETENESS = 6
KINDS = OrderedDict([("BULK", "bulk_deals"), ("BLOCK", "block_deals")])
CLASSES = ("BULK_BUY", "BULK_SELL", "BULK_ALL")
IST_OFFSET = 19800                 # seconds; bar ts are UTC epochs of IST bar starts

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPO = os.path.dirname(BACKEND)
CACHE_DIR = os.path.join(BACKEND, "data", "nse_deals")
OUT_DIR = os.path.join(REPO, "docs", "research", "data")
STAGE0_OUT = os.path.join(OUT_DIR, "l50_stage0.json")
EVENTS_CSV = os.path.join(OUT_DIR, "l50_events.csv")
RESULT_OUT = os.path.join(OUT_DIR, "l50_result.json")
CANDLE_DB = os.environ.get("L50_CANDLE_DB", os.path.join(BACKEND, "data", "kite_history.db"))

NSE = "https://www.nseindia.com"
REPORT_PAGE = "/report-detail/display-bulk-and-block-deals"
DEALS_API = "/api/historicalOR/bulk-block-short-deals?optionType=%s&from=%s&to=%s&csv=true"
SYMBOLCHANGE_URL = "https://nsearchives.nseindia.com/content/equities/symbolchange.csv"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120 Safari/537.36"),
    "Accept": "text/csv, application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_GAP_S = 2.5
ATTEMPTS = 3


# ---- dates and the fetch plan (pure) -----------------------------------------------

def iso(d):
    return d.isoformat() if isinstance(d, date) else d


def dmy(iso_date):
    """'2024-09-19' -> '19-09-2024', the report's query format."""
    y, m, d = iso_date.split("-")
    return "%s-%s-%s" % (d, m, y)


def month_windows(first=DEAL_FIRST, last=DEAL_LAST):
    """[(from_iso, to_iso)] one per calendar month, clipped to [first, last]."""
    lo, hi = date.fromisoformat(first), date.fromisoformat(last)
    out, cur = [], date(lo.year, lo.month, 1)
    while cur <= hi:
        nxt = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)
        out.append((max(cur, lo).isoformat(), min(nxt - timedelta(days=1), hi).isoformat()))
        cur = nxt
    return out


# ---- parsing (pure) -----------------------------------------------------------------

def _num(s):
    s = (s or "").strip().replace(",", "")
    return float(s) if s not in ("", "-") else None


def parse_deals_csv(text):
    """NSE's bulk/block CSV -> [{date, symbol, name, client, side, qty, price, remarks}].

    Handles the BOM, header cells padded with a space, Indian digit grouping
    ('3,03,645') and Remarks cells holding a line break (hence csv, not lines).
    Returns None if the header is not the report's, so a changed format or an error
    page is never read as an empty day."""
    if text is None:
        return None
    text = text.lstrip("\ufeff")
    if text.lstrip().startswith("{"):
        try:
            data = json.loads(text)
        except ValueError:
            return None
        return [] if isinstance(data, dict) and data.get("data") == [] else None
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return None
    hdr = [h.strip().lower() for h in rows[0]]
    if len(hdr) < 7 or hdr[0] != "date" or hdr[1] != "symbol" or "client" not in hdr[3]:
        return None
    out = []
    for r in rows[1:]:
        if not r or not any(c.strip() for c in r):
            continue
        side = r[4].strip().upper()
        out.append({
            "date": datetime.strptime(r[0].strip().title(), "%d-%b-%Y").date().isoformat(),
            "symbol": r[1].strip().upper(),
            "name": r[2].strip(),
            "client": " ".join(r[3].split()),
            "side": side,
            "qty": int(_num(r[5]) or 0),
            "price": _num(r[6]),
            "remarks": (r[7].strip() if len(r) > 7 else ""),
        })
    return out


def parse_symbol_changes(text):
    """NSE's symbolchange.csv -> {old: [(applicable_from_iso, new)]}."""
    out = defaultdict(list)
    for p in csv.reader(io.StringIO((text or "").lstrip("\ufeff"))):
        p = [x.strip() for x in p]
        if len(p) < 4 or not p[1] or not p[2] or p[1] == "SM_KEY_SYMBOL":
            continue
        try:
            when = datetime.strptime(p[3].title(), "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        out[p[1].upper()].append((when, p[2].upper()))
    for k in out:
        out[k].sort()
    return dict(out)


def canon(symbol, on_date, changes):
    """Today's symbol for a stock that traded as `symbol` on `on_date`: follow every
    change applicable AFTER the date the stock took its current symbol (a change that
    took effect on or before it belongs to an earlier holder of that symbol, so it is
    not followed). The first step compares with the deal date; each later step with
    the previous rename's effective date."""
    seen, since = set(), on_date
    while symbol in changes and symbol not in seen:
        seen.add(symbol)
        later = [(d, new) for d, new in changes[symbol] if d > since]
        if not later:
            break
        since, symbol = later[0]
    return symbol


# ---- events (pure) -------------------------------------------------------------------

def aggregate(rows, kind, changes):
    """{(symbol_today, deal_date, kind): {"B", "S", "rows", "clients", "deal_symbols"}}."""
    out = OrderedDict()
    for r in rows:
        key = (canon(r["symbol"], r["date"], changes), r["date"], kind)
        a = out.setdefault(key, {"B": 0, "S": 0, "rows": 0, "clients": [], "deal_symbols": set()})
        if r["side"] == "BUY":
            a["B"] += r["qty"]
        elif r["side"] == "SELL":
            a["S"] += r["qty"]
        a["rows"] += 1
        a["clients"].append("%s:%s:%d" % (r["side"], r["client"], r["qty"]))
        a["deal_symbols"].add(r["symbol"])
    return out


def bulk_side(b, s, threshold=DOMINANCE):
    """+1 BUY, -1 SELL, 0 MIXED. Directional if |B - S| >= threshold * (B + S) and the
    net is not zero; threshold 1/3 means the larger side is at least twice the smaller."""
    g, n = b + s, b - s
    if g <= 0 or n == 0 or abs(n) < threshold * g:
        return 0
    return 1 if n > 0 else -1


def bulk_class(side):
    return {1: "BULK_BUY", -1: "BULK_SELL", 0: "MIXED"}[side]


def classes_of(ev):
    """The tested classes an event belongs to (none for MIXED or BLOCK)."""
    if ev["kind"] != "BULK" or ev["side"] == 0:
        return []
    return [bulk_class(ev["side"]), "BULK_ALL"]


# ---- sessions and bars (pure) --------------------------------------------------------

def ts_to_ist(ts):
    """(date_iso, 'HH:MM') of a bar's IST start from its UTC epoch."""
    t = datetime.utcfromtimestamp(ts + IST_OFFSET)
    return t.date().isoformat(), t.strftime("%H:%M")


def ist_midnight_epoch(iso_date):
    d = date.fromisoformat(iso_date)
    return int((datetime(d.year, d.month, d.day) - datetime(1970, 1, 1)).total_seconds()) - IST_OFFSET


def regular_sessions(bar_times, min_symbols=MIN_SYMBOLS_REGULAR):
    """Dates on which at least `min_symbols` symbols have a bar starting 09:20."""
    count = defaultdict(int)
    for days in bar_times.values():
        for d, hhmms in days.items():
            if ENTRY_BAR in hhmms:
                count[d] += 1
    return sorted(d for d, n in count.items() if n >= min_symbols)


def next_session(d, sessions):
    """First session strictly after date d, or None."""
    i = bisect.bisect_right(sessions, d)
    return sessions[i] if i < len(sessions) else None


def prev_session(d, sessions):
    """Last session strictly before date d, or None."""
    i = bisect.bisect_left(sessions, d)
    return sessions[i - 1] if i > 0 else None


def bars_present(hhmms, horizon):
    return hhmms is not None and ENTRY_BAR in hhmms and EXITS[horizon] in hhmms


def boundary_between(bounds, d, entry):
    """True if a Kite fetch-run boundary (a from_date, 'YYYY-MM-DD...') falls in (d, entry]."""
    return any(d < b[:10] <= entry for b in bounds or [])


# ---- statistics (pure) ---------------------------------------------------------------

def _betacf(a, b, x):
    """Continued fraction for the incomplete beta (Numerical Recipes, betacf)."""
    fpmin, eps = 1e-300, 3e-14
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > fpmin else fpmin)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betai(a, b, x):
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t, df):
    """Two-sided p of Student's t with df degrees of freedom."""
    if t is None or df is None or df < 1:
        return None
    return betai(df / 2.0, 0.5, df / (df + t * t))


def clustered_mean(values, clusters):
    """Mean, CR1 standard error clustered by `clusters`, t, and the cluster count.
    With one value per cluster this equals the ordinary standard error s / sqrt(n)."""
    n = len(values)
    out = {"n": n, "clusters": len(set(clusters)), "mean": None, "se": None, "t": None, "p": None}
    if n == 0:
        return out
    m = sum(values) / n
    out["mean"] = m
    sums = defaultdict(float)
    for v, g in zip(values, clusters):
        sums[g] += v - m
    g_n = len(sums)
    if n < 2 or g_n < 2:
        return out
    var = g_n / (g_n - 1.0) * sum(s * s for s in sums.values()) / (n * n)
    se = math.sqrt(var)
    out["se"] = se
    if se > 0:
        out["t"] = m / se
        out["p"] = t_two_sided_p(out["t"], g_n - 1)
    return out


def aligned_bp(side, entry, exit_):
    return side * (exit_ / entry - 1.0) * 1e4


def cell_gate(cell):
    """The prereg's §7 conditions other than BH, each named."""
    s = cell["stats"]
    return {
        "events_ge_60": s["n"] >= MIN_EVENTS,
        "mean_net_positive_t_gt_2": (s["mean"] is not None and s["mean"] > 0 and s["t"] is not None and s["t"] > 2),
        "both_halves_positive": all(h["mean"] is not None and h["mean"] > 0 for h in cell["halves"].values()),
    }


# ---- I/O: NSE -------------------------------------------------------------------------

class NseClient(object):
    """A polite session for the report's CSV download: cookies from the home page and
    the report page, a Referer, >= REQUEST_GAP_S between requests, a fresh session on
    a failed attempt."""

    def __init__(self):
        import requests
        self._requests = requests
        self.session = None
        self.last = 0.0

    def _wait(self):
        gap = time.time() - self.last
        if gap < REQUEST_GAP_S:
            time.sleep(REQUEST_GAP_S - gap)
        self.last = time.time()

    def _warm(self):
        s = self._requests.Session()
        s.headers.update(HEADERS)
        for path in ("/", REPORT_PAGE):
            try:
                self._wait()
                s.get(NSE + path, timeout=20)  # sets the anti-bot cookies even on a 403
            except self._requests.RequestException:
                pass
        self.session = s

    def get_csv(self, path):
        """(status, raw_bytes, parsed_rows or None, attempts)."""
        status, raw = None, b""
        for attempt in range(1, ATTEMPTS + 1):
            if self.session is None or attempt > 1:
                self._warm()
            try:
                self._wait()
                resp = self.session.get(NSE + path, headers={"Referer": NSE + REPORT_PAGE}, timeout=30)
                status, raw = resp.status_code, resp.content
                rows = parse_deals_csv(raw.decode("utf-8-sig", "replace")) if status == 200 else None
                if rows is not None:
                    return status, raw, rows, attempt
            except self._requests.RequestException as exc:
                status, raw = "error: %s" % exc, b""
            time.sleep(5)
        return status, raw, None, ATTEMPTS

    def get_archive(self, url):
        self._wait()
        resp = self._requests.get(url, headers=HEADERS, timeout=30)
        return resp.status_code, resp.content


def _cache_path(name):
    return os.path.join(CACHE_DIR, name)


def fetch_deals(client, stage0):
    """Every month x kind as NSE's CSV, cached raw under backend/data/nse_deals/.
    Returns {kind: [rows]}; halts (raises) on a month that cannot be fetched."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    log, rows = [], {k: [] for k in KINDS}
    for kind, opt in KINDS.items():
        for frm, to in month_windows():
            name = "%s_%s_%s.csv" % (opt, frm, to)
            path = _cache_path(name)
            if os.path.exists(path):
                raw = open(path, "rb").read()
                parsed = parse_deals_csv(raw.decode("utf-8-sig", "replace"))
                entry = {"file": name, "from": frm, "to": to, "source": "cache", "bytes": len(raw)}
            else:
                status, raw, parsed, attempts = client.get_csv(DEALS_API % (opt, dmy(frm), dmy(to)))
                entry = {"file": name, "from": frm, "to": to, "source": "nse", "status": status,
                         "attempts": attempts, "bytes": len(raw), "fetched_at": datetime.now().isoformat()}
                if parsed is not None:
                    with open(path, "wb") as f:
                        f.write(raw)
            if parsed is None:
                entry["rows"] = None
                log.append(entry)
                stage0["source"] = {"files": log}
                raise Halt(1, "could not fetch %s %s..%s" % (kind, frm, to))
            entry["rows"] = len(parsed)
            entry["dates"] = len({r["date"] for r in parsed})
            log.append(entry)
            rows[kind].extend(parsed)
            print("  %-5s %s..%s  %5d rows  (%s)" % (kind, frm, to, len(parsed), entry["source"]), flush=True)
    stage0["source"] = {"endpoint": NSE + DEALS_API % ("{kind}", "{from}", "{to}"), "files": log,
                        "rows": {k: len(v) for k, v in rows.items()}}
    return rows


def _row_key(r):
    return (r["date"], r["symbol"], r["client"], r["side"], r["qty"], r["price"])


def completeness(client, rows, stage0):
    """Six fixed-seed deal dates re-queried one day at a time must equal the month files."""
    dates = sorted({r["date"] for k in KINDS for r in rows[k]})
    picks = sorted(random.Random(SEED).sample(dates, min(N_COMPLETENESS, len(dates))))
    checks, ok = [], True
    for d in picks:
        for kind, opt in KINDS.items():
            name = "%s_day_%s.csv" % (opt, d)
            path = _cache_path(name)
            if os.path.exists(path):
                day = parse_deals_csv(open(path, "rb").read().decode("utf-8-sig", "replace"))
            else:
                status, raw, day, _ = client.get_csv(DEALS_API % (opt, dmy(d), dmy(d)))
                if day is not None:
                    with open(path, "wb") as f:
                        f.write(raw)
            month = sorted(_row_key(r) for r in rows[kind] if r["date"] == d)
            got = sorted(_row_key(r) for r in (day or []))
            same = day is not None and got == month
            ok = ok and same
            checks.append({"date": d, "kind": kind, "month_rows": len(month),
                           "day_rows": None if day is None else len(got), "identical": same})
    stage0["completeness"] = {"seed": SEED, "dates": picks, "checks": checks, "all_identical": ok}
    if not ok:
        raise Halt(1, "a one-day query differs from its month file")


def fetch_symbol_changes(client, stage0):
    path = _cache_path("symbolchange.csv")
    if os.path.exists(path):
        raw, source = open(path, "rb").read(), "cache"
    else:
        status, raw = client.get_archive(SYMBOLCHANGE_URL)
        if status != 200:
            raise Halt(3, "symbolchange.csv: HTTP %s" % status)
        with open(path, "wb") as f:
            f.write(raw)
        source = "nse"
    changes = parse_symbol_changes(raw.decode("utf-8-sig", "replace"))
    stage0["symbol_changes"] = {"url": SYMBOLCHANGE_URL, "source": source, "symbols_with_changes": len(changes)}
    return changes


# ---- I/O: the candle cache, read-only ---------------------------------------------------

def open_candles_ro(path=None):
    path = path or CANDLE_DB
    if not os.path.exists(path):
        raise SystemExit("candle cache not found: %s (set L50_CANDLE_DB)" % path)
    conn = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_bar_times(conn):
    """{symbol: {date: set('HH:MM')}} for bars before BAR_BOUND_EXCLUSIVE. Selects symbol
    and time only: stage 0 reads no price."""
    bound = ist_midnight_epoch(BAR_BOUND_EXCLUSIVE)
    out = defaultdict(lambda: defaultdict(set))
    for sym, ts in conn.execute("SELECT symbol, ts FROM candles WHERE interval='5m' AND ts < ?", (bound,)):
        d, hm = ts_to_ist(ts)
        out[sym][d].add(hm)
    return out


def fetched_spans(conn):
    try:
        return [dict(r) for r in conn.execute(
            "SELECT symbol, from_date, to_date, fetched_at FROM fetched WHERE interval='5m'")]
    except sqlite3.Error:
        return []


def load_bar_prices(conn):
    """{symbol: {date: {"open": {hhmm: o}, "close": {hhmm: c}, "first": (hhmm, o), "last": (hhmm, c)}}}
    for bars before BAR_BOUND_EXCLUSIVE. The measurement pass only."""
    bound = ist_midnight_epoch(BAR_BOUND_EXCLUSIVE)
    keep = {AUCTION_BAR, ENTRY_BAR} | set(EXITS.values())
    out = defaultdict(dict)
    q = "SELECT symbol, ts, open, close FROM candles WHERE interval='5m' AND ts < ? ORDER BY symbol, ts"
    for sym, ts, o, c in conn.execute(q, (bound,)):
        d, hm = ts_to_ist(ts)
        day = out[sym].get(d)
        if day is None:
            day = out[sym][d] = {"open": {}, "close": {}, "first": (hm, o), "last": (hm, c)}
        day["last"] = (hm, c)
        if hm in keep:
            day["open"][hm], day["close"][hm] = o, c
    return out


# ---- stage 0 -----------------------------------------------------------------------------

class Halt(Exception):
    def __init__(self, step, why):
        Exception.__init__(self, "stage 0 step %s: %s" % (step, why))
        self.step, self.why = step, why


def build_events(rows, changes, bar_times, members_rows, stage0, spans=()):
    """Stage 0 steps 2-5 on parsed rows and bar TIMES (never a price). `spans` are the
    cache's fetched spans, for the #108 boundary flag. Returns (events, sessions, family)."""
    # step 2: boundaries
    all_dates = [r["date"] for k in KINDS for r in rows[k]]
    outside = [d for d in all_dates if d < DEAL_FIRST or d > DEAL_LAST]
    last_bar = max(d for days in bar_times.values() for d in days)
    stage0["boundaries"] = {"deal_dates": [min(all_dates), max(all_dates)] if all_dates else None,
                            "deal_rows_outside_window": len(outside), "last_bar_date_loaded": last_bar,
                            "bar_bound_exclusive": BAR_BOUND_EXCLUSIVE}
    if outside:
        raise Halt(2, "%d deal rows dated outside %s..%s" % (len(outside), DEAL_FIRST, DEAL_LAST))
    if last_bar > SAMPLE_END:
        raise Halt(2, "a bar dated %s was loaded (sample ends %s)" % (last_bar, SAMPLE_END))

    regular = regular_sessions(bar_times)
    sessions = [d for d in regular if SAMPLE_START <= d <= SAMPLE_END]
    first_half, second_half = splits.halves(sessions)
    half_of = dict([(d, "first") for d in first_half] + [(d, "second") for d in second_half])
    member_cache = {}

    def members(d):
        if d not in member_cache:
            member_cache[d] = membership_asof(members_rows, d)
        return member_cache[d]

    bounds = adjustment_boundaries(list(spans))

    # steps 3-5
    events, lost, not_member, no_session, d_not_regular = [], defaultdict(int), 0, 0, 0
    for kind in KINDS:
        for (sym, d, _), a in aggregate(rows[kind], kind, changes).items():
            entry = next_session(d, regular)
            if entry is None or not (SAMPLE_START <= entry <= SAMPLE_END):
                no_session += 1
                continue
            if sym not in members(entry):
                not_member += 1
                continue
            if sym not in bar_times:
                lost["%s:%s" % (kind, sym)] += 1
                continue
            side = bulk_side(a["B"], a["S"]) if kind == "BULK" else 0
            hhmms = bar_times[sym].get(entry)
            ev = {"symbol": sym, "deal_symbols": sorted(a["deal_symbols"]), "deal_date": d, "entry": entry,
                  "kind": kind, "B": a["B"], "S": a["S"], "rows": a["rows"], "side": side,
                  "class": bulk_class(side) if kind == "BULK" else "BLOCK",
                  "info_sides": {str(t): (bulk_side(a["B"], a["S"], t) if kind == "BULK" else 0)
                                 for t in INFO_THRESHOLDS},
                  "bars": {h: bars_present(hhmms, h) for h in EXITS},
                  "half": half_of.get(entry),
                  "deal_date_is_regular_session": d in regular,
                  "fetch_boundary_between": boundary_between(bounds.get(sym), d, entry),
                  "clients": a["clients"]}
            d_not_regular += 0 if ev["deal_date_is_regular_session"] else 1
            events.append(ev)
    events.sort(key=lambda e: (e["entry"], e["symbol"], e["kind"]))

    stage0["symbols"] = {"stock_days_outside_sample": no_session, "stock_days_not_nifty100_on_entry": not_member,
                         "nifty100_stock_days_lost_no_cached_bars": dict(lost),
                         "nifty100_stock_days": len(events),
                         "deal_dates_not_a_regular_cached_session": d_not_regular}
    bulk = [e for e in events if e["kind"] == "BULK"]
    block = [e for e in events if e["kind"] == "BLOCK"]
    stage0["classes"] = {
        "BULK_BUY": sum(e["side"] == 1 for e in bulk), "BULK_SELL": sum(e["side"] == -1 for e in bulk),
        "MIXED": sum(e["side"] == 0 for e in bulk), "BLOCK": len(block),
        "BLOCK_with_buy_ne_sell": sum(e["B"] != e["S"] for e in block),
        "info_other_thresholds": {str(t): {"BULK_BUY": sum(e["info_sides"][str(t)] == 1 for e in bulk),
                                           "BULK_SELL": sum(e["info_sides"][str(t)] == -1 for e in bulk),
                                           "MIXED": sum(e["info_sides"][str(t)] == 0 for e in bulk)}
                                  for t in INFO_THRESHOLDS},
        "dominance_of_record": "1/3"}

    counts = OrderedDict()
    for c in CLASSES:
        for h in EXITS:
            members_c = [e for e in events if c in classes_of(e) and e["bars"][h]]
            counts["%s:%s" % (c, h)] = {
                "events": len(members_c), "sessions": len({e["entry"] for e in members_c}),
                "first_half": sum(e["half"] == "first" for e in members_c),
                "second_half": sum(e["half"] == "second" for e in members_c)}
    family = [k for k, v in counts.items() if v["events"] >= MIN_EVENTS]
    no_bars = {c: sum(1 for e in events if c in classes_of(e) and not any(e["bars"].values())) for c in CLASSES}
    stage0["bars"] = {"cells": counts, "events_without_any_bars": no_bars}
    stage0["family"] = {"cells": family, "size": len(family), "bh_q": BH_Q, "min_events": MIN_EVENTS}
    stage0["sessions"] = {"regular_in_sample": len(sessions), "first": sessions[0] if sessions else None,
                          "last": sessions[-1] if sessions else None, "first_half": len(first_half),
                          "second_half": len(second_half),
                          "halves_boundary": second_half[0] if second_half else None,
                          # NSE's deal dates are an independent trading calendar for the cache's
                          "deal_dates_in_sample_not_regular": sorted(
                              {d for d in all_dates if SAMPLE_START <= d <= DEAL_LAST} - set(regular)),
                          "regular_sessions_with_no_bulk_row": sorted(
                              set(d for d in sessions if d <= DEAL_LAST) - {r["date"] for r in rows["BULK"]})}
    return events, sessions, family


def write_events_csv(events, path=None):
    path = path or EVENTS_CSV
    cols = ["deal_date", "entry_session", "symbol", "deal_symbols", "kind", "buy_qty", "sell_qty", "class",
            "side", "rows", "bars_15m", "bars_30m", "bars_60m", "half", "fetch_boundary_between", "clients"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for e in events:
            w.writerow([e["deal_date"], e["entry"], e["symbol"], ";".join(e["deal_symbols"]), e["kind"], e["B"],
                        e["S"], e["class"], e["side"], e["rows"], int(e["bars"]["15m"]), int(e["bars"]["30m"]),
                        int(e["bars"]["60m"]), e["half"] or "", int(e["fetch_boundary_between"]),
                        " | ".join(e["clients"])])


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=False, default=str)
        f.write("\n")


def run_stage0(conn, client=None):
    stage0 = OrderedDict([("started", datetime.now().isoformat()),
                          ("prereg", "docs/research/prereg-bulk-block-deals.md (66c1ed3)"),
                          ("candle_db", CANDLE_DB), ("reads_price", False)])
    try:
        client = client or NseClient()
        print("stage 0 step 1: NSE bulk and block deals, %s..%s" % (DEAL_FIRST, DEAL_LAST), flush=True)
        rows = fetch_deals(client, stage0)
        completeness(client, rows, stage0)
        changes = fetch_symbol_changes(client, stage0)
        print("stage 0 steps 2-5: bar times only (no price)", flush=True)
        bar_times = load_bar_times(conn)
        spans = fetched_spans(conn)
        runs = sorted({datetime.utcfromtimestamp(s["fetched_at"] + IST_OFFSET).date().isoformat()
                       for s in spans if s.get("fetched_at") is not None})
        stage0["adjustment"] = {"fetch_run_dates": runs, "spans": len(spans)}
        events, sessions, family = build_events(rows, changes, bar_times, load_membership_rows(), stage0, spans)
        stage0["adjustment"]["events_with_boundary_between"] = sum(e["fetch_boundary_between"] for e in events)
        write_events_csv(events)
        if not family:
            raise Halt(6, "BULK_ALL has fewer than %d events at every horizon: L50 is VOID" % MIN_EVENTS)
        stage0["status"] = "STAGE0_DONE"
    except Halt as h:
        stage0["status"] = "VOID" if h.step == 6 else "HALTED"
        stage0["halt"] = {"step": h.step, "why": h.why}
        print(str(h), flush=True)
    stage0["finished"] = datetime.now().isoformat()
    _write(STAGE0_OUT, stage0)
    return stage0


# ---- the one measurement pass --------------------------------------------------------------

def event_returns(ev, prices, horizon):
    """Aligned gross bp for one event-horizon, or None if a bar is missing."""
    day = prices.get(ev["symbol"], {}).get(ev["entry"])
    if not day:
        return None
    o, c = day["open"].get(ENTRY_BAR), day["close"].get(EXITS[horizon])
    if o is None or c is None or o <= 0:
        return None
    return aligned_bp(ev["side"], o, c)


def raw_window_bp(day, horizon):
    if not day:
        return None
    o, c = day["open"].get(ENTRY_BAR), day["close"].get(EXITS[horizon])
    return None if o is None or c is None or o <= 0 else (c / o - 1.0) * 1e4


def market_window_bp(prices, members, d, horizon):
    vals = [raw_window_bp(prices.get(s, {}).get(d), horizon) for s in members]
    vals = [v for v in vals if v is not None]
    return st.mean(vals) if vals else None


def summarise_cell(items):
    """items: [(net_bp, entry_session, half)]."""
    vals = [x[0] for x in items]
    stats = clustered_mean(vals, [x[1] for x in items])
    halves = OrderedDict()
    for h in ("first", "second"):
        sub = [x for x in items if x[2] == h]
        halves[h] = clustered_mean([x[0] for x in sub], [x[1] for x in sub])
    return {"stats": stats, "halves": halves,
            "share_positive": (sum(v > 0 for v in vals) / len(vals)) if vals else None,
            "power_2se_bp": (2 * stats["se"]) if stats["se"] else None}


def run_measurement(conn, stage0):
    """Stage 0's events and family re-derived from the cached raw files (never refetched),
    checked equal to the committed record, then ONE pass over prices."""
    if stage0.get("status") != "STAGE0_DONE":
        raise SystemExit("stage 0 is not STAGE0_DONE; the measurement pass does not run")
    if os.path.exists(RESULT_OUT):
        raise SystemExit("%s exists: one run only (prereg §9)" % RESULT_OUT)

    class _CacheOnly(object):
        def get_csv(self, path):
            raise SystemExit("measurement pass: a raw deal file is missing from the cache (%s)" % path)

        def get_archive(self, url):
            raise SystemExit("measurement pass: symbolchange.csv missing from the cache")

    check = OrderedDict()
    rows = fetch_deals(_CacheOnly(), check)
    changes = fetch_symbol_changes(_CacheOnly(), check)
    bar_times = load_bar_times(conn)
    events, sessions, family = build_events(rows, changes, bar_times, load_membership_rows(), check,
                                            fetched_spans(conn))
    if family != stage0["family"]["cells"] or check["bars"]["cells"] != stage0["bars"]["cells"]:
        raise SystemExit("re-derived events differ from the committed stage 0; stopping before any price")

    print("measurement pass: loading prices (bars before %s)" % BAR_BOUND_EXCLUSIVE, flush=True)
    prices = load_bar_prices(conn)
    regular = regular_sessions(bar_times)
    members_rows = load_membership_rows()
    in_cache = set(prices)
    mkt_cache = {}

    def market(d, h):
        if (d, h) not in mkt_cache:
            mkt_cache[(d, h)] = market_window_bp(prices, membership_asof(members_rows, d) & in_cache, d, h)
        return mkt_cache[(d, h)]

    cells, descr = OrderedDict(), OrderedDict()
    for c in CLASSES:
        evs = [e for e in events if c in classes_of(e)]
        for h in EXITS:
            items, madj = [], []
            for e in evs:
                g = event_returns(e, prices, h)
                if g is None:
                    continue
                items.append((g - COST_BP, e["entry"], e["half"]))
                m = market(e["entry"], h)
                if m is not None:
                    r_raw = raw_window_bp(prices[e["symbol"]][e["entry"]], h)
                    madj.append((e["side"] * (r_raw - m) - COST_BP, e["entry"], e["half"]))
            key = "%s:%s" % (c, h)
            cells[key] = summarise_cell(items)
            cells[key]["gross_mean_bp"] = (cells[key]["stats"]["mean"] + COST_BP) if items else None
            cells[key]["in_family"] = key in family
            descr[key] = {"market_adjusted_net": clustered_mean([x[0] for x in madj], [x[1] for x in madj])}
        # before the entry: the deal day, the overnight gap, the opening five minutes (aligned, gross)
        pre = {"deal_day_open_to_close": [], "gap_prev_close_to_0915_open": [], "open_0915_to_0920": []}
        for e in evs:
            p = prices.get(e["symbol"], {})
            dd = p.get(e["deal_date"]) if e["deal_date_is_regular_session"] else None
            if dd and dd["first"][1] and dd["first"][1] > 0:
                pre["deal_day_open_to_close"].append((aligned_bp(e["side"], dd["first"][1], dd["last"][1]), e["entry"]))
            prev = prev_session(e["entry"], regular)
            pd, ed = p.get(prev), p.get(e["entry"])
            if pd and ed and ed["open"].get(AUCTION_BAR) and not e["fetch_boundary_between"]:
                pre["gap_prev_close_to_0915_open"].append(
                    (aligned_bp(e["side"], pd["last"][1], ed["open"][AUCTION_BAR]), e["entry"]))
            if ed and ed["open"].get(AUCTION_BAR) and ed["open"].get(ENTRY_BAR):
                pre["open_0915_to_0920"].append(
                    (aligned_bp(e["side"], ed["open"][AUCTION_BAR], ed["open"][ENTRY_BAR]), e["entry"]))
        descr[c] = {k: clustered_mean([x[0] for x in v], [x[1] for x in v]) for k, v in pre.items()}

    # volatility read: |r| against the same stock's non-event sessions
    event_entries = defaultdict(set)
    for e in events:
        event_entries[e["symbol"]].add(e["entry"])
    base = {}
    for sym, days in prices.items():
        for h in EXITS:
            vals = [abs(v) for d in sessions if d not in event_entries[sym]
                    for v in [raw_window_bp(days.get(d), h)] if v is not None]
            base[(sym, h)] = st.mean(vals) if vals else None
    vol = OrderedDict()
    for label, pick in (("BULK_ALL", lambda e: e["kind"] == "BULK" and e["side"] != 0),
                        ("MIXED", lambda e: e["kind"] == "BULK" and e["side"] == 0),
                        ("BLOCK", lambda e: e["kind"] == "BLOCK")):
        for h in EXITS:
            xs = []
            for e in events:
                if not pick(e):
                    continue
                r = raw_window_bp(prices.get(e["symbol"], {}).get(e["entry"]), h)
                b = base.get((e["symbol"], h))
                if r is not None and b is not None:
                    xs.append((abs(r), b, e["entry"]))
            vol["%s:%s" % (label, h)] = {
                "n": len(xs), "mean_abs_bp": st.mean([x[0] for x in xs]) if xs else None,
                "baseline_abs_bp": st.mean([x[1] for x in xs]) if xs else None,
                "excess": clustered_mean([x[0] - x[1] for x in xs], [x[2] for x in xs])}

    pvals = [cells[k]["stats"]["p"] if cells[k]["stats"]["p"] is not None else 1.0 for k in family]
    survivors = {family[i] for i in benjamini_hochberg(pvals, q=BH_Q)} if family else set()
    gate = OrderedDict()
    for k in cells:
        g = cell_gate(cells[k])
        g["in_family"] = k in family
        g["survives_bh"] = k in survivors
        g["passes"] = all(g.values())
        gate[k] = g
    result = OrderedDict([("stage0_status", stage0["status"]), ("family", family), ("cost_bp", COST_BP),
                          ("cells", cells), ("gate", gate), ("any_pass", any(g["passes"] for g in gate.values())),
                          ("descriptive", descr), ("volatility", vol),
                          ("finished", datetime.now().isoformat())])
    _write(RESULT_OUT, result)
    for k, cl in cells.items():
        s = cl["stats"]
        print("%-14s n %4s  net %8s bp  t %6s  halves %s / %s  %s%s" % (
            k, s["n"], _f(s["mean"]), _f(s["t"]), _f(cl["halves"]["first"]["mean"]),
            _f(cl["halves"]["second"]["mean"]), "family" if k in family else "outside",
            "  PASS" if gate[k]["passes"] else ""))
    print("wrote", RESULT_OUT)
    return result


def _f(x):
    return "—" if x is None else "%.2f" % x


def _engine_hours(now=None):
    """True during 08:30-15:45 IST on a weekday, when the Mac runs the trading engine."""
    now = now or datetime.utcnow() + timedelta(seconds=IST_OFFSET)
    return now.weekday() < 5 and (8, 30) <= (now.hour, now.minute) < (15, 45)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--stage0-only", action="store_true", help="fetch deals, count events, read no price")
    g.add_argument("--measure", action="store_true", help="the one measurement pass, after review")
    ap.add_argument("--allow-engine-hours", action="store_true",
                    help="run inside 08:30-15:45 IST on a weekday anyway (recorded)")
    args = ap.parse_args(argv)
    if _engine_hours() and not args.allow_engine_hours:
        raise SystemExit("08:30-15:45 IST on a weekday: the engine is running; not starting")
    conn = open_candles_ro()
    if args.stage0_only:
        s0 = run_stage0(conn)
        print("stage 0: %s  family %s" % (s0["status"], s0.get("family", {}).get("cells")))
        print("wrote", STAGE0_OUT, "and", EVENTS_CSV)
        return
    with open(STAGE0_OUT) as f:
        run_measurement(conn, json.load(f))


if __name__ == "__main__":
    main()
