# Bài Học Kỹ Thuật: Đồng Bộ Tự Động 2 Chiều R3G & MobiProxy, Cơ Chế Captive Portal Chấm Than vs. Leak IP & Sing-box Deprecations

## 1. Bài học về Cron Auto-Sync Whitelist R3G vs MobiProxy (Anti-Orphan Script)
- **Bẫy cũ:** Viết script `setup_r3g_ddns_cron.py` chạy thủ công bằng tay 1 lần thấy pass rồi báo cáo xong, nhưng không nối vào cronjob định kỳ 5 phút (`update_mikrotik_scan_guard.py`). Khi line `pppoe-out1` của MikroTik đổi IP, MobiProxy được tự động cập nhật nhưng R3G bị bỏ rơi, dẫn đến toàn bộ kết nối từ Farm sang R3G bị trả mã `403 Forbidden` / `502 Bad Gateway`.
- **Giải pháp chuẩn hóa:**
  - File `D:/Taadaa/AI-Tools/scripts/update_mikrotik_scan_guard.py` bắt buộc tích hợp cả 2 mắt xích:
    1. Đẩy IP mới lên MobiProxy qua API `proxy.scan_guard.save`.
    2. SSH qua Tailscale `100.115.94.49` (dùng `paramiko` với credentials chuẩn) cập nhật dòng `Allow <new_mikrotik_ip>` vào 16 file config Tinyproxy (`/etc/tinyproxy/instances/tp_51*.conf` và `/root/generate_all_proxies.sh`) rồi gửi `killall -HUP tinyproxy`.
  - Không bao giờ để script mồ côi (orphan script) mà không có cronjob bọc lót.

## 2. Giải mã hiện tượng "Wi-Fi Dấu Chấm Than" trên Android Samsung S7
- **Hiện tượng thực tế:** Khi proxy Sing-box hoặc proxy Thái Bình chết, điện thoại S7 hiện ngay icon dấu chấm than (!) trên cột sóng Wi-Fi và app không thể tải video.
- **Nguyên lý tầng OS Android:**
  - Khi thiết lập Manual Wi-Fi Proxy trên Android, hệ điều hành liên tục gửi gói tin thăm dò mạng (Captive Portal Probe tới `connectivitycheck.gstatic.com/generate_204`) xuyên qua chính cổng proxy đó.
  - Khi proxy chết, gói tin thăm dò bị timeout $\rightarrow$ Android đánh dấu mạng là "No Internet" và hiển thị dấu chấm than.
  - Các ứng dụng tuân thủ network framework của Android (kể cả TikTok) sẽ bị hệ điều hành chặn truy cập, hoạt động như một lớp Kill-Switch tự nhiên bảo vệ không để lộ IP.
- **Lưu ý rủi ro:** Tuy nhiên, nếu không có firewall chặn cổng ngầm, một số native socket hoặc ứng dụng có cơ chế fallback có thể lén bắn kết nối ra default gateway local. Do đó vẫn cần giữ các rule chặn UDP 443 (QUIC) và UDP 53 (DNS) để triệt tiêu mọi nguy cơ rò rỉ.

## 3. Khắc phục Sing-box 1.12+ Crash & Giảm Tải Logging
- **Lỗi văng container Sing-box 1.12+:**
  ```text
  ERROR[0000] missing `route.default_domain_resolver` or `domain_resolver` in dial fields is deprecated in sing-box 1.12.0 and will be removed in sing-box 1.14.0
  FATAL[0000] to continuing using this feature, set environment variable ENABLE_DEPRECATED_MISSING_DOMAIN_RESOLVER=true
  ```
  - **Sửa chữa:** Trong section `route` của file cấu hình Sing-box, bắt buộc phải khai báo:
    ```json
    "route": {
      "rules": [...],
      "final": "block",
      "default_domain_resolver": "dns-direct"
    }
    ```
- **Hạ tải CPU do I/O Logging:**
  - Chuyển `log.level` từ `info` sang `warn`. Mức `info` trên 160 inbound listeners khiến container liên tục format chuỗi và ghi log hàng chục nghìn kết nối mỗi giây, gây nghẽn I/O và đẩy CPU MikroTik lên cao.

## 4. Chuẩn Hóa Cấu Hình Gộp 160 Máy (Kibe + Admin)
- Khi sinh cấu hình `singbox_full_160.json` cho cả 2 dàn máy:
  - Dàn Kibe: máy 1-80 nghe tại ports `20001-20080`.
  - Dàn Admin: máy 201-280 nghe tại ports `20201-20280`.
  - Bắt buộc xử lý đọc độc lập cả 2 file Excel (`D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx` và `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`), bỏ qua các dòng ngoài phạm vi để không gây lỗi `ConfigError`.
  - File JSON nén (minified) khoảng ~38KB được PATCH trực tiếp vào MikroTik REST API (`/file/*8072575`).
