# Fast Targeted Auto-Login & Parent Device Lock Inheritance

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ (Incident Pattern M32)

- **Hiện tượng**: Trong ca nuôi/lướt feed (ví dụ Ca 2 Row 3), một máy dừng với mã lỗi `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`. Kiểm tra UI XML thực tế cho thấy máy đang thiếu đúng 1 nick mục tiêu (ví dụ M32 có 7/8 nick, thiếu slot 3 `thanhlee327`).
- **Cơ chế tự phục hồi lý thuyết**: Runner nuôi (`feed_swipe_smoke.py`) có hàm `_run_fast_targeted_login` tự động gọi script đăng nhập nhanh:
  ```bash
  python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <EXPECTED_ID> --ss
  ```
- **Cạm bẫy va chạm Device Lock (Lock Collision Trap)**:
  - Khi `multi-machine-feed-session` chạy, tiến trình cha `run_tiktok.py` đang nắm giữ lock file vật lý: `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`.
  - Nếu `tiktok_login_v1.py` khởi chạy mà không có cơ chế kế thừa lock, lệnh `acquire_device_lock` phát hiện PID khác đang giữ máy và lập tức ném ngoại lệ:
    `DeviceLockNeedsUserDecision: device lock active: path=... pid=... project=tiktok-luot nuoi acc machine=<N>`
  - Tiến trình fast login thoát ngay với mã lỗi 2.
  - Runner tiếp tục fallback sang `reconcile_tiktok_accounts.py`, nhưng do reconcile quét diện rộng và chạy nặng, phiên bị timeout sau 300s và fail-closed dừng máy.

---

## 2. Invariant Thiết Kế: Cờ `--allow-parent-lock` & Contract `InheritedDeviceLock`

### A. Phía Caller (`feed_swipe_smoke.py`)
Khi gọi subprocess `tiktok_login_v1.py`, caller BẮT BUỘC truyền cờ `--allow-parent-lock`:
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

### B. Phía Target CLI (`tiktok_login_v1.py`)
1. **Whitelist Parent Projects**:
   Chỉ cho phép kế thừa lock khi project của owner đang giữ lock thuộc danh sách hợp lệ:
   ```python
   PARENT_LOCK_PROJECTS = (
       "tiktok-luot nuoi acc",
       "tiktok-feed",
       "multi-machine-feed-session",
   )
   ```
2. **Kiểm tra Ownership**:
   Hàm `_is_parent_lock_owner(exc)` bóc tách `exc.owner` (hỗ trợ cả dict và object), trích xuất `project` và `pid`. Nếu `parent_project in PARENT_LOCK_PROJECTS`, cho phép kế thừa.
   Nếu project lạ (unauthorized tool) hoặc user lock riêng biệt -> giữ nguyên fail-closed `NEEDS_USER_DECISION` (exit code 2).

3. **Contract Đầy Đủ của `InheritedDeviceLock` (Thay thế stub rỗng)**:
   Để tương thích 100% với `DeviceLockLease` và vượt qua Closeout Gate (Sol Auditor $\ge 85$ điểm), `InheritedDeviceLock` phải triển khai đầy đủ các thuộc tính và phương thức sau:
   - **Thuộc tính**:
     * `machine`: STT máy (int/str).
     * `serial`: Serial thiết bị ADB.
     * `parent_project`: Tên project cha sở hữu lock gốc.
     * `parent_pid`: PID của tiến trình cha.
     * `lock_id`: Mã định danh phiên kế thừa duy nhất (ví dụ `f"inherited-{os.urandom(4).hex()}"`).
     * `status`: Trạng thái lease, mặc định `'running'`.
     * `released`: Boolean cờ giải phóng lease.
     * `acquired_at`: Timestamp bắt đầu kế thừa.
     * `released_at`: Timestamp kết thúc kế thừa.
     * `lifecycle_events`: Danh sách lưu trữ telemetry trong phiên.
   - **Phương thức & Telemetry Invariant**:
     * `set_status(status)`: Chuẩn hóa chữ thường, kiểm tra nằm trong `{'queued', 'running', 'recovery', 'handoff', 'blocked', 'temporarily_skipped'}`. Cập nhật `self.status` và log:
       `[device-lock] [telemetry] action=set_status lock_id=... machine=... serial=... parent=... pid=...`
     * `mark_reg_success_today(*, today=None)`: Gọi `record_machine_reg_success(self.machine, serial=self.serial, success_date=today)` có try/except bọc ngoài để tránh crash phiên login.
     * `is_daily_reg_cooldown_active(*, today=None)`: Gọi `is_machine_reg_cooldown_active(str(self.machine), today=today)` có try/except an toàn.
     * `release()`: Nếu chưa release, bật `self.released = True`, gán `self.released_at = time.time()`, tính duration và ghi telemetry `action=released`.

---

## 3. Unit Test Pattern Cho Parent Lock Inheritance

Mọi thay đổi liên quan đến `InheritedDeviceLock` BẮT BUỘC có test coverage cho các trường hợp:
1. `test_parse_args_allow_parent_lock`: Cờ `--allow-parent-lock` được parse đúng, default là `False`.
2. `test_is_parent_lock_owner_allowed_projects`: Mọi project trong `PARENT_LOCK_PROJECTS` đều trả về `(True, project, pid)`.
3. `test_is_parent_lock_owner_disallowed_project`: Project lạ trả về `False`.
4. `test_inherited_device_lock_full_lifecycle_and_telemetry`: Thử nghiệm toàn bộ chu trình `acquired` $\to$ `set_status` $\to$ `mark_reg_success_today` $\to$ `release`, xác nhận `lifecycle_events` ghi nhận đủ và duration được tính toán.
5. `test_inherited_device_lock_invalid_status_raises`: Ném `ValueError` khi truyền status ngoài whitelist.
6. `test_inherited_device_lock_cooldown_and_reg_success`: Mock `is_machine_reg_cooldown_active` và `record_machine_reg_success` để kiểm chứng tương thích logic farm mà không phụ thuộc dữ liệu đĩa thật.
7. `test_main_fails_without_allow_parent_lock_when_locked`: Không có cờ `--allow-parent-lock` $\to$ returncode 2.
8. `test_main_fails_when_locked_by_unauthorized_project_even_with_flag`: Có cờ nhưng parent project không nằm trong whitelist $\to$ returncode 2.
9. `test_main_succeeds_lock_stage_with_allow_parent_lock`: Có cờ và parent project hợp lệ $\to$ kế thừa thành công và đi tiếp vào luồng xử lý tài khoản.
