# TikTok Realtime Avatar Status & Tracker DB Single Source of Truth

## Bối cảnh & Vấn đề
- Trước đây, watchdog upload avatar (`post_evening_avatar_watchdog.py`) lọc danh sách máy cần up avatar bằng cách đọc cột `Avatar` trong file Excel workbook (`TikN.xlsx`).
- **Lỗ hổng thực tế:**
  1. Trong Excel ghi `Avatar = 'OK'`, nhưng trên TikTok thật nick chưa bao giờ được đặt avatar (hoặc dùng avatar mặc định của hệ thống).
  2. Dẫn đến watchdog bị "mù", tưởng đã up đủ nên bỏ qua các máy chưa có avatar (ví dụ thực tế: Máy 42 `@seifeespe23` và Máy 30 `@kiki90456` đều là avatar silhouette mặc định nhưng trong Excel ghi `OK`).
  3. Rule cũ trên Web Dashboard chỉ lưu số liệu follower/heart/status, không lưu trạng thái avatar thật và rule cắn đề xuất bị lỏng (`> 0`) dẫn đến báo sai lệch.

---

## 1. Định nghĩa chuẩn Avatar Mặc Định (Default Avatar) trên TikTok
Khi inspect payload JSON `__UNIVERSAL_DATA_FOR_REHYDRATION__` từ trang profile TikTok (`https://www.tiktok.com/@username`), trường `avatarThumb` hoặc `avatarLarger` của nick chưa đổi avatar luôn trỏ về các CDN object mặc định:
- Chứa URL pattern: `musically-maliva-obj` hoặc ID `1594805258216454`.
- Hoặc trường avatar rỗng / `None`.

```python
def is_default_avatar(avatar_url: str) -> bool:
    if not avatar_url:
        return True
    u = str(avatar_url).lower()
    return "musically-maliva-obj" in u or "1594805258216454" in u
```

---

## 2. Chuẩn hóa Ngưỡng Cắn Đề Xuất (Trending Rule)
- Rule lỏng cũ: `delta_f > 0 or delta_h > 0` ➔ Sai lệch nghiêm trọng (20% nick rác tăng +1 tim bị đánh dấu nhầm).
- **Rule chuẩn hóa:**
  - `delta_follower >= 20` **HOẶC** `delta_heart >= 50` (hoặc `follower >= 1000 and status == 'LIVE'`).
  - Đồng bộ 100% giữa `tiktok_dashboard.py`, `tiktok_account_tracker.py`, và các test suites.

---

## 3. Kiến trúc Single Source of Truth: TikTok Tracker DB (`tiktok_tracker.db`)
- Bỏ hoàn toàn việc đọc cột `Avatar` trong file Excel để quyết định máy nào cần up avatar.
- Nguồn sự thật duy nhất là database SQLite tại `D:/Taadaa/data/tiktok_tracker.db`:
  - Bảng `snapshots`: Lưu lịch sử quét realtime từ TikTok (`avatar_thumb`, `has_avatar`, `follower`, `heart`, `status`).
  - Bảng `farm_account_info`: Lưu ánh xạ cấu hình máy (`username`, `may`, `tik`, `updated_at`).

### Truy vấn lấy danh sách máy thiếu avatar theo từng Tik:
```sql
WITH Ranked AS (
    SELECT s.username, s.status, s.has_avatar,
           ROW_NUMBER() OVER (PARTITION BY s.username ORDER BY s.id DESC) as rn
    FROM snapshots s
)
SELECT DISTINCT m.may
FROM farm_account_info m
LEFT JOIN Ranked r ON m.username = r.username AND r.rn = 1
WHERE m.tik = ? AND (r.has_avatar = 0 OR r.has_avatar IS NULL)
ORDER BY m.may;
```

---

## 4. Nguyên tắc Vận Hành & Fallback
1. Watchdog upload avatar (`post_evening_avatar_watchdog.py`) ưu tiên kết nối `file:tiktok_tracker.db?mode=ro` để lấy danh sách máy thiếu avatar thực tế.
2. Chỉ fallback đọc Excel nếu database không tồn tại hoặc bị lỗi I/O.
3. Khi thêm tính năng/trường mới vào Tracker, nếu dữ liệu snapshot cũ là `NULL`, phải kích hoạt tiến trình backfill quét ngầm để lấp đầy dữ liệu thực tế trước khi hiển thị/báo cáo.
