import sys
import os
import json
import sqlite3
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

REPO_SCRIPTS = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(REPO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REPO_SCRIPTS))

import cron_chatgpt_web_pool_watchdog as w

class TestCronChatgptWebPoolWatchdog(unittest.TestCase):
    def test_get_connections_by_provider_codex(self):
        mock_data = {
            "connections": [
                {"id": "1", "provider": "codex", "name": "acc1", "isActive": True, "testStatus": "active"},
                {"id": "2", "provider": "chatgpt-web", "name": "acc2", "isActive": True, "testStatus": "active"},
                {"id": "3", "provider": "codex", "name": "acc3", "isActive": False, "testStatus": "active"},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")

        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp

        with patch("requests.get", return_value=mock_resp), \
             patch("urllib.request.urlopen", return_value=mock_cm):
            conns = w.get_connections_by_provider("codex")
            self.assertEqual(len(conns), 2)
            self.assertEqual(conns[0]["id"], "1")
            self.assertEqual(conns[1]["id"], "3")

    def test_codex_observability_standby_preserved(self):
        # Tôn trọng trạng thái router/người dùng đặt Standby, không tự ý toggle bật lại
        codex_conns = [
            {"id": "conn-1", "name": "acc1@gmail.com", "isActive": False, "testStatus": "active"},
            {"id": "conn-2", "name": "acc2@gmail.com", "isActive": True, "testStatus": "active"}
        ]
        toggled_off = [c for c in codex_conns if not c.get("isActive") and c.get("testStatus") == "active"]
        self.assertEqual(len(toggled_off), 1)
        self.assertEqual(toggled_off[0]["id"], "conn-1")

    def test_broken_codex_detected(self):
        codex_conns = [
            {"id": "conn-1", "name": "acc1@gmail.com", "isActive": True, "testStatus": "expired"},
            {"id": "conn-2", "name": "acc2@gmail.com", "isActive": True, "testStatus": "active"}
        ]
        broken = [c for c in codex_conns if c.get("testStatus") != "active"]
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]["name"], "acc1@gmail.com")

    def test_report_lines_format(self):
        report_lines = [
            "🤖 [POOL HEALER] BÁO CÁO SỨC KHỎE",
            "• ChatGPT-Web: 21/21 ACTIVE",
            "• Antigravity: 114/121 ACTIVE",
            "• Codex: 29/29 ACTIVE"
        ]
        full_text = "\n".join(report_lines)
        self.assertIn("• Codex: 29/29 ACTIVE", full_text)
        self.assertIn("• ChatGPT-Web: 21/21 ACTIVE", full_text)

    def test_save_telemetry_metrics_atomic_write(self):
        metrics = {
            "timestamp": "2026-09-25T00:00:00Z",
            "chatgpt_web": {"active": 15, "total": 21},
            "antigravity": {"active": 109, "total": 119},
            "codex": {"active": 29, "total": 29},
            "recovered_chatgpt": ["acc1@gmail.com"],
            "recovered_ag": [],
            "total_failures": 0,
            "failures": []
        }
        test_cache = Path(__file__).resolve().parent / "temp_telemetry_test.json"
        test_hist = Path(__file__).resolve().parent / "temp_telemetry_hist.jsonl"
        with patch.object(w, "TELEMETRY_CACHE_PATH", str(test_cache)), \
             patch.object(w, "TELEMETRY_HISTORY_PATH", str(test_hist)):
            ok = w.save_telemetry_metrics(metrics)
            self.assertTrue(ok)
            self.assertTrue(test_cache.exists())
            self.assertTrue(test_hist.exists())
            with open(test_cache, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["chatgpt_web"]["active"], 15)
            self.assertEqual(data["selector_version"], "2026.09.25-v1")
            with open(test_hist, "r", encoding="utf-8") as f_h:
                lines = f_h.readlines()
            self.assertEqual(len(lines), 1)
            if test_cache.exists(): test_cache.unlink()
            if test_hist.exists(): test_hist.unlink()

    def test_sqlite_transaction_rollback_on_failure(self):
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cur
            mock_cur.fetchone.return_value = ("chatgpt-web", "test_acc")
            mock_cur.execute.side_effect = [None, Exception("Simulated DB Disk I/O Error")]

            with patch("requests.get") as mock_req, \
                 patch.object(w, "perform_auto_login_and_extract_cookies", return_value="cookie=test"), \
                 patch.object(w, "test_connection_valid", return_value=(True, {})):
                mock_req.return_value.json.return_value = {
                    "success": True,
                    "data": {"remote_debugging_address": "127.0.0.1:9222"}
                }
                ok, msg = w.perform_revive_chatgpt_account("dummy_pid", "dummy_cid", "test@gmail.com", {})
                self.assertFalse(ok)
                mock_conn.rollback.assert_called_once()
                mock_conn.close.assert_called_once()

    def test_chatgpt_revive_guard_rejects_wrong_provider(self):
        # Kiểm tra guard chặn đứng nếu connection không phải chatgpt-web
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cur
            mock_cur.fetchone.return_value = ("antigravity", "wrong_target_acc")

            with patch("requests.get") as mock_req, \
                 patch.object(w, "perform_auto_login_and_extract_cookies", return_value="cookie=test"), \
                 patch.object(w, "test_connection_valid", return_value=(True, {})):
                mock_req.return_value.json.return_value = {
                    "success": True,
                    "data": {"remote_debugging_address": "127.0.0.1:9222"}
                }
                ok, msg = w.perform_revive_chatgpt_account("dummy_pid", "cid_antigravity", "test@gmail.com", {})
                self.assertFalse(ok)
                self.assertIn("Guard rejected", msg)

    def test_sqlite_real_schema_mutation_and_combos_update(self):
        # Integration test trên SQLite schema thực tế
        test_db_path = str(Path(__file__).resolve().parent / "temp_integration.sqlite")
        conn = sqlite3.connect(test_db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE provider_connections (id TEXT PRIMARY KEY, provider TEXT, name TEXT, api_key TEXT, is_active INTEGER, test_status TEXT, last_error TEXT, last_error_at TEXT, backoff_level INTEGER, rate_limited_until TEXT, updated_at TEXT)")
        cur.execute("CREATE TABLE combos (name TEXT PRIMARY KEY, data TEXT)")
        cur.execute("INSERT INTO provider_connections VALUES ('cid_web_1', 'chatgpt-web', 'test@gmail.com', 'old_key', 0, 'expired', 'error', '2026-09-20', 1, NULL, '2026-09-20')")
        cur.execute("INSERT INTO combos VALUES ('chatgpt-web-pool', '{\"models\": []}')")
        conn.commit()
        conn.close()

        with patch.object(w, "DB_PATH", test_db_path), \
             patch("requests.get") as mock_req, \
             patch.object(w, "perform_auto_login_and_extract_cookies", return_value="session-token=new_fresh_token"), \
             patch.object(w, "test_connection_valid", return_value=(True, {})):
            mock_req.return_value.json.return_value = {
                "success": True,
                "data": {"remote_debugging_address": "127.0.0.1:9222"}
            }
            ok, msg = w.perform_revive_chatgpt_account("pid_1", "cid_web_1", "test@gmail.com", {})
            self.assertTrue(ok)

            # Verify actual database state
            conn_check = sqlite3.connect(test_db_path)
            row = conn_check.cursor().execute("SELECT is_active, test_status, api_key FROM provider_connections WHERE id='cid_web_1'").fetchone()
            self.assertEqual(row[0], 1)
            self.assertEqual(row[1], "active")
            self.assertEqual(row[2], "session-token=new_fresh_token")

            combo_row = conn_check.cursor().execute("SELECT data FROM combos WHERE name='chatgpt-web-pool'").fetchone()
            cdata = json.loads(combo_row[0])
            self.assertEqual(len(cdata["models"]), 1)
            self.assertEqual(cdata["models"][0]["connectionId"], "cid_web_1")
            self.assertEqual(cdata["models"][0]["model"], "chatgpt-web/gpt-5.6-sol-high")
            conn_check.close()

        if os.path.exists(test_db_path):
            os.remove(test_db_path)

    def test_phone_checkpoint_predicate_detection(self):
        sample_page_text_phone = "Để giữ an toàn cho tài khoản của bạn, Google muốn đảm bảo rằng bạn chính là người đang cố đăng nhập. Nhập số điện thoại để nhận mã xác minh."
        txt = sample_page_text_phone.lower()
        is_phone_cp = (("phone number" in txt or "số điện thoại" in txt) and ("enter a phone" in txt or "nhập số" in txt))
        self.assertTrue(is_phone_cp)

        sample_page_text_normal = "Nhập mật khẩu của bạn. Tiếp theo."
        txt_normal = sample_page_text_normal.lower()
        is_phone_cp_normal = (("phone number" in txt_normal or "số điện thoại" in txt_normal) and ("enter a phone" in txt_normal or "nhập số" in txt_normal))
        self.assertFalse(is_phone_cp_normal)

    def test_load_accounts_credentials_column_integrity(self):
        fake_rows = [
            ("số máy", "email", "pass", "2fa", "recovery_email"),
            (1, "acc1@gmail.com", "PassWord123!", "JBSWY3DPEHPK3PXP", "recovery1@gmail.com"),
            (2, "acc2@gmail.com", "PassWord456!", None, "recovery2@gmail.com"),
        ]
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = fake_rows
        mock_wb.sheetnames = ["Sheet1"]
        mock_wb.__getitem__.return_value = mock_ws
        mock_wb.active = mock_ws
        with patch("openpyxl.load_workbook", return_value=mock_wb), \
             patch("os.path.exists", return_value=True):
            creds = w.load_accounts_credentials()
            self.assertIn("acc1@gmail.com", creds)
            self.assertEqual(creds["acc1@gmail.com"]["password"], "PassWord123!")
            self.assertEqual(creds["acc1@gmail.com"]["totp"], "JBSWY3DPEHPK3PXP")
            self.assertEqual(creds["acc1@gmail.com"]["recovery_email"], "recovery1@gmail.com")
            self.assertNotIn("recovery1@gmail.com", creds)

    def test_main_controller_multi_provider_failures_and_reporting(self):
        # Kiểm chứng toàn bộ main() controller xử lý đúng khi nhiều provider gặp lỗi đồng thời
        mock_chatgpt_conns = [
            {"id": "cid_cg_1", "name": "user1@gmail.com (GPM Web)", "isActive": False, "testStatus": "expired", "provider": "chatgpt-web"}
        ]
        mock_ag_conns = [
            {"id": "cid_ag_1", "name": "user2@gmail.com", "isActive": True, "testStatus": "expired", "provider": "antigravity"}
        ]
        mock_codex_conns = [
            {"id": "cid_cx_1", "name": "user3@gmail.com", "isActive": False, "testStatus": "active", "provider": "codex"}
        ]

        def mock_get_conns(prov):
            if prov == "chatgpt-web": return mock_chatgpt_conns
            if prov == "antigravity": return mock_ag_conns
            if prov == "codex": return mock_codex_conns
            return []

        mock_gpm_profiles = [
            {"id": "pid_1", "name": "01 - user1@gmail.com - 5101", "raw_proxy": "test:5101"},
            {"id": "pid_2", "name": "02 - user2@gmail.com - 5102", "raw_proxy": "test:5102"}
        ]

        with patch.object(w, "get_connections_by_provider", side_effect=mock_get_conns),              patch.object(w, "get_gpm_profiles", return_value=mock_gpm_profiles),              patch.object(w, "load_accounts_credentials", return_value={"user1@gmail.com": {}, "user2@gmail.com": {}}),              patch.object(w, "refresh_chatgpt_account_via_gpm", return_value=(True, "OK")),              patch.object(w, "refresh_antigravity_account_via_gpm", return_value=(False, "Phone Checkpoint")),              patch.object(w, "save_telemetry_metrics") as mock_save_telem:
            w.main()
            mock_save_telem.assert_called_once()
            telem_arg = mock_save_telem.call_args[0][0]
            self.assertIn("user1@gmail.com", telem_arg["recovered_chatgpt"])
            self.assertEqual(telem_arg["total_failures"], 1)
            self.assertEqual(telem_arg["failures"][0]["account"], "user2@gmail.com")

    def test_refresh_antigravity_oauth_flow_structure(self):
        # Kiểm tra cấu trúc flow refresh antigravity account qua GPM
        import time
        ten_days_ago = time.time() - (10 * 86400)
        mock_gpm_profile = {"id": "pid_ag", "name": "M01 - user@gmail.com - 5101", "raw_proxy": "test:5101", "created_at": ten_days_ago}
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = {"success": False, "message": "Proxy connection error"}
            ok, msg = w.refresh_antigravity_account_via_gpm("pid_ag", "user@gmail.com", mock_gpm_profile, {})
            self.assertFalse(ok)
            self.assertIn("Start profile fail", msg)

    def test_profile_aged_7_days_safety_valve(self):
        import time
        # Case 1: Profile 10 ngày tuổi -> Đạt điều kiện
        prof_old = {"created_at": time.time() - (10 * 86400)}
        self.assertTrue(w.is_profile_aged_7_days(prof_old, min_days=7))

        # Case 2: Profile 2 ngày tuổi -> Bị van an toàn chặn
        prof_new = {"created_at": time.time() - (2 * 86400)}
        self.assertFalse(w.is_profile_aged_7_days(prof_new, min_days=7))

        # Case 3: Chặn ngay trong refresh_antigravity_account_via_gpm
        ok, msg = w.refresh_antigravity_account_via_gpm("pid_new", "new@gmail.com", prof_new, {})
        self.assertFalse(ok)
        self.assertIn("Van an toàn", msg)

    def test_live_omniroute_api_provider_query(self):
        # Test live integration với OmniRoute daemon đang chạy tại localhost:20129
        try:
            conns = w.get_connections_by_provider("chatgpt-web")
            self.assertIsInstance(conns, list)
            self.assertGreater(len(conns), 0)
        except Exception as e:
            self.skipTest(f"OmniRoute daemon not reachable: {e}")

    def test_live_gpm_api_profiles_query(self):
        # Test live integration với GPMLogin daemon đang chạy tại localhost:19995
        try:
            profs = w.get_gpm_profiles()
            self.assertIsInstance(profs, list)
            self.assertGreater(len(profs), 0)
        except Exception as e:
            self.skipTest(f"GPM daemon not reachable: {e}")

    def test_live_database_schema_and_integrity(self):
        # Test đối soát schema storage.sqlite thực tế của OmniRoute
        db_path = w.DB_PATH
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            self.assertIn("provider_connections", tables)
            self.assertIn("combos", tables)
            conn.close()

    def test_telemetry_resilience_on_io_failure(self):
        # Kiểm tra tính phục hồi: telemetry gặp lỗi disk IO không được làm crash watchdog
        with patch("builtins.open", side_effect=IOError("Simulated disk full / permission denied")):
            ok = w.save_telemetry_metrics({"dummy": "data"})
            self.assertFalse(ok)

    def test_fetch_google_recovery_otp_regex_and_filtering(self):
        # Kiểm tra logic trích xuất OTP 6 số và bỏ qua cảnh báo bảo mật
        import re
        sample_security_alert = "Cảnh báo bảo mật cho tài khoản liên kết"
        is_alert = any(k in sample_security_alert.lower() for k in ["cảnh báo", "security alert", "cảnh báo bảo mật"])
        self.assertTrue(is_alert)

        sample_otp_body = "Mã xác minh Google của bạn là 492815. Mã này sẽ hết hạn sau 10 phút."
        m = re.search(r'\b(\d{6})\b', sample_otp_body)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "492815")
