# Safe ADB, DeviceLock Enforcement & Preflight Queue Architecture

## 1. Vấn đề cốt lõi (Root Cause)
- **Worker Timeout do tranh chấp lock:** Worker subagent là đơn vị thực thi ngắn hạn (<2 phút, giới hạn timeout 600s). Khi máy Android đang bận chạy batch/cronjob dài (15–30 phút như TikTok feed session), nếu Worker đứng chờ rolling-wait trong loop `sleep(30s)`, Worker sẽ bị timeout 600s, vừa fail task vừa đốt token LLM vô ích.
- **Phá lock là vi phạm Invariant:** Tuyệt đối KHÔNG ĐƯỢC dùng `force_preempt=True` để giật máy khi cron đang chạy, vì sẽ làm gãy ca nuôi, văng app, và hỏng phiên làm việc của farm.
- **LLM Memory/Prompt không đáng tin:** Ghi nhớ vào prompt/memory rất dễ bị trôi sau khi context compaction. BẮT BUỘC phải enforce bằng Code Layer và Infrastructure Guard.

---

## 2. Kiến trúc 3 tầng chuẩn (Decoupling Waiting vs Execution)

```
User / Coordinator phát lệnh can thiệp thiết bị
               │
               ▼
   [TẦNG 1: Coordinator Preflight Probe O(1)]
   TaskQueue.check_preflight_free(machine, serial)
               │
      ┌────────┴────────┐
      │                 │
   [MÁY RẢNH]      [MÁY ĐANG BẬN CRON]
      │                 │
      ▼                 ▼
Spawn Worker      KHÔNG spawn Worker! (Tiết kiệm 100% token)
(<2 phút xong)    Đẩy task vào [TẦNG 2: Persistent Task Queue]
                        │
                        ▼
                  Báo ngay cho User: "Máy N bận cron [project], đã xếp hàng"
                        │
                        ▼
                  [TẦNG 3: Watchdog Dispatcher ngoài band]
                  (Script Python nền, poll 30s/lần, không tốn token)
                  Khi máy nhả lock ──> Kích hoạt Worker thực thi!
```

---

## 3. Các thành phần kỹ thuật trong `automation-core`

### 3.1. `SafeAdb` (`automation_core.safe_adb`)
- Drop-in wrapper cho ADB, hardcoded `force_preempt=False`.
- Mọi câu lệnh ADB bắt buộc phải nằm trong khối `with safe_adb.acquire():`.
- Nếu gọi `run()` hoặc `shell()` ngoài context -> Ném `LockNotHeldError`.

```python
from automation_core.safe_adb import SafeAdb, LockNotHeldError

safe_adb = SafeAdb(serial="988627414444594c51", machine="9", project="gpm-login")
try:
    with safe_adb.acquire(timeout_seconds=60.0):
        # Thiết bị đã được cô lập an toàn
        output = safe_adb.shell("getprop", "ro.product.model")
except TimeoutError as exc:
    # Bắt khi quá hạn mà máy vẫn bận
    print(f"Device busy: {exc}")
```

### 3.2. `AdbGuard` (`automation_core.adb_guard`)
- Monkey-patch hàm `subprocess.run` để chặn đứng các câu lệnh raw ADB (`subprocess.run(["adb", "-s", serial...])`) nếu serial đó chưa được bọc trong DeviceLock active.

```python
from automation_core.adb_guard import install_adb_guard, uninstall_adb_guard

# Kích hoạt guard khi process khởi động
install_adb_guard()
```

### 3.3. `TaskQueue` (`automation_core.task_queue`)
- Quản lý hàng đợi tác vụ bền vững tại `C:/Users/Kibe/.codex/device-locks/operator_task_queue.json`.
- Cung cấp hàm preflight `check_preflight_free(machine, serial)` kiểm tra lock O(1) qua `inspect_device_lock`:
  - `(True, None)`: Máy rảnh.
  - `(False, owner_dict)`: Máy bận, kèm thông tin project và PID đang giữ lock.

---

## 4. Invariants cho Coordinator & Worker

1. **Coordinator Preflight Invariant:** Trước khi dispatch bất kỳ worker nào thao tác ADB tới máy N, Coordinator BẮT BUỘC chạy `TaskQueue.check_preflight_free(machine)`.
   - Nếu máy bận: CẤM dispatch worker. Enqueue task và báo cáo user.
2. **Worker Fail-Fast Invariant:** Nếu worker nhận task mà phát hiện máy bận (`DeviceLockUnavailable`), PHẢI thoát ngay trong 3 giây (Fail-Fast), trả về mã `DEVICE_BUSY` để Coordinator đưa vào Queue. CẤM sleep ngâm budget chờ lock.
3. **No Force Preempt:** Tuyệt đối không bao giờ phá lock đang active của cron.
