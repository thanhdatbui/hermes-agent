# Sponsored Check ATX Session Unavailable Triage & Recovery (2026-08-24)

## Triệu chứng & Bối cảnh
- **Alert Telegram:** `🚨 [MÁY XX] DỪNG PHIÊN • Script: multi-machine-feed-session • Lý do: capture-invalid: ATX_SESSION_UNAVAILABLE artifact=...\sponsored_check`
- **Hiện trường thiết bị:** TikTok trên máy vẫn đang mở bình thường trên tab Đề xuất (For You), video chạy mượt mà, không dính CAPTCHA hay checkpoint.

## Nguyên nhân gốc (Root Cause)
1. Trong vòng lặp `feed_swipe_smoke.py`, trước mỗi swipe ở chế độ `is_feed_session`, flow gọi `_sponsored_present(ctx)` để kiểm tra video quảng cáo.
2. `_sponsored_present` kích hoạt `_capture_xml_text(ctx, "sponsored_check")` -> gọi `capture_required_ui`.
3. Khi thiết bị yếu (Samsung Galaxy S7) chạy animation video TikTok dài, tiến trình nền `com.github.uiautomator` (stub) có thể bị Android OOM/killer ngắt ngầm, dẫn đến `ATX_SESSION_STUB_NOT_RUNNING` (`stub_process_lines: []` trong `ps -A`).
4. Khi ATX retry/reset nội bộ không kịp bind lại JSON-RPC trong timeout ngân sách của step, `capture_required_ui_result` fail-closed an toàn và raise `UIDumpError("ATX_SESSION_UNAVAILABLE")`, dừng phiên để giữ hiện trường (`preserve_blocker_screen`).

## Quy trình xử lý & Phục hồi Hiện trường
1. **Kiểm tra hiện trường qua ADB screencap:**
   - Chụp màn hình bằng `adb -s <serial> exec-out screencap -p` để xác nhận màn hình thực tế là TikTok feed bình thường.
2. **Kiểm tra trạng thái ATX qua `automation_core.persistent_ui`:**
   ```python
   from automation_core.adb import AdbClient
   from automation_core.persistent_ui import capture_atx_session_ui, reset_atx_agent
   client = AdbClient(adb_path=..., serial=...)
   res = capture_atx_session_ui(client, timeout=15)
   # Nếu health == 'UNHEALTHY' và attempts ghi nhận ATX_SESSION_STUB_NOT_RUNNING:
   reset_atx_agent(client, timeout=20)
   # Verify lại:
   res = capture_atx_session_ui(client, timeout=15)
   assert res.health == 'VERIFIED_HEALTHY' and len(res.xml) > 20000
   ```
3. **Báo cáo kết quả:** Gửi ảnh hiện trường thật bằng `MEDIA:<path>` kèm xác nhận ATX đã được phục hồi khỏe mạnh (`VERIFIED_HEALTHY`).
