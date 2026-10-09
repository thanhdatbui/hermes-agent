# ChatGPT Google OAuth & Guest Landing Automation via GPM Playwright CDP

## 1. Bối cảnh & Tự động hóa qua Script
Khi mở rộng tài nguyên từ Google Account Pool trên GPMLogin để tạo/đăng nhập các dịch vụ bên thứ 3 (như ChatGPT, OpenAI, Anthropic,...):
- Luôn tổ chức thành **script Python chuẩn hóa** (đặt tại `D:\Taadaa\GPM auto\scripts\`) quản lý vòng đời từng profile:
  1. `start_profile(profile_id)` qua GPM Local API v3 (`http://127.0.0.1:19995/api/v3`).
  2. Lấy `remote_debugging_address` và kết nối Playwright qua `connect_over_cdp(f"http://{remote_addr}")`.
  3. Thao tác flow OAuth / Signup / Onboarding.
  4. Đóng browser và gọi `stop_profile(profile_id)` trong khối `finally` để tránh rò rỉ RAM/CPU khi chạy batch.

---

## 2. Các cạm bẫy UI trên ChatGPT & Cách khắc phục

### Cạm bẫy 1: Guest Landing Page (Nhận diện nhầm "Đã Đăng Nhập")
- **Hiện tượng**: Từ tháng 04/2024, ChatGPT mở ô nhập prompt (`textarea`, `#prompt-textarea`, placeholder *"Hỏi ChatGPT"* / *"What can I help with?"*) cho **khách vãng lai (Guest) chưa đăng nhập**.
- **Hậu quả**: Nếu script kiểm tra trạng thái login bằng sự xuất hiện của `textarea` hoặc kiểm tra `chatgpt.com in page.url`, script sẽ **báo ảo `SUCCESS`** dù tài khoản hoàn toàn chưa đăng nhập, chụp ảnh landing page khách.
- **Giải pháp bắt buộc**:
  ```python
  def check_logged_in(page):
      url = page.url
      if any(k in url for k in ["/auth", "/login", "accounts.google.com"]):
          return False
      
      # 1. Nếu còn bất kỳ nút đăng nhập/đăng ký nào -> Chắc chắn CHƯA login
      login_sels = [
          'button:has-text("Đăng nhập")', 'a:has-text("Đăng nhập")',
          'button:has-text("Log in")', 'a:has-text("Log in")',
          'button:has-text("Sign up")', 'a:has-text("Sign up")',
          'button:has-text("Đăng ký")', 'a:has-text("Đăng ký")',
          '[data-testid="login-button"]', '[data-testid="signup-button"]'
      ]
      for sel in login_sels:
          if page.locator(sel).first.is_visible(timeout=500):
              return False
      
      # 2. Phải xuất hiện Profile Button / User menu
      profile_sels = [
          'button[data-testid="profile-button"]',
          '[aria-label*="User menu"]',
          '[aria-label*="Menu người dùng"]',
          'button[aria-label*="profile"]',
          'nav button img[alt]'
      ]
      for sel in profile_sels:
          if page.locator(sel).first.is_visible(timeout=1000):
              return True
      return False
  ```

### Cạm bẫy 2: Cookie Consent Modal che khuất phần tử
- ChatGPT hiển thị banner cookie *"Chúng tôi sử dụng cookie"* / *"We use cookies"*. Banner này có thể phủ lớp che hoặc chặn click vào các nút bên dưới.
- **Giải pháp**: Tạo hàm `dismiss_cookie_banner(page)` gọi ngay sau mỗi lần load trang:
  ```python
  def dismiss_cookie_banner(page):
      cookie_btns = [
          'button:has-text("Chấp nhận tất cả")',
          'button:has-text("Accept all cookies")',
          'button:has-text("Accept all")',
          '#onetrust-accept-btn-handler'
      ]
      for sel in cookie_btns:
          loc = page.locator(sel).first
          if loc.is_visible(timeout=1000):
              loc.click()
              time.sleep(1)
              return True
      return False
  ```

### Cạm bẫy 3: Điều hướng trực tiếp tới Auth Endpoint
- Thay vì vào trang chủ `chatgpt.com` rồi tìm nút click, điều hướng thẳng tới:
  `https://chatgpt.com/auth/login`
- Chờ xuất hiện nút `"Continue with Google"` / `"Tiếp tục với Google"` (`button[data-provider="google"]`).
- Khi click, Chrome sẽ mở trang đăng nhập Google hoặc redirect. Vì Profile GPM đã đăng nhập sẵn Gmail, Google sẽ hiển thị danh sách tài khoản (Account Chooser). Click vào tài khoản tương ứng `div[data-email="{email}"]` và xác nhận quyền (Continue / Tiếp tục).

---

## 3. Xử lý Onboarding & Checkpoint tài khoản mới
Khi tạo tài khoản ChatGPT lần đầu bằng Gmail:
1. **Màn hình "Tell us about you" (Họ tên & Ngày sinh)**:
   - Điền tên và ngày sinh hợp lệ (đảm bảo độ tuổi $\ge 18$, ví dụ: `15/08/1998`).
   - Nhấn *Tiếp tục / Agree*.
2. **Màn hình Phone Verification**:
   - Nếu OpenAI yêu cầu xác minh số điện thoại (`input[type="tel"]` / *"Verify your phone"*):
   - Chụp ảnh màn hình bằng chứng, ghi nhận trạng thái `PHONE_VERIFICATION_REQUIRED` và đóng profile, chuyển sang profile kế tiếp, tuyệt đối không treo luồng đợi OTP.
