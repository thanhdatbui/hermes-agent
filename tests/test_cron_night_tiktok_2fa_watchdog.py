# -*- coding: utf-8 -*-
import base64
from datetime import datetime
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path("D:/Taadaa/Hermes/deploy/hermes-home/scripts")))


class TestCronNightTiktok2FAWatchdog(unittest.TestCase):
    TOTAL_OUT = "=== CLUSTER KIBE (MÁY 1-80) ===\nTOTAL=40 SUCCESS=40 FAILED=0\n=== CLUSTER ADMIN (MÁY 201-280) ===\nTOTAL=40 SUCCESS=40 FAILED=0"

    def setUp(self):
        import cron_night_tiktok_2fa_watchdog as wd
        p = patch.object(wd, "send_telegram_report")
        p.start()
        self.addCleanup(p.stop)

    def _run_main(self, argv_extra, gmail_result=(0, ""), batch_result=(0, ""), already_ran=False):
        import cron_night_tiktok_2fa_watchdog as wd
        targets = {
            "run_gmail_batch": {"return_value": gmail_result}, "run_night_batch": {"return_value": batch_result},
            "save_state": {}, "save_gmail_state": {}, "send_telegram_report": {},
            "already_ran_gmail_tonight": {"return_value": already_ran},
            "is_safe_rolling_window": {"return_value": True}, "is_feed_runner_active": {"return_value": False},
            "is_clear_cache_active": {"return_value": False},
            "claim_lane": {"return_value": True}, "release_lane": {},
        }
        mocks = {k: patch.object(wd, k, **v).start() for k, v in targets.items()}
        for k in targets:
            self.addCleanup(patch.stopall)
        with patch.object(sys, "argv", ["cron_night_tiktok_2fa_watchdog.py", *argv_extra]):
            return wd.main(), mocks

    def test_parse_summary_counts_table(self):
        import cron_night_tiktok_2fa_watchdog as wd
        out = "machine | source_row | username | status\n12 | 96 | u1 | success\n75 | 596 | u2 | failed\n3 | 25 | u3 | skip"
        res = wd.parse_summary_counts(out)
        self.assertEqual((res["total"], res["success"], res["failed"], res["skip_safe"]), (3, 1, 1, 1))

    def test_parse_summary_counts_total_line(self):
        import cron_night_tiktok_2fa_watchdog as wd
        res = wd.parse_summary_counts("TOTAL=40 SUCCESS=38 FAILED=2")
        self.assertEqual((res["total"], res["success"], res["failed"], res["skip_safe"]), (40, 38, 2, 0))

    @patch("cron_night_tiktok_2fa_watchdog.save_state")
    @patch("cron_night_tiktok_2fa_watchdog.run_night_batch")
    @patch("cron_night_tiktok_2fa_watchdog.is_feed_runner_active", return_value=False)
    @patch("cron_night_tiktok_2fa_watchdog.already_ran_today", return_value=False)
    @patch("cron_night_tiktok_2fa_watchdog.claim_lane", return_value=True)
    def test_main_dual_cluster_suc_fail_defined(self, m_claim, m_ran, m_feed, m_batch, m_save):
        import cron_night_tiktok_2fa_watchdog as wd
        m_batch.return_value = (0, "=== CLUSTER KIBE (MÁY 1-80) ===\nTOTAL=40 SUCCESS=38 FAILED=2\n=== CLUSTER ADMIN (MÁY 201-280) ===\nTOTAL=40 SUCCESS=40 FAILED=0\n")
        with patch.object(sys, "argv", ["cron_night_tiktok_2fa_watchdog.py", "--force", "--lane", "tiktok"]):
            ret = wd.main()
        self.assertEqual(ret, 0)
        m_save.assert_called_once()
        _, details = m_save.call_args[0]
        self.assertEqual((details["success_count"], details["failed_count"], details["status"]), (78, 2, "partial_failure"))

    @patch("cron_night_tiktok_2fa_watchdog.save_state")
    @patch("cron_night_tiktok_2fa_watchdog.run_night_batch")
    @patch("cron_night_tiktok_2fa_watchdog.is_feed_runner_active", return_value=False)
    @patch("cron_night_tiktok_2fa_watchdog.already_ran_today", return_value=False)
    @patch("cron_night_tiktok_2fa_watchdog.claim_lane", return_value=True)
    def test_main_success_zero_failed(self, m_claim, m_ran, m_feed, m_batch, m_save):
        import cron_night_tiktok_2fa_watchdog as wd
        m_batch.return_value = (0, "=== CLUSTER KIBE (MÁY 1-80) ===\nTOTAL=40 SUCCESS=40 FAILED=0\n=== CLUSTER ADMIN (MÁY 201-280) ===\nTOTAL=40 SUCCESS=40 FAILED=0\n")
        with patch.object(sys, "argv", ["cron_night_tiktok_2fa_watchdog.py", "--force", "--lane", "tiktok"]):
            ret = wd.main()
        self.assertEqual(ret, 0)
        m_save.assert_called_once()
        _, details = m_save.call_args[0]
        self.assertEqual((details["success_count"], details["failed_count"], details["status"]), (80, 0, "success"))

    @patch("cron_night_tiktok_2fa_watchdog.save_state")
    @patch("cron_night_tiktok_2fa_watchdog.run_night_batch")
    @patch("cron_night_tiktok_2fa_watchdog.is_feed_runner_active", return_value=False)
    @patch("cron_night_tiktok_2fa_watchdog.already_ran_today", return_value=False)
    @patch("cron_night_tiktok_2fa_watchdog.claim_lane", return_value=True)
    def test_main_runner_error_exit_code(self, m_claim, m_ran, m_feed, m_batch, m_save):
        import cron_night_tiktok_2fa_watchdog as wd
        m_batch.return_value = (1, "Runner crashed")
        with patch.object(sys, "argv", ["cron_night_tiktok_2fa_watchdog.py", "--force", "--lane", "tiktok"]):
            ret = wd.main()
        self.assertEqual(ret, 1)
        m_save.assert_called_once()
        _, details = m_save.call_args[0]
        self.assertEqual((details["code"], details["status"]), (1, "failed"))

    @patch("cron_night_tiktok_2fa_watchdog.subprocess.run")
    @patch("cron_night_tiktok_2fa_watchdog.hydrate_workbook", return_value=True)
    def test_run_night_batch_subprocess_timeout(self, m_hydrate, m_sub):
        import subprocess
        import cron_night_tiktok_2fa_watchdog as wd
        with patch.object(Path, "exists", return_value=True):
            m_sub.side_effect = subprocess.TimeoutExpired(cmd="runner", timeout=5400)
            code, out = wd.run_night_batch(dry_run=False)
            self.assertEqual(code, 1)
            self.assertIn("timed out", out.lower())

    @patch("cron_night_tiktok_2fa_watchdog.subprocess.run")
    @patch("cron_night_tiktok_2fa_watchdog.hydrate_workbook", return_value=True)
    def test_ssh_admin_farm_encoded_command_utf16le(self, m_hydrate, m_sub):
        import cron_night_tiktok_2fa_watchdog as wd
        with patch.object(Path, "exists", return_value=True):
            m_sub.return_value = MagicMock(returncode=0, stdout="TOTAL=40 SUCCESS=40 FAILED=0", stderr="")
            code, out = wd.run_night_batch(dry_run=False)
            self.assertEqual(m_sub.call_count, 2)
            admin_cmd = m_sub.call_args_list[1][0][0]
            self.assertEqual((admin_cmd[0], admin_cmd[3]), ("ssh", "admin-farm"))
            ps_arg = admin_cmd[4]
            b64_str = ps_arg.split("-EncodedCommand ")[1]
            decoded = base64.b64decode(b64_str).decode("utf-16le")
            self.assertIn("python_runner/run_batch_live_2fa.py", decoded)
            self.assertIn("--workbook-sheet 'Tài Khoản'", decoded)

    @patch("cron_night_tiktok_2fa_watchdog.subprocess.run")
    @patch("cron_night_tiktok_2fa_watchdog.hydrate_workbook", return_value=True)
    def test_return_code_constants_and_logic(self, m_hydrate, m_sub):
        import cron_night_tiktok_2fa_watchdog as wd
        self.assertEqual((wd.EXIT_SUCCESS, wd.EXIT_SAFE_SKIP, wd.ACCEPTABLE_RETURN_CODES), (0, 4, (0, 4)))
        with patch.object(Path, "exists", return_value=True):
            m_sub.side_effect = [MagicMock(returncode=0, stdout="", stderr=""), MagicMock(returncode=0, stdout="", stderr="")]
            self.assertEqual(wd.run_night_batch(dry_run=False)[0], 0)
            m_sub.side_effect = [MagicMock(returncode=4, stdout="", stderr=""), MagicMock(returncode=0, stdout="", stderr="")]
            self.assertEqual(wd.run_night_batch(dry_run=False)[0], 0)
            m_sub.side_effect = [MagicMock(returncode=4, stdout="", stderr=""), MagicMock(returncode=4, stdout="", stderr="")]
            self.assertEqual(wd.run_night_batch(dry_run=False)[0], 4)
            m_sub.side_effect = [MagicMock(returncode=1, stdout="", stderr=""), MagicMock(returncode=0, stdout="", stderr="")]
            self.assertEqual(wd.run_night_batch(dry_run=False)[0], 1)

    def test_is_feed_runner_active(self):
        import cron_night_tiktok_2fa_watchdog as wd
        m_p1 = MagicMock()
        m_p1.info = {"name": "python.exe"}
        m_p1.cmdline.return_value = ["python", "multi_machine_feed_session.py"]
        m_p2 = MagicMock()
        m_p2.info = {"name": "notepad.exe"}
        m_p2.cmdline.return_value = ["notepad.exe"]
        with patch("psutil.process_iter", return_value=[m_p2]):
            self.assertFalse(wd.is_feed_runner_active())
        with patch("psutil.process_iter", return_value=[m_p1]):
            self.assertTrue(wd.is_feed_runner_active())

    def test_save_state_persists_failure_reason_and_cluster_details(self):
        import cron_night_tiktok_2fa_watchdog as wd
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_f = Path(tmp_dir) / "test_state.json"
            with patch.object(wd, "STATE_FILE", tmp_f), patch.object(wd, "STATE_DIR", Path(tmp_dir)):
                payload = {"status": "failed", "code": 1, "failure_reason": "Err", "clusters": {"admin": {"failed": 5}}}
                wd.save_state("2026-10-10", payload)
                saved = json.loads(tmp_f.read_text(encoding="utf-8"))
                self.assertIsNone(saved.get("last_success_date"))
                self.assertEqual(saved["details"]["failure_reason"], "Err")

    @patch("cron_night_tiktok_2fa_watchdog.save_state")
    @patch("cron_night_tiktok_2fa_watchdog.run_night_batch")
    @patch("cron_night_tiktok_2fa_watchdog.is_feed_runner_active", return_value=False)
    @patch("cron_night_tiktok_2fa_watchdog.already_ran_today", return_value=False)
    @patch("cron_night_tiktok_2fa_watchdog.claim_lane", return_value=True)
    def test_main_generates_unique_correlation_id_per_run(self, m_claim, m_ran, m_feed, m_batch, m_save):
        import cron_night_tiktok_2fa_watchdog as wd
        m_batch.return_value = (0, "TOTAL=2 SUCCESS=2 FAILED=0")
        ids = []
        for _ in range(2):
            with patch.object(sys, "argv", ["cron_night_tiktok_2fa_watchdog.py", "--force", "--lane", "tiktok"]):
                wd.main()
            ids.append(m_save.call_args[0][1]["correlation_id"])
        self.assertRegex(ids[0], r"^[0-9a-f]{12}$")
        self.assertNotEqual(ids[0], ids[1])

    def test_save_state_writes_top_level_correlation_id(self):
        import cron_night_tiktok_2fa_watchdog as wd
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_f = Path(tmp_dir) / "test_state.json"
            with patch.object(wd, "STATE_FILE", tmp_f), patch.object(wd, "STATE_DIR", Path(tmp_dir)):
                wd.save_state("2026-10-10", {"status": "success", "code": 0, "correlation_id": "abc123def456"})
                saved = json.loads(tmp_f.read_text(encoding="utf-8"))
                self.assertEqual(saved["correlation_id"], "abc123def456")

    def test_log_records_carry_correlation_id(self):
        import cron_night_tiktok_2fa_watchdog as wd
        with patch.object(wd, "CORRELATION_ID", "feedfacecafe"):
            rec = wd.logger.makeRecord("n", 20, __file__, 1, "msg", (), None)
            for h in wd.logger.handlers:
                for flt in h.filters:
                    flt.filter(rec)
            self.assertEqual(rec.correlation_id, "feedfacecafe")

    def test_paths_and_ssh_host_overridable_via_env(self):
        import importlib
        import cron_night_tiktok_2fa_watchdog as wd
        env = {"TAADAA_TIKTOK_2FA_REPO": "/tmp/custom-repo", "TAADAA_KIBE_WORKBOOK": "/tmp/custom-kibe.xlsx", "TAADAA_ADMIN_SSH": "custom-admin-host"}
        try:
            with patch.dict(os.environ, env):
                importlib.reload(wd)
                self.assertEqual(wd.TIKTOK_2FA_REPO_DIR, Path("/tmp/custom-repo"))
                self.assertEqual(wd.ADMIN_SSH_HOST, "custom-admin-host")
        finally:
            importlib.reload(wd)
        self.assertEqual(wd.ADMIN_SSH_HOST, os.getenv("TAADAA_ADMIN_SSH", "admin-farm"))

    def test_is_ca4_finished_detection(self):
        import tempfile
        import cron_night_tiktok_2fa_watchdog as watchdog

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_rep_file = Path(tmp_dir) / "feed_session_reported.json"
            with patch.object(watchdog, "REPORTED_FILE", temp_rep_file):
                # Case 1: file doesn't exist
                self.assertFalse(watchdog.is_ca4_finished("2026-10-10"))

                # Case 2: ca4_phien2 not reported yet
                temp_rep_file.write_text(json.dumps({"reported_sessions": ["2026-10-10_ca4_phien1"]}), encoding="utf-8")
                self.assertFalse(watchdog.is_ca4_finished("2026-10-10"))

                # Case 3: ca4_phien2 reported
                temp_rep_file.write_text(json.dumps({"reported_sessions": ["2026-10-10_ca4_phien1", "2026-10-10_ca4_phien2"]}), encoding="utf-8")
                self.assertTrue(watchdog.is_ca4_finished("2026-10-10"))

    @patch("cron_night_tiktok_2fa_watchdog.save_state")
    @patch("cron_night_tiktok_2fa_watchdog.run_night_batch", return_value=(0, ""))
    def test_main_skips_outside_safe_window(self, mock_batch, mock_save):
        from datetime import datetime
        import cron_night_tiktok_2fa_watchdog as watchdog
        now_dt = datetime(2026, 10, 10, 5, 30, tzinfo=watchdog.HCMC)
        with patch("cron_night_tiktok_2fa_watchdog.datetime") as mock_dt:
            mock_dt.now.return_value = now_dt
            with patch.object(sys, "argv", ["cron_night_tiktok_2fa_watchdog.py"]):
                ret = watchdog.main()
        self.assertEqual(ret, 0)
        mock_batch.assert_not_called()
        mock_save.assert_not_called()

    def test_is_safe_rolling_window_reboot_blackouts(self):
        import cron_night_tiktok_2fa_watchdog as watchdog
        for hour, minute in [(5, 20), (11, 20), (17, 20), (11, 15), (17, 15)]:
            with self.subTest(hour=hour, minute=minute):
                now_dt = datetime(2026, 10, 20, hour, minute, tzinfo=watchdog.HCMC)
                self.assertFalse(watchdog.is_safe_rolling_window(now_dt))
        now_dt = datetime(2026, 10, 20, 16, 50, tzinfo=watchdog.HCMC)
        self.assertTrue(watchdog.is_safe_rolling_window(now_dt))

    def test_gmail_phase_reports_to_gmail_chat(self):
        ret, m = self._run_main(["--lane", "gmail", "--force"], gmail_result=(0, self.TOTAL_OUT))
        self.assertEqual(ret, 0)
        m["run_night_batch"].assert_not_called()
        self.assertEqual(m["send_telegram_report"].call_args[0][0], "-5139245637")
        self.assertIn("BÁO CÁO REG GMAIL BAN ĐÊM", m["send_telegram_report"].call_args[0][1])
        m["save_gmail_state"].assert_called_once()

    def test_2fa_phase_reports_to_tiktok_chat(self):
        ret, m = self._run_main(["--lane", "tiktok", "--force"], batch_result=(0, self.TOTAL_OUT))
        self.assertEqual(ret, 0)
        m["run_gmail_batch"].assert_not_called()
        self.assertEqual(m["send_telegram_report"].call_args[0][0], "-5468653590")
        self.assertIn("BÁO CÁO 2FA TIKTOK BAN ĐÊM", m["send_telegram_report"].call_args[0][1])

    def test_gmail_failure_does_not_block_2fa(self):
        ret, m = self._run_main(["--force"], gmail_result=(1, ""), batch_result=(0, self.TOTAL_OUT))
        self.assertEqual(ret, 1)
        m["run_night_batch"].assert_called_once()
        self.assertEqual([c[0][0] for c in m["send_telegram_report"].call_args_list], ["-5139245637", "-5468653590"])

    def test_lane_selects_phases(self):
        for lane, (gc, bc) in {"gmail": (1, 0), "tiktok": (0, 1), "all": (1, 1)}.items():
            _, m = self._run_main(["--lane", lane, "--force"], gmail_result=(0, self.TOTAL_OUT), batch_result=(0, self.TOTAL_OUT))
            self.assertEqual((m["run_gmail_batch"].call_count, m["run_night_batch"].call_count), (gc, bc))

    def test_gmail_skipped_when_already_ran_tonight(self):
        ret, m = self._run_main(["--lane", "gmail"], gmail_result=(0, self.TOTAL_OUT), already_ran=True)
        self.assertEqual(ret, 0)
        m["run_gmail_batch"].assert_not_called()
        m["send_telegram_report"].assert_not_called()

    def test_state_file_records_both_lanes(self):
        import cron_night_tiktok_2fa_watchdog as wd
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_f = Path(tmp_dir) / "night_tiktok_2fa_state.json"
            with patch.object(wd, "STATE_FILE", tmp_f), patch.object(wd, "STATE_DIR", Path(tmp_dir)):
                wd.save_gmail_state("2026-10-20", {"status": "success", "code": 0})
                wd.save_state("2026-10-20", {"status": "partial_failure", "code": 0})
                saved = json.loads(tmp_f.read_text(encoding="utf-8"))
        self.assertEqual((saved["last_gmail_date"], saved["last_gmail_success"]), ("2026-10-20", True))
        self.assertEqual((saved["last_2fa_date"], saved["last_2fa_success"]), ("2026-10-20", False))
        self.assertEqual(saved["details"]["gmail"]["code"], 0)
        self.assertEqual(saved["details"]["2fa"]["status"], "partial_failure")


