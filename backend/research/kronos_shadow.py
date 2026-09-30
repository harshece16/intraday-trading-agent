"""Forward shadow of research look L40: the same Kronos forecast, computed live
during a session for the day's list, written next to the scanner's side, and
never used for a decision. Pre-registration: docs/research/prereg-kronos-feature-ic.md,
the dated note of 2026-09-29.

What it does, each five minutes from FIRST to LAST:
  - reads the day's list and the scanner's rows from the running engine's API;
  - fetches 5-minute bars for those stocks (Kite when connected, else the delayed
    feed, recorded per row) and keeps only closed bars;
  - forecasts the next 12 bars from the last 512 closed bars, exactly as the look
    does (kronos_feature_ic.KronosForecaster, sample_count 3, CPU, 4 threads);
  - records f15, f30, f60 in bp with the scanner's side and score for the stock;
  - fills in the realised 15, 30 and 60-minute returns of earlier rows as the bars
    arrive, and keeps a running rank IC per horizon across the day's times.
At END it writes the day's summary. One day is an anecdote, not a test: the
day's numbers are recorded, nothing is concluded from them, and no threshold is
applied. Any test on the shadow record is pre-registered separately.

Nothing in the live path imports this (tests/test_research_splits.py). It reads the
engine over its API and Kite over data_provider; it writes only under data/.

From the run branch's backend/, with the research environment:
    KRONOS_MAIN_BACKEND=/Users/harshgupta/Projects/webapp/backend \\
    KRONOS_VENDOR=/Users/harshgupta/Projects/webapp/backend/research/kronos_vendor \\
    research/.kvenv/bin/python research/kronos_shadow.py run       # waits for FIRST, runs the day
    ...                                        research/kronos_shadow.py once      # one cycle now, to a test file
"""
import json
import os
import statistics as st
import sys
import time
import urllib.request
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
MAIN_BACKEND = os.environ.get("KRONOS_MAIN_BACKEND", BACKEND)
for p in (BACKEND, MAIN_BACKEND):
    if p not in sys.path:
        sys.path.insert(0, p)

FIRST, LAST, END = "09:45", "14:15", "15:36"   # Kite's 5-minute bars end at 15:10, so 14:15 is the last time with a 60-minute outcome
STEP_MINUTES = 5
LOOKBACK, PRED_LEN = 512, 12
SAMPLE_COUNT, DEVICE, THREADS = 3, "cpu", 4
HISTORY_PERIOD = "14d"            # calendar days of 5-minute bars: about nine sessions, over 512 bars
API = "http://127.0.0.1:8000"
OUT_DIR = os.path.join(MAIN_BACKEND, "data")
STAGE0 = os.path.join(os.path.dirname(BACKEND), "docs", "research", "data", "kronos_l40_stage0.json")


