# Device Lock Preflight & Rolling-Wait Policy (Anti-Cron-Preemption)

## Bối Cảnh & Nguyên Tắc Tối Cao
1. **Không Tin Trí Nhớ LLM / Memory:** Memory có thể bị trôi hoặc nén qua các turn compaction. Mọi ràng buộc an toàn thiết bị phải được enforce ở **tầng Code (SafeAdb / AdbGuard)** và **Quy trình Dispatch Coordinator**.
2. **CẤM PHÁ CRON (`force_preempt=False`):** Cronjob nuôi acc (TikTok feed, upload, follow, avatar) là tiến trình vận hành sống còn của farm. Mọi lệnh can thiệp của Coordinator/Worker (sửa script, canary, login GPM, lấy OTP) tuyệt đối không được giật lock hay kill tiến trình cron đang chạy.

---

## 1. Preflight Lock Check của Coordinator Trước Khi Dispatch
- **Vấn Đề:** Nếu dispatch worker vào máy đang bận, worker sẽ rơi vào blocking wait hoặc retry mù dẫn đến **Timeout 600s** và cạn ngân sách tool calls.
- **Giải Pháp:** Coordinator phải kiểm tra O(1) trạng thái lock của máy N trước khi gọi `delegate_task`:
```python
from automation_core.device_lock import inspect_device_lock, DeviceLockTransactionError

def is_machine_busy(machine_id: str | int) -> tuple[bool, dict | None]:
    try:
        info = inspect_device_lock(machine=str(machine_id))
        return True, info
    except DeviceLockTransactionError:
        return False, None
```
- **Hành Động Khi Máy Bận:**
  - **DỪNG DISPATCH NGAY.** Không tạo worker đứng chờ.
  - **Báo cáo User:** `Máy {N} đang bận chạy {project} (PID {pid}). Chuyển sang hàng đợi cuốn chiếu.`
  - **Xếp hàng cuốn chiếu:** Đăng ký task vào watchdog nền hoặc chờ cron kết thúc mới dispatch.

---

## 2. Pattern Code Chuẩn Cho Worker / Scripts
Mọi tương tác ADB với thiết bị Android bắt buộc tuân theo pattern:
```python
import sys
sys.path.insert(0, r"D:\Taadaa\automation-core\src")
from automation_core.device_lock import DeviceContext, DeviceLockUnavailable

serial = "988627414444594c51"
machine = "9"

try:
    with DeviceContext(serial=serial, machine=machine, project="operator-task", force_preempt=False) as lease:
        # THỰC HIỆN CÁC THAO TÁC ADB TẠI ĐÂY
        pass
except DeviceLockUnavailable as e:
    owner = e.owner
    print(f"⚠️ [MÁY {machine} BẬN] Bị khóa bởi {owner.get('project')} (PID {owner.get('pid')})")
    sys.exit(1)
```

---

## 3. Kiến Trúc Bảo Vệ Tầng Code: SafeAdb & AdbGuard
Để ngăn chặn hoàn toàn việc Worker hoặc mã nguồn tự do gọi `adb shell` trần ngoài lock:
1. **`SafeAdb` (`automation_core/safe_adb.py`):**
   - Class quản lý ADB gắn liền với context lock.
   - `with safe_adb.acquire(timeout_seconds=300):` tự động chạy rolling-wait (kiểm tra mỗi 10-30s), ném `TimeoutError` nếu quá hạn.
   - Nếu gọi `safe_adb.run(...)` khi chưa acquire lock -> ném `LockNotHeldError`.
2. **`AdbGuard` (`automation_core/adb_guard.py`):**
   - Monkey-patch `subprocess.run` để quét command chứa `"adb"` và `"-s <serial>"`.
   - Nếu phát hiện gọi ADB tới serial đang không được giữ lock trong context -> Chặn đứng ngay lập tức với `LockNotHeldError`.
