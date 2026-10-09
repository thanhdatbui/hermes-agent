# Quy Trình Cấu Hình Máy S7 Mới Thay Thế Máy Die Trên Farm Kibe

## 1. Phát hiện & Nhận Diện Máy Mới
- Khi cắm máy mới vào thay thế máy cũ: chạy `adb devices` và đối chiếu với `taikhoan_run_safe.xlsx` để tìm Serial mới chưa có trong hệ thống.
- Model phổ biến: Samsung Galaxy S7 (SM-G930K/L/S/F), Android 8.0 (API 26).

## 2. Kết Nối Wi-Fi & Bẫy Mật Khẩu SSID Aruba
- **Quy tắc SSID & Passwords trên Aruba AP (BẮT BUỘC NHỚ CHUẨN):**
  + **`kibe 1` (Máy 1–40, AP-325 Zone 1):** Mật khẩu là **`23102025`** (KHÔNG PHẢI 19051995!).
  + **`kibe 2` (Máy 41–80, AP-325 Zone 2):** Mật khẩu là **`19051995`**.
  + **`admin 1` & `admin 2` (Máy 201+, AP-315 Zone 3/4):** Mật khẩu là **`19051995`**.
- **Bẫy `adbjoinwifi` trên Android 8:** Ứng dụng `adb-join-wifi` bị thiếu quyền Location runtime dẫn đến không kết nối được qua intent. Dùng lệnh trực tiếp trên UI settings hoặc tap kết nối kèm nhập mật khẩu:
  ```bash
  adb -s <serial> shell am start -a android.settings.WIFI_SETTINGS
  # Tap SSID, nhập pass, bấm Kết nối
  ```

## 3. Cấu Hình Phần Cứng Chuẩn Farm S7 & Khắc Phục Lệch Giờ
- **Đồng bộ thời gian tự động (Ngăn lỗi SSL Handshake & Fake mất mạng):**
  ```bash
  adb -s <serial> shell "settings put global auto_time 1 && settings put global auto_time_zone 1 && setprop persist.sys.timezone Asia/Ho_Chi_Minh"
  ```
- **Hardware Profile Farm S7 (Độ sáng 0, tắt màn, tắt AOD):**
  ```bash
  adb -s <serial> shell "settings put system screen_brightness 0"
  adb -s <serial> shell "settings put system screen_brightness_mode 0"
  adb -s <serial> shell "settings put system screen_off_timeout 600000"
  adb -s <serial> shell "settings put global stay_on_while_plugged_in 0"
  adb -s <serial> shell "settings put system aod_mode 0 && settings put global aod_mode 0"
  adb -s <serial> shell "settings put system accelerometer_rotation 0"
  adb -s <serial> shell "settings put system sound_effects_enabled 0"
  adb -s <serial> shell "setprop persist.sys.locale vi-VN && settings put system system_locales vi-VN"
  ```

## 4. Gán Proxy Sing-box & Tắt Captive Portal
- Dải port Sing-box: `192.168.110.2:20000+N` (Ví dụ máy 30 -> `20030`):
  ```bash
  adb -s <serial> shell "settings put global http_proxy 192.168.110.2:20030"
  adb -s <serial> shell "settings put global captive_portal_mode 0"
  adb -s <serial> shell "settings put global captive_portal_detection_enabled 0"
  ```
- Kiểm tra kết nối proxy:
  ```bash
  adb -s <serial> shell "toybox nc -w 3 192.168.110.2 20030 < /dev/null && echo PROXY_OK || echo PROXY_FAIL"
  ```

## 5. Tắt Package Verifier & Cài Đặt Apps
- **Tắt Package Verifier (Tránh ADB Install bị treo/timeout 10 phút):**
  ```bash
  adb -s <serial> shell "settings put global verifier_verify_adb_installs 0 && settings put global package_verifier_enable 0"
  ```
- **Cài ATX Agent & UiAutomator:**
  ```bash
  adb -s <serial> push "D:/Taadaa/AI-Tools/tools/atx/atx-agent" /data/local/tmp/atx-agent
  adb -s <serial> shell "chmod 755 /data/local/tmp/atx-agent"
  adb -s <serial> install -r -d -g "D:/Taadaa/AI-Tools/tools/atx/app-uiautomator.apk"
  adb -s <serial> install -r -d -g "D:/Taadaa/AI-Tools/tools/atx/app-uiautomator-test.apk"
  ```
- **Cài TikTok v46.6.3 (55 Split APKs):**
  ```bash
  cd /d/Taadaa/tools/tiktok_full_apks_v46.6.3
  adb -s <serial> install-multiple -r -d base.apk split_*.apk
  ```
- **Cài Outlook:**
  ```bash
  adb -s <serial> install -r -d -g "D:/OneDrive/apk-bank/com_microsoft_office_outlook/com.microsoft.office.outlook_4.2325.1-32325818_minAPI26(armeabi-v7a)(nodpi)_apkmirror.com.apk"
  ```

## 6. Cập Nhật Serial Mapping Trong Toàn Bộ Workbooks (12 Files)
Chạy script Python cập nhật cột Serial cho hàng Máy N trên toàn bộ 12 file:
- `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
- `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
- `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` đến `Tik8.xlsx`
- `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx`
- `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx`
- Cập nhật cả `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` (mảng `ACCOUNTS`) và `calibrate.py`.

## 7. Đăng Nhập Tài Khoản & Bẫy UI TikTok v46.6.3
- Nút chọn đăng nhập bằng email trong v46.6.3 là:
  `"Sử dụng số điện thoại/email/tên người dùng"` (thay vì `"Dùng số điện thoại/email"`).
- Khi máy mới chưa có sẵn session, cần đảm bảo app Outlook/Gmail có sẵn hộp thư nhận OTP hoặc tài khoản có mã 2FA TOTP trong tracking (`taikhoan_dat_v2_updated.xlsx`).
- Luôn kết thúc bằng việc đưa máy về HOME (`input keyevent 3`) và xuất ảnh nghiệm thu `MEDIA:<path_to_png>`.
