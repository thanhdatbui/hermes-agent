# Account Switcher Active Account Overlay Pitfall

## Triệu chứng & Bối cảnh
- **Lỗi báo**: `navigation target profile not found in XML` trong bước `profile_preflight_verify_2` hoặc `_navigate_profile_for_preflight`.
- **Hiện trường**: Màn hình thiết bị đang ở Profile, nhưng bị che phủ nửa dưới bởi popup **"Chuyển đổi tài khoản"** (Bottom Sheet modal).
- **Tài khoản mục tiêu**: Đã được chọn (có dấu tích đỏ $\checkmark$) ngay trong danh sách tài khoản của popup.

## Nguyên nhân gốc (Root Cause)
1. Trong luồng `profile_preflight`, khi cần chuyển sang tài khoản mong muốn (ví dụ `dongoc2504` ở Row 2), script kích hoạt popup switcher (`Chuyển đổi tài khoản`).
2. Script tìm thấy node của tài khoản mong muốn và thực hiện lệnh tap `tap_expected_account`.
3. Khi tài khoản được tap **trùng khớp với tài khoản đang đăng nhập hiện tại** (active sẵn trên TikTok), hệ thống TikTok Android **không tự động dismiss popup**.
4. Luồng tiếp tục gọi `_navigate_profile_for_preflight` để tìm tab điều hướng `Hồ sơ` / `Profile` ở bottom navigation (`bounds=[864,1794][1080,1920]`).
5. Vì popup switcher chiếm trọn nửa dưới (`bounds=[0,852][1080,1920]`), node bottom navigation bar hoàn toàn vắng mặt trong cây UI XML dump được.
6. `find_navigation_target` trả về `not-found`, kích hoạt cơ chế an toàn giữ hiện trường.

## Giải pháp xử lý (Pattern)
1. Sau khi tap chọn tài khoản trong switcher:
   - Dành 1-2s chờ UI phản hồi.
   - Dump lại XML và kiểm tra xem popup switcher có còn hiển thị hay không (`is_switcher_open` hoặc `_is_profile_account_switcher_xml`).
2. Nếu popup switcher vẫn còn mở:
   - Tap nút `Đóng` (`✕` ở `[936,864][1056,996]` hoặc node `content-desc="Đóng"`) hoặc gửi phím `BACK` để hạ switcher sheet xuống.
3. Sau khi switcher sheet đã đóng hoàn toàn, mới tiến hành bước `_navigate_profile_for_preflight` và verify profile.
