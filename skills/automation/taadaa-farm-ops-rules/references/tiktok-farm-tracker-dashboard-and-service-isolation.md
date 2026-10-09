# TikTok Farm Account Tracking, Mobile Web Dashboard & Live Service Isolation

## 1. Bối cảnh & Mục tiêu
- Theo dõi thống kê danh sách tài khoản TikTok của Phone Farm (~600 accounts) bao gồm: Follower, Tim (Heart), Video Count, trạng thái Live/Die/WAF và phát hiện nick cắn đề xuất (viral).
- Cung cấp giao diện Mobile Web Dashboard xem trực quan trên điện thoại, đồng thời xuất báo cáo Excel và gửi tóm tắt tự động qua Telegram lúc 07:00 sáng.

## 2. Kỹ thuật Thu thập Dữ liệu TikTok Profile (Zero-Device, Zero-Login)
1. **Public Web Hydration Extraction**:
   - Dùng User-Agent Mobile Safari (`iPhone OS 16_6`) request công khai `https://www.tiktok.com/@{username}`.
   - Trích xuất JSON từ thẻ `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">`.
   - Trích xuất: UID (`user['id']`), `uniqueId`, `nickname`, `secUid`, `followerCount`, `followingCount`, `heartCount`, `videoCount`.
2. **Phân biệt SlardarWAF vs NOT_FOUND / DIE**:
   - **Bẫy tai hại**: Khi gửi request dồn dập từ 1 IP, TikTok trả về trang HTML chỉ có `SlardarWAF` (không có script rehydration). Nếu coi việc thiếu data là `NOT_FOUND`, hệ thống sẽ báo ảo hàng trăm nick DIE (false DIE panic).
   - **Quy tắc**:
     + Chỉ đánh dấu `NOT_FOUND` / `DIE` khi có JSON với `statusCode == 10221`.
     + Nếu gặp `SlardarWAF` hoặc `ConnectionError`/`Timeout`: đánh dấu `RATE_LIMITED` và tự động retry qua proxy khác.
3. **Quản lý Proxy Pool cho Crawler**:
   - Sử dụng kho proxy chuẩn của farm: `D:/Taadaa/Tiktok-video/proxy_pool_67.txt` (hoặc `proxy_combined_pool.txt`).
   - Parse `host:port:user:pass` với URL-encode (`urllib.parse.quote(pwd, safe="")` cho `#`, `!`).
   - Xoay vòng proxy giữa các workers (10-15 workers) để mỗi IP chỉ thực hiện vài request, tránh hoàn toàn WAF rate-limit.

## 3. Tiêu chí Phát hiện "Cắn Đề Xuất" (Trending / Viral Detection)
- **Baseline Snapshot**: Phải dọn sạch các snapshot lỗi (như snapshot ghi nhận 0 follower do WAF) trước khi tính delta.
- **Tiêu chí cắn đề xuất chuẩn cho farm 600 nick (chu kỳ 24h)**:
  1. `heart_delta >= 500`: Lượt tim tăng đột biến trong ngày (chứng tỏ có video lọt xu hướng/FYP).
  2. `follower_delta >= 50`: Tăng trưởng follower đột biến trong ngày.
- Không đặt ngưỡng quá thấp (như 10 follow / 50 like) vì sẽ làm loãng danh sách đề xuất.

## 4. Web Dashboard Mobile-Responsive (`tiktok_dashboard.py`)
- Chạy qua Python `http.server.ThreadingHTTPServer` trên cổng riêng biệt (mặc định: `1905`).
- Dark mode responsive cho điện thoại di động:
  - 4 KPI cards: Tổng nick, Tổng follower, Nick Live, Cắn đề xuất.
  - Bộ lọc nhanh: Tất cả, Chỉ nick cắn đề xuất, Chỉ Live.
  - Sắp xếp tức thì theo cột: Cho phép bấm vào tiêu đề cột `Tim`, `Followers`, `Videos`... để sort tăng/giảm trực tiếp bằng JS.
- Truy cập:
  - Wi-Fi Farm: `http://192.168.110.123:1905`
  - Tailscale: `http://100.88.164.111:1905`

## 5. Nguyên tắc Cách ly Dịch vụ Mạng Đang Hoạt Động (Service Isolation Invariant)
1. **TUYỆT ĐỐI CẤM can thiệp, gộp chung hoặc chèn code vào các dịch vụ đang chạy ổn định**:
   - Nghiêm cấm chèn route mới hoặc sửa đổi `server.py` của MikroTik Web Manager (`kibe:2310`).
   - Mọi công cụ dashboard, UI mới BẮT BUỘC chạy độc lập trên process và port riêng (`1905`, v.v.).
2. **CẤM tự ý thêm bản ghi DNS tĩnh trên Router MikroTik (`192.168.110.2`)**:
   - Việc tự ý thêm static DNS `kibe -> 192.168.110.123` làm đè MagicDNS của Tailscale (`100.88.164.111`), gây treo trình duyệt điện thoại khi truy cập từ ngoài hoặc qua VPN.
3. **Nhận thức về Môi trường Python & Windows Firewall**:
   - Python 3.11 (`C:\Users\Kibe\AppData\Roaming\uv\python\cpython-3.11...` hoặc system) đã được Windows Firewall mở port in-bound.
   - Python 3.12 trong môi trường ảo mới (`automation`) bị Windows Firewall mặc định block các kết nối in-bound từ mạng ngoài. Các service phục vụ web cho điện thoại truy cập qua LAN/Tailscale phải chạy bằng Python được phép mở port.
