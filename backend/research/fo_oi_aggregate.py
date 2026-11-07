"""Trial 207 data: NSE F&O bhavcopy -> one row per stock-futures symbol-day.

Rules: docs/research/prereg-oi-buildup.md ("Data"). Stdlib only, so it runs as
one copied file on sahab-pc, where the zips live on /mnt/data. Output columns:
date, symbol, oi (shares, summed over every live expiry), n_exp, expiry_day
(1 when any stock future expires that date).

    python3 -I fo_oi_aggregate.py build /mnt/data/trader-sahab/fo_bhav fo_oi_daily.csv.gz

`fetch` is route (a) of the prereg's "Terms" bullet: NSE's Terms of Use forbid
systematic collection, so it is run only on the owner's explicit choice.

    python3 -I fo_oi_aggregate.py fetch /mnt/data/trader-sahab/fo_bhav 2009-01-01 2025-12-31
"""
import csv
import datetime as dt
import gzip
import io
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

OLD_URL = ("https://nsearchives.nseindia.com/content/historical/DERIVATIVES/"
           "{y}/{mon}/fo{d:02d}{mon}{y}bhav.csv.zip")
NEW_URL = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"
UDIFF_FROM = dt.date(2024, 7, 8)   # NSE's first UDiFF F&O file; either name is tried on a 404
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
PAUSE = 1.5                        # seconds between requests

# (instrument column, stock-future code, symbol, expiry, OI, trade date, date format)
FORMATS = (("INSTRUMENT", "FUTSTK", "SYMBOL", "EXPIRY_DT", "OPEN_INT", "TIMESTAMP", "%d-%b-%Y"),
           ("FinInstrmTp", "STF", "TckrSymb", "XpryDt", "OpnIntrst", "TradDt", "%Y-%m-%d"))


def urls(day):
    old = OLD_URL.format(y=day.year, mon=day.strftime("%b").upper(), d=day.day)
    new = NEW_URL.format(ymd=day.strftime("%Y%m%d"))
    return (new, old) if day >= UDIFF_FROM else (old, new)


def fetch(folder, first, last):
    day, end = dt.date.fromisoformat(first), dt.date.fromisoformat(last)
    got = missing = 0
    while day <= end:
        path = os.path.join(folder, str(day.year), day.strftime("%Y%m%d") + ".zip")
        if day.weekday() < 5 and not os.path.exists(path):
            data = None
            for url in urls(day):
                data = get(url)
                time.sleep(PAUSE)
                if data:
                    break
            if data:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path + ".part", "wb") as fh:
                    fh.write(data)
                os.replace(path + ".part", path)
                got += 1
            else:
                missing += 1      # a holiday, or a gap stage 0 lists against the cash sessions
        day += dt.timedelta(days=1)
    print(f"fetched {got}, no file for {missing} weekdays")


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            return body if body[:2] == b"PK" else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(10 * (i + 1))
    raise RuntimeError(f"giving up on {url}")


def parse(data):
    """(trade date ISO, {symbol: [oi, n_exp]}, expiry_day) from one zip's bytes."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        text = io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace")
        rows = csv.reader(text)
        head = [h.strip() for h in next(rows)]
        ins_c, code, sym_c, exp_c, oi_c, date_c, dfmt = next(f for f in FORMATS if f[0] in head)
        ins, sym, exp, oi, date = (head.index(c) for c in (ins_c, sym_c, exp_c, oi_c, date_c))
        out, day, expiry_day = {}, None, False
        for r in rows:
            if len(r) <= max(ins, sym, exp, oi, date) or r[ins].strip() != code:
                continue
            d = dt.datetime.strptime(r[date].strip(), dfmt).date().isoformat()
            e = dt.datetime.strptime(r[exp].strip(), dfmt).date().isoformat()
            if day is None:
                day = d
            acc = out.setdefault(r[sym].strip(), [0, 0])
            acc[0] += int(float(r[oi] or 0))
            acc[1] += 1
            expiry_day = expiry_day or e == d
    return day, out, expiry_day


def build(folder, out_path):
    seen, rows, bad = set(), [], []
    for root, _dirs, files in os.walk(folder):
        for f in sorted(files):
            if not f.endswith(".zip"):
                continue
            try:
                with open(os.path.join(root, f), "rb") as fh:
                    day, syms, expiry_day = parse(fh.read())
            except Exception as e:   # noqa: BLE001  (a bad file is listed, not fatal)
                bad.append((f, repr(e)[:80]))
                continue
            if day is None or day in seen:
                bad.append((f, "empty or duplicate date"))
                continue
            seen.add(day)
            rows += [(day, s, v[0], v[1], int(expiry_day)) for s, v in syms.items()]
    rows.sort()
    with gzip.open(out_path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(("date", "symbol", "oi", "n_exp", "expiry_day"))
        w.writerows(rows)
    print(f"{len(seen)} sessions, {len(rows)} symbol-days -> {out_path}; bad files: {len(bad)}")
    for b in bad[:20]:
        print("  bad", *b)


if __name__ == "__main__":
    if sys.argv[1:2] == ["fetch"]:
        fetch(*sys.argv[2:5])
    elif sys.argv[1:2] == ["build"]:
        build(*sys.argv[2:4])
    else:
        sys.exit(__doc__)
