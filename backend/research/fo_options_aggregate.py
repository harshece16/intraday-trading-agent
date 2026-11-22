"""Trials 208/209 data: NSE F&O bhavcopy -> NIFTY and BANKNIFTY option and future rows on expiry days.

Rules: docs/research/prereg-index-premium.md ("Data"). Stdlib only, so it runs as one
copied file on sahab-pc, where the zips live on /mnt/data. For each symbol it keeps a
session only when an option series of that symbol expires on it (or expired on it
because the listed expiry was a day with no file), and then writes every index-future
row and every index-option row whose expiry is within 45 days. A sidecar
<out>.meta.json lists every session date and every bad file. No 2026 file is opened.

    python3 -I fo_options_aggregate.py build /mnt/data/trader-sahab/fo_bhav /mnt/data/trader-sahab/fo_opt_expiry.csv.gz
    python3 -I fo_options_aggregate.py selftest
"""
import csv
import datetime as dt
import functools
import gzip
import io
import json
import os
import sys
import zipfile

SYMBOLS = ("NIFTY", "BANKNIFTY")
HELD_OUT = "2026-01-01"      # never read before a pass (prereg "Rules that do not change")
NEAR_DAYS = 45               # the expiring series and the next one, monthly or weekly
HEADER = ("date", "symbol", "kind", "expiry", "expiry2", "strike", "close", "settle",
          "vol", "val", "oi", "und", "lot", "fmt")

# kind is F for a future, else CE / PE. expiry2 is UDiFF's actual expiry date.
FORMATS = (
    {"name": "old", "ins": "INSTRUMENT", "opt": "OPTIDX", "fut": "FUTIDX", "sym": "SYMBOL",
     "date": "TIMESTAMP", "fmt": "%d-%b-%Y",
     "cols": {"expiry": "EXPIRY_DT", "strike": "STRIKE_PR", "typ": "OPTION_TYP", "close": "CLOSE",
              "settle": "SETTLE_PR", "vol": "CONTRACTS", "val": "VAL_INLAKH", "oi": "OPEN_INT"}},
    {"name": "udiff", "ins": "FinInstrmTp", "opt": "IDO", "fut": "IDF", "sym": "TckrSymb",
     "date": "TradDt", "fmt": "%Y-%m-%d",
     "cols": {"expiry": "XpryDt", "expiry2": "FininstrmActlXpryDt", "strike": "StrkPric", "typ": "OptnTp",
              "close": "ClsPric", "settle": "SttlmPric", "vol": "TtlTradgVol", "val": "TtlTrfVal",
              "oi": "OpnIntrst", "und": "UndrlygPric", "lot": "NewBrdLotQty"}},
)
DATE_FALLBACKS = ("%d-%b-%y", "%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y")


@functools.lru_cache(maxsize=None)
def _date(text, fmt):
    for f in (fmt,) + DATE_FALLBACKS:
        try:
            return dt.datetime.strptime(text, f).date().isoformat()
        except ValueError:
            pass
    raise ValueError("unparsed date %r" % text)


