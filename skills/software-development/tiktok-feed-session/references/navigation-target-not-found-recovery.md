# Xử lý lỗi navigation target not found in XML & External Profile Drift

## 1. Hiện tượng & Triệu chứng
- Khi chuyển tab điều hướng (`home`, `friends`, `following`, `for-you`, `profile`) hoặc ở bước `verify_profile` cuối phiên nuôi acc:
- Script văng lỗi `navigation target <name> not found in XML` (ví dụ: `navigation target profile not found in XML`) và kích hoạt cờ giữ hiện trường `manual-needed`.

## 2. Nguyên nhân cốt lõi
1. **Lạc vào trang Profile người khác / Creator landing page:**
   - Trong quá trình vuốt lướt video hoặc tap tương tác, ngón tay vô tình bấm trúng avatar / link tên tác giả video khiến giao diện mở trang cá nhân của creator bên thứ ba (External Profile Page) hoặc màn hình chi tiết âm thanh/quảng cáo.
   - Các màn hình này không chứa thanh bottom bar điều hướng chuẩn (`Trang chủ`, `Bạn bè`, `Hộp thư`, `Hồ sơ`) hoặc bị che khuất.
2. **Kẹt Drawer / Modal:**
   - Account switcher sheet đang mở khi nick đã tick chọn sẵn (`selected="true"`), tap lại không tự đóng sheet.
   - Popup bảo mật hoặc prompt cập nhật chưa được dismiss.

## 3. Quy tắc xử lý chuẩn (Encoded Recovery)
1. **Tại hàm điều hướng hạ tầng (`tap_navigation_target` trong `calibrate_screens.py`):**
   - Khi tìm target navigation trong XML lần 1 không thấy (`point is None`), tự động kích hoạt `navigation_target_not_found_back_recovery`.
   - Gửi lệnh `KEYCODE_BACK` (phím 4) qua ADB để thoát trang lạc / overlay về màn hình chính.
   - Chờ 1.0s, capture lại XML hierarchy và tìm lại target điều hướng.
2. **Trong vòng lặp lướt feed (`feed_swipe_smoke.py`):**
   - Khi quan sát thấy `detected == "profile"` (lạc vào profile creator ngoài), tự động gửi phím `BACK` để quay lại For You feed trước khi lướt tiếp.
3. **Trong Account Switcher:**
   - Nếu tài khoản mục tiêu đã ở trạng thái `selected="true"`, gửi phím `BACK` để thu gọn drawer thay vì tap lại.
