# Case 114: Screen Capture Invalid & Feed Not Confirmed (ATX Session Loss Recovery)

## 1. Triệu chứng & Bối cảnh
Khi chạy feed session hoặc calibrate screen, bước kiểm tra xác nhận feed thất bại với lỗi:
`screen capture invalid; feed not confirmed` hoặc fallback sang force-stop app không cần thiết.

Nguyên nhân gốc rễ:
- Khi dump UI XML gặp sự cố (ví dụ `ATX_SESSION_UNAVAILABLE` hoặc `ui_dump_failed`), `calibrate_screens.py` trước đây chỉ cho phép fallback sang `detect_feed_controls` (nhận diện hình ảnh thanh điều hướng TikTok) nếu `xml_error_code` thuộc một danh sách hạn chế (`uiautomator_idle_state_error`, `ui_dump_file_missing`, `ui_dump_command_failed`, `uiautomator_null_root_node`).
- Khi lỗi là `ATX_SESSION_UNAVAILABLE` hoặc biến thể chữ thường, bộ phân loại bỏ qua nhận diện hình ảnh dù ảnh chụp màn hình hoàn toàn bình thường và rõ nét giao diện Feed Home.

## 2. Giải pháp 2 lớp (Two-tier Fix)

### Lớp 1: Fallback nhận diện hình ảnh (`flows/calibrate_screens.py`)
Mở rộng tập hợp mã lỗi chấp nhận fallback `detect_feed_controls`:
```python
and (
    xml_error_code in {"uiautomator_idle_state_error", "ui_dump_file_missing", "ui_dump_command_failed", "uiautomator_null_root_node", "ATX_SESSION_UNAVAILABLE", "atx_session_unavailable", "ui_dump_failed"}
    or xml_error_code.lower() in {"atx_session_unavailable", "ui_dump_failed"}
)
```
Nếu dump XML bị hỏng nhưng screenshot nhận diện được feed controls (For You / Following / Home), màn hình vẫn được phân loại chính xác là `home`.

### Lớp 2: Phục hồi ATX Agent trước khi Force-Stop (`flows/feed_swipe_smoke.py`)
Trong `_capture_step`, khi `_capture_retry_needed` kích hoạt mà ứng dụng TikTok vẫn đang ở foreground:
- Không vội vàng force-stop app.
- Gọi `reset_atx_agent(ctx.adb, timeout=15)` từ `automation_core.persistent_ui`.
- Chờ 1.0s và thực hiện capture lại bằng `capture_calibration_attempt`.
- Nếu feed được xác nhận sau khi reset ATX, luồng swipe tiếp tục bình thường mà không làm mất phiên xem feed của tài khoản.

## 3. Lưu ý khi viết Unit Test
Trong `flows.calibrate_screens`:
- Hàm chụp ảnh nội bộ là `_capture_valid_screenshot` (trả về `screenshot_bytes, screenshot_path, error`).
- Hàm dump UI XML nội bộ là `capture_required_ui`.
- Không patch `capture_screenshot_file` hoặc `dump_ui_xml_file` vì các hàm này không nằm ở namespace của `calibrate_screens`.
