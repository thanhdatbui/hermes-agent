# ChatGPT-Web Sentinel 403 / Turnstile Cooldown & Account Deactivation Safeguards

Tài liệu kỹ thuật về cơ chế phòng thủ khi tài khoản trong `chatgpt-web-pool` (OmniRoute) gặp lỗi **403 Sentinel / Turnstile** nhằm ngăn chặn việc tài khoản bị OpenAI xóa hoặc vô hiệu hóa vĩnh viễn (Deactivated/Disabled).

---

## 1. Cơ chế Phát hiện Bot của OpenAI (Sentinel & Turnstile)

### Bản chất lỗi 403 Sentinel:
Khi tương tác với endpoint reverse-engineered web client `/backend-api/conversation`:
```text
[403]: ChatGPT blocked the request (Sentinel/Turnstile required). 
Try again later or open chatgpt.com in a browser to refresh state.
```
OpenAI yêu cầu giải thử thách tính toán (Proof-of-Work - PoW) và token Cloudflare Turnstile xác thực người dùng thật trên trình duyệt. Khi request gửi từ backend script / router ngầm:
- Không giải được Turnstile challenge.
- Lệch TLS fingerprint (JA3/JA4) giữa HTTP client của router và trình duyệt Chrome thật.
- Điểm tín nhiệm rủi ro (Risk Trust Score) của session bị đẩy lên mức nguy hiểm.

---

## 2. Rủi ro Tối nghiêm trọng: Bị Khóa / Xóa Tài khoản Vĩnh viễn

Khi một tài khoản gặp 403 Sentinel:
- **Nếu tiếp tục retry dồn dập:** Hệ thống Anti-Abuse của OpenAI nhận diện hành vi bot cố tình vượt rào cản Sentinel $\rightarrow$ Tự động chuyển hình phạt từ **tạm khóa phiên** sang **XÓA HOẶC VÔ HIỆU HÓA TÀI KHOẢN VĨNH VIỄN** (`auth.openai.com/error?payload=... "Bạn không có tài khoản vì tài khoản đã bị xóa hoặc vô hiệu hóa"`).
- **Hậu quả:** Tài khoản bị vô hiệu hóa hoàn toàn từ máy chủ OpenAI, không thể login lại hay lấy lại session.

---

## 3. Quy chuẩn Cấu hình & Vận hành Chống Trảm Nick

### 3.1. Kích hoạt Van bảo vệ `rate_limit_protection = 1`:
Trên cơ sở dữ liệu `~/.omniroute/storage.sqlite`, mọi connection thuộc provider `chatgpt-web` **BẮT BUỘC** phải bật cờ `rate_limit_protection = 1`:
```sql
UPDATE provider_connections 
SET rate_limit_protection = 1, updated_at = CURRENT_TIMESTAMP 
WHERE provider = 'chatgpt-web';
```
**Tác dụng:** Khi nhận mã 403 Sentinel hoặc 429 Too Many Requests, OmniRoute sẽ lập tức cách ly connection vào chế độ Cooldown (nghỉ ngơi) với thời gian tăng dần (exponential backoff), tuyệt đối ngăn chặn việc bắn request liên hoàn làm cháy tài khoản.

### 3.2. Quy trình Xử lý khi Tài khoản bị gắn cờ `testStatus = "banned"`:
1. **Tuyệt đối không spam API:** Không cố gắng gọi endpoint API để kiểm tra lại tài khoản.
2. **Cho tài khoản nghỉ ngơi (Cooldown):** Ngâm tài khoản tối thiểu **24h - 48h**.
3. **Mở thủ công trên trình duyệt GPM chuẩn:**
   - Mở profile GPM tương ứng qua Local API (`/api/v3/profiles/start/{id}`).
   - Truy cập trực tiếp `https://chatgpt.com` để Cloudflare Turnstile và Sentinel trên trình duyệt thật giải quyết thử thách và cấp session cookie mới.
   - Trích xuất cookie `__Secure-next-auth.session-token` mới nạp lại vào OmniRoute.
4. **Nếu tài khoản đã bị báo "bị xóa hoặc vô hiệu hóa":**
   - Loại bỏ ngay connection ra khỏi các combo `chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna` trên OmniRoute để tránh làm ô nhiễm router và gây nghẽn watchdog hàng ngày.
