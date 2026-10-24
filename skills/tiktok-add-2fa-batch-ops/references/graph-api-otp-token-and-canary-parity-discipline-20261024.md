# Graph API Token OTP Retrieval, Outlook App Fallback & Canary Parity Discipline (24/10/2026)

## 1. Điểm nghẽn cũ của luồng tạo Pass & Add 2FA trên Android S7
- **Phụ thuộc cứng vào app Outlook trên máy S7:** Khi TikTok yêu cầu xác minh danh tính qua Email OTP để tạo pass hoặc add 2FA, `LivePhaseBAdapter` trước đây chỉ gọi duy nhất `read_tiktok_otp_from_outlook_app()` thao tác ADB trên app Outlook.
- **Hệ quả thực tế:**
  1. Hòm thư Hotmail trên máy Android thường xuyên bị văng session hoặc chưa đăng nhập sẵn.
  2. Runner chỉ truyền `email` mà bỏ trống `password=None`, khiến Outlook app không thể tự động đăng nhập hòm thư mà báo lỗi `OUTLOOK_APP_MAILBOX_NOT_SIGNED_IN`.
  3. Lỗi bị nuốt trong khối fail-safe, dẫn tới script âm thầm bỏ qua bước tạo pass. Cột PASS (D) trong Excel để trống `None`, khiến 226+ nick Admin bị nghẽn không đủ điều kiện sang bước bảo mật Hotmail.

## 2. Kiến trúc đọc OTP 2 tầng hoàn thiện (`flows/hotmail_login.py`)

### Tầng 1: Đọc mã OTP qua Microsoft Graph API Token (< 0.5s, không chạm điện thoại)
- **Kho Token sẵn có:** 625 / 631 nick Admin trong `D:/OneDrive/TaadaaData/admin/gmail_clean_v2.xlsx` (sheet `Gmail Accounts`) đã lưu sẵn cặp `Refresh Token` (`M.C5...`, Cột 9 / Index 8) và `Client ID` (`9e5f94bc...`, Cột 10 / Index 9).
- **Cơ chế gọi:**
  1. Tra cứu email mục tiêu trong `gmail_clean_v2.xlsx`.
  2. Gửi request OAuth2 tới `https://login.microsoftonline.com/consumers/oauth2/v2.0/token` lấy `access_token` tạm thời.
  3. Gọi REST API `https://graph.microsoft.com/v1.0/me/messages?$top=5&$orderby=receivedDateTime desc` với Bearer token.
  4. **Kỷ luật độ tươi (Freshness Filter):** BẮT BUỘC kiểm tra `receivedDateTime` của thư TikTok trong vòng `<= 15 phút` (`<= 900s`). Tuyệt đối không nhặt nhầm OTP cũ từ lúc đăng ký nick vài tuần trước! Polling tối đa 12 lần (mỗi lần giãn cách 3s) để bắt ngay khi TikTok vừa phát mã.

### Tầng 2: Native Outlook App Fallback với Tự động Đăng nhập
- Nếu hòm thư không có token Graph (hoặc token bị revoke): Script tự động trích xuất mật khẩu gốc (`PASS MAIL`, Cột 7) từ Excel làm `password`.
- Khi app Outlook trên máy S7 chưa có tài khoản, script tự động kích hoạt `login_outlook_app(adb, device, email, password, ...)` để nạp tài khoản vào Outlook, sau đó đọc hòm thư Inbox.

## 3. Kỷ luật Canary Parity (Chống Canary Ảo & Chống Gửi Thiếu Ảnh)

### 3.1. Chạy Canary giống hệt như Cron thực tế (No Stubbing / No False Success)
- **CẤM TUYỆT ĐỐI:** Chạy canary với cờ chắp vá như `--password-only` trên nick chưa ở màn hình đổi pass rồi vội vàng báo cáo `success` khi giá trị thực tế trong workbook vẫn là `PASS: None`.
- **Chuẩn hóa Canary:** Canary kiểm chứng BẮT BUỘC phải chạy đúng entrypoint và tham số của Cron (`run_batch_live_2fa.py --workbook-path ... --workbook-sheet 'Tài Khoản' --rows <row> --live`), thực thi trọn vẹn từ mở TikTok ➔ Add 2FA ➔ Bóc Secret ➔ Đọc OTP Graph ➔ Tạo Pass ➔ Ghi nhận vào Cột 4 (PASS) và Cột 5 (2FA) của Excel.

### 3.2. Gate 6 & Invariant Visual Evidence (Bắt buộc ảnh hiện trường)
- Báo cáo Canary THẤT BẠI NẶNG NHẤT nếu không đính kèm ảnh bằng chứng thực tế (`MEDIA:<path>`).
- BẮT BUỘC kéo ảnh screencap từ thiết bị về Kibe, chạy WinRT OCR đọc text màn hình (xác nhận đúng màn hình Account Switcher / Settings / 2-Step Verified), soi mắt kiểm tra trước khi gửi thẻ `MEDIA:`.

### 3.3. Phòng chống va chạm lịch nuôi acc (Active Feed Session Check)
- Trước khi kích hoạt bất kỳ lệnh canary hay batch live nào trên thiết bị: BẮT BUỘC kiểm tra tiến trình `run_tiktok.py --mode multi-machine-feed-session`.
- Nếu ca nuôi (Feed + Upload Hook) đang chạy trên dải máy đó: **TUYỆT ĐỐI CẤM** can thiệp, cấm kill process, cấm force-preempt lock. Báo cáo rõ máy đang trong phiên nuôi chính và chờ nhả máy an toàn.

## 4. Các cạm bẫy thực thi Remote Node Admin-PC & CLI Encoding

### 4.1. Lệch môi trường Python trên Admin-PC (`automation_core`)
- Lệnh `python` mặc định trong PATH của Admin-PC trỏ về `Python311\python.exe` (không cài `automation_core`), gọi trực tiếp sẽ văng `ModuleNotFoundError: No module named 'automation_core'`.
- **Quy chuẩn:** BẮT BUỘC dùng đúng `D:\Taadaa\python-envs\automation\Scripts\python.exe` hoặc nạp `PYTHONPATH`:
  `$env:PYTHONPATH="D:\Taadaa\automation-core\src;D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner"`

### 4.2. Tránh truyền tham số có dấu tiếng Việt qua SSH Windows (`--workbook-sheet`)
- Khi gọi qua SSH / cmd.exe / PowerShell, chuỗi `"Tài Khoản"` bị lỗi bảng mã ANSI thành `"Ti Kho?n"`.
- Vì `run_batch_live_2fa.py` đã mặc định `--workbook-sheet` là `"Tài Khoản"` và có fuzzy resolver, **tốt nhất bỏ qua tham số `--workbook-sheet`** khi gọi từ CLI để tránh lỗi encoding.

### 4.3. Kỷ luật đồng bộ code 2 node (Kibe ➔ Admin-PC)
- Code sửa ở `D:/Taadaa/Hotmail` trên Kibe không tự chạy trên Admin-PC.
- Sửa xong BẮT BUỘC copy file sang `D:/OneDrive/TaadaaData/admin/` và kích hoạt script `copy_to_admin.py` trên Admin-PC trước khi chạy batch hoặc canary, tránh trường hợp runner Admin chạy code cũ nuốt lỗi âm thầm.
