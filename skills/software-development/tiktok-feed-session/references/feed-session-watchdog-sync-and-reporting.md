# Feed Session Watchdog: Triển Khai & Kiểm Thử Đồng Bộ (3 File Rule)

## 1. Bản Đồ 3 File Bắt Buộc Đồng Bộ Tuyệt Đối
Khi chỉnh sửa `feed_session_watchdog.py`, BẮT BUỘC phải áp dụng đồng thời cho cả 3 vị trí:
1. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py` (Hermes local active runtime)
2. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py` (Hermes deploy source)
3. `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py` (Repo copy được import bởi pytest)

**Lý do:**
- Pytest (`test_feed_session_watchdog.py`) import trực tiếp từ đường dẫn (3).
- Tiến trình cron thật chạy từ đường dẫn (1).
- Quá trình deploy lấy nguồn từ đường dẫn (2).
- Nếu chỉ sửa (1) hoặc (3), hệ thống sẽ gặp hiện tượng drift: test pass nhưng runtime lỗi, hoặc ngược lại.

## 2. Quy Tắc Phân Nhóm Follow Thành Công & Bỏ Qua
- `format_success_follows(fl_success: list, all_follows: dict) -> list`:
  - Phân nhóm máy follow thành công theo các mức: `1 - 4 lượt`, `5 - 9 lượt`, `10+ lượt`.
  - Nếu `not fl_success`: trả về `["  + Success (0): Không có"]`.
- Phân loại trạng thái follow trong `main()`:
  - `status in {"OK", "SUCCESS"} and len(flist) > 0`: tính vào `fl_success`.
  - `status in {"OK", "SUCCESS"} and len(flist) == 0`: tính vào `fl_skipped` (bỏ qua / không có target hợp lệ).
  - Tránh nhầm lẫn trạng thái 0 lượt follow sang `fl_error`.

## 3. Điều Kiện Chốt Báo Cáo Phiên (`can_report_session`)
- Trong giờ phiên (`is_today and now_hm < window_end_hm`):
  - Nếu `runner_busy` hoặc `has_unattempted_locked`: cấm chốt (`return False`) để tránh race-condition chốt thiếu máy đang chạy dở.
  - Chỉ chốt khi `completed_expected_count >= expected_count`.
- Khi đã qua giờ phiên (`now_hm >= window_end_hm`) hoặc là ngày cũ (`not is_today`):
  - BẮT BUỘC chốt báo cáo (`return True`), không thêm grace period tự ý làm sai lệch test contract.

## 4. Quy Trình Verify Bắt Buộc
- Biên dịch cú pháp:
  ```bash
  python -m py_compile "C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py"
  python -m py_compile "D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py"
  python -m py_compile "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py"
  ```
- Chạy test suite:
  ```bash
  "D:/Taadaa/python-envs/automation/Scripts/python.exe" -m pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_feed_session_watchdog.py" -v
  ```
- Luôn đảm bảo toàn bộ tests (ví dụ 15/15) PASS 100%.
