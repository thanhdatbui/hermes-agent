# Fast Targeted Login Recovery Architecture & Telemetry

## 1. Context & Architecture (Single Responsibility Principle)
Trong flow `python_runner/flows/feed_swipe_smoke.py`, khi phát hiện account mong đợi bị thiếu trên device switcher:
- Helper tách biệt `_build_fast_login_env(adb_path: Path | None) -> dict[str, str]` chịu trách nhiệm chuẩn bị environment cho sub-process gọi sang `tiktok_login_v1.py`:
  - Luôn xóa `PYTHONPATH` (`fast_env.pop("PYTHONPATH", None)`) để tránh import shadowing từ python runner sang repo script đăng nhập.
  - Tự động prepend thư mục ADB tools (`adb_path.parent` hoặc fallback `C:\Program Files (x86)\xiaowei\tools`) vào đầu biến `PATH`.
- Hàm thực thi `_run_fast_targeted_login` chỉ tập trung vào việc dựng command, quản lý vòng đời tiến trình subprocess, và phát telemetry.

## 2. Duration Metrics Telemetry
Mọi invocation của fast login recovery đều được đo đạc chính xác:
- Bắt đầu trước khi gọi `subprocess.run`: `start_time = time.time()`.
- Tính thời gian thực thi: `duration_seconds = round(time.time() - start_time, 2)`.
- Ghi nhận `duration_seconds` vào trường `extra` metadata của `ctx.logger.log` ở cả 3 nhánh trạng thái kết thúc:
  1. `finish_fast_login` (kết quả thành công, returncode == 0)
  2. `fast_login_failed_fallback_reconcile` (kết quả thất bại, returncode != 0)
  3. `fast_login_exception_fallback_reconcile` (gặp exception như timeout, subprocess error)

## 3. Unit Test Validation
File `python_runner/tests/test_auto_login_fast_recovery.py` xác thực:
- `test_build_fast_login_env`: assert `PYTHONPATH` vắng mặt và đường dẫn tool ADB nằm trong `PATH`.
- `test_auto_login_fast_targeted_success`: assert `duration_seconds` có mặt trong `extra` metadata và là kiểu float.
- `test_auto_login_fast_targeted_fail_fallback_reconcile` & `test_auto_login_fast_targeted_timeout_fallback`: assert `duration_seconds` có mặt khi fail/timeout.
