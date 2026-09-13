"""
The tradable universe: NIFTY 100 constituents (large, liquid, F&O-eligible
names with tight spreads), refreshed weekly from NSE's published list and
cached in data/nifty100.csv so the app still works offline.
"""

import csv
import io
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger("trading_bot")

CSV_PATH = Path(__file__).parent / "data" / "nifty100.csv"
SOURCE_URL = "https://archives.nseindia.com/content/indices/ind_nifty100list.csv"
REFRESH_SECONDS = 7 * 86400
_rows = None


def _parse(text):
    return [
        {"symbol": r["Symbol"].strip().upper(), "name": r["Company Name"].strip(), "industry": r["Industry"].strip()}
        for r in csv.DictReader(io.StringIO(text))
        if r.get("Symbol")
    ]


def load():
    global _rows
    if _rows is not None:
        return _rows
    stale = not CSV_PATH.exists() or time.time() - CSV_PATH.stat().st_mtime > REFRESH_SECONDS
    if stale:
        try:
            resp = requests.get(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            resp.raise_for_status()
            if len(_parse(resp.text)) >= 50:
                CSV_PATH.parent.mkdir(exist_ok=True)
                CSV_PATH.write_text(resp.text)
        except Exception as exc:
            logger.warning(f"Could not refresh NIFTY 100 list ({exc}); using cached copy")
    _rows = _parse(CSV_PATH.read_text()) if CSV_PATH.exists() else []
    return _rows


def by_symbol():
    return {r["symbol"]: r for r in load()}
