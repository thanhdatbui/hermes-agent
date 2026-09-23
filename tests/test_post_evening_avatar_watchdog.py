from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# Add scripts directory to sys.path
scripts_dir = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
local_scripts = Path(os.path.expanduser(r"~\AppData\Local\hermes\scripts"))
if local_scripts.exists() and str(local_scripts) not in sys.path:
    sys.path.insert(0, str(local_scripts))

from post_evening_avatar_watchdog import (
    format_report_html,
    get_tik_avatar_stats,
    get_tik_avatar_status,
    rescan_completed_machines,
    count_active_locks,
    collect_recent_batch_results,
    check_batch_status,
    report_final_summary,
)


def test_format_report_html_all_done():
    host_id = "kibe"
    stats = {
        5: {"uploaded_count": 20, "total_accounts": 20, "unuploaded": []},
        6: {"uploaded_count": 20, "total_accounts": 20, "unuploaded": []},
    }
    now_dt = datetime(2026, 9, 15, 22, 30, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    report = format_report_html(host_id=host_id, all_done=True, stats_by_tik=stats, target_tiks=[5, 6], now_dt=now_dt)

    assert "hoàn tất" in report.lower()
    assert "HOÀN TẤT UP AVATAR CHO CÁC ACC ĐÃ CÓ NICK" in report
    assert "Đã có 20/20 (hoàn tất 100%)" in report


def test_format_report_html_unassigned_tik():
    host_id = "admin"
    stats = {
        1: {"uploaded_count": 20, "total_accounts": 20, "unuploaded": []},
        2: {"uploaded_count": 0, "total_accounts": 0, "unuploaded": []},
    }
    now_dt = datetime(2026, 9, 15, 22, 30, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    report = format_report_html(host_id=host_id, all_done=True, stats_by_tik=stats, target_tiks=[1, 2], now_dt=now_dt)

    assert "Chưa gán nick" in report
    assert "Tik 2" in report
    assert "HOÀN TẤT UP AVATAR CHO CÁC ACC ĐÃ CÓ NICK" in report


def test_format_report_html_not_all_done():
    host_id = "kibe"
    stats = {
        5: {"uploaded_count": 15, "total_accounts": 20, "unuploaded": [1, 2, 3, 4, 5]},
        6: {"uploaded_count": 18, "total_accounts": 20, "unuploaded": [10, 11]},
    }
    now_dt = datetime(2026, 9, 15, 23, 45, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    report = format_report_html(host_id=host_id, all_done=False, stats_by_tik=stats, target_tiks=[5, 6], now_dt=now_dt)

    assert "Đã có:" in report
    assert "%" in report
    assert "còn 7 máy chưa up" in report
    assert "còn 5 máy" in report
    assert "còn 2 máy" in report


def _setup_mock_db(db_path: Path):
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE farm_account_info (
                username TEXT,
                may INTEGER,
                tik INTEGER,
                host_id TEXT,
                updated_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                username TEXT,
                uid TEXT,
                follower INTEGER,
                following INTEGER,
                heart INTEGER,
                video INTEGER,
                status TEXT,
                avatar_thumb TEXT,
                has_avatar INTEGER
            )
            """
        )
        # Insert test data:
        # may 1, tik 7, host_id 'kibe', username 'u1', has_avatar 1
        # may 2, tik 7, host_id 'kibe', username 'u2', has_avatar 0
        # may 201, tik 7, host_id 'admin', username 'u201', has_avatar 1
        cursor.executemany(
            "INSERT INTO farm_account_info (may, tik, host_id, username) VALUES (?, ?, ?, ?)",
            [
                (1, 7, "kibe", "u1"),
                (2, 7, "kibe", "u2"),
                (201, 7, "admin", "u201"),
            ],
        )
        cursor.executemany(
            "INSERT INTO snapshots (username, has_avatar, status) VALUES (?, ?, ?)",
            [
                ("u1", 1, "active"),
                ("u2", 0, "active"),
                ("u201", 1, "active"),
            ],
        )
        conn.commit()


def test_get_tik_avatar_stats_sqlite_parameterized_query(tmp_path):
    tmp_db_path = tmp_path / "tiktok_tracker.db"
    _setup_mock_db(tmp_db_path)

    stats = get_tik_avatar_stats(7, host_context={"host_id": "kibe", "db_path": tmp_db_path})
    assert stats["total_accounts"] == 2
    assert stats["uploaded_count"] == 1
    assert stats["unuploaded"] == [2]


def test_get_tik_avatar_stats_admin_host(tmp_path):
    tmp_db_path = tmp_path / "tiktok_tracker.db"
    _setup_mock_db(tmp_db_path)

    stats = get_tik_avatar_stats(7, host_context={"host_id": "admin", "db_path": tmp_db_path})
    assert stats["total_accounts"] == 1
    assert stats["uploaded_count"] == 1
    assert stats["unuploaded"] == []


def test_get_tik_avatar_stats_fallback_excel(tmp_path):
    # Pass non-existent sqlite db and empty workbook_dir
    non_existent_db = tmp_path / "non_existent.db"
    stats = get_tik_avatar_stats(
        7,
        workbook_dir=tmp_path,
        host_context={"host_id": "kibe", "db_path": non_existent_db, "workbook_dir": tmp_path},
    )
    assert stats == {"unuploaded": [], "uploaded_count": 0, "total_accounts": 0}


@patch("subprocess.run")
@patch("pathlib.Path.exists")
def test_rescan_completed_machines_subprocess_call(mock_exists, mock_run):
    mock_exists.return_value = True
    mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

    res = rescan_completed_machines([1, 2, 1])
    assert res is True

    assert mock_run.called
    called_cmd = mock_run.call_args[0][0]
    assert "--machines" in called_cmd
    machines_idx = called_cmd.index("--machines")
    assert called_cmd[machines_idx + 1] == "1,2"
    assert "--workers" in called_cmd
    workers_idx = called_cmd.index("--workers")
    assert called_cmd[workers_idx + 1] == "10"


def test_rescan_completed_machines_silence_stdout(capsys):
    with patch("subprocess.run") as mock_run, patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="TRACKER DATA", stderr="")
        res = rescan_completed_machines([1, 2])
        assert res is True
        captured = capsys.readouterr()
        assert captured.out == ""


def test_count_active_locks_freshness_and_lock_files(tmp_path):
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    # 1. Fresh active json
    f_active = lock_dir / "machine_1.json"
    f_active.write_text('{"status": "active"}', encoding="utf-8")
    # 2. Stale json (> 2700s)
    f_stale = lock_dir / "machine_2.json"
    f_stale.write_text('{"status": "active"}', encoding="utf-8")
    past_mtime = time.time() - 3600
    os.utime(f_stale, (past_mtime, past_mtime))
    # 3. Old style .lock file
    f_lock = lock_dir / "machine_3.lock"
    f_lock.write_text("lock", encoding="utf-8")
    # 4. Malformed json
    f_bad = lock_dir / "machine_4.json"
    f_bad.write_text("{invalid json", encoding="utf-8")

    with patch("post_evening_avatar_watchdog.LOCK_DIR", lock_dir):
        with patch("post_evening_avatar_watchdog.Path") as MockPath:
            # Let Path(expanduser) return non-existent secondary dir
            def side_effect(p):
                if str(p) == str(lock_dir):
                    return lock_dir
                return tmp_path / "non_existent"
            cnt = count_active_locks()
            assert cnt >= 1


def test_collect_recent_batch_results_from_summary(tmp_path):
    batch_dir = tmp_path / "batch_runs"
    batch_dir.mkdir()
    run_dir = batch_dir / "batch_tik7_20260923_210000"
    run_dir.mkdir()
    summary = run_dir / "summary.csv"
    summary.write_text(
        "Machine,Status,Verified,Reason,Report\n"
        "1,SUCCESS,true,,\n"
        "2,FAILED,false,[AVATAR_UPLOAD_MENU_MISSING],\n"
        "3,FAILED,false,[DEVICE_OFFLINE],\n",
        encoding="utf-8",
    )
    succeeded, failed_by_reason = collect_recent_batch_results(7, batch_runs_dir=batch_dir)
    assert 1 in succeeded
    assert 2 in failed_by_reason.get("AVATAR_UPLOAD_MENU_MISSING", [])
    assert 3 in failed_by_reason.get("DEVICE_OFFLINE", [])


def test_report_final_summary_duplicate_prevention(capsys):
    state = {}
    with patch("post_evening_avatar_watchdog.get_telegram_bot_token", return_value="fake_token"):
        with patch("post_evening_avatar_watchdog.send_farm_alert", return_value=True) as mock_send:
            stats = {5: {"uploaded_count": 80, "total_accounts": 80, "unuploaded": []}}
            ctx = {
                "host_id": "admin",
                "target_tiks": [5],
                "workbook_dir": None,
                "state_file": Path("test_state.json"),
            }
            with patch("post_evening_avatar_watchdog.save_state"):
                report_final_summary(state, all_done=True, host_context=ctx, stats_by_tik=stats)
                assert mock_send.called
                captured = capsys.readouterr()
                # Since send_farm_alert returned True, stdout must remain silent to prevent duplicate cron dispatch
                assert captured.out == ""


def test_format_report_html_backward_compatibility_legacy_list():
    # Legacy caller passes dict[int, list[int]] for stats_by_tik instead of dict[int, dict]
    legacy_stats = {
        5: [1, 2, 3],
        6: [],
    }
    now_dt = datetime(2026, 9, 15, 23, 45, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    report = format_report_html(host_id="kibe", all_done=False, stats_by_tik=legacy_stats, target_tiks=[5, 6], now_dt=now_dt)
    assert "Tik 5" in report
    assert "Tik 6" in report
    assert "còn 3 máy" in report


def test_report_final_summary_fallback_on_api_failure(capsys):
    state = {}
    with patch("post_evening_avatar_watchdog.send_farm_alert", side_effect=Exception("API Network Timeout")):
        stats = {5: {"uploaded_count": 80, "total_accounts": 80, "unuploaded": []}}
        ctx = {
            "host_id": "admin",
            "target_tiks": [5],
            "workbook_dir": None,
            "state_file": Path("test_state.json"),
        }
        with patch("post_evening_avatar_watchdog.save_state"):
            report_final_summary(state, all_done=True, host_context=ctx, stats_by_tik=stats)
            captured = capsys.readouterr()
            assert "send_farm_alert failed" in captured.err



