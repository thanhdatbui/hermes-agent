# Quy trình chọn lọc Hotmail Change Info & Quản lý Mail Khôi phục Tạm (2026-08-23)

## 1. Tiêu chí chọn lọc tài khoản Hotmail đủ điều kiện Change Info
1. **Thời gian ngâm (Aging Gate >= 7 ngày):**
   - Đọc ngày login/tạo từ `gmail_clean_v2.xlsx` (Cột G `ngày tạo` hoặc H `mã phụ hồi`).
   - Điều kiện: `(today - login_date).days >= 7`. Tránh bị Microsoft checkpoint khóa tài khoản do đổi mật khẩu quá sớm khi chưa có device trust.
2. **Bỏ qua tài khoản đã xử lý:**
   - Kiểm tra mật khẩu hiện tại (Cột C `pass mail`): nếu đã được đổi sang định dạng an toàn (ví dụ tiền tố `Taadaa2026M...`) hoặc đã có đánh dấu bảo vệ thì bỏ qua.
3. **ADB Online & Device Lock:**
   - Serial máy phải online trên ADB server (`5037`).
   - Bắt buộc acquire Device Lock (`acquire_device_lock`) trước khi thực hiện bất kỳ thao tác nào và release lock trong khối `finally`.

## 2. Thực trạng Flow Change Info (`flows/hotmail_change_info.py`)
- **Các bước hiện đã tự động hóa:**
  1. `task_change_password`: Đổi mật khẩu qua web Chrome (`account.live.com/password/Change`).
  2. `task_logout_devices`: Đăng xuất khỏi mọi nơi (`account.live.com/proofs/manage/additional` -> "Sign out everywhere").
  - Hai bước này đã đủ để **hủy bỏ toàn bộ session cũ và vô hiệu hóa vĩnh viễn refresh_token OAuth2** của bên bán (BoxTaiKhoan).
- **Trạng thái bước gỡ mail khôi phục tạm (Getnada / fviainboxes...):**
  - Hiện tại `task_remove_getnada` chưa được tích hợp vào flow tự động `hotmail_change_info.py` mà chỉ là stub trong `flows/hotmail_security.py`.
  - Khi Microsoft xuất hiện màn checkpoint `Hãy bảo vệ tài khoản của bạn` (`recover_account`), flow sẽ tự động gán mail khôi phục chính chủ `thanhdatbui1995@gmail.com`.
  - **Lưu ý bẫy 30 ngày:** Khi thao tác trong Security proofs, tuyệt đối không chọn "Tôi không còn quyền truy cập vào các thông tin này" vì Microsoft sẽ ép trạng thái chờ 30 ngày (Pending 30 days).

## 3. Cập nhật & Đánh dấu trạng thái vào Excel (`gmail_clean_v2.xlsx`)
Khi đổi pass và logout thành công:
- **Cột C (`pass mail`):** Ghi mật khẩu mới đã đổi.
- **Cột E (`mail khôi phục`):** Ghi `thanhdatbui1995@gmail.com` nếu đã qua bước recovery.
- **Cột I (`token`):** Clear trống (vì token shop đã vô hiệu).
- **Cột Ghi chú / Trạng thái:** Ghi `SECURED_YYYYMMDD` để các lượt chạy sau tự động bỏ qua.
- **Backup bắt buộc:** Phải tạo file snapshot sibling (ví dụ `.backup_before_password_update_machine_XX_...`) trước khi lưu đè.
