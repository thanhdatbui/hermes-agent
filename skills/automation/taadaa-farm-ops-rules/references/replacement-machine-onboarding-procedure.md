# Quy trình thay thế & khởi tạo máy mới cho Taadaa Phone Farm (Samsung Galaxy S7)

## 1. Nguyên tắc cốt lõi & Cạm bẫy thực tế
- **CẤM đoán mò mật khẩu Wi-Fi:**
  - `kibe 1` (AP 192.168.110.253, zone1) dùng mật khẩu: `23102025` (trích xuất từ `show running-config no-encrypt` của Aruba Virtual Controller).
  - `kibe 2`, `admin 1`, `admin 2` dùng mật khẩu: `19051995`.
  - Mật khẩu sai sẽ gây lỗi `인증 오류 발생` (Authentication Error) và làm treo script nếu không kiểm tra kỹ.
- **Không dùng `adbjoinwifi` trên Android 8:**
  - `adb-join-wifi.apk` bị lỗi thiếu runtime permissions (chưa xin quyền location) trên Samsung S7 Android 8, intent chạy ngầm nhưng không kết nối được Wi-Fi.
  - **Cách làm chuẩn:** Mở `android.settings.WIFI_SETTINGS`, dump UI XML hoặc dùng tap để nhập mật khẩu và bấm Connect trực tiếp trên UI.

## 2. Các bước cấu hình máy mới thay thế máy cũ
1. **Phát hiện máy mới:**
   - So sánh danh sách `adb devices` với danh sách serial trong `taikhoan_run_safe.xlsx` để tìm serial mới cắm vào farm.
2. **Gỡ bỏ Keyguard & Màn hình khóa:**
   - `wm dismiss-keyguard`
   - Bấm HOME (`input keyevent 3`) và giải phóng popup MtpApplication/Samsung Tips.
3. **Kết nối Wi-Fi chuẩn AP:**
   - Mở màn hình cài đặt: `am start -a android.settings.WIFI_SETTINGS`.
   - Tìm SSID tương ứng (`kibe 1` cho máy 1-40 với pass `23102025`; `kibe 2` cho máy 41-80 với pass `19051995`).
   - Nhập mật khẩu và tap nút Kết nối.
   - Xác nhận có IP qua `ip addr show wlan0`.
4. **Chuẩn hóa Hardware & Cài đặt hệ thống S7:**
   - Đồng bộ giờ tự động: `settings put global auto_time 1 && settings put global auto_time_zone 1 && setprop persist.sys.timezone Asia/Ho_Chi_Minh`.
   - Thiết lập màn hình: `screen_off_timeout 600000`, `screen_brightness 0`, `screen_brightness_mode 0`, `stay_on_while_plugged_in 0`.
   - Tắt xoay màn hình & âm thanh: `accelerometer_rotation 0`, `sound_effects_enabled 0`.
   - Đặt ngôn ngữ: `setprop persist.sys.locale vi-VN && settings put system system_locales vi-VN`.
5. **Gán Proxy Sing-box:**
   - Gán `http_proxy` trỏ về `192.168.110.2:20000+N`.
   - Tắt captive portal: `captive_portal_mode 0`, `captive_portal_detection_enabled 0`.
6. **Cài đặt bộ Tool & Apps farm:**
   - Tool nền: `atx-agent` (`chmod 755` vào `/data/local/tmp/atx-agent`), `app-uiautomator.apk`, `app-uiautomator-test.apk`.
   - App: `com.microsoft.office.outlook`, `vn.vichanger.app`.
   - TikTok v46.6.3: Cài đặt toàn bộ 55 Split APKs qua lệnh:
     `adb -s <serial> install-multiple -r -d base.apk split_*.apk` (thư mục `D:\Taadaa\tools\tiktok_full_apks_v46.6.3`).
7. **Cập nhật Serial Mapping trong các File Excel:**
   - Cập nhật serial cũ thành serial mới trên các file:
     - `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
     - `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
     - `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` .. `Tik8.xlsx`
8. **Nghiệm thu & Báo cáo:**
   - Đưa máy về HOME (`input keyevent 3`).
   - Chụp ảnh màn hình nghiệm thu: `adb -s <serial> exec-out screencap -p > <path_anh>`.
   - Đính kèm đường dẫn ảnh dạng `MEDIA:<path_anh>`.
