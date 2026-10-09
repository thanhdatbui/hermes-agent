# S7 Wi-Fi Hang Triage & Recovery via ADB (O(1))

## Triệu chứng
1. Màn hình máy farm hoặc bảng Huanwei hiển thị icon mất sóng Wi-Fi (hoặc báo disconnected).
2. ADB vẫn online bình thường qua cáp USB.
3. Kiểm tra Wi-Fi service: `dumpsys wifi`
   - Wi-Fi is enabled (`curState=DeviceActiveState`, `WifiManager.setWifiEnabled(true)`).
   - Supplicant rơi vào trạng thái `UNINITIALIZED` / `DISCONNECTED`.
   - wlan0 interface: `state DORMANT`, `NO-CARRIER`, `inet` rỗng (không gán IP).
   - Log Wi-Fi xuất hiện chuỗi `EVENT_SCAN_TIMEOUT` liên tục hoặc kẹt scan không associate lại AP đã lưu.

## Quy trình Kiểm tra O(1)
1. **Kiểm tra trạng thái interface wlan0:**
   ```bash
   adb -s <SERIAL> shell ip addr show wlan0
   ```
2. **Kiểm tra trạng thái Wi-Fi & SSID kết nối gần nhất:**
   ```bash
   adb -s <SERIAL> shell "dumpsys wifi | grep -E 'Wi-Fi is|mWifiInfo|mNetworkInfo|curState'"
   ```
3. **Kiểm tra AP đã lưu trong máy:**
   ```bash
   adb -s <SERIAL> shell "dumpsys wifi | grep -A 10 'Configured networks Begin'"
   ```
   *(Farm S7 thường kết nối `kibe 1` hoặc `kibe 2` trên băng tần 5GHz AP).*

## Quy trình Khôi phục Nhanh (O(1) Soft Reset)
Không cần reboot cả máy Android (tránh rớt ADB hay restart app ngầm). Dùng lệnh `svc wifi` để reset stack Wi-Fi:
```bash
# Kibe Local:
adb -s <SERIAL> shell "svc wifi disable && sleep 1 && svc wifi enable"

# Admin Remote (192.168.110.119:5037):
adb -H 192.168.110.119 -P 5037 -s <SERIAL> shell "svc wifi disable && sleep 1 && svc wifi enable"
```

## Cạm bẫy Code Automation & Watchdog Fleet (2026-09-24)
1. **Cạm bẫy `svc wifi enable` đơn thuần trong code (Preflight / Runner)**:
   - Khi máy rớt sóng AP hoặc kẹt DHCP, switch Wi-Fi trong Cài đặt hệ điều hành Android thực tế **vẫn đang ở trạng thái BẬT (ON)**.
   - Gọi `adb.shell(["svc", "wifi", "enable"])` đơn thuần hoàn toàn là NO-OP, không kích hoạt lại driver hay chu kỳ quét AP.
   - **Bắt buộc trong code**: Phải gọi chuỗi toggle trọn vẹn: `adb.shell(["svc", "wifi", "disable"])` -> `time.sleep(1.0)` -> `adb.shell(["svc", "wifi", "enable"])` (như đã chuẩn hóa trong `vpn_preflight.py`).
2. **Watchdog Fleet (`farm_wifi_auto_healer.py`) Bắt Buộc Dual-Cluster & Đa Luồng Song Song**:
   - Watchdog nền nếu chỉ quét `adb devices` cục bộ sẽ bỏ sót toàn bộ 80 máy Farm Admin (`192.168.110.119:5037`). Bắt buộc phải load cả 2 mapping (`kibe\PROXYgandienthoai.xlsx` và `admin\PROXYgandienthoai.xlsx`).
   - Quét tuần tự 160 máy làm watchdog ngốn 500-600s dẫn đến timeout. BẮT BUỘC dùng `ThreadPoolExecutor(max_workers=20)` để quét và heal song song toàn bộ 160 máy trong **~6.3 giây**.

## Nghiệm thu & Bằng chứng (Gate 6)
1. Chờ 4-5s để DHCP client nhận lại IP:
   ```bash
   adb -s <SERIAL> shell ip addr show wlan0
   adb -s <SERIAL> shell "dumpsys wifi | grep 'mWifiInfo:'"
   ```
2. Kiểm tra ping thông mạng nội bộ và Internet:
   ```bash
   adb -s <SERIAL> shell ping -c 3 192.168.110.2
   adb -s <SERIAL> shell ping -c 3 8.8.8.8
   ```
3. Chụp screencap nghiệm thu hiện trường đính kèm `MEDIA:<path>` theo Gate 6:
   ```bash
   adb -s <SERIAL> shell screencap -p /sdcard/wifi_recovered.png
   adb -s <SERIAL> shell pull /sdcard/wifi_recovered.png D:/Taadaa/wifi_recovered.png
   adb -s <SERIAL> shell rm /sdcard/wifi_recovered.png
   ```
