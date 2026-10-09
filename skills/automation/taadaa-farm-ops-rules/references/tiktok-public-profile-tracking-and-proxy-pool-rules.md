# TikTok Public Profile Tracking, Proxy Pool & Web Service Discipline (2026-09-17)

## 1. TikTok Public Profile Scraping & SlardarWAF Defense
- **Bản chất**: TikTok Desktop Web khi nhận request dồn dập từ 1 IP sẽ kích hoạt `SlardarWAF` (trả về HTML 1.4KB không có script hydration).
- **Mobile Safari Header**: Sử dụng User-Agent Safari trên iPhone (`Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15...`) giúp lấy trực tiếp hydration JSON từ thẻ:
  `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">`
  chứa đầy đủ: `id` (UID), `secUid`, `nickname`, `followerCount`, `heartCount` (tổng like), `videoCount`, `friendCount`.
- **Bẫy Phân Loại Sai Lệch (SlardarWAF False-Positive Trap)**:
  - Khi không tìm thấy thẻ `__UNIVERSAL_DATA_FOR_REHYDRATION__`, **CẤM** tự động gán `status = 'NOT_FOUND'` / `DIE`!
  - Kiểm tra nếu chuỗi HTML chứa `SlardarWAF` hoặc `slardarClient` -> Đánh dấu là `RATE_LIMITED` và kích hoạt retry qua proxy khác.
  - **CHỈ ĐƯỢC GÁN** `NOT_FOUND` / `DIE` khi TikTok trả về JSON có `statusCode == 10221` hoặc `userInfo == None`.

## 2. Kỷ Luật Nạp Proxy Pool Toàn Farm (Dải 67 Proxy Chuẩn)
- **Nguồn chuẩn duy nhất**: File canonical `D:/Taadaa/Tiktok-video/proxy_pool_67.txt` (hoặc fallback `D:/OneDrive/TaadaaData/proxy_combined_pool.txt`).
- **Bẫy nạp cộng dồn (Proxy Inflation Trap)**:
  - Farm Kibe có **67 proxy 4G vật lý**.
  - Tuyệt đối CẤM nạp gộp cả 4 file (`proxy_pool_67.txt`, `proxy_pool_67_direct.txt`, `proxy_combined_pool.txt`, và dải local port `192.168.110.2:20001..20032`). Các file này chỉ là alias (tên miền vs IP direct vs local mapping) của cùng một dải proxy vật lý.
  - Nạp gộp sẽ làm tăng ảo số lượng proxy (lên 157 proxy) và user sẽ bắt lỗi "Tổng có 67 proxy thôi mà ở đâu ra 157".

## 3. Quy Chuẩn Tích Hợp Web Dashboard & Cổng Truy Cập Mobile
- **Tránh mở cổng mới tùy tiện**:
  - Khi tạo web dashboard xem trên điện thoại, việc mở các cổng tùy ý (như 1905, 20130) sẽ bị chặn bởi Windows Firewall và DNS mobile không thể phân giải tên máy đơn lẻ (`http://kibe:...`).
- **Cổng chuẩn kibe:2310**:
  - Dịch vụ MikroTik Web Manager tại `D:/Taadaa/AI-Tools/tools/mikrotik_web/server.py` đã mở sẵn cổng `2310`, có cấu hình Windows Firewall và Whitelist IP cho cả LAN (`192.168.110.x`) lẫn Tailscale (`100.x`).
  - Mọi công cụ dashboard / tra cứu mới cho farm nên tích hợp trực tiếp làm sub-route của `kibe:2310` (ví dụ `http://kibe:2310/tiktok`) hoặc đặt nút điều hướng ngay trên giao diện `kibe:2310` để user mở trên điện thoại tiện nhất.

## 4. Kỷ Luật Điều Phối: Sol Plan Trước Khi Dispatch
- **Quy tắc bất biến**: Khi nhận task phát triển tool, sửa flow hoặc refactor code, Coordinator **BẮT BUỘC** gọi `sol_planner.py` (`D:/Taadaa/tools/sol_planner.py`) qua cổng `:20129` để lấy Sol Plan Tầng A trước khi dispatch worker.
- CẤM Coordinator tự lên plan mà bỏ qua Sol Brain.
