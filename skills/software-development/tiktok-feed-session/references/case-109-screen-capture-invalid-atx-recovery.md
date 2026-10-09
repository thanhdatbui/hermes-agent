# Case 109: Screen Capture Invalid / ATX Session Unavailable Auto-Recovery

## 1. Triệu chứng Hiện trường
- Alert farm: `screen capture invalid; feed not confirmed` (thường xuất hiện trên máy cấu hình yếu/cũ như Samsung S7, máy 19).
- TikTok thực tế vẫn đang hiển thị ở foreground (`MainActivity` / `SplashActivity`), video For You đang chạy bình thường.
- Session lướt feed bị fail-closed hoặc force stop oan do dump UI XML thất bại và không fallback được sang nhận diện feed qua screenshot.

## 2. Nguyên nhân gốc rễ
1. **Thiếu mã lỗi trong Fallback của `flows/calibrate_screens.py`**:
   - Dòng ~834: điều kiện lọc lỗi XML degraded trước đây chỉ kiểm tra:
     `xml_error_code in {"uiautomator_idle_state_error", "ui_dump_file_missing", "ui_dump_command_failed", "uiautomator_null_root_node"}`
   - Khi ATX daemon bị chết hoặc rơi session, mã lỗi trả về là `"ATX_SESSION_UNAVAILABLE"` hoặc `"ui_dump_failed"`.
   - Do thiếu 2 mã lỗi này, hàm bỏ qua bước `detect_feed_controls(screenshot_path.read_bytes())` mặc dù ảnh chụp screenshot có đầy đủ icon feed controls, khiến `detected_screen` trả về None -> `feed not confirmed`.

2. **Thiếu cơ chế Auto-Recovery ATX Agent trong `flows/feed_swipe_smoke.py`**:
   - Tại `_capture_step()` (dòng ~3680-3710), khi `_capture_retry_needed` kích hoạt do capture invalid / ATX rớt:
   - Nếu TikTok vẫn đang ở foreground (`focus_package in tiktok_pkgs`), script trước đây nhảy thẳng vào `_capture_invalid_force_stop_recovery` (force stop và relaunch app tốn 15-20s) hoặc fail-closed.
   - Script cần auto-recover ATX agent trước khi force stop:
     ```python
     from automation_core.persistent_ui import reset_atx_agent
     reset_atx_agent(ctx.adb, timeout=15)
     time.sleep(1.0)
     recaptured = capture_calibration_attempt(ctx, step, len(attempts) + 1, ...)
     ```
     Nếu `_is_feed_confirmed(recaptured)` trả về True -> gán `attempt = recaptured` và thoát vòng lặp retry thành công.

## 3. Quy chuẩn Khắc phục & Test Case
- Đảm bảo bổ sung `"ATX_SESSION_UNAVAILABLE"` và `"ui_dump_failed"` vào danh sách degraded XML errors ở mọi vị trí fallback image-based.
- Khi gặp lỗi capture invalid / ATX unavailable, luôn kiểm tra `get_focused_activity(ctx)`: nếu TikTok vẫn đang ở foreground, ưu tiên restart ATX service thay vì force stop TikTok.
- Viết unit test giả lập `ATX_SESSION_UNAVAILABLE` với ảnh screenshot feed controls hợp lệ để đảm bảo pipeline nhận diện trả về `home` và feed confirmed.
