# TikTok Login Runner Timeout & Kỷ Luật Nghiệm Thu Account Switcher S7 (2026-09-24)

## 1. Timeout Runner `tiktok_login_v1.py` Trong Môi Trường Automation

### 1.1. Hiện tượng & Rủi ro timeout giả (False Timeout)
- Khi chạy login / resume nạp nick:
  `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID> --resume --ss --allow-parent-lock`
- Quá trình đăng nhập tài khoản thường trải qua các bước:
  - Khởi động app / chuyển account screen
  - Nhập username / password
  - Vượt captcha hoặc chờ OTP / xử lý 2FA Authenticator TOTP
  - Đồng bộ trạng thái session
- **Điểm nghẽn**: Nếu wrapper / subagent đặt timeout 120s, lệnh có thể bị timeout ngắt giữa chừng (Exit 124).
- **Hậu quả**: Tiến trình Python con (`python.exe` / `cpython`) vẫn tiếp tục chạy ngầm trong Windows, nắm giữ file lock thiết bị và can thiệp màn hình, gây hiểu lầm là script treo hoặc thất bại.

### 1.2. Kỷ luật cấu hình timeout
- Khi gọi qua terminal CLI hoặc sub-process, luôn set `timeout >= 240` (khuyến nghị 240s - 300s).
- Nếu nghi ngờ script bị timeout ngắt ngoài, kiểm tra tiến trình nền qua WMI / PowerShell:
  `powershell -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Select-Object ProcessId, CommandLine"`
  trước khi chạy lại hoặc can thiệp thiết bị.

---

## 2. Kỷ Luật Bung & Nghiệm Thu Account Switcher Trên Thiết Bị S7 (Android 7/8)

### 2.1. Hai bẫy thường gặp khi cố dump UI XML
1. **Bẫy `uiautomator dump`:**
   - Chạy `adb shell uiautomator dump` trên Samsung S7 (Android 7/8) hầu như luôn bị Android OOM killer kết liễu với lỗi `Killed` (EXIT=137).
2. **Bẫy `adb shell curl`:**
   - Android gốc không tích hợp binary `curl` trong `/system/bin`. Chạy `adb shell curl -s http://127.0.0.1:7912/...` sẽ trả về `/system/bin/sh: curl: not found` (EXIT=127).

### 2.2. Quy trình bung Account Switcher & Chụp ảnh nghiệm thu chuẩn xác
Không cần dump toàn bộ XML để kiểm tra số lượng tài khoản (ví dụ nghiệm thu đủ 8 nick):
1. **Chuyển về tab Hồ sơ (Profile):**
   `adb -s <serial> shell input tap 972 1857`
   (Ngủ 2 giây để UI tải xong).
2. **Bung Bottom Sheet Account Switcher:**
   Tap trực tiếp vào Header Display Name ở nửa trên màn hình:
   `adb -s <serial> shell input tap 500 290`
   (Ngủ 1.5 giây để Bottom Sheet `rid='psy'` hiển thị đầy đủ danh sách nick).
3. **Chụp ảnh nghiệm thu:**
   `adb -s <serial> shell screencap -p /sdcard/<filename>.png`
   `adb -s <serial> pull /sdcard/<filename>.png <dest_path>`
   Trả đường dẫn `MEDIA:<dest_path>` để hoàn tất nghiệm thu bằng bằng chứng trực quan thực tế.
