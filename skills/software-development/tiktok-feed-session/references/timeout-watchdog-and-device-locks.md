# Feed Session Timeout, Watchdog & Device Lock Architecture

## 1. Timeout & Per-Device Deadline Watchdog
- **Hằng số cấu hình:** `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1500.0` (25 phút/máy) được đặt trong `python_runner/flows/multi_machine_feed_session.py`.
- **Cơ chế hoạt động:**
  - Mỗi máy khi bắt đầu phiên được gán `child_config["_deadline_monotonic"] = time.monotonic() + timeout_seconds`.
  - Ở các bước trọng yếu (chờ xem video, chụp UI XML, kiểm tra popup, đổi tab feed), hàm `ensure_run_plan_deadline(ctx.config, operation)` kiểm tra thời gian hiện tại so với deadline.
  - Khi vượt quá deadline, hệ thống ném ngoại lệ `RunPlanDeadlineExceeded(f"run plan max_duration_seconds exceeded before {operation}")`.
  - Worker bắt ngoại lệ này, chuyển trạng thái phiên thành `failed`, ghi nhận `stop_reason` chi tiết, kích hoạt `finalize_feed_session_cleanup` và xuất `summary.txt` terminal hợp lệ để process cha không bị treo vô hạn.

## 2. Quy tắc Device Lock & Giữ hiện trường
- **Tạo Lock khi bắt đầu:** Mỗi thiết bị/serial được cấp một file device lock độc quyền nhằm ngăn xung đột giữa các tool hoặc tiến trình cron chạy song song.
- **Thành công (`SUCCESS`):** Tự động xóa file device lock (`release_recovery_lock` / unlock) để trả máy về trạng thái rảnh cho các ca tự động tiếp theo.
- **Sự cố / Dừng phiên (`BLOCKED` / `failed` / `manual-needed`):** Runner chủ động GIỮ NGUYÊN LOCK ("GIỮ HIỆN TRƯỜNG"), dừng lại và cảnh báo lên Telegram để bảo toàn trạng thái màn hình máy cho Hermes Agent kiểm tra, ngăn các ca sau đè lên làm mất vết lỗi.
- **Sau khi khắc phục:** Sau khi kiểm tra/sửa code xong hoặc được người dùng chỉ định, file lock của máy mới được xóa/giải phóng an toàn.
