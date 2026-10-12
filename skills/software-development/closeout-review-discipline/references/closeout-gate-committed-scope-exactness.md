# Closeout Gate Committed Scope Exactness (`committed_targeted` Invariant)

Hướng dẫn xử lý lỗi từ chối đánh giá phạm vi commit từng phần (`refusing partial committed scope`) khi chạy `closeout_gate.py`.

---

## 1. Hiện tượng & Lỗi phát sinh
Khi chạy `closeout_gate.py` với cờ `--files` trên các thay đổi đã được commit vào git:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/tools" --base 649341f --files audit_stale_upload_accounts.py tests/test_audit_stale_upload_accounts.py --json-output
```
Gate báo lỗi:
```text
✘ Failed to extract diff: committed 649341f..HEAD scope ['audit_stale_upload_accounts.py', 'do_logout_account.py', 'tests/test_audit_stale_upload_accounts.py'] != --files targets ['audit_stale_upload_accounts.py', 'tests/test_audit_stale_upload_accounts.py']; refusing partial committed scope
```

---

## 2. Bản chất Cơ chế Kiểm soát trong `closeout_gate.py`
Trong hàm `targeted_candidate` (dòng 429-440 của `closeout_gate.py`):
1. **Chế độ `worktree_targeted` (Ưu tiên 1):** Khi các target files có thay đổi chưa commit trong working-tree (`git diff HEAD`). Khi đó `--files` có thể nhận danh sách file hẹp hơn toàn bộ repo.
2. **Chế độ `committed_targeted` (Ưu tiên 2):** Khi các target files **đã được commit** (không còn dirty diff trong working tree so với HEAD). Khi đó, `closeout_gate.py` tính toán `committed_scope` giữa `--base` và `HEAD`:
   ```python
   diff_range, committed_scope_list = _committed_scope(repo, base_ref)
   committed_scope = set(committed_scope_list)
   if set(targets) == committed_scope and diff_range is not None:
       return "committed_targeted", targets, ...
   if set(targets) & committed_scope:
       raise ValueError(f"committed {scope_label} scope {sorted(committed_scope)} != --files targets {targets}; refusing partial committed scope")
   ```
3. **Quy tắc Bất biến:** Trong chế độ `committed_targeted`, tập hợp các file được truyền qua `--files` **BẮT BUỘC PHẢI KHỚP TUYỆT ĐỐI 100%** với danh sách các file đã thay đổi giữa `--base` và `HEAD` (`set(targets) == committed_scope`). Gate từ chối duyệt một phần (partial scope) của commit range để ngăn chặn việc giấu diếm diff ngoài hợp đồng đánh giá.

---

## 3. Các Giải pháp Xử lý Chuẩn

### Cách 1: Hoàn nguyên file bị dính commit ngoài ý muốn (Accidental Commit Revert)
Nếu một file bị commit nhầm vào range (ví dụ `do_logout_account.py` bị commit cùng lúc):
1. Đưa file đó về lại trạng thái của base commit:
   ```bash
   git checkout <base_ref> <unrelated_file>
   git commit -m "revert accidental <unrelated_file> change" <unrelated_file>
   ```
2. Kiểm tra lại danh sách file đã thay đổi giữa base và HEAD:
   ```bash
   git --no-pager diff --no-ext-diff <base_ref>..HEAD --name-only
   ```
   Xác nhận output chỉ chứa đúng các file trong `--files`.

### Cách 2: Thu hẹp mốc `--base` vào đúng phạm vi commit của task
Nếu commit range chứa nhiều commit của các task trước đó đã hoàn tất:
- Điều chỉnh `--base` trỏ vào commit cha ngay trước chuỗi commit của task hiện tại:
  ```bash
  # Ví dụ chỉ review 2 commit gần nhất:
  python D:/Taadaa/tools/closeout_gate.py --repo "<repo>" --base HEAD~2 --files <file1> <file2> --json-output
  ```

### Cách 3: Bổ sung file vào `--files` nếu thực sự thuộc phạm vi phiên
Nếu file đó là một phần của công việc cần review trong phiên (ví dụ test file hoặc helper file):
- Cung cấp đầy đủ toàn bộ các file trong committed scope vào tham số `--files`:
  ```bash
  --files file1.py file2.py tests/test_file1.py
  ```
