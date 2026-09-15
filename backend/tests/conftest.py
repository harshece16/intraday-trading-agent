"""
Test isolation for database.py.

Without this, tests ran against the SAME sqlite file the live engine
writes to (database.DB_PATH is a fixed path). state.log() calls
database.record_activity() unconditionally, so anything that logs
through a real AppState/TradingEngine (e.g. test_entries_today_rollback.py's
_try_enter() calls) wrote fake TESTCO/TESTCO3 rows straight into the
production activity table — the same one the Live Log UI reads from.

This fixture points database.DB_PATH at a throwaway file per test and
resets the thread-local connection cache so _conn() actually reconnects
to it, instead of reusing whatever connection an earlier test opened.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import database


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test_journal.db")
    database._local.conn = None
    yield
    conn = getattr(database._local, "conn", None)
    if conn is not None:
        conn.close()
        database._local.conn = None
