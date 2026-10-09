# Parent-Subprocess Device Lock Inheritance (Case LOCK-05 Pattern)

## 1. Bản chất sự cố "Cha khóa cửa con" (Parent Lockout Child Subprocess)
Trong hệ thống Farm Automation đa repo, khi một tiến trình cha (ví dụ `run_tiktok.py` / `multi-machine-feed-session` trong `tiktok-luot nuoi acc`) đang chạy, nó giữ active device lock trên thiết bị:
- `status`: `"running"`
- `owner_active`: `True`
- `pid`: PID của tiến trình cha (đang sống)

Khi phát hiện điều kiện cần phục hồi (ví dụ: mở switcher thấy thiếu tài khoản cần lướt feed, hoặc kết thúc lướt cần chạy follow hook), tiến trình cha gọi subprocess con qua `subprocess.run()`:
- Ví dụ: `reconcile_tiktok_accounts.py` (`tiktok-log-in`) hoặc `run_follow.py` (`tiktok-follow`).

### Anti-Pattern:
1. Subprocess con khi khởi động gọi `acquire_device_lock()`.
2. Trong `automation_core.device_lock`, cơ chế `FULL_SCOPE_TAKEOVER` chỉ cho phép chiếm quyền trên lock **inactive/dead** (`alive is False` hoặc `status in {"handoff", "recovery"}`). Khi lock thuộc về tiến trình cha đang chạy (`alive is True`, `status="running"`), `acquire_device_lock` lập tức ném `DeviceLockUnavailable` hoặc `DeviceLockNeedsUserDecision`.
3. Subprocess con bắt ngoại lệ, đánh dấu máy bị `SKIPPED_LOCKED` và thoát với exit code lỗi (ví dụ returncode = 4) chỉ sau 1-2 giây.
4. Tiến trình cha thấy subprocess trả về mã lỗi, kết luận auto-recovery thất bại và rơi vào nhánh fallback dừng phiên `manual-needed` (ví dụ `profile username still mismatched after switch`), giữ lock `blocked` (TTL 1h).

---

## 2. Mô hình chuẩn hóa: Lock Inheritance (Kế thừa Lock theo Case LOCK-05)

Subprocess con khi được gọi từ tiến trình cha KHÔNG ĐƯỢC cướp hay giải phóng lock của cha, mà phải **kế thừa quyền truy cập thiết bị (Lock Inheritance)**:

### Bước 1: Khai báo CLI argument trên script con
Thêm cờ chỉ định kế thừa lock, ví dụ `--allow-parent-lock` (hoặc `--skip-identity-verify` trong follow hook):
```python
parser.add_argument(
    "--allow-parent-lock",
    action="store_true",
    help="Cho phép kế thừa active device lock từ tiến trình cha tiktok-luot nuoi acc",
)
```

### Bước 2: Danh sách Parent Project hợp lệ & No-Op Lease
Định nghĩa allowlist các project cha được phép kế thừa và tạo class dummy lease để không làm thay đổi trạng thái lock của cha:
```python
PARENT_LOCK_PROJECTS = (
    "tiktok-luot nuoi acc",
    "tiktok-feed",
    "multi-machine-feed-session",
)

class InheritedDeviceLock:
    """No-op dummy lease khi kế thừa device lock từ tiến trình cha."""
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_status(self, *args, **kwargs):
        pass

    def finish(self, *args, **kwargs):
        pass

    def release(self, *args, **kwargs):
        pass

    def release_with_audit(self, *args, **kwargs):
        pass
```

### Bước 3: Bắt ngoại lệ Lock và kế thừa an toàn
Cả ở vòng lặp gom máy (`main`) và hàm xử lý từng máy (`reconcile_target`):
```python
try:
    lease = acquire_device_lock(...)
except (DeviceLockNeedsUserDecision, DeviceLockUnavailable) as exc:
    owner_dict = getattr(exc, "owner", {}) or {}
    parent_project = str(owner_dict.get("project") or "").strip().lower()
    if allow_parent_lock and parent_project in PARENT_LOCK_PROJECTS:
        logger.info(
            "Machine %s: kế thừa active device lock từ parent project '%s' (pid %s)",
            target.machine, parent_project, owner_dict.get("pid")
        )
        lease = InheritedDeviceLock()
    elif isinstance(exc, DeviceLockNeedsUserDecision):
        return None, ReconcileOutcome(..., "NEEDS_USER_DECISION", ...)
    else:
        return None, ReconcileOutcome(..., "SKIPPED_LOCKED", ...)
```

