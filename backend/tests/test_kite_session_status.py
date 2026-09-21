"""The dashboard used to report "Kite connected" from `bool(access_token)`,
which stays true for days after Zerodha has invalidated the session. These
tests pin the replacement: connected means the session should actually work.

The bug that motivated them: a token generated 2026-09-19 21:34 UTC still
reported connected:true on 2026-09-21, two 06:00 IST cutoffs later, while
every Kite call was failing.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from kiteconnect.exceptions import TokenException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import data_provider  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def kite_env(monkeypatch):
    """A configured, freshly-logged-in Kite session, with the rejected-token
    flag cleared so each test starts from the same place."""
    monkeypatch.setattr(config, "KITE_API_KEY", "key", raising=False)
    monkeypatch.setattr(config, "KITE_API_SECRET", "secret", raising=False)
    monkeypatch.setattr(config, "KITE_ACCESS_TOKEN", "token", raising=False)
    monkeypatch.setattr(config, "KITE_REDIRECT_URL", "http://127.0.0.1:8000/kite/callback", raising=False)
    monkeypatch.setattr(data_provider, "_kite_rejected_token", None, raising=False)
    monkeypatch.setattr(config, "USE_KITE_DATA", True, raising=False)
    # Generated a minute ago, so it is inside its life whenever the suite runs.
    monkeypatch.setattr(config, "KITE_SESSION_GENERATED_AT",
                        (datetime.now(IST) - timedelta(minutes=1)).isoformat(), raising=False)
    return monkeypatch


# --- expiry arithmetic -------------------------------------------------


def test_expiry_is_the_next_6am_ist_not_24_hours_later(kite_env):
    """The bug in one line: a token made at 21:34 dies the next morning, not
    the following evening."""
    made = datetime(2026, 9, 19, 21, 34, tzinfo=IST)
    expiry = data_provider.kite_token_expires_at(made.isoformat())
    assert expiry == datetime(2026, 9, 20, 6, 0, tzinfo=IST)
    assert expiry - made < timedelta(hours=9)


def test_a_token_made_just_after_6am_lives_almost_a_full_day(kite_env):
    made = datetime(2026, 9, 19, 6, 30, tzinfo=IST)
    assert data_provider.kite_token_expires_at(made.isoformat()) == datetime(2026, 9, 20, 6, 0, tzinfo=IST)


def test_a_token_made_just_before_6am_dies_within_the_hour(kite_env):
    made = datetime(2026, 9, 19, 5, 30, tzinfo=IST)
    assert data_provider.kite_token_expires_at(made.isoformat()) == datetime(2026, 9, 19, 6, 0, tzinfo=IST)


def test_utc_timestamps_are_converted_before_the_cutoff_is_applied(kite_env):
    """save_kite_session() writes UTC. 2026-09-19T21:34Z is 03:04 IST on the
    20th, so it dies at 06:00 IST that same morning — under three hours later.
    Reading it as if it were IST would give an extra day of false confidence.
    """
    expiry = data_provider.kite_token_expires_at("2026-09-19T21:34:50.142346+00:00")
    assert expiry == datetime(2026, 9, 20, 6, 0, tzinfo=IST)


def test_unparseable_and_missing_timestamps_return_none(kite_env):
    assert data_provider.kite_token_expires_at("") is None
    assert data_provider.kite_token_expires_at(None) is None
    assert data_provider.kite_token_expires_at("not a timestamp") is None


# --- kite_session_live() -----------------------------------------------


def test_fresh_session_is_live(kite_env):
    assert data_provider.kite_session_live() is True


def test_expired_session_is_not_live(kite_env):
    kite_env.setattr(config, "KITE_SESSION_GENERATED_AT",
                     (datetime.now(IST) - timedelta(days=3)).isoformat(), raising=False)
    assert data_provider.kite_session_live() is False


def test_the_reported_regression_case_is_not_live(kite_env):
    """The exact value the running backend held when the bug was found."""
    kite_env.setattr(config, "KITE_SESSION_GENERATED_AT",
                     "2026-09-19T21:34:50.142346+00:00", raising=False)
    assert data_provider.kite_session_live() is False
    assert data_provider.kite_session_status()["state"] == "expired"


def test_a_rejected_token_is_not_live_even_when_the_clock_says_fresh(kite_env):
    data_provider.mark_kite_token_rejected()
    assert data_provider.kite_token_rejected() is True
    assert data_provider.kite_session_live() is False


def test_a_rejection_of_a_different_token_does_not_taint_the_new_one(kite_env):
    """Reconnecting must clear the rejection: the flag stores the token that
    failed, so a new token is judged on its own."""
    data_provider.mark_kite_token_rejected()
    kite_env.setattr(config, "KITE_ACCESS_TOKEN", "a-fresh-token", raising=False)
    assert data_provider.kite_token_rejected() is False
    assert data_provider.kite_session_live() is True


def test_no_token_is_not_live(kite_env):
    kite_env.setattr(config, "KITE_ACCESS_TOKEN", "", raising=False)
    assert data_provider.kite_session_live() is False


def test_env_supplied_token_without_a_timestamp_is_trusted(kite_env):
    """A token exported as KITE_ACCESS_TOKEN has no generated_at to age it
    against; refusing it would break the documented env-var path."""
    kite_env.setattr(config, "KITE_SESSION_GENERATED_AT", None, raising=False)
    assert data_provider.kite_session_live() is True


# --- kite_session_status() ---------------------------------------------


def test_status_of_a_working_session(kite_env):
    s = data_provider.kite_session_status()
    assert s["state"] == "connected"
    assert s["connected"] is True
    assert s["has_token"] is True
    assert s["token_rejected"] is False
    assert s["seconds_until_expiry"] > 0
    assert "Live prices" in s["reason"]


def test_status_distinguishes_never_configured_from_logged_out(kite_env):
    kite_env.setattr(config, "KITE_ACCESS_TOKEN", "", raising=False)
    assert data_provider.kite_session_status()["state"] == "disconnected"

    kite_env.setattr(config, "KITE_API_KEY", "", raising=False)
    kite_env.setattr(config, "KITE_API_SECRET", "", raising=False)
    assert data_provider.kite_session_status()["state"] == "not_configured"


def test_every_state_carries_a_reason_a_person_can_act_on(kite_env):
    """The point of the change: never a bare boolean."""
    cases = []
    cases.append(data_provider.kite_session_status())
    kite_env.setattr(config, "KITE_SESSION_GENERATED_AT",
                     (datetime.now(IST) - timedelta(days=3)).isoformat(), raising=False)
    cases.append(data_provider.kite_session_status())
    kite_env.setattr(config, "KITE_ACCESS_TOKEN", "", raising=False)
    cases.append(data_provider.kite_session_status())
    kite_env.setattr(config, "KITE_API_KEY", "", raising=False)
    cases.append(data_provider.kite_session_status())
    for s in cases:
        assert s["reason"] and len(s["reason"]) > 20, s
        assert s["state"] in {"connected", "disconnected", "expired", "not_configured", "error"}


def test_expired_session_never_reports_live_data(kite_env):
    kite_env.setattr(config, "KITE_SESSION_GENERATED_AT",
                     (datetime.now(IST) - timedelta(days=3)).isoformat(), raising=False)
    s = data_provider.kite_session_status()
    assert s["using_live_data"] is False


def test_status_does_not_probe_unless_asked(kite_env):
    def explode():
        raise AssertionError("the 15-second poll must not hit Kite's API")

    kite_env.setattr(data_provider, "_get_kite", explode, raising=False)
    assert data_provider.kite_session_status()["probed"] is False


def test_probe_downgrades_a_clock_fresh_session_that_kite_rejects(kite_env):
    """The case the clock cannot see: revoked from Zerodha's side."""
    class Rejecting:
        def profile(self):
            raise TokenException("Invalid `api_key` or `access_token`.")

    kite_env.setattr(data_provider, "_get_kite", lambda: Rejecting(), raising=False)
    s = data_provider.kite_session_status(probe=True)
    assert s["probed"] is True
    assert s["connected"] is False
    assert s["state"] == "expired"
    assert s["token_rejected"] is True
    # And the rejection sticks, so later un-probed calls agree.
    assert data_provider.kite_session_live() is False


