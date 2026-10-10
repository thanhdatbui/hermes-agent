# Manual Avatar Guard G1-G5 Hardening & Atomic Grant Lifecycle

## 1. Context & Architecture (Claude Review Approved Criteria)
Khi vận hành trang trại TikTok, các tài khoản được Operator chỉnh sửa avatar thủ công (qua chat) phải được bảo vệ bất khả xâm phạm trước các script tái tạo tự động (`regenerate_unique_avatars.py`, `_make_avatar.py`). 
Hệ thống chốt chặn gồm:
- Registry trung tâm: `manual_avatar_protected_folders.json` (tại `Tiktok-video/data/` và `D:/Taadaa/data/`).
- In-folder markers: `.manual_avatar_locked` tại cả `D:\TIKTOK-videonuoinick\<folder>` và `D:\video goc\<folder>`.
- Chốt chặn SSOT: `scripts/manual_avatar_guard.py`.

## 2. Các điểm thắt chặt trọng yếu (G1, G2, G4, G5, R3)

### G1: Fail-Closed Protection
- `get_protected_folders()`:
  - Nếu không có file registry nào tồn tại trong `REGISTRY_PATHS` -> raise `GuardIntegrityError`.
  - Nếu file JSON hỏng hoặc root không phải `dict` -> raise `GuardIntegrityError`.
  - Nếu bất kỳ phần tử nào trong `protected_folders` không parse được thành số nguyên dương -> raise `GuardIntegrityError`.
  - Quét `iterdir()` trong `ROOT_NUOI` và `ROOT_VG`: nếu gặp `PermissionError`/`OSError` -> raise `GuardIntegrityError`.
- `is_folder_avatar_protected(folder, caller="")`:
  - `folder` không parse được thành `int` (như `"abc"`, `None`, `""`) -> log cảnh báo và **trả về `True` (Fail-closed)**.

### G2: Dual Registry Integrity Validation
- Trong `validate_registry_integrity()`:
  - Khi cả 2 file trong `REGISTRY_PATHS` tồn tại, so khớp tập hợp `set(folders1) == set(folders2)`.
  - Nếu lệch nhau -> trả về `(False, f"Registry mismatch between {p1} and {p2}")`.

### G4: Path & Folder Binding
- Trong `guarded_replace(src_path, dst_path, folder, caller, grant_path, consume=True)`:
  - Nếu `dst_path.parent.name.isdigit()` và `int(dst_path.parent.name) != int(folder)`:
    - Lập tức ném `LockedFolderError("Folder mismatch: caller folder=... does not match path folder=...")`.
  - Cơ chế ghi kép NUOI + VG:
    - Khi ghi NUOI: truyền `consume=False` để giữ grant hợp lệ cho bước đồng bộ kế tiếp.
    - Khi ghi VG: truyền `consume=True` để tiêu thụ grant nguyên tử sau khi hoàn tất.

### G5: One-Time Override Grant Lifecycle
- `issue_override_grant(folder, reason, ttl_seconds=900)`:
  - TTL bị kẹp cứng: `min(900, max(30, int(ttl_seconds)))`.
  - Tạo nonce 6 bytes ngẫu nhiên: `nonce = os.urandom(6).hex()`.
  - Filename: `grant_{folder}_{timestamp}_{nonce}.json` lưu trong `get_grants_dir()`.
- `verify_override_grant(grant_path, folder)`:
  - Đường dẫn grant bắt buộc phải nằm trực tiếp trong `get_grants_dir().resolve()`.
  - Bị từ chối nếu tồn tại marker `<grant_path>.used` (hoặc `.json.used`).
  - Kiểm tra `used is False`, `folder == int(folder)`, `time.time() < expires_at`.
- `consume_grant(grant_path)`:
  - Đổi tên file grant sang `.used` bằng `os.replace` nguyên tử.
  - Nếu file đã bị đổi tên hoặc không tồn tại -> ném `LockedFolderError("Grant file missing or already consumed")`.
  - Cập nhật payload `used: True`, `consumed_at: time.time()`.

### R3 & CLI Integration
- `_make_avatar.py`: Xóa bỏ hoàn toàn cờ `--force`. Khi folder được bảo vệ, in log và thoát an toàn `return 0`.
- `regenerate_unique_avatars.py`: Khi phát hiện `LOCKED_CONFLICTS`, in output JSON `[LOCK_CONFLICT]` và thoát với **Exit Code 3** để Caller/Supervisor nhận diện yêu cầu Operator can thiệp.
