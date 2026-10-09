# Cấu hình máy mới / thay thế máy die trong Taadaa Farm S7

## 1. Mật khẩu Wi-Fi thực tế trên Aruba AP
- **`kibe 1` (AP-325 Zone 1, IP 192.168.110.253):** Mật khẩu là **`23102025`** (truy xuất từ `show running-config no-encrypt`).
- **`kibe 2`, `admin 1`, `admin 2`:** Mật khẩu là **`19051995`**.
- **CẤM** dùng `adbjoinwifi` trên Samsung Galaxy S7 (Android 8) vì app bị hạn chế quyền Location runtime gây kẹt kết nối.
- Cách kết nối chuẩn: Mở `android.settings.WIFI_SETTINGS`, tap SSID `kibe 1` qua tọa độ XML, nhập mật khẩu và tap `연결` (Connect).

## 2. Bẫy lệch thời gian xuất xưởng (năm 2016)
- Khi máy mới lắp hoặc cúp nguồn, hệ thống hay bị tụt về `2016` -> Gây lỗi SSL handshake (`CertificateNotYetValid`), cờ `dumpsys connectivity` bị kẹt `lastValidated: false` làm TikTok và trình duyệt báo "Không có Internet".
- Lệnh khắc phục ngay lập tức:
  ```bash
  adb -s <serial> shell "settings put global auto_time 1 && settings put global auto_time_zone 1 && setprop persist.sys.timezone Asia/Ho_Chi_Minh"
  ```

## 3. Hardware Profile Farm S7 (Độ sáng 0 & Màn hình đen hoàn toàn)
- Cài đặt chống nóng màn hình và tiết kiệm pin:
  ```bash
  adb -s <serial> shell "settings put system screen_brightness 0"
  adb -s <serial> shell "settings put system screen_brightness_mode 0"
  adb -s <serial> shell "settings put system screen_off_timeout 600000"
  adb -s <serial> shell "settings put global stay_on_while_plugged_in 0"
  adb -s <serial> shell "settings put system aod_mode 0 && settings put global aod_mode 0"
  ```
- **Tắt màn hình hoàn toàn:** Gửi `input keyevent 223` -> Kiểm tra `dumpsys power | grep "Display Power"` phải đạt `state=OFF` (màn hình đen tuyệt đối, không hiện đồng hồ Always-On Display).

## 4. Gán Proxy Sing-box
- Mỗi máy N trỏ vào cổng Sing-box local:
  ```bash
  adb -s <serial> shell "settings put global http_proxy 192.168.110.2:20000+N"
  adb -s <serial> shell "settings put global captive_portal_mode 0"
  adb -s <serial> shell "settings put global captive_portal_detection_enabled 0"
  ```
- Kiểm tra kết nối ra proxy:
  ```bash
  adb -s <serial> shell "toybox nc -w 3 192.168.110.2 20000+N < /dev/null && echo PROXY_OK || echo PROXY_FAIL"
  ```

