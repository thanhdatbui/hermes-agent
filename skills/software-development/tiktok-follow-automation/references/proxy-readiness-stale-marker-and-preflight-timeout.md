# Proxy Readiness Timeout do Stale Marker (~/.codex/device-readiness)

## 1. Hiện tượng & Triệu chứng
Khi chạy canary follow hoặc khởi động phiên follow cho một máy (ví dụ Máy 51 `ce0616063df1094004`), runner lập tức fail-closed ở tầng preflight với log:
```text
BLOCKED: preflight device-lock/VPN fail-closed: proxy readiness timed out for <serial>
```
Tiến trình con bị chặn trước khi chạm vào TikTok UI, màn hình máy không có hành động.

## 2. Bản chất & Nguyên nhân gốc rễ (Root Cause)
1. **Mạng và Proxy thực tế vẫn 100% bình thường:**
   - Wi-Fi trên máy vẫn `COMPLETED`, RSSI tốt (-40 đến -50 dBm).
   - Global proxy trên máy vẫn trỏ đúng `192.168.110.2:200XX` (Singbox mixed inbound).
   - Test egress IP qua proxy bằng cả PC (`curl -x http://192.168.110.2:200XX http://api.ipify.org`) và shell điện thoại (`toybox nc`) đều trả về HTTP 200 OK kèm public IP.
2. **Kẹt Stale Marker trong Device Readiness:**
   - Trong `automation-core/src/automation_core/device_lock.py`, khi gọi `acquire_device_lock(..., status="running")`:
     ```python
     if serial and not bypass_proxy_readiness and normalized_status != "queued":
         readiness_proof = wait_for_proxy_ready(serial, timeout=readiness_timeout, ...)
     ```
   - Hàm `wait_for_proxy_ready()` đọc file trạng thái tại:
     `~/.codex/device-readiness/<safe_hash>.json`
     với `safe_hash = hashlib.sha256(serial.encode("utf-8")).hexdigest()[:24]`.
   - Nếu trước đó thiết bị từng reboot hoặc chạy watcher cũ và để lại marker:
     ```json
     {
       "serial": "<serial>",
       "state": "proxy_pending",
       "boot_id": "...",
       "updated_at": "2026-08-30T03:01:44.639744+00:00"
     }
     ```
     marker này đã tồn tại nhiều ngày/tuần nhưng không có watcher nào cập nhật sang `proxy_ready`.
   - Do `read_readiness(serial)` trả về một dict có `state == "proxy_pending"`, `wait_for_proxy_ready` rơi vào vòng lặp chờ polling cho đến khi hết `timeout=180.0`s và raise `TimeoutError(f"proxy readiness timed out for {serial}")`.

## 3. Quy trình Chẩn đoán & Xử lý Nhanh (O(1))

### Bước 1: Kiểm tra kết nối Wi-Fi & Proxy thực tế
```bash
# Binary ADB chuẩn trên host Kibe
export ADB="C:/Program Files (x86)/xiaowei/tools/adb.exe"

# Kiểm tra Wi-Fi & Global proxy trên máy
"$ADB" -s <serial> shell "dumpsys wifi | grep mWifiInfo"
"$ADB" -s <serial> shell "settings get global http_proxy"

# Kiểm tra Egress IP trực tiếp qua proxy port
curl -s -m 10 -x http://192.168.110.2:<PORT> http://api.ipify.org
```

### Bước 2: Kiểm tra và giải phóng file device-readiness stale
Chạy Python one-liner kiểm tra và update marker lên `proxy_ready`:
```python
import sys
sys.path.insert(0, "D:/Taadaa/automation-core/src")
from automation_core.readiness import mark_proxy_state, read_readiness, wait_for_proxy_ready

serial = "<serial>"
print("Current readiness:", read_readiness(serial))

# Nếu stale (state="proxy_pending" cũ): cập nhật ngay sang proxy_ready
mark_proxy_state(serial, "proxy_ready")
print("Verified:", wait_for_proxy_ready(serial, timeout=5))
```

### Bước 3: Kiểm tra và Reset Cooldown State trước khi chạy Canary
Nếu nick trên máy từng dính `FOLLOW_FAILED` vào ngày trước đó hoặc trong ngày:
- Mở `D:/Taadaa/tiktok-follow/runs/state/follow_state_<M>_row_<slot>.json`.
- Nếu `follow_failed: true`: runner sẽ short-circuit ngay khi mở phiên mà không thao tác device.
- Reset `data["follow_failed"] = False` và lưu file json để canary có thể thực thi live action.

### Bước 4: Chạy Canary an toàn với `--force-preempt`
Khi máy đang bị tiến trình batch cha giữ lock ở trạng thái `queued_v2`:
```bash
cd /d/Taadaa/tiktok-follow
export PYTHONPATH="D:/Taadaa/tiktok-follow;D:/Taadaa/automation-core/src"
/d/Taadaa/python-envs/automation/Scripts/python.exe -m follow_runner.run_follow \
    --machine <M> \
    --account-row-index <slot> \
    --config config/machine<M>.yaml \
    --force-preempt
```
Lệnh sẽ chiếm quyền điều khiển (operator preempt), bỏ qua lock hàng đợi, và chạy thẳng canary follow.
