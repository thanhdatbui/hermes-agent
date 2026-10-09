# Google Onboarding Multi-Step Dismissal & CIM Pipeline Cleanup Pitfall

## 1. PowerShell CIM Pipeline Bug — Lỗi `Stop-Process` Im Lặng (2026-09-05)

### Triệu chứng
Hàm dọn dẹp Chrome mồ côi (`kill_chrome_port`, `kill_orphaned_chrome`) được gọi trong khối `finally` nhưng các cửa sổ Chrome GPM vẫn mở nguyên vẹn trên màn hình và không bao giờ bị đóng, dẫn đến tích tụ hàng chục cửa sổ Chrome và hàng trăm tiến trình ngốn RAM/CPU.

### Nguyên nhân gốc (Root Cause)
Khi dùng câu lệnh:
```powershell
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match "$port" } | Stop-Process -Force -ErrorAction SilentlyContinue
```
1. `Get-CimInstance Win32_Process` trả về object kiểu `Microsoft.Management.Infrastructure.CimInstance` có thuộc tính `.Name = 'chrome.exe'`.
2. Cmdlet `Stop-Process` nhận 2 tham số chính từ pipeline theo tên thuộc tính (ValueFromPipelineByPropertyName):
   - `-Id <int[]>`
   - `-Name <string[]>`
3. Do object CIM có thuộc tính `.Name` chứa `'chrome.exe'` (có phần đuôi `.exe`), `Stop-Process` tự động bind vào tham số `-Name 'chrome.exe'`.
4. Trên Windows, `Stop-Process -Name` yêu cầu tên tiến trình **không có extension** (vd: `Stop-Process -Name chrome`), nên lệnh ném lỗi:
   `Cannot find a process with the name "chrome.exe"`.
5. Khi kết hợp với cờ `-ErrorAction SilentlyContinue`, PowerShell nuốt toàn bộ ngoại lệ trong im lặng, khiến **toàn bộ tiến trình không bao giờ bị dừng**.

### Cách khắc phục chuẩn
Bắt buộc dùng `ForEach-Object` để bind tường minh thuộc tính `ProcessId` vào tham số `-Id`:
```powershell
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { ($_.CommandLine -match 'GPMLogin' -or $_.CommandLine -match '--remote-debugging-port') -and ($_.CommandLine -notmatch '9222') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
```
Trong Python script:
```python
cmd = f'Get-CimInstance Win32_Process -Filter "Name = \'chrome.exe\'" | Where-Object {{ $_.CommandLine -match "{port}" }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}'
subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=10)
```

---

## 2. Luồng Xử Lý Lời Nhắc / Popup Onboarding Google Đa Bước Qua CDP (2026-09-05)

Khi tự động hóa đăng nhập hoặc xác minh tài khoản Google, Google thường chuyển tiếp qua chuỗi màn hình onboarding bảo mật:

### A. Màn hình 1: Account Recovery Options (`gds.google.com/web/recoveryoptions`)
- URL: `https://gds.google.com/web/recoveryoptions?cardIndex=0...`
- Nút bấm cần click: **"Huỷ"** (Lưu ý: Google render tiếng Việt Unicode với dấu hỏi kiểu `Huỷ`, aria-label `Huỷ`).
- Selector:
  ```python
  page.locator('button:has-text("Huỷ"), button:has-text("Hủy"), [aria-label*="Huỷ"]').first.click(force=True)
  ```
- Sau khi bấm "Huỷ", Google chuyển tiếp ngay sang màn hình số 2.

### B. Màn hình 2: Home Address Onboarding (`gds.google.com/web/homeaddress`)
- URL: `https://gds.google.com/web/homeaddress?cardIndex=1...`
- Nút bấm cần click: **"Bỏ qua"** (aria-label `Bỏ qua`).
- Selector:
  ```python
  page.locator('button:has-text("Bỏ qua"), [aria-label*="Bỏ qua"]').first.click(force=True)
  ```
- Sau khi bấm "Bỏ qua", Google chuyển tiếp về `https://myaccount.google.com/?utm_source=sign_in_no_continue&pli=1`.

### C. Màn hình 3: Banner Đề Xuất Tại Trang Chủ MyAccount (`myaccount.google.com`)
- Thường có thẻ banner gợi ý bảo mật/tính năng kèm nút **"Bỏ qua"**.
- Quét và click nút `button:has-text("Bỏ qua"), [role="button"]:has-text("Bỏ qua")`.

### D. Màn hình 4: 2-Step Verification Hoàn Tất (`signinoptions/twosv`)
- Dialog "You're now protected with 2-Step Verification" có các nút: **"Skip"** hoặc **"Done"** / **"Hoàn tất"**.
- Quét và click lần lượt `button:has-text("Skip")`, `button:has-text("Done")`, `button:has-text("Hoàn tất")`.
