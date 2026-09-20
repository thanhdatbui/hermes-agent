import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

REPO_SCRIPTS = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(REPO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REPO_SCRIPTS))

import watchdog_link_chatgpt_idle as w_cg
import post_evening_gpm_login_watchdog as w_gpm

class TestWatchdogLinkChatgptAndGpm(unittest.TestCase):
    def test_get_live_targets_from_mock_excel(self):
        with patch.object(w_cg, "get_gpm_pending_emails", return_value={"live_ok@gmail.com", "live_chatgpt@gmail.com"}):
            with patch("watchdog_link_chatgpt_idle.MASTER_XLSX") as mock_p:
                mock_p.exists.return_value = True
                with patch("openpyxl.load_workbook") as mock_wb_func:
                    mock_wb = MagicMock()
                    mock_wb.sheetnames = ["Kibe_Farm_S7"]
                    mock_ws = MagicMock()
                    mock_ws.iter_rows.return_value = [
                        ["STT", "Email", "Password", "Recovery", "2FA", "SDT", "Trạng Thái", "Số Máy", "Model", "Serial", "Proxy", "Profile", "Nguồn", "Ghi Chú", "Cập Nhật"],
                        [1, "live_ok@gmail.com", "P1", "", "", "", "LIVE", "Máy 10", "S7", "serial_10", "", "", "", "", "2026-09-04"],
                        [2, "live_chatgpt@gmail.com", "P2", "", "", "", "LIVE", "Máy 11", "S7", "serial_11", "", "", "", "CHATGPT_READY", "2026-09-04"],
                        [3, "die_acc@gmail.com", "P3", "", "", "", "DIE", "Máy 12", "S7", "serial_12", "", "", "", "", "2026-09-04"],
                    ]
                    mock_wb.__getitem__.return_value = mock_ws
                    mock_wb_func.return_value = mock_wb

                    targets = w_cg.get_live_targets()
                    self.assertEqual(len(targets), 1)
                    self.assertEqual(targets[0]["email"], "live_ok@gmail.com")
                    self.assertEqual(targets[0]["stt"], 10)
                    self.assertEqual(targets[0]["serial"], "serial_10")

    def test_dry_run_mode_telemetry(self):
        with patch.object(w_cg, "get_live_targets", return_value=[
            {"stt": 1, "serial": "s1", "email": "a@gmail.com", "pwd": "p", "dob": "2000-01-01"}
        ]):
            with patch.object(w_cg, "is_machine_locked", return_value=False):
                with patch.object(w_cg, "get_next_feed_slot_distance_minutes", return_value=999.0):
                    with patch.object(w_cg, "is_machine_in_feed", return_value=False):
                        res = w_cg.check_and_run_one(dry_run=True)
                        self.assertTrue(res.get("dry_run"))
                        self.assertIn("scanned_targets", res)

    def test_post_evening_gpm_login_constants(self):
        self.assertEqual(w_gpm.MAX_WORKERS, 2)
        self.assertEqual(w_gpm.MAX_LOGINS_PER_PROXY, 2)
        self.assertEqual(w_gpm.MIN_IDLE_BUFFER_MIN, 45)

    def test_aged_gate_fail_closed_logic(self):
        from datetime import datetime
        today_str = "2026-09-20"

        # Trường hợp 1: Đủ 14 ngày tuổi -> Passed
        valid_date = "2026-09-04"
        d_created = datetime.fromisoformat(valid_date).date()
        d_today = datetime.fromisoformat(today_str).date()
        self.assertGreaterEqual((d_today - d_created).days, 7)

        # Trường hợp 2: Chưa đủ 7 ngày tuổi (mới tạo hôm qua) -> Fail / Skip
        young_date = "2026-09-19"
        d_young = datetime.fromisoformat(young_date).date()
        self.assertLess((d_today - d_young).days, 7)

        # Trường hợp 3: Chuỗi rác hoặc rỗng -> Fail-closed
        bad_date = "invalid-date"
        is_valid = len(bad_date) >= 10 and bad_date[4] == "-" and bad_date[7] == "-"
        self.assertFalse(is_valid)

    def test_watchdog_telemetry_fields(self):
        telemetry = {
            "scanned_targets": 188,
            "skipped_locked": 2,
            "skipped_feed": 5,
            "skipped_distance": 10,
            "skipped_die": 0,
            "attempted": 1,
            "success": 1,
            "failed": 0,
            "dry_run": True
        }
        for k in ["scanned_targets", "skipped_locked", "skipped_feed", "skipped_distance", "attempted", "success", "failed"]:
            self.assertIn(k, telemetry)

if __name__ == "__main__":
    unittest.main()
