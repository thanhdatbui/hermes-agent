# Subfolder Scoped Search vs Root Guard Boundary & Guidance Quality Invariant

## 1. Bối cảnh & Vấn đề Cốt lõi
Trong các phiên giám sát tuân thủ farm 6h (`gate_compliance_watchdog.py`), Operator thường xuyên thấy Gate G7 (*Anti-Scan & Terminal Guard*) nổ liên tiếp các vi phạm:
- `GUARD_SEARCH_FILES_ROOT`
- `GUARD_RECURSIVE_GREP`
- `GUARD_FIND_SCAN`
- `GUARD_DANGEROUS_ROOT`

### Nguyên nhân gốc rễ:
1. **Lỗi Boundary So Khớp Chuỗi Trơ Trọi (`root in norm`)**:
   Hook bảo vệ `guard_broad_grep.py` dùng kiểm tra `root in norm` với các root nguy hiểm (như `D:/Taadaa`, `D:/`). Hậu quả: Mọi thư mục con hợp lệ của dự án (như `D:/Taadaa/tools`, `D:/Taadaa/orders`, `D:/Taadaa/tiktok-follow`) đều bị đối xử như quét root diện rộng và bị **BLOCK** thẳng tay.
2. **Nghịch Lý Guidance & Chỉ Dẫn Mù**:
   - Hook chặn `search_files` và nhả hướng dẫn: *"Scope vào thư mục con cụ thể vd D:/Taadaa/tools"*, nhưng khi Agent scope đúng `D:/Taadaa/tools` thì chính Hook lại tiếp tục BLOCK!
   - Regex nhận diện `FARM_TERM` bị bắt dính các từ phổ thông (`log`, `logs`, `farm`, `machine`) trong các câu lệnh tìm code, khiến guidance tự động gắn thêm câu thừa vô nghĩa: `DÙNG LỆNH O(1): python D:/Taadaa/tools/inspect_machine.py <N>...`. Agent tìm file code nhưng bị xúi đi soi thiết bị Android.
3. **Hiệu Ứng Domino Bế Tắc (Spiral of Blind Retries)**:
   Agent bị chặn ở `search_files` $\to$ thử dùng bash `grep -rn` $\to$ bị chặn tiếp `GUARD_RECURSIVE_GREP` $\to$ thử dùng `find` $\to$ bị chặn `GUARD_FIND_SCAN` $\to$ quá bí, liều mình viết inline Python `os.walk` $\to$ bị chặn `GUARD_DANGEROUS_ROOT`. Càng thử càng sinh bão vi phạm trên watchdog.

---

## 2. Invariants Kiến Trúc Bảo Vệ & Dẫn Đường Cơ Giới

### Invariant 1: Path Boundary Regex cho Protected Roots
Khi kiểm tra root nguy hiểm, BẮT BUỘC dùng regex biên giới ký tự đường dẫn thay vì kiểm tra chuỗi `in`:
```python
pattern = rf"(?<![\w.-]){re.escape(root)}(?:/|\\)?(?=[\s\"'`;|)&$]|$)"
if re.search(pattern, norm):
    return True
```
- Cho phép: `D:/Taadaa/tools`, `D:/Taadaa/orders`, `D:/Taadaa/tiktok-*`
- Chặn đúng mục tiêu: `D:/`, `D:/Taadaa`, `D:/Taadaa/Hermes`, `D:/CodexRuntime` (khi đứng độc lập làm target hoặc sau khoảng trắng/ngắt lệnh).

### Invariant 2: Tách Biệt Scope Của `search_files`
- `search_files` tìm kiếm nội dung (`target="content"`) chỉ chặn khi `path` rơi vào **Exact Dangerous Roots**:
  ```python
  exact_dangerous_roots = {
      "d:", "d:/", "d:/taadaa", "d:/taadaa/hermes", "d:/codexruntime",
      "c:", "c:/", "c:/users/kibe", "/", "", "."
  }
  ```
- Nếu `path` trỏ vào một thư mục con cụ thể của dự án $\to$ **ALLOW ngay lập tức**.

### Invariant 3: Farm Hint Phải Kèm Định Danh Máy Cụ Thể
- Regex `FARM_TERM` chỉ được kích hoạt khi câu lệnh/target thực sự chứa ID máy hoặc điện thoại:
  ```python
  FARM_TERM = re.compile(r"\b(?:machine\s*\d+|phone\s*\d+|m\d{1,3})\b", re.I)
  ```
- TUYỆT ĐỐI CẤM gắn hint `inspect_machine.py` vào các lệnh tìm kiếm code hoặc script thuần túy.

### Invariant 4: Guidance Tìm Kiếm File Hướng Về O(1)
Khi chặn `GUARD_FIND_SCAN` hoặc `GUARD_SEARCH_FILES_ROOT`, hướng dẫn hành động phải chuẩn xác:
- Tìm theo tên file: Dùng `search_files(target='files', pattern='*.py')` hoặc `git ls-files "<pattern>"`.
- Tìm theo nội dung: Dùng `search_files(path='D:/Taadaa/tools', pattern='...')` với subfolder cụ thể hoặc grep trên 1 file đơn lẻ.
