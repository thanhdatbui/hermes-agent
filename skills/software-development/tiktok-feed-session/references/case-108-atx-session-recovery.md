# Case 108: ATX Session Unavailable Recovery in Profile Navigation

## Hiện tượng & Bối cảnh
- **Lỗi:** `ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset artifact=...profile\navigation`
- **Hiện trường:** TikTok vẫn đang mở ở foreground Home/Feed (`SplashActivity`), tiến trình uiautomator stub vẫn còn nhưng HTTP/RPC session bị lỗi hoặc đứt quãng.
- **Mẫu máy gặp lỗi:** Máy 76 (serial `9885b64d56305a3731`), Máy 80 (serial `ce061606cd45950405`).

## Anti-Pattern Cần Tránh
1. **Bẫy logic `navigation_error is None` triệt tiêu recovery:**
   Khi capture UI ban đầu ném `UIDumpError`, `navigation_error` đã được gán exception. Nếu kiểm tra `if point is None and navigation_error is None:`, toàn bộ logic recovery bị bỏ qua, runner fail-closed ngay lập tức mà không thử phục hồi.
2. **Preflight thiếu tầng ATX recovery khi app vẫn foreground:**
   Trong `_navigate_profile_for_preflight`, chỉ kiểm tra nhánh `is_launcher` để relaunch TikTok mà không có nhánh reset ATX agent khi app vẫn ở TikTok foreground.
3. **Assignment Manifest thiếu máy (Máy 75..80):**
   Trong `C:\Users\Kibe\AppData\Local\automation-core\assignments\tiktok-feed.json`, danh sách `resources` phải đủ `machine:1` đến `machine:80`. Nếu thiếu, `run-feed-session.ps1` sẽ fail-closed với `TARGET_OUTSIDE_ASSIGNMENT:machine:<N>` khi chạy canary hoặc batch.

## Quy Trình Phục Hồi Chuẩn (Case 108 Fix)
1. **Tự động phục hồi ATX tại `tap_navigation_target`:**
   - Khi bắt `UIDumpError`, kiểm tra `get_focused_activity(ctx)`.
   - Nếu app vẫn thuộc `tiktok_pkgs`:
     - Gọi `automation_core.persistent_ui.reset_atx_agent(ctx.adb, timeout=15)`.
     - `time.sleep(1.0)`.
     - Chụp lại UI XML bằng `capture_required_ui`.
     - Nếu thành công và tìm thấy target, xóa `navigation_error = None`, `navigation_status = "pass"` và tap navigation target.
     - Nếu vẫn fail: bảo toàn đúng `UIDumpError` gốc.
   - Nếu app đã mất focus (ở launcher / app khác): không reset ATX mù quáng, bảo toàn lỗi.
2. **Bảo toàn guard an toàn phím BACK (Case 105):**
   - Tuyệt đối không gửi `input keyevent 4` (KEYCODE_BACK) khi màn hình đang ở Home/Feed hoặc khi thiết bị đã văng về Launcher.
3. **Tầng bảo vệ thứ hai tại `_navigate_profile_for_preflight`:**
   - Nếu `not navigation.ok` với lỗi `ATX_SESSION_UNAVAILABLE` hoặc `UI_DUMP_FAILED` và TikTok vẫn foreground, gọi `reset_atx_agent` và retry `tap_navigation_target` 1 lần an toàn.

## Canary Test Pattern
Khi chạy canary test kiểm chứng sau khi fix:
1. **Tránh xung đột Python environment:**
   Luôn chạy với `env -u PYTHONPATH` vì biến môi trường PYTHONPATH từ terminal/agent có thể chứa các thư viện của runtime khác gây lỗi xung đột (ví dụ Pillow `_imaging`).
   ```bash
   env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe -u \
     "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" ...
   ```
2. **Xử lý thiết bị đang dính lock `blocked`:**
   Nếu máy đang giữ file lock `status: blocked` từ phiên lỗi trước trong `~/.codex/device-locks/`, truyền thêm flag `--full-scope-takeover` để chiếm quyền điều khiển và dọn dẹp lock cũ an toàn:
   ```bash
   --full-scope-takeover
   ```
3. **Unit tests kiểm chứng:**
   - `python_runner/tests/test_navigation_atx_recovery.py` (6 tests)
   - `python_runner/tests/test_calibrate_screens.py` (40 tests)
