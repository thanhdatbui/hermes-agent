# Shift Upload Lock Contention & "Quá giờ up video" Pitfall (Phiên 3)

## 1. Hiện tượng lỗi (Symptom & Alert)
- **Watchdog Alert:** `feed_session_watchdog.py` báo cáo hàng loạt máy bị `Timeout/Quá giờ` ở Phiên 3 (ví dụ 21 máy M1, M2, M13, M16, M17, M18, M24, M25, M31, M35, M38, M39, M41, M49, M53, M55, M60, M64, M77, M78, M80).
- **User Prompt:** "Fix lỗi quá giờ up vidoe đi", "sao nhiều máy quá giờ đăng clip thế".
- **Artifact Evidence:** File `upload_result.json` tại `machines/machine_<N>/<timestamp>/upload_result.json` ghi nhận:
  ```json
  {
    "machine": 1,
    "row": 1,
    "status": "failed",
    "reason": "shift_upload_lock_timeout_fail_closed",
    "session_index": 3
  }
  ```
- **Đặc điểm:** Máy lướt Feed hoàn toàn thành công (`final_status: success`), nhưng vừa chuyển sang Upload Hook thì sau đúng 180s (bằng `lock_timeout`) thì văng lỗi `shift_upload_lock_timeout_fail_closed`.

---

## 2. Nguyên nhân cốt lõi (Root Cause)

1. **Hiệu ứng Thắt Cổ Chai Đồng Thời (Thundering Herd):**
   - Ở Phiên 3, 40–80 máy cùng hoàn thành lượt lướt feed trong khung 60–120 giây.
   - Hàng chục worker threads đồng thời bước vào `_run_upload_hook` và gọi `_ShiftUploadLedger.claim_reservation`.

2. **Thiếu In-Process Thread Synchronization:**
   - `_InterProcessFileLock` trên file `shift_upload_history.json.lock` chỉ sử dụng cơ chế file lock hệ điều hành (`msvcrt.locking` trên Windows).
   - Khi 40 threads trong cùng 1 tiến trình Python cùng mở file và thử lock liên tục với sleep jitter 0.02–0.08s, Windows kernel bị quá tải xử lý tranh chấp file handle (`EACCES` / `EDEADLK`), gây nghẽn I/O nghiêm trọng.

3. **Heavy Disk I/O & Scandir Dưới Exclusive Lock:**
   - Khi một thread giữ được file lock, nó thực hiện kiểm tra ground truth bằng `report_root.glob(f"run_{serial}_{date_compact}_*/report.json")` trên thư mục `D:/CodexRuntime/tiktok-video/runs`.
   - Thư mục `runs/` tích lũy hơn 48.000 thư mục qua nhiều tháng vận hành. Hàm `Path.glob()` phải quét toàn bộ danh sách 48.000 thư mục trên đĩa NTFS cho mỗi máy.
   - Thao tác quét đĩa kèm đọc/ghi JSON 250KB + `os.fsync` + `os.replace` tốn từ 100ms đến vài giây cho mỗi máy.

4. **Tràn Hàng Đợi (Queue Timeout Overflow):**
   - Với 40 máy xếp hàng tuần tự, tổng thời gian chờ của các máy ở cuối hàng vượt quá giới hạn `lock_timeout = 180.0s`.
   - Các máy này bị `TimeoutError` và ngắt an toàn dạng fail-closed (`shift_upload_lock_timeout_fail_closed`), khiến watchdog gom vào mục `Timeout/Quá giờ`.

---

## 3. Quy chuẩn Khắc phục (Standard Solution Pattern)

Khi gặp sự cố tranh chấp lock upload giữa các worker:

1. **Kết hợp In-Process Lock (`threading.RLock`) và File Lock OS:**
   - Khai báo một `_LOCAL_LEDGER_LOCK = threading.RLock()` ở cấp module.
   - Mọi thao tác truy cập `_InterProcessFileLock` bắt buộc phải acquire `_LOCAL_LEDGER_LOCK` trước.
   - Các threads trong cùng process sẽ xếp hàng êm dịu trong bộ nhớ Python, triệt tiêu 100% hiện tượng tranh chấp handle ở tầng Windows kernel.

2. **Tối ưu Hóa Truy Vấn Ground Truth Thư Mục Lớn:**
   - Tuyệt đối CẤM dùng `Path.glob()` quét toàn bộ thư mục lớn (>10.000 mục) khi đang giữ lock.
   - Sử dụng `os.scandir()` có điều kiện lọc sớm theo prefix `run_{serial}_{date_compact}_` hoặc chuyển phần quét này ra ngoài lock trước khi claim.

3. **Nâng Ngân Sách Timeout Khóa Phù Hợp Với Farm Lớn:**
   - Cấp `lock_timeout` tối thiểu 300.0s – 600.0s (vì hook upload có ngân sách tổng tới 2700s = 45 phút).
   - Truyền đúng `deadline_config` (chứa `_hard_deadline_monotonic`) để đảm bảo không bị ngắt oan khi ca làm việc vẫn còn thời gian.