class TestSendTelegramReport(unittest.TestCase):
    @patch("cron_night_tiktok_2fa_watchdog._load_telegram_token", return_value="fake_tok")
    def test_send_telegram_report_paths(self, m_tok):
        import cron_night_tiktok_2fa_watchdog as wd
        with patch("automation_core.alerts._send_telegram_text", return_value=True) as m_send:
            self.assertTrue(wd.send_telegram_report("-5139245637", "Test msg"))
            m_send.assert_called_once_with("fake_tok", "-5139245637", "Test msg")

        with patch("automation_core.alerts._send_telegram_text", side_effect=Exception("net err")), patch("urllib.request.urlopen") as m_url:
            m_url.return_value.__enter__.return_value.status = 200
            self.assertTrue(wd.send_telegram_report("-5468653590", "Fallback"))
            self.assertIn(b"chat_id=-5468653590", m_url.call_args[0][0].data)

        with patch("cron_night_tiktok_2fa_watchdog._load_telegram_token", return_value=None), patch("urllib.request.urlopen") as m_url:
            self.assertFalse(wd.send_telegram_report("-5139245637", "No token"))
            m_url.assert_not_called()

        with patch("automation_core.alerts._send_telegram_text", return_value=False), patch("urllib.request.urlopen", side_effect=Exception("fatal")):
            self.assertFalse(wd.send_telegram_report("-5139245637", "Err"))

    def test_dispatch_report_success(self):
        import cron_night_tiktok_2fa_watchdog as wd
        with patch.object(wd, "send_telegram_report", return_value=True) as m_send:
            res = wd.dispatch_report("-5468653590", "ok message", dry_run=False)
            self.assertTrue(res)
            m_send.assert_called_once_with("-5468653590", "ok message")

    def test_dispatch_report_failure_logs_error_and_returns_false(self):
        import cron_night_tiktok_2fa_watchdog as wd
        with patch.object(wd, "send_telegram_report", return_value=False), patch.object(wd.logger, "error") as m_err:
            res = wd.dispatch_report("-5468653590", "fail message", dry_run=False)
            self.assertFalse(res)
            m_err.assert_called_once()
            self.assertIn("-5468653590", m_err.call_args[0][1])

    def test_dispatch_report_dry_run_returns_true_without_sending(self):
        import cron_night_tiktok_2fa_watchdog as wd
        with patch.object(wd, "send_telegram_report") as m_send:
            res = wd.dispatch_report("-5468653590", "dry run message", dry_run=True)
            self.assertTrue(res)
            m_send.assert_not_called()


