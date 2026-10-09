# Hotmail Providers & Dongvanfb Scopes Reference

## Đánh giá nguồn mail từ sàn dongvanfb.net cho TikTok Reg
Khi mua mail Hotmail có token trên `dongvanfb.net` để phục vụ đọc OTP qua PC:

1. **Loại ID 5 (`Hotmail TRUSTED [GRAPH API]`):**
   - Refresh token **thiếu scope `Mail.Read`**, chỉ có `IMAP/POP3/SMTP`.
   - Kết nối `graph.microsoft.com/v1.0/me/messages` sẽ bị từ chối (`Graph token invalid`). Bắt buộc phải login app Outlook/IMAP. KHÔNG NÊN MUA.

2. **Loại ID 57 (`HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM` - 350đ):**
   - Refresh token cấp đầy đủ scope: `User.Read`, `Mail.ReadWrite`, `Mail.Read`, `IMAP`, `POP`, `SMTP`.
   - Trao đổi token và đọc OTP qua Microsoft Graph API trên PC hoạt động 100%.
   - Có mail khôi phục sẵn `@fviainboxes.com`. Flow chuẩn: Reg TikTok -> ngâm 7 ngày -> đổi pass Hotmail + chọn đá thiết bị cũ -> gỡ mail khôi phục của shop -> thêm thông tin bảo mật riêng.
