# Two-Way Device Lock Concurrency: Feed Session vs Operator Ad-Hoc Scripts

## 1. Context & Operational Invariant
On multi-device phone farms (e.g. 74 Samsung S7 nodes), device exclusivity must work predictably in two opposite directions:
1. **Operator Preempts Batch (Clean Skip)**: An operator locks a device to perform maintenance (app upgrade, account fix, APK push). When the automated feed session or batch schedule runs, it must cleanly skip the locked machine without failing the entire batch into `MANUAL_NEEDED` (exit code 2).
2. **Batch Preempts Operator (Wait & Hold)**: When a scheduled feed session is actively running, an operator or background tool attempting to touch the machine must automatically wait (`wait_for_device_lock`) until the feed session releases the lock, rather than erroring out or firing concurrent ADB commands.
3. **Cross-Project Invariant (TẤT CẢ REPO BẮT BUỘC CHUNG THƯ MỤC LOCK)**:
   - Tất cả các repo trên farm (`Tiktok-video`, `register gmail`, `tiktok-add-bao-mat-f2a`, `tiktok-luot nuoi acc`) **BẮT BUỘC** phải ghi và đọc chung lock tại:
     `C:\Users\Kibe\AppData\Local\automation-core\device-locks` (hoặc fallback `~/.codex/device-locks`).
   - Tuyệt đối không được có repo nào bypass hay tự ý comment out `_filter_locks()` với lý do "bỏ hết cơ chế lock".

---

## 2. Bài Học Thực Tế: Hổng Lock 2 Chiều Giữa TikTok Upload & Reg Gmail (2026-09-23)
### Hiện tượng
- Khi đang chạy Canary Upload Avatar trên Máy 13 trong repo `Tiktok-video`, đột nhiên app Gmail bật lên đè lên màn hình TikTok với thông báo checkpoint xác minh selfie.
- Quản trị viên/User phát hiện và chỉ ra: "cron reg gmail chiếm máy, cơ chế lock 2 chiều bị lỗi rồi".

### Nguyên nhân kỹ thuật
1. **Repo `Tiktok-video` hổng lock:**
   Trong `scripts/tiktok_workflow/machine_inventory.py`, hàm `_filter_locks()` bị bypass:
   ```python
   def _filter_locks(entries, skipped, lock_root):
       # "bỏ hết cơ chế lock" -> return entries
       return entries
   ```
   Dẫn đến khi chạy `run_tiktok_upload_avatar.ps1` hoặc `run_tiktok_upload_batch.ps1`, không có file lock nào được ghi vào `device-locks/`.
2. **Watchdog `post_noon_chain_watchdog` quét thấy máy rảnh:**
   Watchdog kiểm tra `has_active_device_locks()` trong thư mục lock chung. Thấy không có file lock nào của Máy 13, watchdog kết luận toàn farm rảnh và kích hoạt batch `run_all.ps1` (Reg Gmail) và `run_batch_live_2fa.py`.
3. **Hai tiến trình cùng can thiệp ADB:**
   Reg Gmail thực hiện `pm clear com.google.android.gm` và mở luồng tạo tài khoản trên Máy 13 ngay lúc TikTok đang thực hiện đổi avatar.
4. **Cộng hưởng với Teardown Recent Apps:**
   Khi TikTok upload gặp lỗi và thực hiện teardown thất bại qua `close_all_recent_apps()` (bấm phím `keyevent 187` - Recent Apps), giao diện task switcher đã lôi cửa sổ Gmail đang treo nền ra foreground đè lên màn hình.

### Khắc phục & Rào chắn (Hard Guard)
- **Cửa ngõ `machine_inventory.py`**: Bắt buộc khôi phục kiểm tra `device_lock_paths()`; nếu máy đang có active lock thì đưa vào `skipped` (`SKIPPED_LOCKED`).
- **Khởi chạy Worker**: Từng worker khi chạy bắt buộc tạo lock với `project="tiktok-video"` (hoặc `tiktok-upload`), và chỉ release khi hoàn thành.
- **Teardown sạch**: Sau khi gọi `close_all_recent_apps()`, bắt buộc gửi thêm `keyevent 3` (HOME) để đưa máy về màn hình chính sạch, không để lộ recent tasks.

