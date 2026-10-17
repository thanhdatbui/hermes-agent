# OneDrive Files On-Demand Dehydration Errno 22 Preflight Hydration (18/10/2026)

## 1. Hiện Tượng & Mã Lỗi
Khi chạy tiến trình batch 2FA ban đêm (`cron_night_tiktok_2fa_watchdog.py`), Cluster Admin (máy 201-280) bị sập ngay lập tức với mã lỗi 5:
`{"status": "blocked", "reason": "[Errno 22] Invalid argument: 'D:\\OneDrive\\TaadaaData\\admin\\taikhoan_dat_v2_updated .xlsx'"}`

## 2. Phân Tích Nguyên Nhân (Root Cause)
File workbook nằm trên thư mục OneDrive được đồng bộ hóa với cơ chế Files On-Demand.
Khi Windows tự động chuyển file sang trạng thái offline stub (`FILE_ATTRIBUTE_OFFLINE` / `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`, cờ `attrib A O`), file chỉ là con trỏ metadata 0-byte thực trên đĩa.
Khi tiến trình Python `openpyxl` mở file này trong một phiên headless SSH hoặc tiến trình nền, hệ điều hành Windows không tự động trigger tải nội dung file về mà trả ngay lỗi hệ thống `[Errno 22] Invalid argument`.

## 3. Quy Trình Khắc Phục (Preflight Hydration Protocol)

### A. Lệnh Cưỡng Chế Hydrate Cục Bộ Trên Windows (PowerShell / CMD)
Trước khi gọi Python mở workbook trên máy cục bộ hoặc remote Admin qua SSH:
1. Gỡ cờ offline và ghim trạng thái luôn sẵn sàng trên thiết bị:
   `attrib -u +p <đường_dẫn_workbook>`
2. Kích hoạt I/O đọc thật để ép Windows hoàn tất việc tải dữ liệu:
   - Trong PowerShell:
     `try { [System.IO.File]::ReadAllBytes($wb) | Out-Null } catch {}`
   - Trong Python:
     ```python
     with open(workbook_path, "rb") as f:
         f.read(10)
     ```
3. Sau bước trên, thuộc tính file chuyển từ `attrib A O` sang `attrib A P` và Python openpyxl có thể đọc ghi workbook bình thường.

### B. Mẫu Tích Hợp Chuẩn Trong Remote SSH Runner
```python
ps_admin_script = (
    "$env:PYTHONIOENCODING = 'utf-8'\n"
    "$env:PYTHONUTF8 = '1'\n"
    f"Set-Location '{_ps_quote(ADMIN_REPO_DIR)}'\n"
    f"$wb = '{_ps_quote(ADMIN_WORKBOOK)}'\n"
    "attrib -u +p $wb\n"
    "try { [System.IO.File]::ReadAllBytes($wb) | Out-Null } catch {}\n"
    f"& '{_ps_quote(ADMIN_PYTHON)}' python_runner/run_batch_live_2fa.py "
    "--workbook-path $wb --workbook-sheet 'Tài Khoản' --max-workers 15 --live\n"
    "exit $LASTEXITCODE\n"
)
```
