# Case 180: Loại Bỏ Rò Rỉ Mẫu Số Màn Hình Gợi Ý Rỗng Tab Bạn Bè / Following & Mở Rộng Fallback Từ Khóa

## 1. Hiện Tượng & Triệu Chứng
- Báo cáo Watchdog nuôi TikTok ghi nhận tỷ lệ Like tab Bạn bè tụt sâu bất thường:
  `Thả tim: 133 tim / 1185 video (11.2%) [Đề xuất: 126 (31.5%) | Bạn bè: 2 (8.7%) | Following: 5 (50.0%)]`
- Người vận hành đặt câu hỏi: "Sao tỉ lệ thả tim bạn bè thấp vậy?" và "Màn rỗng thì mắc gì tính vào mẫu số để rồi chia ra % bé?".

## 2. Root Cause Kép
1. **Lọt lưới nhận diện màn rỗng (`_FRIENDS_FEED_CONTENT_TERMS`):**
   - Danh sách từ khóa cũ chỉ gồm: `"Hãy follow bạn bè"`, `"Nhật ký"`, `"Tác giả nổi bật"`, `"bạn sẽ nhận thấy họ ở đây"`, `"xem video mới nhất của họ tại đây"`, `"Khi bạn Follow"`.
   - Các biến thể UI mới trên TikTok khi chuyển sang tab Bạn bè trên nick mới / chưa có bạn:
     + `"Kết nối với bạn bè để xem bài đăng của họ"`
     + `"Kết nối với liên hệ trong danh bạ"`
     + `"Kết nối với bạn bè trên Facebook"`
     + `"Tìm các liên hệ của bạn"`
   - Do không khớp từ khóa cũ, hàm `_has_friends_feed_content(after)` trả về `False`, script không kích hoạt `fallback_to_for_you` mà tiếp tục vuốt trên danh sách thẻ danh bạ.

2. **Rò rỉ mẫu số trong `_feed_action_counts(table)`:**
   - Logic cũ cứ thấy `row.get("action") == "swipe" and feed_type in feed_counts` là cộng dồn `feed_counts[feed_type] += 1`.
   - Trên màn gợi ý kết nối danh bạ / Facebook, không có video player và không có nút like. Các lượt swipe trên màn rỗng này làm tăng mẫu số `feed_counts["friends"]` thêm hàng chục lượt với 0 lượt like, kéo tụt tỷ lệ % tim Friends từ 100% (trên video thật như Máy 44: 2 tim / 2 video) xuống còn 7.7% ~ 8.7%.

## 3. Quy Chuẩn Sửa Đổi (Fix Contract)
File: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`

1. **Mở rộng `_FRIENDS_FEED_CONTENT_TERMS`:**
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

2. **Gắn cờ cách ly khi fallback:**
   ```python
   if is_feed_session and current_feed_type in (FEED_TYPE_FRIENDS, FEED_TYPE_FOLLOWING) and _has_friends_feed_content(after):
       fb_res = tap_navigation_target(...)
       if fb_res.ok:
           ...
           current_feed_type = FEED_TYPE_FOR_YOU
           after["feed_type"] = FEED_TYPE_FOR_YOU
           after["is_empty_feed_fallback"] = True
   ```

3. **Chặn tính vào mẫu số trong `_feed_action_counts(table)`:**
   ```python
   for row in table:
       feed_type = row.get("feed_type")
       if row.get("action") == "swipe" and feed_type in feed_counts:
           if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
               feed_counts[feed_type] += 1
   ```

## 4. Kiểm Chứng (Verification)
- Chạy unit test kiểm tra từ khóa và logic đếm mẫu số:
  `pytest python_runner/tests/test_feed_swipe_smoke.py -k "friends or like"` -> 8/8 passed.