def write_json(path, obj):
    """Write to a temporary file and rename it into place, so a reader never sees a
    half-written file."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def api(path):
    with open(os.path.join(MAIN_BACKEND, ".dashboard_key.json")) as f:
        key = json.load(f)["key"]
    req = urllib.request.Request(API + path, headers={"X-Api-Key": key})
    return json.load(urllib.request.urlopen(req, timeout=60))


def reload_kite_token():
    """The engine's in-app login rewrites .kite_session.json each morning. A process
    started the night before must read it again. The token is never printed."""
    import config
    import data_provider
    path = os.path.join(MAIN_BACKEND, ".kite_session.json")
    if os.path.exists(path):
        with open(path) as f:
            token = json.load(f).get("access_token", "")
        if token and token != config.KITE_ACCESS_TOKEN:
            config.KITE_ACCESS_TOKEN = token
            data_provider.reset_kite_client()
    return data_provider.kite_data_active()


def revisions():
    with open(STAGE0) as f:
        s = json.load(f)["stage0"]["revisions"]
    return {repo: v["picked"][0] for repo, v in s.items() if repo != "moved_window"}


def now_ist():
    return datetime.now(IST)


def hhmm_list(first=FIRST, last=LAST, step=STEP_MINUTES):
    t = datetime.strptime(first, "%H:%M")
    end = datetime.strptime(last, "%H:%M")
    out = []
    while t <= end:
        out.append(t.strftime("%H:%M"))
        t += timedelta(minutes=step)
    return out


def sleep_until(hhmm, seconds_after=20, day=None):
    day = day or now_ist().date()
    target = datetime.combine(day, datetime.strptime(hhmm, "%H:%M").time(), tzinfo=IST) + timedelta(seconds=seconds_after)
    while True:
        gap = (target - now_ist()).total_seconds()
        if gap <= 0:
            return
        time.sleep(min(gap, 30))


def closed_windows(candles_by_symbol, hhmm):
    """{symbol: (window of LOOKBACK closed bars ending with the bar that closes at hhmm,
    delayed flag)}. A stock whose newest closed bar is not that bar is left out."""
    import data_provider
    from research import kronos_feature_ic as k
    start = (datetime.strptime(hhmm, "%H:%M") - timedelta(minutes=k.BAR_MINUTES)).strftime("%H:%M")
    out = {}
    for sym, candles in candles_by_symbol.items():
        bars = sorted(candles or [], key=lambda c: c["time"])
        bars = data_provider.closed_bars(bars, "5m")
        if len(bars) < LOOKBACK or bars[-1]["time"][11:16] != start:
            continue
        out[sym] = (bars[-LOOKBACK:], bool(bars[-1].get("delayed")))
    return out


def realise(rows, candles_by_symbol, date):
    """Fill in the realised targets of rows whose horizon has passed, from today's bars."""
    from research import kronos_feature_ic as k
    filled = 0
    for r in rows:
        if r.get("targets") and all(v is not None for v in r["targets"].values()):
            continue
        bars = k.by_session(sorted(candles_by_symbol.get(r["symbol"]) or [], key=lambda c: c["time"])).get(date)
        if not bars:
            continue
        import data_provider
        bars = data_provider.closed_bars(bars, "5m")
        i = k.decision_bar_index(bars, r["hhmm"])
        if i is None:
            continue
        r["targets"] = {name: k.target_bp(bars, i, kb) for name, kb in k.HORIZONS.items()}
        filled += 1
    return filled


def running_stats(rows):
    """Per time, per horizon: rank IC, partial IC given m60 and the quintile spread
    across the stocks that have a realised target; then mean and t across times."""
    from research import kronos_feature_ic as k
    out = {}
    for name in k.HORIZONS:
        per_time = OrderedDict()
        for hhmm in sorted({r["hhmm"] for r in rows}):
            trip = [(r["features"][name], r["targets"][name], r["m60"]) for r in rows
                    if r["hhmm"] == hhmm and r.get("targets") and r["targets"].get(name) is not None and r["m60"] is not None]
            if len(trip) >= 10:
                per_time[hhmm] = k.session_stats(trip)
        if per_time:
            summary = k.summarise(per_time)
            summary["times"] = summary.pop("sessions")
            out[name] = summary
    return out


def table(rows, hhmm, stats, note):
    lines = ["KRONOS SHADOW  %s  forecasts at %s  (%s)" % (rows[0]["date"] if rows else "", hhmm, note),
             "%-12s %-5s %5s   %7s %7s %7s   %s" % ("stock", "side", "score", "f15", "f30", "f60", "bars"),
             "-" * 64]
    for r in sorted((r for r in rows if r["hhmm"] == hhmm), key=lambda r: -(r["features"]["f60"] or 0)):
        f = r["features"]
        lines.append("%-12s %-5s %5s   %7.1f %7.1f %7.1f   %s" % (
            r["symbol"], (r["scanner"].get("side") or "")[:5], r["scanner"].get("score"), f["f15"], f["f30"], f["f60"],
            "delayed" if r["bars_delayed"] else "live"))
    lines.append("")
    lines.append("forecast in bp of the last close: + means Kronos expects the price higher after 15 / 30 / 60 minutes")
    if stats:
        lines.append("")
        lines.append("running rank IC across times with realised outcomes (one day: an anecdote, not a test):")
        for name, s in stats.items():
            ic, sp = s["ic"], s["spread"]
            lines.append("  %s: times %d | IC %+.3f (t %.2f) | top-minus-bottom quintile %+.1f bp (t %.2f)" % (
                name, s["times"], ic["mean"] or 0, ic["t"] or 0, sp["mean"] or 0, sp["t"] or 0))
    return "\n".join(lines)


