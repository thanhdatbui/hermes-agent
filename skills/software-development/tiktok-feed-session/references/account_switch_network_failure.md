# Pitfall: Profile Username Mismatch After Account Switch Due to Network/Wi-Fi Loss

## 1. Triệu chứng
- Alert `[MÁY N] DỪNG PHIÊN`: `profile username still mismatched after switch`.
- Hiện trường: Script đã mở Account Switcher thành công, tìm thấy đúng username mục tiêu và tap vào row, nhưng sau khi TikTok reload/quay lại Profile thì username vẫn giữ nguyên nick cũ.

## 2. Nguyên nhân gốc (Root Cause)
- TikTok yêu cầu kết nối mạng online đến auth server khi chuyển tài khoản qua Switcher Sheet.
- Nếu Wi-Fi trên máy bị mất Internet (ví dụ: roaming nhầm sang BSSID 2.4GHz yếu RSSI < -80dBm, mất default gateway, mất route đến proxy MikroTik/Singbox `192.168.110.2`, hoặc proxy timeout):
  - TikTok âm thầm hủy bỏ lệnh chuyển tài khoản mà không báo lỗi rõ ràng.
  - Ứng dụng tự động quay về Home/Feed ở chế độ offline với popup `"Không có kết nối. Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"`.
  - Profile vẫn hiển thị nick cũ đã cache trước đó.

## 3. Quy trình chẩn đoán nhanh (ADB trực tiếp theo Serial)
1. **Kiểm tra thông báo thanh trạng thái (SystemUI):**
   - Dump UI XML kiểm tra node `com.android.systemui:id/wifi_combo` xem có chuỗi `Không có Internet` hay không.
2. **Kiểm tra link Wi-Fi & BSSID:**
   ```bash
   adb -s <serial> shell dumpsys wifi | grep -E "mWifiInfo.*SSID"
   ```
   - Kiểm tra xem máy có bị rớt xuống Link speed 1-2Mbps, RSSI suy hao, hoặc kết nối nhầm SSID/BSSID phụ không.
3. **Kiểm tra IP route & Ping tới Proxy:**
   ```bash
   adb -s <serial> shell ip route
   adb -s <serial> shell ping -c 3 192.168.110.2
   ```

## 4. Xử lý phục hồi
1. Reset lại interface Wi-Fi trên thiết bị:
   ```bash
   adb -s <serial> shell "svc wifi disable && sleep 2 && svc wifi enable && sleep 4"
   ```
2. Xác nhận kết nối phục hồi (ping proxy 192.168.110.2 đạt 0% packet loss, link speed > 50Mbps).
3. Tiến hành chuyển lại tài khoản trên TikTok hoặc cho phép script retry preflight.
