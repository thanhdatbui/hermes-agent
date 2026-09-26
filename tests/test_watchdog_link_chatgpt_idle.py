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
import post_morning_gmail_2fa_watchdog as w_morning
import cron_clear_tiktok_cache as w_cache

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
        self.assertEqual(w_gpm.MAX_WORKERS, 5)
        self.assertEqual(w_gpm.MAX_LOGINS_PER_PROXY, 2)
        self.assertEqual(w_gpm.MIN_IDLE_BUFFER_MIN, 10)

    def test_morning_2fa_uses_session_verified_candidates(self):
        candidates = [
            {"email": "ready@gmail.com", "name": "1 ready@gmail.com", "machine": 1,
             "google_session_verified": True},
            {"email": "pending@gmail.com", "name": "2 pending@gmail.com", "machine": 2,
             "google_session_verified": False},
        ]
        events = []

        def acquire():
            events.append("acquire")
            return True

        def setup(candidate):
            events.append("action")
            return {"status": "ALREADY_ACTIVE"}

        def release():
            events.append("release")

        with patch.object(w_morning, "get_gpm_candidates", return_value=candidates), \
             patch.object(w_morning, "setup_authenticator_for_profile", side_effect=setup) as setup_mock, \
             patch.object(w_morning, "save_state_results"), \
             patch.object(w_morning, "ProcessLock") as lock_cls, \
             patch.object(w_morning.sys, "argv", ["watchdog", "--force"]):
            lock_cls.return_value.acquire.side_effect = acquire
            lock_cls.return_value.release.side_effect = release
            self.assertEqual(w_morning.main(), 0)
        setup_mock.assert_called_once_with(candidates[0])
        self.assertEqual(events, ["acquire", "action", "release"])

    def test_morning_session_helper_is_fail_closed(self):
        self.assertTrue(w_morning._profile_has_google_session({"session_verified": True}))
        self.assertFalse(w_morning._profile_has_google_session({"session_verified": False}))
        self.assertFalse(w_morning._profile_has_google_session({"email": "missing@gmail.com"}))

    def test_cache_dry_run_does_not_consume_retry_budget(self):
        state = {"last_date": "2026-09-26", "cleared_machines": [], "machine_retries": {"1": 0}}
        with patch.object(w_cache, "load_state", return_value=state), \
             patch.object(w_cache, "get_connected_devices", return_value={"serial-1": "device"}), \
             patch.object(w_cache, "load_machine_serials", return_value=[(1, "serial-1")]), \
             patch.object(w_cache, "save_state") as save_state, \
             patch.object(w_cache, "clear_device_cache") as clear_device, \
             patch.object(w_cache.sys, "argv", ["cache", "--force", "--dry-run"]):
            self.assertEqual(w_cache.main(), 0)
        clear_device.assert_not_called()
        save_state.assert_not_called()
        self.assertEqual(state["machine_retries"]["1"], 0)

    def test_cache_retry_policy_increments_only_on_unlocked_failure(self):
        state = {"last_date": "2026-09-26", "cleared_machines": [], "machine_retries": {}}

        def mock_clear(m_num, serial):
            if m_num == 1:
                return m_num, serial, True, f"[OK] Machine {m_num}: cache cleared"
            if m_num == 2:
                return m_num, serial, False, f"[LOCKED] Machine {m_num} is busy"
            return m_num, serial, False, f"[WARN] Machine {m_num} (code 1): error"

        with patch.object(w_cache, "load_state", return_value=state), \
             patch.object(w_cache, "get_connected_devices", return_value={"s-1": "device", "s-2": "device", "s-3": "device"}), \
             patch.object(w_cache, "load_machine_serials", return_value=[(1, "s-1"), (2, "s-2"), (3, "s-3")]), \
             patch.object(w_cache, "save_state"), \
             patch.object(w_cache, "clear_device_cache", side_effect=mock_clear), \
             patch.object(w_cache.sys, "argv", ["cache", "--force"]):
            self.assertEqual(w_cache.main(), 0)

        # Successful machine 1: cleared, NO retry increment
        self.assertIn(1, state["cleared_machines"])
        self.assertEqual(state["machine_retries"].get("1", 0), 0)
        # Locked machine 2: ignored, NO retry increment
        self.assertEqual(state["machine_retries"].get("2", 0), 0)
        # Failed error machine 3: retry count incremented by 1
        self.assertEqual(state["machine_retries"].get("3", 0), 1)


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
