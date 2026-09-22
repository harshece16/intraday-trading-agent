"""
Single-writer guard for the journal.

Two TradingEngines pointed at the same sqlite file both scan, both seed a
watchlist and both write activity — and after the fact their rows are
indistinguishable from each other, because they have the same shape, kinds
and wording. That happened on 2026-09-22: a second backend started for
testing wrote 119 rows (18 activity, 1 scan, 100 scan_rows) into the live
journal, and the research post-mortem written from that journal had to
carry a disclaimer. Issue #70.

The lock is advisory and deliberately simple: a JSON file next to the
database holding the owning pid. A lock whose pid is no longer alive is
stale and gets taken over, so a crash or a hard kill can't wedge the engine
out of its own journal permanently.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


class EngineAlreadyRunning(RuntimeError):
    """Raised when another live process already owns this journal."""


def lock_path(db_path) -> Path:
    return Path(str(db_path) + ".enginelock")


def _pid_alive(pid: int) -> bool:
    """signal 0 checks for existence without touching the process. EPERM
    means it exists and belongs to someone else — still alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def read_owner(db_path):
    """The live owner of this journal, or None if unlocked or stale."""
    path = lock_path(db_path)
    try:
        info = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    pid = info.get("pid")
    if not isinstance(pid, int) or not _pid_alive(pid):
        return None
    return info


def acquire(db_path, pid=None):
    """Claim this journal for `pid`. Raises EngineAlreadyRunning if another
    live process holds it. Re-acquiring our own lock is a no-op."""
    pid = os.getpid() if pid is None else pid
    owner = read_owner(db_path)
    if owner is not None and owner.get("pid") != pid:
        raise EngineAlreadyRunning(
            f"another Trader Sahab engine (pid {owner['pid']}, started "
            f"{owner.get('started_at')}) is already writing to {db_path}. "
            f"Two engines on one journal corrupt the research evidence base — "
            f"set SAHAB_DB_PATH to a copy to run a second instance."
        )
    path = lock_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "pid": pid,
        "db_path": str(db_path),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }))
    return path


def release(db_path, pid=None):
    """Drop our own lock. Never removes a lock another process owns."""
    pid = os.getpid() if pid is None else pid
    path = lock_path(db_path)
    try:
        info = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    if info.get("pid") != pid:
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return True
