# Hotmail GPM Direct Registration & Lifecycle Rules

## 1. Hotmail Direct ChatGPT Registration
- Tham khảo đầy đủ kiến trúc Microsoft Graph OTP và chính sách PASS CHATGPT tại `references/hotmail-gpm-chatgpt-direct-reg-and-graph-otp.md` trong skill `gpm-account-pool-automation`.

## 2. Các quy tắc quan trọng:
- Tách bạch mật khẩu: `PASS CHATGPT` (tạo tài khoản ChatGPT) độc lập với `PASS MAIL` (session Outlook/Microsoft).
- Sau 7 ngày change-info, mật khẩu Hotmail mới sẽ được đổi đồng bộ về cùng giá trị `PASS CHATGPT`.
- Đồng hồ Microsoft Graph API dùng UTC; khi polling OTP, luôn trừ 1 phút dung sai (`timedelta(minutes=1)`) để tránh bỏ lỡ email do clock skew.
