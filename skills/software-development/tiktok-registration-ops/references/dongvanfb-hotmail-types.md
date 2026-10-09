# dongvanfb.net Hotmail Supplier Reference (Live Verified: 2026-09-21)

## 1. Bản chất dịch vụ & Cảnh báo TikTok
- Trang web: `https://dongvanfb.net` (API: `https://api.dongvanfb.net`)
- Đối tượng phục vụ chính: Nuôi clone/via Facebook.
- **KHÔNG CÓ** nhãn cam kết "Chưa qua dịch vụ" hay "Chưa qua TikTok" (sàn không phân loại tình trạng TikTok).

## 2. So sánh kỹ thuật 3 loại Hotmail trên sàn

| Loại trên sàn | ID | Giá | Tồn kho | Graph API Scope | Dùng cho Farm Taadaa? |
| :--- | :---: | :---: | :---: | :--- | :---: |
| **Hotmail TRUSTED [GRAPH API]** | 5 | 350đ | ~500 | `IMAP.AccessAsUser.All`, `POP`, `SMTP` (**THIẾU `Mail.Read`**) | ❌ **KHÔNG DÙNG ĐƯỢC (LỎ)** — Lỗi `Graph token invalid` khi gọi Microsoft Graph API đọc OTP từ PC |
| **Hotmail TRUSTED [IMAP/POP3/GRAPH API]** | 59 | 350đ | ~500 | IMAP / POP3 cơ bản | ❌ Không khuyến khích |
| **HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM** | 57 | 350đ | ~500 | `User.Read`, `Mail.ReadWrite`, `Mail.Read`, `IMAP`, `POP`, `SMTP` (**FULL SCOPE**) | ✅ **CHUẨN 100%** — Đọc OTP Graph API từ PC mượt mà |

## 3. Quy trình sở hữu độc quyền sau 7 ngày (User Workflow)
Với loại ID 57:
1. Định dạng xuất từ sàn: `email|pass|refresh_token|client_id|mail_khoi_phuc` (mail khôi phục đuôi `@fviainboxes.com`).
2. Sử dụng token Graph API để reg TikTok tự động.
3. Sau 7 ngày ngâm nick trên Farm:
   - Đăng nhập Microsoft Account, đổi mật khẩu mới.
   - Tích chọn **"Sign me out of all devices"** (đá toàn bộ thiết bị cũ của shop).
   - Vào mục Bảo mật nâng cao (Advanced Security Options) xóa mail khôi phục `@fviainboxes.com`, thay bằng thông tin cá nhân.
