"""
Two engines on one journal write rows that are indistinguishable from each
other afterwards — same kinds, same wording, same shape. That is how 119
rows from a test backend ended up in the live journal on 2026-09-22 and
forced a disclaimer into the research post-mortem. Issue #70.

These cover the guard itself: one owner at a time, a dead owner's lock is
stale rather than permanent, and releasing never touches someone else's.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import engine_lock


def test_acquire_then_second_process_is_refused(tmp_path):
    db = tmp_path / "j.db"
    engine_lock.acquire(db, pid=os.getpid())

    with pytest.raises(engine_lock.EngineAlreadyRunning) as exc:
        engine_lock.acquire(db, pid=os.getpid() + 1)   # a different live pid

    assert "already writing" in str(exc.value)
    assert "SAHAB_DB_PATH" in str(exc.value)          # tells you the way out


def test_reacquiring_our_own_lock_is_a_noop(tmp_path):
    db = tmp_path / "j.db"
    engine_lock.acquire(db, pid=os.getpid())
    engine_lock.acquire(db, pid=os.getpid())          # must not raise
    assert engine_lock.read_owner(db)["pid"] == os.getpid()


def test_a_dead_owners_lock_is_stale_not_permanent(tmp_path):
    """A crash or hard kill must not wedge the engine out of its own
    journal — otherwise the fix for #70 becomes a worse outage."""
    db = tmp_path / "j.db"
    dead = _a_definitely_dead_pid()
    engine_lock.lock_path(db).write_text(json.dumps({"pid": dead, "started_at": "x"}))

    assert engine_lock.read_owner(db) is None
    engine_lock.acquire(db, pid=os.getpid())          # takes it over
    assert engine_lock.read_owner(db)["pid"] == os.getpid()


def test_release_only_drops_our_own_lock(tmp_path):
    db = tmp_path / "j.db"
    engine_lock.acquire(db, pid=os.getpid())

    assert engine_lock.release(db, pid=os.getpid() + 1) is False
    assert engine_lock.lock_path(db).exists()

    assert engine_lock.release(db, pid=os.getpid()) is True
    assert not engine_lock.lock_path(db).exists()


def test_release_on_an_unlocked_journal_is_harmless(tmp_path):
    assert engine_lock.release(tmp_path / "nothing.db") is False


def _a_definitely_dead_pid():
    """Spawn a process, wait for it to exit, and reuse its pid. Beats
    guessing a number that might belong to something real."""
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


# ---- DB_PATH override (issue #70) ------------------------------------------
#
# database.DB_PATH is resolved at import time, so this runs in a subprocess
# rather than reloading the module under the conftest fixture that is already
# monkeypatching DB_PATH for every other test.

def _db_path_with_env(env_value):
    env = dict(os.environ)
    env.pop("SAHAB_DB_PATH", None)
    if env_value is not None:
        env["SAHAB_DB_PATH"] = env_value
    out = subprocess.run(
        [sys.executable, "-c", "import database; print(database.DB_PATH)"],
        cwd=str(Path(__file__).parent.parent), env=env,
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def test_db_path_defaults_to_the_real_journal():
    assert _db_path_with_env(None).endswith("backend/data/sahab_journal.db")


def test_db_path_follows_the_environment_variable(tmp_path):
    target = tmp_path / "copy.db"
    assert _db_path_with_env(str(target)) == str(target)
