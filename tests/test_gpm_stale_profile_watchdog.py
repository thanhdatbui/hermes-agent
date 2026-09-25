import os
import sys
import json
import sqlite3
import pytest
import requests
from datetime import datetime
from unittest.mock import MagicMock, patch
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import gpm_stale_profile_watchdog as watchdog


def test_is_gpm_chrome_process_protection():
    # Personal Chrome -> Must return False
    personal = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "--user-data-dir=C:\\Users\\Kibe\\AppData\\Local\\Google\\Chrome\\User Data"
    ]
    assert watchdog.is_gpm_chrome_process(personal) is False

    # GPM Chrome -> Must return True
    gpm = [
        "C:\\Users\\Kibe\\AppData\\Local\\Programs\\GPMLogin\\gpmdriver\\chrome.exe",
        "--user-data-dir=C:\\Users\\Kibe\\AppData\\Local\\Programs\\GPMLogin\\profile\\B2qsvD2MSF-23092026",
        "--remote-debugging-port=51194"
    ]
    assert watchdog.is_gpm_chrome_process(gpm) is True

    # Empty / Other -> False
    assert watchdog.is_gpm_chrome_process([]) is False
    assert watchdog.is_gpm_chrome_process(["python", "app.py"]) is False


def test_extract_profile_path_and_port():
    cmd = [
        "chrome.exe",
        "--user-data-dir=C:\\Users\\Kibe\\AppData\\Local\\Programs\\GPMLogin\\profile\\test_profile_path",
        "--remote-debugging-port=55123"
    ]
    assert watchdog.extract_profile_path(cmd) == "test_profile_path"
    assert watchdog.extract_debugging_port(cmd) == 55123


def test_lookup_profile_info(tmp_path):
    db_file = tmp_path / "profile_data.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("CREATE TABLE profiles (Id TEXT, Name TEXT, ProfilePath TEXT);")
    cur.execute("INSERT INTO profiles VALUES ('id-123', '01 - test@gmail.com', 'test_path_123');")
    conn.commit()
    conn.close()

    p_id, p_name = watchdog.lookup_profile_info(db_file, "test_path_123")
    assert p_id == "id-123"
    assert p_name == "01 - test@gmail.com"

    # Not found
    n_id, n_name = watchdog.lookup_profile_info(db_file, "non_existent")
    assert n_id is None
    assert n_name is None


def test_ignore_fresh_gpm_profile():
    mock_proc = MagicMock()
    mock_proc.info = {
        "pid": 1111,
        "name": "chrome.exe",
        "create_time": 9900.0,
        "cmdline": [
            "chrome.exe",
            "--user-data-dir=C:\\Users\\Kibe\\AppData\\Local\\Programs\\GPMLogin\\profile\\fresh_prof"
        ]
    }
    with patch("time.time", return_value=10000.0):
        with patch("psutil.process_iter", return_value=[mock_proc]):
            reaped = watchdog.reap_stale_profiles(threshold_seconds=3600)
            assert len(reaped) == 0


def test_detect_and_reap_stale_gpm_profile():
    mock_proc = MagicMock()
    mock_proc.info = {
        "pid": 2222,
        "name": "chrome.exe",
        "create_time": 5000.0,
        "cmdline": [
            "chrome.exe",
            "--user-data-dir=C:\\Users\\Kibe\\AppData\\Local\\Programs\\GPMLogin\\profile\\stale_prof",
            "--remote-debugging-port=51122"
        ]
    }
    mock_proc.children.return_value = []

    with patch("time.time", return_value=10000.0):
        with patch("psutil.process_iter", return_value=[mock_proc]):
            with patch("requests.get") as mock_req:
                with patch("gpm_stale_profile_watchdog.lookup_profile_info", return_value=("prof-uuid-2222", "M02 - stale@gmail.com")):
                    reaped = watchdog.reap_stale_profiles(threshold_seconds=3600, dry_run=False)

                    assert len(reaped) == 1
                    assert reaped[0]["pid"] == 2222
                    assert reaped[0]["profile_id"] == "prof-uuid-2222"
                    assert reaped[0]["name"] == "M02 - stale@gmail.com"

                    mock_req.assert_called_once_with("http://127.0.0.1:19995/api/v3/profiles/stop/prof-uuid-2222", timeout=5)
                    mock_proc.terminate.assert_called_once()


