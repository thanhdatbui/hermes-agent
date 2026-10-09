# ChatGPT-Web Dual-Path Login & Session Rescue Protocol

## 1. Bản Chất Tài Khoản & Mật Khẩu (ID/Pass vs SSO)
- **Tài khoản cũ:** Đăng ký bằng Google SSO (`Continue with Google`).
- **Tài khoản mới:** Đăng ký trực tiếp bằng Email + Password (Direct Auth).
- **MẬT KHẨU CHÍNH CHỦ (AUTHORITATIVE SOT):**
  - Mật khẩu ChatGPT đăng nhập trên Web nằm tại **Cột L (`PASS CHATGPT`)** trong file Excel `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (hoặc `taikhoan_dat_v2_updated.xlsx`).
  - **CẤM** lấy nhầm `pass mail` ở cột 2 hoặc cột 6 để điền vào form ChatGPT vì đa số mật khẩu ChatGPT có định dạng riêng (ví dụ `@Ks` hoặc chuỗi tạo ngẫu nhiên khác).

## 2. Ba Cái Bẫy Cần Tránh Khi Tự Động Hóa Trình Duyệt GPM
1. **Bẫy URL Giả Định:**
   - Khi vào `https://chatgpt.com/`, dù tài khoản đã bị văng session (logged out) thì URL trên thanh địa chỉ **vẫn giữ nguyên là `https://chatgpt.com/`** (không redirect về `/auth/login`).
   - BẮT BUỘC phải đọc DOM text (`body.inner_text`): nếu có chữ *"Log in"*, *"Đăng nhập"*, *"Your session has expired"* thì khẳng định là phiên đã hết hạn.
2. **Bẫy Cookie Tồn Dư (Stale Cookie Jar):**
   - Cookie Jar của Chrome profile lưu lại cookie `__Secure-next-auth.session-token` cũ.
   - Script đọc cookie thô sẽ thấy chuỗi `eyJhbG...` hợp lệ nhưng thực tế token đó đã expired trên máy chủ OpenAI.
   - Chỉ được coi là lấy cookie thành công khi đã hoàn tất luồng đăng nhập hoặc xác minh qua Inference Probe.
3. **Bẫy Cookie Banner Che Khuất Pointer:**
   - OpenAI chèn static cookie consent (`div[data-octane-static-cookie-consent]`) đè lên nút Đăng nhập.
   - Click thông thường sẽ bị Playwright timeout 30s (`intercepts pointer events`).
   - BẮT BUỘC dismiss trước:
     `page.locator('button:has-text("Chấp nhận tất cả"), button:has-text("Accept all")').first.click(force=True)`

## 3. Quy Trình Đăng Nhập Kép (Dual-Path Execution)
```python
# 1. Điền Email
email_inp = page.locator('input#email-input, input[name="email"], input[type="email"]').first
if email_inp.is_visible():
    email_inp.fill(email)
    page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")').first.click(force=True)
    page.wait_for_timeout(3000)

# 2. Xử lý Password hoặc SSO
pwd_inp = page.locator('input#password, input[name="password"]').first
if pwd_inp.is_visible() and chatgpt_password:
    pwd_inp.fill(chatgpt_password)
    page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")').first.click(force=True)
else:
    # Fallback SSO nếu trang tự chuyển hướng
    g_btn = page.locator('button[data-provider="google"]').first
    if g_btn.is_visible():
        g_btn.click(force=True)
```

## 4. Bắt Buộc Nghiệm Thu Qua Live Inference (Inference Gate)
- Tuyệt đối không chỉ tin vào sự tồn tại của chuỗi cookie.
- Sau khi bóc tách token và cập nhật DB, BẮT BUỘC bắn 1 probe:
  `1+1=? Trả lời đúng 1 số duy nhất.` qua OmniRoute `:20129`.
- Chỉ khi trả về đúng `2` trong vòng $\le 30$s mới được set `is_active = 1, test_status = 'active'`.
