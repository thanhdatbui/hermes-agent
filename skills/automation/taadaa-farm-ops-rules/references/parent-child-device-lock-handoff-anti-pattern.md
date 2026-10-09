# Anti-Pattern: Parent Process Locks Out Child Recovery Subprocess (Device Lock Self-Deadlock)

## 1. Hiện tượng & Triệu chứng
Trong các luồng tự động phục hồi (auto-recovery / auto-reconcile) giữa chừng khi đang chạy job chính (ví dụ `multi_machine_feed_session` phát hiện thiếu tài khoản trong switcher và gọi `reconcile_tiktok_accounts.py` để đăng nhập bù):
- Quá trình chạy lướt feed phát hiện thiếu nick, kích hoạt hook phục hồi `_maybe_recover_missing_account_via_login`.
- Subprocess con kết thúc gần như ngay lập tức (~2 giây) với `returncode = 4` (hoặc exit code báo lỗi lock).
- File kết quả summary của subprocess con (ví dụ `tiktok-account-reconcile-*.json`) ghi nhận:
  ```json
  "status": "SKIPPED_LOCKED",
  "reason": "device lock active: path=C:\\Users\\Kibe\\.codex\\device-locks\\machine_<N>.lock.json pid=<PID_CHA> host=... project=tiktok-luot nuoi acc status=running ..."
  ```
- Tiến trình cha nhận `returncode != 0`, kết luận phục hồi thất bại và rơi vào nhánh fallback cuối cùng: `manual-needed: profile username still mismatched after switch` kèm trạng thái giữ lock `blocked` (TTL 1h).

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Tiến trình cha đang giữ active lock:**
   Tiến trình cha (`run_tiktok.py` PID cha) đã acquire device lock từ đầu phiên với trạng thái `status: "running"`, `owner_active: true`.
2. **Subprocess con không thể cướp lock của cha đang sống:**
   Khi cha gọi `subprocess.run(["...reconcile_tiktok_accounts.py", "--machines", str(machine), "--allow-live-reconcile", "--full-scope-takeover"])`:
   - Subprocess con là một process OS độc lập (PID riêng).
   - Con gọi `acquire_device_lock(machine=..., allow_takeover=True, takeover_scope="FULL_SCOPE_TAKEOVER")`.
   - `automation_core.device_lock` kiểm tra chủ sở hữu hiện tại:
     ```python
     alive = _owner_process_alive(owner)
     elif owner_status in _WIRE_ACTIVE_DEVICE_LOCK_STATUSES: # ("running", "recovery")
         if alive is not False:
             return None
     ```
   - Do PID cha VẪN ĐANG SỐNG (`alive == True`) và đang ở trạng thái `running`, cờ `--full-scope-takeover` **tuyệt đối từ chối** chiếm quyền từ tiến trình đang hoạt động (để bảo vệ chống tranh chấp đồng thời).
   - Subprocess con nhận ngoại lệ `DeviceLockUnavailable`, đánh dấu `SKIPPED_LOCKED` và thoát với mã lỗi 4.

## 3. Quy chuẩn Khắc phục Chuẩn hóa (Standard Patterns)
Để subprocess con có thể can thiệp vào thiết bị mà cha đang giữ lock, bắt buộc áp dụng một trong hai cơ chế sau:

### Pattern A: Lock Handoff Lifecycle (Khuyến nghị cho recover cùng repo / shared core)
Trước khi gọi subprocess, tiến trình cha chuyển tạm thời trạng thái lock sang trạng thái chuyển giao `handoff`:
```python
# 1. Cha tạm hạ active status sang handoff
lease.set_status("handoff")
try:
    # 2. Chạy subprocess con với quyền takeover
    proc = subprocess.run(cmd, ...)
finally:
    # 3. Cha reclaim lại quyền điều khiển
    lease.set_status("running")
```

### Pattern B: Kế thừa Lock Lease Token / Skip Lock cho Recovery Hook (Chuẩn Case LOCK-05)
Giống như cơ chế đã triển khai giữa `tiktok-luot nuoi acc` và `tiktok-follow` (`--skip-identity-verify`):
- Subprocess con nhận tham số báo hiệu được gọi từ tiến trình cha hợp lệ (ví dụ `--parent-pid <PID>` hoặc cờ `--recovery-hook` / `--inherited-lease`).
- Subprocess con kiểm tra nếu lock hiện tại trên máy thuộc về chính PID cha đã sinh ra nó thì cho phép kế thừa quyền truy cập thiết bị mà không tự block chính mình.
- Hoặc nếu dùng takeover có thẩm quyền, truyền `force_preempt=True` / `TAKEOVER_SCOPE_OPERATOR_PREEMPT` nếu subprocess được ủy quyền cưỡng chế.
