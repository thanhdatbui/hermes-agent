# Playwright Gmail Navigation Timeout & Re-Login Challenge Runbook

## 1. Pitfall: Playwright `page.goto` Timeout on Gmail (`mail.google.com`)
When opening Gmail inbox via Playwright (e.g. `mail_page.goto("https://mail.google.com/mail/u/0/#inbox")`):
- **Problem**: Playwright defaults to `wait_until="load"`. Gmail frequently executes background service workers, long-polling streams, or redirects to Google challenge URLs. This causes `Page.goto: Timeout 35000ms exceeded. waiting until "load"` even though the DOM has already loaded.
- **Solution**: Always use `wait_until="domcontentloaded"` and wrap in an inner `try...except` so execution continues to parse the DOM:
  ```python
  try:
      mail_page.goto("https://mail.google.com/mail/u/0/#inbox", timeout=35000, wait_until="domcontentloaded")
  except Exception as ge:
      logger.warning(f"[{email}] mail_page.goto báo: {ge}, tiếp tục xử lý DOM...")
  time.sleep(5)
  ```

## 2. Re-login Challenge / Expired Session Detection in Gmail
When reading OTP from Gmail after account dormancy, Google often redirects to session re-authentication ("Xác minh danh tính của bạn" / "Vui lòng đăng nhập lại" / "Verify it's you").

### Pattern:
```python
body_content = mail_page.locator("body").inner_text() or ""
if any(k in body_content.lower() for k in ["xác minh danh tính", "vui lòng đăng nhập lại", "verify it's you", "sign in to continue"]):
    logger.info(f"[{email}] Google yêu cầu đăng nhập lại Gmail, xử lý xác thực...")
    # Click nút Tiếp theo nếu cần
    next_btn = mail_page.locator('button:has-text("Tiếp theo"), button:has-text("Next"), #identifierNext, #passwordNext').first
    if next_btn.is_visible(timeout=2000):
        next_btn.click()
        time.sleep(3)
    # Điền mật khẩu
    pwd_mail = mail_page.locator('input[type="password"], input[name="Passwd"], input[name="password"]').first
    if pwd_mail.is_visible(timeout=3000):
        logger.info(f"[{email}] Điền mật khẩu Gmail để vào hộp thư...")
        pwd_mail.fill(pwd)
        time.sleep(1)
        pwd_next = mail_page.locator('button:has-text("Tiếp theo"), button:has-text("Next"), #passwordNext').first
        if pwd_next.is_visible(timeout=2000):
            pwd_next.click()
            time.sleep(5)
```

### Pitfall & Boundary:
If Google prompts beyond password (e.g. 2FA phone, Google Prompt/device tap, or passkey challenge), the automated password fill alone will not bypass the checkpoint, resulting in `FAIL_OTP_TIMEOUT` unless 2FA TOTP/recovery mail flow is hooked. Always verify debug screenshots (e.g. `_step4_gmail_check.png`) to identify whether further challenges appeared.

## 3. Google reCAPTCHA Checkbox Handling ("Tôi không phải là người máy")
Khi Google yêu cầu re-login, màn hình thường kèm widget reCAPTCHA v2 ("Xác nhận bạn không phải là rô-bốt"):
```python
# Tự động tick checkbox reCAPTCHA trước khi bấm Tiếp theo
for f in mail_page.frames:
    if "recaptcha" in f.url and "anchor" in f.url:
        try:
            cb = f.locator("#recaptcha-anchor, .recaptcha-checkbox").first
            if cb.is_visible(timeout=2000):
                logger.info(f"[{email}] Tick checkbox 'Tôi không phải là người máy'...")
                cb.click(force=True)
                time.sleep(3)
        except Exception:
            pass
```
Nếu checkbox chuyển thành tích xanh (green checkmark), bấm `[Tiếp theo]` và điền mật khẩu. Nếu bật bframe audio/image challenge phức tạp, dừng ngay lập tức (Freeze) theo quy tắc an toàn farm để tránh kích hoạt SMS checkpoint.

## 4. Preflight Candidate Selection: Né Toàn Bộ Captcha Bằng Profile Nuôi Ấm
*Vấn đề gốc rễ:* Quét tuần tự SQLite GPM DB (`ORDER BY Id ASC`) sẽ vướng vào các profile "nguội" đã ngâm lâu ngày không mở, khiến Google đòi re-auth và captcha khi vào `mail.google.com`.
*Giải pháp bắt buộc:* Trong mọi hàm chọn candidate (như `get_gpm_candidates()`):
1. Đọc state file nuôi GPM (`gpm_gmail_nurture_state.json`), lọc set `nurture_warm` gồm các email có `status == "success"`.
2. Kiểm tra SQLite `cookies` table của profile: đếm token session Google (`SID`, `SSID`, `HSID`, `SAPISID`) $\ge 2$.
3. Gán **Priority 1** cho các profile thỏa mãn cả 2 điều kiện: vừa được nuôi thành công vừa có session cookie sống.
4. Ưu tiên bốc các profile Priority 1 này chạy trước: 100% mở `mail.google.com` là vào thẳng Inbox trong 1 giây, hoàn toàn không bị Google hỏi lại mật khẩu hay captcha.

## 5. GPM 2FA Authenticator Watchdog Triage (Transient Challenge vs Real Failure)
- **Triệu chứng alert watchdog (`post-morning-gmail-2fa-watchdog`)**:
  - `hakha18062003@gmail.com: EXCEPTION - Locator.fill: Timeout 35000ms exceeded (waiting for locator("input[type=\"password\"]"))`
  - `benghowelltpkf1@gmail.com: UNKNOWN_UI - Snippet: Loading Verify it’s you...`
- **Root cause kỹ thuật**:
  - Khi điều hướng tới `/two-step-verification/authenticator`, Google kích hoạt `challenge/pwd` hoặc interstitial page `challenge/dp` ("Verify it's you").
  - Nếu iframe reCAPTCHA hoặc form password đang chuyển trạng thái (detach/re-render DOM), lệnh `fill()` có thể timeout 35s hoặc text snippet ghi nhận lúc trang đang loading.
- **Kỷ luật điều phối & thẩm định trước khi kết luận**:
  1. Đây là lỗi **TRANSIENT** thuộc phân loại L0/L1, không phải tài khoản bị die hay mất pass.
  2. BẮT BUỘC kiểm tra log mới nhất tại `D:/Taadaa/GPM auto/logs/run_add_2fa_remaining.log` hoặc đối soát trực tiếp 2 file Excel (`master_gmail_manager.xlsx` sheet `Master_All` & `gmail_clean_v2.xlsx`) và folder screenshot `D:/Taadaa/GPM auto/debug_screenshots/add_2fa/`.
  3. Ở các nhịp cron kế tiếp (mỗi 5 phút), watchdog tự động re-run khi Google đã cập nhật rapt/session token, vượt qua challenge mượt mà và lưu Secret Key thành công.
  4. Tránh kết luận vội vàng hay báo lỗi manual cho User khi chưa đối soát log và Excel thực tế ở nhịp chạy mới nhất.