## 5. Cài đặt APK lớn (>50MB)
- File APK nằm trên OneDrive (`D:\OneDrive\apk-bank\...`) nếu đọc trực tiếp qua ADB stream có thể bị timeout 600s.
- **Quy tắc:** Copy file APK lớn về ổ cứng cục bộ (`D:\Taadaa\tools\`) trước khi chạy `adb install` để cài đặt mượt mà trong vài giây.
- TikTok v46.6.3 cài bằng 55 Split APKs:
  `adb -s <serial> install-multiple -r -d base.apk split_*.apk` từ thư mục `D:\Taadaa\tools\tiktok_full_apks_v46.6.3`.

## 6. Cập nhật Serial Mapping toàn farm
- Cập nhật serial mới thay thế serial cũ trong các file:
  + `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
  + `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`
  + `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` đến `Tik8.xlsx`
- Cập nhật danh sách hardcode trong repo `Tiktok_Reg`:
  + `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` (dict `ACCOUNTS`)
  + `D:\Taadaa\Tiktok_Reg\calibrate.py`

## 7. Kỷ luật 100% Tiếng Việt & Đăng nhập TikTok v46.6.3
- **Tuyệt đối 100% Tiếng Việt:** Cả Coordinator và Subagent bắt buộc phản hồi bằng tiếng Việt; cấm xuất template/báo cáo tiếng Anh làm phiền người dùng.
- **Form Đăng nhập TikTok v46.6.3:**
  + Nút chọn phương thức email trong build mới mang text: `"Sử dụng số điện thoại/email/tên người dùng"` (thay vì các chuỗi cũ như `"Dùng số điện thoại/email"`).
  + Khi gọi script đăng nhập cho máy mới, dùng cờ `--resume` nếu máy đã mở sẵn màn hình điền email để tránh bị lặp lại flow từ đầu.

## 8. Hiện tượng cúp điện / sụp nguồn và đặc thù ROM S7
- **ROM gốc:** Sau khi cúp điện và có điện lại, máy chỉ hiển thị màn hình sạc pin (LPM), KHÔNG tự khởi động lại vào Android mà bắt buộc phải bấm nút nguồn vật lý.
- **ROM mod (Auto-boot / Boot on charge):** Tự động khởi động vào OS ngay khi có nguồn sạc trở lại mà không cần can thiệp tay.
- **Đường dẫn ADB chuẩn trên host Kibe:** Khi `adb` chưa nằm trong system PATH của bash, dùng trực tiếp binary: `"C:\Program Files (x86)\xiaowei\tools\adb.exe"` hoặc script O(1): `python D:/Taadaa/tools/inspect_machine.py <N>`.
- **Chẩn đoán nguồn điện & Uptime O(1):**
  + Kiểm tra thời điểm tắt đột ngột và boot lại của Windows:
    `powershell -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='System'; Id=41,6008} -MaxEvents 5"`
  + Kiểm tra uptime thiết bị qua ADB: `adb -s <serial> shell uptime`
  + Phân biệt sụt áp lưới tức thời 1-2s (chớp quạt/đèn cả nhà do Recloser EVN, nguồn PC có tụ lọc gánh được nhưng adapter box phone sụp ngay) với mất điện kéo dài.

## 9. Đọc OTP Hotmail Qua OAuth Token (CẤM Đăng Nhập Thủ Công App Outlook)
- **Kiến trúc đọc OTP Hotmail của Farm:**
  + Các Hotmail mua loại 2 (`mail|pass|refresh_token|client_id`) lưu trong `hotmail_all_60_bought.txt` hoặc cột `token` / `client_id` của `gmail_clean_v2.xlsx`.
  + Module `D:\Taadaa\Tiktok_Reg\hotmail_provider.py` đã tích hợp sẵn hàm `exchange_refresh_token` để tự động đổi token lấy `access_token` và truy vấn Microsoft Graph API đọc mã OTP về tự điền vào TikTok.
  + **KỶ LUẬT TỐI CAO:** Khi tài khoản có OAuth Token, **CẤM TUYỆT ĐỐI** mất công mở app Outlook / Gmail trên Android để đăng nhập tài khoản thủ công. Chỉ cần gán biến môi trường `HOTMAIL_TOKEN_LIST` hoặc cập nhật đúng cột trong `gmail_clean_v2.xlsx`, script login sẽ tự động đọc OTP qua API backend.
- **Bẫy `suspicious_login` (SparkActivity):**
  + Khi máy mới tinh hoặc proxy bị TikTok gắn cờ đăng nhập bất thường, TikTok không gửi OTP về mail mà kích hoạt màn hình xác minh WebView:
    `com.ss.android.ugc.trill/com.bytedance.hybrid.spark.page.SparkActivity` (`enter_from=suspicious_login`).
  + Đây là luồng challenge dạng Web/Captcha của TikTok đối với thiết bị mới, không có node native nên script automation UI cơ bản sẽ dừng lại báo cáo.
