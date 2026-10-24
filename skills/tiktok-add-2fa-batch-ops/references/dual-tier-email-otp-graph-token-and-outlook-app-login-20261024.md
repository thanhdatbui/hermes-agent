# Kiến Trúc Đọc OTP Hotmail 2 Tầng & Invariant Bảo Toàn Mật Khẩu TikTok (24/10/2026)

## 1. Invariant Thứ Tự Vòng Đời: Bắt Buộc Có Pass TikTok Trước Khi Đổi Pass Hotmail
- **Quy tắc bất di bất dịch:** Tài khoản bắt buộc phải có đầy đủ **Username (Cột 3)** VÀ **Password TikTok (Cột 4)** trong workbook Excel trước khi Supervisor GPM cho phép chuyển từ `WAIT_7D` sang `CHANGE_INFO` để đổi mật khẩu và bật 2FA Hotmail.
- **Cơ sở kỹ thuật sống còn:**
  * Các tài khoản TikTok đăng ký qua luồng Email OTP trên thiết bị thường chưa có mật khẩu (`PASS = None`).
  * Khi vào màn hình *Cài đặt > Tài khoản > Mật khẩu* để tạo mật khẩu, TikTok **bắt buộc gửi mã xác minh 6 số OTP về hòm thư Hotmail**.
  * Hòm thư Hotmail tại thời điểm này **bắt buộc phải đang sống bằng mật khẩu cũ** (trên Outlook app thiết bị hoặc qua Graph API) thì script mới đọc được OTP để hoàn tất tạo pass TikTok.
  * Nếu đổi mật khẩu Hotmail trên GPM trước, hòm thư Hotmail sẽ bị văng phiên trên điện thoại. Khi đó, TikTok gửi OTP về hòm thư mà script không vào lấy được ➔ **Nick TikTok sẽ chết kẹt vĩnh viễn không bao giờ đặt được pass**.
  * CẤM nới lỏng điều kiện `has_tiktok` thành chỉ kiểm tra username. Phải giữ nguyên `bool(username and password)`.

---

## 2. Kiến Trúc Đọc OTP Hotmail 2 Tầng Cho Luồng Add 2FA & Tạo Pass (`tiktok-add-bao-mat-f2a`)

### Tầng 1 (Ưu tiên số 1): Microsoft Graph API qua Refresh Token (Tốc độ < 1s, Không Phụ Thuộc Thiết Bị)
- **Nguồn dữ liệu Ground Truth:**
  * File `D:/OneDrive/TaadaaData/admin/gmail_clean_v2.xlsx` (sheet `Gmail Accounts`) lưu trữ sẵn **Refresh Token (`M.C5...`)** và **Client ID (`9e5f94bc...`)** cho 625/631 (99%) tài khoản Admin.
- **Cơ chế hoạt động:**
  1. Khi TikTok gửi mã xác minh tạo pass, helper nạp ánh xạ `email -> (refresh_token, client_id)` từ `gmail_clean_v2.xlsx` (cache vào memory, nạp < 0.1s).
  2. POST `refresh_token` + `client_id` tới `https://login.microsoftonline.com/common/oauth2/v2.0/token` để lấy `access_token` (scope: `https://graph.microsoft.com/Mail.Read offline_access`).
  3. GET `https://graph.microsoft.com/v1.0/me/messages?$top=5` kèm Bearer token để đọc danh sách thư mới nhất.
  4. Trích xuất mã OTP 6 số từ subject (`<mã 6 số> là mã TikTok của bạn`) hoặc body.
- **Ưu điểm vượt trội:** Tốc độ phản hồi < 1 giây, hoàn toàn không chạm vào màn hình thiết bị, không phụ thuộc UI điện thoại, không bao giờ bị nghẽn bởi popup Microsoft hay độ trễ ADB.

### Tầng 2 (Dự phòng): Native Outlook App Trên Điện Thoại + Tự Động Đăng Nhập
- **Kịch bản áp dụng:** Dành cho các tài khoản không có token trong `gmail_clean_v2.xlsx` hoặc khi Graph API gặp sự cố mạng.
- **BẪY KỸ THUẬT CỐT TỬ CẦN NÉ:**
  * Hàm `read_tiktok_otp_from_outlook_app` trong `D:/Taadaa/Hotmail/flows/hotmail_login.py` đã có sẵn logic: nếu mailbox chưa có trong app, nó sẽ tự động gọi `login_outlook_app` để đăng nhập vào app.
  * **ĐIỀU KIỆN TIÊN QUYẾT:** Bắt buộc phải truyền tham số `password = mail_password` (Cột 7 `PASS MAIL` trong workbook).
  * **Cấm kỵ:** Trong `run_capture_phase_b.py` và `LivePhaseBAdapter`, nếu chỉ đọc email mà bỏ quên `mail_password`, tham số `password` sẽ bị `None`. Khi đó `read_tiktok_otp_from_outlook_app` sẽ báo lỗi `OUTLOOK_APP_MAILBOX_NOT_SIGNED_IN`, rơi vào fail-safe nuốt lỗi và âm thầm bỏ qua bước tạo pass.

---

## 3. Checklist Nghiệm Thu Tự Động Trước Khi Chạy Batch
1. **Kiểm tra Token Map:** Xác nhận `gmail_clean_v2.xlsx` có mặt tại `D:/OneDrive/TaadaaData/admin/` và nạp được >= 600 tokens.
2. **Kiểm tra Cột 7 Workbook:** Đảm bảo `read_mail_password_value(cfg.workbook_path, target)` đọc được mật khẩu mail trước khi khởi tạo `LivePhaseBAdapter`.
3. **Giám sát kết quả Write-Through:** Sau mỗi lượt chạy máy, đối soát workbook: ô `PASS` (Cột 4) bắt buộc phải chuyển từ `None` sang chuỗi mật khẩu mạnh 18 ký tự (`generate_account_password`), đồng thời ô `2FA` (Cột 5) có mã Secret 32 ký tự.
