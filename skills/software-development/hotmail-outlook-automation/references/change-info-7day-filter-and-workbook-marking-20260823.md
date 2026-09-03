# Hotmail Change-Info 7-Day Filter, Account Selection & Workbook Marking Rules (2026-08-23)

## 1. Mục tiêu & Nguyên tắc bảo vệ Hotmail BoxTaiKhoan
- **Quy định BoxTaiKhoan:**
  - Hàng Hotmail mua từ BoxTaiKhoan (đặc biệt là Type 2 OAuth2 393đ hoặc Type 1 có mail khôi phục tạm Getnada/fviainboxes): Shop từ chối bảo hành nếu sau 7 ngày không tự đổi thông tin bảo mật dẫn đến bị scan/back lại.
  - Đổi mật khẩu sẽ **hủy hoàn toàn refresh_token OAuth2 cũ** của shop, ngăn chặn bên thứ ba hoặc shop đọc trộm OTP.
  - **Gỡ bỏ mail khôi phục tạm:** Phải thay thế/gỡ mail ảo (getnada, fviainboxes) và gắn mail khôi phục chính chủ (`thanhdatbui1995@gmail.com`).
  - **Tránh bẫy 30 ngày (Pending 30 days):** Thao tác trực tiếp trong Security và xác nhận bằng OTP. Tuyệt đối KHÔNG chọn *"Tôi không còn quyền truy cập vào các thông tin này"*.

## 2. Tiêu chí lọc tài khoản Hotmail đủ điều kiện Change Info
1. **Domain:** Thuộc họ Microsoft (`@hotmail.com`, `@outlook.com`, `@live.com`, `@msn.com`).
2. **Thời gian ngâm (Age Gate):** `as_of_date - login_date >= 7 ngày` (login date lấy từ cột `ngày tạo` hoặc `mã phụ hồi` trong `gmail_clean_v2.xlsx` / artifact login verified).
3. **Chưa từng đổi mật khẩu (Un-changed):**
   - Bỏ qua các dòng có mật khẩu đã đổi theo format chuẩn farm (ví dụ `Taadaa2026M...`) hoặc đã có đánh dấu hoàn tất bảo vệ.
4. **Máy ADB Online & Device Lock:**
   - Serial máy phải online trên ADB (`adb devices`).
   - Phải acquire exclusive Device Lock trước khi chạy; chạy tuần tự từng máy để tránh va chạm mã OTP gửi về hộp thư khôi phục dùng chung (`thanhdatbui1995@gmail.com`).

## 3. Quy tắc cập nhật & Đánh dấu Excel (`gmail_clean_v2.xlsx`)
- **Cột C (`pass mail`):** Ghi mật khẩu mới ngẫu nhiên / chuẩn farm.
- **Cột E (`mail khôi phục`):** Ghi `thanhdatbui1995@gmail.com`.
- **Cột I (`token`):** Xóa trống (clear token) vì refresh_token cũ đã bị vô hiệu hóa.
- **Backup bắt buộc:** Phải tạo bản backup sibling (dạng `.backup_before_password_update_machine_XX_...`) trước khi lưu đè workbook.
