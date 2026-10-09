# Dynamic Continuous Interaction Rates (Phân phối mềm động tương tác)

Cập nhật dải tương tác mềm (soft continuous distributions) cho Feed Swipe (`python_runner/flows/feed_swipe_smoke.py`):

## 1. Dải tỷ lệ Like (`_feed_like_rates`)
Khi config không ghi đè tỷ lệ like cố định (`raw is None`), tỷ lệ like được tạo ngẫu nhiên theo dải động liên tục:
- **For You (`FEED_TYPE_FOR_YOU`)**: `random.randint(5, 12)` (5% - 12%)
- **Following (`FEED_TYPE_FOLLOWING`)**: `random.randint(30, 60)` (30% - 60%)
- **Friends (`FEED_TYPE_FRIENDS`)**: `random.randint(50, 80)` (50% - 80%)

## 2. Dải tỷ lệ Comment Peek (`_maybe_peek_comments`)
- Áp dụng trên video deep inspect (`is_deep_inspect_video`).
- Phân phối động: `peek_rate = random.randint(8, 16)` (8% - 16%), truyền qua tham số `peek_rate_percent`.
- Cho phép xem lướt comment tự nhiên mà không làm dồn dập tần suất mở bình luận trên toàn bộ chuỗi video.
