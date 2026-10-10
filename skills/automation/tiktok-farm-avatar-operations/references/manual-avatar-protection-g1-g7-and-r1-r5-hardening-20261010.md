# Manual Avatar Guard: Hardened Protection G1-G7 & R1-R5 (Architecture & Integration Guide)

Tài liệu hướng dẫn triển khai và tích hợp bộ chốt chặn G1-G7 và R1-R5 bảo vệ avatar thủ công khỏi các script quét và tái tạo hàng loạt.

---

## 1. Bản chất & Nguyên tắc cốt lõi
- **Fail-closed (Mặc định là KHÓA):** Mọi sự cố nạp registry, lỗi JSON format, hoặc thiếu file đều kích hoạt ném ngoại lệ `GuardIntegrityError` và dừng chạy ngay, cấm fail-open.
- **One-Time Override Grant:** Operator là người duy nhất có quyền cấp phép ghi đè avatar thủ công. Grant có thời hạn 15 phút (900s), dùng 1 lần duy nhất cho đúng `folder_id`. Khi ghi đè xong, trạng thái khóa của folder vẫn giữ nguyên (không xóa marker, không xóa registry).
- **Điểm ghi duy nhất (`guarded_replace`):** Toàn bộ các script thay thế avatar cấm gọi `os.replace` trần, bắt buộc đi qua `guarded_replace(src, dst, folder, caller, grant_path)`.

---

## 2. API Contract trong `manual_avatar_guard.py` (G1-G7)

### Exceptions
```python
class LockedFolderError(Exception):
    """Ném ra khi ghi đè vào folder bị khóa mà không có grant hợp lệ."""
    pass

class GuardIntegrityError(Exception):
    """Ném ra khi registry JSON bị hỏng, rỗng hoặc môi trường bảo vệ bị lỗi."""
    pass
```

### Chi tiết trạng thái khóa
```python
def get_lock_info(folder: Any) -> dict:
    """
    Trả về thông tin chi tiết:
    {
        'folder': int,
        'locked': bool,
        'sources': list[str], # ['registry:<path>', 'marker:<path>']
        'account_info': dict   # metadata từ accounts[str(folder)] trong registry
    }
    """
```

### Override Grant Mechanism
- **Cấp grant:** `issue_override_grant(folder: int, reason: str, ttl_seconds: int = 900) -> Path`
  - Lưu tại `D:\Taadaa\data\avatar_override_grants` (fallback `REPO_ROOT/data/avatar_override_grants`).
  - Ghi file `grant_<folder>_<timestamp>.json` chứa `{folder, reason, created_at, expires_at, used: False}`.
- **Xác thực grant:** `verify_override_grant(grant_path: Path | str, folder: int) -> bool`
  - Điều kiện hợp lệ: file tồn tại, folder khớp, `time.time() < expires_at`, `used == False`.
- **Tiêu thụ grant:** `consume_grant(grant_path: Path | str) -> None`
  - Đánh dấu `used: True`, ghi `consumed_at`.

### Atomic Write Guard
```python
def guarded_replace(
    src_path: Path | str,
    dst_path: Path | str,
    folder: int,
    caller: str = "",
    grant_path: Path | str | None = None
) -> None:
    """
    - Nếu folder bị khóa và không có grant hợp lệ: ném LockedFolderError, log denied metric.
    - Nếu folder bị khóa và có grant hợp lệ:
      1. Sao lưu dst_path hiện tại sang <dst_path.parent>/.manual_backup/avatar.<YYYYMMDD_HHMMSS>.jpg
      2. os.replace(src_path, dst_path)
      3. consume_grant(grant_path)
      4. log override_write metric.
    - Nếu folder không bị khóa: os.replace(src_path, dst_path) bình thường.
    """
```

---

## 3. Tích hợp trong `regenerate_unique_avatars.py` (R1-R5)

1. **Khởi động an toàn (R1):**
   Gọi `validate_registry_integrity()` ngay đầu `main()`. Nếu trả về `(False, reason)` $\to$ log lỗi và exit ngay.
2. **Quét trùng & ghi nhận khóa (R2):**
   Trong `find_all_duplicate_folders()`:
   - `locked_hits = unique_folders & protected`
   - Log `[GUARD] Phát hiện {len(locked_hits)} folder trùng đang bị khóa: {sorted(list(locked_hits))}`
3. **Thao tác ghi qua `guarded_replace` (R4):**
   Trong `process_folder(folder)`:
   - Thay thế `os.replace(tmp_target, final_target)` bằng `guarded_replace(tmp_target, final_target, folder=folder, caller="regenerate_unique_avatars")`.
   - Thay thế `os.replace(vg_tmp, vg_target)` bằng `guarded_replace(vg_tmp, vg_target, folder=folder, caller="regenerate_unique_avatars")`.
4. **Báo cáo xung đột & Mã thoát (R3):**
   Nếu có `locked_hits`, xuất khối JSON `[LOCK_CONFLICT]` chứa chi tiết từng folder và `get_lock_info(folder)`. Trả về exit code 3 (`NEEDS_OPERATOR_DECISION`) để Coordinator gọi tool `clarify` xin chỉ thị từ Operator.
