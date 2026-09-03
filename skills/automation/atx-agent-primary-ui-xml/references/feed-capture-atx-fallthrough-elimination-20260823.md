# Chẩn đoán & Xử lý: Fallthrough xuống UiAutomator khi ATX trả XML rỗng trên Video Feed (2026-08-23)

## Hiện tượng (Evidence Máy 23, Row 1, 2026-08-23)
- Máy đang chạy TikTok feed session (`multi-machine-feed-session`) bị dừng phiên với lỗi:
  `capture-invalid: UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2`
- Hiện trường máy thật: TikTok đang mở bình thường, video feed đang phát (ảnh `screen.png` chụp video Đào Lê Phương Hoa).

## Nguyên nhân gốc (Root Cause)
1. **ATX trả rỗng/502 khi có video animation:**
   - Khi TikTok đang phát video animation, endpoint JSON-RPC ATX session `dumpWindowHierarchy [true]` có thể trả về `EMPTY_HIERARCHY` (node_count = 0, xml_bytes < 100) hoặc `502: Bad Gateway`.
2. **Code consumer có retry + reset ATX nhưng vẫn còn nhánh fallthrough:**
   - Tại `python_runner/core/ui_capture.py::capture_required_ui_result`:
     Đoạn đầu hàm đã có logic retry ATX 3 lần + `reset_atx_agent(adb)` + retry sau reset (tổng cộng 4 lần).
     Tuy nhiên, cả 4 lần đều không thu được XML hợp lệ (`<hierarchy` không có).
   - Code **không dừng lại (fail-closed)** mà tiếp tục chạy xuống dòng `capture_once()` phía dưới.
3. **Kích hoạt chuỗi uiautomator shell & recovery cũ:**
   - `capture_once()` gọi `capture_ui_xml(..., lightweight=True)` -> chạy shell command `uiautomator dump /sdcard/...`.
   - `uiautomator dump` bị Android kernel OOM kill (`SHELL_EXIT_137`).
   - Lỗi 137 kích hoạt recovery ladder cũ `recover_uiautomator_foreground_service` -> cố gọi `am startservice` chạy nền -> bị Android chặn với lỗi `Error: app is in background`.
   - Báo lỗi fatal `UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2` và dừng máy.

## Quy tắc bắt buộc (Invariant)
1. **CẤM FALLTHROUGH XUỐNG BẤT KỲ SHELL UIAUTOMATOR / LEGACY LADDER NÀO:**
   - Khi ATX retry 3 lần + `reset_atx_agent` + retry sau reset mà vẫn không có XML, hàm `capture_required_ui_result` BẮT BUỘC raise `UIDumpError("ATX_SESSION_UNAVAILABLE", ...)` hoặc trả `CaptureResult(None, ...)`.
   - Tuyệt đối không để sót bất kỳ dòng lệnh gọi `capture_ui_xml(lightweight=True)` hoặc các hàm recovery uiautomator cũ bên dưới.
2. **Trình tự chẩn đoán log khi gặp lỗi UiAutomator:**
   - Đọc kỹ `log.jsonl` và file artifact `ui_dump_error_*.json`.
   - Kiểm tra xem ATX đã chạy bao nhiêu attempt trước đó, có gọi `reset_atx_agent` chưa, và tại sao lại rơi xuống shell dump.
