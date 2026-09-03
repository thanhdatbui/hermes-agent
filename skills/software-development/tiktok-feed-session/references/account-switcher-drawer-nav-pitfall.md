# Pitfall: Account Switcher Drawer Obscures Bottom Navigation

## Triệu chứng
Lỗi `navigation target profile not found in XML` xảy ra trong flow `profile_preflight_verify` (hoặc sau bước switch account).

## Nguyên nhân gốc rễ
1. Khi script mở drawer "Chuyển đổi tài khoản" (bottom sheet chiếm từ Y=420 đến Y=1920) để switch sang account đích.
2. Nếu account đích đã được chọn sẵn (checked) hoặc sau khi tap switch sheet không tự dismiss/đóng ngay, drawer tiếp tục hiển thị trên màn hình.
3. Khi drawer đang mở, toàn bộ bottom navigation bar ở đáy màn hình (vùng Y=1794 - 1920 chứa nút tab Hồ sơ / Profile) bị che khuất trong UI XML dump.
4. Parser XML tìm kiếm node navigation target `Profile` / `Hồ sơ` không thấy -> quăng lỗi `navigation target profile not found in XML` và kích hoạt `manual-needed` giữ hiện trường.

## Cách xử lý chuẩn
- Sau khi tap switch account hoặc khi phát hiện account đã được tick sẵn trong switcher sheet, kiểm tra nếu drawer "Chuyển đổi tài khoản" vẫn còn hiển thị trong XML (node `Chuyển đổi tài khoản` / resource-id `com.ss.android.ugc.trill:id/fue` / nút đóng `Đóng` tại `[936,432][1056,564]`):
  1. Thực hiện tap nút Đóng `[936,432][1056,564]` hoặc gửi `keyevent BACK` để đóng drawer.
  2. Chờ giao diện render lại bottom bar rồi mới gọi `_navigate_profile_for_preflight` hoặc tìm tab Profile.
