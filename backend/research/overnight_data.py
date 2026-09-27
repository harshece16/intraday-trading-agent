"""
Overnight-ETF line (owner decision 2026-09-26): 1-minute bars for the Nifty
ETFs and the Nifty 50 index from Kite, selection sample only (2015-2025).
Data only; no return is computed here.

    .venv/bin/python research/overnight_data.py fetch    # needs a live Kite session

Writes backend/data/overnight_1m.db (git-ignored). The 2026 held-out window is
never requested.
"""

import datetime
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

DB = os.path.join(BACKEND, "data", "overnight_1m.db")
INSTRUMENTS = {"NIFTYBEES": 2707457, "SETFNIF50": 2605057, "NIFTY 50": 256265, "INDIA VIX": 264969}
START, END = datetime.date(2015, 1, 1), datetime.date(2025, 12, 31)
CHUNK_DAYS = 55


def conn():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS bars (symbol TEXT, ts TEXT, open REAL, high REAL, low REAL, close REAL, "
              "volume INTEGER, PRIMARY KEY (symbol, ts))")
    c.execute("CREATE TABLE IF NOT EXISTS fetched (symbol TEXT, frm TEXT, upto TEXT, rows INTEGER, "
              "PRIMARY KEY (symbol, frm))")
    return c


def fetch():
    import data_provider
    kite = data_provider._get_kite()
    c = conn()
    done = {(r[0], r[1]) for r in c.execute("SELECT symbol, frm FROM fetched")}
    for sym, tok in INSTRUMENTS.items():
        d = START
        while d <= END:
            e = min(d + datetime.timedelta(days=CHUNK_DAYS - 1), END)
            if (sym, d.isoformat()) not in done:
                for attempt in range(3):
                    try:
                        rows = kite.historical_data(tok, datetime.datetime.combine(d, datetime.time(9, 0)),
                                                    datetime.datetime.combine(e, datetime.time(15, 40)), "minute")
                        break
                    except Exception as exc:
                        print(f"{sym} {d} retry {attempt + 1}: {str(exc)[:80]}", flush=True)
                        time.sleep(2 + 2 * attempt)
                else:
                    raise SystemExit(f"{sym} {d}: giving up")
                c.executemany("INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?,?,?)",
                              [(sym, r["date"].strftime("%Y-%m-%d %H:%M"), r["open"], r["high"], r["low"], r["close"],
                                int(r.get("volume") or 0)) for r in rows])
                c.execute("INSERT OR REPLACE INTO fetched VALUES (?,?,?,?)", (sym, d.isoformat(), e.isoformat(), len(rows)))
                c.commit()
                time.sleep(0.4)
            d = e + datetime.timedelta(days=1)
        n, lo, hi = c.execute("SELECT COUNT(*), MIN(ts), MAX(ts) FROM bars WHERE symbol=?", (sym,)).fetchone()
        print(f"{sym}: {n} bars, {lo} -> {hi}", flush=True)
    print("fetch done", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        fetch()
