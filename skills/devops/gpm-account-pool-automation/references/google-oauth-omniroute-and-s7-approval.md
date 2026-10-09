# Google Antigravity OAuth to OmniRoute & S7 Device Lock Approval

## 1. Tổng Quan Quy Trình Nạp Antigravity OAuth vào OmniRoute (Port 20129)
Khi tự động nạp tài khoản Google từ profile GPMLogin vào OmniRoute làm Antigravity connection:
1. **Lấy Authorize URL:** Gọi `GET /api/oauth/antigravity/authorize?redirect_uri=http://127.0.0.1:20129/callback`.
2. **Khởi chạy Profile GPM:** Mở Playwright persistent context vào thư mục profile của GPM kết nối qua đúng port proxy của tài khoản (Singbox direct `http://192.168.110.2:{20000+port_offset}`).
3. **Mở Auth URL & Duyệt Xác Minh:**
   - Chọn tài khoản trong Account Chooser.
   - Vượt qua các lớp bảo vệ Google Prompt / S7 Security Code / TOTP.
   - Bấm nút chấp thuận cấp quyền: `Tiếp tục` / `Cho phép` / `Sign in` / `Allow`.
4. **Bắt Callback & Exchange:** Bắt authorization code qua request hook `/callback?code=...` và gửi `POST /api/oauth/antigravity/exchange`.
5. **Gán Proxy 1:1 & Đồng Bộ Model:**
   - `PUT /api/settings/proxies/assignments` với payload:
     `{"scope": "account", "scopeId": "<connection_id>", "proxyId": "<proxy_id>"}`
   - `POST /api/providers/<connection_id>/sync-models` để kích hoạt models và cập nhật `token_expires_at`.

---

## 2. Các Cạm Bẫy Bảo Mật Google OAuth (Pitfalls & Solutions)

### A. Bẫy Biến Thể Nút "Thử Cách Khác" -> "Cách Xác Minh Khác" (2026-09-05)
- Khi Google hiển thị màn hình Google Prompt (`challenge/dp`: *"Kiểm tra Galaxy S7 của bạn..."*), Google đã cập nhật text nút bấm thành **"Cách xác minh khác"** (hoặc `"More ways to verify"`).
- Bộ chọn cũ chỉ tìm `"Thử cách khác"` / `"Try another way"` sẽ bị miss `count = 0` dẫn đến timeout.
- **Bộ chọn chuẩn hóa:**
  ```python
  try_another_btn = page.locator(
      'button:has-text("Cách xác minh khác"), '
      'button:has-text("Thử cách khác"), '
      'button:has-text("Try another way"), '
      'button:has-text("More ways to verify"), '
      'div[role="button"]:has-text("Cách xác minh khác"), '
      'div[role="button"]:has-text("Thử cách khác"), '
      'div[role="button"]:has-text("Try another way"), '
      'a:has-text("Cách xác minh khác"), '
      'a:has-text("Thử cách khác"), '
      'a:has-text("Try another way"), '
      'span:has-text("Cách xác minh khác"), '
      'span:has-text("Thử cách khác")'
  )
  ```

### B. Bẫy Xung Đột Input `name="Pin"` giữa TOTP 2FA và Offline Security Code (`challenge/ootp`)
- Trên màn hình `challenge/ootp` (Mã bảo mật ngoại tuyến 10 số từ điện thoại), ô nhập mã mang thuộc tính `name="Pin"` và `type="tel"`.
- Nếu bộ chọn TOTP dùng `input[name="Pin"], input[type="tel"]`, script sẽ nhận nhầm đây là ô TOTP và điền mã 6 số Authenticator vào ô 10 số, gây lỗi từ chối và loop điền mã liên tục.
- **Quy tắc bắt buộc:**
  1. Xử lý `challenge/ootp` trước: nhận diện `"challenge/ootp" in page.url.lower()` hoặc trang chứa chuỗi `"mã bảo mật"`.
  2. Ô TOTP chỉ tìm: `input#totpPin, input[name="totpPin"]` hoặc điều kiện `"totp" in page.url.lower() and "ootp" not in page.url.lower()`.

### C. Giao Diện Google Play Services Mới trên Galaxy S7 (Tab "Tất Cả Dịch Vụ")
- Khi mở intent `com.google.android.gms/.app.settings.GoogleSettingsLink`, giao diện Google Settings phiên bản mới mặc định ở tab **"Đề xuất"** (Recommended).
- Menu **"Bảo mật và đăng nhập"** / **"Mã bảo mật"** nằm trong tab **"Tất cả dịch vụ"** (All services).
- **Quy trình chuẩn hóa:**
  1. Kiểm tra tài khoản hiện tại: nếu khác `target_email`, tap avatar `[60,758][204,902]` (hoặc node chứa `@gmail.com`) để mở danh sách và chọn đúng `target_email`.
  2. Tap tab `"Tất cả dịch vụ"` (`node.attrib["text"] == "Tất cả dịch vụ"`).
  3. Cuộn màn hình và tap `"Bảo mật và đăng nhập"` (hoặc `"Bảo mật"`).
  4. Cuộn màn hình và tap `"Mã bảo mật"`.
  5. Trích xuất mã 10 số (regex `^\d{10}$`).

---

## 3. Kỷ Luật Khóa Thiết Bị Bắt Buộc Khi Thao Tác ADB S7 (`Device Lock`)
- **Nguyên tắc an toàn:** Mọi thao tác ADB vào thiết bị Farm S7 BẮT BUỘC bọc trong context manager:
  ```python
  sys.path.insert(0, r"D:\Taadaa\automation-core")
  from automation_core.device_lock import acquire_device_lock

  with acquire_device_lock(machine=str(mid), serial=serial, project="gpm-login", bypass_proxy_readiness=True, force_preempt=True):
      try:
          # Các thao tác ADB tại đây
          ...
      finally:
          # BẮT BUỘC trả máy về màn hình chính trước khi nhả lock
          subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "3"], capture_output=True, timeout=5)
  ```
- Thao tác này tạm dừng các cron nuôi acc (TikTok/GemPhone) tranh chấp màn hình, chống treo socket và bảo toàn 100% phiên hoạt động của Farm.