def parse(data):
    """(trade date ISO, format name, rows) from one zip's bytes; rows follow HEADER[1:-1]."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        text = io.TextIOWrapper(z.open(name), encoding="utf-8-sig", errors="replace")
        head = [h.strip() for h in next(csv.reader([text.readline()]))]
        f = next(f for f in FORMATS if f["ins"] in head)
        ins, sym, date = (head.index(f[k]) for k in ("ins", "sym", "date"))
        col = {k: head.index(v) for k, v in f["cols"].items() if v in head}
        missing = [k for k in ("expiry", "strike", "typ", "close", "settle", "vol") if k not in col]
        if missing:
            raise ValueError("columns missing: %s" % missing)
        day, rows = None, []
        # every wanted row has NIFTY in it; skipping the rest before csv parsing is most of the speed
        for r in csv.reader(line for line in text if "NIFTY" in line):
            if len(r) <= max(col.values()) or r[sym].strip() not in SYMBOLS:
                continue
            code = r[ins].strip()
            if code not in (f["opt"], f["fut"]):
                continue
            d = _date(r[date].strip(), f["fmt"])
            if day is None:
                day = d
            elif d != day:
                raise ValueError("two trade dates in one file: %s, %s" % (day, d))

            def get(k):
                return r[col[k]].strip() if k in col else ""
            e2 = get("expiry2")
            rows.append((r[sym].strip(), "F" if code == f["fut"] else get("typ"),
                         _date(get("expiry"), f["fmt"]), _date(e2, f["fmt"]) if e2 else "",
                         get("strike"), get("close"), get("settle"), get("vol"), get("val"),
                         get("oi"), get("und"), get("lot")))
    return day, f["name"], rows


def expiry_rows(day, rows, next_day):
    """The rows to keep for `day`: per symbol, nothing unless an option series expires today
    (listed today, or listed on a later date that has no file before the next session)."""
    out = []
    limit = (dt.date.fromisoformat(day) + dt.timedelta(days=NEAR_DAYS)).isoformat()
    for s in SYMBOLS:
        mine = [r for r in rows if r[0] == s]
        ahead = [r[2] for r in mine if r[1] != "F" and r[2] >= day]
        if not ahead:
            continue
        nearest = min(ahead)
        today = nearest == day or any(r[3] == day for r in mine if r[1] != "F")
        moved = next_day is not None and nearest < next_day
        if today or moved:
            out += [r for r in mine if r[1] == "F" or r[2] <= limit]
    return out


def build(folder, out_path):
    paths = sorted((f, os.path.join(root, f)) for root, _dirs, files in os.walk(folder)
                   for f in files if f.endswith(".zip"))
    sessions, bad, per_format, kept, n = [], [], {}, {s: 0 for s in SYMBOLS}, 0
    held = None      # the previous session, written once the next session's date is known
    with gzip.open(out_path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)

        def flush(next_day):
            nonlocal n
            day, fmt, rows = held
            out = expiry_rows(day, rows, next_day)
            for s in {r[0] for r in out}:
                kept[s] += 1
            w.writerows((day,) + r + (fmt,) for r in out)
            n += len(out)

        for f, path in paths:
            if f[:8] >= HELD_OUT.replace("-", ""):
                bad.append((f, "held-out, not opened"))
                continue
            try:
                with open(path, "rb") as zf:
                    day, fmt, rows = parse(zf.read())
            except Exception as e:   # noqa: BLE001  (a bad file is listed, not fatal)
                bad.append((f, repr(e)[:120]))
                continue
            if day is None or day != "%s-%s-%s" % (f[:4], f[4:6], f[6:8]):
                bad.append((f, "no index rows, or the trade date is not the file's date: %s" % day))
                continue
            if held:
                flush(day)
            held = (day, fmt, rows)
            sessions.append(day)
            per_format[fmt] = per_format.get(fmt, 0) + 1
        if held:
            flush(None)
    with open(out_path + ".meta.json", "w") as fh:
        json.dump({"sessions": sessions, "rows": n, "files_per_format": per_format,
                   "expiry_days": kept, "bad_files": bad}, fh, indent=1)
    print("%d sessions, %d rows, expiry days %s -> %s; bad files: %d"
          % (len(sessions), n, kept, out_path, len(bad)))


def selftest():
    import tempfile
    old = "INSTRUMENT,SYMBOL,EXPIRY_DT,STRIKE_PR,OPTION_TYP,OPEN,HIGH,LOW,CLOSE,SETTLE_PR,CONTRACTS,VAL_INLAKH,OPEN_INT,CHG_IN_OI,TIMESTAMP,"
    new = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,"
           "OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,"
           "ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks")

    def o(ins, sym, exp, k, typ, close, stamp):
        return "%s,%s,%s,%s,%s,1,1,1,%s,%s,500,9.5,1000,0,%s," % (ins, sym, exp, k, typ, close, close, stamp)

    def u(ins, sym, exp, k, typ, close, day):
        return ("%s,%s,FO,NSE,%s,1,,%s,,%s,%s,%s,%s,X,1,1,1,%s,1,1,25000.5,%s,1000,0,500,9.5,7,F1,75,"
                % (day, day, ins, sym, exp, exp, k, typ, close, close))

    files = {
        # Thursday: NIFTY expires today; the far series (60 days) and the other symbols are dropped
        "20210603": [old, o("OPTIDX", "NIFTY", "03-Jun-2021", 15000, "CE", 687.1, "03-JUN-2021"),
                     o("OPTIDX", "NIFTY", "10-Jun-2021", 15700, "PE", 90, "03-JUN-2021"),
                     o("OPTIDX", "NIFTY", "26-Aug-2021", 15700, "PE", 300, "03-JUN-2021"),
                     o("FUTIDX", "NIFTY", "24-Jun-2021", 0, "XX", 15712.4, "03-JUN-2021"),
                     o("OPTIDX", "FINNIFTY", "03-Jun-2021", 15000, "CE", 5, "03-JUN-2021"),
                     o("OPTSTK", "RELIANCE", "24-Jun-2021", 2000, "CE", 5, "03-JUN-2021"),
                     o("OPTIDX", "BANKNIFTY", "10-Jun-2021", 35000, "CE", 5, "03-JUN-2021")],
        # no expiry today and the nearest one has a file: nothing kept
        "20210604": [old, o("OPTIDX", "NIFTY", "10-Jun-2021", 15700, "PE", 80, "04-JUN-2021")],
        # the listed expiry (the 10th) has no file before the next session (the 11th): moved to today
        "20210609": [old, o("OPTIDX", "NIFTY", "10-Jun-2021", 15700, "PE", 70, "09-JUN-2021")],
        "20210611": [new, u("IDO", "NIFTY", "2021-06-17", 15700, "PE", 60, "2021-06-11")],
        # UDiFF expiry day, last file: kept by its listed date
        "20210617": [new, u("IDO", "NIFTY", "2021-06-17", 15700, "PE", 0.05, "2021-06-17"),
                     u("IDF", "NIFTY", "2021-06-24", "", "", 15800, "2021-06-17")],
        "20260102": [new, u("IDO", "NIFTY", "2026-01-02", 26000, "PE", 1, "2026-01-02")],
    }
    with tempfile.TemporaryDirectory() as tmp:
        for name, lines in files.items():
            with zipfile.ZipFile(os.path.join(tmp, name + ".zip"), "w") as z:
                z.writestr("x.csv", "\n".join(lines) + "\n")
        out = os.path.join(tmp, "out.csv.gz")
        build(tmp, out)
        with gzip.open(out, "rt") as fh:
            rows = list(csv.DictReader(fh))
        with open(out + ".meta.json") as fh:
            meta = json.load(fh)
    got = [(r["date"], r["symbol"], r["kind"], r["expiry"], r["close"]) for r in rows]
    assert got == [("2021-06-03", "NIFTY", "CE", "2021-06-03", "687.1"),
                   ("2021-06-03", "NIFTY", "PE", "2021-06-10", "90"),
                   ("2021-06-03", "NIFTY", "F", "2021-06-24", "15712.4"),
                   ("2021-06-09", "NIFTY", "PE", "2021-06-10", "70"),
                   ("2021-06-17", "NIFTY", "PE", "2021-06-17", "0.05"),
                   ("2021-06-17", "NIFTY", "F", "2021-06-24", "15800")], got
    assert rows[-2]["und"] == "25000.5" and rows[-2]["lot"] == "75" and rows[-2]["fmt"] == "udiff"
    assert meta["sessions"] == ["2021-06-03", "2021-06-04", "2021-06-09", "2021-06-11", "2021-06-17"]
    assert meta["bad_files"] == [["20260102.zip", "held-out, not opened"]], meta["bad_files"]
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"] and len(sys.argv) == 4:
        build(*sys.argv[2:4])
    elif sys.argv[1:2] == ["selftest"]:
        selftest()
    else:
        sys.exit(__doc__)
