# ChatGPT Google OAuth & Onboarding Flow via GPM CDP

## 1. ChatGPT Login Flow via Google OAuth
1. Mở `https://chatgpt.com/auth/login`.
2. Click cookie banner (nếu có): `button:has-text("Accept all"), button:has-text("Chấp nhận tất cả")`.
3. Click `Continue with Google` / `Tiếp tục với Google`.
4. Tìm và switch sang tab Google OAuth (`accounts.google.com`):
   - Chọn đúng email mục tiêu (`div[data-identifier="..."]` hoặc `get_by_text(email)`).
   - Nếu bị yêu cầu password: fill password -> Next (`#passwordNext`).
   - Nếu bị yêu cầu TOTP 2FA: sinh mã qua `pyotp.TOTP(secret).now()` -> fill vào `#totpPin` hoặc `input[type="tel"]` -> Next (`#totpNext`).
   - Nếu gặp consent screen: click Continue/Allow (`#submit_approve_access`).

## 2. OpenAI Onboarding Page (`https://auth.openai.com/about-you`)
Khi tài khoản lần đầu đăng nhập ChatGPT hoặc chưa hoàn tất thông tin cá nhân:
- URL sẽ chuyển hướng về `https://auth.openai.com/about-you` (Tiêu đề: *"Bạn bao nhiêu tuổi? - OpenAI"* hoặc *"Tell us about you"*).
- **Form bao gồm các input**:
  - `input[name="name"]`: Họ và tên (Full name). Nếu rỗng hoặc cần chuẩn hóa, fill tên người dùng.
  - `input[name="age"]`: **BẮT BUỘC**. Placeholder "Tuổi" / type="number". **Nếu không điền age, nút submit sẽ không chuyển trang dù form không báo lỗi rõ ràng.** Điền tuổi hợp lệ (ví dụ: `24` - `28`).
  - `birthday` và `isExplicitConsentRequired`: các trường hidden.
- Sau khi điền `age`, bấm `button[type="submit"]` (hoặc `button:has-text("Tiếp tục")` / `button:has-text("Continue")`). Trang sẽ ngay lập tức chuyển hướng vào `https://chatgpt.com/`.

## 3. Pitfall: Playwright `page.screenshot` bị Timeout do Fonts trên ChatGPT
- Trên `https://chatgpt.com/`, Playwright mặc định đợi fonts load (`waiting for fonts to load...`). Do ChatGPT load nhiều web fonts (KaTeX, Söhne, v.v.) qua proxy GPM, lệnh `screenshot()` dễ bị `playwright._impl._errors.TimeoutError: Page.screenshot: Timeout 30000ms exceeded`.
- **Cách khắc phục**:
  - Truyền timeout ngắn hoặc dùng evaluate / chụp clip, hoặc thêm `timeout=10000`:
    ```python
    try:
        page.screenshot(path=SCREENSHOT_PATH, timeout=10000)
    except Exception:
        # Fallback qua CDP Page.captureScreenshot trực tiếp không chờ fonts
        cdp_session = page.context.new_cdp_session(page)
        res = cdp_session.send("Page.captureScreenshot", {"format": "png"})
        import base64
        with open(SCREENSHOT_PATH, "wb") as f:
            f.write(base64.b64decode(res["data"]))
    ```
- Hoặc kiểm tra sự hiện diện của selector `#prompt-textarea`, `nav`, hoặc inner text "ChatGPT" / "Hôm nay bạn muốn làm gì?" để xác nhận đăng nhập thành công.
