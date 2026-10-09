# Bidirectional Device Lock: Feed Session vs Operator Tool Concurrency (2026-09-17)

## Kiến trúc 2 chiều bắt buộc cho Farm 74 máy:
1. **Chiều 1 (Operator lock máy can thiệp -> Ca nuôi phải Clean Skip):**
   - Preflight PS (`run-feed-session.ps1`): Lọc `$activeMachineValues` trước khi tạo `$machineList`. Nếu lock file có PID sống -> Ghi log skip và LOẠI ngay khỏi `$machineList`. Nếu 100% máy bận -> `exit 0` clean exit.
   - Batch Aggregation (`multi_machine_feed_session.py`): Tách biệt `needs-user-decision` (xung đột thật -> `MANUAL_NEEDED`) và `skipped-device-locked` (operator đang lock -> nếu có máy khác chạy thành công thì trả về `ExitStatus.SUCCESS` với status `success`, KHÔNG làm fail đỏ cả batch 74 máy).
2. **Chiều 2 (Ca nuôi đang chạy -> Operator tool phải tự động chờ):**
   - Core API: `wait_for_device_lock(*, machine, serial, project, timeout=300, poll_interval=5, release_on_terminal=True)` có loop deadline và kiểm tra `_owner_process_alive(last_owner)` để dọn stale lock nếu PID cũ đã chết.
   - Context manager: `operator_device_lock(...)` tự giải phóng lock trong `finally`.
   - CLI Wrapper ngoài band: `python D:/Taadaa/tools/with_device_lock.py --machine N -- <command...>` giúp mọi tool ADB/bảo trì tự xếp hàng chờ ca nuôi xong mới chạy.
