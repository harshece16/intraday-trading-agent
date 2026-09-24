"""
Point-in-time NIFTY 100 membership, rebuilt from NSE Indices' own press releases.

RESEARCH ONLY (3f stage 0b). Nothing in the live path imports this.

Why it exists: a "buy last year's winners" test run on today's NIFTY 100 selects,
by construction, the stocks that rose into the index. The 3f pre-registration
makes month-by-month membership a hard gate, not a caveat.

How it works:

  1. Every NSE Indices press release announcing index changes (niftyindices.com,
     /Press_Release/ind_prsDDMMYYYY.pdf, 2009 onward) is converted to text and
     parsed for its "Nifty 50" and "Nifty Next 50" sections (older names: "S&P
     CNX Nifty", "CNX Nifty Junior"). Nifty 100 is their union by construction,
     so the union is rebuilt from the two walks and the releases' explicit
     "Nifty 100" / "CNX 100" sections are used only as a cross-check.
  2. Each index is walked BACKWARDS from its current constituent list
     (ind_nifty50list.csv, ind_niftynext50list.csv): before a change, the set is
     (current - inclusions) + exclusions. The count must be exactly 50 at every
     step (51 while the Tata Motors DVR was carried as an additional security),
     every inclusion walked back must be a member, and no exclusion may be.
     One missed release breaks the chain, so the chain's length is the proof.
  3. Nifty 100 = Nifty 50 ∪ Nifty Next 50 ∪ additional securities the releases
     put in Nifty 100 alone (the DVR, 2016-04-01..2020-06-26 and
     2023-09-29..2024-08-30), snapshotted at each month end.

Two announcement rules, both from the releases themselves:
  - A change announced twice for one stock (same index, same direction, no
    opposite change between) is one change: the later-dated release is the one
    that held. Covers Yes Bank's removal brought forward to 2020-03-19, and the
    March 2020 review deferred to June 26, 2020.
  - NSE Indices' May 13, 2020 release deferred the whole review announced on
    Feb 18, 2020 (effective March 27); it was re-run and re-announced on June
    10, 2020 with a different list. The Feb 18 announcement is voided.

Corporate-adjustment releases (a spun-off or demerged entity added to indices
at a notional price for a few sessions, e.g. JIOFIN in July 2023, DUMMYITC in
January 2025) are ignored: those securities have no price history and are not
investable members on any signal date.

One release (August 23, 2021) is an image-only PDF; its tables were transcribed
by hand from the rendered pages into data/nifty100_manual_events.csv, which
overrides the parse for that file and records the source per row.
"""
from __future__ import annotations

import calendar
import collections
import csv
import datetime
import glob
import os
import re
import unicodedata

MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December|"
          "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec")

# Symbols the NSE reference files no longer resolve (delisted, merged or renamed
# before NSE's symbolchange.csv begins). Mapped to the symbol under which the
# listing continued where it did (Sesa Goa -> Vedanta), else to the last symbol.
HAND_SYMBOLS = {
    "abb": "ABB", "aventis pharma": "SANOFI", "corporation bank": "CORPBANK",
    "moser baer india": "MOSERBAER", "national aluminium co": "NATIONALUM", "nirma": "NIRMA",
    "reliance petroleum": "RPL", "satyam computer services": "SATYAMCOMP", "sesa goa": "VEDL",
    "titan industries": "TITAN", "united phosphorous": "UPL", "vijaya bank": "VIJAYABANK",
    "mangalore refinery and petrochemicals": "MRPL", "jaiprakash associates": "JPASSOCIAT",
    "infrastructure development finance co": "IDFC", "crompton greaves": "CROMPGREAV",
    "indiabulls real estate": "IBREALEST", "reliance capital": "RELCAPITAL",
    "ing vysya bank": "INGVYSYABK", "idea cellular": "IDEA",
    "rural electrification corporation": "RECLTD", "shriram transport finance co": "SRTRANSFIN",
    "jindal steel and power": "JINDALSTEL", "punj lloyd": "PUNJLLOYD",
    "mahindra and mahindra financial services m and mfin": "M&MFIN",
    "mahindra and mahindra financial services": "M&MFIN",
}
# (release file, effective date) pairs that never took effect — see the docstring.
VOIDED = {("ind_prs18022020.txt", "2020-03-27")}
# Securities carried in an index in addition to its 50 companies (a second share class).
ADDITIONAL = {"TATAMTRDVR"}

