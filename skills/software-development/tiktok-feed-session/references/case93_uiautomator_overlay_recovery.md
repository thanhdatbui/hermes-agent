# Case 93: UIAutomator App Overlay & TikTok Focus Recovery

## Hiện tượng
Máy (ví dụ Máy 24) gặp alert `TikTok focus lost` khi app `com.github.uiautomator` (developer options / atx agent shortcut) nổi lên che mất giao diện TikTok tại các nhịp baseline hoặc sau khi swipe.

## Root Cause
- Service uiautomator / atx-agent khi gặp sự cố hoặc restart có thể spawn activity của `com.github.uiautomator` đè lên foreground.
- Engine chưa đăng ký detector / dismisser cho `uiautomator_app_overlay` trong `benign_popup_registry.py` và `classifier.py`.
- Các hàm kiểm tra `_is_launcher_focus_loss` và `_relaunch_and_poll_tiktok_focus` trong `feed_swipe_smoke.py` chưa chủ động dọn dẹp các overlay app lingering trước khi relaunch TikTok.

## Giải pháp Đã Triển Khai
1. **`flows/benign_popup_registry.py`**:
   - Thêm `_detect_uiautomator_overlay`: bắt marker `com.github.uiautomator`, `stop atx agent`, `uiautomator helper`, `uiautomator2`.
   - Thêm `_dismiss_uiautomator_overlay`: gửi KEYCODE_BACK + gọi `am start` đưa package TikTok trở lại foreground.
   - Đăng ký entry `uiautomator_app_overlay` với priority 98.
2. **`core/benign_popup.py`**:
   - Thêm hàm `detect_uiautomator_overlay` hỗ trợ trích xuất element popup.
3. **`core/classifier.py`**:
   - Đăng ký nhận diện `UIAutomator app / developer options overlay detected` -> gán screen `GENERIC_POPUP_SCREEN`.
4. **`flows/feed_swipe_smoke.py`**:
   - Cập nhật `_is_launcher_focus_loss`: nhận diện thêm khi `detected` chứa `uiautomator` hoặc `com.github.uiautomator`.
   - Cập nhật `_relaunch_and_poll_tiktok_focus`: thêm lệnh `am force-stop com.github.uiautomator` trước khi relaunch và bổ sung nhịp retry `input keyevent 4` + `monkey` launch.
   - Bổ sung `uiautomator_app_overlay` vào `benign_drain_allowlist`.
5. **Unit Tests**:
   - `test_detect_uiautomator_overlay_and_registry_match` trong `test_benign_popup_registry.py`.