---

## 3. Shared-Core Primitives (`automation_core.device_lock`)

### `wait_for_device_lock`
Polling loop with a deadline that attempts `acquire_device_lock`:
- Traps `(DeviceLockUnavailable, DeviceLockNeedsUserDecision)`.
- Reaps dead owners if `_owner_process_alive(owner) is False` (comparing both PID existence and creation timestamps to defeat Windows PID reuse).
- Raises structured `DeviceLockTimeoutError` (with `machine`, `serial`, `owner`, `waited_seconds`) on expiry.

### `operator_device_lock`
Context manager wrapper around `wait_for_device_lock`:
```python
from automation_core.device_lock import operator_device_lock

with operator_device_lock(machine=12, project="operator_tool", timeout=300):
    # Safe section: feed sessions will skip machine 12
    # Operator tool runs exclusive ADB operations
    # Lock is automatically released on exit
    ...
```

---

## 4. Consumer Batch Integration Pattern (`run-feed-session.ps1` & `_aggregate_rows`)

### Preflight Filter (PowerShell)
Filter machine lists **before** dispatching to the runner:
```powershell
$activeMachineValues = [System.Collections.Generic.List[int]]::new()
foreach ($m in $machineValues) {
    $lockPath = Join-Path $lockDir "machine_${m}.lock.json"
    if (Test-Path -LiteralPath $lockPath) {
        $lockData = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json
        $proc = if ($lockData.pid) { Get-Process -Id $lockData.pid -ErrorAction SilentlyContinue } else { $null }
        if ($proc) {
            Write-Host "[PRE-FLIGHT] SKIP may $m: dang bi lock boi PID $($lockData.pid) ($($lockData.project))"
            continue  # Exclude from batch
        } else {
            Remove-Item -Force -LiteralPath $lockPath -ErrorAction SilentlyContinue
        }
    }
    $activeMachineValues.Add($m)
}
$machineList = ($activeMachineValues -join ",")
if ($activeMachineValues.Count -eq 0) {
    Write-Host "[PRE-FLIGHT] All machines locked. Clean exit."
    exit 0
}
```

### Result Aggregation (`_aggregate_rows`)
Decouple `skipped-device-locked` from unhandled `needs-user-decision`:
- `needs-user-decision` present $\rightarrow$ `MANUAL_NEEDED` (operator must intervene).
- `skipped-device-locked` present with other machines succeeding $\rightarrow$ `SUCCESS` / `SUCCESS_WITH_SKIPS` (clean skip).
- 100% machines locked $\rightarrow$ `MANUAL_NEEDED` / `NO_WORK_AVAILABLE`.

---

## 5. Subprocess Parent-Child Lock Handoff Contract (`--allow-parent-lock`)

### Bối cảnh & Hiện tượng (2026-09-24 / 2026-09-25)
Trong luồng nuôi đa máy (`multi_machine_feed_session.py`, project `tiktok-luot nuoi acc`), sau khi lướt feed xong, flow kích hoạt upload hook bằng cách gọi subprocess `tiktok_workflow` (`run_post.py` -> `state_machine.py`, project `tiktok-upload`).
- **Lỗi phát sinh:** Toàn bộ các máy được kích hoạt upload đều thất bại ngay tại bước khởi tạo với lỗi:
  `[FAILED] [NEEDS_USER_DECISION] ACQUIRE_LOCKS: Cần user quyết định cho device lock: device needs user decision (locked by another owner): path=C:\Users\Kibe\.codex\device-locks\machine_X.lock.json`
- **Nguyên nhân:** Parent process (`tiktok-luot nuoi acc`) vẫn đang nắm giữ exclusive device lock. Khi subprocess (`tiktok-upload`) khởi chạy, nó gọi `acquire_device_lock()`. Vì lock file mang PID và project name của parent (`tiktok-luot nuoi acc`), child coi đây là foreign active lock và fail ngay lập tức trước khi chạm vào UI thiết bị.

