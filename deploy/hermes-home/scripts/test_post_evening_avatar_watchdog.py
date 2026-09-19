from __future__ import annotations

import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# Add scripts directory to sys.path
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from post_evening_avatar_watchdog import (
    format_report_html,
    get_tik_avatar_stats,
    get_tik_avatar_status,
    rescan_completed_machines,
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

    assert "chưa gán nick (0/80 acc)" in report
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


def test_get_tik_avatar_stats_real_farm_db_if_exists():
    from pathlib import Path
    real_db = Path(r"D:\Taadaa\data\tiktok_tracker.db")
    if not real_db.exists():
        pytest.skip("Real farm DB not available on this host")
    st = get_tik_avatar_stats(7, host_context={"host_id": "kibe", "db_path": real_db})
    assert "unuploaded" in st
    assert "uploaded_count" in st
    assert "total_accounts" in st
    assert isinstance(st["uploaded_count"], int)
    assert st["total_accounts"] <= 80, f"Tik 7 got {st['total_accounts']} accounts, expected <= 80 for Kibe"

