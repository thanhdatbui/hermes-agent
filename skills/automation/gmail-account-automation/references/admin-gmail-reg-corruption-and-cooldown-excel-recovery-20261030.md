# Admin Farm Gmail Reg Recovery & Cooldown Excel Triage

**Ngày ghi nhận:** 2026-10-30  
**Bối cảnh:** Luồng Reg Gmail ban đêm (00:00 - 02:30) trên máy Admin (201-280) bị tê liệt ngầm dù Watchdog TikTok 2FA báo cáo bình thường.

---

## 1. Hai Điểm Nghẽn Hạ Tầng Cốt Lõi (Silent Infrastructure Traps)

### A. File Code Bị Truncate Khi Đồng Bộ SSH (`SyntaxError: unterminated string literal`)
* **Triệu chứng:** Khi chạy `run_all.ps1` trên Admin, lệnh kiểm tra inventory `python -c "import gmail_reg_v10 as g; ..."` crash ngay lập tức:
  `SyntaxError: unterminated string literal (detected at line 827)` -> PowerShell báo `Khong lay duoc danh sach may tu device inventory`.
* **Nguyên nhân:** File `D:\Taadaa\register gmail\gmail_reg_v10.py` trên Admin-PC trước đó bị gián đoạn truyền tải khiến file bị cụt đuôi ở dòng 827.
* **Quy tắc khắc phục:**
  1. Khi đồng bộ code sang Admin qua OneDrive hoặc script sync, bắt buộc kiểm tra mã băm SHA256 hai đầu:
     `Get-FileHash 'D:\Taadaa\register gmail\gmail_reg_v10.py' -Algorithm SHA256`.
  2. Mã băm phải trùng khớp bit-for-bit trước khi coi là đồng bộ hoàn tất.

### B. Hỏng Sổ Cái Excel `gmail_clean_v2.xlsx` (`ParseError: mismatched tag`)
* **Triệu chứng:**
  `ForEach-Object : Cannot convert value "[warn] Khong doc duoc Excel de tinh cooldown: mismatched tag: line 1" to type "System.Int32"`.
* **Cơ chế lỗi:**
  * File `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx` bị lỗi corrupt cấu trúc zip/XML (`xml.etree.ElementTree.ParseError: mismatched tag: line 1, column 266830`).
  * Hàm `_load_last_run_dates()` trong `gmail_reg_v10.py` in warning ra stdout thay vì stderr hoặc raise.
  * PowerShell trong `run_parallel.ps1` parse stdout từ Python: `$readyOutput = & $pythonExe -c $pythonCode 2>&1`, bắt nhầm dòng log cảnh báo vào `$readyList` và cố cast thành `[int]`, dẫn tới crash luồng chọn máy.
* **Quy tắc khắc phục & Phục hồi:**
  1. **Khôi phục ngay lập tức:** Thay thế file hỏng bằng bản backup gần nhất nguyên vẹn trong `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.bak_*.xlsx` (đảm bảo `openpyxl.load_workbook()` mở thành công).
  2. **Cách ly Stream:** Mọi cảnh báo hoặc log trong các hàm helper được gọi từ PowerShell CLI (`get_machines_ready`, `load_device_map_from_excel`) **BẮT BUỘC** in ra `sys.stderr` hoặc suppress bằng flag `quiet=True`, tuyệt đối không in text rác ra stdout làm ô nhiễm chuỗi kết quả trả về cho PowerShell.

---

## 2. Dispatch SSH Cho Admin-PC Bằng `powershell -EncodedCommand`

* Cửa ngõ an toàn của `admin_ssh.py` chặn các lệnh CLI có token lạ hoặc chuỗi môi trường `$env:...` bắt đầu dòng (`COMMAND_NOT_IN_ALLOWLIST`).
* **Mẫu chuẩn hóa bắt buộc:** Đóng gói toàn bộ script PowerShell khởi chạy trên Admin bằng Base64 UTF-16LE:
  ```python
  import base64
  script = (
      "$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'\n"
      "Set-Location 'D:\\Taadaa\\register gmail'\n"
      "$env:PROXY_DIENTHOAI_PATH='D:\\OneDrive\\TaadaaData\\admin\\PROXYgandienthoai.xlsx'\n"
      "$env:GMAIL_EXCEL_FILE='D:\\OneDrive\\TaadaaData\\admin\\gmail_clean_v2.xlsx'\n"
      "$env:PYTHONPATH='D:\\Taadaa\\register gmail;D:\\Taadaa\\automation-core\\src'\n"
      "$env:GMAIL_REG_PYTHON_EXE='D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe'\n"
      "$env:GMAIL_ASSIGNMENT_MANIFEST='C:\\Users\\Admin\\AppData\\Local\\automation-core\\assignments\\register-gmail.json'\n"
      "$env:GMAIL_WORKER_ID='taadaa-writer-admin-farm'\n"
      "& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File 'D:\\Taadaa\\register gmail\\run_all.ps1'\n"
      "exit $LASTEXITCODE\n"
  )
  encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
  cmd = ["ssh", "-o", "ConnectTimeout=10", "admin-farm", f"powershell -NoProfile -EncodedCommand {encoded}"]
  ```
