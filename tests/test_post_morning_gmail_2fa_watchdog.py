import io
import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Portable path resolution: resolve repo root relative to this test file
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "deploy" / "hermes-home" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import post_morning_gmail_2fa_watchdog as wd


def test_log_telemetry_metric(capsys):
    metric = wd.log_telemetry_metric("test_event", {"key": "val", "num": 42})
    assert metric["event"] == "test_event"
    assert metric["data"] == {"key": "val", "num": 42}
    assert "timestamp" in metric
    assert "pid" in metric

    captured = capsys.readouterr()
    assert "[TELEMETRY_METRIC]" in captured.err
    # Parse the emitted JSON
    json_part = captured.err.split("[TELEMETRY_METRIC]")[1].strip()
    parsed = json.loads(json_part)
    assert parsed["event"] == "test_event"
    assert parsed["data"]["num"] == 42


def test_save_state_results(tmp_path):
    mock_state_file = tmp_path / "test_state.json"
    with patch.object(wd, "STATE_FILE", mock_state_file), \
         patch.object(wd, "STATE_DIR", tmp_path):
        wd.save_state_results(
            success_list=["acc1@gmail.com (KEY1)"],
            fail_list=["acc2@gmail.com: ERROR"],
            pending_list=["acc3@gmail.com: PENDING_GPM_LOGIN_NO_SESSION"]
        )

    assert mock_state_file.exists()
    data = json.loads(mock_state_file.read_text(encoding="utf-8"))
    assert data["success"] == ["acc1@gmail.com (KEY1)"]
    assert data["failed"] == ["acc2@gmail.com: ERROR"]
    assert data["pending"] == ["acc3@gmail.com: PENDING_GPM_LOGIN_NO_SESSION"]
    assert "last_run_date" in data
    assert "updated_at" in data


def test_report_suppressed_when_only_pending(capsys, tmp_path):
    candidates = [{
        "id": "pid-1",
        "name": "M01 - test@gmail.com",
        "email": "test@gmail.com",
        "machine": 1,
        "pwd": "password123",
        "2fa_secret": "",
        "group_id": 10,
        "profile_path": "prof1",
        "google_session_verified": False,
    }]

    with patch.object(wd, "get_gpm_candidates", return_value=candidates), \
         patch.object(wd, "save_state_results") as mock_save, \
         patch.object(wd, "ProcessLock") as mock_lock_cls, \
         patch.object(wd, "log_telemetry_metric") as mock_telemetry, \
         patch.object(wd, "setup_authenticator_for_profile", MagicMock()), \
         patch.object(wd, "_profile_has_google_session", return_value=False), \
         patch.object(sys, "argv", ["post_morning_gmail_2fa_watchdog.py", "--force"]):

        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock_cls.return_value = mock_lock

        rc = wd.main()
        assert rc == 0

    captured = capsys.readouterr()
    # Suppressed stdout: silent watchdog when no success and no fail
    assert captured.out.strip() == ""

    # State results still persisted
    mock_save.assert_called_once()
    args, _ = mock_save.call_args
    assert args[0] == []  # success_list
    assert args[1] == []  # fail_list
    assert len(args[2]) == 1  # pending_list has 1 entry
    assert "PENDING_GPM_LOGIN_NO_SESSION" in args[2][0]

    # Telemetry emitted for pending and summary
    telemetry_events = [c[0][0] for c in mock_telemetry.call_args_list]
    assert "2fa_setup_pending" in telemetry_events
    assert "watchdog_execution_summary" in telemetry_events


def test_report_emitted_when_success(capsys):
    candidates = [{
        "id": "pid-1",
        "name": "M01 - test@gmail.com",
        "email": "test@gmail.com",
        "machine": 1,
        "pwd": "password123",
        "2fa_secret": "",
        "group_id": 10,
        "profile_path": "prof1",
        "google_session_verified": True,
    }]

    fake_setup = MagicMock(return_value={"status": "SUCCESS", "secret_key": "MOCKSECRET32CHARSXXXXXXXXXXXXXX"})

    with patch.object(wd, "get_gpm_candidates", return_value=candidates), \
         patch.object(wd, "save_state_results") as mock_save, \
         patch.object(wd, "ProcessLock") as mock_lock_cls, \
         patch.object(wd, "log_telemetry_metric") as mock_telemetry, \
         patch.object(wd, "setup_authenticator_for_profile", fake_setup), \
         patch.object(wd, "_profile_has_google_session", return_value=True), \
         patch.object(sys, "argv", ["post_morning_gmail_2fa_watchdog.py", "--force"]):

        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock_cls.return_value = mock_lock

        rc = wd.main()
        assert rc == 0

    captured = capsys.readouterr()
    assert "### [BÁO CÁO 2FA GMAIL QUA GPM PROFILE]" in captured.out
    assert "test@gmail.com (MOCKSECRET32CHARSXXXXXXXXXXXXXX)" in captured.out
    mock_save.assert_called_once()

    telemetry_events = [c[0][0] for c in mock_telemetry.call_args_list]
    assert "2fa_setup_success" in telemetry_events
    assert "watchdog_execution_summary" in telemetry_events


