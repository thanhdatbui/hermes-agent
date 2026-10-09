# Hot-Session Dual OAuth & Watchdog Recovery (Antigravity + ChatGPT-Web)

## 1. Bản chất kiến trúc
Khi một tài khoản Gmail đã ngâm đủ 7 ngày trên điện thoại S7 được đăng nhập vào GPMLogin:
- **Hot-Session Principle**: Khi vừa đăng nhập thành công vào GPM, phiên Google đang "nóng" (được Google tin cậy cao nhất).
- Thay vì để profile "nguội" rồi hôm sau mới đem đi OAuth (dễ bị hỏi lại mật khẩu, reCAPTCHA, đòi OTP thiết bị lần 2), pipeline thực hiện **OAuth liền 2 dịch vụ trong cùng 1 persistent browser session**:
  1. **Antigravity (Google Cloud / Code Assist / Gemini)** qua OmniRoute `:20129/api/oauth/antigravity/authorize`.
  2. **ChatGPT-Web (OpenAI)** qua Direct Google OAuth URL.

---

## 2. Direct Google OAuth Bypass cho ChatGPT-Web
Không bấm qua nút "Đăng nhập" hay modal đăng nhập trên giao diện chính của `https://chatgpt.com` (dễ bị kẹt DOM, layout thay đổi hoặc không kích hoạt redirect). Điều hướng trực tiếp URL:
```text
https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup&ext-web-mobile-direct-social-login=true
```

### Flow tự động hóa:
1. **Google Account Chooser**:
   - Selector: `div[data-email="{email}"]` hoặc `page.get_by_text(email).first`.
2. **Google Email Identifier (nếu chưa có session)**:
   - Input có `id="identifierId"` (type="text", KHÔNG PHẢI type="email").
3. **Google TOTP 2FA Challenge**:
   - Sinh mã động qua `pyotp.TOTP(totp_key).now()`.
   - Input: `#totpPin` hoặc `input[type="tel"]`.
4. **OpenAI Onboarding Form (`about-you`)**:
   - Thường xuất hiện ở tài khoản đăng nhập ChatGPT lần đầu:
     - Họ tên: `input[name="name"]` -> điền tên (VD: `Quynh Le`, `Lan Dinh`).
     - Tuổi: `input[name="age"]` (type="number") -> **Điền số TUỔI (VD: 24, 26), TUYỆT ĐỐI KHÔNG điền ngày tháng năm sinh** kẻo form không submit được.
     - Submit: `button[type="submit"]` -> trang lập tức redirect về `chatgpt.com` và sinh session cookies.
5. **Trích xuất & Validate**:
   - Cookie: Trích xuất context cookies từ `https://chatgpt.com` (>= 15 cookies hợp lệ).
   - Validate qua: `POST http://127.0.0.1:20129/api/providers/validate` với body `{"provider": "chatgpt-web", "apiKey": cookie_str}`.
   - Nạp vào Combo `chatgpt-web-pool` (Model: `chatgpt-web/gpt-5.6-sol-high`).

---

## 3. Dual Recovery Watchdog Pattern (Healer lúc 05:00 AM)
Watchdog `cron_chatgpt_web_pool_watchdog.py` chạy lúc 05:00 AM hàng ngày để quét và hồi sinh:
- **ChatGPT-Web**: Quét connection `isActive == 0` hoặc validate fail -> Bật profile GPM tương ứng -> Chạy Direct OAuth -> Hút cookie tươi -> Update SQLite.
- **Antigravity**: Quét connection `isActive == 0` hoặc `test_status == 'expired'` -> Bật profile GPM -> Authorize OmniRoute -> Bắt code -> Exchange refresh token mới.
- Xong mỗi tài khoản phải gọi ngay `requests.get(f"{GPM_API}/profiles/close/{pid}")` để giải phóng RAM cho Farm.

---

## 4. Phân chia khung giờ an toàn (Farm Anti-Collision Invariant)
- **Sáng (07:15 - 08:45)**: Chỉ khung giờ này mới được phép chạy watchdog quét máy S7 rảnh (`watchdog-link-chatgpt-idle` với schedule `*/15 7,8 * * *`).
- **Chiều**: Tuyệt đối KHÔNG chạm máy S7 (thiết bị đang nuôi feed TikTok).
- **Tối (20:15 - 23:45)**: Khung giờ vàng của `post-evening-gpm-login-watchdog` (chạy 5 workers kéo Gmail ngâm đủ 7 ngày lên GPM và chạy Hot-Session Dual OAuth).
