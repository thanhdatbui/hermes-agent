import unittest
import sys
import os

# Add scripts directory to sys.path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from feed_session_watchdog import (
    is_device_locked_skip,
    merge_machine_result,
    can_report_session,
    _add_minutes_to_hm,
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

    def test_add_minutes_to_hm(self):
        self.assertEqual(_add_minutes_to_hm("07:30", 20), "07:50")
        self.assertEqual(_add_minutes_to_hm("23:50", 20), "00:10")
        self.assertEqual(_add_minutes_to_hm("00:00", 60), "01:00")
        self.assertEqual(_add_minutes_to_hm("15:45", 15), "16:00")

    def test_can_report_session(self):
        # 1. Tất cả máy dự kiến đã hoàn tất thật (không còn unattempted lock) -> chốt ngay lập tức kể cả khi runner_busy=True
        self.assertTrue(can_report_session(
            is_today=True,
            completed_expected_count=80,
            expected_count=80,
            now_hm="07:00",
            window_end_hm="07:30",
            runner_busy=True,
            has_unattempted_locked=False,
        ))
        self.assertTrue(can_report_session(
            is_today=True,
            completed_expected_count=80,
            expected_count=80,
            now_hm="08:00",
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
        # 3b. Runner đang chạy nhưng đã hết grace period 20 phút (now=07:55 >= 07:50) -> True (BẮT BUỘC chốt báo cáo)
        self.assertTrue(can_report_session(
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


if __name__ == "__main__":
    unittest.main()
