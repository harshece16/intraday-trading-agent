"""
Deep intraday history from Kite, cached on disk so a backtest reads it once.

yfinance stops at about 60 days of 5-minute candles, which caps a NIFTY 100
backtest at 21-42 trades — far short of the 101 needed to detect a +0.5R edge
at the measured 2.51R spread, let alone the 631 for +0.2R (issue #46). Kite's
historical API paginates back years, so this fetches once, stores every candle
in SQLite, and lets run_backtest() read from the cache.

It also removes a quieter problem: live trading reads Kite and backtests read
yfinance, so some part of any divergence between them is the feed rather than
the strategy, and nothing distinguishes the two. Backtesting on the feed the
engine actually trades on makes that question go away.

This is a backtest-only source. The live engine keeps its yfinance fallback,
because that is what carries it through a Kite session expiring mid-session —
see issue #23, where a dead token cost 5h20m of a trading day.

    python kite_history.py --days 730                  # the NIFTY 100
    python kite_history.py --symbols RELIANCE,TCS --days 365
    python kite_history.py --status                    # what's cached
"""
import argparse
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import config

logger = logging.getLogger("trading_bot")

DB_PATH = Path(__file__).parent / "data" / "kite_history.db"

# Kite allows a limited window per historical request and the limit varies by
# interval. 60 days is inside every documented limit for intraday intervals,
# so chunk to that rather than probing for the true maximum.
CHUNK_DAYS = 60

# Kite's historical endpoint is documented at 3 requests/second. Leave room:
# being throttled mid-pull is far more expensive than being slightly slower.
MIN_SECONDS_BETWEEN_REQUESTS = 0.4