def test_probe_reports_a_network_failure_as_error_not_as_expired(kite_env):
    """A flaky connection is not a dead token, and telling the user to
    reconnect would send them round a login loop that cannot help."""
    class Unreachable:
        def profile(self):
            raise OSError("Connection refused")

    kite_env.setattr(data_provider, "_get_kite", lambda: Unreachable(), raising=False)
    s = data_provider.kite_session_status(probe=True)
    assert s["state"] == "error"
    assert s["connected"] is False
    assert s["token_rejected"] is False
    assert data_provider.kite_session_live() is True  # the token itself is untouched


def test_probe_gives_up_on_a_hanging_kite_without_hanging_the_request(kite_env):
    """An unreachable Kite must not hold the dashboard response open for the
    socket's own timeout — and a slow network is not a dead token."""
    import time as _time

    class Hanging:
        def profile(self):
            _time.sleep(30)

    kite_env.setattr(data_provider, "_get_kite", lambda: Hanging(), raising=False)
    kite_env.setattr(data_provider, "KITE_PROBE_TIMEOUT_SECONDS", 0.2, raising=False)
    started = _time.monotonic()
    s = data_provider.kite_session_status(probe=True)
    elapsed = _time.monotonic() - started

    assert elapsed < 5, f"probe blocked for {elapsed:.1f}s"
    assert s["state"] == "error"
    assert s["token_rejected"] is False
    assert "didn't answer" in s["reason"]
    assert data_provider.kite_session_live() is True  # the token is untouched


