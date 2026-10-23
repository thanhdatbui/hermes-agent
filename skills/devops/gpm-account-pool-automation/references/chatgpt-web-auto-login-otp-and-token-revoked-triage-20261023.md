# ChatGPT Web Auto-Login: Nút Bấm Google Redirect, Email OTP Verification & Phân Loại Token Revoked Runbook

## 1. Triệu Chứng Sự Cố & Phản Ánh Hiện Trường (2026-10-23)
- **Triệu chứng Watchdog:**
  Watchdog `chatgpt-web-pool-healer-watchdog` (job `fff7f688990d`) báo cáo 13 tài khoản `Validate fail: EMPTY_SESSION_TOKEN` và nhiều tài khoản bị OmniRoute dán nhãn `test_status = 'banned'`.
  User yêu cầu: *"Chạy canary trên 1 profile xem fix cứu được acc không?"* và bức xúc khi agent báo kết quả mà không có ảnh: *"Tại sao đéo có hình ảnh chứng minh? Là sao mày đã đăng nhập được đâu? Script như lồn v r cron đến h sao nó cứu được acc"*.

---

## 2. Bóc Tách 4 Nguyên Nhân Gốc Rễ Khiến Script Bị Liệt

### Nguyên nhân 1: Bẫy Selector Nút Bấm Văng Sang Google Sign-in & Bot-Check
- **Cơ chế lỗi:**
  Trên trang `https://chatgpt.com/auth/login`, giao diện có 4 nút:
  1. Nút nộp form email: *"Tiếp tục"* (`type="submit"`).
  2. Nút đăng nhập Google: *"Tiếp tục với Google"* (`data-provider="google"`).
  3. Nút đăng nhập Microsoft: *"Tiếp tục với tài khoản Microsoft"*.
  4. Nút đăng nhập Apple: *"Tiếp tục với Apple"*.
- **Hậu quả:**
  Dùng selector lỏng lẻo như `button:has-text("Tiếp tục")` hoặc `button[type="submit"]` sẽ bốc nhầm ngay nút *"Tiếp tục với Google"*! Trình duyệt bị đá sang `accounts.google.com/v3/signin/identifier`, gặp phiên Google đã logout và vấp phải thử thách reCAPTCHA bot-check của Google.
- **Kỷ luật khắc phục:**
  BẮT BUỘC dùng hàm JavaScript `evaluate` hoặc locator chuẩn loại trừ triệt để:
  ```javascript
  const buttons = Array.from(document.querySelectorAll('button'));
  const btn = buttons.find(b => {
      const t = (b.innerText || '').trim();
      return (t === 'Tiếp tục' || t === 'Continue' || b.type === 'submit') &&
             !t.includes('Google') && !t.includes('Apple') && !t.includes('Microsoft') &&
             !t.includes('phone') && !t.includes('thoại');
  });
  if (btn) btn.click();
  ```

---

### Nguyên nhân 2: Bẫy Email OTP Verification (`auth.openai.com/email-verification`)
- **Cơ chế lỗi:**
  Sau khi submit email chính chủ của tài khoản (dù là Gmail hay Hotmail), OpenAI thường **KHÔNG HIỆN Ô MẬT KHẨU** mà chuyển hướng sang:
  `https://auth.openai.com/email-verification` (Tiêu đề: *"Kiểm tra hộp thư đến của bạn - OpenAI"*).
  Form yêu cầu nhập mã xác thực OTP 6 số gửi về hòm thư.
- **Điểm yếu của Watchdog cũ:**
  Hàm `perform_auto_login_and_extract_cookies` chỉ tìm `input[type="password"]`. Khi gặp trang OTP, script đứng chờ 20 giây rồi văng ra ngoài, kết luận sai: `EMPTY_SESSION_TOKEN`.
- **Giải pháp bắt buộc:**
  1. Kiểm tra URL nếu chứa `/email-verification`:
  2. Với Hotmail: Gọi Microsoft Graph API (`https://login.microsoftonline.com/common/oauth2/v2.0/token` scope `https://graph.microsoft.com/Mail.Read offline_access`) bóc mã OTP 6 số từ mail mới nhất của OpenAI.
  3. Với Gmail: Trích xuất qua App Password IMAP hoặc kiểm tra hòm thư trên profile GPM.
  4. Điền OTP vào 6 ô input bằng `page.keyboard.type(code)`.

---

### Nguyên nhân 3: Bẫy Bộ Lọc Domain Regex Bỏ Quên Kho Hotmail
- **Cơ chế lỗi:**
  `cron_chatgpt_web_pool_watchdog.py` trong hàm `get_gpm_profiles_map()` và `_worker_task()` chỉ dùng:
  `m = re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', pname)`
- **Hậu quả:**
  Hơn 460 profile `@hotmail.com` trên GPM bị bỏ qua 100%, không bao giờ được đưa vào map hay hồi sinh khi rớt token.
- **Giải pháp:**
  Đổi toàn bộ sang:
  `m = re.search(r'([a-zA-Z0-9_.+-]+@(gmail|hotmail)\.com)', pname, re.IGNORECASE)`

---

### Nguyên nhân 4: Bản Chất Nhãn "Banned" Của OmniRoute & Mã Lỗi `token_revoked`
- **Cơ chế lỗi:**
  Trong `chatgpt-web.ts`, OmniRoute bắt mọi lỗi HTTP 401 trên endpoint `/backend-api/sentinel/chat-requirements/prepare` rồi tự động gán nhãn:
  `ChatGPT blocked the request (Sentinel/Turnstile required)` và set `test_status = 'banned'`.
- **Sự thật khi probe:**
  - `/api/auth/session` vẫn trả về `accessToken` (HTTP 200).
  - `/prepare` trả về:
    `HTTP 401: {"error": {"code": "token_revoked", "message": "Encountered invalidated oauth token for user, failing request"}}`
- **Kết luận:**
  Tài khoản KHÔNG HỀ BỊ BAN / VÔ HIỆU HÓA (`AccountDeactivated`). Đây chỉ là session token bị OpenAI thu hồi phía server. Chỉ cần re-login qua GPM là lấy lại session token tươi mới và active lại bình thường.

---

## 3. Kỷ Luật Visual Evidence (Bằng Chứng Hình Ảnh Thực Tế)
- **CẤM TUYỆT ĐỐI báo cáo text suông:** Bất kỳ thao tác đăng nhập, test canary hay gỡ lỗi UI nào đều bắt buộc chụp ảnh và gửi thẻ `MEDIA:` tại từng bước:
  * Checkpoint 1 (Pre-submit): Sau khi điền email, chụp ảnh xác nhận ô nhập liệu.
  * Checkpoint 2 (Post-submit): Chụp ảnh màn hình phản hồi của trang trong <= 3 giây.
- **Soi mắt trước khi gửi:** BẮT BUỘC gọi `browser_vision` kiểm tra ảnh, mô tả nội dung thấy được trong tin nhắn trả lời user.
