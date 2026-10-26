# Lifecycle Guard Null-Byte Handling & Coordinator T1 Temp-File Budget Isolation

## 1. Lifecycle Guard Null-Byte Exception on Windows (Python Script Parsing)

### Triệu chứng & Bản chất lỗi
Trong module `cron/lifecycle_guard.py` (hoặc các pre-execution inspection hooks):
Khi kiểm tra nội dung script shell hoặc dòng lệnh terminal:
```python
def _read_referenced_script(path: Path) -> tuple[Optional[str], bool]:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None, False
```
Trên Windows, khi `path` được parse từ các chuỗi inline phức tạp (`python -c "..."` có ký tự xuống dòng, escape hoặc unicode byte), hàm `os.open(path, ...)` sẽ ném ra `ValueError: open: embedded null character in path`.
Vì `ValueError` không phải là con của `OSError`, exception này văng ra ngoài phạm vi `try/except`, đánh sập toàn bộ tiến trình kiểm tra trước khi thực thi (Terminal Crash).

### Khắc phục chuẩn hóa O(1)
Mở rộng mệnh đề bắt exception:
```python
    try:
        descriptor = os.open(path, flags)
    except (OSError, ValueError):
        return None, False
```
Bất kỳ đường dẫn chứa null-byte hoặc định dạng path không hợp lệ đều được bỏ qua an toàn như một non-script target thay vì làm chết gateway/terminal.

---

## 2. Loại Trừ File Tạm Khỏi Ngân Sách T1 Của Coordinator (Temp-File Budget Bleed)

### Vấn đề gốc rễ
`coordinator_write_gate` giám sát ngân sách ghi mã nguồn của Coordinator:
- `COORD_T1_MAX_FILES` (ví dụ 10 files)
- `COORD_T1_MAX_LINES` (ví dụ 500 dòng cộng dồn)

Khi Coordinator thực hiện các tác vụ trích xuất ảnh, debug hiện trường, hoặc tạo bảng ảnh canvas tạm thời (lưu tại `D:/Taadaa/tmp/`, `reports/`, `tmp_*.py`), các file này nếu bị tính gộp vào `write_ledger["t1_files"]` sẽ nhanh chóng làm cạn sạch hạn mức T1. Hậu quả là Coordinator rơi vào trạng thái `[COORDINATOR WRITE DENIED]` và bị liệt toàn diện dù chưa hề sửa file production nào.

### Quy tắc phân loại vùng ghi (Target Scoping Invariant)
1. **Exempt Path Patterns:** Các file thuộc thư mục tạm hoặc file script dùng một lần:
   - `*/tmp/*`, `D:/Taadaa/tmp/*`
   - `tmp_*.py`, `temp_*.py`
   - `reports/*`
   -> **KHÔNG TÍNH** vào `write_ledger["t1_files"]` và `write_ledger["t1_lines"]`.
2. **Production Code Targets:** Chỉ các file mã nguồn cốt lõi (`tools/*.py`, `hooks/*.py`, `scripts/*.py`, production repos) mới ghi nhận vào ledger T1/L2.
3. **User Sudo Auto-Unblock:** Khi có grant hợp lệ từ `D:/Taadaa/runtime/sudo_grant.json` được kích hoạt bởi chỉ đạo trực tiếp của User (`"làm luôn"`, `"sửa đi"`, `"tao cho phép"`), `coordinator_write_gate` tự động bypass kiểm tra trần T1 và cho phép thực thi ngay trong 0 turn.
