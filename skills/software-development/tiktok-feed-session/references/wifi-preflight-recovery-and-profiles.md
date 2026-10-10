# Wi-Fi Preflight Auto-Join Recovery & Dynamic Profile Governance

## Bối cảnh & Hiện trường
Khi chạy TikTok nuôi acc / feed session, nếu watchdog báo `Lỗi cấu hình Proxy` (mã `blocked-proxy-vpn`), nguyên nhân thường rơi vào 2 nhóm:
1. **Lệch port proxy thật:** Cấu hình vượt quá dải port PPPoE khả dụng trên router (ví dụ: gán nhầm port > 40 trong khi router chỉ mở 40 port PPPoE).
2. **Thiết bị rớt sóng Wi-Fi:** Preflight kiểm tra thấy `dumpsys connectivity: Wi-Fi not connected` dẫn tới không thông tới router proxy `192.168.110.2:200xx`.

## Cơ chế tự phục hồi 2 cấp tại Preflight (`vpn_preflight.py`)
Không dừng lại ở việc fail-closed hay bấm tay qua ADB, runner cần tự động phục hồi qua 2 cấp:

1. **Cấp 1 (Radio Toggle):**
   - Thử `svc wifi disable` -> `sleep 1` -> `svc wifi enable` -> `sleep 2`.
   - Nếu radio toggle phục hồi được Wi-Fi và egress IP thông qua proxy, tiếp tục ca chạy.

2. **Cấp 2 (Auto-join qua adbjoinwifi theo phân vùng Farm):**
   - Khi Cấp 1 thất bại (thường do AP Aruba dính cờ `ASSOCIATION_REJECTION` hoặc máy mất profile SSID), runner tự resolve số máy của serial thông qua file mapping `PROXYgandienthoai.xlsx` (cache thread-safe theo `mtime_ns` để tránh đọc lại file Excel liên tục và đóng file an toàn trong `finally`).
   - Đọc profile SSID & Mật khẩu từ file JSON ngoài mã nguồn để không vi phạm quy tắc an toàn (tránh hardcode credentials trong source code dẫn đến trượt Closeout Gate):
     - Biến môi trường: `FARM_WIFI_PROFILES_FILE` trỏ tới `D:/Taadaa/machine-config/farm_wifi_profiles.json`.
     - Phân vùng chuẩn:
       - Máy 01 – 40: `kibe 1`
       - Máy 41 – 80: `kibe 2`
       - Máy 201 – 240: `admin 1`
       - Máy 241 – 280: `admin 2`
   - Lệnh kích hoạt re-join:
     ```bash
     am force-stop com.steinwurf.adbjoinwifi && am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "<SSID>" --es password_type WPA --es password "<PASSWORD>"
     ```
   - Chờ máy nhận IP, gửi phím Home (`input keyevent 3`) để đưa màn hình về trạng thái sạch.
   - Thẩm định lại: Nếu Wi-Fi đã CONNECTED và Egress IP thông qua proxy -> Cho phép chạy tiếp. Nếu vẫn thất bại -> Fail-closed chặn an toàn (cấm tự ý fallback sang SSID vãng lai ngoài farm).
