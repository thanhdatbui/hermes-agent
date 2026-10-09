# Case 180: Friends Tab Empty Suggestion Screen Denominator Leakage & Feed Action Filtering

## Triệu chứng & Hiện tượng
- Báo cáo watchdog nuôi TikTok ghi nhận tỷ lệ tim Bạn bè (Friends) tụt sâu bất thường: `Bạn bè: 2 (8.7%)` dù tỉ lệ cấu hình là 35-50% và trên máy có video thật (ví dụ Máy 44) đạt 100% (2 tim / 2 video).
- Người vận hành phản ánh: "Ủa màn rỗng thì mắc gì tính vào mẫu số để r chia ra % bé?".

## Root Cause
Phân tích hiện trường XML trên 80 máy (Máy 2, Máy 26, Máy 44...):
1. **Lệch từ khóa nhận diện màn hình rỗng (`_FRIENDS_FEED_CONTENT_TERMS`):**
   - Bộ từ khóa cũ chỉ chứa: `"Hãy follow bạn bè"`, `"Nhật ký"`, `"Tác giả nổi bật"`, `"bạn sẽ nhận thấy họ ở đây"`, `"xem video mới nhất của họ tại đây"`, `"Khi bạn Follow"`.
   - UI TikTok mới hiển thị các biến thể màn hình gợi ý kết nối danh bạ / Facebook:
     - Máy 26: `"Kết nối với bạn bè để xem bài đăng của họ"`, `"Kết nối với liên hệ trong danh bạ"`, `"Kết nối với bạn bè trên Facebook"`.
     - Máy 2: `"Danh bạ"`, `"Tìm các liên hệ của bạn"`, `"Follow bạn"`.
   - Do không khớp từ khóa, runner không kích hoạt `fallback_to_for_you` mà tiếp tục swipe trên màn hình danh bạ.

2. **Rò rỉ mẫu số trong `_feed_action_counts`:**
   - Logic cũ: cứ mỗi `row["action"] == "swipe"` và `feed_type == "friends"` là cộng dồn `feed_counts["friends"] += 1`.
   - Các màn hình danh bạ / gợi ý kết nối không có video player và không có nút Like ("Thích video") $\rightarrow$ 0 like.
   - Khi đó 24 lượt swipe trên màn hình rỗng bị tính oan vào mẫu số `feed_counts["friends"]` (tổng 26 video, 2 like $\rightarrow$ 7.7% ~ 8.7%).

## Giải pháp Chuẩn (Code Surgery Contract)
File: `python_runner/flows/feed_swipe_smoke.py`

1. **Bổ sung từ khóa nhận diện màn hình gợi ý rỗng vào `_FRIENDS_FEED_CONTENT_TERMS`:**
   ```python
   _FRIENDS_FEED_CONTENT_TERMS = (
       "Hãy follow bạn bè",
       "Nhật ký",
       "Tác giả nổi bật",
       "bạn sẽ nhận thấy họ ở đây",
       "xem video mới nhất của họ tại đây",
       "Khi bạn Follow",
       # UI biến thể kết nối danh bạ & Facebook:
       "Kết nối với bạn bè để xem bài đăng",
       "Kết nối với liên hệ trong danh bạ",
       "Tìm các liên hệ của bạn",
       "Kết nối với bạn bè trên Facebook",
   )
   ```

2. **Lọc mẫu số trong `_feed_action_counts` (Chỉ tính video player thật):**
   - Không đếm lượt swipe vào `feed_counts[feed_type]` nếu màn hình là gợi ý rỗng hoặc không phải video stream hợp lệ.
   - Màn rỗng / danh bạ không được tính làm mẫu số chia tỷ lệ like.
