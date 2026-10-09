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
adb -s <SERIAL> shell svc wifi disable && sleep 2 && adb -s <SERIAL> shell svc wifi enable
```

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
