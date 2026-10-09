# WiFi Disconnect → blocked-vichanger-vpn → Keyguard Lock (2026-09-03)

## Triệu chứng
- Máy bị khóa màn hình (Keyguard `showing=true`), không thấy chạy.
- Device lock file tồn tại: `status: blocked`, `owner_active: false`.
- Run artifact `final_status: blocked-proxy-vpn` (hoặc nhãn legacy `blocked-vichanger-vpn`).

## Root Cause Chain
1. **WiFi mất kết nối** trên thiết bị (`mWifiInfo SSID: <unknown ssid>`, `Supplicant state: DISCONNECTED`).
2. Preflight proxy kiểm tra proxy router (`require_proxy_connected`) → không reach được → emit `stop_reason: "required router proxy is unreachable for <serial> (kill switch active or no connection): dumpsys connectivity: Wi-Fi not connected"`.
3. Script exit ngay (`blocked-proxy-vpn` / `blocked-vichanger-vpn`), không chạy feed session → màn hình không giữ sáng → timeout 600s → Keyguard lock.
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
# -> final_status: blocked-proxy-vpn (hoặc legacy: blocked-vichanger-vpn)
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

### Trường hợp lỗi nặng: ASSOCIATION_REJECTION (AP từ chối kết nối)
Nếu `dumpsys wifi` hiển thị `NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION` (count >= 8, `ASSOCIATION_REJECTION_EVENT` reason code 1) và `Supplicant state: INACTIVE`:
- Lệnh mềm `svc wifi enable` không có tác dụng do AP hoặc driver từ chối bắt tay.
- **Bước 1:** `adb reboot` để reset sạch subsystem WiFi/radio.
- **Bước 2:** Nếu sau reboot vẫn loop association rejection với SSID hiện tại (ví dụ `kibe 1`), dùng UI hoặc intent kết nối sang AP phụ cùng zone trong farm (`admin 1` hoặc `admin 2`, mật khẩu `19051995`):
  ```bash
  adb -s <serial> shell "am start -a android.settings.WIFI_SETTINGS"
  # Sau đó chọn và nhập mật khẩu 19051995 kết nối sang AP admin 1/2
  ```

## Lưu ý
- Mã nguồn đã chuẩn hóa đổi nhãn sang `blocked-proxy-vpn` / `proxy-vpn`, hoàn toàn loại bỏ chuỗi `vichanger`.
- Máy bị mất WiFi thường do: AP reset, điện nguồn máy bị gián đoạn, WiFi sleep policy, hoặc cổng switch/AP bị lỗi.
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
