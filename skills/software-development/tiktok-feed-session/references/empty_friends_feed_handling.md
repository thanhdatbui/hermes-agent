# Xử Lý Màn Hình Gợi Ý Kết Nối Bạn Bè / Danh Bạ Rỗng Trong Feed Session

## 1. Bản Chất Vấn Đề
Khi tài khoản mới hoặc tài khoản chưa đồng bộ danh bạ/bạn bè chuyển sang tab Bạn bè (Friends) hoặc Đang follow (Following), TikTok thường hiển thị giao diện rỗng kèm các lời mời:
- "Kết nối với bạn bè để xem bài đăng"
- "Tìm các liên hệ của bạn"
- "Kết nối với liên hệ trong danh bạ"
- "Kết nối với bạn bè trên Facebook"
- "Hãy follow bạn bè" / "bạn sẽ nhận thấy họ ở đây" / "xem video mới nhất của họ tại đây"

Nếu không xử lý:
- Tỷ lệ tương tác (like/follow) và phân bổ feed bị lệch do tính cả các màn hình rỗng này vào mẫu số `feed_counts`.
- Máy có thể bị kẹt ở tab rỗng không có video thực tế để lướt.

## 2. Quy Tắc Chuẩn Hóa Trong `feed_swipe_smoke.py`

### Bổ Sung Từ Khóa Nhận Diện (`_FRIENDS_FEED_CONTENT_TERMS`)
Bổ sung đầy đủ các chuỗi UI xuất hiện khi tab Friends/Following không có video:
```python
_FRIENDS_FEED_CONTENT_TERMS = (
    "Hãy follow bạn bè",
    "Nhật ký",
    "Tác giả nổi bật",
    "bạn sẽ nhận thấy họ ở đây",
    "xem video mới nhất của họ tại đây",
    "Khi bạn Follow",
    "Kết nối với bạn bè để xem bài đăng",
    "Tìm các liên hệ của bạn",
    "Kết nối với liên hệ trong danh bạ",
    "Kết nối với bạn bè trên Facebook",
)
```

### Fallback Về For You & Gắn Cờ `is_empty_feed_fallback`
Khi phát hiện màn hình rỗng (`_has_friends_feed_content(after)`):
1. Chuyển tab về For You qua `tap_navigation_target(ctx, _top_tab_target(FEED_TYPE_FOR_YOU), ...)`.
2. Khi thành công (`fb_res.ok`):
   - Chuyển `current_feed_type = FEED_TYPE_FOR_YOU`
   - Gắn cờ: `after["is_empty_feed_fallback"] = True`

### Loại Bỏ Khỏi Mẫu Số `feed_counts`
Trong hàm tổng hợp `_feed_action_counts(table)`:
Row chỉ được cộng vào `feed_counts[feed_type]` khi nó là một video thật sự được lướt, không phải màn hình gợi ý kết nối bạn bè rỗng:
```python
if row.get("action") == "swipe" and feed_type in feed_counts:
    if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
        feed_counts[feed_type] += 1
```
Điều này đảm bảo like rate, follow rate và feed distribution phản ánh đúng số video thực tế người dùng đã xem.
