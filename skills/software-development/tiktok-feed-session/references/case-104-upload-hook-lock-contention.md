# Case 104: Khắc phục tranh chấp lock hook upload Phiên 3 (shift_upload_lock_timeout_fail_closed)

## 1. Hiện tượng & Sự cố thực tế (2026-09-05)
- Watchdog Phiên 3 Ca 1 báo 21 máy bị "Timeout/Quá giờ" khi đăng video (M1, M2, M13, M16, M17, M18, M24, M25, M31, M35, M38, M39, M41, M49, M53, M55, M60, M64, M77, M78, M80).
- File artifact `upload_result.json` ghi nhận: `status="failed"`, `reason="shift_upload_lock_timeout_fail_closed"`.

## 2. Phân tích nguyên nhân gốc rễ (Anti-Patterns)
1. **Thiếu điều phối luồng nội bộ (Thread vs Process Contention):**
   - Ở Phiên 3 (đăng video), khi 40-74 máy cùng xong lướt feed trong 1-2 phút, hàng chục worker threads trong cùng process Python đồng loạt gọi `_run_upload_hook` -> `_ShiftUploadLedger.claim_reservation`.
   - Khóa file `_InterProcessFileLock` chỉ dùng OS-level locking (`msvcrt.locking`) mà không có in-process lock (`threading.RLock()`).
   - Hàng chục threads liên tục gọi `open()`, `locking()` rồi sleep jitter 20-80ms, gây bão tranh chấp file lock và nghẽn kernel I/O trầm trọng.
2. **Quét đĩa lớn khi đang giữ exclusive file lock:**
   - Trong `claim_reservation`, khi đang giữ exclusive lock, hàm chạy `report_root.glob(f"run_{serial}_{date_compact}_*/report.json")` trên thư mục `D:/CodexRuntime/tiktok-video/runs` chứa hơn 48.000 thư mục.
   - Thao tác `glob()` 48k thư mục trên Windows NTFS tốn 100-300ms/máy khi ĐANG GIỮ exclusive lock, cộng thêm đọc/ghi JSON 254KB và `os.fsync`.
   - Thời gian xếp hàng dồn lại của 40+ máy vượt quá `lock_timeout = 180.0s`, khiến 21 máy ở cuối hàng bị `TimeoutError` và fail closed.
3. **Truyền sai cấu hình deadline:**
   - Trong `_run_upload_hook`, lời gọi `claim_reservation` truyền `ctx.config` thay vì `deadline_config`, làm thất thoát thông tin deadline riêng biệt của worker.

## 3. Quy chuẩn giải pháp bắt buộc (Dual-Tier Locking Architecture)
1. **Khóa kép In-Process + Inter-Process (`_LOCAL_LEDGER_LOCK`):**
   - Khởi tạo `_LOCAL_LEDGER_LOCK = threading.RLock()` cấp process và context manager `_acquire_local_ledger_lock(timeout, deadline)`.
   - Serialize các threads trong cùng Python process một cách mượt mà qua Python threading scheduler trước khi gọi `_InterProcessFileLock`.
   - Tại bất kỳ thời điểm nào, tối đa chỉ có 1 thread trong tiến trình chạm vào OS file lock, triệt tiêu bão I/O kernel.
2. **Kiểm tra Ground Truth trước khi chiếm lock qua fast `os.scandir`:**
   - Thay thế `report_root.glob(...)` bằng hàm lọc nhanh `_find_ground_truth_reports()` sử dụng `os.scandir` với prefix `run_{serial}_{date_compact}_`.
   - Đưa thao tác scan ra TRƯỚC khi chiếm exclusive file lock. Rút ngắn thời gian chiếm lock từ 100-300ms xuống chỉ còn ~1-3ms (chỉ đọc/ghi JSON lịch sử).
3. **Nâng timeout an toàn và cấu hình linh hoạt:**
   - Nâng `lock_timeout` mặc định lên 300.0s, hỗ trợ ghi đè qua `shift_upload_lock_timeout_seconds`.
4. **Truyền đúng `deadline_config`:**
   - Luôn truyền `deadline_config` vào toàn bộ các lời gọi `_ShiftUploadLedger` trong `_run_upload_hook`.
