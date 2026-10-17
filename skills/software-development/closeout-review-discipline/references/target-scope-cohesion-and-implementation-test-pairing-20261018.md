# Target Scope Cohesion & Implementation-Test Pairing in Closeout Gate (18/10/2026)

## 1. Hiện Tượng & Cạm Bẫy Phân Rã Scope (The Test-Only Target Trap)
Khi chạy `closeout_gate.py` với cờ `--target-file` để thẩm định độc lập:
1. **Bẫy Reviewer phạt điểm khi chỉ truyền file Test:**
   - Nếu Coordinator chỉ truyền file test vào `--target-file` (ví dụ: `--target-file deploy/.../test_watchdog.py`), Sol Reviewer / OpenAI Reviewer sẽ chấm trượt (thường dao động 57–63 điểm) với nhận xét cố định:
     ```text
     "Diff chỉ bổ sung hoặc thay đổi test; không cung cấp phần triển khai... Vì vậy, không thể xác nhận đầy đủ logic triển khai hoặc khả năng chống regression từ bằng chứng hiện có."
     ```
   - Hậu quả: Dù toàn bộ test suite pass 100%, phiên vẫn bị REJECTED liên tiếp, dễ kích hoạt oan Strike 3 Reviewer Hand-off.

2. **Bẫy Lệch Trạng Thái Working Tree trong `targeted_candidate`:**
   - Trong `closeout_gate.py`, hàm `targeted_candidate` đối soát danh sách target với thay đổi thực tế:
     - Nếu một file đã lỡ commit trước đó (working tree sạch), còn file test đang dirty ở working tree, lệnh sẽ bị ném ngoại lệ:
       ```text
       ValueError: targets without working-tree changes: ['<file_da_commit>']
       ```
     - Nếu truyền `--base HEAD~N` khi giữa commit của task và HEAD có các commit tự động khác (như cron sync memory/skills), cổng sẽ từ chối:
       ```text
       refusing partial committed scope
       ```

---

## 2. Quy Chuẩn Kỹ Thuật Bắt Buộc (Mandatory Best Practices)

### A. Nguyên Tắc Cặp Đôi Đồng Bộ (Implementation-Test Pairing)
Mọi lượt chạy `closeout_gate.py` BẮT BUỘC phải truyền đồng thời cả file mã nguồn triển khai và file kiểm thử tương ứng:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo <repo> \
  --target-file <path_to_implementation.py> \
  --target-file <path_to_test.py> \
  --model review --json-output
```
- Reviewer cần thấy cả logic thực thi (defensive checks, error handling, helper functions) VÀ các assertion kiểm thử để chấm điểm trọn vẹn cho `logic_correctness`, `code_architecture` và `test_evidence` (đưa điểm từ 60 lên >= 80–85).

### B. Đồng Bộ Trạng Thái Đích Trước Khi Chạy Gate
Cả hai file trong cặp đôi target BẮT BUỘC phải ở cùng một trạng thái:
- **Trạng thái Working Tree:** Cả 2 file đều có uncommitted changes so với HEAD.
- **HOẶC Trạng thái Staged Index:** Cả 2 file đều được đưa vào git index:
  ```bash
  git add <path_to_implementation.py> <path_to_test.py>
  ```
  Khi có staged changes, `targeted_candidate` bóc tách trực tiếp staged diff (`git diff --cached`) sạch sẽ, bỏ qua hoàn toàn các commit sync chen ngang trong lịch sử.

### C. Kỷ Luật Mock Khi Viết Test Cho Helper I/O & Subprocess
1. **Kiểm tra mã thoát subprocess thật:**
   Trong các hàm gọi lệnh hệ thống (ví dụ: `attrib -u +p`, `adb`), luôn kiểm tra tường minh `if result.returncode != 0: return False` thay vì chỉ bọc `try...except`.
2. **Mock đúng namespace `builtins.open`:**
   Khi mã nguồn dùng `with open(...) as f:`, trong Python hàm `open` thuộc built-in namespace.
   Trong pytest, `monkeypatch.setattr(Path, 'open', ...)` sẽ KHÔNG chặn được lệnh `open(path, 'rb')`.
   BẮT BUỘC mock qua `builtins.open`:
   ```python
   import builtins
   monkeypatch.setattr(builtins, 'open', mock_failing_open)
   ```
