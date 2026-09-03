# Cross-Repo Upload Hook Module Resolution and Two-Tier Watchdog Architecture (2026-08-23)

## 1. Cross-Repo Upload Hook Module Resolution (`tiktok-video`)
- **Vấn đề:** Khi `multi_machine_feed_session.py` gọi subprocess sang repo `tiktok-video` để upload video sau phiên 3:
  Lệnh cũ: `python -m tiktok_workflow --config ... --workflow-workbook ... --machine ... --no-dry-run`
  Thất bại với lỗi: `No module named tiktok_workflow` (exit code 1).
- **Nguyên nhân:** Trong repo `D:\Taadaa\tiktok-video`, entrypoint CLI không nằm trực tiếp tại root mà nằm trong package `scripts/tiktok_workflow/` (`scripts.tiktok_workflow`).
- **Khắc phục chuẩn:**
  Lệnh gọi bắt buộc:
  ```python
  command = [
      ctx.config.get("python_exe") or sys.executable,
      "-m",
      "scripts.tiktok_workflow",
      "--config", str(config_file),
      "--workflow-workbook", str(workbook_path),
      "--machine", str(account.machine),
      "--no-dry-run",
  ]
  ```
- **Test verification:** Cập nhật assertion trong `test_upload_hook.py` để chấp nhận `scripts.tiktok_workflow`.

## 2. Hai Lớp Watchdog Chống Treo Cron Batch (`multi_machine` + `tiktok_runner`)
### Lớp 1: Hard Outer Watchdog Timeout trong ThreadPoolExecutor (Flow Level)
- **Cơ chế:** Thay vì gọi `as_completed(futures)` và `future.result()` chờ vô hạn:
  - Dùng vòng lặp `wait(pending_futures, timeout=5.0, return_when=FIRST_COMPLETED)`.
  - Lưu `start_monotonic` cho từng machine future.
  - Quét định kỳ: Nếu máy chạy vượt quá `worker_hard_timeout` (mặc định 30 phút = 1800s):
    1. Gỡ future khỏi `pending_futures`.
    2. Đánh dấu `reservation.set_status("handoff")`.
    3. Tạo fallback child artifacts (`final_status="failed"`, `stop_reason="hard outer watchdog timeout exceeded ..."`).
    4. Gửi alert Telegram Farm Alerts và ghi log JSONL.
  - **Kết quả:** Ngăn chặn việc 1 máy bị kẹt ADB socket / ATX hang làm process batch cha không bao giờ kết thúc.

### Lớp 2: Auto-Reap Stale Runner Lease (Runner Level)
- **Cơ chế trong `tiktok_runner.py::_lease_alive()`:**
  1. Kiểm tra giới hạn 90 phút (`total_seconds() > 5400`): Nếu lease cũ đã tồn tại quá 90 phút (vượt quá thời gian tối đa của 1 ca feed), tự động xóa file lease `unlink(missing_ok=True)` và trả về `False` để ca tiếp theo được spawn bình thường.
  2. Kiểm tra PID aliveness: Nếu PID ghi trong lease đã chết hoặc không hợp lệ, tự động xóa lease ngay lập tức.
  3. Bọc an toàn ngoại lệ `(OSError, SystemError)` khi gọi `os.kill(pid, 0)` trên Windows.
