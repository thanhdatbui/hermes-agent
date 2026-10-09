# Trailing Assignment Patch Truncation & Windows Pytest Cache Denied

## 1. Cạm bẫy nuốt gán biến khi Patch ngoặc đóng (`)] = target` -> `)]`)

### Bối cảnh & Hiện tượng
Trong `login_runner/account_reconcile.py`:
```python
futures[pool.submit(
    reconcile_target,
    ...
    user_authorized=args.full_scope_takeover,
)] = target
```
Khi áp Patch Contract thêm cờ `--allow-parent-lock`:
- `old_string`: kết thúc bằng `user_authorized=args.full_scope_takeover,\n)]`
- `new_string`: `user_authorized=args.full_scope_takeover,\nallow_parent_lock=args.allow_parent_lock,\n)]`

Do `old_string` chỉ lấy đến `)]`, công cụ `patch` đã cắt bỏ phần gán `= target` phía sau. Kết quả biến thành:
```python
futures[pool.submit(...)]
```

### Hậu quả nguy hiểm
- `python -m py_compile` **hoàn toàn không bắt được lỗi** vì `futures[...]` là một expression statement hợp lệ trong cú pháp Python!
- Tuy nhiên ở runtime: `futures` là một dictionary rỗng `{}`. Việc index `futures[future]` mà không có phép gán `=` sẽ ném ngoại lệ `KeyError` ngay lập tức khi thực thi!
- Tại dòng tiếp theo: `target = futures[future]` sẽ crash toàn bộ batch reconcile.

### Quy tắc phòng ngừa
- Khi soạn Patch Contract trên các cấu trúc bao bọc (dict indexing, tuple unpacking, chained assignment), **BẮT BUỘC** kiểm tra ký tự ngay sau dấu ngoặc đóng.
- Nếu dòng gốc có `= target`, `as f:`, `in list:`, bắt buộc phải đưa trọn vẹn phần đuôi này vào cả `old_string` lẫn `new_string`.

---

## 2. Lỗi `[Errno 13] Permission denied` trên `.pytest_cache` & Thiếu PYTHONPATH

### Hiện tượng
Khi chạy `pytest` trên các repo farm tại ổ `D:/Taadaa/<repo>/tests/...`:
1. `pytest` cố ghi vào `.pytest_cache/v/cache/nodeids` và vấp phải:
   `PytestCacheWarning: cache could not write path ... [Errno 13] Permission denied`
2. `ModuleNotFoundError: No module named '<package>'` do thư mục repo hiện tại chưa nằm trong `sys.path`.

### Giải pháp chuẩn
1. Luôn vô hiệu hóa provider cache của pytest bằng cờ `-p no:cacheprovider`.
2. Luôn truyền `PYTHONPATH` rõ ràng bao gồm cả repo đích và `automation-core`:
   ```bash
   PYTHONPATH="D:/Taadaa/tiktok-log-in;D:/Taadaa/automation-core" pytest -p no:cacheprovider "D:/Taadaa/tiktok-log-in/tests/<test_file>.py"
   ```

---

## 3. Cạm bẫy Mock thuộc tính không tồn tại (`AttributeError` trong `patch()`)

### Hiện tượng
Khi prompt giao đoạn test mẫu chỉ định mock các hàm/class:
- `from login_runner.workbook_inventory import WorkbookMachine, WorkbookAccount` (trong khi file thực tế là `account_inventory.py` và `accounts` là tuple string).
- `patch("login_runner.account_reconcile.capture_device_accounts")` (trong khi hàm này không tồn tại trong module `account_reconcile`).

Mặc định, `unittest.mock.patch()` kiểm tra xem thuộc tính có tồn tại trong target module hay không trước khi mock. Nếu không có, nó ném terminating `AttributeError`.

### Giải pháp
- Nếu cần mock một interface ngoài hoặc backward compatibility trong test, thêm cờ `create=True`:
  ```python
  patch("login_runner.account_reconcile.capture_device_accounts", create=True, return_value=([], []))
  ```
- Luôn kiểm tra định vị thực tế của các models/dataclasses trước khi import trong test suite.
