# Duyệt Google Prompt S7 qua Device Lock & Tự động nạp OAuth vào OmniRoute

## 1. Quy tắc bắt buộc số 1: Bảo vệ Device Lock
- Mọi thao tác ADB vào Samsung Galaxy S7 (cả Google Prompt lẫn lấy Mã bảo mật) **BẮT BUỘC** bọc trong context manager:
  ```python
  from automation_core.device_lock import acquire_device_lock

  with acquire_device_lock(
      machine=str(machine_id),
      serial=serial,
      project="gpm-login",
      bypass_proxy_readiness=True,
      force_preempt=True
  ):
      # Thao tác ADB / ATX
  ```
- **Invariant bất biến**: Trong khối `finally` của mọi hàm thao tác ADB/S7, **BẮT BUỘC** gửi `keyevent 3` (KEYCODE_HOME) trước khi nhả device lock:
  ```python
  finally:
      subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "3"], capture_output=True, timeout=5)
  ```

---

## 2. Quy trình xử lý Google Prompt (`challenge/dp` hoặc `challenge/ipp`)

Khi Google OAuth trên trình duyệt PC yêu cầu xác nhận danh tính qua thiết bị tin cậy (Galaxy S7):
- **Nhận diện trên Web**: URL chứa `challenge/dp` hoặc nội dung web có các chỉ dẫn như:
  - "Check your Galaxy S7" / "Kiểm tra Galaxy S7 của bạn"
  - "Tap Yes on the Google prompt, then tap 43" / "Nhấn vào Có... rồi nhấn vào số 43"
- **Các bước thực thi tự động**:
  1. **Trích xuất số PIN trên PC**:
     - Regex tìm 2 chữ số lớn trên giao diện web (hoặc đọc từ element số PIN).
  2. **Khóa máy & Đánh thức S7**:
     - `acquire_device_lock(...)`
     - Bật màn hình: `input keyevent 26` (POWER) -> `input keyevent 82` (MENU / UNLOCK).
     - Vuốt nhẹ nếu còn keyguard: `input swipe 500 1500 500 500`.
  3. **Mở Notification Drawer**:
     - Lệnh ADB: `adb -s <serial> shell cmd statusbar expand-notifications`
  4. **Tìm & Tap thông báo Google Play Services qua ATX**:
     - Port ATX: `17000 + machine_id` (được forward từ port `7912`).
     - Dump XML qua `http://127.0.0.1:{atx_port}/dump/hierarchy`.
     - Tìm node thông báo có text/desc chứa "Dịch vụ Google Play" / "Google Play services" / "Yêu cầu đăng nhập" / "Verify it's you".
     - Tap vào bounds của thông báo.
  5. **Xác nhận số PIN trên Dialog**:
     - Chờ dialog hiện (dump lại UI).
     - Tap nút "Có" / "Yes".
     - Tìm ô số có text trùng với số PIN trích xuất từ PC -> Tap vào ô số đó.
  6. **Hoàn tất**:
     - Trình duyệt trên PC sẽ tự động nhận diện xác nhận thành công và chuyển hướng sang màn hình Consent cấp quyền.

---

## 3. Quy trình dự phòng: Mã bảo mật 10 chữ số (`challenge/ootp`)

Nếu Google Prompt không nảy thông báo (do VPN/FCM push bị nghẽn) hoặc web rơi vào `challenge/ootp`:
1. Mở cài đặt Google trực tiếp:
   ```bash
   adb -s <serial> shell am start -n com.google.android.gms/.app.settings.GoogleSettingsLink
   ```
2. Kiểm tra tài khoản hiện tại trên màn hình:
   - Nếu khác `target_email`: tap avatar tài khoản (bounds khoảng `[60,758][204,902]`) -> chọn đúng `target_email`.
3. Chuyển sang mục Bảo mật:
   - Tap tab "Tất cả dịch vụ" (nếu có) hoặc vuốt tìm "Bảo mật và đăng nhập" / "Bảo mật".
4. Lấy mã:
   - Cuộn tìm và tap "Mã bảo mật" (Security code).
   - Dump UI qua ATX, trích xuất chuỗi 10 chữ số (loại bỏ khoảng trắng, dấu Unicode `\u202d`).
5. Gửi `keyevent 3` (HOME) trong `finally` và nhả lock.
6. Điền 10 chữ số vào ô Pin trên web -> bấm Tiếp theo / Enter.

---

## 4. Tự động nạp vào OmniRoute & Gán Proxy 1:1

Sau khi vượt qua xác minh danh tính và vào màn hình Consent:
1. **Cấp quyền Consent**:
   - Tick tất cả checkboxes nếu có (`Select all` / `Chọn tất cả`).
   - Click "Tiếp tục" / "Cho phép" / "Allow" / "Sign in".
2. **Bắt Callback & Exchange Code**:
   - Lắng nghe request network hoặc URL chuyển hướng tới `/callback?code=...`.
   - Gửi request exchange code:
     ```python
     POST /api/oauth/antigravity/exchange
     payload = {
         "code": captured_code,
         "redirectUri": redirect_uri,
         "codeVerifier": code_verifier,
         "state": state
     }
     ```
3. **Gán Proxy 1:1 theo Port**:
   - Trích xuất port proxy gán cho máy (từ tên profile / proxy string, ví dụ `5121`, `5112`, `5124`, `5125`).
   - Lấy danh sách proxy từ OmniRoute: `GET /api/settings/proxies`.
   - Tìm Proxy ID khớp với port.
   - Gán proxy cho connection (scope `account`):
     ```python
     PUT /api/settings/proxies/assignments
     payload = {
         "scope": "account",
         "scopeId": connection_id,
         "proxyId": proxy_id
     }
     ```
4. **Đồng bộ Models**:
   - Kích hoạt sync models cho connection mới:
     ```python
     POST /api/providers/{connection_id}/sync-models
     ```
