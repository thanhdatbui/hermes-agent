# Workbook Concurrent Read Lock & Retry Pattern

## Bối cảnh & Hiện tượng (Root Cause)
Khi 30–40 worker chạy song song trong các đợt upload video (như khung 06:51 – 06:54 Ca 1):
- Các worker hoàn tất upload gọi `update_video_number()` qua `atomic_workbook_update()`. Quá trình này tạo file `.lock` và hoán đổi file Excel qua `temp_path.replace()`.
- Các worker khác cùng lúc gọi `AccountSource.read_row()` để đọc cấu hình tài khoản.
- Nếu `read_row` không nhận biết file `.lock` và không có cơ chế retry:
  - Trên Windows, việc đọc trùng thời điểm file đang được ghi/thay thế hoặc sync OneDrive sẽ dẫn đến việc `openpyxl` đọc ra dòng rỗng hoặc thiếu cột, ném lỗi:
    `[READ_WORKBOOK_ERROR] Missing required fields: ID TikTok`
  - Đóng văng phiên upload của hàng loạt máy.

## Quy tắc bắt buộc (Hard Invariants)

1. **Per-Attempt Lock Wait:**
   - Trích xuất hàm `_wait_for_lock(lock_file, timeout=10.0) -> float`.
   - BẮT BUỘC gọi `_wait_for_lock()` **trước mỗi nhịp thử** trong vòng lặp retry (thay vì chỉ kiểm tra một lần bên ngoài vòng lặp) để loại trừ race condition khi lock xuất hiện giữa chừng giữa các lần retry.

2. **Retry với Exponential Backoff:**
   - Vòng lặp `max_attempts = 5`.
   - Mỗi lần thất bại, chờ `0.5 * attempt` giây (0.5s -> 1.0s -> 1.5s -> 2.0s -> 2.5s) trước khi thử lại.
   - Giải phóng sạch handle workbook (`_wb.close()`) ở cả nhánh thành công lẫn ngoại lệ để chống rò rỉ file lock trên Windows.

3. **Telemetry & Quan sát có cấu trúc:**
   - Lưu metrics `_read_attempts` và `_lock_wait_seconds` trên instance `AccountSource`.
   - Ghi log định lượng `[WORKBOOK_READ_RECOVERED]` khi đọc thành công sau retry (`attempt > 1`) hoặc sau khi chờ lock (`total_lock_wait > 0`).

4. **Multi-Worker Stress Test:**
   - Mọi bản vá liên quan đến concurrent workbook access bắt buộc phải có test case kiểm thử tải đa luồng (`ThreadPoolExecutor`) gồm cả luồng Writer liên tục ghi và nhiều luồng Reader đồng thời đọc (`test_account_source_concurrency.py`).
