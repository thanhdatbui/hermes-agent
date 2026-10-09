# Dynamic Continuous Interaction Rates (Like & Comment Peek)

Cập nhật và chuẩn hóa dải tương tác mềm liên tục (soft continuous distributions) trong luồng Feed Swipe (`python_runner/flows/feed_swipe_smoke.py`):

## 1. Dải tỷ lệ Like động theo tab (`_feed_like_rates`)
Khi config không ghi đè tỷ lệ like (`raw is None`), tỷ lệ like được chọn ngẫu nhiên theo từng phiên chạy (session-level random distribution):
- **For You (`FEED_TYPE_FOR_YOU`)**: `random.randint(5, 12)` (5% - 12%) - trước đây là giá trị cố định 8%.
- **Following (`FEED_TYPE_FOLLOWING`)**: `random.randint(30, 60)` (30% - 60%)
- **Friends (`FEED_TYPE_FRIENDS`)**: `random.randint(50, 80)` (50% - 80%)

## 2. Dải tỷ lệ Comment Peek trên Deep Inspect (`_maybe_peek_comments`)
- Áp dụng độc quyền trên các video được chọn làm Deep Inspect (`is_deep_inspect_video`).
- Thay vì tỷ lệ cố định (12%), tỷ lệ được sinh động trên mỗi video:
  `peek_rate = random.randint(8, 16)` (8% - 16%), truyền qua tham số `peek_rate_percent` trong `_maybe_peek_comments(ctx, after, peek_rate_percent=peek_rate)`.
- Hành vi:
  - Mở xem bình luận, lướt đọc một vài comment ngẫu nhiên rồi đóng lại an toàn.
  - Phân phối 8% - 16% giúp hành vi lướt tự nhiên, tạo độ lệch chuẩn (entropy), tránh pattern máy móc lặp lại cố định.