_KITE_INTERVAL = {"1m": "minute", "3m": "3minute", "5m": "5minute",
                  "10m": "10minute", "15m": "15minute", "30m": "30minute",
                  "60m": "60minute", "1h": "60minute", "1d": "day"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    symbol TEXT NOT NULL, interval TEXT NOT NULL, ts INTEGER NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume INTEGER,
    PRIMARY KEY (symbol, interval, ts)
);
CREATE INDEX IF NOT EXISTS idx_candles_lookup ON candles(symbol, interval, ts);
-- Which windows have already been asked for, so an interrupted two-year pull
-- resumes instead of starting again. Recorded even when a window came back
-- empty: a holiday or a pre-listing stretch is a real answer, not a gap.
CREATE TABLE IF NOT EXISTS fetched (
    symbol TEXT NOT NULL, interval TEXT NOT NULL,
    from_date TEXT NOT NULL, to_date TEXT NOT NULL,
    rows INTEGER, fetched_at REAL,
    PRIMARY KEY (symbol, interval, from_date, to_date)
);
"""

_local = threading.local()


def _conn():
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        conn.commit()
        _local.conn = conn
    return conn


def _reset_connection():
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
    _local.conn = None


class RateLimiter:
    """One gate for the whole process, so concurrent callers can't between
    them exceed what a single caller would."""

    def __init__(self, min_interval=MIN_SECONDS_BETWEEN_REQUESTS):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self):
        with self._lock:
            gap = time.time() - self._last
            if gap < self.min_interval:
                time.sleep(self.min_interval - gap)
            self._last = time.time()


_limiter = RateLimiter()


def _chunks(start: datetime, end: datetime, days=CHUNK_DAYS):
    """Windows covering [start, end], oldest first, each at most `days` long."""
    out = []
    cursor = start
    while cursor < end:
        stop = min(cursor + timedelta(days=days), end)
        out.append((cursor, stop))
        cursor = stop
    return out


def _already_fetched(symbol, interval, frm, to) -> bool:
    row = _conn().execute(
        "SELECT 1 FROM fetched WHERE symbol=? AND interval=? AND from_date=? AND to_date=?",
        (symbol, interval, frm.isoformat(), to.isoformat())).fetchone()
    return row is not None


def _store(symbol, interval, frm, to, rows):
    conn = _conn()
    with conn:
        if rows:
            conn.executemany(
                "INSERT OR REPLACE INTO candles (symbol, interval, ts, open, high, low, close, volume) "
                "VALUES (?,?,?,?,?,?,?,?)",
                [(symbol, interval, int(r["date"].timestamp()), float(r["open"]), float(r["high"]),
                  float(r["low"]), float(r["close"]), int(r["volume"] or 0)) for r in rows])
        conn.execute(
            "INSERT OR REPLACE INTO fetched (symbol, interval, from_date, to_date, rows, fetched_at) "
            "VALUES (?,?,?,?,?,?)",
            (symbol, interval, frm.isoformat(), to.isoformat(), len(rows), time.time()))


def download_symbol(symbol, interval="5m", days=730, kite=None, token_for=None, progress=None) -> dict:
    """Fill the cache for one symbol. Returns counts; never raises for a single
    failed window — a two-year pull across 100 stocks should not be lost to one
    bad response, and the window simply stays unrecorded so a rerun retries it."""
    import data_provider
    kite = kite or data_provider._get_kite()
    token_for = token_for or data_provider._instrument_token
    kite_interval = _KITE_INTERVAL.get(interval, "5minute")

    try:
        token = token_for(symbol)
    except Exception as exc:
        logger.warning("kite_history: no instrument token for %s (%s)", symbol, exc)
        return {"symbol": symbol, "windows": 0, "rows": 0, "skipped": 0, "errors": 1}

    end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    counts = {"symbol": symbol, "windows": 0, "rows": 0, "skipped": 0, "errors": 0}

    for frm, to in _chunks(start, end):
        if _already_fetched(symbol, interval, frm, to):
            counts["skipped"] += 1
            continue
        _limiter.wait()
        try:
            rows = kite.historical_data(token, frm, to, kite_interval) or []
        except Exception as exc:
            counts["errors"] += 1
            logger.warning("kite_history: %s %s..%s failed (%s)", symbol, frm.date(), to.date(), exc)
            continue
        _store(symbol, interval, frm, to, rows)
        counts["windows"] += 1
        counts["rows"] += len(rows)
        if progress:
            progress(symbol, frm, to, len(rows))
    return counts


def download(symbols, interval="5m", days=730, progress=None) -> dict:
    total = {"symbols": 0, "windows": 0, "rows": 0, "skipped": 0, "errors": 0}
    for symbol in symbols:
        c = download_symbol(symbol, interval=interval, days=days, progress=progress)
        total["symbols"] += 1
        for k in ("windows", "rows", "skipped", "errors"):
            total[k] += c[k]
    return total


def load(symbol, interval="5m", days=None) -> list:
    """Cached candles, oldest first, in the shape data_provider returns."""
    sql = "SELECT ts, open, high, low, close, volume FROM candles WHERE symbol=? AND interval=?"
    args = [symbol, interval]
    if days:
        sql += " AND ts >= ?"
        args.append(int((datetime.now() - timedelta(days=days)).timestamp()))
    sql += " ORDER BY ts ASC"
    return [
        {"time": datetime.fromtimestamp(r["ts"]).isoformat(),
         "open": r["open"], "high": r["high"], "low": r["low"],
         "close": r["close"], "volume": r["volume"]}
        for r in _conn().execute(sql, args)
    ]


def load_batch(symbols, interval="5m", days=None) -> dict:
    out = {}
    for s in symbols:
        candles = load(s, interval=interval, days=days)
        if candles:
            out[s] = candles
    return out


def available(interval="5m") -> bool:
    """True when the cache holds anything usable for this interval."""
    if not DB_PATH.exists():
        return False
    try:
        row = _conn().execute("SELECT 1 FROM candles WHERE interval=? LIMIT 1", (interval,)).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def status(interval="5m") -> dict:
    if not DB_PATH.exists():
        return {"cached": False, "symbols": 0, "candles": 0, "note": "No cache yet — run kite_history.py"}
    c = _conn()
    row = c.execute("SELECT COUNT(*) n, COUNT(DISTINCT symbol) s, MIN(ts) lo, MAX(ts) hi "
                    "FROM candles WHERE interval=?", (interval,)).fetchone()
    if not row["n"]:
        return {"cached": False, "symbols": 0, "candles": 0, "note": "Cache exists but holds no candles"}
    sessions = c.execute("SELECT COUNT(DISTINCT date(ts,'unixepoch')) d FROM candles WHERE interval=?",
                         (interval,)).fetchone()["d"]
    return {
        "cached": True,
        "symbols": row["s"],
        "candles": row["n"],
        "sessions": sessions,
        "from": datetime.fromtimestamp(row["lo"]).date().isoformat(),
        "to": datetime.fromtimestamp(row["hi"]).date().isoformat(),
        "db_mb": round(DB_PATH.stat().st_size / 1e6, 1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--symbols", help="Comma-separated NSE symbols (default: the NIFTY 100 universe)")
    parser.add_argument("--interval", default=config.CANDLE_INTERVAL)
    parser.add_argument("--days", type=int, default=730, help="How far back to fetch (default: 2 years)")
    parser.add_argument("--status", action="store_true", help="Show what's cached and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.status:
        for k, v in status(args.interval).items():
            print(f"  {k}: {v}")
        return

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        import universe
        symbols = [r["symbol"] for r in universe.load()]

    print(f"Fetching {args.days}d of {args.interval} candles for {len(symbols)} symbols from Kite.")
    print(f"Cache: {DB_PATH}")
    print(f"About {len(_chunks(datetime.now() - timedelta(days=args.days), datetime.now()))} windows per symbol, "
          f"paced at {1/MIN_SECONDS_BETWEEN_REQUESTS:.1f} req/s — already-fetched windows are skipped.\n")

    started = time.time()
    done = [0]

    def progress(symbol, frm, to, rows):
        done[0] += 1
        if done[0] % 10 == 0:
            print(f"  {done[0]:>5} windows · {symbol} {frm.date()}..{to.date()} · {rows} candles", flush=True)

    total = download(symbols, interval=args.interval, days=args.days, progress=progress)
    print(f"\nDone in {time.time() - started:.0f}s: {total['rows']:,} candles over {total['windows']} windows "
          f"({total['skipped']} already cached, {total['errors']} errors).")
    for k, v in status(args.interval).items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
