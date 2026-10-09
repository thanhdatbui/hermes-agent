# DongVanFB (`dongvanfb.net`) API & Token Verification Reference

## 1. API Endpoints
- **Base API**: `https://api.dongvanfb.net`
- **Check Balance**:
  `GET https://api.dongvanfb.net/user/balance?apikey=<KEY>`
- **Account Types & Stock**:
  `GET https://api.dongvanfb.net/user/account_type?apikey=<KEY>`
- **Buy Mail (Auto purchase)**:
  `GET https://api.dongvanfb.net/user/buy?apikey=<KEY>&account_type=<ID>&quality=<QTY>&type=full`
  - Note: `type=full` trả về full string `email|pass|refresh_token|client_id` (hoặc có thêm mail khôi phục).

## 2. So Sánh & Cảnh Báo Scope Microsoft Token (Cực kỳ quan trọng)
Nhiều sản phẩm trên sàn tuy cùng tên "Graph API" nhưng phạm vi scope OAuth2 cấp từ Microsoft Azure App lại hoàn toàn khác nhau:

| Product ID | Tên sản phẩm trên sàn | Giá | Scopes thực tế Microsoft cấp | Dùng cho Farm Taadaa? |
| :---: | :--- | :---: | :--- | :---: |
| **ID 5** | `Hotmail TRUSTED [GRAPH API]` | 350đ | `IMAP.AccessAsUser.All POP.AccessAsUser.All SMTP.Send` | **LỎ — CẤM DÙNG**. Thiếu scope `Mail.Read`. Gọi `graph.microsoft.com/v1.0/me/messages` sẽ bị lỗi `Graph token invalid`. Bắt buộc phải mở app Outlook trên điện thoại để đọc OTP. |
| **ID 59** | `Hotmail TRUSTED [IMAP/POP3/GRAPH API]` | 350đ | Tương tự ID 5 | **KHÔNG DÙNG** (trừ khi tool chạy IMAP cổ điển). |
| **ID 57** | `HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM` | 350đ | `openid profile User.Read Mail.ReadWrite Mail.Read IMAP.AccessAsUser.All POP.AccessAsUser.All SMTP.Send` | **CHUẨN 100% — KHUYÊN DÙNG**. Có đầy đủ quyền `Mail.Read` và `Mail.ReadWrite`, đọc OTP trực tiếp qua PC bằng Graph API không cần mở app Outlook. |

## 3. Quy Trình Vận Hành Với Hàng ID 57
- **Định dạng trả về**:
  `email|pass|refresh_token|client_id|mail_khoi_phuc`
- **Import vào `gmail_clean_v2.xlsx`**:
  - Cột 1 (Số máy): `<STT>`
  - Cột 2 (Tài khoản gmail): `email`
  - Cột 3 (Pass mail): `pass`
  - Cột 5 (Mail khôi phục): `mail_khoi_phuc` (`@fviainboxes.com`)
  - Cột 9 (Token): `refresh_token`
  - Cột 10 (Client ID): `client_id`
- **Flow 7 ngày bàn giao**:
  1. Dùng token reg TikTok tự động (đọc OTP qua PC).
  2. Ngâm tài khoản 7 ngày trên điện thoại.
  3. Đăng nhập Hotmail trên PC đổi password + tích chọn *"Sign me out of all devices"* (đá sạch thiết bị và token cũ của shop).
  4. Vào *Security / Advanced Security Options* gỡ bỏ mail khôi phục `@fviainboxes.com` và gắn mail/SĐT cá nhân.
