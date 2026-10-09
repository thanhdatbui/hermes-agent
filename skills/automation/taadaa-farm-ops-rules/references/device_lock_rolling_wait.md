# Device Lock Enforcement & Rolling-Wait Pattern

## Quy tắc cốt lõi
1. Mọi lệnh/script chạm ADB vào máy S7 BẮT BUỘC bọc trong `DeviceContext(force_preempt=False)`.
2. TUYỆT ĐỐI CẤM `force_preempt=True` khi user/operator phát lệnh can thiệp.
3. Nếu gặp `DeviceLockUnavailable`:
   - BẮT BUỘC log/báo về: Machine đang bận bởi project nào (`e.owner.get('project')`), PID nào.
   - TUYỆT ĐỐI KHÔNG phá lock cron (không giật máy làm hỏng ca nuôi TikTok hay reg).
   - Tự động vào vòng lặp chờ cuốn chiếu (rolling-wait) hoặc báo về Coordinator để xếp hàng chờ máy rảnh.
4. Cơ chế phải được enforce ở tầng code (`SafeAdb` wrapper / guard hook), không dựa vào trí nhớ LLM.

## Code mẫu chuẩn
```python
from automation_core.device_lock import DeviceContext, DeviceLockUnavailable

try:
    with DeviceContext(serial=serial, machine=str(machine_id), project="operator-task", force_preempt=False) as lease:
        # Thao tác ADB an toàn tại đây
        pass
except DeviceLockUnavailable as e:
    owner = e.owner
    print(f"⚠️ [MÁY {machine_id:02d} ĐANG BẬN] Lock active bởi project='{owner.get('project')}' (PID={owner.get('pid')})!")
    print(f"⏳ Không phá lock cron. Đã chuyển task vào hàng đợi canh máy hết lock để chạy cuốn chiếu.")
```
