# TikTok Avatar Tracking: Realtime Detection & Tracker DB Truth

## 1. Vấn đề cốt lõi với file Excel
- Trước đây, watchdog upload avatar (`post_evening_avatar_watchdog.py`) lấy danh sách máy cần up avatar từ cột `Avatar` trong file Excel `TikN.xlsx`.
- **Rủi ro:** Cột Excel ghi `'OK'` (hoặc đã được đánh dấu trong quá khứ), nhưng thực tế trên TikTok nick chưa bao giờ được đổi avatar (hoặc dùng avatar silhouette mặc định).
- **Hệ quả:** Watchdog bỏ sót hàng loạt máy chưa có avatar (ví dụ Máy 42 `@seifeespe23` và Máy 30 `@kiki90456`).

---

## 2. Nhận diện Avatar mặc định (Default Avatar Detection)
Khi fetch profile qua web (`__UNIVERSAL_DATA_FOR_REHYDRATION__`), URL `avatarThumb` / `avatarLarger` của tài khoản chưa đặt avatar luôn chứa pattern CDN đặc trưng:
- Chứa `musically-maliva-obj` hoặc ID `1594805258216454`.
- Hoặc chuỗi URL rỗng / `None`.

```python
def is_default_avatar(avatar_url: str) -> bool:
    if not avatar_url:
        return True
    u = str(avatar_url).lower()
    return "musically-maliva-obj" in u or "1594805258216454" in u
```

---

## 3. Kiến trúc Single Source of Truth
- Nguồn sự thật duy nhất là database `D:/Taadaa/data/tiktok_tracker.db` (bảng `snapshots` kết hợp `farm_account_info`).
- Watchdog upload avatar truy vấn danh sách máy chưa có avatar trực tiếp từ SQLite:
  - `status == 'LIVE'`
  - `has_avatar == 0` hoặc `has_avatar IS NULL`
- Bỏ hoàn toàn sự phụ thuộc vào cột Excel để quyết định máy cần chạy avatar batch.
