"""
Official NSE feeds: corporate announcements (order wins, acquisitions,
buybacks, resignations, pledges...) and the event calendar (results / board
meetings). These are the primary catalyst source — companies must file here
before or as news breaks.

These are the JSON endpoints behind nseindia.com's own pages, not a
documented public API: they need browser-like headers and can change or
rate-limit without notice. Responses are cached (announcements 10 min,
calendar 6 h) and any failure returns the last good data or nothing.
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from sentiment_lexicon import score_text

logger = logging.getLogger("trading_bot")
IST = ZoneInfo("Asia/Kolkata")
BASE = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Filing categories that carry no price information.
ROUTINE = (
    "shareholders meeting", "analysts/institutional", "trading window", "newspaper", "certificate",
    "loss of share", "duplicate share", "investor presentation", "esop", "esos", "transcript",
    "audio", "recording", "compliance", "74(5)", "record date",
)
# Category tilt, checked in order (first match wins).
TILTS = (
    ("default", -1.0), ("fraud", -1.0), ("insolvency", -1.0), ("pledge", -0.5), ("resignation", -0.4),
    ("litigation", -0.3), ("buy back", 0.8), ("buyback", 0.8), ("bagging", 0.8), ("receiving of order", 0.8),
    ("order", 0.6), ("contract", 0.5), ("bonus", 0.6), ("acquisition", 0.4), ("dividend", 0.3),
)

_session = {"s": None, "created": 0.0}
_cache = {}
_lock = threading.Lock()


def _fetch(path, referer, ttl):
    with _lock:
        hit = _cache.get(path)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
        err = "unknown"
        for attempt in range(2):
            if _session["s"] is None or attempt == 1 or time.time() - _session["created"] > 1800:
                s = requests.Session()
                s.headers.update(HEADERS)
                try:
                    s.get(BASE + "/", timeout=15)  # sets anti-bot cookies even when it returns 403
                except requests.RequestException:
                    pass
                _session.update(s=s, created=time.time())
            try:
                resp = _session["s"].get(BASE + path, headers={"Referer": BASE + referer}, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    _cache[path] = (time.time(), data)
                    return data
                err = f"HTTP {resp.status_code}"
            except (requests.RequestException, ValueError) as exc:
                err = str(exc)
        logger.warning(f"NSE {path} unavailable ({err})")
        return hit[1] if hit else None


def announcements_by_symbol():
    """{SYMBOL: [news item, ...]} for price-relevant filings from the last ~2 days."""
    today = datetime.now(IST).date()
    frm = (today - timedelta(days=2)).strftime("%d-%m-%Y")
    path = f"/api/corporate-announcements?index=equities&from_date={frm}&to_date={today.strftime('%d-%m-%Y')}"
    data = _fetch(path, "/companies-listing/corporate-filings-announcements", 600)
    if not data:
        data = _fetch("/api/corporate-announcements?index=equities", "/companies-listing/corporate-filings-announcements", 600) or []

    out = {}
    for a in data if isinstance(data, list) else []:
        symbol = (a.get("symbol") or "").upper()
        desc = a.get("desc") or ""
        text = a.get("attchmntText") or ""
        d = desc.lower()
        if not symbol or any(k in d for k in ROUTINE):
            continue
        tilt = next((w for k, w in TILTS if k in d), 0.0)
        score = max(-1.0, min(1.0, tilt + 0.6 * score_text(f"{desc}. {text}")))
        if abs(score) < 0.1:
            continue
        try:
            published = datetime.strptime(a.get("an_dt", ""), "%d-%b-%Y %H:%M:%S").replace(tzinfo=IST)
        except ValueError:
            published = None
        out.setdefault(symbol, []).append({
            "title": f"{desc}: {text[:180]}".strip(": "),
            "summary": "",
            "published": published,
            "source": "NSE filing",
            "publisher": "NSE",
            "url": a.get("attchmntFile"),
            "score": round(score, 2),
        })
    return out


def corporate_actions_on(date_iso):
    """{SYMBOL: subject} for dividends, bonuses, splits and rights whose ex-date is date_iso (YYYY-MM-DD).
    On an ex-date the price drops mechanically, which charts read as a gap down."""
    day = datetime.strptime(date_iso, "%Y-%m-%d")
    ds = day.strftime("%d-%m-%Y")
    data = _fetch(f"/api/corporates-corporateActions?index=equities&from_date={ds}&to_date={ds}",
                  "/companies-listing/corporate-filings-actions", 21600) or []
    out = {}
    for a in data if isinstance(data, list) else []:
        try:
            ex = datetime.strptime(a.get("exDate", ""), "%d-%b-%Y").date()
        except ValueError:
            continue
        if ex == day.date() and a.get("symbol"):
            out[a["symbol"].upper()] = a.get("subject") or "corporate action"
    return out


def large_deals_today():
    """{SYMBOL: {"bulk": [...], "block": [...]}} for today's real NSE bulk
    (>0.5% of shares) and block (single large trade) deal disclosures —
    named market participants, published end-of-day, real and free
    (api/snapshot-capital-market-largedeal, verified live). Deliberately
    informational only, never scored: real academic evidence (an IIM
    Calcutta working paper on price discovery from bulk trades; a
    Managerial Finance/Emerald study on Indian bulk deals) found the
    apparent "predictive" pattern in these disclosures is substantially
    explained by pre-announcement information leakage and front-running,
    not a clean edge a system reading the after-the-fact disclosure can
    capture. Shown as context — informed large flow happened here today —
    not a signal to act on."""
    data = _fetch("/api/snapshot-capital-market-largedeal",
                  "/report-detail/display-bulk-and-block-deals", 3600) or {}
    out = {}
    for kind, key in (("bulk", "BULK_DEALS_DATA"), ("block", "BLOCK_DEALS_DATA")):
        for d in data.get(key) or []:
            sym = (d.get("symbol") or "").upper()
            if not sym or not d.get("buySell"):
                continue
            out.setdefault(sym, {"bulk": [], "block": []})[kind].append({
                "side": d["buySell"], "qty": d.get("qty"), "price": d.get("watp"),
                "client": d.get("clientName"),
            })
    return out


def fii_dii_flows():
    """Most recent real daily FII/DII net flow (₹ crore), from NSE's own
    daily report (api/fiidiiTradeReact, verified live). A real, documented
    relationship with NIFTY returns exists (an SJCC Management Research
    Review study on FII flows and NSE returns found it strongest when the
    market is falling) but the exact meaningful threshold isn't crisply
    established in that literature — used as a modest, honestly-thresholded
    market-context input (see scanner.py's market_context()), same
    discipline as every other signal here: logged through the same scoring
    database.factor_ic() checks, never assumed to help on arrival."""
    data = _fetch("/api/fiidiiTradeReact", "/reports/fii-dii", 3600) or []
    fii = next((r for r in data if r.get("category") == "FII/FPI"), None)
    dii = next((r for r in data if r.get("category") == "DII"), None)
    if not fii:
        return None
    try:
        return {
            "date": fii.get("date"),
            "fii_net_cr": float(fii["netValue"]),
            "dii_net_cr": float(dii["netValue"]) if dii else None,
        }
    except (KeyError, ValueError, TypeError):
        return None


def market_breadth():
    """Real, whole-exchange market breadth — Murphy, Technical Analysis of
    the Financial Markets ch 10 (advance-decline line, Arms Index/TRIN) —
    from NSE's own live-analysis feed (api/live-analysis-advance +
    api/live-analysis-decline, verified live: 3,687 stocks total on NSE,
    not just this scanner's NIFTY 100 universe, which is why this couldn't
    be self-computed from scan_rows the way scanner.py's own narrower
    "breadth" reading is). Each side's response also carries each stock's
    totalTradedVolume, which is what TRIN needs beyond a plain
    advance/decline count.

    TRIN (Arms Index) = (advances/declines) / (up_volume/down_volume).
    Below 1.0: volume favors advancing stocks (bullish tape). Above 1.0:
    volume favors declining stocks even if price breadth looks neutral —
    Murphy's example of volume confirming or contradicting price breadth.
    Returned here as a raw, real number; scanner.py doesn't score it yet
    (see README) — same "don't assume it helps on arrival" discipline as
    fii_dii_flows(), pending a real database.factor_ic() check once enough
    days of history exist to test it."""
    adv = _fetch("/api/live-analysis-advance", "/market-data/live-market-indices", 300)
    dec = _fetch("/api/live-analysis-decline", "/market-data/live-market-indices", 300)
    if not adv or not dec:
        return None
    try:
        a_count = adv["advance"]["count"]
        d_count = dec["decline"]["count"]
        advances, declines = a_count["Advances"], d_count["Declines"]
        up_volume = sum(r.get("totalTradedVolume") or 0 for r in adv["advance"]["data"])
        down_volume = sum(r.get("totalTradedVolume") or 0 for r in dec["decline"]["data"])
        trin = (advances / declines) / (up_volume / down_volume) if declines and down_volume else None
        return {
            "timestamp": adv.get("timestamp"), "advances": advances, "declines": declines,
            "unchanged": a_count.get("Unchange"), "total": a_count.get("Total"),
            "up_volume": round(up_volume, 1), "down_volume": round(down_volume, 1),
            "trin": round(trin, 3) if trin is not None else None,
        }
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        return None


def _next_trading_day(d):
    n = d + timedelta(days=1)
    while n.weekday() >= 5:
        n += timedelta(days=1)
    return n


def results_calendar():
    """{SYMBOL: {"date", "purpose"}} for results due today or on the next trading day."""
    data = _fetch("/api/event-calendar", "/companies-listing/corporate-filings-event-calendar", 21600) or []
    today = datetime.now(IST).date()
    horizon = _next_trading_day(today)
    out = {}
    for e in data if isinstance(data, list) else []:
        text = f"{e.get('purpose', '')} {e.get('bm_desc', '')}".lower()
        if "result" not in text:
            continue
        try:
            d = datetime.strptime(e.get("date", ""), "%d-%b-%Y").date()
        except ValueError:
            continue
        if today <= d <= horizon and e.get("symbol"):
            out[e["symbol"].upper()] = {"date": e["date"], "purpose": e.get("purpose") or "Financial Results"}
    return out


# ---- F&O ban list (Market Wide Position Limit) -----------------------------
# Once market-wide open interest in a stock's derivatives crosses 95% of its
# limit, the stock enters the "ban period". NSE publishes the list for each
# trade date as a small CSV. Index derivatives are never in it. Two readers:
# the scanner's ban guard (scanner.guard_check) and the F&O entry path
# (fno_risk.mwpl_block_reason, called from trading_engine._try_enter_fno).

ARCHIVES = "https://nsearchives.nseindia.com"
FNO_BAN_URL = ARCHIVES + "/content/fo/fo_secban.csv"
PRICE_BANDS_URL = ARCHIVES + "/content/equities/sec_list.csv"
_ban_cache = {"at": 0.0, "value": None}
_bands_cache = {"at": 0.0, "value": None}


def parse_fno_ban(text):
    """NSE's fo_secban.csv -> {"trade_date": "YYYY-MM-DD", "symbols": set}.
    The first line is 'Securities in Ban For Trade Date 25-SEP-2026:',
    then one 'n,SYMBOL' row per banned stock (none on a clear day).
    Returns None if the header is not recognisable, so a changed format is
    treated as unknown status rather than as an empty ban list."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines or "Trade Date" not in lines[0]:
        return None
    try:
        raw = lines[0].split("Trade Date", 1)[1].strip().rstrip(":").strip()
        trade_date = datetime.strptime(raw.title(), "%d-%b-%Y").date().isoformat()
    except ValueError:
        return None
    symbols = set()
    for ln in lines[1:]:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) >= 2 and parts[1]:
            symbols.add(parts[1].upper())
    return {"trade_date": trade_date, "symbols": symbols}


