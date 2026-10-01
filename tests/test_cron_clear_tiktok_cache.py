# -*- coding: utf-8 -*-
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add deploy scripts directory
SCRIPTS_DIR = Path("D:/Taadaa/Hermes/deploy/hermes-home/scripts")
sys.path.insert(0, str(SCRIPTS_DIR))


class TestCronClearTiktokCacheDualCluster(unittest.TestCase):
    def test_clusters_definition(self):
        import cron_clear_tiktok_cache as ctc
        self.assertTrue(hasattr(ctc, "CLUSTERS"), "Script must define CLUSTERS")
        cluster_names = [c["name"] for c in ctc.CLUSTERS]
        self.assertIn("kibe", cluster_names, "CLUSTERS must include 'kibe'")
        self.assertIn("admin", cluster_names, "CLUSTERS must include 'admin'")

        admin_cluster = next(c for c in ctc.CLUSTERS if c["name"] == "admin")
        self.assertIn("adb_socket", admin_cluster, "Admin cluster must specify adb_socket")
        self.assertEqual(admin_cluster["adb_socket"], "tcp:192.168.110.119:5037")

        kibe_cluster = next(c for c in ctc.CLUSTERS if c["name"] == "kibe")
        self.assertIsNone(kibe_cluster.get("adb_socket"), "Kibe cluster should not specify remote socket")

    def test_shared_state_disjoint_fleet_ranges_no_collision(self):
        import cron_clear_tiktok_cache as ctc
        ranges = {}
        for c in ctc.CLUSTERS:
            start, end = c["fleet_range"]
            s = set(range(start, end + 1))
            for other_name, other_set in ranges.items():
                collision = s & other_set
                self.assertEqual(
                    collision,
                    set(),
                    f"Fleet range collision detected between {c['name']} and {other_name}: {collision}",
                )
            ranges[c["name"]] = s

    @patch("openpyxl.load_workbook")
    def test_load_machine_serials_hermetic_parsing(self, mock_load_wb):
        import cron_clear_tiktok_cache as ctc
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.active = mock_ws
        # Mock rows: header, valid machine, out-of-range machine, invalid serial, empty row
        mock_ws.max_row = 5
        mock_ws.cell.side_effect = lambda r, c: MagicMock(
            value={
                (2, 1): 5, (2, 2): "s_valid_5",
                (3, 1): 205, (3, 2): "s_out_of_range",
                (4, 1): "invalid", (4, 2): "s_bad",
                (5, 1): None, (5, 2): None,
            }.get((r, c), None)
        )
        mock_load_wb.return_value = mock_wb

        with patch("os.path.exists", return_value=True):
            kibe_cluster = next(c for c in ctc.CLUSTERS if c["name"] == "kibe")
            serials = ctc.load_machine_serials(kibe_cluster)
            self.assertEqual(serials, [(5, "s_valid_5")])

    @patch("cron_clear_tiktok_cache.subprocess.run")
    @patch("cron_clear_tiktok_cache.DeviceLock")
    def test_clear_device_cache_admin_routing(self, mock_lock_cls, mock_subproc):
        import cron_clear_tiktok_cache as ctc
        mock_lock = MagicMock()
        mock_lock.__enter__.return_value = mock_lock
        mock_lock_cls.return_value = mock_lock

        # Mock child process success
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "OK"
        mock_proc.stderr = ""
        mock_subproc.return_value = mock_proc

        admin_cluster = next(c for c in ctc.CLUSTERS if c["name"] == "admin")
        res = ctc.clear_device_cache(201, "ce071827e07a093701", admin_cluster)

        self.assertEqual(len(res), 5, "clear_device_cache must return a 5-element tuple")
        m_num, serial, ok, msg, c_name = res
        self.assertTrue(ok)
        self.assertEqual(c_name, "admin")

        # Verify child command environment included ADB_SERVER_SOCKET
        child_call = mock_subproc.call_args_list[0]
        child_env = child_call[1].get("env", {})
        self.assertEqual(child_env.get("ADB_SERVER_SOCKET"), "tcp:192.168.110.119:5037")

        # Verify teardown adb call included host & port arguments
        teardown_call = mock_subproc.call_args_list[1]
        teardown_cmd = teardown_call[0][0]
        self.assertIn("-H", teardown_cmd)
        self.assertIn("192.168.110.119", teardown_cmd)
        self.assertIn("-P", teardown_cmd)
        self.assertIn("5037", teardown_cmd)

    @patch("cron_clear_tiktok_cache.subprocess.run")
    @patch("cron_clear_tiktok_cache.DeviceLock")
    def test_clear_device_cache_kibe_local(self, mock_lock_cls, mock_subproc):
        import cron_clear_tiktok_cache as ctc
        mock_lock = MagicMock()
        mock_lock.__enter__.return_value = mock_lock
        mock_lock_cls.return_value = mock_lock

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "OK"
        mock_proc.stderr = ""
        mock_subproc.return_value = mock_proc

        kibe_cluster = next(c for c in ctc.CLUSTERS if c["name"] == "kibe")
        res = ctc.clear_device_cache(1, "ce0616061a74682305", kibe_cluster)

        self.assertEqual(len(res), 5, "clear_device_cache must return a 5-element tuple")
        m_num, serial, ok, msg, c_name = res
        self.assertTrue(ok)
        self.assertEqual(c_name, "kibe")

        child_call = mock_subproc.call_args_list[0]
        child_env = child_call[1].get("env", {})
        self.assertIsNone(child_env.get("ADB_SERVER_SOCKET"))

        teardown_call = mock_subproc.call_args_list[1]
        teardown_cmd = teardown_call[0][0]
        self.assertNotIn("-H", teardown_cmd)

    @patch("cron_clear_tiktok_cache.subprocess.run")
    @patch("cron_clear_tiktok_cache.DeviceLock")
    def test_clear_device_cache_teardown_runs_on_child_failure(self, mock_lock_cls, mock_subproc):
        import cron_clear_tiktok_cache as ctc
        mock_lock = MagicMock()
        mock_lock.__enter__.return_value = mock_lock
        mock_lock_cls.return_value = mock_lock

        # Child process fails
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Script failed"
        mock_subproc.return_value = mock_proc

        admin_cluster = next(c for c in ctc.CLUSTERS if c["name"] == "admin")
        m_num, serial, ok, msg, c_name = ctc.clear_device_cache(201, "ce071827e07a093701", admin_cluster)

        self.assertFalse(ok)
        self.assertIn("[WARN]", msg)

        # Teardown must STILL have been executed (call index 1)
        self.assertEqual(len(mock_subproc.call_args_list), 2)
        teardown_cmd = mock_subproc.call_args_list[1][0][0]
        self.assertIn("am force-stop com.ss.android.ugc.trill;", teardown_cmd[teardown_cmd.index("shell") + 1])

    @patch("cron_clear_tiktok_cache.DeviceLock")
    def test_clear_device_cache_lock_contention(self, mock_lock_cls):
        import cron_clear_tiktok_cache as ctc
        from automation_core.device_lock import DeviceLockUnavailable
        mock_lock_cls.side_effect = DeviceLockUnavailable(Path("dummy.lock"), {"process": "feed"})

        kibe_cluster = next(c for c in ctc.CLUSTERS if c["name"] == "kibe")
        m_num, serial, ok, msg, c_name = ctc.clear_device_cache(1, "ce0616061a74682305", kibe_cluster)

        self.assertFalse(ok)
        self.assertIn("[LOCKED]", msg)
        self.assertEqual(c_name, "kibe")

    @patch("cron_clear_tiktok_cache.save_state")
    @patch("cron_clear_tiktok_cache.clear_device_cache")
    @patch("cron_clear_tiktok_cache.get_connected_devices")
    @patch("cron_clear_tiktok_cache.load_machine_serials")
    @patch("sys.argv", ["cron_clear_tiktok_cache.py", "--force", "--dry-run"])
    def test_dry_run_does_not_mutate_state(self, mock_load, mock_conn, mock_clear, mock_save):
        import cron_clear_tiktok_cache as ctc
        mock_conn.return_value = {"ce01": "device"}
        mock_load.return_value = [(1, "ce01")]

        rc = ctc.main()
        self.assertEqual(rc, 0)
        mock_save.assert_not_called()
        mock_clear.assert_not_called()

    @patch("cron_clear_tiktok_cache.save_state")
    @patch("cron_clear_tiktok_cache.clear_device_cache")
    @patch("cron_clear_tiktok_cache.get_connected_devices")
    @patch("cron_clear_tiktok_cache.load_machine_serials")
    @patch("cron_clear_tiktok_cache.load_state")
    @patch("sys.argv", ["cron_clear_tiktok_cache.py", "--force"])
    def test_main_dual_cluster_execution_and_retry_on_failure(
        self, mock_load_state, mock_load, mock_conn, mock_clear, mock_save
    ):
        import cron_clear_tiktok_cache as ctc
        mock_load_state.return_value = {
            "last_date": "2026-09-29",
            "cleared_machines": [],
            "machine_retries": {},
            "reported_date": None,
        }

        # Include an extra unassigned serial in ADB connected to test fleet filtering
        def fake_conn(cluster):
            if cluster["name"] == "kibe":
                return {"kibe_s1": "device", "unrelated_serial": "device"}
            return {"admin_s1": "device"}
        mock_conn.side_effect = fake_conn

        def fake_serials(cluster):
            return [(1, "kibe_s1")] if cluster["name"] == "kibe" else [(201, "admin_s1")]
        mock_load.side_effect = fake_serials

        def fake_clear(m, s, cluster):
            if m == 1:
                return m, s, True, "Cleared ok", cluster["name"]
            return m, s, False, "[WARN] Machine 201: Timeout", cluster["name"]
        mock_clear.side_effect = fake_clear

        rc = ctc.main()
        self.assertEqual(rc, 0)

        # Retry counter must only be incremented for failed machine (201)
        save_calls = mock_save.call_args_list
        self.assertGreater(len(save_calls), 0)
        final_state = save_calls[-1][0][0]
        self.assertEqual(final_state["machine_retries"].get("201"), 1)
        self.assertNotIn("1", final_state["machine_retries"])
        self.assertIn(1, final_state["cleared_machines"])

        # Cluster stats telemetry recorded with comprehensive observability fields
        self.assertIn("cluster_stats", final_state)
        kibe_stats = final_state["cluster_stats"]["kibe"]
        admin_stats = final_state["cluster_stats"]["admin"]
        self.assertEqual(kibe_stats["fleet_total"], 1)
        self.assertEqual(kibe_stats["online_count"], 1)
        self.assertEqual(kibe_stats["cleared_count"], 1)
        self.assertEqual(kibe_stats["batch_success"], 1)
        self.assertEqual(kibe_stats["batch_failed"], 0)

        self.assertEqual(admin_stats["fleet_total"], 1)
        self.assertEqual(admin_stats["online_count"], 1)
        self.assertEqual(admin_stats["cleared_count"], 0)
        self.assertEqual(admin_stats["batch_success"], 0)
        self.assertEqual(admin_stats["batch_failed"], 1)

    @patch("cron_clear_tiktok_cache.print")
    @patch("cron_clear_tiktok_cache.save_state")
    @patch("cron_clear_tiktok_cache.clear_device_cache")
    @patch("cron_clear_tiktok_cache.get_connected_devices")
    @patch("cron_clear_tiktok_cache.load_machine_serials")
    @patch("cron_clear_tiktok_cache.load_state")
    @patch("sys.argv", ["cron_clear_tiktok_cache.py", "--force"])
    def test_completion_condition_no_false_positive_when_offline_cleared_earlier(
        self, mock_load_state, mock_load, mock_conn, mock_clear, mock_save, mock_print
    ):
        """
        Scenario:
        Machine 1 was cleared earlier and went offline.
        Machine 2 is currently online, but NOT yet cleared.
        Even though len(cleared_today) == 1 and len(online) == 1,
        the system must NOT falsely declare 'Toàn farm hoàn tất'.
        """
        import cron_clear_tiktok_cache as ctc
        mock_load_state.return_value = {
            "last_date": "2026-09-29",
            "cleared_machines": [1],  # 1 was cleared earlier
            "machine_retries": {"2": 2},  # 2 already hit max retries, so target_machines empty
            "reported_date": "2026-09-29",  # already reported earlier
        }

        # Only Machine 2 is currently online (Machine 1 is offline)
        def fake_conn(cluster):
            if cluster["name"] == "kibe":
                return {"kibe_s2": "device"}
            return {}
        mock_conn.side_effect = fake_conn

        def fake_serials(cluster):
            if cluster["name"] == "kibe":
                return [(1, "kibe_s1"), (2, "kibe_s2")]
            return []
        mock_load.side_effect = fake_serials

        rc = ctc.main()
        self.assertEqual(rc, 0)

        # Because Machine 2 is online and NOT in cleared_today, it must not print 'Toàn farm online ... đã hoàn tất'
        for call in mock_print.call_args_list:
            printed_text = call[0][0]
            self.assertNotIn("đã hoàn tất", printed_text)

    @patch("cron_clear_tiktok_cache.print")
    @patch("cron_clear_tiktok_cache.save_state")
    @patch("cron_clear_tiktok_cache.clear_device_cache")
    @patch("cron_clear_tiktok_cache.get_connected_devices")
    @patch("cron_clear_tiktok_cache.load_machine_serials")
    @patch("cron_clear_tiktok_cache.load_state")
    @patch("sys.argv", ["cron_clear_tiktok_cache.py", "--force"])
    def test_report_format_simplified(self, mock_ls, mock_lms, mock_cd, mock_cdc, mock_ss, mock_p):
        import cron_clear_tiktok_cache as ctc
        mock_ls.return_value = {"last_date": "2026-10-02", "cleared_machines": [], "machine_retries": {}, "reported_date": None}
        mock_cd.side_effect = lambda cl: {"ce01": "device"} if cl["name"] == "kibe" else {}
        mock_lms.side_effect = lambda cl: [(1, "ce01")] if cl["name"] == "kibe" else []
        mock_cdc.side_effect = lambda m, s, cl: (m, s, True, "OK", cl["name"])
        ctc.main()
        out = "\n".join(call[0][0] for call in mock_p.call_args_list)
        self.assertIn("• Đã hoàn tất: 1 máy", out)
        self.assertIn("• Lỗi (0)", out)


if __name__ == "__main__":
    unittest.main()
