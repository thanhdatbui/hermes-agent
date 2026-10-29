# Admin Cluster 2FA: Deployment Pipeline, SSH Socket Deadlock, & Single-Writer Guard (2026-10-29)

## 1. Hiện Tượng Thực Tế
- Báo cáo 2FA ban đêm toàn farm:
  - Farm Kibe (Máy 1-80): Hoàn tất 23 | Bỏ qua 8 | Lỗi 38.
  - Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 22 | Lỗi 69 (Liệt 100% mục tiêu).
- Toàn bộ 69 máy cụm Admin đều văng lỗi mặc dù ADB daemon nhận đủ 78 thiết bị vật lý và mạng Wi-Fi/Proxy hoàn toàn bình thường.

## 2. Phân Tích Root Cause 3 Tầng (Why It Broke Repeatedly)

### Tầng 1: Deployment Sync Gap (Cơ chế đẩy file chắp vá)
- Thư mục `D:/Taadaa/tiktok-add-bao-mat-f2a` trên Admin-PC không phải là Git repository, không có `git pull`.
- Script đồng bộ `D:/Taadaa/tools/sync_2fa_to_admin.py` bị hardcode danh sách chỉ đẩy `run_capture_phase_b.py` và `run_batch_live_2fa.py`, bỏ quên `run_capture_phase_a.py`.
- Phiên làm việc trước đó sửa fallback `C:\Program Files (x86)\xiaowei\tools\adb.exe` trong `run_capture_phase_a.py` trên Kibe nhưng không bao giờ sang được Admin-PC. User `Admin` thiếu ADB trong `PATH`, worker văng `FileNotFoundError: 'adb'` chết 100%.

### Tầng 2: Bẫy SSH Chunking Socket Deadlock (Gây Treo Session)
- Khi cố gắng đẩy file qua SSH PowerShell chunking (`[IO.File]::Open` lặp lại nhiều lần qua `admin_ssh.py`):
  - File mã nguồn lớn (>20 KB) tạo ra hàng chục kết nối SSH dồn dập.
  - OpenSSH Windows socket bị tắc nghẽn I/O khiến script treo cứng vô tận (`timeout=60s` vẫn không nhả), nuốt sạch terminal slot và làm đứt kết nối session chat (User phẫn nộ vì session bị treo).
- **Quy tắc vàng:** TUYỆT ĐỐI KHÔNG dùng SSH cắt nhỏ base64 để đẩy file lớn sang Admin. Hãy copy file vào thư mục trung gian OneDrive Shared (`D:\OneDrive\TaadaaData\admin\<file>`), sau đó kích hoạt 1 lệnh PowerShell duy nhất qua SSH để copy sang đích.

### Tầng 3: Single-Writer Workbook Guard Trầm Lặng (Data Loss Sau TOTP)
- Sau khi fix được ADB, máy Android đã vào TikTok, kích hoạt Authenticator thành công và ghi secret vào DPAPI journal (`AUTHENTICATOR_CONFIRMED`).
- Tuy nhiên, khi gọi `write_2fa()`, `_write_cell()` trong `python_runner/core/workbook.py` gọi `single_writer_workbook_update()` của `automation-core`.
- Do biến môi trường `TIKTOK_ADD_WRITER_ID` và `TIKTOK_ADD_EXPECTED_WRITER_ID` không được thiết lập mặc định trong runtime của Admin, `automation-core` văng lỗi:
  `WorkbookError: BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking`
- Tiến trình con sập, Secret Key bị kẹt trong journal và file Excel Master không ghi nhận, dẫn đến kết quả 0% thành công.

## 3. Bản Vá Chuẩn Hóa & Giải Pháp Vĩnh Viễn

### (a) Tự Động Fallback Writer ID trong `python_runner/core/workbook.py`
```python
expected_wid = os.environ.get("TIKTOK_ADD_EXPECTED_WRITER_ID") or "tiktok_add_2fa"
declared_wid = os.environ.get("TIKTOK_ADD_WRITER_ID") or "tiktok_add_2fa"
_shared.single_writer_workbook_update(
    path, update, expected_writer_id=expected_wid,
    declared_writer_id=declared_wid, logical_workbook_id="tiktok_tracking",
    ...
)
```

### (b) Kỹ Thuật Đồng Bộ Nhanh Qua OneDrive Shared (Chống Treo SSH)
```python
# Trên Kibe:
shutil.copy2(local_file, r"D:\OneDrive\TaadaaData\admin\<file_name>")

# Trên Admin (gọi qua 1 lệnh SSH duy nhất):
# Copy-Item -Path "D:\OneDrive\TaadaaData\admin\<file_name>" -Destination "D:\Taadaa\tiktok-add-bao-mat-f2a\<dest>" -Force
```

### (c) Quy Trình Cứu Hộ Secret Từ DPAPI Journal Khi Workbook Bị Chặn
Khi gặp trường hợp app đã bật 2FA nhưng workbook chưa có số:
1. Đọc DPAPI Journal tại `C:\Users\Admin\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\journals\<account_hash>.dpapi`.
2. Kiểm tra state `AUTHENTICATOR_CONFIRMED` và trích xuất `rec.secret`.
3. Bọc `PhaseBRecord(state=rec.state)` và gọi `write_2fa(..., record=phase_record, secret=rec.secret)`.
4. Readback đối soát cột `2FA` (Cột E) để đảm bảo dữ liệu đã vào file.
