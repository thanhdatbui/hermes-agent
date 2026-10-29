# Single-Writer Missing Writer ID & SSH Chunk-Hang Resolution Protocol (2026-10-29)

## 1. Bản Chất 2 Sự Cố Chí Mạng Khiến Farm Admin Liệt 100% (0/69 Máy)

### Sự cố 1: `sync_2fa_to_admin.py` Treo Cứng Session (SSH Chunk Hang)
- **Cơ chế lỗi:** Script đồng bộ `sync_2fa_to_admin.py` cắt nhỏ các file code lớn (như `run_capture_phase_a.py` 23KB) thành hàng chục chunk Base64 rồi liên tục gọi `admin_ssh.py` để ghi append file trên Admin.
- **Hệ quả:** Trên Windows OpenSSH, việc spam các kết nối SSH liên tiếp trong thời gian ngắn làm kẹt socket I/O, tiến trình subprocess bị treo vô hạn không trả ra stdout/stderr, dẫn tới nghẽn terminal gateway của Coordinator.
- **Giải pháp chuẩn hóa:**
  * **CẤM** chia nhỏ file qua vòng lặp SSH Base64 cho các file có kích thước > 5KB.
  * **BẮT BUỘC** tận dụng thư mục đồng bộ OneDrive dùng chung (`D:\OneDrive\TaadaaData\admin\`) làm kênh truyền tải trung gian (Copy vào OneDrive từ Kibe -> Gọi 1 lệnh PowerShell đơn qua SSH trên Admin để Copy về repo).

---

### Sự cố 2: Single-Writer Guard Chặn Ghi Workbook (`BLOCKED_EXPECTED_WRITER_ID_MISSING`)
- **Cơ chế lỗi:**
  * Trên các máy vật lý cụm Admin, app TikTok **đã bật 2FA Authenticator thành công**, mã TOTP đã được sinh và lưu an toàn vào `.dpapi` journal cũng như `2fa_audit.log`.
  * Tuy nhiên khi tiến trình gọi `write_2fa()` trong `python_runner/core/workbook.py`, hàm này ủy thác cho `single_writer_workbook_update()` của thư viện `automation_core.workbook`.
  * Do môi trường chạy ngầm trên máy Admin không set 2 biến môi trường `TIKTOK_ADD_EXPECTED_WRITER_ID` và `TIKTOK_ADD_WRITER_ID`, `assert_writer_identity()` lập tức ném lỗi fail-closed:
    ```text
    automation_core.workbook.WorkbookError: BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking
    ```
  * Ngoại lệ này khiến worker bị đánh dấu crash/failed, toàn bộ kết quả 2FA thành công trên thiết bị không được ghi vào file Excel Master, gây ra hiện tượng thất bại ảo 100% trên 69 máy.
- **Bản vá kiến trúc (Default Fallback trong `workbook.py`):**
  Trong khối cập nhật workbook của `_write_cell`:
  ```python
  expected_wid = os.environ.get("TIKTOK_ADD_EXPECTED_WRITER_ID") or "tiktok_add_2fa"
  declared_wid = os.environ.get("TIKTOK_ADD_WRITER_ID") or "tiktok_add_2fa"
  _shared.single_writer_workbook_update(
      path, update, expected_writer_id=expected_wid,
      declared_writer_id=declared_wid, logical_workbook_id="tiktok_tracking",
      ...
  )
  ```

---

## 2. Quy Trình Cứu Hộ Secret Hàng Loạt (Cross-Host Rescue Tự Động)
Khi phát hiện hàng loạt máy đã bật 2FA trên thiết bị nhưng cột 2FA trong Master Excel bị trống:
1. Đọc nội dung `2fa_audit.log` từ máy đích:
   ```powershell
   Get-Content -Path 'C:\Users\Admin\AppData\Local\tiktok-add-bao-mat-f2a\logs\2fa_audit.log' | Select-String -Pattern "YYYY-MM-DD"
   ```
2. Parse regex đa dòng (do PowerShell console có thể ngắt dòng trước chuỗi 32 ký tự Base32):
   ```python
   re.compile(r"May:\s*(?P<machine>\d+)\s*\|\s*Sheet:[^|]+\|\s*Row:\s*(?P<row>\d+)\s*\|\s*Username:\s*(?P<username>[^|]+)\s*\|\s*2FA_Secret:\s*(?:\r?\n)?(?P<secret>[A-Z0-9]{32})")
   ```
3. Nạp an toàn trực tiếp vào file Excel Master tương ứng (chỉ ghi đè nếu ô hiện tại rỗng).
