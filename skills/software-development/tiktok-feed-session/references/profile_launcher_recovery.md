# Profile Verification & Launcher Focus Recovery

## Vấn đề
Khi thực hiện bước verify profile hoặc preflight navigation trong TikTok feed session (`flows/feed_swipe_smoke.py`), nếu app bị crash hoặc văng về màn hình Launcher (Home launcher):
- `navigation.ok` trả về `False` với reason dạng `navigation target profile not found in XML` hoặc `target not found` hoặc status `not-found`.
- `navigation.focused_package` đôi khi bị rỗng hoặc chưa kịp cập nhật, dẫn tới logic launcher detection thông thường không bắt được.

## Giải pháp kỹ thuật (Contract chuẩn)
1. **Kiểm tra focus thực tế**:
   Gọi `actual_focus = get_focused_activity(ctx)` để lấy package thực tế đang hiển thị trên thiết bị.
2. **Điều kiện kích hoạt relaunch recovery**:
   Kích hoạt relaunch khi:
   - `_is_launcher_focus_loss(...)` trả về True
   - `actual_pkg` thuộc danh sách `LAUNCHER_PACKAGES` hoặc chứa từ khoá launcher, hoặc không nằm trong tập TikTok package hợp lệ
   - `is_target_not_found` = True (lý do chứa `not found in xml`, `target not found`, hoặc status là `not-found`)
3. **Relaunch & Poll**:
   Gọi `_relaunch_and_poll_tiktok_focus(ctx, after_launch_delay_seconds=POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS)` để đưa TikTok trở lại foreground trước khi tiếp tục flow.

## Lưu ý kiểm thử (Unit test)
- Khi viết unit test trong `tests/test_feed_swipe_smoke.py`, đảm bảo kiểm tra cấu trúc module của `flows/feed_swipe_smoke.py` trước khi import hàm (tránh import các hàm được định nghĩa nested hoặc mang tên khác ở module level).
