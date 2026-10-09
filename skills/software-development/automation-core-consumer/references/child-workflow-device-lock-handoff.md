# Child Workflow Device Lock Handoff Pattern

## 1. Context & The Problem

On multi-machine farm operations, long-running parent workflows often need to invoke specialized child workflows as subprocesses.

### Example Topology
- **Parent Process**: `multi_machine_feed_session.py` (project: `tiktok-luot nuoi acc`). Holds device lock on machine $N$ (`machine_N.lock.json`).
- **Child Subprocess**: `run_post.py` / `tiktok_workflow` (project: `tiktok-upload` / `tiktok-video`). Invoked by parent during feed session to upload a video hook.

### The Lock Contention Trap
When the child workflow starts, its state machine runs `ACQUIRE_LOCKS`. Normally:
1. Child queries `acquire_device_lock` for the serial/machine.
2. It detects an active lock owned by another PID and a foreign project (`tiktok-luot nuoi acc` vs `tiktok-upload`).
3. Since the lock owner is alive and foreign, `acquire_device_lock` raises `DeviceLockNeedsUserDecision` (`[NEEDS_USER_DECISION] ACQUIRE_LOCKS`).
4. The child upload fails immediately before performing any UI steps.

---

## 2. Anti-Patterns (Cấm Tuyệt Đối)

1. **Cấm bypass toàn bộ lock trong child workflow**: Bỏ qua hoàn toàn bước check lock sẽ khiến các batch khác (Reg Gmail, 2FA, Watchdog) tưởng máy rảnh và lao vào can thiệp đồng thời.
2. **Cấm xóa hoặc ghi đè file lock của parent**: Child process tuyệt đối không được xóa file `machine_N.lock.json` hoặc ép takeover, vì parent vẫn đang chạy và cần bảo vệ máy đến khi kết thúc toàn bộ feed session.
3. **Cấm dùng `user_authorized=True` bừa bãi**: `user_authorized=True` chỉ dành cho operator can thiệp thủ công từ console, không dùng trong automation tự động.

---

## 3. Architecture Pattern: Parent-Lock Handoff

The safe contract allows the parent to explicitly authorize the child to run under its existing lease without creating or modifying lock files.

### Step 1: Parent Subprocess Invocation (`multi_machine_feed_session.py`)
Parent explicitly passes `--allow-parent-lock` when building argv for the upload subprocess:
```python
cmd = [
    sys.executable, "-m", "tiktok_workflow.run_post",
    "--config", str(config_file),
    "--workflow-workbook", str(workbook_path),
    "--single-device", str(account.serial),
    "--video-number", str(next_video),
    "--video-source-root", str(media_root),
    "--allow-device-reboot-recovery",
    "--allow-parent-lock",
    "--no-dry-run",
]
```

### Step 2: Child CLI Flag (`run_post.py`)
Child entrypoint defines a narrow, non-destructive CLI flag:
```python
parser.add_argument(
    "--allow-parent-lock",
    action="store_true",
    default=False,
    help=(
        "Allow execution when parent process already holds the device lock. "
        "Operates unlocked via no-op lease without modifying lock files."
    ),
)
```
And maps it into configuration:
```python
if args.allow_parent_lock:
    config._data["allow_parent_lock"] = True
```

### Step 3: State Machine No-Op Lease (`state_machine.py`)
In `_handle_acquire_locks`, immediately after dry-run early-return and **before** any stale-lock inspection or takeover:
```python
from automation_core.device_lock import _UnlockedDeviceLockLease

if self.context.config.get("allow_parent_lock") is True:
    logger.info("[PARENT_LOCK] parent-lock handoff accepted; using no-op lease")
    self.context.device_lease = _UnlockedDeviceLockLease(
        lock_paths=[],
        host=socket.gethostname(),
        pid=os.getpid(),
        lock_id=f"parent-lock-handoff-{uuid.uuid4().hex[:8]}",
        release_on_terminal=False,
    )
    return True
```

### Why `_UnlockedDeviceLockLease(lock_paths=[])` Works
`_UnlockedDeviceLockLease` inherits from `DeviceLockLease` but overrides:
- `release()` $\rightarrow$ `self._released = True` (no file deletion).
- `set_status(...)` $\rightarrow$ `return None` (no file writes).
- `finish(...)` $\rightarrow$ `self._released = True`.
- `__exit__(...)` $\rightarrow$ `self._released = True`.

Because `lock_paths` is empty (`[]`), even if any inner code inspects paths, no lock file on disk is touched. The parent continues to hold the real lock unbroken throughout child startup, execution, and exit.

---

## 4. Verification Checklist

1. **Subprocess Argv Test**: Verify that the parent caller's hook runner (`_run_upload_hook`) builds command arguments containing `--allow-parent-lock`.
2. **Child Entrypoint Test**: Verify `--allow-parent-lock` correctly sets `config["allow_parent_lock"] == True`.
3. **State Machine Test**: Verify that when `allow_parent_lock=True`, `_handle_acquire_locks` succeeds, assigns an instance of `_UnlockedDeviceLockLease`, and leaves all files under `device-locks/` untouched.
