# Khử Lỗi WorkbookError Triệt Để Khi Sang SQLite SSOT & Kỷ Luật Vận Hành Pipeline (2026-11-04)

## 1. Hiện Tượng & Dữ Liệu Thực Tế
Ca chạy 2FA ban đêm toàn farm gặp 111 lỗi, trong đó:
- Farm Kibe: 36 lỗi (chủ yếu `WorkbookError`)
- Farm Admin: 75 lỗi (100% `WorkbookError`)
- Báo cáo trace: `D:\Taadaa\reports\night_2fa_trace_2026-11-04.log`

## 2. Phân Tích Căn Nguyên Kỹ Thuật (Root Cause)

1. **Bẫy `acc.get("password")` Falsy Fall-Through:**
   - Trong `python_runner/core/workbook.py`, hai hàm `read_pass_value` và `read_email_value` có đoạn:
     ```python
     acc = get_account(target.username)
     if acc is not None and acc.get("password"):
         return str(acc["password"]).strip()
     # Fall-through mở openpyxl...
     ```
   - Trên Farm Admin (và các máy Kibe tạo nick qua Hotmail/SSO), tài khoản chưa từng đặt mật khẩu tĩnh (`password = NULL` hoặc `""`).
   - `acc.get("password")` trả về falsy $\rightarrow$ Script bỏ qua block `if` và rơi tự do (fall-through) xuống mở file Excel bằng `openpyxl`.
   - Hàm `_validate_identity()` dùng `target.source_row` (vốn là `a.rowid` từ SQLite `farm_master.db`) để soi vào dòng Excel tương ứng. Vì chỉ số dòng Excel khác với SQLite `rowid`, hàm ném ngay exception:
     `WorkbookError("SOURCE_ROW_IDENTITY_MISMATCH_USERNAME")`.

2. **Bẫy Nuốt Lỗi Toàn Cục vs Không Bắt `WorkbookError` Trong `_write_cell`:**
   - Nếu không bắt `WorkbookError` trong `_write_cell`, worker crash ngay sau khi đã bật 2FA thành công vì bước ghi Excel phụ bị lỗi lệch dòng.
   - Nếu nuốt `WorkbookError` mù quáng trong mọi trường hợp, các bài unit test kiểm tra ca chặn ghi đè bất hợp pháp (`test_identity_mismatch_is_blocked_and_original_unchanged`, `test_wrong_writer_identity_is_blocked`) sẽ bị fail toàn bộ (status `TEST_FAILED`).

## 3. Quy Chuẩn Sửa Đổi O(1) Đã Được Kiểm Chứng (Invariants)

1. **Khử Fall-through khi `acc is not None`:**
   ```python
   acc = get_account(target.username)
   if acc is not None:
       pwd = acc.get("password")
       return str(pwd).strip() if pwd else None
   ```
   Tương tự cho `read_email_value`.

2. **Bắt `WorkbookError` Có Điều Kiện Theo Cờ `sqlite_updated`:**
   ```python
   # Step 1: SQLite farm_master.db là SSOT; cập nhật trước
   sqlite_updated = False
   try:
       ...
       sqlite_updated = bool(get_account(target.username))
   except Exception:
       pass

   # Step 2: Excel là tùy chọn
   try:
       _shared.single_writer_workbook_update(...)
   except WorkbookError:
       if sqlite_updated:
           return backup
       raise
   except (OSError, openpyxl.utils.exceptions.InvalidFileException, zipfile.BadZipFile):
       return backup
   ```

3. **Kỷ Luật Unified Patch Pipeline (`--allow-no-test`):**
   - Khi sửa logic data layer backend đã có sẵn test suite đầy đủ và không cần thay đổi cấu trúc test, truyền `--allow-no-test` để vượt qua `MANDATORY_TEST_DELTA_VIOLATION`.
   - BẮT BUỘC chỉ định `--test-cmd "pytest python_runner/tests/test_workbook.py -q"` để S3 Verify kiểm chứng toàn bộ 17 test cases.
   - Bắt buộc đồng bộ file đã vá sang Farm Admin qua `tools/sync_2fa_to_admin.py` (`push_file`).