def _archive(url, parse, cache, ttl, what):
    """A small static file from NSE's archives, parsed and cached. None when
    it cannot be fetched or parsed: callers must treat that as UNKNOWN."""
    if cache["value"] is not None and time.time() - cache["at"] < ttl:
        return cache["value"]
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        parsed = parse(resp.text) if resp.status_code == 200 else None
    except requests.RequestException as exc:
        logger.warning(f"NSE {what} unavailable ({exc})")
        parsed = None
    if parsed is not None:
        cache.update(at=time.time(), value=parsed)
    return parsed


def fno_ban_list(ttl=1800):
    """The F&O ban list for the current trade date, cached for `ttl` seconds."""
    return _archive(FNO_BAN_URL, parse_fno_ban, _ban_cache, ttl, "F&O ban list")


# ---- price bands ------------------------------------------------------------
# NSE's list of every security with its price band for the day: 2, 5, 10 or
# 20 (per cent either way), or "No Band" for stocks with derivatives. The
# same file carries the series (EQ, or BE/BZ for trade-for-trade) and any
# graded-surveillance remark.

def parse_price_bands(text):
    """sec_list.csv -> {symbol: {"series", "band" (per cent, or None for no
    band), "remarks"}}. None if the header is not the one expected."""
    lines = (text or "").lstrip("\ufeff").splitlines()
    if not lines:
        return None
    header = [h.strip().lower() for h in lines[0].split(",")]
    if header[:2] != ["symbol", "series"] or "band" not in header:
        return None
    import csv
    out = {}
    for r in csv.DictReader(lines):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        sym, band = r.get("symbol", "").upper(), r.get("band", "")
        if not sym:
            continue
        try:
            pct = None if band.lower() == "no band" else float(band)
        except ValueError:
            continue
        remarks = r.get("remarks", "")
        row = {"series": r.get("series", "").upper(), "band": pct, "remarks": "" if remarks == "-" else remarks}
        # a symbol can be listed in more than one series; the EQ row is the one that trades intraday
        if sym not in out or row["series"] == "EQ":
            out[sym] = row
    return out or None


