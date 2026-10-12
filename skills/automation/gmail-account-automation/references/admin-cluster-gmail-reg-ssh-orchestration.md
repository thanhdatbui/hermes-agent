# Tích Hợp Điều Phối Reg Gmail Đa Cụm (Kibe Máy 1-80 & Admin Máy 201-280)

**Ngày cập nhật:** 2026-10-12  
**Chỉ thị từ Operator:** "Fix gọi luôn farm admin"

---

## 1. Kiến Trúc Orchestration Đa Cụm (Dual-Farm Cluster Architecture)
- **Cụm Kibe (Máy 1 - 80):**
  - Chạy trực tiếp trên host cục bộ qua PowerShell runner `run_all.ps1`.
  - Inventory: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`.
  - Sổ cái đích: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
- **Cụm Admin (Máy 201 - 280):**
  - Điều phối từ xa từ Kibe qua SSH `admin-farm` bằng PowerShell `-EncodedCommand` (UTF-16LE Base64).
  - Tách biệt hoàn toàn môi trường và dữ liệu:
    + Cấu hình Proxy/Device: `$env:PROXY_DIENTHOAI_PATH = 'D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx'`.
    + Sổ cái đích: `$env:GMAIL_EXCEL_FILE = 'D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx'`.
    + Script run: `D:/Taadaa/register gmail/run_all.ps1`.
    + Python executable: `D:\Taadaa\python-envs\automation\Scripts\python.exe`.

---

## 2. Chuẩn Hóa Payload SSH EncodedCommand
- Tránh bẫy escape ký tự trong Python: Khi truyền chuỗi file path cho PowerShell, bắt buộc dùng forward slash `./run_all.ps1` hoặc double backslash `.\\run_all.ps1` để tránh ký tự `\r` bị parse thành Carriage Return (ASCII 13) làm đứt gãy lệnh.
- Mẫu payload chuẩn:
  ```powershell
  $env:PYTHONIOENCODING = 'utf-8'
  $env:PYTHONUTF8 = '1'
  Set-Location 'D:/Taadaa/register gmail'
  $env:PROXY_DIENTHOAI_PATH = 'D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx'
  $env:GMAIL_EXCEL_FILE = 'D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx'
  $env:PYTHONPATH = 'D:/Taadaa/register gmail;D:/Taadaa/automation-core/src'
  $env:GMAIL_REG_PYTHON_EXE = 'D:\Taadaa\python-envs\automation\Scripts\python.exe'
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ./run_all.ps1
  ```

---

## 3. Phân Tách Output & Telemetry Báo Cáo Đối Xứng
- Đầu ra của 2 cụm được đóng gói với marker định danh:
  + `=== CLUSTER KIBE (MÁY 1-80) ===`
  + `=== CLUSTER ADMIN (MÁY 201-280) ===`
- Sử dụng regex linh hoạt `re.search(r"===\s*CLUSTER\s+ADMIN\b", output, re.I)` để bóc tách an toàn thay vì split chuỗi thô.
- Format báo cáo Telegram chuẩn đối xứng giữa Phase 1 (Reg Gmail) và Phase 2 (TikTok 2FA):
  ```text
  - Phase 1 (Reg Gmail - Code 0):
    • Farm Kibe (Máy 1-80): Hoàn tất X máy | Bỏ qua Y | Lỗi Z
    • Farm Admin (Máy 201-280): Hoàn tất A máy | Bỏ qua B | Lỗi C
  ```

---

## 4. Quy Ước Mã Thoát (Exit Codes & Error Partitioning)
- `Exit Code 0`: Cả 2 cụm đều hoàn tất trọn vẹn (không có lỗi).
- `Exit Code 1`: Thực thi hoàn tất bình thường nhưng có một số máy fail nền tảng Google (`phone_verify`, `account_creation_error`). Vẫn xem là hợp lệ nếu `total > 0`.
- `Exit Code 2`: Runner crash, lỗi cú pháp, mất kết nối mạng hoặc SSH timeout (`RUNNER_ERROR|KIBE|...` hoặc `RUNNER_ERROR|ADMIN|...`). Watchdog ghi nhận `failed` vào state file để không nuốt lỗi hạ tầng.
