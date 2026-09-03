# Incident Triage: UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2 Cascade (2026-08-23)

## 1. Hiện tượng & Triệu chứng
- Alert Telegram: `🚨 [MÁY XX] DỪNG PHIÊN`
- Script: `multi-machine-feed-session`
- Lý do: `capture-invalid: UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2`
- Hiện trường máy: TikTok vẫn đang mở và phát video feed bình thường, không kẹt splash/treo app.

## 2. Chuỗi phản ứng dây chuyền (Cascade Root Cause)
1. **ATX Session Tạm thời Không đọc được XML:**
   - Trong quá trình phát video feed có animation, lệnh ATX JSON-RPC `dumpWindowHierarchy [true]` gặp phản hồi chậm, trả mã `HTTP 502: Bad Gateway` hoặc XML rỗng (`EMPTY_HIERARCHY`).
2. **Fallthrough trong Consumer (`python_runner/core/ui_capture.py`):**
   - Hàm `capture_required_ui_result` có khối ATX-primary ở đầu hàm (3 retry + 1 hard reset).
   - Tuy nhiên, sau khi các lần thử ATX thất bại, hàm **KHÔNG fail-closed** mà rơi xuống dòng tiếp theo gọi `capture_once()` với tham số `lightweight=True`.
3. **Kích hoạt Shell `uiautomator dump`:**
   - Khi `capture_ui_xml` nhận `lightweight=True`, shared core tự động bỏ qua ATX và thực thi lệnh shell `uiautomator dump /sdcard/...`.
   - Trên thiết bị Samsung Galaxy S7 (Android 7/8), shell dump khi TikTok đang phát video bị hệ điều hành OOM kill (`dump_exit_code: 137` / `SHELL_EXIT_137`).
4. **Kích hoạt Recovery Ladder cũ (`capture_recovery.py`):**
   - Lỗi `SHELL_EXIT_137` kích hoạt handler `tiktok_uiautomator_foreground_service_v2`.
   - Handler này cố gắng khởi động lại uiautomator service bằng lệnh `am startservice com.github.uiautomator/.Service`.
   - Android chặn khởi chạy background service (`Error: app is in background uid null`), đánh dấu trạng thái `FINAL_BLOCKED` với signature `UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2`.

## 3. Quy tắc & Giải pháp triệt để
- **Cấm Fallthrough sang `capture_once(lightweight=True)`:**
  - Trong consumer `ui_capture.py`, nếu toàn bộ các lần thử ATX (kể cả sau `reset_atx_agent`) đều không trả về XML hợp lệ, phải raise `UIDumpError("ATX_SESSION_CAPTURE_FAILED", ...)` hoặc trả về CaptureResult lỗi ngay lập tức.
  - Tuyệt đối không để code trôi xuống lệnh gọi shell dump cũ.
- **Loại bỏ / vô hiệu hóa handler `tiktok_uiautomator_foreground_service_v2`:**
  - Quy trình khôi phục UI service trên farm bắt buộc sử dụng `reset_atx_agent(adb)` (dùng `monkey -p com.github.uiautomator 1` để warmup stub), không bao giờ dùng `am startservice`.
