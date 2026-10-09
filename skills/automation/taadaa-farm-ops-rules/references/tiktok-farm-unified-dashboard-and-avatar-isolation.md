# Quy chuẩn Quản trị Hợp nhất Đa cụm Farm (Kibe vs Admin) & Cơ chế Lọc Avatar Realtime

## 1. Bối cảnh & Mục tiêu
Khi hợp nhất danh sách theo dõi tài khoản TikTok từ nhiều host (ví dụ: host `kibe` máy 1-80 và host `admin` máy 201-280) về chung một Web Dashboard / Database duy nhất (`D:/Taadaa/data/tiktok_tracker.db`):
- **Web Dashboard**: Hiển thị hợp nhất toàn bộ tài khoản farm để người vận hành có bức tranh tổng thể (followers, tim, cắn đề xuất, avatar).
- **Automation Runner / Watchdog (Upload avatar, login, feed)**: **BẮT BUỘC** cách ly vật lý theo dải máy (`host_id`). Host Kibe tuyệt đối không bao giờ gửi ADB / lệnh can thiệp vào máy của Admin, và ngược lại.

---

## 2. Nhận diện Avatar Thật trên TikTok (Avatar Realtime Heuristic)
Không bao giờ dựa vào cột `Avatar` trong file Excel (thường xuyên bị ghi stale `OK` trong khi nick thực tế chưa được up avatar).

### Quy luật định danh của TikTok:
Khi request profile `https://www.tiktok.com/@username`, payload JSON `__UNIVERSAL_DATA_FOR_REHYDRATION__` trả về trường `avatarThumb` / `avatarLarger`:
- **Avatar mặc định hệ thống (Chưa đặt avatar)**: URL chứa chuỗi `musically-maliva-obj` hoặc ID `1594805258216454` (hoặc rỗng).
- **Avatar tùy chỉnh (Đã có avatar)**: URL thường có path dạng `tos-alisg-avt-0068/...` hoặc `tos-maliva-avt-0068/...` với hash ảnh thật.

### Implementation Chuẩn:
```python
def is_default_avatar(avatar_url: str) -> bool:
    if not avatar_url:
        return True
    u = avatar_url.lower()
    return "musically-maliva-obj" in u or "1594805258216454" in u
```

---

## 3. Quy chuẩn Phân vùng Phần cứng (Hardware Boundary Isolation)

### Cấu trúc Schema Mapping (`farm_account_info`):
```sql
CREATE TABLE IF NOT EXISTS farm_account_info (
    username TEXT PRIMARY KEY,
    may INTEGER,
    tik INTEGER,
    host_id TEXT DEFAULT 'kibe',
    updated_at TEXT
);
```

### Nguyên tắc Truy vấn Watchdog theo Host:
Mỗi watchdog upload avatar / can thiệp máy khi đọc từ database **BẮT BUỘC** lọc theo `host_id` của chính nó:

```python
# Kibe watchdog (Chỉ nhận máy 1..80)
c.execute("""
    WITH Ranked AS (
        SELECT s.username, s.status, s.has_avatar,
               ROW_NUMBER() OVER (PARTITION BY s.username ORDER BY s.id DESC) as rn
        FROM snapshots s
    )
    SELECT m.may, r.has_avatar
    FROM farm_account_info m
    LEFT JOIN Ranked r ON m.username = r.username AND r.rn = 1
    WHERE m.host_id = ? AND m.tik = ?
    ORDER BY m.may
""", (current_host_id, tik))
```

- Nếu `current_host_id == 'kibe'`: Bỏ qua hoàn toàn các máy > 80 (hoặc `host_id == 'admin'`).
- Nếu `current_host_id == 'admin'`: Bỏ qua hoàn toàn các máy 1..80 (hoặc `host_id == 'kibe'`).

---

## 4. Ngưỡng Cắn Đề Xuất (Viral Threshold Benchmark)
Đã chuẩn hóa thống nhất giữa Core Tracker (`tiktok_account_tracker.py`) và Web Dashboard (`tiktok_dashboard.py`):
- **Điều kiện**:
  ```python
  is_trending = (delta_follower >= 20) or (delta_heart >= 50) or (follower >= 1000 and is_live)
  ```
- **Lưu ý**: Tránh tuyệt đối ngưỡng nhạy `delta > 0` vì biến động tự nhiên (+1 fl, +1 tim) của farm 600+ acc sẽ gây tràn 20-30% false positive báo cắn đề xuất ảo.
