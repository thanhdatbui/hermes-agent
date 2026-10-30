# Quy Trình Khởi Chạy & Vận Hành Reg Gmail Farm Admin (Máy 201-280)

**Ngày cập nhật:** 2026-10-30  
**Bối cảnh:** Xử lý sự cố cụm Farm Admin bị treo/ngắt kết nối trong ca ban đêm và bẫy báo cáo khống.

---

## 1. Cấm Tuyệt Đối Báo Cáo Hứa Hẹn (Anti-Phantom Reporting)
- **Tử huyệt:** Kết thúc turn bằng tin nhắn hứa hẹn ("Em đang chuẩn bị đẩy bản patch...", "Anh chờ em vài phút...") nhưng không kích hoạt tool trong cùng lượt.
- Do cơ chế vận hành turn-based, phiên sẽ dừng lại và đứng im hàng tiếng đồng hồ chờ tin nhắn tiếp theo của user, biến lời hứa thành báo cáo khống / bỏ trôi nhiệm vụ.
- **Kỷ luật bắt buộc:** 
  - Đã nói sửa/chạy thì **BẮT BUỘC** gọi tool thực thi ngay trong cùng turn (`terminal(background=True)` hoặc lệnh thực thi cụ thể).
  - Chỉ trả lời text sau khi đã có kết quả lệnh hoặc PID/session_id của background process thực sự đang chạy.

---

## 2. Các Rào Cản Kỹ Thuật Khi Dispatch Sang Admin-PC

### A. Rào cản Assignment Manifest & Worker Identity
- Khi gọi `run_all.ps1` trên Admin-PC, `run_parallel.ps1` bắt buộc kiểm tra `GMAIL_ASSIGNMENT_MANIFEST` và `GMAIL_WORKER_ID`.
- **Lỗi thường gặp:** Truyền `-workerId 'admin-farm'` sẽ bị `AssignmentManifest.assert_owner` từ chối vì owner_id trong `C:\Users\Admin\AppData\Local\automation-core\assignments\register-gmail.json` là:
  ```json
  "owner_id": "taadaa-writer-admin-farm"
  ```
- **Lệnh chuẩn hóa khi gọi SSH:**
  ```powershell
  $env:PYTHONIOENCODING = 'utf-8'
  $env:PYTHONUTF8 = '1'
  Set-Location 'D:\Taadaa\register gmail'
  $env:PROXY_DIENTHOAI_PATH = 'D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx'
  $env:GMAIL_EXCEL_FILE = 'D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx'
  $env:PYTHONPATH = 'D:/Taadaa/register gmail;D:/Taadaa/automation-core/src'
  $env:GMAIL_REG_PYTHON_EXE = 'D:\Taadaa\python-envs\automation\Scripts\python.exe'
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ./run_all.ps1 `
      -assignmentManifest 'C:\Users\Admin\AppData\Local\automation-core\assignments\register-gmail.json' `
      -workerId 'taadaa-writer-admin-farm'
  ```

### B. Cơ Chế Đồng Bộ Code Sạch (Base64 Chunking qua SSH)
- Không dùng `Copy-Item` qua OneDrive hay PowerShell string interpolation vì dễ bị lỗi OS error 22 / escape ký tự quote.
- Chia file thành các chunk Base64 (4000 ký tự) và ghi nhị phân bằng Python qua SSH:
  `python -c "import base64; open(r'D:\Taadaa\register gmail\gmail_reg_v10.py', 'ab').write(base64.b64decode('...'))"`
- Sau khi đồng bộ, bắt buộc kiểm tra mã băm SHA256 khớp 100% giữa Kibe và Admin trước khi kích hoạt chạy.

### C. Khôi Phục File Excel Sổ Cái Bị Lỗi Cấu Trúc XML
- Nếu `openpyxl` báo lỗi `ParseError: mismatched tag`, PowerShell sẽ bắt nhầm chuỗi warning vào danh sách máy và crash toàn bộ runner.
- Khi gặp lỗi này, lập tức khôi phục từ bản backup `.bak_*.xlsx` sạch gần nhất, kiểm tra `openpyxl.load_workbook()` đọc được sheet `Gmail Accounts` và `max_row` hợp lệ.
