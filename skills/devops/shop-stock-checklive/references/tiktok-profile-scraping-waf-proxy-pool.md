# TikTok Profile Web Scraping: SlardarWAF vs NOT_FOUND & MobiProxy Pool Rotation

## 1. Cơ chế và cạm bẫy SlardarWAF
Khi cào dữ liệu profile TikTok qua endpoint web (`https://www.tiktok.com/@username`) để track follower/stats hoặc check live:
- TikTok thường xuyên chặn IP/bot bằng trang challenge WAF chứa chuỗi `SlardarWAF`.
- Trong trang WAF này, thẻ `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">` hoàn toàn không tồn tại.
- **Bẫy ngộ nhận DIE**: Nếu code parser chỉ kiểm tra sự tồn tại của script tag này và fallback về `status: 'NOT_FOUND'`, toàn bộ tài khoản LIVE bị dính WAF sẽ bị đánh đồng thành `NOT_FOUND` / `DIE`.

## 2. Tiêu chuẩn phân loại trạng thái (Status Resolution)
| Trạng thái | Điều kiện xác định | Xử lý |
|---|---|---|
| **LIVE** | Trích xuất được JSON `userInfo`, `statusCode == 0` | Lưu snapshot, cập nhật follower/heart |
| **NOT_FOUND (Thật)** | JSON có `statusCode == 10221` hoặc HTTP status code 404 | Xác nhận nick DIE / biến mất thật |
| **BLOCKED / WAF** | HTML chứa `SlardarWAF` và thiếu JSON hydration | **CẤM gán NOT_FOUND/DIE**. Đổi proxy & retry |
| **ERROR** | Exception `requests.Timeout`, `ConnectionError` | Đổi proxy & retry; cạn retry giữ `ERROR` |

## 3. Cấu hình MobiProxy 32 Ports & Smart Retry
Dải 32 cổng MobiProxy xoay vòng trên gateway nội bộ farm:
```python
PROXY_POOL = [
    f'http://TaadaaMobi%232026%21:TaadaaMobi%232026%21@192.168.110.2:{port}'
    for port in range(20001, 20033)
]
```

### Quy trình Retry:
1. Gặp `SlardarWAF` hoặc `Timeout` / `ConnectionError`.
2. Loại trừ proxy vừa thất bại (`tried_proxies`), chọn ngẫu nhiên proxy mới từ pool.
3. Cho phép tối đa 2 lần retry (tổng 3 lượt request).
4. Nếu sau 2 lần retry vẫn thất bại: Trả về `status: 'BLOCKED'` hoặc `status: 'ERROR'`, không đưa vào danh sách DIE / dọn kho.

## 4. Giải mã thời gian tạo tài khoản & đăng video qua TikTok 64-bit Snowflake ID
Mọi định danh ID trong hệ sinh thái ByteDance (User ID `uploader_id`, Video ID `aweme_id`, Comment ID) đều là 64-bit snowflake ID. Trong đó **32 bit cao nhất** chính là Unix timestamp (tính theo giây) tại thời điểm khởi tạo:
```python
import datetime

def decode_tiktok_id_timestamp(snowflake_id: int or str) -> datetime.datetime:
    ts = int(snowflake_id) >> 32
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)

# Ví dụ thực tế:
# User ID: 7614058181921326098
# 7614058181921326098 >> 32 = 1772786067 -> 2026-03-06 08:34:27 UTC (15:34:27 GMT+7)
```
- **Ứng dụng audit / checklive / farm**: Cho phép xác định chính xác tuổi đời tài khoản (account age), ngày tạo gốc của clone/nick mua, ngày đăng video đầu tiên và chu kỳ đăng mà không cần quyền sở hữu tài khoản hay gọi API private.
- **Tích hợp vào Tracker & Checklive Report**:
  - Khi cào profile qua `parse_tiktok_html()` hoặc public endpoint, trích xuất `uid_val = str(user.get('id', ''))`.
  - Hàm chuẩn hóa:
    ```python
    def extract_creation_time(uid: Union[str, int], date_only: bool = True) -> str:
        if not uid:
            return ""
        try:
            val = int(str(uid).strip())
            if val <= 0:
                return ""
            ts = val >> 32
            if not (1400000000 <= ts <= 2500000000):
                return ""
            dt = datetime.fromtimestamp(ts)
            return dt.strftime("%Y-%m-%d") if date_only else dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""
    ```
  - **Auto-migration SQLite**: Khi bổ sung cột `created_at` vào bảng `snapshots` (`D:/Taadaa/data/tiktok_tracker.db`), luôn kiểm tra PRAGMA và chạy `ALTER TABLE snapshots ADD COLUMN created_at TEXT` an toàn trong try/except để không làm crash DB cũ.
  - **Xuất báo cáo Excel / Bàn giao**: Cột `"Ngày Tạo"` đặt ngay sau `"UID"` để dễ dàng phân loại tài khoản theo độ ngâm (aged accounts vs new reg).
  - **Cạm bẫy Unit Test kiểm tra vị trí cột Excel**: Khi chèn `"Ngày Tạo"` vào ngay sau `"UID"` (vị trí index 4), toàn bộ các cột phía sau (`Follower`, `Tăng Follow`, `Tổng Like`, `Trạng Thái`, `Avatar`, `Cắn Đề Xuất`) sẽ bị tịnh tiến chỉ số (+1 index). Các unit tests kiểm tra theo index cứng (ví dụ `assert row[4] == follower`, `assert row[9] == 'LIVE'`) bắt buộc phải cập nhật tương ứng (`row[5] == follower`, `row[10] == 'LIVE'`, `row[11] == 'CÓ'`, v.v.) và bổ sung `assert "Ngày Tạo" in headers` để tránh vỡ kiểm thử hồi quy.

## 5. Bóc tách Full Profile & Video qua yt-dlp Native Challenge Solver
Khi cào web gặp SlardarWAF hoặc giao diện browser bị dính Popup Puzzle Slider ("Drag the slider to fit the puzzle"), `yt-dlp` có cơ chế giải JS challenge ngầm natively cực mạnh:
```bash
# Dump toàn bộ video và metadata kênh không bị chặn WAF / Captcha:
yt-dlp --flat-playlist --dump-json "https://www.tiktok.com/@username"
```
Kết hợp bóc tách metadata:
- `view_count`, `like_count`, `comment_count`, `save_count`, `repost_count`
- `duration`, `upload_date`, `track` (âm thanh/nhạc sử dụng)
- `channel_id` (SecUid), `uploader_id` (User ID -> tính được tuổi acc)