def test_dry_run_mode():
    mock_proc = MagicMock()
    mock_proc.info = {
        "pid": 3333,
        "name": "chrome.exe",
        "create_time": 5000.0,
        "cmdline": [
            "chrome.exe",
            "--user-data-dir=C:\\Users\\Kibe\\AppData\\Local\\Programs\\GPMLogin\\profile\\stale_prof"
        ]
    }
    with patch("time.time", return_value=10000.0):
        with patch("psutil.process_iter", return_value=[mock_proc]):
            with patch("requests.get") as mock_req:
                reaped = watchdog.reap_stale_profiles(threshold_seconds=3600, dry_run=True)
                assert len(reaped) == 1
                mock_req.assert_not_called()
                mock_proc.terminate.assert_not_called()
                mock_proc.kill.assert_not_called()


def test_main_silent_when_clean(capsys):
    with patch("gpm_stale_profile_watchdog.reap_stale_profiles", return_value=[]):
        with patch("sys.argv", ["watchdog"]):
            ret = watchdog.main()
            assert ret == 0
            captured = capsys.readouterr()
            assert captured.out == ""


# --- 5 NEW AUDIT TESTS ---


def test_is_gpm_chrome_process_edge_cases():
    # 1. False positive with custom chrome profile directory
    custom_chrome = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "--user-data-dir=C:\\temp\\custom_chrome"
    ]
    assert watchdog.is_gpm_chrome_process(custom_chrome) is False

    # 2. Case-insensitive path matching
    case_upper = [
        "CHROME.EXE",
        "--USER-DATA-DIR=C:\\USERS\\KIBE\\APPDATA\\LOCAL\\PROGRAMS\\GPMLOGIN\\PROFILE\\PROFILE_01"
    ]
    assert watchdog.is_gpm_chrome_process(case_upper) is True

    # 3. Forward slash variant
    forward_slash = [
        "chrome.exe",
        "--user-data-dir=C:/Programs/GPMLogin/profile/profile_02"
    ]
    assert watchdog.is_gpm_chrome_process(forward_slash) is True

    # 4. Separated argument format --user-data-dir <path>
    separated = [
        "chrome.exe",
        "--user-data-dir",
        "C:\\Programs\\GPMLogin\\profile\\profile_03"
    ]
    assert watchdog.is_gpm_chrome_process(separated) is True

    # 5. Chrome without user-data-dir (e.g. headless or vanilla)
    no_dir = ["chrome.exe", "--remote-debugging-port=9222"]
    assert watchdog.is_gpm_chrome_process(no_dir) is False


def test_multi_process_tree_deduplication():
    # 1 browser process + 3 child processes (renderer, gpu, utility) with same profile
    browser_proc = MagicMock()
    browser_proc.info = {
        "pid": 5001,
        "name": "chrome.exe",
        "create_time": 1000.0,
        "cmdline": [
            "chrome.exe",
            "--user-data-dir=C:\\Programs\\GPMLogin\\profile\\shared_prof_id"
        ]
    }
    renderer_proc = MagicMock()
    renderer_proc.info = {
        "pid": 5002,
        "name": "chrome.exe",
        "create_time": 1000.0,
        "cmdline": [
            "chrome.exe",
            "--type=renderer",
            "--user-data-dir=C:\\Programs\\GPMLogin\\profile\\shared_prof_id"
        ]
    }
    gpu_proc = MagicMock()
    gpu_proc.info = {
        "pid": 5003,
        "name": "chrome.exe",
        "create_time": 1000.0,
        "cmdline": [
            "chrome.exe",
            "--type=gpu-process",
            "--user-data-dir=C:\\Programs\\GPMLogin\\profile\\shared_prof_id"
        ]
    }
    utility_proc = MagicMock()
    utility_proc.info = {
        "pid": 5004,
        "name": "chrome.exe",
        "create_time": 1000.0,
        "cmdline": [
            "chrome.exe",
            "--type=utility",
            "--user-data-dir=C:\\Programs\\GPMLogin\\profile\\shared_prof_id"
        ]
    }

    with patch("time.time", return_value=10000.0):
        with patch("psutil.process_iter", return_value=[browser_proc, renderer_proc, gpu_proc, utility_proc]):
            reaped = watchdog.reap_stale_profiles(threshold_seconds=3600, dry_run=True)
            # Only the single browser process is reaped; child processes are skipped / deduplicated
            assert len(reaped) == 1
            assert reaped[0]["pid"] == 5001
            assert reaped[0]["profile_path"] == "shared_prof_id"


