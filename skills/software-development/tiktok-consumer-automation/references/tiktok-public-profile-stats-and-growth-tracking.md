# TikTok Public Profile Stats & Growth Tracking (Zero-Device WAF Bypass)

## Bối cảnh & Mục đích
Theo dõi chỉ số tăng trưởng (Followers, Likes, Video count, Friend count, trạng thái Live/Die) của toàn bộ dàn tài khoản TikTok trong Phone Farm một cách tự động, nhanh chóng mà **không cần chạm vào thiết bị thật (S7)**, không cần đăng nhập, và không tốn chi phí cho các dịch vụ SaaS bên ngoài (như Exolyt, Social Blade).

---

## Cơ chế Bypass WAF & Trích xuất Dữ liệu

### 1. Hiện tượng chặn trên Desktop Browser / Bot thông thường
- Khi gửi request với User-Agent Chrome/Firefox Desktop hoặc curl thông thường đến `https://www.tiktok.com/@{username}`, TikTok kích hoạt hệ thống WAF **Slardar** (`slardar_us_waf` / `browser.sg.js`), trả về HTML rỗng (<2KB) kèm script thử thách token và chặn trích xuất dữ liệu.
- Công cụ `yt-dlp` khi tải profile user thường văng lỗi: `ERROR: Unable to extract secondary user ID` do thiếu impersonate browser engine.

### 2. Giải pháp Mobile Safari User-Agent (Bypass 100% không dính Slardar)
Gửi HTTP GET trực tiếp với Header giả lập trình duyệt Mobile Safari:
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
}
```

### 3. Cấu trúc Rehydration JSON Payload
TikTok trả về HTML đầy đủ chứa thẻ script rehydration:
`<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">({JSON_PAYLOAD})</script>`

Trích xuất JSON qua Regex:
`re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>({.*?})</script>', response.text)`

**Key map trong JSON:**
`scope = data['__DEFAULT_SCOPE__']['webapp.user-detail']`

#### Trạng thái tài khoản LIVE:
- `userInfo = scope['userInfo']`
- **Thông tin cơ bản (`userInfo['user']`):**
  - `id`: UID số duy nhất của tài khoản (VD: `7609673791706825735`)
  - `uniqueId`: Username TikTok (VD: `lipsellczaw`)
  - `nickname`: Tên hiển thị (VD: `Mai Anh🥑🥑`)
  - `secUid`: Mã bảo mật SecUID dùng cho API TikTok
- **Thống kê (`userInfo['stats']`):**
  - `followerCount`: Tổng số người theo dõi
  - `followingCount`: Số người đang theo dõi
  - `heartCount`: Tổng lượt thích toàn bộ video
  - `videoCount`: Số lượng video đang public
  - `friendCount`: Bạn bè (follow chéo hai chiều)

#### Trạng thái tài khoản DIE / BANNED / NOT FOUND:
- `scope.get('statusCode') == 10221` hoặc `userInfo is None`
- Đánh dấu trạng thái: `DIE_OR_BANNED`

---

## Kiến trúc Tool Theo dõi Danh sách Farm (`tiktok_account_tracker.py`)

1. **Nguồn dữ liệu (Single Source of Truth):**
   - Đọc trực tiếp từ `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (cột `May`, `Device ID`, `ID`, `Video Đã Đăng`).
   - Hỗ trợ fallback sang file Excel/TXT custom qua CLI `--source`.

2. **Lưu trữ Lịch sử & Đo biến động ($\Delta$):**
   - Lưu snapshot theo ngày vào SQLite database `D:\Taadaa\runtime\kibe\tiktok_tracker\tracker.db`.
   - Tính toán độ tăng trưởng hàng ngày:
     - $\Delta \text{Follower} = \text{Follower}_{\text{hôm nay}} - \text{Follower}_{\text{hôm qua}}$
     - $\Delta \text{Heart} = \text{Heart}_{\text{hôm nay}} - \text{Heart}_{\text{hôm qua}}$
   - Gắn cờ **CẮN ĐỀ XUẤT** khi $\Delta \text{Follower} \ge 100$ hoặc $\Delta \text{Heart} \ge 500$ trong 24h.

3. **Báo cáo & Tích hợp:**
   - Xuất file Excel báo cáo tiến độ: `D:\OneDrive\TaadaaData\kibe\tiktok_stats_daily.xlsx`.
   - Bắn tin tóm tắt hàng ngày qua Telegram (Top nick tăng trưởng, tổng follower farm, cảnh báo nick die).
