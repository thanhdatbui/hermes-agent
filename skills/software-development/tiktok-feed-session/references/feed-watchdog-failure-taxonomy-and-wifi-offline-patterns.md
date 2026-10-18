# Feed Session Failure Classification Taxonomy & Watchdog Invariant

## Bối cảnh & Nguyên nhân lỗi gom cụm
Khi chạy nuôi feed TikTok trên quy mô 80–160 máy (Dual Cluster Kibe & Admin), watchdog `feed_session_watchdog.py` tổng hợp kết quả dựa trên hàm `classify_feed_failure(reason)` trong `scripts/watchdog/formatters.py`.
Nếu `classify_feed_failure` thiếu các pattern cụ thể, mọi lỗi không khớp sẽ rơi vào fallback mặc định là `"Lỗi App TikTok/Script"`. Điều này làm sai lệch báo cáo (phóng đại con số app crash trong khi bản chất là lỗi mạng Wi-Fi hoặc lệch focus/swipe).

## Bảng chuẩn hóa Taxonomy trong `scripts/watchdog/formatters.py`
1. **Mất kết nối Wi-Fi (AP):**
   - Pattern: `"wi-fi not connected"`, `"wifi not connected"`, `"association_rejection"`, `"no-carrier"`, `"dormant"`, `"wlan0 down"`, `"network disconnected"`, `"network-offline"`, `"no internet connection"`, `"wifi_combo"`.
   - Đặc trưng: Các máy dính `manual-needed:network-offline: Wi-Fi has no internet connection (wifi_combo status)` theo dải (ví dụ M33–38).
2. **Mất kết nối ADB/USB:**
   - Pattern: `"device not found"`, `"device offline"`, `"not found in adb"`, `"no-run-recorded"`, `"unauthorized"`, `"transport"`, `"adb/usb"`.
3. **Chưa gán Proxy / Proxy :0:**
   - Pattern: `"missing or :0"`, `"http_proxy is missing"`, `":0"`, `"proxy is not set on device"`, `"missing proxy"`, `"no proxy"`.
4. **Nghẽn đường truyền Proxy / 4G:**
   - Pattern: `"proxy is unreachable"`, `"proxy readiness timed out"`, `"connection refused"`, `"context deadline exceeded"`, `"proxy timeout"`, `"network is unreachable"`.
5. **Lỗi cấu hình Proxy:**
   - Pattern: `"proxy"`, `"vpn"`.
6. **Lỗi mở/focus App TikTok:**
   - Pattern: `"failed to focus tiktok"`, `"prepare-tiktok failed to focus"`, `"focused package unavailable"`.
7. **Lỗi thao tác vuốt (Swipe):**
   - Pattern: `"swipe command failed"`.
8. **Lỗi chụp màn hình Feed:**
   - Pattern: `"screen capture invalid"`, `"feed not confirmed"`.
9. **Lệch Profile/Nick TikTok:**
   - Pattern: `"profile account mismatch"`, `"profile username"`, `"navigation target profile not found"`.
10. **Văng màn hình Đăng nhập:**
    - Pattern: `"login/account screen detected"`.
11. **Trạng thái TikTok lạ/chưa hỗ trợ:**
    - Pattern: `"unknown tiktok state"`.
12. **Fallback cuối:**
    - `"Lỗi App TikTok/Script"`.

## Quy tắc kiểm chứng & Regression Test
- Khi cập nhật `classify_feed_failure`, bắt buộc cập nhật test tương ứng tại `python_runner/tests/test_feed_session_watchdog.py`.
- Lệnh chạy test:
  `python -m pytest python_runner/tests/test_feed_session_watchdog.py -k "test_classify_feed_failure"`
