# Empty Friends Feed Detection & Metric Accounting

## 1. Cơ chế Empty Suggestion Feed Fallback
Khi account mở tab **Friends / Bạn bè** nhưng tài khoản chưa có nhiều bạn bè hoặc bạn bè chưa đăng video, TikTok sẽ hiển thị các màn hình gợi ý kết bạn thay vì video feed dạng lướt thông thường.

Khi gặp các màn hình này:
- Flow `feed_swipe_smoke.py` tự động chuyển tiếp (`tap_navigation_target`) sang tab `for-you`.
- Row sự kiện swipe ghi nhận hành động này được gắn cờ:
  ```python
  after["is_empty_feed_fallback"] = True
  ```

## 2. Danh sách Content Terms nhận diện (`_FRIENDS_FEED_CONTENT_TERMS`)
Bao gồm các chuỗi văn bản XML đặc trưng:
- `"Hãy follow bạn bè"`
- `"Nhật ký"`
- `"Tác giả nổi bật"`
- `"bạn sẽ nhận thấy họ ở đây"`
- `"xem video mới nhất của họ tại đây"`
- `"Khi bạn Follow"`
- `"Kết nối với bạn bè để xem bài đăng"`
- `"Tìm các liên hệ của bạn"`
- `"Kết nối với liên hệ trong danh bạ"`
- `"Kết nối với bạn bè trên Facebook"`

## 3. Quy tắc tính mẫu số `feed_counts` trong `_feed_action_counts`
Để tỷ lệ tương tác (like / comment / favorite / follow) trên tab Friends phản ánh đúng số video bạn bè thực tế (không bị loãng mẫu số bởi các màn hình fallback trống):
- Các hàng có `row.get("is_empty_feed_fallback")` hoặc `_has_friends_feed_content(row)` **KHÔNG** được tính vào `feed_counts[feed_type]`:
  ```python
  if row.get("action") == "swipe" and feed_type in feed_counts:
      if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
          feed_counts[feed_type] += 1
  ```
