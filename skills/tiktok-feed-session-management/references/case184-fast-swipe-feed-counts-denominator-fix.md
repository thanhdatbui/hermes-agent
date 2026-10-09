# Case 184: Vá Lỗi Fast Swipe Bị Bỏ Sót Trong Mẫu Số feed_counts Khiến % Thả Tim Tăng Ảo & Kỷ Luật Worker Monolith

## 1. Hiện tượng & Triệu chứng
Trên báo cáo Watchdog của các ca nuôi feed (Row 3, Ca 2):
```text
+ Thả tim: 140 tim / 1159 video (12.1%) [Đề xuất: 132 (32.3%) | Bạn bè: 8 (57.1%) | Following: 0 (0.0%)]
```
- Tỉ lệ tổng ngoài ngoặc: `140 tim / 1159 video = 12.1%` (hoàn toàn bình thường và tự nhiên).
- Tỉ lệ trong ngoặc: Đề xuất vọt lên `32.3%` ($132 / 408$), Bạn bè `57.1%` ($8 / 14$).
- Tổng mẫu số của 3 tab cộng lại chỉ có: $408 + 14 + 0 = 422$ video, trong khi toàn farm đã lướt $1159$ video. Bị thất thoát hơn 700 video khỏi mẫu số các tab.

## 2. Root Cause
1. Trong luồng chạy Fast Swipe (`feed_swipe_smoke.py`, dòng ~21827, 21980), các lượt lướt nhanh không dump XML được ghi nhận vào `results` với action là `"fast_swipe"`.
2. Hàm thống kê `_feed_action_counts(table)` kiểm tra:
   ```python
   # CŨ:
   if row.get("action") == "swipe" and feed_type in feed_counts:
       if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
           feed_counts[feed_type] += 1
   ```
   Do kiểm tra cứng `row.get("action") == "swipe"`, toàn bộ các lượt `fast_swipe` (~65-70% số video) bị bỏ qua, không được cộng vào `feed_counts[feed_type]`.
3. Chỉ các lượt Deep Inspect (dừng lại dump XML và tìm nút like) mới mang nhãn `"swipe"`. Hệ quả là mẫu số của từng tab chỉ đếm video Deep Inspect, khiến phép chia tỉ lệ `% like` của tab Đề xuất bị phình to ảo lên 30-40%.

## 3. Bản Vá Chuẩn (Commit `5e3cc8e`)
- Cập nhật điều kiện gom mẫu số trong `_feed_action_counts`:
  ```python
  # MỚI:
  if row.get("action") in ("swipe", "fast_swipe") and feed_type in feed_counts:
      if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
          feed_counts[feed_type] += 1
  ```
- Thêm unit test kiểm chứng trong `test_feed_swipe_smoke.py`:
  - Verify row `fast_swipe` được tính đúng vào `feed_counts["for-you"]`.

## 4. Kỷ Luật Điều Phối Worker Cho File Monolith Cực Lớn (>20.000 dòng)
- **Cạm bẫy:** `feed_swipe_smoke.py` có tới 23.315 dòng (676KB). Nếu worker subagent gọi `read_file` hoặc `search_files` toàn bộ file, payload phản hồi sẽ thổi phồng context và gây timeout mạng 600s ở tầng LLM API.
- **Kỷ luật bắt buộc:** 
  1. Coordinator BẮT BUỘC tự định vị anchor O(1) ở session chính.
  2. Bơm chỉ thị cấm tuyệt đối worker dùng `read_file`/`search_files` trên monolith.
  3. Worker CHỈ dùng duy nhất tool `patch` (mode replace) với `old_string` và `new_string` chính xác tuyệt đối, sau đó chạy ngay focused unit test nghiệm thu.
