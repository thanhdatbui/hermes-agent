# WiFi Disconnect → blocked-vichanger-vpn → Keyguard Lock (2026-09-03)

## Triệu chứng
- Máy bị khóa màn hình (Keyguard `showing=true`), không thấy chạy.
- Device lock file tồn tại: `status: blocked`, `owner_active: false`.
- Run artifact `final_status: blocked-vichanger-vpn`.

## Root Cause Chain
1. **WiFi mất kết nối** trên thiết bị (`mWifiInfo SSID: <unknown ssid>`, `Supplicant state: DISCONNECTED`).
2. Preflight `require_vichanger_connected` kiểm tra proxy router → không reach được → emit `stop_reason: "required router proxy is unreachable for <serial> (kill switch active or no connection): dumpsys connectivity: Wi-Fi not connected"`.
3. Script exit ngay (`blocked-vichanger-vpn`), không chạy feed session → màn hình không giữ sáng → timeout 600s → Keyguard lock.
4. Device lock file **vẫn còn** (PID còn sống nhưng đã handoff, `status: blocked`).

## Xác nhận nhanh
```bash
# 1. Kiểm tra keyguard + WiFi
adb -s <serial> shell "dumpsys window | grep -i 'showing=true'; dumpsys wifi | grep mWifiInfo | head -2"

# 2. Kiểm tra device lock
cat "C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json"
# -> status: blocked, owner_active: false = đúng pattern này

# 3. Đọc summary artifact
# D:/Taadaa/runtime/kibe/live/<date>/row-N-<time>/<run>/machines/machine_<N>/<run>/summary.txt
# -> final_status: blocked-vichanger-vpn
```

## Fix
```bash
# Bật lại WiFi qua ADB
adb -s <serial> shell svc wifi enable
# Chờ 10-15s, kiểm tra lại
adb -s <serial> shell dumpsys wifi | grep mWifiInfo | head -2
# Mở khóa màn hình (nếu cần)
adb -s <serial> shell input keyevent 82
```

## Lưu ý
- Máy bị mất WiFi thường do: AP reset, điện nguồn máy bị gián đoạn, WiFi sleep policy, hoặc cổng switch/AP bị lỗi.
- `blocked-vichanger-vpn` trong farm đã bỏ ViChanger — tên label cũ nhưng logic thực tế là "proxy/router không reach được qua WiFi".
- Device lock vẫn còn sau khi xử lý WiFi — cron tiếp theo sẽ tự phát hiện `owner_active: false` và reclaim lock hoặc skip tùy protocol version.
- **Không nhầm** với lock do script đang chạy thật (`owner_active: true`) — kiểm tra PID liveness trước khi can thiệp.

## PID Liveness Check
```python
import psutil
try:
    p = psutil.Process(<pid>)
    print(p.name(), p.cmdline())
except psutil.NoSuchProcess:
    print("PID dead — lock stale, có thể clear")
```
