# Bật 2FA Google Authenticator Tự Động Qua GPM Profile (Playwright CDP)

## 1. Bối Cảnh & Lý Do Chuyển Đổi Khỏi ADB Trên Thiết Bị S7
- **Vấn đề của luồng cũ (ADB trên Android S7):**
  - Chạy ADB UI automation trực tiếp trên điện thoại Samsung S7 rất dễ xung đột với các ca nuôi feed TikTok (foreground app).
  - Nguy cơ tranh chấp thiết bị, vướng lock máy, dẫn đến tiến trình watchdog bị treo đến timeout cron (10,800s / 180 phút).
- **Giải pháp chuyển đổi sang GPM Profile:**
  - Tận dụng GPM Profile có sẵn session đăng nhập Google và proxy chuẩn theo từng máy.
  - Chạy headless/background qua Playwright CDP, không chạm vào điện thoại thật.
  - Bounded batch: Giới hạn tối đa 3 profiles/tick để mỗi phiên watchdog kết thúc nhanh trong 2-4 phút.

---

## 2. Các Quy Tắc Bất Di Bất Dịch (Critical Safety Rules)
1. **TUYỆT ĐỐI CẤM** điều hướng tới `myaccount.google.com/device-activity`.
2. **TUYỆT ĐỐI CẤM** bấm nút Đăng xuất (Sign out / Logout) bất kỳ thiết bị Galaxy S7 hay Android nào. Thiết bị Android thật là thiết bị tin cậy bậc 1 duy trì trust score của tài khoản trong farm.
3. **Chỉ kill Chrome theo CDP port:** Sử dụng PowerShell lọc chính xác `CommandLine` chứa port debug (`remote_debugging_address`) của profile GPM. Tuyệt đối không `taskkill /IM chrome.exe /F` làm tắt trình duyệt cá nhân của người dùng.

---

## 3. Quy Trình Kỹ Thuật Chi Tiết (Module: `D:\Taadaa\GPM auto\scripts\run_add_2fa_remaining.py`)

### Bước 1: Khởi Động Profile GPM & Kết Nối Playwright CDP
- Gọi GPM Local API: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
- Lấy `remote_debugging_address` (ví dụ `127.0.0.1:port`).
- Kết nối Playwright: `pw.chromium.connect_over_cdp(f"http://{cdp_addr}", timeout=10000)`.
- Đặt `page.set_default_timeout(35000)`.

### Bước 2: Kiểm Tra Session & Điều Hướng Trực Tiếp
- Truy cập `https://myaccount.google.com/` để xác nhận session live. Nếu redirect về `signin` hoặc `account/about` -> Đánh dấu `NO_SESSION` và dừng.
- Điều hướng trực tiếp tới URL thiết lập Authenticator:
  `https://myaccount.google.com/two-step-verification/authenticator`

### Bước 3: Vượt Thử Thách Bảo Mật (Password & reCAPTCHA)
- **reCAPTCHA Enterprise Challenge:**
  - Nhận diện iframe recaptcha anchor và bframe.
  - Click nút Audio challenge.
  - Tải file MP3 challenge, chuyển đổi sang WAV qua `pydub` + `ffmpeg`.
  - Nhận diện chuỗi âm thanh bằng `speech_recognition` (Google STT API).
  - Điền kết quả vào input và bấm Verify.
- **Password Challenge:**
  - Phát hiện `input[type="password"]` hoặc URL chứa `challenge/pwd`.
  - Đọc password chính xác từ Excel (`master_gmail_manager.xlsx` hoặc `gmail_clean_v2.xlsx`).
  - Điền mật khẩu và submit.

### Bước 4: Trích Xuất Secret Key Base32 & Tính Google True UTC TOTP
- Tìm nút mở hiển thị khóa bí mật (Text key / Can't scan QR):
  - Click vào link "Không thể quét mã?" / "Can't scan it?".
- Trích xuất chuỗi Base32 (thường gồm 32 ký tự in hoa, loại bỏ khoảng trắng).
- **Tính TOTP chuẩn True UTC của Google Server:**
  - Hệ điều hành Windows thường bị clock skew vài chục giây khiến TOTP sinh ra bị lệch.
  - Lấy thời gian chuẩn từ Date header của `https://www.google.com`:
    ```python
    req = urllib.request.urlopen("https://www.google.com", timeout=4)
    date_header = req.headers.get("Date")
    google_utc = calendar.timegm(email.utils.parsedate(date_header))
    code = pyotp.TOTP(secret_key).at(google_utc)
    ```
- Nhập mã 6 số vào trường xác nhận trên Google và nhấn Xác minh.

### Bước 5: Đồng Bộ Hóa Secret Vào Excel
- Lưu đồng thời vào 2 file dữ liệu:
  1. `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx`: Cả 2 sheet `Kibe_Farm_S7` và `Master_All` (cột `2fa_secret`, cập nhật thời gian và ghi chú).
  2. `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`: Cột `2fa`.

### Bước 6: Dọn Dẹp & Đóng Profile Trong Khối Finally
- Luôn bọc toàn bộ luồng trong `try...finally`:
  ```python
  try:
      ...
  finally:
      if browser:
          try: browser.close()
          except Exception: pass
      if pw:
          try: pw.stop()
          except Exception: pass
      try:
          requests.get(f"{GPM_BASE}/profiles/stop/{pid}", timeout=10)
      except Exception: pass
      time.sleep(1)
      kill_chrome_by_port(port)
  ```

---

## 4. Thiết Kế Watchdog Cuốn Chiếu (Watchdog Semantics)
- **Tần suất & Khung giờ:** Chạy từ 08:30 đến 11:30 (HCM) sau Ca 1 nuôi feed.
- **Giới hạn Bounded Batch:** Tối đa 3 profiles/tick (`BATCH_SIZE = 3`).
- **File lock chống chạy đè:** `post_morning_gmail_2fa.lock` dùng OS-level lock (`msvcrt` trên Windows).
- **Silent Output:**
  - Nếu không có candidate hoặc chạy không có thay đổi: Thoát exit code 0, không in gì ra stdout.
  - Khi có kết quả: In markdown tổng kết ngắn gọn (Tổng máy xử lý, Thành công, Thất bại) và ghi state vào `post_morning_gmail_2fa_state.json`.
- **Đồng bộ mã nguồn:** Cần đồng bộ qua 3 thư mục:
  1. `C:\Users\Kibe\AppData\Local\hermes\scripts\`
  2. `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`
  3. `D:\Taadaa\tools\`
