# Case 65: Khắc Phục Tranh Chấp File Lock Shift Upload Ledger, Hard Deadline Propagation & Atomic Ledger Commit

## 1. Hiện tượng & Bối cảnh
- **Lỗi thực tế:** `shift_upload_lock_timeout_fail_closed` xuất hiện đồng loạt trên nhiều máy (máy 2, 13, 20, 26, 28, 36, 57, 74) trong ca nuôi Row 3 (Phiên 3) khi 50-80 máy đồng thời hoàn thành lướt feed và chuyển sang hook upload video.
- **Hệ quả sai lệch:** Feed Session Watchdog quét log phát hiện `shift_upload_lock_timeout_fail_closed` nhưng lại phân loại nhầm vào nhóm timeout ca feed tổng thể, gây sai lệch báo cáo giám sát.

## 2. Nguyên nhân cốt lõi (Anti-Patterns)
1. **Timeout Lock Quá Ngắn & Thundering Herd:** Cơ chế `_InterProcessFileLock` cũ bị hardcode timeout chỉ **10.0s** và sleep cố định **0.05s**. Khi 80 worker đồng loạt tranh chấp file lock chung `.shift_upload_history.lock`, thời gian xếp hàng vượt quá 10s khiến các máy sau cùng bị fail-closed.
2. **Thiếu Retry Jitter:** Sleep cố định làm tất cả tiến trình thức dậy cùng thời điểm và tiếp tục đâm vào lock.
3. **Stale Lock Không Được Dọn:** Nếu tiến trình trước đó bị crash hoặc kill giữa chừng, lock file cũ bị bỏ lại và block các lượt chạy sau.
4. **Nguy Cơ Corrupt File Khi Ghi Trực Tiếp:** Ghi trực tiếp vào `.shift_upload_history.json` mà không qua file tạm + fsync + replace nguyên tử có nguy cơ làm hỏng JSON nếu tiến trình bị ngắt.

## 3. Giải pháp chuẩn hóa (Case Fix)

### A. Nâng Lock Timeout & Randomized Jitter (Cập nhật 2026-09-02)
- Nâng timeout mặc định lên **180.0s** (`shift_upload_lock_timeout_seconds`, fallback 180.0s).
- **Tách biệt Lock Timeout khỏi Global Session Hard Deadline**: File lock của `claim_reservation` sử dụng deadline riêng `lock_deadline = min(hard_dl, now + lock_timeout)` thay vì truyền trực tiếp `deadline=hard_dl` đã cạn kiệt sau 30-40 phút feed session, ngăn chặn cascade timeout khi 80 máy đồng loạt xả feed cuối ca.
- Áp dụng sleep jitter ngẫu nhiên `random.uniform(0.02, 0.08)` kèm clamping `min(remaining, jitter)` giúp phân tán hoàn toàn tải tranh chấp giữa 80 máy.
- Tự động dọn dẹp stale lock file tồn tại quá **120.0s**.

### B. Linearizable Ground-Truth Inspection
- Quét báo cáo `report.json` trong `CodexRuntime` dưới lock coordinating; yêu cầu khớp chính xác danh tính tài khoản (`rep_acc == acc_tag`) và fail-closed an toàn nếu file report rỗng hoặc hỏng.

### C. Hard Monotonic Deadline Enforcement
- Tiếp nhận deadline tuyệt đối (`_hard_deadline_monotonic`, `feed_session_deadline`) và kiểm tra nghiêm ngặt xuyên suốt từng bước: trước khi acquire, sau khi tạo thư mục, sau khi serialize JSON, trước khi ghi file, trước fsync và trước khi `os.replace`.

### D. Ghi Ledger Nguyên Tử (Atomic Commit)
- Sử dụng cơ chế ghi qua file tạm (`tempfile.NamedTemporaryFile(delete=False)`) cùng thư mục, gọi `os.fsync()` đảm bảo dữ liệu ghi xuống đĩa, sau đó `os.replace()` nguyên tử đè lên file ledger chính. Tự động dọn dẹp file tạm trong block `finally`.

### E. Token-Verified Terminal Reconciliation
- Các phương thức trạng thái cuối (`complete_success`, `record_launched`, `record_spawn_failed`, `release_reservation`) yêu cầu token hợp lệ và chỉ tác động đúng các bản ghi `in_progress` / `launched`, tuyệt đối bảo vệ các bản ghi `success` không bao giờ bị xóa nhầm.

## 4. Bộ Kiểm Thử Hồi Quy
- `python_runner/tests/test_upload_hook.py`: 59/59 tests pass 100% (bao gồm kiểm thử tranh chấp đa tiến trình đồng thời, lock jitter, fsync failure propagation, token isolation, deadline clamping).
- `python_runner/tests/test_multi_machine_feed_session.py`: 101/101 tests pass 100%.