def test_report_emitted_when_failed(capsys):
    candidates = [{
        "id": "pid-1",
        "name": "M01 - test@gmail.com",
        "email": "test@gmail.com",
        "machine": 1,
        "pwd": "password123",
        "2fa_secret": "",
        "group_id": 10,
        "profile_path": "prof1",
        "google_session_verified": True,
    }]

    fake_setup = MagicMock(return_value={"status": "CDP_FAILED", "details": "CDP timeout after 6 retries"})

    with patch.object(wd, "get_gpm_candidates", return_value=candidates), \
         patch.object(wd, "save_state_results") as mock_save, \
         patch.object(wd, "ProcessLock") as mock_lock_cls, \
         patch.object(wd, "log_telemetry_metric") as mock_telemetry, \
         patch.object(wd, "setup_authenticator_for_profile", fake_setup), \
         patch.object(wd, "_profile_has_google_session", return_value=True), \
         patch.object(sys, "argv", ["post_morning_gmail_2fa_watchdog.py", "--force"]):

        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock_cls.return_value = mock_lock

        rc = wd.main()
        assert rc == 0

    captured = capsys.readouterr()
    assert "### [BÁO CÁO 2FA GMAIL QUA GPM PROFILE]" in captured.out
    assert "Cần lưu ý (1):" in captured.out
    assert "CDP_FAILED" in captured.out
    mock_save.assert_called_once()

    telemetry_events = [c[0][0] for c in mock_telemetry.call_args_list]
    assert "2fa_setup_failed" in telemetry_events
    assert "watchdog_execution_summary" in telemetry_events


def test_lock_released_on_unhandled_exception(tmp_path):
    mock_lock = MagicMock()
    mock_lock.acquire.return_value = True

    candidates = [{
        "id": "pid-crash",
        "name": "M01 - crash@gmail.com",
        "email": "crash@gmail.com",
        "machine": 1,
        "pwd": "password123",
        "2fa_secret": "",
        "group_id": 10,
        "profile_path": "prof1",
        "google_session_verified": True,
    }]

    # Simulate setup_authenticator_for_profile raising unexpected fatal error
    with patch.object(wd, "get_gpm_candidates", return_value=candidates), \
         patch.object(wd, "ProcessLock", return_value=mock_lock), \
         patch.object(wd, "setup_authenticator_for_profile", side_effect=RuntimeError("GPM process died")), \
         patch.object(wd, "_profile_has_google_session", return_value=True), \
         patch.object(sys, "argv", ["post_morning_gmail_2fa_watchdog.py", "--force"]):

        wd.main()

    # Invariant: lock MUST always be released in finally block
    mock_lock.release.assert_called_once()


def test_lock_not_acquired_exits_silently(capsys):
    mock_lock = MagicMock()
    mock_lock.acquire.return_value = False  # Lock held by another tick

    candidates = [{"id": "1", "name": "M01 - a@gmail.com", "email": "a@gmail.com", "machine": 1}]

    with patch.object(wd, "get_gpm_candidates", return_value=candidates), \
         patch.object(wd, "ProcessLock", return_value=mock_lock), \
         patch.object(sys, "argv", ["post_morning_gmail_2fa_watchdog.py", "--force"]):

        rc = wd.main()
        assert rc == 0

    captured = capsys.readouterr()
    # Silent watchdog: no stdout output when lock is active
    assert captured.out.strip() == ""


def test_profile_has_google_session_cookie_db(tmp_path):
    p_folder = tmp_path / "profile_test"
    cookies_dir = p_folder / "Default" / "Network"
    cookies_dir.mkdir(parents=True, exist_ok=True)
    db_file = cookies_dir / "Cookies"

    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("CREATE TABLE cookies (host_key TEXT, name TEXT)")
    cur.execute("INSERT INTO cookies VALUES ('.google.com', 'SID')")
    cur.execute("INSERT INTO cookies VALUES ('.google.com', 'SSID')")
    conn.commit()
    conn.close()

    assert wd._profile_has_google_session({"profile_path": str(p_folder)}) is True
    assert wd._profile_has_google_session({"google_session_verified": True}) is True
    assert wd._profile_has_google_session({"google_session_verified": False}) is False
