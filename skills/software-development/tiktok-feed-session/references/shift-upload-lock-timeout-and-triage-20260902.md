# Shift Upload Lock Timeout & Triage Pattern (2026-09-02)

## 1. Triage & Log Inspection Speed Rule
- **CẤM** quét đệ quy `grep -r` hoặc `find` qua toàn bộ thư mục `D:/Taadaa/runtime/kibe/live` hoặc `.ai-runs/` (gây timeout 900s và context bloat).
- **Quy trình chuẩn:**
  1. Xác định thư mục run gần nhất: `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<row-session-id>/<timestamp>/`.
  2. Đọc trực tiếp `summary.txt` ở root run dir để nắm tổng quan số máy success/skipped/manual-needed.
  3. Dùng Python one-liner đọc và đếm nhanh status trong `machines/*/upload_result.json` hoặc `machines/*/summary.txt`.
  4. Đọc ground-truth ledger đăng video tại: `C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json`.

## 2. Shift Upload Lock Contention (Lỗi `shift_upload_lock_timeout_fail_closed`)
- **Hiện tượng:** Khi chạy batch 80 máy, đến Phiên 3 (đăng video), các máy lướt feed xong gần như cùng lúc và đồng loạt chuyển sang bước hook upload.
- **Root Cause:** 
  - Tất cả các worker tranh chấp file lock `upload_ledger` để kiểm tra `already_uploaded_in_shift` và cấp phát slot upload.
  - Hàng đợi chờ lock bị dồn ứ quá thời gian timeout (budget), dẫn đến hàng loạt máy fail-closed với mã lỗi `shift_upload_lock_timeout_fail_closed`.

## 3. Fix Applied (2026-09-02) — `python_runner/flows/multi_machine_feed_session.py`
**File/Method:** `_ShiftUploadLedger.claim_reservation` (line ~2731)

**Before:** `_InterProcessFileLock(lock_file, deadline=hard_dl)` — dùng deadline toàn phiên (~30-45 phút). Khi 80 máy cùng lúc vào hàm này, deadline sắp hết → `TimeoutError` ngay lập tức.

**After:** Tách timeout lock riêng (`lock_timeout = 180s` mặc định, cấu hình được qua `shift_upload_lock_timeout_seconds`):
```python
lock_timeout = 180.0
try:
    lock_timeout = float(config.get("shift_upload_lock_timeout_seconds", lock_timeout))
except Exception:
    pass
lock_deadline = None if hard_dl is None else min(hard_dl, time.monotonic() + lock_timeout)
with _InterProcessFileLock(lock_file, timeout=lock_timeout, deadline=lock_deadline):
    ...
```

**Behavior:**
- Lock timeout mặc định 180s (cấu hình được), độc lập với `hard_dl` của phiên.
- `lock_deadline = min(hard_dl, now + lock_timeout)` — bảo đảm không bao giờ vượt quá deadline phiên, nhưng thường dài hơn thời gian chờ thực tế.
- `_InterProcessFileLock` có jitter/backoff built-in (0.02-0.08s), 80 máy sẽ chia đều vào cửa sổ 180s.

**Test Result:** 101 tests pass (`test_multi_machine_feed_session.py`).

## 4. Triage Pattern for Upload Failures & Machine Offline Check
Khi người dùng hỏi "Sao nhiều máy không đăng video", quy trình điều tra chuẩn gồm 3 bước:

1. **Kiểm tra Shift Upload History:**
   Đọc `C:\\ProgramData\\Taadaa\\tiktok-upload-concurrency-v1\\shift_upload_history.json` để lấy danh sách máy đã `status: "success"` theo ngày logic và ca (row). Tránh kết luận sai khi phiên chạy bù/retry nhiều lần.

2. **Kiểm tra Device Offline vs Subprocess Failure:**
   Với các máy chưa upload, map serial qua `taikhoan_run_safe.xlsx` và kiểm tra `report.json` tại `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<YYYYMMDD>_*/report.json`:
   - **`[DEVICE_OFFLINE]`**: Thiết bị mất kết nối ADB (hub/cáp USB), cần cắm lại hoặc restart ADB daemon.
   - **`[ACCOUNT_SWITCHER_FAILED]` / `SWITCHER_NOT_CONFIRMED`**: Kẹt màn hình chọn tài khoản hoặc popup onboarding trên TikTok app.
   - **`video_not_rendered`**: File MP4 tiếp theo chưa được render trong thư mục media.

## 5. Workbook Serial Drift (Case 73, Machine 75..80)
**Root Cause:** `Tik2.xlsx` and `tik3.xlsx` Column B (`device ID`) got swapped during creation — machine 75↔79, 76↔78, 77↔80.

**Why Sync Cron Didn't Catch It:** 5-min `sync-tik-workbooks.py` only synced Column C (`ID`), never validated Column B (`device ID`).

**Fix:** 
- `sync-tik-workbooks.py` now maintains `canonical_serials` (Tik1.xlsx + EXTRA_MACHINES + master DAT) and enforces Column B every sync cycle.
- Added `EXTRA_MACHINES` dict with hardcoded serials for 75..80.
- Added `_is_valid_serial()` filter to reject date-like garbage.
- New test `test_sync_fixes_swapped_serial` validates self-healing.

**Key Lesson:** Sync cron MUST validate Column B (device ID) every cycle — not just Column C (ID).