class TestAtomicPhaseClaim(unittest.TestCase):
    def test_claim_lane_skips_when_active_and_reclaims_when_stale(self):
        import cron_night_tiktok_2fa_watchdog as wd
        import time
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_f = Path(tmp_dir) / "night_tiktok_2fa_state.json"
            with patch.object(wd, "STATE_FILE", tmp_f), patch.object(wd, "STATE_DIR", Path(tmp_dir)):
                # Initially not active, can claim
                self.assertTrue(wd.claim_lane("gmail", "2026-10-20"))
                saved = json.loads(tmp_f.read_text(encoding="utf-8"))
                self.assertIn("gmail_running_since", saved)

                # Active (< 5400s), second claim should skip
                self.assertFalse(wd.claim_lane("gmail", "2026-10-20"))

                # Release lane clears running_since
                wd.release_lane("gmail")
                saved_after_release = json.loads(tmp_f.read_text(encoding="utf-8"))
                self.assertNotIn("gmail_running_since", saved_after_release)

                # Stale claim (> 5400s) should reclaim
                tmp_f.write_text(json.dumps({"gmail_running_since": time.time() - 6000}), encoding="utf-8")
                self.assertTrue(wd.claim_lane("gmail", "2026-10-20"))

    def test_claim_lane_skips_when_already_ran_without_force(self):
        import cron_night_tiktok_2fa_watchdog as wd
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_f = Path(tmp_dir) / "night_tiktok_2fa_state.json"
            with patch.object(wd, "STATE_FILE", tmp_f), patch.object(wd, "STATE_DIR", Path(tmp_dir)):
                # Already ran gmail tonight
                tmp_f.write_text(json.dumps({"last_gmail_date": "2026-10-20", "last_gmail_success": True}), encoding="utf-8")
                self.assertFalse(wd.claim_lane("gmail", "2026-10-20", force=False))
                self.assertTrue(wd.claim_lane("gmail", "2026-10-20", force=True))


if __name__ == "__main__":
    unittest.main()


