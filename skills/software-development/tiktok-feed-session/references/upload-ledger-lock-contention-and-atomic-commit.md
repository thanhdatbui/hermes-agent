# Upload Ledger Concurrency, Lock Contention & Atomic Commit Rules (Case 65)

## 1. Bối Cảnh & Vấn Đề (Anti-Pattern)
Khi hơn 50-80 máy hoàn thành feed-session đồng thời và kích hoạt hook upload, tất cả worker cùng tranh chấp file lock chung `.shift_upload_history.lock`.
- **Lỗi cũ:** `_InterProcessFileLock` bị hardcode timeout 10.0s với sleep cố định 0.05s. Các worker xếp hàng sau bị quá 10s dẫn đến mã lỗi `shift_upload_lock_timeout_fail_closed` và Watchdog phân loại nhầm vào nhóm timeout ca feed.
- **Rủi ro rò rỉ reservation:** Nếu phương thức dọn dẹp lỗi (`record_spawn_failed`, `release_reservation`) không kiểm tra token hoặc trạng thái, một callback dọn dẹp trễ có thể xóa nhầm bản ghi `success` hoặc `indeterminate` đã hoàn thành, dẫn đến nguy cơ upload trùng lặp.

---

## 2. Quy Tắc Kỹ Thuật Bắt Buộc (Case Fix Standards)

### A. Lock Timeout & Randomized Jitter
1. **Timeout mặc định:** Nâng lên `60.0s` cho file lock liên tiến trình `_InterProcessFileLock`.
2. **Randomized Retry Jitter:** Sử dụng `random.uniform(0.02, 0.08)` và clamp khoảng sleep vào thời gian còn lại: `min(remaining, jitter)` để phân tán thời điểm thử lại của hàng chục worker, tránh hiện tượng thundering herd.
3. **Phân loại lỗi locking:**
   - Trên Windows: retry khi gặp `msvcrt` contention (`EACCES`, `EDEADLK`, `EAGAIN`).
   - Trên POSIX: retry khi gặp `flock` contention (`EAGAIN`, `EWOULDBLOCK`, `EACCES`, `EDEADLK`).
   - Mọi lỗi permission/I/O khi `mkdir` hoặc `open` lock file phải fail-fast / raise ngay lập tức, không loop như lock contention.

### B. Linearizable Ground-Truth Discovery Under Lock
1. **Quét dưới Lock:** Quét báo cáo `report.json` trong `CodexRuntime/tiktok-video/runs/` ngay bên trong lock coordinating trước khi ghi `in_progress`.
2. **Khớp chính xác Account Identity:** Bắt buộc `rep_acc and acc_tag and rep_acc == acc_tag`. Báo cáo thành công nhưng trống danh tính tài khoản phải fail-closed với `indeterminate_ground_truth_report_fail_closed` để tránh upload trùng.

### C. Explicit Atomic Commit Boundary (`_atomic_write_ledger`)
1. **Quy trình ghi:** Ghi ra file tạm cùng thư mục `.shift_upload_history.<uuid>.tmp`, gọi `f.flush()` -> `os.fsync(f.fileno())` -> `os.replace(tmp, hist_file)`.
2. **Pre-Commit Deadline Gates:** Kiểm tra deadline trước khi serialize JSON, trước khi ghi file, trước khi `fsync` và trước khi `os.replace`.
3. **Dọn dẹp an toàn:** Bọc `os.replace` trong try/finally; nếu chưa commit thành công (`replaced is False`), tự động `tmp.unlink()` trong `finally`.

### D. Token-Verified Terminal Reconciliation
1. **Admission vs Reconciliation:**
   - `claim_reservation`: Đóng vai trò Admission Gate, kiểm soát nghiêm ngặt `_hard_deadline_monotonic`.
   - `complete_success`, `record_launched`, `record_spawn_failed`, `release_reservation`: Đóng vai trò Reconciliation, yêu cầu non-empty `token` khớp chính xác với ledger entry và hoàn tất commit trạng thái ngay cả khi ca feed đã hết giờ.
2. **Bảo vệ Trạng Thái Thành Công:**
   - `release_reservation`: CHỈ xóa bản ghi khi `status == "in_progress"` và `entry.token == token`.
   - `record_spawn_failed`: CHỈ xóa bản ghi khi `status in ("in_progress", "launched")` và `entry.token == token`.
   - Tuyệt đối KHÔNG BAO GIỜ xóa bản ghi `status == "success"` hoặc `status == "indeterminate"`.

---

## 3. Quy Tắc Chuyển Đổi Trạng Thái Video #1 (Avatar Transition)
Trong repo `Tiktok-video/scripts/tiktok_workflow/state_machine.py`:
- `TRANSITION_MAP[WorkflowState.UPDATE_WORKBOOK]` bắt buộc phải bao gồm `WorkflowState.ENSURE_AVATAR`.
- Sau khi `_step_update_workbook` ghi nhận đăng video #1 thành công cho tài khoản mới (như Row 3), state machine phải chuyển tiếp vào `ENSURE_AVATAR` để cập nhật `avatar.jpg` từ thư mục profile trước khi chuyển sang `DELETE_REMOTE_MEDIA`.
