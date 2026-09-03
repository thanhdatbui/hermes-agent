# Wifi/connectivity check trước live + sau reboot (bài học máy 74, 2026-08-03)

## Triệu chứng

- Máy văng wifi tự nhiên: `wlan0` ở `DORMANT`/`NO-CARRIER`, mất IP, `ping: Network is unreachable`.
- VPN `tun0` VẪN báo `CONNECTED/CONNECTED` trong `dumpsys connectivity` (VPN gán trên nền không mạng) — **không được tin tun0 như bằng chứng internet**.
- `svc wifi enable` KHÔNG cứu được (wifi_on=1 nhưng wlan0 vẫn NO-CARRIER → radio không thấy AP, không phải bị tắt mềm).
- `adb reboot` không đảm bảo wifi tự lên lại — máy 74 sau reboot vẫn DORMANT, phải **toggle tay trong Settings** (tắt/bật wifi) mới lên.

## Chuẩn đoán nhanh

```bash
ADB="/c/Program Files (x86)/xiaowei/tools/adb.exe"
SERIAL=ce061606c21e153d03

# 1. wlan0 phải UP + có inet
"$ADB" -s "$SERIAL" shell ip addr show wlan0 | grep -E 'state|inet '
#   OK:   state UP ... inet 192.168.110.215/24
#   FAIL: state DORMANT (NO-CARRIER) — không có dòng inet

# 2. ping ra internet
"$ADB" -s "$SERIAL" shell ping -c 2 -W 3 8.8.8.8

# 3. tun0 KHÔNG được dùng làm proof (xem dumpsys connectivity)
"$ADB" -s "$SERIAL" shell dumpsys connectivity | grep -iE 'NetworkAgentInfo.*(WIFI|VPN)'

# 4. radio có thấy AP không
"$ADB" -s "$SERIAL" shell cat /proc/net/wireless
#   wlan0: link level = 0, status 0000 → radio không thấy tín hiệu nào
```

## Rule cần implement (spec: tasks/2026-08-03-wifi-check-after-reboot.md)

1. Core `automation_core/device_recovery.py`:
   - Thêm `wait_for_wifi(adb, timeout, poll_interval)` — verify `ip addr show wlan0` có `state UP` + `inet`, hoặc ping gateway/8.8.8.8 OK.
   - Trong `watch_device_reconnect`: sau `wait_until_unlocked`, chạy `wait_for_wifi` trước `on_ready`. Hết hạn → KHÔNG gọi `on_ready`, báo `WIFI_NOT_READY`; vòng lặp retry ở event kế tiếp. Tham số mới `wifi_timeout: float = 120` (truyền 0 để tắt, backward-compatible).
2. Consumer gan-proxy `gan_proxy_fleet.py::apply_proxy`: nếu set VPN fail vì thiếu connectivity → ghi `WIFI_NOT_READY`, không ghi `VPN_APPLIED` giả.
3. KHÔNG tự reboot/toggle trong core — chỉ chờ + verify + báo lỗi rõ.

## Khôi phục đã xác nhận (máy 74)

- User **toggle tay wifi trong Settings** (tắt → bật) → wifi lên lại
  (`wlan0 UP`, `inet 192.168.110.215`), ping OK, watcher gan-proxy tự gán lại
  VPN (`tun0 inet 172.19.0.1/30`) → workflow chạy tiếp được. Không cần reboot
  thêm, không cần sửa gì trong watcher khi wifi tự lên.
- Sau khi wifi lên, máy có thể gặp **popup USB Samsung**
  (`MtpApplication/USBConnection`, do USB reconnect) → xử lý bằng handler core
  `automation_core/usb_popup.py` (xem SKILL.md).

## Verifier đúng sau reboot

```python
# Thay vì chỉ _verify_vpn(tun0), phải verify cả wifi + vpn:
def _verify_connectivity(adb_path, serial):
    adb = AdbClient(str(adb_path), serial, default_timeout=10)
    wlan = adb.shell(["ip", "addr", "show", "wlan0"], timeout=10)
    tun = adb.shell(["ip", "addr", "show", "tun0"], timeout=10)
    return ("inet " in str(wlan.stdout or "") and "state UP" in str(wlan.stdout or "")) \
        and "inet " in str(tun.stdout or "")
```
