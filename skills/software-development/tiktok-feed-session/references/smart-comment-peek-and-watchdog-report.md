# Cơ chế Smart Comment Peek và Báo cáo Watchdog Nuôi Acc

## 1. Mục đích & Nguyên lý
- **Chống dead swipe & giảm entropy giả**: Không bao giờ mở hoặc cuộn ở các video có 0 comment hoặc tắt comment.
- **Fail-closed pre-check**: Trích xuất số lượng bình luận trước khi tap. Nếu không nhận diện được số lượng rõ ràng (>0) hoặc `comment_count <= 0`, bỏ qua (`return False`).
- **Phân phối tự nhiên**: Tỷ lệ mở comment được tính toán để trên toàn bộ phiên nuôi (bù trừ cho các video fast swipe) đạt ~8% - 15% tổng số video xem.
- **Closed-loop focus verification**: Sau khi bấm Back đóng sheet comment, bắt buộc kiểm tra package name còn là TikTok (`trill`/`musically`/`aweme`). Nếu lệch package -> log `failed_dismissal` và fail-closed.

## 2. Các điểm code then chốt trong `feed_swipe_smoke.py`
- `_parse_comment_count(text: str) -> int | None`: Hỗ trợ regex nhận diện các dạng số: `123`, `1.2k`, `1,5k`, `2m`, `2 tr`, `500 n`.
- `_maybe_peek_comments(...)`:
  - Kiểm tra `random.randint(1, 100) > int(peek_rate_percent)` ngay đầu hàm.
  - Tìm nút comment và text kế cận (dy 0-120px).
  - Gated: `if comment_count is None or comment_count <= 0: return False`.
  - Chỉ cuộn lướt nhẹ khi `comment_count >= 5` và xác suất 50%.
- Ghi nhận `comment_peeked` trong `build_feed_swipe_summary`, `_feed_action_counts`, `aggregate_feed_swipe_results`.

## 3. Tích hợp báo cáo trong `feed_session_watchdog.py`
- Trích xuất `comment_peeks` từ `summary.txt` từng máy.
- Tổng kết hiển thị trên Telegram:
  `  + Đọc comment: {tot_comment_peeks} lượt / {tot_swipes} video ({tot_comment_rate:.1f}%)`
