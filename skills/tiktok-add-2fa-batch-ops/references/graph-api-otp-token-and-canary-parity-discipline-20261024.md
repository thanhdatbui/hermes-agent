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

### 4.4. Bắt buộc khai báo Writer ID tránh lỗi WorkbookError ẩn
- Trong `automation_core.workbook.assert_writer_identity`, hệ thống kiểm soát khóa đơn ghi (single writer lock) bằng cách so khớp 2 biến môi trường:
  - `TIKTOK_ADD_EXPECTED_WRITER_ID`
  - `TIKTOK_ADD_WRITER_ID`
- **Cạm bẫy:** Khi chạy script canary độc lập hoặc gọi `run_capture_phase_b.py` bên ngoài pool `run_batch_live_2fa.py`, nếu thiếu 2 biến này, hàm `single_writer_workbook_update` sẽ quăng ngoại lệ `WorkbookError("BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking")`. Runner bắt `RuntimeError` và in ra `{"status": "failed", "reason": "WorkbookError"}` ngay sau khi đã điền mật khẩu TikTok thành công, khiến việc cập nhật Excel bị hủy bỏ âm thầm.
- **Quy chuẩn:** Mọi lệnh thực thi ghi workbook BẮT BUỘC phải nạp trong `env`:
  ```python
  env["TIKTOK_ADD_EXPECTED_WRITER_ID"] = "tiktok_tracking_writer"
  env["TIKTOK_ADD_WRITER_ID"] = "tiktok_tracking_writer"
  ```

### 4.5. Điều phối lệnh SSH dài (> 60s) & Bẫy Windows File Descriptor
- Terminal của Coordinator có timeout trần foreground là 60s, trong khi chu trình Add 2FA + Đổi mật khẩu trên điện thoại S7 kéo dài 60–90s.
- Nếu gọi `admin_ssh.py --timeout 180` trực tiếp không chuyển hướng, lệnh foreground sẽ bị ngắt ở 58–60s (exit code 124).
- **Quy tắc điều phối bền vững:** Chuyển hướng stdout/stderr của lệnh từ xa vào file log cố định trên disk:
  ```bash
  python D:/Taadaa/tools/admin_ssh.py --timeout 180 "python D:\OneDrive\TaadaaData\admin\run_canary.py ... > D:\OneDrive\TaadaaData\admin\result.txt 2>&1"
  ```
  Ngay cả khi terminal foreground timeout, tiến trình trên Admin-PC vẫn tiếp tục chạy độc lập đến khi hoàn tất và ghi toàn bộ `STDOUT`, `STDERR`, `EXIT_CODE` vào `result.txt`.
- **Cảnh báo Windows FD:** Trên Windows, `subprocess.Popen` nếu đặt `close_fds=True` sẽ chặn kế thừa file descriptor mở qua Python, làm mất output hoặc kết thúc tiến trình con sớm. Phải mở file unbuffered/append và không đóng handle khi Popen chưa xong.

## 5. Bẫy kiểm chứng Form Thay đổi Mật khẩu & Va chạm Mật khẩu cũ (Password Collision & Toast Check)

### 5.1. Triệu chứng & Nguyên nhân
- Khi tài khoản chuyển sang nhánh màn hình **"Thay đổi mật khẩu"**, runner sinh mật khẩu ngẫu nhiên, gõ vào trường `EditText` và bấm nút **"Tiếp tục"**.
- Nếu mật khẩu vừa sinh vô tình trùng với mật khẩu cũ của tài khoản, TikTok từ chối lưu và hiện toast cảnh báo màu đỏ:
  `"Mật khẩu mới không thể giống mật khẩu cũ"` (hoặc `"New password cannot be the same as old password"`).
- **Lỗ hổng logic cũ:** Hàm `_complete_password_setup` chỉ `_wait_for` kiểm tra không có chữ `"tạo mật khẩu"` / `"create password"`. Vì tiêu đề màn hình là `"Thay đổi mật khẩu"`, điều kiện này thỏa mãn ngay lập tức, khiến runner tưởng đã lưu thành công và gọi callback ghi pass vào Excel trong khi mật khẩu chưa hề được TikTok cập nhật!