### Các Phản Hoa Văn Cần Tránh (Anti-Patterns)
1. **CẤM release lock trước khi spawn subprocess:** Sẽ tạo ra khoảng hở thời gian (race condition) khiến các cronjob khác (Reg Gmail, 2FA, Watchdog) nhảy vào chiếm máy.
2. **CẤM xoá file lock của parent:** Sẽ làm hỏng state tracking và watchdog kiểm toán của parent flow.
3. **CẤM lạm dụng `--takeover-force` hoặc `user_authorized=True`:** Gây phá hủy metadata của parent lock và che giấu xung đột thực sự giữa các tiến trình độc lập.

### Hợp Đồng Chuẩn (Parent-Child Handoff Protocol)
1. **Parent CLI Invocation:**
   Khi parent workflow gọi subprocess child trên cùng một thiết bị đang giữ lock, parent BẮT BUỘC truyền cờ tường minh:
   ```python
   subprocess_cmd = [
       sys.executable, "-m", "tiktok_workflow",
       "--machine", str(machine),
       "--allow-device-reboot-recovery",
       "--no-dry-run",
       "--allow-parent-lock",  # Handoff ủy quyền từ parent
   ]
   ```
2. **Child CLI & Config Binding (`run_post.py`):**
   - Đăng ký argument `--allow-parent-lock` (action="store_true", default=False).
   - Truyền giá trị vào context config: `context.config["allow_parent_lock"] = bool(...)`.
3. **Child State Machine Non-Destructive Lease (`state_machine.py`):**
   - Tại state `_handle_acquire_locks`, kiểm tra `if self.context.config.get("allow_parent_lock") is True:`.
   - Gán `self.context.device_lease = _UnlockedDeviceLockLease()` (import từ `automation_core.device_lock`).
   - Ghi log xác nhận `[DEVICE_LOCK] parent-lock handoff accepted (machine=X)`.
   - `_UnlockedDeviceLockLease` có các phương thức (`release()`, `finish()`, `set_status()`) là no-op với `lock_paths=[]`, đảm bảo không ghi đè, không sửa đổi và không xoá file lock của parent khi child hoàn thành hoặc thoát (hoặc đơn giản gán `self.context.device_lease = None` nếu repo đã có các guard `if lease is not None`).

4. **Dual-Defense Fallback: Bắt Exception `DeviceLockNeedsUserDecision` Tự Động Kế Thừa (Case LOCK-05):**
   Phòng trường hợp parent runner chưa kịp update cờ `--allow-parent-lock`, child process BẮT BUỘC có lớp phòng thủ thứ hai ngay tại khối `except DeviceLockNeedsUserDecision as e:` (áp dụng chuẩn trên cả `tiktok-follow/follow_runner/run_follow.py` và `Tiktok-video/scripts/tiktok_workflow/state_machine.py`):
   ```python
   except DeviceLockNeedsUserDecision as exc:
       owner = getattr(exc, "owner", {}) or {}
       parent_project = str(owner.get("project") or "").strip().lower()
       # Nếu lock file thuộc về tiến trình cha nuôi feed hợp lệ:
       if parent_project in ("tiktok-luot nuoi acc", "tiktok-feed", "multi-machine-feed-session") or self.context.config.get("allow_parent_lock"):
           logger.info(
               f"[LOCK-INHERIT] Kế thừa device lock từ parent project '{parent_project}' (pid={owner.get('pid')}) cho machine={machine}, serial={device_id}"
           )
           self.context.device_lease = None
           return True
       raise WorkflowError(
           WorkflowState.ACQUIRE_LOCKS,
           f"Cần user quyết định cho device lock: {exc.describe()}",
           "NEEDS_USER_DECISION",
       )
   ```
   Cơ chế phòng vệ 2 lớp này đảm bảo 100% upload hooks và follow hooks không bao giờ bị fail hàng loạt khi chạy ngầm dưới parent feed session.

