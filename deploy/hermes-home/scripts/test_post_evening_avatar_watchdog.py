from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add scripts directory to sys.path
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from post_evening_avatar_watchdog import format_report_html, get_tik_avatar_status


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