def cycle(fc, hhmm, rows, date, out_json, latest_txt):
    import data_provider
    from research import kronos_feature_ic as k
    live = reload_kite_token()
    sc = api("/api/scanner")
    symbols = list(sc.get("active") or [])
    scanner_rows = {r["symbol"]: r for r in sc.get("rows", [])}
    candles = data_provider.get_candles_batch(symbols, "5m", HISTORY_PERIOD) if symbols else {}
    windows = closed_windows(candles, hhmm)
    if not windows:
        time.sleep(20)                                        # the bar can land a few seconds late
        candles = data_provider.get_candles_batch(symbols, "5m", HISTORY_PERIOD) if symbols else {}
        windows = closed_windows(candles, hhmm)
    syms = sorted(windows)
    preds = fc.forecast_batch([windows[s][0] for s in syms]) if syms else []
    computed = now_ist().isoformat()
    for s, pc in zip(syms, preds):
        w, delayed = windows[s]
        c0 = w[-1]["close"]
        row = scanner_rows.get(s, {})
        rows.append({"date": date, "hhmm": hhmm, "symbol": s, "computed_at": computed, "c0": c0, "pred_close": pc,
                     "features": k.forecast_features(pc, c0), "m60": k.m60_bp(w, len(w) - 1), "bars_delayed": delayed,
                     "kite_active": live,
                     # "side" is the old score's stronger side; since README section 115 the
                     # scanner row carries it as score_side and leaves its own side empty.
                     "scanner": {**{kk: row.get(kk) for kk in ("score", "final_score", "ltp", "gap_pct", "rvol", "feed")},
                                 "side": row.get("score_side") or row.get("side")},
                     "targets": None})
    filled = realise(rows, candles, date)
    stats = running_stats(rows)
    note = "%d stocks forecast, %d skipped, %d outcomes filled" % (len(syms), len(symbols) - len(syms), filled)
    write_json(out_json, {"date": date, "sample_count": SAMPLE_COUNT, "device": DEVICE, "rows": rows, "running": stats,
                          "updated": computed})
    with open(latest_txt + ".tmp", "w") as f:
        f.write(table(rows, hhmm, stats, note) + "\n")
    os.replace(latest_txt + ".tmp", latest_txt)
    print("%s %s: %s" % (computed[11:19], hhmm, note), flush=True)


def build_forecaster():
    import torch
    torch.set_num_threads(THREADS)
    from research import kronos_feature_ic as k
    revs = revisions()
    return k.KronosForecaster(revs[k.MODEL_REPO], revs[k.TOKENIZER_REPO], SAMPLE_COUNT, device=DEVICE)


def summary(rows, date, out_json):
    from research import kronos_feature_ic as k
    stats = running_stats(rows)
    by_feed = {"live": sum(1 for r in rows if not r["bars_delayed"]), "delayed": sum(1 for r in rows if r["bars_delayed"])}
    agree = {}
    for name in k.HORIZONS:
        pairs = [(r["features"][name], r["scanner"].get("side")) for r in rows if r["scanner"].get("side") in ("LONG", "SHORT")]
        if pairs:
            agree[name] = round(sum(1 for f, s in pairs if (f > 0) == (s == "LONG")) / len(pairs), 3)
    out = {"date": date, "rows": len(rows), "stocks": len({r["symbol"] for r in rows}), "times": len({r["hhmm"] for r in rows}),
           "bars": by_feed, "sample_count": SAMPLE_COUNT, "device": DEVICE,
           "share_of_forecasts_on_the_scanners_side": agree, "stats": stats,
           "note": "One session. Recorded, not concluded from; no threshold applies. See the dated note of 2026-09-29 in the pre-registration."}
    write_json(out_json, out)
    return out


