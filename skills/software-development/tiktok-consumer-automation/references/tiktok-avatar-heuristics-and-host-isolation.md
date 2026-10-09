# TikTok Default Avatar Heuristics & Host Isolation for Uploader

## 1. Cơ chế Nhận diện Avatar Mặc định (Web Scraping / Profile Payload)
Không dựa vào trạng thái ghi trong file Excel (`Avatar = 'OK'`). Excel thường xuyên bị out-of-sync hoặc đánh dấu sai.
Lấy dữ liệu trực tiếp từ thẻ `__UNIVERSAL_DATA_FOR_REHYDRATION__` của TikTok profile:
- **Default Avatar**: URL trỏ về CDN musically object (`musically-maliva-obj` hoặc ID `1594805258216454`).
- **Custom Avatar**: URL trỏ về avt object thật (`tos-alisg-avt-0068`, `tos-maliva-avt-0068`).

```python
def is_default_avatar(avatar_url: str) -> bool:
    if not avatar_url:
        return True
    u = avatar_url.lower()
    return "musically-maliva-obj" in u or "1594805258216454" in u
```

## 2. Cách ly Phân vùng Thiết bị (Host Boundary Isolation)
Khi hợp nhất cơ sở dữ liệu `tiktok_tracker.db` giữa máy Kibe (máy 1..80) và Admin (máy 201..280):
- Bảng `farm_account_info` lưu kèm cột `host_id` (`kibe` hoặc `admin`).
- Script watchdog upload avatar (`post_evening_avatar_watchdog.py`) chạy trên Kibe chỉ query máy có `host_id = 'kibe'` và dải máy 1..80.
- Script watchdog chạy trên Admin chỉ query máy có `host_id = 'admin'` và dải máy 201..280.
- Tuyệt đối cấm cross-device execution: Kibe không gửi lệnh ADB sang dải máy Admin và ngược lại.
