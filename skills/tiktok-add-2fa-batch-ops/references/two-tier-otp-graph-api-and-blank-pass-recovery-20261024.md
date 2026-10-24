# Quy Trình Bật 2FA & Đặt Mật Khẩu TikTok Qua Graph API Token 2 Tầng (24/10/2026)

## 1. Bản Chất Kỷ Luật: CẤM Bỏ Qua Kiểm Tra Pass TikTok Khi Đổi Bảo Mật Hotmail
- **Nguyên tắc bất biến:** Tài khoản TikTok bắt buộc phải có đầy đủ cả **Username (Cột 3)** VÀ **Password (Cột 4)** trong Excel (`taikhoan_dat_v2_updated .xlsx`) thì mới được Supervisor GPM cấp quyền chuyển từ `WAIT_7D` sang `CHANGE_INFO` để đổi mật khẩu Hotmail.
- **Hậu quả nếu đổi pass Hotmail trước:** Khi TikTok yêu cầu tạo mật khẩu hoặc xác minh danh tính, TikTok bắt buộc gửi OTP về Hotmail. Nếu đổi mật khẩu Hotmail trên GPM trước, hòm thư Hotmail trên điện thoại sẽ bị văng phiên (hoặc token bị revoke), khiến script không thể lấy được mã OTP ➔ Tài khoản TikTok bị kẹt vĩnh viễn không thể đặt mật khẩu hay đăng nhập lại.
- **Thứ tự thực thi bắt buộc:**
  1. Chạy batch `tiktok-add-bao-mat-f2a` trên dàn máy Android trước để **Tạo Pass TikTok + Bật 2FA TikTok** ➔ Ghi pass mới vào Cột 4 của Excel.
  2. Sau khi Cột 4 đã có mật khẩu, Supervisor GPM mới tự động mở khóa điều kiện `has_tiktok = True` để tiến hành **Đổi Mật Khẩu Hotmail + Bật 2FA Microsoft**.

---

## 2. Vì Sao Tài Khoản Admin Đã Reg TikTok Nhưng Cột PASS Bị Trống (`None`)
- Theo đúng quy trình `tiktok-reg-hotmail-outlook-flow`, các nick reg trên điện thoại bằng luồng **Email-only / OTP** qua Outlook không đi qua màn hình nhập password.
- TikTok chuyển thẳng từ nhập mã xác thực sang ngày sinh và vào thẳng trang chủ. Farm nghiêm cấm tự ý ghi mật khẩu giả vào sheet nên ô `PASS` (Cột 4) được để trống (`None`).
- Trong toàn bộ 630 nick Admin, có 270 nick đang trống pass TikTok (bao gồm 229 nick đã ngâm đủ 7 ngày).

---

## 3. Kiến Trúc Đọc OTP 2 Tầng Cho Luồng Đặt Mật Khẩu TikTok (`flows/hotmail_login.py`)
Khi runner 2FA (`run_capture_phase_b.py`) gặp tài khoản có `PASS = None`, hàm `ensure_account_password_saved()` sẽ vào màn hình đổi mật khẩu của TikTok. Khi TikTok yêu cầu xác minh OTP qua Email, hàm `read_tiktok_otp_from_outlook_app()` áp dụng 2 tầng xử lý:

### Tầng 1: Đọc mã OTP siêu tốc qua Microsoft Graph API Token (Ưu tiên số 1)
- **Nguồn dữ liệu:** File `D:/OneDrive/TaadaaData/admin/gmail_clean_v2.xlsx` lưu sẵn `token` (Cột 9) và `client_id` (Cột 10) của hơn 99% tài khoản Admin (625/631 nick).
- **Cơ chế:**
  * Hàm `_try_read_tiktok_otp_graph(email)` tra cứu hòm thư trong `gmail_clean_v2.xlsx`.
  * Gửi Refresh Token + Client ID lên `https://login.microsoftonline.com/common/oauth2/v2.0/token` lấy `access_token`.
  * Gọi Microsoft Graph API: `https://graph.microsoft.com/v1.0/me/messages?$top=5&$orderby=receivedDateTime desc` với Bearer token.
  * Regex bóc tách mã 6 chữ số từ subject: `r'(?<!\d)(\d{6})(?!\d)'`.
- **Ưu điểm:** Tốc độ phản hồi < 1s, triệt tiêu hoàn toàn sự phụ thuộc vào app Outlook trên điện thoại (không lo modal chặn, không lo màn hình đen, không lo đơ ADB).

### Tầng 2: Tự động Đăng nhập Outlook App Trên Thiết Bị (Fallback)
- **Kích hoạt khi:** Tài khoản không có token Graph API hoặc token hết hạn.
- **Cơ chế:**
  * Helper tự động bốc `PASS MAIL` gốc được lưu trong sheet làm biến `password`.
  * Nếu hòm thư chưa có sẵn trong app Outlook trên thiết bị Android, hàm `read_tiktok_otp_from_outlook_app` tự động gọi `login_outlook_app(adb, device, email, password, ...)` để đăng nhập tài khoản vào Outlook app trước khi đọc thư.

---

## 4. Kiểm Thử & Nghiệm Thu Live Canary
- **Lệnh chạy canary focused 1 nick:**
  ```bash
  python D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/run_capture_phase_b.py \
    --machine <M> --serial <SERIAL> \
    --expected-username <USERNAME> --source-row <ROW> \
    --workbook-path "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" \
    --workbook-sheet "Tài Khoản" \
    --password-only --live
  ```
- **Kết quả nghiệm thu thực tế trên Máy 228 (`honggiang2953`, Row 336):**
  * Thời gian hoàn tất: **29.26 giây** (nhanh gấp 3 lần so với luồng mở app qua ADB).
  * Graph API trả về OTP thành công 100%, runner điền mã và sinh mật khẩu TikTok mới lưu vào Cột 4 của Excel, dọn dẹp thiết bị về trạng thái Sleep an toàn.
