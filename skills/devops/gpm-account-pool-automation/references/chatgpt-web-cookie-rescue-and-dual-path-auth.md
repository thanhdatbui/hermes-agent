# ChatGPT-Web Cookie Rescue, Dual-Path Auth & Account Liveness Triage

## 1. Bản Chất Tài Khoản: Direct Reg (ID/Pass) vs Google SSO

Qua đối soát thực tế trên toàn bộ dàn tài khoản Taadaa Phone Farm:
- **Tài khoản Direct Email + Password (100% SỐNG SÓT):**
  - Đăng ký bằng Email + Password + giải OTP (lưu tại cột L `PASS CHATGPT` file `taikhoan_dat_v2_updated .xlsx` hoặc `master_gmail_manager.xlsx`).
  - **Tỷ lệ sống 100%:** Tuyệt đối không bị OpenAI ban nick / deactivate.
  - Khi gặp lỗi, chỉ là **hết hạn cookie tạm thời** hoặc **Cloudflare Sentinel 403** (yêu cầu verify người thật). Mở GPM profile, đăng nhập lại bằng `PASS CHATGPT` là lập tức lấy được cookie mới và hồi sinh 100%.
- **Tài khoản Google SSO ("Continue with Google") (NGUY CƠ BỊ DEACTIVATE):**
  - Đăng ký bấm nhanh qua Google SSO trong các đợt cũ.
  - Khi chạy qua proxy hoặc tự động hóa, OpenAI dễ quét cờ và khóa vĩnh viễn với mã lỗi: `{"kind": "AccountDeactivated", "message": "Your account has been deactivated."}`.
  - **Hiệu ứng kép (Cả 2 bên cùng chết):** Khi tài khoản bị `AccountDeactivated`, phiên Web bị văng và OpenAI **đồng thời thu hồi luôn OAuth token bên Codex CLI** (`[401]: Encountered invalidated oauth token for user, failing request`). Cả Web lẫn Codex đều cook, bắt buộc set `is_active=0, test_status='banned'` trên cả 2 provider.

## 2. Bẫy Token Ảo (Anti-Fake Token Pitfall)

Khi Chromium trong GPM profile bị văng phiên (session expired):
1. **Bẫy URL:** Trang chuyển về `https://chatgpt.com/` hiển thị popup modal *"Your session has expired"* hoặc nút *"Log in"*, nhưng trên thanh địa chỉ URL vẫn là `https://chatgpt.com/` (không có chữ `/auth/`). Kiểm tra URL thuần túy sẽ bị lừa.
2. **Bẫy Cookie Jar tồn dư:** Trong cookie jar của trình duyệt vẫn còn nguyên cookie `__Secure-next-auth.session-token` CŨ của phiên trước (chuỗi base64 `eyJhbG...`). Nếu chỉ đọc cookie ra mà không kiểm tra trạng thái trang thì sẽ lưu token rác đã hết hạn vào OmniRoute, gây lỗi 401 hàng loạt.
3. **Quy chuẩn nghiệm thu Token thật:**
   - Kiểm tra DOM không còn chữ *"Your session has expired"*, *"Phiên của bạn đã hết hạn"*, *"Log in"*, *"Đăng nhập"*.
   - Đảm bảo đã xuất hiện thanh điều hướng chat chính (`New chat`, `Đoạn chat mới`, hoặc form nhập prompt).
   - **Thẩm định vật lý (Inference Proof):** Sau khi nạp token vào OmniRoute, bắt buộc bắn 1 câu hỏi probe `1+1=?` qua endpoint `:20129`. Nhận về đúng số `2` thì mới bật cờ `is_active=1` và `test_status='active'`.

## 3. Luồng Đăng Nhập Chuẩn Đa Năng (Dual-Path Login Workflow)

```python
# 1. Dismiss Cookie Banner triệt để (ngăn chặn intercept pointer event làm timeout 30s)
cb = page.locator('button:has-text("Chấp nhận tất cả"), button:has-text("Accept all"), button:has-text("Allow all"), button:has-text("Accept")').first
if cb.count() > 0 and cb.is_visible():
    cb.click(force=True)

# 2. Xử lý popup văng phiên nếu có
b_text = page.locator("body").inner_text()
if "session has expired" in b_text.lower() or "phiên của bạn đã hết hạn" in b_text.lower():
    page.locator('button:has-text("Log in"), button:has-text("Đăng nhập")').first.click(force=True)

# 3. Điền Email
email_inp = page.locator('input#email-input, input[name="email"], input[type="email"], input[name="username"]').first
if email_inp.count() > 0 and email_inp.is_visible():
    email_inp.fill(email)
    page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")').first.click(force=True)

# 4. Nhánh Password (Ưu tiên cột L PASS CHATGPT)
pwd_inp = page.locator('input#password, input[name="password"], input[type="password"]').first
if pwd_inp.count() > 0 and pwd_inp.is_visible() and password:
    pwd_inp.fill(password)
    page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")').first.click(force=True)
else:
    # Nhánh Google SSO fallback nếu tài khoản cũ reg qua Google
    g_btn = page.locator('button[data-provider="google"], button:has-text("Continue with Google")').first
    if g_btn.count() > 0 and g_btn.is_visible():
        g_btn.click(force=True)

# 5. Xử lý Onboarding tuổi (nếu OpenAI hỏi)
if "about-you" in page.url:
    age_inp = page.locator('input[name="age"]').first
    if age_inp.count() > 0 and age_inp.is_visible():
        age_inp.fill("24")
    page.locator('button[type="submit"]').first.click(force=True)
```

## 4. Vận Hành Cron Watchdog (05:00 AM)

- Script: `C:/Users/Kibe/AppData/Local/hermes/scripts/cron_chatgpt_web_pool_watchdog.py`.
- Tự động chạy với `max_workers = 5` mở đồng thời 5 profile GPM song song.
- Tra cứu mật khẩu từ `taikhoan_dat_v2_updated .xlsx` (cột L) hoặc `gmail_clean_v2.xlsx`.
- Tự động bóc tách chunk `.0`, `.1` của `__Secure-next-auth.session-token` nếu token dài > 4000 ký tự.
- Ghi nhận `AccountDeactivated` để lập tức đóng profile và block connection, không thử lại lặp đi lặp lại.
