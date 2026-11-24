import os
import sys
import time
from unittest.mock import patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "deploy", "hermes-home", "scripts"))
import watchdog_kill_orphaned_scans as wks


def test_reboot_blackout_windows():
    # Giả lập uptime lớn (10000s) để chỉ kiểm tra theo giờ
    with patch("psutil.boot_time", return_value=0.0):
        # 05:05 -> True, 05:20 -> True, 05:35 -> True
        for h, m, exp in [
            (5, 0, False),
            (5, 5, True),
            (5, 20, True),
            (5, 35, True),
            (5, 36, False),
            (11, 20, True),
            (17, 20, True),
            (6, 0, False),
            (12, 0, False),
        ]:
            mock_time = time.mktime((2026, 11, 25, h, m, 0, 0, 0, -1))
            assert wks.is_reboot_blackout_window(now_ts=mock_time) is exp


def test_reboot_blackout_uptime():
    # Khi uptime < 900s, luôn trả về True kể cả ngoài khung giờ reboot (06:00)
    now_ts = 1000.0
    with patch("psutil.boot_time", return_value=now_ts - 300.0):
        assert wks.is_reboot_blackout_window(now_ts=now_ts) is True

    # Khi uptime >= 900s và ngoài khung giờ -> False
    with patch("psutil.boot_time", return_value=now_ts - 1000.0):
        mock_time = time.mktime((2026, 11, 25, 6, 0, 0, 0, 0, -1))
        assert wks.is_reboot_blackout_window(now_ts=mock_time) is False


def test_kill_orphaned_scans_skips_during_blackout(capsys):
    with patch.object(wks, "is_reboot_blackout_window", return_value=True), \
         patch("psutil.process_iter") as mock_iter:
        wks.kill_orphaned_scans()
        assert mock_iter.call_count == 0
    captured = capsys.readouterr()
    assert captured.out == ""
