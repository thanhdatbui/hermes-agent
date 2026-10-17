from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from cron_night_tiktok_2fa_watchdog import (
    is_safe_rolling_window,
    parse_summary_counts,
    run_night_batch,
    EXIT_SUCCESS,
)

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")


def test_is_safe_rolling_window():
    # Né ca 1 (05:45 - 09:30)
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 6, 0, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 8, 30, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 9, 15, tzinfo=HCMC))

    # Khung rảnh sáng (09:30 - 11:45)
    assert is_safe_rolling_window(datetime(2026, 10, 15, 10, 0, tzinfo=HCMC))

    # Né ca 2 (11:45 - 15:30)
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 12, 0, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 14, 0, tzinfo=HCMC))

    # Khung rảnh chiều (15:30 - 17:45)
    assert is_safe_rolling_window(datetime(2026, 10, 15, 16, 0, tzinfo=HCMC))

    # Né ca 3 (17:45 - 21:30)
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 18, 0, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 20, 0, tzinfo=HCMC))

    # Khung rảnh đêm (21:30 - 04:00)
    assert is_safe_rolling_window(datetime(2026, 10, 15, 22, 0, tzinfo=HCMC))
    assert is_safe_rolling_window(datetime(2026, 10, 15, 1, 0, tzinfo=HCMC))

    # Né dọn cache (04:00 - 04:30)
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 4, 15, tzinfo=HCMC))
    assert is_safe_rolling_window(datetime(2026, 10, 15, 4, 45, tzinfo=HCMC))

    # Khung giờ 5h sáng (chạy đến 05:15)
    assert is_safe_rolling_window(datetime(2026, 10, 15, 5, 5, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 5, 20, tzinfo=HCMC))


def test_parse_summary_counts():
    output = "=== CLUSTER KIBE (MÁY 1-80) ===\nTOTAL=40 SUCCESS=38 FAILED=2\n"
    res = parse_summary_counts(output)
    assert res["total"] == 40
    assert res["success"] == 38
    assert res["failed"] == 2


def test_run_night_batch_dry_run():
    code, out = run_night_batch(dry_run=True)
    assert code == EXIT_SUCCESS
    assert "TOTAL=40 SUCCESS=40 FAILED=0" in out


def test_workbook_path_type():
    from cron_night_tiktok_2fa_watchdog import WORKBOOK_PATH

    assert isinstance(WORKBOOK_PATH, Path)

