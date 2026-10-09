# Case 180: Exclude Empty Friends/Suggestion Screens from Feed Counts Denominator & Expand Fallback Markers

## 1. Triệu chứng & Feedback Người Vận Hành
- Báo cáo watchdog nuôi TikTok báo tỉ lệ like tab Bạn bè cực thấp: `Bạn bè: 2 (8.7%)` (hoặc ~7.7% trên tổng máy).
- Người vận hành chất vấn: *"Ủa màn rỗng thì mắc gì tính vào mẫu số để r chia ra % bé?"*
- Bản chất kỳ vọng: Màn hình gợi ý rỗng (chưa có bạn bè / danh bạ / tác giả đề xuất) không phải video player thật, không có nút like, tuyệt đối không được tính làm mẫu số chia tỷ lệ tương tác.

## 2. Root Cause Codebase
Trong `python_runner/flows/feed_swipe_smoke.py`:
1. **Lọt lưới từ khóa rỗng (`_FRIENDS_FEED_CONTENT_TERMS`):**
   - Danh sách cũ chỉ có: `"Hãy follow bạn bè"`, `"Nhật ký"`, `"Tác giả nổi bật"`, `"bạn sẽ nhận thấy họ ở đây"`, `"xem video mới nhất của họ tại đây"`, `"Khi bạn Follow"`.
   - Màn hình TikTok thực tế trên máy hiện trường hiển thị các cụm từ mới:
     - `"Kết nối với bạn bè để xem bài đăng"`
     - `"Tìm các liên hệ của bạn"`
     - `"Kết nối với liên hệ trong danh bạ"`
     - `"Kết nối với bạn bè trên Facebook"`
   - Script không nhận diện được màn rỗng nên không kích hoạt fallback về For You, chấp nhận tiếp tục swipe 1-2 nhịp trên danh sách danh bạ.
2. **Lỗi đếm mù trong `_feed_action_counts`:**
   - Hàm thống kê đếm mẫu số mù quáng:
     ```python
     if row.get("action") == "swipe" and feed_type in feed_counts:
         feed_counts[feed_type] += 1
     ```
   - Khi swipe trên màn hình danh bạ rỗng, không có video player và không có nút like, nhưng vẫn bị tính là 1 lượt xem video. 24 lượt swipe rỗng bị tính dồn vào mẫu số, chia cho 2 tim thật kéo tụt tỷ lệ like toàn farm xuống 7.7% ~ 8.7%.

## 3. Patch Contract Chuẩn (Commit acb7989)
1. **Anchor 1 (`_FRIENDS_FEED_CONTENT_TERMS`):**
   Bổ sung 4 cụm từ UI TikTok mới vào tuple nhận diện:
   - `"Kết nối với bạn bè để xem bài đăng"`
   - `"Tìm các liên hệ của bạn"`
   - `"Kết nối với liên hệ trong danh bạ"`
   - `"Kết nối với bạn bè trên Facebook"`
2. **Anchor 2 (Fallback handling):**
   Trong nhánh fallback về For You khi phát hiện `_has_friends_feed_content(after)`:
   ```python
   after["is_empty_feed_fallback"] = True
   ```
3. **Anchor 3 (Lọc mẫu số trong `_feed_action_counts`):**
   Chặn không cộng dồn các màn hình gợi ý rỗng vào mẫu số:
   ```python
   if row.get("action") == "swipe" and feed_type in feed_counts:
       if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
           feed_counts[feed_type] += 1
   ```

## 4. Kiểm Chứng (Verification)
- Thêm unit test `test_empty_friends_suggestion_feed_not_counted_in_feed_counts` vào `python_runner/tests/test_feed_swipe_smoke.py`.
- Chạy pytest: 9/9 test cases pass 100%.
