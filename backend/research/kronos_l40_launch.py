"""Run harness for research look L40. The look is kronos_feature_ic.py, unchanged.

Pre-registration: docs/research/prereg-kronos-feature-ic.md, amendment 3, which was
committed before this file ran anything. This file decides only four things the
look's own script leaves to whoever runs it:

  1. where the candle cache is read from (KRONOS_CANDLE_DB), so the run can happen
     in a worktree while the cache stays in the main checkout;
  2. the device (cpu, or KRONOS_DEVICE for a replication on another machine) and the
     thread count (4), fixed for the whole run;
  3. that the sample_count chosen by the stage-0-only run is the one of record:
     the full run repeats the timing, and halts if its own choice differs;
  4. when the run is paused. It is stopped from 08:30 to 15:45 IST on trading days
     so it cannot slow the engine, and continued after. A pause changes no forecast.

Nothing in the live path imports this (tests/test_research_splits.py). torch is
imported inside worker() only, so this module is testable without it.

From backend/, with the research environment:
    research/.kvenv/bin/python -m research.kronos_l40_launch stage0
    research/.kvenv/bin/python -m research.kronos_l40_launch start     # detached, supervised
    research/.kvenv/bin/python -m research.kronos_l40_launch status
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
PAUSE_FROM, PAUSE_TO = "08:30", "15:45"
DEVICE = os.environ.get("KRONOS_DEVICE", "cpu")     # the run of record is cpu (amendment 3); a PC replication may set cuda
THREADS = 4
NICE = 10
POLL_SECONDS = 20

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
DATA_OUT = os.path.join(os.path.dirname(BACKEND), "docs", "research", "data")
STAGE0_OUT = os.path.join(DATA_OUT, "kronos_l40_stage0.json")
LOG = os.path.join(HERE, "kronos_l40_run.log")
DONE = os.path.join(HERE, "kronos_l40_run.done")
PIDFILE = os.path.join(HERE, "kronos_l40_run.pid")


def paused_at(now, is_holiday):
    """True inside the pause window of a trading day. `now` is an aware datetime."""
    now = now.astimezone(IST)
    if now.weekday() >= 5 or is_holiday(now):
        return False
    return PAUSE_FROM <= now.strftime("%H:%M") < PAUSE_TO


def sample_count_of_record(path=STAGE0_OUT):
    """The sample_count the stage-0-only run chose. None if that run is not on file
    or did not finish."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        obj = json.load(f)
    if obj.get("status") != "STAGE0_DONE":
        return None
    return obj["stage0"]["timing"]["sample_count_chosen"]


def checked_timing(inner, want, halt):
    """Wrap the look's timing step: the choice must equal the one of record."""
    def run(stage0, *a, **kw):
        chosen = inner(stage0, *a, **kw)
        stage0["timing"]["sample_count_of_record"] = want
        if chosen != want:
            halt(stage0, 4, "this run's timing chose sample_count %s; the stage-0 run of record chose %s"
                 % (chosen, want))
        return chosen
    return run


def environment(vendor, candle_db):
    import platform
    out = {"python": sys.version.split()[0], "machine": platform.machine(), "device": DEVICE,
           "threads": THREADS, "nice": NICE, "candle_db": candle_db,
           "pause_window_ist": [PAUSE_FROM, PAUSE_TO]}
    for name in ("torch", "numpy", "pandas", "einops", "huggingface_hub", "safetensors"):
        try:
            out[name] = __import__(name).__version__
        except Exception as exc:                      # recorded, not fatal
            out[name] = "unavailable: %s" % exc
    try:
        out["vendor_commit"] = subprocess.run(["git", "-C", vendor, "rev-parse", "HEAD"], capture_output=True,
                                              text=True).stdout.strip()
        out["look_commit"] = subprocess.run(["git", "-C", BACKEND, "rev-parse", "HEAD"], capture_output=True,
                                            text=True).stdout.strip()
        out["look_script_dirty"] = bool(subprocess.run(
            ["git", "-C", BACKEND, "status", "--porcelain", "research/kronos_feature_ic.py",
             "research/kronos_l40_launch.py"], capture_output=True, text=True).stdout.strip())
    except Exception as exc:
        out["vendor_commit"] = "unavailable: %s" % exc
    return out


