# DongVanFB (dongvanfb.net) Integration & Product Classification

## 1. API Spec
- Base API: `https://api.dongvanfb.net/user/`
- Balance: `GET https://api.dongvanfb.net/user/balance?apikey=<KEY>`
- Account Types: `GET https://api.dongvanfb.net/user/account_type?apikey=<KEY>`
- Buy Endpoint: `GET https://api.dongvanfb.net/user/buy?apikey=<KEY>&account_type=<ID>&quality=<QTY>&type=full`
- Output Format (type=full):
  `email|pass|refresh_token|client_id` (hoặc có thêm `|mail_khoi_phuc`)

## 2. Phân biệt 3 loại Hotmail trên dongvanfb.net
1. **ID 5 - Hotmail TRUSTED [GRAPH API] (350đ)**:
   - **Tình trạng**: LỎ, KHÔNG DÙNG ĐƯỢC CHO HỆ THỐNG FARM TAADAA.
   - **Nguyên nhân kỹ thuật**: Refresh token bị bóp scope chỉ gồm `IMAP.AccessAsUser.All POP.AccessAsUser.All SMTP.Send`, hoàn toàn THIẾU quyền `Mail.Read` của Microsoft Graph API.
   - **Hậu quả**: Khi tool farm (`hotmail_provider.py`) gọi Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages`) để lấy OTP từ PC, server Microsoft trả về lỗi `Graph token invalid` (từ chối truy cập).

2. **ID 59 - Hotmail TRUSTED [IMAP/POP3/GRAPH API] (350đ)**:
   - Tương tự ID 5, chỉ bật cổng IMAP/POP3 cho tool giả lập cổ điển.

3. **ID 57 - HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM (350đ)**:
   - **Tình trạng**: CHUẨN 100% CHO FARM VÀ QUY TRÌNH REG TIKTOK.
   - **Scope Microsoft cấp**: `openid profile User.Read Mail.ReadWrite Mail.Send Mail.Read IMAP.AccessAsUser.All POP.AccessAsUser.All SMTP.Send`. Có đầy đủ quyền `Mail.Read` để exchange token và đọc OTP qua Microsoft Graph API trực tiếp từ PC.
   - **Khớp quy trình ngâm 7 ngày của user**:
     - Mail có sẵn mail khôi phục cứu hộ `@fviainboxes.com`.
     - Sau khi reg TikTok và ngâm 7 ngày: Đăng nhập Microsoft -> Đổi mật khẩu -> Tích chọn *"Sign me out of all devices"* (đá toàn bộ phiên cũ của shop ra ngoài) -> Xóa mail khôi phục fviainboxes trong Advanced Security để độc quyền tài khoản.

## 3. Lưu ý về nhãn "Chưa qua TikTok"
- Sàn `dongvanfb.net` chuyên tệp Facebook, KHÔNG gắn nhãn "Chưa qua dịch vụ" hay "Đã qua TikTok" như các sàn khác.
- Cần mua đợt nhỏ test trước khi nạp batch lớn.
