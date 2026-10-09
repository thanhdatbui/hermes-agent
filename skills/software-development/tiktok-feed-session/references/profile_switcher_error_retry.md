# Profile Switcher Error Screen Retry Pattern

## Context
Trong flow `verify_and_switch_profile` (`python_runner/flows/feed_swipe_smoke.py`), khi đã chọn đúng tài khoản qua exact switcher row (`selected_account_by_exact_switcher`), TikTok có thể hiển thị thông báo lỗi mạng/kết nối kèm nút "Thử lại" thay vì tải ngay hồ sơ mới.

## Error Indicators
- Resource ID: `com.ss.android.ugc.trill:id/dcj`
- Text tiếng Việt: `"thử lại"` hoặc `"đã xảy ra lỗi"`

## Recovery Handling
1. Kiểm tra XML `(recaptured_xml or "").lower()` có chứa các indicator trên không.
2. Nếu có:
   - Tap nút Thử lại tại tọa độ `540, 1436` với timeout 5s:
     ```python
     ctx.adb.shell(["input", "tap", "540", "1436"], timeout=ctx.timeout("adb_seconds", 5))
     ```
   - Chờ `time.sleep(3.0)`.
3. Nếu không có indicator lỗi nhưng vẫn chưa verified: chờ `time.sleep(2.0)`.
4. Gọi lại `_read_profile_identity_with_add_phone_guard(...)` để lấy XML và profile identity mới nhất.
5. Re-check username/display name matches và cập nhật cờ `verified` cùng `selected_account_recaptured_without_handle`.