def session_day():
    """The session this run belongs to: today, or the next trading day when today's
    session is over, a weekend or a holiday. A process started the night before
    must not take the night for a session."""
    import holidays
    now = now_ist()
    day = now.date()
    if now.strftime("%H:%M") >= END or day.weekday() >= 5 or holidays.is_holiday(day):
        day = holidays.next_trading_day(day)
    return day


def run(once=False):
    day = now_ist().date() if once else session_day()
    date = day.isoformat()
    tag = "test_" if once else ""
    out_json = os.path.join(OUT_DIR, "kronos_shadow_%s%s.json" % (tag, date))
    latest_txt = os.path.join(OUT_DIR, "kronos_shadow_latest.txt")
    rows = []
    if os.path.exists(out_json) and not once:
        with open(out_json) as f:
            rows = json.load(f).get("rows", [])
        print("resuming with %d rows from %s" % (len(rows), out_json), flush=True)
    fc = build_forecaster()
    print("forecaster ready (%s, %d threads, sample_count %d)" % (DEVICE, THREADS, SAMPLE_COUNT), flush=True)
    if once:
        # after the close every bar is closed: the last bar of the day is the decision bar
        sc = api("/api/scanner")
        import data_provider
        cand = data_provider.get_candles_batch(list(sc.get("active") or [])[:5], "5m", HISTORY_PERIOD)
        last = max(c[-1]["time"][11:16] for c in cand.values() if c)
        hhmm = (datetime.strptime(last, "%H:%M") + timedelta(minutes=5)).strftime("%H:%M")
        cycle(fc, hhmm, rows, date, out_json, latest_txt)
        print(open(latest_txt).read())
        return
    times = hhmm_list()
    done = {r["hhmm"] for r in rows}
    print("session %s: %d forecast times from %s to %s" % (date, len(times), times[0], times[-1]), flush=True)
    for hhmm in times:
        if hhmm in done:
            continue
        sleep_until(hhmm, day=day)
        try:
            cycle(fc, hhmm, rows, date, out_json, latest_txt)
        except Exception as exc:                     # one bad cycle must not end the day
            print("%s: cycle failed: %s" % (hhmm, exc), flush=True)
    sleep_until(END, seconds_after=0, day=day)
    try:
        import data_provider
        symbols = sorted({r["symbol"] for r in rows})
        candles = data_provider.get_candles_batch(symbols, "5m", "3d") if symbols else {}
        realise(rows, candles, date)
        write_json(out_json, {"date": date, "sample_count": SAMPLE_COUNT, "device": DEVICE, "rows": rows,
                              "running": running_stats(rows), "updated": now_ist().isoformat()})
    except Exception as exc:
        print("end of day: outcomes failed: %s" % exc, flush=True)
    out = summary(rows, date, os.path.join(OUT_DIR, "kronos_shadow_%s_summary.json" % date))
    print(json.dumps({kk: out[kk] for kk in ("rows", "stocks", "times", "bars", "share_of_forecasts_on_the_scanners_side")}), flush=True)
    for name, s in out["stats"].items():
        print("%s: IC %+.3f (t %.2f) over %d times; quintile spread %+.1f bp (t %.2f)" % (
            name, s["ic"]["mean"] or 0, s["ic"]["t"] or 0, s["times"], s["spread"]["mean"] or 0, s["spread"]["t"] or 0), flush=True)


if __name__ == "__main__":
    run(once=(len(sys.argv) > 1 and sys.argv[1] == "once"))
