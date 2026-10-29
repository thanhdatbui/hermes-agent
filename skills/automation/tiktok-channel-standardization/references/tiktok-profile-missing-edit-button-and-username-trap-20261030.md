# TikTok Username Editing Constraints & Missing "Edit Profile" Variant Trap

## 1. Bản Chất Layout Profile Khuyết "Sửa Hồ Sơ"
Trên một số phiên bản TikTok Android (đặc biệt các biến thể Samsung S7 hoặc tài khoản reg tự động chưa hoàn tất onboarding):
- **Giao diện không có nút "Sửa hồ sơ" (Edit Profile):**
  - Màn hình chỉ hiển thị nút `+ Thêm tiểu sử` (Add Bio) lớn ở giữa.
  - Dòng handle `@username` có thể bấm được nhưng khi tap vào, hệ thống chỉ điều hướng vào trang chỉnh sửa **Tiểu sử (Bio)** thay vì trang đổi Username.
  - Trong `Cài đặt và quyền riêng tư` -> `Tài khoản` -> `Thông tin tài khoản`: Chỉ chứa thông tin Email, Số điện thoại, Ngày sinh và Khu vực tài khoản. Tuyệt đối **không có mục đổi Username** tại đây.

## 2. Kỷ Luật Điều Phối & Triage Trước Khi Đổi Username
- **Kiểm tra thực tế giao diện trước khi cam kết:**
  - Không cam kết đổi username ngay lập tức khi chưa kiểm tra nút `Sửa hồ sơ`.
  - Nếu profile thiếu nút `Sửa hồ sơ` chuẩn và deeplink bị rơi về trang chính/bio, dừng lại báo cáo hiện trường thực tế, không thực hiện tap mù hay swipe cưỡng bức.
- **Quy tắc an toàn dữ liệu:**
  - Không tự tiện sửa ID trong sổ cái Excel / SQLite DB khi chưa đổi thành công trên app TikTok thật.
