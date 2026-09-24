import unittest
import sys
import os

# Add scripts directory to sys.path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from unittest.mock import patch, MagicMock
from feed_session_watchdog import (
    is_device_locked_skip,
    merge_machine_result,
    can_report_session,
    _add_minutes_to_hm,
    is_feed_runner_active,
)


class TestFeedSessionWatchdogLockGuard(unittest.TestCase):
    def test_is_device_locked_skip(self):
        # None and empty cases
        self.assertFalse(is_device_locked_skip(None))
        self.assertFalse(is_device_locked_skip({}))

        # Normal runs
        self.assertFalse(is_device_locked_skip({"status": "success", "reason": ""}))
        self.assertFalse(is_device_locked_skip({"status": "fail", "reason": "app_crash"}))
        self.assertFalse(is_device_locked_skip({"status": "error", "reason": "network_timeout"}))

        # Direct status
        self.assertTrue(is_device_locked_skip({"status": "skipped-device-locked"}))
        self.assertTrue(is_device_locked_skip({"status": "SKIPPED-DEVICE-LOCKED"}))

        # Reason contains device-lock / device lock active
        self.assertTrue(is_device_locked_skip({"status": "fail", "reason": "device-lock: machine 10 busy"}))
        self.assertTrue(is_device_locked_skip({"status": "fail", "reason": "Device lock active on slot 1"}))
        self.assertTrue(is_device_locked_skip({"status": "skipped", "reason": "DEVICE-LOCK in use"}))

    def test_merge_machine_result(self):
        real_fail = {"status": "fail", "reason": "crash"}
        locked_fail = {"status": "skipped-device-locked", "reason": "device lock active"}
        success = {"status": "success", "reason": ""}

        # None handling
        self.assertEqual(merge_machine_result(None, real_fail), real_fail)
        self.assertEqual(merge_machine_result(real_fail, None), real_fail)

        # Success takes priority
        self.assertEqual(merge_machine_result(success, real_fail), success)
        self.assertEqual(merge_machine_result(real_fail, success), success)
        self.assertEqual(merge_machine_result(success, locked_fail), success)
        self.assertEqual(merge_machine_result(locked_fail, success), success)

        # Real run prioritized over lock
        self.assertEqual(merge_machine_result(locked_fail, real_fail), real_fail)
        self.assertEqual(merge_machine_result(real_fail, locked_fail), real_fail)

        # Both locked or both real fail -> new takes precedence
        new_locked = {"status": "skipped-device-locked", "reason": "device-lock new"}
        self.assertEqual(merge_machine_result(locked_fail, new_locked), new_locked)

        new_real_fail = {"status": "fail", "reason": "timeout"}
        self.assertEqual(merge_machine_result(real_fail, new_real_fail), new_real_fail)

        # Merge feed_counts, likes, swipes
        p_data = {
            "status": "fail",
            "likes": {"for-you": 10, "following": 2},
            "feed_counts": {"for-you": 100, "following": 20},
            "swipes": 120,
        }
        n_data = {
            "status": "success",
            "likes": {"for-you": 15, "friends": 5},
            "feed_counts": {"for-you": 150, "friends": 50},
            "swipes": 200,
        }
        merged = merge_machine_result(p_data, n_data)
        self.assertEqual(merged["status"], "success")
        self.assertEqual(merged["likes"], {"for-you": 15, "following": 2, "friends": 5})
        self.assertEqual(merged["feed_counts"], {"for-you": 150, "following": 20, "friends": 50})
        self.assertEqual(merged["swipes"], 200)

    def test_feed_counts_tab_rate_calculation(self):
        # Kiểm tra tính tỷ lệ like từng tab khi có feed_counts
        all_machines = {
            "1": {
                "status": "success",
                "swipes": 100,
                "likes": {"for-you": 10, "friends": 5, "following": 2},
                "feed_counts": {"for-you": 80, "friends": 15, "following": 5},
            },
            "2": {
                "status": "success",
                "swipes": 200,
                "likes": {"for-you": 20, "friends": 10, "following": 3},
                "feed_counts": {"for-you": 160, "friends": 25, "following": 15},
            },
            "3": {
                "status": "fail",
                "swipes": 50,
                "likes": {"for-you": 5},
                "feed_counts": {"for-you": 50},
            },
        }

        # Chỉ tính trên machines có status == 'success'
        succ_machines = [d for d in all_machines.values() if d.get("status") == "success"]
        tot_fy_likes = sum(d.get("likes", {}).get("for-you", 0) for d in succ_machines)
        tot_fl_likes = sum(d.get("likes", {}).get("following", 0) for d in succ_machines)
        tot_fr_likes = sum(d.get("likes", {}).get("friends", 0) for d in succ_machines)

        tot_fy_swipes = sum(d.get("feed_counts", {}).get("for-you", 0) for d in succ_machines)
        tot_fl_swipes = sum(d.get("feed_counts", {}).get("following", 0) for d in succ_machines)
        tot_fr_swipes = sum(d.get("feed_counts", {}).get("friends", 0) for d in succ_machines)

        self.assertEqual(tot_fy_likes, 30)
        self.assertEqual(tot_fy_swipes, 240)
        self.assertEqual(tot_fl_likes, 5)
        self.assertEqual(tot_fl_swipes, 20)
        self.assertEqual(tot_fr_likes, 15)
        self.assertEqual(tot_fr_swipes, 40)

        fy_rate_str = f"{(tot_fy_likes / tot_fy_swipes * 100.0):.1f}%" if tot_fy_swipes > 0 else "0.0%"
        fl_rate_str = f"{(tot_fl_likes / tot_fl_swipes * 100.0):.1f}%" if tot_fl_swipes > 0 else "0.0%"
        fr_rate_str = f"{(tot_fr_likes / tot_fr_swipes * 100.0):.1f}%" if tot_fr_swipes > 0 else "0.0%"

        self.assertEqual(fy_rate_str, "12.5%")
        self.assertEqual(fl_rate_str, "25.0%")
        self.assertEqual(fr_rate_str, "37.5%")

    def test_add_minutes_to_hm(self):
        self.assertEqual(_add_minutes_to_hm("07:30", 20), "07:50")
        self.assertEqual(_add_minutes_to_hm("23:50", 20), "00:10")
        self.assertEqual(_add_minutes_to_hm("00:00", 60), "01:00")
        self.assertEqual(_add_minutes_to_hm("15:45", 15), "16:00")

    def test_can_report_session(self):
        # 1. Tất cả máy dự kiến đã hoàn tất thật và runner không còn bận -> chốt ngay
        self.assertTrue(can_report_session(
            is_today=True,
            completed_expected_count=80,
            expected_count=80,
            now_hm="07:00",
            window_end_hm="07:30",
            runner_busy=False,
            has_unattempted_locked=False,
        ))
        self.assertTrue(can_report_session(
            is_today=True,
            completed_expected_count=80,
            expected_count=80,
            now_hm="08:00",
            window_end_hm="07:30",
            runner_busy=False,
            has_unattempted_locked=False,
        ))
        # Nếu runner vẫn đang bận (hôm nay) -> không chốt sớm
        self.assertFalse(can_report_session(
            is_today=True,
            completed_expected_count=80,
            expected_count=80,
            now_hm="07:00",
            window_end_hm="07:30",
            runner_busy=True,
            has_unattempted_locked=False,
        ))

        # 2. Đang trong giờ phiên (now_hm < window_end_hm)
        # 2a. Nếu runner_busy=True và chưa hoàn tất -> False
        self.assertFalse(can_report_session(
            is_today=True,
            completed_expected_count=40,
            expected_count=80,
            now_hm="07:00",
            window_end_hm="07:30",
            runner_busy=True,
            has_unattempted_locked=False,
        ))
        # 2b. Tất cả máy bị lock trước window_end_hm -> False
        self.assertFalse(can_report_session(
            is_today=True,
            completed_expected_count=0,
            expected_count=80,
            now_hm="07:00",
            window_end_hm="07:30",
            runner_busy=False,
            has_unattempted_locked=True,
        ))
        # 2c. Kể cả nếu count được truyền vào >= expected_count, has_unattempted_locked trước end_hm phải chặn lại -> False
        self.assertFalse(can_report_session(
            is_today=True,
            completed_expected_count=80,
            expected_count=80,
            now_hm="07:00",
            window_end_hm="07:30",
            runner_busy=False,
            has_unattempted_locked=True,
        ))
        # 2d. Chưa hoàn tất máy nhưng runner rảnh và không có lock unattempted trước end_hm -> False
        self.assertFalse(can_report_session(
            is_today=True,
            completed_expected_count=50,
            expected_count=80,
            now_hm="07:00",
            window_end_hm="07:30",
            runner_busy=False,
            has_unattempted_locked=False,
        ))

        # 3. Đã qua window_end_hm: grace period 20 phút nếu runner đang chạy
        # 3a. Runner đang chạy và trong grace period 20 phút (07:30 + 20 = 07:50, now=07:40) -> False
        self.assertFalse(can_report_session(
            is_today=True,
            completed_expected_count=50,
            expected_count=80,
            now_hm="07:40",
            window_end_hm="07:30",
            runner_busy=True,
            has_unattempted_locked=False,
        ))
        # 3b. Runner đang chạy nhưng đã qua window_end_hm -> False (chờ runner chạy xong hẳn mới chốt)
        self.assertFalse(can_report_session(
            is_today=True,
            completed_expected_count=50,
            expected_count=80,
            now_hm="07:55",
            window_end_hm="07:30",
            runner_busy=True,
            has_unattempted_locked=False,
        ))
        # 3c. Đã qua window_end_hm và runner không bận -> BẮT BUỘC chốt báo cáo (kể cả có máy bị lock)
        self.assertTrue(can_report_session(
            is_today=True,
            completed_expected_count=0,
            expected_count=80,
            now_hm="07:35",
            window_end_hm="07:30",
            runner_busy=False,
            has_unattempted_locked=True,
        ))

        # 4. 80 máy chạy thật xong trước window_end_hm -> True
        self.assertTrue(can_report_session(
            is_today=True,
            completed_expected_count=80,
            expected_count=80,
            now_hm="07:00",
            window_end_hm="07:30",
            runner_busy=False,
            has_unattempted_locked=False,
        ))

        # 5. Ngày hôm trước (is_today=False)
        self.assertTrue(can_report_session(
            is_today=False,
            completed_expected_count=80,
            expected_count=80,
            now_hm="01:00",
            window_end_hm="23:59",
            runner_busy=False,
        ))
        self.assertTrue(can_report_session(
            is_today=False,
            completed_expected_count=10,
            expected_count=80,
            now_hm="02:30",
            window_end_hm="23:59",
            runner_busy=False,
        ))
        self.assertFalse(can_report_session(
            is_today=False,
            completed_expected_count=10,
            expected_count=80,
            now_hm="01:30",
            window_end_hm="23:59",
            runner_busy=False,
        ))


