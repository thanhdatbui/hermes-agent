# Direct Google OAuth SSO & OpenAI Onboarding Automation via CDP

## Bối Cảnh & Vấn Đề Gặp Phải
1. **Nút "Đăng nhập" / "Log in" trên `chatgpt.com` không kích hoạt OAuth:**
   Khi mở trang `https://chatgpt.com/` bằng Playwright CDP qua profile GPM, các nút đăng nhập dạng client-side button có thể bị chặn popup, cookie banner che phủ hoặc hydration delay khiến click vào không chuyển hướng sang `auth.openai.com`.
2. **Onboarding `about-you` của OpenAI làm kẹt cookie session:**
   Sau khi hoàn tất xác thực Google OAuth (kể cả đã điền TOTP 2FA thành công), OpenAI chuyển hướng tới `https://auth.openai.com/about-you`. Nếu không hoàn tất form này, cookie session người dùng thực sự (`__Secure-next-auth.session-token`...) không được cấp, khiến OmniRoute validate trả về `ChatGPT session expired`.
3. **Bẫy định dạng trường ngày sinh / tuổi:**
   Form `about-you` hiện đại của OpenAI yêu cầu:
   - `input[name="name"]`: Tên hiển thị (Text).
   - `input[name="age"]`: Số tuổi (Number, ví dụ: 24, 26), KHÔNG PHẢI định dạng ngày sinh DD/MM/YYYY.

---

## Giải Pháp Chuẩn Hóa

### 1. Direct Google OAuth Bypass URL
Bỏ qua hoàn toàn giao diện trang chủ `chatgpt.com`, điều hướng thẳng tới URL Direct Social Login:
```python
DIRECT_OAUTH_URL = "https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup&ext-web-mobile-direct-social-login=true"
page.goto(DIRECT_OAUTH_URL, timeout=60000, wait_until="domcontentloaded")
```
URL này đưa thẳng profile vào luồng Google OAuth (`accounts.google.com`) mà không phụ thuộc vào DOM của ChatGPT.

### 2. Bộ Selector Google Auth Chuẩn Xác
- **Email identifier input:**
  Google Sign-in sử dụng `id="identifierId"` (thường mang `type="text"`, KHÔNG PHẢI `type="email"`).
  ```python
  id_inp = page.locator('#identifierId, input[name="identifier"]').first
  if id_inp.count() > 0 and id_inp.is_visible():
      id_inp.fill(email)
      page.locator('#identifierNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
  ```
- **Account Chooser:**
  ```python
  acc_elem = page.get_by_text(email).first
  if acc_elem.count() > 0:
      acc_elem.click()
  else:
      page.locator(f'[data-identifier="{email}"]').first.click()
  ```
- **Password Challenge:**
  ```python
  pwd_inp = page.locator('input[name="Passwd"], input[type="password"]:visible').first
  if pwd_inp.count() > 0 and pwd_inp.is_visible():
      pwd_inp.fill(password)
      page.locator('#passwordNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
  ```
- **TOTP 2FA (pyotp):**
  ```python
  import pyotp
  code = pyotp.TOTP(totp_key).now()
  totp_inp = page.locator('#totpPin, input[type="tel"]').first
  if totp_inp.count() > 0:
      totp_inp.fill(code)
      page.locator('#totpNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
  ```

### 3. Tự Động Hoàn Tất OpenAI `about-you`
```python
if "about-you" in page.url.lower():
    short_name = email.split('@')[0].capitalize()
    name_inp = page.locator('input[name="name"]').first
    if name_inp.count() > 0:
        name_inp.fill(short_name)
    age_inp = page.locator('input[name="age"]').first
    if age_inp.count() > 0:
        age_inp.fill("24") # hoặc tính theo năm sinh
    page.wait_for_timeout(1000)
    submit_btn = page.locator('button[type="submit"]').first
    if submit_btn.count() > 0:
        submit_btn.click()
```

### 4. Nghiệm Thu & Cập Nhật Session Cookie
Chờ URL chuyển về `chatgpt.com` và không còn nút Đăng nhập:
```python
cookies = context.cookies(["https://chatgpt.com"])
cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

# Validate qua OmniRoute :20129
v_res = requests.post("http://127.0.0.1:20129/api/providers/validate", json={
    "provider": "chatgpt-web",
    "apiKey": cookie_str
}).json()

if v_res.get("valid") is True:
    # Cập nhật SQLite storage.sqlite và combo chatgpt-web-pool
    ...
```
