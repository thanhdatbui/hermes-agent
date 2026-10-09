# Auto-Login Recovery Parent-Child Device Lock Deadlock (SKIPPED_LOCKED / Return Code 4)

## Triệu chứng
Trong phiên lướt feed (`multi_machine_feed_session` / `feed_swipe_smoke.py`), khi phát hiện tài khoản mục tiêu thiếu trong switcher, runner kích hoạt hook phục hồi tự động `_maybe_recover_missing_account_via_login()` (Case 74).
Subprocess gọi `reconcile_tiktok_accounts.py` kết thúc chỉ sau 2 giây với mã lỗi `returncode: 4`.
Log đối soát `tiktok-account-reconcile-*.json` ghi nhận:
```json
{
  "machine": 40,
  "status": "SKIPPED_LOCKED",
  "reason": "device lock active: path=C:\\Users\\Kibe\\.codex\\device-locks\\machine_40.lock.json pid=182096 host=... project=tiktok-luot nuoi acc machine=40 serial=... command=run_tiktok.py --mode multi-machine-feed-session reservation"
}
```
Luồng chính coi reconcile thất bại $\rightarrow$ rơi vào fallback `manual-needed: profile username still mismatched after switch` và giữ lock `blocked` (TTL 1h).

## Nguyên nhân gốc rễ
1. **Lỗi "Cha khóa cửa con"**: Tiến trình cha (`run_tiktok.py` PID 182096) đang giữ active device lock (`status: "running"`, `owner_active: true`).
2. Subprocess con (`reconcile_tiktok_accounts.py`) là process độc lập, gọi `acquire_device_lock(machine=40, allow_takeover=True, takeover_scope="FULL_SCOPE_TAKEOVER")`.
3. Trong `automation_core.device_lock`:
   - Hàm `_takeover_payload()` kiểm tra chủ sở hữu: nếu `owner_status in _WIRE_ACTIVE_DEVICE_LOCK_STATUSES` ("running", "recovery") và `alive is not False` (PID cha vẫn sống) $\rightarrow$ trả về `None` (từ chối takeover).
   - `--full-scope-takeover` CHỈ cho phép chiếm quyền trên các lock không hoạt động (`inactive`) hoặc dead PID; nó tuyệt đối không cướp lock từ tiến trình đang active để tránh xung đột concurrent.
   - Do đó, script con bắt `DeviceLockUnavailable`, gán trạng thái `SKIPPED_LOCKED` và exit code 4.

## Giải pháp chuẩn hóa
1. **Pattern Handoff (Khuyến nghị)**: Trước khi cha spawn subprocess login reconcile, tạm thời chuyển lease sang `status = "handoff"`:
   ```python
   # Trong feed_swipe_smoke.py
   lease.set_status("handoff")
   try:
       proc = subprocess.run(cmd, ...)
   finally:
       lease.set_status("running")
   ```
2. **Pattern Kế thừa Lease / Bypass (Chuẩn Case LOCK-05 — Đã chuẩn hóa)**:
   - Thêm cờ `--allow-parent-lock` (action="store_true") vào parser (`build_parser()` trong `login_runner/account_reconcile.py`).
   - Khai báo danh sách project cha hợp lệ:
     ```python
     PARENT_LOCK_PROJECTS = (
         "tiktok-luot nuoi acc",
         "tiktok-feed",
         "multi-machine-feed-session",
     )
     ```
   - Định nghĩa `InheritedDeviceLock`: dummy/noop lease object implement các method `set_status`, `finish`, `release`, `release_with_audit`, `__enter__`, `__exit__` không can thiệp hay giải phóng lock của tiến trình cha.
   - Trong `main()` (vòng reservation ban đầu) và `reconcile_target()` (vòng chạy worker):
     - Khi bắt `(DeviceLockUnavailable, DeviceLockNeedsUserDecision)`:
       Nếu `allow_parent_lock` bật và `(exc.owner or {}).get("project")` nằm trong `PARENT_LOCK_PROJECTS`:
       Cho phép target tiếp tục thực thi với `lease = InheritedDeviceLock()` thay vì gán `SKIPPED_LOCKED` / `NEEDS_USER_DECISION`.
   - Trong tiến trình cha (`python_runner/flows/feed_swipe_smoke.py` hàm `_maybe_recover_missing_account_via_login`):
     Bổ sung `"--allow-parent-lock"` vào command list `cmd` khi gọi `reconcile_tiktok_accounts.py`.