class TestRunnerZombieFilter(unittest.TestCase):
    def test_zombie_runner_ignored_when_ctime_exceeds_9000s(self):
        now = 100000.0
        # Process created 9500s ago (> 9000s -> zombie, ignored)
        zombie_proc = MagicMock()
        zombie_proc.pid = 99999
        zombie_proc.info = {
            'name': 'python.exe',
            'cmdline': ['python.exe', 'multi_machine_feed_session.py'],
            'create_time': now - 9500,
        }
        zombie_proc.create_time.return_value = now - 9500

        with patch('time.time', return_value=now):
            with patch('psutil.process_iter', return_value=[zombie_proc]):
                self.assertFalse(is_feed_runner_active())

    def test_active_runner_detected_when_ctime_within_9000s(self):
        now = 100000.0
        # Process created 1000s ago (<= 9000s -> active runner)
        active_proc = MagicMock()
        active_proc.pid = 99999
        active_proc.info = {
            'name': 'python.exe',
            'cmdline': ['python.exe', 'multi_machine_feed_session.py'],
            'create_time': now - 1000,
        }
        active_proc.create_time.return_value = now - 1000

        with patch('time.time', return_value=now):
            with patch('psutil.process_iter', return_value=[active_proc]):
                self.assertTrue(is_feed_runner_active())


if __name__ == "__main__":
    unittest.main()
