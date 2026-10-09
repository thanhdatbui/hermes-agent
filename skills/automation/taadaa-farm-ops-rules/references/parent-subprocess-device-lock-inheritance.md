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

### Bước 2: Danh sách Parent Project hợp lệ & InheritedDeviceLock Chuẩn DeviceLockLease
Định nghĩa allowlist các project cha được phép kế thừa và kế thừa trực tiếp từ `DeviceLockLease` (từ `automation_core.device_lock`) thay vì dùng bare duck-typed class (sẽ bị Plan-Review REJECT vì thiếu interface conformance):
```python
from datetime import datetime, timezone
from typing import Any
from automation_core.device_lock import DeviceLockLease, DeviceLockReleaseAudit

PARENT_LOCK_PROJECTS = (
    "tiktok-luot nuoi acc",
    "tiktok-feed",
    "multi-machine-feed-session",
)

def _is_parent_lock_owner(exc: BaseException) -> tuple[bool, str, Any]:
    """Check whether a lock exception was caused by an active parent project lock."""
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

class InheritedDeviceLock(DeviceLockLease):
    """Lease proxy inheriting an active device lock held by a parent process."""
    def __init__(self, machine: int | None = None, serial: str = "", status: str = "running"):
        self.lock_paths = []
        self.host = ""
        self.pid = 0
        self.lock_id = "inherited-parent-lease"
        self.release_on_terminal = False
        self._released = False
        self.machine = machine
        self.serial = serial
        self.status = status
        self.path = None
        self.owner: dict[str, Any] = {}

    def is_still_held(self) -> bool:
        return True

    def set_status(self, status: str) -> None:
        self.status = str(status or "").strip().lower()
        logger.info(
            "InheritedDeviceLock [Machine %s]: status transition to '%s' (retained under parent lock)",
            self.machine, self.status
        )

    def finish(self, *, succeeded: bool, failure_status: str = "handoff", **kwargs) -> None:
        logger.info(
            "InheritedDeviceLock [Machine %s]: finish(succeeded=%s, failure_status=%s) (parent lock preserved)",
            self.machine, succeeded, failure_status
        )

    def release(self) -> None:
        self._released = True
        logger.info(
            "InheritedDeviceLock [Machine %s]: release requested; lock ownership retained by parent",
            self.machine
        )

    def release_with_audit(self, *, reason: str = "") -> DeviceLockReleaseAudit:
        self._released = True
        logger.info(
            "InheritedDeviceLock [Machine %s]: release_with_audit (reason=%s); parent lock retained",
            self.machine, reason
        )
        return DeviceLockReleaseAudit(
            host=self.host,
            run_id="inherited",
            machine=self.machine,
            serial=self.serial,
            reason=reason or "inherited-parent-lock",
            released_paths=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def __enter__(self) -> "InheritedDeviceLock":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        pass
```

### Bước 3: Bắt ngoại lệ Lock và kế thừa an toàn
Cả ở vòng lặp gom máy (`main`) và hàm xử lý từng máy (`reconcile_target`):
- Trong `main()`: Bắt buộc lưu `reservations[target.machine] = InheritedDeviceLock(machine=target.machine, serial=target.serial)` để khi kết thúc batch, vòng lặp giải phóng `reservations` không bị lỗi thiếu khóa hoặc KeyError.
- Trong `reconcile_target()`: Sử dụng helper `_is_parent_lock_owner(exc)` để kiểm tra gọn, không lặp lại code trích xuất `owner_obj`.

```python
try:
    lease = acquire_device_lock(...)
except (DeviceLockNeedsUserDecision, DeviceLockUnavailable) as exc:
    is_parent, parent_project, parent_pid = _is_parent_lock_owner(exc)
    if allow_parent_lock and is_parent:
        logger.info(
            "Machine %s: kế thừa active device lock từ parent project '%s' (pid %s)",
            target.machine, parent_project, parent_pid
        )
        lease = InheritedDeviceLock(machine=target.machine, serial=target.serial)
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
2. **Conftest Path Portability (CẤM Hardcode Windows Path):** CẤM TUYỆT ĐỐI hardcode đường dẫn tuyệt đối như `Path("D:/Taadaa/automation-core/src")` trong `tests/conftest.py` (bị Plan-Review REJECT ngay lập tức vì phá hỏng tính di động trên máy khác/CI). Luôn dùng biến môi trường kết hợp fallback tương đối:
   ```python
   automation_core_env = os.environ.get("AUTOMATION_CORE_PATH")
   automation_core_path = (
       Path(automation_core_env).resolve()
       if automation_core_env
       else (REPO_ROOT.parent / "automation-core" / "src").resolve()
   )
   ```
3. **English Help Strings & Docstrings:** Các CLI argument mới và docstring/comment cần dùng tiếng Anh hoặc chuẩn hóa để tránh reviewer ngoại ngữ gắn cờ "mixed language documentation".
4. **Path Type Rigor:** Khởi tạo `DeviceLockUnavailable(Path("path/to/lock.json"), owner_dict)` bắt buộc truyền `pathlib.Path`. Truyền chuỗi thô `"..."` sẽ vi phạm type annotation và bị linter/Pyright bắt lỗi `reportArgumentType`.
5. **Môi trường Pytest trên Windows (MSYS/Git Bash):** Khi chạy `pytest` từ terminal Windows, luôn thêm cờ `-p no:cacheprovider` để chống lỗi phân quyền ghi `.pytest_cache` làm fail giả toàn bộ test run:
   ```bash
   PYTHONPATH="D:/Taadaa/tiktok-log-in;D:/Taadaa/automation-core/src" pytest -p no:cacheprovider "D:/Taadaa/tiktok-log-in/tests/test_account_reconcile_parent_lock.py"
   ```
6. **Mock Target Scope:** Trong `tiktok-log-in`, `WorkbookMachine` import từ `login_runner.account_inventory` với cấu trúc `accounts: tuple[str, ...]`, kiểm tra đúng module để unit test chạy O(1) không dính import error.
7. **Monorepo Broken Baseline Isolation:** Khi monorepo lớn có test suite cũ bị lỗi do thiếu fixture ngoài (như thiếu `Tiktok_Reg/social_reg_v1.py`), chạy focused unit test riêng cho code vừa sửa (`test_account_reconcile_parent_lock.py` pass 4/4), sau đó dùng `closeout_gate.py --skip-test` để gửi diff candidate sang Gate 1 AI Review an toàn mà không bị cản bởi broken baseline.
