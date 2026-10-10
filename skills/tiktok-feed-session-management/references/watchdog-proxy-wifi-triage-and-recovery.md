# Watchdog Proxy vs Wi-Fi Triage & Stage 2 Auto-Recovery

## 1. Context Drift Guard: Farm Proxy vs LLM Proxy
- **Bẫy lạc đề**: Khi người dùng hoặc watchdog báo "Lỗi cấu hình Proxy" sau khi kết thúc ca nuôi acc (feed session), ngữ cảnh 100% là **Farm Device / Router Proxy** (MikroTik `192.168.110.2:200xx`, Singbox, modem PPPoE).
- **CẤM TUYỆT ĐỐI**: Chạy sang kiểm tra các cổng LLM proxy của OmniRoute (`:20129`) hoặc 9Router (`:20128`). Đó là hai hệ thống hoàn toàn độc lập.

## 2. Bản chất nhãn "Lỗi cấu hình Proxy" trên Watchdog
- Nhãn "Lỗi cấu hình Proxy" trên báo cáo Watchdog thực chất gom chung tất cả các lỗi dừng tại bước preflight `blocked-proxy-vpn`.
- **Thao tác chẩn đoán O(1)**: Đọc file `log.jsonl` tại thư mục runtime của máy bị báo lỗi.
- **Dấu hiệu nhận biết**:
  - Nếu log ghi: `dumpsys connectivity: Wi-Fi not connected` ➔ Nguyên nhân gốc là **thiết bị mất kết nối Wi-Fi** tới AP Aruba, dẫn đến không kết nối được tới proxy LAN MikroTik.
  - Nếu log ghi: `proxy server port is closed/refused` ➔ Cổng proxy trên MikroTik bị đóng (ví dụ lệch dải port > 40 trên dàn Admin).
  - Nếu log ghi: `device '...' not found` hoặc `offline` ➔ Rớt cáp USB / hub ADB, không phải lỗi proxy.

## 3. Cơ chế tự cứu Wi-Fi 2 cấp (Stage 2 adbjoinwifi trong vpn_preflight.py)
Khi preflight phát hiện mất Wi-Fi:
- **Cấp 1 (Radio Toggle)**: Thử `svc wifi disable` ➔ `svc wifi enable`.
- **Cấp 2 (Auto-join chuẩn theo Quy hoạch Wi-Fi Farm)**:
  - Nếu Cấp 1 thất bại (thường do AP Aruba dính cờ `ASSOCIATION_REJECTION` hoặc mất profile):
  - Tra cứu số máy từ device serial trong `PROXYgandienthoai.xlsx`.
  - Quy hoạch cố định AP Aruba:
    * Máy 01 – 40: SSID `kibe 1`, Pass `23102025`
    * Máy 41 – 80: SSID `kibe 2`, Pass `19051995`
    * Máy 201 – 240: SSID `admin 1`, Pass `19051995`
    * Máy 241 – 280: SSID `admin 2`, Pass `19051995`
  - Thực thi tự động:
    ```bash
    am force-stop com.steinwurf.adbjoinwifi && am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "<SSID>" --es password_type WPA --es password "<PASSWORD>"
    sleep 4
    input keyevent 3
    ```
- **Kỷ luật hiệu năng & Giám sát**:
  - Bắt buộc dùng `_WIFI_CREDENTIALS_CACHE` trong bộ nhớ, kiểm tra theo `st_mtime_ns` của file workbook để tránh đọc lại đĩa liên tục trong các batch lớn.
  - Luôn ghi nhận telemetry qua `_log_vpn_timeout_event` cho các sự kiện `stage2_wifi_adbjoinwifi_attempt`, `stage2_wifi_adbjoinwifi_success`, và `stage2_wifi_adbjoinwifi_failed`.
