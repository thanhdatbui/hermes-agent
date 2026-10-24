# Cơ Chế Đọc OTP 2 Tầng (Graph API Token & Auto Login Outlook) Cho Luồng Tạo Pass TikTok & 2FA (24/10/2026)

## 1. Bối Cảnh Sự Cố & Bẫy "2FA Thành Công Nhưng Trống Pass"
- **Hiện tượng:**
  * Toàn bộ 630 nick cụm Admin đã đăng ký TikTok (Cột 3 ID) bằng luồng OTP qua Outlook (không qua màn hình đặt pass), dẫn tới Cột 4 `PASS` trong `taikhoan_dat_v2_updated .xlsx` bị để trống (`None`).
  * Khi chạy batch 2FA (`tiktok-add-bao-mat-f2a`), 34 nick được báo cáo bật 2FA thành công (có mã 2FA Secret ở Cột 5).
  * Nhưng đối soát thực tế: **33/34 nick vẫn có Cột 4 PASS = None**!
- **Nguyên nhân cốt lõi:**
  * Sau khi bật 2FA Authenticator, TikTok yêu cầu xác minh danh tính qua Email để vào màn hình "Tạo mật khẩu" (Create Password).
  * Runner `live_phase_b_adapter.py` gọi `read_tiktok_otp_from_outlook_app()` để đọc mã OTP trên điện thoại.
  * Trên các máy Android S7, hòm thư Hotmail của nick đó chưa được đăng nhập sẵn vào app Outlook. Đồng thời runner không truyền `password`, khiến script không thể tự đăng nhập hòm thư vào Outlook.
  * Ngoại lệ bị nuốt bởi fail-safe:
    `# Fail-safe: Nếu không vào được form đổi mật khẩu, giữ nguyên mật khẩu hiện tại trong workbook`
    dẫn tới phiên báo `success`, ghi nhận 2FA nhưng bỏ qua việc tạo pass TikTok!

## 2. Phát Hiện Nguồn Tài Nguyên Token Graph API Sẵn Có
- Trong file `D:/OneDrive/TaadaaData/admin/gmail_clean_v2.xlsx` (sheet `Gmail Accounts`):
  * Đang lưu trữ 723 tài khoản có đầy đủ **Refresh Token** (`M.C5...`) và **Client ID** (`9e5f94bc...`).
  * Khớp với **625 / 631 tài khoản Admin (99%)**.
- Thử nghiệm REST API:
  * Handshake `login.microsoftonline.com` lấy `access_token` mất < 0.3s.
  * Gọi `https://graph.microsoft.com/v1.0/me/messages?$orderby=receivedDateTime desc` đọc mã OTP TikTok 6 số (`noreply@account.tiktok.com`) mất < 0.2s.
  * Tổng thời gian < 0.5s, hoàn toàn không đụng tới ADB hay UI điện thoại!

## 3. Kiến Trúc 2 Tầng Chuẩn Hóa Cho `read_tiktok_otp_from_outlook_app`
Trong `D:/Taadaa/Hotmail/flows/hotmail_login.py`:
1. **Tầng 1 (Graph API Token - Fast Path < 1s):**
   - Gọi `_try_read_tiktok_otp_graph(email)` tra cứu token từ `gmail_clean_v2.xlsx`.
   - Nếu có token: Lấy access token và đọc ngay 6 số OTP từ Graph API. Trả về ngay lập tức, bỏ qua toàn bộ thao tác ADB/Outlook.
2. **Tầng 2 (Native Outlook App + Auto Login - Fallback):**
   - Nếu không có token: Kiểm tra mật khẩu hòm thư (lấy từ sheet hoặc tham số truyền vào).
   - Mở app Outlook trên Android qua ADB. Nếu hòm thư chưa có trong app, tự động gọi `login_outlook_app(adb, device, email, password, ...)` để đăng nhập tài khoản vào Outlook trước khi đọc Inbox.

## 4. Invariant Vận Hành Giữa TikTok Pass Và Hotmail Change Pass
- **BẮT BUỘC:** Nick thiếu pass TikTok **TUYỆT ĐỐI CẤM** được chuyển sang `CHANGE_INFO` để đổi pass/2FA Hotmail.
- **Lý do kỹ thuật:** Khi TikTok tạo pass, TikTok bắt buộc gửi OTP về Hotmail. Hòm thư Hotmail phải đang sống bằng mật khẩu cũ thì Graph API / Outlook app mới đọc được OTP. Nếu đổi pass Hotmail trước, phiên mail bị đứt gãy và nick TikTok sẽ bị kẹt vĩnh viễn không bao giờ tạo được pass.
- **Thứ tự thực thi:**
  1. Chạy batch 2FA TikTok: Tạo Pass TikTok 18 ký tự + Bật 2FA Secret ➔ Lưu đầy đủ vào Cột 4 và Cột 5 của Excel.
  2. Supervisor GPM kiểm tra `has_tiktok = bool(username and password)` thấy đủ ➔ Tự động mở khóa cho phép đổi mật khẩu và bảo mật Hotmail.
