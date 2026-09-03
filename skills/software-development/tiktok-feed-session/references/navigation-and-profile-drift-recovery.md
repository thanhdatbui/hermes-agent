# Navigation Target & Profile Drift Recovery

## 1. Hiện tượng & Triệu chứng
- Khi chạy `multi-machine-feed-session` hoặc `feed-session-smoke`, script có thể gặp lỗi:
  `navigation target profile not found in XML` hoặc `navigation target for-you not found in XML`.
- **Nguyên nhân chính**:
  1. Trong lúc lướt feed / tương tác ngẫu nhiên, tap nhầm vào avatar/tên người dùng hoặc hashtag khiến TikTok mở trang Profile bên ngoài (`External Creator Profile`).
  2. Bảng chọn tài khoản (`Account Switcher`) hoặc popup cập nhật tài khoản còn mở đè lên màn hình.
  3. Thanh điều hướng đáy (`Bottom Navigation Bar`: Home, Friends, +, Inbox, Profile) bị che khuất trong UI XML dump.

## 2. Kiến trúc xử lý 2 tầng (Two-Layer Recovery)

### Tầng 1: Hạ tầng điều hướng (`calibrate_screens.py` - `tap_navigation_target`)
- Khi tìm kiếm element mục tiêu trong XML thất bại (`point is None`):
- Hệ thống tự động kích hoạt `navigation_target_not_found_back_recovery`:
  1. Gửi lệnh `KEYCODE_BACK` (phím 4 qua `input keyevent 4`).
  2. Nghỉ 1.0 giây để giao diện TikTok hoàn tất animation quay lại màn hình trước.
  3. Dump lại UI XML và tìm lại element điều hướng đích.
- Giúp bảo vệ an toàn cho toàn bộ các luồng chuyển tab (bao gồm cả `verify_profile` sau khi hoàn thành session nuôi nick).

### Tầng 2: Vòng lặp lướt video (`feed_swipe_smoke.py` - `_recover_post_swipe_to_for_you`)
- Nếu phát hiện màn hình hiện tại bị trôi sang `profile` người khác trong lúc lướt feed:
  1. Gửi `KEYCODE_BACK` để thoát profile ngoài.
  2. Điều hướng lại tab `For You` hoặc `Home`.
  3. Nếu điều hướng For You vẫn chưa lộ, gửi tiếp 1 lệnh Back và tap `Home` bottom tab để tiếp tục chuỗi nuôi nick mà không làm dừng phiên.

## 3. Quy tắc kiểm tra & Tránh trùng lặp
- Không sửa lặp lại logic ở nhiều nơi gây xung đột.
- Tầng UI switcher (`verify_and_switch_profile`): Nếu nick đã `selected="true"`, bấm phím Back đóng modal chứ không tap lại.
- Luôn chạy kiểm tra unit test trước khi chốt:
  ```bash
  pytest python_runner/tests/test_calibrate_screens.py python_runner/tests/test_feed_swipe_smoke.py
  ```
