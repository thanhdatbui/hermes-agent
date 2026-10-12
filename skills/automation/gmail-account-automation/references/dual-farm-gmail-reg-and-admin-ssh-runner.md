# Kiến Trúc Dual-Farm Reg Gmail & Điều Phối SSH Farm Admin

**Ngày cập nhật:** 2026-10-12  
**Chỉ thị từ Operator:** "Fix gọi luôn farm admin" (Mở rộng chuỗi Reg Gmail sau ca trưa sang toàn bộ cụm Farm Admin 201-280).

---

## 1. Nguyên Tắc Điều Phối Dual-Farm Cho Reg Gmail
- Trước đây Phase 1 (`run_gmail_batch`) chỉ kích hoạt cục bộ trên Farm Kibe (Máy 1-80).
- Chuỗi sau ca trưa (`post_noon_chain_watchdog.py`) hiện tại được nâng cấp để kích hoạt tuần tự/đối xứng cả 2 cụm:
  1. **Cụm Farm Kibe (Máy 1 - 80):** Chạy `run_all.ps1` cục bộ qua môi trường Python automation của Kibe.
  2. **Cụm Farm Admin (Máy 201 - 280):** Kích hoạt từ xa qua SSH sang host `admin-farm` bằng PowerShell EncodedCommand.

---

## 2. Chuẩn Hóa Biến Môi Trường Khi Kích Hoạt Qua SSH Admin Farm
- Khi gọi `run_all.ps1` trên `admin-farm`, bắt buộc inject tường minh các đường dẫn tài nguyên độc lập của Admin để tránh ô nhiễm chéo dữ liệu với Kibe:
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
- **Bẫy escape đường dẫn (CRITICAL PITFALL):**
  - Trong Python template string, chuỗi `.\run_all.ps1` có `\r` sẽ bị hiểu nhầm thành ký tự xuống dòng (Carriage Return `\r`), làm gãy lệnh PowerShell.
  - **Bắt buộc:** Luôn dùng forward slash `./run_all.ps1` hoặc escape double backslash `.\\run_all.ps1`.

---

## 3. Phân Biệt Mã Lỗi Runner (Exit Code Contract)
- **Exit Code 0:** Batch chạy thành công 100%.
- **Exit Code 1:** Batch chạy bình thường nhưng có một số máy thất bại do rào cản nền tảng (`phone_verify`, Google đòi SĐT). Trạng thái này được chấp nhận là hoàn tất ca (`gmail_ok = True`).
- **Exit Code 2 (RUNNER_ERROR / CRASH):** Lỗi ngoại lệ hệ thống, rớt kết nối SSH, timeout hoặc crash script:
  - Bắt buộc log có cấu trúc: `RUNNER_ERROR|KIBE|{exc_type}: {exc}` hoặc `RUNNER_ERROR|ADMIN|{exc_type}: {exc}`.
  - Phân tách rõ ràng với Exit Code 1 để không nuốt lỗi hạ tầng vào lỗi nền tảng.

---

## 4. Định Dạng Báo Cáo Đối Xứng Phase 1 & Phase 2
- Báo cáo gửi Telegram của watchdog chuẩn hóa đối xứng theo từng cụm farm:
  ```text
  - Phase 1 (Reg Gmail - Code 0):
    • Farm Kibe (Máy 1-80): Hoàn tất 5 máy | Bỏ qua 0 | Lỗi 10
    • Farm Admin (Máy 201-280): Hoàn tất 0 máy | Bỏ qua 0 | Lỗi 0

  - Phase 2 (Add 2FA TikTok - Code 4):
    • Farm Kibe (Máy 1-80): Hoàn tất 12 máy | Bỏ qua 10 | Lỗi 52
    • Farm Admin (Máy 201-280): Hoàn tất 0 máy | Bỏ qua 59 | Lỗi 21
  ```
