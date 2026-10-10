# Nhãn Watchdog 'Lỗi cấu hình Proxy' & Cơ Chế Tự Cứu Wi-Fi 2 Cấp (2026-10-10)

## 1. Cạm bẫy nhãn 'Lỗi cấu hình Proxy' trong Watchdog Ca Chạy
Khi báo cáo feed session (ví dụ cron `tiktok-feed-session-watchdog`) thông báo:
```text
Fail: M7, M10, M35
- Lỗi cấu hình Proxy (3): M7, M10, M35
```
Nhãn này được watchdog map từ trạng thái kết thúc `blocked-proxy-vpn` hoặc lỗi ở bước `vpn_preflight`.
Tuy nhiên, `blocked-proxy-vpn` được kích hoạt bởi nhiều nguyên nhân khác nhau:
1. **Wi-Fi trên máy bị rớt hoàn toàn**: `dumpsys connectivity: Wi-Fi not connected` hoặc `wlan0: state DOWN`.
2. **Proxy server port bị đóng/refused**: Server MikroTik/Singbox không lắng nghe hoặc cổng PPPoE chưa quay xong.
3. **Mất proxy setting trên máy**: `settings get global http_proxy` rỗng hoặc `:0`.
4. **Port proxy vượt dải cấu hình**: Điển hình là máy M241–M280 trên Admin bị gán port `10041..10080` vượt quá 40 port PPPoE của MikroTik.

**Hành động bắt buộc cho Agent Coordinator:**
- Khi User hỏi về lỗi proxy trên ca chạy, TUYỆT ĐỐI KHÔNG tra cứu các hệ thống proxy LLM (như OmniRoute, 9Router, OpenAI proxy).
- BẮT BUỘC kiểm tra hiện trường máy chạy TikTok qua `inspect_machine.py <N>` và đọc file `log.jsonl` của ca chạy tương ứng tại `D:/Taadaa/runtime/<cluster>/live/.../machines/machine_<N>/.../log.jsonl`.

## 2. Vì sao Runner trước đây không tự cứu được khi rớt Wi-Fi
Trong `python_runner/core/vpn_preflight.py` (`require_proxy_connected`):
- Nhánh phục hồi chế độ Router Transparent Proxy (`wlan0`) trước đây chỉ có Cấp 1 (Radio Toggle):
  ```python
  adb.shell(["svc", "wifi", "disable"], timeout=5, check=False)
  time.sleep(1.0)
  wifi_res = adb.shell(["svc", "wifi", "enable"], timeout=5, check=False)
  ```
- Khi máy gặp phải các sự cố như:
  - Access Point (Aruba) từ chối kết nối (`ASSOCIATION_REJECTION`).
  - Cấu hình Wi-Fi trên máy bị corrupt hoặc chưa lưu profile.
  - Sau khi toggle, máy không tự động kết nối lại SSID quy hoạch.
- Kết quả: `dumpsys connectivity` vẫn báo `Wi-Fi not connected` $\rightarrow$ Runner kích hoạt kill-switch an toàn và dừng phiên `blocked-proxy-vpn` để tránh rò rỉ IP nhà mạng. Máy bị bỏ rơi cho đến khi có người can thiệp.

## 3. Bản thiết kế Cơ chế Tự Cứu Wi-Fi Cấp 2 (2-Stage Recovery Ladder)
Để runner có khả năng tự cứu (Self-Healing) hoàn chỉnh:

### Cấp 1: Radio Toggle
Thực hiện `svc wifi disable` ➔ `sleep 1` ➔ `svc wifi enable` ➔ `sleep 2`.
Nếu `check_android_vpn` kiểm tra thấy `allowed=True` ➔ Tiếp tục ca chạy.

### Cấp 2: Auto-Join Chuẩn Quy Hoạch Qua `adbjoinwifi`
Nếu sau Cấp 1 mà Wi-Fi vẫn chưa UP:
1. Ánh xạ số máy sang SSID & Password tương ứng theo `farm-wifi-governance`:
   - Máy 01 – 40: SSID `kibe 1`, Pass `23102025`
   - Máy 41 – 80: SSID `kibe 2`, Pass `19051995`
   - Máy 201 – 240: SSID `admin 1`, Pass `19051995`
   - Máy 241 – 280: SSID `admin 2`, Pass `19051995`
2. Gửi Intent tới app `adbjoinwifi`:
   ```bash
   adb -s <serial> shell 'am force-stop com.steinwurf.adbjoinwifi && am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "<SSID>" --es password_type WPA --es password "<PASSWORD>"'
   ```
3. Chờ 4 giây cho Android bắt sóng và nhận IP `192.168.110.x`.
4. Bấm `input keyevent 3` (HOME) để dọn dẹp giao diện app `adbjoinwifi` khỏi màn hình chính.
5. Thẩm định lại qua `check_android_vpn`. Nếu thành công ➔ Tiếp tục; nếu thất bại ➔ Fail-closed (CẤM fallback sang bất kỳ SSID nào ngoài farm).
