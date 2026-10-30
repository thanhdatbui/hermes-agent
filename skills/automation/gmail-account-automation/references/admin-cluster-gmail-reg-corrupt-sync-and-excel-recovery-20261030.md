# Admin Farm Gmail Reg Recovery: Truncated Script & Corrupt Excel XML (30/10/2026)

## 1. Hiện Tượng & Triệu Chứng
- Watchdog Reg Gmail ban đêm chỉ ghi nhận và chạy máy Farm Kibe (1-80), Farm Admin (201-280) hoàn toàn không phát sinh lượt chạy.
- Sổ cái Admin `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx` không thay đổi ngày cập nhật.
- Không có lỗi hiển thị rõ ràng trên báo cáo tổng hợp do lỗi xảy ra trước khi sinh `summary.json`.

## 2. Hai Nguyên Nhân Gốc Rễ (Dual Root-Causes)

### A. File code `gmail_reg_v10.py` trên Admin-PC bị đứt ngang (Truncated Sync)
- Do quá trình đồng bộ qua mạng/SSH trước đó bị timeout hoặc ngắt giữa chừng, file `D:\Taadaa\register gmail\gmail_reg_v10.py` trên Admin-PC bị cắt cụt ở dòng ~827.
- **Biểu hiện:** Khi `run_all.ps1` gọi Python đọc inventory thiết bị:
  ```text
  File "D:\Taadaa\register gmail\gmail_reg_v10.py", line 827
      raise RuntimeError(f"[DEVICE_STATE][STARTUP] {stop_r
                                                         ^
  SyntaxError: unterminated string literal (detected at line 827)
  ```
  Dẫn đến `Khong lay duoc danh sach may tu device inventory` và thoát ngay lập tức với exit code 1.

### B. File Excel sổ cái Admin `gmail_clean_v2.xlsx` bị lỗi cấu trúc XML (ParseError)
- File `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx` bị ghi đè dở dang hoặc lỗi sync OneDrive làm hỏng stream nén:
  `xml.etree.ElementTree.ParseError: mismatched tag: line 1, column 266830`
- Trong `run_parallel.ps1`, đoạn code lấy danh sách máy đủ cooldown dùng `2>&1`:
  `$readyOutput = & $pythonExe -c $pythonCode 2>&1`
- Khi `openpyxl` văng lỗi, hàm `_load_last_run_dates()` in ra warning:
  `[08:14:44] [warn] Khong doc duoc Excel de tinh cooldown: mismatched tag: line 1`
- Warning này bị nuốt vào `$readyOutput`, khiến lệnh PowerShell `ForEach-Object { [int]$_.Trim() }` crash do không ép kiểu chuỗi văn bản warning sang số nguyên được.

## 3. Quy Trình Khắc Phục Chuẩn Hóa

### Bước 1: Khôi phục file Excel sổ cái từ Backup sạch
- Kiểm tra file backup mới nhất còn nguyên vẹn trong thư mục:
  `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.bak_*.xlsx`
- Dùng Python `openpyxl.load_workbook(path)` test thử toàn bộ các sheet.
- Khi xác nhận backup sạch (`rows > 600`), sao lưu file hỏng và ghi đè backup vào `gmail_clean_v2.xlsx`.
- Đồng bộ qua OneDrive và hydrate trên Admin-PC bằng PowerShell `Get-Content -TotalCount 5`.

### Bước 2: Đồng bộ bit-for-bit `gmail_reg_v10.py` sang Admin-PC
1. Copy file sạch từ Kibe vào thư mục OneDrive Admin:
   `shutil.copy2('D:/Taadaa/register gmail/gmail_reg_v10.py', 'D:/OneDrive/TaadaaData/admin/gmail_reg_v10.py')`
2. Kích hoạt hydrate trên Admin-PC qua SSH:
   `Get-Content 'D:\OneDrive\TaadaaData\admin\gmail_reg_v10.py' -TotalCount 5`
3. Trên Admin-PC, dùng Python `shutil.copy2` sao chép sang `D:\Taadaa\register gmail\gmail_reg_v10.py`:
   `python -c "import shutil; shutil.copy2('D:/OneDrive/TaadaaData/admin/gmail_reg_v10.py', 'D:/Taadaa/register gmail/gmail_reg_v10.py')"`
4. **Bắt buộc đối soát SHA256:**
   `Get-FileHash 'D:\Taadaa\register gmail\gmail_reg_v10.py' -Algorithm SHA256`
   Khớp 100% với hash trên Kibe mới được nghiệm thu.

### Bước 3: Xác minh khởi chạy
Chạy thử nghiệm lệnh với `maxMachines = 1`:
```powershell
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File 'D:\Taadaa\register gmail\run_all.ps1' -cooldownDays 5 -maxMachines 1
```
Xác nhận log nhận đủ `80/80` máy (201-280), tạo thư mục `logs_parallel_*` và bắt đầu launch máy thành công.
