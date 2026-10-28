# GuardGate Invariant: Step-by-Step Structure & Test Diff Scope Trap

## 1. Bối Cảnh & Triệu Chứng
Khi chạy `closeout_gate.py` để thẩm định độc lập đóng phiên làm việc, pipeline bị GuardGate từ chối với lỗi:
```text
  ✘  [GuardGate DENY] Phat hien vi pham Invariant xuong mau!
[GuardEngine DENY] rule=case_invariant_require_step_by_step_structure
VIOLATION: predicate_failed:check_step_by_step_structure
HƯỚNG DẪN KIẾN TRÚC: Chia nhỏ logic và thêm comment định danh bước rõ ràng trước các khối logic chính.
```
Ngay cả sau khi Coordinator/Worker đã chia nhỏ hàm trong file code chính và thêm các comment `# Bước 1`, `# Bước 2`, `# Bước 3`, `# Bước 4`, gate vẫn tiếp tục DENY nếu trong diff có file khác vi phạm.

---

## 2. Cơ Chế Cơ Giới Hóa Của Predicate (`predicates.py`)
Trong `D:/Taadaa/tools/guardgate/predicates.py`:
```python
_STEP_MIN_CODE_LINES = 15
_STEP_COMMENT_RE = re.compile(r"#.*(buoc|bước|step|phase|stage|checkpoint)|#\s*={3,}", re.IGNORECASE)
_IMPORT_RE = re.compile(r"^(import\s|from\s+\S+\s+import\s)")
_TRIPLE_QUOTE_RE = re.compile(r'^[rRuUbBfF]{0,2}("""|\'\'\')')

def check_step_by_step_structure(action: Mapping[str, Any]) -> bool:
    diff = action.get("args", {}).get("diff", "")
    if not diff:
        return True

    for added in _added_python_lines_by_file(diff).values():
        code_lines = 0
        has_step_comment = False
        quote = ""
        for raw in added:
            # Bỏ qua import, comment, docstring...
            # Đếm code_lines thực tế
            if _STEP_COMMENT_RE.search(stripped):
                has_step_comment = True
            ...
            code_lines += 1
        if code_lines >= _STEP_MIN_CODE_LINES and not has_step_comment:
            return False

    return True
```

### Điểm Cốt Lõi:
1. **Ngưỡng kích hoạt:** $\ge 15$ dòng code thực tế (không tính comment, import, docstrings).
2. **Regex khớp comment bước:** Chứa từ khóa `buoc`, `bước`, `step`, `phase`, `stage`, `checkpoint` hoặc `# ===`.
3. **Phạm vi duyệt (Scope Trap):** Predicate duyệt qua **TẤT CẢ** các file Python trong diff (`_added_python_lines_by_file(diff)`). **KHÔNG CÓ NGOẠI LỆ CHO FILE TEST (`tests/test_*.py`)**.

---

## 3. Bẫy Thường Gặp (The Test File Blindspot)
- **Sai lầm phổ biến:** Điều phối viên hoặc Worker chỉ tập trung thêm comment `# Bước 1: ...` vào file triển khai chính (ví dụ `scripts/hermes_cron/tiktok_runner.py`), nhưng bỏ quên file unit test đi kèm (ví dụ `tests/test_tiktok_runner_healing.py`).
- **Hậu quả:** Một hàm unit test mới chuẩn bị mock dữ liệu, thiết lập monkeypatch, gọi hàm và assert thường dài 20–30 dòng code (`code_lines >= 15`). Khi file test không có comment bước, predicate duyệt tới file test và fail ngay lập tức, khiến AI tưởng nhầm là fix trong file chính chưa ăn và rơi vào vòng lặp sửa đi sửa lại file chính vô ích.

---

## 4. Quy Tắc Khắc Phục Chuẩn O(1)
1. **Kiểm tra toàn bộ diff:** Xem tất cả các file `.py` có trong `git diff HEAD~1` (hoặc `--files`).
2. **Áp dụng đồng bộ cả Code và Test:**
   - Trong file logic:
     - `# Bước 1: Đọc nguồn dữ liệu / workbook`
     - `# Bước 2: Xác định tham số và phân bổ tài nguyên`
     - `# Bước 3: Lọc danh sách thực thể hợp lệ`
     - `# Bước 4: Thực thi subprocess / API call`
   - Trong file unit test:
     - `# Bước 1: Chuẩn bị mock environment và mock inputs`
     - `# Bước 2: Thực thi hàm cần kiểm thử và kiểm tra assertions`
3. **Hậu kiểm cú pháp & test:** Luôn chạy focused test < 30s sau khi bổ sung comment trước khi commit và chạy lại Closeout Gate.
