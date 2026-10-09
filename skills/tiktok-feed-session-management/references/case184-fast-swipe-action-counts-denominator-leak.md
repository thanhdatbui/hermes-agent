# Case 184: Fast Swipe Bị Bỏ Sót Trong Mẫu Số feed_counts Gây Phình Ảo Tỉ Lệ Like Từng Tab

## 1. Hiện Tượng & Nghi Vấn
- Trên báo cáo Watchdog Feed Session:
  ```text
  • Thả tim: 140 tim / 1159 video (12.1%) [Đề xuất: 132 (32.3%) | Bạn bè: 8 (57.1%) | Following: 0 (0.0%)]
  ```
- Tỉ lệ tổng ngoài ngoặc là `12.1%` (140 tim / 1159 video), hoàn toàn an toàn và nằm trong ngưỡng tự nhiên.
- Tuy nhiên trong ngoặc vuông, tỉ lệ tab Đề xuất hiển thị `32.3%` và Bạn bè `57.1%`, gây nghi vấn bot thả tim bất thường hoặc thuật toán tính mẫu số bị sai.

## 2. Root Cause
1. **Fast Swipe không dump XML:** Nhánh `is_fast_swipe_candidate` trong `feed_swipe_smoke.py` chỉ vuốt nhanh và kiểm tra focus nhẹ nhàng, không dump XML và không thực hiện like. Record kết quả mang nhãn `"action": "fast_swipe"`.
2. **Lọc sót action trong `_feed_action_counts`:**
   ```python
   # Code cũ trước khi fix:
   if row.get("action") == "swipe" and feed_type in feed_counts:
       if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
           feed_counts[feed_type] += 1
   ```
   Điều kiện `row.get("action") == "swipe"` bỏ qua hoàn toàn `"action": "fast_swipe"`.
3. **Mẫu số tab bị co cụm về Deep Inspect:**
   - Trong tổng số 1159 lượt vuốt, có tới ~737 lượt là Fast Swipe.
   - `feed_counts["for-you"]` chỉ đếm ~408 video (các video Deep Inspect có dump XML).
   - Watchdog tính `fy_rate_str = (tot_fy_likes / tot_fy_swipes * 100.0)` với mẫu số 408 video thay vì ~1100 video, khiến tỉ lệ bị phình to ảo lên 32.3%.

## 3. Giải Pháp (Patch Contract)
- Mở rộng điều kiện kiểm tra action trong `_feed_action_counts`:
  ```python
  if row.get("action") in ("swipe", "fast_swipe") and feed_type in feed_counts:
      if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
          feed_counts[feed_type] += 1
  ```
- Bổ sung unit test trong `test_feed_swipe_smoke.py` kiểm tra row `{"action": "fast_swipe", "feed_type": "for-you"}` được cộng dồn chính xác vào `feed_counts["for-you"]`.

## 4. Verification
- Py_compile file `flows/feed_swipe_smoke.py` exit 0.
- Chạy focused unit test: `python -m unittest test_feed_swipe_smoke.py -k "test_empty_friends_suggestion_feed_not_counted_in_feed_counts"` đạt 1/1 test passed.