def test_probe_confirms_a_working_session(kite_env):
    class Fine:
        def profile(self):
            return {"user_id": "AB1234"}

    kite_env.setattr(data_provider, "_get_kite", lambda: Fine(), raising=False)
    s = data_provider.kite_session_status(probe=True)
    assert s["probed"] is True
    assert s["connected"] is True
    assert s["state"] == "connected"


def test_probe_is_skipped_when_the_clock_already_says_expired(kite_env):
    """No point spending an API call to confirm what the cutoff settles."""
    def explode():
        raise AssertionError("should not probe an already-expired session")

    kite_env.setattr(config, "KITE_SESSION_GENERATED_AT",
                     (datetime.now(IST) - timedelta(days=3)).isoformat(), raising=False)
    kite_env.setattr(data_provider, "_get_kite", explode, raising=False)
    s = data_provider.kite_session_status(probe=True)
    assert s["probed"] is False
    assert s["state"] == "expired"


# --- the login round trip ----------------------------------------------
#
# A Kite login is a browser round trip and Zerodha redirects to the URL
# registered in the Kite Connect app, not one we choose. When that URL does
# not reach this backend the round trip never completes and nothing in the app
# hears about it — clicking Connect Kite simply appears to do nothing. That
# happened for real on 2026-09-21: the tunnel the registered URL named was
# offline, and two request tokens were burned before anyone could tell.


@pytest.fixture
def logged_out(kite_env):
    kite_env.setattr(config, "KITE_ACCESS_TOKEN", "", raising=False)
    kite_env.setattr(data_provider, "_kite_login_started_at", None, raising=False)
    kite_env.setattr(data_provider, "_kite_callback_at", None, raising=False)
    return kite_env


def test_a_login_never_started_is_not_stalled(logged_out):
    assert data_provider.kite_login_stalled() is False
    assert data_provider.kite_session_status()["login_stalled"] is False


def test_a_login_just_started_is_not_yet_stalled(logged_out):
    data_provider.note_kite_login_started()
    assert data_provider.kite_login_stalled() is False


def test_a_login_that_never_returned_is_stalled(logged_out):
    logged_out.setattr(data_provider, "_kite_login_started_at",
                       datetime.now(IST) - timedelta(minutes=10), raising=False)
    assert data_provider.kite_login_stalled() is True
    s = data_provider.kite_session_status()
    assert s["login_stalled"] is True
    assert "never came back" in s["reason"]
    assert config.KITE_REDIRECT_URL in s["reason"]


def test_a_callback_clears_the_stall(logged_out):
    logged_out.setattr(data_provider, "_kite_login_started_at",
                       datetime.now(IST) - timedelta(minutes=10), raising=False)
    data_provider.note_kite_callback()
    assert data_provider.kite_login_stalled() is False


def test_an_old_callback_does_not_clear_a_newer_stalled_login(logged_out):
    """Yesterday's successful login must not mask today's broken one."""
    logged_out.setattr(data_provider, "_kite_callback_at",
                       datetime.now(IST) - timedelta(days=1), raising=False)
    logged_out.setattr(data_provider, "_kite_login_started_at",
                       datetime.now(IST) - timedelta(minutes=10), raising=False)
    assert data_provider.kite_login_stalled() is True


def test_a_connected_session_is_never_reported_as_stalled(kite_env):
    """If it works, the redirect obviously reached us — whatever the timers say."""
    kite_env.setattr(data_provider, "_kite_login_started_at",
                     datetime.now(IST) - timedelta(minutes=10), raising=False)
    kite_env.setattr(data_provider, "_kite_callback_at", None, raising=False)
    s = data_provider.kite_session_status()
    assert s["state"] == "connected"
    assert s["login_stalled"] is False


def test_status_always_reports_the_redirect_url(kite_env):
    """The half of the round trip the app cannot see from inside."""
    assert data_provider.kite_session_status()["redirect_url"] == config.KITE_REDIRECT_URL
