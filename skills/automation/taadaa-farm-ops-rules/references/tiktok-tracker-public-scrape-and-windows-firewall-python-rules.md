# TikTok Account Tracker & Windows Firewall Inbound Python Rules (2026-09-17)

## 1. TikTok Public Profile Scraping & SlardarWAF Defense

### Cơ chế trích xuất chỉ số profile công khai
- Endpoint: `https://www.tiktok.com/@{username}`
- Headers bắt buộc: Mobile Safari User-Agent (giả lập iPhone truy cập link chia sẻ):
  ```python
  MOBILE_HEADERS = {
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8',
  }
  ```
- Dữ liệu nằm trong thẻ script:
  `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>({.*?})</script>`
- Trích xuất từ JSON:
  - `user['id']` (UID thật), `user['secUid']`, `user['nickname']`
  - `stats['followerCount']`, `stats['followingCount']`, `stats['heartCount']` (tổng tim), `stats['videoCount']`

### Bẫy SlardarWAF vs DIE / NOT_FOUND (CỰC KỲ QUAN TRỌNG)
- Khi quét nhanh nhiều request từ 1 IP, TikTok kích hoạt Slardar WAF: trả về trang HTML ~1400 bytes chứa chuỗi `slardarClient: SlardarWAF` và KHÔNG CÓ thẻ `__UNIVERSAL_DATA_FOR_REHYDRATION__`.
- **Lỗi chết người**: Nếu code kiểm tra "không có thẻ dữ liệu -> gán NOT_FOUND", toàn bộ dàn nick sẽ bị báo nhầm là DIE (như sự cố 568/592 nick bị báo nhầm).
- **Quy tắc phân biệt**:
  1. **DIE / NOT_FOUND thật**: Có thẻ `__UNIVERSAL_DATA_FOR_REHYDRATION__` nhưng `statusCode == 10221` hoặc `userInfo is None`.
  2. **Dính WAF / Rate Limit**: Không có thẻ dữ liệu VÀ html chứa `'SlardarWAF'` hoặc `'slardar'`. Trường hợp này BẮT BUỘC trả về `RATE_LIMITED` và xoay proxy thử lại, TUYỆT ĐỐI CẤM gán `NOT_FOUND`!

### Nạp Proxy Pool chuẩn của Farm
- Nạp duy nhất từ file canonical: `D:/Taadaa/Tiktok-video/proxy_pool_67.txt` (hoặc fallback `D:/OneDrive/TaadaaData/proxy_combined_pool.txt`).
- URL-encode user và password (đặc biệt ký tự `#` và `!` như `TaadaaMobi%232026%21`).
- Xoay vòng proxy khi gặp `RATE_LIMITED` hoặc network error, tối đa retry 2-3 lần.

---

## 2. Windows Firewall Inbound Rules: Python 3.11 vs Python 3.12

### Hiện tượng
Server web local (như Dashboard cổng 1905, 2310...) chạy trên máy Kibe nhưng điện thoại (iPhone qua Wi-Fi LAN hoặc Tailscale) không thể mở được trang: Safari báo *"Safari không thể mở trang vì máy chủ ngừng phản hồi"* (Connection timeout / refused).

### Nguyên nhân gốc rễ trong Windows Firewall
- Trên máy host Windows Kibe, firewall cấu hình rule Inbound theo đường dẫn file thực thi `Program`:
  - `C:\Users\Kibe\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe` (môi trường Python 3.11 mặc định của hệ thống) -> **Action: ALLOW** (Inbound Private, LocalPort: Any).
  - `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe` (Python 3.12 / automation env) -> **Action: BLOCK** (Inbound Private)!
- Khi bất kỳ web server nào được khởi chạy bằng Python 3.12 (hoặc qua virtualenv trỏ về 3.12), Windows Firewall sẽ **âm thầm chặn toàn bộ kết nối từ điện thoại/máy bên ngoài**.

### Quy tắc bất biến khi chạy Web Server / Dashboard truy cập từ xa
- Mọi web server local cần mở cho điện thoại xem (như `mikrotik_web/server.py` cổng 2310, `tiktok_dashboard.py` cổng 1905) **BẮT BUỘC chạy bằng Python 3.11**:
  ```cmd
  cmd.exe /c "python server.py"
  # hoặc đường dẫn tuyệt đối uv cpython-3.11:
  C:\Users\Kibe\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe <script.py>
  ```
- **TUYỆT ĐỐI CẤM** dùng `D:/Taadaa/python-envs/automation/Scripts/python.exe` (Python 3.12) để start web server phục vụ truy cập ngoài mạng localhost.

---

## 3. Nguyên tắc Độc lập Dịch vụ & Chống Xung đột DNS

1. **Không can thiệp vào service đang chạy ổn định của Farm**:
   - `mikrotik_web/server.py` (cổng 2310) là công cụ vận hành mạng sống còn của farm. CẤM TUYỆT ĐỐI chỉnh sửa, chèn route phụ hoặc restart service này để phục vụ các tính năng mới/thử nghiệm.
   - Các công cụ mới (như TikTok Dashboard) phải chạy trên tiến trình và cổng riêng biệt (vd: port 1905).

2. **Chống xung đột Tailscale MagicDNS**:
   - Host `kibe` đã được quản lý định danh bởi Tailscale MagicDNS (`100.88.164.111`).
   - CẤM tự ý thêm bản ghi static DNS tên `kibe` trên router MikroTik trỏ về IP LAN `192.168.110.123` vì sẽ gây split-brain và mất kết nối trên các thiết bị chạy Tailscale.
