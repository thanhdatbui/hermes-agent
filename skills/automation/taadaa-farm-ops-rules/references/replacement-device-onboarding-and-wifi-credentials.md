# Quy trình Thay thế & Cấu hình Máy Farm Mới (Replacement Device Onboarding)

## 1. Phát hiện Thiết bị Mới (O(1))
- Khi thay máy chết (ví dụ Máy N cũ die, cắm máy S7 mới vào hub):
  - Tra cứu danh sách serial online: `adb devices`
  - So sánh với serial hiện hữu trong `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` hoặc `PROXYgandienthoai.xlsx` để xác định serial thiết bị mới chưa có trong hệ thống.

## 2. Quy tắc Kết nối Wi-Fi & Mật khẩu AP Aruba (BẮT BUỘC)
- **CỰC KỲ QUAN TRỌNG - MẬT KHẨU KHÔNG GIỐNG NHAU:**
  - `kibe 1` (Zone 1 - AP .253): Mật khẩu là **`23102025`**
  - `kibe 2` (Zone 2 - AP .252): Mật khẩu là **`19051995`**
  - `admin 1` (Zone 3 - AP .250): Mật khẩu là **`19051995`**
  - `admin 2` (Zone 4 - AP .250): Mật khẩu là **`19051995`**
- **Cách trích xuất pass unencrypted trên Aruba CLI:**
  - SSH vào AP (`admin` / `n0spam@@`): gõ `show running-config no-encrypt`
  - Lệnh này sẽ hiển thị rõ ràng `wpa-passphrase` dạng cleartext, không bị hash.
- **Quy trình kết nối qua ADB UI:**
  - Mở cài đặt: `am start -a android.settings.WIFI_SETTINGS`
  - Tap vào SSID tương ứng -> điền mật khẩu -> tap Kết nối (Connect).

## 3. Cấu hình Hệ thống & Chuẩn Phần cứng S7 Farm
```bash
# 1. Đồng bộ giờ (Chống lỗi SSL / 2016 Clock Trap)
adb -s <serial> shell "settings put global auto_time 1 && settings put global auto_time_zone 1 && setprop persist.sys.timezone Asia/Ho_Chi_Minh"

# 2. Chuẩn phần cứng chống nóng và bảo vệ màn hình
adb -s <serial> shell "settings put global stay_on_while_plugged_in 0"
adb -s <serial> shell "settings put system screen_off_timeout 600000"
adb -s <serial> shell "settings put system screen_brightness 0"
adb -s <serial> shell "settings put system screen_brightness_mode 0"
adb -s <serial> shell "settings put system accelerometer_rotation 0"
adb -s <serial> shell "settings put system sound_effects_enabled 0"

# 3. Tắt Always On Display (AOD) để màn hình tắt đen hoàn toàn
adb -s <serial> shell "settings put system aod_mode 0 && settings put global aod_mode 0"

# 4. Ngôn ngữ Tiếng Việt
adb -s <serial> shell "setprop persist.sys.locale vi-VN && settings put system system_locales vi-VN"

# 5. Gán Sing-box Proxy Máy N
adb -s <serial> shell "settings put global http_proxy 192.168.110.2:20000+N"
adb -s <serial> shell "settings put global captive_portal_mode 0"
adb -s <serial> shell "settings put global captive_portal_detection_enabled 0"
```

## 4. Cài đặt Ứng dụng Bắt buộc
- **ATX Agent & UIAutomator:**
  - Push `/data/local/tmp/atx-agent`, chmod 755.
  - Install `app-uiautomator.apk` và `app-uiautomator-test.apk`.
  - Khởi động server daemon: `/data/local/tmp/atx-agent server -d --stop`.
- **TikTok v46.6.3 (55 Split APKs):**
  - Thư mục: `D:\Taadaa\tools\tiktok_full_apks_v46.6.3`
  - Cài đặt an toàn giữ login: `adb install-multiple -r -d base.apk split_*.apk`
- **Outlook (`com.microsoft.office.outlook`):**
  - **Bẫy OneDrive:** Không install trực tiếp từ thư mục `D:\OneDrive\apk-bank` nếu file chưa được fully hydrate (dễ gây nghẽn I/O và timeout ADB 10 phút). Copy file về ổ cục bộ (`D:\Taadaa\tools\`) trước khi chạy `adb install`.

## 5. Cập nhật Mapping Toàn Diện (Không được bỏ sót)
Khi thay serial máy N, bắt buộc cập nhật đồng bộ ở cả 2 nơi:
1. **Các Workbooks Excel (`D:\OneDrive\TaadaaData\kibe\`):**
   - `taikhoan_run_safe.xlsx` (cột Device ID cho tất cả các row của máy N)
   - `PROXYgandienthoai.xlsx` (cột device ID)
   - `Tik1.xlsx` đến `Tik8.xlsx` (cột device ID)
2. **Code Repo Dictionaries:**
   - `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` (`ACCOUNTS` list: cập nhật serial cho `stt: N`)
   - `D:\Taadaa\Tiktok_Reg\calibrate.py` (dictionary mapping STT -> serial)

## 6. Nghiệm thu & Chụp ảnh Evidence
- Tắt màn hình về trạng thái nghỉ an toàn: `adb shell input keyevent 223` (Display Power: `state=OFF`).
- Đính kèm đường dẫn ảnh chụp nghiệm thu trong báo cáo cuối theo định dạng:
  `MEDIA:<path_to_screencap.png>`