def price_bands(ttl=6 * 3600):
    """Today's price band, series and surveillance remark for every security."""
    return _archive(PRICE_BANDS_URL, parse_price_bands, _bands_cache, ttl, "price-band list")


# ---- the last completed session, from NSE's own daily files -------------------
# yfinance's daily bars can end a session early for hours after the close: at
# 01:00 on 29 Sep 2026 they still ended on the 25th, so a read made before the
# open ranked on data one session old. NSE publishes each session's prices in
# the evening: the equity bhavcopy and the closing values of every index.

BHAVCOPY_URL = ARCHIVES + "/content/cm/BhavCopy_NSE_CM_0_0_0_{tag}_F_0000.csv.zip"
INDEX_CLOSE_URL = ARCHIVES + "/content/indices/ind_close_all_{tag}.csv"
INDEX_NAMES = {
    "^NSEI": "Nifty 50", "^INDIAVIX": "India VIX", "NIFTY_FIN_SERVICE.NS": "Nifty Financial Services",
    "^CNXAUTO": "Nifty Auto", "^CNXPHARMA": "Nifty Pharma", "^CNXFMCG": "Nifty FMCG", "^CNXMETAL": "Nifty Metal",
    "^CNXENERGY": "Nifty Energy", "^CNXIT": "Nifty IT", "^CNXREALTY": "Nifty Realty",
}
_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_last_session_cache = {}


