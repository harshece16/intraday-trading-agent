"""#161: credential files are owner-read/write only (0600). The dashboard key
and the Kite session are written that way from the first byte, and start-up
tightens any credential file other accounts can read. Every test works on
temporary files; the real ones are never read."""
import json
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import config


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


@pytest.fixture
def loose_umask():
    old = os.umask(0o022)       # the usual default: new files come out 0644
    yield
    os.umask(old)


def test_a_new_secret_file_is_0600(tmp_path, loose_umask):
    path = tmp_path / ".secret.json"
    config.write_secret_file(path, '{"key": "x"}')
    assert _mode(path) == 0o600
    assert json.loads(path.read_text()) == {"key": "x"}
    assert not (tmp_path / ".secret.json.tmp").exists()


def test_rewriting_a_0644_file_leaves_it_0600(tmp_path, loose_umask):
    path = tmp_path / ".secret.json"
    path.write_text("old")
    os.chmod(path, 0o644)
    config.write_secret_file(path, "new")
    assert _mode(path) == 0o600 and path.read_text() == "new"


def test_a_leftover_temporary_file_with_a_wide_mode_is_not_reused_as_is(tmp_path, loose_umask):
    path = tmp_path / ".secret.json"
    tmp = tmp_path / ".secret.json.tmp"
    tmp.write_text("stale")
    os.chmod(tmp, 0o666)
    config.write_secret_file(path, "new")
    assert _mode(path) == 0o600 and path.read_text() == "new"


def test_the_dashboard_key_file_is_created_0600(tmp_path, monkeypatch, loose_umask):
    path = tmp_path / ".dashboard_key.json"
    monkeypatch.setattr(config, "_KEY_FILE", path)
    monkeypatch.setattr(config, "DASHBOARD_API_KEY_IS_NEW", False)
    key = config._load_or_create_dashboard_key()
    assert _mode(path) == 0o600
    assert json.loads(path.read_text())["key"] == key and config.DASHBOARD_API_KEY_IS_NEW is True


def test_the_kite_session_file_is_written_0600(tmp_path, monkeypatch, loose_umask):
    path = tmp_path / ".kite_session.json"
    path.write_text("{}")
    os.chmod(path, 0o644)
    monkeypatch.setattr(config, "SESSION_FILE", path)
    monkeypatch.setattr(config, "KITE_API_KEY", "k")
    monkeypatch.setattr(config, "KITE_API_SECRET", "s")
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "")
    monkeypatch.setattr(config, "KITE_SESSION_GENERATED_AT", None)
    config.save_kite_session("test-token")
    assert _mode(path) == 0o600
    assert json.loads(path.read_text())["access_token"] == "test-token"
    assert config.KITE_ACCESS_TOKEN == "test-token"


def test_start_up_tightens_readable_files_and_names_only_those(tmp_path):
    loose, group, tight = tmp_path / ".a.json", tmp_path / ".b.json", tmp_path / ".c.json"
    for p, mode in ((loose, 0o644), (group, 0o640), (tight, 0o600)):
        p.write_text("secret-value")
        os.chmod(p, mode)
    missing = tmp_path / ".missing.json"
    changed = config.tighten_secret_files((loose, group, tight, missing))
    assert [_mode(p) for p in (loose, group, tight)] == [0o600, 0o600, 0o600]
    assert changed == [".a.json (644 -> 600)", ".b.json (640 -> 600)"]
    assert not missing.exists()
    assert all("secret-value" not in c for c in changed)


def test_every_credential_file_is_covered():
    names = {p.name for p in config.SECRET_FILES}
    assert names == {".dashboard_key.json", ".kite_session.json", ".typesafe_key.json", ".telegram.json"}
