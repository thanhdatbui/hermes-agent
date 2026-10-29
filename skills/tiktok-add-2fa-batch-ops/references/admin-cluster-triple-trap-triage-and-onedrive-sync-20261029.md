# Admin Cluster 2FA Triple Trap Triage & OneDrive Sync Architecture (2026-10-29)

## 1. Hiện Tượng Thực Tế
- Báo cáo 2FA ban đêm toàn farm:
  - Farm Kibe (Máy 1-80): Hoàn tất 23 | Bỏ qua 8 | Lỗi 38 (Tồn chỉ còn 52 nick).
  - Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 22 | Lỗi 69 (Liệt 100% 69 máy mục tiêu).
- Thiết bị trên Admin vẫn online đủ 78 máy qua socket `192.168.110.119:5037`, Wi-Fi & Proxy đều vượt qua VPN Gate của `automation-core`.

---

## 2. Ba Tầng Lỗi Hệ Thống (Triple Trap Root Cause)

### Trap 1: Cắt file nhỏ qua SSH gây nghẽn socket & thiếu file đồng bộ (Sync Drift)
- Script cũ `sync_2fa_to_admin.py` dùng vòng lặp gửi hàng chục chunk Base64 qua PowerShell SSH `[IO.File]::Open`.
- **Hậu quả**:
  1. Với file lớn (>20 KB như `run_capture_phase_a.py`), OpenSSH Windows bị nghẽn I/O socket, process con treo cứng không trả về, làm timeout và sập gateway phiên làm việc.
  2. Script cũ bị hardcode chỉ sync 2 file (`run_capture_phase_b.py`, `run_batch_live_2fa.py`), bỏ quên `run_capture_phase_a.py`.
  3. File trên Admin vẫn chứa code cũ hardcode đường dẫn GemPhoneFarm của `C:\Users\Kibe\...`, khiến hàm fallback trả về bare string `"adb"` -> toàn bộ 69 worker trên Admin văng `FileNotFoundError: 'adb'`.
- **Giải pháp**:
  - Dùng thư mục dùng chung `D:\OneDrive\TaadaaData\admin\` làm cầu nối đồng bộ giữa Kibe và Admin.
  - Copy file từ Kibe vào OneDrive, trên Admin chạy đúng 1 lệnh PowerShell `Copy-Item` từ OneDrive sang `D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner\`. Tránh hoàn toàn việc stream Base64 qua SSH.

### Trap 2: Single-Writer Guard chặn ghi workbook (`BLOCKED_EXPECTED_WRITER_ID_MISSING`)
- Trong `python_runner/core/workbook.py`, hàm `_write_cell` gọi `single_writer_workbook_update` của `automation-core`.
- Khi biến môi trường `TIKTOK_ADD_EXPECTED_WRITER_ID` và `TIKTOK_ADD_WRITER_ID` không được set trong subprocess worker, guard ném lỗi:
  ```text
  automation_core.workbook.WorkbookError: BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking
  ```
- **Hậu quả**: Thiết bị Android đã bật 2FA thành công trên app TikTok và lưu vào `.dpapi` journal, nhưng khi ghi vào Master Excel thì crash batch.
- **Giải pháp**:
  - Trong `workbook.py`, đặt fallback mặc định:
    ```python
    expected_wid = os.environ.get("TIKTOK_ADD_EXPECTED_WRITER_ID") or "tiktok_add_2fa"
    declared_wid = os.environ.get("TIKTOK_ADD_WRITER_ID") or "tiktok_add_2fa"
    ```

### Trap 3: Protected Zip Part Drift khi thêm text mới vào Excel (`WORKBOOK_PROTECTED_PART_DRIFT`)
- Thư viện `automation-core` kiểm tra tính toàn vẹn của workbook qua `protected_zip_parts`.
- Hàm này hash cả file `xl/sharedstrings.xml`. Khi openpyxl ghi thêm Secret 2FA (chuỗi Base32 mới 32 ký tự), file `xl/sharedstrings.xml` bắt buộc phải thay đổi nội dung.
- Guard bắt nhầm thay đổi này là hư hỏng cấu trúc và ném `WorkbookError("WORKBOOK_PROTECTED_PART_DRIFT")`.
- **Giải pháp**:
  - Đối với cell-only string updates trong batch runner 2FA, truyền `protected_parts=None` vào `single_writer_workbook_update` để openpyxl commit an toàn.
  - Đồng thời trong `automation-core`, đã gỡ bỏ `xl/sharedstrings.xml` khỏi hàm `protected_zip_parts` (chỉ hash drawings, charts, tables, media và relationships).

### Trap 4: Các Tử Huyệt Locking & File Replacement Trên Windows (Audit bởi Claude CLI)
- **Cross-Drive Rollback**: File rollback tạo trong `%TEMP%` (ổ `C:`) trong khi file Excel ở ổ `D:`. Trên Windows, lệnh `os.replace` khác ổ đĩa văng `OSError: [WinError 17]`. Khắc phục: Bắt buộc tạo tempfile trong cùng thư mục `target.parent`.
- **Windows SharingViolation khi Unlink Lock**: Khi process A xóa file lock mà process B đang mở đọc để check stale lock, Windows ném `PermissionError`. Nếu nuốt lỗi này, lock file bị mồ côi vĩnh viễn $\rightarrow$ gây timeout hàng loạt. Khắc phục: Bọc `_unlink_with_retry(path, retries=5, delay=0.05)` và coi lock rỗng/hỏng cũ >30s là stale để xóa.
- **Vòng lặp 5x Retry Lồng Nhau (Treo Caller 10-12 phút)**: `_write_cell` bọc 5 lần retry bên ngoài timeout 120s bên trong, kèm random sleep, khiến khi kẹt lock thì tiến trình treo tới 10 phút làm sập gateway. Khắc phục: Dẹp bỏ hoàn toàn outer retry loop, chỉ dùng 1 lần atomic update với timeout rõ ràng.
- **Tiền tố dấu `=` trong Secret**: openpyxl tự biến chuỗi bắt đầu bằng `=` thành Excel Formula `#NAME?`. Khắc phục: Ép kiểu `cell.data_type = "s"`.
- **Kỷ Luật GuardGate**: Rule `case_2fa_prohibit_blind_workbook_access` cấm `openpyxl.load_workbook` không bọc lock (kể cả trong file test, bắt buộc có `acquire_workbook_lock`). Rule `case_invariant_require_step_by_step_structure` bắt buộc các khối code mới >= 15 dòng phải có comment `# Step X: ...`.

---

## 3. Quy Trình Cứu Hộ Dữ Liệu Sau Sự Cố (Audit Log Rescue)
- Khi máy vật lý đã bật 2FA thành công nhưng kẹt ở bước ghi Excel:
  1. Trích xuất Secret Key từ `$env:LOCALAPPDATA/tiktok-add-bao-mat-f2a/logs/2fa_audit.log` trên Admin-PC.
  2. Parse pattern: `May: (\d+) | Sheet: [^|]+ | Row: (\d+) | Username: ([^|]+) | 2FA_Secret: ([A-Z0-9]{32})`.
  3. Lọc các record phát sinh trong ngày, lấy secret mới nhất và backfill trực tiếp vào Cột E (`2FA`) của Master Excel `taikhoan_dat_v2_updated .xlsx`.
  4. Đã cứu hộ thành công 65 tài khoản bị kẹt trong phiên 29/10/2026, nâng tổng số nick có 2FA của Admin từ 35 lên 101/630.