def previous_trading_day(day):
    """The last weekday before `day` that was not an NSE holiday."""
    import holidays
    d = day - timedelta(days=1)
    while d.weekday() >= 5 or holidays.is_holiday(d):
        d -= timedelta(days=1)
    return d


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_bhavcopy_bars(zip_bytes, date_iso):
    """{symbol: daily bar} for the EQ series of one equity bhavcopy."""
    import csv
    import io
    import zipfile
    out = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z, z.open(z.namelist()[0]) as fh:
        for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="ignore")):
            if (r.get("SctySrs") or "").strip() != "EQ" or (r.get("TradDt") or "").strip() != date_iso:
                continue
            o, h, low, c = (_num(r.get(k)) for k in ("OpnPric", "HghPric", "LwPric", "ClsPric"))
            if not (o and h and low and c):
                continue
            out[r["TckrSymb"].strip()] = {"time": f"{date_iso}T00:00:00+05:30", "open": o, "high": h, "low": low,
                                          "close": c, "volume": int(_num(r.get("TtlTradgVol")) or 0)}
    return out


def parse_index_bars(text, date_iso):
    """{yfinance ticker: daily bar} for the indices the scanner reads."""
    import csv
    by_name = {}
    for r in csv.DictReader((text or "").lstrip("\ufeff").splitlines()):
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        try:
            when = datetime.strptime(r.get("Index Date", ""), "%d-%m-%Y").date().isoformat()
        except ValueError:
            continue
        if when == date_iso:
            by_name[r.get("Index Name", "").lower()] = r
    out = {}
    for ticker, name in INDEX_NAMES.items():
        r = by_name.get(name.lower())
        if not r:
            continue
        o, h, low, c = (_num(r.get(k)) for k in ("Open Index Value", "High Index Value", "Low Index Value",
                                                  "Closing Index Value"))
        if o and h and low and c:
            out[ticker] = {"time": f"{date_iso}T00:00:00+05:30", "open": o, "high": h, "low": low, "close": c,
                           "volume": int(_num(r.get("Volume")) or 0)}
    return out


