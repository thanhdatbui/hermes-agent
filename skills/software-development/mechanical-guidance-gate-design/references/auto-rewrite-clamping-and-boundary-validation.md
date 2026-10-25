# Auto-Rewrite Clamping, Strict Boundary Validation & Closeout Remediation Loop

## 1. Bối Cảnh Thực Tế (Session Remediation Case Study)
Trong phiên nâng cấp các chốt chặn cơ học sang Guidance Gate:
- Hook `guard_read_file_size.py` được chuyển từ cấm thụ động (`block`) sang tự động nắn tham số (`rewrite`): nếu đọc file > 10MB mà không chỉ định slice hoặc limit > 2000, hook tự clamp về 200 dòng cuối (`offset=max(1, total_lines - 200 + 1)`, `limit=200`).
- Reviewer LLM độc lập (Sol Auditor qua Closeout Gate) chấm điểm ban đầu đạt **78/100 (REJECTED)** vì phát hiện các lỗ hổng biên:
  1. `isinstance(True, int) == True`: Ép kiểu `int(raw_offset)` chấp nhận boolean `True/False` thành `1/0`, để lọt các payload dị thường.
  2. Không kiểm tra cận dưới: Chỉ kiểm tra `limit <= 2000`, bỏ sót `offset <= 0` hoặc `limit <= 0`.
  3. Đếm dòng theo chunk: `chunk.count(b'\n')` bỏ sót dòng cuối cùng nếu file không có trailing newline.
  4. Test Evidence Deficit: File hook được sửa nhưng test file `test_guard_read_file_size.py` không được đưa vào danh mục thẩm định `--files`, khiến reviewer đánh giá thiếu bằng chứng kiểm thử thực tế.

## 2. Các Chuẩn Cơ Học Bắt Buộc

### 1. Strict Type Parsing vs Python Boolean Inheritance
Trong Python, `bool` là lớp con của `int` (`issubclass(bool, int) is True`). Mọi đoạn code kiểm tra tham số số nguyên bắt buộc phải loại bỏ boolean tường minh:
```python
def parse_int_strict(val):
    if val is None or isinstance(val, bool):
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
```

### 2. Dual-Boundary Positive Validation
Khi cho phép lệnh đọc file lớn đi qua (`sys.exit(0)`), bắt buộc phải thỏa mãn đồng thời:
- `offset >= 1`
- `1 <= limit <= 2000`
Bất kỳ giá trị nào <= 0, `None`, hoặc vượt ngưỡng an toàn đều phải tự động bị clamp về lát cắt an toàn 200 dòng cuối.

### 3. Last Chunk Newline Accounting
Khi đếm số dòng nhị phân trên file dung lượng lớn:
```python
total_lines = 0
last_byte = b""
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        total_lines += chunk.count(b"\n")
        if chunk:
            last_byte = chunk[-1:]
if last_byte and last_byte != b"\n":
    total_lines += 1
target_offset = max(1, total_lines - 200 + 1)
```

### 4. Closeout Remediation Loop & Scope Parity
- Khi Closeout Gate trả về `REJECTED (< 85)`:
  - Strike 1 & 2 Remediation: BẮT BUỘC Sol High (`sol_repair.py`) độc quyền đề xuất patch O(1).
  - Nếu `sol_repair.py` timeout (exit 124) hoặc lỗi, fallback sang Worker CLI / Claude CLI để vá.
  - Toàn bộ các file test bổ sung (`tests/test_*.py`) BẮT BUỘC phải được đưa vào danh mục `--files` của `closeout_gate.py`.
  - Reviewer ở Round 2+ sẽ freeze scope theo Anti-Moving Goalposts và thẩm định 100% bằng chứng kiểm thử tập trung để cấp Approved >= 85 (thực tế đạt 96/100).
