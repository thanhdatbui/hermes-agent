# Khắc phục lỗi Samsung S7 mới tinh: GMS Freeze & Failure Evidence First (16/09/2026)

## 1. Hiện tượng & Bản chất lỗi GMS Freeze trên S7 mới
Khi đưa một máy Samsung Galaxy S7 (Android 8.0) mới tinh hoặc vừa wipe ROM vào farm:
- **Hiện tượng 1**: Mở app Gmail luôn hiện màn hình giới thiệu `Mới có trong Gmail` (`WelcomeTourActivity`). Nút `OK` (`welcome_tour_got_it`, bounds: `[0,1752][1080,1920]`) nhận sự kiện click/tap qua ADB, ATX RPC nhưng hoàn toàn trơ ra không đóng.
- **Hiện tượng 2**: Vào `Cài đặt Android -> Tài khoản -> Thêm tài khoản -> Google`: Màn hình đứng im, không bật ra giao diện nhập email của Google.
- **Hiện tượng 3**: App TikTok mở WebView xác minh thiết bị (`SparkActivity / suspicious_login`) bị trắng xóa hoàn toàn do nhân `com.google.android.webview` cũ (v70) bị lỗi cú pháp JS `Unexpected token ?`.

### Nguyên nhân kỹ thuật:
- Package `com.google.android.webview` bị ở trạng thái `disabled-user` trên ROM stock hoặc image clone.
- Trạng thái Google Services Framework (GMS / GSF) bị treo do tiến trình khởi tạo nền (`Phenotype / MinuteMaidActivity`) chưa hoàn thành sau khi boot lần đầu.

## 2. Quy trình xử lý dứt điểm (Standard Recovery Flow)
Không cố spam tap ADB hay chạy uiautomator click lặp lại. Thực hiện đúng trình tự 4 bước:

1. **Enable lại WebView & Clear cache Google Framework**:
   ```bash
   adb -s <SERIAL> shell pm enable com.google.android.webview
   adb -s <SERIAL> shell pm clear com.google.android.gm
   adb -s <SERIAL> shell pm clear com.google.android.gms
   ```
2. **Reboot máy bắt buộc**:
   ```bash
   adb -s <SERIAL> reboot
   ```
   Chờ máy online và `sys.boot_completed == 1`.
3. **Mở Settings để nạp tài khoản Google**:
   ```bash
   adb -s <SERIAL> shell am start -a android.settings.ADD_ACCOUNT_SETTINGS
   # Tap vào dòng 'Google' -> GMS lúc này sẽ bật MinuteMaidActivity thành công!
   ```
4. **Xử lý popup bàn phím Samsung khi nhập mật khẩu**:
   - Khi bàn phím hiện popup "Chọn bàn phím" đè lên màn hình, set IME về Samsung Keypad:
     ```bash
     adb -s <SERIAL> shell ime set com.sec.android.inputmethod/.SamsungKeypad
     ```
   - Nhập email -> mật khẩu -> Đồng ý điều khoản -> Vào lại Gmail xác nhận Hộp thư đến (Inbox) đã đồng bộ.

## 3. Kiến trúc Hotmail: OAuth Token vs Login App Outlook
- **Hotmail có OAuth Token**: Các tài khoản Hotmail mua có sẵn `refresh_token|client_id` (trong `hotmail_all_60_bought.txt`), repo `Tiktok_Reg/hotmail_provider.py` tự động đổi `refresh_token` lấy `access_token` để gọi thẳng **Microsoft Graph API** lấy mã OTP TikTok. **Tuyệt đối KHÔNG cần đăng nhập vào app Outlook trên điện thoại**.
- **Hotmail thường không có Token**: Bắt buộc đăng nhập vào app Outlook hoặc thêm tài khoản IMAP trên thiết bị.

## 4. Quy tắc bất di bất dịch: FAILURE EVIDENCE FIRST (Claude CLI Architecture)
- **Cấm tiệt**: Phát hiện lỗi -> chạy Teardown/Force-stop/bấm HOME -> mới chụp ảnh -> gửi ảnh HOME rác.
- **Bắt buộc**: Ngay millisecond phát hiện lỗi (sai PIN, OTP kẹt, trắng màn hình, timeout, captcha):
  1. Chụp ảnh screencap đóng băng hiện trường NGAY LẬP TỨC (`FREEZE SCREENSHOT`) tại chỗ.
  2. Kiểm tra `foreground_package`: Nếu là launcher/HOME -> chặn gửi và báo động.
  3. In đường dẫn `MEDIA:<path>` ở dòng đầu tiên của báo cáo.
  4. Sau khi đã gửi ảnh bằng chứng hiện trường xong xuôi -> mới được phép chạy các lệnh dọn dẹp hoặc về HOME.
