# Smart Comment Peek & Watchdog Reporting Rules (2026-09-16)

## 1. Cơ chế Smart Comment Peek (`feed_swipe_smoke.py`)
- **Vấn đề trước đây:** Video 0 comment hoặc tắt comment nhưng script vẫn mở lên đọc, dẫn đến:
  - Dead swipe (cuộn rỗng trên UI trống).
  - Telemetry rác gửi về máy chủ TikTok.
  - Tốn thời gian phiên nuôi mà không tạo được giá trị tương tác thật.
- **Quy tắc triển khai chuẩn:**
  1. **Probability Gate trước:** Đặt `if random.randint(1, 100) > int(peek_rate_percent): return False` ngay đầu hàm trước khi duyệt XML để tiết kiệm CPU và tránh chạy thừa.
  2. **Trích xuất số lượng đa ngôn ngữ (`_parse_comment_count`):** Phải hỗ trợ các định dạng:
     - Số thuần: `123`, `0`
     - Ký hiệu quốc tế: `1.2k`, `2m`
     - Ký hiệu tiếng Việt: `1,2k`, `500 n` (nghìn), `2 tr` (triệu)
  3. **Fail-Closed Zero-Comment Guard:**
     - Nếu `comment_count is None or comment_count <= 0`: BỎ QUA HOÀN TOÀN (`return False`), log `skipped_zero_comments` hoặc `skipped_unverifiable_comments`. Tuyệt đối không bấm mở.
  4. **Chỉ vuốt khi có nhiều bình luận:** Chỉ vuốt đọc lướt khi video có từ $\ge 5$ bình luận (`has_many_comments`).
  5. **Closed-Loop Verification:** Sau khi đóng comment sheet bằng phím Back (`keyevent 4`), bắt buộc xác minh package focused vẫn là TikTok (`trill`, `musically`, `aweme`). Nếu lệch package -> fail-closed ngay lập tức.
  6. **Telemetry:** Ghi nhận `comment_peeked: True` vào kết quả attempt thành công và thống kê theo từng tab (`for-you`, `following`, `friends`) vào summary metadata.

## 2. Tích hợp báo cáo Watchdog Cron (`feed_session_watchdog.py`)
- Trích xuất `comment_peeks` từ log tóm tắt (`summary.txt`) của từng máy trong ca.
- Thống kê tỷ lệ trên tổng số video lướt thành công của toàn ca:
  `tot_comment_rate = (tot_comment_peeks / tot_swipes * 100.0)`
- Format báo cáo Telegram chuẩn:
  ```text
    + Thả tim: {tot_likes} tim / {tot_swipes} video ({tot_rate:.1f}%) [...]
    + Đọc comment: {tot_comment_peeks} lượt / {tot_swipes} video ({tot_comment_rate:.1f}%)
  ```
