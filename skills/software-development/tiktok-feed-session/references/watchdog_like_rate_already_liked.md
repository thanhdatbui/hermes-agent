# Watchdog Like Rate Telemetry: already_liked Denominator Exclusion

## 1. Bản chất vấn đề
Khi tài khoản TikTok xem lại các video của bạn bè hoặc video đã xuất hiện trước đó, nhiều video đã có tim đỏ (`already_liked`).
- Script nuôi acc (`feed_swipe_smoke.py`) phát hiện và skip like an toàn (không tap lại để tránh bị unlike).
- Nếu watchdog tính tỉ lệ thả tim bằng cách lấy `likes / total_swipes`, mẫu số bao gồm cả các video đã like từ trước, khiến tỉ lệ thả tim bị loãng giả tạo (ví dụ: gặp 24 video bạn bè, 19 video đã tim đỏ từ trước, 5 video mới thì tim cả 5; nếu chia cho 24 thì chỉ đạt 20.8% thay vì 100%).

## 2. Quy chuẩn tính toán chuẩn (Mẫu số hợp lệ)
- **Mẫu số hợp lệ**:
  ```python
  valid_fy_swipes = max(tot_fy_likes, tot_fy_swipes - tot_fy_al)
  valid_fl_swipes = max(tot_fl_likes, tot_fl_swipes - tot_fl_al)
  valid_fr_swipes = max(tot_fr_likes, tot_fr_swipes - tot_fr_al)
  ```
- **Tỉ lệ tính theo valid swipes**:
  ```python
  fy_rate_str = f"{(tot_fy_likes / valid_fy_swipes * 100.0):.1f}%" if valid_fy_swipes > 0 else "0.0%"
  fr_rate_str = f"{(tot_fr_likes / valid_fr_swipes * 100.0):.1f}%" if valid_fr_swipes > 0 else "0.0%"
  fl_rate_str = f"{(tot_fl_likes / valid_fl_swipes * 100.0):.1f}%" if valid_fl_swipes > 0 else "0.0%"
  ```

## 3. Telemetry Pipeline
1. `feed_swipe_smoke.py`:
   - `_maybe_like_video`: gán `after_attempt["already_liked"] = True` khi video đã tim.
   - `_feed_action_counts`: tổng hợp dictionary `already_liked_counts` theo từng feed type.
   - `aggregate_feed_swipe_results`: đưa `already_liked_counts` vào summary.
2. `feed_session_watchdog.py`:
   - `parse_run_all`: trích xuất `already_liked_counts` từ `summary.txt` (hoặc fallback đếm `already_liked` từ `log.jsonl`).
   - `merge_machine_result`: merge `already_liked` qua `max(p_al.get(k, 0), n_al.get(k, 0))`.
