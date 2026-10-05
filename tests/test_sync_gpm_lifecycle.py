"""Offline regression tests for deploy/hermes-home/scripts/sync_gpm_lifecycle.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import openpyxl

SCRIPTS_DIR = Path(r"D:\Taadaa\Hermes\deploy\hermes-home\scripts")
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Load by explicit path under a unique module name so a stale runtime copy of
# sync_gpm_lifecycle elsewhere on sys.path (or already in sys.modules) cannot shadow it.
_LIFECYCLE_PATH = Path(r"D:/Taadaa/Hermes/deploy/hermes-home/scripts/sync_gpm_lifecycle.py")
_spec = importlib.util.spec_from_file_location("hermes_repo_sync_gpm_lifecycle", _LIFECYCLE_PATH)
lifecycle = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lifecycle
_spec.loader.exec_module(lifecycle)


def _write_workbook(path: Path, sheet_name: str, rows: list[tuple]) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def test_log_telemetry_metric_has_stable_schema():
    payload = {"created_count": 2, "reason": "offline-test"}
    with patch.object(lifecycle.logger, "info") as log_info, patch.object(
        lifecycle.os, "getpid", return_value=4321
    ):
        metric = lifecycle.log_telemetry_metric("regression", payload)

    assert set(metric) == {"timestamp", "event", "pid", "data"}
    assert metric["event"] == "regression"
    assert metric["pid"] == 4321
    assert metric["data"] == payload
    datetime.fromisoformat(metric["timestamp"])
    logged = log_info.call_args.args[0]
    assert "[TELEMETRY_METRIC]" in logged
    assert json.loads(logged.split("[TELEMETRY_METRIC] ", 1)[1]) == metric


def test_get_online_adb_devices_parses_only_device_state():
    adb_output = (
        "List of devices attached\n"
        "SERIAL-01\tdevice\n"
        "SERIAL-02\toffline\n"
        "SERIAL-03\tunauthorized\n"
        "SERIAL-04\tdevice product:foo\n"
    )
    result = MagicMock(stdout=adb_output)
    with patch.object(lifecycle.subprocess, "run", return_value=result) as run:
        assert lifecycle.get_online_adb_devices() == {"SERIAL-01", "SERIAL-04"}
    run.assert_called_once_with(
        [lifecycle.ADB_PATH, "devices"], capture_output=True, text=True, timeout=5
    )


def test_get_online_adb_devices_returns_empty_on_subprocess_failure():
    with patch.object(lifecycle.subprocess, "run", side_effect=OSError("adb missing")):
        assert lifecycle.get_online_adb_devices() == set()


def test_merge_taikhoan_dat_candidates_filters_rows_and_preserves_existing(tmp_path):
    workbook_path = tmp_path / "taikhoan_dat.xlsx"
    _write_workbook(
        workbook_path,
        "Tài Khoản",
        [
            ("Máy", "B", "C", "D", "E", "Email"),
            (1, None, None, None, None, "new@gmail.com"),
            (2, None, None, None, None, "excluded@gmail.com"),
            (3, None, None, None, None, "khoale@gmail.com"),
            ("bad", None, None, None, None, "badmachine@gmail.com"),
            (4, None, None, None, None, "not-an-email"),
            (5, None, None, None, None, "existing@gmail.com"),
            (6, None, None, None, None, "new@gmail.com"),
        ],
    )
    candidates = {"existing@gmail.com": 99}

    added = lifecycle.merge_taikhoan_dat_candidates(
        str(workbook_path), candidates, {"excluded@gmail.com"}
    )

    assert added == 1
    assert candidates == {"existing@gmail.com": 99, "new@gmail.com": 1}


def test_merge_taikhoan_dat_proxies_adds_values_and_fallback(tmp_path):
    workbook_path = tmp_path / "taikhoan_dat.xlsx"
    _write_workbook(
        workbook_path,
        "Tài Khoản",
        [
            tuple(f"col-{i}" for i in range(11)),
            (1, None, None, None, None, None, None, None, None, "SERIAL-01", "host:20001:user:pass"),
            (2, None, None, None, None, None, None, None, None, "SERIAL-02", ""),
            (3, None, None, None, None, None, None, None, None, None, "not-a-proxy"),
        ],
    )
    serials = {2: "KEEP-SERIAL"}
    proxy_map = {2: "keep:proxy"}

    lifecycle.merge_taikhoan_dat_proxies(str(workbook_path), serials, proxy_map)

    assert serials == {1: "SERIAL-01", 2: "KEEP-SERIAL"}
    assert proxy_map[1] == "host:20001:user:pass"
    assert proxy_map[2] == "keep:proxy"
    assert proxy_map[3] == "test.taadaa.click:20003:mobi3:TaadaaMobi#2026!"


def test_cleanup_s7_skips_machine_when_device_lock_unavailable(tmp_path):
    master_path = tmp_path / "master.xlsx"
    proxy_path = tmp_path / "proxy.xlsx"
    _write_workbook(
        master_path,
        "Kibe_Farm_S7",
        [
            tuple(f"col-{i}" for i in range(8)),
            (None, "die@gmail.com", None, None, None, None, "DIE", "M01"),
        ],
    )
    _write_workbook(proxy_path, "Proxy", [("Máy", "Serial"), (1, "SERIAL-01")])

    def unavailable_lock(**_kwargs):
        raise lifecycle.DeviceLockUnavailable("machine busy")

    with patch.object(lifecycle, "MASTER_FILE", str(master_path)), patch.object(
        lifecycle, "PROXY_FILE", str(proxy_path)
    ), patch.object(lifecycle, "get_online_adb_devices", return_value={"SERIAL-01"}), patch.object(
        lifecycle, "is_machine_in_feed_slot", return_value=False
    ), patch.object(lifecycle, "acquire_device_lock", side_effect=unavailable_lock), patch.object(
        lifecycle, "log_telemetry_metric"
    ) as telemetry, patch.object(lifecycle.subprocess, "run") as adb_run:
        assert lifecycle.cleanup_s7_die_accounts(force=True) == 0

    adb_run.assert_not_called()
    telemetry.assert_called_once_with(
        "s7_cleanup_completed", {"cleaned_count": 0, "die_machines_count": 1}
    )


def test_farm_safety_s7_account_preservation_when_adb_offline(tmp_path):
    master_path = tmp_path / "master.xlsx"
    proxy_path = tmp_path / "proxy.xlsx"
    _write_workbook(
        master_path,
        "Kibe_Farm_S7",
        [
            tuple(f"col-{i}" for i in range(8)),
            (None, "die1@gmail.com", None, None, None, None, "DIE", "M01"),
            (None, "ban2@gmail.com", None, None, None, None, "BAN", "M02"),
            (None, "live3@gmail.com", None, None, None, None, "LIVE", "M01"),
        ],
    )
    _write_workbook(proxy_path, "Proxy", [("Máy", "Serial"), (1, "SERIAL-01"), (2, "SERIAL-02")])
    adb_devices = MagicMock(stdout="List of devices attached\nSERIAL-01\toffline\nSERIAL-02\tunauthorized\n")
    preflight = MagicMock()

    with patch.object(lifecycle, "MASTER_FILE", str(master_path)), patch.object(
        lifecycle, "PROXY_FILE", str(proxy_path)
    ), patch.object(lifecycle.subprocess, "run", return_value=adb_devices) as adb_run, patch.object(
        lifecycle, "acquire_device_lock"
    ) as lock, patch.object(lifecycle, "log_telemetry_metric") as telemetry, patch.object(
        lifecycle.logger, "warning"
    ) as log_warning, patch.dict(sys.modules, {"preflight_s7_rolling_cleanup": preflight}):
        cleaned = lifecycle.cleanup_s7_die_accounts(dry_run=False, force=True)

    assert (cleaned or 0) == 0
    # Only the `adb devices` probe ran; no dumpsys, no keyevent, no account removal.
    adb_run.assert_called_once_with(
        [lifecycle.ADB_PATH, "devices"], capture_output=True, text=True, timeout=5
    )
    lock.assert_not_called()
    preflight.remove_account_adb.assert_not_called()
    telemetry.assert_not_called()
    log_warning.assert_called_once_with("Không có thiết bị ADB nào online.")


def test_lifecycle_telemetry_integration_with_watchdog(tmp_path):
    import sqlite3

    master_path = tmp_path / "master.xlsx"
    proxy_path = tmp_path / "proxy.xlsx"
    gpm_db = tmp_path / "profile_data.db"
    _write_workbook(
        master_path,
        "Kibe_Farm_S7",
        [
            tuple(f"col-{i}" for i in range(8)),
            (None, "live1@gmail.com", None, None, None, None, "LIVE", "M01"),
            (None, "live2@gmail.com", None, None, None, None, "LIVE", "M02"),
            (None, "exist@gmail.com", None, None, None, None, "LIVE", "M01"),
            (None, "die@gmail.com", None, None, None, None, "DIE", "M03"),
        ],
    )
    _write_workbook(
        proxy_path,
        "Proxy",
        [("Máy", "Serial", "Proxy"), (1, "SERIAL-01", "host:20001:u:p"), (2, "SERIAL-02", "host:20002:u:p")],
    )
    conn = sqlite3.connect(str(gpm_db))
    conn.execute("CREATE TABLE profiles (Id TEXT, Name TEXT)")
    conn.execute("INSERT INTO profiles VALUES ('p1', '01 - exist@gmail.com - 20001')")
    conn.commit()
    conn.close()

    client = MagicMock()
    client.create_profile.return_value = {"success": True}

    with patch.object(lifecycle, "MASTER_FILE", str(master_path)), patch.object(
        lifecycle, "PROXY_FILE", str(proxy_path)
    ), patch.object(lifecycle, "GPM_DB", gpm_db), patch.object(
        lifecycle, "TAIKHOAN_DAT_FILE", str(tmp_path / "missing_taikhoan.xlsx")
    ), patch.object(lifecycle, "STATUS_FILE", str(tmp_path / "missing_status.json")), patch.object(
        lifecycle, "GPMClient", return_value=client
    ), patch.object(lifecycle, "is_gpm_api_live", return_value=True), patch.object(
        lifecycle, "get_online_adb_devices", return_value={"SERIAL-01"}
    ), patch.object(lifecycle.logger, "info") as log_info:
        created = lifecycle.sync_lifecycle_gpm()

    # live2 is skipped because SERIAL-02 is offline; exist already has a profile.
    assert created == 1
    client.create_profile.assert_called_once_with(
        name="01 - live1@gmail.com - 20001", raw_proxy="host:20001:u:p", group_id=1
    )

    # Downstream watchdogs parse the structured [TELEMETRY_METRIC] log lines.
    metrics = [
        json.loads(call.args[0].split("[TELEMETRY_METRIC] ", 1)[1])
        for call in log_info.call_args_list
        if "[TELEMETRY_METRIC]" in call.args[0]
    ]
    events = [m["event"] for m in metrics]
    assert events == ["gpm_lifecycle_sync_die_skipped", "gpm_lifecycle_sync_completed"]

    completed = metrics[-1]
    assert set(completed) == {"timestamp", "event", "pid", "data"}
    assert isinstance(completed["pid"], int)
    assert datetime.fromisoformat(completed["timestamp"]).tzinfo is not None
    assert completed["data"] == {
        "created_count": 1,
        "live_candidates_total": 3,
        "existing_gpm_profiles": 1,
    }
    assert metrics[0]["data"] == {"die_emails_in_master": 1, "reason": "preserve_openai_codex_sessions"}
