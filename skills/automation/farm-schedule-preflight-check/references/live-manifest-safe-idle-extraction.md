# Calculating Safe Idle S7 Machines from Live Manifest

## 1. Mục đích
Xác định danh sách máy Samsung S7 rảnh an toàn ($\ge 60$ hoặc $\ge 90$ phút tới không có slot nuôi acc TikTok) trực tiếp từ manifest ngày hiện tại, tránh xung đột lịch cron feed/upload.

## 2. Đường dẫn Manifest
- Thư mục: `D:\Taadaa\runtime\kibe\cron-state\manifests\<YYYY-MM-DD>\`
- Tập tin phân bổ: `assignment-v1-<hash>.json`

## 3. Mẫu code trích xuất máy rảnh an toàn:
```python
import json
from datetime import datetime, timedelta

manifest_path = r"D:\Taadaa\runtime\kibe\cron-state\manifests\2026-09-12\assignment-v1-811404fabb06c14cb7aa7c582b75a4ac.json"
with open(manifest_path, "r", encoding="utf-8") as f:
    data = json.load(f)

entries = data.get("entries", [])
now = datetime.now()

# Đệm an toàn 60 - 90 phút
SAFE_BUFFER_MINUTES = 90
busy_machines = set()

for e in entries:
    st = datetime.fromisoformat(e["slot_time"]).replace(tzinfo=None)
    et = datetime.fromisoformat(e["slot_end"]).replace(tzinfo=None)
    
    # Máy đang trong slot chạy hoặc sắp bắt đầu trong buffer
    if (st <= now <= et) or (now <= st <= now + timedelta(minutes=SAFE_BUFFER_MINUTES)):
        busy_machines.add(e["machine"])

all_machines = set(range(1, 81))
safe_idle_machines = sorted(all_machines - busy_machines)
print(f"Safe Idle Machines (>={SAFE_BUFFER_MINUTES}m buffer): {safe_idle_machines}")
```

## 4. Kiểm tra chéo trạng thái thiết bị qua ADB
Sau khi có danh sách máy rảnh lịch, kiểm tra thực tế trên thiết bị trước khi dispatch:
```bash
adb -s <serial> shell dumpsys window windows | grep -E "mCurrentFocus|mFocusedApp"
```
BẮT BUỘC thiết bị phải ở màn hình chính (`com.sec.android.app.launcher.activities.LauncherActivity`).
