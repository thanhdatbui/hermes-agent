# atx-agent curl Direct Fallback Trap on Global Proxy Devices

## Hiện tượng & Bối cảnh
- Dàn máy farm Kibe sử dụng cụm Sing-box trung gian (`192.168.110.2:20001..20080`), cấu hình qua lệnh:
  `settings put global http_proxy 192.168.110.2:200xx`
- Sing-box forward upstream sang MobiProxy ngoài (`test.taadaa.click:51xx`).
- Khi box MobiProxy sập mạng hoặc trả `502 Bad Gateway`, điện thoại thật không thể truy cập internet qua proxy.
- Tuy nhiên, script nuôi TikTok (`run_tiktok.py` / `multi_machine_feed_session.py`) vẫn vượt qua bước `vichanger_preflight` (`result="connected"`), app TikTok vẫn bị bật lên, cố gắng chuyển tài khoản và gặp lỗi *"Không có kết nối. Tự động tải video về qua Wi-Fi..."* dẫn đến văng trắng/hỏng phiên chạy vô ích.

## Nguyên nhân cốt lõi (Root Cause)
1. **`atx-agent` không kế thừa Android Java Global Proxy:**
   - Binary `atx-agent` được viết bằng Go, chạy trong môi trường adb daemon (Linux shell).
   - Nó không tự động đọc và áp dụng Android Java System Settings `settings get global http_proxy` trừ khi được truyền rõ biến môi trường `export http_proxy=...`.
2. **Cạm bẫy Fallback Direct Egress:**
   - Trong `automation-core/src/automation_core/preflight.py` (hàm `check_android_vpn`):
     ```python
     if global_proxy:
         extracted_ip, ... = _probe_atx_curl_public_ip(adb, proxy=global_proxy)
         if extracted_ip:
             egress_ip_ok = True

     if not egress_ip_ok:
         # CẠM BẪY: Khi probe qua proxy thất bại, code lại fallback sang direct probe!
         extracted_ip, ... = _probe_atx_curl_public_ip(adb)
         if extracted_ip:
             egress_ip_ok = True
     ```
   - Khi upstream proxy chết, probe qua proxy trả về rỗng / 502 (`egress_ip_ok = False`).
   - Bước fallback probe không truyền `proxy`, `atx-agent` đi trực tiếp qua card mạng Wi-Fi `wlan0`. Do router LAN vẫn có đường ra internet (IP WAN FPT `1.53.55.190`), probe direct trả về thành công IP WAN FPT!
   - Hàm coi như `egress_ip_ok = True` và kết luận `is_safe = True` (`status.allowed = True`).
3. **Mâu thuẫn môi trường thực thi giữa Tool probe và User App:**
   - Script probe (`atx-agent` fallback) đi qua Direct Wi-Fi $\rightarrow$ Có mạng $\rightarrow$ Báo PASS.
   - App TikTok (chạy trong Android Framework) bị ép đi qua Global Proxy `192.168.110.2:200xx` $\rightarrow$ Nhận `502 Bad Gateway` $\rightarrow$ Mất mạng hoàn toàn.

## Khắc phục & Invariant
1. **CẤM Fallback sang Direct Probe khi có Global Proxy:**
   - Khi `global_proxy` được phát hiện trên thiết bị:
     ```python
     if global_proxy:
         extracted_ip, last_err, conn_lost = _probe_atx_curl_public_ip(adb, proxy=global_proxy)
         if extracted_ip:
             proxy_ip = extracted_ip
             egress_ip_ok = True
         else:
             errors.append(f"global proxy ({global_proxy}) egress failed: {last_err}")
             # KHÔNG ĐƯỢC fallback sang direct probe!
     ```
   - Nếu probe qua proxy thất bại, lập tức fail-closed: `status.allowed = False` để dừng máy ngay tại preflight trong vòng 3 giây, tuyệt đối không mở app.
2. **Loại bỏ Ping LAN nghiệm thu Internet khi dùng Proxy:**
   - Điều kiện `if egress_ip_ok or (ping_ok and wifi_validated):` cần loại trừ nhánh ping LAN khi máy đang bắt buộc chạy qua HTTP proxy.
