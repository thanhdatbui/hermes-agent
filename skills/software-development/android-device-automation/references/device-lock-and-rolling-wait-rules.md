# Device Lock Protocol & Rolling-Wait Rules for Farm S7

## 1. Nguyên tắc cốt lõi: Bắt buộc Lock & Cấm phá Lock Cron
Khi User hoặc Coordinator phát lệnh can thiệp vào thiết bị Samsung S7 (chạy script, sửa code, canary test, login tài khoản, lấy mã OTP...):
1. **MỌI THAO TÁC CHẠM ADB PHẢI BỌC TRONG `DeviceContext`:**
   ```python
   import sys
   sys.path.insert(0, r"D:\Taadaa\automation-core\src")
   from automation_core.device_lock import DeviceContext, DeviceLockUnavailable

   serial = "988627414444594c51"
   machine_id = "9"
   task_name = "operator-login-task"

   try:
       # ⚠️ TUYỆT ĐỐI CẤM force_preempt=True khi user/operator chạy lệnh can thiệp
       with DeviceContext(serial=serial, machine=machine_id, project=task_name, force_preempt=False) as lease:
           # THỰC THI THAO TÁC ADB AN TOÀN TẠI ĐÂY
           ...
   except DeviceLockUnavailable as e:
       owner = e.owner
       # BÁO CÁO MINH BẠCH: Không được raise im lặng, không được giật máy
       print(f"⚠️ [MÁY {machine_id} BUSY] Đang bị khóa bởi project='{owner.get('project')}' (PID={owner.get('pid')})!")
       print(f"⏳ Cấm phá lock cron. Chuyển sang cơ chế canh máy hết lock để chạy cuốn chiếu (rolling-wait).")
   ```

2. **TUYỆT ĐỐI CẤM `force_preempt=True`:**
   - Lệnh của User/Coordinator KHÔNG ĐƯỢC PHÉP cướp máy hay phá vỡ session cron đang chạy (nuôi TikTok, feed session, avatar watchdog...).
   - Bất kỳ hành vi phá lock nào cũng gây lỗi văng app, mất phiên hoặc hỏng dữ liệu phiên nuôi của farm.

## 2. Mô hình Canh Cuốn Chiếu (Rolling-Wait Pattern)
Khi gặp `DeviceLockUnavailable`, Coordinator/Worker thực thi vòng lặp chờ máy rảnh:
```python
import time

def run_when_device_free(serial: str, machine_id: str, task_fn, poll_interval=30, max_wait=3600):
    start_t = time.time()
    while time.time() - start_t < max_wait:
        try:
            with DeviceContext(serial=serial, machine=machine_id, project="rolling-operator", force_preempt=False):
                return task_fn()
        except DeviceLockUnavailable as e:
            owner = e.owner
            print(f"Máy {machine_id} đang bận bởi {owner.get('project')}. Chờ {poll_interval}s trước khi thử lại...")
            time.sleep(poll_interval)
    raise TimeoutError(f"Máy {machine_id} vẫn bận sau {max_wait}s.")
```

## 3. Checklist Điều Phối Trước Khi Dispatch Worker
- [ ] Script của worker đã import và bọc code ADB trong `DeviceContext` chưa?
- [ ] Có tham số `force_preempt=True` trái phép không? (Nếu có -> Xóa ngay).
- [ ] Đã có khối `try...except DeviceLockUnavailable` để bắt và báo cáo trạng thái máy bận chưa?
