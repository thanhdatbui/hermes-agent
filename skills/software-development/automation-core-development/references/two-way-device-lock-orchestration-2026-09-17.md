# Hai chiều Device Lock giữa Ca Nuôi (Batch) và Operator Tool (2026-09-17)

## Bối cảnh & Mục tiêu
Giải quyết bài toán tranh chấp thiết bị farm 2 chiều giữa ca nuôi định kỳ (`multi-machine-feed-session`) và các script can thiệp/bảo trì ngoài band của operator (`tools/*.py`):
1. **Chiều 1:** Operator lock máy để làm script can thiệp -> Ca nuôi đến giờ chạy phải tự động bỏ qua máy đó (Clean Skip), không được biến cả batch thành `ExitStatus.MANUAL_NEEDED` (exit code 2).
2. **Chiều 2:** Ca nuôi đang chạy -> Operator chạy script can thiệp thì script phải tự động chờ (wait/poll có timeout) cho tới khi ca nuôi kết thúc và nhả lock, đồng thời tự chiếm lock độc quyền để chạy an toàn.

---

## Kiến trúc & Hợp đồng Concurrency

### 1. `automation_core.device_lock`
- **`wait_for_device_lock(*, machine, serial, project, timeout=300.0, poll_interval=5.0, ...)`**:
  - Polling loop với deadline `time.monotonic() + timeout`.
  - **Bẫy PID Reuse & Stale Lock:** Nếu bắt được `(DeviceLockUnavailable, DeviceLockNeedsUserDecision)`, dùng `_owner_process_alive(last_owner)` để so khớp `process_started_at`. Nếu PID đã chết, tự dọn stale lock files và retry ngay.
  - **Structured Exception:** Hết thời gian chờ ném `DeviceLockTimeoutError` (chứa `machine`, `serial`, `owner`, `waited_seconds`).
- **`operator_device_lock(*, machine, serial, project="operator_tool", timeout=300.0, ...)`**:
  - Context manager chuẩn: acquire chờ lock -> yield lease -> tự động `release()` trong `finally` nếu `release_on_terminal=True`.

### 2. Consumer Feed Session (`tiktok-luot nuoi acc`)
- **Preflight PowerShell (`scripts/run-feed-session.ps1`)**:
  - Lọc bỏ ngay các máy có lock sống khỏi `$machineList` trước khi truyền vào `run_tiktok.py`.
  - Nếu tất cả máy đều bị lock: Clean exit (`exit 0`), không báo đỏ runner.
- **Batch Aggregator (`multi_machine_feed_session.py:_aggregate_rows`)**:
  - Tách rành mạch `needs-user-decision` (xung đột cần quyết định -> `MANUAL_NEEDED`) khỏi `skipped-device-locked` (skip do operator lock).
  - Nếu có máy thành công và một số máy `skipped-device-locked` -> Trả về `ExitStatus.SUCCESS` ("multi-machine-feed-session completed with some locked machines cleanly skipped").
  - Chỉ khi 100% máy bị lock mới trả `MANUAL_NEEDED`.

### 3. CLI Wrapper cho Operator (`D:/Taadaa/tools/with_device_lock.py`)
Mọi tool can thiệp ngoài band không cần sửa code bên trong, chỉ cần bọc ngoài bằng wrapper:
```bash
python D:/Taadaa/tools/with_device_lock.py --machine 12 -- python D:/Taadaa/tools/upgrade_tiktok.py 12
python D:/Taadaa/tools/with_device_lock.py --machine 5 --timeout 600 --project "fix_acc" -- python script.py
```
Wrapper tự động: Chờ ca nuôi nhả lock -> Giữ lock độc quyền -> Thực thi lệnh con -> Auto-release an toàn khi kết thúc hoặc crash/Ctrl+C.
