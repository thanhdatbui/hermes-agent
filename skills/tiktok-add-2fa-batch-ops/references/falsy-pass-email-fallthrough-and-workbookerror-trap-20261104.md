# Bẫy Falsy Fall-Through Khi Khử Excel Sang SQLite SSOT (2FA TikTok & Mailboxes)

## Hiện tượng (2026-11-04)
Báo cáo 2FA ban đêm toàn farm gặp lỗi hàng loạt:
- Farm Kibe: 36 lỗi (phần lớn `WorkbookError`)
- Farm Admin: 75 lỗi (100% `WorkbookError`)
- Tổng cộng 93 máy chết với lỗi `WorkbookError`.

## Nguyên nhân Kỹ thuật (Root Cause)

### 1. Bẫy `and acc.get("password")` gây rơi tự do (Fall-through) sang openpyxl
Trong `python_runner/core/workbook.py`:
```python
def read_pass_value(workbook_path: Path, target: WorkbookTarget) -> str | None:
    try:
        ...
        acc = get_account(target.username)
        if acc is not None and acc.get("password"):
            return str(acc["password"]).strip()
    except Exception:
        pass
    # Fall-through mở openpyxl và gọi _validate_identity(...)
```
- Trên Farm Admin (và các nick SSO/Hotmail Kibe), phần lớn tài khoản chưa từng đặt mật khẩu tĩnh (`password = NULL` hoặc `""`).
- `acc.get("password")` trả về falsy $\rightarrow$ Script tưởng rằng chưa đọc được từ SQLite nên rơi tự do (fall-through) xuống mở file Excel bằng `openpyxl`.
- Tại đây, hàm `_validate_identity(ws, target, ...)` dùng `target.source_row` (vốn là `a.rowid` từ SQLite) để soi vào dòng Excel. Vì `rowid` không trùng với dòng Excel, `_validate_identity` ném ngay `WorkbookError("SOURCE_ROW_IDENTITY_MISMATCH_USERNAME")`.
- Tương tự với `read_email_value`.

### 2. Bẫy không bọc `WorkbookError` trong `_write_cell`
Trong `_write_cell`:
```python
# Step 1: Update SQLite farm_master.db
# Step 2: Update Excel
try:
    _shared.single_writer_workbook_update(...)
except (OSError, openpyxl.utils.exceptions.InvalidFileException, zipfile.BadZipFile):
    return backup
```
- Khi `update()` chạy, `_validate_identity()` bị lệch dòng và ném `WorkbookError`.
- Vì `WorkbookError` không nằm trong danh sách exception được bắt, nó thoát ra ngoài làm crash toàn bộ worker con dù SQLite SSOT đã ghi nhận credentials thành công.

## Giải pháp Chuẩn hóa (Invariants)

1. **Khử fall-through khi `acc is not None`:**
   ```python
   acc = get_account(target.username)
   if acc is not None:
       pwd = acc.get("password")
       return str(pwd).strip() if pwd else None
   ```
   Nếu tài khoản đã có trong SQLite SSOT, dù password hay email rỗng, phải trả về `None` ngay lập tức, tuyệt đối không fall-through sang openpyxl.

2. **Non-blocking Excel write khi SQLite đã cập nhật:**
   ```python
   try:
       _shared.single_writer_workbook_update(...)
   except Exception:
       if sqlite_updated:
           return backup
       raise
   ```
   Nếu SQLite SSOT đã nhận credentials (`sqlite_updated = True`), mọi lỗi từ tầng Excel legacy (kể cả `WorkbookError` do lệch dòng) đều được bỏ qua an toàn và trả về backup.
