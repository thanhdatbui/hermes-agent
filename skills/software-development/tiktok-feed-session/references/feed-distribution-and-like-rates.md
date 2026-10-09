# Cấu Hình Phân Bổ Feed & Tỉ Lệ Thả Tim Nuôi Acc (feed-session-smoke)

## 1. Thông Số Chuẩn Phân Bổ Feed & Thả Tim (Cập nhật 2026-09-08)

Định nghĩa tại `python_runner/flows/feed_swipe_smoke.py`:

```python
DEFAULT_FEED_DISTRIBUTION = {
    FEED_TYPE_FOR_YOU: 0.70,   # 70% Đề xuất (giữ interest graph, tránh bị gắn cờ pod ảo)
    FEED_TYPE_FOLLOWING: 0.15, # 15% Đang follow (ghé xem video kênh follow)
    FEED_TYPE_FRIENDS: 0.15,   # 15% Bạn bè (~2 video/phiên để kích hoạt đẩy đề xuất chéo)
}

DEFAULT_FEED_LIKE_RATES = {
    FEED_TYPE_FOR_YOU: 8,      # 8% danh nghĩa (nhịp Deep Inspect bù 40% ngẫu nhiên)
    FEED_TYPE_FOLLOWING: 30,   # 30% tim vừa phải cho nick follow/ngoài
    FEED_TYPE_FRIENDS: 70,     # 70% tim bạn bè nội bộ dàn máy (độ nhiễu tự nhiên 30% bỏ qua)
}
```

## 2. Pitfall Kiến Trúc: Fast Swipe vs Like Rate Từng Tab

- **Đặc thù tab:** Fast Swipe (lướt nhanh không dump XML) **CHỈ áp dụng cho tab Đề xuất (For You)**.
- Khi chuyển sang tab Following hoặc Friends, hệ thống **bắt buộc Deep Inspect 100%** từng video (dump XML đầy đủ, kiểm tra tương tác chuẩn).
- **Lỗi từng gặp (Đã fix):** Nhịp Deep Inspect trước đây dùng guard:
  ```python
  if is_feed_session and fast_swipe["enabled"] and ctx.config.get("_like_rate", ...) is None:
      _deep_like_rate = fast_swipe["deep_like_rate_percent"]  # 40%
  else:
      _deep_like_rate = like_rates.get(current_feed_type, like_rate_percent)
  ```
  Guard trên thiếu kiểm tra `current_feed_type == FEED_TYPE_FOR_YOU`, làm cho cả tab Friends (70%) và Following (30%) bị ghi đè thành 40%.
- **Quy tắc bất biến:** Phải có `and current_feed_type == FEED_TYPE_FOR_YOU` để các tab Bạn bè & Following luôn ăn đúng tỷ lệ cấu hình riêng từ `like_rates`.

## 3. Pitfall Môi Trường Khi Chạy Test

Khi chạy pytest trong repo `tiktok-luot nuoi acc`:
```bash
PYTHONPATH="" D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest python_runner/tests/test_feed_swipe_smoke.py -k "<test_name>"
```
- **Lý do:** Session terminal có thể kế thừa `PYTHONPATH` chứa package của `hermes-agent` (đặc biệt là PIL/Pillow), gây lỗi xung đột binary `ImportError: cannot import name '_imaging' from 'PIL'`. Luôn set `PYTHONPATH=""` trước lệnh python/pytest.
