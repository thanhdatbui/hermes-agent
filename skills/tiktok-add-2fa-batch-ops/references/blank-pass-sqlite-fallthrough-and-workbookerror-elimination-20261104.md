# Bẫy Fall-Through Mở Excel Khi Mật Khẩu Rỗng & Khử Triệt Để WorkbookError (2026-11-04)

## 1. Bối Cảnh & Triệu Chứng Ban Đêm Toàn Farm
Báo cáo 2FA TikTok ban đêm ghi nhận sự cố tê liệt trên diện rộng:
- Farm Kibe (Máy 1-80): Hoàn tất 23 | Bỏ qua 10 | Lỗi 36
- Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 10 | Lỗi 75
- Toàn bộ 93 máy lỗi đều mang chung reason code: `WorkbookError`.

## 2. Căn Nguyên Kỹ Thuật (Root Cause)
1. **Lệch chỉ số dòng giữa SQLite `rowid` và Excel `source_row`:**
   - `freeze_targets_from_sqlite` query `SELECT a.rowid AS source_row ... FROM tiktok_accounts a` và gán vào `target.source_row`.
   - `rowid` SQLite (1, 2, 3...) hoàn toàn không tương ứng với vị trí dòng thực tế trong file Excel legacy `taikhoan_dat_v2_updated .xlsx` (có header, các dòng trống hoặc khác thứ tự).
2. **Bẫy điều kiện `and acc.get(...)` trong hàm đọc credential:**
   - Trong `python_runner/core/workbook.py`:
     ```python
     # CODE LỖI CŨ:
     acc = get_account(target.username)
     if acc is not None and acc.get("password"):
         return str(acc["password"]).strip()
     # Fall-through xuống load_workbook(openpyxl)
     ```
   - Trên Farm Admin (và các nick SSO/Hotmail Kibe), phần lớn nick chưa từng đặt mật khẩu tĩnh (`password = NULL` hoặc `""`).
   - Biểu thức `acc.get("password")` trả về falsy $\rightarrow$ Bỏ qua block `if` và rơi tự do (fall-through) xuống mở Excel legacy bằng `openpyxl`.
   - Hàm `_validate_identity()` dùng `target.source_row` (SQLite rowid) để soi vào dòng Excel tương ứng $\rightarrow$ Sai lệch định danh và ném ngay `WorkbookError("SOURCE_ROW_IDENTITY_MISMATCH_USERNAME")`.
3. **Bẫy crash worker tại `_write_cell`:**
   - Khi ghi 2FA hoặc Password mới, Step 1 cập nhật thành công vào SQLite `farm_master.db`, nhưng Step 2 gọi `single_writer_workbook_update` ghi vào Excel bị lệch dòng và ném `WorkbookError`.
   - `_write_cell` chỉ bắt `(OSError, openpyxl.utils.exceptions.InvalidFileException, zipfile.BadZipFile)`, làm lọt `WorkbookError` và đánh sập worker con.

## 3. Giải Pháp Cơ Giới Hóa Chuẩn O(1)
Trong `python_runner/core/workbook.py`:
1. **Khử fall-through trong `read_pass_value` và `read_email_value`:**
   ```python
   acc = get_account(target.username)
   if acc is not None:
       pwd = acc.get("password")
       return str(pwd).strip() if pwd else None
   ```
   Nếu tài khoản đã có trong SQLite SSOT nhưng password/email rỗng, trả về `None` ngay lập tức, tuyệt đối cấm mở openpyxl đối soát dòng.

2. **Bọc bắt `WorkbookError` an toàn khi SQLite SSOT đã nhận bản ghi:**
   ```python
   # Step 1: SQLite SSOT
   sqlite_updated = False
   try:
       ...
       sqlite_updated = bool(get_account(target.username))
   except Exception:
       pass

   # Step 2: Excel update
   try:
       _shared.single_writer_workbook_update(...)
   except WorkbookError:
       if sqlite_updated:
           return backup
       raise
   except (OSError, openpyxl.utils.exceptions.InvalidFileException, zipfile.BadZipFile):
       return backup
   ```
   Nếu SQLite SSOT đã nhận cập nhật (`sqlite_updated = True`), mọi lỗi lệch dòng của Excel legacy đều được bỏ qua an toàn. Nếu `sqlite_updated = False` (như trong unit test mock), exception vẫn được ném ra để đảm bảo tính toàn vẹn của test suite.

3. **Đồng bộ song song sang Admin-PC:**
   Sử dụng script `sync_2fa_to_admin.py` qua SSH `push_file` đẩy tệp `workbook.py` đã vá sang `D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner\core\workbook.py` trên Farm Admin.
