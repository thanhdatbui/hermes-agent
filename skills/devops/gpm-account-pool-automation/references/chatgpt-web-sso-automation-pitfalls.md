# ChatGPT Web SSO Automation & Pitfalls via GPM CDP

Kinh nghiệm thực chiến khi tự động hóa đăng nhập Google SSO vào ChatGPT Web (`chatgpt.com`) trên profile GPMLogin:

## 1. Bản chất giao diện ChatGPT Web hiện tại
- Trên `https://chatgpt.com/`, nút "Đăng nhập" trong DOM có thể bị ẩn (`visible: false`) hoặc nằm trong các component React phức tạp không kích hoạt navigation khi gọi click thông thường qua Playwright/Puppeteer.
- **Giải pháp Direct OAuth URL**: Trong DOM của ChatGPT luôn tồn tại link direct OAuth để nhảy thẳng vào Google Auth:
  ```text
  https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup&ext-web-mobile-direct-social-login=true
  ```
  Điều hướng thẳng tới URL này giúp bỏ qua hoàn toàn việc tìm và click nút trên giao diện ChatGPT Web.

## 2. Xử lý Google SSO Challenges qua Playwright/CDP
1. **Google Email Identifier (`signin/identifier`)**:
   - Điền email vào `input[type="email"]:visible` -> click `#identifierNext`.
2. **Google Account Chooser (`accountchooser`)**:
   - Không click chung chung thẻ div ngoài. Dùng `page.get_by_text(email).first.click()` hoặc selector `[data-identifier="<email>"]`.
3. **Google Password Challenge**:
   - Input: `input[type="password"]:visible` -> click `#passwordNext`.
4. **Google 2FA / TOTP Challenge (`challenge/totp`)**:
   - Khi gặp URL chứa `challenge/totp` hoặc selector `#totpPin:visible`:
     Dùng thư viện `pyotp.TOTP(totp_secret).now()` lấy mã 6 số tức thì -> điền vào `#totpPin` -> click `#totpNext`.
5. **Màn hình Consent (`accounts.google.com/signin/oauth/id` / consent)**:
   - Click nút "Tiếp tục" / "Continue" / "Cho phép" để cấp quyền OAuth.
6. **Màn hình OpenAI Onboarding (`auth.openai.com/about-you`)**:
   - Đối với tài khoản mới hoặc vừa reset session, OpenAI có thể chuyển hướng về trang `about-you` yêu cầu xác nhận ngày sinh.
   - Điền ngày sinh chuẩn (DD/MM/YYYY hoặc theo placeholder) vào input và click nút `button[type="submit"]` / "Continue" để hoàn tất chuyển hướng về `chatgpt.com`.

## 3. Trích xuất Cookie & Cập nhật OmniRoute
- Lấy cookies domain `https://chatgpt.com` qua Playwright context.
- Validate cookie qua endpoint: `POST http://127.0.0.1:20129/api/providers/validate` với payload `{"provider": "chatgpt-web", "apiKey": cookie_str}`.
- Khi `valid == True`: Cập nhật trực tiếp vào SQLite `provider_connections` (`is_active = 1`, `test_status = 'active'`) và đưa connection ID vào combo `chatgpt-web-pool`.
