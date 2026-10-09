# Feed Session Like Rate Telemetry and Already Liked Denominator Adjustment

## Vấn đề
Khi nuôi feed qua các tab (Bạn bè / Following / For You), nhiều video đã được thả tim đỏ từ trước (`already_liked`), runner bỏ qua không tap lại để tránh un-like.
Nếu Watchdog tính tỉ lệ tim theo mẫu số thô (`tot_swipes`), tỉ lệ tim bị pha loãng nghiêm trọng (ví dụ 5 tim / 24 video = 20.8% dù 19 video còn lại đã có tim từ trước).

## Chuẩn hóa kiến trúc
1. **Runner (`feed_swipe_smoke.py`):**
   - Khi `liked is not None` trong `_maybe_like_video`: gán `after_attempt["already_liked"] = True`.
   - `_feed_action_counts`: đếm `already_liked` cho từng `feed_type`.
   - `aggregate_feed_swipe_results`: lưu `already_liked_counts` vào summary.
2. **Watchdog (`feed_session_watchdog.py`):**
   - Parse `already_liked_counts` từ summary hoặc đọc fallback từ `log.jsonl`.
   - Merge `already_liked` qua `merge_machine_result`.
   - Điều chỉnh mẫu số: `valid_swipes = max(tot_likes, tot_swipes - tot_already_liked)`.
   - Tỉ lệ hiển thị phản ánh đúng 100% tỉ lệ thả tim thực tế trên các video mới chưa tim.
