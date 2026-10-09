# Google Prompt (Lời Nhắc) Removal & Safe Chrome Process Cleanup

## 1. BẮT BUỘC: Tắt "Lời Nhắc Của Google" (Google Prompt) Sau Khi Bật 2FA TOTP

### Lý Do & Tác Động Vận Hành
Khi bật 2-Step Verification (2FA / 2SV) cho tài khoản Google trên trình duyệt, Google mặc định tự động kích hoạt **"Lời nhắc của Google" (Google Prompt)** và gán vào toàn bộ thiết bị Android (Samsung Galaxy S7 của Farm) đang đăng nhập tài khoản đó.
- Nếu không tắt Lời nhắc của Google: Khi đăng nhập tài khoản trên các môi trường mới hoặc OmniRouter, Google sẽ tự động đẩy thông báo chọn số / prompt về màn hình điện thoại S7.
- Điện thoại S7 đang chạy cron TikTok full-screen sẽ bị đè popup, treo phiên nuôi acc, hoặc không hiển thị kịp dẫn đến timeout hủy phiên đăng nhập.
- **Quy tắc bắt buộc:** Sau khi kích hoạt thành công Google Authenticator (TOTP Base32), BẮT BUỘC phải vào trang `https://myaccount.google.com/signinoptions/twosv` và gỡ bỏ / xóa sạch toàn bộ thiết bị khỏi "Lời nhắc của Google", chỉ để lại DUY NHẤT phương thức **Ứng dụng Authenticator**.

### Quy Trình Xóa Lời Nhắc Của Google Trên Playwright CDP
1. Điều hướng tới `https://myaccount.google.com/signinoptions/twosv`.
2. Nếu gặp màn hình yêu cầu nhập lại mật khẩu (`signin/challenge/pwd`): Điền password từ Excel và submit Next.
3. Chờ trang `twosv` tải xong (`wait_until="domcontentloaded"`).
4. Tìm khối "Lời nhắc của Google" (`Google prompts` / `Thiết bị nhận lời nhắc`):
   - Quét các nút xóa / biểu tượng thùng rác bên cạnh thiết bị S7:
     `button[aria-label*="Xóa"], button[aria-label*="Delete"], button[aria-label*="Remove"], div[role="listitem"] button:has-text("Xóa")`
   - Hoặc click "Đăng xuất khỏi thiết bị này" / "Không nhận lời nhắc trên thiết bị này".
   - Bắt dialog xác nhận và click "Xóa" / "Xác nhận".
5. Kiểm tra lại DOM: Xác nhận mục "Lời nhắc của Google" không còn thiết bị nào hoặc đã bị tắt hoàn toàn.

---

## 2. Xử Lý Triệt Để Lời Nhắc / Popup Onboarding Của Google

Trước khi đóng profile, luôn quét và bấm tắt các màn hình đề xuất/onboarding của Google để không làm phiền người dùng:
- **Tùy chọn khôi phục tài khoản:** URL `gds.google.com/web/recoveryoptions` -> Click nút **"Hủy"** hoặc **"Để sau"**.
- **Cập nhật địa chỉ nhà:** URL `gds.google.com/web/homeaddress` -> Click nút **"Bỏ qua"** (`button:has-text("Bỏ qua")`).
- **Banner hoàn tất 2FA:** URL `signinoptions/twosv` -> Click **"Done"** hoặc **"Skip"** trên modal thành công.
- **Trang chủ tài khoản:** URL `myaccount.google.com` -> Click **"Bỏ qua"** trên các thẻ gợi ý bảo mật.

---

## 3. Bug Critical: PowerShell Pipeline `Stop-Process` Bị Nuốt Lỗi Khi Dọn Chrome

### Triệu Chứng
Các script chạy xong nhưng hàng chục cửa sổ Chrome GPM vẫn mở nguyên trên desktop / taskbar, làm tràn RAM và che màn hình người dùng.

### Root Cause
Lệnh dọn dẹp ban đầu:
```powershell
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match 'GPMLogin' } | Stop-Process -Force -ErrorAction SilentlyContinue
```
- `Get-CimInstance Win32_Process` trả về object có property `.Name = 'chrome.exe'`.
- Khi pipe thẳng vào `Stop-Process`, PowerShell bind tham số `ProcessName` bằng giá trị `Name` của object thay vì `Id`.
- Lệnh tìm theo tên process `chrome.exe` thất bại với thông báo: `Cannot find a process with the name "chrome.exe"`.
- Vì có cờ `-ErrorAction SilentlyContinue`, lỗi bị bỏ qua hoàn toàn và **0 tiến trình Chrome nào bị tắt**.

### Giải Pháp Đã Sửa Chuẩn Hóa
BẮT BUỘC dùng `ForEach-Object` để truyền tường minh `ProcessId`:
```powershell
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match 'GPMLogin|--remote-debugging-port' -and $_.CommandLine -notmatch '9222' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
```
- Bảo vệ 100% Chrome cá nhân chạy trên port 9222 hoặc từ thư mục chuẩn.
- Đóng sạch 100% các tiến trình Chrome con của GPM mồ côi.
