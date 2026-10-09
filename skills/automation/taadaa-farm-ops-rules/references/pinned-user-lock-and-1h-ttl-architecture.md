# Pinned User Lock & 1-Hour TTL DeviceContext Architecture

## Context & Background
Khi người dùng trực tiếp ra lệnh thực thi (chạy Canary, test ad-hoc, chạy batch liên kết), tác vụ đó đại diện cho quyền cao nhất của Operator. Nếu tác vụ này chạy mà không có cơ chế Pinned Lock, các cronjob nền định kỳ (feed session, avatar upload, account switcher...) sẽ quét thấy thiết bị rảnh hoặc dùng quyền takeover để nhảy vào điều khiển máy, gây cướp foreground và phá vỡ phiên chạy của người dùng.

Đồng thời, theo chỉ đạo nghiêm ngặt của User:
1. **Lệnh của User là bất khả xâm phạm:** Không cronjob hay tiến trình ngầm nào được phép can thiệp/preempt trừ khi chính người dùng ra lệnh gỡ lock.
2. **Bảo tồn TTL 1 giờ tự động dọn dẹp:** Để ngăn chặn kịch bản treo máy hoặc crash tiến trình qua đêm gây deadlock vĩnh viễn, mọi lock (kể cả Pinned Lock) đều chịu sự giám sát của Reaper với trần thời gian 1 giờ (3600s).

---

## Architecture Implementation

### 1. Pinned Lock Schema (`automation_core/device_lock.py`)
Khi `acquire_device_lock` được gọi với `user_authorized=True`:
- Tự động gắn các trường metadata bảo vệ vào payload lock file:
  ```json
  {
    "user_authorized": true,
    "pinned": true,
    "last_heartbeat": "2026-09-19T22:50:00.000000+00:00",
    "ttl_seconds": 3600
  }
  ```
- **Quy tắc chặn Takeover:**
  Trong `_takeover_payload`, nếu target lock có `pinned: True` hoặc `user_authorized: True`, mọi request takeover từ các scope thông thường (`SAME_PROJECT_RECOVERY`, `FULL_SCOPE_TAKEOVER`) bị BÁC BỎ NGAY LẬP TỨC (`return None`).
  Chỉ duy nhất khi caller truyền `force_preempt=True` (tương đương `takeover_scope == TAKEOVER_SCOPE_OPERATOR_PREEMPT` - lệnh trực tiếp từ Operator) mới được phép reclaim.

### 2. Context Manager `DeviceContext`
Chuẩn hóa wrapper cho toàn bộ các script runner, canary hoặc batch do người dùng kích hoạt:
```python
from automation_core.device_lock import DeviceContext, DeviceLockNeedsUserDecision

# Tự động gắn pinned=True, user_authorized=True mặc định
with DeviceContext(serial=serial, machine=str(stt), project="operator-task", user_authorized=True) as lease:
    # Thiết bị được bảo vệ tuyệt đối trong suốt khối này
    ...
# Tự động giải phóng lock sạch sẽ khi ra khỏi block
```

### 3. Tự Động Dọn Dẹp Stale Lock (`reap-dead-owner-locks.py`)
Cronjob reaper chạy định kỳ mỗi 5 phút giám sát thư mục lock:
- **Nếu tiến trình chủ chết (`owner_alive is False`):** Thu hồi (reap) ngay lập tức về thư mục quarantine, không để lại orphan lock.
- **Nếu tiến trình chủ còn sống:**
  - Nếu `age_seconds < 3600s` (trong vòng 1h): **BẢO VỆ TUYỆT ĐỐI**, cấm reap.
  - Nếu `age_seconds >= 3600s` (vượt trần 1h): **BẮT BUỘC REAP** với lý do `pinned_1h_ttl` để giải phóng thiết bị cho các ca nuôi sau, triệt tiêu rủi ro deadlock farm qua đêm.