IDX = {
    "N50": r"(?:S&P\s+CNX\s+Nifty|CNX\s+Nifty|Nifty\s*50|NIFTY\s*50)",
    "NN50": r"(?:CNX\s+Nifty\s+Junior|Nifty\s+Next\s*50|NIFTY\s+Next\s*50)",
    "N100": r"(?:CNX\s*100|Nifty\s*100|NIFTY\s*100)",
}
# A heading's numbering, then the name. Space, tab, page break and nbsp may
# precede it — never a newline, or a heading would anchor on the blank line above.
PFX = r"^[ \t\x0c\xa0]*(?:\(?\d{1,2}\)|\d{1,2}[.)]|\(?[a-zA-Z]\)|[A-Z][.)])?[ \t]*"
SEC = {k: re.compile(PFX + v + r"\s*(?:Index)?\s*:?\s*$", re.I | re.M) for k, v in IDX.items()}
ANYHDR = re.compile(PFX + r"(?:(?:S&P\s+)?(?:CNX|Nifty|NIFTY)[A-Za-z0-9 &%.,\-]*?(?:\s+Index)?"
                    r"|Replacements?\b[^\n]*|Changes?\b[^\n]*|Consequent[^\n]*)\s*:?\s*$", re.I | re.M)
ROW = re.compile(r"^\s*(\d{1,3})\s+(.+?)(?:\s{2,}([A-Z0-9&\-]{2,20}))?\s*$")
FOLLOWING = re.compile(r"\s*The following (company|companies|securit|scrip)", re.I)
EFFECTIVE = re.compile(r"(?:effective\s+from|w\.?e\.?f\.?|with\s+effect\s+from)\s*[:\-]?\s*"
                       r"([A-Za-z]+\.?\s+\d{1,2},?\s*\d{4})", re.I)
PROSE = re.compile(r"\(Symbol:\s*([A-Z0-9&\-]+)\)\s*(?:shall|will|would)\s+be\s+(excluded\s+from|included\s+in)"
                   r"\s+(?:the\s+)?following\s+ind(?:ex|ices)\s*:?\s*(.{0,1500})", re.I | re.S)
