# ChatGPT Account Lifecycle, Dual-Channel OTP & Session Healer Pipeline

## 1. Vấn đề thực tế
- Khi ChatGPT revoke session hoặc văng auth (401/403/lightweight unauthenticated):
  - Không thể dùng password thường để bypass trên web; OpenAI bắt buộc 100% nhập mã xác minh OTP 6 số gửi về email.
  - Sau khi nạp OTP, nếu OpenAI hiển thị trang **Lỗi xác thực: "Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa"** (`error_code: account_deactivated`), tài khoản đã bị OpenAI khóa vĩnh viễn user ID ở máy chủ. Cấm thử lại, cấm loop OTP.
  - Nếu tài khoản chưa bị xóa: Có thể đăng nhập thành công và trích xuất session cookie mới (`__Secure-next-auth.session-token`) để cập nhật vào OmniRoute (`:20129`).

## 2. Bẫy giao diện & Nút bấm Form Login OpenAI (Critical Pitfall)
- **Cấm tìm nút bằng `innerText.includes('Tiếp tục')` đơn thuần:**
  - Nút đầu tiên chứa chữ "Tiếp tục" là **"Tiếp tục với Google"**!
  - Nếu click nhầm, browser sẽ chuyển hướng sang `accounts.google.com/o/oauth2/...`, dẫn đến kẹt tại màn hình đăng nhập Google và gõ nhầm OTP vào ô email của Google.
- **Selector chuẩn bắt buộc loại trừ:**
  ```javascript
  const buttons = Array.from(document.querySelectorAll('button'));
  const contBtn = buttons.find(b => {
      const t = (b.innerText || '').trim();
      return (t === 'Tiếp tục' || t === 'Continue' || b.type === 'submit') &&
             !t.includes('Google') && !t.includes('Apple') && !t.includes('thoại');
  });
  if (contBtn) contBtn.click();
  ```
- **React Native Value Setter**: Khi điền email vào input React, dùng native setter descriptor để React nhận diện sự thay đổi:
  ```javascript
  const input = document.querySelector('input[type="email"], input[name="email"], input#email-input');
  const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  nativeSetter.call(input, email);
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  ```

## 3. Cơ chế Dual-Channel OTP (Bóc mã 2 tầng)
1. **Tầng 1 (Ưu tiên): Microsoft Graph API**:
   - Dành cho các nick Hotmail mua dạng OAuth2 còn `refresh_token` và `client_id`.
   - Đổi token lấy access token: scope `"https://graph.microsoft.com/Mail.Read offline_access"`.
   - Lấy email gần nhất từ `https://graph.microsoft.com/v1.0/me/messages?$top=5&$orderby=receivedDateTime desc` và regex `\b(\d{6})\b`.
2. **Tầng 2 (Fallback): Hòm thư Webmail Outlook trên GPM**:
   - Dành cho các nick Hotmail không còn token, chỉ có mật khẩu.
   - Mở tab mới trên CDP: `http://{host_port}/json/new?https://outlook.live.com/mail/0/`.
   - Dùng flow login Hotmail canonical:
     * Điền email (`#i0116`), bấm submit (`#idSIButton9`).
     * Bypass nút *"Sử dụng mật khẩu của bạn / Use your password instead"* (`#idA_PWD_SwitchToPassword`).
     * Điền mật khẩu (`#i0118`), bấm submit.
     * Vượt màn hình KMSI (`#declineButton` / `#idSIButton9`).
     * Đọc các row thư `[role="row"]` lấy mã 6 số OTP của OpenAI.

## 4. Vòng đời State & Cơ chế Skip O(1) Cho Acc Die
- Lưu trữ persistent state tại: `D:/Taadaa/runtime/chatgpt_account_lifecycle.json`.
- Khi phát hiện `account_deactivated`:
  1. Chụp ảnh lưu bằng chứng vào `D:/Taadaa/runtime/artifacts/deactivated_{safe_email}.png`.
  2. Ghi state: `{"status": "DEAD_DEACTIVATED", "updated_at": ts, "proof": path}`.
  3. Purge sạch connection khỏi OmniRoute (`:20129`) và 9Router (`:20128`), dọn sạch khỏi SQLite `provider_connections` và mảng `models` trong `combos.data`.
  4. Ở tất cả các chu kỳ sau (chạy tay hoặc Cron), kiểm tra state đầu vào: nếu `status == "DEAD_DEACTIVATED"` -> **SKIP O(1) ngay lập tức** trong 0.5s, không mở GPM profile.
- Khi đăng nhập thành công (`status == "LIVE"`):
  1. Bóc cookie `__Secure-next-auth.session-token` qua CDP `Network.getCookies`.
  2. Cập nhật `session_token` mới vào OmniRoute API và SQLite `provider_connections`.
  3. Đồng bộ lại combo list (`chatgpt-web-pool`, `gpt-web-sol`, `review`).
  4. Ghi state: `{"status": "LIVE", "updated_at": ts, "has_token": True}`.

## 5. Cron Watchdog Định Kỳ
- Job `chatgpt-account-lifecycle-healer` chạy mỗi 6 giờ (`0 */6 * * *`):
  `python D:/Taadaa/tools/login_audit_and_purge_deactivated.py --all`
- Tự động thanh lọc các acc die mới phát sinh, phục hồi session cho các acc còn sống và xuất báo cáo JSON `D:/Taadaa/reports/chatgpt_lifecycle_report.json`.
