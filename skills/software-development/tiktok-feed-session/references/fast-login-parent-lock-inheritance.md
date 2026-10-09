# Kế thừa Device Lock cho Fast Auto-Login trong Feed Session (Parent-Lock Inheritance)

## 1. Bối cảnh & Triệu chứng lỗi (Root Cause từ Ca chạy Row 3 Farm Kibe)
- Trong luồng nuôi acc (`feed-session-smoke` / `multi-machine-feed-session`), khi kiểm tra Account Switcher phát hiện thiếu nick mục tiêu (`manual-needed:account-switcher-missing-expected`), script kích hoạt `auto_login_recovery` qua Fast Targeted Login:
  `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID> --ss`
- **Điểm nghẽn xung đột lock:** Tiến trình mẹ `run_tiktok.py` (project `tiktok-luot nuoi acc`) đang nắm giữ file lock thiết bị:
  `C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json`
- Khi `tiktok_login_v1.py` khởi chạy với `acquire_device_lock(user_authorized=False)`, nó phát hiện active lock của `run_tiktok.py` và raise `DeviceLockNeedsUserDecision`, thoát ngay với exit code 2:
  `[device-lock] NEEDS_USER_DECISION: device lock active: path=... project=tiktok-luot nuoi acc command=run_tiktok.py --mode multi-machine-feed-session reservation`
- Hậu quả: Fast auto-login thất bại trong 6 giây, feed session fallback sang `reconcile_tiktok_accounts.py` (vốn quét toàn bộ inventory) dẫn đến timeout 300s và toàn bộ máy bị đánh dấu `manual-needed` oan uổng dù máy còn slot trống và nick có sẵn pass/2FA TOTP trong workbook.

---

## 2. Kiến trúc Kế thừa Device Lock (Inherited Device Lock Pattern)

### Phía Child Tool (`D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py`):
1. **Tham số CLI:**
   Bổ sung argument `--allow-parent-lock` vào `parse_args`:
   ```python
   parser.add_argument(
       "--allow-parent-lock",
       action="store_true",
       help="Kế thừa active device lock nếu được gọi từ parent automation (ví dụ: tiktok-luot nuoi acc)",
   )
   ```

2. **Allowlist Parent Projects & Helper Kiểm tra:**
   ```python
   PARENT_LOCK_PROJECTS = (
       "tiktok-luot nuoi acc",
       "tiktok-feed",
       "multi-machine-feed-session",
   )

   def _is_parent_lock_owner(exc: BaseException) -> tuple[bool, str, Any]:
       owner_obj = getattr(exc, "owner", None)
       if not owner_obj:
           return False, "", None
       if isinstance(owner_obj, dict):
           parent_project = str(owner_obj.get("project") or "").strip().lower()
           parent_pid = owner_obj.get("pid")
       else:
           parent_project = str(getattr(owner_obj, "project", "") or "").strip().lower()
           parent_pid = getattr(owner_obj, "pid", None)
       return parent_project in PARENT_LOCK_PROJECTS, parent_project, parent_pid
   ```

3. **Proxy Lease không giải phóng lock của mẹ:**
   ```python
   class InheritedDeviceLock:
       """Lease proxy kế thừa lock đang được giữ bởi tiến trình mẹ."""
       def __init__(self, machine: int | None = None, serial: str = "", status: str = "running"):
           self.machine = machine
           self.serial = serial
           self.status = status
           self.path = None
           self.owner = {}

       def is_still_held(self) -> bool:
           return True

       def release(self) -> None:
           # Không xóa file lock vì lock thuộc sở hữu của tiến trình mẹ
           pass
   ```

4. **Bắt ngoại lệ tại `main()`:**
   ```python
   try:
       device_lock = acquire_device_lock(
           machine=args.stt,
           serial=device_id,
           project="Tiktok_Reg",
           command=sys.argv,
           user_authorized=False,
       )
   except (DeviceLockNeedsUserDecision, DeviceLockUnavailable) as e:
       is_parent, parent_proj, parent_pid = _is_parent_lock_owner(e)
       if getattr(args, "allow_parent_lock", False) and is_parent:
           log(f"[device-lock] Kế thừa active device lock từ parent project '{parent_proj}' (pid {parent_pid})")
           device_lock = InheritedDeviceLock(machine=args.stt, serial=device_id)
       elif isinstance(e, DeviceLockNeedsUserDecision):
           log(f"[device-lock] NEEDS_USER_DECISION: {e.describe()}")
           return 2
       else:
           log(f"[device-lock] SKIP login STT {args.stt}: {e.describe()}")
           return 0
   ```

---

## 3. Phía Caller (`D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`)
Trong hàm `_run_fast_targeted_login`:
```python
fast_cmd = [
    str(python_exe),
    str(fast_login_script),
    str(machine_id),
    "--email", str(expected),
    "--ss",
    "--allow-parent-lock",
]
```

---

## 4. Focused Unit Test Pattern (< 30s)
Tại `D:/Taadaa/Tiktok_Reg/tests/test_tiktok_login_parent_lock.py`:
- Mock lock file trên đĩa chứa `{"project": "tiktok-luot nuoi acc", "pid": os.getpid()}`.
- Test case 1: Gọi `main([str(stt), "--email", "dummy"])` -> Bắt buộc trả về exit code 2 (`NEEDS_USER_DECISION`).
- Test case 2: Gọi `main([str(stt), "--email", "dummy", "--allow-parent-lock"])` -> Vượt qua bước kiểm tra lock thành công, gán `InheritedDeviceLock`.