def test_gpm_api_failure_and_process_race_condition():
    mock_proc = MagicMock()
    mock_proc.info = {
        "pid": 6001,
        "name": "chrome.exe",
        "create_time": 1000.0,
        "cmdline": [
            "chrome.exe",
            "--user-data-dir=C:\\Programs\\GPMLogin\\profile\\race_prof"
        ]
    }
    # Simulate process disappearing before terminate/wait/kill
    mock_proc.children.side_effect = psutil.NoSuchProcess(pid=6001)
    mock_proc.terminate.side_effect = psutil.NoSuchProcess(pid=6001)
    mock_proc.wait.side_effect = psutil.NoSuchProcess(pid=6001)
    mock_proc.kill.side_effect = psutil.NoSuchProcess(pid=6001)

    with patch("time.time", return_value=10000.0):
        with patch("psutil.process_iter", return_value=[mock_proc]):
            with patch("requests.get", side_effect=requests.RequestException("GPM API Connection Refused")):
                with patch("gpm_stale_profile_watchdog.lookup_profile_info", return_value=("prof-race-id", "Race Profile")):
                    # Must not throw unhandled exception, completes cleanly
                    reaped = watchdog.reap_stale_profiles(threshold_seconds=3600, dry_run=False)
                    assert len(reaped) == 1
                    assert reaped[0]["pid"] == 6001


def test_telemetry_file_and_stderr_format(tmp_path, capsys):
    log_file = tmp_path / "gpm_watchdog.jsonl"
    mock_proc = MagicMock()
    mock_proc.info = {
        "pid": 7001,
        "name": "chrome.exe",
        "create_time": 2000.0,
        "cmdline": [
            "chrome.exe",
            "--user-data-dir=C:\\Programs\\GPMLogin\\profile\\telemetry_prof"
        ]
    }
    with patch.object(watchdog, "TELEMETRY_LOG", log_file):
        with patch("time.time", return_value=10000.0):
            with patch("psutil.process_iter", return_value=[mock_proc]):
                reaped = watchdog.reap_stale_profiles(threshold_seconds=3600, dry_run=True)
                assert len(reaped) == 1

                # Check stderr format
                captured = capsys.readouterr()
                assert "[TELEMETRY_METRIC]" in captured.err

                # Check telemetry file exists and JSON line format
                assert log_file.exists()
                lines = log_file.read_text(encoding="utf-8").strip().splitlines()
                assert len(lines) == 1
                entry = json.loads(lines[0])
                assert entry["event"] == "stale_gpm_reaped"
                assert entry["pid"] == 7001
                assert entry["age_seconds"] == 8000
                assert "profile_id" in entry
                assert "timestamp" in entry
                # Validate ISO timestamp parseable
                datetime.fromisoformat(entry["timestamp"])


def test_access_denied_graceful_handling():
    class DeniedProc:
        @property
        def info(self):
            raise psutil.AccessDenied(pid=9999)

    denied_proc = DeniedProc()

    valid_proc = MagicMock()
    valid_proc.info = {
        "pid": 8001,
        "name": "chrome.exe",
        "create_time": 1000.0,
        "cmdline": [
            "chrome.exe",
            "--user-data-dir=C:\\Programs\\GPMLogin\\profile\\valid_prof"
        ]
    }

    with patch("time.time", return_value=10000.0):
        with patch("psutil.process_iter", return_value=[denied_proc, valid_proc]):
            reaped = watchdog.reap_stale_profiles(threshold_seconds=3600, dry_run=True)
            # Denied process is gracefully skipped, valid process is reaped
            assert len(reaped) == 1
            assert reaped[0]["pid"] == 8001
