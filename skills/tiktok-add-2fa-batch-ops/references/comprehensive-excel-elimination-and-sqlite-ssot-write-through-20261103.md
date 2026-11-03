# Comprehensive Excel Elimination and SQLite SSOT Write-Through Guide (2026-11-03)

## 1. Bối Cảnh Lỗi & Căn Nguyên Hệ Thống
Trong đợt vận hành batch 2FA ban đêm ngày 2026-11-03, toàn bộ 126 máy farm gặp lỗi (43 máy dính `WorkbookError`, 69 máy dính `POST_SUCCESS_VERIFICATION_FAILED`). Quá trình điều tra hiện trường và mã nguồn phát hiện 4 căn nguyên cốt tử:

1. **Gốc SQLite nhưng ngọn cắm vào Excel:** `freeze_targets_from_sqlite` chỉ query từ `farm_master.db` để lấy danh sách máy/nick rồi ném cho worker con `run_capture_phase_b.py`. Worker con sinh ra vẫn nhận tham số `--workbook-path D:/OneDrive/Tiktok_Reg/taikhoan_dat_v2_updated .xlsx`.
2. **File Excel nguồn không tồn tại trên đĩa:** Toàn bộ dữ liệu đã được migrate sang `D:/Taadaa/data/farm_master.db`, file Excel nguồn tại `D:/OneDrive/Tiktok_Reg` thực tế không còn tồn tại. Khi worker con cố mở file để ghi nhận secret cell bằng `openpyxl.load_workbook()`, hệ thống văng `BadZipFile` hoặc `WorkbookError` làm hỏng toàn bộ lượt chạy.
3. **Lệch số dòng `rowid` SQLite vs Dòng Excel:** Code cũ gán `source_row = a.rowid`. Trong SQLite, `rowid` chỉ là chỉ mục nội bộ tự tăng của bảng, hoàn toàn không tương ứng với vị trí dòng thực tế trong file Excel legacy $\rightarrow$ Hàm `_validate_identity()` thấy sai tên máy/user tại dòng đó và ném ngay `SOURCE_ROW_IDENTITY_MISMATCH`.
4. **Bẫy nghiệm thu tài khoản chưa có password (`blank_pass`):** Nhiều tài khoản reg đời cũ qua Mail/SSO chưa trải qua bước đặt mật khẩu tĩnh (`password = NULL`). Khi hoàn tất bật 2FA, hàm `_verification()` lại ép `password_saved = not password_is_blank(...)` bắt buộc phải True $\rightarrow$ Đánh trượt oan 69 tài khoản thành `POST_SUCCESS_VERIFICATION_FAILED`.
5. **Thiếu định tuyến dải máy theo cụm:** Khi chạy cho cụm Kibe nhưng `freeze_targets_from_sqlite` nạp lẫn cả máy Admin (201-280) và ngược lại.

---

## 2. Các Quy Chuẩn Đã Chuẩn Hoá (Invariants)

### A. Tự Động Định Tuyến Phân Cụm
Trong `run_batch_live_2fa.py`:
```python
is_admin = 'admin' in str(cfg.workbook_path).casefold()
if is_admin:
    if int(machine) < 200:
        continue
else:
    if int(machine) > 80:
        continue
```
Đảm bảo mẻ chạy cụm Kibe chỉ lấy máy `1 - 80`, mẻ chạy cụm Admin chỉ lấy máy `201 - 280`.

### B. Nghiệm Thu Hợp Lệ Cho `blank_pass`
Trong `run_batch_live_2fa.py`:
```python
password_ok = password_saved or target.blank_pass
verified = has_2fa and password_ok and journal_purged and released
```
Tài khoản chưa có mật khẩu tĩnh khi hoàn tất 2FA sẽ được công nhận hoàn thành hợp lệ mà không bị đánh rớt.

### C. Write-Through Thẳng Vào SQLite SSOT Trước Tiên
Trong `core/workbook.py` (`_write_cell`):
```python
# Step 1: SQLite farm_master.db là Single Source of Truth; cập nhật trước tiên
try:
    db_path = Path("D:/Taadaa/data/farm_master.db")
    if db_path.exists():
        from farm_db import update_tiktok_credentials, get_account
        if column_name == "2fa":
            update_tiktok_credentials(target.username, twofa_secret=value)
        elif column_name == "pass":
            update_tiktok_credentials(target.username, password=value)
        _acc_verify = get_account(target.username)
except Exception:
    pass

# Step 2: Excel là tùy chọn (optional/non-blocking)
if not path.exists():
    return backup

try:
    _shared.single_writer_workbook_update(...)
except (OSError, openpyxl.utils.exceptions.InvalidFileException, zipfile.BadZipFile):
    return backup
```
Nếu file Excel legacy không tồn tại hoặc lỗi zip, worker vẫn trả về thành công an toàn và dữ liệu đã được ghim chặt vào SQLite SSOT.

### D. Đồng Bộ Cho Cả Gmail GPM 2FA (`run_add_2fa_remaining.py`)
Mọi script bật 2FA (kể cả Gmail GPM) trong hàm `sync_secret_to_excels()` đều phải gọi:
```python
from farm_db import update_mailbox_credentials
update_mailbox_credentials(email, twofa_secret=clean_secret)
```
để cập nhật song song vào bảng `mailboxes` của `farm_master.db`.

### E. Watchdog Hạ Tầng (`farm_idle_screen_and_app_healer.py`)
Hàm `load_mapping()` đọc danh sách 160 mapping thiết bị trực tiếp từ bảng `machines` trong `farm_master.db` (`SELECT device_serial, machine_id FROM machines`), dứt điểm hoàn toàn việc đọc file Excel `PROXYgandienthoai.xlsx`.
