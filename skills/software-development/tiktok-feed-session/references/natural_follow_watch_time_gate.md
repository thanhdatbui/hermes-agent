# Natural Follow & Watch Time Gate Workflow

## 1. Natural Follow Watch Time Gate (`feed_swipe_smoke.py`)
Khi triển khai tính năng follow tự nhiên trong lúc lướt feed:
- Hàm xử lý chính: `_maybe_follow_video(ctx, after_attempt, follow_rate_percent)`.
- **Cơ chế Watch Time Gate**:
  - Không được bấm follow ngay lập tức khi vừa swipe tới video mới.
  - Phải vượt qua check xác suất `random.randint(1, 100) > int(follow_rate_percent)`.
  - Ngay sau khi trúng điều kiện follow: thực hiện ngâm video (Watch Time Gate) từ 8.0s đến 12.0s bằng `time.sleep(random.uniform(8.0, 12.0))`.
  - Chỉ sau khi đã ngâm đủ thời gian mới tiến hành `_capture_xml_text(ctx, "follow_video")` và tìm UIElement follow button để tap. Tránh hoàn toàn việc TikTok phát hiện hành vi bot click siêu tốc.

## 2. Watchdog Metrics Reporting (`feed_session_watchdog.py`)
Khi bổ sung metric tương tác mới (như Natural Follow, Comment Peeks, Shares) vào báo cáo Ca:
- **4 vị trí bắt buộc đồng bộ**:
  1. `merge_machine_result`: Hợp nhất dữ liệu dict/count giữa các run thử lại (retry runs).
  2. `parse_run_all`: Phân tích `summary.txt` (dùng regex hoặc json load) để bóc tách số liệu vào payload từng máy.
  3. Khối tính toán tổng: Tổng hợp số lượt, tính tỷ lệ trên tổng số video swipe (`tot_swipes`), phân bổ theo tab (`for-you`, `friends`, `following`).
  4. Khối tin nhắn Telegram: Thêm dòng thống kê trực quan vào `block_lines` dưới mục Thả tim.
  5. Đồng bộ code: Kiểm tra và đồng bộ script tới mirror `C:\Users\<user>\AppData\Local\hermes\scripts\feed_session_watchdog.py`.
