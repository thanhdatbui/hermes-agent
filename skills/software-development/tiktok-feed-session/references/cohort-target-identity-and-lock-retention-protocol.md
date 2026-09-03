# Cohort Target Identity Binding & Device Lock Retention Protocol

## 1. Context & Root Cause
Trong cơ chế quản lý batch đa máy theo Frozen Cohort (`python_runner/flows/multi_machine_feed_session.py` và `hermes_cron`), mỗi worker kiểm tra tính khớp nối định danh (`_apply_cohort_identity`) trước khi chạy device actions:
- Manifest có thể có hoặc không có trường `"tik"` tùy theo ca (ví dụ Row 2 có `tik`, Row 4 không khai báo `tik`).
- **Quy tắc bất biến:** Trường `"tik"` trong target identity chỉ được đối soát khi manifest CÓ khai báo (`if "tik" in expected:`). Tuyệt đối không coi việc thiếu key `"tik"` trong manifest là lỗi `missing:tik` làm fail toàn bộ cohort.

## 2. Tránh Kẹt Device Lock Toàn Farm (Blocked Lock Storm)
- Khi `_apply_cohort_identity` gặp lỗi `cohort-target-mismatch` (hoặc lỗi cấu hình hàng loạt), hệ thống sẽ gán trạng thái lock `blocked` (TTL 2h) trên toàn bộ danh sách máy để giữ hiện trường.
- Hậu quả: Toàn bộ các tick cron tiếp theo trong ca sẽ skip các máy này vì `device_lock active`.
- **Quy trình gỡ:**
  1. Fix triệt để code validation logic (`_apply_cohort_identity`).
  2. Rà soát và dọn dẹp các file `.lock.json` bị kẹt oan trong `~/.codex/device-locks/` phát sinh từ run_id lỗi.
  3. Verify bằng test suite `pytest python_runner/tests/ -k cohort` trước khi kích hoạt lại cron.

## 3. Windows Process Termination (`_kill_stale_pids`)
- Trong `tiktok_runner.py`, khi kết thúc hoặc dọn dẹp tiến trình runner cũ/treo:
- Trên Windows, việc lấy handle qua `kernel32.OpenProcess` có thể gặp hạn chế quyền (ERROR_ACCESS_DENIED) hoặc PID đã thoát giữa chừng. Không được để việc thiếu process handle làm fail toàn bộ hàm `_kill_stale_pids`; lệnh `taskkill /F /T /PID <pid>` vẫn là chốt chặn tin cậy.
