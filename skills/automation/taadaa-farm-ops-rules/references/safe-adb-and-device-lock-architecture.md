# SafeAdb, AdbGuard & 3-Tier Rolling-Wait Architecture

## Bối cảnh & Vấn đề giải quyết
Trong hệ thống AI Coordinator (Hermes) điều phối Worker subagent thao tác trên Phone Farm (Samsung S7):
1. **Tranh chấp khóa thiết bị (DeviceLock Contention):**
   - Máy S7 thường xuyên chạy ca nuôi TikTok (15–30 phút) với lock cứng `pinned=True`.
   - Lệnh từ User/Operator tuyệt đối **CẤM force_preempt** phá lock làm gián đoạn cronjob.
2. **Nguy cơ Worker Timeout 600s:**
   - Worker là đơn vị thực thi ngắn (<2 phút). Nếu Worker gánh thêm việc chờ đợi máy bận (sleep 30s lặp lại) -> Cạn timeout 600s, chết subagent và đốt token vô ích.
3. **Lỗ hổng quên bọc Lock:**
   - LLM có thể quên bọc `DeviceContext` nếu chỉ dựa vào prompt/memory.

---

## Kiến trúc 3 tầng chuẩn (Decoupled Lifecycle)

```
User Lệnh ──> Coordinator PREFLIGHT check O(1)
                │
                ├──> Máy RẢNH: Dispatch Worker (thực thi <2 phút)
                │
                └──> Máy BẬN:
                       ├── KHÔNG dispatch worker (tiết kiệm 100% token)
                       ├── Enqueue vào TaskQueue (operator_task_queue.json)
                       └── Watchdog ngoài band (không phải LLM) poll & trigger khi nhả lock
```

### 1. Preflight O(1) trên Coordinator
Trước khi gọi `delegate_task`:
```python
from automation_core.task_queue import TaskQueue

tq = TaskQueue()
free, owner = tq.check_preflight_free(machine_id, serial)
if not free:
    # BÁO USER NGAY, KHÔNG DISPATCH WORKER:
    print(f"Máy {machine_id} đang bận ca nuôi {owner.get('project')}. Đã xếp hàng chờ cuốn chiếu.")
    tq.enqueue(machine_id, serial, task_name, payload)
    # DỪNG LẠI, KHÔNG GỌI delegate_task
```

### 2. Module SafeAdb (Enforcement ở tầng Code)
Vị trí: `D:/Taadaa/automation-core/src/automation_core/safe_adb.py`
- Tự động bọc `DeviceContext(force_preempt=False)`.
- Chặn đứng các lệnh ADB raw nếu chưa giữ lock (`LockNotHeldError`).

```python
from automation_core.safe_adb import SafeAdb, LockNotHeldError

safe_adb = SafeAdb(serial=serial, machine=machine, project="canary-task")
# BẮT BUỘC dùng context manager:
with safe_adb.acquire(timeout_seconds=30.0):
    res = safe_adb.shell("getprop", "ro.product.model")
```

### 3. Module AdbGuard (Monkey-patch Defense-in-depth)
Vị trí: `D:/Taadaa/automation-core/src/automation_core/adb_guard.py`
- Hook `subprocess.run`: Nếu phát hiện lệnh `adb -s <serial>` mà serial chưa nằm trong set các serial đang giữ lock -> Ném `LockNotHeldError` chặn đứng ngay lập tức!
- Sử dụng:
```python
from automation_core.adb_guard import install_adb_guard, uninstall_adb_guard

install_adb_guard()   # Kích hoạt chốt chặn ADB
# ...
uninstall_adb_guard() # Gỡ bỏ khi cần
```

---

## Bản chất 2FA: S7 vs GPM
1. **Trên Android S7:** Cổng bảo mật "Xác minh 2 bước" mở WebView mới -> Bị Google chặn cứng bằng reCAPTCHA (không có audio captcha solver trên Android).
2. **Trên GPM Chrome:** Có đầy đủ cookie session, cùng dải proxy 4G của máy S7 -> Google nhận diện tin cậy -> Cho qua thẳng hoặc chỉ qua reCAPTCHA (có audio captcha solver) -> Bật 2FA thành công 100% và bóc Base32 Secret Key vào Excel.