def worker(mode):
    """The run itself, in this process. mode is 'stage0' or 'run'."""
    from pathlib import Path
    if hasattr(os, "nice"):                    # not on Windows
        os.nice(NICE)
    if BACKEND not in sys.path:
        sys.path.insert(0, BACKEND)
    import kite_history
    candle_db = os.environ.get("KRONOS_CANDLE_DB") or str(kite_history.DB_PATH)
    kite_history.DB_PATH = Path(candle_db)
    if not kite_history.DB_PATH.exists():
        sys.exit("no candle cache at %s" % candle_db)
    import torch
    torch.set_num_threads(THREADS)
    from research import kronos_feature_ic as k

    env = environment(k.VENDOR, candle_db)
    write = k._write

    def write_with_harness(obj):
        obj["harness"] = env
        write(obj)
    k._write = write_with_harness

    if mode == "run":
        want = sample_count_of_record()
        if want is None:
            sys.exit("no finished stage-0 run on file at %s; run stage0 first" % STAGE0_OUT)
        k.stage0_timing = checked_timing(k.stage0_timing, want, k.halt)
    argv = ["--device", DEVICE] + (["--stage0-only"] if mode == "stage0" else [])
    sys.argv = [sys.argv[0]] + argv
    k.main(argv)
    if mode == "stage0":
        shutil.copyfile(k.OUT, STAGE0_OUT)
        print("stage 0 of record saved to", STAGE0_OUT)


def _log(text):
    line = "%s %s" % (datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"), text)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def supervise():
    """Run the worker as a child, stop it inside the pause window, continue it after."""
    sys.path.insert(0, BACKEND)
    import holidays
    out = open(LOG, "a")
    child = subprocess.Popen([sys.executable, "-m", "research.kronos_l40_launch", "worker", "run"], cwd=BACKEND,
                             stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    with open(PIDFILE, "w") as f:
        json.dump({"supervisor": os.getpid(), "worker": child.pid, "started": datetime.now(IST).isoformat()}, f)
    awake = None
    if shutil.which("caffeinate"):
        awake = subprocess.Popen(["caffeinate", "-i", "-w", str(child.pid)])
    _log("supervisor %d started worker %d" % (os.getpid(), child.pid))
    stopped, pauses = False, []
    while child.poll() is None:
        want = paused_at(datetime.now(IST), holidays.is_holiday)
        if want and not stopped:
            os.kill(child.pid, signal.SIGSTOP)
            stopped = True
            pauses.append({"stopped": datetime.now(IST).isoformat()})
            _log("paused for the session")
        elif stopped and not want:
            os.kill(child.pid, signal.SIGCONT)
            stopped = False
            pauses[-1]["continued"] = datetime.now(IST).isoformat()
            _log("continued after the session")
        time.sleep(POLL_SECONDS)
    if awake and awake.poll() is None:
        awake.terminate()
    with open(DONE, "w") as f:
        json.dump({"exit_code": child.returncode, "finished": datetime.now(IST).isoformat(), "pauses": pauses}, f, indent=1)
    _log("worker exited with code %s" % child.returncode)


def start():
    """Start the supervisor in a session of its own, so it outlives this shell."""
    if os.path.exists(DONE):
        os.remove(DONE)
    out = open(LOG, "a")
    p = subprocess.Popen([sys.executable, "-m", "research.kronos_l40_launch", "supervise"], cwd=BACKEND, stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True,
                         env=dict(os.environ))
    print("supervisor pid", p.pid)


def status():
    info = {"done": None, "pids": None, "rows": 0}
    if os.path.exists(DONE):
        with open(DONE) as f:
            info["done"] = json.load(f)
    if os.path.exists(PIDFILE):
        with open(PIDFILE) as f:
            info["pids"] = json.load(f)
    rows = os.path.join(HERE, "kronos_rows_l40.jsonl")
    if os.path.exists(rows):
        with open(rows) as f:
            info["rows"] = sum(1 for _ in f)
    print(json.dumps(info, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["stage0", "start", "supervise", "worker", "status"])
    ap.add_argument("mode", nargs="?", default="run", choices=["stage0", "run"])
    args = ap.parse_args(argv)
    if args.command == "stage0":
        worker("stage0")
    elif args.command == "worker":
        worker(args.mode)
    elif args.command == "supervise":
        supervise()
    elif args.command == "start":
        start()
    else:
        status()


if __name__ == "__main__":
    main()
