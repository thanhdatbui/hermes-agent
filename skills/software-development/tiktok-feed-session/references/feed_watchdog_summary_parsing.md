# Feed Session Watchdog & Summary Parsing Patterns

## 1. Cấu trúc và định dạng `summary.txt` trong Feed Session Run
Mỗi run thư mục (ví dụ `D:/Taadaa/runtime/kibe/live/YYYY-MM-DD/row-X-XXXXXX/YYYYMMDD-HHMMSS/`):
- **Root `summary.txt`**: Chứa danh sách các máy bị failed / skipped.
  - Các máy trống nick / không có cấu hình row thường có log: `"account row X is empty (no username) for machine Y, skipping"`.
  - Nếu parse root summary fallback bắt `machine_(\d+)`, các máy này có thể bị gán tạm `batch-config-error`. Cần phân biệt: nếu machine KHÔNG thuộc `get_expected_machines_for_row(active_row)`, đó là empty-slot chứ không phải lỗi thật (`fail_real`).
- **Per-machine `summary.txt`** (`machines/machine_N/YYYYMMDD-HHMMSS/summary.txt`):
  - Chứa cả text header và JSON block dump.
  - Trạng thái trống slot: reason chứa `"is empty (no username)"` hoặc `"does not have valid row"` -> gán `status="skipped-empty"`.
  - Thống kê Like & Swipe:
    - `"total_swipes_completed": N`: lấy số hoàn tất vuốt (thường là số đầu tiên xuất hiện sau key).
    - `"like_counts": { "for-you": X, "following": Y, "friends": Z }`: sum các số sau 3 danh mục này để ra tổng likes của máy.

## 2. Quy tắc Merge và Báo cáo Watchdog
- **Merge (`merge_machine_result`)**:
  - Khi merge các lượt chạy / retry của cùng một máy, cần cộng dồn (accumulate) `likes` và `swipes`, không ghi đè mất dữ liệu.
- **Báo cáo Feed Session**:
  - `succ`: máy có `status == "success"`.
  - `empty`: `status == "skipped-empty"` HOẶC reason chứa `"is empty (no username)"` HOẶC (`batch-config-error` mà máy không nằm trong `expected_machines_for_row`).
  - `fail_real`: toàn bộ máy còn lại.
  - Dòng hiển thị thêm trong message:
    - `+ Trống slot/chưa có nick (N): ...`
    - `+ Thả tim: {total_likes} tim / {total_swipes} video ({rate:.1f}%)` (chỉ tính trên các máy success).
