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

## 2. Kiến trúc Kế thừa Device Lock (Production Contract Approved by Sol Auditor >= 85)

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

3. **Contract Đầy Đủ của `InheritedDeviceLock` (Đạt chuẩn Closeout Gate >= 85 điểm):**
   ```python
   class InheritedDeviceLock:
       """Device lock lease adapter that inherits and tracks active parent lock lease."""

       def __init__(self, machine=None, serial="", parent_project="", parent_pid=None):
           self.machine = machine
           self.serial = serial
           self.parent_project = parent_project
           self.parent_pid = parent_pid
           self.lock_id = f"inherited-{os.urandom(4).hex()}"
           self.status = "running"
           self.released = False
           self.acquired_at = time.time()
           self.released_at = None
           self.lifecycle_events = []
           self._record_telemetry("acquired", {"status": self.status})

       def _record_telemetry(self, action: str, extra: dict | None = None) -> None:
           evt = {
               "timestamp": time.time(),
               "action": action,
               "lock_id": self.lock_id,
               "machine": self.machine,
               "serial": self.serial,
               "parent_project": self.parent_project,
               "parent_pid": self.parent_pid,
           }
           if extra:
               evt.update(extra)
           self.lifecycle_events.append(evt)
           log(f"[device-lock] [telemetry] action={action} lock_id={self.lock_id} machine={self.machine} serial={self.serial} parent={self.parent_project} pid={self.parent_pid}")

       def set_status(self, status: str) -> None:
           normalized = str(status or "").strip().lower()
           if normalized not in {"queued", "running", "recovery", "handoff", "blocked", "temporarily_skipped"}:
               raise ValueError(f"unsupported device lock status: {status}")
           self.status = normalized
           self._record_telemetry("set_status", {"status": normalized})

       def mark_reg_success_today(self, *, today=None) -> None:
           try:
               if self.machine not in (None, ""):
                   record_machine_reg_success(self.machine, serial=self.serial or "", success_date=today)
           except Exception as exc:
               log(f"[device-lock] warning: mark_reg_success_today failed: {exc}")
           self._record_telemetry("mark_reg_success_today")

       def is_daily_reg_cooldown_active(self, *, today=None) -> bool:
           try:
               if self.machine not in (None, ""):
                   return is_machine_reg_cooldown_active(str(self.machine), today=today)
           except Exception as exc:
               log(f"[device-lock] warning: is_daily_reg_cooldown_active failed: {exc}")
           return False

       def release(self) -> None:
           if not self.released:
               self.released = True
               self.released_at = time.time()
               self._record_telemetry("released", {"duration": round(self.released_at - self.acquired_at, 2)})
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
           log(f"[device-lock] Ke thua active device lock tu parent project '{parent_proj}' (pid {parent_pid})")
           device_lock = InheritedDeviceLock(
               machine=args.stt,
               serial=device_id,
               parent_project=parent_proj,
               parent_pid=parent_pid,
           )
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
- Test arg parsing `--allow-parent-lock`.
- Test allowlist project matching (`PARENT_LOCK_PROJECTS`) và reject unauthorized project.
- Test `InheritedDeviceLock` full lifecycle: `acquired` -> `set_status` -> `mark_reg_success_today` -> `release`.
- Mock `is_machine_reg_cooldown_active` và `record_machine_reg_success` để test cooldown logic độc lập với file lock trên đĩa.
- Test `main()` fail closed (exit 2) khi lock active mà không có cờ hoặc project không hợp lệ.
- Test `main()` pass qua bước lock khi có cờ và parent project hợp lệ.
