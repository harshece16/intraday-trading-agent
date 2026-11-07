"""Trial 207 data: NSE F&O bhavcopy -> one row per stock-futures symbol-day.

Rules: docs/research/prereg-oi-buildup.md ("Data"). Stdlib only, so it runs as
one copied file on sahab-pc, where the zips live on /mnt/data. Output columns:
date, symbol, oi (shares, summed over every live expiry), n_exp (contracts),
chg (the file's own change in OI, summed), expiry_day (1 when any stock future
expires that date, by either UDiFF expiry column, or it is the last file day
before an expiry listed on a holiday), fmt (old or udiff) and
day_expiries (distinct stock-future expiries in the file). A sidecar
<out>.meta.json lists every bad file and the file count per format.

    python3 -I fo_oi_aggregate.py build /mnt/data/trader-sahab/fo_bhav fo_oi_daily.csv.gz

`fetch` is route (a) of the prereg's "Terms" bullet: NSE's Terms of Use forbid
systematic collection, so it is run only on the owner's explicit choice.

    python3 -I fo_oi_aggregate.py fetch /mnt/data/trader-sahab/fo_bhav 2009-01-01 2025-12-31
"""
import bisect
import csv
import datetime as dt
import gzip
import io
import json
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
HELD_OUT = dt.date(2026, 1, 1)     # never fetched before a pass (prereg "Rules")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
PAUSE = 1.5                        # seconds between requests

# exp: every expiry column; a day is an expiry day if any of them equals the trade date
FORMATS = (
    {"name": "old", "ins": "INSTRUMENT", "code": "FUTSTK", "sym": "SYMBOL", "exp": ("EXPIRY_DT",),
     "oi": "OPEN_INT", "chg": "CHG_IN_OI", "date": "TIMESTAMP", "fmt": "%d-%b-%Y"},
    {"name": "udiff", "ins": "FinInstrmTp", "code": "STF", "sym": "TckrSymb",
     "exp": ("XpryDt", "FininstrmActlXpryDt"), "oi": "OpnIntrst", "chg": "ChngInOpnIntrst",
     "date": "TradDt", "fmt": "%Y-%m-%d"},
)
DATE_FALLBACKS = ("%d-%b-%y", "%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y")


def urls(day):
    old = OLD_URL.format(y=day.year, mon=day.strftime("%b").upper(), d=day.day)
    new = NEW_URL.format(ymd=day.strftime("%Y%m%d"))
    return (new, old) if day >= UDIFF_FROM else (old, new)


def fetch(folder, first, last):
    day, end = dt.date.fromisoformat(first), dt.date.fromisoformat(last)
    if end >= HELD_OUT:
        sys.exit(f"refusing: {last} reaches the 2026 held-out window")
    got = missing = 0
    while day <= end:
        path = os.path.join(folder, str(day.year), day.strftime("%Y%m%d") + ".zip")
        if not os.path.exists(path):
            data = None
            # weekends: one try at the era's own name (Budget Saturdays, Muhurat, special sessions)
            for url in urls(day) if day.weekday() < 5 else urls(day)[:1]:
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
            elif day.weekday() < 5:
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


def _date(text, fmt):
    text = text.strip()
    for f in (fmt,) + DATE_FALLBACKS:
        try:
            return dt.datetime.strptime(text, f).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"unparsed date {text!r}")


def _num(text):
    text = text.strip()
    return 0 if text in ("", "-") else int(float(text))


def parse(data):
    """(trade date ISO, {symbol: [oi, contracts, chg]}, expiry_day, info) from one zip's bytes."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        rows = csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig", errors="replace"))
        head = [h.strip() for h in next(rows)]
        f = next(f for f in FORMATS if f["ins"] in head)
        ins, sym, oi, date = (head.index(f[k]) for k in ("ins", "sym", "oi", "date"))
        exps = [head.index(c) for c in f["exp"] if c in head]
        chg = head.index(f["chg"]) if f["chg"] in head else None
        need = max([ins, sym, oi, date] + exps + ([chg] if chg is not None else []))
        out, day, expiry_day, expiries = {}, None, False, set()
        for r in rows:
            if len(r) <= need or r[ins].strip() != f["code"]:
                continue
            d = _date(r[date], f["fmt"])
            es = {_date(r[i], f["fmt"]) for i in exps if r[i].strip()}
            day = day or d
            acc = out.setdefault(r[sym].strip(), [0, 0, 0])
            acc[0] += _num(r[oi])
            acc[1] += 1
            acc[2] += _num(r[chg]) if chg is not None else 0
            expiries |= es
            expiry_day = expiry_day or d in es
    return day, out, expiry_day, {"format": f["name"], "expiries": len(expiries), "has_chg": chg is not None,
                                  "listed": expiries}


def build(folder, out_path):
    seen, rows, bad, per_format, listed = set(), [], [], {}, set()
    for root, _dirs, files in os.walk(folder):
        for f in sorted(files):
            if not f.endswith(".zip"):
                continue
            try:
                with open(os.path.join(root, f), "rb") as fh:
                    day, syms, expiry_day, info = parse(fh.read())
            except Exception as e:   # noqa: BLE001  (a bad file is listed, not fatal)
                bad.append((f, repr(e)[:120]))
                continue
            if day is None or day in seen:
                bad.append((f, "empty or duplicate date"))
                continue
            seen.add(day)
            per_format[info["format"]] = per_format.get(info["format"], 0) + 1
            listed |= info["listed"]
            rows += [(day, s, v[0], v[1], v[2], int(expiry_day), info["format"], info["expiries"])
                     for s, v in syms.items()]
    # Amendment 2: an expiry listed on a day with no file (a holiday; April 2009 and 2014) was
    # settled on the last file day before it, so that day is the expiry day
    days = sorted(seen)
    moved = sorted({days[bisect.bisect_left(days, e) - 1] for e in listed
                    if e not in seen and days and days[0] < e <= days[-1]})
    rows = sorted(r[:5] + (1 if r[0] in moved else r[5],) + r[6:] for r in rows)
    with gzip.open(out_path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(("date", "symbol", "oi", "n_exp", "chg", "expiry_day", "fmt", "day_expiries"))
        w.writerows(rows)
    with open(out_path + ".meta.json", "w") as fh:
        json.dump({"sessions": len(seen), "symbol_days": len(rows), "files_per_format": per_format,
                   "bad_files": bad, "moved_expiries": moved}, fh, indent=1)
    print(f"{len(seen)} sessions, {len(rows)} symbol-days -> {out_path}; bad files: {len(bad)}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["fetch"]:
        fetch(*sys.argv[2:5])
    elif sys.argv[1:2] == ["build"]:
        build(*sys.argv[2:4])
    else:
        sys.exit(__doc__)
