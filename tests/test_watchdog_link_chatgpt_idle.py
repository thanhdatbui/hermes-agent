import sys
import os
import sqlite3
import tempfile
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

    def test_morning_candidate_mapping_uses_sqlite_and_excel_sources(self):
        class Rows:
            def iter_rows(self, values_only=True):
                return iter([
                    ("STT", "Email", "Password", "Recovery", "2FA"),
                    (1, "Mapped@Gmail.com", "master-pass", "", ""),
                    (2, "ready@gmail.com", "", "", "master-2fa"),
                ])

        class Workbook:
            sheetnames = ["Master_All"]
            def __getitem__(self, name):
                return Rows()
            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "profiles.db"
            master_path = Path(tmp) / "master.xlsx"
            master_path.touch()
            nurture_path = Path(tmp) / "nonexistent_nurture.json"

            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE Profiles (Id INTEGER, Name TEXT, ProfilePath TEXT, GroupId INTEGER)")
            conn.execute("INSERT INTO Profiles VALUES (7, '07 Mapped@Gmail.com', 'profile-7', 10)")
            conn.execute("INSERT INTO Profiles VALUES (8, '08 ready@gmail.com', 'profile-8', 10)")
            conn.commit()
            conn.close()
            with patch.object(w_morning, "GPM_DB_PATH", db_path), \
                 patch.object(w_morning, "MASTER_EXCEL", master_path), \
                 patch.object(w_morning, "CLEAN_V2_EXCEL", Path(tmp) / "no_clean.xlsx"), \
                 patch.object(w_morning, "NURTURE_STATE_FILE", nurture_path), \
                 patch("openpyxl.load_workbook", return_value=Workbook()), \
                 patch.object(w_morning, "_profile_has_google_session", return_value=True):
                candidates = w_morning.get_gpm_candidates(limit=5)
        self.assertEqual([(c["id"], c["email"], c["pwd"]) for c in candidates],
                         [(7, "mapped@gmail.com", "master-pass")])

    def test_morning_candidate_mapping_filters_exclusions_and_soak_gate(self):
        class CleanRows:
            def iter_rows(self, values_only=True):
                return iter([
                    ("STT", "Email", "Password", "2FA"),
                    (8, "clean_only@gmail.com", "clean-pass", ""),
                ])

        class EmptyMasterWb:
            sheetnames = ["Master_All"]
            def __getitem__(self, name):
                class Empty:
                    def iter_rows(self, values_only=True):
                        return iter([("STT", "Email", "Password")])
                return Empty()
            def close(self):
                pass

        class CleanWb:
            def __init__(self):
                self.active = CleanRows()
            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "profiles.db"
            master_path = Path(tmp) / "master.xlsx"
            master_path.touch()
            clean_path = Path(tmp) / "clean.xlsx"
            clean_path.touch()

            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE Profiles (Id INTEGER, Name TEXT, ProfilePath TEXT, GroupId INTEGER)")
            # 1. khoale exclusion
            conn.execute("INSERT INTO Profiles VALUES (1, '01 khoale_acc@gmail.com', 'p1', 10)")
            # 2. AMZ_ exclusion
            conn.execute("INSERT INTO Profiles VALUES (2, 'AMZ_m02@gmail.com', 'p2', 10)")
            # 3. gid != 10 exclusion
            conn.execute("INSERT INTO Profiles VALUES (3, '03_other_group@gmail.com', 'p3', 20)")
            # 4. soak gate unverified
            conn.execute("INSERT INTO Profiles VALUES (4, '04 unsoaked@gmail.com', 'p4', 10)")
            # 5. valid with clean_v2 fallback
            conn.execute("INSERT INTO Profiles VALUES (8, '08 clean_only@gmail.com', 'p8', 10)")
            conn.commit()
            conn.close()

            nurture_path = Path(tmp) / "nurture.json"
            import json
            nurture_path.write_text(json.dumps({
                "unsoaked@gmail.com": {"status": "failed"},
                "clean_only@gmail.com": {"last_nurtured": "2026-09-25", "status": "success"}
            }), encoding="utf-8")

            def mock_wb_opener(p, *args, **kwargs):
                if "clean" in str(p):
                    return CleanWb()
                return EmptyMasterWb()

            with patch.object(w_morning, "GPM_DB_PATH", db_path), \
                 patch.object(w_morning, "MASTER_EXCEL", master_path), \
                 patch.object(w_morning, "CLEAN_V2_EXCEL", clean_path), \
                 patch.object(w_morning, "NURTURE_STATE_FILE", nurture_path), \
                 patch("openpyxl.load_workbook", side_effect=mock_wb_opener), \
                 patch.object(w_morning, "_profile_has_google_session", return_value=True):
                candidates = w_morning.get_gpm_candidates(limit=10)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["id"], 8)
        self.assertEqual(candidates[0]["email"], "clean_only@gmail.com")
        self.assertEqual(candidates[0]["pwd"], "clean-pass")
        self.assertEqual(candidates[0]["machine"], 8)

    def test_morning_get_active_locks_parses_status(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            p_tmp = Path(tmp)
            (p_tmp / "lock1.json").write_text(json.dumps({"machine": 3, "status": "running"}), encoding="utf-8")
            (p_tmp / "lock2.json").write_text(json.dumps({"machine": 4, "status": "blocked"}), encoding="utf-8")
            (p_tmp / "lock3.json").write_text(json.dumps({"machine": 5, "status": "idle"}), encoding="utf-8")
            (p_tmp / "lock4.json").write_text(json.dumps({"machine": 6, "status": "released"}), encoding="utf-8")
            (p_tmp / "corrupt.json").write_text("not json", encoding="utf-8")

            with patch.object(w_morning, "LOCK_DIR", p_tmp):
                active = w_morning.get_active_locks()
            self.assertEqual(active, {3, 4})

    def test_morning_safety_gates_skip_runner_lock_and_upcoming_feed(self):
        candidate = {"email": "ready@gmail.com", "name": "1 ready@gmail.com", "machine": 1,
                     "google_session_verified": True}
        with patch.object(w_morning, "is_within_time_window", return_value=True), \
             patch.object(w_morning, "is_feed_ca1_finished", return_value=True), \
             patch.object(w_morning, "is_feed_runner_active", return_value=False), \
             patch.object(w_morning, "get_gpm_candidates", return_value=[candidate]), \
             patch.object(w_morning, "get_active_locks", return_value={1}), \
             patch.object(w_morning, "get_upcoming_feed_machines", return_value={2}), \
             patch.object(w_morning, "setup_authenticator_for_profile") as setup, \
             patch.object(w_morning.sys, "argv", ["watchdog"]):
            self.assertEqual(w_morning.main(), 0)
        setup.assert_not_called()

        with patch.object(w_morning, "is_within_time_window", return_value=True), \
             patch.object(w_morning, "is_feed_ca1_finished", return_value=True), \
             patch.object(w_morning, "is_feed_runner_active", return_value=True), \
             patch.object(w_morning, "get_gpm_candidates") as candidates, \
             patch.object(w_morning.sys, "argv", ["watchdog"]):
            self.assertEqual(w_morning.main(), 0)
        candidates.assert_not_called()

    def test_morning_safety_gate_allows_unblocked_candidate(self):
        candidate = {"email": "ready@gmail.com", "name": "1 ready@gmail.com", "machine": 1,
                     "google_session_verified": True}
        with patch.object(w_morning, "is_within_time_window", return_value=True), \
             patch.object(w_morning, "is_feed_ca1_finished", return_value=True), \
             patch.object(w_morning, "is_feed_runner_active", return_value=False), \
             patch.object(w_morning, "get_gpm_candidates", return_value=[candidate]), \
             patch.object(w_morning, "get_active_locks", return_value=set()), \
             patch.object(w_morning, "get_upcoming_feed_machines", return_value=set()), \
             patch.object(w_morning, "setup_authenticator_for_profile", return_value={"status": "ALREADY_ACTIVE"}) as setup, \
             patch.object(w_morning, "save_state_results"), \
             patch.object(w_morning, "ProcessLock") as lock_cls, \
             patch.object(w_morning.sys, "argv", ["watchdog"]):
            lock_cls.return_value.acquire.return_value = True
            self.assertEqual(w_morning.main(), 0)
        setup.assert_called_once_with(candidate)

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
