# Safe Workbook Schema Extension: Cột thứ 5 "Ngày Tạo" & Date Parsing (2026-09-25)

## 1. Mục đích & Cấu trúc Safe Workbook mới
Safe workbook (`taikhoan_run_safe.xlsx` sinh bởi `scripts/sync-safe-workbook.py`) trước đây gồm 4 cột:
`("May", "Device ID", "ID", "Video Đã Đăng")`

Được mở rộng chuẩn hóa thêm cột thứ 5:
`OUTPUT_COLS = ("May", "Device ID", "ID", "Video Đã Đăng", "Ngày Tạo")`

Cột thứ 5 lưu trữ ngày tạo tài khoản dưới định dạng chuẩn ISO `YYYY-MM-DD` (hoặc rỗng nếu không có dữ liệu / slot trống).

---

## 2. Header Detection & Robust Date Parsing

### A. Header Detection
Trong file nguồn DAT (`taikhoan_dat_v2_updated .xlsx`), tên cột ngày tạo có thể biến thể. Nhận diện an toàn qua:
```python
date_col = _header_index(
    source_sheet,
    ("ngay tao", "ngày tạo", "created at", "created_at", "date created", "ngay"),
)
```

### B. Hàm parse đa định dạng `_parse_date_iso`
Hỗ trợ cả object `datetime/date` lẫn các chuỗi định dạng ISO, dấu gạch chéo `/`, giờ kèm theo, và định dạng ngày Việt Nam `DD/MM/YYYY`:
```python
def _parse_date_iso(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    if not s:
        return None
    # YYYY-MM-DD or YYYY/MM/DD (with optional time)
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            pass
    # DD/MM/YYYY or DD-MM-YYYY (with optional time)
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m:
        try:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            pass
    return None
```

---

## 3. Quy tắc Reopen Verify & Unit Tests Pitfall
- **Reopen Verify Gate**: Khi gọi `verify` trong `sync_safe_workbook`, TUYỆT ĐỐI KHÔNG hardcode `range(1, 5)`. Phải dùng:
  ```python
  headers = tuple(sheet.cell(1, column).value for column in range(1, len(OUTPUT_COLS) + 1))
  if headers != OUTPUT_COLS:
      raise RuntimeError("SAFE_WORKBOOK_REOPEN_VERIFY_FAILED_HEADERS")
  ```
- **Unit Tests Assertion**: Trong `python_runner/tests/test_sync_safe_workbook.py`, các dòng đọc từ `iter_rows(min_row=2, values_only=True)` trả về tuple 5 phần tử:
  `("75", EXTRA_MACHINES[75], "safe_75", 0, None)`
  Slot không có ngày tạo sẽ được openpyxl load lên thành `None` (hoặc `""` tùy chế độ đọc). Cần cập nhật đúng tuple length trong assertions.
