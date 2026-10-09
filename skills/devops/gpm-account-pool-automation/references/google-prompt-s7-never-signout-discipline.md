# Kỷ Luật Tuyệt Đối: Không Đăng Xuất Thiết Bị S7 Để "Tắt Lời Nhắc" & Cách Decouple S7 Chuẩn

## 1. Cấm Tuyệt Đối: Vào `device-activity` Đăng Xuất Thiết Bị Galaxy S7
- **Hành vi sai lầm:** Truy cập `https://myaccount.google.com/device-activity` -> chọn Galaxy S7 -> bấm **"Đăng xuất" (Sign out)** với mục đích "tắt Lời nhắc của Google" (Google Prompt).
- **Hậu quả nghiêm trọng:** Thiết bị Samsung Galaxy S7 thật của Farm bị thu hồi phiên đăng nhập Google, hiện thông báo *"Lỗi hành động tài khoản"* (Account action required), làm gián đoạn toàn bộ hoạt động của Farm (TikTok, đồng bộ Google Play Services, backup).

---

## 2. Bản Chất Cơ Chế "Lời Nhắc Của Google" (Google Prompt)
1. **Gắn chặt với thiết bị Android:** Chỉ cần điện thoại Android (Galaxy S7) còn đăng nhập tài khoản Google và có Google Play Services, Google **bắt buộc tự động gán máy đó làm thiết bị nhận Lời nhắc**.
2. **Không có nút Tắt riêng:** Trên giao diện tài khoản Google (`myaccount.google.com/signinoptions/twosv`), Google **HOÀN TOÀN KHÔNG CUNG CẤP** nút gạt (toggle) để tắt nhận lời nhắc cho một thiết bị cụ thể nếu thiết bị đó vẫn đang đăng nhập. Nút duy nhất làm biến mất thiết bị khỏi mục Lời nhắc là nút "Đăng xuất" (Sign out).
3. **Kết luận:** Muốn duy trì tài khoản trên máy S7 của Farm thì **bắt buộc phải chấp nhận thiết bị S7 tồn tại trong mục Lời nhắc của Google**, tuyệt đối không được tìm cách xóa/đăng xuất thiết bị khỏi `device-activity`.

---

## 3. Quy Trình Vượt Lời Nhắc Chuẩn Khi Login GPM (S7 Decoupling Thực Tế)
Để đăng nhập trên PC/GPM mà **hoàn toàn không cần chạm vào máy S7**, quy trình chuẩn là:
1. Tài khoản **phải được bật 2FA Google Authenticator (TOTP)** trước đó, Secret Key Base32 (32 ký tự) đã lưu vào `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`.
2. Khi mở trình duyệt GPM đăng nhập Gmail:
   - Điền Email $\rightarrow$ Next.
   - Điền Password $\rightarrow$ Next.
   - Nếu Google hiển thị màn hình Lời nhắc: *"Kiểm tra điện thoại Galaxy S7 của bạn"* hoặc hiển thị số để chọn:
     👉 **BƯỚC QUYẾT ĐỊNH:** Script Playwright click ngay vào liên kết:
     `button:has-text("Thử cách khác"), a:has-text("Thử cách khác"), button:has-text("Try another way"), a:has-text("Try another way")`
     👉 Trên danh sách tùy chọn xác minh: Click chọn phương thức Authenticator:
     `div[data-challengetype="6"], div:has-text("Authenticator"), div:has-text("Ứng dụng xác thực")`
     👉 Trích xuất Secret Key từ Excel, tính TOTP 6 số qua `pyotp.TOTP(secret).at(google_utc)`.
     👉 Điền mã 6 số vào ô `input#totpPin` hoặc `input[name="totpPin"]` $\rightarrow$ Next.
3. **Kết quả:**
   - Đăng nhập GPM thành công 100% trong 2-3 giây.
   - Hoàn toàn không cần mở máy S7, không cần tap số trên màn hình điện thoại.
   - Máy S7 trên Farm vẫn giữ đăng nhập nguyên vẹn 100%, không bị văng acc.

---

## 4. Lỗi Pipeline PowerShell Dọn Dẹp Chrome & Biến MSYS Bash
- **Lỗi pipe sai thuộc tính:**
  ```powershell
  # SAI: Trả về object có .Name = 'chrome.exe', pipe sang Stop-Process sẽ tìm theo tên thay vì PID -> Lỗi nuốt âm thầm do SilentlyContinue
  Get-CimInstance Win32_Process ... | Stop-Process -Force -ErrorAction SilentlyContinue

  # ĐÚNG:
  Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match $port } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  ```
- **Lỗi MSYS Bash Variable Expansion:** Khi chạy PowerShell từ Git-Bash qua cờ `-Command "..."` (dùng dấu ngoặc kép `"`), biến `$_` trong PowerShell bị Bash mở rộng thành chuỗi `$HOME` (`/c/Users/<user>`), làm hỏng câu lệnh.
  - **Khắc phục:** Luôn dùng dấu nháy đơn `powershell -Command '...'` hoặc bọc logic dọn dẹp tiến trình trong một hàm Python sử dụng thư viện `psutil`.
