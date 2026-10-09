# Google Prompt ("Lời nhắc của Google") Removal via Device Activity Sign-out (2026-09-05)

## 1. Bản chất kiến trúc của Google Prompt
- Trên giao diện Quản lý tài khoản Google (`myaccount.google.com/signinoptions/twosv` và `myaccount.google.com/two-step-verification/prompt`), Google **không cung cấp nút toggle switch hay icon thùng rác trực tiếp** để xóa "Lời nhắc của Google".
- Google tự động kích hoạt Lời nhắc (push notification qua Google Play Services) tới mọi thiết bị Android đang đăng nhập tài khoản.
- Cơ chế chính thức do chính Google quy định tại `two-step-verification/prompt`:
  > *"Để tắt lời nhắc của Google trên một thiết bị, hãy đăng xuất khỏi Tài khoản Google của bạn trên thiết bị đó. Dưới đây là những thiết bị hỗ trợ lời nhắc mà bạn hiện đang đăng nhập."*

---

## 2. Quy trình UI Automation Xóa Google Prompt
Để xóa bỏ triệt để Lời nhắc của Google (ví dụ giải phóng thiết bị Farm Samsung Galaxy S7 khỏi tài khoản và chỉ giữ lại Authenticator app):

1. **Điều hướng trực tiếp tới Device Activity:**
   `https://myaccount.google.com/device-activity`
2. **Vượt qua Re-auth Password / TOTP Challenge:**
   - Password: `input[type="password"]` $\rightarrow$ `#passwordNext`.
   - 2FA TOTP: `input#totpPin` $\rightarrow$ `#totpNext` (dùng `calendar.timegm` đồng bộ UTC).
   - Onboarding popup: dismiss qua `button:has-text("Bỏ qua"), button:has-text("Skip")` với cờ `force=True`.
3. **Lọc thiết bị phone cần đăng xuất:**
   - Selector thẻ thiết bị: `a[href*="device-activity/id/"]`.
   - Bỏ qua phiên PC hiện tại: `windows`, `phiên hoạt động hiện tại`, `current session`.
   - Bỏ qua thiết bị đã sign out: `đã đăng xuất`, `signed out`.
   - Bắt các keyword phone: `galaxy`, `samsung`, `sm-`, `android`, `phone`.
4. **Đăng xuất thiết bị (Sign out):**
   - Click vào link chi tiết thiết bị $\rightarrow$ Click nút `Đăng xuất` / `Sign out` (`button:has-text("Đăng xuất")`).
   - Google hiển thị modal xác nhận: `div[role="dialog"]`.
   - Kích hoạt xác nhận an toàn qua JavaScript DOM click:
     ```javascript
     const dialog = document.querySelector('div[role="dialog"], div[aria-modal="true"]');
     for (const b of dialog.querySelectorAll('button, [role="button"]')) {
         const txt = (b.innerText || '').trim().toLowerCase();
         if (txt === 'đăng xuất' || txt === 'sign out') {
             b.click();
             return true;
         }
     }
     ```
5. **Xác minh trạng thái tại `signinoptions/twosv`:**
   - Dòng "Lời nhắc của Google" không còn thiết bị nhận prompt (`0 thiết bị`).
   - Khi vào `two-step-verification/prompt`: danh sách thiết bị nhận lời nhắc hoàn toàn trống.
   - Phương thức xác thực bước 2 duy nhất còn hiệu lực là `Authenticator` (2FA TOTP).

---

## 3. Pitfalls Kỹ Thuật Đã Xử Lý
- **Lỗi Bash Variable Expansion với PowerShell `$_`:** Khi chạy lệnh PowerShell `Where-Object { $_.CommandLine -match ... }` qua terminal bash, bash sẽ diễn giải `$_` thành chuỗi đường dẫn người dùng `/c/Users/<user>`, làm hỏng cú pháp PowerShell. **Khắc phục:** Dùng trực tiếp thư viện `psutil` trong Python để kill process theo port CDP:
  ```python
  import psutil
  for p in psutil.process_iter(['name', 'cmdline']):
      try:
          if 'chrome' in (p.info['name'] or '').lower():
              cmd = ' '.join(p.info['cmdline'] or [])
              if target_port in cmd and 'remote-debugging-port' in cmd:
                  p.kill()
      except Exception:
          pass
  ```
- **Modal Dialog Confirmation Button Visibility:** Nút xác nhận Đăng xuất bên trong `div[role="dialog"]` có thể bị lỗi `element is outside of the viewport` hoặc timeout 25s nếu dùng selector thông thường. Bắt buộc dùng JS evaluate `.click()` hoặc `locator.click(force=True)`.
- **Fail-Closed Trên ReCAPTCHA:** Khi Google chuyển hướng sang `challenge/recaptcha`, không cố giải hay bấm lung tung; ghi nhận `PARTIAL_SUCCESS` / `CHECKPOINT` và đóng profile ngay lập tức để bảo toàn cookie session.
