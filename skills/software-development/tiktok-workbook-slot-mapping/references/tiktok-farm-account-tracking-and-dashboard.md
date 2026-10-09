# TikTok Farm Account Tracking, Proxy Pool & Mobile Dashboard (2026-09-17)

## 1. Bản chất & Cơ chế Thu thập Dữ liệu Profile Công khai
- Không cần login, không cần ADB vào điện thoại S7, không tốn tài nguyên thiết bị.
- Request GET `https://www.tiktok.com/@{username}` với User-Agent mobile Safari:
  ```python
  headers = {
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8',
  }
  ```
- TikTok trả về hydration JSON trong thẻ `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">`.
- Trích xuất:
  - `user['id']` (UID gốc), `user['secUid']`, `user['nickname']`
  - `stats['followerCount']`, `stats['followingCount']`, `stats['heartCount']` (tổng like), `stats['videoCount']`
  - Bị xóa/khóa/đổi tên: `statusCode == 10221` hoặc `userInfo is None`.

---

## 2. Bẫy Nguy Hiểm: SlardarWAF vs NOT_FOUND False Positive
- **Hiện tượng**: Quét dồn dập >25 nick liên tục từ 1 IP máy tính PC, TikTok trả về trang HTML ~1462 bytes chứa `slardarClient: SlardarWAF` (không có hydration script).
- **Sai lầm chết người**: Nếu code kiểm tra `if not match_universal_data: return NOT_FOUND` sẽ dẫn đến việc **500+ nick đang sống bị báo ảo thành DIE / BANNED**!
- **Quy tắc bắt buộc**:
  1. Kiểm tra HTML: nếu thấy `SlardarWAF` hoặc `slardar` $\rightarrow$ gán trạng thái `RATE_LIMITED` (hoặc WAF challenge), TUYỆT ĐỐI CẤM đánh dấu `NOT_FOUND` hoặc `DIE`.
  2. Bắt buộc kích hoạt cơ chế retry xoay vòng qua danh sách Proxy của farm.

---

## 3. Quản lý Proxy Pool của Farm (Kho 67 Proxy Chuẩn)
- **Nguồn chuẩn duy nhất**: `D:/Taadaa/Tiktok-video/proxy_pool_67.txt` (dải 67 proxy 4G chuẩn của farm).
- **Bẫy gom trùng file (157 vs 67 proxy)**:
  Tuyệt đối CẤM nạp gộp nhiều file pool (`proxy_pool_67.txt`, `proxy_pool_67_direct.txt`, `proxy_combined_pool.txt`, cụm 32 cổng nội bộ). Các file này chứa alias cùng endpoint vật lý qua tên miền vs IP direct vs cổng nội bộ. Gom mù quáng sẽ sinh 157 string giả, làm sai lệch số lượng proxy thực tế của farm.
- **Quy tắc nạp proxy chuẩn trong Python**:
  Pass và user có ký tự đặc biệt `#` và `!` $\rightarrow$ BẮT BUỘC dùng `urllib.parse.quote(..., safe="")` để URL-encode thành `%23` và `%21`, ví dụ:
  `http://mobi2:TaadaaMobi%232026%21@test.taadaa.click:5102`.

---

## 4. Web Dashboard xem trên Điện thoại & MikroTik Local DNS (`http://kibe:1905`)
- **Web Dashboard Server**: `D:/Taadaa/tools/tiktok_dashboard.py` (chạy trên cổng `1905`).
- **Cấu hình MikroTik Local DNS cho địa chỉ dễ nhớ**:
  - Router MikroTik tại `192.168.110.2:9090` (REST API `/rest/ip/dns/static`, Basic Auth `admin:N0spam@@`).
  - Thêm bản ghi tĩnh:
    + `name: "kibe"` $\rightarrow$ `address: "192.168.110.123"`
    + `name: "kibe.local"` $\rightarrow$ `address: "192.168.110.123"`
  - Mọi điện thoại kết nối Wi-Fi Farm chỉ cần gõ đúng:
    👉 **`http://kibe:1905`** là truy cập trực tiếp dashboard mà không cần nhớ IP máy tính.
- Đọc dữ liệu từ SQLite `D:/Taadaa/data/tiktok_tracker.db`.
- Tự tính toán $\Delta$ Follower và $\Delta$ Like giữa 2 snapshot gần nhất.
- Giao diện tối ưu Mobile: Dark mode, 4 thẻ KPI to, tìm kiếm realtime, 1 chạm lọc nick cắn đề xuất.

---

## 5. Kỷ luật Điều phối & Kế hoạch Sol Brain
- Trước khi dispatch worker làm tính năng mới hoặc can thiệp farm, BẮT BUỘC chạy `python D:/Taadaa/tools/sol_planner.py` để Sol Web (:20129) lập kế hoạch Tầng A.
- Đóng Patch Contract duy nhất tuyệt đối cho worker, giới hạn <= 15 calls. Không để worker chạy live request dài gây timeout, tách riêng unit test mock 100% chạy <10s.

---

## 5. Cron Job Định Kỳ
- Job: `daily-tiktok-farm-tracker` (`cron_tiktok_daily_tracker.py`, 07:00 sáng hàng ngày).
- Quét toàn bộ ~592 nick từ `taikhoan_run_safe.xlsx`.
- Xuất file Excel: `D:/OneDrive/TaadaaData/kibe/tiktok_stats_farm.xlsx` (OneDrive) và `D:/Taadaa/reports/tiktok_tracker_report.xlsx`.
- Bắn tin nhắn tóm tắt qua Telegram chat.
