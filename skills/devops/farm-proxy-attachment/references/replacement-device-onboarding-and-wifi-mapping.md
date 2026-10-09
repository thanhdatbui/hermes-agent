# Quy trình Thay thế & Onboarding máy Farm S7 mới (Replacement Device Onboarding)

## 1. Phát hiện & Nhận diện Thiết bị
- Dò tìm serial máy mới thay thế qua ADB:
  `adb devices` đối chiếu với các serial đã lưu trong `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` và `taikhoan_run_safe.xlsx`.
- Serial máy thay thế cho Máy 30: `ce0416040cba423104` (thay thế serial cũ `ce0217126cd4bc640c`).

## 2. Kết nối Wi-Fi Farm & Mật khẩu AP Aruba Thực tế (2026-09-15)
- **Mật khẩu thực tế trích xuất từ running-config Aruba AP Controller (192.168.110.253):**
  + **`kibe 1` (Zone 1, Cụm trên - Máy 1 đến 40):** Mật khẩu là **`23102025`** (WPA2-PSK).
    * *Cảnh báo:* Tuyệt đối không nhập `19051995` vào `kibe 1` vì sẽ bị từ chối bắt tay `인증 오류 발생` (Authentication error).
  + **`kibe 2` (Zone 2, Cụm dưới - Máy 41 đến 80):** Mật khẩu là **`19051995`**.
  + **`admin 1` / `admin 2` (Zone 3 & 4):** Mật khẩu là **`19051995`**.
- **Lưu ý thao tác kết nối trên Android 8:**
  + Tránh dùng `adbjoinwifi` nếu chưa cấp Runtime Permission vị trí (bị ném SecurityException).
  + Phương án chuẩn: Mở `am start -a android.settings.WIFI_SETTINGS`, dùng ADB tap chọn SSID hoặc nạp mật khẩu trực tiếp.

## 3. Cấu hình Chuẩn Phần cứng & Hệ thống S7
Chạy tuần tự trên ADB shell:
```bash
# 1. Chống lệch giờ (tránh lỗi handshake TLS/SSL và cờ giả mạo No Internet)
settings put global auto_time 1
settings put global auto_time_zone 1
setprop persist.sys.timezone Asia/Ho_Chi_Minh

# 2. Cấu hình độ sáng, màn hình & pin
settings put system screen_brightness 0
settings put system screen_brightness_mode 0
settings put system screen_off_timeout 600000
settings put global stay_on_while_plugged_in 0
settings put system aod_mode 0
settings put global aod_mode 0
settings put system accelerometer_rotation 0
settings put system sound_effects_enabled 0

# 3. Ngôn ngữ giao diện Tiếng Việt
setprop persist.sys.locale vi-VN
settings put system system_locales vi-VN

# 4. Sing-box Inbound Proxy (Cổng 20000 + N)
settings put global http_proxy 192.168.110.2:20030
settings put global captive_portal_mode 0
settings put global captive_portal_detection_enabled 0

# 5. Tắt Play Protect / ADB verifier chặn cài đặt APK ngầm
settings put global verifier_verify_adb_installs 0
settings put global package_verifier_enable 0
```

## 4. Cài đặt Gói Ứng dụng Bắt buộc
1. **ATX Agent & UiAutomator:**
   Push `atx-agent` vào `/data/local/tmp/` (`chmod 755`), cài đặt `app-uiautomator.apk` và `app-uiautomator-test.apk`.
2. **TikTok v46.6.3 Split APKs:**
   Cài đặt đầy đủ 55 split files:
   `cd /d/Taadaa/tools/tiktok_full_apks_v46.6.3 && adb -s <serial> install-multiple -r -d base.apk split_*.apk`
3. **Outlook:**
   Cài đặt từ file APK cục bộ `D:\Taadaa\tools\outlook.apk` (tránh stream trực tiếp từ đường dẫn OneDrive đồng bộ nếu gặp hiện tượng treo I/O).

## 5. Đồng bộ Serial Mapping vào Workbooks & Codebase
1. **Workbooks Excel (`openpyxl`):**
   Thay thế serial cũ bằng serial mới trên các file kèm backup `.bak`:
   - `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
   - `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
   - `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` đến `Tik8.xlsx`
2. **Codebase Automation:**
   - Cập nhật serial trong `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` (mảng `ACCOUNTS`).
   - Cập nhật serial trong `D:\Taadaa\Tiktok_Reg\calibrate.py`.
3. **Selector Login TikTok v46.6.3:**
   Chuỗi text nút chọn đăng nhập bằng email trong layout mới là: `"Sử dụng số điện thoại/email/tên người dùng"`.

## 6. Lưu ý Tài khoản khi Onboarding Máy mới
- Máy mới tinh chưa có tài khoản Google / Microsoft nào trong hệ thống Android (`dumpsys account` = 0).
- TikTok login tự động yêu cầu OTP gửi về email. Cần bổ sung tài khoản Gmail/Outlook tương ứng vào máy hoặc đăng nhập qua 2FA TOTP secret nếu tài khoản đã có cấu hình TOTP trong tracking.
