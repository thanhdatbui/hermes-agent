# Graph API OTP Token Integration & Cron-Parity Canary Discipline (24/10/2026)

## 1. Bối cảnh & Điểm nghẽn hệ thống (Admin Cluster)
- **Kho dữ liệu Token có sẵn nhưng chưa kết nối**:
  * Tại `D:/OneDrive/TaadaaData/admin/gmail_clean_v2.xlsx` (sheet `Gmail Accounts`), hệ thống lưu 723 tài khoản có sẵn `Refresh Token` (`M.C5...`) và `Client ID` (`9e5f94bc...`).
  * Đối soát 630 nick Admin: Có **625 / 631 tài khoản (99%)** đã có sẵn Refresh Token Graph API.
- **Điểm nghẽn kiến trúc trước đây**:
  * Runner `tiktok-add-bao-mat-f2a` (`live_phase_b_adapter.py`) khi đọc OTP email chỉ gọi ADB mở app Outlook trên thiết bị Android S7 (`read_tiktok_otp_from_outlook_app`).
  * Do app Outlook trên dàn máy Admin không duy trì sẵn phiên đăng nhập, app văng lỗi `OUTLOOK_APP_MAILBOX_NOT_SIGNED_IN`.
  * Khối `except Exception: return None` nuốt mất ngoại lệ khiến runner âm thầm kích hoạt fail-safe: lưu 2FA Secret vào Cột E nhưng **bỏ qua bước tạo pass TikTok**, khiến Cột D (`PASS`) bị trống `None`.
  * Cột D trống khiến Supervisor GPM chặn toàn bộ nick Admin tại `WAIT_7D`, không cho phép chuyển sang `CHANGE_INFO` để đổi pass Hotmail.

## 2. Kiến trúc đọc OTP 2 Tầng (`flows/hotmail_login.py`)
Mọi luồng đọc OTP xác minh danh tính từ Hotmail cho TikTok bắt buộc đi qua 2 tầng:

1. **Tầng 1 (Ưu tiên số 1 - Microsoft Graph REST API Token, < 1s)**:
   - Helper `_try_read_tiktok_otp_graph(email)` tra cứu email trong `gmail_clean_v2.xlsx`.
   - Nạp cặp `Refresh Token` và `Client ID`, đổi `access_token` qua OAuth2 `login.microsoftonline.com`.
   - Truy vấn REST API `https://graph.microsoft.com/v1.0/me/messages?$top=5&$orderby=receivedDateTime desc`.
   - **Chốt chặn độ tươi OTP**: Chỉ chấp nhận email TikTok nhận được trong vòng **<= 15 phút (900s)** so với thời điểm hiện tại (`datetime.now(timezone.utc)`), chống nhặt nhầm OTP cũ của các đợt reg từ tháng trước.
   - Polling 12 lần x 3s để đón thư vừa gửi tới từ TikTok.
   - Tốc độ bóc tách mã: < 0.5s - 1s, hoàn toàn không phụ thuộc màn hình điện thoại, không sợ kẹt uiautomator.

2. **Tầng 2 (Dự phòng - Native Outlook App + Auto-login)**:
   - Nếu không có token: Helper tự bóc tách `PASS MAIL` gốc từ workbook Excel.
   - Khi mở app Outlook trên thiết bị Android mà hòm thư chưa có sẵn, script tự động gọi `login_outlook_app(adb, device, email, password, ...)` để đăng nhập tài khoản vào Outlook app rồi đọc OTP.

## 3. Kỷ luật Cron-Parity Canary & Chống Báo Cáo Ảo (Anti-Premature Report)
- **Nguyên tắc Cron Parity**:
  * Khi User yêu cầu Canary sau khi fix, Canary BẮT BUỘC phải chạy theo **ĐÚNG CÁCH THỨC VÀ LỆNH** mà Cron chính thức (`night-tiktok-2fa-watchdog`) sẽ thực thi:
    `& 'D:\Taadaa\python-envs\automation\Scripts\python.exe' python_runner/run_batch_live_2fa.py --workbook-path <wb> --workbook-sheet 'Tài Khoản' --live`
  * **CẤM TUYỆT ĐỐI**: Chạy lệnh lẻ với cờ `--password-only` rồi phán đã xong 2FA + đổi pass. Cờ này chỉ chạy nhánh đổi pass và nếu màn hình không nằm ở form đổi pass, runner sẽ return ngay mà không làm gì.
- **Đối soát dữ liệu kép (Workbook Verification)**:
  * Trước khi báo cáo hoàn thành cho User, BẮT BUỘC mở file Excel đọc lại giá trị thực tế của hàng đó:
    + Cột D (4): `PASS` khác `None` và độ dài >= 12 ký tự.
    + Cột E (5): `2FA` khác `None` và độ dài >= 16 ký tự.
- **Kỷ luật Môi trường Python trên Admin Node**:
  * Lệnh `python` mặc định trên Admin-PC trỏ vào `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe` (môi trường render video, KHÔNG có `automation_core`).
  * Mọi lệnh thực thi automation/cron trên Admin bắt buộc dùng đúng Python venv automation:
    `D:\Taadaa\python-envs\automation\Scripts\python.exe`
- **Gate 6 Invariant (Bằng chứng hình ảnh trên thiết bị)**:
  * CẤM TUYỆT ĐỐI báo cáo kết quả chay không có hình.
  * Screencap trên thiết bị phải chụp tại màn hình đích (Account Switcher hiển thị danh sách nick hoặc màn hình 2FA/Security settings).
  * Kiểm định ảnh qua WinRT OCR / vision trước khi gửi, cấm gửi ảnh màn hình Home/Launcher.
