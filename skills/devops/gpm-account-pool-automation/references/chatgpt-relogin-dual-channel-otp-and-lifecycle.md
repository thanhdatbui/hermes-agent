# ChatGPT Re-Login trên GPM: Dual-Channel OTP (Graph API -> Canonical Webmail) & State Skip

## 1. Phân loại Hotmail & Kênh bóc OTP 2 tầng
Khi tự động re-login tài khoản ChatGPT trên profile GPM (tránh văng session):
1. **Kênh 1: Microsoft Graph API (Ưu tiên, O(1))**:
   - Áp dụng khi Hotmail còn OAuth `refresh_token` hợp lệ (mua dạng API).
   - Scope: `https://graph.microsoft.com/Mail.Read offline_access`.
   - Nếu token hết hạn hoặc tài khoản không có refresh token -> tự động fallback sang Kênh 2.
2. **Kênh 2: Webmail Outlook Fallback trên GPM (Dùng code login canonical có sẵn)**:
   - Áp dụng khi không còn token Graph API.
   - BẮT BUỘC dùng lại các selector và luồng login chuẩn từ `batch_gpm_hotmail_password_login.py` và `read_otp_gpm.py`:
     * Mở tab mới: `http://{host_port}/json/new?https://outlook.live.com/mail/0/`.
     * Điền email: `#i0116` -> click submit `#idSIButton9`.
     * Tự động bắt và click bypass đổi phương thức mật khẩu: `#idA_PWD_SwitchToPassword`.
     * Điền mật khẩu Hotmail từ Excel/kho: `#i0118` -> click `#idSIButton9`.
     * Vượt màn hình KMSI: click `#idSIButton9` hoặc `#declineButton`.
     * Quét nội dung danh sách thư (`[role="row"]`) lấy mã OTP 6 số của OpenAI.
     * Đóng tab webmail sau khi lấy mã để giải phóng tài nguyên profile GPM.

## 2. Vòng đời Tài khoản ChatGPT & O(1) Skip cho Nick Die
- Nhận diện lỗi die vĩnh viễn: `error_code: account_deactivated` ("Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa").
- Chụp ảnh bằng chứng artifacts, lưu state vào `D:/Taadaa/runtime/chatgpt_account_lifecycle.json`: `"status": "DEAD_DEACTIVATED"`.
- Purge sạch khỏi OmniRoute (`:20129`) và 9Router (`:20128`).
- **O(1) Skip Invariant**: Mọi lần chạy sau (Cron / manual) kiểm tra file state đầu tiên: nếu đã `DEAD_DEACTIVATED` thì lập tức BỎ QUA trong 0.5s, không mở GPM profile.
- Khi nick đăng nhập thành công vào ChatGPT: dùng CDP bóc `__Secure-next-auth.session-token`, nạp lại vào OmniRoute (`provider_connections`), reload combo pool và cập nhật state `"status": "LIVE"`.
