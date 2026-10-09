# Quy Trình Đăng Nhập & Hồi Sinh ChatGPT Web Pool Trên GPMLogin Qua CDP

Tài liệu quy chuẩn kỹ thuật tự động hóa đăng nhập Google SSO vào ChatGPT Web (`https://chatgpt.com`), trích xuất cookie session cho OmniRoute (`:20129`) và các bẫy DOM cần xử lý.

---

## 1. Direct Social Login URL Bypass
Không điều hướng vào `https://chatgpt.com/` rồi dò click nút "Đăng nhập" (dễ bị kẹt ở mobile view hoặc button không có direct handler). Mở thẳng URL direct Google OAuth:
```text
https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup&ext-web-mobile-direct-social-login=true
```
URL này sẽ nhảy thẳng vào trang Google Account Chooser hoặc Google Sign-in mà không cần tương tác với trang chủ ChatGPT.

---

## 2. Các Bẫy Selector Trên Google Sign-in
1. **Trang nhập Email (`accounts.google.com/v3/signin/identifier`):**
   - Trường nhập email KHÔNG PHẢI là `input[type="email"]`. Nó là `input[type="text"]` với selector chuẩn:
     ```python
     page.locator('#identifierId, input[name="identifier"]').first.fill(email)
     page.locator('#identifierNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
     ```
2. **Trang chọn tài khoản (`accountchooser`):**
   - Dùng click đích danh theo text: `page.get_by_text(email).first.click()` hoặc selector `[data-identifier="{email}"]`.
3. **Trang nhập Mật khẩu:**
   - Dùng selector: `input[name="Passwd"], input[type="password"]:visible`.
4. **Trang TOTP 2FA (`challenge/totp`):**
   - Sinh mã bằng `pyotp.TOTP(totp_key).now()`.
   - Selector: `input#totpPin, input[type="tel"], input[name="totpPin"]`. Bấm `#totpNext`.

---

## 3. Bẫy Màn Hình Onboarding Lần Đầu Của OpenAI (`https://auth.openai.com/about-you`)
Khi tài khoản Google lần đầu tiên đăng nhập vào OpenAI/ChatGPT, hệ thống sẽ chuyển hướng tới màn hình khai báo thông tin:
- **Trường Họ tên:** `input[name="name"]` -> Điền họ tên tài khoản.
- **Trường Tuổi:** `input[name="age"]` (**Lưu ý quan trọng: type="number", yêu cầu nhập TUỔI chứ KHÔNG PHẢI NGÀY SINH**).
  - Tính tuổi dựa trên năm sinh trong bảng kho tài khoản: `age = 2026 - birth_year`.
  - Tránh nhầm lẫn điền `dd/mm/yyyy` vào trường này khiến form không submit được.
- **Nút Submit:** `button[type="submit"]` (thường mang text "Tiếp tục" hoặc "Continue").

---

## 4. Trích Xuất & Xác Thực Cookie Cho OmniRoute (:20129)
Sau khi chuyển hướng về lại `https://chatgpt.com/`:
```python
cookies = context.cookies(["https://chatgpt.com"])
cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

# Validate qua OmniRoute
req = urllib.request.Request(
    "http://127.0.0.1:20129/api/providers/validate",
    data=json.dumps({"provider": "chatgpt-web", "apiKey": cookie_str}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
# Cập nhật SQLite khi valid=True
```

---

## 5. Chốt Chặn Fail-Fast Khi Gặp reCAPTCHA
Nếu Google chuyển hướng sang `accounts.google.com/v3/signin/challenge/recaptcha`:
- **Dừng ngay lập tức (Fail-Fast)**, đóng profile GPM và báo cáo hiện trường.
- **Tuyệt đối không lặp lại request tự động** tránh gây checkpoint thiết bị hoặc khóa tài khoản Google. Yêu cầu mở thủ công trên GPM để giải captcha.
