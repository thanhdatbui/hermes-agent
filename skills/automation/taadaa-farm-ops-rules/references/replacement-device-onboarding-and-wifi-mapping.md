# Quy trình thay thế & Cấu hình máy Farm mới (Replacement Device Onboarding)

## 1. Phát hiện máy mới thay thế
- Dò tìm máy mới cắm vào USB chưa có trong bảng mapping hoặc thế chỗ máy die:
  `python D:/Taadaa/tools/inspect_machine.py <N>`
  Đối chiếu danh sách `adb devices` với cột Device ID trong `PROXYgandienthoai.xlsx` và `taikhoan_run_safe.xlsx`.

## 2. Kết nối Wi-Fi Farm & Mật khẩu AP Aruba
- **Quy hoạch SSID & Mật khẩu thực tế:**
  + `kibe 1` (Zone 1, AP 325 trên, máy 1–40): Mật khẩu là **`23102025`** (đã xác thực qua `show running-config no-encrypt` trên Aruba Controller `192.168.110.253`).
  + `kibe 2` (Zone 2, AP 325 dưới, máy 41–80): Mật khẩu là **`19051995`**.
  + `admin 1` (Zone 3, AP 315): Mật khẩu là **`19051995`**.
  + `admin 2` (Zone 4, AP 315): Mật khẩu là **`19051995`**.
- **Lưu ý kết nối Android 8:**
  + CẤM dùng `adbjoinwifi` nếu chưa được cấp quyền vị trí Runtime Permissions vì sẽ bị security exception trên Android 8+.
  + Phương án chuẩn: Mở `android.settings.WIFI_SETTINGS`, dùng UI tap chọn SSID hoặc nạp profile qua script/keyevent.

## 3. Cấu hình Tiêu chuẩn Phần cứng Samsung S7 Farm
Chạy qua ADB shell:
```bash
# 1. Chống lệch giờ (tránh lỗi TLS/SSL và cờ fake No Internet)
settings put global auto_time 1
settings put global auto_time_zone 1
setprop persist.sys.timezone Asia/Ho_Chi_Minh

# 2. Tiêu chuẩn phần cứng & pin
settings put system screen_brightness 0
settings put system screen_brightness_mode 0
settings put system screen_off_timeout 600000
settings put global stay_on_while_plugged_in 0
settings put system aod_mode 0
settings put global aod_mode 0
settings put system accelerometer_rotation 0
settings put system sound_effects_enabled 0

# 3. Ngôn ngữ Tiếng Việt
setprop persist.sys.locale vi-VN
settings put system system_locales vi-VN

# 4. Sing-box Proxy (Port 20000 + N)
settings put global http_proxy 192.168.110.2:20030
settings put global captive_portal_mode 0
settings put global captive_portal_detection_enabled 0

# 5. Tắt Google Play Protect / ADB verifier chặn cài app ngầm
settings put global verifier_verify_adb_installs 0
settings put global package_verifier_enable 0
```

## 4. Cài đặt các ứng dụng chuẩn
1. **ATX Agent & UiAutomator:**
   Push binary `atx-agent` vào `/data/local/tmp/` (chmod 755), cài `app-uiautomator.apk` và `app-uiautomator-test.apk`.
2. **TikTok v46.6.3 Split APKs:**
   Cài đặt qua lệnh `install-multiple`:
   `cd /d/Taadaa/tools/tiktok_full_apks_v46.6.3 && adb -s <serial> install-multiple -r -d base.apk split_*.apk`
3. **Outlook:**
   Cài từ kho APK `com.microsoft.office.outlook`. Khuyên dùng ổ cục bộ `D:\Taadaa\tools\` thay vì stream trực tiếp qua thư mục OneDrive đồng bộ nếu gặp hiện tượng nghẽn I/O.

## 5. Đồng bộ hóa Mapping Serial trong Workbooks & Codebase
1. **Cập nhật Workbooks Excel:**
   Dùng `openpyxl` thay thế serial cũ thành serial mới trên các file (kèm backup `.bak`):
   - `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
   - `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
   - `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` đến `Tik8.xlsx`
2. **Cập nhật Hardcoded Serial trong Codebase:**
   - `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` (Mảng `ACCOUNTS`)
   - `D:\Taadaa\Tiktok_Reg\calibrate.py`
3. **Selector Login TikTok v46.6.3:**
   Text nút chọn đăng nhập bằng email là: `"Sử dụng số điện thoại/email/tên người dùng"`.

## 6. Lưu ý về tài khoản khi mới thay máy
- Trên máy mới tinh, app Gmail/Outlook chưa có sẵn tài khoản nào đăng nhập trong hệ thống (`dumpsys account` = 0).
- Muốn tự động đăng nhập TikTok cần có email nhận OTP, do đó cần add tài khoản Gmail/Outlook tương ứng vào máy hoặc đăng nhập qua 2FA TOTP secret nếu nick đã bật 2FA.
