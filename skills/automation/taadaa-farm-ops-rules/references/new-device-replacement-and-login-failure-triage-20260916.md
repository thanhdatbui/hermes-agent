# Quy Trình Thiết Lập Máy Mới Thay Thế (New Device Replacement) & Xử Lý Lỗi Login (2026-09-16)

## 1. Bản Đồ Hiện Trường Máy Mới (New Samsung Galaxy S7 Provisioning)
Khi thay thế một máy cũ hỏng bằng máy mới vào giàn (Ví dụ: Máy 30 thay thế serial `ce0217126cd4bc640c` -> `ce0416040cba423104`):

### Các bước hòa mạng và cấu hình hệ thống (Chuẩn O(1)):
1. **Tra cứu Wi-Fi & Proxy Singbox:**
   - Tra Wi-Fi SSID và Pass từ AP router (`kibe 1`: Pass trích xuất từ Aruba config).
   - Gán `http_proxy` theo đúng STT máy (`192.168.110.2:20000+STT`), kiểm tra kết nối qua `toybox nc` hoặc curl `http://ipinfo.io/json`.
2. **Cấu hình Samsung S7 Farm:**
   - `screen_brightness=0`, `screen_brightness_mode=0`, `stay_on_while_plugged_in=0`, `aod_mode=0` (tắt AOD), `screen_off_timeout=600000` (10 phút).
   - Dismiss triệt để popup kết nối USB (`automation_core.usb_popup.dismiss_usb_popup_shell`).
3. **Cài đặt bộ ứng dụng cơ sở:**
   - `atx-agent` (port 7912), `com.github.uiautomator`.
   - `TikTok v46.6.3` (55 Split APKs qua `install-multiple`).
   - `Outlook` (`com.microsoft.office.outlook`).
4. **Cập nhật đồng bộ toàn bộ Workbooks:**
   - Chạy script cập nhật serial cũ -> serial mới trên toàn bộ 12+ files: `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`, `Tik1.xlsx` -> `Tik8.xlsx`, `PROXYgandienthoai.xlsx`.

---

## 2. Lỗi Google Framework Treo Nền Trê Mới & Giải Pháp Khởi Động Lại
### Triệu chứng:
- Mở Gmail bị đứng ở màn hình `WelcomeTourActivity` ("Mới có trong Gmail"), tap vào nút `OK` (`welcome_tour_got_it`) nhưng popup trơ ra không đóng.
- Vào `Settings -> Thêm tài khoản -> Google`: Bấm vào nút Google nhưng hệ thống không mở màn hình nhập email của `com.google.android.gms`.
- Logcat báo lỗi: `GoogleCertificatesImpl: Source stamp verification failed ... GmsModuleFndr chimera module scan`.

### Giải pháp kỹ thuật chuẩn xác:
- **Nguyên nhân:** GApps/Google Play Services trên máy mới chưa khởi tạo xong hoặc bị treo callback nền.
- **Xử lý:**
  1. Kích hoạt lại `com.google.android.webview`: `adb shell pm enable com.google.android.webview`.
  2. Clear dữ liệu GMS: `adb shell pm clear com.google.android.gms` và `pm clear com.google.android.gm`.
  3. **Bắt buộc Reboot máy:** `adb reboot`, chờ `sys.boot_completed == 1`.
  4. Sau khi reboot, vào lại `Settings -> Add account -> Google` sẽ mở được luồng `MinuteMaidActivity` để đăng nhập tài khoản Gmail suôn sẻ.

---

## 3. Khác Biệt Giữa Hotmail Thường vs Hotmail Có OAuth Token (Graph API)
1. **Hotmail có OAuth Token:**
   - Lưu trữ trong các file text mua mail (`hotmail_all_60_bought.txt`, format: `email|pass|refresh_token|client_id`).
   - Tự động gọi thẳng **Microsoft Graph API** (`hotmail_provider.py`) để lấy mã OTP 6 số về điền vào TikTok.
   - **HOÀN TOÀN KHÔNG CẦN đăng nhập app Outlook trên điện thoại.**
2. **Hotmail thường không có token:**
   - Bắt buộc đăng nhập vào app Outlook trên máy hoặc nhập pass trực tiếp.

---

## 4. Kỷ Luật "Failure Evidence First" Khi Báo Cáo Lỗi (User Feedback 16/09/2026)
### Yêu cầu sống còn:
- **CẤM TUYỆT ĐỐI:** Sau khi chạy lỗi hoặc timeout thì chạy cleanup/force-stop đưa máy về HOME rồi mới chụp ảnh screencap gửi user (`MEDIA:m30_home.png`). Đây là báo cáo vô giá trị và bị người dùng phạt nặng.
- **QUY TRÌNH BẮT BUỘC:**
  1. Ngay khi phát hiện exception / kẹt OTP / sai pass / màn hình trắng / lỗi UI: **DỪNG NGAY LẬP TỨC VÀ CHỤP ĐÓNG BĂNG HIỆN TRƯỜNG TẠI CHỖ**.
  2. Báo cáo bằng chứng với dòng `MEDIA:<path>` ở dòng đầu tiên.
  3. Chỉ khi nào có lệnh tiếp theo của User hoặc sau khi đã chụp ảnh lưu trữ bằng chứng thành công mới được teardown an toàn.
