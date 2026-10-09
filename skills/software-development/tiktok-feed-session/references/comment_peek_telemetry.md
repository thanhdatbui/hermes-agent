# TikTok Comment Peek Logic & Watchdog Telemetry

## 1. Mục đích
Tạo tính tự nhiên và entropy hành vi cao trong quá trình feed swipe (`feed_swipe_smoke.py`), mô phỏng người dùng lướt đọc bình luận trên các video deep-inspect có tương tác thật, tránh hành vi máy móc trên các video 0 comment hoặc tắt tính năng comment.

## 2. Kiến trúc & Logic Phân Phối
- **Vị trí kích hoạt:** `python_runner/flows/feed_swipe_smoke.py` -> `_maybe_peek_comments()`.
- **Tỷ lệ phiên động:** Mỗi phiên feed session khởi tạo một tỷ lệ riêng `session_comment_peek_rate = random.randint(20, 35)%`.
- **Điều kiện cần:** Chỉ xét trên các video lọt vào luồng deep inspect (`is_deep_inspect_video`).
- **Phân tích số lượng comment (`_parse_comment_count`):**
  - Trích xuất regex số lượng (hỗ trợ định dạng `1.2k`, `3,5m`, số nguyên).
  - Đọc từ `content_desc` / `text` của button comment hoặc nhãn văn bản ngay sát bên dưới button (dx <= 80, 0 < dy <= 120).
  - **Zero comments:** Nếu phát hiện comment == 0 hoặc tắt comment, bỏ qua hoàn toàn (`skipped_zero_comments`).
  - **Không xác định được số (chỉ có icon):** Giảm tỷ lệ tò mò mở xuống mức an toàn 5% (`skipped_unverifiable_count`).
  - **Hành vi đọc:** Chỉ cuộn nhẹ lướt đọc bình luận khi `comment_count >= 5` (xác suất 50%), sau đó đóng bằng `keyevent 4` (Back).

## 3. Telemetry & Watchdog Monitoring
- **Ghi nhận kết quả video:**
  - Khi peek thành công: `after["comment_peeked"] = True`.
  - Tổng hợp qua `build_feed_swipe_summary` và `aggregate_feed_swipe_results` -> trả về trường `comment_peeks` và `comment_peek_counts` theo từng feed type (`fyp`, `following`, `friends`).
- **Watchdog reporting (`feed_session_watchdog.py`):**
  - Trích xuất `comment_peeks` từ log output máy con.
  - Bổ sung tổng hợp `tot_comment_peeks` và `tot_comment_rate` (tổng lượt đọc comment / tổng video đã lướt).
  - Định dạng hiển thị trong báo cáo Telegram / console:
    `+ Đọc comment: {tot_comment_peeks} lượt / {tot_swipes} video ({tot_comment_rate:.1f}%)`.
