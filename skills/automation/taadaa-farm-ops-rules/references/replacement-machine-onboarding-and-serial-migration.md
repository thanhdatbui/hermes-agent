# Quy trình Onboarding & Thay thế Máy Farm Mới (Replacement Machine S7)

Áp dụng khi thay máy cũ chết/hỏng bằng máy Samsung Galaxy S7 mới vào hệ thống Farm Kibe (80 máy).

## 1. Phát hiện thiết bị mới O(1)
Không quét đĩa hay dò thủ công. Chạy so sánh giữa thiết bị online thực tế và bảng phân bổ:
```python
# 1. Lấy serial đang kết nối: adb devices
# 2. Đọc bảng serial đã mapping trong D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx
# 3. Tập hợp chênh lệch (new_attached = attached - mapped_serials) sẽ cho ra chính xác serial máy mới.
```

## 2. Kết nối Wi-Fi tự động qua ADB & Bẫy Cấp quyền adbjoinwifi trên S7

- Dàn Kibe chia 2 cụm AP:
  + **Máy 01 – 40:** SSID `kibe 1` | Pass: `23102025` (LƯU Ý QUAN TRỌNG: Pass kibe 1 là `23102025`, KHÔNG PHẢI 19051995)
  + **Máy 41 – 80:** SSID `kibe 2` | Pass: `19051995`
  + **Cụm Admin (Máy 200+):** SSID `admin 1` & `admin 2` | Pass: `19051995`

### 🚨 Bẫy adbjoinwifi trên Stock Samsung S7 (Android 8.0):
- App `adb-join-wifi.apk` trên Android 8.0 không khai báo quyền `ACCESS_FINE_LOCATION` trong manifest, dẫn đến `SecurityException` hoặc treo im lặng khi kết nối.
- Đồng thời máy S7 mới cắm thường bị kẹt bởi:
  1. **USB MTP Modal Dialog:** `com.samsung.android.MtpApplication/com.samsung.android.MtpApplication.USBConnection` chiếm focus. BẮT BUỘC dismiss qua `automation_core.usb_popup.dismiss_usb_popup_shell(adb)` hoặc tap 'Allow'.
  2. **Keyguard Lock:** Bắt buộc chạy `adb -s <SERIAL> shell "wm dismiss-keyguard"` và đưa về portrait: `adb -s <SERIAL> shell "settings put system accelerometer_rotation 0 && settings put system user_rotation 0"`.

### Phương pháp kết nối Wi-Fi chuẩn (UI Automation):
```bash
# 1. Giải phóng popup USB và mở màn hình Wi-Fi
adb -s <SERIAL> shell wm dismiss-keyguard
adb -s <SERIAL> shell "am start -a android.settings.WIFI_SETTINGS"

# 2. Dump XML tìm SSID (kibe 1 hoặc kibe 2)
adb -s <SERIAL> shell uiautomator dump /data/local/tmp/wifi_ui.xml
# Tìm bounds của 'kibe 1' (hoặc 'kibe 2'), tap vào dòng Wi-Fi
adb -s <SERIAL> shell input tap <X_CENTER> <Y_CENTER>

# 3. Nhập mật khẩu và bấm Kết nối (kibe 1: 23102025 | kibe 2: 19051995)
adb -s <SERIAL> shell input text <PASSWORD>
# Tap nút '연결' (Connect / KẾT NỐI)
adb -s <SERIAL> shell input tap <X_CONNECT> <Y_CONNECT>

# 4. Kiểm tra IP nhận qua DHCP:
adb -s <SERIAL> shell "dumpsys wifi | grep -i mWifiInfo"
adb -s <SERIAL> shell "ip addr show wlan0"
```

## 3. Cấu hình Chuẩn Hardware & OS Profile S7
```bash
# Bật tự động đồng bộ giờ qua mạng (tránh bẫy SSL năm 2016 gây lỗi No Internet):
adb -s <SERIAL> shell "settings put global auto_time 1 && settings put global auto_time_zone 1 && setprop persist.sys.timezone Asia/Ho_Chi_Minh"

# Tiêu chuẩn Farm S7:
adb -s <SERIAL> shell "settings put global stay_on_while_plugged_in 0"
adb -s <SERIAL> shell "settings put system screen_off_timeout 600000"
adb -s <SERIAL> shell "settings put system screen_brightness 0"
adb -s <SERIAL> shell "settings put system screen_brightness_mode 0"
adb -s <SERIAL> shell "settings put system accelerometer_rotation 0"
adb -s <SERIAL> shell "settings put system sound_effects_enabled 0"

# Chuẩn hóa Locale Tiếng Việt:
adb -s <SERIAL> shell "setprop persist.sys.locale vi-VN && settings put system system_locales vi-VN"
```

## 4. Gán Proxy Sing-box Chuẩn Farm Kibe
- Port proxy cố định theo số thứ tự máy: `20000 + N` (ví dụ Máy 30 -> `20030`).
- MikroTik LAN IP: `192.168.110.2`.
```bash
adb -s <SERIAL> shell "settings put global http_proxy 192.168.110.2:20030"
adb -s <SERIAL> shell "settings put global captive_portal_mode 0"
adb -s <SERIAL> shell "settings put global captive_portal_detection_enabled 0"
```

## 5. Cài đặt Bộ Ứng dụng Bắt buộc (Core Apps)
1. **ATX Agent & UIAutomator:**
   - Push binary: `adb -s <SERIAL> push "D:/Taadaa/AI-Tools/tools/atx/atx-agent" /data/local/tmp/atx-agent`
   - Chmod: `adb -s <SERIAL> shell "chmod 755 /data/local/tmp/atx-agent"`
   - Cài APK:
     `adb -s <SERIAL> install -r -d -g "D:/Taadaa/AI-Tools/tools/atx/app-uiautomator.apk"`
     `adb -s <SERIAL> install -r -d -g "D:/Taadaa/AI-Tools/tools/atx/app-uiautomator-test.apk"`
   - Khởi động service: `adb -s <SERIAL> shell "/data/local/tmp/atx-agent server -d --stop"`
2. **Microsoft Outlook:**
   `adb -s <SERIAL> install -r -d -g "D:/OneDrive/apk-bank/com_microsoft_office_outlook/com.microsoft.office.outlook_4.2325.1-32325818_minAPI26(armeabi-v7a)(nodpi)_apkmirror.com.apk"`
3. **TikTok v46+ (Split APK):**
   `cd /d/Taadaa/tools/tiktok_full_apks_v46.6.3 && adb -s <SERIAL> install-multiple -r -d base.apk split_*.apk`

## 6. Đồng bộ Cập nhật Serial Mapping trong các File Quản trị
Cập nhật serial mới thay thế serial cũ trong toàn bộ danh sách file Excel:
- `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
- `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
- `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` đến `Tik8.xlsx`
- `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` (nếu có)
- `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx` (nếu có)

## 7. Nghiệm thu & Chụp ảnh Hiện trường (Media Gate)
- Kiểm tra proxy bằng raw socket HTTP:
  `adb -s <SERIAL> shell "toybox nc -w 3 192.168.110.2 20030 < /dev/null && echo PROXY_OK || echo PROXY_FAIL"`
- Trở về HOME: `adb -s <SERIAL> shell "input keyevent 3"`
- Chụp ảnh screencap: `adb -s <SERIAL> exec-out screencap -p > "D:/Taadaa/m<N>_new_configured.png"`
- Nghiệm thu bắt buộc đính kèm `MEDIA:<path_anh>` ở dòng riêng.