def _cached_file(path, url, binary):
    """The file at `path`, downloaded once from NSE's archives. None if it
    is not published yet or cannot be fetched."""
    if os.path.exists(path) and os.path.getsize(path) > 500:
        with open(path, "rb" if binary else "r") as fh:
            return fh.read()
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as exc:
        logger.warning(f"NSE daily file unavailable ({exc})")
        return None
    if resp.status_code != 200 or len(resp.content) < 500:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(resp.content)
    os.replace(tmp, path)
    return resp.content if binary else resp.text


def last_session(today, data_dir=None):
    """The last completed session's daily bars from NSE's own files:
    {"date", "stocks": {symbol: bar}, "indices": {ticker: bar}}. Either part
    may be empty. `today` is a date; the session is the trading day before it."""
    data_dir = data_dir or _DATA
    day = previous_trading_day(today)
    iso = day.isoformat()
    hit = _last_session_cache.get(iso)
    if hit and hit["stocks"] and hit["indices"]:
        return hit
    stocks, indices = {}, {}
    tag = day.strftime("%Y%m%d")
    path = next((p for p in (os.path.join(data_dir, d, f"{tag}.zip")
                             for d in ("bhav_live", "bhav_daily_2026_heldout", "bhav_daily")) if os.path.exists(p)),
                os.path.join(data_dir, "bhav_live", f"{tag}.zip"))
    try:
        raw = _cached_file(path, BHAVCOPY_URL.format(tag=tag), binary=True)
        stocks = parse_bhavcopy_bars(raw, iso) if raw else {}
    except Exception:
        logger.exception("Could not read the equity bhavcopy for %s", iso)
    try:
        tag = day.strftime("%d%m%Y")
        text = _cached_file(os.path.join(data_dir, "nse_indices", f"ind_close_all_{tag}.csv"),
                            INDEX_CLOSE_URL.format(tag=tag), binary=False)
        indices = parse_index_bars(text, iso) if text else {}
    except Exception:
        logger.exception("Could not read the index closing file for %s", iso)
    out = {"date": iso, "stocks": stocks, "indices": indices}
    _last_session_cache[iso] = out
    return out
