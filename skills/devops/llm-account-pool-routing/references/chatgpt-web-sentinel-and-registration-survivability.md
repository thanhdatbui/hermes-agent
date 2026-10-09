# ChatGPT-Web Sentinel 403, Rate-Limit Protection & Registration Survivability

## 1. Bản chất Lỗi 403 Sentinel / Turnstile & Nguy cơ "Trảm" Nick Vĩnh Viễn
### Hiện tượng
- Request gửi vào model thuộc provider `chatgpt-web` (như `gpt-5.6-sol-high`, `gpt-5.6-sol`) bị lỗi:
  `[403]: ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`
- Trên giao diện OmniRoute, connection tự động chuyển sang `testStatus = "banned"` và `isActive = 0`.

### Cơ chế & Nguy cơ sống còn
- **Sentinel & Cloudflare Turnstile**: Là cơ chế Proof-of-Work (PoW) và browser challenge của OpenAI nhằm chặn bot/script gọi trực tiếp vào endpoint `/backend-api/conversation`.
- **TỬ HUYỆT (Bẫy chết người)**:
  - Khi một tài khoản bị Sentinel gắn cờ 403, nó chỉ đang bị tạm hoãn chờ người dùng mở trình duyệt giải CAPTCHA hoặc nghỉ ngơi.
  - **NẾU** router hoặc script tiếp tục retry bắn request dồn dập vào connection này mà không có khoảng nghỉ, hệ thống Anti-Abuse của OpenAI sẽ nâng mức phạt lên: **Xóa / Vô hiệu hóa vĩnh viễn tài khoản (Account Deleted or Disabled)**.
  - Khi đã bị vô hiệu hóa, truy cập `chatgpt.com` sẽ bị đá về `https://auth.openai.com/error` với thông báo *"Bạn không có tài khoản vì tài khoản đã bị xóa hoặc vô hiệu hóa"*, không thể khôi phục.

### Giải pháp kỹ thuật bắt buộc
1. **Bật van bảo vệ `rate_limit_protection = 1` trong database OmniRoute:**
   Cập nhật toàn bộ các connection thuộc provider `chatgpt-web`:
   ```sql
   UPDATE provider_connections 
   SET rate_limit_protection = 1, updated_at = CURRENT_TIMESTAMP 
   WHERE provider = 'chatgpt-web';
   ```
   *Tác dụng:* Khi một connection gặp 403 Sentinel hoặc 429, OmniRoute sẽ lập tức cách ly connection đó vào chế độ Cooldown an toàn, tuyệt đối không cho phép retry dồn dập.
2. **Cảnh báo Context Payload Quá Lớn (Lỗi 413):**
   - Web API của ChatGPT có trần dung lượng request nhỏ hơn nhiều so với API trả phí chính thức.
   - Nếu client (Hermes/Cline/Kilo) gửi system prompt và context file quá đồ sộ, OpenAI trả về lỗi `413 Payload Too Large`. Bắt buộc bật tính năng context compression hoặc định tuyến prompt lớn sang provider chính thống (Codex / Antigravity).

---

## 2. Phân Định Survivability: Google SSO vs Direct Email + OTP
Khi rà soát các tài khoản gặp sự cố trong Watchdog:
- **Tài khoản đăng ký qua Google SSO (`Continue with Google`):**
  - **Điểm yếu chí mạng**: Phụ thuộc 100% vào trạng thái sống của Gmail.
  - Nếu Google quét khóa tài khoản Gmail (báo DIE / Phone Checkpoint / Disabled), chừng nào cookie phiên ChatGPT còn hạn thì vẫn dùng được; nhưng một khi OpenAI logout bắt đăng nhập lại, **tài khoản ChatGPT sẽ chết vĩnh viễn theo Gmail** vì không thể vượt qua bước Google OAuth.
  - **Quy tắc xử lý:** Với tài khoản Google SSO mà Gmail đã DIE $\rightarrow$ Gỡ bỏ connection khỏi các combo OmniRoute (`chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna`) và xóa khỏi hệ thống để không làm nhiễu log watchdog mỗi sáng.
- **Tài khoản đăng ký bằng Direct Email + Password:**
  - **Độc lập cao**: ChatGPT có credential riêng (Email + Password + OTP). Dù Gmail backend có bị hạn chế thì tài khoản ChatGPT vẫn có thể login độc lập qua form email/password trên OpenAI.
  - **Quy tắc xử lý:** Giữ lại tài khoản, chỉ refresh session cookie qua GPM khi cần.

---

## 3. Quy Trình Phân Xử & Dọn Dẹp Profile GPM Trùng Lặp (Duplicate Triage Protocol)
Khi watchdog báo lỗi `AMBIGUOUS_GPM_PROFILE`:
1. **Tuyệt đối không đoán mò:** CẤM tự ý xóa bừa dựa vào tên hoặc ngày tạo.
2. **Khởi động từng candidate profile qua CDP:**
   - Kết nối Playwright/CDP vào `http://127.0.0.1:19995/api/v3/profiles/start/{id}`.
   - Kiểm tra `https://myaccount.google.com`: Xác nhận có đúng tài khoản chính chủ đang đăng nhập (`Signed In`) hay đã bị văng (`Signed Out`).
   - Kiểm tra `https://chatgpt.com`: Đếm số lượng cookies phiên (`__Secure-next-auth.session-token`).
   - Kiểm tra `raw_proxy`: Đối chiếu host:port có khớp với cấu hình gán máy trong Excel Farm hay không.
3. **Thực thi:**
   - **Giữ lại**: Duy nhất 1 profile chuẩn (đúng tài khoản Google LIVE, đúng proxy farm, session ChatGPT còn hoạt động).
   - **Xóa dứt điểm các profile clone rác**: Gọi API GPM `GET /api/v3/profiles/delete/{id}?mode=1` (hoặc `mode=2` tùy nhu cầu local).
   - Trích xuất cookie từ profile chuẩn nạp vào OmniRoute để hồi sinh connection ngay lập tức.