### 5.2. Giải pháp cơ giới hóa bất biến ở tầng Script (`live_phase_b_adapter.py`)
1. **Quy tắc vàng của User về thông báo "Mật khẩu mới không thể giống mật khẩu cũ":**
   - Khi điền mật khẩu và bấm "Tiếp tục", nếu TikTok bắn ra dòng chữ đỏ:
     `"Mật khẩu mới không thể giống mật khẩu cũ"` (hoặc `"New password cannot be the same as old password"`).
   - **BẢN CHẤT:** Dòng này chứng minh 100% mật khẩu vừa nhập vào **chính là mật khẩu hiện tại đang hoạt động của nick**!
   - **XỬ LÝ:** Tuyệt đối không xóa đi đổi tiếp hay sinh pass khác. Coi như đã xác minh mật khẩu thành công (`return True`), lưu luôn chuỗi mật khẩu đó vào Excel và kết thúc phiên đổi pass.
2. **Cơ chế bắt điều kiện kép trong `_complete_password_setup()`:**
   - Script không chỉ chờ form đóng mà định nghĩa hàm vị ngữ `_pw_confirmed_or_same(xml)`:
     ```python
     def _pw_confirmed_or_same(xml: str) -> bool:
         low = xml.casefold()
         # Case 1: TikTok báo trùng pass cũ -> Pass đã đúng, lưu luôn pass đó
         if "mật khẩu mới không thể giống mật khẩu cũ" in low or "new password cannot be the same" in low:
             return True
         # Case 2: Đã đổi thành công và form đổi/tạo pass đã biến mất
         return (
             "tạo mật khẩu" not in low
             and "create password" not in low
             and "thay đổi mật khẩu" not in low
             and "change password" not in low
         )
     ```
   - Sau đó `on_password_created(self.account_password)` được kích hoạt để ghi nhận ngay vào workbook.

### 5.3. Kỷ luật lưu trữ quy tắc logic: Lưu ở tầng Script, cấm đẩy vào Persistent Memory
- **Chỉ thị của User (24/10/2026):** Mọi logic xử lý nghiệp vụ TikTok (như bắt thông báo trùng mật khẩu cũ, định danh writer lock, timeout) BẮT BUỘC phải cài đặt cơ giới hóa bằng code trong runner (`live_phase_b_adapter.py`, `run_batch_live_2fa.py`), TUYỆT ĐỐI KHÔNG lưu tạm bợ vào Persistent Memory (`memory`).
- Persistent Memory chỉ dành cho thông tin định danh/sở thích của User; đẩy code rules vào memory sẽ làm context bloat và không tự động hoá được cho các worker khác.

### 5.4. Giải thích hiện tượng lệch pha dữ liệu (Data Drift: Excel trống nhưng TikTok có pass)
- **Bản chất:** Các nick Admin được đăng ký qua OTP Email không tạo pass, nên trong Excel ban đầu là `None`.
- Khi runner chạy canary hoặc batch: Nếu TikTok đã đổi pass thành công ở bước Submit, nhưng runner bị crash/lỗi ở bước ghi workbook (ví dụ thiếu writer lock `TIKTOK_ADD_WRITER_ID`), cột PASS trong Excel vẫn là `None` trong khi TikTok đã đổi sang pass mới.
- Khi người vận hành hoặc phiên chạy sau nhập lại chính chuỗi đó, TikTok sẽ bắn lỗi *"Mật khẩu mới không thể giống mật khẩu cũ"*. Lúc này cơ chế ở 5.2 sẽ tự động nhận diện pass đó là pass sống của nick và cứu hộ ghi đè ngay vào Excel.

## 6. Kỷ luật ứng xử với User: Hành động trước, chứng minh bằng dữ liệu
- Khi phát hiện trục trặc hoặc kẹt máy: **TUYỆT ĐỐI CẤM** trả lời bằng những đoạn văn dài phân trần, giải thích hay than thở khiến User bức xúc ("sao cứ khóc lóc mệt thế").
- **Kỷ luật chuẩn:**
  1. Kiểm tra trạng thái máy qua ADB (`inspect_machine.py`) ngay lập tức.
  2. Khắc phục điểm nghẽn kỹ thuật trong im lặng.
  3. Kích hoạt chạy và đối soát trực tiếp trên file Excel (Cột PASS & 2FA).
  4. Trả lời ngắn gọn, rành mạch kèm bằng chứng thị giác đã soi mắt qua Vision và số liệu thực tế đã cập nhật trong workbook.
