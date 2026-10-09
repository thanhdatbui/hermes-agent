# TikTok Farm Public Account Tracking & Web Dashboard

## Bối cảnh & Mục tiêu
Theo dõi chỉ số tăng trưởng (follower, total heart/like, video count, UID, secUid, trạng thái LIVE/DIE, phát hiện nick cắn đề xuất) cho toàn bộ danh sách tài khoản Phone Farm mà không cần can thiệp thiết bị Android thật, không cần tài khoản đăng nhập hay phụ thuộc vào dịch vụ SaaS trả phí bên ngoài.

---

## 1. Cơ chế bóc tách Public Web Profile (Không chạm thiết bị)
- **Endpoint công khai:** `https://www.tiktok.com/@{username}`.
- **Mobile Safari User-Agent Bắt Buộc:**
  ```python
  MOBILE_HEADERS = {
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8',
  }
  ```
- **Trích xuất JSON:**
  Dữ liệu profile được TikTok nhúng sẵn trong thẻ:
  `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>({.*?})</script>`
  Tại path `__DEFAULT_SCOPE__.webapp.user-detail`:
  - `userInfo.user.id`: UID gốc của tài khoản.
  - `userInfo.user.uniqueId`: Handle username.
  - `userInfo.user.nickname`: Tên hiển thị.
  - `userInfo.stats.followerCount`: Lượng follower.
  - `userInfo.stats.heartCount`: Tổng like/tim.
  - `userInfo.stats.videoCount`: Số lượng video công khai.

---

## 2. Bẫy SlardarWAF vs NOT_FOUND / DIE (CỰC KỲ QUAN TRỌNG)
- **Triệu chứng:** Khi bắn request dồn dập từ 1 IP, TikTok trả về trang HTML chứa `SlardarWAF` (~1400 bytes) và không có thẻ hydration JSON.
- **Bẫy tai hại:** Nếu thấy không có JSON mà kết luận ngay nick `NOT_FOUND` hoặc `DIE`, hàng trăm nick sống sẽ bị báo tử nhầm (false negative).
- **Quy tắc phân biệt:**
  1. Chỉ kết luận nick DIE/NOT_FOUND khi có hydration JSON và `statusCode == 10221` hoặc `userInfo is None`.
  2. Nếu HTML chứa `SlardarWAF` hoặc `slardarClient`: Đây là tín hiệu bị WAF Rate Limit tạm thời. Phải trả về `RATE_LIMITED` và xoay vòng đổi proxy khác để retry (tối đa 2 lần).

---

## 3. Quản lý Proxy Pool (Chuẩn hóa 67 Proxy Farm)
- **Nguồn chuẩn:** Đọc từ file danh sách proxy canonical `D:/Taadaa/Tiktok-video/proxy_pool_67.txt` (định dạng `host:port:user:pass`).
- **Mật khẩu ký tự đặc biệt:** Mật khẩu proxy thường chứa `#` và `!` (vd `TaadaaMobi#2026!`). Bắt buộc URL-encode user và pass bằng `urllib.parse.quote(..., safe="")` trước khi ghép thành URL:
  `http://{user_enc}:{pwd_enc}@{host}:{port}`.
- Không tự ý quét đè các file pool khác để tránh cộng dồn cổng trùng lặp.

---

## 4. Tích hợp Web Dashboard vào Cổng Quản Trị Cố Định (MikroTik Web Manager :2310)
- **Bối cảnh:** Không mở thêm cổng lạ (như 1905, 20130) để tránh bị Windows Firewall chặn kết nối từ điện thoại ra ngoài LAN.
- **Quy chuẩn tích hợp:**
  Ghép thẳng route `/tiktok` và `/api/tiktok` vào `D:/Taadaa/AI-Tools/tools/mikrotik_web/server.py` đang chạy cổng `2310`:
  - Router MikroTik đã gán static DNS: `kibe` -> `192.168.110.123`.
  - Trên điện thoại mở: `http://kibe:2310/tiktok` hoặc vào `http://kibe:2310/` bấm nút tab `🎵 TikTok Farm`.
- **Lưu ý Safari Mobile:** Khi gõ trên Safari điện thoại, bắt buộc kèm port `:2310`. Nếu chỉ gõ `kibe`, Safari sẽ mặc định gọi port 80. Có thể kèm daemon redirector port 80 -> 2310 để user gõ gọn `kibe`.

---

## 5. Trích xuất Ngày Tạo (Creation Date) từ Snowflake User ID
- **Nguyên lý Snowflake ID:** TikTok User ID là số nguyên 64-bit. Trong đó 32 bit cao nhất (`int(uid) >> 32`) là Unix timestamp (giây) tại thời điểm khởi tạo tài khoản.
- **Hàm trích xuất an toàn (`extract_creation_time`):**
  ```python
  def extract_creation_time(uid: Union[str, int], date_only: bool = True) -> str:
      if not uid:
          return ""
      try:
          val = int(str(uid).strip())
          if val <= 0:
              return ""
          ts = val >> 32
          if 1400000000 <= ts <= 2500000000:
              dt = datetime.fromtimestamp(ts)
              return dt.strftime("%Y-%m-%d") if date_only else dt.strftime("%Y-%m-%d %H:%M:%S")
      except Exception:
          pass
      return ""
  ```
- **Lưu trữ & Migration:** Thêm cột `created_at TEXT` vào bảng SQLite `snapshots`. Luôn chạy safe migration `ALTER TABLE snapshots ADD COLUMN created_at TEXT` nếu cột chưa tồn tại để tránh xung đột database cũ.

---

## 6. User Preference: Web Dashboard First (Cấm Xuất File Báo Cáo Mỗi Ngày)
- **Quy tắc vận hành:** User yêu cầu **KHÔNG xuất file báo cáo Excel hàng ngày** (tránh rác bộ nhớ, spam file, phân tán theo dõi).
- **Trực quan hóa tập trung:** Mọi số liệu theo dõi (Followers, Tim, Đã follow, Trạng thái, Ngày tạo, Cắn đề xuất, Anomaly drop) phải được hiển thị, tìm kiếm và sắp xếp trực tiếp trên **Web Dashboard** (`tiktok_dashboard.py` / route `/tiktok`). User chỉ cần mở trình duyệt/điện thoại để xem realtime.
- **Tính năng trên giao diện Web Dashboard:**
  - Bổ sung cột **Ngày Tạo** trong bảng dữ liệu `<table>`.
  - Hỗ trợ sắp xếp (`sortTable('created_at')`) và tìm kiếm theo ngày tạo trong ô `searchInput`.
  - Giữ nguyên cấu trúc mobile-responsive (`data-label="Ngày Tạo"`).