### Bước 4: Caller (tiến trình cha) truyền cờ kế thừa
Trong hàm gọi subprocess (ví dụ `_maybe_recover_missing_account_via_login` trong `feed_swipe_smoke.py`):
```python
cmd = [
    str(python_exe),
    str(reconcile_script),
    "--workbook", str(workbook),
    "--machines", str(machine_id),
    ...
    "--allow-live-reconcile",
    "--full-scope-takeover",
    "--allow-parent-lock",  # BẮT BUỘC để script con không tự block chính mình
]
```

---

## 3. Quy tắc điều phối Coordinator: Patch Contract cho Monolith (>=5k dòng)
- Khi dispatch worker subagent sửa các file monolith (ví dụ `account_reconcile.py`, `feed_swipe_smoke.py`), **CẤM TUYỆT ĐỐI** giao task mở để worker tự đọc và tự tìm vị trí sửa (worker sẽ cạn sạch 20-35 tool calls chỉ để định vị code).
- Coordinator BẮT BUỘC:
  1. Dùng lệnh O(1) kiểm tra `old_string` đảm bảo `count == 1`.
  2. Soạn sẵn **Patch Contract** chi tiết (old_string -> new_string).
  3. Dispatch worker với lệnh duy nhất: dùng `patch(mode='replace')` thực thi contract, chạy `py_compile` và focused unit test (<30s).

---

## 4. Pitfalls & Focused Unit Testing cho Lock Inheritance
1. **Threadpool Caller Wire-up Pitfall:** Khi thêm `allow_parent_lock: bool = False` vào `reconcile_target()`, BẮT BUỘC phải truyền `allow_parent_lock=args.allow_parent_lock` tại lệnh `pool.submit(reconcile_target, ...)` trong `main()`. Nếu quên wire-up ở caller trong threadpool, batch thật vẫn sẽ chạy default `False` và tiếp tục văng `SKIPPED_LOCKED`.
2. **Path Type Rigor:** Khởi tạo `DeviceLockUnavailable(Path("path/to/lock.json"), owner_dict)` bắt buộc truyền `pathlib.Path`. Truyền chuỗi thô `"..."` sẽ vi phạm type annotation và bị linter/Pyright bắt lỗi `reportArgumentType`.
3. **Môi trường Pytest trên Windows (MSYS/Git Bash):** Khi chạy `pytest` từ terminal Windows, luôn thêm cờ `-p no:cacheprovider` để chống lỗi phân quyền ghi `.pytest_cache` làm fail giả toàn bộ test run:
   ```bash
   PYTHONPATH="D:/Taadaa/tiktok-log-in;D:/Taadaa/automation-core/src" pytest -p no:cacheprovider "D:/Taadaa/tiktok-log-in/tests/test_account_reconcile_parent_lock.py"
   ```
4. **Mock Target Scope:** Trong `tiktok-log-in`, `WorkbookMachine` import từ `login_runner.account_inventory` với cấu trúc `accounts: tuple[str, ...]`, kiểm tra đúng module để unit test chạy O(1) không dính import error.

---

## 5. Variant: State-Machine Upload Hook (`tiktok_workflow` / `_UnlockedDeviceLockLease`)

Khi tiến trình cha (`multi_machine_feed_session.py`) gọi subprocess upload hook (`run_post.py` trong repo `Tiktok-video` / `tiktok_workflow`):
- Thay vì tự viết class dummy lease `InheritedDeviceLock`, sử dụng trực tiếp primitive chuẩn từ `automation-core`:
  ```python
  from automation_core.device_lock import _UnlockedDeviceLockLease
  ```
- **CLI (`run_post.py`)**:
  ```python
  parser.add_argument(
      "--allow-parent-lock",
      action="store_true",
      default=False,
      help="Allow child upload workflow to run under parent device lock without mutating locks.",
  )
  if args.allow_parent_lock:
      config._data["allow_parent_lock"] = True
  ```
- **State Machine (`state_machine.py` - `_handle_acquire_locks`)**:
  Xử lý ngay sau dry-run check và **trước** bước kiểm tra stale lock / takeover:
  ```python
  if self.context.config.get("allow_parent_lock") is True:
      logger.info("[PARENT_LOCK] parent-lock handoff accepted; running under no-op lease")
      self.context.device_lease = _UnlockedDeviceLockLease(
          lock_paths=[],
          host=socket.gethostname(),
          pid=os.getpid(),
          lock_id=f"parent-lock-handoff-{uuid.uuid4().hex[:8]}",
          release_on_terminal=False,
      )
      return True
  ```
  `_UnlockedDeviceLockLease` với `lock_paths=[]` đảm bảo khi child workflow hoàn thành, exit hoặc gọi `.release()` / `.finish()`, tuyệt đối không xóa hay sửa đổi file lock của tiến trình cha trên đĩa.