CORP_ADJ = re.compile(r"spun[- ]off entity|demerged entity|dummy symbol|with a dummy|zero price|special pre-open session", re.I)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).replace("’", "'").lower().replace("&", " and ")
    s = re.sub(r"\b(limited|ltd\.?|ltd|the)\b", "", s)
    s = re.sub(r"\(india\)|\(i\)", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(txt: str):
    m = re.search(r"(%s)[a-z]*\.?\s+(\d{1,2}),?\s*(\d{4})" % MONTHS, txt, flags=re.I)
    if not m:
        return None
    try:
        return datetime.datetime.strptime(f"{m.group(1)[:3].title()} {int(m.group(2))} {m.group(3)}",
                                          "%b %d %Y").date().isoformat()
    except ValueError:
        return None


def release_date(base: str) -> str:
    m = re.search(r"ind_prs(\d{2})(\d{2})(\d{4})", base)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


class SymbolMap:
    """Company name -> NSE symbol, from NSE's own files plus the hand map, with
    NSE's symbol-change history applied so a renamed stock walks under today's symbol."""

    def __init__(self, constituent_csvs=(), equity_l_csv=None, symbolchange_csv=None):
        self.name2sym = {}
        for f in constituent_csvs:
            for row in csv.DictReader(open(f)):
                self.name2sym[norm(row["Company Name"])] = row["Symbol"].strip()
        if equity_l_csv:
            for row in csv.DictReader(open(equity_l_csv)):
                self.name2sym.setdefault(norm(row["NAME OF COMPANY"]), row["SYMBOL"].strip())
        self.name2sym.update(HAND_SYMBOLS)
        self.symchange = {}
        if symbolchange_csv:
            for line in open(symbolchange_csv, errors="ignore"):
                p = [x.strip() for x in line.split(",")]
                if len(p) >= 4 and p[1] and p[2] and p[1] != "SM_KEY_SYMBOL":
                    self.symchange[p[1]] = p[2]

    def canon(self, sym: str) -> str:
        seen = set()
        while sym in self.symchange and sym not in seen:
            seen.add(sym)
            sym = self.symchange[sym]
        return sym

    def lookup(self, name: str):
        return self.name2sym.get(norm(name))


def _eff_date(t: str, pos: int):
    dm = list(EFFECTIVE.finditer(t[:pos]))
    if dm:
        return parse_date(dm[-1].group(1))
    dm = EFFECTIVE.search(t)
    return parse_date(dm.group(1)) if dm else None


def parse_release(text: str, base: str, symbols: SymbolMap) -> list:
    """Events {index, effective, action, symbol, name, file, layout} from one release."""
    t = text.replace("–", "-")
    events = []

    def add(idx, eff, action, name, sym, layout):
        sym = sym or symbols.lookup(name)
        events.append({"index": idx, "effective": eff, "action": action,
                       "symbol": symbols.canon(sym) if sym else "", "name": name, "file": base, "layout": layout})

    def is_heading(pos):
        after = [l for l in t[pos:pos + 400].splitlines()[1:6] if l.strip()][:3]
        return any(FOLLOWING.match(l) for l in after)

    hdr_positions = sorted({m.start() for m in ANYHDR.finditer(t)
                            if is_heading(m.start())
                            or re.match(r"\s*\d{1,2}\)\s*(Replacement|Change)", t[m.start():m.start() + 40], re.I)})
    for idx, rx in SEC.items():
        for sm in rx.finditer(t):
            if not is_heading(sm.start()):
                continue
            ends = [p for p in hdr_positions if p > sm.start()]
            block = t[sm.end(): ends[0] if ends else len(t)]
            eff, mode = _eff_date(t, sm.start()), None
            for line in block.splitlines():
                l = line.strip()
                if re.search(r"being\s+excluded|excluded\s*:|^exclusions?\b", l, re.I) and not re.search(r"included", l, re.I):
                    mode = "EXCL"
                    continue
                if re.search(r"being\s+included|included\s*:|^inclusions?\b", l, re.I):
                    mode = "INCL"
                    continue
                if mode is None or not l or re.match(r"^\s*Sr\.?\s*No", l, re.I):
                    continue
                rm = ROW.match(l)
                if not rm or len(rm.group(2)) > 70 or re.search(r"\s{4,}\S+\s{4,}", rm.group(2)):
                    continue
                if re.match(r"^(securities|companies|stocks|scrips)\.?$", rm.group(2).strip(), re.I):
                    continue  # "...index shall have\n101 securities." wrapped onto a numbered line
                sym = rm.group(3) if rm.group(3) and re.match(r"^[A-Z0-9&\-]+$", rm.group(3)) else None
                add(idx, eff, mode, rm.group(2).strip(), sym, "table")
    # Prose layout: "<Company> (Symbol: X) shall be excluded from the following indices:" + an index-name list.
    if not CORP_ADJ.search(t):
        for pm in PROSE.finditer(t):
            sym, action = pm.group(1), "EXCL" if pm.group(2).lower().startswith("excl") else "INCL"
            lst = pm.group(3)
            cut = re.search(r"\n\s*\n\s*[A-Za-z]", lst)
            lst = lst[:cut.start()] if cut else lst
            names = [re.sub(r"^\s*\d+\s+", "", x).strip() for x in lst.splitlines() if re.match(r"^\s*\d+\s+\S", x)]
            for idx, rx in IDX.items():
                if any(re.fullmatch(rx + r"\s*(?:Index)?", n, flags=re.I) for n in names):
                    add(idx, _eff_date(t, pm.start()), action, sym, sym, "prose")
    return events


def apply_manual(events: list, manual_csv: str, symbols: SymbolMap) -> list:
    """Replace the parse of image-only releases with hand-transcribed rows."""
    if not manual_csv or not os.path.exists(manual_csv):
        return events
    ov = list(csv.DictReader(open(manual_csv)))
    drop = {r["file"] for r in ov}
    out = [e for e in events if e["file"] not in drop]
    for r in ov:
        out.append({"index": r["index"], "effective": r["effective"], "action": r["action"],
                    "symbol": symbols.canon(r["symbol"]), "name": r["name"], "file": r["file"], "layout": "manual"})
    return out


def dedupe(events: list):
    """Drop voided announcements, then keep the later-dated release of any run of
    same-direction announcements for one (index, symbol). Returns (events, log)."""
    log = []
    kept = [e for e in events if (e["file"], e["effective"]) not in VOIDED]
    log += [("voided", e["index"], e["symbol"], e["action"], e["effective"], e["file"])
            for e in events if (e["file"], e["effective"]) in VOIDED]
    by = collections.defaultdict(list)
    for e in kept:
        if e["effective"] and e["symbol"]:
            by[(e["index"], e["symbol"])].append(e)
    keep = set()
    for key, lst in by.items():
        lst.sort(key=lambda e: (e["effective"], release_date(e["file"])))
        i = 0
        while i < len(lst):
            j = i
            while j + 1 < len(lst) and lst[j + 1]["action"] == lst[i]["action"]:
                j += 1
            run = lst[i:j + 1]
            winner = max(run, key=lambda e: release_date(e["file"]))
            for e in run:
                if e is winner:
                    keep.add(id(e))
                else:
                    log.append(("superseded", key[0], key[1], e["action"], e["effective"], e["file"],
                                winner["effective"], winner["file"]))
            i = j + 1
    return [e for e in kept if not (e["effective"] and e["symbol"]) or id(e) in keep], log


def walk(events: list, index: str, current: set, today: str):
    """Walk one index backwards from its current members. Returns (snapshots, steps):
    snapshots = [(date, set)] newest first — snapshots[i] is the set in force
    BEFORE the change dated snapshots[i-1]; steps carry the consistency checks."""
    ev = collections.defaultdict(lambda: {"INCL": set(), "EXCL": set()})
    for e in events:
        if e["index"] == index and e["effective"] and e["symbol"] and e["effective"] <= today:
            ev[e["effective"]][e["action"]].add(e["symbol"])
    mem, steps, snaps = set(current), [], [(today, set(current))]
    for d in sorted(ev, reverse=True):
        inc, exc = ev[d]["INCL"], ev[d]["EXCL"]
        bad_inc, bad_exc = inc - mem, exc & mem
        mem = (mem - inc) | exc
        snaps.append((d, set(mem)))
        expected = 50 + len(mem & ADDITIONAL)
        ok = len(mem) == expected and not bad_inc and not bad_exc
        steps.append({"date": d, "incl": sorted(inc), "excl": sorted(exc), "n": len(mem),
                      "bad_inc": sorted(bad_inc), "bad_exc": sorted(bad_exc), "ok": ok})
        if not ok:
            break
    return snaps, steps


def set_asof(snaps, date: str) -> set:
    """Membership in force on `date` (after any change effective that day)."""
    cur = snaps[0][1]
    for i, (dd, mem) in enumerate(snaps):
        if dd <= date:
            return snaps[i - 1][1] if i > 0 else snaps[0][1]
        cur = mem
    return cur


def overlay_asof(events: list, date: str) -> set:
    """Additional securities the releases put in Nifty 100 itself, in force on `date`."""
    out = set()
    for sym in ADDITIONAL:
        state = False
        for e in sorted((e for e in events if e["index"] == "N100" and e["symbol"] == sym and e["effective"]),
                        key=lambda e: e["effective"]):
            if e["effective"] <= date:
                state = e["action"] == "INCL"
        if state:
            out.add(sym)
    return out


def monthly_series(events, snaps_n50, snaps_nn50, start: str, today: str):
    """[(month, asof_date, members)] — Nifty 100 in force at each month end."""
    rows = []
    y, m = int(start[:4]), int(start[5:7])
    while (y, m) <= (int(today[:4]), int(today[5:7])):
        asof = min(datetime.date(y, m, calendar.monthrange(y, m)[1]).isoformat(), today)
        mem = set_asof(snaps_n50, asof) | set_asof(snaps_nn50, asof) | overlay_asof(events, asof)
        rows.append((f"{y:04d}-{m:02d}", asof, sorted(mem)))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return rows


def intervals(events, snaps_n50, snaps_nn50, today):
    """[(symbol, from, to, source_in, source_out)] — every spell a symbol spent in
    Nifty 100, at daily granularity. `to` is the last date in the index (empty
    while still a member); `source_*` is the release announcing the change."""
    dates = sorted({d for d, _ in snaps_n50} | {d for d, _ in snaps_nn50}
                   | {e["effective"] for e in events if e["index"] == "N100" and e["symbol"] in ADDITIONAL and e["effective"]})
    dates = [d for d in dates if d <= today]
    src = {}
    for e in events:
        if e["effective"] and e["symbol"]:
            src.setdefault((e["effective"], e["symbol"], e["action"]), e["file"])
    prev = set_asof(snaps_n50, "0000-00-00") | set_asof(snaps_nn50, "0000-00-00")  # the oldest reconstructed set
    open_since = {s: ("", "") for s in prev}
    out = []
    for d in dates:
        cur = set_asof(snaps_n50, d) | set_asof(snaps_nn50, d) | overlay_asof(events, d)
        for s in sorted(prev - cur):
            out.append((s, open_since[s][0], (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat(),
                        open_since[s][1], src.get((d, s, "EXCL"), "")))
            del open_since[s]
        for s in sorted(cur - prev):
            open_since[s] = (d, src.get((d, s, "INCL"), ""))
        prev = cur
    for s, (fr, so) in sorted(open_since.items()):
        out.append((s, fr, "", so, ""))
    return sorted(out, key=lambda r: (r[0], r[1]))


def cross_check_n100(events, snaps, today):
    """Explicit Nifty 100 sections vs the derived union. Returns mismatches, count checked."""
    ev100 = collections.defaultdict(lambda: {"INCL": set(), "EXCL": set()})
    for e in events:
        if e["index"] == "N100" and e["effective"] and e["symbol"] and e["effective"] <= today:
            ev100[e["effective"]][e["action"]].add(e["symbol"])

    def union_at(d):
        return set_asof(snaps["N50"], d) | set_asof(snaps["NN50"], d)
    mism, checked = [], 0
    for d, ch in sorted(ev100.items()):
        before = union_at((datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat())
        after = union_at(d)
        inc, exc = after - before, before - after
        checked += 1
        if inc != ch["INCL"] or exc != ch["EXCL"]:
            mism.append({"date": d, "explicit_incl": sorted(ch["INCL"]), "explicit_excl": sorted(ch["EXCL"]),
                         "derived_incl": sorted(inc), "derived_excl": sorted(exc)})
    return mism, checked


def load_constituents(path: str) -> set:
    return {row["Symbol"].strip() for row in csv.DictReader(open(path))}


def build(prs_dir, refs_dir, out_dir, today, manual_csv=None, start=None):
    """Regenerate the membership CSV and build log from a directory of press-release
    texts (prs_dir/ind_prs*.txt) and NSE reference files (refs_dir)."""
    symbols = SymbolMap(
        constituent_csvs=[os.path.join(refs_dir, f) for f in ("ind_nifty50list.csv", "ind_niftynext50list.csv")],
        equity_l_csv=os.path.join(refs_dir, "EQUITY_L.csv"),
        symbolchange_csv=os.path.join(refs_dir, "symbolchange.csv"))
    events = []
    for f in sorted(glob.glob(os.path.join(prs_dir, "ind_prs*.txt"))):
        events += parse_release(open(f, errors="ignore").read(), os.path.basename(f), symbols)
    events = apply_manual(events, manual_csv, symbols)
    events, log = dedupe(events)
    cur = {"N50": load_constituents(os.path.join(refs_dir, "ind_nifty50list.csv")),
           "NN50": load_constituents(os.path.join(refs_dir, "ind_niftynext50list.csv"))}
    snaps, report = {}, {}
    for idx in ("N50", "NN50"):
        snaps[idx], steps = walk(events, idx, cur[idx], today)
        report[idx] = {"steps": steps, "consistent_back_to": next((s["date"] for s in reversed(steps) if s["ok"]), None)
                       if all(s["ok"] for s in steps) else None,
                       "first_bad": next((s for s in steps if not s["ok"]), None)}
    mism, checked = cross_check_n100(events, snaps, today)
    earliest = max(v["consistent_back_to"] or today for v in report.values())
    start = start or earliest
    rows = monthly_series(events, snaps["N50"], snaps["NN50"], start, today)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "nifty100_membership_monthly.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["month", "asof", "n", "symbol"])
        for mo, asof, mem in rows:
            for sym in mem:
                w.writerow([mo, asof, len(mem), sym])
    with open(os.path.join(out_dir, "nifty100_membership.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "from", "to", "source_in", "source_out"])
        w.writerows(intervals(events, snaps["N50"], snaps["NN50"], today))
    with open(os.path.join(out_dir, "nifty100_changes.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["index", "effective", "action", "symbol", "name", "file", "layout"])
        w.writeheader()
        w.writerows(sorted(events, key=lambda e: (e["effective"] or "", e["index"], e["action"], e["symbol"])))
    summary = {
        "today": today, "start": start, "months": len(rows), "first_month": rows[0][0], "last_month": rows[-1][0],
        "sizes": dict(collections.Counter(len(m) for _, _, m in rows)),
        "distinct_symbols": len({s for _, _, mem in rows for s in mem}),
        "n50_consistent_back_to": report["N50"]["consistent_back_to"],
        "nn50_consistent_back_to": report["NN50"]["consistent_back_to"],
        "n50_first_bad": report["N50"]["first_bad"], "nn50_first_bad": report["NN50"]["first_bad"],
        "n100_sections_checked": checked, "n100_mismatches": mism,
        "dedupe_log": log, "events": len(events),
        "layouts": dict(collections.Counter(e["layout"] for e in events)),
        "unresolved_names": sorted({e["name"] for e in events if not e["symbol"]}),
    }
    return rows, summary


def main():
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--prs", required=True, help="directory of press-release texts (ind_prs*.txt)")
    ap.add_argument("--refs", required=True, help="directory with ind_nifty50list.csv, ind_niftynext50list.csv, EQUITY_L.csv, symbolchange.csv")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "data"))
    ap.add_argument("--manual", default=os.path.join(os.path.dirname(__file__), "data", "nifty100_manual_events.csv"))
    ap.add_argument("--today", required=True, help="date the constituent lists were downloaded, YYYY-MM-DD")
    ap.add_argument("--start", default=None, help="first month to emit (default: earliest consistent date)")
    a = ap.parse_args()
    rows, summary = build(a.prs, a.refs, a.out, a.today, a.manual, a.start)
    json.dump(summary, open(os.path.join(a.out, "nifty100_membership_build.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("dedupe_log", "n100_mismatches")}, indent=1, default=str))
    print("n100 mismatches:", len(summary["n100_mismatches"]), "| dedupe log entries:", len(summary["dedupe_log"]))


if __name__ == "__main__":
    main()
